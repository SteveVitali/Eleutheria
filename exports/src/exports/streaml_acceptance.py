# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.67 (R11-CONF-14, ADR-154 / L3 §9, SIG-CONF-004/006) — the Stream-L
acceptance record.

CONF-14 is the tail ticket of the L3 confidence program: re-measure L2's
graph-quality findings on the Round-11 release, flip every ratchet whose
named fixing rows landed, and report the §9 success criteria. This module
builds the deterministic ``sig.streaml-acceptance/1`` record over committed
inputs only:

- the committed ``sig.quality-checks/1`` registry (modes already reflect
  this row's flips);
- the historical L2 metrics CSV (the ``sig-2026-09-27-ce480ab1`` census —
  a **before** column, never re-measured here);
- the landed-row census the generator reads off ``BUILD_INDEX.md``;
- whatever ``sig.quality-report/1`` measurements the caller binds
  (today: the deterministic fixture corpus — never the release).

The live re-measurement leg itself is ``prepared_not_executed`` under
``live_verification=false`` — the Round-11 release candidate's cut and
promotion legs are still queued (``D-P37.65a-1`` / ``D-P37.65b-1``) and the
read-only ``sig_audit`` handle is an OM-19 live window. The record names
that owed leg and its verbatim re-run prompt; a fixture number is never a
release measurement.
"""

from __future__ import annotations

import hashlib
from typing import Any, Final

ACCEPTANCE_VERSION: Final = "sig.streaml-acceptance/1"
FLIP_TICKET: Final = "P37.67"
LIVE_DEFERRAL: Final = "D-P37.67-1"
SEAM_DEFERRAL: Final = "D-P37.67-2"
L2_RELEASE: Final = "sig-2026-09-27-ce480ab1"
L2_SOURCE: Final = "docs/build/planning/2026-09-30-next-phase/data/l2_metrics.csv"
RERUN_PROMPT: Final = (
    "implement-spec spec=docs/tickets/496_P37.67__stream-l-re-measure.md live_verification=true"
)

CRITERION_STATUSES: Final = frozenset({"met", "miss", "not_measured"})
CRITERION_BASES: Final = frozenset({"fixture", "engineered", "release", ""})

#: Why each still-ratcheted check was *not* flipped this row — every one names
#: the concrete block (an owed evaluator seam, an unconsumed V-check output, a
#: first-run population, or a gate activation). Kept ratchets are reported,
#: never silently skipped (ADR-154: loosening needs an ADR; a flip lands only
#: where its named cause is demonstrably removed).
KEPT_RATCHET_REASONS: Final = {
    "GQ-02": "capture-replay seam owed — the replay telemetry job is P34.44b's "
    "QUEUED nightly leg; no measured population exists to enforce over",
    "GQ-06": "typing-census evaluator seam owed — the PKG-07/PKG-11 typing work "
    "lands the fix but no evaluator measures the census; a flip would gate on "
    "not_evaluable",
    "GQ-08": "consumes V9 (REL-04b → P35.58) at release-verify — the withheld-"
    "point verdict is not folded into the quality report; the seam is owed "
    "before enforcement",
    "GQ-09": "R evaluator seam owed — the dossier-key scheme split landed "
    "(P35.17/P35.18) but no evaluator reads it yet",
    "GQ-12": "lineage/independence-class seam owed (CONF-04); the resolution "
    "independence census has no evaluator",
    "GQ-16": "consumes the V6 one-resolved verdict at release-verify — not "
    "folded into the quality report",
    "GQ-17": "consumes the V8 attribution verdict at release-verify — not "
    "folded into the quality report",
    "GQ-18": "flips to the full requirement at the G2 byte-binding activation "
    "(its registry note names the trigger); enforcement rides the activation "
    "gate, not this sweep",
    "GQ-23": "first derivation-collapse run not yet executed — P37.46b landed "
    "the materializer but no collapse run exists to census; evaluated=0 must "
    "fail, so a flip would gate on an empty population",
    "GQ-25": "same first-collapse-run debt as GQ-23 — the namespace coverage "
    "check has no population until a collapse run exists",
    "GQ-26": "RDC corpus legs ride the rdc harness leg queue; no measured "
    "population exists to enforce over",
}

#: The L3 §9 "Round-11 success criteria" (verbatim fragments), each naming the
#: evidence that establishes it. ``checks`` are registry ids; ``artifact`` refs
#: name non-registry evidence. CONF-14 measures these, never asserts them.
SUCCESS_CRITERIA: Final = (
    ("SC-01", "subject-key collisions = 0", ("GQ-04",)),
    ("SC-02", "enforce-mode failures = 0", ("run:enforce_failures",)),
    ("SC-03", "UUID labels = 0", ("GQ-14",)),
    ("SC-04", "1970 edges = 0", ("GQ-15",)),
    ("SC-05", "publisher-as-operator = 0", ("GQ-07",)),
    ("SC-06", "entity-type mismatches = 0", ("GQ-06",)),
    ("SC-07", "exact claim repeats <= 1 %", ("GQ-03",)),
    ("SC-08", "dossier inflation <= 1.02x", ("GQ-10",)),
    (
        "SC-09",
        "100 % of >=2-lineage coincident points accounted for",
        ("GQ-10", "GQ-12"),
    ),
    ("SC-10", "derivation census 100 %", ("GQ-23",)),
    ("SC-11", "M-1b lower bound >= 0.98 per declared namespace", ("mech-eval:M-1b",)),
    ("SC-12", "0 unexplained out-of-polygon points", ("GQ-08",)),
    ("SC-13", "0 swaps, 0 null-island points", ("GQ-08",)),
    ("SC-14", "technology on 100 % of site rows", ("GQ-06",)),
    ("SC-15", "contradiction recall 1.0", ("GQ-13",)),
    ("SC-16", "byte binding 100 % for every re-run source", ("GQ-18",)),
    ("SC-17", "attribution empty-where-required = 0", ("GQ-17",)),
    ("SC-18", "/quality/ live with every check", ("artifact:quality-page",)),
    ("SC-19", "0 'verified' strings without a B5 marker", ("GQ-27",)),
)

_METRIC_REF_RE_PREFIX = "L2-M"


def _metric_refs(note: str) -> list[str]:
    """``L2-M`` metric ids a check note cites — the before-column link."""
    import re

    out = []
    for m in re.finditer(r"L2-(M\d\d)", note):
        mid = "L2-" + m.group(1)
        if mid not in out:
            out.append(mid)
    return out


def _digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _report_label(report: dict[str, Any]) -> str:
    """A bound report's honest label — its placement + target, never 'the
    release'."""
    target = str(report.get("target") or "unspecified target")
    placement = str(report.get("placement") or "?")
    return f"{placement} scan over {target}"


def _check_measurements(check_id: str, reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Every bound-report row for one check, labelled by where it ran."""
    rows: list[dict[str, Any]] = []
    for placement in sorted(reports):
        report = reports[placement]
        for row in report.get("checks", ()):
            if row.get("id") == check_id:
                rows.append(
                    {
                        "placement": placement,
                        "target": _report_label(report),
                        "outcome": row.get("outcome"),
                        "measured": row.get("measured"),
                        "evaluated": row.get("evaluated"),
                        "reason": row.get("reason"),
                    }
                )
    return rows


def _check_row(
    check: Any,  # QualityCheck
    landed: frozenset[str],
    l2_by_id: dict[str, dict[str, str]],
    reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    flipped = check.mode == "enforce" and FLIP_TICKET in check.fixing
    if flipped:
        flip = "flipped"
    elif check.mode == "ratchet":
        flip = "kept_ratchet"
    elif check.mode == "enforce":
        flip = "enforce"  # flipped in an earlier row
    else:
        flip = "report"
    before = [
        {
            "metric": mid,
            "value": l2_by_id[mid]["value"] if mid in l2_by_id else None,
            "status": l2_by_id[mid]["status"] if mid in l2_by_id else None,
        }
        for mid in _metric_refs(check.note)
    ]
    fixing_rows = [t for t in check.fixing if t != FLIP_TICKET]
    row: dict[str, Any] = {
        "id": check.check_id,
        "mode": check.mode,
        "flip": flip,
        "basis_class": check.basis_class,
        "placement": sorted(check.placement),
        "direction": check.direction,
        "threshold": str(check.threshold),
        "baseline": ("pending" if check.baseline_pending else check.baseline),
        "unit": check.unit,
        "from": check.source_ids,
        "note": check.note,
        "fixing": list(check.fixing),
        "fixing_landed": all(t in landed for t in fixing_rows),
        "l2": before,
        "measured": _check_measurements(check.check_id, reports),
    }
    if flip == "kept_ratchet":
        row["kept_reason"] = KEPT_RATCHET_REASONS.get(check.check_id, "")
    return row


def _criterion(
    cid: str,
    text: str,
    evidence: tuple[str, ...],
    reports: dict[str, dict[str, Any]],
    quality_page: dict[str, Any] | None,
    registry_check_ids: frozenset[str],
) -> dict[str, Any]:
    """The honest verdict for one §9 criterion: met/miss only over a bound
    measurement, else not_measured naming the owed live leg."""
    out: dict[str, Any] = {
        "id": cid,
        "text": text,
        "evidence": list(evidence),
        "verdict": "not_measured",
        "basis": "",
        "detail": "",
        "deferral": LIVE_DEFERRAL,
    }

    def _measured_outcomes(check_id: str) -> list[dict[str, Any]]:
        rows = []
        for m in _check_measurements(check_id, reports):
            if m["outcome"] in ("pass", "fail", "regression"):
                rows.append(m)
        return rows

    if "artifact:quality-page" in evidence:
        # Engineered half: the page artifact declares every registered check
        # (Q-L3-5). The "live" half rides the promotion leg — D-P37.65b-1.
        if quality_page is not None:
            declared = {c.get("id") for c in quality_page["registry"]["checks"]}
            missing = sorted(registry_check_ids - declared)
            out["verdict"] = "met" if not missing else "miss"
            out["basis"] = "engineered"
            out["detail"] = (
                f"the committed sig.quality-page/1 artifact declares "
                f"{len(declared)}/{len(registry_check_ids)} checks"
                + (f"; missing {missing}" if missing else "")
                + "; the live-publication half rides the promotion leg "
                "(D-P37.65b-1, QUEUED)"
            )
            out["deferral"] = "D-P37.65b-1"
        return out

    if "mech-eval:M-1b" in evidence:
        out["detail"] = (
            "the M-1b namespace-bound measurement runs in P37.44's "
            "mechanical-evaluation machinery; its upstream legs are deferred "
            "under live_verification=false and the live release's bound is "
            "owed by the live leg"
        )
        return out

    if "run:enforce_failures" in evidence:
        measured = [(p, r) for p, r in reports.items() if "summary" in r]
        if not measured:
            out["detail"] = "no bound report measured the run summary"
            return out
        placement, report = sorted(measured)[0]
        fails = report["summary"].get("enforce_failures", [])
        out["verdict"] = "met" if not fails else "miss"
        out["basis"] = "fixture" if "fixture" in _report_label(report) else "release"
        out["detail"] = (
            f"{_report_label(report)}: enforce_failures={fails!r}; the "
            "release measurement is owed by the live leg"
        )
        return out

    # Check-evidenced criteria: every evidence check must be measured.
    all_rows: list[dict[str, Any]] = []
    for ref in evidence:
        if ref.startswith("GQ-"):
            all_rows.extend(_measured_outcomes(ref))
    if not all_rows:
        out["detail"] = "no evidence check was measured in a bound report"
        return out
    if any(r["outcome"] in ("fail", "regression") for r in all_rows):
        out["verdict"] = "miss"
    else:
        out["verdict"] = "met"
    labels = sorted({r["target"] for r in all_rows})
    out["basis"] = "fixture" if all("fixture" in t for t in labels) else "release"
    out["detail"] = (
        "; ".join(f"{r['outcome']} ({r['target']}, measured={r['measured']})" for r in all_rows)
        + "; the release measurement is owed by the live leg"
    )
    return out


def build_acceptance(
    *,
    registry: Any,  # CheckRegistry
    l2_rows: list[dict[str, str]],
    landed: frozenset[str],
    reports: dict[str, dict[str, Any]],
    quality_page: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    """Emit the ``sig.streaml-acceptance/1`` record."""
    l2_by_id = {r["metric_id"]: r for r in l2_rows}
    checks = [_check_row(c, landed, l2_by_id, reports) for c in registry.checks]
    check_ids = frozenset(c.check_id for c in registry.checks)
    criteria = [
        _criterion(cid, text, ev, reports, quality_page, check_ids)
        for cid, text, ev in SUCCESS_CRITERIA
    ]
    status_counts: dict[str, int] = {}
    for r in l2_rows:
        status_counts[r.get("status", "") or "unknown"] = (
            status_counts.get(r.get("status", "") or "unknown", 0) + 1
        )
    flipped = [c["id"] for c in checks if c["flip"] == "flipped"]
    kept = [c["id"] for c in checks if c["flip"] == "kept_ratchet"]
    # Record only the landed evidence this row actually relies on (the flipped
    # checks' fixing rows) — the full BUILD_INDEX census would make the record
    # churn on every later landed row.
    needed_landed = sorted(
        {t for c in checks if c["flip"] == "flipped" for t in c["fixing"] if t != FLIP_TICKET}
    )
    return {
        "version": ACCEPTANCE_VERSION,
        "generated_at": generated_at,
        "row": FLIP_TICKET,
        "conf": "R11-CONF-14",
        "target": (
            "the Round-11 release (the P37.65a/b cut+promotion legs are still "
            "queued — D-P37.65a-1 / D-P37.65b-1)"
        ),
        "l2": {
            "release": L2_RELEASE,
            "source": L2_SOURCE,
            "metrics": len(l2_rows),
            "status_counts": status_counts,
            "note": (
                "historical L2 census values — the before column. Re-measured "
                "only by the live leg; never re-asserted here."
            ),
        },
        "measurement": {
            "live_leg": "prepared_not_executed",
            "deferral": LIVE_DEFERRAL,
            "rerun_prompt": RERUN_PROMPT,
            "bound_reports": [
                {
                    "placement": p,
                    "target": _report_label(r),
                    "digest": r.get("digest"),
                    "summary": r.get("summary"),
                }
                for p, r in sorted(reports.items())
            ],
        },
        "landed_tickets": needed_landed,
        "flips": {
            "flipped": flipped,
            "kept_ratchet": kept,
            "note": (
                "flips land only where every named fixing row is landed and a "
                "measurement seam exists; kept ratchets name their block in "
                "kept_reason (the owed work rides " + SEAM_DEFERRAL + ")"
            ),
        },
        "checks": checks,
        "criteria": criteria,
        "counts": {
            "checks": len(checks),
            "flipped": len(flipped),
            "kept_ratchet": len(kept),
            "criteria": len(criteria),
            "criteria_met": sum(1 for c in criteria if c["verdict"] == "met"),
            "criteria_miss": sum(1 for c in criteria if c["verdict"] == "miss"),
            "criteria_not_measured": sum(1 for c in criteria if c["verdict"] == "not_measured"),
        },
    }


def acceptance_lint_errors(doc: dict[str, Any]) -> list[str]:
    """Fail-closed structural checks — the same posture as the registry and
    page lints: silence is never a pass."""
    errors: list[str] = []
    if doc.get("version") != ACCEPTANCE_VERSION:
        errors.append(f"version must be {ACCEPTANCE_VERSION!r}")
        return errors
    checks = doc.get("checks") or []
    seen: set[str] = set()
    for c in checks:
        cid = c.get("id", "")
        if cid in seen:
            errors.append(f"duplicate check row {cid}")
        seen.add(cid)
        flip = c.get("flip")
        if flip not in {"flipped", "kept_ratchet", "enforce", "report"}:
            errors.append(f"{cid}: flip {flip!r} not in the vocabulary")
        if flip == "flipped":
            if c.get("mode") != "enforce":
                errors.append(f"{cid}: flipped row must be enforce")
            if FLIP_TICKET not in (c.get("fixing") or ()):
                errors.append(f"{cid}: flipped row must carry {FLIP_TICKET} in fixing")
            if not c.get("fixing_landed"):
                errors.append(f"{cid}: flipped row must have every other fixing row landed")
        if flip == "kept_ratchet" and not c.get("kept_reason"):
            errors.append(f"{cid}: kept ratchet must name its block")
        if c.get("basis_class") == "B5":
            errors.append(f"{cid}: B5 evidence may never be asserted by this record")
    flipped = sorted(c["id"] for c in checks if c.get("flip") == "flipped")
    declared_flipped = sorted(doc.get("flips", {}).get("flipped", []))
    if flipped != declared_flipped:
        errors.append(f"flips.flipped {declared_flipped} != flipped check rows {flipped}")
    landed = set(doc.get("landed_tickets") or [])
    for c in checks:
        if c.get("flip") == "flipped":
            missing = [t for t in c.get("fixing", []) if t != FLIP_TICKET and t not in landed]
            if missing:
                errors.append(f"{c['id']}: fixing rows not landed: {missing}")
    for crit in doc.get("criteria") or []:
        if crit.get("verdict") not in CRITERION_STATUSES:
            errors.append(f"{crit.get('id')}: verdict {crit.get('verdict')!r} invalid")
        if crit.get("basis") not in CRITERION_BASES:
            errors.append(f"{crit.get('id')}: basis {crit.get('basis')!r} invalid")
        if crit.get("verdict") == "not_measured" and not crit.get("deferral"):
            errors.append(f"{crit.get('id')}: not_measured must name its deferral")
    declared_criteria = {c[0] for c in SUCCESS_CRITERIA}
    emitted = {c.get("id") for c in doc.get("criteria") or []}
    if emitted != declared_criteria:
        errors.append(
            f"criteria coverage mismatch: missing {sorted(declared_criteria - emitted)}, "
            f"extra {sorted(emitted - declared_criteria)}"
        )
    if doc.get("measurement", {}).get("live_leg") != "prepared_not_executed":
        errors.append("measurement.live_leg must be 'prepared_not_executed'")
    if doc.get("measurement", {}).get("rerun_prompt") != RERUN_PROMPT:
        errors.append("measurement.rerun_prompt must be the verbatim re-run prompt")
    counts = doc.get("counts") or {}
    if counts.get("checks") != len(checks):
        errors.append("counts.checks != len(checks)")
    if counts.get("criteria") != len(doc.get("criteria") or []):
        errors.append("counts.criteria != len(criteria)")
    return errors


def render_readout(doc: dict[str, Any]) -> str:
    """The generated markdown readout — the before/after table plus the §9
    criteria verdicts, honestly labelled."""
    lines: list[str] = []
    lines.append("<!-- GENERATED by scripts/eval/run_streaml_acceptance.py — do not hand-edit. -->")
    lines.append("")
    lines.append("# P37.67 — Stream-L acceptance (L2 re-measurement, R11-CONF-14)")
    lines.append("")
    lines.append(f"Generated `{doc['generated_at']}` · record `sig.streaml-acceptance/1`")
    lines.append("")
    l2 = doc["l2"]
    lines.append(
        f"The **before** column is the historical L2 census over release "
        f"`{l2['release']}` ({l2['metrics']} metrics: "
        + ", ".join(f"{v} {k}" for k, v in sorted(l2["status_counts"].items()))
        + "). The Round-11 release itself is **not measured here** — its cut "
        "and promotion legs are still queued (D-P37.65a-1 / D-P37.65b-1) and "
        "the live re-measurement is `prepared_not_executed` "
        f"(`{doc['measurement']['deferral']}`). Fixture numbers below are "
        "engineering evidence over a committed fixture corpus — they never "
        "establish release, staging, live or public status."
    )
    lines.append("")
    lines.append("## Before / after — the 27-check registry")
    lines.append("")
    lines.append(
        "| check | L2 reference (before) | mode | flip | measured after (bound reports) | basis |"
    )
    lines.append("|---|---|---|---|---|---|")
    for c in doc["checks"]:
        before = (
            "; ".join(f"{b['metric']} {b['status']} `{b['value']}`" for b in c["l2"]) or c["from"]
        )
        measured = (
            "; ".join(
                f"{m['outcome']} `{m['measured']}` ({m['target']})"
                + (f" — {m['reason']}" if m.get("reason") else "")
                for m in c["measured"]
            )
            or "not measured in a bound report"
        )
        flip = c["flip"]
        if flip == "kept_ratchet":
            flip = f"kept ratchet — {c.get('kept_reason', '')}"
        lines.append(
            f"| {c['id']} | {before} | {c['mode']} | {flip} | {measured} | {c['basis_class']} |"
        )
    lines.append("")
    lines.append("## L3 §9 success criteria")
    lines.append("")
    lines.append("| criterion | evidence | verdict | basis | detail |")
    lines.append("|---|---|---|---|---|")
    for crit in doc["criteria"]:
        lines.append(
            f"| {crit['id']} {crit['text']} | {', '.join(crit['evidence'])} | "
            f"**{crit['verdict']}** | {crit['basis'] or '—'} | {crit['detail']} |"
        )
    lines.append("")
    m = doc["measurement"]
    lines.append("## The owed live leg")
    lines.append("")
    lines.append(
        f"Re-running L2's measurements over the Round-11 release is "
        f"`{m['live_leg']}` — deferred as `{m['deferral']}` with the verbatim "
        f"re-run prompt `{m['rerun_prompt']}`. The packet at "
        "`docs/build/reports/p37.67-l2-remeasure/PACKET.md` names the exact "
        "verb sequence; a queued leg is never a pass."
    )
    lines.append("")
    return "\n".join(lines)
