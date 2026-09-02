# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared fixtures for the public read API tests (P14.1, §37).

The store is the demo scenario (Appendix D.2 OKCPD device counts) extended with
the cases the acceptance criteria need: a C2 asset (coordinates truncated), a C4
asset (jurisdiction only), a restricted entity, and a second, incompatibly-
licensed source (ODbL) so the licence statement can be exercised both ways.
"""

from __future__ import annotations

from datetime import date

import pytest
from api.demo import build_demo_store
from api.store import EntityRecord, InMemoryStore
from evidence.tiers import CaptureMetadata, StorageTier
from policy.rights import RightsRecord
from policy.sensitivity import SensitivityClass
from starlette.testclient import TestClient

from api import create_app


@pytest.fixture
def store() -> InMemoryStore:
    s = build_demo_store()
    # A C2 asset: coordinates are published truncated to 2 dp (geo tier 1).
    s.add_entity(
        EntityRecord(
            entity_id="asset:c2",
            entity_type="asset",
            label="Hidden sensor (C2)",
            lat=35.4676234,
            lon=-97.5164276,
            sensitivity_class=SensitivityClass.C2,
        )
    )
    # A C4 asset: jurisdiction only, no coordinates ever (geo tier 3).
    s.add_entity(
        EntityRecord(
            entity_id="asset:c4",
            entity_type="asset",
            label="Confidential facility (C4)",
            lat=35.4676234,
            lon=-97.5164276,
            sensitivity_class=SensitivityClass.C4,
        )
    )
    # A restricted entity: not served through any tier (SIG-API-011).
    s.add_entity(
        EntityRecord(
            entity_id="agency:restricted",
            entity_type="agency",
            label="Restricted agency",
            visibility=StorageTier.RESTRICTED,
        )
    )
    # An ODbL source that cannot be merged with the CC-BY graph (SIG-LIC-004a).
    s.add_rights(
        RightsRecord(
            source_id="src:osm",
            spdx="ODbL-1.0",
            attribution="OpenStreetMap contributors",
            redistributable=True,
            derivative_permitted=True,
            terms_url="https://www.openstreetmap.org/copyright",
            retrieval_date=date(2026, 7, 1),
        )
    )
    # A restricted capture: metadata public, excerpt redacted, bytes never (SIG-EVID-010).
    s.add_capture(
        CaptureMetadata(
            capture_id="cap:restricted:1",
            source_id="src:records",
            source_uri="https://example/records/restricted.pdf",
            retrieved_at="2026-07-01",
            content_digest="c" + "0" * 40,
            media_type="application/pdf",
            tier=StorageTier.RESTRICTED,
            claims_supported=("contract",),
            title="Restricted memo",
            excerpt="sensitive body text",
        ),
        artifact_id="art:contract",
    )
    return s


@pytest.fixture
def client(store: InMemoryStore) -> TestClient:
    return TestClient(create_app(store))
