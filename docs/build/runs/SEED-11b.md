# Run ledger — SEED-11b (Round 11 Stage B, T1): Round-11 ADRs 157–167 authored by SEED-11

- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 4140fda
- **Started:** 2026-10-01T07:34:17Z
- **Closed:** 2026-10-01T07:45:43Z
- **Unit:** SEED-11b — write the ADRs numbered 157…167 whose author in `PD/NEXT_PHASE_PLAN.md` §7 is SEED-11
  (`PD` = `docs/build/planning/2026-09-30-next-phase/`); brief `PD/stageB/AGENT_BRIEF.md`.
- **Worktree / branch:** `~/Eleutheria-next-phase` (the Stage-B worktree), `r11/seed` (no git state changed by this unit;
  the planning orchestrator commits).

## Scope as assigned (PLAN §7, author column)

| ADR | §7 author | this unit |
|---|---|---|
| 157 Static figure kit and dossier visualisations | **P36.27** | skipped (ticket-authored) |
| 158 Graph exploration as aggregated overviews | SEED-11 | written |
| 159 Organisation publication | SEED-11 | written |
| 160 Structured jurisdiction scheme and placement | **P35.17** | skipped (ticket-authored) |
| 161 Release model v2 | **P35.12** | skipped (ticket-authored) |
| 162 Transparency and distribution | SEED-11 | written |
| 163 Single-maintainer publication posture (WV-03) | SEED-11 | written |
| 164 Interim editorial authority and public decision log (WV-02) | SEED-11 | written |
| 165 Interim legal home (WV-01) | SEED-11 | written |
| 166 Legal-demand posture | SEED-11 | written |
| 167 Counsel basis | SEED-11 | written |

## What was done

- Read the brief, PLAN §4, §5.6/5.7/5.10, §6, §7 and Appendix A T1/T4; RATIFICATION_LOG rounds 2–26; RATIFICATION_ANSWERS
  (A-3, A-4, A-10, A-11, A-22, A-23, B-18, B-19, C-3); `decision_catalog.csv` (operator_answer + answered_at) for every
  member line; E2 (§0, E2-01/03/04/05/10), E1-05; K0 (§7, §8, §11), K2 (§0, §3.4, §5–§8, §11, §14), K13 §10; J3 (§0–§3,
  §6.8–§9, §11, §13), J4 (§0, §2, §10); L3 CP-10/CONF-13; S4 TS-09, FEA-18; S6 §5; the implementing rows in
  `round11_plan.csv`/`ticket_catalog.csv`; the landed ADR-086, ADR-106, ADR-124, ADR-143…145, the ADR template and
  `layout.md` BM-ADR rules; spec text of SIG-UI-021/022/023, SIG-IDENT-030, SIG-PUB-008, SIG-SEC-003, SIG-GOV-012/013/015,
  SIG-LIC-009, SIG-ONTO-013, SIG-EXPORT-008/009, SIG-UI-035, SIG-TRUST-006; and, read-only at HEAD, `officer.py`,
  `publication.ts`, `terms.py`, the governance doc and the five `rights_reviewed_by = "counsel (HG-02)"` registry rows.
- Wrote eight ADRs in the template shape (`# ADR-NNN:`; Status/Date/Ticket/Requirement ids/Spec header bullets; Context,
  Decision, Consequences, Alternatives considered, Revisit trigger), status `Accepted`, `Date: 2026-10-01` (the GATE-P
  round dates from the log), plus a `Recorded:` stamp from `date -u` written by the same shell command.
- Operator words quoted verbatim from the log with round time, `printf '%s' … | shasum -a 256` and the label "agent-drafted,
  adopted by the operator at <time>". Adopted sentences re-hashed at writing match S6 §5: WV-01 `b9dc5a91…`, WV-02
  `bee2cd2b…`, WV-03 `44644f6b…`, C-3 `1461ae21…`. Selected option labels hashed too (A-3, A-4, A-10, A-11, A-22, B-18,
  B-19, C-3's option). Agent-drafted copy that is not yet operator-confirmed (E2's disclosure/label texts) is quoted as
  draft, pending a copy batch (B-2), never as adopted.
- No landed ADR, index, spec, ledger or register edited; no git state changed.

## Relationships each new ADR records (for SEED-11d's status lines; from PLAN §7)

| new ADR | supersedes | qualifies | amends | extends |
|---|---|---|---|---|
| ADR-158 | — | — | — | — |
| ADR-159 | — | — | — | **ADR-124** |
| ADR-162 | — | — | — | — (see open issue 4) |
| ADR-163 | — | — | — | — |
| ADR-164 | — | — | — | — |
| ADR-165 | — | — | — | — |
| ADR-166 | — | — | — | — |
| ADR-167 | — | **ADR-086, ADR-106** | — | — |

## Checks

| check | result |
|---|---|
| `uv run pytest tests/unit/test_policy_adrs.py -q` | **169 passed** (8 passed for ADR-158/159/162–167 alone) |
| `adr-index.sh --check docs/adr` (read-only preview; index not regenerated) | all eight rows parse: title, `SEED-11 (Round 11 Stage B, T1; unit SEED-11b)`, `Accepted` — no `—` cells |
| sha256 of WV-01/02/03 and C-3 re-computed vs `PD/design/S6-ratification-applied.md` §5 | identical |
| grep of the eight ADRs for personal e-mail / name | clean (only `contact@surveillancegraph.org`, the project alias) |

Not run (not this unit's check): `check_spec_src.py` — its ADR-set = Appendix F check is expected to fail until SEED-12
adds the Appendix F rows and the index is regenerated.

## Open issues (for the orchestrator / other units)

1. **B-9 Class R standing go.** Appendix A T1 lists it among the adopted words SEED-11 ADRs must store, but §7 gives
   ADR-161 (release model v2) to P35.12. No ADR in 157–167 stores it; decide whether ADR-149 (OM-20) or P35.12's ADR-161
   carries the verbatim sentence + sha256 (`e4e24975…`, S6 §5).
2. **SIG-UI-021/022 wording amendment** (D-K0-6, "amends SIG-UI-021/022 wording"; K0 §7 text) is not in PLAN §6.3; no
   owner (SEED-12 or PLAN-11C) and no §6.5 "weakening = waiver" check is assigned. ADR-158 records it as owed, not applied.
3. **WV-01 vs C-5.** WV-01 says the legal home is "disclosed on the site"; at C-5 the operator declined the
   "'A single independent maintainer'" option and chose "Omit until I write it" for About's "who runs SIG". ADR-165
   carries the disclosure wording/placement to the copy batch rather than settling it.
4. **ADR-132.** J3 §8.1 / D-J3-6 call the snapshot decision "a new ADR extending ADR-132"; §7 gives ADR-132's
   `Extended by` line only to ADR-161. ADR-162 claims no extension; SEED-11d should not append ADR-132 → ADR-162 unless
   the orchestrator decides otherwise.
5. **E2 label text (ADR-167)** is not operator-confirmed. ADR-167 stores both forms (PLAN §5.10's two-sentence pin,
   `f62f9e98…`; E2-05's three-sentence draft, `c7e4f78b…`); the copy batch picks one and records confirmation against the
   sha256 (ADR-167 is not edited afterwards).
6. **Catalog drift.** `ticket_catalog.csv` R11-GOV-01 still says the five registry values become "operator-reported";
   PLAN/TS-09 require "the operator's own determination (no counsel)" (ADR-167 governs). P34.16's contract (T3) should use
   the PLAN wording.
7. **ADR-124's third revisit trigger** is engaged by ADR-159 (allow-recording becomes rule-driven); its recorded
   evaluation is SEED-11d's.
8. ADR-159's and ADR-166's T4 dependencies: the new OPEN rows "SEC-003 owner" and "the ADR-124 allow row" (Appendix A
   T4) are cited, not created, here.
