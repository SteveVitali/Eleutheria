# P35.2 — alert-roll packet (prepared, not executed)

Ticket `346_P35.2__alerting-as-code-and-escalation.md` /
R11-OPS-02 — alerting as code + probe targets out of the image +
escalation (SIG-OPS-006, SIG-OPS-007; codifies and extends P34.4).

**Status: `prepared_not_executed` — no production write was
attempted, no `gcloud`/`gh`/`storage` mutation ran, no Monitoring
resource was touched.** The roll is a named mutation (OM-20: the
GATE-G5 list names this row verbatim); its live leg additionally
needs the hosted environment and a valid AR-3 + AR-2 window, and
neither held at the run clock. Deferred: `D-P35.2-1`
(`docs/tickets/DEFERRALS.md`).

Machine-readable twin: `ALERT_ROLL_PACKET.json`
(`alert-roll-packet/1`).

## Why nothing ran (recorded at 2026-10-26T07:38Z, `date -u`)

- **Hosted environment absent.** `SIG_GCP_PROJECT` is unset and no
  Application Default Credentials are configured in this shell —
  `lib.sh require_adc` would refuse (exit 3) before any mutation.
- **Window posture.** The run clock (Sunday 2026-10-26 ~07:38Z) is
  outside the preferred weekday 14:00–20:00Z AR-3 slot and inside no
  batch window; the roll is operator-windowed work, never a
  Sunday-night write. AR-2's on-demand backup first is the
  operator's recorded step — it was not taken.
- **OM-20 naming holds** — the GATE-G5 list names this row — but a
  named mutation still runs only inside its window with its
  environment; silence is never a substitute.
- The script's own guard re-queues (exit 42) inside the 03:00–06:30Z
  freeze or an AR-3 batch window — it cannot be accidentally forced.

## Re-run prompt (verbatim)

```
implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true
```

Resumed apply is **idempotent-reconcile**: every leg reads live
state first and either converges or skips (`SKIP retention` /
`SKIP versioning` / create→update-in-place) — it never re-creates a
resource that already matches the committed def.

## The mutation set (the contract's OM-14 list)

| # | resource | leg | verb |
|---|---|---|---|
| 1 | alert policies (6 defs: 4 update + 2 create-or-update) | `policies` | `gcloud alpha monitoring policies update\|create --policy-from-file` |
| 2 | uptime checks (2 defs: site content match + API /health; 5 min, 3 regions) | `uptime` | `gcloud monitoring uptime update\|create` (argv rendered by `monitoring-defs render-uptime`) |
| 3 | notification channel | gate only | `beta monitoring channels list` — P34.4's `apply=diff-only`; the policies leg REFUSES (42) while it is absent |
| 4 | log retention `_Default` 30 → 90 | `retention` | `gcloud logging buckets update _Default --retention-days=90` (the restricted-sink alternative stands recorded in the contract) |
| 5 | bucket versioning (ops/probes/ + ops/runs/ → `sig-restricted`) | `versioning` | `gcloud storage buckets update --versioning` |
| 6 | probe targets out of the image (G1-02a) | `bundle` + `proberoll` | `live-diff --emit-declared` → `storage cp`; `--update-env-vars=SIG_OPS_DECLARED_GCS`; image rebuild + `roll-jobs` digest pin |

## Ordered apply sequence (verbatim)

```
ops/gcp/alerting.sh --apply prestate     # AR-2 captures (below) + sha256s
ops/gcp/alerting.sh --apply bundle       # republish ops/declared/live-diff.json
ops/gcp/alerting.sh --apply policies     # gate: channel present; reconcile 6 defs
ops/gcp/alerting.sh --apply uptime       # resolve id by displayName; rendered flags
ops/gcp/alerting.sh --apply retention    # describe first; update to 90
ops/gcp/alerting.sh --apply versioning   # describe first; enable versioning
ops/gcp/alerting.sh --apply proberoll    # bundle + env assert + build + roll-jobs
ops/gcp/alerting.sh --verify             # 9 OK + posture rows; exit 1 on any non-OK
```

—or one shot: `ops/gcp/alerting.sh --apply all` (prestate → every
leg → post-state verify).

## AR-2 pre-state captures (the restore point, per leg)

Every mutating leg captures its own pre-state into
`docs/build/logs/alerting/apply-<ts>/` (gitignored) before it
writes; `prestate` captures the full posture into `pre-<ts>/`
with `sha256s.txt` sidecars. The restore point = the committed IaC
text (`ops/monitoring/*.json`, `ops/cadence.toml`) plus:

- `channels.json` / `uptime-checks.json` / `alert-policies.json` —
  the three Monitoring list captures `monitoring-defs verify`
  consumes.
- `log-retention.json` — `_Default` describe (the retention
  leg's rollback target: `--retention-days=<captured>`).
- `restricted-bucket.json` — versioning posture (rollback:
  `--no-versioning`).
- `sig-probe.job.json` / `.image.txt` / `.declared-env.txt` —
  the job's before-digest (rollback: `roll-jobs --image
  <before>`) and env.
- `sig-alerts.service.json` / `.image.txt` — the digest record
  (§3.3: `:latest` is DRIFT).
- `policy.<id>.prior.json` + `.prior.rendered.json` — per-policy
  rollback bodies (`--policy-from-file`).
- `uptime.<id>.prior.json` — per-check rollback input.
- `declared-bundle.prior.json` — the bundle object before republish.
- `ssl-cert.json` — the cert the 21-day policy watches.

## Rollback summary

| leg | rollback |
|---|---|
| policy update | `policies update <id> --policy-from-file=<captured prior>` |
| policy create | `policies delete <new id>` |
| uptime update | re-apply `uptime.<id>.prior.json` via the same `render-uptime` flags |
| uptime create | `gcloud monitoring uptime delete <new id>` |
| retention | `logging buckets update _Default --retention-days=<captured>` |
| versioning | `storage buckets update --no-versioning` |
| bundle | `storage cp <prior bundle> gs://…/ops/declared/live-diff.json` |
| proberoll | `sig-ops roll-jobs --job sig-probe --image <recorded before-digest>` |

## The monthly delivery test (after the roll)

`probe-hosted --extra-target
forced-failure-drill=https://does-not-exist.invalid.example --alert`
on the rolled `sig-probe` produces a DOWN row → the recorded alert →
`SIG-ALERT` log line → the log-match policy's incident → e-mail in
< 1 h (SIG-OPS-006's AC). The mechanism stays available in
`probe-hosted --extra-target` — a *planted* failure, reversed and
receipted, never a real incident.

## Check-mode plan (recorded verbatim, `alerting.sh --check all`)

See `PLAN.txt` beside this file — the same lines the apply prints
before each leg.
