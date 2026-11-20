<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.2 Wave-C — L3 leg report (`P37.2-l3-national-run`) — **ADMITTED, EXECUTION-BLOCKED (IAM drift)**

Run: `r11/P37.2-live-1`, runner `devin-desktop/swe-2-high/subagent`,
`SIG_GCP_PROJECT=zeta-medley-508121-u7`, ADC `14stevevitali@gmail.com`.

## Status

- **Admit gate:** `sig-ops wave-c-gate --inputs inputs-l3-admit.json`
  at `now=2026-11-20T08:48:36Z` → **exit 0 GO**, all 9 criteria green
  (`gates/l3-admit-2026-11-20T0848Z.json`).
- **Driver:** `wave-c.sh --apply --leg L3 --inputs inputs-l3-admit.json`
  with `SIG_JOB_IMAGE=…/sig-api:p37-2-80ec72ba6534` → **exit 1 at
  08:49:56Z**, inside the L3.2 fleet reconcile's FIRST job deploy
  (`driver/l3-apply.log` is the verbatim transcript).
- The leg is **blocked, not refused**: the admission stands; the leg
  re-runs with a fresh `now` once the IAM prerequisite lands. Every
  minute of delay erodes the strict `<2026-11-21T00:00Z` close bound.

## The blocker — declared-but-absent secret-accessor bindings

`scheduled-ops.sh --apply` deploys every job as its declared class
service account with `--set-secrets` re-declared. Cloud Run's
deploy-time validation requires each bound secret's accessor:

```
ERROR: spec.template.spec.containers[0].env[11].value_from.secret_key_ref.name:
Permission denied on secret: projects/873541617837/secrets/sig-pg-password/versions/latest
for Revision service account sig-probe-rt@zeta-medley-508121-u7.iam.gserviceaccount.com.
The service account used must be granted the 'Secret Manager Secret Accessor' role
(roles/secretmanager.secretAccessor) at the secret, project or higher level.
(same for env[12] → sig-alert-webhook-token)
```

Live evidence (`l3-blocker/`):

- `sig-pg-password` accessor bindings: `default-compute` +
  `sig-api-rt` only. Declared consumers
  (`ops/iam_identities.toml` `[[secret]]` consumer matrix):
  `sig-api-rt`, `sig-ingest-rt`, `sig-probe-rt`, `sig-export-rt`,
  `sig-materialize-rt`, `default-compute` — so `sig-ingest-rt`,
  `sig-probe-rt`, `sig-export-rt`, `sig-materialize-rt` are
  **declared but absent**.
- `sig-alert-webhook-token` accessor bindings: `default-compute` +
  `sig-alerts-rt` only. Declared consumers add `sig-probe-rt` +
  `sig-quality-probe-rt` — both absent.
- The other keyed secrets (`sig-muckrock-refresh`, `sig-data-gov-key`,
  `sig-openstates-key`, …) carry `default-compute` only —
  `sig-ingest-rt` absent on all of them.
- Project IAM has no `secretAccessor` grant at all; per-secret
  bindings are the only path.
- Admin-activity log: **no `SetIamPolicy` on secrets in the last
  10 days** — consistent with never-applied rather than a recent
  deliberate revocation (see below).
- `job-sa-image-table.txt`: the fleet is mixed —
  `sig-probe` already runs `sig-probe-rt`; the ingest jobs
  (`osm-overpass`, `camreg-batch-05`, `replay-ingest`, `muckrock`)
  and `sig-materialize` still run `default-compute` — the P34.42b
  jobs-iam `jobs`/`bindings` actions never completed fleet-wide.
- `iam-bucket-restricted.json`: the restricted bucket likewise has
  no class-SA bindings — the declared conditioned `objectUser`
  grant (ADR-201) is unapplied. Jobs work today only because they
  run as `default-compute` (`roles/editor` → legacy owner member),
  except `sig-probe` whose runtime secret/bucket paths evidently
  resolve (its 06:01Z sweep stored rows + alerted, running
  `sig-probe-rt`).

Every secret-binding deploy in the reconcile would hit the same
refusal — the reconcile cannot proceed past job #1 while the
declared consumer bindings are absent.

## Why the driver is stopped here (not improvised around)

- Restoring the bindings is a production IAM grant **not enumerated**
  in this ticket's OM-14 mutation list (backup; disk pre-grow; tier
  bump + revert; cadence retarget + rebuild; national run; ER
  rematerialize; mirror retirement; Wave-B pause — each behind its
  gate). The committed repair machinery is the P34.42b jobs-iam
  `bindings` action (`ops/gcp/iam-job-identities.sh --apply
  bindings` — windowed + its own operator go record).
- The bindings are declared-and-absent, not invented — but applying
  them inside Wave-C's window is still an IAM mutation the recorded
  authorization does not name. Recorded + reported, per the
  fail-closed rule — never improvised.

## Mutations that DID land before the stop (all receipted)

| mutation | receipt | note |
|---|---|---|
| Cloud Build `e26a2a8d` SUCCESS 08:45:03Z (2m53s) | `image/` | `sig-api:p37-2-80ec72ba6534` → `sha256:9aaec866…05489` from `git archive` HEAD `80ec72ba` (carries P37.1 `3bde97b1` code + the committed mirror-retirement diff) |
| `sig-materialize` re-imaged 08:47Z | `l3-blocker/sig-materialize-image.txt` | now `@sha256:9aaec866…` — needed for the ER step (P37.1's `camera_sites_pg._TARGETS_SQL` osm-subject admission); prior `sha256:e0674d95…` is the recorded restore point |
| `gcloud services enable cloudscheduler.googleapis.com` | driver log | idempotent no-op |
| `sig-probe` job spec — deploy reported a validation error, but the spec update persisted | describe in `job-sa-image-table.txt` | image now `@sha256:9aaec866…`, SA `sig-probe-rt`, env/secrets re-declared — consistent with the reconcile's intended end state; its runtime paths were already working under `sig-probe-rt` (06:01Z sweep stored + alerts fired) |

Nothing else mutated: no ingest/batch job re-deployed, no scheduler
trigger changed, no declaration bundle republished, no run invoked.

## Bounded repair options for the operator (either unblocks L3 today)

1. **Scoped grants (smallest):** `gcloud secrets add-iam-policy-binding`
   for the declared-but-absent consumers the reconcile deploys:
   `sig-probe-rt` on `sig-pg-password` + `sig-alert-webhook-token`;
   `sig-ingest-rt` on `sig-pg-password` + the per-source keyed secrets
   (`sig-muckrock-refresh`, `sig-data-gov-key`, `sig-openstates-key`,
   `sig-sam-gov-key`, `sig-us511-*-key`). All are verbatim-declared
   consumers in `ops/iam_identities.toml`.
2. **The declared leg:** `ops/gcp/iam-job-identities.sh --apply
   bindings` — applies the whole consumer matrix + class grants
   (heavier; also applies bucket/project grants + `jobs_revoke`
   removals off `default-compute` — wider blast radius inside a live
   wave; the scoped set is the tighter repair).

After the repair: re-run the same admit inputs with a fresh `now`
(the admission re-judges) → `wave-c.sh --apply --leg L3` with the same
`SIG_JOB_IMAGE`. The reconcile is idempotent (deploys + upserts).

## Unrelated operational observations (recorded, not blockers)

- `sig-probe` sweeps have been alerting `CRITICAL` on
  `sig-public-okc-manifest` + `sig-public-france-manifest`
  `DOWN (unreachable)` since at least 2026-11-19 — pre-existing,
  unrelated to this leg (public surface is HG-11 territory).
- The `2026-11-16` scheduled `osm_overpass` run failed on an Overpass
  502 Gateway Timeout (recorded `content_drift`, exit 5) — upstream
  flakiness, not the IAM drift.
