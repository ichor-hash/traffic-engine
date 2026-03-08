"""
FastAPI route handlers for the Ambulance Dispatch System.

Endpoints:
    POST /route              — Compute a shortest path
    GET  /traffic            — Current traffic state (all edges)
    GET  /graph              — Full graph topology (nodes + edges)
    POST /simulation/start   — Start the traffic simulation
    POST /simulation/stop    — Stop the traffic simulation
    POST /compare            — Run Dijkstra vs A* side-by-side
    GET  /dispatch/state     — Current dispatch system state
    POST /dispatch/emergency — Generate a random emergency
    POST /dispatch/assign    — Dispatch using specified algorithm
    POST /dispatch/compare   — Compare greedy vs hungarian
    POST /dispatch/reset     — Reset dispatch state
    WS   /updates            — Live traffic + dispatch update stream
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.services.routing_service import RoutingService
    from app.simulation.engine import TrafficEngine
    from app.dispatch.dispatch_service import DispatchService
    from app.graph.graph import Graph


logger = logging.getLogger("dispatch.routes")


# ── Request / Response models ─────────────────────────────────────────────


class RouteRequest(BaseModel):
    source: str
    destination: str
    algorithm: str = "dijkstra"


class CompareRequest(BaseModel):
    source: str
    destination: str


class DispatchAssignRequest(BaseModel):
    algorithm: str = "greedy"  # "greedy" or "hungarian"
    emergency_id: Optional[str] = None


class DispatchCompareRequest(BaseModel):
    emergency_id: Optional[str] = None


class SimSpeedRequest(BaseModel):
    tick_interval: float = 3.0  # seconds per tick


# ── Router factory ────────────────────────────────────────────────────────


def create_router(
    graph: "Graph",
    engine: "TrafficEngine",
    routing: "RoutingService",
    dispatch: "DispatchService",
) -> APIRouter:
    """
    Build and return an ``APIRouter`` wired to the given services.

    This avoids global state — all dependencies are injected.
    """
    router = APIRouter()

    # Connected WebSocket clients
    ws_clients: list[WebSocket] = []

    # ── Helper: broadcast to all WS clients ───────────────────────────

    async def _broadcast(event_type: str, payload: dict) -> None:
        """Send a JSON message to every connected WebSocket client."""
        message = json.dumps({"type": event_type, "data": payload})
        disconnected: list[WebSocket] = []
        for ws in ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            ws_clients.remove(ws)

    # We need an event loop reference to schedule broadcasts from
    # synchronous callbacks (traffic engine runs in a thread).
    _loop: asyncio.AbstractEventLoop | None = None

    def _sync_broadcast(event_type: str, payload: dict) -> None:
        """Thread-safe broadcast — schedules onto the asyncio event loop."""
        if _loop is None or _loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(_broadcast(event_type, payload), _loop)

    # ── Wire callbacks ────────────────────────────────────────────────

    def _on_traffic_change(changes: list[dict]) -> None:
        _sync_broadcast("traffic_update", {
            "changes": changes,
            "time_of_day": engine.time_of_day.value
        })

    def _on_route_update(result, reason: str) -> None:
        _sync_broadcast("route_update", result.to_dict())

    def _on_dispatch_event(event_type: str, data: dict) -> None:
        _sync_broadcast(event_type, data)

    engine.on_change(_on_traffic_change)
    routing.on_route_update(_on_route_update)
    dispatch.on_dispatch_event(_on_dispatch_event)

    # ── REST endpoints ────────────────────────────────────────────────

    @router.post("/route")
    async def compute_route(req: RouteRequest) -> dict:
        """Compute shortest path and set as active route."""
        try:
            node_ids = [n.id for n in graph.get_all_nodes()]
            if req.source not in node_ids:
                raise HTTPException(400, f"Source node '{req.source}' not found")
            if req.destination not in node_ids:
                raise HTTPException(400, f"Destination node '{req.destination}' not found")
            result = routing.compute_route(req.source, req.destination, req.algorithm)
            return result.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Route computation failed: {e}")
            raise HTTPException(500, f"Route computation failed: {e}")

    @router.post("/route/trace")
    async def compute_route_trace(req: RouteRequest) -> dict:
        """Compute shortest path with full exploration trace for animation."""
        try:
            from app.algorithms.trace import dijkstra_trace, astar_trace
            trace_fn = astar_trace if req.algorithm == "astar" else dijkstra_trace
            result, trace = trace_fn(graph, req.source, req.destination)
            routing.compute_route(req.source, req.destination, req.algorithm)
            return {"result": result.to_dict(), "trace": trace}
        except Exception as e:
            logger.error(f"Route trace failed: {e}")
            raise HTTPException(500, f"Route trace failed: {e}")

    @router.get("/traffic")
    async def get_traffic() -> dict:
        """Return current traffic state for all edges."""
        try:
            edges = graph.get_all_edges()
            return {
                "edges": [
                    {
                        "from_node": e.from_node,
                        "to_node": e.to_node,
                        "base_weight": e.base_weight,
                        "current_weight": e.current_weight,
                        "status": e.status.value,
                    }
                    for e in edges
                ]
            }
        except Exception as e:
            logger.error(f"Traffic fetch failed: {e}")
            raise HTTPException(500, f"Traffic fetch failed: {e}")

    @router.get("/graph")
    async def get_graph() -> dict:
        """Return the full graph topology."""
        try:
            return graph.to_dict()
        except Exception as e:
            logger.error(f"Graph fetch failed: {e}")
            raise HTTPException(500, f"Graph fetch failed: {e}")

    @router.post("/simulation/start")
    async def start_simulation() -> dict:
        """Start the background traffic simulation."""
        try:
            engine.start()
            return {"status": "running"}
        except Exception as e:
            logger.error(f"Simulation start failed: {e}")
            raise HTTPException(500, f"Simulation start failed: {e}")

    @router.post("/simulation/stop")
    async def stop_simulation() -> dict:
        """Stop the background traffic simulation."""
        try:
            engine.stop()
            return {"status": "stopped"}
        except Exception as e:
            logger.error(f"Simulation stop failed: {e}")
            raise HTTPException(500, f"Simulation stop failed: {e}")

    @router.get("/simulation/status")
    async def simulation_status() -> dict:
        """Check whether the simulation is running."""
        return {
            "running": engine.is_running,
            "tick_interval": engine.tick_interval,
            "time_of_day": engine.time_of_day.value
        }

    @router.post("/simulation/speed")
    async def set_simulation_speed(req: SimSpeedRequest) -> dict:
        """Change the simulation tick interval."""
        try:
            engine.set_tick_interval(req.tick_interval)
            return {"tick_interval": engine.tick_interval}
        except Exception as e:
            logger.error(f"Speed change failed: {e}")
            raise HTTPException(500, f"Speed change failed: {e}")

    @router.post("/compare")
    async def compare_algorithms(req: CompareRequest) -> dict:
        """Run Dijkstra and A* side-by-side for performance comparison."""
        try:
            results = routing.compare_algorithms(req.source, req.destination)
            return {algo: r.to_dict() for algo, r in results.items()}
        except Exception as e:
            logger.error(f"Algorithm comparison failed: {e}")
            raise HTTPException(500, f"Algorithm comparison failed: {e}")

    @router.get("/active-route")
    async def get_active_route() -> dict:
        """Return the currently active route, if any."""
        result = routing.active_result
        if result is None:
            return {"active": False}
        return {"active": True, **result.to_dict()}

    # ── Dispatch endpoints ────────────────────────────────────────────

    @router.get("/dispatch/state")
    async def dispatch_state() -> dict:
        """Return current ambulances, hospitals, and emergencies."""
        try:
            return dispatch.get_state()
        except Exception as e:
            logger.error(f"Dispatch state fetch failed: {e}")
            raise HTTPException(500, f"Dispatch state fetch failed: {e}")

    @router.post("/dispatch/emergency")
    async def dispatch_emergency() -> dict:
        """Generate a random emergency."""
        try:
            emg = dispatch.generate_emergency()
            return emg.to_dict()
        except Exception as e:
            logger.error(f"Emergency generation failed: {e}")
            raise HTTPException(500, f"Emergency generation failed: {e}")

    @router.post("/dispatch/assign")
    async def dispatch_assign(req: DispatchAssignRequest) -> dict:
        """Dispatch ambulance(s) using the specified algorithm."""
        try:
            if req.algorithm not in ("greedy", "hungarian"):
                raise HTTPException(400, f"Unknown algorithm: '{req.algorithm}'. Use 'greedy' or 'hungarian'.")
            if req.algorithm == "hungarian":
                results = dispatch.dispatch_hungarian()
                if not results:
                    raise HTTPException(409, "No available ambulances or pending emergencies")
                return {"assignments": [r.to_dict() for r in results]}
            else:
                result = dispatch.dispatch_greedy(req.emergency_id)
                if result is None:
                    raise HTTPException(409, "No available ambulance or pending emergency")
                return {"assignments": [result.to_dict()]}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Dispatch assign failed: {e}")
            raise HTTPException(500, f"Dispatch failed: {e}")

    @router.post("/dispatch/compare")
    async def dispatch_compare(req: DispatchCompareRequest) -> dict:
        """Compare greedy vs hungarian for a pending emergency."""
        try:
            result = dispatch.compare_methods(req.emergency_id)
            if "error" in result:
                raise HTTPException(409, result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Dispatch compare failed: {e}")
            raise HTTPException(500, f"Dispatch compare failed: {e}")

    @router.post("/dispatch/reset")
    async def dispatch_reset() -> dict:
        """Reset all dispatch state and traffic conditions."""
        try:
            dispatch.reset()
            engine.reset_traffic()
            return {"status": "reset"}
        except Exception as e:
            logger.error(f"Dispatch reset failed: {e}")
            raise HTTPException(500, f"Dispatch reset failed: {e}")

    # ── WebSocket ─────────────────────────────────────────────────────

    @router.websocket("/updates")
    async def websocket_updates(ws: WebSocket) -> None:
        """
        Live update stream.

        Pushes event types:
          • ``traffic_update``    — when edges change
          • ``route_update``      — when the active path is recomputed
          • ``emergency_new``     — when an emergency is generated
          • ``dispatch_assigned`` — when an ambulance is dispatched
        """
        nonlocal _loop
        await ws.accept()
        ws_clients.append(ws)

        # Capture event loop on first WS connection
        if _loop is None:
            _loop = asyncio.get_running_loop()

        try:
            # Keep connection alive — client can also send pings
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            if ws in ws_clients:
                ws_clients.remove(ws)

    return router
