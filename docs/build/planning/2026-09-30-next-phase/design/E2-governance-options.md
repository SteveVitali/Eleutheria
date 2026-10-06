# E2 — Option memos per contradiction (governance, rights, evaluation, record integrity)

Row **E2** of `META_PLAN.md` (Stage P, stream E). Owner D, read-only.
Written 2026-09-30T17:10Z onward (`date -u`) in the planning worktree at `fddfc1b4` (branch `claude/next-phase-planning`,
chain tip `b051732c`). Primary input: `research/E1-contradictions.md` (E1-01…E1-21, cross-cutting X-1/X-2). Also read:
`META_PLAN.md` §2, §3, §6 (E rows), §7/§7.1, §8; `research/E3-human-work.md`; `design/E4-rights-packets.md`;
`findings/FINDINGS.csv` (F-01…F-44) and the incoming CSVs (A1, A3, E1, E3, E4, G1, H1, J1). Code and records re-checked
in this row are listed in §10. Incoming findings: `findings/incoming/E2.csv` (NEW-1…NEW-3).

> **Not legal advice (P4).** This document lays out options, consequences and plain-language risk. It does not say
> what the law requires or whether anything is lawful. Where an option turns on law, the memo says so and §7 lists
> the questions a qualified lawyer would need to be asked. "Exposure" lines describe what could go wrong in ordinary
> words; they are not assessments of liability. **Every piece of public wording below is *agent-drafted*** and must
> be confirmed verbatim by the operator before it ships (META_PLAN §2). Recommendations are the agent's; every
> decision is the operator's, taken at S5 (Q-7, recommendation "decide at S5").

**How to read a memo.** Each memo gives: the contradiction in one sentence (with E1 refs) · the facts that matter
for the decision · options — **(a) amend the spec** (an ADR-recorded waiver or redefinition, with compensating
controls, disclosure wording and a revisit trigger), **(b) keep it owed with a feasible plan** (who, from E3's roles
R1–R15, effort, cost, lead time, and what stays disclosed or blocked), **(c) hybrid**, and where relevant **(d) remove
the offending public claim now** · consequences per option for the site's honesty, for exposure, and for the build ·
a recommendation with the **one-line decision** the operator would record (a proposed `Q-E2-nn` row; the orchestrator
numbers it Q-29+ at S5, single writer) · dependencies.

**Conventions.** Human effort and cost figures marked [E3] come from `research/E3-human-work.md` (themselves planning
estimates and web figures). Engineering sizes marked [est] are this row's rough guesses, not measurements. Evidence
classes as P1. Verdicts named in (a)/(c) options use the proposed §8.3 vocabulary (`MET-ENGINEERED`, `WAIVED(ADR)`),
which is itself decided at S5 (memo E2-16). "ADR" always means a **new** ADR (landed ADR bodies are never edited,
SIG-ENG-003); spec changes go through `docs/research/_meta/spec_src/` + `BUILD.sh`; the go-live spec
(`docs/3_sig_golive_spec.md`) is a hand-edited file (F-35). No planning row edits any of these (P10); Stage B (T1)
writes them.

---

## 0. Decision table — one line per memo

Answer each line with the option letter, or the recommended one-line decision verbatim (§8 lists them in full).
"Counsel?" = the option set includes a question only a qualified lawyer can answer (§7).

| memo | E1 | group | decision needed | options | recommendation | counsel? | Q |
|---|---|---|---|---|---|---|---|
| **E2-02** | E1-02 | 1 honesty | What `/editorial-standards/` may say about the hostile-reader review | d remove now · b perform a real review · a waive SIG-UI-042 · c = d + b | **c** — remove the fixture now, keep the MUST, schedule one real review (operator + 1 external) | no | Q-E2-01 |
| **E2-07** | E1-07 | 1 honesty | Make the crawler policy text match the crawler | fix now to current behaviour · wait for E2-06 | **fix now**, same ticket as E2-06/E2-08, new ADR on the `robots_policy` field | no | Q-E2-02 |
| **E2-08** | E1-08 | 1 honesty | Crawler contact URL on an unregistered domain | register `sig-project.org` · move to `surveillancegraph.org` · both | **both** — defensive registration now, move UA + publish page in Round 11 | no | Q-E2-03 |
| **E2-12** | E1-12 (+J1 NEW-2/3) | 1 honesty | Missing and wrong upstream attribution in live data | fix as defect · interim attribution page · withdraw compartments | **fix as defect** (no spec change) + interim page + publish-time check | optional | Q-E2-04 |
| **A-1** | (F-03, routed to E2) | 1 honesty | "One-click dispute" promised on every page; no channel exists | d honest text + one contact · b open the receiver · c = d then b | **c** | no | Q-E2-05 (+Q-27) |
| **E2-01** | E1-01 | 2 governance | SIG-PUB-008 two independent reviewers vs sole-maintainer "waiver" | a waive · b recruit a 2nd reviewer · c requirement stands, nobody named | **c** | no | Q-E2-06 |
| **E2-03** | E1-03 | 2 governance | Editorial board "exists" vs none | a amend to single maintainer · b constitute a board · c interim authority + public decision log | **c** | no | Q-E2-07 |
| **E2-04** | E1-04 | 2 governance | Legal home: individual vs sponsor/nonprofit before launch | a amend (individual) · b sponsor/entity · c interim ADR + counsel questions + resource list | **c** | **yes** | Q-E2-08 |
| **E2-10** | E1-10 | 2 governance | SIG-SEC-003 transparency report + demand posture: unowned | a relax · b full incl. canary · c posture + counts now, canary declined | **c** | review requested | Q-E2-09 |
| **E2-05** | E1-05 | 3 legal | Counsel requirements vs no counsel document | a amend to operator basis · b obtain an opinion · c label + re-record now, seek one opinion, dated fallback to a | **c** | **yes** | Q-E2-10 (+Q-26) |
| **E2-06** | E1-06 | 3 legal | Robots disregarded without the counsel step; opt-out and reservation MUSTs unbuilt | a amend 037 · b re-gate robots pending counsel · c confirm/narrow + build controls + counsel question | **c** | **yes** | Q-E2-11 |
| **E2-09** | E1-09 | 3 legal | Stage-0 outreach MUST vs WONTFIX (no ADR) | a make it SHOULD · b contact all 19 · c amend timing, contact live projects | **c** | no | Q-E2-12 |
| **E2-11** | E1-11 | 3 legal | GL-GATE-07 blanket approval vs fail-closed rights + counsel on DB right | a recognise operator-accepted basis · b revert to per-source review · c recognise with guardrails + re-decide out-of-rule rows | **c** | **yes** | Q-E2-13 (+Q-19) |
| **E2-13** | E1-13 | 3 legal | ODbL residual: one map over all compartments on operator-reported clearance | a accept by ADR · b counsel · c keep map, re-record basis, counsel question | **c** | **yes** | Q-E2-14 |
| **E2-14** | E1-14 | 4 evaluation | Independent human evaluation vs four deferrals and model-made labels | a disclosed model-assisted standard · b E3 minimal program · c keep MUST, fix wording, pilot sets the aim | **c** | no | Q-E2-15 (+Q-24/25/28) |
| **E2-15** | E1-15 | 4 evaluation | Moderated usability study WONTFIX, verdict MET | a amend out · b run as specified · c contributor system "not complete"; live-site reader study instead | **c** | no | Q-E2-16 |
| **E2-16** | E1-16, X-2 | 4 evaluation | Scoped acceptances and waived items recorded MET / DONE | a redefine MET · b re-verdict MET-ENGINEERED / WAIVED(ADR) | **b** | no | Q-E2-17 |
| **E2-17** | E1-17 | 5 record | Agent-drafted, future-dated gate signatures | a stand · b re-confirm · c supersede GATE-G3, re-confirm the rest, add rule | **c** | no | Q-E2-18 (+Q-12) |
| **E2-18** | E1-18 (+F-22) | 5 record | Go-public ran with gates skipped; records unreconciled; history deleted | a amend go-live spec + supersessions + restore deleted rows · (take site down) | **a** | no | Q-E2-19 |
| **E2-19** | E1-19 | 5 record | Normative text asserts future-dated events | correct via B1 | **correct** | no | Q-E2-20 |
| **E2-X1** | X-1 | 5 record | Tentative/instructional words recorded as decisions | a leave · b operator confirms · c confirm + forward rule | **c** | no | Q-E2-21 |
| **E2-20** | E1-20 | 5 record | "Narrowly excellent at US ALPR" vs international all-camera | a amend · b reaffirm and demote · c breadth with per-layer quality labels | **decide at D3**; ADR either way | no | Q-E2-22 |
| **E2-21** | E1-21 | 5 record | Software Heritage deposit declined on a lapsed rationale | a drop · b deposit · c scan history, then deposit | **c** | no | Q-E2-23 |

**Count.** 22 memos (one per E1 entry, plus X-1): group 1 = 4, group 2 = 4, group 3 = 5, group 4 = 3, group 5 = 6;
plus **A-1**, an adjacent memo for F-03, which A2 routed to E2.

### 0.1 Honesty fixes that need no policy decision

These correct public or public-repo statements that are false today. The operator's recorded decisions already imply
them, or no decision covers them at all. The only open choices are wording (agent-drafted, operator-confirmed) and
timing. **Timing:** during planning, production is read-only (P3), so a fix before Round 11 needs a **Track-0 go per
action**. Otherwise these are the **first Round-11 tickets**. Any republish must use the single allow-listed publish
path (G1 NEW-6), never a hand `rsync` (the cause of F-02).

| # | fix | where | severity | memo | size [est] |
|---|---|---|---|---|---|
| H-1 | Replace the fixture hostile-reader review with "not yet performed". This needs a **code** change: the build gate throws on a truthful record (NEW-1) | `web/src/pages/editorial-standards.astro`, `web/src/lib/editorial.ts`, test, `docs/governance/hostile-reader-review-dossier.md` | S0 | E2-02 | ≤1 day + republish |
| H-2 | Per-source attribution in rights records, exports, API and map; fix the "DeFlock community map" misattribution; valid licence ids and URLs in `datapackage.json`; amend the `LICENCES.json` per-row promise until fixed | `db/claim_sink.py:955-973` (root cause per J1), `exports/`, `web/` map attribution | S0 (J1 NEW-2 ruling) | E2-12 | 2–4 days + hosted re-export |
| H-3 | Replace the "one-click dispute" promise with the operated truth. Choosing the contact mechanism is Q-E2-05; removing the false promise is not a choice | all pages, `/dispute/`, governance doc `:30` | S0 (F-03) | A-1 | ≤1 day |
| H-4 | `/methodology/` "the frozen, human-verified holdout" → accurate provenance; relabel the "LLM adjudicator vs maintainer seed" κ row | `web/src/lib/resolution-eval.ts:67` and the κ row source | S1 (F-06, E1 NEW-10) | E2-14 | ≤0.5 day |
| H-5 | API `/terms` "referral to the SIG editorial board and … counsel"; governance doc "an editorial board exists", "not a public launch" | `api/src/api/terms.py:32-33`; `docs/governance/governance-and-code-of-conduct.md:22,57,66` | S1 | E2-03, E2-18 | ≤0.5 day (API redeploy) |
| H-6 | Add the publication-basis label the operator's own GL-GATE-02 decision required "in every artifact". Its second clause ("before real public exposure") is now past, so the text is updated | `manifest.json`, `LICENCES.json`, `datapackage.json`, `/methodology/`, footer | S1 (E1 NEW-3) | E2-05 | ≤1 day |
| H-7 | Crawler: "honor robots" text in the executable policy, registry and letter; contact URL on a non-existent domain | `policy/…/crawler_conduct.toml`, `crawler.py:9-11`, `sources.toml`, `net.py:61` + 3 sites | S1/S2 | E2-07, E2-08 | 1 day + image rebuild |
| H-8 | Records that say "counsel" with no document; deferrals closed `DONE` for waived items | `sources.toml` `rights_reviewed_by` (5 rows); DEFERRALS (appended corrections, Stage B) | S1 (public repo) | E2-05, E2-16 | small |
| H-9 | The web publication gate default-allows US public-employee names (latent, not live) → default-deny unless a concurrence record exists | `web/src/lib/publication.ts:36-40,66-77` | S2 (E1 NEW-12) | E2-01 | ≤1 day |

H-1, H-3, H-4 and H-5 are copy and small-code changes that could ship in **one** site republish. H-2 needs a hosted
re-export. H-7 needs every ingest image rebuilt (G1 NEW-10).

### 0.2 Decisions that truly need the operator

These are the choices with real trade-offs that only the operator can make. Everything else in §0 is close to
mechanical once the operator accepts the recommendation.
1. **Governance posture** (Q-E2-06, -07): run openly as a disclosed single-maintainer project, with naming off and a
   public decision log, or recruit a second reviewer and a board now.
2. **Legal home** (Q-E2-08): keep the disclosed individual home as an interim, or pursue a fiscal sponsor or entity.
   This interacts with counsel.
3. **Counsel path and deadline** (Q-E2-10, with Q-26): who (if anyone) gave the 2026-09-16/24 "counsel" answers;
   whether to seek one written opinion (pro bono ≈ $0, 1–4 months; paid ≈ $3.5k–10.5k [E3]); and what happens if none
   arrives.
4. **Robots** (Q-E2-11): re-confirm GL-GATE-08 in the operator's own words or narrow it (for example, honour explicit
   refusals on non-US hosts).
5. **Database-right basis** (Q-E2-13, with Q-19): keep operator risk acceptance as a disclosed basis with guardrails,
   or return to evidenced per-source review.
6. **Human evaluation** (Q-E2-15, with Q-24/25/28): keep the MUST and staff the pilot, or amend to a disclosed
   model-assisted standard.
7. **Outward contact** (Q-E2-12, Q-28): authorize contacting ecosystem projects and recruiting reviewers.
8. **Confirmations only the operator can give** (Q-E2-21): the robots decision, the "counsel" attestation and the
   human-review deferral, in the operator's own words.
9. **Design centre** (Q-E2-22): at D3.
10. **Contact mechanism and SLAs** (Q-E2-05, with Q-27): whose address, and what response times.

### 0.3 Dependency map

```
Q-E2-21 confirmations (X-1) ──► E2-05 counsel ──► E2-04 legal home ──► E2-03 board ◄──► E2-01 reviewers ◄──► E2-02 review page
             │                    │ (one packet, §7)      └────────► E2-10 demand posture ◄── A-1 contact channel
             │                    ├──► E2-06 robots ──► E2-07 policy text ──► E2-08 crawler page/UA ◄── A-1
             │                    ├──► E2-11 DB-right basis ◄── Q-19 (new sources, Stream I)
             │                    └──► E2-13 ODbL
             └──► E2-14 human eval ──► E2-15, E2-16 (verdict vocabulary, F2/T4) ◄── Q-24/25/28, F4
E2-12 attribution fix ──► E2-09 outreach (correct misattributed upstreams) ; ──► E2-11/E2-13 (attribution on those rows)
E2-17 readouts ◄──► E2-19 dates ◄──► B1/B4 ; E2-18 gate records ◄──► B2/B3 (restore deleted rows) ; E2-20 ──► D3
All group-1 site fixes ──► one republish via the fixed publish path (G1 NEW-6)
```

Three hubs decide most of the rest: **(1) the X-1 confirmations** (cheap; do first at S5), **(2) the counsel path**
(one packet feeds E2-04/05/06/10/11/13 and E4 R2b/R4d), and **(3) the governance posture** (E2-01/03/04).

---

## 1. Group 1 — public false or overstated claims (fix regardless)

### E2-02 — A fixture "hostile-reader review" presented live as a real release gate (E1-02 · S0)

**Contradiction.** SIG-UI-042 requires a recorded two-reader hostile-reader review before a dossier template ships.
The live `/editorial-standards/` page shows one as completed ("Reviewer A (counsel stance); Reviewer B", 2026-08-19,
"Releasable"). It is a fixture constant, no reviewer exists, the date predates the repository, and the linked
`/dossier/oklahoma-city/` returns 404 (E1-02; E1 NEW-1; E3 NEW-1).

**Facts for the decision.**
- The gate `assertReviewReleasable` (`web/src/lib/editorial.ts:221-235`, `code`, this row) **throws unless two or
  more reviewer names are present**. Its only caller is the standards page (`editorial-standards.astro:26`), so a
  truthful record (0 reviewers) **fails the web build**. No dossier page consults the gate: "release is blocked until
  every finding is dispositioned" blocks no dossier release (**NEW-1**). The unit test pins at least 2 reviewers
  (`web/tests/unit/editorial.test.ts:78-79`).
- A real review costs 2 readers × 3 dossiers × 1–2 h + 1–2 h disposition = **7–14 h** [E3 R5]. The operator may be
  one reader, with disclosure; the other must be external. Sourcing: journalist networks, a paralegal or law student,
  or a civic-tech researcher. Cost is $0 (volunteer) or about $120–700 paid (3–7 h at $40–100/h) [E3 rates]. Lead time
  is 2–6 weeks.
- The P32.18–20 research dossiers are built from stand-in documents (E3 NEW-3), so the review should use a **live
  public dossier render** (e.g. `/dossier/al/`).

**Options.**
- **(d) Remove now.** The page renders a "not performed" state instead of fixture data, the test is updated, a dated
  correction is appended to `docs/governance/hostile-reader-review-dossier.md`, and COVERAGE SIG-UI-042 moves from
  MET to MISSING. No ADR is needed: this is a defect fix.
  *Agent-drafted wording:* "**Hostile-reader review — not yet performed.** Our standard is that two reviewers
  independently read a real rendered dossier from the point of view of the documented organization's lawyer, log
  every sentence they would challenge, and resolve each finding before a dossier template is released. No such review
  has been performed for the current template. An earlier version of this page showed placeholder reviewers from test
  data; that was an error and has been removed."
- **(b) Keep owed and perform it.** Two readers (operator + 1 external, disclosed) review a live dossier, and the
  findings are dispositioned. In the same ticket, the gate moves into the **dossier build** so that it gates
  something ([est] 1–2 days).
- **(a) Amend.** An ADR waives SIG-UI-042, so dossier templates ship without an adversarial read. Compensating
  controls (existing): style-guide register rules (SIG-UI-045/046) and evidence links. Revisit trigger: the first
  dispute from a documented organization.
- **(c) Hybrid** = (d) now + (b) scheduled.

| option | site may / may not claim | exposure (plain) | build |
|---|---|---|---|
| d | may describe the standard and say it is owed; may not show reviewers, a date or "releasable" | removes a record that reads as fabricated; while it stays up it discredits every other claim on the site for anyone who checks | web ticket, COVERAGE, governance-doc correction |
| b | after the review: real roles, date, findings | an operator-reader is a weaker check (disclosed) | human session + dossier-build gate ticket |
| a | may not claim any adversarial review | dossiers are what advocates carry into council meetings; skipping the hostile read raises the chance an overstatement reaches the organization it describes | ADR + spec_src; verdict WAIVED(ADR) |
| c | as d, then b | lowest | both |

**Recommendation: (c).** *Decision line:* **"Remove the fixture review from /editorial-standards/ now and say it has
not been performed; SIG-UI-042 stays a MUST (verdict MISSING) and one real two-reader review — me plus one external
reader, disclosed — is scheduled against a live dossier, with the gate moved into the dossier build."** (Q-E2-01;
answers Q-E3-9.)
**Dependencies.** E2-01 (the same false premise, "the published surface makes no two-reviewer claim"); Q-25 (operator
seat); Q-28 (recruiting); the G1 publish path.

### E2-07 — The executable crawler policy, registry and outreach letter say "honor robots" (E1-07)

**Contradiction.** SIG-INGEST-036 requires a published Crawler Conduct Policy that binds every connector. The policy
the code serves (`crawler_conduct.toml` rule 2, via `conduct_rules()`), the `crawler.py:9-11` docstring,
`robots_policy = "honor"` on 235 permitted registry rows, and the Stage-0 outreach letter all say SIG honours
robots.txt. Meanwhile `net.py:382-393` proceeds and stamps `robots_disregarded` (E1-07; E1 NEW-6).

**Facts for the decision.** ADR-088 kept `robots_policy = "honor"` as "accurate declarations of posture", so changing
what the field means needs a new ADR. The registry is not public yet, but Stream J plans to publish it (J1 NEW-7). At
that point 235 "honor" values become public false statements. The letter has not been sent, but E2-09 may send it.

**Options.** (1) **Fix now** so the text describes current behaviour: robots verdicts are recorded on every fetch and
do not gate, plus whatever E2-06 adds. Either retire the `honor` values or document the field as "posture declared
at review time; not enforced". Correct the letter before any send. [est] ≤1 day. (2) **Wait** for E2-06: this leaves
false text in the public repo until an S5-derived ticket and gains nothing. (a)/(b) do not apply: nobody proposes
keeping text that contradicts the code.

| option | site / repo may claim | exposure (plain) | build |
|---|---|---|---|
| 1 | exactly what the crawler does | a written policy that contradicts behaviour is what a site operator or journalist would cite as bad faith | new ADR (field semantics), data and docstring edit, test |
| 2 | nothing new; the false text stays | as above, for longer | none now |

**Recommendation: (1), in the same Round-11 ticket as E2-06's outcome and E2-08's page.** If E2-06 re-gates robots,
the old text becomes true again and only the field documentation changes. *Decision line:* **"Bring
crawler_conduct.toml, the crawler.py docstring, the registry robots_policy field and the outreach letter into line
with the E2-06 outcome in one ticket, with a new ADR superseding ADR-088's 'accurate declarations' clause; the policy
of record is crawler_conduct.toml, published on the crawler page."** (Q-E2-02.)
**Dependencies.** E2-06 (content), E2-08 (where it is published), E2-09 (letter), J3 (registry export).

### E2-08 — The crawler's contact URL is on a domain nobody owns (E1-08)

**Contradiction.** SIG-INGEST-011 and §26 rule 1 require a user agent with a contact URL and an explanation page.
Every production fetch sends `+https://sig-project.org/data-collection`, but that domain is not registered (NXDOMAIN;
whois "Domain not found") and no explanation page exists anywhere (E1-08; E1 NEW-2). No operator decision covers it.

**Facts for the decision.**
- The URL is hard-coded in four places: `net.py:61`, `transports/httpx_transport.py:66`, `tasks/maproulette.py:219`
  and `procurement_portal_tenants.toml:45`.
- Code and config are baked into the images, across 4 different ingest builds (G1 NEW-10). A code change therefore
  reaches production only after every ingest image is rebuilt and redeployed.
- Until then, anyone can register the domain and receive the complaints and opt-outs that site operators send to SIG.

**Options.**
- **(1) Register `sig-project.org` now.** This is an operator purchase outside GCP (not a production mutation), but
  it is still an outward act that needs the operator's go. Cost ≈ $10–30/year [est; registrar prices vary]. Point
  `/data-collection` at the explanation page. It closes the capture window immediately.
- **(2) Move the user agent** to `https://surveillancegraph.org/data-collection/` and publish that page as a
  zero-JS content page. This is a Round-11 ticket plus an image rebuild.
- **(3) Both:** (1) now as a defensive hold, then (2), with the old domain redirecting to the new page.
- *Page content (agent-drafted outline):* who runs the crawler; what it collects (public records; no personal or
  plate data by design); the conduct policy (E2-07); the robots posture stated plainly (E2-06); rate limits; how to
  opt out (E2-06 rule-7 register); a working contact (A-1).

| option | may claim | exposure (plain) | build |
|---|---|---|---|
| 1 | a reachable contact (once the page exists) | the capture risk ends; the old images keep working | operator purchase + DNS |
| 2 | a contact on the project's own domain | until every image is rebuilt, the old URL keeps going out unowned | ticket + image rebuild + page |
| 3 | both | lowest | both |

In plain terms, while the domain is unowned, a stranger could register it and receive, or answer, messages meant for
SIG. Site operators who try to object find nothing, which reads as evasion whatever the intent.

**Recommendation: (3).** *Decision line:* **"Register sig-project.org defensively now (my action), and in Round 11
move the crawler contact to surveillancegraph.org/data-collection/ with a published conduct and opt-out page,
redirecting the old domain."** (Q-E2-03.)
**Dependencies.** E2-06/E2-07 (page content), A-1 (contact), G1 NEW-10 (image rebuild), J3 (source pages could host
it).

### E2-12 — Required upstream attribution missing, and sometimes wrong, in live public data (E1-12; J1 NEW-2, NEW-3)

**Contradiction.** SIG-CONTRIB-020, SIG-API-004 and SIG-EXPORT-006 require every claim's upstream source to be named
in the UI, the API and exports. Instead:
- the live map credits "Surveillance data © SIG contributors" across 12 compartments;
- 61,603 download rows carry `rights_attribution_required = 1` with an empty attribution;
- 3,272 CC-BY rows, and the API's obligations for EFF Atlas data, are credited to the wrong upstream ("DeFlock
  community map").

All three ids are verdicted MET (E1-12; J1 NEW-2 — **orchestrator ruling S0**; J1 NEW-3).

**Facts for the decision.**
- Probable root cause (J1, `inference`): `db/src/db/claim_sink.py:955-973` reuses the first `rights_record` for each
  SPDX expression. The registry holds the correct attribution text.
- `datapackage.json` licence URLs return 404 (the SPDX id is `OGL-UK-3.0`).
- `LICENCES.json` promises "the per-row source attribution each record carries".
- No operator decision touches any of this.

**Options.**
- **Fix as a defect** (no spec change):
  - key rights records per source, additively: new rights rows and links, never `UPDATE` on the spine;
  - carry the attribution and terms URL into exports and the API;
  - build the map attribution from the compartments actually drawn (at minimum, a linked per-source list);
  - fix the licence ids and URLs;
  - add a **publish-time check** that fails when any attribution-required row is unattributed;
  - republish.
  [est] 2–4 days + a hosted re-export.
- **(d) Interim page:** a per-source attribution page listing each upstream, its licence and its terms URL, linked
  from the map, the downloads and `LICENCES.json`, which is amended to say per-row attribution is being repaired. It
  is cheap, but the spec says aggregate acknowledgement "is not sufficient", so it is **interim only**.
- **Withdraw** the affected compartments (public_record, operator_accepted, sig_graph, ogl_uk3, dot511_ccbysa2) from
  downloads and the map until fixed. This is the most conservative option; it removes most public rows and map layers
  for weeks [inference from the counts].
- **Compliance review** (E1's question): the mechanical checks are automatable and need no lawyer. Whether the lapse
  period calls for anything beyond fixing it, such as notifying licensors, is optional question Q-L10 (§7).

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| fix | after the fix: "every row names its source" | CC-BY, CC-BY-SA and OGL allow reuse **on condition** of attribution; missing credit is the usual way those conditions are broken, and crediting the wrong source is a false public statement about provenance | exports/db/web tickets; COVERAGE PARTIAL until fixed |
| d (interim) | an honest list; not per-row attribution | reduces but does not remove the gap | small web/J3 ticket |
| withdraw | nothing about withdrawn layers | smallest licence exposure; largest loss of public value | republish without the compartments |

**Recommendation: fix as a defect, first wave, with the interim page in the same release or earlier; no withdrawal
unless the operator wants maximum caution.** Correct the record with the misattributed upstreams (DeFlock, the EFF
Atlas) as part of E2-09. *Decision line:* **"Treat attribution as a defect under the existing MUSTs: a first-wave
ticket fixes per-source attribution in rights records, exports, API and map, adds a publish-time attribution gate and
republishes; an interim sources-and-licences page ships no later than the fix."** (Q-E2-04.)
**Dependencies.** J3/J4 (source pages), E2-09 (outreach after the fix), E2-11 and E2-13 (attribution for those rows),
the G1 publish path.

### A-1 — Dispute channel promised on every page but absent (F-03, routed to E2 by A2; adjacent)

**Contradiction.**
- Every page advertises a one-click, no-account dispute and correction channel.
- The governance doc names "the served `/corrections` and `/dispute` mechanisms" as the takedown contact of record
  (`governance-and-code-of-conduct.md:30`).
- In fact `/dispute/` has no form or address, `/intake/` returns 404, and the receiver is `receiver_not_operating`
  by design (F-03 S0; E1-10; E3 R10).

**Options.**
- **(d) Replace the promise now** with the operated truth and one monitored contact route. *Agent-drafted wording:*
  "**Corrections and disputes.** Our online dispute form is not operating yet. Email ‹address›. One maintainer reads
  this inbox; we aim to reply within 72 hours for privacy or safety issues, 7 days for legal or copyright matters and
  14 days for factual corrections, and replies may pause during absences." The times mirror `takedown.toml`
  (72 h / 168 h / 336 h); the operator may publish longer, honest single-maintainer times instead. Use a role address
  on the project domain rather than a personal inbox (operator's choice).
- **(b) Open the receiver** (Q-27). The operator owns it (R10). Setup is 4–8 h plus 2–4 h/week; covering the 72 h
  SLA through absences needs a backup with infrastructure access; retention must be ratified and hosted grants
  provisioned [E3 R10].
- **(c)** = (d) now + (b) once a backup exists.

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| d | "email us; one maintainer; these times"; not "one-click" | a site that names agencies and vendors but offers no working correction path makes every error harder to fix and pushes complaints to other routes (the host, the unowned crawler domain, lawyers' letters) | copy change + mailbox (operator) |
| b | an operating form, with SLAs | inbound personal data (reporters) must then be protected and retained per policy | G2 activation + ops |

**Recommendation: (c).** *Decision line:* **"Replace every one-click dispute promise with the operated truth now and
publish one monitored contact address with single-maintainer response times; open the receiver only when a backup
moderator exists (Q-27)."** (Q-E2-05.)
**Dependencies.** E2-10 (the counts on `/corrections/`), E2-08 (the same contact), E2-04 (who is named).

---

## 2. Group 2 — governance structure

### E2-01 — SIG-PUB-008 two independent reviewers vs the sole-maintainer "waiver" (E1-01 · safety)

**Contradiction.** SIG-PUB-008 requires two independent reviewers to concur in writing before a named individual is
published. Instead:
- the maintainer filled both reviewer roles, with independence "waived, not satisfied";
- that state is recorded `DONE` (D-P21.4-2) and verdicted MET;
- no ADR records it, and ADR-145 left the spec text unchanged (E1-01).

**Facts for the decision.**
- **The Python gate is enforced.** `policy/src/policy/officer.py:82-90` (`_concurrence_ok`) requires at least two
  distinct reviewer ids flagged independent, each with a written rationale. The only production caller
  (`okc_documents.py:231`) passes no reviewers, so every person-naming predicate is refused (`code`, re-read here).
- **The web gate has a latent gap.** `web/src/lib/publication.ts:36-40,66-77` lets a US public-employee name through
  on jurisdiction alone (E1 NEW-12). It is not live today.
- **Nobody is named today.** The recorded "waiver" therefore excuses nothing: it only matters on the day someone
  wants to name a person.
- **The second seat cannot be the operator** [E3 R6]. It costs 0 h while naming is off, then 0.5–2 h per decision. The
  E2-02 external reader could fill it later.

**Options.**
- **(a) Amend:** an ADR waives independence, so the maintainer may concur alone. The only compensating control is the
  maintainer's own judgment on the publication class most likely to cause harm. Revisit trigger: a second maintainer
  joins.
- **(b) Keep owed:** recruit a second independent reviewer (R6) before any naming. Cost $0 (volunteer); lead time 2–6
  weeks. Until then, naming stays off.
- **(c) Reframe (hybrid):**
  - The requirement **stands unamended**. The operated posture is "**no named individual is published**", not a
    waiver.
  - Fix the web gate to default-deny person names unless a concurrence record exists (H-9).
  - Coverage becomes `MET-ENGINEERED` (the human leg is owed on the trigger "a naming decision is wanted").
  - Append corrections to D-P21.4-2 and RISK-P0-05; the risk register still describes the control as
    two-reviewer concurrence.
  - *Agent-drafted disclosure:* "SIG does not publish the names of individual officers or officials. Our standard
    requires two independent reviewers to agree in writing before anyone is named; SIG currently has one maintainer,
    so no one is named."

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "one maintainer decides naming" | naming individuals on a surveillance-accountability site is the publication most likely to bring harassment of that person, or a complaint that SIG harmed their reputation; a single reviewer is exactly the set-up the spec was written to avoid | ADR + spec_src; WAIVED(ADR) |
| b | two-reviewer naming, once recruited | lowest once staffed | recruiting only |
| c | "no individuals named" | what remains: names inside quoted source documents (e.g. contract signature blocks, E4 S2) and the latent web gate until H-9 lands | H-9 ticket, ADR recording the posture, verdict change, appended corrections |

**Recommendation: (c).** *Decision line:* **"SIG-PUB-008 stands unamended; no named individual is published until two
independent reviewers exist; the web publication gate is fixed to default-deny person names; verdict MET-ENGINEERED,
with the human leg owed when naming is wanted."** (Q-E2-06; answers Q-E3-8.)
**Dependencies.** E2-02, E2-03 (under the spec, the board provides this concurrence), E3 R5/R6, Q-28.

### E2-03 — "An editorial board exists" vs none (E1-03 · safety)

**Contradiction.** SIG-GOV-015 requires an editorial board, distinct from the technical maintainers, for contested
claims, officer naming and sensitivity classifications. Instead:
- one person holds every role;
- the operator signed off the Part-VIII-sensitive classes on 2026-09-22 (`facial_recognition_world_map`,
  `pathways_rtcc_federation`, `pathways_acoustic_drone_location`, person naming);
- the public governance doc says "An editorial board exists" (`:57`, `:66`);
- the live API `/terms` refers abuse "to the SIG editorial board and, where applicable, to counsel"
  (`api/src/api/terms.py:32-33`) (E1-03; E1 NEW-7).

**Facts for the decision.**
- A board needs 2–3 people distinct from the maintainer, about 1–2 h/month plus decisions [E3 R6]. The operator
  cannot fill it.
- The existing code invariants (no person or plate fields, tier coordinate reduction, the officer gate) cover the
  mechanical half of what a board would guard.
- They do not cover *classification judgments* such as publishing a world map of facial recognition deployments.

**Options.**
- **(a) Amend GOV-015 to a single-maintainer model** by ADR.
  - Compensating controls, existing: the Part VIII invariants in code; naming off (E2-01).
  - To build: a **public editorial-decisions log** (date, decision, class, rationale, evidence links) for sensitivity
    classifications and contested claims, so transparency stands in for separation. The 2026-09-22 sign-offs are
    logged retroactively. [est] 1–2 days (static page from a data file).
  - Revisit trigger: a contested-claim dispute from a documented organization, naming wanted, a second maintainer, or
    a legal-home entity.
- **(b) Constitute a board:** 2–3 volunteers from journalism, advocacy or legal-academic networks. This is outward
  contact (Q-28). Lead time 1–3 months; cost $0. Board members take on reputational, and possibly legal, exposure for
  a project whose legal home is an individual. *Inference:* hard to recruit before E2-04 resolves.
- **(c) Hybrid:** (a) as the interim posture; (b) owed with a trigger (an entity exists or naming is wanted). The
  public text is fixed now (H-5).
  - *Agent-drafted governance-doc text:* "SIG does not yet have an editorial board. Until it does, editorial decisions
    (contested claims and sensitivity classifications) are made by the maintainer and recorded publicly in the
    editorial decisions log. Officer and person naming is turned off."
  - *Agent-drafted API terms text:* "…and — where the violation is an attempted re-identification of an individual —
    review by the SIG maintainer and any further action that review warrants."

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a / c | "decisions by the maintainer, logged publicly"; never "a board" | sensitivity calls (e.g. the facial-recognition world map) are the decisions most likely to cause harm if wrong, and one decision-maker means no second look; stating that a board exists when none does could matter if a dispute escalates | ADR + spec_src; decision-log ticket; H-5 |
| b | "an independent editorial board" once seated | lowest once staffed | recruiting, charter, log |

**Recommendation: (c).** *Decision line:* **"Correct the governance doc and API terms now; record by ADR an interim
single-maintainer editorial authority (naming off, Part VIII invariants in code, a public editorial-decisions log to
be built, with the 2026-09-22 class sign-offs logged retroactively); constitute a board when a legal-home entity
exists or naming is wanted."** (Q-E2-07.)
**Dependencies.** E2-01, E2-04 (entity → board), E2-10, Q-28.

### E2-04 — Legal home: an individual in personal capacity vs a sponsor or nonprofit before launch (E1-04 · legal)

**Contradiction.** SIG-GOV-012 requires a fiscal sponsor or nonprofit legal home before public launch, and
SIG-GOV-013 requires legal-defence resources identified "before they are needed". SIG has been public since
2026-09-16 with an individual in personal capacity as its legal home, no legal-defence resources and no ADR.
RISK-P0-13 still reads "no public launch without it" (E1-04).

**Facts for the decision.**
- **Sponsor or entity [E3 R15].** Applying to a fiscal sponsor takes 5–15 h. Fees are 7% (HCB) to 10% (OSC), 8–15%
  typical, charged on revenue, so they mainly matter if donations or grants flow [inference].
- **Liability is open.** Whether any sponsorship model or entity shields the operator from claims is uncertain; that
  is a counsel question [E3 inference].
- **The site is anonymous; the repo is not.** The live site names no operator or contact, while the public repo
  names the individual (E1-04).
- **The spec's own rationale:** "operating a project with this threat profile as an unincorporated individual effort
  exposes contributors personally" (`:6523-6526`).

**Options.**
- **(a) Amend by ADR:** the individual legal home becomes the operated posture.
  - Compensating controls, existing: data minimisation (no contributor data, SIG-SEC-002); no person or plate data;
    naming off.
  - To do: SIG-GOV-013 resources *identified*, not retained: a written list of referral routes (EFF Cooperating
    Attorneys, a law-school clinic, the RCFP hotline [E3]) and, optionally, a media-liability insurance quote (cost
    not researched).
  - Revisit triggers: the first legal demand or threat letter; the first external contributor, reviewer or board
    member; the first donation or grant; any counsel advice; naming wanted.
- **(b) Keep owed:** apply to a fiscal sponsor (operator 5–15 h, lead 1–3 months [est], fee on revenue only) or form
  an entity (state fees and ongoing compliance, weeks to months [est]). Counsel advises which (shared §7 packet).
- **(c) Hybrid:** (a) as a disclosed interim now; the legal-home questions go in the §7 counsel packet; the resource
  list is written now; sponsor or entity is decided after counsel answers.
- **Disclosure trade-off (operator's call).** "Operated by an individual maintainer" is truthful without naming
  anyone. Naming the person on the site raises their visibility, and harassment is in the spec's own threat model. The
  agent does not recommend naming the person beyond what the public repo already shows.
  - *Agent-drafted wording:* "SIG is currently run by an individual maintainer, not by an organization. It has no
    fiscal sponsor or incorporated legal entity yet."

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "run by an individual"; never "a nonprofit project" | by the spec's own reasoning, any claim against the project lands on one person; how much an entity or sponsor would change that is a lawyer's question | ADR + spec_src; RISK-P0-13 appended correction |
| b | the sponsor or entity once real | depends on counsel's answer | operator applications |
| c | as a, then as b | as a, with a dated plan to reduce it | ADR + packet + list |

**Recommendation: (c).** *Decision line:* **"Record by ADR the individual legal home as an interim, disclosed posture
with revisit triggers; put the legal-home questions in the counsel packet; decide fiscal sponsor vs entity after
counsel answers; list (not retain) legal-defence resources now."** (Q-E2-08; answers Q-E3-11.)
**Dependencies.** E2-05 (the same packet), E2-03 (board recruiting), E2-10, E2-18 (GL-GATE-01 records).

### E2-10 — SIG-SEC-003 transparency report and demand-response posture: unowned (E1-10 · legal)

**Contradiction.** SIG-SEC-003 requires three things:
- a transparency report on legal demands (received, complied with, refused);
- a warrant canary (SHOULD);
- a demand-response posture documented **before** the first demand.

None exists. No row or owner is recorded, and `/corrections/` shows intake counts from a channel that cannot receive
anything (E1-10; E1 NEW-5; F-03).

**Facts for the decision.** A legal demand would target:
- the `evidence_access_log` (requester, purpose), which the public API role can read (J1 NEW-9: a blanket grant; the
  engineering fix belongs to G1);
- infrastructure logs (G1 NEW-12: no Data Access audit logs);
- intake personal data, if the receiver opens (retention 30 days, 90-day ceiling).

**Options.**
- **(a) Relax:** amend to "posture documented when the first demand arrives", or drop the report until volume exists.
  This defeats the spec's own point ("before").
- **(b) Full, including the canary.** A canary needs one person to re-publish it on schedule; a missed update signals
  a demand that did not happen [inference].
- **(c) Hybrid:**
  - The operator adopts a written demand-response posture. Agent-drafted outline: what SIG holds and minimises; who
    receives legal process; preservation handling; the user-notice policy; publication of counts. Operator effort is
    3–6 h [est].
  - Counsel review is requested in the §7 packet. The draft is not legal advice.
  - `/corrections/` gains legal-demand counts (received, complied, refused) with an as-of date ([est] small ticket).
  - The canary is declined, with the rationale recorded.
  - A data-holdings inventory goes to G1, alongside the J1 NEW-9 grant fix.

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | nothing about demands | the first subpoena, preservation letter or takedown demand lands on one person, with deadlines and no plan | ADR + spec_src |
| b | report + canary | a lapsed canary is itself a false signal | posture, page, canary process |
| c | "legal demands received: N (as of date)" + a posture page | lower: a plan exists before it is needed; holding little data stays the main protection | posture doc, small web ticket, G1 inventory |

**Recommendation: (c).** *Decision line:* **"Own SIG-SEC-003 now: I adopt a written demand-response posture
(agent-drafted, confirmed by me, counsel review requested in the packet), the site publishes legal-demand counts, and
the warrant canary (a SHOULD) is declined with a recorded rationale."** (Q-E2-09.)
**Dependencies.** E2-04, E2-05 (packet), A-1 (channel and counts), J1 NEW-9 and G1 (what is held and who can read it).

---

## 3. Group 3 — legal and counsel-dependent

### E2-05 — Counsel requirements vs no counsel document on file (E1-05 · legal)

**Contradiction.** SIG-LIC-009, R-01, HG-02 and GL-GATE-02 require three things before launch:
- a referral to counsel;
- a counsel opinion on ODbL 4.4(b), the EU database right, officer naming, tiers and Part VIII;
- a "pending counsel" label in every artifact.

Yet no counsel-authored document exists. "Counsel" appears in the records only in three forms:
- operator-reported: 5 registry rows `rights_reviewed_by = "counsel (HG-02)"`, and ADR-086 and ADR-106 ("On
  2026-09-16 counsel resolved HG-02", ADR-086 body);
- operator-adopted agent drafts (D-LEGAL.1-1);
- an attestation read from instructional words (D-P30.3-COUNSEL).

The label appears in no public artifact (E1-05; E1 NEW-3; E3 NEW-4).

**Facts for the decision.**
- **Cost [E3 R7].** 10–30 counsel hours plus 5–10 operator hours. $0 (EFF referral or a clinic; lead time 1–4
  months) to about $3.5k–10.5k at $349/h. The operator cannot fill this role. An agent may draft the question packet,
  never the opinion.
- **An earlier source may exist.** Q-26 asks who gave the 2026-09-16 and 2026-09-24 determinations. If a real lawyer
  did, a short dated confirmation is the cheapest path.
- **Known risk.** RISK-P21-02 already warns that a recorded reviewer role could be mistaken for legal sign-off.
- **No owed row.** The owed register has no counsel row (E3 NEW-4).

**Options.**
- **(a) Amend:** an ADR plus spec_src changes.
  - SIG-LIC-009 becomes "SHOULD be referred to counsel; until then the operator's disposition is recorded and
    disclosed". HG-02 is redefined as an operator publication disposition.
  - Compensating controls, existing: per-compartment licences, the `assert_separated` / public-clean guard, the tier-0
    role, the officer gate.
  - To build: the basis label in every artifact (H-6), and a record rule: "counsel" appears in a record only with a
    reference to a dated document.
  - Revisit triggers: a licensor objection, a legal demand, a takedown under `takedown.toml`, naming wanted, or a
    counsel opinion filed.
- **(b) Keep owed:** one dated written opinion on the consolidated packet (§7, role R7). Stage B adds an OPEN
  DEFERRALS row. Until the opinion is filed, the label and the re-recorded entries stand.
- **(c) Hybrid:**
  - Now, with no decision needed: add the label (H-6) and re-record "counsel" entries as "operator-reported; no
    document on file" (H-8).
  - Ask Q-26. If a real lawyer gave the 2026-09-16/24 answers, ask them for a dated written confirmation (days to
    weeks). Otherwise seek a pro bono referral with the packet.
  - Set a date (suggested: the end of Round 11). If no opinion is filed by then, record (a) by ADR.
- *Agent-drafted label* (replaces the GL-GATE-02 text, whose "before real public exposure" clause is past):
  "Published on the maintainer's own rights and publication decisions. No lawyer's written opinion has been obtained;
  nothing here states that this publication has been cleared by counsel."

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "published on the maintainer's decisions"; never "counsel-cleared" | if a licensor, vendor or agency challenges the publication, no legal analysis is on file; with an individual legal home, that person carries it | ADR superseding ADR-086/106's counsel wording; spec_src; label |
| b | "reviewed by counsel on ‹date›" once filed | reduced to whatever the opinion leaves open | packet + OPEN row |
| c | the label now; the opinion's scope once filed | records stop claiming a clearance that cannot be shown, which is itself the larger credibility risk | label, re-records, packet, dated fallback |

**Recommendation: (c).** *Decision line:* **"Label every public artifact with the operated basis now and re-record
'counsel' entries as operator-reported with no document; seek one dated written opinion on a single consolidated
packet (starting with whoever gave the 2026-09-16/24 advice); if none is filed by the end of Round 11, record by ADR
that publication rests on my risk acceptance."** (Q-E2-10, with Q-26.)
**Dependencies.** This is the hub for E2-04, E2-06, E2-10, E2-11 and E2-13, and for E4 R2b/R4d. It also depends on
E2-X1 (the ACCEPT-R8 attestation). Build: a new ADR qualifying ADR-086/106; `sources.toml` reviewer values (the
flip-metadata validator in `connectors/review.py:99-126` may constrain allowed values; engineering); appended DEFERRALS
corrections to D-LEGAL.1-1 and D-P30.3-COUNSEL; a new OPEN counsel row.

### E2-06 — Robots disregarded without the counsel step; opt-out and reservation MUSTs unbuilt (E1-06 · legal)

**Contradiction.** The spec sets three rules:
- SIG-INGEST-037: any crawler-conduct deviation is "an ADR-level decision requiring counsel";
- §26 rule 7: honour opt-outs "immediately";
- SIG-INGEST-046c: treat machine-readable rights reservations, including an EU DSM Article 4 reservation, as
  refusals.

GL-GATE-08 / ADR-088 disregard robots with no counsel step, and no runtime control implements rule 7 or 046c (E1-06;
E1 NEW-15).

**Facts for the decision** (`code` and `recorded-execution`, this row).
- **Runtime:** `net.py:382-393` lets fetches proceed on `disallowed` or `unretrievable` and stamps them
  `robots_disregarded`. `policy/crawler.py:89-113` (Content-Signal parsing) is called only from
  `tests/unit/test_policy_crawler.py`.
- **No opt-out register.** None exists in `connectors/` or `policy/` (grep). The only way to stop crawling a host is a
  package-data registry edit plus rebuilding and redeploying the ingest images, so "immediately" cannot be met today
  (**NEW-3**).
- **Scale.** The P26.17 run files record **125 disregarded fetches on 122 hosts** (**NEW-2**):
  - 103 explicit `disallowed`: 102 PrimeGov municipal-agenda hosts and `www.oscn.net`;
  - 22 `unretrievable`: 6 eScribe hosts and 5 French prefecture `gouv.fr` hosts.
  - primegov, escribe and raa_prefectures are scheduled in `ops/cadence.toml`.
  - No aggregate inventory across hosted runs exists in build memory.
- **The recorded words are a question** ("I also wonder if we should…", X-1). Later answers are consistent with the
  recorded decision.
- **ADR-088 already has the trigger.** Its revisit trigger names "Counsel objects".

**Options.**
- **(a) Amend:** an ADR changes SIG-INGEST-037's counsel clause to "operator risk acceptance recorded; counsel review
  recommended". Rule 7 and 046c stay MUSTs and are **built**.
  - Compensating controls, existing: per-fetch `robots_disregarded` provenance; SIG-INGEST-013 no-circumvention
    (fails closed); rate limits and crawl-delay.
  - To build: a host-level opt-out register checked before every fetch ([est] 1–2 days); Content-Signal / TDM /
    Article 4 reservation detection that refuses and records the refusal ([est] 2–3 days); the published conduct page
    (E2-08).
  - Revisit triggers: an egress block, a host objection, counsel objects, or a reservation is encountered.
- **(b) Keep owed and re-gate robots until counsel answers.** At least the 103 explicit-refusal hosts are lost from
  coverage (council agendas and minutes, core CCOPS and procurement evidence [inference on value]). Counsel lead time
  is 1–4 months.
- **(c) Hybrid:**
  - The operator re-confirms GL-GATE-08 in their own words (E2-X1), **or narrows it**. Example: honour explicit
    `disallowed` verdicts on non-US hosts, where 046c's legal-effect concern sits, and keep the disregard for US
    public-body hosts.
  - Build rule 7 and 046c in Round 11 (these MUSTs were never waived).
  - Put the robots question in the §7 packet.
  - Amend 037 as in (a).

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "we record robots.txt but do not obey it; we honour opt-outs and reservations" | ignoring robots.txt ignores a site's stated wish not to be crawled; the practical risks are blocks on shared vendor infrastructure (PrimeGov is exactly that case) and complaints; the spec itself notes that EU reservations have legal effect | ADR, spec_src §26, two tickets, E2-07 text |
| b | "we obey robots.txt" | lowest crawl exposure; real coverage loss | revert ADR-088 by a new ADR; re-gate code |
| c | as a, possibly narrower | as a, reduced for non-US hosts if narrowed; whether any of SIG's crawling creates legal exposure is a counsel question the record shows was never asked | as a + counsel question |

**Recommendation: (c).** *Decision line:* **"I re-confirm (or narrow) GL-GATE-08 in my own words; an ADR amends
SIG-INGEST-037's counsel clause to 'operator risk acceptance, counsel question pending'; Round 11 builds the rule-7
opt-out register and SIG-INGEST-046c reservation refusal; robots goes in the counsel packet."** (Q-E2-11.)
**Dependencies.** E2-X1, E2-05, E2-07, E2-08; E4 S2 (bonfire re-scope); Stream I (new sources inherit the posture,
Q-19); J3 (publishing a crawl-disregard log is a transparency option).

### E2-09 — Stage-0 outreach MUST vs WONTFIX "optional" with no ADR (E1-09)

**Contradiction.** SIG-CONTRIB-012, with -013, INGEST-030a, CHART-033, INGEST-029 and GOV-024, requires contacting an
ecosystem project **before** writing its connector, agreeing ShareAlike attribution and offering archival succession.
Instead:
- the operator skipped outreach (WONTFIX "optional"), with no ADR;
- ecosystem connectors run live (for example Eyes on Flock → the CC-BY-SA `sig_portal` compartment);
- the five ids carry four different verdicts (E1-09).

**Facts for the decision.**
- 19 projects × 0.5–1 h = 10–19 h plus follow-up; the operator can do it; $0 [E3 R15].
- The letter says "we honour robots" and must be fixed first (E2-07).
- Ecosystem data is live with missing or wrong credit (E2-12: DeFlock credited on others' data; EFF Atlas obligations
  misattributed).
- Outreach is outward contact and needs the operator's authorization (as Q-28 does).

**Options.**
- **(a) Amend by ADR** to SHOULD.
  - Compensating controls: honest `public_terms_only` postures in the registry (public once J3 exports it);
    structural attribution after E2-12; licence compartments.
  - Revisit trigger: a project objects or changes its terms.
- **(b) Keep owed:** contact all 19 projects after correcting the letter. Lead time 2–6 weeks for replies.
- **(c) Hybrid:**
  - Amend the **timing** by ADR: contact is owed per ecosystem project, not a precondition for a connector that
    already exists.
  - After E2-12 ships, contact the projects whose data is live now (Eyes on Flock, DeFlock and the EFF Atlas first),
    including a correction of the misattribution.
  - Give all five ids one consistent verdict.

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | honest postures only | ecosystem projects are also SIG's natural allies and its reviewer pool (E3); finding their data republished without contact, and with the wrong credit, risks those relationships; the CC-BY-SA terms apply whether or not anyone is contacted | ADR + spec_src; verdicts |
| b | "we contacted every project" once done | lowest | 10–19 h operator |
| c | "we contacted the projects whose data we publish" | low, and the misattribution gets corrected at the source | ADR + a few hours of operator time |

**Recommendation: (c).** *Decision line:* **"Amend Stage-0 outreach by ADR from a pre-connector precondition to an
owed per-project obligation; after the attribution fix ships I contact the ecosystem projects whose data is live
(Eyes on Flock, DeFlock, EFF Atlas first), and the five outreach ids get one verdict."** (Q-E2-12.)
**Dependencies.** E2-12, E2-07, E2-13, Q-28.

### E2-11 — GL-GATE-07 "err on the side of approving" vs fail-closed rights and counsel on the database right (E1-11 · licensing)

**Contradiction.** SIG-LIC-004 and SIG-LIC-003 require unresolved rights to fail closed and never infer
redistributability, and SIG-LIC-009 sends the EU database right to counsel. GL-GATE-07 approved every "rights review"
case on the operator's risk acceptance, including non-US database-right risk. Execution then went beyond the recorded
rule: unresolved-jurisdiction and terms-not-captured rows were flipped too. The result is 94 sources and **21,682
public rows** under `LicenseRef-OperatorAccepted-DBRight` (E1-11; E1 NEW-13; E4 NEW-9).

**Facts for the decision.**
- **The manifest names the basis honestly.**
- **Execution followed worklist membership, not facts** (E4 NEW-9).
- **Counsel-flagged clauses were flipped anyway:** Lexington's indemnify-and-defend terms and Maryland's iMAP terms
  [E3 R7].
- **Per-source re-review cost:** about 0.5–2 h per source [E3 R9 rate]; for all 94 sources, 47–188 h. Missing terms
  can be captured with `sig-db rights-decisions --capture-terms` (E4).
- **Q-19 asks the same question going forward** (new sources, Stream I).

**Options.**
- **(a) Amend:** the spec recognises operator risk acceptance as a **distinct, disclosed** rights basis, never
  presented as "evidenced rights". Guardrails:
  - terms captured verbatim per source (backfill);
  - express prohibitions, non-commercial clauses, indemnities and unresolved jurisdictions excluded from any blanket
    and decided per source;
  - a licensor objection triggers takedown (`takedown.toml` exists);
  - the database-right question goes in the §7 packet;
  - HG-03 text updated.
  Revisit triggers: a licensor objection, a legal demand, a counsel opinion, or a new jurisdiction class.
- **(b) Revert:** return all 94 sources to UNDETERMINED (fail closed) until evidenced per-source review. This removes
  21,682 public rows and a map layer; costs 47–188 h of operator review plus counsel for flagged clauses; and takes
  months.
- **(c) Hybrid:** (a) plus a targeted re-decision now of the out-of-rule and counsel-flagged rows (`camreg_aikner`,
  `camreg_calgary_ab`, Lexington, MD iMAP, and any DBRight row with no captured terms), using E4-style per-source
  packets. Q-19 is answered with the same guardrails.

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "published on the maintainer's acceptance of database-right risk" (already the label) | in the EU, the UK and some other places a compiled database can be protected separately from copyright, and republishing a substantial part without permission is what that protection targets; the rows where the rule was stretched are the weakest | ADR + spec_src (LIC-004/009, HG-03); terms-capture ticket |
| b | only evidenced sources | lowest licensing exposure; large loss of public coverage | re-gate + reviews |
| c | as a; the edge rows re-decided | as a, minus the weakest rows | as a + E4-style packets for the edge rows |

**Recommendation: (c).** *Decision line:* **"Amend SIG-LIC-004/009 and HG-03 by ADR to recognise a disclosed
operator-risk-acceptance basis with guardrails (terms captured; restrictive clauses and unresolved jurisdictions
decided per source; a licensor objection triggers takedown); re-decide the out-of-rule and counsel-flagged rows
individually; put the database-right question in the counsel packet."** (Q-E2-13, with Q-19.)
**Dependencies.** E2-05, E2-12 (these rows need attribution too), E4 (R4a–d follow the same rule), I7/I8.

### E2-13 — ODbL residual: one map over all compartments on an operator-reported clearance (E1-13 · licensing)

**Contradiction.** SIG-EXPORT-005, LIC-004a and LIC-006 require OSM-derived data to ship as its own ODbL compartment
so share-alike does not reach the whole export. The "publish it all together" deviation was retired (`/map/points.json`
404, per-compartment tiles), but the map is still one produced work drawing every compartment. Its clearance rests on
operator-reported counsel only (ADR-106) (E1-13).

**Options.**
- **(a) Accept by ADR:** the produced-work reading stands on operator judgment, with no document.
  - Compensating controls (existing): per-compartment downloads and tiles; "© OpenStreetMap contributors (ODbL)" on
    the map.
  - Revisit triggers: ADR-106's own (an OSMF or licensor objection; a counsel opinion that differs).
- **(b) Counsel:** this is RISK-P0-01 and SIG-LIC-009's first named question anyway.
- **(c)** (a) now + (b) in the shared packet + E2-12's check that the OSM compartment's downloads carry a share-alike
  notice.

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a / c | "the map combines separately licensed layers; OSM data stays under ODbL"; never "counsel-cleared" | ODbL's share-alike can extend to databases derived from OSM; SIG's separation is designed to limit that, and whether the combined rendering falls outside share-alike is a published-guidance-plus-lawyer question | new ADR qualifying ADR-106's basis |
| b | the opinion's scope once filed | reduced | packet |

**Recommendation: (c).** *Decision line:* **"Keep the per-compartment map; record by a new ADR that ADR-106's
clearance is operator-reported with no document; the ODbL produced-work and 4.4(b) questions go in the counsel
packet."** (Q-E2-14.)
**Dependencies.** E2-05, E2-12.

---

## 4. Group 4 — evaluation and human review

### E2-14 — Independent human evaluation vs four deferrals and model-made labels (E1-14 · trust)

**Contradiction.** SIG-EVAL-001…007, SIG-IDENT-027 and §55.9 require independent human labels with adjudication, and
forbid agent labels from standing in for them. Instead:
- human review was deferred four times;
- the camera-site gold set and holdout were produced by `claude-opus-5-5`;
- the org-resolution "LLM adjudicator" is deterministic code, compared against a fixture "maintainer seed";
- `/methodology/` calls the holdout "human-verified" (E1-14; E1 NEW-10; F-06).

**Facts for the decision.**
- **The wording is hard-coded.** `web/src/lib/resolution-eval.ts:67` contains "the frozen, human-verified holdout"
  (`code`, this row).
- **Nothing automatic depends on the provisional thresholds.** Auto-write runs in shadow mode (`mode=shadow`,
  `applied=[]`).
- **E3's minimal honest program:**
  - two external labelers at 18–45 h each, an adjudicator at 7–17 h, custodian 16–33 h and method reviewer 8–20 h
    (both operator seats, disclosed; the method reviewer plus an OSF preregistration);
  - cost $0 (volunteers) to about $0.9k–3.6k (paid labelers); 3–5 months;
  - engineering prerequisites: a reviewer UI and hosted access (E3 NEW-2), and the P32.22 snapshot
    (D-R10-LIVE-1).
- **The 0.98 gate is hard to certify.** At a true 99% precision, a single-tier n = 149 campaign passes only 22% of the
  time (E3 NEW-8).

**Options.**
- **(a) Amend to a disclosed model-assisted standard.** An ADR records that resolution quality is measured against
  model-made reference labels, disclosed as such, and that auto-write stays in shadow unless human evidence arrives.
  Revisit triggers: any decision to enable auto-write, or recruiting succeeds. Consequence: SIG's "evidence-first"
  standard would rest on model-vs-model agreement for identity resolution.
- **(b) Keep owed** and run E3's minimal program as specified, with the aim set by Q-24.
- **(c) Hybrid:**
  - Fix the wording now (H-4). The EVAL MUSTs stay; there is no waiver.
  - Round 11 builds the reviewer path and runs the H4 pilot with two external labelers (Q-28). The operator holds the
    custodian and method-reviewer seats, disclosed (Q-25).
  - **The pilot's `insufficient_evidence` rate sets the H5 aim:** certify (single tier, n = 149–236) or estimate only
    (n ≈ 100).
  - Auto-write stays PROVISIONAL until H5 passes.
  - If nobody is recruited by a set date, rows 184–187 get a later-phase trigger (F4) and the disclosure stays.
- *Agent-drafted methodology wording:* "Holdout: 180 pairs labelled by an AI model (claude-opus-5-5) and checked by the
  same model family; no human has verified them. Organization resolution: a rules-based adjudicator compared with a
  small set of seed labels stored in the repository; no record shows those labels were made by a person."

| option | may / may not claim | exposure (plain) | build |
|---|---|---|---|
| a | "model-evaluated, not human-verified" permanently | for an evidentiary project, a reader who learns the quality figures are model-vs-model agreement will discount the numbers that depend on resolution (the public counts and the 33,907 pending merges) | ADR + spec_src §55/EVAL |
| b | a human-verified precision estimate with its interval, once done | lowest | E3 program + F4 re-entry |
| c | honest provenance now; human-verified figures only after H4/H5 | the false "human-verified" claim ends now | H-4 + reviewer-path ticket + pilot |

**Recommendation: (c).** *Decision line:* **"Independent human evaluation stays a MUST — no waiver; the methodology
page is corrected now; Round 11 builds the reviewer path and runs the H4 pilot with two external labelers; the
pilot's insufficient-evidence rate sets the H5 aim; auto-write stays PROVISIONAL until H5 passes."** (Q-E2-15, with
Q-24, Q-25, Q-28; F4 designs the re-entry.)
**Dependencies.** E3, F4, E2-16 (verdicts), E2-X1 (the Round-9 deferral words), E2-19 (the future-dated deferral
record).

### E2-15 — Moderated usability study WONTFIX, verdict MET (E1-15)

**Contradiction.** SIG-CONTRIB-003 requires a published moderated usability study (≥5 participants) before the
contributor system is declared complete. HG-10 was skipped (WONTFIX), yet the verdict is MET (E1-15).

**Facts for the decision.**
- **There is no public contributor system.** `/curate/submit/` is loopback-only, and `/curate/` was removed from the
  public site (Track 0.2).
- **Neither protocol tests the live site** (E3 NEW-5).
- **The study is affordable [E3 R8]:** 5 participants; a moderator at 13.5–23 h (the operator may moderate);
  $0–940; lead time 2–6 weeks.
- **A reader study is already owed:** D-R10-USERS-1 is OPEN.

**Options.**
- **(a) Amend it out by ADR.**
- **(b) Run the contributor study as specified.** This first needs a public contributor path, which does not exist.
- **(c) Hybrid:** record the contributor system as **not complete** (no public path). CONTRIB-003 stays a MUST,
  triggered by any public contribution launch. Near-term usability effort goes to a five-session **live-site** study
  with design-centre users (D-R10-USERS-1, SIG-UI-001), with the protocol amended to the live site. This serves thesis
  T7.

| option | may / may not claim | exposure | build |
|---|---|---|---|
| a | nothing about usability | low (process) | ADR + spec_src |
| b | "usability-validated contributor system" once done | low | needs a public contributor path first |
| c | no usability claims until the reader study; then its findings | low | verdict change; protocol amendment; R8 sessions |

**Recommendation: (c).** *Decision line:* **"Record the contributor system as not complete (no public contribution
path); SIG-CONTRIB-003 stays a MUST triggered by any public contribution launch; near-term usability effort goes to a
five-session live-site study with design-centre users (D-R10-USERS-1)."** (Q-E2-16.)
**Dependencies.** D3, E3 R8, G2, Track 0.2.

### E2-16 — Scoped acceptances and waived items recorded MET or DONE (E1-16, X-2)

**Contradiction.** SIG-TRUST-009's own text says a scoped signature never waives the full criterion set, and
SIG-DOS-002 says incomplete publication does not satisfy pilot completion. Yet:
- SIG-TRUST-009/010, SIG-DOS-002…005, SIG-FIND-006 and SIG-ACQ-004 are MET on staging, fixture or bounded scope;
- four deferrals whose named act never happened (D-P21.4-1, D-P21.4-2, D-LEGAL.1-1, D-P30.3-COUNSEL) are recorded
  `DONE` (E1-16; X-2; F-16; E1 NEW-8; A3 NEW-1).

**Options.**
- **(a) Redefine MET** to include scoped acceptance, via an ADR amending §55. This contradicts the spec's own
  anti-collapse text and is the P5 failure mode.
- **(b) Re-verdict** with §8.3's vocabulary: `MET-ENGINEERED` citing the open D-ids; `WAIVED(ADR)` only where an ADR
  exists. Append status corrections to the four deferrals ("closed without the named act; waived by operator").

No Round-10 surface is live (F-14), so this carries no public exposure.

**Recommendation: (b).** *Decision line:* **"Scoped acceptances are recorded as owed, not waived: adopt §8.3's
MET-ENGINEERED / WAIVED(ADR) verdicts, re-verdict the scoped ids with their open D-ids, and append status corrections
to deferrals closed DONE without their named act."** (Q-E2-17; applied by F2/T4.)
**Dependencies.** F2, T4, E2-14, E2-15.

---

## 5. Group 5 — process and record integrity

### E2-17 — Agent-drafted, future-dated gate signatures (E1-17; F-29)

**Contradiction.** The readout template said "an agent must not sign"; ticket 190 requires the actual authority and
date; SIG-TRUST-009 says agent judgment cannot sign. Yet the GATE-G3 and ACCEPT-R10 signing commits:
- deleted that template line;
- ticked every box;
- carry agent-drafted scope text with no operator verbatim;
- date GATE-G3 2026-10-19, although it was committed on 2026-09-28 (E1-17).

**Facts for the decision.**
- What GATE-G3 accepted, candidate `p-17b713…`, held 0 records (F-15). Q-12 recommends superseding that candidate.
- The operator's words exist only in the LEDGER: `:116` *"I sign/accept. Please proceed"* and `:115` *"oik looks
  good, proceed"*.
- ACCEPT-R8 was signed "by the orchestrator at the operator's explicit instruction".

**Options.**
- **(a) Let them stand,** appending the operator's LEDGER verbatim to each readout.
- **(b) The operator re-confirms each against its exact text:** an appended confirmation per readout, dated from
  `date -u`; about 0.5–1 h of operator time.
- **(c) Supersede and add a rule:**
  - GATE-G3 is superseded together with the fixture candidate (Q-12); what it accepted never shipped.
  - ACCEPT-R10 and ACCEPT-R8 are re-confirmed via (b).
  - Forward rule (META_PLAN §2): agent-drafted gate text is labelled, the operator confirms the exact text, and the
    readout quotes the operator verbatim. B4's validator rejects a readout with no verbatim quote or with a date later
    than its commit.

**Recommendation: (c).** No public exposure. Build: appended records (B1/T2) and B4's validator. *Decision line:*
**"GATE-G3's signature is superseded with the fixture candidate; I re-confirm ACCEPT-R10 and ACCEPT-R8 against their
exact text in appended records; from now on agent-drafted gate text is labelled and confirmed verbatim, and a
validator enforces it."** (Q-E2-18, with Q-12.)
**Dependencies.** B1, B4, B5, E2-19, E2-X1.

### E2-18 — Go-public ran with gates skipped; the records were never reconciled and the history was deleted (E1-18; F-22)

**Contradiction.** The go-live spec says "nothing publishes without the two-reviewer + counsel gates" and requires a
real legal home before cutover. Go-public ran on 2026-09-16 with HG-11 skipped and HG-02 deferred. The gate records
still say otherwise:

| record | what it still says |
|---|---|
| GATE-G2 | "SKIPPED … required before cutover" |
| PUBLICATION_CHECKLIST | "Go-public: ❌ NO" |
| RISK-P0-13 | "no public launch without it" |
| governance doc | "not a public launch" |

The 53-row GATE DECISIONS table that recorded those waivers was deleted in `c2055d96` (E1-18; F-22; E1 NEW-11;
A3 NEW-3).

**Options.**
- **(a) Record what happened:**
  - amend the go-live spec (goal 5, GL-GATE-01/02/05, the gate register) to state what was done, pointing to the
    E2-01/04/05 ADRs;
  - add GL-GATE-06…08 to the go-live spec (F-35);
  - append supersession entries to GATE-G2, PUBLICATION_CHECKLIST and RISK-P0-13/-05;
  - **restore the 53 deleted rows verbatim** from `c2055d96^` as an appended, dated correction (B2/B3).
- **(b) Take the site offline until HG-01/02/11 pass.** This is the only literal way to keep the preconditions
  owed. It is listed so that it is rejected consciously; the agent does **not** recommend it, because the §0.1 fixes
  address the public-truth problem without withdrawing the site.

**Recommendation: (a).** *Decision line:* **"Amend the go-live spec to record the 2026-09-16 go-public and its
waivers; append supersession entries to the stale gate records; restore the deleted GATE DECISIONS rows verbatim as
an appended correction."** (Q-E2-19.)
**Dependencies.** B2, B3, T1, E2-01, E2-04, E2-05.

### E2-19 — Normative text asserts future-dated events (E1-19; F-21)

**Contradiction.** SIG-TRUST-008 forbids marking calendar-dependent checks complete before they are executed. Yet
spec §55, ADR Date headers (ADR-118/142/144), the manifest and coverage notes assert events dated 2026-10-05…10-20:
later than the commits that wrote them, and later than today (2026-09-30).

**Options.** Correct via B1. There is no honest alternative to correcting them. The corrections are:
- a spec_src amendment (append-only, naming each corrected statement and using commit dates), then `BUILD.sh`;
- a correction ADR listing the true dates for ADR headers (landed ADR bodies are not edited);
- corrected coverage notes in T4;
- B4's date-sanity guard.

Public pages were not checked for these dates (limit).

**Recommendation: correct.** *Decision line:* **"Correct every future-dated normative statement by appended
amendment (spec via spec_src + BUILD.sh, a correction ADR for ADR dates, coverage notes in T4) using commit dates, as
part of B1."** (Q-E2-20.)
**Dependencies.** B1, B4, E2-17.

### E2-X1 — Tentative or instructional words recorded as decisions (X-1; E1 NEW-9)

**Contradiction.** Operator decisions must be recorded verbatim, and the operator confirms any agent-drafted text
(META_PLAN §2). Three consequential records instead supply a decisive reading of words that were interrogative,
tentative or instructional:

| record | operator's words | recorded as |
|---|---|---|
| GL-GATE-08 | *"I also wonder if we should…"* | "disregard robots entirely" |
| ACCEPT-R8 | *"counsel opinion should just be to give us the green light"* | "operator attests counsel cleared" |
| Round 9 | *"perhaps we defer human review…"* | human review deferred |

**Options.**
- **(a) Leave them.**
- **(b) The operator confirms or corrects each** in their own words (about 15 minutes in total), appended verbatim.
  For ACCEPT-R8 the confirming question is factual: *"Did a lawyer tell you public release was OK? If so, who and
  when?"* The answer feeds Q-26 and E2-05.
- **(c)** = (b) + a forward rule: when the operator's words are tentative or instructional, the recorder asks a closed
  confirming question and records both the words and the answer.

**Recommendation: (c).** Only the operator can answer. Ask it first at S5 (or at D2), because E2-05, E2-06 and E2-14
depend on it. *Decision line:* **"I confirm or correct, in my own words, the robots decision, the 'counsel'
attestation and the human-review deferral; future records require an explicit confirmation whenever my words are
tentative or instructional."** (Q-E2-21.)
**Dependencies.** E2-05, E2-06, E2-14, B5, D2.

### E2-20 — "Narrowly excellent at U.S. ALPR" vs a national/international all-camera launch (E1-20 · trust)

**Contradiction.** SIG-CHART-025 requires the first release to be narrowly excellent at U.S. ALPR infrastructure. The
live release is national and international and covers all camera types (227,335 map points; dossiers for AU, GB, JP,
TH and others). The id is verdicted MET-DIFFERENTLY under an acceptance signed before the national launch (E1-20).

**Facts for the decision.** Related quality issues: F-04 ("unresolved" holds 71.4% of publishable subjects) and F-44
(Idaho merged with Indonesia, Minnesota with Mongolia). This is D3's question (thesis T7).

**Options.**
- **(a) Amend CHART-025** to the operated scope.
- **(b) Reaffirm U.S. ALPR** as the quality bar and demote other classes and geographies to labelled "breadth" layers.
- **(c) Keep the breadth,** make U.S. ALPR the primary quality target, and label coverage quality per layer on the
  site.

Whichever is chosen: record it by ADR, and label per-layer quality so that breadth is not read as depth.

**Recommendation: decide at D3.** *Decision line:* **"At D3: reaffirm or amend SIG-CHART-025, record it by ADR, and
label coverage quality per technology class and geography on the site."** (Q-E2-22.)
**Dependencies.** D1, D3, Stream I, F-04, F-44.

### E2-21 — Software Heritage deposit declined on a lapsed rationale (E1-21)

**Contradiction.** SIG-EVID-019 requires a Software Heritage deposit of the code. It was declined because "the repo
stays private", but the repository is now public (E1-21; E1 NEW-14).

**Facts for the decision.**
- Save Code Now for a public repository is a free web submission taking minutes of operator time [inference; verify
  when executing].
- The archive is permanent and includes history. Anything sensitive in the history becomes permanently archived:
  deletable on GitHub, not in the archive [inference].

**Options.**
- **(a) Drop the requirement.** No rationale remains for doing so.
- **(b) Deposit now.**
- **(c) Scan the full history first** for secrets and Part VIII data (P14/G1 scope; [est] 1–2 h with a standard
  scanner), then deposit.

**Recommendation: (c).** *Decision line:* **"Re-open the Software Heritage deposit: scan the public history for
secrets and restricted data first, then I submit it."** (Q-E2-23.)
**Dependencies.** G1 (secret handling), Track 0.3 (the stale MapRoulette key).

---

## 6. What each recommendation implies for the build (summary for S2/T1/T3)

| kind | items |
|---|---|
| **New ADRs** (T1) | PUB-008 posture (E2-01) · interim editorial authority (E2-03) · interim legal home (E2-04) · SEC-003 posture and canary decline (E2-10) · counsel basis, qualifying ADR-086/106, with a dated fallback (E2-05) · SIG-INGEST-037 amendment + rule 7/046c (E2-06) · crawler policy field semantics, superseding ADR-088's clause (E2-07) · outreach timing (E2-09) · operator-accepted rights basis with guardrails (E2-11) · ADR-106 basis (E2-13) · date-correction ADR (E2-19) · CHART-025 (E2-20, at D3) |
| **spec_src amendments** (T1) | SIG-PUB-008 note · GOV-012/013/015 interim text · SEC-003 · LIC-004/009 + HG-03 · INGEST-037 / §26 · CONTRIB-012/013/030a · §55 date corrections · CHART-025 (D3). Go-live spec (hand-edited): goal 5, GL-GATE-01/02/05, the gate register, GL-GATE-06…08 (E2-18) |
| **First-wave tickets** (T3) | H-1…H-9 (§0.1) · rights-record per-source attribution + publish-time gate (E2-12) · opt-out register (E2-06) · reservation refusal (E2-06) · crawler page + UA move (E2-08) · editorial-decisions log page (E2-03) · legal-demand counts (E2-10) · reviewer path for human evaluation (E2-14, with F4) · dossier-build hostile-reader gate (E2-02) |
| **Operator actions** | register `sig-project.org` (E2-08) · contact mailbox (A-1) · counsel outreach or Q-26 follow-up (E2-05) · outreach to live ecosystem projects (E2-09) · E2-X1 confirmations · ACCEPT-R8/R10 re-confirmation (E2-17) · SWH submission after the scan (E2-21) · recruiting (Q-28) |
| **Records** (T2/T4) | appended corrections: D-P21.4-1/-2, D-LEGAL.1-1, D-P30.3-COUNSEL, RISK-P0-05/-13, GATE-G2, PUBLICATION_CHECKLIST, governance doc · restore 53 GATE DECISIONS rows · new OPEN rows: counsel opinion (E2-05), SEC-003 owner (E2-10), second reviewer/board with trigger (E2-01/03) · re-verdicts (E2-16) |

---

## 7. Counsel packet — questions a qualified lawyer would need to be asked

**These are questions, not answers.** They are agent-drafted for the operator to review, trim and send. No part of
this row is, or substitutes for, legal advice. One consolidated packet is estimated at 10–30 counsel hours plus 5–10
operator hours to assemble [E3 R7]. If only two questions can be afforded, E3's smallest honest version is **L1 + L4**;
the agent would add **L6** third, because the robots decision has the least recorded analysis behind it.

| # | question (for counsel) | memo |
|---|---|---|
| L1 | Do SIG's API responses that return device-linked claims derived partly from OpenStreetMap distribute a Derivative Database under ODbL 4.4(b)? What would change the answer? (RISK-P0-01, SIG-LIC-009) | E2-13 |
| L2 | Is the `/map/` rendering, which draws the ODbL compartment together with separately licensed compartments, a Produced Work outside share-alike? What notice and attribution does it need? | E2-13 |
| L3 | SIG-LIC-009's other residuals: the correct regional-cut unit, and the OSM boundary-geometry / Collective Database question | E2-13 |
| L4 | Republication (downloads + map) of 94 non-US factual compilations (21,682 rows) under operator risk acceptance: what database-right exposure exists in the EU, the UK, Australia and elsewhere? Do "jurisdiction unresolved" or "terms not captured" change it? What per-source standard would be defensible? | E2-11 |
| L5 | Specific terms: Lexington (indemnify-and-defend), the Maryland iMAP terms, Bellevue's non-commercial clause (is SIG's use "commercial"?), the CourtListener membership terms | E2-11; E4 R4d/R2b |
| L6 | Crawling: what exposure comes from fetching hosts whose robots.txt disallows SIG (102 PrimeGov municipal hosts, `oscn.net`) or cannot be retrieved (including French government hosts)? Do EU text-and-data-mining (Art. 4) reservations apply to SIG's use? What opt-out handling is expected? | E2-06 |
| L7 | Legal home: what is the personal exposure of an individual operating SIG? Would a fiscal sponsor (which model) or an entity change it, and how much? Is insurance available or advisable? Does any jurisdiction SIG publishes about require an operator identification on the site? | E2-04 |
| L8 | HG-02 remainder: review the operator-adopted drafts (`docs/governance/publication-opinion-drafts.md`) on publication tiers, officer naming and Part VIII | E2-01, E2-05 |
| L9 | Review the draft demand-response posture: preservation, user notice, what to publish, and whether a warrant canary is advisable | E2-10 |
| L10 (optional) | Does the period of missing or wrong attribution in public data call for any step beyond fixing it (for example, notifying licensors)? | E2-12 |

Sourcing (none contacted) [E3]: first, whoever gave the 2026-09-16/24 advice, if a lawyer did (Q-26); then an EFF
Cooperating Attorneys referral; a law-school technology clinic (the Harvard Cyberlaw Clinic advised OSM-US on ODbL in
2016); the RCFP hotline (media law; may not cover database licensing); or paid counsel (about $349/h).

---

## 8. Proposed Q rows (the one-line decisions, for S5)

The orchestrator numbers these Q-29+ (single writer). "Rec." is the agent's recommended answer; the operator may
answer with a letter from §0 instead.

| proposed id | one-line decision the operator would record (rec.) | memo | related |
|---|---|---|---|
| Q-E2-01 | Remove the fixture review from /editorial-standards/ now and say it has not been performed; SIG-UI-042 stays a MUST (MISSING); one real two-reader review (me + one external, disclosed) against a live dossier; the gate moves into the dossier build | E2-02 | Q-E3-9, Q-25, Q-28 |
| Q-E2-02 | Bring crawler_conduct.toml, the crawler.py docstring, the registry robots_policy field and the outreach letter into line with the E2-06 outcome in one ticket, with a new ADR superseding ADR-088's clause | E2-07 | — |
| Q-E2-03 | Register sig-project.org defensively now (me); in Round 11 move the crawler contact to surveillancegraph.org/data-collection/ with a published conduct and opt-out page; redirect the old domain | E2-08 | Track 0 |
| Q-E2-04 | Treat attribution as a defect under the existing MUSTs: first-wave fix in rights records, exports, API and map + a publish-time attribution gate + republish; an interim sources-and-licences page no later than the fix | E2-12 | J3 |
| Q-E2-05 | Replace every one-click dispute promise with the operated truth now; publish one monitored contact address with single-maintainer response times; open the receiver only when a backup moderator exists | A-1 | Q-27 |
| Q-E2-06 | SIG-PUB-008 stands unamended; no named individual is published until two independent reviewers exist; the web gate is fixed to default-deny; verdict MET-ENGINEERED | E2-01 | Q-E3-8 |
| Q-E2-07 | Correct the governance doc and API terms now; an ADR records an interim single-maintainer editorial authority with a public decision log; a board is constituted when an entity exists or naming is wanted | E2-03 | Q-28 |
| Q-E2-08 | Record by ADR the individual legal home as an interim, disclosed posture with revisit triggers; legal-home questions go to counsel; sponsor vs entity decided after counsel; legal-defence resources listed now | E2-04 | Q-E3-11 |
| Q-E2-09 | Own SIG-SEC-003 now: a written demand-response posture (counsel review requested), legal-demand counts published, the warrant canary declined with rationale | E2-10 | — |
| Q-E2-10 | Label every public artifact with the operated basis now; re-record "counsel" entries as operator-reported; seek one dated written opinion on one packet; if none by the end of Round 11, an ADR records publication on my risk acceptance | E2-05 | Q-26 |
| Q-E2-11 | I re-confirm (or narrow) GL-GATE-08 in my own words; an ADR amends SIG-INGEST-037's counsel clause; Round 11 builds the rule-7 opt-out register and 046c reservation refusal; robots goes in the counsel packet | E2-06 | Q-E2-21 |
| Q-E2-12 | Amend Stage-0 outreach by ADR to an owed per-project obligation; after the attribution fix I contact the ecosystem projects whose data is live; the five ids get one verdict | E2-09 | Q-28 |
| Q-E2-13 | Amend SIG-LIC-004/009 and HG-03 by ADR to recognise a disclosed operator-risk-acceptance basis with guardrails; re-decide the out-of-rule and counsel-flagged rows individually; the database right goes in the counsel packet | E2-11 | Q-19 |
| Q-E2-14 | Keep the per-compartment map; a new ADR records ADR-106's clearance as operator-reported with no document; the ODbL questions go in the counsel packet | E2-13 | — |
| Q-E2-15 | Independent human evaluation stays a MUST; methodology wording corrected now; Round 11 builds the reviewer path and runs the H4 pilot with two external labelers; the pilot's insufficient-evidence rate sets the H5 aim; auto-write stays PROVISIONAL | E2-14 | Q-24, Q-25, Q-28 |
| Q-E2-16 | The contributor system is recorded as not complete; SIG-CONTRIB-003 stays a MUST triggered by any public contribution launch; near-term usability effort goes to a five-session live-site study | E2-15 | — |
| Q-E2-17 | Scoped acceptances are recorded as owed, not waived: adopt MET-ENGINEERED / WAIVED(ADR), re-verdict the scoped ids, append corrections to deferrals closed DONE without their act | E2-16 | §8.3 |
| Q-E2-18 | GATE-G3's signature is superseded with the fixture candidate; I re-confirm ACCEPT-R10 and ACCEPT-R8 against their exact text; agent-drafted gate text is labelled and confirmed verbatim from now on | E2-17 | Q-12 |
| Q-E2-19 | Amend the go-live spec to record the 2026-09-16 go-public and its waivers; append supersessions to the stale gate records; restore the deleted GATE DECISIONS rows verbatim | E2-18 | — |
| Q-E2-20 | Correct every future-dated normative statement by appended amendment using commit dates, as part of B1 | E2-19 | — |
| Q-E2-21 | I confirm or correct, in my own words, the robots decision, the "counsel" attestation and the human-review deferral; tentative or instructional words need explicit confirmation from now on | E2-X1 | Q-26 |
| Q-E2-22 | At D3: reaffirm or amend SIG-CHART-025, record it by ADR, and label coverage quality per class and geography | E2-20 | Q-9, D3 |
| Q-E2-23 | Re-open the Software Heritage deposit: scan the public history for secrets and restricted data first, then submit | E2-21 | — |

---

## 9. Findings filed (`findings/incoming/E2.csv`)

| id | sev | summary |
|---|---|---|
| NEW-1 | S1 | The SIG-UI-042 gate (`assertReviewReleasable`) throws unless two or more reviewer names exist, and it gates only the `/editorial-standards/` page. A truthful "no review performed" record therefore fails the web build, and no dossier release consults the gate. This is the mechanism behind E1 NEW-1 / E3 NEW-1. |
| NEW-2 | S2 | Robots disregard under GL-GATE-08 is dominated by explicit refusals on one vendor platform (102 PrimeGov hosts) and reaches EU government hosts (5 French prefecture sites, `unretrievable`): 125 entries on 122 hosts in the P26.17 run files. The connectors are scheduled, and no aggregate inventory exists. |
| NEW-3 | S2 | §26 rule 7 ("honor opt-out **immediately**") has no mechanism. No per-host opt-out register exists, and stopping a host requires a package-data registry edit plus rebuilding and redeploying the ingest images (config is baked in, G1 NEW-10). Refines E1 NEW-15. |

Adjacent items routed to stream E by other rows and handled here: F-03 → memo A-1; J1 NEW-2/NEW-3 → folded into
E2-12; J1 NEW-9 (the public API role's blanket SELECT reaches `evidence_access_log`) → a least-privilege engineering
fix for G1 that needs no policy decision, noted in E2-10 because those are the records a legal demand would target.

---

## 10. Evidence re-checked in this row, and limits

All reads were read-only. `date -u` 2026-09-30T17:02:08Z (start) and 17:09:06Z.

| read | result used in |
|---|---|
| `sed -n 75,95p policy/src/policy/officer.py`; `grep -n _concurrence_ok` → `:82`, called `:128` | E2-01 |
| `sed -n 30,80p web/src/lib/publication.ts` | E2-01 (H-9) |
| `sed -n 1,80p web/src/pages/editorial-standards.astro`; `grep -n assertReviewReleasable web/src/lib/editorial.ts` → `:221-235`; `grep -rln "assertReviewReleasable\|getHostileReaderReview" web/src web/tests` → data.ts, editorial.ts, editorial-standards.astro, editorial.test.ts; `grep -rn "template_version\|hostile" web/src/pages/dossier web/src/pages/research-dossier` → 0 hits; `editorial.test.ts:78-79,98-100` | E2-02, NEW-1 |
| `grep -rn human-verified web/src …` → `web/src/lib/resolution-eval.ts:67` | E2-14 |
| `api/src/api/terms.py:28-35`; `docs/governance/governance-and-code-of-conduct.md:14-34,50-70` | E2-03, E2-04, A-1 |
| `grep -n DEFAULT_CONTACT_URL\|sig-project.org` over connectors/tasks/ops → 4 sites; `net.py:375-400` | E2-06, E2-08 |
| `grep -rn "opt_out\|opt-out\|optout\|do_not_crawl\|denylist\|blocklist"` over `connectors/src policy/src` → only procurement fixture comments and the dot_511 media blocklist; `grep -rn "parse_content_signal\|content_signal_permits_training"` → `tests/unit/test_policy_crawler.py:52,67` only | E2-06, NEW-3 |
| `connectors/src/connectors/registry.py:219` (`load_table("sources")`); `ops/Dockerfile:56` (`COPY connectors ./connectors`) | NEW-3 |
| `python3` over `docs/build/reports/live_runs/2026-09-19_*_p2617.json` `robots_disregarded` (entries, hosts, verdicts, TLDs); `grep -rl robots_disregarded docs/build/reports` → 5 files; `grep -n "primegov\|raa_prefectures\|escribe" ops/cadence.toml` → `:111`, `:275-279`, `:291-295` | E2-06, NEW-2 |
| `docs/adr/ADR-145…md:110-130`; ADR-088 `## Revisit trigger`; ADR-106 `## Revisit trigger`; `grep -n counsel` in ADR-086/106 | E2-01, E2-05, E2-06, E2-13 |
| `grep -n "RISK-P0-01\|RISK-P0-05\|RISK-P0-13" docs/risk_register.md`; RISK-P21-02 | E2-01, E2-04, E2-05 |
| `grep` of `docs/build/COVERAGE_MATRIX.csv` for the ids named | all memos |
| `docs/3_sig_golive_spec.md:46,93` (GL-GATE-02 label text, HG-02) | E2-05 |
| `findings/FINDINGS.csv` and `findings/incoming/*.csv` (titles; J1 NEW-2/3/9 in full) | §0.1, §9 |

**Limits.**
- No legal conclusion is drawn anywhere. Exposure lines are plain descriptions (P4).
- Engineering sizes are guesses [est]. Human effort and cost are E3's planning estimates.
- Domain registration and Software Heritage figures are unverified inference.
- Hosted run rows were not queried for robots disregards (NEW-2 counts only the five committed P26.17 run files).
- Public pages were not re-captured in this row; live-site facts are E1's and A2's reads of 16:39–16:56Z.
- Whether `sources.toml` reviewer values can carry an "operator-reported" qualifier without a validator change was
  not tested.
