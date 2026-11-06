# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The operator-only true-deletion mechanism (P37.71; ADR-181/WV-06 +
ADR-189/WV-11; SIG-GOV-007/008/009, SIG-STORE-011).

Two halves, one gate:

* **deletion** — evidence bytes, restricted objects and derived artifacts the
  go names are deleted from their stores. Possible because the evidence
  bucket's retention is 365-day *unlocked* (ADR-177, B-14 = a) and the object
  lock is governance-mode (SIG-GOV-009) — the act is an operator decision,
  never a routine.
* **purge** — the named claim rows are removed through ``sig_purge_claims``,
  the one DB-enforced function executable only by ``sig_purge_operator`` (the
  sole SIG-STORE-011 exception). Every other role and path stays append-only.

Every use is gated the same way: a ``sig.deletion-order/1`` file naming the
material verbatim (no wildcards — a purge never scans a prefix) plus a
``sig.operator-authority/1`` record on the registry store, verified — never
created — per SIG-SEC-010. The mechanism is never pre-authorised and never
agent-initiated; nothing calls it without the operator's in-ticket go.

A governed run always leaves three append-only records — the audit trail the
waiver requires:

* ``registry/deletions/tombstones/<order_id>.json`` — ``sig.deletion-tombstone/1``:
  category + date + counts, never content;
* ``registry/deletions/audit/<order_id>.json`` — ``sig.deletion-audit/1``:
  the authorisation and the act, internal;
* ``registry/deletions/decision-entries/<order_id>.json`` — the
  ``sig.editorial-decision/1`` entry the operator commits to the public
  decision log (P37.7) with the same go,

plus ``registry/receipts/deletion-<order_id>.json`` — the run receipt. The DB
half writes ``purge_tombstone`` + ``purge_audit`` in the same transaction as
the delete itself.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.operator_purge import PURGE_CATEGORIES
from db.operator_purge import purge_claims as _db_purge_claims

from . import probe_run
from . import release_pipeline as rp
from . import release_reversal as rr

ORDER_SCHEMA = "sig.deletion-order/1"
TOMBSTONE_SCHEMA = "sig.deletion-tombstone/1"
AUDIT_SCHEMA = "sig.deletion-audit/1"
RECEIPT_SCHEMA = "sig.deletion-receipt/1"
DECISION_ENTRY_SCHEMA = "sig.editorial-decision/1"

#: The closed category vocabulary — the same CHECK list the
#: ``operator_purge`` sqitch change enforces (mirrored from
#: ``db.operator_purge.PURGE_CATEGORIES``; a test pins equality).
DELETION_CATEGORIES = PURGE_CATEGORIES

#: The material kinds an order may name. Object kinds map to the store an
#: ``--*-store`` option binds; ``claims`` rides the claim-spine DSN.
MATERIAL_KINDS = (
    "claims",
    "evidence_objects",
    "restricted_objects",
    "derived_artifacts",
)

#: A deletion names objects verbatim — never a glob, prefix or traversal.
_BAD_NAME = re.compile(r"(^/)|(\.\.)|[*?[\]]")

DELETIONS_PREFIX = "registry/deletions/"
RECEIPTS_PREFIX = "registry/receipts/"


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(obj: Any) -> bytes:
    from exports.release_identity import canonical_json

    return canonical_json(obj)


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# The order — parsed and validated fail-closed                                 #
# --------------------------------------------------------------------------- #


def _clean_name(kind: str, name: Any) -> str:
    if not isinstance(name, str) or not name.strip():
        raise rp.PipelineError(
            "bad-target-name", f"{kind} target must be a non-empty object name — got {name!r}"
        )
    if _BAD_NAME.search(name):
        raise rp.PipelineError(
            "wildcard-refused",
            f"{kind} target {name!r} is a glob/traversal — an order names each "
            "object verbatim, never a prefix",
        )
    return name


def validate_order(order: Any) -> dict[str, Any]:
    """Validate a ``sig.deletion-order/1`` document fail-closed.

    Every refusal names the violated field; a malformed order can never reach
    a delete path.
    """
    if not isinstance(order, dict) or order.get("schema") != ORDER_SCHEMA:
        raise rp.PipelineError("order-schema", f"order does not declare schema {ORDER_SCHEMA!r}")
    reasons: list[str] = []
    for field in ("order_id", "issued_at", "go_ref", "category"):
        if not str(order.get(field) or "").strip():
            reasons.append(f"order carries no {field}")
    if order.get("category") not in DELETION_CATEGORIES:
        reasons.append(
            f"category {order.get('category')!r} is not in the closed vocabulary "
            f"{sorted(DELETION_CATEGORIES)}"
        )
    material = order.get("material")
    if not isinstance(material, dict):
        reasons.append("order carries no material object")
        material = {}
    named = 0
    for kind in MATERIAL_KINDS:
        values = material.get(kind, [])
        if values is None:
            values = []
        if not isinstance(values, list):
            reasons.append(f"material.{kind} is not a list")
            continue
        if kind == "claims":
            for raw in values:
                try:
                    uuid.UUID(str(raw))
                except (ValueError, AttributeError):
                    reasons.append(f"material.claims entry {raw!r} is not a uuid")
        else:
            for raw in values:
                try:
                    _clean_name(kind, raw)
                except rp.PipelineError as exc:
                    reasons.append(str(exc))
        named += len(values)
    if named == 0:
        reasons.append("the order names no material")
    if reasons:
        raise rp.PipelineError("order-refused", "; ".join(reasons))
    return order


def load_order(path: str | Path) -> dict[str, Any]:
    """Read + validate the order file — the operator's in-ticket go naming
    the material."""
    p = Path(path)
    if not p.is_file():
        raise rp.PipelineError("order-absent", f"{p} does not exist")
    try:
        order = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise rp.PipelineError("order-unreadable", f"{p} is not JSON: {exc}") from exc
    return validate_order(order)


def order_material(order: dict[str, Any]) -> dict[str, list[str]]:
    """The named material, keyed by kind — lists normalised, never wildcarded."""
    material = order.get("material") or {}
    return {kind: [str(v) for v in (material.get(kind) or [])] for kind in MATERIAL_KINDS}


def decision_entry_id(order: dict[str, Any]) -> str:
    """The ``sig.editorial-decision/1`` id the entry will carry — either the
    order's own ``decision_entry_id`` or the deterministic one derived from
    the order id (``ed:<issue-date>:<order slug>``)."""
    declared = str(order.get("decision_entry_id") or "").strip()
    if declared:
        return declared
    issued = str(order.get("issued_at") or "")[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", str(order.get("order_id") or "deletion").lower()).strip("-")
    return f"ed:{issued}:{slug}"


def plan_deletion(order: dict[str, Any], stores: dict[str, rp.Store]) -> dict[str, Any]:
    """The read-only plan: what the order names, which objects exist, what a
    delete would touch. Never mutates."""
    material = order_material(order)
    legs: dict[str, Any] = {}
    for kind in ("evidence_objects", "restricted_objects", "derived_artifacts"):
        store = stores.get(kind)
        names = material[kind]
        if names and store is None:
            legs[kind] = {
                "named": len(names),
                "present": 0,
                "missing": names,
                "store": "UNBOUND — pass the matching --*-store option",
            }
            continue
        present: list[str] = []
        missing: list[str] = []
        for name in names:
            (present if store.read(name) is not None else missing).append(name)  # type: ignore[union-attr]
        legs[kind] = {
            "named": len(names),
            "present": len(present),
            "missing": missing,
            "store": store.describe() if store is not None else None,
        }
    legs["claims"] = {
        "named": len(material["claims"]),
        "path": "sig_purge_claims over the claim-spine DSN (--dsn)",
    }
    return {
        "order_id": order["order_id"],
        "category": order["category"],
        "go_ref": order["go_ref"],
        "legs": legs,
        "decision_entry_id": decision_entry_id(order),
    }


# --------------------------------------------------------------------------- #
# The emitted records                                                          #
# --------------------------------------------------------------------------- #


def _tombstone_record(
    order: dict[str, Any],
    results: dict[str, Any],
    *,
    occurred_at: str,
    entry_id: str,
) -> dict[str, Any]:
    """``sig.deletion-tombstone/1`` — category + date + counts, never content."""
    counts = {
        "claims": results["claims"]["purged"],
        "evidence_objects": results["evidence_objects"]["deleted"],
        "restricted_objects": results["restricted_objects"]["deleted"],
        "derived_artifacts": results["derived_artifacts"]["deleted"],
    }
    operation = "purge" if counts["claims"] else "deletion"
    return {
        "schema": TOMBSTONE_SCHEMA,
        "tombstone_id": str(uuid.uuid4()),
        "order_id": order["order_id"],
        "operation": operation,
        "category": order["category"],
        "occurred_at": occurred_at,
        "authority_ref": order["go_ref"],
        "counts": counts,
        "claim_tombstone_id": results["claims"].get("tombstone_id"),
        "decision_entry_id": entry_id,
    }


def _audit_record(
    order: dict[str, Any],
    authority: dict[str, Any],
    results: dict[str, Any],
    *,
    occurred_at: str,
) -> dict[str, Any]:
    """``sig.deletion-audit/1`` — the internal record of the authorisation and
    the act (names the target ids; restricted, never the public surface)."""
    return {
        "schema": AUDIT_SCHEMA,
        "audit_id": str(uuid.uuid4()),
        "order_id": order["order_id"],
        "category": order["category"],
        "authority_ref": order["go_ref"],
        "authority_record": authority,
        "targets": order_material(order),
        "results": results,
        "recorded_at": occurred_at,
    }


def _decision_entry(
    order: dict[str, Any],
    tombstone: dict[str, Any],
    *,
    occurred_at: str,
    entry_id: str,
) -> dict[str, Any]:
    """The ``sig.editorial-decision/1`` entry the operator commits to the
    public decision log (P37.7) with the same go — a tombstone-shaped entry:
    category + date, never the deleted content."""
    counts = tombstone["counts"]
    legs = ", ".join(f"{k}={v}" for k, v in counts.items())
    return {
        "schema": DECISION_ENTRY_SCHEMA,
        "decision_id": entry_id,
        "class": tombstone["operation"],
        "decided_at": order["issued_at"],
        "logged_at": occurred_at[:10],
        "retroactive": False,
        "decision": (
            f"True {tombstone['operation']} under the operator's in-ticket go "
            f"{order['go_ref']} — order {order['order_id']}."
        ),
        "scope": (
            f"SIG-GOV-008 material ({order['category']}); removed: {legs}. "
            "Every other path stays append-only."
        ),
        "rationale": order.get("reason") or "recorded in the order's go",
        "gate_ref": {"row": order["go_ref"], "recorded_at": order["issued_at"]},
        "evidence": [
            f"registry/deletions/tombstones/{order['order_id']}.json",
            f"registry/receipts/deletion-{order['order_id']}.json",
        ],
        "tombstone": {"category": order["category"]},
    }


# --------------------------------------------------------------------------- #
# execute / verify                                                             #
# --------------------------------------------------------------------------- #


def execute_deletion(
    order: dict[str, Any],
    *,
    registry: rp.Store,
    authority: str,
    stores: dict[str, rp.Store] | None = None,
    dsn: str | None = None,
    now: str | None = None,
    purge_claims_fn: Any = _db_purge_claims,
) -> dict[str, Any]:
    """Run one governed deletion. Every step is recorded; a refusal anywhere
    aborts before the first delete (the plan phase validates everything)."""
    order = validate_order(order)
    occurred_at = now or _utcnow()
    stores = stores or {}
    material = order_material(order)

    # The authority record is verified, never created (SIG-SEC-010).
    auth = rr.check_authority(registry, authority, now=None)

    # The claim leg needs a DSN; an absent store for a named object leg is a
    # refusal, never a silent skip.
    if material["claims"] and not dsn:
        raise rp.PipelineError(
            "dsn-required",
            "the order names claims but no --dsn bound the claim spine — never silently skipped",
        )
    for kind in ("evidence_objects", "restricted_objects", "derived_artifacts"):
        if material[kind] and stores.get(kind) is None:
            raise rp.PipelineError(
                "store-unbound",
                f"the order names {kind} but no --*-store bound that surface",
            )

    entry_id = decision_entry_id(order)
    results: dict[str, Any] = {}

    # Object legs: delete the named objects; a missing object is a recorded
    # outcome, never a fabricated delete.
    for kind in ("evidence_objects", "restricted_objects", "derived_artifacts"):
        store = stores.get(kind)
        deleted: list[str] = []
        missing: list[str] = []
        if store is not None:
            for name in material[kind]:
                if store.read(name) is None:
                    missing.append(name)
                else:
                    store.delete(name)
                    deleted.append(name)
        results[kind] = {"deleted": len(deleted), "deleted_names": deleted, "missing": missing}

    # The claim leg — the sole SIG-STORE-011 exception, via the DB function.
    if material["claims"]:
        out = purge_claims_fn(
            dsn,
            material["claims"],
            category=order["category"],
            authority_ref=order["go_ref"],
            decision_entry_id=entry_id,
        )
        results["claims"] = {
            "purged": len(material["claims"]),
            "tombstone_id": out["tombstone_id"],
            "audit_id": out["audit_id"],
        }
    else:
        results["claims"] = {"purged": 0}

    # Records — tombstone, audit, the decision-log entry, the receipt.
    tombstone = _tombstone_record(order, results, occurred_at=occurred_at, entry_id=entry_id)
    audit = _audit_record(order, auth, results, occurred_at=occurred_at)
    entry = _decision_entry(order, tombstone, occurred_at=occurred_at, entry_id=entry_id)
    registry.insert(
        f"{DELETIONS_PREFIX}tombstones/{order['order_id']}.json",
        _canonical(tombstone),
        content_type="application/json",
    )
    registry.insert(
        f"{DELETIONS_PREFIX}audit/{order['order_id']}.json",
        _canonical(audit),
        content_type="application/json",
    )
    registry.insert(
        f"{DELETIONS_PREFIX}decision-entries/{order['order_id']}.json",
        _canonical(entry),
        content_type="application/json",
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "order_id": order["order_id"],
        "authority": auth,
        "executed_at": occurred_at,
        "tombstone_sha256": _sha256(_canonical(tombstone)),
        "decision_entry_id": entry_id,
        "results": results,
    }
    registry.insert(
        f"{RECEIPTS_PREFIX}deletion-{order['order_id']}.json",
        _canonical(receipt),
        content_type="application/json",
    )
    return {
        "applied": True,
        "order_id": order["order_id"],
        "operation": tombstone["operation"],
        "tombstone": tombstone,
        "audit_id": audit["audit_id"],
        "decision_entry": entry,
        "receipt": receipt,
        "results": results,
    }


def verify_deletion(
    order: dict[str, Any],
    *,
    stores: dict[str, rp.Store] | None = None,
    dsn: str | None = None,
    claim_absent_fn: Any = None,
) -> dict[str, Any]:
    """The post-run verify — a ``sig.probe-run/1`` whose every leg proves the
    named material is gone. A leg it cannot evaluate is ``skipped``, never a
    fabricated pass."""
    order = validate_order(order)
    stores = stores or {}
    material = order_material(order)
    checks: dict[str, probe_run.CheckResult] = {}
    for kind in ("evidence_objects", "restricted_objects", "derived_artifacts"):
        names = material[kind]
        store = stores.get(kind)
        if not names:
            checks[kind] = probe_run.CheckResult("skipped", {"reason": "no targets named"})
            continue
        if store is None:
            checks[kind] = probe_run.CheckResult("skipped", {"reason": "no store bound"})
            continue
        remaining = [n for n in names if store.read(n) is not None]
        checks[kind] = probe_run.CheckResult(
            "fail" if remaining else "pass",
            {"offered": len(names), "evaluated": len(names), "remaining": remaining},
        )
    if material["claims"]:
        if claim_absent_fn is not None:
            remaining = [c for c in material["claims"] if not claim_absent_fn(dsn, c)]
            checks["claims"] = probe_run.CheckResult(
                "fail" if remaining else "pass",
                {
                    "offered": len(material["claims"]),
                    "evaluated": len(material["claims"]),
                    "remaining": remaining,
                },
            )
        else:
            checks["claims"] = probe_run.CheckResult(
                "skipped", {"reason": "no claim-absent probe bound"}
            )
    else:
        checks["claims"] = probe_run.CheckResult("skipped", {"reason": "no targets named"})
    return probe_run.build_record(
        probe="operator-deletion-verify",
        checks=checks,
        subject={"order_id": order["order_id"], "category": order["category"]},
    )
