"""YAML import/export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body
from fastapi.responses import PlainTextResponse

from ...core import config_io

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/export", response_class=PlainTextResponse)
def export_config() -> str:
    return config_io.export_yaml()


@router.post("/import")
def import_config(
    yaml_text: str = Body(..., media_type="text/plain"), replace: bool = False
) -> dict:
    channels, watches = config_io.import_yaml(yaml_text, replace=replace)
    return {"channels": channels, "watches": watches}
