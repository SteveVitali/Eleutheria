# P34.42a — IAM live leg 2 records (the least-privilege service-identity leg, operator-approved retry)

The queued OM-19 leg of `docs/tickets/251_P34.42a__least-privilege-service-identities.md`
(`ops/gcp/iam-service-accounts.sh`, declaration `ops/iam_identities.toml`,
`sig.iam-identities/1`) re-ran 2026-10-14 on live-leg branch `r11/P34.42a-live-2`
against project `zeta-medley-508121-u7` (region `us-central1`), inside its window
(≥ 2026-10-13T12:00Z, outside 03:00–06:30Z; `date -u` stamps in the transcripts
under `logs/`). Harness `devin-desktop/swe-2-high/subagent`. Branch base
`9a02c24f` — the repaired record-isolation base; the poisoned unsigned-decision
head `3a7916d6` was never incorporated.

**Outcome: COMPLETE — `live:P34.42a` satisfied.** Leg 1 stopped when Cloud Run
refused the `sig-alerts` same-image revision because the service mounts
`sig-alert-webhook-token` as env `SIG_ALERT_WEBHOOK_TOKEN` while the landed
declaration gave `sig-alerts-rt` no secret access (`D-P34.42a-1`). The operator
answered `"approve, proceed"` (LEDGER GATE DECISIONS confirmation,
2026-10-14T12:27:08Z) — option (a) only: declare `sig-alerts-rt` a consumer of
`sig-alert-webhook-token` plus the one scripted
`roles/secretmanager.secretAccessor` grant, then run this verbatim retry. The
declaration was amended accordingly (nothing else changed), and the leg ran
end-to-end: every service serves 100 % on its dedicated runtime SA at a
byte-identical image digest, `sig-alerts` invokes by IAM only (no `allUsers`),
and public responses are byte-for-byte unchanged.

## What ran (all times `date -u`; transcripts in `logs/`)

| step | result |
|---|---|
| `prestate` (12:48:32Z) | captured under `pre/` — project + per-service + per-secret + web-bucket IAM, service describes, `sig-probe` job describe (caller identity), 39-route byte-compare baseline per service, sha256 sidecars. Semantically identical to leg 1's post-rollback state (only `captured_at`/redaction/user-metadata drift) — the declared diff was exactly the eight expected pending mutations, nothing else |
| `identities` (12:49:06Z–07Z) | created `sig-api-rt`, `sig-web-rt`, `sig-alerts-rt` |
| `bindings` (12:49:14Z–15Z) | `roles/cloudsql.client`→`sig-api-rt` (project); `roles/storage.objectViewer`→`sig-web-rt` (`gs://zeta-medley-508121-u7-sig-web`); `secretAccessor`→`sig-api-rt` on `sig-pg-password`; **`secretAccessor`→`sig-alerts-rt` on `sig-alert-webhook-token`** (the approved option-(a) grant) |
| `revisions` (12:49:24Z–25Z) | `sig-api` → `sig-api-00011-wic` on `sig-api-rt`; `sig-web` → `sig-web-00005-hbr` on `sig-web-rt`; `sig-alerts` → `sig-alerts-00007-qcs` on `sig-alerts-rt` — each serving 100 % of traffic. (`sig-api`'s revision reuses leg 1's name because the template — image + SA + env — is byte-identical; Cloud Run revision names are template-addressed.) |
| `invoker` (12:49:51Z–53Z) | `roles/run.invoker` granted to the recorded caller (`873541617837-compute@…`, the `sig-probe` job identity) first, then `allUsers` revoked — final policy carries exactly the one declared binding |
| `verify` (12:49:5xZ–12:5xZ) | poststate under `post/`; `sig-ops route-compare verify`: **39/39 routes byte-identical per service** (117/117 total — `/health` and every sampled route match baseline); `check-revisions`: clean — every workload kept its recorded image; `sig-ops iam diff --leg services`: **clean** — the snapshot carries the declared posture, no unexpected bindings |
| troubleshooter analysis | Policy Troubleshooter reads returned unavailable for every (principal, forbidden-permission, resource) pair — recorded non-fatal by the script (`post/analysis-*.json` are empty captures). The hard check is the captured-policy analysis: **no runtime SA holds a basic role, no `*.delete` on the spine/evidence stores (Cloud SQL instances, `sig-restricted`/`sig-backups`/`sig-public`/`sig-web` buckets), and no accessor on another consumer's secret** — `analysis OK`. No pair answered GRANTED. |
| anonymous probe (`anonymous-probe.txt`) | post-revoke, `curl https://sig-alerts-…/health` anonymous → **HTTP 403** (×2). A probe ~60 s after the revoke caught the app's own 501 page — the IAM revocation had not propagated; after ~90 s the front end consistently denies with 403. `sig-api`/`sig-web` stay public by declaration: anonymous `/health` 200 / `/` 200. |

## Posture now held (verified in `post/`)

- `sig-api` runs as `sig-api-rt` — project `cloudsql.client` + accessor on
  `sig-pg-password` only.
- `sig-web` runs as `sig-web-rt` — `objectViewer` on the web bucket only.
- `sig-alerts` runs as `sig-alerts-rt` — no project roles; accessor on its own
  `sig-alert-webhook-token` only; invokable only by the recorded caller SA.
- No service carries `roles/editor` or any basic role; the default compute SA
  retains only its pre-existing grants (untouched — `sig-probe` still runs on
  it, as declared by `jobs_revoke` for the P34.42b leg).
- `sig-api` + `sig-web` remain `allUsers`-invokable by declaration (public read
  API + public site); every route response is byte-identical to baseline.

## Files

- `pre/` — the AR-2 restore point taken before any mutation (all reads;
  `date -u` inside each capture; `sha256s.txt` sidecars over the committed,
  sanitized bytes).
- `post/` — the poststate capture + the troubleshooter analysis captures +
  `sha256s.txt`.
- `logs/` — the verbatim `iam-service-accounts.sh` transcripts per step.
- `anonymous-probe.txt` — the unauthenticated-invocation evidence for
  `sig-alerts` (403) with the public controls (200).
- Sanitization: the operator's account e-mail is replaced by
  `<redacted-operator-account>` and the local checkout path by `<repo>` in
  every committed byte (Round-11 rule: the operator's personal e-mail is never
  added to a file). It appeared in the raw captures only as
  `serving.knative.dev`/`run.googleapis.com` `creator`/`lastModifier`
  annotations and the project policy's `roles/owner` `user:` member — no
  credential or secret material exists in any file (policies are IAM metadata
  only; env-only secrets were never read).
- `pre/secret-sig-audit-password-iam.json`, `…-sig-recovery-password-…`,
  `…-sig-er-rerun-password-…` read `{"bindings":[]}` — those secrets do not
  exist yet (P34.43/P34.45 create them; the script records the absence rather
  than failing). `sig-api-env`, `sig-maproulette-api-key`, `sig-zenodo-*` exist
  with no bindings (etag-only captures).

## What changed vs leg 1 (the approved declaration amendment)

`ops/iam_identities.toml`: `sig-alert-webhook-token`'s `consumers` now names
`sig-alerts-rt` first (the receiver mounts it as `SIG_ALERT_WEBHOOK_TOKEN` —
the leg-1 finding), and `sig-alerts-rt`'s purpose records "no project roles;
accessor on its own `sig-alert-webhook-token` only". The engine derives the
one new scripted grant (`sig-alerts-rt` → `secretAccessor` on
`sig-alert-webhook-token`) from the consumer matrix; the script's `bindings`
and `rollback` steps name it explicitly. Nothing else in the scripted mutation
list changed.
