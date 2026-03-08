/* ── DispatchPanel — Material 3 minimalist control panel ── */

import {
    Truck, Building2, Zap, AlertTriangle,
    Play, Square, RotateCcw, Scale, ChevronRight,
    Activity, CircleDot, Gauge,
} from "lucide-react";
import type { GraphNode, Ambulance, Hospital, Emergency, DispatchResult, DispatchComparison } from "../types";
import type { AnimatingAmbulance } from "./LeafletMap";

interface Props {
    ambulances: Ambulance[];
    hospitals: Hospital[];
    emergencies: Emergency[];
    nodes: GraphNode[];
    comparison: DispatchComparison | null;
    lastResult: DispatchResult | null;
    selectedEmergency: string | null;
    simRunning: boolean;
    simSpeed: number;
    isAnimating: boolean;
    animatingState: AnimatingAmbulance | null;
    onGenerateEmergency: () => void;
    onDispatch: (algorithm: string) => void;
    onCompare: () => void;
    onReset: () => void;
    onToggleSim: () => void;
    onSelectEmergency: (id: string | null) => void;
    onSpeedChange: (speed: number) => void;
}

export default function DispatchPanel({
    ambulances, hospitals, emergencies, nodes, comparison, lastResult,
    selectedEmergency, simRunning, simSpeed, isAnimating, animatingState,
    onGenerateEmergency, onDispatch, onCompare, onReset, onToggleSim,
    onSelectEmergency, onSpeedChange,
}: Props) {
    const nodeMap = nodes.reduce((acc, node) => ({ ...acc, [node.id]: node.label || node.id }), {} as Record<string, string>);
    const pendingCount = emergencies.filter(e => !e.assigned).length;
    const availableCount = ambulances.filter(a => a.status === "available").length;
    const pending = emergencies.filter(e => !e.assigned);

    const speedLabel = simSpeed <= 1 ? "Fast" : simSpeed <= 3 ? "Normal" : simSpeed <= 6 ? "Slow" : "Very Slow";

    return (
        <div className="dispatch-panel">
            {/* ── Fleet ── */}
            <div className="card">
                <div className="card-title"><Truck /> Fleet</div>
                <div className="fleet-list">
                    {ambulances.map(a => (
                        <div key={a.id} className={`fleet-item ${a.status}`}>
                            <div className="fleet-icon">
                                {a.status === "dispatched" ? <Activity /> : <Truck />}
                            </div>
                            <span className="fleet-name">{a.name}</span>
                            <span className={`fleet-status ${a.status}`}>{a.status}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Hospitals ── */}
            <div className="card">
                <div className="card-title"><Building2 /> Hospitals</div>
                {hospitals.map(h => (
                    <div key={h.id} className="hospital-item">
                        <span className="hospital-name">{h.name}</span>
                        <div className="capacity-track">
                            <div className="capacity-fill" style={{
                                width: `${h.congestion * 100}%`,
                                background: h.congestion > .8 ? "var(--m3-error)"
                                    : h.congestion > .5 ? "var(--m3-warning)"
                                        : "var(--m3-success)",
                            }} />
                        </div>
                        <span className="capacity-label">{h.current_load}/{h.capacity}</span>
                    </div>
                ))}
            </div>

            {/* ── Dispatch Controls ── */}
            <div className="card">
                <div className="card-title"><Zap /> Dispatch</div>
                <div className="stats-row">
                    <div className="stat-box">
                        <span className="stat-num">{pendingCount}</span>
                        <span className="stat-lbl">Pending</span>
                    </div>
                    <div className="stat-box">
                        <span className="stat-num">{availableCount}</span>
                        <span className="stat-lbl">Available</span>
                    </div>
                </div>
                <div className="btn-stack">
                    <button className="btn btn-error" onClick={onGenerateEmergency} disabled={isAnimating}>
                        <AlertTriangle /> New Emergency
                    </button>
                    <button className="btn btn-filled"
                        onClick={() => onDispatch("greedy")}
                        disabled={!selectedEmergency || availableCount === 0 || isAnimating}>
                        <ChevronRight /> Greedy Dispatch
                    </button>
                    <button className="btn btn-tonal"
                        onClick={() => onDispatch("hungarian")}
                        disabled={pendingCount === 0 || availableCount === 0 || isAnimating}>
                        <ChevronRight /> Hungarian Dispatch
                    </button>
                    <button className="btn btn-outline"
                        onClick={onCompare}
                        disabled={pendingCount === 0 || availableCount === 0 || isAnimating}>
                        <Scale /> Compare Methods
                    </button>
                </div>
                <div className="btn-row">
                    <button className={`btn btn-sm ${simRunning ? "btn-error" : "btn-success"}`} onClick={onToggleSim}>
                        {simRunning ? <><Square /> Stop</> : <><Play /> Traffic</>}
                    </button>
                    <button className="btn btn-sm btn-outline" onClick={onReset} disabled={isAnimating}>
                        <RotateCcw /> Reset
                    </button>
                </div>
            </div>

            {/* ── Simulation Speed ── */}
            <div className="card">
                <div className="card-title"><Gauge /> Sim Speed</div>
                <div className="speed-control">
                    <input
                        type="range" min="0.5" max="8" step="0.5"
                        value={simSpeed}
                        onChange={e => onSpeedChange(parseFloat(e.target.value))}
                        className="speed-slider"
                    />
                    <div className="speed-labels">
                        <span>Fast</span>
                        <span className="speed-current">{speedLabel} ({simSpeed}s)</span>
                        <span>Slow</span>
                    </div>
                </div>
            </div>

            {/* ── Pending Emergencies ── */}
            {pending.length > 0 && (
                <div className="card">
                    <div className="card-title"><CircleDot /> Emergencies</div>
                    <div className="emg-list">
                        {pending.map(e => (
                            <div key={e.id}
                                className={`emg-item ${selectedEmergency === e.id ? "selected" : ""}`}
                                onClick={() => onSelectEmergency(selectedEmergency === e.id ? null : e.id)}>
                                <span className="emg-id">#{e.id}</span>
                                <span className="emg-sev">SEV {e.severity}</span>
                            </div>
                        ))}
                    </div>
                    <div className="hint">
                        Click an emergency, then <strong>Greedy Dispatch</strong> to watch the ambulance move
                    </div>
                </div>
            )}

            {/* ── Comparison ── */}
            {comparison && (
                <div className="card">
                    <div className="card-title"><Scale /> Comparison</div>
                    <table className="cmp-table">
                        <thead><tr><th>Metric</th><th>Greedy</th><th>Hungarian</th></tr></thead>
                        <tbody>
                            <tr>
                                <td>Distance</td>
                                <td>{comparison.greedy?.total_distance_m !== undefined ? (comparison.greedy.total_distance_m / 1000).toFixed(1) + " km" : "—"}</td>
                                <td>{comparison.hungarian?.total_distance_m !== undefined ? (comparison.hungarian.total_distance_m / 1000).toFixed(1) + " km" : "—"}</td>
                            </tr>
                            <tr>
                                <td>Est. Time</td>
                                <td className={comparison.greedy && comparison.hungarian
                                    ? (comparison.greedy.total_minutes <= comparison.hungarian.total_minutes ? "win" : "") : ""}>
                                    {comparison.greedy?.total_minutes?.toFixed(1) ?? "—"} min
                                </td>
                                <td className={comparison.greedy && comparison.hungarian
                                    ? (comparison.hungarian.total_minutes <= comparison.greedy.total_minutes ? "win" : "") : ""}>
                                    {comparison.hungarian?.total_minutes?.toFixed(1) ?? "—"} min
                                </td>
                            </tr>
                            <tr>
                                <td>Nodes</td>
                                <td>{comparison.greedy?.nodes_visited ?? "—"}</td>
                                <td>{comparison.hungarian?.nodes_visited ?? "—"}</td>
                            </tr>
                            <tr>
                                <td style={{ fontSize: 10, color: "var(--m3-outline)" }}>Algo Time</td>
                                <td style={{ fontSize: 10, color: "var(--m3-outline)" }}>{comparison.greedy?.algorithm_ms?.toFixed(2) ?? "—"} ms</td>
                                <td style={{ fontSize: 10, color: "var(--m3-outline)" }}>{comparison.hungarian?.algorithm_ms?.toFixed(2) ?? "—"} ms</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            )}

            {/* ── Last Result ── */}
            {lastResult && !isAnimating && (
                <div className="card">
                    <div className="card-title"><Activity /> Last Dispatch</div>
                    <div className="result-grid">
                        <div className="result-cell">
                            <span className="result-lbl">Algorithm</span>
                            <span className="result-val">{lastResult.algorithm}</span>
                        </div>
                        <div className="result-cell" style={{ gridColumn: "span 2" }}>
                            <span className="result-lbl">Assignment</span>
                            <span className="result-val">{lastResult.ambulance_id} → {lastResult.hospital_id}</span>
                        </div>
                        <div className="result-cell">
                            <span className="result-lbl">Distance</span>
                            <span className="result-val">{(lastResult.total_distance_m / 1000).toFixed(1)} km</span>
                        </div>
                        <div className="result-cell">
                            <span className="result-lbl">Est. Time</span>
                            <span className="result-val accent">{lastResult.total_minutes.toFixed(1)} min</span>
                        </div>
                        <div className="result-cell" style={{ gridColumn: "span 2" }}>
                            <span className="result-lbl">Execution Time (Backend)</span>
                            <span className="result-val">{lastResult.algorithm_ms.toFixed(2)} ms</span>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Animation status ── */}
            {isAnimating && (
                <div className="card">
                    <div className="card-title"><Activity /> Dispatching...</div>
                    <div className="hint" style={{ marginBottom: "12px" }}>
                        Ambulance is en route. Watch the map.
                    </div>
                    {animatingState && (
                        <div className="live-trace" style={{
                            maxHeight: '150px',
                            overflowY: 'auto',
                            fontSize: '12px',
                            background: 'var(--m3-surface-container-highest)',
                            padding: '12px',
                            borderRadius: '8px',
                            fontFamily: 'monospace',
                            lineHeight: '1.6'
                        }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '8px', color: 'var(--m3-primary)' }}>Live Route Trace:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                {animatingState.path.map((node, i) => (
                                    <span key={i} style={{
                                        color: i === animatingState.currentIdx ? 'var(--m3-primary)' :
                                            i < animatingState.currentIdx ? 'var(--m3-on-surface-var)' : 'var(--m3-on-surface)',
                                        fontWeight: i === animatingState.currentIdx ? 'bold' : 'normal',
                                        background: i === animatingState.currentIdx ? 'color-mix(in srgb, var(--m3-primary) 15%, transparent)' : 'transparent',
                                        padding: i === animatingState.currentIdx ? '0 4px' : '0',
                                        borderRadius: '4px'
                                    }}>
                                        {nodeMap[node] || node}{i < animatingState.path.length - 1 ? <span style={{ color: 'var(--m3-outline-variant)', margin: '0 2px' }}>→</span> : ''}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
