# ADR-192 — The production alert set lives as committed REST-shape definitions (P34.4)

- Date: 2026-10-02
- Status: accepted (engineering; the live legs are window-queued — D-P34.4-1)
- Ticket: P34.4 (Round 11 / P34, row 205; requirements SIG-OPS-006 partial,
  QA-3/QA-4/QA-5/QA-8-disable; cited: SIG-ENG-042)
- Base: `r11/P34.3-ops-data-protection` (Round-11 chain)

## Context

P34.4 must make production failures reach a human *and* commit the alert set
as definitions that can be diffed against the live project. Track 0.5 created
the channel, two uptime checks and four policies by hand
(`docs/build/reports/` Track-0.5 record); this ticket adds a TLS-expiry policy,
a `SIG-ALERT` log-match policy, extends the failed-job policy to `sig-probe`,
disables the redundant `reingest.yml` schedule, and rolls `sig-probe` onto the
current cadence.

Two design questions needed a recorded answer:

1. **Where do the definitions live and in what shape?** Options: a Terraform
   module, a bespoke YAML domain language, or the Cloud Monitoring REST
   resource shape. The repo's ops precedent is `gcloud`-driven shell with
   recorded evidence (P34.3's `protect.sh`), not a Terraform toolchain.
2. **Does the failed-job policy's authorized update carry
   `notificationRateLimit`?** Deliverable 5 requires daily re-notification for
   a condition red > 24 h "where the policy type supports it, else recorded as
   owed to P35.2". The strictest reading of the S5-3 mutation ("the
   job-failure policy extended to `sig-probe`") touches only the filter.

## Decision

**Definitions**: `ops/monitoring/*.json` — one file per live resource in Cloud
Monitoring REST shape **minus volatile fields** (`name`, `creationRecord`,
`mutationRecord(s)`, `verificationStatus`, condition `name`s), with the project
id templated as `{project}` and a `_sig` envelope (`kind`, match `id` or
`displayName`, `apply: diff-only|create|update`, `source`). This is exactly the
JSON `gcloud monitoring policies create|update --policy-from-file` consumes, so
a def is simultaneously the diffable record and the apply payload — no second
schema to drift. A def leaf whose whole value is a `<placeholder>` never
compares; that is how the operator's e-mail address stays out of the repo while
the channel still verifies (`channel.operator-email.json` carries
`"<redacted …>"` — committing the address is forbidden).

**Verify**: `sig-ops monitoring-defs verify` (`ops/src/ops/monitoring_defs.py`)
normalises live resources the same way and emits `OK/DRIFT/MISSING/EXTRA` per
resource + `probe: monitoring-defs-verify result=ok|drift`, exit 1 on any
non-OK — the P35.3-probe line shape (SIG-ENG-042: a scheduled check that
measured nothing must fail). `ops/gcp/alerts.sh --verify [--from-state DIR]`
wraps it and adds the workflow-state and sig-probe-pin rows.

**Apply path**: `ops/gcp/alerts.sh` — the only write path; dry-run default,
window guard (never 03:00–10:00Z; the sig-probe image roll additionally never
inside AR-3), pre-state capture, per-leg rollback recorded. Creates are
idempotent (displayName match → update in place); an update's rollback is the
captured prior definition rendered through the same normaliser.

**Re-notification**: the failed-job policy's update carries
`notificationRateLimit=86400s` in the same write — deliverable 5 asks for daily
re-notification where the type supports it, and this is the only pre-existing
policy the mutation list authorises this ticket to write. The same field on the
other three Track-0.5 policies is **owed to P35.2** (`D-P34.4-3`) — they are
not in the authorised mutation set.

**sig-probe roll**: reuses `sig-ops roll-jobs --job sig-probe` (ADR-111
digest-pinning, before/after record, `SIG_CODE_COMMIT`) over an image built
from `git archive HEAD` via `gcloud builds submit` — `probe-hosted` reads its
targets from `/app/ops/cadence.toml` baked into the image, so the image roll
*is* the cadence re-roll. The `jobfail` extension is gated on the roll's next
sweep being green (contract ordering; `alerts.sh jobfail` exits 42 and queues
otherwise).

**Workflow**: `reingest.yml` keeps `workflow_dispatch` (a manual operator
re-ingest remains available) and loses `schedule:`; the live disable is
`gh workflow disable reingest.yml`. Rollback: `gh workflow enable` + restoring
the block from git history.

## Consequences

- `alerts.sh --verify` post-leg = `9 OK, 0 DRIFT` over the committed set
  (6 policies + channel + 2 uptime checks) plus workflow/probe rows.
- The diff itself is the backlog: pre-leg it shows exactly the queued work
  (jobfail DRIFT + two MISSING), which is honest rather than noise.
- An unmanaged console-side policy surfaces as `EXTRA` — drift is
  bidirectional.
- P35.2 inherits: `notificationRateLimit` on the remaining three Track-0.5
  policies, escalation beyond e-mail, and any channel/check recreation path
  (the `diff-only` defs are the seed).

## Revisit trigger

P35.2 lands the full alerting-as-code mechanism (reconciliation, escalation,
channel/check recreation) — at that point this ADR's file-per-resource shape is
either absorbed into that mechanism or confirmed as its substrate; also revisit
if a second notification channel is added (the `<placeholder>` rule must stay
the only redaction).
