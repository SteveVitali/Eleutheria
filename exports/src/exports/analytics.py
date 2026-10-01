# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``web/analytics/`` artifact family (P31.14 / SURFACE.1, ADR-R9-ANALYTICS).

Resolves **D-P27.5-1**: the presentation analytics the public surfaces render —
map density bins, network centrality + the ego-focus rule, the watch's tracked
decision point, per-surface provenance summaries with real evidence tiers
(W4…W0, §10.6), and the research-queue metadata — are **export-emitted**, not
committed constants and not the demo-guarded ``web/presentation/`` overlay
(P30.3 / ADR-106 §6). In export mode the web data seam reads these files and
fails loud when one is absent; a national build can never reach a DEMO value.

Every file carries the same envelope:

* ``schema`` — the versioned schema id;
* ``as_of`` — the export's as-of snapshot (one ``REPEATABLE READ`` spine state);
* ``denominator`` — a NAMED denominator, never a total (§32, SIG-METRIC-008),
  with ``is_population_total: false``;
* ``source_compartments`` — the licence compartments the inputs were placed in.

Licence posture (ADR-106 §4 applied to this family):

* files carrying only SIG-original *aggregate expression* (counts, degree
  numbers, summaries, the decision-point pick, queue metadata) are labelled
  ``CC-BY-4.0`` and sit in the export's own ``web`` compartment — publishable;
* a file that carries licence-bearing content (the density bins are a coarsened
  derived point set — an ODbL-derived database beside CC-BY points when the
  contributing sites span licences) is labelled with the SPDX ``AND`` of every
  licence it draws on (:func:`~exports.spine_export.surface_license`) and filed
  in the ``web_mixed`` compartment — a restricted build input of the produced-
  work website, never a public download (same posture as ``web/map.json``);
* :func:`assert_analytics_separated` re-proves :func:`~exports.compartments.
  assert_separated` over the emitted set: each compartment holds exactly ONE
  licence label, so a second distinct licence in one compartment (a producer
  bug, or a second mixed file without its own partition) is refused loudly.

Determinism: every producer is a pure function of one snapshot's shaped dataset
+ supplementary raw reads — sorted keys, deterministic tie-breaks, no clocks.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import h3
from policy.licensing import compute_export_license
from policy.rights import RightsRecord

from . import compartments as C
from .shaping import ShapedDataset

# --------------------------------------------------------------------------- #
# Schema ids + the family's compartments                                       #
# --------------------------------------------------------------------------- #

SCHEMA_DENSITY_BINS = "sig/analytics-density-bins/1"
SCHEMA_CENTRALITY = "sig/analytics-centrality/1"
SCHEMA_DECISION_POINT = "sig/analytics-decision-point/1"
SCHEMA_PROVENANCE = "sig/analytics-provenance/1"
SCHEMA_QUEUE_META = "sig/analytics-queue-meta/1"

ANALYTICS_DIR = "web/analytics"
#: The family the surfaces read — the manifest-stable filenames emitted under
#: ``web/analytics/`` (the demo-guarded ``web/presentation/`` is never emitted).
ANALYTICS_FILES = ("density_bins", "centrality", "decision_point", "provenance", "queue_meta")
_WEB_COMPARTMENT = "web"
#: The compartment a non-CC-BY-labelled analytics file lands in — an unregistered
#: (restricted) partition, never the public ``web`` compartment. One file per
#: distinct licence label by construction; a second label in it is a leak
#: ``assert_analytics_separated`` refuses.
_MIXED_COMPARTMENT = "web_mixed"

_SIG_SPDX = "CC-BY-4.0"

#: The H3 resolution of the national-zoom density bins (SIG-GEO-011, §19.5 —
#: H3 via the ``h3`` library, since ``h3-pg`` is not on the test/CI images). Res 3
#: cells average ~12,459 km²: the coarse, honest "national view ≤ zoom 6" bin the
#: map renders (SIG-UI-019). Finer/zoom-aware binning is P31.15 tile work.
DENSITY_H3_RESOLUTION = 3

#: The §12.2 access kinds that form the typed network — the same set the
#: ``web/network.json`` surface emits, so centrality can never disagree with it.
_ACCESS_KINDS = ("configured_access", "observed_use", "declared_policy")


@dataclass(frozen=True)
class AnalyticsArtifact:
    """One emitted ``web/analytics/`` file: path, manifest licence + compartment."""

    path: str
    compartment: str
    license: str
    payload: dict[str, Any]


def _envelope(
    schema: str,
    as_of: str,
    denominator: str,
    source_compartments: Sequence[str],
    **fields: Any,
) -> dict[str, Any]:
    return {
        "schema": schema,
        "as_of": as_of,
        "denominator": denominator,
        # Every counted quantity states it is not a population total (§32.5).
        "is_population_total": False,
        "source_compartments": sorted(source_compartments),
        **fields,
    }


def _compartments_for_licences(
    licences: set[str] | frozenset[str], registry: Mapping[str, Any] | None
) -> list[str]:
    """The compartment names a set of input licences places into (honest labels).

    Each licence is placed the way the export places its rows — a single licence
    computes to its most-constraining relicensable target and lands in the
    compartment declaring it. A licence that computes but has no registered
    compartment is skipped (the file's own ``AND`` label still names it).
    """
    out: set[str] = set()
    for spdx in sorted(licences):
        try:
            record = RightsRecord(
                source_id="analytics-input",
                spdx=spdx,
                attribution="",
                redistributable=True,
                derivative_permitted=True,
                terms_url="",
                retrieval_date=date(1970, 1, 1),
            )
            licence = compute_export_license([record], registry)
            out.add(C.compartment_for_license(licence, None, registry))
        except Exception:  # noqa: BLE001 - an unplaceable licence stays named, not placed
            continue
    return sorted(out)


def _artifact(
    name: str,
    licence: str,
    payload: dict[str, Any],
) -> AnalyticsArtifact:
    """File the artifact: SIG CC-BY → ``web``; anything else → ``web_mixed``."""
    compartment = _WEB_COMPARTMENT if licence == _SIG_SPDX else _MIXED_COMPARTMENT
    return AnalyticsArtifact(
        path=f"{ANALYTICS_DIR}/{name}.json",
        compartment=compartment,
        license=licence,
        payload=payload,
    )


def assert_analytics_separated(artifacts: Sequence[AnalyticsArtifact]) -> None:
    """Re-prove the compartment invariant over the emitted analytics set.

    Runs the same :func:`exports.compartments.assert_separated` the placed
    tables pass — each manifest compartment must hold exactly ONE licence
    label. A mixed-licence file is refused *as a shared compartment member*:
    it carries its own ``AND`` label in ``web_mixed`` (restricted), and a
    producer bug that lands a second distinct licence in one compartment is
    loud, never silently merged.
    """
    placed = [
        C.PlacedTable(
            table=C.ExportTable(name=a.path, rows=(), kind="tabular"),
            compartment=a.compartment,
            license=a.license,
        )
        for a in artifacts
    ]
    C.assert_separated(placed)


# --------------------------------------------------------------------------- #
# 1. Map density bins — tier-0 points only, H3-binned (§19.4/§19.5, SIG-UI-018/019)
# --------------------------------------------------------------------------- #


def _coverage_level(distinct_sources: int) -> str:
    """The honest per-cell "looked-ness" proxy (SIG-UI-018).

    Not a surveyed-area claim: how many DISTINCT named sources contribute to the
    cell — one source is thin coverage, several independent registries searched
    the same ground. A cell is only emitted when ≥1 published point falls in it,
    so "none" never appears (SIG never claims a searched-empty cell it did not
    search).
    """
    if distinct_sources >= 3:
        return "high"
    if distinct_sources == 2:
        return "partial"
    return "low"


def _dominant_jurisdiction(counts: Mapping[str, int]) -> str:
    """The plurality jurisdiction label of a cell (ties → lexically smallest)."""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _density_bins(
    dataset: ShapedDataset,
    *,
    licences_by_subject: Mapping[str, set[str]],
    refused_subjects: frozenset[str] | set[str],
    registry: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """Bin every published tier-0 site point into H3 cells (§19.5, SIG-UI-019).

    Input is the same published point set the map surface draws (tier-0,
    already tier-reduced per §19.4; licence-refused subjects excluded — a cell
    can never contain a refused byte). The bin itself is the only geometry that
    leaves the producer: cell ids, counts, and a coverage proxy — coordinates
    never travel at finer than cell resolution.
    """
    cells: dict[str, dict[str, Any]] = {}
    contributing_licences: set[str] = set()
    n_points = 0
    for site in dataset.sites:
        if site.entity_id in refused_subjects:
            continue
        if site.sensitivity_tier != 0:
            # Part VIII: only tier-0 (fully publishable) points are binned.
            continue
        if site.point_status != "resolved" or site.latitude is None or site.longitude is None:
            continue
        cell = h3.latlng_to_cell(site.latitude, site.longitude, DENSITY_H3_RESOLUTION)
        agg = cells.setdefault(cell, {"count": 0, "sources": set(), "jurisdictions": {}})
        agg["count"] += 1
        agg["sources"].update(site.source_ids)
        j = site.jurisdiction or ""
        agg["jurisdictions"][j] = agg["jurisdictions"].get(j, 0) + 1
        contributing_licences.update(licences_by_subject.get(site.entity_id, ()))
        n_points += 1

    bins = [
        {
            "h3": cell,
            "jurisdiction": _dominant_jurisdiction(agg["jurisdictions"]),
            "deviceCount": agg["count"],
            "coverage": _coverage_level(len(agg["sources"])),
        }
        for cell, agg in sorted(cells.items())
    ]
    # ADR-106 §4: the bin map is a coarsened derived point set — it is labelled
    # with every licence its contributing sites draw on, so a licence-mixed
    # national spine marks it mixed-licence (a restricted build input).
    licence = _surface_license(contributing_licences)
    payload = _envelope(
        SCHEMA_DENSITY_BINS,
        dataset.as_of,
        (
            f"{n_points} published observation-level site records with a releasable "
            "tier-0 point (licence-refused subjects excluded)"
        ),
        _compartments_for_licences(contributing_licences, registry),
        grid="h3",
        h3_resolution=DENSITY_H3_RESOLUTION,
        coverage_rule=(
            "cell coverage = the number of distinct named sources contributing to the "
            "cell: >=3 'high', 2 'partial', 1 'low'; a cell exists only where at least "
            "one published point falls — never a searched-empty claim (SIG-UI-018)"
        ),
        bins=bins,
    )
    return payload, licence


def _surface_license(licences: set[str] | frozenset[str]) -> str:
    """Mirror of ``spine_export.surface_license`` (kept import-cycle-free)."""
    ordered = sorted(licences)
    if not ordered:
        return _SIG_SPDX
    return ordered[0] if len(ordered) == 1 else " AND ".join(ordered)


# --------------------------------------------------------------------------- #
# 2. Network centrality + the ego-focus rule (§39.4, SIG-UI-022/023)
# --------------------------------------------------------------------------- #


def _typed_access_edges(
    materialized_edges: Sequence[Mapping[str, Any]], dataset: ShapedDataset
) -> tuple[list[tuple[str, str]], set[str]]:
    """The same undirected endpoints the ``web/network.json`` surface emits, and
    the ids of the claims that back those edges (for honest source compartments).

    Materialized §29.3 edges when present, else the compute-on-read shaping
    envelope (the honest fallback for an unmaterialized spine, ADR-101/092).
    """
    allowed = set(_ACCESS_KINDS)
    pairs: list[tuple[str, str]] = []
    claim_ids: set[str] = set()
    if materialized_edges:
        for e in materialized_edges:
            if str(e.get("access_kind")) in allowed:
                pairs.append((str(e["from_entity"]), str(e["to_entity"])))
                if e.get("evidence_claim") is not None:
                    claim_ids.add(str(e["evidence_claim"]))
    else:
        for edge in dataset.sharing_edges:
            if edge.access_kind in allowed and edge.partner_ref is not None:
                pairs.append((edge.subject_id, edge.partner_ref))
                claim_ids.add(str(edge.claim_id))
    # Deterministic, de-duplicated undirected edge list.
    seen: set[tuple[str, str]] = set()
    for a, b in pairs:
        if a != b:
            seen.add((a, b) if a <= b else (b, a))
    return sorted(seen), claim_ids


_ER_DISCLOSURE = (
    "Undirected degree over the exported typed sharing-edge graph; the edge "
    "endpoints are spine entities minted by deterministic identity resolution, "
    "so this figure does not rest on the probabilistic camera-site ER eval — "
    "it is exact for the exported graph and never an estimate."
)


def _centrality(
    dataset: ShapedDataset,
    materialized_edges: Sequence[Mapping[str, Any]],
    *,
    weight_rows: Sequence[Mapping[str, Any]] = (),
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Degree centrality over the typed access network + the ego-focus pick.

    The declared measure (ADR-R9-ANALYTICS): **undirected degree** — the count
    of typed access edges incident on the entity — over the SAME edge set the
    network surface renders. The focus entity is the highest-degree node; ties
    resolve to the lexically smallest entity id (deterministic, stated in the
    file).
    """
    pairs, claim_ids = _typed_access_edges(materialized_edges, dataset)
    licences = {r["spdx"] for r in weight_rows if r["claim_id"] in claim_ids and r["spdx"]}
    degree: Counter[str] = Counter()
    for src, dst in pairs:
        degree[src] += 1
        degree[dst] += 1
    statistics = [
        {
            "node_id": node,
            "metric": "degree",
            "value": deg,
            # SIG-UI-023: every statistic carries its resolution-dependence
            # statement INLINE. This edge set does not rest on the probabilistic
            # camera-site ER eval, so there is no measured ER quality to cite —
            # the disclosure says so rather than inventing numbers.
            "er_quality": None,
            "disclosure": _ER_DISCLOSURE,
        }
        for node, deg in sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    focus_entity: str | None = str(statistics[0]["node_id"]) if statistics else None
    payload = _envelope(
        SCHEMA_CENTRALITY,
        dataset.as_of,
        (
            f"{len(pairs)} typed access edges between {len(degree)} entities in the "
            "exported sharing network"
        ),
        _compartments_for_licences(licences, registry),
        measure=(
            "undirected degree over the typed access edges "
            f"({', '.join(_ACCESS_KINDS)}) the web/network.json surface emits"
        ),
        statistics=statistics,
        focus={
            "entity_id": focus_entity,
            "degree": degree.get(focus_entity) if focus_entity else None,
            "rule": (
                "the entity with the highest undirected degree over the typed "
                "access edges; ties resolve to the lexically smallest entity id"
            ),
        },
    )
    return payload


# --------------------------------------------------------------------------- #
# 3. The watch's tracked decision point (§39.5/§39.5a, SIG-UI-014b)
# --------------------------------------------------------------------------- #


def _next_decision_date(termination: Mapping[str, Any]) -> str | None:
    """The SIG-UI-014b decision date, mirroring the web's ``nextDecisionDate``
    (``web/src/lib/dossier.ts``) so the analytics artifact can never drift from
    the derivation the watch and dossier render.

    No expiry → no derivable decision date; an auto-renewing contract with a
    notice window → expiry minus the window (whole days); otherwise the decision
    must be taken by the expiry itself.
    """
    expiry = termination.get("expiry_date")
    if not expiry:
        return None
    try:
        expiry_d = date.fromisoformat(str(expiry)[:10])
    except (ValueError, TypeError):
        return None
    window = termination.get("notice_window_days")
    if termination.get("auto_renews") and window is not None:
        try:
            return (expiry_d - timedelta(days=int(window))).isoformat()
        except (ValueError, TypeError):
            return expiry_d.isoformat()
    return expiry_d.isoformat()


def _decision_point(
    dataset: ShapedDataset, raw: Mapping[str, Any], registry: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The single tracked decision the evidence recommender ranks for.

    Rule (stated in the file): the earliest derivable ``next_decision_date``
    across the renewal watch — expiry minus the notice window for an
    auto-renewing contract, else the expiry itself (SIG-UI-014b); ties resolve
    to the smallest subject key. ``null`` when no watch item carries a derivable
    date (honest "none tracked", never a fabricated urgency).
    """
    candidates: list[tuple[str, str, dict[str, Any]]] = []
    n_watch = 0
    for row in raw.get("contract_watch") or []:
        if not isinstance(row, Mapping):
            continue
        n_watch += 1
        termination = row.get("termination") or {}
        decision = _next_decision_date(termination)
        if decision is None:
            continue
        subject = str(
            row.get("subject_id") or row.get("contract_id") or row.get("subject_label") or ""
        )
        candidates.append(
            (
                decision,
                subject,
                {
                    "decision_type": "renewal",
                    "subject_id": subject,
                    "label": str(row.get("subject_label") or row.get("contract_id") or subject),
                    "date": decision,
                },
            )
        )
    point = sorted(candidates, key=lambda c: (c[0], c[1]))[0][2] if candidates else None
    return _envelope(
        SCHEMA_DECISION_POINT,
        dataset.as_of,
        f"{n_watch} contracts on the renewal watch",
        (),
        rule=(
            "the earliest derivable next_decision_date across the watch "
            "(expiry minus notice_window_days for an auto-renewing contract, "
            "else the expiry itself — SIG-UI-014b); ties resolve to the "
            "smallest subject key"
        ),
        decision_point=point,
    )


# --------------------------------------------------------------------------- #
# 4. Per-surface provenance summaries + evidence tiers (SIG-UI-044, §10.6)
# --------------------------------------------------------------------------- #


def _tier_distribution(weight_rows: Sequence[Mapping[str, Any]], as_of: date) -> dict[str, int]:
    """Count the publishable claims per composed weight class W4…W0 (§10.6).

    ``weight_rows`` are the ``claim_weights`` read: (source_reliability,
    claim_directness, artifact_integrity, observed_at, predicate_id). Currency
    is derived per predicate registry half-life at ``as_of`` (§28.3, never
    stored). A claim that cannot be honestly weighted — D6 non-probative, a
    missing axis value, an unknown predicate registry row — is counted
    ``untiered``, never silently assigned a weight.
    """
    from reconcile.weight import currency, predicate_meta, weight_class

    dist: Counter[str] = Counter()
    for row in weight_rows:
        reliability = str(row.get("source_reliability") or "")
        directness = str(row.get("claim_directness") or "")
        integrity = str(row.get("artifact_integrity") or "")
        observed = row.get("observed_at")
        predicate_id = str(row.get("predicate_id") or "")
        if observed is None:
            dist["untiered"] += 1
            continue
        observed_d = observed.date() if isinstance(observed, datetime) else observed
        if not isinstance(observed_d, date):
            dist["untiered"] += 1
            continue
        try:
            meta = predicate_meta(predicate_id)
            cur = currency(
                volatility_class=str(meta.get("volatility_class", "")),
                half_life=str(meta.get("half_life", "")),
                observed_at=observed_d,
                as_of=as_of,
            )
            w = weight_class(
                reliability=reliability,
                directness=directness,
                integrity=integrity,
                currency=cur,
            )
        except Exception:  # noqa: BLE001 - unweightable (D6/unknown code) → honest bucket
            dist["untiered"] += 1
            continue
        dist[f"W{w}"] += 1
    return dict(sorted(dist.items()))


def _date_range(
    rows: Sequence[Mapping[str, Any]], key: str = "observed_at"
) -> dict[str, str] | None:
    """The earliest/latest evidence dates over dated rows, or ``None`` (honest)."""
    dates: list[str] = []
    for row in rows:
        v = row.get(key)
        if v is None:
            continue
        iso = v.isoformat() if hasattr(v, "isoformat") else str(v)
        dates.append(iso[:10])
    if not dates:
        return None
    return {"earliest": min(dates), "latest": max(dates)}


def _claim_weight_rows(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalise the ``claim_weights`` supplementary read into dicts."""
    out: list[dict[str, Any]] = []
    for r in raw.get("claim_weights") or []:
        # (claim_id, source_id, predicate_id, source_reliability, claim_directness,
        #  artifact_integrity, observed_at, spdx)
        out.append(
            {
                "claim_id": str(r[0]),
                "source_id": str(r[1]) if r[1] is not None else "",
                "predicate_id": str(r[2]),
                "source_reliability": str(r[3]),
                "claim_directness": str(r[4]),
                "artifact_integrity": str(r[5]),
                "observed_at": r[6],
                "spdx": str(r[7]) if len(r) > 7 and r[7] is not None else "",
            }
        )
    return out


def _provenance(
    dataset: ShapedDataset,
    raw: Mapping[str, Any],
    *,
    weight_rows: Sequence[Mapping[str, Any]],
    ruleset_version: str,
    human_reviewed: bool,
    registry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The three per-surface "How we know this" summaries (SIG-UI-044).

    * **site** — the W-tier distribution over every publishable claim backing
      the exported surfaces, the published evidence artifacts, the distinct
      named sources, the dated-observation range, the ruleset, and the honest
      human-review posture.
    * **corrections** — the same over the correction/retraction claim rows.
    * **research_queue** — tasks are detector outputs, not weighted claims:
      counted honestly as ``untiered`` units with the detector set named.
    """
    as_of = date.fromisoformat(dataset.as_of[:10]) if dataset.as_of else date.today()
    corrections_rows = list(raw.get("corrections") or [])
    correction_ids = {str(r[0]) for r in corrections_rows}
    task_rows = list(raw.get("research_tasks") or [])
    artifact_rows = list(raw.get("evidence_artifacts") or [])

    site = {
        "artifact_count": len(artifact_rows),
        "tier_distribution": _tier_distribution(weight_rows, as_of),
        "source_independence_count": len({r["source_id"] for r in weight_rows if r["source_id"]}),
        "date_range": _date_range(weight_rows),
        "rules_applied": [ruleset_version],
        "human_review_status": "partially_reviewed" if human_reviewed else "unreviewed",
        "denominator": (
            f"{len(weight_rows)} publishable tier-0 claims carrying the epistemic "
            "axes (reliability/directness/integrity/observed_at)"
        ),
    }
    correction_weights = [r for r in weight_rows if r["claim_id"] in correction_ids]
    corrections = {
        "artifact_count": len(corrections_rows),
        "tier_distribution": _tier_distribution(correction_weights, as_of)
        or {"untiered": len(corrections_rows)},
        "source_independence_count": len(
            {r["source_id"] for r in correction_weights if r["source_id"]}
        ),
        "date_range": _date_range(
            [{"observed_at": r[7]} for r in corrections_rows], key="observed_at"
        ),
        "rules_applied": [ruleset_version],
        "human_review_status": "unreviewed",
        "denominator": f"{len(corrections_rows)} correction/retraction claim rows (§39.8)",
    }
    detectors = sorted({str(r[8]) for r in task_rows if len(r) > 8 and r[8]})
    research_queue = {
        "artifact_count": len(task_rows),
        # Tasks are detector outputs — no §10.6 weight applies. Counted honestly
        # as untiered units rather than assigned a weight they do not carry.
        "tier_distribution": {"untiered": len(task_rows)} if task_rows else {"untiered": 0},
        "source_independence_count": len(detectors),
        "date_range": None,
        "rules_applied": [*detectors, ruleset_version],
        "human_review_status": "unreviewed",
        "denominator": f"{len(task_rows)} research tasks (§39.7 detector outputs)",
    }
    licences = {r["spdx"] for r in weight_rows if r["spdx"]}
    return _envelope(
        SCHEMA_PROVENANCE,
        dataset.as_of,
        (
            f"{len(weight_rows)} publishable tier-0 claims carrying the epistemic "
            "axes (reliability/directness/integrity/observed_at)"
        ),
        _compartments_for_licences(licences, registry),
        ruleset_version=ruleset_version,
        surfaces={"site": site, "corrections": corrections, "research_queue": research_queue},
    )


# --------------------------------------------------------------------------- #
# 5. Research-queue metadata (§33.5/§39.7)
# --------------------------------------------------------------------------- #


def _queue_meta(dataset: ShapedDataset, raw: Mapping[str, Any]) -> dict[str, Any]:
    """The queue's render as-of + live jurisdiction claims.

    ``jurisdiction_claims`` is honestly EMPTY on the spine export: a §33.5
    jurisdiction claim is community-curation state (a local group claiming a
    jurisdiction), which the claim spine does not record today — never a
    fabricated list.
    """
    tasks = list(raw.get("research_tasks") or [])
    return _envelope(
        SCHEMA_QUEUE_META,
        dataset.as_of,
        (
            f"{len(tasks)} research tasks; jurisdiction claims are community-curation "
            "state the claim spine does not carry"
        ),
        (),
        queue_as_of=dataset.as_of[:10],
        jurisdiction_claims=[],
    )


# --------------------------------------------------------------------------- #
# The producer entry point                                                     #
# --------------------------------------------------------------------------- #


def build_analytics(
    dataset: ShapedDataset,
    raw: Mapping[str, Any],
    *,
    licences_by_subject: Mapping[str, set[str]],
    refused_subjects: frozenset[str] | set[str],
    materialized_edges: Sequence[Mapping[str, Any]] = (),
    materialized_site_runs: Sequence[Mapping[str, Any]] = (),
    ruleset_version: str = "",
    registry: Mapping[str, Any] | None = None,
) -> list[AnalyticsArtifact]:
    """Emit the ``web/analytics/`` family for one shaped snapshot (pure).

    Deterministic for the snapshot: every payload is a sorted/canonicalised
    function of the shaped dataset + supplementary reads. The licence label is
    computed per file the same way ``web/map.json`` is labelled (ADR-106 §4):
    a single licence → that id; several → the sorted ``AND`` expression, filed
    in ``web_mixed`` (restricted); an empty licence set → SIG CC-BY-4.0.
    :func:`assert_analytics_separated` then proves no compartment holds two
    licence labels.
    """
    human_reviewed = False
    if materialized_site_runs:
        review = (materialized_site_runs[0].get("summary") or {}).get("human_review") or {}
        human_reviewed = int(review.get("verdict_pairs") or 0) > 0

    density_payload, density_licence = _density_bins(
        dataset,
        licences_by_subject=licences_by_subject,
        refused_subjects=refused_subjects,
        registry=registry,
    )
    weight_rows = _claim_weight_rows(raw)
    artifacts = [
        _artifact("density_bins", density_licence, density_payload),
        _artifact(
            "centrality",
            _SIG_SPDX,
            _centrality(
                dataset,
                materialized_edges,
                weight_rows=weight_rows,
                registry=registry,
            ),
        ),
        _artifact("decision_point", _SIG_SPDX, _decision_point(dataset, raw, registry)),
        _artifact(
            "provenance",
            _SIG_SPDX,
            _provenance(
                dataset,
                raw,
                weight_rows=weight_rows,
                ruleset_version=ruleset_version,
                human_reviewed=human_reviewed,
                registry=registry,
            ),
        ),
        _artifact("queue_meta", _SIG_SPDX, _queue_meta(dataset, raw)),
    ]
    assert_analytics_separated(artifacts)
    return artifacts


__all__ = [
    "ANALYTICS_DIR",
    "ANALYTICS_FILES",
    "DENSITY_H3_RESOLUTION",
    "SCHEMA_CENTRALITY",
    "SCHEMA_DECISION_POINT",
    "SCHEMA_DENSITY_BINS",
    "SCHEMA_PROVENANCE",
    "SCHEMA_QUEUE_META",
    "AnalyticsArtifact",
    "assert_analytics_separated",
    "build_analytics",
]
