"""Pydantic DTOs for API/CLI/MCP input + the validated filter/template shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class IncludeExclude(BaseModel):
    """A pair of pattern lists. Semantics depend on the filter category."""

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class FilterSet(BaseModel):
    """All filter categories for a watch. Every category is optional.

    A commit matches when it passes *every* configured category (AND). Within a
    category, it must match an include (if any are given) and match no exclude.
    """

    message: IncludeExclude | None = None  # regex on commit message
    author: IncludeExclude | None = None  # substring on author name/email
    files: IncludeExclude | None = None  # glob on changed file paths
    diff: IncludeExclude | None = None  # regex on added/removed diff lines

    def needs_diff(self) -> bool:
        """Whether evaluating this filter set requires fetching per-commit diffs."""
        return bool(self.files or self.diff)


class TemplateSpec(BaseModel):
    # `item` is kind-neutral (works for both commits and issues). Commit watches
    # may also use `commit.*`, issue watches `issue.*`.
    title: str = "{{ repo }}: {{ item.title }}"
    body: str = "{{ item.author }} · {{ item.ref }}"


class WatchCreate(BaseModel):
    name: str
    repo: str
    kind: Literal["commits", "issues"] = "commits"
    branch: str | None = None
    interval: int | None = Field(default=None, ge=5)
    enabled: bool = True
    filters: FilterSet = Field(default_factory=FilterSet)
    template: TemplateSpec = Field(default_factory=TemplateSpec)
    channels: list[str] = Field(default_factory=list)

    @field_validator("repo")
    @classmethod
    def _repo_shape(cls, v: str) -> str:
        if v.count("/") != 1 or v.startswith("/") or v.endswith("/"):
            raise ValueError("repo must be 'owner/name'")
        return v

    @model_validator(mode="after")
    def _filters_match_kind(self) -> WatchCreate:
        # files/diff inspect commit contents; they never apply to issues.
        if self.kind == "issues" and (self.filters.files or self.filters.diff):
            raise ValueError(
                "issue watches support only 'message' (title+body) and 'author' "
                "filters; 'files' and 'diff' are commit-only"
            )
        return self


class WatchUpdate(BaseModel):
    repo: str | None = None
    kind: Literal["commits", "issues"] | None = None
    branch: str | None = None
    interval: int | None = Field(default=None, ge=5)
    enabled: bool | None = None
    filters: FilterSet | None = None
    template: TemplateSpec | None = None
    channels: list[str] | None = None


class WatchRead(BaseModel):
    id: int
    name: str
    repo: str
    kind: str
    branch: str | None
    interval: int | None
    enabled: bool
    filters: dict[str, Any]
    template: dict[str, Any]
    channels: list[str]


class ChannelCreate(BaseModel):
    name: str
    url: str


class ChannelRead(BaseModel):
    id: int
    name: str
    url: str


class MatchRead(BaseModel):
    id: int
    watch_id: int
    kind: str
    sha: str
    repo: str
    branch: str | None
    author: str | None
    message: str | None
    url: str | None
    matched_keywords: list[str]
    changed_files: list[str]
    notified: bool
    notify_error: str | None
    created_at: datetime


class WatchStatus(BaseModel):
    watch_id: int
    name: str
    enabled: bool
    primed: bool
    last_polled_at: datetime | None
    last_status: int | None
    rate_remaining: int | None
    last_error: str | None
    seen_count: int
    match_count: int


class DryRunResult(BaseModel):
    """A rendered candidate from a dry run (not persisted, not sent)."""

    sha: str
    author: str | None
    message: str | None
    url: str | None
    matched: bool
    matched_keywords: list[str]
    changed_files: list[str]
    rendered_title: str | None = None
    rendered_body: str | None = None
