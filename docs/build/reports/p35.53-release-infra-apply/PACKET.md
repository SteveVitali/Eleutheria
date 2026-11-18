<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P35.53 — release-infrastructure apply packet (**executed green**)

**Status:** `D-P35.53-1`'s apply leg **executed and verified** on 2026-11-18 in
project `zeta-medley-508121-u7` (region `us-central1`) under the operator's
application-default credentials, per the operator's verbatim authorisation
"You run it under my ADC" (2026-11-18, this thread). Run inside a valid
AR-3 + AR-2 window (09:15–09:47Z — outside the preferred weekday 14:00–20:00Z
slot, never inside the forbidden 03:00–06:30Z band).

**Script fixes:** the apply surfaced six defects in
`ops/gcp/release-infra.sh`, fixed on
`r11/ops-release-infra-apply-fixes` (PR #528) — the green legs below ran the
patched script.

## Authorisation & window

- Owner: the operator (OP-24). Executed by the orchestrator under the
  operator's ADC (`stevevitali@gmail.com`, active account) on verbatim go.
- Window guard passed every attempt (`assert_window`); each `all` run
  captured pre-state and took an AR-2 restore point first.

## Restore points (AR-2, on-demand snapshots of `sig-pg` POSTGRES_18)

| capture | sqlpoint dir | latest backupRun |
|---|---|---|
| 09:15Z | `docs/build/logs/restore-point/sqlpoint-20261118T091519Z` | in `post-backups.json` |
| 09:22Z | `docs/build/logs/restore-point/sqlpoint-20261118T092204Z` | in `post-backups.json` |
| 09:25Z | `docs/build/logs/restore-point/sqlpoint-20261118T092511Z` | in `post-backups.json` |
| 09:28Z | `docs/build/logs/restore-point/sqlpoint-20261118T092815Z` | in `post-backups.json` |
| 09:31Z | `docs/build/logs/restore-point/sqlpoint-20261118T093130Z` | `1794994294972` SUCCESSFUL 09:31:34→09:33:06Z |

Pre-state captures: `$STATE_DIR/prestate-20261118T09{1513,2150,2458,2803,3117}Z`
(buckets/services/jobs/project-IAM JSON per capture).

## Precondition: job-class identities (P34.42b `identities` action only)

`sig-release-rt` + `sig-status-rt` were absent — declared by
`ops/gcp/iam-job-identities.sh` but never created. Ran **only** the
sanctioned `identities` action (7 created before an IAM 429, then idempotent
re-run → all 9 declared SAs exist). The disputed `jobs`/`bindings` actions
(88-vs-100 job-map contradiction) were **not** run — that remains an
operator decision.

## Apply arc — three attempts, six script defects

1. **Attempt 1** (unpatched): prestate + sqlpoint + bucket created (UBLA,
   PAP, versioning, lifecycle) + conditioned writer bindings → **failed**
   on the unconditional viewer adds: `Adding a binding without specifying
   a condition to a policy containing conditions is prohibited in
   non-interactive mode`.
2. **Attempt 2** (`--condition=None` added): IAM legs green → **failed**
   deploying `sig-web-staging`: the `name:sa:img` pair parser's
   `img="${pair##*:}"` stripped through the image's `sha256:` colon and
   passed a bare hex digest (`mirror.gcr.io/library/<hex>` not found).
   Staging service stubs registered with failed revisions.
3. **Attempt 3** (`img="${pair#*:}"`): `sig-release` job created on the
   full digest → `do_verify` failed on `bucket-uniform-access` — the
   verify read REST-schema field paths `gcloud storage buckets describe`
   does not emit. Verify paths corrected; staging stubs redeployed with
   the declared production digests (the exact `gcloud run deploy`
   invocation `do_apply` runs); verify iteratively unblocked
   (`env[?name==]` filter unsupported → `--format=json` + python3;
   absent `minScale` annotation means scale-to-zero → default `0`;
   `sha256sum` → `shasum -a 256` fallback).

## Final verified state (`--apply verify` — all green)

- `gs://zeta-medley-508121-u7-sig-release`: `uniform_bucket_level_access=true`,
  `versioning_enabled=true`, `public_access_prevention=enforced`,
  lifecycle `daysSinceNoncurrentTime=30`, private.
- IAM (recorded, no `allUsers`/`allAuthenticatedUsers`):
  `sig-release-rt` `objectUser` conditioned `release-writer-not-status`
  (never `status/**`); `sig-status-rt` `objectUser` conditioned
  `status-writer-only`; `sig-web-rt` + `sig-api-rt` unconditional
  `objectViewer`; legacy project roles only.
- `gs://zeta-medley-508121-u7-sig-restricted`: `sig-release-rt`
  `objectViewer` conditioned `release-reads-exports` (`exports/` only).
- `sig-web-staging` / `sig-api-staging`: IAM-only
  (`--no-allow-unauthenticated`), `SIG_STAGING=1`,
  `SIG_TARGET=production`, scale-0/1, serving the exact live production
  digests — `sig-web@sha256:d8244804eb4fa7db5b0ebe25f0177f4270409e3a6d5f484418efcd03b086ee2b`,
  `sig-api@sha256:40a47dc8a2cf8f68e84aede7e7e3f9f43a03ed823c83a9924d6535970354b722`.
- `sig-release` job: `sig-release-rt`, image = the `sig-api` production
  digest, `SIG_RELEASE_REGISTRY_URI` + `SIG_PROJECT_ID` env set; bare
  execute is a refused no-op by design.

## Probes & refusal matrix (`--apply probe`, `--apply stale-check`)

- Unauthenticated: `sig-web-staging` 403, `sig-api-staging` 403, release
  bucket 401 — nothing publicly reachable.
- Stale-check on the real bucket: first stage journaled
  `staged/p-0bf8b897…`; identical re-stage resumed without rewrite;
  mutated-byte re-stage **refused** (name-collision, SIG-REL-005);
  `status --apply` **refused** on seeded `registry/LOCK` (lock-held);
  stale-generation **refused** (registry moved under held lock). LOCK
  removed after the check.

## Disposition of `D-P35.53-1`

Every acceptance cell is now met and evidenced above; the DEFERRALS.md
status flip (`OPEN` → `DONE`) + `obligation-event/1` transition land on
the orchestration chain after the in-flight P37.66 boundary, to keep the
single-writer ordering on `docs/tickets/DEFERRALS.md`.

Downstream unblock: `D-P37.65a-1` (release-cut + live-crawl), then
`D-P37.65b-1` (promote, on the operator's staged verbatim go —
pre-authorised 2026-11-18 pending candidate + signed readout), then the
`D-P37.63-1`/`D-P37.64-1` post-promote live legs.
