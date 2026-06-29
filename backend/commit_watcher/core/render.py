"""Jinja2 rendering of notification title/body from commit/issue context.

Every context exposes a kind-neutral ``item`` (title/author/ref/url) so one
template works for both. Commit watches additionally get ``commit.*`` and issue
watches ``issue.*`` for richer templates.
"""
from __future__ import annotations

from jinja2 import Environment, StrictUndefined

from .filters import CommitData
from .schemas import TemplateSpec

_env = Environment(undefined=StrictUndefined, autoescape=False, trim_blocks=True)


def build_context(
    repo: str,
    branch: str | None,
    commit: CommitData,
    matched_keywords: list[str],
    html_url: str | None,
) -> dict:
    message = commit.message or ""
    first_line = message.splitlines()[0] if message else ""
    url = html_url or f"https://github.com/{repo}/commit/{commit.sha}"
    return {
        "repo": repo,
        "branch": branch,
        "matched_keywords": matched_keywords,
        "changed_files": commit.changed_files,
        "item": {
            "title": first_line,
            "author": commit.author_name,
            "ref": commit.sha[:7],
            "url": url,
        },
        "commit": {
            "sha": commit.sha,
            "short_sha": commit.sha[:7],
            "message": message,
            "message_first_line": first_line,
            "author": commit.author_name,
            "author_email": commit.author_email,
            "url": url,
        },
    }


def build_issue_context(
    repo: str,
    issue: dict,
    matched_keywords: list[str],
) -> dict:
    number = issue.get("number")
    title = issue.get("title", "") or ""
    url = issue.get("html_url", "") or ""
    author = (issue.get("user", {}) or {}).get("login", "") or ""
    labels = [label.get("name", "") for label in issue.get("labels", []) or []]
    return {
        "repo": repo,
        "branch": None,
        "matched_keywords": matched_keywords,
        "changed_files": [],
        "item": {
            "title": title,
            "author": author,
            "ref": f"#{number}",
            "url": url,
        },
        "issue": {
            "number": number,
            "title": title,
            "body": issue.get("body", "") or "",
            "author": author,
            "url": url,
            "labels": labels,
        },
    }


def render(template: TemplateSpec, context: dict) -> tuple[str, str]:
    title = _env.from_string(template.title).render(**context)
    body = _env.from_string(template.body).render(**context)
    return title, body
