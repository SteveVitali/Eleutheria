# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Contributor submissions: L0 entry, device routing, data minimisation
(§34.1–34.3, SIG-CONTRIB-002/004/005).

AC1 (SIG-CONTRIB-002): a submission creates an L0 evidence artifact and no L1
claim. AC2 (SIG-CONTRIB-005): the retained record carries no contributor PII, and
operational logs purge past a short window.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tasks.contributor import EvidenceLevel
from tasks.submission import (
    FORBIDDEN_CONTRIBUTOR_DATA,
    DeviceObservationNotCapturedError,
    OperationalLog,
    SubmissionKind,
    is_sig_capturable,
    retained_submission_fields,
    route_device_observation,
    submit,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_submit_creates_l0_evidence_and_no_l1_claim() -> None:
    """AC1 / SIG-CONTRIB-002: a submission is L0 evidence, never a direct L1 claim."""
    receipt = submit(
        submission_id="sub-1",
        kind=SubmissionKind.SIGNAGE,
        evidence_ref="evidence:ocfl-object-1",
    )
    assert receipt.entry_level is EvidenceLevel.L0_EVIDENCE
    assert receipt.produces_l1_claim is False
    assert receipt.evidence_ref == "evidence:ocfl-object-1"


def test_device_observation_is_routed_not_captured() -> None:
    """SIG-CONTRIB-004: device observations go to OSM/DeFlock, not SIG capture."""
    assert not is_sig_capturable(SubmissionKind.DEVICE_OBSERVATION)
    assert is_sig_capturable(SubmissionKind.OPERATOR_EVIDENCE)
    assert is_sig_capturable(SubmissionKind.CONTRACT)

    referral = route_device_observation()
    assert referral.target == "OSM/DeFlock"

    with pytest.raises(DeviceObservationNotCapturedError):
        submit(
            submission_id="sub-2",
            kind=SubmissionKind.DEVICE_OBSERVATION,
            evidence_ref="evidence:ocfl-object-2",
        )


def test_submission_record_retains_no_contributor_pii() -> None:
    """AC2 / SIG-CONTRIB-005: no real name, device id, or contributor geolocation."""
    field_names = set(retained_submission_fields())
    assert not (field_names & FORBIDDEN_CONTRIBUTOR_DATA)
    # No field name even hints at the forbidden categories.
    for name in field_names:
        lowered = name.lower()
        assert "real_name" not in lowered
        assert "device" not in lowered
        assert not lowered.startswith("ip")
    # The one location it keeps is the *observation's*, not the contributor's.
    assert "observation_location" in field_names
    assert "contributor_location" not in field_names


def test_operational_log_purges_entries_past_the_window() -> None:
    """AC2 / SIG-CONTRIB-005: IP/operational logs are dropped past the short window."""
    log = OperationalLog()
    window = timedelta(days=7)
    log.record("ip", "203.0.113.7", at=_NOW)
    log.record("ip", "203.0.113.8", at=_NOW + timedelta(days=6))

    # Nine days later, the first entry is past the window and the second is not.
    purged = log.purge_expired(_NOW + timedelta(days=9), window=window)
    kept_values = {e.value for e in log.entries()}
    purged_values = {e.value for e in purged}

    assert purged_values == {"203.0.113.7"}
    assert kept_values == {"203.0.113.8"}

    # Far enough in the future, nothing operational survives.
    log.purge_expired(_NOW + timedelta(days=365), window=window)
    assert log.entries() == []
