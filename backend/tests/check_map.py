import json
d = json.loads(open("data/map.json").read())
m = d["metadata"]
print(f"Nodes: {m['node_count']}")
print(f"Edges: {m['edge_count']}")
print(f"Strongly connected: {m.get('strongly_connected')}")
# Test route between first and last node
n1 = d["nodes"][0]["id"]
n2 = d["nodes"][-1]["id"]
print(f"Sample nodes: {n1} -> {n2}")
