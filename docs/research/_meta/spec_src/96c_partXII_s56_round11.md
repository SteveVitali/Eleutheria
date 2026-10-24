# Part XII — Round-11 build truth, operations, releases and confidence

## 56. Round-11 contract extension (2026-10-01)

### 56.1 Scope, precedence and execution authority

This additive extension records the new requirement families of the Round-11 plan, `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` (canonical; §6, with the themes of §5.2–§5.4, §5.8 and §5.11), which the operator ratified at GATE-P through the answers logged verbatim in `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md` (rounds 1–26, 2026-10-01T03:41:19Z–06:51:11Z). It defines future implementation obligations; it is not evidence that any of them is implemented, that any human check exists, or that any gate is signed. Part VIII protections, the frozen §47 layout, the insert-only claim spine (SIG-STORE-011 binds every path except the one operator-only purge function of ADR-189) and every earlier part remain binding. Nothing in this part weakens a MUST elsewhere.

Round 11 runs without independent humans and without contact outside the project (the operator's constraints U-008 and U-011; plan §3.4). A requirement that needs an independent person stays owed under its own trigger (T-EVAL-IND); agent or maintainer work is never relabelled to satisfy it. The waivers the operator adopted (ADR-153, ADR-163…165, ADR-179…182, ADR-186…189) are recorded as amendments in the sections that own the waived requirements and in Appendix G.7, not here: this part only adds requirements.

The draft ids of the planning notes (B4 §5 DRAFT-MEM/ENG/OPS; G1 §4; G3 §10 SIG-REL-D01…D14; L3 §7 SIG-CONF-D01…D14) map to the final ids below in `docs/build/planning/2026-09-30-next-phase/stageB/T1_id_map.csv`. A draft listed under two families is written once. A surviving draft keeps its ordinal (G3's SIG-REL-D04 is SIG-REL-004; G1's provisional SIG-OPS-004 stays SIG-OPS-004). **Id note:** the requirement ids SIG-OPS-nnn, SIG-REL-nnn and SIG-CONF-nnn are not the planning ticket keys OPS-01…08, REL-01…11 and CONF-01…14 (catalog ids `R11-OPS-*`, `R11-REL-*`, `R11-CONF-*`); a ticket key never names a requirement.

Each requirement names one implementing owner: a Round-11 chain row by its `data/round11_plan.csv` id, or a Stage-B seed unit (SEED-nn). Where the manifest (rows 201+) renames a row, the manifest is authoritative. "Also" names rows that extend the owner's work without owning the requirement. Operator decisions are quoted with the round time from the log; a text the operator adopted by selecting an agent-drafted option carries the label `agent-drafted, adopted by the operator at <time>` and the sha256 prefix computed in `design/S6-ratification-applied.md` §5.

### 56.2 Build-memory truth (extends §55.7)

In Round 10 the committed build memory (ADR-073) carried future-dated records, lost append-only history and readouts composed after one-line approvals, and every validator passed because each checked structure, not truth (plan §5.2; B1–B5). These requirements make the memory's truth mechanically checked (ADR-146, ADR-147, ADR-148).

**SIG-MEM-005 (MUST).** *Clock-true records.* Every date or time recorded as an event — in build memory, ADR headers, spec landed-status text, obligation events, `db/sqitch.plan`, release identities and product constants — MUST come from the system clock at the moment of recording (`date -u`), or from the git or GitHub time of the event with its source named; never from a "chain date" or an estimate. It MUST NOT be later than the commit that records it. A future date is allowed only for a scheduled, real-world, synthetic or illustrative value that carries an explicit future-ok class and reason, or an allow-list entry that expires; forecast text in the planning documents under `docs/build/planning/` is a plan, not a record. A recorded date found to be wrong is corrected only by an appended, dated correction that names what it corrects (ADR-146), never by rewriting the record or by a footer on a landed ADR; deployed migration-plan lines keep their stamped dates (SIG-ENG-045). CI MUST fail a change that adds a violating record. Owner: SEED-02 (guard core). Also: P34.8 (obligation-event clock defaults), P34.22a/b (code literals and fixtures).

**SIG-MEM-006 (MUST).** *Append-only, proven per change.* Protected build-memory regions, declared in a committed policy, MUST change only by appending at the region's end, by filling a declared placeholder, by an annotation that preserves the prior text, or — for a declared living region (the ledger head, OPERATING MODE, CURRENT STATE) — by replacement whose removed bytes are archived verbatim and hash-linked in the same commit. CI MUST check every pull request against its base and every push to `main` against its first parent. Lost append-only history is restored verbatim from git first and annotated afterwards by appended rows. Owner: P34.7. Also: SEED-02 (core modes), P34.27 (remaining restorations).

**SIG-MEM-007 (MUST).** *CI truth at every boundary.* Before closing a ticket and before dispatching the next, the orchestrator MUST read the head-bound GitHub check runs of the ticket's pull request at its current head and of every unmerged ancestor in the stack. A failing, cancelled, skipped, missing or unknown required check MUST set `blockedOn` and stop the chain until it is fixed or waived verbatim by the operator. "CI unavailable" is never green: it needs a verbatim, time-boxed operator waiver and a later sweep of the owed runs. Only an allow-listed flake gets one re-run per head. The recorded result (check names, conclusions, run ids, head sha) MUST be verifiable by CI against GitHub; a local-only result is recorded as `locally-green`. Each boundary MUST also record `main`'s head, whether the chain descends from it, and the merges since the previous boundary, read from GitHub. In Round 11 the check covers the `r11/` pull requests and their `r11/` ancestors; the reds of the earlier stack are merge-readiness items for the operator, not Round-11 blocks (B-15, "As stated (Recommended)", 2026-10-01T04:33:54Z). Owner: P34.2. Also: SEED-02 (the boundary reader).

**SIG-MEM-008 (MUST).** *Gate records.* Each gate decision MUST be recorded as a table row giving the `date -u` of receipt, the gate, the item, the operator's words verbatim (or `provided: yes/no` where the words would carry a secret), the consequence and its kind (decision, pre-authorization, confirmation, waiver or date-correction). A decision MUST be dated at or after its gate's pause, unless it is a pre-authorization that lists explicit item ids and an expiry. Nothing is pre-authorized on silence, and silence is never consent. Words that are interrogative, conditional, hedged or instructional MUST be followed by a recorded plain yes/no before any consequence is acted on — the forward rule the operator adopted with A-16 ("Key + forward rule (Recommended)", 2026-10-01T04:16:29Z). No record may delegate a signature or attestation to an agent. Owner: P34.28. Also: SEED-02 (table form and dates).

**SIG-MEM-009 (MUST).** *Readout authorship.* Every gate or human readout MUST contain, from creation and permanently, the sentence "An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval." A signed readout's decision MUST be the operator's verbatim words, identical to its gate record. Agent-written text MUST sit in labelled agent-drafted blocks whose sha256 the operator confirmed in words recorded verbatim; a text the operator adopts by selecting an agent-drafted option is recorded with its sha256 and the label `agent-drafted, adopted by the operator at <time>`. Signing MUST only change the status line and append a signature block. A past determination is recorded as what it was: a "counsel" determination for which no counsel existed is recorded as the operator's own determination (ADR-167). Owner: P34.28. Also: SEED-02 (the sentence in new readouts).

**SIG-MEM-010 (MUST).** *Ledger contract.* The control ledger's orient region MUST stay within a declared byte budget (12 KiB in Round 11). CURRENT STATE MUST hold single values from declared vocabularies, including the harness of the current segment. Every path named in the orient region MUST exist, and no deny-listed stale token may appear in it. PHASE LOG entries MUST be appended only at the end of the current round's section, in the fixed shape and size. BUILD_INDEX rows MUST be well formed and uniquely sequenced, with no placeholders after close. RETURN PASS MUST equal its generated form. Run ledgers MUST name the harness and model. A CI probe MUST show that the documented orient recipe resolves the next unit within its budget. Planning ledgers MUST keep CURRENT STATE consistent with their change logs. Owner: P34.9. Also: SEED-10 (the slim head), P34.29 (the RETURN PASS generator).

**SIG-MEM-011 (MUST).** *Status layers and live claims.* A statement of progress MUST name its layer — engineered, fixture-verified, staging-verified, live-executed, public or human-completed — and never report a lower layer as a higher one. A build-memory, readiness or README statement that asserts production state MUST cite a probe-run record (id, time, result, output digest) no older than 24 hours at its commit. The citation is what is checked; the truth rests on the probe (SIG-OPS-011). Owner: P35.3.

**SIG-MEM-012 (MUST).** *Harness attribution.* Round-11 commits keep the operator's name as author (A-21: the operator chose "Keep my name", 2026-10-01T04:25:48Z). Every agent commit MUST therefore carry a trailer naming its harness and model — a recognised harness co-author trailer, or `Harness: <harness>/<model-id>/<tier>` — and CI MUST fail a Round-11 pull request that contains an untrailered agent commit. An operator commit is identified by a valid operator signature (SIG-SEC-010) or `Harness: operator` and needs no harness trailer. One harness and model run each segment; a switch happens only at a boundary and is recorded in the PHASE LOG, and CURRENT STATE, run ledgers and contract headers name the segment's harness. Trailers are self-reported: they prove consistency, not origin. Owner: SEED-02 (trailer grammar). Also: P34.9 (ledger fields).

### 56.3 Engineering verification

**SIG-ENG-040 (MUST).** *Tests and validators assert invariants.* A test MUST NOT assert the current value of a living record: the next unit, the project status, a named obligation's, requirement's or readout's status, or the counts, row ranges or dates of living registers. Tests read living control records only through the validators or against an explicit snapshot commit, and assert only properties that hold at every commit (vocabulary membership, uniqueness, generated equals source, reference resolution, append-only properties) or facts about frozen artifacts. A validator MUST NOT pin a living count either: an expected count is derived from its source, such as the spec's requirement definitions. A failing pin is converted or deleted, never relaxed in place. A lint in `make check` MUST enforce this. Owner: P34.31. Also: SEED-03 (the seed's conversions).

**SIG-ENG-041 (MUST).** *Verdict integrity.* The coverage-matrix checker MUST enforce the verdict grammar — MET, MET-DIFFERENTLY(ADR|RISK), MET-ENGINEERED(D-id…), PARTIAL, MISSING, AT-RISK-INTEGRATION, WAIVED(ADR) and N/A-RATIONALE — with its parameters and the columns `required_domain`, `achieved_domain`, `owed_legs` and `accepted_scope`. It MUST cross-check each verdict against the obligation register and `accepted_scope`: no MET with an owed leg; MET-ENGINEERED only with open owed legs; WAIVED only with an accepted ADR that contains the id and a revisit trigger, and no open leg; a scoped acceptance never raises a verdict. The routing of an open verdict MUST name a ticket that has not landed, cited evidence MUST exist, expected counts MUST be derived from the spec rather than pinned, and every verdict change is written as a `coverage-assessment/1` event. A spec amendment that removes or weakens a MUST is a waiver, recorded as WAIVED(ADR) with the operator's words, compensating controls and a revisit trigger (ADR-150). An acceptance packet MUST report both sums — engineering closed (MET + MET-DIFFERENTLY + MET-ENGINEERED) and requirement satisfied (MET + MET-DIFFERENTLY) — and never "N MET" alone. Owner: SEED-15. Also: P34.33 (the capstone two-sum check).

**SIG-ENG-042 (MUST).** *Validator gates; no vacuous pass.* Every build-memory and spec validator MUST run in `make docs-check` and in the CI documentation job on every pull request and every push to `main`. Each validator and scheduled check MUST report how many items its input offers and how many it evaluated, and MUST fail when it evaluated none of a non-empty candidate set or when its parse rate falls below a declared floor. A scheduled job that measured nothing MUST NOT report success. Owner: P34.9. Also: SEED-02 (CI wiring).

**SIG-ENG-043 (MUST).** *Revisit triggers are monitored.* Every ADR revisit trigger MUST have exactly one register row with the hash of its trigger text, a state (quiet, fired-unanswered, fired-answered, superseded or dormant), evidence, an open home and a last-evaluated date. A fired trigger MUST have a recorded answer — a new ADR, a ticket or a waiver — before the round closes, and at the round tail every row is evaluated within the round. Owner: P34.32. Also: SEED-15 (the register file).

**SIG-ENG-044 (MUST).** *Guards precede the records they protect.* A round's seed MUST carry, before its first record commit, the guard core for the record classes it writes: record dates (SIG-MEM-005), append-only regions (SIG-MEM-006), the CI-boundary reader (SIG-MEM-007), the gate-table form (SIG-MEM-008), the readout sentence for new readouts (SIG-MEM-009), the trailer grammar (SIG-MEM-012) and the validator wiring (SIG-ENG-042), with the living-record test pins converted (SIG-ENG-040). The seed pull request MUST be green under them before the round's first gate (GATE-B in Round 11). The full readout rules (SIG-MEM-009) MUST land before the round's first readout is signed. A guard that cannot land first is replaced by an equivalent planning-side check until it lands, and the gap is recorded. The operator chose the full seed (A-13, "Full seed (Recommended)", and Q-B4-1, both 2026-10-01T04:09:43Z). Owner: SEED-02. Also: SEED-03 (pin conversions).

**SIG-ENG-045 (MUST).** *Migration lifecycle.* The whole sqitch plan MUST deploy, verify, revert and redeploy cleanly in CI on every pull request, into a fresh database created from `template0` (SIG-STORE-041). A plan line, once deployed to any database, MUST NOT be edited or re-stamped, because its planned time is part of its change id. A wrong date in the plan is corrected by an appended amendment (ADR-146), and a defective verify script by `sqitch tag` and `rework`, never by editing a deployed script. In particular, `db/sqitch.plan` lines 44–52 keep their stamped dates: a local database holds them as stamped (C-10; operator-approved local inspection, 2026-10-01T04:59:41Z). Owner: P34.24a.

**SIG-ENG-046 (MUST).** *Pinned toolchain.* The Node, npm and uv versions and the CI runner image MUST be pinned in the repository and identical in local and CI runs, checked by a CI assertion, and CI MUST fail when a dependency install would rewrite a lockfile; a lockfile regeneration is its own recorded change. Superseded pull-request runs MAY be cancelled; runs on pushes to `main` MUST NOT be. Owner: P34.1.

### 56.4 Operations (opens the `OPS` family)

The hosted deployment (ADR-081) had no restore drill at scale, no deletion protection, no alert path that reached a person, no scheduler of record and no least privilege (plan §5.8; G1). Operations requirements were carried under SIG-ENG-* in Part IX; §0.3 now opens `SIG-OPS-*` for them. The release model — identity, promotion, Class R and Class S, rollback and cadence — is the `REL` family (§56.6), not OPS. Production mutations follow the Round-11 operating clauses OM-14 and OM-20: named in a contract, scripted, with a restore point, and run only under the operator's go or an operator-approved pre-authorization list.

**SIG-OPS-001 (MUST).** *Restore drill and logical export.* The production claim spine MUST be restored from its managed backups (point-in-time and a full backup) into a new, isolated instance at least quarterly and after every schema-changing deploy. The drill MUST verify append-only row-count parity at the restore point for every spine table, MUST record the measured RTO and RPO, and MUST delete the drill instance afterwards by a name-checked command that cannot touch production. A drill against a seed or fixture database does not satisfy this requirement. A logical export of the production database MUST be stored outside the instance's lifecycle at least monthly. Owner: P34.6.

**SIG-OPS-002 (MUST).** *Instance survivability.* The production database instance MUST have deletion protection enabled, MUST retain its backups on instance deletion, MUST have a maintenance window outside the scheduled batch windows, and MUST have a storage autoresize cap at the value the operator set (B-11, "As stated (Recommended)", 2026-10-01T04:35:53Z). Owner: P34.3.

**SIG-OPS-003 (MUST).** *Public route allow-list.* The public web origin MUST serve only routes on a committed allow-list. The publish tooling MUST refuse to publish a build that contains an unlisted top-level route or a page built from internal or demo layouts. Each denied route MUST return 404 on every public origin, verified after every publish and every probe sweep. A surface the operator accepted as withdrawn rather than made to work stays off the list until it works (C-12, "Accept the list (Recommended)", 2026-10-01T05:03:05Z). Owner: P34.10.

**SIG-OPS-004 (MUST).** *Single publish path and release record.* The public site and the public compartments MUST be published only by the repository-owned publish command — the release tool of SIG-REL-004 once it exists. Hand-typed syncs to public buckets are prohibited, and no publish deletes a release tree. Every publish MUST write a release record (release id, git commit, image digests, digest of the published tree). The release id on every page is SIG-REL-009. Owner: P34.10.

**SIG-OPS-005 (MUST).** *Live-configuration reconciliation.* A read-only reconciler MUST compare the live scheduler, jobs, services, identities and bucket policies with their repository declarations (the cadence file, a manual-job allow-list and the declared posture) at least daily, and alert on drift. One scheduler of record runs every scheduled job. A cron schedule that restricts both day-of-month and day-of-week MUST be rejected unless explicitly annotated. Configuration MUST NOT require an image roll to take effect. Owner: P35.1a.

**SIG-OPS-006 (MUST).** *Alert delivery.* Every critical alert MUST reach a human channel — at minimum e-mail to the operator's address — within 1 hour. A condition red for more than 24 hours MUST re-notify daily. The operator MUST be notified of any failed scheduled execution. Probes MUST cover the canonical public origin through the load balancer, including TLS certificate expiry (alerted at least 21 days ahead), and not only platform URLs. A scheduled check that measured nothing fails (SIG-ENG-042). Owner: P35.2. Also: P34.4 (the first channel, uptime checks and the TLS-expiry alert).

**SIG-OPS-007 (SHOULD).** *Availability objectives.* The public site root and the API health endpoint SHOULD meet 99.5 % monthly availability, measured by external checks at intervals of 5 minutes or less, with a monthly error-budget readout. Owner: P35.2.

**SIG-OPS-008 (MUST).** *Read-model freshness.* While scheduled ingestion runs, materialized read models MUST be refreshed at least weekly, so that the live API lags the claim spine by at most seven days. The site's republish cadence and its triggers are SIG-REL-011; the site's as-of and its notice that the API may be newer are SIG-REL-009. Owner: P36.44.

**SIG-OPS-009 (MUST).** *Cost truth.* Measured monthly cost MUST be available (a billing export or equivalent) and compared against the operator-set ceiling with a budget alert. The ceiling covers infrastructure only; costs billed outside the cloud account (object hosting and CDN, registrar, domains) are read into the same monthly spend ledger. Agent usage is reported, not capped, and a usage-limit event pauses the round for the operator (A-2a, "Infra only; alert later", and A-2b, "Report + pause on limit (Recommended)", 2026-10-01T03:53:59Z). Documented cost claims MUST be measured, not projected; an estimate is labelled as one. Owner: P34.5.

**SIG-OPS-010 (SHOULD).** *Runbooks.* Hosted operations SHOULD have maintained runbooks, with commands verified against the tree, for alert response, restore, republish, scheduled-window watch, job failure, secret rotation, roll, cost review and decommissioning, plus the rollback and withdrawal procedures of SIG-REL-013. Owner: P35.4.

**SIG-OPS-011 (MUST).** *Probe placement and evidence.* Each production-truth probe — route allow-list and absence (SIG-OPS-003), release record and page stamp (SIG-OPS-004, SIG-REL-009), live-configuration drift (SIG-OPS-005), monitoring liveness (SIG-OPS-006), and the attribution, jurisdiction–coordinate, API-parity and number-truth probes — MUST declare its trigger points (pull request, release candidate, publish, schedule, round tail) and write a `probe-run/1` record (id, time, result, output digest). The round tail MUST include a full probe sweep. Owner: P35.3.

**SIG-OPS-012 (MUST).** *Fixture sentinels.* Release candidates, the public web build and sampled live API responses MUST be scanned for fixture and placeholder sentinels: test domains, placeholder IRIs, fixture and demo markers, loopback URLs, undisclosed stand-in captures and unregistered contact domains. A hit outside a declared fixture compartment fails the gate. Owner: P35.3.

**SIG-STORE-048 (MUST).** *Evidence immutability in hosting.* The hosted OCFL capture store and the ops run and probe records MUST be protected against overwrite and deletion by a bucket retention policy, or by object versioning with noncurrent retention of at least 90 days. The capture store's retention is 365 days and stays unlocked, so that lawful takedowns and the operator-only deletion path (ADR-181, ADR-189) remain possible (B-14, "Accept all three (Recommended)", 2026-10-01T04:39:45Z). Runtime identities that write captures MUST NOT hold object-delete. No document may call a store WORM unless such a control is in force. Owner: P37.3. Also: P34.3 (versioning and noncurrent lifecycle).

### 56.5 Security posture

SIG-SEC-001…006 (§44) stand. SIG-SEC-003's Round-11 amendment (a written demand-response posture, published legal-demand counts, the warrant canary declined; ADR-166) is recorded in §44 and Appendix G.7, not here.

**SIG-SEC-007 (MUST).** *Least-privilege runtime identities.* No service or job may run as a principal holding a basic project role (Owner, Editor or Viewer). Each workload class MUST have a dedicated service account with only the roles it needs, and each secret is readable only by its consumers. Public-facing workloads MUST NOT hold delete permissions on the spine or evidence stores. Owner: P34.42a/b.

**SIG-SEC-008 (MUST).** *Digest pinning everywhere.* Every service and job MUST reference its image by digest (extending ADR-111 from jobs to services), and deployed code MUST be reproducible from the repository. Owner: P35.1a/b.

**SIG-SEC-009 (SHOULD).** *Secret lifecycle.* Each secret SHOULD have a recorded owner, consumer and last-rotation date. A secret known to be exposed MUST be rotated before its first production use. Secret values live only in the secret manager, never in files (SIG-SEC-006). Owner: P35.4.

**SIG-SEC-010 (MUST).** *Operator-only gate signatures.* Gate signatures — HG gate decisions, Class S release gos, and every source flip from `ingestion_permitted = false` to `true` — MUST be made in commits or records signed with an operator-only key that is passphrase- or hardware-backed and never loaded where an agent session can reach it (no agent-reachable ssh-agent or credential store). CI MUST verify those signatures against a committed `allowed_signers` file, and MUST fail a gate signature, a Class S go or an `ingestion_permitted` false-to-true transition that no operator-signed commit or GATE DECISIONS record covers. The key proves origin; it never signs release manifests (SIG-REL-015). The operator adopted this control with A-16 ("Key + forward rule (Recommended)", 2026-10-01T04:16:29Z). Owner: P34.28 (the operator creates the key, OP-25).

**SIG-SEC-011 (MUST).** *Public read role by explicit grant.* The public API's database role MUST read only the published read surface (§37), through explicit column lists or views granted by a sqitch change. It MUST NOT hold a blanket SELECT that reaches internal tables such as the evidence access log, review decisions, run environments or unscreened evidence excerpts. A database test MUST allow-list exactly what the role can read. Owner: P34.25.

### 56.6 Releases (opens the `REL` family)

The live release id was neither content-addressed nor belief-pinned, versions read `0.0.0`, a web redeploy could erase release trees, and live serving could not honour withdrawals (plan §5.8; G3). The operator adopted G3's release model with its Class R standing go (B-9, "Adopt + standing go (Recommended)") and its versioning and legacy-bucket answers (B-10, "Yes (Recommended)"), both 2026-10-01T04:35:53Z, and the manifest-signing split (B-20, "Pipeline key + your gate key (Recommended)", 2026-10-01T04:41:11Z). The model's engineering ADR is written by its owning row.

**SIG-REL-001 (MUST).** *Release identity.* Every production release MUST have a content-addressed publication id (`p-` followed by the sha256 of its canonical descriptor) and an immutable human label `sig-YYYY-MM-DD.N`: the UTC date of the data as-of plus an ordinal per date, allocated under a lock and never reused. A label that was never promoted is shown as such. Owner: P35.12.

**SIG-REL-002 (MUST).** *Descriptor binding.* The release descriptor MUST bind the spine snapshot (world and belief instants, watermark, environment); the clean, pushed code commit; the ruleset, resolver, policy, projection and ontology versions from one version source; the publication-gate digests; the evaluation status; the disclosure digests; the graph-quality report digest (SIG-CONF-006); and the build instant. Only a descriptor of this version is promotable: promotion MUST refuse a dirty tree, an unpushed commit, a `0.0.0` version, a non-sha revision or an older descriptor. A production release MAY be built from a pushed, CI-green, unmerged stack commit. Owner: P35.12.

**SIG-REL-003 (MUST).** *Clock-true release dates.* Every date in a release MUST come from the clock at the moment it describes, and none may be later than the build instant. A replay MUST be labelled as one and is always Class S. The label date is derived, never typed. Owner: P35.12.

**SIG-REL-004 (MUST).** *One writer of public bytes.* Public release bytes MUST change only through the release tool (promote, rollback, withdraw) or the status publisher (status files only). Release storage MUST NOT be publicly readable except through the serving layer. This refines SIG-OPS-004 once the release tool exists. Owner: P35.53.

**SIG-REL-005 (MUST).** *Immutable after staging.* After staging, a release's bytes MUST NOT change except by a tombstone or removal under a recorded disposition; no tool deletes a staged release. Owner: P35.53.

**SIG-REL-006 (MUST).** *Metadata-only promotion.* Promotion MUST switch the latest view, `/releases/latest.json` and the API's current release together, by metadata only — a new configuration generation, with services rolled by digest — and MUST copy no release bytes. A candidate MUST NOT be publicly reachable before promotion. Owner: P35.54.

**SIG-REL-007 (MUST).** *Verification and automatic rollback.* A candidate MUST pass the verification suite on a private staging origin — integrity; identity and clock; route allow-list and absence; stamp and manifest; link crawl and containment; number truth; API parity; attribution; jurisdiction–coordinate sanity; withdrawal barrier; budgets and accessibility; scrub; disclosures; diff sanity (V1–V14); and the graph-quality gate (V15, SIG-CONF-007) — and the public-origin subset after promotion. Any failure or skip blocks promotion. A post-promotion failure MUST roll back automatically and alert the operator; that rollback is pre-authorised (D-G3-8, adopted with B-9). Owner: P35.58. Also: P35.56 (suite A).

**SIG-REL-008 (MUST).** *Snapshot containment.* A release's page snapshot MUST contain no same-origin link outside its own `/s/<pub>/` prefix, except to `/r/<pub>/`, `/releases/` and declared latest-version links. The transparency family's snapshot requirements (appended by PLAN-11B, §56.8) complement this one. Owner: P36.66b. Also: P35.65 (the CI containment check).

**SIG-REL-009 (MUST).** *Release stamp.* Every HTML page MUST show the release label, the data as-of, the code commit (linked) and the build time; MUST say that the public API may serve newer, unreleased records; and MUST link the release's `release.json`. Every response MUST carry `X-SIG-Release`. Owner: P35.13.

**SIG-REL-010 (MUST).** *API release parity.* Every API route whose answer the site shows MUST serve the current promoted release's files and name that release. Every other route MUST label itself live-spine, with its watermark and the current release id. A live-spine answer may change before a release gate only with that label and a `/status/` notice (A-20, "Yes, with labels", 2026-10-01T04:25:48Z). Owner: P35.57. Also: P34.25 (the basis label).

**SIG-REL-011 (MUST).** *Cadence.* A release MUST be cut at least monthly outside the batch window, and early when net-new publishable claims reach 10 % and 14 days have passed since the last promotion. The scheduled cut is suppressed when a Class S promotion landed within the previous 14 days. Release age MUST be alerted at 35 days. This absorbs the republish triggers of G1's freshness draft (SIG-OPS-008). Owner: P36.44.

**SIG-REL-012 (MUST).** *Release classes and the standing go.* Promotion MUST be Class S — a candidate-specific readout signed by the operator (HG-11) — unless the classifier proves every Class R condition; the classifier MUST fail closed. Class R requires a recorded, revocable standing operator go. Agents may run a Class R promotion under it, but MUST NOT promote Class S, sign, or treat silence as approval. Round 11's standing go is the operator's adopted text (B-9; agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z; sha256 `e4e24975b854…`): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." It is renewed at each sub-round gate and never by a bare "continue". A ratchet regression always yields Class S (SIG-CONF-007). Every Class S readout states "single maintainer, no second reviewer" (ADR-163) and "no human check performed" (SIG-CONF-010). Owner: P35.60.

**SIG-REL-013 (MUST).** *Rollback and withdrawal.* Rollback MUST re-apply the current withdrawal set and MUST NOT revert serving configuration. A withdrawal MUST be live on every alias of every release, snapshot, latest view, download and mirror within 15 minutes, served as 410 with a dated tombstone (D-G3-9, adopted with B-9). A reinstatement is a new disposition and a new release, never an edit. Owner: P35.55.

**SIG-REL-014 (MUST).** *Code versions.* Code versions MUST come from one source, and no package may report `0.0.0`. Semver tags MUST be placed on `main` by the operator after merge sittings; agents never tag or push `main`. Public-behaviour changes MUST carry a CHANGELOG entry, and release notes MUST link commits or tags to release labels. Owner: P34.23.

**SIG-REL-015 (MUST).** *Manifest signatures.* Every release manifest and checksum list MUST be signed with the release pipeline's key, held in the secret manager and disclosed as signed by SIG's release pipeline; that signature proves integrity, not approval. Approval of a Class S release is the operator's gate signature (SIG-SEC-010), and the pipeline key never signs gate records. Owner: P36.50 (the operator creates the key, OP-20).

### 56.7 Confidence without independent review (opens the `CONF` family)

No independent human evaluation exists or is planned in Round 11 (ADR-152). Confidence is built by construction and held by mechanical checks; agent and maintainer judgements are disclosed and never gate. The operator adopted "derivation, not identity" (A-6, 2026-10-01T04:03:25Z; ADR-153) and chose no maintainer check (B-31: "No maintainer check", 2026-10-01T04:43:37Z); per the log's labelled interpretation of B-31, the line's other parts — a public quality page that shows failing and ratchet checks, and derivation tier C2 enabled — stand as stated. SIG-EVAL-001…007 remain in force; the waiver of SIG-EVAL-004's lower-bound clause for C0–C2 only is recorded at §55.4 and in ADR-153.

**SIG-CONF-001 (MUST).** *Basis classes.* Every published quality, evaluation or confidence statement MUST carry exactly one basis class — by construction (B0), mechanical census (B1), mechanical sample (B2), agent review (B3), maintainer check (B4) or independent human (B5) — and its n, population, source-mix digest, ruleset and time window. "Human-verified", "independently reviewed", "verified" or "certified" MUST appear only with an independent-human completion marker. Owner: P34.45. Also: P37.45 (basis on public surfaces).

**SIG-CONF-002 (MUST).** *Agent labels are segregated.* Labels produced by AI agents or models MUST be stored with labeller kind, model id, prompt digest and context id. They MUST NOT be stored in or read from human-evaluation tables, MUST NOT be read by any auto-write gate, evaluation-status promotion or release gate, and MUST NOT be applied to partitions reserved for an independent campaign. Owner: P35.48.

**SIG-CONF-003 (MUST).** *Only mechanical checks gate.* A release, materialization or auto-write gate MUST depend only on by-construction, mechanical-census or mechanical-sample evidence (or on independent-human evidence under SIG-EVAL-004). Agent-review and maintainer-check results MAY trigger work and MUST be published with their class. Owner: P34.44a.

**SIG-CONF-004 (MUST).** *Derivation, not identity.* Automatic collapse of records MUST be limited to copies of one upstream record: C0, the same layer ingested twice under one source; C1, the same value in a declared id namespace of a declared lineage, unique in both captures; C2, a one-to-one exact-position match within a lineage declared with documentary evidence whose measured overlap meets the declared floor (at least 0.9), within the copy tolerance and with no attribute conflict. A collapse is recorded as a derivation link and a shared site id, never as an entity merge. Every collapse MUST be re-verified by census on every run, and a failing lineage's tier MUST demote automatically. A collapse MUST NOT produce fewer records than the origin publisher lists as distinct. Organisations auto-link only on an exact shared authoritative identifier or an established registry crosswalk; a name-based match is published as "possibly the same". This is the policy under which SIG-EVAL-004's lower-bound clause is waived for C0–C2 only, in the operator's adopted sentence: "I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes." (A-6; agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z; sha256 `03c0a79ef3b8…`; ADR-L3-B is ADR-153.) Owner: P35.46. Also: P37.46a/b (organisations).

**SIG-CONF-005 (MUST).** *Identity inference is never auto-written without independent evaluation.* Candidate pairs that are not derivation collapses MUST NOT be auto-written while no independent-human evaluation certifies their tier. They MUST be published as possible duplicates with basis and distance, and every affected count MUST be published as a range beside its record count: copies collapsed for the upper bound, and every possible duplicate within the declared distance merged for the lower bound. Owner: P35.47. Also: P34.45 (inferential tiers review-only).

**SIG-CONF-006 (MUST).** *Graph-quality suite.* A versioned check registry MUST declare, for each check, its id, statement, population, placement (sink, spine probe, release gate, pull request, scheduled), mode (enforce, ratchet with baseline, report), threshold, basis class and fixing ticket. The release gate MUST write a `quality.json` report bound into the release descriptor (SIG-REL-002). Owner: P34.44a.

**SIG-CONF-007 (MUST).** *Ratchet discipline.* A ratchet check MUST fail on any regression beyond its baseline. Its baseline MAY only move toward its threshold, and it MUST flip to enforce in the ticket that removes its cause. Loosening a baseline or threshold MUST be recorded by a new ADR. The release gate passes on zero ratchet regressions and zero failures of enforced checks; any other miss is a known-issue line in the readout, not a block. A ratchet regression MUST classify the candidate as Class S (SIG-REL-012). Owner: P34.44a.

**SIG-CONF-008 (MUST).** *Real-data regression corpus.* A pinned corpus of captured upstream slices, one per recorded failure archetype, MUST run with oracles computed from the source bytes by code independent of the pipeline. Committed slices MUST respect their licences; restricted slices run in a scheduled job with their digests committed. Snapshot changes MUST be approved by an explicit commit. Owner: P35.23.

**SIG-CONF-009 (MUST).** *Upstream reconciliation.* Each target run MUST record the upstream's own count at fetch and compare it with the subjects held after the run. An unexplained difference above 1 % MUST fail the target run once the check is enforced; an explained difference carries a recorded reason (a filter, withheld rows, a pagination cap). Owner: P35.34. Also: P34.44a/b (the check).

**SIG-CONF-010 (MUST).** *Maintainer checks, when performed.* Checks by the project's maintainer, when performed, MUST be recorded with the maintainer's answers verbatim, the time, the packet digest, the seed and the strata. The maintainer MUST answer before seeing the system's or an agent's answer. The checks MUST be published as not independent and MUST NOT count as independent labels. Round 11 performs none, because the operator chose "No maintainer check" (B-31, 2026-10-01T04:43:37Z); every Class S readout and the quality page therefore state "no human check performed". Owner: P35.60. Also: P37.45.

**SIG-CONF-011 (MUST).** *Public quality page.* A release-bound quality page (`/quality/`) MUST render every registered check, including failing and ratchet checks, from the release's `quality.json`; a "who checked what" table by basis class, whose independent-review row reads "none" while none has been performed; and a "what we cannot tell you" section. It is a content page without client script. A per-record basis block MUST show the copy, possible-duplicate, corroboration, location-check, technology and evidence states. Owner: P37.45. Also: P37.39 (per-record rendering).

**SIG-CONF-012 (MUST).** *Mechanical estimands are labelled.* Perturbation, hard-negative, census and fidelity results MUST state their estimand in the report header and MUST NOT be presented as real-world identity precision or recall. No public text may claim human verification, independent review or certification; a cross-source camera-match precision figure or a 0.98 certification; completeness ("complete", "every"); model agreement as accuracy; organisation identity or agency counts beyond what the crosswalk proves; candidate recall; that a camera exists or operates (SIG records claims about cameras); capture–recapture totals; maintainer independence; or centrality, rankings or "most connected". Owner: P37.44. Also: P34.47 and P38.1a/b (claim probes).

**SIG-CONF-013 (MUST).** *Least-privilege audit path.* Continuous checks over the production database MUST use a login that can only read, with a statement timeout, and MUST write a probe-run record per run. Owner: P34.43.

**SIG-CONF-014 (SHOULD).** *Declared lineage.* Every source registry row SHOULD declare its lineage (origin, mirror-of, derived-from) with documentary evidence, and each key field its id namespace. An undeclared layer pair with measured overlap above 50 % MUST be held from publication until it is declared (SIG-EPIS-029). Owner: P35.25.

### 56.8 Families appended by later rows, and de-duplication

- **Transparency (`SIG-TRANSP-*`; J3 §11 D01–D25 and K9/K10 D26–D43)** is appended by PLAN-11B, whose 11B transparency rows cite it. SIG-TRANSP-D26…D43 also appear in the K13 UX set; they are written once, by PLAN-11B.
- **The K13 UX set** (UXR-01…38, UXR-A01…A13 and the K0–K14 design ids they adopt) is appended by PLAN-11C, which decides whether it opens new prefixes or folds into `SIG-UI-*`. UXR-A13 adopts SIG-CONF-D01, D05 and D11; these are written once, here, as SIG-CONF-001, SIG-CONF-005 and SIG-CONF-011, and PLAN-11C cites those ids.
- Each later family is an append-only `spec_src` change from the ratified plan, rebuilt by `BUILD.sh`, and registers its prefix in §0.3.
- **De-duplications made here.** G1's provisional SIG-OPS-004: its page release-id clause is SIG-REL-009 and its single-path clause is refined by SIG-REL-004. G1's provisional SIG-OPS-008: its republish triggers are SIG-REL-011 and its as-of disclosure SIG-REL-009; SIG-OPS-008 keeps read-model freshness. The monthly logical export moves from G1's SIG-OPS-002 to SIG-OPS-001. The vacuous-success sentence of G1's SIG-OPS-006 is SIG-ENG-042. DRAFT-ENG-4 and DRAFT-ENG-5 are amendments of SIG-ENG-039 and SIG-ENG-031, not new ids; their "CI green" means SIG-MEM-007.

### 56.9 Traceability

New requirement rows enter the coverage matrix as MISSING with their owner's routing; planning does not turn them MET, and their verdicts follow SIG-ENG-041. The draft-id → final-id map is `docs/build/planning/2026-09-30-next-phase/stageB/T1_id_map.csv`. Landed-status text for this part is appended, dated from the clock, as its rows land; at the time of writing nothing in this part has landed.

### 56.10 Transparency (opens the `TRANSP` family)

This family (appended 2026-10-05 by PLAN-11B, row 239, `decompose-spec mode=extend`) carries the ratified transparency requirements the design phase wrote as drafts: J3 §11's `SIG-TRANSP-D01…D25`, amended by K9 §10's `D26…D34` and K10 §18's `D35…D43`, adopted wholesale by K13's UXR-A10 (plan §5.6, §6.2). The draft → final map is `docs/build/reports/plan-11b/TRANSP_id_map.csv`; the amendments the later designs made to J3's drafts are folded into the final text below, not into separate ids — K9 supersedes D01's index columns with D28's table, replaces D02's funnel with D26/D27's registry-row counting and partition, narrows D07 by D29–D31, extends D14 with D32's per-source statements slice, and K10 gives D03 the §4 publish-matrix reference, re-keys D06 by D36 and gives D09 the D38/D39 texts. D26–D43 are listed under the K13 UX set as well; they are written once, here, and PLAN-11C cites these final ids (§56.8). ADR-162 (transparency and distribution) records the operator's ratification of the design space; SIG-EXPORT-002's RO-Crate clause stands as written (G.7.5 — the design decided linked files, D-J3-7). Nothing in this section weakens a MUST elsewhere.

**SIG-TRANSP-001 (MUST).** *Source index.* SIG MUST publish a source index listing every registered source with name, publisher, publisher type, technology classes, geography, lifecycle status, upstream licence, SIG publication basis, raw-bytes lane, last run and freshness state. Its column set and no-JavaScript presentation are SIG-TRANSP-028's (the K9 table supersedes this draft's own index-columns clause). Owner: P36.48. Also: P35.40 (the source universe it lists).

**SIG-TRANSP-002 (MUST).** *Named source counts.* Every public count of sources MUST name one published counting definition; a published counting funnel MUST list the source ids behind every difference between adjacent steps. The counting mechanics — a source is a registry row and every count is the number of registry rows satisfying a named predicate — are SIG-TRANSP-026's, and the lifecycle partition is SIG-TRANSP-027's (they replace this draft's funnel definition). Owner: P35.40. Also: P35.35.

**SIG-TRANSP-003 (MUST).** *Source pages.* Each source MUST have a page carrying the J3 §4.3 field set; every field MUST be a value or a named absence kind; every field's publication follows the registry publish verdicts of SIG-TRANSP-035 (the K10 amendment). Owner: P36.47. Also: P36.69 (the page's second half), P36.45 (the publish matrix).

**SIG-TRANSP-004 (MUST).** *Upstream ground truth.* A source page MUST link to the upstream ground truth (homepage, dataset endpoint, terms) after credential scrubbing, and MUST show the terms capture date and digest where one exists. Owner: P36.47.

**SIG-TRANSP-005 (MUST).** *Capture history.* A source page MUST show capture history (full UTC time, digest, bytes, media type, changed/unchanged, classification, bytes-available) and MUST NOT state bytes are available unless the lane is raw-ok and the bytes exist in the public archive; a synthetic capture is labelled. Owner: P36.69. Also: P36.51, P37.36.

**SIG-TRANSP-006 (MUST).** *Per-run log.* A source page MUST show a per-run log with outcome, times, duration, fetches, records parsed, claims considered/added/duplicate, rejected counts by reason class and error classes from a closed vocabulary — keyed to executions per SIG-TRANSP-036 (the K10 re-keying). Owner: P36.46. Also: P35.33 (the run/capture export it renders).

**SIG-TRANSP-007 (MUST).** *Cadence disclosure.* Freshness MUST distinguish cadence (declared, next scheduled day, observed) — the shared verdict function, predicate volatility and the two last-change dates are SIG-TRANSP-029/030/031's (the K9 narrowing). Owner: P35.41.

**SIG-TRANSP-008 (MUST).** *Coverage and dossier contribution.* A source page MUST show coverage by jurisdiction and technology and its contribution to each dossier, and each dossier MUST link back to its sources with the same numbers (one shared artifact). Owner: P36.69. Also: P35.44 (the dossier contribution export).

**SIG-TRANSP-009 (MUST).** *Rights record and collection conduct.* A source page MUST show the rights-review record and collection conduct without naming persons — the record content per SIG-TRANSP-038 and the conduct rendered from observed runs per SIG-TRANSP-039 (the K10 texts). Owner: P36.47. Also: P36.69.

**SIG-TRANSP-010 (MUST).** *Issues log.* SIG MUST publish an issues log per source (auto-detected classes + curated known issues) with opened/closed dates, append-only. Owner: P36.49.

**SIG-TRANSP-011 (MUST).** *Per-claim provenance panel.* Every released record MUST carry a per-claim provenance panel (J3 §5.2) stating one binding state and never implying a document SIG does not hold; `legacy_synthetic` claims render the run-level text. Owner: P35.36.

**SIG-TRANSP-012 (MUST).** *View original.* "View original" MUST follow the lane × Part VIII × bytes-stored table (J3 §5.3); no raw link for a screened or restricted lane. Owner: P36.51. Also: P37.36.

**SIG-TRANSP-013 (MUST).** *Figure → evidence.* Every material number on a public page MUST be rendered with a pointer to a manifest-listed artifact and a visible link to its evidence (J3 §5.4). Owner: P35.37.

**SIG-TRANSP-014 (MUST).** *Downloads center.* SIG MUST publish a downloads center per release listing every downloadable file with licence, attribution, size, row count, sha256 and format, plus per-source slices and claim-level statements files (the per-source statements slice is the K9 amendment). Owner: P36.50.

**SIG-TRANSP-015 (MUST).** *Attribution in bundles.* Each downloadable bundle MUST carry `ATTRIBUTION.txt` generated from the source registry, and the publish MUST fail on any required-but-empty attribution. Owner: P36.50.

**SIG-TRANSP-016 (MUST).** *Data dictionary.* SIG MUST publish a data dictionary generated from the ontology and the exporter column registry, and a Table Schema for every tabular resource. Owner: P35.39.

**SIG-TRANSP-017 (MUST).** *Linked metadata.* SIG MUST publish DCAT 3 and PROV-O metadata as linked files; public content pages MUST stay free of `<script>` elements, including JSON-LD, unless a new ADR exempts a named page (the D-J3-7 "linked files only" decision; the SIG-EXPORT-002 RO-Crate clause stands as written, G.7.5). Owner: P35.39.

**SIG-TRANSP-018 (MUST).** *Signed release files.* Release files MUST be signed (detached signature over `SHA256SUMS`) with a published public key — the release pipeline's minisign key under SIG-REL-015's custody split (operator-held; D-J3-8). Owner: P36.50.

**SIG-TRANSP-019 (MUST).** *Zero-egress distribution.* Downloads MUST be served from a zero-or-low-egress host with a non-listable origin, per-file size caps, rate limits and an egress alert with a documented kill switch (D-J3-4/A-3: R2, $50/month ceiling). Owner: P35.5.

**SIG-TRANSP-020 (MUST).** *Raw-bytes lane.* Raw captured bytes MUST NOT be published except for raw-ok sources after the Part VIII byte screen; redactions MUST be new captures; a withdrawal MUST delete, purge and tombstone. Owner: P37.36. Also: P35.31.

**SIG-TRANSP-021 (MUST).** *Status lane.* SIG MUST publish a status page and heartbeat updated at least every 6 hours from scrubbed run records, labelled separately from the release as-of; gated/refused sources appear as counts only (D-J3-11). Owner: P36.43.

**SIG-TRANSP-022 (MUST).** *Scrub gate.* Every transparency surface MUST pass the scrub gate (J3 S-1…S-14); a secret-shaped value anywhere in the publish set MUST abort the publish. Owner: P35.31.

**SIG-TRANSP-023 (MUST).** *Immutable citations.* Every public page MUST cite an immutable URL (`/s/<pub>/` or `/r/<pub>/`) with the release id; a legacy as-of selector MUST resolve at the edge to a real release or answer 400/404/409, never current content (SIG-UI-035's amended clause; SIG-REL-008's containment complements it). Owner: P35.42. Also: P36.66a/b (the snapshots and selectors).

**SIG-TRANSP-024 (MUST).** *Release diff and changelog.* Each release MUST publish an id-level diff against the previous activated release and a human changelog; `/v1/changes` MUST be backed by it; prior releases publish their manifests and a disclosure, not their bytes (D-J3-10). Owner: P36.67.

**SIG-TRANSP-025 (MUST).** *JSON twins and API parity.* Every transparency page MUST have a JSON twin, and the API MUST serve the same release-backed data (J3 §6.10; the API-side parity rule is SIG-REL-010). Owner: P37.42. Also: P35.57.

**SIG-TRANSP-026 (MUST).** *Source = registry row.* SIG MUST define a source as a registry row and MUST publish every source count as the number of registry rows satisfying a named predicate; identifiers that carry data without a registry row MUST be listed as anomalies and never counted. Owner: P35.40.

**SIG-TRANSP-027 (MUST).** *Lifecycle partition.* The sources table MUST assign every registry row exactly one lifecycle state from a published precedence list, and MUST show the partition counts, which MUST sum to the registry row count. Owner: P35.40. Also: P36.48.

**SIG-TRANSP-028 (MUST).** *Sources table.* The sources table MUST offer the K9 §4.1 columns in pre-rendered views, sortable ascending and descending by every sortable column through plain links, and filterable by single-dimension facet pages, all without JavaScript. Owner: P36.48.

**SIG-TRANSP-029 (MUST).** *One freshness verdict.* A source's freshness verdict MUST come from one function shared with alerting, evaluated at the release as-of on release pages and at status time on status pages, and MUST never be shown without its evaluation time. Owner: P35.41.

**SIG-TRANSP-030 (MUST).** *Honest volatility.* Volatility MUST be derived from the ontology predicate registry over all of the source's published claims, and staleness MUST state its evaluable and not-evaluable counts; "unknown" and "0 stale" MUST NOT be shown for an unevaluable source. Owner: P35.41.

**SIG-TRANSP-031 (MUST).** *Two change dates.* "Last upstream change" MUST come from the upstream's declared last-modified value where available, else from a canonical records digest; a byte-only change MUST NOT move it; "last change in SIG's records" MUST be shown separately. Owner: P35.41.

**SIG-TRANSP-032 (MUST).** *Per-source extracts.* Every published source MUST have a per-release derived extract (sites where applicable, statements always) with sha256, size, licence and registry attribution, and a version index listing every activated release containing the source, with added/removed/changed counts. Owner: P36.68.

**SIG-TRANSP-033 (MUST).** *Table download.* The sources table MUST be downloadable as CSV and JSON with a generated Table Schema, and the API MUST serve the same rows. Owner: P36.48. Also: P35.39.

**SIG-TRANSP-034 (MUST).** *Two clocks separated.* Release pages MUST NOT show values that depend on the reader's current time (next run, current verdict); those appear only on status-lane pages labelled with the status time. Owner: P36.43. Also: P35.41.

**SIG-TRANSP-035 (MUST).** *Registry publish matrix.* Every registry field MUST carry a publish verdict (publish / transform / never); fields without a verdict MUST NOT be published, and free-text registry notes, contact fields, credential variable names and internal paths MUST never reach a public artifact. Owner: P36.45.

**SIG-TRANSP-036 (MUST).** *Execution-keyed history.* A source page's ingestion history MUST have one row per execution across every execution store, each with its link basis and clock basis; values that describe a shared run MUST NOT be presented as the execution's. Owner: P36.46. Also: P35.32 (the ingest_run_report store).

**SIG-TRANSP-037 (MUST).** *No-record honesty.* A source whose published data has no execution record MUST say so on its page and in the table. Owner: P36.46. Also: P36.47, P36.48.

**SIG-TRANSP-038 (MUST).** *Rights review record.* The rights review record MUST list every rights decision with basis, gate, reviewer role and date, and MUST state plainly when an approval came from a standing delegated rule rather than a per-source review, when it went beyond the recorded rule, when captured terms conflict, and when a counsel review is operator-reported without a written opinion. Owner: P36.47.

**SIG-TRANSP-039 (MUST).** *Observed conduct.* Collection conduct MUST be rendered from observed run records (robots outcomes per host, refusals, rate limits) and never from the registry's declared robots policy; a disclosure decision to withhold robots outcomes MUST itself be stated. Owner: P36.47. Also: P36.46.

**SIG-TRANSP-040 (MUST).** *Shared dossier artifact.* A source's contribution to each dossier MUST come from one artifact shared with the dossier page and MUST state how records were assigned to the jurisdiction. Owner: P36.69. Also: P35.44.

**SIG-TRANSP-041 (MUST).** *Capture change kind.* Each capture row MUST state its change kind and the file action allowed by the lane × Part VIII × bytes-stored table (J3 §5.3); download links MUST exist only for raw-ok, screened, retained bytes. Owner: P36.69. Also: P36.51.

**SIG-TRANSP-042 (MUST).** *Source changelog.* Each source MUST have a changelog generated from append-only records and release diffs, dated by those records' clocks, never by version-control dates. Owner: P37.41.

**SIG-TRANSP-043 (MUST).** *Published entities.* Source pages MUST list published entities (capped, with the total and the cap stated) and link to the full per-source data. Owner: P36.69.

### 56.11 The K13 public-web experience (extends `SIG-UI-*`; opens `SIG-SRCH`, `SIG-JUR`, `SIG-DSRC`, `SIG-WATCH`, `SIG-EVUI` and `SIG-RQ`)

This family (appended 2026-10-24 by PLAN-11C, row 340, `decompose-spec mode=extend`) carries the ratified K13 user-experience requirements: the synthesis's thirty-eight `UXR-01…38` statements and thirteen adoption rows `UXR-A01…A13` over the K0–K14 design drafts (`docs/build/planning/2026-09-30-next-phase/design/`; plan §5.6, ratified at GATE-P). The draft → final map is `docs/build/reports/plan-11c/K13_id_map.csv`. Prefix decision (§56.8): the synthesis and the K0/K1/K2/K6/K14 interface drafts fold into `SIG-UI-*` as 051–156; K1's `SIG-GEO-DM10` joins `SIG-GEO-*` as 014 and K2's `SIG-EXPORT-D20/D21` join `SIG-EXPORT-*` as 014–015; the K3 search, K4 dossier-index, K5 dossier-sources, K7 watch, K8 evidence and K11 research-queue drafts open the new prefixes `SIG-SRCH-*` (001–014), `SIG-JUR-*` (001–012), `SIG-DSRC-*` (001–009), `SIG-WATCH-*` (001–010), `SIG-EVUI-*` (001–010) and `SIG-RQ-*` (001–010). UXR-A10's J3/K9/K10 drafts are written once in §56.10 as SIG-TRANSP-001…043 and are cited, not re-minted; UXR-A13's L3 drafts are written once as SIG-CONF-001, SIG-CONF-005 and SIG-CONF-011 and are likewise cited. The adoption rows' amendments are folded into the final text where they change a draft: UXR-A01 extends D01 with UXR-02's registry fields and applies D06 through UXR-16; UXR-A02 amends DM06's cannot-apply affordance and DM09's colour use; UXR-A03 swaps D31's years= for dated= and replaces the draft's H-3 symbols with the lexicon; UXR-A04 binds entity links to SIG-UI-067's keys and re-keys the result parameters on SIG-UI-059's registry; UXR-A05 routes every place form through the one gazetteer with the A-Z fallback; UXR-A06 sends the co-located half of source disagreements to the quality-basis row and makes the explorer enhancement the T1 `<sig-table>` element; UXR-A07 generalises DV04 and DV11 through SIG-UI-055, SIG-UI-060 and SIG-UI-061; UXR-A08 keeps the watch filter on the T1 kit element with no watch map in Round 11; UXR-A09 makes `/evidence/<id>/` a generated redirect to `/evidence/claim/<id>/`; UXR-A11 binds research-queue handles to the one identifier module; UXR-A12 binds DR-K14-16's sections to SIG-UI-051 and DR-K14-09's lexicon to SIG-UI-061. Where a draft's table carried no level marker (SIG-GEO-DM10, SIG-UI-D20, SIG-UI-D23, SIG-UI-D33, SIG-SRCH-D14) the final level is MUST: each is a prohibition or a bound the surrounding text states unconditionally, recorded in the map. Nothing in this section weakens a MUST elsewhere.

*The K13 synthesis requirements (UXR-01…38) — final ids SIG-UI-051…088.*

**SIG-UI-051 (MUST).** *Six-section navigation.* The site header MUST offer at most six sections plus a search field: Places; Explore (Map, Graph explorer, Search, Disagreements); Organizations; Watch; Sources & data (Sources, Evidence, Downloads & API, Releases & changes, Status); About (About & how it works, How to read SIG, Glossary, Methodology, How sure is SIG?, Editorial standards, Corrections, Open questions, Dispute). A section or menu item MUST render only when its target route exists in the release being served. Owner: P36.18. Also: P36.16, P36.17.

**SIG-UI-052 (MUST).** *Route registry completeness.* Every route pattern in the page-type registry MUST declare its page type, owner ticket, data-contract id(s) and its no-JS equivalent; the build MUST fail on an unclassified built route or a pattern missing any field. Owner: P36.21. Also: P35.50.

**SIG-UI-053 (MUST).** *Linked mentions only.* Every rendered mention of an entity, place, source, evidence artifact, research task, watch item or release MUST be a link to that object's page using the shared label or handle, or a typed absence. UUIDs, connector keys and registry ids MUST appear only inside Identifiers / Technical details blocks. Owner: P36.41. Also: P36.24.

**SIG-UI-054 (MUST).** *Figure to evidence in two actions.* From every material figure on every page type, the reader MUST reach the claim anchor, record list or evidence artifact behind it in at most two actions, with JavaScript on and off, or see the stated reason why it cannot. Owner: P36.22. Also: P35.37.

**SIG-UI-055 (MUST).** *Sideways links per page type.* Each page type MUST carry the sideways links of the K13 matrix (2.4): dossier to its map, graph, scoped search, watch, open questions, sources ledger, organizations and parent/child places; entity to its places, relationships, graph view, sources and tasks; source to its dossiers, entities, runs, captures, downloads and upstream; evidence to its claims, source and upstream; task and watch item to their subject, place and evidence. Owner: P36.57. Also: P36.55.

**SIG-UI-056 (MUST).** *Upstream and other-resources links.* Every source page and evidence-artifact page MUST show at least one upstream link (S-6 gated) or a named absence, and every dossier and the About page MUST carry a neutral 'Other public resources' block that excludes avoidance routing and plate lookups. Owner: P36.47. Also: P36.64.

**SIG-UI-057 (MUST).** *Place-slug paths.* Place-scoped routes MUST use the K4 display-slug path (for example usa/tx/harris-county-48201) as path segments, handles MUST use the dash-joined place token, and no new route may carry a bare two-letter jurisdiction code. Owner: P36.34. Also: P35.17, P35.18, P35.19.

**SIG-UI-058 (MUST).** *One redirect generator.* Every URL SIG has published (dossier slugs, entity keys, task/watch/evidence handles, /data-freshness/**, /network/, /task/<uuid>/, /id/<type>/<uuid>, /evidence/<id>/) MUST resolve through one generated redirect include with 301/300/410 semantics and static stubs as fallback; no historical URL may return 404 or come to denote a different object. Owner: P36.35.

**SIG-UI-059 (MUST).** *Workspace-state parameter registry.* sig.workspace-state/2 MUST be defined by one parameter registry: common v, release, view, q, type (result type), kind (entity type), jurisdiction (a filter including descendants), frame and bbox (framing only, canonicalised to at), technology, vendor, operator, source, collection, location, status (epistemic status), seen (when SIG observed it), dated (the world date of the fact), currency, focus, page, sort, dir, cursor, within; map at, layers, basemap; graph overview, hops, edge, expand, path. Every v=1 URL MUST keep resolving. Owner: P36.21.

**SIG-UI-060 (MUST).** *Unapplied-facet notice.* A surface that receives a workspace-state parameter it cannot apply MUST display a visible notice naming that parameter and MUST NOT present unfiltered results as filtered. Owner: P36.21.

**SIG-UI-061 (MUST).** *One legend lexicon.* One machine-readable legend lexicon MUST define every symbol, fill, line pattern, colour role and short label, and every template, SVG builder and map style MUST read it. On any page each encoding MUST have one meaning: hollow = exactly one source (points and areas only, never network figures); line pattern = access kind only (configured solid, stated dashed, observed double); currency = ink weight plus a word or date, never a pattern; raspberry = contested or unresolved only; amber = provisional only; the hatch = absence only. Owner: P36.17. Also: P36.28.

**SIG-UI-062 (MUST).** *Candidate versus Provisional.* The record lifecycle state 'Candidate' and the epistemic label 'Provisional' (output of a method not yet independently evaluated) MUST be distinct words, symbols and filter values on every surface. Owner: P36.17. Also: P36.24.

**SIG-UI-063 (MUST).** *Records versus camera sites.* The UI MUST call observation-level rows 'records' and MUST say 'camera sites' or 'listed cameras' only for de-duplicated counts, which appear only once L3 CONF-07b publishes them and then as an interval beside the record count. Owner: P36.24. Also: P36.37.

**SIG-UI-064 (MUST).** *Independent-lineage corroboration.* The corroborated (filled) vs single-source (hollow) encoding MUST count independent lineages; until lineage is declared (L3 CONF-04/CONF-07b) the legend MUST say '2+ source records; republications not yet collapsed'. Owner: P36.17. Also: P36.37.

**SIG-UI-065 (SHOULD).** *One data hue.* The map SHOULD draw records in one data hue and convey technology by facet, legend, list and text code; a categorical colour key SHOULD wait until F5 PKG-07 typing is live and a K14 amendment validates it. Owner: P36.37.

**SIG-UI-066 (MUST).** *One static figure kit.* Every build-time SVG (maps, locators, entity egos, overview graphs, dossier network figures, charts) MUST come from one static figure kit that emits byte-deterministic SVG with no script, no event attributes and no external references; inline figures MUST be styled by the page stylesheet's classes, and standalone figure files MUST be served under a dedicated no-script response policy. Owner: P36.27. Also: P36.28.

**SIG-UI-067 (MUST).** *One identifier module.* Entity labels, entity URL keys (7-character hash) and the T/M/W/E handles (4+ character hash) MUST come from one module sharing slug and hash primitives and the Part VIII person-name screen; search shards, map tiles, graph files, watch/evidence/task titles and the API MUST read its outputs. Owner: P36.29. Also: P36.58.

**SIG-UI-068 (MUST).** *Site-record link target.* Until the release record tree /r/<pub>/ is publicly exposed (G2 ACT-24), links to an individual site record MUST target its row in the dossier sites list (/dossier/<path>/sites/...#<key>); afterwards they MUST target the T0 record. No site link may return 404. Owner: P36.36. Also: P36.35.

**SIG-UI-069 (MUST).** *One dossier template.* Every dossier level MUST be rendered by one template in SIG-UI-010 order with these sections, each a value or a typed empty state: header strip (K4 row fields), At a glance with Figure 1 and locator, Explore bar, deployed/cost/access/policy figures, Where the hardware is (sites list), Where this comes from (K5), Next decisions (K7), What we don't know (with K11 links), Other public resources, How we know this (dossier scope). Owner: P36.55.

**SIG-UI-070 (MUST).** *Entity index.* /entity/ MUST list the published entity types with counts and link a paginated A-Z list per type; every entity count MUST carry the entity-resolution disclosure. Owner: P36.41.

**SIG-UI-071 (MUST).** *Disagreements browser.* SIG MUST publish a disagreements browser listing every published contradiction record with both sides, sources and dates, kept apart from within-source coordinate conflicts and declared-vs-located disagreements, each labelled by kind; the phrase 'kept visible' MUST appear only where the page links them. Owner: P37.38.

**SIG-UI-072 (MUST).** *Changes page and feeds.* SIG MUST publish a changes page and Atom feeds per place and per source generated from release diffs, separating 'SIG's records changed' from 'the source reports a change in the world', dated by release activation and world dates, never by version-control dates. Owner: P37.40.

**SIG-UI-073 (MUST).** *One search index for all entries.* The header typeahead, /search/, scoped forms, the map place search and the explorer's search-to-node MUST use the same release-pinned index and static shards; no surface may keep its own entity or place index, call the live spine, or send keystrokes to a server. Owner: P36.31.

**SIG-UI-074 (MUST).** *One gazetteer.* A place name typed into any search entry (header, home hero, dossier index, map) MUST resolve through the one gazetteer (the K4 registry plus the city layer) to the same top result, showing homonyms with their parents. Owner: P36.31.

**SIG-UI-075 (MUST).** *Base-path helper on every link.* Every internal link in new or changed templates MUST be built with the base-path helper so that a snapshot build under /s/<pub>/ keeps its links inside the snapshot. Owner: P36.66a. Also: P35.65.

**SIG-UI-076 (MUST).** *Release-pinned data only.* Public pages MUST read only release-pinned data (static release files, PMTiles, release-namespaced API routes); any live-spine route shown to readers MUST be labelled 'live, not a citation'. Owner: P36.38. Also: P36.66a.

**SIG-UI-077 (MUST).** *Named acceptance check per ask.* Each operator ask U-003.1 to U-003.11 MUST have a named live acceptance check (K13 5.1) that passes on the promoted release before announcement, recorded as agent-verified with evidence, never as user-tested. Owner: P37.68a.

**SIG-UI-078 (MUST).** *Acceptance journeys.* D3's 13 journeys (A1-A4, J1-J5, O1-O4) MUST pass on the promoted release at 390 px and 1440 px, with JavaScript on and, where the journey allows, off, within their budgets and with zero wrong-conclusion risk; results recorded agent-verified plus the operator's walkthrough. Owner: P37.68a.

**SIG-UI-079 (MUST).** *Queue reachable from absences.* Open research questions MUST be reachable in one action from every typed-absence chip that has a task and from each dossier's 'What we don't know' section; the queue hub MUST be linked from About and from the organizer start-here path. Owner: P36.61. Also: P36.62.

**SIG-UI-080 (MUST).** *Withheld-organisations notice.* Where the publication gate withholds organisations or relationships, surfaces MUST say 'some relationships are not shown pending publication review' without naming or counting Part VIII withholdings. Owner: P36.41.

**SIG-UI-081 (MUST).** *Serving-cost readout.* Each acceptance ticket with a live stage MUST read the billing export and report the UX serving cost (map sessions, tiles, search queries, downloads egress) against the $300/month ceiling; a design change projected to exceed it MUST wait for the operator's explicit go. Owner: P36.71. Also: P37.63, P37.68a.

**SIG-UI-082 (SHOULD).** *Linked metadata files.* In Round 11, machine-readable metadata (DCAT, PROV) SHOULD ship as linked files, not inline JSON-LD, although the page-type registry classifies application/ld+json as data. Owner: P36.50. Also: P35.39.

**SIG-UI-083 (MUST).** *One provenance-panel contract.* Record pages, the claim viewer, entity relationship rows, graph edge panels and the map selection panel MUST render claim provenance through one <ProvenancePanel> data contract with the same fields and binding-state wording. Owner: P36.22. Also: P36.51, P35.36.

**SIG-UI-084 (MUST).** *One Figure component and figures registry.* Every number in page main content MUST be rendered by the one <Figure> component, and each page MUST have one figures[] registry whose ids are unique and resolve to breakdowns. Owner: P36.22. Also: P35.37.

**SIG-UI-085 (MUST).** *The T2 set is closed.* The T2 set MUST stay exactly {map, graph explorer, search}; watch, evidence, research-queue, sources and dossier enhancements MUST use T1 kit elements within T1 budgets, and a new T2 surface MUST need an amendment to the page-type ADR. Owner: P36.20. Also: P35.50.

**SIG-UI-086 (MUST).** *Five-part typed empty states.* Every typed empty state MUST follow the five-part pattern (kind, what is missing and why, what exists nearby, what you can do, when it may change) and MUST name the actual cause class; no surface may call a pipeline or publication gap a research gap. Owner: P36.22. Also: P36.24.

**SIG-UI-087 (MUST).** *Release pages free of live-clock values.* Release pages MUST NOT show values that depend on the reader's current time (next run, current freshness verdict, status-lane counts); those appear only under /status/** labelled with the status clock. Owner: P36.67. Also: P36.43.

**SIG-UI-088 (MUST).** *Historical and undated marked.* Historical and undated relationships and facts MUST be marked as such and excluded from present-tense text on every surface that shows them (map panel, search cards, dossier figures, entity pages, graph panels, watch items). Owner: P36.41. Also: P36.37, P36.39.

*The K0 architecture drafts (UXR-A01) — SIG-UI-089…098.*

**SIG-UI-089 (MUST).** *Route classification.* Every built public route MUST match exactly one page-type pattern; unmatched routes fail the build. Adopted by UXR-A01 extended by SIG-UI-052: the registry also declares each route's owner ticket and data-contract id(s). Owner: P36.20. Also: P35.50.

**SIG-UI-090 (MUST).** *No script on T0.* T0 routes MUST contain no `<script>` element. Owner: P36.20. Also: P35.50.

**SIG-UI-091 (MUST).** *T1 no-JS parity.* T1 routes MUST render identical `main` text with and without JavaScript (excluding `[data-enhancement]`). Owner: P36.20. Also: P35.50.

**SIG-UI-092 (MUST).** *Per-type budgets held.* Per-type budgets (§4.3) MUST hold on a real-sized synthetic build and on each release before promotion. Owner: P36.72a. Also: P35.51.

**SIG-UI-093 (MUST).** *Workspace-state round-trip.* T2 state MUST round-trip through `sig.workspace-state/2`; Back/Forward restore it; a stateful URL without JS shows a notice and its equivalent. Owner: P36.21.

**SIG-UI-094 (MUST).** *Static SVG for every visualisation.* Every visualization MUST have a static SVG rendition with a table/list equivalent in the same box; no `client:only` on public pages. Adopted by UXR-A01 applied to every figure kind through SIG-UI-066. Owner: P36.27. Also: P36.20.

**SIG-UI-095 (MUST).** *Canvas reachability.* Canvas-drawn features MUST be reachable as focusable list items; popups close on Escape and return focus; pan has a single-pointer alternative. Owner: P36.37. Also: P36.20.

**SIG-UI-096 (MUST).** *Strict CSP and HSTS.* Every public response MUST carry a strict CSP and HSTS; no third-party runtime origins. Owner: P36.19.

**SIG-UI-097 (MUST).** *Runtime dependency discipline.* Browser runtime dependencies MUST be on `runtime-deps.json`; public bundles MUST NOT include React after migration. Owner: P36.37. Also: P36.20.

**SIG-UI-098 (MUST).** *Printed dossiers carry figures.* Printed dossiers MUST include their static visualizations with attribution. Owner: P36.26.

*The K1 map drafts (UXR-A02) — SIG-UI-099…107 and SIG-GEO-014; interface copy says 'records' (SIG-UI-063).*

**SIG-UI-099 (MUST).** *Record represented at every zoom.* Every published located record MUST be represented at every zoom: in exactly one cell count at z ≤ 9, and as a drawn feature from its tier's minimum zoom. Owner: P37.17. Also: P35.52, P36.33.

**SIG-UI-100 (MUST).** *Self-hosted basemap.* The map MUST draw a self-hosted OSM basemap from a SIG-controlled origin, with attribution visible and not overlaying controls; on failure it MUST show a notice and a boundaries base. Owner: P36.33.

**SIG-UI-101 (MUST).** *Selection panel fields.* Selecting a site MUST show a derived label, technology, operator (or "not stated"), jurisdiction (linked), source(s) (linked, with licence), first/last seen, precision and status, rendered as text only. Owner: P36.37.

**SIG-UI-102 (MUST).** *Synchronised map list.* A synchronized, keyboard-operable list of what the map shows (places below z10, sites from z10, ≤ 50 rows) MUST be present; Escape MUST return focus. Owner: P36.37. Also: P36.36.

**SIG-UI-103 (MUST).** *Map state round-trip.* Viewport, filters, layers, basemap choice and selection MUST round-trip through `sig.workspace-state/2`; `at=` precision follows §3.4. Owner: P36.37. Also: P36.21.

**SIG-UI-104 (MUST).** *Filter counts and cannot-apply.* Every filter MUST state its count and MUST disclose when it cannot apply at the current zoom. Adopted by UXR-A02 as amended: a filter that cannot apply greys its cells with a note and no hatch. Owner: P36.37.

**SIG-UI-105 (MUST).** *No-JS map baseline.* Without JS, `/map/` MUST show the static overview, the place form and the places table, within ≤ 100 KiB, and every jurisdiction with located records MUST have a paginated site list. Owner: P36.36.

**SIG-UI-106 (MUST).** *Map budgets.* The map MUST meet the K0 T2 budgets on the real release (≤ 360 KiB gzip initial JS; first view ≤ 1.5 MiB tiles + glyphs; Lighthouse mobile ≥ 0.75). Owner: P36.37.

**SIG-UI-107 (MUST).** *Symbol contrast and channels.* Symbols MUST keep ≥ 3:1 contrast against every basemap fill in both themes, and colour MUST NOT be the only channel. Adopted by UXR-A02 as amended: colour means only what SIG-UI-061 and SIG-UI-065 allow. Owner: P36.37. Also: P36.17.

**SIG-GEO-014 (MUST).** *Tile precision bound.* No tile may contain a record at finer precision than its tier, a tier-3 record, or a property outside `sig.map-tiles/2`. Owner: P37.17. Also: P35.52.

*The K2 entity and graph drafts (UXR-A03) — SIG-UI-108…122 and SIG-EXPORT-014/015.*

**SIG-UI-108 (MUST).** *No raw identifiers as labels.* No public surface MAY render a UUID, connector key or source id as a label, heading, node text, link text or table cell outside an "Identifiers" block. Owner: P36.41. Also: P36.24, P35.29.

**SIG-UI-109 (MUST).** *One entity label.* Every entity MUST have exactly one label from `sig.entity-label/1`, identical on entity page, T0 record, overview, typeahead, map popup and API. Owner: P36.29. Also: P35.29.

**SIG-UI-110 (MUST).** *Label basis shown.* Every non-source label MUST display its basis. Owner: P36.41.

**SIG-UI-111 (MUST).** *Unique labels per kind.* Within (kind, release) no two public entities MAY share a full display label. Owner: P36.29.

**SIG-UI-112 (MUST).** *Person-name screen.* Labels and slugs MUST pass the person-name screen; person entities MUST have no page, node, label or slug. Owner: P36.29.

**SIG-UI-113 (MUST).** *Entity URL scheme and permanence.* Entity URLs MUST follow §3.3; the hash MUST never be reissued; rename/merge → 301, split → 300, withdrawal → 410, `/id/<type>/<uuid>` → current. Owner: P36.29. Also: P36.35.

**SIG-UI-114 (MUST).** *Entity page sections.* Entity pages MUST contain the §4.2 sections with typed empty states, within T1 budgets and JS-off parity. Owner: P36.41. Also: P36.42a.

**SIG-UI-115 (MUST).** *Relationship row fields.* Every relationship row and edge MUST show H-2's fields. Owner: P36.41. Also: P36.42a.

**SIG-UI-116 (MUST).** *Historical relationships marked.* Historical and undated relationships MUST be excluded from present-tense text and from the default "current" filter, and MUST be visibly marked. Adopted by UXR-A03 as amended: the draft's 'dash = historical, hollow = undated' symbol clauses are replaced by the lexicon — muted ink plus the word (SIG-UI-061; SIG-UI-088 marks them site-wide). Owner: P36.41. Also: P36.42a.

**SIG-UI-117 (MUST).** *Degree-only is not an edge.* Degree-only facts MUST NOT be drawn as edges. Owner: P37.24.

**SIG-UI-118 (MUST).** *Overview bounds.* Each overview MUST have ≤ 3,000 nodes, per-compartment data files, a static SVG, an adjacency table and a download. Owner: P37.24.

**SIG-UI-119 (MUST).** *Explorer state round-trip.* `/explore/` state MUST round-trip through `sig.workspace-state/2` incl. `path`, `currency`, `years`; "cite this view" yields the snapshot URL. Adopted by UXR-A03 as amended: explorer URL state uses dated= per SIG-UI-059's parameter registry, not the draft's years=. Owner: P37.26.

**SIG-UI-120 (MUST).** *Path answers.* Path answers MUST list every hop with evidence, publish ≤ 3 hops, label longer paths speculative, and type "no path". Owner: P37.26.

**SIG-UI-121 (MUST).** *No unverified centrality.* No centrality, hub ranking or labelled community MAY ship before SIG-IDENT-030's gates pass or an ADR waives them; every count carries the H-8 disclosure. Owner: P37.26.

**SIG-UI-122 (MUST).** *Edge to provenance in two actions.* From any edge or relationship row, the J3 provenance panel of each supporting claim MUST be reachable in ≤ 2 actions with and without JS. Owner: P36.42a. Also: P36.51.

**SIG-EXPORT-014 (MUST).** *Entity and graph export artifacts.* The exporter MUST emit `sig.entity-label/1`, `sig.entity-page/1`, `sig.graph-overview/1`, `sig.graph-components/1`, `sig.slug-history/1`, per compartment, listed in the release descriptor. Owner: P36.41. Also: P37.24, P36.30.

**SIG-EXPORT-015 (MUST).** *Edges carry their claims.* Network and overview edges MUST carry relation, date + kind, currency class, sources and supporting claim ids from the claims, never constants. Owner: P37.24. Also: P36.30.

*The K3 search drafts (UXR-A04/A05) — the SIG-SRCH prefix, 001…014.*

**SIG-SRCH-001 (MUST).** *All compartments in one request.* Public search MUST cover every eligible record of the selected release across **all** licence compartments in one request, keeping each compartment's records in a labelled licence group Owner: P36.38.

**SIG-SRCH-002 (MUST).** *Typed linked results.* Results MUST be typed (place, organization, technology, source, document, page, record) and each MUST link to an existing page of that type in the same release Adopted by UXR-A04: entity result links use the shared identifier keys (SIG-UI-067). Owner: P36.39.

**SIG-SRCH-003 (MUST).** *Match-quality ordering.* Result order MUST be by match quality with a stated match reason per result; it MUST NOT use popularity, evidence counts or confidence Owner: P36.38.

**SIG-SRCH-004 (MUST).** *Jurisdiction names resolve first.* A query that exactly names a jurisdiction (official or alternate name, ISO or postal code) MUST return that place first; homonyms MUST all be shown with their parent, ordered by records held Owner: P36.31.

**SIG-SRCH-005 (MUST).** *Acronym handling.* Acronym aliases MUST match case-sensitively, show their expansion and its source, and MUST NOT present word-matches as matches for the acronym Owner: P36.31.

**SIG-SRCH-006 (MUST).** *Spelling suggestions.* A query with no strong match MUST offer a spelling suggestion when one yields strong results, and MUST say it did so Owner: P36.39.

**SIG-SRCH-007 (MUST).** *Evidence basis per result.* Every result MUST show its evidence basis (sources, support counts, release, as-of; for derived names, that the name is derived) Owner: P36.39.

**SIG-SRCH-008 (MUST).** *Search empty states.* Empty and filtered-to-zero states MUST name what was searched (release, record count, groups) and MUST NOT assert research status or absence Owner: P36.39.

**SIG-SRCH-009 (MUST).** *Search without JavaScript.* Search MUST work without JavaScript (GET form → server-rendered HTML with site chrome, facets, per-group paging and HTML error pages) and pass WCAG 2.2 AA in both states Owner: P36.39.

**SIG-SRCH-010 (MUST).** *Typeahead shards.* The typeahead MUST be an APG combobox over static per-release shards of named things, ≤ 50 KiB per shard, keystroke → suggestions ≤ 100 ms at 4× CPU throttle, sending no keystroke to a server Adopted by UXR-A04 as amended: type= is the result type and kind= the entity type per SIG-UI-059's registry; the draft's /search/?kind=site route becomes type=record. Owner: P36.40.

**SIG-SRCH-011 (MUST).** *Release-verified indexes.* Search indexes MUST be built from the bound release projection, verified against the integrity manifest by streaming hash before use, and served only for promoted releases Adopted by UXR-A05: a jurisdiction entry's place form resolves through the one gazetteer to type=place with the A-Z fallback; no /map/place/ route ships. Owner: P36.31.

**SIG-SRCH-012 (MUST).** *No query logging.* Search MUST NOT log query strings; per-client rate limits MUST key on the LB-reported client address Owner: P36.38.

**SIG-SRCH-013 (MUST).** *Measured relevance.* Relevance MUST be measured each release on a development set and a held-out set: top-3 success ≥ 90% (dev) and ≥ 80% (held-out) on answerable queries; 0 misleading top hits on the honest set; zero-result rate reported Owner: P36.71. Also: P36.79.

**SIG-SRCH-014 (MUST).** *Search performance bound.* p95 latency ≤ 300 ms for the benchmark on the production service shape (1 vCPU); index bytes ≤ 150 MB per release Owner: P36.71.

*The K4 dossier-index drafts — the SIG-JUR prefix, 001…012.*

**SIG-JUR-001 (MUST).** *Canonical jurisdiction keys.* Every published jurisdiction MUST be identified by exactly one scheme-qualified canonical key drawn from ISO 3166-1, ISO 3166-2, US Census GEOID with an explicit level, or a named national scheme. It MUST carry its other identifiers as `(scheme, value)` pairs in a published jurisdiction registry. Owner: P36.34. Also: P35.17.

**SIG-JUR-002 (MUST).** *Scheme preserved end to end.* A jurisdiction claim MUST keep its declared scheme from connector to spine to export. No export MAY group, slug or label on a bare code. Owner: P36.34. Also: P35.17, P35.18.

**SIG-JUR-003 (MUST).** *Placement carried.* Each published record MUST carry its placement: key chain, basis, check and boundary vintage. These are derived by a versioned ruleset from its point claims and from boundary datasets held as captured evidence. Boundary digests MUST be inputs to the release descriptor. Owner: P36.34. Also: P35.19.

**SIG-JUR-004 (MUST).** *Located counts.* A record whose located and declared jurisdictions disagree MUST be counted where it is located and disclosed on both dossiers with per-source counts. Points at (0,0) or suspected of axis swap or sign flip MUST NOT be placed, mapped or counted by their coordinates. Owner: P36.34. Also: P35.19.

**SIG-JUR-005 (MUST).** *Unplaced report.* Records without a placement MUST appear in a data-quality report with counts per reason (closed vocabulary) and per source. They MUST NOT be listed, counted or labelled as a jurisdiction. Owner: P36.34. Also: P35.45.

**SIG-JUR-006 (MUST).** *Grouped dossier index.* The dossier index MUST group US states (and territories) under the United States, separately from other countries and their subdivisions. Each row MUST show name, code with scheme, level, records, located share, sources, evidence types, open questions, disagreements, freshness and children, each with a named definition. Owner: P36.34.

**SIG-JUR-007 (MUST).** *Dossier hierarchy sums.* SIG MUST publish county and place dossiers under each state for the thresholds the operator sets. A parent's total MUST equal the sum of its children plus records placed only at the parent level. Owner: P36.34. Also: P35.45.

**SIG-JUR-008 (MUST).** *Human dossier titles.* Dossier titles MUST be human-readable names. Codes and schemes MUST be secondary. Owner: P36.34.

**SIG-JUR-009 (MUST).** *Dossier URL permanence.* Every dossier URL ever published (including print and JSON aliases) MUST resolve permanently to its successor, a split page listing its successors, or the data-quality report. A URL MUST NOT change to denote a different place. Owner: P36.35.

**SIG-JUR-010 (MUST).** *Publication regime by country.* The dossier's publication regime MUST be derived from its country key. Countries without an adapter MUST use the conservative profile. Owner: P36.34. Also: P36.45.

**SIG-JUR-011 (MUST).** *No-JS dossier reachability.* Every dossier MUST be reachable without JavaScript within three clicks of `/dossier/`, via the hierarchy or an A–Z directory. A search form and a map entry MUST exist with no-JS baselines. Owner: P36.34.

**SIG-JUR-012 (MUST).** *As-of permalinks.* Legacy "as-of" permalinks printed on published dossiers MUST resolve to the content as originally published, with a correction banner where the content was later corrected. Owner: P36.35.

*The K5 dossier-sources drafts (UXR-A06) — the SIG-DSRC prefix, 001…009.*

**SIG-DSRC-001 (MUST).** *Dossier contribution artifact.* For every dossier, the export MUST emit a contribution artifact (`sig.dossier-sources/1`), computed in the release's single read snapshot. Per-source counts MUST sum to the dossier totals under a declared rule. Owner: P36.52. Also: P35.44.

**SIG-DSRC-002 (MUST).** *Per-source contribution display.* Each dossier MUST show, per contributing source: name (linked to its source page), publisher type, records, share, located vs declared, claims by predicate, records by entity type and technology (or `not_typed`), licence and latest-run state. It MUST NOT show bare source ids. Owner: P36.52.

**SIG-DSRC-003 (MUST).** *Contribution timing.* Each dossier MUST show when each source contributed: first and last seen by SIG, first and last run (linked to the run log), and a per-period series. Where re-sightings are not recorded it MUST say `run_level_only` instead of showing a last-seen date. Owner: P36.52.

**SIG-DSRC-004 (MUST).** *Figure definitions and breakdowns.* Every material figure on a dossier MUST carry a definition, an artifact pointer and a per-source breakdown that reconciles to it. The "How we know this" module on a dossier MUST be computed for that dossier; a site-wide block MUST be labelled "Site-wide". Owner: P36.52. Also: P36.55.

**SIG-DSRC-005 (MUST).** *Source disagreements shown.* Each dossier MUST show where sources disagree or overlap: intra-source coordinate conflicts, cross-source contradictions, declared-vs-located disagreements, and co-located records from different sources. Where one of these is not computable it MUST show `not_evaluable` with its reason. Adopted by UXR-A06: the co-located half of a source disagreement is rendered by the quality-basis row (QB-01) from the L3 CONF-07b derivation fields (SIG-CONF-005's possible-duplicate intervals). Owner: P36.52. Also: P37.39.

**SIG-DSRC-006 (MUST).** *Explorer without JavaScript.* The explorer MUST be fully usable without JavaScript: sort (where >25 sources), per-source detail, the over-time chart with a table equivalent, and downloads. Enhanced interactions MUST be optional and within the K0 budget. Adopted by UXR-A06 as amended: the enhancement is the T1 <sig-table> kit element (ENH-01); chart brushing is deferred. Owner: P36.52. Also: P37.61.

**SIG-DSRC-007 (MUST).** *Dossier downloads by compartment.* Dossier data downloads MUST be split by licence compartment, carry registry-rendered attribution and licence, sha256, rows and bytes, and MUST NOT be linked before the attribution, terms-withdrawal and egress gates pass. Owner: P36.53.

**SIG-DSRC-008 (MUST).** *Contribution parity.* The contribution of a source to a dossier MUST be identical on the dossier's explorer and on the source's page. Owner: P36.52. Also: P36.47, P36.69.

**SIG-DSRC-009 (MUST).** *Explorer JSON twin.* The explorer MUST have a JSON twin, and the release-backed API MUST serve the same data. Owner: P36.52.

*The K6 dossier-visualisation drafts (UXR-A07) — SIG-UI-123…134.*

**SIG-UI-123 (MUST).** *Dossier at-a-glance map.* Every dossier with ≥ 1 located record MUST show, in "At a glance", a build-time static map of its jurisdiction: outline, child outlines where there are ≥ 2 children, binned or point records, the single-source encoding, the "no published point" counts and the coverage statement. A caption MUST state release, as-of, source count, "not a census" and every drawn compartment's licence line. A place-level table with equal counts MUST follow in the same page. A dossier with 0 located records MUST show the typed empty state, not a blank map. Owner: P36.27. Also: P36.55.

**SIG-UI-124 (MUST).** *Static-map binning.* Static maps MUST draw points only for tier-0 records where the framing zoom is ≥ 10 and there are ≤ 1,000 records. Otherwise they MUST draw H3 areas at the finest resolution whose average diameter is ≥ 12 px at the figure width, never finer than a record's published precision. Tier-3 records MUST NOT be drawn. Owner: P36.27.

**SIG-UI-125 (MUST).** *Dossier network figure.* A dossier network figure MUST draw only evidenced edges between anchors placed in the jurisdiction (K4 placement) and their counterparties. It MUST have ≤ 40 nodes, reached by grouping only (no ranking). Every node MUST link. The three access kinds MUST be visually distinct and independently hideable without JavaScript. Every edge MUST carry K2 H-2's fields in its table row. A figure with no evidenced edge MUST NOT be drawn. Owner: P36.28. Also: P37.28.

**SIG-UI-126 (MUST).** *Dossier sideways links.* Every dossier MUST link the map, the graph explorer and scoped search for its jurisdiction using `sig.workspace-state/2`. A target that cannot apply a facet it receives MUST say so visibly rather than show unfiltered results as filtered. Adopted by UXR-A07: generalised to every page type by SIG-UI-055's sideways-links rule and SIG-UI-060's unapplied-parameter notice. Owner: P36.57. Also: P36.21.

**SIG-UI-127 (MUST).** *No T2 preload on dossiers.* Dossier pages MUST NOT load T2 code before an explicit reader action. In-place activation MUST reuse the static figure's reserved box, keep the static figure in the DOM for print, write no browser history, and hand state to `/map/` for "Open full map" and "Cite this view". Owner: P37.29.

**SIG-UI-128 (MUST).** *Dossier scoped search.* Every dossier MUST carry a zero-JS GET search scoped to its jurisdiction and descendants, pinned to its release. Owner: P36.56. Also: P36.57.

**SIG-UI-129 (MUST).** *Dossier T1 budgets.* Dossiers MUST meet T1 budgets (§10) on the largest real dossiers (US, GA, TX, CA) and a small one. Each inline map MUST be ≤ 30 KiB gzip and ≤ 60 SVG elements. Owner: P36.55.

**SIG-UI-130 (MUST).** *Print carries every figure.* Printed dossiers MUST include every figure as its static rendition with its caption, attribution, as-of and figure permalink. No figure may split across pages, no control or canvas may print, and symbols MUST stay distinguishable in greyscale. The map MUST lead page 2 after the council brief, with the locator on page 1. Owner: P36.26.

**SIG-UI-131 (MUST).** *Figure accessibility.* Dossier figures MUST meet WCAG 2.2 AA with JS on and off: text alternatives, table equivalents with equal values, a keyboard path to every link, skip links for network figures, 320 px reflow and dark-mode tokens. Owner: P36.27.

**SIG-UI-132 (MUST).** *Figure counts reconcile.* A static figure's counts MUST equal the dossier's K5 figure values and the interactive map's summed cells for the same framing and release. Owner: P36.55.

**SIG-UI-133 (MUST).** *One meaning per symbol.* Within one page, each symbol and line pattern MUST have one meaning, drawn from the single legend lexicon. Adopted by UXR-A07: generalised by the one legend lexicon (SIG-UI-061). Owner: P36.17.

**SIG-UI-134 (MUST).** *Figures leak no data.* Static figures are produced works. They MUST NOT expose per-area numeric data (no data attributes, no per-area titles), and the dossier-visuals build input MUST NOT be published. Owner: P36.27.

*The K7 watch drafts (UXR-A08) — the SIG-WATCH prefix, 001…010.*

**SIG-WATCH-001 (MUST).** *Watch items from publishable claims.* The export MUST produce watch items from publishable spine claims for every kind in §5.2 whose inputs exist. A watch surface MUST NOT depend on a raw key that no query fills. Owner: P36.59. Also: P35.43.

**SIG-WATCH-002 (MUST).** *One alert date.* Every watch item MUST carry one alert date with `date_kind` and `date_certainty`. An `upper_bound` date MUST NOT be labelled a deadline. Owner: P36.59.

**SIG-WATCH-003 (MUST).** *Watch evidence links.* Every item MUST link to its supporting claims and to an upstream document per the J3 §5.3 lane table. Owner: P36.59.

**SIG-WATCH-004 (MUST).** *Watch page per place.* Every place in the dossier index MUST have a watch page and feeds with a coverage statement (bodies monitored, last checked). An empty result MUST appear together with that statement. Owner: P36.59. Also: P36.34.

**SIG-WATCH-005 (MUST).** *Feeds validate.* Feeds MUST validate: iCal (RFC 5545, including empty calendars), RSS 2.0 (with `atom:link self`) and JSON Feed 1.1. They MUST be served with `text/calendar` / `application/rss+xml` / `application/feed+json`. UIDs MUST be stable across builds and use the production domain. Owner: P37.34. Also: P36.59.

**SIG-WATCH-006 (MUST).** *Real feed timestamps.* Feed timestamps (`DTSTAMP`, `lastBuildDate`) MUST come from the watch build, never from a fixture constant. Owner: P37.34.

**SIG-WATCH-007 (MUST).** *Recommender bounds.* The recommender MUST rank only artifacts that bear on the decision's subject, with finite scores computed from D/C/retrievability values the export emits. Owner: P37.31.

**SIG-WATCH-008 (MUST).** *Agenda recency.* Agenda-derived items MUST reach the public watch within 24 h of the source publishing them for watched tenants. Adopted by UXR-A08: the enhanced watch filter is the T1 <sig-table> element and no watch map ships in Round 11 (SIG-UI-085 closes the T2 set). Owner: P37.31.

**SIG-WATCH-009 (MUST).** *Dossier next decisions.* Each dossier MUST show its next decisions and link to its place's watch page. Owner: P36.55. Also: P36.59.

**SIG-WATCH-010 (MUST).** *Watch empty-state honesty.* Empty-state copy MUST state the actual cause class (not connected / not monitored / none found). It MUST NOT call a pipeline gap a research gap. Owner: P36.59.

*The K8 evidence drafts (UXR-A09) — the SIG-EVUI prefix, 001…010.*

**SIG-EVUI-001 (MUST).** *Evidence index.* `/evidence/` MUST list every publishable artifact in the release, paginated, with a human title, source, type, classification and lane. It MUST NOT be empty while the release has publishable artifacts. Owner: P36.60.

**SIG-EVUI-002 (MUST).** *Artifact page blocks.* Each publishable artifact MUST have a page with the §4.2 blocks. Each field MUST be a value or a named absence. Adopted by UXR-A09: /evidence/<id>/ redirects to /evidence/claim/<id>/ through the one redirect generator (SIG-UI-058). Owner: P36.60.

**SIG-EVUI-003 (MUST).** *Capture classification shown.* Every capture row MUST show its classification, and a synthetic capture MUST be labelled a run record. `bytes_available`/"download original" MUST appear only for raw-ok lanes with bytes in the public archive (= J3 SIG-TRANSP-D05). Owner: P36.60.

**SIG-EVUI-004 (MUST).** *Claim viewer binding states.* The claim viewer MUST render by binding state × lane × Part VIII class (§4.3). A missing document text MUST NOT fail the build when the lane forbids bytes. **Amends SIG-UI-028** ("render the document with the supporting span highlighted *where the lane permits showing the bytes*; otherwise the locator, digest and a view-at-source link"). Owner: P36.51. Also: P37.37.

**SIG-EVUI-005 (MUST).** *No fixture diffs.* Capture diffs MUST be computed only from real captures of the same artifact. An export build MUST contain no fixture evidence identifiers. Owner: P36.60.

**SIG-EVUI-006 (MUST).** *Artifact eligibility gate.* The artifact export MUST apply the shared artifact eligibility gate (ADR-124). A withheld or withdrawn artifact MUST be absent from indexes and answer 410 with a content-free tombstone. Owner: P36.60.

**SIG-EVUI-007 (MUST).** *Claim to evidence navigable.* Every claim MUST be navigable to its evidence: record claim anchors link to artifact pages, and `/v1/claim` returns `artifact_id`, capture ids and a provenance href (J3 §5.5). Owner: P36.51.

**SIG-EVUI-008 (MUST).** *Evidence empty-state honesty.* Empty or partial evidence states MUST name the cause class (not built / not yet linked to stored documents / rights-restricted) and MUST NOT call a pipeline gap a research gap. Owner: P36.60.

**SIG-EVUI-009 (MUST).** *Claim-view coverage and cap.* Claim-view pages MUST be generated for every document-genre claim with an `actual_capture` binding, up to a published cap. The cap and the overflow count MUST be stated on `/evidence/`. Owner: P37.37.

**SIG-EVUI-010 (MUST).** *Artifact handles.* Artifact handles MUST be human-readable, stable across releases, and redirect when they change. Owner: P36.29. Also: P36.60.

*The K11 research-queue drafts (UXR-A11) — the SIG-RQ prefix, 001…010.*

**SIG-RQ-001 (MUST).** *Handles and titles.* Every public task, campaign, watch item and evidence artifact MUST have a handle and title per §3. No public queue or task page may use a raw UUID as a label or heading. Adopted by UXR-A11: task handles share the identifier module's primitives (SIG-UI-067). Owner: P36.58.

**SIG-RQ-002 (MUST).** *Task detail blocks.* Every public task MUST have a detail page with the §5.3 blocks. Each block MUST be a value or a named absence. Owner: P36.62.

**SIG-RQ-003 (MUST).** *Card metadata real.* Exported cards MUST carry the catalog's assignee class, effort, scope and reachable dispositions for their type, and the subject's jurisdiction when attributable. Placeholder values are forbidden. Owner: P36.58.

**SIG-RQ-004 (MUST).** *Queue pagination and facets.* The queue MUST be paginated (≤50 cards and ≤150 KiB per page), with no-JS routes by place, type and role, and totals that reconcile. Owner: P36.61.

**SIG-RQ-005 (MUST).** *Gap routing predicate table.* Coverage-gap routing MUST use an explicit predicate→task table. Each task MUST name its missing predicate(s), and its closing condition MUST match its subject grain. Owner: P36.58.

**SIG-RQ-006 (MUST).** *Field gaps as campaigns.* Per-object field gaps MUST be presented as aggregated campaigns (or excluded, D-K11-1), not as individual research tasks. Owner: P36.58.

**SIG-RQ-007 (MUST).** *Draft requests shown, never sent.* Records-requester and document-reviewer tasks MUST show a DRAFT request (statute, citation, template version, residency note) with no requester identity and no transmit path. Owner: P36.63.

**SIG-RQ-008 (MUST).** *Gap links resolve.* Dossier gap links MUST resolve to the real task page for that gap or to a named absence. Static "task has been generated" pages MUST NOT ship in export builds. Owner: P36.62.

**SIG-RQ-009 (MUST).** *Handle redirects.* Handles MUST be stable within a release and redirect (301) across releases when they change. `/task/<uuid>/` MUST redirect to the handle. Owner: P36.62. Also: P36.35.

**SIG-RQ-010 (MUST).** *Queue downloads sharded.* Bulk queue downloads MUST be sharded (≤25 MB per file) and served from the low-egress host. Owner: P36.63.

*The K14 design-system drafts (UXR-A12) — SIG-UI-135…156.*

**SIG-UI-135 (MUST).** *Home leads with tagline and search.* The home page MUST lead with the confirmed tagline (H1), the one-sentence statement and a GET place search, above the fold at 390×844 and 1440×900; the H1 top ≤ 120 px (mobile) and ≤ 160 px (desktop). Owner: P36.64.

**SIG-UI-136 (MUST).** *Home headline figures.* The home page MUST be ≤ 5 viewport heights at 390 px and show ≤ 6 headline figures, each rendered by the J3 `<Figure>` with unit, denominator, as-of, source link and any Provisional or contested flag. Owner: P36.64.

**SIG-UI-137 (MUST).** *Persona start-here paths.* The home page MUST offer one start-here path per co-primary persona (advocate, journalist, organizer), each 3–4 linked steps whose targets resolve on the release. Owner: P36.64. Also: P36.65.

**SIG-UI-138 (MUST).** *Generated example questions.* Example questions MUST be generated from the release and emitted only when their target satisfies the example contract (§6.2). Owner: P36.64.

**SIG-UI-139 (MUST).** *Capability table.* Every capability statement on home and About MUST come from a capability table bound to release metrics. A capability whose metric is 0 MUST render its "being built" state instead. Owner: P36.64.

**SIG-UI-140 (MUST).** *About and glossary pages.* `/about/` and `/glossary/` MUST exist as T1 pages linked from the header's About section and the footer. About MUST state the maintainer model, the independent-review status, what SIG is not, and how to cite and correct. Owner: P36.64.

**SIG-UI-141 (MUST).** *In-brief leads.* Each reference page (methodology, editorial standards, how to read SIG, coverage) MUST open with an "In brief" of ≤ 80 words linking to its precise sections. The precise text MUST NOT lose content. Requirement ids MUST appear only inside "Spec references" disclosures. Owner: P36.64.

**SIG-UI-142 (MUST).** *Glossary popover links.* The first use of a glossary term in `main` on record and reference pages MUST link to its glossary entry with an HTML `popover` definition. Print pages MUST list the terms used. Owner: P36.64.

**SIG-UI-143 (MUST).** *One epistemic lexicon.* Epistemic labels, symbols, plain meanings and precise links MUST come from one lexicon (`epistemic.ts`). Visible text MUST NOT contain raw enum values (`STRONGLY_SUPPORTED`, `BEST_CLAIM_W1`, …) outside Technical details or `code`. Adopted by UXR-A12: the lexicon is SIG-UI-061's one legend lexicon. Owner: P36.17.

**SIG-UI-144 (MUST).** *No repeated sentences.* No sentence of 8 or more words MAY appear more than once in a page's `main` + footer. Count figures MUST carry the "not a census" label instead of a repeated sentence. Owner: P36.24.

**SIG-UI-145 (MUST).** *Forty-word chrome.* Shared chrome visible by default (header labels excluded; footer, provenance, dispute, cite) MUST be ≤ 40 words. The full SIG-UI-044 module MUST be one action away and MUST be page-specific on record pages. Owner: P36.18. Also: P36.24.

**SIG-UI-146 (MUST).** *Design tokens only.* All colours, font sizes, spaces and radii MUST come from `tokens.css`. Text tokens MUST meet ≥ 4.5:1 (large text ≥ 3:1) and essential non-text tokens ≥ 3:1 in both themes. The support ramp MUST be single-hue and lightness-monotone. Reserved hues MUST be used only by their states. Owner: P36.16.

**SIG-UI-147 (MUST).** *Dark theme.* Every template MUST render in a dark theme under `prefers-color-scheme: dark`, declare `color-scheme`, force light for print, and pass axe colour-contrast in dark. Owner: P36.17. Also: P36.16.

**SIG-UI-148 (MUST).** *Type scale.* The type scale MUST have ≤ 8 size tokens with a 13 px minimum, prose measure ≤ 70 ch, and tabular numerals for figures and numeric columns. Owner: P36.16.

**SIG-UI-149 (MUST).** *Reduced motion.* With `prefers-reduced-motion: reduce` there MUST be no animated transitions, map easing or animated layouts. Owner: P36.17.

**SIG-UI-150 (MUST).** *Header and menu.* The header MUST show ≤ 6 sections plus a search field, mark the current section with `aria-current`, share the page grid with `main`, and on mobile collapse into a no-JavaScript `<details>` menu. Record pages MUST show breadcrumbs. Adopted by UXR-A12: the six sections are SIG-UI-051's; nothing here opens a seventh. Owner: P36.18.

**SIG-UI-151 (MUST).** *Empty and error pages.* Every empty state MUST follow the five-part pattern (§6.4) and use the hatch only when the emptiness is absence. 404/410/500 pages MUST be branded, with search, home and status links. Owner: P36.22. Also: P36.18.

**SIG-UI-152 (MUST).** *Visual regression grid.* Visual regression MUST cover every template × {light, dark} × {1440, 390, 320} on the synthetic fixture (no real names, K0 §4.12.6), with canvases masked. A baseline change MUST cite its ticket. Owner: P37.60.

**SIG-UI-153 (MUST).** *Joined words and digit grouping.* Built text MUST contain no words joined at element boundaries and no ungrouped numbers of 5 or more digits outside code, ids and dates. Owner: P36.24.

**SIG-UI-154 (MUST).** *Brand assets.* The site MUST ship a logo SVG, a favicon set, a social card per page type and unique titles and meta descriptions. Owner: P36.25.

**SIG-UI-155 (MUST).** *Print first page.* Printed dossiers MUST open with the council-brief page 1 and carry place, as-of, release, permalink and licence on every page, with no orphan pages. Owner: P36.26.

**SIG-UI-156 (MUST).** *CSS and font budgets.* Design-system CSS MUST be ≤ 12 KiB gzip. The font (if adopted) MUST be ≤ 30 KiB and `font-display: optional`. K14 pages ship 0 KiB JavaScript beyond K0-approved elements. Owner: P36.16.

UXR-A10 and UXR-A13 close the set by citation: the transparency drafts land in §56.10 as SIG-TRANSP-001…043 (appended by PLAN-11B) and the confidence drafts in §56.7 as SIG-CONF-001, SIG-CONF-005 and SIG-CONF-011; contracts cite those ids and mint none again.
