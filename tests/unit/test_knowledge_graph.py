"""
Tests for memory/knowledge_graph.py — KnowledgeGraph, KGNode, KGEdge.
"""

from __future__ import annotations

import pytest

from bantu_os.memory.knowledge_graph import KGEdge, KGNode, KnowledgeGraph


class TestKGNode:
    def test_dataclass_fields(self):
        node = KGNode(id="n1", label="person", properties={"name": "Alice"})
        assert node.id == "n1"
        assert node.label == "person"
        assert node.properties == {"name": "Alice"}

    def test_default_properties(self):
        node = KGNode(id="n1", label="thing")
        assert node.properties == {}


class TestKGEdge:
    def test_dataclass_fields(self):
        edge = KGEdge(
            id="e1",
            from_id="a",
            to_id="b",
            relation="knows",
            properties={"since": 2020},
        )
        assert edge.from_id == "a"
        assert edge.to_id == "b"
        assert edge.relation == "knows"
        assert edge.properties == {"since": 2020}

    def test_default_weight(self):
        edge = KGEdge(id="e1", from_id="a", to_id="b", relation="links")
        assert edge.weight == 1.0


class TestKnowledgeGraph:
    @pytest.fixture
    def kg(self) -> KnowledgeGraph:
        return KnowledgeGraph()

    def test_init_empty(self, kg: KnowledgeGraph):
        assert kg.node_count() == 0
        assert kg.edge_count() == 0

    def test_add_node(self, kg: KnowledgeGraph):
        node = kg.add_node("n1", "person", {"name": "Bob"})
        assert node.id == "n1"
        assert node.label == "person"
        assert kg.node_count() == 1

    def test_add_edge_requires_nodes(self, kg: KnowledgeGraph):
        kg.add_node("n1", "thing", {})
        with pytest.raises(ValueError):
            kg.add_edge("e1", "n1", "n2", "relates")

    def test_add_edge(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        edge = kg.add_edge("e1", "a", "b", "connects")
        assert edge.from_id == "a"
        assert edge.to_id == "b"
        assert kg.edge_count() == 1

    def test_get_node(self, kg: KnowledgeGraph):
        kg.add_node("n1", "person", {})
        node = kg.get_node("n1")
        assert node is not None
        assert node.id == "n1"

    def test_get_node_unknown(self, kg: KnowledgeGraph):
        assert kg.get_node("nonexistent") is None

    def test_get_edges_from(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_node("c", "z", {})
        kg.add_edge("e1", "a", "b", "links")
        kg.add_edge("e2", "a", "c", "connects")
        edges = kg.get_edges_from("a")
        assert len(edges) == 2

    def test_get_edges_to(self, kg: KnowledgeGraph):
        kg.add_node("a", "x", {})
        kg.add_node("b", "y", {})
        kg.add_edge("e1", "a", "b", "links")
        edges = kg.get_edges_to("b")
        assert len(edges) == 1
        assert edges[0].from_id == "a"

    def test_traverse_bfs(self, kg: KnowledgeGraph):
        kg.add_node("root", "x", {})
        kg.add_node("child1", "y", {})
        kg.add_node("child2", "z", {})
        kg.add_node("grandchild", "w", {})
        kg.add_edge("e1", "root", "child1", "has")
        kg.add_edge("e2", "child1", "grandchild", "has")
        kg.add_edge("e3", "root", "child2", "has")

        results = kg.traverse("root", "has", max_depth=2)
        ids = {r.id for r in results}
        assert "child1" in ids
        assert "child2" in ids
        assert "grandchild" in ids
