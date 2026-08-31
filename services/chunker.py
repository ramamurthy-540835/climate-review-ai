"""Structure-aware chunking for scientific assessment reports."""

import re
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_start: int
    page_end: int


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")


def _words(text: str) -> list[str]:
    return text.split()


def _split_long_block(block: str, max_words: int) -> list[str]:
    """Prefer sentence boundaries, falling back to a word boundary."""
    sentences = _SENTENCE_END.split(block.strip())
    parts: list[str] = []
    current: list[str] = []
    current_size = 0
    for sentence in sentences:
        sentence_words = _words(sentence)
        if len(sentence_words) > max_words:
            if current:
                parts.append(" ".join(current))
                current, current_size = [], 0
            for start in range(0, len(sentence_words), max_words):
                parts.append(" ".join(sentence_words[start:start + max_words]))
            continue
        if current and current_size + len(sentence_words) > max_words:
            parts.append(" ".join(current))
            current, current_size = [], 0
        current.extend(sentence_words)
        current_size += len(sentence_words)
    if current:
        parts.append(" ".join(current))
    return parts


def _blocks(text: str, max_words: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    result: list[str] = []
    for paragraph in paragraphs:
        if len(_words(paragraph)) <= max_words:
            result.append(paragraph)
        else:
            result.extend(_split_long_block(paragraph, max_words))
    return result


def chunk_pages(
    pages: Iterable[dict],
    chunk_size_words: int = 450,
    overlap_words: int = 75,
) -> List[TextChunk]:
    """Chunk on natural boundaries and retain page-level citations.

    Chunks intentionally do not span pages. This makes reviewer citations
    precise and keeps repeated page headers out of the middle of chunks.
    """
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be greater than zero")
    if overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be between 0 and chunk_size_words")

    chunks: list[TextChunk] = []
    for page in pages:
        page_number = int(page["page"])
        blocks = _blocks(page.get("content", ""), chunk_size_words)
        current: list[str] = []
        current_size = 0

        def emit() -> None:
            nonlocal current, current_size
            content = "\n\n".join(current).strip()
            if not content:
                return
            chunks.append(TextChunk(content, page_number, page_number))
            overlap = _words(content)[-overlap_words:] if overlap_words else []
            current = [" ".join(overlap)] if overlap else []
            current_size = len(overlap)

        for block in blocks:
            block_size = len(_words(block))
            if current and current_size + block_size > chunk_size_words:
                emit()
            if current_size and current_size + block_size > chunk_size_words:
                current, current_size = [], 0
            current.append(block)
            current_size += block_size

        if current:
            content = "\n\n".join(current).strip()
            if content and (not chunks or chunks[-1].content != content):
                chunks.append(TextChunk(content, page_number, page_number))

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[str]:
    """Split text into overlapping character chunks.

    Retained for compatibility; ingestion should use chunk_pages.
    """
    text = text.strip()
    if not text:
        return []

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks