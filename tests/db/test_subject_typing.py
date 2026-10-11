# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.14b — subject entity typing, fail-closed refusal, and the append-only
typed-identity write (L1 NEW-5 / FM-17, SIG-IDENT-025, SIG-GEO-005).

Covered here, over the real sqitch-deployed spine:

* mapped subjects mint their declared ``entity_type`` (never ``deployment``);
* an unmapped subject quarantines ``unknown_subject_scheme`` and mints nothing;
* a ``sig.connector.subject`` object_ref disagreeing with the map quarantines;
* the typed-identity write is dry-run by default, INSERT-only, and a re-run
  appends +0 while the original mistyped ``entity`` row is untouched;
* ``physical_asset.mobility`` rejects a value outside the Mobility enum
  (NOT VALID binds new writes) and admits every enum member;
* ``entity_current_type`` resolves the decided type over the recorded one.

DB-gated: these run under ``SIG_REQUIRE_DB_TESTS`` (``make test-db``) and skip
without Docker — the conftest's autouse typer stub is deliberately bypassed by
constructing sinks with the REAL map explicitly.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

_PREDICATE = "sig.test.subject_typing"
_TRUNCATE = (
    "TRUNCATE claim_evidence, assertion_quarantine, claim, extraction, "
    "evidence_capture, evidence_blob, evidence_artifact, entity_identifier, "
    "entity_type_decision, entity_identity_key, ingest_run, source_registry, "
    "entity CASCADE"
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """A DSN whose spine is truncated before AND after the test."""
    dsn = _dsn(sig_database)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)
        from conftest import register_vocab_predicate

        register_vocab_predicate(conn, _PREDICATE)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)


def _real_map_sink(dsn: str, **kwargs: Any) -> Any:
    """A sink whose subject typer is the committed map — explicit, so the
    conftest stub (kept for pre-existing plumbing fixtures) cannot soften the
    fail-closed contract these tests pin.
    """
    from db.claim_sink import PgClaimSink
    from db.subject_types import entity_type_for_subject

    return PgClaimSink.from_dsn(
        dsn,
        connector_name="subject_typing_test",
        connector_version="1.0.0",
        code_commit="p35.14b-test",
        subject_typer=entity_type_for_subject,
        **kwargs,
    )


def _claim(subject: str, value: str = "v") -> dict[str, Any]:
    return {
        "record_kind": "claim",
        "subject_id": subject,
        "predicate_id": _PREDICATE,
        "value": value,
        "raw_value": value,
        "source_id": "subject_typing_source",
        "license": "CC0-1.0",
    }


def _entity_type_for_subject_value(conn: Any, value: str) -> str | None:
    row = conn.execute(
        "SELECT e.entity_type FROM entity_identifier i "
        "JOIN entity e ON e.entity_id = i.entity_id "
        "WHERE i.scheme = 'sig.connector.subject' AND i.value = %s",
        (value,),
    ).fetchone()
    return None if row is None else str(row[0])


def test_mapped_subjects_mint_their_declared_types(clean_dsn: str) -> None:
    sink = _real_map_sink(clean_dsn)
    cases = {
        "agency:test:typing-org": "organization",
        "contract:test:typing-c1": "contract",
        "traffic_camera:test:t:cam-1": "physical_asset",
        "flock_portal:test-portal": "data_system",
        "legal_instrument:test:li-1": "legal_instrument",
        "records:test:req-1": "records_request",
        "sig:deployment:test-d1": "deployment",
    }
    sink.assert_claims([_claim(s, f"v-{i}") for i, s in enumerate(cases)])
    assert sink.report.quarantined == 0
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        for subject, expected in cases.items():
            actual = _entity_type_for_subject_value(conn, subject)
            assert actual == expected, f"{subject}: minted {actual}, expected {expected}"


def test_the_default_sink_binds_the_declared_map(clean_dsn: str, monkeypatch: Any) -> None:
    # The conftest autouse stub replaces the sink's module-level typer; restore
    # the real one and prove a default-constructed sink resolves the map —
    # the production path (no kwargs) must be the fail-closed one.
    import db.claim_sink as claim_sink
    from db.claim_sink import PgClaimSink
    from db.subject_types import entity_type_for_subject

    monkeypatch.setattr(claim_sink, "entity_type_for_subject", entity_type_for_subject)
    sink = PgClaimSink.from_dsn(
        clean_dsn,
        connector_name="subject_typing_test",
        connector_version="1.0.0",
        code_commit="p35.14b-test",
    )
    sink.assert_claims([_claim("agency:test:default-map")])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _entity_type_for_subject_value(conn, "agency:test:default-map") == "organization"


def test_an_unmapped_subject_quarantines_and_mints_nothing(clean_dsn: str) -> None:
    sink = _real_map_sink(clean_dsn)
    sink.assert_claims([_claim("totally:new:scheme:1")])
    assert sink.report.inserted == 0
    assert sink.report.quarantined == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = conn.execute(
            "SELECT reason FROM assertion_quarantine ORDER BY received_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None and row[0] == "unknown_subject_scheme"
        # No identifier, no entity — the record is preserved, nothing minted.
        assert (
            conn.execute(
                "SELECT count(*) FROM entity_identity_key WHERE value = %s",
                ("totally:new:scheme:1",),
            ).fetchone()[0]
            == 0
        )


def test_a_subject_scheme_object_ref_must_agree_with_the_map(clean_dsn: str) -> None:
    from db.claim_sink import record_object_ref

    sink = _real_map_sink(clean_dsn, object_resolver=record_object_ref)
    claim = _claim("agency:test:ref-subject")
    claim["object_ref"] = {
        "scheme": "sig.connector.subject",
        "value": "flock_portal:test-partner",
        "entity_type": "deployment",  # the pre-P35.14b placeholder type — wrong now
        "label": "test-partner",
    }
    sink.assert_claims([claim])
    assert sink.report.quarantined == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = conn.execute(
            "SELECT reason FROM assertion_quarantine ORDER BY received_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None and row[0] == "unknown_subject_scheme"
        # The disagreeing ref minted nothing either.
        assert (
            conn.execute(
                "SELECT count(*) FROM entity_identity_key WHERE value = %s",
                ("flock_portal:test-partner",),
            ).fetchone()[0]
            == 0
        )


def test_a_subject_scheme_object_ref_agreeing_with_the_map_lands(clean_dsn: str) -> None:
    from db.claim_sink import record_object_ref

    sink = _real_map_sink(clean_dsn, object_resolver=record_object_ref)
    claim = _claim("agency:test:ref-ok")
    claim["object_ref"] = {
        "scheme": "sig.connector.subject",
        "value": "flock_portal:test-ok",
        "entity_type": "data_system",
        "label": "test-ok",
    }
    sink.assert_claims([claim])
    assert sink.report.inserted == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _entity_type_for_subject_value(conn, "flock_portal:test-ok") == "data_system"


# --- The append-only typed-identity write (L1 leg, part b) --------------------


def _seed_mistyped_spine(dsn: str) -> None:
    """Reproduce the pre-P35.14b world: subjects minted as 'deployment'
    regardless of family — via a stub typer, exactly like the old default."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink.from_dsn(
        dsn,
        connector_name="subject_typing_test",
        connector_version="1.0.0",
        code_commit="p35.14b-test",
        subject_typer=lambda _s: "deployment",
    )
    sink.assert_claims(
        [
            _claim("agency:test:hist-org"),
            _claim("contract:test:hist-c"),
            _claim("sig:deployment:test:hist-d"),
        ]
    )


def test_typed_identity_write_dry_run_apply_and_plus_zero(clean_dsn: str) -> None:
    from db.typed_identity import apply_decisions, plan_decisions

    _seed_mistyped_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # Dry-run: computes pending corrections, writes nothing.
        plan = plan_decisions(conn)
        pending = {d.value: (d.prior_type, d.entity_type) for d in plan.pending}
        assert pending == {
            "agency:test:hist-org": ("deployment", "organization"),
            "contract:test:hist-c": ("deployment", "contract"),
        }
        assert conn.execute("SELECT count(*) FROM entity_type_decision").fetchone()[0] == 0

        inserted = apply_decisions(conn, plan)
        assert inserted == 2
        # Rerun: the UNIQUE (scheme, value, type, map_version) barrier lands +0.
        assert apply_decisions(conn, plan_decisions(conn)) == 0
        assert conn.execute("SELECT count(*) FROM entity_type_decision").fetchone()[0] == 2

        # The original rows stand — append-only history, never rewritten.
        assert _entity_type_for_subject_value(conn, "agency:test:hist-org") == "deployment"
        # …while the effective-type view resolves the decision.
        row = conn.execute(
            "SELECT c.entity_type FROM entity_current_type c "
            "JOIN entity_identifier i ON i.entity_id = c.entity_id "
            "WHERE i.value = 'agency:test:hist-org'"
        ).fetchone()
        assert row is not None and row[0] == "organization"

        # Decision rows carry the provenance the leg requires: the keyed
        # subject, the prior recorded type, the map version that decided it.
        cols = conn.execute(
            "SELECT scheme, value, prior_type, entity_type, map_version "
            "FROM entity_type_decision ORDER BY value"
        ).fetchall()
        assert cols == [
            (
                "sig.connector.subject",
                "agency:test:hist-org",
                "deployment",
                "organization",
                "1.0.0",
            ),
            ("sig.connector.subject", "contract:test:hist-c", "deployment", "contract", "1.0.0"),
        ]


def test_unmapped_existing_subjects_are_reported_never_typed(clean_dsn: str) -> None:
    from db.typed_identity import apply_decisions, plan_decisions

    _seed_mistyped_spine(clean_dsn)
    # A keyed subject the map does not cover (minted under the old default).
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        entity_id = conn.execute(
            "INSERT INTO entity (entity_type) VALUES ('deployment') RETURNING entity_id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO entity_identity_key (scheme, value, entity_id) "
            "VALUES ('sig.connector.subject', 'strange:historical:1', %s)",
            (entity_id,),
        )
        plan = plan_decisions(conn)
        assert ("strange:historical:1", "deployment") in plan.unmapped
        assert all(d.value != "strange:historical:1" for d in plan.pending)
        apply_decisions(conn, plan)
        # Reported, never typed: no decision row names the unmapped subject.
        assert (
            conn.execute(
                "SELECT count(*) FROM entity_type_decision WHERE value = 'strange:historical:1'"
            ).fetchone()[0]
            == 0
        )


# --- The Mobility CHECK NOT VALID (SIG-GEO-005) --------------------------------


def test_physical_asset_mobility_check_rejects_out_of_vocabulary(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        (entity_id,) = conn.execute(
            "INSERT INTO entity (entity_type) VALUES ('physical_asset') RETURNING entity_id"
        ).fetchone()
        # 'mobile' — the exact out-of-vocabulary value the OSM writer recorded.
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO physical_asset (entity_id, mobility) VALUES (%s, 'mobile')",
                (entity_id,),
            )


def test_physical_asset_mobility_check_admits_the_enum(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        for member in (
            "fixed",
            "redeployable",
            "vehicle_mounted",
            "airborne",
            "handheld",
            "unknown",
        ):
            (entity_id,) = conn.execute(
                "INSERT INTO entity (entity_type) VALUES ('physical_asset') RETURNING entity_id"
            ).fetchone()
            conn.execute(
                "INSERT INTO physical_asset (entity_id, mobility) VALUES (%s, %s)",
                (entity_id, member),
            )


def test_mobility_check_is_not_valid_yet(clean_dsn: str) -> None:
    # NOT VALID binds new writes; existing rows wait on the named follow-up —
    # asserting convalidated=false pins that the change did NOT secretly
    # validate historical rows.
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = conn.execute(
            "SELECT convalidated FROM pg_constraint "
            "WHERE conrelid = 'physical_asset'::regclass "
            "AND conname = 'physical_asset_mobility_vocab'"
        ).fetchone()
        assert row is not None and row[0] is False


def test_entity_type_decision_is_immutable(clean_dsn: str) -> None:
    from db.typed_identity import apply_decisions, plan_decisions

    _seed_mistyped_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        apply_decisions(conn, plan_decisions(conn))
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("UPDATE entity_type_decision SET entity_type = 'product'")
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("DELETE FROM entity_type_decision")
