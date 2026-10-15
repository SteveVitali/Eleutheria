<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Post-`0.1.0` changes land here first, each entry naming its ticket and
requirement ids (G3 §9.4, SIG-REL-014). At each tag the heading becomes
`## [0.N.0] — tagged by the operator (see git show v0.N.0)` — the tag object
carries the true date, so no date is typed here — and the section ends with
"Production releases built from this range: …". A PR touching the
public-behaviour path set (`web/src/pages/**`, `web/src/layouts/**`,
`api/src/api/{routes,app,models}.py`,
`exports/src/exports/{release*,spine_export,manifest}.py`,
`ops/public_routes.toml`, `ops/disclosures.toml`, `policy/**`,
`ontology/src/**`) must add an entry here or carry a
`Changelog: none (<reason>)` commit trailer — the `docs` CI job enforces it
(`docs/build/tools/changelog_gate.py`).

### Added

- **Host-level opt-out register + affirmative rights-reservation refusal**
  (P36.1a; cites SIG-INGEST-046c, §26 rule 7 under SIG-INGEST-036) — the two
  E2-06 controls, exercised on fixtures only: a committed, append-only
  `connectors/data/opt_out_register.toml` (`sig.opt-out-register/1`)
  consulted by the shared `PoliteFetcher` **before every fetch — before the
  robots probe** — so a listed host receives zero egress, with
  `$SIG_OPT_OUT_REGISTER` applying an entry on the next run without a
  registry rebuild or redeploy; and `policy.crawler.detect_reservation`,
  which detects affirmative machine-readable rights reservations
  (`Content-Signal` directives such as `ai-train=no`, `TDM-Reservation`,
  `X-Robots-Tag: noai`/`noimageai`, and the page-level TDMRep/robots-meta
  EU DSM Article 4 forms) and refuses with the signals kept verbatim as
  evidence. The refusal lands on `policy.rights.RightsRecord` as a new
  additive `reservation` field — a *refused* state stored distinctly from
  `UNDETERMINED` (SIG-INGEST-046c) — and on the run report's `refusals`
  as a first-class disposition; `assert_loadable`, `live_gate_reasons`,
  the flip-ready verdict and the flip-metadata rule all refuse a reserved
  record. GL-GATE-08 is unchanged: a robots `Disallow` is not a
  reservation and still proceeds stamped `robots_disregarded`. No
  `ingestion_permitted` flip, no live fetch, no external contact.
- **Scheduler of record: `ops/cadence.toml` + `sig-ops live-diff`** (P35.1a;
  cites SIG-OPS-006, SIG-OPS-011; ADR-174) — Cloud Scheduler + the committed
  `ops/cadence.toml` become the repository-owned scheduler of record, and a
  new read-only `sig-ops live-diff` reconciles declaration against live
  production: Cloud Scheduler triggers (schedule/state/body), Cloud Run
  jobs and services (image digest, service account, env/secret wiring),
  undeclared live jobs (`[[manual_jobs]]` is the only legitimate
  trigger-less job), and bucket posture (UBLA, versioning, lifecycle,
  public access). `cadence --check` now lints cron syntax **and semantics**
  — simultaneous day-of-month/day-of-week restrictions (cron ORs them)
  refuse unless the row names its exception owner via
  `cron_or_semantics_ok`; `[[pins]]` enforce digest-pinned images with a
  required `reason` + `expiry` per exception (tags and expired pins are
  drift). `scheduled-ops.sh` reconciles triggers from cadence (paused
  maintenance rows stay declared-but-paused), stamps
  `SIG_OPS_CADENCE_SHA256`, publishes the declaration bundle to restricted
  GCS, and **reports** undeclared triggers rather than deleting them
  (P35.1b owns the deletion pass). The daily `sig-sched-live-diff` trigger
  and the paused `sig-sched-pg-logical-export` are declared; the GitHub
  Actions `reingest.yml` schedule is retired (manual `workflow_dispatch`
  stays inert). The scheduler apply leg queues in RETURN PASS (operator
  ADC + AR-3 window); the read-only live run already landed real evidence —
  28 findings, exit 1, never claimed as clean.
- **Post-DNS cut-over probe: `sig-ops post-cutover-probe`** (P35.67;
  cites SIG-OPS-006, SIG-OPS-011) — the read-only verification the
  operator's OP-09 nameserver switch must satisfy: a `sig.probe-run/1`
  record covering the Cloudflare NS pair, the grey-cloud apex/www A
  records, DNSSEC (`ad` + RRSIG + parent DS rollover), TLS SAN + dates,
  the `sig-web-cert` managed `ACTIVE` status, both redirects, the public
  route sweep (sitemap locs with the `ops/public_routes.toml` allowlist
  fallback), the two-state mail posture, and registrar-lock drift.
  `--capture`/`--from-capture` preserve and replay raw outputs; every
  emitted command is a read-only dig/curl/openssl/gcloud/whois call —
  no mutating argv is reachable (pinned in tests). Both live legs queue
  in RETURN PASS: L1 waits on OP-09 (dig still answers Squarespace at
  dispatch), L2 is the cert-renewal read ≈ 2026-11-22. The committed
  checklist maps each check to the `DNS_CUTOVER_RUNBOOK.md` step it
  discharges (`docs/build/reports/POST_CUTOVER_PROBE_CHECKLIST.md`).
- **Zero-egress distribution host: the R2 public mirror leg** (P35.5;
  cites SIG-TRANSP-019, D-J3-4/A-3) — release downloads gain a
  zero-egress Cloudflare R2 mirror so egress cost cannot scale with
  traffic; GCS stays the origin of record. `ops/mirrors.toml` carries the
  committed-**disabled** `r2-public` row (enabled by the live leg after
  the operator's OP-09 nameserver switch + the GATE-G4 OM-20 listing —
  queued in RETURN PASS with the ticket's re-run prompt).
  `exports.push` gains fail-closed `PushLimits` (per-file 512 MiB,
  per-run object/byte caps, a request-rate guard that refuses an
  over-rate run, optional pacing) and `assert_non_listable_origin` — a
  push run never truncates, and an origin that answers an anonymous
  listing refuses. The publish path takes the leg: `sig-ops publish-web
  --mirror <row>` runs `assert_low_egress` inside the preflight (a
  disabled row, a metered provider, a breached cap, or an egress ALARM
  all refuse before any write), and `sig-ops mirror-push` is the
  standalone verb. The $50/month hard ceiling lands in
  `ops/config.toml` `[egress] hard_ceiling_usd` — `sig-ops egress-report
  --usage-usd` warns at 80% ($40) and alarms at 100% ($50) through the
  P34.4 recorded-alert seam; the documented kill switch (disable the CDN
  route / R2 public access — an operator step, never an agent action)
  lives in `docs/build/reports/R2_MIRROR_RUNBOOK.md`.
- **API release parity: release-backed routes serve the promoted
  release's verified files** (P35.57; cites SIG-REL-010) — the routes
  whose answers the site shows (`/v1/dossier/**`, `/v1/coverage/**`,
  `/v1/export`, `/v1/changes`, `/v1/sources`, `/v1/releases/**`)
  answer byte-for-byte from the current promoted release's
  `sig.api-slice/1` document set, digest-pinned to the release integrity
  manifest, with `?release=<publication_id>` selecting any promoted
  release. Responses carry `X-SIG-Basis: release`,
  `X-SIG-Release: <label> <publication_id>` and a body-level `basis` /
  `release` identity block; routes still answered from the claim spine
  now disclose `X-SIG-Basis: live-spine` plus `basis.spine_watermark` and
  `basis.latest_release`. Release failures are fail-closed typed errors
  (`unknown_publication`, `scope_not_available`, `withdrawn`,
  `release_artifact_absent`, `release_artifact_unpinned`,
  `release_verification_failed`, `release_metadata_mismatch`,
  `no_current_release`, `release_serving_unconfigured`), never silent
  fallbacks. `/` and `/v1/health` name the current release, code commit
  and image digest; `--release-registry` also reads
  `SIG_RELEASE_REGISTRY`. Release promotion gains the V7 api-parity
  preflight — a release the API cannot serve is refused; pre-slice
  releases are recorded `deferred` (obligation `D-P35.57-1`).
- **Withdrawal-barrier bytes: real tombstones on every alias** (P34.41;
  cites SIG-REL-013 (owner P35.55), SIG-FIND-001/002, SIG-GOV-007;
  ADR-132) — the generated deny map now denies **every alias** of a
  withdrawn route (`/<route>`, `/<route>/`, `/<route>/index.html` for
  page routes; the exact path for file routes such as the record's
  `.json` twin) with `error_page 410` onto that route's own
  `sig.tombstone/1` body staged under `conf/tombstone/` (an
  `internal`-only prefix in `ops/web/nginx.conf`) — the 410 answers the
  recorded tombstone (target kind/id, `withdrawn_at`, public-safe
  `reason_class`, `disposition_ref`, `superseded_by`, release label,
  corrections link; never an e-mail address), never nginx's generic
  page. `/entity/<t>/<id>/` convenience stubs are denied and rewritten
  to stub tombstones from the same deny set — entity-level denies,
  claim denies on the active release's record route, and the latest
  release's own namespace deny all reach the stub — and `page_index`
  pages embedding a denied id are denied and marked `withdrawn` in the
  index. `/r/<pub>/` now emits a real namespace landing page (with meta
  description) instead of a directory 403.
- **Release-archive chrome + same-origin link crawl** (P34.34a; cites
  SIG-FIND-001/002, SIG-UI-033, SIG-UI-024, SIG-LIC-011, SIG-UI-049) — every
  exports-rendered page now carries site navigation, a `/dispute/` link, and
  the licence of the data shown; `validate_release` and `activate` crawl
  every page's same-origin `href`/`action` and refuse unresolved links
  (withdrawal 410 tombstones resolve); `record_claims` rows and claim
  anchors carry the sparse `access_kind` field via the reconciler
  vocabulary; dossiers state their provisional computed posture and link
  from release landings; zero-record landings explain themselves as
  verified-empty publications; `build_spine_export` always emits
  `web/leverage.json` (the recorded changeset feed folded in, else the
  honest zeroed ledger — never a live fetch).
- **Versioning discipline + one version source** (P34.23, SIG-REL-014) —
  every package derives `__version__` via `importlib.metadata` (no `0.0.0`
  reported anywhere); `scripts/bump_version.py` bumps all 14 pyprojects and
  `web/package.json` together (dry-run default); `resolver_version` in
  export manifests is now the `resolution` package version + `+g<commit8>`
  instead of the exports placeholder; the CHANGELOG gate joins the `docs`
  CI job; `docs/build/reports/releases/` holds the operator tag procedure,
  `TAG_TEMPLATE.md`, and the prepared `TAG_v0.1.0.md` (not tagged —
  operator action, OP-08).

### Changed

### Deprecated

### Removed

### Fixed

- **Archive link depth, zero-record validation, and the empty-tile build**
  (P34.34a) — record/evidence links in nested release routes are
  site-root-absolute (`/r/<pub>/…`), removing the depth-fragile `../../`
  forms by construction; `validate_release` no longer misreads a legitimate
  `indexed_records == 0` scope as missing (a zero-record release was
  unvalidatable); a zero-archive tile manifest no longer fails the web
  build — `/map/` states the absence honestly in export mode; and the
  journey verifier's browse needle was updated to the new link shape.
- **API honesty: scope, completeness, bytes, terms, basis, grants** (P34.25,
  S0 RI-02, SIG-SEC-011; extends SIG-REL-010) — `/v1/dossier/{scope}` and
  `/v1/coverage/{scope}` now answer a typed 404 `scope_not_available` for a
  scope the store does not hold (the arbitrary 25-subject dossier fallback is
  removed); coverage never reports `complete: true` with zero evaluated
  records; `bytes_available` is claimed only for public-tier captures recorded
  byte-bearing (`capture_classification = 'actual'`), with
  `bytes_unavailable_reason` disclosing why otherwise; the hand-seeded OKC
  fixture sources never appear in live PostgreSQL answers; `/terms` no longer
  names a nonexistent editorial board or counsel; every response carries the
  `X-SIG-Basis: live-spine` header and a `basis` body field; and the
  `sig_read_public` role is narrowed by the `public_read_allowlist` migration
  to exactly the published read surface.
- **Release-search states tell the truth** (P34.36; cites SIG-FIND-003,
  SIG-UI-040, SIG-UI-050; owns S1 F-154 at the fixture layer) — the
  released-corpus search's empty page now asserts only that no released
  record in the compartment matches (the "recorded absence" claim is
  removed); HTML clients get a real HTML error page for every error status
  (`format=html` or `Accept: text/html`, including a search-scoped 422 for
  malformed parameters) while JSON clients keep the `{detail, code}`
  contract; `eligible_records` and `excluded_records_by_reason` now count
  records the current policy withholds at access time (the `denied` hook
  carries the public-safe reason category; `indexed_records` stays the
  pinned index truth); the no-JS pager names the actual `limit`, drops the
  duplicated browse sentence, and humanises display labels while wire
  values stay raw; non-record compartments (`metadata`, `web`,
  `web_mixed`, `code`, `ontology`) answer 404 `compartment_not_searchable`
  instead of a readiness 503, and `build_release` fails closed if one ever
  carries `sites.jsonl`; a zero-record release reports completeness
  `not_evaluable` instead of `complete`.
- **The graph-quality suite: versioned check registry + ratchet engine +
  read-only probe** (P34.44a; owner SIG-CONF-003/SIG-CONF-006/
  SIG-CONF-007; cites SIG-CONF-009/SIG-CONF-013/SIG-ENG-042; ADR-154 →
  ADR-204) — `sig.quality-checks/1` (`exports/src/exports/data/
  quality_checks.toml`) declares the 27 checks GQ-01…GQ-27 with
  placement/mode/threshold/baseline/basis-class/fixing-row; only
  mechanical basis classes may gate; `sig-ops quality run --placement`
  evaluates the implemented M/R/P checks over a read-only spine session
  or a release dir and emits `sig.quality-report/1` + `sig.probe-run/1`
  with offered/evaluated counts — a 0-evaluated check fails and an
  unwired seam reports `not_evaluable`, never a pass; `diff_registry`
  enforces the ratchet on the ruleset itself (baselines move only toward
  thresholds, loosenings and mode weakenings need a cited new ADR, an
  `enforce` flip is legal only in the check's fixing row); `sig-ops
  quality gate` is the standalone V15 hook (a `not_evaluable` enforce
  check fails closed). The hosted baseline run and the nightly job are
  P34.44b's.
- **The quality suite measures production: the nightly probe job +
  measured baselines** (P34.44b; cites SIG-CONF-006/007 (owner
  P34.44a), SIG-CONF-009 (owner P35.34; the check here), SIG-CONF-013,
  SIG-OPS-006; ADR-154/202/204 → ADR-205) — `ops/quality_probe.toml`
  declares the permanent `sig-quality-probe` Cloud Run job
  (`sig.quality-probe/1`: pinned digest, `sig-quality-probe-rt`,
  `sig_audit`, one task, zero retries, the two declared secret envs) and
  its `sig-sched-quality-probe` trigger firing `0 1 1-5,14-31 * *`
  Etc/UTC — 01:00Z off-peak, days 6–13 structurally unschedulable — and
  the in-container `sig-ops quality nightly` verb re-checks both
  suppression windows before connecting, recording a `suppressed`
  `sig.probe-run/1` instead of running. Every run writes
  `sig.quality-report/1` + `sig.probe-run/1` as new timestamped objects
  under the conditioned `ops/probes/` scope; a failed run records an
  error probe-run and alerts through the ADR-077 ledger + `sig-alerts`
  channel. `sig-ops quality baseline` is the read-only L2 baseline leg
  (the M checks over the hosted spine + the R checks over the fetched
  release files) emitting `sig.quality-baseline/1`; `sig-exports quality
  apply-baselines` is the only writer of measured baselines — it
  recomputes the proposal from the record, stamps the additive
  `baseline_run`/`baseline_at` provenance pair (`date -u`), and re-diffs
  the result so a loosening is never written. The hosted leg is queued
  on the `live:P34.43` `sig_audit` login (exit 42, recorded).
- **Honest evaluation posture: basis classes, review-only inferential
  tiers, and the one-shot v3-interim ER re-run leg** (P34.45; owner
  SIG-CONF-001/SIG-CONF-005; cites SIG-EVAL-001/004/006, SIG-CONF-012,
  SIG-REL-010; ADR-152/153 → ADR-206) — estimands and evidence now
  carry a basis class (`human`/`agent`/`llm`/`synthetic`/`mixed`/
  `unknown`/`none`), human estimands measure only on
  `reference_provenance='human'` evidence, and agent/LLM/synthetic rows
  stay visible under their own basis — never fabricated into human
  evidence. The committed camera-site gold is relabelled `agent` (it was
  never human-labelled), and the v3-interim ruleset marks tiers 3–5
  inferential: their decisions demote to review-only
  (`no_certifying_evaluation`) absent a B5-certified evaluation, with
  GQ-24's enforce lock refusing a completed run that carries an
  uncertified inferential auto-write while disclosing historical ones on
  the append-only spine; GQ-27 enforces one basis class per published
  quality statement and refuses `verified`/`human`/`independent` under a
  non-human basis. `scripts/eval/run_honest_eval_posture.py` emits the
  posture report (every human estimand `unavailable` / `basis=agent` /
  `no_human_reference`). `db`'s `er_rerun_login` change adds
  `sig_materialize_login` — a distinct LOGIN member of the existing
  NOLOGIN `sig_materialize` group, append-only INSERT surface,
  UPDATE/DELETE/TRUNCATE refused, no claim-spine write — and
  `ops/gcp/er-rerun.sh` runs the pre-authorised one-shot leg: `--check`
  plan-only, `--apply` window-/author-/dependency-/backup-/
  exactly-once-gated (a prior `ruleset_version='3-interim'` run exits
  42), `--verify` read-only; rollback is forward-only. The hosted leg is
  queued on `live:P34.43` + the AR-3 window (exit 42, recorded).

### Security

- **Part VIII at-rest protective seal: counts-only screen + two-carrier
  deny set** (P34.49, TS-07; cites SIG-GOV-007, SIG-PUB-002, SIG-PUB-003,
  SIG-INGEST-045e, SIG-GOV-008, SIG-STORE-011; ADR-185 → ADR-203) — the
  evidence store gains a deterministic at-rest audit: committed
  field-name/shape/scoped-pattern rules screen every stored capture for
  the three F-406 byte classes, the nine I7 S1–S9 lane screens and the
  five SIG-PUB-002 never-publish categories, reporting **counts only** —
  a field name or value is never emitted. Flagged captures are
  protectively sealed (suppression, never deletion): an append-only
  `capture_seal` register (`seal_register` sqitch change; immutability
  trigger, no UPDATE/DELETE grant, the `capture_currently_sealed`
  latest-action helper, the INSERT-only `sig_seal_writer` role) plus a
  versioned `sig.seal-deny/1` deny set in the restricted bucket. The API
  evidence paths answer the SIG-EVID-010 sealed representation (existence
  + digest + claims only) for a currently-sealed capture whatever its
  stored tier, and `spine_export`'s evidence bindings drop every sealed
  capture with a fail-closed post-check and `sealed_bindings_*` counts.
  No byte is deleted or overwritten; true purge stays the operator's
  WV-11 action (ADR-181/189). Both live legs are queued exit 42 —
  nothing hosted ran.
- **Correction-intake + moderation hardening before any operational flip**
  (P34.37; cites SIG-FIND-006, SIG-FIND-008; C4 NEW-8/15/16/17/18/19/30,
  DR-C4-11/12) — the non-operational correction receiver and its curation
  moderation surface are made safe to operate: the PostgreSQL reviewer
  detail route serialises UUID/datetime values instead of 500ing; the
  operating gate additionally fails closed unless `[intake].owner` is set
  and `[intake].staffed = true` (an unowned, unstaffed receiver can never
  answer as operating); the abuse limiter keys on the edge-normalised
  client address via `[intake].trusted_proxy_hops` (a raw client-supplied
  `Forwarded`/`X-Forwarded-For` is never trusted on its own) and refused
  submissions no longer consume the allowance; demo curation tokens are
  refused whenever a DSN backs the service; the reporter status view shows
  the decided outcome, the approved public response and the
  correction/release link once published (new `intake_reporter_outcome`
  sqitch change — additive columns on `intake.report_public`, grants
  unchanged); a proposal's value shape is validated against its declared
  `object_type` at proposal time and re-checked against the resolved target
  type at bridge apply (`object_type_mismatch`); the intake form gains a
  viewport meta, a real category placeholder, contract-shaped deep-link
  prefill, and copy that no longer promises anonymous/one-click intake —
  the Round-11 public channel stays e-mail-only (WV-05/ADR-180), and
  `[intake].operational` remains `false` (B-8).

## [0.1.0] — unreleased (REL.1 marker skipped-by-operator; the current integration plan has no tag step — `docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md`)

First tagged snapshot of the Surveillance Infrastructure Graph (SIG): the complete
specification-driven build (Phases 0–18), the post-build capstone, reconciliation and
release-readiness chain (Phases 19–20), and the Phase-21 operationalization chain that runs the
system as composed local staging (Phases 21.1–21.9). Full detail:
[`docs/build/reports/RELEASE_NOTES_v0.1.0.md`](./docs/build/reports/RELEASE_NOTES_v0.1.0.md).

> **Post-Phase-21 chain (rows 67–198, dated history — see `docs/build/BUILD_INDEX.md`).** The chain
> continued through go-live and Round 10: the GCP deployment executed 2026-09-15
> (`docs/build/reports/GCP_DEPLOYMENT.md`, ADR-081); HG-01 was satisfied at an interim posture and
> HG-11 was granted 2026-09-27, so the public surface is **live at https://surveillancegraph.org**
> (launch record 2026-09-24; republish 2026-09-27 over a ~2.4M-claim spine — green-reviewed sources
> were fetched live); the national publish, hosted materialization, partner registries and the
> research-queue/records flows landed in P25–P31. **Round 10 (P32/P33)** added typed assertions +
> actual-capture bindings, the shared bitemporal contract, immutable `r/<publication>` release
> namespaces + compartmented FTS5 search, the coordinated workspace, durable anonymous intake
> (built; `operational=false` — answers `503 receiver_not_operating`), the three dossier packets
> (`mechanical_complete`, `review.status=not_run`), the shadow evaluator + preregistered human-eval
> campaign tooling (deferred spine — no human labels), the provisional-ruleset release candidate
> (**staging-only**; production exposure `D-R10-PUBLISH-1` remains OPEN), and the build-memory
> v2 projections/closeout machinery. GATE-ACCEPT signed 2026-09-28 accepting the register as
> presented: **36 owed obligations + `SIG-MEM-004`** remain — see `docs/tickets/DEFERRALS.md` and
> `docs/build/OPERATIONAL_READINESS.md` §(f).

> **Phase 21 — operationalization (local staging, no live sources).** SIG now runs as a composed
> system for one real jurisdiction (Oklahoma City), end-to-end, without fetching a live source: the
> `ingestion_permitted` gate stays fail-closed (HG-03 pending), so every connector run is
> fixture-backed replay/shadow. **No version bump:** this is staging, not live; go-public is gated on
> HG-01 + HG-11 (`docs/build/reports/PUBLICATION_CHECKLIST.md`), and the `0.2.0` "first public jurisdiction"
> cut-over is a later, human-gated decision. The chain (each a stacked PR):
>
> - **P21.1** (#56, ADR-063) — 27 rights-review packets + the registry `review-status`/flip rule; the 19-project Stage-0 outreach record. Nothing flipped (`loadable now: 0`).
> - **P21.2** (#58) — annotation-layer alignment tests; contradiction/coverage/task persistence ACCEPTED as compute-on-read under A5/HG-14 (shrunk, no new persistence).
> - **P21.3** (#59, ADR-065) — live connector wiring behind the gate: the `httpx` transport, the OCFL capture store, and `sig-connectors run --mode live|replay|shadow` (refuses a non-green live fetch, exit 3).
> - **P21.4** (#60, ADR-066) — runtime composition: `sig-ops up/status/down/seed` (`ops/docker-compose.yml`, PG18+PostGIS + API + static), the export-backed web data layer (`web/src/lib/data.ts`, `SIG_DATA_SOURCE=fixtures|export`), and `docs/build/tools/run_okc.sh` — the OKC dossier renders the 299-vs-190 contradiction from the export bytes (LD-V08 crossed).
> - **P21.5** (#61, ADR-067) — infrastructure: `sig-exports deposit` (Zenodo), `push` (object store/CDN, R2 with S3/CloudFront documented), `tiles` (real PMTiles), `.torrent` mirrors, `sig-ops egress-report`, and `sig-ops degraded` + the monthly keepalive (the $0-beyond-static posture). A1 ticked — no MapLibre island.
> - **P21.6** (#62, ADR-068) — the authenticated curation service (`sig-api serve-curation`, enabled only by `SIG_CURATION_ENABLED=1`, never on the public API) + the `/curate/**` progressively-enhanced web surface.
> - **P21.7** (#63, ADR-069) — contribution-back live: the MapRoulette client (dry-run without a key, sensitive tiers never pushed), the OSM changeset feed → `LeverageLedger`, the Organised Editing activity record, and opt-in aggregate-only onboarding timing.
> - **P21.8** (#64, ADR-070) — the first-class `data_driven` connector (release-as-unit-of-ingestion, per-agency aggregate rows only) and the coarse-international reference-capture path.
> - **P21.9** (#65, ADR-071) — the `pathways` connector (three per-family extractors) + the ADR-033-deferred layer-3/4 parser engines in `parsing/`, enforcing `procured` ≠ `deployed`; retires RISK-P17-03.

### Added
- **Domain model & ontology.** LinkML ontology + SKOS vocabularies + deterministic generators
  (`ontology/`); the append-only claim/evidence spine L0–L3 with RLS on PostgreSQL 18 + PostGIS
  (`db/`); the OCFL content-addressed evidence store (`evidence/`); EDTF temporal semantics, as-of
  functions, and PROV-O lineage.
- **Identity & resolution.** Jurisdiction/organization registries, deterministic and probabilistic
  entity resolution (`resolution/`), the deterministic `RESOLVE` engine and §29 reconciliation
  workflows (`reconcile/`), `Contradiction` as a first-class object, coverage/negative-space metrics
  and the research-task engine (`inference/`, `tasks/`).
- **Acquisition.** The eight-stage connector framework with rate-limit/robots, licence gate, replay
  and shadow mode (`connectors/`); twelve fixture-tested connectors (osm, atlas, flock_portal,
  audit_structural, accountability, procurement, records, france_belgium_procurement/records, and —
  added in Phase 21 — data_driven, coarse_international, pathways); the
  parsing stack (`parsing/`); the source registry with per-source rights records (fail-closed
  `ingestion_permitted` gate).
- **Delivery.** The read API with resolution envelope, as-of, dereferenceable IDs and `/changes`
  (`api/`) served over PostgreSQL; exports with per-compartment licence computation and the ODbL
  split (`exports/`); the zero-JS Astro web shell with dossier, static map, network explorer,
  watch/evidence, corrections and methodology surfaces (`web/`).
- **Governance & policy.** The executable crawler/licence/publication/threat policy package
  (`policy/`) and the prose governance/safety policies (`docs/governance/`).
- **Engineering.** uv workspace of 14 members (SIG-ENG-011/012); `make check` CI gate mirrored in
  `.github/workflows/ci.yml` (Python `python` job incl. `tests/db`; `web` job incl. e2e + a11y +
  licence + perf); PEP 751 `pylock.toml` export and CycloneDX SBOM targets.
- **Build memory & reconciliation.** `docs/build/` (planning ledger, build index, decision memo,
  coverage matrix over 671 requirement ids, capstone closure with the operator-signed 76-row
  ACCEPTED-deviations list, backlog, operational-readiness map, ticket-vs-spec reconciliation);
  Appendix F rebuilt to repository ADR numbering; ADR-001…062.
- **Release readiness (this ticket, P20.3).** `docs/build/tools/merge_dryrun.sh` (read-only merge
  dry-run), `docs/build/INTEGRATION_PLAN.md`, `docs/build/CI_STATUS.md`, version bump to `0.1.0`
  across all members, these release notes, `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`.

### Changed
- Spec reconciliation (P20.2): eight normative amendments (A1–A8) applied at `spec_src`; three
  requirement ids folded back (`SIG-UI-047`, `SIG-EVID-020`, `SIG-ENG-039`); spec id count 668 → 671.
- Capstone spine wiring (P19.4/P19.5): connector claims persist to PostgreSQL (`PgClaimSink`), the
  read API is served over PG (`PgReadStore`), entity resolution and the review queue run over PG, and
  the export gate honours `derivative_permitted`.

### Known limitations (conforming, tracked — refreshed 2026-09-28, P33.7)
- The `ingestion_permitted` gate stays **fail-closed per source**: green-reviewed sources are fetched
  live by the hosted scheduled jobs (the national publish's ~2.4M claims), while every source whose
  review record is not green still gets a refused `run --mode live` (exit 3). Sources left to review
  or unblock are the `D-SOURCES.*`/`D-JURIS.2-1`/`D-R10-SOURCES-1` rows of
  `docs/tickets/DEFERRALS.md`; publication gating is recorded in
  `docs/build/reports/PUBLICATION_CHECKLIST.md`.
- The Round-10 **provisional-policy release candidate is published to staging only**: production
  exposure (`D-R10-PUBLISH-1`), the hosted recovery/freeze (`D-R10-LIVE-1`) and the production
  candidate build (`D-P32.23a-1`) are open operator obligations. The public site currently serves the
  prior HG-11-signed national publish.
- The anonymous **correction receiver is built but not operating** (`[intake].operational=false`;
  `503 receiver_not_operating`; `D-P32.16-1`), and the independent **human-evaluation spine is
  deferred** (`D-R10-HUMAN-1`, `D-R6.1-EVAL` — no human labels exist; the evaluator runs shadow-only).
- Resolved since the capstone (Phase 21): `LD-V08` — the web now reads export bytes, not just
  committed fixtures, so the OKC dossier renders the contradiction from the export (P21.4); PG
  persistence of contradiction/coverage/task objects is ACCEPTED as compute-on-read under A5/HG-14
  (P21.2); the web curation surface shipped (A6 → P21.6). The `/map/` surface later gained an
  **opt-in MapLibre + PMTiles island** (P27.9, ADR-097; per-island budgets ADR-134/P32.15) — all
  other public content pages remain zero-JS.
- Deferred human-gated steps (not defects): the moderated onboarding usability study is landed but
  **not yet run** (HG-10 / `D-R10-USERS-1`); Zenodo/live-mirror deposits and live MapRoulette pushes
  refuse until their gates are ticked (HG-07/HG-08; `D-P21.5-1`, `D-P21.7-1`). All owed work is
  tracked in `docs/tickets/DEFERRALS.md` (36 rows + `SIG-MEM-004`) and `docs/build/BACKLOG.csv`.

[0.1.0]: https://github.com/SteveVitali/Eleutheria/releases/tag/v0.1.0
