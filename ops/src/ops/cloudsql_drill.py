# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Cloud SQL restore drill at scale (P34.6 / SIG-OPS-001, ADR-175).

The drill proves the production spine restorable at scale: a point-in-time
``gcloud sql instances clone`` of ``sig-pg`` into a disposable
``sig-pg-drill-<STAMP>`` instance, then *append-only row-count parity at the
restore point T* — the same comparison on both instances through the Cloud SQL
Auth Proxy — plus ``sqitch.changes`` tip equality and PostGIS presence, with
RTO (clone start → verified) and RPO (T vs the newest recorded instant)
measured. The shell half (``ops/gcp/restore-drill.sh``) owns gcloud and the
proxy; this module owns the SQL surface and the drill record so both are
unit-testable without credentials, network or Docker — ``connect`` is
injectable (``ops/backup.py``'s runner pattern, P24.1).

Two hard rules encoded here:

- **The delete is name-checked.** ``assert_drill_name`` accepts only the
  producer's own shape ``sig-pg-drill-<STAMP>`` / ``sig-pg-drill-b-<STAMP>``
  (``<STAMP>`` = ``%Y%m%dt%H%Mz``) and refuses ``sig-pg`` itself outright — a
  deletion command built from it can never name production.
- **The drill reads plan state only (C-10).** The sqitch comparison reads
  ``sqitch.changes``; nothing here touches ``db/sqitch.plan`` lines 44–52,
  and D-P32.10a-1's ``sqitch verify`` division-by-zero is a *verify-command*
  defect — never to be mistaken for a restore failure.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

#: The drill instance names this module will ever bless. ``sig-pg`` itself
#: does not match (it lacks the ``-drill-`` infix); the pattern is deliberately
#: tighter than the contract's ``sig-pg-drill-*`` wildcard — only the stamp
#: shape the producer emits is deletable, so a hand-typed or truncated name
#: fails closed. ``-b-`` marks the full-backup variant's instance (leg 3).
# lowercase t/z — Cloud SQL instance names allow [a-z0-9-] only (found by
# the 2026-10-02 live leg: %Y%m%dT%H%MZ made an INVALID_ARGUMENT submit).
DRILL_INSTANCE_RE = re.compile(r"^sig-pg-drill(?:-b)?-[0-9]{8}t[0-9]{4}z$")

#: The production instance name — refused explicitly before the pattern is
#: even consulted, so the refusal is a distinct, greppable message.
PRODUCTION_INSTANCE = "sig-pg"

#: The contract's spine table list → the per-table instant expression used for
#: "rows existing at T". The expressions mirror the spine_watermark facet map
#: in ``db/deploy/shared_temporal_contract.sql`` (P32.4/ADR-123) — the same
#: columns the watermark triggers bump on. ``None`` means the table carries no
#: commit-time instant column (``evidence_artifact``); parity there is a plain
#: total count on both sides, recorded with ``bounded_by_t: false``.
DRILL_TABLES: Mapping[str, str | None] = {
    "claim": "lower(sys_period)",
    "claim_evidence": "bound_at",
    "evidence_capture": "retrieved_at",
    "evidence_artifact": None,
    "entity": "created_at",
    "ingest_run": "coalesce(finished_at, started_at)",
    "ingest_run_completion": "recorded_at",
    "resolution": "lower(sys_period)",
    "contradiction": "resolved_at",
    "coverage_record": "searched_at",
}

#: The columns each instant expression reads. The deployed spine may predate
#: the shared_temporal_contract migration (P32.4) — production sat at the
#: P31.11 tip when the 2026-10-02 live leg ran, so ``claim_evidence.bound_at``
#: and ``spine_watermark`` did not exist there. The drill never invents a
#: predicate the schema cannot answer: a missing instant column (or a missing
#: table) degrades that facet to the unbounded count, recorded honestly via
#: ``instant: null`` / ``present: false`` — and the *effective* map is compared
#: between source and clone, so a schema-drifted clone is itself a DRIFT.
DRILL_INSTANT_COLUMNS: Mapping[str, tuple[str, ...]] = {
    "claim": ("sys_period",),
    "claim_evidence": ("bound_at",),
    "evidence_capture": ("retrieved_at",),
    "evidence_artifact": (),
    "entity": ("created_at",),
    "ingest_run": ("finished_at", "started_at"),
    "ingest_run_completion": ("recorded_at",),
    "resolution": ("sys_period",),
    "contradiction": ("resolved_at",),
    "coverage_record": ("searched_at",),
}

#: Bookkeeping table compared verbatim when present; absent on a
#: pre-shared_temporal_contract spine (``None`` on both sides is still parity).
WATERMARK_TABLE = "spine_watermark"

#: RPO is measured on ``claim`` — the append-only spine head whose instant the
#: watermark also tracks (``latest_instant`` = max(lower(sys_period))).
RPO_INSTANT_SQL = "SELECT max(lower(sys_period)) FROM claim"


class DrillNameError(ValueError):
    """A drill-instance name outside the blessed ``sig-pg-drill-*`` shape."""


def assert_drill_name(name: str) -> str:
    """Return ``name`` iff it is a drill instance; refuse anything else.

    Refuses ``sig-pg`` outright (a distinct error so a refusal to touch
    production is greppable) and any name outside
    ``sig-pg-drill(-b)?-<YYYYmmddtHHMMz>``.
    """
    if name == PRODUCTION_INSTANCE:
        raise DrillNameError(f"{name!r} is the production instance — never a drill target")
    if not DRILL_INSTANCE_RE.match(name):
        raise DrillNameError(
            f"{name!r} is not a drill instance — expected sig-pg-drill-<YYYYmmddtHHMMz> "
            "(or sig-pg-drill-b-<stamp> for the full-backup variant)"
        )
    return name


class _Conn(Protocol):
    """The sliver of ``psycopg.Connection`` the drill uses (test-injectable)."""

    def execute(self, query: str, params: tuple = ()) -> Any: ...

    def __enter__(self) -> _Conn: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Any: ...


ConnectFactory = Callable[[str], _Conn]


def _connect(dsn: str) -> _Conn:
    import psycopg

    return psycopg.connect(dsn, connect_timeout=15)


def _count_sql(table: str, instant: str | None) -> str:
    if instant is None:
        return f"SELECT count(*) FROM {table}"
    return f"SELECT count(*) FROM {table} WHERE {instant} <= %s"


def _scalar(conn: _Conn, sql: str, params: tuple = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def schema_surface(conn: _Conn) -> dict[str, frozenset[str]]:
    """``{table: {columns}}`` over the public schema — the drill's honest view
    of what the deployed schema can answer. One ``information_schema`` read;
    SELECTs only."""
    rows = conn.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public'"
    ).fetchall()
    surface: dict[str, set[str]] = {}
    for table, col in rows:
        surface.setdefault(str(table), set()).add(str(col))
    return {t: frozenset(cs) for t, cs in surface.items()}


def effective_instants(surface: Mapping[str, frozenset[str]]) -> dict[str, str | None]:
    """The instant expression the *deployed* schema can actually evaluate per
    :data:`DRILL_TABLES` table — ``expr`` when every required column exists,
    ``None`` for an unbounded count, and the table simply absent is told apart
    by :func:`spine_counts` (the caller sees ``present`` on the record)."""
    out: dict[str, str | None] = {}
    for table, expr in DRILL_TABLES.items():
        cols = surface.get(table)
        if (
            cols is not None
            and expr is not None
            and all(c in cols for c in DRILL_INSTANT_COLUMNS[table])
        ):
            out[table] = expr
        else:
            out[table] = None
    return out


def spine_counts(
    conn: _Conn,
    at: datetime,
    instants: Mapping[str, str | None] | None = None,
) -> dict[str, int | None]:
    """``{table: count at T}`` — SELECTs only. ``instants`` is the effective
    map from :func:`effective_instants` (default: :data:`DRILL_TABLES` itself);
    a table absent from the schema counts ``None`` rather than erroring — a
    missing spine table is recorded drift, never a crash."""
    out: dict[str, int | None] = {}
    instants = instants or dict(DRILL_TABLES)
    surface = schema_surface(conn)
    for table, instant in instants.items():
        if table not in surface:
            out[table] = None
            continue
        params = (at,) if instant is not None else ()
        out[table] = int(_scalar(conn, _count_sql(table, instant), params))
    return out


def watermark_rows(
    conn: _Conn, surface: Mapping[str, frozenset[str]] | None = None
) -> dict[str, dict[str, Any]] | None:
    """The ``spine_watermark`` facet rows — compared verbatim between the
    source and the clone (the contract's "spine_watermark row equal").
    ``None`` when the deployed schema predates the table (P32.4); two absent
    watermarks are still equal (``None == None``) while absent-vs-present is
    recorded drift. A delta means spine writes landed between T and the
    measurement — the record keeps both sides visible rather than reconciling
    them."""
    if surface is None:
        surface = schema_surface(conn)
    if WATERMARK_TABLE not in surface:
        return None
    rows = conn.execute(
        "SELECT facet, row_count, closed_count, latest_instant FROM spine_watermark ORDER BY facet"
    ).fetchall()
    return {
        str(facet): {
            "row_count": int(rc),
            "closed_count": int(cc),
            "latest_instant": li.isoformat() if li is not None else None,
        }
        for facet, rc, cc, li in rows
    }


def sqitch_tip(conn: _Conn) -> list[dict[str, str]]:
    """Ordered ``(change, change_id)`` from ``sqitch.changes`` — the recordable
    equivalent of ``sqitch status`` (the drill reads plan *state*; C-10)."""
    rows = conn.execute(
        "SELECT change, change_id FROM sqitch.changes ORDER BY committed_at, change"
    ).fetchall()
    return [{"change": str(c), "change_id": str(i)} for c, i in rows]


def postgis_version(conn: _Conn) -> str | None:
    """The installed PostGIS version, or ``None`` when the extension is absent."""
    v = _scalar(conn, "SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
    return str(v) if v is not None else None


def newest_instant(conn: _Conn) -> datetime | None:
    """``max(lower(sys_period))`` on ``claim`` — the RPO measurement point."""
    v = _scalar(conn, RPO_INSTANT_SQL)
    return v if v is None else v if isinstance(v, datetime) else datetime.fromisoformat(str(v))


@dataclass(frozen=True)
class TableParity:
    table: str
    source_at_t: int | None  # None ⇒ the table is absent on that side
    clone_at_t: int | None
    bounded_by_t: bool  # False ⇒ no usable instant column; the count is total-vs-total
    instant: str | None  # the predicate expression actually applied (recorded honestly)

    @property
    def equal(self) -> bool:
        return (
            self.source_at_t is not None
            and self.clone_at_t is not None
            and self.source_at_t == self.clone_at_t
        )


@dataclass(frozen=True)
class DrillRecord:
    """The P34.6 drill record — the artefact AC1 names.

    ``rto_seconds`` is clone-submit → verified; ``rpo_seconds`` is T minus the
    newest recorded spine instant on the clone (T − max instant; a smaller
    value is tighter). Every field is measured or explicitly null — never
    fabricated.
    """

    at: str  # T, ISO-8601 UTC — the restore point
    clone_instance: str
    clone_started_at: str | None  # when `gcloud sql instances clone` was submitted
    verified_at: str | None  # when the parity read finished
    rto_seconds: float | None
    rpo_seconds: float | None
    newest_instant: str | None  # max(lower(claim.sys_period)) on the clone
    tables: tuple[TableParity, ...]
    schema_map_equal: bool  # the effective instant map identical on both sides
    watermark_present: bool  # spine_watermark exists (pre-P32.4 spines: False on both)
    watermark_source: dict[str, dict[str, Any]] | None
    watermark_clone: dict[str, dict[str, Any]] | None
    sqitch_tip_source: tuple[dict[str, str], ...]
    sqitch_tip_clone: tuple[dict[str, str], ...]
    postgis_source: str | None
    postgis_clone: str | None
    api_smoke: dict[str, Any]  # e.g. {"health": 200, "coverage": 200} filled by the shell leg

    @property
    def tables_equal(self) -> bool:
        return all(t.equal for t in self.tables)

    @property
    def watermark_equal(self) -> bool:
        return self.watermark_source == self.watermark_clone

    @property
    def sqitch_equal(self) -> bool:
        return list(self.sqitch_tip_source) == list(self.sqitch_tip_clone)

    @property
    def postgis_ok(self) -> bool:
        return self.postgis_source is not None and self.postgis_clone is not None

    @property
    def reproduced(self) -> bool:
        """The AC1 verdict: per-table parity + watermark + sqitch tip + PostGIS
        — and the effective predicate map identical on both sides (a clone whose
        schema drifted from the source's would otherwise answer a *different*
        question)."""
        return (
            self.tables_equal
            and self.schema_map_equal
            and self.watermark_equal
            and self.sqitch_equal
            and self.postgis_ok
        )

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": "sig.restore-drill/1",
            "at": self.at,
            "clone_instance": self.clone_instance,
            "clone_started_at": self.clone_started_at,
            "verified_at": self.verified_at,
            "rto_seconds": self.rto_seconds,
            "rpo_seconds": self.rpo_seconds,
            "newest_instant": self.newest_instant,
            "tables": [
                {
                    "table": t.table,
                    "source_at_t": t.source_at_t,
                    "clone_at_t": t.clone_at_t,
                    "bounded_by_t": t.bounded_by_t,
                    "instant": t.instant,
                    "equal": t.equal,
                }
                for t in self.tables
            ],
            "schema_map_equal": self.schema_map_equal,
            "watermark_present": self.watermark_present,
            "watermark_equal": self.watermark_equal,
            "watermark_source": self.watermark_source,
            "watermark_clone": self.watermark_clone,
            "sqitch_equal": self.sqitch_equal,
            "sqitch_tip_source": list(self.sqitch_tip_source),
            "sqitch_tip_clone": list(self.sqitch_tip_clone),
            "postgis_source": self.postgis_source,
            "postgis_clone": self.postgis_clone,
            "api_smoke": self.api_smoke,
            "reproduced": self.reproduced,
        }


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


def drill_parity(
    *,
    source_dsn: str,
    clone_dsn: str,
    at: datetime,
    clone_instance: str,
    clone_started_at: datetime | None = None,
    verified_at: datetime | None = None,
    connect: ConnectFactory | None = None,
) -> DrillRecord:
    """Run the at-T parity comparison between the source and the clone.

    Both connections run the identical per-table predicate
    (``instant <= :at``); for the clone that predicate equals its total (it is
    frozen at T) while on the source it reconstructs the T-state — the
    comparison is symmetric and honest about unbounded (no-instant) tables.
    """
    assert_drill_name(clone_instance)
    connect = connect or _connect
    with connect(source_dsn) as src, connect(clone_dsn) as cln:
        surf_src = schema_surface(src)
        surf_cln = schema_surface(cln)
        map_src = effective_instants(surf_src)
        map_cln = effective_instants(surf_cln)
        src_counts = spine_counts(src, at, map_src)
        cln_counts = spine_counts(cln, at, map_cln)
        newest = newest_instant(cln) if "sys_period" in surf_cln.get("claim", frozenset()) else None
        wm_src = watermark_rows(src, surf_src)
        wm_cln = watermark_rows(cln, surf_cln)
        sq_src = tuple(sqitch_tip(src))
        sq_cln = tuple(sqitch_tip(cln))
        pg_src = postgis_version(src)
        pg_cln = postgis_version(cln)

    tables = tuple(
        TableParity(
            table=t,
            source_at_t=src_counts[t],
            clone_at_t=cln_counts[t],
            bounded_by_t=map_src[t] is not None,
            instant=map_src[t],
        )
        for t in DRILL_TABLES
    )
    rto = (
        (verified_at - clone_started_at).total_seconds()
        if clone_started_at is not None and verified_at is not None
        else None
    )
    rpo = (at - newest).total_seconds() if newest is not None else None
    return DrillRecord(
        at=_iso(at) or "",
        clone_instance=clone_instance,
        clone_started_at=_iso(clone_started_at),
        verified_at=_iso(verified_at),
        rto_seconds=rto,
        rpo_seconds=rpo,
        newest_instant=_iso(newest),
        tables=tables,
        schema_map_equal=map_src == map_cln,
        watermark_present=WATERMARK_TABLE in surf_src or WATERMARK_TABLE in surf_cln,
        watermark_source=wm_src,
        watermark_clone=wm_cln,
        sqitch_tip_source=sq_src,
        sqitch_tip_clone=sq_cln,
        postgis_source=pg_src,
        postgis_clone=pg_cln,
        api_smoke={},
    )


__all__ = [
    "DRILL_INSTANCE_RE",
    "DRILL_INSTANT_COLUMNS",
    "DRILL_TABLES",
    "PRODUCTION_INSTANCE",
    "RPO_INSTANT_SQL",
    "WATERMARK_TABLE",
    "ConnectFactory",
    "DrillNameError",
    "DrillRecord",
    "TableParity",
    "assert_drill_name",
    "drill_parity",
    "effective_instants",
    "newest_instant",
    "postgis_version",
    "schema_surface",
    "spine_counts",
    "sqitch_tip",
    "watermark_rows",
]
