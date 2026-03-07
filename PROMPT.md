You are a senior software architect and algorithm specialist.



We are building a full-stack academic project titled:



"Dynamic Traffic Simulation and Real-Time Route Optimization Using Graph Algorithms"



This is a DAA-focused system.

Routing logic must be fully implemented manually.

Do NOT use NetworkX shortest\_path or built-in routing functions.



====================================================

TECH STACK

====================================================



Backend:

\- Python 3.11

\- FastAPI

\- WebSockets

\- heapq (priority queue)

\- JSON-based map data



Frontend:

\- React + TypeScript

\- Vite

\- Canvas rendering



Architecture must be modular and clean.



====================================================

PROJECT OBJECTIVE

====================================================



Build a simulated real-time traffic system where:



1\. A real city map is extracted from OpenStreetMap once and stored as JSON.

2\. The system loads this city topology.

3\. A traffic simulation engine dynamically changes edge weights.

4\. Dijkstra and A\* recompute shortest path in real time.

5\. Only recompute if affected edges lie in the current path.

6\. Display performance metrics.



====================================================

PHASED DEVELOPMENT — BUILD STEP BY STEP

====================================================



Do NOT generate entire project at once.

Proceed phase-by-phase.

Wait for confirmation before next phase.



====================================================

PHASE 1 — GRAPH DATA STRUCTURE

====================================================



Create:



backend/app/graph/



Implement:



1\. Node class:

&nbsp;  - id

&nbsp;  - x

&nbsp;  - y



2\. Edge class:

&nbsp;  - from\_node

&nbsp;  - to\_node

&nbsp;  - base\_weight

&nbsp;  - current\_weight

&nbsp;  - status (normal | congested | blocked)



3\. Graph class:

&nbsp;  - adjacency list representation

&nbsp;  - add\_node()

&nbsp;  - add\_edge()

&nbsp;  - get\_neighbors()



Include:

\- Type hints

\- Docstrings

\- Time complexity comments



====================================================

PHASE 2 — SHORTEST PATH ALGORITHMS

====================================================



Create:



backend/app/algorithms/



Implement manually:



A. Dijkstra:

\- Use heapq

\- Track:

&nbsp;   - visited\_nodes

&nbsp;   - relaxations

&nbsp;   - runtime

\- Return:

&nbsp;   {

&nbsp;     path,

&nbsp;     total\_cost,

&nbsp;     nodes\_visited,

&nbsp;     runtime

&nbsp;   }



B. A\*:

\- Use Euclidean distance heuristic

\- Same metrics

\- Heuristic must be admissible



Include complexity comments:

\- O((V+E) log V)



====================================================

PHASE 3 — OSM DATA EXTRACTION SCRIPT

====================================================



Create:



backend/data/extract\_osm.py



Requirements:

\- Use osmnx only for extraction

\- Extract small region (max 200–300 nodes)

\- Convert to lightweight JSON:

&nbsp;   {

&nbsp;     nodes: \[],

&nbsp;     edges: \[]

&nbsp;   }

\- Store only:

&nbsp;   id, x, y, base\_weight



After extraction, system must NOT depend on osmnx.



====================================================

PHASE 4 — TRAFFIC SIMULATION ENGINE

====================================================



Create:



backend/app/simulation/



Implement:



TrafficEngine class:

\- Runs in background thread

\- Every N seconds:

&nbsp;   - Randomly select edges

&nbsp;   - Apply:

&nbsp;       - Congestion (weight multiplier 1.5–3)

&nbsp;       - Accident (weight = infinity)

&nbsp;       - Recovery (gradual return to base\_weight)



Rules:

\- Modify only current\_weight

\- Do NOT recreate graph

\- Emit event when edges change



Add logic:

\- If changed edge is in current path → trigger recompute

\- Otherwise ignore



====================================================

PHASE 5 — ROUTING SERVICE

====================================================



Create:



backend/app/services/routing\_service.py



Responsibilities:

\- Accept source, destination, algorithm

\- Run Dijkstra or A\*

\- Store current active path

\- Expose recompute() method



====================================================

PHASE 6 — FASTAPI LAYER

====================================================



Create:



backend/app/api/



Endpoints:



POST /route

{

&nbsp; source,

&nbsp; destination,

&nbsp; algorithm

}



GET /traffic



WebSocket /updates

\- Push traffic changes

\- Push path updates if recomputed



====================================================

PHASE 7 — FRONTEND

====================================================



React + TypeScript.



Create:



GraphCanvas.tsx

\- Draw nodes

\- Draw edges

\- Color edges:

&nbsp;   Green → normal

&nbsp;   Red → congested

&nbsp;   Black → blocked

\- Highlight shortest path



ControlPanel.tsx

\- Select source

\- Select destination

\- Choose algorithm

\- Start / Stop simulation



MetricsPanel.tsx

\- Display:

&nbsp;   - runtime

&nbsp;   - nodes visited

&nbsp;   - total cost



Use WebSocket to receive live updates.



====================================================

PERFORMANCE MODE

====================================================



Add experimental mode:

\- Increase congestion frequency

\- Compare Dijkstra vs A\*

\- Display:

&nbsp;   - Runtime difference

&nbsp;   - Node expansion difference



====================================================

CODE STYLE RULES

====================================================



\- Modular separation

\- No global state

\- Clean dependency injection

\- Type hints everywhere

\- Docstrings for all classes

\- Complexity analysis in algorithm files

\- Do not over-engineer



====================================================

IMPORTANT CONSTRAINTS

====================================================



\- No built-in shortest path libraries

\- No paid APIs

\- Map data must be lightweight

\- Graph size must stay below 300 nodes

\- Recompute only when necessary



====================================================



Start with:



PHASE 1 — Implement Node, Edge, Graph classes with adjacency list.



Do not continue to next phase until I confirm.



