# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The GeoParquet **boundary pack** (K4 §4.2, P35.17, ADR-160; SIG-GEO-008).

The upstream boundary files — TIGER/Line 2025 state/county/place, the Census
Gazetteer 2025 names/points, Natural Earth 10m admin-0/admin-1, and the
cartographic 500k display files — are **evidence**: captured into the OCFL
store behind the fail-closed ingestion gate (HG-03 flips of
``census_gazetteer_tiger`` and ``natural_earth_10m`` — never this module's
act), then converted once per vintage into a GeoParquet pack staged as a
**restricted export input** under ``<export>/inputs/boundary-pack/``. Its
content root is the descriptor v2 ``boundaries_root`` (K4 §4.2 / REL-01).

Fail-closed by construction:

* :func:`build_pack` refuses (``BoundaryPackError``) when any declared layer's
  source is not ``ingestion_permitted`` in the committed source registry —
  unless the caller declares the inputs are stand-ins (``--fixture``, recorded
  in the manifest's ``gate.mode`` as ``"fixture-bypass"`` so a fixture pack can
  never pass for a captured one).
* :func:`verify_pack` re-hashes every emitted file and recomputes the content
  root; :func:`derive_boundaries_root` (the descriptor's source of truth) runs
  the same verification on the staged copy and refuses a tampered or
  inconsistent pack.
* Layer formats are a closed vocabulary and every input file is read through
  DuckDB ``spatial`` — a declared-but-absent input fails the build, never
  silently skipped.

GeoParquet is written by DuckDB's ``COPY … (FORMAT PARQUET)`` over a
``GEOMETRY`` column with the ``spatial`` extension loaded (WKB encoding + the
``geo`` footer metadata block). The extension must be loadable at build time;
absence raises ``BoundaryPackError`` (recorded honestly, never a stub pack).
"""

from __future__ import annotations

import shutil
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import canonical_json, sha256_hex

PACK_SCHEMA = "sig.boundary-pack/1"
PACK_SPEC_RESOURCE = "data/boundary_pack.toml"
#: The committed default spec (the declared layer set; a caller may pass a
#: narrower fixture spec but the production one is data, not code).
PACK_SPEC_RESOURCE_PATH = Path(__file__).resolve().parent / PACK_SPEC_RESOURCE
#: Where a built pack is staged inside an export directory (restricted-export
#: input; K4 §4.2): ``<export>/inputs/boundary-pack/manifest.json``.
PACK_STAGING_RELPATH = Path("inputs") / "boundary-pack"
PACK_MANIFEST_NAME = "manifest.json"

#: The committed source registry the ingestion gate is read from (fail-closed;
#: ``connectors`` is not an exports dependency — the TOML is data, read with
#: stdlib ``tomllib`` so the check needs no import cycle).
DEFAULT_SOURCES_TOML = (
    Path(__file__).resolve().parents[3] / "connectors/src/connectors/data/sources.toml"
)

_LAYER_FORMATS = frozenset({"geojson", "shapefile-zip", "gazetteer-txt"})
_LAYER_ROLES = frozenset({"us_containment", "us_display", "us_names", "non_us", "national"})
_REGISTRY_LEVELS = frozenset({"country", "state_province", "county", "municipality"})


class BoundaryPackError(Exception):
    """A fail-closed boundary-pack error — spec, gate, input or verification."""


@dataclass(frozen=True)
class PackLayer:
    """One declared pack layer: the upstream artifact + its registry role."""

    id: str
    source: str
    file: str
    format: str
    role: str
    vintage: str
    level: str  # "" when the layer feeds no registry rows (display/names)
    key_scheme: str  # "" when no jkey is minted from this layer
    fields: dict[str, Any]
    rollup: dict[str, Any] | None
    note: str

    @property
    def mints_rows(self) -> bool:
        """Whether registry rows are minted from this layer."""
        return bool(self.level) and bool(self.key_scheme)


@dataclass(frozen=True)
class PackSpec:
    """The parsed ``sig.boundary-pack/1`` spec file (declared data, not code)."""

    pack_id: str
    vintages: dict[str, str]
    layers: tuple[PackLayer, ...]
    registry: dict[str, Any]

    def layer(self, layer_id: str) -> PackLayer:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(layer_id)


def load_spec(path: Path | str) -> PackSpec:
    """Parse a ``sig.boundary-pack/1`` spec; fail closed on every malformed field."""
    path = Path(path)
    if not path.exists():
        raise BoundaryPackError(f"pack spec not found: {path}")
    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    pack = doc.get("pack")
    if not isinstance(pack, dict) or pack.get("schema") != PACK_SCHEMA:
        raise BoundaryPackError(f"{path}: [pack].schema must be {PACK_SCHEMA!r}")
    pack_id = str(pack.get("pack_id") or "")
    if not pack_id:
        raise BoundaryPackError(f"{path}: [pack].pack_id is required")
    vintages = dict(pack.get("vintages") or {})
    if not vintages or not all(isinstance(v, str) and v for v in vintages.values()):
        raise BoundaryPackError(f"{path}: [pack].vintages must be a non-empty string map")

    registry = dict(doc.get("registry") or {})
    if not isinstance(registry.get("attribution"), list) or not registry["attribution"]:
        raise BoundaryPackError(f"{path}: [registry].attribution must be a non-empty list")
    if not isinstance(registry.get("standing_note"), str):
        raise BoundaryPackError(f"{path}: [registry].standing_note must be a string (D-K4-2)")
    if registry.get("license") != "CC-BY-4.0":
        raise BoundaryPackError(f"{path}: [registry].license must be CC-BY-4.0")

    layers: list[PackLayer] = []
    seen: set[str] = set()
    for i, raw in enumerate(doc.get("layers") or []):
        if not isinstance(raw, dict):
            raise BoundaryPackError(f"{path}: layers[{i}] is not a table")
        try:
            layer = PackLayer(
                id=str(raw["id"]),
                source=str(raw["source"]),
                file=str(raw["file"]),
                format=str(raw["format"]),
                role=str(raw["role"]),
                vintage=str(raw["vintage"]),
                level=str(raw.get("level") or ""),
                key_scheme=str(raw.get("key_scheme") or ""),
                fields=dict(raw.get("fields") or {}),
                rollup=(dict(raw["rollup"]) if raw.get("rollup") is not None else None),
                note=str(raw.get("note") or ""),
            )
        except KeyError as exc:
            raise BoundaryPackError(f"{path}: layers[{i}] lacks {exc}") from exc
        if layer.id in seen:
            raise BoundaryPackError(f"{path}: duplicate layer id {layer.id!r}")
        seen.add(layer.id)
        if layer.format not in _LAYER_FORMATS:
            raise BoundaryPackError(
                f"{path}: layer {layer.id!r} format {layer.format!r}; "
                f"must be one of {sorted(_LAYER_FORMATS)}"
            )
        if layer.role not in _LAYER_ROLES:
            raise BoundaryPackError(
                f"{path}: layer {layer.id!r} role {layer.role!r}; "
                f"must be one of {sorted(_LAYER_ROLES)}"
            )
        if layer.level and layer.level not in _REGISTRY_LEVELS:
            raise BoundaryPackError(
                f"{path}: layer {layer.id!r} level {layer.level!r}; "
                f"must be one of {sorted(_REGISTRY_LEVELS)} or empty"
            )
        if layer.mints_rows and not layer.fields.get("name"):
            raise BoundaryPackError(
                f"{path}: layer {layer.id!r} mints rows but fields.name is unset"
            )
        if layer.vintage not in set(vintages.values()):
            raise BoundaryPackError(
                f"{path}: layer {layer.id!r} vintage {layer.vintage!r} is not a "
                f"declared [pack].vintages value"
            )
        layers.append(layer)
    if not layers:
        raise BoundaryPackError(f"{path}: no [[layers]] declared")
    return PackSpec(pack_id=pack_id, vintages=vintages, layers=tuple(layers), registry=registry)


def gate_violations(spec: PackSpec, sources_toml: Path | str | None = None) -> list[str]:
    """The fail-closed ingestion check (SIG-INGEST-028; HG-03 is the operator's act).

    Returns one message per declared layer whose ``source`` is absent from the
    registry or carries ``ingestion_permitted`` not-true. Building a pack from
    bytes that could not lawfully have been captured is exactly the hole the
    gate exists for — the check runs *before* any file is read.
    """
    path = Path(sources_toml) if sources_toml is not None else DEFAULT_SOURCES_TOML
    if not path.exists():
        raise BoundaryPackError(f"source registry not found: {path}")
    registry = tomllib.loads(path.read_text(encoding="utf-8")).get("sources", {})
    out: list[str] = []
    for layer in spec.layers:
        row = registry.get(layer.source)
        if row is None:
            out.append(f"layer {layer.id!r}: source {layer.source!r} is not a registry row")
            continue
        if row.get("ingestion_permitted") is not True:
            out.append(
                f"layer {layer.id!r}: source {layer.source!r} is not "
                "ingestion_permitted — the HG-03 flip is the operator's act "
                "(fail closed; fixture inputs need --fixture)"
            )
    return out


def _spatial(con: Any) -> None:
    """Load the DuckDB spatial extension or refuse — never a degraded read."""
    try:
        con.execute("LOAD spatial")
    except Exception as exc:  # noqa: BLE001 — surface the load failure verbatim
        try:
            con.execute("INSTALL spatial")
            con.execute("LOAD spatial")
            return
        except Exception:
            pass
        raise BoundaryPackError(
            "duckdb spatial extension is required to read/write GeoParquet and "
            f"could not be loaded: {exc} — no stub pack is emitted"
        ) from exc


def _resolve_input(layer: PackLayer, inputs_dir: Path, tmp: Path) -> Path:
    """Resolve a layer's declared input file inside the captured-inputs dir.

    ``shapefile-zip``/zipped gazetteer inputs are extracted to ``tmp`` and the
    first ``.shp``/text member returned. A declared file that is absent raises
    — the pack never silently drops a layer.
    """
    direct = inputs_dir / layer.file
    if direct.exists():
        if direct.suffix == ".zip":
            return _unzip(direct, tmp / layer.id, layer)
        return direct
    # A directory-shaped input (the already-extracted capture) resolves too.
    cand_dir = inputs_dir / Path(layer.file).stem
    if cand_dir.is_dir():
        return _pick_member(cand_dir, layer)
    raise BoundaryPackError(
        f"layer {layer.id!r}: declared input {layer.file!r} not found in {inputs_dir}"
    )


def _unzip(zpath: Path, dest: Path, layer: PackLayer) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(dest)
    return _pick_member(dest, layer)


def _pick_member(directory: Path, layer: PackLayer) -> Path:
    """Pick the readable member of an extracted/flat input directory."""
    suffix = {"shapefile-zip": ".shp", "gazetteer-txt": ".txt", "geojson": ".geojson"}[layer.format]
    members = sorted(directory.rglob(f"*{suffix}"))
    if not members:
        raise BoundaryPackError(f"layer {layer.id!r}: no *{suffix} member under {directory}")
    return members[0]


def _quoted(path: Path) -> str:
    """A single-quoted SQL literal for a filesystem path."""
    return "'" + str(path).replace("'", "''") + "'"


def _read_layer_sql(layer: PackLayer, path: Path) -> str:
    """The SELECT that lands a layer's rows with a canonical ``geom`` column."""
    q = _quoted(path)
    if layer.format in ("geojson", "shapefile-zip"):
        return f"SELECT * REPLACE (geom AS geom) FROM ST_Read({q})"
    # gazetteer-txt: tab- or pipe-delimited with a header; geometry is the
    # declared internal point (INTPTLONG/INTPTLAT → ST_Point, lon first).
    fields = layer.fields
    lon, lat = str(fields["intptlong"]), str(fields["intptlat"])
    return (
        f'SELECT *, ST_Point(CAST("{lon}" AS DOUBLE), '
        f'CAST("{lat}" AS DOUBLE)) AS geom '
        f"FROM read_csv({q}, delim='\\t', header=true, all_varchar=true, "
        f"null_padding=true, union_by_name=true)"
    )


def build_pack(
    spec: PackSpec,
    inputs_dir: Path | str,
    out_dir: Path | str,
    *,
    sources_toml: Path | str | None = None,
    fixture_inputs: bool = False,
) -> dict[str, Any]:
    """Build the GeoParquet pack + its ``sig.boundary-pack/1`` manifest.

    ``fixture_inputs=True`` bypasses the ingestion gate check and records
    ``gate.mode = "fixture-bypass"`` in the manifest — a fixture pack is never
    passable for a captured one (the staged ``inputs/boundary-pack`` copy is
    verified file-by-file before ``boundaries_root`` is trusted anyway).
    """
    import duckdb

    inputs_dir = Path(inputs_dir)
    out_dir = Path(out_dir)
    if not inputs_dir.is_dir():
        raise BoundaryPackError(f"inputs dir not found: {inputs_dir}")

    if fixture_inputs:
        gate_mode: dict[str, str] = {
            "mode": "fixture-bypass",
            "note": (
                "inputs are declared stand-ins, not captured evidence; the "
                "ingestion gate check was bypassed for this build (P35.17 "
                "fixtures exercise the machinery, never the flips)"
            ),
        }
    else:
        violations = gate_violations(spec, sources_toml)
        if violations:
            raise BoundaryPackError(
                "boundary-pack build refused by the ingestion gate:\n  " + "\n  ".join(violations)
            )
        gate_mode = {
            "mode": "enforced",
            "note": (
                "every declared layer's source carried ingestion_permitted=true "
                "in the committed source registry at build time"
            ),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    _spatial(con)

    layers_out: list[dict[str, Any]] = []
    roots: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        for layer in spec.layers:
            src = _resolve_input(layer, inputs_dir, tmp)
            select = _read_layer_sql(layer, src)
            dest = out_dir / f"{layer.id}.parquet"
            try:
                con.execute(f"COPY ({select}) TO {_quoted(dest)} (FORMAT PARQUET)")
                rows = con.execute(
                    f"SELECT count(*) FROM read_parquet({_quoted(dest)})"
                ).fetchone()[0]
            except Exception as exc:  # noqa: BLE001 — the layer error must name the layer
                raise BoundaryPackError(
                    f"layer {layer.id!r} read/convert failed ({layer.format} "
                    f"from {src.name}): {exc}"
                ) from exc
            digest = sha256_hex(dest.read_bytes())
            roots[f"{layer.id}.parquet"] = digest
            layers_out.append(
                {
                    "id": layer.id,
                    "source": layer.source,
                    "file": layer.file,
                    "path": dest.name,
                    "sha256": digest,
                    "bytes": dest.stat().st_size,
                    "rows": rows,
                    "vintage": layer.vintage,
                    "role": layer.role,
                    "level": layer.level or None,
                }
            )

    manifest: dict[str, Any] = {
        "schema": PACK_SCHEMA,
        "pack_id": spec.pack_id,
        "vintages": dict(sorted(spec.vintages.items())),
        "gate": gate_mode,
        "layers": layers_out,
        "boundaries_root": boundaries_root({r["path"]: r["sha256"] for r in layers_out}),
    }
    (out_dir / PACK_MANIFEST_NAME).write_bytes(canonical_json(manifest))
    return manifest


def boundaries_root(file_digests: dict[str, str]) -> str:
    """The content root over the pack's ``{relpath: sha256}`` map — the value
    descriptor v2 binds as ``boundaries_root`` (K4 §4.2)."""
    return sha256_hex(canonical_json(dict(sorted(file_digests.items()))))


def read_manifest(pack_dir: Path | str) -> dict[str, Any]:
    """Read + shape-check a ``sig.boundary-pack/1`` manifest."""
    path = Path(pack_dir) / PACK_MANIFEST_NAME
    if not path.exists():
        raise BoundaryPackError(f"no pack manifest at {path}")
    import json

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != PACK_SCHEMA:
        raise BoundaryPackError(
            f"{path}: schema {manifest.get('schema')!r}; expected {PACK_SCHEMA!r}"
        )
    if not isinstance(manifest.get("layers"), list) or not manifest["layers"]:
        raise BoundaryPackError(f"{path}: layers must be a non-empty list")
    if not isinstance(manifest.get("boundaries_root"), str):
        raise BoundaryPackError(f"{path}: boundaries_root must be a string")
    return manifest


def verify_pack(pack_dir: Path | str) -> list[str]:
    """Re-hash every declared file + recompute ``boundaries_root``.

    Returns the list of violations (empty = verified). Any missing file,
    digest mismatch, or root drift is reported — the descriptor never binds a
    pack that fails here.
    """
    pack_dir = Path(pack_dir)
    failures: list[str] = []
    try:
        manifest = read_manifest(pack_dir)
    except BoundaryPackError as exc:
        return [str(exc)]
    actual: dict[str, str] = {}
    for entry in manifest["layers"]:
        path = pack_dir / str(entry.get("path") or "")
        if not path.exists():
            failures.append(f"manifest layer {entry.get('id')!r}: {path.name} missing")
            continue
        digest = sha256_hex(path.read_bytes())
        actual[path.name] = digest
        if digest != entry.get("sha256"):
            failures.append(f"manifest layer {entry.get('id')!r}: {path.name} sha256 drifted")
    if not failures and boundaries_root(actual) != manifest["boundaries_root"]:
        failures.append("boundaries_root does not recompute over the staged files")
    return failures


def derive_boundaries_root(export_dir: Path | str) -> str | None:
    """The v2 descriptor's ``boundaries_root`` from the staged pack.

    ``<export>/inputs/boundary-pack/manifest.json`` is the seam (K4 §4.2's
    "restricted export inputs"). Absent → ``None`` (declared-empty). Present →
    the pack is fully verified and the *recomputed* root is returned, so a
    tampered or inconsistent staging fails the release, never signs it.
    """
    pack_dir = Path(export_dir) / PACK_STAGING_RELPATH
    if not (pack_dir / PACK_MANIFEST_NAME).exists():
        return None
    failures = verify_pack(pack_dir)
    if failures:
        raise BoundaryPackError(
            "the staged boundary pack fails verification — refusing to bind "
            "boundaries_root to it:\n  " + "\n  ".join(failures)
        )
    manifest = read_manifest(pack_dir)
    digests = {
        str(e["path"]): sha256_hex((pack_dir / str(e["path"])).read_bytes())
        for e in manifest["layers"]
    }
    return boundaries_root(digests)


def copy_pack(pack_dir: Path | str, export_dir: Path | str) -> Path:
    """Stage a built pack into ``<export>/inputs/boundary-pack/`` (the
    restricted-export-input seam). Returns the staging dir."""
    pack_dir = Path(pack_dir)
    dest = Path(export_dir) / PACK_STAGING_RELPATH
    dest.mkdir(parents=True, exist_ok=True)
    for f in sorted(pack_dir.iterdir()):
        if f.name == PACK_MANIFEST_NAME or f.suffix == ".parquet":
            shutil.copy2(f, dest / f.name)
    return dest
