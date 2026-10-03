# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Express-terms disclosure (P34.19, F-403, ADR-183).

The operator accepted the express-terms risk for the eight captured-terms
sources whose rows were public at decision time — **"Keep all, accept risk"**
(round 4, 2026-10-01T04:07:45Z), **"Keep everything as is"** (round 5,
2026-10-01T04:09:43Z) — with the SB-2 clarification **"Yes, same sources
(Recommended)"** (round 27, 2026-10-01T13:46:58Z): scheduled refreshes of the
same sources are covered; a *new* source with a non-commercial clause follows
A-9 (facts and pointers only).

This module loads the committed disclosure table
(:mod:`policy.data.express_terms`) — the affected list itself — and decorates
:class:`~policy.rights.RightsRecord` so every layer that already carries the
rights record (registry, export obligations, the read API) can pass the
captured terms and the publication basis downstream unchanged
(SIG-LIC-001, SIG-LIC-011). The record is **data, not code**; the row counts in
it are computed from release compartment rows and test-verified.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from policy._data import load_json_table
from policy.rights import RightsRecord

#: The recorded publication-basis string, verbatim (ADR-183).
PUBLICATION_BASIS = "operator-accepted express terms (ADR-183)"

#: The data table schema this module reads.
EXPRESS_TERMS_SCHEMA = "sig.express-terms-disclosure/1"


def express_terms() -> dict[str, Any]:
    """The full ``sig.express-terms-disclosure/1`` table."""
    table = load_json_table("express_terms")
    if table.get("schema") != EXPRESS_TERMS_SCHEMA:
        raise ValueError(
            f"express_terms table schema {table.get('schema')!r} != {EXPRESS_TERMS_SCHEMA!r}"
        )
    return table


def basis() -> dict[str, Any]:
    """The ADR-183 basis block (operator words verbatim + adopted sentence)."""
    return express_terms()["basis"]


def affected_source_ids() -> set[str]:
    """The source ids covered by the operator's express-terms acceptance."""
    return {entry["source_id"] for entry in express_terms()["sources"]}


def disclosure_for(source_id: str) -> dict[str, Any] | None:
    """The disclosure entry for ``source_id``, or ``None`` when unaffected."""
    for entry in express_terms()["sources"]:
        if entry["source_id"] == source_id:
            return entry
    return None


def apply_to_record(record: RightsRecord) -> RightsRecord:
    """Return ``record`` with disclosure fields populated when affected.

    Unchanged (the same object) for unaffected sources — additive and
    backwards-compatible: a record built elsewhere without the new fields
    gains them only here.
    """
    entry = disclosure_for(record.source_id)
    if entry is None:
        return record
    return replace(
        record,
        captured_terms_verbatim=entry["captured_terms_verbatim"],
        captured_terms_evidence=entry["captured_terms_evidence"],
        publication_basis=entry["publication_basis"],
    )
