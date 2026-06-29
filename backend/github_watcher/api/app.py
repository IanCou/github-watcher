"""FastAPI application: REST API, /metrics, /healthz, background poller, SPA."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..db import init_db
from ..poller import Poller
from ..settings import settings
from .routers import channels, config, matches, watches

logging.basicConfig(level=settings.log_level)

# Static SPA build (mounted only if present, e.g. in the Docker image).
_FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", "/app/frontend"))

_poller = Poller()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.environ.get("DISABLE_POLLER") != "1":
        await _poller.start()
    try:
        yield
    finally:
        await _poller.stop()


app = FastAPI(
    title="github-watcher",
    version="0.1.0",
    summary="Poll any GitHub repo, filter commits, and notify.",
    lifespan=lifespan,
)

app.include_router(watches.router)
app.include_router(channels.router)
app.include_router(matches.router)
app.include_router(config.router)


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics", tags=["ops"])
def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _mount_spa() -> None:
    """Serve the built SPA with history-API fallback, if it exists."""
    if not (_FRONTEND_DIR / "index.html").exists():
        return
    assets = _FRONTEND_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = _FRONTEND_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIR / "index.html")


_mount_spa()
