"""Apprise-backed notifications with per-channel ${ENV} resolution + throttling.

Channel URLs may embed ``${VAR}`` placeholders so secrets stay in the
environment rather than the database. A small per-URL rate limiter spaces sends
to respect provider caps (e.g. Discord ~30/min).
"""
from __future__ import annotations

import asyncio
import os
import re
import time

import apprise

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def resolve_env(url: str) -> str:
    return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), url)


class _Throttle:
    """Minimum-interval gate keyed by resolved URL."""

    def __init__(self, min_interval: float = 2.0):
        self._min = min_interval
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            last = self._last.get(key, 0.0)
            delay = self._min - (now - last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last[key] = time.monotonic()


_throttle = _Throttle()


async def send(urls: list[str], title: str, body: str) -> tuple[bool, str | None]:
    """Send one notification to a fan-out of Apprise URLs.

    Returns (ok, error). ``ok`` is True only if every target accepted it.
    """
    if not urls:
        return True, None
    errors: list[str] = []
    for raw in urls:
        resolved = resolve_env(raw)
        await _throttle.wait(resolved)
        ap = apprise.Apprise()
        if not ap.add(resolved):
            errors.append(f"invalid channel url: {raw[:40]}")
            continue
        ok = await asyncio.to_thread(ap.notify, body=body, title=title)
        if not ok:
            errors.append(f"send failed: {raw[:40]}")
    if errors:
        return False, "; ".join(errors)
    return True, None
