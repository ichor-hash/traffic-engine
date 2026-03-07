import urllib.request, json

BASE = "http://localhost:8000"

# Get graph to find valid node IDs
r = urllib.request.urlopen(f"{BASE}/graph")
d = json.loads(r.read())
print(f"Graph: {len(d['nodes'])} nodes, {len(d['edges'])} edges")

n1 = d["nodes"][0]["id"]
n2 = d["nodes"][-1]["id"]
print(f"Testing route: {n1} -> {n2}")

# Compute route
req = urllib.request.Request(
    f"{BASE}/route",
    data=json.dumps({"source": n1, "destination": n2, "algorithm": "dijkstra"}).encode(),
    headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
result = json.loads(r.read())
print(f"Found: {result['found']}")
print(f"Path length: {len(result['path'])} nodes")
print(f"Cost: {result['total_cost']}")
print(f"Path: {' -> '.join(result['path'][:5])}{'...' if len(result['path']) > 5 else ''}")
