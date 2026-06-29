# The story behind github-watcher

A walk through how this project came to be and the engineering decisions along the way. If you want the
structured rationale, each decision below links to its [ADR](./decisions/index.md); this is the narrative
that ties them together.

## The problem

It started with a small, real annoyance: I wanted to be notified the moment a specific kind of change
landed in a GitHub repo I didn't own - concretely, a new posting in a popular internship-tracking repo.
The obvious answer is "use a webhook" or "add a GitHub Action." Neither works here: those need admin on the
repo, and this is someone else's repo. That single constraint - **you don't own the thing you're watching**

- shaped the entire design.

## Research: the only door that's open

If you can't push, you have to pull. The only mechanism a non-owner has is the **public read API**. The
RSS/Atom commit feed is tempting (no token, cheap) but it only carries titles - no diffs, no changed files,
no structured data - so the content filtering that makes the tool _useful_ is impossible. So: poll the REST
API ([ADR 0001](./decisions/0001-poll-not-webhooks.md)).

The immediate objection to polling is cost - you burn requests checking for changes that usually haven't
happened. The fix is an old HTTP idea: **conditional requests**. Send the last `ETag` with `If-None-Match`;
when nothing changed, GitHub returns `304 Not Modified` with an empty body - and a `304` doesn't count
against the rate limit. Idle polls become free, so I could poll tightly without worrying about the budget
([ADR 0002](./decisions/0002-etag-conditional-requests.md)).

## Design: one brain, many mouths

I wanted to drive this four ways - a web UI, a CLI, an AI agent, and an always-on poller. The trap is
letting each grow its own copy of the rules until they quietly disagree. So everything routes through a
single **service layer**; the interfaces are thin adapters that just translate their transport
([ADR 0003](./decisions/0003-shared-service-layer.md)). That decision paid off twice: adding an **MCP
server** so an AI agent can manage watches was almost free - each tool is a one-line wrapper over the same
logic the UI uses ([ADR 0007](./decisions/0007-mcp-agent-access.md)).

State lives in **SQLite** (one file, no external services, perfect for a single container), with YAML
import/export so a deployment can be seeded declaratively without making a config file the source of truth
([ADR 0004](./decisions/0004-sqlite-source-of-truth.md)). Notifications go through **Apprise** - one
dependency, 100+ targets - with secrets kept in `${ENV}` placeholders resolved at send time so they never
touch the database ([ADR 0005](./decisions/0005-apprise-notifications.md)).

## The lesson: matching intent, not text

The most instructive moment came from testing on real data. A filter for `google` in the diff fired on a
commit that added a posting whose **title** was "Java / Google Cloud Platform" - at a completely different
company. The word was there; the _meaning_ wasn't. The fix was to match the **structured field** the data
actually uses (`"company_name": "Google"`) rather than a loose substring. The same realization pushed me to
also watch **issues**, not just commits - in this repo, new postings show up as issues first, so that's the
earliest signal. Both came together under a single `kind` discriminator so commits and issues share one
pipeline ([ADR 0006](./decisions/0006-commits-and-issues-structured-filtering.md)).

## Shipping it like it matters

Going public means other people - and my own homelab - pull and run the image, so CI protects the **supply
chain**, not just correctness: CodeQL, gitleaks secret scanning, Trivy and hadolint on the container,
dependency audits, Dependabot, and tagged releases that publish a **cosign-signed image with an SBOM**. The
test coverage gate is deliberately an honest **floor** rather than an aspirational 80% - the hardest code to
unit-test is the live network path, and a number that forces bad tests is worse than a modest true one
([ADR 0008](./decisions/0008-supply-chain-ci.md)).

## Where it runs

The same image deploys to a self-hosted homelab - a Proxmox LXC provisioned with Terraform, configured with
Ansible, reachable over Tailscale, with its Prometheus metrics scraped into Grafana. The tool that started
as a one-off script to watch one repo is now a general, signed, observable service that watches any repo -
and replaced the script that inspired it.

---

_For the full design rationale, see the [Architecture Decision Records](./decisions/index.md) and
[ARCHITECTURE.md](./ARCHITECTURE.md)._
