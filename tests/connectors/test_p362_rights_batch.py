# SPDX-License-Identifier: Apache-2.0
"""P36.2 (row 350) rights-flip/decline batch — staging artifacts and gate invariants.

The ticket's agent half is *staging*: packets, the queued terms-capture
manifest, and the prepared flip patch on ``r11/sources-flips``. The hard
boundary (OP-26 / ADR-169 §14) is that staging a flip can never *be* a flip —
these tests pin that invariant at the loader gate on fixtures, plus the
structural contract of the committed batch artifacts.

Tests here assert only frozen-artifact facts and fixture behaviour — never a
living record's current value (BM-TEST-01 / OM-15).
"""

from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

import pytest
from connectors.loader import (
    IngestionNotPermitted,
    assert_loadable,
    is_loadable,
)
from connectors.registry import (
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    SourceRecord,
)
from policy.rights import RightsRecord

P362 = Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "rights" / "p362"
RIGHTS = P362.parent

RERUN = (
    "implement-spec "
    "spec=docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md "
    "live_verification=true"
)

EXPECTED_LEGS = {
    "p362-iu1-leonardo-terms",
    "p362-iu2-carahsoft-terms",
    "p362-iu3-google-terms",
    "p362-iu4-soundthinking-terms",
    "p362-iu5-flockradar-terms",
    "p362-camreg-edmonton-terms",
    "p362-bidnet-terms",
    "p362-camreg-und-001-terms",
    "p362-camreg-calgary-terms",
    "p362-camreg-lexington-terms",
    "p362-dot-511-md-terms",
    "p362-camreg-md-opendata-terms",
}


def _fixture_record(
    source_id: str,
    *,
    permitted: bool = False,
    compact: CompactStatus = CompactStatus.NOT_CONTACTED,
    custody: CustodyPosture = CustodyPosture.MIRROR,
) -> SourceRecord:
    """A registry row shaped like a staged-but-unflipped P36.2 source."""
    return SourceRecord(
        id=source_id,
        name=f"{source_id} fixture",
        source_kind=SourceKind.GOVERNMENT_PORTAL,
        homepage_url="https://example.invalid/",
        default_tier="R1",
        custody_posture=custody,
        compact_status=compact,
        robots_policy=RobotsPolicy.HONOR,
        rights=RightsRecord(
            source_id=source_id,
            spdx="UNDETERMINED",
            attribution="",
            redistributable=False,
            derivative_permitted=False,
            terms_url="",
            retrieval_date=date(2026, 10, 27),
        ),
        ingestion_permitted=permitted,
        review_packet="docs/build/reports/rights/p362/batch.md",
    )


def test_batch_artifacts_exist():
    for name in ("batch.md", "terms-manifest.toml", "queued-captures.json", "capture_terms.py"):
        assert (P362 / name).is_file(), f"missing batch artifact {name}"


def test_manifest_carries_all_twelve_legs_queued():
    manifest = tomllib.loads((P362 / "terms-manifest.toml").read_text())
    legs = {leg["id"]: leg for leg in manifest["leg"]}
    assert set(legs) == EXPECTED_LEGS
    for leg_id, leg in legs.items():
        assert leg["status"] == "queued", leg_id
        assert leg["executed"] is False, leg_id
        assert leg["urls"], f"{leg_id} records no capture target"
        assert leg["packet"].startswith("docs/build/reports/rights/")
    assert manifest["meta"]["rerun"] == RERUN
    assert "live:P35.38a" in manifest["meta"]["blocker"]


def test_queued_record_is_prepared_not_executed():
    record = json.loads((P362 / "queued-captures.json").read_text())
    assert record["status"] == "prepared_not_executed"
    assert record["rerun"] == RERUN
    assert set(record["legs"]) == EXPECTED_LEGS
    assert record["probe"]["verdict"].startswith("live:P35.38a FAILS")


def test_batch_doc_carries_e4_lines_and_gate_times():
    text = (P362 / "batch.md").read_text()
    # Every E4 line the operator answered, with its GATE-P time.
    for line in ("R3", "R4a", "R4b", "R4c", "R4d", "R5", "R6a", "R6b"):
        assert line in text
    assert "2026-10-01T04:49:27Z" in text  # B-41 GATE-P time
    assert "2026-10-01T04:46:04Z" in text  # B-36/B-37 GATE-P time (IU captures)
    # The five folded re-decision sources each get a staged line.
    for src in (
        "camreg_und_001",
        "camreg_calgary_ab",
        "camreg_lexington_ky",
        "dot_511_md",
        "camreg_md_opendata",
    ):
        assert src in text
    assert RERUN in text


def test_staged_flip_without_operator_line_is_refused():
    """A staged packet never opens the gate: a row whose only change is a
    prepared packet + the operator's line *pending* still fails closed —
    `ingestion_permitted` defaults false and the loader refuses."""
    rec = _fixture_record("dot_511_tx_like")
    assert not is_loadable(rec)
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(rec)


def test_declined_source_stays_refused_end_to_end():
    """E4-R4d = c (decline): the declined row never gains the flag, so the
    gate refuses — REFUSED is the honest terminal state, not a soft hold."""
    rec = _fixture_record(
        "camreg_bellevue_wa_like",
        compact=CompactStatus.NOT_CONTACTED,
        custody=CustodyPosture.MIRROR,
    )
    assert not is_loadable(rec)
    with pytest.raises(IngestionNotPermitted, match="ingestion_permitted=false"):
        assert_loadable(rec)


def test_flagless_row_with_green_compact_and_custody_still_refuses():
    """Even if compact + custody were repaired (the E4 recipe's other edits),
    the flag alone failing keeps the row REFUSED — the flip is the operator's
    act, everything else is staging."""
    rec = _fixture_record(
        "procportal_chicago_il_like",
        compact=CompactStatus.PUBLIC_TERMS_ONLY,
        custody=CustodyPosture.MIRROR,
    )
    assert not is_loadable(rec)
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(rec)
