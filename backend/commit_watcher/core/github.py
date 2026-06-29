"""Async GitHub REST client: list commits (ETag-conditional) + fetch diffs.

Unchanged commit listings return HTTP 304 via ``If-None-Match`` and cost zero
against the rate limit — the key efficiency lever that makes tight polling safe.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..settings import settings
from .filters import CommitData


@dataclass
class CommitsResponse:
    status: int  # 200, 304, or an error code
    commits: list[dict]  # raw GitHub commit objects (empty on 304/error)
    etag: str | None
    rate_remaining: int | None
    error: str | None = None


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str | None = None):
        self._token = token if token is not None else settings.github_token
        self._base = (base_url or settings.github_api).rstrip("/")

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        h = {
            "Accept": accept,
            "User-Agent": settings.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def list_commits(
        self,
        repo: str,
        *,
        branch: str | None = None,
        etag: str | None = None,
        per_page: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> CommitsResponse:
        params: dict[str, str | int] = {"per_page": per_page}
        if branch:
            params["sha"] = branch
        headers = self._headers()
        if etag:
            headers["If-None-Match"] = etag

        owns = client is None
        client = client or httpx.AsyncClient(timeout=20)
        try:
            r = await client.get(
                f"{self._base}/repos/{repo}/commits", params=params, headers=headers
            )
            remaining = _int_or_none(r.headers.get("X-RateLimit-Remaining"))
            new_etag = r.headers.get("ETag", etag)
            if r.status_code == 304:
                return CommitsResponse(304, [], new_etag, remaining)
            if r.status_code != 200:
                return CommitsResponse(
                    r.status_code, [], new_etag, remaining, error=r.text[:300]
                )
            return CommitsResponse(200, r.json(), new_etag, remaining)
        except httpx.HTTPError as e:
            return CommitsResponse(0, [], etag, None, error=str(e))
        finally:
            if owns:
                await client.aclose()

    async def fetch_commit_detail(
        self, repo: str, sha: str, *, client: httpx.AsyncClient | None = None
    ) -> CommitData | None:
        """Fetch a single commit's files + per-file patch and build CommitData."""
        owns = client is None
        client = client or httpx.AsyncClient(timeout=30)
        try:
            r = await client.get(
                f"{self._base}/repos/{repo}/commits/{sha}", headers=self._headers()
            )
            if r.status_code != 200:
                return None
            return commit_data_from_detail(r.json())
        except httpx.HTTPError:
            return None
        finally:
            if owns:
                await client.aclose()


def _int_or_none(v: str | None) -> int | None:
    try:
        return int(v) if v is not None else None
    except ValueError:
        return None


def commit_data_from_summary(c: dict) -> CommitData:
    """Build CommitData from a list-commits entry (no files/diff)."""
    commit = c.get("commit", {})
    author = commit.get("author", {}) or {}
    return CommitData(
        sha=c.get("sha", ""),
        message=commit.get("message", ""),
        author_name=author.get("name", "") or "",
        author_email=author.get("email", "") or "",
    )


def commit_data_from_detail(c: dict) -> CommitData:
    """Build CommitData from a single-commit response (includes files + patches)."""
    base = commit_data_from_summary(c)
    files = c.get("files", []) or []
    base.changed_files = [f.get("filename", "") for f in files if f.get("filename")]
    base.diff_text = "\n".join(f.get("patch", "") for f in files if f.get("patch"))
    return base
