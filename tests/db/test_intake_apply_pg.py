# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The reviewed-correction application bridge over real PostgreSQL
(P32.16a / ADR-135 follow-up, SIG-FIND-008).

Docker-backed (postgis:18-3.6 + the full sqitch plan). The AC proofs:

* **Canonical path only.** ``correct`` lands the §16.6 pair (close the old
  claim's sys_period + a new claim carrying revises_claim/correction_reason/
  asserted_by curator) in ONE transaction with the applied receipt and the
  `applied` event — through the real append-only machinery, never a parallel
  write. ``suppress``/``delete`` land ``publication_disposition`` rows;
  ``refuse`` never reaches the bridge.
* **Exactly once.** approve→apply→restart→retry reconciles by
  UNIQUE(operation_id) to the SAME applied receipt — no second canonical
  write. Failed/uncertain transactions leave nothing.
* **Refusals don't mutate.** Unauthorized roles, stale records, changed
  evidence, unsafe payloads, unapproved proposals and denials fail without
  touching the graph.
* **Distinct states + ids.** received / reviewed(approved) / applied /
  unpublished / published stay visibly distinct; the applied receipt links to
  the release identity and the corrections-log pointer after publication.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import psycopg
import pytest
from conftest import seed_claim_prerequisites
from db.intake_apply import (
    IntakeApplyError,
    PgIntakeApplicationStore,
    claim_evidence_digest,
    claim_state_digest,
    derive_operation_id,
)
from psycopg.rows import dict_row, tuple_row

from policy import intake as pint


def _dsn(db: dict[str, object]) -> str:
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"


@pytest.fixture()
def seed_conn(sig_database: dict[str, object]) -> Any:
    """A committed superuser conn (dict_row) — fixtures must outlive the
    rollback-scoped `conn` fixture for the bridge's role-scoped session."""
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    yield c
    c.close()


@pytest.fixture()
def bridge_conn(sig_database: dict[str, object]) -> Any:
    """A committed, role-scoped bridge connection — the from_dsn pattern."""
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    c.execute("SET ROLE sig_intake_bridge")
    yield c
    c.close()


@pytest.fixture()
def rev_conn(sig_database: dict[str, object]) -> Any:
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    c.execute("SET ROLE sig_intake_reviewer")
    yield c
    c.close()


@pytest.fixture()
def recv_conn(sig_database: dict[str, object]) -> Any:
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    c.execute("SET ROLE sig_intake_receiver")
    yield c
    c.close()


# --------------------------------------------------------------------------- #
# Seed helpers — committed fixture state the bridge session can see.
# --------------------------------------------------------------------------- #
def _seed_capture(conn: Any, prereqs: dict[str, object], key: str) -> str:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted','obey',true)"
        " ON CONFLICT (source_id) DO NOTHING",
        (f"src-apply-{key}", f"src-apply-{key}", prereqs["rights_id"]),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (f"src-apply-{key}", f"urn:sig:apply:{key}", prereqs["rights_id"]),
    )
    artifact_id = cur.fetchone()["artifact_id"]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact_id,
            f"digest-{key}",
            prereqs["run_id"],
            f"urn:sig:apply:{key}",
            f"urn:sig:apply:{key}",
        ),
    )
    return str(cur.fetchone()["capture_id"])


def _seed_claim(
    conn: Any, key: str, *, tier: int = 0, value_num: int = 25, bind: bool = True
) -> dict[str, Any]:
    """A live tier-0 quantity claim + (optionally) one evidence binding."""
    prereqs = seed_claim_prerequisites(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,value_num,unit,raw_value,observed_at,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'cameras',%s,"
        "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,%s)"
        " RETURNING claim_id",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            str(value_num),
            value_num,
            str(value_num),
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            tier,
        ),
    )
    claim_id = str(cur.fetchone()["claim_id"])
    capture_id = None
    if bind:
        capture_id = _seed_capture(conn, prereqs, key)
        conn.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role)"
            " VALUES(%s::uuid,%s::uuid,'establishes')",
            (claim_id, capture_id),
        )
    row = conn.execute("SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,)).fetchone()
    evidence_rows = [
        tuple(r.values())
        for r in conn.execute(
            "SELECT capture_id::text, role, binding_status FROM claim_evidence"
            " WHERE claim_id = %s::uuid ORDER BY capture_id, role",
            (claim_id,),
        ).fetchall()
    ]
    return {
        "prereqs": prereqs,
        "claim_id": claim_id,
        "capture_id": capture_id,
        "claim_digest": claim_state_digest(dict(row)),
        "evidence_digest": claim_evidence_digest(evidence_rows),
    }


def _seed_report(conn: Any, key: str, claim_ids: list[str] | None = None) -> dict[str, str]:
    """Insert one report (citing the disputed claims) + its `received` event,
    under the receiver role like production does."""
    report_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sig-apply-test-{key}"))
    receipt_id = f"rct-{uuid.uuid5(uuid.NAMESPACE_DNS, f'rct-{key}').hex[:32]}"
    conn.execute("SET ROLE sig_intake_receiver")
    try:
        conn.execute(
            "INSERT INTO intake.report "
            "(report_id, receipt_id, idempotency_key, category, description,"
            " claim_ids, evidence_urls) VALUES (%s,%s,%s,'factual_error',%s,%s::jsonb,'[]')",
            (
                report_id,
                receipt_id,
                f"nonce-{key}-abcdefghij",
                "the count reads wrong — fixture narrative, never applied",
                json.dumps(claim_ids or []),
            ),
        )
        conn.execute(
            "INSERT INTO intake.event (report_id, event, actor)"
            " VALUES (%s,'received','sig-intake-receiver')",
            (report_id,),
        )
    finally:
        conn.execute("RESET ROLE")
    return {"report_id": report_id, "receipt_id": receipt_id}


def _propose(conn: Any, report_id: str, outcome: str, proposal: dict[str, Any] | None) -> int:
    """The reviewer's disposition_proposed — the same detail shape the API's
    validate_moderation_detail produces. Returns the event_seq."""
    detail: dict[str, Any] = {"outcome": outcome, "reason": "verified fixture"}
    if proposal is not None:
        detail["proposal"] = proposal
    row = conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, detail)"
        " VALUES (%s,'disposition_proposed','rev-1',%s::jsonb) RETURNING event_seq",
        (report_id, json.dumps(detail)),
    ).fetchone()
    return int(row["event_seq"])


def _approve(
    conn: Any,
    report_id: str,
    outcome: str,
    approves_seq: int,
    *,
    approver: str = "cur-1",
) -> int:
    row = conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, detail)"
        " VALUES (%s,'disposition_approved',%s,%s::jsonb) RETURNING event_seq",
        (
            report_id,
            approver,
            json.dumps(
                {
                    "outcome": outcome,
                    "reason": "verified against the cited record",
                    "approves_seq": approves_seq,
                }
            ),
        ),
    ).fetchone()
    return int(row["event_seq"])


def _proposal_correct(seed: dict[str, Any], value_num: int = 225, **extra: Any) -> dict[str, Any]:
    proposal: dict[str, Any] = {
        "target_kind": "claim",
        "target_id": seed["claim_id"],
        "claim_digest": seed["claim_digest"],
        "evidence_digest": seed["evidence_digest"],
        # P34.37 (C4 NEW-18): the declared object_type pins the value shape —
        # the seeded claim is object_type='quantity'.
        "object_type": "quantity",
        "value": {
            "value_text": str(value_num),
            "value_num": value_num,
            "unit": "cameras",
        },
        "correction_reason": "extraction_error",
    }
    proposal.update(extra)
    return proposal


def _claim_row(conn: Any, claim_id: str) -> dict[str, Any]:
    return dict(
        conn.execute("SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,)).fetchone()
    )


def _events_for(conn: Any, report_id: str) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT event_seq, event, actor, detail FROM intake.event"
            " WHERE report_id = %s ORDER BY event_seq",
            (report_id,),
        ).fetchall()
    ]


# --------------------------------------------------------------------------- #
# Grant shape — the bridge role's least-privilege matrix
# --------------------------------------------------------------------------- #
def test_bridge_role_grant_shape(conn: object) -> None:
    priv = lambda r, t, p: conn.execute(  # noqa: E731
        "SELECT has_table_privilege(%s, %s, %s)", (r, t, p)
    ).fetchone()[0]
    # The bridge writes canonical rows — but ONLY the narrow set.
    assert priv("sig_intake_bridge", "claim", "INSERT")
    assert priv("sig_intake_bridge", "claim_evidence", "INSERT")
    assert priv("sig_intake_bridge", "ingest_run", "INSERT")
    assert priv("sig_intake_bridge", "publication_disposition", "INSERT")
    assert priv("sig_intake_bridge", "entity", "INSERT")
    assert priv("sig_intake_bridge", "entity_identifier", "INSERT")
    assert priv("sig_intake_bridge", "entity_identity_key", "INSERT")
    assert priv("sig_intake_bridge", "intake.application", "INSERT")
    assert priv("sig_intake_bridge", "intake.event", "INSERT")
    # …and holds no mutation outside them.
    for t in ("claim", "intake.application", "intake.event", "publication_disposition"):
        assert not priv("sig_intake_bridge", t, "DELETE"), t
    # Column-level: sys_period close ONLY (the §16.6 correction step).
    col = lambda c, p: conn.execute(  # noqa: E731
        "SELECT has_column_privilege('sig_intake_bridge','claim',%s,%s)", (c, p)
    ).fetchone()[0]
    assert col("sys_period", "UPDATE")
    assert not col("raw_value", "UPDATE")
    # No review-write privilege — the bridge is not a reviewer.
    assert not priv("sig_intake_bridge", "review_decision", "INSERT")
    assert not priv("sig_intake_bridge", "intake.report", "INSERT")
    assert not priv("sig_intake_bridge", "intake.report", "UPDATE")
    assert not priv("sig_intake_bridge", "intake.reporter_contact", "SELECT")
    assert not priv("sig_intake_bridge", "evidence_capture", "INSERT")
    # The existing roles gained nothing.
    for role in ("sig_intake_receiver", "sig_intake_reviewer"):
        assert not priv(role, "intake.application", "INSERT"), role
        assert not priv(role, "claim", "INSERT"), role


# --------------------------------------------------------------------------- #
# Happy path — the canonical correction pair, atomic with the receipt
# --------------------------------------------------------------------------- #
def test_correct_apply_lands_canonical_pair(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "happy01")
    report = _seed_report(seed_conn, "happy01", [seed["claim_id"]])
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    _approve(rev_conn, report["report_id"], "correct", pseq, approver="cur-9")

    store = PgIntakeApplicationStore(bridge_conn)
    result = store.apply(report["receipt_id"], actor="cur-9")

    assert result["applied"] is True
    assert result["reconciled"] is False
    assert result["outcome"] == "correct"
    assert result["approved_by"] == "cur-9"
    assert result["applied_by"] == "cur-9"
    new_claim_id = result["result_claim_id"]
    assert new_claim_id != seed["claim_id"]
    assert result["operation_id"].startswith("op-")

    old = _claim_row(seed_conn, seed["claim_id"])
    new = _claim_row(seed_conn, new_claim_id)
    # §16.6: prior belief closed — the original assertion still exists.
    assert not old["sys_period"].upper_inf
    assert new["sys_period"].upper_inf
    assert str(new["revises_claim"]) == seed["claim_id"]
    assert new["correction_reason"] == "extraction_error"
    assert int(new["value_num"]) == 225
    assert new["value_text"] == "225"
    # The approving curator asserts the correction — a `person` entity under
    # the guarded sig.curator.handle scheme (§11.3 attributable curators).
    ident = seed_conn.execute(
        "SELECT entity_id::text FROM entity_identifier"
        " WHERE scheme = 'sig.curator.handle' AND value = 'cur-9'"
    ).fetchone()
    assert ident is not None
    assert str(new["asserted_by"]) == ident["entity_id"]
    ent = seed_conn.execute(
        "SELECT entity_type FROM entity WHERE entity_id = %s::uuid",
        (ident["entity_id"],),
    ).fetchone()
    assert ent["entity_type"] == "person"
    # The bridge's ingest run carries the operation's provenance.
    run = seed_conn.execute(
        "SELECT connector_name, parameters FROM ingest_run WHERE run_id = %s::uuid",
        (result["ingest_run_id"],),
    ).fetchone()
    assert run["connector_name"] == "sig.intake.bridge"
    assert run["parameters"]["operation_id"] == result["operation_id"]
    # The same captures re-bind to the new assertion (evidence preserved).
    bound = seed_conn.execute(
        "SELECT capture_id::text, role FROM claim_evidence WHERE claim_id = %s::uuid",
        (new_claim_id,),
    ).fetchall()
    assert [(r["capture_id"], r["role"]) for r in bound] == [(seed["capture_id"], "establishes")]
    # The applied receipt + lifecycle event — distinct ids, same transaction.
    events = _events_for(seed_conn, report["report_id"])
    applied = [e for e in events if e["event"] == "applied"]
    assert len(applied) == 1
    assert applied[0]["detail"]["application_id"] == result["application_id"]
    assert applied[0]["detail"]["operation_id"] == result["operation_id"]
    app = store.application(report["receipt_id"])
    assert app["operation_id"] == result["operation_id"]


def test_annotate_writes_non_superseding_claim(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "anno01")
    seed_conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES('fixture_note','1.0.0','string','literal','fixture',"
        "'MODERATE',365,'authoritative_source_wins') ON CONFLICT DO NOTHING"
    )
    report = _seed_report(seed_conn, "anno01", [seed["claim_id"]])
    proposal = _proposal_correct(
        seed,
        predicate_id="fixture_note",
        object_type="literal",
        value={"value_text": "noted in field visit"},
    )
    pseq = _propose(rev_conn, report["report_id"], "annotate", proposal)
    _approve(rev_conn, report["report_id"], "annotate", pseq)

    result = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    # The target claim is NOT closed — an annotation does not supersede.
    old = _claim_row(seed_conn, seed["claim_id"])
    assert old["sys_period"].upper_inf
    new = _claim_row(seed_conn, result["result_claim_id"])
    assert new["revises_claim"] is None
    assert new["predicate_id"] == "fixture_note"
    assert new["value_text"] == "noted in field visit"
    assert seed["claim_id"] in [str(x) for x in new["derived_from_claim_ids"]]


def test_suppress_records_canonical_disposition(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "supp01")
    report = _seed_report(seed_conn, "supp01", [seed["claim_id"]])
    proposal = {
        "target_kind": "claim",
        "target_id": seed["claim_id"],
        "claim_digest": seed["claim_digest"],
        "evidence_digest": seed["evidence_digest"],
        "reason_category": "suppressed",
        "disposition": "withhold",
    }
    pseq = _propose(rev_conn, report["report_id"], "suppress", proposal)
    _approve(rev_conn, report["report_id"], "suppress", pseq)

    result = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert result["result_claim_id"] is None
    row = seed_conn.execute(
        "SELECT target_kind, target_id, disposition, reason_category, authority,"
        " decided_by FROM publication_disposition"
        " WHERE disposition_id = %s::uuid",
        (result["disposition_id"],),
    ).fetchone()
    assert row["target_kind"] == "claim"
    assert row["target_id"] == seed["claim_id"]
    assert row["disposition"] == "withhold"
    assert row["reason_category"] == "suppressed"
    assert row["authority"].startswith("intake:approval:")
    # The disposition REALLY gates — the shared selector now denies the claim.
    from db.dispositions import effective_dispositions
    from policy.eligibility import Disposition, TargetKind

    # The batch reader unpacks rows positionally — feed it a tuple-row cursor.
    with seed_conn.cursor(row_factory=tuple_row) as tcur:
        eff = effective_dispositions(tcur, TargetKind.CLAIM, [seed["claim_id"]])
    assert eff[seed["claim_id"]].disposition is Disposition.WITHHOLD


def test_delete_maps_to_withdraw_never_delete(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "del01")
    report = _seed_report(seed_conn, "del01", [seed["claim_id"]])
    proposal = {
        "target_kind": "claim",
        "target_id": seed["claim_id"],
        "reason_category": "safety_withdrawal",
    }
    pseq = _propose(rev_conn, report["report_id"], "delete", proposal)
    _approve(rev_conn, report["report_id"], "delete", pseq)

    result = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    row = seed_conn.execute(
        "SELECT disposition FROM publication_disposition WHERE disposition_id = %s::uuid",
        (result["disposition_id"],),
    ).fetchone()
    # Byte-level deletion stays the separately gated process — withdraw is the
    # strongest non-destructive gate the registry offers.
    assert row["disposition"] == "withdraw"
    assert _claim_row(seed_conn, seed["claim_id"]) is not None


# --------------------------------------------------------------------------- #
# Explicit approval + exactly-once semantics
# --------------------------------------------------------------------------- #
def test_apply_requires_explicit_approval(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "noapp01")
    report = _seed_report(seed_conn, "noapp01", [seed["claim_id"]])
    store = PgIntakeApplicationStore(bridge_conn)
    # A bare report — nothing to approve.
    with pytest.raises(IntakeApplyError) as exc:
        store.apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "no_current_approval"
    # A proposal alone is not approval — the gate stays shut.
    _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    with pytest.raises(IntakeApplyError) as exc:
        store.apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "no_current_approval"
    # Nothing mutated.
    assert _claim_row(seed_conn, seed["claim_id"])["sys_period"].upper_inf
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM intake.application WHERE report_id = %s::uuid",
            (report["report_id"],),
        ).fetchone()["n"]
        == 0
    )


def test_retry_after_restart_reconciles_one_receipt(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any, sig_database: dict[str, object]
) -> None:
    """approve→apply→restart→retry yields ONE canonical disposition and ONE
    stable applied receipt (the ticket's idempotency AC)."""
    seed = _seed_claim(seed_conn, "retry01")
    report = _seed_report(seed_conn, "retry01", [seed["claim_id"]])
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    _approve(rev_conn, report["report_id"], "correct", pseq)

    first = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    # The "restart": a brand-new bridge session applies the same report.
    fresh = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    try:
        fresh.execute("SET ROLE sig_intake_bridge")
        second = PgIntakeApplicationStore(fresh).apply(report["receipt_id"], actor="cur-1")
    finally:
        fresh.close()
    assert second["reconciled"] is True
    assert second["application_id"] == first["application_id"]
    assert second["operation_id"] == first["operation_id"]
    assert second["result_claim_id"] == first["result_claim_id"]
    # Exactly one canonical write + one receipt + one applied event.
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM intake.application WHERE report_id = %s::uuid",
            (report["report_id"],),
        ).fetchone()["n"]
        == 1
    )
    applied_events = [
        e for e in _events_for(seed_conn, report["report_id"]) if e["event"] == "applied"
    ]
    assert len(applied_events) == 1
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM claim WHERE revises_claim = %s::uuid",
            (seed["claim_id"],),
        ).fetchone()["n"]
        == 1
    )


def test_explicit_operation_id_reconciles(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "opid01")
    report = _seed_report(seed_conn, "opid01", [seed["claim_id"]])
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    _approve(rev_conn, report["report_id"], "correct", pseq)
    store = PgIntakeApplicationStore(bridge_conn)
    first = store.apply(report["receipt_id"], actor="cur-1", operation_id="op-test-xyz")
    assert first["operation_id"] == "op-test-xyz"
    second = store.apply(report["receipt_id"], actor="cur-1", operation_id="op-test-xyz")
    assert second["reconciled"] is True
    # A DIFFERENT operation id on the same report is a conflict, not a retry.
    with pytest.raises(IntakeApplyError) as exc:
        store.apply(report["receipt_id"], actor="cur-1", operation_id="op-different-1")
    assert exc.value.code == "operation_id_conflict"


def test_derived_operation_id_is_stable(seed_conn: Any) -> None:
    assert derive_operation_id("rid", 7, "correct") == derive_operation_id("rid", 7, "correct")
    assert derive_operation_id("rid", 7, "correct") != derive_operation_id("rid", 8, "correct")
    assert derive_operation_id("rid", 7, "correct").startswith("op-")


def test_failed_transaction_leaves_nothing(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """An apply that fails MID-write (a claim CHECK the proposal validator
    cannot see — a future observed_at) rolls back the close+insert+receipt:
    the old claim stays open, no application row, no applied event."""
    seed = _seed_claim(seed_conn, "failtx01")
    report = _seed_report(seed_conn, "failtx01", [seed["claim_id"]])
    proposal = _proposal_correct(
        seed,
        scope={"observed_at": "2999-01-01T00:00:00Z"},  # future-ok: synthetic: sentinel observed_at
    )
    pseq = _propose(rev_conn, report["report_id"], "correct", proposal)
    _approve(rev_conn, report["report_id"], "correct", pseq)
    with pytest.raises(psycopg.errors.CheckViolation):
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    # Nothing landed — the only permitted claim update was rolled back.
    assert _claim_row(seed_conn, seed["claim_id"])["sys_period"].upper_inf
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM intake.application WHERE report_id = %s::uuid",
            (report["report_id"],),
        ).fetchone()["n"]
        == 0
    )
    assert [e for e in _events_for(seed_conn, report["report_id"]) if e["event"] == "applied"] == []


# --------------------------------------------------------------------------- #
# Unauthorized paths — the receiver/reviewer roles never apply
# --------------------------------------------------------------------------- #
def test_reviewer_role_cannot_write_application_or_events(rev_conn: Any, seed_conn: Any) -> None:
    report = _seed_report(seed_conn, "revdeny")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        rev_conn.execute(
            "INSERT INTO intake.application"
            "(report_id, operation_id, approval_seq, proposal_seq, outcome,"
            " approved_by, applied_by, target_kind, target_id)"
            " VALUES (%s,'op-nope-123456',1,1,'correct','x','x','claim','x')",
            (report["report_id"],),
        )
    for event in ("applied", "published"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            rev_conn.execute(
                "INSERT INTO intake.event (report_id, event, actor) VALUES (%s,%s,'rev-1')",
                (report["report_id"], event),
            )


def test_receiver_role_cannot_write_application_or_events(recv_conn: Any, seed_conn: Any) -> None:
    report = _seed_report(seed_conn, "recdeny")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        recv_conn.execute(
            "INSERT INTO intake.application"
            "(report_id, operation_id, approval_seq, proposal_seq, outcome,"
            " approved_by, applied_by, target_kind, target_id)"
            " VALUES (%s,'op-nope-654321',1,1,'correct','x','x','claim','x')",
            (report["report_id"],),
        )
    for event in ("applied", "published"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            recv_conn.execute(
                "INSERT INTO intake.event (report_id, event, actor)"
                " VALUES (%s,%s,'sig-intake-receiver')",
                (report["report_id"], event),
            )
    # And the receiver cannot even READ canonical state to forge a proposal.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        recv_conn.execute("SELECT 1 FROM claim LIMIT 1")


def test_bad_actor_refused(bridge_conn: Any, seed_conn: Any) -> None:
    report = _seed_report(seed_conn, "badact")
    store = PgIntakeApplicationStore(bridge_conn)
    with pytest.raises(IntakeApplyError) as exc:
        store.apply(report["receipt_id"], actor="BAD ACTOR!")
    assert exc.value.code == "bad_actor"


# --------------------------------------------------------------------------- #
# Stale / changed / unsafe / unanchored proposals — refusal without mutation
# --------------------------------------------------------------------------- #
def _approved_report(
    seed_conn: Any, rev_conn: Any, key: str, outcome: str, proposal: dict[str, Any] | None
) -> dict[str, str]:
    # The report must cite the disputed claim — the bridge refuses a proposal
    # whose target the reporter never flagged (target_not_reported).
    cited = None
    if proposal is not None and proposal.get("target_kind") == "claim":
        cited = [str(proposal["target_id"])]
    report = _seed_report(seed_conn, key, cited)
    pseq = _propose(rev_conn, report["report_id"], outcome, proposal)
    _approve(rev_conn, report["report_id"], outcome, pseq)
    return report


def test_stale_record_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "stale01")
    report = _approved_report(seed_conn, rev_conn, "stale01", "correct", _proposal_correct(seed))
    # The record moved on between approval and apply — belief already closed.
    seed_conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)')"
        " WHERE claim_id = %s::uuid",
        (seed["claim_id"],),
    )
    store = PgIntakeApplicationStore(bridge_conn)
    with pytest.raises(IntakeApplyError) as exc:
        store.apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "stale_record"
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM claim WHERE revises_claim = %s::uuid",
            (seed["claim_id"],),
        ).fetchone()["n"]
        == 0
    )


def test_changed_record_fingerprint_refused(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "chgrec01")
    proposal = _proposal_correct(seed)
    proposal["claim_digest"] = "0" * 64  # the reviewer saw a different row
    report = _approved_report(seed_conn, rev_conn, "chgrec01", "correct", proposal)
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "record_changed"


def test_changed_evidence_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "chgev01")
    report = _approved_report(seed_conn, rev_conn, "chgev01", "correct", _proposal_correct(seed))
    # A new evidence binding lands between approval and apply — the set the
    # reviewer pinned no longer matches.
    capture = _seed_capture(seed_conn, seed["prereqs"], "chgev01b")
    seed_conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role)"
        " VALUES(%s::uuid,%s::uuid,'corroborates')",
        (seed["claim_id"], capture),
    )
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "evidence_changed"


def test_object_type_mismatch_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """C4 NEW-18 (P34.37): a proposal validated for a DECLARED object_type
    that does not match the live target's resolved type is refused at apply —
    the shape that passed proposal-time validation may not fit the live
    record, so the bridge fails closed rather than apply an unvalidated
    shape. The stored proposal is a perfectly valid ``literal`` shape; the
    seeded target claim is ``quantity``."""
    seed = _seed_claim(seed_conn, "otype01")
    proposal = _proposal_correct(
        seed,
        # Literal-shaped value + a declared type that disagrees with the
        # target claim's 'quantity' — passes validate_proposal, fails the
        # declared/resolved agreement check.
        object_type="literal",
        value={"value_text": "twenty-five"},
    )
    report = _approved_report(seed_conn, rev_conn, "otype01", "correct", proposal)
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "object_type_mismatch"
    # Nothing reached the spine — refusal never mutates.
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM claim WHERE revises_claim = %s::uuid",
            (seed["claim_id"],),
        ).fetchone()["n"]
        == 0
    )


def test_unsafe_payload_never_reaches_the_spine(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    """A proposal carrying Part VIII-shaped content fails at proposal
    validation — and even if the raw JSON reaches the event log (a bypassing
    writer), the bridge's own screen refuses it without mutation."""
    seed = _seed_claim(seed_conn, "unsafe01")
    bad = _proposal_correct(seed, value={"value_text": "license plate ABC123", "value_num": 225})
    with pytest.raises(pint.IntakeFieldError):
        pint.validate_proposal("correct", bad)
    report = _approved_report(seed_conn, rev_conn, "unsafe01", "correct", bad)
    with pytest.raises(IntakeApplyError):
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM claim WHERE revises_claim = %s::uuid",
            (seed["claim_id"],),
        ).fetchone()["n"]
        == 0
    )
    assert _claim_row(seed_conn, seed["claim_id"])["sys_period"].upper_inf


def test_target_not_reported_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """The bridge applies only what the reporter flagged — a proposal naming
    an un-cited claim is refused even when the claim exists."""
    seed = _seed_claim(seed_conn, "notanchor")
    # The report cites NO claims — the proposal targets one anyway.
    report = _seed_report(seed_conn, "notanchor", [])
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    _approve(rev_conn, report["report_id"], "correct", pseq)
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "target_not_reported"


def test_moderator_denial_never_mutates(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """A `refuse` disposition is a real review outcome — it writes nothing
    canonical, silently or otherwise (SIG-GOV-004)."""
    seed = _seed_claim(seed_conn, "refuse01")
    report = _approved_report(seed_conn, rev_conn, "refuse01", "refuse", None)
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "outcome_not_appliable"
    old = _claim_row(seed_conn, seed["claim_id"])
    assert old["sys_period"].upper_inf and old["value_text"] == "25"
    assert (
        seed_conn.execute(
            "SELECT count(*) AS n FROM publication_disposition WHERE target_id = %s",
            (seed["claim_id"],),
        ).fetchone()["n"]
        == 0
    )


def test_restricted_sensitivity_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "tier01", tier=1)
    report = _approved_report(seed_conn, rev_conn, "tier01", "correct", _proposal_correct(seed))
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "restricted_target"


def test_denying_disposition_refused(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """A claim already under a current withhold is outside the bridge's
    public correction lane."""
    seed = _seed_claim(seed_conn, "denydisp")
    from db.dispositions import record_disposition
    from policy.eligibility import (
        Disposition,
        ReasonCategory,
        TargetKind,
        new_disposition,
    )

    record_disposition(
        seed_conn,
        new_disposition(
            target_kind=TargetKind.CLAIM,
            target_id=seed["claim_id"],
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.REVIEW_PENDING,
            authority="fixture",
        ),
    )
    report = _approved_report(seed_conn, rev_conn, "denydisp", "correct", _proposal_correct(seed))
    with pytest.raises(IntakeApplyError) as exc:
        PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "target_denied"


def test_reporter_text_is_never_applied(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    """The asserted value is the curator's approved proposal — the report's
    free-text narrative is never consulted as claim content."""
    seed = _seed_claim(seed_conn, "notxt01")
    report = _seed_report(seed_conn, "notxt01", [seed["claim_id"]])
    # The reporter's own text claims something else entirely — it is
    # quarantined narrative, never a claim input. (Payload columns may change
    # only through the maintenance functions; the superuser fixture writes
    # them directly to keep the seed minimal.)
    seed_conn.execute(
        "UPDATE intake.report SET description = 'the true value is 999 cameras' "
        "WHERE report_id = %s::uuid",
        (report["report_id"],),
    )
    pseq = _propose(
        rev_conn, report["report_id"], "correct", _proposal_correct(seed, value_num=225)
    )
    _approve(rev_conn, report["report_id"], "correct", pseq)
    result = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    new = _claim_row(seed_conn, result["result_claim_id"])
    assert new["value_text"] == "225"
    assert "999" not in (new["value_text"] or "")


# --------------------------------------------------------------------------- #
# Publication linkage + visible state distinction
# --------------------------------------------------------------------------- #
def test_publication_linkage_and_state_distinction(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    seed = _seed_claim(seed_conn, "pub01")
    report = _seed_report(seed_conn, "pub01", [seed["claim_id"]])
    store = PgIntakeApplicationStore(bridge_conn)

    def public_state() -> str:
        row = seed_conn.execute(
            "SELECT state FROM intake.report_public WHERE receipt_id = %s",
            (report["receipt_id"],),
        ).fetchone()
        return str(row["state"])

    # received — applied-vs-published are visibly DISTINCT at every step.
    assert public_state() == "received"
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    assert public_state() == "under_review"
    _approve(rev_conn, report["report_id"], "correct", pseq)
    assert public_state() == "decided"
    # Publishing before applying is refused.
    with pytest.raises(IntakeApplyError) as exc:
        store.mark_published(report["receipt_id"], actor="cur-1")
    assert exc.value.code == "not_applied"

    applied = store.apply(report["receipt_id"], actor="cur-1")
    # Applied is still "decided" publicly — applied ≠ published.
    assert public_state() == "decided"

    pub = store.mark_published(
        report["receipt_id"],
        actor="cur-1",
        publication_id="p-" + "a" * 64,
    )
    assert pub["event"] == "published"
    detail = pub["detail"]
    assert detail["publication_id"] == "p-" + "a" * 64
    # The public corrections-log pointer is the applied assertion.
    assert detail["correction_ref"] == applied["result_claim_id"]
    assert detail["application_id"] == applied["application_id"]
    assert detail["operation_id"] == applied["operation_id"]
    assert public_state() == "resolved"
    # Idempotent: republishing reconciles to the same event.
    again = store.mark_published(report["receipt_id"], actor="cur-1")
    assert again["reconciled"] is True and again["event_seq"] == pub["event_seq"]


def test_publish_linkage_validates_shapes(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "pubval")
    report = _seed_report(seed_conn, "pubval", [seed["claim_id"]])
    pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
    _approve(rev_conn, report["report_id"], "correct", pseq)
    store = PgIntakeApplicationStore(bridge_conn)
    store.apply(report["receipt_id"], actor="cur-1")
    # A malformed release namespace is refused — the link must resolve.
    with pytest.raises(IntakeApplyError) as exc:
        store.mark_published(report["receipt_id"], actor="cur-1", publication_id="not-a-release")
    assert exc.value.code == "invalid_linkage"
    # A safe tombstone is a legitimate linkage when no release ships.
    pub = store.mark_published(
        report["receipt_id"], actor="cur-1", tombstone="pending next release cut"
    )
    assert pub["detail"]["tombstone"] == "pending next release cut"
    assert "correction_ref" in pub["detail"]


# --------------------------------------------------------------------------- #
# The applied receipt is append-only like every other audit row
# --------------------------------------------------------------------------- #
def test_application_table_is_append_only(seed_conn: Any, rev_conn: Any, bridge_conn: Any) -> None:
    seed = _seed_claim(seed_conn, "apponly")
    report = _approved_report(seed_conn, rev_conn, "apponly", "correct", _proposal_correct(seed))
    result = PgIntakeApplicationStore(bridge_conn).apply(report["receipt_id"], actor="cur-1")
    for sql in (
        "UPDATE intake.application SET outcome = 'annotate' WHERE application_id = %s::uuid",
        "DELETE FROM intake.application WHERE application_id = %s::uuid",
    ):
        with pytest.raises(psycopg.errors.Error):
            seed_conn.execute(sql, (result["application_id"],))


def test_curator_entity_stable_across_applications(
    seed_conn: Any, rev_conn: Any, bridge_conn: Any
) -> None:
    """Two approvals by the same curator handle resolve asserted_by to ONE
    person entity — the guard never mints a duplicate."""
    store = PgIntakeApplicationStore(bridge_conn)
    results = []
    for key in ("custab01", "custab02"):
        seed = _seed_claim(seed_conn, key)
        report = _seed_report(seed_conn, key, [seed["claim_id"]])
        pseq = _propose(rev_conn, report["report_id"], "correct", _proposal_correct(seed))
        _approve(rev_conn, report["report_id"], "correct", pseq, approver="cur-7")
        results.append(store.apply(report["receipt_id"], actor="cur-7"))
    claims = [_claim_row(seed_conn, r["result_claim_id"]) for r in results]
    assert str(claims[0]["asserted_by"]) == str(claims[1]["asserted_by"])
    n = seed_conn.execute(
        "SELECT count(*) AS n FROM entity_identifier"
        " WHERE scheme = 'sig.curator.handle' AND value = 'cur-7'"
    ).fetchone()["n"]
    assert n == 1


def test_unknown_receipt(bridge_conn: Any) -> None:
    store = PgIntakeApplicationStore(bridge_conn)
    with pytest.raises(IntakeApplyError) as exc:
        store.apply("rct-" + "0" * 32, actor="cur-1")
    assert exc.value.code == "unknown_receipt"
