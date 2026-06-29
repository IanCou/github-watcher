"""SQLite engine + session/init helpers."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from .settings import settings

# check_same_thread=False so the engine is usable from the poller task + API.
_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Columns added after the initial schema. SQLModel.create_all never ALTERs an
# existing table, so we add them by hand (idempotent) to upgrade older DBs.
_ADDED_COLUMNS = {
    "watch": [("kind", "VARCHAR NOT NULL DEFAULT 'commits'")],
    "match": [("kind", "VARCHAR NOT NULL DEFAULT 'commit'")],
}


def _migrate() -> None:
    with _engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            if not existing:
                continue  # table doesn't exist yet; create_all will build it fresh
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    # Import models so tables register on SQLModel.metadata.
    from .core import models  # noqa: F401

    SQLModel.metadata.create_all(_engine)
    _migrate()


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(_engine) as session:
        yield session


def engine():
    return _engine
