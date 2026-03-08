/* ── LeafletMap — Material 3 map with animated ambulance movement ── */

import { useEffect, useRef, useMemo, useCallback, memo } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GraphNode, GraphEdge, Ambulance, Hospital, Emergency, DispatchResult } from "../types";

interface AnimatingAmbulance {
    id: string;
    path: string[];       // node IDs
    currentIdx: number;
    phase: "to_emergency" | "to_hospital";
    result: DispatchResult;
}

interface Props {
    nodes: GraphNode[];
    edges: GraphEdge[];
    ambulances: Ambulance[];
    hospitals: Hospital[];
    emergencies: Emergency[];
    selectedEmergency: string | null;
    dispatchResult: DispatchResult | null;
    animating: AnimatingAmbulance | null;
    onNodeClick: (nodeId: string) => void;
    onEmergencyClick: (id: string) => void;
}

export type { AnimatingAmbulance };

const CENTER: L.LatLngExpression = [13.045, 80.235];
const ZOOM = 16;

/* ── SVG icons (Lucide-style) ── */
const SVG = {
    truck: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18h2a1 1 0 0 0 1-1v-3.28a1 1 0 0 0-.684-.948l-1.923-.641a1 1 0 0 1-.684-.948V8a1 1 0 0 0-1-1h-1"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/></svg>`,
    building: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>`,
    alert: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
};

function svgIcon(svg: string, cls: string): L.DivIcon {
    return L.divIcon({
        html: `<div class="map-marker ${cls}">${svg}</div>`,
        className: "custom-div-icon",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function edgeStyle(status: string) {
    if (status === "blocked") return { color: "#ff453a", weight: 2.5, opacity: 0.7 };
    if (status === "congested") return { color: "#ff9f0a", weight: 2, opacity: 0.5 };
    return { color: "#48484a", weight: 1.2, opacity: 0.35 };
}

function LeafletMap({
    nodes, edges, ambulances, hospitals, emergencies,
    selectedEmergency, dispatchResult, animating,
    onNodeClick, onEmergencyClick,
}: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<L.Map | null>(null);
    const edgeLayer = useRef(L.layerGroup());
    const nodeLayer = useRef(L.layerGroup());
    const markerLayer = useRef(L.layerGroup());
    const pathLayer = useRef(L.layerGroup());
    const animLayer = useRef(L.layerGroup());
    const boundsLayer = useRef(L.layerGroup());
    const edgeObjects = useRef<Record<string, L.Polyline>>({});
    const hospitalMarkers = useRef<Record<string, L.Marker>>({});
    const ambulanceMarkers = useRef<Record<string, L.Marker>>({});
    const emergencyMarkers = useRef<Record<string, L.Marker>>({});

    const nodeMap = useMemo(() => {
        const m: Record<string, GraphNode> = {};
        for (const n of nodes) m[n.id] = n;
        return m;
    }, [nodes]);

    /* ── Init map ── */
    useEffect(() => {
        if (!containerRef.current || mapRef.current) return;
        const map = L.map(containerRef.current, { center: CENTER, zoom: ZOOM, zoomControl: true, preferCanvas: true });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
            maxZoom: 19,
        }).addTo(map);

        edgeLayer.current.addTo(map);
        nodeLayer.current.addTo(map);
        markerLayer.current.addTo(map);
        pathLayer.current.addTo(map);
        animLayer.current.addTo(map);
        boundsLayer.current.addTo(map);

        mapRef.current = map;
        return () => { map.remove(); mapRef.current = null; };
    }, []);

    /* ── Region Boundary ── */
    useEffect(() => {
        boundsLayer.current.clearLayers();
        if (nodes.length === 0) return;

        let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
        for (const n of nodes) {
            if (n.y < minLat) minLat = n.y;
            if (n.y > maxLat) maxLat = n.y;
            if (n.x < minLng) minLng = n.x;
            if (n.x > maxLng) maxLng = n.x;
        }

        const bounds: L.LatLngBoundsLiteral = [[minLat, minLng], [maxLat, maxLng]];
        L.rectangle(bounds, { color: "#0a84ff", weight: 3, fillOpacity: 0, dashArray: "10, 10", opacity: 0.8 })
            .bindTooltip("Simulation Area Boundary", { direction: "top", sticky: true, className: "node-tip" })
            .addTo(boundsLayer.current);
    }, [nodes]);

    /* ── Edges (Persistent Optimization) ── */
    useEffect(() => {
        if (!mapRef.current) return;

        // We only clear if edges array is empty (reset)
        if (edges.length === 0) {
            edgeLayer.current.clearLayers();
            edgeObjects.current = {};
            return;
        }

        for (const e of edges) {
            const key = `${e.from_node}-${e.to_node}`;
            const poly = edgeObjects.current[key];

            if (!poly) {
                const f = nodeMap[e.from_node], t = nodeMap[e.to_node];
                if (!f || !t) continue;
                const newPoly = L.polyline([[f.y, f.x], [t.y, t.x]], edgeStyle(e.status));
                newPoly.addTo(edgeLayer.current);
                edgeObjects.current[key] = newPoly;
            } else {
                // Light-weight style update instead of full re-creation
                poly.setStyle(edgeStyle(e.status));
            }
        }
    }, [edges, nodeMap]);

    /* ── Nodes ── */
    useEffect(() => {
        nodeLayer.current.clearLayers();
        for (const n of nodes) {
            const m = L.circleMarker([n.y, n.x], {
                radius: 2.5, fillColor: "#636882", fillOpacity: .5,
                color: "#636882", weight: .5,
            });
            m.bindTooltip(n.label || n.id, { direction: "top", offset: [0, -4], className: "node-tip" });
            m.on("click", () => onNodeClick(n.id));
            m.addTo(nodeLayer.current);
        }
    }, [nodes, onNodeClick]);

    /* ── Hospitals persist ── */
    useEffect(() => {
        if (!mapRef.current) return;
        const currentIds = new Set(hospitals.map(h => h.name));

        // Remove old
        Object.keys(hospitalMarkers.current).forEach(id => {
            if (!currentIds.has(id)) {
                hospitalMarkers.current[id].remove();
                delete hospitalMarkers.current[id];
            }
        });

        for (const h of hospitals) {
            const n = nodeMap[h.location]; if (!n) continue;
            const stateCls = h.congestion > 0.8 ? "critical" : h.congestion > 0.5 ? "warning" : "safe";
            const icon = svgIcon(SVG.building, `hospital ${stateCls}`);

            if (!hospitalMarkers.current[h.name]) {
                const m = L.marker([n.y, n.x], { icon }).addTo(markerLayer.current);
                m.bindTooltip(`<strong>${h.name}</strong><br/>${h.current_load}/${h.capacity} beds`, { direction: "top", offset: [0, -16], className: "node-tip" });
                hospitalMarkers.current[h.name] = m;
            } else {
                hospitalMarkers.current[h.name].setIcon(icon);
                hospitalMarkers.current[h.name].setTooltipContent(`<strong>${h.name}</strong><br/>${h.current_load}/${h.capacity} beds`);
            }
        }
    }, [hospitals, nodeMap]);

    /* ── Ambulances persist ── */
    useEffect(() => {
        if (!mapRef.current) return;
        const currentIds = new Set(ambulances.map(a => a.id));

        Object.keys(ambulanceMarkers.current).forEach(id => {
            if (!currentIds.has(id)) {
                ambulanceMarkers.current[id].remove();
                delete ambulanceMarkers.current[id];
            }
        });

        for (const a of ambulances) {
            if (animating && animating.id === a.id) {
                if (ambulanceMarkers.current[a.id]) {
                    ambulanceMarkers.current[a.id].remove();
                    delete ambulanceMarkers.current[a.id];
                }
                continue;
            }

            const n = nodeMap[a.location]; if (!n) continue;
            const cls = a.status === "dispatched" ? "ambulance dispatched" : "ambulance";
            const icon = svgIcon(SVG.truck, cls);

            if (!ambulanceMarkers.current[a.id]) {
                const m = L.marker([n.y, n.x], { icon }).addTo(markerLayer.current);
                m.bindTooltip(`<strong>${a.name}</strong><br/>${a.status}`, { direction: "top", offset: [0, -16], className: "node-tip" });
                ambulanceMarkers.current[a.id] = m;
            } else {
                ambulanceMarkers.current[a.id].setLatLng([n.y, n.x]);
                ambulanceMarkers.current[a.id].setIcon(icon);
                ambulanceMarkers.current[a.id].setTooltipContent(`<strong>${a.name}</strong><br/>${a.status}`);
            }
        }
    }, [ambulances, animating, nodeMap]);

    /* ── Emergencies persist ── */
    useEffect(() => {
        if (!mapRef.current) return;
        const currentIds = new Set(emergencies.filter(e => !e.assigned).map(e => e.id));

        Object.keys(emergencyMarkers.current).forEach(id => {
            if (!currentIds.has(id)) {
                emergencyMarkers.current[id].remove();
                delete emergencyMarkers.current[id];
            }
        });

        for (const e of emergencies) {
            if (e.assigned) continue;
            const n = nodeMap[e.location]; if (!n) continue;
            let sevCls = "";
            if (e.severity >= 5) sevCls = "sev-critical";
            else if (e.severity >= 4) sevCls = "sev-high";
            const cls = selectedEmergency === e.id ? "emergency selected-emg" : `emergency ${sevCls}`;
            const icon = svgIcon(SVG.alert, cls);

            if (!emergencyMarkers.current[e.id]) {
                const m = L.marker([n.y, n.x], { icon }).addTo(markerLayer.current);
                m.bindTooltip(`<strong>Emergency #${e.id}</strong><br/>Severity: ${e.severity}`, { direction: "top", offset: [0, -16], className: "node-tip" });
                m.on("click", () => onEmergencyClick(e.id));
                emergencyMarkers.current[e.id] = m;
            } else {
                emergencyMarkers.current[e.id].setIcon(icon);
                if (selectedEmergency === e.id) emergencyMarkers.current[e.id].setZIndexOffset(1000);
            }
        }
    }, [emergencies, selectedEmergency, nodeMap, onEmergencyClick]);

    /* ── Dispatch paths ── */
    useEffect(() => {
        pathLayer.current.clearLayers();
        if (!dispatchResult) return;

        if (dispatchResult.path_to_emergency.length > 1) {
            const coords: L.LatLngExpression[] = dispatchResult.path_to_emergency
                .map(id => nodeMap[id]).filter(Boolean).map(n => [n!.y, n!.x] as L.LatLngExpression);
            L.polyline(coords, { color: "#0a84ff", weight: 4, opacity: .85, dashArray: "8, 5" }).addTo(pathLayer.current);
        }

        if (dispatchResult.path_to_hospital.length > 1) {
            const coords: L.LatLngExpression[] = dispatchResult.path_to_hospital
                .map(id => nodeMap[id]).filter(Boolean).map(n => [n!.y, n!.x] as L.LatLngExpression);
            L.polyline(coords, { color: "#ff453a", weight: 4, opacity: .85, dashArray: "8, 5" }).addTo(pathLayer.current);
        }
    }, [dispatchResult, nodeMap]);

    /* ── Animated ambulance marker ── */
    useEffect(() => {
        animLayer.current.clearLayers();
        if (!animating) return;

        const node = nodeMap[animating.path[animating.currentIdx]];
        if (!node) return;

        const cls = "ambulance dispatched";
        L.marker([node.y, node.x], { icon: svgIcon(SVG.truck, cls), zIndexOffset: 1000 })
            .addTo(animLayer.current);

        // Draw trail behind the ambulance
        const trailCoords: L.LatLngExpression[] = animating.path
            .slice(0, animating.currentIdx + 1)
            .map(id => nodeMap[id]).filter(Boolean)
            .map(n => [n!.y, n!.x] as L.LatLngExpression);

        if (trailCoords.length > 1) {
            const color = animating.phase === "to_emergency" ? "#0a84ff" : "#ff453a";
            L.polyline(trailCoords, { color, weight: 5, opacity: 1 }).addTo(animLayer.current);
        }

        // Draw planned route ahead of the ambulance
        const plannedCoords: L.LatLngExpression[] = animating.path
            .slice(animating.currentIdx)
            .map(id => nodeMap[id]).filter(Boolean)
            .map(n => [n!.y, n!.x] as L.LatLngExpression);

        if (plannedCoords.length > 1) {
            const plannedColor = animating.phase === "to_emergency" ? "#0a84ff" : "#ff453a";
            L.polyline(plannedCoords, { color: plannedColor, weight: 3, opacity: 0.4, dashArray: "4, 6" }).addTo(animLayer.current);
        }
    }, [animating, nodeMap]);

    return <div ref={containerRef} id="leaflet-map" />;
}

export default memo(LeafletMap);
