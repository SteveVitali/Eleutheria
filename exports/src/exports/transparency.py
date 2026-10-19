# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.33 — the transparency run/capture/issue emission (J3 §3.1–3.2,
§4.5–4.6, §7.3; K9 §10 C-4…C-7; K10 §18 C-13/C-14; D-J3-2 [B-19] = yes).

The spine export reads ``v_transparency_run`` / ``v_transparency_capture``
(the ``sig_export``-only explicit-column views, J3 §3.3 items 1–2) inside the
same repeatable-read snapshot as every other surface; every emitted field then
passes through :mod:`policy.transparency` (the one scrub vocabulary — S-1…S-14)
and the release artifacts land under ``transparency/``:

* ``transparency/runs.jsonl`` — ``sig.run-record/1``: one scrubbed row per
  **execution** (one ``ingest_run_report`` row). Execution-keyed per C-13:
  ``started_at`` is the report row's own clock (else ``finished_at −
  duration``); code identity carries ``ingest_run.code_commit`` only where
  the execution owns its run — a shared run renders
  ``"not_recorded (shared run)"``, never the shared value.
* ``transparency/captures.jsonl`` — ``sig.capture-record/1``: one row per
  capture mark — actual/synthetic classification, the served storage tier
  (the recorded tier tightened by the lane derivation, never assumed
  ``public``), bytes, digest, retained status, and ``changed_vs_prior``
  per target. A sealed-tier capture stays sealed: its URL/URI never
  reaches the file.
* ``transparency/issues.jsonl`` — ``sig.source-issue/1``: the auto-detected
  issue classes (J3 §7.3, closed vocabulary) with
  ``opened_at``/``last_seen_at``/``closed_at`` + counts. Instances are
  keyed ``(source_id, class, opened_at)`` — a re-export over the same
  spine emits byte-identical rows (the append-only history only grows).
* ``transparency/freshness.jsonl`` — ``sig.source-freshness/1``: the
  cadence **rule** (K9 C-4 — never a "next run" timestamp on release
  artifacts), the freshness-state inputs the P35.41 verdict consumes
  (``one_time_load``, ``run_record_missing``), the two change columns
  (C-6), and the volatility basis + ``staleness_not_evaluable`` counts
  (C-5 — never "unknown", never a fake "0 stale").

The robots-disregard disclosure is host + count + the GL-GATE-08 decision
reference — never per-request detail (D-J3-2 [B-19]).
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from policy.freshness import (
    cadence_rule,
    freshness_state,
    valid_issue_class,
    valid_quarantine_reason,
)
from policy.transparency import (
    TIER_SEALED,
    TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
    TRANSPARENCY_RUN_VIEW_COLUMNS,
    error_counts,
    explicit_columns,
    interim_lane,
    iso_utc,
    opaque_id,
    robots_disclosure_rows,
    scrub_source_url,
    served_storage_tier,
    upstream_host,
    valid_error_class,
)

#: Schema ids (J3 §3.2).
RUN_RECORD_SCHEMA = "sig.run-record/1"
CAPTURE_RECORD_SCHEMA = "sig.capture-record/1"
ISSUE_RECORD_SCHEMA = "sig.source-issue/1"
FRESHNESS_RECORD_SCHEMA = "sig.source-freshness/1"

#: Release artifact paths under ``transparency/`` (J3 §3.1–3.2).
TRANSPARENCY_RUNS_PATH = "transparency/runs.jsonl"
TRANSPARENCY_CAPTURES_PATH = "transparency/captures.jsonl"
TRANSPARENCY_ISSUES_PATH = "transparency/issues.jsonl"
TRANSPARENCY_FRESHNESS_PATH = "transparency/freshness.jsonl"

# ---------------------------------------------------------------------------
# The spine reads — EXPORT_QUERIES-style (guard table, explicit SELECT). Each
# SELECT lists exactly the columns the scrub allow-list names; a missing view
# or table degrades to honest absence ([]) via the to_regclass guard.
# ---------------------------------------------------------------------------

#: Per-source rights fields the interim lane reads (row 313's
#: ``[redistribution]`` fields are not landed yet; the interim basis is
#: recorded per row, never guessed).
SOURCE_RIGHTS_COLUMNS: tuple[str, ...] = (
    "source_id",
    "custody_posture",
    "spdx_expression",
    "redistributable",
    "reviewed",
    "ingestion_permitted",
)

TRANSPARENCY_QUERIES: dict[str, tuple[str, str]] = {
    "transparency_runs": (
        "v_transparency_run",
        "SELECT "
        + ", ".join(TRANSPARENCY_RUN_VIEW_COLUMNS)
        + " FROM v_transparency_run ORDER BY report_id",
    ),
    "transparency_captures": (
        "v_transparency_capture",
        "SELECT "
        + ", ".join(TRANSPARENCY_CAPTURE_VIEW_COLUMNS)
        + " FROM v_transparency_capture ORDER BY run_id, target_key, state",
    ),
    "transparency_source_rights": (
        "source_registry",
        "SELECT sr.source_id, sr.custody_posture, rr.spdx_expression, "
        "rr.redistributable, (rr.reviewed_at IS NOT NULL) AS reviewed, "
        "sr.ingestion_permitted "
        "FROM source_registry sr JOIN rights_record rr USING (rights_id) "
        "ORDER BY sr.source_id",
    ),
    "transparency_predicates": (
        "vocab_predicate",
        "SELECT predicate_id, volatility_class, half_life_days "
        "FROM vocab_predicate ORDER BY predicate_id",
    ),
}

#: The emitted ``sig.*`` record field allow-lists — ``explicit_columns``
#: copies exactly these keys and raises on a never-exported field name, so a
#: builder refactor can never slip ``detail``/``parameters``/a WORM locator
#: through (S-12's closure applied at the artifact boundary too).
RUN_RECORD_FIELDS: tuple[str, ...] = (
    "schema",
    "execution_id",
    "run_id",
    "source_id",
    "link_basis",
    "clock_basis",
    "shared_run",
    "started_at",
    "started_basis",
    "finished_at",
    "duration_seconds",
    "outcome",
    "claims_considered",
    "claims_inserted",
    "claims_duplicate",
    "fetches",
    "records_emitted",
    "rejected",
    "error_class",
    "error_classes",
    "robots",
    "rate_limit_events",
    "disappearances",
    "document_outcomes",
    "quota_reached",
    "budget_reached",
    "per_fetch",
    "code_commit",
    "connector_name",
    "connector_version",
    "recorded_at",
)

CAPTURE_RECORD_FIELDS: tuple[str, ...] = (
    "schema",
    "run_id",
    "source_id",
    "target",
    "state",
    "records",
    "digest",
    "bytes",
    "media_type",
    "retrieved_at",
    "mark_recorded_at",
    "classification",
    "storage_tier",
    "tier_basis",
    "lane",
    "lane_basis",
    "bytes_retained",
    "redaction_applied",
    "redacted_derivative",
    "http_status",
    "changed_vs_prior",
    "shared_run",
)

ISSUE_RECORD_FIELDS: tuple[str, ...] = (
    "schema",
    "issue_id",
    "source_id",
    "issue_class",
    "opened_at",
    "last_seen_at",
    "closed_at",
    "count",
    "basis",
)

FRESHNESS_RECORD_FIELDS: tuple[str, ...] = (
    "schema",
    "source_id",
    "cadence_rule",
    "cadence_basis",
    "cadence_state",
    "scheduled",
    "one_time_load",
    "freshness_state",
    "run_record_missing",
    "evaluated_at",
    "last_upstream_change",
    "last_sig_records_change",
    "volatility",
    "staleness",
)

#: ``per_fetch`` entries pass only these keys (PKG-12's recorded shape);
#: anything else recorded is dropped fail-closed rather than emitted raw.
_PER_FETCH_FIELDS = (
    "host",
    "status",
    "bytes",
    "duration_ms",
    "records_emitted",
    "error_class",
    "outcome",
)

#: The C-13 honest-absence tokens.
_NOT_RECORDED = "not_recorded"
_NOT_RECORDED_SHARED = "not_recorded (shared run)"
_NOT_RECORDED_NO_RUN = "not_recorded (no linked run)"

#: The refusal classes ``refusal_class_map`` (ops.run_report) records —
#: closed, so the ``rejected`` map can fail closed on a key it cannot
#: name. Quarantine reasons ride ``valid_quarantine_reason`` separately.
_REJECTION_CLASSES: frozenset[str] = frozenset(
    {
        "robots_disallow",
        "robots_unavailable",
        "politeness_refusal",
        "content_drift",
        "quota_reached",
        "gate_refused",
        "no_live_targets",
        "rate_limited",
        "budget_reached",
    }
)


def _rejection_class(reason: str) -> bool:
    return reason in _REJECTION_CLASSES


_CADENCE_PATH = Path(__file__).resolve().parents[3] / "ops" / "cadence.toml"


def _rows(raw: Sequence[Any], columns: Sequence[str]) -> list[dict[str, Any]]:
    return [dict(zip(columns, r, strict=False)) for r in raw]


def _claim_get(claim: Any, key: str) -> Any:
    """Read a claim field off either a Mapping row or the ShapingClaim
    dataclass the export pipeline parses."""
    if isinstance(claim, Mapping):
        return claim.get(key)
    return getattr(claim, key, None)


def _iso(value: Any) -> str | None:
    return iso_utc(value) if isinstance(value, (datetime, str)) else None


def _dt(value: Any) -> datetime | None:
    """A view datetime (psycopg ``datetime`` or an ISO string) → datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return None


def _robots_host(host: str) -> str:
    """The publishable form of a recorded robots host — the S-6 host
    normalisation; an unrepresentable host (an IP literal) degrades to an
    opaque id rather than leaking (S-5)."""
    cleaned = upstream_host(f"https://{host}")
    return cleaned or opaque_id(host, kind="internal")


def load_cadence_sources(path: str | Path | None = None) -> dict[str, dict[str, str]] | None:
    """The declared cadence map the cadence-rule + scheduled flags read —
    ``ops/cadence.toml`` ``[[sources]]`` rows plus ``[[batches]]`` members
    resolved to their batch cadence (G1 NEW-10: the image bakes the file).

    Returns ``None`` when the doc cannot be read — the emitted rows then
    carry ``cadence_basis: "not_recorded"`` rather than fabricating
    schedules. ``state != "enabled"`` rows keep their declared cadence but
    report ``scheduled: false`` with the paused state recorded — never
    silently dropped.
    """
    p = Path(path) if path is not None else _CADENCE_PATH
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    out: dict[str, dict[str, str]] = {}
    for s in doc.get("sources", []):
        sid = str(s.get("id", "")).strip()
        if not sid:
            continue
        out[sid] = {
            "cron": str(s.get("cron", "")),
            "cadence": str(s.get("cadence", "")),
            "state": str(s.get("state", "enabled")).lower(),
        }
    for b in doc.get("batches", []):
        for member in b.get("members", []):
            sid = str(member).strip()
            if not sid or sid in out:
                continue
            out[sid] = {
                "cron": str(b.get("cron", "")),
                "cadence": str(b.get("cadence", "")),
                "state": str(b.get("state", "enabled")).lower(),
            }
    return out


# ---------------------------------------------------------------------------
# sig.run-record/1 — one scrubbed row per execution (K10 C-13/C-14)
# ---------------------------------------------------------------------------


def _run_owned(value: Any, row: Mapping[str, Any]) -> Any:
    """A run-owned value or the C-13 honest-absence token — the view already
    NULLs the field on shared runs; here we only label *why* it is absent
    (never a shared value, never a fabricated one)."""
    if value is not None:
        return value
    if row.get("shared_run"):
        return _NOT_RECORDED_SHARED
    if row.get("run_id") is None:
        return _NOT_RECORDED_NO_RUN
    return _NOT_RECORDED


def _count_field(value: Any, row: Mapping[str, Any]) -> Any:
    """A run-level count field — ``not_recorded`` typed on shared runs and
    on backfilled rows whose completion predates the field (the contract's
    'not_recorded on backfilled rows that predate the fields')."""
    if value is not None:
        return int(value)
    if row.get("shared_run"):
        return _NOT_RECORDED_SHARED
    return _NOT_RECORDED


def run_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Scrub one ``v_transparency_run`` row into ``sig.run-record/1``."""
    started = _dt(row.get("started_at"))
    finished = _dt(row.get("finished_at"))
    duration = row.get("duration_seconds")
    started_basis = "report"
    if started is None and finished is not None and isinstance(duration, (int, float)):
        # C-13's fallback clock: finished_at − duration (the completion's own
        # finish is only present on unshared rows — never a borrowed clock).
        started = finished - timedelta(seconds=float(duration))
        started_basis = "derived (finished_at − duration)"
    elif started is None:
        started_basis = _NOT_RECORDED

    error = row.get("error_class")
    outcome = row.get("completion_status")
    if outcome is None:
        if error:
            outcome = "failed"
        elif row.get("quota_reached"):
            outcome = "quota_reached"
        elif row.get("shared_run"):
            outcome = _NOT_RECORDED_SHARED
        else:
            outcome = "not_recorded (no completion recorded)"

    # Rejected counts by reason class — off-vocabulary keys fold into the
    # unclassifiable bucket, never emitted raw and never fabricated.
    rejected: dict[str, int] = {}
    unclassifiable = 0
    for reason, count in dict(row.get("refusal_classes") or {}).items():
        if _rejection_class(str(reason)) or valid_quarantine_reason(str(reason)):
            rejected[str(reason)] = rejected.get(str(reason), 0) + int(count)
        else:
            unclassifiable += int(count)
    if unclassifiable:
        rejected["other_unclassifiable"] = unclassifiable

    # Robots per-host outcome counts → the host+count disclosure shape;
    # 'disregarded' rows carry the GL-GATE-08 decision reference (B-19) and
    # never per-request detail.
    robots_rows = [
        {"host": _robots_host(str(host)), "outcome": str(outcome_k), "count": int(count)}
        for host, outcomes in dict(row.get("robots_outcomes") or {}).items()
        for outcome_k, count in dict(outcomes or {}).items()
    ]
    robots = robots_disclosure_rows(robots_rows)

    per_fetch: list[dict[str, Any]] | None = None
    if isinstance(row.get("per_fetch"), list):
        per_fetch = []
        for entry in row["per_fetch"]:
            if not isinstance(entry, Mapping):
                continue
            clean = explicit_columns(dict(entry), _PER_FETCH_FIELDS)
            if clean.get("host") is not None:
                clean["host"] = _robots_host(str(clean["host"]))
            if clean.get("error_class") is not None and not valid_error_class(
                str(clean["error_class"])
            ):
                clean["error_class"] = "unclassified_error"
            per_fetch.append({k: v for k, v in clean.items() if v is not None})

    record = {
        "schema": RUN_RECORD_SCHEMA,
        "execution_id": str(row["report_id"]),
        "run_id": str(row["run_id"]) if row.get("run_id") else None,
        "source_id": row.get("source_id"),
        "link_basis": row.get("link_basis"),
        "clock_basis": row.get("clock_basis"),
        "shared_run": bool(row.get("shared_run")),
        "started_at": iso_utc(started) if started else None,
        "started_basis": started_basis,
        "finished_at": iso_utc(finished) if finished else None,
        "duration_seconds": duration,
        "outcome": outcome,
        "claims_considered": _count_field(row.get("claims_considered"), row),
        "claims_inserted": _count_field(row.get("claims_inserted"), row),
        "claims_duplicate": _count_field(row.get("claims_duplicate"), row),
        "fetches": row.get("fetches"),
        "records_emitted": row.get("records_emitted"),
        "rejected": rejected,
        "error_class": error
        if error is None or valid_error_class(str(error))
        else "unclassified_error",
        "error_classes": error_counts([error] if error else []),
        "robots": robots,
        "rate_limit_events": row.get("rate_limit_events"),
        "disappearances": row.get("disappearances"),
        "document_outcomes": dict(row.get("document_outcomes") or {}) or None,
        "quota_reached": row.get("quota_reached"),
        "budget_reached": row.get("budget_reached"),
        "per_fetch": per_fetch,
        "code_commit": _run_owned(row.get("code_commit"), row),
        "connector_name": _run_owned(row.get("connector_name"), row),
        "connector_version": _run_owned(row.get("connector_version"), row),
        "recorded_at": _iso(row.get("recorded_at")),
    }
    return explicit_columns(record, RUN_RECORD_FIELDS)


# ---------------------------------------------------------------------------
# sig.capture-record/1 — classification + tier, sealed stays sealed
# ---------------------------------------------------------------------------


def _lane_map(source_rights: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """source_id → the interim lane decision (basis recorded per row)."""
    out: dict[str, Any] = {}
    for r in source_rights:
        out[str(r["source_id"])] = interim_lane(
            custody_posture=r.get("custody_posture"),
            spdx=r.get("spdx_expression"),
            redistributable=r.get("redistributable"),
            reviewed=r.get("reviewed"),
        )
    return out


def capture_record(row: Mapping[str, Any], *, lane: Any = None) -> dict[str, Any]:
    """Scrub one ``v_transparency_capture`` row into ``sig.capture-record/1``.

    The tier is ``served_storage_tier`` — the recorded tier tightened by the
    lane derivation where the recorded row predates the writer's derivation
    (never a silent ``public`` upgrade); a mark with no joined capture row
    derives the lane floor and labels the basis. A sealed-tier capture emits
    no URL/URI at all — even a path-hash would bind it to the host.
    """
    lane_name = getattr(lane, "lane", "unknown")
    lane_basis = getattr(lane, "basis", "not_recorded")

    classification = str(row.get("capture_classification") or "legacy")
    derivation = served_storage_tier(row.get("storage_tier"), lane=lane_name)
    if row.get("storage_tier") is None:
        # No capture row recorded a tier — the lane floor stands, labelled.
        tier_basis = "derived (no capture row — lane floor)"
    else:
        tier_basis = derivation.basis
    tier = derivation.tier

    if tier == TIER_SEALED:
        target = "sealed"
    else:
        scrubbed = scrub_source_url(
            str(row.get("source_uri") or row.get("target_key") or "") or None,
            lane=lane_name,
            gate_passed=lane is not None,
        )
        if scrubbed is None:
            target = _NOT_RECORDED
        elif scrubbed.url:
            target = scrubbed.url
        else:
            target = f"{scrubbed.host}#path_sha256:{scrubbed.path_sha256}"

    record = {
        "schema": CAPTURE_RECORD_SCHEMA,
        "run_id": str(row["run_id"]) if row.get("run_id") else None,
        "source_id": row.get("source_id"),
        "target": target,
        "state": row.get("state"),
        "records": row.get("records"),
        "digest": row.get("mark_digest"),
        "bytes": row.get("byte_size"),
        "media_type": row.get("media_type"),
        "retrieved_at": _iso(row.get("retrieved_at")),
        "mark_recorded_at": _iso(row.get("mark_recorded_at")),
        "classification": classification,
        "storage_tier": tier,
        "tier_basis": tier_basis,
        "lane": lane_name,
        "lane_basis": lane_basis,
        "bytes_retained": bool(row.get("bytes_retained")),
        "redaction_applied": bool(row.get("redaction_applied")),
        "redacted_derivative": bool(row.get("redacted_derivative")),
        "http_status": row.get("http_status"),
        "changed_vs_prior": "first",  # filled by order_capture_records
        "shared_run": bool(row.get("shared_run")),
    }
    return explicit_columns(record, CAPTURE_RECORD_FIELDS)


def order_capture_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort capture records (source, target, retrieved_at) and compute
    ``changed_vs_prior`` — the digest-diff signal J3 §3.2 names (a byte-only
    change still marks ``changed`` until P35.41's records-digest lands; the
    field's honest basis lives on the freshness row)."""
    records.sort(
        key=lambda r: (
            str(r.get("source_id") or ""),
            str(r.get("target") or ""),
            str(r.get("retrieved_at") or ""),
            str(r.get("mark_recorded_at") or ""),
        )
    )
    prev: dict[tuple[str, str], str | None] = {}
    for r in records:
        key = (str(r.get("source_id") or ""), str(r.get("target") or ""))
        digest = r.get("digest")
        if key not in prev:
            r["changed_vs_prior"] = "first"
        elif digest is None or prev[key] is None:
            r["changed_vs_prior"] = "not_comparable (no digest)"
        else:
            r["changed_vs_prior"] = "changed" if str(digest) != prev[key] else "unchanged"
        if digest is not None:
            prev[key] = str(digest)
    return records


# ---------------------------------------------------------------------------
# sig.source-freshness/1 — cadence rule + state inputs + the two change
# columns + the volatility basis (K9 C-4…C-7)
# ---------------------------------------------------------------------------


def _source_volatility(
    claims: Iterable[Mapping[str, Any]],
    predicate_classes: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Per-source volatility basis: the distribution of the source's
    published-claim predicates by registry class plus the unregistered and
    undated-observation counts (C-5 — basis fields, never "unknown" or a
    fake "0 stale"; P35.41 computes the displayed verdict)."""
    by_source: dict[str, dict[str, Any]] = {}
    for c in claims:
        sid = str(_claim_get(c, "source_id") or "")
        if not sid:
            continue
        entry = by_source.setdefault(
            sid,
            {"distribution": {}, "unregistered_predicate": 0, "undated": 0, "dated": 0},
        )
        pred = str(_claim_get(c, "predicate_id") or "")
        cls = predicate_classes.get(pred)
        if cls is None:
            entry["unregistered_predicate"] += 1
        else:
            entry["distribution"][cls] = entry["distribution"].get(cls, 0) + 1
        if _claim_get(c, "observed_at"):
            entry["dated"] += 1
        else:
            entry["undated"] += 1
    return by_source


def _last_upstream_change(captures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The C-6 'last upstream change' column over a source's capture marks:
    the latest capture whose digest differs from the prior capture of the
    same target (J3's interim rule — the upstream-declared value and the
    canonical ``records_digest`` land with P35.41's connector roll; the
    basis names the interim)."""
    by_target: dict[str, list[Mapping[str, Any]]] = {}
    for row in captures:
        key = str(row.get("target_key") or row.get("source_uri") or "")
        by_target.setdefault(key, []).append(row)
    latest_change: str | None = None
    for rows in by_target.values():
        rows = sorted(
            rows,
            key=lambda r: (
                str(r.get("retrieved_at") or ""),
                str(r.get("mark_recorded_at") or ""),
            ),
        )
        prev_digest = None
        for r in rows:
            digest = r.get("mark_digest")
            ts = _iso(r.get("retrieved_at")) or _iso(r.get("mark_recorded_at"))
            if prev_digest is not None and digest != prev_digest and ts:
                if latest_change is None or ts > latest_change:
                    latest_change = ts
            if digest is not None:
                prev_digest = digest
    if latest_change is not None:
        return {
            "value": latest_change,
            "basis": "capture_digest (interim — a formatting-only byte change may move this date)",
        }
    if by_target:
        return {
            "value": None,
            "basis": "capture_digest (no digest change recorded — may understate real changes)",
        }
    return {"value": None, "basis": "not_detectable (no captures recorded)"}


def freshness_records(
    *,
    source_ids: Iterable[str],
    executions_by_source: Mapping[str, Sequence[Mapping[str, Any]]],
    capture_rows_by_source: Mapping[str, Sequence[Mapping[str, Any]]],
    claim_counts: Mapping[str, int],
    volatility_by_source: Mapping[str, Mapping[str, Any]],
    cadence_sources: Mapping[str, Mapping[str, str]] | None,
    at: datetime,
) -> list[dict[str, Any]]:
    """One ``sig.source-freshness/1`` row per source the spine evidences or
    the cadence doc declares — the state inputs P35.41's verdict consumes,
    every value carrying its evaluation time (the release as-of)."""
    out: list[dict[str, Any]] = []
    for sid in sorted(set(source_ids)):
        declared = (cadence_sources or {}).get(sid)
        cadence_missing = cadence_sources is None
        declared_fields = dict(declared or {})
        scheduled = bool(declared) and declared_fields.get("state", "enabled") == "enabled"
        one_time = declared_fields.get("cadence", "").lower() in {
            "one_time",
            "one-time",
            "one_time_load",
        }
        executions = [
            {
                "finished_at": _dt(e.get("finished_at")) or _dt(e.get("started_at")),
                "status": e.get("completion_status")
                or ("failed" if e.get("error_class") else None),
            }
            for e in executions_by_source.get(sid, [])
        ]
        state = freshness_state(
            cadence_cron=declared_fields.get("cron") or None,
            cadence_word=declared_fields.get("cadence", ""),
            scheduled=scheduled,
            one_time_load=one_time,
            has_records=claim_counts.get(sid, 0) > 0,
            executions=executions,
            at=at,
        )
        vol = volatility_by_source.get(sid)
        record = {
            "schema": FRESHNESS_RECORD_SCHEMA,
            "source_id": sid,
            "cadence_rule": (
                "not_recorded (cadence doc unreadable)"
                if cadence_missing
                else (
                    cadence_rule(
                        str(declared_fields.get("cron", "")),
                        str(declared_fields.get("cadence", "")),
                    )
                    if declared and declared.get("cron")
                    else "not_scheduled"
                )
            ),
            "cadence_basis": (
                "not_recorded"
                if cadence_missing
                else ("ops/cadence.toml" if declared else "not_declared")
            ),
            "cadence_state": declared_fields.get("state") if declared else None,
            "scheduled": scheduled,
            "one_time_load": one_time,
            "freshness_state": state.state,
            "run_record_missing": state.run_record_missing,
            "evaluated_at": iso_utc(state.evaluated_at),
            "last_upstream_change": _last_upstream_change(capture_rows_by_source.get(sid, [])),
            "last_sig_records_change": {
                "value": "first_release" if claim_counts.get(sid, 0) > 0 else "not_published",
                "basis": "no previous release carries per-source slices (UX9-4/P36.68)",
            },
            "volatility": (
                {
                    "distribution": vol["distribution"],
                    "unregistered_predicate": vol["unregistered_predicate"],
                    "basis": "predicate_registry over published claims (interim — P35.41 refines)",
                }
                if vol
                else {"basis": "not_evaluable (no published claims)"}
            ),
            "staleness": (
                {
                    "evaluable": vol["dated"],
                    "not_evaluable": vol["undated"],
                    "basis": "undated observations are never '0 stale' (C-5/F-137)",
                }
                if vol
                else {"basis": "not_evaluable (no published claims)"}
            ),
        }
        out.append(explicit_columns(record, FRESHNESS_RECORD_FIELDS))
    return out


# ---------------------------------------------------------------------------
# sig.source-issue/1 — the auto-detected classes (J3 §7.3)
# ---------------------------------------------------------------------------


def _execution_instant(rec: Mapping[str, Any]) -> str | None:
    return rec.get("finished_at") or rec.get("started_at") or rec.get("recorded_at")


def _execution_issue_classes(rec: Mapping[str, Any]) -> set[str]:
    """The J3 §7.3 classes one run record evidences (closed vocabulary —
    internal error classes like ``db_connection_lost`` never surface as
    public issue classes; quarantine counts surface as
    ``quarantine_<reason>`` by reason class, never payload)."""
    out: set[str] = set()
    err = rec.get("error_class")
    if err and valid_issue_class(str(err)):
        out.add(str(err))
    for reason in rec.get("rejected") or {}:
        if reason == "other_unclassifiable":
            continue
        if valid_issue_class(str(reason)):
            out.add(str(reason))
        elif valid_quarantine_reason(str(reason)):
            out.add(f"quarantine_{reason}")
    if (rec.get("rate_limit_events") or 0) > 0:
        out.add("rate_limited")
    if rec.get("quota_reached"):
        out.add("quota_reached")
    if rec.get("budget_reached"):
        out.add("budget_reached")
    if (rec.get("disappearances") or 0) > 0:
        out.add("disappearance")
    for r in rec.get("robots") or []:
        if r.get("outcome") == "disallowed" and int(r.get("count") or 0) > 0:
            out.add("robots_disallow")
    if rec.get("outcome") in {"ok", "partial"} and rec.get("records_emitted") == 0:
        # SIG-ENG-021 — silent success is an issue, not a green row.
        out.add("zero_records")
    return out


def issue_records(
    *,
    run_records: Sequence[Mapping[str, Any]],
    capture_rows: Sequence[Mapping[str, Any]],
    freshness_rows: Sequence[Mapping[str, Any]],
    scheduler_drift: Mapping[str, bool] | None = None,
    at: datetime,
) -> list[dict[str, Any]]:
    """Detect the J3 §7.3 auto issue classes into append-only instances
    keyed ``(source_id, class, opened_at)``: ``opened_at`` = the first
    observation showing the class, ``last_seen_at`` = the latest,
    ``closed_at`` = the first later execution not showing it (still-open
    = null), ``count`` = the number of observations showing it. Curated
    ``known_issues.toml`` issues are P36.49's — only the auto classes
    land here.
    """
    instances: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _fire(source: str, cls: str, instant: str | None, basis: str) -> None:
        if not source or not valid_issue_class(cls):
            return
        inst = instant or iso_utc(at) or "not_recorded"
        open_key = next(
            (
                k
                for k, v in instances.items()
                if k[0] == source and k[1] == cls and v["closed_at"] is None
            ),
            None,
        )
        if open_key is not None:
            issue = instances[open_key]
            issue["last_seen_at"] = max(issue["last_seen_at"], inst)
            issue["count"] += 1
            return
        instances[(source, cls, inst)] = {
            "schema": ISSUE_RECORD_SCHEMA,
            "issue_id": f"issue:{source}:{cls}:{inst}",
            "source_id": source,
            "issue_class": cls,
            "opened_at": inst,
            "last_seen_at": inst,
            "closed_at": None,
            "count": 1,
            "basis": basis,
        }

    # Executions ordered oldest-first per source; a stretch of executions
    # showing a class is one instance, closed by the first clean later run.
    by_source: dict[str, list[Mapping[str, Any]]] = {}
    for rec in run_records:
        by_source.setdefault(str(rec.get("source_id") or ""), []).append(rec)
    for source, recs in by_source.items():
        recs.sort(key=lambda r: _execution_instant(r) or "")
        per_run: list[tuple[str | None, set[str]]] = [
            (_execution_instant(r), _execution_issue_classes(r)) for r in recs
        ]
        for inst, classes in per_run:
            for cls in sorted(classes):
                _fire(source, cls, inst, "run_record")
        # Close: the first execution after the last showing that lacks it.
        classes_seen = {k[1] for k in instances if k[0] == source}
        for cls in classes_seen:
            open_key = next(
                (
                    k
                    for k, v in instances.items()
                    if k[0] == source and k[1] == cls and v["closed_at"] is None
                ),
                None,
            )
            if open_key is None:
                continue
            last_shown = max((inst or "" for inst, cs in per_run if cls in cs), default="")
            later_clean = next(
                (inst for inst, cs in per_run if (inst or "") > last_shown and cls not in cs),
                None,
            )
            if later_clean:
                instances[open_key]["closed_at"] = later_clean

    # Captures: a mark whose bytes were not retained is capture_not_retained.
    for row in capture_rows:
        if row.get("bytes_retained") is False:
            _fire(
                str(row.get("source_id") or ""),
                "capture_not_retained",
                _iso(row.get("retrieved_at")) or _iso(row.get("mark_recorded_at")),
                "capture_mark",
            )

    # Freshness-state classes (evaluated at the release as-of) and the
    # recorded scheduler-drift signal (the live comparison is the probe
    # machinery's; this export only carries what the record evidences).
    for row in freshness_rows:
        state = row.get("freshness_state")
        if state in {"late", "overdue", "never_run"}:
            _fire(str(row["source_id"]), str(state), row.get("evaluated_at"), "freshness_state")
        if (scheduler_drift or {}).get(str(row["source_id"])):
            _fire(
                str(row["source_id"]),
                "scheduler_drift",
                row.get("evaluated_at"),
                "scheduler_probe",
            )

    out = [explicit_columns(v, ISSUE_RECORD_FIELDS) for v in instances.values()]
    out.sort(key=lambda r: (r["source_id"], r["issue_class"], r["opened_at"] or ""))
    return out


# ---------------------------------------------------------------------------
# The artifact emission
# ---------------------------------------------------------------------------


def _jsonl(records: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(dict(r), sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        for r in records
    )


def emit_transparency_artifacts(
    raw: Mapping[str, Any],
    *,
    claims: Sequence[Any] = (),
    cadence_sources: Mapping[str, Mapping[str, str]] | None = None,
    cadence_path: str | Path | None = None,
    scheduler_drift: Mapping[str, bool] | None = None,
    at: datetime,
) -> dict[str, bytes]:
    """The four ``transparency/`` release artifacts — every field through
    the scrub, every honesty token typed. ``raw`` is the export's guarded
    raw map (the ``TRANSPARENCY_QUERIES`` keys); a missing view degrades to
    empty files — honest absence, never a fabricated row. ``at`` is the
    release evaluation instant (the export as-of — a release-bound value
    never reads the reader's clock, K9 C-4).
    """
    run_rows = _rows(raw.get("transparency_runs") or [], TRANSPARENCY_RUN_VIEW_COLUMNS)
    capture_rows = _rows(raw.get("transparency_captures") or [], TRANSPARENCY_CAPTURE_VIEW_COLUMNS)
    rights_rows = _rows(raw.get("transparency_source_rights") or [], SOURCE_RIGHTS_COLUMNS)
    predicate_classes = {
        str(r[0]): str(r[1]) for r in (raw.get("transparency_predicates") or []) if r and r[1]
    }

    if cadence_sources is None:
        cadence_sources = load_cadence_sources(cadence_path)

    lane_by_source = _lane_map(rights_rows)

    run_recs = [run_record(r) for r in run_rows]
    run_recs.sort(key=lambda r: (str(r.get("source_id") or ""), _execution_instant(r) or ""))

    cap_recs = [
        capture_record(r, lane=lane_by_source.get(str(r.get("source_id") or "")))
        for r in capture_rows
    ]
    cap_recs = order_capture_records(cap_recs)

    executions_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for r in run_rows:
        executions_by_source.setdefault(str(r.get("source_id") or ""), []).append(r)
    captures_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for r in capture_rows:
        captures_by_source.setdefault(str(r.get("source_id") or ""), []).append(r)
    claim_counts: dict[str, int] = {}
    for c in claims:
        sid = str(_claim_get(c, "source_id") or "")
        if sid:
            claim_counts[sid] = claim_counts.get(sid, 0) + 1
    vol = _source_volatility(claims, predicate_classes)

    source_ids = (
        set(executions_by_source)
        | set(captures_by_source)
        | set(claim_counts)
        | set(cadence_sources or {})
    )

    freshness = freshness_records(
        source_ids=source_ids,
        executions_by_source=executions_by_source,
        capture_rows_by_source=captures_by_source,
        claim_counts=claim_counts,
        volatility_by_source=vol,
        cadence_sources=cadence_sources,
        at=at,
    )

    issues = issue_records(
        run_records=run_recs,
        capture_rows=capture_rows,
        freshness_rows=freshness,
        scheduler_drift=scheduler_drift,
        at=at,
    )

    return {
        TRANSPARENCY_RUNS_PATH: _jsonl(run_recs),
        TRANSPARENCY_CAPTURES_PATH: _jsonl(cap_recs),
        TRANSPARENCY_ISSUES_PATH: _jsonl(issues),
        TRANSPARENCY_FRESHNESS_PATH: _jsonl(freshness),
    }


__all__ = [
    "CAPTURE_RECORD_FIELDS",
    "CAPTURE_RECORD_SCHEMA",
    "FRESHNESS_RECORD_FIELDS",
    "FRESHNESS_RECORD_SCHEMA",
    "ISSUE_RECORD_FIELDS",
    "ISSUE_RECORD_SCHEMA",
    "RUN_RECORD_FIELDS",
    "RUN_RECORD_SCHEMA",
    "SOURCE_RIGHTS_COLUMNS",
    "TRANSPARENCY_CAPTURES_PATH",
    "TRANSPARENCY_FRESHNESS_PATH",
    "TRANSPARENCY_ISSUES_PATH",
    "TRANSPARENCY_QUERIES",
    "TRANSPARENCY_RUNS_PATH",
    "capture_record",
    "emit_transparency_artifacts",
    "freshness_records",
    "issue_records",
    "load_cadence_sources",
    "order_capture_records",
    "run_record",
]
