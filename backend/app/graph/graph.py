"""
Graph data structure using an adjacency-list representation.

This is the core data structure for the traffic simulation.  All routing
algorithms (Dijkstra, A*) operate directly on this graph.

Design decisions
────────────────
• Adjacency list chosen over matrix — road networks are sparse (E ≈ 2–3 × V).
• Nodes stored in a dict for O(1) lookups by ID.
• Edges stored per-node as a list (append is O(1) amortised).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from .models import Edge, EdgeStatus, Node


class Graph:
    """
    Weighted directed graph with adjacency-list storage.

    Space complexity: O(V + E)

    Attributes:
        _nodes: Mapping from node ID → Node object.
        _adj:   Mapping from node ID → list of outgoing Edge objects.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._adj: dict[str, list[Edge]] = defaultdict(list)

    # ── Mutators ──────────────────────────────────────────────────────────

    def add_node(self, node: Node) -> None:
        """
        Register a node in the graph.

        Time complexity: O(1) average (dict insertion).
        Raises ValueError if a node with the same ID already exists.
        """
        if node.id in self._nodes:
            raise ValueError(f"Node '{node.id}' already exists in the graph.")
        self._nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """
        Add a directed edge to the graph.

        Time complexity: O(1) amortised (list append).
        Raises ValueError if either endpoint node has not been added.
        """
        if edge.from_node not in self._nodes:
            raise ValueError(
                f"Source node '{edge.from_node}' not found. Add it before adding edges."
            )
        if edge.to_node not in self._nodes:
            raise ValueError(
                f"Destination node '{edge.to_node}' not found. Add it before adding edges."
            )
        self._adj[edge.from_node].append(edge)

    # ── Queries ───────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Node | None:
        """
        Return the Node with the given ID, or None.

        Time complexity: O(1) average.
        """
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> list[Edge]:
        """
        Return all outgoing edges from *node_id*.

        Time complexity: O(degree(node_id)).
        Returns an empty list if the node has no outgoing edges.
        Raises ValueError if the node does not exist.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' does not exist in the graph.")
        return list(self._adj[node_id])

    def get_all_nodes(self) -> list[Node]:
        """
        Return every node in the graph.

        Time complexity: O(V).
        """
        return list(self._nodes.values())

    def get_all_edges(self) -> list[Edge]:
        """
        Return every edge in the graph.

        Time complexity: O(V + E) — iterates all adjacency lists.
        """
        edges: list[Edge] = []
        for edge_list in self._adj.values():
            edges.extend(edge_list)
        return edges

    def get_edge(self, from_id: str, to_id: str) -> Edge | None:
        """
        Return the edge from *from_id* → *to_id*, or None.

        Time complexity: O(degree(from_id)).
        """
        for edge in self._adj.get(from_id, []):
            if edge.to_node == to_id:
                return edge
        return None

    @property
    def node_count(self) -> int:
        """Number of nodes.  O(1)."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges.  O(V + E) — counts across all adjacency lists."""
        return sum(len(edges) for edges in self._adj.values())

    # ── Serialisation ─────────────────────────────────────────────────────

    def load_from_json(self, path: str | Path) -> None:
        """
        Populate the graph from a JSON file.

        Expected JSON schema::

            {
              "nodes": [
                {"id": "1", "x": 80.27, "y": 13.08},
                ...
              ],
              "edges": [
                {"from_node": "1", "to_node": "2", "base_weight": 3.5},
                ...
              ]
            }

        Time complexity: O(V + E).
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data: dict = json.load(f)

        for n in data.get("nodes", []):
            self.add_node(Node(
                id=str(n["id"]),
                x=float(n["x"]),
                y=float(n["y"]),
                label=n.get("label", str(n["id"])),
            ))

        for e in data.get("edges", []):
            edge = Edge(
                from_node=str(e["from_node"]),
                to_node=str(e["to_node"]),
                base_weight=float(e["base_weight"]),
            )
            self.add_edge(edge)

    def to_dict(self) -> dict:
        """
        Serialise the graph to a plain dict (JSON-ready).

        Time complexity: O(V + E).
        """
        return {
            "nodes": [
                {"id": n.id, "x": n.x, "y": n.y, "label": n.label or n.id}
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "from_node": e.from_node,
                    "to_node": e.to_node,
                    "base_weight": e.base_weight,
                    "current_weight": e.current_weight,
                    "status": e.status.value,
                }
                for e in self.get_all_edges()
            ],
        }

    # ── Dunder helpers ────────────────────────────────────────────────────

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __repr__(self) -> str:
        return f"Graph(nodes={self.node_count}, edges={self.edge_count})"
