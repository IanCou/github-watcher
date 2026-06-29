"""Match history + per-watch status."""

from __future__ import annotations

from fastapi import APIRouter

from ... import services
from ...core.schemas import MatchRead, WatchStatus

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


@router.get("/matches", response_model=list[MatchRead])
def list_matches(watch_id: int | None = None, limit: int = 100) -> list[MatchRead]:
    return [
        MatchRead.model_validate(m, from_attributes=True)
        for m in services.list_matches(watch_id=watch_id, limit=limit)
    ]


@router.get("/status", response_model=list[WatchStatus])
def status() -> list[WatchStatus]:
    return services.get_status()
