# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.39 (SIG-TRANSP-016, J3 §6.5): the exporter column registry.

One :class:`ColumnSpec` per emitted column — description, Frictionless type,
unit, nullability, and enum source — and one :class:`ResourceSpec` per emitted
tabular/row-stream resource. The spec tuples are declared **beside the writer
that emits them** (``compartments.RIGHTS_BLOCK_SPECS`` beside ``row_rights``,
``placement.PLACEMENT_COLUMN_SPECS`` beside ``sites_columns``, the
``transparency.*_SPECS`` tuples beside each ``*_FIELDS`` allow-list,
``statements.STATEMENT_COLUMN_SPECS`` beside ``statement_row``,
``source_licences.SOURCE_LICENCE_COLUMN_SPECS`` beside ``source_licence_table``,
``shaping``'s spec tuples beside the ``as_json``/``freshness_row`` writers and
``spine_export``'s beside the sites/record-claims/labels/coverage emit seams).
This module only *aggregates* them into :func:`column_registry`.

The gate: :func:`assert_documented` runs at every writer seam; a column a
writer emits that no spec declares **fails the build** (J3 §6.5's verbatim
posture). An artifact path the manifest can classify as row-bearing must
resolve to a registered resource — :func:`resource_for_path` is that
classifier.

Enum and slot metadata is resolved from the generated LinkML schema
(``ontology/generated/jsonschema/sig.schema.json``) and the generated
vocabulary registry — never hand-copied — by :func:`enum_values`; the emitted
dictionary cites the generated tree's version + digest.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]


def __getattr__(name: str) -> Any:
    # ``COLUMN_REGISTRY`` — the contract's name for the aggregated registry —
    # resolves lazily so writer modules can import this module (for
    # ``ColumnSpec``/``assert_documented``) without an import cycle: the
    # registry reads their spec tuples only when first consulted.
    if name == "COLUMN_REGISTRY":
        return column_registry()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


#: The emitted dictionary + Table Schema documents carry this schema id.
DICTIONARY_SCHEMA = "sig.data-dictionary/1"
TABLESCHEMA_PROFILE = "https://datapackage.org/profiles/2.0/tableschema.json"
#: Where per-resource Table Schema artifacts land inside the export.
SCHEMAS_DIR = "schemas"


class ColumnRegistryError(Exception):
    """Base for column-registry failures (fail-closed emit gates)."""


class UndocumentedColumnError(ColumnRegistryError):
    """A writer emitted a column no registry spec declares — the build fails."""


class UnregisteredResourceError(ColumnRegistryError):
    """A row-bearing artifact resolved to no registered resource."""


@dataclass(frozen=True)
class ColumnSpec:
    """One emitted column's declared documentation (J3 §6.5).

    ``dtype`` is the Frictionless Table Schema type (``string``, ``integer``,
    ``number``, ``boolean``, ``array``, ``object``, ``date``, ``datetime``,
    ``any``). ``unit`` names the measured unit where one applies (``seconds``,
    ``bytes``, ``count``). ``enum_source`` names the vocabulary authority —
    ``linkml:enum:<Name>`` resolves permissible values from the generated
    JSON Schema ``$defs``; ``linkml:slot:<name>`` cites the generated slot the
    column derives from; ``linkml:skos:<scheme>`` resolves slugs from the
    generated vocabulary registry; ``export:<module>.<anchor>`` marks a
    writer-declared vocabulary (``declared_values`` carries it);
    ``policy:<source>`` marks a valueset owned by a policy/rights table;
    ``None`` means the column is free-typed.
    """

    name: str
    description: str
    dtype: str = "string"
    nullable: bool = True
    unit: str | None = None
    enum_source: str | None = None
    declared_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ResourceSpec:
    """One emitted tabular/row-stream resource's declared documentation.

    ``rights_block`` marks the bundle-table resources whose rows carry the
    ``compartments.row_rights`` block (``_rights``/``rights`` nested forms and
    the flattened ``rights_*`` columns) — the shared writer-declared spec
    applies to exactly those resources.
    """

    name: str
    title: str
    description: str
    columns: tuple[ColumnSpec, ...]
    kind: str = "table"  # "table" (columnar: fields/columns) or "document"
    schema_id: str | None = None  # the emitted sig.*/N row schema, when one exists
    rights_block: bool = False


# --------------------------------------------------------------------------- #
# The aggregated registry                                                     #
# --------------------------------------------------------------------------- #


def _spec(
    name: str, title: str, description: str, columns: Sequence[ColumnSpec], **kw: Any
) -> ResourceSpec:
    names = [c.name for c in columns]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ColumnRegistryError(f"resource {name!r} declares duplicate columns {dup}")
    return ResourceSpec(
        name=name, title=title, description=description, columns=tuple(columns), **kw
    )


@cache
def column_registry() -> dict[str, ResourceSpec]:
    """The aggregated ``name → ResourceSpec`` registry (built once per process).

    Imports the writer modules lazily so no module that declares its columns
    beside its writer pays an import cycle: the writer modules import *this*
    module for :class:`ColumnSpec`; this module reads their spec tuples only
    when the registry is first consulted.
    """
    from . import bundle as _bundle
    from . import bundle_io as _bio
    from . import placement, shaping, source_licences, statements, transparency
    from . import spine_export as _se

    registry: dict[str, ResourceSpec] = {}

    def reg(spec: ResourceSpec) -> None:
        if spec.name in registry:
            raise ColumnRegistryError(f"duplicate resource registration {spec.name!r}")
        registry[spec.name] = spec

    # The request-surface tables — a ``sig-exports build request.json`` names
    # them; the specs are declared beside ``bundle_io.table_from_json`` (the
    # writer that materialises them). All carry the shared rights block.
    _REQUEST_TITLES = {
        "devices": ("Request devices table", "A request-JSON device/geo table."),
        "claims": ("Request claims table", "A request-JSON claim table."),
        "legal_instruments": (
            "Request legal-instruments table",
            "A request-JSON legal-instrument table (JURIS.2 surface).",
        ),
        "captures": ("Request captures table", "A request-JSON evidence-capture table."),
    }
    for _name, (_title, _desc) in _REQUEST_TITLES.items():
        reg(
            _spec(
                _name,
                _title,
                _desc,
                _bio.REQUEST_RESOURCE_SPECS[_name],
                kind="table",
                rights_block=True,
            )
        )

    reg(
        _spec(
            "sites",
            "Published site observations",
            "One row per (site, source, rights-record) slice: the tier-reduced point "
            "plus the disclosure columns — observation-level records, never a resolved "
            "census (SIG-RECON-058). Emitted per licence compartment in every §38.1 "
            "format; the GeoJSON/PMTiles forms carry the same fields as feature "
            "properties with ``geometry`` as the feature geometry.",
            _se.SITES_COLUMN_SPECS + placement.PLACEMENT_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "jurisdictions",
            "Jurisdiction aggregates",
            "One row per queryable jurisdiction bucket — the named-denominator "
            "aggregate (subjects, geolocated sites, conflicted subjects) including "
            "the honest 'unresolved' bucket.",
            shaping.JURISDICTION_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "coverage",
            "Coverage metrics",
            "One row per §32.5 coverage metric — a counted quantity with a NAMED "
            "denominator and the excluded-class disclosure; ``is_population_total`` "
            "is pinned false (SIG-METRIC-009/010).",
            _se.COVERAGE_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "freshness",
            "Per-source freshness",
            "One row per source: the last successful run and content change, the "
            "volatility-class-relative staleness status, and the not-evaluable "
            "count (SIG-METRIC-006/007).",
            shaping.FRESHNESS_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "sharing_edges",
            "Sharing edges",
            "One row per observed §29.3 sharing edge — subject → partner with the "
            "§12.2 access kind and the backing claim anchor.",
            shaping.SHARING_EDGE_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "sig_external_crosswalk",
            "SIG ↔ external identifier crosswalk",
            "The published identifier crosswalk (SIG-EXPORT-007): each row maps a "
            "SIG entity id to a declared external scheme + value, under the most "
            "permissive licence its constituents allow.",
            _bundle.CROSSWALK_COLUMN_SPECS,
            kind="table",
            rights_block=True,
        )
    )
    reg(
        _spec(
            "record_claims",
            "Record claim anchors",
            "The claim/evidence anchors behind every published site row, one row "
            "per claim per licence compartment — public-safe fields only (never "
            "raw claim literals).",
            _se.RECORD_CLAIMS_COLUMN_SPECS,
            kind="table",
        )
    )
    reg(
        _spec(
            "statements",
            "Published claim statements",
            "The ``sig.statement/1`` per-claim provenance stream — one row per "
            "published claim carrying its binding/capture/upstream/evidence "
            "blocks, emitted per licence compartment.",
            statements.STATEMENT_COLUMN_SPECS,
            kind="table",
            schema_id=statements.STATEMENT_SCHEMA,
        )
    )
    reg(
        _spec(
            "labels",
            "Entity label registry",
            "The ``sig.entity-label/1`` rows — the shared label derivation every "
            "surface reads (K2 §3/L-1), one row per publishable entity per licence "
            "compartment.",
            _se.LABEL_COLUMN_SPECS,
            kind="table",
            schema_id="sig.entity-label/1",
        )
    )
    reg(
        _spec(
            "transparency_runs",
            "Ingestion run records",
            "The ``sig.transparency-runs/1`` stream — one record per executed "
            "ingestion run (timing, outcome, counts, error classes).",
            transparency.RUN_RECORD_SPECS,
            kind="table",
            schema_id=transparency.RUN_RECORD_SCHEMA,
        )
    )
    reg(
        _spec(
            "transparency_captures",
            "Capture records",
            "The ``sig.transparency-captures/1`` stream — one record per evidence "
            "capture (target, retrieval instant, digest, storage tier, S-6-gated "
            "locators).",
            transparency.CAPTURE_RECORD_SPECS,
            kind="table",
            schema_id=transparency.CAPTURE_RECORD_SCHEMA,
        )
    )
    reg(
        _spec(
            "transparency_issues",
            "Integrity issue records",
            "The ``sig.transparency-issues/1`` stream — one record per detected "
            "integrity issue (disappearance, robots change, …).",
            transparency.ISSUE_RECORD_SPECS,
            kind="table",
            schema_id=transparency.ISSUE_RECORD_SCHEMA,
        )
    )
    reg(
        _spec(
            "transparency_freshness",
            "Cadence/freshness records",
            "The ``sig.transparency-freshness/1`` stream — the per-source cadence "
            "evaluation at the release's as-of instant (K9 C-4's two-clocks rule).",
            transparency.FRESHNESS_RECORD_SPECS,
            kind="table",
            schema_id=transparency.FRESHNESS_RECORD_SCHEMA,
        )
    )
    reg(
        _spec(
            "transparency_sources",
            "Source registry rows",
            "The ``sig.source-row/1`` rows inside ``transparency/sources.json`` "
            "— the lane-evidenced registry record per declared source.",
            transparency.SOURCE_RECORD_SPECS,
            kind="table",
            schema_id=transparency.SOURCE_RECORD_SCHEMA,
        )
    )
    reg(
        _spec(
            "source_licence_table",
            "Sources & licences table",
            "The ``sig.source-licence-table/1`` rows inside ``web/sources.json`` — "
            "the per-source licence/attribution aggregation the /sources/ page and "
            "the P36.48 CSV/JSON download share (SIG-TRANSP-033).",
            source_licences.SOURCE_LICENCE_COLUMN_SPECS,
            kind="table",
            schema_id=source_licences.SCHEMA,
        )
    )
    return registry


@cache
def rights_block_columns() -> tuple[ColumnSpec, ...]:
    """The shared per-row rights block — declared beside ``compartments.row_rights``."""
    from . import compartments

    return compartments.RIGHTS_BLOCK_SPECS


# --------------------------------------------------------------------------- #
# The fail-closed gate                                                        #
# --------------------------------------------------------------------------- #


def declared_columns(
    resource: str, *, registry: Mapping[str, ResourceSpec] | None = None
) -> set[str]:
    """The full declared column set for ``resource`` (spec + shared rights block)."""
    spec = (registry or column_registry()).get(resource)
    if spec is None:
        raise UnregisteredResourceError(
            f"no column registry entry for resource {resource!r} — every emitted "
            "resource registers (SIG-TRANSP-016); declare it beside its writer"
        )
    declared = {c.name for c in spec.columns}
    if spec.rights_block:
        declared.update(c.name for c in rights_block_columns())
    return declared


def assert_documented(
    resource: str,
    emitted_columns: Iterable[str],
    *,
    registry: Mapping[str, ResourceSpec] | None = None,
) -> None:
    """Fail the build when a writer emits a column no spec declares.

    ``resource`` names the registry resource; ``emitted_columns`` is the union
    of column names the artifact's serialisations carry (flattened
    ``rights_*`` columns and the ``rights``/``_rights`` nested forms included).
    An unregistered resource is a failure too — a table the registry does not
    know IS undocumented.
    """
    declared = declared_columns(resource, registry=registry)
    missing = sorted(set(emitted_columns) - declared)
    if missing:
        raise UndocumentedColumnError(
            f"resource {resource!r} emits undocumented column(s) {missing} — "
            "every emitted column registers (description/type/unit/nullability/"
            "enum source); declare it beside its writer (SIG-TRANSP-016)"
        )


# --------------------------------------------------------------------------- #
# Artifact-path classification                                                #
# --------------------------------------------------------------------------- #

#: Extensions a row-bearing serialisation carries (checked against the registry).
#: ``jsonld`` resolves by stem like the rest, but a ``jsonld`` path that names
#: no resource is a LINKED-DATA DOCUMENT (catalog.jsonld, provenance.jsonld) —
#: never a failure; it is therefore absent from the assert set below.
_TABULAR_EXTENSIONS = frozenset({"csv", "parquet", "sqlite", "jsonl", "jsonld"})
#: Extensions ``assert_path_documented`` fails closed on when the path maps to
#: no registered resource — every column-bearing form except the document-only
#: ``jsonld``.
_ASSERT_EXTENSIONS = (_TABULAR_EXTENSIONS - {"jsonld"}) | {"geojson", "pmtiles"}
#: The geometry serialisations carry the sites table's columns as properties.
_GEO_STEMS = frozenset({"sites"})


def resource_for_path(path: str) -> str | None:
    """The registry resource an artifact path is a serialisation of, or ``None``.

    ``None`` means the artifact is a document (a JSON descriptor/payload or
    other non-columnar file) — listed in the dictionary but column-exempt.
    A columnar path that resolves to nothing returns ``None`` only through
    :func:`classify_artifact` callers that fail closed — use
    :func:`assert_path_documented` for the hard gate.
    """
    name = path.rsplit("/", 1)[-1]
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return None
    if ext in _TABULAR_EXTENSIONS:
        if stem in column_registry():
            return stem
        # directory-scoped streams: labels/<comp>.jsonl, transparency/<name>.jsonl
        if path.startswith("labels/"):
            return "labels"
        if path.startswith("transparency/"):
            res = f"transparency_{stem}"
            return res if res in column_registry() else None
        return None
    if ext in ("geojson", "pmtiles"):
        # A geometry serialisation carries the named table's columns as feature
        # properties — resolve the stem (compartment-suffixed forms like
        # ``osm_physical/devices`` classify on the last path segment's stem).
        if stem in column_registry():
            return stem
        if "sites" in stem:
            return "sites"
    if path == "web/sources.json":
        return "source_licence_table"
    if path == "web/freshness.json":
        return "freshness"
    if path == "web/coverage.json":
        return "coverage"
    if path == "web/sites.json":
        return "sites"
    if path == "transparency/sources.json":
        # A row-bearing document (``sig.source-row/1`` rows) carried
        # under a .json extension — it IS the transparency_sources resource.
        return "transparency_sources"
    return None


def assert_path_documented(path: str) -> str | None:
    """Fail closed when a row-bearing artifact path resolves to no resource.

    Returns the resource name for columnar artifacts, ``None`` for documents.
    """
    name = path.rsplit("/", 1)[-1]
    _stem, dot, ext = name.rpartition(".")
    res = resource_for_path(path)
    if res is None and dot and ext in _ASSERT_EXTENSIONS:
        raise UnregisteredResourceError(
            f"artifact {path!r} is a row-bearing serialisation with no registry "
            "resource — register it beside its writer (SIG-TRANSP-016)"
        )
    return res


# --------------------------------------------------------------------------- #
# Generated documents: Table Schema + dictionary.json                         #
# --------------------------------------------------------------------------- #

_GENERATED_SCHEMA = _REPO_ROOT / "ontology" / "generated" / "jsonschema" / "sig.schema.json"
_VOCAB_SUMMARY = _REPO_ROOT / "ontology" / "generated" / "registry" / "vocab_summary.json"


@cache
def _generated_schema() -> Mapping[str, Any]:
    return json.loads(_GENERATED_SCHEMA.read_text(encoding="utf-8"))


@cache
def _vocab_summary() -> Mapping[str, Any]:
    return json.loads(_VOCAB_SUMMARY.read_text(encoding="utf-8"))


def enum_values(spec: ColumnSpec) -> tuple[str, ...] | None:
    """The permissible values a column's ``enum_source`` resolves to.

    The result is the column's *complete* closed vocabulary — what a Table
    Schema ``constraints.enum`` may assert — built from the named authority
    plus any writer-declared members the source does not carry (e.g. the
    honest-absence token ``not_evaluable`` beside ``linkml:enum:Predicate-
    Volatility``, or ``unclassified`` beside ``linkml:enum:AccessKind``):

    ``linkml:enum:<Name>`` reads the generated JSON Schema ``$defs``; a missing
    enum definition raises (never a hand-copied fallback — the entry must name
    a real generated definition). ``linkml:skos:<scheme>`` reads the generated
    vocabulary registry's slug list. ``export:*``/``policy:*`` sources carry
    ``declared_values`` beside the writer. ``linkml:slot:``/``None`` resolve to
    no closed set.
    """
    declared = tuple(spec.declared_values or ())
    src = spec.enum_source
    resolved: tuple[str, ...] | None
    if src is None:
        resolved = None
    elif src.startswith("linkml:enum:"):
        name = src.split(":", 2)[2]
        definition = _generated_schema().get("$defs", {}).get(name)
        values = (definition or {}).get("enum")
        if not values:
            raise ColumnRegistryError(
                f"column {spec.name!r} cites linkml:enum:{name} which the generated "
                "schema does not define — enum entries come from ontology/generated, "
                "never hand-copied (SIG-TRANSP-016)"
            )
        resolved = tuple(str(v) for v in values)
    elif src.startswith("linkml:skos:"):
        scheme = src.split(":", 2)[2]
        entry = _vocab_summary().get(scheme)
        # The generated vocabulary registry carries each scheme's members as a
        # list of record objects (``slug``) — e.g. ``technology.technologies`` —
        # or, for a bare scheme, a flat ``slugs`` list. Both resolve here.
        members = None
        if isinstance(entry, dict):
            for key, value in entry.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    members = [m.get("slug") for m in value]
                    break
                if key == "slugs" and isinstance(value, list):
                    members = list(value)
                    break
        if not members:
            raise ColumnRegistryError(
                f"column {spec.name!r} cites linkml:skos:{scheme} which the generated "
                "vocabulary registry does not carry"
            )
        resolved = tuple(str(s) for s in members if s)
    elif src.startswith(("linkml:slot:", "export:", "policy:", "registry:")):
        resolved = None
    else:
        raise ColumnRegistryError(f"column {spec.name!r} has unrecognised enum_source {src!r}")
    if resolved is None:
        return declared or None
    return resolved + tuple(v for v in declared if v not in resolved)


def resource_columns(
    resource: str, *, registry: Mapping[str, ResourceSpec] | None = None
) -> tuple[ColumnSpec, ...]:
    """The resource's full column listing — spec columns + the shared rights block."""
    spec = (registry or column_registry())[resource]
    cols: list[ColumnSpec] = list(spec.columns)
    if spec.rights_block:
        cols.extend(rights_block_columns())
    return tuple(cols)


def table_schema(
    resource: str,
    *,
    registry: Mapping[str, ResourceSpec] | None = None,
) -> dict[str, Any]:
    """The Frictionless Table Schema (v2) document for one resource (J3 §6.5)."""
    spec = (registry or column_registry())[resource]
    fields: list[dict[str, Any]] = []
    for col in resource_columns(resource, registry=registry):
        field_entry: dict[str, Any] = {
            "name": col.name,
            "type": col.dtype,
            "description": col.description,
        }
        constraints: dict[str, Any] = {}
        if not col.nullable:
            constraints["required"] = True
        values = enum_values(col)
        if values:
            constraints["enum"] = list(values)
        if constraints:
            field_entry["constraints"] = constraints
        if col.unit is not None:
            field_entry["unit"] = col.unit
        if col.enum_source is not None:
            field_entry["enum_source"] = col.enum_source
        fields.append(field_entry)
    out: dict[str, Any] = {
        "$schema": TABLESCHEMA_PROFILE,
        "name": resource,
        "title": spec.title,
        "description": spec.description,
        "fields": fields,
    }
    if spec.schema_id is not None:
        out["sig:schema"] = spec.schema_id
    return out


def table_schema_path(resource: str) -> str:
    return f"{SCHEMAS_DIR}/{resource}.tableschema.json"


def table_schema_artifacts(
    resources: Iterable[str],
    *,
    registry: Mapping[str, ResourceSpec] | None = None,
) -> dict[str, bytes]:
    """``schemas/<res>.tableschema.json`` bytes for each emitted resource."""
    from .manifest import canonical_json

    return {
        table_schema_path(name): canonical_json(table_schema(name, registry=registry))
        for name in sorted(set(resources))
    }


def dictionary_document(
    *,
    build_spec: Any,
    resources: Sequence[str],
    paths_by_resource: Mapping[str, Sequence[str]],
    documents: Sequence[Mapping[str, Any]],
    sources_by_resource: Mapping[str, Sequence[str]] | None = None,
    registry: Mapping[str, ResourceSpec] | None = None,
) -> dict[str, Any]:
    """The ``sig.data-dictionary/1`` document — the generated data dictionary.

    ``resources`` are the registry resources this export actually emitted;
    ``paths_by_resource`` maps each to its artifact paths;
    ``documents`` lists the non-columnar manifest artifacts
    (``{path, media_type, schema, description}``);
    ``sources_by_resource`` names the upstream sources each resource draws on.
    """
    reg = registry or column_registry()
    entries: list[dict[str, Any]] = []
    for name in sorted(set(resources)):
        spec = reg[name]
        cols: list[dict[str, Any]] = []
        for col in resource_columns(name, registry=reg):
            entry: dict[str, Any] = {
                "name": col.name,
                "type": col.dtype,
                "description": col.description,
                "nullable": col.nullable,
            }
            if col.unit is not None:
                entry["unit"] = col.unit
            if col.enum_source is not None:
                entry["enum_source"] = col.enum_source
                values = enum_values(col)
                if values:
                    entry["enum_values"] = list(values)
            cols.append(entry)
        res_entry: dict[str, Any] = {
            "name": name,
            "title": spec.title,
            "description": spec.description,
            "kind": spec.kind,
            "table_schema": table_schema_path(name),
            "paths": sorted(paths_by_resource.get(name, ())),
            "columns": cols,
        }
        if spec.schema_id is not None:
            res_entry["schema"] = spec.schema_id
        srcs = (sources_by_resource or {}).get(name)
        if srcs:
            res_entry["sources"] = sorted(str(s) for s in srcs)
        entries.append(res_entry)
    return {
        "schema": DICTIONARY_SCHEMA,
        "name": "SIG data dictionary",
        "version": build_spec.release_id(),
        "created": build_spec.as_of_snapshot.isoformat(),
        "ontology": _ontology_citation(),
        "resources": entries,
        "documents": sorted(documents, key=lambda d: str(d.get("path", ""))),
    }


def _ontology_citation() -> dict[str, Any]:
    """The generated-schema citation the dictionary carries (never hand-copied)."""
    schema = _generated_schema()
    from .manifest import sha256_hex as _sha  # local import: manifest owns it

    return {
        "schema_file": "ontology/generated/jsonschema/sig.schema.json",
        "schema_id": schema.get("$id"),
        "version": schema.get("version"),
        "metamodel_version": schema.get("metamodel_version"),
        "sha256": _sha(_GENERATED_SCHEMA.read_bytes()),
        "vocabulary_registry": "ontology/generated/registry/vocab_summary.json",
    }


__all__ = [
    "COLUMN_REGISTRY",  # noqa: F822 — provided lazily via module __getattr__ above
    "ColumnRegistryError",
    "ColumnSpec",
    "DICTIONARY_SCHEMA",
    "ResourceSpec",
    "SCHEMAS_DIR",
    "TABLESCHEMA_PROFILE",
    "UndocumentedColumnError",
    "UnregisteredResourceError",
    "assert_documented",
    "assert_path_documented",
    "column_registry",
    "declared_columns",
    "dictionary_document",
    "enum_values",
    "resource_columns",
    "resource_for_path",
    "rights_block_columns",
    "table_schema",
    "table_schema_artifacts",
    "table_schema_path",
]
