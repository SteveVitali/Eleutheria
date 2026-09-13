# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OKC vertical-slice fixture source_ids -> registry ids (P21.1, SCOPING_NUMBERS §(ii)).

Additive mapping only: the acceptance fixture
``tests/acceptance/fixtures/okc_sources.json`` is UNCHANGED. P21.1 registers the six
OKC critical-path sources; this test asserts every fixture ``source_id`` resolves to a
registered registry id so the slice is wired to real registry rows (SIG-INGEST-023/038).
"""

from __future__ import annotations

import json
from pathlib import Path

from connectors.registry import CompactStatus, CustodyPosture, get, registry
from policy.rights import is_undetermined

_FIXTURE = Path(__file__).resolve().parents[1] / "acceptance" / "fixtures" / "okc_sources.json"

# The fixture's `src:*` source_ids -> connector registry ids. `src:deflock` maps to
# the already-registered `deflock_repo`; the other six are the P21.1 OKC rows.
FIXTURE_TO_REGISTRY: dict[str, str] = {
    "src:okc-procurement": "okc_procurement",
    "src:okc-council": "okc_council",
    "src:okcpd-policy": "okcpd_policy",
    "src:ok-statute": "ok_statute",
    "src:journalrecord": "journalrecord",
    "src:oklahoman": "oklahoman",
    "src:deflock": "deflock_repo",
}

_OKC_NEW_ROWS = (
    "okc_procurement",
    "okc_council",
    "okcpd_policy",
    "ok_statute",
    "journalrecord",
    "oklahoman",
)


def _fixture_source_ids() -> set[str]:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return {a["source_id"] for a in data["artifacts"]}


def test_every_fixture_source_id_maps_to_a_registered_source() -> None:
    reg = registry()
    for fixture_id in _fixture_source_ids():
        assert fixture_id in FIXTURE_TO_REGISTRY, f"unmapped fixture source_id: {fixture_id}"
        registry_id = FIXTURE_TO_REGISTRY[fixture_id]
        assert registry_id in reg, f"{fixture_id} -> {registry_id} not registered"


_OKC_FLIPPED_GOV_ROWS = ("okc_procurement", "okc_council", "okcpd_policy", "ok_statute")
_OKC_NEWS_ROWS = ("journalrecord", "oklahoman")


def test_the_okc_government_rows_are_flipped_with_review_metadata() -> None:
    # RIGHTS.1 flip re-run (GL-GATE-03, 2026-09-10): the four OKC government-record
    # rows now carry a resolved public-domain rights block (CC0-1.0, the registry-
    # accepted expression) + full review metadata, and are flipped loadable.
    from datetime import date

    for sid in _OKC_FLIPPED_GOV_ROWS:
        rec = get(sid)
        assert not is_undetermined(rec.rights), f"{sid} should have a resolved rights block"
        assert rec.rights.spdx == "CC0-1.0"
        assert rec.rights.redistributable is True
        assert rec.rights.derivative_permitted is True
        assert rec.ingestion_permitted is True
        assert rec.rights_reviewed_by == "maintainer (delegated)"
        assert rec.rights_reviewed_on == date(2026, 9, 10)
        assert rec.last_verified == date(2026, 9, 10)
        assert rec.compact_status is CompactStatus.PUBLIC_TERMS_ONLY


def test_the_okc_news_rows_stay_undetermined_and_gated() -> None:
    # journalrecord/oklahoman stay LINK-posture per their packets (GL-GATE-03):
    # UNDETERMINED, not permitted.
    for sid in _OKC_NEWS_ROWS:
        rec = get(sid)
        assert is_undetermined(rec.rights), f"{sid} should stay UNDETERMINED"
        assert rec.ingestion_permitted is False
        assert rec.compact_status is CompactStatus.PUBLIC_TERMS_ONLY
        assert "P06.1" in rec.notes  # cites the slice precondition doc


def test_okc_government_records_are_reference_and_news_is_link() -> None:
    # Government records are REFERENCE custody; the two news publishers are
    # LINK-posture candidates (link out, never re-host content).
    for sid in ("okc_procurement", "okc_council", "okcpd_policy", "ok_statute"):
        assert get(sid).custody_posture is CustodyPosture.REFERENCE
    for sid in ("journalrecord", "oklahoman"):
        assert get(sid).custody_posture is CustodyPosture.LINK


def test_okc_council_uses_the_civicclerk_oklahomacityok_tenant() -> None:
    # okc_council flows through the CivicClerk tenant seeded in agenda_tenants.toml.
    assert "civicclerk" in get("okc_council").access_method.lower()
    assert "oklahomacityok" in get("okc_council").access_method
