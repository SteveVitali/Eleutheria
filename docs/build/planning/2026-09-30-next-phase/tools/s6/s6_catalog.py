"""S6: fold the GATE-P answers into data/ticket_catalog.csv (new units, dropped/moved units, re-scopes)."""
import csv
import pathlib

PD = pathlib.Path("/Users/stevenvitali/Eleutheria-next-phase/docs/build/planning/2026-09-30-next-phase")
F = PD / "data" / "ticket_catalog.csv"
rows = list(csv.DictReader(F.open()))
FIELDS = list(rows[0].keys())
by = {r["cat_id"]: r for r in rows}
ENV = ("public, unauthenticated pages only; no logins, API keys or access-control circumvention; rate-limited; "
       "robots per GL-GATE-08; terms text captured verbatim; exposure disclosed; Part VIII screen on every byte")


def add(r, col, text):
    r[col] = (r[col] + " | " if r[col] else "") + "S6: " + text


def drop(cid, why):
    r = by[cid]
    r["where_it_must_land"] = f"dropped (S6: {why})"
    r["est_runs"] = "0"
    r["monthly_cost_delta_usd"] = "0"


# ---- dropped / done / moved
drop("R11-CONF-11", "B-31 'No maintainer check' — no OPCHECK protocol; D-P30.2b-1 stays OPEN under T-EVAL-IND")
drop("OP-11", "B-6 'Move UA, don't buy domain' — sig-project.org not purchased; residual squatting risk recorded")
drop("OP-14", "A-10 'Auto-allow + absence only' — no operator top-50 review")
drop("OP-15", "D-P32.3-1 folds into the A-10 auto-allow ADR + R11-CONF-13; no operator review")
drop("OP-16", "D-P30.2b-1 has no fold target after B-31; stays OPEN, non-blocking (T-EVAL-IND, LATER-01)")
drop("OP-17", "B-31 'No maintainer check'")
drop("OP-21", "B-28 'Separate agent, labelled' — R11-K13-SRCH-00 writes the held-out set")
r = by["OP-18"]
r["where_it_must_land"] = "done at GATE-P (C-13 answered 'Superseded', 2026-10-01T05:03:05Z)"
r = by["LATER-10"]
r["where_it_must_land"] = "moved into R11 (S6) as R11-SRC-07 (B-18 a; S5-4 keep non-US)"
r = by["LATER-15"]
r["where_it_must_land"] = "moved into R11 (S6): CI verification in R11-MEM-07 + operator key OP-25 (A-16 = yes)"
for cid in ("R11-ACQ-23a", "R11-ACQ-23b"):
    r = by[cid]
    r["where_it_must_land"] = "R11 (S6: back in the round — S5-4 keep non-US; B-34 N1–N21 flip)"
    r["operator_gate"] = "I7-N1…N21 = a; RB-06 = a (GATE-P); flips by the operator (OP-26) with ING-GO-D"

# ---- conditional -> in scope
for cid in ("R11-ACQ-19", "R11-ACQ-20", "R11-ACQ-21", "R11-ACQ-22", "R11-ACQ-24", "R11-ACQ-25", "R11-ACQ-26",
            "R11-ACQ-27", "R11-SRC-03"):
    r = by[cid]
    r["where_it_must_land"] = r["where_it_must_land"].replace("R11 (conditional)", "R11 (S6: in scope — B-11 I8-Q5 a / B-18 a)")
r = by["R11-ACQ-27"]
r["depends_on"] += ";R11-ACQ-31;R11-ACQ-32;R11-ACQ-33"
add(r, "scope", "also activates Axon Connect (R11-ACQ-31), DocumentCloud (R11-ACQ-32) and Sourcewell/OMNIA (R11-ACQ-33); flips executed by the operator (OP-26)")
r = by["R11-ACQ-16"]
r["depends_on"] += ";R11-ACQ-29"
add(r, "scope", "+ the direct Flock transparency-portal family (R11-ACQ-29)")

# ---- re-scopes
r = by["R11-SAFE-02"]
r["title"] = "Express-terms disclosure instead of withdrawal (A-8) + leak-taint withdrawal of 9 Atlas FR rows (F-337)"
r["scope"] = ("A-8 'Keep all, accept risk' (2026-10-01T04:07:45Z): the ≈8,088 rows (5,267 NEW-1 + ≈2,821 camreg_txdot_rep_tx, incl. "
              "the 3 live NC rows) stay public; each source's rights record, page, list entry and download ATTRIBUTION file show the "
              "captured terms verbatim and the operator-accepted basis (ADR-183; text via copy batch #1). Still withdrawn: the 9 "
              "leak-derived Atlas FR rows (F-337). demo_* task pages stay stripped (R11-ACT-06, C-12). Rides republish #1 (pages) and the "
              "R11-ACT-07 re-export (files).")
r["operator_gate"] = "A-8 answered (Q-J4-2/D-J3-5 = b; I7-C1 = keep); disclosure texts confirmed verbatim (B-2)"
r["acceptance_sketch"] = ("every express-terms source shows its captured terms + the operator-accepted basis on its page and in its "
                          "download files; 0 rows of the 9 leak-derived Atlas FR rows in any public artifact")
add(r, "merged_from", "re-scoped at GATE-P (A-8): the J3 D-J3-5 / I7-C1 withdrawal work in TX-02, TX-10b, DSRC-03 and UX9-4 is replaced by this disclosure")
r = by["R11-CONF-02"]
add(r, "scope", "A-20 = a: its ER re-run is on the 11A OM-20 list (S5-3) and may change live-API answers before HG-11, disclosed by the basis label + /status/ notice; lands in 11A (no wait for REL-05)")
r["operator_gate"] = "Q-L3-1 = a; ER re-run pre-authorised on the 11A OM-20 list (S5-3); Class S republish rides R11-ACT-24"
r = by["R11-MEM-07"]
r["title"] = "Readout authorship rules in full (G4b) + gate-record hedge/delegation lint + G4c signed-gate CI verification (A-16)"
add(r, "scope", "A-16 = yes: CI verifies the operator's gate-signature commits against a committed allowed_signers (key: OP-25); absorbs LATER-15")
r["est_runs"] = "1"
r["size"] = "M"
r = by["R11-OPS-03"]
add(r, "scope", "G1-TRIM = a: consolidate the scheduler triggers into one hourly dispatcher (−$7/mo); A-5 = GL-GATE-08 as is, so no step pauses the robots-disallowing hosts")
r["monthly_cost_delta_usd"] = "-8"
r = by["R11-SAFE-06"]
add(r, "scope", "B-6 = move UA, no purchase: remove every remaining sig-project.org reference from code and docs (OP-11 dropped)")
r["operator_gate"] = "Q-E2-03 = b (GATE-P); IRI base = surveillancegraph.org"
r = by["R11-ACT-07"]
add(r, "scope", "A-0.2 = b: also removes anonymous read/list on the sig-public 09-27 tree (live-fetched prefixes excluded; tombstone) on its own verbatim go, as the first live leg; A-8: the re-export keeps the express-terms rows")
r = by["R11-SAFE-01"]
add(r, "scope", "A-0.1 = b: removes the 41 e-mail-shaped owner strings and handle tokens from the registry's non-id text at the repo tip; A-0.4 = a: its correction note discloses the retained git history (unblocks the deposits after the history scan)")
r = by["R11-ACT-06"]
add(r, "scope", "A-0.3 = b: removes /visual-language/ and the handle-bearing pages (N-6); B-8: no response-time promise; WV-05: the dispute text says senders disclose their address; A-20 basis-label / status text and the A-8 disclosure text in copy batch #1")
r["operator_gate"] = "operator go for the republish (HG-11 semantics) + every public sentence confirmed verbatim (copy batch #1); B-8 = no response-time promise"
r = by["R11-CONF-12"]
add(r, "scope", "Q-L3-5 = yes: public incl. failing and ratchet checks; states 'no human check performed' (Q-L3-3 = c)")
r = by["R11-ACT-22"]
r["operator_gate"] = "HG-03 (E4-B1 = a, batch-wide; flips by the operator, OP-26) + E4-B2 = agent clears each family after the Part VIII screen (disclosed) + operator go for each capture run"
r = by["R11-SRC-01"]
r["title"] = "Rights-flip/decline batch for owed rows (D-SOURCES.7-1, 8-1, 9-1, 9-4) + terms capture (IU1–IU5, E4-R4a OGL-Edmonton, E4-R6a bidnet)"
r["operator_gate"] = "HG-03 per GATE-P line (E4-R3 a, R4a OGL-Edmonton, R4b a, R4c b, R4d c, R5 a, R6a a, R6b a; IU1–IU5 a); flips executed by the operator (OP-26)"
r = by["R11-GOV-04"]
add(r, "scope", "A-5 = GL-GATE-08 re-confirmed as is (robots disallows disregarded, disclosed as host + count); the rule-7 opt-out register and 046c reservation refusal are still built")
for cid in ("R11-ACQ-17", "R11-ACQ-18"):
    add(by[cid], "scope", "S5-4 = keep non-US acquisition: the national OSM run keeps its non-US objects (CF-06 not confirmed)")
r = by["R11-K13-SRCH-02"]
add(r, "scope", "B-28 = b: the held-out set comes from R11-K13-SRCH-00 and stays sealed from this unit")
r["data_prereqs"] = (r["data_prereqs"] + "; " if r["data_prereqs"] else "") + "S6: the sealed held-out set from R11-K13-SRCH-00 (sha256 only)"
r = by["SEED-11"]
r["est_runs"] = "4"
add(r, "scope", "30 ADRs after GATE-P (23 + WV-04/05/06/07 + ADR-183 express-terms acceptance + ADR-184 terms-conflicted public pages + ADR-185 Part VIII lanes); 4 contexts")
r = by["OP-13"]
r["title"] = "Register the free US 511 API keys and the QLDTraffic + NSW Live Traffic keys in Secret Manager (HG-09), after the contact@ alias"
r["depends_on"] = "OP-10"
r["where_it_must_land"] = "R11 (S6: in scope — B-18 US + AU keys; C-8 alias first)"
add(r, "scope", "B-18 = a for US and AU; unblocks R11-SRC-03 and R11-SRC-07")
r = by["OP-10"]
add(r, "scope", "C-8 = alias first: every request needing a contact string (EDGAR later, 511/QLD/NSW key sign-ups) waits for it")
r = by["OP-20"]
r["where_it_must_land"] = "R11 (B-20 = a)"
r = by["OP-23"]
r["title"] = "Store the agent-made git bundle of the planning branch privately, off-disk"
r["scope"] = "B-16 = a + c: the agent creates a git bundle; the operator stores it privately; the branch is pushed at T6 (OD-27 = a) after the scans."
for cid, when in (("OP-01", "T0 (A-14: applied now)"), ("OP-02", "before the first Devin Desktop dispatch"),
                  ("OP-03", "early in Round 11 (A-14 'All, staged')"), ("OP-04", "early in Round 11 (A-14 'All, staged')")):
    add(by[cid], "scope", f"A-14 = all, staged: {when}; Devin CLI reads ~/.claude/skills (verified); Devin Desktop's path is verified at T6")
r = by["LATER-09"]
r["title"] = "Acquisition long tail: Tier-2 remainder (130), Tier 3, EDGAR (after the alias), CourtListener bulk, OCDS, paid data"
add(r, "scope", "tribal (B-32 S8) and territory (B-33 RB-08) channels and ACQ-23a/b moved into Round 11")
r = by["LATER-19"]
add(r, "scope", "scheduler consolidation moved into R11-OPS-03 (B-13 a); remaining: Cloud SQL CUD after 3 measured bills (≈ −$12/mo)")
r["monthly_cost_delta_usd"] = "-12"
r = by["LATER-01"]
add(r, "scope", "+ D-P30.2b-1 (no fold target after B-31)")
r = by["LATER-05"]
add(r, "scope", "WV-07 waived the counsel-review clauses: optional, not owed by the spec")


# ---- new units
def new(**kw):
    base = {k: "" for k in FIELDS}
    base.update(kw)
    return base


NEW = [
    new(cat_id="R11-ACQ-29", **{"class": "r11"}, title="Flock transparency-portal connector (direct fetch; A-17 D3-Q3 b)",
        theme="R11-SOURCES",
        scope=("Fetch the agency transparency portals hosted by Flock under ADR-184's envelope (" + ENV + "). Emit portal facts "
               "(retention, camera counts, aggregate search counts — S3 lane, never search reasons, case numbers, operator/user ids "
               "or plates) and shared-with lists for R11-ACQ-30. New registry row lands ingestion_permitted=false; activation in Wave B."),
        size="M", est_runs="1", depends_on="R11-ACQ-01;R11-DATA-02;R11-DATA-03;R11-GOV-04;R11-SAFE-03;R11-SAFE-04",
        operator_gate="D3-Q3 = b (GATE-P); HG-03 flip by the operator with ING-GO-B (OP-26)", live_stage="none (activation in R11-ACQ-16)",
        monthly_cost_delta_usd="0.5", where_it_must_land="R11 (S6 new; 11B Wave B)",
        merged_from="GATE-P A-17 (D3-Q3 b) + A-22 (b); D2-10", source_refs="feedback/RATIFICATION_LOG.md rounds 6, 8; design/D3-product-direction.md; research/I3-alpr-networks.md",
        acceptance_sketch="portal facts for every reachable Flock transparency portal, each with its captured terms and fetch record; 0 Part VIII bytes stored"),
    new(cat_id="R11-ACQ-30", **{"class": "r11"}, title="Flock share lists -> organisation-level configured_access claims (D-K2-4 yes)",
        theme="R11-SOURCES",
        scope=("Turn the 474,184 share-list edges (Eyes on Flock mirror) plus the direct portals' lists into organisation-level "
               "configured_access claims after the §43.2a/Part VIII screen (no operator ids, search reasons or audit rows); append-only "
               "hosted write; feeds the state × state Flock-sharing overview (R11-K13-GX-08b, A-11)."),
        size="M", est_runs="1", depends_on="R11-ACQ-29;R11-CONF-04;R11-SAFE-03;R11-K13-GX-05a",
        operator_gate="D-K2-4 = yes; OD-24 = b (GATE-P); hosted write on the GATE-G5 OM-20 list or an in-ticket go",
        live_stage="production write (append-only claims)", monthly_cost_delta_usd="0", where_it_must_land="R11 (S6 new; 11C)",
        merged_from="GATE-P A-22 (OD-24 b, D-K2-4 yes); K2 D-K2-4", source_refs="feedback/RATIFICATION_LOG.md round 8; design/K2-graph-and-entities.md",
        acceptance_sketch="share-list claims exist at organisation level only; 0 person-level or audit-row fields; overview O2 shows Flock-scale access"),
    new(cat_id="R11-ACQ-31", **{"class": "r11"}, title="Axon Fusus 'Connect <Place>' connector (B-35 IT7 full fetch; SIG-PUB-002-safe)",
        theme="R11-SOURCES",
        scope=("Fetch the agency-hosted Connect pages in full under ADR-184's envelope; redact private registrants (resident/business "
               "names, home addresses, contact data, cameras at private residences) in memory before any byte is persisted — store only a "
               "redacted re-serialisation (J4 P8-5) — and emit programme-level facts and counts (S1 lane)."),
        size="M", est_runs="1", depends_on="R11-ACQ-01;R11-SAFE-04;R11-SAFE-03",
        operator_gate="I7-IT7 = a (GATE-P); HG-03 flip by the operator with ING-GO-D (OP-26)", live_stage="none (activation in R11-ACQ-27)",
        monthly_cost_delta_usd="0.3", where_it_must_land="R11 (S6 new; 11C code, Wave D activation)",
        merged_from="GATE-P B-35 (IT7 a) + A-17", source_refs="feedback/RATIFICATION_LOG.md round 16; research/I7-candidates.md",
        acceptance_sketch="programme-level Axon Connect facts for every reachable agency page; 0 registrant bytes in any tier (schema + storage test)"),
    new(cat_id="R11-ACQ-32", **{"class": "r11"}, title="DocumentCloud / MuckRock connector (E4-R2a flip; public documents only)",
        theme="R11-SOURCES",
        scope=("Fetch public DocumentCloud documents relevant to surveillance under ADR-184's envelope; Part VIII screen on every byte "
               "(S6/S7 free text and incidental names); every claim links the uploader's page."),
        size="M", est_runs="1", depends_on="R11-ACQ-01;R11-SAFE-04;R11-ACQ-14",
        operator_gate="E4-R2a = b; I7-C2 = fetch (GATE-P); HG-03 flip by the operator with ING-GO-D (OP-26)",
        live_stage="none (activation in R11-ACQ-27)", monthly_cost_delta_usd="0.5", where_it_must_land="R11 (S6 new; 11C code, Wave D activation)",
        merged_from="GATE-P B-39 (C2) + B-41 (R2a b)", source_refs="feedback/RATIFICATION_LOG.md rounds 17-18; design/E4-rights-packets.md",
        acceptance_sketch="documents fetched only from public pages; uploader link on every claim; Part VIII screen report 0 unscreened bytes"),
    new(cat_id="R11-ACQ-33", **{"class": "r11"}, title="Sourcewell + OMNIA Partners contract-page connector (B-39 C3)",
        theme="R11-SOURCES",
        scope="Fetch public Sourcewell and OMNIA contract pages under ADR-184's envelope; contract facts and documents; terms captured verbatim.",
        size="M", est_runs="1", depends_on="R11-ACQ-01;R11-ACQ-11;R11-SAFE-04",
        operator_gate="I7-C3 = fetch (GATE-P); HG-03 flips by the operator with ING-GO-D (OP-26)", live_stage="none (activation in R11-ACQ-27)",
        monthly_cost_delta_usd="0.2", where_it_must_land="R11 (S6 new; 11C code, Wave D activation)",
        merged_from="GATE-P B-39 (C3)", source_refs="feedback/RATIFICATION_LOG.md round 17; research/I7-candidates.md",
        acceptance_sketch="contract facts with captured terms and fetch records for both portals"),
    new(cat_id="R11-K13-SRCH-00", **{"class": "r11"}, title="Held-out search relevance set written by a separate agent context (B-28 b)",
        theme="R11-UX-CORE",
        scope=("A separate agent context writes the ≥ 40-query held-out set, labelled 'agent-authored held-out set; not independent', "
               "before and never visible to the contexts that tune search; stored outside the worktree (restricted bucket) with only its "
               "sha256 committed; read only by the search acceptance (R11-K13-SRCH-07)."),
        size="S", est_runs="0.5", depends_on="", data_prereqs="the first model release (R11-ACT-24) to judge relevance against", operator_gate="D-K3-7 = b (GATE-P); restricted-bucket write on the GATE-G5 OM-20 list or an in-ticket go",
        live_stage="production write (restricted-bucket object)", monthly_cost_delta_usd="0", where_it_must_land="R11 (S6 new; 11C)",
        merged_from="GATE-P B-28 (D-K3-7 b); replaces OP-21", source_refs="feedback/RATIFICATION_LOG.md round 14; design/K3-search.md",
        acceptance_sketch="set sealed before SRCH-01/02 start; sha256 matches at SRCH-07; label present wherever the metric appears"),
    new(cat_id="R11-SRC-07", **{"class": "r11"}, title="Keyed AU traffic-camera APIs: QLDTraffic + NSW Live Traffic (D-SOURCES.8-2 a)",
        theme="R11-SOURCES", scope="Wire the QLDTraffic and NSW Live Traffic APIs after the operator registers the keys (Secret Manager, HG-09); QLDTraffic replaces camreg_qldc_au (E4-R4c b).",
        size="M", est_runs="1", depends_on="OP-13;R11-ACQ-01", operator_gate="D-SOURCES.8-2 = a; E4-R4c = b (GATE-P); HG-09 keys by the operator",
        live_stage="production write", monthly_cost_delta_usd="0.2", where_it_must_land="R11 (S6 new; 11D)",
        merged_from="LATER-10 (moved in at S6); D-SOURCES.8-2; E4 R4c option b", source_refs="research/F1-owed-register.md; design/E4-rights-packets.md",
        acceptance_sketch="per I8 §7.7 per-source verification for both APIs; keys never in files"),
    new(cat_id="R11-GOV-06", **{"class": "r11"}, title="Single-operator true-deletion path (WV-06): design first, mechanism keeps the audit record",
        theme="R11-GOVERNANCE-RECORDS",
        scope=("Design note + ADR-181 compensating controls, then a mechanism that deletes material SIG must not hold (evidence bytes or "
               "rows) on the operator's in-ticket go only, never on an OM-20 list, never run by an agent without that go; every use logged "
               "publicly with its reason and a tombstone (category + date, never content). The insert-only spine rule is unchanged for every "
               "other path."),
        size="M", est_runs="1", depends_on="R11-OPS-04;R11-REL-08;R11-GOV-02", operator_gate="WV-06 waived (GATE-P); each deletion = operator in-ticket go",
        live_stage="none (mechanism only)", monthly_cost_delta_usd="0", where_it_must_land="R11 (S6 new; 11D)",
        merged_from="GATE-P A-23 WV-06", source_refs="feedback/RATIFICATION_LOG.md round 9; docs/2_canonical_design_spec.md SIG-GOV-008",
        acceptance_sketch="a fixture deletion leaves a tombstone and a decision-log entry; no agent path can invoke it without the go"),
    new(cat_id="R11-K13-MAP-08", **{"class": "r11"}, title="'My location' map-pan control (D-K1-7 approved) after a SIG-GOV-017 analysis",
        theme="R11-UX-EXPLORE",
        scope=("Write a SIG-GOV-017 analysis first; build only a map-pan control (browser-only geolocation after a click, never sent to SIG; "
               "no 'cameras near you' list, count, alert or proximity notice). If the analysis finds it cannot comply, pause and return the "
               "question (waive GOV-017 for it, or drop it) to the operator."),
        size="S", est_runs="0.5", depends_on="R11-K13-MAP-03b", operator_gate="D-K1-7 = yes (GATE-P); GOV-017 not waived",
        live_stage="none", monthly_cost_delta_usd="0", where_it_must_land="R11 (S6 new; 11D)",
        merged_from="GATE-P B-44 (D-K1-7)", source_refs="feedback/RATIFICATION_LOG.md round 18; design/K1-map.md",
        acceptance_sketch="GOV-017 analysis committed; no location leaves the browser (network test); no proximity output"),
    new(cat_id="R11-REVIEW-01", **{"class": "r11"}, title="Post-round deep review by Claude Code (Opus 5.5, xhigh), modelled on the Stage-P review",
        theme="R11-ACCEPTANCE",
        scope=("After the final release and the tail's DOC row, a different harness (Claude Code) reviews the round read-only — code, build "
               "memory, CI and live state — and writes a findings register (S0–S3) and a next-round planning input. Not a chain row; "
               "no in-round second harness."),
        size="L", est_runs="8", depends_on="", operator_gate="A-15 (GATE-P); read-only", live_stage="read-only", monthly_cost_delta_usd="0",
        where_it_must_land="post-round (after P38.4)", merged_from="GATE-P A-15 follow-up (round 7)",
        source_refs="feedback/RATIFICATION_LOG.md round 7; META_PLAN.md (this Stage-P review as the model)",
        acceptance_sketch="findings register with evidence classes; every S0/S1 finding cites file:line, commit, PR or probe"),
    new(cat_id="OP-25", **{"class": "operator"}, title="Operator-only gate-signing key + allowed_signers (A-16)", theme="OPERATOR-ACTION",
        scope="Passphrase- or hardware-backed SSH signing key never loaded into an agent-reachable ssh-agent; public key committed to allowed_signers; R11-MEM-07 verifies in CI.",
        size="S", est_runs="0", operator_gate="Q-B4-2 = a", live_stage="none", monthly_cost_delta_usd="0",
        where_it_must_land="stage-B (by GATE-B if possible; before GATE-G4 at the latest)", merged_from="GATE-P A-16; LATER-15",
        source_refs="feedback/RATIFICATION_LOG.md round 6; design/B4-verification.md", acceptance_sketch="—"),
    new(cat_id="OP-26", **{"class": "operator"}, title="HG-03 flips of the GATE-P-decided rows, executed by the operator per wave",
        theme="OPERATOR-ACTION",
        scope="Agents prepare each wave's flip list from the GATE-P lines (A-7, A-18, B-33, B-34, B-35, B-39, B-41); the operator's verbatim line flips ingestion_permitted; never pre-authorised.",
        size="S", est_runs="0", operator_gate="HG-03", live_stage="production write (registry flip)", monthly_cost_delta_usd="0",
        where_it_must_land="R11 (per wave: A-18 in 11B; GATE-G4, GATE-G5, GATE-G6 lists)", merged_from="GATE-P (rights lines)",
        source_refs="feedback/RATIFICATION_LOG.md rounds 3-4, 7, 16-18", acceptance_sketch="—"),
]
out = rows + NEW
with F.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
print("catalog rows", len(out))
