# SPEC_RECONCILIATION_PLAN — ADR dispositions, amendments, fold-backs (P20.2)

Companion to `TICKET_VS_SPEC.md`. This plan (a) dispositions every repository ADR against the spec,
(b) states each HG-13 amendment with its exact `spec_src` target + before/after + tick state, (c)
lists the fold-back ids, (d) the order of application, and (e) what remains a proposal. ADR numbers
are **repository** numbers (Appendix F). Gate HG-13: **all eight amendments TICKED — applied.**

---

## (a) ADR disposition table — ADR-001 … ADR-061

Legend: **no-op** = the ADR's decision is already consistent with the spec, nothing to change;
**F-index** = fixed by rebuilding Appendix F to repository numbering (LD-X04/LD-D03);
**G-correction** = recorded as an Appendix G.5 note (no new id); **amendment (Ax)** = a ticked
normative amendment applied at `spec_src`.

| ADR | Disposition | Note |
|---|---|---|
| ADR-001 | no-op | §15.1 canonical store — consistent |
| ADR-002 | no-op | §16.1–16.3 append-only claims — consistent |
| ADR-003 | no-op | §9.2 time dimensions — consistent |
| ADR-004 | no-op | §16.7 EDTF — consistent |
| ADR-005 | no-op | §16.4 resolution record — consistent |
| ADR-006 | no-op | §17.3 OCFL — consistent |
| ADR-007 | no-op | §20.1 LinkML — consistent |
| ADR-008 | no-op | §20.2 SKOS — consistent |
| ADR-009 | no-op | §42.1/42.4 SPDX gate — consistent |
| ADR-010 | no-op | §18 analytics boundary — consistent |
| ADR-011 | no-op | §42.3 ODbL posture — consistent |
| ADR-012 | no-op | §16.8/19.4 RLS tiers — consistent |
| ADR-013 | no-op | uv — stack ADR, no spec requirement softened |
| ADR-014 | no-op | Astro — stack ADR |
| ADR-015 | no-op | S3/CloudFront — resolves §38.5 egress |
| ADR-016 | no-op | Dagster OSS — §21.8 |
| ADR-017 | no-op | FastAPI — stack ADR |
| ADR-018 | **amendment (A1)** | §40 SIG-UI-038: zero-JS static map is the conforming default; MapLibre island optional (SIG-UI-047) |
| ADR-019 | no-op | pytest/Hypothesis — §48 |
| ADR-020 | no-op | GitHub Actions — CI |
| ADR-021 | no-op | §22 seeded registry — consistent (seed breadth = data, TICKET_VS_SPEC/Appendix G) |
| ADR-022 | **amendment (A4)** | §16.2 #6: partitioning MAY/deferred, MUST keep `claim_id` PK/FK |
| ADR-023 | **amendment (A7) + fold-back** | §47 layout adds `evidence/`; blob-vs-capture dedup folded back as SIG-EVID-020 |
| ADR-024 | no-op | §16.7 EDTF envelope — determinism note in Appendix G |
| ADR-025 | no-op | temporal invariants/as-of — consistent |
| ADR-026 | no-op | §21 connector framework — consistent |
| ADR-027 | no-op | §21/§42.3 osm connector — consistent |
| ADR-028 | no-op | §21 atlas connector — consistent |
| ADR-029 | **F-index** | ledger "logical ADR-016 = Splink" vs repo ADR-016 = Dagster → repo ADR-029; fixed by Appendix F rebuild (LD-D03) |
| ADR-030 | **amendment (A6)** | §34/§39.7: CLI+JSONL curation queue conforming for Phase 5; web → Phase 21 |
| ADR-031 | **G-correction** | P06.1 minimal count-recon seed ahead of Phase 8 — Appendix G.5 |
| ADR-032 | **G-correction** | P06.1 slice dossier renderer, superseded by ADR-050 — Appendix G.5 |
| ADR-033 | no-op | §24 parsing stack — consistent |
| ADR-034 | no-op | §23 records connector — consistent |
| ADR-035 | no-op | §23 procurement connector — consistent |
| ADR-036 | no-op | §29 reconciliation workflows — consistent |
| ADR-037 | **amendment (A5)** | §31 SIG-RECON-053: `Contradiction` materialized **or** compute-on-read |
| ADR-038 | **amendment (A5)** | §32 SIG-METRIC-001: `CoverageRecord` materialized **or** compute-on-read |
| ADR-039 | **amendment (A5)** | §33 SIG-TASK-002: research tasks materialized **or** compute-on-read |
| ADR-040 | **G-correction** | §52 "32 task types" → "34" (matches §33.2 catalog) — Appendix G.5 N-03 |
| ADR-041 | **amendment (A2)** | §32.1/§33 SIG-TASK-016a: residency barrier → `absence_kind = not_researched`; vocabulary made explicit |
| ADR-042 | no-op | §21/§42.3 flock_portal — consistent |
| ADR-043 | no-op | §18.1 audit_structural — consistent (new source type in Appendix G) |
| ADR-044 | no-op | §18 analytics — consistent (substrate choice in Appendix G) |
| ADR-045 | no-op | §30.2 access-path closure — consistent |
| ADR-046 | no-op | §11.13/11.14/§29.6 policy/legal — consistent |
| ADR-047 | no-op | §37 read API — consistent (ReadStore seam impl-detail) |
| ADR-048 | no-op | §38/§42.4 exports — consistent |
| ADR-049 | no-op | §39.1/39.9/§40 web shell — consistent (OSI waiver in Appendix G) |
| ADR-050 | no-op | §39.2 local dossier — consistent |
| ADR-051 | **amendment (A1)** | §39.3/§40: static PMTiles served without the MapLibre runtime; SIG-UI-038 default + SIG-UI-047 island |
| ADR-052 | no-op | §39.5/39.6 watch/evidence — consistent |
| ADR-053 | no-op | §39.7/39.8/§41 queue/corrections/editorial — consistent |
| ADR-054 | **amendment (A5/A6)** | §34 contributor system pure logic ahead of persistence — compute-on-read + CLI form conforming |
| ADR-055 | **F-index** | records the spec's *logical* "ADR-017" (no-OSM-writes, §35.2) = repo ADR-055; fixed by Appendix F rebuild (LD-X04) |
| ADR-056 | **amendment (A3)** | §11.2 `canonical_name` scalar |
| ADR-057 | no-op | §21/§23 France/Belgium connectors — consistent (DECP `end_date` impl-detail) |
| ADR-058 | no-op | tickets/scratch committed — build-memory decision, no spec requirement softened |
| ADR-059 | no-op | capstone spine wiring — compute-on-read seam consistent with A5 |
| ADR-060 | no-op | resolver retro-fitted record — §28 consistent |
| ADR-061 | no-op | capstone gap closure — §38/§43.8/§14 consistent |

**Also applied globally:** Appendix F rebuilt to repository numbering (all of ADR-001…062), which is
the structural fix behind the two F-index rows and LD-X04/LD-D03; and `docs/adr/README.md` gained the
missing ADR-056/ADR-057 index rows.

Disposition tally: **no-op 45 · F-index 2 · G-correction 3 · amendment 11** (ADR-018, 022, 023, 030,
037, 038, 039, 041, 051, 054, 056) = 61.

---

## (b) Amendments A1 … A8 — target, anchor, before/after, tick state

All eight ticked (HG-13). Applied at `docs/research/_meta/spec_src/*.md`, then
`sh docs/research/_meta/spec_src/BUILD.sh`. "after" strings are greppable in the committed spec.

### A1 — §40 / ADR-018 · **[x] TICKED — APPLIED**
- **Target:** `81_partVII_s39to41_ui.md` (§40, SIG-UI-038; new SIG-UI-047). ADR-051, ADR-018, LD-F09.
- **Before:** *"**SIG-UI-038 (MUST).** Maps MUST use an open-source renderer with self-hosted vector tiles (§19.5). Third-party tile CDNs MUST NOT be a hard dependency, and basemap attribution MUST be correct in every context (SIG-GEO-013)."*
- **After:** the same, plus *"A **zero-JS static map** … is a **conforming default** for this requirement; a client-side interactive renderer (MapLibre GL) is an **optional progressive-enhancement island** (SIG-UI-047), not a precondition of conformance (ADR-051, ADR-018, LD-F09)."* and a new **SIG-UI-047 (MAY)** paragraph.
- **New id:** SIG-UI-047.

### A2 — §32.2 / ADR-041 · **[x] TICKED — APPLIED**
- **Target:** `61_partV_s29to32_workflows.md` (§32.1 SIG-METRIC-001 vocabulary note) and `70_partVI_s33to36_research.md` (§33 SIG-TASK-016a item 3). ADR-041, LD-F14.
- **Before (SIG-TASK-016a #3):** *"Record the constraint as a coverage fact, so that thin evidence … is attributed to the legal barrier … (§9.5, §32.2)."*
- **After:** adds *"The coverage fact MUST use `absence_kind = not_researched` (§32.1) … distinct from `searched_not_found` … and MUST NOT be recorded as the latter (ADR-041, LD-F14)."*; and a closed-vocabulary paragraph under SIG-METRIC-001 defining `not_researched`. *(The vocabulary table already contained `not_researched`; this makes its use binding.)*
- **New id:** none.

### A3 — §11.2 / ADR-056 · **[x] TICKED — APPLIED**
- **Target:** `23_partII_s11_entities.md` (§11.2 `Organization`, `canonical_name` row). ADR-056, LD-D12.
- **Before:** *"| `canonical_name` | literal | **A claim, not a column.** Competing names are competing claims (§8.2) |"*
- **After:** *"| `canonical_name` | literal (**scalar**) | A **single** resolved display/identity label … The competing names it is chosen from **remain claims** (§8.2) … not a repeatable column (ADR-056, LD-D12) |"*
- **New id:** none.

### A4 — §16.2 item 6 / ADR-022 · **[x] TICKED — APPLIED**
- **Target:** `41_partIII_s16_schema.md` (§16.2 design-point #6 + the DDL `PARTITION BY` line). ADR-022, LD-D01.
- **Before:** *"| 6 | Partitioned by `observed_at`, not by `sys_period` | Queries filter on observation time … |"* and DDL *") PARTITION BY RANGE (observed_at);"*
- **After:** *"| 6 | **MAY** partition by `observed_at` (never by `sys_period`); physical partitioning is **deferred** and MUST preserve the `claim_id` PK/FK contract (ADR-022) | … partitioning MUST NOT break the `claim_id` primary key or any foreign key … until that contract can be kept, the table stays unpartitioned (ADR-022, LD-D01). |"* and DDL *");  -- MAY later: PARTITION BY RANGE (observed_at) — deferred to preserve the claim_id PK/FK contract (ADR-022)"*
- **New id:** none.

### A5 — §30/§32/§33 / ADR-037/038/039 · **[x] TICKED — APPLIED**
- **Target:** `61_partV_s29to32_workflows.md` (§31 SIG-RECON-053; §32 SIG-METRIC-001) and `70_partVI_s33to36_research.md` (§33 SIG-TASK-002). Kept per P19.5's ACCEPTED list.
- **Before (SIG-RECON-053):** *"`Contradiction` MUST be a materialized entity with:"*
- **After:** *"`Contradiction` MUST be a first-class object with the shape below — **materialized as a stored entity _or_ computed on read** … either is conforming so long as the shape, the lifecycle … and the byte-identical L3 rebuild (SIG-STORE-018) hold. Compute-on-read is the accepted Phase-8 form; persistence is deferred to Phase 21 (ADR-037):"* — and matching compute-on-read clauses on SIG-METRIC-001 (ADR-038) and SIG-TASK-002 (ADR-039).
- **New id:** none.

### A6 — §34 / ADR-030 · **[x] TICKED — APPLIED**
- **Target:** `70_partVI_s33to36_research.md` (§34 SIG-CONTRIB-002) and `81_partVII_s39to41_ui.md` (§39.7 SIG-UI-031). ADR-030, LD-F05.
- **Before (SIG-CONTRIB-002):** *"No tier may write a claim without provenance. Contributor submissions enter at **L0** … never directly at L1."*
- **After:** adds *"The curation / review surface … **MAY be a CLI + JSONL queue** for Phase 5; that form is **conforming** … with an interactive **web** curation/review surface deferred to Phase 21 (P21.6). This is a form allowance, not a weakening … (ADR-030, LD-F05)."*; SIG-UI-031 gains the matching clause.
- **New id:** none.

### A7 — §47 / ADR-023 · **[x] TICKED — APPLIED**
- **Target:** `95_partIX_s47to50_eng.md` (§47 SIG-ENG-012 layout). ADR-023.
- **Before:** layout list without `evidence/`.
- **After:** adds *"evidence/        content-addressed evidence blobs; OCFL capture rows; blob dedup (§17, ADR-023)"* to the SIG-ENG-012 layout.
- **New id:** none (the blob-dedup contract is folded back separately as SIG-EVID-020).

### A8 — further `P20.2:spec`-routed items · **[x] TICKED — APPLIED (empty set)**
- **Enumeration:** the only id routed `P20.2:spec` anywhere in `COVERAGE_MATRIX.csv`,
  `CAPSTONE_GAP_ANALYSIS.md`, or `CAPSTONE_CLOSURE.md` is **`SIG-UI-038`**, which is amendment A1.
  P19.2/P19.5 routed **no further** normative item to `P20.2:spec`. The enumerated A8 set is
  therefore **empty**; there is nothing additional to fold back under A8 (0 further ids).
- **New id:** none.

---

## (c) Fold-back ids (approved `ticket-added` scope folded into the spec)

New ids appended to their prefix sequences (§0.3: append-only, never reused/renumbered). Count **N = 3**;
spec requirement-id total 668 → **671**.

| New id | Level | Section / file | Requirement | Origin |
|---|---|---|---|---|
| SIG-UI-047 | MAY | §40 / `81_partVII_s39to41_ui.md` | Interactive MapLibre progressive-enhancement map island, optional, deferred to Phase 21; must not break the zero-JS default or the perf/archival budgets | A1 / ADR-051 / ADR-018 / P15.3 ticket-added |
| SIG-EVID-020 | MUST | §17 / `42_partIII_s17_evidence.md` | The `evidence/` package separates content-addressed blob from capture row; identical bytes dedup to one blob; deleting a capture never deletes a still-referenced blob | ADR-023 / P02.2 ticket-added / A7 |
| SIG-ENG-039 | MUST | §47 / `95_partIX_s47to50_eng.md` | Every `docs/adr/ADR-*.md` MUST have an Appendix F row in the same PR; `check_spec_src.py` asserts file-set == index-set | ADR-062 / P20.2 reconciliation |

Reserved ids **not** used (§0.3): SIG-ENG-006/007/008/009/028/029. Next free ordinals consumed:
SIG-UI-047 (was max 046), SIG-EVID-020 (was max 019), SIG-ENG-039 (was max 038 — clears the 028/029
reservation).

---

## (d) Order of application

1. Tick the HG-13 gate block in the ticket (first commit).
2. Apply A1–A7 + the three fold-backs at `spec_src/*.md`; apply the non-normative corrections
   (Appendix F rebuild, `docs/adr/README.md` ADR-056/057, §52 "34 task types", Appendix G.5).
3. `sh docs/research/_meta/spec_src/BUILD.sh`; commit the regenerated `docs/2_canonical_design_spec.md`.
4. Add ADR-062 + its README index row.
5. `python docs/build/tools/check_spec_src.py` (exit 0: 671 ids, Appendix F == ADR files, byte-clean).
6. Downstream: `traceability.md`, `COVERAGE_MATRIX.csv` (+ bump `check_coverage_matrix.py` to 671),
   the manifest amendment log, the risk register (RISK-P20-02), and `BACKLOG.csv`.
7. `make check`; open the stacked PR.

---

## (e) What stays a proposal / residual risk

**Nothing stays an unapplied amendment** — all eight A1–A8 were ticked and applied, and A8's
enumerated set is empty. There are therefore no "unticked proposals" for this pass.

Residual (tracked, not a spec proposal):

- **RISK-P20-02** — *unapplied build work implied by the ticked amendments could drift from the
  spec.* The amendments legitimise deferrals whose **build** is still outstanding: the optional
  MapLibre island (SIG-UI-047 → Phase 21 / P21.5), the Phase-21 persistence of
  contradiction/coverage/task objects (A5 → P21.2), and the web curation surface (A6 → P21.6). If
  those tickets never land, the MAY-level island and the deferred persistence remain unbuilt — which
  is conforming, but the risk of the spec and code diverging further is carried in `BACKLOG.csv` and
  `docs/risk_register.md` (RISK-P20-02).
- The `ticket-added` rows dispositioned **Appendix G** or **impl-detail** in `TICKET_VS_SPEC.md` were
  deliberately *not* folded back (they are data/process/plumbing choices, not new requirements); they
  are recorded rather than proposed.
