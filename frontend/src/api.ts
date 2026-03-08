/* ── API service layer — all backend communication ── */

import type {
    GraphData, PathResult, CompareResult, TraceResponse,
    DispatchState, DispatchResult, DispatchComparison, Emergency,
} from "./types";

const BASE = "";

/* ── Graph & Routing ── */

export async function fetchGraph(): Promise<GraphData> {
    const res = await fetch(`${BASE}/graph`);
    return res.json();
}

export async function computeRoute(
    source: string,
    destination: string,
    algorithm: string
): Promise<PathResult> {
    const res = await fetch(`${BASE}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, destination, algorithm }),
    });
    return res.json();
}

export async function compareAlgorithms(
    source: string,
    destination: string
): Promise<CompareResult> {
    const res = await fetch(`${BASE}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, destination }),
    });
    return res.json();
}

export async function fetchTraffic(): Promise<{ edges: GraphData["edges"] }> {
    const res = await fetch(`${BASE}/traffic`);
    return res.json();
}

export async function startSimulation(): Promise<void> {
    await fetch(`${BASE}/simulation/start`, { method: "POST" });
}

export async function stopSimulation(): Promise<void> {
    await fetch(`${BASE}/simulation/stop`, { method: "POST" });
}

export async function setSimulationSpeed(tickInterval: number): Promise<void> {
    await fetch(`${BASE}/simulation/speed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tick_interval: tickInterval }),
    });
}

export async function computeRouteTrace(
    source: string,
    destination: string,
    algorithm: string
): Promise<TraceResponse> {
    const res = await fetch(`${BASE}/route/trace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, destination, algorithm }),
    });
    return res.json();
}

/* ── Dispatch ── */

export async function fetchDispatchState(): Promise<DispatchState> {
    const res = await fetch(`${BASE}/dispatch/state`);
    return res.json();
}

export async function triggerEmergency(): Promise<Emergency> {
    const res = await fetch(`${BASE}/dispatch/emergency`, { method: "POST" });
    return res.json();
}

export async function dispatchAssign(
    algorithm: string,
    emergencyId?: string
): Promise<{ assignments: DispatchResult[] }> {
    const res = await fetch(`${BASE}/dispatch/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ algorithm, emergency_id: emergencyId }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Dispatch failed");
    }
    return res.json();
}

export async function dispatchCompare(
    emergencyId?: string
): Promise<DispatchComparison> {
    const res = await fetch(`${BASE}/dispatch/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emergency_id: emergencyId }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Comparison failed");
    }
    return res.json();
}

export async function resetDispatch(): Promise<void> {
    await fetch(`${BASE}/dispatch/reset`, { method: "POST" });
}

/* ── WebSocket ── */

export function createUpdateSocket(
    onTrafficUpdate: (changes: any[], timeOfDay?: string) => void,
    onRouteUpdate: (result: PathResult) => void,
    onEmergencyNew?: (data: any) => void,
    onDispatchAssigned?: (data: any) => void,
    onHospitalUpdate?: (data: any) => void,
    onFleetUpdate?: (data: any) => void,
): WebSocket {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/updates`);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "traffic_update") {
            onTrafficUpdate(msg.data.changes, msg.data.time_of_day);
        } else if (msg.type === "route_update") {
            onRouteUpdate(msg.data);
        } else if (msg.type === "emergency_new" && onEmergencyNew) {
            onEmergencyNew(msg.data);
        } else if (msg.type === "dispatch_assigned" && onDispatchAssigned) {
            onDispatchAssigned(msg.data);
        } else if (msg.type === "hospital_update" && onHospitalUpdate) {
            onHospitalUpdate(msg.data);
        } else if (msg.type === "fleet_update" && onFleetUpdate) {
            onFleetUpdate(msg.data);
        }
    };

    return ws;
}
