# ADR-106 — Share-alike compartments go public as separate, attributed compartments; mixed-licence artifacts never do

- **Status:** Accepted
- **Supersedes:** ADR-096 **§Decision 1 only** (the classifier rule "a compartment is public iff its licence is non-`share_alike` …"). ADR-096 §Decision 2 (partition → prove-clean guard before any sync) and §Decision 3 (the public build reads the real national export or fails loud) stand unchanged.
- **Phase / ticket:** Phase 30 / P30.3 (`docs/tickets/P30.3__national-export-and-public-cutover.md`) — Round 8 `GO-LIVE.3`, the national export + public cut-over; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** §42 / §42.3 (SIG-LIC-004a/005/006 — the ODbL posture; SIG-EXPORT-005/006 — compartments never merged, per-row rights provenance), §38 (export bundles), §39.3 / SIG-GEO-013 (OSM attribution in every rendering context), ADR-048 (ODbL tiles keep their attribution), ADR-090/092 (the spine-built national surface), ADR-096 (the superseded classifier), ADR-097 (the map island), ADR-098 (the domain LB), ADR-105 (the resolved-site metric the launch publishes); gate answers LEDGER § GATE DECISIONS **2026-09-23** (HG-11 launch go + binding safety framing) and **2026-09-24** (share-alike layers: *"counsel says it's okay and we can publish it all together."*); deferrals **D-P30.3-COUNSEL** (written opinion owed — stays OPEN), **D-LEGAL.1-1**; backlog home **BL-056**.

## Context

ADR-096 classified every share-alike compartment (ODbL-1.0 `osm_physical`, the CC-BY-SA layers) as
RESTRICTED at the national cut-over, pending a dated counsel ODbL 4.4(b) opinion — its revisit trigger.
At the national launch that rule would have kept the majority of the graph private: the settled launch
baseline (`LAUNCH_BASELINE_2026-09-24.md` §3) has 1,220,651 ODbL claims (all of OpenStreetMap, ~154k
camera sites) and 58,634 CC-BY-SA claims, and — because `compute_export_license` places CC0 rows under
their most-constraining relicensable target (`CC-BY-SA-4.0`) — the CC0 DOT camera feeds too.

On 2026-09-24 the operator answered the ADR-096 revisit: *"counsel says it's okay and we can publish it
all together."* The clearance is **operator-reported**; no dated written opinion is on file (tracked as
`D-P30.3-COUNSEL`, OPEN). The 2026-09-16 operator-adopted drafted analysis
(`docs/governance/publication-opinion-drafts.md`, D-LEGAL.1-1) already concluded publication is
permitted **via compartment separation**. "Together" admits two readings with very different legal
consequences:

- **One combined downloadable database** (ODbL merged into the CC-BY graph) — under ODbL 4.4(a) the
  whole combined database becomes an ODbL Derivative Database, relicensing SIG's own CC-BY graph, and it
  breaches the gated ODbL-compartment-separation invariant (SIG-EXPORT-005). Not authorized by the answer.
- **One public site drawing on every layer** — the rendered website/map is a *Produced Work* (ODbL
  4.4(b)/4.3), which may be published under any terms provided it carries the notice "© OpenStreetMap
  contributors" and the ODbL-derived database it uses is itself offered under ODbL (4.6). This is what
  the recorded consequence (LEDGER 2026-09-24 (2)) specifies.

Building the national export (P30.3) also exposed two places where the *artifact-level* licence label
was not honest, which a share-alike-public rule makes consequential:

1. `web/map.json` — the map render surface — carries every published subject's own point and label from
   every site compartment (ODbL OSM points beside CC-BY/CC0/OGL/… points) but was labelled
   `CC-BY-4.0` in the `web` compartment. Under ADR-096 it was published as CC-BY (an ODbL-derived
   database relabelled — the very merge 4.4(a) forbids).
2. Per-compartment tiles were labelled `osm_physical` if ODbL else `sig_graph`, so a CC-BY-SA tile was
   filed under the CC-BY graph compartment.

## Decision

1. **Share-alike is no longer a reason to restrict.** An export artifact is PUBLIC iff
   (`ops/src/ops/publish.py:restriction_reason` returns `None`):
   - it carries **ONE** licence id — absent / list / compound SPDX expression (`A AND B`, `A OR B`) ⇒
     `mixed-licence` ⇒ restricted;
   - that licence is **known** to `policy/data/licenses.toml` — `UNDETERMINED` / unknown ⇒
     `unknown-licence` ⇒ restricted;
   - it has **no recorded export exclusion** (`export_disposition = "excluded"`, counsel-pending) ⇒
     `excluded:<key>` ⇒ restricted;
   - its compartment is **declared** — a `[compartments.*]` row, or the export's own `web` / `metadata`
     (SIG CC-BY-4.0) — ⇒ otherwise `unregistered-compartment` ⇒ restricted; and its licence **equals**
     that declared licence ⇒ otherwise `compartment-licence-mismatch` ⇒ restricted.

   So the ODbL `osm_physical`, the CC-BY-SA `portal` / `dot511_ccbysa2`, and every other single-licence
   compartment publish as **their own separate downloads** beside the CC-BY `sig_graph`; UNDETERMINED,
   excluded and mixed-licence bytes stay in the PRIVATE `…-sig-restricted` bucket.
2. **The guard re-proves separation over the public tree.** `assert_public_clean` fails loud
   (`CompartmentLeak`) on any artifact with a restriction reason, on **two licences inside one public
   compartment** (the `assert_separated` invariant re-proven after the partition, so ODbL can never sit
   in a file or directory with the CC-BY graph), and on any physical file outside the public manifest.
3. **Every public compartment is labelled.** `write_licence_index` writes `LICENCES.json` at the public
   root: per compartment its single SPDX licence, licence URL, share-alike / attribution-required facts,
   the attribution line a re-user must carry (ODbL: "© OpenStreetMap contributors (ODbL-1.0)"), and the
   artifact paths it covers; per-row source attribution already travels in the rows (SIG-EXPORT-006).
4. **Render surfaces are labelled with every licence they draw on.** The exporter labels `web/map.json`
   with the SPDX `AND` of the licences of the subjects it carries (a single-licence map keeps that one
   licence); the aggregate surfaces (counts, coverage, freshness, dossiers) remain SIG CC-BY-4.0. A
   subject with any licence-refused slice never reaches the map surface. Tiles are filed under the
   compartment their sites were placed in. The mixed `web/map.json` is therefore a **restricted build
   input** of the website, never a public download.
5. **The website is the produced work.** The public site (`web/dist`, built from the full export) shows
   every layer on one map/site, with `MAP_ATTRIBUTION_LINE` ("© OpenStreetMap contributors (ODbL) · …")
   on the map page, in the interactive map's attribution control, and in print (SIG-GEO-013); the
   ODbL-derived database it draws on is offered as the separate `osm_physical` compartment (4.6).
   The map's tile archives stay **per compartment** (`/tiles/<compartment>-sites.pmtiles`), each a
   separate style source with its own attribution (the ODbL source carries the OSM notice); the
   opt-in island fetches its points from the static `/map/points.json` instead of inlining ~225k points
   as props. That file is the **website's rendering data** — the same located points the rendered map
   and its tabular equivalent already put on the public page — so it draws on every compartment; it
   carries the OSM attribution and a licence note pointing re-users at the licence-separated
   compartments (anyone extracting a database from it takes an ODbL Derivative Database, 4.4). It is
   named explicitly as a question for counsel's written opinion (`D-P30.3-COUNSEL`); if counsel wants
   the site's rendering data split too, it becomes one points file per compartment (as the tiles are).
   The publish guard also refuses a site that serves a tile archive the public partition withholds
   (`assert_site_matches_partition`), so a data-row rollback of a compartment takes it off the site too.
6. **A real-data build renders only real data.** Building the national site surfaced committed OKC
   *demo* constants rendered on the public surfaces regardless of data source (density bins,
   centrality, the "OKCPD ALPR renewal" decision point, the worked-OKC "How we know this" default,
   the Paris/Brussels demonstration dossiers, demo jurisdiction claims). In `SIG_DATA_SOURCE=export`
   they are now read only from optional `web/presentation/*.json` artifacts (which the P27.5
   fixture-export harness ships for the test suite and no `--from-spine` export emits), so the
   national site shows each surface's honest empty state instead; the site-wide provenance default is
   derived from the export. The authenticated `/curate/**` shell ("not public", ADR-068) is stripped
   from `web/dist` before the public sync, and the web sync mirrors the build exactly.

## Consequences

- The national launch publishes all of the graph the rights gate admits, without ever merging licence
  regimes into one downloadable database; the separation invariant is enforced at export time
  (`assert_separated`, fail-closed licence gate) **and** re-proven at publish time.
- A new share-alike source needs no code change: it gets its own `[compartments.*]` row and publishes
  as its own compartment. A licence with no row / an UNDETERMINED record still fails closed.
- The honest-label fix means a consumer can no longer mistake ODbL-derived points for CC-BY data by
  downloading `web/map.json` — the file is simply not public; the per-licence compartments are.
- The launch rests on **operator-reported** counsel clearance. If the dated written opinion differs, the
  classifier narrows by data (an `export_disposition = "excluded"` row on the affected licence) and the
  next deploy's partition moves those compartments back to restricted — no code change.

## Alternatives considered

- **Keep ADR-096 (share-alike private).** Rejected — the operator lifted the counsel gate (2026-09-24);
  it would keep ~⅔ of the graph and all of OpenStreetMap off the public record.
- **Merge everything into one downloadable CC-BY/ODbL database.** Rejected — ODbL 4.4(a) would relicense
  SIG's own graph as ODbL and it breaks the gated separation invariant; explicitly not authorized.
- **Publish `web/map.json` as a public file (mixed label).** Rejected — the export bucket is where the
  *downloadable datasets* live, and a mixed-licence file there is a merged database in all but name; it
  stays a restricted build input while the site renders from it. (The site's own `/map/points.json` is
  the produced work's rendering data — Decision 5 — and is flagged to counsel.)
- **A per-compartment `public = true/false` flag.** Rejected again (ADR-096's reasoning holds): the
  licence facts + recorded exclusions already encode the distinction; a second flag can drift.

## Revisit trigger

- Counsel's **dated written opinion** (`D-P30.3-COUNSEL`) differs from the operator-reported clearance
  (e.g. limits ODbL 4.4(b) produced-work use, requires share-alike layers be served apart from the
  site, or wants the site's `/map/points.json` rendering data split per compartment) — record the narrowing as an `export_disposition = "excluded"` data row and/or a new ADR.
- A licensor (OpenStreetMap Foundation, a CC-BY-SA publisher) objects, or a takedown request under
  `policy/data/takedown.toml` targets a share-alike compartment.
- A new licence must stay private despite being known and single (e.g. a sensitive government feed) —
  the licence-only rule no longer suffices; introduce a per-compartment restriction in a new ADR.
- A render surface other than `web/map.json` starts carrying per-record data from several compartments —
  label it with `surface_license` in the exporter so the classifier keeps it restricted.
