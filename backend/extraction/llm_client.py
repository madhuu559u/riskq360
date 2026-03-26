"""Unified LLM client supporting OpenAI, Azure OpenAI, and Google Gemini.

Provides a consistent interface for all LLM calls with retries, logging, and token tracking.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import LLMProvider, LLMSettings
from core.exceptions import JSONParsingError, LLMCallError

logger = structlog.get_logger(__name__)


class UnifiedLLMClient:
    """Multi-provider LLM client with structured JSON output support."""

    def __init__(self, llm_settings: LLMSettings) -> None:
        self.settings = llm_settings
        self.provider = llm_settings.active_llm_provider
        self.model = llm_settings.active_llm_model
        self._openai_client = None
        self._total_tokens = 0
        self._total_calls = 0

    @property
    def openai_client(self):
        if self._openai_client is None:
            import openai
            if self.provider == LLMProvider.AZURE:
                self._openai_client = openai.AsyncAzureOpenAI(
                    azure_endpoint=self.settings.azure.endpoint,
                    api_key=self.settings.azure.key,
                    api_version=self.settings.azure.api_version,
                )
            else:
                self._openai_client = openai.AsyncOpenAI(
                    api_key=self.settings.openai.api_key,
                    organization=self.settings.openai.org_id or None,
                )
        return self._openai_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = True,
    ) -> Dict[str, Any]:
        """Call the LLM and return parsed JSON response.

        Args:
            system_prompt: System instructions.
            user_prompt: User message (clinical text + task).
            model: Override model name.
            temperature: Override temperature.
            max_tokens: Override max tokens.
            json_mode: Request JSON response format.

        Returns:
            Parsed JSON dict from the LLM response.
        """
        model = model or self.model
        temperature = temperature if temperature is not None else self.settings.llm_temperature
        max_tokens = max_tokens or self.settings.llm_max_tokens

        start_time = time.time()

        try:
            if self.provider in (LLMProvider.OPENAI, LLMProvider.AZURE):
                result = await self._call_openai(
                    system_prompt, user_prompt, model, temperature, max_tokens, json_mode
                )
            elif self.provider == LLMProvider.GEMINI:
                result = await self._call_gemini(
                    system_prompt, user_prompt, model, temperature, max_tokens
                )
            else:
                raise LLMCallError(f"Unsupported provider: {self.provider}")

            elapsed = time.time() - start_time
            self._total_calls += 1

            logger.info("llm.call_success", provider=self.provider.value,
                         model=model, elapsed=round(elapsed, 2),
                         tokens=result.get("_usage", {}).get("total_tokens", 0))

            return result

        except LLMCallError:
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("llm.call_failed", provider=self.provider.value,
                          model=model, error=str(e), elapsed=round(elapsed, 2))
            raise LLMCallError(
                f"LLM call failed: {e}",
                provider=self.provider.value,
                model=model,
            ) from e

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> Dict[str, Any]:
        """Call OpenAI / Azure OpenAI API."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.openai_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            self._total_tokens += response.usage.total_tokens

        parsed = safe_parse_json(content)
        parsed["_usage"] = usage
        return parsed

    async def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Call Google Gemini API."""
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini.gemini_key)
        gen_model = genai.GenerativeModel(
            model_name=model or "gemini-2.0-flash",
            system_instruction=system_prompt,
        )
        response = gen_model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        content = response.text or ""
        parsed = safe_parse_json(content)
        parsed["_usage"] = {}
        return parsed

    async def call_vision(
        self,
        image_b64: str,
        prompt: str,
        model: str | None = None,
    ) -> Dict[str, Any]:
        """Call GPT-4o Vision API with a base64-encoded image."""
        model = model or "gpt-4o"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ]

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return safe_parse_json(content)

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def total_calls(self) -> int:
        return self._total_calls


def safe_parse_json(text: str) -> Dict[str, Any]:
    """Robustly parse JSON from LLM output.

    Handles: markdown fences, trailing commas, truncated JSON.
    """
    if not text or not text.strip():
        return {}

    # Strip markdown code fences
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to balance braces for truncated JSON
    open_braces = cleaned.count("{") - cleaned.count("}")
    open_brackets = cleaned.count("[") - cleaned.count("]")
    if open_braces > 0 or open_brackets > 0:
        repaired = cleaned + ("]" * open_brackets) + ("}" * open_braces)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # Last resort: try to find first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("json.parse_failed", text_preview=text[:200])
    return {"_raw_text": text, "_parse_error": True}
