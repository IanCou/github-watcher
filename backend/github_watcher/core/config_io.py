"""YAML <-> DB import/export for portability/GitOps. The DB stays authoritative."""

from __future__ import annotations

from typing import Any

import yaml

from .. import repository as repo
from ..core.models import Channel, Watch
from ..core.schemas import WatchCreate
from ..db import get_session


def export_yaml() -> str:
    with get_session() as s:
        channels = {c.name: {"url": c.url} for c in repo.list_channels(s)}
        watches = []
        for w in repo.list_watches(s):
            entry: dict[str, Any] = {
                "name": w.name,
                "repo": w.repo,
                "channels": w.channels,
            }
            if w.kind != "commits":
                entry["kind"] = w.kind
            if w.branch:
                entry["branch"] = w.branch
            if w.interval:
                entry["interval"] = w.interval
            if not w.enabled:
                entry["enabled"] = False
            if w.filters:
                entry["filters"] = w.filters
            if w.template:
                entry["template"] = w.template
            watches.append(entry)
    return yaml.safe_dump({"channels": channels, "watches": watches}, sort_keys=False, width=100)


def import_yaml(text: str, *, replace: bool = False) -> tuple[int, int]:
    """Upsert channels + watches from YAML. Returns (channels, watches) counts."""
    doc = yaml.safe_load(text) or {}
    n_ch = n_w = 0
    with get_session() as s:
        if replace:
            for w in repo.list_watches(s):
                repo.delete_watch(s, w)
            for c in repo.list_channels(s):
                repo.delete_channel(s, c)

        for name, spec in (doc.get("channels") or {}).items():
            url = spec["url"] if isinstance(spec, dict) else spec
            existing = repo.get_channel_by_name(s, name)
            if existing:
                existing.url = url
                s.add(existing)
                s.commit()
            else:
                repo.add_channel(s, Channel(name=name, url=url))
            n_ch += 1

        for entry in doc.get("watches") or []:
            wc = WatchCreate.model_validate(entry)
            existing = repo.get_watch_by_name(s, wc.name)
            payload = dict(
                repo=wc.repo,
                kind=wc.kind,
                branch=wc.branch,
                interval=wc.interval,
                enabled=wc.enabled,
                filters=wc.filters.model_dump(exclude_none=True),
                template=wc.template.model_dump(),
                channels=wc.channels,
            )
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
                repo.save_watch(s, existing)
            else:
                repo.add_watch(s, Watch(name=wc.name, **payload))
            n_w += 1
    return n_ch, n_w
