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
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from db.dispositions import (
    artifact_eligible_sql,
    claim_eligible_sql,
    eligible_claim_ids,
    eligible_entity_ids,
    entity_eligible_sql,
)
from db.occurrences import BELIEF_NOW, BELIEF_PARAM, claim_source_cte
from inference.accountability import read_materialized_accountability_links
from inference.materialize import read_materialized_coverage
from policy.labels import (
    EntityLabel,
    LabelFacts,
    derive_label,
    hash4,
    kind_for,
    resolve_disambiguators,
)
from policy.licensing import _registry as _license_registry
from policy.licensing import (
    compute_export_license,
    export_refusal_reason,
)
from policy.licensing import (
    license_url as policy_license_url,
)
from policy.rights import RightsRecord
from policy.source_aliases import resolve_public_text
from policy.transparency import TRANSPARENCY_SOURCE_VIEW_COLUMNS, LaneDecision
from reconcile.materialize import (
    classify_access_kind,
    read_materialized_contradictions,
    read_materialized_edges,
    read_materialized_resolutions,
)
from resolution.camera_sites_pg import read_resolved_site_runs
from resolution.partner_identity import natural_person_signal
from tasks.catalog import catalog as _task_catalog
from tasks.contribution import LeverageLedger
from tasks.osm_feed import ingest_changesets, leverage_metric_json, parse_changesets
from tasks.vocabulary import Disposition

from policy import disclosure as policy_disclosure
from policy import withdrawals as policy_withdrawals

from . import analytics, provo, source_licences
from . import compartments as C
from . import placement as _placement
from . import statements as _stmt
from .audit import _LATEST_DECISION_CTE
from .bundle import Bundle, build_bundle
from .jurisdictions import jurisdiction_slug
from .manifest import (
    PUBLICATION_BASIS,
    Artifact,
    BuildSpec,
    Manifest,
    canonical_json,
    sha256_hex,
)
from .shaping import (
    LAT_PREDICATE,
    LON_PREDICATE,
    SHAPING_SCHEMA_VERSION,
    SHARING_DEGREE_PREDICATES,
    ShapedDataset,
    ShapedSite,
    ShapingClaim,
    SharingEdge,
    parse_shaping_claims,
    shape_sites,
)
from .tiles import render_compartment_sites_pmtiles
from .transparency import (
    SOURCE_RIGHTS_COLUMNS,
    _lane_map,
    _registry_lane_decision,
    emit_transparency_artifacts,
    load_source_registry,
)
from .transparency import TRANSPARENCY_QUERIES as _TRANSPARENCY_QUERIES
from .transparency import (
    _rows as _tuples_to_dicts,
)

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
#: The predicates ``policy.labels`` reads as label candidates (K2 §3.2). The
#: ``label_facts`` query selects the first publishable value per
#: (subject, predicate) for exactly this set — no other claim text leaves the
#: spine for labelling.
_LABEL_FACT_PREDICATES: tuple[str, ...] = (
    "agency_name",
    "asset_operator",
    "asset_type",
    "award_date",
    "bill_external_id",
    "bill_identifier",
    "bill_jurisdiction",
    "bill_session",
    "bill_status",
    "bill_status_date",
    "bill_title",
    "buyer",
    "camera_name",
    "camera_operator",
    "camera_roadway",
    "citation",
    "content_term",
    "contract_signed_date",
    "country",
    "description",
    "effective_from",
    "enacting_body",
    "event_date",
    "event_epistemic_status",
    "event_organizations",
    "event_type",
    "external_id",
    "filed_date",
    "funder",
    "funding_program_name",
    "instrument_type",
    "jurisdiction",
    "legal_name",
    "manufacturer",
    "matched_keyword",
    "meeting_date",
    "name",
    "notice_type",
    "operator_stated",
    "ordinance_citation",
    "organization_identifier",
    "organization_legal_name",
    "place_of_performance",
    "platform",
    "platform_name",
    "posted_date",
    "procurement_state",
    "program_name",
    "recipient",
    "recipient_name",
    "records_response_status",
    "request_date",
    "response_date",
    "response_status",
    "seller",
    "serial_number",
    "service_name",
    "session",
    "signed_date",
    "source_name",
    "status",
    "target_agency",
    "technology",
    "title",
    "vendor",
)

EXPORT_QUERIES: dict[str, tuple[str, str]] = {
    # (guard-table, SELECT). source_registry names — node labels + PROV agents.
    "source_names": (
        "source_registry",
        "SELECT source_id, name FROM source_registry ORDER BY source_id",
    ),
    # entity_identifier labels — sharing-edge partner display names.
    # P32.5/ADR-124 (D-P31.5-2): a withheld/review-pending entity contributes NO
    # label — {PUB_ENTITY_GATE} is the shared selector (``true`` pre-P32.5).
    "entity_labels": (
        "entity_identifier",
        "SELECT ei.entity_id::text, ei.scheme, ei.value FROM entity_identifier ei"
        " WHERE {PUB_ENTITY_GATE} ORDER BY ei.entity_id, ei.scheme",
    ),
    # research_task rows (§39.7) — the research queue surface. The trailing
    # trigger_kind/trigger_ref (P29.2) cite what made each task's detector fire (the
    # materialized contradiction/coverage/relationship); a pre-P29.2 spine lacks the
    # columns, so the query raises and fetch_export_raw degrades it to [] honestly.
    "research_tasks": (
        "research_task",
        "SELECT rt.task_id::text, rt.task_type, rt.subject_id::text, rt.jurisdiction_id::text,"
        "       rt.priority, rt.status, rt.disposition, rt.closing_condition,"
        "       rt.detector_version, rt.trigger_kind, rt.trigger_ref"
        "  FROM research_task rt"
        # P32.5/ADR-124: a task about a withheld subject does not surface on the
        # public research queue — the subject still exists on the spine for
        # authorized review (the task's own disposition field is unchanged).
        " WHERE {PUB_TASK_GATE} ORDER BY rt.priority DESC, rt.task_id",
    ),
    # publishable evidence_artifact metadata (§39.6) — the evidence surface. Bytes
    # never travel; sealed captures stay metadata-only (§17.5).
    # P34.20 (K8 NEW-6 / SIG-EVUI-D08): the /evidence/ interim artifact list
    # groups the published artifacts by source, so the row carries the registry
    # name plus the capture class the honest label turns on — a `synthetic`
    # capture renders as "run record — SIG did not store this document"
    # (SIG-EVUI-D04), never as a capture. `upstream_url` is the source's own
    # link ONLY where the artifact's effective rights (P27.2/ADR-095 latest
    # decision) are redistributable — the S-6 scrub, emitted as data the page
    # labels as a recorded claim, never as a stored capture. P32.5/ADR-124:
    # the shared {PUB_ARTIFACT_GATE} — a withheld artifact never lists.
    "evidence_artifacts": (
        "evidence_artifact",
        "{EFFECTIVE}" + "SELECT ea.artifact_id::text, ea.source_id, ea.title, ea.artifact_type,"
        "       ea.stable_locator, ea.primary_or_secondary, ea.capture_status,"
        "       ea.published_at_edtf, sr.name AS source_name,"
        "       (SELECT ec.capture_classification FROM evidence_capture ec"
        "          WHERE ec.artifact_id = ea.artifact_id"
        "          ORDER BY ec.retrieved_at DESC, ec.capture_id"
        "          LIMIT 1) AS capture_classification,"
        "       CASE WHEN rr.redistributable = 'yes'"
        "            THEN COALESCE(ea.url, CASE WHEN ea.stable_locator ~ '^https?://'"
        "                                 THEN ea.stable_locator END)"
        "            ELSE NULL END AS upstream_url"
        "  FROM evidence_artifact ea"
        "  LEFT JOIN source_registry sr ON sr.source_id = ea.source_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = ea.source_id AND ld.prior_rights_id = ea.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, ea.rights_id)"
        " WHERE ea.sensitivity_tier = 0 AND ea.capture_status = 'captured'"
        "   AND {PUB_ARTIFACT_GATE}"
        " ORDER BY ea.artifact_id",
    ),
    # correction claims (§39.8) — new rows with revises_claim / retraction_of; the
    # prior value stays citable at its belief-time (history never rewritten).
    # P32.16a (SIG-FIND-008): the entry now names BOTH assertions — oc is the
    # superseded/retracted claim the entry revises — and previous_value /
    # previous_belief_date populate only when the prior row itself is publicly
    # eligible (tier 0 + current policy). A gated prior yields
    # previous_withheld=true — the safe tombstone, never a leak.
    "corrections": (
        "claim",
        "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id, c.raw_value,"
        "       c.correction_reason, c.revises_claim::text, c.retraction_of::text,"
        "       lower(c.sys_period), oc.claim_id::text, oc.raw_value,"
        "       lower(oc.sys_period),"
        "       (oc.claim_id IS NOT NULL AND oc.sensitivity_tier = 0"
        "        AND {OLD_CLAIM_GATE}) AS old_eligible"
        "  FROM claim c"
        "  LEFT JOIN claim oc ON oc.claim_id = COALESCE(c.revises_claim, c.retraction_of)"
        " WHERE (c.revises_claim IS NOT NULL OR c.retraction_of IS NOT NULL)"
        "   AND c.sensitivity_tier = 0 AND upper_inf(c.sys_period)"
        # P32.5/ADR-124: a currently-withheld claim does not surface as a public
        # correction entry (its history stays on the spine; access is gated).
        "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.claim_id",
    ),
    # publishable tier-0 claims with the §10.4-§10.6 epistemic axes — the input
    # the web/analytics/provenance.json evidence-tier (W4..W0, §10.6) producer
    # weights (P31.14 / ADR-R9-ANALYTICS). Effective rights apply, so a licence-
    # refused claim never pads the "How we know this" distribution.
    "claim_weights": (
        "claim",
        "{EFFECTIVE}"
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
        # P32.5/ADR-124: a currently-withheld claim never pads the evidence-tier
        # distribution — the same selector as every other surface.
        "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.claim_id",
    ),
    # P32.13 (SIG-FIND-002): claim → capture → artifact bindings for every
    # publishable claim that backs a released site row — the evidence-anchor
    # backbone of the released record routes. The artifact side carries the
    # shared ARTIFACT eligibility gate (the SQL twin of ``access_decision``):
    # a withheld artifact loses its public bindings exactly as it loses its
    # route. Claims themselves reach this join already gated (the shaping
    # ``{PUB_CLAIM_GATE}`` selected the claim set the sites were built from).
    # P34.49/ADR-185: a capture under a current `seal` record loses its public
    # binding exactly as a withheld artifact does — the {CAPTURE_SEAL_GATE}
    # twin of the deny-set consult, never a second rule.
    "evidence_bindings": (
        "claim_evidence",
        "SELECT ce.claim_id::text, ce.capture_id::text, ec.artifact_id::text, ce.role"
        "  FROM claim_evidence ce"
        "  JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "  JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        " WHERE ea.sensitivity_tier = 0"
        "   AND {PUB_ARTIFACT_GATE}"
        "   AND {CAPTURE_SEAL_GATE}"
        " ORDER BY ce.claim_id, ce.capture_id",
    ),
    # P35.36 (R11-K13-TX-08a / J3 §5.1–5.2, SIG-TRANSP-011): the binding DETAIL
    # the ``sig.statement/1`` statements rows and the provenance panel read —
    # the same claim→capture→artifact eligibility join as ``evidence_bindings``
    # (the shared artifact gate + the capture-seal gate) widened with the P32.2
    # binding columns (``binding_status`` — the four-state source), the
    # capture's scrubbed locators, the artifact's upstream URL (scrubbed
    # downstream through S-6 — never emitted raw) and the extraction identity.
    # Guarded on ``claim_evidence`` like its sibling: a pre-P32.2 spine degrades
    # to [] and statements carry ``not_recorded`` binding state — honest
    # absence, never a guessed ``legacy_synthetic``.
    "claim_binding_detail": (
        "claim_evidence",
        "SELECT ce.claim_id::text, ce.capture_id::text, ec.artifact_id::text, ce.role,"
        "       ce.binding_status, ce.bound_at::text, ce.extractor_version,"
        "       ec.retrieved_at::text, ec.content_digest, ec.byte_size, ec.media_type,"
        "       ec.storage_tier, ec.capture_classification, ec.retrieved_by_run_id::text,"
        "       ea.url, ea.source_id, ea.acquisition_method,"
        "       ex.method, ex.extractor_name, ex.extractor_version, ex.review_status"
        "  FROM claim_evidence ce"
        "  JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "  JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "  LEFT JOIN extraction ex ON ex.extraction_id = ce.extraction_id"
        " WHERE ea.sensitivity_tier = 0"
        "   AND {PUB_ARTIFACT_GATE}"
        "   AND {CAPTURE_SEAL_GATE}"
        " ORDER BY ce.claim_id, ce.capture_id",
    ),
    # P35.36 (R11-K13-TX-08a): the claim-level provenance fields the statements
    # row + panel need beyond the shaping row — review/epistemic status, the
    # recording run + belief instant, and the supersession pair. Same claim
    # gate + tier filter as every other claim read; a pre-bitemporal spine
    # degrades to [] and the fields emit ``not_recorded``.
    "claim_provenance": (
        "claim",
        "SELECT c.claim_id::text, c.review_status::text, c.claim_directness,"
        "       c.source_reliability, c.artifact_integrity,"
        "       c.ingest_run_id::text, lower(c.sys_period)::text,"
        "       c.revises_claim::text, c.retraction_of::text"
        "  FROM claim c"
        " WHERE c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.claim_id",
    ),
    # P35.19 / JUR-02b (K4 §3.3 note): landed ``geometry_defect`` claims
    # (P35.16 / PKG-06b) are placement inputs — ``raw_value`` is the defect
    # class itself. Absent predicate/table degrades to [] and the engine
    # applies its own R1/R3 checks ("consumes PKG-06b detectors if landed —
    # else flags only"). Read-only: this is a SELECT inside the export's
    # snapshot; nothing is written back (ADR-092).
    "geometry_defects": (
        "claim",
        "SELECT c.subject_id::text, c.raw_value"
        "  FROM claim c"
        " WHERE c.predicate_id = 'geometry_defect'"
        "   AND c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.subject_id, c.raw_value",
    ),
    # P35.30 (SIG-EXPORT-D21 draft / K2 §7 H-2): the declared independence
    # class per claim (P35.25 / SIG-CONF-014) — the input the network edge's
    # support level derives from (two+ declared-independent classes is a
    # genuinely corroborated edge; everything else stays the single-source
    # floor, never a constant). Guarded on ``claim_lineage`` — a pre-P35.25
    # spine degrades to [] and every edge keeps the honest floor.
    "claim_lineage": (
        "claim_lineage",
        "SELECT claim_id::text, independence_class FROM claim_lineage ORDER BY claim_id",
    ),
    # P35.29 (K2 §3 / A-10, R11-K13-GX-01): the shared ``sig.entity-label/1``
    # registry inputs. Three seams, each degrading independently:
    #   * ``label_entities`` — every entity + type + subject key + org columns
    #     (never gated: the registry itself renders the eligible/typed-review
    #     state per row; a spine with entities emits rows for all of them).
    #   * ``label_entity_dispositions`` — the CURRENT effective entity
    #     disposition per target (``publication_disposition`` is post-P32.5 —
    #     absent → honest "no dispositions", never a missing entity list).
    #   * ``label_facts`` — the publishable label-input claims (first value per
    #     subject+predicate under the same {PUB_CLAIM_GATE}/effective-rights
    #     semantics as claim_weights) + the rights slot each rides, so the
    #     emitted row files under the compartment its input claims license to.
    "label_entities": (
        "entity",
        "SELECT e.entity_id::text, e.entity_type,"
        "       (SELECT ei.value FROM entity_identifier ei"
        "         WHERE ei.entity_id = e.entity_id"
        "           AND ei.scheme = 'sig.connector.subject'"
        "         ORDER BY ei.value LIMIT 1) AS subject_key,"
        "       e.merged_into::text,"
        "       o.cached_canonical_name, o.publication_review_required, o.status"
        "  FROM entity e LEFT JOIN organization o ON o.entity_id = e.entity_id"
        " ORDER BY e.entity_id",
    ),
    "label_entity_dispositions": (
        "publication_disposition",
        "SELECT DISTINCT ON (d.target_id) d.target_id, d.disposition::text"
        "  FROM publication_disposition d"
        " WHERE d.target_kind = 'entity' AND d.decided_at <= clock_timestamp()"
        " ORDER BY d.target_id, d.decided_at DESC, d.disposition_seq DESC",
    ),
    "label_facts": (
        "claim",
        "{EFFECTIVE}SELECT DISTINCT ON (c.subject_id, c.predicate_id)"
        "       c.subject_id::text, c.predicate_id,"
        "       COALESCE(c.value_text, c.raw_value::text),"
        "       cs.source_id, rr.spdx_expression, rr.attribution_text,"
        "       rr.redistributable, rr.derivative_permitted, rr.terms_url,"
        "       rr.rights_id"
        "  FROM claim c"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE c.predicate_id IN (" + ",".join(f"'{p}'" for p in _LABEL_FACT_PREDICATES) + ")"
        "   AND c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.subject_id, c.predicate_id, c.observed_at DESC, c.claim_id",
    ),
    # P35.33 (J3 §3.1–3.3 + K9 C-4…C-7 + K10 C-13): the transparency
    # run/capture views, the per-source rights fields the interim lane
    # reads, and the predicate-registry volatility basis — every row
    # explicit-column, sig_export-facing, scrubbed again at emission.
    **_TRANSPARENCY_QUERIES,
}


def fetch_export_raw(cur: Any, *, belief: datetime | None = None) -> dict[str, Any]:
    """Fetch every supplementary export query inside the caller's transaction.

    Read-only and snapshot-consistent: the caller runs this inside the SAME
    ``REPEATABLE READ READ ONLY`` snapshot as shaping, so every emitted artifact
    describes one spine state. Each query is guarded by ``to_regclass`` — a spine
    missing a table yields an empty result (honest absence), never an error.

    ``belief`` pins the belief-partitioned reads (P32.4 / ADR-123): ``claim``
    rows are filtered by ``sys_period @> belief`` *and* the shared
    ``claim_source`` CTE's evidence bindings by ``bound_at <= belief`` — the
    same frozen view every other consumer sees; non-partitioned reference
    tables are unchanged. The belief expressions are module constants, never
    caller SQL.
    """
    belief_filter = (
        "upper_inf(c.sys_period)" if belief is None else "c.sys_period @> %s::timestamptz"
    )
    occ_bound = BELIEF_PARAM if belief is not None else BELIEF_NOW
    effective = _LATEST_DECISION_CTE + claim_source_cte(occ_bound)
    # P32.5/ADR-124: the shared eligibility gates — real fragments when the
    # registry exists, ``true`` on a pre-P32.5 spine (no dispositions can be
    # recorded there). The entity gate also needs ``organization``.
    has_registry = _table_present(cur, "publication_disposition")
    has_orgs = _table_present(cur, "organization")
    entity_gate = entity_eligible_sql("ei.entity_id") if (has_registry and has_orgs) else "true"
    claim_gate = claim_eligible_sql("c") if has_registry else "true"
    # The same selector against the superseded side of a correction (`oc` —
    # never aliased `o`, which collides with the `organization o` subquery the
    # entity gate expands inline).
    old_claim_gate = claim_eligible_sql("oc") if has_registry else "true"
    task_gate = entity_eligible_sql("rt.subject_id") if (has_registry and has_orgs) else "true"
    # P32.13: the artifact twin of the same rule — one selector, never a
    # second eligibility definition.
    artifact_gate = artifact_eligible_sql("ea.artifact_id") if has_registry else "true"
    # P34.49/ADR-185: the capture-seal twin — ``capture_currently_sealed`` is
    # the SQL helper the seal_register change installs; a pre-seal spine
    # answers ``true`` (honest absence).
    seal_gate = (
        "NOT capture_currently_sealed(ce.capture_id)"
        if _table_present(cur, "capture_seal")
        else "true"
    )
    raw: dict[str, Any] = {}
    for key, (guard, sql) in EXPORT_QUERIES.items():
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (guard,))
        row = cur.fetchone()
        if not (row and row[0]):
            raw[key] = []
            continue
        try:
            final = (
                sql.replace("{EFFECTIVE}", effective)
                .replace("{PUB_ENTITY_GATE}", entity_gate)
                .replace("{PUB_CLAIM_GATE}", claim_gate)
                .replace("{OLD_CLAIM_GATE}", old_claim_gate)
                .replace("{PUB_TASK_GATE}", task_gate)
                .replace("{PUB_ARTIFACT_GATE}", artifact_gate)
                .replace("{CAPTURE_SEAL_GATE}", seal_gate)
                .replace("upper_inf(c.sys_period)", belief_filter)
            )
            cur.execute(final, tuple([belief] * final.count("%s")) or None)
            raw[key] = cur.fetchall()
        except Exception:  # noqa: BLE001 - a schema-shape mismatch is honest absence
            raw[key] = []
    # P34.49/ADR-185: fail-closed post-check on the emitted bindings — no
    # binding may name a capture under a CURRENT seal (the {CAPTURE_SEAL_GATE}
    # query fragment is the consult; this defensive filter is the assert, and
    # the dropped count is a counts-only record, never material).
    if _table_present(cur, "capture_seal"):
        cur.execute(
            "SELECT DISTINCT s.capture_id::text FROM capture_seal s"
            "  WHERE s.action = 'seal' AND NOT EXISTS ("
            "    SELECT 1 FROM capture_seal u"
            "     WHERE u.capture_id = s.capture_id AND u.action = 'unseal'"
            "       AND (u.recorded_at, u.seal_seq) > (s.recorded_at, s.seal_seq))"
        )
        sealed_ids = {str(r[0]) for r in cur.fetchall()}
        bindings = raw.get("evidence_bindings") or []
        kept = [r for r in bindings if str(r[1]) not in sealed_ids]
        # ``dropped`` is the post-check's own catch (0 while the query gate
        # holds — nonzero means the consult failed and the assert fired);
        # ``suppressed`` is the counts-only record of how many claim→capture
        # bindings the seal removes from the publishable tier. Both are
        # row-shaped like every other ``raw`` value (single-column counts).
        raw["sealed_bindings_dropped"] = [(len(bindings) - len(kept),)]
        raw["evidence_bindings"] = kept
        # P35.36: the statements detail read carries the same capture key in
        # position 1 — a sealed capture loses its binding row here too (the
        # same fail-closed assert, same rule).
        detail = raw.get("claim_binding_detail") or []
        raw["claim_binding_detail"] = [r for r in detail if str(r[1]) not in sealed_ids]
        raw["sealed_bindings_suppressed"] = [(0,)]
        if _table_present(cur, "claim_evidence"):
            try:
                cur.execute(
                    "SELECT count(*) FROM claim_evidence WHERE capture_currently_sealed(capture_id)"
                )
                row = cur.fetchone()
                raw["sealed_bindings_suppressed"] = [(int(row[0]) if row else 0,)]
            except Exception:  # noqa: BLE001 - honest absence
                raw["sealed_bindings_suppressed"] = [(0,)]
    else:
        raw["sealed_bindings_dropped"] = [(0,)]
        raw["sealed_bindings_suppressed"] = [(0,)]
    # P34.18 / ADR-178 (S0 RI-01): the keyed-digest alias projection — every
    # retired identifier token in a supplementary row (source ids, evidence
    # titles/locators, subject refs, attribution strings) resolves or redacts
    # to its neutral public form here, once, before any surface builder sees
    # it. Nothing publicly renderable may repeat a handle (TS-04).
    return {k: resolve_public_text(v) for k, v in raw.items()}


def _table_present(cur: Any, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
    row = cur.fetchone()
    return bool(row and row[0])


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


#: Raw keys the web-surface builders read for which NO spine query produces a
#: result — declared, never silently absent. P34.20 (K7 NEW-1 /
#: SIG-EVUI-D08): the static producer check
#: (``tests/unit/test_p34_20_producer_check.py``) fails any ``raw`` read whose
#: key is neither produced (``EXPORT_QUERIES`` ∪ ``shaping.QUERIES`` ∪
#: ``_MATERIALIZED_SEAMS``) nor declared here with its cause class, so a
#: surface can never silently render from a key a query was expected to fill —
#: the empty state then names a REAL cause ("no producer"), never a vague
#: "research gap".
DECLARED_UNPRODUCED_READ_KEYS: dict[str, str] = {
    # §39.5 contract watch — the spine has no materialized contract-watch
    # producer yet (renewal/decision tracking lands in a later family). The
    # watch surface reads it and honestly degrades to the "not connected yet"
    # empty state.
    "contract_watch": "no_producer",
    # §7 leverage (P34.34a): the changeset feed is not a spine query — the
    # recorded OSM replay XML is bound to the export by the operator/CLI
    # (HG-08: never a live poll). Unbound → the zeroed ledger, the honest
    # "measured nothing yet", not a missing artifact.
    "osm_changeset_feeds": "operator_bound_replay",
}


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
    # P32.5/ADR-124 (SIG-TRUST-006): a withheld entity or claim must not leak
    # through materialized TOPOLOGY either — edges, accountability links,
    # contradictions and resolutions citing a currently-withheld target are
    # dropped whole under the same selector (current dispositions, not the
    # materialization-time set). The rows stay materialized on the spine; the
    # public export never names them.
    return _eligibility_filter_materialized(cur, out)


def _eligibility_filter_materialized(
    cur: Any, out: dict[str, list[dict[str, Any]]]
) -> dict[str, list[dict[str, Any]]]:
    """Drop materialized rows that would expose a currently-withheld entity or
    claim — batch-evaluated through the shared selector (current access policy)."""
    if not _table_present(cur, "publication_disposition"):
        return out
    entity_ids: set[str] = set()
    claim_ids: set[str] = set()
    for e in out.get("materialized_edges", []):
        entity_ids.update((str(e["from_entity"]), str(e["to_entity"])))
        if e.get("evidence_claim"):
            claim_ids.add(str(e["evidence_claim"]))
    for link in out.get("materialized_accountability_links", []):
        for k in ("deployment_id", "object_id", "via_org", "via_contract"):
            if link.get(k):
                entity_ids.add(str(link[k]))
        claim_ids.update(map(str, link.get("establishing_claims") or ()))
        claim_ids.update(map(str, link.get("input_claim_ids") or ()))
    for c in out.get("materialized_contradictions", []):
        entity_ids.add(str(c["subject_id"]))
        claim_ids.update(map(str, c.get("claim_ids") or ()))
    for r in out.get("materialized_resolutions", []):
        entity_ids.add(str(r["subject_id"]))
        if r.get("winning_claim"):
            claim_ids.add(str(r["winning_claim"]))
    for cov in out.get("materialized_coverage", []):
        if cov.get("subject_id"):
            entity_ids.add(str(cov["subject_id"]))
    ok_entities = eligible_entity_ids(cur, sorted(entity_ids))
    ok_claims = eligible_claim_ids(cur, sorted(claim_ids))

    def _ent_ok(v: Any) -> bool:
        # Only entity-shaped (uuid) references are entity-gated — a coverage
        # metric's jurisdiction/candidate subject string is not an entity leak.
        s = str(v).strip().lower()
        if len(s) == 36 and s.count("-") == 4:
            return s in ok_entities
        return True

    def _all_ok(ids: Any) -> bool:
        return all(str(i) in ok_claims for i in (ids or ()))

    out["materialized_edges"] = [
        e
        for e in out.get("materialized_edges", [])
        if _ent_ok(e["from_entity"])
        and _ent_ok(e["to_entity"])
        and _all_ok([e.get("evidence_claim")])
    ]
    out["materialized_accountability_links"] = [
        link
        for link in out.get("materialized_accountability_links", [])
        if all(
            _ent_ok(link[k])
            for k in ("deployment_id", "object_id", "via_org", "via_contract")
            if link.get(k)
        )
        and _all_ok(link.get("establishing_claims"))
        and _all_ok(link.get("input_claim_ids"))
    ]
    out["materialized_contradictions"] = [
        c
        for c in out.get("materialized_contradictions", [])
        if _ent_ok(c["subject_id"]) and _all_ok(c.get("claim_ids"))
    ]
    out["materialized_resolutions"] = [
        r
        for r in out.get("materialized_resolutions", [])
        if _ent_ok(r["subject_id"]) and _all_ok([r.get("winning_claim")])
    ]
    out["materialized_coverage"] = [
        cov
        for cov in out.get("materialized_coverage", [])
        if not cov.get("subject_id") or _ent_ok(cov["subject_id"])
    ]
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


def _site_row_data(
    site: ShapedSite,
    rights: Mapping[str, Any],
    *,
    placement: _placement.PlacementResult | None = None,
    labels: Mapping[str, EntityLabel] | None = None,
) -> dict[str, Any]:
    """The per-(site, source, rights) export row — geometry + provenance keys.

    P35.19 / JUR-02b (K4 §5.3): when a ``placement@1`` run is bound, the row
    gains the seven additive placement columns and — when the run withheld
    the point (suspect swap/flip, rejected null-island/invalid, or a guarded
    agency-centroid precision) — emits ``geometry: null`` so no downstream
    surface ever re-draws a point the ruleset refused to stand behind (the
    raw observed pair stays on the claim rows — nothing is erased). The
    legacy ``jurisdiction`` column is unchanged (the declared bucket,
    back-compat). With no placement run the row is byte-identical to today.
    """
    geometry: dict[str, Any] | None = None
    if (
        site.latitude is not None
        and site.longitude is not None
        and not (placement is not None and placement.point_withheld)
    ):
        geometry = {"type": "Point", "coordinates": [site.longitude, site.latitude]}
    # P35.29 (K2 §3/L-1): the public label is the shared registry's derivation
    # — never the per-slice envelope and never the entity id (L-2).
    lbl = (labels or {}).get(site.entity_id)
    row = {
        "entity_id": site.entity_id,
        "entity_type": site.entity_type,
        "label": (lbl.label if lbl is not None and lbl.label else site.label),
        "label_basis": (lbl.label_basis if lbl is not None and lbl.label_basis else None),
        # P35.15a / PKG-07: the declared SKOS technology slug (null when
        # unreported/conflicted — the status keeps the honest reason).
        "technology": site.technology,
        "technology_status": site.technology_status,
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
    if placement is not None:
        row.update(placement.sites_columns())
    return row


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
    #: P35.19: the ``placement@1`` results behind the emitted rows — the
    #: quality report's input. Empty when no engine was bound.
    placement_results: tuple[_placement.PlacementResult, ...] = ()


def _slice_sites(
    claims: Sequence[ShapingClaim],
    entity_types: Mapping[str, str],
    *,
    subject_flags: Mapping[str, bool] | None = None,
    retrieval: date,
    registry: Mapping[str, Any] | None,
    placement: _placement.PlacementEngine | None = None,
    defect_flags: Mapping[str, frozenset[str]] | None = None,
    labels: Mapping[str, EntityLabel] | None = None,
) -> _SiteSlices:
    """Licence-slice every site per (source, rights_id) into per-compartment rows.

    Each source's sites are recomputed from *that source's own* observations
    (``shape_sites`` over the per-source claim subset — never a silent cross-source
    merge, so a per-slice envelope reflects only what that source observed). A
    refused (source, rights) slice is dropped into the exclusions list, loudly; a
    surviving slice lands in the compartment its own computed licence declares.

    P35.66 (SIG-PUB-011/013): ``subject_flags`` carries the emit-stamped
    ``residential_parcel_flag`` per subject (from the ``subject_entities``
    read). A ``candidate_asset`` subject — or any flagged subject — never
    shapes a site at all (``shape_sites`` refuses it) and is folded into the
    returned ``refused_subjects`` so EVERY downstream surface (map, analytics,
    licence mix) excludes it identically; the refusal is counted on the
    dataset's ``candidate_subjects_excluded`` total.
    """
    publish_refused = {sid for sid, etype in entity_types.items() if etype == "candidate_asset"} | {
        sid for sid, flag in (subject_flags or {}).items() if flag
    }
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

    # P35.19 / JUR-02b: shape every source's sites first, then run
    # ``placement@1`` over ALL of them in one batch (a single DuckDB join —
    # never a per-record round trip) and keep the results keyed by
    # (source, subject) so each slice row stamps its own placement. With no
    # engine bound, nothing here changes.
    sites_by_source: dict[str, list[ShapedSite]] = {}
    for source_id in sorted(by_source):
        sites_by_source[source_id] = shape_sites(
            by_source[source_id],
            entity_types=entity_types,
            refused_subjects=publish_refused,
        )
    placements: dict[tuple[str, str], _placement.PlacementResult] = {}
    placement_results: list[_placement.PlacementResult] = []
    if placement is not None:
        inputs: list[_placement.PlacementInput] = []
        for source_id in sorted(sites_by_source):
            claims_by_id = {c.claim_id: c for c in by_source[source_id]}
            for site in sites_by_source[source_id]:
                inputs.append(
                    _placement.site_input(
                        site,
                        claims_by_id=claims_by_id,
                        defect_flags=(defect_flags or {}).get(site.entity_id, frozenset()),
                        source_id=source_id,
                    )
                )
        placement_results = placement.place_many(inputs)
        placements = {(r.source_id or "", r.record_id): r for r in placement_results}

    for source_id in sorted(by_source):
        for site in sites_by_source[source_id]:
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
                    C.ExportRow(
                        source_id=slice_key,
                        data=_site_row_data(
                            site,
                            rights,
                            placement=placements.get((source_id, site.entity_id)),
                            labels=labels,
                        ),
                    )
                )
                index.setdefault(slice_key, replace(record, source_id=slice_key))
    exclusions = [refused[k] for k in sorted(refused)]
    return _SiteSlices(
        rows_by_compartment=rows_by_compartment,
        index=index,
        exclusions=exclusions,
        licences_by_subject=licences_by_subject,
        # P35.66: publish-refused subjects (candidate / parcel-flagged) join
        # the licence-refused set — every render surface excludes them the
        # same way. The exclusion count lives on
        # ``ShapedDataset.candidate_subjects_excluded``.
        refused_subjects=refused_subjects | publish_refused,
        placement_results=tuple(placement_results),
    )


def _claim_access_kind(predicate_id: str | None, materialized_kind: str | None) -> str | None:
    """P34.34a (SIG-UI-024): the §12.2 access-edge type a published claim
    carries, or ``None`` when the claim is not an access-typed claim at all.

    A materialized ``sharing`` edge's recorded ``access_kind`` wins when the
    §29.3 reconciler cited this claim as its ``evidence_claim`` — the
    recorded classification is never re-derived. Otherwise the predicate
    vocabulary gates emission (sharing/access/…``_edge`` predicates only) so
    an ordinary observation claim is never labelled an edge; an
    unclassifiable access predicate reports ``unclassified`` honestly —
    never coerced, never silently dropped (SIG-ONTO-042).
    """
    if materialized_kind:
        return str(materialized_kind)
    if not predicate_id:
        return None
    p = predicate_id.lower()
    if "sharing" in p or "access" in p or p.endswith("_edge"):
        return classify_access_kind(p) or "unclassified"
    return None


def _record_claims(
    claims: Sequence[ShapingClaim],
    slices: _SiteSlices,
    bindings: Sequence[Any],
    *,
    retrieval: date,
    registry: Mapping[str, Any] | None,
    materialized_edges: Sequence[Mapping[str, Any]] = (),
) -> dict[str, dict[str, Any]]:
    """P32.13 (SIG-FIND-002): the claim anchors + evidence bindings behind
    every published site row, sliced into per-compartment ``record_claims``
    payloads — each claim filed under **its own** licence compartment (the
    same ``compute_export_license`` + ``compartment_for_license`` gate the
    sites tables pass through; never co-mingled, never silently dropped).

    Rows carry public-safe fields only: the claim anchor (id, predicate,
    observed date, source) and typed capture/artifact locators — never raw
    claim literals. A claim whose licence computes to a refused compartment
    contributes no anchor row (its site slice already dropped the row).

    P34.34a: access-typed claims additionally carry ``access_kind``
    (configured_access / observed_use / declared_policy / unclassified) —
    the materialized edge's recorded kind when the claim backs one, else
    the predicate-vocabulary classification.
    """
    slots = _claim_slots(claims, slices, retrieval=retrieval, registry=registry)
    bindings_by_claim: dict[str, list[dict[str, Any]]] = {}
    for r in bindings or []:
        cid, cap, art, role = str(r[0]), str(r[1]), str(r[2]), str(r[3])
        bindings_by_claim.setdefault(cid, []).append(
            {"capture_id": cap, "artifact_id": art, "role": role}
        )
    # claim_id → the reconciler's recorded §12.2 kind (one row per edge's
    # evidence_claim — the first recorded kind wins; an edge never renames
    # its claim's kind).
    kind_by_claim: dict[str, str] = {}
    for e in materialized_edges or []:
        edge_cid = e.get("evidence_claim")
        edge_kind = e.get("access_kind")
        if edge_cid is not None and edge_kind is not None:
            kind_by_claim.setdefault(str(edge_cid), str(edge_kind))
    rows_by_comp: dict[str, list[dict[str, Any]]] = {}
    lic_by_comp: dict[str, str] = {}
    for c in sorted(claims, key=lambda c: c.claim_id):
        slot = slots.get(c.claim_id)
        if slot is None:
            continue
        licence, comp = slot
        lic_by_comp[comp] = str(licence)
        crow: dict[str, Any] = {
            "claim_id": c.claim_id,
            "entity_id": c.subject_id,
            "predicate_id": c.predicate_id,
            "observed_at": c.observed_at.isoformat() if c.observed_at else None,
            "source_id": c.source_id,
            "evidence": bindings_by_claim.get(c.claim_id, []),
        }
        # Sparse field: access-typed claims name their §12.2 kind; an ordinary
        # claim emits no key at all (byte-identical for non-edge rows).
        claim_kind = _claim_access_kind(c.predicate_id, kind_by_claim.get(c.claim_id))
        if claim_kind is not None:
            crow["access_kind"] = claim_kind
        rows_by_comp.setdefault(comp, []).append(crow)
    return {
        comp: {"rows": rows, "license": lic_by_comp[comp]} for comp, rows in rows_by_comp.items()
    }


def _claim_slots(
    claims: Sequence[ShapingClaim],
    slices: _SiteSlices,
    *,
    retrieval: date,
    registry: Mapping[str, Any] | None,
) -> dict[str, tuple[str, str]]:
    """claim_id → (licence, compartment) for every claim backing a published
    site row — the shared ``compute_export_license`` +
    ``compartment_for_license`` placement ``record_claims`` and ``statements``
    both file under (a claim lands under its OWN licence compartment; a claim
    whose rights refuse contributes no row at all — never co-mingled, never
    silently dropped, SIG-LIC-004a)."""
    wanted: set[str] = set()
    for rows in slices.rows_by_compartment.values():
        for row in rows:
            wanted.update(str(cid) for cid in (row.data.get("claim_ids") or []))
    placement: dict[str, tuple[str | None, str | None]] = {}
    slots: dict[str, tuple[str, str]] = {}
    for c in sorted(claims, key=lambda c: c.claim_id):
        if c.claim_id not in wanted or not c.source_id:
            continue
        slot = placement.get(c.effective_rights_id)
        if slot is None:
            record = RightsRecord(
                source_id=c.source_id,
                spdx=c.effective_spdx,
                attribution=c.effective_attribution,
                redistributable=str(c.effective_redistributable) == "yes",
                derivative_permitted=str(c.effective_derivative_permitted) == "yes",
                terms_url=c.effective_terms_url,
                retrieval_date=retrieval,
            )
            if export_refusal_reason(record, registry) is not None:
                placement[c.effective_rights_id] = (None, None)
                continue
            licence2 = str(compute_export_license([record], registry))
            comp2 = C.compartment_for_license(licence2, None, registry)
            slot = (licence2, comp2)
            placement[c.effective_rights_id] = slot
        licence, comp = slot
        if comp is None:
            continue
        slots[c.claim_id] = (str(licence), str(comp))
    return slots


def _claim_lane_map(
    raw: Mapping[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """source_id → {decision: LaneDecision, p8} for the statements upstream
    gate (P35.36 / J4 S-6).

    The recorded ``[redistribution]`` verdict wins — via the
    ``v_transparency_source`` mirror row first (the DB record), then the
    committed registry of record (``sources.toml``); absent both, the interim
    rights-record derivation stands with its basis labelled — the same
    precedence ``_lane_map`` + ``_registry_lane_decision`` encode on the
    transparency surfaces. A source with no recorded posture at all falls to
    the ``unknown`` lane — the fail-closed floor, never an assumed lane.
    """
    rights_rows = _tuples_to_dicts(
        raw.get("transparency_source_rights") or [], SOURCE_RIGHTS_COLUMNS
    )
    source_view_rows = _tuples_to_dicts(
        raw.get("transparency_sources") or [], TRANSPARENCY_SOURCE_VIEW_COLUMNS
    )
    lane_by_source = _lane_map(rights_rows, source_view_rows)
    for sid, reg in (source_registry or {}).items():
        red = reg.get("redistribution") or {}
        recorded_lane = str(red.get("lane") or "").strip()
        p8 = str(red.get("part_viii_class") or "").strip() or None
        entry = lane_by_source.get(str(sid))
        if entry is None:
            lane_by_source[str(sid)] = {
                "decision": _registry_lane_decision(reg),
                "p8": p8,
            }
            continue
        if p8 and not entry.get("p8"):
            entry["p8"] = p8
        if recorded_lane:
            entry["decision"] = LaneDecision(recorded_lane, basis="registry:[redistribution]")
    return lane_by_source


def _statements(
    claims: Sequence[ShapingClaim],
    slices: _SiteSlices,
    bindings: Sequence[Any],
    detail_rows: Sequence[Any],
    provenance_rows: Sequence[Any],
    *,
    retrieval: date,
    registry: Mapping[str, Any] | None,
    source_registry: Mapping[str, Mapping[str, Any]] | None,
    lane_by_source: Mapping[str, Mapping[str, Any]],
    materialized_edges: Sequence[Mapping[str, Any]] = (),
    materialized_contradictions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, dict[str, Any]]:
    """P35.36 (R11-K13-TX-08a / J3 §5.1–5.2, SIG-TRANSP-011): the
    ``sig.statement/1`` per-compartment statements stream — one row per
    published claim carrying the full provenance block the shared
    ``<ProvenancePanel>`` contract reads (binding state, scrubbed capture
    locators, S-6-gated upstream, extraction, epistemics, supersession,
    contradictions, per-claim rights). Compartment placement is exactly
    ``_record_claims``'s — the same licence gate, the same no-co-mingle rule.

    Raw claim values are never emitted (``value`` is the closed token
    ``not_published``); every upstream reference passes the P35.31 S-6 gate
    (``statements.upstream_block``); a claim with no publishable binding row
    carries ``not_recorded`` — honest absence, never a fabricated binding.
    """
    slots = _claim_slots(claims, slices, retrieval=retrieval, registry=registry)
    detail_by_claim: dict[str, list[dict[str, Any]]] = {}
    for d in _tuples_to_dicts(detail_rows or [], _stmt.BINDING_DETAIL_COLUMNS):
        detail_by_claim.setdefault(str(d["claim_id"]), []).append(d)
    plain_by_claim: dict[str, list[dict[str, Any]]] = {}
    for r in bindings or []:
        plain_by_claim.setdefault(str(r[0]), []).append(
            {"capture_id": str(r[1]), "artifact_id": str(r[2]), "role": str(r[3])}
        )
    prov_by_claim: dict[str, dict[str, Any]] = {}
    prior_recorded_at: dict[str, str | None] = {}
    for p in _tuples_to_dicts(provenance_rows or [], _stmt.CLAIM_PROVENANCE_COLUMNS):
        cid = str(p["claim_id"])
        prov_by_claim[cid] = p
        prior_recorded_at[cid] = str(p["recorded_at"]) if p.get("recorded_at") else None
    kind_by_claim: dict[str, str] = {}
    for e in materialized_edges or []:
        edge_cid = e.get("evidence_claim")
        edge_kind = e.get("access_kind")
        if edge_cid is not None and edge_kind is not None:
            kind_by_claim.setdefault(str(edge_cid), str(edge_kind))
    by_subject: dict[str, list[Mapping[str, Any]]] = {}
    for contra in materialized_contradictions or []:
        for cid in (str(x) for x in (contra.get("claim_ids") or [])):
            by_subject.setdefault(cid, []).append(contra)
    rows_by_comp: dict[str, list[dict[str, Any]]] = {}
    lic_by_comp: dict[str, str] = {}
    for c in sorted(claims, key=lambda c: c.claim_id):
        slot = slots.get(c.claim_id)
        if slot is None:
            continue
        licence, comp = slot
        lic_by_comp[comp] = str(licence)
        lane_entry = lane_by_source.get(str(c.source_id)) or {}
        decision = lane_entry.get("decision")
        lane = str(getattr(decision, "lane", "unknown") or "unknown")
        lane_basis = getattr(decision, "basis", None)
        p8 = lane_entry.get("p8")
        homepage = (
            str(
                ((source_registry or {}).get(str(c.source_id)) or {}).get("homepage_url") or ""
            ).strip()
            or None
        )
        row = _stmt.statement_row(
            claim_id=c.claim_id,
            entity_id=c.subject_id,
            predicate_id=c.predicate_id,
            observed_at=c.observed_at.isoformat() if c.observed_at else None,
            source_id=str(c.source_id),
            licence=licence,
            compartment=comp,
            attribution=c.effective_attribution or None,
            access_kind=_claim_access_kind(c.predicate_id, kind_by_claim.get(c.claim_id)),
            provenance=prov_by_claim.get(c.claim_id),
            details=detail_by_claim.get(c.claim_id, ()),
            plain_bindings=plain_by_claim.get(c.claim_id, ()),
            lane=lane,
            lane_basis=lane_basis,
            part_viii_class=p8,
            gate_passed=True,  # the claim published — the gate's own verdict
            source_homepage=homepage,
            prior_recorded_at=prior_recorded_at,
            contradictions=by_subject.get(c.claim_id, ()),
        )
        rows_by_comp.setdefault(comp, []).append(row)
    return {
        comp: {"rows": rows, "license": lic_by_comp[comp]} for comp, rows in rows_by_comp.items()
    }


def _leverage_metric(raw: Mapping[str, Any]) -> dict[str, Any]:
    """The §7 contribution-back leverage record (P21.7, SIG-CONTRIB-016e).

    Folds any recorded changeset feed bound to the export
    (``raw["osm_changeset_feeds"]`` — XML documents captured for replay, the
    HG-08 posture; nothing is fetched live) into a fresh
    :class:`LeverageLedger`. An unbound export emits the zeroed ledger —
    the honest ``0`` of a metric that has measured nothing yet, never a
    fabricated count (§3.1) and never a missing file (P34.34a).
    """
    ledger = LeverageLedger()
    for xml in raw.get("osm_changeset_feeds") or []:
        ingest_changesets(ledger, parse_changesets(xml))
    return leverage_metric_json(ledger)


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

    P35.20a / ED-42 (F-134): a reconciliation ratio carries its excluded classes as
    data — ``exclusions`` (``{conflicted, withheld, non_publishable, filtered}``)
    plus ``excluded_total``. The numerator ⊆ denominator join and the
    ``numerator + not_evaluable = denominator`` CHECK mean the emitted ``value``
    can never read "N of N" while an exclusion exists — the excluded subjects are
    disclosed, never clamped away.
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
    out: dict[str, Any] = {
        "id": f"materialized_{method}_{ident}",
        "kind": _COMPLETENESS_TO_KIND.get(str(method), "counted_quantity"),
        "label": str(label),
        "value": value,
        "denominator": str(named),
        "population_note": _POPULATION_NOTE,
        "is_population_total": False,
    }
    # The excluded-class disclosure (ED-42): persisted on the measured row,
    # carried through as data — the presentation seam that renders it is
    # DSRC-01's; the derivation emits it here.
    exclusions = row.get("exclusions")
    if isinstance(exclusions, Mapping):
        out["exclusions"] = {str(k): int(v) for k, v in exclusions.items()}
        out["excluded_total"] = sum(int(v) for v in exclusions.values())
    elif row.get("not_evaluable") is not None:
        out["excluded_total"] = int(float(row["not_evaluable"]))
    return out


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
        # P34.11 (K12b NEW-17 / F-22): "contradictions kept visible" claimed a
        # browsability the public surface does not have — the claim is withdrawn;
        # only the recorded count is shown. Mirrors the web fixture.
        "label": "recorded contradictions",
        "value": f"{open_n} open of {k} recorded contradictions",
        "denominator": (
            f"{k} recorded contradictions in the materialized graph "
            "(both evidence sides retained, §31)"
        ),
        "population_note": (
            "Contradictions are never silently reconciled (§3.1); both disagreeing sides are "
            "retained. This counts recorded contradictions, not an estimate of every "
            "disagreement that exists. This page shows only the recorded count; SIG does "
            "not publish a contradiction browser."
        ),
        "is_population_total": False,
    }


# --- P35.30 (R11-K13-GX-02, SIG-EXPORT-D21 draft): honest edge fields ---------
#
# Every emitted edge carries the relation in words, the observed date AND its
# kind (the epoch-zero placeholder renders ``undated``, never a synthetic
# 1970-01-01 — SIG-TIME-012 class honesty; the spine-side repair is L3
# CONF-06's), the source display names, the currency class and the full set of
# supporting claim ids — all from the claims, never constants (K2 §7 H-2).

#: The three §12.2 access kinds — emitted separately, never merged
#: (SIG-UI-024 / SIG-RECON-034).
_NETWORK_ACCESS_KINDS: frozenset[str] = frozenset(
    {"configured_access", "observed_use", "declared_policy"}
)

#: Alias for the shared degree-predicate vocabulary (SIG-INGEST-043c /
#: K2 §7 H-4) — the degree is a node attribute, never an edge.
_DEGREE_PREDICATES = SHARING_DEGREE_PREDICATES

#: The epoch-zero placeholder a pre-P35.26 write stamped for "no recorded date"
#: (the ``*_no_epoch_zero`` constraints now refuse it on the spine). Rendered
#: ``undated`` — never a real-looking 1970 date.
_EPOCH_DATE = "1970-01-01"

#: ``reconcile.weight.currency`` C-codes → the web's currency words
#: (``web/src/lib/epistemic.ts#CURRENCY_LEVELS``), plus K2 §5.3's ``UNDATED``
#: class for an edge with no evidenced date (currency is uncomputable, not
#: fabricated).
_CURRENCY_WORDS = {"C1": "CURRENT", "C2": "AGING", "C3": "STALE", "C4": "HISTORICAL"}

#: valid-to bound kinds meaning the edge's valid time has ENDED (the
#: bound-kind vocabulary, ``db/deploy/role_edges.sql``: exact/before/after all
#: bound the end; ``ongoing``/``never`` assert non-ending, ``unknown`` asserts
#: nothing). The raw inputs for the H-3 historical marking.
_ENDED_TO_KINDS: frozenset[str] = frozenset({"exact", "before", "after"})


def _uuid_like(value: Any) -> bool:
    """True iff ``value`` parses as a UUID (an entity id, never a literal)."""
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


@dataclass(frozen=True)
class _NetworkEvidence:
    """The claim-side evidence the network surface joins onto its edges.

    ``claim_source``/``claim_predicate``/``claim_observed`` come from the
    publishable ``claim_weights`` read (one row per claim × source — sources
    accumulate, never overwrite); ``lineage`` carries each claim's declared
    independence class (P35.25 ``claim_lineage`` — ``unclassified`` is never
    corroboration); ``as_of`` pins currency to the build's snapshot date so the
    emitted class is reproducible, never wall-clock.
    """

    claim_source: Mapping[str, frozenset[str]]
    claim_predicate: Mapping[str, str]
    claim_observed: Mapping[str, str]
    lineage: Mapping[str, str]
    as_of: date | None


def _norm_iso_date(value: Any) -> str | None:
    """An ISO ``YYYY-MM-DD`` date, or ``None`` for absence/epoch placeholder."""
    if value is None:
        return None
    d = value.date() if isinstance(value, datetime) else value
    if isinstance(d, date):
        text = d.isoformat()
    else:
        text = str(value)[:10]
    return None if text == _EPOCH_DATE else text


def _network_evidence(raw: Mapping[str, Any], as_of: str | date | None) -> _NetworkEvidence:
    """Index the publishable-claim reads the network edges cite (P35.30)."""
    claim_source: dict[str, set[str]] = {}
    claim_predicate: dict[str, str] = {}
    claim_observed: dict[str, str] = {}
    for row in raw.get("claim_weights") or []:
        try:
            cid = str(row[0])
        except (TypeError, IndexError):
            continue
        if len(row) > 1 and row[1]:
            claim_source.setdefault(cid, set()).add(str(row[1]))
        if len(row) > 2 and row[2]:
            claim_predicate[cid] = str(row[2])
        if len(row) > 6:
            obs = _norm_iso_date(row[6])
            if obs:
                claim_observed[cid] = obs
    lineage: dict[str, str] = {}
    for row in raw.get("claim_lineage") or []:
        try:
            lineage[str(row[0])] = str(row[1])
        except (TypeError, IndexError):
            continue
    as_of_date: date | None = None
    if isinstance(as_of, datetime):
        as_of_date = as_of.date()
    elif isinstance(as_of, date):
        as_of_date = as_of
    elif as_of:
        try:
            as_of_date = date.fromisoformat(str(as_of)[:10])
        except ValueError:
            as_of_date = None
    return _NetworkEvidence(
        claim_source={cid: frozenset(s) for cid, s in claim_source.items()},
        claim_predicate=claim_predicate,
        claim_observed=claim_observed,
        lineage=lineage,
        as_of=as_of_date,
    )


def _sharing_edge_groups(
    sharing_edges: Sequence[SharingEdge],
) -> tuple[
    dict[tuple[str, str, str], list[SharingEdge]],
    dict[tuple[str, str, str], list[SharingEdge]],
    dict[str, list[SharingEdge]],
]:
    """Group the publishable sharing-edge claims for the network surface.

    Returns ``(entity, literal, degree)``:

    - ``entity`` — claims whose ``partner_ref`` is an entity id, keyed by
      (subject, partner, access_kind): the claim set behind each materialized
      edge, or a publishable entity edge awaiting materialization.
    - ``literal`` — claims whose ``partner_ref`` is a source-stated literal
      (the K2 §2 "literal twin" that never materializes), keyed the same.
    - ``degree`` — ``subject → claims`` for the count predicates: a node
      attribute, never an edge (SIG-INGEST-043c).
    """
    entity: dict[tuple[str, str, str], list[SharingEdge]] = {}
    literal: dict[tuple[str, str, str], list[SharingEdge]] = {}
    degree: dict[str, list[SharingEdge]] = {}
    for e in sharing_edges:
        if e.predicate_id in _DEGREE_PREDICATES:
            degree.setdefault(e.subject_id, []).append(e)
            continue
        if e.access_kind not in _NETWORK_ACCESS_KINDS or not e.partner_ref:
            continue
        key = (e.subject_id, e.partner_ref, e.access_kind)
        (entity if _uuid_like(e.partner_ref) else literal).setdefault(key, []).append(e)
    return entity, literal, degree


def _edge_support(claim_ids: Sequence[str], evidence: _NetworkEvidence) -> str:
    """The edge's §10.7-style support floor — derived, never a constant.

    Two or more DISTINCT *declared* independence classes among the backing
    claims is genuine corroboration (``STRONGLY_SUPPORTED``); an edge on a
    single source/class — or undeclared lineage — keeps the single-source
    floor (``WEAKLY_SUPPORTED``). ``CONFIRMED`` is never emitted at this layer
    (W4 needs artifact-weighted evidence the edge surface does not evaluate).
    """
    classes = {
        evidence.lineage.get(cid, "")
        for cid in claim_ids
        if evidence.lineage.get(cid) not in (None, "", "unclassified")
    }
    if len(classes) >= 2:
        return "STRONGLY_SUPPORTED"
    if claim_ids:
        return "WEAKLY_SUPPORTED"
    return "UNSUPPORTED"


def _edge_currency(
    predicate_ids: Sequence[str],
    observed: str | None,
    evidence: _NetworkEvidence,
) -> str | None:
    """The edge's currency class (§28.3, derived at export time).

    ``UNDATED`` when no evidenced date exists (K2 §5.3's fifth class); the
    worst (most conservative) class across the edge's distinct registered
    predicates; ``None`` when no predicate resolves in the registry — honest
    absence, never a guessed class.
    """
    if observed is None:
        return "UNDATED"
    if evidence.as_of is None:
        return None
    from reconcile.weight import currency, predicate_meta

    observed_d = date.fromisoformat(observed)
    classes: list[str] = []
    for pid in sorted(set(predicate_ids)):
        try:
            meta = predicate_meta(pid)
        except KeyError:
            continue
        classes.append(
            currency(
                volatility_class=str(meta.get("volatility_class", "")),
                half_life=str(meta.get("half_life", "")),
                observed_at=observed_d,
                as_of=evidence.as_of,
            )
        )
    if not classes:
        return None
    return _CURRENCY_WORDS[max(classes)]


def _predicate_words(predicate_ids: Sequence[str], fallback: str) -> str:
    """The relation in words — the claim's predicate unslugged, never a raw
    slot name (K2 H-2); ``fallback`` (the edge type / access kind, likewise
    unslugged) when no claim resolves."""
    words = sorted({p.replace("_", " ") for p in predicate_ids if p})
    return "; ".join(words) if words else fallback.replace("_", " ")


def _edge_withheld_entity(entity_id: str, labels: Mapping[str, EntityLabel]) -> bool:
    """True when the registry withholds the entity — a withheld/person entity
    is never a node and an edge that would name it is dropped whole (Part VIII,
    A-10 c)."""
    lbl = labels.get(entity_id)
    return lbl is not None and lbl.label_state == "withheld"


def _network_node(
    nodes: dict[str, dict[str, Any]],
    entity_id: str,
    *,
    node_type: str,
    word: str,
    labels: Mapping[str, EntityLabel],
) -> None:
    """Emit a node whose label is the registry's — never a raw id (L-2/D20)."""
    if entity_id in nodes:
        return
    lbl = labels.get(entity_id)
    node: dict[str, Any] = {"id": entity_id, "type": node_type}
    if lbl is not None and lbl.label:
        node["label"] = lbl.label
        node["label_basis"] = lbl.label_basis or "derived"
    elif lbl is not None and lbl.label_state == "not_yet_reviewed":
        # A-10 b: the typed review state IS the node label — visible, never
        # improvised.
        node["label"] = lbl.descriptor or "Organisation · not yet reviewed"
        node["label_basis"] = None
        node["label_state"] = "not_yet_reviewed"
    else:
        # The registry is the ONLY label authority — a source id is never a
        # label (K2 §2 fault 1, L-2/D20), so ``source_names`` is never consulted
        # here; an unlabelled entity renders the typed hash fallback.
        node["label"] = f"{word} #{hash4(entity_id)}"
        node["label_basis"] = "fallback"
    nodes[entity_id] = node


def _literal_partner_label(text: str) -> str | None:
    """The display label for a source-stated literal partner, or ``None``.

    ``None`` withholds the whole edge — the literal is never a node id, so a
    text we cannot honestly name never leaks. Two withhold cases (Part VIII,
    K2 §3.4 R-8 — the screen runs over literal party values BEFORE any label,
    node or slug is made from them):

    - a person-shaped literal (the affirmative ``natural_person_signal``);
    - a literal the shared derivation cannot turn into a display label (the
      L-2 typed fallback would leave the raw text as the node id).
    """
    if natural_person_signal(text):
        return None
    lbl = derive_label(
        LabelFacts(
            entity_id=f"literal:{text}",
            kind="org",
            disposition="allow",
            canonical_name=text,
        ),
        person_screen=lambda t: bool(natural_person_signal(t)),
    )
    if lbl.label is None or lbl.label_basis == "fallback":
        return None
    return lbl.label


def _emit_network_edge(
    out_edges: list[dict[str, Any]],
    *,
    src: str,
    dst: str,
    access_kind: str,
    direction: str,
    relation_fallback: str,
    claims: Sequence[SharingEdge],
    extra_claim_ids: Sequence[str],
    evidence: _NetworkEvidence,
    source_names: Mapping[str, str],
    valid_from_kind: str | None,
    valid_to_kind: str | None,
    valid_to: Any,
    extra_observed: Any = None,
) -> None:
    """Emit one honest evidence-carrying edge (P35.30, SIG-EXPORT-D21 draft)."""
    claim_ids = sorted({c.claim_id for c in claims if c.claim_id} | set(extra_claim_ids))
    predicate_ids = sorted(
        {c.predicate_id for c in claims}
        | {evidence.claim_predicate[cid] for cid in claim_ids if cid in evidence.claim_predicate}
    )
    source_ids = sorted(
        {c.source_id for c in claims if c.source_id}
        | {sid for cid in claim_ids for sid in evidence.claim_source.get(cid, ())}
    )
    observed_dates = sorted(
        {
            d
            for d in (
                *(_norm_iso_date(c.observed_at) for c in claims),
                *(_norm_iso_date(evidence.claim_observed.get(cid)) for cid in claim_ids),
                _norm_iso_date(extra_observed),
            )
            if d
        }
    )
    observed = observed_dates[0] if observed_dates else None
    date_kind = "observed" if observed else "undated"
    currency = _edge_currency(predicate_ids, observed, evidence)
    valid_to_s = _norm_iso_date(valid_to)
    ended = valid_to_s is not None or (valid_to_kind or "") in _ENDED_TO_KINDS
    historical = ended or currency == "HISTORICAL"
    sources = sorted({source_names[sid] for sid in source_ids if sid in source_names})
    out_edges.append(
        {
            "from": src,
            "to": dst,
            "access_kind": access_kind,
            "relation": _predicate_words(predicate_ids, relation_fallback),
            "predicate": _predicate_words(predicate_ids, relation_fallback),
            "direction": direction,
            "observed_at": observed,
            "date_kind": date_kind,
            "valid_from_kind": valid_from_kind or "unknown",
            "valid_to_kind": valid_to_kind or "unknown",
            "valid_to": valid_to_s,
            "source": "; ".join(sources) if sources else None,
            "sources": sources,
            "currency": currency,
            "historical": historical,
            # Derived from the claim set's declared independence classes —
            # never a constant (the pre-P35.30 ``WEAKLY_SUPPORTED``/
            # ``evidence_count: 1`` placeholders are gone, D21).
            "support": _edge_support(claim_ids, evidence),
            "evidence_count": len(claim_ids),
            # P32.15 (SIG-FIND-004) — the supporting claims travel with the
            # edge; ``evidence`` stays as the P32.15 name, ``claim_ids`` is
            # the D21 contract's name for the same set.
            "evidence": claim_ids,
            "claim_ids": claim_ids,
        }
    )


def _degree_attribute(node: dict[str, Any], claims: Sequence[SharingEdge]) -> None:
    """Attach the source-stated partner COUNT to the node — an attribute, never
    an edge (SIG-INGEST-043c / H-4). Carries its own provenance (§3.1)."""
    values = sorted(
        {int(e.partner_ref) for e in claims if e.partner_ref and e.partner_ref.strip().isdigit()}
    )
    if not values:
        return
    node["degree"] = values[0] if len(values) == 1 else values
    node["degree_claim_ids"] = sorted(e.claim_id for e in claims if e.claim_id)
    observed = sorted({d for d in (_norm_iso_date(e.observed_at) for e in claims) if d})
    if observed:
        node["degree_observed_at"] = observed[0]


def _network_from_materialized(
    edges: Sequence[Mapping[str, Any]],
    source_names: Mapping[str, str],
    labels: Mapping[str, EntityLabel] | None = None,
    *,
    sharing_edges: Sequence[SharingEdge] = (),
    evidence: _NetworkEvidence | None = None,
) -> dict[str, Any]:
    """Build the §39.4 network surface from the materialized ``relationship`` edges (P28.2).

    Consumes ``reconcile.materialize.read_materialized_edges`` (already reconciled through the
    P08.2 §29.3 reconciler): the three §12.2 access kinds stay separate, every edge carries its
    backing ``evidence_claim`` (no unevidenced edge, §3.1). An edge whose access kind is not one
    of the three typed kinds is honestly absent from the typed network rather than coerced.

    P35.30 (SIG-EXPORT-D21 draft / K2 §7 H-2…H-4): each edge rejoins the
    publishable claim set that evidences it (the relationship row stores one
    representative claim; ``sharing_edges`` carries the full publishable set)
    and gains the real dates/kinds/sources/currency. The literal-twin claims a
    materializer could not map to an entity (``skipped_unmapped``) join the
    emitted edge set as person-screened literal partner nodes; a withheld or
    person-shaped endpoint drops the edge whole (Part VIII).
    """
    labels = labels or {}
    evidence = evidence or _NetworkEvidence({}, {}, {}, {}, None)
    entity_claims, literal_claims, degree_claims = _sharing_edge_groups(sharing_edges)
    nodes: dict[str, dict[str, Any]] = {}
    out_edges: list[dict[str, Any]] = []
    covered: set[tuple[str, str, str]] = set()
    for e in edges:
        access_kind = str(e.get("access_kind"))
        if access_kind not in _NETWORK_ACCESS_KINDS:
            continue
        src = str(e["from_entity"])
        dst = str(e["to_entity"])
        if _edge_withheld_entity(src, labels) or _edge_withheld_entity(dst, labels):
            continue
        key = (src, dst, access_kind)
        covered.add(key)
        claims = entity_claims.get(key, [])
        _network_node(nodes, src, node_type="agency", word="Record", labels=labels)
        _network_node(nodes, dst, node_type="partner", word="Partner", labels=labels)
        _emit_network_edge(
            out_edges,
            src=src,
            dst=dst,
            access_kind=access_kind,
            direction=str(e.get("direction") or "a_to_b"),
            relation_fallback=str(e.get("edge_type") or access_kind),
            claims=claims,
            extra_claim_ids=[str(e["evidence_claim"])] if e.get("evidence_claim") else [],
            evidence=evidence,
            source_names=source_names,
            valid_from_kind=e.get("valid_from_kind"),
            valid_to_kind=e.get("valid_to_kind"),
            valid_to=e.get("valid_to"),
            extra_observed=e.get("observed_at"),
        )
    # Publishable entity-ref claims with no materialized edge (awaiting
    # materialization) still emit — the claim is publishable; only the
    # reconciled row is missing.
    for (src, dst, kind), claims in sorted(entity_claims.items()):
        if (src, dst, kind) in covered:
            continue
        if _edge_withheld_entity(src, labels) or _edge_withheld_entity(dst, labels):
            continue
        _network_node(nodes, src, node_type="agency", word="Record", labels=labels)
        _network_node(nodes, dst, node_type="partner", word="Partner", labels=labels)
        _emit_network_edge(
            out_edges,
            src=src,
            dst=dst,
            access_kind=kind,
            direction="a_to_b",
            relation_fallback=kind,
            claims=claims,
            extra_claim_ids=[],
            evidence=evidence,
            source_names=source_names,
            valid_from_kind="unknown",
            # No reconciled valid-to bound exists yet — ``unknown``, never the
            # assertion ``ongoing`` (absence of an end bound is not evidence of
            # continuation).
            valid_to_kind="unknown",
            valid_to=None,
        )
    # The literal-twin edges (K2 §2): a source-stated partner name that never
    # resolved to an entity joins the edge set — person-screened first; a
    # person-shaped literal withholds the edge whole (Part VIII, §3.4 R-8).
    for (src, literal_text, kind), claims in sorted(literal_claims.items()):
        label = _literal_partner_label(literal_text)
        if label is None:
            continue
        if _edge_withheld_entity(src, labels):
            continue
        _network_node(nodes, src, node_type="agency", word="Record", labels=labels)
        nodes.setdefault(
            literal_text,
            {
                "id": literal_text,
                "label": label,
                "type": "partner",
                "label_basis": "source_name",
            },
        )
        _emit_network_edge(
            out_edges,
            src=src,
            dst=literal_text,
            access_kind=kind,
            direction="a_to_b",
            relation_fallback=kind,
            claims=claims,
            extra_claim_ids=[],
            evidence=evidence,
            source_names=source_names,
            valid_from_kind="unknown",
            valid_to_kind="unknown",
            valid_to=None,
        )
    # Degree is a node attribute, never an edge (SIG-INGEST-043c / H-4).
    for subject, claims in sorted(degree_claims.items()):
        node = nodes.get(subject)
        if node is None:
            if _edge_withheld_entity(subject, labels):
                continue
            _network_node(
                nodes,
                subject,
                node_type="agency",
                word="Record",
                labels=labels,
            )
            node = nodes[subject]
        _degree_attribute(node, claims)
    return {"nodes": [nodes[k] for k in sorted(nodes)], "edges": out_edges, "access_paths": []}


def _map_layer(
    dataset: ShapedDataset,
    *,
    resolved: Mapping[str, Any] | None = None,
    exclude: set[str] | frozenset[str] = frozenset(),
    placements: Mapping[str, _placement.PlacementResult] | None = None,
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
        res = placements.get(site.entity_id) if placements is not None else None
        # P35.19 / JUR-02b (K4 §3.3): under a placement run only a
        # ``point_in_polygon``-placed point may draw — a declared-level
        # fallback, a suspected swap/flip, a rejected point, and a guarded
        # agency centroid never paint the map. The additive
        # ``jurisdictionKey``/``placementCheck`` fields carry the honest
        # verdict on every asset (the frozen MapAsset contract admits extra
        # properties).
        draw_point = (
            site.latitude is not None
            and site.longitude is not None
            and (
                placements is None
                or (res is not None and res.placement_basis == "point_in_polygon")
            )
        )
        asset: dict[str, Any] = {
            "id": site.entity_id,
            # P35.29 (L-2): the registry label — never the entity id.
            "label": site.label or f"Surveillance camera #{hash4(site.entity_id)}",
            "jurisdiction": site.jurisdiction,
            # P35.15a / PKG-07: the declared technology slug for the map's
            # facet band; `technologyStatus` keeps an unresolved/conflicted
            # declaration honest (never a guessed class).
            "technology": site.technology,
            "technologyStatus": site.technology_status,
            "tier": site.sensitivity_tier,
            "lat": site.latitude if draw_point else None,
            "lon": site.longitude if draw_point else None,
            "precision": site.precision,
        }
        if res is not None:
            asset["jurisdictionKey"] = res.jurisdiction_key
            asset["placementCheck"] = res.placement_check
        if not draw_point:
            # An honest reason there is no point (a gap, not a guess, §3.1), in the web's
            # §9.5 absence vocabulary (`epistemic.ts#ABSENCE_KINDS`, P30.3): conflicting
            # coordinate evidence is UNRESOLVED; a record whose named source carries no
            # coordinate is NO_EVIDENCE_FOUND (the point was looked for in that record).
            # P35.19: under a placement run a withheld/suspect point is also
            # UNRESOLVED — the record HAS coordinates but the ruleset refused
            # to publish them as a point (the placementCheck names why).
            asset["locationAbsence"] = (
                "UNRESOLVED"
                if site.point_status == "conflicted" or site.latitude is not None
                else "NO_EVIDENCE_FOUND"
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


def _network(
    dataset: ShapedDataset,
    source_names: Mapping[str, str],
    labels: Mapping[str, EntityLabel] | None = None,
    *,
    evidence: _NetworkEvidence | None = None,
) -> dict[str, Any]:
    """Surface 4 — NetworkNode / NetworkEdge (§39.4). The three §12.2 access-edge
    types are never merged; an unclassifiable edge carries no typed relationship, so
    it is honestly absent from the typed network rather than coerced into one.

    The compute-on-read fallback (ADR-092) — P35.30 routes it through the SAME
    emitter as the materialized path so both paths produce the additive D21
    fields (dates/kinds, sources, claim ids, currency); a claim-level edge that
    has not been reconciled simply carries ``valid_from_kind="unknown"`` (the
    single-snapshot rule — never an inferred start).
    """
    return _network_from_materialized(
        [],
        source_names,
        labels,
        sharing_edges=dataset.sharing_edges,
        evidence=evidence,
    )


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
    captures never carry bytes (§17.5).

    P34.20 (K8 NEW-6): the row also carries the registry ``source_name``, the
    honest ``capture_classification`` (synthetic captures are run records —
    SIG-EVUI-D04), and the S-6-scrubbed ``upstream_url`` (the source's own
    link, present only where the query's effective-rights gate allows it).
    """
    artifacts: list[dict[str, Any]] = []
    for r in raw.get("evidence_artifacts") or []:
        (
            artifact_id,
            source_id,
            title,
            artifact_type,
            locator,
            direct,
            capture_status,
            published,
            source_name,
            capture_class,
            upstream_url,
        ) = r
        artifact: dict[str, Any] = {
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
        # Optional, additive fields — absent means "not known / not allowed",
        # never a fabricated value.
        if source_name:
            artifact["source_name"] = str(source_name)
        if capture_class:
            artifact["capture_classification"] = str(capture_class)
        if upstream_url:
            artifact["upstream_url"] = str(upstream_url)
        artifacts.append(artifact)
    return {"artifacts": artifacts, "claim_views": []}


def _corrections(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Surface 9 — CorrectionEntry[] (§39.8). History never rewritten: the prior
    value stays citable at its belief-time (SIG-GOV-005)."""
    out: list[dict[str, Any]] = []
    for r in raw.get("corrections") or []:
        (
            claim_id,
            subject_id,
            predicate_id,
            raw_value,
            reason,
            revises,
            retraction,
            recorded,
            old_id,
            old_value,
            old_belief,
            old_eligible,
        ) = r
        old_id = str(old_id) if old_id else ""
        # The prior assertion's value/date surface only when that row is itself
        # publicly eligible — otherwise the entry carries the withheld marker.
        show_old = bool(old_id) and bool(old_eligible)
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
                # P32.16a (SIG-FIND-008): old/new assertion identity — the entry
                # points to BOTH the superseded claim and this successor.
                "previous_claim_id": old_id,
                "revises_claim": str(revises or ""),
                "retraction_of": str(retraction or ""),
                "previous_value": str(old_value or "") if show_old else "",
                "corrected_value": str(raw_value or ""),
                "previous_belief_date": (
                    old_belief.date().isoformat()
                    if show_old and hasattr(old_belief, "date")
                    else ""
                ),
                "previous_withheld": bool(old_id) and not show_old,
                "subject_path": f"/dossier/{subject_id}",
            }
        )
    return out


#: The honest label a queue card carries in its classification fields when the
#: task's ``task_type`` is not in the §33.2 catalog (a legacy/hand-inserted
#: row, or catalog drift). P34.12 (K11 RQ-00, C3 NEW-10): never an invented
#: ``contributor`` assignee, never an ``unknown`` effort. Mirrored verbatim by
#: the web surface (``web/src/lib/research-queue.ts``), kept in lockstep by
#: ``tests/exports/test_spine_export.py``.
NOT_YET_CLASSIFIED = "not yet classified"


def _research_queue(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Surface 10 — ResearchTaskCard[] (§39.7). Every task has a testable closing
    condition (SIG-TASK-002).

    P34.12 (K11 RQ-00): the card carries the task's own ``task_id`` and its
    classification comes from the §33.2 catalog — the ``TaskType`` registry
    entry for the row's ``task_type`` supplies ``assignee_class``,
    ``effort_estimate``, ``geographic_scope`` and the permitted ``dispositions``
    (SIG-TASK-001/008). A type the catalog does not know emits
    ``not yet classified`` for those fields plus the FULL §33.4 disposition
    vocabulary — an unclassified task may reach any legal outcome, and `[]`
    would claim it can never leave the queue.
    """
    registry = _task_catalog()
    out: list[dict[str, Any]] = []
    for r in raw.get("research_tasks") or []:
        task_id, task_type, subject_id, jurisdiction_id, priority, status, disp, closing, _det = r[
            :9
        ]
        # P29.2: trigger_kind/trigger_ref cite what made the detector fire — present when the
        # detector run wrote the row, absent (None) for a legacy/hand-inserted row.
        trigger_kind = r[9] if len(r) > 9 else None
        trigger_ref = r[10] if len(r) > 10 else None
        spec = registry.get(str(task_type)) if str(task_type) in registry else None
        card: dict[str, Any] = {
            "task_id": str(task_id),
            "task_type": str(task_type),
            "subject_id": str(subject_id or task_id),
            "subject_label": str(subject_id or task_id),
            "closing_condition": str(closing),
            "evidence_sought": str(task_type),
            "assignee_class": (
                spec.assignee_class.value if spec is not None else NOT_YET_CLASSIFIED
            ),
            "effort_estimate": (
                spec.effort_estimate.value if spec is not None else NOT_YET_CLASSIFIED
            ),
            "geographic_scope": (
                spec.geographic_scope.value if spec is not None else NOT_YET_CLASSIFIED
            ),
            "jurisdiction": str(jurisdiction_id or ""),
            "dispositions": (
                [d.value for d in spec.dispositions]
                if spec is not None
                else [d.value for d in Disposition]
            ),
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


#: coverage_record ``absence_kind`` (§32.1/SIG-METRIC-002) → the web ``Gap.kind``
#: (§9.5/SIG-UI-007). ``not_applicable`` is not an unknown — it drops out.
_COVERAGE_ABSENCE_TO_GAP_KIND: dict[str, str | None] = {
    "not_researched": "NOT_RESEARCHED",
    "searched_not_found": "NO_EVIDENCE_FOUND",
    "evidence_of_absence": "EVIDENCE_OF_ABSENCE",
    "not_applicable": None,
}


def _coverage_gaps(
    jurisdiction: str,
    coverage_rows: Sequence[Mapping[str, Any]],
    *,
    entity_label_by_id: Mapping[str, str],
    site_jurisdiction: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Evidence-backed dossier gaps (P32.17, SIG-DOS-001): negative-space
    ``coverage_record`` rows become first-class gaps with their absence kind and
    the named searched sources — replacing the former hardcoded "Data-sharing
    partners / NOT_RESEARCHED" row that minted the same generic gap on every
    jurisdiction regardless of evidence. A spine with no recorded absences emits
    zero gaps (honest absence, never a fabricated field state).
    """
    subjects_in_jurisdiction = {eid for eid, j in site_jurisdiction.items() if j == jurisdiction}
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in coverage_rows:
        kind = _COVERAGE_ABSENCE_TO_GAP_KIND.get(str(row.get("absence_kind") or ""))
        if kind is None:
            continue  # a metric row or a not_applicable row is not a gap
        subject = str(row.get("subject_id") or "")
        attributed = (
            entity_label_by_id.get(str(row.get("jurisdiction_id") or "")) == jurisdiction
            or subject in subjects_in_jurisdiction
        )
        if not attributed:
            continue
        predicate = str(row.get("predicate_id") or "unrecorded_field")
        key = (predicate, kind)
        if key in seen:
            continue
        seen.add(key)
        searched = [str(s) for s in (row.get("sources_searched") or ()) if s]
        gap: dict[str, Any] = {
            "label": predicate.replace("_", " "),
            "kind": kind,
            # P35.18 (JUR-02a): ``jurisdiction`` is the declared-scheme bucket
            # key — the subject id slugs the KEY, never a bare value.
            "subject_id": subject or f"jurisdiction:{jurisdiction_slug(jurisdiction)}",
            "predicate_id": predicate,
            "note": "Recorded negative-space coverage finding (§32.1).",
        }
        if searched:
            gap["sources_searched"] = searched
        out.append(gap)
    return out


def _dossiers(
    dataset: ShapedDataset,
    as_of: str,
    belief: datetime | None,
    *,
    accountability_links: Sequence[Mapping[str, Any]] = (),
    coverage_rows: Sequence[Mapping[str, Any]] = (),
    entity_label_by_id: Mapping[str, str] | None = None,
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
    # P35.29 (K2 §3/L-1): jurisdiction attribution reads the shared label
    # registry — a row's ``jurisdiction_id`` entity label is looked up, never
    # the raw identifier value and never guessed from the id.
    label_by_id: dict[str, str] = dict(entity_label_by_id or {})
    site_jurisdiction = {str(s.entity_id): s.jurisdiction for s in dataset.sites}
    dossiers: list[dict[str, Any]] = []
    for group in dataset.jurisdictions:
        # P35.18 (JUR-02a): the dossier slug derives from the declared-scheme
        # jurisdiction KEY (``iso3166-2:US-OK`` → ``iso3166-2-us-ok``), never
        # a bare asserted value.
        slug = jurisdiction_slug(group.jurisdiction)
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
        # Evidence-backed gaps only (P32.17/SIG-DOS-001): the recorded coverage
        # absences for this jurisdiction, plus conflicted-subject rows — never a
        # hardcoded generic gap.
        gaps = _coverage_gaps(
            group.jurisdiction,
            coverage_rows,
            entity_label_by_id=label_by_id,
            site_jurisdiction=site_jurisdiction,
        )
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
            # P32.17 (SIG-DOS-003): the §39.2 inventory overview is marked so it
            # can never be mistaken for a reviewed research-dossier portfolio.
            "kind": "inventory_overview",
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


# P35.18 (JUR-02a): the only slugging this module performs on the jurisdiction
# path is ``jurisdictions.jurisdiction_slug`` — of the declared-scheme KEY,
# never a bare value; the old bare-value slug helper is gone by design.


# --------------------------------------------------------------------------- #
# The build                                                                    #
# --------------------------------------------------------------------------- #


def _apply_publication_withdrawals(
    claims: Sequence[ShapingClaim],
) -> tuple[list[ShapingClaim], list[dict[str, Any]]]:
    """Drop committed publication-withdrawal targets (P34.19, F-337, SIG-GOV-007).

    The committed ``sig.publication-withdrawals/1`` list names the claims that
    leave every public artifact — leak-provenance refusals and other
    ``rights_withdrawal`` entries. Matching is fail-closed
    (``candidate_claim_ids`` suppress alongside ``claim_ids`` until a host-side
    rerun narrows them); unmatched claims pass through untouched. Returns the
    kept claims plus one loud exclusion record per dropped claim.
    """
    kept: list[ShapingClaim] = []
    dropped: list[dict[str, Any]] = []
    for claim in claims:
        # A listed claim id is suppressed; so is ANY claim about a listed
        # subject entity (the withdrawal's public-artifact semantics —
        # "suppress matching claims and their subject entities" — fail
        # closed both directions; the spine record itself is untouched).
        entry = policy_withdrawals.withdrawal_for_claim(
            str(claim.claim_id)
        ) or policy_withdrawals.withdrawal_for_entity(str(claim.subject_id))
        if entry is None:
            kept.append(claim)
            continue
        dropped.append(
            {
                "surface": "all",
                "source_id": claim.source_id,
                "entity_id": claim.subject_id,
                "claim_id": str(claim.claim_id),
                "upstream_id": entry["upstream_id"],
                "reason": entry["reason"],
                "authority": entry["authority"],
            }
        )
    return kept, dropped


def _base_source_id(slice_key: str) -> str:
    """The source id a ``source@rights`` multi-rights slice key counts under."""
    return slice_key.split("@", 1)[0]


def _terms_disclosure_payload(
    rows_by_compartment: Mapping[str, list[C.ExportRow]],
    *,
    as_of: str,
    generated_at: str,
) -> dict[str, Any] | None:
    """The ``web/terms_disclosure.json`` payload (sig.terms-disclosure/1).

    Every affected source this export actually carries is listed with its
    captured terms verbatim + the ADR-183 publication basis; the per-source
    row counts are computed from the built slices (never copied from the
    acceptance narrative). ``None`` when no affected source has rows (a
    fixture or scoped export without them emits no artifact — honest absence).
    """
    table = policy_disclosure.express_terms()
    counts: dict[str, int] = {}
    for rows in rows_by_compartment.values():
        for row in rows:
            base = _base_source_id(row.source_id)
            counts[base] = counts.get(base, 0) + 1
    sources = [
        {**entry, "export_row_count": counts[entry["source_id"]]}
        for entry in table["sources"]
        if counts.get(entry["source_id"], 0) > 0
    ]
    if not sources:
        return None
    return {
        "schema": "sig.terms-disclosure/1",
        "as_of": as_of,
        "generated_at": generated_at,
        "basis": table["basis"],
        "sources": sources,
    }


#: P34.21b (E2-12 / ADR-194): the marker a ``rights_decision.basis`` carries
#: when it is an attribution correction (``db.rights_corrections`` validates
#: the recorded basis names ADR-194) — what distinguishes a correction from
#: an ordinary rights-resolution decision in this export's effective set.
_CORRECTION_BASIS_MARKER = "ADR-194"


def _attribution_corrections_payload(
    claims: Sequence[ShapingClaim],
    *,
    as_of: str,
    generated_at: str,
) -> dict[str, Any] | None:
    """The ``web/attribution_corrections.json`` payload (sig.attribution-corrections/1).

    One row per source whose rows this export resolves through an attribution-
    correction ``rights_decision`` (the ADR-194 basis marker), carrying the
    decision's ``decided_at`` — the dated correction note ``/sources/``
    renders (E2-12: "earlier downloads credited some rows to the wrong
    source"). Source ids are the claims' ALREADY-ALIASed (re-keyed) public
    ids, so the note never repeats a retired identifier. ``None`` when no
    carried claim resolves through a correction — honest absence (a fixture
    or pre-backfill export emits no artifact and the page shows no note).
    """
    per_source: dict[str, dict[str, Any]] = {}
    for claim in claims:
        basis = claim.effective_decision_basis or ""
        if _CORRECTION_BASIS_MARKER not in basis:
            continue
        if not claim.source_id or claim.effective_decision_decided_at is None:
            continue
        stamp = claim.effective_decision_decided_at.isoformat()
        entry = per_source.setdefault(
            claim.source_id, {"decided_at": "", "basis": "", "affected_rows": 0}
        )
        entry["affected_rows"] += 1
        if stamp > entry["decided_at"]:
            # the newest correction decision wins the stamp/basis pair — the
            # append-only ordering the effective-rights join itself obeys.
            entry["decided_at"] = stamp
            entry["basis"] = basis
    if not per_source:
        return None
    return {
        "schema": "sig.attribution-corrections/1",
        "as_of": as_of,
        "generated_at": generated_at,
        "note": (
            "The append-only attribution corrections (E2-12 / ADR-194) this "
            "export's effective rights resolve through — one row per corrected "
            "source with the decision's decided_at, its recorded basis, and "
            "the count of rows this export carries under it. Earlier downloads "
            "of the same rows may carry the wrong credit; re-users must take "
            "this export's per-row attribution."
        ),
        "corrections": [
            {
                "source_id": sid,
                "decided_at": entry["decided_at"],
                "basis": entry["basis"],
                "affected_rows": entry["affected_rows"],
            }
            for sid, entry in sorted(per_source.items())
        ],
    }


def _compartment_tile_attribution(
    rows: Sequence[C.ExportRow], index: Mapping[str, RightsRecord]
) -> str | None:
    """The drawn sources' own credit for a compartment's tile archive (E2-12).

    The deduplicated attribution strings of the slice records actually drawn in
    this compartment — the line the PMTiles metadata + map sources carry instead
    of the generic "© The SIG project" fallback. ``None`` when no slice record
    carries attribution (the renderer's licence-level fallback applies).
    """
    lines: dict[str, None] = {}
    for row in rows:
        record = index.get(row.source_id)
        text = (record.attribution if record is not None else "") or ""
        if text.strip():
            lines.setdefault(text.strip())
    return " · ".join(sorted(lines)) if lines else None


def _compartment_attribution(
    compartment: str,
    rows: Sequence[C.ExportRow],
    *,
    index: Mapping[str, RightsRecord],
    license_id: str,
    license_url: str | None,
    source_names: Mapping[str, str],
    registry: Mapping[str, Any] | None,
    generated_at: str,
) -> dict[str, Any] | None:
    """The ``<compartment>/ATTRIBUTION.json`` payload for a compartment.

    P34.21a (E2-12, ADR-194, SIG-CONTRIB-020/SIG-LIC-011): EVERY source whose
    rows sit in this compartment is named — not only the express-terms set —
    with the effective attribution + terms URL its own rights record carries,
    the licence the file computes to, its licence URL (``null`` for a
    project LicenseRef — the terms then live in ``terms_url``/the recorded
    basis), the ``attribution_required`` fact, and the row count this export
    contributes. Express-terms sources additionally carry their captured terms
    verbatim + the operator-accepted publication basis (P34.19, ADR-183 —
    additive keys, unchanged). ``None`` when the compartment carries no rows
    (honest absence — never an empty artifact).
    """
    reg = _license_registry(registry)["licenses"]
    facts = reg.get(license_id, {})
    per_source: dict[str, dict[str, Any]] = {}
    any_express_terms = False
    for row in rows:
        # Key on the slice key (source or source@rights_id): a source sliced
        # under two rights records appears once per record, each named by its
        # own effective attribution/terms (SIG-LIC-004a).
        record = index.get(row.source_id)
        base = _base_source_id(row.source_id)
        rec = per_source.setdefault(
            row.source_id,
            {
                "source_id": base,
                "name": source_names.get(base) or base,
                "license": license_id,
                "license_url": license_url,
                "attribution_required": bool(facts.get("attribution_required", True)),
                "attribution": record.attribution if record is not None else "",
                "terms_url": record.terms_url if record is not None else "",
                "rights_ids": [],
                "slice_source_ids": [],
                "rows": 0,
            },
        )
        rights_id = str(row.data.get("rights_id") or "")
        if rights_id and rights_id not in rec["rights_ids"]:
            rec["rights_ids"].append(rights_id)
        disclosure = policy_disclosure.disclosure_for(base)
        if disclosure is not None and "captured_terms_verbatim" not in rec:
            any_express_terms = True
            rec["captured_terms_verbatim"] = disclosure["captured_terms_verbatim"]
            rec["captured_terms_evidence"] = disclosure["captured_terms_evidence"]
            rec["publication_basis"] = disclosure["publication_basis"]
        rec["rows"] = int(rec["rows"]) + 1
        if row.source_id not in rec["slice_source_ids"]:
            rec["slice_source_ids"].append(row.source_id)
    if not per_source:
        return None
    note = (
        "Every source whose rows sit in this compartment is named with the "
        "effective attribution its own rights record carries (E2-12 / ADR-194) — "
        "the credit a re-user must carry (SIG-CONTRIB-020, SIG-LIC-011)."
    )
    if any_express_terms:
        note += (
            " Sources carrying captured_terms_verbatim publish under the "
            "operator's recorded acceptance of the express-terms risk (P34.19, "
            "ADR-183); the captured terms are verbatim. Scheduled refreshes of "
            "the same sources are covered (SB-2); a new source with a "
            "non-commercial clause follows A-9 (facts and pointers only)."
        )
    return {
        "schema": "sig.compartment-attribution/2",
        "compartment": compartment,
        "generated_at": generated_at,
        "license": license_id,
        "license_url": license_url,
        "attribution_required": bool(facts.get("attribution_required", True)),
        "publication_basis": PUBLICATION_BASIS,
        "note": note,
        "sources": [per_source[k] for k in sorted(per_source)],
    }


def _table(name: str, rows: Sequence[C.ExportRow], *, kind: str, compartment: str) -> C.ExportTable:
    return C.ExportTable(name=name, rows=tuple(rows), kind=kind, compartment=compartment)


# --------------------------------------------------------------------------- #
# P35.29 (K2 §3 / A-10, R11-K13-GX-01): the shared ``sig.entity-label/1``      #
# registry. ONE derivation (policy.labels.derive_label) over the export's own  #
# snapshot — the artifact, map, dossier, network and record surfaces all read  #
# this registry rather than re-deriving a name (L-1).                          #
# --------------------------------------------------------------------------- #

#: The disposition vocabulary's denying side (policy.eligibility.DENYING).
_DENYING_DISPOSITIONS = frozenset({"withhold", "restrict", "withdraw"})
#: Organisation ``status`` values the shared selector denies on.
_WITHDRAWN_ORG_STATUSES = frozenset({"withdrawn", "suppressed"})


def _org_disposition(
    review_required: bool, status: str | None, effective: str | None
) -> str | None:
    """Render the shared selector's outcome for an organisation (A-10 / D-K2-1).

    Exactly ``db.dispositions.entity_eligible_sql``'s org rule, rendered as a
    label input rather than a boolean: a current deny disposition or a
    withdrawn/suppressed org status denies; a recorded ``allow`` or an org
    without ``publication_review_required`` labels; everything else is the
    operator-mandated typed ``not_yet_reviewed`` state (``None`` — the label
    module renders the row; we never silently drop the org).
    """
    if effective in _DENYING_DISPOSITIONS or (status or "") in _WITHDRAWN_ORG_STATUSES:
        return "deny"
    if effective == "allow" or not review_required:
        return "allow"
    return None


def _label_registry(
    raw: Mapping[str, Any],
    dataset: ShapedDataset,
    *,
    retrieval: date,
    registry: Mapping[str, Any] | None,
) -> tuple[dict[str, EntityLabel], dict[str, set[str]]]:
    """Build ``entity_id → EntityLabel`` + ``entity_id → compartment set``.

    Compartment rule (the same law as ``_record_claims``): an entity's rows
    file under every compartment its label-input claims license to — the
    label text embeds those claims' literals, so an ODbL-sourced name lands
    in the ODbL compartment, never co-mingled. Site subjects additionally
    carry their published-slice licences (the caller augments the returned
    sets after ``_slice_sites``); an entity with no publishable label inputs
    defaults to the SIG compartment at emit time (its typed/fallback row is
    SIG's own derived framing).
    """
    dispositions = {str(r[0]): str(r[1]) for r in (raw.get("label_entity_dispositions") or [])}
    identifiers: dict[str, list[tuple[str, str]]] = {}
    for row in raw.get("entity_labels") or []:
        try:
            identifiers.setdefault(str(row[0]), []).append((str(row[1]), str(row[2])))
        except (TypeError, IndexError):
            continue
    fields: dict[str, dict[str, str]] = {}
    fact_rights: dict[str, dict[str, RightsRecord]] = {}
    for row in raw.get("label_facts") or []:
        try:
            sid, pred, val = str(row[0]), str(row[1]), row[2]
            src, spdx, attr = row[3], str(row[4]), str(row[5])
            redist, deriv, terms, rid = str(row[6]), str(row[7]), row[8], str(row[9])
        except (TypeError, IndexError):
            continue
        if val not in (None, ""):
            fields.setdefault(sid, {}).setdefault(pred, str(val))
        if src:
            fact_rights.setdefault(sid, {})[rid] = RightsRecord(
                source_id=str(src),
                spdx=spdx,
                attribution=attr,
                redistributable=redist == "yes",
                derivative_permitted=deriv == "yes",
                terms_url=str(terms or ""),
                retrieval_date=retrieval,
            )
    site_by_id = {s.entity_id: s for s in dataset.sites}
    results: list[EntityLabel] = []
    comps: dict[str, set[str]] = {}
    for row in raw.get("label_entities") or []:
        try:
            eid, etype = str(row[0]), str(row[1])
            skey = str(row[2]) if row[2] else None
            merged = row[3]
            cname = str(row[4]) if row[4] else None
            review_req = bool(row[5])
            status = str(row[6]) if row[6] else None
        except (TypeError, IndexError):
            continue
        kind = kind_for(etype, skey)
        effective = dispositions.get(eid)
        if merged or kind == "person":
            disposition: str | None = "deny"
        elif kind == "org":
            disposition = _org_disposition(review_req, status, effective)
        else:
            disposition = "deny" if effective in _DENYING_DISPOSITIONS else "allow"
        site = site_by_id.get(eid)
        extra: dict[str, Any] = {}
        place: str | None = None
        if site is not None:
            if site.technology:
                extra["technology"] = site.technology
            if site.jurisdiction_status == "resolved":
                place = site.jurisdiction
        facts = LabelFacts(
            entity_id=eid,
            entity_key=skey,
            entity_type=etype,
            kind=kind,
            disposition=disposition,
            canonical_name=cname,
            place=place,
            identifiers=tuple(identifiers.get(eid, ())),
            fields=fields.get(eid, {}),
            extra=extra,
        )
        results.append(
            derive_label(
                facts,
                person_screen=lambda t: bool(natural_person_signal(t)),
            )
        )
        entity_comps = comps.setdefault(eid, set())
        for rec in (fact_rights.get(eid) or {}).values():
            if export_refusal_reason(rec, registry) is not None:
                continue
            licence = compute_export_license([rec], registry)
            comp = C.compartment_for_license(licence, None, registry)
            if comp:
                entity_comps.add(str(comp))
    resolved = {r.entity_id: r for r in resolve_disambiguators(results)}
    return resolved, comps


def _label_artifacts(
    registry: Mapping[str, EntityLabel],
    entity_comps: Mapping[str, set[str]],
    *,
    default_compartment: str,
) -> dict[str, list[dict[str, Any]]]:
    """``compartment → sig.entity-label/1 rows`` for ``labels/<comp>.jsonl``.

    A withheld entity emits NO row (no label, no node, no slug — A-10 c);
    a review-pending organisation emits its typed ``not_yet_reviewed`` row
    (A-10 b — the state is visible, the label is not). Rows sort by
    (kind, label, entity_id) for byte-stable output.
    """
    by_comp: dict[str, list[dict[str, Any]]] = {}
    for eid, label in registry.items():
        if label.label_state == "withheld":
            continue
        for comp in entity_comps.get(eid) or {default_compartment}:
            by_comp.setdefault(comp, []).append(label.row())
    for rows in by_comp.values():
        rows.sort(key=lambda r: (r["kind"], r["label"] or "", r["entity_id"]))
    return by_comp


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
    subject_flags: Mapping[str, bool] | None = None,
    registry: Mapping[str, Any] | None = None,
    dossier_packets: Sequence[Mapping[str, Any]] | None = None,
    placement: _placement.PlacementEngine | None = None,
    cadence_sources: Mapping[str, Mapping[str, str]] | None = None,
    scheduler_drift: Mapping[str, bool] | None = None,
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

    ``dossier_packets`` (P32.17, SIG-DOS-001/002) are the reviewed
    ``sig.dossier-packet/1`` records the dossier tickets author; when supplied,
    the portfolio is composed through ``exports.research_dossier`` and emitted
    as ``web/research_dossiers.json``. Absent input emits no artifact (honest
    absence — the web getter reads a missing file as an empty portfolio).

    ``placement`` (P35.19 / JUR-02b, ADR-092 compute-on-read) is a
    :class:`exports.placement.PlacementEngine` built over the verified
    boundary pack + bound registry. When supplied, every site row gains the
    seven K4 §5.3 columns, withheld points lose their emitted geometry, the
    map draws only ``point_in_polygon`` placements, and the
    ``sig.placement-report/1`` quality report lands at
    ``web/placement.json``. When absent the export is byte-identical to the
    pre-placement posture — placement never silently defaults on.
    """
    raw = dict(raw or {})
    retrieval = date.fromisoformat(dataset.as_of[:10]) if dataset.as_of else date.today()

    if claims is None and raw.get("shaping_claims"):
        claims = parse_shaping_claims(raw["shaping_claims"])
    if entity_types is None:
        entity_types = {str(r[0]): str(r[1]) for r in (raw.get("subject_entities") or [])}
    if subject_flags is None:
        # P35.66: the emit-stamped residential-parcel flag per subject — read
        # off the subject_entities rows when they carry it (a 2-column row set
        # degrades to no flags — the candidate_asset type check still binds).
        subject_flags = {
            str(r[0]): bool(r[2]) for r in (raw.get("subject_entities") or []) if len(r) > 2
        }
    if claims is None:
        claims = _claims_from_dataset(dataset)

    source_names = {str(r[0]): str(r[1]) for r in (raw.get("source_names") or [])}

    # --- P34.19 (F-337, SIG-GOV-007): committed publication withdrawals -------
    # Every public surface derives from ``claims`` (the sites slice, record
    # claims, tiles, search) or from ``dataset.sites`` (map, dossiers, coverage,
    # analytics), so suppressing the committed withdrawal targets at BOTH seams
    # — before any surface is built — keeps every artifact consistent. The
    # dropped claims are recorded loudly in exclusions.json; the withdrawal is
    # the claim, never the agency's whole deployment record.
    claims, withdrawn_claims = _apply_publication_withdrawals(claims)
    withdrawn_entities = policy_withdrawals.withdrawn_entity_ids()
    if withdrawn_entities:
        dataset = replace(
            dataset,
            sites=tuple(s for s in dataset.sites if s.entity_id not in withdrawn_entities),
        )

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

    # --- P35.19: landed geometry-defect claims are placement inputs ---------
    # (P35.16 / PKG-06b; K4 §3.3 "consumes PKG-06b detectors if landed").
    defect_flags: dict[str, frozenset[str]] = {}
    if placement is not None:
        by_subject: dict[str, set[str]] = {}
        for row in raw.get("geometry_defects") or []:
            by_subject.setdefault(str(row[0]), set()).add(str(row[1]))
        defect_flags = {k: frozenset(v) for k, v in by_subject.items()}

    # --- P35.29 (K2 §3 / A-10): the shared label registry ----------------------
    # Built ONCE over the export's own snapshot before any surface is drawn —
    # sites rows, map assets, network nodes, dossier attribution and the
    # labels/<comp>.jsonl artifact all read this one derivation (L-1).
    label_registry, label_comps = _label_registry(
        raw, dataset, retrieval=retrieval, registry=registry
    )

    # --- the licence-critical path: sites sliced per (source, rights) -----------
    slices = _slice_sites(
        claims,
        entity_types,
        subject_flags=subject_flags,
        retrieval=retrieval,
        registry=registry,
        placement=placement,
        defect_flags=defect_flags,
        labels=label_registry,
    )
    site_rows, site_index, site_exclusions = (
        slices.rows_by_compartment,
        slices.index,
        slices.exclusions,
    )
    # Sites' published-slice licences join their label-row compartments (the
    # registry itself only saw label-input claims).
    for _eid, _lics in slices.licences_by_subject.items():
        for _lic in _lics:
            _comp = C.compartment_for_license(_lic, None, registry)
            if _comp:
                label_comps.setdefault(_eid, set()).add(str(_comp))
    # The map/dossier layer reads site.label — stamp the registry's label so
    # every surface shows the ONE derivation (a withheld/typed-absence site
    # keeps its shaping label; those subjects are excluded from surfaces).
    if label_registry:
        dataset = replace(
            dataset,
            sites=tuple(
                replace(
                    s,
                    label=(
                        label_registry[s.entity_id].label
                        if s.entity_id in label_registry and label_registry[s.entity_id].label
                        else s.label
                    ),
                )
                for s in dataset.sites
            ),
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

    # P35.19: the aggregate (cross-source) sites the map draws are placed by
    # the same engine + the same rule — a point the ruleset refused never
    # paints the map even at the aggregate level.
    map_placements: dict[str, _placement.PlacementResult] | None = None
    if placement is not None:
        all_claims_by_id = {c.claim_id: c for c in claims}
        map_inputs = [
            _placement.site_input(
                site,
                claims_by_id=all_claims_by_id,
                defect_flags=defect_flags.get(site.entity_id, frozenset()),
            )
            for site in dataset.sites
        ]
        map_placements = {r.record_id: r for r in placement.place_many(map_inputs)}

    # --- the ten P27.1-contract web surfaces ------------------------------------
    dossiers = _dossiers(
        dataset,
        dataset.as_of,
        belief,
        accountability_links=m_acct_links,
        coverage_rows=m_coverage,
        entity_label_by_id={
            eid: lbl.label for eid, lbl in label_registry.items() if lbl.label is not None
        },
    )
    surfaces: dict[str, Any] = {
        "dossier_index": _dossier_index(dossiers),
        "dossiers": dossiers,
        "map": _map_layer(
            dataset,
            resolved=resolved_counts,
            exclude=slices.refused_subjects | withdrawn_entities,
            placements=map_placements,
        ),
        # The network reads the materialized §29.3 edges (P28.2) when present, else the
        # compute-on-read shaping envelope (the honest fallback for an unmaterialized spine).
        # P35.30: both paths emit the additive D21 fields — dates/kinds, source names,
        # claim ids, currency — by joining the publishable claim reads and the
        # declared-independence lineage over the same shaping rows.
        "network": (
            _network_from_materialized(
                m_edges,
                source_names,
                label_registry,
                sharing_edges=dataset.sharing_edges,
                evidence=_network_evidence(raw, dataset.as_of),
            )
            if m_edges
            else _network(
                dataset,
                source_names,
                label_registry,
                evidence=_network_evidence(raw, dataset.as_of),
            )
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
    # P32.17 (SIG-DOS-001/002): reviewed dossier packets compose into the
    # research-dossier portfolio — a separate artifact class from the §39.2
    # inventory overviews above. Emitted only when packets are supplied (the
    # reviewed packets are authored per dossier ticket; an empty input emits no
    # artifact — honest absence, and the web getter treats a missing file as an
    # empty portfolio).
    if dossier_packets:
        from .research_dossier import build_portfolio, render_portfolio_json

        web_artifacts[f"{_WEB_DIR}/research_dossiers.json"] = render_portfolio_json(
            build_portfolio(dossier_packets)
        )

    # The map surface carries every published subject's own point + label, so it draws on
    # every site compartment's licence (ODbL OSM points beside CC-BY/CC0/… points) — its
    # label says so (ADR-106). The other surfaces carry SIG's aggregate framing (counts,
    # freshness, coverage) and stay SIG CC-BY-4.0.
    mapped = {
        site.entity_id
        for site in dataset.sites
        if site.entity_id not in slices.refused_subjects
        and site.entity_id not in withdrawn_entities
    }
    web_licenses = {
        f"{_WEB_DIR}/map.json": surface_license(
            {lic for sid in mapped for lic in slices.licences_by_subject.get(sid, ())}
        )
    }

    # P34.34a (G2 step-4, F5 PKG-03a): the §7 contribution-back leverage
    # record — web/leverage.json is a first-class web artifact of EVERY
    # spine export so `SIG_DATA_SOURCE=export` builds never hit a missing
    # file. The metric is the *recorded* ledger: when a recorded changeset
    # feed is bound to the export (raw["osm_changeset_feeds"] — the same
    # fixture-replay XML the jurisdiction path reads; no live poll, HG-08)
    # it is folded in; otherwise the zeroed ledger is the honest state — an
    # export that never measured never fabricates a count (§3.1), and the
    # record carries only hashtag + count + public changeset ids (no OSM
    # user data, Part VIII §0.7).
    leverage_path = f"{_WEB_DIR}/leverage.json"
    web_artifacts[leverage_path] = _web_bytes(_leverage_metric(raw))
    web_licenses[leverage_path] = _SIG_SPDX

    # --- the P31.14 analytics family (web/analytics/<name>.json) ---------------
    # The presentation analytics the surfaces render — density bins, centrality +
    # focus, the watch's decision point, per-surface provenance (W4..W0 tiers),
    # queue metadata — emitted with schema id / as_of / named denominator /
    # source compartments, licence-labelled like map.json (ADR-R9-ANALYTICS).
    web_compartments: dict[str, str] = {}
    # P35.36 (R11-K13-TX-08a): per-artifact schema ids + row/entity counts the
    # manifest carries for the ``sig.*`` row streams (``statements.jsonl``).
    web_schemas: dict[str, str] = {}
    web_counts: dict[str, tuple[int, int | None]] = {}
    for art in analytics.build_analytics(
        dataset,
        raw,
        licences_by_subject=slices.licences_by_subject,
        refused_subjects=slices.refused_subjects,
        materialized_edges=m_edges,
        materialized_site_runs=m_site_runs,
        ruleset_version=build_spec.ruleset_version,
        registry=registry,
        # P35.20b (ED-44): the density bins reconcile cell→jurisdiction against
        # the same placement run's scheme-qualified keys (P35.19) the map layer
        # already consumes; absent a run they key on the declared buckets.
        placements=map_placements,
    ):
        web_artifacts[art.path] = _web_bytes(art.payload)
        web_licenses[art.path] = art.license
        web_compartments[art.path] = art.compartment

    # P35.19 / JUR-02b (SIG-JUR-D05, K4 §3.4): the placement quality report —
    # the "Not yet placed" data — emitted only when a placement run happened;
    # absent input emits no artifact (the same honest-absence posture as
    # research_dossiers). SIG's own analytical expression → CC-BY-4.0.
    if placement is not None:
        placement_path = f"{_WEB_DIR}/placement.json"
        web_artifacts[placement_path] = _web_bytes(
            _placement.build_report(slices.placement_results, manifest=placement.pack_manifest)
        )
        web_licenses[placement_path] = _SIG_SPDX
        web_compartments[placement_path] = _WEB_COMPARTMENT

    # --- P32.13 (SIG-FIND-002): per-compartment `record_claims.jsonl` ---------
    # The claim/evidence anchors behind every published site — filed under the
    # claim's OWN licence compartment with its checksum in the manifest.
    for comp, payload in sorted(
        _record_claims(
            claims,
            slices,
            raw.get("evidence_bindings") or [],
            retrieval=retrieval,
            registry=registry,
            materialized_edges=m_edges,
        ).items()
    ):
        path = f"{comp}/record_claims.jsonl"
        web_artifacts[path] = b"".join(canonical_json(r) for r in payload["rows"])
        web_licenses[path] = str(payload["license"])
        web_compartments[path] = comp

    # --- P35.36 (R11-K13-TX-08a / J3 §5.1–5.2, SIG-TRANSP-011): per-compartment
    # `statements.jsonl` — the sig.statement/1 stream the release's claim index
    # and every <ProvenancePanel> consumer reads. One file per licence
    # compartment (the _record_claims placement — an ODbL claim never lands in
    # a CC-BY statements file); the committed source registry is the
    # homepage-fallback input for unbound claims' upstream reference.
    stmt_source_registry = load_source_registry()
    for comp, payload in sorted(
        _statements(
            claims,
            slices,
            raw.get("evidence_bindings") or [],
            raw.get("claim_binding_detail") or [],
            raw.get("claim_provenance") or [],
            retrieval=retrieval,
            registry=registry,
            source_registry=stmt_source_registry,
            lane_by_source=_claim_lane_map(raw, stmt_source_registry),
            materialized_edges=m_edges,
            materialized_contradictions=m_contradictions,
        ).items()
    ):
        path = f"{comp}/statements.jsonl"
        web_artifacts[path] = b"".join(canonical_json(r) for r in payload["rows"])
        web_licenses[path] = str(payload["license"])
        web_compartments[path] = comp
        web_schemas[path] = _stmt.STATEMENT_SCHEMA
        web_counts[path] = (
            len(payload["rows"]),
            len({r["entity_id"] for r in payload["rows"]}),
        )

    # --- P34.19 (F-403, ADR-183): express-terms disclosure ----------------------
    # Each express-terms source the operator chose to keep public discloses its
    # captured terms verbatim + the accepted publication basis: file-level in a
    # per-compartment ``ATTRIBUTION.json`` (P34.21a generalises the mechanism to
    # every compartment file) and machine-readable in ``web/terms_disclosure.json``
    # for P34.17's interim sources-and-licences page. Row counts are computed
    # from THIS export's slices — never copied from the acceptance narrative.
    comp_licenses = {pt.compartment: pt.license for pt in bundle.placed}

    # --- P35.29 (K2 §3/L-1): the ``sig.entity-label/1`` registry artifact -----
    # One derivation for every publishable entity, filed per the compartment
    # its label inputs license to — the single registry every downstream
    # consumer (API, pages, graph, typeahead) reads instead of re-deriving.
    for comp, label_rows in sorted(
        _label_artifacts(
            label_registry,
            label_comps,
            default_compartment=sig_compartment,
        ).items()
    ):
        path = f"labels/{comp}.jsonl"
        web_artifacts[path] = b"".join(canonical_json(r) for r in label_rows)
        web_licenses[path] = str(comp_licenses.get(comp, _SIG_SPDX))
        web_compartments[path] = comp

    disclosure = _terms_disclosure_payload(
        slices.rows_by_compartment,
        as_of=dataset.as_of,
        generated_at=generated_at,
    )
    if disclosure is not None:
        path = f"{_WEB_DIR}/terms_disclosure.json"
        web_artifacts[path] = _web_bytes(disclosure)
        web_licenses[path] = _SIG_SPDX
        web_compartments[path] = _WEB_COMPARTMENT

    # --- P35.37 (R11-K13-TX-09, SIG-TRANSP-013, J3 §5.4): the figure-evidence
    # artifacts the <Figure> pointer contract resolves into -----------------
    # ``web/sources.json`` — the ``sig.source-licence-table/1`` artifact the
    # /sources/ page's per-source row-count figures point at. It is the same
    # aggregation the web data layer would re-derive from the compartment
    # row streams — emitted once so the pointer lands on manifest-listed
    # bytes and the page can never drift from the downloads.
    sources_table = source_licences.source_licence_table(
        slices.rows_by_compartment, slices.index, registry=registry
    )
    sources_path = f"{_WEB_DIR}/sources.json"
    web_artifacts[sources_path] = _web_bytes(sources_table)
    web_licenses[sources_path] = _SIG_SPDX
    web_compartments[sources_path] = _WEB_COMPARTMENT
    web_schemas[sources_path] = source_licences.SCHEMA
    web_counts[sources_path] = (len(sources_table["rows"]), None)

    # ``web/evaluation.json`` — the ``sig.resolution-eval/1`` record (DR-C3-03):
    # the numbers that measure SIG's own resolver (§32.5, SIG-METRIC-008b) are a
    # published release artifact — emitted verbatim from the committed record,
    # never a hard-coded page constant.
    eval_path = f"{_WEB_DIR}/evaluation.json"
    web_artifacts[eval_path] = (
        Path(__file__).resolve().parent / "data" / "resolution_eval.json"
    ).read_bytes()
    web_licenses[eval_path] = _SIG_SPDX
    web_compartments[eval_path] = _WEB_COMPARTMENT
    web_schemas[eval_path] = "sig.resolution-eval/1"

    for comp, rows in sorted(slices.rows_by_compartment.items()):
        comp_license = str(comp_licenses.get(comp, _SIG_SPDX))
        payload = _compartment_attribution(
            comp,
            rows,
            index=slices.index,
            license_id=comp_license,
            license_url=policy_license_url(comp_license, registry),
            source_names=source_names,
            registry=registry,
            generated_at=generated_at,
        )
        if payload is None:
            continue
        path = f"{comp}/ATTRIBUTION.json"
        web_artifacts[path] = _web_bytes(payload)
        web_licenses[path] = comp_license
        web_compartments[path] = comp

    # --- P34.21b (E2-12): the dated attribution-correction record ------------
    # The /sources/ note renders only when THIS export's effective rights
    # resolve through ADR-194 correction decisions — absent otherwise (a
    # pre-backfill export shows no note, never a fabricated correction).
    corrections = _attribution_corrections_payload(
        claims, as_of=dataset.as_of, generated_at=generated_at
    )
    if corrections is not None:
        path = f"{_WEB_DIR}/attribution_corrections.json"
        web_artifacts[path] = _web_bytes(corrections)
        web_licenses[path] = _SIG_SPDX
        web_compartments[path] = _WEB_COMPARTMENT

    # --- P35.33 (J3 §3.1–3.2 + K9 C-4…C-7 + K10 C-13): the transparency
    # run/capture/issue release artifacts under transparency/. The
    # evaluation instant is the release as-of — a release-bound value,
    # never the reader's clock (K9 C-4's two-clocks rule).
    transparency_at = (
        _parse_instant(str(getattr(dataset, "as_of", "") or ""))
        or _parse_instant(generated_at)
        or datetime.now(UTC)
    )
    # P35.35: the source ids this release's published site records name —
    # the ``with site records`` attribute K9 C-1 counts.
    site_source_ids: set[str] = set()
    for site in dataset.sites:
        site_source_ids.update(site.source_ids)
    for path, data in emit_transparency_artifacts(
        raw,
        claims=list(claims or ()),
        cadence_sources=cadence_sources,
        scheduler_drift=scheduler_drift,
        site_source_ids=site_source_ids,
        at=transparency_at,
    ).items():
        web_artifacts[path] = data
        web_licenses[path] = _SIG_SPDX
        web_compartments[path] = _META_COMPARTMENT

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
        rendered, renderer = _render_tiles(
            pt.compartment,
            geojson_bytes,
            pt.license,
            attribution=_compartment_tile_attribution(
                slices.rows_by_compartment.get(pt.compartment, []), slices.index
            ),
        )
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
        # P34.19 (F-337, SIG-GOV-007): the committed publication-withdrawal
        # targets dropped before any surface was built — recorded loudly, one
        # row per suppressed claim.
        "withdrawn": withdrawn_claims,
        "totals": {
            "refused_slices": len(site_exclusions),
            "refused_rows": sum(int(e["rows"]) for e in site_exclusions),
            "withdrawn_claims": len(withdrawn_claims),
        },
    }

    manifest = _extended_manifest(
        bundle,
        web_artifacts=web_artifacts,
        tile_artifacts=tile_artifacts,
        web_licenses=web_licenses,
        web_compartments=web_compartments,
        web_schemas=web_schemas,
        web_counts=web_counts,
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


def _render_tiles(
    compartment: str,
    geojson_bytes: bytes,
    license_id: str,
    *,
    attribution: str | None = None,
) -> tuple[bytes, str]:
    """Render one compartment's sites.geojson → PMTiles bytes (+ renderer name).

    Thin alias over :func:`exports.tiles.render_compartment_sites_pmtiles` (the shared
    per-compartment renderer — ODbL keeps its OSM notice, slimmed render properties,
    z0–z14 via tippecanoe or the pure-Python encoder). ``attribution`` is the drawn
    sources' own credit (P34.21a / E2-12); absent it, the licence-level fallback stands.
    """
    return render_compartment_sites_pmtiles(
        compartment, geojson_bytes, license_id, attribution=attribution
    )


def _extended_manifest(
    bundle: Bundle,
    *,
    web_artifacts: Mapping[str, bytes],
    tile_artifacts: Sequence[tuple[str, str, str, bytes]],
    provenance: bytes,
    exclusions: Mapping[str, Any],
    web_licenses: Mapping[str, str] | None = None,
    web_compartments: Mapping[str, str] | None = None,
    web_schemas: Mapping[str, str] | None = None,
    web_counts: Mapping[str, tuple[int, int | None]] | None = None,
) -> Manifest:
    """Extend the bundle manifest with the web JSONs, tiles, provenance, exclusions.

    Every added artifact carries its checksum + compartment + computed licence, so a
    consumer can verify integrity and know the governing licence of each file
    (SIG-EXPORT-001/006). P35.36: ``web_schemas`` records the emitted ``sig.*``
    row-schema id (``sig.statement/1`` on the statements files) and
    ``web_counts`` the ``(row_count, distinct_entities)`` pair where the
    artifact is a row stream.
    """
    # Each tile is labelled with the compartment its sites were placed in (and that
    # compartment's licence) — a CC-BY-SA tile is never filed under `sig_graph` (ADR-106).
    tiles = {path: (comp, lic) for path, comp, lic, _ in tile_artifacts}
    labels = dict(web_licenses or {})
    compartments_for = dict(web_compartments or {})
    schemas = dict(web_schemas or {})
    counts = dict(web_counts or {})
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
            row_count, distinct_entities = counts.get(path, (None, None))
            artifacts.append(
                Artifact.of(
                    name=Path(path).name,
                    path=path,
                    media_type=(
                        "application/x-ndjson" if path.endswith(".jsonl") else "application/json"
                    ),
                    compartment=compartments_for.get(path, _WEB_COMPARTMENT),
                    license=labels.get(path, _SIG_SPDX),
                    data=data,
                    row_count=row_count,
                    distinct_entities=distinct_entities,
                    schema=schemas.get(path),
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
    dossier_packets: Sequence[Mapping[str, Any]] | None = None,
    generated_at: datetime | None = None,
    environment: str | None = None,
    replay: str | None = None,
    materialize_run: str | None = None,
    restore_point: str | None = None,
    boundary_pack: str | Path | None = None,
    jurisdiction_registry: str | Path | None = None,
    boundary_spec: str | Path | None = None,
) -> SpineExport:
    """Execute the read-only reads and assemble the national export.

    One ``REPEATABLE READ READ ONLY`` snapshot covers BOTH shaping and the
    supplementary export reads, so every emitted artifact describes the same spine
    state. The session is put in read-only mode first — no statement can mutate the
    append-only spine (§16). When the caller already holds an open transaction (the
    test seam) the reads run inside it unchanged.

    P35.12 / SIG-REL-003 clock rules: ``generated_at`` is T0 — read exactly
    once here (injected by tests/replay); the default ``as_of`` is literally
    that same instant, and a typed ``as_of`` later than T0 refuses before
    any DB read (a future snapshot can never be cut). ``environment`` /
    ``replay`` ride the :class:`BuildSpec` into the export manifest (the
    release builder reads them back for the v2 descriptor); ``replay``
    marks a Class-S rebuild of a historical snapshot.

    P35.19 / JUR-02b (ADR-092 compute-on-read): ``boundary_pack`` +
    ``jurisdiction_registry`` stage the verified placement inputs — a
    ``sig.boundary-pack/1`` directory and the ``sig.jurisdiction-registry/1``
    document derived from it. Both must be given together; the engine
    verifies the pack and cross-binds ``boundaries_root`` + vintages before
    any placement runs, and a failure refuses the export. Absent → no
    placement columns and no ``web/placement.json`` — honest absence, never
    a silently-half-configured placement.
    """
    from .release_identity import ClockGuardError, parse_instant
    from .shaping import (
        _queries_for,
        build_shaped_dataset,
        fetch_shaping_raw,
    )
    from .versioning import code_commit, default_resolver_version

    # T0, read exactly once (G3 §3.3 rule 7): the build instant, the default
    # as-of, and every emitted stamp share it.
    t0 = generated_at or datetime.now(UTC)
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=UTC)
    t0 = t0.astimezone(UTC)
    generated_at_s = t0.strftime("%Y-%m-%dT%H:%M:%SZ")
    as_of = as_of or generated_at_s
    as_of_dt = parse_instant(as_of)
    if as_of_dt is None:
        raise ClockGuardError(f"--as-of {as_of!r} is not an ISO-8601 date or instant")
    if as_of_dt > t0:
        raise ClockGuardError(
            f"--as-of {as_of!r} is later than the build instant {generated_at_s} — "
            "an export can never name a future snapshot (SIG-REL-003)"
        )

    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")
    status = getattr(getattr(conn, "info", None), "transaction_status", None)
    snapshot = status is None or int(status) == 0
    if snapshot:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    sqitch_head: str | None = None
    try:
        cur.execute("SELECT to_regclass('rights_decision') IS NOT NULL")
        has_row = cur.fetchone()
        has_decisions = bool(has_row and has_row[0])
        # P35.25 (SIG-CONF-014): the claim_lineage record — absent on a
        # pre-P35.25 spine, where independence_class projects NULL (undeclared).
        cur.execute("SELECT to_regclass('claim_lineage') IS NOT NULL")
        has_row = cur.fetchone()
        shaping_raw = fetch_shaping_raw(
            cur,
            _queries_for(has_decisions, has_lineage=bool(has_row and has_row[0])),
            belief=belief,
        )
        export_raw = fetch_export_raw(cur, belief=belief)
        # The materialized graph (P28.1-P28.4, ADR-101), read inside the SAME snapshot so
        # every emitted artifact describes one spine state; empty/absent tables degrade to []
        # (the honest state until the hosted materialization runs, D-R6.5-SURFACE).
        export_raw.update(
            {k: resolve_public_text(v) for k, v in fetch_materialized_graph(cur).items()}
        )
        # The sqitch head inside the SAME snapshot (SIG-REL-001
        # snapshot.sqitch_head — the schema state the export ran against);
        # an absent sqitch schema degrades to None, honestly recorded.
        cur.execute("SELECT to_regclass('sqitch.changes') IS NOT NULL")
        has_sqitch = cur.fetchone()
        if has_sqitch and has_sqitch[0]:
            cur.execute("SELECT change FROM sqitch.changes ORDER BY committed_at DESC LIMIT 1")
            row = cur.fetchone()
            sqitch_head = str(row[0]) if row and row[0] else None
    finally:
        if snapshot:
            cur.execute("ROLLBACK")

    dataset = build_shaped_dataset(
        shaping_raw,
        as_of=as_of,
        generated_at=generated_at_s,
        spine_label=spine_label,
        note=note,
    )
    claims = parse_shaping_claims(shaping_raw.get("shaping_claims") or [])
    subject_rows = list(shaping_raw.get("subject_entities") or [])
    entity_types = {str(r[0]): str(r[1]) for r in subject_rows}
    # P35.66: the emit-stamped residential-parcel flag rides the subject rows.
    subject_flags = {str(r[0]): bool(r[2]) for r in subject_rows if len(r) > 2}
    # ``fetch_export_raw`` already read source_registry names into
    # ``export_raw['source_names']`` (compat-guarded); the surface builders consume it.

    # P35.19: the placement engine is constructed HERE — before the bundle is
    # assembled — so an unverified/inconsistent pack refuses the export
    # outright rather than emitting half-placed surfaces. Constructing it
    # touches nothing but its own in-memory DuckDB; the spine snapshot above
    # is already closed.
    engine: _placement.PlacementEngine | None = None
    if boundary_pack is not None or jurisdiction_registry is not None:
        if boundary_pack is None or jurisdiction_registry is None:
            raise _placement.PlacementError(
                "boundary_pack and jurisdiction_registry must be given "
                "together — placement refuses a half-staged input set"
            )
        engine = _placement.PlacementEngine(
            boundary_pack, jurisdiction_registry, spec_path=boundary_spec
        )

    if build_spec is None:
        as_of_snapshot = date.fromisoformat(as_of[:10]) if as_of else date.today()
        as_of_belief = belief.date() if belief is not None else as_of_snapshot
        build_spec = BuildSpec(
            as_of_snapshot=as_of_snapshot,
            as_of_belief=as_of_belief,
            ruleset_version=ruleset_version,
            # SIG-REL-014 (G3 §3.2 ★): the resolver's code identity — the
            # resolution package version + the tree's commit — never the
            # exports placeholder the pre-REL-10 manifests carried.
            resolver_version=resolver_version or default_resolver_version(),
            dataset_slug=dataset_slug,
            # SIG-REL-001 (P35.12): the full instants, watermark, commit and
            # declared environment/replay — the export-id key inputs and the
            # descriptor snapshot block's source.
            as_of_snapshot_instant=as_of,
            as_of_belief_instant=(
                (belief if belief.tzinfo is not None else belief.replace(tzinfo=UTC))
                .astimezone(UTC)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
                if belief is not None
                else generated_at_s
            ),
            belief_pinned=belief is not None,
            spine_watermark=str(shaping_raw.get("spine_watermark") or "") or None,
            code_commit=code_commit() or None,
            environment=environment,
            replay=replay,
            materialize_run=materialize_run,
            sqitch_head=sqitch_head,
            restore_point=restore_point,
        )

    return build_spine_export(
        dataset,
        export_raw,
        build_spec=build_spec,
        generated_at=generated_at_s,
        note=note,
        belief=belief,
        claims=claims,
        entity_types=entity_types,
        subject_flags=subject_flags,
        dossier_packets=dossier_packets,
        placement=engine,
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
