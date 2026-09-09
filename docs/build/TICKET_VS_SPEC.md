# TICKET_VS_SPEC — ticket deliverables tagged against the canonical spec (P20.2)

One table per build ticket **P00.1 → P18.2** (46 tables). Each deliverable line is tagged:

- **in-spec** — a canonical § + requirement id says to build it;
- **spec-implied** — needed to satisfy a § but not named by an id;
- **ticket-added** — decomposition-time scope beyond the spec text.

Every **ticket-added** row carries a proposed disposition: **fold-back** (a new id was appended to
the spec by P20.2), **Appendix G** (recorded as a reconciliation note, no new id), or **impl-detail**
(a build/data choice, left as-is). Fold-backs and amendments are detailed in
`SPEC_RECONCILIATION_PLAN.md`; the ADR numbers are the repository numbers (Appendix F).

Method: tagging input is each ticket's *In scope — deliverables* + *Requirement IDs*, cross-checked
against `COVERAGE_MATRIX.csv`, `LEDGER_DEFERRALS.md`, and the ADR set. This is a reconciliation view,
not a re-derivation of coverage (P19.2 owns verdicts).

---

## Phase 0

### P00.1 — repo skeleton
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| uv monorepo, §47 package layout, CI, licence headers | in-spec | §47 SIG-ENG-010/011/012/013 |
| The frozen §47 top-level package set incl. `evidence/` | in-spec | §47 SIG-ENG-012 (amended A7 to name `evidence/`) |

### P00.2 — policy as code
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Executable crawler/licence/publication/threat policy | in-spec | §26/§42/§43 SIG-INGEST-036/037, SIG-LIC-* |
| ADR-001…012 + stack ADRs ADR-013…020 authored | in-spec | Appendix F; SIG-STORE-006/007 |

### P00.3 — governance policies
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Takedown/corrections/suppression, CoC, anti-misuse, contributor safety | in-spec | §44/§45/§39.8 SIG-GOV-*, SIG-UI-032 |

### P00.4 — source registry
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Source registry as seeded data + `ingestion_permitted` gate | in-spec | §22 SIG-INGEST-*, ADR-021 |
| Rights records + SPDX per source | in-spec | §42 SIG-LIC-001..004 |
| Breadth of the seeded registry (which 19+ sources, host variants) | ticket-added | **Appendix G** — seed data, not a spec requirement (ADR-021) |

---

## Phase 1

### P01.1 — ontology as code
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| LinkML ontology for §11/§12; SKOS vocabularies; generators | in-spec | §20 SIG-ONTO-*, ADR-007/008 |
| Generalization conformance suite | in-spec | §8 SIG-CHART-028 |
| Appendix F ↔ `docs/adr/` equivalence enforced in CI | ticket-added | **fold-back → SIG-ENG-039** (ADR-062) |

---

## Phase 2

### P02.1 — claim spine
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Claim/evidence schema L0–L3, append-only, resolution table, RLS | in-spec | §16 SIG-STORE-008..018 |
| `tstzrange`+GiST EXCLUDE instead of "native PERIOD"; unpartitioned claim table | ticket-added | **Appendix G / A4** — partitioning is MAY/deferred, MUST keep `claim_id` PK/FK (ADR-022, LD-D01) |

### P02.2 — evidence store
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| OCFL evidence store, content addressing, capture pipeline, sealed tiers | in-spec | §17 SIG-EVID-001..010, ADR-006 |
| Separate `evidence/` package + content-addressed blob-vs-capture dedup | ticket-added | **fold-back → SIG-EVID-020**, and **A7** (`evidence/` in §47) (ADR-023, LD-D02) |

### P02.3 — temporal & provenance
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| EDTF, as-of functions, temporal invariants, PROV-O, lineage | in-spec | §9/§16.7 SIG-TIME-*, ADR-004/024/025 |
| Pinned deterministic in-repo EDTF envelope derivation | ticket-added | **Appendix G** — a determinism choice under SIG-TIME (ADR-024) |

---

## Phase 3

### P03.1 — identity registries
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Jurisdiction + org registries, geometry, temporal identity | in-spec | §11.1/11.2/§14 SIG-ONTO-011..013, SIG-IDENT-* |

### P03.2 — deterministic ER
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Crosswalk, `normalize_org_name`, cascade tiers 0–3, public-ID lifecycle | in-spec | §14.5/14.6 SIG-IDENT-020..028 |

---

## Phase 4

### P04.1 — connector framework
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| 8-stage framework, rate-limit/robots, licence gate, replay, shadow mode | in-spec | §21 SIG-INGEST-*, ADR-026 |
| Socket-level network-isolated replay | ticket-added | **Appendix G** — a hardening of §21.7 replay (ADR-026) |

### P04.2 — osm connector
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `osm` connector + separate ODbL asset table; `(type,id,version)` keying | in-spec | §21/§42.3 SIG-INGEST-*, ADR-011/027 |

### P04.3 — atlas connector
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `atlas` (EFF) connector, family-level `deployment_exists`, category retirement | in-spec | §21 SIG-INGEST-*, ADR-028; SIG-ONTO-059 |

---

## Phase 5

### P05.1 — probabilistic ER
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Splink matcher, blocking, gold set, tiers 4–5 to review, cluster alerts | in-spec | §14.6/14.7 SIG-IDENT-028, ADR-029 |

### P05.2 — curation UI
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Review queue + LLM-to-review scaffolding | in-spec | §39.7 SIG-UI-031; §34 SIG-CONTRIB-*, ADR-030 |
| Curation surface delivered as **CLI + JSONL**, web deferred | ticket-added | **A6** — CLI+JSONL conforming for Phase 5, web → Phase 21 (ADR-030, LD-F05/D04) |

---

## Phase 6

### P06.1 — vertical slice (HARD GATE)
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| One jurisdiction end-to-end (J-1) | in-spec | §52 Phase 6 gate |
| Retrospective report format | ticket-added | **impl-detail** — a process artifact of the hard gate |
| Minimal count-reconciliation seed + 3 count predicates; slice dossier renderer | ticket-added | **Appendix G** — ahead-of-phase seeds superseded later (ADR-031/032, LD-D05) |

---

## Phase 7

### P07.1 — parsing stack
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Parsing stack, locators, file classification, canary drift defences | in-spec | §24 SIG-PARSE-001..008, ADR-033 |

### P07.2 — records connectors
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Records connectors + `RecordsRequest`; MuckRock api_v2 JWT | in-spec | §23 SIG-INGEST-*, ADR-034 |
| Additive per-request `headers` seam on the shared fetcher | ticket-added | **impl-detail** — additive plumbing (ADR-034, LD-D06) |

### P07.3 — procurement connectors
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Procurement + cooperative/federal sub-awards + `FundingInstrument` + agenda registry | in-spec | §23/§11 SIG-ONTO-032/033, ADR-035 |
| Published `agenda_tenants.toml` municipality→platform registry | ticket-added | **Appendix G** — realises A-03's "SIG should build one" (ADR-035) |

---

## Phase 8

### P08.1 — resolver
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Deterministic `RESOLVE`, ruleset-as-data, four axes, rationales, ambiguity test | in-spec | §28 SIG-RECON-007/021, ADR-060 |

### P08.2 — reconciliation workflows
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| The §29 reconciliation workflows (owns §29.3/§29.7) | in-spec | §29 SIG-RECON-*, ADR-036 |

### P08.3 — contradiction object
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `Contradiction` first-class object + lifecycle | in-spec | §31 SIG-RECON-053..057, ADR-037 |
| Delivered as compute-on-read value object, no PG persistence | ticket-added | **A5** — compute-on-read conforming; persistence → Phase 21 (ADR-037, LD-D07) |

---

## Phase 9

### P09.1 — coverage
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Coverage, completeness, negative space; capture–recapture prohibition | in-spec | §32 SIG-METRIC-001..010, ADR-038 |
| Coverage layer as compute-on-read in `inference` | ticket-added | **A5** — compute-on-read conforming (ADR-038, LD-D07) |

---

## Phase 10

### P10.1 — task engine
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Detector DSL, lifecycle, dispositions, geo queues, anti-abuse, registry | in-spec | §33 SIG-TASK-001..018, ADR-039 |
| Tasks as compute-on-read callables, no queue persistence | ticket-added | **A5** — compute-on-read conforming (ADR-039, LD-D07) |

### P10.2 — detector catalog
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| The §33.2 catalog of **34** detectors + contradiction→task map | in-spec | §33.2 SIG-TASK-003, ADR-040 |
| §52 phase text said "32 task types" | ticket-added | **Appendix G (N-03)** — §52 aligned to "34" (ADR-040) |

### P10.3 — records-request generation
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Records-request generation + 51-jurisdiction statute templates + consent gate | in-spec | §33 SIG-TASK-016..018, ADR-041 |
| Residency barrier recorded as `absence_kind = not_researched` | ticket-added | **A2** — vocabulary made explicit; residency uses `not_researched` (ADR-041, LD-F14) |

---

## Phase 11

### P11.1 — flock portal
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `flock_portal` connector (CC-BY-SA compartment, snapshot diff, backfill, fallbacks) | in-spec | §21/§42.3 SIG-INGEST-031, ADR-042 |

### P11.2 — audit structural
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `audit_structural` connector (aggregates-only, Camera Count, SharedNetworks, `***`≠empty) | in-spec | §18.1 SIG-STORE-*, ADR-043 |
| New `agency_audit_export` source type | ticket-added | **Appendix G** — additive source (SIG-INGEST-046a, ADR-043) |

---

## Phase 12

### P12.1 — usage analytics
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Usage aggregates + analytics boundary + small-cell suppression | in-spec | §18 SIG-STORE-025..033, ADR-044 |
| Hive-partitioned Parquet substrate, no columnar PG extension | ticket-added | **Appendix G** — a substrate choice under §18 (ADR-044) |

### P12.2 — network inference
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Access edges (3 types) + access-path closure | in-spec | §30.2 SIG-RECON-047..050, SIG-ONTO-042/044/049, ADR-045 |

---

## Phase 13

### P13.1 — accountability
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `AccountabilityEvent` + `LegalProceeding` + `epistemic_status` + connector | in-spec | §11 SIG-ONTO-*, §10 |
| `CuratedSourceIndex` general form (`index_only`, `as_claims()` raises) | ticket-added | **Appendix G** — general form of SIG-EPIS-030 (ADR-046) |

### P13.2 — policy & legal
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| `Policy` + `LegalInstrument` + policy/config divergence reconciler | in-spec | §11.13/11.14/§29.6 SIG-ONTO-034, SIG-RECON-044, ADR-046 |

---

## Phase 14

### P14.1 — public API
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Read API, resolution envelope, as-of, `/id/{type}/{uuid}`, `/changes` | in-spec | §37 SIG-API-001..012, ADR-047 |
| `ReadStore` seam with in-memory impl (no DB fetch layer yet) | ticket-added | **impl-detail** — seam later satisfied by PgReadStore (ADR-047/059) |

### P14.2 — exports
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Exports + licence computation + ODbL split + crosswalk + Zenodo DOIs | in-spec | §38/§42.4 SIG-INGEST-016, SIG-LIC-010, ADR-048 |
| PMTiles as a v3 archive (no rendered tiles); `derivative_permitted` not gated | ticket-added | **Appendix G** — closed later by ADR-061 (LD-D09) |

---

## Phase 15

### P15.1 — web shell
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Astro shell + epistemic visual language + a11y/no-JS + citation | in-spec | §39.1/39.9/§40 SIG-UI-036..046, ADR-049 |
| OSI licence gate with documented CC0+BlueOak waiver | ticket-added | **Appendix G** — a CI gate policy under SIG-UI-039 (ADR-049, LD-D10) |

### P15.2 — local dossier
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Local dossier + print/PDF + "what we don't know" | in-spec | §39.2 SIG-UI-010..015, ADR-050 |

### P15.3 — map & network
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Infrastructure map + network explorer honest-rendering rules | in-spec | §39.3/39.4 SIG-UI-017..025, ADR-051 |
| Zero-JS static PMTiles served **without** the MapLibre runtime | ticket-added | **A1 + fold-back → SIG-UI-047** — static map conforming default; MapLibre island optional/Phase 21 (ADR-051, LD-F09/D11) |

### P15.4 — watch & evidence
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Renewal watch (iCal/RSS) + evidence recommender + evidence viewer | in-spec | §39.5/39.5a/39.6 SIG-UI-027..028, ADR-052 |

### P15.5 — corrections & methodology
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Research queue + corrections log + methodology/coverage + editorial gate | in-spec | §39.7/39.8/§41 SIG-UI-031..046, SIG-METRIC-008..010, ADR-053 |

---

## Phase 16

### P16.1 — contributors
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Contributor system (tiers, safety, L0 entry, revert, anti-poisoning) | in-spec | §34 SIG-CONTRIB-001..011c, ADR-054 |
| Delivered as pure `tasks`-package logic ahead of persistence | ticket-added | **A5/A6** — compute-on-read + CLI form conforming; persistence → Phase 21 (ADR-054) |

### P16.2 — contribution back
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| OSM human-mediated suggestion workflow, organised-editing page, hashtag | in-spec | §35.2 SIG-CONTRIB-014..020, ADR-055 |

---

## Phase 17

### P17.1 — broader federation / RTCC
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Private-camera federation + RTCC integration | in-spec | §11/§12 SIG-ONTO-*, §30 |

### P17.2 — FR / CSS / forensics
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Facial recognition + cell-site simulators + mobile forensics | in-spec | §11.5/11.6 SIG-ONTO-*, technology taxonomy |

### P17.3 — acoustic / drone / location
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Gunshot detection + drones + commercial location data | in-spec | §11.5 SIG-ONTO-*, A-05/A-13 |

---

## Phase 18

### P18.1 — international framework
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| Jurisdiction adapter framework + i18n + jurisdiction-conditional publication | in-spec | §43.8/§13.7 SIG-ONTO-*, ADR-056 |
| `canonical_name` treated as a **scalar** (spec-faithful) | ticket-added | **A3** — `canonical_name` scalar, competing names remain claims (ADR-056, LD-D12) |

### P18.2 — France / Belgium
| Deliverable | Tag | Anchor / disposition |
|---|---|---|
| France/Belgium connectors + OSM-import study | in-spec | §21/§23 SIG-INGEST-*, ADR-057 |
| DECP `end_date` unset (derivable); amendments kept in `raw` | ticket-added | **impl-detail** — derivable field, no `ProcurementState` (ADR-057, LD-D13) |

---

## Totals

| Tag | Count |
|---|---|
| in-spec | 50 |
| spec-implied | 0 |
| ticket-added | 26 |
| **rows total** | **76** |

**Ticket-added dispositions (26 — every `ticket-added` row is dispositioned exactly once):**

| Disposition | Count | Rows |
|---|---|---|
| **fold-back** (new spec id) | 3 | P01.1 → SIG-ENG-039; P02.2 → SIG-EVID-020 (also A7); P15.3 → SIG-UI-047 (also A1) |
| **amendment** (softening, no new id) | 9 | P02.1/A4, P05.2/A6, P08.3/A5, P09.1/A5, P10.1/A5, P10.2/N-03, P10.3/A2, P16.1/A5+A6, P18.1/A3 |
| **Appendix G** (note, no id) | 10 | P00.4, P02.3, P04.1, P06.1 (seeds), P07.3, P11.2, P12.1, P13.1, P14.2, P15.1 |
| **impl-detail** (left as-is) | 4 | P06.1 retro format, P07.2 headers seam, P14.1 ReadStore seam, P18.2 DECP `end_date` |

3 + 9 + 10 + 4 = 26. The two fold-back rows P02.2 and P15.3 are *also* touched by amendments A7/A1
respectively (a single deliverable both folded back **and** reflected in an enumeration/softening);
they are counted once, under fold-back. Every `ticket-added` row carries a disposition.
