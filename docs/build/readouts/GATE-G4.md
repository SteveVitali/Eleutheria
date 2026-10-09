# GATE-G4 — pending readout

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/260_GATE-G4__11a-check-in.md`.
Decision domain: the 11A check-in — budget, publication, rights (ING-GO-A/B
+ flip lists), the 11B OM-20 list, the Class R standing-go renewal — and
nothing else; each line's default is non-action.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] The packet presented is P34.47's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due.
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted.
- [ ] The 11B OM-20 list (if any) names exact row ids with expiry; the Class R renewal (if given) is quoted with its expiry; ING-GO-A/B and the flip lists are recorded as answered or defaulted.
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 261 only after the answer.

## Packet (agent-drafted)

<!-- agent-drafted:begin sha256=25ecd4644ba90b4807a272384b92071fec4b618f5651211f67aee045de02b722 -->
**Agent-drafted GATE-G4 packet** — composed by P34.47 before the operator
answers; every default is non-action; ``continue`` answers **batch** lines
only; rights/money/OM-20/own-words lines each need a verbatim answer;
silence = pause (OM-18).

**1. Budget** — *(status lines: batch)*

- Infra month-to-date + forecast vs the $300/mo ceiling — **committed spend ledger (4 rows): latest — month=2026-10; surface=domain; provider=squarespace; category=registrar/domains; source_label=pending; evidence=docs/build/reports/spend/SPEND_LEDGER.md; note=outside-cloud-account (OD-02/OD-03); operator-reported figure owed at the first monthly report**. *Default: none (status; information only).* **batch**
- agent usage ledger: agent_usage.csv present (1 rows) — reported, not capped (A-2b). *Default: none.* **batch**
- Lines exceeding the ceiling needing a verbatim money answer: none identified at draft time. *Default: none.* **batch**

**2. Publication** — *(verbatim lines)*

- What 11A published: republish #1 and republish #2 — each under its own verbatim in-ticket go, quoted not re-asked; at draft time both legs remain queued (see the queue) — **nothing has republished yet**. *Default: none (status).* **batch**
- 11B plans P35.63 — the first model release under a signed HG-11 readout ("single maintainer, no second reviewer"; "no human check performed"), with its date window and new route families. *Default: none (status).* **batch**
- **P35.57 API-roll go** — its own verbatim line (a roll that changes a public route's response is never pre-authorised); P35.57 is an improvement, not a gate — the 11B structural spine writes do not wait for it (A-20 = a). *Default: P35.57 pauses in-ticket (non-action).*

**3. Rights** — *(verbatim lines)*

- **ING-GO-A** — Wave A legs 2026-10-19 → 10-23, 14:00–20:00Z (P35.11; future-ok: scheduled: the contract's Wave-A window instants) with the operator's Wave A HG-03 flip list (OP-26; flips are operator-executed — one OP-25-signed commit or a signed GATE DECISIONS row naming each source id). *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them.*
- **ING-GO-B** — Wave B legs 10-26 → 11-05, one family a day (P36.12; future-ok: scheduled: the contract's Wave-B window) with the Wave B flip list (FEA-02). *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false`.*
- A-7/B-32 Part VIII screen lanes due in 11B — disclosed, not asked (B-42's agent clear is disclosed, never asked). *Default: none.* **batch**
- Carried, not asked unless ready: E4-R6a BidNet (terms captured by P34.38; due at GATE-G6 at the latest, S6R-28). *Default: none.* **batch**

**4. The 11B OM-20 list** — *(an OM-20 line: approved only by its own verbatim line, never by `continue`)*

- Candidates (the 19 OM-20 rows of 11B, exact ids): P35.5, P35.1a, P35.14a, P35.15a, P35.15b, P35.1b, P35.16, P35.17, P35.22, P35.24, P35.25, P35.26, P35.27, P35.32, P35.41, P35.46, P35.53, P35.59, P35.62 — each with its contract's mutation, restore point and rollback quoted by the PLAN-11B contracts (row 239); expiry: the next sub-round GATE (GATE-G5, or GATE-G4b if the re-split rule fires). *Default: nothing pre-authorised — each named mutation pauses in-ticket.*
- Never on any list: P35.57, P35.11, P35.14b, P36.12, P35.61, P35.63 and every HG-03 flip (incl. P35.17's boundary flip). *Default: none.* **batch**
- 11A legs whose S5-3 pre-authorisation expires at this gate unrun (from the RETURN PASS map at draft time): P34.18; P34.21a; P34.3; P34.4; P34.40; P34.42a; P34.42b; P34.43; P34.44b; P34.45; P34.49 — re-listed by row id or left to an in-ticket go. *Default: each re-asks in-ticket.*

**5. Class R standing-go renewal (B-9)** — *(verbatim line; never renewed by `continue`)*

- The operator's adopted text (adopted 2026-10-01T04:35:53Z — retro: the B-9 answer record, planning RATIFICATION_LOG round 12 / decision catalog; sha256 `e4e24975b854…`): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." — renewed verbatim or not; it expires at the next sub-round gate or after 30 days, whichever is first; void on any ratchet regression, Part VIII screen change or new source. *Default: it lapses → every release is Class S.*

**6. Status** — *(information only; batch)*

- Per-row layered status: `docs/build/reports/acceptance/11A.md` (P34.47's acceptance note; the live sweep is queued — see the note). *Default: none.* **batch**
- Live-leg queue at draft time (36 legs): P34.3-live (P34.3); P34.4-live (P34.4); P34.4-human-check (P34.4); P34.5-testbudget-delete (P34.5); P34.5-export-link (P34.5); P34.5-first-report (P34.5); P34.6-export (P34.6); P34.6-lifecycle (P34.6); P34.6-relabel (P34.6); P34.6-fullrestore (P34.6); P34.6-post-deploy-redrill (P34.6); P34.17-L2 (P34.17); P34.18-L2 (P34.18); P34.21a-L1 (P34.21a); P34.21b-L1 (P34.21b); P34.21b-L2 (P34.21b); P34.38-bidnet-terms (P34.38); P34.39a-osm-replay-readback (P34.39a); P34.39b-firstfire-wave (P34.39b); P34.39b-peel-on (P34.39b); P34.39b-final-read (P34.39b); P34.40-web-roll (P34.40); P34.40-lb-routes (P34.40); P34.42a-iam (P34.42a); P34.42b-jobs-iam (P34.42b); P34.43-exec-host (P34.43); P34.43-audit-login (P34.43); P34.43-recovery-login (P34.43); P34.49-scan (P34.49); P34.49-seal (P34.49); P34.44b-quality-probe (P34.44b); P34.44b-baseline (P34.44b); P34.45-er-rerun (P34.45); P34.46-slot (P34.46); P34.46-soak (P34.46); P34.47-sweep-packet (P34.47). *Default: none.* **batch**
- CI incidents, anomalies, operator-side merges read from GitHub at the sitting. *Default: none.* **batch**
- Managed certificate expires 2026-12-22 (live status read at the sweep). *Default: none.* **batch**
- RI-01 and the isolation probe repeated at this GATE (plan §8.5). *Default: none.* **batch**
- B-2's notice allowance (N-1…N-7 by sha256) ends here — every later sentence needs per-text confirmation. *Default: none.* **batch**
- Whether PLAN-11B's sizing review fired the 11B re-split rule (>85 engineering rows or >75 runs → GATE-G4b at the Wave-B activation boundary, S6R-15). *Default: none.* **batch**
- For the record: the REVIEW-R11 → GATE-ANNOUNCE rule (fix rows appended after row 510 + a new GATE-ANNOUNCE row + row 510 `superseded-by(row <n>)`; S6-F3, S6R-19). *Default: none.* **batch**

**Carried questions (only if not already answered at GATE-B)** — *(verbatim lines)*

- OP-24 (the leg-runner backstop, "decide by GATE-G4"): launchd → headless Devin CLI (needs `devin auth login`), operator-run at window opens, or no backstop; first windows open ≥ 2026-10-13. *Default: no backstop recorded.*
- Whether fallback mode B (headless Devin) is verified (`devin auth login` + a live `--agent-cmd` run). *Default: reported as not verified.*
<!-- agent-drafted:end -->

## Signature

<!-- Appended only at signing, by the commit that moves Status:. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-G4
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:25ecd4644ba9
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
