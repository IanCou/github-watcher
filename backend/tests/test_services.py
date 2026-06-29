import pytest

from github_watcher import services
from github_watcher.core.schemas import (
    ChannelCreate,
    FilterSet,
    IncludeExclude,
    WatchCreate,
    WatchUpdate,
)


def test_channel_crud(fresh_db):
    c = services.create_channel(ChannelCreate(name="ntfy", url="ntfy://x@h/t"))
    assert c.id is not None
    assert [ch.name for ch in services.list_channels()] == ["ntfy"]
    with pytest.raises(ValueError):
        services.create_channel(ChannelCreate(name="ntfy", url="dup"))
    services.delete_channel("ntfy")
    assert services.list_channels() == []
    with pytest.raises(KeyError):
        services.delete_channel("missing")


def test_watch_crud_and_filters(fresh_db):
    w = services.create_watch(
        WatchCreate(
            name="w1",
            repo="o/r",
            channels=["ntfy"],
            filters=FilterSet(message=IncludeExclude(include=["fix"])),
        )
    )
    assert w.id is not None and w.kind == "commits"
    assert w.filters["message"]["include"] == ["fix"]

    updated = services.update_watch(w.id, WatchUpdate(enabled=False, interval=300))
    assert updated.enabled is False and updated.interval == 300

    assert len(services.list_watches()) == 1
    assert services.get_watch(w.id).name == "w1"

    with pytest.raises(ValueError):
        services.create_watch(WatchCreate(name="w1", repo="o/r", channels=[]))

    services.delete_watch(w.id)
    assert services.list_watches() == []
    with pytest.raises(KeyError):
        services.update_watch(w.id, WatchUpdate(enabled=True))


def test_issue_watch_creation(fresh_db):
    w = services.create_watch(
        WatchCreate(
            name="issues",
            repo="o/r",
            kind="issues",
            channels=[],
            filters=FilterSet(message=IncludeExclude(include=["(?i)google"])),
        )
    )
    assert w.kind == "issues"


def test_status_and_matches_empty(fresh_db):
    services.create_watch(WatchCreate(name="w", repo="o/r", channels=[]))
    status = services.get_status()
    assert len(status) == 1
    assert status[0].name == "w" and status[0].primed is False
    assert status[0].match_count == 0
    assert services.list_matches() == []
