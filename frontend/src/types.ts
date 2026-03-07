/* ── Shared TypeScript types for the Ambulance Dispatch System ── */

export interface GraphNode {
    id: string;
    x: number;
    y: number;
    label: string;
}

export interface GraphEdge {
    from_node: string;
    to_node: string;
    base_weight: number;
    current_weight: number;
    status: "normal" | "congested" | "blocked";
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface PathResult {
    path: string[];
    total_cost: number;
    nodes_visited: number;
    relaxations: number;
    runtime_ms: number;
    algorithm: string;
    found: boolean;
}

export interface TrafficChange {
    from_node: string;
    to_node: string;
    old_weight: number;
    new_weight: number;
    status: string;
}

export interface CompareResult {
    dijkstra: PathResult;
    astar: PathResult;
}

export interface TraceStep {
    type: "visit" | "relax" | "path";
    node?: string;
    from?: string;
    to?: string;
    cost?: number;
    path?: string[];
}

export interface TraceResponse {
    result: PathResult;
    trace: TraceStep[];
}

/* ── Dispatch types ── */

export interface Ambulance {
    id: string;
    name: string;
    location: string;
    status: "available" | "dispatched" | "returning";
}

export interface Hospital {
    id: string;
    name: string;
    location: string;
    capacity: number;
    current_load: number;
    congestion: number;
    available_beds: number;
}

export interface Emergency {
    id: string;
    location: string;
    severity: number;
    timestamp: number;
    assigned: boolean;
}

export interface DispatchResult {
    emergency_id: string;
    ambulance_id: string;
    hospital_id: string;
    algorithm: string;
    path_to_emergency: string[];
    path_to_hospital: string[];
    // Distance in meters
    response_distance_m: number;
    transport_distance_m: number;
    total_distance_m: number;
    // Estimated time in minutes (at 40 km/h)
    response_minutes: number;
    transport_minutes: number;
    total_minutes: number;
    // Algorithm metrics
    nodes_visited: number;
    algorithm_ms: number;
    // Legacy (kept for scoring compatibility)
    response_time: number;
    transport_time: number;
    total_time: number;
}

export interface DispatchState {
    ambulances: Ambulance[];
    hospitals: Hospital[];
    emergencies: Emergency[];
    history: DispatchResult[];
    score: number;
    dispatches: number;
    missed: number;
}

export interface DispatchComparison {
    emergency: Emergency;
    greedy: DispatchResult | null;
    hungarian: DispatchResult | null;
}
