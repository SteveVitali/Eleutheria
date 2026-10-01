# P31.13 hosted verification — BREADTH.2 (2026-09-26)

Live-verification evidence for the remaining four P29.3 rights-flipped
accountability-breadth sources — the three CCOPS jurisdictions plus FEMA
Homeland Security Grant Program allocations — run **only as Cloud Run jobs**
on the digest-pinned image `sig-api:ingest-26d5ceeeab74`
(`us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-api@sha256:63b809b2ab41b36df4d1fca33f4aa1a22953cf114639f27f0766b9c1245115b6`,
Cloud Build `00683e88-ad8e-4a4e-bb2d-013e4b2caec9`, built from `git archive
HEAD` @ `26d5cee` — never `:latest`).

Per-source JSON evidence (WORM `ops/runs` rows, `ingest_run_completion`
rows, landed-claim breakdown, captures, rights decisions):
`ccops_oakland.json`, `ccops_cambridge.json`, `ccops_somerville.json`,
`fema_hsgp_allocations.json` in this directory.

## Jobs + schedulers (created — only the four new jobs)

`scheduled-ops.sh` was **not** re-applied over the existing fleet (ADR-111).
Four `sig-ingest-<id>` jobs were deployed on the pinned digest with the
restricted-bucket gcsfuse capture store at `/mnt/captures`, the Cloud SQL
`sig-pg` socket, `sig-pg-password` from Secret Manager, `--max-retries 0`,
gen2. Each got `run.invoker` for `sig-scheduler@…` and a `sig-sched-<id>`
Cloud Scheduler trigger on its `ops/cadence.toml` cron (`9 6 18/19/20/21
* *` UTC, monthly days 18–21). A first scheduler pass mis-set the crons
(macOS Bash lacks `declare -A`); all four were explicitly corrected and
re-read from the live objects.

## Executions (all `sig-ops scheduled-ingest --source <id> --sink pg`)

| source | first execution | ops/runs row (UTC) | records → claims | re-run (+0) |
|---|---|---|---|---|
| `ccops_oakland` | `sig-ingest-ccops-oakland-4r84v` | 09-58-43 | 46 records → 27 claims; 9 fetches | `…-ppmqw` → completion `inserted 0 / duplicate 27` |
| `ccops_cambridge` | `sig-ingest-ccops-cambridge-8r87w` | 10-00-52 | 42 → 37; 2 fetches | `…-g4nmx` → `inserted 0 / duplicate 37` |
| `ccops_somerville` | `sig-ingest-ccops-somerville-jgpg6` | 10-03-57 | 72 → 57; 7 fetches | `…-qf89s` → `inserted 0 / duplicate 57` |
| `fema_hsgp_allocations` | `sig-ingest-fema-hsgp-allocations-x8zd6` | 10-06-39 | 4,060 → 3,658; 2 page fetches | `…-wz5sn` → `inserted 0 / duplicate 3,658` |

All eight `ok` executions: `outcome: ok`, `exit_code: 0`, `mode: live`,
0 refusals, 0 content drift; robots `retrieved` (200) on
`www.oaklandca.gov`, `cambridgema.iqm2.com`, `somervillema.legistar.com`,
`api.usaspending.gov` — GL-GATE-08. The run-record `claims_added` field
counts **emitted records**; `ingest_run_completion.claims_inserted` is the
authoritative land count (ADR-109).

**Duplicate-launch failures (honest):** two sources were re-run a second
time concurrently (`sig-ingest-ccops-somerville-7t2k4`,
`sig-ingest-fema-hsgp-allocations-79h9b`); the losers exited 1 with
`OSError: [Errno 116] Stale file handle` — a gcsfuse mount race on the
shared capture volume, `claims_added 0`, and each appended its own honest
`outcome: error` WORM row beside the winner's. No claims or evidence were
lost or duplicated by it.

## Landed surface (first run — measured)

- **CCOPS (27/37/57 claims):** `enacting_body` (9/1/1 — verbatim council
  name per filing), `ordinance_citation` (9/2/6 — OMC 9.64 / Cambridge
  2.128 / Somerville 10-66), `legal_authority` (Oakland 5), per-agency
  `technology` rows (4/26/5), and `disclosure_field_state`
  mandated-vs-populated claims (Cambridge 8, Somerville 45). Reporting
  periods ride inside each claim's aggregate subject identity
  (agency + period), never a separate predicate. All per-agency
  aggregate — no person/plate-level output.
- **FEMA (3,658 claims):** 200 assistance awards over the bounded 2-page
  97.067 slice — `award` claims (external/federal_award_id, amount,
  award_date, period, program_name, description, conditions,
  lifecycle_transition), `funder` text + candidate identifier, `recipient`
  text + candidate identifier + **340 entity-refs** (`sig.org.name:*`
  organisations minted through the ADR-112 identity guard), and the §11.12
  `FundingInstrument` claim sets (`instrument_type=federal_grant`,
  `federal_award_id`, `funder`, `recipient`) — emitted for all 200
  reviewed rows where funder + recipient + award id are all evidenced.
  **No deployment predicates, ever** — funding ≠ deployed.
- **Funder entity-ref refusal (honest):** `partner_identity` refuses
  "Federal Emergency Management Agency" as `generic_name` (every token is
  a generic/org word — the designed ambiguity rule), so the funder landed
  as text + `procurement.org_name` candidate id only. Recorded, not
  worked around — a ruleset review for federal agencies is a governance
  decision, not a code tweak.

## Rights (ADR-095 — append-only)

`sig-db rights-decisions --decisions
docs/build/reports/rights/p293_dispositions.json --apply` over the Cloud
SQL proxy appended **four** `rights_decision` rows (2026-09-26T10:16Z) —
`fema_hsgp_allocations` → `CC0-1.0`; `ccops_*` ×3 →
`LicenseRef-PublicRecord-FactualCompilation` — resolving the shared
UNDETERMINED record `01a0a5fe-cb9d-…`. The four P31.12 resolutions
returned `inserted: false` (idempotent on (source, prior, resolved) — no
duplicate decisions). Effective-licence read-back lifted
54/37/57/3,658 claim-evidence rows per source.

## Materialization (sig-materialize job, `sig_materialize` role)

- `accountability` (`python -m inference materialize-accountability-links`):
  `sig-materialize-bj9h9` (10:25:51→10:27:36Z, exit 0) —
  `deployments_considered 249,773 / claims_considered 33,003 /
  links_derived 200 / inserted 0 / skipped_existing 200 / by_link_type {}`
  — honest zero: the newly minted organisations (filing agencies, grant
  recipients) operate no deployment anchors in the graph, so no
  `overseen_by` edge is derivable; the disclosure/funding events carry
  the relationship without asserting operation.
- `resolution` (`python -m reconcile materialize`):
  `sig-materialize-nxmbh` (10:25:35→12:33:08Z, exit 0) —
  `considered_pairs 1,977,905 / inserted 20,047 / skipped_existing
  1,957,858 / resolved 1,976,555 / unresolved 1,350 / superseded
  16,717 / skipped_pinned 0 / skipped_unresolvable 0`. Decomposition by
  winning-claim lineage: **16,717 inserts trace to `dot_511_wa`** (the
  ADR-114 supersession path firing at scale — re-sighting digest drift
  closed the prior `auto` rows and re-decided them; 16,717 = the
  `superseded` count exactly) and **3,328 to this ticket's sources**
  (fema 3,318 / oakland 4 / cambridge 3 / somerville 3); 2 unattributed.
- **Re-runs:** accountability `sig-materialize-d2phk` (→12:39:52Z) —
  byte-identical summary, clean +0. Resolution `sig-materialize-4zk2k`
  (12:39→13:40:06Z) — `inserted 0 / skipped_existing 1,977,905 /
  superseded 0`: **literal +0**; every run-1 insert was a one-time
  append-only decision.
