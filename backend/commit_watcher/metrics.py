"""Prometheus metrics."""
from __future__ import annotations

from prometheus_client import Counter, Gauge

polls_total = Counter(
    "commit_watcher_polls_total", "Commit-list polls performed", ["watch", "status"]
)
commits_seen_total = Counter(
    "commit_watcher_commits_seen_total", "New commits observed", ["watch"]
)
matches_total = Counter(
    "commit_watcher_matches_total", "Commits that passed filters", ["watch"]
)
notifications_total = Counter(
    "commit_watcher_notifications_total", "Notifications dispatched", ["watch", "result"]
)
rate_remaining = Gauge(
    "commit_watcher_github_rate_remaining", "GitHub rate-limit remaining", ["watch"]
)
poll_errors_total = Counter(
    "commit_watcher_poll_errors_total", "Polling errors", ["watch"]
)
