# 0001. Poll the REST API instead of webhooks/Actions

**Status:** Accepted

## Context

The project grew out of a concrete need: be notified when a specific change lands in a GitHub repo that
**someone else owns** (the original case was watching `SimplifyJobs/Summer2026-Internships` for a new
posting). The defining constraint is ownership: you only get push-based mechanisms - repository webhooks,
GitHub Actions `on: push`, the Events API for an org - if you have admin/write on the repo. For a
third-party repo you have none of that. The only thing a non-owner can rely on is the **public read API**.
So the core question isn't "webhooks or polling?" in the abstract; it's "what can a non-owner actually
use?"

## Options considered

### Option A - Repository webhooks / GitHub Actions

- **Pros:** Push-based, instant, zero wasted requests.
- **Cons:** Require admin on the target repo. **Impossible** for the third-party repos this tool exists to
  watch. Non-starter.

### Option B - Poll the public REST API

- **Pros:** Works on any public repo with no permissions; optional token only raises rate limits. Simple,
  self-contained, no inbound endpoint to host.
- **Cons:** Not instant (bounded by poll interval); naively wasteful against the rate limit; you must
  track "seen" state yourself.

### Option C - Poll the Atom/RSS commit feed (`/commits.atom`)

- **Pros:** No token, cheap.
- **Cons:** Title/summary only - no diff, no changed-file list, no structured fields, so the content
  filtering that makes this tool useful isn't possible. Issues aren't covered.

## Decision

**Poll the public REST API (Option B).** It is the only mechanism available to a non-owner, and unlike the
Atom feed it exposes commit diffs, changed files, and issue bodies - the data the filter engine needs. The
rate-limit cost objection is addressed separately in [0002](./0002-etag-conditional-requests.md).

## Consequences

### Positive

- Works on any public repo immediately; no setup on the watched repo; no inbound webhook endpoint to
  secure or host.

### Negative / risks

- Latency is bounded by the poll interval, not instant. Acceptable for this use case.
- The app owns "seen" state and rate-limit budgeting (see [0002](./0002-etag-conditional-requests.md) and
  [0004](./0004-sqlite-source-of-truth.md)). Revisit only if GitHub ever exposes a pull-style change feed
  for non-owners.
