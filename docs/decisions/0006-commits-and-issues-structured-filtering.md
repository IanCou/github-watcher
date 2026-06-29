# 0006. Watch commits **and** issues; filter on structured fields

**Status:** Accepted

## Context

Two related questions surfaced once the commit watcher worked. First, **commits aren't the only signal** -
in the internship repo, new postings arrive as **issues** (a `new_internship` form) before they're merged
into the data file, so the earliest alert lives on the issues timeline, not commits. Second, and more
subtly: **what should a filter match against?** Testing on real data exposed a false-positive. A naive
"notify when the diff contains `google`" fired on a commit that added an SEI/Strayer posting whose
**title** was "Java / Google Cloud Platform" - not a Google posting at all. The word `google` appearing
somewhere in a changed line is not the same as "a Google posting was added."

## Options considered

### Option A - Commits only, substring/loose keyword filters

- **Pros:** Simplest.
- **Cons:** Misses the earlier issue signal entirely; loose keyword matching produces false positives
  (matched "Google Cloud Platform" in an unrelated company's title).

### Option B - Separate, bespoke code paths for commits vs. issues

- **Pros:** Each tailored.
- **Cons:** Duplicates the whole poll -> filter -> notify -> persist pipeline; two things to maintain and
  keep in sync.

### Option C - One pipeline with a `kind` discriminator; encourage structured-field regexes

- **Pros:** Commits and issues flow through the **same** path; a `kind` field selects the source and the
  field mapping (for issues, `message` matches title+body, `author` matches the opener; `files`/`diff` are
  commit-only and rejected by validation). Filtering on a **structured field** -
  `"company_name":\s*"Google"` instead of bare `\bgoogle\b` - keys off the repo's JSON schema and
  eliminates the false positive.
- **Cons:** The user has to know to target the structured field; the engine matches text, it doesn't parse
  JSON semantically.

## Decision

**One pipeline, a `kind` of `commits` or `issues` (Option C).** The same engine evaluates both; issue
watches reuse priming, ETag polling, history, and notifications unchanged, with pull requests skipped.
Filtering remains regex/glob over text, but the docs and examples steer toward **structured-field**
patterns (matching the `company_name` JSON field) rather than loose substrings, because that is what
encodes intent. This was validated against real commits: the structured pattern matched true Amazon/
Microsoft/TikTok additions and correctly ignored the "Google Cloud Platform" title.

## Consequences

### Positive

- Earlier signal (issues) and fewer false positives, with no duplicated code - the `kind` discriminator
  extends the core abstraction instead of forking it.
- Exact-match patterns also avoid name-collision traps found in real data (e.g. `Meta` vs `Metalenz`,
  `Snap` vs `Snap Finance`).

### Negative / risks

- Filtering is textual, not semantic JSON parsing, so a malformed or reformatted source could need pattern
  tweaks. Acceptable; patterns are per-watch and easy to adjust. Revisit if a repo needs true structured
  querying.
