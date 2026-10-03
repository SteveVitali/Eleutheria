# E1 — Contradiction register (spec ⟷ operator decisions / landed behaviour)

Row **E1** of `META_PLAN.md` (Stage P, stream E). Owner R, read-only.
Written 2026-09-30T16:56Z (`date -u`) in the planning worktree at `6266f393` (branch `claude/next-phase-planning`);
chain tip and every control file are those frozen in `baseline/BASELINE.md` (2026-09-30T16:31:55Z; LEDGER sha256
`d459173f…`, COVERAGE_MATRIX `11b77c2c…`, DEFERRALS `b688f3b4…`). Live reads were taken 16:39–16:54Z (listed at the end).
Incoming findings: `findings/incoming/E1.csv` (NEW-1…NEW-15).

**What this is.** A register of every place found where a normative requirement of the canonical spec
(`docs/2_canonical_design_spec.md`, MUST/SHOULD) or the go-live spec (`docs/3_sig_golive_spec.md`) is contradicted
by (i) a recorded operator decision, or (ii) landed code, data, documents or public behaviour. It **describes**;
it does not adjudicate, recommend a disposition, or offer legal advice. Options per contradiction are E2's job;
every "decision needed" below is phrased neutrally, and the decision is the operator's.

**Conventions.**
- Evidence classes (P1): `code` · `recorded-execution` (git / LEDGER / DEFERRALS / readouts) · `live-read` ·
  `operator-statement` · `inference` (labelled wherever used).
- "LEDGER:n" = current `docs/build/LEDGER.md` line n (GATE DECISIONS is lines 113–191).
  "LEDGER^c2055d96:n" = the pre-deletion copy `git show c2055d96^:docs/build/LEDGER.md` (the 53 rows deleted by
  `c2055d96`, 2026-09-18, F-22) — those rows are cited from that copy because they no longer exist at HEAD.
- **⚠ future-dated** marks any record whose stated date is later than the commit that wrote it (F-21, P2). The
  stated date is quoted as written; the git commit time is given beside it.
- Coverage verdicts are read from `docs/build/COVERAGE_MATRIX.csv` (column `verdict`) at the baseline digest.
- Risk class (one primary per entry): **legal** · **safety** · **trust** · **licensing** · **process**.

---

## Summary

21 contradictions. By primary risk class: **process 8 · legal 4 · trust 4 · licensing 3 · safety 2.**

| id | contradiction (short) | primary class | key spec ids | coverage verdict(s) | state today |
|---|---|---|---|---|---|
| E1-01 | Two independent reviewers → sole-maintainer self-concurrence ("waived, not satisfied") | safety | SIG-PUB-008 | MET | operated waiver; spec unchanged |
| E1-02 | Live site presents a fixture "two independent reviewers" hostile-reader review as a real release gate | trust | SIG-UI-042, SIG-PUB-008 | MET | **live, public** |
| E1-03 | Editorial board "distinct from maintainers" asserted in governance doc + API terms; none exists; Part-VIII classes signed off by the operator | safety | SIG-GOV-015 | PARTIAL | live (API terms), public repo |
| E1-04 | Legal home must be fiscal sponsor/nonprofit before launch → individual in personal capacity | legal | SIG-GOV-012, -013; GL-GATE-01 | PARTIAL, PARTIAL | operated; spec unchanged |
| E1-05 | Counsel before launch / "pending counsel" labels → no counsel opinion on file; operator-reported and operator-attested "counsel"; drafted analyses adopted | legal | SIG-LIC-009, R-01, HG-02, GL-GATE-02 | LIC-009 MET | live launch rests on it |
| E1-06 | Conduct deviations need counsel; honour opt-out / rights reservations → "disregard robots entirely" (GL-GATE-08), no counsel | legal | SIG-INGEST-037, §26 r.6–7, SIG-INGEST-046c | 037 MET; 046b/046c MISSING | in production |
| E1-07 | Executable crawler policy, registry and outreach letter still say "honor robots" | process | SIG-INGEST-036 | 036 MET | code/data stale |
| E1-08 | Crawler UA contact URL is on an **unregistered domain** | trust | SIG-INGEST-011, §26 r.1 | MET | in production |
| E1-09 | Stage-0 outreach MUST before connectors → WONTFIX "optional", no ADR; verdicts inconsistent | process | SIG-CONTRIB-012/012a/013, CHART-033, INGEST-029/030a, GOV-024 | MISSING / MET-DIFF / MET / PARTIAL | operated |
| E1-10 | Transparency report + demand-response posture before first demand → no owner, no decision, no row | legal | SIG-SEC-003 | MISSING | public operation without it |
| E1-11 | Unresolved rights fail closed / counsel on EU DB right → blanket "err on the side of approving" incl. non-US DB-right risk | licensing | SIG-LIC-003/004/009, HG-03 | MET, MET, MET | 21,682 rows public |
| E1-12 | Upstream attribution structural in UI/API/exports → public map and downloads omit required attribution | licensing | SIG-CONTRIB-020, API-004, EXPORT-006 | MET ×3 | **live, public** |
| E1-13 | ODbL compartment separation → "publish it all together" / combined `/map/points.json` | licensing | SIG-EXPORT-005, LIC-004a/006 | MET | resolved 2026-09-27; residual counsel |
| E1-14 | Independent human evaluation → deferred four times; agent/LLM-made gold labels; "human-verified" public wording | trust | SIG-EVAL-001…007, IDENT-027, §55.9 | PARTIAL/MET/MISSING | live disclosure mixed |
| E1-15 | Moderated usability study before "contributor system complete" → WONTFIX; verdict MET | process | SIG-CONTRIB-003, UI-001 | MET, PARTIAL | operated |
| E1-16 | "Scope never waives the full criterion set" → MET on reduced/staging scope | process | SIG-TRUST-009/010, DOS-002…005, FIND-006 | MET | no production exposure |
| E1-17 | "An agent must not sign" → template line removed at signing; agent-authored scope; future date | process | SIG-TRUST-009; ticket 190/195 | — | recorded |
| E1-18 | Go-live spec: "nothing publishes without the two-reviewer + counsel gates" → go-public 2026-09-16 with both skipped; gate records never reconciled | process | GL goal 5, GL-GATE-01/05, HG-01/02/11 | — | stale records |
| E1-19 | Normative spec/ADR/manifest text asserts events dated 2026-10-19/20 (future) | process | SIG-TRUST-008; §55.1/55.8/55.9 | — | in spec text |
| E1-20 | First release "narrowly excellent at U.S. ALPR" → national/international all-camera launch | trust | SIG-CHART-025 | MET-DIFFERENTLY | live |
| E1-21 | Software Heritage deposit of code MUST → declined "repo stays private"; repo is now public | process | SIG-EVID-019, GOV-022 | PARTIAL, PARTIAL | rationale lapsed |

**Top 5 by consequence** (agent judgement, labelled `inference`): E1-02 (false public claim, now) → E1-05 (every
public layer rests on no counsel opinion, and the promised "pending counsel" label is absent) → E1-06 with E1-08
(the crawler's legal posture changed without the counsel step the spec names, and its self-identification points
to a domain anyone can register) → E1-12 (required attribution missing from live public data under attribution
licences) → E1-04 (personal exposure of an individual legal home while publicly live). E1-11 is next.

**Contradictions the operator may not be aware of** (no operator decision on record touches them): E1-02, E1-08,
E1-10, E1-12, the absent GL-GATE-02 label (E1-05 b), the stale executable policy (E1-07), the governance-doc and
API-terms editorial-board/counsel claims (E1-03), the latent officer-naming bypass in the web gate (E1-01 c), the
GL-GATE-07 execution beyond its recorded rule (E1-11 c), and the way three decisive records convert tentative or
instructional operator words into decisions/attestations (cross-cutting note X-1).

---

## Entries

### E1-01 — SIG-PUB-008 two independent reviewers vs the sole-maintainer waiver · **safety**

**Spec.** `docs/2_canonical_design_spec.md:6324-6325`: *"**SIG-PUB-008 (MUST).** **Two independent reviewers MUST
concur in writing.** Disagreement defaults to **no-publish**. The decision, its reasoning, and its reviewers MUST be
recorded."* Go-live `docs/3_sig_golive_spec.md:92`: HG-11 = *"two reviewer **roles** + written concurrence workflow
(SIG-PUB-008) + live takedown/corrections contact"*, blocking *"LIVE.2 publish"*.

**Contradicting decisions** (`operator-statement` as recorded; `recorded-execution`).
- LEDGER^c2055d96:164 (2026-09-16, go-public): *"**HG-11 SKIPPED-BY-OPERATOR** (sole-maintainer posture; no second
  reviewer, no concurrence — `D-P21.4-2`)"*.
- LEDGER^c2055d96:165 (2026-09-16): *"**HG-11 RESOLVED-BY-OPERATOR** — operator filled both reviewer roles personally
  and recorded written concurrence (`concurrence.md`); SIG-PUB-008 independence **waived, not satisfied** —
  officer-naming stays default-no-publish."*
- LEDGER:154 (2026-09-22, P27.8): *"**HG-11** (reviewer concurrence) — answer: **Carry forward sole-maintainer
  posture.** Consequence: proceed on the recorded waiver (D-P21.4-2); a second independent reviewer + written
  concurrence stays owed post-launch, and the published surface makes no two-reviewer claim."*
- `docs/tickets/DEFERRALS.md:40` D-P21.4-2: *"DONE 2026-09-16 — operator-resolved under sole-maintainer posture … the
  SIG-PUB-008 *independence* requirement is **waived by explicit operator decision**, not satisfied"*.
- `docs/build/reports/okc/concurrence.md:17-19`: both rows *"Steven Vitali"*; row 2 *"**not independent**;
  independence waived by operator"*.
- ADR-145 (2026-09-28) `:118-122` keeps the text: *"the requirement stands as the bar; the operated sole-maintainer
  posture is a recorded operator waiver … and the published surface makes no two-reviewer claim. A deviation in
  *operated state*, not in spec text."* No ADR waives SIG-PUB-008.

**Compensating controls (verified in code).**
(a) `policy/src/policy/officer.py:82-90` `_concurrence_ok` requires ≥2 *distinct* `reviewer_id`s among reviewers
flagged `independent=True` with a written rationale, else refuses. (b) The only non-test caller,
`connectors/src/connectors/okc_documents.py:231-240`, defaults to all-False prongs and no reviewers, so any
person-naming predicate raises `OfficerNamingRefused`. `inference`: the check trusts the caller-declared
`independent` flag and distinct id strings; it cannot detect one person entered under two ids.
(c) **Gap (latent):** the web build gate `web/src/lib/publication.ts:36-40` publishes a *public-employee name*
whenever both jurisdictions permit it (`US: true`, SIG-PUB-017) and never evaluates the SIG-PUB-007 prongs or the
SIG-PUB-008 concurrence; the OKC fixture `web/src/lib/dossier-fixture.ts:226-233` renders an "Approving official"
row with a named police chief under that rule. Not observed on the live site (`/dossier/okc/` → 404, 16:39Z), so
latent (`code` + `live-read`).

**Coverage.** SIG-PUB-008 **MET** (evidence `tests/unit/test_policy_officer.py:4`) — the verdict records the gate,
not the concurrence the requirement names. `docs/risk_register.md:24` (RISK-P0-05) still describes the control as
*"no publish without two independent, written, concurring reviewers"*.

**Public surface.** The recorded premise "the published surface makes no two-reviewer claim" is **false** on the
live site — see E1-02.

**Decision needed.** Whether SIG-PUB-008 is amended in spec text (a recorded waiver with its compensating control
and revisit trigger) or kept as an owed obligation with a sourcing plan for a second independent reviewer; and
which coverage verdict records the chosen state.

---

### E1-02 — SIG-UI-042 hostile-reader review: a fixture presented live as two independent reviewers · **trust** · NEW-1

**Spec.** `:5997-6001`: *"**SIG-UI-042 (MUST).** Each dossier template version MUST receive a recorded
**hostile-reader review** before release: two reviewers independently read a real rendered dossier adopting the
stance of the documented organization's counsel, log every sentence they would challenge, and sign off. … Release
is blocked until every finding is dispositioned."*

**Contradicting landed behaviour** (`live-read` 2026-09-30T16:42Z, `code`, `recorded-execution`).
- `https://surveillancegraph.org/editorial-standards/` (200) renders: *"Before a dossier template version is
  released, two reviewers independently read a real rendered dossier adopting the stance of the documented
  organization's counsel … Dossier reviewed /dossier/oklahoma-city/ Reviewers Reviewer A (counsel stance); Reviewer
  B (counsel stance) Review date 2026-08-19 Release status Releasable — every finding dispositioned"*.
- The data is a constant: `web/src/lib/corrections-methodology-fixture.ts:201-202`
  (`reviewers: ["Reviewer A (counsel stance)", "Reviewer B (counsel stance)"], review_date: "2026-08-19"`), served in
  every mode by `web/src/lib/data.ts:854-856` (`getHostileReaderReview()` returns the fixture).
  `docs/governance/hostile-reader-review-dossier.md` table: *"Reviewers | Reviewer A (counsel stance); Reviewer B
  (counsel stance) — two independent"*, *"Dossier reviewed | `/dossier/oklahoma-city/` (a real render, not a mock)"*.
- Introduced by `2b361f18` (2026-09-08, P15.5, trailer `Co-Authored-By: Devin`). The stated review date
  (2026-08-19) precedes the repository's first code commit (`10be37ce`, 2026-08-26). `/dossier/oklahoma-city/` → 404
  (16:49:40Z).
- It contradicts the operator record that no independent reviewer exists (E1-01) and the premise "the published
  surface makes no two-reviewer claim" (LEDGER:154; ADR-145:118-122; `PUBLICATION_CHECKLIST.md:163`).

**Compensating controls.** `web/src/lib/editorial.ts::assertReviewReleasable` checks that findings are
dispositioned — it cannot check that reviewers exist. None found for the authenticity of the record.

**Coverage.** SIG-UI-042 **MET** (`web/tests/unit/editorial.test.ts:77`).

**Public surface.** Live, public, unlinked from any caveat; the same site elsewhere says "Not yet human-reviewed".

**Decision needed.** What the page should present about hostile-reader review given the recorded reviewer
reality, and how SIG-UI-042 is dispositioned (performed, waived with rationale, or owed).

---

### E1-03 — SIG-GOV-015 editorial board distinct from maintainers · **safety** · NEW-7

**Spec.** `:6537-6540`: *"**SIG-GOV-015 (MUST).** An **editorial board** MUST exist for contested claims,
officer-naming decisions (§43.4), and sensitivity classifications, distinct from the technical maintainers. These
are editorial judgments and should not be made by whoever happens to hold commit access."*

**Contradicting decisions / documents.**
- Sole-maintainer posture (E1-01): one person holds maintainer, both reviewer roles, legal home and takedown contact
  (`docs/governance/governance-and-code-of-conduct.md:8-9, 26-33`).
- LEDGER:181-191 (2026-09-22, P27.2), operator verbatim: *"I'd prefer to just err on the side of signing off on
  these now"* — *"operator SIGNS OFF on the Part-VIII-sensitive classes (`facial_recognition_world_map`,
  `pathways_rtcc_federation`, `pathways_acoustic_drone_location`, officer/person-naming) for publication now"*.
  Sensitivity classification is a board function under GOV-015.
- The same governance doc asserts the opposite of the operated state: `:55-57` *"An **editorial board exists,
  distinct from the technical maintainers.**"*; `:66` *"The board's two-reviewer concurrence is the human
  counterpart…"*. It also still says (`:21-22`) *"Until then the project runs at Finish-line A (deployed,
  access-restricted), not a public launch."* (stale since 2026-09-16).
- Live API terms (`GET https://sig-api-e5ctyx36jq-uc.a.run.app/terms`, 16:42Z): *"referral to the SIG editorial
  board and, where applicable, to counsel."*

**Compensating controls.** Mechanical Part VIII invariants recorded at LEDGER:185-189 and enforced in code (no
person/plate fields; tier coordinate reduction; `_concurrence_ok` refuses person-named claims — E1-01 a/b).

**Coverage.** SIG-GOV-015 **PARTIAL** (*"claimed … but no code or test evidence"*).

**Public surface.** API `/terms` names an editorial board and counsel; the repository is **public**
(`gh repo view` → `visibility: PUBLIC`, 16:44:38Z), so the governance doc's claims are public too.

**Decision needed.** Whether GOV-015 is amended to the operated single-person model (with what compensating
control for officer-naming and sensitivity decisions), or kept owed with a plan to constitute a board; and whether
the governance doc and API terms should state the operated reality meanwhile.

---

### E1-04 — SIG-GOV-012 legal home (fiscal sponsor / nonprofit) vs an individual · **legal**

**Spec.** `:6523-6526`: *"**SIG-GOV-012 (MUST).** Before public launch, SIG MUST establish a legal home — a fiscal
sponsor or its own nonprofit — and document what it implies for liability, donations, and legal defence. Operating
a project with this threat profile as an unincorporated individual effort exposes contributors personally."*
`:6528-6529` SIG-GOV-013: legal-defence resources *"**before** they are needed"*. Phase-0 deliverable 6 (`:6831`).
Go-live `:45` GL-GATE-01: *"a **real legal home remains a human action before the actual public cutover**"*.
`docs/risk_register.md:34` RISK-P0-13: *"Tracked as a launch-blocking prerequisite; no public launch without it"*.

**Contradicting decisions.**
- LEDGER^c2055d96:155 (2026-09-15): *"**NAMED — Steven Vitali (individual maintainer, personal capacity).**"* with
  the note *"Interim personal-name home (honest scope note in the doc: personal exposure; **not** legal advice; a
  durable entity + HG-02 counsel recommended before real public exposure)."*
- LEDGER^c2055d96:164 (2026-09-16): *"**GO — executed.**"* (go-public).
- LEDGER:153 (2026-09-22, P27.8): *"**HG-01** (publication go / legal home) — answer: **Carry forward, proceed.**
  Legal home stays *Steven Vitali, individual maintainer*"*.
- DEFERRALS:39 D-P21.4-1 → *"DONE 2026-09-15"*. No ADR records the deviation (`grep -il "legal home" docs/adr` → 0).

**Compensating controls.** Honest scope note in the governance doc (`:16-22`); contributor-safety design ("not
holding data about them", SIG-SEC-002). SIG-GOV-013 unmet (no legal-defence resources identified; coverage PARTIAL).

**Coverage.** SIG-GOV-012 **PARTIAL**; SIG-GOV-013 **PARTIAL**.

**Public surface.** The live site names no legal home, maintainer or contact (0 hits for "Vitali", "contact",
"@" on captured pages); the public repo names the individual.

**Decision needed.** Whether GOV-012/013 are amended to record the individual legal home as the chosen posture
(with rationale and revisit trigger), or kept owed with a plan (entity / fiscal sponsor / legal-defence resources);
this is a question on which the spec itself says counsel is appropriate.

---

### E1-05 — Counsel requirements vs operator-reported, operator-attested and drafted "counsel" · **legal** · NEW-3, NEW-9

**Spec.** `:6196-6200`: *"**SIG-LIC-009 (MUST).** The following MUST be referred to counsel before launch and MUST
appear in the risk register: whether API responses returning device-linked claims constitute distribution of a
Derivative Database under **ODbL clause 4.4(b)**; … the correct regional-cut unit; and the EU sui generis database
right for the international phase."* Risk table `:7231` R-01 mitigation: *"counsel on §42.3 residuals"*. Part VIII
preamble `:6050-6051`: *"it marks explicitly where counsel is required."* Go-live `:80` goal 5: *"nothing publishes
without the two-reviewer + counsel gates"*; `:93` HG-02 *"counsel opinion recorded for ODbL 4.4(b) (RISK-P0-01),
officer-naming gate, publication tiers, Part VIII"*; `:46` GL-GATE-02: *"**Labelled in every artifact as
"operator/engineering disposition pending counsel; counsel review recommended before real public exposure."**"*

**Contradicting decisions** (chronological; all `recorded-execution` of `operator-statement`s).
1. 2026-09-09 GL-GATE-02 (LEDGER^c2055d96:146): *"ENGINEERING DISPOSITION, publish-permitting, NOT a legal opinion"*.
2. 2026-09-15 (LEDGER^c2055d96:162): five held sources *"**APPROVED by counsel** (operator-reported)"*; registry now
   carries `rights_reviewed_by = "counsel (HG-02)"` on 5 rows.
3. 2026-09-16 (LEDGER^c2055d96:163): derived-facts publication *"**APPROVED by counsel** (operator-reported: "ok to go
   forward")"* → ADR-086.
4. 2026-09-16 (LEDGER^c2055d96:165): *"**HG-02 remainder RESOLVED-BY-OPERATOR** — four scoped questions answered by
   operator-adopted drafted analyses (`docs/governance/publication-opinion-drafts.md`, explicitly not legal advice;
   counsel may supersede)"*; DEFERRALS:71 D-LEGAL.1-1 → *"DONE 2026-09-16 — **resolved by operator-adopted drafted
   analyses** (NOT counsel)"*. The drafts file was added in `b542f236` (trailer `Co-Authored-By: Devin`).
5. 2026-09-22 (LEDGER:155): *"**HG-02** (counsel disposition) — answer: **Carry forward interim engineering
   dispositions.** … Provided: no counsel opinion (interim engineering disposition only)."*
6. 2026-09-24 (LEDGER:137): *"counsel says it's okay and we can publish it all together"* — recorded as *"Counsel
   clearance is operator-reported 2026-09-24 — no dated written opinion is on file yet"*.
7. 2026-09-24 (LEDGER:134; `readouts/ACCEPT-R8.md:48`): *"ok please sign docs/build/readouts/ACCEPT-R8.md for me or
   whatever, I approve everything. And likewise counsel opinion should just be to give us the green light."* →
   DEFERRALS:391 D-P30.3-COUNSEL *"DONE 2026-09-24 — **CLOSED BY OPERATOR ATTESTATION, no written opinion filed
   (operator's choice).** … i.e. the operator attests counsel cleared public release"*. (See X-1: the quoted words
   are instructional in form; the attestation reading is the recorder's.)

**Landed behaviour.**
- (a) No counsel-authored document exists in the repo (DEFERRALS:391 says so).
- (b) **The GL-GATE-02 label is absent** (NEW-3): `grep -rni "pending counsel\|engineering disposition"` over
  `exports/src web/src api/src ops/src policy/src` → only a comment in `policy/src/policy/data/licenses.toml:105`;
  the public release manifest (`…-sig-public/manifest.json`, sha256 `717aeb44…`, 16:47:15Z) contains 0 occurrences
  of "counsel"/"pending"; 0 occurrences on the captured live pages. `readouts/HUMAN-H2.md:17-18` nonetheless states
  *"Every artifact that relies on this is labelled …"*.
- (c) `connectors/src/connectors/data/api_allowlist.toml`: 72 entries, all `counsel_reviewed = false`; ADR-083:23
  *"Counsel (HG-02) should still confirm it before *real public exposure*"* — public exposure began 2026-09-16.

**Compensating controls.** Structural safeguards (per-compartment licences, `assert_separated`/public-clean guard,
tier-0 role, officer-naming gate); the drafts file's banner *"NOT legal advice"* (`publication-opinion-drafts.md:3`);
`RISK-P0-01` kept open in the risk register.

**Coverage.** SIG-LIC-009 **MET** (*"design recorded in ADR (ADR-011)"*) — the MUST is a referral to counsel.

**Public surface.** API `/terms` refers some violations "to counsel"; nothing public discloses that publication
rests on no counsel opinion.

**Decision needed.** Whether the counsel requirements (SIG-LIC-009, R-01, HG-02, GL-GATE-02 labelling) are amended
to the operated basis — with the basis stated in public artifacts — or kept owed with a plan to obtain real counsel;
and how operator-reported counsel clearances are to be recorded (evidence required, or recorded as unverified).
Real counsel is required to answer the underlying questions; nothing here is legal advice.

---

### E1-06 — Crawler conduct: counsel for deviations, honour opt-out, rights reservations vs GL-GATE-08 · **legal** · NEW-15

**Spec.** `:4494-4497`: *"**SIG-INGEST-037 (MUST).** Rule 4 is not merely ethical. … The policy is also a **legal
posture**, and deviating from it is an ADR-level decision requiring counsel, not an engineering judgment."* §26
rule 6 `:4490` *"**Ask first** where the compact is unresolved…"*; rule 7 `:4491` *"**Honor opt-out** immediately and
record it in the compact."* `:4285-4290` SIG-INGEST-046c: *"An **affirmative machine-readable rights reservation**
MUST be honoured as a refusal and recorded on the rights record. One ecosystem project combines `Content-Signal:
ai-train=no`, explicit AI-crawler disallows, and an **EU DSM Article 4 reservation** — a formal opt-out with legal
effect in the EU."* (Rule 2 and SIG-INGEST-012/-046b were already amended to the landed posture by ADR-145, `:3502-3516`,
`:4476-4485`, `:4276-4283` — those are no longer contradictions in text.)

**Contradicting decision.** LEDGER:166-173 (2026-09-18) **GL-GATE-08**, verbatim: *"I also wonder if we should
disregard robots.txt-gated sources and crawl them anyway"* → *"operator decision: **disregard robots entirely** —
robots verdicts stop gating fetches. Recorded with the presented risks (weakened never-bypassed audit property;
egress-IP block exposure on shared vendor infra)."* Executed by ADR-088 (Date 2026-09-19): no counsel involvement;
revisit trigger *"**Counsel objects** to disregarding robots verdicts"*. Ticket `P26.17__robots-non-gating.md:13`:
*"DISPOSITION RECORDED — GL-GATE-08 is the operator's decision; risks presented and accepted."* ADR-145 `:123-124`
reads SIG-INGEST-037 as rule-4-only: *"`SIG-INGEST-013`/`SIG-INGEST-037` … — unchanged by ADR-088"*. Earlier:
ADR-083 (2026-09-15) API carve-out *"Firm decision, not pending-counsel"*.

**Landed behaviour** (`code`). `connectors/src/connectors/net.py:382-393`: on `disallowed`/`unretrievable` the fetch
proceeds and is stamped `robots_disregarded`. No connector inspects `Content-Signal` or a TDM/Article-4
reservation at fetch time: `policy.crawler.parse_content_signal`/`content_signal_permits_training`
(`policy/src/policy/crawler.py:89-105`) are called only from `tests/unit/test_policy_crawler.py`.

**Recorded risk presentation** (NEW-15, `recorded-execution`): the only risks recorded as presented are the two
operational ones quoted above; the SIG-INGEST-037 counsel requirement, rule 7 and the SIG-INGEST-046c/EU
reservation dimension do not appear in the GL-GATE-08 record or the P26.17 gate block.

**Compensating controls.** `ingestion_permitted` loader gate (HG-03) — itself blanket-approved (E1-11); no-
circumvention fail-closed (`assert_no_circumvention`, SIG-INGEST-013 challenge handling); per-URL
`robots_disregarded` provenance; conservative rate limits.

**Coverage.** SIG-INGEST-037 **MET** (*"implemented; no id-linked automated test"*); SIG-INGEST-046b **MISSING**;
SIG-INGEST-046c **MISSING**; SIG-INGEST-012/-036 **MET**.

**Public surface.** Nothing on the captured pages mentions robots/crawler posture; see E1-08 for the crawler's
self-identification.

**Decision needed.** Whether SIG-INGEST-037's "requiring counsel" is read as covering the robots decision (an
interpretive question the record currently answers only in ADR-145's narrow reading), and whether GL-GATE-08 is
confirmed with counsel, amended in spec text with that stated, or re-scoped; and whether rule 7 / SIG-INGEST-046c
need a runtime control now that robots no longer gates.

---

### E1-07 — Executable policy, registry and outreach letter still state "honor robots" · **process** · NEW-6

**Spec.** `:4472-4473`: SIG-INGEST-036 — SIG MUST *"adopt and publish a Crawler Conduct Policy binding on every
connector"*; rule 2 as amended (`:4476-4485`) says verdicts *"do not gate"*.

**Contradicting landed artifacts** (`code`).
- `policy/src/policy/crawler.py:9-11` docstring: *"**Rule 2 — honour robots.txt and content-signal headers.** Where
  robots.txt is unretrievable, permission is *not* granted (SIG-INGEST-012)."*; `robots_permits` (`:47-56`) still
  defaults closed (unused by the fetch path after ADR-088).
- `policy/src/policy/data/crawler_conduct.toml:14-17` (`version = "2026-08-26"`): rule 2 *title = "Honor
  robots.txt"*, *text = "Honor robots.txt, … Where robots.txt is unretrievable, permission is NOT granted"*.
  This table is what `policy.crawler.conduct_rules()` serves as "the" policy.
- `connectors/src/connectors/data/sources.toml`: `robots_policy = "honor"` on 235 of 236 `ingestion_permitted`
  rows (1 `not_applicable`). ADR-088 kept these *"accurate declarations of posture"*.
- `docs/governance/stage0-outreach-letter.md:40`: *"We honour robots/ToS and conservative crawler conduct (§26)"*.

**Contradicting decision.** GL-GATE-08 / ADR-088 (E1-06).

**Coverage.** SIG-INGEST-036 **MET**. **Public surface.** Public repo only. **Decision needed.** Whether these
artifacts are brought into line with whichever E1-06 outcome is chosen, and which artifact is the published policy
of record.

---

### E1-08 — Crawler user-agent contact URL on an unregistered domain · **trust** · NEW-2

**Spec.** `:3498-3500` SIG-INGEST-011: *"…a documented crawler UA carrying a contact URL…"*; §26 rule 1 `:4475`:
*"**Identify.** A descriptive UA with a contact URL and an explanation page. No spoofing."*

**Landed behaviour** (`code`, `live-read` 16:43:36Z).
`connectors/src/connectors/net.py:61` `DEFAULT_CONTACT_URL = "https://sig-project.org/data-collection"` (also
`connectors/src/connectors/transports/httpx_transport.py:66`, `tasks/src/tasks/maproulette.py:219`,
`connectors/src/connectors/data/procurement_portal_tenants.toml:45`). `nslookup sig-project.org` → **NXDOMAIN**;
`whois sig-project.org` → *"Domain not found."*; `curl` → *"Could not resolve host"*. The live site has no
explanation page either (`https://surveillancegraph.org/data-collection` → 404). The test only checks the string
(`tests/connectors/test_net.py:19-23`). LEDGER:395 (2026-09-15) records changing the path from `/crawler` to
`/data-collection` to avoid a WAF 406; the domain itself was never recorded as registered.

**Contradicting decision.** None — no operator decision on record (operator likely unaware).
`inference`: an unregistered domain in every production request can be registered by a third party, who would
then receive site operators' complaints/opt-outs intended for SIG.

**Coverage.** SIG-INGEST-011 **MET**. **Public surface.** Every hosted fetch (79 scheduler jobs) sends this UA.

**Decision needed.** Which domain/page serves as the crawler's contact and explanation page, and whether the
registration question (acquire vs. change) is an operator action.

---

### E1-09 — Stage-0 outreach MUST vs WONTFIX "optional" (no ADR) · **process**

**Spec.** `:5367-5371` *"**SIG-CONTRIB-012 (MUST).** Before any connector is written for an ecosystem project, SIG
MUST have attempted contact and recorded the outcome …"*; `:5373-5374` SIG-CONTRIB-012a (SHOULD); `:5385` SIG-CONTRIB-013
(archival succession offer, MUST); `:685-688` SIG-CHART-033; `:3720-3722` SIG-INGEST-029; `:3740-3744` SIG-INGEST-030a
(*"Outreach remains a **Phase 0 deliverable** even though the data is already accessible — … ShareAlike attribution
must be agreed …"*); `:6583` SIG-GOV-024; Phase-0 deliverable 4 `:6828-6829`. Go-live `:95` HG-04.

**Contradicting decision.** LEDGER^c2055d96:165 (2026-09-16): *"**HG-04 outreach SKIPPED-BY-OPERATOR** (all three
sets — `D-P21.1-2`, `D-JURIS.2-2`, `D-CCOPS.1-2` → WONTFIX)"*. DEFERRALS:36/103/118: *"WONTFIX 2026-09-16 —
SKIPPED-BY-OPERATOR: operator elected to skip Stage-0 outreach entirely (optional, not a read-surface or correctness
prerequisite)"*. The spec marks it MUST; no ADR waives it (only ADR-063:28 notes the P21.1 run shipped with HG-04
skipped).

**Landed behaviour.** All 236 permitted sources are `compact_status = "public_terms_only"`; ecosystem connectors
run (e.g. Eyes on Flock → `sig_portal` CC-BY-SA compartment on the live map, `/map/style.json` 16:47:32Z);
`docs/build/reports/STAGE0_OUTREACH_RECORD.md:17` Eyes on Flock `public_terms_only`.

**Compensating controls.** Honest `not_contacted`/`public_terms_only` postures in the (public) registry; loader
gate. No live site or API surface shows compact posture (OpenAPI has no source path, 16:53:07Z).

**Coverage (inconsistent across one obligation).** SIG-CONTRIB-012/012a **MISSING**; SIG-CONTRIB-013 **PARTIAL**;
SIG-CHART-033 **MET-DIFFERENTLY** (in the HG-14 ACCEPTED list signed 2026-09-08 as *"satisfied by design"*,
`CAPSTONE_CLOSURE.md:79`); SIG-INGEST-029 **MET**; SIG-INGEST-030a **MET**; SIG-GOV-024 **PARTIAL**.

**Decision needed.** Whether Stage-0 outreach is amended out of the MUST set (with rationale, including the
030a ShareAlike-attribution and 013 succession points) or kept owed with a plan; and one consistent verdict for the
five ids that encode it.

---

### E1-10 — SIG-SEC-003 transparency report and demand-response posture: unowned · **legal** · NEW-5

**Spec.** `:6436-6438`: *"**SIG-SEC-003 (MUST).** SIG MUST publish a transparency report covering legal demands
received, complied with, and refused, and SHOULD maintain a warrant canary. The response posture for demands
directed at SIG MUST be documented **before** the first demand arrives."* Threat model `:6421`: *"Legal process
against SIG | Compel contributor identity | … transparency reporting"*.

**Contradicting landed state.** Public since 2026-09-16 with no documented demand-response posture (governance
docs mention only intake categories; `grep -i "subpoena|warrant"` → one line, `contributor-safety.md:18`). **No
operator decision** exists: 0 hits for "SEC-003"/"warrant canary" in LEDGER, DEFERRALS, BACKLOG and
OPERATIONAL_READINESS; COVERAGE routes it to *"P20.1:backlog"* but BACKLOG.csv has no row
(`CAPSTONE_GAP_ANALYSIS.md:236` lists it MISSING).

**Partial controls.** `/corrections/` (live 16:42Z) carries a *"Transparency report Total requests recorded: 0 . By
category … legal_demand: 0"* section (SIG-GOV-011 counts). `inference` from F-03 and the capture: the live `/dispute/`
page contains no `<form>`, `<button>` or `<input>` and no contact address appears on any captured page, so the
counts are structurally zero.

**Coverage.** **MISSING**. **Public surface.** A "Transparency report" heading exists; it covers intake counts only.

**Decision needed.** Whether SEC-003 is owned now (posture documented, report scoped), amended, or recorded owed
with an owner — it currently has none.

---

### E1-11 — Rights review / fail-closed rights vs GL-GATE-07 blanket approval · **licensing** · NEW-13

**Spec.** `:6070-6073` *"**SIG-LIC-004 (MUST).** A source with unresolved rights MUST be `UNDETERMINED`, which MUST
**fail the export gate closed.** … (Discharges OL-14.2-02 — "do not discover after launch that a key dataset cannot
legally be redistributed.")"*; `:6066-6068` SIG-LIC-003 (`redistributable` never inferred); `:6196-6200` SIG-LIC-009
(EU sui generis database right → counsel before launch). Go-live `:94` HG-03: *"reviewer reads the 27 packets …
sets `ingestion_permitted=true` + review metadata"*. ADR-094 (spec `:9122`): *"evidenced rights resolution, never
gate bypass"*.

**Contradicting decisions.** LEDGER:156-164 (2026-09-18) **GL-GATE-07**, verbatim: *"We should ungate the
D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of approving
them"* — *"INCLUDING non-US rows: the operator explicitly accepts the sui generis database-right risk on EU/UK/AU
factual compilations after being shown the US/EU split. … reviewer `maintainer (delegated)`"*. Re-applied
LEDGER:174-180 (2026-09-22, *"Approve under GL-GATE-07"*) and LEDGER:143 (2026-09-23, P29.3). GL-GATE-06
(2026-09-16, LEDGER^c2055d96:166) is a narrower blanket for clear public licences.

**Landed behaviour** (`code`, `live-read`). Registry: 236 permitted rows; 94 `LicenseRef-OperatorAccepted-DBRight`
(93 reviewed 2026-09-18); 231 reviewed by `maintainer (delegated)`, 5 by `counsel (HG-02)` (operator-reported,
E1-05). Execution beyond the recorded rule (NEW-13): the recorded rule is *US → PublicRecord; non-US → DBRight*,
but `camreg_und_001` (an *"ArcGIS community-published"* registry, jurisdiction `sig.unresolved`, rows at New Jersey
coordinates) was flipped as *"non-US/unresolved-jurisdiction"*; `camreg_calgary_ab` was flipped although its notes
say the terms *"could not be captured verbatim this run"*. Public: `operator_accepted/sites.{csv,geojson,jsonl,
jsonld,parquet,pmtiles,sqlite}` — **21,682 rows** downloadable (manifest 16:47:15Z) — and the `sig_operator_accepted`
tile source on `/map/`.

**Compensating controls.** Per-compartment separation; UNDETERMINED still fails closed (but these rows are no
longer UNDETERMINED); `LicenseRef-OperatorAccepted-DBRight` names the basis honestly in the manifest.

**Coverage.** SIG-LIC-004 **MET**, SIG-LIC-003 **MET**, SIG-LIC-009 **MET**.

**Decision needed.** Whether operator risk-acceptance is a recognised rights basis in spec text (amend SIG-LIC-004/
009 and HG-03) or the flips return to evidenced per-source review; and whether "unresolved jurisdiction" and
"terms not captured" rows fall inside the recorded GL-GATE-07 rule.

---

### E1-12 — Structural upstream attribution vs public map and downloads · **licensing** · NEW-4

**Spec.** `:5507-5509` *"**SIG-CONTRIB-020 (MUST).** Attribution reciprocity MUST be structural: every claim's
upstream is named in the UI, in API responses, and in exports. Aggregate acknowledgement on an About page is not
sufficient"*; `:5576-5578` SIG-API-004; `:5668-5669` SIG-EXPORT-006 (per-row rights provenance).

**Landed behaviour** (`live-read`; no operator decision touches it).
- `/map/` (16:50:42Z) island props: *"attribution":"© OpenStreetMap contributors (ODbL) · Surveillance data © SIG
  contributors"* over 12 compartments incl. `OGL-3.0`, `OGL-Canada-2.0`, Ottawa/Peel/St Albert ODL, `CC-BY-SA-2.0`,
  `LicenseRef-OperatorAccepted-DBRight`; `/map/style.json` `sig_operator_accepted` attribution *"Surveillance data ©
  SIG contributors (LicenseRef-OperatorAccepted-DBRight)"*.
- Public downloads, first ~400 KB of each `sites.csv` (16:53:44Z): `rights_attribution` **empty** and
  `rights_terms_url` empty while `rights_attribution_required = True` in `operator_accepted` 834/834,
  `ogl_uk3` 870/870, `public_record` 885/885, `dot511_ccbysa2` 537/537; present in `ccby3` 771/771 and
  `osm_physical` 858/858. The registry holds attribution text for such sources (e.g. `camreg_und_001`
  `rights.attribution`), so it is dropped between registry and export (`inference`).
- `datapackage.json`: licences only, no source attribution; its licence URLs for `LicenseRef-OperatorAccepted-DBRight`
  and `OGL-3.0` return **404** at spdx.org (16:54:00Z; the SPDX id for OGL v3 is `OGL-UK-3.0`).
- Not inspected: per-feature properties inside the PMTiles.

**Coverage.** SIG-CONTRIB-020 **MET**, SIG-API-004 **MET**, SIG-EXPORT-006 **MET**.

**Decision needed.** Whether this is treated as a defect to fix within the existing requirements (no spec change),
and whether a licence-compliance review of the live release is wanted before the next publish.

---

### E1-13 — ODbL compartment separation vs "publish it all together" · **licensing** (resolved in operated state; residual)

**Spec.** `:5664-5666` *"**SIG-EXPORT-005 (MUST).** OSM-derived physical assets MUST ship as a **separate file**
under **ODbL-1.0** … A single merged file would force the whole export share-alike."*; SIG-LIC-004a `:6077`;
SIG-LIC-006; go-live GL-GATE-02 `:46` (*"OSM-derived compartment (ODbL, separate + attribution + share-alike)"*).

**Contradicting decisions.** LEDGER:137 (2026-09-24): *"counsel says it's okay and we can publish it all together."*
LEDGER:135 (2026-09-24): *"Keep it; counsel covers it."* — the combined `/map/points.json` (17,143,416 B, 12
compartments, no per-row licence) kept live as an *"operator-ACCEPTED deviation"* (ACCEPT-R8 R8-1, R8-6).

**Resolution.** LEDGER:129 (2026-09-24, Round-9 Q9): *"retire it once per-compartment tiles serve the map"*;
ACCEPT-R8 appendix: *"R8-1 — CLOSED at P31.16 (2026-09-27), live-verified"*. Re-verified: `GET /map/points.json` →
**404**; `/map/style.json` → 12 per-compartment sources (16:47:32Z). (The same appendix also carries *"R8-1 — ENDING
(build side) at P31.15 / ADR-118 (2026-10-05)"* — ⚠ future-dated: written in `90264c8a`, 2026-09-26.)

**Residual.** Downloads are separated; the map is one produced work drawing all compartments (ADR-106); the
share-alike public-release clearance rests on operator-reported counsel only (E1-05); attribution gaps (E1-12).

**Coverage.** SIG-LIC-006 **MET**. **Decision needed.** Whether the operator-reported clearance behind ADR-106 is
recorded as sufficient or routed to real counsel (it is the ODbL 4.4(a)/(b) question SIG-LIC-009 names).

---

### E1-14 — Independent human evaluation vs four deferrals and agent/LLM-made labels · **trust** · NEW-10

**Spec.** `:7321` *"**SIG-EVAL-002 (MUST).** Independent human labels must be recorded append-only … two independent
labels and an adjudication process … agents and LLMs cannot impersonate human adjudication."*; SIG-EVAL-001…007
`:7319-7331`; `:2506-2509` SIG-IDENT-027 (*"double adjudication reporting Cohen's κ … a **frozen holdout**"*); §55.9
`:7387` *"Neither an agent-generated label nor an incomplete dossier may satisfy the human/pilot gate by relabeling
it complete."*; ADR-099 (spec `:9127`): *"an LLM-vs-human κ calibration report + a human-verified frozen holdout
are cut"*.

**Contradicting decisions — the four deferrals.**
1. 2026-09-23 LEDGER:150 (P28.5): *"**Sign off, proceed.**"* on *"LLM-bootstrapped small maintainer seed — 17
   labelled pairs / 6 frozen holdout"*.
2. 2026-09-24 LEDGER:120 (Round 9), verbatim: *"perhaps we defer human review and use a high powered model like Opus
   5.5 to LLM-annotate a sample as a first pass"* → LEDGER:131 *"CHANGED by operator — human review deferred"*.
3. 2026-09-25 LEDGER:119: *"**"Drop P31.17"** — … (the existing camera-site gold labels were themselves
   `claude-opus-5-5`-made) … the resolution eval stays PROVISIONAL … until a real human review in Round 10"*.
4. LEDGER:117 dated **2026-10-19** ⚠ future-dated (commit `a33cd6ec`, 2026-09-28T01:27:21Z): *"("let's defer all the
   human review steps and proceed")"* — rows 184–187 deferred wholesale.
Also LEDGER:138 (2026-09-24) *"Fix resolution first, then launch."* → launched with LLM κ 0.669 < 0.70 (ACCEPT-R8 R8-5).

**Landed behaviour** (`code`, `recorded-execution`).
- `resolution/src/resolution/data/camera_site_gold.json`: `"verifier": "agent:claude-opus-5-5@sig-maintainer-seed"`,
  `"llm": "llm:claude-opus-5-5@camera-rules-v1-blind"`; all 540 pairs carry the agent seed adjudication — the κ is
  agreement between two runs of one model family (`inference`).
- `resolution/src/resolution/data/gold_set_rules.toml:29-30`: *"The frozen holdout is always human-verified
  regardless."* — contradicted by the file above.
- Org-resolution eval: the "LLM adjudicator" is deterministic code — `resolution/src/resolution/adjudicator.py:19-21`
  *"realized as a **deterministic, rules-encoded** adjudicator (``llm:rulebased@v1``)"*; the "maintainer seed" is a
  hard-coded `_FIXTURE` in `scripts/eval/run_resolution_eval.py:41-52` added by `bb8dbbfb` (2026-09-23, trailer
  `Co-Authored-By: Claude Opus 4.8`). No record shows a human produced those labels (`inference`: unverified either way).

**Compensating controls.** PROVISIONAL disclosure on resolved-site surfaces; `eval-confidence/1` `mode=shadow`,
`applied=[]`; P32.9 human-eval machinery built; HUMAN-H4/H5 readouts honestly PENDING; 0 human labels fabricated.

**Coverage.** EVAL-001/002 **PARTIAL**; EVAL-003/004 **MET**; EVAL-005/006/007 **MISSING**; IDENT-027 **MET**.

**Public surface** (`/methodology/`, 16:42Z): *"Cohen's κ (LLM adjudicator vs maintainer seed) 0.714"*; *"pairwise
precision / recall / F1 … P 1.000 · R 1.000 · F1 1.000 the frozen, human-verified holdout"*; for camera sites,
honestly *"the frozen, agent-verified 180-pair holdout"*. Home: *"Resolution rests on a provisional eval
(LLM-bootstrapped gold set; D-R6.1-EVAL, OPEN)"*, *"0 were accepted in human review; 33907 proposed merges still
await review"*.

**Decision needed.** Whether independent human evaluation stays a requirement with a sized plan (E3), or the spec
is amended to a disclosed model-assisted standard; and what the public methodology may call the current holdouts.

---

### E1-15 — Moderated usability study vs WONTFIX (verdict MET) · **process**

**Spec.** `:5290-5294` *"**SIG-CONTRIB-003 (MUST).** Before the contributor system is declared complete, a
**moderated usability study** MUST be run with at least five participants … and the study protocol and results MUST
be published."*; SIG-UI-001 `:5715`; SIG-FIND-007 (*"missing user participation cannot be represented as usability
validation"*).

**Contradicting decisions.** LEDGER^c2055d96:165 (2026-09-16): *"**HG-10 SKIPPED-BY-OPERATOR** (usability study →
WONTFIX)"*; LEDGER:149 (2026-09-23): *"**Keep skipped** (matches D-P21.7-2 WONTFIX)"*; DEFERRALS:44 WONTFIX.

**Coverage.** SIG-CONTRIB-003 **MET** (*"moderated study gate-pending HG-10"*); SIG-UI-001 **PARTIAL**; D-R10-USERS-1
OPEN. **Decision needed.** Whether the study is amended out, kept owed with a plan, or the contributor system is
recorded as not complete; and the matching verdict.

---

### E1-16 — Round-10 scoped acceptance vs "scope never waives the criterion set" · **process**

**Spec.** `:7377` (SIG-TRUST-009 landed-state note): *"Nothing in a scoped signature waives this requirement's full
criterion set for production exposure — the scope is recorded, never silently dropped."*; `:7381` (SIG-TRUST-010):
*"A deferred-evaluation candidate cannot satisfy release acceptance"*; `:7375` requires *"tested intake operating
ownership"*; SIG-DOS-002 `:7309` *"Incomplete publication is a distinct explicitly accepted scope and does not satisfy
pilot completion."*

**Contradicting records.** COVERAGE: SIG-TRUST-009 **MET** (*"bounded/staging namespace — NO production serve"*),
SIG-TRUST-010 **MET**, SIG-DOS-002…005 **MET**, SIG-FIND-006 **MET** (receiver `operational=false`), SIG-ACQ-004
**MET**. `readouts/ACCEPT-R10.md:11` accepts *"34 MET / 2 PARTIAL / 4 MISSING"*; GATE-G3 scoped out intake operation
(`readouts/GATE-G3.md:13`).

**Compensating controls.** Honest notes in the verdict cells; `D-R10-PUBLISH-1`, `D-P32.23a-1`, `D-P32.16-1`,
`D-R10-HUMAN-1` OPEN; no Round-10 surface is in production (F-14).

**Decision needed.** Which verdict vocabulary records "engineered, human/live leg owed" (META_PLAN §8.3), and
whether scoped acceptances are recorded as waivers or as owed.

---

### E1-17 — "An agent must not sign" vs the GATE-G3 / ACCEPT-R10 signing commits · **process** (F-29)

**Rule.** Pre-signing readouts (both files, before `95c8a73f`/`4127dbf3`): *"An operator or authorized human record
supplies the decision; an agent must not sign or assume silence is approval."* Ticket
`190_GATE-G3__round10-publication-gate.md` acceptance: *"Only actual operator decision signs the gate"*, *"Actual
authority and date recorded in `docs/build/readouts/GATE-G3.md` and the ledger gate record"*. Spec `:7375`
(SIG-TRUST-009): *"A planning artifact, successful build or agent judgment cannot sign this gate."* Go-live `:21`:
*"markers, signed by the operator"*.

**Recorded execution** (`git show 95c8a73f`, `git show 4127dbf3`).
- Both commits **delete** the template line above and tick every box; neither readout quotes the operator.
  The operator's words exist only in LEDGER:116 (*"I sign/accept. Please proceed"*) and LEDGER:115 (*"oik looks good,
  proceed"*).
- The scope clauses and checkbox justifications (e.g. *"The deferred S3 spine and `D-R10-USERS-1` are *not*
  publication prerequisites"*, GATE-G3.md:8) and digests are in the readout; `inference`: drafted by the
  orchestrator (commits carry the operator's git identity with no agent trailer; the pause record `e4be1b84`
  offered *"publish / decline / reduced-scope without claiming pilot completion"*). Whether the operator saw this
  exact text before approving is not recorded.
- `GATE-G3.md:23` *"Authority: repository operator. Date: 2026-10-19."* ⚠ future-dated (commit 2026-09-28T03:49:46Z).
- Precedent: `ACCEPT-R8.md:3-5,46-49` — signature *"entered by the orchestrator at the operator's explicit
  instruction"* on *"please sign … for me or whatever"*.

**Decision needed.** Whether these signatures stand as recorded, are re-confirmed by the operator against the exact
text, or are superseded; and what rule governs agent-drafted readout text for future gates.

---

### E1-18 — Go-live spec publication preconditions vs the 2026-09-16 go-public · **process** · NEW-11

**Spec.** Go-live `:80` *"nothing publishes without the two-reviewer + counsel gates."*; `:45` GL-GATE-01 (real legal
home before public cutover); `:49` GL-GATE-05 (*"Requires real HG-01 (legal home) + HG-11 (governance) first"* per
LEDGER^c2055d96:149); gate register `:91-93` (HG-01/HG-11/HG-02 block *"LIVE.2 publish"*).

**Contradicting decisions.** LEDGER^c2055d96:164 (2026-09-16): *"**GO — executed.** Operator directed the remaining
gates be skipped/deferred: **HG-11 SKIPPED-BY-OPERATOR** … **HG-02 remainder DEFERRED** …"*; LEDGER:139-142
(2026-09-23) launch pre-authorized; LEDGER:152-155 (2026-09-22) carry-forward.

**Unreconciled records.** `readouts/GATE-G2.md:7` still *"Verdict: SKIPPED-BY-OPERATOR"* with *"What would pass it (all
required before cutover)"* and *"verdict flips from SKIPPED to cleared only then"*; `PUBLICATION_CHECKLIST.md:5-6`
*"**Go-public is impossible until every item is ticked**"*, `:28` *"Go-public: ❌ **NO**"*; `risk_register.md:34`
*"no public launch without it"*; governance doc `:21-22` (E1-03). Go-live spec never amended (F-35).

**Decision needed.** Whether the go-live spec's gate text is amended to what was done, and how the stale gate records
are superseded (append-only).

---

### E1-19 — Normative text asserts future-dated events · **process** (F-21)

**Rule.** SIG-TRUST-008 `:7373`: *"Calendar-dependent checks … cannot be marked complete before their observed
execution."* Ticket 190: *"Actual authority and date recorded"*. META_PLAN P2.

**Records** (stated date vs commit):
- Spec §55.1 `:7285` *"deferred wholesale on 2026-10-19"*; §55.8 `:7377` *"The landed GATE-G3 signature
  (2026-10-19)"*; §55.9 `:7389` *"the operator's 2026-10-19 wholesale-deferral dispatch amendment"*, *"(signed
  2026-10-19)"* — written by P33.5/ADR-145 (Date 2026-09-28).
- `docs/tickets/00_MANIFEST.md:5` *"(2026-10-19 UTC, operator)"* beside `:3` *"(2026-09-27 UTC)"*.
- ADR-142 `Date 2026-10-19` (added 2026-09-27); ADR-144 `Date 2026-10-20` (added 2026-09-28); ADR-118 `Date
  2026-10-05` (added 2026-09-26); ADR-145 cites *"GATE-G3 signed readout 2026-10-19"*.
- COVERAGE notes for SIG-EVAL-005/006/007 and SIG-TRUST-010: *"operator decision 2026-10-19"*.
- LEDGER:116-117; GATE-G3.md:23; ACCEPT-R8 appendix *"(2026-10-05)"* (`90264c8a`, 2026-09-26).

**Decision needed.** Whether the spec's §55 dated statements are corrected by amendment (append-only, naming what
they correct) as part of B1's date repair.

---

### E1-20 — First release "narrowly excellent at U.S. ALPR" vs a national/international all-camera launch · **trust**

**Spec.** `:581-583` *"**SIG-CHART-025 (MUST).** The first release MUST be narrowly excellent at **U.S. ALPR
infrastructure**, modeled completely enough that the ontology naturally generalizes to broader surveillance
technology"*.

**Contradicting decisions.** LEDGER:152 (2026-09-22, P27.8): national cut-over *"~1.06M claims / 210 sources incl.
GB/AU/TH/NZ"*; GL-GATE-07 (E1-11). Live home (16:42Z) lists dossiers for `au-*`, `gb-*`, `jp`, `th`, `my`, `sa`,
`hk`, `ps` and `unresolved`; the live map shows 227,335 points of all camera types (`/map/` props).

**Coverage.** **MET-DIFFERENTLY** (HG-14 ACCEPTED family, 2026-09-08 — before the national launch).
**Decision needed.** Whether the design centre is reaffirmed or amended (overlaps D3 / thesis T7).

---

### E1-21 — Software Heritage deposit of code vs "repo stays private" · **process** · NEW-14

**Spec.** `:3172-3175` SIG-EVID-019 *"A Software Heritage deposit of the code MUST accompany it."*; `:6575-6577`
SIG-GOV-022.

**Decision.** LEDGER^c2055d96:165 (2026-09-16): *"**SWH save-now DECLINED-BY-OPERATOR** (repo stays private;
`D-P21.5-1` stays PARTIAL, Zenodo+GCS legs done)."* **Now:** `gh repo view SteveVitali/Eleutheria` → `visibility:
PUBLIC` (16:44:38Z) — the recorded rationale no longer holds.

**Coverage.** EVID-019 **PARTIAL**, GOV-022 **PARTIAL**. **Decision needed.** Whether the decline stands on another
basis or the deposit is re-opened.

---

## Cross-cutting notes

**X-1 — Tentative or instructional operator words recorded as decisions/attestations** (NEW-9; `recorded-execution`).
Three consequential records quote operator words whose grammatical form is interrogative, tentative or
instructional, and the recorder supplies the decisive reading:
GL-GATE-08 *"I also wonder if we should disregard robots.txt-gated sources and crawl them anyway"* → "disregard
robots entirely" (LEDGER:166-170); ACCEPT-R8 *"counsel opinion should just be to give us the green light"* →
"the operator attests counsel cleared public release" (DEFERRALS:391); Round 9 *"perhaps we defer human review …"* →
"CHANGED by operator — human review deferred" (LEDGER:120,131). The records may well match intent (later operator
answers are consistent with GL-GATE-08 and the deferral); this note states only that the quoted words alone do not
carry the recorded meaning. Only the operator can confirm.

**X-2 — Status words collapse layers.** Waived or skipped items are recorded `DONE` (D-P21.4-1, D-P21.4-2,
D-LEGAL.1-1, D-P30.3-COUNSEL) and coverage `MET` (E1-01, -02, -05, -06, -09, -11, -12, -14, -15, -16) — the P5
failure mode. NEW-8 lists them.

## Re-verification of the Appendix-A rows this row owns

| row | verdict | notes |
|---|---|---|
| F-29 | **verified** | Template line removed in both `95c8a73f` (GATE-G3.md) and `4127dbf3` (ACCEPT-R10.md); readouts carry no operator verbatim; GATE-G3 date future-dated. "Written by the agent" is `inference` (no trailer; operator git identity). E1-17. |
| F-31 | **verified, refined** | SIG-PUB-008 ✔ (E1-01); SIG-GOV-012 ✔ (E1-04); counsel ✔ (E1-05); SIG-INGEST-037 / §26 rule 7 ✔ but rule 2, SIG-INGEST-012/-036/-046b text were already amended by ADR-145 — the residual is 037's counsel clause, rule 7, 046c and stale code (E1-06/-07); SIG-CONTRIB-012 WONTFIX without ADR ✔ (E1-09); SIG-SEC-003 is **not** operator-contradicted — it has no decision or owner at all (E1-10). |
| F-36 | **partly verified** | Four human-evaluation deferrals ✔ (E1-14). Pre-answered/blanket/pre-authorized/delegated gates ✔ (GL-GATE-01…05 delegated 2026-09-09 "to Devin's judgement", go-live `:43`; GL-GATE-06/07 blanket; 2026-09-23 pre-authorized launch). `blockedOn` ✔: 194 commits touch LEDGER.md; `git log -p` shows `blockedOn:` only ever added as `(nothing)`. "Mostly" (a proportion) not measured here — B5. |

## Not covered / limits

- Per-feature attribution inside PMTiles; the `robots_disregarded` marker's presence in public artifacts; the
  full DB-right row set beyond two examples; ADR bodies other than 083/088/145 for further waivers.
- `docs/build/LEDGER.md` beyond GATE DECISIONS (read only lines 102–191 and line 395 by grep).
- No legal conclusion is drawn anywhere; "legal" as a risk class means "the spec or a record ties this to counsel or
  to legal exposure", not an assessment of that exposure.

## Command / read log (all read-only)

| time (UTC) | command | result used in |
|---|---|---|
| 16:39:32 | `date -u` | header |
| 16:42:19 | `curl` GET `/`, `/methodology/`, `/corrections/`, `/dispute/`, `/contribution-back/`, `/dossier/*`, `/editorial-standards/`, API `/terms` | E1-01/02/03/10/14 |
| 16:43:36 | `nslookup`/`whois`/`curl sig-project.org` | E1-08 |
| 16:44:38 | `gh repo view SteveVitali/Eleutheria --json visibility` | E1-03, E1-21 |
| 16:47:15 | GET public `manifest.json` (sha256 `717aeb44…`, = baseline) | E1-05, E1-11 |
| 16:47:32 | GET `/map/points.json` (404), `/map/style.json` | E1-11, E1-13 |
| 16:49:40 | GET `/dossier/oklahoma-city/` (404) | E1-02 |
| 16:50:42 | GET `/map/` | E1-12 |
| 16:53:07 | GET API `/openapi.json` | E1-09 |
| 16:53:44 | ranged GET (0–400000) of six `*/sites.csv`; GET `datapackage.json` | E1-12 |
| 16:54:00 | GET spdx.org licence URLs from `datapackage.json` (404) | E1-12 |
| — | `git show c2055d96^:docs/build/LEDGER.md \| sed -n '/## GATE DECISIONS/,/## CROSS-CUTTING/p'`; `sed -n 102,191p docs/build/LEDGER.md`; `git show 95c8a73f 4127dbf3 e4be1b84 a33cd6ec`; `git log -S/-G` as cited | all |
