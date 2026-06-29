"""Service layer: the single source of business logic for REST, CLI, MCP, and
the background poller. Everything goes through here so the human and agent
surfaces never drift apart.
"""
from __future__ import annotations

import logging

import httpx

from . import metrics
from . import repository as repo
from .clock import now_local
from .core import github, notify, render
from .core.filters import evaluate
from .core.models import Channel, Match, PollState, Watch
from .core.schemas import (
    ChannelCreate,
    DryRunResult,
    FilterSet,
    TemplateSpec,
    WatchCreate,
    WatchStatus,
    WatchUpdate,
)
from .db import get_session
from .settings import settings

log = logging.getLogger("github_watcher.services")


# ---- Watch CRUD -------------------------------------------------------------
def create_watch(data: WatchCreate) -> Watch:
    with get_session() as s:
        if repo.get_watch_by_name(s, data.name):
            raise ValueError(f"watch '{data.name}' already exists")
        watch = Watch(
            name=data.name,
            repo=data.repo,
            kind=data.kind,
            branch=data.branch,
            interval=data.interval,
            enabled=data.enabled,
            filters=data.filters.model_dump(exclude_none=True),
            template=data.template.model_dump(),
            channels=data.channels,
        )
        return repo.add_watch(s, watch)


def update_watch(watch_id: int, data: WatchUpdate) -> Watch:
    with get_session() as s:
        watch = repo.get_watch(s, watch_id)
        if not watch:
            raise KeyError(watch_id)
        patch = data.model_dump(exclude_unset=True)
        for key in ("repo", "kind", "branch", "interval", "enabled", "channels"):
            if key in patch:
                setattr(watch, key, patch[key])
        if data.filters is not None:
            watch.filters = data.filters.model_dump(exclude_none=True)
        if data.template is not None:
            watch.template = data.template.model_dump()
        return repo.save_watch(s, watch)


def delete_watch(watch_id: int) -> None:
    with get_session() as s:
        watch = repo.get_watch(s, watch_id)
        if not watch:
            raise KeyError(watch_id)
        repo.delete_watch(s, watch)


def list_watches() -> list[Watch]:
    with get_session() as s:
        return repo.list_watches(s)


def get_watch(watch_id: int) -> Watch | None:
    with get_session() as s:
        return repo.get_watch(s, watch_id)


# ---- Channel CRUD -----------------------------------------------------------
def create_channel(data: ChannelCreate) -> Channel:
    with get_session() as s:
        if repo.get_channel_by_name(s, data.name):
            raise ValueError(f"channel '{data.name}' already exists")
        return repo.add_channel(s, Channel(name=data.name, url=data.url))


def delete_channel(name: str) -> None:
    with get_session() as s:
        ch = repo.get_channel_by_name(s, name)
        if not ch:
            raise KeyError(name)
        repo.delete_channel(s, ch)


def list_channels() -> list[Channel]:
    with get_session() as s:
        return repo.list_channels(s)


async def test_channel(name: str) -> tuple[bool, str | None]:
    with get_session() as s:
        ch = repo.get_channel_by_name(s, name)
        if not ch:
            raise KeyError(name)
        url = ch.url
    return await notify.send(
        [url], "github-watcher test", "If you can read this, the channel works. ✅"
    )


# ---- Matches & status -------------------------------------------------------
def list_matches(watch_id: int | None = None, limit: int = 100) -> list[Match]:
    with get_session() as s:
        return repo.list_matches(s, watch_id=watch_id, limit=limit)


def get_status() -> list[WatchStatus]:
    out: list[WatchStatus] = []
    with get_session() as s:
        for w in repo.list_watches(s):
            st = repo.get_state(s, w.id)
            out.append(
                WatchStatus(
                    watch_id=w.id,
                    name=w.name,
                    enabled=w.enabled,
                    primed=bool(st and st.primed),
                    last_polled_at=st.last_polled_at if st else None,
                    last_status=st.last_status if st else None,
                    rate_remaining=st.rate_remaining if st else None,
                    last_error=st.last_error if st else None,
                    seen_count=len(st.seen) if st else 0,
                    match_count=repo.count_matches(s, w.id),
                )
            )
    return out


# ---- The poll/filter/notify core -------------------------------------------
def _filterset(watch: Watch) -> FilterSet:
    return FilterSet.model_validate(watch.filters or {})


async def _commit_data(client, gh, repo_name, summary, fs: FilterSet):
    data = github.commit_data_from_summary(summary)
    if fs.needs_diff():
        detail = await gh.fetch_commit_detail(repo_name, data.sha, client=client)
        if detail:
            data = detail
    return data


async def _listing(gh, watch: Watch, etag, client, per_page=30):
    if watch.kind == "issues":
        return await gh.list_issues(watch.repo, etag=etag, per_page=per_page, client=client)
    return await gh.list_commits(
        watch.repo, branch=watch.branch, etag=etag, per_page=per_page, client=client
    )


def _new_items(kind: str, items: list[dict], seen: set[str]) -> list[tuple[str, dict]]:
    """Unseen raw items, oldest-first. For issues, pull requests are skipped."""
    out: list[tuple[str, dict]] = []
    for raw in reversed(items):
        if kind == "issues":
            if "pull_request" in raw:  # the issues endpoint also returns PRs
                continue
            ident = str(raw.get("number") or "")
        else:
            ident = raw.get("sha") or ""
        if not ident or ident in seen:
            continue
        out.append((ident, raw))
    return out


async def _prepare(watch: Watch, raw: dict, fs: FilterSet, gh, client):
    """Build (filter_input, context_factory, match_kind) for one raw item."""
    if watch.kind == "issues":
        data = github.commit_data_from_issue(raw)

        def ctx(keywords):
            return render.build_issue_context(watch.repo, raw, keywords)

        return data, ctx, "issue"

    data = await _commit_data(client, gh, watch.repo, raw, fs)

    def ctx(keywords):
        return render.build_context(
            watch.repo, watch.branch, data, keywords, raw.get("html_url")
        )

    return data, ctx, "commit"


async def process_watch(watch_id: int, *, send: bool = True) -> list[Match]:
    """Poll a watch once: detect new commits/issues, filter, persist + notify."""
    with get_session() as s:
        watch = repo.get_watch(s, watch_id)
        if not watch:
            raise KeyError(watch_id)
        state = repo.get_state(s, watch_id) or PollState(watch_id=watch_id)
        etag = state.etag
        seen = set(state.seen)
        primed = state.primed
        fs = _filterset(watch)
        template = TemplateSpec.model_validate(watch.template or {})
        channel_urls = repo.resolve_channel_urls(s, watch.channels)

    gh = github.GitHubClient()
    created: list[Match] = []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _listing(gh, watch, etag, client)
        metrics.polls_total.labels(watch.name, str(resp.status)).inc()
        if resp.rate_remaining is not None:
            metrics.rate_remaining.labels(watch.name).set(resp.rate_remaining)

        if resp.status == 304:
            _save_state(watch_id, etag=resp.etag, status=304,
                        rate=resp.rate_remaining, error=None)
            return []
        if resp.status != 200:
            metrics.poll_errors_total.labels(watch.name).inc()
            _save_state(watch_id, etag=resp.etag, status=resp.status,
                        rate=resp.rate_remaining, error=resp.error)
            return []

        new = _new_items(watch.kind, resp.items, seen)
        for _ in new:
            metrics.commits_seen_total.labels(watch.name).inc()

        # First run: prime the seen-set without notifying (no cold-start spam).
        if not primed:
            for ident, _ in new:
                seen.add(ident)
            _save_state(watch_id, etag=resp.etag, status=200, rate=resp.rate_remaining,
                        error=None, seen=list(seen), primed=True)
            return []

        for ident, raw in new:
            seen.add(ident)
            data, ctx_factory, match_kind = await _prepare(watch, raw, fs, gh, client)
            result = evaluate(data, fs)
            if not result.matched:
                continue
            metrics.matches_total.labels(watch.name).inc()
            ctx = ctx_factory(result.keywords)
            title, body = render.render(template, ctx)
            match = Match(
                watch_id=watch_id, kind=match_kind, sha=ident, repo=watch.repo,
                branch=watch.branch if watch.kind == "commits" else None,
                author=ctx["item"]["author"], message=ctx["item"]["title"],
                url=ctx["item"]["url"], matched_keywords=result.keywords,
                changed_files=data.changed_files,
            )
            if send and channel_urls:
                ok, err = await notify.send(channel_urls, title, body)
                match.notified = ok
                match.notify_error = err
                metrics.notifications_total.labels(
                    watch.name, "ok" if ok else "error"
                ).inc()
            with get_session() as s:
                created.append(repo.add_match(s, match))

    _save_state(watch_id, etag=resp.etag, status=200, rate=resp.rate_remaining,
                error=None, seen=list(seen), primed=True)
    return created


async def dry_run(watch_id: int, limit: int = 30) -> list[DryRunResult]:
    """Evaluate the latest commits/issues without touching state or sending."""
    with get_session() as s:
        watch = repo.get_watch(s, watch_id)
        if not watch:
            raise KeyError(watch_id)
        fs = _filterset(watch)
        template = TemplateSpec.model_validate(watch.template or {})

    gh = github.GitHubClient()
    out: list[DryRunResult] = []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _listing(gh, watch, None, client, per_page=limit)
        if resp.status != 200:
            raise RuntimeError(f"GitHub error {resp.status}: {resp.error}")
        items = _new_items(watch.kind, resp.items, set())  # evaluate all, skip PRs
        for ident, raw in items:
            data, ctx_factory, _ = await _prepare(watch, raw, fs, gh, client)
            result = evaluate(data, fs)
            title = body = None
            if result.matched:
                title, body = render.render(template, ctx_factory(result.keywords))
            out.append(
                DryRunResult(
                    sha=ident, author=data.author_name, message=data.message,
                    url=raw.get("html_url"), matched=result.matched,
                    matched_keywords=result.keywords, changed_files=data.changed_files,
                    rendered_title=title, rendered_body=body,
                )
            )
    return out


def _save_state(
    watch_id: int, *, etag, status, rate, error,
    seen: list[str] | None = None, primed: bool | None = None,
) -> None:
    with get_session() as s:
        st = repo.get_state(s, watch_id) or PollState(watch_id=watch_id)
        st.etag = etag
        st.last_status = status
        st.rate_remaining = rate
        st.last_error = error
        st.last_polled_at = now_local()
        if seen is not None:
            st.seen = seen[-settings.seen_cap:]
        if primed is not None:
            st.primed = primed
        repo.upsert_state(s, st)
