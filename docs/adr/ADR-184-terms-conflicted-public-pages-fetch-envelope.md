# ADR-184: Terms-conflicted public pages — the vendor and platform fetch envelope

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-INGEST-037 (this ADR is the ADR-level deviation decision it requires; its counsel clause is waived by ADR-182), SIG-INGEST-036 (rules 1, 3, 4, 5, 7, 8 bind; rule 2 per GL-GATE-08; rule 6 per ADR-187), SIG-INGEST-013, SIG-INGEST-035 (compartment clause; its no-direct-capture clause per ADR-188), SIG-INGEST-046c, SIG-LIC-001, SIG-LIC-002, SIG-LIC-004a, SIG-LIC-010, SIG-PUB-002, SIG-PUB-003, SIG-PUB-003a
- **Spec:** docs/2_canonical_design_spec.md §26 — SIG-INGEST-036 at lines 4472–4492 and SIG-INGEST-037 at lines 4494–4497; §21.5 — SIG-INGEST-013 at lines 3518–3519; §23.4 — SIG-INGEST-035 at lines 4199–4202; §42 and §43 (as built at `71e8bc83`; sources `docs/research/_meta/spec_src/52_partIV_s23to26_connectors_parse.md`, `50_partIV_s21_connectors.md`, `90_partVIII_s42to43_lic_pub.md`)
- **Decision:** the operator's answers to A-17 (2026-10-01T04:16:29Z), B-6 (04:33:54Z), B-35 (04:46:04Z), B-39 (04:49:27Z), B-41 R2a (04:51:39Z), C-8 (04:59:05Z) and round 26 (06:51:11Z) — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, rounds 6, 11, 16, 17, 18, 21 and 26
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.2 (A-17), §4.4 (B-35, B-39, B-41), §5.5 (design and Flock/Axon depth), §6.3 (SIG-INGEST rows), §7 row 184, §14 R-18/R-21
- **Related:** ADR-172 (product direction: D3-Q3 = b), ADR-168 (collection conduct; GL-GATE-08 on every host, extends ADR-088), ADR-185 (Part VIII lanes; the one persistence rule), ADR-187 (WV-09), ADR-188 (WV-10), ADR-182 (WV-07), ADR-083 / ADR-087 / ADR-088 (robots and API-mode posture)
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

D3 recommended that Flock and Axon facts come only from agency pages, procurement records, statutory reports and
already-ingested mirrors, never from vendor hosts, because the captured vendor terms prohibit automated extraction
(D3-Q3 a). The operator chose instead to fetch vendor-hosted pages (A-17, D3-Q3 b), to fetch Axon Fusus "Connect
<Place>" pages in full (B-35 IT7), and to fetch DocumentCloud/MuckRock and Sourcewell/OMNIA despite their terms (B-39;
B-41 R2a re-asked in round 18). SIG-INGEST-037 makes deviation from the crawler-conduct posture "an ADR-level decision
… not an engineering judgment" and names vendor terms that "expressly prohibit bulk extraction"; this ADR is that
decision. Its counsel clause is waived (WV-07, ADR-182). The log recorded, as a labelled agent interpretation of A-17,
the engineering envelope the agent would apply — "not a re-decision". This ADR writes that envelope down as binding
conditions.

## Decision

### The operator's words (verbatim, with the log's round times)

| line | answer, verbatim | time (`date -u`) |
|---|---|---|
| A-17 (ratify D3; D3-Q3) | "Ratify; fetch vendor pages" | 2026-10-01T04:16:29Z |
| B-6 (UA and domain) | "Move UA, don't buy domain" | 2026-10-01T04:33:54Z |
| B-35 (IT1–IT7; IT7 = Axon Fusus Connect pages) | "IT7 full fetch" | 2026-10-01T04:46:04Z |
| B-39 (terms conflicts C2/C3/…) | "Also fetch DocCloud/Sourcewell" | 2026-10-01T04:49:27Z |
| B-41 R2a vs B-39 (DocumentCloud: fetch or decline) | "Fetch, screened (Recommended)" | 2026-10-01T04:51:39Z |
| C-8 (contact-string requests) | "Alias first (Recommended)" | 2026-10-01T04:59:05Z |
| S6R-01 (Flock portals vs SIG-INGEST-035) | "Waive 035; probe without circumventing" | 2026-10-01T06:51:11Z |
| S6R-08 (GL-GATE-08 scope) | "All hosts, as ADR-088 (Recommended)" | 2026-10-01T06:51:11Z |

These are selected option labels; the own-words sentences these lines produced are recorded in their own ADRs (WV-09
in ADR-187, WV-10 in ADR-188). The envelope text in the log (round 6, labelled *agent interpretation*, not operator
words): *"public, unauthenticated pages only; no logins, API keys, or circumvention of access controls; rate-limited;
P16 contact string; terms text captured verbatim and the exposure disclosed."* — sha256
`7138599905455b04449619a68af67eb4abcfe4ab43a40666a826d41869b0f3eb` (computed by SEED-11d, for traceability only).

### Sources in scope

| source family | Round-11 row | activation |
|---|---|---|
| Axon Fusus agency-hosted "Connect <Place>" pages (B-35 IT7) | P36.76 | Wave D, P37.54, after the operator's HG-03 flip |
| DocumentCloud / MuckRock documents (B-39 C2; E4-R2a b), through its documented unauthenticated API (rule 5) | P36.77 | Wave D, P37.54, after the operator's HG-03 flip; rule 6 waived for it by ADR-187 |
| Sourcewell and OMNIA Partners contract pages (B-39 C3) | P36.78 | Wave D, P37.54, after the operator's HG-03 flip |
| Flock transparency portals (A-17) | P36.74 | Wave B, P36.12 — **probe-only**, under ADR-188 |

Any other terms-conflicted source needs its own operator line and an ADR; this envelope does not extend itself.

### The envelope (binding conditions on every fetch in scope)

1. **Public, unauthenticated pages only.** No logins, accounts, API keys, tokens, paywalled or access-controlled
   content.
2. **No circumvention.** No challenge-solving, header spoofing, proxy rotation, human-mimicking or browser automation
   to defeat bot management (rule 4; SIG-INGEST-013; SIG-INGEST-037). A bot challenge, a 403 served as a challenge, an
   interstitial or a block ends the attempt and is recorded as a refusal.
3. **Gentle.** A conservative per-host rate limit with backoff (rule 3); the offered channel where one exists (rule 5);
   conditional requests and content-hash short-circuits (rule 8).
4. **Identity (rule 1; P16).** The project UA names an owned explanation page on surveillancegraph.org
   (`https://surveillancegraph.org/data-collection/`, row **P35.38a**, which lands before any Round-11 fetch and ships
   the page in republish #1), never the operator's name, e-mail or any personal identifier. `sig-project.org` is not
   used (B-6). No request that needs a contact string (a registration or key sign-up) is sent until
   `contact@surveillancegraph.org` exists (C-8 "alias first"; OP-10).
5. **Robots, reservations, opt-outs.** Robots disallows are recorded `robots_disregarded` and disclosed as host + count
   on every host, per GL-GATE-08 and ADR-088 (ADR-168); an affirmative machine-readable rights reservation is refused
   (SIG-INGEST-046c); an opt-out is honoured at once and recorded in the rule-7 register (P36.1a, built before Wave A).
6. **Terms captured and disclosed.** Each source's terms text is captured verbatim into its rights record and archived
   as evidence before activation (SIG-LIC-001/002), and the exposure — that SIG fetches against those terms — is
   disclosed on the source page and in the files.
7. **Part VIII before persistence.** Every byte passes the Part VIII screen before storage or publication, and
   SIG-PUB-002/003/003a are applied before persistence by ADR-185's one rule (a redacted rendition + the upstream URL +
   the sha256 of the original, or only the pointer and the screened facts). Private Connect registrants — resident or
   business names, home addresses, contact data, cameras at private residences — are never stored in any tier (the
   log's "never stored in public output" is narrowed to SIG-PUB-002's "in any tier", S6 flag 4); Connect pages yield
   programme-level facts and counts only (I7 S1 lane).
8. **A rights record and a compartment for every source.** Each terms-conflicted source gets a rights record and an
   export compartment so SIG-LIC-010's computed-licence build check passes. Flock portal output and the Flock share
   lists land in the CC BY-SA 4.0 compartment, never merged into the CC-BY graph (SIG-INGEST-035's compartment clause;
   SIG-LIC-004a; S6R-12).
9. **The operator flips; agents never do.** Each new source lands `ingestion_permitted=false`; the operator flips it
   (HG-03) with its wave's ING-GO (OP-26). Gates are never ticked by an agent.
10. **Stop and record.** A cease-and-desist, an access block, a terms change, an objection or an opt-out stops that
    source at once and is recorded; its published rows are withdrawn by new claims through the withdrawal barrier
    (P34.41); only the operator decides any resumption.

### What this ADR does not decide

Flock's no-direct-capture clause (ADR-188); rule 6 for DocumentCloud/MuckRock (ADR-187); the Part VIII lanes and the
persistence rule (ADR-185); GL-GATE-08 itself (ADR-168); the SIG-CHART-025 amendment (ADR-172); the counsel clauses
(ADR-182).

## Consequences

- SIG fetches pages whose operators' terms forbid automated access. The exposure — breach-of-terms or access claims,
  an IP block — is the operator's accepted risk, plan §14 R-18; for Flock portals the residual is a probe request, not
  extraction.
- Coverage gains programme-level Axon facts, DocumentCloud documents and cooperative-contract pages (plan §5.5 vendor
  table); anything behind a login or key, person-level fields and private Connect registrants stay dark by design.
- T4 records R-18 and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **D3-Q3 a (never fetch vendor hosts)**, **IT7 facts-only pointer**, and **link-only / pointer-only for DocumentCloud
  and Sourcewell (I7-C2 a, I7-C3 a)** — the recommendations, not chosen.
- **Seeking permission first** (I7-C3 b; E4-R2a c). Needs outside contact, excluded by U-011.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- a cease-and-desist, an access block, a terms change or an opt-out affecting any source in scope (stop first);
- a Flock portal is served without a challenge (the first non-zero yield — ADR-188's trigger);
- the operator authorises outside contact (U-011 revisited; LATER-04), so permission could be asked instead;
- the operator obtains counsel (LATER-05), or a first legal demand arrives.
