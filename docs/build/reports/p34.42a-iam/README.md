# P34.42a — IAM live leg 1 records (the least-privilege service-identity leg)

The queued OM-19 leg of `docs/tickets/251_P34.42a__least-privilege-service-identities.md`
(`ops/gcp/iam-service-accounts.sh`, declaration `ops/iam_identities.toml`,
`sig.iam-identities/1`) ran 2026-10-14 on live-leg branch `r11/P34.42a-live-1`
against project `zeta-medley-508121-u7` (region `us-central1`), inside its window
(≥ 2026-10-13T12:00Z, outside 03:00–06:30Z; `date -u` stamps in the transcripts
under `logs/`). Harness `devin-desktop/swe-2-high/subagent`.

**Outcome: STOPPED at the `revisions` step and rolled back to the recorded
prestate — `live:P34.42a` NOT satisfied.** The `sig-alerts` same-image revision
was refused by Cloud Run because the service mounts `sig-alert-webhook-token`
as env `SIG_ALERT_WEBHOOK_TOKEN` (`secretKeyRef` key `latest`, visible in
`pre/service-sig-alerts.json`), so its runtime SA must hold
`roles/secretmanager.secretAccessor` on that secret — while the landed
declaration asserts `sig-alerts-rt` carries *no* secret access. A production
read contradicting a record voids the S5-3 pre-authorisation (contract
§ Production mutations / OM-20), so the leg stopped per the stop rules, ran the
scripted `rollback`, and reported `D-P34.42a-1` (the operator decision on the
declaration defect). Production was verified byte-for-byte back at the recorded
prestate.

## What ran (all times `date -u`; transcripts in `logs/`)

| step | result |
|---|---|
| `prestate` (10:02:50Z) | captured under `pre/` — project + per-service + per-secret + web-bucket IAM, service describes, `sig-probe` job describe (caller identity), 39-route byte-compare baseline per service, sha256 sidecars |
| `identities` (10:03:49Z) | created `sig-api-rt`, `sig-web-rt`, `sig-alerts-rt` (later deleted by rollback) |
| `bindings` (10:03:5xZ) | `roles/cloudsql.client`→`sig-api-rt` (project); `roles/storage.objectViewer`→`sig-web-rt` (`gs://zeta-medley-508121-u7-sig-web`); `secretAccessor`→`sig-api-rt` on `sig-pg-password` (all removed by rollback) |
| `revisions` (10:04:1xZ) | `sig-api` → `sig-api-00011-wic` on `sig-api-rt` (serving, `/health` 200); `sig-web` → `sig-web-00003-4qd` on `sig-web-rt` (serving, 200); `sig-alerts` **REFUSED** — `Permission denied on secret …/sig-alert-webhook-token/versions/latest for Revision service account sig-alerts-rt@…` |
| `invoker` | not run (leg stopped before it) |
| `rollback` (10:0xZ) | services restored to the recorded compute-SA identity at the same image digests; `sig-alerts` invoker policy re-set from the capture (unchanged — `allUsers` still invoker); added bindings removed; the three `-rt` SAs deleted |
| post-rollback verify (10:08:57Z) | `post-rollback/` capture matches `pre/` field-for-field (same SA, same image digest, same env, `allUsers` invokers, SA list = compute + `sig-scheduler`, `sig-pg-password` accessor = compute only, web-bucket `objectViewer` = `allUsers` only); `sig-ops route-compare verify`: **39/39 routes byte-identical per service** |

## Files

- `pre/` — the AR-2 restore point taken before any mutation (all reads;
  `date -u` inside each capture; `sha256s.txt` sidecars over the committed,
  sanitized bytes).
- `post-rollback/` — the post-rollback re-capture used for the prestate-match
  verification above.
- `logs/` — the verbatim `iam-service-accounts.sh` transcripts per step.
- Sanitization: the operator's account e-mail is replaced by
  `<redacted-operator-account>` in every committed byte (Round-11 rule: the
  operator's personal e-mail is never added to a file). It appears in the raw
  captures only as `serving.knative.dev`/`run.googleapis.com` `creator`/
  `lastModifier` annotations and the project policy's `roles/owner` `user:`
  member — no credential or secret material exists in any file (policies are
  IAM metadata only; env-only secrets were never read).
- `pre/secret-sig-audit-password-iam.json`, `…-sig-recovery-password-…`,
  `…-sig-er-rerun-password-…` read `{"bindings":[]}` — those secrets do not
  exist yet (P34.43/P34.45 create them; the script records the absence rather
  than failing). `sig-api-env`, `sig-maproulette-api-key`, `sig-zenodo-*` exist
  with no bindings (etag-only captures).

## The contradiction (the leg's finding)

`pre/service-sig-alerts.json` shows `sig-alerts` mounting
`sig-alert-webhook-token` (`SIG_ALERT_WEBHOOK_TOKEN`, key `latest`) — the
receiver authenticates incoming alert posts with that bearer token
(`ops/src/ops/alerts.py`). `ops/iam_identities.toml` (landed by PR #252)
declares `sig-alerts-rt` "no project roles, no secret access" and omits it
from `sig-alert-webhook-token`'s `consumers` (which names only
`sig-probe-rt`/`sig-quality-probe-rt`). A least-privilege fix exists — add
`sig-alerts-rt` as a consumer of that one secret, grant it, re-run the leg —
but that grant is not in the scripted mutation list and the declaration's diff
would flag it, so it is the operator's call (D-P34.42a-1), never an improvised
step.
