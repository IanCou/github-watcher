# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Documentation: in-repo Architecture Decision Records (`docs/decisions/`), `docs/ARCHITECTURE.md`, and
  this changelog.

## [0.1.0] - 2026-06-29

Initial release.

### Added

- **Watch commits or issues** on any public GitHub repo (`kind: commits | issues`), polling the public
  REST API - the only mechanism available for repos you don't own.
- **ETag conditional requests** so unchanged polls return `304` and cost nothing against the rate limit;
  rate-limit-aware, with cold-start priming to avoid notification floods.
- **Filter engine**: `message` / `author` / `files` (glob) / `diff` (regex) categories, AND-combined, with
  a `**` glob→regex translator. Issue watches filter on title+body and author.
- **Notifications via Apprise** (ntfy, Discord, Slack, Telegram, email, generic webhook, +100), with
  `${ENV}` secret placeholders resolved at send time and per-channel throttling. Jinja2-templated messages.
- **Four interfaces over one service layer**: REST API (OpenAPI at `/docs`), Typer CLI, an MCP server for
  agents, and an async background poller.
- **SQLite source of truth** with YAML import/export for seeding/snapshots, and an idempotent schema
  migration.
- **Web UI** (React + Vite + Tailwind): watches, channels, match history, and live status.
- **Observability**: Prometheus `/metrics` (polls, commits seen, matches, notifications, rate remaining,
  errors) and a `/healthz` endpoint.
- **Packaging & supply chain**: multi-stage Docker image; CI with ruff/prettier, pyright, pytest +
  coverage gate, CodeQL, gitleaks, Trivy, hadolint, pip-audit/npm audit, and Dependabot; tagged releases
  publish a cosign-signed image with an SBOM to GHCR.

[unreleased]: https://github.com/IanCou/github-watcher/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/IanCou/github-watcher/releases/tag/v0.1.0
