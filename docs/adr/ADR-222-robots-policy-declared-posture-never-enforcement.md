# ADR-222 — `robots_policy` is a review-time declaration, never an enforcement claim (P36.1b)

- Date: 2026-10-26
- Status: accepted
- Ticket: P36.1b (R11-GOV-04, manifest row 349 — on `r11/P36.1b-crawler-conduct-text-and-robots-field`)
- Base: `r11/P35.23-real-data-regression-corpus`
- Supersedes: ADR-088 (the "accurate declarations" clause only — the
  `robots_policy` sentence of Decision §5 and the rejected flip-to-
  `not_applicable` alternative; the probe-and-record decision itself stands
  unchanged, re-confirmed by the collection-conduct ADR named below)
- Related: GL-GATE-08 (`docs/build/LEDGER.md` § GATE DECISIONS, 2026-09-18),
  ADR-088 (the robots enforcement removal this field outlived), ADR-087
  (the RFC 9309 §2.3.1.4 classification layer), ADR-083 (the documented
  API-mode carve-out), ADR-168 (the A-5 re-confirmation on every host),
  ADR-182 (WV-07 — the waived counsel clause), ADR-187 (WV-09 — the
  DocumentCloud/MuckRock rule-6 waiver), Q-E2-02 [B-6 = yes] (the adopted
  decision line this ADR executes: *"Bring crawler_conduct.toml, the
  crawler.py docstring, the registry robots_policy field and the outreach
  letter into line with the E2-06 outcome in one ticket, with a new ADR
  superseding ADR-088's 'accurate declarations' clause; the policy of record
  is crawler_conduct.toml, published on the crawler page"* — Q-E2-02,
  answered yes), E2-07 (the contradiction), SIG-INGEST-036/046b/046c,
  SIG-ENG-042.

## Context

`robots_policy = "honor"` sits on the overwhelming majority of
`connectors/src/connectors/data/sources.toml` rows (~579 `honor`, 9
`not_applicable`). It was seeded when the conduct text said SIG "honors
robots.txt" — and ADR-088's body kept the values, reasoning that "the
registry rows are accurate declarations of posture; the ADR changes what
enforcement means". E2-07 (E1-07) found the residual contradiction: after
GL-GATE-08 the fetcher proceeds despite a `disallowed`/`unretrievable`
verdict and stamps `robots_disregarded`, so a published `robots_policy =
"honor"` reads — to a site operator or a journalist — as a promise the code
does not keep. The registry is not public yet, but Stream J plans to
publish it; at that point hundreds of `"honor"` values become public false
statements.

The decided line (Q-E2-02, adopted with B-6 = yes) offered two lawful
fixes — retire the `honor` values, or document the field as *"posture
declared at review time; not enforced"* — and required this ADR either way.

## Decision

1. **`robots_policy` is fixed by declaration as review-time metadata.** The
   field records what a review observed about the source's surface — which
   surface a robots policy governs — not what `PoliteFetcher` will do. No
   value of the field changes behaviour: under GL-GATE-08 (ADR-088, applied
   to every host per ADR-168) every host's robots verdict is probed,
   classified per RFC 9309 §2.3.1.4 and recorded, and a non-grant verdict
   is stamped `robots_disregarded` and disclosed publicly as host + count
   — never enforced.
2. **The vocabulary is kept verbatim** (additive / back-compat; a retcon
   would obscure 588 rows of seeded record): `honor` = a robots policy
   governs this crawl surface — read "probe and record";
   `honor_with_exception` = the same with a recorded exception basis (an
   ADR-083 documented-API allow-list entry); `not_applicable` = no
   robots-governed surface. The semantics are documented where the data
   lives: `connectors/registry.py` `RobotsPolicy` and the `sources.toml`
   header comment.
3. **The policy of record is `crawler_conduct.toml`, published on the
   crawler page.** `policy/src/policy/data/crawler_conduct.toml` now states
   the decided posture verbatim-true (rules 1, 2, 4, 6, 7 carry the
   Round-11 amendments), `policy.crawler`'s docstring matches it, the
   `/data-collection/` page carries the rules verbatim pinned by the copy
   batch, and the Stage-0 outreach letter no longer claims robots
   enforcement. A copy check (`tests/unit/test_conduct_text.py`) fails when
   the text asserts conduct the code does not implement.
4. **A robots disallow is never a reservation.** The field and text must
   not blur the states: a `Disallow` proceeds stamped
   `robots_disregarded`; an affirmative machine-readable rights reservation
   (SIG-INGEST-046c — Content-Signal, TDM-Reservation, X-Robots-Tag
   `noai`/`noimageai`, EU DSM Article 4) is refused and recorded on the
   rights record, and a host-level opt-out (§26 rule 7) receives zero
   egress. The ALPR Abuse Library's recorded reservation
   (`[sources.alpr_abuse_library.rights.reservation]`, F2.20 evidence) is
   the first row carrying the refused state.

## Consequences

- The `honor` values stay — the field is honest because its *declared
  meaning* is now the review-time observation, documented next to the data
  and on the enum. Nothing downstream reads it as an enforcement switch
  (`net.py` never consulted it for gating).
- The E2-07 text/code contradiction closes: conduct file, docstring,
  registry field, page and letter all state the same posture.
- `robots_policy` changes remain registry edits; a real posture change is
  a new gate decision + ADR, never a value retcon (SIG-ENG-003).
- The Stage-0 letter's conduct bullet is corrected **before any send** —
  sending remains operator outreach under ADR-171 (D-R11-LATER-04).

## Alternatives considered

- **Retire `honor` and rewrite every row** (E2-07 option 1a). Rejected —
  ~580 row rewrites obscure the seeded record to fix a semantic ambiguity a
  documented reading resolves; append-only convention favours declaring
  the meaning over renaming the data.
- **Leave ADR-088's clause standing.** Rejected — the E2-07 finding is that
  "declared posture" without a documented meaning *is* the false statement
  once the registry publishes; Q-E2-02's adopted line required this ADR.
- **Make the field drive behaviour** (e.g. `honor` re-gates). Rejected —
  A-5 re-confirmed GL-GATE-08 as is on every host; no posture change was
  asked or decided.

## Revisit trigger

- The registry exports publicly and a consumer demonstrably misreads the
  field as an enforcement promise — then the vocabulary is retired by a new
  ADR (additive rename, never a retcon).
- GL-GATE-08 is revoked or narrowed by a new gate decision — the field's
  meaning is re-documented with the new posture.
- A new reservation or opt-out form lands that the text does not name —
  the conduct file, page and this declaration are updated together.
