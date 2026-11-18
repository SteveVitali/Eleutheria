# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.64 (K2 GX-10 + K6 VIZ-05, R11-K13-ACC-EXPLORE): the entity/graph/
dossier-figure acceptance leg declaration.

The ticket's job is an acceptance battery plus the Class S readout. Its
deterministic halves run in this dispatch — the SIG-UI-D20 identifier-label
crawl, the SIG-UI-DV01…DV12 emitted-route sweep, the J-1…J-6 and
VJ-1…VJ-6 labelled agent walkthroughs, the records-side parity chain, the
axe-in-interaction-states legs and the print-figure checks — all over the
committed fixtures and the emitted dist. The one leg that cannot run in an
engineering dispatch is declared here as ``prepared_not_executed``: the
post-promotion ``verify`` leg (`Live legs: 1: verify after P37.65b
promotes` — the plan cell, verbatim), which re-runs this battery against
the promoted public surface inside the `AR-3 + AR-2` window.

``sig-ops explore-acceptance plan`` prints the declaration offline;
``sig-ops explore-acceptance check`` verifies the committed machinery each
deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops explore-acceptance run --leg <id>`` executes a deterministic leg
and queues exit 42 on the gated leg — the named precondition (a promoted
site plus live_verification) is not met by declaration, never by probing
production.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The ticket's verbatim re-run prompt — the OM-19 form the deferred leg
#: names so the return pass needs no fresh operator text.
RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/492_P37.64__entity-graph-dossier-figure-acceptance.md "
    "live_verification=true"
)


@dataclass(frozen=True)
class Leg:
    """One acceptance leg — its command, the window that must open before it
    may run, and the artifact it writes."""

    leg_id: str
    stage: str  # "deterministic" | "live"
    description: str
    command: str
    precondition: str
    artifact: str


#: The committed leg list — order is the OM-19 execution order.
LEGS: tuple[Leg, ...] = (
    Leg(
        leg_id="dist-sweep",
        stage="deterministic",
        description=(
            "the emitted-route acceptance battery — SIG-UI-D20 legible-id "
            "crawl over every emitted page + overview `l` labels, and the "
            "SIG-UI-DV01…DV12 dossier-figure contract incl. the "
            "records-side parity chain (figure = twin = rollup = "
            "children Σ + placed_only_here = caption decomposition) and "
            "the print figure pages (web/tests/e2e/acceptance-explore.spec.ts)"
        ),
        command=("npx playwright test tests/e2e/acceptance-explore.spec.ts --project=chromium"),
        precondition="none — runs in the ordinary test:e2e pass and this dispatch",
        artifact="playwright run output; cited in the acceptance packet",
    ),
    Leg(
        leg_id="journeys",
        stage="deterministic",
        description=(
            "the labelled agent walkthroughs — K2 J-1…J-6, K6 VJ-1…VJ-6, "
            "the K13 §8 capstone legs (J2, J3, A3, O1), the in-place-map "
            "activation budget leg, and axe in the interaction states "
            "(web/tests/e2e/acceptance-explore-journeys.spec.ts)"
        ),
        command=(
            "npx playwright test tests/e2e/acceptance-explore-journeys.spec.ts --project=chromium"
        ),
        precondition="none — runs in the ordinary test:e2e pass and this dispatch",
        artifact="playwright run output; cited in the acceptance packet",
    ),
    Leg(
        leg_id="budgets",
        stage="deterministic",
        description=(
            "the page-type wire budgets incl. the activated in-place-map "
            "box (budget.spec.ts's scripted interaction per surface) over "
            "the real-sized national fixture build"
        ),
        command="bash scripts/ci/national_budget_leg.sh budgets",
        precondition="none — runs in CI (perf job); this dispatch cites it",
        artifact="budget.spec results incl. post-activation dossier cells",
    ),
    Leg(
        leg_id="live-verify",
        stage="live",
        description=(
            "the plan's `verify` leg — this battery re-run against the "
            "promoted public surface (the K13 §8 capstone journeys at real "
            "scale, the D20 crawl over the released bytes, the DV-parity "
            "chain at release, and the map-cells side of DV10 the fixture "
            "sites model cannot settle)"
        ),
        command=(
            "the re-run prompt below — the same spec files, "
            "SIG_LIVE_MAP_BASE/site origin pointed at the promoted surface"
        ),
        precondition=(
            "P37.65b promotes the release candidate; "
            "live_verification=true inside the `AR-3 + AR-2` window (OM-19)"
        ),
        artifact="paced run log + per-journey verdicts appended to the packet",
    ),
)

#: The committed machinery each deterministic leg names — `check` verifies
#: the paths exist so a renamed/missing leg file can never silently retire
#: an acceptance surface.
DETERMINISTIC_PATHS: tuple[tuple[str, str], ...] = (
    ("web/tests/e2e/acceptance-explore.spec.ts", "the D20 + DV01…DV12 emitted-route sweep"),
    ("web/tests/e2e/acceptance-explore-journeys.spec.ts", "the J/V journey battery"),
    ("web/tests/e2e/acceptance.ts", "the emitted-route + figure-region helpers"),
    ("scripts/ci/national_budget_leg.sh", "the budgets leg carrier"),
    ("web/tests/e2e/page-budgets.json", "the sig.page-budgets/1 contract"),
    ("docs/build/reports/p37.64-explore-acceptance/PACKET.md", "the Class S readout packet"),
)


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops explore-acceptance plan`` prints."""
    return {
        "schema": "sig.explore-acceptance/1",
        "ticket": "P37.64",
        "catalog": "R11-K13-ACC-EXPLORE",
        "posture": "prepared_not_executed",
        "production_mutations": "none",
        "gate": "Class S readout content folds into P37.65 — promotion is the operator's act",
        "rerun_prompt": RERUN_PROMPT,
        "legs": [asdict(lg) for lg in LEGS],
        "deterministic_paths": [p for p, _ in DETERMINISTIC_PATHS],
    }


def check() -> int:
    """Verify the committed machinery exists; never runs a leg."""
    missing = [(path, why) for path, why in DETERMINISTIC_PATHS if not (REPO_ROOT / path).exists()]
    for path, why in missing:
        print(f"explore-acceptance check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "explore-acceptance check: "
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
        print(f"explore-acceptance run: unknown leg '{leg_id}' (legs: {names})", file=sys.stderr)
        return 2
    if leg.stage != "deterministic":
        print(
            f"explore-acceptance run: leg '{leg_id}' queues — "
            f"precondition: {leg.precondition}. Re-run prompt: {RERUN_PROMPT}",
            file=sys.stderr,
        )
        return 42
    if leg_id == "dist-sweep":
        return subprocess.run(
            [
                "npx",
                "playwright",
                "test",
                "tests/e2e/acceptance-explore.spec.ts",
                "--project=chromium",
            ],
            cwd=REPO_ROOT / "web",
            check=False,
        ).returncode
    if leg_id == "journeys":
        return subprocess.run(
            [
                "npx",
                "playwright",
                "test",
                "tests/e2e/acceptance-explore-journeys.spec.ts",
                "--project=chromium",
            ],
            cwd=REPO_ROOT / "web",
            check=False,
        ).returncode
    if leg_id == "budgets":
        return subprocess.run(
            ["bash", "scripts/ci/national_budget_leg.sh", "budgets"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops explore-acceptance",
        description=(
            "P37.64: the K2 GX-10 + K6 VIZ-05 acceptance leg declaration "
            "(prepared_not_executed for the live verify leg; the "
            "deterministic legs run in CI and this dispatch)."
        ),
    )
    sub = parser.add_subparsers(dest="explore_acceptance_command", required=True)
    sub.add_parser("plan", help="print the leg declaration as JSON")
    sub.add_parser("check", help="verify the committed machinery exists")
    r = sub.add_parser("run", help="execute a deterministic leg")
    r.add_argument("--leg", required=True, choices=[lg.leg_id for lg in LEGS])
    args = parser.parse_args(argv)
    if args.explore_acceptance_command == "plan":
        print(json.dumps(plan(), indent=2))
        return 0
    if args.explore_acceptance_command == "check":
        return check()
    if args.explore_acceptance_command == "run":
        return run(args.leg)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
