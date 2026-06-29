"""Timestamp helper. All stored timestamps use the host's local timezone
(timezone-aware), so the UI/CLI/API show times in the machine's local zone.
"""

from __future__ import annotations

from datetime import datetime


def now_local() -> datetime:
    # datetime.now().astimezone() attaches the system local timezone offset.
    return datetime.now().astimezone()
