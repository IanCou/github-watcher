# commit-watcher

Poll **any** GitHub repo's commits, **filter** them by message / author / changed files / diff
content, and get **notified** via ntfy, Discord, Slack, Telegram, email — anything
[Apprise](https://github.com/caronc/apprise) supports.

Built for repos you **don't own** (where webhooks and GitHub Actions aren't an option): it polls the
public REST API efficiently using ETag conditional requests, so idle polls cost nothing against your
rate limit.

Four ways to drive it, all sharing one backend:

- 🖥️ **Web UI** — manage watches/channels, browse match history, watch live status
- 🔌 **REST API** — OpenAPI-documented, at `/docs`
- ⌨️ **CLI** — `commit-watcher watch add …`
- 🤖 **MCP server** — so agents (Claude etc.) can manage and query it directly

> Why it exists: notification tools assume you control the repo. For a third-party repo — say,
> watching [SimplifyJobs/Summer2026-Internships](https://github.com/SimplifyJobs/Summer2026-Internships)
> for a **Google** posting — polling + content filtering is the only path. This generalizes that.

---

## Quickstart (Docker)

```sh
cp .env.example .env        # fill in tokens you actually use
docker compose up -d
open http://localhost:8000  # UI + API docs at /docs
```

Seed it from a config file (optional):

```sh
docker compose exec commit-watcher commit-watcher config import /app/config.yml
```

## How filtering works

A watch has up to four filter categories. A commit notifies only if it passes **every** configured
category (AND). Within a category it must match an `include` (if any) and no `exclude`.

| Category  | Matches against            | Pattern type | Needs diff fetch? |
|-----------|----------------------------|--------------|-------------------|
| `message` | commit message             | regex        | no                |
| `author`  | author name + email        | substring    | no                |
| `files`   | changed file paths         | glob (`**`)  | yes               |
| `diff`    | added/removed diff lines   | regex        | yes               |

Watches using only `message`/`author` cost **one** API call per change. `files`/`diff` filters fetch
each new commit's diff (opt-in cost). Matched keywords are stored on each match and available to your
notification template.

### The "Google internship" example

> *Notify me only when a Google posting is added to the internship list.*

```yaml
watches:
  - name: simplify-google-internships
    repo: SimplifyJobs/Summer2026-Internships
    branch: dev
    interval: 60
    channels: [ntfy-main, discord-jobs]
    filters:
      files: { include: ["**/listings.json"] }   # ignore README/badge noise
      diff:  { include: ['(?i)\bgoogle\b'] }      # only when "google" is added/removed
    template:
      title: "New match in {{ repo }}: {{ matched_keywords | join(', ') }}"
      body:  "{{ commit.message_first_line }} — {{ commit.author }} · {{ commit.short_sha }}"
```

See [`config.example.yml`](config.example.yml) for more.

## Channels

Channels are [Apprise URLs](https://github.com/caronc/apprise/wiki). Use `${VAR}` placeholders so
secrets stay in the environment, not the database:

```
ntfy://${NTFY_TOKEN}@ntfy.example.net/commits
discord://${DISCORD_WEBHOOK_ID}/${DISCORD_WEBHOOK_TOKEN}
```

Test one from the UI, CLI (`commit-watcher channel test ntfy-main`), or MCP.

## CLI

```sh
commit-watcher channel add ntfy-main 'ntfy://${NTFY_TOKEN}@ntfy.example.net/commits'
commit-watcher watch add -f watch.yml      # one watch as YAML/JSON
commit-watcher watch list
commit-watcher watch dry-run 1             # evaluate latest commits, send nothing
commit-watcher watch run 1                 # poll once now
commit-watcher matches --limit 20
commit-watcher status
commit-watcher config export -o config.yml
commit-watcher serve                       # API + poller (what the container runs)
```

## MCP (agent access)

Run the stdio server:

```sh
python -m commit_watcher.mcp_server
```

Register it with an MCP client, e.g. Claude Code:

```json
{ "mcpServers": { "commit-watcher": { "command": "python", "args": ["-m", "commit_watcher.mcp_server"] } } }
```

Tools: `list_watches`, `add_watch`, `update_watch`, `delete_watch`, `list_channels`, `add_channel`,
`test_channel`, `get_matches`, `run_now`, `dry_run`, `get_status`.

## Observability

- `GET /healthz` — liveness (used by the Docker healthcheck)
- `GET /metrics` — Prometheus: polls, commits seen, matches, notifications, GitHub rate remaining,
  errors — all labeled by watch.

## Development

```sh
# Backend
cd backend && python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check .
DISABLE_POLLER=1 uvicorn commit_watcher.api.app:app --reload   # API only

# Frontend (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

## Architecture

A single Python service with a shared **service layer** behind every interface, so the UI, CLI, MCP,
and background poller never drift. **SQLite** is the source of truth; YAML import/export is for
portability. See [docs in the source](backend/commit_watcher/) — `services.py` is the entry point for
all business logic, `core/filters.py` is the filter engine, `core/github.py` the ETag-aware client.

## License

MIT — see [LICENSE](LICENSE).
