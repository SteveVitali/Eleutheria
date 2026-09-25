# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Camera-site review queue logic (P31.10) — the non-PG half.

Pins the stratum vocabulary (the camera-site families vs the P31.3
identity-duplicate family), the strata-spec parser, and the import path's
decision mapping — the parts that don't need a live spine (the SQL, sampler
draw, campaign append, and observation read are exercised against real PG in
``tests/db/test_camera_site_review.py``).
"""

from __future__ import annotations

import pytest
from resolution.camera_site_review import (
    CAMERA_SITE_DISPUTED_PREFIX,
    CAMERA_SITE_ITEM_PREFIX,
    IDENTITY_DUPLICATE_PREFIX,
    import_decisions,
    is_camera_site_item,
    parse_strata,
    stratum_for,
)


def test_is_camera_site_item_families() -> None:
    a = "01a0b0ca-264b-7503-85d8-3ed02303438d"
    b = "01a0b0da-e6f3-7894-94c7-d84e5a303b55"
    assert is_camera_site_item(f"{CAMERA_SITE_ITEM_PREFIX}{a}:{b}")
    assert is_camera_site_item(f"{CAMERA_SITE_DISPUTED_PREFIX}{a}:{b}")
    # The P31.3 identity-triage family is NOT part of the camera-site queue.
    assert not is_camera_site_item(f"{IDENTITY_DUPLICATE_PREFIX}{a}:{b}")
    assert not is_camera_site_item("er_match:agency:okcpd~agency:okc-pd")


def test_stratum_for() -> None:
    a, b = "x", "y"
    # A proposal's stratum is its match tier…
    assert stratum_for(f"{CAMERA_SITE_ITEM_PREFIX}{a}:{b}", {"tier": 5}) == "5g"
    # …unless it carries a soft conflict (its own bucket)…
    assert (
        stratum_for(
            f"{CAMERA_SITE_ITEM_PREFIX}{a}:{b}",
            {"tier": 3, "reason": "soft_conflict:jurisdiction"},
        )
        == "soft-conflict"
    )
    # …or is an adjudicator disagreement — either id spelling lands in
    # ``disputed``.
    assert (
        stratum_for(
            f"{CAMERA_SITE_ITEM_PREFIX}{a}:{b}",
            {"reason": "active_learning:adjudicator_disagreement"},
        )
        == "disputed"
    )
    assert stratum_for(f"{CAMERA_SITE_DISPUTED_PREFIX}{a}:{b}", {}) == "disputed"
    # A proposal with no tier and no reason is honest "other".
    assert stratum_for(f"{CAMERA_SITE_ITEM_PREFIX}{a}:{b}", {}) == "other"


def test_parse_strata_default_and_counts() -> None:
    assert [n for n, _ in parse_strata(None)] == [
        "1g",
        "3g",
        "4g",
        "5g",
        "soft-conflict",
        "disputed",
    ]
    assert parse_strata("4g:150, disputed:all ,1g") == [
        ("4g", 150),
        ("disputed", -1),
        ("1g", None),
    ]
    with pytest.raises(ValueError, match="unknown stratum"):
        parse_strata("4g,bogus")
    with pytest.raises(ValueError, match="not a number"):
        parse_strata("4g:many")
    with pytest.raises(ValueError, match=">= 0"):
        parse_strata("4g:-2")


def test_import_decisions_maps_spellings_and_skips_unsure() -> None:
    """The offline path writes only accept/reject; unsure writes nothing."""

    class _Queue:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str, str | None]] = []

        def decide(self, item_id, decision, *, reviewer, rationale=None):
            if decision not in {"accept", "reject"}:
                raise ValueError("bad decision")
            self.calls.append((item_id, decision, reviewer, rationale))

    queue = _Queue()
    rows = [
        {"item_id": "er_match:camera_site:a:b", "decision": "accept"},
        {"item_id": "er_match:camera_site:c:d", "decision": "match"},
        {"item_id": "er_match:camera_site:e:f", "decision": "no-match"},
        {"item_id": "er_match:camera_site:g:h", "decision": "unsure"},
        {"item_id": "er_match:camera_site:i:j", "decision": None},
        {"item_id": "er_match:camera_site:k:l", "decision": "bogus"},
    ]
    result = import_decisions(queue, rows, reviewer="curator-1")
    assert result["appended"] == 3
    assert result["skipped"] == 2  # "unsure" + blank write NOTHING
    assert len(result["errors"]) == 1  # an unknown label fails loudly, not silently
    decisions = [c[1] for c in queue.calls]
    assert decisions == ["accept", "accept", "reject"]
    assert all(c[2] == "curator-1" for c in queue.calls)


def test_import_decisions_requires_a_reviewer() -> None:
    with pytest.raises(ValueError, match="reviewer"):
        import_decisions(object(), [], reviewer="")
