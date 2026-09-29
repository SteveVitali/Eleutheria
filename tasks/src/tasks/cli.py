# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `tasks` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. P21.7 adds the
contribution-back live edge — all **human-mediated** and all **dry-run by default**
(SIG-CONTRIB-014, additive/back-compat):

* ``maproulette push --challenge ID --jurisdiction J`` — build a MapRoulette
  cooperative challenge from a task selection and (with ``SIG_MAPROULETTE_API_KEY``)
  create it, else print the dry-run JSON payload. **Refuses (exit 3)** while the OSM
  Organised Editing activity is not registered (``ops/config.toml``
  ``[tasks.contribution] registered=false``; SIG-CONTRIB-016d, RISK-P16-14).
* ``maproulette pull --challenge ID`` — fetch task-status changes (dry-run without
  the key). Read-only; never applies an edit.
* ``osm-feed pull [--since T] [--fixtures …] [--out DIR]`` — replay the public OSM
  changeset feed (recorded fixtures by default; HG-08: no live poll) and attribute
  hashtag-bearing changesets to the §7 :class:`~tasks.contribution.LeverageLedger`
  (append-only, no OSM user data — Part VIII §0.7).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from policy.sensitivity import SensitivityClass

from . import __version__
from .contribution import (
    CHANGESET_HASHTAG,
    TagChange,
    TagSuggestion,
    contribution_registered,
)
from .maproulette import (
    ChallengeNotRegisteredError,
    ChallengeTask,
    HttpxMapRouletteTransport,
    MapRouletteClient,
    build_challenge,
)
from .osm_feed import DEFAULT_FIXTURE_GLOB, leverage_metric_json, pull_files
from .request_outcomes import (
    RequestOutcomeLog,
    outcome_from_api_payload,
    outcome_from_claims,
)


def _repo_root() -> Path:
    """The repository root (tasks/src/tasks/cli.py → four parents up)."""
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `tasks` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-tasks",
        description="SIG tasks stage: research-task engine + contribution-back edge (§33/§35).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    mr = sub.add_parser(
        "maproulette",
        help="MapRoulette cooperative challenge push/pull (human-mediated; dry-run without key)",
    )
    mr_sub = mr.add_subparsers(dest="mr_command")
    push = mr_sub.add_parser("push", help="create/update a challenge (dry-run without the API key)")
    push.add_argument("--challenge", default="sig-okc-operator-attribution", help="challenge id")
    push.add_argument("--jurisdiction", default="okc", help="jurisdiction slug (→ #sig-<j>)")
    push.add_argument(
        "--dry-run",
        action="store_true",
        help="print the payload without any live call (the default when no API key)",
    )
    pull = mr_sub.add_parser("pull", help="fetch task-status changes (read-only; dry-run w/o key)")
    pull.add_argument("--challenge", required=True, help="challenge id to pull statuses for")

    feed = sub.add_parser(
        "osm-feed", help="OSM changeset feed → §7 leverage metric (fixtures replay by default)"
    )
    feed_sub = feed.add_subparsers(dest="feed_command")
    fpull = feed_sub.add_parser("pull", help="attribute hashtag-bearing changesets (append-only)")
    fpull.add_argument(
        "--since", default=None, help="only changesets closed at/after this ISO time"
    )
    fpull.add_argument(
        "--fixtures", nargs="*", default=None, help="changeset XML fixtures (default: recorded)"
    )
    fpull.add_argument("--out", default=None, help="write <out>/web/leverage.json (export mode)")

    ro = sub.add_parser(
        "records-outcomes",
        help="records-request outcome log (BL-028): record + fold real request outcomes",
    )
    ro_sub = ro.add_subparsers(dest="ro_command")
    rec = ro_sub.add_parser(
        "record",
        help="append outcome observations (claims JSON per request, or one API payload)",
    )
    rec.add_argument(
        "--claims",
        default=None,
        metavar="FILE",
        help="JSON list of spine/connector claim rows; grouped per request by subject_id",
    )
    rec.add_argument(
        "--payload",
        default=None,
        metavar="FILE",
        help="one platform API request object (e.g. MuckRock api_v2) as JSON",
    )
    rec.add_argument(
        "--status-map",
        default=None,
        metavar="FILE",
        help="JSON map raw platform status -> §11.19 status (e.g. muckrock_status_map)",
    )
    rec.add_argument("--platform", default="muckrock", help="platform id for the observation")
    rec.add_argument(
        "--source",
        default=None,
        help="observation source label (default: claim_spine for --claims, <platform>_api "
        "for --payload)",
    )
    rec.add_argument(
        "--log",
        default=None,
        help="outcome-log path (default: $SIG_RECORDS_OUTCOME_LOG or "
        ".sig/tasks/records_outcomes.jsonl)",
    )
    show = ro_sub.add_parser("show", help="print the folded current state per request")
    show.add_argument("--log", default=None, help="outcome-log path (as for `record`)")
    return parser


# --------------------------------------------------------------------------- #
# MapRoulette
# --------------------------------------------------------------------------- #
def _demo_tasks() -> list[ChallengeTask]:
    """A small demo selection: two publishable geo tasks + one sensitive-tier task.

    The sensitive (C4, confidential-facility) task is EXCLUDED from the push payload
    (RISK-P21-12) — its coordinate never leaves SIG. Real selections come from a
    ``TaskPool``; this is the CLI's demonstration set (cf. connectors ``_seed_demo``).
    """
    return [
        ChallengeTask(
            suggestion=TagSuggestion(
                suggestion_id="sug:okc:1",
                change=TagChange("node", 111, "operator", "Oklahoma City Police Department"),
                instruction=(
                    "Public procurement records (contract OKC-2026-0142) show OCPD operates "
                    "this ALPR. Suggest operator=Oklahoma City Police Department."
                ),
                evidence_ref="evidence:contract:okc-2026-0142",
                source_id="okc-procurement",
                checkin_comment=f"operator=OCPD {CHANGESET_HASHTAG} #sig-okc",
            ),
            lat=35.4676,
            lon=-97.5164,
            sensitivity_class=SensitivityClass.C1,
        ),
        ChallengeTask(
            suggestion=TagSuggestion(
                suggestion_id="sug:okc:2",
                change=TagChange("node", 222, "operator", "Oklahoma City Police Department"),
                instruction="City agenda item 2026-88 attributes this camera to OCPD.",
                evidence_ref="evidence:agenda:okc-2026-88",
                source_id="okc-records",
                checkin_comment=f"operator=OCPD {CHANGESET_HASHTAG} #sig-okc",
            ),
            lat=35.4820,
            lon=-97.5290,
            sensitivity_class=SensitivityClass.C1,
        ),
        ChallengeTask(
            suggestion=TagSuggestion(
                suggestion_id="sug:okc:sensitive",
                change=TagChange("node", 333, "operator", "Confidential facility operator"),
                instruction="EXCLUDED: confidential-facility location (C4); never pushed.",
                evidence_ref="evidence:sealed",
                source_id="okc-records",
                checkin_comment=f"operator=redacted {CHANGESET_HASHTAG} #sig-okc",
            ),
            lat=35.5000,
            lon=-97.6000,
            sensitivity_class=SensitivityClass.C4,
        ),
    ]


def _maproulette_push(args: argparse.Namespace) -> int:
    registered = contribution_registered()
    # `--dry-run` forces the no-network path even if a key is present; without a key
    # the client is already dry-run. The registration gate is checked first either way.
    # HG-08 activation-ready: with a key AND registration, the live push POSTs through
    # the concrete httpx transport; keyless it stays dry-run and the transport is unused.
    client = (
        MapRouletteClient(api_key=None)
        if args.dry_run
        else MapRouletteClient.from_env(transport=HttpxMapRouletteTransport())
    )
    challenge = build_challenge(
        challenge_id=args.challenge,
        name=f"SIG operator attribution — {args.jurisdiction.upper()}",
        instruction=(
            "Each task proposes operator=* for an orphaned surveillance-device node from "
            "public records. Review each individually and apply it in your own account."
        ),
        jurisdiction=args.jurisdiction,
    )
    try:
        result = client.push(
            challenge=challenge,
            jurisdiction=args.jurisdiction,
            tasks=_demo_tasks(),
            registered=registered,
        )
    except ChallengeNotRegisteredError as refused:
        print(f"REFUSED (exit 3): {refused}")
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("dry_run"):
        print("# dry-run: no SIG_MAPROULETTE_API_KEY set — no live MapRoulette call (HG-08).")
    return 0


def _maproulette_pull(args: argparse.Namespace) -> int:
    client = MapRouletteClient.from_env(transport=HttpxMapRouletteTransport())
    result = client.pull(challenge_id=args.challenge)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("dry_run"):
        print("# dry-run: no SIG_MAPROULETTE_API_KEY set — no live MapRoulette call (HG-08).")
    return 0


# --------------------------------------------------------------------------- #
# OSM changeset feed
# --------------------------------------------------------------------------- #
def _osm_feed_pull(args: argparse.Namespace) -> int:
    if args.fixtures:
        paths = [Path(p) for p in args.fixtures]
    else:
        paths = sorted(_repo_root().glob(DEFAULT_FIXTURE_GLOB))
    if not paths:
        print(f"no changeset fixtures found (looked for {DEFAULT_FIXTURE_GLOB}); nothing to pull")
        return 2
    result = pull_files(paths, since=args.since)
    metric = leverage_metric_json(result.ledger)
    print(f"osm-feed pull: replayed {len(paths)} fixture file(s) (no live OSM poll — HG-08)")
    print(f"  newly attributed changesets this run: {result.added_count} {list(result.added)}")
    print(f"  §7 accepted operator-attributions: {metric['accepted_operator_attributions']}")
    print(f"  attributed changeset ids: {metric['attributed_changeset_ids']}")
    if args.out:
        out_dir = Path(args.out) / "web"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "leverage.json").write_text(json.dumps(metric, indent=2, sort_keys=True))
        print(f"  wrote {out_dir / 'leverage.json'} (data.ts export mode)")
    return 0


# --------------------------------------------------------------------------- #
# Records-request outcome log (BL-028 / D-META.1-2)
# --------------------------------------------------------------------------- #
def _outcome_log(args: argparse.Namespace) -> RequestOutcomeLog:
    import os

    path = args.log or os.environ.get("SIG_RECORDS_OUTCOME_LOG")
    return RequestOutcomeLog(path) if path else RequestOutcomeLog()


def _records_outcomes_record(args: argparse.Namespace) -> int:
    log = _outcome_log(args)
    recorded = []
    if args.claims:
        rows = json.loads(Path(args.claims).read_text())
        # Group the claim rows per request subject; a file with no subject_id
        # column is treated as one request's predicate surface.
        groups: dict[str, list[dict]] = {}
        for row in rows:
            groups.setdefault(str(row.get("subject_id") or "_"), []).append(row)
        for claims in groups.values():
            recorded.append(
                log.record(
                    outcome_from_claims(
                        claims,
                        platform=args.platform,
                        source=args.source or "claim_spine",
                    )
                )
            )
    if args.payload:
        status_map = json.loads(Path(args.status_map).read_text()) if args.status_map else None
        recorded.append(
            log.record(
                outcome_from_api_payload(
                    json.loads(Path(args.payload).read_text()),
                    platform=args.platform,
                    status_map=status_map,
                    source=args.source or f"{args.platform}_api",
                )
            )
        )
    if not recorded:
        print("nothing to record: pass --claims or --payload")
        return 2
    for outcome in recorded:
        print(
            f"recorded {outcome.key}: state={outcome.state} "
            f"status={outcome.response_status} agency={outcome.agency} "
            f"filed={outcome.filed_date} response={outcome.response_date} "
            f"(source={outcome.source})"
        )
    print(f"appended {len(recorded)} observation(s) to {log.path}")
    return 0


def _records_outcomes_show(args: argparse.Namespace) -> int:
    log = _outcome_log(args)
    latest = log.latest()
    if not latest:
        print(f"no outcomes recorded in {log.path}")
        return 0
    for key in sorted(latest):
        o = latest[key]
        print(
            f"{key}: {o.state} ({o.response_status}) agency={o.agency} "
            f"filed={o.filed_date} response={o.response_date} "
            f"observed={o.observed_at} via {o.source}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `tasks` CLI. Returns a process exit code (3 = a gated refusal)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "maproulette":
        if args.mr_command == "push":
            return _maproulette_push(args)
        if args.mr_command == "pull":
            return _maproulette_pull(args)
        parser.parse_args([args.command, "--help"])
        return 0
    if args.command == "osm-feed":
        if args.feed_command == "pull":
            return _osm_feed_pull(args)
        parser.parse_args([args.command, "--help"])
        return 0
    if args.command == "records-outcomes":
        if args.ro_command == "record":
            return _records_outcomes_record(args)
        if args.ro_command == "show":
            return _records_outcomes_show(args)
        parser.parse_args([args.command, "--help"])
        return 0
    parser.print_help()
    return 0
