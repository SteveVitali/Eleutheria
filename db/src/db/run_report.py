# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Append-only ingest-run report (P35.32 / J3 §3.3 item 1, K10 §18 C-13/C-14).

``ingest_run_report`` is the report layer for ingestion: one typed row per
execution recording WHAT THE EXECUTION SAW — fetches, robots per host,
refusal classes (incl. quarantine counts-by-reason only), the scrubbed
PKG-12 per-fetch shape, document outcomes, quota/budget and the S-4
``error_class``. The ``ingest_run`` row stays shared bookkeeping; this table
is execution-evidence.

Link honesty (K10 C-13/C-14):

- ``link_basis`` says how the row links to an ``ingest_run``: ``live``,
  ``backfill:claims-in-window``, ``backfill:sole-candidate``,
  ``unmatched:<reason>`` (the P31.2 classes), ``repo_record``.
- ``clock_basis`` says where the row's own clock came from: ``db``,
  ``run_row``, ``git_only``.
- ``run_id`` is nullable: unmatched executions (and live rows whose
  connector ran before the DB wrote a run — refusals) carry NULL.
- ``started_at`` is the execution's OWN clock or NULL — never a borrowed
  shared-run clock (C-13).

Same shape as ``ingest_run_completion`` (P31.2, ADR-109): one INSERT entry
point with the closed vocabularies validated in code (``error_class`` via
``policy.transparency.valid_error_class``), ``ON CONFLICT DO NOTHING`` under
the two partial unique indexes (live key on ``run_id``, backfill key on
``backfilled_from`` — every re-run +0), no UPDATE/DELETE path (the table's
immutability trigger refuses both anyway).
"""

from __future__ import annotations

import json
from typing import Any

from policy.transparency import valid_error_class

# The closed C-14 link vocabulary; ``unmatched:<reason>`` is the open-suffix
# member (the reason is one of the P31.2 matcher classes, mapped by
# ``ops.run_report``).
LINK_BASES = (
    "live",
    "repo_record",
    "backfill:claims-in-window",
    "backfill:sole-candidate",
)

CLOCK_BASES = ("db", "run_row", "git_only")


def valid_link_basis(value: object) -> bool:
    return isinstance(value, str) and (value in LINK_BASES or value.startswith("unmatched:"))


def valid_clock_basis(value: object) -> bool:
    return isinstance(value, str) and value in CLOCK_BASES


def report_present(conn: Any) -> bool:
    """True when ``ingest_run_report`` exists (False pre-deploy — writers
    then record nothing and the backfill mints the rows)."""
    return conn.execute("SELECT to_regclass('public.ingest_run_report') IS NOT NULL").fetchone()[0]


def upstream_recon_present(conn: Any) -> bool:
    """True when ``ingest_run_report.upstream_reconciliation`` is deployed
    (the P35.34 change). A spine not yet migrated answers False — the
    writers then record the row without the reconciliation field rather
    than failing the write; the column is never fabricated onto an older
    schema."""
    return conn.execute(
        "SELECT EXISTS ("
        " SELECT 1 FROM information_schema.columns"
        " WHERE table_schema = 'public'"
        "   AND table_name = 'ingest_run_report'"
        "   AND column_name = 'upstream_reconciliation')"
    ).fetchone()[0]


def append_report(
    conn: Any,
    *,
    link_basis: str,
    clock_basis: str,
    run_id: Any = None,
    source_id: str | None = None,
    started_at: Any = None,
    fetches: int | None = None,
    records_emitted: int | None = None,
    duration_seconds: float | None = None,
    robots_outcomes: Any = None,
    refusal_classes: Any = None,
    rate_limit_events: int | None = None,
    disappearances: int | None = None,
    document_outcomes: Any = None,
    quota_reached: bool | None = None,
    budget_reached: bool | None = None,
    error_class: str | None = None,
    per_fetch: Any = None,
    upstream_reconciliation: Any = None,
    backfilled_from: str | None = None,
) -> str | None:
    """Insert one report row; return the new report_id (uuid str).

    Every field defaults to NULL — "not_recorded" — so an unevidenced value
    is *typed* missing rather than zero-shaped. Validation mirrors the DDL
    CHECKs (the DB enforces them too); ``error_class`` reuses the P35.31
    ``policy.transparency`` S-4 vocabulary verbatim.

    ON CONFLICT DO NOTHING targets the two partial unique keys
    (``run_id`` on live rows, ``backfilled_from`` on backfilled rows) — a
    second insert of the same execution is a +0 no-op returning ``None``.
    """

    if not valid_link_basis(link_basis):
        raise ValueError(f"off-vocabulary link_basis: {link_basis!r}")
    if not valid_clock_basis(clock_basis):
        raise ValueError(f"off-vocabulary clock_basis: {clock_basis!r}")
    if error_class is not None and not valid_error_class(error_class):
        raise ValueError(f"off-vocabulary error_class: {error_class!r}")

    def _jb(v: Any) -> str | None:
        return None if v is None else json.dumps(v, sort_keys=True, default=str)

    # The P35.34 change may not be deployed on this spine yet — a writer
    # then records the row without the reconciliation field rather than
    # failing the write (the same posture ``report_present`` sets: an
    # undeployed surface is skipped, never fabricated onto the old schema).
    has_recon = upstream_recon_present(conn)
    if has_recon:
        sql = (
            "INSERT INTO ingest_run_report"
            " (run_id, source_id, link_basis, clock_basis, started_at,"
            "  fetches, records_emitted, duration_seconds,"
            "  robots_outcomes, refusal_classes, rate_limit_events,"
            "  disappearances, document_outcomes, quota_reached, budget_reached,"
            "  error_class, per_fetch, upstream_reconciliation, backfilled_from)"
            " VALUES"
            " (%s, %s, %s, %s, %s,"
            "  %s, %s, %s,"
            "  %s::jsonb, %s::jsonb, %s,"
            "  %s, %s::jsonb, %s, %s,"
            "  %s, %s::jsonb, %s::jsonb, %s)"
            " ON CONFLICT DO NOTHING RETURNING report_id"
        )
        params: tuple[Any, ...] = (
            run_id,
            source_id,
            link_basis,
            clock_basis,
            started_at,
            fetches,
            records_emitted,
            duration_seconds,
            _jb(robots_outcomes),
            _jb(refusal_classes),
            rate_limit_events,
            disappearances,
            _jb(document_outcomes),
            quota_reached,
            budget_reached,
            error_class,
            _jb(per_fetch),
            _jb(upstream_reconciliation),
            backfilled_from,
        )
    else:
        sql = (
            "INSERT INTO ingest_run_report"
            " (run_id, source_id, link_basis, clock_basis, started_at,"
            "  fetches, records_emitted, duration_seconds,"
            "  robots_outcomes, refusal_classes, rate_limit_events,"
            "  disappearances, document_outcomes, quota_reached, budget_reached,"
            "  error_class, per_fetch, backfilled_from)"
            " VALUES"
            " (%s, %s, %s, %s, %s,"
            "  %s, %s, %s,"
            "  %s::jsonb, %s::jsonb, %s,"
            "  %s, %s::jsonb, %s, %s,"
            "  %s, %s::jsonb, %s)"
            " ON CONFLICT DO NOTHING RETURNING report_id"
        )
        params = (
            run_id,
            source_id,
            link_basis,
            clock_basis,
            started_at,
            fetches,
            records_emitted,
            duration_seconds,
            _jb(robots_outcomes),
            _jb(refusal_classes),
            rate_limit_events,
            disappearances,
            _jb(document_outcomes),
            quota_reached,
            budget_reached,
            error_class,
            _jb(per_fetch),
            backfilled_from,
        )
    row = conn.execute(sql, params).fetchone()
    return None if row is None else str(row[0])


def counts_by_link_basis(conn: Any) -> dict[str, int]:
    """{link_basis: n} over the whole table — the reconcile read-back."""
    out: dict[str, int] = {}
    for basis, n in conn.execute(
        "SELECT link_basis, count(*) FROM ingest_run_report GROUP BY link_basis ORDER BY link_basis"
    ):
        out[basis] = int(n)
    return out


__all__ = [
    "CLOCK_BASES",
    "LINK_BASES",
    "append_report",
    "counts_by_link_basis",
    "report_present",
    "upstream_recon_present",
    "valid_clock_basis",
    "valid_link_basis",
]
