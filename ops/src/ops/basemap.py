# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The basemap pipeline + host machinery (P36.33, R11-K13-MAP-02, SIG-UI-100).

K1 §2 / ADR-156 §Decision 6: the public map draws a self-hosted Protomaps
OpenStreetMap basemap (ODbL) as its own archive on a SIG-controlled origin —
never merged with SIG data, never a release input — pinned by
``ops/basemap.lock.json`` (``sig.basemap-lock/1``). The answered plan cells are
carried verbatim in the lock: **D-K1-1** basemap yes · **Q-31/D-K1-2 [A-3] = a**
the basemap lives on R2 after the DNS move (OP-09) · **D-K1-3 [B-22] = as
recommended**.

The ``sig-ops basemap`` family:

* ``check`` — the offline contract proof: the lock parses and validates, the
  v4↔5.x pairing holds, the generated styles carry the lock's build/key/glyph
  template, the glyph manifest re-hashes over the committed tree, CSP
  ``connect-src`` admits the tile origin, and the alert + kill-switch records
  exist. Fails loud (exit 4), never reports a partial posture as green.
* ``glyphs fetch|verify|stage`` — the self-hosted-glyph leg: fetch the pinned
  upstream ranges (``protomaps.github.io/basemaps-assets``), sha256-verify each
  file, write ``web/public/map/fonts/`` + ``sig.basemap-glyphs/1`` manifest +
  ``OFL.txt``, then stamp the manifest digest back into the lock. OFL assets
  (Noto Sans Regular + Italic — the fontstacks the emitted styles name).
* ``context-build`` — ``context.pmtiles`` (``sig.context-tiles/1``) from
  JUR-01's boundary pack: country/state/county outlines + place-name points,
  z0–10, public domain — the K1 §2.6 boundaries fallback, served same-origin,
  never from the basemap host.
* ``refresh`` — the twice-a-year rebuild leg: fetch ``builds.json``, resolve
  the build, stream-download verifying the published b3sum, upload under a new
  versioned key, record it in ``host.served`` (the previous key keeps serving
  30 days). ``--check`` prints the plan offline; ``--apply`` is env-gated
  (SIG_R2_* + SIG_BASEMAP_AUTHOR + the AR-3 windows) — without them it exits
  42 ``QUEUED`` with the OM-19 re-run prompt, never fabricating an upload.
* ``host`` — the ONE named OM-20 mutation (GATE-G5 list, expires GATE-G6):
  create the R2 bucket, apply the CORS/Range/cache posture and bind
  ``tiles.surveillancegraph.org``. ``--check`` prints the plan; ``--apply``
  refuses (exit 42) until OP-09's DNS move + the env credentials exist —
  ``prepared_not_executed``, never a fabricated create.
* ``kill-switch`` — the zero-cost-posture guard: flips ``serving.active_source``
  to ``context``, so every generated style repoints at the boundaries fallback
  on the next build (K1 §2.4's "points the style at the boundaries fallback").
  ``--check`` dry-runs the flip; ``--apply`` edits the lock.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json, sha256_hex

LOCK_SCHEMA = "sig.basemap-lock/1"
GLYPH_MANIFEST_SCHEMA = "sig.basemap-glyphs/1"
CONTEXT_CONTRACT = "sig.context-tiles/1"
ALERT_SCHEMA = "sig.basemap-alert/1"
DEFAULT_LOCK = Path("ops") / "basemap.lock.json"
GLYPH_ROOT = Path("web") / "public" / "map" / "fonts"
GLYPH_RANGE_SPAN = 256
R2_ACCOUNT_ENV = "SIG_CF_ACCOUNT_ID"
R2_TOKEN_ENV = "SIG_CF_API_TOKEN"
R2_KEY_ENV = "SIG_R2_ACCESS_KEY_ID"
R2_SECRET_ENV = "SIG_R2_SECRET_ACCESS_KEY"
AUTHOR_ENV = "SIG_BASEMAP_AUTHOR"
NOW_ENV = "SIG_BASEMAP_NOW"  # test-only clock override
RERUN = (
    "implement-spec spec=docs/tickets/374_P36.33__basemap-pipeline-and-host.md "
    "live_verification=true"
)


class BasemapError(Exception):
    """A fail-closed basemap pipeline error — spec, lock, fetch or verification."""


# --------------------------------------------------------------------------- #
# Lock model                                                                   #
# --------------------------------------------------------------------------- #


def _now() -> str:
    override = os.environ.get(NOW_ENV)
    if override:
        return override
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_get(url: str, timeout_s: float = 30.0, retries: int = 4) -> bytes:
    import time

    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "sig-ops-basemap/1"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                break
            time.sleep(0.5 * (attempt + 1))
        except urllib.error.URLError as exc:
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise BasemapError(f"fetch {url}: {last}")


def load_lock(path: Path | str = DEFAULT_LOCK) -> dict[str, Any]:
    """Parse + validate ``sig.basemap-lock/1``; a malformed lock refuses."""
    p = Path(path)
    if not p.is_file():
        raise BasemapError(f"basemap lock absent: {p}")
    try:
        lock = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BasemapError(f"{p}: unreadable lock — {exc}") from exc
    failures = validate_lock(lock)
    if failures:
        raise BasemapError(f"{p}: invalid sig.basemap-lock/1:\n  " + "\n  ".join(failures))
    return lock


def validate_lock(lock: dict[str, Any]) -> list[str]:
    """The fail-closed field contract — every named block must be whole."""
    f: list[str] = []
    if lock.get("schema") != LOCK_SCHEMA:
        f.append(f"schema must be {LOCK_SCHEMA}")
    for key in ("D-K1-1", "Q-31/D-K1-2 [A-3]", "D-K1-3 [B-22]"):
        if key not in (lock.get("decisions") or {}):
            f.append(f"decisions.{key} missing — the plan cells ride the lock")
    upstream = lock.get("upstream") or {}
    ref = upstream.get("reference_build") or {}
    for k in ("key", "bytes", "maxzoom", "tile_schema"):
        if ref.get(k) in (None, ""):
            f.append(f"upstream.reference_build.{k} missing")
    for k in ("builds_index", "archive_base"):
        if not str(upstream.get(k, "")).startswith("https://"):
            f.append(f"upstream.{k} must be an https URL")
    style = lock.get("style") or {}
    schema_v = str(ref.get("tile_schema", "")).lstrip("v")
    pkg_v = str(style.get("version", ""))
    if schema_v.startswith("4") and not pkg_v.startswith("5."):
        f.append("style package pairing broken: v4 tiles require @protomaps/basemaps 5.x")
    if not schema_v.startswith("4"):
        f.append("style package pairing broken: non-v4 tiles need a new pairing decision")
    for k in ("package", "version", "generator", "emitted"):
        if not style.get(k):
            f.append(f"style.{k} missing")
    glyphs = lock.get("glyphs") or {}
    for k in ("upstream_base", "fontstacks", "local_root", "url_template", "manifest"):
        if not glyphs.get(k):
            f.append(f"glyphs.{k} missing")
    if "{fontstack}" not in str(glyphs.get("url_template", "")):
        f.append("glyphs.url_template must carry {fontstack}/{range}")
    ctx = lock.get("context") or {}
    if ctx.get("contract") != CONTEXT_CONTRACT:
        f.append(f"context.contract must be {CONTEXT_CONTRACT}")
    host = lock.get("host") or {}
    if not str(host.get("origin", "")).startswith("https://"):
        f.append("host.origin must be an https URL")
    if not host.get("bucket"):
        f.append("host.bucket missing")
    cors = host.get("cors") or {}
    if "GET" not in (cors.get("allowed_methods") or []):
        f.append("host.cors must allow GET")
    if "Content-Range" not in (cors.get("expose_headers") or []):
        f.append("host.cors must expose Content-Range (PMTiles range reads)")
    if "immutable" not in str(host.get("cache_control", "")):
        f.append("host.cache_control must carry immutable on versioned keys")
    serving = lock.get("serving") or {}
    if serving.get("active_source") not in ("basemap", "context"):
        f.append('serving.active_source must be "basemap" or "context"')
    return f


def served_key(lock: dict[str, Any]) -> str:
    """The object key the styles name — ``host.served.key`` when a build has
    been uploaded, else the planned ``key_prefix + reference build`` (the
    refresh replaces it with the build it actually fetches)."""
    host = lock["host"]
    served = host.get("served")
    if isinstance(served, dict) and served.get("key"):
        return str(served["key"])
    return str(host["key_prefix"]) + str(lock["upstream"]["reference_build"]["key"])


def basemap_source_url(lock: dict[str, Any]) -> str:
    """The pmtiles URL the generated styles bind for the `basemap` source."""
    return f"pmtiles://{lock['host']['origin']}/{served_key(lock)}"


def context_source_url() -> str:
    """The same-origin context fallback — never the basemap host (K1 §2.6)."""
    return "pmtiles:///tiles/context.pmtiles"


def glyph_url_template(lock: dict[str, Any]) -> str:
    return str(lock["glyphs"]["url_template"])


# --------------------------------------------------------------------------- #
# Glyphs                                                                       #
# --------------------------------------------------------------------------- #


def glyph_ranges() -> list[str]:
    """The 256 upstream range file names ``0-255`` … ``65280-65535``."""
    return [f"{lo}-{lo + GLYPH_RANGE_SPAN - 1}" for lo in range(0, 65536, GLYPH_RANGE_SPAN)]


def glyph_manifest_root(digests: dict[str, str]) -> str:
    """The content root over ``{relpath: sha256}`` — the lock's pin."""
    return sha256_hex(canonical_json(dict(sorted(digests.items()))))


def build_glyph_manifest(
    digests: dict[str, str], lock: dict[str, Any], *, fetched_at: str
) -> dict[str, Any]:
    return {
        "schema": GLYPH_MANIFEST_SCHEMA,
        "upstream_base": lock["glyphs"]["upstream_base"],
        "fontstacks": list(lock["glyphs"]["fontstacks"]),
        "fetched_at": fetched_at,
        "root": glyph_manifest_root(digests),
        "files": dict(sorted(digests.items())),
        "licence": lock["glyphs"]["licence"],
        "licence_file": "OFL.txt",
    }


def fetch_glyph_set(
    lock: dict[str, Any],
    fetch: Callable[..., bytes] = _http_get,
) -> tuple[dict[str, bytes], str]:
    """Fetch every declared range + ``OFL.txt`` upstream → ``{relpath: bytes}``.

    Returns the file map and the upstream fetch timestamp. The fetcher is
    injectable — tests never touch the network.
    """
    base = str(lock["glyphs"]["upstream_base"]).rstrip("/")
    # the raw.githubusercontent.com mirror of the same repo serves identical
    # bytes and tolerates bulk fetches better than the Pages CDN.
    raw = "https://raw.githubusercontent.com/protomaps/basemaps-assets/main/fonts"
    files: dict[str, bytes] = {}
    for stack in lock["glyphs"]["fontstacks"]:
        enc = urllib.parse.quote(str(stack))
        for rng in glyph_ranges():
            rel = f"{stack}/{rng}.pbf"
            try:
                files[rel] = fetch(f"{raw}/{enc}/{rng}.pbf")
            except BasemapError:
                files[rel] = fetch(f"{base}/{enc}/{rng}.pbf")
    files["OFL.txt"] = fetch(f"{raw}/OFL.txt")
    return files, _now()


def write_glyph_tree(
    files: dict[str, bytes], out_dir: Path | str, lock: dict[str, Any], *, fetched_at: str
) -> dict[str, Any]:
    """Write the staged tree + the ``sig.basemap-glyphs/1`` manifest."""
    out = Path(out_dir)
    digests: dict[str, str] = {}
    for rel, blob in files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        digests[rel] = sha256_hex(blob)
    manifest = build_glyph_manifest(digests, lock, fetched_at=fetched_at)
    (out / "manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def verify_glyph_tree(out_dir: Path | str, manifest_path: Path | str | None = None) -> list[str]:
    """Re-hash the staged tree against its manifest — a drifted byte fails."""
    out = Path(out_dir)
    mpath = Path(manifest_path) if manifest_path else out / "manifest.json"
    failures: list[str] = []
    if not mpath.is_file():
        return [f"glyph manifest absent: {mpath}"]
    try:
        manifest = json.loads(mpath.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{mpath}: unreadable — {exc}"]
    if manifest.get("schema") != GLYPH_MANIFEST_SCHEMA:
        failures.append(f"manifest schema must be {GLYPH_MANIFEST_SCHEMA}")
    declared = manifest.get("files") or {}
    for rel, want in declared.items():
        f = out / rel
        if not f.is_file():
            failures.append(f"missing file {rel}")
            continue
        got = sha256_hex(f.read_bytes())
        if got != want:
            failures.append(f"{rel}: sha256 drift ({got[:12]} != {want[:12]})")
    extra = {
        str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"
    } - set(declared)
    for rel in sorted(extra):
        failures.append(f"unmanifested file {rel}")
    if not failures and manifest.get("root") != glyph_manifest_root(dict(declared)):
        failures.append("manifest root does not recompute over declared files")
    if not (out / "OFL.txt").is_file():
        failures.append("OFL.txt missing — the OFL licence file ships next to the assets")
    return failures


def stamp_lock_manifest(lock_path: Path | str, root: str) -> None:
    """Write the glyph manifest root back into the lock (a recorded field)."""
    p = Path(lock_path)
    lock = json.loads(p.read_text())
    lock["glyphs"]["manifest_sha256"] = root
    p.write_text(json.dumps(lock, indent=2) + "\n")


# --------------------------------------------------------------------------- #
# context.pmtiles                                                              #
# --------------------------------------------------------------------------- #

# The K1 §2.6 fallback content: outlines + place-name points, z0–10.
# (layer_id, tile layer, level/kind, name column, minzoom, maxzoom, geometry)
_CONTEXT_LAYERS: tuple[tuple[str, str, str, str | None, int, int, str], ...] = (
    ("ne_admin0", "boundary", "country", "NAME_EN", 0, 10, "polygon"),
    ("cb_500k", "boundary", "state", "NAME", 2, 10, "polygon"),
    ("ne_admin1", "boundary", "state", "name", 2, 10, "polygon"),
    ("tiger_county", "boundary", "county", "NAME", 7, 10, "polygon"),
    ("ne_admin0", "place", "country", "NAME_EN", 0, 4, "label_point"),
    ("ne_admin1", "place", "state", "name", 3, 7, "label_point"),
    ("gazetteer_state", "place", "state", "NAME", 2, 7, "point"),
    ("gazetteer_county", "place", "county", "NAME", 8, 10, "point"),
    ("gazetteer_place", "place", "place", "NAME", 7, 10, "point"),
)


def _flatten_geojson(geom: dict[str, Any]) -> list[dict[str, Any]]:
    """MultiPolygon → Polygon members; Point/Polygon pass through."""
    t = geom.get("type")
    if t == "MultiPolygon":
        return [{"type": "Polygon", "coordinates": c} for c in geom["coordinates"]]
    if t in ("Point", "Polygon"):
        return [geom]
    return []


def context_features(pack_dir: Path | str) -> list[dict[str, Any]]:
    """Read the boundary pack's parquet layers → tagged GeoJSON features."""
    import duckdb

    from exports import boundary_pack

    pack_dir = Path(pack_dir)
    manifest = boundary_pack.read_manifest(pack_dir)
    present = {r["id"]: r["path"] for r in manifest.get("layers", [])}
    wanted = {row[0] for row in _CONTEXT_LAYERS}
    missing = wanted - set(present)
    if missing:
        raise BasemapError(f"boundary pack {pack_dir} lacks declared layers: {sorted(missing)}")
    con = duckdb.connect()
    boundary_pack._spatial(con)  # noqa: SLF001 — same fail-closed loader
    features: list[dict[str, Any]] = []
    for layer_id, tile_layer, kind, name_col, zmin, zmax, geom_kind in _CONTEXT_LAYERS:
        pq = pack_dir / present[layer_id]
        expr = (
            "ST_AsGeoJSON(ST_PointOnSurface(geom))"
            if geom_kind == "label_point"
            else "ST_AsGeoJSON(geom)"
        )
        sql = f'SELECT "{name_col}" AS name, {expr} AS g FROM read_parquet(?)'
        try:
            rows = con.execute(sql, [str(pq)]).fetchall()
        except Exception as exc:  # noqa: BLE001 — name the layer on any failure
            raise BasemapError(f"context-build: layer {layer_id} read failed: {exc}") from exc
        for name, gjson in rows:
            if not gjson:
                continue
            geom = json.loads(gjson)
            for flat in _flatten_geojson(geom):
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "kind": kind if tile_layer == "place" else None,
                            "level": kind if tile_layer == "boundary" else None,
                            "name": name or "",
                        },
                        "geometry": flat,
                        "tippecanoe": {"layer": tile_layer, "minzoom": zmin, "maxzoom": zmax},
                    }
                )
    # strip None props
    for f in features:
        f["properties"] = {k: v for k, v in f["properties"].items() if v is not None}
    return features


def build_context_pmtiles(pack_dir: Path | str, out_path: Path | str) -> dict[str, Any]:
    """Verify the pack (fail-closed), render + write ``context.pmtiles``."""
    from exports.tiles import _render_pyramid, build_pmtiles

    from exports import boundary_pack

    failures = boundary_pack.verify_pack(pack_dir)
    if failures:
        raise BasemapError(
            "context-build: boundary pack failed verification:\n  " + "\n  ".join(failures)
        )
    manifest = boundary_pack.read_manifest(pack_dir)
    features = context_features(pack_dir)
    if not features:
        raise BasemapError("context-build: zero features — refusing an empty fallback")
    tiles = _render_pyramid(features, layer_name="boundary", minzoom=0, maxzoom=10)
    metadata = {
        "schema": CONTEXT_CONTRACT,
        "name": "SIG context basemap (boundaries fallback)",
        "format": "pbf",
        "vector_layers": [
            {"id": "boundary", "fields": {"level": "String", "name": "String"}},
            {"id": "place", "fields": {"kind": "String", "name": "String"}},
        ],
        "attribution": "Boundaries: U.S. Census Bureau, Natural Earth (public domain)",
        "license": "public domain",
        "source_pack": manifest.get("pack_id"),
        "boundaries_root": manifest.get("boundaries_root"),
        "pack_gate_mode": (manifest.get("gate") or {}).get("mode"),
        "minzoom": 0,
        "maxzoom": 10,
    }
    blob = build_pmtiles(tiles, metadata=metadata, minzoom=0, maxzoom=10)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    return {
        "features": len(features),
        "tiles": len(tiles),
        "bytes": len(blob),
        "sha256": sha256_hex(blob),
        "path": str(out),
        "boundaries_root": manifest.get("boundaries_root"),
    }


# --------------------------------------------------------------------------- #
# Refresh + host legs                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CheckResult:
    id: str
    ok: bool
    detail: str


def _ar3_violations(now_iso: str) -> str | None:
    """AR-3: batch window day 6 00:00Z → day 13 12:00Z; daily 03:00–06:30Z."""
    try:
        dt = datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return f"unparseable clock {now_iso}"
    day = dt.day
    if day == 6 or (7 <= day <= 12) or (day == 13 and dt.hour < 12):
        return "inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)"
    if (dt.hour, dt.minute) >= (3, 0) and (dt.hour, dt.minute) < (6, 30):
        return "inside the daily 03:00-06:30Z exclusion"
    return None


def apply_gate(lock: dict[str, Any], *, env: dict[str, str] | None = None) -> list[str]:
    """The OM-19 apply gate — returns the unmet preconditions (never passes
    silently: an absent env is a queue, not a skip)."""
    env = dict(os.environ if env is None else env)
    unmet: list[str] = []
    for var in (R2_ACCOUNT_ENV, R2_TOKEN_ENV, R2_KEY_ENV, R2_SECRET_ENV, AUTHOR_ENV):
        if not env.get(var):
            unmet.append(f"{var} unset (env only, HG-09)")
    viol = _ar3_violations(str(env.get(NOW_ENV) or _now()))
    if viol:
        unmet.append(f"AR-3 window: {viol}")
    return unmet


def refresh_plan(lock: dict[str, Any]) -> list[str]:
    ref = lock["upstream"]["reference_build"]
    return [
        "PLAN sig-ops basemap refresh (K1 §2.2 — twice a year / on upgrade):",
        "  1. fetch builds_index, resolve --build (default: latest)",
        "  2. stream-download archive_base + key; verify the index's b3sum",
        f"  3. upload under versioned key {lock['host']['key_prefix']}<key> "
        f"→ {lock['host']['bucket']} ({lock['host']['provider']})",
        "  4. record host.served={key,build,b3sum,uploaded_at}; the previous key "
        f"keeps serving {lock['host']['keep_previous_days']} days",
        "  5. regenerate web styles (web/scripts/gen-map-styles.mjs reads this lock)",
        f"  reference: {ref['key']} ({ref['bytes']} B, z0–{ref['maxzoom']}, schema "
        f"{ref['tile_schema']}) — measured, rotated upstream; the apply pins what it fetches",
        f"  cache-control: {lock['host']['cache_control']} on versioned keys",
        "  run outside GCP (a GCP upload ~$17/refresh egress; K1 §2.2 inference)",
    ]


def host_plan(lock: dict[str, Any]) -> list[str]:
    host = lock["host"]
    cors = host["cors"]
    return [
        "PLAN sig-ops basemap host (the ONE named OM-20 mutation — GATE-G5 listed,",
        "expires GATE-G6; queued OM-19 while the hosted env is absent):",
        f"  1. R2 bucket create {host['bucket']} ({host['provider']})",
        "  2. CORS policy: "
        + f"{cors['allowed_methods']} from {cors['allowed_origins']}, "
        + f"headers {cors['allowed_headers']}, expose {cors['expose_headers']}",
        f"  3. custom domain {host['origin']} (needs OP-09 — the zone on Cloudflare)",
        "  4. public access on the custom domain only; the bucket stays non-listable",
        "  5. first upload = `sig-ops basemap refresh --apply` (the same leg)",
        f"  headers: {host['cache_control']} on versioned keys; Range reads pass through",
        "  restore point: the host is re-creatable from basemap.lock.json + the upstream archive",
        "  kill switch: lock serving.active_source → context + the provider-side "
        "domain disable (operator act)",
        f"  re-run: {RERUN}",
    ]


def resolve_build(
    index_url: str, want: str, fetch: Callable[..., bytes] = _http_get
) -> dict[str, Any]:
    """Resolve a build row from builds.json — ``latest`` or a named key."""
    rows = json.loads(fetch(index_url))
    if not isinstance(rows, list) or not rows:
        raise BasemapError(f"{index_url}: empty build index")
    if want == "latest":
        row = rows[-1]
    else:
        row = next((r for r in rows if r.get("key") == want), None)
        if row is None:
            raise BasemapError(f"build {want} not in index ({len(rows)} rows, rotated)")
    for k in ("key", "size", "b3sum", "version"):
        if not row.get(k):
            raise BasemapError(f"index row for {row.get('key')}: {k} missing")
    if str(row["version"]) != "4.15.2" and not str(row["version"]).startswith("4."):
        raise BasemapError(f"build {row['key']} schema {row['version']} breaks the v4↔5.x pairing")
    return row


def _b3_hex(data: bytes) -> str:
    import blake3

    return blake3.blake3(data).hexdigest()


def _download_verified(url: str, want_b3: str, want_size: int, dest: Path) -> dict[str, Any]:
    """Stream-download ``url`` to ``dest`` verifying b3sum + size.

    A digest or size mismatch refuses and unlinks the partial file — the host
    never receives unverified bytes.
    """
    import blake3

    h = blake3.blake3()
    n = 0
    req = urllib.request.Request(url, headers={"User-Agent": "sig-ops-basemap/1"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:  # noqa: S310
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                fh.write(chunk)
                n += len(chunk)
    except urllib.error.URLError as exc:
        dest.unlink(missing_ok=True)
        raise BasemapError(f"download {url}: {exc}") from exc
    if n != want_size:
        dest.unlink(missing_ok=True)
        raise BasemapError(f"download {url}: {n} B != declared {want_size} B")
    got = h.hexdigest()
    if got != want_b3:
        dest.unlink(missing_ok=True)
        raise BasemapError(f"download {url}: b3sum {got} != index {want_b3}")
    return {"bytes": n, "b3sum": got, "path": str(dest)}


def _r2_client() -> Any:
    """The R2 S3 client — env-keyed, injected in tests."""
    import boto3

    endpoint = f"https://{os.environ[R2_ACCOUNT_ENV]}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ[R2_KEY_ENV],
        aws_secret_access_key=os.environ[R2_SECRET_ENV],
        region_name="auto",
    )


def refresh_apply(
    lock: dict[str, Any],
    lock_path: Path | str,
    *,
    build: str = "latest",
    state_dir: Path | str | None = None,
    fetch: Callable[..., bytes] = _http_get,
    client: Any = None,
) -> dict[str, Any]:
    """The refresh leg's bounded write: fetch → b3sum-verify → upload under a
    new versioned key → record ``host.served`` (previous kept 30 days)."""
    import tempfile

    row = resolve_build(lock["upstream"]["builds_index"], build, fetch)
    host = lock["host"]
    key = f"{host['key_prefix']}{row['key']}"
    url = lock["upstream"]["archive_base"].rstrip("/") + "/" + row["key"]
    sdir = Path(state_dir) if state_dir else Path(tempfile.mkdtemp(prefix="basemap-"))
    dest = sdir / row["key"]
    got = _download_verified(url, row["b3sum"], int(row["size"]), dest)
    s3 = client if client is not None else _r2_client()
    s3.put_object(
        Bucket=host["bucket"],
        Key=key,
        Body=dest.read_bytes(),
        ContentType="application/octet-stream",
        CacheControl=host["cache_control"],
    )
    now = _now()
    update_lock_served(lock_path, row, now=now)
    return {
        "status": "uploaded",
        "build": row["key"],
        "key": key,
        "bucket": host["bucket"],
        "bytes": got["bytes"],
        "b3sum": got["b3sum"],
        "uploaded_at": now,
    }


def _cf_api(token: str, account: str, method: str, path: str, body: Any = None) -> Any:
    """One Cloudflare API call — the host-create leg's transport."""
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}{path}",
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise BasemapError(
            f"cloudflare {method} {path}: HTTP {exc.code} — {exc.read()[:400]!r}"
        ) from exc


def host_apply(
    lock: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
    api: Callable[..., Any] = _cf_api,
) -> dict[str, Any]:
    """The host create's three mutations: bucket, CORS posture, custom domain.

    ``api`` is injectable — the env gate precedes this, and the domain bind
    requires OP-09's zone move to have already happened.
    """
    env = dict(os.environ if env is None else env)
    account = env[R2_ACCOUNT_ENV]
    token = env[R2_TOKEN_ENV]
    host = lock["host"]
    cors = host["cors"]
    results: dict[str, Any] = {"bucket": host["bucket"], "steps": []}
    results["steps"].append(api(token, account, "POST", "/r2/buckets", {"name": host["bucket"]}))
    results["steps"].append(
        api(
            token,
            account,
            "PUT",
            f"/r2/buckets/{host['bucket']}/cors",
            {
                "allowed": {
                    "origins": cors["allowed_origins"],
                    "methods": cors["allowed_methods"],
                    "headers": cors["allowed_headers"],
                },
                "exposeHeaders": cors["expose_headers"],
                "maxAgeSeconds": cors["max_age_seconds"],
            },
        )
    )
    domain = str(host["origin"]).removeprefix("https://")
    results["steps"].append(
        api(
            token,
            account,
            "POST",
            f"/r2/buckets/{host['bucket']}/domains/custom",
            {"domain": domain, "enabled": True},
        )
    )
    results["created_at"] = _now()
    results["author"] = env.get(AUTHOR_ENV)
    return results


def update_lock_served(lock_path: Path | str, row: dict[str, Any], *, now: str) -> None:
    """Record the uploaded key; the previous key is kept ``keep_previous_days``."""
    p = Path(lock_path)
    lock = json.loads(p.read_text())
    host = lock["host"]
    prev = host.get("served")
    if isinstance(prev, dict) and prev.get("key"):
        retire = (
            datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            + timedelta(days=int(host.get("keep_previous_days", 30)))
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        host.setdefault("previous", []).append({**prev, "retire_after": retire})
    host["served"] = {
        "key": f"{host['key_prefix']}{row['key']}",
        "build": row["key"],
        "b3sum": row["b3sum"],
        "bytes": row["size"],
        "uploaded_at": now,
    }
    p.write_text(json.dumps(lock, indent=2) + "\n")


def kill_switch(lock_path: Path | str, *, apply: bool) -> list[str]:
    """Flip ``serving.active_source`` → ``context`` (K1 §2.4's fallback repoint)."""
    p = Path(lock_path)
    lock = json.loads(p.read_text())
    current = lock["serving"]["active_source"]
    lines = [
        f"kill switch: serving.active_source {current} → context",
        "  every generated style then binds context.pmtiles (same-origin) —",
        "  basemap fetch traffic stops on the next build/publish",
        "  provider side (operator act): disable the custom domain / R2 public access",
    ]
    if apply:
        if current == "context":
            lines.append("  already at context — no change")
        else:
            lock["serving"]["active_source"] = "context"
            p.write_text(json.dumps(lock, indent=2) + "\n")
            lines.append(f"  APPLIED to {p} — regenerate styles (gen-map-styles.mjs)")
    else:
        lines.append("  (check only — --apply writes the lock)")
    return lines


# --------------------------------------------------------------------------- #
# Offline contract check                                                       #
# --------------------------------------------------------------------------- #


def _csp_admits_origin(config_text: str, origin: str, lib_text: str) -> bool:
    """True when astro.config's connect-src admits the tile origin — either
    literally or through the BASEMAP_TILE_ORIGIN constant whose value equals
    the lock's origin."""
    admits = any(
        "connect-src" in line and (origin in line or "BASEMAP_TILE_ORIGIN" in line)
        for line in config_text.splitlines()
    )
    if not admits:
        return False
    if origin in config_text:
        return True
    return f'"{origin}"' in lib_text or f"'{origin}'" in lib_text


def run_checks(repo_root: Path | str) -> list[CheckResult]:
    """The offline posture proof — every green is a real check (SIG-ENG-042)."""
    root = Path(repo_root)
    out: list[CheckResult] = []

    lock_path = root / DEFAULT_LOCK
    try:
        lock = load_lock(lock_path)
        out.append(CheckResult("lock-parse", True, "sig.basemap-lock/1 valid"))
    except BasemapError as exc:
        out.append(CheckResult("lock-parse", False, str(exc)))
        return out

    styles_ok = True
    style_detail = []
    active = lock["serving"]["active_source"]
    for rel in lock["style"]["emitted"]:
        p = root / rel
        if not p.is_file():
            styles_ok = False
            style_detail.append(f"{rel} missing (run gen-map-styles.mjs)")
            continue
        try:
            style = json.loads(p.read_text())
        except json.JSONDecodeError as exc:
            styles_ok = False
            style_detail.append(f"{rel}: unreadable — {exc}")
            continue
        meta = style.get("metadata") or {}
        sig = meta.get("sig:basemap") or {}
        if sig.get("active_source") != active:
            styles_ok = False
            style_detail.append(f"{rel}: sig:basemap.active_source != lock's {active}")
        sources = style.get("sources") or {}
        if "basemap" in sources and lock["serving"]["active_source"] == "basemap":
            src = sources["basemap"]
            want = basemap_source_url(lock)
            if src.get("url") != want:
                styles_ok = False
                style_detail.append(f"{rel}: basemap source {src.get('url')} != {want}")
        if "context" in sources and sources["context"].get("url") != context_source_url():
            styles_ok = False
            style_detail.append(
                f"{rel}: context source {sources['context'].get('url')} != {context_source_url()}"
            )
        if style.get("glyphs") != glyph_url_template(lock):
            styles_ok = False
            style_detail.append(f"{rel}: glyphs != {glyph_url_template(lock)}")
    out.append(
        CheckResult("styles", styles_ok, "; ".join(style_detail) or "emitted styles bind the lock")
    )

    glyph_failures = verify_glyph_tree(root / lock["glyphs"]["local_root"])
    out.append(
        CheckResult(
            "glyphs",
            not glyph_failures,
            "; ".join(glyph_failures) or "glyph tree re-hashes against its manifest",
        )
    )

    cfg = root / "web" / "astro.config.mjs"
    lib = root / "web" / "src" / "lib" / "basemap.ts"
    csp_ok = cfg.is_file() and _csp_admits_origin(
        cfg.read_text(),
        lock["host"]["origin"],
        lib.read_text() if lib.is_file() else "",
    )
    out.append(
        CheckResult(
            "csp-connect-src",
            csp_ok,
            f"connect-src admits {lock['host']['origin']}"
            if csp_ok
            else "astro.config connect-src lacks the tile origin",
        )
    )

    alert = root / "ops" / "basemap.alert.json"
    alert_ok = False
    if alert.is_file():
        try:
            alert_ok = json.loads(alert.read_text()).get("schema") == ALERT_SCHEMA
        except json.JSONDecodeError:
            alert_ok = False
    out.append(CheckResult("budget-alert", alert_ok, "sig.basemap-alert/1 committed"))
    out.append(
        CheckResult(
            "kill-switch",
            bool(lock["serving"].get("kill_switch")),
            "kill switch declared in the lock",
        )
    )
    return out


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _print(lines: list[str]) -> None:
    for line in lines:
        print(line)


def _queued(unmet: list[str], what: str) -> int:
    print(f"basemap {what}: QUEUED (exit 42) — preconditions unmet:", file=sys.stderr)
    for u in unmet:
        print(f"  - {u}", file=sys.stderr)
    print(f"  re-run: {RERUN}", file=sys.stderr)
    print("  status: prepared_not_executed — nothing ran against any host", file=sys.stderr)
    return 42


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops basemap",
        description=(
            "P36.33 (K1 MAP-02, SIG-UI-100): the basemap pipeline + host — "
            "check / glyphs / context-build / refresh / host / kill-switch"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lock", help="print the parsed sig.basemap-lock/1 (offline)")
    p_check = sub.add_parser("check", help="the offline contract proof (exit 4 on failure)")
    p_check.add_argument("--repo-root", default=".")

    pg = sub.add_parser("glyphs", help="self-hosted glyph machinery")
    pgs = pg.add_subparsers(dest="glyphs_cmd", required=True)
    pgf = pgs.add_parser("fetch", help="fetch + verify + stage the pinned upstream ranges")
    pgf.add_argument("--out", default=str(GLYPH_ROOT))
    pgf.add_argument("--lock", default=str(DEFAULT_LOCK))
    pgf.add_argument("--stamp-lock", action="store_true", help="write manifest root into the lock")
    pgv = pgs.add_parser("verify", help="re-hash the staged tree against its manifest (exit 4)")
    pgv.add_argument("--dir", default=str(GLYPH_ROOT))

    pc = sub.add_parser("context-build", help="context.pmtiles from JUR-01's boundary pack")
    pc.add_argument("--pack", required=True, help="the boundary-pack dir (manifest.json present)")
    pc.add_argument("--out", required=True)

    pr = sub.add_parser("refresh", help="the twice-a-year rebuild leg (--check default)")
    pr.add_argument("--check", action="store_true")
    pr.add_argument("--apply", action="store_true")
    pr.add_argument("--build", default="latest")
    pr.add_argument("--lock", default=str(DEFAULT_LOCK))

    ph = sub.add_parser("host", help="the R2 host create (OM-20 named; --check default)")
    ph.add_argument("--check", action="store_true")
    ph.add_argument("--apply", action="store_true")
    ph.add_argument("--lock", default=str(DEFAULT_LOCK))

    pk = sub.add_parser("kill-switch", help="the fallback repoint (--check default)")
    pk.add_argument("--check", action="store_true")
    pk.add_argument("--apply", action="store_true")
    pk.add_argument("--lock", default=str(DEFAULT_LOCK))

    args = parser.parse_args(argv)

    if args.cmd == "lock":
        _print(
            [json.dumps(load_lock(args.lock if hasattr(args, "lock") else DEFAULT_LOCK), indent=2)]
        )
        return 0
    if args.cmd == "check":
        results = run_checks(args.repo_root)
        for r in results:
            print(f"{'ok  ' if r.ok else 'FAIL'} {r.id}: {r.detail}")
        return 0 if all(r.ok for r in results) else 4
    if args.cmd == "glyphs":
        lock = load_lock(args.lock if getattr(args, "lock", None) else DEFAULT_LOCK)
        if args.glyphs_cmd == "fetch":
            files, fetched_at = fetch_glyph_set(lock)
            manifest = write_glyph_tree(files, args.out, lock, fetched_at=fetched_at)
            print(
                f"glyphs: staged {len(manifest['files'])} files → {args.out} "
                f"(root {manifest['root'][:16]}…)"
            )
            if args.stamp_lock:
                stamp_lock_manifest(args.lock, manifest["root"])
                print(f"glyphs: lock manifest_sha256 → {manifest['root'][:16]}…")
            return 0
        if args.glyphs_cmd == "verify":
            failures = verify_glyph_tree(args.dir)
            if failures:
                for fl in failures:
                    print(f"FAIL {fl}", file=sys.stderr)
                return 4
            print(f"glyphs: {args.dir} verified against its manifest")
            return 0
    if args.cmd == "context-build":
        summary = build_context_pmtiles(args.pack, args.out)
        print(
            f"context-build: {summary['features']} features → {summary['tiles']} tiles, "
            f"{summary['bytes']} B sha256:{summary['sha256'][:16]}… → {summary['path']}"
        )
        return 0
    if args.cmd == "refresh":
        lock = load_lock(args.lock)
        if args.apply:
            unmet = apply_gate(lock)
            if unmet:
                return _queued(unmet, "refresh")
            try:
                rec = refresh_apply(lock, args.lock, build=args.build)
            except BasemapError as exc:
                print(f"refresh: REFUSED — {exc}", file=sys.stderr)
                return 4
            print(
                f"refresh: uploaded {rec['key']} → {rec['bucket']} "
                f"({rec['bytes']} B b3sum:{rec['b3sum'][:16]}…); lock host.served updated"
            )
            return 0
        _print(refresh_plan(lock))
        return 0
    if args.cmd == "host":
        lock = load_lock(args.lock)
        if args.apply:
            unmet = apply_gate(lock)
            if unmet:
                return _queued(unmet, "host")
            try:
                rec = host_apply(lock)
            except BasemapError as exc:
                print(f"host: REFUSED — {exc}", file=sys.stderr)
                return 4
            print(
                f"host: created {rec['bucket']} + CORS + custom domain "
                f"({len(rec['steps'])} steps, {rec['created_at']})"
            )
            return 0
        _print(host_plan(lock))
        return 0
    if args.cmd == "kill-switch":
        _print(kill_switch(args.lock, apply=args.apply))
        return 0
    return 64


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
