# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-INGEST-008: manual-acquisition dependencies are modelled, never fetched.

The committed registry loads under ``sig.manual-acquisitions/1``; the validate
self-check fails closed on either direction of the model rule (a source
declaring manual acquisition with no record; a record naming a non-manual
source) and on provenance dishonesty (an acquired row missing DOI/identifier,
version or checksum; a pending row claiming acquisition fields). ``run_source``
refuses a registered manual dependency in EVERY mode — there is no automatic
fetch path for it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from connectors.manual_acquisition import (
    ManualAcquisition,
    ManualAcquisitionRequired,
    _record_violations,
    assert_automatic_acquirable,
    is_manual_access_method,
    manual_acquisition_violations,
    manual_acquisitions,
)
from connectors.runner import run_source


def _dep(**over: object) -> ManualAcquisition:
    base = dict(
        id="d1",
        source_id="s1",
        identifier="Pub study 1",
        doi="",
        version="",
        sha256="",
        acquired_at="",
        status="pending",
        access="login → download",
        runbook="docs/ops/manual-acquisition.md",
        notes="",
    )
    base.update(over)
    return ManualAcquisition(**base)  # type: ignore[arg-type]


def test_committed_registry_loads_and_is_consistent() -> None:
    """The committed registry parses and its violations list is empty."""
    deps = manual_acquisitions()
    assert {d.id for d in deps}  # non-empty
    assert manual_acquisition_violations() == []


def test_every_manual_source_has_a_record_and_vice_versa() -> None:
    deps = manual_acquisitions()
    assert all(d.source_id for d in deps)
    assert all(d.status in ("pending", "acquired") for d in deps)


def test_access_method_marker() -> None:
    assert is_manual_access_method("manual acquisition (login)")
    assert is_manual_access_method("Manual download")
    assert not is_manual_access_method("direct download (https .zip)")
    assert not is_manual_access_method("")


def test_acquired_row_requires_provenance() -> None:
    dep = _dep(status="acquired")
    violations = _record_violations(dep, {"s1"})
    assert any("version" in v for v in violations)
    assert any("sha256" in v for v in violations)
    assert any("acquired_at" in v for v in violations)


def test_acquired_row_complete_passes() -> None:
    dep = _dep(
        status="acquired",
        doi="10.1234/study.1",
        version="v1",
        sha256="a" * 64,
        acquired_at="2026-01-01",
    )
    assert _record_violations(dep, {"s1"}) == []


def test_pending_row_with_provenance_is_a_fabrication() -> None:
    dep = _dep(status="pending", sha256="b" * 64)
    assert any("pending but sha256 populated" in v for v in _record_violations(dep, {"s1"}))


def test_bad_sha256_and_unknown_source_and_status() -> None:
    dep = _dep(status="acquired", version="v1", sha256="nothex", acquired_at="d")
    violations = _record_violations(dep, {"other"})
    assert any("not a 64-hex digest" in v for v in violations)
    assert any("not in the committed source registry" in v for v in violations)
    weird = _dep(status="lost")
    assert any("not in" in v for v in _record_violations(weird, {"s1"}))


def test_run_source_refuses_a_manual_dependency_every_mode(tmp_path: Path) -> None:
    """SIG-INGEST-008: the build MUST NOT assume a manual dep is fetchable."""
    fixture = tmp_path / "f.json"
    fixture.write_text("{}")
    for mode in ("live", "replay", "shadow"):
        with pytest.raises(ManualAcquisitionRequired, match="manual-acquisition"):
            run_source("leaic_crosswalk", mode=mode, fixture=fixture)


def test_assert_automatic_acquirable_names_the_runbook() -> None:
    with pytest.raises(ManualAcquisitionRequired, match="runbook|manual-acquisition"):
        assert_automatic_acquirable("leaic_crosswalk")
