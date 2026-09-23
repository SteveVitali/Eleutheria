# Round 6 (Depth & Resolution) + Round 7 (Activation, Trust & Reach) — design & synthesis

> **Status:** DESIGN DRAFT for operator review, 2026-09-22. Authored on the isolated
> `devin/round6-planning` branch so it does **not** touch the live P27 worktree (the other agent is
> mid-P27.3). **Nothing here is on the chain yet.** The chain-seeding (ticket files + ADRs + manifest
> rows + ledger) is a **coordinated pass after P27 completes**, forked from the P27.10 tip — exactly as
> the P27 round was seeded off the P26 tip. ADR numbers and manifest row numbers below are
> **placeholders** (`ADR-R6-*`) and are assigned at seed time (the live chain is consuming ADR numbers —
> ADR-095 already landed in P27.2).

## 0. Strategic frame (recap + the pivot, confirmed by evidence)

P27 lands a real-data national public surface. But the P27.1 audit proved the graph is **wide but
shallow**: ~1.06M→~2.43M claims and 75k+ geolocated observations, yet `resolution`, `relationship`,
`contradiction`, and `coverage_record` were all **0 rows**, and P27.3 only shapes them *compute-on-read*
(ADR-092 deferred materialization). P27.2 further showed **rights/publishability is essentially solved**
(effective UNDETERMINED 0, publishable 99.9995%). So breadth is no longer the bottleneck — **depth is**.

The differentiator is epistemic rigor, not size: provenance, contradictions kept visible, resolution as a
recorded decision, honest coverage. That machinery is **built but dormant** — ER (deterministic cascade
+ Splink), the resolver, reconciliation + sharing-edges, the contradiction object, coverage/denominators,
the 34-detector task engine, the contributor system, the gold-set + quality-gate eval harness all exist
and are barely exercised on the real spine. **These two rounds activate it.** Risk profile: "run +
materialize + eval + wire," not greenfield.

**Operator inputs incorporated (2026-09-22):**
- Persist the resolved graph (materialize) — yes.
- Lean auto on resolution, but the auto-vs-human balance must be governed by **rigorous ongoing
  statistical/eval methodology**, with a **defer note to revisit the whole auto-vs-human design from
  first principles** once real ground truth exists (LLM-labeled acceptable in the first pass).
- Carefully reason about **contributor identity/login**.
- Pilot users = **activists around Flock/Axon/US surveillance infrastructure** (a broad, partly
  adversarial public — not a single vetted newsroom/council).

## 1. Round split (my decision)

Two rounds, stacked after P27:

- **Round 6 — Depth & Resolution (Phase P28).** Make the graph *real*: resolve/dedup, materialize the
  relationship network, surface contradictions, compute honest coverage, link the accountability layer,
  and refresh the public surface off the materialized graph. 6 tickets (P28.1–P28.6).
- **Round 7 — Activation, Trust & Reach (Phase P29).** Turn on the human + machine loop: contributor
  identity productionization + corrections/contribution ops, the detector/records-request loop, and
  *targeted* (not maximal) source breadth gated on resolution. 3 tickets (P29.1–P29.3).

Rationale for the split: Round 6 is internally coherent (all "make the graph trustworthy"), largely
un-gated, and a prerequisite for Round 7 to be worth doing (breadth/contribution compound a *resolved*
graph, not a pile of observations). Round 7 carries the human-facing gates (identity, contribution,
records-request sending) and ratifies after Round 6 lands, so its scope can be tuned by what Round 6's
eval reveals.

---

## 2. DEEP DESIGN A — Resolution eval & the auto-vs-human balance (first principles)

### 2.1 The problem, stated honestly
"How much to auto-resolve vs route to a human" is **not** an aesthetic choice — it is an empirical
question: *at what matcher confidence does auto-merging keep precision above the bar we're willing to
publish?* You can only answer it by **measuring precision/recall against ground truth**. We do not yet
have real ground truth (no field-verified "these two observations are the same camera" labels). So the
first pass must **manufacture a provisional ground truth, use it honestly, and be explicit that it is
provisional.**

### 2.2 What already exists (we build on it, we do not reinvent it)
- `resolution/gold_set.py` (SIG-IDENT-027): stratified sampling across match-weight bands (forces
  coverage of the ambiguous pairs near the threshold), a **three-value label vocabulary**
  (`match`/`non_match`/`not_enough_information`), **double adjudication with Cohen's κ**, per-label
  provenance (`Adjudication(pair_id, adjudicator, label, dated, ruleset_version, note)`), and a **frozen,
  immutable holdout** that relabelling refuses — so the model can never be tuned against the eval set.
- `resolution/quality_gates.py` (SIG-IDENT-028/029): pairwise **P/R/F1 at each tier boundary**, **B-cubed
  cluster** precision/recall on the holdout, **auto-write demotion** (a deterministic auto-write tier
  whose holdout precision falls below the published floor is demoted to review), and **cluster-shape
  alerts** (oversized law-enforcement cluster; single-bridge join — the classic bad-merge signatures).
  `AUTO_WRITE_TIERS = (0,1,2,3)`; the precision floor lives in `splink_model.toml`
  (`auto_write_precision_threshold`).

The eval harness is complete. **It is simply unpopulated and unrun on the real spine.** The design below
populates and runs it, and adds the one genuinely new capability the operator asked about: an **LLM
adjudicator**.

### 2.3 The LLM adjudicator (first-pass ground-truth bootstrap)
`Adjudication.adjudicator` is a free string, so an LLM adjudicator slots in with **no schema change**:
register `adjudicator = "llm:<model>@<version>"`. The LLM reads the *same versioned
`adjudication_rules` prose* a human adjudicator reads, and emits one of the three labels **plus a
rationale** (stored in `note`) and, ideally, a self-reported confidence. This is a legitimate adjudicator
*role*, recorded with full provenance like any other.

**But an all-LLM gold set measures agreement-with-the-LLM, not truth.** Three guardrails make it honest:

1. **Calibrate the LLM against a human seed (meta-eval).** We (the maintainers) hand-label a **stratified
   seed** (e.g. 200–400 pairs, oversampling the ambiguous weight bands). Compute **Cohen's κ between the
   LLM adjudicator and the human seed** (`GoldSet.kappa` already does this for any two adjudicators). Only
   if LLM-vs-human κ clears a published bar (target **substantial agreement, κ ≥ ~0.7**, tuned) do we
   trust LLM labels as gold for the *training* partition. If κ is low, the LLM is a *suggester*, not an
   adjudicator, and everything routes to human review.
2. **The frozen holdout is human-verified.** Precision is measured against the holdout, so the holdout
   (or a stratified holdout sample) MUST carry **human adjudication** (LLM may be the *second*
   adjudicator, but a human must be one of the two). This keeps the number that governs auto-write honest.
   LLM-only pairs are labelled `frozen=False` (training-only) until a human verifies them.
3. **Double adjudication stays double.** Working-gold pairs get **LLM + human** (or two independent LLM
   *runs* only where κ-calibration justifies it); disagreement → `label=None` (disputed), surfaced, never
   silently picked (`adjudicated_label` already enforces two distinct adjudicators).

### 2.4 Setting the auto-vs-human balance against the (bootstrapped) holdout
Lean auto (operator preference), but *measured*, not asserted:
- Deterministic cascade tiers 0–3 auto-write; probabilistic tiers 4–5 → review (the spec default).
- The Splink match-weight cutoff for auto-write is placed where **measured holdout precision clears the
  published floor**. Set the floor **high** (recommend `auto_write_precision_threshold ≥ 0.98`, tuned) —
  an auto-merged surveillance-infrastructure claim that's wrong is a trust-destroying error.
- `demote_auto_write_tiers` runs every ER pass: any auto-write tier below the floor on the holdout is
  **auto-demoted to review** — a decaying rule can never silently keep writing.
- `cluster_shape_alerts` catches bad merges (oversized LE cluster, single-bridge join) regardless of tier.
- **Active learning to spend human review where it's worth most:** route to the human queue the pairs
  where (a) the model and the LLM adjudicator *disagree*, or (b) the match weight sits nearest the
  decision boundary. This maximizes the information per human label and grows the gold set fastest.

### 2.5 Ongoing statistical monitoring (this is a *process*, not a one-time gate)
- **Every ER run** re-measures pairwise P/R/F1 + B-cubed on the frozen holdout and records them (a
  time-series in build memory / an ops metric); precision drift below floor → auto-demote + alert.
- **The gold set grows from the live loop:** human review-queue decisions, contributor corrections, and
  `/dispute` resolutions become **new adjudications** → periodically re-`build_gold_set` and **re-freeze a
  new holdout version** (the old holdout stays immutable for provenance; versions are diffable).
- **Track LLM-vs-human κ over time** and recalibrate when the model/version changes (the adjudicator id
  carries the version, so drift is attributable).
- Publish the current holdout P/R/F1 + κ on the methodology/coverage page — SIG measuring *its own*
  method is exactly the epistemic-honesty posture (§32, SIG-METRIC-008b already does this for survey
  recall).

### 2.6 DEFER — revisit the auto-vs-human design from first principles (D-R6.1-EVAL, OPEN)
The first-pass gold set is **LLM-bootstrapped with a small human seed**, and the auto-write floor is set
against **provisional** labels. This is honest and usable, but it is *not* the final word. Record a
standing deferral to **re-derive the auto-vs-human balance from first principles once real ground truth
exists** — field-verified sites, contributor-verified matches, or a substantially larger human-adjudicated
holdout. Specifically owed at revisit:
- Re-estimate precision/recall on a *human* holdout and re-tune the floor + tier cutoffs against it.
- Re-assess whether the LLM adjudicator remains trustworthy (κ) as models drift.
- Formalize the active-learning loop and the cost/benefit of human review vs the marginal precision it buys.
- Consider whether the "right" object is pairwise precision or a decision-theoretic loss (the cost of a
  false merge in a surveillance-accountability record is asymmetric and higher than a false split).
Do **not** ossify the first-pass thresholds; they are explicitly provisional. This deferral is
gate-relevant: a launch claim of "resolved sites" must disclose it rests on a provisional (LLM-bootstrap)
eval until this is closed.

---

## 3. DEEP DESIGN B — Contributor identity & login (first principles)

### 3.1 The question
If humans contribute (corrections, curation, data entry, verification), do we need user identity / login /
accounts? The honest first-principles answer is **identity *minimization*: use the least identity each
contribution type actually requires, and never build a homegrown account/credential system.**

### 3.2 What the contribution types actually require (least-identity analysis)
1. **Corrections / disputes** — already a **one-click, no-account** flow (`/dispute`, P15.x). Requires
   **zero identity**. It is the public's primary channel and the right default: lowest friction, no PII,
   no account liability. *Keep as-is.*
2. **OSM contribution-back** — mediated through **OSM's own identity** (a contributor edits OSM; SIG
   observes via the changeset feed + hashtag → `LeverageLedger`, P16.2/P21.7). SIG stores **no** identity
   here — OSM owns it. This is deliberate (leverage upstream, don't run a competing platform). *Keep.*
3. **Curation / L0 data entry / dispositions / revert** — the **authenticated, tiered** surface. This is
   the only path that needs SIG-side identity, and it **already exists**: `api/curation.py` maps a
   **bearer token → a pseudonymous, tiered `tasks.contributor.Contributor`** (401 without a token, 403
   without the tier scope), every write is append-only carrying the **pseudonymous handle** as the human
   actor id, anti-poisoning applies (`tasks/poisoning.py`), and the surface is **not public** (Part VIII
   §0.7; loopback-bound; `SIG_CURATION_ENABLED`). The only gap is the **"real tier-token store"**
   (the demo `CURATION_KEYS` registry).

### 3.3 The recommendation — three tiers of identity, no accounts we own
- **Anonymous (no account):** corrections/disputes — the public channel. *(built)*
- **Federated / mediated:** OSM contribution-back — identity owned by OSM. *(built)*
- **Tiered, invite/issue-based curators:** the P16.1 pseudonymous contributor + bearer-token curation
  surface, for a **small vetted set** (you + trusted collaborators), promoted through tiers, anti-poisoning
  + append-only attribution. **Productionize the real tier-token store minimally** (replace demo
  `CURATION_KEYS`), but keep it **issue/invite-based, NOT open signup.** *(small productionization)*

**Do NOT build a public username/password account system.** For a surveillance-accountability project
whose pilot users are activists in an adversarial domain (motivated adversaries: vendors, police,
doxxers, poisoners, Sybils), a public account system is the wrong trade on every axis:
- **Ethos:** SIG's defining posture is *minimal PII*; running accounts means storing credentials/PII —
  a target for breach and a contradiction of the mission.
- **Attack surface / safety:** open signup invites Sybil + poisoning at scale (anti-poisoning exists but
  open accounts stress it), and account data on *contributors to a surveillance-watchdog* is itself
  sensitive (could endanger activists).
- **Liability / obligation:** hosting accounts makes SIG a platform with auth, session, reset, moderation,
  and legal obligations disproportionate to the pilot's needs.

### 3.4 The deferred path for public authenticated contribution (D-R7.1-AUTH, OPEN)
If/when contribution must scale beyond a vetted curator set, do it via **OAuth against an external IdP
(OSM and/or GitHub)** — store only a **pseudonymous external subject id + tier**, **never** passwords or
PII — behind anti-poisoning + a moderation/safety plan. This is "identity without an account system." It
is a **deliberate later decision** (its own ADR + ticket), **gated on demonstrated demand + a written
moderation/abuse/safety plan + a threat model for contributor exposure.** Defer it; do not build
speculatively. The first-pass posture (anonymous + OSM-mediated + tier-token curators) covers the pilot.

### 3.5 ADR to mint
**ADR-R6-IDENTITY — Identity minimization for contribution.** Records: the three-tier model; no
homegrown accounts, ever; the tier-token curator store productionized (issue-based, pseudonymous); OAuth-
external-IdP as the *deferred, gated* public-auth path; the safety/threat rationale. Revisit trigger:
demonstrated demand for public authenticated contribution + a ratified moderation/safety plan.

---

## 4. ROUND 6 — Depth & Resolution (P28.1–P28.6)

Common invariants (every R6 ticket): append-only (resolution/relationships/contradictions/coverage are
new rows or new decision records, never overwrites); every inference labelled; contradictions stay
visible (§3.1); coordinate reduction (§19.4); never publish a total (§32); Part VIII binding; materialized
writes are new sqitch changes (deploy/revert/verify), never in-place schema edits.

### P28.1 (`R6.1`) — Entity resolution at scale + the eval loop  *(the keystone)*
- **Goal:** dedup the ~75k+ geolocated observations + orgs into resolved entities, **materialized** in the
  spine with visible provenance, governed by a measured precision floor.
- **Deliverables:** (1) run the deterministic cascade (tiers 0–3) + Splink (4–5) over the real spine via
  `reconcile resolve --dsn` / `resolution.er_run`; **materialize `resolution` envelopes** (new sqitch
  change; append-only — a resolution is a stored decision, ADR-005, not a recompute). (2) **Bootstrap the
  gold set:** the LLM adjudicator (§2.3) + a human seed; LLM-vs-human κ calibration report; human-verified
  frozen holdout. (3) **Run the quality gates:** P/R/F1 at tier boundaries + B-cubed + `demote_auto_write_tiers`
  + `cluster_shape_alerts`; set `auto_write_precision_threshold` from measured holdout precision. (4)
  tier-4/5 + disputed clusters → the review queue (`review_pg`/`review_queue`). (5) active-learning routing
  (§2.4). (6) an **eval report** (holdout P/R/F1, κ, dedup ratio, resolved-site count) committed to build
  memory + published to the methodology page.
- **Gate:** none (engineering), but **decision-relevant** — the eval report is the evidence the operator
  reads. **ADR-R6-RESOLVE** (materialize at scale; the eval methodology; the LLM adjudicator; lean-auto
  with the measured floor). **Defer D-R6.1-EVAL** (§2.6). `live_verification=true` (runs over hosted `sig-pg`).
- **Open decision for operator:** the human-seed size + who labels it (you? us? a small trusted set?), and
  the κ bar + precision floor (I'll propose defaults: κ≥0.7, precision≥0.98, tuned in-ticket).

### P28.2 (`R6.2`) — Sharing & relationship network from evidence
- **Goal:** populate the empty relationship/access-edge layer — vendor↔operator, data-sharing, RTCC/fusion
  federation — from real claims (the §29.3/§29.7 `reconcile/sharing.py` + P12.2 `inference/access_paths.py`).
- **Deliverables:** materialized sharing/access edges with support glyphs + visible contradictions;
  feeds the web network island a real graph. New sqitch change for the edge store; append-only.
- **Depends:** P28.1 (resolved entities are the nodes). **Gate:** none.

### P28.3 (`R6.3`) — Contradictions & count reconciliation surfaced
- **Goal:** run §29 reconciliation + the contradiction object (`reconcile/counts.py`,
  `reconcile/contradiction.py`, P08.3) over the real spine — portal-vs-contract device counts, the
  299-vs-190 pattern at scale — and **materialize contradictions** (kept visible, never resolved away).
- **Deliverables:** materialized `contradiction` rows; the public surface shows real, live contradictions
  (SIG's signature). New sqitch change; append-only. **Gate:** none.

### P28.4 (`R6.4`) — Honest coverage computed
- **Goal:** populate `coverage_record` / §32 metrics from real data via `inference/coverage.py` +
  `denominators.py` + `completeness.py` + `freshness.py` — counted quantities with **named denominators**,
  records-derived bounds, negative space, **never a total** (SIG-METRIC-008).
- **Deliverables:** materialized coverage; the coverage page + "what we don't know" backed by data; the
  resolution eval metrics (§2.5) surfaced here too. **Gate:** none.

### P28.5 (`R6.5`) — Refresh the public export/surface off the materialized graph
- **Goal:** re-derive the P27.4 export (+ islands) from the now-materialized resolution / relationships /
  contradictions / coverage instead of compute-on-read; reconcile the ADR-092 posture to "materialized."
- **Deliverables:** richer resolved public surface (resolved sites, real network, live contradictions,
  honest coverage); "N resolved sites (from M observations)" replaces the observation-level framing.
- **Depends:** P28.1–P28.4. **Gate:** HG-11 if it materially changes what's published. **ADR** note
  reconciling ADR-092.

### P28.6 (`R6.6`) — Accountability linkage (deployment↔vendor↔contract↔funding↔policy↔oversight)
- **Goal:** connect the accountability layer (the ~205k procurement claims + P13.x contracts/funding/
  policy/accountability entities) to deployments/orgs via `inference/` so a dossier answers "who deployed,
  funded how, governed by which policy, with what oversight."
- **Deliverables:** enriched per-jurisdiction dossiers; the graph becomes accountability infra, not a map.
- **Depends:** P28.1. **Gate:** none.

---

## 5. ROUND 7 — Activation, Trust & Reach (P29.1–P29.3)

### P29.1 (`R7.1`) — Contributor identity + corrections/contribution ops
- **Goal:** turn on the human loop under public scrutiny with **identity minimization** (§3).
- **Deliverables:** (1) productionize the **tier-token curator store** (replace demo `CURATION_KEYS`;
  issue/invite-based; pseudonymous; anti-poisoning + append-only actor id intact). (2) corrections/dispute
  intake ops + a **takedown/corrections operator runbook** (append-only correction claims; §36
  governance). (3) OSM contribution-back live (MapRoulette + changeset feed → `LeverageLedger`, P21.7).
  (4) **ADR-R6-IDENTITY** (§3.5). **(5) Defer D-R7.1-AUTH** — public OAuth-external-IdP auth, gated on
  demand + a moderation/safety plan; NOT built now.
- **Gate:** HG-08/HG-10 (contribution-back), operator. `live_verification` for the OSM loop.

### P29.2 (`R7.2`) — Detector/task engine + records-request loop on real data
- **Goal:** run the 34-detector catalog (P10.1/P10.2) + records-request generation (P10.3) over the real
  spine to auto-produce the research queue + records requests — the self-feeding accountability loop.
- **Deliverables:** a real research queue (contradictions/gaps/renewals → tasks); auto-drafted records
  requests (operator-gated to *send*); geo queues; anti-abuse (P10.1) intact.
- **Gate:** operator gate for actually sending records requests.

### P29.3 (`R7.3`) — Targeted, relationship-weighted source breadth (gated on resolution)
- **Goal:** expand sources in the **accountability/governance** dimension — more contract/funding/policy/
  oversight sources, fusion-center/RTCC governance, under-covered jurisdictions — **not** maximal commodity
  camera points; each new source runs through P28.1 resolution so it *deepens* the graph.
- **Deliverables:** N targeted high-signal sources, deduped into the resolved graph; each rights-reviewed
  (the P27.2 rights_decision machinery) and resolution-gated.
- **Gate:** HG-03 per source. **Note:** this is the *disciplined* form of the operator's "expand sources"
  instinct — targeted + resolution-gated, not undifferentiated maximal ingestion.

---

## 6. Cross-cutting: ADRs, defer notes, backlog

**ADRs to mint at seed time** (placeholder ids; real numbers assigned then):
- `ADR-R6-RESOLVE` — materialize resolution at scale + the eval methodology + LLM adjudicator + lean-auto
  measured floor (P28.1). Revisit: D-R6.1-EVAL.
- `ADR-R6-IDENTITY` — identity minimization; no homegrown accounts; OAuth-external-IdP deferred (P29.1).
- `ADR-R6-MATERIALIZE-092` — reconciles ADR-092: the public surface now reads the materialized graph
  (P28.5).
- (possibly) `ADR-R6-ACCOUNTABILITY-LINK` — the linkage inference model (P28.6), if it makes a normative
  choice; else per-ticket.

**Defer notes (append to `docs/tickets/DEFERRALS.md` at seed, homed to a Round-6 BL):**
- `D-R6.1-EVAL` (H/V, OPEN) — revisit auto-vs-human resolution from first principles against real ground
  truth (§2.6). Gate-relevant: launch "resolved" claims disclose the provisional-eval basis until closed.
- `D-R7.1-AUTH` (H, OPEN) — public authenticated contribution via OAuth-external-IdP, gated on demand +
  moderation/safety plan (§3.4).

**Backlog:** a new `BL-057` "Round 6 depth & resolution" (theme T4 Publication surfaces or a new depth
theme — themes are capped at 10; likely reuse T2 Live wiring & connectors or T4) homing the Round-6 ADRs;
`D-R6.1-EVAL`/`D-R7.1-AUTH` cite it. (Exact homing decided at seed against the then-current BACKLOG.)

## 7. Seeding plan (post-P27, coordinated pass)

1. **Wait for P27 to complete** (through P27.10 domain cutover). Do not seed onto a moving chain.
2. Fork `devin/p28-round6-planning` (or similar) **from the P27.10 tip**; create the P28.x/P29.x ticket
   contract files (from §4–§5), mint the real ADRs (from §6, next free numbers), append manifest rows
   127+ with a Round-6/7 banner, update the LEDGER (`nextTicket → P28.1`, `round → 6`), add the DEFERRALS
   rows + the BL, run `check_spec_src`/`check_backlog`/`check-build-memory`/`test_policy_adrs` green,
   commit — exactly the pass that seeded P27 off P26.
3. Ratify Round 6 (operator) → the orchestrator resumes and drives P28.1 onward; Round 7 ratifies after
   Round 6 lands (its gates + scope tuned by Round 6's eval results).

This design branch (`devin/round6-planning`) is the source; the seed re-creates the artifacts fresh on the
correct base (numbers, ADR ids, and BL homes finalized against the then-current tree).
