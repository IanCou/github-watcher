import pytest
from pydantic import ValidationError

from github_watcher.core.filters import evaluate
from github_watcher.core.github import commit_data_from_issue
from github_watcher.core.render import build_issue_context
from github_watcher.core.schemas import (
    FilterSet,
    IncludeExclude,
    TemplateSpec,
    WatchCreate,
)


def _issue(**kw):
    base = dict(
        number=42,
        title="New Internship: Google SWE Intern",
        body="company: Google\nlocation: NYC",
        user={"login": "octocat"},
        html_url="https://github.com/o/r/issues/42",
        labels=[{"name": "new_internship"}],
    )
    base.update(kw)
    return base


def test_issue_filter_input_maps_title_body_author():
    data = commit_data_from_issue(_issue())
    assert data.sha == "42"
    assert "Google SWE Intern" in data.message
    assert "company: Google" in data.message  # body included
    assert data.author_name == "octocat"
    assert data.changed_files == [] and data.diff_text == ""


def test_issue_message_filter_matches_title_or_body():
    fs = FilterSet(message=IncludeExclude(include=[r"(?i)google"]))
    assert evaluate(commit_data_from_issue(_issue()), fs).matched
    other = _issue(title="Meta intern", body="company: Meta")
    assert not evaluate(commit_data_from_issue(other), fs).matched


def test_issue_author_filter():
    fs = FilterSet(author=IncludeExclude(include=["octocat"]))
    assert evaluate(commit_data_from_issue(_issue()), fs).matched
    assert not evaluate(commit_data_from_issue(_issue(user={"login": "someone"})), fs).matched


def test_issue_context_exposes_item_and_issue():
    ctx = build_issue_context("o/r", _issue(), ["(?i)google"])
    assert ctx["item"]["ref"] == "#42"
    assert ctx["item"]["title"].startswith("New Internship")
    assert ctx["item"]["url"].endswith("/issues/42")
    assert ctx["issue"]["labels"] == ["new_internship"]


def test_default_template_renders_for_issues():
    from github_watcher.core.render import render

    ctx = build_issue_context("o/r", _issue(), [])
    title, body = render(TemplateSpec(), ctx)  # kind-neutral default uses item.*
    assert "o/r" in title and "#42" in body


def test_issue_watch_rejects_commit_only_filters():
    with pytest.raises(ValidationError):
        WatchCreate(
            name="x",
            repo="o/r",
            kind="issues",
            filters=FilterSet(diff=IncludeExclude(include=["x"])),
        )
    # message/author are allowed for issues
    WatchCreate(
        name="x",
        repo="o/r",
        kind="issues",
        filters=FilterSet(message=IncludeExclude(include=["x"])),
    )
