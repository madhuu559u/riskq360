"""Text chunking with paragraph-boundary splitting and overlap."""

from __future__ import annotations

import re
from typing import List

from config.pipeline_config import ChunkingConfig


def chunk_text(
    text: str,
    config: ChunkingConfig | None = None,
) -> List[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Args:
        text: Full document text.
        config: Chunking configuration (size, overlap, etc.).

    Returns:
        List of text chunks.
    """
    if config is None:
        config = ChunkingConfig()

    if len(text) <= config.chunk_size:
        return [text]

    chunks: List[str] = []

    if config.split_on_paragraphs:
        # Split at paragraph boundaries (double newlines)
        paragraphs = re.split(r"\n\s*\n", text)
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= config.chunk_size:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If single paragraph exceeds chunk size, split by sentences
                if len(para) > config.chunk_size:
                    sub_chunks = _split_by_sentences(para, config.chunk_size)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk and len(current_chunk) >= config.min_chunk_size:
            chunks.append(current_chunk)
        elif current_chunk and chunks:
            # Append short remainder to last chunk
            chunks[-1] += "\n\n" + current_chunk
    else:
        # Simple character-based chunking with overlap
        start = 0
        while start < len(text):
            end = start + config.chunk_size
            if end < len(text):
                # Try to break at a sentence boundary
                boundary = text.rfind(". ", start + config.chunk_size // 2, end)
                if boundary > start:
                    end = boundary + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - config.chunk_overlap

    # Add overlap context to chunks
    if config.chunk_overlap > 0 and config.split_on_paragraphs and len(chunks) > 1:
        chunks = _add_overlap(chunks, text, config.chunk_overlap)

    return chunks


def _split_by_sentences(text: str, max_size: int) -> List[str]:
    """Split a long paragraph into sentence-based chunks."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_size:
            current += (" " + sent) if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent

    if current:
        chunks.append(current)

    return chunks


def _add_overlap(chunks: List[str], full_text: str, overlap: int) -> List[str]:
    """Add overlap context between consecutive chunks."""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        # Prepend tail of previous chunk
        prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
        result.append(prev_tail + "\n\n" + chunks[i])
    return result
