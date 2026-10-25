# GATE-G5 — pending readout

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/343_GATE-G5__11b-check-in.md`.
Decision domain: the 11B check-in — budget, publication, rights (ING-GO-C
for Wave C + the Wave-C/vendor HG-03 flip list + the A-7 lines due in
11C), the 11C OM-20 list as drafted by PLAN-11C, the Class R standing-go
renewal — and nothing else; each line's default is non-action.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] The packet presented is P35.64's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due.
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted.
- [ ] The 11C OM-20 list (if any) names exact row ids with `expires: GATE-G6`; the Class R renewal (if given) is quoted with its expiry; ING-GO-C and the Wave-C/vendor flip list are recorded as answered or defaulted.
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 344 only after the answer.

## Packet (agent-drafted)

<!-- agent-drafted:begin sha256=490ec9c9047ed4d3953bb076cfb6cae9eabe070a87a70f51fbf73e56f58a5f63 -->
**Agent-drafted GATE-G5 packet** — composed by P35.64 before the operator
answers; every default is non-action; ``continue`` answers **batch** lines
only; own-words, publication, rights, Part VIII, identity, money and OM-20
lines each need a verbatim answer; silence = pause (OM-18), never consent.

**1. Budget** — *(status lines: batch)*

- Infra month-to-date + forecast vs the $300/mo ceiling — **committed spend ledger (6 rows): latest — month=2026-10; surface=domain; provider=squarespace; category=registrar/domains; source_label=pending; evidence=docs/build/reports/spend/SPEND_LEDGER.md; note=outside-cloud-account (OD-02/OD-03); operator-reported figure owed at the first monthly report**. *Default: none (status; information only).* **batch**
- agent usage ledger: agent_usage.csv present (1 rows) — reported, not capped (A-2b). *Default: none.* **batch**
- The recorded 11B/11C cost lines (committed rows, estimates/inferences — never measured billing): ≈ $0.1/mo release storage, ≈ $0.04/mo candidate, the Wave-C ≈ $2.2/mo projection at the S1a upper end, Cloudflare/R2 (the $50.00/mo hard ceiling is a ceiling line, not measured spend) and registrar/domains (operator-linked billing evidence pending). *Default: none.* **batch**
- The 11C projection against $300 stands well under the ceiling at draft time; any line that would exceed it is a money line needing its own verbatim answer — none identified at draft time. *Default: none.* **batch**

**2. Publication** — *(verbatim lines)*

- What 11B published: P35.63 — the first model release under its own signed, candidate-specific HG-11 readout ("single maintainer, no second reviewer"; "no human check performed"), quoted not re-asked. At draft time both of P35.63's legs remain **queued** (`prepared_not_executed`; the promotion awaits the signature — the old GATE-G3 signature is superseded, not transferred): **nothing has been promoted, hosted, deployed or published**. *Default: none (status).* **batch**
- 11C plans P36.72b — the core-surfaces release under its own Class S readout (its cell names the same sitting as GATE-G6) — and P36.70 — the second-release acceptance running under the Class R standing go if it is still valid. Publication lines are never pre-authorised. *Default: none (status).* **batch**

**3. Rights** — *(verbatim lines)*

- **ING-GO-C** — Wave C legs window 2026-11-16 → 11-20 (P37.2; earliest 10-26 if P37.1, PKG-07 and Q-23 are early; the tier-bump go is P37.2's own in-ticket pause, not this list's) with the **Wave-C/vendor HG-03 flip list** (OP-26) naming the sources whose rows land in 11C. *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them.*
- Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's check). *Default: no flips.*
- A-7 lines due in 11C — the Part VIII screen lanes the 11C contracts name; each a rights line with its own verbatim answer, never batch. *Default: each pauses in-ticket.*
- **Title/note recorded, not resolved:** the plan row's title carries `ING-GO-B` while its S4c note reads `collects ING-GO-C for Wave C (P37.2 legs 11-16 -> 11-20), A-7 lines due in 11C` — this packet drafts the note's content and records the title token verbatim; ING-GO-B itself was GATE-G4's Wave-B line. *Default: none (status).* **batch**
- Q-23 (a), A-10 (no review) and I8-Q5 (a) were answered at GATE-P — recorded, not re-asked. *Default: none.* **batch**

**4. The 11C OM-20 list** — *(an OM-20 line: approved only by its own verbatim line, never by `continue`)*

- PLAN-11C's draft (row 340's run ledger — built only from written `Production mutations` headers; each entry is approve-verbatim or nothing; `expires: GATE-G6`, or an inserted gate if the 11C re-split rule fires) — the list below is the ask itself, approved only by its own verbatim line, never by `continue`. *Default: nothing pre-authorised — each named mutation pauses in-ticket.*

| row | id | mutation (contract header) | restore point |
|---|---|---|---|
| 346 | P35.2 | alerting-as-code roll: uptime checks, alert policies, notification-channel binding, log retention/restricted sink, `ops/probes/`+`ops/runs/` bucket versioning, `sig-probe` job rebuild | committed IaC text + recorded pre-state describes |
| 348 | P35.23 | restricted-bucket write of screened corpus slices + committed digests | digest list + bucket versioning |
| 351 | P36.76 | Axon Connect: screen records + page hashes + registry-row appends (single recorded GETs of public registration pages) | appended set's record; leg B is the operator's act |
| 352 | P36.77 | DocumentCloud/MuckRock: unauthenticated public-page GETs + registry appends + redacted-rendition records | appended set's record; activation stays operator's |
| 353 | P36.78 | Sourcewell/OMNIA: public-page GETs + appends + terms captures + redacted renditions | appended set's record; leg B operator's |
| 354 | P36.13 | rate-limit enforcement flip on the hosted deployment (defined → enforced, gate-pending) | prior deployment revision |
| 371 | P36.79 | restricted-bucket object write — the sealed relevance set's bytes | bucket versioning + committed sha256 |
| 374 | P36.33 | R2 host create (basemap host provisioning) | re-creatable from `basemap.lock.json` + JUR-01's pack |
| 385 | P36.75 | append-only claim write on the hosted spine (organisation-level Flock share-list claims, gate-pending) | additive — the written set's digest list |
| 386 | P36.43 | scheduler job create (status lane) | job-definition removal |
| 387 | P36.44 | scheduler job create (monthly cut + weekly materialize) | job-definition removal |
| 389 | P36.46 | append-only history backfill on the hosted spine (gate-pending) | appended set's digest list |
| 412 | P36.68 | mirror writes — content-addressed extract pushes + versions.json | content-addressed objects + index diff |

- 13 rows vs §8.1's recorded count of 10 — the plan anticipated "any further row a written `Production mutations` header names"; the four beyond its named nine are P36.76, P36.77, P36.78 and P36.43. Recorded as the drift it is, never resolved here. *Default: none.* **batch**
- Never on any list: P37.2's tier bump, P36.38 (an API roll that changes a public route's response), P36.72b's HG-11 readout, every HG-03 flip, and P36.70 if the standing go has lapsed — the never-pre-authorised classes of plan §3.3. *Default: none.* **batch**
- 11B legs whose GATE-G4 pre-authorisation expires at this gate unrun (from the RETURN PASS map at draft time — the 19-row OM-20 11B list's queued legs + every go naming `expires next GATE`/`expires GATE-G5`): P35.14a-live-vocab-seed (P35.14a); P35.15a-live-technology-vocab (P35.15a); P35.15b-live-technology-backfill (P35.15b); P35.16-geometry-corrections-live (P35.16); P35.17-boundary-source-capture (P35.17); P35.1a-live-scheduled-ops (P35.1a); P35.1b-fleet-sweep-live (P35.1b); P35.24-subject-rekey-live (P35.24); P35.25-declared-lineage-live (P35.25); P35.26-roles-and-time-live (P35.26); P35.41-freshness-live (P35.41); P35.5-r2-mirror (P35.5); P35.53-release-infra (P35.53); P35.59-dark-cutover (P35.59); P35.62-staging-candidate (P35.62) — re-listed by row id or left to an in-ticket go. *Default: each re-asks in-ticket (nothing pre-authorised — each named mutation pauses in-ticket).*

**5. Class R standing-go renewal (B-9)** — *(verbatim line; never renewed by `continue`)*

- The operator's adopted text (agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z — retro: the B-9 answer record, GATE-P's GATE DECISIONS row; sha256 `e4e24975b854…`): "Agents may promote a Class R release built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet regression, Part VIII screen change or new source." — renewed verbatim or not; it expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, Part VIII screen change or new source (TS-13); a renewal is recorded as a GATE DECISIONS `kind: pre-authorization` row. *Default: it lapses → every release is Class S, and P36.70's first Class R promotion becomes an in-ticket pause.*

**6. Status** — *(information only; batch)*

- Per-row layered status: `docs/build/reports/acceptance/11B.md` (P35.64's acceptance note; the live sweep is queued — the promoted release does not exist — see the note). *Default: none.* **batch**
- Live-leg queue at draft time (73 legs): P34.3-live (P34.3); P34.4-live (P34.4); P34.4-human-check (P34.4); P34.5-testbudget-delete (P34.5); P34.5-export-link (P34.5); P34.5-first-report (P34.5); P34.6-export (P34.6); P34.6-lifecycle (P34.6); P34.6-relabel (P34.6); P34.6-fullrestore (P34.6); P34.6-post-deploy-redrill (P34.6); P34.17-L2 (P34.17); P34.18-L2 (P34.18); P34.21a-L1 (P34.21a); P34.21b-L1 (P34.21b); P34.21b-L2 (P34.21b); P34.38-bidnet-terms (P34.38); P34.39b-firstfire-wave (P34.39b); P34.39b-peel-on (P34.39b); P34.39b-final-read (P34.39b); P34.40-web-roll (P34.40); P34.40-lb-routes (P34.40); P34.42b-jobs-iam (P34.42b); P34.43-exec-host (P34.43); P34.43-audit-login (P34.43); P34.43-recovery-login (P34.43); P34.49-scan (P34.49); P34.49-seal (P34.49); P34.44b-quality-probe (P34.44b); P34.44b-baseline (P34.44b); P34.45-er-rerun (P34.45); P34.46-slot (P34.46); P34.46-soak (P34.46); P34.47-sweep-packet (P34.47); P35.57-api-roll (P35.57); P35.5-r2-mirror (P35.5); P35.67-l1-cutover-probe (P35.67); P35.67-l2-cert-renewal (P35.67); P35.1a-live-scheduled-ops (P35.1a); P35.1a1-seed-declared-jobs-live (P35.1a1); P35.11-l1-roll-seed-manual-runs (P35.11); P35.11-l2-plus-zero-reruns (P35.11); P35.11-l3-resume-schedules (P35.11); P35.14a-live-vocab-seed (P35.14a); P35.14b-live-typing-check (P35.14b); P35.15a-live-technology-vocab (P35.15a); P35.15b-live-technology-backfill (P35.15b); P36.12-l0-wave-open (P36.12); P36.12-l1-acq08-layers-family-day (P36.12); P36.12-l2-acq09-flock-layers-family-day (P36.12); P36.12-l3-acq10-ate-family-day (P36.12); P36.12-l4-acq11-procurement-family-day (P36.12); P36.12-l5-acq12-disclosures-01-family-day (P36.12); P36.12-l6-acq13-disclosures-02-family-day (P36.12); P36.12-l7-acq14-documents-family-day (P36.12); P36.12-l8-acq15-documents-family-day (P36.12); P36.12-l9-flock-portal-probe (P36.12); P36.12-l10-close-materialize-resume (P36.12); P35.1b-fleet-sweep-live (P35.1b); P35.1c-dispatcher-consolidation-live (P35.1c); P35.16-geometry-corrections-live (P35.16); P35.17-boundary-source-capture (P35.17); P35.24-subject-rekey-live (P35.24); P35.25-declared-lineage-live (P35.25); P35.26-roles-and-time-live (P35.26); P35.41-freshness-live (P35.41); P35.53-release-infra (P35.53); P35.59-dark-cutover (P35.59); P35.61-live-pass (P35.61); P35.62-staging-candidate (P35.62); P35.63-dispatch-stage-verify-readout (P35.63); P35.63-promote-under-hg11 (P35.63); P35.64-sweep-packet (P35.64). *Default: none.* **batch**
- Carried 11B legs: P35.61's apply leg (its go was never given — listed, carried); legs whose window extends past this GATE are listed and carried; P35.11's Wave-A window 10-19 → 10-23 elapsed unrun (verbatim-go awaited) — recorded, never smoothed. *Default: none.* **batch**
- CI incidents: NIGHTLY-RED-1 — the scheduled `nightly.yml` runs on `main` failed 2026-10-07 → 10-20 (14 runs; the owed observation of `D-P34.7-1`/`D-P34.2-2`; repair routed separately). Anomalies and operator-side merges read from GitHub at the sitting. *Default: none.* **batch**
- The D-K2-1 top-50 organisation review (OP-14, ≈ 1–2 h of the operator's time) — due by this sitting; its outcome is reported or carried, never performed by a row. *Default: carried.* **batch**
- Whether PLAN-11C's Phase-4 review fired the 11C re-split rule (> 85 engineering rows or > 75 engineering runs → an inserted gate): 11C stood at 76 / 66.5 at S6c — the rule did not fire at draft time. *Default: none.* **batch**
- The launch-unmet MUSTs list (`D-R11-LATER-04` — the ADR-171 Stage-0 set SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024): owed, unmet at launch — carried to GATE-ANNOUNCE's spec-MUSTs list, recorded, never implied satisfied. *Default: none.* **batch**
- The isolation probe repeated at this GATE (plan §8.5) — the orchestrator's work, reported here. *Default: none.* **batch**

<!-- agent-drafted:end -->

## Signature

<!-- Appended only at signing, by the commit that moves Status:. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-G5
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:490ec9c9047e
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
