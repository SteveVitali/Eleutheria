<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SUCCESSION — continuity, mirrors, and how to rebuild SIG from the archive

*P21.5, SIG-GOV-022/023/024, §46.5, ADR-067. Companion: `ops/mirrors.toml` (the mirror
manifest), `docs/build/DEPOSITS.md` (the deposit ledger), `docs/build/INFRA_RUNBOOK.md`.*

**Purpose.** If the primary domain, the git forge, or the project itself disappears, the
data and code are released in a form that lets others continue (SIG-GOV-023). This
document is the map: **what is deposited where**, and **how to rebuild the public site**
from the deposit + the repository.

## Where everything lives (no sole home — SIG-STORE-004/005)

See `ops/mirrors.toml` for the machine-readable manifest. In prose:

| home | kind | what it holds | status |
|---|---|---|---|
| **Zenodo** (`zenodo.org`) | citable archive | each bulk-export release + `manifest.json` + `digests.json` + `CITATION.cff` + `sbom.cdx.json`, under a concept DOI (all versions) and a version DOI (one release) | gate-pending: HG-07 (sandbox until a production token) |
| **Object store** (Cloudflare R2 `sig-bulk`) | primary download | every artifact under `<release_id>/<path>.<hash>`, content-hash keyed, immutable | gate-pending: HG-07 |
| **BitTorrent** | zero-egress peer mirror | a `.torrent` per bulk artifact (trackerless/DHT-capable) | live (free path) |
| **Software Heritage** | source archive | the SIG source repository (save code now) | gate-pending: untriggered this run |
| **git forge** (GitHub) | primary source | the repo + committed export snapshots | live |

The evidence corpus itself is **not** deposited to Zenodo (excluded by size, §38.2); its
per-file SHA-256 digests travel in `digests.json`, and the corpus stays in the OCFL
evidence store (ADR-015/ADR-023), readable **without SIG's software**.

## Rebuild the public site from the deposit + repo (≤10 steps)

A reader with only the Zenodo deposit and the source repository can reconstruct the site:

1. **Clone the source.** `git clone <repo-or-Software-Heritage-URL> && cd Eleutheria`.
2. **Install the toolchain.** `uv python install && make sync` (Python workspace), and
   `npm --prefix web ci` (the web shell). Both install strictly from committed lockfiles.
3. **Fetch the release** from Zenodo by its **concept DOI** (resolves to the latest
   version) or a specific **version DOI** — see `docs/build/DEPOSITS.md` for the DOIs.
4. **Verify integrity.** Check every artifact's SHA-256 against the deposited
   `manifest.json` / `digests.json` (checksums are part of the release, SIG-EXPORT-001).
5. **Place the export** in a directory, e.g. `exports/out/okc/`, preserving the
   `manifest.json`, the compartment dirs (`osm_physical/`, `sig_graph/`), and `web/`.
6. **Build the static site from the export** (no API, no database):
   `SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<dir> uv run sig-ops degraded --data-source export`
   (equivalently `npm --prefix web run build` with those env vars).
7. **Confirm the tiles** were consumed: `web/dist/tiles/sig-infrastructure.pmtiles` exists
   (the ODbL map layer; rendered by `sig-exports tiles`).
8. **Serve `web/dist`** with any static file host (`python -m http.server`, a CDN, or a
   web-archive replay) — the site reads no live API by construction (ADR-066).
9. **(Optional) Re-derive the graph** from the claim spine if the PG dump is available:
   `sig-ops up && sig-ops seed`, then `sig-exports build --jurisdiction <j>` reproduces a
   byte-identical release from the same `BuildSpec` (SIG-EXPORT-003).
10. **(Optional) Re-mirror.** Re-run `sig-exports torrent` / `push` / `deposit` and
    `sig-ops swh-save` to re-establish the mirrors from the rebuilt release.

Steps 1–8 rebuild the **live-equivalent public site** from the archive alone; 9–10
re-establish the full pipeline and mirrors.

## Known decay paths (documented, per SIG-GOV-021)

- **Free schedulers disable dormant workflows.** Guarded by the monthly
  `.github/workflows/keepalive.yml`, which rebuilds the static site and **fails loudly** if
  it cannot (RISK-P0-12).
- **Sandbox vs production DOIs.** A sandbox `10.5072/…` DOI is not citable; `DEPOSITS.md`
  marks the environment (RISK-P21-08).
- **Egress cost runaway.** Bounded by a zero-egress store + content-hash immutable caching;
  measured by `sig-ops egress-report` against the documented budget (RISK-P21-09).
