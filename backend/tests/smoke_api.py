"""Quick smoke test for API endpoints."""
import urllib.request
import json

BASE = "http://localhost:8000"

# 1. GET /graph
r = urllib.request.urlopen(f"{BASE}/graph")
d = json.loads(r.read())
print(f"GET /graph -> {len(d['nodes'])} nodes, {len(d['edges'])} edges")

# 2. POST /route (Dijkstra)
req = urllib.request.Request(
    f"{BASE}/route",
    data=json.dumps({"source": "1", "destination": "25", "algorithm": "dijkstra"}).encode(),
    headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(f"POST /route (dijkstra) -> path={d['path']}, cost={d['total_cost']}, visited={d['nodes_visited']}")

# 3. POST /route (A*)
req = urllib.request.Request(
    f"{BASE}/route",
    data=json.dumps({"source": "1", "destination": "25", "algorithm": "astar"}).encode(),
    headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(f"POST /route (astar)    -> path={d['path']}, cost={d['total_cost']}, visited={d['nodes_visited']}")

# 4. POST /compare
req = urllib.request.Request(
    f"{BASE}/compare",
    data=json.dumps({"source": "1", "destination": "25"}).encode(),
    headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(f"POST /compare -> dijkstra_cost={d['dijkstra']['total_cost']}, astar_cost={d['astar']['total_cost']}")

# 5. GET /traffic
r = urllib.request.urlopen(f"{BASE}/traffic")
d = json.loads(r.read())
print(f"GET /traffic -> {len(d['edges'])} edges")

# 6. GET /simulation/status
r = urllib.request.urlopen(f"{BASE}/simulation/status")
d = json.loads(r.read())
print(f"GET /simulation/status -> running={d['running']}")

print("\n✅ All API endpoints working!")
