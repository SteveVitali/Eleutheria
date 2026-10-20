# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P35.37 (SIG-TRANSP-013, J3 §5.4): ``web/sources.json``.

The ``sig.source-licence-table/1`` artifact — the per-source licence table the
``/sources/`` page renders, emitted as a manifest-listed artifact so each
row-count figure can carry ``data-artifact="web/sources.json"`` with a JSON
pointer into it. The aggregation is the Python twin of the web data layer's
``sourceLicenceTable`` (``web/src/lib/sources.ts``): the same fields, the same
ordering, the same credit-under-correction rule (E2-12/F-387) — computed from
THIS export's compartment slices + rights index, so the page can never drift
from what the download bytes carry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import compartments as C

SCHEMA = "sig.source-licence-table/1"


def source_licence_table(
    rows_by_compartment: Mapping[str, Sequence[C.ExportRow]],
    index: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate the export's compartment site rows into one row per source.

    Mirrors ``web/src/lib/sources.ts#sourceLicenceTable`` field-for-field
    (camelCase — it is the page contract directly): ``sourceId``, ``licenses``,
    ``compartments``, ``rows``, ``attributionRequired``, ``attribution``,
    ``termsUrl``, ``creditUnderCorrection`` — sorted by ``sourceId``.
    """
    agg: dict[str, dict[str, Any]] = {}
    for compartment, rows in sorted(rows_by_compartment.items()):
        for row in rows:
            record = index.get(row.source_id)
            if record is None:
                continue
            rights = C.row_rights(record, registry)
            sid = str(rights.get("source_id") or row.source_id)
            a = agg.setdefault(
                sid,
                {
                    "licenses": set(),
                    "compartments": set(),
                    "rows": 0,
                    "attributionRequired": False,
                    "attrSet": set(),
                    "termsSet": set(),
                },
            )
            a["rows"] += 1
            a["compartments"].add(compartment)
            if isinstance(rights.get("license"), str):
                a["licenses"].add(rights["license"])
            if rights.get("attribution_required") is True:
                a["attributionRequired"] = True
            attribution = rights.get("attribution")
            if isinstance(attribution, str) and attribution.strip():
                a["attrSet"].add(attribution.strip())
            terms = rights.get("terms_url")
            if isinstance(terms, str) and terms.strip():
                a["termsSet"].add(terms.strip())

    out: list[dict[str, Any]] = []
    for sid, a in agg.items():
        attribution = sorted(a["attrSet"])[0] if a["attrSet"] else None
        # F-387: "DeFlock community map" is the recorded mis-credit — it stands
        # on rows whose source is not a DeFlock feed; flag the credit, keep the
        # source (the web twin applies the identical rule).
        deflock_miscredit = (
            attribution is not None
            and "deflock" in attribution.lower()
            and "deflock" not in sid.lower()
        )
        out.append(
            {
                "sourceId": sid,
                "licenses": sorted(a["licenses"]),
                "compartments": sorted(a["compartments"]),
                "rows": a["rows"],
                "attributionRequired": a["attributionRequired"],
                "attribution": attribution,
                "termsUrl": sorted(a["termsSet"])[0] if a["termsSet"] else None,
                "creditUnderCorrection": bool(
                    (a["attributionRequired"] and not attribution) or deflock_miscredit
                ),
            }
        )
    out.sort(key=lambda r: str(r["sourceId"]))
    return {"schema": SCHEMA, "rows": out}


__all__ = ["SCHEMA", "source_licence_table"]
