# ADR-105 — Geospatial camera-site entity resolution: the resolved-site unit, geo blocking, tiered same-device rules, and a measured auto-write gate

- **Status:** Accepted
- **Phase / ticket:** Phase 30 / P30.2b (`docs/tickets/P30.2b__geospatial-camera-site-resolution.md`) — Round 8 `GO-LIVE.2b`, inserted 2026-09-24 ("Fix resolution first, then launch"); the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** ADR-005 (resolution is a stored decision), ADR-099 (materialize resolution at scale with a measured eval loop — this ADR is its camera-site instance), ADR-101 (the surface reads the materialized graph), ADR-103 (`sig_materialize`, in-GCP execution), ADR-104 (camera predicates; its revisit trigger (a) fires here); spec §14.6–14.7 (SIG-IDENT-020/023/024/025/027/028/029), §27 (SIG-RECON-001/002), §19.4, §32; deferrals **D-P30.2-3** (closed here — both halves done), **D-R6.1-EVAL** (first-principles half stays OPEN), **D-P30.2b-1 / -2 / -3** (opened here); backlog home **BL-057**.

## Context

P30.2a registered the camera predicates, so §28 wrote 1,872,344 envelopes and every one of the 230,330
hosted camera records has a value-resolved coordinate. That is **value resolution within one source's
record**, not deduplication: every hosted camera subject is one source's row
(`traffic_camera:<source>:<target>:<ref>`), and nothing ever joined two records of one physical device.
`exports.spine_export.resolved_sites_metric` nonetheless counted *any* winning value decision as a
"resolved site (deduplicated from observations)" — over the hosted graph it would have published
N ≈ M = 230,330 "resolved sites". The existing ER (cascade + Splink) blocks only on organisation names and
state; it has no geospatial capability.

A read-only pull of the hosted spine (2026-09-24, 230,330 records with a coordinate pair, 180+ sources)
measured real cross-source overlap: 6,779 cross-source pairs within 1 m (mostly republished copies — e.g.
three Maryland CHART layers, a PennDOT layer republished twice by a university account, Nottingham CCTV
republished by a community layer, NZTA republished with shared row numbers), a long tail at 5–50 m (OSM
nodes near DOT cameras), and 36,437 **same-source** pairs within 1 m (poles and intersections carrying
several cameras, and registries with coarse coordinates).

## Decision

1. **The unit and the metric.** An *observation-level record* is one source's row for one camera; a
   **resolved site** is a cluster of records judged to be the **same physical device**. M = records (subjects
   with a `camera_latitude`/`camera_longitude` claim), N = post-ER clusters (singletons included), N ≤ M,
   dedup ratio = 1 − N/M. `resolved_sites_metric` is redefined over the latest *completed* camera-site ER
   run's **auto-written** same-device edges (union-find over the export's own sites), labelled "resolved sites
   (clusters of observation-level records of the same device)", valued "N resolved sites (from M
   observation-level records; dedup ratio r)", denominated in M, with the auto-written/proposed merge counts
   and the PROVISIONAL disclosure in its population note. With no completed run it returns `None` (the
   observation framing stays). A §28 value decision is never counted (test-pinned).

2. **Geospatial blocking** (`blocking_rules.toml [[geo_rule]] camera_geo_grid`, `blocking.GeoGridRule`):
   same or neighbouring 0.0005° lat × 0.0016° lon cell, *different source*; the cell provably covers the
   50 m candidate radius up to |lat| 73° (the rule refuses an undersized cell); null-island/out-of-range/polar
   points are unblockable singletons. Sized against the existing 1,000,000 ceiling (hosted: 30,360 pairs).
   Blocking only proposes (SIG-IDENT-024).

3. **Tiers** (`camera_site_rules.toml` v2, mapped onto §14.6): **1g shared upstream ref** (normalised refs
   equal within 50 m, no record of the other source *strictly* nearer on either side — a tie at one point is
   resolved by the shared ref and the next condition, never by record order — and, unless the site
   descriptions agree, each the other's only counterpart within 5 m); **3g coincident point** (≤ 1 m, one-to-one within 5 m);
   **4g proximate & unique** (≤ 25 m, mutual nearest with no distance tie, one-to-one within 25 m); **5g proximate candidate**
   (≤ 25 m, or mutual nearest ≤ 50 m); else tier 6 (no per-pair record). Tiers 1g/3g are the only
   *candidate* auto-write tiers; 4g/5g are always PROPOSED (SIG-IDENT-020). Every decision records
   `match_tier`, `tier_label` and machine-readable `match_evidence` (SIG-IDENT-025).

4. **Hard constraints (test-pinned).** (a) Two records of the same source are never a candidate, and never
   merged *transitively*: constrained union-find refuses any union that would put two records of one
   source in a cluster (the refused edge is proposed with `cluster_constraint:same_source`). (b) Recorded
   device classes (source/operator/explicit-type rules; ALPR vs traffic/CCTV incompatible) are never
   candidates; soft
   conflicts — differing resolved jurisdiction, explicit device type, or viewing directions > 90° apart —
   never auto-write. (c) Mirror lineages are inferred each run (≥ 20 coincident records covering ≥ 50% of
   the smaller source); a cluster's `independent_lineages` counts lineages, so a mirror is never
   independent corroboration. Clusters are also bounded (span ≤ 50 m, ≤ 6 members); cluster-shape alerts
   (elongated chain, oversized, single bridge, same-source) demote an alerted cluster's edges to review.

5. **Measured auto-write gate (ADR-099 loop).** Each run scores the candidate tiers against the committed
   gold set's frozen, **agent/maintainer-verified** holdout, *strictly* (a pair the verifier labels
   `not_enough_information` counts against the tier — an unverifiable merge is not a verified merge), and
   only a tier with at least 50 holdout pairs (`min_holdout_pairs`) and precision ≥ the published 0.98 floor
   auto-writes; silence, or a 1-of-1 "1.000", never auto-writes. The LLM adjudicator's labels are reported as a sensitivity figure, never used to gate.
   Gold set `camera-2` (`resolution/data/camera_site_gold.json`, coordinate-free): 540 pairs, each
   double-adjudicated blind to the matcher's tier (agent seed + an LLM adjudicator run in a fresh context
   that saw only the written rules and the evidence sheet). **Rules v1** measured tier 1g at 0.882 and 3g at
   0.929 on the v1 holdout (both demoted); that holdout was then inspected while diagnosing, so it was
   **retired to training**, rules v2 were derived from training-partition errors only (shared-ref
   ambiguity at co-located points; opposed viewing directions), and v2 was measured **once** on a fresh
   180-pair holdout drawn after the change: **1g 70/70 = 1.000** (Wilson 95% lower 0.948), **3g 69/70 =
   0.986** (lower 0.923), 4g 0.300, 5g 0.250 (0.263 on 19 pairs once distance ties fail proximity mutual-nearest). κ (LLM vs agent) = **0.669** over the 540 pairs (0.667 on the
   180-pair holdout), below the 0.70 bar, so the LLM is a **suggester only**; the 77 disputed pairs are enqueued for
   human review (active learning). Under the LLM's labels tier 3g would score 0.800: the gap is the LLM
   reading sub-metre offsets between republished copies as "proximity only". The auto-write of 3g
   therefore rests on the agent-verified labels, and that is disclosed.

6. **Append-only materialization** (sqitch `camera_site_resolution`): `camera_site_match` — one row per
   recorded decision per run (tier, evidence, the establishing claim ids, disposition `auto_write` |
   `proposed`, `input_digest` UNIQUE, `left < right`); `camera_site_run` — the run record written **last** as
   the completion marker (M, N ≤ M CHECK, measured auto-write tiers, eval summary); proposals are enqueued
   once per pair in `review_item`. The run key digests every decision input — the resolver version, the full
   rules content, the gold set's content, the measured auto-write tiers and every field of every record
   (source, coordinates, reference, name, direction, operator, jurisdiction, type, claim ids) — so an
   unchanged re-run is +0 and ANY change a decision could depend on mints a new run that readers take whole,
   never a union with a stale run's edges. The run summary also splits multi-record sites into
   independently corroborated (≥ 2 lineages) vs one-lineage-only (mirror copies), so (c) is reported, not
   only enforced. `sig_materialize` gains INSERT on these three tables only. Entities are
   never merged or updated: clusters are a decision layer over per-source subjects.

7. **Coordinates are never mixed.** Every published point stays one record's own (the map keeps one asset
   per record); any future cluster point must come from `representative_point` (both axes from ONE member,
   never an average). ADR-104's joint-coordinate condition is met by construction, and its
   `authoritative_source_wins` identifier choice stays correct because identifiers remain per-record.

## Consequences

- The public "resolved sites" figure becomes a measured dedup: see the P30.2b run ledger and
  `docs/build/reports/p30.2b-hosted/resolution_scale.json` for the hosted M / N / ratio, and
  `P28.1_resolution_eval.md` for the regenerated eval. Measured in GCP on the reviewed code (`sig-materialize-fh2bh`, image
  `materialize-7db63484444f`; +0 re-run `sig-materialize-wrxns`): **M 230,330 → N 227,998, dedup ratio
  0.0101** (2,332 merges from 2,337 auto-written decisions — 1g 1,089 + 3g 1,248; 11,235 proposed; 0
  cluster-shape alerts; 273 multi-record sites span ≥ 2 independent lineages, 2,054 are copies within one
  lineage). A first pass on the pre-review code (`sig-materialize-l2frp`, N 227,999) stays as append-only
  history under its own run key. It is small (≈ 1% of records merge), because most
  records have no cross-source counterpart and every uncertain candidate goes to review; that is reported,
  not inflated.
- A limitation of "latest completed run": if the spine ever returned to exactly an earlier input state (e.g.
  a retraction making an older claim current again), that input's run key already exists, no new run row is
  written, and the reader keeps the newer run as "latest" until the next real change. Append-only claim ids
  make this rare; a per-execution completion row would remove it (revisit trigger (g)).
- ~11.5k proposed merges enter `review_item` (tiers 4g/5g, soft conflicts, refused unions, disputed gold
  pairs). Accepting them does not yet feed clustering — D-P30.2b-1.
- The eval stays PROVISIONAL (D-R6.1-EVAL): the holdout is agent-verified, not field-verified; the κ bar was
  missed; the tier-3g figure is sensitive to the adjudicator's reading of "identical coordinates".
- Known gaps recorded, not guessed: a police-CCTV vs traffic-camera conflict visible only in a site name,
  and coincident points whose descriptions name different places, were seen in the retired v1 holdout; the
  v2 rules deliberately do not encode them (holdout discipline) — D-P30.2b-2. A source that republishes
  its own layer twice (e.g. two identical targets under one source id) is not deduplicated within itself
  (constraint (a) is absolute) — D-P30.2b-3.

## Alternatives considered

- **Keep counting value decisions** as resolved sites. Rejected: it publishes N ≈ M as dedup — false.
- **Merge subjects into one entity** (`entity.merged_into`, a new canonical subject). Rejected: needs
  UPDATEs or a new entity per cluster with re-pointed claims; clusters as a separate append-only decision
  layer keep every source's record and its provenance intact and make a re-cluster a new run (SIG-RECON-002).
- **Splink on coordinates.** Rejected for now: without real ground truth its weights would be tuned on the
  same provisional labels; deterministic tiers with a measured gate are auditable and sufficient for the
  coincident/shared-ref duplicates that dominate the overlap.
- **Tune rules until the v1 holdout passes.** Rejected: that measures nothing. v2 was derived from training
  errors and measured on a fresh holdout.
- **Gate on LLM labels or on consensus labels.** Rejected: κ < 0.70 means the LLM is not trusted as gold,
  and consensus would silently drop the disputed pairs from the precision they govern.
- **Proximity-only auto-merge (e.g. ≤ 10 m).** Rejected: measured tier 4g precision is 0.300 — co-located
  devices and nearby unrelated nodes dominate.

## Revisit trigger

Revisit when any of: (a) human review decisions on the queued proposals accumulate (D-P30.2b-1) — feed
accepted merges into clustering and re-measure the tiers on a new holdout version; (b) the per-run
measurement drops a tier below the 0.98 floor (it auto-demotes; a persistent miss re-opens the rules); (c)
field-verified or contributor-verified ground truth exists or κ is re-measured with a stronger adjudicator
(D-R6.1-EVAL); (d) new sources change the overlap shape (e.g. a large source with coarse coordinates, or a
new mirror family) or a cluster-shape alert fires; (e) the site-name/device-kind conflicts of D-P30.2b-2
are encoded; (f) a published surface needs one point per resolved site (use `representative_point`); (g) a spine
state can recur (retraction-driven) often enough that "latest completed run" needs a per-execution
completion record.
