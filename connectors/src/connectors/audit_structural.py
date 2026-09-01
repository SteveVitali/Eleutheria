# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `audit_structural` connector — the Flock audit-export layer (§23.7, P11.2).

This connector ingests the **agency's own** Flock audit CSV exports — the
Organization / Network / Portal-Public audits, the Event Logs, and
``SharedNetworks.csv`` — obtained as public records (source
``agency_audit_export``), and lands them as **structural aggregates and configured
edges only**. It is emphatically **not** the derived HIBF bulk export: a derived
artifact (hashed plates, inferred names, redacted reasons, injected annotations)
MUST NOT be ingested as though it were the agency's primary record
(SIG-INGEST-046a).

The audit layer is exactly where the Part VIII bright line bites — *"no searchable
database of people's movements"* — so the load-bearing discipline of this module is
that **no per-search or per-plate row is ever produced anywhere** (§18.1,
SIG-STORE-025). The per-search rows of an audit export are read **transiently**,
aggregated in :func:`aggregate_search_events`, and dropped; only the aggregates
leave the connector. :func:`assert_no_per_row_output` is the schema gate that
proves it — an emitted row carrying any plate / per-search / officer column is a
hard error (SIG-STORE-026).

This module owns the parts of §23.7 the framework does not provide:

* **Structural aggregates only** (:class:`UsageAggregate`, §11.16): per-search
  events are binned by ``(searching_org, source_org, reason_category, month,
  search_scope)`` and counted; the finest stored granularity is one month (§18.4).
  Overlapping exports are de-duplicated at the event level before aggregation and
  the overlap recorded (§23.7 "Duplicate handling").
* **The audit ``Camera Count`` as an independent count claim** (§23.7, §29.1):
  it lands under ``active_device_count`` (the basis the audit export attests) and
  is reconciled against the other count bases by **P08.2's**
  :func:`reconcile.counts.reconcile_counts` — surfaced as a distinct observation,
  **never merged** into another count (SIG-RECON-026).
* **``SharedNetworks.csv`` as configured access, directional, blanks-as-negatives**
  (SIG-ONTO-042/044): each row's outbound / inbound partner lists become
  directional :class:`reconcile.sharing.SharingObservation` objects and are
  reconciled — across the whole file, so asymmetry can fire — through P08.2's §29.3
  :func:`reconcile.sharing.reconcile_sharing`. Every single-snapshot edge carries
  ``valid_from_kind = 'unknown'`` (SIG-RECON-036).
* **``***`` redaction distinguished from empty** (:func:`classify_cell`,
  SIG-INGEST-046): a redacted cell is a distinct, recorded state — never conflated
  with a missing or blank value.
* **The four audit source types kept non-interchangeable** (§23.7): every
  aggregate carries its ``audit_source_type`` provenance and the connector refuses
  to silently union rows across types.

Every row is append-only (P1–P3): no current-value columns, raw values preserved,
corrections are new assertions resolved downstream (P08.x), never overwrites. The
export compartment is decided per source by the licence gate (SIG-LIC-009a), so —
like ``records`` — this connector does not pin a compartment here. The
``UsageAggregate`` DuckDB/Parquet substrate, small-cell suppression, and the
UUID+period join are **P12.1's** to build (§18); this ticket writes the aggregates.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from reconcile.counts import reconcile_counts
from reconcile.model import CountClaim as _CountClaim
from reconcile.model import CountReconciliation, Evidence
from reconcile.sharing import (
    ACCESS_KINDS,
    SharingObservation,
    SharingReconciliation,
    reconcile_sharing,
)

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

#: The registry source this connector runs against — the agency's OWN audit
#: exports obtained as public records (§23.7), NOT the derived HIBF export.
AGENCY_AUDIT_SOURCE_ID = "agency_audit_export"

#: The subject-id prefixes for the entities this connector keys on.
AGGREGATE_ID_PREFIX = "usage_aggregate"
ORG_ID_PREFIX = "audit_org"
DEPLOYMENT_ID_PREFIX = "audit_deployment"

#: The distinct states a single audit cell can be in (SIG-INGEST-046, `***` != empty).
CELL_PRESENT = "present"
CELL_EMPTY = "empty"
CELL_REDACTED = "redacted"

_DETECTOR_VERSION = "connectors.audit_structural/1"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `audit_structural` vocabulary (``data/audit_structural_vocab.toml``)."""
    return load_table("audit_structural_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def audit_source_types() -> tuple[str, ...]:
    """The four audit source types — NOT interchangeable (§23.7 / §11.16)."""
    return tuple(vocab()["audit_source_types"])


def redaction_sentinel() -> str:
    """The sentinel a Flock audit export writes into a withheld cell (`***`)."""
    return str(vocab()["redaction_sentinel"])


def _aggregate_spec() -> Mapping[str, Any]:
    return vocab()["aggregate"]


def _camera_spec() -> Mapping[str, Any]:
    return vocab()["camera_count"]


def _sharing_spec() -> Mapping[str, Any]:
    return vocab()["sharing"]


def _event_spec() -> Mapping[str, Any]:
    return vocab()["event_log"]


def _provenance_spec() -> Mapping[str, Any]:
    return vocab()["provenance"]


def _reason_map() -> Mapping[str, str]:
    return vocab()["reason_categories"]


# --- the audit source types (non-interchangeable, §23.7) ----------------------


class UnknownAuditSourceType(Exception):
    """Raised when a capture declares an audit source type outside the four (§23.7)."""


def assert_audit_source_type(audit_source_type: str) -> str:
    """Return ``audit_source_type`` if one of the four, else raise (§23.7).

    The four types are **not interchangeable**; a capture whose declared type is
    outside the closed set is refused rather than silently coerced or unioned.
    """
    if audit_source_type not in audit_source_types():
        raise UnknownAuditSourceType(
            f"audit source type {audit_source_type!r} is not one of the four "
            f"non-interchangeable types {list(audit_source_types())} (§23.7); the "
            "connector refuses to silently union it."
        )
    return audit_source_type


# --- the predicate allowlist + the §18.1 per-row bright line ------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


class PerRowLeak(Exception):
    """A schema error: an emitted row carried a per-search / per-plate column (§18.1)."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.7)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (§23.7)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §18.1 places out of scope (per-search/plate/person, officer id)."""
    return tuple(vocab()["forbidden_predicate_genres"])


def forbidden_output_columns() -> frozenset[str]:
    """Column names/substrings that MUST NEVER appear on an emitted row (§18.1)."""
    return frozenset(str(c).lower() for c in vocab()["forbidden_output_columns"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The `audit_structural` connector may write only the §23.7 structural
    predicates: any per-search or per-plate row is refused here, at the ingestion
    boundary, not merely at resolution (SIG-INGEST-033 analogue / §18.1).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the audit_structural connector may write only {sorted(predicate_allowlist())} "
            f"(§23.7, §18.1); {predicate!r} is outside the allowlist — per-search, per-plate, "
            "and per-person rows are refused."
        )
    return predicate


def assert_no_per_row_output(rows: Iterable[Mapping[str, Any]]) -> None:
    """Assert no emitted row carries a per-search / per-plate / officer column (§18.1).

    The bright line is a **schema property**, not a policy note (SIG-STORE-025/026):
    a claim capable of holding a licence plate, a per-search id, or an officer
    identity would be exactly the per-plate leak Part VIII forbids. Any emitted row
    whose keys collide with :func:`forbidden_output_columns` is a hard error.
    """
    banned = forbidden_output_columns()
    for row in rows:
        for key in row:
            k = str(key).lower()
            if k in banned or any(b in k for b in banned):
                raise PerRowLeak(
                    f"row {row.get('record_kind', '?')!r} carries forbidden per-search/"
                    f"per-plate column {key!r} (§18.1, SIG-STORE-025/026); aggregates only."
                )


# --- CSV parsing + the structural canary --------------------------------------


def parse_csv(data: bytes) -> dict[str, Any]:
    """Parse an audit CSV into a header + list of row dicts (pure fn of the capture).

    Kept a pure function of the captured bytes (SIG-INGEST-002): the connector
    reads the archived capture back and calls this, never the network.
    """
    text = data.decode("utf-8-sig")  # tolerate a UTF-8 BOM on the upstream export
    reader = csv.DictReader(io.StringIO(text))
    header = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return {"header": header, "rows": rows}


def _resolve_column(header: Sequence[str], aliases: Iterable[str]) -> str | None:
    """The first alias present in ``header`` (the agency-configured schema, §23.7)."""
    present = set(header)
    for alias in aliases:
        if alias in present:
            return str(alias)
    return None


def canary_findings(parsed: Mapping[str, Any], *, file_kind: str) -> list[str]:
    """Structural-drift findings for one audit capture (SIG-PARSE-008 canary).

    Committed fixtures (SIG-PARSE-007) pin known inputs and pass forever but
    cannot catch an upstream that quietly changes shape; the canary is the
    complement, run against a live export on a cadence. It asserts only the
    structure the parser depends on for ``file_kind`` — never field *values*. An
    empty list means no drift.
    """
    findings: list[str] = []
    header = parsed.get("header")
    if not isinstance(header, list):
        return ["missing CSV header"]
    if file_kind == "shared_networks":
        spec = _sharing_spec()
        if _resolve_column(header, [str(spec["org_field"])]) is None:
            findings.append(f"missing sharing org column {spec['org_field']!r}")
        return findings
    if file_kind == "event_log":
        spec = _event_spec()
        for role, aliases in (
            ("subject", spec["subject_columns"]),
            ("state", spec["state_columns"]),
        ):
            if _resolve_column(header, aliases) is None:
                findings.append(f"missing event-log {role} column (tried {list(aliases)})")
        return findings
    agg = _aggregate_spec()
    if _resolve_column(header, agg["searching_org_columns"]) is None:
        findings.append("missing a searching-organization column")
    return findings


# --- the redaction distinction (`***` != empty, SIG-INGEST-046) ---------------


def classify_cell(value: object) -> str:
    """Classify one audit cell: :data:`CELL_REDACTED`, :data:`CELL_EMPTY`, or present.

    A ``***`` cell is a **distinct, recorded state** — the export withheld a value
    it had — and MUST NOT be conflated with an empty or missing cell, which is the
    absence of a value (SIG-INGEST-046). This distinction is the single function
    every reader of an audit cell goes through.
    """
    if value is None:
        return CELL_EMPTY
    text = str(value).strip()
    if text == redaction_sentinel():
        return CELL_REDACTED
    if not text:
        return CELL_EMPTY
    return CELL_PRESENT


def is_redacted(value: object) -> bool:
    """Whether a cell is the distinct redacted state (`***`), not empty."""
    return classify_cell(value) == CELL_REDACTED


# --- reason / period normalization (§11.16, §18.4) ----------------------------


def reason_category(raw: object) -> str:
    """The normalized ``reason_category`` for an audit reason (§11.16; raw retained).

    ``***`` maps to the distinct ``redacted`` category (never ``unspecified``); a
    blank/absent reason maps to ``unspecified``; a recognised reason maps through
    the versioned vocabulary; anything else falls to ``other`` (raw_value kept, P2).
    """
    state = classify_cell(raw)
    if state == CELL_REDACTED:
        return CELL_REDACTED
    if state == CELL_EMPTY:
        return "unspecified"
    return _reason_map().get(str(raw).strip().lower(), "other")


def period_month(raw: object) -> str | None:
    """Floor an audit timestamp to its ``YYYY-MM`` month (§18.4), or ``None``.

    The finest stored granularity is one month: the per-search timestamp is read
    ONLY to derive this month for the aggregate ``period`` and is then dropped —
    the finer time is never stored (§18.1).
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m",
    ):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None


# --- structural aggregation (§11.16, §18.1/§18.4) -----------------------------


@dataclass(frozen=True)
class UsageAggregate:
    """The runtime shape of a §11.16 ``UsageAggregate`` — structural, never per-row.

    Carries the §11.16 predicate surface: ``searching_org`` / ``source_org`` (both
    required — the direction is the point), the aggregated ``period`` (a month,
    §18.4), the ``count``, the ``search_scope`` and normalized ``reason_category``
    (with the raw reason retained, P2), the non-interchangeable ``audit_source_type``
    (§23.7), and the ``coverage_period`` the underlying audit actually covered
    (distinct from ``period``). Source-agency provenance — the export it came from
    and that export's requesting agency (§23.7) — travels with every aggregate.
    """

    searching_org: str
    source_org: str
    period: str
    count: int
    audit_source_type: str
    coverage_period: str
    search_scope: str | None = None
    reason_category: str = "unspecified"
    reason_raw: str | None = None
    requesting_agency: str | None = None
    audit_export_id: str | None = None

    @property
    def subject_id(self) -> str:
        """The claim subject id for this aggregate (searching->source, scoped)."""
        return (
            f"{AGGREGATE_ID_PREFIX}:{self.source_org}:{self.searching_org}:"
            f"{self.period}:{self.reason_category}:{self.search_scope or 'any'}"
        )

    def to_row(self) -> dict[str, Any]:
        """The append-only ``usage_aggregate`` row for this aggregate (§11.16)."""
        return {
            "record_kind": "usage_aggregate",
            "subject_id": self.subject_id,
            "predicate_id": assert_predicate_allowed("usage_search_aggregate"),
            "searching_org": self.searching_org,
            "source_org": self.source_org,
            "period": self.period,
            "coverage_period": self.coverage_period,
            "count": self.count,
            "raw_value": self.count,
            "search_scope": self.search_scope,
            "reason_category": self.reason_category,
            "reason_raw": self.reason_raw,
            # §23.7: the four audit source types are recorded on EVERY aggregate and
            # are not interchangeable.
            "audit_source_type": self.audit_source_type,
            "requesting_agency": self.requesting_agency,
            "audit_export_id": self.audit_export_id,
        }


def _window_block(event: Mapping[str, Any]) -> tuple[str, str, str]:
    """The ``(source_org, searching_org, window)`` block one event belongs to (§23.7)."""
    return (
        str(event.get("source_org", "")),
        str(event.get("searching_org", "")),
        str(event.get("month") or ""),
    )


def deduplicate_events(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], int]:
    """De-duplicate OVERLAPPING EXPORTS by window block; return ``(kept, overlap)``.

    §23.7 "Duplicate handling": overlapping audit exports covering the same period
    MUST be de-duplicated by ``(source_org, searching_org, window)`` **before
    aggregation**, and the overlap recorded. The unit of overlap is the *export*,
    not the event: distinct per-search rows within one export are all genuine
    activity and are kept (each counted). But once a ``(source_org, searching_org,
    window)`` block has been seen from one export, the SAME block arriving from a
    *different* export (``export_id``) is a double-cover and is dropped — the
    dropped rows are the recorded overlap. Events without export provenance are all
    kept (overlap cannot be told without it).
    """
    owner: dict[tuple[str, str, str], object] = {}
    kept: list[Mapping[str, Any]] = []
    overlap = 0
    for event in events:
        block = _window_block(event)
        exp = event.get("export_id")
        if block not in owner:
            owner[block] = exp
            kept.append(event)
        elif owner[block] == exp:
            # Same export covering the block again — a distinct event, kept + counted.
            kept.append(event)
        else:
            # A different export covering an already-seen block — double-cover.
            overlap += 1
    return kept, overlap


def aggregate_search_events(
    events: Sequence[Mapping[str, Any]],
    *,
    audit_source_type: str,
    requesting_agency: str | None = None,
    audit_export_id: str | None = None,
) -> list[UsageAggregate]:
    """Bin transient per-search events into :class:`UsageAggregate` rows (§11.16, §18.1).

    Each ``event`` is a normalized ``{searching_org, source_org, reason,
    search_scope, month}`` mapping read transiently from an audit CSV. Events are
    de-duplicated (§23.7), then grouped by ``(searching_org, source_org,
    reason_category, month, search_scope)`` and counted. **No per-search row is
    returned** — the events are consumed here and only the aggregates leave
    (§18.1). ``coverage_period`` spans the min…max month observed in the batch,
    distinct from each group's ``period``.
    """
    assert_audit_source_type(audit_source_type)
    unique, _overlap = deduplicate_events(events)  # §23.7: overlapping exports deduped
    months = sorted(m for m in (str(e.get("month") or "") for e in unique) if m)
    coverage = f"{months[0]}..{months[-1]}" if months else "unknown"

    groups: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for event in unique:
        searching = str(event.get("searching_org", "")).strip()
        source = str(event.get("source_org", "")).strip()
        if not searching or not source:
            continue  # an aggregate needs both endpoints — the direction is the point
        month = str(event.get("month") or "unknown")
        scope = _opt_str(event.get("search_scope"))
        raw_reason = event.get("reason")
        category = reason_category(raw_reason)
        key = (searching, source, category, month, scope or "any")
        bucket = groups.setdefault(
            key,
            {
                "searching_org": searching,
                "source_org": source,
                "reason_category": category,
                "reason_raw": _opt_str(raw_reason),
                "month": month,
                "search_scope": scope,
                "count": 0,
            },
        )
        bucket["count"] += 1

    out: list[UsageAggregate] = []
    for bucket in groups.values():
        out.append(
            UsageAggregate(
                searching_org=bucket["searching_org"],
                source_org=bucket["source_org"],
                period=bucket["month"],
                count=int(bucket["count"]),
                audit_source_type=audit_source_type,
                coverage_period=coverage,
                search_scope=bucket["search_scope"],
                reason_category=bucket["reason_category"],
                reason_raw=bucket["reason_raw"],
                requesting_agency=requesting_agency,
                audit_export_id=audit_export_id,
            )
        )
    out.sort(key=lambda a: a.subject_id)
    return out


def _normalize_event(
    row: Mapping[str, Any], *, columns: Mapping[str, str | None], export_id: str | None = None
) -> dict[str, Any]:
    """Read one CSV row into a transient event — the finer time is dropped (§18.1).

    ``export_id`` travels on the event so overlapping exports can be de-duplicated
    at the window-block level (§23.7) without collapsing distinct within-export
    searches.
    """
    ts_col = columns.get("timestamp")
    reason_col = columns.get("reason")
    return {
        "searching_org": _cell(row, columns.get("searching_org")),
        "source_org": _cell(row, columns.get("source_org")),
        "reason": row.get(reason_col) if reason_col else None,
        "search_scope": _cell(row, columns.get("scope")),
        "month": period_month(row.get(ts_col)) if ts_col else None,
        "export_id": export_id,
    }


def _aggregate_columns(header: Sequence[str]) -> dict[str, str | None]:
    """Resolve the agency-configured aggregate columns from the header (§23.7)."""
    agg = _aggregate_spec()
    return {
        "searching_org": _resolve_column(header, agg["searching_org_columns"]),
        "source_org": _resolve_column(header, agg["source_org_columns"]),
        "reason": _resolve_column(header, agg["reason_columns"]),
        "scope": _resolve_column(header, agg["scope_columns"]),
        "timestamp": _resolve_column(header, agg["timestamp_columns"]),
    }


# --- redacted-cell records (the distinct state, SIG-INGEST-046) ---------------


def redacted_cell_rows(
    parsed: Mapping[str, Any],
    *,
    columns: Iterable[str],
    subject_id: str,
    audit_source_type: str,
) -> list[dict[str, Any]]:
    """One ``audit_cell_redacted`` row per redacted cell in ``columns`` (SIG-INGEST-046).

    A redacted (`***`) cell is recorded as its own distinct state so the negative
    space is queryable — "this reason was withheld" is different from "this reason
    was blank". The row records which column was redacted and how many rows in the
    capture were redacted for it; it never stores the (withheld) value.
    """
    rows = parsed.get("rows", [])
    out: list[dict[str, Any]] = []
    for column in columns:
        redacted = sum(1 for r in rows if is_redacted(r.get(column)))
        if redacted:
            out.append(
                {
                    "record_kind": "claim",
                    "subject_id": subject_id,
                    "predicate_id": assert_predicate_allowed("audit_cell_redacted"),
                    "redacted_column": column,
                    "redacted_count": redacted,
                    "cell_state": CELL_REDACTED,
                    "raw_value": redaction_sentinel(),
                    "audit_source_type": audit_source_type,
                    "note": "a withheld cell — a distinct recorded state, not conflated with empty",
                }
            )
    return out


# --- the audit `Camera Count` as an independent count claim (§23.7, §29.1) -----


def camera_count_column(header: Sequence[str]) -> str | None:
    """The camera-count column in this audit header, if any (§23.7)."""
    return _resolve_column(header, _camera_spec()["columns"])


def camera_count_claim(
    subject_id: str,
    value: int,
    observed_at: date | None,
    *,
    audit_source_type: str,
    raw_value: object = None,
) -> dict[str, Any]:
    """One audit ``Camera Count`` as an INDEPENDENT ``active_device_count`` claim.

    §23.7 / §29.1: the audit ``Camera Count`` attests the ``active`` count basis
    ("Portal; audit ``Camera Count``; vendor statement"). It lands as its own count
    claim and is reconciled against the other count bases by P08.2
    (:func:`reconcile.counts.reconcile_counts`) — **never merged** into another
    count (SIG-RECON-026). ``count_basis`` travels on the row so the reconciler bins
    it correctly.
    """
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": subject_id,
        "predicate_id": assert_predicate_allowed(str(_camera_spec()["predicate"])),
        "count_basis": str(_camera_spec()["count_basis"]),
        "value": int(value),
        "raw_value": value if raw_value is None else raw_value,
        "genre": str(_camera_spec()["genre"]),
        "audit_source_type": audit_source_type,
    }
    if observed_at is not None:
        row["observed_at"] = observed_at
    return row


def camera_count_observation(
    subject_id: str,
    value: int,
    observed_at: date,
    *,
    reliability: str,
    source_id: str = AGENCY_AUDIT_SOURCE_ID,
    capture_digest: str = "",
) -> _CountClaim:
    """Build the P08.2 :class:`reconcile.model.CountClaim` for an audit Camera Count.

    The genre is ``audit_log`` — the (genre x predicate) directness the registry
    assigns the audit source for ``active_device_count`` — so P08.2's weight
    composition treats it as the audit-derived observation it is.
    """
    genre = str(_camera_spec()["genre"])
    return _CountClaim(
        count_basis=str(_camera_spec()["count_basis"]),
        value=int(value),
        reliability=reliability,
        integrity="I1",
        observed_at=observed_at,
        genre=genre,
        evidence=Evidence(
            source_id=source_id,
            source_family="audit_structural",
            artifact_type=genre,
            stable_locator=subject_id,
            capture_digest=capture_digest,
            locator={"subject_id": subject_id},
        ),
        structured_exact=True,
    )


def reconcile_camera_counts(
    claims: Sequence[_CountClaim],
    *,
    subject_id: str,
    as_of: date,
) -> CountReconciliation:
    """Reconcile audit + other count observations via P08.2 (§29.1, owned there).

    A thin seam over :func:`reconcile.counts.reconcile_counts`: the connector
    supplies the audit ``Camera Count`` as one observation among the count bases;
    P08.2 resolves each basis on its own and surfaces the deltas — it never emits a
    single merged "true count" (SIG-RECON-026/029).
    """
    return reconcile_counts(subject_id, claims, as_of=as_of)


# --- SharedNetworks.csv → configured-access edges (§23.7, SIG-ONTO-042/044) ---


def _parse_org_list(value: object) -> list[str]:
    """Parse a SharedNetworks partner cell to a list; blanks are negatives.

    An empty / missing / blank cell is a **negative** (no configured sharing) and
    returns ``[]`` — never an "unknown" edge. A ``***`` redacted cell is likewise
    not turned into an edge (it is a withheld value, recorded separately). A
    semicolon/comma-separated list is split defensively.
    """
    if classify_cell(value) != CELL_PRESENT:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value)
    parts = text.replace(";", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def sharing_observations(
    parsed: Mapping[str, Any], *, observed_at: date
) -> list[SharingObservation]:
    """Every SharedNetworks row's directional CONFIGURED-ACCESS observations.

    ``Shares With`` means this org has configured access *to* the partner
    (org → partner); ``Receives From`` means a partner has configured access *to*
    this org (partner → org). Both are single snapshots, so
    ``valid_from_kind = 'unknown'`` (SIG-RECON-036). Blank cells are negatives and
    produce no observation. Feeding **all** rows to one reconciliation pass is what
    lets asymmetry fire (SIG-RECON-035).
    """
    spec = _sharing_spec()
    access_kind = str(spec["access_kind"])
    if access_kind not in ACCESS_KINDS:
        raise ValueError(f"invalid sharing access_kind {access_kind!r} in vocabulary")
    org_field = str(spec["org_field"])
    out: list[SharingObservation] = []
    for row in parsed.get("rows", []):
        org = str(row.get(org_field, "")).strip()
        if not org:
            continue
        for partner in _parse_org_list(row.get(str(spec["shared_with_field"]))):
            out.append(
                SharingObservation(
                    asserted_by=org,
                    from_org=org,
                    to_org=partner,
                    access_kind=access_kind,
                    observed_at=observed_at,
                    from_single_snapshot=True,
                )
            )
        for partner in _parse_org_list(row.get(str(spec["received_from_field"]))):
            out.append(
                SharingObservation(
                    asserted_by=org,
                    from_org=partner,
                    to_org=org,
                    access_kind=access_kind,
                    observed_at=observed_at,
                    from_single_snapshot=True,
                )
            )
    return out


def reconcile_audit_sharing(
    parsed: Mapping[str, Any], *, observed_at: date
) -> SharingReconciliation:
    """Reconcile SharedNetworks configured-access edges across the file (via P08.2)."""
    return reconcile_sharing(sharing_observations(parsed, observed_at=observed_at))


def _sharing_edge_rows(reconciled: SharingReconciliation) -> list[dict[str, Any]]:
    """The connector's L1 rows for the reconciled configured-access edges (§29.3).

    Only the **edges** enter the deterministic claim stream. The asymmetry
    contradictions and research tasks are the §29.3 reconciler's to emit and
    persist (owned by P08.2, SIG-RECON-035): folding its freshly-minted
    (non-deterministic) task ids into L1 would break the run's reproducibility
    fingerprint (SIG-INGEST-003).
    """
    rows: list[dict[str, Any]] = []
    for edge in reconciled.edges:
        rows.append(
            {
                "record_kind": "configured_access_edge",
                "subject_id": f"{ORG_ID_PREFIX}:{edge.from_org}",
                "predicate_id": assert_predicate_allowed("configured_sharing_partner"),
                "from_org": edge.from_org,
                "to_org": edge.to_org,
                # §23.7 / SIG-RECON-034: configured access only, never observed_use.
                "access_kind": edge.access_kind,
                # SIG-RECON-036: a single-snapshot edge's start is UNKNOWN.
                "valid_from_kind": edge.valid_from_kind,
                "corroborated": edge.corroborated,
                "observations_count": len(edge.observations),
            }
        )
    return rows


# --- event-log lifecycle transitions (§23.7 writes; §29.4 owned by P08.2) ------


def lifecycle_transition_rows(
    parsed: Mapping[str, Any], *, audit_source_type: str
) -> list[dict[str, Any]]:
    """Dated ``deployment_lifecycle_transition`` rows from an event-log audit (§23.7).

    An event log yields a ``(state, date)`` transition per row, recorded tagged
    with its ``audit_source_type`` so the §29.4 reconciler can prefer event-log
    transitions over inferred ones (REQ-R2-09) — that reconciliation is owned by
    P08.2; this connector only lands the dated transitions.
    """
    spec = _event_spec()
    header = parsed.get("header", [])
    subject_col = _resolve_column(header, spec["subject_columns"])
    state_col = _resolve_column(header, spec["state_columns"])
    date_col = _resolve_column(header, spec["date_columns"])
    out: list[dict[str, Any]] = []
    for row in parsed.get("rows", []):
        subject = _cell(row, subject_col)
        state = _cell(row, state_col)
        if not subject or not state:
            continue
        out.append(
            {
                "record_kind": "claim",
                "subject_id": f"{DEPLOYMENT_ID_PREFIX}:{subject}",
                "predicate_id": assert_predicate_allowed("deployment_lifecycle_transition"),
                "value": {"state": state, "date": _cell(row, date_col)},
                "raw_value": state,
                "audit_source_type": audit_source_type,
            }
        )
    return out


# --- the connector ------------------------------------------------------------


@register
class AuditStructuralConnector(Connector):
    """The `audit_structural` connector: the Flock audit-export layer (§23.7, P11.2).

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire the
    agency audit CSVs through the shared politeness layer; ``parse`` structures the
    CSV, and ``extract``/``normalize`` are pure functions of the capture that —
    depending on the capture's declared ``file_kind`` — aggregate per-search events
    into :class:`UsageAggregate` rows (never a per-search row, §18.1), land the
    audit ``Camera Count`` as an independent ``active_device_count`` claim, record
    redacted (`***`) cells as a distinct state, reconcile ``SharedNetworks.csv``
    into directional configured-access edges through P08.2's §29.3 reconciler, and
    land event-log lifecycle transitions. Every emitted row passes
    :func:`assert_no_per_row_output`, the §18.1 schema gate.
    """

    name = "audit_structural"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — one per audit CSV in the export bundle.

        Targets come from ``ctx.parameters['targets']``; each carries a ``url`` and
        a ``file_kind`` (one of the four audit source types, or ``shared_networks``)
        plus optional source-agency provenance (``requesting_agency``,
        ``export_id``) and the export's ``observed_at`` snapshot date (§23.7).
        """
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- capture (inherited: the framework stores bytes content-addressed) --

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured CSV, carrying the capture digest + target meta."""
        parsed = parse_csv(ctx.captures.get(capture.digest))
        target = self._target_for(ctx, capture)
        return {**parsed, "_capture_digest": capture.digest, "_target": dict(target)}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Aggregate the capture into structural records — no per-search row leaves.

        The per-search rows are read transiently and consumed here (§18.1): what
        leaves ``extract`` is only aggregates, the camera-count observation,
        redacted-cell records, sharing observations, or lifecycle transitions —
        keyed on the capture's declared ``file_kind``.
        """
        target = parsed.get("_target", {})
        file_kind = str(target.get("file_kind", ""))
        header = list(parsed.get("header", []))
        observed_at = _parse_date(target.get("observed_at"))
        requesting_agency = _opt_str(target.get("requesting_agency"))
        export_id = _opt_str(target.get("export_id"))

        if file_kind == "shared_networks":
            return [
                {
                    "record_kind": "_sharing_capture",
                    "parsed": {"header": header, "rows": list(parsed.get("rows", []))},
                    "observed_at": observed_at,
                }
            ]

        audit_source_type = assert_audit_source_type(file_kind)
        out: list[Mapping[str, Any]] = []

        if file_kind == "event_log":
            out.extend(
                {**row, "record_kind": "_lifecycle"}
                for row in lifecycle_transition_rows(
                    {"header": header, "rows": list(parsed.get("rows", []))},
                    audit_source_type=audit_source_type,
                )
            )

        # UsageAggregate binning (all four audit types carry search activity).
        columns = _aggregate_columns(header)
        if columns["searching_org"] is not None:
            events = [
                _normalize_event(r, columns=columns, export_id=export_id)
                for r in parsed.get("rows", [])
            ]
            for agg in aggregate_search_events(
                events,
                audit_source_type=audit_source_type,
                requesting_agency=requesting_agency,
                audit_export_id=export_id,
            ):
                out.append({"record_kind": "_aggregate", "aggregate": agg})
            # A redacted reason is a distinct recorded state (SIG-INGEST-046).
            reason_col = columns["reason"]
            if reason_col is not None:
                out.extend(
                    {**row, "record_kind": "_redaction"}
                    for row in redacted_cell_rows(
                        {"rows": list(parsed.get("rows", []))},
                        columns=[reason_col],
                        subject_id=f"{AGGREGATE_ID_PREFIX}:{export_id or file_kind}",
                        audit_source_type=audit_source_type,
                    )
                )

        # The audit `Camera Count` — an independent count claim (§23.7, §29.1).
        cam_col = camera_count_column(header)
        if cam_col is not None:
            org_col = columns["source_org"] or columns["searching_org"]
            for r in parsed.get("rows", []):
                if classify_cell(r.get(cam_col)) != CELL_PRESENT:
                    continue
                subject = _cell(r, org_col) or (export_id or file_kind)
                out.append(
                    {
                        "record_kind": "_camera_count",
                        "subject_id": f"{ORG_ID_PREFIX}:{subject}",
                        "value": _to_int(r.get(cam_col)),
                        "raw": r.get(cam_col),
                        "observed_at": observed_at,
                        "audit_source_type": audit_source_type,
                    }
                )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed claim rows beside preserved raw values (P2), confined to the allowlist.

        Aggregates → ``usage_aggregate`` rows; the camera count → an
        ``active_device_count`` claim; redacted cells → ``audit_cell_redacted``
        rows; lifecycle transitions → ``deployment_lifecycle_transition`` rows; the
        SharedNetworks observations → reconciled configured-access edges (via P08.2,
        with only the deterministic edges entering the stream). Every row is stamped
        and then run through :func:`assert_no_per_row_output` (§18.1).
        """
        out: list[dict[str, Any]] = []
        sharing_captures: list[Mapping[str, Any]] = []
        for raw in raw_claims:
            kind = raw.get("record_kind")
            if kind == "_aggregate":
                out.append(_stamp(raw["aggregate"].to_row()))
            elif kind == "_camera_count":
                value = raw.get("value")
                if value is not None:
                    out.append(
                        _stamp(
                            camera_count_claim(
                                str(raw["subject_id"]),
                                int(value),
                                raw.get("observed_at"),
                                audit_source_type=str(raw["audit_source_type"]),
                                raw_value=raw.get("raw"),
                            )
                        )
                    )
            elif kind == "_redaction":
                out.append(_stamp(_without_meta(raw)))
            elif kind == "_lifecycle":
                out.append(_stamp(_without_meta(raw)))
            elif kind == "_sharing_capture":
                sharing_captures.append(raw)

        for capture in sharing_captures:
            observed_at = capture.get("observed_at") or _today()
            reconciled = reconcile_audit_sharing(capture["parsed"], observed_at=observed_at)
            out.extend(_stamp(row) for row in _sharing_edge_rows(reconciled))

        # §18.1: the bright line is a schema property — prove no per-row leak.
        assert_no_per_row_output(out)
        return out

    def reconcile_sharing(
        self, parsed: Mapping[str, Any], *, observed_at: date
    ) -> SharingReconciliation:
        """Invoke P08.2's §29.3 sharing-edge reconciler over a SharedNetworks file.

        The full reconciliation — edges **and** the asymmetry contradictions /
        research tasks (SIG-RECON-035, owned by P08.2). The connector run streams
        only the deterministic edges.
        """
        return reconcile_audit_sharing(parsed, observed_at=observed_at)

    # -- link + load --
    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)

    # -- helpers --
    def _target_for(self, ctx: RunContext, capture: CaptureRef) -> Mapping[str, Any]:
        """Find the discover target whose url matches this capture's source uri."""
        for target in ctx.parameters.get("targets", []):
            if str(target.get("url")) == capture.source_uri:
                return target
        return {}


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any]) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20).

    Like ``records``, the export compartment is decided per source by the licence
    gate (SIG-LIC-009a), so the connector does not pin a compartment here; it
    records the source id and vocabulary version every row is interpretable against,
    and marks append-only provenance (P1–P3).
    """
    row.setdefault("source_id", AGENCY_AUDIT_SOURCE_ID)
    row.setdefault("vocab_version", vocab_version())
    row.setdefault("detector_version", _DETECTOR_VERSION)
    return row


def _without_meta(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the internal ``record_kind`` router tag, restoring the true row kind."""
    row = {k: v for k, v in raw.items() if k != "record_kind"}
    return {"record_kind": "claim", **row}


def _cell(row: Mapping[str, Any], column: str | None) -> str | None:
    """Read a present cell as a stripped string; redacted/empty → ``None``."""
    if column is None:
        return None
    value = row.get(column)
    if classify_cell(value) != CELL_PRESENT:
        return None
    return str(value).strip()


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_date(raw: object) -> date | None:
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if not raw:
        return None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _today() -> date:
    return datetime.now(UTC).date()


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim/entity row needs.

    ``claim_id`` and ``sys_period`` are the two non-deterministic columns the
    reproducibility fingerprint excludes (SIG-INGEST-003), so replay is
    byte-identical modulo exactly these. Only claim/aggregate/edge rows get an
    identity + transaction time.
    """
    stamped_kinds = {"claim", "usage_aggregate", "configured_access_edge"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        row = dict(claim)
        if row.get("record_kind") in stamped_kinds:
            row["claim_id"] = str(uuid4())
            row["sys_period"] = f"[{datetime.now(UTC).isoformat()},)"
        out.append(row)
    return out


__all__ = [
    "AGENCY_AUDIT_SOURCE_ID",
    "AGGREGATE_ID_PREFIX",
    "CELL_EMPTY",
    "CELL_PRESENT",
    "CELL_REDACTED",
    "AuditStructuralConnector",
    "PerRowLeak",
    "PredicateNotAllowed",
    "UnknownAuditSourceType",
    "UsageAggregate",
    "aggregate_search_events",
    "assert_audit_source_type",
    "assert_no_per_row_output",
    "assert_predicate_allowed",
    "audit_source_types",
    "camera_count_claim",
    "camera_count_column",
    "camera_count_observation",
    "canary_findings",
    "classify_cell",
    "deduplicate_events",
    "forbidden_output_columns",
    "forbidden_predicate_genres",
    "is_predicate_allowed",
    "is_redacted",
    "lifecycle_transition_rows",
    "load_claims_for_l1",
    "parse_csv",
    "period_month",
    "predicate_allowlist",
    "reason_category",
    "reconcile_audit_sharing",
    "reconcile_camera_counts",
    "redacted_cell_rows",
    "redaction_sentinel",
    "sharing_observations",
    "vocab",
    "vocab_version",
]
