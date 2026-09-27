# ADR-124 — One publication eligibility/disposition policy (P32.5)

- Date: 2026-10-12
- Status: accepted (engineering; offline-only — no live fetch, publication or gate action)
- Ticket: P32.5 (Round 10 / S1, row 165; requirement SIG-TRUST-006; closes `D-P31.5-2`)
- Base: `03ac3b0` (the P32.4 tip `devin/p32-4-shared-temporal-read-contract`, PR #159)

## Context

SIG-TRUST-006 (§55) requires that every public consumer — indexes, tiles, analytics,
relationship endpoints — apply the *same* reviewed eligibility/disposition policy, consuming
publication-review flags, sensitivity, rights restrictions, and correction/withdrawal state,
with a recorded policy version and reason. Withheld endpoints must not leak through labels or
edge topology. Historical claims stay append-only; a legitimate public withdrawal yields an
honest policy-controlled tombstone. A *current* access withdrawal overrides historical
availability on activation, rollback, and every operator-controlled origin/cache/artifact path.

The P32.1 baseline reconciliation narrowed the delta:

1. The web surface honours `organization.publication_review_required` by construction (P31.16
   evidence: partner-org names label by entity id, and zero names appear in web artifacts).
2. The API did **not**: `PgReadStore._label_for` read `organization.cached_canonical_name`
   directly — `GET /v1/search` and `/v1/entity/organization/…` publicly labelled partner
   organisations the flag marked pending review (the `D-P31.5-2` leak, verified P31.16).
3. Every consumer had its own filter: the API filtered `sensitivity_tier = 0`, exports filtered
   on rights + sensitivity (`ShapingClaim.publishable`), and materialized graph readers served
   persisted rows with no access check at all — a disposition recorded after materialization
   could not take effect.
4. No append-only registry existed in which a publication decision could be recorded,
   superseded, and audited — so "consume the review flag" had no operator-facing release valve.
5. `D-P31.5-2` demanded the choice be made visibly: an ADR declaring the flag moot for public
   accountability organisations, or a read-surface gate — never a silently selected path.

## Decision

**`publication-eligibility/1` — one selector, two carriers, consumed everywhere.**

### The rule (conjunction)

An item is publicly permitted only when ALL of:

- **No current denying disposition** — the latest `publication_disposition` row on the target
  (`decided_at <= clock_timestamp()`, tie-broken by `disposition_seq`) is not
  `withhold`/`restrict`/`withdraw`. A recorded `allow` is the ONLY thing that lifts a pending
  review flag — operator release is an append-only, authority-stamped row, never a code path.
- **Entity eligibility** — the entities the item exposes are eligible: no denying disposition,
  `organization.status` not `withdrawn`/`suppressed`, and `publication_review_required` lifted
  by a recorded `allow` (D-P31.5-2 option B — see below).
- **Existing gates unchanged** — sensitivity (`sensitivity_tier = 0`) and effective rights
  (`redistributable = 'yes'` through the `rights_decision` chain) remain conjoined in the same
  queries; this selector adds, never replaces.

A decision carries `policy_version` + `reason_category` (a public-safe vocabulary:
`pending_publication_review`, `withheld_after_review`, `rights_withdrawal`,
`safety_withdrawal`, `policy_restriction`, `suppressed`) + `authority`. The free-text
`rationale` and `decided_by` stay privileged — a tombstone never states them.

### The carriers

- **Pure** — `policy.eligibility` (`POLICY_VERSION = "publication-eligibility/1"`):
  `DispositionRecord`, `latest_disposition`, `organization_publication_decision`,
  `claim_publication_decision`, `access_decision`, `PublicationDecision.tombstone()`.
- **SQL** — sqitch `publication_dispositions`: the append-only
  `publication_disposition` table (immutability trigger; no UPDATE/DELETE grant to any role;
  `sig_materialize` INSERT only, the same pattern as `review_decision`), the
  `sig.effective_disposition` function, a `spine_watermark` facet (a recorded disposition
  invalidates every cached label/search/shape read in the same transaction), and the shared
  boolean fragments `db.dispositions.entity_eligible_sql` / `claim_eligible_sql`, inlined into
  the API and export queries so a consumer cannot forget to apply the selector. Public roles
  get a *column-grant* on the safe columns only.

Fixture/PG parity tests keep the two carriers identical
(`tests/db/test_publication_dispositions.py`).

### Current access overrides history

Dispositions are evaluated at **access time**, never at build time: the fragments' scalar
lookup orders by `decided_at <= clock_timestamp()`. A withhold recorded in release R2 denies
the data under a rollback to R1 on every origin, cache, archive and compressed-origin path.
Immutable artifacts are denied whole (`access_decision`), never rewritten. The
`effective_disposition(p_at)` pin answers "what did policy say then" for *review*; public
access is always current. Assertion history stays belief-bounded under `temporal-read/1`
(ADR-123) — the disposition layer is orthogonal: history is intact on the spine, access is
gated now.

### Consumers wired

- **API** (`PgReadStore`): `_label_for` (the `cached_canonical_name` path + every label join,
  including `/id/{type}/{uuid}`), `/v1/search` (identifier match + label joins), `/v1/entity`
  (tombstone — no label/facts/location/sources for a withheld entity), `/v1/claim` (tombstone —
  no value), `claims_for` (claim + subject + object-entity gate), the persisted resolution,
  contradiction, relationship/edge, accountability-link and research-task readers (batch
  `eligible_entity_ids`/`eligible_claim_ids` post-filters, so *existing materialized rows* are
  re-filtered at read time), and `/v1/evidence` (artifact-kind dispositions deny the capture
  read). Tombstones carry `{permitted, reason_category, authority, policy_version}` — no
  withheld label, value or topology.
- **Exports**: `ShapingClaim.publication_permitted` conjoined into `publishable` (same
  fragment, evaluated in the shaping query); `sharing_edges`, `subject_entities`,
  `source_stats`, `source_runs` gated so withheld claims pad no count and withheld partners
  emit no edge; `entity_labels`, `corrections`, `claim_weights`, `research_tasks` gated in
  `fetch_export_raw`; `fetch_materialized_graph` post-filters every persisted seam.
- **Fallback posture**: pre-P32.5 dumps (no registry) expand the markers to `true` — honest
  degradation, since no disposition can exist there; the *flag* half is in the same fragment
  and gates whenever `organization` exists.
- **Tiles/analytics/dossiers/compartments** inherit by construction — they consume the shaped
  dataset (publishable-only claims) and the gated raw feeds.

### D-P31.5-2 — option B: the read-surface gate

Chosen: **the flag is enforced, not declared moot.** Rationale:

1. SIG-TRUST-006 explicitly requires that publication-review flags be *consumed*; declaring
   the flag moot would discharge that requirement rather than satisfy it.
2. The flag is a *hold*, not a verdict — its honest release is exactly what the
   `allow` disposition exists for. The HG-11-approved partner organisations (naming them IS
   the accountability feature) are released by the operator recording `allow` rows — the
   approval becomes an auditable, append-only fact instead of an implicit code exemption.
3. A mootness ADR would leave the mechanism absent: the next flagged identity (one the
   operator has *not* approved) would have no gate at all.

Consequence, recorded not silent: until `allow` dispositions are recorded for the
HG-11-approved partners, the API/export surfaces serve them as
`pending_publication_review` tombstones — the flag's meaning, applied uniformly. Recording
those allows is an operator action (the `sig_materialize` role), not a code change.

## Consequences

- **New write surface**: `sig_materialize` appends dispositions; the curation/review path
  records the decisions. The public API gains no write path.
- **Rollback story is now honest**: a release rollback never re-serves withdrawn content —
  the disposition is evaluated at access time on every path.
- **Costs**: one indexed scalar subquery per target in the fragments (covered by
  `publication_disposition_target_idx`); batch readers issue one set-based eligible-ids query
  per seam. Watermark facet adds one row + three statement triggers.
- **`D-P31.5-2` closed** as *read-surface gate*; the flag's release valve is the registry.
- **Authorized review**: the curation/elevated roles keep full-row reads (rationale/decided_by)
  and see the spine ungated — the gate governs *public* representation only and never touches
  sensitivity-tier prohibitions (Part VIII remains governed by its own gates).

## Revisit trigger

- If a legitimately-public denial needs more than the six reason categories (e.g. a
  consent-withdrawn vocabulary for person surfaces under a future Part VIII decision), extend
  `ReasonCategory` + the CHECK together under `publication-eligibility/2`.
- If `restrict` needs to mean "serve coarsened" rather than "deny" on a specific surface (an
  aggregate-only tile tier, say), that surface's semantics need an explicit policy amendment —
  today `restrict` denies public representation uniformly.
- If operator tooling makes `allow`-recording routine (a curation disposition UI), revisit
  whether `publication_review_required` still needs a DB flag or should be modeled purely as
  the absence of an `allow` row.
- If `effective_disposition` ever gains belief-time semantics for public reads (rather than
  review-only), that change is a new ADR — the current-access-overrides-history rule is the
  load-bearing property.
