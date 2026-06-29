import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    """Give each test session a throwaway SQLite file + clean settings/engine."""
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DISABLE_POLLER", "1")
    yield
