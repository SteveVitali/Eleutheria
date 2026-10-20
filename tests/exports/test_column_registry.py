# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.39 (TX-10a, SIG-TRANSP-016/017, J3 §6.5–6.6): the exporter column
registry, its generated documents and the linked-metadata surface.

  - the registry covers every emitted column and fails closed on an
    undeclared one (assert_documented) or an unregistered row-bearing
    artifact path (assert_path_documented);
  - enum/slot entries resolve from the generated LinkML schema + vocabulary
    registry — a cited authority that is absent raises, never silently
    degrades to a hand-copied list;
  - ``dictionary.json`` + per-resource ``schemas/*.tableschema.json`` +
    Frictionless ``datapackage.json`` (v2 fields) + DCAT ``catalog.jsonld``
    emit with every bundle;
  - the spine export regenerates those over the FULL artifact set and adds
    ``provenance.jsonld``;
  - activation stamps the publication-bound descriptors —
    ``releases/<pub>/datapackage.json`` + ``catalog.jsonld`` and the
    ``releases/catalog.jsonld`` series catalog;
  - the archive pages link the metadata with ``<link rel="alternate"
    type="application/ld+json">`` — never inline JSON-LD (D-J3-7).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from exports.manifest import BuildSpec
from policy.rights import RightsRecord

from exports import bundle as B
from exports import column_registry as CR
from exports import compartments as C
from exports import dcat

_SPEC = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1")


def _rr(source_id: str, spdx: str) -> RightsRecord:
    return RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution=f"attr:{source_id}",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 1, 1),
    )


RIGHTS = [_rr("sig", "CC-BY-4.0"), _rr("osm", "ODbL-1.0")]


def _simple_bundle() -> B.Bundle:
    devices = C.ExportTable(
        "devices",
        (
            C.ExportRow(
                "osm",
                {"subject_id": "d1", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
            ),
        ),
        kind="geo",
        compartment="osm_physical",
    )
    claims = C.ExportTable(
        "claims", (C.ExportRow("sig", {"subject_id": "e1", "predicate": "operates"}),)
    )
    return B.build_bundle(_SPEC, [devices, claims], RIGHTS)


# --------------------------------------------------------------------------- #
# Registry completeness + the fail-closed gates                               #
# --------------------------------------------------------------------------- #


def test_every_registered_resource_fully_documents_its_columns() -> None:
    """Every ColumnSpec carries the J3 §6.5 documentation set — description,
    type, nullability (the booleans are defaults but the field is required)."""
    registry = CR.column_registry()
    assert registry, "the registry is never empty"
    for name, spec in registry.items():
        assert spec.columns, f"resource {name} declares no columns"
        for col in spec.columns:
            assert col.description.strip(), f"{name}.{col.name}: empty description"
            assert col.dtype, f"{name}.{col.name}: empty dtype"


def test_every_emitted_column_is_declared() -> None:
    """The union of columns the bundle's serialisations can emit must all be
    registered — this is the property ``assert_documented`` enforces."""
    bundle = _simple_bundle()
    for path, data in bundle.artifact_bytes.items():
        res = CR.resource_for_path(path)
        if res is None:
            continue
        text = data.decode("utf-8", errors="ignore")
        if path.endswith(".csv"):
            CR.assert_documented(res, text.splitlines()[0].split(","))
        elif path.endswith(".jsonl"):
            for line in text.splitlines():
                row = json.loads(line)
                emitted = set(row)
                if "_rights" in row:
                    emitted.update(f"rights_{k}" for k in row["_rights"])
                CR.assert_documented(res, emitted)
        elif path.endswith((".geojson", ".json")):
            doc = json.loads(text)
            feats = doc.get("features") if isinstance(doc, dict) else None
            if feats:
                for f in feats:
                    CR.assert_documented(res, set(f.get("properties") or {}))
            else:
                rows = doc if isinstance(doc, list) else (doc.get("rows") or [])
                for row in rows if isinstance(rows, list) else []:
                    if isinstance(row, dict):
                        CR.assert_documented(res, set(row))


def test_undocumented_column_fails_the_build() -> None:
    """A table emitting a column no spec declares fails the build — the
    registry is a gate, not a linter."""
    rogue = C.ExportTable(
        "claims",
        (C.ExportRow("sig", {"subject_id": "e1", "predicate": "operates", "bogus": 1}),),
    )
    with pytest.raises(CR.UndocumentedColumnError):
        B.build_bundle(_SPEC, [rogue], RIGHTS)


def test_unregistered_table_fails_the_build() -> None:
    """A resource name the registry does not know is a failure — a table the
    registry does not know IS undocumented."""
    unknown = C.ExportTable("mystery_table", (C.ExportRow("sig", {"a": 1}),))
    with pytest.raises(CR.UnregisteredResourceError):
        B.build_bundle(_SPEC, [unknown], RIGHTS)


def test_unregistered_row_artifact_path_fails() -> None:
    """A row-bearing artifact path that maps to no registered resource fails
    the manifest gate."""
    with pytest.raises(CR.UnregisteredResourceError):
        CR.assert_path_documented("sig_graph/no_such_table.jsonl")
    assert CR.assert_path_documented("manifest.json") is None  # a document — exempt
    assert CR.assert_path_documented("sig_graph/sites.jsonl") == "sites"
    assert CR.assert_path_documented("osm_physical/devices.geojson") == "devices"


# --------------------------------------------------------------------------- #
# Enum / slot resolution from the generated ontology                           #
# --------------------------------------------------------------------------- #


def test_enum_values_resolve_from_the_generated_schema() -> None:
    """``linkml:enum:<Name>`` resolves permissible values from the generated
    JSON Schema — never a hand-copied list."""
    spec = next(
        c for c in CR.resource_columns("sites") if (c.enum_source or "").startswith("linkml:enum:")
    )
    values = CR.enum_values(spec)
    assert values, f"{spec.name}: linkml:enum source resolved to nothing"
    generated = json.loads(
        Path(
            CR._GENERATED_SCHEMA  # noqa: SLF001 — the test asserts the resolution seam
        ).read_text(encoding="utf-8")
    )
    enum_name = (spec.enum_source or "").split(":", 2)[2]
    expected = {str(v) for v in generated["$defs"][enum_name]["enum"]}
    assert expected <= set(values)


def test_skos_values_resolve_from_the_vocab_registry() -> None:
    """``linkml:skos:<scheme>`` resolves slugs from the generated vocabulary
    summary (the technology scheme)."""
    spec = CR.ColumnSpec("technology", "demo", enum_source="linkml:skos:technology")
    values = CR.enum_values(spec)
    assert values is not None and "alpr-fixed" in values


def test_a_missing_enum_authority_raises() -> None:
    """A cited enum the generated schema does not define fails — no silent
    fallback to a hand-maintained list."""
    spec = CR.ColumnSpec("x", "demo", enum_source="linkml:enum:NoSuchEnum")
    with pytest.raises(CR.ColumnRegistryError):
        CR.enum_values(spec)


def test_export_declared_values_stand_alone() -> None:
    spec = CR.ColumnSpec("status", "demo", enum_source="export:demo.X", declared_values=("a", "b"))
    assert CR.enum_values(spec) == ("a", "b")


# --------------------------------------------------------------------------- #
# Table Schema + dictionary.json                                              #
# --------------------------------------------------------------------------- #


def test_table_schema_document_shape() -> None:
    schema = CR.table_schema("sites")
    assert schema["$schema"] == CR.TABLESCHEMA_PROFILE
    assert schema["name"] == "sites"
    names = [f["name"] for f in schema["fields"]]
    assert "entity_id" in names and "rights_license" in names  # spec + rights block
    subject = next(f for f in schema["fields"] if f["name"] == "entity_id")
    assert subject["constraints"]["required"] is True
    enum_field = next(f for f in schema["fields"] if f.get("constraints", {}).get("enum"))
    assert enum_field.get("enum_source")


def test_dictionary_document_shape() -> None:
    doc = CR.dictionary_document(
        build_spec=_SPEC,
        resources=["sites"],
        paths_by_resource={"sites": ["sig_graph/sites.csv"]},
        documents=[{"path": "manifest.json", "media_type": "application/json"}],
    )
    assert doc["schema"] == CR.DICTIONARY_SCHEMA
    assert doc["ontology"]["sha256"] and doc["ontology"]["schema_file"]
    res = doc["resources"][0]
    assert res["name"] == "sites" and res["table_schema"] == "schemas/sites.tableschema.json"
    assert all(c["description"] for c in res["columns"])


# --------------------------------------------------------------------------- #
# Bundle-level emission                                                        #
# --------------------------------------------------------------------------- #


def test_the_bundle_emits_the_metadata_set() -> None:
    """dictionary.json + per-resource Table Schemas + datapackage.json +
    catalog.jsonld land in every bundle — the NEW-11 artifact set."""
    bundle = _simple_bundle()
    paths = {a.path for a in bundle.manifest.artifacts}
    assert "dictionary.json" in paths
    assert "datapackage.json" in paths
    assert "catalog.jsonld" in paths
    assert "schemas/devices.tableschema.json" in paths
    assert "schemas/claims.tableschema.json" in paths
    # The metadata set is manifest-listed with digests — verifiable bytes.
    import hashlib

    meta = {a.path: a for a in bundle.manifest.artifacts}
    for p in ("dictionary.json", "datapackage.json", "catalog.jsonld"):
        assert meta[p].sha256 and meta[p].compartment == "metadata"
        assert hashlib.sha256(bundle.artifact_bytes[p]).hexdigest() == meta[p].sha256


def test_datapackage_v2_fields() -> None:
    """The descriptor carries the v2 fields: per-resource schema links,
    sources, licenses and the release version."""
    bundle = _simple_bundle()
    dp = json.loads(bundle.artifact_bytes["datapackage.json"])
    assert dp["$schema"] == "https://datapackage.org/profiles/2.0/datapackage.json"
    assert dp["version"] == _SPEC.release_id()
    assert dp["licenses"]
    for res in dp["resources"]:
        assert res.get("schema", "").startswith("schemas/")
        assert "sources" in res
        assert res["hash"].startswith("sha256:")


def test_catalog_jsonld_shape() -> None:
    """DCAT 3: one Dataset per compartment, Distribution per artifact with
    downloadURL/mediaType/byteSize/spdx checksum; the dataset's
    wasGeneratedBy names the export run."""
    bundle = _simple_bundle()
    cat = json.loads(bundle.artifact_bytes["catalog.jsonld"])
    ctx = cat["@context"]
    assert ctx["dcat"] == "http://www.w3.org/ns/dcat#"
    datasets = {d["@id"].split("/")[-1]: d for d in cat["dcat:dataset"]}
    assert "osm_physical" in datasets and "sig_graph" in datasets
    ds = datasets["osm_physical"]
    assert ds["dcat:inSeries"]["@id"] == dcat.SERIES_IRI
    assert ds["dct:accessRights"]["@id"].endswith("/public")
    assert ds["prov:wasGeneratedBy"]["@id"].startswith(dcat.SIG_PROV)
    dist = ds["dcat:distribution"][0]
    assert dist["dcat:downloadURL"]["@id"].startswith(dcat.CANONICAL_ORIGIN)
    assert dist["spdx:checksum"]["spdx:checksumValue"]
    assert dist["dcat:byteSize"] > 0


# --------------------------------------------------------------------------- #
# Release-layer activation metadata                                            #
# --------------------------------------------------------------------------- #


def _write_export(root: Path) -> Path:
    """A minimal real-shaped export for build_release (same shape the release
    suite stages)."""
    comp = "sig_graph"
    (root / comp).mkdir(parents=True, exist_ok=True)
    (root / "web").mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "entity_id": "e1",
            "subject_id": "e1",
            "geometry": {"coordinates": [-97.5, 35.46], "type": "Point"},
            "jurisdiction": "oklahoma-city",
            "label": "Site sig 0",
            "n_observation_claims": 1,
            "n_sources": 1,
            "point_status": "resolved",
            "precision": "full_precision",
            "rights_id": "r1",
            "source_id": "src_a",
            "spdx": "CC-BY-4.0",
            "tier": 0,
        }
    ]
    (root / comp / "sites.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    claims = [
        {
            "claim_id": "c1",
            "entity_id": "e1",
            "predicate_id": "camera_latitude",
            "observed_at": "2026-05-01",
            "source_id": "src_a",
            "evidence": [],
        }
    ]
    (root / comp / "record_claims.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in claims), encoding="utf-8"
    )
    (root / "web" / "evidence.json").write_text(
        json.dumps({"artifacts": [], "claim_views": []}), encoding="utf-8"
    )
    (root / "web" / "dossiers.json").write_text(json.dumps([]), encoding="utf-8")
    manifest = {
        "artifacts": [
            {
                "path": f"{comp}/sites.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "x",
                "byte_size": 1,
                "media_type": "application/json",
            },
            {
                "path": f"{comp}/record_claims.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "x",
                "byte_size": 1,
                "media_type": "application/json",
            },
        ],
        "concept_id": "c1",
        "content_key": "k1",
        "release_id": "sig-2026-09-27-test",
        "reproducibility_inputs": {
            "as_of_belief": "2026-09-27",
            "as_of_snapshot": "2026-09-27",
            "resolver_version": "0.1.0+g00000000",
            "ruleset_version": "p27.3/1.0.0",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_activation_emits_the_publication_metadata(tmp_path: Path) -> None:
    """``releases/<pub>/datapackage.json`` + ``catalog.jsonld`` and the
    series catalog land at activation — ``version`` = the publication id,
    ``created``/``issued`` = the activation instant."""
    from exports.release import activate, build_release

    export = _write_export(tmp_path / "export")
    built = build_release(export, tmp_path / "rel", renderer_revision="abcd" * 16)
    registry = tmp_path / "registry"
    when = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    receipt = activate(registry, built.out_dir, now=when)
    pub = receipt["publication_id"]
    staged = registry / "staged"

    dp = json.loads((staged / f"releases/{pub}/datapackage.json").read_bytes())
    assert dp["version"] == pub
    assert dp["created"] == when.isoformat()
    assert dp["$schema"] == "https://datapackage.org/profiles/2.0/datapackage.json"

    cat = json.loads((staged / f"releases/{pub}/catalog.jsonld").read_bytes())
    assert cat["@type"] == "dcat:Dataset"
    assert cat["dcat:inSeries"]["@id"] == dcat.SERIES_IRI
    assert cat["dct:issued"] == when.isoformat()

    series = json.loads((staged / "releases/catalog.jsonld").read_bytes())
    kinds = {d.get("@type") for d in series["dcat:dataset"]}
    assert "dcat:DatasetSeries" in kinds and "dcat:Dataset" in kinds
    member = next(d for d in series["dcat:dataset"] if d.get("@id", "").endswith(f"/{pub}"))
    assert member["dcat:version"] == pub


def test_landing_pages_link_the_catalog_never_inline_it(tmp_path: Path) -> None:
    """D-J3-7: the archive pages carry ``<link rel="alternate"
    type="application/ld+json">`` to the series catalog — the JSON-LD itself
    never appears inline."""
    from exports.release import build_release

    export = _write_export(tmp_path / "export")
    built = build_release(export, tmp_path / "rel", renderer_revision="abcd" * 16)
    landing = (built.out_dir / f"releases/{built.publication_id}/index.html").read_text(
        encoding="utf-8"
    )
    assert 'rel="alternate" type="application/ld+json"' in landing
    assert "releases/catalog.jsonld" in landing
    assert 'type="application/ld+json">' not in landing.replace(
        'rel="alternate" type="application/ld+json"', ""
    )
