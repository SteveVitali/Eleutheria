# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ADR-083 API-vs-crawl carve-out allow-list (data-driven).

`robots.txt` governs **crawling**; a host on the allow-list is accessed in **API
mode** — documented, rate-limited access to a named endpoint prefix under that
API's ToS, which the crawler convention does not govern. This is the single reader
`PoliteFetcher` consults; a host that is not listed (or a path outside its endpoint
prefix) stays CRAWL mode and robots binds. There is no wildcard and no blanket
bypass (SIG-INGEST-037 / ADR-083); rate-limiting and no-circumvention still apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from ._data import load_table


@dataclass(frozen=True)
class ApiAllowEntry:
    host: str
    endpoint_prefix: str
    tos_basis: str
    counsel_reviewed: bool
    #: The reviewed per-minute request budget the API publishes/permits
    #: (e.g. OpenStates' declared 5/min — P26.11), or ``None`` when the row
    #: declares no explicit budget.
    rate_limit_per_min: int | None = None


def _entries() -> list[ApiAllowEntry]:
    table = load_table("api_allowlist")
    out: list[ApiAllowEntry] = []
    for row in table.get("api_host", []):
        rpm = row.get("rate_limit_per_min")
        out.append(
            ApiAllowEntry(
                host=str(row["host"]).lower(),
                endpoint_prefix=str(row.get("endpoint_prefix", "/")),
                tos_basis=str(row.get("tos_basis", "")),
                counsel_reviewed=bool(row.get("counsel_reviewed", False)),
                rate_limit_per_min=int(rpm) if rpm is not None else None,
            )
        )
    return out


def api_allow_entry(url: str) -> ApiAllowEntry | None:
    """The allow-list entry governing ``url``, or ``None`` (P26.11).

    A match requires an exact host match AND the path to start with the entry's
    ``endpoint_prefix`` — so an allow-list entry for one API endpoint never blesses
    the rest of the host's pages (which stay CRAWL/robots-governed).
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    for e in _entries():
        if host == e.host and path.startswith(e.endpoint_prefix):
            return e
    return None


def api_allow_reason(url: str) -> str | None:
    """Return the ToS basis if ``url`` is API-mode allowed, else ``None``."""
    entry = api_allow_entry(url)
    return entry.tos_basis if entry is not None else None


__all__ = ["ApiAllowEntry", "api_allow_entry", "api_allow_reason"]
