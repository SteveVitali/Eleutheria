# E4: Rights-decision packets (HG-03)

Row **E4** of `META_PLAN.md` (Stage P). Authored 2026-09-30T16:51Z (`date -u`) by Claude Code (Opus 5.5), planning HEAD
`884915a2`, chain tip `b051732c`. Everything here is read-only. Nothing was flipped and nothing was fetched. No
control file was edited: `sources.toml`, DEFERRALS, LEDGER, the acquisition queue and the packets are unchanged.

> **Not legal advice (P4).** This document sets out facts, options and precedents that are already recorded. Every
> decision belongs to the operator under **HG-03**, and the agent decides nothing. "Precedent-consistent" means only
> "matches what an earlier recorded decision did with the same class of facts". It is not a recommendation on the
> law. Any wording drafted for the operator to sign is *agent-drafted* and must be confirmed verbatim.

**Standing operator rule (LEDGER GATE DECISIONS, `sed -n 156-165p`).** GL-GATE-07, 2026-09-18, verbatim: *"We should
ungate the D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of
approving them"*. Execution rule: US → `LicenseRef-PublicRecord-FactualCompilation`; non-US →
`LicenseRef-OperatorAccepted-DBRight`; reviewer `maintainer (delegated)` + date. The same text says: *"CourtListener
deferred by operator (FLP agreement stays OPEN)."* The operator later invoked the rule per ticket twice. P27.2
(2026-09-22) answered *"Approve under GL-GATE-07"*. P29.3 (2026-09-23) answered *"Flip under GL-GATE-07 + fetch"*,
which covered municipal CCOPS reports and a UK body (`docs/build/reports/rights/p293_dispositions.json`). Q-19
(META_PLAN §7) is still open. It asks whether GL-GATE-07 is the default for new sources.

**GL-GATE-07 coverage vocabulary used below.**
- **EXECUTED**: already flipped under the rule, so no decision is owed.
- **PRECEDENT**: the facts match a row the rule's execution already flipped. One line from the operator confirms it.
- **ARGUABLE**: the literal words ("all the 'rights review' cases") reach it, but no execution applied the rule to
  facts like these.
- **NOT COVERED**: the terms are affirmatively restrictive, the rule's own text defers the source, or the blocker is
  not a rights question.

---

## 1. Decision table: answer each line with its letter (e.g. `R3: a`)

`c/d` = option letters. **New facts first** means that something must be captured before the decision is fully
informed. The operator may still choose to decide without it.

| # | row | source(s) | GL-GATE-07 | options | precedent-consistent | new facts first? |
|---|---|---|---|---|---|---|
| **R1** | D-JURIS.2-1 | `declarationcamera_be` (Belgian-eID leg only) | n/a (rights already decided 2026-09-15) | **a** close: rights scope DONE + eID leg WONTFIX, skipped by operator · **b** keep as an HG-04 operator-credential row (not a rights row) · **c** pursue eID/outreach | a (the operator skipped the same HG-04 outreach class in D-JURIS.2-2, WONTFIX 2026-09-16) | no |
| **R2a** | D-SOURCES.2-2 | `documentcloud` | NOT COVERED (P26.16: "GL-GATE-07's camera-registry basis does not reach it") | **a** decline → WONTFIX · **b** flip despite the ToS anti-extraction clause · **c** seek an affirmative DocumentCloud API grant or review named documents one by one | a (packet already records "declined", 2026-09-17) | no |
| **R2b** | D-SOURCES.2-2 | `courtlistener_recap` | NOT COVERED (deferred by name in GL-GATE-07) | **a** decline → WONTFIX · **b** approach FLP's partnership/commercial tier (agreement + token, HG-09) · **c** accept the membership terms and hold a token (packet: SIG looks ineligible as written) | none recorded | no |
| **R3** | D-SOURCES.7-1 | `dot_511_tx` (the sole remainder, see S4) | PRECEDENT (`camreg_txdot_rep_tx`: a personal-account ArcGIS item with licence "none", flipped and live) | **a** flip under GL-GATE-07 (US) · **b** decline as redundant with `camreg_txdot_rep_tx` · **c** find a TxDOT-owned layer first | a (or b, if the operator treats it as a duplicate) | no |
| **R4a** | D-SOURCES.8-1 | `camreg_edmonton_ab` (CA) | PRECEDENT (Calgary/York: Canadian, no grant → DBRight) | **a** flip, non-US basis · **b** capture the City of Edmonton ToU first · **c** decline | a | no |
| **R4b** | D-SOURCES.8-1 | `camreg_hk_hk` (HK) | PRECEDENT (`camreg_polyu_hk`: HK, licence "none" → DBRight, live) | **a** flip, non-US basis · **b** capture the data.gov.hk T&C first · **c** decline | a | no |
| **R4c** | D-SOURCES.8-1 | `camreg_qldc_au` (AU) | PRECEDENT (Donegal/NZTA: non-grant wording → DBRight) | **a** flip, non-US basis · **b** use the QLDTraffic API (CC-BY per CKAN; key = HG-09) instead · **c** decline | a | no |
| **R4d** | D-SOURCES.8-1 | `camreg_bellevue_wa` (US) | ARGUABLE (express non-commercial clause; closest precedent: Lexington's indemnify-and-defend clause was flipped) | **a** flip under GL-GATE-07 (US) · **b** ask the City of Bellevue for written authorization · **c** decline | none for an NC clause | **yes**: operator statement on whether SIG's use or exports are "commercial" |
| **R5** | D-SOURCES.9-1 | `procportal_chicago_il` | PRECEDENT (`camreg_chicago_il`: same `data.cityofchicago.org` portal, terms uncaptured, flipped) | **a** flip under GL-GATE-07 (US) · **b** capture the Chicago ToU first · **c** decline | a | no |
| **R6a** | D-SOURCES.9-4 | `bidnet_direct` | ARGUABLE (no vendor-platform procurement portal has ever been flipped) | **a** capture `bidnetdirect.com` terms, then decide · **b** flip under GL-GATE-07 now · **c** decline | none (it would be the first vendor platform) | **yes**: vendor ToS never captured |
| **R6b** | D-SOURCES.9-4 | `periscope_s2g` | ARGUABLE | **a** close as superseded by `bidnet_direct` (WONTFIX) · **b** review with R6a | a (the row itself calls it superseded) | no |
| **B1** | D-R10-SOURCES-1 | rights basis for the **23 new targets** in §4 (3 dossier families + 2 pilot families; 3 lanes each) | PRECEDENT (P29.3 applied it to municipal CCOPS reports; Q-19 proposes it as the default) | **a** apply GL-GATE-07 (US) to all three lanes, batch-wide · **b** decide per target after terms are captured · **c** defer the live stage | a | **yes**: URL reconciliation first (§4.3, NEW-7) so the decision binds the real URLs |
| **B2** | D-R10-SOURCES-1 | Part VIII preflight for 5 families (all `not_assessed`) | NOT COVERED (Part VIII, not rights) | **a** a Round-11 ticket screens + the operator signs `clear` in one line per family · **b** keep `not_assessed` (the live stage stays blocked) | a (P27.2 class-level Part VIII sign-off) | no |
| **B3** | D-P32.20-1 | SRC-027 network-audit workbooks | NOT COVERED (`prohibited_until_review`: plates, persons, queries) | **a** keep it metadata-only permanently: record the workbook path `rejected` · **b** commission an aggregate-only design · **c** leave it `prohibited_until_review` (owed) | a (the dossier "does not depend on it", per `PART_VIII_PREFLIGHT.json`) | no |
| **B4** | D-P32.20-1 | SD PAB recommendation (~16 MB) + ALPR Use Policy (recorded 403) | n/a (method, not rights) | **a** approve a per-target byte-bound exception + one bounded retry; outcomes recorded honestly · **b** record both as honest refusals; the recommendation stays `proposed` · **c** drop both | none | no |
| **B5** | D-R10-SOURCES-1 | 4 targets already on green sources (OSCN §7-606.1 ×2, ops manual §5-118, purchasing index) | EXECUTED (GL-GATE-03, 2026-09-10) | **a** confirm that no re-approval is needed (the row says so itself) · **b** re-review anyway | a | no |
| **B6** | D-P32.21-1 | registry rows for SRC-006/007/011 (`registered_source: null`) | follows B1 | **a** Round 11 adds 3 rows (OMES, DAC, CA State Auditor) on the B1 basis · **b** add the rows gated only · **c** drop the incremental families (dossier families only) | none | no |
| **S1** | D-SOURCES.12-1 | (status) | EXECUTED | **a** approve PARTIAL → **DONE** (2026-09-26, P31.13) · **b** → WONTFIX for the 68 unrecoverable rows, re-armed on an infrastructure change · **c** keep PARTIAL | a | no |
| **S2** | D-SOURCES.9-2 | `bonfire` (status + decision) | ARGUABLE | **a** re-scope from robots wall to rights + engineering, capture terms, decide later · **b** decline → WONTFIX (2 tenants, no parser) · **c** keep as is | b or a (P26.17 closed the analogous D-SOURCES.2-4 as "RESOLVED-BY-GL-GATE-08") | **yes** for a (terms uncaptured) |
| **S3** | D-SOURCES.9-3 | `opengov_procurement` (status) | NOT COVERED (WAF challenge; SIG-INGEST-013 still binds) | **a** later-phase(trigger: documented public endpoint + reviewable terms) · **b** WONTFIX, re-armed on the same trigger · **c** keep OPEN | a | no |
| **S4** | D-SOURCES.7-1 | (status) | EXECUTED for 4 of 5 | **a** approve OPEN → **PARTIAL** (4/5 flipped 2026-09-18; remainder `dot_511_tx` = R3) · **b** keep OPEN | a | no |
| **S5** | D-JURIS.2-1 | (register placement) | n/a | **a** move it out of the "Rights/reviewer" lane into "Operator credentials/outreach" (Appendix B, OPERATIONAL_READINESS §(f3)); moot if R1 = a · **b** leave it | a | no |

**Tally.** 22 decision lines: 11 rights (R), 6 batch (B), 5 status (S).
- **EXECUTED already:** S1, S4 and B5 are corrections or confirmations only.
- **PRECEDENT (GL-GATE-07 covers them by precedent):** R3, R4a, R4b, R4c, R5 and B1.
- **ARGUABLE:** R4d, R6a, R6b and S2.
- **NOT COVERED:** R2a, R2b, B2, B3 and S3.
- **New facts first:** R4d (operator statement), R6a (vendor ToS), S2a (Bonfire terms) and B1 (URL reconciliation).
  The terms captures can run through `sig-db rights-decisions --capture-terms` in Round 11 (it needs a DSN and is a
  hosted write), or as a manual capture quoted into the packet.

---

## 2. Conventions: what a decision records, and how it is verified

**CLI verified in code (evidence class `code`).**
- `sig-connectors` (`connectors/pyproject.toml:38`) → `connectors/src/connectors/cli.py`:
  - `gate --source` (`:56-57`, `_gate` `:184-192`): prints `LOADABLE`, exit 0, or `REFUSED`, exit 1.
  - `review-status --source` (`:59-63`, `_review_status` `:223-241`): shows the five fields `ingestion_permitted`,
    `compact`, `custody`, `rights` and `reviewed-by`.
  - `validate`: the flip-metadata rule, `connectors/review.py:99-126`.
  - `export-check`.
  - `run --source <id> --mode live`: refuses with exit 3 unless review-status is green (`:20-24`, `:64-69`).
- `sig-tasks acquisition {queue,explain,packet,check,pilot,pilot-check}`: `tasks/src/tasks/cli.py:173-238`.
- `sig-db rights-decisions --dsn --decisions [--apply] [--capture-terms]`: `db/src/db/cli.py:55-81`, ADR-095
  append-only.

**Baseline at authoring (`recorded-execution`, 2026-09-30T16:41Z):**
- `sig-connectors validate` returns: 342 registered, 236 `ingestion_permitted`, 236 loadable, 101 UNDETERMINED,
  "self-checks OK".
- `sig-tasks acquisition check` and `pilot-check` both return 0 violations.
- Per-source `gate` and `review-status` outputs appear in §6.

**A flip alone does not make a row loadable.** The loader ANDs three conditions (`connectors/loader.py:94-116`):
`ingestion_permitted`, a `compact_status` in {permission_granted, permission_granted_conditional, public_terms_only,
partnership_active}, and a `custody_posture` in {MIRROR, DERIVE, REFERENCE}. Today every gated row in this packet
fails at least one of the last two:
- 13 rows (the 5 R-rows' camera/TX sources, the 5 procurement rows and the 3 dossier rows) sit at `not_contacted`
  (`compact=False`).
- 5 procurement rows sit at `LINK` (`custody=False`).

**Flip recipe.** This follows the P26.16/P29.3 precedent. The edits happen in a Round-11 ticket, never in planning.
- Set `ingestion_permitted = true` on the `sources.toml` row.
- Set `compact_status = "public_terms_only"` and change the custody posture from `LINK` to `REFERENCE` or `MIRROR`.
  The procportal siblings use `MIRROR`.
- Set `rights_reviewed_by = "maintainer (delegated)"` or `"operator"`, always a role and never a name.
- Set `rights_reviewed_on` and `last_verified` from `date -u`, and set `review_packet`.
- Fill the `[rights]` block: `spdx` (per the GL-GATE-07 rule), `attribution`, `redistributable`,
  `derivative_permitted`, `terms_url` and `retrieval_date`.
- Add notes of the form `FLIPPED <date> under GL-GATE-07 — "<operator's verbatim answer>"`.
- Fill the packet's **Decision** line. 25 flipped sources still carry a blank line (NEW-10).
- Add a LEDGER GATE DECISIONS entry that carries the verbatim answer.
- In Stage B, update the DEFERRALS row and append an obligation event.
- If hosted claims already exist, add a dispositions JSON for `sig-db rights-decisions`.

Verify with:

```
uv run sig-connectors review-status --source <id>   # all five fields True; "loadable now: True"
uv run sig-connectors gate --source <id>            # LOADABLE, exit 0
uv run sig-connectors validate                      # flip-metadata rule holds
uv run sig-connectors export-check                  # compartments stay single-licence
uv run sig-connectors run --source <id> --mode live # (Round 11) no longer exit 3
```

**Decline recipe.** A decline is a valid close: the obligation event for D-SOURCES.2-2 already reads "decline is a
valid close".
- Fill the packet's Decision line with `declined — <role>, <date>`.
- Add a `DECLINED <date> (operator, HG-03)` note to the registry row. Leave `ingestion_permitted` unset/false.
- Mark the DEFERRALS row `WONTFIX` with the reason.

Verify: `gate --source <id>` still returns `REFUSED` with exit 1, and `run --mode live` returns exit 3.

---

## 3. Part A: the six rights rows (per-row packets)

### R1: D-JURIS.2-1 (PARTIAL; Appendix B places it in "Rights/reviewer")

- **Sources:**
  - `raa_prefectures`: ODbL-1.0.
  - `decp_fr`: LicenceOuverte-2.0, ADR-084.
  - `madada` and `declarationcamera_be`: `LicenseRef-DerivedFacts-Citations`, reviewer `counsel (HG-02)`.
  - All four were flipped 2026-09-15, and `gate` returns **LOADABLE** for each (§6).
- **Live evidence:**
  - `docs/build/reports/live_runs/2026-09-16_{decp_fr,raa_prefectures,madada,declarationcamera_be}.json`.
  - `2026-09-19_raa_prefectures_p2617.json`.
  - The DEFERRALS cell records 7,234 `decp_fr` spine claims and 26 `madada` claims.
- **What is actually still blocked:** only `declarationcamera_be`'s *access* is blocked. The register sits behind
  Belgian eID (citizen assurance Level 300) and has `NoLiveTargets` (`sources.toml` notes). The DEFERRALS cell reads:
  *"Still owed — HG-04 only"*.
  - The row's "unblocked by" text is stale: it still asks the operator to "resolve the LO 2.0 disposition". That was
    decided on 2026-09-15 (`PROPOSED_DISPOSITIONS.md:45`, ADR-084).
  - OPERATIONAL_READINESS `:72-73`/`:346` carry the same staleness (NEW-5).
- **Rights evidence status:** captured and decided. Packets: `docs/build/reports/rights/{raa_prefectures,decp_fr,madada,declarationcamera_be}.md`.
- **Related decision:** D-JURIS.2-2 (the HG-04 outreach to the FR/BE operators, including `declarationcamera_be`) is
  **WONTFIX 2026-09-16, "SKIPPED-BY-OPERATOR"**.
- **Options:** see the table. Option (a) keeps the register consistent with D-JURIS.2-2.
- **What is recorded:** under (a), the DEFERRALS cell becomes `DONE (rights/flip scope) + WONTFIX (eID leg, skipped by
  operator — consistent with D-JURIS.2-2)`. Nothing changes in `sources.toml`: the row is already flipped, and live
  stays refused on `NoLiveTargets`.
- **Verify:** `uv run sig-connectors gate --source declarationcamera_be` returns LOADABLE today. That confirms the
  rights posture is done and that the remaining block is access, not rights.

### R2a / R2b: D-SOURCES.2-2 (OPEN)

- **`documentcloud`:** REFUSED; `compact=True`, `custody=True`, `rights=False`, `reviewed-by=False`.
  - The packet `rights/documentcloud.md` quotes the MuckRock ToS **verbatim** (retrieved 2026-09-17). It excludes
    *"any use of data mining, robots, or similar data gathering and extraction tools"*, and user content is
    *"personal use only"*.
  - The packet Decision reads **"declined"**, maintainer (delegated), 2026-09-17.
  - P26.16 re-affirmed it: *"GL-GATE-07's camera-registry basis does not reach it"* (`runs/P26.16.md` §DocumentCloud
    disposition).
  - Robots: `api.www.documentcloud.org` has `Disallow: /`. Robots no longer gates under GL-GATE-08; the ToS does.
- **`courtlistener_recap`:** REFUSED.
  - The packet `rights/courtlistener_recap.md` quotes the FLP membership terms **verbatim** (2026-09-17): *"may not
    be used to build tools for for-profit or non-profit organizations…"* and *"Commercial users should contact our
    partnerships team"*.
  - A keyless probe returns 401. GL-GATE-07's own text: *"CourtListener deferred by operator (FLP agreement stays
    OPEN)"*.
- **What is blocked:** targeted-lookup connectors that are landed and fixture-tested. Nothing downstream depends on
  them.
- **Terms status:** both are captured verbatim, so no new facts are needed.
- **Recorded on decline:** the Decision lines already say "declined". Add the operator line to the packets; the
  DEFERRALS row becomes WONTFIX.
- **Recorded on R2b (b):** the FLP agreement is an off-repo operator act. The token is env-only (HG-09, never in a
  file). Then flip under a new per-source basis (not GL-GATE-07); the packet records the agreement tier.

### R3: D-SOURCES.7-1 (OPEN; S4 proposes PARTIAL)

- **State (`gate`, §6):**
  - `dot_511_la`, `_ga`, `_al` and `_md` are **LOADABLE**. They were flipped 2026-09-18 under GL-GATE-07 with
    `LicenseRef-PublicRecord-FactualCompilation` (annexes `rights/annex/p2616/dot_511_{la,ga,al,md}.md`).
  - All four ran live `ok`: la 5,220, ga 83,653, al 6,084 and md 4,968 claims (`docs/build/reports/p2616_outcomes.json`).
  - MD's "needs a licence-registry row first" was resolved by that LicenseRef (`policy/src/policy/data/licenses.toml:248`).
- **Remainder: `dot_511_tx`.**
  - REFUSED; `compact=False` (`not_contacted`), `rights=False`.
  - `sources.toml:3054`: ArcGIS item `adb3663e…` is published under a *personal account (dkarctur)*, with an EMPTY
    `licenseInfo`. The target has 2,798 observed rows (`dot_511_targets.toml:234`).
- **Precedent:** `camreg_txdot_rep_tx` ("Texas Traffic Cameras", owner `JustinZero`, licence "none" in the reviewed
  catalog) was flipped under GL-GATE-07 on 2026-09-18 and ran live (32,140 claims locally; the D-SOURCES.12-1 cell
  reports 33,900 hosted on retry). *Inference:* the two layers likely overlap (same TxDOT camera population), so
  option (b) is a real choice.
- **Terms:** there are none to capture. The item has no licence text.
- **Recorded on (a):** the flip recipe (§2), with spdx `LicenseRef-PublicRecord-FactualCompilation`.
- **Verify:** `uv run sig-connectors gate --source dot_511_tx`.

### R4a–d: D-SOURCES.8-1 (PARTIAL: 10 of 14 flipped 2026-09-18, all live `ok`)

The four remainder rows are all REFUSED with `compact=False` and `rights=False` (§6). They were never in P26.16's
257-row worklist:
- Edmonton appears in `catalog_sweep_2026-09-18_reviewed.json` classified `shape: non_target` ("no camera/surveillance
  signal"), even though its keywords list `camera`, `traffic camera` and `public safety camera`.
- The other three items are absent from the artifact.

That is why the execution skipped them. The operator excluded nothing (NEW-9).

| id | publisher / rows | recorded terms (`sources.toml` notes, verbatim metadata) | captured verbatim? | nearest flipped precedent |
|---|---|---|---|---|
| `camreg_edmonton_ab` (`:3387`) | City of Edmonton, Socrata `7fnd-72gr`, 67 rows (intersection safety devices) | licence "See Terms of Use"; no licence on dataset or portal | no (ToU not fetched) | `camreg_calgary_ab`, `camreg_york_on` (CA → DBRight) |
| `camreg_hk_hk` (`:3652`) | ArcGIS `0b05a33c…`, 32 rows | defers to data.gov.hk "Terms and Conditions of Use" | no | `camreg_polyu_hk` (HK, licence "none" → DBRight, 176 claims live) |
| `camreg_qldc_au` (`:3607`) | ArcGIS `eebb9977…`, 240 rows | "Currently available for external use" (not a grant); QLDTraffic API is token-gated, CC-BY per CKAN | licenceInfo yes; API terms no | `camreg_donegal_ie` ("No Access Constraints" ≠ grant → DBRight), `camreg_nzta_nz` |
| `camreg_bellevue_wa` (`:3536`) | City of Bellevue, ArcGIS `d47e172d…`, 234 cameras | no-warranty disclaimer **plus** *"Any commercial use or sale of this map or portions thereof, is prohibited without express written authorization by the City of Bellevue"* | yes (licenseInfo verbatim) | `camreg_lexington_ky` (ToU with an indemnify-and-defend clause, flagged counsel-needed, flipped anyway) |

- **Bellevue new fact (R4d).** DEFERRALS says Bellevue needs "an operator decision on whether SIG's use is
  non-commercial". That is an operator statement of fact. The agent cannot supply it.
  - Relevant recorded facts: SIG's legal home is an individual maintainer (HG-01, 2026-09-22).
  - The `public_record` compartment is exported under `LicenseRef-PublicRecord-FactualCompilation`, which is
    self-relicensable only (`licenses.toml:248-252`).
- **Recorded on flip:** the §2 recipe. Edmonton, HK and QLDC get `LicenseRef-OperatorAccepted-DBRight`; Bellevue gets
  `LicenseRef-PublicRecord-FactualCompilation`, with the NC clause quoted in the notes.
- **Verify:** `uv run sig-connectors gate --source camreg_<id>`.

### R5: D-SOURCES.9-1 (OPEN), `procportal_chicago_il`

- **State:** REFUSED on all three conditions: `compact=False` (`not_contacted`), `custody=False` (`LINK`) and
  `rights=False`.
- **Packet `rights/procportal_chicago_il.md`:** `/api/views/rsxa-ify5` retrieved 2026-09-18. `license` is **absent**
  and attribution is "City of Chicago".
  - Robots allow `/resource/*.json` (`Crawl-delay: 1`).
  - Verified surveillance-relevant rows exist ("VIDEO/SURVEILLANCE CAMERA SERVICES", "VIDEO SURVEILLANCE MANAGEMENT
    SYSTEM").
  - The City ToU is **not captured**.
- **Precedent:**
  - `camreg_chicago_il` is on the same `data.cityofchicago.org` portal. Its note reads "the City terms document could
    not be captured verbatim this run (chicago.gov ToU page 404)". It was **flipped under GL-GATE-07** on 2026-09-18
    (`sources.toml:3339`).
  - The four sibling procportal datasets were flipped under GL-GATE-06 on verbatim PD/CC0 metadata.
- **Recorded on (a):** the §2 recipe. Custody changes from `LINK` to `MIRROR` (matching the siblings), and compact
  becomes `public_terms_only`.
- **Verify:** `uv run sig-connectors gate --source procportal_chicago_il`.

### R6a / R6b: D-SOURCES.9-4 (OPEN), `bidnet_direct` and `periscope_s2g`

- **State:** both are REFUSED on `compact`, `custody` (`LINK`) and `rights`.
- **`bidnet_direct` packet:**
  - Access verified 2026-09-18 on 9 registered storefronts.
  - robots.txt is quoted verbatim: `User-agent: *` allows public paths with `Crawl-delay: 5`. It also names
    `anthropic-ai`/`ClaudeBot` among the blocked agents; SIG's `procurement/1.0.0` UA is not named.
  - The **ToS is not captured**: *"the reviewer must fetch and quote `https://www.bidnetdirect.com/terms`"*.
  - The operator of the record is the agency, but the surface belongs to a vendor (mdf commerce).
- **`periscope_s2g` packet:** a skeleton. Terms were *"NOT fetched"* and robots were "not reviewed this pass". The
  registry notes call BidNet Direct "the Periscope S2G successor surface".
- **Precedent:** none. No vendor-platform procurement portal is flipped (`planetbids`, `publicpurchase`, `demandstar`,
  `buyboard` and `bonfire` are all gated). GL-GATE-07's recorded rationale is public-record factual compilations
  (`licenses.toml:242-247`). A vendor surface re-serving agency records is a different fact pattern. That is a fact,
  not a conclusion.
- **Recorded on (a):**
  1. A Round-11 capture of the terms, quoted into `rights/bidnet_direct.md` with its retrieval date.
  2. Then the operator's one-line decision.
  3. Then the §2 recipe or a decline.
- **Verify:** `uv run sig-connectors gate --source bidnet_direct`.

---

## 4. Part B: the D-R10-SOURCES-1 per-target batch (with D-P32.18/19/20/21-1)

### 4.1 Scope

D-R10-SOURCES-1 owns the "exact-target source/evidence-use review and bounded pilot acquisition". Its live legs are
the four return passes:
- `docs/build/reports/p32.18-okc-dossier/LIVE_RETURN_PASS.json`: 6 targets.
- `p32.19-tulsa-dossier/LIVE_RETURN_PASS.json`: 6 targets.
- `p32.20-san-diego-dossier/LIVE_RETURN_PASS.json`: 9 targets.
- `p32.21-acquisition-pilot/ACQ_PILOT_RETURN_PASS.json`: 2 families, 6 targets.

All four are `prepared_not_executed` with `approval_refs: []`.

That makes **27 target rows**. 4 are already on green sources (B5), leaving **23 that need B1**. The row's own text
says *"independently authorized existing targets need no invented reapproval"*. The other 21 acquisition-queue
candidates (SRC-008–010, 012–026) are **not** in the live batch: the pilot rejected them for "capacity",
"no_recorded_award_gap", "p31_owned" or "preflight_screening_owed" (`p32.21-acquisition-pilot/READOUT.md:25-45`). No
decision is owed on them now; they route to Stream I7 and Q-19.

The registry rows `dossier_okc`, `dossier_tulsa` and `dossier_san_diego` (`sources.toml:7503-7535`) are REFUSED with
`compact=False` (`not_contacted`) and `rights=False`. Custody is `REFERENCE`, which is fine. The pilot families have
no registry row at all (`registered_source: null`), hence B6.

The acquisition-queue gates are the same for every target: rights lanes `document_bytes`, `fact_extraction` and
`derived_publication` are all `undetermined`, and `municipal_publication_observed = true` (the non-edict question;
municipal publication is "not auto-CC0", ADR-130 §3).

Terms status: none of the dossier or pilot publishers' site terms were ever captured. That includes okc.gov:
`rights/okcpd_policy.md` and `okc_procurement.md` say *"Terms were NOT fetched verbatim"*, yet those sources were
flipped 2026-09-10 under GL-GATE-03.

### 4.2 Per-target facts

Column key:
- **URL** is the return-pass/`live_targets.toml` URL.
- **research match** compares it with the URL recorded in the acquisition packets and in
  `docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv`: `=` (same), `≠` (different; research URL
  given), `—` (not in the research record at all).
- **VIII** is the Part VIII preflight status from `tasks/src/tasks/data/acquisition_queue.toml`.

| # | doc_id | URL | publisher (SRC) | research match | on a green source? | VIII | decision needed |
|---|---|---|---|---|---|---|---|
| O1 | okc-flock-usage-2026 | `okc.gov/departments/police/flock-safety-lpr-usage` | City of OKC (SRC-001) | **≠** `okc.gov/Services/Public-Safety/Police/Flock-Safety-license-plate-reader-LPR-usage-in-Oklahoma-City` | no | not_assessed | B1, B2 |
| O2 | okc-council-memo-2026-08 | `okc.gov/files/police/flock-council-memo-august-2026.pdf` | City of OKC (SRC-001) | — (packet mentions a "two-page council memo", no URL) | no | not_assessed | B1, B2 |
| O3 | okc-flock-amendment-2026 | `okc.gov/files/police/flock-amendment-1-2026.pdf` | City of OKC (SRC-001) | **≠** `okc.gov/files/assets/city/v/1/police/documents/flock/flock-amendment-august-2026.pdf` (research: "amendment later returned 403") | no | not_assessed | B1, B2 |
| O4 | okc-statute-47-7-606-1 | `oscn.net/…DeliverDocument.asp?CiteID=478582` | OSCN | = | **yes**: `ok_statute` target (`live_targets.toml:311`) | n/a | B5 |
| O5 | okc-ops-manual-5-118 | `okc.gov/files/assets/city/v/2/police/documents/operations-manual-6th-edition-june-15-2026.pdf` | OKCPD | = | **yes**: `okcpd_policy` (`:328`) | n/a | B5 |
| O6 | okc-purchasing-index | `okc.gov/departments/finance/purchasing` | City of OKC | = | **yes**: `okc_procurement` (`:343`; edge WAF may refuse) | n/a | B5 |
| T1 | tulsa-mou-template | `tulsapolice.org/files/camera-integration-mou-template.pdf` | TPD (SRC-002) | — (review depth: "three-page blank MOU") | no | not_assessed (blank template, no parties) | B1, B2 |
| T2 | tulsa-policy-113c | `tulsapolice.org/files/policy-113c-alpr.pdf` | TPD (SRC-002) | — | no | not_assessed | B1, B2 |
| T3 | tulsa-policy-113e | `tulsapolice.org/files/policy-113e-alpr-sharing.pdf` | TPD (SRC-002) | — | no | not_assessed | B1, B2 |
| T4 | tpd-flock-page | `tulsapolice.org/flock-safety` | TPD (SRC-002) | = (primary) | no | not_assessed | B1, B2 |
| T5 | tpd-policies-index | `tulsapolice.org/policies-and-procedures` | TPD (SRC-002) | = (secondary) | no | not_assessed | B1, B2 |
| T6 | tulsa-corridor-safety-guide | `cityoftulsa.org/…/commercial-corridor-safety-guide/` | City of Tulsa Planning | — (a P32.19 lead) | no | not_assessed | B1, B2 |
| S1 | sd-asr-2025-vigilant | `sandiego.gov/sites/default/files/sdpd-annual-surveillance-report-2025.pdf` | SDPD (SRC-003) | **≠** `…/files/2026-02/sdpd-annual-surveillance-report-2025.pdf` | no | not_assessed | B1, B2 |
| S2 | sd-ubicquia-agreement-2023 | `sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf` | City of SD Purchasing (SRC-004) | = (secondary) | no | not_assessed (signature blocks name persons; officer-naming gate applies) | B1, B2 |
| S3 | sd-technology-index | `sandiego.gov/police/data-transparency/technology` | SDPD (SRC-003) | = | no | not_assessed | B1, B2 |
| S4 | sd-pab-index | `sandiego.gov/pab/reports` | SD Privacy Advisory Board (SRC-005) | = | no | not_assessed | B1, B2 |
| S5 | sd-alpr-program-page | `sandiego.gov/police/data-transparency/technology?tech=alpr` | SDPD | **≠** `…/technology/view?tech=Automated+License+Plate+Recognition+(ALPR)` (SRC-027 primary) | no | not_assessed | B1, B2 |
| S6 | sd-alpr-use-policy | `sandiego.gov/sites/default/files/alpr-use-policy.pdf` | SDPD | — (index-linked; recorded 403) | no | not_assessed | B1, B2, **B4** |
| S7 | sd-pab-recommendation-2025 | `sandiego.gov/sites/default/files/pab-final-recommendation-alpr-2025.pdf` | SD PAB (SRC-005) | **≠** `…/files/2026-05/pab-final-recommendation-alpr-2025-asr-00235352xbde34.pdf` (~16 MB, over the byte bound) | no | not_assessed | B1, B2, **B4** |
| S8 | sd-council-memo-2025-12-10 | `sandiego.gov/city-clerk/officialdocs/council-documents` | City Clerk | — (lead) | no | not_assessed | B1, B2 |
| S9 | sd-network-audit-links | (S5 page, metadata only) | SDPD (SRC-027) | ≈ SRC-027 | no | **prohibited_until_review** (`license_plate`, `personal_identifier`) | **B3** (workbook path); link labels are permitted metadata |
| P1 | src-007-target-1 | `oklahoma.gov/dac/about/staff/about-the-uved-program.html` | OK District Attorneys Council (SRC-007) | = | no (no row) | not_assessed | B1, B2, B6 |
| P2 | src-007-target-2 | `oscn.net/…CiteID=478582` | OSCN | = | **yes**: same URL as O4 / `ok_statute` | n/a | B5 |
| P3 | src-006-target-1 | `oklahoma.gov/omes/…/statewide-contracts.html` | OK OMES (SRC-006) | = | no (no row) | not_assessed | B1, B2, B6 |
| P4 | src-006-target-2 | `oklahoma.gov/omes/services/purchasing/solicitations/0900000569.html` | OK OMES (SRC-006) | = | no (no row) | not_assessed | B1, B2, B6 |
| P5 | src-011-target-1 | `information.auditor.ca.gov/reports/2019-118/index.html` | California State Auditor (SRC-011) | = | no (no row) | not_assessed | B1, B2, B6 |
| P6 | src-011-target-2 | `information.auditor.ca.gov/reports/2019-118/surveys.html` | California State Auditor (SRC-011) | = | no (no row) | not_assessed | B1, B2, B6 |

### 4.3 Pre-decision facts (engineering, not operator decisions)

1. **URL reconciliation (NEW-7).** For 5 of the 21 dossier targets, the URL in the return pass or `live_targets.toml`
   differs from the research-recorded URL (O1, O3, S1, S5, S7). Another 7 appear in no research record (O2, T1–T3,
   T6, S6, S8).
   - The live-target rows were authored alongside the hand-authored stand-in documents (F-16;
     `p32.18-okc-dossier/EVIDENCE_PACK.md:37` calls them "reviewed targets").
   - *Inference:* several of these are stand-in URLs. A live pass run as written would record `link_rotted` or 404,
     or would fetch something other than what was reviewed.
   - B1 should bind the reconciled URL list.
2. **The pilot return pass names the wrong family (NEW-8).** `ACQ_PILOT_RETURN_PASS.json` `bounded_questions` asks
   about SRC-010 Sourcewell, which the pilot rejected. The selected incremental families are SRC-006/007 and SRC-011.
   The text is hard-coded at `tasks/src/tasks/acquisition_pilot.py:1336`, and `pilot-check` does not catch it.
3. **Date note.** The DEFERRALS cells for D-P32.18-1 and D-P32.19-1 are dated 2026-10-02 and 2026-10-01, which is
   later than `date -u` (2026-09-30). This is the known F-21 class and is not re-filed here.

### 4.4 What each B decision records, and how it is verified

- **B1 (rights).** For each candidate in `tasks/src/tasks/data/acquisition_queue.toml`, record `rights = {
  document_bytes = {decision="decided", decision_ref="<packet path>", decided_by="<role>", decided_on=<date>,
  basis="…"}, fact_extraction = {…}, derived_publication = {…} }`. The loader is `acquisition.py:915-947`, and a
  `decided` lane without a `decision_ref` fails validation (`:307-313`).
  - Flip `dossier_okc`, `dossier_tulsa` and `dossier_san_diego` via the §2 recipe (compact → `public_terms_only`).
  - The return passes gain `approval_refs`.
  - Verify: `uv run sig-tasks acquisition check` and `uv run sig-tasks acquisition pilot-check` return 0 violations,
    and `uv run sig-connectors gate --source dossier_okc` (likewise `_tulsa` and `_san_diego`) returns LOADABLE.
  - Then re-dispatch each ticket with `live_verification=true` (`OPERATIONAL_READINESS.md:331-334`).
- **B2 (Part VIII).** Record `preflight = { status = "clear" }` per candidate, or `screening_required` with flags,
  with notes naming the screener role and date. Verify with `sig-tasks acquisition check`.
- **B3 (SRC-027).** Under (a), record `preflight.status = "rejected"` for the workbook path, keep the link-label
  metadata path, and update `PART_VIII_PREFLIGHT.json` `safe_aggregate_path.status`. Under (b), open a design ticket.
- **B4 (method).** A per-target bound override is recorded as data on the target row. Under (b), the fetch record
  carries the honest `too_large`/403 outcome.
- **B5 (existing targets).** Nothing to record beyond a note in the return passes that O4, O5, O6 and P2 ride the
  existing green sources.
- **B6 (registry rows).** Three new rows are added in Round 11, each with a packet under
  `docs/build/reports/rights/`. ADR-130: "rows arrive only through the recorded HG-03 decision."

---

## 5. Part C: status re-assessments (proposals only; Stage B/T4 applies them)

| row | cell today | proposed | evidence |
|---|---|---|---|
| **D-SOURCES.12-1** | leads `PARTIAL 2026-09-19` and ends *"nothing actionable remains in this row"* | **DONE 2026-09-26 (P31.13)** | (1) rights half: GL-GATE-07, P26.16 flipped 151 sources and ran 151/151 `ok` (`runs/P26.16.md`); (2) hosted wave tail split to **D-SOURCES.17-1 = DONE 2026-09-24** (DEFERRALS `:247`); (3) the 68 probe-error rows were each retried once, with **0 recovered** (40 link_rotted / 21 non_target / 7 unreachable; `docs/build/reports/catalog_sweep_2026-09-26_retry.json`); (4) `camreg_stalbert_ab` is LOADABLE (§6). The 36-row owed register would drop to 35. |
| **D-SOURCES.9-2** | kind F, "a platform-wide robots refusal is never bypassed"; Appendix B lists it as "Scheduled/external" | **re-scope** to kind P (HG-03 rights) plus an engineering leg, then decide by S2 | GL-GATE-08 (2026-09-18) and ADR-088 made robots non-gating. `connectors/procurement.py:1400-1403` records the Bonfire robots verdict as "disregarded per GL-GATE-08 / ADR-088". P26.17 closed the analogous D-SOURCES.2-4 as "DONE (RESOLVED-BY-GL-GATE-08)" (`runs/P26.17.md` §5) but never revisited 9-2. The **real** blockers are (i) no terms captured (`rights/bonfire.md`: "none — every tenant host refuses all paths", i.e. terms were not fetched *because of* robots) and `compact`/`custody`/`rights` all False; (ii) no parser: `procurement.py:2095-2099` says Bonfire "carr[ies] no reviewed markup contract — a captured body is ContentDrift by construction"; (iii) `/portal` answers with a login redirect (packet). Yield: 2 verified tenants (laurier, columbus). Stale comments: `procurement_portal_tenants.toml:58-60`, `rights/bonfire.md`. |
| **D-SOURCES.9-3** | OPEN; blocker "external" | **later-phase(trigger)** or WONTFIX with re-arm (S3) | GL-GATE-08 does not touch it. The wall is a Cloudflare managed challenge (HTTP 403, `cf-mitigated: challenge`, 10 slugs probed 2026-09-18, `rights/opengov_procurement.md`), and SIG-INGEST-013 (never defeat a challenge) still binds. No owner, no date and no in-repo action exist. As an OPEN row it holds the owed register with nothing anyone can do. Last probe: 2026-09-18. |
| **D-SOURCES.7-1** | `OPEN 2026-09-17`; lists all 5 DOT rows as gated | **PARTIAL**: 4/5 flipped 2026-09-18 (P26.16, GL-GATE-07) and live `ok`; remainder `dot_511_tx` (R3) | §3 R3; `p2616_outcomes.json`; `gate` output in §6 |
| **D-JURIS.2-1** | PARTIAL, listed under "Rights/reviewer" | move it to "Operator credentials/outreach" (or close per R1 a) | §3 R1. Every rights leg is flipped and live; the sole remainder is HG-04 Belgian eID. |

---

## 6. Evidence index (commands run, all read-only)

`date -u` 2026-09-30T16:41:28Z; worktree `/Users/stevenvitali/Eleutheria-next-phase`.
Command: `uv run sig-connectors gate --source <id>` plus `review-status --source <id>`. Fields are
`ingestion_permitted`/`compact`/`custody`/`rights`/`reviewed-by`.

| source | gate | fields | | source | gate | fields |
|---|---|---|---|---|---|---|
| raa_prefectures | LOADABLE | T/T/T/T/T | | camreg_edmonton_ab | REFUSED | F/F/T/F/F |
| decp_fr | LOADABLE | T/T/T/T/T | | camreg_hk_hk | REFUSED | F/F/T/F/F |
| madada | LOADABLE | T/T/T/T/T | | camreg_bellevue_wa | REFUSED | F/F/T/F/F |
| declarationcamera_be | LOADABLE | T/T/T/T/T | | camreg_qldc_au | REFUSED | F/F/T/F/F |
| documentcloud | REFUSED | F/T/T/F/F | | procportal_chicago_il | REFUSED | F/F/F/F/F |
| courtlistener_recap | REFUSED | F/T/T/F/F | | bonfire | REFUSED | F/F/F/F/F |
| dot_511_la / _ga / _al / _md | LOADABLE | T/T/T/T/T | | opengov_procurement | REFUSED | F/F/F/F/F |
| dot_511_tx | REFUSED | F/F/T/F/F | | bidnet_direct / periscope_s2g | REFUSED | F/F/F/F/F |
| camreg_stalbert_ab | LOADABLE | T/T/T/T/T | | dossier_okc / _tulsa / _san_diego | REFUSED | F/F/T/F/F |
| ok_statute / okcpd_policy / okc_procurement / okc_council | LOADABLE | — | | granicus / sourcewell | REFUSED | — |

Other reads:
- `uv run sig-connectors validate` (342 / 236 / 236; OK).
- `uv run sig-connectors review-status` (1 flip-ready: `state_alpr_statute_inventory`, intentionally held as
  seed-only per its notes).
- `uv run sig-tasks acquisition check` and `pilot-check` (0 / 0).
- LEDGER slices: `sed -n 113,191p`, which includes GL-GATE-07/08, P27.2 and P29.3.
- DEFERRALS rows, read by `sed -n <line>p`: 101, 103, 130, 145, 160, 176–179, 210, 247, 581, 643–645, 660.
- The `obligation-event/1` migration anchors for the nine D-JURIS/D-SOURCES rows (`events.jsonl`).

## 7. Findings filed (`findings/incoming/E4.csv`)

- NEW-1: D-SOURCES.7-1 status stale (4/5 flipped).
- NEW-2: D-SOURCES.12-1 leads PARTIAL although it is fully discharged.
- NEW-3: D-SOURCES.9-2's robots blocker is obsolete; the real blockers are rights + parser.
- NEW-4: D-JURIS.2-1 is placed in the rights lane, but the remainder is HG-04 eID.
- NEW-5: OPERATIONAL_READINESS rights-lane text is stale.
- NEW-6: RIGHTS_REVIEW_INDEX.md is a P21.1-era snapshot with broken links.
- NEW-7: dossier live-target URLs diverge from the research record.
- NEW-8: the pilot return pass names SRC-010 Sourcewell.
- NEW-9: GL-GATE-07 execution treated same-class rows differently (worklist membership, not facts).
- NEW-10: 25 flipped sources' packets still show a blank or UNDETERMINED Decision line.
- NEW-11: a flip alone leaves 13 gated rows REFUSED (compact/custody), but the DEFERRALS "how to verify" text implies
  one flip suffices.
