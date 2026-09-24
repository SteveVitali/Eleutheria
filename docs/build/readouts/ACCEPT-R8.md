# Readout — Round 8 (GO-LIVE) accepted-deviations delta — PENDING operator signature

- **Prepared by:** P30.4 (GO-LIVE.4, post-launch closeout), 2026-09-24. **Signed by:** — (**pending**; the
  signature is the operator's, and no agent signs it).
- **Scope:** the deviations the GO-LIVE tail (P30.1 → P30.4) introduced or executed, on top of the 77-row
  ACCEPTED list the operator re-confirmed at P24.9 (`docs/build/readouts/GATE-ACCEPT.md`, 2026-09-13). The
  Round 5–7 decisions (ADR-090 … ADR-101) were ratified with their rounds (LEDGER § GATE DECISIONS
  2026-09-22 / 2026-09-23). They are not re-listed here.
- **Coverage matrix:** `MET-DIFFERENTLY` count **77**, unchanged (677 rows; `check_coverage_matrix.py` exit
  0). None of the rows below changes a matrix verdict. They are operational and publication deviations,
  recorded in ADRs and GATE DECISIONS.

## The delta the operator is asked to sign

| # | deviation | what it departs from | recorded in | status |
|---|---|---|---|---|
| R8-1 | **Combined `/map/points.json`**: a public map-rendering file mixing all 12 licence compartments (225,105 tier-0 points, 17,143,416 B, no per-row licence field) | the 2026-09-24 condition "no mixed-licence artifact in any public object" (the downloads stay licence-separated) | LEDGER § GATE DECISIONS 2026-09-24 (operator: *"Keep it; counsel covers it."*); ADR-106 §5; D-P30.3-COUNSEL | **already accepted by the operator** (2026-09-24); scoped to this one file; split per compartment if counsel's written opinion or a licensor objects |
| R8-2 | **Temporary Cloud SQL scale-up** `db-f1-micro` → `db-custom-2-8192` for the OSM land | the P30 tickets' "no Cloud SQL scaling" default | ADR-102 | operator-approved 2026-09-23; **ended** by P30.4 (R8-7) |
| R8-3 | **In-GCP least-privilege materialization**: role `sig_materialize` (INSERT-only on materialized tables, tier-0 RLS), run as Cloud Run job `sig-materialize`; coverage run `--no-negative-space`; detectors routed to OK | the tickets' laptop-proxy execution + the full negative-space rule | ADR-103; D-P30.2-1 | operator pre-authorized the DB role 2026-09-23 |
| R8-4 | **Camera predicates in the registry**: 14 camera-registry predicates + genres `camera_registry` / `connector_run` at conservative directness D6; undated claims dated from their capture time (labelled inference) | §28 registry coverage limited to the camera family; the non-camera predicates stay unadjudicated | ADR-104; D-P30.2a-1/-2 | engineering decision within §28 latitude |
| R8-5 | **Geospatial camera-site ER published PROVISIONAL**: LLM κ **0.669 < 0.70** → the LLM is a suggester only; auto-write only on tiers whose strict holdout precision ≥ 0.98 (1g 1.000, 3g 0.986); the headline "227998 resolved sites (from 230330 …)" carries the provisional disclosure | the P28.5 bar (κ ≥ 0.70 to trust the LLM adjudicator) and a human-ground-truth evaluation | ADR-105; D-R6.1-EVAL; D-P30.2b-1/-2/-3 | operator "Fix resolution first, then launch" (2026-09-24); the disclosure stays public until D-R6.1-EVAL closes |
| R8-6 | **Share-alike layers public** as separate, attributed compartments (ODbL `osm_physical`, CC-BY-SA ×2), on **operator-reported** counsel clearance with no written opinion on file | ADR-096 §Decision 1 (share-alike stays private pending a dated counsel opinion) | ADR-106 (supersedes ADR-096 §1 only); D-P30.3-COUNSEL | operator 2026-09-24: *"counsel says it's okay and we can publish it all together"* |
| R8-7 | **Steady-state DB tier `db-custom-1-3840`** (not the original `db-f1-micro`) | ADR-075's low-cost posture / ADR-102's "scale back" (the original tier was measured starved) | ADR-107 | engineering decision (≈ $49/month compute, list-price estimate); **new — for signature** |

## What is *not* a deviation (listed so it is not signed by mistake)

- **Honest empty surfaces.** 0 edges and 0 accountability links (D-P30.2-2), `not-recorded` freshness
  (D-P30.3-1), single-z0 tiles (D-P30.3-2) and empty analytics (D-P30.3-3) are **deferred work**, each
  disclosed on the site. Nothing was fabricated to fill them.
- **Operator-gated items.** D-R7.2-SEND (records requests are never sent automatically), D-P21.7-1
  (contribution-back, HG-08), D-P30.3-COUNSEL (the written opinion). These are **owed operator actions**,
  not accepted deviations.

## Gate readiness

- Rows R8-1 … R8-6 already carry the operator's recorded answers (GATE DECISIONS 2026-09-23 / 2026-09-24).
  Signing confirms them as the accepted Round-8 list. **R8-7 is the only new row.**
- **Deferrals rule.** OPEN rows remain. Each one names its owner, precise blocker and landing
  (`docs/tickets/DEFERRALS.md` § "P30.4 sweep"). The engineering rows have a backlog home (BL-055 / BL-056 /
  BL-057) but **no scheduled chain row**, which is why `projectStatus` stays `IN-PROGRESS` (BM-TAIL-03). See
  `docs/build/reports/CAPSTONE_VERIFICATION_2026-09-24.md` §4.

## Operator disposition line

> *(pending)* Operator (project maintainer), date — Reviewed the Round-8 accepted-deviations delta R8-1 …
> R8-7. Disposition: ______ (accept all / send back rows: ______).
