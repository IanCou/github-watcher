"""Test config. The DB env is set at import time (before any test module imports
github_watcher.db, whose engine binds at import) so DB-backed tests are isolated.
"""

import os
import tempfile

# Set before github_watcher.settings / github_watcher.db are imported.
_TMPDB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMPDB}")
os.environ.setdefault("DISABLE_POLLER", "1")

import pytest  # noqa: E402


@pytest.fixture
def fresh_db():
    """Reset the isolated test database to empty tables before each test."""
    from sqlmodel import SQLModel

    from github_watcher.db import engine, init_db

    SQLModel.metadata.drop_all(engine())
    init_db()
    yield
