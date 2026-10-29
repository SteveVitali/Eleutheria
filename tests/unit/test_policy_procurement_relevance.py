# SPDX-License-Identifier: Apache-2.0
"""P36.30 — the procurement relevance rule (K2 GX-04 / H-13, R11-K13-GX-04).

Fixture-level, never living records: the vocabulary is built from
fabricated TOML-shaped tables; every verdict is a pure function of the
inputs.
"""

from __future__ import annotations

from policy.procurement_relevance import (
    BASIS_VALUES,
    INPUT_PREDICATES,
    RELEVANCE_VALUES,
    SCHEMA,
    UNCLASSIFIED_LABEL,
    classify_notice,
    is_notice_subject,
    load_reviewed_vocabulary,
    relevance_doc,
    vocabulary_from_tables,
)


def _vocab():
    """A fabricated reviewed vocabulary — one term, one CPV code."""
    return vocabulary_from_tables(
        {
            "vocab_version": "test-agenda/1",
            "terms": [
                {
                    "id": "alpr",
                    "kind": "technology",
                    "label": "automated license plate reader",
                    "patterns": ["\\balprs?\\b", "license plate reader"],
                },
                {
                    "id": "cctv",
                    "kind": "technology",
                    "label": "closed-circuit television",
                    "patterns": ["\\bcctv\\b"],
                },
            ],
        },
        {
            "vocab_version": "test-proc/1",
            "ted_eu_sweep": {
                "cpv_codes": [{"code": "35120000", "label": "Surveillance systems"}],
                "keywords": [
                    {
                        "id": "drone",
                        "kind": "technology",
                        "query": "drone",
                        "patterns": ["\\bdrones?\\b", "unmanned aerial"],
                    }
                ],
            },
            "terms": {
                "ate_keywords": {
                    "kind": "technology",
                    "label": "automated traffic enforcement",
                    "terms": ["speed camera", "red light camera"],
                },
            },
        },
        digest="0" * 64,
    )


# ---------------------------------------------------------------------------
# Subject family + constants
# ---------------------------------------------------------------------------


def test_notice_subject_prefixes():
    assert is_notice_subject("procurement_notice:ted_eu:2026-1")
    assert is_notice_subject("notice:portal:x")
    assert not is_notice_subject("contract:c-1")
    assert is_notice_subject("procurement_notice_extra:x") is False
    assert not is_notice_subject(None)
    assert not is_notice_subject("")


def test_vocabulary_is_closed():
    assert set(RELEVANCE_VALUES) == {"surveillance_related", "not_classified"}
    assert "none" in BASIS_VALUES
    assert "matched_keyword" in INPUT_PREDICATES
    assert "products" in INPUT_PREDICATES
    assert UNCLASSIFIED_LABEL == "not classified as surveillance-related"
    assert SCHEMA == "sig.procurement-relevance/1"


# ---------------------------------------------------------------------------
# Classification — both ways (the ticket's AC)
# ---------------------------------------------------------------------------


def test_keyword_hit_is_relevant():
    r = classify_notice(
        "procurement_notice:ted_eu:1",
        {"matched_keyword": ["alpr"]},
        vocab=_vocab(),
    )
    assert r.relevance == "surveillance_related"
    assert r.bases == ("matched_keyword",)
    assert r.matched == ("alpr",)
    assert r.buyer_label is None


def test_cpv_code_hit_is_relevant():
    r = classify_notice(
        "procurement_notice:ted_eu:2",
        {"products": ["35120000"]},
        vocab=_vocab(),
    )
    assert r.relevance == "surveillance_related"
    assert r.bases == ("product_code",)
    assert r.matched == ("cpv:35120000",)


def test_cpv_code_with_check_digit_normalises():
    r = classify_notice(
        "procurement_notice:ted_eu:2b",
        {"products": ["35120000-3"]},
        vocab=_vocab(),
    )
    assert r.relevance == "surveillance_related"
    assert "cpv:35120000" in r.matched


def test_product_literal_matching_a_reviewed_term_is_relevant():
    r = classify_notice(
        "procurement_notice:portal:9",
        {"products": ["Speed camera maintenance"]},
        vocab=_vocab(),
    )
    assert r.relevance == "surveillance_related"
    assert r.bases == ("product_text",)
    assert r.matched == ("ate_keywords",)


def test_product_literal_word_boundary_guard():
    # 'drones' inside a longer word never classifies on a bare substring:
    # "droneszz" has no word boundary after `drones` → not classified.
    r = classify_notice(
        "procurement_notice:portal:9b",
        {"products": ["supply of droneszz parts"]},
        vocab=_vocab(),
    )
    assert r.relevance == "not_classified"


def test_unclassified_notice_carries_the_h13_label():
    r = classify_notice(
        "procurement_notice:okc_portal:4471",
        {"title": "Playground resurfacing", "products": ["93500000"]},
        vocab=_vocab(),
    )
    assert r.relevance == "not_classified"
    assert r.bases == ("none",)
    assert r.matched == ()
    assert r.buyer_label == "not classified as surveillance-related"


def test_no_claims_at_all_is_not_classified():
    r = classify_notice("procurement_notice:portal:0", {}, vocab=_vocab())
    assert r.relevance == "not_classified"
    assert r.buyer_label == UNCLASSIFIED_LABEL


def test_unreviewed_code_is_never_classified_on_a_guess():
    # A CPV code the reviewed set does not name — fail closed.
    r = classify_notice(
        "procurement_notice:ted_eu:9",
        {"products": ["99999999"]},
        vocab=_vocab(),
    )
    assert r.relevance == "not_classified"


def test_naics_slot_is_declared_and_empty():
    # A NAICS literal never classifies — no reviewed NAICS set exists.
    r = classify_notice(
        "procurement_notice:sam:1",
        {"naics": ["541690"]},
        vocab=_vocab(),
    )
    assert r.relevance == "not_classified"


def test_multiple_bases_record_in_order():
    r = classify_notice(
        "procurement_notice:ted_eu:3",
        {
            "matched_keyword": ["cctv"],
            "products": ["35120000", "surveillance camera maintenance"],
        },
        vocab=_vocab(),
    )
    assert r.relevance == "surveillance_related"
    assert set(r.bases) == {"matched_keyword", "product_code"}
    assert "cctv" in r.matched
    assert "cpv:35120000" in r.matched


def test_fields_accept_scalar_or_list():
    a = classify_notice("procurement_notice:x:1", {"matched_keyword": "alpr"}, vocab=_vocab())
    b = classify_notice("procurement_notice:x:1", {"matched_keyword": ["alpr"]}, vocab=_vocab())
    assert a.relevance == b.relevance == "surveillance_related"


# ---------------------------------------------------------------------------
# The emitted document
# ---------------------------------------------------------------------------


def test_relevance_doc_shape_and_counts():
    vocab = _vocab()
    rows = [
        classify_notice("procurement_notice:a:1", {"matched_keyword": ["alpr"]}, vocab=vocab),
        classify_notice("procurement_notice:a:2", {}, vocab=vocab),
    ]
    doc = relevance_doc(rows, generated_at="2026-09-01T00:00:00Z", publication="pub-1", vocab=vocab)
    assert doc["schema"] == "sig.procurement-relevance/1"
    assert doc["publication"] == "pub-1"
    assert doc["rule"]["decision"].startswith("D-K2-5")
    assert doc["counts"] == {
        "notices": 2,
        "surveillance_related": 1,
        "not_classified": 1,
    }
    assert doc["vocabulary"]["cpv_codes"] == 1
    assert doc["vocabulary"]["naics_codes"] == 0
    by_skey = {r["subject_key"]: r for r in doc["rows"]}
    assert by_skey["procurement_notice:a:1"]["relevance"] == "surveillance_related"
    assert (
        by_skey["procurement_notice:a:2"]["buyer_label"] == "not classified as surveillance-related"
    )


def test_committed_vocabulary_loads():
    """The committed connector vocab tables load — reviewed, never fabricated."""
    vocab = load_reviewed_vocabulary()
    assert vocab.cpv_codes  # the verified TED CPV set is non-empty
    assert vocab.terms  # the reviewed keyword set is non-empty
    assert vocab.digest and len(vocab.digest) == 64
    assert vocab.naics_codes == {}  # recorded absent — I8 owns new sources
    # A verbatim CPV literal classifies; a product name scans the patterns.
    r = classify_notice(
        "procurement_notice:ted_eu:live",
        {"products": ["35120000"]},
        vocab=vocab,
    )
    assert r.relevance == "surveillance_related"
