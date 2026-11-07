# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The disappeared_observed_at writer against a real PG18 (P37.5b).

SIG-INGEST-009/010 + SIG-EVID-013/014 (§17.6): a connector-observed
disappearance persists as append-only data — the artifact's two event columns
(the designed UPDATE surface, scoped by the ``disappearance_event_grant``
column grant) plus a deduped ``research_task`` — never a delete, and the
earliest observation is never erased (COALESCE).
"""

from __future__ import annotations

import psycopg
import pytest
from connectors.disappearance import note_disappearance
from tasks.disappearance_pg import (
    DISAPPEARANCE_TRIGGER,
    disappeared_artifacts,
    insert_task_row,
    persist_disappearance,
    persist_disappearances,
)


def _seed_artifact(conn: object) -> dict[str, object]:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) "
        "VALUES('Apache-2.0','yes','yes','2026-01-01') RETURNING rights_id"
    )
    rights_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
        "VALUES('portalx','Portal X','portal','R2','fixture',%s,'MIRROR','no_response','obey')",
        (rights_id,),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES('portalx','urn:sig:test:art:x','webpage','crawl','primary',%s,'captured') "
        "RETURNING artifact_id",
        (rights_id,),
    )
    return {"artifact_id": cur.fetchone()[0]}


_WHEN = "2026-09-15T00:00:00Z"


def test_disappearance_writer_lands_event_and_task(conn: object) -> None:
    seed = _seed_artifact(conn)
    d = note_disappearance(
        artifact_id=str(seed["artifact_id"]),
        observed_at="2026-09-15",
        failing_status="link_rotted",
    )
    write = persist_disappearance(conn, d)
    assert write.artifact_found and write.event_applied and not write.already_marked
    assert write.task_outcome == "written"
    row = conn.execute(
        "SELECT capture_status, disappeared_observed_at IS NOT NULL "
        "FROM evidence_artifact WHERE artifact_id = %s",
        (seed["artifact_id"],),
    ).fetchone()
    assert row == ("link_rotted", True)
    task = conn.execute(
        "SELECT task_type, status, trigger_kind FROM research_task WHERE trigger_ref = %s",
        (str(seed["artifact_id"]),),
    ).fetchone()
    assert task[0] == "source_disappeared" and task[1] == "generated"
    assert task[2] == DISAPPEARANCE_TRIGGER


def test_first_observation_wins_and_status_tracks_latest(conn: object) -> None:
    seed = _seed_artifact(conn)
    first = note_disappearance(
        artifact_id=str(seed["artifact_id"]),
        observed_at="2026-09-01",
        failing_status="unreachable",
    )
    second = note_disappearance(
        artifact_id=str(seed["artifact_id"]),
        observed_at="2026-10-01",
        failing_status="link_rotted",
    )
    persist_disappearance(conn, first)
    w2 = persist_disappearance(conn, second)
    assert w2.already_marked
    row = conn.execute(
        "SELECT capture_status, disappeared_observed_at::text "
        "FROM evidence_artifact WHERE artifact_id = %s",
        (seed["artifact_id"],),
    ).fetchone()
    assert row[0] == "link_rotted"
    assert row[1].startswith("2026-09-01")  # the earliest observation stands


def test_locator_resolution_and_unresolved_honesty(conn: object) -> None:
    _seed_artifact(conn)  # the artifact exists so the locator resolves
    by_locator = note_disappearance(
        artifact_id="urn:sig:test:art:x",
        observed_at="2026-09-15",
        failing_status="link_rotted",
    )
    assert persist_disappearance(conn, by_locator).artifact_found
    missing = note_disappearance(
        artifact_id="urn:sig:test:nope",
        observed_at="2026-09-15",
        failing_status="link_rotted",
    )
    w = persist_disappearance(conn, missing)
    assert not w.artifact_found and not w.event_applied
    assert w.task_outcome == "written"  # the task still lands, subjectless


def test_task_dedup_is_idempotent(conn: object) -> None:
    seed = _seed_artifact(conn)
    d = note_disappearance(
        artifact_id=str(seed["artifact_id"]),
        observed_at="2026-09-15",
        failing_status="link_rotted",
    )
    s1 = persist_disappearances(conn, [d])
    s2 = persist_disappearances(conn, [d])
    assert s1.tasks_written == 1
    assert s2.tasks_written == 0 and s2.tasks_existing == 1
    n = conn.execute(
        "SELECT count(*) FROM research_task WHERE task_type='source_disappeared'"
    ).fetchone()[0]
    assert n == 1


def test_disappeared_artifacts_is_the_queryable_read(conn: object) -> None:
    seed = _seed_artifact(conn)
    assert disappeared_artifacts(conn) == []
    persist_disappearance(
        conn,
        note_disappearance(
            artifact_id=str(seed["artifact_id"]),
            observed_at="2026-09-15",
            failing_status="link_rotted",
        ),
    )
    rows = disappeared_artifacts(conn)
    assert len(rows) == 1
    assert rows[0]["capture_status"] == "link_rotted"
    assert rows[0]["disappeared_observed_at"].startswith("2026-09-15")
    assert rows[0]["task_id"]


def test_sig_ingest_writes_event_columns_only(conn: object) -> None:
    """The column-scoped grant: event columns writable, nothing else — no DELETE."""
    seed = _seed_artifact(conn)
    conn.execute("SET ROLE sig_ingest")
    conn.execute(
        "UPDATE evidence_artifact SET capture_status='link_rotted',"
        " disappeared_observed_at='2026-09-15' WHERE artifact_id=%s",
        (seed["artifact_id"],),
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "UPDATE evidence_artifact SET stable_locator='moved' WHERE artifact_id=%s",
            (seed["artifact_id"],),
        )
    conn.rollback()
    conn.execute("SET ROLE sig_ingest")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM evidence_artifact WHERE artifact_id=%s", (seed["artifact_id"],))


def test_insert_task_row_refuses_no_closing_condition(conn: object) -> None:
    with pytest.raises(ValueError, match="closing_condition"):
        insert_task_row(conn, {"task_type": "x", "closing_condition": ""})
    with pytest.raises(ValueError, match="task_type"):
        insert_task_row(conn, {"task_type": "", "closing_condition": "c"})
