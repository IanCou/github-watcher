# Architecture Decision Records

This directory captures the **why** behind github-watcher's design - the trade-offs that were weighed,
the options rejected, and the consequences accepted. The code says _what_ it does; these records say
_why it's built that way_.

## What an ADR is

A short, immutable document describing a single architecturally-significant decision: its context, the
options considered with pros and cons, the option chosen, and the consequences. Once accepted, an ADR is
not rewritten - if a later decision overrides it, a new ADR is added and the old one is marked
**Superseded**.

## How to add one

1. Copy `_template.md` to `NNNN-kebab-title.md`, incrementing `NNNN` (zero-padded). Files prefixed with
   `_` are templates, not records.
2. Fill every section. Keep options concrete - list real alternatives with honest pros **and** cons.
3. Set **Status** to `Proposed` until in effect, then `Accepted`. If it replaces an older ADR, mark the
   old one `Superseded by NNNN` and link both ways.
4. Add a row to the table below.

## Records

| #                                                         | Decision                                                         | Status   |
| --------------------------------------------------------- | ---------------------------------------------------------------- | -------- |
| [0001](./0001-poll-not-webhooks.md)                       | Poll the REST API instead of webhooks/Actions                    | Accepted |
| [0002](./0002-etag-conditional-requests.md)               | ETag conditional requests for near-zero-cost polling             | Accepted |
| [0003](./0003-shared-service-layer.md)                    | One shared service layer behind REST, CLI, MCP, and the poller   | Accepted |
| [0004](./0004-sqlite-source-of-truth.md)                  | SQLite as source of truth, with YAML import/export               | Accepted |
| [0005](./0005-apprise-notifications.md)                   | Apprise for notifications; secrets stay in `${ENV}`              | Accepted |
| [0006](./0006-commits-and-issues-structured-filtering.md) | Watch commits **and** issues; filter on structured fields        | Accepted |
| [0007](./0007-mcp-agent-access.md)                        | An MCP server so agents can drive the tool                       | Accepted |
| [0008](./0008-supply-chain-ci.md)                         | Supply-chain-focused CI: signing, SBOM, scanning, coverage floor | Accepted |
