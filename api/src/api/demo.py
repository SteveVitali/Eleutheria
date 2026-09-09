# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A deterministic demo :class:`InMemoryStore` for ``sig-api serve`` and live checks.

This is illustrative fixture data — the Appendix D.2 worked case (42 contracted
vs 38 portal device counts for OKCPD) plus a correction, a sealed capture, and a
snapshot-diff pair — so a human (or the interactive verification step) can drive
every §37 surface end-to-end. Production wires a real :class:`ReadStore` to
Postgres; nothing here is canonical data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from evidence.tiers import CaptureMetadata, StorageTier
from inference.coverage import CoverageRecord
from policy.rights import RightsRecord
from policy.sensitivity import SensitivityClass
from reconcile.resolve import Claim
from reconcile.snapshot_diff import Capture

from .store import (
    ContradictionRecord,
    CrosswalkRecord,
    DossierRecord,
    EntityRecord,
    IdDescriptor,
    InMemoryStore,
    StoredClaim,
    TaskRecord,
)

_SUBJECT = "agency:okcpd"
_PREDICATE = "active_device_count"


def _claim(cid: str, value: int, *, r: str, genre: str, source_id: str) -> Claim:
    return Claim(
        claim_id=cid,
        subject_id=_SUBJECT,
        predicate_id=_PREDICATE,
        value=value,
        reliability=r,
        integrity="I1",
        genre=genre,
        observed_at=date(2026, 7, 1),
        raw_value=str(value),
        source_id=source_id,
        collection_method=genre,
    )


def build_demo_store() -> InMemoryStore:
    """Seed a store covering every §37 resource family (see module docstring)."""
    store = InMemoryStore()

    # Two independent device-count claims about OKCPD (Appendix D.2).
    store.add_claim(
        StoredClaim(
            _claim("portal", 38, r="R2", genre="portal_snapshot", source_id="src:portal"),
            asserted_at=datetime(2026, 7, 2, tzinfo=UTC),
            capture_ids=("cap:portal:1",),
        )
    )
    store.add_claim(
        StoredClaim(
            _claim("contract", 42, r="R3", genre="contract", source_id="src:records"),
            asserted_at=datetime(2026, 7, 2, tzinfo=UTC),
            capture_ids=("cap:contract:1",),
        )
    )

    # Rights records for the constituent sources (§42.4 attribution/licence).
    store.add_rights(
        RightsRecord(
            source_id="src:portal",
            spdx="CC-BY-4.0",
            attribution="Eyes on Flock portal aggregator",
            redistributable=True,
            derivative_permitted=True,
            terms_url="https://example/portal/terms",
            retrieval_date=date(2026, 7, 1),
        )
    )
    store.add_rights(
        RightsRecord(
            source_id="src:records",
            spdx="CC-BY-4.0",
            attribution="Public records request (city procurement)",
            redistributable=True,
            derivative_permitted=True,
            terms_url="https://example/records/terms",
            retrieval_date=date(2026, 7, 1),
        )
    )

    # An entity with a C3 (residential-tier) location — coordinates get reduced.
    store.add_entity(
        EntityRecord(
            entity_id=_SUBJECT,
            entity_type="agency",
            label="Oklahoma City Police Department",
            predicate_ids=(_PREDICATE,),
            source_ids=("src:portal", "src:records"),
            lat=35.4676234,
            lon=-97.5164276,
            sensitivity_class=SensitivityClass.C3,
        )
    )

    # A sealed capture: metadata public, bytes never (SIG-API-012).
    store.add_capture(
        CaptureMetadata(
            capture_id="cap:sealed:1",
            source_id="src:records",
            source_uri="https://example/records/contract.pdf",
            retrieved_at="2026-07-01",
            content_digest="b" + "0" * 40,
            media_type="application/pdf",
            tier=StorageTier.SEALED,
            claims_supported=("contract",),
            title="Vendor contract (sealed)",
            excerpt="… full text withheld …",
        ),
        artifact_id="art:contract",
    )
    store.add_capture(
        CaptureMetadata(
            capture_id="cap:portal:1",
            source_id="src:portal",
            source_uri="https://example/portal/okcpd.json",
            retrieved_at="2026-07-01",
            content_digest="a" + "0" * 40,
            media_type="application/json",
            tier=StorageTier.PUBLIC,
            claims_supported=("portal",),
            title="Portal snapshot",
            excerpt="active_device_count=38",
        ),
        artifact_id="art:portal",
    )

    # Coverage: one predicate researched, one not (an explained gap, §32.2).
    store.add_coverage(
        f"{_SUBJECT}:{_PREDICATE}",
        [
            CoverageRecord(
                predicate_id=_PREDICATE,
                absence_kind="searched_not_found",
                subject_id=_SUBJECT,
                sources_searched=("portal", "records"),
            )
        ],
    )
    store.add_coverage(
        _SUBJECT,
        [
            CoverageRecord(
                predicate_id="sharing_partners",
                absence_kind="not_researched",
                subject_id=_SUBJECT,
            )
        ],
    )

    # Two snapshots of one artifact → a /changes field event (§29.7).
    store.add_snapshot_capture(
        Capture(
            artifact_id="art:portal",
            capture_digest="a" + "0" * 40,
            captured_at=date(2026, 6, 1),
            fields={"active_device_count": 35},
        )
    )
    store.add_snapshot_capture(
        Capture(
            artifact_id="art:portal",
            capture_digest="a" + "1" * 40,
            captured_at=date(2026, 7, 1),
            fields={"active_device_count": 38},
        )
    )

    store.add_dossier(
        DossierRecord(
            scope="jurisdiction:okc",
            title="Oklahoma City surveillance dossier",
            sections=(
                {"heading": "Agencies", "entities": [_SUBJECT]},
                {"heading": "Device counts", "note": "portal 38 vs contract 42 (contradiction)"},
            ),
            source_ids=("src:portal", "src:records"),
        )
    )
    store.add_crosswalk(
        CrosswalkRecord(
            sig_id=_SUBJECT,
            external_scheme="wikidata",
            external_id="Q7112786",
            relation="exactMatch",
        )
    )
    store.add_task(
        TaskRecord(
            task_id="task:okcpd-count",
            kind="reconcile_contradiction",
            status="open",
            rationale="Portal (38) and contract (42) device counts disagree.",
            subject_id=_SUBJECT,
            predicate_id=_PREDICATE,
        )
    )
    store.add_contradiction(
        ContradictionRecord(
            contradiction_id="contradiction:okcpd-count",
            subject_id=_SUBJECT,
            predicate_id=_PREDICATE,
            kind="value_disagreement",
            state="open",
            claim_ids=("portal", "contract"),
        )
    )
    store.add_id(
        IdDescriptor(
            id_type="agency",
            uuid="okcpd",
            label="Oklahoma City Police Department",
            canonical_path=f"/v1/entity/agency/{_SUBJECT}",
            predicates={"active_device_count": "38", "jurisdiction": "Oklahoma City"},
        )
    )
    return store
