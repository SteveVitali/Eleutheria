# Contribution-back live — runbook + what ran live (P21.7)

- **Ticket:** `docs/tickets/P21.7__contribution-back-live.md`
- **ADR:** [ADR-069](../adr/ADR-069-contribution-back-live-maproulette-client-osm-changeset-feed-and-the-registration-gate.md) (amends ADR-055).
- **Gate:** HG-08 (MapRoulette/OSM account) and HG-10 (usability participants) —
  **both gate-pending**. This run touched **no** live MapRoulette or OSM endpoint.

## What ran live this run

**Nothing on the network.** Per HG-08 there is no `SIG_MAPROULETTE_API_KEY` and no
`SIG_OSM_OE_PAGE`, so every command below ran in its safe default:

| command | what happened this run |
|---|---|
| `sig-tasks maproulette push` | **REFUSED — exit 3** (`registered=false` in `ops/config.toml`). No payload was sent. |
| `sig-tasks maproulette pull --challenge …` | **dry-run** — printed the endpoint it *would* GET; no network. |
| `sig-tasks osm-feed pull` | **fixtures replay** — parsed `tests/tasks/fixtures/osm_changesets_*.xml`; attributed 4 changesets (3 accepted); **no live OSM poll**. |

No automated OSM edit was made, and none can be: `tasks.contribution.write_to_osm`
exists only to refuse (SIG-CONTRIB-014). The only live OSM verbs the system will ever
perform are a **human-authorised challenge create** and a **public feed read**.

## Runbook — turning on the live edge (when HG-08 clears)

1. **Register** the Organised Editing activity in the OSMF activities list (an
   off-repo human act). Publish the wiki page under
   `Organised Editing/Activities/SIG operator attribution`.
2. **Record** the registration in `ops/config.toml` `[tasks.contribution]`:
   - `registered = true`
   - `oe_page = "<the OSM wiki page URL>"` (`SIG_OSM_OE_PAGE`)
3. **Export** the MapRoulette account key at push time (never committed):
   `export SIG_MAPROULETTE_API_KEY=…`.
4. **Push** a challenge — now authorised and no longer dry-run:
   `sig-tasks maproulette push --jurisdiction okc`.
   Record the returned challenge id in `ops/config.toml`
   `[tasks.contribution] maproulette_challenge` and in the *Live challenges* table
   below.
5. **Pull** task-status changes: `sig-tasks maproulette pull --challenge <id>`.
6. **Feed** the §7 metric from the real changeset feed and write the web artifact:
   `sig-tasks osm-feed pull --since <ISO> --out exports/out/okc`
   (writes `exports/out/okc/web/leverage.json`), then build the web in export mode
   (`SIG_DATA_SOURCE=export`) so `/contribution-back/` renders real data.

## Safety properties (hold with or without HG-08)

- **Registration gate, fails closed.** No push before `registered=true`
  (`tasks.contribution.contribution_registered()`; exit 3).
- **Sensitive tiers never pushed.** Tasks with `geo_tier>=3` (C3/C4/C5) are excluded
  from every payload (RISK-P21-12).
- **No OSM user data.** The changeset feed stores only the changeset id + comment
  (Part VIII §0.7).
- **Dry-run by default.** No key ⇒ no network; the payloads are printed for review.

## Live record (fill in when a real push/pull happens)

| date | challenge id | jurisdiction | tasks pushed | excluded (sensitive) | accepted (metric) |
|---|---|---|---|---|---|
| _none — gate-pending HG-08_ | — | — | — | — | — |

## Usability study

See [`USABILITY_STUDY.md`](USABILITY_STUDY.md): protocol + aggregate-only
instrumentation landed; the moderated study is **not yet run — gate-pending HG-10**.
