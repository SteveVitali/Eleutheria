# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.18 (SIG-DOS-003): the OKC seed-correction packet applied to a live spine.

Docker-gated (PG18+PostGIS via the shared ``sig_database`` harness). The test
seeds the *legacy* pre-P32.3 records verbatim — the ambiguous flagship rows the
correction packet targets — then drives ``ops.seed_correction.apply_packet``
and asserts the §16.6 contract end to end:

* every legacy row's belief window is CLOSED (``sys_period`` upper bound), never
  deleted — a historical query still returns the original value;
* each corrected claim lands append-only with ``revises_claim`` +
  ``correction_reason`` + the declared ``count_scope`` qualifiers;
* the sourced ~100 replaces the never-sourced 190 while the labelled derived
  roll-up stays a packet label, not a claim;
* a dry-run writes nothing; a second apply is idempotent
  (``already_applied``, +0 rows);
* the ODbL OSM row keeps its own licence compartment.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from ops.seed_correction import _LEGACY_CLAIMS, apply_packet, correction_packet

#: The append-only tables the seed + correction paths write; truncated for a
#: deterministic state (same isolation convention as test_claim_sink.py).
_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "claim",
    "assertion_quarantine",
    "extraction",
    "ingest_run_capture",
    "ingest_run",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "organization",
    "source_registry",
    "rights_record",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """A spine truncated to a deterministic empty state, restored on exit."""
    dsn = _dsn(sig_database)
    sql = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql)


def _seed_legacy(dsn: str) -> None:
    """Write the pre-P32.3 records exactly as the early slice emitted them —
    unscoped counts, journalism genre on the 299, the 190-as-source figure."""
    from db.claim_sink import PgClaimSink

    sink = PgClaimSink.from_dsn(
        dsn, connector_name="okc-seed-legacy", connector_version="1.0.0", code_commit="p21.4-legacy"
    )
    sink.assert_claims([dict(r) for r in _LEGACY_CLAIMS])
    assert sink.report.inserted == len(_LEGACY_CLAIMS)
    assert sink.report.quarantined == 0


def _claim_rows(dsn: str) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, autocommit=True, row_factory=psycopg.rows.dict_row) as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT claim_id::text, content_digest, revises_claim::text,"
                " correction_reason, upper_inf(sys_period) AS open, value_num, value_text"
                " FROM claim ORDER BY lower(sys_period), claim_id"
            ).fetchall()
        ]


def test_correction_packet_applies_additively(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    packet = correction_packet()

    report = apply_packet(clean_dsn, packet)
    assert report["schema"] == "sig.seed-correction-report/1"
    outcomes = {c["correction_id"]: c for c in report["corrections"]}
    assert len(outcomes) == len(packet["corrections"])
    assert all(c["outcome"] == "applied" for c in outcomes.values())

    rows = _claim_rows(clean_dsn)
    # 5 legacy + 5 replacements — nothing deleted.
    assert len(rows) == len(_LEGACY_CLAIMS) * 2
    legacy_open = [r for r in rows if r["revises_claim"] is None]
    replacements = [r for r in rows if r["revises_claim"] is not None]
    assert len(legacy_open) == len(replacements) == len(_LEGACY_CLAIMS)
    # §16.6: every legacy row's belief window closed; the row still exists.
    assert not any(r["open"] for r in legacy_open)
    assert all(r["open"] for r in replacements)
    # The claim_correction_reasoned CHECK: revises_claim ⇒ correction_reason.
    assert all(r["correction_reason"] for r in replacements)
    # Each replacement names the claim it revises.
    assert {r["revises_claim"] for r in replacements} == {r["claim_id"] for r in legacy_open}
    # 190 was never sourced: the corrected okc_council_statement claim asserts the literal ~100.
    nums = {r["value_num"] for r in replacements}
    assert 190 not in nums and 100 in nums


def test_replacement_qualifiers_declare_scope(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    apply_packet(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True, row_factory=psycopg.rows.dict_row) as conn:
        quals = [
            dict(r)
            for r in conn.execute(
                "SELECT c.revises_claim::text AS revises, q.qualifier_id, q.value_text"
                " FROM claim_qualifier q JOIN claim c ON c.claim_id = q.claim_id"
                " WHERE c.revises_claim IS NOT NULL"
            ).fetchall()
        ]
    by_revision: dict[str, dict[str, str]] = {}
    for q in quals:
        by_revision.setdefault(str(q["revises"]), {})[q["qualifier_id"]] = q["value_text"]
    # Every corrected count declares its universe + fixture origin.
    assert len(by_revision) == len(_LEGACY_CLAIMS)
    for quals_for in by_revision.values():
        assert "count_scope" in quals_for
        assert quals_for.get("evidence_origin") == "seed_fixture"
    scopes = {q["value_text"] for q in quals if q["qualifier_id"] == "count_scope"}
    assert scopes == {"metro", "city_limits"}


def test_odbl_compartment_preserved(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    apply_packet(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True, row_factory=psycopg.rows.dict_row) as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT r.spdx_expression, c.revises_claim::text AS revises"
                " FROM claim c JOIN rights_record r USING (rights_id)"
                " WHERE c.predicate_id = 'mapped_device_count'"
            ).fetchall()
        ]
    # Both the closed OSM row and its correction stay in the ODbL compartment.
    assert {r["spdx_expression"] for r in rows} == {"ODbL-1.0"}
    assert len(rows) == 2


def test_dry_run_writes_nothing(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    report = apply_packet(clean_dsn, dry_run=True)
    assert report["dry_run"] is True
    assert all(
        c["outcome"] == "would_apply" and c["matching_rows"] == 1 for c in report["corrections"]
    )
    rows = _claim_rows(clean_dsn)
    assert len(rows) == len(_LEGACY_CLAIMS)
    assert all(r["open"] for r in rows)  # nothing closed
    assert all(r["revises_claim"] is None for r in rows)


def test_apply_is_idempotent(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    apply_packet(clean_dsn)
    after_first = _claim_rows(clean_dsn)
    second = apply_packet(clean_dsn)
    outcomes = {c["correction_id"]: c["outcome"] for c in second["corrections"]}
    assert set(outcomes.values()) == {"already_applied"}
    after_second = _claim_rows(clean_dsn)
    # +0 rows on the re-apply: the closed rows stay closed, replacements dedupe.
    assert len(after_second) == len(after_first)


def test_missing_target_reports_no_target(clean_dsn: str) -> None:
    """A spine seeded post-P32.3 (already scoped) has no legacy rows — the
    packet must not invent targets."""
    report = apply_packet(clean_dsn)
    assert all(c["outcome"] == "no_target" for c in report["corrections"])
    assert _claim_rows(clean_dsn) == []


def test_derived_190_never_becomes_a_current_claim(clean_dsn: str) -> None:
    _seed_legacy(clean_dsn)
    packet = correction_packet()
    apply_packet(clean_dsn, packet)
    rows = _claim_rows(clean_dsn)
    # The legacy 190 row stays in history (closed, never deleted) — but no
    # CURRENT claim asserts it; every open claim is a corrected record.
    current = [r for r in rows if r["open"]]
    assert current and all(r["value_num"] != 190 for r in current)
    assert all(r["revises_claim"] is not None for r in current)
    # The label stays in the report as a labelled derivation.
    views = [d["view"]["label"] for d in packet["derived_labels"]]
    assert views == ["~190"]
