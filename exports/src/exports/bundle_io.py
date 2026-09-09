# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Construct a bulk-export build request from a plain JSON document.

Keeps :mod:`exports.bundle` free of I/O (like ``provo_io`` does for ``provo``): the CLI
hands this module a dict shaped like the export inputs and gets back the typed
:class:`~exports.manifest.BuildSpec`, the tables, the rights records, and an optional
crosswalk table. Dates are ISO-8601 strings.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from policy.rights import RightsRecord

from . import bundle as B
from . import compartments as C
from .manifest import BuildSpec


def _date(value: Any, default: date | None = None) -> date:
    if value in (None, "") and default is not None:
        return default
    return date.fromisoformat(value)


def build_spec_from_json(doc: dict[str, Any]) -> BuildSpec:
    return BuildSpec(
        as_of_snapshot=_date(doc["as_of_snapshot"]),
        as_of_belief=_date(doc["as_of_belief"]),
        ruleset_version=str(doc["ruleset_version"]),
        resolver_version=str(doc["resolver_version"]),
        dataset_slug=str(doc.get("dataset_slug", "sig")),
    )


def rights_from_json(rows: list[dict[str, Any]]) -> list[RightsRecord]:
    out: list[RightsRecord] = []
    for r in rows:
        out.append(
            RightsRecord(
                source_id=str(r["source_id"]),
                spdx=str(r["spdx"]),
                attribution=str(r.get("attribution", "")),
                redistributable=bool(r.get("redistributable", False)),
                derivative_permitted=bool(r.get("derivative_permitted", False)),
                terms_url=str(r.get("terms_url", "")),
                retrieval_date=_date(r.get("retrieval_date"), date(2026, 1, 1)),
                ai_training_permitted=bool(r.get("ai_training_permitted", False)),
                upstream_license=r.get("upstream_license"),
            )
        )
    return out


def table_from_json(doc: dict[str, Any]) -> C.ExportTable:
    return C.ExportTable(
        name=str(doc["name"]),
        rows=tuple(
            C.ExportRow(source_id=str(row["source_id"]), data=dict(row.get("data", {})))
            for row in doc.get("rows", [])
        ),
        kind=str(doc.get("kind", "tabular")),
        compartment=doc.get("compartment"),
        geometry_key=str(doc.get("geometry_key", "geometry")),
    )


def build_request_from_json(
    doc: dict[str, Any],
) -> tuple[BuildSpec, list[C.ExportTable], list[RightsRecord], C.ExportTable | None]:
    """Parse a full export build request document into typed inputs for ``build_bundle``."""
    build_spec = build_spec_from_json(doc["build_spec"])
    rights = rights_from_json(doc.get("rights", []))
    tables = [table_from_json(t) for t in doc.get("tables", [])]
    crosswalk: C.ExportTable | None = None
    cw = doc.get("crosswalk")
    if cw is not None:
        crosswalk = B.crosswalk_table_from_rows(
            cw.get("rows", []),
            source_id=str(cw["source_id"]),
            name=str(cw.get("name", "sig_external_crosswalk")),
        )
    return build_spec, tables, rights, crosswalk


__all__ = [
    "build_spec_from_json",
    "rights_from_json",
    "table_from_json",
    "build_request_from_json",
]
