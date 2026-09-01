# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The 51-jurisdiction records-law reference table (§36, SIG-TASK-016).

The table is the authority the generator cites (SIG-TASK-015) and routes on
(SIG-TASK-016a). These are its data-quality checks: it covers every US
jurisdiction, every row is complete, and the operationally-binding residency flag
is exactly the six restricted states and never drifts from the table's own list.
"""

from __future__ import annotations

import pytest
from tasks.records_request import (
    JURISDICTION_COUNT,
    RESIDENCY_RESTRICTED_JURISDICTIONS,
    RecordsLaw,
    UnknownJurisdictionError,
    records_law_for,
    records_law_table,
    table_version,
)

# The 50 states plus the District of Columbia — the 51 US jurisdictions (SIG-TASK-016).
_EXPECTED_JURISDICTIONS = frozenset(
    {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    }
)

_RESTRICTED = frozenset({"AL", "AR", "DE", "KY", "TN", "VA"})


def test_table_covers_all_51_us_jurisdictions() -> None:
    """SIG-TASK-016: the table covers all 51 US jurisdictions, no more, no fewer."""
    table = records_law_table()
    assert JURISDICTION_COUNT == 51
    assert len(table) == 51
    assert frozenset(table) == _EXPECTED_JURISDICTIONS


def test_every_row_carries_all_six_reference_fields() -> None:
    """SIG-TASK-016: statute name/citation, deadline, fee rules, appeal path, residency."""
    for jid, law in records_law_table().items():
        assert isinstance(law, RecordsLaw)
        assert law.jurisdiction_id == jid
        assert law.name, jid
        assert law.statute, jid
        assert law.citation, jid
        assert law.response_deadline, jid
        assert law.fee_rules, jid
        assert law.appeal_path, jid
        assert isinstance(law.residency_required, bool), jid


def test_citations_are_distinct_per_jurisdiction() -> None:
    """A citation is what the request emits; two jurisdictions must not share one."""
    citations = [law.citation for law in records_law_table().values()]
    assert len(citations) == len(set(citations))


def test_exactly_six_residency_restricted_jurisdictions() -> None:
    """SIG-TASK-016a: exactly Alabama, Arkansas, Delaware, Kentucky, Tennessee, Virginia."""
    assert RESIDENCY_RESTRICTED_JURISDICTIONS == _RESTRICTED


def test_per_row_residency_flag_agrees_with_the_restricted_list() -> None:
    """The per-row flag and the table's restricted list cannot drift (SIG-TASK-016a)."""
    by_flag = {jid for jid, law in records_law_table().items() if law.residency_required}
    assert by_flag == RESIDENCY_RESTRICTED_JURISDICTIONS == _RESTRICTED


def test_records_law_for_returns_the_row() -> None:
    law = records_law_for("VA")
    assert law.name == "Virginia"
    assert law.citation == "Va. Code § 2.2-3700"
    assert law.residency_required is True


def test_records_law_for_unknown_jurisdiction_raises() -> None:
    """A target outside the 51-jurisdiction table is refused, not guessed."""
    with pytest.raises(UnknownJurisdictionError, match="not in the §36 records-law table"):
        records_law_for("ZZ")


def test_table_version_is_stamped() -> None:
    assert table_version()
