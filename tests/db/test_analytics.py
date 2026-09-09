# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §18 analytics boundary: Hive-partitioned Parquet on DuckDB.

These are the SIG-STORE-025/026/027/028/029 guards. They run entirely in-process
against DuckDB and a temp directory — no Postgres, no network — because the
boundary is a self-contained substrate. They assert: the bright line (no plate /
no name column, and join keys are real UUIDs) holds for the analytics store;
aggregates round-trip through Hive-partitioned Parquet; partitions join to the
graph by UUID + period ONLY; and each partition is content-addressed and cited by
a summary claim.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from db.analytics import (
    AGG_RULESET_VERSION,
    ANALYTICS_COLUMNS,
    JOIN_KEYS,
    AnalyticsRow,
    AnalyticsSchemaError,
    JoinKeyError,
    assert_analytics_schema,
    assert_join_keys,
    assert_no_name_or_plate_column,
    build_graph_join_sql,
    partition_artifact_id,
    partition_relative_path,
    project_aggregate,
    publish_aggregates,
    read_partitions_expr,
    register_partition_as_evidence,
    summary_claim_for_partition,
    write_partitions,
)
from db.suppression import SuppressionRationale

INST = SuppressionRationale.INSTITUTIONAL_CONDUCT
INDIV = SuppressionRationale.PROTECTS_INDIVIDUAL
CONTRACT = SuppressionRationale.CONTRACTUAL

# Real sig_entity_id UUIDs (entity.entity_id is uuidv7) — the join keys are UUIDs,
# never names (§18.3, SIG-STORE-028).
ORG_A = "0190a000-0000-7000-8000-00000000000a"
ORG_B = "0190a000-0000-7000-8000-00000000000b"
ORG_C = "0190a000-0000-7000-8000-00000000000c"
ORG_Z = "0190a000-0000-7000-8000-00000000000f"


def _published(**kw: object) -> AnalyticsRow:
    base: dict[str, object] = dict(
        searching_org_id=ORG_A,
        source_org_id=ORG_B,
        period="2026-07",
        count=12,
        reason_category="criminal_investigation",
        audit_source_type="organization_audit",
        coverage_period="2026-06..2026-07",
        suppressed_flag=False,
        ingest_run_id="run-1",
    )
    base.update(kw)
    return AnalyticsRow(**base)  # type: ignore[arg-type]


# --- the bright line for the analytics store (SIG-STORE-025/026/028) ----------


def test_analytics_schema_honours_the_bright_line() -> None:
    # SIG-STORE-026/028: no plate-capable column, no name column, and the UUID +
    # period + lineage columns are present.
    assert_analytics_schema()
    assert JOIN_KEYS == {"searching_org_id", "source_org_id", "period"}


def test_no_analytics_column_is_a_name_or_plate_column() -> None:
    # The whole published schema must be name-free and plate-free.
    assert_no_name_or_plate_column(ANALYTICS_COLUMNS)


@pytest.mark.parametrize(
    "column",
    [
        "plate",
        "license_plate",
        "plate_number",
        "vrm",
        "searching_org_name",
        "org_name",
        # the connector's textual org identifiers must never become columns
        "searching_org",
        "source_org",
    ],
)
def test_plate_or_name_columns_are_rejected(column: str) -> None:
    with pytest.raises(AnalyticsSchemaError):
        assert_no_name_or_plate_column([column])


def test_schema_missing_a_uuid_or_lineage_column_is_rejected() -> None:
    with pytest.raises(AnalyticsSchemaError):
        assert_analytics_schema(["period", "count"])  # no UUIDs, no ingest_run_id


# --- AnalyticsRow invariants (SIG-STORE-028/030/031) --------------------------


def test_join_key_values_must_be_uuids_never_names() -> None:
    # SIG-STORE-028: "never via names" is a data guarantee — a textual name cannot
    # masquerade as a join key.
    with pytest.raises(AnalyticsSchemaError):
        _published(searching_org_id="City PD")
    with pytest.raises(AnalyticsSchemaError):
        _published(source_org_id="State Network")


def test_audit_source_type_must_be_one_of_the_four_types() -> None:
    with pytest.raises(AnalyticsSchemaError):
        _published(audit_source_type="made_up_audit")


def test_suppressed_row_must_publish_null_never_a_count() -> None:
    with pytest.raises(AnalyticsSchemaError):
        _published(suppressed_flag=True, count=3)


def test_published_row_must_carry_a_count() -> None:
    with pytest.raises(AnalyticsSchemaError):
        _published(suppressed_flag=False, count=None)


def test_unsuppressed_small_non_institutional_cell_is_refused() -> None:
    # Defence in depth: a small published cell is legitimate only for institutional
    # conduct; anything else is a suppression that should have happened upstream.
    with pytest.raises(AnalyticsSchemaError):
        _published(count=3, suppression_rationale=INDIV.value)


def test_institutional_small_cell_is_allowed_to_publish() -> None:
    row = _published(count=3, suppression_rationale=INST.value)
    assert row.count == 3


def test_contractual_suppression_must_cite_a_rights_record() -> None:
    with pytest.raises(AnalyticsSchemaError):
        _published(
            count=None, suppressed_flag=True, suppression_rationale=CONTRACT.value
        )  # no rights_record
    row = _published(
        count=None,
        suppressed_flag=True,
        suppression_rationale=CONTRACT.value,
        rights_record="rights:xyz",
    )
    assert row.to_row()["rights_record"] == "rights:xyz"


def test_row_period_must_be_month_granular() -> None:
    with pytest.raises(ValueError):
        _published(period="2026-07-15")


def test_row_columns_match_the_declared_schema_exactly() -> None:
    assert set(_published().to_row().keys()) == set(ANALYTICS_COLUMNS)


def test_suppressed_row_carries_flag_and_threshold() -> None:
    row = _published(count=None, suppressed_flag=True, suppression_rationale=INDIV.value)
    r = row.to_row()
    assert r["count"] is None
    assert r["suppressed_flag"] is True
    assert r["k_threshold"] == 5
    assert r["agg_ruleset_version"] == AGG_RULESET_VERSION


# --- projection drops names, keeps UUIDs, retains raw reason (SIG-STORE-028) ---


def test_project_aggregate_keys_on_uuids_and_drops_names() -> None:
    # A connector usage_aggregate row carries textual org identifiers; the analytics
    # projection keys on the RESOLVED UUIDs and never carries a name column.
    aggregate = {
        "searching_org": "City PD",  # a name — must not cross the boundary
        "source_org": "State Network",
        "period": "2026-07",
        "count": 12,
        "reason_category": "criminal_investigation",
        "reason_raw": "Criminal Investigation",  # the raw reason (§11.16 P2)
        "audit_source_type": "organization_audit",
        "coverage_period": "2026-06..2026-07",
        "search_scope": "state",
    }
    row = project_aggregate(
        aggregate,
        searching_org_id=ORG_A,
        source_org_id=ORG_B,
        ingest_run_id="run-1",
        suppressed_count=12,
        suppressed_flag=False,
        rationale=INST,
    )
    r = row.to_row()
    assert r["searching_org_id"] == ORG_A
    assert r["source_org_id"] == ORG_B
    assert "City PD" not in r.values()
    # §11.16 P2: the raw reason is retained beside the normalized category.
    assert r["reason_raw"] == "Criminal Investigation"
    assert r["reason_category"] == "criminal_investigation"
    assert_no_name_or_plate_column(r.keys())


def test_project_aggregate_carries_the_contractual_rights_record() -> None:
    aggregate = {
        "period": "2026-07",
        "reason_category": "licensed_use",
        "audit_source_type": "portal_public_audit",
        "coverage_period": "2026-07..2026-07",
    }
    row = project_aggregate(
        aggregate,
        searching_org_id=ORG_A,
        source_org_id=ORG_B,
        ingest_run_id="run-1",
        suppressed_count=None,
        suppressed_flag=True,
        rationale=CONTRACT,
        rights_record="rights:partner-licence",
    )
    assert row.to_row()["rights_record"] == "rights:partner-licence"


# --- Hive partition layout + round-trip (SIG-STORE-027) -----------------------


def test_partition_path_is_hive_key_value() -> None:
    assert (
        partition_relative_path("organization_audit", "2026-07")
        == "audit_source_type=organization_audit/period=2026-07"
    )


def test_partition_path_rejects_a_non_month_period() -> None:
    with pytest.raises(ValueError):
        partition_relative_path("organization_audit", "2026-07-15")


def test_partition_path_rejects_an_unknown_audit_source_type() -> None:
    with pytest.raises(AnalyticsSchemaError):
        partition_relative_path("bogus", "2026-07")


def test_aggregates_round_trip_through_hive_partitioned_parquet(tmp_path: Path) -> None:
    rows = [
        _published(source_org_id=ORG_B, period="2026-07", count=12),
        _published(
            source_org_id=ORG_C,
            period="2026-07",
            count=None,
            suppressed_flag=True,
            suppression_rationale=INDIV.value,
        ),
        _published(audit_source_type="network_audit", period="2026-08", count=7),
    ]
    con = duckdb.connect()
    artifacts = write_partitions(rows, tmp_path, con=con)

    # One partition per (audit_source_type, period); Hive key=value directories.
    paths = {a.relative_path for a in artifacts}
    assert any("audit_source_type=organization_audit/period=2026-07" in p for p in paths)
    assert any("audit_source_type=network_audit/period=2026-08" in p for p in paths)

    # Read back through DuckDB with hive partitioning; the partition keys reappear
    # and the suppressed NULL survives (never a zero).
    back = con.execute(
        "SELECT source_org_id, period, count, audit_source_type "
        f"FROM {read_partitions_expr(tmp_path)} ORDER BY period, source_org_id"
    ).fetchall()
    assert (ORG_B, "2026-07", 12, "organization_audit") in back
    assert (ORG_C, "2026-07", None, "organization_audit") in back
    assert (ORG_B, "2026-08", 7, "network_audit") in back


def test_written_partitions_are_content_addressed(tmp_path: Path) -> None:
    con = duckdb.connect()
    artifacts = write_partitions([_published()], tmp_path, con=con)
    assert len(artifacts) == 1
    art = artifacts[0]
    # A base32-lowercase multibase multihash (SIG-EVID-002 begins with 'b').
    assert art.digest.startswith("b")
    assert art.byte_size > 0
    assert art.row_count == 1
    # The bytes on disk reproduce the digest.
    from evidence.digest import verify

    data = (tmp_path / art.relative_path).read_bytes()
    assert verify(data, art.digest)


def test_write_tolerates_a_path_with_a_single_quote(tmp_path: Path) -> None:
    # The path is a SQL literal in COPY/read_parquet; a stray quote must not break
    # (or inject into) the statement.
    quoted = tmp_path / "o'brien"
    con = duckdb.connect()
    artifacts = write_partitions([_published()], quoted, con=con)
    assert artifacts and artifacts[0].row_count == 1
    back = con.execute(f"SELECT count(*) FROM {read_partitions_expr(quoted)}").fetchone()
    assert back[0] == 1


# --- the join: UUID + period only, never names (SIG-STORE-028) ----------------


def test_assert_join_keys_allows_uuid_and_period() -> None:
    assert assert_join_keys(["searching_org_id", "period"]) == ("searching_org_id", "period")
    assert assert_join_keys(["source_org_id"]) == ("source_org_id",)


@pytest.mark.parametrize("key", ["searching_org_name", "org_name", "name", "searching_org"])
def test_assert_join_keys_refuses_name_keys(key: str) -> None:
    with pytest.raises(JoinKeyError):
        assert_join_keys([key])


def test_empty_join_keys_are_refused() -> None:
    with pytest.raises(JoinKeyError):
        assert_join_keys([])


def test_join_sql_refuses_to_build_on_a_partition_name_key() -> None:
    with pytest.raises(JoinKeyError):
        build_graph_join_sql("part", "entities", keys=("searching_org_name",))


def test_join_sql_refuses_a_name_on_the_graph_side() -> None:
    # SIG-STORE-028: the graph column may not be a name either — the hazard is
    # symmetric.
    with pytest.raises(JoinKeyError):
        build_graph_join_sql("part", "entities", keys=("searching_org_id",), entity_key="name")


def test_join_sql_refuses_a_non_identifier_entity_source() -> None:
    with pytest.raises(JoinKeyError):
        build_graph_join_sql("part", "entities; DROP TABLE x", keys=("searching_org_id",))


def test_partitions_join_to_the_graph_by_uuid(tmp_path: Path) -> None:
    con = duckdb.connect()
    write_partitions(
        [
            _published(searching_org_id=ORG_A, period="2026-07", count=12),
            _published(searching_org_id=ORG_Z, period="2026-07", count=9),
        ],
        tmp_path,
        con=con,
    )
    con.execute("CREATE TABLE entities(entity_id VARCHAR, entity_type VARCHAR)")
    con.execute("INSERT INTO entities VALUES (?, 'organization')", [ORG_A])  # ORG_Z absent
    sql = build_graph_join_sql(
        read_partitions_expr(tmp_path), "entities", keys=("searching_org_id",)
    )
    joined = con.execute(sql).fetchall()
    # Only the row whose UUID resolves in the graph joins — a name join is impossible
    # because there is no name column to join on.
    assert len(joined) == 1


def test_join_carries_lineage_columns(tmp_path: Path) -> None:
    con = duckdb.connect()
    write_partitions([_published(ingest_run_id="run-42")], tmp_path, con=con)
    lineage = con.execute(
        f"SELECT DISTINCT ingest_run_id, agg_ruleset_version FROM {read_partitions_expr(tmp_path)}"
    ).fetchall()
    assert lineage == [("run-42", AGG_RULESET_VERSION)]


# --- partition-as-evidence + summary claims (SIG-STORE-029) -------------------


def test_partition_is_registered_as_an_evidence_artifact(tmp_path: Path) -> None:
    con = duckdb.connect()
    art = write_partitions([_published()], tmp_path, con=con)[0]
    ev = register_partition_as_evidence(art, ingest_run_id="run-1")
    assert ev["record_kind"] == "evidence_artifact"
    assert ev["content_digest"] == art.digest
    assert ev["subject_id"] == partition_artifact_id(art.digest)
    assert ev["media_type"].endswith("parquet")
    assert ev["byte_size"] == art.byte_size


def test_summary_claim_cites_the_partition_as_evidence(tmp_path: Path) -> None:
    con = duckdb.connect()
    art = write_partitions([_published()], tmp_path, con=con)[0]
    claim = summary_claim_for_partition(
        art,
        subject_id="usage:agg:A:B:2026-07",
        searching_org_id=ORG_A,
        source_org_id=ORG_B,
        period="2026-07",
        count=412,
        ingest_run_id="run-1",
    )
    assert claim["record_kind"] == "claim"
    # SIG-STORE-029: the claim cites exactly the partition bytes.
    assert claim["cites_partition_digest"] == art.digest
    assert claim["evidence_artifact_id"] == partition_artifact_id(art.digest)
    assert_no_name_or_plate_column(claim.keys())


def test_summary_claim_refuses_to_publish_a_small_count(tmp_path: Path) -> None:
    con = duckdb.connect()
    art = write_partitions([_published()], tmp_path, con=con)[0]
    with pytest.raises(AnalyticsSchemaError):
        summary_claim_for_partition(
            art,
            subject_id="s",
            searching_org_id=ORG_A,
            source_org_id=ORG_B,
            period="2026-07",
            count=3,  # small — must have been suppressed
            ingest_run_id="run-1",
        )


def test_publish_aggregates_writes_and_registers_in_one_call(tmp_path: Path) -> None:
    con = duckdb.connect()
    result = publish_aggregates(
        [
            _published(period="2026-07", count=12),
            _published(audit_source_type="network_audit", period="2026-08", count=7),
        ],
        tmp_path,
        ingest_run_id="run-9",
        con=con,
    )
    assert len(result.artifacts) == 2
    assert len(result.evidence_rows) == 2
    # Every partition has a matching evidence registration citing its digest.
    digests = {a.digest for a in result.artifacts}
    assert {e["content_digest"] for e in result.evidence_rows} == digests
    assert all(e["ingest_run_id"] == "run-9" for e in result.evidence_rows)


def test_summary_claim_uses_the_effective_partner_threshold(tmp_path: Path) -> None:
    # SIG-STORE-033: a partner's stricter k must be respected consistently. Under
    # k=10, a count of 8 is still small and may not be summarized.
    con = duckdb.connect()
    art = write_partitions([_published()], tmp_path, con=con)[0]
    with pytest.raises(AnalyticsSchemaError):
        summary_claim_for_partition(
            art,
            subject_id="s",
            searching_org_id=ORG_A,
            source_org_id=ORG_B,
            period="2026-07",
            count=8,
            ingest_run_id="run-1",
            k_threshold=10,
        )
