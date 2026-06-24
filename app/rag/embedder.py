from __future__ import annotations

import hashlib
import math
import re


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class HashingEmbedder:
    """Dependency-free embedding using hashed token counts.

    This is intentionally simple. It keeps the project runnable without a paid
    embedding API. Replace it later with sentence-transformers, OpenAI
    embeddings, or another production embedder when needed.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
            idx = int.from_bytes(digest, "big") % self.dim
            vector[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
