"""
Vector Database - Simple in-memory vector store using list of dicts.
"""

from typing import List, Dict, Any, Optional
import numpy as np


class VectorDB:
    """In-memory vector database using a simple list of dicts."""

    def __init__(self, dim: int = 768):
        self.dim = dim
        self.vectors: List[Dict[str, Any]] = []

    def add(
        self, embedding: List[float], text: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Add a vector record to the store."""
        if len(embedding) != self.dim:
            raise ValueError(f"Embedding dimension must be {self.dim}")

        record_id = f"vec_{len(self.vectors) + 1}"
        record = {
            "id": record_id,
            "embedding": np.array(embedding),
            "text": text,
            "metadata": metadata or {},
        }
        self.vectors.append(record)
        return record_id

    def query(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity."""
        if len(query_embedding) != self.dim:
            raise ValueError(f"Query embedding dimension must be {self.dim}")

        q = np.array(query_embedding)
        q_norm = np.linalg.norm(q)

        results = []
        for record in self.vectors:
            v = record["embedding"]
            similarity = float(np.dot(q, v) / (q_norm * np.linalg.norm(v)))
            results.append((record, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "id": r["id"],
                "embedding": r["embedding"].tolist(),
                "text": r["text"],
                "metadata": r["metadata"],
                "similarity": sim,
            }
            for r, sim in results[:top_k]
        ]

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector record by ID."""
        for record in self.vectors:
            if record["id"] == record_id:
                return record
        return None

    def delete(self, record_id: str) -> bool:
        """Delete a vector record by ID."""
        for i, record in enumerate(self.vectors):
            if record["id"] == record_id:
                self.vectors.pop(i)
                return True
        return False
