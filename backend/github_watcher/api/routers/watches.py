"""Watch CRUD + per-watch actions (run-now, dry-run)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import services
from ...core.schemas import (
    DryRunResult,
    MatchRead,
    WatchCreate,
    WatchRead,
    WatchUpdate,
)

router = APIRouter(prefix="/api/v1/watches", tags=["watches"])


def _read(w) -> WatchRead:
    return WatchRead(
        id=w.id,
        name=w.name,
        repo=w.repo,
        kind=w.kind,
        branch=w.branch,
        interval=w.interval,
        enabled=w.enabled,
        filters=w.filters,
        template=w.template,
        channels=w.channels,
    )


@router.get("", response_model=list[WatchRead])
def list_watches() -> list[WatchRead]:
    return [_read(w) for w in services.list_watches()]


@router.post("", response_model=WatchRead, status_code=201)
def create_watch(data: WatchCreate) -> WatchRead:
    try:
        return _read(services.create_watch(data))
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/{watch_id}", response_model=WatchRead)
def get_watch(watch_id: int) -> WatchRead:
    w = services.get_watch(watch_id)
    if not w:
        raise HTTPException(404, "watch not found")
    return _read(w)


@router.patch("/{watch_id}", response_model=WatchRead)
def update_watch(watch_id: int, data: WatchUpdate) -> WatchRead:
    try:
        return _read(services.update_watch(watch_id, data))
    except KeyError as e:
        raise HTTPException(404, "watch not found") from e


@router.delete("/{watch_id}", status_code=204)
def delete_watch(watch_id: int) -> None:
    try:
        services.delete_watch(watch_id)
    except KeyError as e:
        raise HTTPException(404, "watch not found") from e


@router.post("/{watch_id}/run", response_model=list[MatchRead])
async def run_now(watch_id: int) -> list[MatchRead]:
    try:
        created = await services.process_watch(watch_id)
    except KeyError as e:
        raise HTTPException(404, "watch not found") from e
    return [MatchRead.model_validate(m, from_attributes=True) for m in created]


@router.post("/{watch_id}/dry-run", response_model=list[DryRunResult])
async def dry_run(watch_id: int, limit: int = 30) -> list[DryRunResult]:
    try:
        return await services.dry_run(watch_id, limit=limit)
    except KeyError as e:
        raise HTTPException(404, "watch not found") from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
