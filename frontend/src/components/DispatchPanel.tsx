import React, { memo, useMemo } from "react";
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
    onShowAnalytics: () => void;
    variant?: "sidebar" | "controls" | "fleet" | "hospitals" | "speed";
    nodeLabelMap?: Record<string, string>;
}

function DispatchPanel({
    ambulances, hospitals, emergencies, nodes, comparison, lastResult,
    selectedEmergency, simRunning, simSpeed, isAnimating, animatingState,
    onGenerateEmergency, onDispatch, onCompare, onReset, onToggleSim,
    onSelectEmergency, onSpeedChange, onShowAnalytics, variant, nodeLabelMap
}: Props) {
    const labels = nodeLabelMap || {};
    const nodeMap = labels;

    const pendingCount = useMemo(() => emergencies.filter(e => !e.assigned).length, [emergencies]);
    const availableCount = useMemo(() => ambulances.filter(a => a.status === "available").length, [ambulances]);
    const pending = useMemo(() => emergencies.filter(e => !e.assigned), [emergencies]);

    const speedLabel = simSpeed <= 1 ? "Fast" : simSpeed <= 3 ? "Normal" : simSpeed <= 6 ? "Slow" : "Very Slow";

    const getEmergencyName = (severity: number) => {
        if (severity >= 5) return "Cardiac Arrest";
        if (severity >= 4) return "Major Trauma";
        if (severity >= 3) return "Respiratory Distress";
        if (severity >= 2) return "Moderate Injury";
        return "Minor Incident";
    };

    return (
        <div className="dispatch-panel">
            {/* ── FLEET VARIANT ── */}
            {variant === "fleet" && (
                <div className="card">
                    <div className="card-title"><Truck /> Fleet Status</div>
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
            )}

            {/* ── HOSPITALS VARIANT ── */}
            {variant === "hospitals" && (
                <div className="card">
                    <div className="card-title"><Building2 /> Hospital Capacity</div>
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
            )}

            {/* ── SPEED VARIANT ── */}
            {variant === "speed" && (
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
            )}

            {/* ── DISPATCH & FEEDBACK VARIANT ── */}
            {variant === "controls" && (
                <>
                    <div className="card">
                        <div className="card-title"><Zap /> Dispatch Control</div>
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
                            <button className="btn btn-tonal" onClick={onShowAnalytics}>
                                <Activity /> Analytics
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

                    {pending.length > 0 && (
                        <div className="card">
                            <div className="card-title"><CircleDot /> Emergencies</div>
                            <div className="emg-list">
                                {pending.map(e => (
                                    <div key={e.id}
                                        className={`emg-item ${selectedEmergency === e.id ? "selected" : ""}`}
                                        onClick={() => onSelectEmergency(selectedEmergency === e.id ? null : e.id)}>
                                        <div className="emg-info">
                                            <span className="emg-id">{getEmergencyName(e.severity)}</span>
                                            <span className="emg-loc-hint">#{e.id}</span>
                                        </div>
                                        <span className={`emg-sev sev-${e.severity}`}>SEV {e.severity}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

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
                                </tbody>
                            </table>
                        </div>
                    )}

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
                            </div>
                        </div>
                    )}

                    {isAnimating && (
                        <div className="card">
                            <div className="card-title"><Activity /> Dispatching...</div>
                            {animatingState && (
                                <div className="live-trace" style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '11px', background: 'var(--m3-surface-container-highest)', padding: '12px', borderRadius: '8px', fontFamily: 'monospace' }}>
                                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Route Trace:</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px' }}>
                                        {animatingState.path.map((node, i) => (
                                            <span key={i} style={{ color: i === animatingState.currentIdx ? 'var(--m3-primary)' : i < animatingState.currentIdx ? 'var(--m3-on-surface-var)' : 'var(--m3-on-surface)' }}>
                                                {labels[node] || node}{i < animatingState.path.length - 1 ? ' → ' : ''}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default memo(DispatchPanel);
