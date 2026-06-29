# Architecture

How github-watcher is put together and why each piece sits where it does. For the _decisions_ behind this
shape, see the [ADRs](./decisions/index.md); this document is the map.

## The shape

A single Python backend with a **shared service layer** that every interface and the background poller call
through, plus a React SPA served by the same process. SQLite is the source of truth.

```
                    ┌──────────────── shared core ────────────────┐
   React SPA ──HTTP─▶  FastAPI REST API  ┐                          │
   Typer CLI ───────▶  service layer  ───┼─▶ repository (SQLModel/SQLite)
   MCP server ──────▶  (services.py)  ───┘     filter engine
                       background poller ──────▶ GitHub client (httpx, ETag)
                                          ──────▶ notify (Apprise) → ntfy/Discord/…
```

Why this shape: the four surfaces are thin adapters so logic never forks
([ADR 0003](./decisions/0003-shared-service-layer.md)); polling is the only option for third-party repos
([0001](./decisions/0001-poll-not-webhooks.md)) and ETag keeps it cheap
([0002](./decisions/0002-etag-conditional-requests.md)).

## Module map (`backend/github_watcher/`)

| Module                               | Responsibility                                                                                                                                          |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services.py`                        | **The entry point for all business logic.** Watch/channel CRUD, status, and the poll→filter→notify pipeline. Every interface calls here.                |
| `core/filters.py`                    | The filter engine: `message`/`author`/`files`/`diff` categories, AND-combined; includes the `**` glob→regex translator. Pure, heavily unit-tested.      |
| `core/github.py`                     | Async GitHub client. ETag-conditional `list_commits`/`list_issues`, per-commit diff fetch, rate-limit parsing. Maps raw API objects into filter inputs. |
| `core/notify.py`                     | Apprise wrapper: named channels, `${ENV}` resolution at send time, per-channel throttling.                                                              |
| `core/render.py`                     | Jinja2 rendering of notification title/body; exposes a kind-neutral `item.*` plus `commit.*` / `issue.*`.                                               |
| `core/config_io.py`                  | YAML ⇄ DB import/export (seeding/snapshots).                                                                                                            |
| `core/models.py` / `core/schemas.py` | SQLModel tables (Watch, Channel, Match, PollState) / Pydantic DTOs + validation.                                                                        |
| `repository.py`                      | Data access over SQLModel sessions. No business logic.                                                                                                  |
| `poller.py`                          | Async supervisor: one task per enabled watch on its own interval, reconciled every 15s.                                                                 |
| `api/`                               | FastAPI app + routers (`watches`, `channels`, `matches`, `config`), `/metrics`, `/healthz`, serves the built SPA, starts the poller in its lifespan.    |
| `cli.py`                             | Typer CLI over the service layer.                                                                                                                       |
| `mcp_server.py`                      | MCP server exposing the service layer as agent tools ([ADR 0007](./decisions/0007-mcp-agent-access.md)).                                                |
| `db.py`                              | Engine, session, table creation + idempotent column migration.                                                                                          |
| `metrics.py`                         | Prometheus counters/gauges (polls, commits seen, matches, notifications, rate remaining, errors).                                                       |
| `settings.py` / `clock.py`           | Env-sourced settings / local-timezone timestamps.                                                                                                       |

## The core pipeline

`services.process_watch(watch_id)` is the heart; the REST "run now", the CLI `run`, and the poller all call
it.

1. **Load** the watch, its filter set, template, channel URLs, and poll state (ETag + seen-set).
2. **List** via the GitHub client with `If-None-Match`:
   - `304` → nothing changed; update bookkeeping, return. (Free against the rate limit.)
   - non-200 → record the error on the watch's status, return.
   - `200` → continue.
3. **Diff** the returned items against the seen-set → the new ones (oldest-first; PRs skipped for issues).
4. **Cold-start priming**: on the very first successful poll, record the new items into the seen-set
   **without notifying**, so a new watch doesn't blast the channel with history. Subsequent polls notify.
5. For each new item: build the **filter input** (for commits, fetch the diff only if file/diff filters
   exist - opt-in cost), **evaluate** the filter set, and on a match: **render** the template, **persist**
   a `Match`, and **notify** the channels (recording success/error).
6. **Persist** updated poll state (new ETag, capped seen-set, status, rate remaining).

### Commits vs. issues

The same pipeline serves both via a `kind` discriminator
([ADR 0006](./decisions/0006-commits-and-issues-structured-filtering.md)). For `kind=issues`, the GitHub
client lists issues (excluding PRs), the filter input maps title+body→`message` and the opener→`author`,
and `files`/`diff` filters are rejected at validation. Templates use the kind-neutral `item.*` so one
template works for either.

## How to extend (the reuse seams)

- **A new filter category** → add it to `FilterSet` in `core/schemas.py` and the evaluator in
  `core/filters.py`; the pipeline picks it up unchanged.
- **A new notification target** → it's almost certainly already an Apprise URL; just add a channel. No code
  ([ADR 0005](./decisions/0005-apprise-notifications.md)).
- **A new interface** → write a thin adapter over `services.py` (as `cli.py` / `mcp_server.py` do); don't
  put logic in the adapter ([ADR 0003](./decisions/0003-shared-service-layer.md)).
- **A new watch source** (beyond commits/issues) → add a `kind`, a `list_*` on the GitHub client, and a
  filter-input mapping; reuse the rest of `process_watch`.

## Deployment shape

One container (multi-stage build: Vite SPA compiled, then served by the FastAPI process), SQLite on a
mounted volume, the poller running in the API lifespan. `/healthz` for the container healthcheck and
`/metrics` for Prometheus. See the [README](../README.md) for run instructions.
