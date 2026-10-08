# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The release-serving boundary (P32.13 / ADR-132 — SIG-FIND-001/002).

The ONE withdrawal rule lives in ``exports.release`` (pure, reusing the P32.5
``policy.eligibility`` selector); this module is the runtime seam that applies
it at the serving boundary:

* ``apply`` — re-apply the CURRENT withdrawal registry to a staged public
  tree: denied routes become content-free tombstones, denied artifact bytes
  are removed whole, and ``conf/withdrawn_routes.conf`` is regenerated so
  nginx evaluates the denies BEFORE any origin file or CDN access.
* ``check`` — the pure per-route access decision a serving layer consults
  (the same check P32.14's search/API surfaces must call).

Offline staging only: this module never pushes to a bucket/CDN and never
touches the live site — public exposure stays with GATE-G3.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def apply(registry: str | Path, staged: str | Path) -> dict[str, Any]:
    """Re-apply the current withdrawal registry to ``staged`` — deterministic:
    same registry + same tree ⇒ same tombstones + same deny map. The
    ``/entity/<t>/<id>/`` convenience stubs follow the registry's latest
    pointer (P34.41: a stub denies when the record it would point at is
    denied under the active release)."""
    from exports.release import ReleaseRegistry, apply_withdrawals

    reg = ReleaseRegistry(Path(registry))
    latest = reg.latest() or {}
    out = apply_withdrawals(
        Path(staged), reg.withdrawals(), active_pub=latest.get("publication_id")
    )
    # the internal route→disposition stub map is CLI-serialised as its
    # sorted route list (dispositions are not JSON values)
    stubs = out.get("entity_stubs") or {}
    out["entity_stubs"] = sorted(stubs)
    return out


def check(registry: str | Path, route: str) -> dict[str, Any]:
    """The barrier check for ONE route — the current-disposition decision +
    tombstone payload (public-safe fields only)."""
    from exports.release import route_access

    return route_access(registry, route)


def main_check(registry: str | Path, route: str) -> int:
    out = check(registry, route)
    print(json.dumps(out, indent=2))
    return 0 if out.get("permitted") else 4


def main_apply(registry: str | Path, staged: str | Path) -> int:
    out = apply(registry, staged)
    print(json.dumps(out, indent=2))
    return 0
