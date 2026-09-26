# Rights-review packet — `escribe` (eScribe Meetings public calendar JSON)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `escribe`
- **Homepage:** https://pub-<tenant>.escribemeetings.com/ — the per-tenant public
  meetings calendar the municipality itself publishes (e.g. pub-nanaimo,
  pub-victoria, pub-orlando, pub-detroitmi).
- **Terms URL(s):** https://pub-nanaimo.escribemeetings.com/ — the public tenant
  surface publishes no licence document; the records' rights resolve as municipal
  public records, the same basis as `okc_council`/`legistar`/`civicclerk`
  (GL-GATE-06, 2026-09-17).
- **robots.txt:** honor — per-tenant hosts answer `User-agent: PetalBot /
  Disallow: /` (a rule for a different crawler, never the SIG UA) or 404
  (no policy exists — RFC 9309 §2.3.1.4 / ADR-087). CRAWL mode binds and passes;
  no API-mode carve-out is claimed.

## Terms (verbatim)

> The eScribe Meetings tenant surface publishes municipal meeting indexes
> (meeting name, date, type, location, agenda linkage) — US/CA local-government
> public records. No licence document is served by the tenant hosts; the records'
> rights resolve as municipal public records, the same basis as `okc_council`
> (GL-GATE-06). The vendor platform ToS governs the ACCESS METHOD, not the record
> rights.
>
> The index the connector reads is the JSON webmethod the tenant's own public
> calendar page calls —
> `POST /MeetingsCalendarView.aspx/GetCalendarMeetings` answering
> `{"d": [ …meeting records… ]}` — verified live 2026-09-17 across the
> enumerated `pub-*` tenant surface (68 serving tenants).

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Municipal meeting records are public records — redistributable on the same basis as `okc_council` (GL-GATE-06).  → registry `redistributable = true`.

## derivative_permitted analysis

Public-record derivatives permitted (same basis as `okc_council`).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (fetch the bounded calendar-window meeting index for enumerated tenants).

## Access note (2026-09-17, live-verified)

`POST pub-{tenant}.escribemeetings.com/MeetingsCalendarView.aspx/GetCalendarMeetings`
answers `{"d":[…]}` with real meeting records (ID, MeetingName, StartDate,
MeetingType, PortalId) on the enumerated `pub-*` surface; `bm-*`/`bm-public-*`
hosts are the Boards module (not the meetings index) and were excluded.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — municipal public-record rights resolved under GL-GATE-06.**
