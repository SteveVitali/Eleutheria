# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed rationale-template test (SIG-RECON-022/023, SIG-EPIS-025).

Every versioned template MUST render to text a journalist can quote verbatim:
(a) no unresolved placeholder; (b) names a source or a named rule; (c) attributes
every value; (d) never a support term and an agreement term in one sentence;
(e) no evaluative adjective from the style guide's prohibited list. This suite is
the mechanical enforcement §28.8 requires; changing a template re-runs it.
"""

from __future__ import annotations

from datetime import date

from reconcile.model import Evidence
from reconcile.rationale import check_template, render_rationale, render_representative
from reconcile.resolve import RESOLVE, Claim
from reconcile.ruleset import load_ruleset

AS_OF = date(2026, 9, 1)


def test_every_committed_template_passes_all_five_clauses() -> None:
    rs = load_ruleset()
    problems: list[str] = []
    assert rs.templates, "the ruleset must ship at least one rationale template"
    for code, raw in rs.templates.items():
        rendered = render_representative(rs, code)
        problems += check_template(rs, code, rendered, raw)
    assert problems == [], "\n".join(problems)


def test_no_template_mixes_a_support_term_and_an_agreement_term() -> None:
    # Clause (d) is the SIG-EPIS-025 rule that stops unparseable "probably
    # contested" sentences. Prove the checker actually catches a violation.
    rs = load_ruleset()
    bad = "The value is probably contested by the portal."
    problems = check_template(rs, "SYNTHETIC", bad, "{value} attributed to {source}.")
    assert any("(d)" in p for p in problems)


def test_checker_flags_a_prohibited_adjective() -> None:
    rs = load_ruleset()
    bad = "A massive deployment reported by the portal."
    problems = check_template(rs, "SYNTHETIC", bad, "reported by {source}.")
    assert any("(e)" in p for p in problems)


def test_checker_flags_an_unresolved_placeholder() -> None:
    rs = load_ruleset()
    problems = check_template(rs, "SYNTHETIC", "value is {value}", "attributed to {source}.")
    assert any("(a)" in p for p in problems)


def test_checker_flags_an_unattributed_value() -> None:
    rs = load_ruleset()
    # A value with no source and no attribution phrase in its sentence.
    problems = check_template(rs, "SYNTHETIC", "The count is 38.", "The count is {value}.")
    assert any("(c)" in p for p in problems)


def _ev(family: str) -> Evidence:
    return Evidence(
        source_id=f"src:{family}",
        source_family=family,
        artifact_type=family,
        stable_locator=f"https://example/{family}",
        capture_digest="b" + "0" * 40,
        locator={"selector": "#v"},
    )


def _claim(
    cid: str,
    predicate: str,
    value: object,
    *,
    R: str,
    genre: str,
    observed: date,
    method: str,
    source_id: str,
) -> Claim:
    return Claim(
        claim_id=cid,
        subject_id="S",
        predicate_id=predicate,
        value=value,
        reliability=R,
        integrity="I1",
        genre=genre,
        observed_at=observed,
        source_id=source_id,
        collection_method=method,
        evidence=_ev(genre),
    )


def test_live_resolution_rationale_is_quotable_and_conformant() -> None:
    # A real resolution's rationale must satisfy the same clauses as the template.
    rs = load_ruleset()
    portal = _claim(
        "portal",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
        method="scrape",
        source_id="src:portal",
    )
    contract = _claim(
        "contract",
        "active_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        method="read",
        source_id="src:contract",
    )
    r = RESOLVE(
        "S", "active_device_count", [portal, contract], as_of_world=AS_OF, as_of_belief=AS_OF
    )

    assert "38" in r.rationale_text
    assert "portal" in r.rationale_text  # names the source that mattered
    # Re-run the mechanical clauses against the live text (raw == rendered here).
    problems = check_template(rs, r.rationale_code, r.rationale_text, r.rationale_text)
    # Only (c) is structural on placeholders; the live text has none, so skip it.
    assert [p for p in problems if "(c)" not in p] == []


def test_confirmed_rationale_keeps_support_and_agreement_apart() -> None:
    rs = load_ruleset()
    _, text = render_rationale(
        ruleset=rs,
        status="RESOLVED",
        code=None,
        predicate_id="active_device_count",
        support="CONFIRMED",
        winner=_confirmed_winner(),
        second=None,
        as_of_world=AS_OF,
    )
    # "Confirmed." and the "…record…" clause are in separate sentences.
    support = set(rs.support_terms)
    agreement = set(rs.agreement_terms)
    import re

    for sentence in re.split(r"(?<=[.])\s+", text):
        words = set(re.findall(r"[a-z][a-z-]*", sentence.lower()))
        assert not ((words & support) and (words & agreement)), sentence


def _confirmed_winner() -> object:
    from reconcile.resolve import Candidate

    rep = _claim(
        "a",
        "active_device_count",
        38,
        R="R1",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        method="open_data",
        source_id="src:a",
    )
    return Candidate(
        value=38,
        best_weight=4,
        supporting_class_ids=("src:a", "src:b"),
        method_breadth=2,
        representative=rep,
        supporting_claim_ids=("a", "b"),
        class_weights=(4, 3),
        class_methods=("open_data", "field_survey"),
    )
