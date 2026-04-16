"""
Tests for memory/vector_db.py — VectorDB.
"""
from __future__ import annotations

import pytest
import numpy as np
from bantu_os.memory.vector_db import VectorDB


class TestVectorDB:
    @pytest.fixture
    def vdb(self) -> VectorDB:
        return VectorDB(dim=4)

    def test_add_vector(self, vdb: VectorDB):
        vec = [0.1, 0.2, 0.3, 0.4]
        record_id = vdb.add(vec, "hello world", {"source": "test"})
        assert record_id == "vec_1"
        assert vdb.get(record_id)["text"] == "hello world"

    def test_add_wrong_dimension_raises(self, vdb: VectorDB):
        with pytest.raises(ValueError):
            vdb.add([0.1, 0.2], "short vector")

    def test_query_returns_top_k(self, vdb: VectorDB):
        vdb.add([1.0, 0.0, 0.0, 0.0], "exact x")
        vdb.add([0.0, 1.0, 0.0, 0.0], "exact y")
        vdb.add([0.9, 0.1, 0.0, 0.0], "near x")

        results = vdb.query([1.0, 0.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "vec_1"  # exact x is closest

    def test_query_wrong_dimension_raises(self, vdb: VectorDB):
        with pytest.raises(ValueError):
            vdb.query([1.0, 2.0], top_k=1)

    def test_get_existing(self, vdb: VectorDB):
        vec = [0.1, 0.2, 0.3, 0.4]
        rid = vdb.add(vec, "test")
        record = vdb.get(rid)
        assert record is not None
        assert record["text"] == "test"

    def test_get_unknown(self, vdb: VectorDB):
        assert vdb.get("ghost") is None

    def test_delete_existing(self, vdb: VectorDB):
        vec = [0.1, 0.2, 0.3, 0.4]
        rid = vdb.add(vec, "todelete")
        assert vdb.delete(rid) is True
        assert vdb.get(rid) is None

    def test_delete_unknown(self, vdb: VectorDB):
        assert vdb.delete("ghost") is False

    def test_empty_query(self, vdb: VectorDB):
        results = vdb.query([0.1, 0.2, 0.3, 0.4], top_k=5)
        assert results == []