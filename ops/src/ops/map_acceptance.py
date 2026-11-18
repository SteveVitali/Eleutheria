# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.63 (K1 MAP-07, R11-K13-MAP-07): the map-acceptance leg declaration.

The ticket's job — "acceptance + republish" — is a *leg set*: the
deterministic halves run in this dispatch (the J1–J10 journey battery over
the real-sized national fixture, the national budgets/Lighthouse legs), and
the halves that can only run against a staged release candidate or the
promoted public surface are declared here as ``prepared_not_executed``
legs — the same posture the Round-10 composed machinery carries (the live
halves are return-pass work, never a fabricated pass).

Leg ordering follows K1 §9.5/§9.6 and OM-19:

* ``candidate`` legs queue on P37.65a staging the real release candidate —
  ``sig-exports tiles verify`` over the candidate's real-sized archives, the
  Lighthouse CI leg on the staged build, and the J1–J10 battery re-run.
* ``live`` legs queue on P37.65b promoting — the paced production journeys
  (K1 §9.5: J1, J2, J4, J6, ≤20 page loads, 3 s pacing), Lighthouse mobile
  against the public ``/map/``, the served-archive tile verification, and
  the 7-day billing-export cost read (K1 §9.6 — the window opens ≥7 days
  after promotion).

``sig-ops map-acceptance plan`` prints the declaration offline;
``sig-ops map-acceptance check`` verifies the *committed* machinery each
deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops map-acceptance run --leg <id>`` executes a deterministic leg
(``journeys-fixture``) and queues exit 42 on every gated leg — the named
precondition (a staged candidate, a promotion window, live_verification) is
not met by declaration, never by probing production.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The ticket's verbatim re-run prompt — the OM-19 form the deferred legs
#: name so the return pass needs no fresh operator text.
RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/491_P37.63__map-acceptance-and-republish.md "
    "live_verification=true"
)


@dataclass(frozen=True)
class Leg:
    """One acceptance leg — its command, the window that must open before it
    may run, and the artifact it writes."""

    leg_id: str
    stage: str  # "deterministic" | "candidate" | "live"
    description: str
    command: str
    precondition: str
    artifact: str


#: The committed leg list — order is the OM-19 execution order.
LEGS: tuple[Leg, ...] = (
    Leg(
        leg_id="journeys-fixture",
        stage="deterministic",
        description=(
            "the J1–J10 map-acceptance journey battery over the real-sized "
            "deterministic national fixture (web/tests/e2e/"
            "map-journeys.spec.ts; also runs under committed fixtures in the "
            "ordinary test:e2e pass)"
        ),
        command="bash scripts/ci/national_budget_leg.sh journeys",
        precondition="none — runs in CI (perf job) and this dispatch",
        artifact="playwright run output; cited in the acceptance packet",
    ),
    Leg(
        leg_id="budgets-fixture",
        stage="deterministic",
        description=(
            "the national wire-budget sweep + Lighthouse legs on the "
            "real-sized build (T2-map measured gaps bound at their recorded "
            "values — never relaxed)"
        ),
        command=(
            "bash scripts/ci/national_budget_leg.sh budgets && "
            "bash scripts/ci/national_budget_leg.sh lighthouse"
        ),
        precondition="none — runs in CI (perf job) and this dispatch",
        artifact="budget.spec results + lhci assert matrix output",
    ),
    Leg(
        leg_id="candidate-tiles",
        stage="candidate",
        description=(
            "pre-promotion tile verification over the REAL release "
            "candidate's archives (K1 §15: conservation, precision/tier, "
            "size, metadata, renderer parity where tippecanoe is pinned)"
        ),
        command="uv run sig-exports tiles verify --in <candidate-export-dir>",
        precondition="P37.65a stages the release candidate",
        artifact="<candidate>/reports/tiles_verify.json",
    ),
    Leg(
        leg_id="candidate-lhci",
        stage="candidate",
        description=(
            "Lighthouse CI on the staged release-candidate build — the "
            "generated national assert matrix incl. the T2-map budgets"
        ),
        command="npx lhci autorun --config=web/lighthouserc.national.json",
        precondition="P37.65a stages the release candidate",
        artifact="lhci report on the candidate build",
    ),
    Leg(
        leg_id="live-journeys",
        stage="live",
        description=(
            "K1 §9.5 production journeys — J1, J2, J4, J6 against the public "
            "origin, ≤20 page loads paced 3 s (the same battery file, "
            "SIG_LIVE_MAP_BASE pointing at the promoted origin)"
        ),
        command=(
            "SIG_LIVE_MAP_BASE=<public-origin> npx playwright test "
            "tests/e2e/map-journeys.spec.ts --grep 'J1|J2|J4|J6' "
            "(paced ≤20 loads / 3 s)"
        ),
        precondition="P37.65b promotes; live_verification=true (OM-19)",
        artifact="paced run log + per-journey verdicts",
    ),
    Leg(
        leg_id="live-lhci",
        stage="live",
        description="Lighthouse mobile against the promoted public /map/",
        command="npx lhci autorun --collect.url=<public-origin>/map/",
        precondition="P37.65b promotes; live_verification=true (OM-19)",
        artifact="lhci report against production",
    ),
    Leg(
        leg_id="live-tiles",
        stage="live",
        description=(
            "verify the SERVED tile archives: fetch tiles/index.json + the "
            "compartment archives from the public origin, then the same "
            "verifier the candidate leg ran"
        ),
        command="uv run sig-exports tiles verify --in <fetched-served-export>",
        precondition="P37.65b promotes; live_verification=true (OM-19)",
        artifact="reports/tiles_verify.json over the served bytes",
    ),
    Leg(
        leg_id="cost-7d",
        stage="live",
        description=(
            "the 7-day billing-export cost read for the map surface "
            "(K1 §9.6) — compares the post-promotion window against the "
            "declared ceiling"
        ),
        command="bq query <billing-export> — 7-day post-promotion window",
        precondition=(
            "≥7 days after P37.65b promotes AND the billing export exists; "
            "live_verification=true (OM-19)"
        ),
        artifact="cost row appended to the acceptance packet",
    ),
)

#: The committed machinery each deterministic leg names — `check` verifies
#: the paths exist so a renamed/missing leg file can never silently retire
#: an acceptance surface.
DETERMINISTIC_PATHS: tuple[tuple[str, str], ...] = (
    ("web/tests/e2e/map-journeys.spec.ts", "the J1–J10 battery"),
    ("web/playwright.journeys.config.ts", "the national journeys runner"),
    ("scripts/ci/national_budget_leg.sh", "the journeys leg carrier"),
    ("scripts/ci/tile_verify_leg.sh", "the tile-verification leg carrier"),
    ("web/lighthouserc.national.json", "the national Lighthouse matrix"),
    ("exports/src/exports/tile_verify.py", "the tile verifier"),
)


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops map-acceptance plan`` prints."""
    return {
        "schema": "sig.map-acceptance/1",
        "ticket": "P37.63",
        "catalog": "R11-K13-MAP-07",
        "posture": "prepared_not_executed",
        "production_mutations": "none",
        "gate": "publish rides P37.65 Class S — promotion is the operator's act",
        "rerun_prompt": RERUN_PROMPT,
        "legs": [asdict(lg) for lg in LEGS],
        "deterministic_paths": [p for p, _ in DETERMINISTIC_PATHS],
    }


def check() -> int:
    """Verify the committed machinery exists; never runs a leg."""
    missing = [(path, why) for path, why in DETERMINISTIC_PATHS if not (REPO_ROOT / path).exists()]
    for path, why in missing:
        print(f"map-acceptance check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "map-acceptance check: "
        f"{len(DETERMINISTIC_PATHS)} committed legs present; "
        f"{sum(1 for lg in LEGS if lg.stage != 'deterministic')} gated legs "
        "declared prepared_not_executed"
    )
    return 0


def run(leg_id: str) -> int:
    """Execute a deterministic leg; queue (exit 42) every gated leg."""
    leg = next((lg for lg in LEGS if lg.leg_id == leg_id), None)
    if leg is None:
        names = ", ".join(lg.leg_id for lg in LEGS)
        print(f"map-acceptance run: unknown leg '{leg_id}' (legs: {names})", file=sys.stderr)
        return 2
    if leg.stage != "deterministic":
        print(
            f"map-acceptance run: leg '{leg_id}' queues — "
            f"precondition: {leg.precondition}. Re-run prompt: {RERUN_PROMPT}",
            file=sys.stderr,
        )
        return 42
    if leg_id == "journeys-fixture":
        return subprocess.run(
            ["bash", "scripts/ci/national_budget_leg.sh", "journeys"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
    if leg_id == "budgets-fixture":
        for sub in ("budgets", "lighthouse"):
            rc = subprocess.run(
                ["bash", "scripts/ci/national_budget_leg.sh", sub],
                cwd=REPO_ROOT,
                check=False,
            ).returncode
            if rc != 0:
                return rc
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops map-acceptance",
        description=(
            "P37.63: the K1 MAP-07 map-acceptance leg declaration "
            "(prepared_not_executed for every candidate/live leg; the "
            "deterministic legs run in CI)."
        ),
    )
    sub = parser.add_subparsers(dest="map_acceptance_command", required=True)
    sub.add_parser("plan", help="print the leg declaration (offline)")
    sub.add_parser("check", help="verify the committed leg machinery exists (never runs a leg)")
    runp = sub.add_parser(
        "run",
        help="execute a deterministic leg; gated legs queue exit 42",
    )
    runp.add_argument("--leg", required=True, help="the leg id (see plan)")
    args = parser.parse_args(argv)
    if args.map_acceptance_command == "plan":
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.map_acceptance_command == "check":
        return check()
    if args.map_acceptance_command == "run":
        return run(args.leg)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
