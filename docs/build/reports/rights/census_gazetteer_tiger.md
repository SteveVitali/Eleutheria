# Rights-review packet — `census_gazetteer_tiger` (SIG-LIC-001, P21.1; P35.17 / D-K4-1 [A-18])

> Packet convention (`_TEMPLATE.md`): **facts** (quoted terms + retrieval date) are
> laid out separately from **judgement** (the reviewer decision line, left
> unchecked — the HG-03 flip is the operator's act, OP-26). Reading a terms or
> technical-documentation page is permitted research, **not** ingestion; no
> source *content* (no boundary dataset) was fetched. The terms read is a read
> of published text; nobody was contacted (U-011, ADR-171 Decision 3).

- **Source id:** `census_gazetteer_tiger`
- **Homepage:** <https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html>
- **Terms URL(s) fetched:** <https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc_Ch1.pdf> —
  retrieved 2026-10-17 (`date -u` 2026-10-17T07:24:13Z at fetch; HTTP 200; 150,512 bytes;
  sha256 `ce40bee768cdb00f9dadc154ca0b1dc6ca91180c1b9362e5d2b70cbea2d75003` of the downloaded
  bytes — the byte-identical "TIGER/Line Shapefiles — 2025 Technical Documentation, Chapter 1:
  Legal Disclaimer, Citation Information and Contact" chapter the Gazetteer/TIGER download pages cite).
  The general policy page <https://www.census.gov/about/policies/terms.html> and the Census **API**
  terms <https://www.census.gov/data/developers/about/terms-of-service.html> were also read; the API
  terms govern `api.census.gov` keys, not file downloads — recorded here so the terms basis is not
  confused (the technical document carries the TIGER/Line + Gazetteer usage text).
- **robots.txt:** honor — the read was manual-page + document fetch under the published path; no
  crawl, no API key.

## Terms (verbatim)

From `TGRSHP2025_TechDoc_Ch1.pdf` §1.1 "TIGER/Line Shapefile Legal Disclaimers" (verbatim):

> No warranty, expressed or implied, is made with regard to the accuracy of the data in the
> TIGER/Line Shapefiles, and no liability is assumed by the United States Government in general,
> or the Census Bureau specifically, as to the positional or attribute accuracy of the data. The
> boundary information in the TIGER/Line Shapefiles is for statistical data collection and
> tabulation purposes only. Their depiction and designation for statistical purposes does not
> constitute a determination of jurisdictional authority or rights of ownership or entitlement
> and are not legal land descriptions.
>
> TIGER/Line® is a registered trademark of the Census Bureau. TIGER/Line cannot be used as or
> within the proprietary product names of any commercial product including or otherwise relevant
> to Census Bureau data and may only be used to refer to the nature of such a product. The Census
> Bureau requests that any repackaging of the TIGER/Line Shapefile data, documentation, and other
> files accompanying it for distribution include a conspicuously placed statement to this effect
> on the product's cover, the first page of the website, or elsewhere of comparable visibility.
> Further, Census Bureau trademarks, when used in reference to the nature of the product, should
> be accompanied by the ® (registered) symbol or ™ symbol, where convenient.

And §1.2 "Citation Information" (verbatim):

> Copyright protection is not available for any work of the United States Government (Title 17
> U.S.C., Section 105). Thus, you are free to reproduce census materials as you see fit. We would
> ask, however, that you cite the Census Bureau as the source.

§1.3 (verbatim, for the record — organisational contacts only):

> Members of the public can obtain the TIGER/Line Shapefiles free of charge through the Census
> Bureau's website … Office: (301) 763-1128 · E-mail: geo.geography@census.gov

## SPDX candidate

`CC0-1.0` (accepted expression per `policy/data/licenses.toml`) — the registry precedent for a US
Government work under 17 U.S.C. §105 (`usaspending`, `sam_gov`: "DATA Act federal public-domain
(17 U.S.C. §105) → CC0-1.0"). Candidate, not a landed flip.

## redistributable analysis

A US Government work carries no copyright (17 U.S.C. §105, quoted verbatim above): reproduction is
free; the citation is a *request* ("We would ask, however…"), not a licence condition. Attribution
is still carried in `sources.toml` (`attribution = "U.S. Census Bureau — TIGER/Line and Gazetteer
files"`) and the `jurisdictions` registry export attributes the upstreams. The trademark clause is
a *naming* constraint (don't call a repackaged product "TIGER/Line®"), honoured — the pack/registry
artifacts are named `boundary-pack`/`jurisdictions`, never "TIGER/Line", and show the source
attribution conspicuously per the repackaging request.

## derivative_permitted analysis

§105 basis: derivative products are free to make and distribute; the only express request is
conspicuous attribution of the repackaged content's Census origin (recorded in `notes` and carried
on the `jurisdictions` registry attribution). No SIG-INGEST-048b linking hazard: the file is a
public `.gov` download path, no login, no key.

## ODbL compartment implications

Not OSM-derived — this source feeds the CC-BY-4.0 `jurisdictions` registry metadata (upstreams
attributed), and the boundary pack stays a restricted-export input until the flip.

## Custody posture recommendation

MIRROR (§8.4) — full boundary files are held as captured evidence (OCFL objects) once the operator
flips `ingestion_permitted`; conversion to the GeoParquet pack is a derived artifact, never the
only copy.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____ *(unchecked — the HG-03 flip is the operator's
  act (OP-26); this ticket pauses for it and never performs it)*

## Counsel-needed flag

NO — a statutory public-domain basis (17 U.S.C. §105) quoted verbatim; no ambiguous licence text.
(SIG-LIC-009 stands: a reviewer role is not a legal opinion.)
