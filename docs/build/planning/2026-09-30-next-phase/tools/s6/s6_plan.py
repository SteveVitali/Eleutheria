"""S6: fold the GATE-P answers into data/round11_plan.csv (rows, gates, notes, new/dropped/moved units)."""
import csv
import pathlib
import re

PD = pathlib.Path("/Users/stevenvitali/Eleutheria-next-phase/docs/build/planning/2026-09-30-next-phase")
F = PD / "data" / "round11_plan.csv"
rows = list(csv.DictReader(F.open()))
FIELDS = list(rows[0].keys())
by = {r["id"]: r for r in rows}
CHAIN = ("11A", "11B", "11C", "11D", "11D-tail")

ENV = ("public, unauthenticated pages only; no logins, API keys or access-control circumvention; rate-limited; "
       "robots per GL-GATE-08; terms text captured verbatim; exposure disclosed; Part VIII screen on every byte")
LIST11A = {"P34.3", "P34.4", "P34.5", "P34.6", "P34.21a", "P34.24b", "P34.40", "P34.42a", "P34.42b", "P34.43",
           "P34.44b", "P34.49", "P34.45"}
GATE_OF = {"11B": "GATE-G4", "11C": "GATE-G5", "11D": "GATE-G6"}


def note(r, text):
    r["notes"] = (r["notes"] + " | " if r["notes"] else "") + "S6: " + text


# ------------------------------------------------------------------ moves before gate rewriting
by["P34.45"]["sub_round"] = "11A"
by["P34.45"]["depends_on"] = "P34.17;P34.43(S2);P34.44b"
for rid in ("P35.22", "P35.24", "P35.25", "P35.27", "P35.46"):
    by[rid]["depends_on"] = ";".join(t for t in by[rid]["depends_on"].split(";") if "P35.57(A-20 b)" not in t)
    note(by[rid], "A-20 = a: no live: edge to P35.57; its writes may change live-API answers before HG-11, disclosed "
                  "by the API basis label (P34.25) and a /status/ notice")


# ------------------------------------------------------------------ OM-20 phrase
OM = re.compile(
    r"named mutation -> OM-20 \(([^)]*)\) -> default: (?:NOT pre-authorised = ?)?(?:IN-TICKET PAUSE"
    r"(?:; pre-authorised only if (?:this row id is )?on an OM-20 list (?:the operator )?approved verbatim"
    r"(?: \(expiry at the next GATE; voided by a new material fact; OM-10\))?)?)?")


def om20(r):
    sr = r["sub_round"]
    if sr == "11A":
        if r["id"] in LIST11A:
            return ("named mutation -> OM-20 PRE-AUTHORISED: on the 11A list the operator approved verbatim at "
                    "GATE-P (S5-3, 2026-10-01T04:28:49Z; expires at GATE-G4; void on a red probe, a failed restore "
                    "point or a production read that contradicts a record)")
        return "named mutation, not on the 11A OM-20 list (S5-3) -> IN-TICKET PAUSE: explicit verbatim go"
    g = GATE_OF.get(sr, "next GATE")
    return (f"named mutation -> OM-20: pre-authorised only if the {g} list the operator approves verbatim names "
            f"this row (expiry at the next GATE; OM-10); otherwise NOT pre-authorised = IN-TICKET PAUSE")


# ------------------------------------------------------------------ exact segment rewrites
SEG = {
    "Q-H2-4 [B-15] -> default: no re-run; allow-listed flakes go to blockedOn":
        "Q-H2-4 [B-15] = yes: one gh run rerun --failed per head for allow-listed flakes only; anything else -> blockedOn",
    "Q-23 disk cap [B-11] -> default: autoresize cap 25 GB":
        "Q-23 [B-11] = a: autoresize cap 40 GB (the pre-grow to 25 GB is P37.2's)",
    "OD-01 [A-1] -> default c (no Track-0; this ticket executes); Track 0.5 alerts already live 2026-10-01T00:09Z — ticket verifies, extends (QA-5/QA-8) and codifies":
        "OD-01 [A-1] answered 'None now; ticket it' (2026-10-01T03:53:59Z): no Track-0 change; this ticket adds the TLS-expiry alert early in 11A and verifies, extends (QA-5/QA-8) and codifies the Track 0.5 alerts (live 2026-10-01T00:09Z); risk until then unresolved, operator-deferred",
    "OD-02/OD-03 [A-2] -> default: ceiling = infra only; budget alert + billing export land in this ticket":
        "OD-02/OD-03/OD-26 [A-2] answered (2026-10-01T03:53:59Z): ceiling = infrastructure only; 'alert later' = the budget alert + billing export land in this ticket, early in 11A; agent usage reported per wave, pause at any usage-limit event (no $ cap)",
    "OD-01 [A-1] QA-9 timing -> default: the drill runs here":
        "OD-01 [A-1] answered 'None now; ticket it': the QA-9 restore drill runs here, early in 11A (ideally before the 10-10 replay); risk until then unresolved, operator-deferred",
    'OD-07 [B-2] -> default b: removal-only corrections ship; new sentences stay "pending review" until confirmed verbatim':
        "OD-07 [B-2] = a: new sentences ship only after verbatim confirmation in copy batches of ~25; only N-1…N-7 ship by sha256 (until GATE-G4)",
    "OD-07 [B-2] -> default b": "OD-07 [B-2] = a (copy batches confirmed verbatim; N-1…N-7 allowance until GATE-G4)",
    "OD-07 [B-2] -> default b (as UXW0-1)": "OD-07 [B-2] = a (as UXW0-1)",
    "Q-E2-07/Q-E2-10 [A-4] -> default: text correction only (false claims removed, spec clauses stay owed); wording via B-2":
        "Q-E2-07/Q-E2-10 [A-4] = c/a (disclosed posture adopted): text corrections + ADR-164/ADR-167; SIG-GOV-015 and the counsel clauses waived (WV-02, WV-07); wording via copy batches (B-2)",
    "Q-J4-2/D-J3-5 + I7-C1 [A-8] -> default: withdraw the NEW-1 rows and restrict camreg_txdot_rep_tx":
        "Q-J4-2/D-J3-5 + I7-C1 [A-8] answered 'Keep all, accept risk' / 'Keep everything as is' (2026-10-01T04:07:45Z / 04:09:43Z): no withdrawal and no TxDOT restriction; this ticket writes the disclosure instead (captured terms verbatim + the operator-accepted basis, ADR-183)",
    "every new sentence confirmed verbatim, except the S5-ratified notice strings N-1..N-7 (B-2/OD-07 [B-2] -> default b: no allowance)":
        "every new sentence confirmed verbatim in copy batch #1, except the notice strings N-1..N-7 ratified at GATE-P by sha256 (B-2/OD-07 = a; allowance until GATE-G4)",
    "OD-08 [B-8] -> default: email-only, no response-time commitment published until confirmed":
        "Q-27/OD-08 [B-8] answered 'Email, no time promises': the dispute notice names the operator's address (until contact@ exists), promises no response time and says plainly that senders disclose their address (WV-05) · A-0.3 [OD-19] answered b (2026-10-01T03:41:19Z): this republish removes /visual-language/ and every page whose URL or title embeds a personal handle (N-6 until P34.21b republishes them re-keyed)",
    "B-3 [B-3] -> default a (re-key proceeds; publication only with the republish #2 go)":
        "DR-C6-01 [B-3] = a: re-key; neutral 'identifier changed' page; old->new map restricted; publication with the republish #2 go",
    "A-0 [A-0] answered 'a' -> the interim removals already ran as Track-0 actions":
        "A-0.1 [OD-17] answered b (2026-10-01T03:41:19Z): this ticket removes the 41 e-mail-shaped owner strings and handle tokens from the registry's non-id text (on the r11 branch at once; on public main only when the operator merges, OP-08) · A-0.4 [OD-20] = a: history retained and disclosed in this ticket's correction note",
    "IN-TICKET PAUSE: republish #2 go, verbatim":
        "IN-TICKET PAUSE: republish #2 go, verbatim · A-0.2 [OD-18] answered b (2026-10-01T03:41:19Z): this ticket also removes anonymous read/list on the sig-public 09-27 tree (prefixes the live site fetches excluded after a read-only listing; tombstone note) on its own verbatim go — the first leg, allowed as soon as the code lands (bucket IAM, not a hosted DB write; PUB window)",
    "A-8/B-3 defaults as P34.18/P34.19": "A-8 = keep all (no withdrawal in the re-export; terms + basis per file); B-3 = a",
    "Q-12/Q-B1-3 [B-4] -> default a: supersede p-17b713, no re-sign": "Q-12/Q-B1-3 [B-4] = a: supersede p-17b713, no re-sign",
    "D-G3-6 [B-10] -> default: no tags (tags are operator acts, OP-08)":
        "D-G3-6 [B-10] = yes: the operator tags v0.1.0 after the #190 sitting (OP-08); agents never tag",
    "G2-HOTFIX [B-7] -> default a: no API hotfix; ships with P34.46 unless P34.46 slips past 2026-10-21 (then disclosed)":
        "G2-HOTFIX [B-7] = a: no API hotfix; ships with P34.46 unless P34.46 slips past 2026-10-21 (then disclosed) · A-20 [OD-22] = a: every API response carries a basis label (live spine, not release-pinned; text via copy batch #1) so structural writes before HG-11 are disclosed",
    "G2-ADR124 + D-K2-1 [A-10] -> default: empty allow list (all organisations withheld)":
        "G2-ADR124 + D-K2-1 [A-10] answered 'Auto-allow + absence only' (2026-10-01T04:07:45Z): the allow list = organisations matched to the Census of Governments, a SAM UEI or a Wikidata QID (ADR-159; person-name screen always runs); every other organisation typed 'not yet reviewed'; no operator review queue",
    "OD-06 [A-13] -> default yes (restoration is corrective)": "OD-06 [A-13] = yes (restore first)",
    "OP-18 readout-addenda confirmations (operator)":
        "C-13 [OD-29] answered 'Superseded' at GATE-P (2026-10-01T05:03:05Z); no operator readout addendum",
    "Q-E2-21 [A-16] -> default yes":
        "Q-E2-21 [A-16] = yes · Q-B4-2 [A-16] = a: this ticket adds the G4c CI verification of gate-signature commits against a committed allowed_signers (operator key OP-25; LATER-15 closes)",
    "OD-05 [A-13] -> default: D-R10-MEMORY-1 stays OPEN in shadow (ticket records the no-change disposition only)":
        "OD-05 [A-13] = a: D-R10-MEMORY-1 split per B3 option C",
    "G2-ADR124 [A-10] -> default: empty allow list": "G2-ADR124 [A-10] = the registry auto-allow set (ADR-159)",
    "IN-TICKET PAUSE (never pre-authorised under OM-20: changes public API responses); explicit verbatim go":
        "IN-TICKET PAUSE (never pre-authorised under OM-20: changes public API responses); explicit verbatim go · A-20 [OD-22] = a: no longer a precondition for P34.45 or the 11B structural writes; kept as an improvement",
    "Q-L3-1 [A-6] -> default: no automatic collapse at all, inferential tiers review-only":
        "Q-L3-1 [A-6] = a: inferential tiers review-only; only C0–C2 collapse (P35.46)",
    "A-20 -> default b: the ER re-run's rematerialisation waits for P35.57 (live) so no API answer changes before HG-11":
        "A-20 [OD-22] = a (2026-10-01T04:25:48Z): the ER re-run may change live-API answers before HG-11, disclosed by the basis label (P34.25) and a /status/ notice; no wait for P35.57",
    "publication rides P35.63's Class S readout (FEA-19); only the ER re-run may be pre-authorised":
        "the present-tense merge sentence ships with P35.63's Class S readout (FEA-19); only the ER re-run is pre-authorised",
    "D-J3-4 + Q-31 [A-3] -> default b: no DNS change, host built but no public download link; R2 leg needs OP-09":
        "D-J3-4 + Q-31 [A-3] = a: R2 zero-egress origin, $50/mo egress ceiling + kill switch, R2 operations ceiling; the R2 leg runs after the operator switches nameservers (OP-09, P34.50 runbook)",
    "I7-X4 [B-40] -> default approve": "I7-X4 [B-40] = approve",
    "C9 -> default a": "I7-C9 [B-39] = a: refresh the statute seed from origins",
    "ING-GO-A verbatim [B-11] (collected at GATE-G4 for 10-19..10-23, else IN-TICKET PAUSE; unanswered -> live leg queued, code lands)":
        "ING-GO-A verbatim (B-11 I8-Q3 = one go per wave; collected at GATE-G4 for 10-19..10-23, else IN-TICKET PAUSE; unanswered -> live leg queued, code lands)",
    "I7-X3 [A-7] -> default: NOT confirmed, widening configs land disabled":
        "I7-X3 [A-7] = confirm (2026-10-01T04:07:45Z): widening configs enabled under their parent source's rights basis (Part VIII screen still applies)",
    "Q-E2-11 [A-5] -> default: GL-GATE-08 stands, no new robots-disallowed host":
        "Q-E2-11 [A-5] answered 'Re-confirm GL-GATE-08 as is' (2026-10-01T04:03:25Z): robots disallows stay disregarded (the 122 hosts incl. PrimeGov, and new hosts), disclosed as host + count; this row still builds the rule-7 opt-out register and the SIG-INGEST-046c reservation refusal (a disallow is not a reservation)",
    "Q-E2-02 [B-6] -> default yes": "Q-E2-02 [B-6] = yes: crawler texts follow A-5",
    "ING-GO-B verbatim [B-11] (collected at GATE-G4; else IN-TICKET PAUSE; unanswered -> legs stay queued, nothing activates)":
        "ING-GO-B verbatim (collected at GATE-G4 with the operator's Wave-B flip list, OP-26; else IN-TICKET PAUSE; unanswered -> legs stay queued, nothing activates)",
    "G1-TRIM [B-13] -> default: no trims (lint + scheduler of record only)":
        "G1-TRIM [B-13] = a: consolidate the scheduler triggers into one hourly dispatcher (−$7/mo); LB and min-instances 1 kept; Cloud SQL CUD later (LATER-19)",
    "D-G3-1/D-G3-2 [B-9] -> default yes": "D-G3-1/D-G3-2 [B-9] = yes",
    "D-K4-1 [B-24] HG-03 boundaries -> default NOT flipped: code + fixtures land, hosted capture queued; JUR chain and P35.63 wait (critical-path stall; S2 asks S3/S5 to move B-24 to Part A)":
        "D-K4-1 [A-18] = yes (2026-10-01T04:21:56Z): this ticket captures the terms text of census_gazetteer_tiger + natural_earth_10m, then pauses for the operator's HG-03 flip of both (OP-26); P35.17 stays on the critical path",
    "D-K4-2/D-K4-4 [B-22] -> as recommended": "D-K4-2/D-K4-4 [B-22] = as recommended (K-BATCH a)",
    'D-K2-1 [A-10] -> default: organisations withheld ("pending publication review"); non-organisation labels ship':
        "D-K2-1 [A-10] = b + c: organisations matched by the registry auto-allow ADR (ADR-159) are labelled; every other organisation shows a typed 'not yet reviewed' state; non-organisation labels ship",
    "D-K2-1 [A-10] -> default as P35.29": "D-K2-1 [A-10] = b + c (as P35.29)",
    "D-J3-1 [B-19] -> default: no raw bytes":
        "D-J3-1 [B-19] = yes: raw bytes for raw-ok sources only, after the Part VIII byte screen (P37.36)",
    "D-J3-5 [A-8] -> default withdraw":
        "D-J3-5 [A-8] = b: no withdrawal; the rights lanes carry the captured terms + the operator-accepted basis (ADR-183)",
    "Q-E2-03 [B-6] -> default b: UA/contact URL moves to surveillancegraph.org, no purchase":
        "Q-E2-03 [B-6] answered 'Move UA, don't buy domain': UA/contact URL moves to surveillancegraph.org; sig-project.org is not purchased and every remaining reference to it is removed from code and docs (residual squatting risk recorded)",
    "IRI base -> default surveillancegraph.org": "IRI base = surveillancegraph.org",
    "Q-L3-6 [B-31] -> default b: C0/C1 only": "Q-L3-6 [B-31] = a: C2 enabled",
    'Q-L3-1 [A-6] -> default: no automatic collapse, "possible duplicate" ranged counts':
        "Q-L3-1 [A-6] = a: auto-collapse only C0–C2 (SIG-EVAL-004 lower bound waived for C0–C2, ADR-153); every inferential match is a 'possible duplicate' with intervals",
    "D-K13-4 [B-26] -> default yes (dedup is an announce criterion)": "D-K13-4 [B-26] = yes (dedup is an announce criterion)",
    "Q-L3-4 [B-31] -> default no (same-family blind contexts only)":
        "Q-L3-4 [B-31] = no: same-family blind contexts only; labelled, never gating",
    "D-K0-1 [A-12] -> default b: existing zero-JS ADRs stand (registry still built; T1/T2 limited to the three islands)":
        "D-K0-1 [A-12] = a: HTML-first page types (ADR-155) replace the zero-JS rule",
    "D-G3-10 [B-9] -> default yes": "D-G3-10 [B-9] = yes",
    "D-G3-8 [B-9] -> default yes (auto-rollback pre-authorised)": "D-G3-8 [B-9] = yes (auto-rollback pre-authorised)",
    "D-G3-3 [B-9] -> default b: no standing go, every release Class S":
        "D-G3-3 [B-9] = a: Class R standing go in the operator's adopted words (expires at the next sub-round GATE or after 30 days; void on a ratchet regression, a Part VIII screen change or a new source; renewed at each GATE); the generator writes 'single maintainer, no second reviewer' (WV-03) and 'no human check performed' (B-31) into every Class S readout",
    "IN-TICKET PAUSE: HG-11 candidate-specific readout signed verbatim (+ OPCHECK if Q-L3-3 = a)":
        "IN-TICKET PAUSE: HG-11 candidate-specific readout signed verbatim (no OPCHECK: Q-L3-3 = c; the readout states 'single maintainer, no second reviewer' and 'no human check performed')",
    "Q-9/G2-HOTFIX [B-7] -> default a: archive + pinned citations + release search first":
        "Q-9/G2-HOTFIX [B-7] = a: archive + pinned citations + release search first",
    "ING-GO-C verbatim + Q-23 [B-11] (collected at GATE-G5) -> default: cap 25 GB and Wave C waits (legs stay queued)":
        "ING-GO-C verbatim (collected at GATE-G5) · Q-23 [B-11] = a: cap 40 GB, pre-grow to 25 GB, temporary tier bump · S5-4 = keep non-US acquisition: the national run keeps its non-US objects (US-first ordering)",
    "HG-03 flips are never pre-authorised: each executes only after its verbatim line (E4-R3..R6b [B-41] -> default: not flipped / status unchanged; R4a-c recommended b after S4c, COV-07)":
        "HG-03 flips are never pre-authorised: the operator executes each on its GATE-P line (OP-26) — E4-R3 = a flip dot_511_tx; E4-R4a = capture the OGL-Edmonton body, then decide on it (I7-C11 a); E4-R4b = a flip camreg_hk_hk; E4-R4c = b QLDTraffic API (P37.70); E4-R4d = c decline; E4-R5 = a flip procportal_chicago_il; E4-R6a = capture bidnetdirect terms, then a line; E4-R6b = a close · I7-IU1…IU5 [B-36] = a: capture terms here, then a line at the next GATE",
    "D-K3-6 [B-30] -> default yes (30/min)": "D-K3-6 [B-30] = yes: 30/min, burst 10; no Cloud Armor now",
    "D-K14-3/D-K14-5 [B-22] -> default as recommended": "D-K14-3/D-K14-5 [B-22] = as recommended",
    "D-K14-5/D-K14-6 [B-22] -> as recommended": "D-K14-5/D-K14-6 [B-22] = as recommended",
    "D-K14-8 [B-29] -> default no": "D-K14-8 [B-29] = yes: the spec published as a page per release",
    "D-K14-2 [B-22] -> default yes": "D-K14-2 [B-22] = yes",
    "D-K2-5 [B-22] -> default: exclude unclassified procurement": "D-K2-5 [B-22] = as recommended: exclude unclassified procurement",
    "D-K3-7 [B-28] -> default b: a separate agent writes the held-out set, labelled (OP-21 if a)":
        "D-K3-7 [B-28] answered 'Separate agent, labelled': the held-out set comes from P36.79 (a separate agent context, sealed from this row); the metric is labelled 'agent-authored held-out set; not independent'",
    "Q-31/D-K1-2 [A-3] -> default b: GCS-hosted basemap (≈$6-43/mo)": "Q-31/D-K1-2 [A-3] = a: basemap on R2 after the DNS move (OP-09)",
    "D-K1-3 [B-22]": "D-K1-3 [B-22] = as recommended",
    "D-K3-5 [B-30] -> default no: v2 API built and staged, not rolled (/search/ stays P32.14; U-003.3 unmet)":
        "D-K3-5 [B-30] = yes: sig-api 512 MiB -> 1 GiB (+$3/mo) and the v2 API rolls (U-003.3)",
    "D-K2-1 [A-10] -> default: organisations withheld; entity pages for non-organisation types only":
        "D-K2-1 [A-10] = b + c: entity pages for organisations matched by the registry auto-allow ADR; every other organisation typed 'not yet reviewed'",
    "D-J3-11 [B-19] -> default: no status lane (built, not scheduled)": "D-J3-11 [B-19] = yes: status lane every 6 h; gated/refused sources as counts",
    "D-G3-4 [B-9] -> default yes": "D-G3-4 [B-9] = yes",
    "D-J3-12 [B-2] -> default OD-07 b": "D-J3-12 [B-2] = OD-07 a (batches of ~25 confirmed verbatim; 'description pending review' until then)",
    "D-K10-1 [B-2] -> default OD-07 b": "D-K10-1 [B-2] = OD-07 a (disclosure texts confirmed verbatim in batches)",
    "D-J3-5 [A-8] -> withdraw":
        "D-J3-5 [A-8] = b: no withdrawal; each bundle's ATTRIBUTION/LICENCE file states the captured terms and the operator-accepted basis (ADR-183)",
    "D-J3-8 [B-20] -> default: sha256 only, no signatures": "D-J3-8 [B-20] = a: SHA256SUMS + the pipeline minisign signature (key OP-20)",
    "A-3 -> default: no public download links": "A-3 = a: public download links from the R2 host",
    "D-J3-5 [A-8]": "D-J3-5 [A-8] = b (no withdrawal; terms + basis per file)",
    "D-K5-1 [B-22]": "D-K5-1 [B-22] = as recommended",
    "HG-03 E4 (K4 NEW-4) -> default not flipped": "HG-03 E4 (K4 NEW-4): per the GATE-P lines (A-7, B-41); an unflipped source stays out of the slices",
    "A-3 -> default: links hidden": "A-3 = a: links shown (R2 host)",
    "D-K11-3 [B-22] -> default yes": "D-K11-3 [B-22] = yes",
    "D-K14-1 [C-4] -> default: current copy minus false claims; new positioning waits":
        "D-K14-1 [C-4] = tagline 'Public surveillance, traced to the documents.'; the sub-head, About paragraph, why-it-exists line and four 'is not' lines ship after verbatim confirmation in copy batch #1",
    'D-K14-7 [C-5] -> placeholder "a single independent maintainer"':
        "D-K14-7 [C-5] = 'Omit until I write it': no 'who runs SIG' section or placeholder ships until the operator writes it",
    "D-J3-6 [B-19] -> default no: /s/ snapshots built, not published (J4 then cannot pass)": "D-J3-6 [B-19] = yes: /s/<pub>/ snapshots published (J4)",
    "D-K9-2 [B-22] -> default a": "D-K9-2 [B-22] = a",
    'D-G3-3 [B-9] -> default: no standing go, so the "first Class R promotion" is run as Class S (IN-TICKET PAUSE)':
        "D-G3-3 [B-9] = a: the first Class R promotion runs under the standing go if it is still valid (renewed at GATE-G5); otherwise as Class S (IN-TICKET PAUSE)",
    "G1-RET [B-14] -> default: status-quo retention":
        "G1-RET [B-14] = a: 365-day unlocked retention (takedowns and the WV-06 deletion path stay possible)",
    "Q-E2-07 [A-4] -> default c: page ships only if A-4 = a; else the text correction only":
        "Q-E2-07 [A-4] = c and WV-02 waived: the page ships (interim single-maintainer authority + public decision log)",
    "Q-E2-09 [A-4] -> default: page not published until the operator confirms the posture text":
        "Q-E2-09 [A-4] = c: written posture + published counts; canary declined; posture text via copy batch (B-2)",
    "D-SOURCES.7-2 [B-18] -> default b: sources stay gated -> row recorded as dropped (conditional)":
        "D-SOURCES.7-2 [B-18] = a: in scope; the operator registers the US 511 keys (OP-13) after the contact@ alias (C-8)",
    "IN-TICKET PAUSE (never pre-authorised under OM-20: capture runs on Part VIII-screened families need the per-family Part VIII sign); explicit verbatim go":
        "IN-TICKET PAUSE (never pre-authorised under OM-20: capture runs touching Part VIII-screened families); explicit verbatim go for the capture run",
    "HG-03 E4-B1/B5/B6 [A-7] + E4-B2 Part VIII sign [B-42] -> default: not flipped -> captures skipped, stand-ins stay disclosed":
        "HG-03 E4-B1/B5/B6 [A-7] = a (GL-GATE-07 batch-wide for the 23 targets; the operator executes the flips, OP-26) · E4-B2 [B-42] answered 'Agent clears, disclosed': the agent clears each family after the Part VIII screen; readouts state 'cleared by agent screen, no human review'",
    "D-K1-4 [B-22] -> default yes": "D-K1-4 [B-22] = yes",
    "OD-09 [B-23] -> default a (Natural Earth)": "OD-09 [B-23] = a (Natural Earth)",
    "D-K1-7 [B-22]": "D-K1-7 [B-44] = yes: the 'My location' control is P37.72's (SIG-GOV-017 analysis first)",
    "D-K2-2 [A-11] -> default a (descriptive only)": "D-K2-2 [A-11] = a (descriptive only)",
    "D-K2-3 [B-22]": "D-K2-3 [B-22] = as recommended",
    "D-K2-4 [B-25] -> default no: Flock share lists not used":
        "D-K2-4 [A-22] = yes (OD-24 b): the share-list configured_access claims (P36.75) feed the state × state Flock-sharing overview (A-11)",
    "D-K7-2 [B-22] -> default: the lane": "D-K7-2 [B-22] = the lane",
    "D-K11-1 [B-22]": "D-K11-1 [B-22] = as recommended",
    "D-J3-1 [B-19] -> default: no raw bytes published (archive built, not exposed)":
        "D-J3-1 [B-19] = yes: raw bytes for raw-ok sources only, after the Part VIII byte screen",
    "D-K8-1/D-K8-2 [B-22] -> as recommended":
        "D-K8-1 [B-44] / D-K8-2 [B-22] = as recommended (a locator always; an excerpt ≤ 300 characters only where recorded terms permit quotation)",
    "OD-15 [C-8] -> default: U-014 contact string (operator name + address) for upstream GETs; alias (OP-10) used if it exists":
        "OD-15 [C-8] = alias first: upstream GETs that need a contact string wait for contact@surveillancegraph.org (OP-10); no request sends the operator's name or address",
    "Q-L3-5 [B-31] -> default: /quality/ built but NOT published until answered (never a passing-checks-only page; TS-10/COV-01)":
        "Q-L3-5 [B-31] = yes: /quality/ public, including failing and ratchet checks; it states 'no human check performed' (Q-L3-3 = c)",
    "HG-03 per crosswalk source -> default not flipped (tier-0/1 ids from already-permitted sources only)":
        "HG-03 per crosswalk source: tier-0/1 ids from already-permitted sources; a new registry source (e.g. Census of Governments, Wikidata) needs its own line, flipped by the operator (OP-26)",
    "I8-Q5 [B-11] -> default b (core only): row recorded dropped": "I8-Q5 [B-11] = a: Wave D in scope",
    "per-row lines [A-7/B-33/B-39] -> not flipped":
        "per-row lines [A-7/B-33/B-39] = flip per GATE-P (A-7 batch-wide; RB-06b share-alike compartment; RB-08 territories = US); the operator executes the flips (OP-26)",
    "I8-Q5 [B-11] -> default b: dropped": "I8-Q5 [B-11] = a: Wave D in scope",
    "I7-S3/S4/S7 [B-32] -> metadata-only": "I7-S3/S4/S7 [B-32] = a: screened lanes only",
    "I7-RB-05 [A-7]": "I7-RB-05 [A-7] = a",
    "I7-RB-04 [A-7]": "I7-RB-04 [A-7] = a",
    "I7-RB-08 [B-33] -> default not flipped (capture terms first)": "I7-RB-08 [B-33] = a: territories treated as US under GL-GATE-07",
    "I7-RB-04/07 [A-7]": "I7-RB-04/07 [A-7] = a",
    "I7-S1 [B-32]": "I7-S1 [B-32] = a: screened lane (programme-level facts only)",
    "ING-GO-D verbatim [B-11] (collected at GATE-G6) + HG-11 -> default: dropped with ACQ-19..26":
        "ING-GO-D verbatim (collected at GATE-G6 with the operator's Wave-D flip list, OP-26) + HG-11 · I8-Q5 [B-11] = a: Wave D in scope",
    "Q-E2-23 [B-6] -> default: no deposit":
        "Q-E2-23 [B-6] = a: history scan, then SWH deposit (A-0.4: retained history disclosed in P34.18's correction note)",
    "D-J3-9 [B-21] -> default none": "D-J3-9 [B-21] = yes: Zenodo DOIs for openly licensed compartments only, after the attribution fix",
    "Q-27/OD-08 [B-8] -> default a: intake stays email-only -> live leg not run; re-homed later (trigger: announcement done + operator opens intake)":
        "Q-27/OD-08 [B-8] answered 'Email, no time promises': intake stays e-mail-only and dark -> live leg not run; re-homed later (trigger: announcement done + operator opens intake)",
    "D-K11-4 [B-8] -> default b: task pages say reporting opens with the intake form":
        "D-K11-4 [B-8] = a: task pages name the dispute address (the operator's address until contact@ exists)",
    "OP-22 operator walkthrough + D-K14-9 gallery [B-29] -> default yes (requested, never simulated)":
        "OP-22 operator walkthrough + D-K14-9 gallery [B-29] = yes (requested, never simulated; recorded 'operator walkthrough (maintainer, not independent)')",
    "D3-Q5 [A-17] -> default a: D3 §5 is the gate, no early preview": "D3-Q5 [A-17] = a: D3 §5 is the gate, no early preview",
    "D-K14-9 [B-29]": "D-K14-9 [B-29] = yes",
    "Q-L3-2 [A-6] -> default: supersession mechanics apply, D-R10-HUMAN-1 stays OPEN (non-blocking)":
        "Q-L3-2 [A-6] = a: superseded; D-R10-HUMAN-1 OPEN, non-blocking (T-EVAL-IND)",
    "Q-B4-1 / Q-14 (fallback: this becomes row 201 and checks run planning-side in seed_verify.py)":
        "Q-B4-1 = yes / Q-14 = a (full seed; the records-only fallback is not used)",
    "GATE-P decisions (Q-E2-*, Q-L3-1/2, D-K0-1, D-K1-1, D-K13-1..5, Q-12, D-G3-1)":
        "GATE-P decisions as recorded in feedback/RATIFICATION_LOG.md: 30 ADRs incl. the seven A-23 waivers (WV-01…07), ADR-183 express-terms acceptance, ADR-184 terms-conflicted public pages, ADR-185 Part VIII lanes",
    "GATE-P; Q-13 (if skills deferred, hand-apply SK-17..20 template content)":
        "GATE-P; Q-13 = a (Tier A skills applied at T0); hand-apply SK-17..20 template content only if the T6 check finds Devin Desktop does not load ~/.claude/skills",
    "GATE-P; Q-15; Q-16; Q-B4-4/Q-B6-4 (harness key, see CF-04)":
        "GATE-P; Q-15 = a; Q-16 = Devin Desktop, model swe-2-high (256k) for every row; harness key (CF-04)",
    "Q-L3-4": "Q-L3-4 = no (Round 11)",
    "operator obtains counsel (U-013: do not block)": "operator obtains counsel (U-013: do not block; WV-07 waived the counsel clauses, so this is optional)",
    "HG-09": "HG-09; C-8 alias first (after OP-10); B-18: D-SOURCES.7-2 = a (US 511) + D-SOURCES.8-2 = a (QLD/NSW)",
    "D-J3-9; HG-07": "D-J3-9 = yes; HG-07",
    "D-J3-8; HG-09": "D-J3-8 = a; HG-09",
    "Q-H2-6": "Q-H2-6 = a + c",
    "operator cost decision": "operator cost decision (G1-TRIM d: revisit after 3 measured bills)",
}


def rewrite_gate(r):
    g = r["operator_gate"]
    # truncated OM-20 cells (P34.24a, P34.42a, P34.44a, P35.14a, P35.15a, P37.4a, P35.1a)
    g = re.sub(r"named mutation -> OM-20 \(([^)]*)\) -> default: NOT pre-authorised =(?= G1-TRIM)",
               "<<OM20>> ·", g)
    g = OM.sub("<<OM20>>", g)
    out = []
    for s in g.split(" · "):
        st = s.strip()
        if st in SEG:
            st = SEG[st]
        st = re.sub(r"HG-03 (I7-RB-[0-9A-Z/\-]+) \[A-7\] -> default: (?:rows land )?ingestion_permitted=false",
                    r"HG-03 \1 [A-7] = a (GL-GATE-07 re-confirmed: batch-wide; Part VIII S-lines still apply): rows land "
                    r"ingestion_permitted=false and flip when the operator executes the wave's flip list (OP-26) with its ING-GO",
                    st)
        st = re.sub(r"D-J3-2 \[B-19\] -> default: no run logs published.*?\(PLAN §4\.4\)",
                    "D-J3-2 [B-19] = yes: scrubbed run logs published (robots disregard disclosed as host + count; W2-6)",
                    st)
        out.append(st)
    g = " · ".join(out)
    g = g.replace("<<OM20>>", om20(r))
    r["operator_gate"] = g


# ------------------------------------------------------------------ notes rewrites (generic)
NOTE_SUBS = [
    ("A-3-dependent (default b: GCS host, no public download links)", "S6: A-3 = a (R2 host; public download links)"),
    ("A-6-dependent (default: no automatic collapse)", "S6: A-6 = a (C0–C2 collapse)"),
    ("A-10-dependent (default: organisations withheld)", "S6: A-10 = b + c (registry auto-allow + typed 'not yet reviewed')"),
    ("A-7-dependent (default: nothing flips)", "S6: A-7 = GL-GATE-07 re-confirmed (batch-wide flips)"),
    ("A-12-dependent (default b: re-scope to the three islands)", "S6: A-12 = a (HTML-first page types)"),
]
COND = "conditional row: dropped (recorded, V2-skipped) when its gate default applies"

for r in rows:
    rewrite_gate(r)
    for a, b in NOTE_SUBS:
        r["notes"] = r["notes"].replace(a, b)

# ------------------------------------------------------------------ row-specific changes
def R(i):
    return by[i]


# 11A
note(R("P34.4"), "A-1 = 'None now; ticket it': early-11A ticket (TLS-expiry alert); exposure until then unresolved, operator-deferred")
note(R("P34.5"), "A-2 = infra-only ceiling, 'alert later' (this ticket, early 11A), agent usage per wave with a pause at any usage-limit event")
note(R("P34.6"), "A-1 = 'None now; ticket it': the QA-9 drill is an early-11A ticket")
r = R("P34.17")
r["notes"] = r["notes"].replace(", /visual-language/ if A-0 did not remove it", ", /visual-language/ (A-0.3 = b)")
note(r, "A-0.3 = b: removes /visual-language/ and the handle-bearing pages (N-6), R1.3/R1.11; R1.8 dropped (A-8 = keep all: the P34.19 disclosure replaces the withdrawal); R1.2 promises no response time and states that senders disclose their address (B-8, WV-05); A-20 basis-label/status text and the express-terms disclosure text go to copy batch #1")
r = R("P34.18")
r["notes"] = r["notes"].replace(
    "repo tip registry notes/agency strings (if A-0.1 did not already); sig-public 09-27 tree tombstoned per G3 withdrawal (if A-0.2 did not)",
    "repo tip registry notes/agency strings (A-0.1 = b: owned here); the sig-public 09-27 tree's anonymous access is P34.21b's (A-0.2 = b)")
note(r, "the correction note discloses the retained git history (A-0.4 = a); it unblocks P37.55's deposits after the history scan · not on the 11A OM-20 list -> the hosted rename is an in-ticket go")
r = R("P34.19")
r["title"] = "Express-terms disclosure instead of withdrawal (A-8) + leak-taint withdrawal of 9 Atlas FR rows (F-337)"
r["notes"] = ("size S | owns S0/S1: F-403(S1) — closed by the operator's express-terms acceptance (ADR-183) + disclosure, "
              "not by withdrawal | catalog: early R11 (wave 0) | S6: A-8 = 'Keep all, accept risk': the ≈8,088 rows "
              "(5,267 NEW-1 + ≈2,821 camreg_txdot_rep_tx, incl. the 3 live NC rows) stay public; each source's rights "
              "record, page and list entry show the captured terms verbatim and the operator-accepted basis (text via copy "
              "batch #1); demo_* task pages are still stripped (R1.9, C-12); the 9 leak-derived Atlas FR rows (F-337) are "
              "still withdrawn (not an A-8 row) | replaces the J3 D-J3-5 / I7-C1 withdrawal work in TX-02, TX-10b, DSRC-03, UX9-4")
r["window_constraints"] = "publication rides P34.17 (pages) and P34.21b (exports)"
r = R("P34.21b")
r["leg_runs"] = "1"
r["live_legs"] = ("2: L1 sig-public 09-27 anonymous read/list removal + tombstone after its verbatim go (earliest; PUB "
                  "window; not a hosted DB write) | L2 republish #2 after the verbatim go (>= 10-13T12:00Z backfill)")
note(r, "A-0.2 = b: owns removing anonymous read/list on the sig-public 09-27 tree (live-fetched prefixes excluded after a read-only listing); also closes most of the denial-of-wallet window before P35.5")
note(R("P34.21a"), "A-8 = keep all: the re-export keeps the express-terms rows, with terms + basis in ATTRIBUTION files")
note(R("P34.25"), "adds the API response basis label (A-20 = a)")
r = R("P34.28")
r["title"] = "Readout authorship rules in full (G4b) + gate-record hedge/delegation lint + G4c signed-gate CI verification (A-16)"
r["est_runs"] = "1.0"
note(r, "A-16 = yes: + CI verification of the operator's gate signatures against a committed allowed_signers (OP-25); LATER-15 closes into this row; size S -> M")
r = R("P34.27")
r["depends_on"] = "P34.7;P34.8"
note(r, "OP-18 removed: C-13 answered at GATE-P ('Superseded', 2026-10-01T05:03:05Z)")
r = R("P34.45")
note(r, "moved back 11B -> 11A after P34.44b (A-20 = a; its ER re-run is on the 11A OM-20 list approved at GATE-P, S5-3); no edge to P35.57")
for i in ("P34.24a", "P34.44a"):
    note(R(i), "not on the 11A OM-20 list (S5-3) -> its named mutation is an in-ticket go")

# 11B
note(R("P35.57"), "A-20 = a: no longer gates P34.45 or the 11B structural writes; kept at the head of 11B as an improvement (its own go at GATE-G4)")
note(R("P35.5"), "A-3 = a (R2; the operator switches nameservers, OP-09)")
note(R("P35.11"), "X3 confirmed (2026-10-01T04:07:45Z): widening configs enabled")
note(R("P35.1b"), "G1-TRIM = a adds the scheduler consolidation (−$7/mo); A-5 = GL-GATE-08 as is, so no step pauses the 103 robots-disallowing hosts (that default-only step is gone) — split at PLAN-11B if the consolidation does not fit the 256k window")
r = R("P35.1a")
r["operator_gate"] = om20(r)
note(R("P35.17"), "A-18 = yes: in-ticket pause for the operator's HG-03 flip after terms capture")
r = R("P35.38")
r["depends_on"] = "P34.25"
note(r, "B-6 = move UA, no purchase: removes every sig-project.org reference from code and docs; OP-11 dropped")
note(R("P35.46"), "Q-L3-6 = a: C2 enabled")
note(R("P35.60"), "readout generator writes 'single maintainer, no second reviewer' (WV-03) and 'no human check performed' (B-31)")
r = R("P35.63")
r["depends_on"] = ";".join(t for t in r["depends_on"].split(";") if not t.startswith("P35.49"))
note(r, "P35.49 dropped (B-31 = no maintainer check); readout states 'single maintainer, no second reviewer' and 'no human check performed'")
for i in ("P36.1a", "P36.1b"):
    note(R(i), "A-5 = GL-GATE-08 as is: no host is paused for robots; the opt-out register and 046c reservation refusal are still built")
r = R("P36.12")
r["depends_on"] += ";P36.74"
r["leg_runs"] = "4.5"
r["live_legs"] = r["live_legs"].replace("8-9: one leg per family-day 10-26 -> 11-05 (ACQ-08..15)",
                                        "9-10: one leg per family-day 10-26 -> 11-05 (ACQ-08..15 + the Flock transparency-portal family, P36.74)")
note(r, "+ the direct Flock transparency-portal family (A-17 D3-Q3 b; P36.74); flips executed by the operator with ING-GO-B (OP-26)")
p = R("P35.49")
p.update(row="", sub_round="dropped (S6)", kind="dropped", est_runs="0", leg_runs="0", live_legs="",
         operator_gate="dropped: Q-L3-3 [B-31] = c (no maintainer check); D-P30.2b-1 stays OPEN, non-blocking (T-EVAL-IND)")
note(p, "dropped — B-31 'No maintainer check' (2026-10-01T04:43:37Z): no OPCHECK protocol; readouts and /quality/ say 'no human check performed'")
note(R("P35.48"), "Q-L3-4 = no")

# 11C
r = R("P37.2")
r["notes"] = r["notes"].replace(
    "CF-06: OSM origin query scoped to the US + territories (the layer it replaces); non-US per-country counts logged, not ingested",
    "S6: S5-4 = keep non-US acquisition (CF-06 not confirmed): the national run keeps non-US objects (I8 §4.3; ≈ 1.11 M claims again the planning figure); US-first ordering for priority")
note(R("P37.1"), "S5-4 = keep non-US: code covers non-US objects too")
r = R("P36.13")
r["operator_gate"] = r["operator_gate"].replace("(rate limits; optional Cloud Armor within the ceiling)",
                                                "(rate limits; no Cloud Armor now, D-K3-6)")
note(r, "B-30 D-K3-6 = yes: no Cloud Armor now (−$6/mo vs the S4c projection)")
note(R("P36.2"), "B-41 as answered (R3 flip; R4a OGL-Edmonton; R4b flip; R4c -> P37.70; R4d decline; R5 flip; R6a capture; R6b close) + B-36 IU1–5 terms capture; flips executed by the operator (OP-26); split at PLAN-11C if it does not fit 256k")
R("P36.2")["title"] = "Rights-flip/decline batch for owed rows (D-SOURCES.7-1, 8-1, 9-1, 9-4) + terms capture (IU1–IU5, E4-R4a OGL-Edmonton, E4-R6a bidnet)"
r = R("P36.32")
r["depends_on"] += ";P36.79"
note(r, "B-28 = b: reads only the sealed set's sha256, never the set (P36.79)")
r = R("P36.71")
r["depends_on"] += ";P36.79"
note(r, "the only context that reads the sealed held-out set (B-28 = b)")
note(R("P36.33"), "A-3 = a: basemap on R2")
note(R("P36.38"), "B-30 = yes (+$3/mo)")
r = R("P36.55")
r["operator_gate"] = "D3-Q4 [B-27] = yes: neutral 'Other public resources' block (no avoidance routing or plate lookup) · D-K7-3 = official agenda portals always"
note(r, "B-27 = yes")
r = R("P36.60")
r["operator_gate"] = "D-K8-4 [B-44] = as recommended: show the 255 synthetic run-record artifacts with honest labels"
r = R("P36.34")
r["operator_gate"] = "D-K4-3 [B-44] = as recommended: all counties with ≥ 1 record, places with ≥ 10 records + any place with non-site evidence, non-US admin-1 with ≥ 10"
r = R("P35.45")
r["operator_gate"] = "D-K4-3 [B-44] = as recommended (county + place pages)"
note(R("P36.64"), "C-4 tagline; C-5 omit 'who runs SIG' until the operator writes it")
note(R("P36.70"), "B-9 = a: Class R rehearsal under the standing go (renewed at GATE-G5)")
for i in ("P36.4", "P36.5", "P36.6", "P36.7", "P36.8", "P36.9a", "P36.9b", "P36.10", "P36.11"):
    note(R(i), "A-7 = GL-GATE-07 re-confirmed: batch-wide flip lines (Part VIII S-lines B-32 still apply)")

# 11D
note(R("P37.3"), "B-14 = a; the WV-06 deletion path (P37.71) builds on this retention")
for i in ("P37.47", "P37.48", "P37.49", "P37.50", "P37.51", "P37.52", "P37.53", "P37.54", "P37.12"):
    rr = R(i)
    rr["notes"] = rr["notes"].replace(COND, "S6: in scope (B-11 I8-Q5 = a; B-18 = a for P37.12) — the S4c drop-by-default rule no longer applies")
    rr["notes"] = rr["notes"].replace("catalog: R11 (conditional)", "catalog: R11")
r = R("P37.54")
r["depends_on"] = "P37.47;P37.48;P37.49;P37.50;P37.69a;P37.69b;P37.51;P37.52;P37.53;P36.76;P36.77;P36.78"
r["notes"] = r["notes"].replace("CF-06: ACQ-23a/b moved to LATER-09; T3 drops them from this row's depends_on",
                                "S6: S5-4 = keep non-US: ACQ-23a/b back as P37.69a/b")
r["leg_runs"] = "1.5"
note(r, "first window also activates Axon Connect (P36.76), DocumentCloud (P36.77) and Sourcewell/OMNIA (P36.78); flips executed by the operator with ING-GO-D (OP-26)")
r = R("P37.59")
r["notes"] = r["notes"].replace(COND, "S6: stays conditional — B-8 = e-mail-only: engineering lands dark, live leg not run")
note(R("P37.16a"), "B-42 = agent clears each family after the Part VIII screen (disclosed); the capture run is still an in-ticket go")
note(R("P37.16b"), "B-42 = agent clears each family after the Part VIII screen (disclosed)")
r = R("P37.25")
r["depends_on"] += ";P36.75"
note(r, "A-22 = b / D-K2-4 = yes: uses P36.75's share-list claims for the state × state Flock-sharing overview (A-11)")
r = R("P37.63")
r["depends_on"] += ";P37.72"
r = R("P37.67")
r["depends_on"] = ";".join(t for t in r["depends_on"].split(";") if t != "P35.49")
note(r, "P35.49 dropped (B-31)")
r = R("P37.68a")
r["depends_on"] = ";".join(t for t in r["depends_on"].split(";") if not t.startswith("P35.49"))
r["depends_on"] += ";P37.72"
note(R("P37.44"), "C-8 = alias first")
note(R("P37.45"), "B-31: Q-L3-5 = yes, 'no human check performed'")
note(R("P37.55"), "B-6 Q-E2-23 = a; B-21 = yes; A-0.4 = a (history disclosed by P34.18)")
note(R("P37.7"), "WV-02 waived: interim single-maintainer authority + public decision log; also logs every WV-06 deletion")
r = R("P38.2")
note(r, "the accepted-deviations list now holds the operator-chosen descopes and accepted risks (PLAN §4.3), the C-12 withdrawals and the seven A-23 waivers — no 'not attempted (default …)' lines remain")
r = R("GATE-ANNOUNCE")
note(r, "all seven A-23 waivers adopted, so 'spec MUSTs unmet at launch' lists only items owed for other reasons; the post-round Claude Code review (REVIEW-R11) is cited if it has finished; dispute text states no response time is promised (B-8)")

# seeds
r = R("SEED-11")
r["est_runs"] = "4.0"
note(r, "30 ADRs after GATE-P (23 + WV-04/05/06/07 + ADR-183/184/185); 4 contexts of ≈ 7–8 ADRs each, each ≤ ~150k tokens loaded (A-15)")
note(R("SEED-13"), "manifest rows for 309 chain rows; full contracts for the 59 11A rows + PLAN-11B; every Load list sized for Devin Desktop's 256k window (≤ ~150k loaded; A-15) — split the unit at T3 if a context exceeds it")
note(R("SEED-14"), "registers record the S6 changes: LATER-10/15 pulled in, R11-ACQ-23a/b back in the round, OP-11/14/15/16/17/21 dropped, OP-18 done; D-P30.2b-1 stays OPEN under T-EVAL-IND; T4 records the final kind of every decision-dependent universe item from decision_catalog.csv's operator_answer")
note(R("SEED-17"), "harness: Devin Desktop, model swe-2-high (256k context) for every row (A-15); OM-01 trailers enforced in CI because commits keep the operator's name as author (A-21)")
note(R("SEED-19"), "the orient dry-run runs in Devin Desktop and verifies that it loads the skills from ~/.claude/skills (Devin CLI was verified to; Desktop was not)")
for i in ("HUMAN-H4", "P32.22a", "HUMAN-H5", "P32.23"):
    pass

# operator rows
note(R("OP-01"), "A-14 = all, staged: Tier A applied at T0 (in progress); the T6 check confirms Devin Desktop loads them")
R("OP-01")["sub_round"] = "T0 (A-14: applied now, before Stage B)"
R("OP-02")["sub_round"] = "before row 201 (first Devin Desktop dispatch)"
R("OP-03")["sub_round"] = "early in the round (A-14 'All, staged')"
R("OP-04")["sub_round"] = "early in the round, alongside P34.7-P34.33 (A-14)"
note(R("OP-08"), "B-10 = yes: the operator tags v0.1.0 after the sitting")
note(R("OP-09"), "A-3 = yes: the operator switches nameservers from the P34.50 runbook")
r = R("OP-10")
r["sub_round"] = "right after OP-09 (by GATE-G4); before any contact-string request (C-8)"
note(r, "C-8 = alias first: OP-13's key sign-ups, EDGAR (later) and any upstream GET needing a contact string wait for it")
r = R("OP-13")
r["title"] = "Register the free US 511 API keys and the QLDTraffic + NSW Live Traffic keys in Secret Manager (HG-09), after the contact@ alias"
r["sub_round"] = "after OP-10; by GATE-G6 (before P37.12, P37.70)"
r["depends_on"] = "OP-10"
note(r, "B-18 = US + AU keys (D-SOURCES.7-2 a, D-SOURCES.8-2 a); C-8 alias first")
note(R("OP-12"), "A-2a = alert later: the budget alert + billing export are P34.5's, early 11A")
note(R("OP-19"), "B-21 = yes")
r = R("OP-20")
r["sub_round"] = "by GATE-G5 (before P36.50 TX-10b)"
note(r, "B-20 = a: pipeline key signs manifests; the operator's gate key is OP-25")
note(R("OP-22"), "B-29 = yes (gallery + spec page); C-5: the 'who runs SIG' text only if and when the operator writes it")
r = R("OP-23")
r["title"] = "Store the agent-made git bundle of the planning branch privately, off-disk"
r["sub_round"] = "stage-B (when the agent hands over the bundle; before the T6 push)"
note(r, "B-16 = a + c: push at T6 (OD-27 = a)")
note(R("OP-24"), "the backstop runs in Devin (Desktop if it supports scheduled sessions, else Devin CLI headless with the same model) — verified at T6 and recorded as a harness note (OM-01)")
DROP = {
    "OP-11": "dropped — B-6 'Move UA, don't buy domain': sig-project.org is not purchased (residual squatting risk recorded; P35.38 removes every reference)",
    "OP-14": "dropped — A-10 'Auto-allow + absence only': no operator top-50 review",
    "OP-15": "dropped — D-P32.3-1 folds into A-10's auto-allow ADR + P37.46 (no operator review)",
    "OP-16": "dropped — D-P30.2b-1 had no fold target once B-31 removed the maintainer check: stays OPEN, non-blocking (T-EVAL-IND, LATER-01)",
    "OP-17": "dropped — B-31 'No maintainer check'",
    "OP-21": "dropped — B-28 'Separate agent, labelled': P36.79 writes the held-out set",
}
for i, why in DROP.items():
    rr = R(i)
    rr.update(sub_round="dropped (S6)", kind="dropped", depends_on="")
    note(rr, why)
rr = R("OP-18")
rr.update(sub_round="done at GATE-P (2026-10-01T05:03:05Z)", kind="done", depends_on="")
note(rr, "done — C-13 answered 'Superseded' (2026-10-01T05:03:05Z)")

# later rows
for i, to, why in (("LATER-10", "P37.70", "B-18 + S5-4: AU keyed APIs come into Round 11"),
                   ("LATER-15", "P34.28 + OP-25", "A-16 = yes: the gate-signing key is set up now"),
                   ("R11-ACQ-23a", "P37.69a", "S5-4 = keep non-US acquisition"),
                   ("R11-ACQ-23b", "P37.69b", "S5-4 = keep non-US acquisition")):
    rr = R(i)
    rr.update(sub_round=f"moved (S6) -> {to}", kind="moved", depends_on="", est_runs="0")
    note(rr, f"moved into Round 11 as {to} ({why})")
r = R("LATER-09")
r["title"] = "Acquisition long tail: Tier-2 remainder (130), Tier 3, EDGAR (after the alias), CourtListener bulk, OCDS, paid data"
note(r, "tribal (B-32 S8) and territory (B-33 RB-08) channels and ACQ-23a/b moved into Round 11; EDGAR ingestion stays later (B-38), first request only after contact@ exists")
r = R("LATER-19")
note(r, "scheduler consolidation moved into P35.1b (B-13 a); what remains: Cloud SQL CUD after 3 measured bills (≈ −$12/mo); min-instances 0 and LB removal not adopted")
note(R("LATER-01"), "+ D-P30.2b-1 (no fold target after B-31)")
note(R("LATER-18"), "Q-L3-4 = no")


# ------------------------------------------------------------------ S6 extra text fixes
R("P36.32")["notes"] = R("P36.32")["notes"].replace("unless OP-21 is done (TS-20)", "(TS-20; always, since B-28 = b)")
note(R("P35.48"), "no OPCHECK accompanies P35.63 (B-31 c); the agent lane stays labelled and never gates")
R("P37.54")["title"] = "Wave D activation (Tier 2 + ACQ-23a/b + Axon Connect, DocumentCloud, Sourcewell/OMNIA)"
for i in ("SEED-02", "SEED-03"):
    R(i)["notes"] = R(i)["notes"].replace("guard core stays in the seed (A-13 rec); if A-13 defaults, T3 inserts it as row 201 (P34.0a) and renumbers +2",
                                          "guard core stays in the seed (A-13 = a; the P34.0a fallback is not used)")
r = R("GATE-G5")
r["notes"] = r["notes"].replace("ING-GO-C + Q-23 for Wave C", "ING-GO-C for Wave C").replace("D-K2-1 top-50 review (OP-14), ", "")
note(r, "Q-23 (a), A-10 (no review) and I8-Q5 (a) were answered at GATE-P; G5 collects ING-GO-C, the Wave-C/vendor flip list (OP-26), the 11C OM-20 list and the Class R standing-go renewal (B-9)")
note(R("GATE-G4"), "G4 also collects the Wave A/B HG-03 flip lists (OP-26), the 11B OM-20 list and the Class R standing-go renewal (B-9); every other S5 line was answered at GATE-P")
note(R("GATE-G6"), "I8-Q5 answered a at GATE-P (Wave D in scope); G6 collects ING-GO-D, the Wave-D flip list (N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08; OP-26), the 11D OM-20 list and the standing-go renewal")
note(R("P34.47"), "RI-01 closes only when the repo tip (r11 branch; public main after OP-08) and the sig-public 09-27 listing (after P34.21b's first leg) are clean")
for i in ("PLAN-11B", "PLAN-11C", "PLAN-11D"):
    note(R(i), "the Phase-4 sizing review checks every contract against Devin Desktop's 256k window (<= ~150k tokens loaded; A-15) and splits oversized rows")
for i in ("P34.46", "P35.61", "P35.63", "P36.12", "P36.72a", "P37.65a", "P37.68d", "P38.1a", "P38.1b", "P38.3b"):
    note(R(i), "looks oversized for a 256k window (A-15): split at T3 (11A) or at the PLAN row's Phase-4 review if its Load list + working set exceeds ~150k tokens")


note(R("P36.1a"), "S6 flag (R-19): classify the captured licence metadata of the A-8 express-terms rows; any that is an affirmative machine-readable reservation under SIG-INGEST-046c (not waived) goes back to the operator")
note(R("P34.17"), "S6 flag (R-31): SIG-GOV-003 (published SLAs by category) is not waived and conflicts with B-8; the notice promises no time and the conflict is put to the operator")

# ------------------------------------------------------------------ new rows
def new(**kw):
    base = {k: "" for k in FIELDS}
    base.update(kw)
    return base


NEW = {
    "P36.74": new(id="P36.74", cat_ids="R11-ACQ-29", sub_round="11B", phase="P36", kind="ticket",
                  title="Flock transparency-portal connector: direct fetch of agency portals on Flock's host (A-17 D3-Q3 b)",
                  depends_on="P35.6;P35.14b;P35.15b;P36.1a(S2);P35.28;P36.15;P35.66;P34.49",
                  operator_gate=("D3-Q3 [A-17] = b (2026-10-01T04:16:29Z): fetch vendor-hosted public pages under ADR-184's envelope ("
                                 + ENV + ") · aggregate-only for audit/search figures (S3 lane): no search reasons, case numbers, operator/user ids or plate data stored (SIG-PUB-002/003a) · "
                                 "HG-03: the new source row lands ingestion_permitted=false; the operator flips it with ING-GO-B (OP-26)"),
                  live_stage="none (activation in P36.12)", est_runs="1.0", leg_runs="0", window_constraints="none",
                  notes=("size M | S6: new (A-17 D3-Q3 b; A-22 b): direct freshness and coverage beyond the Eyes on Flock mirror "
                         "(≈ 23 % of networks, D2-10); portal facts (retention, camera counts, aggregate search counts) and "
                         "shared-with lists for P36.75; terms text captured verbatim into the rights record | inference ≈ +$0.5/mo")),
    "P36.79": new(id="P36.79", cat_ids="R11-K13-SRCH-00", sub_round="11C", phase="P36", kind="ticket",
                  title="Held-out search relevance set (≥ 40 queries) written by a separate agent context (B-28 b)",
                  depends_on="P35.63",
                  operator_gate=("restricted-bucket write = named mutation -> OM-20: pre-authorised only if the GATE-G5 list the operator approves verbatim names this row (expiry at the next GATE; OM-10); otherwise NOT pre-authorised = IN-TICKET PAUSE · "
                                 "D-K3-7 [B-28] = b (2026-10-01T04:41:11Z): labelled 'agent-authored held-out set; not independent'; "
                                 "written before, and never visible to, the contexts that tune search (P36.31, P36.32, P36.38–P36.40); "
                                 "stored outside the worktree (restricted-bucket object) with only its sha256 committed; read only by P36.71"),
                  live_stage="production write (restricted-bucket object)", est_runs="0.5", leg_runs="0",
                  window_constraints="any time outside 03:00-10:00Z",
                  notes="size S | S6: new (B-28 b); replaces OP-21 | judged against the first model release (P35.63)"),
    "P36.75": new(id="P36.75", cat_ids="R11-ACQ-30", sub_round="11C", phase="P36", kind="ticket",
                  title="Flock share lists -> organisation-level configured_access claims (D-K2-4 yes; §43.2a/Part VIII screen)",
                  depends_on="P36.74;P35.25;P35.28;P34.49;P36.41",
                  operator_gate=("hosted append-only claim write = named mutation -> OM-20: pre-authorised only if the GATE-G5 list the operator approves verbatim names this row (expiry at the next GATE; OM-10); otherwise NOT pre-authorised = IN-TICKET PAUSE · "
                                 "D-K2-4 + OD-24 [A-22] = yes / b (2026-10-01T04:25:48Z): organisation level only, after the §43.2a/Part VIII "
                                 "screen (no operator ids, search reasons or audit rows) · A-10 = b + c: organisation labels per the auto-allow ADR, others 'not yet reviewed'"),
                  live_stage="production write (append-only claims)", est_runs="1.0", leg_runs="0.5",
                  live_legs="1: hosted append-only claim write after the G5 list or its go", window_constraints="AR-3 + AR-2",
                  notes=("size M | S6: new (A-22 b): the 474,184 share-list edges (I3) from the Eyes on Flock mirror plus P36.74's direct "
                         "portals become organisation-level claims; feeds P37.25's state × state Flock-sharing overview (A-11) | "
                         "split at PLAN-11C if screen + resolution do not fit 256k")),
    "P36.76": new(id="P36.76", cat_ids="R11-ACQ-31", sub_round="11C", phase="P36", kind="ticket",
                  title="Axon Fusus 'Connect <Place>' connector (B-35 IT7 full fetch; SIG-PUB-002 redaction before anything is persisted)",
                  depends_on="P35.6;P36.15;P35.66;P35.28;P34.49",
                  operator_gate=("I7-IT7 [B-35] = a (2026-10-01T04:46:04Z): full fetch of the agency-hosted Connect pages under ADR-184's envelope · "
                                 "SIG-PUB-002/003 are not waived: private registrants (resident or business names, home addresses, contact data, cameras at private "
                                 "residences) are redacted in memory before any byte is persisted — only a redacted re-serialisation is stored (J4 P8-5 pattern); "
                                 "programme-level facts and counts only (S1 lane) · HG-03: the new row lands ingestion_permitted=false; the operator flips it with ING-GO-D (OP-26)"),
                  live_stage="none (activation in P37.54)", est_runs="1.0", leg_runs="0", window_constraints="none",
                  notes=("size M | S6: new (B-35 IT7 a; A-17) | U-007 Axon priority: code in 11C, activation in Wave D's first window "
                         "(11-23 -> 12-04) so it ships in P37.65 | flagged in design/S6-ratification-applied.md: the log's 'never stored in public "
                         "output' is narrower than SIG-PUB-002's 'MUST NOT store, in any tier'; this row applies PUB-002 | inference ≈ +$0.3/mo")),
    "P36.77": new(id="P36.77", cat_ids="R11-ACQ-32", sub_round="11C", phase="P36", kind="ticket",
                  title="DocumentCloud / MuckRock connector (E4-R2a flip; public documents only; Part VIII screen; uploader link)",
                  depends_on="P35.6;P36.15;P36.10;P34.49",
                  operator_gate=("E4-R2a [B-41] = b (2026-10-01T04:51:39Z) + I7-C2 [B-39] = fetch despite terms: public documents only, under ADR-184's "
                                 "envelope; Part VIII screen on every byte (S6/S7 free-text and incidental-name redaction); every claim links the uploader's page · "
                                 "HG-03: the operator flips documentcloud with ING-GO-D (OP-26) · SIG-INGEST-036 rule 6 (ask first where the source is a small "
                                 "civil-society project) is not waived and conflicts with U-011 (no contact): flagged at S6 (design/S6-ratification-applied.md §6); "
                                 "the question (waive rule 6 for it, authorise contact, or keep it dark) goes to the operator before activation"),
                  live_stage="none (activation in P37.54)", est_runs="1.0", leg_runs="0", window_constraints="none",
                  notes="size M | S6: new (B-39 C2; E4-R2a b) | inference ≈ +$0.5/mo (document bytes in the evidence store)"),
    "P36.78": new(id="P36.78", cat_ids="R11-ACQ-33", sub_round="11C", phase="P36", kind="ticket",
                  title="Sourcewell + OMNIA Partners contract-page connector (B-39 C3 fetch despite terms)",
                  depends_on="P35.6;P36.7;P36.15",
                  operator_gate=("I7-C3 [B-39] = fetch despite terms (2026-10-01T04:49:27Z) under ADR-184's envelope (" + ENV + ") · "
                                 "HG-03: the operator flips sourcewell + omnia_partners with ING-GO-D (OP-26)"),
                  live_stage="none (activation in P37.54)", est_runs="1.0", leg_runs="0", window_constraints="none",
                  notes="size M | S6: new (B-39 C3) | inference ≈ +$0.2/mo"),
    "P37.69a": new(id="P37.69a", cat_ids="R11-ACQ-23a", sub_round="11D", phase="P37", kind="ticket",
                   title="International open-data portals and files (ACQ-23a; N1–N21 lines)",
                   depends_on="P35.6",
                   operator_gate=("I7-N1…N21 [B-34] = a (2026-10-01T04:46:04Z): flip under the non-US database-right precedent (express prohibitions "
                                  "excluded) · RB-06 [A-7] = a · S5-4 = keep non-US acquisition · SIG-PUB-017 jurisdiction-conditional publication · "
                                  "the operator executes the flips with ING-GO-D (OP-26)"),
                   live_stage="none (activation in P37.54)", est_runs="1.0", leg_runs="0", window_constraints="none",
                   notes=("size M | S6: back in the round (S5-4; was LATER-09 under CF-06) | SIG-LIC-009's counsel clause waived (WV-07); "
                          "the EU/UK database right stays a risk-register item (PLAN §14 R-20)")),
    "P37.69b": new(id="P37.69b", cat_ids="R11-ACQ-23b", sub_round="11D", phase="P37", kind="ticket",
                   title="OGC WFS family (ACQ-23b)", depends_on="P37.69a",
                   operator_gate="as P37.69a (N1–N21 = a; RB-06 = a; flips executed by the operator, OP-26)",
                   live_stage="none (activation in P37.54)", est_runs="1.0", leg_runs="0", window_constraints="none",
                   notes="size M | S6: back in the round (S5-4)"),
    "P37.70": new(id="P37.70", cat_ids="R11-SRC-07", sub_round="11D", phase="P37", kind="ticket",
                  title="Keyed AU traffic-camera APIs: QLDTraffic + NSW Live Traffic (D-SOURCES.8-2 a; E4-R4c b)",
                  depends_on="OP-13;P35.6",
                  operator_gate=("named mutation -> OM-20: pre-authorised only if the GATE-G6 list the operator approves verbatim names this row (expiry at the next GATE; OM-10); otherwise NOT pre-authorised = IN-TICKET PAUSE · "
                                 "D-SOURCES.8-2 [B-18] = a: the operator registers the QLDTraffic + NSW keys (OP-13; Secret Manager, HG-09) after the "
                                 "contact@ alias (C-8) · E4-R4c [B-41] = b: the QLDTraffic API replaces camreg_qldc_au"),
                  live_stage="production write", est_runs="1.0", leg_runs="0", window_constraints="AR-3 + AR-2",
                  notes="size M | S6: pulled in from LATER-10 (S5-4 keep non-US; B-18) | inference ≈ +$0.2/mo"),
    "P37.71": new(id="P37.71", cat_ids="R11-GOV-06", sub_round="11D", phase="P37", kind="ticket",
                  title="Single-operator true-deletion path (WV-06): design first, then a mechanism that keeps the audit record",
                  depends_on="P37.3;P35.55;P37.7",
                  operator_gate=("WV-06 [A-23] waived (2026-10-01T04:28:49Z): 'I alone may authorise a deletion, publicly logged with its reason.' · "
                                 "never on an OM-20 list; never run by an agent without the operator's in-ticket go naming the material; every use logged "
                                 "publicly with its reason (P37.7's decision log) and a tombstone recording category and date, never content "
                                 "(SIG-GOV-008's tombstone clause stands) · the insert-only claim-spine rule is unchanged for every other path"),
                  live_stage="none (mechanism built; used only on an operator go)", est_runs="1.0", leg_runs="0", window_constraints="none",
                  notes=("size M | S6: new (WV-06 waived; operator chose it over 'keep owed') | design note + ADR-181 compensating controls first; "
                         "this ticket executes no deletion | must reconcile B-14's unlocked 365-day retention (P37.3) and the OCFL write-once store "
                         "(ADR-023): the design states how a governance-mode delete keeps the audit record")),
    "P37.72": new(id="P37.72", cat_ids="R11-K13-MAP-08", sub_round="11D", phase="P37", kind="ticket",
                  title="'My location' map-pan control (D-K1-7 approved): written SIG-GOV-017 analysis first",
                  depends_on="P37.18",
                  operator_gate=("D-K1-7 [B-44] = yes (2026-10-01T04:51:39Z; operator chose it over 'no') · SIG-GOV-017 is not waived: the ticket "
                                 "first writes a GOV-017 analysis; the control only pans the map (browser-only geolocation after a click; never sent to SIG; "
                                 "no 'cameras near you' list, count, alert or proximity notice) · if the analysis finds it cannot comply -> IN-TICKET PAUSE "
                                 "and the question (waive GOV-017 for it, or drop it) returns to the operator"),
                  live_stage="none (ships with P37.63)", est_runs="0.5", leg_runs="0", window_constraints="none",
                  notes="size S | S6: new (B-44 D-K1-7) | T1 enhancement inside the K0 /map/ budget"),
}
REVIEW = new(id="REVIEW-R11", cat_ids="R11-REVIEW-01", sub_round="post-round", phase="post-round", kind="review",
             title="Post-round deep review by Claude Code (Opus 5.5, xhigh effort), modelled on the Stage-P review",
             depends_on="P38.4",
             operator_gate=("A-15 (2026-10-01T04:21:56Z): 'Claude Code can do a deep review after the entire thing' · read-only against code, "
                            "build memory, CI and live state; no production mutation; its findings are agent findings (P1 evidence classes), never human review"),
             live_stage="read-only", est_runs="8.0", leg_runs="0", window_constraints="after the final release and the tail's DOC row",
             notes=("S6: new closing unit (A-15) — not a chain row: a different harness, after the final release, outside the Devin chain "
                    "(no in-round second harness) | output: a findings register (S0–S3, FINDINGS.csv-style) + a next-round planning input | "
                    "≈ 8–12 fresh Claude Code contexts (inference, modelled on Stage P's review rows); its own meta-plan sizes them | "
                    "GATE-ANNOUNCE's packet cites it if it has finished; the operator may wait for it"))
OPS_NEW = [
    new(id="OP-25", cat_ids="NEW (S6)", sub_round="stage-B (by GATE-B if possible; at the latest before GATE-G4)", phase="—",
        kind="operator",
        title="Operator-only gate-signing key (A-16): a passphrase- or hardware-backed SSH signing key never loaded into an agent-reachable ssh-agent; public key committed to allowed_signers",
        depends_on="", operator_gate="Q-B4-2 [A-16] = a; P34.28 verifies gate signatures in CI", live_stage="none",
        est_runs="0", leg_runs="0",
        notes="S6: new (A-16 = yes); ≈ 15–30 min; optional hardware key ≈ $25–55 one-off; LATER-15 closes"),
    new(id="OP-26", cat_ids="NEW (S6)",
        sub_round="per wave: A-18 boundaries (P35.17); Waves A/B at GATE-G4; Wave C at GATE-G5; Wave D (N1–N21, ACQ-23, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08) at GATE-G6",
        phase="—", kind="operator",
        title="HG-03 flips of the GATE-P-decided rows, executed by the operator per wave (agents prepare each flip list; the operator's verbatim line flips)",
        depends_on="", operator_gate="HG-03 (operator only; never pre-authorised); lines decided at GATE-P: A-7, A-18, B-33, B-34, B-35, B-39, B-41",
        live_stage="production write (registry flip)", est_runs="0", leg_runs="0",
        notes="S6: new — makes the operator's flip act explicit; ≈ 0.25 h per wave (5 sittings incl. A-18)"),
]

# ------------------------------------------------------------------ assemble order
chain = [r for r in rows if r["sub_round"] in CHAIN and r["id"] != "P34.45"]
other = [r for r in rows if r["sub_round"] not in CHAIN and r["id"] != "P34.45"]
order = [r["id"] for r in chain]


def insert_after(anchor, ids):
    i = order.index(anchor)
    for k, x in enumerate(ids):
        order.insert(i + 1 + k, x)


def insert_before(anchor, ids):
    i = order.index(anchor)
    for k, x in enumerate(ids):
        order.insert(i + k, x)


insert_after("P34.44b", ["P34.45"])
insert_before("P36.12", ["P36.74"])
insert_after("P36.2", ["P36.76", "P36.77", "P36.78"])
insert_before("P36.31", ["P36.79"])
insert_after("P36.42b", ["P36.75"])
insert_after("P37.8", ["P37.71"])
insert_after("P37.12", ["P37.70"])
insert_after("P37.18", ["P37.72"])
insert_after("P37.53", ["P37.69a", "P37.69b"])
all_by = dict(by)
all_by.update(NEW)
new_chain = [all_by[i] for i in order]
for n, r in enumerate(new_chain, start=201):
    r["row"] = str(n)
# keep the gate texts consistent for moved/new rows (11A list etc.)
for r in new_chain:
    if r["id"] in NEW:
        continue
out = new_chain + [r for r in other if r["id"] != "P35.49"] + OPS_NEW + [REVIEW, by["P35.49"]]
# re-run the OM-20 rewrite for P34.45 (sub_round changed before rewriting, so already 11A) - nothing to do
with F.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
print("rows written", len(out), "chain", len(new_chain))
