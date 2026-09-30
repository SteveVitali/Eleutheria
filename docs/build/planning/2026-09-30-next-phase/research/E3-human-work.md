# E3 — Human-work feasibility and sourcing

Row **E3** of `META_PLAN.md` (Stage P, Wave 2). Research only: read-only over the repo, one public-page read of
`https://surveillancegraph.org/editorial-standards/`, and web searches for market context. **Nobody was contacted,
recruited or asked for anything.** No human work was done or simulated (P4). Every effort figure below is a
*planning estimate*: the project's own rule is that measured time is recorded only from real session sheets
(`docs/evaluation/measured-time-worksheet.md` §4 rule 1), and this document supplies none.

- Started 2026-09-30T16:39:46Z; written 2026-09-30T16:48Z onward (`date -u`). Planning branch head at write time `884915a2`.
- Evidence classes (P1): `code` · `live-read` · `inference`. Figures marked **[ext]** come from web sources (§10) and
  are external estimates. Figures marked **[est]** are this row's own assumptions, with the reasoning shown.
- Every source file cited in §11 was read, as the whole file or as `grep`/`sed` slices. LEDGER.md was not opened (P13).

---

## 0. Bottom line

1. **The owed human work adds up to roughly 145–375 person-hours for a minimal *honest* program** (§5). Of that,
   about **70–200 h falls to the operator**, about **60–135 h to three external reviewers**, **10–30 h to counsel**, and
   **5–6 h to five usability participants**. In cash that ranges from **about $0–1k** (volunteers, pro bono counsel,
   paid participants) to **about $6k–25k** (everyone paid) **[ext]**. The critical path is **about 3–5 months**, driven
   by recruitment and counsel lead times [est].
2. **Engineering has to come first.** External reviewers cannot take part today. Each labeler needs a personal
   PostgreSQL login and has to hand-edit JSON workbooks, and there is no reviewer UI (NEW-2). The research dossiers
   that a semantic reviewer would check are built from hand-authored stand-in documents (NEW-3). The H4 pilot
   needs P32.22's repaired snapshot, but production recovery (`D-R10-LIVE-1`) is still OPEN.
3. **The spec's 0.98 promotion gate cannot be met by a small campaign.** The smallest possible confirmatory sample
   is **149 pairs for one tier, and only if none fail**. Even when the rules really are 99% precise, a 149–400-pair
   campaign passes only **22–43%** of the time (§4). A smaller campaign that only reports an estimate is honest but
   saves little effort, because fixed costs dominate: going from 100 to 149 pairs adds only about 8–23 h. So the
   operator has to choose between two aims: (a) attempt certification, or (b) measure precision and keep
   auto-write PROVISIONAL.
4. **The operator can legitimately fill most roles:**
   - rights decisions (HG-03)
   - intake owner
   - partner-identity review
   - operational curation
   - records filing (in states without a residency rule)
   - the OSM account
   - campaign custodian and method reviewer, both with disclosure

   **Some roles must be independent of the operator:**
   - both first-pass reference labelers (preferred; see §6 for the minimal fallback)
   - the dossier semantic reviewer
   - one of the two hostile-reader reviewers
   - the second publication reviewer and the editorial board
   - counsel
   - usability participants
5. **New issue found (NEW-1, S1).** `/editorial-standards/` publicly presents a completed two-reviewer
   "hostile-reader review" (SIG-UI-042) by placeholder reviewers "Reviewer A/B". It is dated **2026-08-19, the day
   before the repository's first commit**, and it lives in a fixture constant written by an agent. It carries no
   human provenance, yet the coverage matrix marks SIG-UI-042 MET.

---

## 1. Effort basis (reused from the P32.9 packet and S3 research)

| Parameter | Value | Source |
|---|---|---|
| Pilot, per reading | 8–15 min | `docs/evaluation/measured-time-worksheet.md` §1; `training-pilot-packet.md` §2 |
| Pilot size / design | 40 items × 2 independent readers; the pilot budget is 20–40 reviewer-hours | `training-pilot-packet.md` §2; worksheet §3 |
| Final campaign, per reading | 4–12 min | S3 §10 table (`research/S3-human-evaluation.md`) |
| Adjudication share and time | 20–30% of items at 8–15 min each | S3 §10 |
| Campaign prep and QA | 12–24 h, stated for a 400-pair campaign and not scaled down here (conservative) | S3 §10 |
| Protocol / method review | 8–20 h | S3 §10 |
| 40-neighborhood recall study | 26–75 h | S3 §10 |
| Seats the current campaign marker asks for | "2+ independent human reviewers, 1 custodian/adjudicator, 1 method reviewer" | `human-campaign-marker-packet.md` §3 |
| Adjudicator rule | Records an independent judgment, blind to the earlier votes, before resolving; `unresolved` is a permanent valid outcome | `docs/evaluation/rubric.md` §5 |
| Gate coding | `insufficient_evidence`, `unresolved`, `different` and missing all count as **non-successes** | S3 §8 "Proposed machine decision"; SIG-EVAL-004 |

---

## 2. Role register

Each role lists: what the contract asks, competence, independence, effort with arithmetic, whether the operator can
fill it, sourcing, the smallest honest version, and what stays blocked or disclosed if nobody fills it.

### R1 — Device / camera-site reference labelers (HUMAN-H4 development, HUMAN-H5 blinded confirmatory)
- **Task.** Each reader works alone and blind to matcher output. For each sampled pair they answer *"same physical
  device at a compatible observation period?"* as `same`, `different` or `insufficient_evidence`, with a
  `reference_basis` and cited reasons (`rubric.md` §1–§4). They time each item on the worksheet.
  - **H4:** training, the 40-item pilot and a calibration discussion. These are development labels only
    (`184_HUMAN-H4…` deliverable 2).
  - **H5:** the sealed sample from P32.22a, two independent labels per item, then attestations and a sealed
    watermark (`186_HUMAN-H5…`).
- **Competence.** Reads source records (upstream IDs, lineage, capture dates, coarse geometry) and follows a written
  rubric carefully. No legal expertise is needed. Familiarity with ALPR/CCTV hardware helps but is not required.
- **Independence.** The two readers must be independent of each other: they work alone, and a human attestation is
  required (`reviewer-provisioning.md` §3). The docs also prefer readers "who did not author the candidate rule or
  the operational decision" (§1 there; S3 §5). The rules-author firewall says *"Rules authors and operators receive
  only training/development labels until the final run is frozen and unsealed"* (`training-pilot-packet.md` §5).
  An agent can never attest or label (`README.md`; P4).
- **Effort per labeler [arithmetic].**

  | Step | Arithmetic | Hours |
  |---|---|---|
  | Training [est] | — | 2–3 h |
  | Pilot | 40 × 8–15 min | 5.3–10 h |
  | Calibration [est] | — | 1–2 h |
  | H5 final, n = 149 | 149 × 4–12 min | 9.9–29.8 h |
  | **Total per labeler** | | **18–45 h** |

  For other sample sizes, each labeler's final-campaign share scales as n × 4–12 min: 236 → 15.7–47.2 h;
  366 → 24.4–73.2 h; 554 → 36.9–110.8 h.
- **Can the operator do it?** **Not as an independent labeler.** The operator directed the rule development, so
  labeling sealed items conflicts with the §5 firewall and with the "non-author" preference. The minimal fallback
  (operator as one of the two readers) needs a recorded exception and public disclosure (§6).
- **Sourcing** (none contacted):
  - **(a) Volunteers from the surveillance-transparency community.** DeFlock mappers **[ext]**, the EFF Atlas of
    Surveillance volunteer and student network **[ext]**, MuckRock users. Cost $0. Lead time about 2–6 weeks [est].
    Caveat: DeFlock/OSM mappers may have authored the OSM observations SIG resolves, and SIG deliberately stores
    **no OSM user names** (`D-P21.7-1`). An item-level conflict-of-interest screen is therefore impossible, so
    conflicts must be self-attested (for example "not my home region") through the existing
    `conflict_of_interest` attestation kind.
  - **(b) Academic partner.** A journalism or information-school course, following the EFF–UNR Reynolds School model
    that built the Atlas of Surveillance **[ext]**. Cost $0. Lead time is a semester (about 3–6 months) [est].
  - **(c) Paid annotators.** $10–35/h on Upwork generally; $28–40/h for senior/QA annotators; $40–100/h for domain
    experts **[ext]**. Lead time about 1–2 weeks [est]. Cost for two labelers at 18–45 h each and $25–40/h is
    about **$900–3,600**.
- **Smallest honest version.** Run the pilot plus a **single-tier confirmatory sample of n = 149**, preregistered
  (§4), with two external readers. Alternatively, an estimate-only n ≈ 100 that openly cannot certify (§4). Publish
  every limitation the protocol requires.
- **If nobody is sourced.** The marker stays `tooling_ready`. `D-R10-HUMAN-1`, `D-R6.1-EVAL` and `D-P30.2b-2` stay
  OPEN. SIG-EVAL-001/002 stay PARTIAL and 005/006/007 stay MISSING. Auto-write thresholds stay PROVISIONAL
  (LLM-bootstrapped), and every "resolved sites" surface must keep its provisional-evaluation disclosure (see F-06
  for the current public wording).

### R2 — Adjudicator
- **Task.** Resolves every disagreement, every `insufficient_evidence` and every non-completion. First records an
  independent blind judgment, then inspects the evidence (`rubric.md` §5).
- **Competence.** Same as R1, plus care in weighing conflicting evidence.
- **Independence.** Must not be one of the first-pass readers on the same item, because the blind judgment has to
  come first.
- **Effort [arithmetic].**

  | Step | Arithmetic | Hours |
  |---|---|---|
  | Pilot | 8–12 items × 8–15 min | 1.1–3.0 h |
  | H5, n = 149 | 30–45 items × 8–15 min | 4.0–11.3 h |
  | Training [est] | — | 2–3 h |
  | **Total** | | **7–17 h** |

  At n = 366 the H5 share is 73–110 items → 9.7–27.5 h.
- **Can the operator do it?** Possible with disclosure: the operator casts no first-pass vote, but sees sealed items
  and votes before unsealing, which needs a recorded exception to the §5 firewall. **Recommended: an external
  person** (who can also be R5; see §5).
- **Sourcing.** As R1. $40–100/h if paid **[ext]** → about $280–1,700.
- **Smallest honest version.** If no adjudicator exists, disagreements stay `unresolved`, which the rubric allows.
  They count as gate non-successes, so the result is conservative but honest.
- **If nobody is sourced.** Same as R1 when labelers exist; otherwise unresolved outcomes accumulate.

### R3 — Campaign custodian
- **Task.**
  - Provisions pseudonymous reviewer logins, assignments and attestations (`reviewer-provisioning.md` §2–§5).
  - Does packet QA and signs the freeze checklist together with the method reviewer (`training-pilot-packet.md` §4).
  - Records adjudications and the one-time release, and fills in the worksheet rollup.
- **Effort.** 2–5 h (H4) + 12–24 h (H5 prep/QA, S3) + 2–4 h provisioning [est] = **16–33 h**.
- **Can the operator do it?** **Yes.** It is an administrative seat, and S3 §5 allows "one person can perform
  administrative roles if separation and access limits are documented". Because the custodian reads sealed labels
  before unsealing, the §5 firewall needs a recorded exception. The risk is low only because P32.22a freezes the
  candidate first; any post-unseal change would require a new campaign.
- **If nobody is sourced.** No campaign can run.

### R4 — Method reviewer
- **Task.** Signs the statistical design and analysis manifest, the seal, and the independent-reproduction step
  (S3 §5 and §10; freeze checklist). Covers design, multiplicity, fixed stopping rule and interval method.
- **Competence.** Survey sampling and exact binomial / finite-population inference.
- **Effort.** **8–20 h** (S3).
- **Can the operator do it?** Yes with disclosure. An agent may draft the analysis, but an agent cannot sign (P4).
  **Cheapest honest mitigation:** publish the preregistration on **OSF Registries** (free, time-stamped, read-only)
  **[ext]**, so outside scrutiny stands in for an independent statistician. A paid statistician would cost about
  $100–150/h × 8–20 h (professional research rate **[ext]**, used as a proxy).
- **If nobody is sourced.** The freeze checklist cannot be signed, so the campaign cannot proceed.

### R5 — Dossier semantic / legal-documentary reviewer, plus hostile-reader reviewers (SIG-UI-042)
- **Task (H4 deliverable 3).** Complete the fixed dossier rubric (36 points) and a material
  governance/contract/relationship semantic review. Trace every material assertion to the fact-to-capture ledger and
  record unresolved applicability or execution issues. "Device-label expertise is not automatically
  legal/applicability expertise" (`184_HUMAN-H4…`).
- **SIG-UI-042.** Two reviewers independently read a real rendered dossier *from the stance of the documented
  organization's counsel*, log every sentence they would challenge, and sign off. This is required per template
  version, and release is blocked until every finding is dispositioned (spec `:5998-6006`).
- **Competence.** Reading contracts, policies, ordinances and council memos: amendment versus executed contract,
  posted versus effective, access versus hardware. Typical profiles are a public-records journalist, paralegal or law
  student, or a civic-tech researcher.
- **Independence.** Required. The checklist item is `independent_semantic_review`, and all three dossiers record
  `review.status=not_run`, "never fabricated" (`p32.18/19/20 *_dossier.json → review`).
- **Effort [arithmetic].**
  - Ledger entries are 36 (OKC) + 13 (Tulsa) + 37 (San Diego) = **86**. At 5–10 min each [est]: 7.2–14.3 h.
  - Answers are 3 × 12 = 36. Rubric scoring at 5–10 min each: 3–6 h.
  - Reading the three dossiers at 0.5–1 h each: 1.5–3 h.
  - **Semantic review total: 12–23 h.**
  - Hostile reader: 2 readers × 3 dossiers × 1–2 h, plus 1–2 h to disposition findings: **7–14 h**.
- **Sequencing caveat (NEW-3).** The three dossiers are composed over *hand-authored stand-in documents*
  (`tests/connectors/fixtures/dossier/SOURCES.md`). A review now can only check extraction fidelity against the
  stand-ins, not real-world truth. It should follow the live return passes (`D-P32.18-1`, `D-P32.19-1`,
  `D-P32.20-1`) or be scoped and labeled as a stand-in review.
- **Can the operator do it?** **Not the semantic reviewer.** The operator may serve as **one** of the two hostile
  readers with disclosure; the other must be external [recommendation].
- **Sourcing.** Journalist networks, law-school clinics or students, EFF/MuckRock circles (none contacted).
  $40–100/h if paid **[ext]** → about $500–2,300 for 12–23 h.
- **Smallest honest version.** One external semantic reviewer for the three dossiers, who is also one of the two
  hostile readers. The operator is the other hostile reader (disclosed). **Correct the public `/editorial-standards/`
  page now** (NEW-1).
- **If nobody is sourced.** `pilot_complete=False` everywhere. Research dossiers are published, if at all, as
  "not independently reviewed". SIG-UI-042 must be downgraded from MET, and the public hostile-reader claim
  withdrawn or relabeled.

### R6 — Second independent publication reviewer and editorial board (SIG-PUB-008, SIG-GOV-015, HG-11)
- **Task.**
  - SIG-PUB-008: two independent reviewers concur in writing before any named individual is published;
    disagreement means no-publish.
  - SIG-GOV-015: an editorial board, distinct from the technical maintainers, decides contested claims,
    officer-naming and sensitivity classifications.
  - Also relevant: SIG-PUB-005's leak-provenance human review.
- **Current state.** The operator filled both reviewer roles personally. Independence was **waived** (`D-P21.4-2`
  DONE under a sole-maintainer posture). `policy.officer._concurrence_ok` still returns False, so person-named
  claims stay default-no-publish. SIG-GOV-015 is PARTIAL (coverage matrix).
- **Effort.** 0 h while officer-naming stays off. Otherwise 0.5–2 h per decision, plus about 1–2 h/month for a
  standing board [est].
- **Can the operator do it?** **No for the second seat.** For the board, the spec requires people "distinct from
  the technical maintainers".
- **Smallest honest version.** Keep officer-naming default-no-publish (already enforced in code). Record the
  SIG-PUB-008/GOV-015 position as an ADR waiver or keep it owed (E1/E2 decide). Make no public "two-reviewer"
  claim. The R5 external reviewer could serve as the second seat later.
- **If nobody is sourced.** Nothing public changes as long as the code keeps names unpublishable. The spec stays
  contradicted until E2 resolves it.

### R7 — Counsel
- **Scope the spec requires counsel for.**
  - SIG-LIC-009's four residuals: ODbL 4.4(b) API distribution; OSM boundary geometry and the Collective Database
    question; the regional-cut unit; the **EU sui generis database right**. The last is already live, because EU
    sources run under `LicenseRef-OperatorAccepted-DBRight` (`D-SOURCES.8-1`).
  - Officer-naming, publication tiers and sensitive coordinates, and Part VIII (HG-02).
  - **Deviating from robots.txt** (SIG-INGEST-037: "an ADR-level decision requiring counsel"; GL-GATE-08 / ADR-088
    "disregard robots").
  - Source clauses:
    - Still gated: Bellevue's express use prohibition (`D-SOURCES.8-1` remainder) and `dot_511_md`'s
      iMAP-conditioned terms (`D-SOURCES.7-1`).
    - Already flipped without the counsel review their packets called for: `camreg_lexington_ky` (indemnify-and-defend
      terms) and `camreg_md_opendata` (iMAP terms), flipped under GL-GATE-07 in P26.16 (`D-SOURCES.8-1` status cell).
  - Legal home and legal-defence resources (SIG-GOV-012/013).
  - Receiver wording and retention for legal demands.
- **Current state.**
  - `D-LEGAL.1-1` is DONE through **operator-adopted drafted analyses, "NOT counsel"**.
  - `D-P30.3-COUNSEL` is DONE by **operator attestation**; there is "no counsel-authored document in the repo".
  - ADR-086 and ADR-106 cite *operator-reported* counsel determinations (2026-09-16, 2026-09-24).
  - As a result, Appendix B's 36 owed rows contain **no counsel row** (NEW-4).
- **Effort.** A scoped written opinion on 4–6 questions: **10–30 counsel-hours** [est], plus 5–10 h for the
  operator to assemble the question packet. An agent may draft that packet, but not the opinion (P4).
- **Can the operator do it?** **No.**
- **Sourcing** (none contacted):
  - EFF Cooperating Attorneys referral, "often pro bono or at a reduced fee" **[ext]**.
  - Law-school technology clinics: Harvard Cyberlaw Clinic advised OSM-US on ODbL in 2016 **[ext]**. Clinics take
    new clients by semester (lead time about 1–4 months [est]).
  - RCFP legal hotline, which is free but aimed at journalists and media law **[ext]**. It may not cover database
    licensing.
  - Paid counsel: the US average rate is **$349/h** (Clio 2025) **[ext]**, so 10–30 h ≈ **$3.5k–10.5k**.
  - The existing counsel behind ADR-086/106, if one exists (question Q-E3-6).
- **Smallest honest version.** One dated written opinion covering ODbL 4.4(b) and the EU database right, filed under
  `docs/governance/`. Every other area stays labeled "operator-adopted analysis, not legal advice", and public copy
  never says "counsel-cleared" unless a document exists.
- **If nobody is sourced.** Publication continues on operator dispositions, with the risk stated in the risk
  register (R-01, RISK-P0-*). The robots deviation and the EU database-right exposure stay operator-accepted risks.
  E1/E2 must make the spec say so.

### R8 — Usability participants and moderator (D-R10-USERS-1, SIG-UI-001, HG-10 / SIG-CONTRIB-003)
- **Task.** Two protocols are landed but have not been run:
  - **(a) P32.24 think-aloud.** 4–6 participants, at least 2 non-technical, **no SIG contributors**. Sessions are
    45–60 min over tasks T1–T7, with evidence-grounded scoring (`USABILITY_TASK_PROTOCOL.md`).
  - **(b) Contributor onboarding.** At least 5 ontology-naïve participants; the median time from landing page to
    first accepted contribution must be ≤ 10 min (`docs/build/reports/USABILITY_STUDY.md`).
- **Design-center recruitment.** Local advocates preparing for council meetings (SIG-UI-002). Examples: CCOPS
  coalitions, ACLU affiliates, DeFlock, plus journalists and council staff.
- **Effort [arithmetic, 5 participants].**

  | Who | Step | Hours |
  |---|---|---|
  | Moderator | Recruiting and screening [est] | 3–8 h |
  | Moderator | Sessions: 5 × 1 h | 5 h |
  | Moderator | Notes and scoring: 5 × 0.5–1 h | 2.5–5 h |
  | Moderator | Readout [est] | 3–5 h |
  | Moderator | **Total** | **13.5–23 h** |
  | Participants | 5 × 1–1.25 h (adding the onboarding task to the same session) | 5–6.25 h |

- **Can the operator do it?** The operator **can moderate**, with disclosure. The operator **cannot be a
  participant**.
- **Sourcing and cost.** Incentives are about **$60–100/h** for consumer participants and **$100–150/h** for
  professionals such as journalists or attorneys **[ext]**, so 5 sessions ≈ **$300–940**. Prolific's floor is
  $8/h, with $12/h recommended **[ext]**. That fits unmoderated tasks, not the design-center persona. Volunteers from
  advocacy groups cost $0. An academic partner may need IRB review (about 2–6 weeks [est]).
- **Feasibility caveat (NEW-5).** Protocol (a) is confined to "staged releases only (the acceptance corpus is
  synthetic by construction)". Protocol (b) needs `/curate/submit/`, which is loopback-only and was removed from the
  public site (Track 0.2). Neither currently tests the live public site that the design-center persona actually uses.
- **Smallest honest version.** Five moderated 60–75 min sessions against the *live public site*, with the protocol
  amended by the owning ticket. Report medians and the distribution only, plus the wrong-conclusion findings.
- **If nobody is sourced.** `D-R10-USERS-1` stays OPEN and SIG-UI-001 stays PARTIAL. No "validated usability"
  claims. Agent walkthroughs (C2/C3) stay labeled as agent evidence.

### R9 — Rights reviewer for HG-03 packets (E4 drafts the packets)
- **Scope.** 13 still-gated sources:
  - `D-SOURCES.2-2`: 2 sources. Both packets already conclude they are restrictive or ineligible, so the owed act is
    most likely a recorded decline.
  - `D-SOURCES.7-1`: 5 DOT/511 feeds.
  - `D-SOURCES.8-1`: 4 remaining camera registries.
  - `D-SOURCES.9-1`: 1.
  - `D-SOURCES.9-4`: 1.

  Plus the per-target reviews for the P32.18–21 pilot slices in `D-R10-SOURCES-1` (up to 27 candidates). HG-03 is
  **the operator's decision by design**.
- **Effort.** 13 × 0.5–2 h [est] = **6.5–26 h**. Candidate targets add about 0.5–1.5 h each. Clauses marked
  counsel-needed go to R7.
- **Can the operator do it?** **Yes.** Independence is not required, but clauses needing counsel must not be decided
  on agent analysis alone.
- **If nobody acts.** The sources stay fail-closed (exit 3). Nothing unsafe happens; there is a coverage gap and
  coverage facts should say so.
- **Related (NEW-6).** `D-JURIS.2-1`'s *only* remaining blocker is Belgian eID access to `declarationcamera_be`
  (HG-04). The operator cannot fill that role, since it needs a Belgian eID holder or a Belgian partner
  organization.

### R10 — Intake moderation owner, rotation and on-call (D-P32.16-1)
- **Task.**
  - A named `[intake].owner` and a rotation that covers the published SLAs: **72 h** for privacy harm and security,
    **168 h** for legal demands and copyright, **336 h** for factual errors (`policy/src/policy/data/takedown.toml`).
  - Ratify retention: 30 days after disposition, with a 90-day ceiling.
  - Provision secrets and database grants.
  - Enumerate which infrastructure logs retain identifiers (`intake-receiver-operating-packet.md` §1, §7, §8).
  - Moderation happens **only on the loopback curation app**, so any moderator needs trusted infrastructure access.
- **Effort.** One-off setup 4–8 h [est]. Ongoing, 15 min/day of queue checks + 10–30 min per report ≈ **2–4 h/week**
  at low volume [est]; volume is unknown.
- **Can the operator do it?** **Yes as owner.** Covering the 72 h SLA through absences needs a **second trusted
  person with infrastructure access**, or honest published SLAs, e.g. "single maintainer; responses may pause during
  absences" [option for E2].
- **If nobody is sourced.** The receiver stays `receiver_not_operating` (enforced in code). `/dispute/` must stop
  implying one-click correction (F-03).

### R11 — Partner-identity reviewer session (D-P32.3-1)
- **Task.** Record a keep, split or `same_as` disposition for every legacy `sig.org.name` key in
  `partner-name-audit`, until `split_keys` exposure reaches zero.
- **Effort.** The number of keys on the hosted database has **never been measured** (P32.3 ran with
  `live_verification=false`; NEW-7). At 2–5 min per key [est], N = 50–500 gives **1.7–42 h**. A read-only hosted
  audit run (G2) is needed to size it.
- **Can the operator do it?** **Yes.** These are operational identity decisions with `decided_by`; independence is
  not required.
- **If nobody acts.** Legacy name-only unions remain, and organization identity stays qualified.

### R12 — Operational camera-site curator (D-P30.2b-1; not in the role brief, but owed)
- **Task.** Make accept/reject decisions in the loopback curation app over the seeded
  `camsite-r10-seed-round10-v1` sample of 400 items. The hosted database shows **11,625 pending, 0 decided**. After
  that comes the hosted verify leg: an accepted pair clusters and N drops.
- **Effort.** Full seed: 400 × 2–5 min [est] = **13–33 h**. The minimal closure is 50–100 items (about 2–8 h) plus
  the verify leg.
- **Can the operator do it?** **Yes.** Operational decisions are not reference labels, but they must never be
  recycled as reference labels (`README.md` "What this packet is not"). Ideally they avoid the future confirmatory
  dependency groups.
- **If nobody acts.** Proposals stay PROPOSED, are excluded from N, and the pending-count disclosure stays in place.

### R13 — Records-request filer (D-R7.2-SEND)
- **Task.** A consenting filer who acknowledges filing as a public act (SIG-TASK-018) and is valid for the
  jurisdiction's residency rule. Residents-only states: **AL, AR, DE, KY, TN, VA** (SIG-TASK-016a). Hosted state is
  `records_request` = 0 and one drafted `research_task`.
- **Effort.** 1–4 h per request including follow-up [est]. Fees vary.
- **Can the operator do it?** **Yes**, outside the six residency states (for those, only if the operator is a
  resident). Otherwise a local filer is needed.
- **Sourcing.** MuckRock: free account; $20 plan for 4 requests; $40/month Professional for 20 requests/month
  **[ext]**.
- **If nobody acts.** `records_requests_sent` stays 0. Coverage in restricted states must record `not_researched`
  (SIG-TASK-016a §3).

### R14 — OSM contribution-back account holder (D-P21.7-1, HG-08)
- **Task.**
  - Hold an OSM account and a MapRoulette key; rotate the key first, since it appeared in a transcript (Track 0.3).
  - Publish an OSM wiki page at `Organised Editing/Activities/<name>`.
  - **Notify the community at least two weeks before starting**, per the OSMF Organised Editing Guidelines
    **[ext]**.
  - Then set `registered=true` and run the one-step push/pull.
- **Effort.** 3–8 h [est], plus at least 2 weeks of calendar time.
- **Can the operator do it?** **Yes** (operator-only).
- **If nobody acts.** Contribution-back stays in dry-run.

### R15 — Other human seats found in the owed register or spec
- **Stage-0 outreach liaison** (HG-04, SIG-CONTRIB-012 MISSING). 19 projects × 0.5–1 h = **10–19 h**, plus
  follow-up. The operator can do this.
- **Legal home** (SIG-GOV-012/HG-01). Today the legal home is the operator as an individual, in a personal
  capacity (`D-P21.4-1` DONE 2026-09-15). The row's own note says "personal exposure; a more durable
  entity/fiscal-sponsor + HG-02 counsel recommended". Applying to a fiscal sponsor takes 5–15 h [est]. Fees are
  **7% (HCB)** to **10% (Open Source Collective)**, with a general range of 8–15% of revenue **[ext]**.
  [inference] A Model-C style sponsor may not shield liability or accept a high legal-risk project; counsel (R7)
  should confirm.
- **Belgian eID holder** (see R9). The operator cannot fill this.

---

## 3. Consolidated table

Scenario: the H5 confirmatory sample is **single-tier, n = 149**. "Op?" means the operator can fill the seat.

| Role | Effort | Op? | Cheapest honest option | Blocked / disclosed if none |
|---|---|---|---|---|
| R1 labelers ×2 (H4+H5) | 18–45 h each | No (fallback in §6) | 2 volunteers (COI self-attested); preregistered n=149 | `tooling_ready`; auto-write PROVISIONAL; EVAL-005/6/7 MISSING |
| R2 adjudicator | 7–17 h | Disclosed exception | External; else `unresolved` counts as a non-success | Same as R1 |
| R3 custodian | 16–33 h | **Yes** (§5 exception recorded) | Operator | No campaign |
| R4 method reviewer | 8–20 h | Yes, disclosed | Operator + OSF preregistration | Freeze checklist unsigned |
| R5 semantic + hostile reader | 12–23 h + 7–14 h | No / 1 of 2 | 1 external reviewer after live captures; operator as second hostile reader | `pilot_complete=False`; SIG-UI-042 claim withdrawn |
| R6 2nd publication reviewer / board | 0 h while names are off | No | Keep default-no-publish; E2 waiver | Spec contradiction only |
| R7 counsel | 10–30 h (+5–10 h operator) | No | Pro bono referral/clinic; 1 dated opinion (ODbL 4.4(b), EU DB right) | Operator-accepted risk, disclosed |
| R8 participants + moderator | 5–6 h + 13.5–23 h | Moderate only | 5 advocates, $0–940, on the live site | USERS-1 OPEN; no usability claims |
| R9 rights (HG-03) | 6.5–26 h | **Yes** | Operator; counsel for flagged clauses | Sources stay fail-closed |
| R10 intake | 4–8 h + 2–4 h/week | **Yes** + backup | Operator + honest SLAs or a backup | `receiver_not_operating` |
| R11 partner identity | 1.7–42 h (N unknown) | **Yes** | Operator after a hosted count | Legacy unions remain |
| R12 operational curator | 2–33 h | **Yes** | Operator, 50–400 items | Proposals stay PROPOSED |
| R13 records filer | 1–4 h per request | **Yes** (non-restricted states) | Operator; MuckRock free/$20 | Sent = 0; `not_researched` |
| R14 OSM account | 3–8 h + ≥2 weeks | **Yes** | Operator after key rotation | Dry-run only |
| R15 outreach / legal home / eID | 10–19 h / 5–15 h / — | Yes / Yes / No | Operator; HCB 7% | GOV-012 PARTIAL; `declarationcamera_be` blocked |

---

## 4. Sizing the confirmatory campaign (SIG-EVAL-004: exact lower bound ≥ 0.98)

The candidate auto-write tiers are **1 and 3** (`resolution/src/resolution/data/camera_site_rules.toml:47`). The
numbers below are exact Clopper–Pearson bounds, computed in this row with Python and no file writes. They reproduce
S3 §8's all-success figures and add the one- and two-error cases.

| Design | α per tier | n for 0 errors | n for ≤1 error | n for ≤2 errors |
|---|---:|---:|---:|---:|
| 1 tier | 0.05 | 149 | 236 | 313 |
| 2 tiers (Bonferroni) | 0.025 | 183 each (366) | 277 each (554) | 359 each (718) |
| 4 tiers | 0.0125 | 217 each | 317 each | 404 each |

**Probability of passing at the true success rate [inference].** "Success" means an adjudicated `same` on sufficient
evidence, so the `insufficient_evidence` rate is counted against precision.

| Design | p = 0.99 | p = 0.995 | p = 0.999 |
|---|---:|---:|---:|
| 1 tier, n = 149 (0 errors allowed) | 0.22 | 0.47 | 0.86 |
| 1 tier, n = 236 (1 error) | 0.32 | 0.67 | 0.98 |
| 1 tier, n = 400 (3 errors) | 0.43 | 0.86 | 1.00 |
| 2 tiers, 183 each | 0.16 | 0.40 | 0.83 |

An all-success lower bound is 0.928 at n = 40, 0.958 at n = 70 and 0.971 at n = 100. **If the evidence packets have
even a 2% `insufficient_evidence` rate, the 0.98 gate is out of reach at any affordable n.** The pilot measures that
rate, and it should decide which aim the campaign takes.

**Decision for the operator / F4.**
- **(A) Certification attempt.** One tier, n = 236 (H5 ≈ 58–156 h), or n = 149 at the floor (44–115 h).
- **(B) Estimate-only.** n ≈ 100 (36–92 h). It publishes a human-verified precision with its interval and keeps
  auto-write PROVISIONAL.

Fixed overheads (QA 12–24 h, method review 8–20 h) dominate, so (B) saves only about 8–23 h compared with n = 149.
(A) with n = 149 therefore costs little more than (B), even though it passes only if nothing fails. The recall study
(26–75 h) is optional in both; if dropped, publish "recall not measured".

---

## 5. Minimal honest program (MHP)

**Staffing.**

| Person | Seats | Hours |
|---|---|---|
| E1, E2 (external labelers) | R1 | 18–45 h each |
| E3 (external) | R2 adjudicator + R5 semantic reviewer + hostile reader #1 | 22–46 h |
| Operator | R3, R4 (disclosed), hostile reader #2, R8 moderator, R9, R11, R12, R13, R14, counsel packet | 70–203 h |
| Counsel | R7 | 10–30 h |
| 5 participants | R8 | 5–6 h |
| **Total** | | **≈ 145–375 h** |

The operator's line is the sum of: custodian 14–29 + method review 8–20 + hostile reader and disposition 4–8 +
moderating 13–23 + rights 7–26 + partner identity 2–42 + curation 13–33 + filing 1–4 + OSM 3–8 + counsel packet
5–10. That comes to 70–203 h. It excludes intake (2–4 h/week, only if the receiver is opened) and outreach
(10–19 h).

**Cash [ext-based].**
- **All-volunteer with pro bono counsel:** about $0–1k (participant incentives plus MuckRock).
- **Mixed** (paid labelers at $25–40/h, volunteer E3, pro bono counsel, paid participants): about $1.2k–4.6k.
- **All-paid:** about $6k–25k (labelers $1.4k–9k, E3 $0.9k–4.6k, counsel $3.5k–10.5k, participants $0.3k–0.9k).

For comparison, S3 gave a hypothetical $6.5k–17.5k at $50/h.

**Prerequisites before any external reviewer starts** (engineering; F4/G2 own these):
1. A reviewer-facing packet renderer and a credentialed import path that does not require each non-technical
   reviewer to run a PostgreSQL CLI (NEW-2).
2. The `human_eval_*` schema deployed on a database reviewers can reach. Hosted `sig-pg` allows 0 authorized
   networks.
3. P32.22's repaired snapshot, which depends on `D-R10-LIVE-1`.
4. Live dossier captures before R5 (NEW-3).

**Calendar [est].**
- Recruiting: 2–6 weeks.
- H4 pilot: 2–4 weeks.
- P32.22a: engineering.
- H5 at a volunteer pace of about 5 h/week: 4–9 weeks.
- Counsel: 1–4 months in parallel.
- OSM: at least 2 weeks.

Critical path: **about 3–5 months**.

---

## 6. Operator-fillable versus independence-required

- **The operator may fill:** R3 custodian, R4 method reviewer (disclosed plus OSF), R8 moderator, R9 HG-03, R10
  owner, R11, R12, R13 (in non-restricted states), R14, the outreach liaison, the legal-home applicant, and one of
  the two hostile readers.
- **Requires independence from the operator:**
  - R1 labelers (preferred; see the fallback below)
  - R2 adjudicator (preferred)
  - R5 semantic reviewer (required)
  - R6 second reviewer and editorial board (required by spec text)
  - R7 counsel (required; P4)
  - R8 participants (required: "no SIG contributors")
  - Belgian eID (a capability the operator lacks)
- **Absolute-minimum fallback, if only one external labeler can be found.** The operator and one external reader
  are the two first-pass readers. There is no adjudicator, so disagreements stay `unresolved` and count as
  non-successes. The readout discloses that "one reader is the project maintainer". This requires an **ADR-recorded
  exception** to `training-pilot-packet.md` §5 and to S3's non-author preference. It is weaker evidence, and the
  public statement must say so.

---

## 7. If nothing is sourced: what stays blocked and what must be disclosed

- **Blocked:** HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 (rows 184–187); `D-R10-HUMAN-1`, `D-R6.1-EVAL`,
  `D-P30.2b-1/-2`, `D-R10-USERS-1`, `D-P32.16-1`, `D-P32.3-1`, `D-R7.2-SEND`, `D-P21.7-1`; the six rights rows;
  SIG-EVAL-001/002/005/006/007, SIG-UI-001, SIG-GOV-012/013/015.
- **Public copy must say:**
  - Resolution thresholds are provisional and LLM-bootstrapped. No "human-verified" wording (F-06).
  - The hostile-reader review is not performed (NEW-1).
  - No independent reviewer has checked the research dossiers.
  - The intake receiver is not operating (F-03).
  - Publication rests on operator dispositions, not a written counsel opinion.
  - Coverage is thin where sources are gated or states restrict records requests to residents.
- **None of this blocks deterministic engineering, activation or truth-repair work.** Theses T3 and T5 hold.

---

## 8. Findings raised (→ `findings/incoming/E3.csv`)

| id | sev | summary |
|---|---|---|
| NEW-1 | S1 | The public `/editorial-standards/` hostile-reader review (SIG-UI-042) comes from a fixture: placeholder "Reviewer A/B", review date 2026-08-19 before the first repo commit (2026-08-20), committed in P15.5 (Devin co-author) whose acceptance item is marked *(agentic)*. No human provenance, yet the matrix marks it MET. |
| NEW-2 | S2 | The human-evaluation reviewer workflow needs each reviewer to hold a PostgreSQL login and hand-edit JSON workbooks. There is no reviewer UI, and hosted `sig-pg` allows 0 authorized networks, so non-technical external reviewers cannot take part. |
| NEW-3 | S2 | The H4 dossier semantic review would review dossiers composed from hand-authored stand-ins. It must follow the live return passes or be scoped as a stand-in review. |
| NEW-4 | S2 | The counsel obligations required by SIG-LIC-009, SIG-INGEST-037 (robots deviation) and the EU database right have no OPEN row. `D-LEGAL.1-1` and `D-P30.3-COUNSEL` were closed DONE without any counsel document, and two counsel-flagged sources (Lexington indemnity, MD iMAP) were flipped under GL-GATE-07. The 36-row owed register therefore undercounts human work. |
| NEW-5 | S2 | Neither usability protocol can currently test the live public site: P32.24 is limited to staged synthetic releases, and the onboarding study needs the loopback-only `/curate/submit/`. |
| NEW-6 | S3 | `D-JURIS.2-1`'s only remaining blocker is Belgian eID (HG-04), which the operator cannot fill. `D-SOURCES.2-2`'s packets already conclude "restrictive/ineligible", so the owed act is a recorded decline. |
| NEW-7 | S3 | The hosted count of legacy `sig.org.name` keys has never been measured, so `D-P32.3-1` reviewer effort cannot be sized (1.7–42 h range). |
| NEW-8 | S2 | Even with zero errors, the smallest valid campaign for the 0.98 gate is n = 149 for one tier, and the pass probability is only 0.22–0.43 at a true precision of 0.99. A 2% `insufficient_evidence` rate makes the gate unreachable. The campaign's aim must be chosen explicitly. |

---

## 9. Questions for the operator (inputs to Q-8, F4, E2)

- **Q-E3-1 Time.** How many hours per week can you give personally? The minimal program needs about 70–200 operator
  hours over about 3–5 months.
- **Q-E3-2 Cash.** What is the one-off ceiling: $0, about $5k, or about $25k? Are paid reviewers or participants
  acceptable?
- **Q-E3-3 Aim.** Should H5 (a) attempt certification (one tier, n = 149–236) or (b) measure only (n ≈ 100) and keep
  auto-write PROVISIONAL? Which tier: 1, 3, or both?
- **Q-E3-4 Roles.** May you hold custodian and method-reviewer seats, and possibly adjudicator, with public
  disclosure and an ADR exception to the §5 firewall?
- **Q-E3-5 Outreach.** Do you authorize recruiting from DeFlock, EFF/Atlas, MuckRock or academic networks? Do you
  have existing contacts?
- **Q-E3-6 Counsel.** Who gave the counsel determinations recorded on 2026-09-16 (ADR-086) and 2026-09-24
  (ADR-106)? Would they write one dated opinion? If not, may we seek a pro bono referral or a clinic?
- **Q-E3-7 Intake.** Should the receiver open next phase? If so, who is the backup, or will you accept revised
  single-maintainer SLAs?
- **Q-E3-8 Officer naming.** Does it stay default-no-publish, so no second publication reviewer is needed?
- **Q-E3-9 Hostile-reader claim.** Should the `/editorial-standards/` hostile-reader claim be corrected in the first
  Round-11 tickets?
- **Q-E3-10 Records filing.** Are you willing to be the consenting filer for jurisdictions without a residency rule?
- **Q-E3-11 Legal home.** Is pursuing a fiscal sponsor in scope for this phase?

---

## 10. External sources (accessed 2026-09-30; all are external estimates, not quotes to SIG)

- Great Question, research incentives guide: <https://greatquestion.co/blog/customer-research-incentives-guide>.
  $60–100/h consumer, $100–150/h professional, median moderated $75/h.
- User Interviews, incentive guide/calculator: <https://www.userinterviews.com/blog/the-user-research-incentive-calculator>
- Prolific payment principles: <https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-principles>.
  £6/$8 minimum, £9/$12 recommended.
- Annotation rates: <https://riseuplabs.com/freelance-data-annotators-for-hire/>;
  <https://www.secondtalent.com/resources/data-annotation-costs-by-country-comparing-global-rates/>.
  Upwork $10–35/h; senior/QA $28–40/h; domain experts $40–100/h.
- OSMF Organised Editing Guidelines: <https://osmfoundation.org/wiki/Organised_Editing_Guidelines>. Wiki page plus
  community post "no less than two weeks before the activity is started".
- MuckRock: <https://accounts.muckrock.com>; <https://www.muckrock.com/about/how-we-work/>. Free / $20 (4 requests)
  / $40 per month Professional (20 requests) / $100 per month Organization.
- RCFP legal hotline: <https://www.rcfp.org/reporters-committee-hotline/>; <https://rcfp.org/what-we-do>
- EFF legal assistance and Cooperating Attorneys: <https://eff.org/pages/legal-assistance>;
  <https://www.eff.org/deeplinks/2020/08/digital-rights-ground-view-effs-intake-desk>
- OSM-US and Harvard Cyberlaw Clinic on ODbL (2016): <https://openstreetmap.us/news/2016/02/law-clinic/>
- Clio Legal Trends 2025 rates: <https://clio.com/resources/legal-trends/compare-lawyer-rates/>. Average $349/h.
- Fiscal sponsor fees: <https://help.hcb.hackclub.com/article/18-what-is-the-fiscal-sponsorship-fee-and-how-much-is-it-why-does-hcb-take-a-fiscal-sponsorship-fee-how-does-it-compare-to-other-fiscal-sponsors>
  (7%); <https://buildingblocks.superbloom.design/fiscal-sponsorship/> (OSC 10%, typical 8–15%).
- EFF / UNR Atlas of Surveillance: <https://atlasofsurveillance.org/about>;
  <https://www.unr.edu/nevada-today/news/2019/eff-and-rsj-student-partnership>
- DeFlock: <https://github.com/FoggedLens/deflock>; <https://blog.deflock.me/deflock-mobile-guide/>
- OSF Registries (free preregistration): <https://casrai.org/guides/osf-preregistration>

## 11. Repository evidence read

- Planning inputs: `META_PLAN.md` §3, §6 (E3 and neighbors), §7–§9, Appendices A–C; `baseline/BASELINE.md`
  (git, CI, production); `findings/incoming/A1.csv` (schema).
- Tickets: `docs/tickets/184_HUMAN-H4__*.md`, `185_P32.22a__*.md`, `186_HUMAN-H5__*.md`, `187_P32.23__*.md`.
- Evaluation packet: `docs/evaluation/{README,rubric,training-pilot-packet,reviewer-provisioning,measured-time-worksheet,human-campaign-marker-packet}.md`;
  `docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md` §1, §5, §7, §8, §10, §13.
- Governance and usability: `docs/governance/intake-receiver-operating-packet.md`;
  `docs/governance/hostile-reader-review-dossier.md`;
  `docs/build/reports/p32.24-investigation-journey-verification/USABILITY_TASK_PROTOCOL.md`;
  `docs/build/reports/USABILITY_STUDY.md`; `docs/governance/contributor-onboarding-usability-study.md` (grep).
- Owed register: `docs/tickets/DEFERRALS.md` rows D-R10-HUMAN-1, D-R6.1-EVAL, D-P30.2b-1/-2, D-R10-USERS-1,
  D-P32.3-1, D-P32.16-1, D-R7.2-SEND, D-P21.7-1, D-JURIS.2-1, D-SOURCES.2-2/7-1/8-1/9-1/9-2/9-4/12-1,
  D-R10-SOURCES-1, D-R10-PUBLISH-1, D-R7.1-AUTH, D-LEGAL.1-1, D-P30.3-COUNSEL, D-P21.4-1, D-P21.4-2,
  D-R10-LIVE-1 (grep). Every row that mentions "counsel" was status-checked (`grep -i counsel`). Note that many
  DEFERRALS status dates are future-dated relative to today (F-21); they are cited as recorded, not as true dates.
- Spec `docs/2_canonical_design_spec.md`: :4494-4497, :5290 (grep line only), :5519-5554, :5715-5730,
  :5996-6006, :6190-6200, :6324-6326, :6460-6475, :6510-6560, :6815-6840, :7319-7331 (grep lines), :9370-9371.
- Go-live spec `docs/3_sig_golive_spec.md` :85-101. `docs/build/COVERAGE_MATRIX.csv` rows (grep).
- ADR-086, ADR-106 (grep). Code and config: `ops/config.toml [intake]`; `policy/src/policy/data/takedown.toml`;
  `resolution/src/resolution/data/camera_site_rules.toml:41-47`;
  `resolution/src/resolution/human_eval_pg.py:669-706`; `web/src/lib/corrections-methodology-fixture.ts:189-215`.
- Dossiers: `docs/build/reports/p32.{18,19,20}-*/*_dossier.json` (counts of `ledger`, `answers`, `review`);
  `tests/connectors/fixtures/dossier/SOURCES.md`.
- Git: `git log` of `2b361f18` (P15.5; Co-Authored-By Devin) and of the first commit `a33177c7` (2026-08-20).
- Live read: `curl https://surveillancegraph.org/editorial-standards/` at 2026-09-30T16:41:27Z → 200; the page text
  includes "Reviewers Reviewer A (counsel stance); Reviewer B (counsel stance) Review date 2026-08-19".
