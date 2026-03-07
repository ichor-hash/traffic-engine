"""
DAA Project: Optimized Ambulance Dispatch Using Hybrid Greedy + Dijkstra

Algorithm Theory:
1. Why this algorithm is hybrid:
   It combines exact shortest-path graph traversal (Dijkstra) with a Greedy heuristic
   multi-objective scoring approach (evaluated using Min-Heap). It doesn't just look at distance;
   it simultaneously weighs distance, traffic severity, and hospital congestion.

2. Why it performs better than nearest-ambulance baseline:
   The baseline method is naive: it considers spatial distance only. In reality,
   the nearest ambulance could be stuck in dense traffic, or the nearest hospital could
   be overflowing (leading to delayed patient admission). By mathematically balancing 
   these components, the Hybrid method prevents systemic congestion and reduces real-world turnaround time.
"""

import heapq
import random

def build_graph(num_nodes=20, num_edges=35):
    """
    Builds a random city graph represented as an adjacency list.
    V = intersections, E = roads
    Edge weight = travel_time * traffic_factor
    """
    graph = {i: [] for i in range(num_nodes)}
    edges_added = 0
    
    # Create a connected path to ensure all nodes are reachable
    for i in range(num_nodes - 1):
        travel_time = random.uniform(5.0, 15.0)
        traffic_factor = random.uniform(1.0, 2.0)
        weight = travel_time * traffic_factor
        graph[i].append((i+1, weight, travel_time, traffic_factor))
        graph[i+1].append((i, weight, travel_time, traffic_factor))
        edges_added += 1

    # Add remaining extra edges
    while edges_added < num_edges:
        u = random.randint(0, num_nodes - 1)
        v = random.randint(0, num_nodes - 1)
        # Avoid self-loops and duplicate edges
        if u != v and not any(neighbor == v for neighbor, _, _, _ in graph[u]):
            travel_time = random.uniform(5.0, 15.0)
            traffic_factor = random.uniform(1.0, 2.0)
            weight = travel_time * traffic_factor
            graph[u].append((v, weight, travel_time, traffic_factor))
            graph[v].append((u, weight, travel_time, traffic_factor))
            edges_added += 1
            
    return graph

def generate_ambulances(num_ambulances=5, num_nodes=20):
    """
    Generates available ambulances at random intersections.
    """
    ambulances = {}
    for i in range(num_ambulances):
        name = f"A{i+1}"
        # Start at a random node
        location = random.randint(0, num_nodes - 1)
        ambulances[name] = {"location": location, "available": True}
    return ambulances

def generate_hospitals(num_hospitals=3, num_nodes=20):
    """
    Generates hospitals at random locations, tracking capacity and load.
    """
    hospitals = {}
    for i in range(num_hospitals):
        name = f"H{i+1}"
        location = random.randint(0, num_nodes - 1)
        capacity = random.randint(50, 100)
        # Random initial load
        current_load = random.randint(20, capacity) 
        hospitals[name] = {
            "location": location,
            "capacity": capacity,
            "current_load": current_load
        }
    return hospitals

def dijkstra(graph, source):
    """
    Step 1: Dijkstra's algorithm to compute shortest paths.
    Using Priority Queue (heapq)
    Time Complexity: O((V + E) log V)
    Returns: distances and average traffic factors to all nodes
    """
    # Min-heap queue elements: (cumulative_weight, node, cumulative_traffic, edges_traversed)
    queue = [(0, source, 1.0, 0)]
    
    distances = {node: float('inf') for node in graph}
    distances[source] = 0
    
    # We will also compute average traffic to each node for scoring
    node_traffic = {node: 1.0 for node in graph}
    
    while queue:
        curr_weight, u, curr_traffic, edges_count = heapq.heappop(queue)
        
        # If we found a shorter path previously, skip
        if curr_weight > distances[u]:
            continue
            
        for v, weight, travel_time, edge_traffic in graph[u]:
            new_weight = curr_weight + weight
            new_edges = edges_count + 1
            # Moving average of traffic on this route
            new_traffic_avg = ((curr_traffic * edges_count) + edge_traffic) / new_edges
            
            if new_weight < distances[v]:
                distances[v] = new_weight
                node_traffic[v] = new_traffic_avg
                heapq.heappush(queue, (new_weight, v, new_traffic_avg, new_edges))
                
    return distances, node_traffic

def baseline_dispatch(graph, ambulances, hospitals, emergency_loc):
    """
    BASELINE METHOD: Nearest Ambulance Dispatch
    Assigns the ambulance and hospital with the shortest pure distance.
    Ignores traffic variants and hospital capacities.
    """
    distances, _ = dijkstra(graph, emergency_loc)
    
    # 1. Find nearest ambulance
    best_amb = None
    min_dist = float('inf')
    for a_name, a_data in ambulances.items():
        if a_data["available"]:
            dist = distances[a_data["location"]]
            if dist < min_dist:
                min_dist = dist
                best_amb = a_name
                
    # 2. Find nearest hospital
    best_hosp = None
    min_hosp_dist = float('inf')
    for h_name, h_data in hospitals.items():
        dist = distances[h_data["location"]]
        if dist < min_hosp_dist:
            min_hosp_dist = dist
            best_hosp = h_name
            
    return best_amb, min_dist, best_hosp, distances

def hybrid_dispatch(graph, ambulances, hospitals, emergency_loc):
    """
    PROPOSED HYBRID METHOD:
    Computes a composite score using Dijkstra + Greedy heuristics.
    Parameters (Alpha, Beta, Gamma) balance distance, traffic congestion, and hospital loads.
    """
    alpha = 0.5 # Weight for distance
    beta = 0.3  # Weight for route traffic
    gamma = 0.2 # Weight for hospital load
    
    distances, traffic_factors = dijkstra(graph, emergency_loc)
    
    # Step 2 & 3: Score Hospitals based on distance AND congestion
    best_hosp = None
    best_hosp_score = float('inf')
    assigned_hosp_congestion = 0.0
    
    for h_name, h_data in hospitals.items():
        dist = distances[h_data["location"]]
        congestion = h_data["current_load"] / h_data["capacity"]
        
        # Normalize distance (assuming max expected approx 100)
        norm_dist = min(dist / 100.0, 1.0)
        
        # Hospital score heavily relies on capacity constraints + distance
        h_score = (alpha * norm_dist) + (gamma * congestion)
        
        if h_score < best_hosp_score:
            best_hosp_score = h_score
            best_hosp = h_name
            assigned_hosp_congestion = congestion
            
    # Step 4: Compute composite score for Ambulances
    amb_scores = [] # Min-Heap
    recorded_scores = {}
    
    for a_name, a_data in ambulances.items():
        if a_data["available"]:
            dist = distances[a_data["location"]]
            route_traffic = traffic_factors[a_data["location"]]
            
            # Normalization heuristics
            norm_dist = min(dist / 100.0, 1.0)
            norm_traffic = route_traffic - 1.0 # Traffic scales 1.0 -> 2.0, map to 0 -> 1.0
            
            # Composite calculation
            score = (alpha * norm_dist) + (beta * norm_traffic) + (gamma * assigned_hosp_congestion)
            recorded_scores[a_name] = score
            
            # Step 5: Insert into Heap
            heapq.heappush(amb_scores, (score, a_name, dist))
            
    # Pop best option
    best_score, selected_amb, response_time = heapq.heappop(amb_scores)
    
    return selected_amb, response_time, best_hosp, recorded_scores

def simulate_emergency(num_nodes):
    """Generates random emergency locus."""
    return random.randint(0, num_nodes - 1)

def compare_results():
    """Main execution orchestrating algorithm showcase."""
    # SETTINGS
    num_nodes = 20
    num_edges = 35
    
    # INITIALIZATION
    graph = build_graph(num_nodes, num_edges)
    ambulances = generate_ambulances(5, num_nodes)
    hospitals = generate_hospitals(3, num_nodes)
    emergency_loc = simulate_emergency(num_nodes)
    
    # 1) BASELINE DISPATCH
    b_amb, b_time, b_hosp, distances = baseline_dispatch(graph, ambulances, hospitals, emergency_loc)
    
    # 2) HYBRID DISPATCH
    h_amb, h_time, h_hosp, h_scores = hybrid_dispatch(graph, ambulances, hospitals, emergency_loc)

    # --- CLI DEMONSTRATION OUTPUT FORMAT ---
    print("--- CITY GRAPH ---")
    print(f"Total Nodes: {num_nodes}")
    real_edges = sum(len(neighbors) for neighbors in graph.values()) // 2
    print(f"Total Edges: {real_edges}\n")
    
    print("--- AMBULANCES ---")
    for a_name, a_data in ambulances.items():
        print(f"{a_name} \u2192 Node {a_data['location']}")
    print()
    
    print("--- HOSPITALS ---")
    for h_name, h_data in hospitals.items():
        print(f"{h_name} \u2192 Node {h_data['location']} | Load: {h_data['current_load']}/{h_data['capacity']}")
    print()
    
    print("--- EMERGENCY ---")
    print(f"Location: Node {emergency_loc}\n")
    
    print("--- BASELINE RESULT ---")
    print(f"Selected Ambulance: {b_amb}")
    print(f"Distance: {b_time:.2f}")
    print(f"Assigned Hospital: {b_hosp}\n")
    
    print("--- HYBRID ALGORITHM RESULT ---")
    print("Ambulance Scores (Lower is Better):")
    # Sort for cleaner display
    for a_name, score in sorted(h_scores.items(), key=lambda item: item[1]):
        print(f"{a_name} Score: {score:.4f}")
    print()
    print(f"Selected Ambulance: {h_amb}")
    print(f"Response Time: {h_time:.2f}")
    print(f"Assigned Hospital: {h_hosp}\n")
    
    print("--- COMPARISON ---")
    print(f"Baseline Response Time: {b_time:.2f}")
    print(f"Proposed Response Time: {h_time:.2f}\n")
    
    b_h_data = hospitals[b_hosp]
    h_h_data = hospitals[h_hosp]
    print("Hospital Load Impact:")
    print(f"- Baseline forced to {b_hosp} (Load: {b_h_data['current_load']}/{b_h_data['capacity']} "
          f"-> {(b_h_data['current_load']/b_h_data['capacity'])*100:.1f}%)")
    print(f"- Hybrid deferred to {h_hosp} (Load: {h_h_data['current_load']}/{h_h_data['capacity']} "
          f"-> {(h_h_data['current_load']/h_h_data['capacity'])*100:.1f}%)")
    print()
    
    print("--- ANALYSIS SECTION ---")
    print("Time Complexity Explanation:")
    print("  Dijkstra's (with heapq): O((V + E) log V)")
    print("  Baseline dispatch:       O(A) for nearest ambulance + O(H) for nearest hospital.")
    print("  Hybrid dispatch:         O(H) hospital scoring + O(A log A) ambulance heap insertion/extraction.")
    print("  Total Time Complexity:   O((V + E) log V + A log A), optimized for real-time live routing.\n")
    
    print("Space Complexity Explanation:")
    print("  Graph (Adjacency List):  O(V + E) structure.")
    print("  Algorithmic Tracking:    O(V) for distances Dictionary and Priority Queue size.")
    print("  Total Space Complexity:  O(V + E), easily scales to large national map grids.")

if __name__ == "__main__":
    compare_results()
