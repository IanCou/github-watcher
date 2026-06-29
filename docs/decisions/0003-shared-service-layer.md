# 0003. One shared service layer behind REST, CLI, MCP, and the poller

**Status:** Accepted

## Context

The tool must be drivable four ways: a REST API (for the web UI and scripts), a CLI (for humans and shell
automation), an MCP server (for AI agents), and a background poller (the always-on engine). All four do
the same fundamental things - create/update/delete watches and channels, evaluate a watch, persist and
query matches. The risk is the classic one: four entry points each growing their own copy of the rules
until they quietly diverge (the CLI validates differently than the API, the agent path skips a guard,
etc.).

## Options considered

### Option A - Logic inside each interface

- **Pros:** Direct; no indirection.
- **Cons:** Four copies of business logic that drift; bugs fixed in one path persist in the others; an
  agent (MCP) could behave differently than the UI for the same operation. Hard to test once, trust
  everywhere.

### Option B - One service layer; interfaces are thin adapters

- **Pros:** Single source of truth for behavior (`services.py`); each interface only translates its
  transport (HTTP status codes, CLI args, MCP tool schemas) to/from service calls. Test the logic once;
  every surface inherits it. New interfaces are cheap.
- **Cons:** A little ceremony (DTOs/validation shared via Pydantic schemas); the layer must stay
  transport-agnostic.

### Option C - Framework-coupled (logic in FastAPI routes, others call HTTP)

- **Pros:** No separate layer.
- **Cons:** CLI/poller/MCP would have to go through HTTP to reuse logic, coupling everything to a running
  server and the network. Awkward for an in-process background poller.

## Decision

**A single service layer (Option B).** `services.py` holds all business logic and owns the
poll -> filter -> render -> persist -> notify pipeline. `api/`, `cli.py`, `mcp_server.py`, and `poller.py`
are thin adapters: they validate/translate with shared `core/schemas.py` Pydantic models and call the
service functions. The poller runs the same `process_watch()` the REST "run now" endpoint does.

## Consequences

### Positive

- Human and agent surfaces cannot drift - they execute identical logic.
- Adding an interface (or splitting the poller into its own worker) is additive, not a rewrite.
- The logic is unit-tested directly, independent of HTTP.

### Negative / risks

- Discipline required to keep transport concerns out of the service layer. Enforced by code review and by
  the layer's signature shape (it takes/returns DTOs, not `Request`/`Response`).
