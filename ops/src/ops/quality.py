# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The read-only quality harness — the P34.44a probe runner (SIG-CONF-006/007/008/013).

`exports.quality` owns the ruleset: the registry, the ratchet engine and the
record shapes. This module owns the *runner*: for a placement it selects the
registry's checks, runs each implemented evaluator — spine evaluators over a
READ-ONLY connection (the audit login's posture: ``default_transaction_read_only``,
a 60 s statement timeout; the harness opens one transaction and never writes),
or file scans over a release/build directory — and emits the
``sig.quality-report/1`` + ``sig.probe-run/1`` records.

A registered check whose evaluation seam does not exist yet (the replay seam,
the lineage/collapse seams, the procurement surfaces) reports
``not_evaluable`` with the seam named — never a pass, never a silent skip
(SIG-ENG-042 / B4 G11). P34.44b adds the run surface on top of this runner:
the in-container ``nightly`` verb (the ``sig-quality-probe`` job's command —
window-suppressed, record-emitting, alerting on failure), the ``baseline``
verb (the L2 reproduction + baseline proposal leg), and the ``job`` surface
that renders the declaration ``ops/quality_probe.toml``.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exports.quality import (
    CheckRegistry,
    Measurement,
    QualityCheck,
    build_probe_run,
    build_quality_report,
    evaluate_check,
    load_registry,
)

# ---------------------------------------------------------------------------
# The evaluator contract

#: A check evaluator: given the run context it measures the spine/files and
#: returns a Measurement. It NEVER writes; a DB evaluator runs under the
#: read-only session the runner opens.
Evaluator = Callable[["EvalContext"], Measurement]


@dataclass(frozen=True)
class EvalContext:
    """What the runner hands an evaluator for one run."""

    conn: Any = None  # psycopg connection (read-only session) or a test stub
    scan_dir: Path | None = None  # release/build dir for file scans (R/P checks)
    sample_percent: float | None = None  # TABLESAMPLE percent for B2 checks
    sample_seed: int = 42  # the REPEATABLE seed — always recorded


# ---------------------------------------------------------------------------
# DB evaluators — the M-placement spine checks implemented by this ticket.
# Each is a bounded SELECT-only probe. The aggregate numbers come back in
# `detail` so the report carries the evidence, not just the metric.


def _rows(conn: Any, sql: str, params: tuple = ()) -> list[Mapping[str, Any]]:
    cur = conn.execute(sql, params)
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]


def _not_evaluable(check_id: str, reason: str) -> Measurement:
    return Measurement(check_id=check_id, offered=0, evaluated=0, not_evaluable_reason=reason)


def _claim_block(ctx: EvalContext) -> str:
    """The sampled claim relation for the heavy B2 census checks."""
    if ctx.sample_percent is not None:
        return (
            f"claim TABLESAMPLE SYSTEM ({float(ctx.sample_percent)}) "
            f"REPEATABLE ({int(ctx.sample_seed)})"
        )
    return "claim"


def eval_gq03(ctx: EvalContext) -> Measurement:
    """GQ-03 — exact current repeats of (subject, predicate, value, source)."""
    sql = f"""
        WITH cur AS (
          SELECT c.subject_id, c.predicate_id,
                 coalesce(c.value_text, c.value_num::text, c.value_geom::text,
                          c.value_json::text) AS val, ea.source_id
          FROM {_claim_block(ctx)} c
          JOIN claim_evidence ce ON ce.claim_id = c.claim_id
          JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
          JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
          WHERE upper_inf(c.sys_period)
        ), dup AS (
          SELECT count(*) AS members
          FROM cur GROUP BY subject_id, predicate_id, val, source_id
          HAVING count(*) > 1
        )
        SELECT (SELECT count(*) FROM cur) AS total,
               coalesce((SELECT sum(members) FROM dup), 0) AS duplicate_members
    """
    r = _rows(ctx.conn, sql)[0]
    total, dup = int(r["total"]), int(r["duplicate_members"])
    return Measurement(
        check_id="GQ-03",
        offered=total,
        evaluated=total,
        measured=(dup / total) if total else None,
        sampled=ctx.sample_percent is not None,
        detail={
            "duplicate_members": dup,
            "sample_percent": ctx.sample_percent,
            "seed": ctx.sample_seed if ctx.sample_percent is not None else None,
        },
    )


def eval_gq05(ctx: EvalContext) -> Measurement:
    """GQ-05 — key stability: subjects whose point moved > 0.0005° between a
    source's latest two runs (L3 §3.1). A source with one run is honestly
    not-yet-comparable; zero comparable subjects is reported, not hidden."""
    rows = _rows(
        ctx.conn,
        """
        SELECT ea.source_id, c.subject_id, c.ingest_run_id AS run_id,
               max(CASE WHEN c.predicate_id = 'camera_latitude'
                        THEN c.value_num END) AS lat,
               max(CASE WHEN c.predicate_id = 'camera_longitude'
                        THEN c.value_num END) AS lon
        FROM claim c
        JOIN claim_evidence ce ON ce.claim_id = c.claim_id
        JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
        JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
        WHERE upper_inf(c.sys_period)
          AND c.predicate_id IN ('camera_latitude', 'camera_longitude')
        GROUP BY ea.source_id, c.subject_id, c.ingest_run_id
        """,
    )
    order = {
        str(r["run_id"]): i
        for i, r in enumerate(
            _rows(
                ctx.conn,
                "SELECT run_id FROM ingest_run ORDER BY finished_at NULLS LAST, run_id",
            )
        )
    }
    by_source: dict[str, dict[str, dict[str, tuple[float, float]]]] = {}
    for r in rows:
        if r["lat"] is None or r["lon"] is None:
            continue
        by_source.setdefault(str(r["source_id"]), {}).setdefault(str(r["run_id"]), {})[
            str(r["subject_id"])
        ] = (float(r["lat"]), float(r["lon"]))
    compared = moved = offered = 0
    skipped_sources: list[str] = []
    for source_id, per_run in by_source.items():
        runs = sorted(per_run, key=lambda k: order.get(k, 1 << 30))
        # subjects in the latest run are the offered population — a source
        # with one run offers them but cannot evaluate them (honest count)
        offered += len(per_run[runs[-1]])
        if len(runs) < 2:
            skipped_sources.append(source_id)
            continue
        latest, previous = per_run[runs[-1]], per_run[runs[-2]]
        for subject, (lat, lon) in latest.items():
            prev = previous.get(subject)
            if prev is None:
                continue
            compared += 1
            if abs(lat - prev[0]) > 0.0005 or abs(lon - prev[1]) > 0.0005:
                moved += 1
    return Measurement(
        check_id="GQ-05",
        offered=offered,
        evaluated=compared,
        measured=(moved / compared) if compared else 0.0,
        detail={
            "moved": moved,
            "sources_compared": len(by_source) - len(skipped_sources),
            "sources_single_run": skipped_sources,
        },
    )


#: The seed publisher blocklist for GQ-07 — the publisher-as-operator strings
#: L2 M23 counted. The check's fixing row (P35.26) owns the real catalog; the
#: seed keeps the mechanical scan honest ("publisher strings are blocklisted").
PUBLISHER_BLOCKLIST: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bflock\b",
        r"\bmotorola\b",
        r"\bvigilant\b",
        r"\bgenetec\b",
        r"\brekor\b",
        r"\bneology\b",
        r"\bplatefinder\b",
    )
)


def eval_gq07(ctx: EvalContext) -> Measurement:
    """GQ-07 — camera_operator is an organization entity or the literal
    'unknown'; publisher strings violate."""
    rows = _rows(
        ctx.conn,
        """
        SELECT c.claim_id, c.value_text, c.object_entity, e.entity_type
        FROM claim c
        LEFT JOIN entity e ON e.entity_id = c.object_entity
        WHERE c.predicate_id = 'camera_operator' AND upper_inf(c.sys_period)
        """,
    )
    violations = publisher_hits = 0
    for r in rows:
        if r["object_entity"] is not None:
            if r["entity_type"] != "organization":
                violations += 1
            continue
        text = str(r["value_text"] or "")
        if text.strip().lower() == "unknown":
            continue
        violations += 1
        if any(p.search(text) for p in PUBLISHER_BLOCKLIST):
            publisher_hits += 1
    return Measurement(
        check_id="GQ-07",
        offered=len(rows),
        evaluated=len(rows),
        measured=violations,
        detail={
            "violations": violations,
            "publisher_blocklist_hits": publisher_hits,
        },
    )


def eval_gq11(ctx: EvalContext) -> Measurement:
    """GQ-11 — undeclared copying: source-layer pairs where > 50 % of the
    smaller layer's distinct points sit within 1 m of the other layer's.
    No declared-lineage seam exists yet, so every overlap counts as undeclared
    — matching L2's "at least 11 inferred, 0 declared"."""
    pairs = _rows(
        ctx.conn,
        """
        WITH pts AS (
          SELECT DISTINCT ea.source_id, c.subject_id, c.value_geom
          FROM claim c
          JOIN claim_evidence ce ON ce.claim_id = c.claim_id
          JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
          JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
          WHERE upper_inf(c.sys_period) AND c.value_geom IS NOT NULL
        ), layers AS (
          SELECT source_id, count(DISTINCT subject_id) AS n
          FROM pts GROUP BY source_id
        ), pairlist AS (
          SELECT a.source_id AS a_src, b.source_id AS b_src,
                 a.n AS a_n, b.n AS b_n
          FROM layers a JOIN layers b ON a.source_id < b.source_id
        ), overlap AS (
          SELECT a.source_id AS a_src, b.source_id AS b_src,
                 count(DISTINCT a.subject_id) AS a_within,
                 count(DISTINCT b.subject_id) AS b_within
          FROM pts a JOIN pts b
            ON a.source_id < b.source_id
           AND ST_DWithin(a.value_geom::geography, b.value_geom::geography, 1.0)
          GROUP BY a.source_id, b.source_id
        )
        SELECT p.a_src, p.b_src, p.a_n, p.b_n,
               coalesce(o.a_within, 0) AS a_within,
               coalesce(o.b_within, 0) AS b_within
        FROM pairlist p
        LEFT JOIN overlap o ON o.a_src = p.a_src AND o.b_src = p.b_src
        """,
    )
    violating = []
    for r in pairs:
        smaller = min(int(r["a_n"]), int(r["b_n"]))
        covered = int(r["a_within"]) if int(r["a_n"]) <= int(r["b_n"]) else int(r["b_within"])
        if smaller and covered > 0.5 * smaller:
            violating.append((r["a_src"], r["b_src"]))
    return Measurement(
        check_id="GQ-11",
        offered=len(pairs),
        evaluated=len(pairs),
        measured=len(violating),
        detail={
            "violating_pairs": violating,
            "declared_lineage": "no lineage seam in schema — every overlap is undeclared (P35.25)",
        },
    )


def eval_gq13(ctx: EvalContext) -> Measurement:
    """GQ-13 — contradiction recall: current resolutions whose considered
    claims disagree (two or more distinct values) must be contested or carry
    dissent. (Distinct literal values is the documented seed approximation of
    'beyond the predicate tolerance'.)"""
    rows = _rows(
        ctx.conn,
        """
        SELECT r.resolution_id, r.contradiction_state,
               cardinality(r.dissenting_claims) AS dissent_n,
               count(DISTINCT coalesce(c.value_text, c.value_num::text)) AS distinct_vals
        FROM resolution r
        JOIN claim c ON c.claim_id = ANY(r.considered_claims)
        WHERE upper_inf(r.sys_period)
        GROUP BY r.resolution_id, r.contradiction_state, r.dissenting_claims
        """,
    )
    contested_population = [r for r in rows if int(r["distinct_vals"]) >= 2]
    violations = sum(
        1
        for r in contested_population
        if r["contradiction_state"] == "uncontested" and int(r["dissent_n"]) == 0
    )
    return Measurement(
        check_id="GQ-13",
        offered=len(rows),
        evaluated=len(contested_population),
        measured=violations,
        detail={
            "resolutions_with_disagreement": len(contested_population),
            "violations": violations,
            "approximation": "distinct literal values ≈ beyond predicate tolerance",
        },
    )


def eval_gq15(ctx: EvalContext) -> Measurement:
    """GQ-15 — published/live edges carry observed or valid time (or an
    explicit kind), none begin at the epoch, and no (from, to, kind) has live
    duplicates. 'Undated' = no observed_at AND a fully unbounded valid_period
    AND no explicit valid_from_kind beyond the 'unknown' default."""
    rows = _rows(
        ctx.conn,
        """
        SELECT relationship_id, from_entity, to_entity, edge_type,
               observed_at IS NOT NULL AS has_observed,
               (lower_inf(valid_period) AND upper_inf(valid_period)) AS undated,
               valid_from_kind,
               lower(valid_period) = '1970-01-01T00:00:00Z'::timestamptz AS epoch_start
        FROM relationship WHERE upper_inf(sys_period)
        """,
    )
    undated = epoch = 0
    groups: dict[tuple, int] = {}
    for r in rows:
        if r["undated"] and not r["has_observed"] and r["valid_from_kind"] == "unknown":
            undated += 1
        if r["epoch_start"]:
            epoch += 1
        key = (str(r["from_entity"]), str(r["to_entity"]), str(r["edge_type"]))
        groups[key] = groups.get(key, 0) + 1
    duplicates = sum(n - 1 for n in groups.values() if n > 1)
    violations = undated + epoch + duplicates
    return Measurement(
        check_id="GQ-15",
        offered=len(rows),
        evaluated=len(rows),
        measured=violations,
        detail={"undated": undated, "epoch_start": epoch, "duplicate_edges": duplicates},
    )


def eval_gq18(ctx: EvalContext) -> Measurement:
    """GQ-18 — per-source share of current claims bound to a byte-bearing
    capture with a locator; the metric is the worst source's share."""
    rows = _rows(
        ctx.conn,
        """
        WITH src AS (
          SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id
          FROM claim_evidence ce
          JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
          JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
          ORDER BY ce.claim_id, ec.retrieved_at
        )
        SELECT coalesce(s.source_id, '(unbound)') AS source_id,
               count(*) AS total,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM claim_evidence ce2
                   JOIN evidence_capture ec2 ON ec2.capture_id = ce2.capture_id
                   JOIN evidence_artifact ea2 ON ea2.artifact_id = ec2.artifact_id
                   WHERE ce2.claim_id = c.claim_id
                     AND ec2.byte_size > 0
                     AND ea2.stable_locator IS NOT NULL
               )) AS bound
        FROM claim c
        LEFT JOIN src s ON s.claim_id = c.claim_id
        WHERE upper_inf(c.sys_period)
        GROUP BY coalesce(s.source_id, '(unbound)')
        """,
    )
    per_source = {
        str(r["source_id"]): (int(r["bound"]) / int(r["total"]) if r["total"] else 0.0)
        for r in rows
    }
    return Measurement(
        check_id="GQ-18",
        offered=sum(int(r["total"]) for r in rows),
        evaluated=sum(int(r["total"]) for r in rows),
        measured=min(per_source.values()) if per_source else None,
        detail={"per_source_share": per_source, "metric": "worst-source share"},
    )


def eval_gq21(ctx: EvalContext) -> Measurement:
    """GQ-21 — accountability join rate: share of deployment entities with an
    operator claim (the procurement-buyer half joins when its surface lands)."""
    r = _rows(
        ctx.conn,
        """
        SELECT count(*) AS deployments,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM claim c
                   WHERE c.subject_id = e.entity_id
                     AND c.predicate_id = 'camera_operator'
                     AND upper_inf(c.sys_period)
               )) AS with_operator
        FROM entity e WHERE e.entity_type = 'deployment'
        """,
    )[0]
    total, bound = int(r["deployments"]), int(r["with_operator"])
    return Measurement(
        check_id="GQ-21",
        offered=total,
        evaluated=total,
        measured=(bound / total) if total else None,
        detail={"deployments_with_operator": bound},
    )


#: Inferential tiers whose auto-write is locked (GQ-24): tiers 3g (across
#: independent lineages), 4g and 5g outright, plus any 1g label that is not a
#: namespace join — ``1g:shared_upstream_ref`` IS the namespace variant (a
#: deterministic upstream-reference join, not identity inference) and stays
#: legal. New 1g labels fail closed into the locked set.
_NAMESPACE_1G_LABELS: frozenset[str] = frozenset({"1g:shared_upstream_ref"})
_INFERENTIAL_TIER_RE = re.compile(r"^[345]g:|^1g:")


def _is_inferential_tier(tier_label: str) -> bool:
    """A tier label naming an identity inference (never the namespace join)."""
    return bool(_INFERENTIAL_TIER_RE.match(tier_label)) and (tier_label not in _NAMESPACE_1G_LABELS)


def eval_gq24(ctx: EvalContext) -> Measurement:
    """GQ-24 — the inferential auto-write lock: auto-written same-device
    decisions in any identity-inference tier while no B5 evaluation certifies
    that tier.

    P34.45 scoping. The spine is append-only: a superseded run's auto_write
    rows can never be deleted, so the violation set is the LATEST completed
    execution's run — what a reader resolves today. Inferential auto_writes
    recorded under superseded runs are still *detected* and disclosed
    (``historical_inferential_auto_writes``), never silently excused. And a
    zero is never vacuous (SIG-ENG-042): with no completed execution or a
    latest run carrying no inferential-tier decisions the measurement reports
    ``evaluated=0`` and the ratchet's vacuous-pass guard fails it.
    """
    latest = _rows(
        ctx.conn,
        """
        SELECT run_key FROM camera_site_execution
        ORDER BY completed_at DESC, execution_id DESC LIMIT 1
        """,
    )
    latest_run = str(latest[0]["run_key"]) if latest else None
    rows = _rows(
        ctx.conn,
        """
        SELECT match_id, match_tier, tier_label, run_key
        FROM camera_site_match
        WHERE disposition = 'auto_write' AND decided_by = 'auto'
        """,
    )
    violations = sum(
        1
        for r in rows
        if latest_run is not None
        and str(r["run_key"]) == latest_run
        and _is_inferential_tier(str(r["tier_label"]))
    )
    historical = sum(
        1
        for r in rows
        if str(r["run_key"]) != latest_run and _is_inferential_tier(str(r["tier_label"]))
    )
    # The evaluated population is the latest run's inferential-tier decision
    # set — 0 violations over 0 inferential decisions is not a pass.
    inferential_decisions = (
        int(
            _rows(
                ctx.conn,
                """
                SELECT count(*) AS n FROM camera_site_match
                WHERE run_key = %s
                  AND (tier_label ~ '^[345]g:'
                       OR (tier_label ~ '^1g:' AND tier_label <> '1g:shared_upstream_ref'))
                """,
                (latest_run,),
            )[0]["n"]
        )
        if latest_run is not None
        else 0
    )
    return Measurement(
        check_id="GQ-24",
        offered=inferential_decisions,
        evaluated=inferential_decisions,
        measured=violations if inferential_decisions else None,
        detail={
            "latest_run_key": latest_run,
            "inferential_decisions_latest_run": inferential_decisions,
            "inferential_auto_writes_latest_run": violations,
            "historical_inferential_auto_writes": historical,
            "auto_write_total": len(rows),
        },
    )


# ---------------------------------------------------------------------------
# File-scan evaluators — the R/P placement halves of GQ-14 and GQ-27.

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _iter_site_rows(scan_dir: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    """Every sites/node row in the release dir (``<comp>/sites.jsonl`` plus any
    ``*nodes*.jsonl``/``*network*.jsonl`` artifact)."""
    for path in sorted(scan_dir.rglob("*.jsonl")):
        if path.name not in ("sites.jsonl",) and not (
            "node" in path.name or "network" in path.name or "edge" in path.name
        ):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "entity_id" in row:
                yield path, row


def eval_gq14(ctx: EvalContext) -> Measurement:
    """GQ-14 — no published node/site is labelled by its UUID, and no site
    ships unlabeled (the ≤ 5 % tolerance half rides the check's threshold)."""
    if ctx.scan_dir is None:
        return _not_evaluable("GQ-14", "no scan dir — the R placement needs a release dir")
    offered = violations = uuid_labels = unlabeled = 0
    seen_any = False
    for _path, row in _iter_site_rows(ctx.scan_dir):
        seen_any = True
        offered += 1
        label = str(row.get("label") or "").strip()
        if _UUID_RE.match(label):
            uuid_labels += 1
            violations += 1
        elif not label:
            unlabeled += 1
            violations += 1
    if not seen_any:
        return _not_evaluable("GQ-14", f"no sites/nodes artifacts under {ctx.scan_dir}")
    return Measurement(
        check_id="GQ-14",
        offered=offered,
        evaluated=offered,
        measured=violations,
        detail={"uuid_labels": uuid_labels, "unlabeled": unlabeled},
    )


#: Claim-marker phrases GQ-27 gates on — a B5-word is a published claim of
#: human verification and is legal only next to a B5 completion marker
#: (P34.45 adds bare "verified" to the L3 list).
_CLAIM_PHRASES = ("human-verified", "independently reviewed", "verified", "certified")
_CLAIM_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, _CLAIM_PHRASES)) + r")\b")

#: The context a published quality figure's statement must carry (the GQ-27
#: statement): its n, population, source-mix digest, ruleset and window. Each
#: field may live on the figure object or be inherited from an enclosing
#: object in the same document (a report-level ruleset/window applies to the
#: figures it wraps) — except ``n``, which is the figure's own denominator
#: and is never inherited. Aliases cover the shapes our own report records
#: emit (evaluation rows, probe reports, dossier stats).
_FIGURE_CONTEXT: dict[str, tuple[str, ...]] = {
    "n": ("n", "denominator", "drawn", "sample_n", "offered"),
    "population": ("population", "population_note", "target_population", "frame_population"),
    "source_mix_digest": (
        "source_mix_digest",
        "provenance_digest",
        "provenance_counts",
        "source_mix",
    ),
    "ruleset": (
        "ruleset",
        "ruleset_digest",
        "ruleset_version",
        "rules_version",
        "design_digest",
    ),
    "window": ("window", "as_of", "sys_period", "scope", "completed_at"),
}
_FIGURE_KEYS = {"measured", "value", "precision", "recall", "f1"}
_BASIS_KEYS = ("basis_class", "basis")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _scan_quality_figures(
    obj: Any, path: Path, hits: list[str], ctx: Mapping[str, str] | None = None
) -> None:
    """Walk a JSON tree: every object that publishes a quality/evaluation
    figure (a numeric value under a metric-ish key) must name exactly one
    basis class and carry the figure context (n, population, source-mix
    digest, ruleset, window — on the figure or inherited); claim phrases need
    a B5 marker in the same object."""
    scope = dict(ctx or {})
    if isinstance(obj, dict):
        # context fields this object contributes to the figures inside it
        for field, aliases in _FIGURE_CONTEXT.items():
            if field == "n" or field in scope:
                continue  # n is per-figure; an ancestor's n is not this figure's
            for a in aliases:
                if a in obj and obj[a] not in (None, "", [], {}):
                    scope.setdefault(field, a)
                    break
        if "basis" not in scope:
            for k in _BASIS_KEYS:
                if str(obj.get(k) or "").strip():
                    scope["basis"] = k
                    break
        text = " ".join(str(v) for v in obj.values() if isinstance(v, str))
        basis = str(obj.get("basis_class") or obj.get("basis") or "")
        if _CLAIM_RE.search(text) and "B5" not in basis:
            hits.append(f"{path}: claim phrase without a B5 marker")
        if any(_is_number(obj.get(k)) for k in _FIGURE_KEYS):
            basis_values = {
                str(obj[k]).strip() for k in _BASIS_KEYS if str(obj.get(k) or "").strip()
            }
            if len(basis_values) > 1:
                hits.append(f"{path}: quality figure names more than one basis class")
            elif not basis_values and "basis" not in scope:
                hits.append(f"{path}: quality figure without a basis class")
            own_scope = dict(scope)
            for a in _FIGURE_CONTEXT["n"]:
                if a in obj and obj[a] not in (None, "", [], {}):
                    own_scope["n"] = a
                    break
            missing = sorted(f for f in _FIGURE_CONTEXT if f not in own_scope)
            if missing:
                hits.append(f"{path}: quality figure missing context {missing}")
        for v in obj.values():
            _scan_quality_figures(v, path, hits, scope)
    elif isinstance(obj, list):
        for v in obj:
            _scan_quality_figures(v, path, hits, ctx)


def eval_gq27(ctx: EvalContext) -> Measurement:
    """GQ-27 — the basis-label/claim-marker rule over build output: JSON
    records and prose under the scan dir. (B4 G10's own disposition is the
    human gate's; this is the mechanical scan it consumes.)"""
    if ctx.scan_dir is None:
        return _not_evaluable("GQ-27", "no scan dir — the P/R placement needs build output")
    hits: list[str] = []
    scanned = 0
    for path in sorted(ctx.scan_dir.rglob("*")):
        if path.suffix == ".json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            scanned += 1
            _scan_quality_figures(doc, path, hits)
        elif path.suffix in (".md", ".txt", ".html"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            scanned += 1
            for m in _CLAIM_RE.finditer(text):
                if "B5" not in text:
                    hits.append(f"{path}: '{m.group(0)}' without a B5 marker")
    if scanned == 0:
        return _not_evaluable("GQ-27", f"nothing to scan under {ctx.scan_dir}")
    return Measurement(
        check_id="GQ-27",
        offered=scanned,
        evaluated=scanned,
        measured=len(hits),
        detail={"violations": hits[:50], "violation_count": len(hits)},
    )


# ---------------------------------------------------------------------------
# The evaluator table + the runner

#: Checks whose seams do not exist yet — registered, honestly reported as
#: not_evaluable with the seam's owner named (never silently skipped).
SEAM_DEFERRALS: dict[str, str] = {
    "GQ-02": "replay determinism needs the capture-replay seam (P35.22)",
    "GQ-06": "the subject/entity typing census lands with PKG-11/PKG-07 (P35.14/P35.15)",
    "GQ-08": "the R placement consumes the release-verify V9 point checks "
    "(REL-04b / P35.58, after PKG-06b)",
    "GQ-09": "the dossier-key scheme split lands with PKG-06a (P35.17/P35.18)",
    "GQ-10": "duplicate accounting rides V15 (P35.58; PKG-c2 P35.47)",
    "GQ-12": "the lineage/independence-class seam lands with CONF-04 (P35.25)",
    "GQ-16": "the one-resolved join consumes the V6 coverage check (P35.20a/b)",
    "GQ-17": "the R placement consumes the V8 attribution check (P34.21a/b)",
    "GQ-19": "upstream-count run telemetry lands with PKG-12/TX-04 (P35.32/P35.34)",
    "GQ-20": "the release diff consumes the V14 diff (P35.58)",
    "GQ-23": "collapse tiers do not exist yet (CONF-07a / P35.46)",
    "GQ-25": "collapse/cluster comparisons need CONF-07a (P35.46)",
    "GQ-26": "ER metamorphic re-runs ride the regression corpus (P35.23)",
}

#: The implemented evaluators, keyed by the placements they serve. A check's
#: other placements (I sink hooks, V*-consumed R gates, S scheduled probes)
#: are named by the registry; the runner evaluates the placements that read
#: the spine or a scan dir.
SPINE_EVALUATORS: dict[str, Evaluator] = {
    "GQ-03": eval_gq03,
    "GQ-05": eval_gq05,
    "GQ-07": eval_gq07,
    "GQ-11": eval_gq11,
    "GQ-13": eval_gq13,
    "GQ-15": eval_gq15,
    "GQ-18": eval_gq18,
    "GQ-21": eval_gq21,
    "GQ-24": eval_gq24,
}

FILE_EVALUATORS: dict[str, Evaluator] = {
    "GQ-14": eval_gq14,
    "GQ-27": eval_gq27,
}


def select_evaluators(check: QualityCheck, placement: str) -> Evaluator | None:
    """The evaluator a check runs under this placement — or None when the
    placement is not probe-evaluated (I-placement sink hooks are the ingest
    pipeline's, not this runner's)."""
    if check.check_id in FILE_EVALUATORS and placement in check.placement:
        return FILE_EVALUATORS[check.check_id]
    if check.check_id in SPINE_EVALUATORS and placement in check.placement:
        return SPINE_EVALUATORS[check.check_id]
    return None


def run_quality_probe(
    ctx: EvalContext,
    *,
    placement: str = "M",
    target: str = "spine",
    registry: CheckRegistry | None = None,
    generated_at: Any = None,
) -> dict[str, Any]:
    """Evaluate every registry check the placement selects and return the
    ``sig.quality-report/1`` record. Read-only end to end: the caller owns the
    connection and opens it read-only (see ``connect_readonly``); a check with
    no implemented evaluator records ``not_evaluable`` naming its seam."""
    reg = registry or load_registry()
    outcomes = []
    for check in reg.checks:
        evaluator = select_evaluators(check, placement)
        if placement not in check.placement:
            continue  # the placement doesn't run this check
        if check.check_id in SEAM_DEFERRALS:
            m = _not_evaluable(check.check_id, SEAM_DEFERRALS[check.check_id])
        elif evaluator is None:
            m = _not_evaluable(
                check.check_id,
                f"no evaluator for placement {placement} — "
                f"lands with {', '.join(check.fixing) or 'the check owner'}",
            )
        elif check.check_id in SPINE_EVALUATORS and ctx.conn is None:
            m = _not_evaluable(check.check_id, "no spine connection")
        elif check.check_id in FILE_EVALUATORS and ctx.scan_dir is None:
            m = _not_evaluable(check.check_id, "no scan dir")
        else:
            m = evaluator(ctx)
        outcomes.append(evaluate_check(check, m))
    return build_quality_report(
        reg,
        outcomes,
        placement=placement,
        target=target,
        generated_at=generated_at,
    )


def probe_run_record(report: dict[str, Any]) -> dict[str, Any]:
    """The ``sig.probe-run/1`` envelope for a quality report."""
    return build_probe_run(report)


def connect_readonly(dsn: str) -> Any:
    """Open a spine connection in the audit posture (SIG-CONF-008): read-only
    transactions, a 60 s statement timeout — the same session shape the
    ``sig_audit`` login enforces server-side."""
    import psycopg

    conn = psycopg.connect(
        dsn,
        autocommit=True,
        options="-c default_transaction_read_only=on -c statement_timeout=60000",
    )
    conn.execute("SET default_transaction_read_only = on")
    conn.execute("SET statement_timeout = '60s'")
    return conn


def write_records(report: dict[str, Any], out: Path) -> dict[str, str]:
    """Write ``quality-report.json`` + ``probe-run.json`` under ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "quality-report.json"
    probe_path = out / "probe-run.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    probe_path.write_text(json.dumps(probe_run_record(report), indent=2, sort_keys=True) + "\n")
    return {"report": str(report_path), "probe_run": str(probe_path)}


# ---------------------------------------------------------------------------
# The P34.44b run surface — the nightly probe job, its records, and the
# L2 baseline leg (SIG-CONF-006/007/009, ADR-154/205).

#: The restricted-bucket prefix each nightly run's two records land under —
#: inside the conditioned ``ops/probes/`` objectCreator scope the job's
#: identity holds (ops/iam_identities.toml).
PROBE_PREFIX_DEFAULT = "ops/probes/quality/"

#: The baseline leg's records — the same conditioned scope.
BASELINE_PREFIX_DEFAULT = "ops/probes/quality-baseline/"

#: The alert kind stamped on a nightly run's recorded alert (ADR-077's
#: ledger + the sig-alerts channel, P34.4 / SIG-OPS-006).
QUALITY_ALERT_KIND = "quality-probe"

#: The fetch caps on ``baseline --release-prefix``: the current release's
#: public objects, bounded — a runaway listing never becomes an unbounded
#: download.
RELEASE_MAX_OBJECTS = 2000
RELEASE_MAX_BYTES = 64 * 2**20


def _object_stamp(generated_at: str) -> str:
    """``2026-01-02T03:04:05Z`` → the object-name-safe ``2026-01-02/2026-01-02T03-04-05Z``."""
    return f"{generated_at[:10]}/{generated_at.replace(':', '-')}"


def suppressed_probe_record(
    *, reason: str, generated_at: str, job: str = "", target: str = "hosted-spine"
) -> dict[str, Any]:
    """A suppressed run's ``sig.probe-run/1`` — the window guard fired before
    any connection opened (the contract's off-peak/batch-window promise is
    itself part of the recorded evidence)."""
    return {
        "version": "sig.probe-run/1",
        "generated_at": generated_at,
        "probe": "sig-quality",
        "placement": "M",
        "target": target,
        "job": job,
        "suppressed": reason,
        "checks": [],
        "overall": "suppressed",
    }


def error_probe_record(
    *, reason: str, generated_at: str, job: str = "", target: str = "hosted-spine"
) -> dict[str, Any]:
    """A failed run's ``sig.probe-run/1`` — the run could not produce a
    report (a refused connection, a fetch failure); the record still lands
    so a missing record is never mistaken for a pass."""
    return {
        "version": "sig.probe-run/1",
        "generated_at": generated_at,
        "probe": "sig-quality",
        "placement": "M",
        "target": target,
        "job": job,
        "checks": [{"name": "run", "outcome": "fail", "reason": reason}],
        "overall": "fail",
        "error": reason,
    }


def upload_records(bucket: Any, prefix: str, report: dict[str, Any]) -> dict[str, str]:
    """Write a run's two records as NEW timestamped objects under ``prefix``
    (WORM-shaped — never rewritten). ``bucket`` is a ``GcsBucket``-shaped
    object (injectable in tests)."""
    stamp = _object_stamp(str(report["generated_at"]))
    names = {
        "report": f"{prefix}{stamp}-quality-report.json",
        "probe_run": f"{prefix}{stamp}-probe-run.json",
    }
    bucket.put_object(
        names["report"],
        (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        content_type="application/json",
    )
    bucket.put_object(
        names["probe_run"],
        (json.dumps(probe_run_record(report), indent=2, sort_keys=True) + "\n").encode("utf-8"),
        content_type="application/json",
    )
    return names


def upload_probe_record(bucket: Any, prefix: str, record: dict[str, Any]) -> str:
    """Write a suppressed/error ``sig.probe-run/1`` as a new object."""
    name = f"{prefix}{_object_stamp(str(record['generated_at']))}-probe-run.json"
    bucket.put_object(
        name,
        (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        content_type="application/json",
    )
    return name


def nightly_dsn(env: dict[str, str]) -> str:
    """The spine conninfo for the in-container run: the explicit DSN env
    wins, else the Cloud SQL socket + the mounted ``sig_audit`` credential.
    Empty when neither is available — the caller then runs file checks only
    (spine checks report ``not_evaluable``, never a pass)."""
    explicit = (env.get("SIG_QUALITY_DSN") or env.get("SIG_DB_DSN") or "").strip()
    if explicit:
        return explicit
    conn = env.get("SIG_CLOUDSQL_CONNECTION", "").strip()
    password = env.get("SIG_AUDIT_PASSWORD", "")
    if not conn or not password:
        return ""
    db = env.get("SIG_PG_DB", "sig").strip() or "sig"
    return f"host=/cloudsql/{conn} dbname={db} user=sig_audit password={password}"


def fetch_release(
    bucket: Any,
    prefix: str,
    dest: Path,
    *,
    max_objects: int = RELEASE_MAX_OBJECTS,
    max_bytes: int = RELEASE_MAX_BYTES,
) -> dict[str, Any]:
    """Fetch the public release's objects under ``prefix`` into ``dest`` —
    read-only, bounded, deterministic order. ``bucket`` is a
    ``GcsBucket``-shaped object (injectable). Returns the fetch accounting
    the baseline record carries."""
    names = sorted(bucket.list_objects(prefix))
    written = 0
    total = 0
    truncated = len(names) > max_objects
    for name in names[:max_objects]:
        rel = name[len(prefix) :] if name.startswith(prefix) else name
        if not rel or rel.endswith("/") or ".." in rel.split("/"):
            continue
        body = bucket.get_object(name)
        if total + len(body) > max_bytes:
            truncated = True
            break
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        written += 1
        total += len(body)
    return {
        "objects_seen": len(names),
        "objects_written": written,
        "bytes": total,
        "truncated": truncated,
    }


def _fire_quality_alert(
    message: str,
    *,
    detail: dict[str, Any] | None = None,
    severity: str = "critical",
    kind: str = QUALITY_ALERT_KIND,
    ledger: Any = None,
    notifiers: Any = None,
) -> Any:
    """Record the alert, then fan out to every configured sink — the record
    never depends on delivery (ADR-077; P34.4's channel)."""
    from .alerts import Alert, AlertLedger, fire, notifiers_from_env

    alert = Alert.create(kind, severity, message, detail=detail)
    if ledger is None:
        ledger = AlertLedger(Path(os.environ.get("SIG_ALERT_LOG", ".sig/ops/alerts.jsonl")))
    if notifiers is None:
        notifiers = notifiers_from_env()
    fire(alert, ledger=ledger, notifiers=notifiers)
    return alert


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    """``gs://<bucket>/<prefix>/`` → (bucket, prefix); anything else refuses."""
    m = re.match(r"^gs://([a-z0-9._-]+)/(.+)$", uri.strip())
    if not m:
        raise ValueError(f"release prefix {uri!r} must be a gs://<bucket>/<prefix>/ URI")
    return m.group(1), m.group(2)


def _iso_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    """``sig-ops quality`` — the P34.44a/b harness surface (offline/read-only)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops quality",
        description=(
            "P34.44a/b (SIG-CONF-006/007/008/013): run the read-only quality "
            "probe for a placement and emit sig.quality-report/1 + "
            "sig.probe-run/1 records. DB checks run under a read-only "
            "session; file checks scan a release/build dir. `nightly` is the "
            "sig-quality-probe job's in-container command (window-suppressed, "
            "record-emitting, alerting); `baseline` is the L2 reproduction "
            "leg; `job` renders the ops/quality_probe.toml declaration."
        ),
    )
    sub = parser.add_subparsers(dest="quality_command", required=True)
    p_run = sub.add_parser("run", help="evaluate the registry checks selected by a placement")
    p_run.add_argument(
        "--placement",
        default="M",
        choices=sorted("IMRPS"),
        help="I ingest/sink · M nightly spine probe · R release gate · "
        "P pull request · S scheduled public probe (default M)",
    )
    p_run.add_argument(
        "--dsn",
        default=os.environ.get("SIG_DB_DSN", ""),
        help="PostgreSQL DSN — opened read-only; empty skips spine checks "
        "(they report not_evaluable, never a pass)",
    )
    p_run.add_argument(
        "--scan-dir",
        default=None,
        help="release/build dir for the file-scan checks (GQ-14, GQ-27)",
    )
    p_run.add_argument(
        "--sample-percent",
        type=float,
        default=None,
        help="TABLESAMPLE percent for the B2 heavy checks (recorded)",
    )
    p_run.add_argument("--seed", type=int, default=42, help="the REPEATABLE seed")
    p_run.add_argument("--target", default="spine", help="what was measured")
    p_run.add_argument(
        "--out",
        default=None,
        help="write quality-report.json + probe-run.json under this dir",
    )
    p_run.add_argument("--emit", action="store_true", help="print both records as JSON")
    p_gate = sub.add_parser(
        "gate",
        help="the release-V15 hook (SIG-CONF-007): consume a "
        "sig.quality-report/1 and emit the gate verdict — standalone now, "
        "joins the V15 suite with P35.58",
    )
    p_gate.add_argument("--report", required=True, help="a quality-report JSON")

    # --- P34.44b: the nightly job's in-container verb ---------------------
    p_nightly = sub.add_parser(
        "nightly",
        help="the sig-quality-probe job's command (P34.44b): suppress inside "
        "the contract's windows, run the M placement read-only, write both "
        "records under the restricted prefix, alert on failure",
    )
    p_nightly.add_argument(
        "--dsn",
        default=None,
        help="PostgreSQL DSN (default: SIG_QUALITY_DSN / SIG_DB_DSN, else the "
        "Cloud SQL socket + SIG_AUDIT_PASSWORD)",
    )
    p_nightly.add_argument("--scan-dir", default=None, help="file checks' scan dir")
    p_nightly.add_argument("--target", default="hosted-spine", help="what was measured (recorded)")
    p_nightly.add_argument(
        "--bucket",
        default=os.environ.get("SIG_OPS_GCS_BUCKET", ""),
        help="restricted bucket the records upload to (default: SIG_OPS_GCS_BUCKET; "
        "empty = local only)",
    )
    p_nightly.add_argument(
        "--prefix",
        default=os.environ.get("SIG_QUALITY_PROBE_PREFIX", PROBE_PREFIX_DEFAULT),
        help="bucket-relative record prefix (default: SIG_QUALITY_PROBE_PREFIX)",
    )
    p_nightly.add_argument(
        "--job-name",
        default=os.environ.get("SIG_QUALITY_JOB_NAME", "sig-quality-probe"),
        help="the job name stamped on the records",
    )
    p_nightly.add_argument("--out", default=None, help="local dir for the records")
    p_nightly.add_argument("--emit", action="store_true", help="print the probe-run JSON")
    p_nightly.add_argument(
        "--no-alert",
        action="store_true",
        help="record only — never fire the alert channel",
    )
    p_nightly.add_argument(
        "--now",
        default=None,
        help="ISO-UTC timestamp for the window guard (default: now — the test "
        "hook only; a live run always reads the clock)",
    )
    p_nightly.add_argument("--sample-percent", type=float, default=None)
    p_nightly.add_argument("--seed", type=int, default=42)

    # --- P34.44b: the L2 baseline leg --------------------------------------
    p_base = sub.add_parser(
        "baseline",
        help="the L2 baseline run (P34.44b): every M + R check once over the "
        "hosted spine + the current public release files, emitting the "
        "sig.quality-baseline/1 record + the ratchet-baseline proposal",
    )
    p_base.add_argument("--dsn", default=None, help="PostgreSQL DSN (as nightly)")
    p_base.add_argument("--scan-dir", default=None, help="staged release files")
    p_base.add_argument(
        "--release-prefix",
        default=os.environ.get("SIG_BASELINE_RELEASE_PREFIX", ""),
        help="gs://<bucket>/<prefix>/ the current public release's objects "
        "live under — fetched read-only + bounded (SIG_BASELINE_RELEASE_PREFIX)",
    )
    p_base.add_argument(
        "--fetch-dir",
        default=None,
        help="where --release-prefix objects are staged (default: <out>/release-scan)",
    )
    p_base.add_argument("--target", default="hosted-spine", help="what was measured (recorded)")
    p_base.add_argument("--run-id", default=None, help="the run id (default: baseline-<stamp>)")
    p_base.add_argument(
        "--out",
        default=None,
        help="dir for the baseline record + the two reports (required for a "
        "local run; the leg then commits the counts summary)",
    )
    p_base.add_argument(
        "--bucket",
        default=os.environ.get("SIG_OPS_GCS_BUCKET", ""),
        help="restricted bucket the baseline record uploads to (default: "
        "SIG_OPS_GCS_BUCKET; empty = local only)",
    )
    p_base.add_argument(
        "--prefix",
        default=os.environ.get("SIG_BASELINE_PREFIX", BASELINE_PREFIX_DEFAULT),
        help="bucket-relative record prefix",
    )
    p_base.add_argument("--emit", action="store_true", help="print the baseline JSON")
    p_base.add_argument("--sample-percent", type=float, default=None)
    p_base.add_argument("--seed", type=int, default=42)

    # --- P34.44b: the job declaration surface ------------------------------
    p_job = sub.add_parser(
        "job",
        help="the sig-quality-probe declaration surface (P34.44b): plan, "
        "render, verify-describe, verify-trigger, window — offline verbs "
        "ops/gcp/quality-probe.sh drives",
    )
    job_sub = p_job.add_subparsers(dest="job_command", required=True)
    p_jp = job_sub.add_parser("plan", help="print the validated declaration (offline)")
    p_jp.add_argument("--declaration", default=None)
    p_jr = job_sub.add_parser("render", help="render the whole mutation set as argv JSON (offline)")
    p_jr.add_argument("--declaration", default=None)
    p_jr.add_argument("--image", required=True, help="digest-pinned image ref")
    p_jr.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", "<SIG_GCP_PROJECT>"))
    p_jr.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_jr.add_argument(
        "--env",
        dest="env_pairs",
        action="append",
        default=[],
        help="NAME=value for a declared plain env var (repeatable)",
    )
    p_jd = job_sub.add_parser(
        "verify-describe",
        help="judge a recorded `run jobs describe --format=json`",
    )
    p_jd.add_argument("--declaration", default=None)
    p_jd.add_argument("--describe", required=True)
    p_jd.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt = job_sub.add_parser(
        "verify-trigger",
        help="judge a recorded `scheduler jobs describe --format=json`",
    )
    p_jt.add_argument("--declaration", default=None)
    p_jt.add_argument("--describe", required=True)
    p_jt.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_jw = job_sub.add_parser(
        "window",
        help="the leg's clock guard: exit 0 when the window is open, 42 when "
        "queued (before-earliest / quiet band / batch window)",
    )
    p_jw.add_argument("--earliest", default="", help="ISO-UTC lower bound")
    p_jw.add_argument("--now", default=None, help="ISO-UTC (default: now)")

    args = parser.parse_args(argv)
    if args.quality_command == "gate":
        from exports.quality import run_release_gate

        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        try:
            verdict = run_release_gate(report)
        except Exception as e:  # noqa: BLE001 — refuse loudly, never silent
            print(f"sig-ops quality gate: refused — {e}", file=sys.stderr)
            return 4
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict["verdict"] == "pass" else 4
    if args.quality_command == "run":
        conn = None
        if args.dsn:
            conn = connect_readonly(args.dsn)
        ctx = EvalContext(
            conn=conn,
            scan_dir=Path(args.scan_dir) if args.scan_dir else None,
            sample_percent=args.sample_percent,
            sample_seed=args.seed,
        )
        report = run_quality_probe(ctx, placement=args.placement, target=args.target)
        if args.out:
            paths = write_records(report, Path(args.out))
            print(f"wrote {paths['report']} + {paths['probe_run']}")
        if args.emit:
            print(json.dumps(probe_run_record(report), indent=2, sort_keys=True))
        summary = report["summary"]
        print(
            f"sig-ops quality: {args.placement} → {summary['overall']} "
            f"({report['totals']['evaluated']}/{report['totals']['offered']} "
            f"evaluated; enforce failures {summary['enforce_failures']}; "
            f"regressions {summary['ratchet_regressions']}; "
            f"not_evaluable {summary['not_evaluable']})",
            file=sys.stderr,
        )
        if conn is not None:
            conn.close()
        if summary["overall"] == "fail":
            return 4
        if summary["overall"] == "partial":
            return 3
        return 0

    if args.quality_command == "nightly":
        from datetime import UTC, datetime

        from .quality_job import suppression_reason

        now = datetime.now(UTC)
        if args.now:
            now = datetime.fromisoformat(str(args.now).replace("Z", "+00:00")).astimezone(UTC)
        generated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        reason = suppression_reason(now)
        if reason is not None:
            # The window contract is enforced in-container too: a run inside
            # the quiet band or the batch window records `suppressed` and
            # exits 0 — never a probe, never a silent no-op.
            record = suppressed_probe_record(
                reason=reason,
                generated_at=generated,
                job=args.job_name,
                target=args.target,
            )
            if args.bucket:
                from .gcs import GcsBucket

                name = upload_probe_record(GcsBucket(args.bucket), args.prefix, record)
                print(
                    f"sig-quality-probe suppressed ({reason}): gs://{args.bucket}/{name}",
                    file=sys.stderr,
                )
            else:
                print(f"sig-quality-probe suppressed ({reason})", file=sys.stderr)
            if args.out:
                out = Path(args.out)
                out.mkdir(parents=True, exist_ok=True)
                (out / "probe-run.json").write_text(
                    json.dumps(record, indent=2, sort_keys=True) + "\n"
                )
            if args.emit:
                print(json.dumps(record, indent=2, sort_keys=True))
            return 0
        try:
            env = dict(os.environ)
            dsn = args.dsn if args.dsn is not None else nightly_dsn(env)
            conn = connect_readonly(dsn) if dsn else None
            ctx = EvalContext(
                conn=conn,
                scan_dir=Path(args.scan_dir) if args.scan_dir else None,
                sample_percent=args.sample_percent,
                sample_seed=args.seed,
            )
            report = run_quality_probe(ctx, placement="M", target=args.target)
            report["job"] = args.job_name
            if conn is not None:
                conn.close()
        except Exception as e:  # noqa: BLE001 — a failed run is recorded, never silent
            from .alerts import scrub_secrets

            reason = scrub_secrets(str(e))  # never a secret value in the record
            record = error_probe_record(
                reason=reason,
                generated_at=generated,
                job=args.job_name,
                target=args.target,
            )
            if args.bucket:
                try:
                    from .gcs import GcsBucket

                    upload_probe_record(GcsBucket(args.bucket), args.prefix, record)
                except Exception as up:  # noqa: BLE001 — surfaced, still alerts
                    print(f"record upload failed after the run failed: {up}", file=sys.stderr)
            print(f"sig-quality-probe run failed: {reason}", file=sys.stderr)
            if not args.no_alert:
                fired = _fire_quality_alert(
                    f"sig-quality-probe {args.target}: run failed — {reason}",
                    detail={"target": args.target, "job": args.job_name, "error": reason},
                )
                from .alerts import alert_exit_code

                return alert_exit_code(fired)
            return 4
        # A completed run: write both records, then the verdict decides.
        if args.bucket:
            from .gcs import GcsBucket

            names = upload_records(GcsBucket(args.bucket), args.prefix, report)
            print(f"records → gs://{args.bucket}/{names['report']}", file=sys.stderr)
        if args.out:
            paths = write_records(report, Path(args.out))
            print(f"wrote {paths['report']} + {paths['probe_run']}", file=sys.stderr)
        if args.emit:
            print(json.dumps(probe_run_record(report), indent=2, sort_keys=True))
        summary = report["summary"]
        print(
            f"sig-quality-probe: M → {summary['overall']} "
            f"(enforce failures {summary['enforce_failures']}; "
            f"ratchet regressions {summary['ratchet_regressions']}; "
            f"not_evaluable {summary['not_evaluable']})",
            file=sys.stderr,
        )
        if summary["overall"] == "fail" and not args.no_alert:
            fired = _fire_quality_alert(
                f"sig-quality-probe {args.target}: {summary['overall']} — "
                f"enforce failures {summary['enforce_failures']}, "
                f"ratchet regressions {summary['ratchet_regressions']}",
                detail={
                    "target": args.target,
                    "job": args.job_name,
                    "summary": summary,
                },
            )
            from .alerts import alert_exit_code

            return alert_exit_code(fired)
        if summary["class_s_trigger"] and summary["overall"] != "fail" and not args.no_alert:
            # The engine's alert band breached on an otherwise-clean run —
            # a recorded "alarm" the operator sees (the class-S trigger is the
            # registry's own alert semantics, never paged critical).
            _fire_quality_alert(
                f"sig-quality-probe {args.target}: alert band breach "
                f"(overall {summary['overall']})",
                detail={
                    "target": args.target,
                    "job": args.job_name,
                    "summary": summary,
                },
                severity="alarm",
            )
        if summary["overall"] == "fail":
            return 4
        if summary["overall"] == "partial":
            return 3
        return 0

    if args.quality_command == "baseline":
        import tempfile

        from exports.quality import build_baseline_record

        generated = _iso_now()
        run_id = args.run_id or f"baseline-{generated}"
        env = dict(os.environ)
        dsn = args.dsn if args.dsn is not None else nightly_dsn(env)
        out_dir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="sig-baseline-"))
        out_dir.mkdir(parents=True, exist_ok=True)
        scan_dir = Path(args.scan_dir) if args.scan_dir else None
        fetch: dict[str, Any] | None = None
        if scan_dir is None and args.release_prefix:
            bucket_name, rel_prefix = _parse_gs_uri(args.release_prefix)
            dest = Path(args.fetch_dir) if args.fetch_dir else out_dir / "release-scan"
            from .gcs import GcsBucket

            fetch = fetch_release(GcsBucket(bucket_name), rel_prefix, dest)
            scan_dir = dest
            print(
                f"release fetch: {fetch['objects_written']}/"
                f"{fetch['objects_seen']} objects ({fetch['bytes']} bytes"
                f"{' — TRUNCATED at the caps' if fetch['truncated'] else ''})",
                file=sys.stderr,
            )
        conn = connect_readonly(dsn) if dsn else None
        ctx = EvalContext(
            conn=conn,
            scan_dir=scan_dir,
            sample_percent=args.sample_percent,
            sample_seed=args.seed,
        )
        reg = load_registry()
        report_m = run_quality_probe(ctx, placement="M", target=args.target, registry=reg)
        report_r = run_quality_probe(ctx, placement="R", target=args.target, registry=reg)
        if conn is not None:
            conn.close()
        record = build_baseline_record(
            registry=reg,
            reports={"M": report_m, "R": report_r},
            target=args.target,
            run_id=run_id,
            fetch=fetch,
        )
        record_path = out_dir / "quality-baseline.json"
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        (out_dir / "quality-report-M.json").write_text(
            json.dumps(report_m, indent=2, sort_keys=True) + "\n"
        )
        (out_dir / "quality-report-R.json").write_text(
            json.dumps(report_r, indent=2, sort_keys=True) + "\n"
        )
        print(f"wrote {record_path} (+ quality-report-M/R.json)", file=sys.stderr)
        if args.bucket:
            from .gcs import GcsBucket

            stamp = _object_stamp(generated)
            name = f"{args.prefix}{stamp}-baseline.json"
            GcsBucket(args.bucket).put_object(
                name,
                (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                content_type="application/json",
            )
            print(f"baseline record → gs://{args.bucket}/{name}", file=sys.stderr)
        if args.emit:
            print(json.dumps(record, indent=2, sort_keys=True))
        counts = record["counts"]
        print(
            f"quality baseline {run_id}: {counts['measured']}/{counts['ratchet_checks']} "
            f"ratchet checks measured; {counts['baselined']} pending→baselined, "
            f"{counts['tightened']} tightened, {counts['regressions']} regressions, "
            f"{counts['findings']} findings",
            file=sys.stderr,
        )
        # The leg's follow-up: `sig-exports quality apply-baselines --report
        # <this record>` rewrites the registry from the proposal (the ratchet
        # diff re-checks the result — a loosening cannot be written).
        return 0 if counts["measured"] > 0 else 3

    if args.quality_command == "job":
        from . import quality_job as qj

        try:
            decl = qj.load_declaration(getattr(args, "declaration", None))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if args.job_command == "plan":
            import dataclasses

            print(
                json.dumps(
                    {"schema": qj.SCHEMA, **dataclasses.asdict(decl)},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.job_command == "render":
            env_values: dict[str, str] = {}
            for pair in args.env_pairs:
                if "=" not in pair:
                    print(f"job render: --env {pair!r} must be NAME=value", file=sys.stderr)
                    return 2
                k, v = pair.split("=", 1)
                env_values[k] = v
            try:
                plan = qj.render(
                    decl,
                    project=args.project,
                    region=args.region,
                    image=args.image,
                    env_values=env_values,
                )
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 2
            print(json.dumps(plan, indent=2, sort_keys=True))
            return 0
        if args.job_command == "verify-describe":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = qj.verify_describe(decl, describe, project=args.project)
            if diffs:
                for d in diffs:
                    print(f"DRIFT: {d}", file=sys.stderr)
                return 4
            print("verify-describe OK — the job posture matches the declaration")
            return 0
        if args.job_command == "verify-trigger":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = qj.verify_trigger(decl, describe, project=args.project, region=args.region)
            if diffs:
                for d in diffs:
                    print(f"DRIFT: {d}", file=sys.stderr)
                return 4
            print("verify-trigger OK — the trigger matches the declaration")
            return 0
        if args.job_command == "window":
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            if args.now:
                now = datetime.fromisoformat(str(args.now).replace("Z", "+00:00")).astimezone(UTC)
            reason = qj.leg_window_reason(now, earliest=args.earliest)
            if reason is not None:
                print(f"QUEUED ({reason}): the leg runs inside its contract window only")
                return 42
            print("window open")
            return 0
        return 2
    return 2


__all__ = [
    "BASELINE_PREFIX_DEFAULT",
    "PROBE_PREFIX_DEFAULT",
    "QUALITY_ALERT_KIND",
    "EvalContext",
    "Evaluator",
    "FILE_EVALUATORS",
    "PUBLISHER_BLOCKLIST",
    "SEAM_DEFERRALS",
    "SPINE_EVALUATORS",
    "connect_readonly",
    "error_probe_record",
    "fetch_release",
    "nightly_dsn",
    "probe_run_record",
    "run_quality_probe",
    "suppressed_probe_record",
    "upload_probe_record",
    "upload_records",
    "write_records",
]
