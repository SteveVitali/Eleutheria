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
