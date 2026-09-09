# ADR-042: The `flock_portal` connector — the CC BY-SA compartment, snapshot-keyed change detection, and the P08.2 reconciler seam

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P11.1
- **Requirement ids:** SIG-INGEST-030/030a/030b/030c/031/032, SIG-INGEST-035/036/037, SIG-LIC-004a/004b, SIG-ONTO-042/044; exercises (owned/tested by P08.2) SIG-RECON-034/035/036/037/045
- **Spec:** docs/2_canonical_design_spec.md §22.5 (the Eyes on Flock dependency); §23.4 (`flock_portal` — via the aggregator API); §26 (crawler conduct); §29.3 (sharing-edge reconciliation); §29.7 (snapshot-diff reconciliation); §17.6 (disappearance and link rot); §42.2 (the N-compartment export model)

## Context

P11.1 adds the fifth source connector on the P04.1 framework — the **portal layer**
(`flock_portal`) — sourcing the Flock transparency-portal inventory from the **Eyes on Flock**
aggregator's public **CC BY-SA 4.0** JSON API (`GET /api/v1/data`, §22.5, SC-18). It differs
from the CC-BY (`atlas`) and ODbL (`osm`) connectors in ways that each forced a decision:

1. **Its licence is share-alike (CC BY-SA 4.0), incompatible with the CC-BY graph
   (SIG-LIC-004a).** Portal claims MUST land in their own separable compartment; an export
   merging them with the CC-BY graph must fail the build.
2. **The aggregator API is a single point of failure for the only lawful route to the portal
   layer (SIG-INGEST-031, RISK-P0-17).** The vendor 403s every scripted client (F2.1), and a
   challenge-defeating crawler is explicitly out of bounds and not an ADR option (§26 rule 4,
   SIG-INGEST-036/037). Change detection and back-fill therefore key on the upstream, not on SIG.
3. **The portal layer is the input to two P08.2-owned reconcilers** — §29.3 sharing-edge and
   §29.7 snapshot-diff — and the ticket scopes finding *emission* to P08.2. So the connector
   must *produce the raw edges/captures and invoke that logic* without forking it, and without
   contaminating its own reproducible claim stream with the reconciler's non-deterministic ids.

The `compartments.portal` (CC-BY-SA-4.0) row, the `eyes_on_flock` source (MIRROR,
`public_terms_only`, `ai_training_permitted` defaulting false), the export/training gates
(`policy.licensing`), and the two P08.2 reconcilers (`reconcile.sharing`,
`reconcile.snapshot_diff`) already exist. This ticket owns the connector's **runtime** shape.

## Decision

1. **Every row is stamped into the CC-BY-SA-4.0 `portal` compartment, never the CC-BY graph
   (SIG-INGEST-035, SIG-LIC-004a).** `_stamp` sets `license = "CC-BY-SA-4.0"`,
   `compartment = "portal"`, and `ai_training_permitted = false` on every emitted row. The
   build-failing guard is the existing computed export gate: `assert_export_compatible` over the
   portal source plus any CC-BY source raises `LicenseIncompatibilityError` (SIG-LIC-010),
   pinned by a test. `ai_training_permitted = false` is both recorded on rows and *enforced* —
   `assert_training_allowed` refuses the source (SIG-LIC-004b).

2. **A challenge is honoured as a refusal; there is no challenge-defeating code anywhere in the
   module (SIG-INGEST-036/037, §26 rule 4).** The connector holds no HTTP client of its own and
   `fetch()` egresses only through the shared `PoliteFetcher`, which raises `ChallengeEncountered`
   on a 401/403/429 and lets the pipeline record a disappearance (§17.6). The connector never
   retries, rotates identity, solves a challenge, or configures a circumvention technique.

3. **Change detection and `observed_at` key on the upstream `data_last_updated` snapshot field,
   never SIG's fetch time (SIG-INGEST-030c).** `portal_snapshot_date` parses that field and it
   becomes the claim `observed_at`; the portal's own declared freshness is additionally recorded
   as `portal_last_updated_declared` but is **never** trusted as an observation time. `is_poll_due`
   is a pure predicate that suppresses polling until either the upstream snapshot advances or the
   upstream's declared refresh cadence (`upstream_refresh_days`, data) has elapsed.

4. **Back-fill is target-agnostic (SIG-INGEST-030b).** An archived (Wayback) capture is just
   another `discover` target; because `observed_at` keys on the capture's own snapshot date, a
   2025 archived response and a live one are treated identically downstream. No separate back-fill
   code path exists — this is a property of keying on the snapshot field, not a special case.

5. **The predicate write-set is a versioned allowlist enforced as a schema gate (§23.4).** The
   aggregator field → SIG predicate map, the windowed-usage set (SIG-RECON-011), the snapshot
   field, the sharing fields, and the fallback routes are **data** (`data/flock_portal_vocab.toml`).
   `assert_predicate_allowed` refuses anything outside the §23.4 write-set; contract facts, device
   geometry, and any per-search/per-plate row (§18.1) are refused at ingest, not merely at resolution.

6. **Sharing edges are produced as configured-access observations and reconciled through P08.2's
   §29.3 reconciler across the whole snapshot; only the deterministic edges enter the claim
   stream (SIG-ONTO-042/044, SIG-RECON-034/035/036/037).** `organizations_shared_with` /
   `organizations_received_from` become directional `SharingObservation`s (`access_kind =
   "configured_access"`, `from_single_snapshot=True` ⇒ `valid_from_kind = "unknown"`); blank cells
   are negatives (no observation), never "unknown" edges. Reconciling **all** portals in one call
   is what lets asymmetry fire. The connector run streams the reconciled *edges*; the asymmetry
   contradictions and research tasks are the reconciler's to *emit* (owned by P08.2) and are
   available via `FlockPortalConnector.reconcile_sharing`, not folded into the connector's L1
   output — folding in the reconciler's freshly-minted task ids would break the run's
   reproducibility fingerprint (SIG-INGEST-003).

7. **Snapshot diffing and portal appearance/disappearance are cross-capture module functions,
   not single-run `normalize` output (SIG-RECON-045, SIG-INGEST-035).** A single connector run
   sees one capture, so `portal_capture` + `diff_portal_snapshots` (a thin wrapper over P08.2's
   `diff_series`) and `detect_portal_changes` operate over multiple captures supplied by the
   backfill / change-feed driver. A portal dropping out of a later snapshot yields a
   `portal_exists = False` artifact event plus a `source_disappeared` task; an appeared portal
   yields a `portal_exists = True` event plus a "no known deployment" task.

8. **The SIG-INGEST-031 fallbacks are retained as named routes, not scrapers.** Where the
   aggregator lacks a field for a portal, `fallback_tasks_for_gaps` routes to records acquisition,
   contributor capture, or partner archive. Records-request *generation* itself is P10.3; this
   connector only routes to it. A challenge-defeating crawler is explicitly NOT a fallback route.

9. **`connectors` gains `sig-reconcile` as a direct workspace dependency.** `reconcile` depends
   only on `sig-ontology` + `sig-db` and never imports `connectors` (no cycle); declaring it
   directly makes the `reconcile.sharing` / `reconcile.snapshot_diff` imports honest. `pylock.toml`
   is unchanged (the package was already in the resolved graph).

## Consequences

The portal layer now ingests through the same eight stages as every other source, in its own
CC-BY-SA compartment that the export gate keeps out of the CC-BY graph, keyed on the upstream's
own freshness rather than SIG's clock, honouring a challenge as a refusal, and feeding the two
P08.2 reconcilers rather than forking them. Costs and deferrals, stated rather than hidden:

- **No live HTTP transport and no DB wiring ship here** (the connector framework is not DB-wired;
  cf. ADR-028/029). The connector is exercised end-to-end over committed JSON fixtures and pure
  helpers; the live `/api/v1/data` fetch and the orchestration of the backfill/change-feed drivers
  land with the live transport wiring, exactly as every prior connector defers it.
- **Cross-capture operations are module functions, not run output.** Snapshot diffing and
  appearance/disappearance detection require ≥2 captures, which a single run does not have; they
  are invoked by the backfill/change-feed driver. This keeps a single run's claim set a pure
  function of its one capture (SIG-INGEST-003).
- **The sharing findings are not in the connector's L1 stream** (Decision 6). This is faithful to
  the ticket ("emission runs through P08.2, owned there") and preserves reproducibility, at the
  cost that a driver must persist `reconcile_sharing`'s contradictions/tasks separately.
- **`upstream_refresh_days` is a conservative data default (1 day).** The confirmed cadence is a
  Phase-0 outreach deliverable (SIG-INGEST-030a); when it lands it is a one-line data edit.

## Alternatives considered

- **Landing portal claims in the CC-BY graph compartment.** Rejected by SIG-LIC-004a: CC BY-SA is
  share-alike and incompatible; merging must fail the build.
- **Keying change detection on fetch time.** Rejected by SIG-INGEST-030c: it would poll faster
  than the upstream refreshes, adding load without information, and would misattribute the
  observation time. `observed_at` is the upstream snapshot date.
- **A dedicated back-fill code path for archived captures.** Rejected: keying on the snapshot
  field makes an archived capture and a live one identical downstream; a special path is needless.
- **Folding the sharing contradictions/tasks into the connector's claim stream.** Rejected: the
  reconciler mints non-deterministic task ids, which would break the run's reproducibility
  fingerprint, and emission is P08.2's responsibility, not the connector's.
- **Re-implementing the field diff / the sharing reconciliation in the connector.** Rejected: both
  are owned by P08.2 (SIG-RECON-045/034/035/036/037); the connector produces inputs and invokes
  them, and MUST NOT fork them.
- **Building a challenge-defeating crawler as a fallback when the API is unavailable.** Rejected
  outright: it is explicitly out of bounds (SIG-INGEST-031, §26 rule 4) and is not an ADR option.

## Revisit trigger

Revisit if any of: Eyes on Flock changes its API shape, licence, or `data_last_updated` semantics
(re-verify against `/api/v1/data`); the confirmed upstream refresh cadence lands from Stage-0
outreach (a data edit to `upstream_refresh_days`, SIG-INGEST-030a); the connector is DB-wired and
the backfill/change-feed drivers must persist the cross-capture events and sharing findings;
P08.2's §29.3/§29.7 reconciler interfaces change; or §26's crawler-conduct posture is amended
(an ADR with counsel).
