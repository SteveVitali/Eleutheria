# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The prose governance policies are published and linked (§45/§46/§34.3, SIG-GOV/CONTRIB)."""

from __future__ import annotations

import pytest
from support import REPO_ROOT

GOV_DIR = REPO_ROOT / "docs" / "governance"
INDEX = GOV_DIR / "README.md"

# The governance documents this ticket (P00.3) must publish.
GOV_DOCS = (
    "takedown-corrections-suppression.md",
    "governance-and-code-of-conduct.md",
    "anti-misuse-statement.md",
    "contributor-safety.md",
)


@pytest.mark.parametrize("name", GOV_DOCS)
def test_governance_document_is_published(name: str) -> None:
    path = GOV_DIR / name
    assert path.is_file(), f"missing governance document: docs/governance/{name}"
    assert path.read_text(encoding="utf-8").strip(), f"docs/governance/{name} is empty"


@pytest.mark.parametrize("name", GOV_DOCS)
def test_governance_document_is_linked_from_the_index(name: str) -> None:
    # Every policy document is linked from the repo (SIG-GOV-014 / Phase 0 AC):
    # the governance index links each one, and the repo README links the index.
    index = INDEX.read_text(encoding="utf-8")
    assert f"]({name})" in index, f"docs/governance/{name} is not linked from the index"


def test_repo_readme_links_the_governance_dir() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/governance/" in readme


def test_anti_misuse_statement_published_verbatim() -> None:
    # SIG-GOV-019: the statement is a first-class page addressing the tension
    # honestly, published verbatim in SIG's own voice. Presence check on the exact
    # spec sentences that carry the position.
    text = " ".join((GOV_DIR / "anti-misuse-statement.md").read_text(encoding="utf-8").split())
    verbatim = (
        "SIG's position is that public knowledge of publicly deployed "
        "infrastructure is legitimate and necessary for democratic oversight; "
        "that the same information is already available to anyone who drives the "
        "road and looks; and that the alternative \u2014 infrastructure that "
        "watches the public while remaining unknown to it \u2014 is the condition "
        "the project exists to remedy."
    )
    assert verbatim in text, "SIG-GOV-019 statement is not published verbatim"
    assert "Mapping surveillance infrastructure does inherently make avoidance easier." in text


def test_contributor_safety_documents_pseudonymity_and_pii_window() -> None:
    # SIG-CONTRIB-005..008: PII-minimisation window, pseudonymity, know-your-rights /
    # no-interference, and the detained-contributor policy.
    raw = (GOV_DIR / "contributor-safety.md").read_text(encoding="utf-8").lower()
    text = " ".join(raw.split())
    assert "pseudonym" in text  # matches "pseudonymity"/"pseudonymous"/"pseudonym"
    assert "pii-minimisation window" in text
    for req in ("sig-contrib-005", "sig-contrib-006", "sig-contrib-007", "sig-contrib-008"):
        assert req in text, f"contributor-safety.md does not cite {req.upper()}"


def test_takedown_doc_covers_suppression_and_corrections() -> None:
    raw = (GOV_DIR / "takedown-corrections-suppression.md").read_text(encoding="utf-8").lower()
    text = " ".join(raw.split())
    assert "suppression" in text and "deletion" in text
    assert "as_of_belief" in text
    for req in ("sig-gov-005", "sig-gov-007", "sig-gov-008", "sig-gov-011"):
        assert req in text
