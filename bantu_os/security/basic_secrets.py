"""
Simple in-memory knowledge graph for Bantu-OS.
Nodes and edges stored as dicts. Supports add, query, traverse.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional


class KnowledgeGraph:
    """Simple in-memory knowledge graph with dict-based storage."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, str]] = []

    def add_node(self, label: str, properties: Optional[dict[str, Any]] = None) -> str:
        node_id = str(uuid.uuid4())[:8]
        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "properties": properties or {},
        }
        return node_id

    def add_edge(self, from_id: str, to_id: str, relation: str, properties: Optional[dict[str, Any]] = None) -> Optional[str]:
        if from_id not in self.nodes or to_id not in self.nodes:
            return None
        edge_id = str(uuid.uuid4())[:8]
        self.edges.append({
            "id": edge_id,
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "properties": properties or {},
        })
        return edge_id

    def query(self, label: Optional[str] = None, relation: Optional[str] = None) -> list[dict[str, Any]]:
        results = []
        for node in self.nodes.values():
            if label and node["label"] != label:
                continue
            results.append(node)
        return results

    def traverse(self, from_id: str, depth: int = 1) -> list[dict[str, Any]]:
        if from_id not in self.nodes or depth < 1:
            return []
        visited: set[str] = set()
        queue = [(from_id, 0)]
        results = []

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_id in visited or current_depth > depth:
                continue
            visited.add(current_id)
            if current_id in self.nodes:
                results.append(self.nodes[current_id])
            for edge in self.edges:
                if edge["from"] == current_id and current_depth < depth:
                    queue.append((edge["to"], current_depth + 1))
                    if edge["to"] in self.nodes:
                        results.append(self.nodes[edge["to"]])

        return results

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)


# Default instance
_default_graph: Optional[KnowledgeGraph] = None

def get_graph() -> KnowledgeGraph:
    global _default_graph
    if _default_graph is None:
        _default_graph = KnowledgeGraph()
    return _default_graph

def add_node(label: str, properties: Optional[dict[str, Any]] = None) -> str:
    return get_graph().add_node(label, properties)

def add_edge(from_label: str, to_label: str, relation: str) -> Optional[str]:
    g = get_graph()
    from_nodes = g.query(label=from_label)
    to_nodes = g.query(label=to_label)
    if not from_nodes or not to_nodes:
        return None
    return g.add_edge(from_nodes[0]["id"], to_nodes[0]["id"], relation)

def query(label: Optional[str] = None) -> list[dict[str, Any]]:
    return get_graph().query(label=label)
