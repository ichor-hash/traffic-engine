/* ── MetricsPanel — results display with visual path steps ── */

import type { PathResult, CompareResult, GraphNode } from "../types";

interface MetricCardProps {
    label: string;
    value: string | number;
    unit?: string;
}

function MetricCard({ label, value, unit }: MetricCardProps) {
    return (
        <div className="metric-card">
            <span className="metric-label">{label}</span>
            <span className="metric-value">
                {value}
                {unit && <span className="metric-unit">{unit}</span>}
            </span>
        </div>
    );
}

interface PathStepProps {
    nodes: GraphNode[];
    path: string[];
}

function PathSteps({ nodes, path }: PathStepProps) {
    if (path.length === 0) return null;
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    return (
        <div className="path-visual">
            <span className="path-visual-label">Route ({path.length} stops)</span>
            <div className="path-steps">
                {path.map((nodeId, i) => {
                    const node = nodeMap.get(nodeId);
                    const label = node?.label || nodeId;
                    return (
                        <div key={nodeId} className="path-step">
                            <div className="path-step-dot" />
                            <span className="path-step-name">{label}</span>
                            {i === 0 && <span className="path-step-dist">Start</span>}
                            {i === path.length - 1 && i > 0 && <span className="path-step-dist">End</span>}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

interface Props {
    result: PathResult | null;
    comparison: CompareResult | null;
    recomputeCount: number;
    nodes: GraphNode[];
}

export default function MetricsPanel({ result, comparison, recomputeCount, nodes }: Props) {
    return (
        <div className="panel metrics-panel">
            <h2 className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 3v18h18" />
                    <path d="M18 17V9" /><path d="M13 17V5" /><path d="M8 17v-3" />
                </svg>
                Results
            </h2>

            {result ? (
                <>
                    <div className="metrics-grid">
                        <MetricCard
                            label="Total Cost"
                            value={result.total_cost != null ? result.total_cost.toFixed(1) : "∞"}
                            unit="m"
                        />
                        <MetricCard
                            label="Algorithm"
                            value={result.algorithm === "astar" ? "A*" : "Dijkstra"}
                        />
                        <MetricCard
                            label="Nodes Visited"
                            value={result.nodes_visited}
                        />
                        <MetricCard
                            label="Relaxations"
                            value={result.relaxations}
                        />
                        <MetricCard
                            label="Runtime"
                            value={result.runtime_ms.toFixed(2)}
                            unit="ms"
                        />
                        <MetricCard
                            label="Recomputes"
                            value={recomputeCount}
                        />
                    </div>

                    <PathSteps nodes={nodes} path={result.path} />

                    {!result.found && (
                        <p className="hint" style={{ color: "#dc2626" }}>
                            No path found between these nodes.
                        </p>
                    )}
                </>
            ) : (
                <p className="placeholder-text">
                    Select two nodes and find a route to see results.
                </p>
            )}

            {comparison && (
                <div className="comparison-section">
                    <h3 className="section-title">Algorithm Comparison</h3>
                    <table className="comparison-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Dijkstra</th>
                                <th>A*</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Cost</td>
                                <td>{comparison.dijkstra.total_cost != null ? comparison.dijkstra.total_cost.toFixed(1) : "∞"}</td>
                                <td>{comparison.astar.total_cost != null ? comparison.astar.total_cost.toFixed(1) : "∞"}</td>
                            </tr>
                            <tr>
                                <td>Visited</td>
                                <td>{comparison.dijkstra.nodes_visited}</td>
                                <td className={comparison.astar.nodes_visited < comparison.dijkstra.nodes_visited ? "delta highlight" : ""}>
                                    {comparison.astar.nodes_visited}
                                </td>
                            </tr>
                            <tr>
                                <td>Relaxations</td>
                                <td>{comparison.dijkstra.relaxations}</td>
                                <td className={comparison.astar.relaxations < comparison.dijkstra.relaxations ? "delta highlight" : ""}>
                                    {comparison.astar.relaxations}
                                </td>
                            </tr>
                            <tr>
                                <td>Runtime</td>
                                <td>{comparison.dijkstra.runtime_ms.toFixed(2)}ms</td>
                                <td className={comparison.astar.runtime_ms < comparison.dijkstra.runtime_ms ? "delta highlight" : ""}>
                                    {comparison.astar.runtime_ms.toFixed(2)}ms
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
