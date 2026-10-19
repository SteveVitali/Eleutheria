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

P35.35 (row 313, J3 §3.3 item 3 + §4.3; K9 §3.2 C-1 + §5.4 C-6; J4 S-6/S-11)
adds the source-metadata pair:

* ``transparency/sources.json`` — ``sig.transparency-sources/1``: one
  object per **registry** source (the committed ``sources.toml`` is the
  registry of record — the lane + Part VIII fields land from its
  ``[redistribution]`` blocks; ``v_transparency_source`` corroborates the
  DB mirror and carries the latest rights decision + last-seen columns).
  Lane ``raw-ok``/``derived-only``/``link-only`` rows render the full
  record — identity, licence, the recorded lane + evidence + decision
  authority, ground-truth URLs through S-6 (full URL only for
  raw-ok/derived-only whose source published; host+path-hash otherwise;
  ``no_upstream_url_recorded`` when none), cadence, the two change columns
  under the same field names and interim basis labels ``freshness.jsonl``
  uses (the C-6 "same field, not a new one" instruction), and the
  published claims/sites counts. Gated, refused, withdrawn and
  ``unknown``/``restricted``-lane sources render the S-11 registry-only
  row — name, publisher, status, reason class, lane, homepage host — never
  runs, captures, samples or probe details.
* ``transparency/counts.json`` — ``sig.source-counts/1``: the K9 C-1
  lifecycle partition (every registry row in exactly one of ``withdrawn``
  · ``published`` · ``ingested_not_published`` · ``permitted_not_ingested``
  · ``gated`` · ``refused``, each named by its predicate and carrying its
  id list) plus the orthogonal named attributes (rights permitted,
  scheduled, run records, site records, lane, open issues) and the
  anomaly list — identifiers carrying data with no registry row, listed by
  id and never counted as sources. A CI check recomputes every number
  from ``sources.json``.

The robots-disregard disclosure is host + count + the GL-GATE-08 decision
reference — never per-request detail (D-J3-2 [B-19]).
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from policy.freshness import (
    cadence_rule,
    freshness_state,
    valid_issue_class,
    valid_quarantine_reason,
)
from policy.transparency import (
    NO_UPSTREAM_URL,
    PART_VIII_SEALED_CLASSES,
    TIER_SEALED,
    TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
    TRANSPARENCY_RUN_VIEW_COLUMNS,
    TRANSPARENCY_SOURCE_VIEW_COLUMNS,
    LaneDecision,
    error_counts,
    explicit_columns,
    gated_source_row,
    interim_lane,
    iso_utc,
    opaque_id,
    reviewer_role,
    robots_disclosure_rows,
    scrub_source_url,
    scrub_text,
    served_storage_tier,
    upstream_host,
    valid_error_class,
)

#: Schema ids (J3 §3.2).
RUN_RECORD_SCHEMA = "sig.run-record/1"
CAPTURE_RECORD_SCHEMA = "sig.capture-record/1"
ISSUE_RECORD_SCHEMA = "sig.source-issue/1"
FRESHNESS_RECORD_SCHEMA = "sig.source-freshness/1"
SOURCE_RECORD_SCHEMA = "sig.transparency-sources/1"
COUNTS_SCHEMA = "sig.source-counts/1"

#: Release artifact paths under ``transparency/`` (J3 §3.1–3.2).
TRANSPARENCY_RUNS_PATH = "transparency/runs.jsonl"
TRANSPARENCY_CAPTURES_PATH = "transparency/captures.jsonl"
TRANSPARENCY_ISSUES_PATH = "transparency/issues.jsonl"
TRANSPARENCY_FRESHNESS_PATH = "transparency/freshness.jsonl"
TRANSPARENCY_SOURCES_PATH = "transparency/sources.json"
TRANSPARENCY_COUNTS_PATH = "transparency/counts.json"

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
    "transparency_sources": (
        "v_transparency_source",
        "SELECT "
        + ", ".join(TRANSPARENCY_SOURCE_VIEW_COLUMNS)
        + " FROM v_transparency_source ORDER BY source_id",
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

#: The full ``sig.transparency-sources/1`` row — a lane-evidenced source's
#: record (J3 §4.3 + K9 §8's ``sig.source-row/1`` subset the committed
#: registry + views can honestly populate). Deliberately absent:
#: ``robots_policy``, ``notes``, ``contact``, ``auth_model``,
#: ``access_method`` (K10 §4's never-shown registry fields), reviewer
#: identity beyond ROLE, and the P8 material itself (the class token
#: publishes; the payload never does).
SOURCE_ROW_FIELDS: tuple[str, ...] = (
    "schema",
    "source_id",
    "name",
    "publisher",
    "publisher_type",
    "lifecycle_state",
    "status_flags",
    "lane",
    "lane_basis",
    "lane_evidence",
    "lane_decision_authority",
    "lane_review_needed",
    "part_viii_class",
    "licence",
    "ground_truth",
    "cadence",
    "last_successful_run",
    "last_upstream_change",
    "last_sig_records_change",
    "published_claims",
    "published_sites",
    "review",
)

#: The S-11 gated row — J3 §4.3's registry-only page twin (identity,
#: status, reason class, homepage-host — never runs, captures, samples or
#: probe details) plus the bookkeeping fields ``counts.json`` must be
#: able to recompute from ``sources.json`` alone (SIG-TRANSP-D27):
#: lifecycle state, lane, flags, declared cadence and site naming are all
#: registry/ops metadata, not upstream detail.
GATED_SOURCE_ROW_FIELDS: tuple[str, ...] = (
    "schema",
    "source_id",
    "name",
    "publisher",
    "publisher_type",
    "status",
    "homepage_url",
    "reason_class",
    "lifecycle_state",
    "lane",
    "lane_basis",
    "part_viii_class",
    "status_flags",
    "cadence",
    "published_sites",
)

#: The K9 C-1 lifecycle states, in partition precedence order (first
#: match wins). ``withdrawn`` has no recorded signal yet — a source-level
#: withdrawal is a gate decision (D-J3-5) the registry does not carry;
#: the partition still names the state so its count is defined, never
#: absent (0 ids with its predicate named).
LIFECYCLE_STATES: tuple[str, ...] = (
    "withdrawn",
    "published",
    "ingested_not_published",
    "permitted_not_ingested",
    "gated",
    "refused",
)

LIFECYCLE_DEFINITIONS: dict[str, str] = {
    "withdrawn": (
        "a source-level withdrawal from publication is recorded "
        "(no withdrawal is recorded in this registry — the predicate "
        "exists so the state is named, not implied)"
    ),
    "published": (
        "≥1 claim from the source passes the publication gate in this "
        "release (the claims this export carries)"
    ),
    "ingested_not_published": (
        "≥1 completion recording claims_inserted > 0 or ≥1 capture mark, "
        "but no claim passes the publication gate in this release"
    ),
    "permitted_not_ingested": (
        "ingestion_permitted = true and no recorded ingestion evidence "
        "(no claim, no claims_inserted > 0 completion, no capture mark)"
    ),
    "gated": (
        "ingestion_permitted false/absent, not refused, no published "
        "claims — the source waits on a rights review"
    ),
    "refused": (
        "the registry records a do-not-ingest decision (compact_status = permission_declined)"
    ),
}

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
# The source registry (registry of record — P35.35)
# ---------------------------------------------------------------------------

_SOURCES_PATH = (
    Path(__file__).resolve().parents[3]
    / "connectors"
    / "src"
    / "connectors"
    / "data"
    / "sources.toml"
)


def load_source_registry(path: str | Path | None = None) -> dict[str, dict[str, Any]] | None:
    """The committed ``sources.toml`` registry of record, keyed by source id.

    The export cannot import ``connectors`` (the package boundary is
    one-way); the same data lands through ``tomllib`` — the
    ``boundary_pack.py`` precedent. Returns ``None`` when the doc cannot be
    read: ``sources.json`` then emits ``registry_source: not_recorded``
    rather than fabricating a source list.
    """
    p = Path(path) if path is not None else _SOURCES_PATH
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    out: dict[str, dict[str, Any]] = {}
    for sid, row in doc.get("sources", {}).items():
        if not isinstance(row, dict):
            continue
        rights = row.get("rights") or {}
        red = row.get("redistribution") or {}
        out[str(sid)] = {
            "name": str(row.get("name", "")),
            "source_kind": str(row.get("source_kind", "")),
            "homepage_url": str(row.get("homepage_url", "")),
            "custody_posture": str(row.get("custody_posture", "LINK")),
            "compact_status": str(row.get("compact_status", "not_contacted")),
            "ingestion_permitted": bool(row.get("ingestion_permitted", False)),
            "cadence": str(row.get("cadence", "")),
            "rights_reviewed_by": str(row.get("rights_reviewed_by", "")),
            "rights_reviewed_on": row.get("rights_reviewed_on"),
            "rights": {
                "spdx": str(rights.get("spdx", "UNDETERMINED")),
                "attribution": str(rights.get("attribution", "")),
                "redistributable": bool(rights.get("redistributable", False)),
                "derivative_permitted": bool(rights.get("derivative_permitted", False)),
                "terms_url": str(rights.get("terms_url", "")),
            },
            "redistribution": {
                "lane": str(red.get("lane", "")).strip(),
                "evidence": str(red.get("evidence", "")),
                "evidence_uri": str(red.get("evidence_uri", "")),
                "decision_authority": str(red.get("decision_authority", "")),
                "review_needed": bool(red.get("review_needed", False)),
                "part_viii_class": str(red.get("part_viii_class", "")).strip(),
                "packet_limited": bool(red.get("packet_limited", False)),
                "sig_labelled_cc0": bool(red.get("sig_labelled_cc0", False)),
            },
        }
    return out


# ---------------------------------------------------------------------------
# sig.transparency-sources/1 — the J3 §4.3 source-metadata record
# ---------------------------------------------------------------------------


def _source_redistributable(reg: Mapping[str, Any]) -> str:
    """The honest redistributable vocabulary — the ``_registry_lane``
    normalisation: ``redistributable=false`` on an unreviewed record is
    ``UNDETERMINED``, never a recorded refusal."""
    rights = reg.get("rights") or {}
    reviewed = bool(reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on"))
    if str(rights.get("spdx", "")) == "UNDETERMINED":
        return "UNDETERMINED"
    if rights.get("redistributable"):
        return "yes"
    return "no" if reviewed else "UNDETERMINED"


def _registry_lane_decision(reg: Mapping[str, Any]) -> LaneDecision:
    """The source's lane as the registry of record declares it — the
    recorded ``[redistribution]`` verdict where the block lands, else the
    interim rights-record basis (the fallback's basis is labelled, never a
    silent upgrade to a reviewed lane)."""
    red = reg.get("redistribution") or {}
    if red.get("lane"):
        return LaneDecision(str(red["lane"]), basis="registry:[redistribution]")
    rights = reg.get("rights") or {}
    reviewed = bool(reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on"))
    spdx = str(rights.get("spdx", ""))
    if spdx == "UNDETERMINED":
        redist = "UNDETERMINED"
    elif rights.get("redistributable"):
        redist = "yes"
    else:
        redist = "no" if reviewed else "UNDETERMINED"
    return interim_lane(
        custody_posture=reg.get("custody_posture"),
        spdx=spdx,
        redistributable=redist,
        reviewed=reviewed,
        refused=str(reg.get("compact_status") or "") == "permission_declined",
        packet_limited=bool(red.get("packet_limited")),
        sig_labelled_cc0=bool(red.get("sig_labelled_cc0")),
    )


def _lifecycle_state(
    reg: Mapping[str, Any],
    *,
    published: bool,
    ingested: bool,
) -> str:
    """The K9 §3.2 partition — exactly one state per registry row, first
    match wins. ``withdrawn`` has no recorded signal in this registry: a
    source-level withdrawal is a gate decision (D-J3-5) nothing carries
    yet, so the state exists in the partition definition and never fires —
    honest absence, never a fabricated state."""
    if published:
        return "published"
    if ingested:
        return "ingested_not_published"
    if reg.get("ingestion_permitted"):
        return "permitted_not_ingested"
    if str(reg.get("compact_status") or "") == "permission_declined":
        return "refused"
    return "gated"


def _status_flags(
    reg: Mapping[str, Any],
    *,
    data_bearing: bool,
    has_run_records: bool,
    one_time_load: bool,
    open_issue: bool,
) -> list[str]:
    """The orthogonal flags the data can honestly carry (K9 §4.1 col 7),
    present on every row — full and gated — so ``counts.json`` recomputes
    from ``sources.json`` alone (SIG-TRANSP-D27):

    * ``rights_not_reviewed`` — no completed rights review or not
      permitted;
    * ``run_records_present`` — ≥1 execution row exists;
    * ``run_record_missing`` — data-bearing source with no execution row
      (K9 C-7: records exist but no run record does);
    * ``one_time_load`` — a one-time seed, never a schedule;
    * ``open_issue`` — ≥1 open issue on this release's ``issues.jsonl``.
    """
    flags: list[str] = []
    reviewed = bool(reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on"))
    if not (reg.get("ingestion_permitted") and reviewed):
        flags.append("rights_not_reviewed")
    if has_run_records:
        flags.append("run_records_present")
    elif data_bearing:
        flags.append("run_record_missing")
    if one_time_load:
        flags.append("one_time_load")
    if open_issue:
        flags.append("open_issue")
    return sorted(flags)


def _gated_reason_class(reg: Mapping[str, Any], *, lane: str, part_viii_class: str) -> str:
    """The S-11 reason class for a registry-only row — the closed J3 §4.3
    vocabulary (``terms`` · ``part_viii`` · ``not_reviewed`` plus the
    lifecycle classes ``refused`` / ``gated`` / ``unknown_lane``)."""
    if str(reg.get("compact_status") or "") == "permission_declined":
        return "refused"
    if str(part_viii_class or "") in PART_VIII_SEALED_CLASSES:
        return "part_viii"
    if lane == "restricted":
        return "terms"
    if lane == "unknown":
        reviewed = bool(reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on"))
        return "unknown_lane" if reviewed else "not_reviewed"
    return "gated"


def _scrubbed_ground_truth(url: str, *, lane: str, gate_passed: bool) -> dict[str, Any]:
    """One ground-truth URL through S-1+S-6 — the full credential-stripped
    URL only for raw-ok/derived-only lanes on a gate-passed source; host +
    path-hash otherwise; ``no_upstream_url_recorded`` when absent."""
    scrubbed = scrub_source_url(url or None, lane=lane, gate_passed=gate_passed)
    if scrubbed is None:
        return {"value": NO_UPSTREAM_URL, "host": None}
    if scrubbed.url:
        return {"value": scrubbed.url, "host": scrubbed.host}
    return {
        "value": f"{scrubbed.host}#path_sha256:{scrubbed.path_sha256}",
        "host": scrubbed.host,
    }


def _last_successful_run(executions: Sequence[Mapping[str, Any]]) -> Any:
    """The latest execution finishing ok/partial/quota_reached (K9 col 8);
    honest absences — ``never_run`` with no executions, ``not_recorded``
    when executions carry no recorded success."""
    if not executions:
        return "never_run"
    best: datetime | None = None
    for e in executions:
        status = e.get("completion_status")
        if status not in {"ok", "partial"} and not e.get("quota_reached"):
            continue
        finished = _dt(e.get("finished_at")) or _dt(e.get("started_at"))
        if finished is not None and (best is None or finished > best):
            best = finished
    if best is None:
        return "not_recorded (no successful execution recorded)"
    return iso_utc(best)


def source_record(
    source_id: str,
    *,
    registry_row: Mapping[str, Any],
    view_row: Mapping[str, Any] | None,
    executions: Sequence[Mapping[str, Any]],
    capture_rows: Sequence[Mapping[str, Any]],
    published_claims: int,
    published_sites: bool,
    cadence_decl: Mapping[str, str] | None,
    open_issue: bool,
) -> dict[str, Any]:
    """One ``sig.transparency-sources/1`` row — the J3 §4.3 record.

    The registry of record supplies identity + rights + the recorded
    ``[redistribution]`` fields; the view row corroborates the DB mirror
    and carries the latest rights decision. A gated/refused/withdrawn or
    unknown/restricted-lane source renders the S-11 registry-only row —
    every field through the same scrub, every absence a named token. The
    orthogonal bookkeeping fields ride on gated rows too so every
    ``counts.json`` number recomputes from ``sources.json`` alone.
    """
    reg = registry_row
    red = reg.get("redistribution") or {}
    rights = reg.get("rights") or {}
    decision = _registry_lane_decision(reg)
    lane = decision.lane
    p8 = str(red.get("part_viii_class") or (view_row or {}).get("part_viii_class") or "")

    ingested = bool(capture_rows) or any((e.get("claims_inserted") or 0) > 0 for e in executions)
    data_bearing = ingested or published_claims > 0
    state = _lifecycle_state(reg, published=published_claims > 0, ingested=ingested)

    declared_fields = dict(cadence_decl or {})
    scheduled = bool(cadence_decl) and declared_fields.get("state", "enabled") == "enabled"
    one_time = declared_fields.get("cadence", "").lower() in {
        "one_time",
        "one-time",
        "one_time_load",
    }
    registry_cadence = str(reg.get("cadence") or "")
    cadence_block: dict[str, Any]
    if cadence_decl is None:
        cadence_block = (
            {
                "rule": registry_cadence,
                "basis": "registry, not scheduled",
            }
            if registry_cadence
            else {"rule": "not_scheduled", "basis": "not_declared"}
        )
    else:
        cadence_block = {
            "rule": cadence_rule(
                str(declared_fields.get("cron", "")),
                str(declared_fields.get("cadence", "")),
            )
            if declared_fields.get("cron")
            else "not_scheduled",
            "basis": "ops/cadence.toml",
            "state": declared_fields.get("state"),
        }
    cadence_block = cadence_block | {"scheduled": scheduled, "one_time_load": one_time}
    flags = _status_flags(
        reg,
        data_bearing=data_bearing,
        has_run_records=bool(executions),
        one_time_load=one_time,
        open_issue=open_issue,
    )

    # S-11: gated, refused, withdrawn and unknown/restricted-lane sources
    # publish the registry-only row — never runs, captures, samples or
    # probe details. The lifecycle/lane/flags/cadence fields are registry
    # and ops metadata: they stay so every count remains recomputable.
    if state in {"gated", "refused", "withdrawn"} or lane in {"unknown", "restricted"}:
        homepage_raw = str(reg.get("homepage_url") or "")
        # S-6 on a gated row: the host alone is the publishable form — the
        # full URL never is (only raw-ok/derived-only gate-passed sources
        # render it, and a gated row is never those).
        host = upstream_host(homepage_raw)
        row = gated_source_row(
            {
                "source_id": source_id,
                "name": scrub_text(str(reg.get("name") or "")),
                "publisher": "publisher_not_recorded",
                "publisher_type": str(reg.get("source_kind") or "") or None,
                "status": (
                    state
                    if state in {"gated", "refused", "withdrawn"}
                    else "gated"  # lane-gated, whatever the lifecycle says
                ),
                "homepage_url": (
                    host or (NO_UPSTREAM_URL if not homepage_raw.strip() else "not_publishable")
                ),
            },
            reason_class=_gated_reason_class(reg, lane=lane, part_viii_class=p8),
        )
        row["schema"] = SOURCE_RECORD_SCHEMA
        row["lifecycle_state"] = state
        row["lane"] = lane
        row["lane_basis"] = decision.basis
        row["part_viii_class"] = p8 or None
        row["status_flags"] = flags
        row["cadence"] = cadence_block
        row["published_sites"] = published_sites
        return explicit_columns(row, GATED_SOURCE_ROW_FIELDS)

    gate_passed = published_claims > 0
    homepage = _scrubbed_ground_truth(
        str(reg.get("homepage_url") or ""), lane=lane, gate_passed=gate_passed
    )
    terms = _scrubbed_ground_truth(
        str(rights.get("terms_url") or ""), lane=lane, gate_passed=gate_passed
    )
    view = view_row or {}
    review = {
        "basis": str(view.get("rights_decision_basis") or "no_decision_recorded"),
        "reviewer_role": reviewer_role(str(view.get("rights_decision_reviewer") or "")),
        "decided_at": _iso(view.get("rights_decided_at")),
        "terms_reviewed": bool(view.get("terms_reviewed"))
        or bool(reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on")),
    }
    record = {
        "schema": SOURCE_RECORD_SCHEMA,
        "source_id": source_id,
        "name": scrub_text(str(reg.get("name") or "")),
        "publisher": "publisher_not_recorded",
        "publisher_type": str(reg.get("source_kind") or "") or None,
        "lifecycle_state": state,
        "status_flags": flags,
        "lane": lane,
        "lane_basis": decision.basis,
        "lane_evidence": scrub_text(str(red.get("evidence") or "")) or None,
        "lane_decision_authority": str(red.get("decision_authority") or "") or None,
        "lane_review_needed": bool(red.get("review_needed")),
        "part_viii_class": p8 or None,
        "licence": {
            "spdx": str(rights.get("spdx") or "UNDETERMINED"),
            "redistributable": _source_redistributable(reg),
            "derivative_permitted": (
                "yes"
                if rights.get("derivative_permitted")
                else (
                    "no"
                    if reg.get("rights_reviewed_by") and reg.get("rights_reviewed_on")
                    else "UNDETERMINED"
                )
            ),
            "attribution": scrub_text(str(rights.get("attribution") or "")) or None,
            "terms_reviewed": review["terms_reviewed"],
            "sig_labelled_cc0": bool(red.get("sig_labelled_cc0")),
        },
        "ground_truth": {
            "homepage": homepage["value"],
            "homepage_host": homepage["host"],
            "terms_url": terms["value"],
        },
        "cadence": cadence_block,
        "last_successful_run": _last_successful_run(executions),
        # The same field names + the same interim basis labels
        # ``freshness.jsonl`` carries (K9 C-6 — "the same field, not a new
        # one"): the upstream-declared value and the canonical records
        # digest land with the connector roll; until then the basis says so.
        "last_upstream_change": _last_upstream_change(capture_rows),
        "last_sig_records_change": {
            "value": "first_release" if published_claims > 0 else "not_published",
            "basis": "no previous release carries per-source slices (UX9-4/P36.68)",
        },
        "published_claims": published_claims if published_claims > 0 else "not_published",
        "published_sites": published_sites,
        "review": review,
    }
    return explicit_columns(record, SOURCE_ROW_FIELDS)


# ---------------------------------------------------------------------------
# sig.source-counts/1 — the K9 C-1 lifecycle partition + named attributes
# ---------------------------------------------------------------------------


def recompute_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Derive every ``counts.json`` number from ``sources.json`` rows alone
    (SIG-TRANSP-D27): the release file is the checkable record, never a
    second data source. The producer runs the same function on the rows it
    is about to emit, so a drifted count cannot be written."""
    partition: dict[str, list[str]] = {state: [] for state in LIFECYCLE_STATES}
    permitted = scheduled = one_time = run_present = run_missing = 0
    site_present = open_issues = 0
    lanes: dict[str, int] = {
        lane: 0 for lane in ("raw-ok", "derived-only", "link-only", "restricted", "unknown")
    }
    # Lifecycle ∈ {published, ingested_not_published, permitted_not_ingested}
    # is exactly the set of states ingestion_permitted sources can reach
    # (the gate requires permission; refused/withdrawn carry no permission).
    _PERMITTED_STATES = {
        "published",
        "ingested_not_published",
        "permitted_not_ingested",
    }
    for row in rows:
        sid = str(row.get("source_id") or "")
        state = str(row.get("lifecycle_state") or "")
        if state in partition:
            partition[state].append(sid)
        if state in _PERMITTED_STATES:
            permitted += 1
        lane = str(row.get("lane") or "unknown")
        lanes[lane if lane in lanes else "unknown"] += 1
        cadence = row.get("cadence") or {}
        if cadence.get("scheduled"):
            scheduled += 1
        if cadence.get("one_time_load"):
            one_time += 1
        flags = set(row.get("status_flags") or [])
        if "run_records_present" in flags:
            run_present += 1
        if "run_record_missing" in flags:
            run_missing += 1
        if row.get("published_sites"):
            site_present += 1
        if "open_issue" in flags:
            open_issues += 1
    return {
        "registered": len(rows),
        "partition": partition,
        "rights_permitted": permitted,
        "scheduled": scheduled,
        "one_time_load": one_time,
        "run_records_present": run_present,
        "run_records_missing": run_missing,
        "site_records": site_present,
        "open_issues": open_issues,
        "lanes": lanes,
    }


def source_counts(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    anomalies: Sequence[str],
    at: datetime,
) -> dict[str, Any]:
    """``counts.json`` — every count a named predicate over ``sources.json``
    rows (SIG-TRANSP-D26/D27): the lifecycle partition (Σ = the registry
    row count, id lists per state) plus the orthogonal attributes, and the
    anomaly id list (identifiers carrying data with no registry row —
    listed, never counted)."""
    counts = recompute_counts(source_rows)
    lifecycle = {
        state: {
            "definition": LIFECYCLE_DEFINITIONS[state],
            "count": len(counts["partition"][state]),
            "ids": sorted(counts["partition"][state]),
        }
        for state in LIFECYCLE_STATES
    }
    registered = counts["registered"]
    scheduled = counts["scheduled"]
    one_time = counts["one_time_load"]
    site_present = counts["site_records"]
    return {
        "schema": COUNTS_SCHEMA,
        "as_of": iso_utc(at),
        "universe": {
            "definition": "rows in the source registry (connectors/sources.toml)",
            "count": registered,
        },
        "lifecycle": lifecycle,
        "attributes": {
            "rights_permitted": {
                "definition": "ingestion_permitted = true",
                "count": counts["rights_permitted"],
            },
            "rights_not_permitted": {
                "definition": "ingestion_permitted false or absent",
                "count": registered - counts["rights_permitted"],
            },
            "scheduled": {
                "definition": "declared in ops/cadence.toml with state = enabled",
                "count": scheduled,
            },
            "one_time_load": {
                "definition": "a one-time seed load, never a schedule",
                "count": one_time,
            },
            "not_scheduled": {
                "definition": "no declared enabled schedule and not a one-time load",
                "count": registered - scheduled - one_time,
            },
            "run_records_present": {
                "definition": "≥1 execution row recorded",
                "count": counts["run_records_present"],
            },
            "run_records_missing": {
                "definition": "data-bearing source with no execution row (K9 C-7)",
                "count": counts["run_records_missing"],
            },
            "site_records": {
                "definition": "≥1 published site record names the source",
                "count": site_present,
            },
            "no_site_records": {
                "definition": "no published site record names the source",
                "count": registered - site_present,
            },
            "lanes": dict(counts["lanes"]),
            "open_issues": {
                "definition": "≥1 open issue on this release's issues.jsonl",
                "count": counts["open_issues"],
            },
        },
        "anomalies": {
            "definition": (
                "identifiers carrying data (claims, captures, runs, sites) "
                "with no registry row — listed by id, never counted as sources"
            ),
            "ids": sorted(set(anomalies)),
        },
    }


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


def _lane_map(
    source_rights: Sequence[Mapping[str, Any]],
    source_view: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """source_id → the lane decision used for capture-tier derivation.

    The recorded ``[redistribution]`` verdict wins (via the
    ``v_transparency_source`` mirror row); the interim rights-record
    derivation stands where no mirror row exists, its basis labelled.
    """
    out: dict[str, Any] = {}
    for r in source_rights:
        out[str(r["source_id"])] = {
            "decision": interim_lane(
                custody_posture=r.get("custody_posture"),
                spdx=r.get("spdx_expression"),
                redistributable=r.get("redistributable"),
                reviewed=r.get("reviewed"),
            ),
            "p8": None,
        }
    for r in source_view:
        sid = str(r.get("source_id") or "")
        if not sid:
            continue
        recorded_lane = str(r.get("lane") or "").strip()
        p8 = str(r.get("part_viii_class") or "").strip() or None
        if recorded_lane:
            out[sid] = {
                "decision": LaneDecision(recorded_lane, basis="source_redistribution"),
                "p8": p8,
            }
        elif sid in out:
            out[sid]["p8"] = out[sid]["p8"] or p8
    return out


def capture_record(
    row: Mapping[str, Any], *, lane: Any = None, part_viii_class: Any = None
) -> dict[str, Any]:
    """Scrub one ``v_transparency_capture`` row into ``sig.capture-record/1``.

    The tier is ``served_storage_tier`` — the recorded tier tightened by the
    lane+Part VIII derivation where the recorded row predates the writer's
    derivation (never a silent ``public`` upgrade); a mark with no joined
    capture row derives the lane floor and labels the basis. A sealed-tier
    capture emits no URL/URI at all — even a path-hash would bind it to the
    host.
    """
    lane_name = getattr(lane, "lane", "unknown")
    lane_basis = getattr(lane, "basis", "not_recorded")
    p8 = str(part_viii_class or "") or None

    classification = str(row.get("capture_classification") or "legacy")
    derivation = served_storage_tier(row.get("storage_tier"), lane=lane_name, part_viii_class=p8)
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


_UNSET = object()


def emit_transparency_artifacts(
    raw: Mapping[str, Any],
    *,
    claims: Sequence[Any] = (),
    cadence_sources: Mapping[str, Mapping[str, str]] | None | object = _UNSET,
    cadence_path: str | Path | None = None,
    scheduler_drift: Mapping[str, bool] | None = None,
    source_registry: Mapping[str, Mapping[str, Any]] | None | object = _UNSET,
    sources_path: str | Path | None = None,
    site_source_ids: Iterable[str] = (),
    at: datetime,
) -> dict[str, bytes]:
    """The ``transparency/`` release artifacts — every field through the
    scrub, every honesty token typed. ``raw`` is the export's guarded raw
    map (the ``TRANSPARENCY_QUERIES`` keys); a missing view degrades to
    empty files — honest absence, never a fabricated row. ``at`` is the
    release evaluation instant (the export as-of — a release-bound value
    never reads the reader's clock, K9 C-4).

    ``source_registry`` is the committed ``sources.toml`` map (the
    registry of record — P35.35); left unset it loads from
    ``sources_path`` (defaulting to the committed file), and an explicit
    ``None`` suppresses ``sources.json``/``counts.json`` entirely for
    callers that have no registry surface. ``site_source_ids`` carries the
    source ids this release's published site records name.
    """
    run_rows = _rows(raw.get("transparency_runs") or [], TRANSPARENCY_RUN_VIEW_COLUMNS)
    capture_rows = _rows(raw.get("transparency_captures") or [], TRANSPARENCY_CAPTURE_VIEW_COLUMNS)
    rights_rows = _rows(raw.get("transparency_source_rights") or [], SOURCE_RIGHTS_COLUMNS)
    source_view_rows = _rows(
        raw.get("transparency_sources") or [], TRANSPARENCY_SOURCE_VIEW_COLUMNS
    )
    predicate_classes = {
        str(r[0]): str(r[1]) for r in (raw.get("transparency_predicates") or []) if r and r[1]
    }

    cadence_map = cast(
        "Mapping[str, Mapping[str, str]] | None",
        load_cadence_sources(cadence_path) if cadence_sources is _UNSET else cadence_sources,
    )
    registry_map = cast(
        "Mapping[str, Mapping[str, Any]] | None",
        load_source_registry(sources_path) if source_registry is _UNSET else source_registry,
    )

    lane_by_source = _lane_map(rights_rows, source_view_rows)

    run_recs = [run_record(r) for r in run_rows]
    run_recs.sort(key=lambda r: (str(r.get("source_id") or ""), _execution_instant(r) or ""))

    cap_recs = [
        capture_record(
            r,
            lane=(lane_by_source.get(str(r.get("source_id") or "")) or {}).get("decision"),
            part_viii_class=(lane_by_source.get(str(r.get("source_id") or "")) or {}).get("p8"),
        )
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
        | set(cadence_map or {})
    )

    freshness = freshness_records(
        source_ids=source_ids,
        executions_by_source=executions_by_source,
        capture_rows_by_source=captures_by_source,
        claim_counts=claim_counts,
        volatility_by_source=vol,
        cadence_sources=cadence_map,
        at=at,
    )

    issues = issue_records(
        run_records=run_recs,
        capture_rows=capture_rows,
        freshness_rows=freshness,
        scheduler_drift=scheduler_drift,
        at=at,
    )

    artifacts = {
        TRANSPARENCY_RUNS_PATH: _jsonl(run_recs),
        TRANSPARENCY_CAPTURES_PATH: _jsonl(cap_recs),
        TRANSPARENCY_ISSUES_PATH: _jsonl(issues),
        TRANSPARENCY_FRESHNESS_PATH: _jsonl(freshness),
    }

    if registry_map is not None:
        # P35.35: the source-metadata pair. The registry of record is the
        # universe; identifiers carrying data with no registry row land in
        # ``anomalies`` — listed, never counted (K9 C-1).
        open_issue_sources = {
            str(i.get("source_id") or "") for i in issues if i.get("closed_at") is None
        }
        view_by_source = {str(r.get("source_id") or ""): r for r in source_view_rows}
        site_sources = {str(s) for s in site_source_ids}
        source_rows = [
            source_record(
                sid,
                registry_row=registry_map[sid],
                view_row=view_by_source.get(sid),
                executions=executions_by_source.get(sid, ()),
                capture_rows=captures_by_source.get(sid, ()),
                published_claims=claim_counts.get(sid, 0),
                published_sites=sid in site_sources,
                cadence_decl=(cadence_map or {}).get(sid),
                open_issue=sid in open_issue_sources,
            )
            for sid in sorted(registry_map)
        ]
        anomalies = (
            set(executions_by_source) | set(captures_by_source) | set(claim_counts) | site_sources
        ) - set(registry_map)
        sources_doc = {
            "schema": SOURCE_RECORD_SCHEMA,
            "as_of": iso_utc(at),
            "registry_source": "connectors/src/connectors/data/sources.toml",
            "sources": source_rows,
        }
        counts_doc = source_counts(source_rows, anomalies=sorted(anomalies), at=at)
        artifacts[TRANSPARENCY_SOURCES_PATH] = (
            json.dumps(sources_doc, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        artifacts[TRANSPARENCY_COUNTS_PATH] = (
            json.dumps(counts_doc, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")

    return artifacts


__all__ = [
    "CAPTURE_RECORD_FIELDS",
    "CAPTURE_RECORD_SCHEMA",
    "COUNTS_SCHEMA",
    "FRESHNESS_RECORD_FIELDS",
    "FRESHNESS_RECORD_SCHEMA",
    "GATED_SOURCE_ROW_FIELDS",
    "ISSUE_RECORD_FIELDS",
    "ISSUE_RECORD_SCHEMA",
    "LIFECYCLE_STATES",
    "RUN_RECORD_FIELDS",
    "RUN_RECORD_SCHEMA",
    "SOURCE_RECORD_SCHEMA",
    "SOURCE_RIGHTS_COLUMNS",
    "SOURCE_ROW_FIELDS",
    "TRANSPARENCY_CAPTURES_PATH",
    "TRANSPARENCY_COUNTS_PATH",
    "TRANSPARENCY_FRESHNESS_PATH",
    "TRANSPARENCY_ISSUES_PATH",
    "TRANSPARENCY_QUERIES",
    "TRANSPARENCY_RUNS_PATH",
    "TRANSPARENCY_SOURCES_PATH",
    "capture_record",
    "emit_transparency_artifacts",
    "freshness_records",
    "issue_records",
    "load_cadence_sources",
    "load_source_registry",
    "order_capture_records",
    "recompute_counts",
    "run_record",
    "source_counts",
    "source_record",
]
