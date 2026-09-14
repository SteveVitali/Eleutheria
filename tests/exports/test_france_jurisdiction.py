# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France jurisdiction export + dossier (P24.6 / JURIS.2 / GL-JURIS-01).

The second jurisdiction's publish path: the licence compartments hold in the
second jurisdiction (arrêté rows ride the recorded ODbL — share-alike, never
merged with the CC-BY graph), the DECP content stays OUT while its rights are
UNDETERMINED (the gate exercised, not bypassed), and the FR-GDPR publication
gate withholds the signing-officer name where the US dossier publishes it
(SIG-PUB-017 — Part VIII on the new jurisdiction's data).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from exports.cli import _france_request, _jurisdiction_request
from exports.web_dossier import _france_dossier, build_web_dossiers

REPO_ROOT = Path(__file__).resolve().parents[2]

# The twelve §39.2 dossier sections the web contract requires.
REQUIRED_SECTIONS = {
    "at_a_glance",
    "what_is_deployed",
    "cost_and_expiry",
    "who_else_can_see",
    "configuration_and_retention",
    "usage",
    "where_the_hardware_is",
    "policy",
    "accountability_events",
    "timeline",
    "what_we_dont_know",
    "how_we_know_this",
}


def test_france_is_a_buildable_jurisdiction() -> None:
    request = _jurisdiction_request("france")
    assert request["build_spec"]["ruleset_version"]
    assert _jurisdiction_request("okc")["tables"]  # the OKC path is unchanged


def test_unknown_jurisdiction_still_refuses() -> None:
    with pytest.raises(ValueError, match="no jurisdiction export request"):
        _jurisdiction_request("atlantis")
    with pytest.raises(ValueError, match="no jurisdiction dossier bundle"):
        build_web_dossiers("atlantis")


def test_france_request_rights_records() -> None:
    rights = {r["source_id"]: r for r in _france_request()["rights"]}
    assert rights["raa_prefectures"]["spdx"] == "ODbL-1.0"
    assert rights["raa_prefectures"]["redistributable"] is True
    assert rights["sig"]["spdx"] == "CC-BY-4.0"
    # No UNDETERMINED rights row — the export carries only resolved licences.
    assert all(r["spdx"] != "UNDETERMINED" for r in rights.values())


def test_france_export_excludes_decp_content() -> None:
    # DECP rights are UNDETERMINED: the honest posture is a recorded gap, not a
    # re-published row (§42 fail-closed). No export row may cite `decp_fr`.
    for table in _france_request()["tables"]:
        for row in table["rows"]:
            assert row["source_id"] != "decp_fr"
            blob = json.dumps(row["data"])
            assert "50754" not in blob


def test_france_export_bundle_keeps_the_odbl_compartment_separate(
    tmp_path: Path,
) -> None:
    # Build the real bundle: legal_instruments lands in the ODbL compartment
    # (share-alike), claims in the CC-BY graph — the compartments never merge.
    out = tmp_path / "export"
    rc = subprocess.run(
        ["uv", "run", "sig-exports", "build", "--jurisdiction", "france", "--out", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr
    assert (out / "osm_physical").is_dir()
    assert (out / "sig_graph").is_dir()
    assert (out / "osm_physical" / "legal_instruments.jsonl").exists()
    assert (out / "sig_graph" / "claims.jsonl").exists()
    datapackage = json.loads((out / "datapackage.json").read_text())
    assert {lic["name"] for lic in datapackage["licenses"]} == {"CC-BY-4.0", "ODbL-1.0"}
    # The arrêté table carries ODbL inside its own compartment directory.
    resource = next(r for r in datapackage["resources"] if r["name"] == "legal_instruments.csv")
    assert resource["path"].startswith("osm_physical/")
    assert {lic["name"] for lic in resource["licenses"]} == {"ODbL-1.0"}
    dossiers = json.loads((out / "web" / "dossiers.json").read_text())
    assert dossiers[0]["slug"] == "gex-videoprotection"


def test_france_dossier_is_a_valid_twelve_section_dossier() -> None:
    dossier = _france_dossier()
    assert dossier["jurisdictionCode"] == "FR"
    assert dossier["lang"] == "fr"  # its own BCP-47 language
    assert dossier["slug"] == "gex-videoprotection"
    assert {s["section_id"] for s in dossier["sections"]} == REQUIRED_SECTIONS


def test_france_dossier_flags_the_officer_name_for_fr_gdpr_withholding() -> None:
    # Part VIII on the second jurisdiction's data: the signing-officer row is
    # flagged isPublicEmployeeName + originJurisdiction FR, and the FR adapter
    # withholds it — where the US dossier publishes the equivalent name.
    from policy.jurisdiction import adapter_publication_permitted, get

    adapter = get("FR")
    assert adapter.publication_profile == "FR-GDPR"
    assert not adapter_publication_permitted(adapter, "FR", is_public_employee_name=True)
    # The US contrast stands: the same row publishes under US-DEFAULT.
    us = get("US")
    assert adapter_publication_permitted(us, "US", is_public_employee_name=True)

    name_rows = [
        row
        for section in _france_dossier()["sections"]
        for row in section.get("rows", [])
        if row.get("isPublicEmployeeName")
    ]
    assert name_rows, "the dossier must carry a flagged officer-name row"
    assert all(r.get("originJurisdiction") == "FR" for r in name_rows)


def test_france_dossier_records_the_decp_rights_gap() -> None:
    dossier = _france_dossier()
    blob = json.dumps(dossier)
    assert '"UNRESOLVED"' in blob
    assert "decp" in blob.lower() or "DECP" in blob


def test_france_dossier_absence_kinds_are_registered() -> None:
    # The web renderer fails closed on an unknown AbsenceKind — every `absence`
    # and `kind` in the dossier must be one of the four §9.5 kinds.
    registered = {
        "NOT_RESEARCHED",
        "NO_EVIDENCE_FOUND",
        "EVIDENCE_OF_ABSENCE",
        "UNRESOLVED",
    }
    dossier = _france_dossier()
    for gap in dossier.get("gaps", []):
        assert gap["kind"] in registered, gap
    for section in dossier["sections"]:
        for row in section.get("rows", []):
            if "absence" in row:
                assert row["absence"] in registered, row


def test_france_dossier_contains_no_real_person_name() -> None:
    # The officer row names the office, not a person ("M. le préfet de l'Ain") —
    # Part VIII: even the withheld value is a role, not an individual.
    name_rows = [
        row
        for section in _france_dossier()["sections"]
        for row in section.get("rows", [])
        if row.get("isPublicEmployeeName")
    ]
    for row in name_rows:
        assert "préfet" in row["value"] or "prefet" in row["value"].lower()
