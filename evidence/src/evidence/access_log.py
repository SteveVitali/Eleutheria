# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access logging for restricted/sealed bytes (§17.5, SIG-EVID-012).

Access to ``restricted`` and ``sealed`` bytes MUST be logged with requester,
purpose, and timestamp. The access log MUST itself be subject to a retention
limit so that it does not become a surveillance record of SIG's own researchers
(§44.5) — so entries expire, and :func:`expired` marks the ones a retention
sweep deletes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .tiers import StorageTier

# The access log is a record of SIG's own staff; it is kept only as long as it is
# needed to detect insider misuse, then purged (§44.5). Shorter than the evidence
# retention on purpose.
ACCESS_LOG_RETENTION_DAYS = 180


def access_must_be_logged(tier: StorageTier) -> bool:
    """restricted and sealed byte access is audited; public access is not (SIG-EVID-012)."""
    return tier.bytes_are_audited


@dataclass(frozen=True)
class AccessLogEntry:
    """One audited access to restricted/sealed bytes."""

    capture_id: str
    requester: str
    purpose: str
    accessed_at: datetime
    tier: StorageTier

    def __post_init__(self) -> None:
        if not self.requester or not self.purpose:
            raise ValueError("access log requires a requester and a purpose (SIG-EVID-012)")
        if not access_must_be_logged(self.tier):
            raise ValueError(f"{self.tier.value} access is not audited; do not log it")

    def to_row(self) -> dict[str, object]:
        return {
            "capture_id": self.capture_id,
            "requester": self.requester,
            "purpose": self.purpose,
            "accessed_at": self.accessed_at,
            "storage_tier": self.tier.value,
        }


def expired(
    entry_accessed_at: datetime, now: datetime, retention_days: int = ACCESS_LOG_RETENTION_DAYS
) -> bool:
    """True once an access-log entry is past its retention window (SIG-EVID-012)."""
    return now - entry_accessed_at > timedelta(days=retention_days)
