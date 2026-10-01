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
    if args.command == "camera-sites":
        return _run_camera_sites(args)
    if args.command == "identity-triage":
        return _run_identity_triage(args)

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
