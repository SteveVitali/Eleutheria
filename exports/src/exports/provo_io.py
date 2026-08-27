# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Construct a :class:`exports.provo.Lineage` from a plain JSON document.

Keeps the PROV-O core (`exports.provo`) free of I/O: the CLI and any caller can
hand it a dict shaped like the lineage tables and get typed dataclasses back.
Timestamps are ISO-8601 strings (or null); ids are strings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .provo import (
    Capture,
    Claim,
    Connector,
    Curator,
    Extraction,
    IngestRun,
    Lineage,
    Source,
)


def _dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(value)


def lineage_from_json(doc: dict[str, Any]) -> Lineage:
    """Build a :class:`Lineage` from a JSON-decoded lineage document."""
    return Lineage(
        sources=[Source(**s) for s in doc.get("sources", [])],
        connectors=[Connector(**c) for c in doc.get("connectors", [])],
        curators=[Curator(**c) for c in doc.get("curators", [])],
        runs=[
            IngestRun(
                run_id=r["run_id"],
                connector_name=r["connector_name"],
                connector_version=r.get("connector_version"),
                started_at=_dt(r.get("started_at")),
                finished_at=_dt(r.get("finished_at")),
            )
            for r in doc.get("runs", [])
        ],
        extractions=[Extraction(**e) for e in doc.get("extractions", [])],
        captures=[
            Capture(
                capture_id=c["capture_id"],
                source_id=c.get("source_id"),
                run_id=c.get("run_id"),
                retrieved_at=_dt(c.get("retrieved_at")),
            )
            for c in doc.get("captures", [])
        ],
        claims=[
            Claim(
                claim_id=c["claim_id"],
                extraction_id=c.get("extraction_id"),
                run_id=c.get("run_id"),
                revises_claim_id=c.get("revises_claim_id"),
                asserted_by_curator_id=c.get("asserted_by_curator_id"),
                recorded_at=_dt(c.get("recorded_at")),
            )
            for c in doc.get("claims", [])
        ],
    )
