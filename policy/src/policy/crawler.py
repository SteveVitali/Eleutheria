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

import re
from collections.abc import Mapping
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


def robots_access_permits(*, retrieved: bool, status: int | None) -> bool:
    """Whether the robots.txt *retrieval outcome* permits fetching at all.

    This is the access-result split RFC 9309 §2.3.1.4 draws (ADR-087, the
    P26.3 amendment to SIG-INGEST-012):

    * ``retrieved`` (a 2xx policy body was obtained) — a policy exists and its
      parsed verdict governs via :func:`robots_permits` → ``True`` here.
    * ``status`` in the 4xx range **except 429** — the server answered "no
      such policy resource" (404) or an equivalent client error: under the
      RFC, a 4xx means no robots.txt exists, so access is *unrestricted* →
      ``True``.
    * ``status`` ``429`` — rate limiting is not "no policy"; the RFC treats it
      as unavailable → ``False``.
    * ``status`` ``None`` (connection failure, timeout, redirect exhaustion)
      or a 5xx/1xx/3xx residue — the file is genuinely *unavailable*; the RFC
      has the crawler assume complete disallow → ``False``.

    The distinction this guards: "no policy exists" (4xx) is a different
    signal from "the policy could not be retrieved" (429, 5xx, or a
    connection-level failure) — only the latter defaults closed
    (SIG-INGEST-012 as amended by ADR-087).
    """
    if retrieved:
        return True
    if status is None:
        return False
    return 400 <= status < 500 and status != 429


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


# --- Rule 7 + SIG-INGEST-046c: affirmative rights reservations -----------------
#
# An *affirmative machine-readable rights reservation* is honoured as a refusal
# (SIG-INGEST-046c, §23.7 — not waived, not amended under ADR-168/A-5): a
# ``Content-Signal`` directive, a TDM reservation, or an EU DSM Article 4
# reservation. A robots ``Disallow`` verdict is NOT such a reservation — under
# GL-GATE-08 a disallow is recorded ``robots_disregarded`` and the fetch
# proceeds; only the signals below refuse. The detector is a pure function of
# the response envelope: the shared fetch layer calls it on every response and
# the refusal lands on the rights record (recorded, never silent).

#: ``Content-Signal`` directives whose ``no`` value is an affirmative
#: reservation of automated-use rights (the IETF aipref automated-use keys:
#: ``ai-train`` is the §23.7 example; ``ai-input`` and ``search`` reserve the
#: sibling automated uses SIG performs — inference-input and search indexing).
CONTENT_SIGNAL_RESERVATION_KEYS: frozenset[str] = frozenset({"ai-train", "ai-input", "search"})

#: ``X-Robots-Tag`` directive tokens that are affirmative TDM/AI reservations
#: (the deployed convention — e.g. ``X-Robots-Tag: noai`` or ``noimageai``).
X_ROBOTS_TAG_RESERVATION_TOKENS: frozenset[str] = frozenset({"noai", "noimageai"})

#: The TDM-Reservation Protocol's affirmative values (``TDM-Reservation: 1``).
_TDM_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes"})

#: How much of an HTML body the meta-tag detector scans (the <head> prefix).
_META_SCAN_BYTES = 65536


@dataclass(frozen=True)
class ReservationSignal:
    """One affirmative rights-reservation signal observed on a response.

    ``kind`` names the reservation form; ``detail`` carries the
    machine-readable signal as observed (a header line or meta directive), so
    the refusal record keeps the evidence verbatim (§3.1).
    """

    kind: str
    detail: str


@dataclass(frozen=True)
class ReservationVerdict:
    """The outcome of scanning one response for affirmative reservations."""

    signals: tuple[ReservationSignal, ...] = ()

    @property
    def refuses(self) -> bool:
        """Whether any affirmative reservation was observed (SIG-INGEST-046c)."""
        return bool(self.signals)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (HTTP header names are case-insensitive)."""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def content_signal_reservations(header: str | None) -> tuple[ReservationSignal, ...]:
    """The affirmative reservations a ``Content-Signal`` header declares.

    A directive ``<key>=no`` on an automated-use key is an affirmative
    reservation (§23.7's example is ``ai-train=no``); ``yes`` values and
    unknown keys are not reservations.
    """
    if header is None:
        return ()
    out: list[ReservationSignal] = []
    for key, value in parse_content_signal(header).items():
        if key in CONTENT_SIGNAL_RESERVATION_KEYS and value == "no":
            out.append(ReservationSignal("content_signal", f"{key}={value}"))
    return tuple(out)


def _tdm_reservation_signals(header: str | None) -> tuple[ReservationSignal, ...]:
    """The TDM-Reservation Protocol header (EU DSM Article 4 machine-readable)."""
    if header is None:
        return ()
    value = header.strip().lower()
    if value in _TDM_TRUTHY:
        return (ReservationSignal("tdm_reservation", f"TDM-Reservation: {header.strip()}"),)
    return ()


def _x_robots_tag_signals(header: str | None) -> tuple[ReservationSignal, ...]:
    """``X-Robots-Tag`` tokens that are affirmative TDM/AI reservations."""
    if header is None:
        return ()
    out: list[ReservationSignal] = []
    for token in header.split(","):
        token = token.strip().lower()
        if token in X_ROBOTS_TAG_RESERVATION_TOKENS:
            out.append(ReservationSignal("x_robots_tag", f"X-Robots-Tag: {token}"))
    return tuple(out)


_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_META_NAME_RE = re.compile(r"""name\s*=\s*["']?([^"'>\s]+)["']?""", re.IGNORECASE)
_META_CONTENT_RE = re.compile(r"""content\s*=\s*["']([^"']*)["']""", re.IGNORECASE)


def _meta_reservation_signals(body: bytes | None, media_type: str) -> tuple[ReservationSignal, ...]:
    """Page-level reservations: ``<meta name="robots" content="…noai…">`` and
    ``<meta name="tdm-reservation" content="1">`` (the EU DSM Article 4 /
    TDMRep page-level forms). Only an HTML body is scanned, and only its head
    prefix — a bounded, deterministic check, never a content read.
    """
    if body is None or "html" not in media_type.lower():
        return ()
    text = body[:_META_SCAN_BYTES].decode("utf-8", errors="replace")
    out: list[ReservationSignal] = []
    for match in _META_TAG_RE.finditer(text):
        tag = match.group(0)
        name = _META_NAME_RE.search(tag)
        content = _META_CONTENT_RE.search(tag)
        if name is None or content is None:
            continue
        meta_name = name.group(1).strip().lower()
        meta_content = content.group(1).strip().lower()
        if meta_name == "robots":
            for token in meta_content.split(","):
                token = token.strip()
                if token in X_ROBOTS_TAG_RESERVATION_TOKENS:
                    # Same directive family as X-Robots-Tag, page-level form —
                    # the kind stays in the reservation vocabulary so it can
                    # land verbatim on a RightsRecord.
                    out.append(ReservationSignal("x_robots_tag", f'<meta name="robots"> {token}'))
        elif meta_name == "tdm-reservation" and meta_content in _TDM_TRUTHY:
            # The TDMRep page-level form of the same Article 4 reservation.
            out.append(
                ReservationSignal(
                    "tdm_reservation",
                    f'<meta name="tdm-reservation" content="{meta_content}">',
                )
            )
    return tuple(out)


def detect_reservation(
    headers: Mapping[str, str],
    *,
    body: bytes | None = None,
    media_type: str = "",
) -> ReservationVerdict:
    """Scan one response's envelope (and HTML head) for reservations.

    Returns every affirmative signal observed — a ``Content-Signal``
    directive, a ``TDM-Reservation`` header, an ``X-Robots-Tag`` AI
    reservation, or a page-level meta reservation (EU DSM Article 4). An empty
    verdict means no reservation; absent signals are never treated as grants
    of anything — they simply are not refusals.
    """
    signals: list[ReservationSignal] = []
    signals += content_signal_reservations(_header(headers, "Content-Signal"))
    signals += _tdm_reservation_signals(_header(headers, "TDM-Reservation"))
    signals += _x_robots_tag_signals(_header(headers, "X-Robots-Tag"))
    signals += _meta_reservation_signals(body, media_type)
    return ReservationVerdict(tuple(signals))


def reservation_refuses(
    headers: Mapping[str, str],
    *,
    body: bytes | None = None,
    media_type: str = "",
) -> bool:
    """Whether the response carries an affirmative reservation (SIG-INGEST-046c)."""
    return detect_reservation(headers, body=body, media_type=media_type).refuses


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
