# ADR-168: Collection conduct — GL-GATE-08 re-confirmed on every host; reservations and opt-outs honoured

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 168)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: A-5 at 2026-10-01T04:03:25Z (log round 3); scope
  (S6R-08) at 2026-10-01T06:51:11Z (log round 26)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P). This ADR records the decision; it decides nothing the operator did not.
- **Relation to landed ADRs:** **extends ADR-088** (the `Extended by ADR-168 (<date -u>)` status line on ADR-088 is
  appended by SEED-11d, not by this file). ADR-087's RFC 9309 classification layer and ADR-083's documented-API mode are
  unchanged.
- **Related:** GL-GATE-08 (`docs/build/LEDGER.md` § GATE DECISIONS, 2026-09-18); SIG-INGEST-011/012/013, SIG-INGEST-036
  (§26 rules 1–8), SIG-INGEST-037, SIG-INGEST-046b/046c; RISK-P0-06 (via BL-001); ADR-171 (outreach), ADR-182 (WV-07,
  counsel clauses), ADR-183 (express-terms acceptance), ADR-184 (terms-conflicted fetch envelope), ADR-187 (WV-09, rule 6
  for DocumentCloud/MuckRock), ADR-188 (WV-10, Flock portals probe-only); plan rows P35.38a, P35.38b, P36.1a, P36.1b,
  P35.11; operator actions OP-10. `PD` below = `docs/build/planning/2026-09-30-next-phase/`: `PD/NEXT_PHASE_PLAN.md`
  §4.2 A-5, §4.9, §5.5, §6.3, §6.5, §14 R-21/R-29; `PD/feedback/RATIFICATION_LOG.md` rounds 3, 11, 21, 26;
  `PD/design/E2-governance-options.md` E2-06/E2-07/E2-08; `PD/reviews/S6r-consistency.md` S6R-08;
  `PD/data/decision_catalog.csv` rows Q-E2-11, Q-E2-02, Q-E2-03, GL-GATE-08-SCOPE.

## Context

**What was recorded.** GL-GATE-08 was recorded on 2026-09-18 (`docs/build/LEDGER.md` § GATE DECISIONS), verbatim:
*"I also wonder if we should disregard robots.txt-gated sources and crawl them anyway"* → operator decision **disregard
robots entirely** — robots verdicts stop gating fetches; the verdict is still probed and recorded per target. ADR-088
(P26.17, 2026-09-19) executed it: `PoliteFetcher` still probes, caches and classifies each host's `robots.txt` per
RFC 9309 §2.3.1.4 (ADR-087), but a `disallowed` or `unretrievable` verdict never blocks a fetch; the fetch proceeds and
carries the per-URL `robots_disregarded` provenance marker.

**What the Stage-P review found** (E1-06/E2-06, E2-07, E2-08, E2-X1; facts as recorded in E2, not re-measured here):

- The recorded words are a question, so the decision needed the operator's confirmation in their own words (E2-X1,
  Q-E2-21; OM-09).
- SIG-INGEST-037 says a crawler-conduct deviation "is an ADR-level decision requiring counsel"; no counsel step occurred
  ("counsel" so far was the operator, U-013; the C-3 sentence recorded by ADR-167).
- §26 rule 7 (honour opt-outs immediately) and SIG-INGEST-046c (an affirmative machine-readable rights reservation MUST
  be honoured as a refusal) were never built: E2 found no opt-out register in `connectors/` or `policy/`, and the
  Content-Signal parser is called only from a unit test.
- Scale: the P26.17 run files record **125 disregarded fetches on 122 hosts** — 103 explicit `disallowed` verdicts
  (102 PrimeGov municipal-agenda hosts and `www.oscn.net`) and 22 `unretrievable` policies.
- The published crawler texts still say SIG honours robots (`crawler_conduct.toml` rule 2, the `crawler.py` docstring,
  `robots_policy = "honor"` on 235 permitted registry rows, the unsent Stage-0 outreach letter) (E2-07).
- The user agent's contact URL `+https://sig-project.org/data-collection` names a domain nobody owns, hard-coded in four
  places (E2-08).
- RISK-P0-06 ("SIG-INGEST-037 no-circumvention as a *legal posture*") sat under BL-001's "tested deterministic gate"
  rationale, which ADR-088 removed for robots (F3).

**What the operator was asked.** A-5 (log round 3): "robots rule (GL-GATE-08 re-decided in the operator's words)", with
the options *Honour vendor/reservations; US gov ok (Recommended)* · *Obey robots.txt everywhere* · *Re-confirm GL-GATE-08
as is*. The fresh-context review S6r then found the plan applying "as is" to new hosts while the log's labelled reading
named the 122 hosts (S6R-08); round 26 asked "does GL-GATE-08 'as is' cover new hosts?" with *All hosts, as ADR-088
(Recommended)* · *Only the 122 hosts*.

## Decision

1. **GL-GATE-08 stands as recorded, re-confirmed by the operator at GATE-P** (A-5, 2026-10-01T04:03:25Z). The operator
   chose **against the recommendation**: they declined *"Honour vendor/reservations; US gov ok"* (Q-E2-11 **b**: at
   minimum honour explicit disallows on vendor platforms such as PrimeGov and every TDM/rights reservation everywhere,
   with the disregard for US public-body hosts continuing only in the operator's own words) and *"Obey robots.txt
   everywhere"* (Q-E2-11 **c**), and selected *"Re-confirm GL-GATE-08 as is"*, adopting its option text as their words
   (§ Operator words recorded).
2. **Scope: every host, per ADR-088** (round 26, 2026-10-01T06:51:11Z, as recommended). Robots `disallowed` and
   `unretrievable` verdicts are disregarded on the 122 hosts incl. PrimeGov **and on every new host** SIG fetches, vendor
   and platform hosts included (the A-17 and B-39 fetch lanes, ADR-172/ADR-184). No host is paused for robots (P35.1b
   pauses none).
3. **Mechanism unchanged.** ADR-088 §Decision 1–5 stand as landed: the probe runs, the verdict is classified per
   RFC 9309 (ADR-087) and recorded per URL as `robots_disregarded`, and it never gates; ADR-083's documented-API mode is
   unchanged; crawl-delay and `rate_limit_per_min` pins are honoured; challenges are never defeated.
4. **Disclosure.** Every disregard is disclosed publicly as **host + count**, with a GL-GATE-08 reference, in the scrubbed
   public run logs (B-19 / D-J3-2) and on the crawler explanation page (`/data-collection/`: minimal page in P35.38a, full
   crawler conduct text in P36.1b). The published crawler texts are brought into line with this posture (Q-E2-02 = yes,
   answered at B-6, 2026-10-01T04:33:54Z): `crawler_conduct.toml` rule 2, the `crawler.py` docstring, the registry
   `robots_policy` field — documented as a posture declared at review time, read as "probe and record, never enforced"
   for every value (ADR-088 Decision 5's reading, made explicit in the published text) — and the outreach letter text
   (which is not sent this round, ADR-171). This changes no ADR-088 clause; §7 records the relation as an extension.
5. **A disregarded disallow is not a reservation, a licence or an ingestion clearance.** Still built and binding on every
   host — **not waived**:
   - **SIG-INGEST-046c:** an affirmative machine-readable rights reservation (e.g. a Content-Signal header, a TDM
     reservation, an EU DSM Article 4 reservation) is honoured as a refusal and recorded on the rights record. A host whose
     robots disallow is disregarded is still refused if it publishes such a reservation.
   - **§26 rule 7:** a host-level opt-out register, checked before every fetch, honoured at once and recorded in the
     compact, without an image rebuild.
   - Both are built by **P36.1a**, which sits ahead of every Round-11 acquisition activation (hard edge P36.1a → P35.11,
     Wave A; S6R-04). P36.1a also classifies the captured licence metadata of the express-terms rows kept under A-8
     (ADR-183); any that is an affirmative reservation goes back to the operator in the GATE-G5 packet (§14 R-19; S6R-28).
   - §26 rules 1, 3, 4, 5 and 8 and SIG-INGEST-013 bind every source; rule 6 ("ask first") binds every source except
     DocumentCloud/MuckRock (WV-09, ADR-187); the fail-closed ingestion gate (`ingestion_permitted`, HG-03) stays the
     binding access control, which robots never replaces.
6. **Rule 1 — identify (P16).** Before any Round-11 acquisition fetch, **P35.38a** (row 203, at the head of 11A) moves the
   user agent's contact URL to an owned explanation page, `https://surveillancegraph.org/data-collection/`, never the
   operator's personal identifiers; e-mail contact runs only through `contact@surveillancegraph.org` once the operator
   creates it (OP-10; C-8 *"Alias first (Recommended)"*, 2026-10-01T04:59:05Z). Every Round-11 activation row carries a
   hard edge to P35.38a. The existing first-fire crons keep the old UA until the next connector-image roll — the exposure
   window B-6 accepted.
7. **`sig-project.org` is not bought** (B-6 *"Move UA, don't buy domain"*, 2026-10-01T04:33:54Z; Q-E2-03 **b**). The
   operator chose this **against the recommendation** (B-6 *"As stated (Recommended)"*, i.e. Q-E2-03 **a**: register
   `sig-project.org` defensively and move the UA). Every remaining reference to the unbought domain is removed from code
   and docs (P35.38a; the IRI base moves in P35.38b with an alias map); the residual squatting risk is §14 R-29.
8. **SIG-INGEST-037's legal posture, restated in the operator's A-5 words.** Rule 4 (never circumvent access controls) is
   a legal posture and stands unchanged: no authentication bypass, paywall evasion, challenge-solving, proxy rotation or
   human-mimicking to defeat bot management (rule 4; SIG-INGEST-013; ADR-088 Decision 5), and no user-agent spoofing
   (rule 1). The departure from the policy's original "honour robots" reading
   is this ADR-level decision, resting on the operator's recorded determination at A-5, not on counsel — SIG-INGEST-037's
   counsel clause is waived by WV-07 (ADR-182). Plan §6.5 records that **RISK-P0-06 closes by this ADR**; appending that
   closure to `docs/risk_register.md` / BL-001 is record work outside this file.

### Labelled agent interpretation (from the log, applied as written)

- Log round 3: *"A-5 → GL-GATE-08 stands for robots.txt disallows on the 122 hosts (incl. PrimeGov), disclosed as host +
  count in public run logs (B-19). It does not by itself waive SIG-INGEST-046c … or the rule-7 opt-out register … Disallow
  ≠ reservation: a host that publishes an explicit reservation is refused under 046c even though its robots disallow is
  disregarded."*
- Log round 26: *"S6R-08 → GL-GATE-08 applies to every host per ADR-088 (disallows recorded as `robots_disregarded`,
  disclosed as host + count); 046c reservations and rule-7 opt-outs honoured everywhere."*
- "Vendor and platform hosts included" (Decision 2) is the plan's reading of "All hosts" (§4.2 A-5; §5.5), labelled here
  as agent interpretation of the operator's round-26 answer.

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time (log) | words | label | sha256 |
|---|---|---|---|---|
| GL-GATE-08 (2026-09-18) | LEDGER § GATE DECISIONS | *"I also wonder if we should disregard robots.txt-gated sources and crawl them anyway"* | the operator's own words (a question; E2-X1) | `4ea45f22648f42e85d82b96ac81a881ce34a7bd52f44979f81227e33987c56db` |
| A-5 (selected option) | 2026-10-01T04:03:25Z | *"Re-confirm GL-GATE-08 as is"* | option label selected by the operator | `a18c157582477205dc8ca4edd5a745283a56cc47fa059e9bcd1c5bede2ae34ca` |
| A-5 (adopted option text) | 2026-10-01T04:03:25Z | *"Keep disregarding on all 122 hosts incl. PrimeGov; conflicts with SIG-INGEST-046c for reservations. Not recommended."* | agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z (the operator chose it over the recommendation) | `9a8a3109c95faaecec7a744d90c6e49e52d72aaae6a3550e7edad38f5633de13` |
| S6R-08 / GL-GATE-08-SCOPE | 2026-10-01T06:51:11Z | *"All hosts, as ADR-088 (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T06:51:11Z | `038d8bb1c184bd08034d1dac3c8ce84a1d60a3fd53f1bbe12cf4c8df4b1d5c22` |
| B-6 | 2026-10-01T04:33:54Z | *"Move UA, don't buy domain"* | option label selected by the operator (against the recommendation) | `7a31095fa9947a22d967f8b20f7ccb6f05a7596f0b0f282359c226d61073de68` |
| C-8 | 2026-10-01T04:59:05Z | *"Alias first (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:59:05Z | `8f8d7914fbb8f07dbecf848b69c378aff131ccc06bd5245ba813a756333a8f38` |

## Consequences

- **Accepted risk (§14 R-21):** robots disallows are disregarded on every host, including a vendor platform (PrimeGov)
  that disallows `/` platform-wide; the practical exposure is complaints and egress-IP blocks on shared infrastructure.
  Mitigations: public host + count disclosure, 046c reservations refused, rule-7 opt-outs honoured at once, conservative
  rate limits; blocks and challenges are recorded (`access_restricted` / `unreachable`), never evaded.
- **Coverage kept:** the PrimeGov, eScribe, `ok_statute`, `ccops_sf` and RAA hosts stay reachable; no Round-11 host is
  paused for robots.
- **Build order:** P36.1a (opt-out register + 046c refusal) and P35.38a (owned UA contact page) land before any
  Round-11 acquisition fetch; P36.1b writes the full crawler conduct text in 11C.
- **Unbought domain (§14 R-29):** until every ingest image is rolled, old UA strings name an unowned domain; a third
  party could register it.
- **Records:** the go-live spec records GL-GATE-08 as re-confirmed at GATE-P in the operator's adopted words (SEED-12;
  Appendix A T1); the spec's §26 / SIG-INGEST-036 / -037 / -046c amendment notes are SEED-12's `spec_src` work.

## Alternatives considered

- **Honour vendor/reservations; US gov ok** (recommended; Q-E2-11 b) — declined by the operator at A-5.
- **Obey robots.txt everywhere** (Q-E2-11 c; re-gate) — declined; it would have lost at least the 103 explicit-refusal
  hosts' agenda and statute evidence.
- **Only the 122 hosts** (round 26) — declined; GL-GATE-08 applies to every host per ADR-088.
- **Treat a disregarded disallow as covering reservations too** — rejected: SIG-INGEST-046c was never waived, and a
  reservation is a different, stronger signal than a disallow.

## Revisit trigger

- An **opt-out** from any host or upstream (honoured at once under rule 7, then reviewed), an **affirmative
  reservation** found on a host already fetched, an **egress-IP block** or other access block on shared vendor
  infrastructure, or a host operator's **objection** (§14 R-21; ADR-088's first trigger).
- A **cease-and-desist or other legal demand** about collection (handled under the legal-demand posture, ADR-166).
- **Counsel is obtained** (LATER-05) and advises against disregarding robots verdicts — this restates ADR-088's
  counsel-conditioned trigger ("Counsel objects"), dormant while there is no counsel (F3 NEW-8), as an event that can fire.
- The operator revokes or narrows GL-GATE-08 (a new gate decision and a new ADR, never a silent code change).
- `sig-project.org` is registered by a third party (§14 R-29).
- RFC 9309 is revised or superseded (ADR-087's and ADR-088's own trigger).
