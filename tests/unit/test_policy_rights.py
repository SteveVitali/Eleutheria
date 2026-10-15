# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The rights record's refused state (SIG-INGEST-046c, §23.7; P36.1a).

An affirmative machine-readable rights reservation is a *refused* state,
distinct from ``UNDETERMINED``: unresolved rights invite the Stage-0
conversation; a recorded reservation closes it. These tests pin the model —
not any living registry row.
"""

from __future__ import annotations

from datetime import date

import pytest
from policy.rights import (
    RESERVATION_KINDS,
    UNDETERMINED,
    RightsRecord,
    RightsReservation,
    is_refused,
    is_undetermined,
)


def _record(**kwargs: object) -> RightsRecord:
    base: dict[str, object] = {
        "source_id": "fixture_source",
        "spdx": UNDETERMINED,
        "attribution": "",
        "redistributable": False,
        "derivative_permitted": False,
        "terms_url": "",
        "retrieval_date": date(2026, 10, 1),
    }
    base.update(kwargs)
    return RightsRecord(**base)  # type: ignore[arg-type]


def _reservation(kind: str = "content_signal") -> RightsReservation:
    return RightsReservation(
        kind=kind,
        verbatim="ai-train=no",
        observed_on=date(2026, 10, 1),
        evidence="test fixture: response header",
    )


def test_reservation_is_an_additive_optional_field() -> None:
    # Back-compat: a record with no reservation still constructs and is neither
    # refused nor cleared — ``None`` means "no refusal recorded", nothing more.
    record = _record()
    assert record.reservation is None
    assert not is_refused(record)


def test_refused_is_distinct_from_undetermined() -> None:
    # The load-bearing distinction (SIG-INGEST-046c): a reservation on an
    # UNDETERMINED record makes it *refused*, never silently "resolved" or
    # collapsed into the unresolved bucket.
    record = _record(reservation=_reservation())
    assert is_undetermined(record)  # the SPDX is still UNDETERMINED
    assert is_refused(record)  # and the record is refused — a different axis
    resolved = _record(spdx="CC-BY-4.0", reservation=_reservation("tdm_reservation"))
    assert not is_undetermined(resolved)
    assert is_refused(resolved)  # a refusal can sit beside a real SPDX too


def test_reservation_kind_must_be_in_the_vocabulary() -> None:
    for kind in RESERVATION_KINDS:
        _reservation(kind)
    with pytest.raises(ValueError, match="not in"):
        _reservation("invented_kind")


def test_reservation_requires_verbatim_signal_and_evidence() -> None:
    # §3.1: a refusal is asserted only on evidence — the signal as observed
    # plus a pointer a reviewer can audit. Neither may be empty.
    with pytest.raises(ValueError, match="verbatim"):
        RightsReservation(
            kind="content_signal",
            verbatim="",
            observed_on=date(2026, 10, 1),
            evidence="e",
        )
    with pytest.raises(ValueError, match="evidence"):
        RightsReservation(
            kind="content_signal",
            verbatim="ai-train=no",
            observed_on=date(2026, 10, 1),
            evidence="",
        )


def test_reservation_vocabulary_names_the_spec_forms() -> None:
    # The recorded kinds cover §23.7's named forms: Content-Signal, TDM /
    # Article 4, X-Robots-Tag, express terms, and the host-level opt-out.
    assert {
        "content_signal",
        "tdm_reservation",
        "article_4",
        "x_robots_tag",
        "express_terms",
        "opt_out",
        "other",
    } == RESERVATION_KINDS
