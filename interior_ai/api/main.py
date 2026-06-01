"""FastAPI application factory."""

from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from .session_manager import SessionManager
from .routes import upload_router, design_router, render_router, edit_router
from .models import HealthResponse
from ..blender_integration.blender_bridge import BlenderBridge
from ..blender_integration.render_manager import RenderManager
from ..furniture.asset_manager import AssetManager
from ..furniture.furniture_db import FurnitureDatabase


def create_app(config: dict | None = None) -> FastAPI:
    cfg = config or {}

    app = FastAPI(
        title="Interior AI Designer",
        description="Open-source AI-powered interior design platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins = cfg.get("cors_origins", [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Shared state ─────────────────────────────────────────────────────
    assets_root = cfg.get("assets_root", "./assets")
    blender_exec = os.environ.get("BLENDER_PATH", "/usr/bin/blender")

    app.state.session_manager = SessionManager(
        timeout_minutes=cfg.get("session_timeout_minutes", 60)
    )
    app.state.blender_bridge = BlenderBridge(
        blender_executable=blender_exec,
    )
    app.state.render_manager = RenderManager(
        output_root=cfg.get("output_renders", "./output/renders"),
        max_parallel=cfg.get("max_parallel_renders", 2),
        blender_bridge=app.state.blender_bridge,
    )
    app.state.furniture_db = FurnitureDatabase()
    app.state.asset_manager = AssetManager(
        assets_root=assets_root,
        db=app.state.furniture_db,
    )

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(upload_router)
    app.include_router(design_router)
    app.include_router(render_router)
    app.include_router(edit_router)

    # ── Furniture assets endpoint ─────────────────────────────────────────
    from fastapi import APIRouter
    from .models import AssetListResponse

    assets_router = APIRouter(prefix="/assets", tags=["assets"])

    @assets_router.get("/furniture", response_model=AssetListResponse)
    async def list_furniture(category: str = "", style: str = ""):
        db: FurnitureDatabase = app.state.furniture_db
        if category:
            from ..types import FurnitureCategory
            try:
                assets = db.by_category(FurnitureCategory(category))
            except ValueError:
                assets = []
        elif style:
            assets = db.by_style(style)
        else:
            assets = db.all_assets()
        return AssetListResponse(
            assets=[{
                "id": a.id,
                "name": a.name,
                "category": a.category.value,
                "license": a.license,
                "source": a.source,
                "dimensions_m": [a.dimensions_m.x, a.dimensions_m.y, a.dimensions_m.z],
                "styles": a.styles,
                "tags": a.tags,
            } for a in assets],
            total=len(assets),
        )

    @assets_router.get("/hdri")
    async def list_hdri():
        from ..lighting.hdri_manager import HDRIManager
        mgr = HDRIManager(f"{assets_root}/hdri")
        return {"hdri_maps": mgr.available()}

    app.include_router(assets_router)

    # ── Health ────────────────────────────────────────────────────────────
    @app.get("/health", response_model=HealthResponse)
    async def health():
        blender_ok = app.state.blender_bridge.is_available()
        return HealthResponse(
            status="ok",
            blender_available=blender_ok,
        )

    @app.get("/")
    async def root():
        return {
            "name": "Interior AI Designer API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    # ── Session cleanup background task ───────────────────────────────────
    from fastapi import BackgroundTasks
    import asyncio

    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(_prune_sessions(app))

    return app


async def _prune_sessions(app: FastAPI):
    import asyncio
    while True:
        await asyncio.sleep(300)  # every 5 minutes
        try:
            pruned = app.state.session_manager.prune_expired()
            if pruned:
                print(f"[session] Pruned {pruned} expired sessions")
        except Exception:
            pass
