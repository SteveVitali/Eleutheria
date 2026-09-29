# Contribution-back live runbook (HG-08, §7/§35.2; P21.7 → P29.1, ADR-069/ADR-100)

**Owner:** SIG operator. **Scope:** how the operator turns on the real OSM
contribution-back loop — MapRoulette cooperative-challenge push + OSM changeset-feed
pull → the §7 `LeverageLedger` — with **identity owned by OSM** and **no OSM display
names ever stored** (Part VIII §0.7).

## Current status (P29.1, 2026-09-23)

- **Code is activation-ready.** The concrete httpx transport
  (`tasks.maproulette.HttpxMapRouletteTransport`) is wired into the CLI, so a real
  MapRoulette push/pull POSTs the moment the operator provides the API key **and**
  registration is confirmed. Without them the client stays in dry-run and makes no
  network call (never fabricates a call).
- **HG-08 key this run: `provided: no`** (env `SIG_MAPROULETTE_API_KEY` checked; value
  never printed). So **no live push ran** and **`registered` stays `false`**
  (`ops/config.toml [tasks.contribution]`). Proven instead by dry-run + fixture replay:
  - `sig-tasks maproulette push --dry-run` → **REFUSED (exit 3)** while `registered=false`
    (SIG-CONTRIB-016d, RISK-P16-14).
  - sensitive-tier (C3/C4/C5) tasks **excluded** from any push payload (RISK-P21-12).
  - `sig-tasks osm-feed pull` over the committed fixtures attributes hashtag-bearing
    changesets to `LeverageLedger`, **idempotent** on re-run (+0), and stores **no OSM
    display names / uids** (`test_no_osm_user_names_are_stored_anywhere`).
- The real live push/pull is carried as a **RETURN PASS advancing `D-P21.7-1`**
  (deferred → activation-ready). It is NOT done; nothing is fabricated.

## Operator's remaining steps (the off-repo human acts, HG-08)

1. Create the MapRoulette account.
2. **Register** the SIG OSM Organised-Editing activity page (see
   `docs/governance/organised-editing-activity.md`); set `SIG_OSM_OE_PAGE` and, once
   truly registered, `ops/config.toml [tasks.contribution] registered = true`. **Do not
   set `registered=true` unless the OE page is actually registered** — SIG cannot verify
   a registration it did not perform.
3. Export the API key **into the run shell only** (env-only, HG-09; never a file):
   `export SIG_MAPROULETTE_API_KEY=…`
4. Re-run the live push/pull:
   ```bash
   uv run python -m tasks maproulette push --challenge sig-okc-operator-attribution --jurisdiction okc
   uv run python -m tasks maproulette pull --challenge <challenge-id-from-push>
   uv run python -m tasks osm-feed pull   # attribute landed changesets → LeverageLedger
   ```
   Record the resulting MapRoulette challenge id in `ops/config.toml`
   (`maproulette_challenge`) and flip `D-P21.7-1` → DONE with the real push evidence.

## Invariants (never relax)

- **No OSM display names or uids stored** — only public changeset ids (Part VIII §0.7).
- Contribution-back is a **human/gate action**, never automated; SIG performs no OSM
  edits (SIG-CONTRIB-014/015).
- Sensitive-tier coordinates never leave SIG in a challenge (RISK-P21-12).
- The API key lives in the environment only (HG-09) — no token literal in any file.
