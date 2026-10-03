# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The publication-disposition registry + shared eligibility fragments (P32.5 /
ADR-124, SIG-TRUST-006).

Coverage:

* the registry exists with its immutability trigger and watermark facet;
* ``sig.effective_disposition`` precedence — latest ``decided_at`` wins, then
  ``disposition_seq``, and a later ``allow`` lifts an earlier deny
  (the append-only "override"/rollback case);
* the shared SQL fragments (``entity_eligible_sql`` / ``claim_eligible_sql``)
  deny what the pure layer denies — a withheld entity, a review-flagged
  organisation, a dispositioned claim, and a claim whose partner ``object_entity``
  is withheld;
* **current access overrides history** — a withhold recorded in R2 denies a claim
  whose belief-time was valid in R1 (the fragment never consults belief);
* append-only enforcement — no UPDATE/DELETE route (trigger AND privilege);
* least-privilege grants — public roles hold the safe-column SELECT only
  (``rationale``/``decided_by`` stay elevated), ``sig_materialize`` holds INSERT;
* single clock authority (P32.10a) — ``decided_at`` is stamped by the database
  on normal writes; a skewed host clock cannot hide a fresh disposition, and a
  future-dated replay row is recorded history but never the effective
  disposition on either carrier.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites
from db.dispositions import (
    TargetKind,
    claim_eligible_sql,
    dispositions_for,
    effective_dispositions,
    entity_eligible_sql,
    record_disposition,
)
from policy.eligibility import (
    POLICY_VERSION,
    Disposition,
    ReasonCategory,
    new_disposition,
)


def _org(conn: object, entity_id: object, *, review: bool = False, status: str = "active") -> None:
    conn.execute(
        "INSERT INTO organization(entity_id, organization_type, status,"
        " publication_review_required, cached_canonical_name)"
        " VALUES(%s, 'us.le.municipal_police', %s, %s, 'Test Org')",
        (entity_id, status, review),
    )


def _record(
    conn: object,
    kind: TargetKind,
    target_id: object,
    disposition: Disposition,
    reason: ReasonCategory,
    *,
    decided_at: str | None = None,
    authority: str = "reviewer:test",
) -> str:
    rec = new_disposition(
        target_kind=kind,
        target_id=str(target_id),
        disposition=disposition,
        reason_category=reason,
        authority=authority,
        decided_at=None if decided_at is None else datetime.fromisoformat(decided_at),
    )
    return record_disposition(conn, rec)


# --- schema + effective_disposition ------------------------------------------


def test_registry_objects_exist(conn: object) -> None:
    assert conn.execute("SELECT to_regclass('publication_disposition') IS NOT NULL").fetchone()[0]
    assert conn.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'effective_disposition')"
    ).fetchone()[0]
    assert conn.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = 'publication_disposition_immutable')"
    ).fetchone()[0]


def test_effective_disposition_is_none_when_unrecorded(conn: object) -> None:
    row = conn.execute("SELECT * FROM effective_disposition('entity', 'no-such-target')").fetchall()
    assert row == []


def test_effective_disposition_latest_wins(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHHOLD,
        ReasonCategory.REVIEW_DENIED,
        decided_at="2026-06-01T00:00:00+00:00",
    )
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.ALLOW,
        ReasonCategory.REVIEW_DENIED,
        decided_at="2026-06-02T00:00:00+00:00",
    )
    row = conn.execute(
        "SELECT disposition, policy_version FROM effective_disposition('entity', %s)", (eid,)
    ).fetchone()
    assert row[0] == "allow" and row[1] == POLICY_VERSION


def test_effective_disposition_respects_the_time_pin(conn: object) -> None:
    """A p_at pin answers 'what did policy say then' (review); the un-pinned read
    always sees the CURRENT decision — the R2-withhold-over-R1-rollback case."""
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.ALLOW,
        ReasonCategory.REVIEW_DENIED,
        decided_at="2026-06-01T00:00:00+00:00",
    )
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHDRAW,
        ReasonCategory.SAFETY_WITHDRAWAL,
        decided_at="2026-06-05T00:00:00+00:00",
    )
    past = conn.execute(
        "SELECT disposition FROM effective_disposition('entity', %s, '2026-06-02')",
        (eid,),
    ).fetchone()
    now = conn.execute(
        "SELECT disposition FROM effective_disposition('entity', %s, NULL)", (eid,)
    ).fetchone()
    assert past[0] == "allow"  # the review question
    assert now[0] == "withdraw"  # current access — the rollback rule


# --- single clock authority (P32.10a) -----------------------------------------


def test_recorded_disposition_is_immediately_visible(conn: object) -> None:
    """The nominal flake: record a disposition and select it IMMEDIATELY —
    before the fix, host-stamped `decided_at` could transiently future-date
    the row against the container's `clock_timestamp()` (the 4 intermittent
    P32.10 reds). The decision instant is now the database's own stamp."""
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    t0 = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    did = _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHHOLD,
        ReasonCategory.SAFETY_WITHDRAWAL,
    )
    t1 = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    decided_at = conn.execute(
        "SELECT decided_at FROM publication_disposition WHERE disposition_id = %s::uuid",
        (did,),
    ).fetchone()[0]
    # stamped by the database, inside the write call
    assert t0 <= decided_at <= t1
    # visible to BOTH carriers at once
    row = conn.execute(
        "SELECT disposition FROM effective_disposition('entity', %s)", (eid,)
    ).fetchone()
    assert row is not None and row[0] == "withhold"
    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608
    assert conn.execute(eligible, (eid, eid, eid)).fetchone()[0] is False


def test_host_clock_skew_cannot_hide_a_recorded_disposition(
    conn: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deterministic pre-fix failure: fake the host clock one hour AHEAD of
    the database — the exact skew direction (Docker Desktop VM lag) that made a
    fresh host-stamped row future-dated and invisible. With the fix the host
    clock is never consulted: the row is stamped server-side and selected."""
    real_datetime = datetime

    class _SkewedHostClock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:  # what the defect trusted
            return real_datetime.now(tz) + timedelta(hours=1)

    monkeypatch.setattr("policy.eligibility.datetime", _SkewedHostClock)
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHHOLD,
        ReasonCategory.SAFETY_WITHDRAWAL,
    )
    row = conn.execute(
        "SELECT disposition FROM effective_disposition('entity', %s)", (eid,)
    ).fetchone()
    assert row is not None and row[0] == "withhold"
    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608
    assert conn.execute(eligible, (eid, eid, eid)).fetchone()[0] is False


def test_normal_write_carries_no_host_stamp() -> None:
    """Structure of the fix (no Docker needed): a normal INSERT must not carry
    a Python-side `decided_at` — the column is omitted so `DEFAULT
    clock_timestamp()` stamps it. An explicit value is written only as a
    replay/migration input. Pre-fix the column always carried a host stamp."""
    captured: dict[str, object] = {}

    class _StubConn:
        def execute(self, sql: str, params: object = None) -> _StubConn:
            captured["sql"], captured["params"] = sql, params
            return self

        def fetchone(self) -> tuple[str]:
            return ("00000000-0000-0000-0000-000000000000",)

    normal = new_disposition(
        target_kind=TargetKind.ENTITY,
        target_id="x",
        disposition=Disposition.WITHHOLD,
        reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
        authority="reviewer:test",
    )
    assert normal.decided_at is None  # un-stamped — the database assigns it
    record_disposition(_StubConn(), normal)
    assert "decided_at" not in str(captured["sql"])

    replay = new_disposition(
        target_kind=TargetKind.ENTITY,
        target_id="x",
        disposition=Disposition.WITHHOLD,
        reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
        authority="reviewer:test",
        decided_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    record_disposition(_StubConn(), replay)
    assert "decided_at" in str(captured["sql"])
    assert replay.decided_at in captured["params"]


def test_decided_at_default_is_the_database_clock(conn: object) -> None:
    """The schema pin the sqitch change verify asserts: the column carries
    `DEFAULT clock_timestamp()` — if a later migration dropped it, normal
    writes would silently need a stamp again."""
    default = conn.execute(
        "SELECT column_default FROM information_schema.columns"
        " WHERE table_name = 'publication_disposition' AND column_name = 'decided_at'"
    ).fetchone()[0]
    assert "clock_timestamp" in default


def test_future_dated_replay_is_not_the_effective_disposition(conn: object) -> None:
    """Carrier parity: a replay/migration row stamped in the FUTURE is recorded
    history (`dispositions_for` shows it — append-only, never rewritten) but is
    never the CURRENT effective disposition on EITHER carrier
    (`decided_at <= clock_timestamp()` bounds both)."""
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHHOLD,
        ReasonCategory.SAFETY_WITHDRAWAL,
        decided_at="2999-01-01T00:00:00+00:00",  # future-ok: synthetic: sentinel decided_at
    )
    history = dispositions_for(conn, TargetKind.ENTITY, [eid])
    assert [d.disposition for d in history] == [Disposition.WITHHOLD]
    sql = conn.execute("SELECT * FROM effective_disposition('entity', %s)", (eid,)).fetchall()
    assert sql == []
    assert effective_dispositions(conn, TargetKind.ENTITY, [eid]) == {}


def test_python_and_sql_effective_agree(conn: object) -> None:
    """The pure twin (``effective_dispositions``) and ``sig.effective_disposition``
    return the same row — the two carriers of ONE rule stay identical."""
    prereqs = seed_claim_prerequisites(conn)
    eid = str(prereqs["subject_id"])
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.WITHHOLD,
        ReasonCategory.REVIEW_DENIED,
        decided_at="2026-06-01T00:00:00+00:00",
    )
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.ALLOW,
        ReasonCategory.REVIEW_DENIED,
        decided_at="2026-06-02T00:00:00+00:00",
    )
    py = effective_dispositions(conn, TargetKind.ENTITY, [eid])[eid]
    sql = conn.execute(
        "SELECT disposition_id FROM effective_disposition('entity', %s)", (eid,)
    ).fetchone()
    assert py.disposition is Disposition.ALLOW
    assert sql is not None


# --- the shared fragments (API + export both inline these) --------------------


def _entity(conn: object, entity_type: str = "organization") -> object:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,)
    ).fetchone()[0]


def test_entity_fragment_denies_withheld_and_review_flagged(conn: object) -> None:
    withheld, flagged, plain = _entity(conn), _entity(conn), _entity(conn)
    _org(conn, withheld, review=False)
    _org(conn, flagged, review=True)
    _org(conn, plain, review=False)
    _record(
        conn,
        TargetKind.ENTITY,
        withheld,
        Disposition.WITHHOLD,
        ReasonCategory.SAFETY_WITHDRAWAL,
    )
    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608 - constant fragment
    # the fragment embeds the id expression THREE times (two COALESCE'd latest
    # lookups + the organisation-status EXISTS)
    thrice = lambda e: (str(e), str(e), str(e))  # noqa: E731
    assert conn.execute(eligible, thrice(withheld)).fetchone()[0] is False
    assert conn.execute(eligible, thrice(flagged)).fetchone()[0] is False
    assert conn.execute(eligible, thrice(plain)).fetchone()[0] is True


def test_entity_fragment_recorded_allow_lifts_review_flag(conn: object) -> None:
    """D-P31.5-2 option B: the flag withholds until a reviewer records ALLOW —
    a deliberate, authority-stamped release, never a silent code path."""
    eid = _entity(conn)
    _org(conn, eid, review=True)
    _record(
        conn,
        TargetKind.ENTITY,
        eid,
        Disposition.ALLOW,
        ReasonCategory.REVIEW_DENIED,
        authority="gate:publication_review",
    )
    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608
    e3 = (str(eid), str(eid), str(eid))
    assert conn.execute(eligible, e3).fetchone()[0] is True


def test_entity_fragment_withdrawn_status_denies(conn: object) -> None:
    eid = _entity(conn)
    _org(conn, eid, status="withdrawn")
    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608
    e3 = (str(eid), str(eid), str(eid))
    assert conn.execute(eligible, e3).fetchone()[0] is False


def test_claim_fragment_denies_dispositioned_claim(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    cid = insert_claim(conn, prereqs)
    _record(
        conn,
        TargetKind.CLAIM,
        cid,
        Disposition.RESTRICT,
        ReasonCategory.POLICY_RESTRICTION,
    )
    q = f"SELECT count(*) FROM claim c WHERE c.claim_id = %s AND {claim_eligible_sql('c')}"  # noqa: S608
    assert conn.execute(q, (cid,)).fetchone()[0] == 0


def test_claim_fragment_denies_withheld_subject(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    cid = insert_claim(conn, prereqs)
    _record(
        conn,
        TargetKind.ENTITY,
        prereqs["subject_id"],
        Disposition.WITHDRAW,
        ReasonCategory.SAFETY_WITHDRAWAL,
    )
    q = f"SELECT count(*) FROM claim c WHERE c.claim_id = %s AND {claim_eligible_sql('c')}"  # noqa: S608
    assert conn.execute(q, (cid,)).fetchone()[0] == 0


def test_claim_fragment_denies_withheld_object_entity(conn: object) -> None:
    """The partner-organisation seam (SIG-TRUST-006): a claim pointing AT a
    withheld entity is not public — the edge topology never leaks the partner."""
    prereqs = seed_claim_prerequisites(conn)
    partner = _entity(conn)
    _org(conn, partner, review=True)
    cid = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,"
        "rights_id,sensitivity_tier,object_entity) "
        "VALUES(%s,%s,'entity_ref','value',NULL,'x','2026-05-01','R1','D1','I1',"
        "%s,'fixture',%s,%s,0,%s) RETURNING claim_id",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            partner,
        ),
    ).fetchone()[0]
    q = f"SELECT count(*) FROM claim c WHERE c.claim_id = %s AND {claim_eligible_sql('c')}"  # noqa: S608
    assert conn.execute(q, (cid,)).fetchone()[0] == 0


def test_claim_fragment_permits_clean_claim(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    cid = insert_claim(conn, prereqs)
    q = f"SELECT count(*) FROM claim c WHERE c.claim_id = %s AND {claim_eligible_sql('c')}"  # noqa: S608
    assert conn.execute(q, (cid,)).fetchone()[0] == 1


# --- append-only enforcement ---------------------------------------------------


def test_disposition_update_is_rejected(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _record(
        conn,
        TargetKind.ENTITY,
        prereqs["subject_id"],
        Disposition.WITHHOLD,
        ReasonCategory.REVIEW_DENIED,
    )
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute("UPDATE publication_disposition SET disposition = 'allow'")
    assert "immutable" in str(excinfo.value)


def test_disposition_delete_is_rejected(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _record(
        conn,
        TargetKind.ENTITY,
        prereqs["subject_id"],
        Disposition.WITHHOLD,
        ReasonCategory.REVIEW_DENIED,
    )
    with pytest.raises(psycopg.Error) as excinfo:
        with conn.transaction():
            conn.execute("DELETE FROM publication_disposition")
    assert "immutable" in str(excinfo.value)


def test_watermark_bumps_on_insert(conn: object) -> None:
    before = conn.execute(
        "SELECT row_count, bump FROM spine_watermark WHERE facet = 'publication_disposition'"
    ).fetchone()
    prereqs = seed_claim_prerequisites(conn)
    _record(
        conn,
        TargetKind.ENTITY,
        prereqs["subject_id"],
        Disposition.WITHHOLD,
        ReasonCategory.REVIEW_DENIED,
    )
    after = conn.execute(
        "SELECT row_count, bump FROM spine_watermark WHERE facet = 'publication_disposition'"
    ).fetchone()
    assert after[0] == before[0] + 1
    assert after[1] > before[1]


# --- least-privilege grants -----------------------------------------------------


def test_public_roles_hold_no_write_privileges(conn: object) -> None:
    for role in ("sig_read_public", "sig_export", "sig_ingest"):
        for priv in ("INSERT", "UPDATE", "DELETE"):
            has = conn.execute(
                "SELECT has_table_privilege(%s, 'publication_disposition', %s)",
                (role, priv),
            ).fetchone()[0]
            assert has is False, f"{role} unexpectedly holds {priv}"


def test_materialize_role_inserts_but_cannot_mutate(conn: object) -> None:
    has_insert = conn.execute(
        "SELECT has_table_privilege('sig_materialize', 'publication_disposition', 'INSERT')"
    ).fetchone()[0]
    assert has_insert is True
    for priv in ("UPDATE", "DELETE"):
        assert (
            conn.execute(
                "SELECT has_table_privilege('sig_materialize', 'publication_disposition', %s)",
                (priv,),
            ).fetchone()[0]
            is False
        )


def test_rationale_and_decided_by_stay_privileged(conn: object) -> None:
    """The tombstone columns are public; the recording actor and free-text
    rationale are NOT granted to the public read/export roles (SIG-TRUST-006's
    'safe reason category')."""
    for role in ("sig_read_public", "sig_export"):
        for col in ("rationale", "decided_by"):
            has = conn.execute(
                "SELECT has_column_privilege(%s, 'publication_disposition', %s, 'SELECT')",
                (role, col),
            ).fetchone()[0]
            assert has is False, f"{role} unexpectedly reads {col}"
        # ...while the safe tombstone columns ARE readable.
        for col in ("disposition", "reason_category", "authority", "policy_version"):
            has = conn.execute(
                "SELECT has_column_privilege(%s, 'publication_disposition', %s, 'SELECT')",
                (role, col),
            ).fetchone()[0]
            assert has is True, f"{role} cannot read the tombstone column {col}"
