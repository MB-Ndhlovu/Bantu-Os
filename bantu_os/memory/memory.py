"""
Memory orchestrator for Bantu OS.

Abstractions:
- EmbeddingsProvider: converts text -> vector
- VectorStore: adds/searches vectors with metadata/text

Public API (kept simple and swappable):
- store_memory(query: str, embedding: np.ndarray, metadata: dict | None) -> str
- retrieve_memory(query: str, top_k: int = 5) -> list[dict]

Helpers:
- store_text(text: str, metadata: dict | None) -> str  # convenience, embeds internally
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from .vector_store import VectorStore, VectorDBStore
from .embeddings.base import EmbeddingsProvider


class Memory:
    """High-level memory built on embeddings + vector store."""

    def __init__(
        self,
        store: Optional[VectorStore] = None,
        embeddings: Optional[EmbeddingsProvider] = None,
        dim: int = 768,
    ) -> None:
        self.store = store or VectorDBStore(dim=dim)
        self.embeddings = embeddings  # optional: caller may provide later
        self.dim = dim
        
    def set_embeddings_provider(self, provider: EmbeddingsProvider) -> None:
        self.embeddings = provider

    def store_memory(self, query: str, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory vector with associated text and metadata.
        'query' is saved as the document text for later recall/explanation.
        """
        if embedding.shape[-1] != self.dim:
            raise ValueError(f"Embedding dim {embedding.shape[-1]} != expected {self.dim}")
        return self.store.add(vector=embedding.astype(np.float32), metadata=metadata or {}, text=query)

    async def store_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Convenience: embed and store text."""
        if not self.embeddings:
            raise RuntimeError("Embeddings provider not configured for Memory")
        vecs = await self.embeddings.embed([text])
        return self.store_memory(query=text, embedding=vecs[0], metadata=metadata)

    async def retrieve_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Embed the query and return top-k similar memories."""
        if not self.embeddings:
            raise RuntimeError("Embeddings provider not configured for Memory")
        vec = (await self.embeddings.embed([query]))[0]
        return self.store.search(query_vector=vec.astype(np.float32), top_k=top_k)
