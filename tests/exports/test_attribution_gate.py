# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21a — the publish-time attribution gate at the export build (E2-12/ADR-194).

``enrich_rows`` stamps every exported row with its ``_rights`` block; a row
whose licence declares ``attribution_required = true`` but whose effective
attribution is empty must fail the build — that is exactly the F-387 defect
shape, and the gate exists so it can never reach a file again. A row under a
non-attribution-required licence, or a populated credit, passes untouched.
"""

from __future__ import annotations

from datetime import date

import pytest
from exports.compartments import (
    AttributionGateError,
    assert_attribution_rows,
    attribution_gate_violations,
)
from policy.rights import RightsRecord

from exports import compartments as C


def _rr(source_id: str, spdx: str, *, attribution: str = "") -> RightsRecord:
    return RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution=attribution,
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 9, 18),
    )


def test_enrich_rows_refuses_empty_attribution_where_required() -> None:
    """CC-BY-4.0 requires attribution (licenses.toml); an empty credit fails."""
    table = C.ExportTable("sites", (C.ExportRow("src_a", {"id": "1"}),))
    index = C.rights_index([_rr("src_a", "CC-BY-4.0", attribution="")])
    with pytest.raises(AttributionGateError, match="E2-12"):
        C.enrich_rows(table, index)


def test_enrich_rows_refuses_whitespace_only_attribution() -> None:
    table = C.ExportTable("sites", (C.ExportRow("src_a", {"id": "1"}),))
    index = C.rights_index([_rr("src_a", "CC-BY-4.0", attribution="   ")])
    with pytest.raises(AttributionGateError):
        C.enrich_rows(table, index)


def test_enrich_rows_passes_a_populated_credit() -> None:
    table = C.ExportTable("sites", (C.ExportRow("src_a", {"id": "1"}),))
    index = C.rights_index([_rr("src_a", "CC-BY-4.0", attribution="Council A open data")])
    rows = C.enrich_rows(table, index)
    assert rows[0][C.RIGHTS_KEY]["attribution"] == "Council A open data"
    # the licence URL travels with the row's obligations (P34.21a)
    assert rows[0][C.RIGHTS_KEY]["license_url"] == "https://creativecommons.org/licenses/by/4.0/"


def test_enrich_rows_passes_a_non_attribution_required_licence() -> None:
    """CC0-1.0 carries attribution_required=false — an empty credit is legal."""
    table = C.ExportTable("sites", (C.ExportRow("src_a", {"id": "1"}),))
    index = C.rights_index([_rr("src_a", "CC0-1.0", attribution="")])
    rows = C.enrich_rows(table, index)
    assert rows[0][C.RIGHTS_KEY]["attribution_required"] is False


def test_gate_names_the_offending_source() -> None:
    table = C.ExportTable(
        "sites",
        (C.ExportRow("src_bad", {"id": "1"}), C.ExportRow("src_ok", {"id": "2"})),
    )
    index = C.rights_index(
        [_rr("src_bad", "CC-BY-4.0"), _rr("src_ok", "CC-BY-4.0", attribution="ok")]
    )
    with pytest.raises(AttributionGateError, match="src_bad"):
        C.enrich_rows(table, index)


def test_violations_scanner_is_the_shared_rule() -> None:
    rows = [
        {"_rights": {"source_id": "s1", "attribution_required": True, "attribution": ""}},
        {"_rights": {"source_id": "s2", "attribution_required": False, "attribution": ""}},
        {"_rights": {"source_id": "s3", "attribution_required": True, "attribution": "ok"}},
        {"no_rights_block": True},
    ]
    violations = attribution_gate_violations(rows)
    assert len(violations) == 1
    assert violations[0][0] == "s1"
    with pytest.raises(AttributionGateError):
        assert_attribution_rows(rows, context="fixture")
