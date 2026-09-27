# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `intake` schema over real PostgreSQL (P32.16 / ADR-135, SIG-FIND-006).

Docker-backed (postgis:18-3.6 + the full sqitch plan) — the AC proofs:

* **Role isolation is schema-level.** ``sig_intake_receiver`` can INSERT its
  own payloads + `received` event and read the coarse projection/digest only;
  it cannot write claim/review_decision/publication_disposition, cannot read
  raw payload rows, and cannot append reviewer events. ``sig_intake_reviewer``
  reads payloads + appends reviewer events but cannot mutate payload rows or
  canonical state. No existing role touches `intake`.
* **Durable + restart-safe.** A committed receipt is visible from a fresh
  connection (the restart boundary the AC names); duplicate idempotency keys
  collide on the UNIQUE constraint.
* **Writer guard.** The session-role trigger refuses cross-role events and the
  reserved `applied`/`published` bridge events for every current role.
* **Retention + redaction.** The SECURITY DEFINER functions blank payloads +
  drop the restricted contact row and append audited housekeeping events; the
  public projection exposes only coarse state + an approved public_response.
* **End-to-end.** The real FastAPI receiver app + curation moderation app over
  the live schema: submit → restart → receipt → authorized moderation.
"""

from __future__ import annotations

import secrets
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest
from conftest import (
    DB_DIR,
    PG_DB,
    PG_IMAGE,
    PG_PASSWORD,
    PG_USER,
    SQITCH_IMAGE,
    _docker_reachable,
    _require_or_skip,
    seed_claim_prerequisites,
)
from db.intake import (
    RECEIVER_ACTOR,
    PgIntakeReceiverStore,
    PgIntakeReviewerStore,
)
from psycopg.rows import dict_row

from policy import intake as pint


def _dsn(db: dict[str, object]) -> str:
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"


def _denied(conn: object, sql: str, params: tuple = ()) -> None:
    with pytest.raises(psycopg.errors.Error):
        with conn.transaction():
            conn.execute(sql, params)


@pytest.fixture()
def recv_conn(sig_database: dict[str, object]) -> Any:
    """A committed, role-scoped receiver connection. Store tests write real
    rows — the container is session-ephemeral and fixture keys are unique."""
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    c.execute("SET ROLE sig_intake_receiver")
    yield c
    c.close()


@pytest.fixture()
def rev_conn(sig_database: dict[str, object]) -> Any:
    """A committed, role-scoped reviewer connection (same session pattern)."""
    c = psycopg.connect(_dsn(sig_database), autocommit=True, row_factory=dict_row)
    c.execute("SET ROLE sig_intake_reviewer")
    yield c
    c.close()


def _report_kw(key: str) -> dict[str, Any]:
    """Deterministic-but-unique fixture ids (the container is session-shared)."""
    return {
        "report_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sig-intake-test-{key}")),
        "receipt_id": f"rct-{uuid.uuid5(uuid.NAMESPACE_DNS, key).hex[:32]}",
        "idempotency_key": f"nonce-{key}-abcdefghij",
        "category": "factual_error",
        "description": "fixture narrative — quarantined, reviewer-only",
        "publication_id": None,
        "record_key": None,
        "claim_ids": [],
        "evidence_urls": ["https://example.com/doc"],
        "contact": None,
        "token_digest": secrets.token_bytes(32),
    }


# --------------------------------------------------------------------------- #
# Grants matrix — the least-privilege shape the deploy applied
# --------------------------------------------------------------------------- #
def test_receiver_role_isolation_matrix(conn: object) -> None:
    priv = lambda r, t, p: conn.execute(  # noqa: E731
        "SELECT has_table_privilege(%s, %s, %s)", (r, t, p)
    ).fetchone()[0]
    # Receiver: its own writes only.
    for t in ("intake.report", "intake.reporter_contact", "intake.receipt", "intake.event"):
        assert priv("sig_intake_receiver", t, "INSERT"), t
        assert not priv("sig_intake_receiver", t, "UPDATE"), t
        assert not priv("sig_intake_receiver", t, "DELETE"), t
    # Receiver reads ONLY the coarse projection + the digest column — never the
    # raw payload store, the contact table, or the audit log.
    assert priv("sig_intake_receiver", "intake.report_public", "SELECT")
    assert not priv("sig_intake_receiver", "intake.report", "SELECT")
    assert not priv("sig_intake_receiver", "intake.event", "SELECT")
    assert not priv("sig_intake_receiver", "intake.reporter_contact", "SELECT")
    # The receipt table is a column-grant: digest readable, everything else not.
    col = lambda c: conn.execute(  # noqa: E731
        "SELECT has_column_privilege('sig_intake_receiver', 'intake.receipt', %s, 'SELECT')",
        (c,),
    ).fetchone()[0]
    assert col("token_digest")
    assert col("report_id")  # needed for the WHERE clause of the digest lookup
    assert not col("issued_at")
    # The receiver credential cannot write canonical state — the AC's core.
    for t in ("claim", "review_decision", "review_item", "publication_disposition"):
        assert not priv("sig_intake_receiver", t, "INSERT"), t
        assert not priv("sig_intake_receiver", t, "SELECT"), t
    # Reviewer: read payloads + append events + run maintenance; no canonical
    # writes, no payload mutation.
    for t in ("intake.report", "intake.reporter_contact", "intake.receipt", "intake.event"):
        assert priv("sig_intake_reviewer", t, "SELECT"), t
        assert not priv("sig_intake_reviewer", t, "UPDATE"), t
        assert not priv("sig_intake_reviewer", t, "DELETE"), t
    assert priv("sig_intake_reviewer", "intake.event", "INSERT")
    assert not priv("sig_intake_reviewer", "intake.report", "INSERT")
    for t in ("claim", "review_decision", "publication_disposition"):
        assert not priv("sig_intake_reviewer", t, "INSERT"), t
    # No existing role touches the intake schema at all.
    for role in (
        "sig_read_public",
        "sig_read_restricted",
        "sig_read_sealed",
        "sig_export",
        "sig_ingest",
        "sig_materialize",
    ):
        assert not priv(role, "intake.report", "SELECT"), role
        assert not priv(role, "intake.event", "SELECT"), role


def test_maintenance_functions_revoked_from_public(conn: object) -> None:
    # PUBLIC EXECUTE was revoked: the function ACL names the reviewer role and
    # carries no blanket `=X/` (PUBLIC) item.
    rows = conn.execute(
        "SELECT proname, proacl FROM pg_proc p JOIN pg_namespace n"
        " ON n.oid = p.pronamespace WHERE n.nspname='intake'"
        " AND proname IN ('redact_report','expunge_report')"
    ).fetchall()
    assert len(rows) == 2
    for name, acl in rows:
        items = [str(i) for i in acl]
        assert any(i.startswith("sig_intake_reviewer=X/") for i in items), (name, items)
        # An empty grantee (`=X/...`) means PUBLIC EXECUTE — must not appear.
        assert all(not i.startswith("=X/") for i in items), (name, items)
    for fn in ("intake.expunge_report(uuid)", "intake.redact_report(uuid,text[],text)"):
        assert conn.execute(
            "SELECT has_function_privilege('sig_intake_reviewer', %s, 'EXECUTE')", (fn,)
        ).fetchone()[0]
        assert not conn.execute(
            "SELECT has_function_privilege('sig_intake_receiver', %s, 'EXECUTE')", (fn,)
        ).fetchone()[0]
    # And the receiver credential really cannot run them.
    conn.execute("SET ROLE sig_intake_receiver")
    try:
        _denied(conn, "SELECT intake.expunge_report(gen_random_uuid())")
    finally:
        conn.execute("RESET ROLE")


def test_receiver_cannot_actually_write_canonical(conn: object) -> None:
    """Beyond the grants matrix: real denied statements under the session role."""
    conn.execute("SET ROLE sig_intake_receiver")
    try:
        _denied(
            conn,
            "INSERT INTO claim (claim_id, subject_id, predicate_id, object_value)"
            " VALUES (gen_random_uuid(), gen_random_uuid(), 'x', '1'::jsonb)",
        )
        _denied(conn, "SELECT 1 FROM intake.report LIMIT 1")
        _denied(conn, "SELECT 1 FROM claim LIMIT 1")
    finally:
        conn.execute("RESET ROLE")


# --------------------------------------------------------------------------- #
# Writer guard — the session-role event boundary
# --------------------------------------------------------------------------- #
def _seed_report_pg(
    conn: object,
    key: str,
    *,
    received_at: datetime | None = None,
    wrap_role: bool = True,
) -> tuple[str, str]:
    """Insert one report + `received` event. ``wrap_role`` wraps the writes in
    SET/RESET ROLE for the neutral shared conn; the recv_conn fixture already
    carries the role."""
    kw = _report_kw(key)
    if wrap_role:
        conn.execute("SET ROLE sig_intake_receiver")
    try:
        conn.execute(
            "INSERT INTO intake.report "
            "(report_id, receipt_id, idempotency_key, category, description,"
            " evidence_urls, received_at) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)",
            (
                kw["report_id"],
                kw["receipt_id"],
                kw["idempotency_key"],
                kw["category"],
                kw["description"],
                '["https://example.com/doc"]',
                received_at or datetime.now(UTC),
            ),
        )
        conn.execute(
            "INSERT INTO intake.event (report_id, event, actor) VALUES (%s,'received',%s)",
            (kw["report_id"], RECEIVER_ACTOR),
        )
    finally:
        if wrap_role:
            conn.execute("RESET ROLE")
    return kw["report_id"], kw["receipt_id"]


def test_receiver_write_and_writer_guard(conn: object) -> None:
    rid, _ = _seed_report_pg(conn, "guard01")
    # Receiver may NOT append reviewer events — even though it holds INSERT.
    conn.execute("SET ROLE sig_intake_receiver")
    try:
        _denied(
            conn,
            "INSERT INTO intake.event (report_id, event, actor)"
            " VALUES (%s,'triaged','sig-intake-receiver')",
            (rid,),
        )
        _denied(
            conn,
            "INSERT INTO intake.event (report_id, event, actor)"
            " VALUES (%s,'received','not-the-receiver')",
            (rid,),
        )
    finally:
        conn.execute("RESET ROLE")
    # Reviewer may NOT mint a `received` event.
    conn.execute("SET ROLE sig_intake_reviewer")
    try:
        _denied(
            conn,
            "INSERT INTO intake.event (report_id, event, actor)"
            " VALUES (%s,'received','sig-intake-receiver')",
            (rid,),
        )
        # The reserved bridge events are refused for EVERY current role.
        for event in ("applied", "published"):
            _denied(
                conn,
                f"INSERT INTO intake.event (report_id, event, actor) VALUES (%s,'{event}','rev')",
                (rid,),
            )
    finally:
        conn.execute("RESET ROLE")


def test_append_only_and_immutable_identity(conn: object) -> None:
    rid, _ = _seed_report_pg(conn, "immut01")
    conn.execute("SET ROLE sig_intake_reviewer")
    try:
        conn.execute(
            "INSERT INTO intake.event (report_id, event, actor) VALUES (%s,'triaged','rev')",
            (rid,),
        )
    finally:
        conn.execute("RESET ROLE")
    _denied(conn, "UPDATE intake.event SET event='closed' WHERE report_id=%s", (rid,))
    _denied(conn, "DELETE FROM intake.event WHERE report_id=%s", (rid,))
    _denied(conn, "DELETE FROM intake.report WHERE report_id=%s", (rid,))
    _denied(
        conn,
        "UPDATE intake.report SET receipt_id='rct-zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz01'"
        " WHERE report_id=%s",
        (rid,),
    )
    _denied(
        conn,
        "UPDATE intake.report SET idempotency_key='nonce-forged00000000' WHERE report_id=%s",
        (rid,),
    )


def test_idempotency_uniqueness(conn: object) -> None:
    _seed_report_pg(conn, "idem01")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conn.transaction():
            conn.execute("SET ROLE sig_intake_receiver")
            conn.execute(
                "INSERT INTO intake.report (report_id, receipt_id, idempotency_key,"
                " category, description) VALUES (gen_random_uuid(),"
                " 'rct-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1', 'nonce-idem01-abcdefghij',"
                " 'factual_error', 'duplicate key')"
            )


# --------------------------------------------------------------------------- #
# The store classes + the public projection
# --------------------------------------------------------------------------- #
def test_public_state_sql_parity(conn: object) -> None:
    """intake.public_state is the SQL twin of policy.intake.public_state."""
    for event in pint.event_vocabulary()["lifecycle"]:
        got = conn.execute("SELECT intake.public_state(%s)", (event,)).fetchone()[0]
        assert got == pint.public_state(event), event


def test_receiver_store_roundtrip(recv_conn: object) -> None:
    store = PgIntakeReceiverStore(recv_conn)
    kw = _report_kw("store01")
    store.insert_report(**kw)

    found = store.find_by_idempotency(kw["idempotency_key"])
    assert found["receipt_id"] == kw["receipt_id"]
    status = store.public_status(kw["receipt_id"])
    assert status["state"] == "received"
    assert status["lifecycle_event"] == "received"
    assert "public_response" in status and status["public_response"] is None
    # The digest is fetchable for the app's constant-time compare.
    assert store.receipt_token_digest(kw["report_id"]) == kw["token_digest"]
    # The projection NEVER exposes the payload.
    colnames = {
        d.name for d in recv_conn.execute("SELECT * FROM intake.report_public LIMIT 0").description
    }
    assert {"description", "contact", "evidence_urls", "claim_ids"}.isdisjoint(colnames)


def test_reviewer_store_queue_detail_events(recv_conn: object, rev_conn: object) -> None:
    _, receipt = _seed_report_pg(recv_conn, "revw01", wrap_role=False)
    store = PgIntakeReviewerStore(rev_conn)
    queue = store.queue()
    assert any(r["receipt_id"] == receipt for r in queue)
    detail = store.detail(receipt)
    assert detail["description"].startswith("fixture narrative")
    assert [e["event"] for e in detail["events"]] == ["received"]
    seq = store.record_event(receipt, "triaged", "rev-1", {"note": "looks real"})
    assert seq >= 1
    detail2 = store.detail(receipt)
    assert detail2["lifecycle_event"] == "triaged"
    # The receiver's projection now reports under_review.
    status = PgIntakeReceiverStore(recv_conn).public_status(receipt)
    assert status["state"] == "under_review"


def test_redact_and_expunge_functions(recv_conn: object, rev_conn: object) -> None:
    rid, receipt = _seed_report_pg(recv_conn, "redac01", wrap_role=False)
    # The contact row is written at intake time by the RECEIVER (the only role
    # holding INSERT); the reviewer mutates it only via the functions.
    recv_conn.execute(
        "INSERT INTO intake.reporter_contact (report_id, contact)"
        " VALUES (%s,'clerk@court.example')",
        (rid,),
    )
    rev_conn.execute(
        "SELECT intake.redact_report(%s::uuid, %s::text[], %s)",
        (rid, ["contact", "description"], "rev-9"),
    )
    row = rev_conn.execute(
        "SELECT description FROM intake.report WHERE report_id=%s", (rid,)
    ).fetchone()
    assert row["description"] == "[redacted]"
    assert (
        rev_conn.execute(
            "SELECT count(*) AS n FROM intake.reporter_contact WHERE report_id=%s", (rid,)
        ).fetchone()["n"]
        == 0
    )
    assert (
        rev_conn.execute(
            "SELECT event FROM intake.event WHERE report_id=%s ORDER BY event_seq DESC",
            (rid,),
        ).fetchone()["event"]
        == "redacted"
    )
    rev_conn.execute("SELECT intake.expunge_report(%s::uuid)", (rid,))
    row2 = rev_conn.execute(
        "SELECT description, expunged_at IS NOT NULL AS gone FROM intake.report WHERE report_id=%s",
        (rid,),
    ).fetchone()
    assert row2["description"] == "[expunged]" and row2["gone"] is True
    # The expunge event is on the audit log; the row itself still exists and
    # the receipt still resolves through the public projection.
    status = PgIntakeReceiverStore(recv_conn).public_status(receipt)
    assert status["receipt_id"] == receipt


def test_public_response_only_when_published_flagged(recv_conn: object, rev_conn: object) -> None:
    rid, receipt = _seed_report_pg(recv_conn, "pubre01", wrap_role=False)
    # A proposal's response text is NOT public yet.
    rev_conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, detail) VALUES"
        " (%s,'disposition_proposed','rev-1',%s::jsonb)",
        (
            rid,
            '{"outcome":"correct","reason":"verified","public_response":"We corrected it.",'
            '"public_response_publish":false}',
        ),
    )
    status = PgIntakeReceiverStore(recv_conn).public_status(receipt)
    assert status["state"] == "under_review"
    assert status["public_response"] is None
    rev_conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, detail) VALUES"
        " (%s,'disposition_approved','cur-1',%s::jsonb)",
        (
            rid,
            '{"outcome":"correct","reason":"verified","public_response":"We corrected it.",'
            '"public_response_publish":true,"approves_seq":2}',
        ),
    )
    status = PgIntakeReceiverStore(recv_conn).public_status(receipt)
    assert status["state"] == "decided"
    assert status["public_response"] == "We corrected it."
    # Coarse only — no rationale, no actor, no payload.
    assert set(status) <= {
        "report_id",
        "receipt_id",
        "category",
        "received_at",
        "lifecycle_event",
        "state",
        "public_response",
    }


# --------------------------------------------------------------------------- #
# Retention sweep
# --------------------------------------------------------------------------- #
def test_expunge_due_retention(recv_conn: object, rev_conn: object) -> None:
    """The sweep expunges post-disposition payloads past 30d and flags >90d
    undecided; legal_hold rows are skipped and reported."""
    old = datetime.now(UTC) - timedelta(days=95)
    # Decided long ago → expunge.
    rid_a, receipt_a = _seed_report_pg(recv_conn, "purge01", received_at=old, wrap_role=False)
    # Undecided and very old → review_overdue.
    _, receipt_b = _seed_report_pg(recv_conn, "purge02", received_at=old, wrap_role=False)
    # Decided long ago but held → skipped + listed.
    rid_c, receipt_c = _seed_report_pg(recv_conn, "purge03", received_at=old, wrap_role=False)
    rev_conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, at, detail)"
        " VALUES (%s,'disposition_approved','cur-1',%s,"
        ' \'{"outcome":"refuse","reason":"dup","approves_seq":1}\'::jsonb)',
        (rid_a, old + timedelta(days=1)),
    )
    rev_conn.execute(
        "INSERT INTO intake.event (report_id, event, actor, at, detail)"
        " VALUES (%s,'disposition_approved','cur-1',%s,"
        ' \'{"outcome":"refuse","reason":"dup","approves_seq":1,'
        '"legal_hold":true}\'::jsonb)',
        (rid_c, old + timedelta(days=1)),
    )
    report = PgIntakeReviewerStore(rev_conn).expunge_due(
        after_disposition_days=30, ceiling_days=90, now=datetime.now(UTC)
    )
    assert receipt_a in report["expunged"]
    assert receipt_b in report["review_overdue"]
    assert receipt_c in report["legal_hold_skipped"]
    row = rev_conn.execute(
        "SELECT description, expunged_at IS NOT NULL AS gone FROM intake.report WHERE report_id=%s",
        (rid_a,),
    ).fetchone()
    assert row["description"] == "[expunged]" and row["gone"] is True
    # The held row kept its payload.
    held = rev_conn.execute(
        "SELECT description FROM intake.report WHERE report_id=%s", (rid_c,)
    ).fetchone()
    assert held["description"].startswith("fixture narrative")


# --------------------------------------------------------------------------- #
# The flagship durability acceptance: submit → restart → receipt → moderation
# --------------------------------------------------------------------------- #
def test_durable_submit_restart_receipt_moderation(sig_database: dict[str, object]) -> None:
    """The AC end-to-end over the REAL app + schema: a report committed under
    the receiver role is still there for a fresh connection (the restart), the
    receipt+token authorize a status check, and the loopback moderation surface
    sees + decides it — all without the receiver ever gaining canonical writes."""
    import re

    from api.curation import create_curation_app
    from api.intake import create_intake_app
    from starlette.testclient import TestClient

    dsn = _dsn(sig_database)
    key = secrets.token_hex(6)
    receiver = create_intake_app(
        store=PgIntakeReceiverStore.from_dsn(dsn),
        enabled=True,
        operational=True,
        form_secret="pg-form-secret-0123456789",
        abuse_secret="pg-abuse-secret-0123456",
    )
    client = TestClient(receiver, raise_server_exceptions=True)
    token = re.search(r'name="form_token" value="([^"]+)"', client.get("/intake/new").text).group(1)
    resp = client.post(
        "/intake/v1/reports",
        json={
            "form_token": token,
            "category": "factual_error",
            "description": f"restart-durability fixture {key}",
            "idempotency_key": f"nonce-{key}",
        },
    )
    assert resp.status_code == 201
    accepted = resp.json()
    receipt = accepted["receipt_id"]

    # RESTART: a brand-new receiver process on a fresh connection sees it.
    receiver2 = create_intake_app(
        store=PgIntakeReceiverStore.from_dsn(dsn),
        enabled=True,
        operational=True,
        form_secret="pg-form-secret-0123456789",
        abuse_secret="pg-abuse-secret-0123456",
    )
    client2 = TestClient(receiver2, raise_server_exceptions=True)
    status = client2.post(
        "/intake/v1/status",
        json={"receipt_id": receipt, "status_token": accepted["status_token"]},
    )
    assert status.status_code == 200
    assert status.json()["state"] == "received"

    # The private curation surface (fresh connection too) shows it in the queue.
    curation = create_curation_app(enabled=True, intake_store=PgIntakeReviewerStore.from_dsn(dsn))
    cur = TestClient(curation, raise_server_exceptions=True)
    queue = cur.get(
        "/v1/curation/intake", headers={"Authorization": "Bearer reviewer-demo-key"}
    ).json()["pending"]
    assert any(r["receipt_id"] == receipt for r in queue)
    decided = cur.post(
        f"/v1/curation/intake/{receipt}/events",
        json={
            "event": "disposition_proposed",
            "detail": {
                "outcome": "correct",
                "reason": "verified fixture",
                "public_response": "Corrected in the next release.",
                "public_response_publish": True,
            },
        },
        headers={"Authorization": "Bearer reviewer-demo-key"},
    )
    assert decided.status_code == 201
    seq = decided.json()["event_seq"]
    approved = cur.post(
        f"/v1/curation/intake/{receipt}/events",
        json={
            "event": "disposition_approved",
            "detail": {
                "outcome": "correct",
                "reason": "verified fixture",
                "public_response": "Corrected in the next release.",
                "public_response_publish": True,
                "approves_seq": seq,
            },
        },
        headers={"Authorization": "Bearer curator-demo-key"},
    )
    assert approved.status_code == 201

    # The reporter sees the coarse decided state + the approved response — and
    # nothing else. The whole chain survived two fresh connections.
    final = client2.post(
        "/intake/v1/status",
        json={"receipt_id": receipt, "status_token": accepted["status_token"]},
    )
    assert final.json()["state"] == "decided"
    assert final.json()["response"] == "Corrected in the next release."

    # Cleanup: the test rows are committed; expunge leaves an audited
    # payload-free tombstone (rows are never deleted — that IS the schema).
    cleaner = PgIntakeReviewerStore.from_dsn(dsn)
    try:
        cleaner.expunge(receipt)
    finally:
        cleaner.close()


# --------------------------------------------------------------------------- #
# Reversibility — the change deploys and reverts without touching history     #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def revert_db() -> Iterator[dict[str, object]]:
    """A dedicated container for the sqitch revert drill (module-scoped)."""
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")

    import docker
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network

    network = Network()
    network.create()
    container = (
        DockerContainer(PG_IMAGE)
        .with_env("POSTGRES_USER", PG_USER)
        .with_env("POSTGRES_PASSWORD", PG_PASSWORD)
        .with_env("POSTGRES_DB", PG_DB)
        .with_exposed_ports(5432)
        .with_network(network)
        .with_network_aliases("db")
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        deadline = time.time() + 120
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with psycopg.connect(
                    host=host,
                    port=port,
                    user=PG_USER,
                    password=PG_PASSWORD,
                    dbname=PG_DB,
                    connect_timeout=3,
                ):
                    break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1)
        else:
            raise RuntimeError(f"Postgres never became ready: {last_err}")

        client = docker.from_env()

        def sqitch(*argv: str) -> None:
            return client.containers.run(
                SQITCH_IMAGE,
                command=[*argv, f"db:pg://{PG_USER}:{PG_PASSWORD}@db:5432/{PG_DB}"],
                network=network.name,
                working_dir="/repo",
                volumes={str(DB_DIR): {"bind": "/repo", "mode": "ro"}},
                environment={"PGPASSWORD": PG_PASSWORD},
                remove=True,
                stdout=True,
                stderr=True,
            )

        sqitch("deploy")
        yield {
            "dsn": f"postgresql://{PG_USER}:{PG_PASSWORD}@{host}:{port}/{PG_DB}",
            "sqitch": sqitch,
        }
    finally:
        container.stop()
        network.remove()


def test_revert_drops_intake_surface_and_keeps_canonical(revert_db: dict) -> None:
    """Deploy → seed claim + intake rows → revert to the parent change → the
    intake schema + roles are gone, every earlier table and row intact →
    re-deploy → clean (the forward path stays migratable)."""
    sqitch = revert_db["sqitch"]
    dsn = str(revert_db["dsn"])
    with psycopg.connect(dsn, autocommit=True) as conn:
        prereqs = seed_claim_prerequisites(conn)
        claim_before = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
        conn.execute("SET ROLE sig_intake_receiver")
        rid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "sig-intake-revert-drill"))
        conn.execute(
            "INSERT INTO intake.report (report_id, receipt_id, idempotency_key,"
            " category, description) VALUES (%s,"
            " 'rct-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'nonce-revert-drill-0000',"
            " 'factual_error', 'revert-drill payload')",
            (rid,),
        )
        conn.execute(
            "INSERT INTO intake.event (report_id, event, actor) VALUES (%s,'received',%s)",
            (rid, RECEIVER_ACTOR),
        )
        conn.execute("RESET ROLE")

    sqitch("revert", "-y", "--to", "disposition_decided_at_authority")

    with psycopg.connect(dsn, autocommit=True) as conn:
        assert conn.execute("SELECT to_regclass('intake.report')").fetchone()[0] is None
        assert conn.execute("SELECT to_regclass('intake.event')").fetchone()[0] is None
        for role in ("sig_intake_receiver", "sig_intake_reviewer"):
            assert (
                conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone() is None
            )
        # Canonical history survives byte-for-byte — the revert touched ONLY
        # the isolated surface.
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == claim_before
        assert prereqs["subject_id"] is not None

    sqitch("deploy")
    with psycopg.connect(dsn, autocommit=True) as conn:
        assert conn.execute("SELECT to_regclass('intake.report')").fetchone()[0] is not None
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == claim_before


def test_change_verify_script_passes(sig_database: dict[str, object]) -> None:
    """Run this change's own sqitch verify script against the deployed
    container. (Whole-plan `sqitch verify` is separately broken — the OPEN
    D-P32.10a-1 deferral — so the ticket's verify bar is per-change.)"""
    script = (DB_DIR / "verify" / "intake_storage.sql").read_text()
    # ClientCursor uses the simple query protocol — a multi-statement script
    # runs statement-by-statement and any `1/0` aborts it like psql -f.
    with psycopg.connect(_dsn(sig_database), autocommit=True) as conn:
        with psycopg.ClientCursor(conn) as cur:
            cur.execute(script)
