"""Channel CRUD + test."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import services
from ...core.schemas import ChannelCreate, ChannelRead

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@router.get("", response_model=list[ChannelRead])
def list_channels() -> list[ChannelRead]:
    return [ChannelRead(id=c.id, name=c.name, url=c.url) for c in services.list_channels()]


@router.post("", response_model=ChannelRead, status_code=201)
def create_channel(data: ChannelCreate) -> ChannelRead:
    try:
        c = services.create_channel(data)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return ChannelRead(id=c.id, name=c.name, url=c.url)


@router.delete("/{name}", status_code=204)
def delete_channel(name: str) -> None:
    try:
        services.delete_channel(name)
    except KeyError as e:
        raise HTTPException(404, "channel not found") from e


@router.post("/{name}/test")
async def test_channel(name: str) -> dict:
    try:
        ok, err = await services.test_channel(name)
    except KeyError as e:
        raise HTTPException(404, "channel not found") from e
    return {"ok": ok, "error": err}
