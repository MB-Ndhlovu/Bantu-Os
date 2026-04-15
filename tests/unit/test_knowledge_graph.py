"""
Tests for memory/knowledge_graph.py — KnowledgeGraph, Node, and Edge.
"""
from __future__ import annotations

import pytest
from bantu_os.memory.knowledge_graph import KnowledgeGraph, Node, Edge


class TestNode:
    def test_dataclass_fields(self):
        node = Node(id="n1", type="person", properties={"name": "Alice"})
        assert node.id == "n1"
        assert node.type == "person"
        assert node.properties == {"name": "Alice"}


class TestEdge:
    def test_dataclass_fields(self):
        edge = Edge(source_id="a", target_id="b", relationship="knows", properties={"since": 2020})
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.relationship == "knows"
        assert edge.properties == {"since": 2020}

    def test_default_properties(self):
        edge = Edge(source_id="a", target_id="b", relationship="links")
        assert edge.properties is None


class TestKnowledgeGraph:
    @pytest.fixture
    def kg(self) -> KnowledgeGraph:
        return KnowledgeGraph()

    def test_init_empty(self, kg: KnowledgeGraph):
        assert kg.nodes == {}
        assert kg.edges == []
        assert kg.node_edges == {}

    def test_add_node_creates_new(self, kg: KnowledgeGraph):
        node = kg.add_node("n1", "person", {"name": "Bob"})
        assert node.id == "n1"
        assert node.type == "person"
        assert node.properties == {"name": "Bob"}
        assert "n1" in kg.nodes

    def test_add_node_updates_existing(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {"a": 1})
        node = kg.add_node("n1", "person", {"b": 2})
        assert kg.nodes["n1"].properties == {"a": 1, "b": 2}

    def test_add_edge_requires_nodes_exist(self, kg: KnowledgeGraph):
        kg.add_node("n1", "thing", {})
        with pytest.raises(ValueError, match="Both source and target nodes must exist"):
            kg.add_edge("n1", "n2", "relates")

    def test_add_edge_inserts_edge(self, kg: KnowledgeGraph):
        kg.add_node("a", "cat", {})
        kg.add_node("b", "dog", {})
        edge = kg.add_edge("a", "b", "plays_with", {"context": "park"})
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.relationship == "plays_with"
        assert len(kg.edges) == 1

    def test_add_edge_appears_in_node_edges(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_edge("a", "b", "connects")
        assert len(kg.node_edges["a"]) == 1
        assert len(kg.node_edges["b"]) == 1

    def test_get_node_returns_node(self, kg: KnowledgeGraph):
        kg.add_node("n1", "thing", {"k": "v"})
        node = kg.get_node("n1")
        assert node is not None
        assert node.id == "n1"

    def test_get_node_unknown_returns_none(self, kg: KnowledgeGraph):
        assert kg.get_node("nonexistent") is None

    def test_get_related_nodes_no_filter(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_node("c", "z", {})
        kg.add_edge("a", "b", "links")
        kg.add_edge("a", "c", "connects")
        related = kg.get_related_nodes("a")
        assert len(related) == 2

    def test_get_related_nodes_filter_by_relationship(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_node("c", "z", {})
        kg.add_edge("a", "b", "relates")
        kg.add_edge("a", "c", "different")
        related = kg.get_related_nodes("a", relationship="relates")
        assert len(related) == 1
        assert related[0].id == "b"

    def test_get_related_nodes_unknown_node_returns_empty(self, kg: KnowledgeGraph):
        assert kg.get_related_nodes("ghost") == []

    def test_query_by_type(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {})
        kg.add_node("n2", "place", {})
        kg.add_node("n3", "person", {})
        results = kg.query({"type": "person"})
        assert len(results) == 2

    def test_query_by_property(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {"age": 25})
        kg.add_node("n2", "person", {"age": 30})
        kg.add_node("n3", "place", {"age": 100})
        results = kg.query({"age": 25})
        assert len(results) == 1
        assert results[0]["node"].id == "n1"

    def test_query_returns_relationships_in_result(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_edge("a", "b", "links")
        results = kg.query({"id": "a"})
        assert len(results) == 1
        rels = results[0]["relationships"]
        assert len(rels) == 1
        assert rels[0]["edge"].relationship == "links"

    def test_query_no_match(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {})
        results = kg.query({"type": "animal"})
        assert results == []

    def test_query_unknown_property_key(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {"name": "Alice"})
        results = kg.query({"unknown_key": "val"})
        assert results == []