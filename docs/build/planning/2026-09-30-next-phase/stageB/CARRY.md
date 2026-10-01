# Stage B carry list (orchestrator)

Items surfaced by seed units that a later unit (or the operator) must resolve. Each: source unit · item · owner.

- SEED-11a · ADR requirement ids cite SEED-12a's draft map (`stageB/T1_id_map.csv`) — re-check every new ADR's ids against the final map · SEED-12c
- SEED-11a · ADR-155 dated at the B-22 round (04:33:54Z) rather than A-12's (04:09:43Z) — acceptable (it also records B-22's Preact/JSON-LD adoption); no change
- SEED-11a · ADR-155 also narrows ADR-091 Decision 1 and the React choice (ADR-091 D2 / ADR-097 D1) — status lines? · SEED-11d decides, orchestrator reviews
- SEED-11a · ADR-148 extends ADR-073; ADR-150 extends ADR-126 (agent interpretation; not in §7) · SEED-11d (optional `Extended by` lines)
- SEED-11c · RISK-P0-06 closes by ADR-168 (plan §6.5) — risk-register / BL-001 append · SEED-14 (T4)
- SEED-11c · D-P30.3-COUNSEL reads DONE in the main DEFERRALS table but OPEN in a summary table · SEED-14 (T4)
- SEED-11c · plan §6.3 cites "SIG-CONTRIB-030a" — correct id is SIG-INGEST-030a (also SIG-INGEST-029) · SEED-12b
- SEED-11c · Q-E2-13 option c (adopted via A-4) calls for re-deciding the out-of-rule / counsel-flagged rows (aikner, Calgary, Lexington, MD iMAP); no plan row owns it · orchestrator: add a ticket row at T3 (rights re-review under ADR-169 guardrails, operator HG-03 lines as needed)
- SEED-11c · E4-R4a/R4b `recommendation` cells in decision_catalog are an earlier S4c draft; ADR-169 records the answer as presented (round-26 clarification) · no change (log is authoritative)
- SEED-11b · B-9 Class R standing-go sentence (S6 hash `e4e24975…`) has no seed ADR home (ADR-161 is P35.12's) → record it at T5 as a GATE DECISIONS `kind: pre-authorization` row (expires next sub-round GATE or 30 days; void on ratchet regression / Part VIII screen change / new source) and cite it from ADR-149 · SEED-17 (T5) + orchestrator
- SEED-11b · SIG-UI-021/022 amendment called for by D-K0-6 is not in plan §6.3; check whether it weakens a MUST (then it is a waiver needing the operator) · SEED-12b
- SEED-11b · WV-01 "disclosed on the site" vs C-5 "Omit until I write it": the legal-home disclosure must not name the operator or describe them beyond the adopted WV-01 sentence until they write the About text · T3 (copy-batch contract) + HANDOFF note
- SEED-11b · ticket_catalog R11-GOV-01 says counsel values become "operator-reported"; P34.16's contract must say "the operator's own determination (no counsel)" (TS-09) · SEED-13 (T3)
- SEED-11b · ADR-159 / ADR-166 cite T4's new OPEN rows ("the ADR-124 allow row", "SEC-003 owner") — create them · SEED-14 (T4); ADR-124's third revisit trigger evaluated · SEED-11d
- SEED-12a · `check_spec_src.py` id count will fail after BUILD.sh (777 vs 715) unless the 62 new §56 ids are appended to its `FOLD_BACK_IDS` (list in `docs/build/runs/SEED-12a.md`) · SEED-12c
- SEED-12a · spec version line (`00_front_part0.md:5`, 1.1.0) not bumped · SEED-12c
- SEED-12a · owners to confirm: SIG-OPS-007→P35.2, SIG-SEC-008→P35.1a/b, SIG-SEC-009→P35.4, SIG-CONF-010→P35.60 (P35.49 dropped) · SEED-13 (T3)
- SEED-12a · SIG-ENG-031 amendment should cite SIG-MEM-007 ("CI green"); Appendix G.7 needs a row for Part XII · SEED-12b/12c
- SEED-12a · seven ids beyond plan §6.2 (SIG-MEM-012, ENG-044/045/046, SEC-010/011, REL-015) — each traced to a ratified answer or cited note; keep (orchestrator review: all trace to A-21, A-13, C-10/F5, F5/H2, A-16, J1 NEW-9, B-20) · keep
- SEED-12a · ADRs citing "final id assigned by SEED-12" → update to final ids from `stageB/T1_id_map.csv` · SEED-12c
- SEED-12a · PLAN-11B / PLAN-11C must register SIG-TRANSP / K13 prefixes in §0.3 · SEED-13 contracts for PLAN-11B/11C
- SEED-12a · 62 new coverage-matrix rows as MISSING routed to owners · SEED-14 (T4)
- SEED-11d · guard must accept the appended `## Status updates` blocks and `### Trigger evaluation` subsections on landed ADRs (message sent to SEED-02a) · SEED-02a
- SEED-11d · SEED-15's `trigger_sha256` must hash revisit-trigger text only up to the first `### Trigger evaluation` · SEED-15
- SEED-11d · RISK-P15-29 still describes the release gate WV-04 retires → appended correction · SEED-14
- SEED-11d · counsel-dormant restatements for the 13 ADRs in F3 §5.4 (ADR-182 names them) not appended → append `Qualified by ADR-182` lines · SEED-12c
- SEED-11d · ADR-032 → ADR-050 supersession line added beyond Appendix A (F-249; ADR-050 "Closes out: ADR-032") — orchestrator keeps it
- orchestrator · ADR-002 `Qualified by ADR-189` status line appended (WV-11 makes the one exception to it)
- SEED-11d · **operator question (GATE-B packet):** ADR-183's acceptance covers "all ≈8,088 currently public rows" — do rows re-ingested after 2026-10-01 from the same express-terms sources (e.g. the TxDOT republish refreshing) also fall under it? Recommended reading to offer: yes for the same sources as of 2026-10-01 (they keep refreshing), new sources follow A-9 · GATE-B packet
- T2-α · history mode must exempt the 53 restored GATE DECISIONS rows from R2 (>48 h back-dated) and check them in restored-dates-vs-`git blame` mode · SEED-02a (+ policy entry)
- T2-α · SEED-05: append `## PHASE LOG — Round 11` after the new LEDGER date-correction section (PHASE LOG must be the last region); PHASE LOG entry drafts are in `docs/build/runs/SEED-01-04-06-07.md` · SEED-05
- T2-α · SEED-08 owns date corrections for runs/pr/readouts/DEFERRALS/manifest; SEED-09 appends index repairs below the DC-BI table under a new header; SEED-10 cites DC-L-01…03 and appends to the memory-repair README · SEED-08/09/10
- T2-α · CF-03 queue path = `docs/build/reports/memory-repair/pending_transitions.csv` (columns are SEED-04's design, labelled) · SEED-13/14
- T2-α · full A1 delta incl. GCP + CI keys still owed before T6 · orchestrator (T6)
