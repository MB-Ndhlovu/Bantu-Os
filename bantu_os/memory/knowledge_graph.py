# SPDX-License-Identifier: MIT
# Bantu-OS Memory Module — Knowledge Graph
# Simple dict-based graph: add_node(), add_edge(), query()

from typing import Dict, List, Any, Optional


class KnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def add_node(
        self,
        node_id: str,
        node_type: str = None,
        properties: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        props = properties or {}
        if node_type is not None:
            props = {**props, _node_type_key(): node_type}

        if node_id in self.nodes:
            self.nodes[node_id].update(props)
        else:
            self.nodes[node_id] = props

        return self.nodes[node_id]

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        if source_id not in self.nodes:
            raise ValueError(f'Node not found: {source_id}')
        if target_id not in self.nodes:
            raise ValueError(f'Node not found: {target_id}')

        edge = {
            _src_key(): source_id,
            _tgt_key(): target_id,
            _rel_key(): relationship,
            **(properties or {}),
        }
        self.edges.append(edge)
        return edge

    def query(
        self,
        node_type: str = None,
        relationship: str = None,
        direction: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = []
        for edge in self.edges:
            if relationship and edge.get(_rel_key()) != relationship:
                continue

            src = edge.get(_src_key())
            tgt = edge.get(_tgt_key())

            if direction == _dir_out():
                node_id = src
            elif direction == _dir_in():
                node_id = tgt
            else:
                node_id = src

            if node_id not in self.nodes:
                continue

            node_props = self.nodes[node_id]
            if node_type and node_props.get(_node_type_key()) != node_type:
                continue

            results.append({
                **node_props,
                _node_id_key(): node_id,
                _edge_key(): edge,
            })

            if len(results) >= limit:
                break

        return results


# Module-level key constants
def _node_id_key() -> str:
    return 'node_id'


def _node_type_key() -> str:
    return 'node_type'


def _src_key() -> str:
    return 'source_id'


def _tgt_key() -> str:
    return 'target_id'


def _rel_key() -> str:
    return 'relationship'


def _edge_key() -> str:
    return 'edge'


def _dir_out() -> str:
    return 'out'


def _dir_in() -> str:
    return 'in'