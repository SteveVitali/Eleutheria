# ADR-069 — Contribution-back live: the MapRoulette client, the OSM changeset feed, and the registration gate

- **Status:** Accepted
- **Phase / ticket:** P21.7 — Contribution-back live (MapRoulette, OSM changeset feed, Organised Editing record, usability study)
- **Date:** 2026
- **Related / amends:** ADR-055 (**amended** — no direct automated OSM writes; the
  human-mediated suggestion workflow, the changeset hashtag, the Organised Editing
  activity page), ADR-065 (`HttpxTransport` / the gated live-run posture), ADR-066
  (the export-backed web data layer `web/src/lib/data.ts`, `SIG_DATA_SOURCE`),
  ADR-054 (the contributor system); LD-F11, LD-P03, LD-P04, LD-F10 (usability half);
  RISK-P16-13/14/15, RISK-P21-12/13; SIG-CONTRIB-014/015/015a/015b/016d/016e/016f/016g/017/017a/018/020,
  SIG-CONTRIB-003, SIG-INGEST-037, SIG-UI-001, the P16.1 AC7 usability ids.

## Gate status (copied from the run contract)

- **HG-08 (accounts): NOT provided → dry-run/stub.** No `SIG_MAPROULETTE_API_KEY`,
  no `SIG_OSM_OE_PAGE`. `sig-tasks maproulette push|pull` run in **dry-run** (JSON of
  the payloads; no live MapRoulette call). The OSM changeset feed runs over recorded
  fixtures (`tests/tasks/fixtures/osm_changesets_*.xml`) — **no live OSM poll** this
  run. The OE page URL is a placeholder; `registered=false` in `ops/config.toml`
  (`[tasks.contribution]`) → a test asserts a challenge push is **REFUSED** (exit 3)
  while `registered=false`. Recorded **gate-pending HG-08** → RETURN PASS.
- **HG-10 (usability study): SKIP — protocol only (not yet run).** The runnable
  protocol (`docs/governance/contributor-onboarding-usability-study.md`) and the
  opt-in, **aggregate-only** timing instrumentation on the L0 form land;
  `docs/build/USABILITY_STUDY.md` results = "not yet run — gate pending HG-10".
  Recorded gate-pending HG-10 → RETURN PASS.

## Context

ADR-055 (P16.2) established contribution back as pure, tested logic ahead of the live
edge: the human-mediated suggestion workflow (`tasks.contribution`), the declared
changeset hashtag `#sig_operator_attribution` wired to the §7 leverage metric
(`LeverageLedger`), and the published Organised Editing activity disclosure. What it
deferred (LD-F11, RISK-P16-14/15) was the **live** edge: a real MapRoulette client, a
real OSM changeset feed populating the ledger, and the §7 metric page reading real
data. This ADR records the design of that edge, built under HG-08's dry-run condition.

Three constraints dominate. First, **SIG performs no automated OSM writes, ever**
(SIG-CONTRIB-014): the live edge may create a *challenge of proposals* and *read* the
public changeset feed, but never applies an edit. Second, **Part VIII §0.7 is
binding**: SIG must store no OSM user data beyond the public changeset id, and the
usability instrumentation must be aggregate-only. Third, **no synthetic certainty**
(§3.1): a call SIG cannot make without HG-08 must be a recorded refusal or a dry-run,
never a fabricated success.

## Decision

1. **MapRoulette client (`tasks/src/tasks/maproulette.py`).** A challenge is built
   from a task selection as a `cooperativeType=tags` payload matching MapRoulette API
   v2 shapes (each task a `modifyElement` operation from
   `tasks.contribution.cooperative_task_payload`, with a point geometry). The
   `checkinComment` carries both the changeset hashtag (the metric reads it) and a
   per-jurisdiction challenge hashtag `#sig-<jurisdiction>` (§35). **Sensitive tiers
   are never pushed (RISK-P21-12):** a task whose sensitivity class publishes no
   geometry (`geo_tier >= 3` — C3/C4/C5, §43.3) is excluded from the payload,
   contributing only to an `excluded_sensitive_task_count`. Without
   `SIG_MAPROULETTE_API_KEY` the client is **dry-run** (returns the payload/endpoint,
   no network); a live call needs the key **and** an injected transport, and refuses
   rather than silently no-op'ing if the transport is absent.
2. **Registration gate (`ops/config.toml` `[tasks.contribution] registered`).**
   `tasks.contribution.contribution_registered()` reads the flag and **fails closed**.
   `MapRouletteClient.push` raises `ChallengeNotRegisteredError` while it is `false`;
   `sig-tasks maproulette push` maps that to **exit 3** with the OE-registration
   reason (RISK-P16-14). The shipped config is `registered=false` (HG-08).
3. **OSM changeset feed (`tasks/src/tasks/osm_feed.py`).** Parses the public
   changeset-API XML and reads **only** the changeset id, its `comment` tag, and
   whether it is closed — **never `user`/`uid`** (Part VIII §0.7); the stored
   `UpstreamChangeset` has no field for a display name, so one cannot be persisted
   even by accident. Hashtag-bearing changesets are folded into a `LeverageLedger`
   (append-only, idempotent by id → re-run adds 0). The CLI replays committed
   fixtures by default (no live poll); `build_feed_url` constructs the public URL a
   live poll *would* fetch, without egress.
4. **§7 metric page (`web/src/pages/contribution-back.astro`).** Reads the metric
   through `web/src/lib/data.ts` `getLeverageMetric()` — `fixtures` mode from the
   committed `leverage-fixture.ts`, `export` mode from `<exportDir>/web/leverage.json`
   (emitted by `sig-tasks osm-feed pull --out`), failing loud if absent (never a
   silent fixtures fall-back — ADR-066's posture). The page publishes the accepted
   count, the auditable hashtag, and the attributed changeset ids (linked, id-only) as
   a **task outcome, not a ranking** (SIG-CONTRIB-016g/020).
5. **Usability: aggregate-only timing (`tasks.onboarding.OnboardingTimingAggregate`
   + the L0 form).** Opt-in timing on `POST /v1/curation/submission` folds one
   elapsed-minutes measurement into a **bucketed histogram** (count + median only) —
   never a per-user row, never written to the append-only submission row, no identity
   (Part VIII §0.7). The moderated protocol and the ≤10-minute median success
   criterion (P16.1 AC7) are documented; the study is **not yet run** (HG-10).

## Consequences

- Contribution back has a real, tested edge that is **safe by construction** without
  HG-08: a push refuses while unregistered, a keyless client is dry-run, the feed
  replays fixtures, and sensitive coordinates are filtered before any payload exists.
- The §7 metric is now sourced from the (replayed) changeset feed rather than a hand
  fixture, and the web page reads it through the same `data.ts` seam as every other
  page — a source swap, not a component change (RISK-P16-15 discharged in shape).
- Flipping `registered=true`, providing the key + `SIG_OSM_OE_PAGE`, and scheduling
  ≥5 naïve participants (HG-08/HG-10) turns the dry-runs into real pushes/pulls and
  the protocol into a completed study — no code change required. Until then the two
  gates are recorded **gate-pending**, not faked.
- **No automated OSM edits are introduced** (SIG-CONTRIB-014 holds); the only OSM
  network verbs are a human-authorised challenge *create* and a public feed *read*.

## Revisit trigger

Revisit when **HG-08 clears** (a real MapRoulette/OSM account + the OSMF activities
registration): flipping `ops/config.toml [tasks.contribution] registered=true`,
providing `SIG_MAPROULETTE_API_KEY` + `SIG_OSM_OE_PAGE`, and running the first live
push/pull replaces the dry-runs — record the challenge id and the first live pull in
`docs/build/CONTRIBUTION_BACK_LIVE.md`. Revisit also when **HG-10 clears** (≥5 naïve
participants scheduled): run the moderated study, record the real `n`/median in
`docs/build/USABILITY_STUDY.md`, and log any onboarding change made from the findings.
Finally, revisit if MapRoulette changes its cooperative-challenge API v2 shapes
(`MAPROULETTE_FIELD_CROSSWALK` / `build_challenge_payload`) or OSM changes the
changeset-API XML, or if the sensitive-tier floor (`SENSITIVE_GEO_TIER_FLOOR`) must
move because the §43.3 class→geo-tier matrix changes.
