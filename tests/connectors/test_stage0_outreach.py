# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Stage-0 outreach record consistency (P21.1, SIG-CONTRIB-012/012a/013, SIG-INGEST-027)."""

from __future__ import annotations

import re
from pathlib import Path

from connectors.registry import CompactStatus, registry

_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _ROOT / "docs/build/reports/STAGE0_OUTREACH_RECORD.md"
_LETTER = _ROOT / "docs/governance/stage0-outreach-letter.md"

_VALID_OUTCOMES = {c.value for c in CompactStatus}
# A source whose compact_status is one of these does NOT require a contacted record row.
_DEFAULT_STATES = {"not_contacted", "public_terms_only"}


def _rows() -> list[tuple[str, str, str, list[str]]]:
    """Parse the record table into (project, contact, outcome, [governed ids])."""
    rows: list[tuple[str, str, str, list[str]]] = []
    in_table = False
    for line in _RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("| # | project |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6 or cells[0] == "#":
                continue
            _num, project, contact, _date, outcome, governs = cells[:6]
            ids = re.findall(r"`([a-z0-9_]+)`", governs)
            rows.append((project, contact, outcome, ids))
    return rows


def test_record_has_exactly_19_project_rows() -> None:
    # The 19 federation-compact projects (spec §6 / §35.1).
    assert len(_rows()) == 19


def test_every_outcome_is_in_the_closed_compact_vocabulary() -> None:
    for _project, _contact, outcome, _ids in _rows():
        assert outcome in _VALID_OUTCOMES, f"unknown outcome {outcome!r}"


def test_gate_skipped_no_fabricated_permission_or_partnership() -> None:
    # HG-04 = SKIP: no outreach performed, so no granted/declined/partnership outcome
    # may appear. Only not_contacted / public_terms_only, plus the pre-existing
    # no_response (FlockReporter, SIG-INGEST-039b) are allowed this run.
    allowed = _DEFAULT_STATES | {"no_response"}
    for project, _contact, outcome, _ids in _rows():
        assert outcome in allowed, f"{project}: unexpected fabricated outcome {outcome!r}"


def test_governed_ids_exist_in_the_registry_or_are_flagged_local() -> None:
    reg = registry()
    for project, _contact, _outcome, ids in _rows():
        for sid in ids:
            # Local-group ids may live in local_groups.toml rather than sources.toml;
            # the row flags that explicitly. Everything else must be a registry id.
            if sid in reg:
                continue
            assert project.startswith("Local") or "eyes_off" in sid, (
                f"{project}: governed id {sid!r} is not a registered source"
            )


def test_every_contacted_source_has_a_matching_record_row() -> None:
    # THE consistency requirement (P21.1 deliverable 6): every sources.toml row whose
    # compact_status != not_contacted/public_terms_only has a matching record row whose
    # outcome equals that status. Today the only such row is flockreporter (no_response).
    reg = registry()
    rows = _rows()
    for sid, rec in reg.items():
        status = rec.compact_status.value
        if status in _DEFAULT_STATES:
            continue
        matching = [(project, outcome) for project, _contact, outcome, ids in rows if sid in ids]
        assert matching, f"contacted source {sid!r} ({status}) has no Stage-0 record row"
        assert any(outcome == status for _project, outcome in matching), (
            f"{sid!r} is {status} in the registry but no record row records that outcome"
        )


def test_flockreporter_no_response_is_recorded() -> None:
    # The one non-default state must surface honestly (append-only, not rewritten).
    rows = _rows()
    fr = [outcome for _p, _c, outcome, ids in rows if "flockreporter" in ids]
    assert fr == ["no_response"]


def test_no_personal_names_only_org_channels() -> None:
    # Part VIII §0.7: contact channels are organisational addresses only. Heuristic:
    # every contact cell is a URL or an org/role email, never "Firstname Lastname".
    for project, contact, _outcome, _ids in _rows():
        assert "http" in contact or "@" in contact or "." in contact, (
            f"{project}: contact channel does not look like a public org address: {contact!r}"
        )
        # A bare "Firstname Lastname" pattern (two capitalised words alone) is forbidden.
        assert not re.fullmatch(r"[A-Z][a-z]+ [A-Z][a-z]+", contact), (
            f"{project}: contact looks like a personal name: {contact!r}"
        )


def test_outreach_letter_template_exists_and_states_the_offer() -> None:
    text = _LETTER.read_text(encoding="utf-8")
    assert "SIG-CONTRIB-013" in text  # archival succession offer
    assert "archival succession" in text.lower()
    assert "opt-out" in text.lower()  # explicit opt-out
    assert "will NOT" in text or "not compete" in text.lower()  # non-competition
