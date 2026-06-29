from github_watcher.core.filters import CommitData, evaluate
from github_watcher.core.schemas import FilterSet, IncludeExclude


def _commit(**kw) -> CommitData:
    base = dict(sha="abc1234", message="", author_name="", author_email="")
    base.update(kw)
    return CommitData(**base)


def test_no_filters_matches_everything():
    res = evaluate(_commit(message="anything"), FilterSet())
    assert res.matched and res.keywords == []


def test_message_include_regex():
    fs = FilterSet(message=IncludeExclude(include=[r"(?i)google"]))
    assert evaluate(_commit(message="Add Google role"), fs).matched
    assert not evaluate(_commit(message="Add Meta role"), fs).matched


def test_message_exclude_wins():
    fs = FilterSet(message=IncludeExclude(include=[r"role"], exclude=[r"(?i)bot"]))
    assert not evaluate(_commit(message="bot: add role"), fs).matched


def test_author_substring_case_insensitive():
    fs = FilterSet(author=IncludeExclude(include=["dependabot"]))
    assert evaluate(_commit(author_name="DependaBot"), fs).matched
    assert not evaluate(_commit(author_name="alice"), fs).matched


def test_files_glob_double_star_and_toplevel():
    fs = FilterSet(files=IncludeExclude(include=["**/listings.json"]))
    assert evaluate(_commit(changed_files=[".github/scripts/listings.json"]), fs).matched
    assert evaluate(_commit(changed_files=["listings.json"]), fs).matched
    assert not evaluate(_commit(changed_files=["README.md"]), fs).matched


def test_files_single_star_does_not_cross_slash():
    fs = FilterSet(files=IncludeExclude(include=["src/*.py"]))
    assert evaluate(_commit(changed_files=["src/app.py"]), fs).matched
    assert not evaluate(_commit(changed_files=["src/sub/app.py"]), fs).matched


def test_diff_regex_on_added_lines():
    diff = "@@ -1 +1 @@\n+  added google here\n-  removed line"
    fs = FilterSet(diff=IncludeExclude(include=[r"(?i)\bgoogle\b"]))
    res = evaluate(_commit(diff_text=diff), fs)
    assert res.matched and res.keywords == [r"(?i)\bgoogle\b"]


def test_diff_ignores_hunk_headers():
    diff = "+++ b/listings.json\n--- a/listings.json\n+   nothing relevant"
    fs = FilterSet(diff=IncludeExclude(include=[r"listings"]))
    # 'listings' only appears in the +++/--- headers, which are excluded.
    assert not evaluate(_commit(diff_text=diff), fs).matched


def test_categories_are_anded():
    fs = FilterSet(
        files=IncludeExclude(include=["**/listings.json"]),
        diff=IncludeExclude(include=[r"(?i)google"]),
    )
    google_in_listings = _commit(
        changed_files=["listings.json"], diff_text="+ Google SWE Intern"
    )
    google_elsewhere = _commit(
        changed_files=["README.md"], diff_text="+ Google SWE Intern"
    )
    assert evaluate(google_in_listings, fs).matched
    assert not evaluate(google_elsewhere, fs).matched


def test_needs_diff_flag():
    assert FilterSet(diff=IncludeExclude(include=["x"])).needs_diff()
    assert FilterSet(files=IncludeExclude(include=["x"])).needs_diff()
    assert not FilterSet(message=IncludeExclude(include=["x"])).needs_diff()
