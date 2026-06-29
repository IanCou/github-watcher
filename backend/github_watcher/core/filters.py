"""Filter engine: decide whether a commit matches a watch's FilterSet.

Categories (all optional, combined with AND):
  - message: regex against the commit message
  - author:  case-insensitive substring against author name/email
  - files:   glob against changed file paths
  - diff:    regex against added/removed diff lines

Within a category: a candidate must match at least one ``include`` pattern (when
any are configured) and must match no ``exclude`` pattern. The set of
human-meaningful matched tokens (e.g. "google") is returned for templating and
stored on the Match record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schemas import FilterSet, IncludeExclude


@dataclass
class CommitData:
    """Everything the filter engine may inspect for one commit."""

    sha: str
    message: str = ""
    author_name: str = ""
    author_email: str = ""
    changed_files: list[str] = field(default_factory=list)
    # Added/removed lines from the unified diff (patch bodies concatenated).
    diff_text: str = ""


@dataclass
class FilterResult:
    matched: bool
    keywords: list[str] = field(default_factory=list)


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    r"""Translate a path glob to a regex.

    ``**`` matches across directory separators; ``*``/``?`` do not. A leading
    ``**/`` also matches zero leading directories, so ``**/listings.json`` hits
    both ``a/b/listings.json`` and a top-level ``listings.json``.
    """
    if glob.startswith("**/"):
        prefix, rest = "(?:.*/)?", glob[3:]
    else:
        prefix, rest = "", glob
    out = [prefix]
    i = 0
    while i < len(rest):
        c = rest[i]
        if c == "*":
            if i + 1 < len(rest) and rest[i + 1] == "*":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _eval(value: str, spec: IncludeExclude, *, regex: bool) -> tuple[bool, list[str]]:
    """Evaluate one string value against an include/exclude spec.

    Returns (passed, matched_include_patterns).
    """

    def hit(pattern: str) -> bool:
        if regex:
            return re.search(pattern, value) is not None
        return pattern.lower() in value.lower()

    for pat in spec.exclude:
        if hit(pat):
            return False, []
    if not spec.include:
        return True, []
    matched = [pat for pat in spec.include if hit(pat)]
    return (bool(matched), matched)


def _eval_any(values: list[str], spec: IncludeExclude, *, regex: bool, glob: bool = False):
    """Evaluate a list of values (files/diff lines). Passes if the include set is
    satisfied by *any* value and no value triggers an exclude."""
    patterns_include = [(_glob_to_regex(p) if glob else p) for p in spec.include]
    patterns_exclude = [(_glob_to_regex(p) if glob else p) for p in spec.exclude]

    def hit(pattern, value: str) -> bool:
        if glob:
            return pattern.match(value) is not None
        if regex:
            return re.search(pattern, value) is not None
        return pattern.lower() in value.lower()

    for pat in patterns_exclude:
        for v in values:
            if hit(pat, v):
                return False, []
    if not spec.include:
        return True, []
    matched: list[str] = []
    for raw, pat in zip(spec.include, patterns_include, strict=True):
        if any(hit(pat, v) for v in values):
            matched.append(raw)
    return (bool(matched), matched)


def evaluate(commit: CommitData, filters: FilterSet) -> FilterResult:
    """Run every configured category; AND the results, union the keywords."""
    keywords: list[str] = []

    if filters.message:
        ok, kw = _eval(commit.message, filters.message, regex=True)
        if not ok:
            return FilterResult(False)
        keywords += kw

    if filters.author:
        author = f"{commit.author_name} {commit.author_email}".strip()
        ok, _ = _eval(author, filters.author, regex=False)
        if not ok:
            return FilterResult(False)

    if filters.files:
        ok, kw = _eval_any(commit.changed_files, filters.files, regex=False, glob=True)
        if not ok:
            return FilterResult(False)
        keywords += kw

    if filters.diff:
        diff_lines = [
            ln[1:]
            for ln in commit.diff_text.splitlines()
            if ln[:1] in ("+", "-") and not ln.startswith(("+++", "---"))
        ]
        ok, kw = _eval_any(diff_lines, filters.diff, regex=True)
        if not ok:
            return FilterResult(False)
        keywords += kw

    # Dedupe, preserve order.
    seen: dict[str, None] = {}
    for k in keywords:
        seen.setdefault(k, None)
    return FilterResult(True, list(seen))
