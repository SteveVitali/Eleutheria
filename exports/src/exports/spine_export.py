# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The spine-backed national export bundle (P27.4, LAUNCH.4).

`sig-exports build --from-spine --dsn <dsn>` reads the shaped spine (P27.3) and
emits a real, national export bundle — replacing the hardcoded okc/france fixture
requests — carrying every artifact the ten public surfaces consume, to the frozen
P27.1 contracts, so the static site is the real graph "by construction" (§38.1,
SIG-EXPORT-012).

The invariants this module never relaxes (all inherited from §38/§42):

* **Read, never mutate.** :func:`run_spine_export` opens a single
  ``REPEATABLE READ READ ONLY`` snapshot, runs shaping AND the supplementary reads
  inside it, and closes it — no ``value_geom``/``resolution`` write, no
  ``UPDATE``/``DELETE`` anywhere.
* **Licence compartments never merged; the gate fails closed.** Every site is
  licence-sliced per ``(source, rights_id)`` pair, each slice's observation
  envelope recomputed from *that source's own* observations (never a silent
  cross-source merge), and placed in the compartment its own computed licence
  declares. A refused record (``UNDETERMINED`` / non-redistributable /
  derivative-forbidden / recorded-exclusion) is dropped **loudly** into the
  exclusions report, never co-mingled. :func:`exports.compartments.assert_separated`
  holds by construction (each compartment file is one licence), so the ODbL layer
  ships physically apart from the CC-BY graph (SIG-EXPORT-005 / §42.3).
* **Every row carries rights provenance (SIG-EXPORT-006).** The bundle rows go
  through :func:`exports.compartments.enrich_rows`, stamping each with its
  downstream attribution/provenance obligation.
* **Never a bare total (§32).** Coverage metrics carry named denominators and
  ``is_population_total: false`` (they come straight from the P27.3 shaping layer,
  which owns that invariant).
* **Honest absence.** A public surface whose spine tables are empty emits ``[]`` /
  a zeroed report — never a fabricated row.

The pure assembler :func:`build_spine_export` builds the :class:`SpineExport` from
an already-shaped :class:`~exports.shaping.ShapedDataset` plus (optionally) the
parsed shaping claims and the supplementary raw reads — unit-testable with no
database. :func:`run_spine_export` is the thin executor that opens the snapshot.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from inference.accountability import read_materialized_accountability_links
from inference.materialize import read_materialized_coverage
from policy.licensing import (
    compute_export_license,
    export_refusal_reason,
)
from policy.rights import RightsRecord
from reconcile.materialize import (
    read_materialized_contradictions,
    read_materialized_edges,
    read_materialized_resolutions,
)
from resolution.camera_sites_pg import read_resolved_site_runs

from . import analytics, provo
from . import compartments as C
from .audit import _EFFECTIVE_CTE
from .bundle import Bundle, build_bundle
from .manifest import Artifact, BuildSpec, Manifest, canonical_json, sha256_hex
from .shaping import (
    LAT_PREDICATE,
    LON_PREDICATE,
    SHAPING_SCHEMA_VERSION,
    ShapedDataset,
    ShapedSite,
    ShapingClaim,
    parse_shaping_claims,
    shape_sites,
)
from .tiles import ODBL_ATTRIBUTION, render_pmtiles_file

#: The SIG-original derived record: coverage/jurisdiction/freshness/dossier framings
#: are SIG's own analytical expression, published CC-BY-4.0 (SIG-LIC-005). The
#: licence-bearing GEOMETRY (sites) is sliced per source instead — this record only
#: governs the derived aggregate/framing tables.
_SIG_SOURCE_ID = "sig"
_SIG_SPDX = "CC-BY-4.0"
_SIG_ATTRIBUTION = "© The SIG project — CC-BY-4.0"
_SIG_TERMS_URL = "https://creativecommons.org/licenses/by/4.0/"

#: Where the web-consumption JSON bytes live inside the bundle (the static site is
#: built from these — the same posture as the P21.4 ``web/dossiers.json``).
_WEB_DIR = "web"
_WEB_COMPARTMENT = "web"
_META_COMPARTMENT = "metadata"

#: The twelve dossier sections (§39.2). Order is the canonical render order.
_DOSSIER_SECTIONS: tuple[str, ...] = (
    "at_a_glance",
    "what_is_deployed",
    "cost_and_expiry",
    "who_else_can_see",
    "configuration_and_retention",
    "usage",
    "where_the_hardware_is",
    "policy",
    "accountability_events",
    "timeline",
    "what_we_dont_know",
    "how_we_know_this",
)


# --------------------------------------------------------------------------- #
# Supplementary read-only query set (compat-guarded like shaping._queries_for) #
# --------------------------------------------------------------------------- #

#: The supplementary read-only SELECTs run inside the caller's shaping snapshot.
#: Each is keyed on a table that a pre-P27.2 / partial spine may not have, so every
#: one is guarded by ``to_regclass`` before it runs; a missing table is honest
#: absence (an empty surface), never a fabricated row.
EXPORT_QUERIES: dict[str, tuple[str, str]] = {
    # (guard-table, SELECT). source_registry names — node labels + PROV agents.
    "source_names": (
        "source_registry",
        "SELECT source_id, name FROM source_registry ORDER BY source_id",
    ),
    # entity_identifier labels — sharing-edge partner display names.
    "entity_labels": (
        "entity_identifier",
        "SELECT entity_id::text, scheme, value FROM entity_identifier ORDER BY entity_id, scheme",
    ),
    # research_task rows (§39.7) — the research queue surface. The trailing
    # trigger_kind/trigger_ref (P29.2) cite what made each task's detector fire (the
    # materialized contradiction/coverage/relationship); a pre-P29.2 spine lacks the
    # columns, so the query raises and fetch_export_raw degrades it to [] honestly.
    "research_tasks": (
        "research_task",
        "SELECT task_id::text, task_type, subject_id::text, jurisdiction_id::text, priority,"
        "       status, disposition, closing_condition, detector_version,"
        "       trigger_kind, trigger_ref"
        "  FROM research_task ORDER BY priority DESC, task_id",
    ),
    # publishable evidence_artifact metadata (§39.6) — the evidence surface. Bytes
    # never travel; sealed captures stay metadata-only (§17.5).
    "evidence_artifacts": (
        "evidence_artifact",
        "SELECT artifact_id::text, source_id, title, artifact_type, stable_locator,"
        "       primary_or_secondary, capture_status, published_at_edtf"
        "  FROM evidence_artifact"
        " WHERE sensitivity_tier = 0 AND capture_status = 'captured'"
        " ORDER BY artifact_id",
    ),
    # correction claims (§39.8) — new rows with revises_claim / retraction_of; the
    # prior value stays citable at its belief-time (history never rewritten).
    "corrections": (
        "claim",
        "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id, c.raw_value,"
        "       c.correction_reason, c.revises_claim::text, c.retraction_of::text,"
        "       lower(c.sys_period)"
        "  FROM claim c"
        " WHERE (c.revises_claim IS NOT NULL OR c.retraction_of IS NOT NULL)"
        "   AND c.sensitivity_tier = 0 AND upper_inf(c.sys_period)"
        " ORDER BY c.claim_id",
    ),
    # publishable tier-0 claims with the §10.4-§10.6 epistemic axes — the input
    # the web/analytics/provenance.json evidence-tier (W4..W0, §10.6) producer
    # weights (P31.14 / ADR-R9-ANALYTICS). Effective rights apply, so a licence-
    # refused claim never pads the "How we know this" distribution.
    "claim_weights": (
        "claim",
        _EFFECTIVE_CTE
        + "SELECT c.claim_id::text, cs.source_id, c.predicate_id, c.source_reliability,"
        "       c.claim_directness, c.artifact_integrity, c.observed_at, rr.spdx_expression"
        "  FROM claim c"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND rr.redistributable = 'yes'"
        " ORDER BY c.claim_id",
    ),
}


def fetch_export_raw(cur: Any, *, belief: datetime | None = None) -> dict[str, Any]:
    """Fetch every supplementary export query inside the caller's transaction.

    Read-only and snapshot-consistent: the caller runs this inside the SAME
    ``REPEATABLE READ READ ONLY`` snapshot as shaping, so every emitted artifact
    describes one spine state. Each query is guarded by ``to_regclass`` — a spine
    missing a table yields an empty result (honest absence), never an error.

    ``belief`` is accepted for symmetry with shaping; the supplementary tables the
    launch surfaces read are not belief-partitioned today, so it is currently
    unused here (the shaping half already pins the belief instant).
    """
    del belief  # symmetry with shaping.fetch_shaping_raw; unused for these reads
    raw: dict[str, Any] = {}
    for key, (guard, sql) in EXPORT_QUERIES.items():
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (guard,))
        row = cur.fetchone()
        if not (row and row[0]):
            raw[key] = []
            continue
        try:
            cur.execute(sql)
            raw[key] = cur.fetchall()
        except Exception:  # noqa: BLE001 - a schema-shape mismatch is honest absence
            raw[key] = []
    return raw


# --------------------------------------------------------------------------- #
# The materialized graph (P28.1-P28.4, ADR-101) — read inside the SAME         #
# snapshot, degrading HONESTLY to [] when the tables are empty/absent.         #
# --------------------------------------------------------------------------- #

#: The materialized-graph seams the P28.5 surface reads, keyed by the table whose
#: ``input_digest`` column the materializer added. Each read is guarded by that
#: column's existence (a pre-P28 spine lacks it) and wrapped so a schema mismatch
#: is honest absence (``[]``) — never a crash, never a fabricated row (ADR-101).
_MATERIALIZED_SEAMS: tuple[tuple[str, str, Any], ...] = (
    ("materialized_resolutions", "resolution", read_materialized_resolutions),
    # P30.2b (ADR-105) — the latest completed camera-site ER run: the auto-written same-device
    # edges the resolved-site metric clusters (N of M), never a §28 value decision.
    ("materialized_site_runs", "camera_site_match", read_resolved_site_runs),
    ("materialized_edges", "relationship", read_materialized_edges),
    ("materialized_contradictions", "contradiction", read_materialized_contradictions),
    ("materialized_coverage", "coverage_record", read_materialized_coverage),
    # P28.6 — the L4 accountability links (in the inference.derived_fact table); the
    # read seam filters to accountability_link:* rows so only governance-chain links load.
    (
        "materialized_accountability_links",
        "derived_fact",
        read_materialized_accountability_links,
    ),
)


def _has_materialize_column(cur: Any, table: str) -> bool:
    """True iff ``table`` exists AND carries the materializer's ``input_digest`` column.

    A cheap, non-erroring probe (``information_schema`` returns 0 rows for a missing
    table/column) so it never poisons the caller's open read-only snapshot — the guard
    that lets a pre-P28 spine degrade to honest absence rather than aborting the read.
    """
    cur.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = 'input_digest')",
        (table,),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def fetch_materialized_graph(cur: Any) -> dict[str, list[dict[str, Any]]]:
    """Read the four materialized-graph tables inside the caller's read-only snapshot.

    Consumes the P28.1-P28.4 read seams (``reconcile.materialize`` /
    ``inference.materialize`` — SIG-ENG-035, never re-implemented). Runs on the caller's OWN
    cursor (the same open ``REPEATABLE READ READ ONLY`` snapshot the shaping reads use — a
    psycopg ``cursor.execute(...)`` returns the cursor, so the seams' ``conn.execute(...).
    fetchall()`` shape is satisfied). Every read is guarded by the materializer's
    ``input_digest`` column and wrapped in ``try`` so a spine whose materialized tables are
    empty or pre-P28 yields ``[]`` — the honest degraded state the hosted spine is in until the
    deferred hosted materialization runs (D-R6.5-SURFACE), never a crash and never a fabricated
    resolved-site count.
    """
    out: dict[str, list[dict[str, Any]]] = {key: [] for key, _table, _seam in _MATERIALIZED_SEAMS}
    for key, table, seam in _MATERIALIZED_SEAMS:
        if not _has_materialize_column(cur, table):
            continue
        try:
            out[key] = list(seam(cur))
        except Exception:  # noqa: BLE001 - a schema mismatch is honest absence, not a crash
            out[key] = []
    return out


# --------------------------------------------------------------------------- #
# The built export                                                            #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SpineExport:
    """A built national export: the licence-compartmented bundle plus web bytes.

    ``bundle`` is the §38 licence-computed release (compartmented data tables,
    Frictionless package, per-artifact manifest). ``web_artifacts`` are the ten
    P27.1-contract JSONs (+ per-compartment PMTiles) the static site consumes.
    ``provenance`` is the PROV-O lineage (§21.6). ``exclusions`` is the loud
    refused-record report. ``manifest`` EXTENDS the bundle manifest with the web
    artifacts + provenance + exclusions, each with its checksum/compartment/licence.
    """

    bundle: Bundle
    web_artifacts: dict[str, bytes]
    provenance: bytes
    exclusions: dict[str, Any]
    manifest: Manifest
    tile_renderers: dict[str, str] = field(default_factory=dict)

    def write_to(self, out_dir: Path | str) -> Path:
        """Materialise the whole export under ``out_dir`` (deterministic bytes)."""
        root = Path(out_dir)
        # 1) the compartmented bundle data tables + descriptors.
        for path, data in self.bundle.artifact_bytes.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        # 2) the web-consumption JSONs (+ tiles) and the PROV-O lineage.
        for path, data in self.web_artifacts.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (root / "provenance.ttl").write_bytes(self.provenance)
        (root / "exclusions.json").write_bytes(
            canonical_json(self.exclusions),
        )
        # 3) the EXTENDED manifest (bundle + web + provenance + exclusions).
        (root / "manifest.json").write_bytes(self.manifest.to_bytes())
        return root

    def summary(self) -> dict[str, Any]:
        """A deterministic build summary for the CLI (no timestamps of its own)."""
        return {
            "release_id": self.bundle.build_spec.release_id(),
            "concept_id": self.bundle.build_spec.concept_id(),
            "artifact_count": len(self.manifest.artifacts),
            "licenses": sorted(self.manifest.licenses()),
            "compartments": sorted({a.compartment for a in self.manifest.artifacts}),
            "web_artifacts": sorted(self.web_artifacts),
            "tiles": dict(sorted(self.tile_renderers.items())),
            "excluded_slices": self.exclusions["totals"]["refused_slices"],
            "excluded_rows": self.exclusions["totals"]["refused_rows"],
        }


# --------------------------------------------------------------------------- #
# Pure helpers                                                                 #
# --------------------------------------------------------------------------- #


def _record_from_site_rights(r: Mapping[str, Any], *, retrieval: date) -> RightsRecord:
    """A :class:`RightsRecord` from one of a site's effective-rights dicts."""
    return RightsRecord(
        source_id=str(r["source_id"]),
        spdx=str(r["spdx"]),
        attribution=str(r.get("attribution", "")),
        redistributable=str(r.get("redistributable")) == "yes",
        derivative_permitted=str(r.get("derivative_permitted")) == "yes",
        terms_url=str(r.get("terms_url", "")),
        retrieval_date=retrieval,
    )


def _sig_record(retrieval: date) -> RightsRecord:
    """The SIG-original CC-BY-4.0 record governing the derived framing tables."""
    return RightsRecord(
        source_id=_SIG_SOURCE_ID,
        spdx=_SIG_SPDX,
        attribution=_SIG_ATTRIBUTION,
        redistributable=True,
        derivative_permitted=True,
        terms_url=_SIG_TERMS_URL,
        retrieval_date=retrieval,
    )


def _site_row_data(site: ShapedSite, rights: Mapping[str, Any]) -> dict[str, Any]:
    """The per-(site, source, rights) export row — geometry + provenance keys."""
    geometry: dict[str, Any] | None = None
    if site.latitude is not None and site.longitude is not None:
        geometry = {"type": "Point", "coordinates": [site.longitude, site.latitude]}
    return {
        "entity_id": site.entity_id,
        "entity_type": site.entity_type,
        "label": site.label,
        "jurisdiction": site.jurisdiction,
        "tier": site.sensitivity_tier,
        "precision": site.precision,
        "point_status": site.point_status,
        "n_observation_claims": site.n_observation_claims,
        "n_sources": site.n_sources,
        "source_id": str(rights["source_id"]),
        "rights_id": str(rights["rights_id"]),
        "spdx": str(rights["spdx"]),
        "claim_ids": list(site.claim_ids),
        "geometry": geometry,
    }


@dataclass(frozen=True)
class _SiteSlices:
    """The licence-sliced sites: per-compartment rows, the rights index, the loud exclusions,
    and — per subject — the licences its PUBLISHED slices carry plus the subjects with any
    REFUSED slice (ADR-106: the render surfaces never carry a refused subject, and a surface
    drawing on several licences is labelled with all of them)."""

    rows_by_compartment: dict[str, list[C.ExportRow]]
    index: dict[str, RightsRecord]
    exclusions: list[dict[str, Any]]
    licences_by_subject: dict[str, set[str]]
    refused_subjects: set[str]


def _slice_sites(
    claims: Sequence[ShapingClaim],
    entity_types: Mapping[str, str],
    *,
    retrieval: date,
    registry: Mapping[str, Any] | None,
) -> _SiteSlices:
    """Licence-slice every site per (source, rights_id) into per-compartment rows.

    Each source's sites are recomputed from *that source's own* observations
    (``shape_sites`` over the per-source claim subset — never a silent cross-source
    merge, so a per-slice envelope reflects only what that source observed). A
    refused (source, rights) slice is dropped into the exclusions list, loudly; a
    surviving slice lands in the compartment its own computed licence declares.
    """
    by_source: dict[str, list[ShapingClaim]] = {}
    rights_ids_by_source: dict[str, set[str]] = {}
    for claim in claims:
        if claim.publishable and claim.source_id:
            by_source.setdefault(claim.source_id, []).append(claim)
            rights_ids_by_source.setdefault(claim.source_id, set()).add(claim.effective_rights_id)
    # A source whose claims carry MORE THAN ONE effective rights record (e.g. a DOT feed with
    # some rows CC0 and some decision-resolved to a public-record basis) is keyed per
    # (source, rights_id) slice, so each slice is placed + attributed by ITS OWN record and
    # two licences are never computed into one compartment file (SIG-LIC-004a). A
    # single-rights source keeps its plain source id (the common case, unchanged).
    multi_rights = {s for s, ids in rights_ids_by_source.items() if len(ids) > 1}

    rows_by_compartment: dict[str, list[C.ExportRow]] = {}
    index: dict[str, RightsRecord] = {}
    refused: dict[tuple[str, str, str], dict[str, Any]] = {}
    licences_by_subject: dict[str, set[str]] = {}
    refused_subjects: set[str] = set()

    for source_id in sorted(by_source):
        sites = shape_sites(by_source[source_id], entity_types=entity_types)
        for site in sites:
            for rights in site.rights:
                record = _record_from_site_rights(rights, retrieval=retrieval)
                reason = export_refusal_reason(record, registry)
                if reason is not None:
                    key = (record.source_id, str(rights["rights_id"]), reason)
                    entry = refused.setdefault(
                        key,
                        {
                            "surface": "sites",
                            "source_id": record.source_id,
                            "rights_id": str(rights["rights_id"]),
                            "spdx": record.spdx,
                            "reason": reason,
                            "rows": 0,
                        },
                    )
                    entry["rows"] = int(entry["rows"]) + 1
                    refused_subjects.add(site.entity_id)
                    continue
                licence = compute_export_license([record], registry)
                compartment = C.compartment_for_license(licence, None, registry)
                licences_by_subject.setdefault(site.entity_id, set()).add(licence)
                slice_key = (
                    f"{record.source_id}@{rights['rights_id']}"
                    if record.source_id in multi_rights
                    else record.source_id
                )
                rows_by_compartment.setdefault(compartment, []).append(
                    C.ExportRow(source_id=slice_key, data=_site_row_data(site, rights))
                )
                index.setdefault(slice_key, replace(record, source_id=slice_key))
    exclusions = [refused[k] for k in sorted(refused)]
    return _SiteSlices(
        rows_by_compartment=rows_by_compartment,
        index=index,
        exclusions=exclusions,
        licences_by_subject=licences_by_subject,
        refused_subjects=refused_subjects,
    )


def surface_license(licences: set[str] | frozenset[str]) -> str:
    """The honest licence label of a render surface drawing on ``licences`` (ADR-106).

    One licence → that id. Several → an SPDX ``AND`` expression (sorted, deterministic),
    which marks the file a MIXED-LICENCE artifact: the public-cut-over classifier keeps it
    out of every public object (it is a build input of the produced-work website, never a
    downloadable dataset — the per-licence compartments are the downloads). No licence (an
    empty surface) → SIG's own CC-BY-4.0.
    """
    ordered = sorted(licences)
    if not ordered:
        return _SIG_SPDX
    return ordered[0] if len(ordered) == 1 else " AND ".join(ordered)


# --------------------------------------------------------------------------- #
# The ten P27.1-contract web surfaces                                         #
# --------------------------------------------------------------------------- #


def _as_of_echo(as_of: str, belief: datetime | None) -> dict[str, Any]:
    return {
        "as_of_world": as_of[:10],
        "as_of_belief": belief.date().isoformat() if belief is not None else as_of[:10],
        "belief_pinned": belief is not None,
    }


#: The §32.5 population-note every counted quantity carries: the true population is
#: unknown, so no figure is a total (SIG-METRIC-008/010).
_POPULATION_NOTE = (
    "The true population of surveillance devices is unknown. These are recorded "
    "observations from named sources — an inventory, not a census or an estimate "
    "(SIG-METRIC-008)."
)

#: The provisional-eval disclosure the resolved-site framing carries until D-R6.1-EVAL
#: closes (ADR-101 §3): a "resolved sites" claim rests on a provisional (LLM-bootstrap)
#: eval, and the surface says so.
_RESOLVED_EVAL_DISCLOSURE = (
    " Resolution rests on a provisional eval (LLM-bootstrapped gold set; D-R6.1-EVAL, OPEN)."
)

#: ``inference.completeness.CompletenessMethod`` → the web ``metrics.ts#CoverageMetricKind``.
#: A 1:1 map (both are the four §32.5 legitimate kinds); a value outside it degrades to a
#: counted quantity rather than fabricating a kind.
_COMPLETENESS_TO_KIND: dict[str, str] = {
    "counted_with_denominator": "counted_quantity",
    "records_derived_bounds": "records_derived_bound",
    "reconciliation_ratio": "reconciliation_ratio",
    "measured_survey_recall": "survey_recall",
}


def _fmt_count(value: Any) -> str:
    """A whole-number-or-decimal count formatter for a metric phrase."""
    if value is None:
        return "0"
    f = float(value)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def coverage_metric_from_materialized(row: Mapping[str, Any]) -> dict[str, Any] | None:
    """Map one materialized ``coverage_record`` metric row → a web ``CoverageMetric`` (§32.5).

    Only *metric* rows (``metric_method`` set) map to a coverage-page metric; negative-space
    absence rows (``absence_kind`` set, no method) feed the dossier gaps, not the coverage
    list, and return ``None``. Every emitted metric carries the row's NAMED denominator
    (the DB CHECK guarantees it is not a reality/total denominator) and ``is_population_total``
    is pinned ``false`` — never a total (SIG-METRIC-009/010).
    """
    method = row.get("metric_method")
    if not method:
        return None
    named = row.get("named_denominator")
    if not named:
        return None  # a metric with no named denominator is not publishable (§32.5)
    numerator = row.get("numerator")
    denominator = row.get("denominator")
    if numerator is not None and denominator is not None:
        value = f"{_fmt_count(numerator)} of {_fmt_count(denominator)}"
    elif row.get("metric_value") is not None:
        value = _fmt_count(row.get("metric_value"))
    else:
        value = _fmt_count(numerator)
    label = row.get("metric_label") or str(method)
    ident = row.get("predicate_id") or row.get("subject_class") or row.get("coverage_id")
    return {
        "id": f"materialized_{method}_{ident}",
        "kind": _COMPLETENESS_TO_KIND.get(str(method), "counted_quantity"),
        "label": str(label),
        "value": value,
        "denominator": str(named),
        "population_note": _POPULATION_NOTE,
        "is_population_total": False,
    }


def resolved_site_counts(
    resolved_site_runs: Sequence[Mapping[str, Any]], dataset: ShapedDataset
) -> dict[str, Any] | None:
    """``M``, ``N`` and the dedup ratio over the export's own sites (P30.2b, ADR-105).

    **The unit.** ``M`` = the observation-level camera records in this export (the sites
    carrying coordinate claims — each ONE source's row). A **resolved site** is a cluster
    of those records the latest completed camera-site ER run judged to be the same
    physical device; ``N`` = the number of such clusters (singletons included), so
    ``N <= M`` by construction and ``dedup ratio = 1 - N/M``. The edges that join
    records are the AUTO-WRITTEN same-device edges (tiers whose measured holdout
    precision cleared the published floor) PLUS every valid human-accepted edge
    (P31.11/ADR-R9-HUMANER, ``human_accept`` — a curator's recorded decision,
    applied under the same hard constraints). PROPOSED merges await human review,
    human REJECTS (cannot-link) and refused accept attempts are recorded but never
    cluster. A §28 value decision on one record (ADR-104) is NOT a resolved site
    and is never counted as one.

    Returns ``None`` when no camera-site ER run has completed (the surface then keeps its
    observation-level framing — never a fabricated resolved-site count).
    """
    if not resolved_site_runs:
        return None
    run = resolved_site_runs[0]
    subjects = sorted({s.entity_id for s in dataset.sites if s.has_coordinate_claims})
    m = len(subjects)
    if m == 0:
        return None
    in_export = set(subjects)
    parent: dict[str, str] = {x: x for x in subjects}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    merges = auto_merges = human_merges = 0
    for kind, edges in (
        ("auto", run.get("auto_write_edges") or ()),
        ("human", run.get("human_accept_edges") or ()),
    ):
        for left, right in edges:
            a, b = str(left), str(right)
            if a not in in_export or b not in in_export:
                continue
            ra, rb = find(a), find(b)
            if ra != rb:
                lo, hi = sorted((ra, rb))
                parent[hi] = lo
                merges += 1
                if kind == "auto":
                    auto_merges += 1
                else:
                    human_merges += 1
    n = m - merges
    return {
        "observations": m,
        "resolved_sites": n,
        "dedup_ratio": 1.0 - n / m,
        "merges": merges,
        "auto_merges": auto_merges,
        "human_merges": human_merges,
        "proposed": int(run.get("proposed_count") or 0),
        "refused": int(run.get("refused_count") or 0),
        "cannot_link": int(run.get("cannot_link_count") or 0),
        "run_key": run.get("run_key"),
    }


def resolved_sites_metric(
    resolved_site_runs: Sequence[Mapping[str, Any]], dataset: ShapedDataset
) -> dict[str, Any] | None:
    """The honest "N resolved sites (from M observation-level records)" metric (ADR-105).

    Denominated in ``M`` observation-level camera records (never a total, §32); ``N`` is
    post-ER clusters of the same physical device (:func:`resolved_site_counts`). An
    honestly-measured ``N`` close to ``M`` (little true overlap between sources) is
    reported as such — the dedup ratio is shown, never inflated. Carries the
    provisional-eval disclosure (D-R6.1-EVAL). ``None`` when no ER run has completed.
    """
    counts = resolved_site_counts(resolved_site_runs, dataset)
    if counts is None:
        return None
    m, n = counts["observations"], counts["resolved_sites"]
    return {
        "id": "resolved_sites",
        "kind": "counted_quantity",
        "label": "resolved sites (clusters of observation-level records of the same device)",
        "value": (
            f"{n} resolved sites (from {m} observation-level records; "
            f"dedup ratio {counts['dedup_ratio']:.3f})"
        ),
        "denominator": (
            f"{m} observation-level sites carrying coordinate claims (each one source's record)"
        ),
        "population_note": (
            _POPULATION_NOTE
            + " A resolved site is a cluster of records judged to describe the same physical "
            f"device: {counts['auto_merges']} same-device merges were auto-written (only tiers "
            "whose measured holdout precision cleared the published floor) and "
            f"{counts['human_merges']} were accepted in human review under the same hard "
            f"constraints; {counts['proposed']} proposed merges still await review and are not "
            f"counted, {counts['cannot_link']} reviewer rejects are recorded as cannot-link and "
            f"{counts['refused']} accepted merges were refused by the hard constraints — none of "
            "these cluster." + _RESOLVED_EVAL_DISCLOSURE
        ),
        "is_population_total": False,
    }


def contradictions_visible_metric(
    materialized_contradictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """The "contradictions kept visible" coverage metric (P28.3, §3.1/§31).

    Surfaces the materialized §31 contradiction object as a counted quantity: how many
    recorded contradictions are open, of the full recorded set — both disagreeing sides
    retained, never silently reconciled (§3.1). Returns ``None`` when the materialized
    contradiction table is empty (the degraded hosted state), so no fabricated count is
    shown. The denominator names the recorded contradiction set (never reality); the value
    is never a total.
    """
    recorded = list(materialized_contradictions)
    k = len(recorded)
    if k == 0:
        return None
    open_states = {"open", "under_research"}
    open_n = sum(1 for c in recorded if str(c.get("status")) in open_states)
    return {
        "id": "contradictions_visible",
        "kind": "counted_quantity",
        "label": "contradictions kept visible",
        "value": f"{open_n} open of {k} recorded contradictions",
        "denominator": (
            f"{k} recorded contradictions in the materialized graph "
            "(both evidence sides retained, §31)"
        ),
        "population_note": (
            "Contradictions are never silently reconciled (§3.1); both disagreeing sides are "
            "retained. This counts recorded contradictions, not an estimate of every "
            "disagreement that exists."
        ),
        "is_population_total": False,
    }


def _network_from_materialized(
    edges: Sequence[Mapping[str, Any]], source_names: Mapping[str, str]
) -> dict[str, Any]:
    """Build the §39.4 network surface from the materialized ``relationship`` edges (P28.2).

    Consumes ``reconcile.materialize.read_materialized_edges`` (already reconciled through the
    P08.2 §29.3 reconciler): the three §12.2 access kinds stay separate, every edge carries its
    backing ``evidence_claim`` (no unevidenced edge, §3.1). An edge whose access kind is not one
    of the three typed kinds is honestly absent from the typed network rather than coerced.
    """
    allowed = {"configured_access", "observed_use", "declared_policy"}
    nodes: dict[str, dict[str, Any]] = {}
    out_edges: list[dict[str, Any]] = []
    for e in edges:
        access_kind = str(e.get("access_kind"))
        if access_kind not in allowed:
            continue
        src = str(e["from_entity"])
        dst = str(e["to_entity"])
        nodes.setdefault(src, {"id": src, "label": source_names.get(src, src), "type": "agency"})
        nodes.setdefault(dst, {"id": dst, "label": source_names.get(dst, dst), "type": "partner"})
        out_edges.append(
            {
                "from": src,
                "to": dst,
                "access_kind": access_kind,
                "relation": str(e.get("edge_type") or access_kind),
                # The read seam surfaces one representative backing claim per edge, so the
                # honest §10.7 support floor is the single-source level — never overclaimed.
                "support": "WEAKLY_SUPPORTED",
                "evidence_count": 1,
            }
        )
    return {"nodes": [nodes[k] for k in sorted(nodes)], "edges": out_edges, "access_paths": []}


def _map_layer(
    dataset: ShapedDataset,
    *,
    resolved: Mapping[str, Any] | None = None,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Surface 3 — MapLayer / MapAsset / JurisdictionIndicator (§39.3).

    When a camera-site ER run has completed (``resolved`` = :func:`resolved_site_counts`,
    ADR-105), the layer describes the resolved sites with the honest N-of-M framing; otherwise
    it keeps the launch observation-level description (the honest degraded state, ADR-092).
    Assets stay one per observation-level record: each carries ONE record's own point, so no
    published point ever mixes coordinates from two sources (ADR-104/ADR-105).
    """
    assets: list[dict[str, Any]] = []
    for site in dataset.sites:
        if site.entity_id in exclude:
            # A subject with any licence-REFUSED slice never reaches a render surface (its
            # aggregate point could carry refused bytes) — it is in exclusions.json instead.
            continue
        asset: dict[str, Any] = {
            "id": site.entity_id,
            "label": site.label or site.entity_id,
            "jurisdiction": site.jurisdiction,
            "tier": site.sensitivity_tier,
            "lat": site.latitude,
            "lon": site.longitude,
            "precision": site.precision,
        }
        if site.latitude is None or site.longitude is None:
            # An honest reason there is no point (a gap, not a guess, §3.1), in the web's
            # §9.5 absence vocabulary (`epistemic.ts#ABSENCE_KINDS`, P30.3): conflicting
            # coordinate evidence is UNRESOLVED; a record whose named source carries no
            # coordinate is NO_EVIDENCE_FOUND (the point was looked for in that record).
            asset["locationAbsence"] = (
                "UNRESOLVED" if site.point_status == "conflicted" else "NO_EVIDENCE_FOUND"
            )
        assets.append(asset)
    if resolved:
        layers = [
            {
                "id": "resolved_sites",
                "label": "Resolved device sites",
                "kind": "resolved",
                "description": (
                    f"{resolved['resolved_sites']} resolved device sites (clusters of the same "
                    f"physical device) from {resolved['observations']} observation-level "
                    f"records (dedup ratio {resolved['dedup_ratio']:.3f}), via materialized "
                    "camera-site entity resolution (ADR-105). Each point shown is one "
                    "record's own. Resolution rests on a provisional eval (D-R6.1-EVAL, OPEN)."
                ),
            }
        ]
    else:
        layers = [
            {
                "id": "observed_sites",
                "label": "Observed device sites",
                "kind": "observed",
                "description": (
                    "Observation-level device sites from named sources — N observations "
                    "across M sources, never a resolved census (SIG-RECON-058)."
                ),
            }
        ]
    indicators = [{"jurisdiction": j.jurisdiction} for j in dataset.jurisdictions]
    return {"layers": layers, "assets": assets, "jurisdiction_indicators": indicators}


def _network(dataset: ShapedDataset, source_names: Mapping[str, str]) -> dict[str, Any]:
    """Surface 4 — NetworkNode / NetworkEdge (§39.4). The three §12.2 access-edge
    types are never merged; an unclassifiable edge carries no typed relationship, so
    it is honestly absent from the typed network rather than coerced into one."""
    _ALLOWED = {"configured_access", "observed_use", "declared_policy"}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for edge in dataset.sharing_edges:
        if edge.access_kind not in _ALLOWED or edge.partner_ref is None:
            continue
        src = edge.subject_id
        dst = edge.partner_ref
        nodes.setdefault(src, {"id": src, "label": src, "type": "agency"})
        nodes.setdefault(dst, {"id": dst, "label": source_names.get(dst, dst), "type": "partner"})
        edges.append(
            {
                "from": src,
                "to": dst,
                "access_kind": edge.access_kind,
                "relation": edge.predicate_id,
                "evidence_count": 1,
            }
        )
    return {
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": edges,
        "access_paths": [],
    }


def _freshness(dataset: ShapedDataset) -> list[dict[str, Any]]:
    """Surface 5 — FreshnessRow[] (§32.4). Straight from the shaping layer."""
    return [s.freshness_row() for s in dataset.sources]


def _coverage(
    dataset: ShapedDataset,
    *,
    materialized_coverage: Sequence[Mapping[str, Any]] = (),
    resolved_site_runs: Sequence[Mapping[str, Any]] = (),
    materialized_contradictions: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Surface 6 — CoverageMetric[] (§32.5). Named denominators, never a total (ADR-101).

    Reads the materialized §32 coverage (P28.4) when present, else the compute-on-read shaping
    metrics (ADR-092, the honest fallback for an unmaterialized spine). Then APPENDS the two
    materialized-graph counted quantities — the resolved-site framing (post-ER clusters of the
    same device, P30.2b/ADR-105) and contradictions kept visible (P28.3) — each gated on its own
    materialized input being non-empty, so an empty hosted spine shows neither a fabricated
    resolved count nor a fabricated contradiction count.
    """
    if materialized_coverage:
        base: list[dict[str, Any]] = [
            m
            for m in (coverage_metric_from_materialized(r) for r in materialized_coverage)
            if m is not None
        ]
    else:
        base = list(dataset.coverage_metrics)
    resolved = resolved_sites_metric(resolved_site_runs, dataset)
    if resolved is not None:
        base.append(resolved)
    contradictions = contradictions_visible_metric(materialized_contradictions)
    if contradictions is not None:
        base.append(contradictions)
    return base


def _watch(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Surface 7 — ContractWatchItem[] (§39.5). Honest absence when the spine has no
    contracts with a derived notice deadline yet."""
    out: list[dict[str, Any]] = []
    for row in raw.get("contract_watch") or []:
        out.append(dict(row))
    return out


def _evidence(raw: Mapping[str, Any], as_of: str) -> dict[str, Any]:
    """Surface 8 — EvidenceArtifact[] + ClaimView[] (§39.6). Metadata only; sealed
    captures never carry bytes (§17.5)."""
    artifacts: list[dict[str, Any]] = []
    for r in raw.get("evidence_artifacts") or []:
        artifact_id, source_id, title, artifact_type, locator, direct, capture_status, published = r
        artifacts.append(
            {
                "artifact_id": str(artifact_id),
                "subject_id": "",
                "title": title or str(artifact_id),
                "source": str(source_id),
                "artifact_type": str(artifact_type),
                "directness": str(direct),
                "currency": str(published or ""),
                "touches_open_contradiction": False,
                "answers_open_task": False,
                "capture_status": str(capture_status),
                "permalink": str(locator),
                "as_of": as_of,
            }
        )
    return {"artifacts": artifacts, "claim_views": []}


def _corrections(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Surface 9 — CorrectionEntry[] (§39.8). History never rewritten: the prior
    value stays citable at its belief-time (SIG-GOV-005)."""
    out: list[dict[str, Any]] = []
    for r in raw.get("corrections") or []:
        claim_id, subject_id, predicate_id, raw_value, reason, revises, retraction, recorded = r
        out.append(
            {
                "id": str(claim_id),
                "subject_id": str(subject_id),
                "subject_label": str(subject_id),
                "what_changed": str(predicate_id),
                "corrected_at": recorded.isoformat() if hasattr(recorded, "isoformat") else "",
                "reason": str(reason or ""),
                "reported_by": "anonymous",
                "category": "retraction" if retraction else "revision",
                "outcome": "applied",
                "previous_value": "",
                "corrected_value": str(raw_value or ""),
                "previous_belief_date": "",
                "subject_path": f"/dossier/{subject_id}",
            }
        )
    return out


def _research_queue(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Surface 10 — ResearchTaskCard[] (§39.7). Every task has a testable closing
    condition (SIG-TASK-002)."""
    out: list[dict[str, Any]] = []
    for r in raw.get("research_tasks") or []:
        task_id, task_type, subject_id, jurisdiction_id, priority, status, disp, closing, _det = r[
            :9
        ]
        # P29.2: trigger_kind/trigger_ref cite what made the detector fire — present when the
        # detector run wrote the row, absent (None) for a legacy/hand-inserted row.
        trigger_kind = r[9] if len(r) > 9 else None
        trigger_ref = r[10] if len(r) > 10 else None
        card: dict[str, Any] = {
            "task_type": str(task_type),
            "subject_id": str(subject_id or task_id),
            "subject_label": str(subject_id or task_id),
            "closing_condition": str(closing),
            "evidence_sought": str(task_type),
            "assignee_class": "contributor",
            "effort_estimate": "unknown",
            "geographic_scope": str(jurisdiction_id or ""),
            "jurisdiction": str(jurisdiction_id or ""),
            "dispositions": [str(disp)] if disp else [],
            "priority": float(priority) if priority is not None else 0.0,
        }
        if trigger_kind:
            card["trigger"] = {"kind": str(trigger_kind), "ref": str(trigger_ref or "")}
        out.append(card)
    return out


#: The P28.6 governance-chain segments, in chain order, with the dossier section each
#: link rides into (the frozen ``web/src/lib/dossier.ts`` ``Section``/``Row`` contract —
#: no new IA). ``chain_role`` is the value_json role the materializer stamps.
_GOVERNANCE_SEGMENTS: tuple[tuple[str, str, str], ...] = (
    ("vendor", "what_is_deployed", "Vendor / platform provider"),
    ("contract", "cost_and_expiry", "Procured under contract"),
    ("funding", "cost_and_expiry", "Funded by"),
    ("policy", "policy", "Governing policy"),
    ("oversight", "accountability_events", "Oversight"),
)


def _governance_by_jurisdiction(
    dataset: ShapedDataset, accountability_links: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, list[Mapping[str, Any]]]]:
    """Attribute each materialized accountability link to a jurisdiction, by chain role.

    The honest bridge: a link is attributed to a jurisdiction ONLY when its
    ``deployment_id`` matches a shaped site's ``subject_id`` (the deployment is a
    geolocated site subject in that bucket). A link whose deployment cannot be proven to
    sit in a jurisdiction is left unattributed — never guessed onto a dossier. Returns
    ``{jurisdiction: {chain_role: [link, ...]}}``.
    """
    site_jurisdiction: dict[str, str] = {}
    for site in dataset.sites:
        # First writer wins deterministically (sites are ordered); a conflicted site keeps
        # its first bucket — attribution is best-effort and never fabricated. The site's
        # ``entity_id`` is the deployment/subject entity the accountability link anchors on.
        site_jurisdiction.setdefault(str(site.entity_id), site.jurisdiction)
    out: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    for link in accountability_links:
        juris = site_jurisdiction.get(str(link.get("deployment_id")))
        if juris is None:
            continue
        role = str(link.get("chain_role") or "")
        out.setdefault(juris, {}).setdefault(role, []).append(link)
    return out


def _governance_row(link: Mapping[str, Any], label: str) -> dict[str, Any]:
    """One governance-chain link as a frozen ``Row`` — always citing its claims (§3.1)."""
    claims = ", ".join(str(c) for c in (link.get("establishing_claims") or ())) or "(none)"
    via_bits = []
    if link.get("via_org"):
        via_bits.append(f"via operator org {link['via_org']}")
    if link.get("via_contract"):
        via_bits.append(f"via contract {link['via_contract']}")
    via = f" ({'; '.join(via_bits)})" if via_bits else ""
    return {
        "label": label,
        "value": str(link.get("object_id")),
        "note": (
            f"Derived accountability link (L4 inference, confidence "
            f"{link.get('confidence', 'probable')}){via}; established by claim(s) {claims} "
            "— procured ≠ deployed (§3.1)."
        ),
    }


def _governance_chain_field(
    slug: str, by_role: Mapping[str, Sequence[Mapping[str, Any]]]
) -> dict[str, Any]:
    """The structured per-dossier governance chain, with honest gaps for empty segments.

    Additive to the dossier JSON: each of the five chain segments lists its evidenced
    links (object + establishing claims + confidence) or is marked ``not_researched`` —
    the honest gap the ticket demands, never a fabricated link.
    """
    segments: dict[str, Any] = {}
    for role, _section, _label in _GOVERNANCE_SEGMENTS:
        links = list(by_role.get(role, ()))
        if links:
            segments[role] = {
                "status": "evidenced",
                "links": [
                    {
                        "object_id": str(link.get("object_id")),
                        "object_type": link.get("object_type"),
                        "confidence": link.get("confidence", "probable"),
                        "establishing_claims": [
                            str(c) for c in (link.get("establishing_claims") or ())
                        ],
                        "via_org": link.get("via_org"),
                        "via_contract": link.get("via_contract"),
                    }
                    for link in links
                ],
            }
        else:
            segments[role] = {
                "status": "not_researched",
                "links": [],
                "note": (
                    f"No evidenced {role} link for a resolved deployment in this "
                    "jurisdiction — an honest gap, not an absence of one (§3.1)."
                ),
            }
    return {"subject_id": f"jurisdiction:{slug}", "segments": segments}


def _dossiers(
    dataset: ShapedDataset,
    as_of: str,
    belief: datetime | None,
    *,
    accountability_links: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Surfaces 1 + 2 — the dossier index / per-jurisdiction dossiers (§39.2).

    One dossier per publishable jurisdiction bucket (incl. the honest ``unresolved``
    bucket), in the frozen ``web/src/lib/dossier.ts`` ``Dossier`` contract. Every
    published count is denominated (§32) and gaps stay first-class (§3.1) — nothing
    fabricated, nothing collapsed.

    P28.6: when materialized accountability links exist (P28.6), each dossier is enriched
    with the deployment→vendor→contract→funding→policy→oversight governance chain — rows
    riding the frozen ``Section``/``Row`` contract (no new IA), each citing its
    establishing claims, plus a structured ``governance_chain`` field with honest gaps.
    An unmaterialized spine (no links) leaves the dossier exactly as before (honest
    degrade — the surface plumbing is P28.5's; this only fills it where evidence exists).
    """
    echo = _as_of_echo(as_of, belief)
    governance = _governance_by_jurisdiction(dataset, accountability_links)
    dossiers: list[dict[str, Any]] = []
    for group in dataset.jurisdictions:
        slug = _slugify(group.jurisdiction)
        by_role = governance.get(group.jurisdiction, {})
        # Governance-chain rows, keyed by the dossier section they ride into.
        gov_rows: dict[str, list[dict[str, Any]]] = {}
        for role, section_id, label in _GOVERNANCE_SEGMENTS:
            for link in by_role.get(role, ()):
                gov_rows.setdefault(section_id, []).append(_governance_row(link, label))
        sections: list[dict[str, Any]] = []
        for section_id in _DOSSIER_SECTIONS:
            section: dict[str, Any] = {"section_id": section_id}
            rows: list[dict[str, Any]] = []
            if section_id == "what_is_deployed":
                rows.append(
                    {
                        "label": "Geolocated site observations",
                        "value": group.sites.phrase(),
                        "note": (
                            "Observation-level count from named sources — not a "
                            "resolved device census (SIG-RECON-058)."
                        ),
                    }
                )
            elif section_id == "where_the_hardware_is":
                rows.append(
                    {
                        "label": "Publishable subjects in this jurisdiction",
                        "value": group.subjects,
                    }
                )
            elif section_id == "how_we_know_this":
                rows.append(
                    {
                        "label": "Sources",
                        "value": ", ".join(group.source_ids) or "(none recorded)",
                    }
                )
            rows.extend(gov_rows.get(section_id, ()))
            if rows:
                section["rows"] = rows
            sections.append(section)
        gaps = [
            {
                "label": "Data-sharing partners",
                "kind": "NOT_RESEARCHED",
                "subject_id": f"jurisdiction:{slug}",
                "predicate_id": "sharing_partners",
            }
        ]
        if group.conflicted_subjects:
            gaps.append(
                {
                    "label": "Subjects with conflicting coordinate evidence",
                    "kind": "UNRESOLVED",
                    "subject_id": f"jurisdiction:{slug}",
                    "predicate_id": "camera_latitude",
                }
            )
        dossier: dict[str, Any] = {
            "slug": slug,
            "subject_label": f"Surveillance infrastructure — {group.jurisdiction}",
            "jurisdiction": group.jurisdiction,
            "asOf": echo,
            "rulesetVersion": SHAPING_SCHEMA_VERSION,
            "sections": sections,
            "gaps": gaps,
            "source_families": list(group.source_ids),
            # The three action blocks (SIG-UI-014a) in their FULL contract shape with every
            # field explicitly UNKNOWN (null / []) — the spine holds no authorization /
            # termination / legal-regime facts for a jurisdiction yet. An empty object made
            # the web render "no" for auto-renewal (a fabricated fact) and crash on
            # `disclosure_duties.length` (P30.3).
            "authorization": dict(_UNKNOWN_AUTHORIZATION),
            "termination": dict(_UNKNOWN_TERMINATION),
            "legal_regime": {**_UNKNOWN_LEGAL_REGIME, "disclosure_duties": []},
        }
        # Only attach the governance chain where it is materialized for this jurisdiction;
        # an unmaterialized spine leaves the dossier byte-identical (honest degrade, P28.5).
        if by_role:
            dossier["governance_chain"] = _governance_chain_field(slug, by_role)
        dossiers.append(dossier)
    return dossiers


#: The web ``dossier.ts`` action-block contracts with every field explicitly unknown.
_UNKNOWN_AUTHORIZATION: dict[str, Any] = {
    "approving_body": None,
    "vote": None,
    "consent_agenda": None,
    "public_comment": None,
    "date": None,
}
_UNKNOWN_TERMINATION: dict[str, Any] = {
    "auto_renews": None,
    "notice_window_days": None,
    "expiry_date": None,
}
_UNKNOWN_LEGAL_REGIME: dict[str, Any] = {
    "state_statute": None,
    "local_ordinance": None,
    "disclosure_duties": [],
}


def _dossier_index(dossiers: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "slug": d["slug"],
            "subject_label": d["subject_label"],
            "jurisdiction": d["jurisdiction"],
            "asOf": d["asOf"],
        }
        for d in dossiers
    ]


def _slugify(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "unresolved"


# --------------------------------------------------------------------------- #
# The build                                                                    #
# --------------------------------------------------------------------------- #


def _table(name: str, rows: Sequence[C.ExportRow], *, kind: str, compartment: str) -> C.ExportTable:
    return C.ExportTable(name=name, rows=tuple(rows), kind=kind, compartment=compartment)


def build_spine_export(
    dataset: ShapedDataset,
    raw: Mapping[str, Any] | None = None,
    *,
    build_spec: BuildSpec,
    generated_at: str,
    note: str = "",
    belief: datetime | None = None,
    claims: Sequence[ShapingClaim] | None = None,
    entity_types: Mapping[str, str] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> SpineExport:
    """Assemble the national :class:`SpineExport` (pure — no database).

    ``dataset`` is the P27.3 shaped dataset (the aggregate national view the web
    surfaces read). ``claims``/``entity_types`` are the parsed shaping rows used to
    licence-slice the sites per (source, rights_id) with per-slice envelopes
    recomputed; when omitted they are re-derived from ``raw['shaping_claims']`` /
    ``raw['subject_entities']`` if present, else from ``dataset`` (a coarser slice
    that reuses the aggregate point). ``raw`` carries the supplementary read sets
    (watch/evidence/corrections/research_queue/source_names) — any missing key is
    honest absence.
    """
    raw = dict(raw or {})
    retrieval = date.fromisoformat(dataset.as_of[:10]) if dataset.as_of else date.today()

    if claims is None and raw.get("shaping_claims"):
        claims = parse_shaping_claims(raw["shaping_claims"])
    if entity_types is None:
        entity_types = {str(r[0]): str(r[1]) for r in (raw.get("subject_entities") or [])}
    if claims is None:
        claims = _claims_from_dataset(dataset)

    source_names = {str(r[0]): str(r[1]) for r in (raw.get("source_names") or [])}

    # --- the materialized graph (P28.1-P28.4, ADR-101) --------------------------
    # Read from ``raw`` (populated by ``run_spine_export`` inside the read-only snapshot);
    # each defaults to () so a pure caller / an unmaterialized spine degrades honestly to the
    # compute-on-read shaping layer, never a crash and never a fabricated resolved-site count.
    m_site_runs = list(raw.get("materialized_site_runs") or [])
    m_edges = list(raw.get("materialized_edges") or [])
    m_contradictions = list(raw.get("materialized_contradictions") or [])
    m_coverage = list(raw.get("materialized_coverage") or [])
    m_acct_links = list(raw.get("materialized_accountability_links") or [])

    # Coverage is computed ONCE (materialized when present, else shaping) so the web
    # coverage.json and the sig_graph coverage table never drift.
    coverage_metrics = _coverage(
        dataset,
        materialized_coverage=m_coverage,
        resolved_site_runs=m_site_runs,
        materialized_contradictions=m_contradictions,
    )
    resolved_counts = resolved_site_counts(m_site_runs, dataset)

    # --- the licence-critical path: sites sliced per (source, rights) -----------
    slices = _slice_sites(claims, entity_types, retrieval=retrieval, registry=registry)
    site_rows, site_index, site_exclusions = (
        slices.rows_by_compartment,
        slices.index,
        slices.exclusions,
    )

    tables: list[C.ExportTable] = []
    for compartment in sorted(site_rows):
        tables.append(_table("sites", site_rows[compartment], kind="geo", compartment=compartment))

    # --- the SIG-derived framing tables (CC-BY-4.0 → sig_graph) ----------------
    sig = _sig_record(retrieval)
    sig_rows: dict[str, list[C.ExportRow]] = {
        "jurisdictions": [
            C.ExportRow(source_id=_SIG_SOURCE_ID, data=j.as_json()) for j in dataset.jurisdictions
        ],
        "coverage": [C.ExportRow(source_id=_SIG_SOURCE_ID, data=dict(m)) for m in coverage_metrics],
        "freshness": [
            C.ExportRow(source_id=_SIG_SOURCE_ID, data=s.freshness_row()) for s in dataset.sources
        ],
        "sharing_edges": [
            C.ExportRow(source_id=_SIG_SOURCE_ID, data=e.as_json()) for e in dataset.sharing_edges
        ],
    }
    sig_compartment = C.compartment_for_license(
        compute_export_license([sig], registry), None, registry
    )
    for name, rows in sig_rows.items():
        if rows:
            tables.append(_table(name, rows, kind="tabular", compartment=sig_compartment))

    rights = [*site_index.values(), sig]
    bundle = build_bundle(build_spec, tables, rights, registry=registry)

    # --- the ten P27.1-contract web surfaces ------------------------------------
    dossiers = _dossiers(dataset, dataset.as_of, belief, accountability_links=m_acct_links)
    surfaces: dict[str, Any] = {
        "dossier_index": _dossier_index(dossiers),
        "dossiers": dossiers,
        "map": _map_layer(dataset, resolved=resolved_counts, exclude=slices.refused_subjects),
        # The network reads the materialized §29.3 edges (P28.2) when present, else the
        # compute-on-read shaping envelope (the honest fallback for an unmaterialized spine).
        "network": (
            _network_from_materialized(m_edges, source_names)
            if m_edges
            else _network(dataset, source_names)
        ),
        "freshness": _freshness(dataset),
        "coverage": coverage_metrics,
        "watch": _watch(raw),
        "evidence": _evidence(raw, dataset.as_of),
        "corrections": _corrections(raw),
        "research_queue": _research_queue(raw),
    }
    web_artifacts: dict[str, bytes] = {}
    for name, payload in surfaces.items():
        web_artifacts[f"{_WEB_DIR}/{name}.json"] = _web_bytes(payload)
    # The map surface carries every published subject's own point + label, so it draws on
    # every site compartment's licence (ODbL OSM points beside CC-BY/CC0/… points) — its
    # label says so (ADR-106). The other surfaces carry SIG's aggregate framing (counts,
    # freshness, coverage) and stay SIG CC-BY-4.0.
    mapped = {
        site.entity_id for site in dataset.sites if site.entity_id not in slices.refused_subjects
    }
    web_licenses = {
        f"{_WEB_DIR}/map.json": surface_license(
            {lic for sid in mapped for lic in slices.licences_by_subject.get(sid, ())}
        )
    }

    # --- the P31.14 analytics family (web/analytics/<name>.json) ---------------
    # The presentation analytics the surfaces render — density bins, centrality +
    # focus, the watch's decision point, per-surface provenance (W4..W0 tiers),
    # queue metadata — emitted with schema id / as_of / named denominator /
    # source compartments, licence-labelled like map.json (ADR-R9-ANALYTICS).
    web_compartments: dict[str, str] = {}
    for art in analytics.build_analytics(
        dataset,
        raw,
        licences_by_subject=slices.licences_by_subject,
        refused_subjects=slices.refused_subjects,
        materialized_edges=m_edges,
        materialized_site_runs=m_site_runs,
        ruleset_version=build_spec.ruleset_version,
        registry=registry,
    ):
        web_artifacts[art.path] = _web_bytes(art.payload)
        web_licenses[art.path] = art.license
        web_compartments[art.path] = art.compartment

    # --- per-compartment PMTiles (ODbL attribution on the OSM layer) ------------
    tile_renderers: dict[str, str] = {}
    # (published_path, compartment, license, bytes)
    tile_artifacts: list[tuple[str, str, str, bytes]] = []
    for pt in bundle.placed:
        if pt.table.name != "sites" or pt.table.kind != "geo":
            continue
        geojson_path = f"{pt.compartment}/sites.geojson"
        geojson_bytes = bundle.artifact_bytes.get(geojson_path)
        if geojson_bytes is None:
            continue
        rendered, renderer = _render_tiles(pt.compartment, geojson_bytes, pt.license)
        tile_path = f"{_WEB_DIR}/tiles/{pt.compartment}-sites.pmtiles"
        web_artifacts[tile_path] = rendered
        tile_renderers[pt.compartment] = renderer
        tile_artifacts.append((tile_path, pt.compartment, pt.license, rendered))

    # --- the PROV-O lineage (§21.6) --------------------------------------------
    provenance = _provenance_ttl(
        dataset,
        source_names,
        release_id=build_spec.release_id(),
        generated_at=generated_at,
    )

    # --- the loud exclusions report --------------------------------------------
    exclusions = {
        "schema": "p27.4/exclusions/1.0.0",
        "as_of": dataset.as_of,
        "generated_at": generated_at,
        "note": note,
        "refused": site_exclusions,
        "totals": {
            "refused_slices": len(site_exclusions),
            "refused_rows": sum(int(e["rows"]) for e in site_exclusions),
        },
    }

    manifest = _extended_manifest(
        bundle,
        web_artifacts=web_artifacts,
        tile_artifacts=tile_artifacts,
        web_licenses=web_licenses,
        web_compartments=web_compartments,
        provenance=provenance,
        exclusions=exclusions,
    )
    return SpineExport(
        bundle=bundle,
        web_artifacts=web_artifacts,
        provenance=provenance,
        exclusions=exclusions,
        manifest=manifest,
        tile_renderers=tile_renderers,
    )


def _web_bytes(payload: Any) -> bytes:
    """Deterministic, human-diffable JSON for a web surface (indented, sorted)."""
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _render_tiles(compartment: str, geojson_bytes: bytes, license_id: str) -> tuple[bytes, str]:
    """Render one compartment's sites.geojson → PMTiles bytes (+ renderer name).

    ODbL keeps its attribution; other compartments get a SIG/CC-BY attribution. The
    renderer writes through a temp file (``render_pmtiles_file`` uses tippecanoe when
    present, else the pure-Python encoder).
    """
    import tempfile

    attribution = ODBL_ATTRIBUTION if license_id == "ODbL-1.0" else _SIG_ATTRIBUTION
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "sites.geojson"
        src.write_bytes(geojson_bytes)
        out = Path(tmp) / "sites.pmtiles"
        renderer = render_pmtiles_file(
            str(src),
            str(out),
            layer_name="sites",
            license_id=license_id,
            attribution=attribution,
        )
        return out.read_bytes(), renderer


def _extended_manifest(
    bundle: Bundle,
    *,
    web_artifacts: Mapping[str, bytes],
    tile_artifacts: Sequence[tuple[str, str, str, bytes]],
    provenance: bytes,
    exclusions: Mapping[str, Any],
    web_licenses: Mapping[str, str] | None = None,
    web_compartments: Mapping[str, str] | None = None,
) -> Manifest:
    """Extend the bundle manifest with the web JSONs, tiles, provenance, exclusions.

    Every added artifact carries its checksum + compartment + computed licence, so a
    consumer can verify integrity and know the governing licence of each file
    (SIG-EXPORT-001/006).
    """
    # Each tile is labelled with the compartment its sites were placed in (and that
    # compartment's licence) — a CC-BY-SA tile is never filed under `sig_graph` (ADR-106).
    tiles = {path: (comp, lic) for path, comp, lic, _ in tile_artifacts}
    labels = dict(web_licenses or {})
    compartments_for = dict(web_compartments or {})
    artifacts: list[Artifact] = list(bundle.manifest.artifacts)
    for path in sorted(web_artifacts):
        data = web_artifacts[path]
        if path in tiles:
            compartment, license_id = tiles[path]
            artifacts.append(
                Artifact.of(
                    name=Path(path).name,
                    path=path,
                    media_type="application/vnd.pmtiles",
                    compartment=compartment,
                    license=license_id,
                    data=data,
                )
            )
        else:
            artifacts.append(
                Artifact.of(
                    name=Path(path).name,
                    path=path,
                    media_type="application/json",
                    compartment=compartments_for.get(path, _WEB_COMPARTMENT),
                    license=labels.get(path, _SIG_SPDX),
                    data=data,
                )
            )
    artifacts.append(
        Artifact.of(
            name="provenance.ttl",
            path="provenance.ttl",
            media_type="text/turtle",
            compartment=_META_COMPARTMENT,
            license=_SIG_SPDX,
            data=provenance,
        )
    )
    artifacts.append(
        Artifact.of(
            name="exclusions.json",
            path="exclusions.json",
            media_type="application/json",
            compartment=_META_COMPARTMENT,
            license=_SIG_SPDX,
            data=canonical_json(exclusions),
        )
    )
    return Manifest(build_spec=bundle.build_spec, artifacts=tuple(artifacts))


def _provenance_ttl(
    dataset: ShapedDataset,
    source_names: Mapping[str, str],
    *,
    release_id: str,
    generated_at: str,
) -> bytes:
    """Build the PROV-O lineage for the release (§21.6, SIG-INGEST-016).

    Every source the export drew from is a ``prov:Agent``; the export build is a
    ``prov:Activity``; each source contributes a capture Entity attributed to it and
    generated by the build. Serialised as canonical N-Triples (a valid Turtle subset)
    so ``provenance.ttl`` is byte-reproducible (SIG-EXPORT-003).
    """
    source_ids: set[str] = set()
    for site in dataset.sites:
        source_ids.update(site.source_ids)
    for s in dataset.sources:
        source_ids.add(s.freshness.source_id)
    generated = _parse_instant(generated_at)
    lineage = provo.Lineage(
        connectors=[provo.Connector(name="sig-exports", version=SHAPING_SCHEMA_VERSION)],
        runs=[
            provo.IngestRun(
                run_id=release_id,
                connector_name="sig-exports",
                started_at=generated,
                finished_at=generated,
            )
        ],
        sources=[
            provo.Source(source_id=sid, name=source_names.get(sid)) for sid in sorted(source_ids)
        ],
        captures=[
            provo.Capture(
                capture_id=f"{release_id}:{sid}",
                source_id=sid,
                run_id=release_id,
                retrieved_at=generated,
            )
            for sid in sorted(source_ids)
        ],
    )
    return (provo.export_lineage(lineage, fmt="nt")).encode("utf-8")


def _parse_instant(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _claims_from_dataset(dataset: ShapedDataset) -> list[ShapingClaim]:
    """A coarse fallback: reconstruct minimal claims from the aggregate sites.

    Used only when the parsed shaping rows are unavailable — it reuses each site's
    aggregate point for every one of its (source, rights) slices (no per-source
    envelope recompute). The production path always passes the real claims.
    """
    claims: list[ShapingClaim] = []
    for site in dataset.sites:
        for rights in site.rights:
            sid = str(rights["source_id"])
            base = f"{site.entity_id}:{sid}:{rights['rights_id']}"
            if site.latitude is not None:
                claims.append(
                    _synthetic_claim(f"{base}:lat", site, sid, rights, LAT_PREDICATE, site.latitude)
                )
            if site.longitude is not None:
                claims.append(
                    _synthetic_claim(
                        f"{base}:lon", site, sid, rights, LON_PREDICATE, site.longitude
                    )
                )
    return claims


def _synthetic_claim(
    claim_id: str,
    site: ShapedSite,
    source_id: str,
    rights: Mapping[str, Any],
    predicate_id: str,
    value: float,
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=claim_id,
        subject_id=site.entity_id,
        predicate_id=predicate_id,
        value_kind="value",
        value_text=str(value),
        value_num=value,
        raw_value=str(value),
        observed_at=None,
        sensitivity_tier=site.sensitivity_tier,
        source_id=source_id,
        connector_name=None,
        effective_rights_id=str(rights["rights_id"]),
        effective_spdx=str(rights["spdx"]),
        effective_redistributable=str(rights.get("redistributable", "yes")),
        effective_derivative_permitted=str(rights.get("derivative_permitted", "yes")),
        effective_attribution=str(rights.get("attribution", "")),
        effective_terms_url=str(rights.get("terms_url", "")),
    )


def run_spine_export(
    conn: Any,
    *,
    build_spec: BuildSpec | None = None,
    as_of: str | None = None,
    belief: datetime | None = None,
    note: str = "",
    spine_label: str = "(unlabelled spine)",
    ruleset_version: str = SHAPING_SCHEMA_VERSION,
    resolver_version: str | None = None,
    dataset_slug: str = "sig",
) -> SpineExport:
    """Execute the read-only reads and assemble the national export.

    One ``REPEATABLE READ READ ONLY`` snapshot covers BOTH shaping and the
    supplementary export reads, so every emitted artifact describes the same spine
    state. The session is put in read-only mode first — no statement can mutate the
    append-only spine (§16). When the caller already holds an open transaction (the
    test seam) the reads run inside it unchanged.
    """
    from . import __version__
    from .shaping import (
        _queries_for,
        build_shaped_dataset,
        fetch_shaping_raw,
    )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    as_of = as_of or generated_at

    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")
    status = getattr(getattr(conn, "info", None), "transaction_status", None)
    snapshot = status is None or int(status) == 0
    if snapshot:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    try:
        cur.execute("SELECT to_regclass('rights_decision') IS NOT NULL")
        has_row = cur.fetchone()
        has_decisions = bool(has_row and has_row[0])
        shaping_raw = fetch_shaping_raw(cur, _queries_for(has_decisions), belief=belief)
        export_raw = fetch_export_raw(cur, belief=belief)
        # The materialized graph (P28.1-P28.4, ADR-101), read inside the SAME snapshot so
        # every emitted artifact describes one spine state; empty/absent tables degrade to []
        # (the honest state until the hosted materialization runs, D-R6.5-SURFACE).
        export_raw.update(fetch_materialized_graph(cur))
    finally:
        if snapshot:
            cur.execute("ROLLBACK")

    dataset = build_shaped_dataset(
        shaping_raw,
        as_of=as_of,
        generated_at=generated_at,
        spine_label=spine_label,
        note=note,
    )
    claims = parse_shaping_claims(shaping_raw.get("shaping_claims") or [])
    entity_types = {str(r[0]): str(r[1]) for r in (shaping_raw.get("subject_entities") or [])}
    # ``fetch_export_raw`` already read source_registry names into
    # ``export_raw['source_names']`` (compat-guarded); the surface builders consume it.

    if build_spec is None:
        as_of_snapshot = date.fromisoformat(as_of[:10]) if as_of else date.today()
        as_of_belief = belief.date() if belief is not None else as_of_snapshot
        build_spec = BuildSpec(
            as_of_snapshot=as_of_snapshot,
            as_of_belief=as_of_belief,
            ruleset_version=ruleset_version,
            resolver_version=resolver_version or __version__,
            dataset_slug=dataset_slug,
        )

    return build_spine_export(
        dataset,
        export_raw,
        build_spec=build_spec,
        generated_at=generated_at,
        note=note,
        belief=belief,
        claims=claims,
        entity_types=entity_types,
    )


def digest_web_artifacts(export: SpineExport) -> dict[str, str]:
    """The ``path -> sha256`` map of the web artifacts (for a live-run record)."""
    return {path: sha256_hex(data) for path, data in sorted(export.web_artifacts.items())}


__all__ = [
    "EXPORT_QUERIES",
    "SpineExport",
    "build_spine_export",
    "fetch_export_raw",
    "fetch_materialized_graph",
    "coverage_metric_from_materialized",
    "resolved_sites_metric",
    "resolved_site_counts",
    "surface_license",
    "contradictions_visible_metric",
    "run_spine_export",
    "digest_web_artifacts",
]
