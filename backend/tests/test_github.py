import httpx
import respx

from github_watcher.core.github import GitHubClient, commit_data_from_detail

BASE = "https://api.github.com"


@respx.mock
async def test_list_commits_304_is_zero_cost():
    respx.get(f"{BASE}/repos/o/r/commits").mock(
        return_value=httpx.Response(
            304, headers={"ETag": '"abc"', "X-RateLimit-Remaining": "4999"}
        )
    )
    gh = GitHubClient(token=None)
    resp = await gh.list_commits("o/r", etag='"abc"')
    assert resp.status == 304
    assert resp.items == []
    assert resp.etag == '"abc"'
    assert resp.rate_remaining == 4999


@respx.mock
async def test_list_commits_200_parses_and_returns_etag():
    respx.get(f"{BASE}/repos/o/r/commits").mock(
        return_value=httpx.Response(
            200,
            headers={"ETag": '"def"', "X-RateLimit-Remaining": "10"},
            json=[{"sha": "1", "commit": {"message": "m", "author": {"name": "a"}}}],
        )
    )
    gh = GitHubClient(token=None)
    resp = await gh.list_commits("o/r")
    assert resp.status == 200
    assert resp.etag == '"def"'
    assert resp.items[0]["sha"] == "1"


def test_commit_data_from_detail_extracts_files_and_diff():
    detail = {
        "sha": "x",
        "commit": {"message": "msg", "author": {"name": "n", "email": "e"}},
        "files": [
            {"filename": "a.json", "patch": "+added"},
            {"filename": "b.md", "patch": "-removed"},
        ],
    }
    data = commit_data_from_detail(detail)
    assert data.changed_files == ["a.json", "b.md"]
    assert "+added" in data.diff_text and "-removed" in data.diff_text
