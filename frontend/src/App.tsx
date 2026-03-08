/* ── App — Ambulance Dispatch System (Material 3 + Animation) ── */

import { useState, useEffect, useCallback, useRef } from "react";
import { Siren, Trophy } from "lucide-react";
import type {
    GraphNode, GraphEdge,
    Ambulance, Hospital, Emergency,
    DispatchResult, DispatchComparison,
} from "./types";
import {
    fetchGraph, fetchTraffic, fetchDispatchState,
    startSimulation, stopSimulation, setSimulationSpeed,
    triggerEmergency, dispatchAssign, dispatchCompare, resetDispatch,
    createUpdateSocket,
} from "./api";
import LeafletMap from "./components/LeafletMap";
import type { AnimatingAmbulance } from "./components/LeafletMap";
import DispatchPanel from "./components/DispatchPanel";
import { ToastContainer, useToast } from "./components/Toast";

export default function App() {
    /* ── Graph ── */
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);

    /* ── Dispatch ── */
    const [ambulances, setAmbulances] = useState<Ambulance[]>([]);
    const [hospitals, setHospitals] = useState<Hospital[]>([]);
    const [emergencies, setEmergencies] = useState<Emergency[]>([]);
    const [lastResult, setLastResult] = useState<DispatchResult | null>(null);
    const [comparison, setComparison] = useState<DispatchComparison | null>(null);
    const [selectedEmergency, setSelectedEmergency] = useState<string | null>(null);
    const [simRunning, setSimRunning] = useState(false);
    const [simSpeed, setSimSpeed] = useState(3.0);
    const [score, setScore] = useState(0);
    const [dispatches, setDispatches] = useState(0);

    /* ── Animation ── */
    const [animating, setAnimating] = useState<AnimatingAmbulance | null>(null);
    const animTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const { toasts, addToast, dismissToast } = useToast();

    const nodeMapRef = useRef<Record<string, GraphNode>>({});
    useEffect(() => {
        const m: Record<string, GraphNode> = {};
        for (const n of nodes) m[n.id] = n;
        nodeMapRef.current = m;
    }, [nodes]);

    /* ── Load ── */
    useEffect(() => {
        Promise.all([fetchGraph(), fetchDispatchState()])
            .then(([g, d]) => {
                setNodes(g.nodes);
                setEdges(g.edges);
                setAmbulances(d.ambulances);
                setHospitals(d.hospitals);
                setEmergencies(d.emergencies);
                setScore(d.score || 0);
                setDispatches(d.dispatches || 0);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to load:", err);
                setLoadError(err.message || "Failed to connect to server");
                setLoading(false);
            });
    }, []);

    /* ── WebSocket ── */
    useEffect(() => {
        let ws: WebSocket;
        try {
            ws = createUpdateSocket(
                (changes) => {
                    setEdges(prev => {
                        const u = [...prev];
                        for (const c of changes) {
                            const i = u.findIndex(e => e.from_node === c.from_node && e.to_node === c.to_node);
                            if (i !== -1) u[i] = { ...u[i], current_weight: c.new_weight, status: c.status };
                        }
                        return u;
                    });
                },
                () => { },
                (data) => {
                    refreshDispatchState();
                    const loc = nodeMapRef.current[data.location];
                    addToast({
                        type: "error",
                        title: `Emergency #${data.id}`,
                        description: `Severity ${data.severity} at ${loc?.label || data.location}`,
                        onClick: () => setSelectedEmergency(data.id),
                        duration: 8000,
                    });
                },
                () => { refreshDispatchState(); },
                (data) => {
                    if (data.hospitals) setHospitals(data.hospitals);
                },
            );
            wsRef.current = ws;
        } catch (err) {
            console.error("WebSocket connection failed:", err);
        }
        return () => { if (ws) ws.close(); };
    }, []);

    const refreshDispatchState = useCallback(async () => {
        try {
            const s = await fetchDispatchState();
            setAmbulances(s.ambulances);
            setHospitals(s.hospitals);
            setEmergencies(s.emergencies);
            setScore(s.score || 0);
            setDispatches(s.dispatches || 0);
        } catch (err) {
            console.error("Failed to refresh state:", err);
        }
    }, []);

    /* ── Traffic polling ── */
    useEffect(() => {
        if (!simRunning) return;
        const iv = setInterval(async () => {
            try {
                const d = await fetchTraffic();
                setEdges(d.edges);
            } catch (err) {
                console.error("Traffic poll failed:", err);
            }
        }, 3000);
        return () => clearInterval(iv);
    }, [simRunning]);

    /* ── Animation engine ── */
    const startAnimation = useCallback((result: DispatchResult) => {
        if (animTimerRef.current) clearInterval(animTimerRef.current);

        const fullPath = [
            ...result.path_to_emergency,
            ...result.path_to_hospital.slice(1),
        ];
        const emergencyIdx = result.path_to_emergency.length - 1;

        setAnimating({
            id: result.ambulance_id,
            path: fullPath,
            currentIdx: 0,
            phase: "to_emergency",
            result,
        });

        let idx = 0;
        animTimerRef.current = setInterval(() => {
            idx++;
            if (idx >= fullPath.length) {
                if (animTimerRef.current) clearInterval(animTimerRef.current);
                animTimerRef.current = null;
                setAnimating(null);
                setLastResult(result);
                refreshDispatchState();
                addToast({
                    type: "success",
                    title: "Patient Delivered",
                    description: `${result.ambulance_id} arrived at hospital`,
                    duration: 8000,
                });
                return;
            }

            const phase = idx <= emergencyIdx ? "to_emergency" : "to_hospital";

            if (idx === emergencyIdx) {
                addToast({
                    type: "info",
                    title: "Patient Picked Up",
                    description: `${result.ambulance_id} en route to hospital`,
                    duration: 8000,
                });
            }

            setAnimating({
                id: result.ambulance_id,
                path: fullPath,
                currentIdx: idx,
                phase,
                result,
            });
        }, 200);
    }, [refreshDispatchState, addToast]);

    useEffect(() => {
        return () => { if (animTimerRef.current) clearInterval(animTimerRef.current); };
    }, []);

    /* ── Handlers ── */
    const handleNodeClick = useCallback((nodeId: string) => {
        setEmergencies(prev => {
            const emg = prev.find(e => e.location === nodeId && !e.assigned);
            if (emg) setSelectedEmergency(emg.id);
            return prev;
        });
    }, []);

    const handleEmergencyClick = useCallback((id: string) => {
        setSelectedEmergency(prev => prev === id ? null : id);
    }, []);

    const handleGenerateEmergency = useCallback(async () => {
        try {
            await triggerEmergency();
            await refreshDispatchState();
        } catch (err: any) {
            addToast({ type: "error", title: "Failed", description: err.message || "Could not generate emergency", duration: 5000 });
        }
    }, [refreshDispatchState, addToast]);

    const handleDispatch = useCallback(async (algorithm: string) => {
        try {
            const res = await dispatchAssign(algorithm, selectedEmergency ?? undefined);
            if (res.assignments && res.assignments.length > 0) {
                const r = res.assignments[0];
                addToast({
                    type: "success",
                    title: "Ambulance Dispatched",
                    description: `${r.ambulance_id} responding to #${r.emergency_id} (${r.algorithm})`,
                    duration: 8000,
                });
                setSelectedEmergency(null);
                startAnimation(r);
                await refreshDispatchState();
            }
        } catch (err: any) {
            addToast({ type: "error", title: "Dispatch Error", description: err.message || "Dispatch failed", duration: 5000 });
        }
    }, [selectedEmergency, refreshDispatchState, addToast, startAnimation]);

    const handleCompare = useCallback(async () => {
        try {
            const res = await dispatchCompare(selectedEmergency ?? undefined);
            setComparison(res);
            addToast({ type: "info", title: "Comparison Ready", description: "Greedy vs Hungarian results below", duration: 4000 });
        } catch (err: any) {
            addToast({ type: "error", title: "Compare Error", description: err.message || "Comparison failed", duration: 5000 });
        }
    }, [selectedEmergency, addToast]);

    const handleReset = useCallback(async () => {
        try {
            if (animTimerRef.current) { clearInterval(animTimerRef.current); animTimerRef.current = null; }
            setAnimating(null);
            setLastResult(null);
            setComparison(null);
            setSelectedEmergency(null);
            setScore(0);
            setDispatches(0);
            await resetDispatch();
            await refreshDispatchState();
            addToast({ type: "info", title: "System Reset", duration: 3000 });
        } catch (err: any) {
            addToast({ type: "error", title: "Reset Failed", description: err.message || "Reset failed", duration: 5000 });
        }
    }, [refreshDispatchState, addToast]);

    const handleToggleSim = useCallback(async () => {
        try {
            if (simRunning) {
                await stopSimulation();
                setSimRunning(false);
            } else {
                await startSimulation();
                setSimRunning(true);
                addToast({ type: "info", title: "Traffic Simulation Started", duration: 3000 });
            }
        } catch (err: any) {
            addToast({ type: "error", title: "Simulation Error", description: err.message || "Failed", duration: 5000 });
        }
    }, [simRunning, addToast]);

    const handleSpeedChange = useCallback(async (speed: number) => {
        setSimSpeed(speed);
        try {
            await setSimulationSpeed(speed);
        } catch (err) {
            console.error("Speed change failed:", err);
        }
    }, []);

    /* ── Render ── */
    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading Dispatch System</p>
            </div>
        );
    }

    if (loadError) {
        return (
            <div className="loading-screen">
                <p style={{ color: "var(--m3-error)", fontSize: 14 }}>
                    Failed to connect to server
                </p>
                <p style={{ color: "var(--m3-on-surface-var)", fontSize: 12, marginTop: 8 }}>
                    {loadError}
                </p>
                <button className="btn btn-outline" style={{ marginTop: 16 }} onClick={() => window.location.reload()}>
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="app">
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />

            <header className="app-header">
                <div className="brand">
                    <Siren size={20} />
                    <h1>Ambulance Dispatch</h1>
                    <span className="brand-sub">T. Nagar, Chennai</span>
                </div>
                <div className="header-right">
                    <div className="score-chip">
                        <Trophy size={14} />
                        <span>{score} pts</span>
                        <span className="score-sep">|</span>
                        <span>{dispatches} dispatched</span>
                    </div>
                    <div className={`status-chip ${simRunning ? "live" : ""}`}>
                        {simRunning && <span className="status-dot" />}
                        {simRunning ? "Traffic Live" : "Traffic Paused"}
                    </div>
                </div>
            </header>

            <main className="main-layout">
                <aside className="sidebar">
                    <DispatchPanel
                        ambulances={ambulances}
                        hospitals={hospitals}
                        emergencies={emergencies}
                        nodes={nodes}
                        comparison={comparison}
                        lastResult={lastResult}
                        selectedEmergency={selectedEmergency}
                        simRunning={simRunning}
                        simSpeed={simSpeed}
                        isAnimating={!!animating}
                        animatingState={animating}
                        onGenerateEmergency={handleGenerateEmergency}
                        onDispatch={handleDispatch}
                        onCompare={handleCompare}
                        onReset={handleReset}
                        onToggleSim={handleToggleSim}
                        onSelectEmergency={setSelectedEmergency}
                        onSpeedChange={handleSpeedChange}
                    />
                </aside>

                <section className="map-section">
                    <LeafletMap
                        nodes={nodes}
                        edges={edges}
                        ambulances={ambulances}
                        hospitals={hospitals}
                        emergencies={emergencies}
                        selectedEmergency={selectedEmergency}
                        dispatchResult={animating ? null : lastResult}
                        animating={animating}
                        onNodeClick={handleNodeClick}
                        onEmergencyClick={handleEmergencyClick}
                    />
                </section>
            </main>
        </div>
    );
}
