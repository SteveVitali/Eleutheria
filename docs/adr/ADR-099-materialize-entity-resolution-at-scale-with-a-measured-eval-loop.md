# ADR-099 — Materialize entity resolution at scale, governed by a measured eval loop

- **Status:** Accepted
- **Phase / ticket:** Phase 28 / P28.1 (`docs/tickets/P28.1__entity-resolution-at-scale.md`) — Round 6 (Depth & Resolution) keystone (`DEPTH.1`); the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-23
- **Related:** **ADR-005** (resolution is a stored decision record, not a view — this ADR materializes exactly that), **ADR-092** (the P27 launch posture — export built from the spine, launch resolution left **compute-on-read + honest observation-level framing**; this ADR supersedes that posture *for the resolved layer*), **ADR-037** (compute-on-read Contradiction/Coverage family, the sibling posture P28.3/P28.4 change), **ADR-101** (the public surface then reads the materialized graph — the P28.5 reconciliation of ADR-092), **§14.7** (ER quality gates SIG-IDENT-027/028/029), **§16** (append-only spine), **§29** (resolution envelope), **§3.1** (defining standard — contradictions stay visible), **§19.4** (coordinate reduction), **§32 / SIG-METRIC-008b** (SIG measuring its own method), **§0.7 / Part VIII**, the deferral **D-R6.1-EVAL** (this ADR opens), backlog home **BL-057**.

## Context

The P27.1 launch audit measured the shape of the real hosted spine: ~1.06M claims / 210 sources /
~92k entities / ~75k geolocated camera-sites, with the modeling tables
(`resolution`/`jurisdiction`/`coverage_record`/`relationship`/`value_geom`) **empty** — coordinates
live as text under the connector-registered `camera_latitude`/`camera_longitude` predicates.

P27.3 (`exports/src/exports/shaping.py`) and P27.4 (`exports/src/exports/spine_export.py`) shipped a
deliberately conservative launch posture (ADR-092): rather than fabricate a resolved census, shaping
computes a lightweight **observation envelope** per `(subject, predicate)` **at export-build time,
read-only, never written back to the spine** — one distinct normalized value → `resolved`, several →
`conflicted` (every candidate retained, §3.1), none → `unreported` — and frames a site as "N
observations across M sources" (SIG-RECON-058). `run_shaping` opens a read-only session; `run_spine_export`
runs everything inside a single `REPEATABLE READ READ ONLY` snapshot. `reconcile.RESOLVE` cannot even
be applied to the `camera_*` predicates (they are connector-registered, not ontology-registered, so the
§29 resolver raises `KeyError`). That was the honest launch choice: observation-level framing, not a
device census, while the ER machinery sat built-but-dormant on the real data.

The built machinery exists and is exercised only on fixtures: the deterministic cascade (tiers 0–3),
the Splink probabilistic model (tiers 4–5, `resolution/data/splink_model.toml`), blocking, `er_run`,
the gold-set + quality-gate toolkit (`resolution/quality_gates` over `data/quality_gates.toml`), and
the review queue (`review_queue`/`review_pg`). What is missing is (a) resolution **materialized** into
the spine over the real graph, and (b) a **measured** basis for how much of it is auto-written versus
sent to human review. The operator's stated preference is "lean auto" — but an auto-merged
surveillance-infrastructure claim that is wrong is a trust-destroying error, so "lean auto" must be
*measured against a holdout*, never asserted.

## Decision

1. **Materialize `resolution` envelopes at scale into the spine** (P28.1). Run the deterministic
   cascade (0–3) + Splink (4–5) over the real spine via `reconcile resolve --dsn` / `resolution.er_run`
   and **write** the resulting resolution envelopes as a **new sqitch change** (deploy/revert/verify),
   **append-only** — a resolution is a stored decision (ADR-005), never a recompute-in-place and never
   an `UPDATE`/`DELETE`. The run is idempotent. This **supersedes ADR-092's compute-on-read posture for
   the resolved layer**: the resolved entities become durable spine rows, not an export-time envelope.
   The observation-envelope path in `shaping.py`/`spine_export.py` remains valid for predicates ER
   cannot yet decide and as the honest fallback; ADR-101 governs how the public surface migrates onto
   the materialized rows.

2. **Bootstrap the gold set, then measure against it.** The first-pass gold set is built from a
   **maintainer-labelled stratified seed** (oversampling the ambiguous match-weight bands) **plus an
   LLM adjudicator** (`adjudicator="llm:<model>@<version>"` reading versioned `adjudication_rules`, with
   its rationale retained). An **LLM-vs-human κ calibration** report is produced and a **human-verified
   frozen holdout** is cut. Every ER run re-measures pairwise P/R/F1 + B-cubed on the frozen holdout and
   records the time series in build memory (and surfaces it on the methodology/coverage page — SIG
   measuring its own method, §32 / SIG-METRIC-008b).

3. **Lean-auto, but against a MEASURED floor.** Deterministic tiers 0–3 auto-write; probabilistic tiers
   4–5 route to review (the spec default). The Splink auto-write cutoff is placed where **measured
   holdout precision clears a published floor**. The floor is set **high**:
   `auto_write_precision_threshold ≥ 0.98` and the LLM-vs-human agreement bar `κ ≥ 0.7` (both tuned
   in-ticket against the bootstrapped holdout — these are the **measured** launch values, not asserted
   constants). `demote_auto_write_tiers` runs every ER pass and **auto-demotes to review** any
   auto-write tier that falls below the floor on the holdout; `cluster_shape_alerts` catches bad merges
   (oversized LE clusters, single-bridge joins) regardless of tier; active-learning routing sends the
   model↔adjudicator disagreements and boundary-weight pairs to the human queue to grow the gold set
   fastest.

4. **Provisional by construction — open `D-R6.1-EVAL`.** The bootstrapped gold set rests on
   **provisional** (LLM-bootstrap + small human-seed) labels. This ADR records a standing deferral
   (`D-R6.1-EVAL`, OPEN, homed to BL-057) to **re-derive the auto-vs-human balance from first principles
   once real ground truth exists** (field-verified sites, contributor-verified matches, or a
   substantially larger human-adjudicated holdout). The thresholds in (3) are explicitly provisional and
   must not ossify; a launch claim of "resolved sites" **discloses** it rests on a provisional eval until
   `D-R6.1-EVAL` is closed.

## Consequences

- The spine gains durable, provenance-carrying `resolution` rows over the real graph; downstream
  P28.2 (relationships), P28.3 (contradictions), P28.4 (coverage) and P28.6 (accountability linkage)
  build on resolved entities as nodes; P28.5 re-derives the public export off the materialized graph
  (ADR-101).
- The auto-write posture is auditable and self-correcting: a decaying rule can never silently keep
  writing (auto-demotion), and the holdout metrics are published, not hidden.
- The launch narrative shifts from "N observations across M sources" to "N resolved sites (from M
  observations)" **only where the measured floor is cleared**; everything else stays observation-level
  and honest.
- Because the eval is provisional, every "resolved" surface must carry the provisional-eval disclosure
  until `D-R6.1-EVAL` closes; the ADR is deliberately not the final word on the balance.

## Alternatives considered

- **Keep ADR-092 compute-on-read forever.** Rejected: it can never show a resolved census and leaves
  the built ER + gold-set + quality-gate machinery permanently dormant; the operator wants depth on the
  real graph. (It is retained as the fallback where ER cannot decide a predicate.)
- **Auto-write everything to "lean auto" maximally.** Rejected: an auto-merged surveillance record that
  is wrong is trust-destroying and asymmetrically costly (a false merge is worse than a false split);
  auto-write must be gated on measured precision, not preference.
- **Human-review everything (no auto-write).** Rejected: it does not scale to ~75k sites and wastes
  human labels where the deterministic cascade is already near-certain; active learning spends review
  where it buys the most precision.
- **Freeze the thresholds as constants now.** Rejected: the holdout is LLM-bootstrapped and provisional;
  hard-coding κ/precision would ossify a provisional measurement — hence `D-R6.1-EVAL`.

## Revisit trigger

- **Real human-labelled ground truth exists** — field-verified sites, contributor-verified matches, or a
  substantially larger human-adjudicated holdout: re-estimate P/R/R on a *human* holdout, re-tune the
  floor and tier cutoffs against it, and close `D-R6.1-EVAL` in a **new ADR** (SIG-ENG-003), never a
  silent threshold edit.
- **A measured floor is missed** — holdout precision drifts below `auto_write_precision_threshold`, or
  LLM-vs-human κ falls below `0.7` (e.g. the adjudicator model drifts): `demote_auto_write_tiers` fires
  and the tier is demoted to review; a persistent miss re-opens the balance decision.
- **A decision-theoretic loss replaces pairwise precision** — if the asymmetric cost of a false merge in
  a surveillance-accountability record warrants optimizing an explicit loss rather than pairwise P/R,
  reconsider the objective (part of `D-R6.1-EVAL`).
- **The connector-registered `camera_*` predicates gain ontology registration** — the §29 resolver can
  then decide them directly; reconsider the shaping-vs-materialize boundary.
