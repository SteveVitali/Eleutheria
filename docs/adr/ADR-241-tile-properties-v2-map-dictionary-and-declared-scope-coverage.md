# ADR-241 — Tile properties v2, the `sig.map-dict/1` dictionary, and the declared-scope coverage rule

- Date: 2026-11-08
- Status: accepted
- Ticket: P37.17 (Round 11 / P37, row 440; SIG-GEO-014, SIG-UI-099)
- Base: `r11/P37.16b-dossier-live-captures-last-two-families`
- Related: K1 MAP-01b §3.3 (the `sig.map-tiles/2` contract), D-K1-4 [B-22]
  = yes (the declared-scope coverage verdict — implemented verbatim,
  never re-decided), `sig.map-dict/1` and `sig.jurisdiction-coverage/1`,
  ADR-156/P35.52 (the tile pipeline this completes), ADR-134/ADR-155 (the
  map island budget posture), L3 CONF-07b (`n_independent_lineages` —
  the interim `st` rule this keeps honest), UXR-14 (carried as a
  later-family draft).

## Context

K1 MAP-01b completes the tile contract P35.52/ADR-156 opened: the §3.3 short keys (`lb`, `tc`, `vd`, `op`/`oe`, `sr`, `j`, `f`/`l`, `st`, `pm`, `co` on sites; `t_<code>`, `v_<slot>`, `s1`, `sx` facet counts on cells) plus `web/map/dict.json` and `web/map/coverage_by_jurisdiction.json`. The `st` status counts **registry sources** until L3 CONF-07b ships `n_independent_lineages`; the legend reads the UXR-14 verbatim "2+ source records; republications not yet collapsed" (K13 C-06).

## Decision

1. **Slice merge.** Per-(record, source) slice rows sharing one published point merge into ONE drawn feature (`rk` links one record page — never a stack of identical markers); slices resolving to different points keep their honest disagreement as separate features. `n` on cells counts merged (record, position) units.
2. **`st` precedence:** contested (2, open contradiction on location or type) > provisional (3, candidate lifecycle) > corroborated (0, ≥ 2 registry sources) > single-source (1). `s1`/`sx` on cells are the single-source vs rest counts (`s1 + sx = n`).
3. **Dictionary.** `dict.json` (`sig.map-dict/1`, CC-BY-4.0) binds `sr` → `(source_id, compartment)` index, `tc` → active-ontology-slug code in `technology.yaml` order (0 = unclassified, retired never coded), `vd` → top-8 vendors by record count + 9 "other" + 0 "unknown", jurisdiction chains + bboxes for `j`/`jp` keys in use, per-jurisdiction unplotted counts (tier 3 + no point), and row-level facet totals (never a census).
4. **Coverage rule `declared-scope@1`** (D-K1-4 (b)): a source covers a jkey when its declared `sources.toml` `jurisdiction_scheme` + `jurisdiction` maps to the jkey or an ancestor; `publisher_type = "crowdsourced"` or scope-less sources are listed under `observed_sources`/`global_sources_not_counted` but never count as "looked". Counts in single-source cells stay visible (D-K1-4 (a)).
5. New site-row columns (`first_seen`, `last_seen`, `operator_label`, `operator_key`, `vendor_label`, `vendor_key`, `point_uncertainty_m`, `lifecycle`) are additive and nullable; `pm` derives from the tier's declared uncertainty (tier 1 → 1,113 m truncation step; tier 2 → 1,000 m grid bin).

## Consequences

- Tile size grows modestly; the verifier's property allowlist already admitted every key.
- `web/map/dict.json` and the real `coverage_by_jurisdiction.json` join the release's CC-BY-4.0 metadata compartment; dossier-figure children draw `covered`/`not_covered` instead of `rule_pending` when the rule is bound.

## Revisit trigger

1. L3 CONF-07b ships — `st` switches to `n_independent_lineages` and the UXR-14 interim legend retires.
2. A declared-scope grammar beyond `jurisdiction_scheme`/`jurisdiction` lands (e.g. multi-key scopes, `jurisdiction_place` geoid resolution).
3. The `s1`/`sx` split or the vendor top-8 slot count proves inadequate for the filters' needs.
