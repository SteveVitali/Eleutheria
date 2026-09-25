# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""AC3 — a belief-pinned request is reproducible after a correction (SIG-API-006).

Pin ``as_of_belief`` to a past instant, apply a correction (a NEW claim asserted
later — append-only, never an edit), and the pinned request returns the identical
pre-correction result. A now-pinned request, by contrast, sees the correction.
"""

from __future__ import annotations

from datetime import UTC, datetime

from api.store import InMemoryStore
from starlette.testclient import TestClient

# A belief instant before any correction, and the later instant a correction is
# asserted at (mirrors the demo timeline in conftest.build fixtures).
BELIEF_BEFORE_CORRECTION = datetime(2026, 7, 3, tzinfo=UTC)
CORRECTION_ASSERTED_AT = datetime(2026, 8, 1, tzinfo=UTC)

_URL = "/v1/resolution/agency:okcpd/active_device_count"
_PINNED = {"as_of_belief": BELIEF_BEFORE_CORRECTION.isoformat()}


def test_belief_pinned_request_is_reproducible_after_a_correction(
    client: TestClient, store: InMemoryStore
) -> None:
    before = client.get(_URL, params=_PINNED).json()["fact"]["envelope"]

    # A correction: the portal claim is re-asserted as 50, AFTER the pinned belief.
    store.correct_claim("portal", value=50, asserted_at=CORRECTION_ASSERTED_AT)

    after = client.get(_URL, params=_PINNED).json()["fact"]["envelope"]

    # Identical: value, supporting/dissenting sets, and the decision-bearing fields.
    assert after["value"] == before["value"]
    assert after["supporting_claim_ids"] == before["supporting_claim_ids"]
    assert after["dissenting_claim_ids"] == before["dissenting_claim_ids"]
    assert after["input_digest"] == before["input_digest"]
    assert after["ruleset_version"] == before["ruleset_version"]


def test_now_pinned_request_sees_the_correction(client: TestClient, store: InMemoryStore) -> None:
    baseline = client.get(_URL).json()["fact"]["envelope"]
    store.correct_claim("portal", value=50, asserted_at=CORRECTION_ASSERTED_AT)
    now = client.get(_URL).json()["fact"]["envelope"]
    # The correction moved the resolution; a now-pinned read is not cached and
    # reflects it (SIG-API-006). Since P31.8 completed the genre axis the
    # contract's figure is admissible (D5, §10.5's own example: weak support for
    # the CURRENT count, capped W1 — contracted_device_count's job is the
    # contract's quantity), so the corrected 50 vs the contract's 42 is a spread
    # beyond the FAST relative tolerance (U4): the honest outcome is UNRESOLVED
    # with the corrected claim leading and both values kept visible — never a
    # silently merged answer.
    assert now["value"] != baseline["value"]
    assert now["resolution_status"] == "UNRESOLVED"
    assert now["unresolved_code"] == "U4"
    corrected = f"portal~corrected@{CORRECTION_ASSERTED_AT.isoformat()}"
    assert now["supporting_claim_ids"] == [corrected]
    assert now["dissenting_claim_ids"] == ["contract"]
    assert corrected in now["considered_claim_ids"]


def test_a_correction_is_a_new_claim_never_an_edit(store: InMemoryStore) -> None:
    """Append-only (P1–P3): the original claim survives the correction."""
    original = store.stored_claim("portal")
    assert original is not None and original.claim.value == 38
    store.correct_claim("portal", value=50, asserted_at=CORRECTION_ASSERTED_AT)
    # The original is untouched; the correction is a distinct, later-asserted claim.
    assert store.stored_claim("portal").claim.value == 38
