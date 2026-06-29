# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's **"Report a vulnerability"**
(Security → Advisories) on this repository, rather than opening a public issue.
I'll acknowledge within a few days and coordinate a fix and disclosure.

## How secrets are handled

- **Notification credentials never touch the database.** Channels store an
  Apprise URL with `${ENV}` placeholders (e.g. `ntfy://${NTFY_TOKEN}@host/topic`);
  the token is read from the process environment **at send time** and is never
  persisted.
- The optional `GITHUB_TOKEN` is read from the environment only.
- `.env` and `*.db` are gitignored; the repo ships `.env.example` with no values.

## Supported versions

This is a young project; security fixes target the latest `main` / latest
release tag.

## Automated controls

CI runs CodeQL, gitleaks secret scanning, Trivy (filesystem + image), hadolint,
`pip-audit`, and `npm audit`; Dependabot keeps dependencies and base images
current; release images are signed with cosign and ship an SBOM.
