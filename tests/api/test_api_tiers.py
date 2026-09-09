# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-011 — access tiers, and no tier reaches restricted/sealed material.

Tiers change rate limits, not what classes of data are reachable: anonymous,
registered, and partner all get a 404 on a restricted entity through the public
API. The public data is reachable at every tier.
"""

from __future__ import annotations

import pytest
from api.tiers import AccessTier, assert_public_visibility, tier_dependency
from evidence.tiers import StorageTier
from starlette.testclient import TestClient

_PARTNER = {"Authorization": "Bearer partner-demo-key"}
_REGISTERED = {"Authorization": "Bearer registered-demo-key"}


def test_bearer_token_maps_to_a_tier() -> None:
    assert tier_dependency("Bearer partner-demo-key") is AccessTier.PARTNER
    assert tier_dependency("Bearer registered-demo-key") is AccessTier.REGISTERED
    assert tier_dependency(None) is AccessTier.ANONYMOUS
    assert tier_dependency("Bearer nonsense") is AccessTier.ANONYMOUS


@pytest.mark.parametrize("headers", [{}, _REGISTERED, _PARTNER])
def test_no_tier_can_read_a_restricted_entity(client: TestClient, headers: dict[str, str]) -> None:
    r = client.get("/v1/entity/agency/agency:restricted", headers=headers)
    assert r.status_code == 404


@pytest.mark.parametrize("headers", [{}, _REGISTERED, _PARTNER])
def test_public_data_is_reachable_at_every_tier(
    client: TestClient, headers: dict[str, str]
) -> None:
    r = client.get("/v1/entity/agency/agency:okcpd", headers=headers)
    assert r.status_code == 200


def test_the_visibility_gate_is_tier_independent() -> None:
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        with pytest.raises(Exception):  # noqa: B017 - HTTPException(404) either way
            assert_public_visibility(tier)
    # public passes for everyone (does not raise).
    assert assert_public_visibility(StorageTier.PUBLIC) is None
