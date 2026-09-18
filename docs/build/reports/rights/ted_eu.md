# Rights-review packet — `ted_eu` (TED — Tenders Electronic Daily)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* beyond the legal
> notice and the documented Search API contract probes was fetched.

- **Source id:** `ted_eu`
- **Homepage:** https://ted.europa.eu/
- **Terms URL(s) fetched:** https://ted.europa.eu/en/legal-notice — retrieved 2026-09-18
- **API documentation:** https://docs.ted.europa.eu/api/latest/search.html — retrieved 2026-09-18
- **robots.txt:** not_applicable — `api.ted.europa.eu/robots.txt` answers HTTP 404 (no
  policy exists, RFC 9309 §2.3.1.4); the host is ADR-083 API-mode allow-listed
  (`api_allowlist.toml` — POST `/v3/notices/search`, the documented public Search API).

## Terms (verbatim)

> Fetched from https://ted.europa.eu/en/legal-notice on 2026-09-18 (the SIMAP legal
> notice — permitted research):
>
> "The European Commission's reuse policy is implemented by the Commission Decision of
> 12 December 2011 on the reuse of Commission documents. **Unless otherwise noted, the
> procurement notices published in the Supplement to the Official Journal of the
> European Union can be freely reused, for commercial or non-commercial purposes.**"
>
> "The copyright over the editorial content of the SIMAP websites (TED, TED eNotices2,
> TED Developer Docs and TED Developer Portal) is licensed under the Creative Commons
> Attribution 4.0 International (CC BY 4.0) license. This means that reuse is allowed
> provided appropriate credit is given and any changes made are indicated."
>
> "The SIMAP's system metadata is dedicated to the public domain in accordance with the
> Creative Commons Universal Public Domain Dedication deed (CC0 1.0)."

> From https://docs.ted.europa.eu/api/latest/search.html (retrieved 2026-09-18), the
> Search API is the documented public programmatic surface: the API "does not require
> authentication". The published fair-usage limits are 700 HTTP requests/minute and 600
> notice views/downloads per 6 minutes per IP — SIG's reviewed budget is 30
> requests/minute, far inside the published limit.

The Search API returns the procurement-notice fields of OJ S notices — the class of
content the legal notice states "can be freely reused, for commercial or
non-commercial purposes". SIG stores verbatim literals + locators as claims, not the
SIMAP editorial layer; attribution is recorded on the source row
(`rights.attribution` in `sources.toml`).

## SPDX candidate

`CC-BY-4.0` — the SIMAP licence covering the system content layer SIG reads through
the documented API; the OJ S notices themselves carry the broader Commission Decision
2011/833/EU free-reuse grant and the system metadata is CC0-1.0. `CC-BY-4.0` is the
most conservative accepted expression covering all three layers
(`policy/data/licenses.toml`).

## redistributable analysis

Separately reviewed (never derived from the SPDX string — SIG-LIC-003): the legal
notice grants free reuse of the procurement notices "for commercial or
non-commercial purposes" with no territorial or purpose restriction;
`redistributable = true` records that verbatim grant. Attribution is discharged by the
`rights.attribution` string on the source row.

## derivative_permitted analysis

CC BY 4.0 permits derivatives "provided appropriate credit is given and any changes
made are indicated" — SIG's claims are verbatim literals with locators, not
adaptations; no SIG-INGEST-048b linking hazard (notices are fetched as JSON fields,
not linked third-party works). `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived — EU procurement notices; no RISK-P0-01/02 implications.

## Custody posture recommendation

`REFERENCE` (§8.4): verbatim field literals + locators are stored as claims; the
source remains the system of record. `compact_status = public_terms_only`.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC-BY-4.0` · rights_reviewed_by: `maintainer (delegated)` ·
  rights_reviewed_on: 2026-09-18

Flipped under the **GL-GATE-06 delegated blanket disposition** — the same
maintainer-review pattern applied to the P26.2/P26.7/P26.9/P26.10/P26.12/P26.13
cohorts: a public-sector source whose published legal terms resolve clear (here an
express free-reuse grant + CC-BY-4.0 + CC0-1.0 layers) is flipped by the delegated
reviewer with the verbatim basis recorded in this packet.

## Counsel-needed flag

NO — SIG-LIC-009: the recorded reviewer role is not a legal opinion. The legal
notice's free-reuse sentence is express and unambiguous; no terms ambiguity requires
counsel (unlike the HG-02 LicenseRef cohort, no bespoke licence had to be drafted —
an accepted SPDX expression covers it).
