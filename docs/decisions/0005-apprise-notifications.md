# 0005. Apprise for notifications; secrets stay in `${ENV}`

**Status:** Accepted

## Context

A match has to be delivered somewhere. The original use case wanted ntfy (phone) and Discord, but "notify
me" is open-ended - Slack, Telegram, email, a generic webhook are all reasonable future targets. Two
concerns: (1) not reinventing a per-provider integration for each channel, and (2) handling the secret
each channel needs (tokens, webhook IDs) without persisting plaintext credentials in the database.

## Options considered

### Option A - Hand-rolled per-provider clients

- **Pros:** Full control over each payload.
- **Cons:** N integrations to write, test, and maintain; every new channel is code. Reinvents a solved
  problem.

### Option B - Apprise as the notification layer

- **Pros:** One dependency yields 100+ notification services via simple URLs (`ntfy://`, `discord://`,
  `slack://`, …) - the same library changedetection.io uses. Adding a channel is configuration, not code.
  Covers the original ntfy + Discord targets directly.
- **Cons:** A dependency in the notification path; payloads are Apprise's shape, less bespoke per provider.

### Option C - Generic outbound webhook only

- **Pros:** Zero provider code.
- **Cons:** Pushes all formatting/routing onto the user or an external relay; poor UX for "just send me a
  Discord message."

## Decision

**Use Apprise (Option B).** Channels are named Apprise URLs. Crucially, URLs may embed **`${VAR}`
placeholders** (e.g. `ntfys://${NTFY_TOKEN}@host/topic`) that are resolved from the process environment
**at send time** - so the stored channel record never contains the secret. Templated titles/bodies (Jinja2)
render the notification per match.

## Consequences

### Positive

- 100+ targets for free; new channels need no code.
- Secret hygiene: credentials live only in the environment (and, in deployment, in a gitignored `.env` on
  the runner), never in the DB or in `config.yml` snapshots.

### Negative / risks

- Reliant on Apprise's URL formats and maintenance. Low risk given its breadth and adoption. Per-channel
  throttling is handled in `core/notify.py` to respect provider rate caps (e.g. Discord).
