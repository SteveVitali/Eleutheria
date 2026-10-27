# P36.76 leg-B packet — the operator's first-wire act (OP-26), staged, never performed

*Agent-drafted packet (OM-09 — labelled, never proxied). Prepared
2026-10-27T05:01Z (`date -u`). Status: `prepared_not_executed` — leg B is the
operator's act; nothing in this packet was performed.*

## What leg B is

The first real host's wire/fetch of the `axon_connect` connector as a
connector run — i.e. the first time `sig-connectors run --source axon_connect
--mode live` (or a subset of its committed targets) egresses to a committed
I9a-C003 host under a flipped source row. Everything before leg B — leg A's
queued screen/page GETs — is separately covered by `leg-a-queue.toml`; leg B
is the act of letting the connector run live at all.

## Preconditions (all must hold; the leg refuses otherwise)

1. **HG-03 rights line answered** — the operator flips
   `ingestion_permitted` on `[sources.axon_connect]` (currently `false`;
   rights `UNDETERMINED`, `redistributable=false`, `review_needed=true`).
   The row's `rights.publication_basis` records the GATE-G5 leg-A naming;
   the flip needs the operator's rights decision line for the
   `Connect <Place>` template's own terms (Axon's public terms prohibit
   automated access — the posture stays `public_terms_only`; the flip is a
   considered acceptance, not a discovered permission).
2. **OP-26 authorisation** — the operator names the run window (the ticket's
   live window cell: `AR-3 + AR-2 + AR-1c` — bounded GETs, backup first).
3. **`live:P35.38a` holds** — `https://surveillancegraph.org/data-collection/`
   serves 200 (it returned 404 at the 2026-10-27T05:01Z probe — recorded in
   `leg-a-queue.toml`); a descriptive UA may not cite a dead owned page
   (SIG-INGEST-036).
4. **Head green** — the stacked branch's head carries all five required
   checks green (CI-2).

## The act (verbatim command surface)

```
# After the flip commit lands on the stack tip and the window opens:
uv run python -m connectors run --source axon_connect --mode live \
    --capture-dir .sig/captures
```

What a leg-B run does — and nothing more:

- `discover()` lists exactly the 12 committed targets (two per site —
  registration page + `:8443/faststream/login.html`); a binding outside the
  committed inventory refuses loud.
- One polite GET per target through the shared fetcher: opt-out register
  first (zero egress on a listed host/site), robots recorded under
  GL-GATE-08, rate-limited, declared backoff.
- Any 401/403/429 or 2xx bot-management interstitial ends the target's
  attempt — recorded as `access_restricted`, never defeated.
- Persisted bytes are ONLY the screened `sig.axon-connect-page/1` /
  `sig.fusus-screen/1` records — the served page's bytes are never stored;
  a registrant-byte field anywhere in an embedded payload refuses the page
  whole before persistence (`ScreenedRefusal`, counts-only detail).
- Emitted claims are the allowlisted programme facts
  (`camera_registration_portal`, `camera_registry_publisher`,
  `agency_name`, `portal_stated_prohibited_use`) plus the bounded
  `acquisition_candidate` row per marked host — never a feed.

## What leg B must never do

- No second GET of the same URL in a run; no retry on a challenge.
- No credentials, no login attempt on the `:8443` screens (the screen is
  evidence-only: markers + status + hash).
- No registrant bytes, names, addresses, emails, phones, camera-level
  records (R11-A16 — refused by construction, tested).
- No proxy rotation, header spoofing, browser automation, challenge-solving
  (SIG-INGEST-013/037 — a test audits the module source).

## Re-run prompt (OM-19 — recorded verbatim from the ticket)

```
implement-spec spec=docs/tickets/351_P36.76__axon-connect-connector.md live_verification=true
```

resumes at leg A (the queued GETs) and stages leg B for the operator.

## Go lines (operator fills; agent drafted the form only)

- [ ] `HG-03:` the rights decision line for `axon_connect` (date, decider,
  licence/compact basis) — *blank: operator's words.*
- [ ] `OP-26:` the window + first-host authorisation — *blank: operator's
  words.*
