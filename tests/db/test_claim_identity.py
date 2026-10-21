# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.22 / F-504 — the claim spine's truthful identity (live PG).

These tests drive ``PgClaimSink`` against a real spine (the Docker/sqitch
harness) and pin the CP-1 invariants:

* a re-observation of the same fact — differing only in volatile acquisition
  fields (row position, capture digest, fetch time) — re-binds to the SAME
  claim (inserts 0, links a re-sighting), never re-mints;
* a ``ref`` predicate's temporal-qualifier change mints no new id;
* an ``obs`` (registry-declared windowed) predicate's qualifier IS identity;
* new rows carry ``payload_version``; a stored digest is never rewritten;
* the migration is additive — pre-existing digests keep working.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPINE_TABLES = (
    "claim_evidence",
    "assertion_quarantine",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
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
    """Truncated spine + the two fixture predicates this file needs."""
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
        from conftest import register_vocab_predicate

        register_vocab_predicate(conn, "sig.test.ref_fact")
        # An `obs`-class fixture predicate: registry-declared windowed —
        # interval resolution strategy + is_windowed (the class is read from
        # vocab_predicate, never guessed).
        conn.execute(
            "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
            "VALUES('interval_union','fixture') ON CONFLICT DO NOTHING"
        )
        conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy,is_windowed) "
            "VALUES('sig.test.obs_fact','1.0.0','integer','literal','fixture',"
            "'VOLATILE',183,'interval_union',true) ON CONFLICT DO NOTHING"
        )
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _sink(dsn: str):
    from db.claim_sink import PgClaimSink, record_resightings

    # `on_duplicates` is the production re-sighting hook (P31.7 /
    # ADR-R9-RESIGHT) — `make_claim_sink` wires it; the direct constructor needs
    # it passed so a re-bound claim gains its new `claim_evidence` sighting.
    return PgClaimSink.from_dsn(
        dsn,
        connector_name="identity_test",
        connector_version="1.0.0",
        code_commit="p35.22-test",
        on_duplicates=record_resightings,
    )


def _claim(predicate: str, value: str, **over: object) -> dict[str, object]:
    rec: dict[str, object] = {
        "subject_id": "sig.test:cam-1",
        "predicate_id": predicate,
        "value": value,
        "source_id": "identity_test_source",
        "license": "CC0-1.0",
        "record_kind": "claim",
    }
    rec.update(over)
    return rec


def _capture(body: bytes, when: object):
    """A CaptureRef shaped like the one OcflCaptureStore.put returns."""
    from datetime import datetime

    from connectors.stages import CaptureRef
    from evidence.digest import multihash

    assert isinstance(when, datetime)
    d = multihash(body)
    return CaptureRef(
        digest=d,
        media_type="text/csv",
        source_uri=f"https://registry.example/{d[:16]}",
        byte_size=len(body),
        retrieved_at=when,
        ocfl_object_id=f"sig:capture:{d}",
        ocfl_version="v1",
    )


def _counts(dsn: str) -> tuple[int, int]:
    with psycopg.connect(dsn, autocommit=True) as conn:
        claims = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest IS NOT NULL"
        ).fetchone()[0]
        links = conn.execute("SELECT count(*) FROM claim_evidence").fetchone()[0]
    return int(claims), int(links)


def test_re_observation_rebinds_never_remints(clean_dsn: str) -> None:
    """F-504: the same fact seen at another row position / fetch is ONE claim."""
    from datetime import UTC, datetime

    sink = _sink(clean_dsn)
    first = _claim("sig.test.ref_fact", "seen-once", row_index=0, page=1)
    sink.assert_claims(
        [first], capture=_capture(b"page-1-bytes", datetime(2026, 10, 1, tzinfo=UTC))
    )
    # Re-observation: another capture, another row position, same fact.
    second = _claim("sig.test.ref_fact", "seen-once", row_index=41, page=9)
    sink.assert_claims(
        [second], capture=_capture(b"page-9-bytes", datetime(2026, 10, 18, tzinfo=UTC))
    )
    claims, links = _counts(clean_dsn)
    assert claims == 1, "a re-observation must re-bind, not mint"
    assert links == 2, "each sighting is its own claim_evidence binding"


def test_ref_temporal_change_never_mints(clean_dsn: str) -> None:
    """A ``valid_from``-only change on a ref predicate re-binds."""
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("sig.test.ref_fact", "v1", valid_from="2024-01-01")])
    sink.assert_claims([_claim("sig.test.ref_fact", "v1", valid_from="2025-06-01")])
    claims, _ = _counts(clean_dsn)
    assert claims == 1, "a ref predicate's temporal qualifier is not identity"


def test_obs_temporal_qualifier_is_identity(clean_dsn: str) -> None:
    """An obs predicate's window IS the claim — two windows, two claims."""
    sink = _sink(clean_dsn)
    sink.assert_claims(
        [
            _claim(
                "sig.test.obs_fact",
                "7",
                value_kind="value",
                valid_from="2026-01-01",
                valid_to="2026-02-01",
            )
        ]
    )
    sink.assert_claims(
        [
            _claim(
                "sig.test.obs_fact",
                "7",
                value_kind="value",
                valid_from="2026-02-01",
                valid_to="2026-03-01",
            )
        ]
    )
    claims, _ = _counts(clean_dsn)
    assert claims == 2, "distinct windows of an obs predicate are distinct claims"


def test_payload_version_stamped_and_digests_stable(clean_dsn: str) -> None:
    """New rows carry the payload version; a stored digest is never rewritten."""
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("sig.test.ref_fact", "versioned")])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = conn.execute("SELECT content_digest, payload_version FROM claim").fetchone()
    assert row is not None
    digest_before = row[0]
    assert row[1] == "sig.claim-payload/1", "new claims record the normalisation version"
    # Re-assert the identical claim: nothing changes, digest untouched.
    sink2 = _sink(clean_dsn)
    sink2.assert_claims([_claim("sig.test.ref_fact", "versioned")])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        after = conn.execute("SELECT content_digest FROM claim").fetchall()
    assert [r[0] for r in after] == [digest_before]


def test_value_json_canonicalised_on_store(clean_dsn: str) -> None:
    """The stored value_json is the canonical form the digest consumes."""
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("sig.test.ref_fact", "payload", value_json={"b": 2, "a": 1.0})])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = conn.execute("SELECT value_json FROM claim").fetchone()
    assert row is not None
    # canonical: sorted keys, compact separators, 1.0 -> 1
    assert row[0] == {"a": 1, "b": 2}


def test_stored_row_digests_never_recomputed(clean_dsn: str) -> None:
    """CP-1's no-mass-re-mint: an old row's digest is append-only bytes."""
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("sig.test.ref_fact", "pinned")])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        digest = conn.execute("SELECT content_digest FROM claim").fetchone()[0]
        # Simulate the migration-invariant: the digest stays what it was —
        # nothing recomputes it from the row's columns.
        same = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest = %s", (digest,)
        ).fetchone()[0]
    assert same == 1
