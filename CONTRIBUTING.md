# Contributing

Thanks for your interest! This project is small and welcomes focused PRs.

## Layout

- `backend/commit_watcher/` — Python service. `services.py` is the single business-logic layer used by
  the REST API, CLI, MCP server, and poller. Add behavior there, not in the interfaces.
- `backend/commit_watcher/core/` — pure-ish building blocks: `filters.py` (filter engine),
  `github.py` (API client), `notify.py` (Apprise), `render.py`, `config_io.py`.
- `frontend/` — React + Vite + Tailwind SPA.

## Before opening a PR

```sh
# backend
cd backend && pip install -e ".[dev]" && ruff check . && pytest -q
# frontend
cd frontend && npm install && npm run lint && npm run build
```

## Guidelines

- New filter behavior must come with cases in `tests/test_filters.py` (the truth table is the spec).
- Keep interfaces thin: REST/CLI/MCP should call `services.*` and translate errors, nothing more.
- Notification targets are Apprise URLs — don't add per-provider code; if Apprise supports it, it works.
- Match the surrounding style; `ruff` is the formatter/linter of record.
