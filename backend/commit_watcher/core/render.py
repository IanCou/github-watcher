"""Jinja2 rendering of notification title/body from commit context."""
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
    return {
        "repo": repo,
        "branch": branch,
        "matched_keywords": matched_keywords,
        "changed_files": commit.changed_files,
        "commit": {
            "sha": commit.sha,
            "short_sha": commit.sha[:7],
            "message": message,
            "message_first_line": message.splitlines()[0] if message else "",
            "author": commit.author_name,
            "author_email": commit.author_email,
            "url": html_url or f"https://github.com/{repo}/commit/{commit.sha}",
        },
    }


def render(template: TemplateSpec, context: dict) -> tuple[str, str]:
    title = _env.from_string(template.title).render(**context)
    body = _env.from_string(template.body).render(**context)
    return title, body
