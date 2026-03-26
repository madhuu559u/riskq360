"""5-pipeline parallel LLM extraction engine.

Runs 5 extraction pipelines in parallel, each processing text chunks
in parallel. Architecture:
  - 5 pipelines x N chunks per pipeline x max_chunk_workers threads
  - Robust JSON parsing with repair for truncated/malformed responses
  - Deep merge of multi-chunk results

Ported and adapted from medinsights_platform/pipeline/openai_extractor.py.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def safe_parse_json(raw_text: str) -> Dict[str, Any]:
    """Robustly parse JSON from LLM output.

    Handles: markdown fences, trailing commas, truncated JSON, unbalanced braces.
    """
    if not raw_text or not raw_text.strip():
        return {}

    text = raw_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fix truncated JSON
    for end_pos in range(len(text) - 1, -1, -1):
        if text[end_pos] in ('}', ']'):
            candidate = text[:end_pos + 1]
            open_braces = candidate.count('{')
            close_braces = candidate.count('}')
            open_brackets = candidate.count('[')
            close_brackets = candidate.count(']')

            repair = candidate
            repair += ']' * max(0, open_brackets - close_brackets)
            repair += '}' * max(0, open_braces - close_braces)
            repair = re.sub(r',\s*([}\]])', r'\1', repair)

            try:
                return json.loads(repair)
            except json.JSONDecodeError:
                continue

    # Last resort: extract any JSON object or array
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    return {"_raw_text": raw_text, "_parse_error": True}


def chunk_text(text: str, chunk_size: int = 10000) -> List[str]:
    """Split text into chunks at paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0

    while start < len(text):
        if start + chunk_size >= len(text):
            chunks.append(text[start:])
            break

        end = start + chunk_size
        # Try paragraph break
        para_break = text.rfind('\n\n', start + chunk_size // 2, end + 500)
        if para_break > start:
            end = para_break
        else:
            line_break = text.rfind('\n', start + chunk_size // 2, end + 200)
            if line_break > start:
                end = line_break

        chunks.append(text[start:end].strip())
        start = end

    return [c for c in chunks if c.strip()]


def deep_merge(base: Dict, addition: Dict) -> Dict:
    """Deep merge two dicts: lists concatenated, dicts recursively merged."""
    result = dict(base)
    for key, value in addition.items():
        if key in result:
            if isinstance(result[key], list) and isinstance(value, list):
                result[key] = result[key] + value
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                if value is not None and value != "":
                    result[key] = value
        else:
            result[key] = value
    return result


def _call_llm_chunk(
    client: Any,
    model: str,
    system_prompt: str,
    chunk_text_content: str,
    chunk_idx: int,
    retries: int = 3,
) -> Dict[str, Any]:
    """Send a single chunk to the LLM with retry logic."""
    backoff_times = [10, 20, 30]

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract data from this medical chart text (chunk {chunk_idx + 1}):\n\n{chunk_text_content}"},
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            return safe_parse_json(raw)
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str:
                if attempt < retries - 1:
                    wait = backoff_times[min(attempt, len(backoff_times) - 1)]
                    log.warning("Rate limited on chunk %d, waiting %ds (attempt %d/%d)",
                                chunk_idx + 1, wait, attempt + 1, retries)
                    time.sleep(wait)
                    continue
            if attempt == retries - 1:
                log.error("LLM call failed on chunk %d: %s", chunk_idx + 1, e)
                return {"_error": str(e), "_chunk": chunk_idx}
            time.sleep(5)

    return {"_error": "max retries exceeded", "_chunk": chunk_idx}


def run_single_pipeline(
    client: Any,
    model: str,
    system_prompt: str,
    full_text: str,
    pipeline_name: str,
    chunk_size: int = 10000,
    max_chunk_workers: int = 4,
) -> Dict[str, Any]:
    """Run one extraction pipeline: chunk text -> parallel API calls -> merge."""
    chunks = chunk_text(full_text, chunk_size)
    log.info("[%s] %d chunk(s)", pipeline_name, len(chunks))

    if len(chunks) == 1:
        return _call_llm_chunk(client, model, system_prompt, chunks[0], 0)

    results: List[tuple] = []
    with ThreadPoolExecutor(max_workers=max_chunk_workers) as executor:
        futures = {
            executor.submit(
                _call_llm_chunk, client, model, system_prompt, chunk, idx
            ): idx
            for idx, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                result = future.result()
                results.append((chunk_idx, result))
            except Exception as e:
                log.error("[%s] Chunk %d exception: %s", pipeline_name, chunk_idx, e)
                results.append((chunk_idx, {"_error": str(e)}))

    results.sort(key=lambda x: x[0])
    merged: Dict = {}
    for _, result in results:
        if "_error" not in result and "_parse_error" not in result:
            merged = deep_merge(merged, result)

    return merged


def run_all_extractions(
    client: Any,
    text: str,
    prompts_dict: Dict[str, str],
    model: str = "gpt-4o-mini",
    max_pipeline_workers: int = 5,
    max_chunk_workers: int = 4,
    chunk_size: int = 10000,
) -> Dict[str, Dict[str, Any]]:
    """Run ALL extraction pipelines in parallel.

    Args:
        client: OpenAI-compatible client instance.
        text: Full chart text.
        prompts_dict: {pipeline_name: system_prompt} for each pipeline.
        model: LLM model to use.
        max_pipeline_workers: Number of parallel pipelines.
        max_chunk_workers: Number of parallel chunks per pipeline.
        chunk_size: Characters per chunk.

    Returns:
        {pipeline_name: extraction_result}
    """
    results: Dict[str, Dict] = {}
    log.info("Running %d extraction pipelines in parallel (model: %s)", len(prompts_dict), model)

    with ThreadPoolExecutor(max_workers=max_pipeline_workers) as executor:
        futures = {
            executor.submit(
                run_single_pipeline,
                client, model, system_prompt, text, name,
                chunk_size, max_chunk_workers,
            ): name
            for name, system_prompt in prompts_dict.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results[name] = result
                log.info("[%s] Complete", name)
            except Exception as e:
                log.error("[%s] FAILED: %s", name, e)
                results[name] = {"_error": str(e)}

    return results
