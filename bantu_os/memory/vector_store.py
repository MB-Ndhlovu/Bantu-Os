"""
Vector store abstraction with an adapter for the existing in-memory VectorDB.

This allows swapping to FAISS/Chroma/Qdrant later without touching Memory callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import os

from .vector_db import VectorDB  # existing simple in-memory DB


class VectorStore(ABC):
    """Abstract interface for vector stores."""

    @abstractmethod
    def add(
        self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None
    ) -> str:
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

    def add(
        self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None
    ) -> str:
        return self.db.add(vector=vector, metadata=metadata, text=text)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.db.query(query_embedding=query_vector, top_k=top_k)

    def get(self, record_id: str) -> Any:
        return self.db.get(record_id)

    def delete(self, record_id: str) -> bool:
        return self.db.delete(record_id)


try:
    # Optional Chroma example adapter skeleton (no hard dependency)
    import chromadb  # type: ignore

    class ChromaVectorStore(VectorStore):  # pragma: no cover - optional
        def __init__(self, collection_name: str = "bantu-memory"):
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(collection_name)
            self.dim = None  # Chroma infers dimension

        def add(
            self,
            vector: np.ndarray,
            metadata: Dict[str, Any],
            text: Optional[str] = None,
        ) -> str:
            _id = metadata.get("id") or f"mem_{metadata.get('seq', 0)}"
            self.collection.add(
                ids=[_id],
                embeddings=[vector.tolist()],
                metadatas=[metadata],
                documents=[text or ""],
            )
            return _id

        def search(
            self, query_vector: np.ndarray, top_k: int = 5
        ) -> List[Dict[str, Any]]:
            res = self.collection.query(
                query_embeddings=[query_vector.tolist()], n_results=top_k
            )
            out: List[Dict[str, Any]] = []
            for i in range(len(res.get("ids", [[]])[0])):
                out.append(
                    {
                        "id": res["ids"][0][i],
                        "similarity": (
                            float(res["distances"][0][i]) if "distances" in res else 0.0
                        ),
                        "metadata": res["metadatas"][0][i],
                        "text": res["documents"][0][i],
                    }
                )
            return out

        def get(self, record_id: str) -> Any:
            # Not implemented in this skeleton
            return None

        def delete(self, record_id: str) -> bool:
            self.collection.delete(ids=[record_id])
            return True

except Exception:  # pragma: no cover - ignore if chroma not installed
    ChromaVectorStore = None  # type: ignore

# ── ChromaDB adapter ──────────────────────────────────────────────────────────

try:
    import chromadb

    HAS_CHROMADB = True
except Exception:
    HAS_CHROMADB = False


class ChromaVectorStore(VectorStore):
    """ChromaDB-backed VectorStore.掉落 to in-memory VectorDB if Chroma is unavailable."""

    def __init__(
        self,
        path: str = "./bantu_os_data/chromadb",
        collection: str = "bantu_memory",
        dim: int = 768,
        distance_fn: str = "cosine",
    ) -> None:
        self.dim = dim
        self._collection_name = collection
        if HAS_CHROMADB:
            os.makedirs(path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=path)
            self._coll = self._client.get_or_create_collection(
                name=collection,
                metadata={"hnsw:space": distance_fn},
            )
        else:
            # Fallback to in-memory
            self._coll = None
            self._fallback = VectorDB(dim=dim)

    def add(
        self, vector: np.ndarray, metadata: Dict[str, Any], text: Optional[str] = None
    ) -> str:
        if self._coll is not None:
            import time

            uid = metadata.get("id") or f"mem_{int(time.time() * 1000)}"
            meta = dict(metadata)
            meta["text"] = text or ""
            self._coll.add(
                ids=[uid],
                embeddings=[vector.tolist()],
                documents=[text or ""],
                metadatas=[meta],
            )
            return uid
        return self._fallback.add(vector=vector, metadata=metadata, text=text)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if self._coll is not None:
            try:
                results = self._coll.query(
                    query_embeddings=[query_vector.tolist()],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception:
                return []
            if not results or not results.get("ids") or not results["ids"][0]:
                return []
            out = []
            for i, uid in enumerate(results["ids"][0]):
                dist = results["distances"][0][i]
                out.append(
                    {
                        "id": uid,
                        "text": (
                            results["documents"][0][i]
                            if i < len(results["documents"][0])
                            else ""
                        ),
                        "metadata": (
                            results["metadatas"][0][i]
                            if i < len(results["metadatas"][0])
                            else {}
                        ),
                        "distance": dist,
                        "similarity": 1.0 - dist,
                    }
                )
            return out
        return self._fallback.query(query_embedding=query_vector, top_k=top_k)

    def get(self, record_id: str) -> Any:
        if self._coll is not None:
            try:
                r = self._coll.get(ids=[record_id])
                if r["ids"]:
                    return {
                        "id": r["ids"][0],
                        "text": r["documents"][0],
                        "metadata": r["metadatas"][0],
                    }
            except Exception:
                pass
            return None
        return self._fallback.get(record_id)

    def count(self) -> int:
        if self._coll is not None:
            return self._coll.count()
        return len(self._fallback.vectors)

    def clear(self) -> None:
        if self._coll is not None:
            self._client.delete_collection(name=self._collection_name)
            self._coll = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self._fallback.vectors.clear()

    def delete(self, record_id: str) -> bool:
        if self._coll is not None:
            try:
                self._coll.delete(ids=[record_id])
                return True
            except Exception:
                return False
        return self._fallback.delete(record_id)
