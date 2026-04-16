"""
Tests for memory/chroma_store.py — ChromaStore with fallback.
"""
import pytest
import time
from unittest.mock import patch, MagicMock


class TestChromaStore:
    """ChromaStore unit tests."""

    def test_add_returns_uid(self):
        """add() returns a uid string."""
        from bantu_os.memory.chroma_store import ChromaStore
        store = ChromaStore()
        uid = store.add([0.1] * 768, "hello world")
        assert isinstance(uid, str)
        assert uid.startswith("mem_")

    def test_query_returns_list(self):
        """query() returns a list of results."""
        from bantu_os.memory.chroma_store import ChromaStore
        store = ChromaStore()
        results = store.query([0.1] * 768, top_k=3)
        assert isinstance(results, list)

    def test_delete_returns_bool(self):
        """delete() returns True on success or False when not available."""
        from bantu_os.memory.chroma_store import ChromaStore
        store = ChromaStore()
        uid = store.add([0.1] * 768, "to be deleted")
        # Returns True if ChromaDB available and delete succeeds, False otherwise
        result = store.delete(uid)
        assert isinstance(result, bool)

    def test_count(self):
        """count() returns int."""
        from bantu_os.memory.chroma_store import ChromaStore
        store = ChromaStore()
        assert isinstance(store.count(), int)

    def test_fallback_when_no_chromadb(self):
        """Store still works (in fallback mode) when ChromaDB is not installed."""
        from bantu_os.memory.chroma_store import ChromaStore, HAS_CHROMADB
        with patch("bantu_os.memory.chroma_store.HAS_CHROMADB", False):
            store = ChromaStore()
            uid = store.add([0.1] * 768, "fallback test")
            assert uid.startswith("mem_")
            assert store.count() == 0  # no ChromaDB, returns 0
