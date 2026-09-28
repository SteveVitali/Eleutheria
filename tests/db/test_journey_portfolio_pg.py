# SPDX-License-Identifier: Apache-2.0
"""P32.24 journey C — the durable receipt→moderation→canonical-correction
journey over a real PG18 spine (SIG-FIND-007, ADR-143).

Docker-backed (postgis:18-3.6 + the full sqitch plan). Executes
``ops.journey_verify.run_intake_journey`` end-to-end on the throwaway
testcontainer and asserts the emitted ``sig.journey-intake-proof/1`` plus the
canonical side-effects the journey is supposed to land:

* the receipt is durable before acknowledgement and visible to a
  fresh-connection store (the restart leg),
* the restricted reviewer queue sees it; the reporter's public projection
  stays coarse (received → decided → resolved — never leakier),
* the approved synthetic ``correct`` proposal traverses the P32.16a bridge to
  ONE canonical §16.6 close+revises pair, exactly once across a retry,
* the applied receipt links the staged release identity + the correction ref
  on publish, and
* a live ``sig_intake_receiver`` session cannot write a canonical row.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from ops import journey_verify as jv

PUB = "p-" + "ab" * 32
RECORD_KEY = "sig_graph:deployment:ent-acc-dep-00"


def _dsn(db: dict[str, object]) -> str:
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"


@pytest.fixture()
def proof(sig_database: dict[str, object]) -> dict[str, Any]:
    key = uuid.uuid4().hex[:8]
    return jv.run_intake_journey(
        dsn=_dsn(sig_database),
        publication_id=PUB,
        record_key_value=RECORD_KEY,
        report_key=key,
    )


def test_every_journey_step_is_ok(proof: dict[str, Any]) -> None:
    assert proof["schema"] == jv.INTAKE_PROOF_SCHEMA
    failed = [s for s in proof["steps"] if not s.get("ok")]
    assert failed == [], f"journey steps failed: {failed}"


def test_the_documented_steps_all_ran(proof: dict[str, Any]) -> None:
    steps = {s["step"] for s in proof["steps"]}
    assert {
        "submit_durable",
        "survives_restart",
        "moderation_queue",
        "reviewed",
        "applied_canonical",
        "exactly_once",
        "published_linkage",
        "distinct_states",
        "resolved_state",
        "receiver_no_fact_write",
    } <= steps


def test_the_close_revises_pair_landed(
    sig_database: dict[str, object], proof: dict[str, Any]
) -> None:
    """The corrected claim exists, revises the seeded target, and is asserted
    by the approving curator — the §16.6 append-only shape."""
    conn = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    try:
        row = conn.execute(
            "SELECT claim_id, value_num, revises_claim, correction_reason,"
            " asserted_by::text AS asserted_by FROM claim"
            " WHERE revises_claim = %s::uuid",
            (proof["target_claim_id"],),
        ).fetchone()
        assert row is not None, "no corrected claim revises the journey target"
        assert row["value_num"] == 225
        assert row["correction_reason"] == "acceptance_journey"
        # the ORIGINAL claim is closed (sys_period upper bound set)
        old = conn.execute(
            "SELECT upper(sys_period) AS closed FROM claim WHERE claim_id = %s::uuid",
            (proof["target_claim_id"],),
        ).fetchone()
        assert old is not None and old["closed"] is not None
    finally:
        conn.close()


def test_the_application_receipt_and_events_exist(
    sig_database: dict[str, object], proof: dict[str, Any]
) -> None:
    conn = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    try:
        app = conn.execute(
            "SELECT application_id::text AS application_id, operation_id,"
            " outcome, applied_by FROM intake.application"
            " WHERE report_id = %s::uuid",
            (proof["report_id"],),
        ).fetchone()
        assert app is not None and app["outcome"] == "correct"
        assert app["application_id"] == proof["application_id"]
        assert app["operation_id"].startswith("op-")
        events = {
            r["event"]
            for r in conn.execute(
                "SELECT event FROM intake.event WHERE report_id = %s::uuid",
                (proof["report_id"],),
            ).fetchall()
        }
        assert {
            "received",
            "disposition_proposed",
            "disposition_approved",
            "applied",
            "published",
        } <= events
        pub = conn.execute(
            "SELECT detail FROM intake.event WHERE report_id = %s::uuid AND event = 'published'",
            (proof["report_id"],),
        ).fetchone()
        assert pub["detail"]["publication_id"] == PUB
        assert pub["detail"]["correction_ref"]
    finally:
        conn.close()


def test_receiver_role_still_cannot_write_after_the_journey(
    sig_database: dict[str, object], proof: dict[str, Any]
) -> None:
    """The journey's own refusal probe ran; re-prove the role grant shape on
    a fresh receiver session so a grant regression is caught here too."""
    conn = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    try:
        conn.execute("SET ROLE sig_intake_receiver")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO intake.application(report_id, operation_id, approval_seq,"
                " proposal_seq, outcome, approved_by, applied_by, target_kind)"
                " VALUES (gen_random_uuid(), 'journey-pg-refused', 1, 1,"
                " 'correct', 'x', 'x', 'claim')"
            )
        conn.rollback()
    finally:
        conn.close()


def test_proof_round_trips_through_the_portfolio(proof: dict[str, Any], tmp_path) -> None:
    """The emitted proof JSON folds into the portfolio's journey-C checks —
    the same artifact shape `sig-ops journey-intake --out` writes."""
    out = tmp_path / "INTAKE_JOURNEY.json"
    out.write_text(json.dumps(proof, default=str))
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == jv.INTAKE_PROOF_SCHEMA
    assert all(s.get("ok") for s in loaded["steps"])
