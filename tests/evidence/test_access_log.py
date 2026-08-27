# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access logging for restricted/sealed bytes + retention (SIG-EVID-012)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from evidence.access_log import (
    ACCESS_LOG_RETENTION_DAYS,
    AccessLogEntry,
    access_must_be_logged,
    expired,
)
from evidence.tiers import StorageTier

_WHEN = datetime(2026, 6, 1, tzinfo=UTC)


def test_only_restricted_and_sealed_access_is_logged() -> None:
    assert not access_must_be_logged(StorageTier.PUBLIC)
    assert access_must_be_logged(StorageTier.RESTRICTED)
    assert access_must_be_logged(StorageTier.SEALED)


def test_entry_requires_requester_and_purpose() -> None:
    with pytest.raises(ValueError):
        AccessLogEntry("cap", "", "audit", _WHEN, StorageTier.SEALED)
    with pytest.raises(ValueError):
        AccessLogEntry("cap", "researcher", "", _WHEN, StorageTier.SEALED)


def test_public_access_is_not_logged() -> None:
    with pytest.raises(ValueError):
        AccessLogEntry("cap", "researcher", "audit", _WHEN, StorageTier.PUBLIC)


def test_entry_row_shape() -> None:
    row = AccessLogEntry("cap", "researcher", "takedown review", _WHEN, StorageTier.SEALED).to_row()
    assert row["requester"] == "researcher"
    assert row["purpose"] == "takedown review"
    assert row["storage_tier"] == "sealed"


def test_retention_expiry() -> None:
    """SIG-EVID-012: the access log is itself retained then purged (§44.5)."""
    now = _WHEN + timedelta(days=ACCESS_LOG_RETENTION_DAYS + 1)
    assert expired(_WHEN, now)
    assert not expired(_WHEN, _WHEN + timedelta(days=1))
