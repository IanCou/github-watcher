"""MCP server exposing commit-watcher to agents (Claude et al.).

Tools mirror the service layer so an agent can manage watches/channels and query
matches with the same semantics as the UI/CLI/REST. Run with:

    python -m commit_watcher.mcp_server      # stdio transport
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import services
from .core.schemas import ChannelCreate, FilterSet, TemplateSpec, WatchCreate, WatchUpdate
from .db import init_db

mcp = FastMCP("commit-watcher")


@mcp.tool()
def list_watches() -> list[dict]:
    """List all watches with their repo, branch, filters, and channels."""
    return [
        {
            "id": w.id, "name": w.name, "repo": w.repo, "branch": w.branch,
            "interval": w.interval, "enabled": w.enabled, "filters": w.filters,
            "channels": w.channels,
        }
        for w in services.list_watches()
    ]


@mcp.tool()
def add_watch(
    name: str,
    repo: str,
    channels: list[str],
    branch: str | None = None,
    interval: int | None = None,
    filters: dict[str, Any] | None = None,
    template: dict[str, Any] | None = None,
) -> dict:
    """Create a watch. `repo` is 'owner/name'. `filters` may set message/author/
    files/diff, each with include/exclude lists (files=globs, message/diff=regex).
    """
    w = services.create_watch(
        WatchCreate(
            name=name, repo=repo, branch=branch, interval=interval, channels=channels,
            filters=FilterSet.model_validate(filters or {}),
            template=TemplateSpec.model_validate(template or {}),
        )
    )
    return {"id": w.id, "name": w.name}


@mcp.tool()
def update_watch(watch_id: int, patch: dict[str, Any]) -> dict:
    """Update fields of a watch (repo/branch/interval/enabled/filters/template/channels)."""
    w = services.update_watch(watch_id, WatchUpdate.model_validate(patch))
    return {"id": w.id, "name": w.name}


@mcp.tool()
def delete_watch(watch_id: int) -> str:
    """Delete a watch and its history."""
    services.delete_watch(watch_id)
    return f"deleted {watch_id}"


@mcp.tool()
def list_channels() -> list[dict]:
    """List notification channels (Apprise URLs may be redacted by the client)."""
    return [{"id": c.id, "name": c.name, "url": c.url} for c in services.list_channels()]


@mcp.tool()
def add_channel(name: str, url: str) -> dict:
    """Add a notification channel. `url` is an Apprise URL (ntfy://, discord://, …)."""
    c = services.create_channel(ChannelCreate(name=name, url=url))
    return {"id": c.id, "name": c.name}


@mcp.tool()
async def test_channel(name: str) -> dict:
    """Send a test notification to a channel."""
    ok, err = await services.test_channel(name)
    return {"ok": ok, "error": err}


@mcp.tool()
def get_matches(watch_id: int | None = None, limit: int = 50) -> list[dict]:
    """Return recent matches (filtered commits), newest first."""
    return [
        {
            "watch_id": m.watch_id, "sha": m.sha, "repo": m.repo, "author": m.author,
            "message": (m.message or "").splitlines()[0] if m.message else "",
            "matched_keywords": m.matched_keywords, "url": m.url,
            "notified": m.notified, "created_at": m.created_at.isoformat(),
        }
        for m in services.list_matches(watch_id=watch_id, limit=limit)
    ]


@mcp.tool()
async def run_now(watch_id: int) -> dict:
    """Poll a watch immediately; returns the number of new matches."""
    created = await services.process_watch(watch_id)
    return {"new_matches": len(created)}


@mcp.tool()
async def dry_run(watch_id: int, limit: int = 30) -> list[dict]:
    """Evaluate the latest commits against a watch's filters without sending."""
    results = await services.dry_run(watch_id, limit=limit)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
def get_status() -> list[dict]:
    """Per-watch health: last poll, status, rate limit, error, counts."""
    return [s.model_dump(mode="json") for s in services.get_status()]


def main() -> None:
    init_db()
    mcp.run()


if __name__ == "__main__":
    main()
