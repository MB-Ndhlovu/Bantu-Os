"""
In-memory vector database for Bantu-OS.
Simple embedding store using cosine similarity on numpy arrays.
"""

from __future__ import annotations

import uuid
import math
from typing import Any, Optional


class VectorStore:
    """Simple in-memory vector store with cosine similarity."""

    def __init__(self) -> None:
        self.vectors: list[dict[str, Any]] = []

    def add(self, text: str, embedding: Optional[list[float]] = None, metadata: Optional[dict[str, Any]] = None) -> str:
        """Add a text entry with its embedding vector."""
        if embedding is None:
            embedding = self._random_embedding(len(text.split()))
        norm = self._normalize(embedding)
        entry_id = str(uuid.uuid4())[:8]
        self.vectors.append({
            "id": entry_id,
            "text": text,
            "embedding": norm,
            "metadata": metadata or {},
        })
        return entry_id

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Find top_k most similar entries by cosine similarity."""
        norm_query = self._normalize(query_embedding)
        scored = []
        for v in self.vectors:
            sim = self._cosine(norm_query, v["embedding"])
            scored.append((sim, v))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": v["id"], "text": v["text"], "score": sim, "metadata": v["metadata"]}
            for sim, v in scored[:top_k]
        ]

    def search_text(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search by text — generates embedding from words."""
        words = query_text.split()
        embedding = self._text_to_embedding(words)
        return self.search(embedding, top_k)

    def delete(self, entry_id: str) -> bool:
        for i, v in enumerate(self.vectors):
            if v["id"] == entry_id:
                self.vectors.pop(i)
                return True
        return False

    def count(self) -> int:
        return len(self.vectors)

    def _random_embedding(self, dim: int) -> list[float]:
        import random
        return [random.uniform(-1, 1) for _ in range(min(dim, 768))]

    def _normalize(self, v: list[float]) -> list[float]:
        mag = math.sqrt(sum(x * x for x in v))
        if mag == 0:
            return v
        return [x / mag for x in v]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return max(0.0, dot)

    def _text_to_embedding(self, words: list[str]) -> list[float]:
        dim = 128
        import random
        random.seed(sum(ord(w) for w in words))
        return [random.uniform(-1, 1) for _ in range(dim)]


# Default instance
_default_store: Optional[VectorStore] = None

def get_store() -> VectorStore:
    global _default_store
    if _default_store is None:
        _default_store = VectorStore()
    return _default_store

def store_text(text: str, metadata: Optional[dict[str, Any]] = None) -> str:
    return get_store().add(text, metadata=metadata)

def query_memory(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    return get_store().search_text(query, top_k=top_k)
