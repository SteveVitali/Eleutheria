# ADR-043: The `audit_structural` connector — aggregates-only, the §18.1 per-plate bright line, and the independent count / sharing reconciler seams

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P11.2
- **Requirement ids:** SIG-INGEST-035/046 (and 046a), SIG-ONTO-042/044, SIG-STORE-025/026 (§18.1), SIG-RECON-011; exercises (owned/tested by P08.2) SIG-RECON-026/029 (count) and SIG-RECON-034/035/036/037 (sharing); §11.16 `UsageAggregate` shape; §18.4 granularity
- **Spec:** docs/2_canonical_design_spec.md §23.7 (`audit_structural`); §11.16 (`UsageAggregate`); §18.1 (the analytics bright line); §18.4 (disclosure granularity); §29.1 (count reconciliation); §29.3 (sharing-edge reconciliation); §29.4 (lifecycle transitions — event-log preferred)

## Context

P11.2 adds the sixth source connector on the P04.1 framework — the **audit-export layer**
(`audit_structural`, §23.7) — parsing the **agency's own** Flock audit CSV exports
(Organization / Network / Portal-Public audits, Event Logs, and `SharedNetworks.csv`), obtained
as public records. Three things forced decisions:

1. **The audit layer is where Part VIII bites.** These exports are per-search logs; ingesting the
   rows as-is would build exactly the "searchable database of people's movements" the project
   forbids (§18.1, SIG-STORE-025). The connector must produce **structural aggregates only** — no
   per-search or per-plate row anywhere — and that must be a *schema property*, not a policy note
   (SIG-STORE-026).
2. **These are the agency's primary records, not the derived HIBF export.** SIG-INGEST-046a
   forbids ingesting a specialist project's *derived* bulk export (hashed plates, inferred names,
   redacted reasons, injected annotations) as though it were the agency record. So the connector
   runs against a dedicated `agency_audit_export` source, never against `have_i_been_flocked`.
3. **The layer feeds two P08.2-owned reconcilers** — §29.1 count (the audit `Camera Count`) and
   §29.3 sharing (`SharedNetworks.csv`) — and the ticket scopes the *reconciliation logic* and
   *finding emission* to P08.2. The connector must produce the observations and invoke that logic
   without forking it or contaminating its reproducible claim stream with non-deterministic ids.

## Decision

**Aggregate in `extract`; guard the boundary in `normalize`.** Per-search rows are read
transiently and consumed inside the pure `extract` stage: what leaves the connector is only
`UsageAggregate` rows (§11.16), the camera-count observation, redacted-cell records, sharing
edges, or lifecycle transitions — never a per-search row. `aggregate_search_events` bins events by
`(searching_org, source_org, reason_category, month, search_scope)` and counts; the finest stored
granularity is one month (§18.4), so the per-search timestamp is read only to derive the month and
then dropped. `assert_no_per_row_output` is run over every emitted row as the §18.1 schema gate: a
row whose keys collide with the data-driven `forbidden_output_columns` (plate, plate_hash,
search_id, officer, timestamp, …) is a hard `PerRowLeak`. The parse artifact holds the raw CSV
(equivalent to the raw capture, retained under a restricted tier per §17.5/N2); only the **L1
claim stream** is the canonical store the bright line governs, and it carries no per-search row.

**The audit `Camera Count` is an independent count claim, not a merge.** It lands under
`active_device_count` (the `active` count basis the §29.1 table assigns "Portal; audit `Camera
Count`; vendor statement"), carrying `count_basis` and the `audit_log` evidence genre so P08.2's
`reconcile.counts.reconcile_counts` bins and weighs it correctly. The connector exposes
`reconcile_camera_counts` as the seam; P08.2 resolves each basis on its own and surfaces
disagreements as findings — it never emits a single merged "true count" (SIG-RECON-026). A `***`
Camera Count is a withheld state (`classify_cell`), never a fabricated count and never a zero.

**`SharedNetworks.csv` → directional configured-access edges via P08.2.** Each row's outbound
(`Shares With`) and inbound (`Receives From`) partner lists become directional
`reconcile.sharing.SharingObservation`s (blank cells are **negatives**, not "unknown" edges;
single-snapshot edges carry `valid_from_kind='unknown'`, SIG-RECON-036) and are reconciled across
the whole file through `reconcile.sharing.reconcile_sharing` so asymmetry can fire (SIG-RECON-035).
Only the **deterministic edges** enter the connector's L1 stream; the asymmetry contradictions and
research tasks are P08.2's to emit (their non-deterministic ids would break the reproducibility
fingerprint, SIG-INGEST-003) — exactly the seam P11.1 established.

**`***` redaction is a distinct recorded state.** `classify_cell` is the single reader every audit
cell goes through, returning `redacted` / `empty` / `present`; a redacted reason maps to the
distinct `redacted` reason-category (never `unspecified`), and `redacted_cell_rows` records the
withheld cells as their own `audit_cell_redacted` state so the negative space is queryable.

**The four audit source types are a closed, non-interchangeable set.** `assert_audit_source_type`
refuses any type outside `{organization_audit, network_audit, portal_public_audit, event_log}`, and
`audit_source_type` is stamped on every aggregate / count / lifecycle row so the types are never
silently unioned (§23.7). Event-log captures land dated `deployment_lifecycle_transition` rows
tagged with their type; the §29.4 preference of event-log over inferred transitions is P08.2's.

**A new `agency_audit_export` source, not a pinned compartment.** The agency public record carries
no copyright reservation (CC0-1.0). Like `records`, the connector does not pin an export
compartment — the licence gate decides it per source (SIG-LIC-009a) — it stamps `source_id`,
`vocab_version`, and append-only provenance. The field/column maps, the four types, the reason and
redaction vocabularies, and the sharing/camera-count columns are **versioned data**
(`data/audit_structural_vocab.toml`, §20), so an agency-configured schema is a data edit (§23.7:
the audit schema is discovered per capture).

## Consequences

- The `UsageAggregate` **analytics substrate** (Hive-partitioned Parquet on DuckDB, small-cell
  suppression, the UUID+period join) is **P12.1's** to build (§18); this connector *writes* the
  aggregate rows only. The rows carry the §11.16 predicate surface and source-agency provenance so
  P12.1 can land them without re-deriving anything.
- Cross-export de-duplication (§23.7 "Duplicate handling") is implemented at the
  `(source_org, searching_org, window)` block level (`deduplicate_events`) — distinct within-export
  searches are preserved and counted; a window covered by a *second* export is the recorded
  overlap. Combining aggregates across many captures in one run is a downstream (P12.1) concern.
- Officer/name resolution and police rosters are discharged **by exclusion** (§23.7, SIG-PUB-010):
  no per-search or per-person row is ingested, so no officer name can enter — enforced by the same
  `forbidden_output_columns` gate.
- The connector is not DB-wired and runs no live public-records fetch in CI (like every prior
  connector, ADR-028/029/042); the pure aggregation / count / sharing logic is fully tested against
  committed CSV fixtures.

## Revisit trigger

Revisit if any of: P12.1 lands the `UsageAggregate` DuckDB/Parquet substrate (the connector's
rows become that boundary's input — re-check the §11.16 predicate surface, small-cell suppression,
and the UUID+period join); the agency audit-export schema drifts (the column aliases, the four
audit source types, the `***` sentinel, or the reason vocabulary are versioned data in
`data/audit_structural_vocab.toml` — a drift is a data migration, and the canary flags it); a
live public-records ingestion backend is wired (the transient CSV transport and cross-capture
aggregation move behind it); or P08.2's count (§29.1) / sharing (§29.3) reconciler contracts change
(the `reconcile_camera_counts` / `reconcile_audit_sharing` seams are re-verified against them).
