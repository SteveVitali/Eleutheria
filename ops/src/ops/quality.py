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
(SIG-ENG-042 / B4 G11). The nightly ``M`` job itself belongs to P34.44b; this
runner is the harness that job calls.
"""

from __future__ import annotations

import json
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


def eval_gq24(ctx: EvalContext) -> Measurement:
    """GQ-24 — the inferential auto-write lock: auto-written same-device
    decisions in any identity-inference tier while no B5 evaluation certifies
    that tier. All auto_writes in tiers 1g/3g/4g/5g count (no B5 certification
    exists today — P34.45 owns the certified posture)."""
    rows = _rows(
        ctx.conn,
        """
        SELECT match_id, match_tier, tier_label
        FROM camera_site_match
        WHERE disposition = 'auto_write' AND decided_by = 'auto'
        """,
    )
    violations = sum(
        1
        for r in rows
        if _INFERENTIAL_TIER_RE.match(str(r["tier_label"]))
        and str(r["tier_label"]) not in _NAMESPACE_1G_LABELS
    )
    return Measurement(
        check_id="GQ-24",
        offered=len(rows),
        evaluated=len(rows),
        measured=violations,
        detail={
            "auto_write_total": len(rows),
            "inferential_auto_writes": violations,
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
#: human verification and is legal only next to a B5 completion marker.
_CLAIM_PHRASES = ("human-verified", "independently reviewed", "certified")


def _scan_quality_figures(obj: Any, path: Path, hits: list[str]) -> None:
    """Walk a JSON tree: every object that publishes a quality/evaluation
    figure (a numeric value under a metric-ish key) must name its basis class;
    claim phrases need a B5 marker in the same object."""
    if isinstance(obj, dict):
        text = " ".join(str(v) for v in obj.values() if isinstance(v, str))
        basis = str(obj.get("basis_class") or obj.get("basis") or "")
        if any(p in text for p in _CLAIM_PHRASES) and "B5" not in basis:
            hits.append(f"{path}: claim phrase without a B5 marker")
        figure_keys = {"measured", "value", "precision", "recall", "f1"}
        if any(isinstance(obj.get(k), (int, float)) for k in figure_keys) and (
            "basis_class" not in obj and "basis" not in obj
        ):
            hits.append(f"{path}: quality figure without a basis class")
        for v in obj.values():
            _scan_quality_figures(v, path, hits)
    elif isinstance(obj, list):
        for v in obj:
            _scan_quality_figures(v, path, hits)


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
            for phrase in _CLAIM_PHRASES:
                if phrase in text and "B5" not in text:
                    hits.append(f"{path}: '{phrase}' without a B5 marker")
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


def main(argv: list[str] | None = None) -> int:
    """``sig-ops quality`` — the P34.44a harness surface (offline/read-only)."""
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops quality",
        description=(
            "P34.44a (SIG-CONF-006/007/008/013): run the read-only quality "
            "probe for a placement and emit sig.quality-report/1 + "
            "sig.probe-run/1 records. DB checks run under a read-only "
            "session; file checks scan a release/build dir. The nightly "
            "schedule and the baseline run belong to P34.44b."
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
    return 2


__all__ = [
    "EvalContext",
    "Evaluator",
    "FILE_EVALUATORS",
    "PUBLISHER_BLOCKLIST",
    "SEAM_DEFERRALS",
    "SPINE_EVALUATORS",
    "connect_readonly",
    "probe_run_record",
    "run_quality_probe",
    "write_records",
]
