# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21a — the attribution-corrections artifact generator.

The committed list is generated from ``sources.toml``'s reviewed rights
blocks: each row carries the source's own (spdx, attribution, terms) +
reviewer ROLE + review date + a basis naming E2-12 and ADR-194, and a source
with no recorded rights review is SKIPPED (it cannot name a reviewer) —
never corrected with a fabricated review.
"""

from __future__ import annotations

import json

from connectors.corrections import (
    CORRECTIONS_SCHEMA,
    SPDX_NORMALISATIONS,
    corrections_list,
    write_corrections_list,
)


def test_schema_and_shape() -> None:
    doc = corrections_list()
    assert doc["schema"] == CORRECTIONS_SCHEMA
    assert isinstance(doc["corrections"], list) and doc["corrections"]
    assert doc["totals"]["corrections"] == len(doc["corrections"])
    assert doc["totals"]["skipped"] == len(doc["skipped"])


def test_every_row_carries_the_decision_fields() -> None:
    doc = corrections_list()
    for row in doc["corrections"]:
        assert row["source_id"]
        assert row["spdx"]
        # the licence fact + the spine vocabulary the writer validates
        assert row["redistributable"] in ("yes", "no", "review_required", "UNDETERMINED")
        assert row["derivative_permitted"] in (
            "yes",
            "no",
            "review_required",
            "UNDETERMINED",
        )
        assert row["reviewed_by"]  # a ROLE — the registry refuses a bare flip
        assert row["reviewed_on"]
        assert row["retrieval_date"]
        assert "E2-12" in row["basis"] and "ADR-194" in row["basis"]


def test_rows_carry_the_registry_signature() -> None:
    """The corrected signature is the source's OWN reviewed rights block."""
    from connectors.registry import get

    doc = corrections_list()
    by_id = {r["source_id"]: r for r in doc["corrections"]}
    for source_id, row in by_id.items():
        rec = get(source_id)
        assert row["spdx"] == rec.rights.spdx
        assert row["attribution"] == rec.rights.attribution
        assert row["terms_url"] == rec.rights.terms_url
        assert row["reviewed_by"] == rec.rights_reviewed_by


def test_identifier_normalisations_are_declared() -> None:
    """Sources on a normalised licence declare the recorded malformed id."""
    doc = corrections_list()
    by_id = {r["source_id"]: r for r in doc["corrections"]}
    for old, new in SPDX_NORMALISATIONS.items():
        for row in doc["corrections"]:
            if row["spdx"] == new:
                assert old in row.get("spdx_aliases", []), (
                    f"{row['source_id']}: {old!r} -> {new!r} undeclared"
                )
    # the two ids the ticket names are in the map
    assert SPDX_NORMALISATIONS["OGL-3.0"] == "OGL-UK-3.0"
    assert SPDX_NORMALISATIONS["LicenceOuverte-2.0"] == "etalab-2.0"
    assert by_id  # silence lint


def test_unreviewed_sources_are_skipped_not_fabricated() -> None:
    doc = corrections_list()
    correction_ids = {r["source_id"] for r in doc["corrections"]}
    skipped_ids = {s["source_id"] for s in doc["skipped"]}
    assert not (correction_ids & skipped_ids)
    # every skipped row names why — the missing review, never a guess
    for s in doc["skipped"]:
        assert "rights review" in s["reason"]


def test_write_emits_committable_json(tmp_path) -> None:
    out = write_corrections_list(tmp_path / "corrections.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == CORRECTIONS_SCHEMA
    # the writer's loader consumes exactly this shape
    from db.rights_corrections import load_corrections

    rows = load_corrections(out)
    assert len(rows) == doc["totals"]["corrections"]
