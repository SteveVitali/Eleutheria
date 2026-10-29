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


def _overpass_targets(source_id: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = os.environ.get("SIG_OVERPASS_ENDPOINT", "").strip() or DEFAULT_OVERPASS_ENDPOINT
    from .osm import build_overpass_query, tile_discovery_targets

    targets: list[dict[str, Any]] = []
    if spec.get("tile_discovery"):
        # P37.1 / ACQ-17: the declared `out count;` area-census targets precede
        # the seed bbox so the two-pass collection (discovery → per-area fetch
        # via discover_more) runs inside the one live run.
        targets.extend(tile_discovery_targets(endpoint))
    if "overpass_query" in spec:
        query = str(spec["overpass_query"]).strip()
    else:
        # The widened selection is built, never literal — the camera-site
        # selectors ride the versioned vocabulary, not a frozen string.
        bbox_raw = [float(x) for x in spec["bbox"]]
        if len(bbox_raw) != 4:
            raise ValueError(f"{source_id}: live_targets bbox needs 4 numbers (S,W,N,E)")
        query = build_overpass_query(
            bbox=(bbox_raw[0], bbox_raw[1], bbox_raw[2], bbox_raw[3]),
            timeout=int(spec.get("timeout", 180)),
        )
    url = f"{endpoint}?{urlencode({'data': query})}"
    targets.append({"id": f"{source_id}:overpass", "url": url, "kind": "overpass"})
    return targets


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
    if kind == "dot_511_targets":
        # A dot_511_<st> source's live targets ARE the verified registry rows in
        # data/dot_511_targets.toml (P26.7): each expands to the deterministic
        # ArcGIS REST query URL; enumerated non-targets (keyed/refused hosts)
        # never produce a target.
        from .dot_511 import registry_targets

        return registry_targets(source_id)
    if kind == "flock_portal_probe_targets":
        # P36.74 (WV-10/ADR-188): the probe source's live targets ARE the
        # committed aggregator-derived inventory in
        # data/flock_portal_probe_targets.toml — the ~917 portals already
        # known from the Eyes on Flock snapshot, never new discovery. The
        # source row stays ingestion_permitted=false until the operator's
        # P36.12 Wave-B ING-GO-B flip.
        from .flock_portal_probe import probe_targets

        return probe_targets()
    if kind == "axon_connect_targets":
        # P36.76 / R11-ACQ-31: the axon_connect source's live targets ARE the
        # committed I9a-C003 site inventory in data/axon_connect_targets.toml —
        # two bounded rows per site (the public registration page + the :8443
        # faststream screen), never new discovery. The source row stays
        # ingestion_permitted=false; leg B is the operator's act (OP-26).
        from .axon_connect import connect_targets

        return connect_targets()
    if kind == "documentcloud_targets":
        # P36.77 / R11-ACQ-32: the documentcloud + muckrock_public sources'
        # live targets ARE the committed released-materials seed inventory in
        # data/documentcloud_targets.toml — bounded rows per public
        # unauthenticated page/API record, never new discovery. Both source
        # rows stay ingestion_permitted=false; leg B is the operator's act
        # (OP-26).
        from .documentcloud import documentcloud_targets

        return documentcloud_targets(source_id=source_id)
    if kind == "cooperative_targets":
        # P36.78 / R11-ACQ-33: the sourcewell + omnia_partners sources' live
        # targets ARE the committed cooperative contract-page seed inventory
        # in data/cooperative_targets.toml — bounded rows per public
        # unauthenticated contract/supplier/terms page, never new discovery.
        # Both source rows stay ingestion_permitted=false; leg B is the
        # operator's act (OP-26).
        from .cooperative import cooperative_targets

        return cooperative_targets(source_id=source_id)
    if kind == "procurement_portal_tenants":
        # A procurement-portal source's live targets ARE its tenant rows in
        # data/procurement_portal_tenants.toml (P26.10): each expands to the
        # tenant's bounded index surfaces (BidNet storefront solicitation
        # indexes, a Socrata dataset's SoQL slice, a gated portal's own URL —
        # the refusal/challenge is the recorded outcome). platform_census rows
        # never produce targets.
        from .procurement import portal_targets

        return portal_targets(source_id=source_id)
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
