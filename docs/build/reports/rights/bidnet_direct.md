# Rights-review packet — `bidnet_direct` (BidNet Direct — public agency bid portal)

> P26.2 skeleton → P26.10 (SOURCES.9) probe update 2026-09-18. Facts are separated
> from judgement; this packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `bidnet_direct`
- **Homepage:** https://www.bidnetdirect.com/
- **Terms URL(s) fetched:** still not captured verbatim — see Counsel-needed flag (D-SOURCES.9-4)
- **robots.txt:** honor — fetched verbatim 2026-09-18 (HTTP 200), quoted below

## Access posture (verified 2026-09-18, SIG `procurement/1.0.0` UA)

Agency storefronts are PATHS under `www.bidnetdirect.com`
(`/<purchasing-group>/<agency>/`): each serves its own
`solicitations/{open,closed,awarded}-bids` index pages (server-rendered
`mets-table-row` items) plus public detail pages carrying the verbatim
solicitation text — all without a login wall. The portal's own public
`?keywords=` field filters each index server-side. robots.txt verbatim (head):

> ```
> User-agent: *
> # --- Authenticated areas (blocked) ---
> Disallow: /private/
> Disallow: /favorites
> # --- Public pages that are NOT indexable ---
> Disallow: /public/registration/
> Disallow: /public/authentication/
> Disallow: /public/info
> Disallow: /public/supplier/services/
> Disallow: /public/monitoring
> Disallow: /public/sendgrid/
> Disallow: /public/dev-tools/
> Disallow: /dev-tools/
> Disallow: /ws/
> Disallow: /jawr/
> Disallow: /login
> Disallow: /logout
> Disallow: /saml/
> # --- Query-string traps ---
> Disallow: /*?*sort=
> Disallow: /*?*page=
> Disallow: /*?*pageSize=
> Disallow: /*?*jsessionid=
> Crawl-delay: 5
> Sitemap: https://www.bidnetdirect.com/sitemap.xml
> ```

…followed by a named-bot blocklist (`GPTBot`, `ChatGPT-User`, `OAI-SearchBot`,
`CCBot`, `anthropic-ai`, `ClaudeBot`, `Claude-Web`, `Google-Extended`,
`PerplexityBot`, `Bytespider`, `AhrefsBot`, `SemrushBot`, `MJ12bot`, `DotBot`
— each `Disallow: /`). The SIG `procurement/1.0.0` UA is not named; the
`User-agent: *` group applies. The connector's targets use only allowed paths
(storefront indexes, `?keywords=`, detail pages) — `?page=`/`?pageSize=`/`?sort=`
are disallowed, so index coverage is page-1 + keyword windows by design, never
paginated crawls.

## Terms (verbatim)

> The platform Terms of Service were NOT captured verbatim this pass; the
> reviewer must fetch and quote `https://www.bidnetdirect.com/terms` (or the
> current terms URL) before any flip. Unlike the Socrata datasets there is no
> per-record licence field, so the GL-GATE-06 "municipal public records → CC0"
> basis needs the vendor-platform terms evaluated first (aggregation platform
> republishing agency solicitations — the record publisher is the agency, the
> surface is the vendor's). This packet makes no licence assertion.

## SPDX candidate

`UNDETERMINED`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Unreviewed — `redistributable = false` until a reviewer resolves the terms.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until a reviewer resolves the terms.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — a multi-tenant vendor portal republishing agency solicitations
(records/procurement surface). Tenant rows live in
`connectors/src/connectors/data/procurement_portal_tenants.toml`.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `UNDETERMINED`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

PENDING REVIEW (D-SOURCES.9-4) — the access posture is verified and robots is
honourable, but the vendor ToS is uncaptured; the source stays
`ingestion_permitted=false` until the terms are reviewed (HG-03 class).
