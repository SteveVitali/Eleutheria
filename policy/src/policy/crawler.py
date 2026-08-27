# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Crawler Conduct Policy as executable rules (§26, SIG-INGEST-036/037).

The eight operative rules bind every connector. Two of them are enforced here
as pure functions the connector layer will call in later phases:

* **Rule 2 — honour robots.txt and content-signal headers.** Where robots.txt is
  unretrievable, permission is *not* granted (SIG-INGEST-012). Access permission
  and AI-training permission are different grants (SIG-LIC-004b): a site may
  ``Allow: /`` for general agents while signalling ``ai-train=no``.
* **Rule 4 — never circumvent access controls.** This is not merely ethical; it
  is a legal posture (SIG-INGEST-037). Deviating from it is an ADR-level
  decision requiring counsel, not an engineering judgment.

Note the boundary against §25: honouring ``ai-train=no`` restricts using content
as model *training* data, not model-*assisted extraction* (inference over a
document), which remains permitted (SIG-LIC-004c).
"""

from __future__ import annotations

from dataclasses import dataclass

from ._data import load_table


@dataclass(frozen=True)
class ConductRule:
    """One operative rule of the Crawler Conduct Policy (§26)."""

    n: int
    title: str
    text: str


def conduct_rules() -> tuple[ConductRule, ...]:
    """Return the eight operative rules, in order (§26, SIG-INGEST-036)."""
    rows = load_table("crawler_conduct")["rules"]
    return tuple(ConductRule(n=r["n"], title=r["title"], text=r["text"]) for r in rows)


# --- Rule 2: robots.txt + content signals -------------------------------------


def robots_permits(fetch_allowed: bool | None) -> bool:
    """Whether a fetch is permitted given the robots.txt determination.

    ``fetch_allowed`` is the parsed robots.txt verdict, or ``None`` when
    robots.txt could not be retrieved. An unretrievable robots.txt is **not**
    an implied grant: permission defaults closed (SIG-INGEST-012).
    """
    if fetch_allowed is None:
        return False
    return fetch_allowed


def parse_content_signal(header: str) -> dict[str, str]:
    """Parse a ``Content-Signal`` header into its directives.

    Example: ``"search=yes, ai-train=no, use=reference"`` →
    ``{"search": "yes", "ai-train": "no", "use": "reference"}``. Unknown or
    malformed segments are ignored rather than raising, so an odd header never
    silently grants a permission it did not express.
    """
    directives: dict[str, str] = {}
    for segment in header.split(","):
        key, sep, value = segment.strip().partition("=")
        if sep and key:
            directives[key.strip().lower()] = value.strip().lower()
    return directives


def content_signal_permits_training(header: str | None) -> bool:
    """Whether a content signal permits using the content as training data.

    Permission is affirmative-only: absent an explicit ``ai-train=yes`` the
    answer is ``False`` (SIG-LIC-004b/004c). ``None`` (no signal) is not a grant.
    """
    if header is None:
        return False
    return parse_content_signal(header).get("ai-train") == "yes"


# --- Rule 4: no circumvention (a legal posture, SIG-INGEST-037) ---------------


class CircumventionError(Exception):
    """Raised when a connector plan includes an access-control circumvention."""


def circumvention_techniques() -> frozenset[str]:
    """The techniques that constitute circumvention under Rule 4 (§26)."""
    return frozenset(load_table("crawler_conduct")["circumvention"]["techniques"])


def is_circumvention(technique: str) -> bool:
    """Whether ``technique`` is a forbidden access-control circumvention."""
    return technique in circumvention_techniques()


def assert_no_circumvention(technique: str) -> None:
    """Raise :class:`CircumventionError` if ``technique`` circumvents access controls.

    Circumvention is an ADR-level deviation requiring counsel (SIG-INGEST-037),
    never a routine engineering choice — hence a hard failure here.
    """
    if is_circumvention(technique):
        raise CircumventionError(
            f"{technique!r} circumvents access controls (Rule 4, §26); deviating "
            "is an ADR-level decision requiring counsel (SIG-INGEST-037)."
        )
