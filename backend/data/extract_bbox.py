"""
OSM extraction — pulls street names and creates readable node labels.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import osmnx as ox
import networkx as nx

NORTH = 13.060
SOUTH = 13.030
EAST  = 80.250
WEST  = 80.220
MAX_NODES = 250
OUTPUT = Path(__file__).parent / "map.json"

print("Downloading T. Nagar road network...")
G = ox.graph_from_bbox(bbox=(WEST, SOUTH, EAST, NORTH), network_type="drive")
print(f"  Raw: {len(G.nodes)} nodes, {len(G.edges)} edges")

# Largest strongly connected component
largest_scc = max(nx.strongly_connected_components(G), key=len)
G = G.subgraph(largest_scc).copy()
print(f"  SCC: {len(G.nodes)} nodes, {len(G.edges)} edges")

# BFS trim from center
if len(G.nodes) > MAX_NODES:
    center_lat = (NORTH + SOUTH) / 2
    center_lon = (EAST + WEST) / 2
    best_node = min(G.nodes, key=lambda n: ((G.nodes[n]["y"] - center_lat)**2 + (G.nodes[n]["x"] - center_lon)**2))
    visited = set()
    queue = [best_node]
    while queue and len(visited) < MAX_NODES:
        node = queue.pop(0)
        if node in visited: continue
        visited.add(node)
        for neighbor in G.neighbors(node):
            if neighbor not in visited: queue.append(neighbor)
    G = G.subgraph(visited).copy()
    largest_scc = max(nx.strongly_connected_components(G), key=len)
    G = G.subgraph(largest_scc).copy()
    print(f"  Trimmed SCC: {len(G.nodes)} nodes, {len(G.edges)} edges")

# ── Build street name mapping for nodes ──
# For each node, collect street names from connected edges
node_streets: dict[int, set[str]] = {n: set() for n in G.nodes}
for u, v, data in G.edges(data=True):
    name = data.get("name", "")
    if isinstance(name, list):
        name = name[0] if name else ""
    if name:
        node_streets[u].add(name)
        node_streets[v].add(name)

# Create readable labels
def make_label(nid: int, streets: set[str]) -> str:
    names = sorted(streets)
    if len(names) >= 2:
        # Intersection of two streets
        short = [n.replace(" Road", " Rd").replace(" Street", " St").replace(" Nagar", " Ngr") for n in names[:2]]
        return f"{short[0]} & {short[1]}"
    elif len(names) == 1:
        return names[0].replace(" Road", " Rd").replace(" Street", " St").replace(" Nagar", " Ngr")
    else:
        return f"Junction {str(nid)[-3:]}"

# Assign labels, making them unique
used_labels: dict[str, int] = {}
node_labels: dict[int, str] = {}
for nid in G.nodes:
    label = make_label(nid, node_streets[nid])
    if label in used_labels:
        used_labels[label] += 1
        label = f"{label} #{used_labels[label]}"
    else:
        used_labels[label] = 1
    node_labels[nid] = label

# ── Build JSON ──
nodes_out = []
for nid, data in G.nodes(data=True):
    nodes_out.append({
        "id": str(nid),
        "x": round(data["x"], 6),
        "y": round(data["y"], 6),
        "label": node_labels[nid],
    })

edges_out = []
for u, v, data in G.edges(data=True):
    length = data.get("length", 1.0)
    name = data.get("name", "")
    if isinstance(name, list):
        name = name[0] if name else ""
    edges_out.append({
        "from_node": str(u),
        "to_node": str(v),
        "base_weight": round(float(length), 2),
        "street_name": name,
    })

payload = {
    "metadata": {
        "city": "T. Nagar, Chennai, India",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
        "strongly_connected": True,
    },
    "nodes": nodes_out,
    "edges": edges_out,
}

OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Saved {len(nodes_out)} nodes, {len(edges_out)} edges → {OUTPUT}")

# Show some sample labels
for n in nodes_out[:10]:
    print(f"  {n['id'][-4:]}: {n['label']}")
