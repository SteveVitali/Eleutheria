# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ingest-run report writer + one-shot backfill (P35.32 / J3 §3.3 item 1,
K10 §18 C-13/C-14 — SIG-TRANSP-036's engine field; the SIG stays routed to
its owner P36.46).

Three writers land rows in the append-only ``ingest_run_report`` table:

1. the scheduled-ingest writer — every ``scheduled-ingest`` invocation,
   after the run row lands in GCS, appends one ``link_basis='live'`` row for
   THAT execution (``db.run_report.append_report``). The run stays the
   shared unit of ingest; the report carries what THE EXECUTION saw.
2. the WORM backfill — ``sig-ops backfill-run-reports`` walks every GCS
   ``runs/<source>/<date>/<timestamp>.json`` object (the count is re-derived,
   never assumed) and reuses P31.2's matcher: rows that already carry a live
   completion URI are linked to that run (the +0 path), rows matched to a
   run by evidence get ``backfill:<basis>``, and rows that cannot get
   ``unmatched:<reason>`` with ``run_id NULL`` — the row exists per
   execution no matter the link (C-14).
3. the repo backfill — the pinned live-run records under
   ``docs/build/reports/live_runs/*.json`` (the P26.9–P27.9 leg records;
   ``link_basis='repo_record'``, ``clock_basis='git_only'``) — evidence that
   lives in git, not GCS.

Honesty rules the whole module shares (K10 C-13/C-14, J3 §3.3 item 1):

- every field is typed; an unevidenced value is NULL ("not_recorded"),
  never a fabricated 0;
- a shared pre-P31.2 run's values are never presented as the execution's
  own — the execution's own clock comes from the run row / git record;
- ``claims_added`` is the WORM row's emitted-claim count (duplicates
  included), surfaced as ``records_emitted`` and never passed off as the
  inserted count — matched rows derive insertion from the claim spine
  window like P31.2's matcher;
- robots outcomes fold to the closed ``obeyed``/``disallowed``/
  ``unavailable``/``disregarded`` vocabulary (internal connector verdicts
  map in, nothing else is invented);
- ``assertion_quarantine`` contributes COUNT-BY-REASON only — the private
  payload never enters the report;
- ``per_fetch`` stays unwritten — the column and its PKG-12
  ``{host,status,bytes}`` contract land in the sqitch change, but the
  telemetry writer is row 312's (P35.34) under J3's "when present" clause;
  NULL is the honest not_recorded value here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from db.run_report import append_report
from policy.transparency import (
    ROBOTS_OUTCOMES,
    interim_lane,
    scrub_source_url,
    upstream_host,
    valid_error_class,
)
from policy.transparency import error_class as s4_error_class

from .run_completion import (
    count_inserted_in_windows,
    load_live_uris,
    load_runs,
    parse_run_row,
    plan_backfill,
)

__all__ = [
    "REPO_RECORD_DIR",
    "RepoRecord",
    "ReportBackfillReport",
    "backfill_run_reports",
    "document_outcome_map",
    "error_class_for",
    "fetch_fields",
    "fields_for_repo_record",
    "fields_for_run_row",
    "fields_for_scheduled_row",
    "load_live_uri_runs",
    "load_quarantine_counts",
    "load_reported_uris",
    "read_repo_records",
    "read_worm_docs",
    "reconcile_run_reports",
    "refusal_class_map",
    "robots_outcome_map",
    "unmatched_link_basis",
    "write_report_for_row",
]

REPO_RECORD_DIR = Path("docs/build/reports/live_runs")

# The closed robots vocabulary is policy.transparency's S-13
# ``ROBOTS_OUTCOMES`` (obeyed|disallowed|unavailable|disregarded) — reused,
# not duplicated. Internal connector verdicts map in; an unmapped value is
# dropped (the report never invents a class outside the shape).
_ROBOTS_MAP = {
    "allowed": "obeyed",
    "obeyed": "obeyed",
    "disallowed": "disallowed",
    "unretrievable": "unavailable",
    "unavailable": "unavailable",
    "no_policy_4xx": "unavailable",
    "disregarded": "disregarded",
}

assert set(_ROBOTS_MAP.values()) <= set(ROBOTS_OUTCOMES), (
    "robots map must fold into the S-13 closed vocabulary"
)

# P31.2 matcher-reason prose → the unmatched link_basis reason slug. The
# mapping is keyed on stable substrings of the matcher's reason strings so
# the classes stay honest when the prose is punctuated differently.
_UNMATCHED_REASONS: tuple[tuple[str, str], ...] = (
    ("is not an ingest execution", "not_an_execution"),
    ("no connector is known", "no_connector"),
    ("overlaps another run row", "overlapping_window"),
    ("had started by the row's finish", "no_candidate_run"),
    ("no proof it touched a run", "failed_no_proof"),
    ("no claim handed to the sink", "no_claims_recorded"),
    ("and no claim in the window (ambiguous)", "ambiguous_candidates"),
    ("claims in the window (ambiguous)", "ambiguous_claims_in_window"),
)


def unmatched_link_basis(reason: str) -> str:
    """Map a P31.2 matcher reason to ``unmatched:<slug>`` (closed slugs)."""
    for needle, slug in _UNMATCHED_REASONS:
        if needle in reason:
            return f"unmatched:{slug}"
    return "unmatched:unresolved"


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _record_get(rec: Any, key: str, default: Any = None) -> Any:
    """Field access over a dict or a dataclass (RunRow / FetchRecord)."""
    if isinstance(rec, Mapping):
        return rec.get(key, default)
    return getattr(rec, key, default)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _safe_host(url: Any) -> str | None:
    """The publishable hostname of a URL via ``policy.transparency`` S-6
    ``upstream_host`` — credentials/port/path stripped; a bare IP host
    folds to the ``ip_host`` token (S-5: the address itself never lands)
    and an URL with no parseable host to ``unknown``. Never returns None
    for a non-empty URL so every recorded fetch keeps its row."""
    if not isinstance(url, str) or not url:
        return None
    host = upstream_host(url)
    if host:
        return host
    return "ip_host" if (urlsplit(str(url)).hostname or "") else "unknown"


def robots_outcome_map(fetch_record: Any) -> dict[str, dict[str, int]] | None:
    """``{host: {obeyed|disallowed|unavailable|disregarded: n}}`` or None.

    Handles the three recorded decision shapes: ``[{host: verdict}]``
    (connector FetchRecord), ``[{host, decision, ...}]`` (the egress-probe
    records) and ``[{host, outcome, ...}]`` (the civicclerk/escribe-era
    records). ``robots_disregarded`` rows ({url,host,verdict}) count under
    ``disregarded`` for the host — the marker means the fetch proceeded in
    spite of the verdict.
    """
    decisions = _as_list(_record_get(fetch_record, "robots_decisions"))
    disregarded = _as_list(_record_get(fetch_record, "robots_disregarded"))
    if not decisions and not disregarded:
        return None
    out: dict[str, dict[str, int]] = {}
    for item in decisions:
        host: object = None
        verdict: object = None
        if isinstance(item, Mapping):
            if "decision" in item or "outcome" in item:
                host = item.get("host")
                verdict = item.get("decision", item.get("outcome"))
            elif len(item) == 1:
                host, verdict = next(iter(item.items()))
        if not host:
            continue
        canon = _ROBOTS_MAP.get(str(verdict))
        if canon is None:
            continue
        out.setdefault(str(host), {}).setdefault(canon, 0)
        out[str(host)][canon] += 1
    for item in disregarded:
        if isinstance(item, Mapping):
            host = item.get("host") or _safe_host(item.get("url"))
            if host:
                out.setdefault(str(host), {}).setdefault("disregarded", 0)
                out[str(host)]["disregarded"] += 1
    return out or None


_REFUSAL_DETAIL_CLASSES: tuple[tuple[str, str], ...] = (
    ("disallows", "robots_disallow"),
    ("unretrievable", "robots_unavailable"),
    ("unavailable", "robots_unavailable"),
    ("content drift", "content_drift"),
    ("drift", "content_drift"),
    ("quota", "quota_reached"),
    ("throttl", "quota_reached"),
)

_POLITENESS_PREFIX_CLASSES = {
    "RobotsUnretrievable": "robots_unavailable",
    "RobotsDisallowed": "robots_disallow",
    "NoLiveTargets": "no_live_targets",
    "PolitenessRefusal": "politeness_refusal",
}


def _refusal_detail_class(detail: str) -> str:
    low = detail.lower()
    for needle, cls in _REFUSAL_DETAIL_CLASSES:
        if needle in low:
            return cls
    return "politeness_refusal"


def _politeness_class(value: str) -> str:
    prefix = value.split(":", 1)[0].strip()
    return _POLITENESS_PREFIX_CLASSES.get(prefix, "politeness_refusal")


def refusal_class_map(
    fetch_record: Any,
    *,
    refusal_reason: str = "",
    quarantine: Mapping[str, int] | None = None,
) -> dict[str, int] | None:
    """``{class: n}`` refusal classes, or None when nothing was refused.

    Classes come from: per-document ``refusals`` (classified by their detail
    prose), the run-level ``politeness_refusal`` / ``content_drift`` marker,
    the scheduled row's ``refusal_reason`` token (gate refusals), and the
    assertion_quarantine COUNT-BY-REASON merge — the private quarantine
    payload never enters this table (K10 §18).
    """
    classes: dict[str, int] = {}
    for item in _as_list(_record_get(fetch_record, "refusals")):
        detail = item.get("detail", "") if isinstance(item, Mapping) else str(item)
        cls = _refusal_detail_class(detail)
        classes[cls] = classes.get(cls, 0) + 1
    politeness = _record_get(fetch_record, "politeness_refusal")
    if isinstance(politeness, str) and politeness:
        cls = _politeness_class(politeness)
        classes[cls] = classes.get(cls, 0) + 1
    drift = _record_get(fetch_record, "content_drift")
    if isinstance(drift, str) and drift:
        classes["content_drift"] = classes.get("content_drift", 0) + 1
    reason = (refusal_reason or "").strip()
    if reason:
        classes[reason] = classes.get(reason, 0) + 1
    for reason_key, n in (quarantine or {}).items():
        classes[str(reason_key)] = classes.get(str(reason_key), 0) + int(n)
    return classes or None


def document_outcome_map(fetch_record: Any) -> dict[str, int] | None:
    """``{outcome: n}`` from the FetchRecord's per-document outcomes."""
    outcomes: dict[str, int] = {}
    for item in _as_list(_record_get(fetch_record, "document_outcomes")):
        if isinstance(item, Mapping):
            outcome = item.get("outcome")
            if outcome:
                outcomes[str(outcome)] = outcomes.get(str(outcome), 0) + 1
    for _item in _as_list(_record_get(fetch_record, "document_drift")):
        outcomes["drifted"] = outcomes.get("drifted", 0) + 1
    return outcomes or None


def error_class_for(
    outcome: str,
    detail: object,
    *,
    refusal_reason: str = "",
    fetch_record: Any = None,
) -> str | None:
    """The run-level S-4 class, or None (ok/partial runs and refusals whose
    class already lives in ``refusal_classes``)."""
    politeness = _record_get(fetch_record, "politeness_refusal") if fetch_record else None
    if isinstance(politeness, str) and politeness:
        cls = _politeness_class(politeness)
        if cls == "robots_unavailable":
            return "robots_unavailable"
        if cls == "robots_disallow":
            return "robots_disallow"
        return "politeness_refusal"
    drift = _record_get(fetch_record, "content_drift") if fetch_record else None
    if isinstance(drift, str) and drift:
        return "content_drift"
    if fetch_record is not None and _record_get(fetch_record, "quota_reached"):
        if outcome in ("quota_reached", "error", "failed"):
            return "quota_reached"
    if refusal_reason == "gate_refused" or outcome in ("gate_refused", "no_live_targets"):
        return None  # a gate outcome is not an upstream error; refusal_classes carries it
    if outcome in ("error", "failed"):
        return s4_error_class(str(detail) if detail else "unknown")
    return None


# ---------------------------------------------------------------------------
# P35.34 / PKG-12 — per-fetch telemetry (the per_fetch column's writer) and
# the SIG-CONF-009 upstream-count pair the GQ-19 check reads.
# ---------------------------------------------------------------------------


#: The stored per-fetch entry shape: ``host`` always (S-6: publishable),
#: ``url`` only where the S-6 lane rules allow it (else ``path_sha256`` so a
#: row still correlates without exposing path detail), then the recorded
#: transport facts. ``kind`` marks the egress class (``content`` /
#: ``robots`` — the robots.txt probe is real egress too); the transparency
#: export's allow-list drops ``url``/``path_sha256``/``fetched_at``/``kind``
#: fields it does not publish, so the stored row keeps the honest scrubbed
#: form and the public surface stays the PKG-12 shape.
def _lane_for_source(source_id: Any) -> tuple[str, bool]:
    """``(lane, gate_passed)`` for the S-6 URL scrub — the same interim
    rights-record basis the capture writer's lane derivation consumes
    (``connectors.sinks._registry_lane``). An unregistered or unreadable
    record resolves ``("unknown", False)`` — the scrub then records host +
    path-hash, never a full URL."""
    if not source_id:
        return "unknown", False
    try:
        from connectors.sinks import _registry_lane

        basis = _registry_lane(str(source_id))
    except Exception:  # noqa: BLE001 — no basis is a closed posture, never a guess
        basis = None
    if not basis:
        return "unknown", False
    decision = interim_lane(
        custody_posture=basis.get("custody_posture"),
        spdx=basis.get("spdx"),
        redistributable=basis.get("redistributable"),
        reviewed=basis.get("reviewed"),
        refused=basis.get("refused"),
    )
    return decision.lane, True


def scrub_per_fetch(source_id: Any, entries: Any) -> list[dict[str, Any]] | None:
    """FetchRecord ``per_fetch`` rows → the report's S-6-scrubbed shape.

    ``None`` in → ``None`` out (never recorded stays unwritten, NULL =
    not_recorded); a recorded empty list stays ``[]`` (recorded, zero
    egress). Each raw URL passes ``policy.transparency.scrub_source_url``:
    credential-stripped host always, the full scrubbed URL only where the
    lane + gate allow, else ``path_sha256``.
    """
    if entries is None:
        return None
    lane, gate = _lane_for_source(source_id)
    out: list[dict[str, Any]] = []
    for item in _as_list(entries):
        if not isinstance(item, Mapping):
            continue
        row: dict[str, Any] = {}
        url = item.get("url")
        scrubbed = scrub_source_url(str(url) if url else None, lane=lane, gate_passed=gate)
        if scrubbed is not None:
            if scrubbed.host:
                row["host"] = scrubbed.host
            if scrubbed.url:
                row["url"] = scrubbed.url
            elif scrubbed.path_sha256:
                row["path_sha256"] = scrubbed.path_sha256
        kind = item.get("kind")
        if kind:
            row["kind"] = str(kind)
        for key in ("status", "bytes", "duration_ms", "records_emitted"):
            value = item.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                row[key] = value
        fetched_at = item.get("fetched_at")
        if fetched_at:
            row["fetched_at"] = str(fetched_at)
        outcome = item.get("outcome")
        if outcome:
            row["outcome"] = str(outcome)
        err = item.get("error_class")
        if err:
            row["error_class"] = str(err) if valid_error_class(str(err)) else "unclassified_error"
        out.append(row)
    return out


#: The SIG-CONF-009 upstream-reconciliation object schema (the
#: ``upstream_reconciliation`` column's contract).
UPSTREAM_RECON_SCHEMA = "sig.upstream-reconciliation/1"

#: The closed explained-difference reason vocabulary (§56.7): the four named
#: classes plus the ``other:<free-text-class>`` escape — a recorded value,
#: never a guess; an unevidenced difference stays ``unexplained``.
RECON_REASONS: tuple[str, ...] = (
    "filtered",
    "withheld_rows",
    "pagination_cap",
    "upstream_misreport",
)

#: The pair classifications — ``in_range`` (≤1 %), ``explained`` (recorded
#: reason), ``unexplained`` (the GQ-19 fail class where it exceeds the
#: threshold), ``not_evaluable`` (a side was never recorded).
RECON_CLASSES: tuple[str, ...] = (
    "in_range",
    "explained",
    "unexplained",
    "not_evaluable",
)

#: The unexplained-difference threshold (§56.7: "above 1 %").
RECON_THRESHOLD_PCT = 1.0

#: The recorded honesty tokens — a side the upstream/connector never exposed
#: is recorded as the token, never a guessed number.
RECON_NOT_EXPOSED = "not_exposed"
RECON_NOT_RECORDED = "not_recorded"

#: Document-outcome fields that carry the upstream's OWN declared count at
#: fetch time (page totals / declared row counts — precedence order;
#: ``upstream_count`` is the canonical name the live runner stamps).
_UPSTREAM_COUNT_FIELDS: tuple[str, ...] = (
    "upstream_count",
    "total_items",
    "total_notice_count",
    "row_count",
    "entry_count",
)

#: Document-outcome fields that carry what the run HELD for that target
#: (precedence order — an explicit ``subjects_held``/``records_emitted``
#: beats the per-kind counters; ``items_count`` is TED's held side, never a
#: declared total).
_SUBJECTS_HELD_FIELDS: tuple[str, ...] = (
    "subjects_held",
    "records_emitted",
    "bills_indexed",
    "returned_count",
    "items_count",
)


def valid_recon_reason(value: Any) -> bool:
    """Is the value in the closed difference-reason vocabulary?"""
    text = str(value or "").strip()
    return text in RECON_REASONS or text.startswith("other:")


def _first_int(row: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[int | None, str | None]:
    """The first recorded non-negative int among ``fields`` + its name."""
    for name in fields:
        value = row.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            return value, name
    return None, None


def _difference_reason(row: Mapping[str, Any], fetch_record: Any) -> str | None:
    """The recorded explanation for a >1 % difference — only what the
    outcome row or the run record explicitly evidences. An unevidenced
    difference returns None and lands ``unexplained`` — never
    explained-away."""
    recorded = row.get("difference_reason") or row.get("explanation")
    if isinstance(recorded, str) and valid_recon_reason(recorded):
        return recorded.strip()
    if row.get("truncated"):
        return "pagination_cap"
    if row.get("filtered"):
        return "filtered"
    withheld = row.get("withheld_rows")
    if isinstance(withheld, int) and not isinstance(withheld, bool) and withheld > 0:
        return "withheld_rows"
    if row.get("timed_out"):
        return "other:timed_out"
    if _record_get(fetch_record, "quota_reached"):
        return "other:quota_reached"
    if _record_get(fetch_record, "budget_reached"):
        return "other:budget_reached"
    return None


def _recon_pair(
    *,
    target: str,
    upstream: int | str,
    count_basis: str,
    held: int | None,
    held_basis: str,
    row: Mapping[str, Any],
    fetch_record: Any,
) -> dict[str, Any]:
    """One comparison pair: the upstream's own count vs the subjects held —
    ``not_exposed``/``not_recorded`` tokens where a side was never recorded,
    ``difference_pct`` + the classification the >1 % check reads."""
    pair: dict[str, Any] = {
        "target": target,  # S-6-scrubbed upstream of this call: host (+ gated url/path hash)
        "upstream_count": upstream,
        "count_basis": count_basis,
        "subjects_held": held if held is not None else RECON_NOT_RECORDED,
        "subjects_basis": held_basis if held is not None else RECON_NOT_RECORDED,
        "difference_pct": None,
        "classification": "not_evaluable",
        "reason": None,
    }
    if not isinstance(upstream, int) or held is None:
        return pair
    diff = abs(upstream - held) / upstream * 100.0 if upstream else (0.0 if held == 0 else 100.0)
    pair["difference_pct"] = round(diff, 4)
    if diff <= RECON_THRESHOLD_PCT:
        pair["classification"] = "in_range"
        return pair
    reason = _difference_reason(row, fetch_record)
    if reason is None:
        pair["classification"] = "unexplained"
    else:
        pair["classification"] = "explained"
        pair["reason"] = reason
    return pair


def upstream_reconciliation(
    fetch_record: Any,
    *,
    records_emitted: int | None = None,
    source_id: Any = None,
) -> dict[str, Any] | None:
    """The ``sig.upstream-reconciliation/1`` object for one execution —
    ``None`` where the record evidences no run (NULL = not_recorded).

    Per-target pairs derive from the FetchRecord's ``document_outcomes``
    rows that carry an upstream-declared count (``total_items`` /
    ``total_notice_count`` / ``row_count`` / ``entry_count`` …); the
    run-level pair (``target: "run"``) compares the summed declared counts —
    or the honest ``not_exposed`` token — with the execution's recorded
    ``records_emitted``. The >1 % unexplained fail rule binds where the
    P34.44a/b check (GQ-19) reads this — this object is the recording
    surface, not the enforcement.

    Per-target identifiers pass the same S-6 scrub as ``per_fetch``: the
    pair records the host always, the full URL only where the lane rules
    allow, else ``path_sha256`` — the report row never holds raw path
    detail outside the gate.
    """
    fr = fetch_record or {}
    lane, gate = _lane_for_source(source_id)
    outcomes = _as_list(_record_get(fr, "document_outcomes"))
    held = records_emitted
    if held is None:
        value = _record_get(fr, "records_emitted")
        if not isinstance(value, int):
            value = _record_get(fr, "claim_count")
        if isinstance(value, int) and not isinstance(value, bool):
            held = int(value)
    evidences_run = bool(
        _as_list(_record_get(fr, "per_fetch"))
        or _as_list(_record_get(fr, "urls"))
        or outcomes
        or isinstance(_record_get(fr, "fetches"), int)
        or held is not None
    )
    if not evidences_run:
        return None

    pairs: list[dict[str, Any]] = []
    declared_total = 0
    declared_any = False
    for item in outcomes:
        if not isinstance(item, Mapping):
            continue
        upstream, basis = _first_int(item, _UPSTREAM_COUNT_FIELDS)
        if upstream is None:
            continue  # the outcome exposes no declared count — no pair for it
        held_v, held_basis = _first_int(item, _SUBJECTS_HELD_FIELDS)
        declared_any = True
        declared_total += upstream
        target_raw = item.get("url") or item.get("source_uri") or item.get("target")
        scrubbed = (
            scrub_source_url(str(target_raw), lane=lane, gate_passed=gate) if target_raw else None
        )
        pair = _recon_pair(
            target=(scrubbed.host if scrubbed and scrubbed.host else RECON_NOT_RECORDED),
            upstream=upstream,
            count_basis=f"document_outcomes.{basis}",
            held=held_v,
            held_basis=(f"document_outcomes.{held_basis}" if held_basis else RECON_NOT_RECORDED),
            row=item,
            fetch_record=fr,
        )
        if scrubbed is not None:
            if scrubbed.url:
                pair["url"] = scrubbed.url
            elif scrubbed.path_sha256:
                pair["path_sha256"] = scrubbed.path_sha256
        pairs.append(pair)

    pairs.append(
        _recon_pair(
            target="run",
            upstream=declared_total if declared_any else RECON_NOT_EXPOSED,
            count_basis=(
                "sum(document_outcomes upstream counts)" if declared_any else RECON_NOT_EXPOSED
            ),
            held=held,
            held_basis="records_emitted",
            row={},
            fetch_record=fr,
        )
    )
    return {"schema": UPSTREAM_RECON_SCHEMA, "pairs": pairs}


def fetch_fields(
    fetch_record: Any,
    *,
    source_id: Any = None,
    records_emitted: int | None = None,
) -> dict[str, Any]:
    """All fetch-evidence fields derived from a FetchRecord-shaped object
    (dict or dataclass). Every unevidenced value stays None."""
    fr = fetch_record or {}
    urls = _as_list(_record_get(fr, "urls"))
    explicit = _record_get(fr, "fetches")
    if isinstance(explicit, int) and not isinstance(explicit, bool):
        fetches: int | None = explicit
    elif (isinstance(fr, Mapping) and "urls" in fr) or urls:
        fetches = len(urls)
    else:
        fetches = None
    return {
        "fetches": fetches,
        "rate_limit_events": (
            len(_as_list(_record_get(fr, "rate_limit_events")))
            if _record_get(fr, "rate_limit_events") is not None
            else None
        ),
        "disappearances": (
            len(_as_list(_record_get(fr, "disappearances")))
            if _record_get(fr, "disappearances") is not None
            else None
        ),
        "robots_outcomes": robots_outcome_map(fr),
        "document_outcomes": document_outcome_map(fr),
        "quota_reached": (
            bool(_record_get(fr, "quota_reached"))
            if _record_get(fr, "quota_reached") is not None
            else None
        ),
        "budget_reached": (
            bool(_record_get(fr, "budget_reached"))
            if _record_get(fr, "budget_reached") is not None
            else None
        ),
        # P35.34 / PKG-12: the recorded per-egress rows, S-6-scrubbed at
        # write (host always; full URL only under the lane rules). Absent
        # from the record → NULL (not_recorded); a recorded [] stays [].
        "per_fetch": scrub_per_fetch(source_id, _record_get(fr, "per_fetch")),
        # SIG-CONF-009: the upstream's own count at fetch vs the subjects
        # held — the sig.upstream-reconciliation/1 object the GQ-19 check
        # reads; NULL where the record evidences no run.
        "upstream_reconciliation": upstream_reconciliation(
            fr, records_emitted=records_emitted, source_id=source_id
        ),
    }


def fields_for_scheduled_row(
    row: Any, *, quarantine: Mapping[str, int] | None = None
) -> dict[str, Any]:
    """The append_report kwargs for a live ``scheduled_ingest`` RunRow
    (the scheduled-ingest writer — link_basis 'live'; clock 'db' when the
    row links a run, else the run row's own clock)."""
    fr = _record_get(row, "fetch_record", {})
    run_id = _record_get(row, "ingest_run_id") or None
    outcome = str(_record_get(row, "outcome", ""))
    detail = _record_get(row, "detail")
    refusal_reason = str(_record_get(row, "refusal_reason") or "")
    source_id = _record_get(row, "source") or None
    emitted = (
        int(_record_get(row, "claims_added") or 0)
        if _record_get(row, "claims_added") is not None
        else None
    )
    fields = fetch_fields(fr, source_id=source_id, records_emitted=emitted)
    return {
        "run_id": run_id,
        "source_id": source_id,
        "link_basis": "live",
        "clock_basis": "db" if run_id else "run_row",
        "started_at": _parse_ts(_record_get(row, "started_at")),
        "records_emitted": emitted,
        "duration_seconds": _record_get(row, "duration_seconds"),
        "refusal_classes": refusal_class_map(
            fr, refusal_reason=refusal_reason, quarantine=quarantine
        ),
        "error_class": error_class_for(
            outcome, detail, refusal_reason=refusal_reason, fetch_record=fr
        ),
        "backfilled_from": None,
        **fields,
    }


def fields_for_run_row(
    doc: Any,
    *,
    link_basis: str,
    run_id: str | None = None,
    quarantine: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """The append_report kwargs for a WORM run-row JSON doc (the backfill).

    ``link_basis`` is 'live' (the row's URI is the live completion's URI),
    'backfill:claims-in-window' / 'backfill:sole-candidate' (matched), or
    'unmatched:<reason>'. The WORM row's own ``claims_added`` lands as
    ``records_emitted`` — the emitted count is never presented as the
    inserted count (C-13); the run's ``started_at`` is the execution's own
    clock, never a borrowed shared-run clock.
    """
    doc = doc if isinstance(doc, Mapping) else {}
    fr = doc.get("fetch_record") if isinstance(doc.get("fetch_record"), Mapping) else {}
    outcome = str(doc.get("outcome") or "")
    refusal_reason = str(doc.get("refusal_reason") or "")
    emitted = doc.get("claims_added")
    emitted_int = int(emitted) if isinstance(emitted, int) else None
    fields = fetch_fields(fr, source_id=doc.get("source"), records_emitted=emitted_int)
    return {
        "run_id": run_id,
        "source_id": doc.get("source") or None,
        "link_basis": link_basis,
        # Every backfill-minted row's clock is the WORM run row's own —
        # 'run_row' even when the link came live (the minted row was never
        # written by the live writer; the 'live' basis records the link
        # strength, the clock stays honest).
        "clock_basis": "run_row",
        "started_at": _parse_ts(doc.get("started_at")),
        "records_emitted": emitted_int,
        "duration_seconds": doc.get("duration_seconds"),
        "refusal_classes": refusal_class_map(
            fr,
            refusal_reason=refusal_reason,
            quarantine=quarantine,
        ),
        "error_class": error_class_for(
            outcome,
            doc.get("detail"),
            refusal_reason=refusal_reason,
            fetch_record=fr,
        ),
        **fields,
    }


def fields_for_repo_record(rec: Any) -> dict[str, Any]:
    """The append_report kwargs for a repo-pinned live-run record
    (link_basis 'repo_record', clock_basis 'git_only' — C-14). Handles the
    three pinned shapes: RunRow docs, FetchRecord dicts, and honest
    non-run artifacts (e.g. the sam.gov quota-probe response — its fields
    mostly stay not_recorded).
    """
    if not isinstance(rec, Mapping):
        rec = {}
    fr = rec.get("fetch_record") if isinstance(rec.get("fetch_record"), Mapping) else rec
    outcome = str(rec.get("outcome") or "")
    source = rec.get("source") or rec.get("source_id") or fr.get("source_id")
    error = error_class_for(outcome, rec.get("detail"), fetch_record=fr)
    if error is None:
        # Non-run artifacts: an upstream throttle/quota response records
        # 'quota_reached' — the message is evidence, not a guess.
        message = str(rec.get("message") or rec.get("description") or "")
        if "quota" in message.lower() or "throttl" in message.lower():
            error = "quota_reached"
    emitted = rec.get("claims_added")
    if emitted is None:
        emitted = fr.get("claim_count") if isinstance(fr, Mapping) else None
    emitted_int = int(emitted) if isinstance(emitted, int) else None
    fields = fetch_fields(fr, source_id=source, records_emitted=emitted_int)
    return {
        "run_id": None,
        "source_id": source,
        "link_basis": "repo_record",
        "clock_basis": "git_only",
        "started_at": _parse_ts(
            rec.get("started_at") or (fr.get("started_at") if isinstance(fr, Mapping) else None)
        ),
        "records_emitted": emitted_int,
        "duration_seconds": rec.get("duration_seconds")
        or (fr.get("duration_seconds") if isinstance(fr, Mapping) else None),
        "refusal_classes": refusal_class_map(fr),
        "error_class": error,
        **fields,
    }


@dataclass(frozen=True)
class RepoRecord:
    """One pinned live-run record under docs/build/reports/live_runs."""

    path: str  # repo-relative path; backfilled_from is 'repo:' + path
    doc: dict


def read_repo_records(directory: Path | str = REPO_RECORD_DIR) -> list[RepoRecord]:
    """Every ``*.json`` record in the live_runs directory, sorted by name
    (the count is re-derived — never the audit's "90")."""
    root = Path(directory)
    out: list[RepoRecord] = []
    for path in sorted(root.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError):
            doc = {}
        out.append(RepoRecord(path=str(path.as_posix()), doc=doc if isinstance(doc, dict) else {}))
    return out


# ---- the live writer ------------------------------------------------------


def write_report_for_row(conn: Any, row: Any) -> str | None:
    """Append the report row for a just-finished scheduled execution.

    INSERT-only, ON CONFLICT +0 under the live unique key. Returns the new
    report_id, or None when the row was already present.
    """
    run_id = _record_get(row, "ingest_run_id") or None
    quarantine = load_quarantine_counts(conn).get(str(run_id)) if run_id else None
    fields = fields_for_scheduled_row(row, quarantine=quarantine)
    return append_report(conn, **fields)


# ---- the backfill ---------------------------------------------------------


def load_reported_uris(conn: Any) -> set[str]:
    """backfilled_from URIs already reported (+0 guard)."""
    return {
        r[0]
        for r in conn.execute(
            "SELECT backfilled_from FROM ingest_run_report WHERE backfilled_from IS NOT NULL"
        ).fetchall()
    }


def load_live_uri_runs(conn: Any) -> dict[str, str]:
    """WORM URI → run_id for live completions (link 'live' rows)."""
    return {
        uri: str(run_id)
        for uri, run_id in conn.execute(
            "SELECT run_record_uri, run_id FROM ingest_run_completion"
            " WHERE backfilled_from IS NULL AND run_record_uri IS NOT NULL"
        ).fetchall()
    }


def load_quarantine_counts(conn: Any) -> dict[str, dict[str, int]]:
    """``{run_id: {reason: n}}`` — COUNT-BY-REASON ONLY. The private
    payload column is never selected; when the caller lacks SELECT on
    ``assertion_quarantine`` (e.g. sig_ingest) the map is empty and the
    refusal classes simply carry no quarantine classes (honest)."""
    try:
        allowed = conn.execute(
            "SELECT has_table_privilege(current_user, 'assertion_quarantine', 'SELECT')"
        ).fetchone()[0]
    except Exception:
        allowed = False
    if not allowed:
        return {}
    out: dict[str, dict[str, int]] = {}
    for run_id, reason, n in conn.execute(
        "SELECT run_id::text, reason, count(*) FROM assertion_quarantine GROUP BY run_id, reason"
    ).fetchall():
        out.setdefault(str(run_id), {})[str(reason)] = int(n)
    return out


def read_worm_docs(bucket: Any, prefix: str) -> list[tuple[str, dict[str, Any]]]:
    """Every ``<prefix>/**.json`` object as ``(uri, doc)`` — the raw docs the
    report fields derive from (``read_worm_rows`` keeps only the reduced
    match shape)."""
    out: list[tuple[str, dict[str, Any]]] = []
    for name in sorted(bucket.list_objects(prefix.rstrip("/") + "/")):
        if not name.endswith(".json"):
            continue
        doc = json.loads(bucket.get_object(name).decode("utf-8"))
        out.append((f"gs://{bucket.bucket}/{name}", doc))
    return out


@dataclass
class ReportBackfillReport:
    """The read-back both ``--dry-run`` and ``--apply`` return (JSON-safe)."""

    run_rows: int = 0
    repo_records: int = 0
    appended: int = 0
    already_present: int = 0
    covered_live: int = 0
    matched: int = 0
    unmatched: int = 0
    link_basis_counts: dict[str, int] = field(default_factory=dict)
    unmatched_rows: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict:
        return {
            "run_rows": self.run_rows,
            "repo_records": self.repo_records,
            "appended": self.appended,
            "already_present": self.already_present,
            "covered_live": self.covered_live,
            "matched": self.matched,
            "unmatched": self.unmatched,
            "link_basis_counts": dict(sorted(self.link_basis_counts.items())),
            "unmatched_rows": self.unmatched_rows,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


def backfill_run_reports(
    conn: Any,
    worm_docs: list[tuple[str, dict[str, Any]]],
    repo_records: list[RepoRecord] | None = None,
    *,
    dry_run: bool = False,
    connector_for_source: Mapping[str, str] | None = None,
) -> ReportBackfillReport:
    """Append one report row per WORM run row + per repo-pinned record.

    INSERT-only; ``ON CONFLICT`` under the ``backfilled_from`` unique key
    makes every re-run a +0 no-op. The P31.2 matcher (``plan_backfill``)
    decides each row's link: rows whose URI is a live completion's URI link
    ``live`` (only minted when the live writer left no row — else the
    execution stays covered once, never double-counted), rows matched by
    evidence get ``backfill:<basis>``, and unmatched executions keep
    ``run_id NULL`` with the P31.2 reason class verbatim
    (``unmatched:<reason>``).
    """
    report = ReportBackfillReport(
        run_rows=len(worm_docs),
        repo_records=len(repo_records or []),
        dry_run=dry_run,
    )
    rows = [
        parse_run_row(uri, doc, connector_for_source=connector_for_source or {})
        for uri, doc in worm_docs
    ]
    docs_by_uri = dict(worm_docs)
    runs = load_runs(conn)
    inserted = count_inserted_in_windows(conn, rows, runs)
    live_uris = load_live_uris(conn)
    live_uri_runs = load_live_uri_runs(conn)
    reported = load_reported_uris(conn)
    live_reported_runs = {
        str(r[0])
        for r in conn.execute(
            "SELECT run_id FROM ingest_run_report"
            " WHERE backfilled_from IS NULL AND run_id IS NOT NULL"
        ).fetchall()
    }
    quarantine = load_quarantine_counts(conn)
    plan = plan_backfill(rows, runs, inserted, live_uris=live_uris)

    def _bump(basis: str) -> None:
        report.link_basis_counts[basis] = report.link_basis_counts.get(basis, 0) + 1

    def _insert(uri: str, fields: dict[str, Any]) -> None:
        fields["backfilled_from"] = uri
        _bump(str(fields["link_basis"]))
        if uri in reported:
            report.already_present += 1
            return
        if dry_run:
            return
        try:
            report_id = append_report(conn, **fields)
        except Exception as exc:  # noqa: BLE001 — keep enumerating
            report.errors.append(f"{uri}: {type(exc).__name__}: {exc}")
            return
        if report_id is None:
            report.already_present += 1
        else:
            report.appended += 1

    # Executions whose run row already backs a live completion: link 'live'
    # (the strongest link — the execution's own recorded URI). Minted only
    # when the live writer left no row for the run — one report row per
    # execution, never a second count.
    for uri in plan.skipped_live:
        run_id = live_uri_runs.get(uri)
        if run_id is not None and run_id in live_reported_runs:
            report.covered_live += 1
            _bump("live")
            continue
        fields = fields_for_run_row(
            docs_by_uri[uri],
            link_basis="live",
            run_id=run_id,
            quarantine=quarantine.get(run_id) if run_id else None,
        )
        _insert(uri, fields)
        report.matched += 1

    for m in plan.matched:
        q = quarantine.get(str(m.run_id))
        fields = fields_for_run_row(
            docs_by_uri[m.row.uri],
            link_basis=f"backfill:{m.basis}",
            run_id=m.run_id,
            quarantine=q,
        )
        _insert(m.row.uri, fields)
        report.matched += 1

    for u in plan.unmatched:
        link_basis = unmatched_link_basis(u.reason)
        fields = fields_for_run_row(docs_by_uri[u.uri], link_basis=link_basis, run_id=None)
        _insert(u.uri, fields)
        report.unmatched += 1
        report.unmatched_rows.append(
            {
                "uri": u.uri,
                "source": u.source,
                "outcome": u.outcome,
                "reason": u.reason,
                "link_basis": link_basis,
            }
        )

    for rec in repo_records or []:
        uri = f"repo:{rec.path}"
        fields = fields_for_repo_record(rec.doc)
        _insert(uri, fields)
    return report


# ---- reconcile / read-back ------------------------------------------------


def reconcile_run_reports(conn: Any) -> dict:
    """Union the execution history (K10 §18): every execution accounted
    once, counts per link_basis, no double counting.

    Double-count means: the same WORM URI reported twice (impossible under
    the unique key — asserted anyway) or a run row reported both live and
    by backfill (a backfilled row whose URI is a live completion's URI).
    Shared runs (a pre-P31.2 run linked by >1 report row) are reported with
    the count of rows that borrowed a clock they should not have — under
    C-13 that must be zero (each carries its own run-row clock or NULL).
    """
    total = conn.execute("SELECT count(*) FROM ingest_run_report").fetchone()[0]
    by_basis: dict[str, int] = {}
    for basis, n in conn.execute(
        "SELECT link_basis, count(*) FROM ingest_run_report GROUP BY link_basis"
    ).fetchall():
        by_basis[str(basis)] = int(n)
    by_clock: dict[str, int] = {}
    for basis, n in conn.execute(
        "SELECT clock_basis, count(*) FROM ingest_run_report GROUP BY clock_basis"
    ).fetchall():
        by_clock[str(basis)] = int(n)
    dup_backfill = conn.execute(
        "SELECT count(*) FROM (SELECT backfilled_from FROM ingest_run_report"
        " WHERE backfilled_from IS NOT NULL GROUP BY backfilled_from"
        " HAVING count(*) > 1) t"
    ).fetchone()[0]
    # An execution is double-counted when its run carries BOTH a live-written
    # row (backfilled_from NULL) and a backfill-minted row — the live writer
    # already covered it, the second row counts it again. Shared-run rows
    # (many backfilled executions under one run_id) are NOT double counts:
    # each is a distinct execution folded through the shared run.
    double_live_backfill = conn.execute(
        "SELECT count(*) FROM ingest_run_report r"
        " WHERE r.backfilled_from IS NOT NULL AND EXISTS ("
        "   SELECT 1 FROM ingest_run_report l"
        "   WHERE l.backfilled_from IS NULL AND l.run_id = r.run_id)"
    ).fetchone()[0]
    shared = conn.execute(
        "SELECT count(*) FROM (SELECT run_id FROM ingest_run_report"
        " WHERE run_id IS NOT NULL GROUP BY run_id HAVING count(*) > 1) t"
    ).fetchone()[0]
    shared_missing_start = conn.execute(
        "SELECT count(*) FROM ingest_run_report r WHERE r.started_at IS NULL"
        " AND r.run_id IN (SELECT run_id FROM ingest_run_report"
        "  WHERE run_id IS NOT NULL GROUP BY run_id HAVING count(*) > 1)"
    ).fetchone()[0]
    return {
        "total": int(total),
        "by_link_basis": dict(sorted(by_basis.items())),
        "by_clock_basis": dict(sorted(by_clock.items())),
        "double_counted": int(dup_backfill) + int(double_live_backfill),
        "shared_run_rows": {
            "runs": int(shared),
            "missing_own_start": int(shared_missing_start),
        },
    }
