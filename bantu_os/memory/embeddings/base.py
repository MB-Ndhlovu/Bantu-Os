"""
Embeddings provider interfaces.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class EmbeddingsProvider(ABC):
    """Abstract interface for text embeddings."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> np.ndarray:
        """Return an array of shape (len(texts), dim)."""
        raise NotImplementedError
