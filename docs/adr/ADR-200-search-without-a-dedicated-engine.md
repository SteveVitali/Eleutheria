# ADR-200 — Search without a dedicated engine: pg_trgm on the read API plus per-compartment FTS5 on releases (P34.48)

- Date: 2026-10-06
- Status: accepted
- Ticket: P34.48 (Round 11 / P34, row 240 — the MET-DIFFERENTLY re-verdict; owns the SIG-UI-040
  named addition SEED-15 routed there)
- Base: `r11/PLAN-11B-contracts-for-11b-and-transp-family`
- Related: **ADR-108** (the bounded `/v1/search` contract — `pg_trgm`, pool-bounded, statement
  timeouts), **ADR-133** (per-compartment immutable corpus search — SQLite FTS5 artifacts, no
  search cluster), ADR-150 (the verdict grammar this ADR exists to satisfy: a
  `MET-DIFFERENTLY(ADR-nnn)` verdict needs an accepted ADR that names the requirement id),
  BL-084 (this ADR's trigger home).

## Context

**SIG-UI-040 (SHOULD):** "Search SHOULD start with Postgres full-text search and add a dedicated
engine only on demonstrated need, checking licensing at that time."

The requirement was first verdicted `MET-DIFFERENTLY(ADR-108;ADR-133)` at F2a on the reading that
the dedicated engine is rejected by design and Postgres-side search already ships. SEED-15
(2026-10-01, assessment `SIG-UI-040:r11-2`) withdrew that parameterised verdict to bare
`MET-DIFFERENTLY` routed to P34.48, because ADR-150 D1/D4 admit `MET-DIFFERENTLY(ADR)` only when
the cited ADR *names the requirement id* — and neither ADR-108 nor ADR-133 names SIG-UI-040 — while
landed ADR bodies are frozen (SIG-ENG-003). The ticket contract records the intent: "a new ADR, if
written, takes the next free number at dispatch and cites both."

## Decision

**SIG-UI-040 is satisfied differently from its letter, and this ADR records the deviation.**

1. **There is no `tsvector` full-text search and no dedicated search engine.** The two search
   surfaces are deliberately split:
   - The read API's `/v1/search` is identifier/substring search over the claim spine using
     `pg_trgm` — ADR-108 rejected `tsvector` for this surface because SIG's searchable text is
     identifier-shaped (`traffic_camera:camreg_jmh_us:jmh_us_mpd_flock:1`), where trigram
     matching is the right primitive; the route is bounded (min query run, `limit` ≤ 200, cursor
     keyset, statement timeout — `api/src/api/routes.py`, `api/src/api/store_pg.py`).
   - Released-corpus search is per-compartment **SQLite FTS5** index artifacts emitted at export
     and served read-only — ADR-133 rejected a search cluster for the released corpora at this
     scale (`exports/src/exports/search_index.py`, `api/src/api/release_search.py`,
     `tests/exports/test_search_index.py`, `tests/api/test_release_search.py`).

2. **The requirement's intent holds verbatim.** "Start with Postgres" is the operating posture
   (`pg_trgm` is the in-database search primitive over the canonical store); "add a dedicated
   engine only on demonstrated need" is the standing rule — no engine is run, and adopting one is
   trigger-gated (below); "checking licensing at that time" binds unchanged.

3. **The deviation is recorded once, here.** A later row citing `MET-DIFFERENTLY(ADR-200)` for
   SIG-UI-040 cites this ADR, which names the id and the alternative; the F2a reading is preserved
   in the coverage row's note.

## Revisit trigger

- `/v1/search` p95 or its statement timeout degrades on real queries, or the surface needs
  ranking/fuzzy matching/search over claim values rather than identifiers (ADR-108's own trigger
  set);
- a released-corpus FTS5 index grows past what read-only SQLite serving supports, or
  cross-compartment search is demanded (ADR-133's boundary);
- a requirement lands that demands full-text ranking or an engine neither surface can express —
  the dedicated-engine decision is then re-opened with its licensing check, as SIG-UI-040
  requires.
