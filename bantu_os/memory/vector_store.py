"""
Vector store abstraction with an adapter for the existing in-memory VectorDB.

This allows swapping to FAISS/Chroma/Qdrant later without touching Memory callers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np

from .vector_db import VectorDB  # existing simple in-memory DB


class VectorStore(ABC):
    """Abstract interface for vector stores."""

    @abstractmethod
    def add(self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get(self, record_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        raise NotImplementedError


class VectorDBStore(VectorStore):
    """Adapter over the existing VectorDB class."""

    def __init__(self, dim: int = 768):
        self.db = VectorDB(dim=dim)
        self.dim = dim

    def add(self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None) -> str:
        return self.db.add(vector=vector, metadata=metadata, text=text)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.db.search(query_vector=query_vector, top_k=top_k)

    def get(self, record_id: str) -> Any:
        return self.db.get(record_id)

    def delete(self, record_id: str) -> bool:
        return self.db.delete(record_id)


try:
    # Optional Chroma example adapter skeleton (no hard dependency)
    import chromadb  # type: ignore
    from chromadb.utils import embedding_functions  # type: ignore

    class ChromaVectorStore(VectorStore):  # pragma: no cover - optional
        def __init__(self, collection_name: str = "bantu-memory"):
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(collection_name)
            self.dim = None  # Chroma infers dimension

        def add(self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None) -> str:
            _id = metadata.get("id") or f"mem_{metadata.get('seq', 0)}"
            self.collection.add(ids=[_id], embeddings=[vector.tolist()], metadatas=[metadata], documents=[text or ""])
            return _id

        def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
            res = self.collection.query(query_embeddings=[query_vector.tolist()], n_results=top_k)
            out: List[Dict[str, Any]] = []
            for i in range(len(res.get("ids", [[]])[0])):
                out.append({
                    "id": res["ids"][0][i],
                    "similarity": float(res["distances"][0][i]) if "distances" in res else 0.0,
                    "metadata": res["metadatas"][0][i],
                    "text": res["documents"][0][i],
                })
            return out

        def get(self, record_id: str) -> Any:
            # Not implemented in this skeleton
            return None

        def delete(self, record_id: str) -> bool:
            self.collection.delete(ids=[record_id])
            return True
except Exception:  # pragma: no cover - ignore if chroma not installed
    ChromaVectorStore = None  # type: ignore
