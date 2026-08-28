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

With no sub-command it prints help and exits 0 (the SIG-ENG-013 convention).
"""

from __future__ import annotations

import argparse
import json
import os

from . import __version__
from .blocking import BlockingRule, BlockingRuleRejected, size_blocking_rule, validate_blocking_rule
from .crosswalk import canonical_scheme_for
from .geoid import GeoidValidationError, validate_geoid
from .identity import parse_agency_name
from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name
from .ori import OriValidationError, is_civil_ori, validate_ori
from .probabilistic import ProbabilisticMatcher
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

    review = sub.add_parser("review", help="the internal review queue / curation surface")
    review_sub = review.add_subparsers(dest="review_command")

    enqueue = review_sub.add_parser("enqueue", help="score records and enqueue PROPOSED matches")
    enqueue.add_argument("queue", help="the JSON queue file (created if absent)")
    enqueue.add_argument("path", help="a JSON file: an array of record objects")

    review_list = review_sub.add_parser("list", help="list pending proposals with confidence")
    review_list.add_argument("queue", help="the JSON queue file")

    show = review_sub.add_parser("show", help="show one proposal's confidence explanation")
    show.add_argument("queue", help="the JSON queue file")
    show.add_argument("item_id", help="the review item id")

    decide = review_sub.add_parser("decide", help="record a human accept/reject decision")
    decide.add_argument("queue", help="the JSON queue file")
    decide.add_argument("item_id", help="the review item id")
    decide.add_argument("decision", choices=("accept", "reject"))
    decide.add_argument("--reviewer", required=True, help="the human reviewer")
    decide.add_argument("--rationale", default=None, help="an optional note / review rationale")
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


def _run_review(args: argparse.Namespace) -> int:
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
    if args.command == "review":
        return _run_review(args)

    parser.print_help()
    return 0
