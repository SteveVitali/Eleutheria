# Rights-review packet — `bonfire` (Bonfire — per-tenant procurement portals, *.bonfirehub.com)

> P26.10 (SOURCES.9) review 2026-09-18. Facts are separated from judgement; this
> packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `bonfire`
- **Homepage:** https://bonfirehub.com/
- **Terms URL(s) fetched:** none — every tenant host refuses all paths (below)
- **robots.txt:** honor — fetched verbatim 2026-09-18 on both verified tenants

## Access posture (verified 2026-09-18, SIG `procurement/1.0.0` UA)

Bonfire (Euna Solutions) serves per-tenant procurement portals on
`*.bonfirehub.com`. The crt.sh certificate set was enumerated
(`data/procurement_portal_tenants.toml` `platform_census`): most names are
vendor infrastructure (account/sso/oauth/zendesk/academy/test/staging hosts),
not agency tenants. Two jurisdiction tenants were verified serving —
`laurier.bonfirehub.com` and `columbus.bonfirehub.com` — each answering
`/portal` with a login redirect that ultimately serves the portal shell.

Both tenants answer `robots.txt` identically, verbatim:

> ```
> User-agent: *
> Disallow: /
> ```

A platform-wide refusal of every path. The shared politeness layer records a
robots refusal for any fetch; the wall stands until it changes or a separately
reviewed API-mode basis exists. It is never bypassed.

## Terms (verbatim)

> No terms document was reachable — the robots wall refuses every path. This
> packet makes no assertion about the licence (defining standard §3.1 — no
> synthetic certainty).

## SPDX candidate

`UNDETERMINED`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Unreviewed — `redistributable = false` until a reviewer resolves the terms.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until a reviewer resolves the terms.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — a per-tenant procurement portal platform (records/procurement surface),
currently robots-walled platform-wide.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `UNDETERMINED`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

PENDING REVIEW (D-SOURCES.9-2) — gated twice over: (1) `Disallow: /` refuses
every path on every verified tenant, and (2) no terms were reachable to review.
The source stays `ingestion_permitted=false`; the registered tenant rows exist
so each host's refusal is recorded honestly per run.

## Posture note — P37.6 (2026-11-06)

This packet's access posture was recorded 2026-09-18, before **GL-GATE-08 /
ADR-088 / ADR-222**: the `Disallow: /` above is a *declared* robots posture —
probed and recorded per RFC 9309, and **never a fetch gate** under the current
posture (a disregarded disallow would proceed, stamped `robots_disregarded`
and disclosed). What still gates `bonfire` is unchanged and is the row's real
blocker set: (1) terms were never captured verbatim — rights remain
`UNDETERMINED`; (2) `compact_status` / `custody_posture` are unsatisfied
(`not_contacted` + `LINK`); (3) no reviewed markup contract exists — a
captured body is `ContentDrift` by construction; and (4) `/portal` answers a
login redirect on both verified tenants. D-SOURCES.9-2 was closed WONTFIX
2026-10-02 (P34.8 transition `PT-003`); the 2026-09-18 record above stands as
the access-posture capture of that day.
