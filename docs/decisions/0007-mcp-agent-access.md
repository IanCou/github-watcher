# 0007. An MCP server so agents can drive the tool

**Status:** Accepted

## Context

A design goal was for the tool to be **agent-accessible** - an AI assistant (Claude and other MCP clients)
should be able to list and create watches, query matches, and trigger a dry run, not just a human at a
terminal or browser. The question was how to expose capabilities to an agent without building yet another
bespoke integration or duplicating logic.

## Options considered

### Option A - REST API only; let agents call HTTP

- **Pros:** Already exists; anything can call it.
- **Cons:** The agent must be taught the endpoints, auth, and payloads out-of-band; no standard
  description of available tools; more glue per agent.

### Option B - A Model Context Protocol (MCP) server

- **Pros:** MCP is the emerging standard for exposing tools to LLM agents; tools are self-describing
  (name, schema, doc) so a client discovers them automatically. Reuses the existing service layer
  ([0003](./0003-shared-service-layer.md)) - each tool is a thin wrapper over a `services.py` function, so
  the agent path runs identical logic to the UI/CLI. Ships in the same package (`python -m
github_watcher.mcp_server`).
- **Cons:** An additional interface to maintain; MCP is young and evolving.

### Option C - A chatbot/LLM baked into the app

- **Pros:** Self-contained "ask it" UX.
- **Cons:** Couples the tool to a model/provider, adds cost and prompt-maintenance, and still doesn't give
  external agents programmatic access. Wrong layer.

## Decision

**Expose an MCP server (Option B).** It surfaces the service layer as discoverable tools - `list_watches`,
`add_watch`, `update_watch`, `delete_watch`, `list_channels`, `add_channel`, `test_channel`,
`get_matches`, `run_now`, `dry_run`, `get_status` - reusing the same logic and validation as every other
surface. This makes the four-interface design ([0003](./0003-shared-service-layer.md)) pay off directly:
the agent surface was nearly free.

## Consequences

### Positive

- Agents manage and query the tool natively, with self-describing tools and no per-agent glue.
- Concretely demonstrates the shared-service-layer dividend: a whole new interface as thin wrappers.

### Negative / risks

- MCP is evolving; the SDK/tool surface may shift. Contained to one module (`mcp_server.py`); the service
  layer it wraps is stable.
