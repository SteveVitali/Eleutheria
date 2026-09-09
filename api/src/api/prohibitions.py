# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The prohibited-endpoint bar (§37.4, SIG-API-012) — a Part VIII enforcement point.

The API MUST NOT expose: any real-time device-liveness signal; any endpoint
enabling per-person lookup; any endpoint returning ``sealed`` capture bytes; or
coordinates finer than an asset's sensitivity tier permits (§19.4). Three of
those are enforced elsewhere (sealed bytes by :func:`evidence.tiers.public_representation`;
per-tier coordinates by :func:`policy.sensitivity.apply_tier`); this module is the
**structural** guard: it asserts, at app construction and in a contract test, that
no *route path* matching a prohibited surface exists at all. A prohibited endpoint
that is never mounted cannot be reached by any bug downstream — the safest state.
"""

from __future__ import annotations

import re

from starlette.routing import Route

#: Path-segment patterns a public route MUST NOT expose (SIG-API-012). Each maps
#: to the prohibition it guards, so a violation reports *why* it is forbidden.
PROHIBITED_PATH_PATTERNS: dict[str, str] = {
    r"live|liveness|online|realtime|real-time|heartbeat|presence|ping": (
        "real-time device-liveness signal (SIG-API-012)"
    ),
    r"person|people|individual|citizen|human|resident|face|plate|license-plate|"
    r"licence-plate|whereabouts|track|trip": (
        "per-person lookup / tracking surface (SIG-API-012, Part VIII)"
    ),
    r"sealed|raw-bytes|rawbytes|capture-bytes|bytes/raw": ("sealed capture bytes (SIG-API-012)"),
    r"precise|exact-coord|exact-location|rooftop|full-precision": (
        "coordinates finer than the sensitivity tier permits (SIG-API-012, §19.4)"
    ),
}

#: Entity types the generic ``/entity/{type}/{id}`` route MUST refuse, so it can
#: never become a per-person lookup even if such a record reached the store
#: (SIG-API-012, Part VIII — defence in depth behind the structural path guard).
PROHIBITED_ENTITY_TYPES: frozenset[str] = frozenset(
    {"person", "people", "individual", "citizen", "human", "resident", "face"}
)

_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), reason) for pat, reason in PROHIBITED_PATH_PATTERNS.items()
]


class ProhibitedEndpointError(RuntimeError):
    """Raised when a mounted route matches a SIG-API-012 prohibited surface."""


def check_path(path: str) -> str | None:
    """Return the prohibition reason if ``path`` is forbidden, else ``None``."""
    lowered = path.lower()
    for pattern, reason in _COMPILED:
        if pattern.search(lowered):
            return reason
    return None


def assert_no_prohibited_routes(paths: list[str]) -> None:
    """Fail if any path is a SIG-API-012 prohibited surface (fail-closed at boot)."""
    violations = [(p, reason) for p in paths if (reason := check_path(p)) is not None]
    if violations:
        lines = "; ".join(f"{p!r} → {reason}" for p, reason in violations)
        raise ProhibitedEndpointError(f"prohibited endpoint(s) mounted (SIG-API-012): {lines}")


def assert_entity_type_allowed(entity_type: str) -> None:
    """Refuse a per-person entity type on the generic entity route (SIG-API-012)."""
    if entity_type.strip().lower() in PROHIBITED_ENTITY_TYPES:
        raise ProhibitedEndpointError(
            f"entity type {entity_type!r} is a per-person lookup and is refused "
            "by the public API (SIG-API-012, Part VIII)"
        )


def route_paths(routes: list[Route]) -> list[str]:
    """Extract the path strings from an app's route table."""
    return [r.path for r in routes if isinstance(r, Route)]
