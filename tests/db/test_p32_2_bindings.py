# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.2 (SIG-TRUST-001/002) live-Postgres tests: typed assertions and actual
capture bindings, end-to-end against the real spine.

* every typed field of ``sig.assertion/1`` persists on the claim row, the typed
  locator + binding classification on ``claim_evidence``, the extraction
  identity on ``extraction``, and the qualifier rows on ``claim_qualifier``;
* two captures in one execution bind individually;
* identical bytes → ONE deduplicated blob + TWO immutable occurrence rows, each
  binding resolving its own occurrence (never a mutable latest);
* repeated ingest is +0; replay binds the ORIGINAL occurrence and preserves the
  original observation time while its own assertion time stays the replay's;
* the no-capture legacy path is honestly classified ``legacy_synthetic`` /
  ``synthetic`` — never presented as real byte provenance;
* bad digest / unknown type / missing required field fail closed into
  ``assertion_quarantine`` while sibling claims still land.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "claim",
    "assertion_quarantine",
    "extraction",
    "ingest_run_capture",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)

_T1 = datetime(2026, 5, 1, tzinfo=UTC)
_T2 = datetime(2026, 6, 1, tzinfo=UTC)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


def _capture(
    body: bytes, uri: str, when: datetime, *, version: str = "v1", original_run: str | None = None
):
    """A CaptureRef shaped like the one OcflCaptureStore.put returns."""
    from connectors.stages import CaptureRef
    from evidence.digest import multihash

    d = multihash(body)
    return CaptureRef(
        digest=d,
        media_type="text/csv",
        source_uri=uri,
        byte_size=len(body),
        retrieved_at=when,
        ocfl_object_id=f"sig:capture:{d}",
        ocfl_version=version,
        original_run_id=original_run,
    )


def _claim(subject: str, predicate: str, value: Any, **kw: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "subject_id": subject,
        "predicate_id": predicate,
        "value": value,
        "source_id": "p32_2_src",
        "license": "CC0-1.0",
        "evidence_genre": "registry_export",
    }
    rec.update(kw)
    return rec


def _sink(dsn: str, **kw: Any):
    from db.claim_sink import PgClaimSink

    return PgClaimSink.from_dsn(
        dsn, connector_name="p32_2", connector_version="1.0.0", code_commit="p32.2-test", **kw
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


def _row(sql: str, conn: psycopg.Connection[Any], params: tuple[Any, ...] = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    assert row is not None, sql
    return row


def _one(sql: str, conn: psycopg.Connection[Any], params: tuple[Any, ...] = ()) -> Any:
    return _row(sql, conn, params)[0]


# --- typed assertion end-to-end -----------------------------------------------


def test_a_typed_assertion_lands_every_field(clean_dsn: str) -> None:
    cap = _capture(b"csv-body", "https://example/reg.csv", _T1, version="v4")
    claim = _claim(
        "cam:1",
        "sig.p32_2.count",
        42,
        object_type="quantity",
        unit="cameras",
        raw_value="42 units",
        raw_context={"section": "4.2", "row": 7},
        normalization_id="int_strip",
        normalization_version="1.2",
        valid_from="2026-01-01",
        valid_to="2026-12-31",
        observed_at="2026-04-15T00:00:00Z",
        source_reliability="R2",
        claim_directness="D3",
        artifact_integrity="I2",
        reliability_provisional=True,
        sensitivity_tier=1,
        claim_polarity="denies",
        rank="preferred",
        review_status="machine_accepted",
        legacy_source_tier="B",
        assertion_rationale="stated in registry",
        extraction_method="deterministic",
        extractor_version="2.1.0",
        extraction_config_digest="cfg:abc123",
        locator={"kind": "byte_range", "start": 10, "end": 20},
        qualifiers=[
            {
                "qualifier_id": "qual.p32_2.jurisdiction",
                "value": "US-OK",
                "jurisdiction": "US-OK",
                "valid_from": "2026-01-01",
                "valid_to": "2026-06-30",
            },
            {"qualifier_id": "qual.p32_2.amount", "value": 7.5, "unit": "USD"},
        ],
    )
    sink = _sink(clean_dsn)
    sink.assert_claims([claim], capture=cap)
    # The two unregistered qualifiers quarantine; the claim itself still lands —
    # a bad qualifier can never make a valid claim disappear (SIG-TRUST-001).
    assert sink.report.inserted == 1 and sink.report.quarantined == 2

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = _row(
            "SELECT value_num, unit, raw_value, raw_context, normalization_id,"
            " normalization_version, valid_period, observed_at, source_reliability,"
            " reliability_provisional, claim_directness, artifact_integrity,"
            " sensitivity_tier, claim_polarity, rank, review_status, legacy_source_tier,"
            " assertion_rationale, object_type, assertion_map_id, assertion_map_basis"
            " FROM claim",
            conn,
        )
        (
            value_num,
            unit,
            raw_value,
            raw_context,
            norm_id,
            norm_ver,
            valid_period,
            observed_at,
            rel,
            prov,
            direc,
            integ,
            tier,
            polarity,
            rank,
            review,
            legacy_tier,
            rationale,
            obj_type,
            map_id,
            map_basis,
        ) = row
        assert str(value_num) == "42" and unit == "cameras" and raw_value == "42 units"
        assert raw_context["row"] == 7
        assert norm_id == "int_strip" and norm_ver == "1.2"
        assert observed_at.isoformat().startswith("2026-04-15")
        assert (rel, direc, integ) == ("R2", "D3", "I2") and prov is True
        assert tier == 1 and polarity == "denies" and rank == "preferred"
        assert review == "machine_accepted" and legacy_tier == "B"
        assert rationale == "stated in registry" and obj_type == "quantity"
        assert map_id == "sig.assertion.map.v1"
        # The only default was value_kind (value present → 'value'), named in the basis.
        assert map_basis == "connector_record|value_kind=derived_from_value_presence"
        # The unregistered qualifiers quarantined (they were never registered) —
        # the claim still landed (a bad qualifier cannot kill a valid claim).
        reasons = [r[0] for r in conn.execute("SELECT reason FROM assertion_quarantine").fetchall()]
        assert reasons == ["unknown_qualifier", "unknown_qualifier"]

        ev = _row(
            "SELECT ce.capture_id, ce.extraction_id, ce.binding_status, ce.locator,"
            " ce.extraction_config_digest, ce.extractor_version"
            " FROM claim_evidence ce",
            conn,
        )
        cap_id, ext_id, bstatus, locator, cfg, ext_ver = ev
        assert bstatus == "actual_capture"
        assert locator == {"kind": "byte_range", "start": 10, "end": 20}
        assert cfg == "cfg:abc123" and ext_ver == "2.1.0"

        cap_row = _row(
            "SELECT content_digest, byte_size, source_uri, ocfl_version,"
            " capture_classification, retrieved_at::text, media_type"
            " FROM evidence_capture WHERE capture_id = %s",
            conn,
            (str(cap_id),),
        )
        assert cap_row[0] == cap.digest and cap_row[1] == len(b"csv-body")
        assert cap_row[2] == "https://example/reg.csv" and cap_row[3] == "v4"
        assert cap_row[4] == "actual" and cap_row[5].startswith("2026-05-01")
        assert cap_row[6] == "text/csv"

        ex = _row(
            "SELECT capture_id, method, extractor_name, extractor_version, run_id"
            " FROM extraction WHERE extraction_id = %s",
            conn,
            (str(ext_id),),
        )
        assert str(ex[0]) == str(cap_id) and ex[1] == "deterministic"
        assert ex[2] == "p32_2" and ex[3] == "2.1.0" and str(ex[4]) == sink.run_id

        blob = _row("SELECT blob_digest, source_uri, ocfl_version FROM evidence_blob", conn)
        assert blob[0] == cap.digest and blob[2] == "v4"


def test_registered_qualifiers_land_on_claim_qualifier(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO vocab_resolution_strategy(strategy_id, definition)"
            " VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
        )
        conn.execute(
            "INSERT INTO vocab_predicate(predicate_id, vocab_version, value_datatype,"
            " object_type, definition, volatility_class, resolution_strategy)"
            " VALUES ('qual.p32_2.jurisdiction','1.0','text','literal','q','IMMUTABLE',"
            "            'authoritative_source_wins'),"
            "        ('qual.p32_2.amount','1.0','numeric','quantity','q','IMMUTABLE',"
            "            'authoritative_source_wins')"
            " ON CONFLICT DO NOTHING"
        )
    cap = _capture(b"q", "https://example/q.csv", _T1)
    claim = _claim(
        "cam:q",
        "sig.p32_2.q",
        "v",
        qualifiers=[
            {
                "qualifier_id": "qual.p32_2.jurisdiction",
                "value": "US-OK",
                "jurisdiction": "US-OK",
                "valid_from": "2026-01-01",
            },
            {"qualifier_id": "qual.p32_2.amount", "value": 9, "unit": "USD", "rank": "preferred"},
        ],
    )
    sink = _sink(clean_dsn)
    sink.assert_claims([claim], capture=cap)
    assert sink.report.quarantined == 0
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT qualifier_id, value_text, value_num, unit, jurisdiction,"
            " valid_from, rank, extraction_id IS NOT NULL FROM claim_qualifier"
            " ORDER BY qualifier_id"
        ).fetchall()
    assert len(rows) == 2
    assert rows[0][:6] == ("qual.p32_2.amount", None, 9, "USD", None, None)
    assert rows[0][6] == "preferred" and rows[0][7] is True
    assert rows[1][0] == "qual.p32_2.jurisdiction" and rows[1][1] == "US-OK"
    assert rows[1][4] == "US-OK" and str(rows[1][5]) == "2026-01-01"


# --- two captures in one execution --------------------------------------------


def test_two_captures_in_one_execution_bind_individually(clean_dsn: str) -> None:
    cap_a = _capture(b"page-a", "https://example/a.html", _T1)
    cap_b = _capture(b"page-b", "https://example/b.html", _T2)
    sink = _sink(clean_dsn)
    sink.assert_claims(
        [_claim("cam:a", "sig.p32_2.a", "va", locator={"kind": "page", "page": 1})],
        capture=cap_a,
    )
    sink.assert_claims(
        [_claim("cam:b", "sig.p32_2.b", "vb", locator={"kind": "page", "page": 2})],
        capture=cap_b,
    )
    assert sink.report.inserted == 2
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT c.predicate_id, ec.content_digest, ec.retrieved_at::text,"
            " ec.capture_classification, ce.binding_status"
            " FROM claim c JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
            " JOIN evidence_capture ec ON ec.capture_id = ce.capture_id"
            " ORDER BY c.predicate_id"
        ).fetchall()
        # Each capture is its own occurrence row — individually attributable.
        assert _one("SELECT count(*) FROM evidence_capture", conn) == 2
    assert len(rows) == 2
    assert rows[0][1] == cap_a.digest and rows[0][2].startswith("2026-05-01")
    assert rows[1][1] == cap_b.digest and rows[1][2].startswith("2026-06-01")
    assert {r[3] for r in rows} == {"actual"} and {r[4] for r in rows} == {"actual_capture"}


# --- blob dedup: one blob, two immutable occurrences ---------------------------


def test_identical_bytes_one_blob_two_occurrences(clean_dsn: str) -> None:
    body = b"same-bytes"
    uri = "https://example/dedup.csv"
    cap1 = _capture(body, uri, _T1, version="v1")
    cap2 = _capture(body, uri, _T2, version="v2")
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("cam:d1", "sig.p32_2.d1", "first")], capture=cap1)
    sink.assert_claims([_claim("cam:d2", "sig.p32_2.d2", "second")], capture=cap2)

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # ONE deduplicated blob for the identical bytes+URI (SIG-EVID-004) ...
        blobs = conn.execute(
            "SELECT blob_digest, source_uri, ocfl_version FROM evidence_blob"
        ).fetchall()
        assert len(blobs) == 1 and blobs[0][1] == uri
        # ... and TWO immutable occurrence rows, each its own retrieval time.
        caps = conn.execute(
            "SELECT ocfl_version, retrieved_at::text FROM evidence_capture ORDER BY retrieved_at"
        ).fetchall()
        assert len(caps) == 2
        assert caps[0][0] == "v1" and caps[0][1].startswith("2026-05-01")
        assert caps[1][0] == "v2" and caps[1][1].startswith("2026-06-01")
        # Each claim binds ITS OWN occurrence — resolvable per binding, not a
        # mutable "latest".
        links = conn.execute(
            "SELECT c.value_text, ec.ocfl_version FROM claim c"
            " JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
            " JOIN evidence_capture ec ON ec.capture_id = ce.capture_id"
            " ORDER BY c.value_text"
        ).fetchall()
        assert [(r[0], r[1]) for r in links] == [("first", "v1"), ("second", "v2")]


def test_version_mismatch_quarantines_instead_of_rebinding(clean_dsn: str) -> None:
    """A binding whose declared OCFL version disagrees with the stored occurrence
    fails closed — never silently re-anchored to a different version."""
    uri = "https://example/vm.csv"
    sink = _sink(clean_dsn)
    sink.assert_claims(
        [_claim("cam:vm", "sig.p32_2.vm", "v1")],
        capture=_capture(b"vm-bytes", uri, _T1, version="v1"),
    )
    # Same occurrence (same digest+uri+retrieved_at) declared as v9 — the
    # binding disagrees with what was recorded: quarantined, +0 claims.
    sink.assert_claims(
        [_claim("cam:vm", "sig.p32_2.vm2", "v2")],
        capture=_capture(b"vm-bytes", uri, _T1, version="v9"),
    )
    assert sink.report.quarantined == 1 and sink.report.inserted == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        reason = _one("SELECT reason FROM assertion_quarantine", conn)
        assert reason == "version_mismatch"
        assert _one("SELECT count(*) FROM claim", conn) == 1
        assert _one("SELECT count(*) FROM evidence_capture", conn) == 1


# --- idempotency ----------------------------------------------------------------


def test_repeated_ingest_is_idempotent(clean_dsn: str) -> None:
    cap = _capture(b"idem", "https://example/i.csv", _T1)
    claims = [_claim("cam:i", "sig.p32_2.i", "iv")]
    sink = _sink(clean_dsn)
    sink.assert_claims(claims, capture=cap)
    sink.assert_claims(claims, capture=cap)  # a re-run: +0 everywhere
    assert sink.report.inserted == 1 and sink.report.duplicates == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _one("SELECT count(*) FROM claim", conn) == 1
        assert _one("SELECT count(*) FROM claim_evidence", conn) == 1
        assert _one("SELECT count(*) FROM evidence_capture", conn) == 1
        assert _one("SELECT count(*) FROM evidence_blob", conn) == 1


# --- replay ---------------------------------------------------------------------


def test_replay_binds_the_original_occurrence_and_time(clean_dsn: str) -> None:
    """A replay asserts NEW claims against the ORIGINAL capture occurrence —
    the source observation time stays the original retrieved_at, the replay's
    own assertion time lands on claim.sys_period / claim_evidence.bound_at."""
    body = b"replayed-bytes"
    uri = "https://example/orig.csv"
    live = _capture(body, uri, _T1, version="v1")
    live_sink = _sink(clean_dsn)
    live_sink.assert_claims([_claim("cam:r", "sig.p32_2.r1", "orig")], capture=live)

    replay_ref = _capture(body, uri, _T1, version="v1", original_run=live_sink.run_id)
    replay_sink = _sink(clean_dsn, is_replay=True)
    replay_sink.assert_claims([_claim("cam:r", "sig.p32_2.r2", "derived")], capture=replay_ref)
    assert replay_sink.report.inserted == 1

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # The same occurrence is REUSED — the replay never writes a second row
        # for bytes the original run already captured.
        assert _one("SELECT count(*) FROM evidence_capture", conn) == 1
        occ = _row("SELECT retrieved_at::text, retrieved_by_run_id FROM evidence_capture", conn)
        assert occ[0].startswith("2026-05-01")  # original observation time kept
        assert str(occ[1]) == live_sink.run_id  # acquisition stays the original run's
        row = _row(
            "SELECT c.observed_at::text, c.ingest_run_id, ce.binding_status,"
            " ce.extraction_id FROM claim c JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
            " WHERE c.predicate_id = 'sig.p32_2.r2'",
            conn,
        )
        # The replayed claim's observation time is the ORIGINAL retrieved_at,
        # its assertion run is the REPLAY run, and the link is marked replayed.
        assert row[0].startswith("2026-05-01")
        assert str(row[1]) == replay_sink.run_id != live_sink.run_id
        assert row[2] == "replayed"
        ex = _row(
            "SELECT capture_id, run_id FROM extraction WHERE extraction_id = %s",
            conn,
            (str(row[3]),),
        )
        assert str(ex[1]) == replay_sink.run_id  # extraction time is the replay's


# --- the honest legacy path -----------------------------------------------------


def test_no_capture_is_honestly_legacy_synthetic(clean_dsn: str) -> None:
    """A sink call without a binding still lands claims — classified truthfully,
    never presented as byte-anchored provenance (SIG-TRUST-002)."""
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("cam:l", "sig.p32_2.l", "lv")])
    assert sink.report.inserted == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        row = _row(
            "SELECT ce.binding_status, ec.capture_classification, c.assertion_map_basis"
            " FROM claim c JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
            " JOIN evidence_capture ec ON ec.capture_id = ce.capture_id",
            conn,
        )
        assert row[0] == "legacy_synthetic" and row[1] == "synthetic"
        assert row[2] == "legacy_synthetic"


# --- fail-closed quarantine ------------------------------------------------------


def test_bad_digest_quarantines_the_whole_call(clean_dsn: str) -> None:
    """A binding with an undecodable digest fails the call closed — nothing is
    silently re-anchored to fabricated provenance."""
    from connectors.stages import CaptureRef

    bad = CaptureRef(
        digest="zzz-not-a-multihash",
        media_type="text/csv",
        source_uri="https://example/bad.csv",
        byte_size=5,
        retrieved_at=_T1,
    )
    sink = _sink(clean_dsn)
    sink.assert_claims(
        [_claim("cam:q1", "sig.p32_2.q1", "a"), _claim("cam:q1", "sig.p32_2.q2", "b")],
        capture=bad,
    )
    # The rejection is call-scoped: the same unusable binding quarantines once.
    assert sink.report.inserted == 0 and sink.report.quarantined == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows = conn.execute("SELECT reason, payload_digest FROM assertion_quarantine").fetchall()
        assert {r[0] for r in rows} == {"bad_digest"}
        # A re-run of the same rejection is +0 (payload_digest idempotency).
        sink2 = _sink(clean_dsn)
        sink2.assert_claims([_claim("cam:q1", "sig.p32_2.q1", "a")], capture=bad)
        assert _one("SELECT count(*) FROM assertion_quarantine", conn) == 1


def test_unknown_type_quarantines_but_siblings_land(clean_dsn: str) -> None:
    """One bad record never makes a valid claim or entity disappear."""
    cap = _capture(b"mix", "https://example/mix.csv", _T1)
    sink = _sink(clean_dsn)
    sink.assert_claims(
        [
            _claim("cam:m", "sig.p32_2.good", "kept"),
            _claim("cam:m", "sig.p32_2.bad", "lost", object_type="no_such_type"),
            _claim("cam:m", "", "orphan"),  # missing predicate
        ],
        capture=cap,
    )
    assert sink.report.inserted == 1 and sink.report.quarantined == 2
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        reasons = sorted(
            r[0] for r in conn.execute("SELECT reason FROM assertion_quarantine").fetchall()
        )
        assert reasons == ["missing_required_field", "unknown_object_type"]
        assert _one("SELECT count(*) FROM claim", conn) == 1
        # The quarantine row carries the full rejected record (auditable).
        payload = _one(
            "SELECT payload FROM assertion_quarantine WHERE reason='unknown_object_type'", conn
        )
        assert payload["record"]["predicate_id"] == "sig.p32_2.bad"


def test_quarantine_is_not_publicly_readable(clean_dsn: str) -> None:
    """Unreviewed rejected content is auditable by internal roles, NEVER exposed
    to the public read surface (SIG-TRUST-001)."""
    cap = _capture(b"qq", "https://example/qq.csv", _T1)
    sink = _sink(clean_dsn)
    sink.assert_claims([_claim("cam:qq", "sig.p32_2.qq", "x", object_type="nope")], capture=cap)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute("SET ROLE sig_read_public")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT count(*) FROM assertion_quarantine").fetchone()
