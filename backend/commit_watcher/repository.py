"""Data-access layer over SQLModel sessions. No business logic lives here."""
from __future__ import annotations

from sqlmodel import Session, select

from .clock import now_local
from .core.models import Channel, Match, PollState, Watch


# ---- Watches ----------------------------------------------------------------
def list_watches(s: Session) -> list[Watch]:
    return list(s.exec(select(Watch).order_by(Watch.name)).all())


def get_watch(s: Session, watch_id: int) -> Watch | None:
    return s.get(Watch, watch_id)


def get_watch_by_name(s: Session, name: str) -> Watch | None:
    return s.exec(select(Watch).where(Watch.name == name)).first()


def add_watch(s: Session, watch: Watch) -> Watch:
    s.add(watch)
    s.commit()
    s.refresh(watch)
    return watch


def save_watch(s: Session, watch: Watch) -> Watch:
    watch.updated_at = now_local()
    s.add(watch)
    s.commit()
    s.refresh(watch)
    return watch


def delete_watch(s: Session, watch: Watch) -> None:
    state = s.get(PollState, watch.id)
    if state:
        s.delete(state)
    for m in s.exec(select(Match).where(Match.watch_id == watch.id)).all():
        s.delete(m)
    s.delete(watch)
    s.commit()


# ---- Channels ---------------------------------------------------------------
def list_channels(s: Session) -> list[Channel]:
    return list(s.exec(select(Channel).order_by(Channel.name)).all())


def get_channel_by_name(s: Session, name: str) -> Channel | None:
    return s.exec(select(Channel).where(Channel.name == name)).first()


def add_channel(s: Session, channel: Channel) -> Channel:
    s.add(channel)
    s.commit()
    s.refresh(channel)
    return channel


def delete_channel(s: Session, channel: Channel) -> None:
    s.delete(channel)
    s.commit()


def resolve_channel_urls(s: Session, names: list[str]) -> list[str]:
    urls: list[str] = []
    for name in names:
        ch = get_channel_by_name(s, name)
        if ch:
            urls.append(ch.url)
    return urls


# ---- Poll state -------------------------------------------------------------
def get_state(s: Session, watch_id: int) -> PollState | None:
    return s.get(PollState, watch_id)


def upsert_state(s: Session, state: PollState) -> PollState:
    s.add(state)
    s.commit()
    s.refresh(state)
    return state


# ---- Matches ----------------------------------------------------------------
def add_match(s: Session, match: Match) -> Match:
    s.add(match)
    s.commit()
    s.refresh(match)
    return match


def list_matches(
    s: Session, *, watch_id: int | None = None, limit: int = 100
) -> list[Match]:
    stmt = select(Match).order_by(Match.created_at.desc()).limit(limit)
    if watch_id is not None:
        stmt = stmt.where(Match.watch_id == watch_id)
    return list(s.exec(stmt).all())


def count_matches(s: Session, watch_id: int) -> int:
    return len(s.exec(select(Match.id).where(Match.watch_id == watch_id)).all())
