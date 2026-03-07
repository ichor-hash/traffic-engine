/* ── ControlPanel — select source, destination, algorithm, and simulation ── */

import type { GraphNode } from "../types";

interface Props {
    nodes: GraphNode[];
    source: string | null;
    destination: string | null;
    algorithm: string;
    simRunning: boolean;
    comparing: boolean;
    onSourceChange: (id: string) => void;
    onDestChange: (id: string) => void;
    onAlgorithmChange: (algo: string) => void;
    onFindRoute: () => void;
    onToggleSim: () => void;
    onCompare: () => void;
}

export default function ControlPanel({
    nodes,
    source,
    destination,
    algorithm,
    simRunning,
    comparing,
    onSourceChange,
    onDestChange,
    onAlgorithmChange,
    onFindRoute,
    onToggleSim,
    onCompare,
}: Props) {
    return (
        <div className="panel control-panel">
            <h2 className="panel-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Controls
            </h2>

            <div className="field-group">
                <label htmlFor="source-select">Source Node</label>
                <select
                    id="source-select"
                    value={source ?? ""}
                    onChange={(e) => onSourceChange(e.target.value)}
                >
                    <option value="">Click node or select…</option>
                    {nodes.map((n) => (
                        <option key={n.id} value={n.id}>
                            {n.label || n.id}
                        </option>
                    ))}
                </select>
            </div>

            <div className="field-group">
                <label htmlFor="dest-select">Destination Node</label>
                <select
                    id="dest-select"
                    value={destination ?? ""}
                    onChange={(e) => onDestChange(e.target.value)}
                >
                    <option value="">Click node or select…</option>
                    {nodes.map((n) => (
                        <option key={n.id} value={n.id}>
                            {n.label || n.id}
                        </option>
                    ))}
                </select>
            </div>

            <div className="field-group">
                <label htmlFor="algo-select">Algorithm</label>
                <select
                    id="algo-select"
                    value={algorithm}
                    onChange={(e) => onAlgorithmChange(e.target.value)}
                >
                    <option value="dijkstra">Dijkstra</option>
                    <option value="astar">A* (Euclidean)</option>
                </select>
            </div>

            <button
                className="btn btn-primary"
                onClick={onFindRoute}
                disabled={!source || !destination}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 2L11 13" /><path d="M22 2L15 22L11 13L2 9L22 2Z" />
                </svg>
                Find Route
            </button>

            <div className="divider" />

            <button
                className={`btn ${simRunning ? "btn-danger" : "btn-success"}`}
                onClick={onToggleSim}
            >
                {simRunning ? "⏹ Stop Simulation" : "▶ Start Simulation"}
            </button>

            <button
                className="btn btn-outline"
                onClick={onCompare}
                disabled={!source || !destination || comparing}
            >
                {comparing ? "Comparing…" : "⚡ Compare Algorithms"}
            </button>

            <p className="hint">
                💡 Click nodes on the map to select source / destination
            </p>
        </div>
    );
}
