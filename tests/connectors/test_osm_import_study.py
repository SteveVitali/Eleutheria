# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The sous-surveillance.net → OSM import study and its contribution gate (§35.2, P18.2).

SIG-CONTRIB-016: the ~12,000-camera import MUST be studied — its conventions, its
community consultation, and its outcome documented — BEFORE any SIG-originated
contribution at scale is proposed. These tests assert the study is complete and that
the gate refuses a scaled-contribution proposal when it is not.
"""

from __future__ import annotations

import dataclasses

import pytest

from connectors import osm_import_study as st


def test_study_documents_conventions_consultation_and_outcome() -> None:
    # AC4: the three required sections are each documented (SIG-CONTRIB-016).
    study = st.import_study()
    assert study.is_complete()
    assert study.missing_sections() == []
    assert set(study.documented_sections()) == set(st.REQUIRED_SECTIONS)
    assert all(study.documented_sections().values())


def test_study_carries_the_reconciliation_join_key() -> None:
    # SIG reconciles against OSM via the surviving upstream id, not a re-import (F9.7).
    assert st.import_study().join_key == "ref:sous-surveillance_net"


def test_study_corrects_the_outline_number_and_actor_attribution() -> None:
    # F9.6/F9.7: the outline's ~12,000 + Technopolice attribution are both corrected.
    corrections = st.import_study().corrections
    assert "18,000" in corrections["corrected_number"]
    assert "OpenStreetMap Belgium" in corrections["corrected_actor"]
    assert "Vucod" in corrections["corrected_actor"]


def test_conventions_capture_the_distance_banded_conflation_rule() -> None:
    # The field-tested reconciliation default SIG adopts (F9.12).
    conventions = st.import_study().conventions
    assert "excluded" in conventions["conflation_under_5m"]
    assert "fixme" in conventions["conflation_5m_to_10m"]
    assert conventions["field_crosswalk"]["id_camera"] == "ref:sous-surveillance_net"


def test_gate_permits_a_scaled_contribution_once_the_import_is_studied() -> None:
    # The study is complete, so proposing (not executing) a scaled contribution is
    # permitted; the returned study is the completed one.
    study = st.assert_import_studied_before_scaled_contribution(
        {"description": "operator attribution across imported FR cameras"}
    )
    assert study.is_complete()


def test_gate_refuses_a_scaled_contribution_when_a_section_is_undocumented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SIG-CONTRIB-016: with the outcome section not yet documented, a scaled
    # contribution MUST be refused, naming the missing section.
    complete = st.import_study()
    incomplete = dataclasses.replace(complete, outcome={"documented": False})
    monkeypatch.setattr(st, "import_study", lambda: incomplete)
    with pytest.raises(st.ImportNotStudied) as excinfo:
        st.assert_import_studied_before_scaled_contribution({"description": "bulk edit"})
    assert "outcome" in str(excinfo.value)
