# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.50 — doc test for the OP-09 DNS cut-over runbook + zone inventory.

The runbook `docs/build/reports/DNS_CUTOVER_RUNBOOK.md` is what the operator's
highest-blast-radius action (FEA-08) runs from; these tests pin its required
sections — TTL step-down, DNSSEC/DS handling, the grey-cloud (DNS-only) rule
for the load-balancer hostnames, rollback, mail, certificate renewal — and the
rule that every checklist step carries a verification command. The dated zone
inventory under `docs/build/reports/dns/` is a frozen artifact: the tests
assert its structure (every record type, an exact query and a `date -u` stamp
per answer) and never pin the record values, which are living DNS state
(BM-TEST-01).
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / "docs" / "build" / "reports" / "DNS_CUTOVER_RUNBOOK.md"
DNS_DIR = REPO_ROOT / "docs" / "build" / "reports" / "dns"

# The contract's required runbook sections (each a heading the doc carries).
REQUIRED_SECTIONS = [
    "TTL",
    "DNSSEC",
    "grey cloud",
    "Rollback",
    "Mail",
    "Certificate renewal",
]

# Every record type the dated inventory must list (contract deliverable 1).
REQUIRED_RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "CAA", "DS", "NS", "SOA"]


def _runbook_text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _inventory_files() -> list[pathlib.Path]:
    return sorted(DNS_DIR.glob("zone_inventory_*.md"))


def test_runbook_exists() -> None:
    assert RUNBOOK.is_file(), "DNS_CUTOVER_RUNBOOK.md is missing"


def test_runbook_has_every_required_section() -> None:
    text = _runbook_text()
    headings = {
        m.group(1).strip().lower().replace("-", " ")
        for m in re.finditer(r"^#{2,3}\s+(.+)$", text, re.M)
    }
    for needle in REQUIRED_SECTIONS:
        n = needle.lower().replace("-", " ")
        assert any(n in h for h in headings), (
            f"runbook has no section covering {needle!r}; headings: {sorted(headings)}"
        )


def test_runbook_every_checklist_row_has_a_verification_command() -> None:
    """Every numbered checklist step carries a `verify` cell with a command."""
    text = _runbook_text()
    rows = [ln for ln in text.splitlines() if re.match(r"^\|\s*(?:\d+|R\d)\s*\|", ln)]
    assert rows, "the runbook has no numbered checklist rows at all"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) >= 3, f"checklist row is not step|verify shaped: {row}"
        verify = cells[-1]
        assert verify and "`" in verify, f"checklist row has no verify command: {row}"


def test_runbook_grey_cloud_rule_is_stated_for_both_lb_names() -> None:
    """The cert-protecting rule names the apex and www as DNS-only records."""
    text = _runbook_text()
    assert re.search(r"grey[- ]cloud", text, re.I)
    assert re.search(r"DNS[- ]only", text, re.I)
    for name in ("136.81.80.102", "sig-web-cert"):
        assert name in text, f"runbook lost the {name} anchor"


def test_runbook_rollback_is_a_nameserver_revert() -> None:
    text = _runbook_text().lower()
    assert "revert" in text and "nameserver" in text
    assert "squarespacedns" in text, "rollback must name the original NS set"


def test_runbook_hands_off_to_p35_67_op10_and_the_spend_ledger() -> None:
    text = _runbook_text()
    for needle in ("P35.67", "OP-10", "spend"):
        assert needle in text, f"runbook lost its hand-off to {needle}"


def test_zone_inventory_exists_and_is_dated() -> None:
    files = _inventory_files()
    assert files, "no zone_inventory_<date>.md under docs/build/reports/dns/"
    for f in files:
        assert re.search(r"zone_inventory_\d{4}-\d{2}-\d{2}\.md$", f.name)


def test_inventory_lists_every_record_type_with_query_and_date() -> None:
    for f in _inventory_files():
        text = f.read_text(encoding="utf-8")
        for rtype in REQUIRED_RECORD_TYPES:
            # the type appears as a query (`dig … <type>`) or a headed section
            assert re.search(rf"\b{rtype}\b", text), f"{f.name}: record type {rtype} is not listed"
        assert "dig " in text, f"{f.name}: no recorded queries"
        assert "date -u" in text, f"{f.name}: queries carry no `date -u` stamp"


def test_inventory_covers_apex_and_www_and_the_cert_read() -> None:
    for f in _inventory_files():
        text = f.read_text(encoding="utf-8")
        for needle in (
            "surveillancegraph.org",
            "www.surveillancegraph.org",
            "openssl s_client",
            "136.81.80.102",
        ):
            assert needle in text, f"{f.name}: missing {needle}"


def test_runbook_references_the_inventory() -> None:
    text = _runbook_text()
    assert "zone_inventory_" in text, "runbook no longer cites the dated inventory"
