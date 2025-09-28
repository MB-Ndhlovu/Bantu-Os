"""
Vector Database - Handles vector embeddings and similarity search.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass

@dataclass
class VectorRecord:
    """Represents a vector record in the database."""
    id: str
    vector: np.ndarray
    metadata: Dict[str, Any]
    text: Optional[str] = None

class VectorDB:
    """In-memory vector database implementation."""
    
    def __init__(self, dim: int = 768):
        """Initialize the vector database with specified dimension size."""
        self.dim = dim
        self.records: Dict[str, VectorRecord] = {}
    
    def add(self, vector: np.ndarray, metadata: Dict[str, Any], text: str = None) -> str:
        """Add a vector to the database."""
        if len(vector) != self.dim:
            raise ValueError(f"Vector dimension must be {self.dim}")
            
        record_id = f"vec_{len(self.records) + 1}"
        self.records[record_id] = VectorRecord(
            id=record_id,
            vector=vector,
            metadata=metadata,
            text=text
        )
        return record_id
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity."""
        if len(query_vector) != self.dim:
            raise ValueError(f"Query vector dimension must be {self.dim}")
        
        # Calculate cosine similarities
        similarities = []
        for record in self.records.values():
            similarity = np.dot(query_vector, record.vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(record.vector)
            )
            similarities.append((record, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        return [
            {
                'id': record.id,
                'similarity': float(similarity),
                'metadata': record.metadata,
                'text': record.text
            }
            for record, similarity in similarities[:top_k]
        ]
    
    def get(self, record_id: str) -> Optional[VectorRecord]:
        """Get a vector record by ID."""
        return self.records.get(record_id)
    
    def delete(self, record_id: str) -> bool:
        """Delete a vector record by ID."""
        if record_id in self.records:
            del self.records[record_id]
            return True
        return False
