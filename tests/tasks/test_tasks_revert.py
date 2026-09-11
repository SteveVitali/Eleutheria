# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Revert a contribution as a unit (§34.4, SIG-CONTRIB-009; §16.6 mechanism).

AC4: a revert supersedes via a new append-only assertion and deletes nothing.
This is the in-memory model; ``tests/db/test_reverts.py`` proves the same over
the real claim spine (``retraction_of``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tasks.revert import ContributionLedger, NothingToRevertError

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = _T0 + timedelta(days=30)


def test_revert_appends_a_new_assertion_and_deletes_nothing() -> None:
    """AC4: reverting closes the belief and appends a retraction; nothing is removed."""
    ledger = ContributionLedger()
    original_id = ledger.assert_value("contrib-1", "deployment:okc-1", "vendor=acme", at=_T0)
    before = len(ledger.all_assertions())

    appended = ledger.revert_contribution("contrib-1", reason="vandalism", at=_T1)

    # A new assertion was appended (never a deletion): the count grew.
    assert len(ledger.all_assertions()) == before + 1
    assert len(appended) == 1

    # The original row still exists and was only closed, never mutated away.
    original = ledger.all_assertions()[original_id]
    assert original.value == "vendor=acme"
    assert original.belief_to == _T1
    assert not original.is_retraction

    # The revert is itself a new assertion pointing back at the original.
    retraction = ledger.all_assertions()[appended[0]]
    assert retraction.is_retraction
    assert retraction.retraction_of == original_id
    assert retraction.revert_reason == "vandalism"
    assert retraction.value is None
    assert ledger.is_reverted("contrib-1")


def test_revert_operates_on_the_whole_contribution_as_a_unit() -> None:
    """SIG-CONTRIB-009: every open assertion of the contribution is reverted at once."""
    ledger = ContributionLedger()
    ledger.assert_value("contrib-2", "deployment:a", "v1", at=_T0)
    ledger.assert_value("contrib-2", "deployment:b", "v2", at=_T0)
    ledger.assert_value("contrib-2", "deployment:c", "v3", at=_T0)
    # A different contribution must be untouched by the revert.
    other = ledger.assert_value("contrib-3", "deployment:z", "keep", at=_T0)

    appended = ledger.revert_contribution("contrib-2", reason="coordinated poisoning", at=_T1)

    assert len(appended) == 3
    assert ledger.is_reverted("contrib-2")
    assert not ledger.is_reverted("contrib-3")
    assert ledger.all_assertions()[other].belief_to is None
    # No original assertion of contrib-2 remains open.
    originals = [a for a in ledger.assertions_for("contrib-2") if not a.is_retraction]
    assert all(a.belief_to is not None for a in originals)


def test_revert_preserves_prior_belief_for_reproducibility() -> None:
    """SIG-CONTRIB-009 / §16.6: a belief time before the revert still returns the value."""
    ledger = ContributionLedger()
    ledger.assert_value("contrib-4", "deployment:okc-1", "vendor=acme", at=_T0)
    mid = _T0 + timedelta(days=10)
    ledger.revert_contribution("contrib-4", reason="error", at=_T1)

    assert ledger.value_as_of_belief("deployment:okc-1", mid) == "vendor=acme"
    assert ledger.value_as_of_belief("deployment:okc-1", _T1 + timedelta(days=1)) is None


def test_revert_requires_a_reason() -> None:
    ledger = ContributionLedger()
    ledger.assert_value("contrib-5", "s", "v", at=_T0)
    with pytest.raises(ValueError, match="reason"):
        ledger.revert_contribution("contrib-5", reason="", at=_T1)


def test_reverting_nothing_open_is_refused() -> None:
    """A revert is never a silent no-op: an unknown or already-reverted unit is refused."""
    ledger = ContributionLedger()
    with pytest.raises(NothingToRevertError):
        ledger.revert_contribution("does-not-exist", reason="x", at=_T1)

    ledger.assert_value("contrib-6", "s", "v", at=_T0)
    ledger.revert_contribution("contrib-6", reason="x", at=_T1)
    with pytest.raises(NothingToRevertError):
        ledger.revert_contribution("contrib-6", reason="again", at=_T1)


def test_ledger_has_no_delete_path() -> None:
    """SIG-CONTRIB-009: withdrawal is only ever by appending — never a deletion."""
    ledger = ContributionLedger()
    assert not hasattr(ledger, "delete")
    assert not hasattr(ledger, "remove")
