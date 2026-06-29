import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(fresh_db):
    # DISABLE_POLLER=1 (set in conftest) keeps the background poller off;
    # fresh_db resets tables so each test starts empty.
    from github_watcher.api.app import app

    with TestClient(app) as c:
        yield c


def test_healthz_and_metrics(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    m = client.get("/metrics")
    assert m.status_code == 200
    assert "github_watcher_polls_total" in m.text


def test_watch_and_channel_crud_over_http(client):
    assert (
        client.post("/api/v1/channels", json={"name": "ntfy", "url": "ntfy://x@h/t"}).status_code
        == 201
    )
    # duplicate -> 409
    assert client.post("/api/v1/channels", json={"name": "ntfy", "url": "y"}).status_code == 409

    r = client.post(
        "/api/v1/watches",
        json={
            "name": "w1",
            "repo": "octocat/Hello-World",
            "channels": ["ntfy"],
            "filters": {"message": {"include": ["fix"]}},
        },
    )
    assert r.status_code == 201, r.text
    wid = r.json()["id"]
    assert r.json()["kind"] == "commits"

    assert len(client.get("/api/v1/watches").json()) == 1
    patched = client.patch(f"/api/v1/watches/{wid}", json={"enabled": False})
    assert patched.json()["enabled"] is False
    assert client.get("/api/v1/status").json()[0]["name"] == "w1"
    assert client.get("/api/v1/matches").json() == []
    assert "channels:" in client.get("/api/v1/config/export").text
    assert client.delete(f"/api/v1/watches/{wid}").status_code == 204


def test_issue_watch_rejects_diff_filter_over_http(client):
    r = client.post(
        "/api/v1/watches",
        json={
            "name": "bad",
            "repo": "o/r",
            "kind": "issues",
            "channels": [],
            "filters": {"diff": {"include": ["x"]}},
        },
    )
    assert r.status_code == 422  # validator rejects commit-only filter on issues


def test_404s(client):
    assert client.get("/api/v1/watches/999").status_code == 404
    assert client.delete("/api/v1/channels/missing").status_code == 404
