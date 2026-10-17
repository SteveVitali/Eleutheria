# Rights-review packet — `natural_earth_10m` (SIG-LIC-001, P21.1; P35.17 / D-K4-1 [A-18])

> Packet convention (`_TEMPLATE.md`): **facts** (quoted terms + retrieval date) are
> laid out separately from **judgement** (the reviewer decision line, left
> unchecked — the HG-03 flip is the operator's act, OP-26). Reading the published
> terms page is permitted research, **not** ingestion; no source *content* (no
> shapefile) was fetched and nobody was contacted (U-011, ADR-171 Decision 3).

- **Source id:** `natural_earth_10m`
- **Homepage:** <https://www.naturalearthdata.com/>
- **Terms URL(s) fetched:** <https://www.naturalearthdata.com/about/terms-of-use/> —
  retrieved 2026-10-17 (HTTP 200; 38,013 bytes of HTML; the session `date -u` bounds are
  2026-10-17T07:24–07:31Z — the commit's committer time is the landing stamp).
- **robots.txt:** honor — single published page read, no crawl.

## Terms (verbatim)

From the terms-of-use page body (verbatim):

> All versions of Natural Earth raster + vector map data found on this website are in the
> public domain. You may use the maps in any manner, including modifying the content and
> design, electronic dissemination, and offset printing. The primary authors, Tom Patterson
> and Nathaniel Vaughn Kelso, and all other contributors renounce all financial claim to the
> maps and invites you to use them for personal, educational, and commercial purposes. No
> permission is needed to use Natural Earth. Crediting the authors is unnecessary. However,
> if you wish to cite the map data, simply use one of the following.
>
> Short text: Made with Natural Earth.
> Long text: Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
>
> All users of Natural Earth are highly encouraged to read about data sources and
> manipulation in the Data Creation section. The authors provide Natural Earth as a public
> service and are not responsible for any problems relating to accuracy, content, design,
> and how it is used. If you find an error or omission, please report it for future updates.

The same page records the upstream-data releases SIG inherits (verbatim excerpts): The
Washington Post, the European Commission JRC IES (European rivers/lakes), XNR Productions
(North-American roads), and International Mapping Associates (time zones) each grant
Natural Earth "a non-exclusive license to use the data being provided by … for the sole
purpose of creating a world base map", each disclaiming warranty and responsibility.

## SPDX candidate

`CC0-1.0` (accepted expression per `policy/data/licenses.toml`) — the published terms are an
express public-domain dedication with no licence conditions. Candidate, not a landed flip.

## redistributable analysis

"You may use the maps in any manner, including … electronic dissemination" — redistribution
is expressly free of permission and even of credit ("Crediting the authors is unnecessary").
SIG still attributes ("Made with Natural Earth" citation string is carried on the
`jurisdictions` registry artifact), because the defining standard wants provenance shown.

## derivative_permitted analysis

"including modifying the content and design" — derivatives expressly permitted. No
SIG-INGEST-048b linking hazard: public `.zip` downloads, no login, no key.

## ODbL compartment implications

Not OSM-derived (K4 §4.1 rejects OSM admin boundaries precisely to keep the ODbL
derivative-database question out of placement).

## Custody posture recommendation

MIRROR (§8.4) — the 10m admin-0/admin-1 shapefiles are captured into OCFL once the operator
flips `ingestion_permitted`; the GeoParquet pack is a derived artifact.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____ *(unchecked — the HG-03 flip is the
  operator's act (OP-26); this ticket pauses for it and never performs it)*

## Counsel-needed flag

NO — an express public-domain dedication on the publisher's own terms page.
(SIG-LIC-009 stands: a reviewer role is not a legal opinion.)
