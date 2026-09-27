# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared bitemporal occurrence-selection contract (P32.4 / SIG-TRUST-005).

**One selection rule for every reader.** Before P32.4 each reader invented its own
"latest": the API/materializer dated an undated claim from ``max(retrieved_at)``
over *every* evidence link (no belief bound, no role filter), the camera-site
reader picked ``DISTINCT ON ... ORDER BY claim_id DESC`` (a claim id is not a
clock), and the API's annotation watermark counted the whole spine per request
(~10 s under ``pg_stat_statements``, the ``D-P31.1-1`` defect). This module is the
single contract they all share:

* a **belief bound** — only knowledge recorded at or before the belief instant is
  visible (``sys_period @> belief`` for assertions; ``bound_at <= belief`` for
  evidence bindings, so a later capture/replay/correction can never re-date a
  frozen past-belief read);
* a **valid-world bound** — ``valid_period`` (or ``valid_from``/``valid_to``)
  must intersect the read's world instant, so a future-effective law is not
  effective early;
* an **occurrence** — one ``claim_evidence`` row binding a claim to a capture,
  i.e. one *sighting*. Only ``role = 'establishes'`` bindings are sightings of
  the source asserting the value; the latest *eligible* occurrence is the most
  recent sighting the belief bound can see;
* an **observation dating with an explicit fallback basis** — a dated claim
  keeps its asserted ``observed_at`` (basis ``"claim"``); an undated claim is
  dated from its latest eligible occurrence's ``retrieved_at`` (basis
  ``"capture_retrieved_at_latest"``, labelled by the resolver as an inference);
  a claim with neither stays undated at the 1970 placeholder — historical, never
  silently current. Date-only source values keep date precision on
  ``observed_at``; the *ordering* instant (``observed_instant``) is carried
  separately at full precision so same-day re-sightings order correctly;
* **deterministic ties** — order keys are real temporal fields
  (``retrieved_at``/``observed_at``/``bound_at``) first; a row id breaks an
  exact-time tie for total ordering but is never used *as* a timestamp;
* **per-lineage concurrent candidates** — selection returns the latest eligible
  claim *within each source lineage*; two independent sources disagreeing at one
  instant stay concurrent candidates (visible contradiction, §3.1) rather than
  being collapsed by a subject-wide ``MAX``.

## Pure conformance model vs SQL

The pure functions below take plain row values and implement the same rule the
SQL fragment (:func:`occurrence_lateral`) and the ``sig.eligible_occurrence``
sqitch function implement server-side. Tests run identical fixture vectors
through both and require identical selections (fixture/PG parity).

## Transaction/snapshot semantics

* The **API** read path (``api.store_pg``) runs each read in one implicit
  statement snapshot on a pooled connection; the annotation/shaping compute
  reads the watermark *first* so the disclosed watermark never overstates the
  computed state (a newer write between the two snapshots makes the disclosed
  value conservative, never stale-in-the-dangerous-direction).
* The **export** (``exports.spine_export.run_spine_export``) and shaping compute
  (``exports.shaping.run_shaping``) fetch inside one explicit
  ``REPEATABLE READ READ ONLY`` snapshot, so the watermark row, the claims, and
  the materialization reads all see the same spine state.
* The **materializers** read occurrences with ``clock_timestamp()`` (current
  knowledge) inside their own transaction; belief-pinned reads pass the instant
  explicitly.
* The **watermark** is a trigger-maintained ``spine_watermark`` table: one row
  per watched relation facet. Every statement-level trigger bumps its facet on
  ``INSERT``/``UPDATE``/``TRUNCATE``, so a read of the table is O(facets),
  bounded, and snapshot-consistent by construction. Any watched write changes
  ``bump`` → every cached serve keyed on the watermark invalidates exactly once
  and can never serve stale (over-invalidation is safe; under-invalidation is
  the bug this closes).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

#: Contract version stamped into ADR-123 and echoed in build memory so the
#: selection rule itself is versioned (a rule change = a version bump + ADR).
CONTRACT_VERSION = "temporal-read/1"

#: The only evidence role that counts as a sighting of the source asserting the
#: value (§13.3). ``corroborates``/``contextualizes``/``contradicts``/… links
#: must never re-date the claim — a refutation is not a re-assertion.
ESTABLISHING_ROLE = "establishes"

#: ``observed_at_basis`` labels — kept byte-identical to the pre-P32.4 names so
#: resolver ``rules_fired`` labels and stored decisions stay comparable.
CLAIM_BASIS = "claim"
CAPTURE_BASIS = "capture_retrieved_at_latest"

#: The documented undated fallback: a claim with no ``observed_at`` and no
#: eligible occurrence stays at the 1970 placeholder — HISTORICAL, never
#: silently current.
UNDATED_DATE = date(1970, 1, 1)

#: SQL belief expressions callers splice into :func:`occurrence_lateral`.
#: ``BELIEF_PARAM`` is a ``%s`` placeholder — callers append the belief value to
#: their parameter list (psycopg binds it server-side; the expression text is a
#: module constant, never caller SQL).
BELIEF_NOW = "clock_timestamp()"
BELIEF_PARAM = "%s::timestamptz"


# --------------------------------------------------------------------------- #
# Pure conformance model                                                       #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Binding:
    """One ``claim_evidence`` row — the occurrence edge between an assertion and
    a capture (one *sighting*).

    ``bound_at`` is the link's knowledge instant (P32.2): when the spine first
    knew this binding. A binding minted by a later re-sighting, replay link or
    correction carries a later ``bound_at`` and so cannot affect a frozen
    earlier belief read.
    """

    claim_id: str
    capture_id: str | None
    role: str
    bound_at: datetime | None
    retrieved_at: datetime | None
    source_id: str | None = None
    artifact_id: str | None = None
    binding_status: str | None = None


@dataclass(frozen=True)
class Occurrence:
    """The selected latest *eligible* establishing occurrence of one claim."""

    capture_id: str | None
    source_id: str | None
    retrieved_at: datetime | None
    bound_at: datetime | None


@dataclass(frozen=True)
class Observation:
    """The contract's dating for one claim: the date-precision value plus the
    exact ordering instant, the fallback basis label, and the occurrence
    reference that produced it (refs preserved for outputs)."""

    observed_at: date
    instant: datetime | None
    basis: str
    occurrence: Occurrence | None


def _aware(value: Any) -> datetime | None:
    """Normalize PG/Python datetime-or-date to an aware UTC instant."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return None


def _utc_date(value: Any) -> date:
    """The UTC calendar date of an instant (session-tz independent)."""
    aware = _aware(value)
    return aware.date() if aware is not None else UNDATED_DATE


def known_at(sys_from: Any, sys_to: Any, belief: datetime) -> bool:
    """Belief eligibility — the pure form of ``sys_period @> belief``."""
    start = _aware(sys_from)
    end = _aware(sys_to)
    if start is not None and start > belief:
        return False
    return end is None or end > belief


def valid_at(valid_from: Any, valid_to: Any, world: date) -> bool:
    """Valid-world eligibility — the pure form of the resolver's
    ``_intersects_world``: open bounds are unbounded; a ``valid_to`` is
    exclusive (future-effective law is not effective early)."""
    vf = valid_from if isinstance(valid_from, date) else None
    vt = valid_to if isinstance(valid_to, date) else None
    if vf is not None and world < vf:
        return False
    if vt is not None and world >= vt:
        return False
    return True


def eligible_bindings(bindings: Iterable[Binding], belief: datetime | None) -> list[Binding]:
    """Bindings a belief-``belief`` reader may see: establishing role only, with
    ``bound_at <= belief``. ``belief=None`` means "current knowledge" (all
    bindings recorded so far)."""
    out: list[Binding] = []
    for b in bindings:
        if b.role != ESTABLISHING_ROLE:
            continue
        bound = _aware(b.bound_at)
        if belief is not None and bound is not None and bound > belief:
            continue
        out.append(b)
    return out


def _occurrence_key(b: Binding) -> tuple[object, ...]:
    """``retrieved_at DESC NULLS LAST, capture_id ASC`` — identical to the SQL."""
    instant = _aware(b.retrieved_at)
    return (
        1 if instant is None else 0,  # NULLS LAST
        -(instant.timestamp()) if instant is not None else 0.0,
        b.capture_id or "",  # deterministic tie — never used as time
    )


def select_occurrence(
    bindings: Iterable[Binding], belief: datetime | None = None
) -> Occurrence | None:
    """The latest eligible establishing occurrence, or ``None``.

    Pure twin of :func:`occurrence_lateral` / ``sig.eligible_occurrence``.
    """
    eligible = eligible_bindings(bindings, belief)
    if not eligible:
        return None
    best = min(eligible, key=_occurrence_key)
    return Occurrence(
        capture_id=best.capture_id,
        source_id=best.source_id,
        retrieved_at=_aware(best.retrieved_at),
        bound_at=_aware(best.bound_at),
    )


def select_observation(
    *,
    observed_at: Any,
    bindings: Iterable[Binding] = (),
    belief: datetime | None = None,
) -> Observation:
    """The contract dating for one claim.

    * dated claim → its own ``observed_at`` (basis ``"claim"``; retrieval time
      is a fallback basis only for *undated* observational claims — a dated
      assertion keeps its asserted instant even when re-sighted);
    * undated claim → latest eligible occurrence's ``retrieved_at`` (basis
      ``"capture_retrieved_at_latest"``);
    * neither → the 1970 placeholder (historical; never silently current).

    The *occurrence* is returned in every branch so outputs can preserve the
    evidence reference of the latest eligible sighting even for dated claims.
    """
    occurrence = select_occurrence(bindings, belief)
    if observed_at is not None:
        return Observation(
            observed_at=_utc_date(observed_at),
            instant=_aware(observed_at),
            basis=CLAIM_BASIS,
            occurrence=occurrence,
        )
    if occurrence is not None and occurrence.retrieved_at is not None:
        return Observation(
            observed_at=_utc_date(occurrence.retrieved_at),
            instant=occurrence.retrieved_at,
            basis=CAPTURE_BASIS,
            occurrence=occurrence,
        )
    return Observation(
        observed_at=UNDATED_DATE, instant=None, basis=CLAIM_BASIS, occurrence=occurrence
    )


def observation_instant(observed_at: Any, retrieved_at: Any) -> datetime | None:
    """The exact ordering instant the contract supplies to readers that select
    the occurrence server-side: the claim's own ``observed_at`` when dated, else
    the latest eligible occurrence's ``retrieved_at``, else ``None`` (undated —
    the reader falls back to the 1970 placeholder). Mirrors
    :func:`select_observation` for the SQL-side join."""
    return _aware(observed_at) or _aware(retrieved_at)


def ordering_instant(instant: datetime | None, observed_at: date) -> datetime:
    """The exact ordering instant used for recency comparisons.

    ``instant`` when the contract supplied one (full precision); else the
    date-precision ``observed_at`` at UTC midnight — a single comparable axis
    for mixed date-only/instanced claims.
    """
    if instant is not None:
        return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)
    return datetime(observed_at.year, observed_at.month, observed_at.day, tzinfo=UTC)


def lineage_candidates(rows: Sequence[Any]) -> list[Any]:
    """The latest member per source lineage — concurrent candidates preserved.

    ``rows`` must expose ``source_id``, ``claim_id`` and either
    ``ordering_instant`` (property, e.g. ``resolve.Claim``) or
    ``observed_instant`` + ``observed_at`` (e.g. ``ShapingClaim``). Latest per
    ``(source_id or claim_id)`` by ordering instant; ``claim_id`` breaks an
    exact-time tie — deterministic, never a timestamp.
    """

    def instant(r: Any) -> datetime:
        got = getattr(r, "ordering_instant", None)
        if isinstance(got, datetime):
            return got
        return ordering_instant(getattr(r, "observed_instant", None), r.observed_at or UNDATED_DATE)

    best: dict[str, Any] = {}
    for r in rows:
        key = getattr(r, "source_id", None) or r.claim_id
        cur = best.get(key)
        if cur is None or (instant(r), r.claim_id) > (instant(cur), cur.claim_id):
            best[key] = r
    return [best[k] for k in sorted(best, key=lambda k: best[k].claim_id)]


# --------------------------------------------------------------------------- #
# SQL fragments — the server-side twin of the pure model                        #
# --------------------------------------------------------------------------- #

#: ``retrieved_at DESC NULLS LAST, capture_id ASC`` — identical to
#: :func:`_occurrence_key` and to ``sig.eligible_occurrence``.
_OCCURRENCE_ORDER = "ec2.retrieved_at DESC NULLS LAST, ce2.capture_id ASC"


def claim_source_cte(bound_sql: str = BELIEF_NOW) -> str:
    """The shared ``claim_source`` CTE fragment (with a leading comma).

    Per claim, its latest *eligible* establishing occurrence — the same
    selection as :func:`occurrence_lateral` / ``sig.eligible_occurrence``
    (``role='establishes'``, ``bound_at <=`` the bound expression, same
    ordering) — rendered as the ``claim_source`` CTE the export queries join for
    per-claim source attribution and occurrence refs. Column contract:
    ``claim_id, source_id, capture_id, retrieved_at, bound_at``.

    ``bound_sql`` is a *constant SQL expression* — :data:`BELIEF_PARAM` or
    :data:`BELIEF_NOW` — never caller input.
    """
    return (
        ", claim_source AS ("
        "  SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id,"
        "         ce.capture_id, ec.retrieved_at, ce.bound_at"
        "    FROM claim_evidence ce"
        "    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "   WHERE ce.role = 'establishes'"
        f"     AND ce.bound_at <= {bound_sql}"
        "   ORDER BY ce.claim_id, ec.retrieved_at DESC NULLS LAST, ce.capture_id ASC"
        ") "
    )


def occurrence_lateral(
    belief_sql: str = BELIEF_NOW,
    *,
    claim_alias: str = "c",
    out_alias: str = "occ",
) -> str:
    """The shared eligible-occurrence ``LATERAL`` join fragment.

    Selects, per claim, the *latest eligible establishing occurrence*: only
    ``role='establishes'`` bindings, ``bound_at <= belief``. Column contract on
    ``out_alias``: ``capture_id``, ``source_id``, ``artifact_type``,
    ``retrieved_at``, ``bound_at`` — everything a reader needs for dating plus
    the occurrence/evidence references outputs preserve.

    ``belief_sql`` is a *constant SQL expression* supplied by the caller —
    :data:`BELIEF_PARAM` (a ``%s`` placeholder; append the belief instant to the
    query's params) or :data:`BELIEF_NOW`. Never caller input.
    """
    return (
        "  LEFT JOIN LATERAL ("
        "     SELECT ce2.capture_id, ea2.source_id, ea2.artifact_type,"
        "            ec2.retrieved_at, ce2.bound_at"
        "       FROM claim_evidence ce2"
        "       JOIN evidence_capture ec2 ON ec2.capture_id = ce2.capture_id"
        "       JOIN evidence_artifact ea2 ON ea2.artifact_id = ec2.artifact_id"
        f"      WHERE ce2.claim_id = {claim_alias}.claim_id"
        f"        AND ce2.role = '{ESTABLISHING_ROLE}'"
        f"        AND ce2.bound_at <= {belief_sql}"
        f"      ORDER BY {_OCCURRENCE_ORDER}"
        f"      LIMIT 1) {out_alias} ON true "
    )


# --------------------------------------------------------------------------- #
# The materialized spine watermark (D-P31.1-1)                                  #
# --------------------------------------------------------------------------- #

#: Facets the trigger-maintained ``spine_watermark`` table tracks — the superset
#: of every relation the API's annotation/shaping compute-on-read paths read
#: (claims + evidence chain + qualifiers + rights + run/completion state +
#: entities + persisted annotations) plus every completed-materialization
#: relation. The watched set is deliberately a superset: a facet that bumps
#: needlessly costs one recompute; a missed relation is a stale serve.
WATERMARK_FACETS: tuple[str, ...] = (
    "claim",
    "claim_evidence",
    "claim_qualifier",
    "evidence_capture",
    "evidence_artifact",
    "evidence_blob",
    "extraction",
    "ingest_run",
    "ingest_run_capture",
    "ingest_run_completion",
    "rights_record",
    "rights_decision",
    "source_registry",
    "entity",
    "entity_identifier",
    "organization",
    "organization_relation",
    "relationship",
    "resolution",
    "contradiction",
    "coverage_record",
    "research_task",
    "review_item",
    "review_decision",
    "camera_site_run",
    "camera_site_match",
    "camera_site_execution",
)

#: The bounded read — O(#facets) on a 26-row table, no claim-spine scan.
WATERMARK_SQL = (
    "SELECT facet, row_count, closed_count, latest_instant, bump"
    " FROM spine_watermark ORDER BY facet"
)

#: Pre-P32.4 fallback for a spine deployed before ``shared_temporal_contract``:
#: the legacy six-count scan (kept so readers degrade honestly on old dumps).
LEGACY_WATERMARK_SQL = (
    "SELECT (SELECT count(*) FROM claim),"
    "       (SELECT count(*) FROM claim WHERE upper(sys_period) IS NOT NULL),"
    "       (SELECT max(lower(sys_period)) FROM claim),"
    "       (SELECT count(*) FROM claim_evidence),"
    "       (SELECT count(*) FROM evidence_capture),"
    "       (SELECT count(*) FROM evidence_artifact)"
)


def spine_watermark(cur: Any) -> str:
    """The append-only spine watermark string (D-P31.1-1).

    Reads the trigger-maintained ``spine_watermark`` table — O(#facets), bounded
    by construction, and *never stale*: any INSERT/UPDATE/TRUNCATE on a watched
    relation bumps its facet in the same transaction, so the watermark the
    reader sees is exactly the committed state of the snapshot it reads. The
    disclosed string keeps the legacy ``claims=… closed=… latest_assertion=…
    evidence=…`` prefix and appends the remaining facets plus the monotone
    ``bump`` total so any change is visible to a comparing reader.
    """
    # ``conn.execute(...)`` returns a cursor in psycopg — chain fetch on the
    # result so this works with a Connection as well as a Cursor.
    present = cur.execute("SELECT to_regclass('spine_watermark') IS NOT NULL").fetchone()
    if not (present and present[0]):
        claims, closed, latest, ce, ec, ea = cur.execute(LEGACY_WATERMARK_SQL).fetchone()
        return (
            f"claims={claims} closed={closed} "
            f"latest_assertion={latest.isoformat() if latest else 'none'} "
            f"evidence={ce}/{ec}/{ea} v=legacy"
        )
    facets: dict[str, tuple[Any, ...]] = {
        r[0]: r[1:] for r in cur.execute(WATERMARK_SQL).fetchall()
    }
    total_bump = sum(int(v[3]) for v in facets.values())
    claim = facets.get("claim", (0, 0, None, 0))
    latest = claim[2]
    prefix = (
        f"claims={claim[0]} closed={claim[1]} "
        f"latest_assertion={latest.isoformat() if latest else 'none'} "
        f"evidence={facets.get('claim_evidence', (0,))[0]}"
        f"/{facets.get('evidence_capture', (0,))[0]}"
        f"/{facets.get('evidence_artifact', (0,))[0]}"
    )
    rest = " ".join(
        f"{f}={facets[f][0]}"
        for f in WATERMARK_FACETS
        if f in facets
        and f not in ("claim", "claim_evidence", "evidence_capture", "evidence_artifact")
    )
    return f"{prefix} {rest} v={total_bump}"


def row_bindings(cur: Any, claim_ids: Sequence[str]) -> dict[str, list[Binding]]:
    """Fetch ``claim_evidence`` bindings for a set of claims — the pure-model
    input for tests/tools that need per-claim occurrence detail."""
    if not claim_ids:
        return {}
    rows = cur.execute(
        "SELECT ce.claim_id::text, ce.capture_id::text, ce.role, ce.bound_at,"
        "       ec.retrieved_at, ea.source_id, ec.artifact_id::text,"
        "       ce.binding_status"
        "  FROM claim_evidence ce"
        "  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id"
        "  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id"
        " WHERE ce.claim_id = ANY(%s::uuid[])"
        " ORDER BY ce.claim_id, ec.retrieved_at DESC, ce.capture_id",
        (list(claim_ids),),
    ).fetchall()
    out: dict[str, list[Binding]] = {}
    for r in rows:
        out.setdefault(str(r[0]), []).append(
            Binding(
                claim_id=str(r[0]),
                capture_id=str(r[1]) if r[1] is not None else None,
                role=str(r[2]),
                bound_at=_aware(r[3]),
                retrieved_at=_aware(r[4]),
                source_id=str(r[5]) if r[5] is not None else None,
                artifact_id=str(r[6]) if r[6] is not None else None,
                binding_status=str(r[7]) if r[7] is not None else None,
            )
        )
    return out
