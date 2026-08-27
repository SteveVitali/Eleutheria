# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector-loader gate: ingestion, compact, custody, export (SIG-INGEST-014, SIG-LIC-010)."""

from __future__ import annotations

import dataclasses

import pytest
from connectors.loader import (
    IngestionNotPermitted,
    LicenseIncompatibilityError,
    assert_export_compatible,
    assert_loadable,
    compact_permits_ingestion,
    custody_permits_fetch,
    is_loadable,
)
from connectors.registry import CompactStatus, CustodyPosture, get


def _permit(source_id: str):  # type: ignore[no-untyped-def]
    return dataclasses.replace(get(source_id), ingestion_permitted=True)


def test_gate_passes_when_all_three_conditions_hold() -> None:
    # eyes_on_flock: MIRROR + public_terms_only; only ingestion_permitted was missing.
    record = _permit("eyes_on_flock")
    assert assert_loadable(record) is record
    assert is_loadable(record)


def test_gate_refuses_when_ingestion_not_permitted() -> None:
    # SIG-INGEST-028: ingestion_permitted defaults false; the gate fails closed.
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(get("eyes_on_flock"))


def test_gate_refuses_when_compact_denies() -> None:
    # SIG-INGEST-014/027: a compact_status that does not permit ingestion refuses.
    denied = dataclasses.replace(
        get("eyes_on_flock"),
        ingestion_permitted=True,
        compact_status=CompactStatus.NO_RESPONSE,
    )
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(denied)
    assert not is_loadable(denied)


def test_gate_refuses_link_only_custody() -> None:
    # SIG-INGEST-014 / §8.4: LINK custody means never fetch/store content.
    link_only = dataclasses.replace(
        get("eyes_on_flock"),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.LINK,
    )
    with pytest.raises(IngestionNotPermitted):
        assert_loadable(link_only)


def test_compact_and_custody_predicates() -> None:
    assert compact_permits_ingestion(CompactStatus.PERMISSION_GRANTED)
    assert compact_permits_ingestion(CompactStatus.PUBLIC_TERMS_ONLY)
    assert not compact_permits_ingestion(CompactStatus.NO_RESPONSE)
    assert not compact_permits_ingestion(CompactStatus.PERMISSION_DECLINED)
    assert custody_permits_fetch(CustodyPosture.MIRROR)
    assert not custody_permits_fetch(CustodyPosture.LINK)


def test_export_of_compatible_compartment_computes_a_licence() -> None:
    # SIG-LIC-010: a set within one compartment computes to a single licence.
    licence = assert_export_compatible(["osm_taginfo", "osm_overpass"])
    assert licence == "ODbL-1.0"


def test_export_mixing_incompatible_compartments_fails_the_build() -> None:
    # SIG-LIC-010: ODbL-1.0 and CC-BY-SA-4.0 cannot be merged — the build fails.
    with pytest.raises(LicenseIncompatibilityError):
        assert_export_compatible(["osm_taginfo", "eyes_on_flock"])
