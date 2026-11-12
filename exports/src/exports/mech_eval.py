# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.44 (CONF-09 / SIG-EVAL-003 + SIG-EVAL-006 + SIG-CONF-012): the mechanical
evaluation report — the ``sig.mech-eval/1`` release artifact that replaces the
P28.1 table on ``/methodology/``.

Human estimands are unavailable: no independent human labeler exists (the
superseded rows 184–187; ``D-R10-HUMAN-1`` under trigger T-EVAL-IND). The
report therefore carries the mechanical measures only — M-1 derivation
census, the M-1b/M-2 sample states with their exact-bound method, M-3
cross-copy agreement, M-4 perturbation, M-5 hard negatives, M-9
corroboration — and records every absence honestly, never substituted
(ADR-152/153, L3 §4).

The SIG-EVAL-003 shape binds per estimand: numerator, denominator, method
and population, plus the ``measured|partial|unavailable`` state and its
basis class. The SIG-EVAL-006 scope block names exactly the tiers,
populations, source mix, ruleset and time window each figure speaks for —
nothing is generalised beyond them (SIG-CONF-012: a mechanical estimand is
labelled as such and is never presented as real-world precision or recall).

Inputs:

* ``runs`` — ``read_resolved_site_runs`` output (``[]`` when no camera-site
  ER run has completed; the spine measures then report ``unavailable`` with
  the honest reason — never fabricated);
* ``dedup_view`` — the P35.47 shared dedup view (M-9's corroboration census);
* ``corpus_doc`` — the committed ``sig.mech-eval-corpus/1`` record the
  deterministic generator (``scripts/eval/run_mech_eval.py``) pins — the
  M-4/M-5 measured sections over the committed real-data regression corpus;
* the scope fields (ruleset version, copy tolerance, source mix, ``as_of``).

Pure module: no SQL, no I/O, no clock reads.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "sig.mech-eval/1"
CORPUS_SCHEMA = "sig.mech-eval-corpus/1"

#: The SIG-CONF-012 verbatim disclaimer — every estimand is mechanical and is
#: never presented as real-world precision or recall.
DISCLAIMER = "never an estimate of real-world precision or recall"

#: The disclosure the report carries verbatim — the honest posture sentence.
DISCLOSURE = (
    "Mechanical evaluation only. No person outside the project has labelled "
    "SIG's data or its matching, and no independent human evaluation exists "
    "(D-R10-HUMAN-1 — it fires only when the operator records that at least "
    "two independent labelers are available, trigger T-EVAL-IND). Every "
    "figure below is a mechanical census or sample over the population its "
    "row names — " + DISCLAIMER + "."
)

#: The four EVAL-003 human estimands — all unavailable in Round 11.
HUMAN_ESTIMANDS: tuple[tuple[str, str], ...] = (
    (
        "auto_positive_precision",
        "strict share of sampled auto-positive edges verified same by a human reference",
    ),
    (
        "candidate_recall",
        "share of the independently referenced same-pair population the "
        "candidate generator recovers",
    ),
    (
        "cluster_quality",
        "pairwise and B-cubed cluster quality against human reference cluster memberships",
    ),
    (
        "labelability",
        "decisive share of the human-labelled frame (abstentions counted)",
    ),
)

#: Why the human estimands are unavailable — the recorded reason, verbatim
#: across all four (the absence is named, never substituted).
HUMAN_UNAVAILABLE_REASON = "no_human_reference"

UPSTREAM_GETS_REASON = "upstream_gets_deferred"

ESTIMAND_STATES: tuple[str, ...] = ("measured", "partial", "unavailable")

MEASURE_IDS: tuple[str, ...] = (
    "m1_derivation_census",
    "m1b_id_resolution_sample",
    "m2_fidelity_sample",
    "m3_cross_copy_agreement",
    "m4_perturbation",
    "m5_hard_negatives",
    "m9_corroboration",
)

#: The estimand label each measure carries (SIG-CONF-012 — named verbatim).
MEASURE_LABELS: dict[str, str] = {
    "m1_derivation_census": (
        "share of the run's applied derivation collapses re-verified by the "
        "GQ-23 census — a mechanical census over declared copy lineages, " + DISCLAIMER
    ),
    "m1b_id_resolution_sample": (
        "share of a seeded per-namespace sample of C1 collapses whose "
        "declared id resolves to a matching upstream record — a mechanical "
        "sample over the copy link only, " + DISCLAIMER
    ),
    "m2_fidelity_sample": (
        "share of a seeded sample of published sites whose current upstream "
        "record still matches on id, point and attributes — a mechanical "
        "fidelity sample, " + DISCLAIMER
    ),
    "m3_cross_copy_agreement": (
        "agreement between copies of one upstream record (coordinate "
        "offsets, attributes) — a mechanical census over the run's measured "
        "copy links, " + DISCLAIMER
    ),
    "m4_perturbation": (
        "per-class join/no-join outcomes over modelled perturbations of "
        "corpus records — a mechanical census against the declared ruleset "
        "contract, " + DISCLAIMER
    ),
    "m5_hard_negatives": (
        "share of mechanically-declared known-distinct pairs the matcher "
        "merges — a census over the declared negative classes only, " + DISCLAIMER
    ),
    "m9_corroboration": (
        "share of resolved sites seen by two or more declared independent "
        "lineages — a mechanical census over declared independence "
        "classes, " + DISCLAIMER
    ),
}


def _estimand(
    estimand_id: str,
    *,
    state: str,
    basis: str,
    numerator: int | None,
    denominator: int | None,
    value: str | None,
    method: str | None,
    population: str,
    unavailable_reason: str | None = None,
    rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """One estimand block — the SIG-EVAL-003 acceptance shape verbatim."""
    return {
        "id": estimand_id,
        "label": MEASURE_LABELS.get(estimand_id, ""),
        "state": state,
        "basis": basis,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "method": method,
        "population": population,
        "unavailable_reason": unavailable_reason,
        "rows": [dict(r) for r in rows],
    }


def _human_estimands() -> dict[str, dict[str, Any]]:
    """The four human estimands — ``unavailable`` with named reasons, never
    substituted by agent/LLM agreement (ADR-152)."""
    out: dict[str, dict[str, Any]] = {}
    for name, population in HUMAN_ESTIMANDS:
        out[name] = {
            "id": name,
            "label": f"human-evaluated {name.replace('_', ' ')} — {DISCLAIMER}",
            "state": "unavailable",
            "basis": "none",
            "numerator": None,
            "denominator": None,
            "value": None,
            "method": None,
            "population": population,
            "unavailable_reason": HUMAN_UNAVAILABLE_REASON,
            "rows": [],
        }
    return out


# ---------------------------------------------------------------------------
# The spine measures — the latest completed camera-site ER run's records
# ---------------------------------------------------------------------------


def _m1_census(run: Mapping[str, Any] | None) -> dict[str, Any]:
    """M-1 derivation census (GQ-23, B1) — every applied collapse re-verified."""
    population = (
        "every applied C0–C2 derivation collapse of the latest completed camera-site ER run"
    )
    if run is None:
        return _estimand(
            "m1_derivation_census",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=population,
            unavailable_reason="no_completed_run",
        )
    summary = run.get("summary") or {}
    census = summary.get("derivation_census")
    run_key = str(run.get("run_key") or "")
    if census is None:
        return _estimand(
            "m1_derivation_census",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=f"{population} (run {run_key})",
            unavailable_reason="no_census_record",
        )
    checked = int(census.get("checked") or 0)
    failures = list(census.get("gq23_failures") or [])
    verified = checked - len(failures)
    rows: list[dict[str, Any]] = [
        {
            "kind": "census",
            "checked": checked,
            "verified": verified,
            "failures": len(failures),
            "demote_next_run": len(census.get("demote_next_run") or []),
            "origin_distinct_violations": int(census.get("origin_distinct_violations") or 0),
        }
    ]
    for f in failures[:20]:
        rows.append(
            {
                "kind": "gq23_failure",
                "left": str(f.get("left") or ""),
                "right": str(f.get("right") or ""),
                "tier": f.get("tier"),
                "token": str(f.get("token") or ""),
                "reason": str(f.get("reason") or ""),
            }
        )
    return _estimand(
        "m1_derivation_census",
        state="measured" if checked > 0 else "unavailable",
        basis="B1" if checked > 0 else "none",
        numerator=verified if checked > 0 else None,
        denominator=checked if checked > 0 else None,
        value=f"{verified} of {checked} re-verified" if checked > 0 else None,
        method=(
            "the GQ-23 derivation census re-verifies every applied C0–C2 "
            "collapse independently on every run — a full census, never a "
            "sample; a failing (lineage, tier) demotes automatically on the "
            "next run"
            if checked > 0
            else None
        ),
        population=f"{population} — run {run_key} recorded {checked}",
        unavailable_reason=(None if checked > 0 else "empty_census"),
        rows=rows,
    )


def _m1b_sample(run: Mapping[str, Any] | None) -> dict[str, Any]:
    """M-1b id-resolution sample (B2) — the seeded per-namespace frame.

    The frame is drawn on every run; the origin-record GETs that verify it
    are the deferred upstream leg (OP-10 — the contact-string decision), so
    the measured bound is honestly ``unavailable`` — the frame and the
    exact-bound method are recorded, never a fabricated verification share.
    """
    method = (
        "seeded simple-random n ≤ 200 per declared id namespace over the "
        "run's applied C1 collapses; the origin record is re-fetched by id "
        "and checked within tolerance; the verified share carries an exact "
        "one-sided Clopper–Pearson α = 0.05 lower bound"
    )
    if run is None:
        return _estimand(
            "m1b_id_resolution_sample",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=method,
            population=(
                "a seeded per-namespace sample of the latest completed "
                "camera-site ER run's applied C1 collapses"
            ),
            unavailable_reason="no_completed_run",
        )
    summary = run.get("summary") or {}
    frame = summary.get("m1b_id_resolution_sample") or {}
    run_key = str(run.get("run_key") or "")
    rows: list[dict[str, Any]] = []
    total_collapses = 0
    total_drawn = 0
    for ns in sorted(frame):
        block = frame[ns] or {}
        collapses = int(block.get("collapses") or 0)
        drawn = int(block.get("sample_size") or 0)
        total_collapses += collapses
        total_drawn += drawn
        rows.append(
            {
                "kind": "namespace_frame",
                "namespace": str(ns),
                "collapses": collapses,
                "drawn": drawn,
            }
        )
    return _estimand(
        "m1b_id_resolution_sample",
        state="unavailable",
        basis="none",
        numerator=None,
        denominator=None,
        value=None,
        method=method,
        population=(
            f"the seeded per-namespace sample drawn from run {run_key}: "
            f"{total_drawn} sampled of {total_collapses} applied C1 "
            f"collapses across {len(frame)} declared namespace(s)"
        ),
        unavailable_reason=UPSTREAM_GETS_REASON,
        rows=rows,
    )


def _m2_fidelity(run: Mapping[str, Any] | None) -> dict[str, Any]:
    """M-2 fidelity sample (B2) — published record vs current upstream.

    The upstream re-fetch leg is deferred with M-1b's (OP-10); the estimand
    and its exact-bound method are recorded, never a substituted figure.
    """
    method = (
        "seeded simple-random n = 200 published sites re-fetched from their "
        "current upstream by id; the share matching on id, point and "
        "attributes carries exact Clopper–Pearson bounds per source class"
    )
    reason = "no_completed_run" if run is None else UPSTREAM_GETS_REASON
    population = (
        "a seeded n = 200 sample of the release's published camera-site records, per source class"
    )
    if run is not None:
        population = (
            f"a seeded n = 200 sample of the {int(run.get('observation_count') or 0)} "
            f"observation-level records behind run {run.get('run_key')}, per source class"
        )
    return _estimand(
        "m2_fidelity_sample",
        state="unavailable",
        basis="none",
        numerator=None,
        denominator=None,
        value=None,
        method=method,
        population=population,
        unavailable_reason=reason,
    )


def _m3_agreement(run: Mapping[str, Any] | None, *, copy_tolerance_m: float) -> dict[str, Any]:
    """M-3 cross-copy agreement (B1) — the measured copy-link distribution."""
    population = "the applied derivation links (C0–C2) of the latest completed camera-site ER run"
    if run is None:
        return _estimand(
            "m3_cross_copy_agreement",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=population,
            unavailable_reason="no_completed_run",
        )
    links = [
        lnk
        for lnk in (run.get("links") or [])
        if str(lnk.get("relation_type") or "") == "derived_from"
        and str(lnk.get("disposition") or "") == "auto_write"
    ]
    run_key = str(run.get("run_key") or "")
    if not links:
        return _estimand(
            "m3_cross_copy_agreement",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=f"{population} — run {run_key} applied none",
            unavailable_reason="no_copy_links",
        )
    distances: list[float] = []
    within = 0
    attr_diff_links = 0
    shared_ref = 0
    tiers: dict[int, int] = {}
    for lnk in links:
        ev = lnk.get("evidence") or {}
        tier = lnk.get("tier")
        if isinstance(tier, int):
            tiers[tier] = tiers.get(tier, 0) + 1
        dist = ev.get("distance_m")
        if isinstance(dist, int | float):
            distances.append(float(dist))
            if float(dist) <= copy_tolerance_m:
                within += 1
        diffs = ev.get("attribute_differences") or []
        if diffs:
            attr_diff_links += 1
        if ev.get("shared_upstream_ref") not in (None, ""):
            shared_ref += 1
    distances.sort()
    n = len(links)
    bands = {
        "le_copy_tolerance": within,
        "above_copy_tolerance": len(distances) - within,
    }
    rows: list[dict[str, Any]] = [
        {
            "kind": "offset_distribution",
            "measured_links": len(distances),
            "max_m": round(distances[-1], 3) if distances else None,
            "median_m": round(distances[len(distances) // 2], 3) if distances else None,
            **bands,
        },
        {
            "kind": "copy_attributes",
            "links_with_shared_upstream_ref": shared_ref,
            "links_with_attribute_differences": attr_diff_links,
            "tiers": {str(t): c for t, c in sorted(tiers.items())},
        },
    ]
    return _estimand(
        "m3_cross_copy_agreement",
        state="measured",
        basis="B1",
        numerator=within,
        denominator=len(distances),
        value=f"{within} of {len(distances)} within {copy_tolerance_m:g} m",
        method=(
            "the census of every applied C0–C2 copy link's measured distance "
            "and recorded attribute differences — the empirical copy "
            "distribution the tolerance is justified from"
        ),
        population=f"{population} — {n} links of run {run_key}",
        rows=rows,
    )


def _m9_corroboration(run: Mapping[str, Any] | None, dedup_view: Any) -> dict[str, Any]:
    """M-9 corroboration (B1) — sites seen by ≥ 2 independent lineages."""
    population = (
        "the resolved sites of the latest completed camera-site ER run over "
        "the release's published member records"
    )
    if run is None or dedup_view is None:
        return _estimand(
            "m9_corroboration",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=population,
            unavailable_reason="no_completed_run",
        )
    n_lineages = getattr(dedup_view, "n_lineages", None)
    site_members = getattr(dedup_view, "site_members", {}) or {}
    if n_lineages is None:
        return _estimand(
            "m9_corroboration",
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=population,
            unavailable_reason="lineage_read_absent",
        )
    multi = [s for s, ms in site_members.items() if len(ms) >= 2]
    corroborated = sum(1 for s in multi if int(n_lineages.get(s, 1)) >= 2)
    rows: list[dict[str, Any]] = [
        {
            "kind": "corroboration",
            "sites": len(site_members),
            "multi_record_sites": len(multi),
            "independently_corroborated": corroborated,
        }
    ]
    summary = run.get("summary") or {}
    for key in (
        "multi_record_sites_independently_corroborated",
        "multi_record_sites_one_lineage_only",
        "multi_record_sites_unclassified_lineage",
    ):
        if key in summary:
            rows.append({"kind": "run_summary", "measure": key, "value": summary[key]})
    return _estimand(
        "m9_corroboration",
        state="measured",
        basis="B1",
        numerator=corroborated,
        denominator=len(multi),
        value=f"{corroborated} of {len(multi)} multi-record sites",
        method=(
            "a census of each resolved site's declared independence-class "
            "count — a site corroborates only when two or more DECLARED "
            "lineage roots contribute records (a republished copy is never "
            "independent)"
        ),
        population=f"{population} — run {run.get('run_key')}",
        rows=rows,
    )


# ---------------------------------------------------------------------------
# The corpus measures — the committed sig.mech-eval-corpus/1 record
# ---------------------------------------------------------------------------


def _corpus_section(corpus_doc: Mapping[str, Any], measure: str) -> dict[str, Any]:
    """Lift a corpus leg (m4/m5) into the EVAL-003 estimand shape."""
    sections = corpus_doc.get("sections") or {}
    section = sections.get(measure)
    population = str(corpus_doc.get("population") or "the committed real-data regression corpus")
    if not isinstance(section, dict):
        return _estimand(
            measure,
            state="unavailable",
            basis="none",
            numerator=None,
            denominator=None,
            value=None,
            method=None,
            population=population,
            unavailable_reason="corpus_section_absent",
        )
    rows: list[dict[str, Any]] = []
    if measure == "m4_perturbation":
        tested = mismatches = 0
        for cls, d in sorted((section.get("classes") or {}).items()):
            t = int(d.get("tested") or 0)
            mm = int(d.get("mismatches") or 0)
            tested += t
            mismatches += mm
            rows.append(
                {
                    "kind": "class",
                    "class": str(cls),
                    "expected": str(d.get("expected") or ""),
                    "tested": t,
                    "joined": int(d.get("joined") or 0),
                    "mismatches": mm,
                    "outcome": str(d.get("outcome") or ""),
                }
            )
        method = (
            "known-answer tests: a declared-mirror twin of each sampled "
            "corpus record is perturbed per class and resolved by the "
            "production ruleset — the outcome is compared to the declared "
            "expectation (modelled perturbations only)"
        )
        return _estimand(
            measure,
            state="measured",
            basis="B1",
            numerator=tested - mismatches,
            denominator=tested,
            value=f"{tested - mismatches} of {tested} matched the known answer",
            method=method,
            population=population,
            rows=rows,
        )
    # m5_hard_negatives — the measured estimand is the MERGED share over the
    # declared negative classes (expected: zero).
    tested = merged = 0
    for cls, d in sorted((section.get("classes") or {}).items()):
        t = int(d.get("tested") or 0)
        mg = int(d.get("merged") or 0)
        tested += t
        merged += mg
        rows.append(
            {
                "kind": "class",
                "class": str(cls),
                "tested": t,
                "merged": mg,
                "assessed": int(d.get("assessed") or 0),
                "outcome": str(d.get("outcome") or ""),
            }
        )
    return _estimand(
        measure,
        state="measured",
        basis="B1",
        numerator=merged,
        denominator=tested,
        value=f"{merged} of {tested} known-distinct pairs merged",
        method=(
            "a census over mechanically-declared known-distinct pairs — "
            "distinct unique ids in one origin namespace (including real "
            "co-located records), incompatible declared technologies, and "
            "far-apart records sharing a normalised ref — resolved by the "
            "production ruleset"
        ),
        population=population,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def build_mech_eval(
    *,
    runs: Sequence[Mapping[str, Any]],
    dedup_view: Any = None,
    member_records: Mapping[str, str] | None = None,
    corpus_doc: Mapping[str, Any],
    source_names: Mapping[str, str] | None = None,
    ruleset_version: str,
    copy_tolerance_m: float,
    as_of: str,
) -> dict[str, Any]:
    """Build the ``sig.mech-eval/1`` record.

    ``runs`` is ``read_resolved_site_runs`` output — ``[]`` is the honest
    no-run posture (the hosted ruleset-v3 run is queued; every spine measure
    reports ``unavailable`` with the named reason). ``member_records`` is the
    export's published-member → source map (the source mix the spine
    measures speak for). ``corpus_doc`` is the committed
    ``sig.mech-eval-corpus/1`` record the generator pins.
    """
    run = runs[0] if runs else None
    members = dict(member_records or {})
    source_ids = sorted({str(s) for s in members.values() if s})
    names = dict(source_names or {})
    corpus_sources = [str(s) for s in (corpus_doc.get("sources") or []) if str(s)]

    estimands: dict[str, dict[str, Any]] = {
        "m1_derivation_census": _m1_census(run),
        "m1b_id_resolution_sample": _m1b_sample(run),
        "m2_fidelity_sample": _m2_fidelity(run),
        "m3_cross_copy_agreement": _m3_agreement(run, copy_tolerance_m=copy_tolerance_m),
        "m4_perturbation": _corpus_section(corpus_doc, "m4_perturbation"),
        "m5_hard_negatives": _corpus_section(corpus_doc, "m5_hard_negatives"),
        "m9_corroboration": _m9_corroboration(run, dedup_view),
    }

    run_summary = (run or {}).get("summary") or {}
    scope = {
        "tiers": {
            "auto_collapse_derivation": [0, 1, 2],
            "review_only_inferential": [3, 4, 5],
            "note": (
                "only derivation-collapse tiers (mechanically verified "
                "copies of one upstream record) auto-merge — every "
                "inferential match is a review-only possible_duplicate"
            ),
        },
        "ruleset": {
            "camera_site_rules_version": ruleset_version,
            "run_rules_version": run_summary.get("rules_version"),
            "resolver_version": run_summary.get("resolver_version"),
        },
        "populations": {
            "spine": (
                f"the latest completed camera-site ER run "
                f"{run.get('run_key')} over {len(members)} published member "
                "records"
                if run is not None
                else "no completed camera-site ER run — the spine measures "
                "report unavailable rather than fabricate"
            ),
            "corpus": str(corpus_doc.get("population") or ""),
        },
        "source_mix": {
            "spine_member_sources": [{"id": s, "name": str(names.get(s) or s)} for s in source_ids],
            "corpus_sources": corpus_sources,
        },
        "time_window": {
            "as_of": str(as_of),
            "run_completed_at": run_summary.get("completed_at"),
            "corpus": corpus_doc.get("time_window") or {},
        },
        "generalisation_limits": (
            "these figures measure exactly the populations named — never "
            "identity precision across independent sources, candidate "
            "recall, organisation identity, coverage completeness, or that "
            "a camera exists or operates (SIG-EVAL-006)"
        ),
    }

    return {
        "schema": SCHEMA,
        "report": "mechanical_evaluation",
        "generated_by": "P37.44 (docs/tickets/468_P37.44__mechanical-evaluation-report.md)",
        "as_of": str(as_of),
        "posture": (
            "mechanical measures only — the human estimands are unavailable "
            "because no independent human evaluation exists"
        ),
        "disclosure": DISCLOSURE,
        "deferral": "D-R10-HUMAN-1",
        "scope": scope,
        "human_estimands": _human_estimands(),
        "estimands": estimands,
    }


# ---------------------------------------------------------------------------
# Lint — the SIG-EVAL-003/012 contract made executable
# ---------------------------------------------------------------------------


def mech_eval_lint_errors(doc: Mapping[str, Any]) -> list[str]:
    """Refuse a report that drops the contract: every estimand carries
    numerator, denominator, method and population (null only with a named
    ``unavailable_reason``); the disclaimer text is verbatim; the human
    estimands are all honestly ``unavailable``; the scope names tiers,
    population, source mix, ruleset and time window (SIG-EVAL-006)."""
    errors: list[str] = []
    if doc.get("schema") != SCHEMA:
        errors.append(f"schema {doc.get('schema')!r} != {SCHEMA!r}")
        return errors
    disclosure = str(doc.get("disclosure") or "")
    if DISCLAIMER not in disclosure:
        errors.append("disclosure drops the required estimand disclaimer (SIG-CONF-012)")

    human = doc.get("human_estimands")
    if not isinstance(human, dict) or set(human) != {n for n, _ in HUMAN_ESTIMANDS}:
        errors.append("human_estimands must name all four EVAL-003 estimands")
    else:
        for name, e in human.items():
            if not isinstance(e, dict):
                errors.append(f"human estimand {name} malformed")
                continue
            if e.get("state") != "unavailable":
                errors.append(
                    f"human estimand {name} state {e.get('state')!r} — human "
                    "estimands are unavailable, never substituted"
                )
            if not e.get("unavailable_reason"):
                errors.append(f"human estimand {name} names no unavailable_reason")

    estimands = doc.get("estimands")
    if not isinstance(estimands, dict) or set(estimands) != set(MEASURE_IDS):
        errors.append(f"estimands must name all of {MEASURE_IDS}")
        estimands = estimands if isinstance(estimands, dict) else {}
    measured = 0
    for mid, e in (estimands or {}).items():
        if not isinstance(e, dict):
            errors.append(f"estimand {mid} malformed")
            continue
        for field in ("numerator", "denominator", "method", "population", "state"):
            if field not in e:
                errors.append(f"estimand {mid} lacks {field} (SIG-EVAL-003 shape)")
        if not str(e.get("label") or ""):
            errors.append(f"estimand {mid} lacks its estimand label (SIG-CONF-012)")
        elif DISCLAIMER not in str(e["label"]):
            errors.append(f"estimand {mid} label drops the disclaimer (SIG-CONF-012)")
        state = e.get("state")
        if state not in ESTIMAND_STATES:
            errors.append(f"estimand {mid} state {state!r} not in {ESTIMAND_STATES}")
        if state == "measured":
            measured += 1
            if e.get("numerator") is None or e.get("denominator") is None:
                errors.append(f"estimand {mid} measured without numerator/denominator")
            if not e.get("method"):
                errors.append(f"estimand {mid} measured without a method")
        if state == "unavailable" and not e.get("unavailable_reason"):
            errors.append(f"estimand {mid} unavailable without a named reason")

    scope = doc.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope absent — SIG-EVAL-006 scoping is required")
    else:
        for key in ("tiers", "ruleset", "populations", "source_mix", "time_window"):
            if key not in scope:
                errors.append(f"scope lacks {key} (SIG-EVAL-006)")
    # SIG-ENG-042 — a report where nothing is measured and nothing names its
    # absence honestly is a vacuous pass: every unavailable estimand must
    # carry its reason (checked above); a doc with zero estimands fails here.
    if isinstance(estimands, dict) and not estimands:
        errors.append("zero estimands — a vacuous report is refused")
    return errors


#: Sanity guard for the corpus record (used by the generator + tests).
def corpus_lint_errors(doc: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != CORPUS_SCHEMA:
        errors.append(f"corpus record schema {doc.get('schema')!r} != {CORPUS_SCHEMA}")
        return errors
    for leg in ("m4_perturbation", "m5_hard_negatives"):
        est = str((doc.get("estimands") or {}).get(leg) or "")
        if DISCLAIMER not in est:
            errors.append(f"corpus estimands.{leg} drops the disclaimer (SIG-CONF-012)")
        if not isinstance((doc.get("sections") or {}).get(leg), dict):
            errors.append(f"corpus sections.{leg} absent — the measure cannot emit")
    if not (doc.get("sources") or []):
        errors.append("corpus record names no source mix (SIG-EVAL-006)")
    if re.fullmatch(r"\d+", str(doc.get("corpus_version") or "")) is None:
        errors.append("corpus record lacks a numeric corpus_version")
    return errors
