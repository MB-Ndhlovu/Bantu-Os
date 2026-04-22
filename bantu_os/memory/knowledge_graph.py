"""
Knowledge Graph for Bantu-OS memory system.
Nodes and edges with optional vector embedding for semantic search.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KGNode:
    id: str
    label: str
    properties: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class KGEdge:
    id: str
    from_id: str
    to_id: str
    relation: str  # e.g. "knows", "part_of", "depends_on"
    properties: dict = field(default_factory=dict)
    weight: float = 1.0


class KnowledgeGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, KGNode] = {}
        self._edges: dict[str, KGEdge] = {}
        self._outgoing: dict[str, list[str]] = {}  # node_id -> list of edge_ids

    def add_node(
        self, id: str, label: str, properties: Optional[dict] = None
    ) -> KGNode:
        node = KGNode(id=id, label=label, properties=properties or {})
        self._nodes[id] = node
        self._outgoing.setdefault(id, [])
        return node

    def add_edge(
        self,
        id: str,
        from_id: str,
        to_id: str,
        relation: str,
        properties: Optional[dict] = None,
        weight: float = 1.0,
    ) -> KGEdge:
        if from_id not in self._nodes or to_id not in self._nodes:
            raise ValueError(f"Both nodes must exist: {from_id}, {to_id}")

        edge = KGEdge(
            id=id,
            from_id=from_id,
            to_id=to_id,
            relation=relation,
            properties=properties or {},
            weight=weight,
        )
        self._edges[id] = edge
        self._outgoing.setdefault(from_id, []).append(id)
        return edge

    def get_node(self, id: str) -> Optional[KGNode]:
        return self._nodes.get(id)

    def get_edges_from(self, node_id: str) -> list[KGEdge]:
        edge_ids = self._outgoing.get(node_id, [])
        return [self._edges[eid] for eid in edge_ids]

    def get_edges_to(self, node_id: str) -> list[KGEdge]:
        return [e for e in self._edges.values() if e.to_id == node_id]

    def traverse(
        self, start_id: str, relation: str, max_depth: int = 3
    ) -> list[KGNode]:
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(start_id, 0)]
        results: list[KGNode] = []

        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)

            node = self._nodes.get(node_id)
            if node:
                results.append(node)

            for edge in self.get_edges_from(node_id):
                if edge.relation == relation or relation == "*":
                    if edge.to_id not in visited:
                        queue.append((edge.to_id, depth + 1))

        return results

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)
