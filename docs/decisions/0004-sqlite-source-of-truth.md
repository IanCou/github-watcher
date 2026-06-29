# 0004. SQLite as source of truth, with YAML import/export

**Status:** Accepted

## Context

The tool needs to persist watches, channels, per-watch poll state (ETag, seen-set, last status), and a
match history. It must support live CRUD from a web UI and agents (so a static config file alone won't
do), survive restarts, and be trivial to run on a single node / in one container. It should also be
portable and reproducible (GitOps-friendly) so a deployment can be seeded declaratively.

## Options considered

### Option A - Config file only (YAML on disk)

- **Pros:** Declarative, version-controllable, dead simple.
- **Cons:** No place for runtime state (seen-set, ETags, match history); live edits from a UI/agent mean
  rewriting the file under a running process. Doesn't fit interactive management.

### Option B - SQLite as source of truth, plus YAML import/export

- **Pros:** Real CRUD with transactions; one file, zero external services; perfect for single-node/one
  container; restart-safe state. YAML import/export gives the GitOps/portability benefit of Option A
  without making the file authoritative.
- **Cons:** Schema evolution needs handling (addressed with a small idempotent migration); typed-ORM
  friction with strict type checkers.

### Option C - External database (Postgres/etc.)

- **Pros:** Scales horizontally; concurrent writers.
- **Cons:** Massive overkill for a single-node poller; an extra service to run, back up, and secure. No
  benefit at this scale.

## Decision

**SQLite via SQLModel is the source of truth (Option B); YAML is an import/export format, not
authoritative.** Watches/channels are CRUD-managed at runtime through any interface; `config.yml` can seed
or snapshot a deployment (`config import` / `config export`). New columns are added by a tiny idempotent
migration (`PRAGMA table_info` + `ALTER TABLE`) so existing volumes upgrade without data loss.

## Consequences

### Positive

- One-file state, no external dependencies; clean fit for the single-container deploy.
- Declarative seeding/snapshotting via YAML keeps the GitOps story without the limits of a file-only model.

### Negative / risks

- Single-writer/single-node by design - horizontal scaling would require a shared DB and work
  partitioning. Accepted; this is a single-operator tool. Revisit if multi-node is ever needed.
