# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-source LIVE fetch targets (P24.1 live deploy / DEPLOY.1, ADR-082).

The eight-stage framework's ``discover()`` reads its targets from
``ctx.parameters["targets"]`` (identifiers, not content — SIG-INGEST-045i). The
committed fixtures encode connector *responses*, not the *request targets*, so the
live runner had no real targets to fetch (P21.3 deliverable-4 gap: it shipped with
a placeholder). This module is the single reader that turns the declarative
``data/live_targets.toml`` rows into the target list the live runner passes in.

No secret ever lives in the table (HG-09): a keyed endpoint is named as an env var
and resolved here at call time. A source with no row has no live targets and the
live runner refuses rather than inventing one.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from ._data import load_table

#: The Overpass instance used when $SIG_OVERPASS_ENDPOINT is unset. The lz4 mirror
#: is the default because the main overpass-api.de host returns HTTP 406 to
#: programmatic requests (a WAF quirk, 2026-09-15); both are on the ADR-083
#: allow-list. The UA must not contain "crawler" or the WAF 406s (see net.py).
DEFAULT_OVERPASS_ENDPOINT = "https://lz4.overpass-api.de/api/interpreter"


def _overpass_targets(source_id: str, spec: dict[str, Any]) -> list[dict[str, str]]:
    endpoint = os.environ.get("SIG_OVERPASS_ENDPOINT", "").strip() or DEFAULT_OVERPASS_ENDPOINT
    query = str(spec["overpass_query"]).strip()
    url = f"{endpoint}?{urlencode({'data': query})}"
    return [{"id": f"{source_id}:overpass", "url": url, "kind": "overpass"}]


def live_targets(source_id: str) -> list[dict[str, str]]:
    """Return the live fetch targets for ``source_id`` (empty if none configured).

    Each target is ``{"id", "url", "kind"}`` — exactly the shape a connector's
    ``discover()`` expects in ``ctx.parameters["targets"]``.
    """
    table = load_table("live_targets")
    spec = table.get(source_id)
    if not spec:
        return []
    kind = str(spec.get("kind", "")).strip()
    if kind == "overpass":
        return _overpass_targets(source_id, spec)
    if kind == "agenda_tenants":
        # An agenda-platform source's live targets ARE the published tenant
        # registry rows (§22.3, P26.2): the connector reads its tenants from
        # data/agenda_tenants.toml — the target list is never duplicated here.
        from .procurement import tenant_targets

        return tenant_targets(platform=source_id)
    # Generic document/http targets: an explicit list of {id, url[, kind]} rows.
    # Extra keys (e.g. a POST body's `post_body`, USAspending's `subaward` flag)
    # pass through untouched — they are reviewed data the connector consumes.
    targets = spec.get("targets", [])
    return [
        {
            "id": str(t["id"]),
            "url": str(t["url"]),
            "kind": str(t.get("kind", kind or "http")),
            **{k: v for k, v in t.items() if k not in {"id", "url", "kind"}},
        }
        for t in targets
    ]


class NoLiveTargets(RuntimeError):
    """A green source was run live but has no ``data/live_targets.toml`` row."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(
            f"source {source_id!r} passed the live gate but has no live targets — "
            f"add a row to connectors/src/connectors/data/live_targets.toml "
            f"(the live runner never fetches a placeholder URL)."
        )


__all__ = ["DEFAULT_OVERPASS_ENDPOINT", "NoLiveTargets", "live_targets"]
