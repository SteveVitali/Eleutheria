# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rights-review status + the flip-metadata rule (P21.1, SIG-INGEST-028/038, SIG-LIC-001/009)."""

from __future__ import annotations

import contextlib
import io
from datetime import date

import pytest
from connectors.cli import main
from connectors.registry import (
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    SourceRecord,
    sources,
)
from connectors.review import (
    flip_ready,
    gate_breakdown,
    is_flip_ready,
    review_metadata_violations,
)
from policy.rights import UNDETERMINED, RightsRecord


def _record(
    source_id: str,
    *,
    permitted: bool,
    spdx: str = "CC0-1.0",
    reviewed_by: str = "licensing reviewer",
    reviewed_on: date | None = date(2026, 9, 10),
    last_verified: date | None = date(2026, 9, 10),
    custody: CustodyPosture = CustodyPosture.REFERENCE,
    compact: CompactStatus = CompactStatus.PUBLIC_TERMS_ONLY,
    redistributable: bool = True,
) -> SourceRecord:
    rights = RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution="test" if spdx != UNDETERMINED else "",
        redistributable=redistributable,
        derivative_permitted=True,
        terms_url="https://example.test/terms" if spdx != UNDETERMINED else "",
        retrieval_date=date(2026, 9, 10),
    )
    return SourceRecord(
        id=source_id,
        name=f"test {source_id}",
        source_kind=SourceKind.GOVERNMENT_PORTAL,
        homepage_url="https://example.test/",
        default_tier="R1",
        custody_posture=custody,
        compact_status=compact,
        robots_policy=RobotsPolicy.HONOR,
        rights=rights,
        ingestion_permitted=permitted,
        rights_reviewed_by=reviewed_by,
        rights_reviewed_on=reviewed_on,
        last_verified=last_verified,
    )


# --- The flip-metadata rule (SIG-INGEST-028/038, SIG-LIC-001) -----------------


def test_flip_without_reviewed_by_is_a_validation_violation_naming_the_id() -> None:
    bad = _record("test_flip_no_reviewer", permitted=True, reviewed_by="")
    violations = review_metadata_violations([bad])
    assert len(violations) == 1
    assert "test_flip_no_reviewer" in violations[0]
    assert "rights_reviewed_by" in violations[0]


def test_flip_without_rights_block_is_a_violation() -> None:
    bad = _record(
        "test_flip_undetermined", permitted=True, spdx=UNDETERMINED, redistributable=False
    )
    (msg,) = review_metadata_violations([bad])
    assert "test_flip_undetermined" in msg
    assert "resolved rights block" in msg


def test_flip_without_reviewed_on_or_last_verified_is_a_violation() -> None:
    bad = _record("test_flip_no_dates", permitted=True, reviewed_on=None, last_verified=None)
    (msg,) = review_metadata_violations([bad])
    assert "rights_reviewed_on" in msg
    assert "last_verified" in msg


def test_a_fully_reviewed_flip_is_not_a_violation() -> None:
    good = _record("test_flip_ok", permitted=True)
    assert review_metadata_violations([good]) == []


def test_unpermitted_rows_are_never_violations_even_without_metadata() -> None:
    # A source that is not flipped needs no review metadata (additive/back-compat).
    row = _record("test_unpermitted", permitted=False, reviewed_by="", reviewed_on=None)
    assert review_metadata_violations([row]) == []


def test_the_seeded_registry_has_no_flip_metadata_violations() -> None:
    # Nothing is flipped in the seed, so the rule holds registry-wide.
    assert review_metadata_violations(sources()) == []


# --- validate wires the rule (AC: validate fails naming the id) ---------------


def test_validate_passes_on_the_seeded_registry(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate"]) == 0
    out = capsys.readouterr().out
    assert "registered sources: 118" in out
    assert "self-checks OK" in out


def test_validate_fails_naming_the_offending_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # A row flipped to ingestion_permitted=true but lacking rights_reviewed_by
    # makes `sig-connectors validate` fail, naming the id (SIG-INGEST-028/038).
    bad = _record("okc_procurement_test_flip", permitted=True, reviewed_by="")
    monkeypatch.setattr(
        "connectors.cli.review_metadata_violations",
        lambda srcs: [
            f"source {bad.id!r} has ingestion_permitted=true but is missing rights_reviewed_by"
        ],
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["validate"])
    assert code == 1
    assert "VALIDATION FAILED" in buf.getvalue()
    assert "okc_procurement_test_flip" in buf.getvalue()


# --- flip-ready + loadable counts (AC: flip-ready 18, loadable 0 == validate) -


def test_review_status_prints_flip_ready_18_and_loadable_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["review-status"]) == 0
    out = capsys.readouterr().out
    assert "registered sources: 118" in out
    assert "flip-ready: 18" in out
    assert "loadable now: 0" in out


def test_review_status_loadable_equals_validate() -> None:
    # review-status' loadable-now count must equal validate's (both = is_loadable).
    from connectors.loader import is_loadable

    loadable = [s for s in sources() if is_loadable(s)]
    assert len(loadable) == 0
    assert len(flip_ready()) == 18


def test_flip_ready_excludes_permitted_and_undetermined_and_link() -> None:
    permitted = _record("t_perm", permitted=True)
    undetermined = _record("t_und", permitted=False, spdx=UNDETERMINED, redistributable=False)
    link = _record("t_link", permitted=False, custody=CustodyPosture.LINK)
    ready = _record("t_ready", permitted=False)
    assert is_flip_ready(ready) is True
    assert is_flip_ready(permitted) is False  # flag already true
    assert is_flip_ready(undetermined) is False  # no rights block
    assert is_flip_ready(link) is False  # link-only custody


def test_review_status_single_source_shows_five_gate_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["review-status", "--source", "osm_overpass"]) == 0
    out = capsys.readouterr().out
    for field in ("ingestion_permitted=", "compact=", "custody=", "rights=", "reviewed-by="):
        assert field in out
    # osm_overpass is flip-ready: rights + compact + custody all true, flag false.
    assert "flip-ready: True" in out
    assert "loadable now: False" in out


def test_review_status_unknown_source_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["review-status", "--source", "no_such_source"]) == 2


def test_gate_breakdown_reports_all_five_fields() -> None:
    bd = gate_breakdown(_record("t", permitted=False))
    assert bd.compact_ok and bd.custody_ok and bd.rights_present and bd.reviewed_by
    assert bd.ingestion_permitted is False
    assert bd.flip_ready is True
    assert bd.loadable is False
