# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize honest §32 coverage into the spine (P28.4, ADR-099 posture).

The Appendix C.6 ``coverage_record`` table (negative space made queryable, §32.1) has
existed since P02.1 but has never held a row — the launch posture computed coverage on
read (ADR-092/ADR-038). :func:`materialize_coverage` runs the §32 coverage inference over
the real (resolved) spine and **writes** honest coverage as durable rows, honoring every
invariant §32 demands:

* **Named denominators, NEVER a total (SIG-METRIC-008/009/010).** Every counted-quantity
  row carries its denominator and the count excluded for lack of evidence; the denominator
  is a concrete *named* population, never the "denominator of reality". No population total
  or capture–recapture estimate is emitted anywhere — a hard, test-pinned invariant
  (:func:`assert_coverage_row_has_named_denominator`, the DB ``coverage_metric_named_denominator``
  CHECK, and the completeness module's always-refusing estimators).
* **Absence is a visible gap, not a guess (§32.1, SIG-METRIC-002).** Where a class of
  subjects is known but a peer-tracked predicate has never been researched for one of them,
  a ``not_researched`` :class:`~inference.coverage.CoverageRecord` is written — the honest
  negative space, distinguished from ``searched_not_found``. The peer classes and their
  tracked predicates are **declared** (``data/peer_classes.toml``, ADR-115), never
  inferred from the whole spine.
* **Append-only (ADR-005).** This path only ``INSERT``s — there is no ``UPDATE``/``DELETE``.
  A changed measurement yields a new :func:`coverage_input_digest` and a *superseding* row;
  a re-run over an unchanged spine is a no-op (+0).
* **Idempotent (+0).** The insert is ``ON CONFLICT (input_digest) DO NOTHING`` against the
  ``coverage_record_input_digest_key`` partial unique index (the ``coverage_materialize``
  sqitch change).
* **REUSE, not re-implement (SIG-ENG-035).** The §32 shapes are the existing
  :mod:`inference.coverage` (`CoverageRecord`), :mod:`inference.denominators`
  (`PublishedAggregate`, `ProvenanceCompleteness`), and :mod:`inference.completeness`
  (`CompletenessMethod`, `assert_no_population_total`) — CONSUMED here, never re-derived.

Per-jurisdiction coverage (SIG-METRIC-004) is driven by the ``jurisdiction`` filter (the
same ``entity_identifier`` token match the P28.1/P28.2/P28.3 materializers use): each
counted quantity is then scoped to that jurisdiction's subjects, so "per-jurisdiction site
counts" is one materialization pass per jurisdiction.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .completeness import (
    CompletenessMethod,
    CompletenessStatement,
    assert_no_population_total,
)
from .coverage import CoverageRecord
from .denominators import ProvenanceCompleteness, PublishedAggregate, provenance_completeness
from .peer_classes import PeerClass, load_peer_classes

__all__ = [
    "CoverageMaterializeSummary",
    "assert_coverage_row_has_named_denominator",
    "coverage_input_digest",
    "metric_row",
    "absence_row",
    "read_provenance_completeness",
    "read_predicate_reconciliation",
    "read_negative_space",
    "materialize_coverage",
    "materialize_coverage_from_dsn",
    "read_materialized_coverage",
    "CoverageRecord",
    "PublishedAggregate",
]

#: The §32.1 absence kind for a subject a peer class covers but SIG has not looked at.
_NOT_RESEARCHED = "not_researched"
#: A metric row is a counted quantity, not an absence — ``not_applicable`` is the honest
#: absence kind for the non-negative-space rows (the predicate-absence taxonomy does not
#: apply to an aggregate).
_METRIC_ABSENCE_KIND = "not_applicable"


@dataclass(frozen=True)
class CoverageMaterializeSummary:
    """The outcome of one coverage materialization pass — every record accounted for."""

    metrics_considered: int = 0
    absences_considered: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    by_method: dict[str, int] = field(default_factory=dict)
    absences_inserted: int = 0

    @property
    def written(self) -> int:
        return self.inserted

    def as_dict(self) -> dict[str, Any]:
        return {
            "metrics_considered": self.metrics_considered,
            "absences_considered": self.absences_considered,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "absences_inserted": self.absences_inserted,
            "by_method": dict(sorted(self.by_method.items())),
        }


def assert_coverage_row_has_named_denominator(row: dict[str, Any]) -> dict[str, Any]:
    """Refuse any coverage row that is a population total (SIG-METRIC-008/009/010).

    The single choke point the materializer routes **every** row through. A negative-space
    row (``metric_method`` is ``None``) passes untouched. A counted-quantity row is
    re-validated as a :class:`~inference.completeness.CompletenessStatement` — which raises
    on a missing or "reality" denominator — so a population total, a capture–recapture
    estimate, or a bare unnamed number can never be written. This makes "no total" a
    failure a test asserts, not a review-time hope.
    """
    method = row.get("metric_method")
    if method is None:
        return row  # negative space carries no denominator by construction — that is fine
    # Reconstruct the §32.5 statement; assert_no_population_total refuses a reality
    # denominator (SIG-METRIC-010) and a non-statement, and CompletenessMethod refuses a
    # method that is not one of the four publishable (never-a-total) methods.
    statement = CompletenessStatement(
        method=CompletenessMethod(str(method)),
        named_denominator=str(row.get("named_denominator") or ""),
        value=float(row.get("metric_value") or 0.0),
    )
    assert_no_population_total(statement)
    return row


def coverage_input_digest(row: dict[str, Any]) -> str:
    """A deterministic sha256 over a coverage row's reproducible content.

    The idempotency key: two passes over the same coverage measurement digest identically
    → the insert is a no-op (+0). A changed measurement → a new digest → a superseding
    append-only row.
    """
    stable = {
        "subject_id": row.get("subject_id"),
        "subject_class": row.get("subject_class"),
        "jurisdiction_id": row.get("jurisdiction_id"),
        "predicate_id": row.get("predicate_id"),
        "absence_kind": row["absence_kind"],
        "sources_searched": sorted(row.get("sources_searched") or ()),
        "metric_method": row.get("metric_method"),
        "metric_label": row.get("metric_label"),
        "numerator": _num(row.get("numerator")),
        "denominator": _num(row.get("denominator")),
        "not_evaluable": _num(row.get("not_evaluable")),
        "named_denominator": row.get("named_denominator"),
        "metric_value": _num(row.get("metric_value")),
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _num(value: Any) -> float | None:
    return None if value is None else float(value)


def metric_row(
    aggregate: PublishedAggregate,
    *,
    method: CompletenessMethod,
    named_denominator: str,
    value: float,
    subject_class: str,
    jurisdiction_id: str | None = None,
    predicate_id: str | None = None,
) -> dict[str, Any]:
    """Map a §32.2 :class:`~inference.denominators.PublishedAggregate` onto a coverage row.

    The counted quantity carries its numerator, evaluable denominator, not-evaluable
    count, method, and NAMED denominator (never a total). ``absence_kind`` is
    ``not_applicable`` — a counted quantity is not a kind of absence. The row is validated
    through :func:`assert_coverage_row_has_named_denominator` before it is returned, so a
    caller cannot construct a total.
    """
    row: dict[str, Any] = {
        "subject_id": None,
        "subject_class": subject_class,
        "jurisdiction_id": jurisdiction_id,
        "predicate_id": predicate_id,
        "absence_kind": _METRIC_ABSENCE_KIND,
        "sources_searched": None,
        "searched_at": None,
        "searched_by": "auto",
        "search_method": "inference.materialize",
        "metric_method": method.value,
        "metric_label": aggregate.label,
        "numerator": aggregate.count,
        "denominator": aggregate.denominator,
        "not_evaluable": aggregate.not_evaluable,
        "named_denominator": named_denominator,
        "metric_value": value,
    }
    assert_coverage_row_has_named_denominator(row)
    row["input_digest"] = coverage_input_digest(row)
    return row


def absence_row(record: CoverageRecord) -> dict[str, Any]:
    """Map a §32.1 :class:`~inference.coverage.CoverageRecord` onto a coverage row.

    Negative space: ``metric_method`` is ``None`` (no denominator — that is the point),
    ``sources_searched`` is required for ``searched_not_found`` (enforced by
    ``CoverageRecord`` itself, mirroring the DDL CHECK).
    """
    row: dict[str, Any] = {
        "subject_id": record.subject_id,
        "subject_class": record.subject_class,
        "jurisdiction_id": record.jurisdiction_id,
        "predicate_id": record.predicate_id,
        "absence_kind": record.absence_kind,
        "sources_searched": list(record.sources_searched) or None,
        "searched_at": record.searched_at,
        "searched_by": record.searched_by or "auto",
        "search_method": record.search_method or "inference.materialize",
        "metric_method": None,
        "metric_label": None,
        "numerator": None,
        "denominator": None,
        "not_evaluable": None,
        "named_denominator": None,
        "metric_value": None,
    }
    assert_coverage_row_has_named_denominator(row)
    row["input_digest"] = coverage_input_digest(row)
    return row


# ---------------------------------------------------------------------------
# Reads over the resolved spine (contradictions visible, tier-0, currently-valid).
# ---------------------------------------------------------------------------


def _jurisdiction_filter(jurisdiction: str | None, params: list[Any]) -> str:
    """The §32.4 per-jurisdiction scope — the entity_identifier token match the other
    materializers use. Returns an empty clause when no jurisdiction is given."""
    if not jurisdiction:
        return ""
    params.append(f"%{jurisdiction}%")
    return " AND c.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"


def read_provenance_completeness(
    conn: Any, *, jurisdiction: str | None = None
) -> ProvenanceCompleteness:
    """Measure §32.3 provenance completeness over the spine (SIG-METRIC-005).

    The share of published tier-0 claims with a resolvable evidence artifact, targeted at
    100%; the shortfall is materialized as the defect list of claim ids that lack one, not
    a statistic. CONSUMES :func:`inference.denominators.provenance_completeness`.
    """
    params: list[Any] = []
    juris = _jurisdiction_filter(jurisdiction, params)
    rows = conn.execute(
        "SELECT c.claim_id::text, "
        "       EXISTS (SELECT 1 FROM claim_evidence ce WHERE ce.claim_id = c.claim_id) "
        "  FROM claim c "
        " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period)"
        + juris
        + " ORDER BY c.claim_id",
        tuple(params),
    ).fetchall()
    claim_ids = [str(r[0]) for r in rows]
    with_evidence = [str(r[0]) for r in rows if r[1]]
    return provenance_completeness(claim_ids, claims_with_resolvable_evidence=with_evidence)


def read_predicate_reconciliation(
    conn: Any, *, jurisdiction: str | None = None
) -> list[dict[str, Any]]:
    """Per-predicate reconciliation ratio over the resolved spine (SIG-METRIC-009).

    For each predicate, the number of subjects that carry a materialized §16.4 resolution
    decision, of the subjects that carry a tier-0 claim for that predicate — "N of M
    subjects with a <predicate> claim have a resolved value". A per-agency-style
    reconciliation ratio, each carrying its named denominator; NEVER extrapolated to a
    total. Returns ``[{predicate_id, claimed_subjects, resolved_subjects}]``.
    """
    params: list[Any] = []
    juris = _jurisdiction_filter(jurisdiction, params)
    claimed = conn.execute(
        "SELECT c.predicate_id, count(DISTINCT c.subject_id) "
        "  FROM claim c "
        " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period)"
        + juris
        + " GROUP BY c.predicate_id ORDER BY c.predicate_id",
        tuple(params),
    ).fetchall()
    claimed_by_pred = {str(r[0]): int(r[1]) for r in claimed}

    # Resolved subjects per predicate — restricted to the same jurisdiction scope so the
    # numerator can never exceed its denominator. Only a decision that picked a winning
    # claim is a "resolved value": a first-class ``unresolved_conflict`` envelope (both
    # sides retained, §3.1) resolves nothing and must never be counted as resolved
    # (P30.2 finding COVERAGE-RESOLVED-01 — the hosted 299-vs-190 conflict was counted).
    rparams: list[Any] = []
    rjuris = ""
    if jurisdiction:
        rparams.append(f"%{jurisdiction}%")
        rjuris = (
            " AND r.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
    resolved = conn.execute(
        "SELECT r.predicate_id, count(DISTINCT r.subject_id) "
        "  FROM resolution r WHERE r.winning_claim IS NOT NULL"
        + rjuris
        + " GROUP BY r.predicate_id",
        tuple(rparams),
    ).fetchall()
    resolved_by_pred = {str(r[0]): int(r[1]) for r in resolved}

    out: list[dict[str, Any]] = []
    for predicate_id, claimed_subjects in claimed_by_pred.items():
        resolved_subjects = min(resolved_by_pred.get(predicate_id, 0), claimed_subjects)
        out.append(
            {
                "predicate_id": predicate_id,
                "claimed_subjects": claimed_subjects,
                "resolved_subjects": resolved_subjects,
            }
        )
    return out


def read_negative_space(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    peer_classes: Iterable[PeerClass] | None = None,
) -> list[CoverageRecord]:
    """Retain the honest §32.1 negative space over the spine (SIG-METRIC-002).

    The peer-class rule (P31.9 / ADR-115, replacing the P28.4
    entity-type-as-class rule — the hosted spine is all ``deployment`` and the
    old rule would emit ~26.7M rows of meaningless absences): a peer class is
    ``(entity_type, connector)``, declared in
    :mod:`inference.peer_classes` (``data/peer_classes.toml``). A claim subject
    belongs to a class when at least one of its tier-0, currently-valid claims
    was written by an ``ingest_run`` whose ``connector_name`` the class
    declares; its tracked set is the UNION of the tracked predicates of every
    class it belongs to. A member with NO claim for a tracked predicate is a
    ``not_researched`` coverage record — "SIG has not looked here",
    distinguished from ``searched_not_found`` (which would need named sources).

    A predicate absent from the declaration is never negative space, and a
    subject whose claims come only from connectors no class declares produces
    no rows — an undeclared coverage surface, never a guess. ``peer_classes``
    is injectable for tests; ``None`` loads the shipped declaration.
    """
    classes = tuple(peer_classes) if peer_classes is not None else load_peer_classes()
    if not classes:
        return []

    params: list[Any] = []
    juris = _jurisdiction_filter(jurisdiction, params)
    rows = conn.execute(
        "SELECT c.subject_id::text, e.entity_type, ir.connector_name, c.predicate_id "
        "  FROM claim c JOIN entity e ON e.entity_id = c.subject_id "
        "  JOIN ingest_run ir ON ir.run_id = c.ingest_run_id "
        " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period)"
        + juris
        + " GROUP BY c.subject_id, e.entity_type, ir.connector_name, c.predicate_id "
        " ORDER BY e.entity_type, c.subject_id",
        tuple(params),
    ).fetchall()

    subject_type: dict[str, str] = {}
    subject_connectors: dict[str, set[str]] = {}
    claimed_pairs: set[tuple[str, str]] = set()
    for subject_id, entity_type, connector_name, predicate_id in rows:
        s = str(subject_id)
        subject_type[s] = str(entity_type)
        subject_connectors.setdefault(s, set()).add(str(connector_name))
        claimed_pairs.add((s, str(predicate_id)))

    classes_by_type: dict[str, list[PeerClass]] = {}
    for pc in classes:
        classes_by_type.setdefault(pc.entity_type, []).append(pc)

    out: list[CoverageRecord] = []
    for subject_id in sorted(subject_type):
        tracked: set[str] = set()
        for pc in classes_by_type.get(subject_type[subject_id], ()):
            if subject_connectors[subject_id] & set(pc.connectors):
                tracked.update(pc.tracked)
        for predicate_id in sorted(tracked):
            if (subject_id, predicate_id) in claimed_pairs:
                continue
            out.append(
                CoverageRecord(
                    predicate_id=predicate_id,
                    absence_kind=_NOT_RESEARCHED,
                    subject_id=subject_id,
                    subject_class=subject_type[subject_id],
                    searched_by="auto",
                    search_method="inference.materialize (peer-class negative space)",
                )
            )
    return out


# ---------------------------------------------------------------------------
# The write path — append-only, idempotent, no-total.
# ---------------------------------------------------------------------------


def _insert_coverage(conn: Any, row: dict[str, Any]) -> bool:
    """INSERT one coverage_record row, idempotent on ``input_digest``. True iff inserted."""
    result = conn.execute(
        "INSERT INTO coverage_record"
        "(subject_id, subject_class, jurisdiction_id, predicate_id, absence_kind, "
        " sources_searched, searched_at, searched_by, search_method, "
        " metric_method, metric_label, numerator, denominator, not_evaluable, "
        " named_denominator, metric_value, input_digest) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s, %s, "
        " %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL "
        "DO NOTHING RETURNING coverage_id",
        (
            row.get("subject_id"),
            row.get("subject_class"),
            row.get("jurisdiction_id"),
            row.get("predicate_id"),
            row["absence_kind"],
            row.get("sources_searched"),
            row.get("searched_at"),
            row.get("searched_by"),
            row.get("search_method"),
            row.get("metric_method"),
            row.get("metric_label"),
            row.get("numerator"),
            row.get("denominator"),
            row.get("not_evaluable"),
            row.get("named_denominator"),
            row.get("metric_value"),
            row["input_digest"],
        ),
    ).fetchone()
    return result is not None


def _metric_rows_for_spine(conn: Any, *, jurisdiction: str | None) -> Iterable[dict[str, Any]]:
    """The counted-quantity coverage rows for the current spine (all denominated)."""
    # §32.3 provenance completeness — one global (or per-jurisdiction) counted quantity.
    prov = read_provenance_completeness(conn, jurisdiction=jurisdiction)
    prov_agg = PublishedAggregate(
        label="published tier-0 claims with a resolvable evidence artifact",
        count=prov.with_resolvable_evidence,
        denominator=prov.published_claims,
        not_evaluable=0,
    )
    # The named denominator names its jurisdiction scope when one is given, so a
    # per-jurisdiction run (SIG-METRIC-004) is never mislabelled as global.
    scope = f" in {jurisdiction}" if jurisdiction else ""
    if prov.published_claims > 0:
        yield metric_row(
            prov_agg,
            method=CompletenessMethod.COUNTED_WITH_DENOMINATOR,
            named_denominator=f"published tier-0 claims{scope}",
            value=prov.share,
            subject_class="claim",
            jurisdiction_id=None,
        )

    # §32.5 per-predicate reconciliation ratio — resolved subjects of claimed subjects.
    for rec in read_predicate_reconciliation(conn, jurisdiction=jurisdiction):
        pred = rec["predicate_id"]
        claimed = rec["claimed_subjects"]
        resolved = rec["resolved_subjects"]
        if claimed <= 0:
            continue
        agg = PublishedAggregate(
            label=f"subjects with a resolved {pred} value",
            count=resolved,
            denominator=claimed,
            not_evaluable=0,
        )
        yield metric_row(
            agg,
            method=CompletenessMethod.RECONCILIATION_RATIO,
            named_denominator=f"subjects with a {pred} claim{scope}",
            value=(resolved / claimed) if claimed else 0.0,
            subject_class="subject",
            jurisdiction_id=None,
            predicate_id=pred,
        )


def materialize_coverage(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    role: str | None = None,
    negative_space: bool = True,
    peer_classes: Iterable[PeerClass] | None = None,
) -> CoverageMaterializeSummary:
    """Materialize honest §32 coverage over the resolved spine (P28.4).

    Writes counted quantities with NAMED denominators (§32.2/32.3), per-predicate
    reconciliation ratios (§32.5), and the honest negative space (§32.1) as append-only,
    idempotent ``coverage_record`` rows — and NEVER a total or a population estimate
    (SIG-METRIC-008/009/010, enforced by :func:`assert_coverage_row_has_named_denominator`
    and the DB CHECK). The negative space is scoped by the declared peer classes
    (P31.9 / ADR-115; ``peer_classes`` overrides the shipped declaration, tests only).
    A second call over an unchanged spine inserts +0.
    """
    if role:
        conn.execute(f"SET ROLE {role}")

    metrics_considered = inserted = skipped_existing = 0
    absences_considered = absences_inserted = 0
    by_method: dict[str, int] = {}

    for row in _metric_rows_for_spine(conn, jurisdiction=jurisdiction):
        metrics_considered += 1
        if _insert_coverage(conn, row):
            inserted += 1
            method = str(row["metric_method"])
            by_method[method] = by_method.get(method, 0) + 1
        else:
            skipped_existing += 1

    if negative_space:
        for record in read_negative_space(
            conn, jurisdiction=jurisdiction, peer_classes=peer_classes
        ):
            absences_considered += 1
            row = absence_row(record)
            if _insert_coverage(conn, row):
                inserted += 1
                absences_inserted += 1
            else:
                skipped_existing += 1

    return CoverageMaterializeSummary(
        metrics_considered=metrics_considered,
        absences_considered=absences_considered,
        inserted=inserted,
        skipped_existing=skipped_existing,
        by_method=by_method,
        absences_inserted=absences_inserted,
    )


#: The identity of one measured coverage quantity — two rows sharing it are successive
#: measurements of the same thing (the later supersedes the earlier, append-only).
_COVERAGE_KEY = (
    "coalesce(metric_method, ''), coalesce(subject_class, ''), "
    "coalesce(jurisdiction_id::text, ''), coalesce(predicate_id, ''), "
    "coalesce(subject_id::text, ''), absence_kind, coalesce(named_denominator, '')"
)


def read_materialized_coverage(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """Read the CURRENT materialized coverage rows (the P28.5 surface seam).

    The real coverage dataset the P28.5 surface refresh consumes to back the coverage +
    "what we don't know" pages: counted quantities with their named denominators and the
    negative space, deterministically ordered. Read-only. Every counted quantity carries a
    named denominator (never a total); every absence carries its absence kind.

    Append-only supersession (P30.2): a changed measurement is a NEW row with a new
    digest, never an UPDATE — so the table holds every measurement ever taken. The seam
    returns only the LATEST row per measured quantity (same method, class, jurisdiction,
    predicate, subject, absence kind and named denominator; latest = highest time-ordered
    ``uuidv7`` ``coverage_id``). The superseded rows stay in the table as history.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT coverage_id::text, subject_id::text, subject_class, jurisdiction_id::text, "
        "       predicate_id, absence_kind, sources_searched, "
        "       metric_method, metric_label, numerator, denominator, not_evaluable, "
        "       named_denominator, metric_value "
        "  FROM ("
        "    SELECT DISTINCT ON (" + _COVERAGE_KEY + ") * "
        "      FROM coverage_record "
        "     WHERE input_digest IS NOT NULL "
        "     ORDER BY " + _COVERAGE_KEY + ", coverage_id DESC"
        "  ) latest "
        " ORDER BY metric_method NULLS LAST, subject_class, predicate_id, subject_id, coverage_id"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "coverage_id": r[0],
                "subject_id": r[1],
                "subject_class": r[2],
                "jurisdiction_id": r[3],
                "predicate_id": r[4],
                "absence_kind": r[5],
                "sources_searched": [str(x) for x in (r[6] or ())],
                "metric_method": r[7],
                "metric_label": r[8],
                "numerator": None if r[9] is None else float(r[9]),
                "denominator": None if r[10] is None else float(r[10]),
                "not_evaluable": None if r[11] is None else float(r[11]),
                "named_denominator": r[12],
                "metric_value": None if r[13] is None else float(r[13]),
            }
        )
    return out


def materialize_coverage_from_dsn(dsn: str, **kwargs: Any) -> CoverageMaterializeSummary:
    """Open an autocommit connection from ``dsn`` and materialize coverage (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_coverage(conn, **kwargs)
    finally:
        conn.close()
