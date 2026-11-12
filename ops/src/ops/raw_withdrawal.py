# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The raw-archive withdrawal rehearsal (P37.36 / TX-12, SIG-TRANSP-020, J3
§9.2 — "object deleted from mirror + origin, CDN purge, tombstone").

D-J3-1 [B-19] = yes decides the lane's withdrawal shape verbatim: a raw
object withdrawal MUST **delete** the object from the mirror and the origin,
**purge** the CDN cache by URL, and **tombstone** — a ``withdrawals.json``
disposition whose access-time barrier answers ``410`` with the
``sig.tombstone/1`` body at the web-origin path (the same ADR-132/ADR-124
barrier every other surface reuses — P35.55's ``record_withdrawal`` +
``apply_withdrawals``).

This module is the **rehearsal**: it runs over a staging mirror/origin pair
and a staged web tree (fixture roots, never the live services), in order:

1. the object at ``raw/<multihash>`` is deleted from the mirror root AND the
   origin root — both removals are reported; a delete on an absent object is
   a recorded ``absent`` leg, never a fabricated deletion;
2. the CDN purge hook is invoked with the object's URLs (an injected
   callable — the live leg binds the Cloudflare purge API; a rehearsal binds
   a recorder);
3. a ``release_artifact`` disposition naming ``raw/<multihash>`` lands in the
   withdrawal registry and ``apply_withdrawals`` re-derives the staged
   barrier — the route answers ``410`` + tombstone at the web origin;
4. the verify probes answer ``410`` at the web path and ``404`` at the
   mirror — the D20 acceptance verbatim.

Every leg lands in a ``sig.raw-withdrawal-rehearsal/1`` record — the honest
rehearsal receipt (SIG-ENG-042: a leg that did not run is ``not_run``,
never claimed).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from exports.release import apply_withdrawals
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

#: The rehearsal receipt schema.
REHEARSAL_SCHEMA = "sig.raw-withdrawal-rehearsal/1"


class RehearsalError(RuntimeError):
    """A withdrawal-rehearsal contract violation — always loud."""


def _delete_object(root: Path, rel: str) -> str:
    """Delete ``root/rel`` — returns ``deleted`` or ``absent`` (never lies)."""
    target = root / rel
    if not target.is_file():
        return "absent"
    target.unlink()
    return "deleted"


def _disposition_for(
    object_rel: str,
    *,
    authority: str,
    reason_category: ReasonCategory,
    decided_at: datetime | None = None,
    rationale: str | None = None,
    seq: int = 0,
) -> Any:
    """The append-only withdrawal order for one raw object."""
    return new_disposition(
        target_kind=TargetKind.RELEASE_ARTIFACT,
        target_id=object_rel,
        disposition=Disposition.WITHDRAW,
        reason_category=reason_category,
        authority=authority,
        decided_at=decided_at,
        rationale=rationale,
        seq=seq,
    )


def _write_disposition(registry_dir: Path, record: Any) -> Path:
    """Land the disposition in ``registry_dir/withdrawals.json`` (append-only:
    the file gains an entry, never rewrites or drops one)."""
    path = registry_dir / "withdrawals.json"
    doc: dict[str, Any] = {"schema": "sig.withdrawal-registry/1", "entries": []}
    if path.is_file():
        doc = json.loads(path.read_bytes())
        if not isinstance(doc.get("entries"), list):
            raise RehearsalError(f"{path}: entries is not a list")
    entry = {
        "target_kind": record.target_kind.value,
        "target_id": record.target_id,
        "disposition": record.disposition.value,
        "reason_category": record.reason_category.value,
        "authority": record.authority,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "policy_version": record.policy_version,
    }
    if record.rationale is not None:
        entry["rationale"] = record.rationale
    doc["entries"].append(entry)
    path.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _records_from_registry(registry_dir: Path) -> list[Any]:
    """Re-read every registry disposition as DispositionRecords — the barrier
    applies the CURRENT registry, so the re-derived deny set is the whole
    recorded set, not just the appended row."""
    from policy.eligibility import Disposition as _D
    from policy.eligibility import DispositionRecord
    from policy.eligibility import ReasonCategory as _R

    raw = registry_dir / "withdrawals.json"
    if not raw.is_file():
        return []
    doc = json.loads(raw.read_bytes())
    out: list[DispositionRecord] = []
    for i, e in enumerate(doc.get("entries") or []):
        decided = e.get("decided_at")
        out.append(
            DispositionRecord(
                target_kind=TargetKind(str(e.get("target_kind") or "artifact")),
                target_id=str(e.get("target_id") or ""),
                disposition=_D(str(e.get("disposition") or "withdraw")),
                reason_category=_R(str(e.get("reason_category") or "rights_withdrawal")),
                authority=str(e.get("authority") or "unrecorded"),
                decided_at=(datetime.fromisoformat(str(decided)) if decided else None),
                seq=int(e.get("seq") or i),
            )
        )
    return out


@dataclass
class RehearsalResult:
    """The ``sig.raw-withdrawal-rehearsal/1`` outcome."""

    object_rel: str
    legs: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": REHEARSAL_SCHEMA,
            "object": self.object_rel,
            "legs": self.legs,
            "ok": all(v.get("ok") for v in self.legs.values() if isinstance(v, Mapping)),
        }


def rehearse_withdrawal(
    *,
    object_rel: str,
    mirror_root: Path | str,
    origin_root: Path | str,
    staged_root: Path | str,
    registry_dir: Path | str,
    cdn_purge: Callable[[list[str]], list[str]],
    web_probe: Callable[[str], tuple[int, bytes]],
    mirror_probe: Callable[[str], tuple[int, bytes]],
    authority: str,
    reason_category: ReasonCategory = ReasonCategory.RIGHTS_WITHDRAWAL,
    decided_at: datetime | None = None,
    rationale: str | None = None,
) -> RehearsalResult:
    """Run the delete/purge/tombstone rehearsal for ``raw/<multihash>``.

    Parameters are injected roots + callables — the rehearsal is provable
    over a fixture tree with no live service. ``object_rel`` must name a
    ``raw/`` object (fail closed: the rehearsal never touches a non-raw
    path). ``authority`` is the withdrawal order's authority string (the
    operator's in a live leg; a fixture value in the rehearsal).
    """
    object_rel = object_rel.lstrip("/")
    if not object_rel.startswith("raw/") or "/" in object_rel[4:]:
        raise RehearsalError(
            f"raw-withdrawal targets are `raw/<multihash>` objects, not {object_rel!r}"
        )
    if not authority:
        raise RehearsalError("a withdrawal order names its authority")
    mirror_root = Path(mirror_root)
    origin_root = Path(origin_root)
    staged_root = Path(staged_root)
    registry_dir = Path(registry_dir)

    result = RehearsalResult(object_rel=object_rel)

    # 1. delete from mirror + origin (the object's two distribution homes).
    m = _delete_object(mirror_root, object_rel)
    o = _delete_object(origin_root, object_rel)
    result.legs["delete"] = {
        "mirror": m,
        "origin": o,
        "ok": m in {"deleted", "absent"} and o in {"deleted", "absent"},
    }

    # 2. CDN purge by URL — the injected callable's recorded answer.
    purged = list(cdn_purge([f"/{object_rel}"]))
    result.legs["purge"] = {"urls": purged, "ok": f"/{object_rel}" in purged}

    # 3. tombstone: append-only disposition + barrier re-derivation.
    record = _disposition_for(
        object_rel,
        authority=authority,
        reason_category=reason_category,
        decided_at=decided_at,
        rationale=rationale,
        seq=len(_records_from_registry(registry_dir)),
    )
    _write_disposition(registry_dir, record)
    applied = apply_withdrawals(staged_root, _records_from_registry(registry_dir))
    denied_routes = list(applied.get("routes") or [])
    result.legs["tombstone"] = {
        "target_id": object_rel,
        "routes_denied": len(denied_routes),
        "ok": object_rel in denied_routes,
    }

    # 4. verify: 410 + tombstone at the web path, 404 at the mirror.
    web_status, web_body = web_probe(f"/{object_rel}")
    mirror_status, _mb = mirror_probe(f"/{object_rel}")
    tomb = False
    try:
        tomb = json.loads(web_body).get("schema") == "sig.tombstone/1" or (
            b"tombstone" in web_body.lower()
        )
    except (ValueError, AttributeError):
        tomb = b"tombstone" in (web_body or b"").lower()
    result.legs["verify"] = {
        "web_status": web_status,
        "web_tombstone": bool(tomb),
        "mirror_status": mirror_status,
        # the D20 acceptance verbatim: 410 + tombstone at the web path,
        # 404 at the mirror.
        "ok": web_status == 410 and bool(tomb) and mirror_status == 404,
    }
    return result


__all__ = [
    "REHEARSAL_SCHEMA",
    "RehearsalError",
    "RehearsalResult",
    "rehearse_withdrawal",
]
