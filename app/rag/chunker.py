from __future__ import annotations

import re


WORD_RE = re.compile(r"\S+")


def chunk_text(text: str, *, chunk_words: int = 180, overlap_words: int = 35) -> list[str]:
    """Split text into overlapping word chunks."""
    words = WORD_RE.findall(text)
    if not words:
        return []

    chunks: list[str] = []
    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_words]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks
