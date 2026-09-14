# ADR-077 — Observability & alerting: the recorded-alert ledger, the env-webhook notifier, and bounded JSONL logs (vs a hosted monitoring stack)

- **Status:** Accepted
- **Phase / ticket:** P24.3 — Observability & alerting (OBS.1, GL-OBS-01)
- **Date:** 2026-09-13
- **Related:** ADR-067 (the egress-budget alarm `ops.egress` + degraded mode + the
  monthly `keepalive.yml` this ticket wires, not re-implements), ADR-075 (the
  zero-cost GCP host the probes measure), ADR-076 (the free GitHub Actions cron
  precedent), ADR-066 (`sig-ops` runtime composition — the stack being observed);
  SIG-STORE-003 (binding zero-cost posture), SIG-GOV-020/021 (degraded mode +
  keepalive), SIG-EXPORT-008 (egress is the existential cost), RISK-P0-07/P0-12/
  P21-09, RISK-P24-02; HG-09 (secrets env-only).

## Context

OBS.1 (GL-OBS-01) asks for four things inside the zero-cost posture: metrics, logs
and alerting for the live stack; the INFRA.1 egress-budget alarm **wired to a real
notifier**; keepalive verification; and uptime + error budgets with bounded log
retention, plus a dashboard/readout.

The landed seams to build on (re-confirmed at build time):

- `ops/egress.py` already *decides* the alarm — `build_report` is a pure
  (usage, budget) function with `ok`/`warn`/`alarm`/`gate-pending` levels and
  `exit_code_for` = 5 on breach (`sig-ops egress-report`, RISK-P21-09). What it
  lacked is a **notifier**: the exit code is only seen by whoever ran the command.
- `.github/workflows/keepalive.yml` already fails loudly when the degraded rebuild
  breaks — but a red workflow is only a notification if someone looks; a keepalive
  failure was not *recorded* anywhere durable.
- `sig-ops status`/`up` already probe PG/API/curation/static health — but the
  results were ephemeral: nothing was measured over time, so "uptime" and an
  "error budget" had no data to compute from.

Two constraints shape the design: **SIG-STORE-003** (zero-cost — no hosted
metrics/alerting service, no paid pager) and **HG-09** (secrets are env-only,
never a file). A notifier that needs an account or a credential literal fails the
first; a log line that can leak a webhook URL fails the second.

## Decision

**1. The notifier seam is: record first, notify second — always.** Every alert
goes through `ops.alerts.fire`, which appends to the **recorded-alert ledger**
(append-only JSONL, `.sig/ops/alerts.jsonl`, env `SIG_ALERT_LOG`) *before* any
external delivery is attempted. The record is the deterministic artifact; delivery
is best-effort. Notifiers (`ops.alerts.notifiers_from_env`): the `LogNotifier`
(a `SIG-ALERT` stderr line — what a workflow log or a host journal captures) is
always on; the `WebhookNotifier` activates when `SIG_ALERT_WEBHOOK_URL` is set
(e.g. a free `ntfy.sh` topic, a self-hosted hook, or the host's own endpoint),
with an optional `SIG_ALERT_WEBHOOK_TOKEN` Bearer header. **Env-only, no paid
service, no credential literals.**

**2. INFRA.1's alarm is consumed, not re-implemented.** `sig-ops egress-report
--alert` keeps the breach decision in `ops.egress.build_report` verbatim and fires
a recorded alert (`kind=egress-budget`, severity `warn`/`alarm`) when the level
crosses the configured `alarm_ratio` — `gate-pending` (no live usage API, HG-07)
still fires nothing.

**3. Metrics are a bounded JSONL probe log; budgets are a pure function.**
`sig-ops probe` runs `observe.probe_stack` — the same `http_ok`/`pg_ready`
implementation `status`/`up` now reuse (one probe definition, no drift) — and
appends one row per service (ok / latency / ts) to `.sig/ops/probes.jsonl`
(env `SIG_PROBE_LOG`). `observe.compute_uptime` derives per-service uptime and
error-budget burn over the rolling `[observability]` window in `ops/config.toml`
(`uptime_target_pct = 99.0`, `window_days = 30`): a service with no in-window
probes reports `no-data`, never a fabricated 100% (§3.1).

**4. Bounded log retention is an age + byte cap on the files.** `prune_jsonl`
drops rows older than `retention_days` (30) and truncates oldest-first to
`probe_log_max_bytes` (1 MiB). A file with a cap, not a paid log service —
retention bounded *within* the zero-cost posture, and it bounds the alert ledger
the same way (`sig-ops alerts --prune`, `dashboard` prunes before reading).

**5. Secret hygiene is structural, not by convention.** Every string that reaches
a log line, the ledger, or the webhook body passes `scrub_secrets`, which masks
the *values* of secret-looking env vars (`*_TOKEN`/`_SECRET`/`_PASSWORD`/`_KEY`,
plus `SIG_ALERT_WEBHOOK_URL` whose path may itself be the credential) with
`***redacted***`. The webhook URL is never logged. Asserted by test.

**6. The dashboard is a markdown readout, not a hosted surface.** `sig-ops
dashboard` renders service health, uptime vs error budget, the egress level, the
keepalive verification, and the recorded alerts — deterministic, no client JS
(the public zero-JS budget is untouched; this is an operator artifact).
`.github/workflows/observability.yml` runs the sweep daily (egress check → probe
when endpoints are configured → readout → artifact upload); `keepalive.yml` gains
an `if: failure()` step that fires a recorded alert (`sig-ops alert`).

**7. Keepalive verification is two checks** (`observe.verify_keepalive`, driven by
`sig-ops keepalive-check`): the *machinery* (the workflow file still carries a
`cron:` schedule and still runs `sig-ops degraded`) and the *function* (the
degraded rebuild actually produces `web/dist`). A failure fires a recorded
`critical` alert and exits 6.

## Consequences

- The live stack is observable at $0: metrics (probe log), logs (bounded JSONL),
  alerting (ledger + log + optional webhook), budgets (`compute_uptime`), and a
  readout (`dashboard`) — all over the same files an operator can inspect or a
  workflow can upload.
- A breach is now *recorded* even when nobody is watching and even when no
  notifier is configured — the "recorded alert" acceptance is deterministic.
- The seam is forward-compatible: adding a notifier is one `Notifier`
  implementation; the ledger, scrubbing, and CLI do not change.
- Offline/honest posture preserved: no endpoint configured → `no-data`, never a
  fabricated green.

## Alternatives considered

- **Hosted monitoring/alerting (Grafana Cloud, UptimeRobot, PagerDuty, GCP
  Monitoring alerts)** — rejected as the default: each needs an account and most
  a paid tier or credentials, against the binding zero-cost posture (SIG-STORE-003).
  The webhook seam still lets an operator *plug one in* without code changes.
- **Prometheus + Alertmanager on the host** — rejected: heavier than the workload
  (one small VM already saturated by the compose stack, ADR-075) and adds a second
  always-on surface; the JSONL log + `compute_uptime` answers the same question
  with no new infra.
- **GitHub Issues/commit-comments as the notifier (`gh` CLI)** — rejected as the
  *only* sink: needs a `GH_TOKEN` (env-only is fine) but couples alerting to one
  vendor and pollutes the repo; kept as a possible additional `Notifier` later.
- **SMTP email** — rejected: needs relay credentials and is no more observable
  than the webhook it would duplicate.
- **Keep the probes inside `cli.py`** — rejected: two copies of `http_ok`/`pg_ready`
  would drift between what `status` reports and what the monitor records; they
  now live once in `observe.py` and the CLI imports them.

## Revisit trigger

Revisit this decision when any of the following holds:

- **The hosted stack is live (HG-12 / D-ACCT.1-1 resolved) and real probe traffic
  exists.** Confirm `uptime_target_pct = 99.0` matches what an e2-micro +
  scales-to-zero API can actually hold; tighten or split per-service targets if
  the aggregate hides a flaky service.
- **A real notifier is configured.** When `SIG_ALERT_WEBHOOK_URL` first delivers,
  confirm the payload shape suits the endpoint (a generic JSON POST may want a
  per-provider formatter — add a `Notifier`, don't fork `fire`).
- **The probe log grows past the byte cap faster than the age cap** — i.e.
  retention is dropping in-window rows: raise `probe_log_max_bytes` or probe less
  often; the caps are config, not code.
- **Alert volume makes the JSONL ledger the wrong store** (needs query/dedup/
  escalation policies): promote the ledger to a table or a real alertmanager —
  the `fire`/`Notifier` seam is the only surface that changes.
- **The free cron decays again** (RISK-P0-12): if the daily `observability.yml`
  sweep is disabled for inactivity, the keepalive failure path is already wired —
  but the *sweep* would need a host-cron fallback on the GCE box (ADR-075).
