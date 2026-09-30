# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of the P31.3 identity guard and batched sink (ADR-110).

Closes D-P30.4-3 (the entity-creation race) and D-P30.1-1 (batched writes):

* Two writers that claim the same new ``(scheme, value)`` concurrently end with
  exactly ONE entity. The second writer blocks on the first one's uncommitted key,
  then reuses its entity. That holds for the guard primitive with a forced
  interleaving, and for two whole sinks racing over the same new subjects.
* An identifier an unguarded (pre-P31.3) writer left behind is adopted, never
  duplicated. The key is immutable.
* The batched write lands byte-for-byte the rows the row-at-a-time path did (the
  float -> numeric cast included), counts duplicates within a chunk, and uses a
  bounded number of round trips per chunk.
* The three extension points work: the duplicate hook (P31.7), the object seam
  (P31.5) and the per-call commit boundary (P31.4).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

_SPINE_TABLES = (
    "ingest_run_completion",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identity_key",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _claims(subjects: list[str], *, tag: str = "g") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in subjects:
        for pred, val in (("sig.test.guard_lat", 35.1234567), ("sig.test.guard_name", f"n-{s}")):
            out.append(
                {
                    "subject_id": s,
                    "predicate_id": pred,
                    "value": val,
                    "source_id": f"guard_src_{tag}",
                    "license": "CC0-1.0",
                }
            )
    return out


def _entities_per_subject(conn: psycopg.Connection[Any], prefix: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT value, count(DISTINCT entity_id) FROM entity_identifier "
        "WHERE scheme = 'sig.connector.subject' AND value LIKE %s GROUP BY value",
        (prefix + "%",),
    ).fetchall()
    return {str(r[0]): int(r[1]) for r in rows}


# --- the guard primitive --------------------------------------------------------


def test_a_concurrent_second_writer_blocks_then_reuses_the_first_entity(clean_dsn: str) -> None:
    """Forced interleaving: B claims the key A holds uncommitted; B waits, then reuses."""
    from db.identity_guard import SUBJECT_SCHEME, resolve_identities

    result: dict[str, Any] = {}
    with psycopg.connect(clean_dsn) as a, psycopg.connect(clean_dsn) as b:
        got_a = resolve_identities(a, SUBJECT_SCHEME, ["race:1"], entity_type="deployment")
        assert got_a.minted == {"race:1"}

        def writer_b() -> None:
            result["b"] = resolve_identities(
                b, SUBJECT_SCHEME, ["race:1"], entity_type="deployment"
            )
            b.commit()

        thread = threading.Thread(target=writer_b)
        thread.start()
        time.sleep(1.0)
        assert thread.is_alive(), "B must block on A's uncommitted key"
        a.commit()
        thread.join(timeout=30)
        assert not thread.is_alive()

    got_b = result["b"]
    assert got_b.minted == frozenset(), "the losing writer mints nothing"
    assert got_b.entity_by_value == got_a.entity_by_value
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _entities_per_subject(conn, "race:") == {"race:1": 1}
        assert conn.execute("SELECT count(*) FROM entity").fetchone()[0] == 1  # no orphan


def test_a_rolled_back_first_writer_leaves_the_key_to_the_second(clean_dsn: str) -> None:
    from db.identity_guard import SUBJECT_SCHEME, resolve_identities

    result: dict[str, Any] = {}
    with psycopg.connect(clean_dsn) as a, psycopg.connect(clean_dsn) as b:
        resolve_identities(a, SUBJECT_SCHEME, ["race:2"], entity_type="deployment")

        def writer_b() -> None:
            result["b"] = resolve_identities(
                b, SUBJECT_SCHEME, ["race:2"], entity_type="deployment"
            )
            b.commit()

        thread = threading.Thread(target=writer_b)
        thread.start()
        time.sleep(1.0)
        a.rollback()
        thread.join(timeout=30)

    assert result["b"].minted == {"race:2"}
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _entities_per_subject(conn, "race:") == {"race:2": 1}
        assert conn.execute("SELECT count(*) FROM entity").fetchone()[0] == 1


def test_two_concurrent_sinks_on_the_same_new_subjects_create_one_entity_each(
    clean_dsn: str,
) -> None:
    """The acceptance criterion: two whole sinks racing over the same new subjects."""
    from db.claim_sink import PgClaimSink

    subjects = [f"sinkrace:{i}" for i in range(300)]
    barrier = threading.Barrier(2)
    reports: dict[str, Any] = {}
    errors: list[BaseException] = []

    def run(name: str) -> None:
        try:
            with psycopg.connect(clean_dsn, autocommit=True) as conn:
                sink = PgClaimSink(conn, connector_name=f"race_{name}", commit_chunk_size=150)
                barrier.wait()
                sink.assert_claims(_claims(subjects, tag="race"))
                reports[name] = sink.report
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        per_subject = _entities_per_subject(conn, "sinkrace:")
        assert len(per_subject) == 300
        assert set(per_subject.values()) == {1}, "a subject resolved to two entities"
        assert conn.execute("SELECT count(*) FROM entity").fetchone()[0] == 300
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 600
    # Between them the two sinks minted every entity exactly once and landed every
    # claim exactly once; which sink won which subject is up to the scheduler.
    assert reports["a"].entities + reports["b"].entities == 300
    assert reports["a"].inserted + reports["b"].inserted == 600
    assert reports["a"].inserted + reports["a"].duplicates == 600
    assert reports["b"].inserted + reports["b"].duplicates == 600


def test_an_unguarded_legacy_identifier_is_adopted_not_duplicated(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # What a pre-P31.3 writer left behind: an entity + identifier, no key.
        legacy = conn.execute(
            "INSERT INTO entity(entity_type) VALUES ('deployment') RETURNING entity_id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO entity_identifier(entity_id, scheme, value) "
            "VALUES (%s, 'sig.connector.subject', 'legacy:1')",
            (legacy,),
        )
        sink = PgClaimSink(conn, connector_name="legacy")
        sink.assert_claims(_claims(["legacy:1", "legacy:2"]))
        assert sink.report.entities == 1  # only legacy:2 was minted
        key = conn.execute(
            "SELECT entity_id, backfilled FROM entity_identity_key WHERE value = 'legacy:1'"
        ).fetchone()
        assert key == (legacy, False)
        assert _entities_per_subject(conn, "legacy:") == {"legacy:1": 1, "legacy:2": 1}
        subjects = {r[0] for r in conn.execute("SELECT DISTINCT subject_id FROM claim").fetchall()}
        assert legacy in subjects


def test_keys_are_immutable(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        PgClaimSink(conn, connector_name="imm").assert_claims(_claims(["imm:1"]))
        for stmt in (
            "UPDATE entity_identity_key SET value = 'x'",
            "DELETE FROM entity_identity_key",
        ):
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                conn.execute(stmt)
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "INSERT INTO entity_identity_key(scheme, value, entity_id) "
                "SELECT scheme, value, entity_id FROM entity_identity_key"
            )


# --- batched writes -------------------------------------------------------------


def test_batched_rows_match_the_row_at_a_time_values(clean_dsn: str) -> None:
    """Every value shape lands in the same columns the pre-P31.3 path wrote."""
    from db.claim_sink import PgClaimSink

    claims = [
        {"subject_id": "v:1", "predicate_id": "sig.test.f", "value": 0.1 + 0.2},
        {"subject_id": "v:1", "predicate_id": "sig.test.big", "value": 12345678901234567890},
        {"subject_id": "v:1", "predicate_id": "sig.test.b", "value": True},
        {"subject_id": "v:1", "predicate_id": "sig.test.s", "value": "héllo", "raw_value": "HÉLLO"},
        {"subject_id": "v:1", "predicate_id": "sig.test.raw", "raw_value": "only raw"},
        {"subject_id": "v:1", "predicate_id": "sig.test.none"},
        {
            "subject_id": "v:1",
            "predicate_id": "sig.test.obs",
            "value": "x",
            "observed_at": "2026-02-01T10:11:12.123456Z",
        },
    ]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        PgClaimSink(conn, connector_name="shape").assert_claims(claims)
        rows = {
            r[0]: r[1:]
            for r in conn.execute(
                "SELECT predicate_id, value_kind::text, value_text, value_num, value_bool,"
                " raw_value, observed_at, observed_unknown_reason, object_type, object_entity"
                " FROM claim"
            ).fetchall()
        }
        # The float travels as float8 then numeric, as psycopg's float8 param did.
        expected_float = conn.execute("SELECT %s::float8::numeric", (0.1 + 0.2,)).fetchone()[0]
        dtypes = dict(
            conn.execute(
                "SELECT predicate_id, value_datatype FROM vocab_predicate "
                "WHERE predicate_id LIKE 'sig.test.%'"
            ).fetchall()
        )
    assert rows["sig.test.f"][2] == expected_float
    assert rows["sig.test.big"][2] == 12345678901234567890
    assert rows["sig.test.b"][1:4] == ("True", None, True)
    assert rows["sig.test.s"][1] == "héllo" and rows["sig.test.s"][4] == "HÉLLO"
    assert rows["sig.test.raw"][:2] == ("value", "only raw")
    assert rows["sig.test.none"][:4] == ("novalue", None, None, None)
    assert rows["sig.test.none"][4] == ""
    obs = rows["sig.test.obs"][5]
    assert obs is not None and obs.isoformat().startswith("2026-02-01T10:11:12.123456")
    assert rows["sig.test.obs"][6] is None
    assert rows["sig.test.s"][6] == "connector run did not record an observation time"
    assert all(r[7] == "literal" and r[8] is None for r in rows.values())
    assert dtypes["sig.test.f"] == "number" and dtypes["sig.test.big"] == "integer"
    assert dtypes["sig.test.b"] == "boolean" and dtypes["sig.test.s"] == "string"


def test_a_repeated_claim_within_one_chunk_counts_as_a_duplicate(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink

    claim = {"subject_id": "dup:1", "predicate_id": "sig.test.d", "value": "v"}
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="dup")
        sink.assert_claims([claim, dict(claim), {**claim, "value": "w"}])
        assert (sink.report.inserted, sink.report.duplicates) == (2, 1)
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM claim_evidence").fetchone()[0] == 2


def test_a_chunk_costs_a_bounded_number_of_round_trips(clean_dsn: str) -> None:
    """Round trips no longer scale with claims: 400 claims fit in a few dozen."""
    from db.claim_sink import PgClaimSink
    from db.sink_bench import CountingConnection

    claims = _claims([f"rt:{i}" for i in range(200)], tag="rt")
    with psycopg.connect(clean_dsn, autocommit=True) as real:
        counting = CountingConnection(real)
        sink = PgClaimSink(counting, connector_name="rt", insert_batch_size=150)  # type: ignore[arg-type]
        sink.assert_claims(claims)
        assert sink.report.inserted == 400
        # ~12 per-run prerequisite statements + predicates (2) + guard (4) +
        # 3 claim INSERTs + 3 evidence links; never ~4 per claim as before.
        assert counting.statements <= 30, counting.statements
        replay_counting = CountingConnection(real)
        replay = PgClaimSink(replay_counting, connector_name="rt")  # type: ignore[arg-type]
        replay.assert_claims(claims)
        assert (replay.report.inserted, replay.report.duplicates) == (0, 400)
        assert replay_counting.statements <= 20, replay_counting.statements


# --- the extension points -------------------------------------------------------


def test_the_duplicate_hook_receives_existing_claim_ids_inside_the_chunk(
    clean_dsn: str,
) -> None:
    from db.claim_sink import DuplicateBatch, PgClaimSink

    claims = _claims(["hook:1", "hook:2"])
    seen: list[DuplicateBatch] = []
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        first = PgClaimSink(conn, connector_name="hook", on_duplicates=seen.append)
        first.assert_claims(claims)
        assert seen == [], "no duplicates on the first land, so no call"
        stored = dict(conn.execute("SELECT content_digest, claim_id FROM claim").fetchall())

        def hook(batch: DuplicateBatch) -> None:
            assert batch.conn.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS
            seen.append(batch)

        again = PgClaimSink(conn, connector_name="hook", on_duplicates=hook)
        again.assert_claims([*claims, {**claims[0], "value": "changed"}])
    assert len(seen) == 1
    batch = seen[0]
    assert {k: str(v) for k, v in stored.items()} == dict(batch.existing)
    assert set(batch.capture_by_digest) == set(batch.existing)
    assert batch.run_id == again.run_id != first.run_id
    assert (again.report.inserted, again.report.duplicates) == (1, 4)


def test_the_object_seam_resolves_entity_refs_through_the_guard(
    clean_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import db.identity_guard as guard
    from db.claim_sink import EntityRef, PgClaimSink

    # P31.5 registers its organisation scheme; this test stands in for it.
    monkeypatch.setattr(guard, "GUARDED_SCHEMES", guard.GUARDED_SCHEMES | {"sig.test.org"})

    def resolver(claim: Any) -> EntityRef | None:
        if claim["predicate_id"] == "sig.test.operator":
            return EntityRef("sig.test.org", str(claim["value"]), "organization")
        if claim["predicate_id"] == "sig.test.blank":
            return EntityRef("sig.test.org", "", "organization")  # no entity named
        return None

    claims = [
        {"subject_id": f"obj:{i}", "predicate_id": "sig.test.operator", "value": "Acme"}
        for i in range(3)
    ] + [
        {"subject_id": "obj:0", "predicate_id": "sig.test.name", "value": "cam"},
        {"subject_id": "obj:0", "predicate_id": "sig.test.blank", "value": "x"},
    ]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="obj", object_resolver=resolver)
        sink.assert_claims(claims)
        assert sink.report.entities == 4  # 3 subjects + 1 organization
        rows = conn.execute(
            "SELECT predicate_id, object_type, object_entity FROM claim ORDER BY predicate_id"
        ).fetchall()
        org = conn.execute(
            "SELECT entity_id FROM entity_identity_key WHERE scheme = 'sig.test.org'"
        ).fetchone()[0]
        org_type = conn.execute(
            "SELECT entity_type FROM entity WHERE entity_id = %s", (org,)
        ).fetchone()[0]
    assert org_type == "organization"
    assert rows[0] == ("sig.test.blank", "literal", None)
    assert rows[1] == ("sig.test.name", "literal", None)
    assert {r[1:] for r in rows[2:]} == {("entity_ref", org)}


def test_the_guard_refuses_an_attribute_scheme(clean_dsn: str) -> None:
    from db.identity_guard import resolve_identities

    with psycopg.connect(clean_dsn) as conn, pytest.raises(ValueError, match="identity-bearing"):
        resolve_identities(conn, "us.state", ["OK"], entity_type="organization")


def test_numeric_subclasses_land_as_plain_numbers(clean_dsn: str) -> None:
    """A float/int subclass (e.g. numpy.float64) stores its number, not its repr."""
    from db.claim_sink import PgClaimSink

    class F(float):
        def __repr__(self) -> str:
            return f"F({float(self)!r})"

    class I(int):  # noqa: E742 - a deliberately odd subclass
        def __str__(self) -> str:
            return f"I<{int(self)}>"

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        PgClaimSink(conn, connector_name="sub").assert_claims(
            [
                {"subject_id": "sub:1", "predicate_id": "sig.test.subf", "value": F(0.5)},
                {"subject_id": "sub:1", "predicate_id": "sig.test.subi", "value": I(7)},
            ]
        )
        got = dict(conn.execute("SELECT predicate_id, value_num FROM claim").fetchall())
    assert got == {"sig.test.subf": 0.5, "sig.test.subi": 7}


def test_a_replay_resolves_keyed_subjects_in_one_statement(clean_dsn: str) -> None:
    """Already-keyed subjects never reach the legacy entity_identifier lookup."""
    from db.identity_guard import SUBJECT_SCHEME, resolve_identities
    from db.sink_bench import CountingConnection

    values = [f"keyed:{i}" for i in range(50)]
    with psycopg.connect(clean_dsn) as real:
        first = resolve_identities(real, SUBJECT_SCHEME, values, entity_type="deployment")
        real.commit()
        counting = CountingConnection(real)
        again = resolve_identities(counting, SUBJECT_SCHEME, values, entity_type="deployment")
        real.commit()
    assert counting.statements == 1
    assert again.entity_by_value == first.entity_by_value and not again.minted


def test_each_assert_claims_call_is_a_commit_boundary_under_one_run(clean_dsn: str) -> None:
    """The P31.4 per-capture flush: every call has committed when it returns."""
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="flush")
        for capture in range(3):
            sink.assert_claims(_claims([f"flush:{capture}"], tag="flush"))
            with psycopg.connect(clean_dsn, autocommit=True) as other:
                seen = other.execute("SELECT count(*) FROM claim").fetchone()[0]
            assert seen == 2 * (capture + 1), "a call's claims are visible to others on return"
        assert sink.report.inserted == 6
        assert conn.execute("SELECT count(DISTINCT ingest_run_id) FROM claim").fetchone()[0] == 1


def test_a_failed_chunk_forgets_the_entities_and_predicates_it_cached(clean_dsn: str) -> None:
    """The rolled-back chunk's cached ids are undone, so the retry re-mints them."""
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="undo", commit_chunk_size=2)
        real_write = sink._write_chunk
        calls = {"n": 0}

        def fail_second() -> None:
            calls["n"] += 1
            real_write()
            if calls["n"] == 2:
                raise RuntimeError("simulated failure after the chunk's writes")

        sink._write_chunk = fail_second  # type: ignore[method-assign]
        claims = [
            {"subject_id": f"undo:{i}", "predicate_id": f"sig.test.undo{i}", "value": i}
            for i in range(4)
        ]
        with pytest.raises(RuntimeError):
            sink.assert_claims(claims)
        assert sink.report.entities == 2 and sink.report.inserted == 2
        sink._write_chunk = real_write  # type: ignore[method-assign]
        sink.assert_claims(claims)
        assert sink.report.inserted == 4 and sink.report.duplicates == 2
        assert sink.report.entities == 4
        assert conn.execute("SELECT count(*) FROM entity").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 4
