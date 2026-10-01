"""S6: add operator_answer + answered_at to data/decision_catalog.csv from feedback/RATIFICATION_LOG.md.

Every answer is derived from the packet line's verbatim answer plus the log's labelled agent interpretation.
Timestamps are the log's round stamps (`date -u` at answer time, recorded in the log).
"""
import csv
import pathlib
import sys

PD = pathlib.Path("/Users/stevenvitali/Eleutheria-next-phase/docs/build/planning/2026-09-30-next-phase")
F = PD / "data" / "decision_catalog.csv"

R = {
    1: "2026-10-01T03:41:19Z", 2: "2026-10-01T03:53:59Z", 3: "2026-10-01T04:03:25Z", 4: "2026-10-01T04:07:45Z",
    5: "2026-10-01T04:09:43Z", 6: "2026-10-01T04:16:29Z", 7: "2026-10-01T04:21:56Z", 8: "2026-10-01T04:25:48Z",
    9: "2026-10-01T04:28:49Z", 10: "2026-10-01T04:32:16Z", 11: "2026-10-01T04:33:54Z", 12: "2026-10-01T04:35:53Z",
    13: "2026-10-01T04:39:45Z", 14: "2026-10-01T04:41:11Z", 15: "2026-10-01T04:43:37Z", 16: "2026-10-01T04:46:04Z",
    17: "2026-10-01T04:49:27Z", 18: "2026-10-01T04:51:39Z", 19: "2026-10-01T04:54:19Z", 20: "2026-10-01T04:56:11Z",
    21: "2026-10-01T04:59:05Z", 22: "2026-10-01T05:03:05Z",
}
# packet line -> round
LINE_ROUND = {
    "A-0": 1, "A-1": 2, "A-2": 2, "A-3": 2, "A-4": 3, "A-5": 3, "A-6": 3, "A-7": 3, "A-8": 4, "A-9": 4, "A-10": 4,
    "A-11": 5, "A-12": 5, "A-13": 5, "A-14": 6, "A-15": 7, "A-16": 6, "A-17": 6, "A-18": 7, "A-19": 8, "A-20": 8,
    "A-21": 8, "A-22": 8, "A-23": 9, "S5-1": 9, "S5-3": 9, "S5-4": 9, "S5-2": 19,
    "B-1": 10, "B-2": 10, "B-3": 10, "B-4": 10, "B-5": 11, "B-17": 11, "B-22": 11, "B-23": 11, "B-26": 11,
    "B-15": 11, "B-6": 11, "B-7": 11, "B-8": 12, "B-9": 12, "B-10": 12, "B-11": 12, "B-12": 13, "B-13": 13,
    "B-14": 13, "B-16": 13, "B-18": 13, "B-19": 13, "B-20": 14, "B-21": 14, "B-27": 14, "B-28": 14, "B-29": 15,
    "B-30": 15, "B-31": 15, "B-32": 15, "B-33": 16, "B-34": 16, "B-35": 16, "B-36": 16, "B-37": 16, "B-38": 17,
    "B-39": 17, "B-40": 17, "B-41": 17, "B-43": 17, "B-42": 18, "B-44": 18,
    "C-1": 19, "C-2": 19, "C-3": 19, "C-4": 20, "C-5": 20, "C-6": 20, "C-7": 20, "C-8": 21, "C-9": 21, "C-10": 21,
    "C-11": 21, "C-12": 22, "C-13": 22,
}
ID_ROUND = {"I7-X3": 4, "E4-R2a": 18}  # X3 answered in round 4; R2a conflict resolved in round 18

WV = {
    "WV-01": "I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, disclosed on the site, revisited at announcement, a first legal demand, funding, or a second maintainer.",
    "WV-02": "I waive SIG-GOV-015's editorial board: I hold interim single-maintainer editorial authority, and every naming/sensitivity decision goes in a public decision log.",
    "WV-03": "I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single maintainer, no second reviewer'.",
    "WV-04": "I waive SIG-UI-042's release block: releases may ship with the hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues.",
    "WV-05": "I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: corrections come by e-mail, and the site says plainly that senders disclose their address.",
    "WV-06": "I waive two-person authorisation for true deletion (SIG-GOV-008): I alone may authorise a deletion, publicly logged with its reason.",
    "WV-07": "I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such.",
}
STANDING_GO = ("Agents may promote a Class R release built from the same signed code whose diff stays within bounds "
               "(records −2%…+15%, no compartment <−5% or >+50%, no source loses >20%), with all checks green and no "
               "waivers; this go expires at the next sub-round gate or after 30 days, and is void on any ratchet "
               "regression, Part VIII screen change or new source.")
A8_SENT = ("I accept the express-terms risk for all ≈8,088 currently public rows, including the non-commercial ones; "
           "A-9 applies to new sources only.")
C3_SENT = ("The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message "
           "'let's defer all the human review steps and proceed' was my decision to defer the human review legs.")
ENVELOPE = ("public, unauthenticated pages only; no logins, API keys or circumvention of access controls; "
            "rate-limited; robots per GL-GATE-08; terms text captured verbatim and the exposure disclosed; "
            "Part VIII screen on every byte")

A = {
    # ---- A-0
    "OD-17": "b — no, wait for P34.18: no Track-0 change; P34.18 (early 11A) removes the 41 e-mail-shaped owner strings and handle tokens from the registry's non-id text; exposure recorded unresolved, operator-deferred (not accepted)",
    "OD-18": "b — no, wait for P34.21: no Track-0 change; P34.21b (early 11A, its own verbatim go) removes anonymous read/list on the sig-public 09-27 tree; exposure unresolved, operator-deferred",
    "OD-19": "b — no, wait for republish: republish #1 (P34.17) removes /visual-language/ and the handle-bearing pages; exposure unresolved, operator-deferred until then",
    "OD-20": "a — accept and disclose: history retained (agents never rewrite it) and disclosed in P34.18's correction note; SWH/Zenodo deposits of history unblocked after the history scan (B-6, B-21)",
    # ---- A-1/A-2/A-3
    "OD-01": "'None now; ticket it' (option c's no-exception path, without risk acceptance): no Track-0 change; the QA-9 restore drill (P34.6) and the TLS-expiry alert (P34.4) are early-11A tickets; the first-fire wave runs on existing backups/PITR + Track-0.5 alerting; risk recorded unresolved, operator-deferred",
    "OD-02": "a — the $300/mo ceiling covers infrastructure only (GCP, Cloudflare, domains, paid APIs); agent usage reported per wave, not capped by this line",
    "OD-03": "b — 'alert later': budget alert + billing export land in ticket P34.5 early in 11A (operator billing-admin step OP-12)",
    "OD-26": "b — no envelope and no fixed $ cap: agent usage reported per wave in every digest; the orchestrator pauses and asks at any usage-limit event",
    "Q-31": "a — move DNS to Cloudflare: P34.50 writes the runbook, then the operator switches nameservers (OP-09); R2 serves basemap, tiles, downloads and snapshots",
    "D-J3-4": "a — R2 mirror + custom domain, $50/mo egress ceiling with automatic kill switch (P35.5)",
    "OD-04": "a — create contact@surveillancegraph.org (OP-10, via Cloudflare Email Routing after OP-09) and use it as the project contact string",
    "D-K1-2": "R2 with the DNS move (follows Q-31 a)",
    "D-K0-4": "R2 zero-egress origin shared with TX-11 (follows Q-31 a)",
    # ---- A-4
    "Q-7": "a — adopt the disclosed single-maintainer, no-counsel posture (each member as recommended); the MUST-weakening members were decided at A-23, where all seven waiver candidates were waived",
    "Q-E2-06": "c — SIG-PUB-008 stands unamended; nobody named; web gate default-deny; the HG-11 second-reviewer role waived for Round-11 releases (WV-03)",
    "Q-E2-07": "c — text corrected; ADR records interim single-maintainer editorial authority + a public decision log; the SIG-GOV-015 board waived (WV-02)",
    "Q-E2-08": "c — interim individual legal home, disclosed, revisited at announcement, a first legal demand, funding or a second maintainer; SIG-GOV-012/013 waived (WV-01)",
    "Q-E2-09": "c — written legal-demand posture + published counts; warrant canary declined",
    "Q-E2-10": "a — publication rests on the operator's recorded determinations, labelled on every artifact; past 'counsel' entries re-recorded as the operator's own determinations (no counsel); counsel clauses waived (WV-07)",
    "Q-E2-13": "c — operator-accepted rights basis recognised with guardrails (Part VIII preflight; express terms decided individually; jurisdiction-conditional publication; withdrawal on objection), recorded as the operator's determination",
    "Q-E2-14": "c — per-compartment map kept; new ADR records ADR-106's ODbL clearance as operator-reported, with no document",
    # ---- A-5
    "Q-E2-11": "a — 'Re-confirm GL-GATE-08 as is' (operator chose it over the recommendation b): robots.txt disallows keep being disregarded on all 122 hosts incl. PrimeGov, disclosed as host + count (B-19); the rule-7 opt-out register and SIG-INGEST-046c reservation refusal are still built (not waived; a disallow is not a reservation). Option text adopted by selection: 'Keep disregarding on all 122 hosts incl. PrimeGov; conflicts with SIG-INGEST-046c for reservations. Not recommended.'",
    # ---- A-6
    "Q-L3-1": "a — derivation, not identity: auto-collapse only C0–C2; SIG-EVAL-004's lower bound waived for C0–C2 in the adopted sentence 'I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes.'",
    "Q-L3-2": "a — rows 184–187 superseded; no Round-11 human rows; D-R10-HUMAN-1 stays OPEN, non-blocking (T-EVAL-IND)",
    "Q-24": "a — no certification attempt in Round 11 (answered by Q-L3-1/2); no 'human-verified', 'certified' or camera-match-precision claim",
    "Q-25": "a as answered at A-6 (maintainer-check seat only), then vacated by B-31 (Q-L3-3 c): the operator holds no evaluation seat in Round 11",
    "Q-E2-15": "c as re-planned by L3 — the independent-evaluation MUSTs stay owed under T-EVAL-IND (superseded by Q-L3-1/2)",
    "Q-F4-1": "answered by Q-L3-1 (a)",
    "Q-F4-2": "answered by Q-L3-2 (a): EV1 not built in Round 11",
    "Q-F4-3": "answered by Q-L3-2 (a): rows 184–187 superseded",
    # ---- A-7
    "Q-19": "a in shape (per-batch HG-03 lines) with GL-GATE-07 re-confirmed (operator chose it over the recommendation): 'US public records and open-licence sources flip batch-wide under precedent, erring on the side of approving.' Part-VIII-flagged members still need their S-line (B-32); express prohibitions follow A-8/A-9/B-39",
    "E4-B1": "a — GL-GATE-07 (US) applied batch-wide to all three lanes of the 23 new targets",
    "E4-B5": "a — no re-approval needed (already executed under GL-GATE-03)",
    "E4-B6": "a — Round 11 adds the 3 registry rows (OMES, DAC, CA State Auditor) on the B1 basis",
    "I7-RB-01": "a — flip all under GL-GATE-07 US, batch-wide (GL-GATE-07 re-confirmed); Part-VIII-flagged members still need their S-line",
    "I7-RB-02": "a — flip under GL-GATE-07 US, batch-wide; Part-VIII-flagged members still need their S-line",
    "I7-RB-03": "a (a′ where only facts + citations are emitted), batch-wide; Part-VIII-flagged members still need their S-line",
    "I7-RB-04": "a — flip under GL-GATE-07 US, batch-wide; Part-VIII-flagged members still need their S-line",
    "I7-RB-05": "a — flip, CC0-1.0 (17 U.S.C. §105), batch-wide; Part-VIII-flagged members still need their S-line",
    "I7-RB-06": "a — flip on the verbatim licence, batch-wide; Part-VIII-flagged members still need their S-line",
    "I7-RB-07": "a — flip, DerivedFacts-Citations (never re-host), batch-wide",
    "I7-RB-09": "a — flip each existing row (E4 §2 recipe)",
    "I7-RG1": "a — flip the existing row (RB-09 member)",
    "I7-RG2": "a — flip the existing row (RB-09 member)",
    "I7-RG3": "a — flip the existing row (RB-09 member)",
    "I7-RG4": "a — flip the existing row (RB-09 member)",
    "I7-RG5": "a — flip the existing row (RB-09 member)",
    "I7-X3": "confirm — the 46 widening configurations inherit their parent source's rights decision (no new HG-03 line); the Part VIII screen still applies",
    # ---- A-8 / A-9 / A-10
    "Q-J4-2": "b — 'Keep all, accept risk' (operator chose it over withdrawal): all ≈8,088 rows stay public, incl. camreg_txdot_rep_tx and the 3 live NC rows ('Keep everything as is', 04:09:43Z); acceptance sentence adopted by selection: '" + A8_SENT + "'",
    "D-J3-5": "b (follows Q-J4-2) — no withdrawal; source pages and file-level rights records show the captured terms and the operator-accepted basis",
    "I7-C1": "keep the flip and the rows public as they are (not b: no restriction; not a's facts-only re-shaping) — 'Keep all, accept risk' / 'Keep everything as is'; the express-terms risk is accepted by ADR",
    "I7-C6": "b — SIG's use is or may be commercial: NEW non-commercial sources are facts + pointers only (E4-R4d declined); the 3 live NC rows stay as they are (A-8)",
    "D-K2-1": "b + c (not a) — 'Auto-allow + absence only': registry auto-allow ADR (Census of Governments / SAM UEI / Wikidata QID; person-name screen always runs; basis shown) and a typed 'not yet reviewed' state for every other organisation; no operator top-50 review",
    "G2-ADR124": "a — the ADR-124 allow list is D-K2-1's output, i.e. the registry auto-allow set (no operator review queue)",
    # ---- A-11..A-14
    "D-K13-1": "a — aggregated overview graphs (≤ 3,000 nodes) + entity egos + /explore/, descriptive only; revisit at > 3,000 labelled nodes",
    "D-K0-6": "yes",
    "D-K2-2": "a — descriptive views only; no centrality, rankings or labelled communities",
    "D-K0-1": "a — HTML-first page types (new ADR superseding ADR-068/091/097/134 and AGENTS.md gotcha 6; K0 budgets; Preact per D-K0-2)",
    "Q-14": "a — full seed: restore-first, correction ADR, guard core, PKG-02 pins; M1–M6 as early tickets",
    "Q-B4-1": "yes",
    "OD-05": "a — split per B3 option C",
    "OD-06": "yes — restore the 53 rows first",
    "Q-17": "yes — phases P34+, manifest rows 201+",
    "Q-13": "a — all 25 B6 changes, staged: Tier A (SK-13/14/17/18/19/20/22) at T0, Tier B-must (SK-01/02/03/06/09/10) before the first dispatch, the rest early in the round",
    # ---- A-15..A-22
    "Q-16": "custom (none of a–d): Devin Desktop, model swe-2-high (256k context), executes every Round-11 ticket; no in-round second harness; a post-round deep review by Claude Code (Opus 5.5, xhigh) closes the round. Verbatim: 'We will drive most of the execution with Devin Desktop using their new SWE-2 High model (256k context window)' (04:16:29Z) and 'How about Devin for everything and Claude Code can do a deep review after the entire thing, similar to what we did here …' (04:21:56Z)",
    "Q-15": "a — 'Gate pauses + wave digest': agents pause only at HG gates (HG-03 lines, HG-11/Class S readouts), one ING-GO per acquisition wave, spend above the ceiling, red CI (blockedOn) and production mutations not on an approved OM-20 list; one digest per wave with a spend line",
    "Q-B4-2": "a — operator-only gate-signing key (passphrase- or hardware-backed, never loaded into an ssh-agent a Devin/Claude session can reach) for HG gate signatures and Class-S gos, CI-verified against a committed allowed_signers",
    "Q-E2-21": "yes — forward rule: tentative words are never recorded as decisions without an explicit yes/no",
    "D3-DIR": "a — ratified, with one edit: D3-Q3 = b ('Ratify; fetch vendor pages')",
    "D3-Q1": "yes",
    "D3-Q3": "b — fetch vendor-hosted transparency pages (Flock/Axon etc.) (operator chose it over the recommendation a); engineering envelope: " + ENVELOPE,
    "D3-Q5": "a — D3 §5's checklist is the announce gate; no earlier preview",
    "Q-E2-22": "a — SIG-CHART-025 amended to US-nationwide multi-vendor/multi-technology breadth with per-class and per-geography quality labels",
    "D-K4-1": "yes — the operator flips census_gazetteer_tiger and natural_earth_10m (HG-03) once the terms text is captured (P35.17)",
    "OD-21": "a — let waves slip to their next windows (cliff table, plan §8.8); nothing dropped",
    "OD-22": "a — 'Yes, with labels' (operator chose it over b): structural spine writes may change live-API answers before HG-11, disclosed by every response's basis label and a /status/ notice; P35.57 is no longer a precondition",
    "OD-23": "b — 'Keep my name': the operator's name stays as commit author (disclosed risk); harness/model trailers enforced in CI (OM-01)",
    "D-K2-4": "yes — Flock share lists become organisation-level configured_access claims after a §43.2a/Part VIII screen",
    "OD-24": "b — keep the Eyes on Flock mirror live on its CC-BY-SA-4.0 basis, the 09-16 review disclosed as delegated, and use its share lists (D-K2-4 yes)",
    # ---- A-23
    **{k: "a — waived (adopted by selection, agent-drafted): '" + v + "'" for k, v in WV.items()},
    # ---- S5
    "S5-1": "ratify both — OM-19 and OM-20 as written (S4c wording, class-based never-list)",
    "S5-2": "ratify — `continue` answers only batch lines; every OW/EX line needs its own verbatim line; the OM-20 list is never approved by `continue`",
    "S5-3": "'Both + list + P34.45': the 11A OM-20 list approved verbatim (P34.3, P34.4, P34.5, P34.6 drill clone, P34.21a, P34.24b, P34.40, P34.42a/b, P34.43, P34.44b, P34.49) plus P34.45's entity-resolution re-run; expiry at GATE-G4",
    "S5-4": "change — 'Keep non-US acquisition': CF-06 not confirmed; R11-ACQ-23a/b stay in Round 11 and Wave C keeps its non-US members; US-first ordering kept for priority (Flock/Axon US-nationwide first, U-007)",
    # ---- B-1..B-4
    "E2-HFIX": "a — approve all",
    "G2-S0X": "yes — the two S0s join Wave 0 (with A-0 = wait: /visual-language/ and handle-bearing pages leave in republish #1; ids re-keyed by P34.18/P34.21b)",
    "OD-07": "a — agent drafts in batches of ~25 confirmed verbatim; only N-1…N-7 ship by sha256, until GATE-G4",
    "DR-C6-01": "a — re-key to neutral ids; neutral 'identifier changed' page; old→new map restricted",
    "Q-12": "a — supersede p-17b713 (no re-sign)",
    "Q-E2-18": "b — GATE-G3 superseded; ACCEPT-R8, ACCEPT-R10 and GATE-G3 annotated with B7's facts; no operator addendum about a past state of mind (forward question = C-13)",
    "Q-E2-19": "yes",
    "Q-E2-20": "yes",
    "Q-B1-2": "confirm — 2026-09-28T01:15:49Z (S3 deferral), 03:49:14Z (GATE-G3), 18:46:46Z (ACCEPT-R10) recorded as the true times",
    "Q-E2-17": "a — adopt the vocabulary + re-verdict",
    # ---- B-6/B-7
    "E2-RESID": "b — all as recommended except Q-E2-03 ('Move UA, don't buy domain')",
    "Q-E2-01": "a for the page (/editorial-standards/ says 'not yet performed'), read with WV-04 waived: SIG-UI-042's release block is waived for Round 11, findings listed as known issues",
    "Q-E2-02": "yes — crawler texts follow A-5 (GL-GATE-08 as is)",
    "Q-E2-03": "b — move the UA/contact URL to surveillancegraph.org; do NOT buy sig-project.org (residual squatting risk recorded; every remaining reference removed from code and docs)",
    "Q-E2-04": "yes",
    "Q-E2-12": "a — outreach becomes an owed later-phase obligation (trigger: the operator authorises outside contact)",
    "Q-E2-16": "yes",
    "Q-E2-23": "a — scan the public history, then SWH deposit (A-0.4 history disclosed)",
    "Q-9": "a — archive + pinned citations + release search first; research dossiers after live captures; intake only if opened",
    "G2-HOTFIX": "a — no API hotfix unless G2 step 1 slips past ~10-21",
    # ---- B-8..B-11
    "Q-27": "a — e-mail-only intake (the operator's address until contact@ exists) until after the announcement; /intake/ shows 'not operating'",
    "OD-08": "none of a–c — 'Email, no time promises': no response-time commitment is published",
    "D-K11-4": "a — task pages name the same dispute address",
    "D-G3-1": "yes", "D-G3-2": "yes",
    "D-G3-3": "a — Class R/S rule with the standing go adopted by selection: '" + STANDING_GO + "' Renewed at each sub-round GATE (never by `continue`)",
    "D-G3-4": "yes", "D-G3-8": "yes", "D-G3-9": "yes", "D-G3-10": "yes",
    "D-G3-5": "yes", "D-G3-6": "yes — the operator tags v0.1.0 after the #190 sitting", "D-G3-7": "yes",
    "Q-23": "a — autoresize cap 40 GB, pre-grow to 25 GB before Wave C, temporary tier bump for the OSM run",
    "I8-Q2": "a — OSM monthly", "I8-Q3": "a — one ING-GO per acquisition wave (4 lines)", "I8-Q4": "yes — targets under flipped sources are configuration",
    "I8-Q5": "a — core + Wave D (Wave D in scope)",
    # ---- B-12..B-21
    "Q-21": "a — $0 for paid data",
    "G1-TRIM": "a (+ d later) — consolidate the scheduler triggers into one dispatcher (−$7/mo); keep the LB and min-instances 1; revisit a Cloud SQL CUD after 3 measured bills",
    "G1-RET": "a — 365 days minimum, unlocked",
    "H2-SET": "a — S-1…S-5 by the operator, timed as stated", "Q-B4-3": "a — main protection after the merge sitting",
    "Q-H2-1": "confirm — pre-#190 reds do not block Round 11", "Q-H2-3": "yes — r11/ prefix", "Q-H2-4": "yes — one allow-listed flake re-run per head",
    "Q-H2-6": "a + c — keep the planning branch local until T6 (secret, personal-identifier and Part VIII scans before the push); the agent makes a git bundle the operator stores privately",
    "OD-27": "a — publish as recorded at T6, after the scans",
    "B3-NEXT": "a — nextTicket = N1", "B3-HG05": "a — operator-owned integration disposition",
    "D-SOURCES.7-2": "a — the operator registers the US 511 keys (Secret Manager, HG-09) after the contact@ alias (C-8)",
    "D-SOURCES.8-2": "a (recommendation updated from b after S5-4) — the operator registers QLDTraffic + NSW keys (HG-09) after the alias",
    "D-P30.2b-1": "a (fold into the maintainer check) — but B-31 removed the maintainer check, so it has no fold target: stays OPEN, non-blocking, trigger T-EVAL-IND",
    "D-P32.3-1": "a — fold into A-10's registry auto-allow ADR + CONF-13 (P37.46); no operator per-key review",
    "D-J3-1": "yes", "Q-J4-7": "yes", "D-J3-2": "yes — robots disclosed as host + count", "D-J3-3": "yes", "D-J3-6": "yes",
    "D-J3-7": "yes", "D-J3-10": "yes", "D-J3-11": "yes", "D-J3-13": "yes",
    "D-J3-8": "a — a pipeline minisign key signs release manifests; the operator's key (A-16) signs gate records",
    "D-J3-9": "yes — operator-run Zenodo DOIs, openly licensed compartments only, after the attribution fix",
    # ---- B-23, B-26..B-31
    "OD-09": "a — Natural Earth now for map and search; GeoNames only if NE proves too thin (with an HG-03 line)",
    "D-K1-5": "Natural Earth now (OD-09 a), not GeoNames",
    "D-K3-3": "Natural Earth now (OD-09 a)",
    "D-K13-4": "yes — publishing the dedup is an announce criterion; 'records' until then",
    "D3-Q4": "yes — neutral 'Other public resources' block on dossiers",
    "D-K7-3": "link to official agenda portals always; peer services per C5's link policy (follows D3-Q4 yes)",
    "D-K3-7": "b — 'Separate agent, labelled' (operator chose it over a): a separate agent context writes the ≥ 40-query set, labelled 'agent-authored held-out set; not independent', before and never visible to the contexts that tune search",
    "D-K14-9": "yes — operator 'beautiful' gallery sign-off before announcing",
    "D-K14-8": "yes — the spec published as a page per release",
    "D-K3-5": "yes — sig-api 512 MiB → 1 GiB (+$3/mo)",
    "D-K3-6": "yes — search rate limit 30/min",
    "Q-L3-3": "c — 'No maintainer check' (operator chose it over a): no operator maintainer check; every Class-S readout and /quality/ say 'no human check performed'",
    "Q-L3-4": "no — no in-round second model family (the post-round Claude Code review per A-15 is outside the round)",
    "Q-L3-5": "yes — /quality/ public, including failing and ratchet checks",
    "Q-L3-6": "a — C2 enabled",
    # ---- B-32..B-40
    "I7-S1": "a — ingest only the screened lane", "I7-S2": "a — ingest only the screened lane",
    "I7-S3": "a — screened lane (the CourtListener member follows I7-C8 b: deferred)",
    "I7-S4": "a — ingest only the screened lane", "I7-S5": "a — screened lane; names suppressed (PUB-008)",
    "I7-S6": "a — ingest only the screened lane", "I7-S7": "a — ingest only the screened lane",
    "I7-S8": "a — 'Include S8 screened lane' (operator chose it over b): the two tribal members ingest their Part VIII-screened lane without a tribal-data-governance rule; no outside contact",
    "I7-S9": "a — ingest only the screened lane",
    "I7-RB-06b": "a — flip into a share-alike compartment",
    "I7-RB-08": "a (recommendation updated from b after A-7) — territories treated as US under GL-GATE-07",
    **{f"I7-N{i}": "a (recommendation updated from b after S5-4) — flip under the non-US database-right precedent (express prohibitions excluded)" for i in range(1, 22)},
    "I7-IT1": "b — facts-only pointer", "I7-IT2": "b — facts-only pointer (A-9)", "I7-IT3": "b — facts-only pointer (A-9)",
    "I7-IT4": "c — decline", "I7-IT5": "b — facts-only pointer (A-9)", "I7-IT6": "b — facts-only pointer (A-9)",
    "I7-IT7": "a — 'IT7 full fetch' (operator chose it over b): the agency-hosted Axon Fusus 'Connect <Place>' pages are fetched in full under A-17's envelope; every byte through the Part VIII screen before storage or publication; private registrants never stored or published (Part VIII and SIG-PUB-002 not waived)",
    **{f"I7-IU{i}": "a — capture terms in Round 11, then a line (facts + citation meanwhile)" for i in range(1, 6)},
    "I7-TR1": "c (recommendation updated after B-32) — facts + citations under the S8 screen",
    "I7-TR2": "c (recommendation updated after B-32) — facts + citations under the S8 screen",
    **{f"I7-P{i}": "a — facts-only basis; ingestion later-phase (I8); first request only after contact@ exists" for i in range(1, 5)},
    "I7-C2": "fetch despite terms — 'Also fetch DocCloud/Sourcewell' (neither a nor b): DocumentCloud/MuckRock fetched like A-17's vendor pages: " + ENVELOPE,
    "I7-C3": "fetch despite terms — Sourcewell and OMNIA fetched under the same envelope (not pointers-only)",
    "I7-C4": "per A-17 (D3-Q3 b) — vendor-hosted public pages fetched under the envelope",
    "I7-C5": "b — accept Chicago/ABQ with a withdrawal-by-new-claim policy; decline the OpenFEMA API route",
    "I7-C7": "a — facts only from district-side pages",
    "I7-C8": "b — CourtListener bulk stays deferred with R2b",
    "I7-C9": "a — refresh the statute seed from origins",
    "I7-C10": "answered by Q-30/U-014; contact string only after contact@ exists (C-8 alias first)",
    "I7-C11": "a — decide E4-R4a on the OGL-Edmonton basis once the body is captured",
    "I7-X1": "confirm", "I7-X2": "confirm", "I7-X4": "approve",
    # ---- B-41..B-44
    "E4-R1": "a — close: rights DONE; eID leg WONTFIX",
    "E4-R2a": "b — flip documentcloud (conflict with B-41 'as listed' re-asked; operator answered 'Fetch, screened'): public documents only, Part VIII screen on every byte, link to the uploader's page",
    "E4-R2b": "a — decline courtlistener_recap",
    "E4-R3": "a — 'As listed, R3 flip': flip dot_511_tx under GL-GATE-07 (US)",
    "E4-R4a": "b, then decide on the OGL-Edmonton basis (I7-C11 a): capture the City of Edmonton terms and flip if they permit (non-US kept by S5-4)",
    "E4-R4b": "a — flip camreg_hk_hk on the non-US basis (non-US kept by S5-4, B-34)",
    "E4-R4c": "b — use the QLDTraffic API instead (key registered by the operator, B-18)",
    "E4-R4d": "c — decline camreg_bellevue_wa (A-9)",
    "E4-R5": "a — flip procportal_chicago_il under GL-GATE-07",
    "E4-R6a": "a — capture bidnetdirect.com terms, then decide",
    "E4-R6b": "a — close periscope_s2g as superseded",
    "E4-B2": "'Agent clears, disclosed' (operator chose it over a): a Round-11 ticket runs the Part VIII screen per family and the agent clears it — no operator 'clear'; readouts state 'cleared by agent screen, no human review'",
    "E4-B3": "a — SRC-027 workbooks metadata-only permanently",
    "E4-B4": "a — per-target byte-bound exception + one bounded retry",
    "E4-S1": "a — D-SOURCES.12-1 PARTIAL → DONE", "E4-S2": "b — bonfire WONTFIX", "E4-S3": "a — opengov_procurement later-phase",
    "E4-S4": "a — D-SOURCES.7-1 OPEN → PARTIAL (remainder dot_511_tx flips under E4-R3 a)", "E4-S5": "a — moot (R1 = a)",
    "F1-P21.3-2": "confirm — D-P21.3-2 → DONE",
    "D-K1-6": "yes — single-source sites shown by default (hollow symbol)",
    "D-K1-7": "yes — 'My location' approved (operator chose it over the recommendation no): built as a map-pan-only control (browser-only geolocation after a click, never sent to SIG; no 'cameras near you' list, count, alert or proximity notice), preceded by a written SIG-GOV-017 analysis; if the analysis finds it cannot comply, the ticket pauses and returns the question (waive GOV-017 for it, or drop it) to the operator",
    "D-K4-3": "as recommended — all counties with ≥ 1 record (2,482); places with ≥ 10 records (2,817) + any place with non-site evidence; non-US admin-1 with ≥ 10 (218)",
    "D-K7-6": "as recommended — verbatim title only when the person-name screen passes; otherwise matter number + matched term",
    "D-K8-1": "as recommended — a locator always; an excerpt of ≤ 300 characters only where the source's recorded terms permit quotation",
    "D-K8-4": "as recommended — show the 255 synthetic run-record artifacts with honest labels",
    # ---- Part C
    "OD-10": "confirm",
    "OD-11": "confirm; intent = planned hand-over: 'Pause after P31.5' was a planned hand-over to Devin CLI at P31.5→P31.6",
    "OD-12": "confirm — sentence adopted by selection (agent-drafted, adopted 2026-10-01T04:54:19Z): '" + C3_SENT + "' Item (3) robots = A-5",
    "D-K14-1": "edit — tagline 'Public surveillance, traced to the documents.'; the sub-head, About paragraph, why-it-exists line and four 'is not' lines go to copy batch #1 for verbatim confirmation (B-2)",
    "D-K14-7": "omit until the operator writes it — no 'who runs SIG' section or placeholder ships",
    "OD-13": "stays public",
    "OD-14": "don't know — keep the ≈ $90–100/mo estimate, labelled inference, until P34.5's billing export measures it",
    "OD-15": "alias first — no request needing a contact string (EDGAR, 511 / QLD / NSW key sign-ups) is sent until contact@surveillancegraph.org exists",
    "Q-H2-2": "confirm — no such value was used in any deployed or staging config",
    "Q-B1-4": "yes — operator-approved local, read-only inspection (2026-10-01T04:59:41Z): the stopped P33.2 test container sig-p332-db holds 48 sqitch changes incl. L44–52 as stamped; never re-stamp L44–52; date corrections by appended amendment only",
    "OD-16": "confirm",
    "OD-28": "accept — sentence adopted by selection: 'I accept that these features are withdrawn or labelled this round rather than made to work.'",
    "OD-29": "superseded — ACCEPT-R10 stands as history, superseded by the Round-11 re-verdicts (B-5); recorded 2026-10-01T05:03:05Z, never as a 09-27/28 statement",
}
D2_PRI = {1: "P1", 2: "P1", 3: "P1", 4: "P1", 5: "P1", 6: "P2", 7: "P1", 8: "P1", 9: "P2", 10: "P2", 11: "P1",
          12: "P1", 13: "P1", 14: "P2", 15: "P2", 16: "P1"}
for i, p in D2_PRI.items():
    A[f"D2-{i:02d}"] = f"agree, {p} (ticked at the shown priority)"

rows = list(csv.DictReader(F.open()))
fields = list(rows[0].keys())
for c in ("operator_answer", "answered_at"):
    if c not in fields:
        fields.append(c)
missing = []
for r in rows:
    d = r["dec_id"]
    pl = r["packet_line"]
    if d in A:
        ans = A[d]
    elif pl == "B-22":
        ans = "a — accept the 52 K-row design recommendations as written" if d == "K-BATCH" else (
            "as recommended (B-22 K-BATCH a): " + r["recommendation"].strip())
    elif pl in ("B-2",) and d.startswith("D-"):
        ans = "a via OD-07 (batched verbatim approval): " + r["recommendation"].strip()
    else:
        ans = ""
    if not ans:
        missing.append(d)
        ans = "UNRESOLVED: no answer derivable from the log"
    rnd = ID_ROUND.get(d, LINE_ROUND.get(pl))
    if pl.startswith("D2"):
        rnd = 22
    r["operator_answer"] = ans
    r["answered_at"] = R[rnd] if rnd else "UNRESOLVED"
    if not rnd:
        missing.append(d + "(time)")
with F.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("rows", len(rows), "missing", missing)
