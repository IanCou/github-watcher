"""SQLModel tables: Channel, Watch, Match, PollState.

Watch filter/template/channel config is stored as JSON columns so the schema
stays flat while the filter engine evolves. Pydantic DTOs in ``schemas.py``
validate the shape on the way in and out.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from ..clock import now_local


def _now() -> datetime:
    return now_local()


class Channel(SQLModel, table=True):
    """A named Apprise notification target (ntfy://, discord://, …)."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: str  # Apprise URL; may contain ${ENV} placeholders resolved at send time.
    created_at: datetime = Field(default_factory=_now)


class Watch(SQLModel, table=True):
    """A single repo/branch poll target with filters, channels, and template."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    repo: str  # "owner/name"
    kind: str = "commits"  # "commits" | "issues"
    branch: str | None = None  # commits only; None -> repo default branch
    interval: int | None = None  # seconds; None -> settings.default_interval
    enabled: bool = True

    # JSON blobs validated by schemas.FilterSet / TemplateSpec.
    filters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    template: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    channels: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class PollState(SQLModel, table=True):
    """Per-watch poll bookkeeping: ETag, seen SHAs, last result, errors."""

    watch_id: int = Field(primary_key=True, foreign_key="watch.id")
    etag: str | None = None
    seen: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    primed: bool = False
    last_polled_at: datetime | None = None
    last_status: int | None = None  # last HTTP status (200/304/4xx)
    rate_remaining: int | None = None
    last_error: str | None = None


class Match(SQLModel, table=True):
    """A commit or issue that passed a watch's filters (history record)."""

    id: int | None = Field(default=None, primary_key=True)
    watch_id: int = Field(index=True, foreign_key="watch.id")
    kind: str = "commit"  # "commit" | "issue"
    sha: str = Field(index=True)  # commit SHA, or issue number as a string
    repo: str
    branch: str | None = None
    author: str | None = None
    message: str | None = None
    url: str | None = None
    matched_keywords: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    changed_files: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    notified: bool = False
    notify_error: str | None = None
    created_at: datetime = Field(default_factory=_now)
