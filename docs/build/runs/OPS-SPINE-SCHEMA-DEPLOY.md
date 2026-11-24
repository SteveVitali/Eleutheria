# OPS-SPINE-SCHEMA-DEPLOY — hosted-spine sqitch deploy leg (post-gate unblock)

- **Leg:** deploy the committed append-only sqitch chain to production
  `sig-pg` (Cloud SQL `zeta-medley-508121-u7:us-central1:sig-pg`,
  POSTGRES_18, db-custom-2-7680, RUNNABLE) under the operator-signed
  GATE DECISIONS row **2026-11-20T18:20Z** ("Authorize sqitch deploy",
  record commit `ddaa969e` on `r11/P38.3c-round11-integration-plan-2`):
  production DDL, sqitch `deploy` only — never `revert`; verify the full
  plan lands and record the deployed change list. The deploy serves the
  blocked export leg (`export.sh --apply run` crashed on missing
  `claim_evidence.bound_at`) and the queued Wave-C L3 ingest path.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch:** `r11/ops-spine-schema-deploy` @ `ddaa969ec857` (worktree
  `/private/tmp/sig-schema-deploy`)
- **Window:** `date -u` 2026-11-20T18:10Z → 2026-11-20T18:16Z

## Result — FAILED CLEAN, fully reverted to prestate

`sqitch deploy --verify` applied **19** changes, then failed on change
**20 (`closed_vocabulary`)**: its verify script raised
`psql:verify/closed_vocabulary.sql:31: ERROR: division by zero`. Sqitch's
default failure handling reverted **all 19** changes deployed in this
run back to the pre-deploy head `camera_site_human_decisions` (every
revert `ok`), and reverted `closed_vocabulary` itself.

**Poststate = prestate, byte-identical at the catalog level:** 39
deployed changes, head `camera_site_human_decisions`
(committed 2026-09-25 23:24:43+00), `claim_evidence.bound_at` still
absent. The only residue is sqitch's own append-only audit trail —
39 `sqitch.events` rows (19 `deploy` + 1 `fail` + 19 `revert`,
18:11:46Z–18:15:44Z) recording the attempt. No deployed change survives;
no partial-deploy state exists.

Per the leg's rules the worker **stopped at the first failure** — no
improvised migration fix, no retry, no `--no-verify` bypass.

## Mechanism (as run)

- `cloud-sql-proxy zeta-medley-508121-u7:us-central1:sig-pg
  --address 127.0.0.1 --port 5433` (ADC in shell), matching
  `materialize.sh`'s `SIG_PROXY_PORT` convention.
- `docker run --rm -e SQITCH_PASSWORD -e "PGOPTIONS=-c
  lock_timeout=1200000" -v <repo>/db:/repo:ro -w /repo
  sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3
  deploy --verify db:pg://sig@host.docker.internal:5433/sig`
  — the `do_schema()` command from `ops/gcp/materialize.sh` verbatim
  except two recorded deltas: `-e PGOPTIONS=-c lock_timeout=1200000`
  (the rehearsed FEA-07 20-minute bound, per
  `docs/build/reports/p34.24b-l44-52-rehearsal/REHEARSAL.md` — the
  script's docker invocation does not pass it) and `:ro` on the `db/`
  mount (the rehearsal's posture; the deploy writes nothing into `/repo`).
- `SQITCH_PASSWORD` pulled from Secret Manager
  (`sig-pg-password`, `gcloud secrets versions access latest`) into env
  only — never on a command line, never in a file. Probe queries used
  `PGPASSWORD` env + the image's bundled `psql` the same way.
- Instance verified RUNNABLE via
  `gcloud sql instances describe sig-pg --project zeta-medley-508121-u7`
  before the proxy started.

## PRESTATE (recorded before any mutation)

- `sqitch status`: head `camera_site_human_decisions`
  (`c748bc5b3ab8e70853427ca0ee17429e01f8992b`, deployed
  2026-09-25 23:24:43+00 by `sqitch <sqitch@bf4546dd4705>`);
  **41 undeployed changes** pending to plan tip `organization_cascade`
  (matches the export worker's "~40 pending" finding).
- `sqitch.changes` count: **39**. `db/sqitch.plan` sha256
  `697884bc0a33202d34227b18dd51278a0eddd6996143be2a3a97ac0742db3589`.
- Probe `SELECT 1 FROM information_schema.columns WHERE
  table_name='claim_evidence' AND column_name='bound_at'` → **0 rows**
  (the missing column that crashed the export leg — confirmed absent).

## The deploy attempt (18:11:19Z → 18:15:55Z, exit 2)

Deployed `ok` (deploy + verify), in order — **all 19 reverted `ok`
after the failure**:

1. `claim_assertion_bindings` · 2. `partner_org_scoped_identity_key` ·
3. `shared_temporal_contract` · 4. `publication_dispositions` ·
5. `human_eval_campaign` · 6. `disposition_decided_at_authority` ·
7. `intake_storage` · 8. `intake_application_bridge` ·
9. `recovery_apply @r11-sqitch-hygiene` · 10. `shared_temporal_contract`
· 11. `public_read_allowlist @r11-read-allowlist` ·
12. `read_surface_grants` · 13. `review_campaign` ·
14. `intake_reporter_outcome` · 15. `audit_login` · 16. `seal_register`
· 17. `er_rerun_login @r11-verify-membership` · 18. `intake_storage`
(rework; NOTICE: `sig` already granted `sig_intake_receiver` +
`sig_intake_reviewer` membership by `cloudsqladmin` — the P34.46
verify-membership fix worked) · 19. `intake_application_bridge`
(rework; same NOTICE for `sig_intake_bridge`).

Then:

```text
  + closed_vocabulary .......................... psql:verify/closed_vocabulary.sql:31: ERROR:  division by zero
Verify script "verify/closed_vocabulary.sql" failed.
not ok
  - intake_application_bridge .................. Reverting to camera_site_human_decisions
… 19 reverts, all ok …
Deploy failed
```

Never reached (still pending — 22 changes): `entity_typing_mobility_check`,
`vocab_enforcement_count`, `vocab_geometry_defect`,
`coverage_exclusion_disclosure`, `claim_payload_version`,
`subject_rekey`, `declared_lineage`, `role_edges`, `vocab_published_by`,
`ingest_run_report`, `transparency_views`,
`ingest_run_report_upstream_recon`, `transparency_source`,
`capture_freshness_marks`, `claim_sightings`,
`camera_site_derivation`, `ingest_run_report_execution_key`,
`disappearance_event_grant`, `operator_purge`,
`research_task_predicates`, `organization_cascade` — plus the failed
`closed_vocabulary` itself (41 pending total, same as prestate).

## POSTSTATE probes

- `sqitch.changes` count **39**; head `camera_site_human_decisions` —
  identical to prestate.
- `claim_evidence.bound_at` probe → **0 rows** (still absent; the
  revert removed it).
- `sqitch.events` for the window: 19 deploy + 1 `fail`
  (`closed_vocabulary`, 18:15:25.532Z) + 19 revert rows — the
  append-only receipt of the attempt.
- Instance stayed RUNNABLE throughout; proxy log clean; no
  `lock_timeout` event occurred (no lock contention observed).

## Root cause (recorded, not fixed)

`db/verify/closed_vocabulary.sql:28-31` asserts **every** seeded
`vocab_predicate` row carries the full SIG-ONTO-066 registry metadata —
it divides by zero when any row has NULL `volatility_class`,
`resolution_strategy`, `definition`, `skos_concept_iri`, or a
non-IMMUTABLE `volatility_class` with NULL `half_life_days`.

On `sig-pg`, `vocab_predicate` holds **133 rows — all 133 with
`skos_concept_iri IS NULL`** (definition/volatility/strategy ARE
populated on the sampled rows; `iri_null` is the deficiency). These are
runtime-registered predicate rows predating the SIG-ONTO-066 metadata
requirement; the `closed_vocabulary` deploy's 280-row registry
projection is `INSERT … ON CONFLICT (predicate_id) DO NOTHING` —
insert-only, so it adds new predicates with full metadata but cannot
fill the NULL iri on pre-existing rows (no UPDATE, per append-only
discipline). On a fresh spine (testcontainers / CI) the only rows are
the change's own 280 full-metadata inserts, so the deficiency count is
0 and the verify passes.

**This is the same fresh-vs-existing-spine verify-defect class as
D-P34.24b-1** (the `intake_storage` `SET ROLE` failure the October
rehearsal found and P34.46 repaired via the `@r11-verify-membership`
rework tag — which itself worked correctly in this run). The fix is a
**new sqitch change** (never an in-place edit): either a recorded
metadata-backfill change covering the 133 registered predicates, or a
verify rework under a new tag scoping the completeness assert to the
rows the change owns — a design call for a proper ticket, not this leg.

Checked-forward (read-only, for the next attempt's benefit):

- None of the predicate ids later changes insert exist in production
  (`enforcement_count`, `geometry_defect`, `published_by`, and the six
  `closed_vocabulary`-asserted ids all absent → 0 rows), so the
  `vocab_enforcement_count` / `vocab_geometry_defect` /
  `vocab_published_by` `count(*)=1`-with-full-metadata asserts have no
  stub-row collision.
- Every other un-rehearsed pending verify asserts catalog shape
  (`pg_constraint`/`pg_trigger`/`to_regclass`/`has_*_privilege`) or runs
  rollback-guarded `DO`-block probes with empty-spine early-returns —
  `closed_vocabulary`'s data-completeness assert is the only located
  blocker of this class. A PITR-clone rehearsal (the P34.24b/P34.46
  procedure) before the next live attempt is still the recorded-safe
  path.

## Unblocked status

Nothing — the leg failed before the changes that matter landed.
`claim_assertion_bindings` (`claim_evidence.bound_at`) deployed and was
reverted; the export leg's `run`/`fetch` and Wave-C L3 ingest remain
blocked on a schema fix + re-deploy.

## Evidence (gitignored `docs/build/logs/ops-spine-schema-deploy/`)

| file | contents |
|---|---|
| `proxy.log` | cloud-sql-proxy startup (13:10:29 local / 18:10:29Z, ready) |
| `prestate-status.txt` | `sqitch status` — head + the 41 undeployed changes |
| `prestate-probe.txt` | 39 deployed changes, head, bound_at absent |
| `deploy-start.txt` | 2026-11-20T18:11:19Z |
| `deploy.log` | full `deploy --verify` output — 19 ok, verify failure, 19 reverts |
| `deploy-end.txt` | 2026-11-20T18:15:55Z |
| `poststate-probe.txt` | 39 deployed, head, bound_at still absent |
| `poststate-events-and-diagnostic.txt` | the 39 sqitch.events rows + the 133 NULL-iri predicate diagnostic |
| `poststate-predicate-collision-check.txt` | 0/8 forward predicate ids present; 133/133 null-iri totals |

## Deviations from the committed script

One env flag added to the verbatim `do_schema()` docker invocation:
`-e PGOPTIONS=-c lock_timeout=1200000` (the recorded FEA-07 bound from
the P34.24b rehearsal) and `:ro` on the `db/` mount (the rehearsal's
posture). No script, migration, or verify was edited; no gate-affecting
record was committed by this agent.

## Follow-up owed (recorded for the orchestrator)

The deploy remains outstanding: production needs a new append-only
sqitch change resolving the `closed_vocabulary` verify's
pre-existing-spine failure (backfill or scoped rework), then a
re-run of this leg under the same authorization scope — the P34.46
`@r11-verify-membership` tag is the precedent shape. A PITR-clone
rehearsal of `closed_vocabulary`→tip before the next live attempt is
recommended (it would have caught this class the same way D-P34.24b-1
was caught).

---

# ATTEMPT 2 — re-deploy, 2026-11-24 (SUCCESS — plan tip landed)

The fix landed as `1debdb6d` (`@r11-vocab-verify-scope` rework — the
metadata assert scoped to registry-seeded rows, `skos_concept_iri IS
NOT NULL`); this branch carries it via merge-forward `5e01c45d`. Same
authorization scope (GATE DECISIONS 2026-11-20T18:20Z, `ddaa969e`);
same mechanism; the prior ledger's two named prerequisites ran in
order.

- **Window:** `date -u` 2026-11-24T13:43Z → 2026-11-24T14:09Z
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch:** `r11/ops-spine-schema-deploy` @ `5e01c45d`

## Result — SUCCESS, plan tip landed

`sqitch deploy --verify` applied **all 42 pending changes** to
production `sig-pg`, every one `ok` — including both `closed_vocabulary`
occurrences (the tagged full projection at its plan position and the
no-op rework at tip). `sqitch status` post-deploy: **`Nothing to
deploy (up-to-date)`**, head `closed_vocabulary`
(`ce6faff91be8b3383396b80d29fdbd87269556ec`, committed
2026-11-24 14:06:08+00). `sqitch.changes` count **81** (39 prestate +
42 deployed — equals the plan's 81 change lines).
`claim_evidence.bound_at` **present** (`information_schema` probe →
1 row) — the export leg's crash cause is cleared.

## Step 1 — PITR-clone rehearsal (the P34.24b/P34.46 procedure, CLEAN)

Ran through `ops/gcp/restore-drill.sh --apply` (the sanctioned harness;
evidence dir redirected to
`docs/build/logs/ops-spine-schema-deploy/restore-drill/`):

- `prestate` — read-only capture, `pre-20261124T134318Z`.
- `clone` — window-guard OK (13:43Z, outside 03:00–10:00Z; no
  sig-materialize execution running); newest sig-pg backup
  `SUCCESSFUL`/`AUTOMATED`; latest `sig-probe` sweep **red exit 6** —
  the recorded stale-targets class (france/okc manifest, red since
  2026-09-27, per P34.4/P34.5/P34.6/P34.46 ledgers), judgment carried
  verbatim via `--probe-note`, not a new-class red. Clone issued as
  `sig-pg-drill-20261124t1343z` at point-in-time
  **2026-11-24T13:33:52Z**, op `f0bdd465-51ec-4a26-a9e4-d2dc00000032`
  DONE (CLONE), RUNNABLE.
- `rehearse` — full pending chain `closed_vocabulary`→tip (42 changes)
  deployed `--verify` on the clone over the **real 133 NULL-iri
  `vocab_predicate` rows**: deploy exit **0**, second `sqitch verify`
  exit **0**. The reworked assert passed — the pre-existing rows stay
  outside the registry-seeded scope by design. Per-change timings in
  `rehearsal/record.json`; max sampled `ACCESS EXCLUSIVE` on
  `claim_evidence` ≈ 21.0 s observed (well inside the 20-min FEA-07
  bound). Source `sig-pg` untouched (read-only snapshots only).
- `deleteclone sig-pg-drill-20261124t1343z` — name-checked delete;
  post-state `gcloud sql instances list` shows **no `sig-pg-drill-*`
  remains** (`sig-pg` only, RUNNABLE).

## Step 2 — live re-deploy (14:03:42Z → 14:06:08Z, exit 0)

Verbatim `do_schema()` from `ops/gcp/materialize.sh` plus the prior
leg's two recorded deltas — `-e PGOPTIONS=-c lock_timeout=1200000`
and `:ro` on the `db/` mount:

```text
cloud-sql-proxy zeta-medley-508121-u7:us-central1:sig-pg --address 127.0.0.1 --port 5433
docker run --rm -e SQITCH_PASSWORD -e "PGOPTIONS=-c lock_timeout=1200000" \
  -v <repo>/db:/repo:ro -w /repo \
  sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3 \
  deploy --verify db:pg://sig@host.docker.internal:5433/sig
```

`SQITCH_PASSWORD` from Secret Manager (`sig-pg-password`) into env
only — never argv, never a file. `DOCKER_DEFAULT_PLATFORM=linux/amd64`
on the arm64 host (emulated pull; recorded).

**PRESTATE** (14:02Z): head `camera_site_human_decisions`; 42
undeployed (the prior 41 + the rework `closed_vocabulary`);
`sqitch.changes` 39; `bound_at` absent; 133 NULL-iri predicate rows;
plan sha256 `6da4128c…6e88` (identical to the rehearsed clone's).

**Deployed (all 42, all `ok`):** claim_assertion_bindings ·
partner_org_scoped_identity_key · shared_temporal_contract ·
publication_dispositions · human_eval_campaign ·
disposition_decided_at_authority · intake_storage ·
intake_application_bridge · recovery_apply @r11-sqitch-hygiene ·
shared_temporal_contract (rework) · public_read_allowlist
@r11-read-allowlist · read_surface_grants (rework) · review_campaign
(rework) · intake_reporter_outcome · audit_login · seal_register ·
er_rerun_login @r11-verify-membership · intake_storage (rework) ·
intake_application_bridge (rework) · closed_vocabulary ·
entity_typing_mobility_check · vocab_enforcement_count ·
vocab_geometry_defect · coverage_exclusion_disclosure ·
claim_payload_version · subject_rekey · declared_lineage ·
role_edges · vocab_published_by · ingest_run_report ·
transparency_views · ingest_run_report_upstream_recon ·
transparency_source · capture_freshness_marks · claim_sightings ·
camera_site_derivation · ingest_run_report_execution_key ·
disappearance_event_grant · operator_purge ·
research_task_predicates · organization_cascade
@r11-vocab-verify-scope · closed_vocabulary (rework).

Benign NOTICEs only: `sig` already granted the eval/intake role
memberships by `cloudsqladmin` (the P34.46 verify-membership fix,
idempotent re-grant) and one `DROP TRIGGER … skipping` in
`ingest_run_report` (guarded drop of a not-yet-existing trigger).

**POSTSTATE** (14:06Z): `sqitch.changes` **81**, head
`closed_vocabulary` tip (`ce6faff9`, 14:06:08Z); `sqitch status`
→ `Nothing to deploy (up-to-date)`; `bound_at` present; the 133
pre-existing NULL-iri `vocab_predicate` rows retained verbatim
(honest runtime state — correcting them stays queued hosted work);
150 registry-seeded rows carry IRIs; 42 `deploy` events
(14:03:42→14:06:08Z) in `sqitch.events`; instance RUNNABLE; proxy
stopped; no lock_timeout event observed.

## Unblocked status

- **Export leg resume path is CLEAR** — `claim_evidence.bound_at`
  (plus `extractor_version`/`extraction_config_digest`/
  `binding_status`, `claim.assertion_map_*`, `evidence_capture.
  capture_classification`, `assertion_quarantine`) is deployed; the
  `export.sh --apply run` crash cause no longer exists.
- **Wave-C L3 ingest path** — the typed-assertion surface
  (`claim_assertion_bindings`), subject-key pins + rekey log
  (`subject_rekey`), declared lineage (`declared_lineage`), role
  edges (`role_edges`) and the transparency views
  (`transparency_views`/`transparency_source`/`claim_sightings`) are
  live.
- `operator_purge` DDL landed (the role `sig_purge_operator` exists
  with no member — by design; each use is still the operator's
  in-ticket go under ADR-189/WV-11, never agent-run).

## Evidence (gitignored `docs/build/logs/ops-spine-schema-deploy/`)

| file | contents |
|---|---|
| `restore-drill/pre-20261124T134318Z/` | prestate instance/backup/probe/op captures + sha256s |
| `restore-drill/drill-20261124T134352Z/meta.env`, `clone.json` | clone identity + point-in-time receipt |
| `restore-drill/drill-20261124T134352Z/rehearsal/` | the full `sig.sqitch-rehearsal/1` bundle: `record.json` (deploy exit 0, verify exit 0), `deploy.stamped.log`, `samples.jsonl`, `head/post/source*.json`, `operations-*.json`, `plan-hashes.json`, `verify.log/json` |
| `proxy.log` | live-leg cloud-sql-proxy (ready 14:02:30Z; SIGTERM 14:06:41Z) |
| `prestate-status.txt` | `sqitch status` — head + the 42 undeployed |
| `prestate-probe.txt` | 39 deployed, head, `bound_at` absent, 133 NULL-iri rows |
| `plan-sha256.txt` | `db/sqitch.plan` sha256 (rehearsal == live) |
| `deploy-start.txt` / `deploy-end.txt` | 14:02:52Z / 14:06:17Z markers |
| `deploy.log` | full live `deploy --verify` output — 42 `ok` |
| `poststate-status.txt` | `Nothing to deploy (up-to-date)`, head `closed_vocabulary` |
| `poststate-probe.txt` | 81 deployed, tip head, `bound_at` present, 133/150 predicate counts |
| `poststate-events.txt` | the 42 `sqitch.events` deploy rows |

## Deviations from the committed script (attempt 2)

Identical to attempt 1 plus the recorded platform note:
`-e PGOPTIONS=-c lock_timeout=1200000`, `:ro` on the `db/` mount,
`DOCKER_DEFAULT_PLATFORM=linux/amd64` (arm64 host). The rehearsal
ran through `restore-drill.sh` with `SIG_DRILL_EVIDENCE_DIR`
redirected under this leg's log root and a verbatim `--probe-note`
for the recorded red-probe class. No script, migration, or verify
edited; no gate-affecting record committed by this agent.
