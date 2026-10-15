# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.5 — doc test for the R2 mirror runbook (SIG-TRANSP-019).

`docs/build/reports/R2_MIRROR_RUNBOOK.md` is the leg's operating document:
prerequisites (OP-09 + the OM-20 list + env credentials), the enable leg, the
$50/month egress ceiling with its alert thresholds, and — the contract's named
deliverable — the **kill switch** as a documented operator step, never an
agent action. These tests pin the required sections and the honesty rules
(the runbook never fabricates a measurement or instructs an agent to run the
kill switch), never the living registry state (BM-TEST-01).
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / "docs" / "build" / "reports" / "R2_MIRROR_RUNBOOK.md"

REQUIRED_NEEDLES = [
    "OP-09",  # the nameserver prerequisite
    "non-listable",  # the origin discipline
    "$50",  # the hard monthly ceiling
    "kill switch",  # the documented operator step
    "rollback",  # the leg's restore path
    "content-hash",  # the immutable key scheme
    "origin of record",  # GCS stays authoritative
    "DNS_CUTOVER_RUNBOOK.md",  # the OP-09 runbook this one defers to
]


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_exists() -> None:
    assert RUNBOOK.is_file(), "R2_MIRROR_RUNBOOK.md is missing"


def test_runbook_names_every_contract_element() -> None:
    text = _text().lower()
    for needle in REQUIRED_NEEDLES:
        assert needle.lower() in text, f"runbook lost {needle!r}"


def test_the_kill_switch_is_an_operator_step() -> None:
    """SIG-TRANSP-019: the kill switch disables the CDN route / R2 public
    access — a documented OPERATOR step, never an agent action."""
    text = _text().lower()
    assert re.search(r"kill switch.*operator step", text, re.S)
    assert "never an agent action" in text
    for needle in ("custom domain", "public access", "enabled = false"):
        assert needle in text, f"kill-switch section lost {needle!r}"


def test_the_ceiling_wires_the_alert_path() -> None:
    """The $50 ceiling is not prose — it names the committed config key and
    the recorded-alert seam it fires through."""
    text = _text()
    assert "hard_ceiling_usd" in text
    assert "egress-report --usage-usd" in text
    assert re.search(r"(warn|80%).*alarm|warns? at", text, re.I)


def test_op09_blocks_the_leg() -> None:
    """The runbook's own state check: while the NS answer names the
    Squarespace servers the leg must not run."""
    text = _text().lower()
    assert "dig" in text and "ns" in text
    assert "squarespacedns" in text
    assert "must not" in text


def test_leg_verification_is_evidence_not_prose() -> None:
    """The enable leg ends in observable checks — the GET against the mirror
    endpoint, the immutable cache header, the $0 egress report."""
    text = _text().lower()
    assert "cache-control" in text and "immutable" in text
    assert "egress-report" in text
    assert "list-type=2" in text or "listing" in text


def test_runbook_contains_no_secrets_or_fabricated_figures() -> None:
    """Env-var names are fine; a credential-looking value or a measured spend
    figure is not (HG-09; the ledger stays pending until reported)."""
    text = _text()
    assert not re.search(r"(?i)(secret|key)[_a-z]*\s*=\s*[a-z0-9/+=]{16,}", text)
    assert "$0" in text  # the free-tier expectation, stated not measured
