"""SQLite engine + session/init helpers."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from .settings import settings

# check_same_thread=False so the engine is usable from the poller task + API.
_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    # Import models so tables register on SQLModel.metadata.
    from .core import models  # noqa: F401

    SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(_engine) as session:
        yield session


def engine():
    return _engine
