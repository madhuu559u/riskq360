"""Extraction layer — LLM-based clinical data extraction.

Two extraction modes:
  1. parallel_extractor: 5-pipeline parallel extraction (demographics, sentences,
     risk dx, HEDIS evidence, encounters) — primary processing mode.
  2. assertion_extractor: MiniMax single-pass extraction — legacy mode.

Supporting modules:
  - smart_pdf: PDF text extraction with quality scoring + vision OCR fallback
  - prompts: System prompts for all 5 extraction pipelines
  - post_processor: Assertion enrichment, deduplication, validation
  - llm_caller: LLM call wrapper with retry logic
"""
