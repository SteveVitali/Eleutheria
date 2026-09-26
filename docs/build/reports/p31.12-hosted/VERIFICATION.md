# P31.12 hosted verification — BREADTH.1 (2026-09-26)

Live-verification evidence for the four P29.3 rights-flipped accountability
sources, run **only as Cloud Run jobs** on the digest-pinned image
`sig-api:ingest-daf83934a7f1`
(`us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-api@sha256:d1f943610f668521f157c94d64f7284eb73025870303ee332f3f9450676e473a`,
Cloud Build `10001895-2913-4a43-a078-74015f889604`, built from `git archive
HEAD` @ `daf83934a7f1` — never `:latest`).

Per-source JSON evidence (the WORM `ops/runs` rows, `ingest_run_completion`
rows, landed claim breakdown, captures, rights decisions):
`gao_surveillance_reports.json`, `dhs_oig_reports.json`,
`dhs_fusion_center_assessments.json`,
`uk_surveillance_camera_commissioner.json` in this directory.

## Jobs + schedulers (created — only the four new jobs)

`scheduled-ops.sh` was **not** re-applied over the existing fleet (ADR-111).
Four `sig-ingest-<id>` jobs were deployed on the pinned digest with the
restricted-bucket gcsfuse capture store mounted at `/mnt/captures`
(`SIG_CAPTURE_DIR=/mnt/captures/evidence/captures`, `SIG_CODE_COMMIT` = the
deployed digest), Cloud SQL `sig-pg` socket, `sig-pg-password` from Secret
Manager, `--max-retries 0`, `--task-timeout 60m`, gen2 — the exact per-source
block of `scheduled-ops.sh`. Each job got `run.invoker` for
`sig-scheduler@…` and a `sig-sched-<id>` Cloud Scheduler trigger on its
`ops/cadence.toml` cron (`9 6 14/15/16/17 * *` UTC, monthly day 14–17).

## Executions (all `sig-ops scheduled-ingest --source <id> --sink pg`)

| source | first execution | ops/runs row (UTC) | claims landed | re-run (+0) |
|---|---|---|---|---|
| `gao_surveillance_reports` | `sig-ingest-gao-surveillance-reports-ll6d8` | 2026-09-26T03-31-06 | 8 claims (5 literal + 3 entity_ref); 10 records emitted | `…-9plqg` → completion `inserted 0 / duplicate 8` |
| `dhs_oig_reports` | `sig-ingest-dhs-oig-reports-g6w6g` | 2026-09-26T03-34-27 | 5 (4 literal + 1 ref); 7 records | `…-9dkg7` → `inserted 0 / duplicate 5` |
| `dhs_fusion_center_assessments` | `sig-ingest-dhs-fusion-center-assessments-tvnh6` | 2026-09-26T03-35-41 | 6 (4 literal + 2 refs); 8 records | `…-v87mw` → `inserted 0 / duplicate 6` |
| `uk_surveillance_camera_commissioner` | `sig-ingest-uk-surveillance-camera-commissioner-2z6z6` | 2026-09-26T03-39-41 | 6 (5 literal + 1 ref); 8 records | `…-8p76h` → `inserted 0 / duplicate 6` |

All eight executions: `outcome: ok`, `exit_code: 0`, `mode: live`, `fetches: 1`,
one OCFL capture each (digests in the per-source JSON), robots decisions
recorded (`retrieved`, 200) for `www.gao.gov` / `www.oig.dhs.gov` /
`www.dhs.gov` / `www.gov.uk` — GL-GATE-08.

**GAO egress note (honest):** `www.gao.gov` answers this workstation's
programmatic egress with a NetScaler WAF 403 (recorded 2026-09-25), so the
committed fixture is a Wayback capture — but Cloud Run egress fetched the
reviewed page cleanly (robots.txt 200, product page captured, all reviewed
literals verified — no drift). The access posture is vantage-dependent and
recorded, never defeated (SIG-INGEST-013, GL-GATE-08).

**Event linkage:** `event_organizations` entity-refs minted
`sig.org.name:` organisations (GAO, FBI, DEA, DHS ×2 sources deduped to one
entity, National Network of Fusion Centers, Home Office); the role-shaped
"Biometrics and Surveillance Camera Commissioner" stayed a verbatim text claim
(Part VIII partner-identity refusal — proven hosted). Each event subject is a
`deployment`-placeholder-typed entity carrying the §11.17 predicate surface.

## Rights (ADR-095 — append-only)

`sig-db rights-decisions --decisions docs/build/reports/rights/p293_dispositions.json
--apply` over the Cloud SQL proxy appended **four** `rights_decision` rows
2026-09-26T03:58Z, one per source, resolving the shared UNDETERMINED record
`01a0a5fe-cb9d-…` → the reviewed `rights_record`s (3× `CC0-1.0`, 1×
`LicenseRef-OperatorAccepted-DBRight`). The other four resolutions in the
artifact (`fema_hsgp_allocations`, `ccops_*`) have no UNDETERMINED priors yet —
no decision rows were written for them (their claims land under P31.13).
Effective-licence read-back: every landed claim resolves through the
latest-decision lookup — gao 16 / oig 10 / fusion 12 / uk 12 claim-evidence
rows lifted.

## Materialization (sig-materialize job, `sig_materialize` role)

- `accountability` (`python -m inference materialize-accountability-links`):
  `sig-materialize-6z7k5` — 249,367 deployment anchors / 30,958
  accountability claims considered; **200 links derived, 0 inserted** (all
  pre-existing from P31.6). Honest zero: the six oversight-org entities the
  new events minted operate **no** deployment in the graph (verified: no
  `operator`/`camera_operator`/`deployed_by` claim points at them), so no
  `overseen_by` edge is derivable — the events carry the oversight
  relationship; linkage awaits a source that deploys under those orgs.
- `resolution` (`python -m reconcile materialize`): `sig-materialize-6fm4h`
  (~03:46→05:35Z on `db-custom-1-3840`) — `considered_pairs 1,966,015 /
  inserted 18 / skipped_existing 1,965,997 / skipped_unresolvable 0 /
  resolved 1,964,667 / unresolved 1,348 / superseded 0 / skipped_pinned 0`.
  The 18 appends are exactly the four new sources' event-level resolutions —
  decomposed by winning-claim source: gao 5 / uk 5 / fusion 4 / oig 4.
- **Re-runs (both on the P31.11-pinned `sig-materialize` image
  `sha256:102389ea…`, `--args` override, job template unchanged):**
  accountability `sig-materialize-tbb7f` (05:43:30→05:43:39Z, exit 0) —
  byte-identical summary (`links_derived 200 / inserted 0 /
  skipped_existing 200`): clean +0. Resolution `sig-materialize-wzzgx`
  (05:43:30→06:40:39Z, exit 0) — `considered_pairs 1,974,575 /
  inserted 8,560 / skipped_existing 1,966,015`: the +8,560 pair growth is
  the scheduled fleet land `dot_511_ia` (+13,805 claims at 04:02:26Z,
  between the two snapshots); **every inserted resolution traces
  winning_claim → ingest_run_id → `dot_511_ia` — zero inserts attributable
  to the P31.12 sources** (their pairs all `skipped_existing`). Honest +0
  per-input on a live spine; reported as the decomposition, never a bare 0.
