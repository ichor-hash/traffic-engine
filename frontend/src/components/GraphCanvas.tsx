/* ── GraphCanvas — light theme with street name labels ── */

import { useRef, useEffect, useCallback } from "react";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
    nodes: GraphNode[];
    edges: GraphEdge[];
    path: string[];
    selectedSource: string | null;
    selectedDest: string | null;
    onNodeClick: (nodeId: string) => void;
    visitedNodes: Set<string>;
    relaxedEdges: Set<string>;
    currentNode: string | null;
    traceActive: boolean;
}

/* ── Light theme palette ── */
const C = {
    bg: "#fafafa",
    grid: "#e4e4e7",
    nodeDefault: "#d4d4d8",
    nodeVisited: "#f59e0b",
    nodeSource: "#2563eb",
    nodeDest: "#dc2626",
    nodeHover: "#71717a",
    nodePath: "#16a34a",
    nodeCurrent: "#18181b",
    edgeNormal: "#d4d4d8",
    edgeCongested: "#f59e0b",
    edgeBlocked: "#dc2626",
    edgeRelaxed: "#f59e0b",
    pathGlow: "#2563eb",
    pathEdge: "#2563eb",
    labelBg: "#ffffffee",
    labelText: "#18181b",
};

const R = 4;
const R_SPECIAL = 8;
const R_CURRENT = 10;

export default function GraphCanvas({
    nodes, edges, path,
    selectedSource, selectedDest, onNodeClick,
    visitedNodes, relaxedEdges, currentNode, traceActive,
}: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const hoveredNode = useRef<string | null>(null);
    const animOffset = useRef(0);
    const animFrameId = useRef<number>(0);

    const getTransform = useCallback(
        (canvas: HTMLCanvasElement) => {
            if (nodes.length === 0) return { sx: 1, sy: 1, ox: 0, oy: 0 };
            const xs = nodes.map((n) => n.x);
            const ys = nodes.map((n) => n.y);
            const minX = Math.min(...xs), maxX = Math.max(...xs);
            const minY = Math.min(...ys), maxY = Math.max(...ys);
            const pad = 50;
            const w = canvas.width - pad * 2;
            const h = canvas.height - pad * 2;
            const rangeX = maxX - minX || 1;
            const rangeY = maxY - minY || 1;
            const scale = Math.min(w / rangeX, h / rangeY);
            return {
                sx: scale,
                sy: -scale,
                ox: pad - minX * scale + (w - rangeX * scale) / 2,
                oy: canvas.height - pad + minY * scale - (h - rangeY * scale) / 2,
            };
        },
        [nodes]
    );

    const toScreen = useCallback(
        (node: GraphNode, t: ReturnType<typeof getTransform>) => ({
            x: node.x * t.sx + t.ox,
            y: node.y * t.sy + t.oy,
        }),
        []
    );

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
        const t = getTransform(canvas);

        const pathSet = new Set<string>();
        for (let i = 0; i < path.length - 1; i++) pathSet.add(`${path[i]}->${path[i + 1]}`);
        const pathNodeSet = new Set(path);
        const nodeMap = new Map(nodes.map((n) => [n.id, n]));

        // Background
        ctx.fillStyle = C.bg;
        ctx.fillRect(0, 0, rect.width, rect.height);

        // Grid dots
        ctx.fillStyle = C.grid;
        for (let x = 0; x < rect.width; x += 30) {
            for (let y = 0; y < rect.height; y += 30) {
                ctx.beginPath();
                ctx.arc(x, y, 0.5, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        /* ── Edges ── */
        for (const edge of edges) {
            const from = nodeMap.get(edge.from_node);
            const to = nodeMap.get(edge.to_node);
            if (!from || !to) continue;
            const key = `${edge.from_node}->${edge.to_node}`;
            if (pathSet.has(key)) continue;

            const isRelaxed = relaxedEdges.has(key) && traceActive;
            const a = toScreen(from, t);
            const b = toScreen(to, t);

            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);

            if (isRelaxed) {
                ctx.strokeStyle = C.edgeRelaxed;
                ctx.lineWidth = 2;
                ctx.globalAlpha = 0.8;
            } else {
                ctx.strokeStyle =
                    edge.status === "blocked" ? C.edgeBlocked
                        : edge.status === "congested" ? C.edgeCongested
                            : C.edgeNormal;
                ctx.lineWidth = 1;
                ctx.globalAlpha = edge.status === "normal" ? 0.4 : 0.7;
            }
            ctx.stroke();
            ctx.globalAlpha = 1;
        }

        /* ── Path edges ── */
        if (path.length > 1 && !traceActive) {
            ctx.save();
            ctx.shadowColor = C.pathGlow;
            ctx.shadowBlur = 12;
            ctx.strokeStyle = C.pathEdge;
            ctx.lineWidth = 3;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.beginPath();
            const s0 = nodeMap.get(path[0]);
            if (s0) {
                const p0 = toScreen(s0, t);
                ctx.moveTo(p0.x, p0.y);
                for (let i = 1; i < path.length; i++) {
                    const n = nodeMap.get(path[i]); if (n) { const p = toScreen(n, t); ctx.lineTo(p.x, p.y); }
                }
            }
            ctx.stroke();
            ctx.restore();

            // Marching ants
            ctx.save();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.lineCap = "round";
            ctx.setLineDash([6, 10]);
            ctx.lineDashOffset = -animOffset.current;
            ctx.globalAlpha = 0.6;
            ctx.beginPath();
            const sn = nodeMap.get(path[0]);
            if (sn) {
                const sp = toScreen(sn, t); ctx.moveTo(sp.x, sp.y);
                for (let i = 1; i < path.length; i++) {
                    const n = nodeMap.get(path[i]); if (n) { const p = toScreen(n, t); ctx.lineTo(p.x, p.y); }
                }
            }
            ctx.stroke();
            ctx.restore();
        }

        /* ── Nodes ── */
        for (const node of nodes) {
            const p = toScreen(node, t);
            const isSource = node.id === selectedSource;
            const isDest = node.id === selectedDest;
            const isCurrent = node.id === currentNode && traceActive;
            const isVisited = visitedNodes.has(node.id) && traceActive;
            const isOnPath = pathNodeSet.has(node.id) && !traceActive;
            const isHovered = node.id === hoveredNode.current;

            let color = C.nodeDefault;
            let radius = R;

            if (isCurrent) { color = C.nodeCurrent; radius = R_CURRENT; }
            else if (isSource) { color = C.nodeSource; radius = R_SPECIAL; }
            else if (isDest) { color = C.nodeDest; radius = R_SPECIAL; }
            else if (isOnPath) { color = C.nodePath; radius = 5; }
            else if (isVisited) { color = C.nodeVisited; radius = 5; }
            else if (isHovered) { color = C.nodeHover; radius = 6; }

            if (isSource || isDest || isCurrent) {
                ctx.save();
                ctx.shadowColor = color;
                ctx.shadowBlur = isCurrent ? 20 : 14;
                ctx.beginPath();
                ctx.arc(p.x, p.y, radius + 3, 0, Math.PI * 2);
                ctx.fillStyle = color + "20";
                ctx.fill();
                ctx.restore();
            }

            ctx.beginPath();
            ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // Label with street name
            if (isSource || isDest || isCurrent || isHovered) {
                const label = node.label || node.id;
                ctx.font = "500 10px 'Inter', sans-serif";
                const tw = ctx.measureText(label).width + 10;
                ctx.fillStyle = C.labelBg;
                ctx.beginPath();
                ctx.roundRect(p.x - tw / 2, p.y - radius - 22, tw, 17, 4);
                ctx.fill();
                ctx.strokeStyle = "#e4e4e7";
                ctx.lineWidth = 0.5;
                ctx.stroke();

                ctx.fillStyle = isSource ? C.nodeSource : isDest ? C.nodeDest : C.labelText;
                ctx.font = "500 10px 'Inter', sans-serif";
                ctx.textAlign = "center";
                ctx.fillText(label, p.x, p.y - radius - 9);
            }
        }

        /* ── Trace counter ── */
        if (traceActive) {
            ctx.fillStyle = "#ffffffdd";
            ctx.beginPath();
            ctx.roundRect(rect.width - 220, 14, 204, 30, 6);
            ctx.fill();
            ctx.strokeStyle = "#e4e4e7";
            ctx.lineWidth = 0.5;
            ctx.stroke();
            ctx.fillStyle = "#18181b";
            ctx.font = "500 11px 'JetBrains Mono', monospace";
            ctx.textAlign = "right";
            ctx.fillText(
                `Visited: ${visitedNodes.size}  Relaxed: ${relaxedEdges.size}`,
                rect.width - 26, 34
            );
        }
    }, [nodes, edges, path, selectedSource, selectedDest, getTransform, toScreen,
        visitedNodes, relaxedEdges, currentNode, traceActive]);

    useEffect(() => {
        let running = true;
        const animate = () => {
            if (!running) return;
            animOffset.current = (animOffset.current + 0.5) % 40;
            draw();
            animFrameId.current = requestAnimationFrame(animate);
        };
        if (path.length > 1 || traceActive) animate();
        else draw();
        return () => { running = false; cancelAnimationFrame(animFrameId.current); };
    }, [draw, path, traceActive]);

    const handleClick = useCallback(
        (e: MouseEvent) => {
            const canvas = canvasRef.current; if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left, my = e.clientY - rect.top;
            const t = getTransform(canvas);
            for (const node of nodes) {
                const p = toScreen(node, t);
                if (Math.hypot(p.x - mx, p.y - my) < R + 10) { onNodeClick(node.id); return; }
            }
        }, [nodes, getTransform, toScreen, onNodeClick]
    );

    const handleMouseMove = useCallback(
        (e: MouseEvent) => {
            const canvas = canvasRef.current; if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left, my = e.clientY - rect.top;
            const t = getTransform(canvas);
            let found: string | null = null;
            for (const node of nodes) {
                const p = toScreen(node, t);
                if (Math.hypot(p.x - mx, p.y - my) < R + 10) { found = node.id; break; }
            }
            if (found !== hoveredNode.current) {
                hoveredNode.current = found;
                canvas.style.cursor = found ? "pointer" : "default";
                if (path.length <= 1 && !traceActive) draw();
            }
        }, [nodes, getTransform, toScreen, draw, path, traceActive]
    );

    useEffect(() => {
        const canvas = canvasRef.current; if (!canvas) return;
        canvas.addEventListener("click", handleClick);
        canvas.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("resize", draw);
        return () => {
            canvas.removeEventListener("click", handleClick);
            canvas.removeEventListener("mousemove", handleMouseMove);
            window.removeEventListener("resize", draw);
        };
    }, [draw, handleClick, handleMouseMove]);

    return (
        <div ref={containerRef} className="canvas-container">
            <canvas ref={canvasRef} className="graph-canvas" />
            <div className="canvas-legend">
                <span className="legend-item"><span className="dot" style={{ background: C.edgeNormal }} /> Normal</span>
                <span className="legend-item"><span className="dot" style={{ background: C.edgeCongested }} /> Congested</span>
                <span className="legend-item"><span className="dot" style={{ background: C.edgeBlocked }} /> Blocked</span>
                <span className="legend-item"><span className="dot" style={{ background: C.pathEdge }} /> Path</span>
                {traceActive && <>
                    <span className="legend-item"><span className="dot" style={{ background: C.nodeVisited }} /> Visited</span>
                    <span className="legend-item"><span className="dot" style={{ background: C.nodeCurrent }} /> Current</span>
                </>}
            </div>
        </div>
    );
}
