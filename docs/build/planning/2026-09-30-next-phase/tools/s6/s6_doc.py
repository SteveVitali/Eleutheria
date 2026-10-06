"""S6: assemble the canonical NEXT_PHASE_PLAN.md from the S4c revision + the GATE-P answers.

Usage: python3 s6_doc.py <S6 timestamp from date -u>
"""
import pathlib
import sys

SP = pathlib.Path(__file__).resolve().parent
PARTS = SP / "doc_parts"
PD = pathlib.Path("/Users/stevenvitali/Eleutheria-next-phase/docs/build/planning/2026-09-30-next-phase")
TS = sys.argv[1]
src = (SP / "orig" / "NEXT_PHASE_PLAN.md").read_text()


def part(name):
    return (PARTS / name).read_text()


def between(text, start, end, new):
    i = text.index(start)
    j = text.index(end, i)
    assert text.count(start) == 1, start
    return text[:i] + new + text[j:]


def sub(text, old, new, n=1):
    c = text.count(old)
    assert c == n, (c, old[:80])
    return text.replace(old, new)


s = src
# ---------------------------------------------------------------- header + §0
s = between(s, "# SIG Round 11 — the next-phase plan", "## 1. Brief and authority", part("header.md"))

# ---------------------------------------------------------------- §1
s = sub(s, "| OM-17 digests (traced **GM-1**, §9.5); S5 is collected one line at a time (§4.6; COV-17) |",
        "| OM-17 digests (traced **GM-1**, §9.5); S5 was collected interactively in 23 rounds (§4.7; COV-17) |")
s = sub(s, "Landing text: D3 §1 (agent-drafted;\nconfirmed or edited at S5 via C-4).",
        "Landing text: D3 §1 (agent-drafted);\nthe tagline ratified at C-4 is *\"Public surveillance, traced to the documents.\"*, and the rest of K14 §2.1's copy is\nconfirmed verbatim in copy batch #1 (B-2).")
s = between(s, "### 1.3 Authority chain and gates", "---\n\n## 2. Baseline", part("s13.md"))

# ---------------------------------------------------------------- §2.3
s = sub(s, "| F-096 (RI-05) | `/visual-language/` asserts fixture facts about real named agencies and a vendor | A-0.3 now (removal-only), else P34.17 |",
        "| F-096 (RI-05) | `/visual-language/` asserts fixture facts about real named agencies and a vendor | P34.17 republish #1 (A-0.3 = wait; unresolved, operator-deferred until then) |")
s = sub(s, "| A-0.1–A-0.3 now (removal-only), else P34.18 → P34.21 (scope widened, §5.1) |",
        "| P34.18 (repo tip, ids) → P34.21b (bucket tree first leg, republish #2); A-0 = wait, so unresolved and operator-deferred until then (scope widened, §5.1) |")
s = sub(s, "| F-01 | backups were off; restore never drilled at scale (mitigated by Track 0.1) | P34.6 (+ P34.3) |",
        "| F-01 | backups were off; restore never drilled at scale (mitigated by Track 0.1; no drill before Round 11 — A-1) | P34.6 (+ P34.3), early 11A |")

# ---------------------------------------------------------------- §3
s = sub(s, "| P16 operator identity | **alias first** (C-8 default): no request needing a contact string is sent until the `contact@` alias exists or the operator answers C-8; the need is stopped and recorded. Agent commit authorship is A-21 | connector config review; OM-01 trailer check |",
        "| P16 operator identity | **alias first** (C-8, ratified): no request needing a contact string (EDGAR, 511/QLD/NSW key sign-ups) is sent until the `contact@` alias exists; the need is stopped and recorded. Commits keep the operator's name as author (A-21), so the harness/model trailer is the only harness record | connector config review; OM-01 trailer check in CI |")
s = sub(s, "| (new) autonomy | **OM-20** + OM-10 + OM-18 | GATE packets list exact row ids |",
        "| (new) autonomy | **OM-20** (ratified; 11A list approved at GATE-P) + OM-10 + OM-18; A-15 pause rules | GATE packets list exact row ids |")
s = sub(s, "OM-01 one harness + model per round, recorded in a `harness:` key and every run ledger; switches only at a boundary; **every agent commit carries a trailer naming the harness and model, and a G-check fails a Round-11 PR with an untrailered agent commit** (B5 OM-01 verbatim; TS-11) ·",
        "OM-01 one harness + model per round — **Devin Desktop, `swe-2-high`** (A-15) — recorded in a `harness:` key, CURRENT STATE and every run ledger; switches only at a boundary; **every agent commit carries a trailer naming the harness and model, and a G-check fails a Round-11 PR with an untrailered agent commit** (B5 OM-01 verbatim; TS-11; required because commits keep the operator's name as author, A-21) ·")
s = sub(s, "**OM-20 (new; S4c wording) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the operator *may*\npre-authorise named production mutations of the next sub-round: exact row ids, each contract's mutation, restore point,\nexpiry at the next GATE. **Nothing is pre-authorised on silence** (S5-1/S5-3 defaults; A-15 does not carry OM-20). **Never",
        "**OM-20 (S4c wording; ratified at GATE-P, S5-1) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the\noperator *may* pre-authorise named production mutations of the next sub-round: exact row ids, each contract's mutation,\nrestore point, expiry at the next GATE. **Nothing is pre-authorised on silence.** **The 11A list was approved at GATE-P\n(S5-3, 2026-10-01T04:28:49Z) verbatim plus P34.45's ER re-run, expiring at GATE-G4:** P34.3, P34.4, P34.5, P34.6 (drill\nclone), P34.21a (attribution backfill), P34.24b (clone rehearsal), P34.40 (dark LB/nginx), P34.42a/b (IAM), P34.43\n(execution host + logins), P34.44b (nightly quality job), P34.49 (Part VIII sealing), P34.45 (ER re-run; A-20 = a). **Never")
s = sub(s, "first, and is void on any ratchet regression, any Part VIII screen change or any new source (TS-13).",
        "first, and is void on any ratchet regression, any Part VIII screen change or any new source (TS-13); it is renewed at each\nsub-round GATE and never by `continue`. **A-20 = a:** a structural spine write may change a live-spine API answer before\nHG-11, disclosed by the basis label on every response and a `/status/` notice; it still needs its OM-20 listing or an\nin-ticket go.")
s = sub(s, "(P35.61); **any capture run or archive write touching a Part VIII-screened family** (P37.16a/b, P37.36); irreversible\nexternal deposits (P37.55); the Wave-C tier bump; any spend above $300/mo.",
        "(P35.61); **any capture run or archive write touching a Part VIII-screened family** (P37.16a/b, P37.36); irreversible\nexternal deposits (P37.55); the Wave-C tier bump; any spend above $300/mo; **any WV-06 true deletion** (P37.71).")
s = between(s, "### 3.4 Constraints the operator fixed (not re-asked)", "---\n\n## 4. Decisions",
            "### 3.4 Constraints the operator fixed (not re-asked)\n\n"
            "≤ $300/mo **infrastructure** without an explicit go on a shown trade-off (U-008; A-2: agent usage is reported, not\n"
            "capped, with a pause at any usage-limit event) · no humans besides the operator (U-008) · no contact outside the\n"
            "project: no outreach, recruiting, records-request sending or contribution-back posting (U-011) · do not block on\n"
            "counsel; no text may imply counsel exists (U-013; the counsel clauses are waived, WV-07) · agents never merge,\n"
            "retarget, tag or push `main` (§7.1) · alerts route to the operator's address · the public dispute and intake contact\n"
            "is the operator's address until the `contact@` alias exists (Q-29, WV-05; revisited at GATE-ANNOUNCE, TS-21) · no\n"
            "response time is promised (B-8) · publication is never pre-authorised; a live-API answer may change before HG-11 only\n"
            "with its basis label and the `/status/` notice (A-20) · Devin Desktop executes the round; Claude Code reviews it\n"
            "afterwards (A-15).\n\n")

# ---------------------------------------------------------------- §4
s = between(s, "## 4. Decisions: ratified so far, and what S5 must decide", "## 5. Themes", part("s4.md"))

# ---------------------------------------------------------------- §5 intro
s = sub(s, "Runs per theme are chain-row totals from the post-split `data/round11_plan.csv` mapped to S1a's `theme` column (275.5 in\nall after S4c: UX core 62.0 · transparency 29.0 · sources 28.5 · data correctness 24.5 · release/ops 23.5 · safety and\nhonesty 20.0 · PLAN contract authoring 20.0 · Round-10 activation 19.0 · UX explore 17.5 · memory truth 11.5 ·\nacceptance/tail rows 8.0 · debt 5.5 · governance 4.5 · CI 2.0). The row/run counts in the §5.x headings below are S3's\npre-split figures, kept for traceability; the CSV is authoritative.",
        "Runs per theme are chain-row totals from the post-S6 `data/round11_plan.csv` mapped to S1a's `theme` column (285.5 in\nall after S6: UX core 62.5 · sources 36.5 · transparency 29.0 · data correctness 24.0 · release/ops 23.5 · safety and\nhonesty 20.0 · PLAN contract authoring 20.0 · Round-10 activation 19.0 · UX explore 18.0 · memory truth 12.0 ·\nacceptance/tail rows 8.0 · governance 5.5 · debt 5.5 · CI 2.0). The row/run counts in the §5.x headings below are S3's\npre-split figures, kept for traceability (§5.5 and §5.10 give S6's); the CSV is authoritative.")

# ---------------------------------------------------------------- §5.1
s = sub(s, "W0 copy P34.11–15\n  and the P34.19 withdrawal → **republish #1** P34.17 → handle re-key P34.18 + evidence empty-state truth P34.20 →\n  **attribution re-export + publish-time attribution gate + republish #2** P34.21a/b (hosted backfill ≥ 2026-10-13T12:00Z).",
        "W0 copy P34.11–15\n  and the P34.19 express-terms disclosure (A-8: no withdrawal) → **republish #1** P34.17 (also removes `/visual-language/`\n  and the handle-bearing pages, A-0.3) → handle re-key incl. the repo-tip strings P34.18 + evidence empty-state truth\n  P34.20 → **attribution re-export + publish-time attribution gate + bucket-tree access removal + republish #2**\n  P34.21a/b (the bucket leg first; hosted backfill ≥ 2026-10-13T12:00Z).")
s = sub(s, "- **A-0, removal-only now (TS-04, TS-12).** If the operator answers A-0 = a, the planning orchestrator runs each member\n  as a Track-0 action with its own go before Round 11 starts: A-0.1 repo-tip PR (non-id registry text; the operator\n  merges); A-0.2 anonymous read of the `sig-public` 09-27 tree removed (prefixes the live site fetches excluded after a\n  read-only listing) + tombstone note; A-0.3 `/visual-language/` and handle-bearing pages removed. If unanswered,\n  nothing is removed now and the exposure is recorded as **unresolved** until P34.17/P34.18/P34.21.",
        "- **A-0 answered \"wait\" (03:41:19Z; TS-04, TS-12).** No Track-0 action ran. The exposures are recorded as **unresolved,\n  operator-deferred** (not accepted) and owned by early-11A tickets: A-0.1 → P34.18 removes the 41 e-mail-shaped owner\n  strings and handle tokens from the registry's non-id text (on the r11 branch at once; on public `main` only when the\n  operator merges, OP-08); A-0.2 → P34.21b's first leg removes anonymous read/list of the `sig-public` 09-27 tree\n  (prefixes the live site fetches excluded after a read-only listing; tombstone note), on its own go and allowed inside\n  AR-3 outside 03:00–10:00Z; A-0.3 → P34.17's republish #1 removes `/visual-language/` and the handle-bearing pages\n  (N-6). A-0.4 = accept and disclose: P34.18's correction note discloses the retained git history.")
s = sub(s, "| R1.2 | every \"one-click dispute\" / \"anonymous\" promise removed; dispute page names the operator's address | F-03 (S0), F-098 | operator-confirmed dispute notice; response times only if OD-08 is confirmed |",
        "| R1.2 | every \"one-click dispute\" / \"anonymous\" promise removed; dispute page names the operator's address, promises no response time (B-8) and says senders disclose their address (WV-05) | F-03 (S0), F-098 | operator-confirmed dispute notice (copy batch #1) |")
s = sub(s, "| R1.3 | `/visual-language/` fixture facts removed (if A-0.3 did not already) | F-096 (S0) | none |",
        "| R1.3 | `/visual-language/` fixture facts removed (A-0.3 = wait for this republish) | F-096 (S0) | none |")
s = sub(s, "| R1.8 | pages and list entries of the P34.19 withdrawn sources removed (≈ 8,088 rows with the TxDOT restriction) | J4 NEW-1 | N-3 |",
        "| R1.8 | ~~withdrawn sources removed~~ — **dropped (A-8 = keep all)**: the express-terms sources' pages and list entries show their captured terms and the operator-accepted basis instead (P34.19, ADR-183) | J4 NEW-1, F-403 | disclosure text (copy batch #1) |")
s = sub(s, "| R1.10 | `/status/` notice for what stays wrong until P34.46 | F-130 (S0), F-189 (API terms) | N-7 |",
        "| R1.10 | `/status/` notice for what stays wrong until P34.46, and the A-20 notice that live-API answers may change before the next Class S release | F-130 (S0), F-189 (API terms); A-20 | N-7 + the A-20 notice (copy batch #1) |\n  | R1.11 | every page whose URL or title embeds a personal handle removed until P34.21b republishes it re-keyed (A-0.3) | F-097, F-131 (S0) | N-6 |")
s = sub(s, "| A-0.2 removes anonymous access to the misattributed downloads; republish #1 replaces wrong per-source credits with N-4 |",
        "| P34.21b's first leg removes anonymous access to the misattributed downloads; republish #1 replaces wrong per-source credits with N-4 |")
s = sub(s, "| personal handles in ids, tiles and one `camera_operator` value (F-097/F-131 S0) | P34.18 → P34.21b (`camera_operator` fully in P35.26) | A-0.1–A-0.3 if answered; else unresolved |",
        "| personal handles in ids, tiles and one `camera_operator` value (F-097/F-131 S0) | P34.18 → P34.21b (`camera_operator` fully in P35.26) | handle-bearing pages removed in republish #1 (R1.11); otherwise unresolved, operator-deferred (A-0) |")
s = sub(s, "| the 5,267 forbidden-terms/NC/ND/demo rows in downloads and tiles | P34.21b re-export | pages/list entries leave in republish #1 (R1.8); A-0.2 covers downloads |",
        "| the ≈8,088 express-terms rows in downloads and tiles | stay (A-8) | captured terms + the operator-accepted basis disclosed on pages (P34.17) and in every file's ATTRIBUTION (P34.21b) |")
s = sub(s, "SIG-PUB-008 and SIG-UI-042 are waiver candidates (A-23), never silently amended.\n  See §6.",
        "SIG-PUB-008's second-reviewer role and SIG-UI-042's release block are WAIVED by ADR (WV-03, WV-04).\n  See §6.")
s = sub(s, "A test alert has been received;\n  the $300 budget alert and billing export are live.",
        "A test alert has been received; the\n  TLS-expiry alert, the $300 budget alert, the billing export and a drilled restore exist (the deferred A-1/A-2a items).")

# ---------------------------------------------------------------- §5.2
s = sub(s, "  - *Skills (out of repo, operator-applied):* B6's 25 proposals; Tier A before Stage B, Tier B-must before row 201\n    (OP-01…OP-04; A-14).",
        "  - *Skills (out of repo):* B6's 25 proposals, all adopted (A-14 \"All, staged\"): Tier A at T0, Tier B-must before row\n    201, the rest early in the round (OP-01…OP-04). They reach Devin CLI through `~/.claude/skills` (verified); Devin\n    Desktop's skill path is verified at T6.")

# ---------------------------------------------------------------- §5.4
s = sub(s, "agent review in two blind contexts, labelled and never gating (P35.48); a disclosed, non-independent,\n  blind-first **maintainer check (OPCHECK)** by the operator per Class-S release (P35.49; OP-17; B-31); independent human\n  evaluation **not planned** — owed under T-EVAL-IND (§11). The honest evaluation posture lands as code in 11A and its ER\n  re-run runs in early 11B after P35.57 (A-20); the public posture text ships in republish #1 only in its past-tense form,\n  and the present-tense merge sentence ships with P35.63 (TS-03, TS-14).",
        "agent review in two blind contexts, labelled and never gating (P35.48); **no maintainer check** — the operator chose\n  none (B-31), so every Class-S readout and `/quality/` say \"no human check performed\" (P35.49, OP-16 and OP-17 dropped);\n  independent human evaluation **not planned** — owed under T-EVAL-IND (§11). The honest evaluation posture and its ER\n  re-run land in 11A (P34.45, on the S5-3 OM-20 list; A-20 = a: its live-API effect is labelled); the public posture text\n  ships in republish #1 only in its past-tense form, and the present-tense merge sentence ships with P35.63 (TS-03, TS-14).")
s = sub(s, "dossier counts ≤ 1.02× lineage roots (or ranged intervals if A-6 defaults) [up to 2.25×]",
        "dossier counts ≤ 1.02× lineage roots [up to 2.25×]")
s = sub(s, "**M-1b: under A-6 = a, a sampled lower\n  bound per declared namespace is reported as measured (no certification figure is claimed — \"0.98\" is L3's forbidden\n  certification number); under A-6's default nothing is collapsed, so M-1b is \"not attempted (default A-6)\"** (TS-10);\n  `/quality/` live with every check, failing and ratchet checks shown (B-31; under Q-L3-5's default it is built, not\n  published).",
        "**M-1b: A-6 = a, so a sampled lower\n  bound per declared namespace is reported as measured (no certification figure is claimed — \"0.98\" is L3's forbidden\n  certification number)** (TS-10); `/quality/` live with every check, failing and ratchet checks shown, stating \"no human\n  check performed\" (B-31).")

# ---------------------------------------------------------------- §5.5 (replace whole)
s = between(s, "### 5.5 Sources and coverage — Stream I", "### 5.6 Transparency and export", part("s55.md"))

# ---------------------------------------------------------------- §5.6–§5.9
s = sub(s, "`/data-freshness/`\n  301s to `/sources/`. The repo is public, so commit hashes are shown (C-6).",
        "`/data-freshness/`\n  301s to `/sources/`. The repo is public, so commit hashes are shown (C-6). B-19 was answered \"yes\" on every member;\n  the express-terms rows are not withdrawn (D-J3-5 = b): each file's ATTRIBUTION states their captured terms and the\n  operator-accepted basis (ADR-183).")
s = sub(s, "**Withdrawn\n  rather than fixed this round** (the operator accepts or rejects the list at C-12):",
        "**Withdrawn\n  rather than fixed this round** (accepted by the operator at C-12, 05:03:05Z):")
s = sub(s, "search relevance is reported as \"held-out ≥ 80 % top-3\n  on an **agent-authored** held-out set\" unless the operator writes it (OP-21; TS-20);",
        "search relevance is reported as \"held-out ≥ 80 % top-3\n  on an **agent-authored held-out set; not independent**\" (B-28; written by P36.79 and sealed from the tuning contexts;\n  TS-20);")
s = sub(s, "Class R (standing go, routine) vs **Class S**",
        "Class R (the standing go in the operator's adopted words, B-9, renewed at each sub-round GATE) vs **Class S**")
s = sub(s, "- **Acceptance.** 11A exit 5: G2 step 1 live, after the 10-10 replay was read back. 11B opens with **P35.57** (API\n  release parity, its own go collected at G4) so no 11B structural spine write changes a public API answer before HG-11\n  (A-20 = b); 11B exit 1: P35.63 promoted (§5.8). Research dossiers become public only after live captures (B-7), and those\n  captures (P37.16a/b) require the per-family Part VIII sign and depend on P35.31's capture-tier fix (TS-07).",
        "- **Acceptance.** 11A exit 5: G2 step 1 live, after the 10-10 replay was read back. **P35.57** (API release parity, its\n  own go collected at G4) stays at the head of 11B as an improvement; under A-20 = a the 11B structural spine writes may\n  change live API answers before HG-11, disclosed by the basis label and the `/status/` notice; 11B exit 1: P35.63 promoted\n  (§5.8). Research dossiers become public only after live captures (B-7); those captures (P37.16a/b) are cleared per\n  family by the agent's Part VIII screen, disclosed as \"cleared by agent screen, no human review\" (B-42), and depend on\n  P35.31's capture-tier fix (TS-07).")

# ---------------------------------------------------------------- §5.10 (replace whole)
s = between(s, "### 5.10 Governance and records", "### 5.11 Engineering debt", part("s510.md"))

# ---------------------------------------------------------------- §6.2 note, §6.3–§6.5, §6.6
s = sub(s, "Every append is an append-only `spec_src` change rebuilt by\n`BUILD.sh`, from this ratified plan (OM-03).",
        "Every append is an append-only `spec_src` change rebuilt by\n`BUILD.sh`, from this ratified plan (OM-03). SIG-CONF-D10 (maintainer checks) is written as \"disclosed when\nperformed\"; Round 11 performs none (B-31), and SIG-CONF-D02 segregates the agent labels it does produce.")
s = between(s, "### 6.3 Amended existing ids and sections", "### 6.6 Coverage re-verdicts T4 applies", part("s63_65.md"))
s = sub(s, "GOV-022, EVID-019 → MET-ENGINEERED; GOV-013/015 → MISSING;",
        "GOV-022, EVID-019 → MET-ENGINEERED; GOV-013/015 → WAIVED(ADR-165/164) (WV-01/02);")

# ---------------------------------------------------------------- §7, §8 (replace whole)
s = between(s, "## 7. ADR list", "## 8. Ticket plan", part("s7.md"))
s = between(s, "## 8. Ticket plan", "## 9. Obligation mapping", part("s8.md"))

# ---------------------------------------------------------------- §9
s = sub(s, "S4c changes (COV-02, COV-06, COV-07): F-184 operator-action(OP-11) → ticket(R11-SAFE-06 = P35.38); F-27 SEED-18 →\nSEED-02 (+ P34.9 link); D-SOURCES.8-1 ticket(P36.2) → decision(E4-R4a), hence operator-action 8 → 7 and decision 41 → 42.",
        "S4c changes (COV-02, COV-06, COV-07): F-184 operator-action(OP-11) → ticket(R11-SAFE-06 = P35.38); F-27 SEED-18 →\nSEED-02 (+ P34.9 link); D-SOURCES.8-1 ticket(P36.2) → decision(E4-R4a), hence operator-action 8 → 7 and decision 41 → 42.\n**S6 changed no universe disposition** (S6 writes only the plan and the three data CSVs): the 42 `decision(…)` items and the\n41 decision-dependent items now have answers in `data/decision_catalog.csv` (`operator_answer`), and T4 re-dispositions\nthem (e.g. D-SOURCES.7-2/8-2 → P37.12/P37.70, D-SOURCES.2-2 → P36.77, D-P30.2b-1 → LATER-01). Dropped catalog units stay in\n`data/ticket_catalog.csv` marked `dropped (S6: …)` so every reference resolves; the S1b checker stays green (§9 heading).")
s = sub(s, "| **ticket (9)** | D-FEDERAL.1-1 → P37.11 · D-P32.10a-1, D-P32.16a-1 → P34.24 · D-P32.16-1 → P37.59 (conditional; Q-27/B-8) · D-R10-MEMORY-1 → P34.30 (split, option C) · D-R10-SOURCES-1 → P34.38 (+ P37.16) · D-SOURCES.7-1, D-SOURCES.9-1, D-SOURCES.9-4 → P36.2 (rights flip/decline batch; E4 R3, R5, R6 lines; now in 11C) · **D-P32.16-1 → P37.59 is expected to remain OPEN in Round 11** under B-8's recommended answer and U-008 (no named moderation owner or reviewer rotation; COV-15) |",
        "| **ticket (9)** | D-FEDERAL.1-1 → P37.11 · D-P32.10a-1, D-P32.16a-1 → P34.24 · D-P32.16-1 → P37.59 (conditional; B-8 = e-mail-only) · D-R10-MEMORY-1 → P34.30 (split, option C) · D-R10-SOURCES-1 → P34.38 (+ P37.16) · D-SOURCES.7-1, D-SOURCES.9-1, D-SOURCES.9-4 → P36.2 (E4-R3 flip, R5 flip, R6a capture / R6b close; 11C) · **D-P32.16-1 → P37.59 remains OPEN in Round 11** (B-8: intake stays dark; U-008; COV-15) |")
s = sub(s, "| **live-return-pass (9)** | D-P21.5-1 (PARTIAL) → P37.55 + OP-19 (closes only if B-6/Q-E2-23, B-21 and A-0.4 are answered; under their defaults it stays PARTIAL — COV-15) ·",
        "| **live-return-pass (9)** | D-P21.5-1 (PARTIAL) → P37.55 + OP-19 (B-6/Q-E2-23 = a, B-21 = yes and A-0.4 = a were all answered, so it can close in 11D) ·")
s = sub(s, "| **decision (7)** | **D-SOURCES.8-1 (PARTIAL) → E4-R4a (B-41: R4a–c capture terms, not flipped — consistent with B-34 and US-first; the three non-US rows wait for trigger \"operator expands non-US coverage\", LATER-09/10; Bellevue declined under A-9; COV-07)** · D-JURIS.2-1 (PARTIAL) → E4-R1 (B-41: close, eID leg WONTFIX) · D-P30.2b-1 → B-18 (merged into the maintainer check, P35.49; else OP-16) · D-P32.3-1 → B-18 (folded into A-10 + P37.46; else OP-15) · D-SOURCES.2-2 → E4-R2a (B-41: decline) · D-SOURCES.7-2 → B-18 (register US 511 keys, OP-13 → P37.12) · D-SOURCES.9-2 → E4-S2 (B-43: WONTFIX) |",
        "| **decision (7) — all answered at GATE-P** | D-SOURCES.8-1 (PARTIAL) → E4-R4a…d (B-41: R4a OGL-Edmonton after capture, R4b flip, R4c QLDTraffic API → P37.70, R4d decline under A-9; non-US kept, S5-4) · D-JURIS.2-1 (PARTIAL) → E4-R1 (close, eID leg WONTFIX) · D-P30.2b-1 → B-18 fold into the maintainer check, **which B-31 removed: stays OPEN, non-blocking, T-EVAL-IND (LATER-01)** · D-P32.3-1 → B-18 (folded into ADR-159's auto-allow + P37.46; no operator review) · D-SOURCES.2-2 → E4-R2a **flip `documentcloud`** (P36.77) + R2b decline · D-SOURCES.7-2 → B-18 (US 511 keys, OP-13 → P37.12) · D-SOURCES.9-2 → E4-S2 (WONTFIX) |")
s = sub(s, "109 land on a seed or 11A/11B unit (108 tickets + F-522's live-return-pass); 3 rest on S5 decisions and **stay open under\ntheir defaults** (F-31 → A-4; F-191 → C-3; F-386 → A-3, with TX-11 at P35.5);",
        "109 land on a seed or 11A/11B unit (108 tickets + F-522's live-return-pass); 3 rested on S5 decisions, **now answered**\n(F-31 → A-4 + the seven A-23 waivers, closed by ADR; F-191 → C-3, recorded; F-386 → A-3 = yes, fixed by P35.5 + P36.50);")
s = sub(s, "| finding(s) | sev. | owner (S0/S1 unit) | fix kind | final fixing row | default that leaves it open |",
        "| finding(s) | sev. | owner (S0/S1 unit) | fix kind | final fixing row | GATE-P answer that shapes it |")
s = sub(s, "| F-097, F-131 (handles) | S0 | P34.18 → P34.21b; A-0 | fixed live in 11A (scope widened); interim A-0 | P34.21b (+ P35.26 for the `camera_operator` value) | A-0 → removal waits to ≥ 10-13 |",
        "| F-097, F-131 (handles) | S0 | P34.18 → P34.21b | fixed live in 11A (scope widened); handle pages leave in republish #1 | P34.21b (+ P35.26 for the `camera_operator` value) | A-0 = wait: unresolved, operator-deferred until P34.17/P34.18/P34.21b |")
s = sub(s, "| F-387 (misattribution) | S0 | P34.21a/b | fixed in republish #2; interim N-4 + A-0.2 | P34.21b | A-0 → downloads stay readable to ≥ 10-13 |",
        "| F-387 (misattribution) | S0 | P34.21a/b | fixed in republish #2; interim N-4 + P34.21b's bucket leg | P34.21b | A-0.2 = wait: the 09-27 downloads stay readable until P34.21b's first leg |")
s = sub(s, "| F-07, F-099, F-390, F-399 (permalinks) | S1 | P35.42 (TX-13a) + P34.11 wording | **interim** (honest wording, release id on every page) | P36.66b (11C) | **B-19/D-J3-6 → snapshots never published, so links never pin** |",
        "| F-07, F-099, F-390, F-399 (permalinks) | S1 | P35.42 (TX-13a) + P34.11 wording | **interim** (honest wording, release id on every page) | P36.66b (11C) | D-J3-6 = yes: `/s/<pub>/` snapshots pin them |")
s = sub(s, "| F-103 (bulk/API/terms unlinked) | S1 | P34.13 | partial (terms linked) | P36.50 (11C) | **A-3 → no public download links** |",
        "| F-103 (bulk/API/terms unlinked) | S1 | P34.13 | partial (terms linked) | P36.50 (11C) | A-3 = yes: download links from the R2 host |")
s = sub(s, "| F-386 (bulk release unreachable) | S1 | decision D-J3-4 (A-3) | default-dependent | P35.5 + P36.50 | **A-3 → stays unreachable** |",
        "| F-386 (bulk release unreachable) | S1 | decision D-J3-4 (A-3) | answered a | P35.5 + P36.50 | A-3 = yes (R2 + $50 egress ceiling) |")
s = sub(s, "| F-452; F-106/F-420 labels | S1 | P34.26; P35.30 | partial (non-organisation labels fixed) | P36.41–P36.42b, P37.22–28 | **A-10 → all organisations withheld** |",
        "| F-452; F-106/F-420 labels | S1 | P34.26; P35.30 | partial (non-organisation labels fixed) | P36.41–P36.42b, P37.22–28 | A-10 = b + c: registry-matched organisations labelled; the rest \"not yet reviewed\" |")
s = sub(s, "| F-31 (spec contradicts decisions) | S1 | decision Q-7 (A-4) | default-dependent | SEED-11/12 | **A-4/A-23 → stays open (owed, listed at GATE-ANNOUNCE)** |",
        "| F-31 (spec contradicts decisions) | S1 | decision Q-7 (A-4) | answered a + seven waivers | SEED-11/12 | A-4 + A-23: closed by the waiver ADRs; S6's flagged contradictions (R-18, R-27) carried |")
s = sub(s, "| F-191 (backward confirmations) | S1 | decision OD-12 (C-3) | default-dependent | SEED-08 | **C-3 → not recorded** |",
        "| F-191 (backward confirmations) | S1 | decision OD-12 (C-3) | answered (sentence adopted) | SEED-08 | C-3 recorded with its 2026-10-01 time |")
s = sub(s, "| F-506, F-507, F-511, F-518…F-521 (L1/L2 correctness) | S1 | P35.24–27, P35.46–47 | pulled forward into 11B; interim P34.44b ratchet | 11B rows | A-6 (no collapse) for F-518/F-519 |",
        "| F-506, F-507, F-511, F-518…F-521 (L1/L2 correctness) | S1 | P35.24–27, P35.46–47 | pulled forward into 11B; interim P34.44b ratchet | 11B rows | A-6 = a: C0–C2 collapse (C2 enabled, B-31) |")
s = sub(s, "| F-512 (inferential tiers auto-written) | S1 | P34.45 (now first in 11B, after P35.57) | fixed in 11B; publication with P35.63 | P35.63 | A-20 = a would let it land in 11A |",
        "| F-512 (inferential tiers auto-written) | S1 | P34.45 (back in 11A; ER re-run on the S5-3 list) | fixed in 11A; publication with P35.63 | P35.63 | A-20 = a: lands in 11A, its live-API effect labelled |")
s = sub(s, "| U-001 | ticket → P36.64 (Home/About; landing text C-4) |",
        "| U-001 | ticket → P36.64 (Home/About; tagline ratified at C-4) |")
s = sub(s, "| U-014 | operator-action → OP-10 (`contact@surveillancegraph.org` alias) |",
        "| U-014 | operator-action → OP-10 (`contact@surveillancegraph.org` alias; alias first, C-8) |")
s = sub(s, "| U-015 | already-done → B7: attribution high-confidence for 477 of the 480 chain commits; the S0 surface \"medium, unknown\"; the model behind `swe-2-high` unknown (TS-17); confirmed or corrected at C-2 |",
        "| U-015 | already-done → B7: attribution high-confidence for 477 of the 480 chain commits; the S0 surface \"medium, unknown\"; the model behind `swe-2-high` unknown (TS-17); confirmed at C-2 (the P31.5→P31.6 hand-over was planned) |")
s = sub(s, "| W2-1 | *\"configure them for ingestion and ingest them into prod\"* | ticket → P35.6–P35.11 (Wave A), P36.1a–P36.12 (Wave B), P37.1–P37.2 (Wave C), P37.54 (Wave D, conditional) |",
        "| W2-1 | *\"configure them for ingestion and ingest them into prod\"* | ticket → P35.6–P35.11 (Wave A), P36.1a–P36.12 + P36.74 (Wave B), P37.1–P37.2 (Wave C), P36.75–78, P37.69a/b, P37.70 and P37.54 (Wave D, in scope) |")
s = sub(s, "| W2-5 | *\"download the raw data\"* | ticket → P37.36 + P36.50; **descoped under B-19/D-J3-1's default (§4.4 row 15)** |",
        "| W2-5 | *\"download the raw data\"* | ticket → P37.36 + P36.50 (D-J3-1 = yes: raw-ok sources after the Part VIII byte screen) |")
s = sub(s, "| W2-6 | *\"see ingestion logs/metrics/timestamps\"* | ticket → P35.32–P35.34, P36.43, P36.46; **descoped under B-19/D-J3-2's default (§4.4 row 16)** |",
        "| W2-6 | *\"see ingestion logs/metrics/timestamps\"* | ticket → P35.32–P35.34, P36.43, P36.46 (D-J3-2 = yes: scrubbed run logs published) |")
s = sub(s, "- **65 candidate groups (694 candidates):** ticket 13 (Waves A–C families), later-phase 43 (LATER-09 long tail, 389\n  candidates), decision 8 (the Wave-D groups, I8-Q5), merged-into 1. Tier 3 (259) is not acquired.\n- **41 decision-dependent items** wait on 24 S1c ids (S1b §4); their final kind is fixed when the operator answers at S5,\n  and T4 records it.",
        "- **65 candidate groups (694 candidates):** ticket 13 (Waves A–C families), later-phase 43 (LATER-09 long tail, 389\n  candidates), decision 8 (the Wave-D groups — I8-Q5 = a, so they become tickets at T4), merged-into 1. Tier 3 (259) is not\n  acquired. With S5-4 the non-US groups that S4c had moved to LATER-09 (ACQ-23a/b) come back into the round (P37.69a/b).\n- **41 decision-dependent items** waited on 24 S1c ids (S1b §4); all 24 were answered at GATE-P, and T4 records each final\n  kind from `data/decision_catalog.csv`'s `operator_answer`.")

# ---------------------------------------------------------------- §10.1, §10.2, §10.4, §10.5
s = sub(s, "**Not done:** restore drill, deletion\nprotection, budget alert, TLS-expiry alert, probe re-roll (A-1/A-2 ask whether any of these run before Round 11).",
        "**Not done:** restore drill, deletion\nprotection, budget alert, TLS-expiry alert, probe re-roll — and none runs before Round 11 (A-1 \"None now; ticket it\", A-2\n\"alert later\"): each is an early-11A ticket, and the gap until then is unresolved, operator-deferred (R-28).")
s = sub(s, "| P34.4 | alerts that reach a human: verify and extend Track 0.5; TLS expiry; `SIG-ALERT` log alert; `sig-probe` re-roll (QA-5); disable the GitHub `reingest` schedule (QA-8) | production write |",
        "| P34.4 | alerts that reach a human: verify and extend Track 0.5; TLS expiry (A-1: not done before the round); `SIG-ALERT` log alert; `sig-probe` re-roll (QA-5); disable the GitHub `reingest` schedule (QA-8) | production write (OM-20, S5-3) |")
s = sub(s, "| P34.5 | cost guard: budget alert at $300, billing export, monthly spend ledger (U-011) | production write (billing admin; OP-12) |",
        "| P34.5 | cost guard: budget alert at $300, billing export, monthly spend ledger incl. Cloudflare/R2 and agent-usage lines (U-011; A-2 \"alert later\") | production write (billing admin; OP-12; OM-20, S5-3) |")
s = sub(s, "| P34.6 | restore drill at scale into an isolated clone with RTO/RPO; restore-point procedure; monthly logical export | production write (separate instance) |",
        "| P34.6 | restore drill at scale into an isolated clone with RTO/RPO; restore-point procedure; monthly logical export (A-1: the drill not done before the round) | production write (separate instance; OM-20, S5-3) |")
s = sub(s, "| P35.1 | scheduler of record + daily live-diff + cron lint + fleet hygiene (79 triggers; cruft jobs) | production write |",
        "| P35.1 | scheduler of record + daily live-diff + cron lint + fleet hygiene (79 triggers; cruft jobs) + the scheduler consolidation into one dispatcher (B-13, −$7/mo); no robots-disallowing host is paused (A-5) | production write |")
s = sub(s, "| P35.5 | zero-egress distribution host; $50/mo egress ceiling + kill switch; R2 Class-B operations ceiling + alert (FEA-18) | production write (R2 via Cloudflare if A-3 = a) |",
        "| P35.5 | zero-egress distribution host; $50/mo egress ceiling + kill switch; R2 Class-B operations ceiling + alert (FEA-18) | production write (R2 via Cloudflare; A-3 = a) |")
s = sub(s, "| P36.13 | API exposure: enforced rate limits (search 30/min) + optional Cloud Armor (+$6) | production write |",
        "| P36.13 | API exposure: enforced rate limits (search 30/min, burst 10); no Cloud Armor now (D-K3-6) | production write |")
s = sub(s, "| P37.15 | scheduled parser canary | production write |",
        "| P37.15 | scheduled parser canary | production write |\n| P36.75, P37.70 | Flock share-list claims (append-only spine write); AU keyed APIs (after the operator's key registration) | production write (OM-20 G5/G6 lists or in-ticket gos) |\n| P37.71 | single-operator true-deletion mechanism (WV-06); executes nothing by itself | code; each use = an operator in-ticket go, never OM-20 |")
s = sub(s, "They need no per-row go **only** if the operator approved, verbatim, an OM-20\nlist naming the row; otherwise each is an in-ticket pause.",
        "They need no per-row go **only** if the operator approved, verbatim, an OM-20\nlist naming the row — for 11A that list was approved at GATE-P (S5-3) — otherwise each is an in-ticket pause.")
s = between(s, "### 10.4 Money", "---\n\n## 11. Human-work plan", part("s104_105.md"))

# ---------------------------------------------------------------- §11 (replace whole)
s = between(s, "## 11. Human-work plan (operator-only)", "## 12. Integration and branch policy", part("s11.md"))

# ---------------------------------------------------------------- §12
s = sub(s, "**Agent commits** carry the harness/model trailer\n  (OM-01, CI-checked) and, if A-21 = a, a distinct agent author identity; pushes use the operator's account.",
        "**Agent commits** carry the harness/model trailer\n  (OM-01, CI-checked) and keep the operator's name as author (A-21 = b, a disclosed risk), so the trailer is the only\n  record of which harness wrote a commit; pushes use the operator's account.")
s = sub(s, "**Integration debt (FEA-17):**\n  by the round's end ≈ 330 stacked PRs (#141–#190 + ≈ 280 Round-11 PRs incl. live-leg PRs);",
        "**Integration debt (FEA-17):**\n  by the round's end ≈ 340 stacked PRs (#141–#190 + ≈ 290 Round-11 PRs incl. live-leg PRs);")
s = sub(s, "An appended correction cannot remove it from the\n  planning branch's history, so the honest options are (OD-27): **(a)** publish as recorded, or **(b)** carry the\n  planning files into `r11/seed` as one new commit with the address replaced, keeping the full planning history in the\n  operator's private backup (OP-23) — a recorded deviation from \"planning commits reach the chain unchanged\". **No\n  default action: the T6 push waits for the answer** (a GATE-B stall, §4.4 S2).",
        "An appended correction cannot remove it from the\n  planning branch's history. **OD-27 = a (GATE-P, 04:39:45Z): publish as recorded** at T6, after the secret,\n  personal-identifier and Part VIII scans; the agent makes a git bundle the operator stores privately (B-16 c, OP-23).\n  Planning commits reach the chain unchanged.")

# ---------------------------------------------------------------- §13
s = between(s, "### 13.2 Round-level success criteria", "## Appendix A", part("s13_15.md"))
s = sub(s, "drafts the GATE packet (agent-drafted, labelled; descoping defaults listed first).",
        "drafts the GATE packet (agent-drafted, labelled; any line with a non-action default listed first).")

# ---------------------------------------------------------------- Appendix A (replace), B (append rows), C (row)
s = between(s, "## Appendix A — Stage-B translation checklist", "## Appendix B", part("appA.md"))
s = sub(s, "| 23 | Appendix B row 9 asked S4 feasibility to confirm the A-16 key work; row 16 asked whether a GATE-G7 is wanted | A-16 = yes adds the CI verification to P34.28 and an operator setup item (LATER-15 closes); no GATE-G7: P38.1a/b is 11D's live-read acceptance and GATE-ACCEPT-R11 follows (no reviewer asked for one) |",
        "| 23 | Appendix B row 9 asked S4 feasibility to confirm the A-16 key work; row 16 asked whether a GATE-G7 is wanted | A-16 = yes adds the CI verification to P34.28 and an operator setup item (LATER-15 closes); no GATE-G7: P38.1a/b is 11D's live-read acceptance and GATE-ACCEPT-R11 follows (no reviewer asked for one) |\n"
        "| 24 | (S6) B-41's \"as listed\" included R2a = decline DocumentCloud while B-39 said fetch it | re-asked in round 18; the operator answered \"Fetch, screened\" (E4-R2a b) |\n"
        "| 25 | (S6) A-8 and A-9 overlap on the 3 live NC rows | round 5's wording: A-8 keeps everything as is; A-9 governs new sources only |\n"
        "| 26 | (S6) B-18 folded D-P30.2b-1 into the maintainer check, which B-31 then removed; Q-25's seat likewise | D-P30.2b-1 stays OPEN, non-blocking (T-EVAL-IND, LATER-01); the operator holds no evaluation seat |\n"
        "| 27 | (S6) the log's A-12 shorthand \"superseding ADR-068/091/097/134\" vs K0 §6 (supersedes ADR-091 §3–4 and ADR-097 §2–3/§6, extends ADR-134, leaves ADR-068 unchanged) | K0 §6's precise clauses kept (the decision is D-K0-1 a, \"supersede the three-island rule\"); flagged for S6r |\n"
        "| 28 | (S6) the interpretation of IT7 says private registrants are \"never stored in public output\"; SIG-PUB-002 forbids storing home addresses and incidental private names in **any** tier | PUB-002 applied: P36.76 redacts before anything is persisted (flagged in `design/S6-ratification-applied.md`) |")
s = sub(s, "| §1, §4.1 | `META_PLAN.md` §7.1; `feedback/OPERATOR_FEEDBACK.md` |",
        "| §1, §4.1 | `META_PLAN.md` §7.1; `feedback/OPERATOR_FEEDBACK.md` |\n| §4.2–§4.7 (and every \"= answer\" in §5–§15) | `feedback/RATIFICATION_LOG.md` (GATE-P; commit `de0b3591`); `data/decision_catalog.csv` (`operator_answer`, `answered_at`); `design/S6-ratification-applied.md` |")
s = sub(s, "| §4.2–§4.5 | `design/S1c-decision-catalog.md` §2–§9; `data/decision_catalog.csv`; S2 §7.3, §11 |",
        "| §4 (the questions as asked) | `design/S1c-decision-catalog.md` §2–§9 and appendix; `data/decision_catalog.csv`; S2 §7.3, §11 |")

# ---------------------------------------------------------------- footer + change notes
s = sub(s, "*End of draft. S3 written 2026-10-01T01:13:07Z → 01:26:35Z; revised at S4c 2026-10-01T02:38:06Z → 2026-10-01T02:55:12Z (`date -u`).\nThe three S4 reviews are closed in `reviews/REVIEW_CLOSURE.md`. Next: S5 / GATE-P (two sittings, one line at a time).*\n",
        "## Change notes\n\n"
        "| revision | when (`date -u`) | what changed |\n|---|---|---|\n"
        "| S3 draft | 2026-10-01T01:13:07Z → 01:26:35Z | first synthesis (committed `c3e37654`) |\n"
        "| S4c revision | 2026-10-01T02:38:06Z → 02:55:12Z | closed the three S4 reviews (`reviews/REVIEW_CLOSURE.md`; committed `e5936f96`) |\n"
        "| GATE-P | 2026-10-01T03:41:19Z → 05:03:05Z | 99 lines answered in 23 rounds (`feedback/RATIFICATION_LOG.md`; committed `de0b3591`) |\n"
        f"| **S6 revision** | {TS} | status → CANONICAL; §4 rewritten as the ratified decisions (Parts A, S5, B, C, D2) with the 27 deviations and the recording gaps; §0, §1.3, §3, §5.1/5.2/5.4/5.5/5.6/5.7/5.9/5.10, §6.3–§6.5, §7 (30 SEED-11 ADRs: +179–185), §8 (309 rows, 285.5 runs, 256k sizing, oversized rows), §9, §10 (money, ops), §11 (operator load), §12, §13 (criteria no longer conditional; post-round review; GATE-ANNOUNCE), §14 (R-18…R-31), §15 and Appendix A updated; Appendix B rows 24–28; CSVs: 11 chain rows + OP-25, OP-26 and REVIEW-R11 added, 1 chain row dropped (P35.49), 6 operator rows dropped, OP-18 done, 4 later rows moved in, P34.45 moved to 11A, every operator_gate default replaced by its answer; `decision_catalog.csv` gains `operator_answer` + `answered_at` for all 346 ids. Details: `design/S6-ratification-applied.md` |\n\n"
        f"*Canonical for Round 11. S3 written 2026-10-01T01:13:07Z → 01:26:35Z; revised at S4c 2026-10-01T02:38:06Z → 02:55:12Z;\nratified at GATE-P 2026-10-01T05:03:05Z; applied at S6 {TS} (`date -u`). Next: S6r (one fresh-context consistency\nreview), then Stage B (T0–T6).*\n")


# ---------------------------------------------------------------- small stale-phrase fixes
s = sub(s, "- **Design (K13; K0 page types if A-12 = a).**", "- **Design (K13; K0 page types, A-12 = a).**")
s = sub(s, "owner is an interim mitigation, depends on a default, or whose final fix lands later.",
        "owner is an interim mitigation, depends on a GATE-P answer, or whose final fix lands later.")
s = sub(s, "| fixed without a purchase | P35.38 | — (OP-11 optional) |", "| fixed without a purchase | P35.38 | B-6: no purchase; OP-11 dropped |")


s = sub(s, "ING-GO; HG-03 flips; **any hosted sqitch change", "ING-GO; HG-03 flips (each executed by the operator, OP-26); **any hosted sqitch change")
s = sub(s, "production read that contradicts a record voids it for the affected rows. Without OM-20 the 58 OM-20 rows become\nin-ticket pauses (§8.1).",
        "production read that contradicts a record voids it for the affected rows. A row not on an approved list pauses in-ticket\n(§8.1: 57 OM-20 rows, 13 of them pre-authorised for 11A).")
s = sub(s, "| R1.8 | ~~withdrawn sources removed~~ — **dropped (A-8 = keep all)**:", "| R1.8 | (S4c: withdrawn sources removed) — **dropped, A-8 = keep all**:")


s = sub(s, "`tools/check_dispositions.py` → structurally valid, 0 errors after S4c — it checks shape, not truth, F-27)",
        "`tools/check_dispositions.py` → structurally valid, 0 errors after S4c and again after S6 — it checks shape, not truth, F-27)")

s = s.replace("@@S6_TS@@", TS)
assert "@@" not in s
(PD / "NEXT_PHASE_PLAN.md").write_text(s)
print("written", len(s.splitlines()), "lines")
