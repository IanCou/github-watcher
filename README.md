# github-watcher

[![ci](https://github.com/IanCou/github-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/IanCou/github-watcher/actions/workflows/ci.yml)
[![codeql](https://github.com/IanCou/github-watcher/actions/workflows/codeql.yml/badge.svg)](https://github.com/IanCou/github-watcher/actions/workflows/codeql.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![ghcr](https://img.shields.io/badge/ghcr.io-iancou%2Fgithub--watcher-blue?logo=docker)](https://github.com/IanCou/github-watcher/pkgs/container/github-watcher)

Poll **any** GitHub repo's **commits or issues**, **filter** them by message / author / changed files /
diff content, and get **notified** via ntfy, Discord, Slack, Telegram, email - anything
[Apprise](https://github.com/caronc/apprise) supports.

Built for repos you **don't own** (where webhooks and GitHub Actions aren't an option): it polls the
public REST API efficiently using ETag conditional requests, so idle polls cost nothing against your
rate limit.

Four ways to drive it, all sharing one backend:

- 🖥️ **Web UI** - manage watches/channels, browse match history, watch live status
- 🔌 **REST API** - OpenAPI-documented, at `/docs`
- ⌨️ **CLI** - `github-watcher watch add …`
- 🤖 **MCP server** - so agents (Claude etc.) can manage and query it directly

> Why it exists: notification tools assume you control the repo. For a third-party repo - say,
> watching [SimplifyJobs/Summer2026-Internships](https://github.com/SimplifyJobs/Summer2026-Internships)
> for a **Google** posting - polling + content filtering is the only path. This generalizes that.

---

## Quickstart (Docker)

```sh
cp .env.example .env        # fill in tokens you actually use
docker compose up -d
open http://localhost:8000  # UI + API docs at /docs
```

Seed it from a config file (optional):

```sh
docker compose exec github-watcher github-watcher config import /app/config.yml
```

## How filtering works

A watch has up to four filter categories. A commit notifies only if it passes **every** configured
category (AND). Within a category it must match an `include` (if any) and no `exclude`.

| Category  | Matches against          | Pattern type | Needs diff fetch? |
| --------- | ------------------------ | ------------ | ----------------- |
| `message` | commit message           | regex        | no                |
| `author`  | author name + email      | substring    | no                |
| `files`   | changed file paths       | glob (`**`)  | yes               |
| `diff`    | added diff lines only    | regex        | yes               |

Watches using only `message`/`author` cost **one** API call per change. `files`/`diff` filters fetch
each new commit's diff (opt-in cost). Matched keywords are stored on each match and available to your
notification template.

### Commits or issues

A watch has a `kind`: **`commits`** (default) or **`issues`**. Issue watches poll a repo's new issues
(pull requests excluded); for them, `message` matches the issue **title + body** and `author` matches the
opener - `files`/`diff` are commit-only. Templates expose a kind-neutral `{{ item.title/author/ref/url }}`
plus `{{ commit.* }}` / `{{ issue.* }}`.

```yaml
watches:
  - name: new-internship-issues
    repo: SimplifyJobs/Summer2026-Internships
    kind: issues
    channels: [ntfy-main]
    filters:
      message: { include: ['(?i)company name\s*\n+\s*(amazon|google|meta)'] }
```

### The "Google internship" example

> _Notify me only when a Google posting is added to the internship list._

```yaml
watches:
  - name: simplify-google-internships
    repo: SimplifyJobs/Summer2026-Internships
    branch: dev
    interval: 60
    channels: [ntfy-main, discord-jobs]
    filters:
      files: { include: ["**/listings.json"] } # ignore README/badge noise
      diff: { include: ['(?i)\bgoogle\b'] } # only when "google" is added (removals don't notify)
    template:
      title: "New match in {{ repo }}: {{ matched_keywords | join(', ') }}"
      body: "{{ commit.message_first_line }} - {{ commit.author }} · {{ commit.short_sha }}"
```

See [`config.example.yml`](config.example.yml) for more.

## Channels

Channels are [Apprise URLs](https://github.com/caronc/apprise/wiki). Use `${VAR}` placeholders so
secrets stay in the environment, not the database:

```
ntfy://${NTFY_TOKEN}@ntfy.example.net/commits
discord://${DISCORD_WEBHOOK_ID}/${DISCORD_WEBHOOK_TOKEN}
```

Test one from the UI, CLI (`github-watcher channel test ntfy-main`), or MCP.

## CLI

```sh
github-watcher channel add ntfy-main 'ntfy://${NTFY_TOKEN}@ntfy.example.net/commits'
github-watcher watch add -f watch.yml      # one watch as YAML/JSON
github-watcher watch list
github-watcher watch dry-run 1             # evaluate latest commits, send nothing
github-watcher watch run 1                 # poll once now
github-watcher matches --limit 20
github-watcher status
github-watcher config export -o config.yml
github-watcher serve                       # API + poller (what the container runs)
```

## MCP (agent access)

Run the stdio server:

```sh
python -m github_watcher.mcp_server
```

Register it with an MCP client, e.g. Claude Code:

```json
{
  "mcpServers": {
    "github-watcher": {
      "command": "python",
      "args": ["-m", "github_watcher.mcp_server"]
    }
  }
}
```

Tools: `list_watches`, `add_watch`, `update_watch`, `delete_watch`, `list_channels`, `add_channel`,
`test_channel`, `get_matches`, `run_now`, `dry_run`, `get_status`.

## Observability

- `GET /healthz` - liveness (used by the Docker healthcheck)
- `GET /metrics` - Prometheus: polls, commits seen, matches, notifications, GitHub rate remaining,
  errors - all labeled by watch.

## Development

```sh
# Backend
cd backend && python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check .
DISABLE_POLLER=1 uvicorn github_watcher.api.app:app --reload   # API only

# Frontend (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

## Architecture

A single Python service with a shared **service layer** behind every interface, so the UI, CLI, MCP,
and background poller never drift. **SQLite** is the source of truth; YAML import/export is for
portability. See [docs in the source](backend/github_watcher/) - `services.py` is the entry point for
all business logic, `core/filters.py` is the filter engine, `core/github.py` the ETag-aware client.

## Design & decisions

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - module map, the core poll→filter→notify pipeline, and how to extend it.
- [docs/decisions/](docs/decisions/index.md) - Architecture Decision Records: the **why** behind polling, ETag, the shared service layer, SQLite, Apprise, commits+issues, MCP, and the CI/supply-chain setup.
- [docs/STORY.md](docs/STORY.md) - the narrative of how the project came to be.
- [CHANGELOG.md](CHANGELOG.md) - release history.

## License

MIT - see [LICENSE](LICENSE).
