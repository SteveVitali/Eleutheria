# GATE-G6 — pending readout

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/420_GATE-G6__11c-check-in.md`.
Decision domain: the 11C check-in — budget, publication, rights (ING-GO-D
for Wave D + the Wave-D HG-03 flip list), the 11D OM-20 list as drafted by
PLAN-11D, the Class R standing-go renewal — and nothing else; each line's
default is non-action. The same sitting hosts P36.72b's HG-11 Class S
readout — a decision line of its own.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] The packet presented is P36.73's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due.
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted.
- [ ] The 11D OM-20 list (if any) names exact row ids traceable to written PLAN-11D contract headers with `expires:` set; the Class R renewal (if given) is quoted with its expiry; ING-GO-D and the Wave-D flip list are recorded as answered or defaulted.
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 421 only after the answer.

## Packet (agent-drafted)

<!-- agent-drafted:begin sha256=7ecdede4ddc9cd4f28183ca8328fb8338b6f0852822ce84649a1b8007dfead90 -->
**Agent-drafted GATE-G6 packet** — composed by P36.73 before the operator
answers; every default is non-action; ``continue`` answers **batch** lines
only; own-words, publication, rights, Part VIII, identity, money and OM-20
lines each need a verbatim answer; silence = pause (OM-18), never consent.

**1. Budget** — *(status lines: batch)*

- Infra month-to-date + forecast vs the $300/mo ceiling — **committed spend ledger (7 rows): latest — month=2026-10; surface=storage/edge; provider=cloudflare-r2; category=basemap hosting (sig-basemap + tiles.surveillancegraph.org); amount_usd=2.00; source_label=estimate; evidence=docs/build/reports/spend/SPEND_LEDGER.md; note=outside-cloud-account (OD-02/OD-03); P36.33 / SIG-UI-100 / SIG-STORE-003:**. *Default: none (status; information only).* **batch**
- agent usage ledger: agent_usage.csv present (1 rows) — reported, not capped (A-2b). *Default: none.* **batch**
- The recorded 11C/11D cost lines (committed rows, estimates/inferences — never measured billing): the 11C projection ≈ +$14.70/mo (optional Cloud Armor ≈ $6, release cadence ≈ $4, Wave B ≈ $2.5, basemap on R2 ≈ $2, status lane ≈ $0.2 → cumulative ≈ $111–121/mo at the S1a upper end) and the 11D projection ≈ +$11.90/mo (security baseline ≈ $5, Wave C ≈ $2.2, conditional intake ≈ $2, conditional Wave D ≈ $1.5, evidence store ≈ $0.5, WACZ ≈ $0.2, keyed 511 ≈ $0.2, canary ≈ $0.1, watch lane ≈ $0.1, raw archive ≈ $0.1 → ≈ $123–133/mo +≈ 1 domain). *Default: none.* **batch**
- The 11D projection against $300 stands well under the ceiling at draft time; any line that would exceed it is a money line needing its own verbatim answer — none identified at draft time. *Default: none.* **batch**

**2. Publication** — *(verbatim lines)*

- What 11C published: P36.72b — the core-surfaces release under its own signed, candidate-specific **HG-11 Class S readout — held in this same sitting** (P36.72b's plan cell, verbatim). At draft time the promote leg remains **queued** (`prepared_not_executed` under `D-P36.72b-1`; the packet `docs/build/reports/p36.72b-promotion/` carries the evidence: P36.72a's `sig.core-surfaces-acceptance/1` PASS fixture-verified + the 9/9 `agent-verified` walkthrough record over the fixture corpus — the readout asks its own verbatim line, never batch): **nothing new has been promoted, and the earlier P35.63 first-model-release promote also stays queued**. *Default: the promote stays queued — no release promoted at this sitting.*
- P36.70 — the second-release acceptance rehearsal — runs under the Class R standing go if it is still valid; its precondition (the P36.72b promote) lands in this same sitting, so its contract's own fallback applies (Class S under the operator's authority records — `D-P36.70-1` records the leg queued `prepared_not_executed`). *Default: the rehearsal stays queued — never pre-authorised beyond the operator's authority records.*
- What 11D plans next: the 11D rows run under the OM-20 list below only if it is approved; every publication line stays the operator's. *Default: none (status).* **batch**

**3. Rights** — *(verbatim lines)*

- **ING-GO-D** — Wave D: the next ingestion wave — the keyed-API unblocks `D-SOURCES.7-2`/`D-SOURCES.8-2` (OP-13's key registration, due by this sitting), the federal resume `D-FEDERAL.1-1` (P37.11), the Wave-D screened lanes (P37.47–53), portal/WFS families (P37.69a/b) and the activation row (P37.54) — with the **Wave-D HG-03 flip list** (OP-26) naming N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08 — the plan cell's verbatim set. I8-Q5 (Wave-D scope) was answered `a` at GATE-P — Wave D is in scope (S6); it is recorded, not re-asked. *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them.*
- Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's check). *Default: no flips.*
- **Title/note recorded, not resolved:** the plan row's title carries `ING-GO-C/D` while its S4c note reads `collects ING-GO-D` — this packet drafts the note's content (ING-GO-C was GATE-G5's Wave-C line, answered at the recorded 2026-10-25 sitting; the packet reads the recorded answer, never re-asks it). The same drift shape GATE-G5's contract recorded for `ING-GO-B`. *Default: none (status).* **batch**
- ING-GO-C's recorded answer (GATE-G5 GATE DECISIONS, 2026-10-25T18:40Z — "Approve ING-GO-C (rec.)" selection + the verbatim go recorded) and the Wave-C/vendor HG-03 flip list (352 ids, "Every registered source" scope + "Pre-approve all 352 ids (rec.)") are read, not re-litigated; the P37.2 Wave-C legs stay queued under their recorded go. *Default: none.* **batch**
- A-7 lines answered at GATE-G5 ("Approve all four (rec.)") — recorded, not re-asked. *Default: none.* **batch**

**4. The 11D OM-20 list** — *(an OM-20 line: approved only by its own verbatim line, never by `continue`)*

- PLAN-11D's draft (row 418's run ledger — built only from written `Production mutations` headers; each entry is approve-verbatim or nothing; `expires:` the next GATE (GATE-ACCEPT-R11, or an inserted gate if an 11D re-split fired — recorded not-fired); `voided-by:` a red probe, a failed restore point or a `production` read that contradicts a record) — the list below is the ask itself, approved only by its own verbatim line, never by `continue`. *Default: nothing pre-authorised — each named mutation pauses in-ticket.*

| row | id | mutation (contract header) | restore point |
|---|---|---|---|
| 421 | P37.3 | evidence-bucket retention-policy write + off-instance replica / cross-project copy jobs | policies/jobs removed; copied objects are additive (retention-governed) |
| 422 | P37.4a | security-baseline `production` writes — scan/SBOM/cosign wiring into the deploy path | deploy-path config reverted to the prior committed state |
| 423 | P37.4b | restricted-byte access posture — audited access, Data Access audit logs + exclusion filter, ENCRYPTED_ONLY | access posture reverted; filter removed; ENCRYPTED_ONLY unset |
| 432 | P37.11 | `hosted` SAM.gov sweep resume (fetch + claim writes from where it stopped) | sweep paused; wrong claims superseded by correction claims (append-only) |
| 433 | P37.12 | keyed US-511 `live` run after the operator's key registration | targets left `ingestion_permitted=false`; job paused |
| 434 | P37.70 | keyed AU traffic-camera `live` runs (QLDTraffic + `NSW Live Traffic`) | targets left `ingestion_permitted=false`; job paused |
| 437 | P37.15 | scheduled parser-canary `production` job | job disabled/removed |
| 455 | P37.31 | `hosted` re-ingest writing the dated decision predicates | ingest paused; wrong predicates superseded (append-only) |
| 456 | P37.32 | `hosted` detector run writing `contract_expiring` findings + renewal tasks | detector schedule disabled; findings superseded |
| 457 | P37.33 | watch-lane job's scheduled `production` run | lane job paused |
| 459 | P37.35 | `hosted` detector re-run under the new routing and mapping campaigns | re-run halted; routing reverted |
| 470 | P37.46a | crosswalk-intake `production` writes (UEI/SAM, ORI, GEOID, QID lanes) | intake paused; written claims corrected by supersession |
| 471 | P37.46b | cascade materializer's `production` writes (tiers 0–1 + tier-2 'possibly the same') | materializer paused; edges superseded, never deleted |
| 483 | P37.56 | WACZ capture runs for the HTML document sources | capture jobs paused; captures are evidence-store objects (retention-governed) |
| 487 | P37.59 | dark intake-service deploy (receiver not operating; loopback only) | service scaled to zero; `operational=false` stands |

- 15 rows, each traceable to a written PLAN-11D contract header — a row without a written contract cannot be listed. *Default: none.* **batch**
- Never on any list: every HG-03 flip (P37.16a/b's per-family lines, the Wave-D flip list OP-26), every HG-11 readout (P37.65b's promote, P36.72b's Class S readout at this sitting), the Part VIII-screened capture runs (rows 438/439), the P37.36 archive write, the P37.42 API roll, the P37.55 external archival deposit, P37.71's purge deploy/uses, every publish line (P37.45, P37.63, P37.64, the capstones — they ride P37.65's Class S path), any Class R promotion if the standing go has lapsed, and any API roll that changes a public route's response — the never-pre-authorised classes of plan §3.3. *Default: none.* **batch**
- 11C legs whose GATE-G5 pre-authorisation expires at this gate unrun (from the RETURN PASS map at draft time — the 13-row OM-20 11C list's queued legs + every go naming `expires next GATE`/`expires GATE-G6`): P35.14a-live-vocab-seed (P35.14a); P35.15a-live-technology-vocab (P35.15a); P35.16-geometry-corrections-live (P35.16); P35.17-boundary-source-capture (P35.17); P35.1b-fleet-sweep-live (P35.1b); P35.2-alert-roll (P35.2); P35.23-rdc-probe (P35.23); P35.24-subject-rekey-live (P35.24); P35.25-declared-lineage-live (P35.25); P35.59-dark-cutover (P35.59); P35.62-staging-candidate (P35.62); P36.13-flip (P36.13); P36.33-host (P36.33); P36.43-job-create (P36.43); P36.44-trigger-create (P36.44); P36.46-backfill (P36.46); P36.75-write (P36.75); P36.76-legA (P36.76); P36.76-legB (P36.76); P36.77-legA (P36.77); P36.77-legB (P36.77); P36.78-legA (P36.78); P36.78-legB (P36.78); P36.79-seal (P36.79) — re-listed by row id or left to an in-ticket go. *Default: each re-asks in-ticket (nothing pre-authorised — each named mutation pauses in-ticket).*

**5. Class R standing-go renewal (B-9)** — *(verbatim line; never renewed by `continue`)*

- The operator's adopted text (agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z — retro: the B-9 answer record, GATE-P's GATE DECISIONS row; sha256 `e4e24975b854…`; renewed verbatim at GATE-G5 2026-10-25T18:40Z): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." — renewed verbatim or not; it expires at the next sub-round GATE or after 30 days, whichever is first (the G5 renewal's recorded bounds: GATE-G6 or 2026-11-24 — it lapses inside this sitting's own window); it is void on any ratchet regression, Part VIII screen change or new source (TS-13); a renewal is recorded as a GATE DECISIONS `kind: pre-authorization` row. *Default: it lapses → every 11D release is Class S, and P36.70's rehearsal runs under the operator's authority records only.*

**6. Status** — *(information only; batch)*

- Per-row layered status: `docs/build/reports/acceptance/11C.md` (P36.73's acceptance note; the live sweep is queued — the promoted release does not exist — see the note). *Default: none.* **batch**
- Live-leg queue at draft time (98 legs): P34.3-live (P34.3); P34.4-live (P34.4); P34.4-human-check (P34.4); P34.5-testbudget-delete (P34.5); P34.5-export-link (P34.5); P34.5-first-report (P34.5); P34.6-export (P34.6); P34.6-lifecycle (P34.6); P34.6-relabel (P34.6); P34.6-fullrestore (P34.6); P34.6-post-deploy-redrill (P34.6); P34.17-L2 (P34.17); P34.18-L2 (P34.18); P34.21a-L1 (P34.21a); P34.21b-L1 (P34.21b); P34.21b-L2 (P34.21b); P34.38-bidnet-terms (P34.38); P34.39b-firstfire-wave (P34.39b); P34.39b-peel-on (P34.39b); P34.39b-final-read (P34.39b); P36.2-terms (P36.2); P34.40-web-roll (P34.40); P34.40-lb-routes (P34.40); P34.42b-jobs-iam (P34.42b); P34.43-exec-host (P34.43); P34.43-audit-login (P34.43); P34.43-recovery-login (P34.43); P34.49-scan (P34.49); P34.49-seal (P34.49); P34.44b-quality-probe (P34.44b); P34.44b-baseline (P34.44b); P34.45-er-rerun (P34.45); P34.46-slot (P34.46); P34.46-soak (P34.46); P34.47-sweep-packet (P34.47); P35.57-api-roll (P35.57); P35.5-r2-mirror (P35.5); P35.67-l1-cutover-probe (P35.67); P35.67-l2-cert-renewal (P35.67); P35.1a-live-scheduled-ops (P35.1a); P35.1a1-seed-declared-jobs-live (P35.1a1); P35.11-l1-roll-seed-manual-runs (P35.11); P35.11-l2-plus-zero-reruns (P35.11); P35.11-l3-resume-schedules (P35.11); P35.14a-live-vocab-seed (P35.14a); P35.14b-live-typing-check (P35.14b); P35.15a-live-technology-vocab (P35.15a); P35.15b-live-technology-backfill (P35.15b); P36.12-l0-wave-open (P36.12); P36.12-l1-acq08-layers-family-day (P36.12); P36.12-l2-acq09-flock-layers-family-day (P36.12); P36.12-l3-acq10-ate-family-day (P36.12); P36.12-l4-acq11-procurement-family-day (P36.12); P36.12-l5-acq12-disclosures-01-family-day (P36.12); P36.12-l6-acq13-disclosures-02-family-day (P36.12); P36.12-l7-acq14-documents-family-day (P36.12); P36.12-l8-acq15-documents-family-day (P36.12); P36.12-l9-flock-portal-probe (P36.12); P36.12-l10-close-materialize-resume (P36.12); P35.1b-fleet-sweep-live (P35.1b); P35.1c-dispatcher-consolidation-live (P35.1c); P35.16-geometry-corrections-live (P35.16); P35.17-boundary-source-capture (P35.17); P35.24-subject-rekey-live (P35.24); P35.25-declared-lineage-live (P35.25); P35.26-roles-and-time-live (P35.26); P35.41-freshness-live (P35.41); P35.53-release-infra (P35.53); P35.59-dark-cutover (P35.59); P35.61-live-pass (P35.61); P35.62-staging-candidate (P35.62); P35.63-dispatch-stage-verify-readout (P35.63); P35.63-promote-under-hg11 (P35.63); P35.64-sweep-packet (P35.64); P37.2-l1-pregrow-disk (P37.2); P37.2-l2-tier-bump (P37.2); P37.2-l3-national-run (P37.2); P37.2-l4-soak-read (P37.2); P37.2-l5-tier-revert (P37.2); P35.2-alert-roll (P35.2); P35.21-partner-name-audit (P35.21); P35.23-rdc-probe (P35.23); P36.76-legA (P36.76); P36.76-legB (P36.76); P36.77-legA (P36.77); P36.77-legB (P36.77); P36.78-legA (P36.78); P36.78-legB (P36.78); P36.13-flip (P36.13); P36.79-seal (P36.79); P36.33-host (P36.33); P36.38-roll (P36.38); P36.75-write (P36.75); P36.43-job-create (P36.43); P36.44-trigger-create (P36.44); P36.46-backfill (P36.46); P36.71-verify (P36.71); P36.72b-promote (P36.72b). *Default: none.* **batch**
- Carried legs: P37.2's Wave-C legs if their window extends past this sitting; legs whose window extends past this GATE are listed and carried; P36.12's Wave-B window 10-26 → 11-05 and P35.11's Wave-A window 10-19 → 10-23 elapsed unrun — recorded, never smoothed. *Default: none.* **batch**
- CI incidents: NIGHTLY-RED-1 — the scheduled `nightly.yml` runs on `main` failed 2026-10-07 → 10-20 (14 runs; the owed observation of `D-P34.7-1`/`D-P34.2-2`; repair routed separately). Anomalies and operator-side merges read from GitHub at the sitting. *Default: none.* **batch**
- The D-K2-1 top-50 organisation review (OP-14, ≈ 1–2 h of the operator's time) — due by the GATE-G5 sitting and carried; its outcome is reported or carried, never performed by a row. *Default: carried.* **batch**
- Whether PLAN-11D's Phase-4 review fired the 11D re-split rule (> 85 engineering rows or > 75 engineering runs → an inserted gate): 11D stood at 76 / 65.0 at PLAN-11D — the rule did not fire at draft time. *Default: none.* **batch**
- The launch-unmet MUSTs list (`D-R11-LATER-04` — the ADR-171 Stage-0 set SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024): owed, unmet at launch — carried to GATE-ANNOUNCE's spec-MUSTs list, recorded, never implied satisfied. *Default: none.* **batch**
- The isolation probe repeated at this GATE (plan §8.5) — the orchestrator's work, reported here. *Default: none.* **batch**
- The same sitting hosts P36.72b's HG-11 Class S readout (P36.72b's plan cell, verbatim) — a decision line of its own, never batch. *Default: none.* **batch**

<!-- agent-drafted:end -->

## Signature

<!-- Appended only at signing, by the commit that moves Status:. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-G6
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:7ecdede4ddc9
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
