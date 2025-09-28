"""
Knowledge Graph - Represents and reasons about relationships between entities.
"""
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass

@dataclass
class Node:
    """Represents a node in the knowledge graph."""
    id: str
    type: str
    properties: Dict[str, Any]

@dataclass
class Edge:
    """Represents a relationship between nodes in the knowledge graph."""
    source_id: str
    target_id: str
    relationship: str
    properties: Dict[str, Any] = None

class KnowledgeGraph:
    """In-memory knowledge graph implementation."""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.node_edges: Dict[str, List[Edge]] = {}
    
    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any] = None) -> Node:
        """Add a node to the knowledge graph."""
        if node_id in self.nodes:
            # Update existing node
            self.nodes[node_id].properties.update(properties or {})
        else:
            # Create new node
            self.nodes[node_id] = Node(
                id=node_id,
                type=node_type,
                properties=properties or {}
            )
            self.node_edges[node_id] = []
        return self.nodes[node_id]
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any] = None
    ) -> Edge:
        """Add a relationship between two nodes."""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Both source and target nodes must exist")
            
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            properties=properties or {}
        )
        self.edges.append(edge)
        self.node_edges[source_id].append(edge)
        self.node_edges[target_id].append(edge)
        return edge
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_related_nodes(
        self,
        node_id: str,
        relationship: str = None
    ) -> List[Node]:
        """Get nodes related to the given node, optionally filtered by relationship."""
        if node_id not in self.node_edges:
            return []
            
        related_nodes = []
        for edge in self.node_edges[node_id]:
            if relationship is None or edge.relationship == relationship:
                other_id = edge.target_id if edge.source_id == node_id else edge.source_id
                if other_id in self.nodes:
                    related_nodes.append(self.nodes[other_id])
        
        return related_nodes
    
    def query(self, pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query the knowledge graph for nodes matching the given pattern."""
        results = []
        for node in self.nodes.values():
            match = True
            for key, value in pattern.items():
                if key == 'type':
                    if node.type != value:
                        match = False
                        break
                elif key in node.properties:
                    if node.properties[key] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            
            if match:
                results.append({
                    'node': node,
                    'relationships': [
                        {
                            'edge': edge,
                            'direction': 'out' if edge.source_id == node.id else 'in'
                        }
                        for edge in self.node_edges[node.id]
                    ]
                })
        
        return results
