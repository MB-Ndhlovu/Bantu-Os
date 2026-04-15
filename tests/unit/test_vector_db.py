"""
Tests for memory/vector_db.py — VectorDB and VectorRecord.
"""
from __future__ import annotations

import pytest
import numpy as np
from bantu_os.memory.vector_db import VectorDB, VectorRecord


class TestVectorRecord:
    def test_dataclass_fields(self):
        rec = VectorRecord(
            id="test_1",
            vector=np.array([0.1, 0.2, 0.3]),
            metadata={"key": "value"},
            text="sample text",
        )
        assert rec.id == "test_1"
        assert isinstance(rec.vector, np.ndarray)
        assert rec.metadata == {"key": "value"}
        assert rec.text == "sample text"


class TestVectorDB:
    @pytest.fixture
    def vdb(self) -> VectorDB:
        return VectorDB(dim=4)

    def test_init_sets_dim(self, vdb: VectorDB):
        assert vdb.dim == 4
        assert vdb.records == {}

    def test_add_inserts_record(self, vdb: VectorDB):
        vec = np.array([0.1, 0.2, 0.3, 0.4])
        record_id = vdb.add(vec, {"source": "test"}, "hello")
        assert record_id.startswith("vec_")
        assert record_id in vdb.records

    def test_add_wrong_dimension_raises(self, vdb: VectorDB):
        with pytest.raises(ValueError, match="Vector dimension must be"):
            vdb.add(np.array([0.1, 0.2]), {"x": 1}, None)

    def test_add_multiple_records_unique_ids(self, vdb: VectorDB):
        vec = np.array([0.1, 0.2, 0.3, 0.4])
        ids = [vdb.add(vec, {}, None) for _ in range(5)]
        assert len(set(ids)) == 5

    def test_get_returns_record(self, vdb: VectorDB):
        vec = np.array([0.1, 0.2, 0.3, 0.4])
        record_id = vdb.add(vec, {"k": 1}, "text")
        record = vdb.get(record_id)
        assert record is not None
        assert record.id == record_id
        assert record.metadata == {"k": 1}

    def test_get_unknown_id_returns_none(self, vdb: VectorDB):
        assert vdb.get("nonexistent") is None

    def test_delete_removes_record(self, vdb: VectorDB):
        vec = np.array([0.1, 0.2, 0.3, 0.4])
        record_id = vdb.add(vec, {}, None)
        assert vdb.delete(record_id) is True
        assert vdb.get(record_id) is None

    def test_delete_unknown_id_returns_false(self, vdb: VectorDB):
        assert vdb.delete("nonexistent") is False

    def test_search_returns_sorted_results(self, vdb: VectorDB):
        vec1 = np.array([1.0, 0.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0, 0.0])
        vdb.add(vec1, {"id": 1}, "one")
        vdb.add(vec2, {"id": 2}, "two")
        query = np.array([0.9, 0.1, 0.0, 0.0])
        results = vdb.search(query, top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "vec_1"
        assert results[0]["similarity"] >= results[1]["similarity"]

    def test_search_wrong_dimension_raises(self, vdb: VectorDB):
        with pytest.raises(ValueError, match="Query vector dimension must be"):
            vdb.search(np.array([0.1, 0.2]), top_k=5)

    def test_search_respects_top_k(self, vdb: VectorDB):
        vec = np.array([0.5, 0.5, 0.5, 0.5])
        for _ in range(10):
            vdb.add(vec, {}, None)
        results = vdb.search(vec, top_k=3)
        assert len(results) == 3

    def test_search_empty_db_returns_empty(self, vdb: VectorDB):
        results = vdb.search(np.array([0.1, 0.2, 0.3, 0.4]), top_k=5)
        assert results == []

    def test_search_includes_metadata_and_text(self, vdb: VectorDB):
        vec = np.array([0.1, 0.2, 0.3, 0.4])
        vdb.add(vec, {"meta_key": "meta_val"}, "stored text")
        results = vdb.search(vec, top_k=1)
        assert results[0]["metadata"] == {"meta_key": "meta_val"}
        assert results[0]["text"] == "stored text"