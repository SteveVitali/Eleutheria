# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Crawler Conduct Policy rules (§26, SIG-INGEST-036/037)."""

from __future__ import annotations

import pytest

from policy import crawler


def test_eight_operative_rules_present_and_ordered() -> None:
    rules = crawler.conduct_rules()
    assert [r.n for r in rules] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(r.title and r.text for r in rules)


def test_robots_unretrievable_is_not_a_grant() -> None:
    # Where robots.txt is unretrievable, permission is NOT granted (SIG-INGEST-012).
    assert crawler.robots_permits(None) is False
    assert crawler.robots_permits(True) is True
    assert crawler.robots_permits(False) is False


@pytest.mark.parametrize(
    "retrieved,status,expected",
    [
        (True, 200, True),  # a policy body was retrieved — its verdict governs
        (True, None, True),  # legacy transport: text present, status unknown
        (False, 404, True),  # RFC 9309 §2.3.1.4: a 4xx means no policy exists
        (False, 410, True),
        (False, 403, True),  # still a client error — no policy, not "unavailable"
        (False, 429, False),  # rate limiting is "unavailable", not "no policy"
        (False, 500, False),  # server error = unavailable → complete disallow
        (False, 503, False),
        (False, None, False),  # connection failure/timeout = unavailable
        (False, 301, False),  # redirect-chain exhaustion residue = unavailable
    ],
)
def test_robots_access_permits_4xx_is_no_policy_not_unavailable(
    retrieved: bool, status: int | None, expected: bool
) -> None:
    # ADR-087 (P26.3 amendment to SIG-INGEST-012): the RFC 9309 §2.3.1.4
    # access-result split — a 4xx robots answer (other than 429) means "no
    # policy exists" → unrestricted; connection failures, 5xx and 429 are
    # "unavailable" → still fail-closed.
    assert crawler.robots_access_permits(retrieved=retrieved, status=status) is expected


def test_content_signal_parsing() -> None:
    signal = crawler.parse_content_signal("search=yes, ai-train=no, use=reference")
    assert signal == {"search": "yes", "ai-train": "no", "use": "reference"}


@pytest.mark.parametrize(
    "header,expected",
    [
        ("search=yes, ai-train=no, use=reference", False),
        ("ai-train=yes", True),
        ("search=yes", False),  # absent => not a grant
        (None, False),
    ],
)
def test_content_signal_training_is_affirmative_only(header: str | None, expected: bool) -> None:
    # Access permission and training permission are different grants (SIG-LIC-004b).
    assert crawler.content_signal_permits_training(header) is expected


@pytest.mark.parametrize(
    "technique",
    [
        "authentication_bypass",
        "paywall_evasion",
        "challenge_solving",
        "proxy_rotation",
        "human_mimicking",
    ],
)
def test_circumvention_techniques_are_rejected(technique: str) -> None:
    assert crawler.is_circumvention(technique)
    with pytest.raises(crawler.CircumventionError):
        crawler.assert_no_circumvention(technique)


def test_offered_channel_is_not_circumvention() -> None:
    assert not crawler.is_circumvention("use_offered_api")
    crawler.assert_no_circumvention("use_offered_api")  # does not raise


# --- P36.1a: affirmative rights reservations (SIG-INGEST-046c, §23.7) --------


def test_content_signal_ai_train_no_is_an_affirmative_reservation() -> None:
    # §23.7's own example: ``ai-train=no`` is an affirmative machine-readable
    # rights reservation — honoured as a refusal.
    verdict = crawler.detect_reservation({"Content-Signal": "ai-train=no"})
    assert verdict.refuses
    assert [(s.kind, s.detail) for s in verdict.signals] == [("content_signal", "ai-train=no")]


def test_content_signal_sibling_automated_use_no_is_a_reservation() -> None:
    # The other aipref automated-use keys reserve the sibling uses SIG performs.
    verdict = crawler.detect_reservation({"Content-Signal": "ai-input=no, search=no"})
    assert verdict.refuses
    assert {s.kind for s in verdict.signals} == {"content_signal"}
    assert {s.detail for s in verdict.signals} == {"ai-input=no", "search=no"}


def test_content_signal_yes_and_unknown_keys_are_not_reservations() -> None:
    # Permissive values and unknown directives are simply not refusals — an
    # absent reservation is never invented (and never treated as a grant either).
    assert not crawler.detect_reservation({"Content-Signal": "ai-train=yes"}).refuses
    assert not crawler.detect_reservation({"Content-Signal": "search=yes"}).refuses
    assert not crawler.detect_reservation({"Content-Signal": "use=reference"}).refuses


def test_tdm_reservation_header_is_an_article_4_refusal() -> None:
    # The TDM-Reservation Protocol: ``TDM-Reservation: 1`` is the EU DSM
    # Article 4 machine-readable reservation (SIG-INGEST-046c).
    verdict = crawler.detect_reservation({"TDM-Reservation": "1"})
    assert verdict.refuses
    assert [(s.kind,) for s in verdict.signals] == [("tdm_reservation",)]
    assert "TDM-Reservation" in verdict.signals[0].detail


def test_x_robots_tag_ai_tokens_are_reservations() -> None:
    # The deployed convention: ``X-Robots-Tag: noai`` / ``noimageai`` are
    # affirmative AI reservations; ordinary tokens (noindex, nofollow) are not.
    verdict = crawler.detect_reservation({"X-Robots-Tag": "noindex, noai"})
    assert verdict.refuses
    assert [(s.kind, s.detail) for s in verdict.signals] == [("x_robots_tag", "X-Robots-Tag: noai")]
    assert not crawler.detect_reservation({"X-Robots-Tag": "noindex, nofollow"}).refuses


def test_page_level_meta_reservations_are_detected_on_html() -> None:
    # The TDMRep / robots-meta page-level forms (Article 4): only HTML bodies
    # are scanned, and only the head prefix.
    body = (
        b"<html><head>"
        b'<meta name="robots" content="noai">'
        b'<meta name="tdm-reservation" content="1">'
        b"</head><body>x</body></html>"
    )
    verdict = crawler.detect_reservation({}, body=body, media_type="text/html")
    assert verdict.refuses
    assert {s.kind for s in verdict.signals} == {"x_robots_tag", "tdm_reservation"}


def test_meta_reservations_do_not_apply_to_non_html_bodies() -> None:
    # A JSON payload that merely mentions the tokens is not a reservation.
    body = b'{"note": "<meta name=\\"robots\\" content=\\"noai\\">"}'
    assert not crawler.detect_reservation({}, body=body, media_type="application/json").refuses


def test_reservation_headers_are_case_insensitive() -> None:
    # HTTP header names are case-insensitive; a folded-case response still refuses.
    verdict = crawler.detect_reservation({"content-signal": "ai-train=no"})
    assert verdict.refuses


def test_absent_and_malformed_signals_never_refuse() -> None:
    # Fail-no-refusal on odd input: an empty envelope, a malformed header and a
    # non-truthy TDM value carry no affirmative reservation.
    assert not crawler.detect_reservation({}).refuses
    assert not crawler.detect_reservation({"Content-Signal": ";;;"}).refuses
    assert not crawler.detect_reservation({"TDM-Reservation": "0"}).refuses
    assert not crawler.detect_reservation({"Content-Signal": "ai-train"}).refuses


def test_reservation_signals_keep_the_verbatim_detail() -> None:
    # §3.1: the recorded refusal keeps the machine-readable signal verbatim so
    # the rights record can carry it as evidence.
    verdict = crawler.detect_reservation({"TDM-Reservation": "true"})
    assert verdict.signals[0].detail == "TDM-Reservation: true"


def test_robots_disallow_is_not_a_reservation() -> None:
    # GL-GATE-08 is untouched: a robots Disallow is an *access* verdict
    # (recorded ``robots_disregarded``), never a rights reservation — no header
    # means no refusal.
    assert not crawler.reservation_refuses({})
