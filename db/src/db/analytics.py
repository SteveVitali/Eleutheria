# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The analytics boundary: Hive-partitioned Parquet on DuckDB (§18).

The high-volume usage aggregates (§11.16) do not belong in PostgreSQL. §18.2
places them **outside** the canonical store as **Hive-partitioned Parquet queried
by DuckDB** (SIG-STORE-027) — no columnar Postgres extension is adopted as
canonical. This module is that substrate.

Three properties make the boundary a *privacy* line, not merely a performance one:

* **The bright line (§18.1, SIG-STORE-025/026).** The analytics store carries no
  per-search or per-plate row and **no column capable of holding a licence plate**,
  and — because a name join would silently reintroduce the entity-resolution
  failure P6 exists to prevent — no name column at all. Every published row keys on
  ``sig_entity_id`` UUIDs and a month ``period``. :func:`assert_analytics_schema`
  is the schema test that enforces it.
* **The join (§18.3, SIG-STORE-028).** Partitions join to the graph **only** via
  ``searching_org_id`` / ``source_org_id`` UUIDs and ``period`` — never via names —
  and every row carries ``ingest_run_id`` and ``agg_ruleset_version`` for lineage.
  :func:`assert_join_keys` refuses any other join key.
* **Partition-as-evidence (§18.3, SIG-STORE-029).** Each written partition is
  content-addressed and registered as an evidence artifact; a *summary* claim
  ("agency X ran N searches in the month to …") is created only by citing that
  partition as its evidence, keeping the §10.1 provenance chain unbroken across the
  boundary.

Small-cell disclosure control (§18.4) lives in :mod:`db.suppression`; callers
suppress *before* projecting rows here, and this module refuses to write a small
published cell that is not institutional-conduct (a defence in depth).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
from evidence.digest import multihash

from .suppression import (
    DEFAULT_K_THRESHOLD,
    SuppressionRationale,
    assert_month_granularity,
    is_small_cell,
)

# The aggregation ruleset version stamped on every published row and summary claim
# (SIG-STORE-028). Bumped as a versioned migration when the projection rules change.
AGG_RULESET_VERSION = "2026.09.01"

# The published analytics-store columns, in order, with their DuckDB types. This is
# the whole schema — it carries UUIDs + period + the aggregate facts, and
# deliberately NO name column and NO plate-capable column (§18.1, SIG-STORE-026/028).
ANALYTICS_COLUMNS: dict[str, str] = {
    "searching_org_id": "VARCHAR",  # sig_entity_id UUID — the join key, never a name
    "source_org_id": "VARCHAR",  # sig_entity_id UUID — the join key, never a name
    "period": "VARCHAR",  # YYYY-MM month (§18.4); a Hive partition key
    "count": "INTEGER",  # NULL when suppressed — never zero (SIG-STORE-030)
    "search_scope": "VARCHAR",
    "reason_category": "VARCHAR",  # normalized (§11.16)
    "reason_raw": "VARCHAR",  # the raw reason the category was derived from (§11.16 P2)
    "audit_source_type": "VARCHAR",  # a Hive partition key; the four non-interchangeable types
    "coverage_period": "VARCHAR",
    "suppressed_flag": "BOOLEAN",  # SIG-STORE-030
    "k_threshold": "INTEGER",  # the k that applied (SIG-STORE-030/033)
    "suppression_rationale": "VARCHAR",  # which §18.4 rationale applied (SIG-STORE-031)
    "rights_record": "VARCHAR",  # cited when a contractual suppression applied (§18.4)
    "ingest_run_id": "VARCHAR",  # lineage (SIG-STORE-028)
    "agg_ruleset_version": "VARCHAR",  # lineage (SIG-STORE-028)
}

# The four non-interchangeable audit source types (§11.16, §23.7). Duplicated here
# (the connector owns its own copy as versioned data) so the analytics layer can
# reject an unknown/injected value WITHOUT importing `connectors` — that would be a
# dependency cycle (connectors depends on db). This is spec-level vocabulary, not
# connector policy.
AUDIT_SOURCE_TYPES: frozenset[str] = frozenset(
    {"organization_audit", "network_audit", "portal_public_audit", "event_log"}
)

# The Hive partition keys. Partitioning by (audit_source_type, period) keeps the
# four non-interchangeable audit types (§23.7) in separate partitions and makes the
# month the coarsest-grain pruning key (§18.4).
PARTITION_KEYS: tuple[str, ...] = ("audit_source_type", "period")

# The ONLY columns a partition may be joined to the graph on (§18.3, SIG-STORE-028):
# the two entity-id UUIDs and the period. Never a name.
JOIN_KEYS: frozenset[str] = frozenset({"searching_org_id", "source_org_id", "period"})

# The Parquet media type registered on a partition evidence artifact.
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"

# Bright-line token guards (mirror tests/db/test_schema_integrity.py): a name
# column would reopen the §18.3 name-join hazard; a plate column is the §18.1 leak.
_NAME_TOKENS = frozenset({"name"})
_PLATE_TOKENS = frozenset({"plate", "vrm"})
_PLATE_PHRASES = ("license_plate", "licence_plate", "plate_number", "plate_no")
# The connector's textual org-identifier columns (`searching_org` / `source_org`,
# audit_structural.py). They must NEVER become analytics columns — the store keys on
# the resolved `*_id` UUIDs — so they are rejected by exact name even though they
# carry no `name` token (§18.3, SIG-STORE-028).
_FORBIDDEN_EXACT_COLUMNS = frozenset({"searching_org", "source_org"})
# A safe SQL identifier (a relation/table name interpolated into a query).
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


class AnalyticsSchemaError(Exception):
    """A bright-line violation in the analytics store (§18.1/§18.3)."""


class JoinKeyError(Exception):
    """An attempt to join a partition to the graph on a forbidden key (§18.3)."""


def _tokens(name: str) -> set[str]:
    return set(re.split(r"[_.]", name.lower()))


def _sql_string_literal(value: str) -> str:
    """A single-quoted SQL string literal with embedded quotes escaped.

    DuckDB's ``COPY … TO 'path'`` and ``read_parquet('glob')`` take a literal, not
    a bind parameter, so a path is escaped here rather than parameterised. A stray
    quote would otherwise terminate the literal and let arbitrary SQL follow.
    """
    return "'" + value.replace("'", "''") + "'"


def assert_no_name_or_plate_column(columns: Iterable[str]) -> None:
    """Assert no column can hold a plate or be used as a name join key.

    Token-based, not substring (so ``template`` is fine but ``plate`` is not).
    A plate column is the §18.1 leak (SIG-STORE-026); a name column — including the
    connector's textual ``searching_org`` / ``source_org`` identifiers — would let
    the partition be joined to the graph by name, the §18.3 hazard (SIG-STORE-028).
    """
    for column in columns:
        toks = _tokens(column)
        lowered = column.lower()
        if (_PLATE_TOKENS & toks) or any(p in lowered for p in _PLATE_PHRASES):
            raise AnalyticsSchemaError(
                f"analytics column {column!r} is plate-capable (§18.1, SIG-STORE-026)"
            )
        if (_NAME_TOKENS & toks) or lowered in _FORBIDDEN_EXACT_COLUMNS:
            raise AnalyticsSchemaError(
                f"analytics column {column!r} is a name column; partitions join by "
                f"UUID + period only, never by name (§18.3, SIG-STORE-028)"
            )


def assert_entity_uuid(value: str, *, field: str) -> str:
    """Return ``value`` if it is a ``sig_entity_id`` UUID, else raise (SIG-STORE-028).

    The join keys are ``sig_entity_id`` UUIDs (``entity.entity_id`` is ``uuidv7``).
    Validating them as UUIDs at the boundary is what makes "never via names"
    (§18.3) a data guarantee, not just a schema one: a textual org name (e.g.
    "City PD") cannot masquerade as a join key.
    """
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise AnalyticsSchemaError(
            f"{field} must be a sig_entity_id UUID, never a name (§18.3, "
            f"SIG-STORE-028); got {value!r}"
        ) from None
    return value


def assert_audit_source_type(value: str) -> str:
    """Return ``value`` if it is one of the four §11.16 audit source types, else raise.

    The four types are non-interchangeable and closed (§11.16, §23.7); an unknown
    or injected value must not reach a Hive partition path or the ``COPY`` SQL.
    """
    if value not in AUDIT_SOURCE_TYPES:
        raise AnalyticsSchemaError(
            f"audit_source_type {value!r} is not one of the four §11.16 types "
            f"{sorted(AUDIT_SOURCE_TYPES)}"
        )
    return value


def assert_analytics_schema(columns: Iterable[str] = tuple(ANALYTICS_COLUMNS)) -> None:
    """Assert the analytics-store schema honours the bright line (SIG-STORE-025/026/028).

    Runs the plate/name guard and confirms the UUID join keys and lineage columns
    are present. This is the schema test the analytics store must always pass.
    """
    cols = list(columns)
    assert_no_name_or_plate_column(cols)
    required = {
        "searching_org_id",
        "source_org_id",
        "period",
        "ingest_run_id",
        "agg_ruleset_version",
    }
    missing = required - set(cols)
    if missing:
        raise AnalyticsSchemaError(
            f"analytics schema is missing required UUID/lineage columns {sorted(missing)} "
            f"(§18.3, SIG-STORE-028)"
        )


@dataclass(frozen=True)
class AnalyticsRow:
    """One published usage-aggregate row in the analytics store (§11.16, §18).

    Keys on ``searching_org_id`` / ``source_org_id`` (sig_entity_id UUIDs — the
    §18.3 join keys, never names) and a month ``period``. ``count`` is ``None`` when
    the cell is suppressed (never zero, SIG-STORE-030). Carries ``ingest_run_id``
    and ``agg_ruleset_version`` for the §18.3 lineage.
    """

    searching_org_id: str
    source_org_id: str
    period: str
    count: int | None
    reason_category: str
    audit_source_type: str
    coverage_period: str
    suppressed_flag: bool
    ingest_run_id: str
    k_threshold: int = DEFAULT_K_THRESHOLD
    search_scope: str | None = None
    reason_raw: str | None = None
    suppression_rationale: str | None = None
    rights_record: str | None = None
    agg_ruleset_version: str = AGG_RULESET_VERSION

    def __post_init__(self) -> None:
        assert_entity_uuid(self.searching_org_id, field="searching_org_id")
        assert_entity_uuid(self.source_org_id, field="source_org_id")
        assert_audit_source_type(self.audit_source_type)
        assert_month_granularity(self.period)
        if (
            self.suppression_rationale == SuppressionRationale.CONTRACTUAL.value
            and not self.rights_record
        ):
            raise AnalyticsSchemaError(
                "a contractual suppression must cite a rights record (§18.4, SIG-STORE-031)"
            )
        if self.suppressed_flag and self.count is not None:
            raise AnalyticsSchemaError(
                f"a suppressed cell must publish count=None, never a value "
                f"(SIG-STORE-030); got {self.count!r}"
            )
        if not self.suppressed_flag and self.count is None:
            raise AnalyticsSchemaError("a published cell must carry a count (SIG-STORE-030)")
        # Defence in depth: a small *published* cell is only legitimate for
        # institutional conduct (§18.4). Anything else is a suppression that did not
        # happen upstream, and must never reach the store.
        if (
            not self.suppressed_flag
            and self.count is not None
            and is_small_cell(self.count, self.k_threshold)
            and self.suppression_rationale != SuppressionRationale.INSTITUTIONAL_CONDUCT.value
        ):
            raise AnalyticsSchemaError(
                f"unsuppressed small cell (count={self.count} < k={self.k_threshold}) with "
                f"rationale {self.suppression_rationale!r}; only institutional_conduct small "
                f"counts may publish (§18.4, SIG-STORE-030/031/032)"
            )

    def to_row(self) -> dict[str, Any]:
        """The ordered analytics-store row (keys are exactly :data:`ANALYTICS_COLUMNS`)."""
        return {
            "searching_org_id": self.searching_org_id,
            "source_org_id": self.source_org_id,
            "period": self.period,
            "count": self.count,
            "search_scope": self.search_scope,
            "reason_category": self.reason_category,
            "reason_raw": self.reason_raw,
            "audit_source_type": self.audit_source_type,
            "coverage_period": self.coverage_period,
            "suppressed_flag": self.suppressed_flag,
            "k_threshold": self.k_threshold,
            "suppression_rationale": self.suppression_rationale,
            "rights_record": self.rights_record,
            "ingest_run_id": self.ingest_run_id,
            "agg_ruleset_version": self.agg_ruleset_version,
        }


def project_aggregate(
    aggregate: Mapping[str, Any],
    *,
    searching_org_id: str,
    source_org_id: str,
    ingest_run_id: str,
    suppressed_count: int | None,
    suppressed_flag: bool,
    rationale: SuppressionRationale,
    k_threshold: int = DEFAULT_K_THRESHOLD,
    rights_record: str | None = None,
) -> AnalyticsRow:
    """Project a connector ``usage_aggregate`` row into an :class:`AnalyticsRow`.

    The connector (``connectors.audit_structural``) emits rows keyed on textual
    org identifiers; the analytics store keys on the **resolved** ``sig_entity_id``
    UUIDs, which the caller supplies (this module never touches the resolver, and
    deliberately DROPS any name-bearing field so it cannot cross the boundary,
    §18.3). ``suppressed_count`` / ``suppressed_flag`` / ``rationale`` /
    ``rights_record`` are the :func:`db.suppression.suppress_group` verdict for this
    cell; the raw reason is retained beside the normalized category (§11.16 P2).
    """
    raw = aggregate.get("reason_raw")
    return AnalyticsRow(
        searching_org_id=searching_org_id,
        source_org_id=source_org_id,
        period=str(aggregate["period"]),
        count=suppressed_count,
        reason_category=str(aggregate.get("reason_category", "unspecified")),
        reason_raw=(None if raw is None else str(raw)),
        audit_source_type=str(aggregate["audit_source_type"]),
        coverage_period=str(aggregate.get("coverage_period", "unknown")),
        suppressed_flag=suppressed_flag,
        ingest_run_id=ingest_run_id,
        k_threshold=k_threshold,
        search_scope=(
            None if aggregate.get("search_scope") is None else str(aggregate["search_scope"])
        ),
        suppression_rationale=rationale.value,
        rights_record=rights_record,
    )


def partition_relative_path(audit_source_type: str, period: str) -> str:
    """The Hive partition directory for a ``(audit_source_type, period)`` (SIG-STORE-027).

    Hive style ``key=value`` segments, in :data:`PARTITION_KEYS` order, so any
    Hive-aware reader (DuckDB, Spark, Arrow) prunes on them without SIG's code. Both
    keys are validated so an injected value cannot corrupt the path or the SQL.
    """
    assert_audit_source_type(audit_source_type)
    assert_month_granularity(period)
    return f"audit_source_type={audit_source_type}/period={period}"


@dataclass(frozen=True)
class PartitionArtifact:
    """A written Parquet partition, content-addressed for evidence (SIG-STORE-029)."""

    relative_path: str
    audit_source_type: str
    period: str
    digest: str  # multihash of the partition bytes (SIG-EVID-002)
    byte_size: int
    row_count: int


def _hive_value(segment: str, key: str) -> str:
    prefix = f"{key}="
    if not segment.startswith(prefix):
        raise AnalyticsSchemaError(f"malformed Hive segment {segment!r} (expected {prefix}…)")
    return segment[len(prefix) :]


def write_partitions(
    rows: Sequence[AnalyticsRow],
    root: str | Path,
    *,
    con: Any | None = None,
) -> list[PartitionArtifact]:
    """Write ``rows`` as Hive-partitioned Parquet under ``root`` (SIG-STORE-027).

    Uses DuckDB's partitioned ``COPY`` (no columnar Postgres extension, §18.2):
    partitions land at ``audit_source_type=…/period=…/`` and each written file is
    content-addressed into a :class:`PartitionArtifact` for §18.3 evidence
    registration. Rows are validated against the bright line before any bytes are
    written. Returns the artifacts, sorted by path (deterministic).
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    assert_analytics_schema()  # the store schema honours §18.1/§18.3
    payload = [r.to_row() for r in rows]
    for row in payload:
        assert_no_name_or_plate_column(row.keys())

    owns_con = con is None
    con = con if con is not None else duckdb.connect()
    try:
        col_defs = ", ".join(f'"{name}" {typ}' for name, typ in ANALYTICS_COLUMNS.items())
        con.execute("DROP TABLE IF EXISTS _agg_out")
        con.execute(f"CREATE TABLE _agg_out ({col_defs})")
        placeholders = ", ".join("?" for _ in ANALYTICS_COLUMNS)
        con.executemany(
            f"INSERT INTO _agg_out VALUES ({placeholders})",
            [tuple(row[name] for name in ANALYTICS_COLUMNS) for row in payload],
        )
        part_by = ", ".join(PARTITION_KEYS)
        con.execute(
            f"COPY (SELECT * FROM _agg_out) TO {_sql_string_literal(root.as_posix())} "
            f"(FORMAT PARQUET, PARTITION_BY ({part_by}), OVERWRITE_OR_IGNORE)"
        )
        con.execute("DROP TABLE _agg_out")
        return _collect_partition_artifacts(root, con)
    finally:
        if owns_con:
            con.close()


def _collect_partition_artifacts(root: Path, con: Any) -> list[PartitionArtifact]:
    artifacts: list[PartitionArtifact] = []
    for path in sorted(root.rglob("*.parquet")):
        rel = path.relative_to(root)
        segments = rel.parts
        # …/audit_source_type=x/period=y/<file>.parquet
        audit_source_type = _hive_value(segments[-3], "audit_source_type")
        period = _hive_value(segments[-2], "period")
        data = path.read_bytes()
        row_count = int(
            con.execute("SELECT count(*) FROM read_parquet(?)", [path.as_posix()]).fetchone()[0]
        )
        artifacts.append(
            PartitionArtifact(
                relative_path=rel.as_posix(),
                audit_source_type=audit_source_type,
                period=period,
                digest=multihash(data),
                byte_size=len(data),
                row_count=row_count,
            )
        )
    return artifacts


# --- the join (§18.3, SIG-STORE-028) ------------------------------------------


def assert_join_keys(keys: Iterable[str]) -> tuple[str, ...]:
    """Return ``keys`` if every one is a UUID or period join key, else raise.

    §18.3 (SIG-STORE-028): partitions join to the graph ONLY via ``sig_entity_id``
    UUIDs and ``period``. A name key would reintroduce, invisibly, the
    entity-resolution failure P6 prevents. Allowed keys are exactly
    :data:`JOIN_KEYS`; any other — especially a name column — is a hard error.
    """
    resolved = tuple(keys)
    if not resolved:
        raise JoinKeyError("a partition join needs at least one key (§18.3)")
    for key in resolved:
        if key in JOIN_KEYS:
            continue
        toks = _tokens(key)
        if _NAME_TOKENS & toks:
            raise JoinKeyError(
                f"refusing to join partitions on name column {key!r}; UUID + period only "
                f"(§18.3, SIG-STORE-028)"
            )
        raise JoinKeyError(
            f"{key!r} is not a permitted partition join key; allowed: {sorted(JOIN_KEYS)} "
            f"(§18.3, SIG-STORE-028)"
        )
    return resolved


def _assert_graph_join_column(column: str) -> str:
    """Return ``column`` if it is a graph-side id/period join column, else raise.

    The graph is joined on its entity-id UUID column (``entity_id`` / ``*_id``) or
    ``period`` — never on a name column, which would reopen the §18.3 name-join
    hazard from the graph side (SIG-STORE-028).
    """
    if not _SQL_IDENTIFIER.match(column):
        raise JoinKeyError(f"entity_key must be a plain SQL identifier, got {column!r} (§18.3)")
    if _NAME_TOKENS & _tokens(column):
        raise JoinKeyError(
            f"refusing to join the graph on name column {column!r}; id/period only "
            f"(§18.3, SIG-STORE-028)"
        )
    if not (column == "period" or column == "id" or column.endswith("_id")):
        raise JoinKeyError(
            f"entity_key {column!r} is not an id or period column; the graph joins on "
            f"its entity-id UUID or period only (§18.3, SIG-STORE-028)"
        )
    return column


def build_graph_join_sql(
    partition_source: str,
    entity_source: str,
    *,
    keys: Sequence[str] = ("searching_org_id",),
    entity_key: str = "entity_id",
) -> str:
    """Build the DuckDB SQL joining partitions to the graph by UUID + period only.

    ``partition_source`` is a ``read_parquet(...)`` expression (e.g. from
    :func:`read_partitions_expr`, whose path is escaped); ``entity_source`` is a
    graph relation exposing ``entity_key``. ``keys`` are validated by
    :func:`assert_join_keys` and ``entity_key`` by :func:`assert_join_keys` too, so
    **neither side** can join on a name (§18.3): the partition column is a validated
    UUID/period key, and the graph column is an id/period column, never ``name``.
    ``entity_source`` must be a plain SQL identifier.
    """
    assert_join_keys(keys)
    _assert_graph_join_column(entity_key)  # the graph-side column may not be a name either
    if not _SQL_IDENTIFIER.match(entity_source):
        raise JoinKeyError(
            f"entity_source must be a plain SQL identifier, got {entity_source!r} (§18.3)"
        )
    conditions: list[str] = []
    for key in keys:
        if key == "period":
            conditions.append("a.period = e.period")
        else:
            conditions.append(f"a.{key} = e.{entity_key}")
    on = " AND ".join(conditions)
    return f"SELECT a.* FROM {partition_source} a JOIN {entity_source} e ON {on}"


def read_partitions_expr(root: str | Path) -> str:
    """A DuckDB ``read_parquet`` expression over all partitions under ``root``.

    Hive partitioning is enabled so ``audit_source_type`` and ``period`` are read
    back as columns from the directory names.
    """
    glob = (Path(root) / "**" / "*.parquet").as_posix()
    return f"read_parquet({_sql_string_literal(glob)}, hive_partitioning=1)"


# --- partition-as-evidence + summary claims (§18.3, SIG-STORE-029) ------------


def partition_artifact_id(digest: str) -> str:
    """The stable evidence-artifact id for a partition, keyed on its digest."""
    return f"analytics:partition:{digest}"


def register_partition_as_evidence(
    artifact: PartitionArtifact,
    *,
    ingest_run_id: str,
) -> dict[str, Any]:
    """An ``evidence_artifact`` row registering a partition with its digest (SIG-STORE-029).

    The partition is content-addressed (``content_digest`` is a multihash,
    SIG-EVID-002), so a summary claim can cite exactly these bytes and the §10.1
    provenance chain stays unbroken across the boundary.
    """
    return {
        "record_kind": "evidence_artifact",
        "subject_id": partition_artifact_id(artifact.digest),
        "predicate_id": "analytics_partition",
        "content_digest": artifact.digest,
        "media_type": PARQUET_MEDIA_TYPE,
        "byte_size": artifact.byte_size,
        "row_count": artifact.row_count,
        "relative_path": artifact.relative_path,
        "audit_source_type": artifact.audit_source_type,
        "period": artifact.period,
        "ingest_run_id": ingest_run_id,
        "agg_ruleset_version": AGG_RULESET_VERSION,
        "raw_value": artifact.relative_path,
    }


def summary_claim_for_partition(
    artifact: PartitionArtifact,
    *,
    subject_id: str,
    searching_org_id: str,
    source_org_id: str,
    period: str,
    count: int,
    ingest_run_id: str,
    reason_category: str | None = None,
    k_threshold: int = DEFAULT_K_THRESHOLD,
) -> dict[str, Any]:
    """A summary claim about a partition, citing the partition as its evidence (SIG-STORE-029).

    §18.3: a claim is created only when SIG asserts a *summary statement* about a
    partition — e.g. "agency X performed 412 searches in the 30 days to …" — and
    that claim MUST cite the partition (``cites_partition_digest``). The claim keys
    on UUIDs + period, never names (§18.3), and never on a suppressed (small) count —
    ``k_threshold`` is the effective k (a partner's stricter threshold, SIG-STORE-033),
    so the small-count check stays consistent with the suppression layer.
    """
    assert_entity_uuid(searching_org_id, field="searching_org_id")
    assert_entity_uuid(source_org_id, field="source_org_id")
    assert_month_granularity(period)
    if is_small_cell(count, k_threshold):
        raise AnalyticsSchemaError(
            f"a summary claim must not publish a small count (count={count} < "
            f"k={k_threshold}); suppress it first (§18.4, SIG-STORE-030)"
        )
    return {
        "record_kind": "claim",
        "subject_id": subject_id,
        "predicate_id": "usage_search_aggregate_summary",
        "searching_org_id": searching_org_id,
        "source_org_id": source_org_id,
        "period": period,
        "reason_category": reason_category,
        "count": count,
        "value_kind": "value",
        "raw_value": count,
        # The §10.1 citation across the boundary: the summary is evidenced by the
        # content-addressed partition, not by a re-derivation.
        "cites_partition_digest": artifact.digest,
        "evidence_artifact_id": partition_artifact_id(artifact.digest),
        "ingest_run_id": ingest_run_id,
        "agg_ruleset_version": AGG_RULESET_VERSION,
    }


@dataclass(frozen=True)
class PublishedPartitions:
    """The result of publishing a batch of aggregates to the analytics store."""

    artifacts: tuple[PartitionArtifact, ...]
    evidence_rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def publish_aggregates(
    rows: Sequence[AnalyticsRow],
    root: str | Path,
    *,
    ingest_run_id: str,
    con: Any | None = None,
) -> PublishedPartitions:
    """Write ``rows`` and register every partition as evidence in one call (§18.3).

    The end-to-end boundary operation: it writes the Hive-partitioned Parquet
    (SIG-STORE-027) and returns each partition both as a :class:`PartitionArtifact`
    and as an ``evidence_artifact`` row (SIG-STORE-029), so a caller can persist the
    partitions and their evidence registrations together, then mint summary claims
    that cite them (:func:`summary_claim_for_partition`).
    """
    artifacts = write_partitions(rows, root, con=con)
    evidence_rows = tuple(
        register_partition_as_evidence(a, ingest_run_id=ingest_run_id) for a in artifacts
    )
    return PublishedPartitions(artifacts=tuple(artifacts), evidence_rows=evidence_rows)
