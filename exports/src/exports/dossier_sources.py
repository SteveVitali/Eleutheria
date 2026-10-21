# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.44 (R11-K13-DSRC-01 / ticket 323, K5 §3) — the dossier contribution export.

One shared accumulation feeds BOTH directions of the contribution view — the
per-dossier ``sig.dossier-sources/1`` artifacts under
``web/dossier_sources/<slug>.json`` and the source-side ``contributions[]`` on
``transparency/sources.json`` (TRANSP-008/040: the dossier↔source numbers are
literally one computation, never two).

Reads:

* ``claim_sightings`` — the ``EXPORT_QUERIES`` aggregate over
  ``v_claim_sightings`` (K5 §3.1 + the shared publishable-claim / artifact /
  capture-seal / effective-rights gates): one row per
  ``(claim, subject, predicate, source)`` carrying first/last seen instants,
  first/last run ids, the sighting run/month sets and the establishing-link
  count the §3.3 ``run_level_only`` check reads.
* the licence-sliced site rows (``_slice_sites`` output): the dossier membership
  — declared bucket ∪ placement chain ancestors (K4 §5.3 roll-up: place →
  county → admin-1 → country). P35.45: chain-less records file under the
  ``unplaced`` data-quality sentinel — never a guessed home — and registry
  keys mint multi-segment slug paths (``usa/ca/verdin-county-06037``) via
  ``dossier_keys``.
* ``transparency_runs`` — the run status/finish instants the "latest complete
  run" rule reads (K5 §3.1: only ``ok`` completions).
* ``materialized_contradictions`` — contradiction records placed through their
  subject.
* ``claim_weights`` + ``claim_lineage`` — the dossier-scope
  ``provenance_summary`` (SIG-UI-044 / the absorbed PKG-10 per-dossier "How we
  know this", D-K5-4).

Honest-absence rules: ``run_level_only`` / ``not_recorded`` / ``not_evaluable``
tokens name every gap (K5 §3.3 + K5-P4 — never a silent zero);
``human_review_status`` is always ``"unreviewed"``; ``cross_source`` stays
``not_evaluable`` until DSRC-04; ``downloads[]`` stays empty until DSRC-03.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from policy.transparency import TRANSPARENCY_RUN_VIEW_COLUMNS, iso_utc

from . import analytics
from . import dossier_keys as _dk
from .formats import _gzip0
from .jurisdictions import jurisdiction_slug
from .placement import PLACEMENT_RULESET

SCHEMA = "sig.dossier-sources/1"
RUNS_ROW_SCHEMA = "sig.dossier-source-run/1"
WEB_DIR = "web/dossier_sources"

#: The ``claim_sightings`` aggregate's positional column contract — the SELECT
#: list below lands exactly this order; tests close on it.
CLAIM_SIGHTINGS_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "subject_id",
    "predicate_id",
    "source_id",
    "first_seen_at",
    "last_seen_at",
    "first_run_id",
    "last_run_id",
    "sighting_runs",
    "sighting_links",
    "has_actual_capture",
    "sighting_run_ids",
    "sighting_months",
    "sighting_artifact_ids",
)

#: The K5 §3.1 aggregate over ``v_claim_sightings`` — explicit columns, grouped
#: by (claim, subject, predicate, sighting source). The shared publishable-claim
#: gates apply at query time: ``{PUB_CLAIM_GATE}`` (subject + object entity +
#: claim dispositions), ``{PUB_ARTIFACT_GATE}`` (a withheld artifact's sightings
#: never count), ``{CAPTURE_SEAL_GATE}`` (a capture under a current seal loses
#: its binding), and effective rights via ``latest_decision`` —
#: ``rr.redistributable = 'yes'`` under the SIGHTING source's decision context
#: (the same posture every sibling claim read takes). ``{SIGHTING_BOUND}`` is
#: the belief bound the module substitutes (``BELIEF_PARAM``/``BELIEF_NOW``) —
#: a binding recorded after the belief cut is not a sighting.
DOSSIER_SOURCES_QUERIES: dict[str, tuple[str, str]] = {
    "claim_sightings": (
        "v_claim_sightings",
        "{EFFECTIVE}"
        # Contribution attribution is by the claim's source of record
        # (``claim_source`` — the spine's own "who asserted this" occurrence
        # pick), never the link's artifact source: a shared-establishment
        # claim sighted through a sibling source's capture contributes to
        # the asserting source's row, keeping ``contributions[]`` consistent
        # with J3's ``published_claims`` (recorded decision, run ledger).
        "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id, cs.source_id,"
        "       min(c.retrieved_at) AS first_seen_at,"
        "       max(c.retrieved_at) AS last_seen_at,"
        "       (array_agg(c.run_id ORDER BY c.retrieved_at, c.run_id))[1]::text AS first_run_id,"
        "       (array_agg(c.run_id ORDER BY c.retrieved_at DESC, c.run_id DESC))[1]::text"
        "         AS last_run_id,"
        "       count(DISTINCT c.run_id) AS sighting_runs,"
        "       count(*) AS sighting_links,"
        "       bool_or(c.binding_status = 'actual_capture') AS has_actual_capture,"
        "       array_agg(DISTINCT c.run_id::text) FILTER (WHERE c.run_id IS NOT NULL)"
        "         AS sighting_run_ids,"
        "       array_agg(DISTINCT date_trunc('month', c.retrieved_at AT TIME ZONE 'UTC')::text)"
        "         FILTER (WHERE c.retrieved_at IS NOT NULL) AS sighting_months,"
        "       array_agg(DISTINCT c.artifact_id::text) AS sighting_artifact_ids"
        "  FROM v_claim_sightings c"
        "  JOIN claim_evidence ce"
        "    ON ce.claim_id = c.claim_id AND ce.capture_id = c.capture_id AND ce.role = c.role"
        "  JOIN evidence_artifact ea ON ea.artifact_id = c.artifact_id"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "    ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND c.bound_at <= {SIGHTING_BOUND}"
        "   AND rr.redistributable = 'yes'"
        "   AND {PUB_CLAIM_GATE}"
        "   AND {PUB_ARTIFACT_GATE}"
        "   AND {CAPTURE_SEAL_GATE}"
        " GROUP BY 1,2,3,4"
        " ORDER BY 1,2,3,4",
    ),
}

#: Placement-registry levels that carry a per-(source, run) ``.runs.jsonl.gz``
#: — K5 §3.2: country and admin-1 dossiers only; county/place dossiers carry
#: the monthly ``series`` and link the source's own run log.
RUNS_FILE_LEVELS: frozenset[str] = frozenset({"country", "state_province"})

#: The disagreement checks that count as the declared↔located pair (the same
#: two tokens ``placement.build_report``'s ``disclosures`` uses — one rule).
_DISAGREE_CHECKS: frozenset[str] = frozenset({"outside_declared", "outside_declared_country"})
_OPEN_CONTRADICTION_STATES: frozenset[str] = frozenset({"open", "under_research"})
_UNRESOLVED = "unresolved"
_RUN_LEVEL_ONLY_REASON = (
    "re-sighting links not recorded for this source — every claim carries "
    "exactly one establishing link across more than one completed run"
)

#: ``assert_documented`` columns for the ``dossier_source_runs`` resource —
#: one row per (source, run) in a ``*.runs.jsonl.gz`` file.
DOSSIER_SOURCE_RUN_COLUMNS: tuple[str, ...] = (
    "schema",
    "source_id",
    "run_id",
    "started_at",
    "finished_at",
    "status",
    "claims_first_seen",
    "claims_resighted",
    "records_first_seen",
)


def _column_specs() -> tuple[Any, ...]:
    from .column_registry import ColumnSpec as _CS

    return (
        _CS(
            "schema",
            "the row's schema id",
            nullable=False,
            declared_values=(RUNS_ROW_SCHEMA,),
        ),
        _CS("source_id", "the registry source the run belongs to", nullable=False),
        _CS("run_id", "the ingest run identifier", nullable=False),
        _CS("started_at", "the run's recorded start instant", dtype="datetime"),
        _CS("finished_at", "the run's recorded finish instant", dtype="datetime"),
        _CS(
            "status",
            "the run's completion status (``ok``/``partial``/``quota_reached``/"
            "``failed``; ``null`` where the shared-run row carries none)",
        ),
        _CS(
            "claims_first_seen",
            "published claims this source first sighted in this run within the dossier's records",
            dtype="integer",
            nullable=False,
            unit="count",
        ),
        _CS(
            "claims_resighted",
            "published claims this source re-sighted in this run that it had "
            "already first-seen earlier",
            dtype="integer",
            nullable=False,
            unit="count",
        ),
        _CS(
            "records_first_seen",
            "dossier records whose earliest sighting by this source landed in this run",
            dtype="integer",
            nullable=False,
            unit="count",
        ),
    )


#: P35.39 (SIG-TRANSP-016): the runs-file column specs, declared beside the
#: writer and aggregated by ``column_registry`` as ``dossier_source_runs``.
DOSSIER_SOURCE_RUN_SPECS = _column_specs()


def _instant(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _month(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m") if value is not None else None


@dataclass(frozen=True)
class _Sighting:
    """One parsed ``claim_sightings`` row — a (claim, source) group."""

    claim_id: str
    subject_id: str
    predicate_id: str
    source_id: str
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    first_run_id: str | None
    last_run_id: str | None
    sighting_links: int
    has_actual_capture: bool
    run_ids: frozenset[str]
    months: frozenset[str]
    artifact_ids: frozenset[str]


def _parse_sightings(rows: Iterable[Sequence[Any]]) -> list[_Sighting]:
    """Parse the positional ``claim_sightings`` rows (CLAIM_SIGHTINGS_COLUMNS)."""
    out: list[_Sighting] = []
    for r in rows:
        row = dict(zip(CLAIM_SIGHTINGS_COLUMNS, r, strict=False))
        run_ids = frozenset(str(x) for x in (row.get("sighting_run_ids") or ()))
        months = frozenset(
            m for m in (str(x)[:7] for x in (row.get("sighting_months") or ())) if m and len(m) == 7
        )
        out.append(
            _Sighting(
                claim_id=str(row["claim_id"]),
                subject_id=str(row["subject_id"]),
                predicate_id=str(row["predicate_id"]),
                source_id=str(row["source_id"]),
                first_seen_at=_instant(row.get("first_seen_at")),
                last_seen_at=_instant(row.get("last_seen_at")),
                first_run_id=(str(row["first_run_id"]) if row.get("first_run_id") else None),
                last_run_id=(str(row["last_run_id"]) if row.get("last_run_id") else None),
                sighting_links=int(row.get("sighting_links") or 0),
                has_actual_capture=bool(row.get("has_actual_capture")),
                run_ids=run_ids,
                months=months,
                artifact_ids=frozenset(str(x) for x in (row.get("sighting_artifact_ids") or ())),
            )
        )
    return out


@dataclass
class _RunRow:
    """One source's ingest run, merged across its report rows."""

    run_id: str
    started_at: Any = None
    finished_at: Any = None
    status: str | None = None

    def absorb(self, other: Mapping[str, Any]) -> None:
        st = other.get("started_at")
        fi = other.get("finished_at")
        if st is not None and (self.started_at is None or str(st) < str(self.started_at)):
            self.started_at = st
        if fi is not None and (self.finished_at is None or str(fi) > str(self.finished_at)):
            self.finished_at = fi
        if self.status is None and other.get("completion_status") is not None:
            self.status = str(other["completion_status"])


@dataclass
class _SourceAcc:
    """The per-(dossier key, source) accumulation."""

    subjects: set[str] = field(default_factory=set)
    #: P35.45: the placed leg — subjects whose recorded chain contains this
    #: key (the dossier's ``records`` count; ``subjects`` stays the
    #: declared-or-placed "appearing" set).
    placed_subjects: set[str] = field(default_factory=set)
    #: Subjects whose chain LEAF is this key — "records placed only here",
    #: the roll-up's additive term (parent = own leaf + Σ children placed).
    leaf_subjects: set[str] = field(default_factory=set)
    #: Placed-leg subjects this source located by point — the per-source
    #: leg of the dossier's ``records_located_by_point`` figure.
    placed_point_subjects: set[str] = field(default_factory=set)
    compartments: set[str] = field(default_factory=set)
    entity_types: dict[str, str] = field(default_factory=dict)
    techs: dict[str, set[str]] = field(default_factory=dict)
    basis: Counter[str] = field(default_factory=Counter)
    checks: Counter[str] = field(default_factory=Counter)
    conflicted: set[str] = field(default_factory=set)
    claims: dict[str, _Sighting] = field(default_factory=dict)
    run_cfs: Counter[str] = field(default_factory=Counter)
    run_crs: Counter[str] = field(default_factory=Counter)
    run_rfs: Counter[str] = field(default_factory=Counter)
    month_cfs: Counter[str] = field(default_factory=Counter)
    month_crs: Counter[str] = field(default_factory=Counter)
    month_rfs: Counter[str] = field(default_factory=Counter)
    artifacts: set[str] = field(default_factory=set)
    contradictions: set[str] = field(default_factory=set)
    #: This source's records in this dossier carrying an outside_declared*
    #: check (the figure's per-source disagreement leg).
    declared_here_located_elsewhere: int = 0


@dataclass
class _DossierAcc:
    """The per-dossier-key accumulation."""

    key: str
    subjects: dict[str, set[str]] = field(default_factory=dict)  # subject → sources
    #: subject → sources — the placed leg (chain membership). ``records``
    #: on the dossier page is ``len(placed_subjects)`` (K4 §5.2 "published
    #: observation-level records placed here").
    placed_subjects: dict[str, set[str]] = field(default_factory=dict)
    #: subjects whose chain leaf is this key — the additive roll-up term.
    leaf_subjects: set[str] = field(default_factory=set)
    #: P35.45: leaf jkey → the placed members whose chain ends at that leaf
    #: AND carries this key (every member except this dossier's own leaf
    #: rows). The roll-up's leaf partition: ``records == leaf + Σ over these
    #: leaf keys' member counts`` — exact under placement@1 even when a
    #: record's recorded chain spans registry siblings (a place and its
    #: containing county are both registry children of the state, yet a
    #: point-placed record's chain lists both).
    leaf_members: dict[str, set[str]] = field(default_factory=dict)
    #: Placed-leg subjects whose basis is ``point_in_polygon`` — the
    #: dossier's "n of N located by point" numerator (distinct subjects).
    placed_point_subjects: set[str] = field(default_factory=set)
    compartments: set[str] = field(default_factory=set)
    claims: dict[str, list[_Sighting]] = field(default_factory=dict)  # claim → (source) rows
    by_source: dict[str, _SourceAcc] = field(default_factory=dict)
    contradictions_open: set[str] = field(default_factory=set)
    declared_elsewhere_pairs: Counter[str] = field(default_factory=Counter)
    located_elsewhere_pairs: Counter[str] = field(default_factory=Counter)

    def source(self, source_id: str) -> _SourceAcc:
        return self.by_source.setdefault(source_id, _SourceAcc())


@dataclass
class DossierContributionPlan:
    """The one shared accumulation (K5 §3.1–3.3 + TRANSP-040).

    ``contributions_by_source`` is the source-side mirror consumed by
    ``emit_transparency_artifacts`` (``transparency/sources.json`` rows); the
    dossier artifacts render through :meth:`render` once that file exists —
    the same accumulated rows feed both (never a second computation).
    """

    contributions_by_source: dict[str, list[dict[str, Any]]]
    dossiers: dict[str, _DossierAcc]
    runs_by_source: dict[str, dict[str, _RunRow]]
    latest_ok_run: dict[str, _RunRow]
    run_level_only: dict[str, bool]
    placement_bound: bool
    release: dict[str, Any]
    ruleset_version: str
    weight_rows: list[dict[str, Any]]
    lineage_by_claim: dict[str, str] | None
    as_of_date: date
    engine: Any = None  # exports.placement.PlacementEngine | None
    #: P35.45: the keyed registry (None pre-placement) + the
    #: ``dossier-key -> slug_path`` map every artifact path resolves through.
    keyed: _dk.KeyedRegistry | None = None
    slug_paths: dict[str, str] = field(default_factory=dict)

    def slug_path(self, key: str) -> str:
        """The dossier artifact/URL path for a membership key — the registry
        slug path for canonical keys, ``unplaced`` for the sentinel, and the
        flat ``jurisdiction_slug`` for a non-registry declared bucket (the
        honest named bucket, never a guessed path)."""
        cached = self.slug_paths.get(key)
        if cached is not None:
            return cached
        if key == _dk.UNPLACED:
            path = _dk.UNPLACED
        elif self.keyed is not None and key in self.keyed.keys:
            path = self.keyed.keys[key].slug_path
        else:
            path = jurisdiction_slug(key)
        self.slug_paths[key] = path
        return path

    def render(
        self,
        transparency_artifacts: Mapping[str, bytes],
    ) -> dict[str, bytes]:
        """Emit ``web/dossier_sources/<slug-path>.json`` (+ ``.runs.jsonl.gz``).

        ``transparency_artifacts`` is the emit_transparency_artifacts output —
        the sources.json/freshness/issues rows supply the registry display
        fields (name, licence, lifecycle, freshness_state, known issues) so the
        dossier source rows and the source page show one derivation.
        """
        source_rows, freshness, issues = _read_back(transparency_artifacts)
        out: dict[str, bytes] = {}
        for key in sorted(self.dossiers):
            acc = self.dossiers[key]
            slug = self.slug_path(key)
            doc = self._dossier_doc(acc, slug, source_rows, freshness, issues)
            path = f"{WEB_DIR}/{slug}.json"
            out[path] = (
                json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            if doc["runs_file"]:
                rows = self._run_rows(acc)
                payload = "".join(
                    json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows
                ).encode("utf-8")
                out[f"{WEB_DIR}/{slug}.runs.jsonl.gz"] = _gzip0(payload)
        return out

    # -- per-dossier document ------------------------------------------------

    def _dossier_doc(
        self,
        acc: _DossierAcc,
        slug: str,
        source_rows: Mapping[str, Mapping[str, Any]],
        freshness: Mapping[str, Mapping[str, Any]],
        issues: Mapping[str, list[str]],
    ) -> dict[str, Any]:
        info = self.keyed.keys.get(acc.key) if self.keyed is not None else None
        jrow = self.engine.jurisdiction_row(acc.key) if self.engine is not None else None
        if acc.key == _dk.UNPLACED:
            # "Not yet placed" is a data-quality state, never a place — the
            # report says so in its own name and carries no registry fields.
            jurisdiction: dict[str, Any] = {
                "jkey": None,
                "slug_path": _dk.UNPLACED,
                "name": "Not yet placed (data-quality report)",
                "level": None,
                "chain": [],
                "boundary_vintage": None,
                "unplaced": True,
            }
            level = None
        elif info is not None:
            jurisdiction = {
                "jkey": acc.key,
                "slug_path": slug,
                "name": info.name,
                "level": info.level,
                "chain": [a for a in info.chain if a != acc.key],
                "boundary_vintage": info.vintage,
            }
            level = info.level
        else:
            # A non-registry declared bucket: the slug stays the flat honest
            # bucket (P35.18-style), named by its own key — never a guessed
            # registry row.
            level = str(jrow.get("level")) if jrow and jrow.get("level") else None
            jurisdiction = {
                "jkey": acc.key,
                "slug_path": slug,
                "name": str(jrow.get("name")) if jrow and jrow.get("name") else acc.key,
                "level": level,
                "chain": (
                    [a for a in self.engine.ancestor_chain(acc.key) if a != acc.key]
                    if self.engine is not None
                    else []
                ),
                "boundary_vintage": (
                    str(jrow.get("vintage")) if jrow and jrow.get("vintage") else None
                ),
            }
        runs_level = level in RUNS_FILE_LEVELS
        path = f"{WEB_DIR}/{slug}.json"

        source_docs = [
            self._source_doc(acc, sid, sacc, source_rows, freshness, issues, runs_level)
            for sid, sacc in sorted(acc.by_source.items())
        ]
        totals = self._totals(acc, source_docs)
        figures = self._figures(acc, source_docs, totals, path)
        contradictions_list = sorted(acc.contradictions_open)
        runs_file = f"{WEB_DIR}/{slug}.runs.jsonl.gz" if runs_level else None
        weight_scoped = [r for r in self.weight_rows if r["claim_id"] in acc.claims]
        lineage_classes = (
            {self.lineage_by_claim[cid] for cid in acc.claims if self.lineage_by_claim.get(cid)}
            if self.lineage_by_claim is not None
            else set()
        )
        independent_lineages: Any = (
            len(lineage_classes)
            if self.lineage_by_claim is not None and lineage_classes
            else (
                {"not_evaluable": "claim_lineage read absent (pre-P35.25 spine)"}
                if self.lineage_by_claim is None
                else {"not_evaluable": "no declared lineage classes among dossier claims"}
            )
        )
        return {
            "schema": SCHEMA,
            "release": self.release,
            "jurisdiction": jurisdiction,
            "definitions": _DEFINITIONS,
            "totals": totals,
            "provenance_summary": {
                "artifact_count": len(
                    {a for rows in acc.claims.values() for s in rows for a in s.artifact_ids}
                ),
                "tier_distribution": analytics._tier_distribution(weight_scoped, self.as_of_date),
                "sources_with_published_claims": len(
                    {s.source_id for rows in acc.claims.values() for s in rows}
                ),
                "independent_lineages": independent_lineages,
                "date_range": analytics._date_range(weight_scoped),
                "rules_applied": [PLACEMENT_RULESET, self.ruleset_version],
                "human_review_status": "unreviewed",
                "scope": "dossier",
            },
            "figures": figures,
            "sources": source_docs,
            "cross_source": {
                "colocated_pairs": {
                    "not_evaluable": "observation_group not yet exported (DSRC-04)"
                },
                "contradictions": [{"contradiction_id": cid} for cid in contradictions_list],
            },
            "placement": {
                "rules": PLACEMENT_RULESET,
                "by_basis": dict(
                    sorted(
                        Counter(
                            b for _, s in acc.by_source.items() for b in s.basis.elements()
                        ).items()
                    )
                ),
                "declared_elsewhere_located_here": [
                    {"jkey": k, "records": n}
                    for k, n in sorted(acc.declared_elsewhere_pairs.items())
                ],
                "declared_here_located_elsewhere": [
                    {"jkey": k, "records": n}
                    for k, n in sorted(acc.located_elsewhere_pairs.items())
                ],
            },
            "runs_file": runs_file,
            "downloads": [],
        }

    def _totals(
        self,
        acc: _DossierAcc,
        source_docs: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        rows = [s for claim_rows in acc.claims.values() for s in claim_rows]
        first = min((s.first_seen_at for s in rows if s.first_seen_at), default=None)
        last = max((s.last_seen_at for s in rows if s.last_seen_at), default=None)
        entity_types: Counter[str] = Counter()
        techs: Counter[str] = Counter()
        conflicted: set[str] = set()
        basis: Counter[str] = Counter()
        located_pairs = declared_pairs = 0
        for sacc in acc.by_source.values():
            basis.update(sacc.basis)
            conflicted |= sacc.conflicted
            located_pairs += sacc.basis.get("point_in_polygon", 0)
            declared_pairs += sacc.basis.get("declared", 0) + sacc.basis.get("name_lookup", 0)
            for subj in sacc.subjects:
                et = sacc.entity_types.get(subj)
                if et:
                    entity_types[et] += 1
                tset = sacc.techs.get(subj) or {"not_typed"}
                for t in sorted(tset):
                    techs[t] += 1
        claims_by_pred: Counter[str] = Counter()
        for claim_rows in acc.claims.values():
            claims_by_pred[claim_rows[0].predicate_id] += 1
        return {
            # ``records`` stays the declared-or-placed "appearing" count the
            # K5 definitions name; the dossier page's headline is
            # ``records_placed`` (K4 §5.2 "records placed here").
            "records": len(acc.subjects),
            "records_placed": len(acc.placed_subjects),
            "records_placed_only_here": len(acc.leaf_subjects),
            "records_located_by_point": len(acc.placed_point_subjects),
            "located_by_point": located_pairs,
            "placed_by_declared": declared_pairs,
            "claims": len(acc.claims),
            "sources": len(acc.by_source),
            "compartments": sorted(acc.compartments),
            "first_seen_at": iso_utc(first),
            "last_seen_at": iso_utc(last),
            "claims_by_predicate": dict(sorted(claims_by_pred.items())),
            "records_by_entity_type": dict(sorted(entity_types.items())),
            "records_by_technology": dict(sorted(techs.items())),
            "coordinate_conflicts_intra_source": len(conflicted),
            "declared_here_located_elsewhere": sum(acc.located_elsewhere_pairs.values()),
            "located_here_declared_elsewhere": sum(acc.declared_elsewhere_pairs.values()),
            "contradictions_open": len(acc.contradictions_open),
            "cross_source_colocated_candidates": {
                "not_evaluable": "observation_group not yet exported (DSRC-04)"
            },
        }

    def _figures(
        self,
        acc: _DossierAcc,
        source_docs: Sequence[Mapping[str, Any]],
        totals: Mapping[str, Any],
        path: str,
    ) -> list[dict[str, Any]]:
        """The material figures with their ``by_source`` reconciliation."""

        def _by_source(field: str) -> list[dict[str, Any]]:
            return [{"source_id": str(d["source_id"]), "value": int(d[field])} for d in source_docs]

        def _rule(field: str, distinct_value: int) -> tuple[str, str | None]:
            """``sum`` while source slices partition the total; ``distinct`` —
            disclosed — the moment a record/claim sits under >1 source."""
            summed = sum(int(d[field]) for d in source_docs)
            if summed == distinct_value:
                return "sum", None
            return (
                "distinct",
                "a record/claim can carry contributions from several sources; "
                "the by_source values overlap — deduplicate, never sum",
            )

        figures: list[dict[str, Any]] = []
        for figure_id, label, field_name, pointer in (
            ("records", "Records (appearing)", "records", "/totals/records"),
            (
                "records_placed",
                "Records placed here",
                "records_placed",
                "/totals/records_placed",
            ),
            (
                "fig-map",
                "Records drawn on the map",
                "records_located_by_point",
                "/totals/records_located_by_point",
            ),
            ("claims", "Claims", "claims", "/totals/claims"),
            (
                "declared_here_located_elsewhere",
                "Declared here, located elsewhere",
                "_declared_here",
                "/totals/declared_here_located_elsewhere",
            ),
            (
                "coordinate_conflicts_intra_source",
                "Intra-source coordinate conflicts",
                "coordinate_conflicts_intra_source",
                "/totals/coordinate_conflicts_intra_source",
            ),
            ("sources", "Sources", "_one", "/totals/sources"),
        ):
            if field_name == "_declared_here":
                by_source: list[dict[str, Any]] = [
                    {
                        "source_id": str(d["source_id"]),
                        "value": int(d["declared_here_located_elsewhere"] or 0),
                    }
                    for d in source_docs
                ]
                summed = sum(int(b["value"]) for b in by_source)
                rule = "sum" if summed == totals["declared_here_located_elsewhere"] else "distinct"
                disclosure = (
                    None
                    if rule == "sum"
                    else "a record can sit under several sources — deduplicate, never sum"
                )
                value = totals["declared_here_located_elsewhere"]
            elif field_name == "_one":
                by_source = [{"source_id": str(d["source_id"]), "value": 1} for d in source_docs]
                rule, disclosure, value = "sum", None, totals["sources"]
            else:
                distinct_value = int(totals[field_name])
                rule, disclosure = _rule(field_name, distinct_value)
                by_source = _by_source(field_name)
                value = distinct_value
            fig: dict[str, Any] = {
                "figure_id": figure_id,
                "label": label,
                "value": value,
                "definition": (
                    field_name.strip("_") if not field_name.startswith("_") else figure_id
                ),
                "artifact": path,
                "pointer": pointer,
                "by_source": by_source,
                "sum_rule": rule,
            }
            if disclosure:
                fig["sum_disclosure"] = disclosure
            figures.append(fig)
        return figures

    def _source_doc(
        self,
        acc: _DossierAcc,
        source_id: str,
        sacc: _SourceAcc,
        source_rows: Mapping[str, Mapping[str, Any]],
        freshness: Mapping[str, Mapping[str, Any]],
        issues: Mapping[str, list[str]],
        runs_level: bool,
    ) -> dict[str, Any]:
        reg = source_rows.get(source_id) or {}
        licence = reg.get("licence") or {}
        claims = sacc.claims
        first = min((s.first_seen_at for s in claims.values() if s.first_seen_at), default=None)
        last = max((s.last_seen_at for s in claims.values() if s.last_seen_at), default=None)
        dated = [s for s in claims.values() if s.first_seen_at is not None]
        dated_last = [s for s in claims.values() if s.last_seen_at is not None]
        first_run = (
            min(dated, key=lambda s: (s.first_seen_at, s.claim_id)).first_run_id if dated else None
        )
        last_run = (
            max(dated_last, key=lambda s: (s.last_seen_at, s.claim_id)).last_run_id
            if dated_last
            else None
        )
        run_level_only = self.run_level_only.get(source_id, False)
        latest = self.latest_ok_run.get(source_id)
        claims_by_pred: Counter[str] = Counter()
        for s in claims.values():
            claims_by_pred[s.predicate_id] += 1
        entity_types: Counter[str] = Counter()
        techs: Counter[str] = Counter()
        for subj in sacc.subjects:
            et = sacc.entity_types.get(subj)
            if et:
                entity_types[et] += 1
            for t in sorted(sacc.techs.get(subj) or {"not_typed"}):
                techs[t] += 1
        if run_level_only:
            sightings = "run_level_only"
            last_seen: dict[str, Any] = {"not_recorded": _RUN_LEVEL_ONLY_REASON}
            not_reasserted: Any = {"not_evaluable": _RUN_LEVEL_ONLY_REASON}
        else:
            sightings = "per_run"
            last_seen = {"at": iso_utc(last), "run_id": last_run}
            if latest is None:
                not_reasserted = {"not_evaluable": "no completed run recorded"}
            else:
                not_reasserted = sum(
                    1
                    for s in claims.values()
                    if s.last_run_id is not None and s.last_run_id != latest.run_id
                )
        compartments = sorted(sacc.compartments)
        row: dict[str, Any] = {
            "source_id": source_id,
            "name": str(reg.get("name") or source_id),
            "publisher": reg.get("publisher"),
            "publisher_type": reg.get("publisher_type"),
            "lifecycle": reg.get("lifecycle_state"),
            "source_page": f"/sources/{source_id}/",
            "runs_page": f"/sources/{source_id}/runs/",
            "licence": {
                "spdx": licence.get("spdx"),
                "compartment": compartments[0] if len(compartments) == 1 else None,
                "compartments": compartments,
                "attribution": licence.get("attribution"),
            },
            "records": len(sacc.subjects),
            "records_placed": len(sacc.placed_subjects),
            "records_placed_only_here": len(sacc.leaf_subjects),
            "records_located_by_point": len(sacc.placed_point_subjects),
            "share": (round(len(sacc.subjects) / len(acc.subjects), 4) if acc.subjects else 0),
            "located_by_point": sacc.basis.get("point_in_polygon", 0),
            "placed_by_declared": sacc.basis.get("declared", 0) + sacc.basis.get("name_lookup", 0),
            "claims": len(claims),
            "claims_by_predicate": dict(sorted(claims_by_pred.items())),
            "records_by_entity_type": dict(sorted(entity_types.items())),
            "records_by_technology": dict(sorted(techs.items())),
            "placement_checks": dict(sorted(sacc.checks.items())),
            "first_seen": {"at": iso_utc(first), "run_id": first_run},
            "last_seen": last_seen,
            "sightings": sightings,
            "latest_run": (
                {
                    "run_id": latest.run_id,
                    "finished_at": iso_utc(latest.finished_at),
                    "status": latest.status,
                }
                if latest is not None
                else {"not_recorded": "no completed run recorded"}
            ),
            "freshness_state": str(
                (freshness.get(source_id) or {}).get("freshness_state") or "not_recorded"
            ),
            "not_reasserted_in_latest_complete_run": not_reasserted,
            "coordinate_conflicts_intra_source": len(sacc.conflicted),
            "declared_here_located_elsewhere": sacc.declared_here_located_elsewhere,
            "contradictions": sorted(sacc.contradictions),
            "series": [
                {
                    "period": m,
                    "records_first_seen": sacc.month_rfs.get(m, 0),
                    "claims_first_seen": sacc.month_cfs.get(m, 0),
                    "claims_resighted": sacc.month_crs.get(m, 0),
                }
                for m in sorted(set(sacc.month_cfs) | set(sacc.month_crs) | set(sacc.month_rfs))
            ],
            "downloads": [],
            "known_issues": sorted(issues.get(source_id, ())),
        }
        return row

    def _run_rows(self, acc: _DossierAcc) -> list[dict[str, Any]]:
        """One row per (source, run) — every recorded run of every contributing
        source, dossier counts filled from the accumulation (0 is a counted
        fact: the source ran and sighted nothing here)."""
        out: list[dict[str, Any]] = []
        for sid in sorted(acc.by_source):
            sacc = acc.by_source[sid]
            runs = self.runs_by_source.get(sid, {})
            for run_id in sorted(runs):
                r = runs[run_id]
                out.append(
                    {
                        "schema": RUNS_ROW_SCHEMA,
                        "source_id": sid,
                        "run_id": run_id,
                        "started_at": iso_utc(r.started_at),
                        "finished_at": iso_utc(r.finished_at),
                        "status": r.status,
                        "claims_first_seen": sacc.run_cfs.get(run_id, 0),
                        "claims_resighted": sacc.run_crs.get(run_id, 0),
                        "records_first_seen": sacc.run_rfs.get(run_id, 0),
                    }
                )
        return out


#: The named, footnoted definitions the schema carries (K5 §3.2 — every count
#: names what it counts, never an implied census).
_DEFINITIONS: dict[str, str] = {
    "records": (
        "distinct published observation-level records (subjects) appearing in "
        "this dossier — through their declared bucket or any ancestor of their "
        "placement chain (K4 §5.3 roll-up); never a resolved device census "
        "(SIG-RECON-058). P35.45: 'appearing' = declared OR placed; the "
        "dossier page's headline count is records_placed"
    ),
    "records_placed": (
        "distinct records whose recorded placement chain contains this "
        "dossier's key (the placed leg — K4 §5.2 'published observation-level "
        "records placed here'); parent = own leaf + Σ children, conserved "
        "by construction"
    ),
    "records_placed_only_here": (
        "distinct records whose placement chain LEAF is this key — placed "
        "at exactly this level, the additive roll-up term"
    ),
    "records_located_by_point": (
        "distinct placed-leg records whose placement basis is "
        "point_in_polygon — 'n of N located' on the dossier page"
    ),
    "located_by_point": (
        "record×source slices whose placement basis is point_in_polygon — the "
        "records the dossier map draws"
    ),
    "placed_by_declared": (
        "record×source slices placed on the declared or name_lookup basis "
        "(no usable point or a withheld one)"
    ),
    "claims": (
        "distinct published claims on dossier records, counted once per "
        "contributing source — a claim sighted through two sources' captures "
        "contributes to both, disclosed by the figure sum_rule"
    ),
    "claims_by_predicate": "published claims on dossier records by predicate",
    "records_by_entity_type": "distinct dossier records by subject entity type",
    "records_by_technology": (
        "distinct dossier records by declared technology slug; "
        "'not_typed' names records with no resolved technology envelope"
    ),
    "coordinate_conflicts_intra_source": (
        "records whose own coordinate evidence conflicts (the shaping "
        "envelope's 'conflicted' verdict) — a disagreement kept visible, "
        "never resolved silently"
    ),
    "declared_here_located_elsewhere": (
        "records declared in this dossier's jurisdiction whose placement "
        "located them elsewhere (outside_declared checks — the same rows "
        "sig.placement-report/1 counts)"
    ),
    "located_here_declared_elsewhere": (
        "records located in this dossier's jurisdiction that declared a different one"
    ),
    "contradictions_open": (
        "materialized contradiction records on dossier subjects in an open "
        "state (open/under_research) — kept visible, never reconciled"
    ),
    "first_seen": "the earliest establishing-link retrieval instant + its run",
    "last_seen": "the latest establishing-link retrieval instant + its run",
    "share": "the source's fraction of this dossier's distinct records",
    "sightings": (
        "per_run when per-link re-sighting data exists; run_level_only when "
        "every claim carries exactly one establishing link across >1 "
        "completed run (K5 §3.3 — the export cannot separate 'not re-sighted' "
        "from 're-sightings not recorded', so only first-seen is shown)"
    ),
    "not_reasserted_in_latest_complete_run": (
        "claims whose last sighting run differs from the source's latest "
        "status=ok run — the derived stand-in for per-record disappearance "
        "(partial/quota_reached/failed runs excluded)"
    ),
    "cross_source_colocated_candidates": (
        "not_evaluable until DSRC-04 publishes observation_group — the "
        "pairing is deliberately uncomputed"
    ),
    "series": (
        "monthly first-seen claims, re-sighted claims, and first-seen "
        "records for the (dossier, source) pair"
    ),
    "series.records_first_seen": "records whose earliest sighting fell in the month",
    "series.claims_first_seen": "claims first sighted in the month",
    "series.claims_resighted": "claims sighted in the month that were first seen earlier",
}


def _read_back(
    artifacts: Mapping[str, bytes],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, list[str]]]:
    """Read the just-emitted transparency artifacts back — registry display
    fields, freshness states and open issue classes for the dossier source
    rows. One computation: the dossier row and the source page show the same
    derivation (TRANSP-040)."""
    source_rows: dict[str, Mapping[str, Any]] = {}
    freshness: dict[str, Mapping[str, Any]] = {}
    issues: dict[str, list[str]] = {}
    blob = artifacts.get("transparency/sources.json")
    if blob:
        try:
            doc = json.loads(blob.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            doc = {}
        for r in doc.get("sources") or []:
            sid = str(r.get("source_id") or "")
            if sid:
                source_rows[sid] = r
    for line in (artifacts.get("transparency/freshness.jsonl") or b"").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        sid = str(r.get("source_id") or "")
        if sid:
            freshness[sid] = r
    for line in (artifacts.get("transparency/issues.jsonl") or b"").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("closed_at") is None:
            issues.setdefault(str(r.get("source_id") or ""), []).append(
                str(r.get("issue_class") or "")
            )
    return source_rows, freshness, issues


def accumulate_dossier_contributions(
    *,
    sightings_rows: Sequence[Sequence[Any]],
    site_rows: Iterable[tuple[str, str, Mapping[str, Any]]],
    run_rows: Sequence[Sequence[Any]],
    contradictions: Sequence[Mapping[str, Any]],
    weight_rows: Sequence[Mapping[str, Any]],
    lineage_rows: Sequence[Sequence[Any]],
    release: Mapping[str, Any],
    ruleset_version: str,
    as_of: str,
    placement: Any = None,
) -> DossierContributionPlan:
    """The one shared (dossier, source) accumulation (K5 §3.1–3.3).

    ``sightings_rows`` is the ``claim_sightings`` export read; ``site_rows`` is
    the licence-sliced site set as ``(compartment, slice_key, row_data)``;
    ``run_rows`` is the ``transparency_runs`` read (positional,
    TRANSPARENCY_RUN_VIEW_COLUMNS); ``contradictions`` is the materialized
    contradiction set; ``weight_rows`` the normalized ``claim_weights`` dicts
    (``analytics._claim_weight_rows``); ``lineage_rows`` the ``claim_lineage``
    read (``(claim_id, independence_class)`` positional pairs).
    """
    sightings = _parse_sightings(sightings_rows)
    placement_bound = placement is not None

    # --- run records per source (merged across report rows) -----------------
    runs_by_source: dict[str, dict[str, _RunRow]] = {}
    latest_ok_run: dict[str, _RunRow] = {}
    for raw in run_rows:
        r = dict(zip(TRANSPARENCY_RUN_VIEW_COLUMNS, raw, strict=False))
        sid = str(r.get("source_id") or "")
        rid = str(r.get("run_id") or "")
        if not sid or not rid:
            continue
        slot = runs_by_source.setdefault(sid, {})
        if rid in slot:
            slot[rid].absorb(r)
        else:
            merged = _RunRow(run_id=rid)
            merged.absorb(r)
            slot[rid] = merged
    for sid, runs in runs_by_source.items():
        oks = [r for r in runs.values() if r.status == "ok" and r.finished_at is not None]
        if oks:
            latest_ok_run[sid] = max(oks, key=lambda r: (str(r.finished_at), r.run_id))

    # --- the per-source §3.3 check over ALL the source's sightings ----------
    per_source_links: dict[str, int] = {}
    for s in sightings:
        per_source_links[s.source_id] = max(per_source_links.get(s.source_id, 0), s.sighting_links)
    run_level_only = {
        sid: per_source_links.get(sid, 0) <= 1
        and sum(1 for r in runs_by_source.get(sid, {}).values() if r.status == "ok") > 1
        for sid in set(per_source_links) | set(runs_by_source)
    }

    # --- dossier membership + per-(key, source) record slices ----------------
    dossiers: dict[str, _DossierAcc] = {}
    claims_by_subject_source: dict[tuple[str, str], list[_Sighting]] = {}
    for s in sightings:
        claims_by_subject_source.setdefault((s.subject_id, s.source_id), []).append(s)

    record_subjects: dict[tuple[str, str], set[str]] = {}
    for compartment, _slice_key, data in site_rows:
        subject = str(data.get("entity_id") or "")
        source = str(data.get("source_id") or "")
        declared = str(data.get("jurisdiction") or _UNRESOLVED)
        chain = [str(x) for x in (data.get("jurisdiction_chain") or ())]
        leaf = str(data.get("jurisdiction_key") or "") or None
        chain_set = frozenset(chain)
        if placement_bound:
            # group_by_key (P35.45): placed leg = every chain ancestor; a
            # chain-less record files under the ``unplaced`` data-quality
            # sentinel — never ``unresolved`` as if it were a place, never a
            # guessed home. The declared bucket joins only when it names a
            # real key (the disagreement keeps both sides visible).
            placed_keys, declared_keys, _leaf = _dk.group_by_key(data)
            keys = set(placed_keys) | set(declared_keys)
        else:
            keys = {declared, *chain}
        if not subject:
            continue
        for key in sorted(keys):
            acc = dossiers.setdefault(key, _DossierAcc(key=key))
            sacc = acc.source(source)
            # A (subject, source) record counts once even when the subject's
            # slices split across rights records/compartments — the placement
            # verdict is per (source, record), identical across its slices.
            new_subject = subject not in sacc.subjects
            sacc.subjects.add(subject)
            sacc.compartments.add(str(compartment))
            acc.compartments.add(str(compartment))
            acc.subjects.setdefault(subject, set()).add(source)
            if key in chain_set:
                sacc.placed_subjects.add(subject)
                acc.placed_subjects.setdefault(subject, set()).add(source)
                if leaf == key:
                    sacc.leaf_subjects.add(subject)
                    acc.leaf_subjects.add(subject)
                elif leaf is not None:
                    acc.leaf_members.setdefault(leaf, set()).add(subject)
            elif not placement_bound:
                # A pre-placement export: the declared bucket IS the record's
                # placement (no chain exists to distinguish), so every member
                # is placed — and leaf — at its own bucket.
                sacc.placed_subjects.add(subject)
                acc.placed_subjects.setdefault(subject, set()).add(source)
                sacc.leaf_subjects.add(subject)
                acc.leaf_subjects.add(subject)
            et = str(data.get("entity_type") or "")
            if et:
                sacc.entity_types[subject] = et
            tech = str(data.get("technology") or "")
            if tech:
                sacc.techs.setdefault(subject, set()).add(tech)
            check = data.get("placement_check")
            if new_subject:
                basis = data.get("placement_basis")
                if basis:
                    sacc.basis[str(basis)] += 1
                if check:
                    sacc.checks[str(check)] += 1
                if str(data.get("point_status") or "") == "conflicted":
                    sacc.conflicted.add(subject)
            if (
                placement_bound
                and key in chain_set
                and str(data.get("placement_basis") or "") == "point_in_polygon"
            ):
                sacc.placed_point_subjects.add(subject)
                acc.placed_point_subjects.add(subject)
            record_subjects.setdefault((key, source), set()).add(subject)
            # The both-sides disagreement reading (placement.build_report's
            # rule): outside_declared* checks place a (declared → located)
            # row on BOTH dossiers.
            if (
                new_subject
                and str(check or "") in _DISAGREE_CHECKS
                and data.get("jurisdiction_key")
            ):
                located = str(data["jurisdiction_key"])
                if declared == key and located != declared:
                    acc.located_elsewhere_pairs[located] += 1
                    sacc.declared_here_located_elsewhere += 1
                if located == key and declared != located:
                    acc.declared_elsewhere_pairs[declared] += 1

    # --- claims: every publishable sighting on a dossier member -------------
    for s in sightings:
        for key in dossiers:
            if s.subject_id not in dossiers[key].subjects:
                continue
            acc = dossiers[key]
            sacc = acc.source(s.source_id)
            sacc.claims[s.claim_id] = s
            acc.claims.setdefault(s.claim_id, []).append(s)
            sacc.artifacts.update(s.artifact_ids)
            if s.first_run_id:
                sacc.run_cfs[s.first_run_id] += 1
            for rid in s.run_ids:
                if rid != s.first_run_id:
                    sacc.run_crs[rid] += 1
            first_month = _month(s.first_seen_at)
            if first_month:
                sacc.month_cfs[first_month] += 1
            for m in s.months:
                if m != first_month:
                    sacc.month_crs[m] += 1

    # --- records_first_seen: a record's earliest sighting by this source ----
    for (key, source), subjects in record_subjects.items():
        rs_acc = dossiers[key].by_source.get(source)
        if rs_acc is None:
            continue
        for subject in subjects:
            candidates = [
                c
                for c in claims_by_subject_source.get((subject, source), ())
                if c.claim_id in rs_acc.claims
            ]
            dated = [c for c in candidates if c.first_seen_at is not None]
            if not dated:
                continue
            first = min(dated, key=lambda c: (c.first_seen_at, c.claim_id))
            month = _month(first.first_seen_at)
            if month:
                rs_acc.month_rfs[month] += 1
            if first.first_run_id:
                rs_acc.run_rfs[first.first_run_id] += 1

    # --- contradictions placed through their subject ------------------------
    for c in contradictions or []:
        subject = str(c.get("subject_id") or "")
        status = str(c.get("status") or "")
        cid = str(c.get("contradiction_id") or "")
        if not cid:
            continue
        claim_ids = {str(x) for x in (c.get("claim_ids") or ())}
        for _key, acc in dossiers.items():
            if subject not in acc.subjects:
                continue
            if status in _OPEN_CONTRADICTION_STATES:
                acc.contradictions_open.add(cid)
            for source in acc.subjects.get(subject, ()):
                sacc = acc.by_source[source]
                own = {cid2 for cid2 in sacc.claims}
                if claim_ids & own:
                    sacc.contradictions.add(cid)

    # --- the keyed registry + slug paths (P35.45) -----------------------------
    keyed: _dk.KeyedRegistry | None = None
    if placement_bound:
        rows_map = (
            placement.jurisdiction_rows()
            if hasattr(placement, "jurisdiction_rows")
            else {
                str(r["jkey"]): r
                for k in dossiers
                if (r := placement.jurisdiction_row(k)) is not None
            }
        )
        chains = (
            placement.ancestor_chains()
            if hasattr(placement, "ancestor_chains")
            else {k: tuple(placement.ancestor_chain(k)) for k in rows_map}
        )
        keyed = _dk.keyed_registry(list(rows_map.values()), chains)

    # --- the source-side mirror (TRANSP-040: the same numbers) ---------------
    plan_stub = DossierContributionPlan(
        contributions_by_source={},
        dossiers=dossiers,
        runs_by_source=runs_by_source,
        latest_ok_run=latest_ok_run,
        run_level_only=run_level_only,
        placement_bound=placement_bound,
        release=dict(release),
        ruleset_version=ruleset_version,
        weight_rows=[dict(r) for r in weight_rows],
        lineage_by_claim=None,
        as_of_date=date.fromisoformat(str(as_of)[:10]) if as_of else date.today(),
        engine=placement,
        keyed=keyed,
    )
    contributions: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(dossiers):
        acc = dossiers[key]
        slug = plan_stub.slug_path(key)
        for sid in sorted(acc.by_source):
            sacc = acc.by_source[sid]
            claims = sacc.claims
            first_at = min(
                (s.first_seen_at for s in claims.values() if s.first_seen_at), default=None
            )
            last_at = max((s.last_seen_at for s in claims.values() if s.last_seen_at), default=None)
            contributions.setdefault(sid, []).append(
                {
                    "dossier_jkey": key if key != _dk.UNPLACED else _dk.UNPLACED,
                    "dossier_slug": slug,
                    "records": len(sacc.subjects),
                    "records_placed": len(sacc.placed_subjects),
                    "claims": len(claims),
                    "first_seen_at": iso_utc(first_at),
                    # §3.3: under run_level_only the dossier row names
                    # ``last_seen`` ``not_recorded`` — the mirror carries the
                    # same named absence, never the single-link instant a
                    # reader could misread as a re-sighting.
                    "last_seen_at": (
                        {"not_recorded": _RUN_LEVEL_ONLY_REASON}
                        if run_level_only.get(sid)
                        else iso_utc(last_at)
                    ),
                }
            )

    weight_norm: list[dict[str, Any]] = [dict(r) for r in weight_rows]
    lineage_by_claim: dict[str, str] | None = None
    if lineage_rows is not None:
        lineage_by_claim = {
            str(r[0]): str(r[1]) for r in lineage_rows if len(r) >= 2 and r[0] is not None
        }
    as_of_date = date.fromisoformat(str(as_of)[:10]) if as_of else date.today()
    plan_stub.weight_rows = weight_norm
    plan_stub.lineage_by_claim = lineage_by_claim
    plan_stub.as_of_date = as_of_date
    plan_stub.contributions_by_source = contributions
    return plan_stub


__all__ = [
    "CLAIM_SIGHTINGS_COLUMNS",
    "DOSSIER_SOURCES_QUERIES",
    "DOSSIER_SOURCE_RUN_COLUMNS",
    "DOSSIER_SOURCE_RUN_SPECS",
    "DossierContributionPlan",
    "RUNS_ROW_SCHEMA",
    "SCHEMA",
    "WEB_DIR",
    "accumulate_dossier_contributions",
]
