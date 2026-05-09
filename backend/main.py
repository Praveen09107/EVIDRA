"""
EVIDRA Forensic Intelligence Platform — Backend Entrypoint.
Run with: uvicorn main:app --reload
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import db
from core.redis_client import close_redis
from core.storage import storage

# Routers
from api.auth import router as auth_router
from api.cases import router as cases_router
from api.pipeline import router as pipeline_router
from api.ws import router as ws_router
from api.timeline import router as timeline_router
from api.hotspots import router as hotspots_router
from api.graph import router as graph_router
from api.analysis import router as analysis_router
from api.agents import router as agents_router
from api.xai import router as xai_router
from api.replay import router as replay_router
from api.reports import router as reports_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evidra.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections
    logger.info("Starting EVIDRA backend...")
    await db.get_pool()
    storage.get_minio() # Ensure bucket exists
    yield
    # Shutdown: Clean up connections
    logger.info("Shutting down EVIDRA backend...")
    await db.close_pool()
    await close_redis()

app = FastAPI(
    title="EVIDRA API",
    description="Forensic Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — Unblock Dev B entirely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Dev: allow all. Prod: restrict to frontend domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Phase 3 & 9 routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(timeline_router, prefix="/api/v1")
app.include_router(hotspots_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(xai_router, prefix="/api/v1")
app.include_router(replay_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(ws_router) # WebSockets don't use standard api prefix

@app.get("/health")
async def health_check():
    """Simple health check."""
    return {"status": "ok", "service": "evidra-api"}
