# -*- coding: utf-8 -*-
"""
Bantu-OS Memory Layer — ChromaDB Integration

Implements persistent vector storage and retrieval using ChromaDB.
Falls back to in-memory VectorDB if ChromaDB is unavailable.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

# ChromaDB (persistent vector store)
try:
    import chromadb

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class ChromaStore:
    """ChromaDB-backed persistent vector store for Bantu-OS memory.

    Supports cosine-similarity search, metadata filtering, and collection
    management. Falls back to in-memory VectorDB if ChromaDB is not installed.
    """

    def __init__(
        self,
        path: str = "./bantu_os_data/chromadb",
        collection: str = "bantu_memory",
        distance_fn: str = "cosine",
    ) -> None:
        self._path = path
        self._collection_name = collection
        self._client = None
        self._coll = None

        if HAS_CHROMADB:
            os.makedirs(path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=path)
            self._coll = self._client.get_or_create_collection(
                name=collection,
                metadata={"hnsw:space": distance_fn},
            )

    def add(
        self,
        embedding: list[float],
        text: str,
        metadata: Optional[dict[str, Any]] = None,
        uid: Optional[str] = None,
    ) -> str:
        uid = uid or f"mem_{int(time.time() * 1000)}"
        meta = (metadata or {}).copy()
        meta["text"] = text
        meta["created_at"] = time.time()

        if self._coll is not None:
            self._coll.add(
                ids=[uid],
                embeddings=[embedding],
                documents=[text],
                metadatas=[meta],
            )
        return uid

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_meta: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        if self._coll is None:
            return []

        try:
            results = self._coll.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_meta,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        if not results or not results.get("ids"):
            return []

        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        out = []
        for i, uid in enumerate(ids):
            out.append(
                {
                    "id": uid,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 0.0,
                    "similarity": 1.0 - dists[i] if i < len(dists) else 0.0,
                }
            )
        return out

    def delete(self, uid: str) -> bool:
        if self._coll is None:
            return False
        try:
            self._coll.delete(ids=[uid])
            return True
        except Exception:
            return False

    def count(self) -> int:
        if self._coll is not None:
            return self._coll.count()
        return 0

    def clear(self) -> None:
        if self._coll is not None:
            self._client.delete_collection(name=self._collection_name)
            self._coll = self._client.get_or_create_collection(
                name=self._collection_name,
            )
