"""
OSM Data Extraction Script — one-time use.

Extracts a small region from OpenStreetMap using osmnx, converts it to
a lightweight JSON format, and saves it to ``backend/data/map.json``.

Usage::

    pip install osmnx
    python extract_osm.py

After extraction, the rest of the system loads ``map.json`` directly
and does NOT depend on osmnx at runtime.

Output schema::

    {
      "metadata": {
        "city": "...",
        "extracted_at": "...",
        "node_count": N,
        "edge_count": M
      },
      "nodes": [
        {"id": "123", "x": 80.27, "y": 13.08},
        ...
      ],
      "edges": [
        {"from_node": "123", "to_node": "456", "base_weight": 142.5},
        ...
      ]
    }

Constraints:
  • Max 200–300 nodes (configurable via MAX_NODES).
  • Edge weight = geometric length in metres.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import osmnx as ox
except ImportError:
    print(
        "ERROR: osmnx is required for extraction.\n"
        "Install it with:  pip install osmnx\n\n"
        "NOTE: osmnx is only needed for this one-time extraction script.\n"
        "The rest of the system uses the generated map.json file."
    )
    sys.exit(1)


# ── Configuration ─────────────────────────────────────────────────────────

# Chennai — T. Nagar area (a dense, well-mapped neighbourhood)
PLACE_NAME = "T. Nagar, Chennai, India"
NETWORK_TYPE = "drive"          # road network for cars
MAX_NODES = 250                 # keep the graph small for the simulation
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "map.json"


def extract_and_save() -> None:
    """Download, simplify, trim, and serialise the road graph."""

    print(f"📡 Downloading road network for: {PLACE_NAME}")
    G = ox.graph_from_place(PLACE_NAME, network_type=NETWORK_TYPE)

    # Simplify topology (merge degree-2 nodes)
    G = ox.simplify_graph(G)

    # Trim to MAX_NODES if necessary
    all_nodes = list(G.nodes)
    if len(all_nodes) > MAX_NODES:
        print(f"⚠  Graph has {len(all_nodes)} nodes — trimming to {MAX_NODES}.")
        keep = set(all_nodes[:MAX_NODES])
        G = G.subgraph(keep).copy()

    # ── Build lightweight JSON ────────────────────────────────────────
    nodes_out: list[dict] = []
    for nid, data in G.nodes(data=True):
        nodes_out.append({
            "id": str(nid),
            "x": round(data["x"], 6),   # longitude
            "y": round(data["y"], 6),    # latitude
        })

    edges_out: list[dict] = []
    for u, v, data in G.edges(data=True):
        length = data.get("length", 1.0)  # metres
        edges_out.append({
            "from_node": str(u),
            "to_node": str(v),
            "base_weight": round(length, 2),
        })

    payload = {
        "metadata": {
            "city": PLACE_NAME,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "node_count": len(nodes_out),
            "edge_count": len(edges_out),
        },
        "nodes": nodes_out,
        "edges": edges_out,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✅ Saved {len(nodes_out)} nodes, {len(edges_out)} edges → {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_and_save()
