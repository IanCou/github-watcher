"""Background poller: one asyncio task per enabled watch, each on its own
interval. Started/stopped via the FastAPI lifespan (or `cli serve`). Shares the
service layer, so a future split into a standalone worker is a no-op.
"""
from __future__ import annotations

import asyncio
import logging

from . import services
from .settings import settings

log = logging.getLogger("commit_watcher.poller")


class Poller:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._supervisor = asyncio.create_task(self._supervise())

    async def stop(self) -> None:
        self._stop.set()
        for t in self._tasks.values():
            t.cancel()
        if getattr(self, "_supervisor", None):
            self._supervisor.cancel()

    async def _supervise(self) -> None:
        """Reconcile running tasks with the set of enabled watches every 15s."""
        while not self._stop.is_set():
            try:
                wanted = {w.id: w for w in services.list_watches() if w.enabled}
                for wid in list(self._tasks):
                    if wid not in wanted or self._tasks[wid].done():
                        self._tasks.pop(wid).cancel()
                for wid, w in wanted.items():
                    if wid not in self._tasks:
                        interval = w.interval or settings.default_interval
                        self._tasks[wid] = asyncio.create_task(
                            self._run_watch(wid, interval)
                        )
            except Exception:  # noqa: BLE001
                log.exception("supervisor loop error")
            await _sleep_or_stop(self._stop, 15)

    async def _run_watch(self, watch_id: int, interval: int) -> None:
        while not self._stop.is_set():
            try:
                created = await services.process_watch(watch_id)
                if created:
                    log.info("watch %s: %d new match(es)", watch_id, len(created))
            except KeyError:
                return  # watch deleted
            except Exception:  # noqa: BLE001
                log.exception("watch %s poll failed", watch_id)
            await _sleep_or_stop(self._stop, interval)


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass
