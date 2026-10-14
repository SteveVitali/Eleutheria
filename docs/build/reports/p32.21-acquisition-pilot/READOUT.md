# P32.21 acquisition pilot — measured readout

**Schemas:** `acq-pilot-batch/1` · `acq-pilot-funnel/1` · `acq-pilot-gap-ledger/1` · `sig.acq-pilot-return-pass/1` · `acq-pilot-readout/1` (selection `acq-pilot-select/1`).
**`live_verification=false` — descriptive only:** the preregistered S5 matched discovery comparison was not run; every number derives from committed artifacts (offline replay) or the research inventory (estimates). `captured_live` is 0 for every family; `measured_minutes` is never fabricated; fixture success closes no live outcome. No causal superiority claim is made or implied.

## Batch — five families under the live-stage ceilings

Ceilings: ≤5 families (incl. the three pilot cities) · ≤2 incremental non-portfolio families · ≤10 approved documents/aggregate rows per family · ≤2 new protocol families. **Observed:** 5 families (3 portfolio + 2 incremental); ≤10 docs/family enforced per slice; 0 new protocols.

| family | slot | role | candidates | excluded | rule |
|---|---|---|---|---|---|
| `okc-municipal` | portfolio | Oklahoma City dossier family (dossier_okc) | SRC-001 | — | P-SEL-1 |
| `tulsa-municipal` | portfolio | Tulsa dossier family (dossier_tulsa) | SRC-002 | — | P-SEL-1 |
| `san-diego-municipal` | portfolio | San Diego dossier family (dossier_san_diego) | SRC-003, SRC-004, SRC-005 | SRC-027 | P-SEL-1 |
| `oklahoma-state` | incremental | contract/acquisition chain | SRC-007, SRC-006 | SRC-009, SRC-008 | P-SEL-2 |
| `california-state-auditor` | incremental | independent oversight | SRC-011 | — | P-SEL-3 |

## Rejected alternatives (all recorded)

| candidate | family | score | reason |
|---|---|---|---|
| `SRC-002` | Tulsa Flock policies integration and executed contra | 25 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-003` | San Diego technology inventory and annual reports | 25 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-004` | San Diego Sunshine Act goods/services contracts | 25 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-001` | OKC Flock council amendment policy packet | 23 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-009` | Oklahoma JAG-LLE local equipment funding | 21 | no_recorded_award_gap — award/funding family — S5 admits one only when a named local procurement has a traceable award gap; no dossier |
| `SRC-005` | San Diego Privacy Advisory Board recommendations | 18 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-022` | DOJ COPS technology/equipment award documents | 17 | no_recorded_award_gap — award/funding family — S5 admits one only when a named local procurement has a traceable award gap; no dossier |
| `SRC-008` | Safe Oklahoma Grant program awards and reports disco | 16 | no_recorded_award_gap — award/funding family — S5 admits one only when a named local procurement has a traceable award gap; no dossier |
| `SRC-026` | UK Algorithmic Transparency Recording Standard publi | 15 | p31_owned — joins to a P31.12/.13-owned source — consumed/improved under prior decisions only, never re-onboarded (SIG-ACQ |
| `SRC-024` | DLA LESO 1033 equipment holdings/transfers subset | 14 | preflight_screening_owed — Part VIII screening is owed work — a family flagged for possible excluded-category content cannot enter a boun |
| `SRC-025` | FAA Part 107 waiver issued records | 13 | preflight_screening_owed — Part VIII screening is owed work — a family flagged for possible excluded-category content cannot enter a boun |
| `SRC-023` | DHS privacy impact assessments commercial LPR | 9 | p31_owned — joins to a P31.12/.13-owned source — consumed/improved under prior decisions only, never re-onboarded (SIG-ACQ |
| `SRC-027` | San Diego ALPR network audit metadata and safe aggre | -8 | blocked — blocked disposition — rights/sensitive rejection is score-independent |
| `SRC-027` | San Diego ALPR network audit metadata and safe aggre | -8 | prohibited_metadata_only — rejected — the Part VIII excluded content is permanently barred (E4-B3: the workbook path stays metadata-only  |
| `SRC-027` | San Diego ALPR network audit metadata and safe aggre | -8 | portfolio_member — inside a pilot-city lineage group — its targets ride the dossier family's own live return pass, never a new fa |
| `SRC-012` | Seattle OIG annual surveillance usage reviews | 22 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-010` | Sourcewell public safety cooperative contracts | 20 | capacity — eligible acquisition-shape candidate outranked by the selected family under acq-score/1 rank order — the two i |
| `SRC-015` | NYC DOI OIG-NYPD surveillance oversight | 19 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-016` | NYC Comptroller surveillance procurement and audits | 18 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-017` | Chicago OIG ShotSpotter evaluation and follow-up | 15 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-018` | BART surveillance reports policies and public decisi | 15 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-013` | San Jose privacy decisions and algorithm register | 14 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-021` | Santa Clara County surveillance impact and oversight | 14 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-014` | Norman police ALPR policy and amendment discovery | 12 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-020` | Boston annual surveillance report and supplements | 12 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |
| `SRC-019` | Berkeley surveillance annual reports policies MOUs | 10 | capacity — eligible oversight-shape candidate outranked by the selected family under acq-score/1 rank order — the two inc |

## Funnel + maintenance burden

Stages: `discovery` → `candidate_qualification` → `approval_gate` → `capture` → `extraction` → `link_support` → `publication_eligibility`.

| family | captures (offline) | claims | unique assertions | docs/targets | protocols | verdict |
|---|---|---|---|---|---|---|
| `okc` | 3 (live 0) | 37 | 14 | 3 / 6 | 2 (new 0) | **continue** |
| `tulsa` | 3 (live 0) | 16 | 12 | 3 / 6 | 1 (new 0) | **improve** |
| `san-diego` | 6 (live 0) | 37 | 32 | 4 / 9 | 3 (new 0) | **continue** |
| `oklahoma-state` | 0 (live 0) | 0 | pending | 4 / 4 | 2 (new 0) | **continue** |
| `california-state-auditor` | 0 (live 0) | 0 | pending | 2 / 2 | 2 (new 0) | **continue** |

Blocked / failed / rights-gated targets stay visible with reasons + retry budget:

- `SRC-002` (tulsa-municipal): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-003` (san-diego-municipal): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b); recorded 403 on a prior retrieval — retry budget 2/target
- `SRC-004` (san-diego-municipal): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-007` (oklahoma-state): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-001` (okc-municipal): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b); recorded 403 on a prior retrieval — retry budget 2/target
- `SRC-006` (oklahoma-state): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-011` (california-state-auditor): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-012` (seattle-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-009` (oklahoma-state): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-010` (sourcewell-cooperative): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-015` (nyc-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-005` (san-diego-municipal): screening_required — drafted screen recorded; the B-42 agent clear is owed at capture (P37.16a/b) — retry budget 2/target
- `SRC-016` (nyc-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-022` (us-federal-doj-cops): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-008` (oklahoma-state): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-017` (chicago-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-018` (bart-district): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-026` (uk-government): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-013` (san-jose-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-021` (santa-clara-county): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-024` (us-federal-dla): screening_required — Part VIII screen owed — retry budget 2/target
- `SRC-025` (us-federal-faa): screening_required — Part VIII screen owed — retry budget 2/target
- `SRC-014` (norman-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-020` (boston-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-019` (berkeley-municipal): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-023` (us-federal-dhs): rights undetermined (3 lanes) — routed to review — retry budget 2/target
- `SRC-027` (san-diego-municipal): rejected — excluded content permanently barred (E4-B3); blocked — rights/sensitive rejection — retry budget 2/target

## Before/after gap ledger — unique contributions

12 supported question slugs; 16 supported solely by the portfolio dossier family; double-counted=0; mirror-as-independent=0; P31-duplicate-onboarding=0.

- `okc` — supports 10 slugs (0 unique, 6 shared), 14 unique assertions
- `tulsa` — supports 6 slugs (6 unique, 0 shared), 12 unique assertions
- `san-diego` — supports 11 slugs (10 unique, 0 shared), 32 unique assertions
- `oklahoma-state` — pending_live — the gated slice has not run; expectations are never counted as closures
- `california-state-auditor` — pending_live — the gated slice has not run; expectations are never counted as closures

## Recommendations (descriptive — no causal claim)

### `okc` → **continue**

- basis: completeness 34/36, mechanical_complete=true, release_valid=true, review=not_run; live slice owed by D-P32.18-1
- unique closure: 14 unique assertions across 12 questions — the scope partition, the amendment's owned-vs-partner distinction, the announced retention change and the memo's contract facts are nowhere else in the corpus
- cost: committed: 3 captures / 37 claims / 6 return-pass targets; measured_minutes none (no approved run)
- condition: D-P32.18-1: HG-03 per-target review then the bounded captures
- condition: independent semantic review (D-R10-HUMAN-1) before pilot_complete can be claimed
- stop if: any rights lane decided reject → stop the affected target
- stop if: a live capture contradicting the fixture replay → stop and re-review the packet
- stop if: if the records-channel follow-ups cannot resolve the contract-chain gap after the bounded slice, stop expanding this family (a scope decision)

### `tulsa` → **improve**

- basis: completeness 24/36, mechanical_complete=false, release_valid=true, review=not_run; live slice owed by D-P32.19-1
- unique closure: 12 unique assertions — the enacted policies' terms and the template's honest present_but_empty fields; the q5 contract-chain gate is unresolved by design
- cost: committed: 3 captures / 16 claims / 6 return-pass targets; measured_minutes none (no approved run)
- condition: D-P32.19-1: HG-03 per-target review then the bounded captures
- condition: independent semantic review (D-R10-HUMAN-1) before pilot_complete can be claimed
- stop if: any rights lane decided reject → stop the affected target
- stop if: a live capture contradicting the fixture replay → stop and re-review the packet
- stop if: if the records-channel follow-ups cannot resolve the contract-chain gap after the bounded slice, stop expanding this family (a scope decision)

### `san-diego` → **continue**

- basis: completeness 29/36, mechanical_complete=true, release_valid=true, review=not_run; live slice owed by D-P32.20-1
- unique closure: 32 unique assertions across 12 questions — the subscription-vs-hardware split, prime-vs-component roles and the proposed recommendation are uniquely evidenced
- cost: committed: 6 captures / 37 claims / 9 return-pass targets; measured_minutes none (no approved run)
- condition: D-P32.20-1: HG-03 per-target review then the bounded captures
- condition: independent semantic review (D-R10-HUMAN-1) before pilot_complete can be claimed
- stop if: any rights lane decided reject → stop the affected target
- stop if: a live capture contradicting the fixture replay → stop and re-review the packet
- stop if: if the records-channel follow-ups cannot resolve the contract-chain gap after the bounded slice, stop expanding this family (a scope decision)

### `oklahoma-state` → **continue**

- basis: acq-score/1 = 24 (P0 dossier), kind=improvement, join=existing_unpermitted; effort M estimated (never measured); 2 in-batch candidates (SRC-007, SRC-006); in-family excluded SRC-009, SRC-008
- unique closure: the batch's only family closing recorded OKC dossier gaps from a non-municipal provenance — the OMES statewide contract channel (q5 documentary leads) plus the DAC UVED program/authority chain (q6, the P0-dossier gap); a state record is not city self-report
- cost: 4 targets / ≤10 docs; effort M; measured_minutes none
- condition: HG-03: OMES portal access terms + state/vendor document rights and the OSCN historical-version basis reviewed
- condition: Part VIII screening (status not_assessed) before capture
- condition: statute versions stay distinct — the DAC program description is never legal adjudication, and no universal OKCPD applicability is asserted
- stop if: any rights lane decided reject → stop
- stop if: content-admissibility or screening failure → stop
- stop if: if the bounded slice costs beyond the recorded effort band, stop and re-scope — expansion is a new scope decision

### `california-state-auditor` → **continue**

- basis: acq-score/1 = 23 (P1 bounded pilot), kind=improvement, join=existing_unpermitted; effort L-M estimated (never measured); 1 in-batch candidates (SRC-011)
- unique closure: the batch's only non-municipal independent provenance (I=3, a state auditor) — findings + agency survey + recommendations give the CA portfolio city a governance baseline no self-report can provide
- cost: 2 targets / ≤10 docs; effort L-M; measured_minutes none
- condition: HG-03: the report + survey pages' rights reviewed (municipal/state publication is not auto-CC0)
- condition: survey answers carry the Auditor's provenance as one account — never independently verified respondent facts
- condition: historical scope labelled (2019–2020 baseline, T=1) — never asserted current
- stop if: any rights lane decided reject → stop
- stop if: content-admissibility or screening failure → stop
- stop if: if the bounded slice costs beyond the recorded effort band, stop and re-scope — expansion is a new scope decision

## Gate packets / return pass

`sig.acq-pilot-return-pass/1` `acq-pilot-p32.21-live-pass` — status `prepared_not_executed`, deferral **D-P32.21-1** (OPEN). Approval refs: none exist (never fabricated). Portfolio slices stay pinned to D-P32.18-1, D-P32.19-1, D-P32.20-1.

## Expansion

Any family beyond this batch is a **new scope decision** — the ceilings are hard, not soft targets.
