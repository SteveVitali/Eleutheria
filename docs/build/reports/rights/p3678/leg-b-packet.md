# P36.78 leg-B packet — the operator's first-wire act (OP-26), staged, never performed

*Agent-drafted packet (OM-09 — labelled, never proxied). Prepared
2026-10-27T11:15Z (`date -u`). Status: `prepared_not_executed` — leg B is the
operator's act; nothing in this packet was performed.*

## What leg B is

The first real host's wire/fetch of the `cooperative` connector as a
connector run — i.e. the first time `sig-connectors run --source
sourcewell` (or `--source omnia_partners`) would egress to a committed
seed under a flipped source row — never performed here. Everything before
leg B — leg A's queued contract-page/terms GETs and the registry-row
amends — is separately covered by `leg-a-queue.toml`; leg B is nothing
more than the act of letting the connector run at all, and no such run
happened.

## Preconditions (all must hold; the leg refuses otherwise)

1. **HG-03 rights line answered** — the operator flips
   `ingestion_permitted` on `[sources.sourcewell]` (currently `false`) and
   on `[sources.omnia_partners]` (currently `false`). Both rows stay
   gated: the rights on both are UNDETERMINED and each platform's captured
   terms expressly prohibit automated extraction — Sourcewell's terms-use
   ("Use automated tools such as robots or spiders to access or copy
   content"), OMNIA's terms-of-use ("you shall not: (a) use any robot,
   spider, or other automatic or manual device or process for the purpose
   of 'scraping,' 'crawling,' harvesting, or compiling information").
   Decision-catalog I7-C3 [B-39] answered the *screen-fetch* question for
   leg A under ADR-184's bounded envelope; the flip that lets the
   connector RUN is a considered acceptance, not a discovered permission.
   custody moved to DERIVE this ticket (`omnia_partners` LINK →
   DERIVE, `sourcewell` REFERENCE → DERIVE — the lane persists
   screened renditions; LINK could never admit it and REFERENCE
   overstated the served-byte holding); the
   flip remains the operator's act.
2. **OP-26 authorisation** — the operator names the run window — the
   ticket's `AR-3 + AR-2 + AR-1c` window cell (bounded GETs, backup
   first, none run without that naming). GATE-G5 granted ING-GO-C only —
   ING-GO-D was never granted, so any activated cadence binds on a
   further operator decision (queues per OM-19).
3. **`live:P35.38a` holds** — `https://surveillancegraph.org/data-collection/`
   serves 200 (it returned 404 at the 2026-10-27T11:10:24Z probe —
   recorded in `leg-a-queue.toml`); a descriptive UA may not cite a dead
   owned page (SIG-INGEST-036).
4. **Head green** — the stacked branch's head carries all required checks
   green (CI-2).

## The act (verbatim command surface)

```
# After the flip commit lands on the stack tip and the window opens —
# never without the operator's OP-26 go:
uv run python -m connectors run --source sourcewell --mode live \  # staged — never run by the agent
    --capture-dir .sig/captures
uv run python -m connectors run --source omnia_partners --mode live \  # staged — never run by the agent
    --capture-dir .sig/captures
```

What a leg-B run does — and nothing more:

- `discover()` lists exactly the committed seeds for the source (2
  `sourcewell` rows + 3 `omnia_partners` rows in
  `data/cooperative_targets.toml`); a binding outside the committed
  inventory refuses loud.
- One polite GET per target through the shared fetcher: opt-out register
  first (zero egress on a listed host/target), robots recorded under
  GL-GATE-08 (the I6 read recorded Sourcewell's robots.txt 200 — a
  recorded verdict is never a silent bypass), rate-limited, declared
  backoff.
- Any 401/403/429 or 2xx bot-management interstitial ends the target's
  attempt — recorded as `access_restricted`, never defeated.
- Persisted bytes are ONLY the screened records:
  `sig.cooperative-rendition/1` (allowlisted fields + `redacted_fields`
  name+classes+hash + `refused_fields` names + contract-page URL +
  original sha256 + linked-document COUNT — member-gated documents are
  pointers, never fetched), `sig.cooperative-terms/1` (verbatim bounded
  terms + digest), or `sig.cooperative-refusal/1` (pointer + counts +
  hash — never raw bytes). The served page's own bytes are never stored;
  a rendition that cannot screen clean is the recorded refusal.
- Emitted claims are the allowlisted linkage only (`contract`,
  `contract_number`, `external_id`, `document`, `platform`,
  `acquisition_method`, `title` + the artifact row's
  `released_documents`) — every row carries `contract_page` — plus
  `contract_index`/`page_index`, `evidence_artifact` (integrity
  `screened_rendition`), `terms_capture`, `capture_refusal` and
  `quality_report` rows. No entity resolution — the contract subject is a
  candidate (`contract:sourcewell:101223-AXN`), never a party or
  piggyback linkage (SIG-INGEST-034).

## What leg B must never do

- No second GET of the same URL in a run; no retry on a challenge.
- No credentials, no member form submission, no login (the
  contract-documents files route through a member form — pointers only;
  `documents_member_gated` is recorded, never submitted).
- No person-name/description verbatim carriage: `contact_name`, `author`,
  `description`, `notes` fields redact in memory (name + classes + value
  sha256 only); plate/address/contact/officer/registrant field names
  refuse.
- No proxy rotation, header spoofing, browser automation, challenge-solving
  (SIG-INGEST-013/037 — a test audits the module source).
- No document *bytes*: linked PDF/XLSX URLs are counted pointers — the
  document's own binary is never fetched (the rendition lane's bound).

## Re-run prompt (OM-19 — recorded verbatim from the ticket)

```
implement-spec spec=docs/tickets/353_P36.78__sourcewell-omnia-contract-pages.md live_verification=true
```

resumes at leg A (the queued GETs) and stages leg B for the operator.

## Go lines (operator fills; agent drafted the form only)

- [ ] `HG-03:` the rights decision lines for `sourcewell` +
  `omnia_partners` (date, decider, licence/compact basis) — *blank:
  operator's words.*
- [ ] `OP-26:` the window + first-host authorisation — *blank: operator's
  words.*
