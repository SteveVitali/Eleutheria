# ADR-092 — The export is built from the live spine; launch resolution posture is compute-on-read + observation-level

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.3 (`docs/tickets/P27.3__export-data-shaping.md`), P27.1, P27.4 — design decision operator-ratified 2026-09-22, posture confirmed in P27.1; **implemented by** those tickets
- **Date:** 2026-09-22
- **Related:** ADR-005 (resolution as a stored decision record, not a view), ADR-037 (the materialized/compute-on-read family), ADR-066 (the export-backed web data layer), ADR-090 (the national surface this feeds), §29 (reconciliation / resolution envelope), §38 (exports), §19.4 (coordinate reduction), §32 (coverage — no total), §3.1 (defining standard). Evidence: `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md` §1 (audit: modeling tables empty).

## Context

The 2026-09-22 audit found the spine holds **1,059,533 raw claims + ~92k bare entities** (92,165
`deployment`), but the higher-level modeling tables — `resolution`, `jurisdiction`, `coverage_record`,
`relationship`, `physical_asset` — and the `value_geom` column are **all empty**. Coordinates live in
`camera_latitude`/`camera_longitude` **claims (text)**; the same physical camera appears from
`dot_511`/`osm`/`atlas`/`flock_portal` **un-deduped** (75,479 distinct entities, observation-level).

To render a map / dossier / coverage from raw claims, something must **shape** them (geometry,
per-jurisdiction grouping, cross-source dedup, coverage aggregation). ADR-005 makes resolution a
*stored* decision; the ADR-037/P21.2 family established *compute-on-read* for annotations without new
persistence. The choice for launch: **materialize into the spine** vs **compute at export build**.

## Decision

1. **The public export is built from the live spine** (`PgReadStore` / `reconcile`), replacing the
   fixture-backed request — ADR-066's export→web seam is generalised from dossiers to the whole surface.
2. **Launch resolution posture = compute-on-read at export build + honest observation-level framing.**
   The export computes geometry / grouping / coverage each build; cross-source duplicates are presented
   as **"N observations across M sources," not a claimed deduped census**, until/unless resolution is
   materialized. This honours §3.1 (no synthetic certainty) and §32 (named denominators, no total).
3. **Coordinates are tier-reduced (§19.4)** on emission even though all current claims are tier-0;
   contradictions stay visible (§3.1), never silently merged.
4. **Materialized resolution is deferred, not rejected.** When the API must *serve* resolved entities,
   or dedup becomes a load-bearing public claim, populate `resolution` (and `jurisdiction`/
   `coverage_record`) via append-only sqitch + `python -m reconcile resolve --dsn` (ADR-005) — by a new
   ADR. P27.1 records the posture; P27.3 implements whichever is chosen.

## Consequences

- Fastest, lowest-risk path to real data public: no new migrations for launch, no premature commitment
  to a resolution ruleset before it is validated.
- The shaping logic lives in the export build (a known trade-off — the API does not gain resolved
  entities at launch); revisited if/when the API needs them.
- The honest "observations, not a census" framing avoids over-claiming a dedup SIG has not validated —
  the defensible position for a public accountability record.

## Alternatives considered

- **Materialize resolution now** (populate the empty tables). Canonical and API-serveable, with lineage
  — but heavier (new migrations + a validated ruleset) and commits to resolution decisions before
  they're vetted. Deferred to a follow-up ADR, not discarded.
- **Ship raw claims unshaped.** Rejected — an un-deduped, un-geolocated dump is not a usable or honest
  public surface.

## Proposed spec_src amendment (NOT yet applied — folds in when P27.3/P27.4 land, under the phase gate)

- `docs/research/_meta/spec_src/61_partV_s29to32_workflows.md` (§29): note the **observation-vs-resolved
  public disclosure** rule (a public count says whether it is observation-level or resolution-backed).
- `docs/research/_meta/spec_src/80_partVII_s37to38_api.md` (§38): note the public export is **spine-read**
  and shaped at build time. Then `sh …/BUILD.sh` + a manifest "Spec amendments applied" entry
  (SIG-ENG-003); tracked as `D-P27-SPEC-1`.

## Revisit trigger

- Cross-source dedup / resolution becomes a load-bearing *public* claim (e.g. a headline "N cameras"
  that must be a resolved count) — materialize resolution by a new ADR.
- The read API must serve resolved entities (a consumer needs them) — materialize by a new ADR.
- Compute-on-read at national scale blows the export build time/memory budget — move the aggregation
  into a materialized, incrementally-refreshed layer by a new ADR.
