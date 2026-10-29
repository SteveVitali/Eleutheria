# P36.77 leg-B packet — the operator's first-wire act (OP-26), staged, never performed

*Agent-drafted packet (OM-09 — labelled, never proxied). Prepared
2026-10-27T08:17Z (`date -u`). Status: `prepared_not_executed` — leg B is the
operator's act; nothing in this packet was performed.*

## What leg B is

The first real host's wire/fetch of the `documentcloud` connector as a
connector run — i.e. the first time `sig-connectors run --source
documentcloud` (or `--source muckrock_public`) would egress to a committed
seed under a flipped source row — never performed here. Everything before
leg B — leg A's queued rendition/terms GETs and the registry-row appends —
is separately covered by `leg-a-queue.toml`; leg B is nothing more than the
act of letting the connector run at all, and no such run happened.

## Preconditions (all must hold; the leg refuses otherwise)

1. **HG-03 rights line answered** — the operator flips
   `ingestion_permitted` on `[sources.documentcloud]` (currently absent →
   `false`) and on `[sources.muckrock_public]` (currently `false`). Both
   rows stay gated: DocumentCloud's rights are UNDETERMINED and its own
   review packet records the MuckRock ToS expressly excluding "data mining,
   robots, or similar data gathering and extraction tools" — the flip is a
   considered acceptance, not a discovered permission (D-SOURCES.2-2 stays
   OPEN until the operator's line).
2. **OP-26 authorisation** — the operator names the run window (the ticket's
   live-window cell `AR-3 + AR-2 + AR-1c` (bounded GETs, backup first, none
   run without that naming)). GATE-G5 granted ING-GO-C only — ING-GO-D was
   never granted, so any activated cadence binds on a further operator
   decision.
3. **`live:P35.38a` holds** — `https://surveillancegraph.org/data-collection/`
   serves 200 (it returned 404 at the 2026-10-27T07:54:48Z probe — recorded
   in `leg-a-queue.toml`); a descriptive UA may not cite a dead owned page
   (SIG-INGEST-036).
4. **Head green** — the stacked branch's head carries all five required
   checks green (CI-2).

## The act (verbatim command surface)

```
# After the flip commit lands on the stack tip and the window opens —
# never without the operator's OP-26 go:
uv run python -m connectors run --source documentcloud --mode live \  # staged — never run by the agent
    --capture-dir .sig/captures
uv run python -m connectors run --source muckrock_public --mode live \  # staged — never run by the agent
    --capture-dir .sig/captures
```

What a leg-B run does — and nothing more:

- `discover()` lists exactly the committed seeds for the source (10
  `documentcloud` rows + 1 `muckrock_public` row in
  `data/documentcloud_targets.toml`); a binding outside the committed
  inventory refuses loud.
- One polite GET per target through the shared fetcher: opt-out register
  first (zero egress on a listed host/target), robots recorded under
  GL-GATE-08 (api.www.documentcloud.org's `Disallow:/` is a recorded
  disregard, never a silent bypass), rate-limited, declared backoff.
- Any 401/403/429 or 2xx bot-management interstitial ends the target's
  attempt — recorded as `access_restricted`, never defeated.
- Persisted bytes are ONLY the screened records: `sig.documentcloud-
  rendition/1` (allowlisted fields + `redacted_fields` name+classes+hash +
  `refused_fields` names + uploader page URL + original sha256),
  `sig.documentcloud-terms/1` (verbatim bounded terms + digest), or
  `sig.documentcloud-refusal/1` (pointer + counts + hash — never raw
  bytes). The served page's own bytes are never stored; a rendition that
  cannot screen clean is the recorded refusal.
- Emitted claims are the allowlisted index linkage only
  (`released_documents`, `platform`, `acquisition_method`, `title`) — every
  row carries `uploader_page` — plus `document_index`/`collection_index`,
  `evidence_artifact` (integrity `screened_rendition`), `terms_capture`,
  `capture_refusal` and `quality_report` rows. No entity resolution, no
  request minting (SIG-INGEST-034).

## What leg B must never do

- No second GET of the same URL in a run; no retry on a challenge.
- No credentials, no api_v2 token path, no login (the `muckrock` api_v2
  source is the `records` connector's own gated lane — untouched).
- No person-name/description verbatim carriage: `contributor`, `author`,
  `description`, `source` fields redact in memory (name + classes + value
  sha256 only); plate/address/contact/officer/registrant field names refuse.
- No proxy rotation, header spoofing, browser automation, challenge-solving
  (SIG-INGEST-013/037 — a test audits the module source).
- No document *bytes*: pdf/full_text/asset URLs are recorded as pointers —
  the document's own binary is never fetched (the rendition lane's bound).

## Re-run prompt (OM-19 — recorded verbatim from the ticket)

```
implement-spec spec=docs/tickets/352_P36.77__documentcloud-muckrock-connector.md live_verification=true
```

resumes at leg A (the queued GETs) and stages leg B for the operator.

## Go lines (operator fills; agent drafted the form only)

- [ ] `HG-03:` the rights decision lines for `documentcloud` +
  `muckrock_public` (date, decider, licence/compact basis) — *blank:
  operator's words.*
- [ ] `OP-26:` the window + first-host authorisation — *blank: operator's
  words.*
