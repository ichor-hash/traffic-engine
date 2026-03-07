"""
FastAPI application entry point.

Wires together:
  • Graph loaded from ``data/map.json``
  • TrafficEngine (background simulation)
  • RoutingService (pathfinding + recomputation)
  • API routes + WebSocket

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.graph.graph import Graph
from app.simulation.engine import TrafficEngine, TrafficConfig
from app.services.routing_service import RoutingService
from app.dispatch.dispatch_service import DispatchService
from app.api.routes import create_router

# ── Bootstrap ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAP_FILE = DATA_DIR / "map.json"

# 1. Load graph
graph = Graph()
graph.load_from_json(MAP_FILE)

# 2. Create services
traffic_config = TrafficConfig(tick_interval=3.0)
engine = TrafficEngine(graph, traffic_config)
routing = RoutingService(graph)
dispatch = DispatchService(graph)

# Wire traffic changes into routing (selective recomputation)
engine.on_change(routing.on_traffic_change)

# Wire hospital dynamics — tick hospitals alongside traffic
def _on_traffic_tick(changes: list[dict]) -> None:
    dispatch.tick_hospitals()

engine.on_change(_on_traffic_tick)

# 3. Build FastAPI app
app = FastAPI(
    title="Ambulance Dispatch System",
    description="Emergency dispatch with Greedy & Hungarian algorithms on real map data",
    version="2.0.0",
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Mount routes
router = create_router(graph, engine, routing, dispatch)
app.include_router(router)

# 5. Global exception handler
logger = logging.getLogger("dispatch")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and return a clean JSON error."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "simulation": engine.is_running,
        "nodes": len(graph.get_all_nodes()),
        "edges": len(graph.get_all_edges()),
    }


# ── Lifecycle hooks ───────────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown() -> None:
    """Ensure the simulation thread is stopped cleanly."""
    engine.stop()
