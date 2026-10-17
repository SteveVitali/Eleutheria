# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.17 boundary-pack tests (K4 §4.2, ADR-160; SIG-GEO-008).

The fail-closed chain under test: declared spec → ingestion-gate check →
GeoParquet conversion → ``sig.boundary-pack/1`` manifest → file-by-file
verification → ``boundaries_root`` derivation for descriptor v2. Fixture
inputs are declared stand-ins (``fixture_inputs=True``); the production gate
state is asserted against the committed source registry — both P35.17 sources
must be ``ingestion_permitted=false`` until the operator's HG-03 flips.
"""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest
from boundary_pack_fixtures import (
    build_fixture_pack,
    write_fixture_inputs,
    write_fixture_registry,
    write_fixture_spec,
)
from exports.boundary_pack import BoundaryPackError

from exports import boundary_pack as bp

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None,
    reason="duckdb is required for the boundary-pack build path",
)


@pytest.fixture()
def spec() -> bp.PackSpec:
    return bp.load_spec(bp.PACK_SPEC_RESOURCE_PATH)


@pytest.fixture()
def fx_spec(tmp_path: Path) -> bp.PackSpec:
    return bp.load_spec(write_fixture_spec(tmp_path / "fixture_pack.toml"))


@pytest.fixture()
def fx_pack(tmp_path: Path, fx_spec: bp.PackSpec) -> tuple[Path, dict]:
    return build_fixture_pack(tmp_path, fx_spec)


# --------------------------------------------------------------------------- #
# Spec handling                                                                #
# --------------------------------------------------------------------------- #


def test_production_spec_loads(spec: bp.PackSpec) -> None:
    assert spec.pack_id
    assert {layer.format for layer in spec.layers} <= {
        "geojson",
        "shapefile-zip",
        "gazetteer-txt",
    }
    assert spec.registry["license"] == "CC-BY-4.0"
    assert spec.registry["standing_note"]  # D-K4-2 — one standing note
    assert spec.registry["attribution"]
    # Every layer's vintage must be declared.
    declared = set(spec.vintages.values())
    assert all(layer.vintage in declared for layer in spec.layers)


def test_spec_rejects_wrong_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text(
        '[pack]\nschema = "sig.boundary-pack/0"\npack_id = "x"\n'
        '[pack.vintages]\nv = "v1"\n'
        '[registry]\nlicense = "CC-BY-4.0"\n'
        'attribution = ["a"]\nstanding_note = "n"\n'
        '[[layers]]\nid = "l"\nsource = "s"\nfile = "f.geojson"\n'
        'format = "geojson"\nrole = "national"\nvintage = "v1"\n'
        'level = "country"\nkey_scheme = "iso3166-1"\n'
        '[layers.fields]\nname = "NAME"\n'
    )
    with pytest.raises(BoundaryPackError, match="sig.boundary-pack/1"):
        bp.load_spec(bad)


def test_spec_rejects_unknown_format(tmp_path: Path) -> None:
    bad = tmp_path / "bad2.toml"
    bad.write_text(
        '[pack]\nschema = "sig.boundary-pack/1"\npack_id = "x"\n'
        '[pack.vintages]\nv = "v1"\n'
        '[registry]\nlicense = "CC-BY-4.0"\n'
        'attribution = ["a"]\nstanding_note = "n"\n'
        '[[layers]]\nid = "l"\nsource = "s"\nfile = "f.gpkg"\n'
        'format = "geopackage"\nrole = "national"\nvintage = "v1"\n'
        'level = "country"\nkey_scheme = "iso3166-1"\n'
        '[layers.fields]\nname = "NAME"\n'
    )
    with pytest.raises(BoundaryPackError, match="geopackage"):
        bp.load_spec(bad)


def test_spec_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BoundaryPackError, match="not found"):
        bp.load_spec(tmp_path / "absent.toml")


# --------------------------------------------------------------------------- #
# The ingestion gate (fail closed; HG-03 is the operator's act)                #
# --------------------------------------------------------------------------- #


def test_committed_registry_keeps_p35_17_sources_closed() -> None:
    """P35.17 contract: both boundary sources are registered but NOT flipped —
    the HG-03 decision belongs to the operator (this ticket never flips it)."""
    import tomllib

    registry = tomllib.loads(Path(bp.DEFAULT_SOURCES_TOML).read_text(encoding="utf-8"))["sources"]
    for sid in ("census_gazetteer_tiger", "natural_earth_10m"):
        assert sid in registry, f"{sid} must be a registry row"
        assert registry[sid].get("ingestion_permitted") is not True, (
            f"{sid} must stay ingestion_permitted=false until HG-03 flips it"
        )


def test_gate_blocks_production_spec(spec: bp.PackSpec) -> None:
    violations = bp.gate_violations(spec)
    assert violations, "the un-flipped sources must block a captured-evidence build"
    assert any("census_gazetteer_tiger" in v for v in violations)
    assert any("natural_earth_10m" in v for v in violations)


def test_gate_permits_when_registry_allows(spec: bp.PackSpec, tmp_path: Path) -> None:
    reg = tmp_path / "sources.toml"
    reg.write_text(
        "[sources.census_gazetteer_tiger]\ningestion_permitted = true\n"
        "[sources.natural_earth_10m]\ningestion_permitted = true\n"
    )
    assert bp.gate_violations(spec, reg) == []


def test_gate_reports_denied_fixture_sources(fx_spec: bp.PackSpec, tmp_path: Path) -> None:
    reg = write_fixture_registry(tmp_path / "sources.toml")
    violations = bp.gate_violations(fx_spec, reg)
    assert violations  # fx_* sources are not ingestion_permitted
    assert all("fx_" in v for v in violations)


def test_gate_reports_unregistered_source(fx_spec: bp.PackSpec, tmp_path: Path) -> None:
    reg = tmp_path / "sources.toml"
    reg.write_text("[sources.other]\ningestion_permitted = true\n")
    violations = bp.gate_violations(fx_spec, reg)
    assert any("not a registry row" in v for v in violations)


def test_build_refuses_without_fixture_flag(tmp_path: Path, fx_spec: bp.PackSpec) -> None:
    inputs = write_fixture_inputs(tmp_path / "inputs")
    reg = write_fixture_registry(tmp_path / "sources.toml")
    with pytest.raises(BoundaryPackError, match="ingestion gate"):
        bp.build_pack(fx_spec, inputs, tmp_path / "pack", sources_toml=reg)


def test_build_fixture_records_bypass(fx_pack: tuple[Path, dict]) -> None:
    _out, manifest = fx_pack
    assert manifest["schema"] == "sig.boundary-pack/1"
    assert manifest["gate"]["mode"] == "fixture-bypass"
    assert len(manifest["layers"]) == 10
    assert all(entry["sha256"] for entry in manifest["layers"])
    assert len(manifest["boundaries_root"]) == 64


# --------------------------------------------------------------------------- #
# Build + verify + root                                                        #
# --------------------------------------------------------------------------- #


def test_layer_parquets_carry_geoparquet_metadata(fx_pack: tuple[Path, dict]) -> None:
    out, _manifest = fx_pack
    data = (out / "tiger_state.parquet").read_bytes()
    # GeoParquet 1.x footer block: WKB encoding + primary column declaration.
    assert b'"primary_column":"geom"' in data
    assert b'"encoding":"WKB"' in data


def test_verify_pack_clean(fx_pack: tuple[Path, dict]) -> None:
    assert bp.verify_pack(fx_pack[0]) == []


def test_verify_pack_detects_drift(fx_pack: tuple[Path, dict]) -> None:
    out, _ = fx_pack
    target = out / "tiger_state.parquet"
    target.write_bytes(target.read_bytes() + b"tamper")
    failures = bp.verify_pack(out)
    assert any("tiger_state" in f for f in failures)


def test_verify_pack_detects_missing(fx_pack: tuple[Path, dict]) -> None:
    out, _ = fx_pack
    (out / "ne_admin0.parquet").unlink()
    failures = bp.verify_pack(out)
    assert any("missing" in f for f in failures)


def test_deterministic_rebuild(tmp_path: Path, fx_spec: bp.PackSpec) -> None:
    out1, m1 = build_fixture_pack(tmp_path / "a", fx_spec)
    out2, m2 = build_fixture_pack(tmp_path / "b", fx_spec)
    assert m1["boundaries_root"] == m2["boundaries_root"]
    # The manifest bytes are canonical: identical inputs → identical document.
    assert (out1 / "manifest.json").read_bytes() == (out2 / "manifest.json").read_bytes()


def test_missing_declared_input_refuses(tmp_path: Path, fx_spec: bp.PackSpec) -> None:
    inputs = write_fixture_inputs(tmp_path / "inputs")
    (inputs / "tiger_county.geojson").unlink()
    with pytest.raises(BoundaryPackError, match="tiger_county"):
        bp.build_pack(fx_spec, inputs, tmp_path / "pack", fixture_inputs=True)


# --------------------------------------------------------------------------- #
# Input detection (shapefile-zip / dir-shaped captures)                        #
# --------------------------------------------------------------------------- #


def test_resolve_input_picks_shp_from_zip(tmp_path: Path) -> None:
    import tempfile

    layer = bp.PackLayer(
        id="l",
        source="s",
        file="shape.zip",
        format="shapefile-zip",
        role="national",
        vintage="v1",
        level="",
        key_scheme="",
        fields={},
        rollup=None,
        note="",
    )
    zpath = tmp_path / "shape.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("shape.shp", b"fixture-bytes")
        zf.writestr("shape.dbf", b"fixture-bytes")
    resolved = bp._resolve_input(layer, tmp_path, Path(tempfile.mkdtemp()))
    assert resolved.name == "shape.shp"


def test_resolve_input_picks_from_flat_dir(tmp_path: Path) -> None:
    layer = bp.PackLayer(
        id="l",
        source="s",
        file="shape.zip",
        format="shapefile-zip",
        role="national",
        vintage="v1",
        level="",
        key_scheme="",
        fields={},
        rollup=None,
        note="",
    )
    d = tmp_path / "shape"
    d.mkdir()
    (d / "shape.shp").write_bytes(b"fixture")
    resolved = bp._resolve_input(layer, tmp_path, tmp_path / "tmp")
    assert resolved.name == "shape.shp"


def test_resolve_input_refuses_absent(tmp_path: Path) -> None:
    layer = bp.PackLayer(
        id="l",
        source="s",
        file="absent.zip",
        format="shapefile-zip",
        role="national",
        vintage="v1",
        level="",
        key_scheme="",
        fields={},
        rollup=None,
        note="",
    )
    with pytest.raises(BoundaryPackError, match="not found"):
        bp._resolve_input(layer, tmp_path, tmp_path / "tmp")


# --------------------------------------------------------------------------- #
# Staging + descriptor-v2 seam                                                 #
# --------------------------------------------------------------------------- #


def test_stage_pack_and_derive_root(tmp_path: Path, fx_pack: tuple[Path, dict]) -> None:
    pack_dir, manifest = fx_pack
    export = tmp_path / "export"
    staged = bp.copy_pack(pack_dir, export)
    assert staged == export / "inputs" / "boundary-pack"
    assert (staged / "manifest.json").exists()
    assert bp.derive_boundaries_root(export) == manifest["boundaries_root"]


def test_derive_root_absent_returns_none(tmp_path: Path) -> None:
    assert bp.derive_boundaries_root(tmp_path) is None


def test_derive_root_refuses_tampered(tmp_path: Path, fx_pack: tuple[Path, dict]) -> None:
    pack_dir, _ = fx_pack
    export = tmp_path / "export"
    staged = bp.copy_pack(pack_dir, export)
    f = staged / "cb_500k.parquet"
    f.write_bytes(f.read_bytes() + b"drift")
    with pytest.raises(BoundaryPackError, match="verification"):
        bp.derive_boundaries_root(export)


def test_manifest_roundtrip(fx_pack: tuple[Path, dict]) -> None:
    out, manifest = fx_pack
    loaded = json.loads((out / "manifest.json").read_text())
    assert loaded["schema"] == "sig.boundary-pack/1"
    assert loaded["boundaries_root"] == manifest["boundaries_root"]
    assert bp.read_manifest(out)["pack_id"] == manifest["pack_id"]


# --------------------------------------------------------------------------- #
# Descriptor v2 wiring (REL-01 — boundaries_root binds the verified pack)      #
# --------------------------------------------------------------------------- #


def test_release_derives_root_from_staged_pack(tmp_path: Path, fx_pack: tuple[Path, dict]) -> None:
    from exports import release as rel

    pack_dir, manifest = fx_pack
    export = tmp_path / "export"
    # No staged pack → declared-empty or the explicit argument.
    assert rel._boundaries_root(export, None) is None
    explicit = "ab" * 32
    assert rel._boundaries_root(export, explicit) == explicit
    # A staged pack re-derives (verified) and overrides nothing silently.
    bp.copy_pack(pack_dir, export)
    assert rel._boundaries_root(export, None) == manifest["boundaries_root"]
    assert rel._boundaries_root(export, manifest["boundaries_root"]) == manifest["boundaries_root"]


def test_release_refuses_contradictory_root(tmp_path: Path, fx_pack: tuple[Path, dict]) -> None:
    from exports import release as rel

    pack_dir, _ = fx_pack
    export = tmp_path / "export"
    bp.copy_pack(pack_dir, export)
    with pytest.raises(rel.ReleaseError, match="contradiction"):
        rel._boundaries_root(export, "00" * 32)


def test_release_refuses_tampered_staged_pack(tmp_path: Path, fx_pack: tuple[Path, dict]) -> None:
    from exports import release as rel

    pack_dir, _ = fx_pack
    export = tmp_path / "export"
    staged = bp.copy_pack(pack_dir, export)
    f = staged / "ne_admin1.parquet"
    f.write_bytes(f.read_bytes() + b"x")
    with pytest.raises(rel.ReleaseError):
        rel._boundaries_root(export, None)
