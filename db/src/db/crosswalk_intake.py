# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The crosswalk-intake apply: spine-asserted organisation identifiers (P37.46a).

R11-CONF-13 13a (design CP-10; SIG-CONF-004 'Also' — organisations auto-link
only on an exact shared authoritative identifier or an established registry
crosswalk). A connector's ``candidate_identifier`` lands on a claim's
``value_json``; this module is the write path that turns each organisation
subject's candidate into a spine-asserted ``entity_identifier`` row whose
``asserted_by_claim`` names the asserting claim — the tier-0 match record the
ADR-159 auto-allow census (``ops.dispositions``) resolves through
``claim → claim_evidence → evidence_capture → evidence_artifact →
source_registry.ingestion_permitted``.

Two invariants the tests pin:

* **Insert-only, idempotent.** The apply is a plain ``INSERT … ON CONFLICT
  (entity_id, scheme, value) DO NOTHING`` — a re-run is +0; nothing is
  UPDATEd or DELETEd (SIG-STORE-011).
* **Provenance is read, never inferred.** ``asserted_by_claim`` is always the
  claim that carried the candidate; the census's permitted-source join does
  the rights check downstream — the apply never fabricates an assertion for a
  subject whose entity is not an organization.

The named mutation (the four lanes' production writes) is ``sig-db
crosswalk-intake --apply`` — dry-run by default, keyset-bounded.
"""

from __future__ import annotations

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "REPORT_SCHEMA",
    "L2_DUPLICATE_BASELINE",
    "assert_lane_identifiers",
    "intake_plan",
    "org_identity_report",
    "lane_schemes",
    "run",
]


@cache
def _lanes_table() -> dict[str, Any]:
    resource = files("db").joinpath("data", "crosswalk_lanes.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def lane_schemes() -> dict[str, str]:
    """Lane id → identifier scheme (the versioned lane vocabulary)."""
    return {str(x["id"]): str(x["scheme"]) for x in _lanes_table()["lane"]}


#: ``sig.org-crosswalk-report/1`` — the committed report record schema.
REPORT_SCHEMA = "sig.org-crosswalk-report/1"

#: The L2 baseline the acceptance measures the fall against (L2 NEW-9:
#: ≥ 171 of 200 sampled agencies duplicated, 0 links).
L2_DUPLICATE_BASELINE = {
    "duplicated_share": 0.855,
    "sample": 200,
    "duplicated_at_least": 171,
    "measured_in": "L2 NEW-9",
}


#: Every claim whose persisted candidate pair is a lane scheme, on an
#: organization subject, not yet asserted on that entity. Keyset-ordered by
#: claim_id for bounded, resumable batches.
_CANDIDATES_SQL = (
    "SELECT c.claim_id::text, c.subject_id::text, "
    "       c.value_json->>'scheme' AS scheme, c.value_json->>'value' AS value "
    "FROM claim c "
    "JOIN entity e ON e.entity_id = c.subject_id "
    "WHERE e.entity_type = 'organization' "
    "  AND c.value_json->>'scheme' = ANY(%s::text[]) "
    "  AND c.value_json->>'value' IS NOT NULL "
    "  AND c.claim_id > %s::uuid "
    "  AND upper_inf(c.sys_period) "
    "ORDER BY c.claim_id LIMIT %s"
)

_ASSERT_SQL = (
    "INSERT INTO entity_identifier(entity_id, scheme, value, asserted_by_claim) "
    "VALUES (%s::uuid, %s, %s, %s::uuid) "
    "ON CONFLICT (entity_id, scheme, value) DO NOTHING"
)

#: The organisation-identity report population: org entities and the lane
#: identifier coverage.
_ORG_TOTAL_SQL = "SELECT count(*) FROM entity WHERE entity_type = 'organization'"
_ORG_LANE_SQL = (
    "SELECT ei.scheme, count(DISTINCT ei.entity_id) AS entities, "
    "       count(DISTINCT ei.value) AS distinct_values, "
    "       count(*) FILTER (WHERE ei.asserted_by_claim IS NOT NULL) AS asserted "
    "FROM entity_identifier ei "
    "JOIN entity e ON e.entity_id = ei.entity_id AND e.entity_type = 'organization' "
    "WHERE ei.scheme = ANY(%s::text[]) GROUP BY ei.scheme ORDER BY ei.scheme"
)
#: The duplicate-agency measure: lane-scheme values held by >1 organisation
#: entity (candidates for the cascade's recorded same_as, never a silent merge).
_ORG_DUP_SQL = (
    "SELECT count(*) FROM ("
    "  SELECT ei.scheme, ei.value FROM entity_identifier ei "
    "  JOIN entity e ON e.entity_id = ei.entity_id AND e.entity_type = 'organization' "
    "  WHERE ei.scheme = ANY(%s::text[]) "
    "  GROUP BY ei.scheme, ei.value HAVING count(DISTINCT ei.entity_id) > 1"
    ") dups"
)
#: The L2-shape duplicate rate over plain org subjects: share of organization
#: entities whose normalized name+state appears on a distinct entity —
#: the pre-crosswalk fragmentation measure the lanes exist to shrink.
_ORG_NAME_DUP_SQL = (
    "SELECT count(*), count(*) FILTER (WHERE dup > 1) FROM ("
    "  SELECT lower(trim(o.cached_canonical_name)) AS n, "
    "         count(DISTINCT o.entity_id) AS dup "
    "  FROM organization o WHERE o.cached_canonical_name IS NOT NULL "
    "  GROUP BY 1"
    ") names"
)


@dataclass(frozen=True)
class IntakeBatch:
    """One bounded batch result."""

    scanned: int
    asserted: int
    last_claim_id: str | None
    lanes: tuple[str, ...]
    apply: bool


@dataclass
class IntakeReport:
    """The accumulated plan/apply report."""

    batches: list[IntakeBatch] = field(default_factory=list)

    @property
    def scanned(self) -> int:
        return sum(b.scanned for b in self.batches)

    @property
    def asserted(self) -> int:
        return sum(b.asserted for b in self.batches)


def assert_lane_identifiers(
    conn: Any,
    *,
    schemes: Sequence[str],
    apply: bool = False,
    limit: int | None = None,
    batch_size: int = 1_000,
    after: str = "00000000-0000-0000-0000-000000000000",
) -> IntakeReport:
    """Assert ``entity_identifier`` rows for lane-scheme candidates (insert-only).

    Dry-run by default: without ``apply`` the same scan counts what *would* be
    asserted and writes nothing. ``after`` is the keyset cursor; ``limit``
    bounds total rows scanned.
    """
    schemes = [str(s) for s in schemes]
    report = IntakeReport()
    cursor = after
    remaining = limit
    while True:
        size = batch_size if remaining is None else min(batch_size, remaining)
        if size <= 0:
            break
        rows = conn.execute(_CANDIDATES_SQL, (schemes, cursor, size)).fetchall()
        if not rows:
            break
        asserted = 0
        if apply:
            for claim_id, subject_id, scheme, value in rows:
                cur = conn.execute(_ASSERT_SQL, (subject_id, scheme, value, claim_id))
                asserted += cur.rowcount if cur.rowcount is not None else 0
        else:
            # dry-run: count rows whose (entity, scheme, value) triple is new
            asserted = len(rows)
        report.batches.append(
            IntakeBatch(
                scanned=len(rows),
                asserted=asserted,
                last_claim_id=str(rows[-1][0]),
                lanes=tuple(schemes),
                apply=apply,
            )
        )
        cursor = str(rows[-1][0])
        if remaining is not None:
            remaining -= len(rows)
        if len(rows) < size:
            break
    return report


def intake_plan(conn: Any, *, schemes: Sequence[str]) -> dict[str, Any]:
    """Read-only plan: per-scheme pending candidate counts."""
    rows = conn.execute(_ORG_LANE_SQL, ([str(s) for s in schemes],)).fetchall()
    pending = conn.execute(
        "SELECT c.value_json->>'scheme' AS scheme, count(*) "
        "FROM claim c JOIN entity e ON e.entity_id = c.subject_id "
        "WHERE e.entity_type = 'organization' "
        "  AND c.value_json->>'scheme' = ANY(%s::text[]) "
        "  AND c.value_json->>'value' IS NOT NULL AND upper_inf(c.sys_period) "
        "GROUP BY 1 ORDER BY 1",
        ([str(s) for s in schemes],),
    ).fetchall()
    return {
        "schemes": list(schemes),
        "existing": {
            str(s): {"entities": int(e), "distinct_values": int(v), "asserted": int(a)}
            for s, e, v, a in rows
        },
        "pending": {str(s): int(n) for s, n in pending},
    }


def org_identity_report(conn: Any) -> dict[str, Any]:
    """The ``sig.org-crosswalk-report/1`` measurement (GQ-21's org half; the
    duplicate-agency rate against the L2 baseline — CP-10 acceptance shape)."""
    schemes = list(lane_schemes().values())
    total_orgs = int(conn.execute(_ORG_TOTAL_SQL).fetchone()[0])
    lanes = {
        str(s): {"entities": int(e), "distinct_values": int(v), "asserted_rows": int(a)}
        for s, e, v, a in conn.execute(_ORG_LANE_SQL, (schemes,)).fetchall()
    }
    dup_pairs = int(conn.execute(_ORG_DUP_SQL, (schemes,)).fetchone()[0])
    name_rows = conn.execute(_ORG_NAME_DUP_SQL).fetchone()
    name_groups, name_dup_groups = int(name_rows[0]), int(name_rows[1])
    name_dup_rate = (name_dup_groups / name_groups) if name_groups else None
    return {
        "record_type": REPORT_SCHEMA,
        "baseline_l2": dict(L2_DUPLICATE_BASELINE),
        "organization_entities": total_orgs,
        "lanes": lanes,
        "identifier_shared_entity_pairs": dup_pairs,
        "name_duplicate_groups": name_dup_groups,
        "name_groups": name_groups,
        "name_duplicate_rate": name_dup_rate,
        "rate_fell_vs_l2": (
            None
            if name_dup_rate is None
            else name_dup_rate < float(str(L2_DUPLICATE_BASELINE["duplicated_share"]))
        ),
    }


def run(
    dsn: str,
    *,
    lanes: Sequence[str] | None = None,
    apply: bool = False,
    limit: int | None = None,
    batch_size: int = 1_000,
) -> dict[str, Any]:
    """The ``sig-db crosswalk-intake`` entry point: plan, apply and report."""
    import psycopg

    by_lane = lane_schemes()
    wanted = list(lanes) if lanes else list(by_lane)
    unknown = [x for x in wanted if x not in by_lane]
    if unknown:
        raise ValueError(f"unknown crosswalk lanes {unknown} (known: {sorted(by_lane)})")
    schemes = sorted({by_lane[x] for x in wanted})
    with psycopg.connect(dsn, autocommit=False) as conn:
        plan = intake_plan(conn, schemes=schemes)
        report = assert_lane_identifiers(
            conn, schemes=schemes, apply=apply, limit=limit, batch_size=batch_size
        )
        org_report = org_identity_report(conn)
        if apply:
            conn.commit()
        else:
            conn.rollback()
    return {
        "mode": "apply" if apply else "plan",
        "lanes": wanted,
        "schemes": schemes,
        "plan": plan,
        "scanned": report.scanned,
        "asserted": report.asserted,
        "batches": len(report.batches),
        "report": org_report,
    }
