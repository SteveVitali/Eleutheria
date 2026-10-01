<!-- Generated 2026-10-01T17:13:33Z by docs/build/planning/2026-09-30-next-phase/tools/s13e/req_index.py (SEED-13e, Round-11 Stage B T3 close-out); regenerate, do not hand-edit. Planning, not execution evidence. -->
# Round-11 requirement → ticket index (rows 201–510)

A companion of `00_MANIFEST.md` (its `## Requirement-ID → ticket index` points here). It maps every requirement id cited by the 310 Round-11 chain contracts — the 60 full 11A contracts and the 250 `Kind: skeleton` contracts of 11B–tail — to the rows that own, deliver, extend or cite it, checks the 62 spec §56 ids against their `Owner:` lines, and lists every waived or amended id with its ADR (spec Appendix G.7). Skeleton rows name only the ids the plan row, the catalog or a Stage-B carry item gave them; **PLAN-11B, PLAN-11C and PLAN-11D extend this index** when they write their sub-round's contracts (re-run the generator; their own requirement-index deliverables point here). Requirement status stays in `docs/build/COVERAGE_MATRIX.csv` and the coverage-assessment events — nothing here is a verdict.

**Roles.** *owner* — the spec §56 `Owner:` row or a contract's `Owner` bullet; *delivers* — a contract's `Satisfied`/`Met at`/`Public layer reached`/`Re-verdicted` bullet (part of the requirement, at the layer the contract states); *also* — §56 `Also:` or the contract's `Also` bullet; *cited* — any other requirement bullet; *mentioned* — the id appears elsewhere in the contract. Rows are written `<id> (<row>)`.

## Summary

- Contracts scanned: **310** (60 full, 250 skeleton).
- Distinct requirement ids cited: **162** — 61 of the 62 §56 ids and 101 ids defined before Round 11. §56 ids no contract cites: SIG-ENG-044 (seed-owned; see §1).
- §56 ids with **no chain-row owner**: 4 — SIG-ENG-041 (owner SEED-15), SIG-ENG-044 (owner SEED-02), SIG-MEM-005 (owner SEED-02), SIG-MEM-012 (owner SEED-02) — owned by Stage-B seed units, not by a Round-11 row (spec §56.1 allows a seed-unit owner); they are verdicted at T4/T6 from the seed's own evidence.
- §56 owner names that are not chain rows: 0.
- §56 owner rows whose contract does not (yet) list the id as owned: 0.
- Ids defined before Round 11 that no Round-11 row owns or delivers (cited only): 88 — their owners are the tickets the coverage matrix names (column *matrix `owning_tickets`* in §3, read at HEAD).
- Appendix G.7: 16 waived ids (G.7.2), 29 amended ids (G.7.3, incl. the outreach set owed later-phase, R11-A15), 18 ids checked and deliberately not amended (G.7.5; the requirement stands) — table §2.

## 1. Spec §56 ids (62) — owner check

| id | level | §56 Owner | §56 Also | owner contract lists it | other Round-11 rows | flag |
|---|---|---|---|---|---|---|
| SIG-CONF-001 | MUST | P34.45 (257) | P37.45 (469) | yes | P37.45 (469) also; P34.44a (255) cited | — |
| SIG-CONF-002 | MUST | P35.48 (327) | — | yes | — | — |
| SIG-CONF-003 | MUST | P34.44a (255) | — | yes | — | — |
| SIG-CONF-004 | MUST | P35.46 (325) | P37.46a (470), P37.46b (471) | yes | P37.46a (470) also; P37.46b (471) also | — |
| SIG-CONF-005 | MUST | P35.47 (326) | P34.45 (257) | yes | P34.45 (257) also | — |
| SIG-CONF-006 | MUST | P34.44a (255) | — | yes | P34.44b (256) cited | — |
| SIG-CONF-007 | MUST | P34.44a (255) | — | yes | P34.44b (256) cited | — |
| SIG-CONF-008 | MUST | P35.23 (348) | — | yes | — | — |
| SIG-CONF-009 | MUST | P35.34 (312) | P34.44a (255), P34.44b (256) | yes | P34.44a (255) also; P34.44b (256) also | — |
| SIG-CONF-010 | MUST | P35.60 (337) | P37.45 (469) | yes | P37.45 (469) also; PLAN-11B (239) cited | owner was an agent assignment (T1 map 'confirm at T3/T4'); confirmed at T3 — agent reading, the PLAN row re-confirms when it writes the contract |
| SIG-CONF-011 | MUST | P37.45 (469) | P37.39 (463) | yes | P37.39 (463) also | — |
| SIG-CONF-012 | MUST | P37.44 (468) | P34.47 (259), P38.1a (501), P38.1b (502) | yes | P34.47 (259) also; P38.1a (501) also; P38.1b (502) also; P34.45 (257) cited | — |
| SIG-CONF-013 | MUST | P34.43 (253) | — | yes | P34.44a (255) cited; P34.44b (256) cited | — |
| SIG-CONF-014 | SHOULD | P35.25 (304) | — | yes | — | — |
| SIG-ENG-040 | MUST | P34.31 (236) | SEED-03 | yes | P34.1 (201) cited; P34.22b (226) cited; P34.34b (242) cited | — |
| SIG-ENG-041 | MUST | SEED-15 | P34.33 (238) | seed unit | P34.33 (238) also; PLAN-11B (239) cited; P34.48 (240) cited | no chain-row owner (seed unit) |
| SIG-ENG-042 | MUST | P34.9 (211) | SEED-02 | yes | P34.2 (202) cited; P34.4 (205) cited; P34.7 (209) cited; P34.20 (222) cited; P34.29 (234) cited; P34.39a (247) cited; P34.39b (248) cited; P34.44a (255) cited; P34.1 (201) mentioned; P34.22a (225) mentioned; P34.32 (237… | — |
| SIG-ENG-043 | MUST | P34.32 (237) | SEED-15 | yes | — | — |
| SIG-ENG-044 | MUST | SEED-02 | SEED-03 | seed unit | — | no chain-row owner (seed unit) |
| SIG-ENG-045 | MUST | P34.24a (228) | — | yes | P34.6 (207) cited; P34.7 (209) cited; P34.22a (225) cited; P34.24b (230) cited | — |
| SIG-ENG-046 | MUST | P34.1 (201) | — | yes | P34.2 (202) cited | — |
| SIG-MEM-005 | MUST | SEED-02 | P34.8 (210), P34.22a (225), P34.22b (226) | seed unit | P34.8 (210) also; P34.22a (225) also; P34.22b (226) also; P34.7 (209) cited; P34.24a (228) cited; P34.39a (247) cited | no chain-row owner (seed unit) |
| SIG-MEM-006 | MUST | P34.7 (209) | SEED-02, P34.27 (232) | yes | P34.27 (232) also; P34.30 (235) cited | — |
| SIG-MEM-007 | MUST | P34.2 (202) | SEED-02 | yes | P34.1 (201) cited; P35.38a (203) mentioned; P34.3 (204) mentioned; P34.4 (205) mentioned; P34.5 (206) mentioned; P34.6 (207) mentioned; P34.50 (208) mentioned; P34.7 (209) mentioned; P34.8 (210) mentioned; P34.9 (211) m… | — |
| SIG-MEM-008 | MUST | P34.28 (233) | SEED-02 | yes | — | — |
| SIG-MEM-009 | MUST | P34.28 (233) | SEED-02 | yes | P34.27 (232) cited | — |
| SIG-MEM-010 | MUST | P34.9 (211) | SEED-10, P34.29 (234) | yes | P34.29 (234) also; P34.1 (201) mentioned; P34.2 (202) mentioned; P35.38a (203) mentioned; P34.3 (204) mentioned; P34.4 (205) mentioned; P34.5 (206) mentioned; P34.6 (207) mentioned; P34.50 (208) mentioned; P34.7 (209) m… | — |
| SIG-MEM-011 | MUST | P35.3 (292) | — | yes | P34.17 (220) cited; P34.33 (238) cited; P34.39a (247) cited; P34.39b (248) cited; P34.47 (259) cited | — |
| SIG-MEM-012 | MUST | SEED-02 | P34.9 (211) | seed unit | P34.9 (211) also; P34.1 (201) cited | no chain-row owner (seed unit) |
| SIG-OPS-001 | MUST | P34.6 (207) | — | yes | P34.46 (258) cited | — |
| SIG-OPS-002 | MUST | P34.3 (204) | — | yes | P34.6 (207) cited | — |
| SIG-OPS-003 | MUST | P34.10 (212) | — | yes | P34.17 (220) cited; P34.21b (224) cited; P34.40 (249) cited; P34.11 (213) mentioned | — |
| SIG-OPS-004 | MUST | P34.10 (212) | — | yes | P34.17 (220) cited; P34.21a (223) cited; P34.21b (224) cited | — |
| SIG-OPS-005 | MUST | P35.1a (264) | — | yes | P34.42a (251) cited; P34.42b (252) cited | — |
| SIG-OPS-006 | MUST | P35.2 (346) | P34.4 (205) | yes | P34.4 (205) also; P34.50 (208) cited; P34.39b (248) cited; P34.44b (256) cited | — |
| SIG-OPS-007 | SHOULD | P35.2 (346) | — | yes | P34.4 (205) mentioned; PLAN-11C (340) mentioned | owner was an agent assignment (T1 map 'confirm at T3/T4'); confirmed at T3 — agent reading, the PLAN row re-confirms when it writes the contract |
| SIG-OPS-008 | MUST | P36.44 (387) | — | yes | — | — |
| SIG-OPS-009 | MUST | P34.5 (206) | — | yes | — | — |
| SIG-OPS-010 | SHOULD | P35.4 (293) | — | yes | P34.50 (208) cited | — |
| SIG-OPS-011 | MUST | P35.3 (292) | — | yes | P34.39a (247) cited; P34.39b (248) cited; P34.43 (253) cited; P34.44b (256) cited; P34.47 (259) cited | — |
| SIG-OPS-012 | MUST | P35.3 (292) | — | yes | P35.38a (203) cited | — |
| SIG-REL-001 | MUST | P35.12 (294) | — | yes | — | — |
| SIG-REL-002 | MUST | P35.12 (294) | — | yes | — | — |
| SIG-REL-003 | MUST | P35.12 (294) | — | yes | — | — |
| SIG-REL-004 | MUST | P35.53 (331) | — | yes | P34.10 (212) cited; P34.40 (249) cited | — |
| SIG-REL-005 | MUST | P35.53 (331) | — | yes | — | — |
| SIG-REL-006 | MUST | P35.54 (332) | — | yes | P34.40 (249) cited | — |
| SIG-REL-007 | MUST | P35.58 (335) | P35.56 (334) | yes | P35.56 (334) also | — |
| SIG-REL-008 | MUST | P36.66b (410) | P35.65 (314) | yes | P35.65 (314) also; P34.34a (241) mentioned | — |
| SIG-REL-009 | MUST | P35.13 (295) | — | yes | P34.10 (212) cited | — |
| SIG-REL-010 | MUST | P35.57 (261) | P34.25 (229) | yes | P34.25 (229) also; P34.45 (257) cited; P34.46 (258) cited | — |
| SIG-REL-011 | MUST | P36.44 (387) | — | yes | — | — |
| SIG-REL-012 | MUST | P35.60 (337) | — | yes | GATE-G4 (260) cited | — |
| SIG-REL-013 | MUST | P35.55 (333) | — | yes | P34.41 (250) cited | — |
| SIG-REL-014 | MUST | P34.23 (227) | — | yes | — | — |
| SIG-REL-015 | MUST | P36.50 (393) | — | yes | P34.28 (233) mentioned | — |
| SIG-SEC-007 | MUST | P34.42a (251), P34.42b (252) | — | yes | P34.40 (249) cited; P34.43 (253) cited | — |
| SIG-SEC-008 | MUST | P35.1a (264), P35.1b (291) | — | yes | PLAN-11B (239) cited | owner was an agent assignment (T1 map 'confirm at T3/T4'); confirmed at T3 — agent reading, the PLAN row re-confirms when it writes the contract |
| SIG-SEC-009 | SHOULD | P35.4 (293) | — | yes | PLAN-11B (239) cited; P34.42a (251) cited; P34.42b (252) cited | owner was an agent assignment (T1 map 'confirm at T3/T4'); confirmed at T3 — agent reading, the PLAN row re-confirms when it writes the contract |
| SIG-SEC-010 | MUST | P34.28 (233) | — | yes | GATE-G4 (260) cited | — |
| SIG-SEC-011 | MUST | P34.25 (229) | — | yes | P34.43 (253) cited; P34.46 (258) cited | — |
| SIG-STORE-048 | MUST | P37.3 (421) | P34.3 (204) | yes | P34.3 (204) also; P34.42b (252) cited | — |

## 2. Waived and amended ids (spec Appendix G.7) and the Round-11 rows that touch them

A waived clause keeps its requirement text and a dated waiver note in its owning section; the coverage verdict is `WAIVED(ADR)` for the clause only (SIG-ENG-041). An amendment adds and removes no obligation; a G.7.5 item was checked and deliberately not amended (a draft that would weaken a MUST was withheld) — the requirement stands as written.

| id | G.7 row | disposition | ADR | Round-11 rows (role) |
|---|---|---|---|---|
| SIG-CHART-025 | R11-A1 | AMENDED (no MUST weakened) | ADR-172 | — |
| SIG-CHART-033 | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned; P34.48 (240) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-CONTRIB-012 | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-CONTRIB-012a | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned |
| SIG-CONTRIB-013 | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned |
| SIG-DOS-002 | G.7.5 | checked, not amended — the requirement stands | — | P34.35 (243) cited |
| SIG-ENG-004 | G.7.5 | checked, not amended — the requirement stands | — | P34.48 (240) cited |
| SIG-ENG-031 | R11-A16 | AMENDED (no MUST weakened) | none — authority: DRAFT-ENG-5 (B4 §5) | P34.33 (238) cited |
| SIG-ENG-039 | R11-A17 | AMENDED (no MUST weakened) | none — authority: DRAFT-ENG-4 (B4 §5); F-32 | P34.32 (237) delivers |
| SIG-EVAL-001 | G.7.5 | checked, not amended — the requirement stands | — | P34.45 (257) cited |
| SIG-EVAL-002 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-EVAL-004 | R11-W1 | WAIVED (clause): the preregistered 0.98 lower-bound clause, for the derivation-collapse tiers C0–C2 only; inferential tiers stay review-only (met fai… | ADR-153 | P34.45 (257) cited; P35.46 (325) mentioned; P38.2 (503) mentioned |
| SIG-EVAL-005 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-EVAL-005 | R11-A10 | AMENDED (no MUST weakened) | ADR-152, ADR-153 | — |
| SIG-EVAL-006 | R11-A10 | AMENDED (no MUST weakened) | ADR-152, ADR-153 | P34.45 (257) cited; P37.44 (468) mentioned |
| SIG-EVAL-007 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-EVAL-007 | R11-A10 | AMENDED (no MUST weakened) | ADR-152, ADR-153 | — |
| SIG-EVID-009 | R11-A7 | AMENDED (no MUST weakened) | ADR-162 | — |
| SIG-EXPORT-002 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-EXPORT-012 | R11-A8 | AMENDED (no MUST weakened) | ADR-099, ADR-101 | — |
| SIG-GOV-001 | R11-W2 | WAIVED (clause): SIG-GOV-001's one-click clause and all of SIG-GOV-002, for Round 11 (e-mail intake; senders disclose their address) | ADR-180 | P34.17 (220) cited; P34.37 (245) cited |
| SIG-GOV-002 | R11-W2 | WAIVED (clause): SIG-GOV-001's one-click clause and all of SIG-GOV-002, for Round 11 (e-mail intake; senders disclose their address) | ADR-180 | P34.17 (220) cited; P34.37 (245) cited |
| SIG-GOV-003 | R11-W3 | WAIVED (clause): the response-time (SLA) clause; the priority clause is met differently by the published handling order | ADR-186 | P34.17 (220) cited; GATE-ANNOUNCE (510) mentioned |
| SIG-GOV-008 | R11-W4 | WAIVED (clause): the two-person clause; the scope and tombstone clauses stand | ADR-181 | P34.49 (254) cited; P37.71 (429) mentioned |
| SIG-GOV-012 | R11-W5 | WAIVED (clause): a legal home before launch and retained legal-defence resources, "for now" (an individual legal home, disclosed) | ADR-165 | P34.16 (218) cited; P34.17 (220) cited |
| SIG-GOV-013 | R11-W5 | WAIVED (clause): a legal home before launch and retained legal-defence resources, "for now" (an individual legal home, disclosed) | ADR-165 | P34.16 (218) cited; P34.17 (220) cited |
| SIG-GOV-015 | R11-W6 | WAIVED (clause): the editorial board (interim single-maintainer authority + public decision log) | ADR-164 | P34.16 (218) cited |
| SIG-GOV-017 | G.7.5 | checked, not amended — the requirement stands | — | P37.72 (442) mentioned; P37.19 (443) mentioned |
| SIG-GOV-024 | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned |
| SIG-IDENT-027 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-IDENT-028 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-IDENT-028 | R11-A9 | AMENDED (no MUST weakened) | ADR-153 | — |
| SIG-INGEST-004 | G.7.5 | checked, not amended — the requirement stands | ADR-121 | PLAN-11B (239) mentioned; P35.34 (312) mentioned |
| SIG-INGEST-029 | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-INGEST-030a | R11-A15 | owed later-phase, not waived (outreach timing) | ADR-171 | PLAN-11B (239) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-INGEST-035 | R11-W11 | WAIVED (clause): the no-direct-capture clause, for Flock transparency portals, probe-only; the aggregator-source and compartment clauses stand | ADR-188 | P36.74 (289) mentioned; P36.75 (385) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-INGEST-036 | R11-A14 | AMENDED (no MUST weakened) | ADR-168, ADR-184 | P35.38a (203) delivers; P34.38 (246) cited; P36.74 (289) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-INGEST-036 | R11-W10 | WAIVED (clause): "ask first", for DocumentCloud/MuckRock only; rules 1–5, 7 and 8 bind every source | ADR-187 | P35.38a (203) delivers; P34.38 (246) cited; P36.74 (289) mentioned; P36.77 (352) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-INGEST-037 | R11-A14 | AMENDED (no MUST weakened) | ADR-168, ADR-184 | P34.16 (218) cited; P36.74 (289) mentioned |
| SIG-INGEST-037 | R11-W9 | WAIVED (clause): the counsel-referral and counsel-requiring clauses; SIG-LIC-009's risk-register clause and SIG-INGEST-037's ADR-level-decision claus… | ADR-182 | P34.16 (218) cited; P36.74 (289) mentioned |
| SIG-INGEST-046c | R11-A14 | AMENDED (no MUST weakened) | ADR-168, ADR-184 | P34.38 (246) cited; P34.19 (219) mentioned; P36.1a (265) mentioned; P36.1b (349) mentioned |
| SIG-LIC-004 | R11-A12 | AMENDED (no MUST weakened) | ADR-167, ADR-169, ADR-183 | P34.19 (219) cited; P36.2 (350) mentioned |
| SIG-LIC-006 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-LIC-009 | R11-W9 | WAIVED (clause): the counsel-referral and counsel-requiring clauses; SIG-LIC-009's risk-register clause and SIG-INGEST-037's ADR-level-decision claus… | ADR-182 | P34.16 (218) cited; P36.2 (350) mentioned; P37.69a (479) mentioned |
| SIG-METRIC-007 | R11-A6 | AMENDED (no MUST weakened) | ADR-162 | — |
| SIG-ONTO-060 | G.7.5 | checked, not amended — the requirement stands | — | PLAN-11B (239) mentioned; P35.14a (272) mentioned |
| SIG-PUB-002 | G.7.5 | checked, not amended — the requirement stands | ADR-185 | P34.18 (221) delivers; P34.21b (224) delivers; P34.26 (231) cited; P34.38 (246) cited; P34.49 (254) cited; P36.74 (289) mentioned; P36.76 (351) mentioned; P36.77 (352) mentioned; P36.78 (353) mentioned; P37.71 (429) mentioned |
| SIG-PUB-003 | G.7.5 | checked, not amended — the requirement stands | ADR-185 | P34.49 (254) cited; P36.76 (351) mentioned |
| SIG-PUB-003a | G.7.5 | checked, not amended — the requirement stands | ADR-185 | P36.74 (289) mentioned |
| SIG-PUB-008 | R11-W7 | WAIVED (clause): the HG-11 second-reviewer role, for Round-11 releases; SIG-PUB-008's naming concurrence stands (nobody is named) | ADR-163 | — |
| SIG-RECON-058 | R11-A8 | AMENDED (no MUST weakened) | ADR-099, ADR-101 | — |
| SIG-SEC-003 | R11-A11 | AMENDED (no MUST weakened) | ADR-166 | P37.8 (428) mentioned |
| SIG-STORE-011 | R11-W12 | WAIVED (clause): append-only, for one operator-only purge function only; every other role and path stays append-only | ADR-189 | P34.18 (221) cited; P34.21a (223) cited; P34.26 (231) cited; P34.49 (254) cited; P34.46 (258) cited; P37.71 (429) mentioned; GATE-ANNOUNCE (510) mentioned |
| SIG-UI-001 | G.7.5 | checked, not amended — the requirement stands | — | — |
| SIG-UI-021 | R11-A2 | AMENDED (no MUST weakened) | ADR-158 | — |
| SIG-UI-022 | G.7.5 | checked, not amended — the requirement stands | ADR-190 | — |
| SIG-UI-022 | R11-A2 | AMENDED (no MUST weakened) | ADR-158 | — |
| SIG-UI-022 | R11-W13 | WAIVED (clause): the default-view clause ("Default view is an ego network with expansion"): the explorer may open on an aggregated overview meeting R… | ADR-190 | — |
| SIG-UI-035 | R11-A4 | AMENDED (no MUST weakened) | ADR-162 | P34.34a (241) mentioned |
| SIG-UI-036 | R11-A3 | AMENDED (no MUST weakened) | ADR-155 | P34.34b (242) mentioned |
| SIG-UI-042 | R11-W8 | WAIVED (clause): the release block; the hostile-reader review stays owed and is recorded "not yet performed" | ADR-179 | P34.17 (220) cited |
| SIG-UI-044 | R11-A5 | AMENDED (no MUST weakened) | none — authority: D-K14-6 (B-22) | P36.17 (357) mentioned |
| SIG-UI-050 | R11-A3 | AMENDED (no MUST weakened) | ADR-155 | P34.15 (217) cited; P34.34b (242) cited; P34.36 (244) cited |

## 3. Full index — every requirement id cited by a Round-11 contract

| id | level | owner / delivering row(s) | also | cited / mentioned by | matrix `owning_tickets` (HEAD; cited-only ids) | G.7 |
|---|---|---|---|---|---|---|
| SIG-ACQ-004 | MUST | — | — | P34.38 (246), P34.35 (243)* | P32.21, P37.16a | — |
| SIG-API-004 | MUST | P34.21a (223) (delivers) | — | — | — | — |
| SIG-CHART-033 | MUST | — | — | PLAN-11B (239)*, P34.48 (240)*, P36.77 (352)*, GATE-ANNOUNCE (510)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-CONF-001 | MUST | P34.45 (257) (§56) | P37.45 (469) | P34.44a (255) | — | — |
| SIG-CONF-002 | MUST | P35.48 (327) (§56) | — | — | — | — |
| SIG-CONF-003 | MUST | P34.44a (255) (§56) | — | — | — | — |
| SIG-CONF-004 | MUST | P35.46 (325) (§56) | P37.46a (470), P37.46b (471) | — | — | — |
| SIG-CONF-005 | MUST | P35.47 (326) (§56) | P34.45 (257) | — | — | — |
| SIG-CONF-006 | MUST | P34.44a (255) (§56) | — | P34.44b (256) | — | — |
| SIG-CONF-007 | MUST | P34.44a (255) (§56) | — | P34.44b (256) | — | — |
| SIG-CONF-008 | MUST | P35.23 (348) (§56) | — | — | — | — |
| SIG-CONF-009 | MUST | P35.34 (312) (§56) | P34.44a (255), P34.44b (256) | — | — | — |
| SIG-CONF-010 | MUST | P35.60 (337) (§56) | P37.45 (469) | PLAN-11B (239) | — | — |
| SIG-CONF-011 | MUST | P37.45 (469) (§56) | P37.39 (463) | — | — | — |
| SIG-CONF-012 | MUST | P37.44 (468) (§56) | P34.47 (259), P38.1a (501), P38.1b (502) | P34.45 (257) | — | — |
| SIG-CONF-013 | MUST | P34.43 (253) (§56) | — | P34.44a (255), P34.44b (256) | — | — |
| SIG-CONF-014 | SHOULD | P35.25 (304) (§56) | — | — | — | — |
| SIG-CONTRIB-012 | MUST | — | — | PLAN-11B (239)*, P36.77 (352)*, GATE-ANNOUNCE (510)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-CONTRIB-012a | SHOULD | — | — | PLAN-11B (239)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-CONTRIB-013 | MUST | — | — | PLAN-11B (239)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-CONTRIB-020 | MUST | P34.21a (223) (delivers), P34.21b (224) (delivers) | — | — | — | — |
| SIG-DOS-001 | MUST | — | — | P34.35 (243) | P32.17 | — |
| SIG-DOS-002 | MUST | — | — | P34.35 (243) | P32.17 | G.7.5 checked, not amended — the requirement stands |
| SIG-ENG-003 | MUST | — | — | PLAN-11B (239) | P18.1 | — |
| SIG-ENG-004 | MUST | — | — | P34.48 (240) | P17.1, P17.2, P17.3 | G.7.5 checked, not amended — the requirement stands |
| SIG-ENG-005 | MUST | — | — | P34.48 (240) | P00.2, P34.48 | — |
| SIG-ENG-012 | MUST | — | — | P34.44a (255)* | P00.1 | — |
| SIG-ENG-031 | MUST | — | — | P34.33 (238) | P06.1 | R11-A16 AMENDED (no MUST weakened) |
| SIG-ENG-039 | MUST | P34.32 (237) (delivers) | — | — | — | R11-A17 AMENDED (no MUST weakened) |
| SIG-ENG-040 | MUST | P34.31 (236) (§56) | — | P34.1 (201), P34.22b (226), P34.34b (242) | — | — |
| SIG-ENG-041 | MUST | SEED-15 (§56) | P34.33 (238) | PLAN-11B (239), P34.48 (240) | — | — |
| SIG-ENG-042 | MUST | P34.9 (211) (§56) | — | P34.2 (202), P34.4 (205), P34.7 (209), P34.20 (222), P34.29 (234), P34.39a (247), P34.39b (248), P34.44a (255), P34.1 (201)*, P34.22a (225)*, P34.32 (237)*, P34.33 (238)* | — | — |
| SIG-ENG-043 | MUST | P34.32 (237) (§56) | — | — | — | — |
| SIG-ENG-045 | MUST | P34.24a (228) (§56) | — | P34.6 (207), P34.7 (209), P34.22a (225), P34.24b (230) | — | — |
| SIG-ENG-046 | MUST | P34.1 (201) (§56) | — | P34.2 (202) | — | — |
| SIG-EVAL-001 | MUST | — | — | P34.45 (257) | P32.9, P34.45 | G.7.5 checked, not amended — the requirement stands |
| SIG-EVAL-003 | MUST | — | — | P37.44 (468)* | P32.10, P37.44 | — |
| SIG-EVAL-004 | MUST | — | — | P34.45 (257), P35.46 (325)*, P38.2 (503)* | P32.10 | R11-W1 WAIVED (clause) — ADR-153 |
| SIG-EVAL-006 | MUST | — | — | P34.45 (257), P37.44 (468)* | P32.23, P37.44 | R11-A10 AMENDED (no MUST weakened) — ADR-152, ADR-153 |
| SIG-EXPORT-006 | MUST | P34.21a (223) (delivers), P34.21b (224) (delivers) | — | P34.18 (221) | — | — |
| SIG-FIND-001 | MUST | — | — | P34.34a (241), P34.40 (249), P34.41 (250) | P32.13 | — |
| SIG-FIND-002 | MUST | — | — | P34.34a (241), P34.40 (249), P34.41 (250) | P32.13 | — |
| SIG-FIND-003 | MUST | — | — | P34.36 (244) | P32.14 | — |
| SIG-FIND-005 | MUST | — | — | P34.34b (242), P34.34a (241)* | P32.15 | — |
| SIG-FIND-006 | MUST | — | — | P34.37 (245), P34.35 (243)* | P32.16, P37.59 | — |
| SIG-FIND-008 | MUST | — | — | P34.37 (245) | P32.16a | — |
| SIG-GOV-001 | MUST | — | — | P34.17 (220), P34.37 (245) | P00.3, P15.5, P34.17 | R11-W2 WAIVED (clause) — ADR-180 |
| SIG-GOV-002 | MUST | — | — | P34.17 (220), P34.37 (245) | P00.3, P15.5, P34.17 | R11-W2 WAIVED (clause) — ADR-180 |
| SIG-GOV-003 | MUST | — | — | P34.17 (220), GATE-ANNOUNCE (510)* | P00.3, P15.5, P34.17 | R11-W3 WAIVED (clause) — ADR-186 |
| SIG-GOV-007 | MUST | — | — | P34.19 (219), P34.41 (250), P34.49 (254), P37.71 (429)* | P00.3, P15.5 | — |
| SIG-GOV-008 | MUST | — | — | P34.49 (254), P37.71 (429)* | P00.3, P15.5, P37.71 | R11-W4 WAIVED (clause) — ADR-181 |
| SIG-GOV-011 | MUST | — | — | P34.37 (245) | P00.3, P15.5 | — |
| SIG-GOV-012 | MUST | — | — | P34.16 (218), P34.17 (220) | P34.16 | R11-W5 WAIVED (clause) — ADR-165 |
| SIG-GOV-013 | MUST | — | — | P34.16 (218), P34.17 (220) | P34.16 | R11-W5 WAIVED (clause) — ADR-165 |
| SIG-GOV-014 | MUST | — | — | P34.16 (218) | — | — |
| SIG-GOV-015 | MUST | — | — | P34.16 (218) | P34.16 | R11-W6 WAIVED (clause) — ADR-164 |
| SIG-GOV-017 | MUST | — | — | P37.72 (442)*, P37.19 (443)* | — | G.7.5 checked, not amended — the requirement stands |
| SIG-GOV-024 | MUST | — | — | PLAN-11B (239)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-IDENT-030 | MUST | — | — | P34.15 (217) | P15.3, P34.15 | — |
| SIG-INGEST-004 | MUST | — | — | PLAN-11B (239)*, P35.34 (312)* | P35.34 | G.7.5 checked, not amended — the requirement stands — ADR-121 |
| SIG-INGEST-011 | MUST | — | — | P35.38a (203) | P07.2 | — |
| SIG-INGEST-013 | MUST | — | — | P36.74 (289)* | — | — |
| SIG-INGEST-025a | MUST | — | — | P37.14 (436)* | P37.14 | — |
| SIG-INGEST-025b | MUST | — | — | P37.14 (436)* | P37.14 | — |
| SIG-INGEST-025c | MUST | — | — | P37.14 (436)* | P37.14 | — |
| SIG-INGEST-029 | MUST | — | — | PLAN-11B (239)*, P36.77 (352)*, GATE-ANNOUNCE (510)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-INGEST-030a | MUST | — | — | PLAN-11B (239)*, P36.77 (352)*, GATE-ANNOUNCE (510)* | — | R11-A15 owed later-phase, not waived (outreach timing) — ADR-171 |
| SIG-INGEST-035 | MUST | — | — | P36.74 (289)*, P36.75 (385)*, GATE-ANNOUNCE (510)* | P11.1, P11.2, P36.74 | R11-W11 WAIVED (clause) — ADR-188 |
| SIG-INGEST-036 | MUST | P35.38a (203) (delivers) | — | P34.38 (246), P36.74 (289)*, P36.77 (352)*, GATE-ANNOUNCE (510)* | — | R11-W10 WAIVED (clause) — ADR-187; R11-A14 AMENDED (no MUST weakened) — ADR-168, ADR-184 |
| SIG-INGEST-037 | MUST | — | — | P34.16 (218), P36.74 (289)* | P07.2, P36.74 | R11-W9 WAIVED (clause) — ADR-182; R11-A14 AMENDED (no MUST weakened) — ADR-168, ADR-184 |
| SIG-INGEST-045e | MUST | — | — | P34.49 (254), PLAN-11B (239)* | P04.2 | — |
| SIG-INGEST-046c | MUST | — | — | P34.38 (246), P34.19 (219)*, P36.1a (265)*, P36.1b (349)* | P36.1a, P36.1b | R11-A14 AMENDED (no MUST weakened) — ADR-168, ADR-184 |
| SIG-LIC-001 | MUST | — | — | P34.19 (219) | P00.2, P00.4 | — |
| SIG-LIC-004 | MUST | — | — | P34.19 (219), P36.2 (350)* | P00.2, P00.4, P14.1, P14.2 | R11-A12 AMENDED (no MUST weakened) — ADR-167, ADR-169, ADR-183 |
| SIG-LIC-004a | MUST | P34.21a (223) (delivers) | — | P36.74 (289)*, P36.75 (385)* | — | — |
| SIG-LIC-009 | MUST | — | — | P34.16 (218), P36.2 (350)*, P37.69a (479)* | P16.2, P36.2 | R11-W9 WAIVED (clause) — ADR-182 |
| SIG-LIC-009a | MUST | — | — | P36.75 (385)*, P37.25 (449)* | P00.2, P14.2 | — |
| SIG-LIC-010 | MUST | — | — | P37.25 (449)* | P04.1, P04.2, P14.2 | — |
| SIG-LIC-011 | MUST | P34.21a (223) (delivers), P34.21b (224) (delivers) | — | P34.19 (219), P34.34a (241), P34.35 (243) | — | — |
| SIG-MEM-002 | MUST | P34.30 (235) (delivers) | — | — | — | — |
| SIG-MEM-003 | MUST | P34.30 (235) (delivers) | — | — | — | — |
| SIG-MEM-005 | MUST | SEED-02 (§56) | P34.8 (210), P34.22a (225), P34.22b (226) | P34.7 (209), P34.24a (228), P34.39a (247) | — | — |
| SIG-MEM-006 | MUST | P34.7 (209) (§56) | P34.27 (232) | P34.30 (235) | — | — |
| SIG-MEM-007 | MUST | P34.2 (202) (§56) | — | P34.1 (201), P35.38a (203)*, P34.3 (204)*, P34.4 (205)*, P34.5 (206)*, P34.6 (207)*, P34.50 (208)*, P34.7 (209)*, P34.8 (210)*, P34.9 (211)*, P34.10 (212)*, P34.11 (213)*, P34.12 (214)*, P34.13 (215)*, P34.14 (216)*, P34.15 (217)*, P34.16 (218)*, P34.19 (219)*, P34.17 (220)*, P34.18 (221)*, P34.20 … | — | — |
| SIG-MEM-008 | MUST | P34.28 (233) (§56) | — | — | — | — |
| SIG-MEM-009 | MUST | P34.28 (233) (§56) | — | P34.27 (232) | — | — |
| SIG-MEM-010 | MUST | P34.9 (211) (§56) | P34.29 (234) | P34.1 (201)*, P34.2 (202)*, P35.38a (203)*, P34.3 (204)*, P34.4 (205)*, P34.5 (206)*, P34.6 (207)*, P34.50 (208)*, P34.7 (209)*, P34.8 (210)*, P34.10 (212)*, P34.11 (213)*, P34.12 (214)*, P34.13 (215)*, P34.14 (216)*, P34.15 (217)*, P34.16 (218)*, P34.19 (219)*, P34.17 (220)*, P34.18 (221)*, P34.20… | — | — |
| SIG-MEM-011 | MUST | P35.3 (292) (§56) | — | P34.17 (220), P34.33 (238), P34.39a (247), P34.39b (248), P34.47 (259) | — | — |
| SIG-MEM-012 | MUST | SEED-02 (§56) | P34.9 (211) | P34.1 (201) | — | — |
| SIG-METRIC-006 | MUST | — | — | P34.35 (243) | P15.5 | — |
| SIG-ONTO-013 | MUST | — | — | P34.26 (231) | P01.1 | — |
| SIG-ONTO-060 | MUST | — | — | PLAN-11B (239)*, P35.14a (272)* | P01.1, P35.14a | G.7.5 checked, not amended — the requirement stands |
| SIG-ONTO-064 | MUST | — | — | P37.9 (430)* | P01.1, P37.9 | — |
| SIG-ONTO-065 | MUST | — | — | P37.9 (430)* | P01.1, P37.9 | — |
| SIG-OPS-001 | MUST | P34.6 (207) (§56) | — | P34.46 (258) | — | — |
| SIG-OPS-002 | MUST | P34.3 (204) (§56) | — | P34.6 (207) | — | — |
| SIG-OPS-003 | MUST | P34.10 (212) (§56) | — | P34.17 (220), P34.21b (224), P34.40 (249), P34.11 (213)* | — | — |
| SIG-OPS-004 | MUST | P34.10 (212) (§56) | — | P34.17 (220), P34.21a (223), P34.21b (224) | — | — |
| SIG-OPS-005 | MUST | P35.1a (264) (§56) | — | P34.42a (251), P34.42b (252) | — | — |
| SIG-OPS-006 | MUST | P35.2 (346) (§56) | P34.4 (205) | P34.50 (208), P34.39b (248), P34.44b (256) | — | — |
| SIG-OPS-007 | SHOULD | P35.2 (346) (§56) | — | P34.4 (205)*, PLAN-11C (340)* | — | — |
| SIG-OPS-008 | MUST | P36.44 (387) (§56) | — | — | — | — |
| SIG-OPS-009 | MUST | P34.5 (206) (§56) | — | — | — | — |
| SIG-OPS-010 | SHOULD | P35.4 (293) (§56) | — | P34.50 (208) | — | — |
| SIG-OPS-011 | MUST | P35.3 (292) (§56) | — | P34.39a (247), P34.39b (248), P34.43 (253), P34.44b (256), P34.47 (259) | — | — |
| SIG-OPS-012 | MUST | P35.3 (292) (§56) | — | P35.38a (203) | — | — |
| SIG-PUB-002 | MUST | P34.18 (221) (delivers), P34.21b (224) (delivers) | — | P34.26 (231), P34.38 (246), P34.49 (254), P36.74 (289)*, P36.76 (351)*, P36.77 (352)*, P36.78 (353)*, P37.71 (429)* | — | G.7.5 checked, not amended — the requirement stands — ADR-185 |
| SIG-PUB-003 | MUST | — | — | P34.49 (254), P36.76 (351)* | — | G.7.5 checked, not amended — the requirement stands — ADR-185 |
| SIG-PUB-003a | MUST | — | — | P36.74 (289)* | — | G.7.5 checked, not amended — the requirement stands — ADR-185 |
| SIG-PUB-004 | MUST | — | — | P35.66 (288)* | P00.2, P14.1 | — |
| SIG-PUB-005 | MUST | — | — | P35.66 (288)* | — | — |
| SIG-PUB-007 | MUST | — | — | P35.28 (286)* | P00.2, P35.28 | — |
| SIG-PUB-012 | MUST | — | — | P37.10 (431)* | P37.10 | — |
| SIG-PUB-013 | MUST | — | — | P35.66 (288)* | — | — |
| SIG-PUB-015 | MUST | — | — | P36.15 (287)* | P36.15 | — |
| SIG-PUB-016 | MUST | — | — | P36.15 (287)* | P36.15 | — |
| SIG-PUB-017 | MUST | — | — | P37.69a (479)* | P18.1 | — |
| SIG-RECON-039 | MUST | — | — | P37.9 (430)* | P08.2, P37.9 | — |
| SIG-RECON-040 | MUST | — | — | P37.9 (430)* | P08.2, P37.9 | — |
| SIG-RECON-052 | MUST | — | — | P36.14 (355)* | P36.14 | — |
| SIG-REL-001 | MUST | P35.12 (294) (§56) | — | — | — | — |
| SIG-REL-002 | MUST | P35.12 (294) (§56) | — | — | — | — |
| SIG-REL-003 | MUST | P35.12 (294) (§56) | — | — | — | — |
| SIG-REL-004 | MUST | P35.53 (331) (§56) | — | P34.10 (212), P34.40 (249) | — | — |
| SIG-REL-005 | MUST | P35.53 (331) (§56) | — | — | — | — |
| SIG-REL-006 | MUST | P35.54 (332) (§56) | — | P34.40 (249) | — | — |
| SIG-REL-007 | MUST | P35.58 (335) (§56) | P35.56 (334) | — | — | — |
| SIG-REL-008 | MUST | P36.66b (410) (§56) | P35.65 (314) | P34.34a (241)* | — | — |
| SIG-REL-009 | MUST | P35.13 (295) (§56) | — | P34.10 (212) | — | — |
| SIG-REL-010 | MUST | P35.57 (261) (§56) | P34.25 (229) | P34.45 (257), P34.46 (258) | — | — |
| SIG-REL-011 | MUST | P36.44 (387) (§56) | — | — | — | — |
| SIG-REL-012 | MUST | P35.60 (337) (§56) | — | GATE-G4 (260) | — | — |
| SIG-REL-013 | MUST | P35.55 (333) (§56) | — | P34.41 (250) | — | — |
| SIG-REL-014 | MUST | P34.23 (227) (§56) | — | — | — | — |
| SIG-REL-015 | MUST | P36.50 (393) (§56) | — | P34.28 (233)* | — | — |
| SIG-SEC-003 | MUST | — | — | P37.8 (428)* | P37.8 | R11-A11 AMENDED (no MUST weakened) — ADR-166 |
| SIG-SEC-007 | MUST | P34.42a (251) (§56), P34.42b (252) (§56) | — | P34.40 (249), P34.43 (253) | — | — |
| SIG-SEC-008 | MUST | P35.1a (264) (§56), P35.1b (291) (§56) | — | PLAN-11B (239) | — | — |
| SIG-SEC-009 | SHOULD | P35.4 (293) (§56) | — | PLAN-11B (239), P34.42a (251), P34.42b (252) | — | — |
| SIG-SEC-010 | MUST | P34.28 (233) (§56) | — | GATE-G4 (260) | — | — |
| SIG-SEC-011 | MUST | P34.25 (229) (§56) | — | P34.43 (253), P34.46 (258) | — | — |
| SIG-STORE-011 | MUST | — | — | P34.18 (221), P34.21a (223), P34.26 (231), P34.49 (254), P34.46 (258), P37.71 (429)*, GATE-ANNOUNCE (510)* | P02.1, P37.71 | R11-W12 WAIVED (clause) — ADR-189 |
| SIG-STORE-041 | MUST | — | — | P34.24a (228), P34.24b (230) | P02.1 | — |
| SIG-STORE-045 | MUST | — | — | P37.58 (486)* | P37.58 | — |
| SIG-STORE-048 | MUST | P37.3 (421) (§56) | P34.3 (204) | P34.42b (252) | — | — |
| SIG-TRUST-006 | MUST | P34.20 (222) (delivers), P34.21b (224) (delivers), P34.26 (231) (delivers) | — | — | — | — |
| SIG-TRUST-009 | MUST | — | — | P34.35 (243) | P32.25, P35.63 | — |
| SIG-TRUST-010 | MUST | — | — | P34.35 (243) | P32.23a | — |
| SIG-UI-007 | MUST | P34.20 (222) (delivers), P34.21b (224) (delivers) | — | — | — | — |
| SIG-UI-010 | MUST | — | — | P36.55 (398)* | P06.1, P15.2 | — |
| SIG-UI-024 | MUST | — | — | P34.34a (241) | P15.3 | — |
| SIG-UI-028 | MUST | — | — | P37.37 (461)* | P15.4 | — |
| SIG-UI-029 | MUST | — | — | P34.20 (222), P37.37 (461)* | P15.4 | — |
| SIG-UI-033 | MUST | — | — | P34.34a (241) | P15.5 | — |
| SIG-UI-035 | MUST | — | — | P34.34a (241)* | — | R11-A4 AMENDED (no MUST weakened) — ADR-162 |
| SIG-UI-036 | SHOULD | — | — | P34.34b (242)* | P15.5 | R11-A3 AMENDED (no MUST weakened) — ADR-155 |
| SIG-UI-040 | SHOULD | P34.48 (240) (delivers) | — | P34.36 (244) | — | — |
| SIG-UI-041 | MUST | — | — | P34.34b (242) | — | — |
| SIG-UI-042 | MUST | — | — | P34.17 (220) | P15.5 | R11-W8 WAIVED (clause) — ADR-179 |
| SIG-UI-044 | MUST | — | — | P36.17 (357)* | P15.5 | R11-A5 AMENDED (no MUST weakened) |
| SIG-UI-049 | MUST | — | — | P34.34a (241) | P27.6 | — |
| SIG-UI-050 | MUST | — | — | P34.15 (217), P34.34b (242), P34.36 (244) | P27.9 | R11-A3 AMENDED (no MUST weakened) — ADR-155 |

`*` = mentioned outside the contract's requirement section. Ids written as later-family drafts (SIG-TRANSP-D…, UXR-…, SIG-EVUI-D…, SIG-WATCH-D…) are not requirement ids yet and are not indexed; PLAN-11B (SIG-TRANSP) and PLAN-11C (the K13 set) assign their final ids and extend this index.
