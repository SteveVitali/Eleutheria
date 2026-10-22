# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.35 — the ``[sources.<id>.redistribution]`` declaration (J4 R-1…R-13,
D-J3-1 [B-19]): closed-vocabulary parsing, fail-closed validation, and the
lane resolver's recorded-verdict path.

The registry-file assertions pin *vocabulary membership* — an invariant that
holds at every commit — never a living row's value (BM-TEST-01).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from connectors.registry import (
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    SourceRecord,
    SourceRedistribution,
    _redistribution_from_row,
    registry,
)
from db.claim_sink import PgClaimSink
from policy.rights import RightsRecord
from policy.transparency import (
    PART_VIII_CLASSES,
    PART_VIII_CLEAR_VALUES,
    REDISTRIBUTION_LANES,
    derive_storage_tier,
)


def _rights() -> RightsRecord:
    return RightsRecord(
        source_id="src.test",
        spdx="UNDETERMINED",
        attribution="",
        redistributable=False,
        derivative_permitted=False,
        terms_url="",
        retrieval_date=date(2026, 10, 19),
    )


def _record(redistribution: SourceRedistribution | None = None) -> SourceRecord:
    return SourceRecord(
        id="src.test",
        name="Fixture",
        source_kind=SourceKind.GOVERNMENT_PORTAL,
        homepage_url="https://example.org",
        default_tier="R2",
        custody_posture=CustodyPosture.MIRROR,
        compact_status=CompactStatus.NOT_CONTACTED,
        robots_policy=RobotsPolicy.HONOR,
        rights=_rights(),
        redistribution=redistribution or SourceRedistribution(),
    )


# --- parsing ----------------------------------------------------------------


def test_absent_block_is_the_undeclared_default():
    red = _redistribution_from_row("src.test", {})
    assert red == SourceRedistribution()
    assert red.lane == ""  # honest absence, not a recorded "unknown"


def test_present_block_parses_the_declared_fields():
    red = _redistribution_from_row(
        "src.test",
        {
            "redistribution": {
                "lane": "derived-only",
                "evidence": "rights/src.test.md; J4 R-7",
                "evidence_uri": (
                    "docs/build/planning/2026-09-30-next-phase/data/redistribution.csv#src.test"
                ),
                "decision_authority": "D-J3-1 [B-19]",
                "review_needed": True,
                "part_viii_class": "P8-3",
                "packet_limited": True,
                "sig_labelled_cc0": True,
            }
        },
    )
    assert red.lane == "derived-only"
    assert red.part_viii_class == "P8-3"
    assert red.review_needed and red.packet_limited and red.sig_labelled_cc0


def test_non_table_block_fails_closed():
    with pytest.raises(ValueError, match="must be a table"):
        _redistribution_from_row("src.test", {"redistribution": "raw-ok"})


def test_unknown_key_fails_closed():
    with pytest.raises(ValueError, match="unknown field"):
        _redistribution_from_row(
            "src.test", {"redistribution": {"lane": "raw-ok", "lane_notes": "x"}}
        )


# --- validation (SourceRecord.__post_init__) ---------------------------------


def test_invented_lane_refuses():
    with pytest.raises(ValueError, match="closed vocabulary"):
        _record(SourceRedistribution(lane="wide-open", evidence="x", decision_authority="d"))


def test_positive_lane_without_evidence_refuses():
    with pytest.raises(ValueError, match="no redistribution.evidence"):
        _record(SourceRedistribution(lane="raw-ok", decision_authority="D-J3-1 [B-19]"))


def test_positive_lane_without_decision_authority_refuses():
    with pytest.raises(ValueError, match="decision_authority"):
        _record(SourceRedistribution(lane="raw-ok", evidence="rights/x.md"))


def test_recorded_unknown_lane_stands_on_thin_evidence():
    rec = _record(SourceRedistribution(lane="unknown", evidence="no J4 row recorded"))
    assert rec.redistribution.lane == "unknown"


def test_fields_without_a_lane_are_dangling():
    with pytest.raises(ValueError, match="no lane"):
        _record(SourceRedistribution(evidence="x"))


@pytest.mark.parametrize("p8", sorted(PART_VIII_CLASSES | PART_VIII_CLEAR_VALUES))
def test_part_viii_vocabulary_accepts_every_recorded_value(p8):
    rec = _record(
        SourceRedistribution(
            lane="derived-only",
            evidence="x",
            decision_authority="d",
            part_viii_class=p8,
        )
    )
    assert rec.redistribution.part_viii_class == p8


def test_invented_part_viii_class_refuses():
    with pytest.raises(ValueError, match="part_viii_class"):
        _record(
            SourceRedistribution(
                lane="raw-ok", evidence="x", decision_authority="d", part_viii_class="P8-99"
            )
        )


def test_registry_version_is_content_derived_and_changes_with_the_verdict():
    a = SourceRedistribution(lane="raw-ok", evidence="x", decision_authority="d")
    b = SourceRedistribution(lane="derived-only", evidence="x", decision_authority="d")
    assert (
        a.registry_version()
        == SourceRedistribution(
            lane="raw-ok", evidence="x", decision_authority="d"
        ).registry_version()
    )
    assert a.registry_version() != b.registry_version()


# --- the committed registry (invariants only) -------------------------------


def test_every_declared_lane_is_in_the_closed_vocabulary():
    """Every ``[redistribution]`` block in the committed registry names a
    closed-vocabulary lane — or no lane (the undeclared default)."""
    for sid, rec in registry().items():
        lane = rec.redistribution.lane
        assert not lane or lane in REDISTRIBUTION_LANES, (sid, lane)


def test_every_declared_part_viii_class_is_in_the_closed_vocabulary():
    vocab = PART_VIII_CLASSES | PART_VIII_CLEAR_VALUES
    for sid, rec in registry().items():
        p8 = rec.redistribution.part_viii_class
        assert not p8 or p8 in vocab, (sid, p8)


def test_every_declared_positive_lane_names_evidence_and_authority():
    for sid, rec in registry().items():
        red = rec.redistribution
        if not red.lane:
            continue
        assert red.evidence.strip(), sid
        if red.lane != "unknown":
            assert red.decision_authority.strip(), sid


# --- the capture writer's tier derivation (recorded verdict wins) ------------


def _sink(fields: dict[str, Any] | None) -> PgClaimSink:
    return PgClaimSink(
        object(),  # _lane_and_custody never touches the connection
        connector_name="sig.test",
        lane_resolver=lambda _sid: fields,
    )


def test_recorded_raw_ok_with_clear_p8_reaches_public():
    sink = _sink(
        {
            "lane": "raw-ok",
            "part_viii_class": "clear",
            "custody_posture": "MIRROR",
            "redistribution_version": "v1",
        }
    )
    tier, _custody = sink._lane_and_custody("src.test")
    assert tier == "public"


def test_recorded_raw_ok_with_p8_class_never_reaches_public():
    sink = _sink(
        {
            "lane": "raw-ok",
            "part_viii_class": "P8-5",
            "custody_posture": "MIRROR",
        }
    )
    tier, _custody = sink._lane_and_custody("src.test")
    assert tier == "restricted"  # bytes stay field-screened (derive_storage_tier)


def test_recorded_raw_ok_without_p8_screening_stays_sealed():
    sink = _sink({"lane": "raw-ok", "custody_posture": "MIRROR"})
    tier, _custody = sink._lane_and_custody("src.test")
    assert tier == "sealed"  # an unevidenced class fails closed


def test_recorded_restricted_and_unknown_stay_sealed():
    for lane in ("restricted", "unknown"):
        tier, _custody = _sink({"lane": lane})._lane_and_custody("src.test")
        assert tier == "sealed", lane


def test_recorded_derived_only_and_link_only_are_restricted():
    for lane in ("derived-only", "link-only"):
        tier, _custody = _sink({"lane": lane})._lane_and_custody("src.test")
        assert tier == "restricted", lane


def test_undeclared_block_falls_back_to_the_interim_basis():
    """No recorded lane → the interim rights-record derivation stands (its
    basis is recorded) — and it never reaches ``public``."""
    sink = _sink(
        {
            "custody_posture": "MIRROR",
            "spdx": "CC0-1.0",
            "redistributable": "yes",
            "reviewed": True,
        }
    )
    tier, _custody = sink._lane_and_custody("src.test")
    # Interim basis can derive raw-ok, but no recorded Part VIII screen —
    # derive_storage_tier fails closed.
    assert tier == "sealed"


def test_unresolvable_source_is_sealed_never_public():
    tier, _custody = _sink(None)._lane_and_custody("src.unknown")
    assert tier == derive_storage_tier(None) == "sealed"
