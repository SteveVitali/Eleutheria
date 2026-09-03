# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Redaction as a new capture (SIG-EVID-011)."""

from __future__ import annotations

import pytest
from evidence.digest import multihash
from evidence.redaction import redact


def test_redaction_is_a_new_capture_pointing_at_the_parent() -> None:
    redacted = redact("parent-cap", b"redacted bytes", method="blackbox", version="2.1")
    row = redacted.to_row()
    assert row["parent_capture_id"] == "parent-cap"
    assert row["redaction_applied"] is True
    assert row["redaction_method"] == "blackbox"
    assert row["redaction_version"] == "2.1"
    # The derivative has its own digest; the original bytes are never edited.
    assert row["content_digest"] == multihash(b"redacted bytes")
    assert row["content_digest"] != multihash(b"original unredacted bytes")


def test_redaction_requires_method_and_version() -> None:
    with pytest.raises(ValueError):
        redact("parent-cap", b"x", method="", version="1")
    with pytest.raises(ValueError):
        redact("parent-cap", b"x", method="blackbox", version="")
