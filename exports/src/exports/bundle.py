# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bulk-export orchestrator: build a versioned, licence-computed release (§38).

:func:`build_bundle` is the one code path that turns a :class:`~exports.manifest.BuildSpec`
plus a set of :class:`~exports.compartments.ExportTable`s into a complete release:

1. **Place every table in its licence compartment** (SIG-LIC-004a) — the licence is
   *computed* from constituent rights, and an incompatible mix **fails the build**
   here (SIG-EXPORT-004 / SIG-LIC-010).
2. **Serialise each table in every §38.1 format**, writing files under a
   compartment-named directory so the ODbL layer and the CC-BY graph are physically
   separate files (SIG-EXPORT-005), each row carrying its rights provenance
   (SIG-EXPORT-006).
3. **Publish the identifier crosswalk** as its own prominent artifact under the most
   permissive licence its constituents allow (SIG-EXPORT-007).
4. **Wrap tabular resources as a Frictionless Data Package and evidence as an RO-Crate**
   (SIG-EXPORT-002), and **emit a manifest with a checksum for every artifact**
   (SIG-EXPORT-001).

The whole function is a **pure function of its inputs**: the same ``BuildSpec`` + tables
produce byte-identical artifacts and the same ``release_id`` (SIG-EXPORT-003). Because
the licence, attribution, and crosswalk are computed with the very functions the read
API uses (``policy.licensing``, ``resolution.crosswalk``), an export and the API agree
by construction rather than by a hand-maintained parallel — "a hand-built export is a
different dataset wearing the same name" (§38.1).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from policy.rights import RightsRecord

from . import compartments as C
from . import downstream, frictionless
from .distribution import DistributionPlan, ObjectStore, plan_distribution
from .formats import FORMATS, formats_for
from .manifest import Artifact, BuildSpec, Manifest, canonical_json

#: The compartment label carried by descriptor artifacts (datapackage / RO-Crate); they
#: are documentation (CC-BY-4.0, SIG-LIC-005), not graph data, and live at the root.
_META_COMPARTMENT = "metadata"
_DESCRIPTOR_LICENSE = "CC-BY-4.0"
#: Where the crosswalk artifacts live — prominently, at their own top-level path
#: (SIG-EXPORT-007), separate from the main dataset compartments.
_CROSSWALK_DIR = "crosswalk"


@dataclass(frozen=True)
class Bundle:
    """A built release: its manifest, every artifact's bytes, and the placement record."""

    build_spec: BuildSpec
    manifest: Manifest
    artifact_bytes: dict[str, bytes]
    placed: tuple[C.PlacedTable, ...] = ()
    crosswalk_license: str | None = None
    evidence_artifacts: tuple[Artifact, ...] = ()
    distribution: DistributionPlan | None = None

    def artifacts(self) -> tuple[Artifact, ...]:
        return self.manifest.artifacts

    def paths_in_compartment(self, compartment: str) -> list[str]:
        return sorted(a.path for a in self.manifest.artifacts if a.compartment == compartment)

    def capabilities(self) -> set[str]:
        """The §38.4 downstream capabilities this bundle provides (SIG-EXPORT-010)."""
        caps: set[str] = set()
        for artifact in self.manifest.artifacts:
            for name, spec in FORMATS.items():
                if artifact.media_type == spec.media_type:
                    caps.add(name)
        if self.crosswalk_license is not None:
            caps.add("crosswalk")
        # The ODbL asset layer served alone (route/privacy class, SIG-EXPORT-011).
        if any(
            a.compartment == "osm_physical"
            and a.media_type in (FORMATS["pmtiles"].media_type, FORMATS["geojson"].media_type)
            for a in self.manifest.artifacts
        ):
            caps.add("odbl_asset_layer")
        return caps

    def validate_portfolio(self, external_capabilities: Iterable[str] = ()) -> None:
        """Assert the §38.4 portfolio serves every downstream class (SIG-EXPORT-010/011).

        ``external_capabilities`` are the capabilities provided by the surrounding
        surfaces this ticket does not own — the P14.1 JSON API (``json_api``,
        ``evidence_links``, ``belief_pinned_permalinks``), the per-jurisdiction slices,
        and the procurement feed (``procurement_feed``, ``ical_rss``) — so the six-class
        check is made against the whole portfolio, not the exports in isolation.
        """
        downstream.assert_all_served(self.capabilities() | set(external_capabilities))
        # SIG-EXPORT-011: the device-alone (route/privacy) and joined-graph (researcher)
        # artifacts must be different files — the ODbL/CC-BY split already guarantees it.
        downstream.assert_separate_serving_artifacts(
            self.paths_in_compartment("osm_physical"), self.paths_in_compartment("sig_graph")
        )

    def write_to(self, out_dir: Path | str) -> Path:
        """Materialise every artifact + the manifest under ``out_dir`` (byte-identical)."""
        root = Path(out_dir)
        for path, data in self.artifact_bytes.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (root / "manifest.json").write_bytes(self.manifest.to_bytes())
        return root


def _write_table_artifacts(
    placed: C.PlacedTable,
    index: Mapping[str, RightsRecord],
    registry: Mapping[str, Any] | None,
    *,
    path_dir: str,
    compartment_label: str,
    license_id: str,
) -> list[tuple[Artifact, bytes]]:
    table = placed.table
    rows = C.enrich_rows(table, index, registry)
    # P35.39 (SIG-TRANSP-016 / J3 §6.5): the fail-closed column gate — every
    # column any serialisation of this table can carry must be declared in the
    # exporter column registry; an undocumented column (or an unregistered
    # resource) fails the build here, before any artifact byte is written.
    from .column_registry import assert_documented

    emitted: set[str] = set()
    for row in rows:
        emitted.update(k for k in row if k != C.RIGHTS_KEY)
        rights = row.get(C.RIGHTS_KEY)
        if isinstance(rights, Mapping):
            emitted.update(f"rights_{k}" for k in rights)
            emitted.add(C.RIGHTS_KEY)
            emitted.add("rights")  # the nested form jsonld/geojson emit
    assert_documented(table.name, emitted)
    # P35.16 (R11-DATA-01, F-322): disclose rows vs distinct entities — the
    # rows are observation-level records, and a licence-conflicted entity
    # splits across compartment files, so `row_count` alone would read as a
    # resolved census. `distinct_entities` counts unique `entity_id`s where
    # the table is entity-bearing (None — not asserted — for tables that
    # carry no entity column).
    entity_ids = {str(row.data["entity_id"]) for row in table.rows if "entity_id" in row.data}
    distinct_entities = len(entity_ids) if entity_ids else None
    out: list[tuple[Artifact, bytes]] = []
    for fmt_name in formats_for(table.kind):
        spec = FORMATS[fmt_name]
        data = spec.writer(rows, geometry_key=table.geometry_key, table_name=table.name)
        path = f"{path_dir}/{table.name}.{spec.extension}"
        out.append(
            (
                Artifact.of(
                    name=f"{table.name}.{spec.extension}",
                    path=path,
                    media_type=spec.media_type,
                    compartment=compartment_label,
                    license=license_id,
                    data=data,
                    row_count=len(table.rows),
                    distinct_entities=distinct_entities,
                ),
                data,
            )
        )
    return out


def build_bundle(
    build_spec: BuildSpec,
    tables: Iterable[C.ExportTable],
    rights: Iterable[RightsRecord],
    *,
    crosswalk: C.ExportTable | None = None,
    registry: Mapping[str, Any] | None = None,
    store: ObjectStore | None = None,
    base_url: str = "",
    cdn_url: str = "",
    mirror_base_urls: Sequence[str] = (),
) -> Bundle:
    """Build a complete, licence-computed, reproducible release (§38).

    Raises :class:`policy.licensing.LicenseIncompatibilityError` /
    :class:`policy.licensing.ExportGateClosed` if any table mixes incompatible regimes or
    cites unpublishable rights — the SIG-EXPORT-004 build gate. When a ``store`` is
    given, an egress-friendly :class:`~exports.distribution.DistributionPlan` is computed
    and shipped as ``distribution.json`` — a metered-egress store fails the build then
    (SIG-EXPORT-008), and the largest artifacts get torrent/IPFS references
    (SIG-EXPORT-009).
    """
    index = C.rights_index(rights)
    tables = list(tables)

    placed = C.place_tables(tables, index, registry)
    C.assert_separated(placed)

    artifacts: list[Artifact] = []
    artifact_bytes: dict[str, bytes] = {}
    evidence_artifacts: list[Artifact] = []
    tabular_artifacts: list[Artifact] = []

    for pt in placed:
        is_evidence = pt.table.kind == "evidence"
        for artifact, data in _write_table_artifacts(
            pt,
            index,
            registry,
            path_dir=pt.compartment,
            compartment_label=pt.compartment,
            license_id=pt.license,
        ):
            artifacts.append(artifact)
            artifact_bytes[artifact.path] = data
            # Tabular resources ship in the Frictionless Data Package; evidence ships in
            # the RO-Crate instead (SIG-EXPORT-002) — the two sets are disjoint.
            if is_evidence:
                evidence_artifacts.append(artifact)
            else:
                tabular_artifacts.append(artifact)

    # --- the crosswalk export (SIG-EXPORT-007): most permissive, prominent, separate ---
    crosswalk_license: str | None = None
    if crosswalk is not None:
        cw_rights = C.table_rights(crosswalk, index)
        crosswalk_license = C.most_permissive_license(cw_rights, registry)
        cw_compartment = C.compartment_for_license(
            crosswalk_license, crosswalk.compartment, registry
        )
        for artifact, data in _write_table_artifacts(
            C.PlacedTable(crosswalk, cw_compartment, crosswalk_license, tuple(cw_rights)),
            index,
            registry,
            path_dir=_CROSSWALK_DIR,
            compartment_label=cw_compartment,
            license_id=crosswalk_license,
        ):
            artifacts.append(artifact)
            artifact_bytes[artifact.path] = data
            tabular_artifacts.append(artifact)

    # --- P35.39 (SIG-TRANSP-016 / J3 §6.5): the registry-generated metadata --
    # a Table Schema per emitted resource, then the dictionary + the DCAT
    # catalog over the whole artifact set. These are ``metadata``-compartment
    # descriptor documents (CC-BY-4.0) like datapackage.json — they describe
    # the data, they are never row-bearing themselves.
    from . import column_registry as CR
    from . import dcat as _dcat

    emitted_resources = sorted({pt.table.name for pt in placed})
    if crosswalk is not None:
        emitted_resources = sorted({*emitted_resources, crosswalk.name})
    # The upstream source ids each resource's rows drew on — honest per-row
    # provenance (``ExportRow.source_id``), the ``resources[].sources`` payload.
    sources_by_table: dict[str, list[str]] = {}
    for pt in placed:
        sources_by_table[pt.table.name] = sorted({r.source_id for r in pt.table.rows})
    if crosswalk is not None:
        sources_by_table[crosswalk.name] = sorted({r.source_id for r in crosswalk.rows})

    for path, data in CR.table_schema_artifacts(emitted_resources).items():
        art = Artifact.of(
            name=Path(path).name,
            path=path,
            media_type="application/json",
            compartment=_META_COMPARTMENT,
            license=_DESCRIPTOR_LICENSE,
            data=data,
        )
        artifacts.append(art)
        artifact_bytes[path] = data

    # --- Frictionless Data Package v2 over the tabular resources (SIG-EXPORT-002) ---
    schema_by_path = {
        a.path: CR.table_schema_path(res)
        for a in tabular_artifacts
        if (res := CR.resource_for_path(a.path)) is not None
    }
    sources_by_path = {
        a.path: sources_by_table.get(res, ())
        for a in tabular_artifacts
        if (res := CR.resource_for_path(a.path)) is not None
    }
    dp = frictionless.data_package(
        tuple(tabular_artifacts),
        build_spec,
        schema_by_path=schema_by_path,
        sources_by_path=sources_by_path,
    )
    dp_artifact = Artifact.of(
        name="datapackage.json",
        path="datapackage.json",
        media_type="application/json",
        compartment=_META_COMPARTMENT,
        license=_DESCRIPTOR_LICENSE,
        data=dp,
    )
    artifacts.append(dp_artifact)
    artifact_bytes[dp_artifact.path] = dp

    # --- RO-Crate over the evidence bundle (SIG-EXPORT-002), if any evidence shipped ---
    if evidence_artifacts:
        crate = frictionless.ro_crate(tuple(evidence_artifacts), build_spec)
        crate_artifact = Artifact.of(
            name="ro-crate-metadata.json",
            path="ro-crate-metadata.json",
            media_type="application/json",
            compartment=_META_COMPARTMENT,
            license=_DESCRIPTOR_LICENSE,
            data=crate,
        )
        artifacts.append(crate_artifact)
        artifact_bytes[crate_artifact.path] = crate

    # --- SIG-EXPORT-011: the ODbL device layer and the CC-BY graph are separate files ---
    odbl_geo = [
        a.path
        for a in artifacts
        if a.compartment == "osm_physical"
        and a.media_type in (FORMATS["pmtiles"].media_type, FORMATS["geojson"].media_type)
    ]
    graph_paths = [a.path for a in artifacts if a.compartment == "sig_graph"]
    downstream.assert_separate_serving_artifacts(odbl_geo, graph_paths)

    # --- egress-friendly distribution plan (SIG-EXPORT-008/009), if a store is given ---
    distribution: DistributionPlan | None = None
    if store is not None:
        # The plan is computed over the manifest built so far; asserting low egress here
        # fails a metered-provider build (SIG-EXPORT-008).
        interim = Manifest(build_spec=build_spec, artifacts=tuple(artifacts))
        distribution = plan_distribution(
            interim,
            store=store,
            base_url=base_url,
            cdn_url=cdn_url,
            mirror_base_urls=mirror_base_urls,
        )
        dist_bytes = canonical_json(distribution.as_json())
        dist_artifact = Artifact.of(
            name="distribution.json",
            path="distribution.json",
            media_type="application/json",
            compartment=_META_COMPARTMENT,
            license=_DESCRIPTOR_LICENSE,
            data=dist_bytes,
        )
        artifacts.append(dist_artifact)
        artifact_bytes[dist_artifact.path] = dist_bytes

    # --- P35.39: dictionary.json + catalog.jsonld over the full artifact set --
    # Every row-bearing path must classify to a registered resource; the
    # documents list carries the rest (descriptors, evidence payloads, the
    # generated schemas). dictionary.json is emitted before catalog.jsonld so
    # the catalog can distribute it; neither lists the other — ordering is by
    # construction, not by hash cycle.
    paths_by_resource: dict[str, list[str]] = {}
    documents: list[dict[str, Any]] = []
    for art in artifacts:
        res = CR.assert_path_documented(art.path)
        if res is None:
            doc: dict[str, Any] = {
                "path": art.path,
                "media_type": art.media_type,
                "compartment": art.compartment,
                "license": art.license,
            }
            if art.schema is not None:
                doc["schema"] = art.schema
            documents.append(doc)
        else:
            paths_by_resource.setdefault(res, []).append(art.path)
    dict_bytes = canonical_json(
        CR.dictionary_document(
            build_spec=build_spec,
            resources=emitted_resources,
            paths_by_resource=paths_by_resource,
            documents=documents,
            sources_by_resource=sources_by_table,
        )
    )
    artifacts.append(
        Artifact.of(
            name="dictionary.json",
            path="dictionary.json",
            media_type="application/json",
            compartment=_META_COMPARTMENT,
            license=_DESCRIPTOR_LICENSE,
            data=dict_bytes,
        )
    )
    artifact_bytes["dictionary.json"] = dict_bytes
    catalog_bytes = _dcat.export_catalog(
        tuple(artifacts),
        release_id=build_spec.release_id(),
        created=build_spec.as_of_snapshot.isoformat(),
        compartments_public={a.compartment for a in artifacts},
    )
    artifacts.append(
        Artifact.of(
            name="catalog.jsonld",
            path="catalog.jsonld",
            media_type="application/ld+json",
            compartment=_META_COMPARTMENT,
            license=_DESCRIPTOR_LICENSE,
            data=catalog_bytes,
        )
    )
    artifact_bytes["catalog.jsonld"] = catalog_bytes

    manifest = Manifest(build_spec=build_spec, artifacts=tuple(artifacts))
    return Bundle(
        build_spec=build_spec,
        manifest=manifest,
        artifact_bytes=artifact_bytes,
        placed=tuple(placed),
        crosswalk_license=crosswalk_license,
        evidence_artifacts=tuple(evidence_artifacts),
        distribution=distribution,
    )


def _crosswalk_specs() -> tuple[Any, ...]:
    """The ``sig_external_crosswalk`` columns — beside the writer (P35.39 /
    SIG-TRANSP-016). The row shape is ``resolution.crosswalk.CrosswalkRow.
    as_dict`` — one scheme/value per SIG id.
    """
    from .column_registry import ColumnSpec as _CS

    return (
        _CS("sig_id", "the SIG entity identifier", nullable=False),
        _CS(
            "scheme",
            "the external identifier scheme the row maps into",
            nullable=False,
            enum_source="export:resolution.crosswalk",
        ),
        _CS("value", "the external identifier value within its scheme", nullable=False),
    )


#: P35.39: the ``sig_external_crosswalk`` resource's column specs.
CROSSWALK_COLUMN_SPECS = _crosswalk_specs()


def crosswalk_table_from_rows(
    rows: Sequence[Mapping[str, Any]], *, source_id: str, name: str = "sig_external_crosswalk"
) -> C.ExportTable:
    """Wrap crosswalk rows (e.g. from ``resolution.crosswalk``) as an ``ExportTable``.

    Every crosswalk row is attributed to ``source_id`` — the registry source whose rights
    govern the crosswalk's publication — so the licence gate and per-row provenance apply
    to the crosswalk exactly as to any other table.
    """
    return C.ExportTable(
        name=name,
        rows=tuple(C.ExportRow(source_id=source_id, data=dict(r)) for r in rows),
        kind="tabular",
    )


def crosswalk_table_from_identifiers(
    entities: Iterable[tuple[str, Iterable[Any]]],
    *,
    source_id: str,
    rights: Iterable[RightsRecord],
    name: str = "sig_external_crosswalk",
) -> C.ExportTable:
    """Build the crosswalk via the canonical ``resolution.crosswalk`` builder (SIG-IDENT-033).

    Uses :func:`resolution.crosswalk.build_sig_external_crosswalk` to produce the
    deterministic SIG↔external rows and routes them through
    :func:`resolution.crosswalk.export_crosswalk`, whose licence gate fails closed on any
    constituent whose rights are undetermined or non-redistributable (SIG-LIC-004) — so
    the crosswalk is produced by exactly the code path that owns it, not re-implemented.
    """
    from resolution.crosswalk import build_sig_external_crosswalk, export_crosswalk

    rows = build_sig_external_crosswalk(entities)
    gated = export_crosswalk(rows, rights=rights)
    return C.ExportTable(
        name=name,
        rows=tuple(C.ExportRow(source_id=source_id, data=r.as_dict()) for r in gated),
        kind="tabular",
    )


__all__ = [
    "Bundle",
    "build_bundle",
    "crosswalk_table_from_rows",
    "crosswalk_table_from_identifiers",
]
