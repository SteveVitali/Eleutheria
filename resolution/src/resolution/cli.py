# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `resolution` stage (SIG-ENG-013).

Sub-commands expose the identity substrate (§11.1-11.3, §14):

* ``geoid CODE LEVEL``  — validate a Census GEOID against its level (SIG-IDENT-005).
* ``agency-name NAME``  — parse a colon-delimited agency name into parent + unit (SIG-IDENT-011).
* ``relation-types``    — list the seven OrganizationRelation types (SIG-IDENT-016).
* ``normalize NAME``    — versioned organisation-name normalisation (SIG-IDENT-022).
* ``ori VALUE``         — validate an ORI9 and report the civil-ORI flag (SIG-IDENT-002/003).
* ``scheme CLASS``      — the canonical identifier scheme for a class (SIG-IDENT-001).
* ``slug SLUG``         — parse a vendor-portal slug into a name hypothesis (SIG-IDENT-015).
* ``er-match PATH``     — score records (a JSON array) with the probabilistic matcher and
  print the tier-4/5 PROPOSED proposals with weights (SIG-IDENT-021/025).
* ``block-size PATH KEYS`` — size an equijoin blocking rule over records and report
  whether it is accepted or rejected (SIG-IDENT-023).
* ``review enqueue QUEUE PATH`` — score a records file with the matcher and enqueue the
  tier-4/5 PROPOSED proposals into a JSON queue file (SIG-IDENT-020).
* ``review list QUEUE`` — list the pending proposals with the confidence explanation
  surfaced inline (SIG-IDENT-025).
* ``review show QUEUE ID`` — the full confidence explanation for one proposal.
* ``review decide QUEUE ID accept|reject --reviewer R`` — record a human decision,
  logging model/prompt provenance for model-assisted items (SIG-IDENT-026).
* ``match --dsn … --jurisdiction ID`` — read org candidates from the PostgreSQL
  claim spine, score them with the probabilistic matcher, and enqueue the tier-4/5
  PROPOSED proposals as append-only ``review_item`` rows (P19.5, SIG-IDENT-021/025).
* ``review {list,show,decide,enqueue} --dsn …`` — the same curation surface backed
  by PostgreSQL (``PgReviewQueue``) instead of a JSON queue file; ``decide --dsn``
  appends exactly one ``review_decision`` row per call (history on repeat).
* ``camera-sites --dsn … [--role R] [--dry-run]`` — geospatial camera-site entity
  resolution (P30.2b, ADR-105): block → assess → measure the tiers on the committed
  gold holdout → auto-write only tiers at/above the published floor → materialize the
  same_as decisions + review proposals append-only (+0 on an unchanged re-run). Prints
  one JSON summary (M, N, dedup ratio, per-tier precision, demotions, alerts).
* ``identity-triage --dsn … [--apply]`` — the P31.3 duplicate-identifier triage
  (ADR-110): list every ``(scheme, value)`` shared by more than one entity, with its
  evidence and recorded decision (read-only; exit 1 while any pair is undecided).
  ``--apply`` appends the committed same_as/distinct decisions through the review
  queue (+0 on re-run).
* ``partner-name-audit --dsn …`` — the P32.3 dry-run impact report (ADR-122):
  every legacy ``sig.org.name`` partner key, its asserting sources/predicates,
  and the scoped ``sig.org.name_scoped`` keys it decomposes into (read-only).

With no sub-command it prints help and exits 0 (the SIG-ENG-013 convention).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any

from . import __version__
from .blocking import BlockingRule, BlockingRuleRejected, size_blocking_rule, validate_blocking_rule
from .crosswalk import canonical_scheme_for
from .geoid import GeoidValidationError, validate_geoid
from .identity import parse_agency_name
from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name
from .ori import OriValidationError, is_civil_ori, validate_ori
from .probabilistic import ProbabilisticMatcher
from .review_pg import PgReviewQueue
from .review_queue import (
    ReviewQueue,
    review_item_from_match,
    surface_confidence_explanation,
)
from .slug import parse_slug
from .temporal_identity import OrganizationRelationType


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `resolution` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-resolution",
        description="SIG resolution stage: the identity registries (§11.1-11.3, §14).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    geoid = sub.add_parser("geoid", help="validate a Census GEOID against its level")
    geoid.add_argument("code")
    geoid.add_argument("level")

    agency = sub.add_parser("agency-name", help="parse a colon-delimited agency name")
    agency.add_argument("name")

    sub.add_parser("relation-types", help="list the seven OrganizationRelation types")

    normalize = sub.add_parser("normalize", help="normalise an organisation name (versioned)")
    normalize.add_argument("name")

    ori = sub.add_parser("ori", help="validate an ORI9 and report the civil-ORI flag")
    ori.add_argument("value")

    scheme = sub.add_parser("scheme", help="the canonical identifier scheme for a class")
    scheme.add_argument("organization_class")

    slug = sub.add_parser("slug", help="parse a vendor-portal slug into a name hypothesis")
    slug.add_argument("slug")

    er_match = sub.add_parser("er-match", help="score records and print PROPOSED proposals")
    er_match.add_argument("path", help="a JSON file: an array of record objects")

    block_size = sub.add_parser("block-size", help="size an equijoin blocking rule")
    block_size.add_argument("path", help="a JSON file: an array of record objects")
    block_size.add_argument("keys", help="comma-separated equijoin key columns")

    match = sub.add_parser(
        "match",
        help="read org candidates from the PG spine, score, and enqueue PROPOSED proposals",
    )
    match.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    match.add_argument(
        "--jurisdiction",
        default=None,
        help="jurisdiction token to filter candidate orgs by (e.g. okc); on identifiers",
    )
    match.add_argument("--role", default=None, help="optional read role to SET ROLE to")

    review = sub.add_parser("review", help="the internal review queue / curation surface")
    review_sub = review.add_subparsers(dest="review_command")

    enqueue = review_sub.add_parser("enqueue", help="score records and enqueue PROPOSED matches")
    enqueue.add_argument("queue", nargs="?", help="the JSON queue file (created if absent)")
    enqueue.add_argument("path", help="a JSON file: an array of record objects")
    enqueue.add_argument("--dsn", default=None, help="use PG (PgReviewQueue), not a file")

    review_list = review_sub.add_parser("list", help="list pending proposals with confidence")
    review_list.add_argument("queue", nargs="?", help="the JSON queue file")
    review_list.add_argument("--dsn", default=None, help="use PG (PgReviewQueue), not a file")
    review_list.add_argument(
        "--prefix",
        default=None,
        action="append",
        help="(PG) item_id prefix filter, repeatable — e.g. er_match:camera_site:",
    )
    review_list.add_argument(
        "--tier", type=int, default=None, help="(PG) payload match-tier filter (e.g. 4)"
    )
    review_list.add_argument(
        "--bucket",
        default=None,
        help="(PG) stratum filter (1g/3g/4g/5g/soft-conflict/disputed/other)",
    )
    review_list.add_argument(
        "--campaign", default=None, help="(PG) restrict to a drawn campaign's items"
    )
    review_list.add_argument("--limit", type=int, default=None, help="(PG) cap the listing")

    show = review_sub.add_parser("show", help="show one proposal's confidence explanation")
    show.add_argument("queue", nargs="?", help="the JSON queue file")
    show.add_argument("item_id", help="the review item id")
    show.add_argument("--dsn", default=None, help="use PG (PgReviewQueue), not a file")

    decide = review_sub.add_parser("decide", help="record a human accept/reject decision")
    decide.add_argument("queue", nargs="?", help="the JSON queue file")
    decide.add_argument("item_id", help="the review item id")
    decide.add_argument("decision", choices=("accept", "reject"))
    decide.add_argument("--reviewer", required=True, help="the human reviewer")
    decide.add_argument("--rationale", default=None, help="an optional note / review rationale")
    decide.add_argument("--dsn", default=None, help="use PG (PgReviewQueue), not a file")

    # P31.10: the stratified campaign sampler + the offline JSONL path. The
    # sampler draws a seeded, reproducible sample of PENDING camera-site items
    # across strata (1g/3g/4g/5g + soft-conflict + disputed) and — only with
    # --campaign — tags it append-only in review_campaign/_item (a re-draw of
    # the same design under the same id is +0; a different design under a taken
    # id is refused). Default --n is the §6 Q11 ~400-pair Round-10 design; this
    # command PREPARES a campaign, it never runs one (no decisions exist here).
    sample = review_sub.add_parser(
        "sample",
        help="draw a stratified, seeded sample of pending camera-site items "
        "(P31.10; --campaign tags it append-only for the Round-10 review)",
    )
    sample.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    sample.add_argument("--role", default=None, help="optional role to SET ROLE to")
    sample.add_argument(
        "--strata",
        default=None,
        help="comma list of stratum[:count] (default: all of "
        "1g,3g,4g,5g,soft-conflict,disputed; 'name:all' draws a whole stratum)",
    )
    sample.add_argument(
        "--n",
        type=int,
        default=400,
        help="unique-item target (default 400 — the §6 Q11 Round-10 design)",
    )
    sample.add_argument(
        "--seed", default="0", help="the sample seed (reproducible for a fixed seed)"
    )
    sample.add_argument(
        "--campaign",
        default=None,
        help="campaign id to materialize append-only (omit to print a dry run)",
    )
    sample.add_argument(
        "--purpose",
        default="prepared for Round 10 (P31.10 tooling; the human review campaign is Round 10)",
        help="the campaign's recorded purpose label",
    )
    sample.add_argument(
        "--created-by",
        default="sig-resolution review sample",
        help="the tool/engineering actor recorded on the campaign row (never a person)",
    )
    sample.add_argument(
        "--dry-run",
        action="store_true",
        help="print the draw summary without writing any campaign rows",
    )

    export = review_sub.add_parser(
        "export",
        help="export pending review items as a JSONL labelling session (P31.10)",
    )
    export.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    export.add_argument("--role", default=None, help="optional role to SET ROLE to")
    export.add_argument("--campaign", default=None, help="export a drawn campaign's items")
    export.add_argument(
        "--prefix",
        default=None,
        action="append",
        help="item_id prefix filter, repeatable (default: the camera-site families)",
    )
    export.add_argument("--tier", type=int, default=None, help="payload match-tier filter")
    export.add_argument("--bucket", default=None, help="stratum filter")
    export.add_argument("--out", default=None, help="the JSONL output path (default: stdout)")

    imp = review_sub.add_parser(
        "import",
        help="import a JSONL labelling session as append-only decisions (P31.10)",
    )
    imp.add_argument("path", help="the JSONL labelling file")
    imp.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    imp.add_argument("--role", default=None, help="optional role to SET ROLE to")
    imp.add_argument(
        "--reviewer",
        required=True,
        help="the pseudonymous reviewer handle recorded on every appended decision",
    )

    # -- eval — the P32.9 independent blinded human-evaluation campaign surface
    # (ADR-128). A different channel from `review`: reference labels answer
    # "same defined object", they are never operational accept/reject
    # decisions, and sealed_final labels stay invisible to clustering and
    # model-development views until a custodian-recorded release. This surface
    # only PREPARES campaigns and records labels a human produced elsewhere —
    # it never runs a campaign, recruits a reviewer, or authors a label.
    ev = sub.add_parser(
        "eval",
        help="independent blinded human-evaluation campaigns (P32.9, ADR-128; "
        "prepare/record tooling only — never runs a human campaign)",
    )
    ev_sub = ev.add_subparsers(dest="eval_command")

    ev_frame = ev_sub.add_parser(
        "frame",
        help="build a camera-site frame JSONL from pending review items (read-only)",
    )
    ev_frame.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_frame.add_argument("--role", default=None, help="optional role to SET ROLE to")
    ev_frame.add_argument("--limit", type=int, default=None, help="frame size cap")
    ev_frame.add_argument("--out", default=None, help="output JSONL path (default: stdout)")

    ev_prep = ev_sub.add_parser(
        "prepare",
        help="preregister a campaign and draw the disjoint, seeded sample "
        "(immutable campaign + manifest + sample rows)",
    )
    ev_prep.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_prep.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_prep.add_argument("--campaign-id", required=True)
    ev_prep.add_argument("--purpose", required=True)
    ev_prep.add_argument("--protocol-digest", required=True)
    ev_prep.add_argument("--frame-snapshot", required=True)
    ev_prep.add_argument("--ruleset-digest", required=True)
    ev_prep.add_argument("--seed", required=True)
    ev_prep.add_argument(
        "--frame-jsonl",
        required=True,
        help="the frame JSONL (rows from `eval frame` or a caller-built frame)",
    )
    ev_prep.add_argument(
        "--design",
        default=None,
        help="optional JSON file {group_spec,sample_spec,target_population,rubric_version}",
    )
    ev_prep.add_argument(
        "--created-by",
        default="sig-resolution eval prepare",
        help="the tool/engineering actor recorded on the campaign (never a person)",
    )
    ev_prep.add_argument(
        "--dry-run",
        action="store_true",
        help="compute + print the draw without writing any rows",
    )

    ev_pkt = ev_sub.add_parser(
        "packets",
        help="build + persist the blinded reviewer packets for a campaign's samples",
    )
    ev_pkt.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_pkt.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_pkt.add_argument("--campaign-id", required=True)
    ev_pkt.add_argument(
        "--from-spine",
        action="store_true",
        help="read the two observations per sample off the spine (camera-site pairs)",
    )
    ev_pkt.add_argument(
        "--evidence-jsonl",
        default=None,
        help="JSONL {sample_id|pair_id, left:{…}, right:{…}} for non-spine frames",
    )

    ev_assign = ev_sub.add_parser(
        "assign", help="record reviewer × sample × pass assignments (append-only)"
    )
    ev_assign.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_assign.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_assign.add_argument("--campaign-id", required=True)
    ev_assign.add_argument("--reviewer", required=True, help="pseudonymous reviewer handle")
    ev_assign.add_argument("--pass", dest="pass_no", type=int, required=True, choices=(1, 2))
    ev_assign.add_argument(
        "--samples",
        default="all",
        help="'all' or a comma list of sample ids (default: all of the campaign)",
    )
    ev_assign.add_argument(
        "--assigned-by",
        default="sig-resolution eval assign",
        help="the tooling actor (never a person)",
    )

    ev_status = ev_sub.add_parser("status", help="campaign state + counts")
    ev_status.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_status.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_status.add_argument("--campaign-id", required=True)

    ev_export = ev_sub.add_parser(
        "export",
        help="export one reviewer's blinded workbook (JSONL; packet payloads only)",
    )
    ev_export.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_export.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_export.add_argument("--campaign-id", required=True)
    ev_export.add_argument("--reviewer", required=True)
    ev_export.add_argument("--pass", dest="pass_no", type=int, default=1, choices=(1, 2))
    ev_export.add_argument("--out", default=None, help="output JSONL path (default: stdout)")

    ev_attest = ev_sub.add_parser("attest", help="record a human-attestation event (append-only)")
    ev_attest.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_attest.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_attest.add_argument("--campaign-id", default=None)
    ev_attest.add_argument("--reviewer", required=True)
    ev_attest.add_argument(
        "--kind",
        required=True,
        choices=(
            "human_identity",
            "training_complete",
            "conflict_declaration",
            "blinding_breach",
            "withdrawn",
        ),
    )
    ev_attest.add_argument("--detail", default="{}", help="JSON detail object")
    ev_attest.add_argument(
        "--recorded-by", default="sig-resolution eval attest", help="the recording actor"
    )

    ev_import = ev_sub.add_parser(
        "import-labels",
        help="append reviewer labels from a filled workbook JSONL "
        "(as sig_eval_reviewer — never as admin/materialize)",
    )
    ev_import.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_import.add_argument("--role", default="sig_eval_reviewer", help="role to SET ROLE to")
    ev_import.add_argument("--campaign-id", required=True)
    ev_import.add_argument("--reviewer", required=True, help="the label-owning reviewer")
    ev_import.add_argument(
        "--round",
        dest="label_round",
        default="independent_1",
        choices=("independent_1", "independent_2", "repeat"),
    )
    ev_import.add_argument("--attestation", required=True, help="the reviewer's attestation_id")
    ev_import.add_argument("--rubric-version", default="eval-rubric/1")
    ev_import.add_argument("path", help="the filled workbook JSONL")

    ev_adj = ev_sub.add_parser(
        "adjudicate",
        help="record an adjudication (custodian only; disagreements stay unresolved-able)",
    )
    ev_adj.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_adj.add_argument("--role", default="sig_eval_custodian", help="role to SET ROLE to")
    ev_adj.add_argument("--campaign-id", required=True)
    ev_adj.add_argument("--sample-id", required=True)
    ev_adj.add_argument("--adjudicator", required=True, help="pseudonymous adjudicator")
    ev_adj.add_argument("--phase", default="resolution", choices=("independent", "resolution"))
    ev_adj.add_argument(
        "--label",
        required=True,
        choices=("same", "different", "insufficient_evidence", "unresolved"),
    )
    ev_adj.add_argument("--reason", required=True)
    ev_adj.add_argument("--evidence-refs", default="[]", help="JSON array")

    ev_unseal = ev_sub.add_parser(
        "unseal",
        help="record the authorized unsealing decision (custodian only)",
    )
    ev_unseal.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_unseal.add_argument("--role", default="sig_eval_custodian", help="role to SET ROLE to")
    ev_unseal.add_argument("--campaign-id", required=True)
    ev_unseal.add_argument(
        "--scope", required=True, choices=("development_only", "final", "operational")
    )
    ev_unseal.add_argument("--authorized-by", required=True)
    ev_unseal.add_argument("--detail", default="{}", help="JSON detail object")

    ev_verify = ev_sub.add_parser(
        "verify", help="recompute the campaign manifest over live rows (tamper check)"
    )
    ev_verify.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_verify.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_verify.add_argument("--campaign-id", required=True)

    ev_wm = ev_sub.add_parser("watermark", help="print the campaign's chained label watermark")
    ev_wm.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_wm.add_argument("--role", default="sig_eval_custodian", help="role to SET ROLE to")
    ev_wm.add_argument("--campaign-id", required=True)

    ev_gate = ev_sub.add_parser(
        "gate",
        help="P32.10: run the design-aware SHADOW evaluation over a campaign's "
        "released labels and print the confidence-gate report (applies nothing)",
    )
    ev_gate.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    ev_gate.add_argument("--role", default="sig_eval_admin", help="role to SET ROLE to")
    ev_gate.add_argument("--campaign-id", required=True)
    ev_gate.add_argument(
        "--design",
        required=True,
        help="JSON preregistration record for the SamplingDesign (frozen at prepare time)",
    )
    ev_gate.add_argument(
        "--tiers",
        default=None,
        help="optional JSON {pair_id: {tier, scope}} mapping the frozen candidate "
        "auto-tier/scope onto each sampled pair",
    )
    ev_gate.add_argument(
        "--format",
        choices=("json", "md"),
        default="json",
        help="report format (json payload or markdown)",
    )

    camera = sub.add_parser(
        "camera-sites",
        help="geospatial camera-site entity resolution over the PG spine (P30.2b)",
    )
    camera.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    camera.add_argument("--role", default=None, help="optional role to SET ROLE to")
    camera.add_argument(
        "--dry-run",
        action="store_true",
        help="read + resolve + measure only; write nothing (prints the summary)",
    )
    triage = sub.add_parser(
        "identity-triage",
        help="P31.3: every (scheme, value) shared by >1 entity, with its evidence and "
        "recorded same_as/distinct decision (read-only; --apply appends the committed ones)",
    )
    triage.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    triage.add_argument(
        "--decisions", default=None, help="decisions JSON (default: the packaged file)"
    )
    triage.add_argument(
        "--apply",
        action="store_true",
        help="append the committed decisions for pairs that have none (default: read-only)",
    )
    audit = sub.add_parser(
        "partner-name-audit",
        help="P32.3 dry-run impact report: every legacy sig.org.name partner key, "
        "its asserting sources/predicates, and the scoped sig.org.name_scoped keys "
        "it decomposes into (read-only)",
    )
    audit.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    return parser


def _load_records(path: str) -> list[dict[str, object]]:
    with open(path, encoding="utf-8") as fh:
        records = json.load(fh)
    if not isinstance(records, list):
        raise ValueError("records file must contain a JSON array of objects")
    return records


def _load_queue(path: str) -> ReviewQueue:
    if not os.path.exists(path):
        return ReviewQueue()
    with open(path, encoding="utf-8") as fh:
        return ReviewQueue.from_dict(json.load(fh))


def _save_queue(path: str, queue: ReviewQueue) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(queue.to_dict(), fh, indent=2, sort_keys=True)


def _read_org_candidates(conn: Any, jurisdiction: str | None) -> list[dict[str, object]]:
    """Read organisation candidates from the PG spine for the probabilistic matcher.

    Each candidate carries the columns the model blocks/compares on
    (``unique_id``, ``normalized_name``, ``name_first_token``, ``state``,
    ``organization_class``), derived from the ``organization`` projection + the
    entity's identifiers. Optionally filtered to a jurisdiction token matched on the
    entity's identifier values (e.g. ``okc``).
    """
    params: list[Any] = []
    where = ""
    if jurisdiction:
        where = (
            " WHERE o.entity_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{jurisdiction}%")
    rows = conn.execute(
        "SELECT o.entity_id, o.cached_canonical_name, o.organization_type, "
        "       (SELECT value FROM entity_identifier ei WHERE ei.entity_id = o.entity_id "
        "          AND ei.scheme = 'us.state' LIMIT 1) AS state "
        "  FROM organization o" + where + " ORDER BY o.entity_id",
        tuple(params),
    ).fetchall()
    candidates: list[dict[str, object]] = []
    for entity_id, canonical_name, org_type, state in rows:
        normalized = normalize_org_name(str(canonical_name or ""))
        first_token = normalized.split()[0] if normalized else ""
        candidates.append(
            {
                "unique_id": str(entity_id),
                "normalized_name": normalized,
                "name_first_token": first_token,
                "state": state or "",
                "organization_class": org_type or "",
            }
        )
    return candidates


def _run_match(args: argparse.Namespace) -> int:
    """Score PG org candidates and enqueue the tier-4/5 PROPOSED proposals (P19.5)."""
    queue = PgReviewQueue.from_dsn(args.dsn)
    if args.role:
        queue._conn.execute(f"SET ROLE {args.role}")
    candidates = _read_org_candidates(queue._conn, args.jurisdiction)
    if len(candidates) < 2:
        print(f"(only {len(candidates)} candidate org(s) for the filter; nothing to match)")
        return 0
    proposals = ProbabilisticMatcher.from_data().match(candidates)
    if not proposals:
        print("(no tier-4/5 proposals; every scored pair fell to tier 6)")
        return 0
    added = queue.enqueue_matches(proposals)
    for m in proposals:
        print(
            f"tier {m.tier_label}  weight {m.match_weight:+.2f}  "
            f"p={m.match_probability:.3f}  {m.left} ~ {m.right}  [{m.disposition}]"
        )
    print(f"enqueued {added} PROPOSED proposal(s) to the PG review queue")
    return 0


def _run_review_pg(args: argparse.Namespace) -> int:
    """The review curation surface backed by PostgreSQL (``PgReviewQueue``)."""
    queue = PgReviewQueue.from_dsn(args.dsn)
    if args.review_command == "enqueue":
        matcher = ProbabilisticMatcher.from_data()
        added = queue.enqueue_matches(matcher.match(_load_records(args.path)))
        print(f"enqueued {added} PROPOSED proposal(s); {len(queue.pending())} pending in PG")
        return 0
    if args.review_command == "list":
        filters = [args.prefix, args.tier, args.bucket, args.campaign, args.limit]
        if any(f is not None for f in filters):
            from .camera_site_review import pending_items

            pending = pending_items(
                queue.conn,
                prefixes=args.prefix,
                tier=args.tier,
                bucket=args.bucket,
                campaign=args.campaign,
                limit=args.limit,
            )
        else:
            pending = queue.pending()
        if not pending:
            print("(no pending proposals)")
            return 0
        for item in pending:
            print(f"[{item.item_id}]")
            print(surface_confidence_explanation(item))
        return 0
    if args.review_command == "show":
        found = queue.get(args.item_id)
        if found is None:
            print(f"no such review item: {args.item_id}")
            return 2
        print(surface_confidence_explanation(found))
        return 0
    if args.review_command == "decide":
        try:
            decision = queue.decide(
                args.item_id,
                args.decision,
                reviewer=args.reviewer,
                rationale=args.rationale,
            )
        except ValueError as exc:
            print(str(exc))
            return 2
        provenance = ""
        if decision.model_id is not None:
            provenance = f" (model {decision.model_id} prompt {decision.prompt_version})"
        print(f"{decision.decision} by {decision.reviewer} at {decision.decided_at}{provenance}")
        return 0
    print("usage: sig-resolution review {enqueue,list,show,decide} --dsn ...")
    return 2


def _run_review_sample(args: argparse.Namespace) -> int:
    """Draw the stratified, seeded camera-site sample; optionally tag a campaign.

    Read-only unless ``--campaign`` is given: the draw itself never writes, and
    ``--dry-run`` forces a print-only run even with ``--campaign``. The default
    ``--n 400`` is the §6 Q11 design — the Round-10 campaign design; this
    tooling prepares the sample, it never runs a review (no decisions here).
    """
    import psycopg

    from .camera_site_review import (
        CAMERA_SITE_PREFIXES,
        draw_sample,
        materialize_campaign,
        parse_strata,
        pending_items,
        stratum_for,
    )
    from .camera_sites_pg import set_role

    try:
        strata = parse_strata(args.strata)
    except ValueError as exc:
        print(str(exc))
        return 2
    with psycopg.connect(args.dsn, autocommit=True) as conn:
        if args.role:
            set_role(conn, args.role)
        pending = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES)
        universe: dict[str, int] = {}
        for it in pending:
            s = stratum_for(it.item_id, it.payload)
            universe[s] = universe.get(s, 0) + 1
        drawn = draw_sample(conn, strata, n=args.n, seed=args.seed)
        union = sorted({i for ids in drawn.values() for i in ids})
        design = {
            "strata": [{"name": n_, "requested": r} for n_, r in strata],
            "n": args.n,
            "seed": args.seed,
            "universe_pending": universe,
            "drawn_by_stratum": {k: len(v) for k, v in drawn.items()},
            "unique_drawn": len(union),
        }
        design["design_digest"] = hashlib.sha256(
            json.dumps(
                {"strata": design["strata"], "seed": args.seed, "n": args.n, "items": union},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        summary: dict[str, Any] = {
            "seed": args.seed,
            "n": args.n,
            "strata": {
                name: {
                    "available": sum(
                        1 for i in pending if stratum_for(i.item_id, i.payload) == name
                    ),
                    "drawn": len(drawn.get(name, [])),
                }
                for name, _r in strata
            },
            "unique_drawn": len(union),
            "design_digest": design["design_digest"],
        }
        if args.campaign and not args.dry_run:
            result = materialize_campaign(
                conn,
                campaign_id=args.campaign,
                purpose=args.purpose,
                design=design,
                created_by=args.created_by,
                drawn=drawn,
            )
            summary["campaign"] = result
            summary["purpose"] = args.purpose
        else:
            summary["campaign"] = None
            summary["dry_run"] = True
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _run_review_export(args: argparse.Namespace) -> int:
    """Serialise pending items to a JSONL labelling session (blank decisions)."""
    import psycopg

    from .camera_site_review import CAMERA_SITE_PREFIXES, export_rows
    from .camera_sites_pg import set_role

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        if args.role:
            set_role(conn, args.role)
        rows = export_rows(
            conn,
            campaign=args.campaign,
            prefixes=args.prefix or CAMERA_SITE_PREFIXES,
            tier=args.tier,
            bucket=args.bucket,
        )
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"exported {len(rows)} pending item(s) to {args.out}")
    else:
        print(text, end="")
    return 0


def _run_review_import(args: argparse.Namespace) -> int:
    """Append a JSONL labelling session's decisions via PgReviewQueue.decide."""
    from .camera_site_review import import_decisions
    from .camera_sites_pg import set_role

    with open(args.path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    queue = PgReviewQueue.from_dsn(args.dsn)
    if args.role:
        set_role(queue.conn, args.role)
    result = import_decisions(queue, rows, reviewer=args.reviewer)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["errors"] else 0


def _run_review(args: argparse.Namespace) -> int:
    if args.review_command == "sample":
        return _run_review_sample(args)
    if args.review_command == "export":
        return _run_review_export(args)
    if args.review_command == "import":
        return _run_review_import(args)
    if getattr(args, "dsn", None):
        return _run_review_pg(args)
    if args.review_command == "enqueue":
        queue = _load_queue(args.queue)
        matcher = ProbabilisticMatcher.from_data()
        added = 0
        for match in matcher.match(_load_records(args.path)):
            item = review_item_from_match(match)
            if queue.get(item.item_id) is None:
                queue.enqueue(item)
                added += 1
        _save_queue(args.queue, queue)
        print(
            f"enqueued {added} PROPOSED proposal(s); {len(queue.pending())} pending in {args.queue}"
        )
        return 0
    if args.review_command == "list":
        queue = _load_queue(args.queue)
        pending = queue.pending()
        if not pending:
            print("(no pending proposals)")
            return 0
        for item in pending:
            print(f"[{item.item_id}]")
            print(surface_confidence_explanation(item))
        return 0
    if args.review_command == "show":
        queue = _load_queue(args.queue)
        found = queue.get(args.item_id)
        if found is None:
            print(f"no such review item: {args.item_id}")
            return 2
        print(surface_confidence_explanation(found))
        return 0
    if args.review_command == "decide":
        queue = _load_queue(args.queue)
        try:
            decision = queue.decide(
                args.item_id,
                args.decision,
                reviewer=args.reviewer,
                rationale=args.rationale,
            )
        except ValueError as exc:
            print(str(exc))
            return 2
        _save_queue(args.queue, queue)
        provenance = ""
        if decision.model_id is not None:
            provenance = f" (model {decision.model_id} prompt {decision.prompt_version})"
        print(f"{decision.decision} by {decision.reviewer} at {decision.decided_at}{provenance}")
        return 0
    print("usage: sig-resolution review {enqueue,list,show,decide} ...")
    return 2


# --------------------------------------------------------------------------- #
# `eval` — the P32.9 independent blinded human-evaluation campaign surface.     #
# --------------------------------------------------------------------------- #
def _frame_items_from_jsonl(path: str) -> list[Any]:
    from .human_eval import FrameItem

    items = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            try:
                items.append(
                    FrameItem(
                        pair_id=row["pair_id"],
                        left_ref=row["left_ref"],
                        right_ref=row["right_ref"],
                        stratum_id=row["stratum_id"],
                        estimand=row.get("estimand", "auto_positive_precision"),
                        reference_basis=row.get("reference_basis", "physical_identity"),
                        entity_neighborhood=row.get("entity_neighborhood", ""),
                        source_lineage_ids=tuple(row.get("source_lineage_ids") or ()),
                        republisher_family=row.get("republisher_family", ""),
                        mirror_group_id=row.get("mirror_group_id", ""),
                    )
                )
            except (KeyError, ValueError) as exc:
                raise ValueError(f"frame JSONL line {i}: {exc}") from exc
    return items


def _run_eval_frame(args: argparse.Namespace) -> int:
    """Emit the camera-site frame JSONL (read-only)."""
    import psycopg

    from .camera_sites_pg import set_role
    from .human_eval_pg import frame_from_review_items

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        if args.role:
            set_role(conn, args.role)
        rows = frame_from_review_items(conn, limit=args.limit)
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(rows)} frame item(s) to {args.out}")
    else:
        print(text, end="")
    return 0


def _run_eval_prepare(args: argparse.Namespace) -> int:
    """Preregister the campaign + draw the disjoint seeded sample."""
    import psycopg

    from .human_eval import (
        GroupSpec,
        SampleSpec,
        assign_partitions,
        campaign_design,
        draw_eval_sample,
        homogenize_group_strata,
        manifest_digest,
    )
    from .human_eval_pg import preregister_campaign, write_manifest, write_samples

    items = _frame_items_from_jsonl(args.frame_jsonl)
    spec_doc: dict[str, Any] = {}
    if args.design:
        with open(args.design, encoding="utf-8") as fh:
            spec_doc = json.load(fh)
    gs = spec_doc.get("group_spec") or {}
    ss = spec_doc.get("sample_spec") or {}
    group_spec = GroupSpec(
        fractions=gs.get("fractions") or GroupSpec().fractions,
        holdout_families=tuple(gs.get("holdout_families") or ()),
        per_stratum=gs.get("per_stratum") or {},
    )
    sample_spec = SampleSpec(quotas=ss.get("quotas") or {})
    design = campaign_design(
        purpose=args.purpose,
        protocol_digest=args.protocol_digest,
        frame_snapshot=args.frame_snapshot,
        ruleset_digest=args.ruleset_digest,
        seed=args.seed,
        group_spec=group_spec,
        sample_spec=sample_spec,
        target_population=spec_doc.get("target_population", ""),
        rubric_version=spec_doc.get("rubric_version", "eval-rubric/1"),
        extra=spec_doc.get("extra"),
    )

    items = homogenize_group_strata(items)
    partitions = assign_partitions(items, seed=args.seed, spec=group_spec)
    rows, denominators = draw_eval_sample(
        items, partitions, campaign_id=args.campaign_id, seed=args.seed, spec=sample_spec
    )
    campaign = {
        "campaign_id": args.campaign_id,
        "purpose": args.purpose,
        "design": design,
    }
    summary: dict[str, Any] = {
        "campaign_id": args.campaign_id,
        "frame_items": len(items),
        "drawn": len(rows),
        "partitions": {
            p: sum(1 for r in rows if r["partition"] == p)
            for p in sorted({r["partition"] for r in rows})
        },
        "denominators": denominators,
        "manifest_digest": manifest_digest(campaign, rows),
        "dry_run": bool(args.dry_run),
    }
    if not args.dry_run:
        with psycopg.connect(args.dsn, autocommit=True) as conn:
            preregister_campaign(
                conn,
                campaign_id=args.campaign_id,
                purpose=args.purpose,
                protocol_digest=args.protocol_digest,
                frame_snapshot=args.frame_snapshot,
                ruleset_digest=args.ruleset_digest,
                seed=args.seed,
                design=design,
                created_by=args.created_by,
                role=args.role,
            )
            write_samples(conn, rows, role=args.role)
            manifest = write_manifest(
                conn,
                campaign_id=args.campaign_id,
                sample_rows=rows,
                denominators=denominators,
                created_by=args.created_by,
                role=args.role,
            )
            summary["manifest"] = manifest
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _run_eval_packets(args: argparse.Namespace) -> int:
    """Build + persist blinded packets for the campaign's samples."""
    import psycopg

    from .camera_site_review import read_observation
    from .camera_sites_pg import set_role
    from .human_eval import build_blinded_packet
    from .human_eval_pg import read_campaign, read_samples, write_packets

    evidence: dict[str, Any] = {}
    if args.evidence_jsonl:
        with open(args.evidence_jsonl, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    evidence[row.get("sample_id") or row.get("pair_id")] = row

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        if args.role:
            set_role(conn, args.role)
        campaign = read_campaign(conn, args.campaign_id, role=None)
        samples = read_samples(conn, args.campaign_id, role=None)
        packets = []
        skipped = 0
        for s in samples:
            if evidence:
                row = evidence.get(s["sample_id"]) or evidence.get(s["pair_id"])
                if row is None:
                    skipped += 1
                    continue
                left_ev, right_ev = row.get("left") or {}, row.get("right") or {}
            elif args.from_spine:
                left_ev = read_observation(conn, s["left_ref"]) or {}
                right_ev = read_observation(conn, s["right_ref"]) or {}
            else:
                print("packets needs --from-spine or --evidence-jsonl")
                return 2
            payload = build_blinded_packet(
                sample_id=s["sample_id"],
                seed=campaign["seed"],
                left_evidence=left_ev,
                right_evidence=right_ev,
            )
            packets.append(
                {
                    "campaign_id": s["campaign_id"],
                    "sample_id": s["sample_id"],
                    "payload": payload,
                }
            )
        n = write_packets(conn, packets, role=None)
    print(json.dumps({"packets": n, "skipped": skipped}, indent=2, sort_keys=True))
    return 0


def _run_eval_assign(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import assign_reviewers, read_samples

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        if args.samples == "all":
            ids = [s["sample_id"] for s in read_samples(conn, args.campaign_id, role=args.role)]
        else:
            ids = [s.strip() for s in args.samples.split(",") if s.strip()]
        n = assign_reviewers(
            conn,
            campaign_id=args.campaign_id,
            reviewer_id=args.reviewer,
            sample_ids=ids,
            pass_no=args.pass_no,
            assigned_by=args.assigned_by,
            role=args.role,
        )
    print(json.dumps({"assigned": n, "reviewer": args.reviewer, "pass": args.pass_no}))
    return 0


def _run_eval_status(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import campaign_status

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        status = campaign_status(conn, args.campaign_id, role=args.role)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def _run_eval_export(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import export_workbook

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        rows = export_workbook(
            conn,
            campaign_id=args.campaign_id,
            reviewer_id=args.reviewer,
            pass_no=args.pass_no,
            role=args.role,
        )
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"exported {len(rows)} workbook row(s) to {args.out}")
    else:
        print(text, end="")
    return 0


def _run_eval_attest(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import record_attestation

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        attestation_id = record_attestation(
            conn,
            campaign_id=args.campaign_id,
            reviewer_id=args.reviewer,
            kind=args.kind,
            detail=json.loads(args.detail),
            recorded_by=args.recorded_by,
            role=args.role,
        )
    print(json.dumps({"attestation_id": attestation_id, "reviewer": args.reviewer}))
    return 0


def _run_eval_import_labels(args: argparse.Namespace) -> int:
    """Append human labels as the reviewer role — one row per filled workbook line."""
    import psycopg

    from .human_eval import label_digest as compute_label_digest
    from .human_eval_pg import record_label

    appended, errors = 0, []
    with open(args.path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    with psycopg.connect(args.dsn, autocommit=True) as conn:
        for i, row in enumerate(rows, 1):
            label = row.get("label")
            if not label:
                continue  # a blank workbook row is an unanswered item, not a label
            try:
                digest = compute_label_digest(
                    campaign_id=args.campaign_id,
                    sample_id=row["sample_id"],
                    reviewer_id=args.reviewer,
                    round=args.label_round,
                    label=label,
                    reason_codes=row.get("reason_codes") or [],
                    evidence_refs=row.get("evidence_refs") or [],
                    rubric_version=row.get("rubric_version") or args.rubric_version,
                    packet_digest=row["packet_digest"],
                )
                record_label(
                    conn,
                    campaign_id=args.campaign_id,
                    sample_id=row["sample_id"],
                    reviewer_id=args.reviewer,
                    round=args.label_round,
                    label=label,
                    reason_codes=row.get("reason_codes") or [],
                    evidence_refs=row.get("evidence_refs") or [],
                    rubric_version=row.get("rubric_version") or args.rubric_version,
                    packet_digest=row["packet_digest"],
                    attestation_id=row.get("attestation_id") or args.attestation,
                    label_digest=digest,
                    role=args.role,
                )
                appended += 1
            except (ValueError, KeyError) as exc:
                errors.append({"line": i, "sample_id": row.get("sample_id"), "error": str(exc)})
    print(json.dumps({"appended": appended, "errors": errors}, indent=2, sort_keys=True))
    return 1 if errors else 0


def _run_eval_adjudicate(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import record_adjudication

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        aid = record_adjudication(
            conn,
            campaign_id=args.campaign_id,
            sample_id=args.sample_id,
            adjudicator_id=args.adjudicator,
            phase=args.phase,
            label=args.label,
            reason=args.reason,
            evidence_refs=json.loads(args.evidence_refs),
            role=args.role,
        )
    print(json.dumps({"adjudication_id": aid, "label": args.label}))
    return 0


def _run_eval_unseal(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import record_release

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        rid = record_release(
            conn,
            campaign_id=args.campaign_id,
            scope=args.scope,
            authorized_by=args.authorized_by,
            detail=json.loads(args.detail),
            role=args.role,
        )
    print(json.dumps({"release_id": rid, "scope": args.scope}))
    return 0


def _run_eval_verify(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import verify_manifest

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        result = verify_manifest(conn, args.campaign_id, role=args.role)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


def _run_eval_watermark(args: argparse.Namespace) -> int:
    import psycopg

    from .human_eval_pg import campaign_watermark

    with psycopg.connect(args.dsn, autocommit=True) as conn:
        wm = campaign_watermark(conn, args.campaign_id, role=args.role)
    print(json.dumps({"campaign_id": args.campaign_id, "label_watermark": wm}))
    return 0


def _run_eval_gate(args: argparse.Namespace) -> int:
    """P32.10 — the SHADOW confidence-gate readout over a campaign.

    Reads the released label/adjudication surface only, materializes eval
    units (missing/sealed stay in the denominator), runs the preregistered
    design-aware gate, and prints the report. ``applied`` is always empty —
    the PROVISIONAL production policy is untouched.
    """
    import psycopg

    from .evaluator import render_report_md, report_digest, sampling_design_from_dict
    from .human_eval_pg import run_shadow_evaluation

    with open(args.design, encoding="utf-8") as fh:
        design = sampling_design_from_dict(json.load(fh))
    tier_of_pair: dict[str, int] = {}
    scope_of_pair: dict[str, str] = {}
    if args.tiers:
        with open(args.tiers, encoding="utf-8") as fh:
            for pair_id, spec in json.load(fh).items():
                tier_of_pair[pair_id] = int(spec["tier"])
                scope_of_pair[pair_id] = str(spec.get("scope", "snapshot"))
    with psycopg.connect(args.dsn, autocommit=True) as conn:
        report = run_shadow_evaluation(
            conn,
            args.campaign_id,
            design=design,
            tier_of_pair=tier_of_pair,
            scope_of_pair=scope_of_pair,
            role=args.role,
        )
    if args.format == "md":
        print(render_report_md(report))
    else:
        print(
            json.dumps(
                {**report.payload(), "report_digest": report_digest(report)},
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _run_eval(args: argparse.Namespace) -> int:
    handlers = {
        "frame": _run_eval_frame,
        "prepare": _run_eval_prepare,
        "packets": _run_eval_packets,
        "assign": _run_eval_assign,
        "status": _run_eval_status,
        "export": _run_eval_export,
        "attest": _run_eval_attest,
        "import-labels": _run_eval_import_labels,
        "adjudicate": _run_eval_adjudicate,
        "unseal": _run_eval_unseal,
        "verify": _run_eval_verify,
        "watermark": _run_eval_watermark,
        "gate": _run_eval_gate,
    }
    handler = handlers.get(args.eval_command)
    if handler is None:
        print(
            "usage: sig-resolution eval {frame,prepare,packets,assign,status,export,"
            "attest,import-labels,adjudicate,unseal,verify,watermark,gate} ..."
        )
        return 2
    try:
        return handler(args)
    except ValueError as exc:
        print(str(exc))
        return 2


def main(argv: list[str] | None = None) -> int:
    """Run the `resolution` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "geoid":
        try:
            print(validate_geoid(args.code, args.level))
        except GeoidValidationError as exc:
            print(str(exc))
            return 2
        return 0
    if args.command == "agency-name":
        parsed = parse_agency_name(args.name)
        print(f"parent: {parsed.parent or '(none)'}")
        print(f"unit:   {parsed.unit}")
        return 0
    if args.command == "relation-types":
        for value in OrganizationRelationType:
            print(value.value)
        return 0
    if args.command == "normalize":
        print(normalize_org_name(args.name))
        print(f"(ruleset v{NORMALIZE_RULESET_VERSION})")
        return 0
    if args.command == "ori":
        try:
            validate_ori(args.value)
        except OriValidationError as exc:
            print(str(exc))
            return 2
        print(f"valid: {args.value}")
        print(f"civil/applicant ORI: {is_civil_ori(args.value)}")
        return 0
    if args.command == "scheme":
        res = canonical_scheme_for(args.organization_class)
        if res.is_surrogate:
            print(f"{args.organization_class}: SIG surrogate (no external canonical scheme)")
        else:
            print(f"{args.organization_class}: {res.canonical_scheme}")
            if res.secondary_schemes:
                print(f"  secondary: {', '.join(res.secondary_schemes)}")
        return 0
    if args.command == "slug":
        hypothesis = parse_slug(args.slug)
        if hypothesis is None:
            print("(denied: vendor-internal test tenant or empty slug)")
            return 0
        print(f"name hypothesis: {hypothesis.name_hypothesis}")
        print(f"(grammar v{hypothesis.grammar_version}; hypothesis only, not an identity)")
        return 0
    if args.command == "er-match":
        matcher = ProbabilisticMatcher.from_data()
        proposals = matcher.match(_load_records(args.path))
        if not proposals:
            print("(no tier-4/5 proposals; every scored pair fell to tier 6)")
            return 0
        for m in proposals:
            print(
                f"tier {m.tier_label}  weight {m.match_weight:+.2f}  "
                f"p={m.match_probability:.3f}  {m.left} ~ {m.right}  [{m.disposition}]"
            )
            for c in m.decomposition:
                print(f"    {c.column}: bf={c.bayes_factor:.3f} [{c.label}]")
        return 0
    if args.command == "block-size":
        rule = BlockingRule("cli", tuple(k.strip() for k in args.keys.split(",") if k.strip()))
        records = _load_records(args.path)
        try:
            accepted = validate_blocking_rule(records, rule)
        except BlockingRuleRejected as exc:
            print(f"rejected ({size_blocking_rule(records, rule)} comparisons): {exc}")
            return 2
        print(f"accepted: {accepted} candidate comparisons")
        return 0
    if args.command == "match":
        return _run_match(args)
    if args.command == "review":
        return _run_review(args)
    if args.command == "eval":
        return _run_eval(args)
    if args.command == "camera-sites":
        return _run_camera_sites(args)
    if args.command == "identity-triage":
        return _run_identity_triage(args)
    if args.command == "partner-name-audit":
        return _run_partner_name_audit(args)

    parser.print_help()
    return 0


def _run_identity_triage(args: argparse.Namespace) -> int:
    """Duplicate-identifier triage (P31.3 / ADR-110, D-P30.4-3)."""
    import psycopg

    from .identity_triage import apply_decisions, as_report, load_decisions, triage

    decisions = load_decisions(args.decisions)
    reviewer = "engineering:P31.3 (operator-delegated, Q6)"
    appended = 0
    with psycopg.connect(args.dsn) as conn:
        if not args.apply:
            conn.execute("SET TRANSACTION READ ONLY")
            statuses = triage(conn, decisions)
            conn.rollback()
        else:
            # One transaction: every committed decision lands, or none does.
            statuses = triage(conn, decisions)
            appended = apply_decisions(PgReviewQueue(conn), statuses, reviewer=reviewer)
            conn.commit()
    undecided = [s for s in statuses if not s.recorded]
    print(
        json.dumps(
            {
                "pairs": as_report(statuses),
                "pair_count": len(statuses),
                "appended": appended,
                "undecided": len(undecided),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if undecided else 0


def _run_partner_name_audit(args: argparse.Namespace) -> int:
    """Dry-run impact report for legacy ``sig.org.name`` partner keys (P32.3)."""
    import psycopg

    from .partner_name_audit import name_scope_report

    with psycopg.connect(args.dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        report = name_scope_report(conn)
        conn.rollback()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _run_camera_sites(args: argparse.Namespace) -> int:
    """Camera-site entity resolution over the PG spine (P30.2b, ADR-105)."""
    import sys
    import time

    from .camera_sites import resolve_camera_sites
    from .camera_sites_pg import (
        materialize_camera_sites_from_dsn,
        read_camera_records,
        set_role,
    )

    started = time.monotonic()

    def _progress(stage: str, done: int, inserted: int) -> None:
        # stderr, so stdout stays the one JSON summary a caller parses.
        elapsed = time.monotonic() - started
        print(
            f"progress: {stage} {done} (inserted {inserted}), {elapsed:.0f}s",
            file=sys.stderr,
            flush=True,
        )

    if args.dry_run:
        import psycopg

        from .camera_sites import load_camera_gold
        from .camera_sites_pg import read_human_verdicts
        from .eval_loop import read_auto_write_threshold

        with psycopg.connect(args.dsn, autocommit=True) as conn:
            if args.role:
                set_role(conn, args.role)
            records = read_camera_records(conn)
            human_items, human_votes = read_human_verdicts(conn)
        result = resolve_camera_sites(
            records,
            gold=load_camera_gold(),
            threshold=read_auto_write_threshold(),
            human_items=human_items,
            human_votes=human_votes,
        )
        print(json.dumps({**result.summary(), "dry_run": True}, indent=2, default=str))
        return 0
    summary = materialize_camera_sites_from_dsn(args.dsn, role=args.role, progress=_progress)
    print(json.dumps(summary, indent=2, default=str))
    return 0
