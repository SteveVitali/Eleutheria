# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The operator-only true-deletion mechanism (P37.71; ADR-181/189).

Acceptance shape: a fixture deletion leaves a tombstone + a decision-log
entry (and an audit + receipt); no path invokes it without the operator's
in-ticket go; wildcards, missing authority and unbound stores refuse.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from ops import operator_deletion as od
from ops import release_pipeline as rp

NOW = "2026-11-06T16:30:00Z"
CLAIM = str(uuid.uuid4())


def _store(tmp_path: Path, name: str = "reg") -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path / name)


def _put(store: rp.Store, name: str, body: Any) -> None:
    store.insert(name, json.dumps(body).encode())


def _authority(store: rp.Store, name: str = "go-1", **fields: Any) -> dict[str, Any]:
    rec = {
        "schema": od.rr.AUTHORITY_SCHEMA,
        "kind": "go",
        "ref": f"OPS-{name}",
        "issued_at": NOW,
        **fields,
    }
    _put(store, f"{od.rr.AUTHORITIES_PREFIX}{name}", rec)
    return rec


def _order(tmp_path: Path, **over: Any) -> dict[str, Any]:
    order = {
        "schema": od.ORDER_SCHEMA,
        "order_id": "del-2026-11-06-test",
        "issued_at": NOW,
        "go_ref": "docs/build/LEDGER.md § GATE DECISIONS — 2026-11-06 test go",
        "category": "categorically_excluded",
        "reason": "fixture reason",
        "material": {},
        **over,
    }
    p = tmp_path / "order.json"
    p.write_text(json.dumps(order), encoding="utf-8")
    return order


def _object_stores(tmp_path: Path) -> dict[str, rp.LocalDirStore]:
    stores = {
        "evidence_objects": _store(tmp_path, "evidence"),
        "restricted_objects": _store(tmp_path, "restricted"),
        "derived_artifacts": _store(tmp_path, "derived"),
    }
    stores["evidence_objects"].insert("evidence/captures/a/b.bin", b"bytes")
    stores["restricted_objects"].insert("restricted/map.json", b"{}")
    stores["derived_artifacts"].insert("staged/v/pub/x.html", b"<html/>")
    return stores


def test_fixture_deletion_leaves_tombstone_and_decision_entry(tmp_path: Path) -> None:
    reg = _store(tmp_path)
    stores = _object_stores(tmp_path)
    _authority(reg)
    order = _order(
        tmp_path,
        material={
            "evidence_objects": ["evidence/captures/a/b.bin"],
            "restricted_objects": ["restricted/map.json"],
            "derived_artifacts": ["staged/v/pub/x.html"],
        },
    )
    od.execute_deletion(order, registry=reg, authority="go-1", stores=stores, now=NOW)
    # objects are gone
    assert stores["evidence_objects"].read("evidence/captures/a/b.bin") is None
    assert stores["restricted_objects"].read("restricted/map.json") is None
    assert stores["derived_artifacts"].read("staged/v/pub/x.html") is None
    # tombstone: category + date + counts, never content
    tomb = json.loads(reg.read("registry/deletions/tombstones/del-2026-11-06-test.json"))
    assert tomb["schema"] == "sig.deletion-tombstone/1"
    assert tomb["operation"] == "deletion"
    assert tomb["category"] == "categorically_excluded"
    assert tomb["occurred_at"] == NOW
    assert tomb["counts"] == {
        "claims": 0,
        "evidence_objects": 1,
        "restricted_objects": 1,
        "derived_artifacts": 1,
    }
    assert "b.bin" not in json.dumps(tomb)
    # audit names the targets internally
    audit = json.loads(reg.read("registry/deletions/audit/del-2026-11-06-test.json"))
    assert audit["schema"] == "sig.deletion-audit/1"
    assert audit["targets"]["evidence_objects"] == ["evidence/captures/a/b.bin"]
    # the decision-log entry is a valid sig.editorial-decision/1 tombstone entry
    entry = json.loads(reg.read("registry/deletions/decision-entries/del-2026-11-06-test.json"))
    assert entry["schema"] == "sig.editorial-decision/1"
    assert entry["class"] == "deletion"
    assert entry["tombstone"]["category"] == "categorically_excluded"
    assert entry["gate_ref"]["row"]
    assert entry["gate_ref"]["recorded_at"] == NOW
    # receipt binds it all
    receipt = json.loads(reg.read("registry/receipts/deletion-del-2026-11-06-test.json"))
    assert receipt["schema"] == "sig.deletion-receipt/1"
    assert receipt["decision_entry_id"] == entry["decision_id"]


def test_fixture_purge_invokes_the_db_function_and_records(tmp_path: Path) -> None:
    reg = _store(tmp_path)
    _authority(reg)
    order = _order(tmp_path, material={"claims": [CLAIM]})
    calls: list[dict[str, Any]] = []

    def fake_purge(dsn, ids, *, category, authority_ref, decision_entry_id):
        calls.append(
            {
                "dsn": dsn,
                "ids": list(ids),
                "category": category,
                "authority_ref": authority_ref,
                "decision_entry_id": decision_entry_id,
            }
        )
        return {
            "tombstone_id": str(uuid.uuid4()),
            "audit_id": str(uuid.uuid4()),
            "executed_by": "op",
            "executed_role": "sig_purge_operator",
            "detail": {},
        }

    out = od.execute_deletion(
        order,
        registry=reg,
        authority="go-1",
        dsn="postgresql://fixture",
        now=NOW,
        purge_claims_fn=fake_purge,
    )
    assert calls == [
        {
            "dsn": "postgresql://fixture",
            "ids": [CLAIM],
            "category": "categorically_excluded",
            "authority_ref": order["go_ref"],
            "decision_entry_id": out["decision_entry"]["decision_id"],
        }
    ]
    assert out["operation"] == "purge"
    assert out["tombstone"]["counts"]["claims"] == 1
    assert out["tombstone"]["claim_tombstone_id"]
    entry = out["decision_entry"]
    assert entry["class"] == "purge"


def test_no_path_without_the_go(tmp_path: Path) -> None:
    reg = _store(tmp_path)
    stores = _object_stores(tmp_path)
    order = _order(tmp_path, material={"evidence_objects": ["evidence/captures/a/b.bin"]})
    # no authority record at all
    with pytest.raises(rp.PipelineError, match="authority"):
        od.execute_deletion(order, registry=reg, authority="go-1", stores=stores)
    # revoked record
    _authority(reg, name="revoked", revoked=True)
    with pytest.raises(rp.PipelineError, match="authorise"):
        od.execute_deletion(order, registry=reg, authority="revoked", stores=stores)
    # nothing deleted on either refusal
    assert stores["evidence_objects"].read("evidence/captures/a/b.bin") == b"bytes"


def test_wildcards_and_empty_material_refuse(tmp_path: Path) -> None:
    for bad in ("evidence/captures/*", "../escape", "/abs", "a?[b]"):
        with pytest.raises(rp.PipelineError):
            _order(tmp_path, material={"evidence_objects": [bad]}) and od.load_order(
                tmp_path / "order.json"
            )
    with pytest.raises(rp.PipelineError, match="no material"):
        od.validate_order(_order(tmp_path, material={}))


def test_unbound_store_and_claim_leg_refusals(tmp_path: Path) -> None:
    reg = _store(tmp_path)
    _authority(reg)
    order = _order(tmp_path, material={"restricted_objects": ["restricted/map.json"]})
    with pytest.raises(rp.PipelineError, match="bound that surface"):
        od.execute_deletion(order, registry=reg, authority="go-1", stores={})
    corder = _order(tmp_path, material={"claims": [CLAIM]})
    with pytest.raises(rp.PipelineError, match="no --dsn bound"):
        od.execute_deletion(corder, registry=reg, authority="go-1")


def test_verify_emits_probe_run_and_proves_absence(tmp_path: Path) -> None:
    stores = _object_stores(tmp_path)
    order = _order(tmp_path, material={"evidence_objects": ["evidence/captures/a/b.bin"]})
    # object still present → fail
    rec = od.verify_deletion(order, stores=stores)
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "fail"
    assert rec["checks"]["evidence_objects"]["remaining"] == ["evidence/captures/a/b.bin"]
    # deleted → pass on that leg; unused legs report skipped, so overall is
    # honest 'partial' (never a fabricated full pass)
    stores["evidence_objects"].delete("evidence/captures/a/b.bin")
    rec = od.verify_deletion(order, stores=stores)
    assert rec["overall"] == "partial"
    assert rec["checks"]["evidence_objects"]["verdict"] == "pass"
    # a named claim with no probe bound reports skipped honestly
    corder = _order(tmp_path, material={"claims": [CLAIM]})
    rec = od.verify_deletion(corder, stores={})
    assert rec["checks"]["claims"]["verdict"] == "skipped"
    assert rec["overall"] == "partial"


def test_plan_is_read_only(tmp_path: Path) -> None:
    stores = _object_stores(tmp_path)
    order = _order(
        tmp_path,
        material={
            "evidence_objects": ["evidence/captures/a/b.bin", "evidence/captures/missing.bin"]
        },
    )
    plan = od.plan_deletion(order, stores)
    assert plan["legs"]["evidence_objects"]["present"] == 1
    assert plan["legs"]["evidence_objects"]["missing"] == ["evidence/captures/missing.bin"]
    # nothing was touched
    assert stores["evidence_objects"].read("evidence/captures/a/b.bin") == b"bytes"


def test_decision_entry_matches_the_committed_contract(tmp_path: Path) -> None:
    """The emitted entry conforms to sig.editorial-decision/1 — mirrors
    isEditorialDecision in web/src/lib/editorial-decisions.ts."""
    reg = _store(tmp_path)
    _authority(reg)
    order = _order(tmp_path, material={"restricted_objects": ["restricted/map.json"]})
    stores = _object_stores(tmp_path)
    out = od.execute_deletion(order, registry=reg, authority="go-1", stores=stores, now=NOW)
    e = out["decision_entry"]
    assert e["schema"] == "sig.editorial-decision/1"
    for field in (
        "decision_id",
        "class",
        "decided_at",
        "logged_at",
        "decision",
        "scope",
        "rationale",
    ):
        assert isinstance(e[field], str) and e[field]
    assert e["retroactive"] is False
    assert e["class"] in ("deletion", "purge")
    assert isinstance(e["tombstone"], dict) and e["tombstone"]["category"]
    assert isinstance(e["evidence"], list)


def test_category_vocabulary_matches_the_db_check(tmp_path: Path) -> None:
    from db.operator_purge import PURGE_CATEGORIES

    assert od.DELETION_CATEGORIES == PURGE_CATEGORIES
    deploy = (Path(__file__).resolve().parents[2] / "db/deploy/operator_purge.sql").read_text()
    for cat in PURGE_CATEGORIES:
        assert f"'{cat}'" in deploy
