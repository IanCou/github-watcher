# 0002. ETag conditional requests for near-zero-cost polling

**Status:** Accepted

## Context

[0001](./0001-poll-not-webhooks.md) commits us to polling, which raises the obvious objection: polling
burns API requests. GitHub's REST API allows 60 req/hr unauthenticated and 5,000 req/hr with a token. A
watch polling every 60s is 60 req/hr per watch; several watches at tight intervals would exhaust the
unauthenticated budget and dent even the authenticated one. But most polls return **the same data** -
nothing changed since last time. Paying full price to re-download an unchanged commit list is the waste,
not the polling itself.

## Options considered

### Option A - Naive polling (GET every interval)

- **Pros:** Trivial.
- **Cons:** Every poll costs a request and full response transfer regardless of whether anything changed;
  forces long intervals to stay under the limit.

### Option B - ETag conditional requests (`If-None-Match`)

- **Pros:** GitHub returns `304 Not Modified` with an **empty body** when nothing changed, and **a `304`
  does not count against the rate limit**. Unchanged polls become effectively free, so intervals can be
  tight without budget worry. Standard HTTP caching, no extra infrastructure.
- **Cons:** Must persist the last ETag per watch and handle the 200/304/error branches explicitly.

### Option C - Long-poll / since-cursors

- **Pros:** Fewer requests in theory.
- **Cons:** The commits API has no long-poll; `since`/pagination cursors still cost a request each and
  don't get the free-304 benefit. More complexity, less saving.

## Decision

**Send `If-None-Match` with the stored ETag on every poll (Option B).** Store the ETag in per-watch poll
state; on `304`, do nothing and update bookkeeping; on `200`, diff against the seen-set. This is
implemented once in `core/github.py` and reused by both commit and issue polling.

## Consequences

### Positive

- Idle polls cost **0** against the rate limit, so tight intervals are safe; a token becomes optional
  rather than required.
- Rate-limit headers (`X-RateLimit-Remaining`) are read and exported as a metric for visibility.

### Negative / risks

- Slightly more client code (ETag persistence + status branching). Cheap and well-contained. Only the
  per-commit **diff** fetches (when file/diff filters are configured) still cost requests - mitigated by
  making diff inspection opt-in per watch ([0006](./0006-commits-and-issues-structured-filtering.md)).
