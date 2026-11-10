# SPDX-License-Identifier: Apache-2.0
"""P37.31 (K7 WX-02 / P07.1) — the deterministic renewal-clause reader.

A captured contract document's renewal clause yields the dated-decision triple
(``auto_renews`` / ``notice_window_days`` / ``renewal_term_months``) verbatim and
byte-located; a document stating no clause emits nothing (§3.1); affirmative and
negative signals both record (the disagreement stays visible, never reconciled);
a year-stated term converts at exactly 12 months while a month-stated notice
window stays unstated (no 30-day guess).
"""

from __future__ import annotations

from parsing.renewals import RENEWAL_CLAUSES_VERSION, extract_renewal_terms

_AUTO = (
    "This Agreement shall automatically renew for successive one-year terms "
    "unless either party provides written notice of non-renewal at least 90 "
    "days prior to the end of the then-current term."
)


def _by_predicate(text: str) -> dict[str, list]:
    out: dict[str, list] = {}
    for term in extract_renewal_terms(text):
        out.setdefault(term.predicate, []).append(term)
    return out


def test_version_is_recorded() -> None:
    assert RENEWAL_CLAUSES_VERSION


def test_affirmative_auto_renewal_reads_true() -> None:
    terms = _by_predicate(_AUTO)
    assert terms["auto_renews"]
    assert all(t.value is True for t in terms["auto_renews"])


def test_notice_window_reads_the_stated_day_count() -> None:
    terms = _by_predicate(_AUTO)
    assert terms["notice_window_days"]
    assert all(t.value == 90 for t in terms["notice_window_days"])
    for t in terms["notice_window_days"]:
        # The raw literal is a verbatim slice at the recorded offsets (P2/SIG-PARSE-003).
        assert _AUTO[t.start : t.end] == t.literal


def test_renewal_term_in_months_reads_directly() -> None:
    terms = _by_predicate("the renewal term of 12 months applies")
    assert [t.value for t in terms["renewal_term_months"]] == [12]


def test_year_stated_term_converts_at_exactly_twelve_months() -> None:
    terms = _by_predicate("the agreement renews for an additional term of 2 years")
    values = [t.value for t in terms.get("renewal_term_months", [])]
    assert values and all(v == 24 for v in values)


def test_number_words_parse() -> None:
    terms = _by_predicate("written notice of non-renewal at least ninety days prior")
    values = [t.value for t in terms.get("notice_window_days", [])]
    assert values and all(v == 90 for v in values)


def test_explicit_negative_renewal_reads_false() -> None:
    terms = _by_predicate("this agreement does not automatically renew")
    assert terms["auto_renews"] and all(t.value is False for t in terms["auto_renews"])


def test_both_signals_record_never_silently_reconciled() -> None:
    text = (
        "Section 4: the maintenance schedule does not automatically renew. "
        "Section 9: this Agreement shall automatically renew unless either "
        "party gives written notice."
    )
    values = {t.value for t in _by_predicate(text)["auto_renews"]}
    assert values == {True, False}


def test_no_clause_is_honest_absence_never_inferred() -> None:
    assert (
        extract_renewal_terms(
            "The vendor shall supply maintenance services during the term. "
            "Payment is due net 30 days of invoice."
        )
        == []
    )


def test_payment_days_are_not_a_notice_window() -> None:
    terms = _by_predicate("payment is due net 30 days of each invoice")
    assert "notice_window_days" not in terms


def test_notice_of_nonrenewal_is_not_a_negative_signal() -> None:
    # "notice of non-renewal" is affirmative auto-renewal phrasing — a bare
    # non-renewal mention never flips the flag false.
    terms = _by_predicate(_AUTO)
    assert all(t.value is True for t in terms["auto_renews"])


def test_deterministic_same_capture_same_terms() -> None:
    a = extract_renewal_terms(_AUTO)
    b = extract_renewal_terms(_AUTO)
    assert a == b


def test_every_term_carries_its_verbatim_locator() -> None:
    for t in extract_renewal_terms(_AUTO):
        assert t.literal and 0 <= t.start < t.end <= len(_AUTO)
        assert _AUTO[t.start : t.end] == t.literal
        assert t.rule_id
