# 0008. Supply-chain-focused CI: signing, SBOM, scanning, coverage floor

**Status:** Accepted

## Context

Going public means the repo and its container image are things other people (and the operator's own
homelab) pull and run. The CI should therefore protect not just correctness but the **supply chain**: no
leaked secrets, no obviously-vulnerable dependencies or base images, and a verifiable provenance for the
published artifact. At the same time, the test suite is young and network-heavy (the poll path talks to
GitHub), so a high coverage target would be dishonest or would push toward brittle over-mocking.

## Options considered

### Option A - Minimal CI (lint + test)

- **Pros:** Fast, simple.
- **Cons:** Says nothing about secrets, dependency CVEs, image provenance, or static-analysis bugs - the
  risks that matter most for something published and self-hosted.

### Option B - Layered quality + supply-chain gates

- **Pros:** Catches different classes of problem: ruff/prettier/pyright/tsc (style+types), pytest with a
  coverage gate (behavior), CodeQL (semantic bugs), gitleaks (secrets), Trivy + hadolint (image/deps),
  pip-audit/npm audit (known CVEs), Dependabot (staleness). Tagged releases publish a **cosign-signed**
  image with an **SBOM**, so consumers can verify provenance and contents.
- **Cons:** More moving parts; more places a flaky external action can fail (seen during setup: a bad
  action version, an uppercase image reference); some gates need tuning.

### Option C - Aim for 80%+ coverage as the headline gate

- **Pros:** Looks rigorous.
- **Cons:** The valuable-but-hard-to-unit-test code is the live polling path; chasing 80% would mean
  over-mocking the network or writing low-value tests. A number that forces bad tests is worse than an
  honest one.

## Decision

**Layered quality + supply-chain CI (Option B), with an honest coverage _floor_.** Four workflows: `ci`
(lint/format/type/test+coverage/audit/hadolint/Trivy-fs), `codeql`, `secret-scan` (gitleaks in
full-history detect mode), and `release` (build -> GHCR -> Trivy image -> SBOM -> cosign sign + attest).
The coverage gate is a **floor (60%)** the suite reliably clears - a regression guard to ratchet up over
time, not an aspiration that invites fake tests. The core filter engine is covered by a dedicated
truth-table suite; the network poll path is exercised end-to-end manually.

## Consequences

### Positive

- Secrets, dependency CVEs, Dockerfile smells, and semantic bugs are caught automatically; releases are
  signed and ship an SBOM, giving the homelab (and anyone) a verifiable image.
- Branch protection requires the core checks to pass before merge, keeping `main` releasable.

### Negative / risks

- More external-action surface and occasional tuning (pinned action versions, lowercased image refs). Cost
  is one-time setup plus Dependabot-managed updates. The coverage floor is explicitly a floor: raise it as
  the service-layer suite grows.
