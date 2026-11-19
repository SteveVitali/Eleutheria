# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.68c (R11-K13-CAP-01, split c): the organizer-capstone leg declaration.

The ticket's job — D3's journeys O1–O4 × {390, 1440 px} × {JS on, JS off
where the journey allows} on the promoted release — is a *leg set*: the
deterministic halves run in this dispatch (the O1–O4 battery over the
committed fixtures build at all four viewport/JS cells; the committed
spend-ledger read against the $300/month ceiling), and the halves that can
only run against the promoted release or inside an operator act are
declared here as ``prepared_not_executed`` legs — the same posture the
advocate/journalist-capstone and map-acceptance machinery carries (a
fixture green is never a live, hosted or public pass; agent-verified is
never user-tested).

Leg ordering follows K13 §8 and OM-19:

* ``journeys-fixture`` runs now: the O1–O4 battery
  (``web/tests/e2e/capstone-organizer.spec.ts``) at all four
  {1440, 390} × {JS, no-JS} project cells against the built fixtures dist.
* ``cost-ledger`` runs now: the deterministic committed-ledger half of the
  UXR-31 / SIG-UI-081 serving-cost read — the committed spend ledger's
  latest month against the $300/month ceiling, labelled honestly
  (``measured`` / ``operator-reported`` / ``estimate`` / ``pending``).
* ``live-journeys`` queues on P37.65b promoting: the same battery with
  ``SIG_CAPSTONE_BASE_URL=<promoted-origin>``. Journey-specific gates ride
  inside it: O1's "named agencies" reading follows the release's own
  placement/publication state (I8 placement, D-K2-1 organisation
  publication — the typed absence is a legitimate pass state, never a
  smoothed figure); O3's "licence and attribution per compartment"
  reading rides ACT-07 (the attribution re-export — K13 §7.4 orders it
  before any download link); O4's "where to send results" is the
  operator-named channel settled by D-K11-4.
* ``cost-read`` queues on the billing export holding rows for the
  promoted-release window — SIG-UI-081's measured read, never an estimate
  passed off as billing.
* ``walkthrough`` is the OP-22 operator walkthrough of O1–O4 —
  *requested, never simulated*; the packet
  (``docs/build/reports/p37.68c-capstone/WALKTHROUGH.md``) is committed and
  the walkthrough itself is the operator's act, recorded
  "operator walkthrough (maintainer, not independent)".

``sig-ops capstone-organizer plan`` prints the declaration offline;
``sig-ops capstone-organizer check`` verifies the *committed* machinery
each deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops capstone-organizer run --leg <id>`` executes a deterministic leg
and queues exit 42 on every gated leg — the named precondition (a promoted
release, a billing-export window, an operator act) is not met by
declaration, never by probing production.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from ops.capstone_advocate import cost_ledger_read as _advocate_cost_ledger_read

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEND_LEDGER = REPO_ROOT / "docs/build/reports/spend/spend_ledger.csv"

#: The ticket's verbatim re-run prompt — the OM-19 form the deferred legs
#: name so the return pass needs no fresh operator text.
RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/499_P37.68c__ux-capstone-organizer-journeys.md "
    "live_verification=true"
)


@dataclass(frozen=True)
class Leg:
    """One capstone leg — its command, the window that must open before it
    may run, and the artifact it writes."""

    leg_id: str
    stage: str  # "deterministic" | "live" | "operator"
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
            "the O1–O4 capstone journey battery over the committed fixtures "
            "build at all four {1440, 390 px} × {JS on, JS off} project cells "
            "(web/tests/e2e/capstone-organizer.spec.ts under "
            "playwright.capstone-organizer.config.ts; also runs inside the "
            "ordinary test:e2e pass under committed fixtures)"
        ),
        command=(
            "npm --prefix web run build && cd web && "
            "npx playwright test -c playwright.capstone-organizer.config.ts"
        ),
        precondition="none — runs in this dispatch and any local check",
        artifact=(
            "web/test-results/capstone-organizer.json (playwright json "
            "reporter); cited in the capstone packet"
        ),
    ),
    Leg(
        leg_id="cost-ledger",
        stage="deterministic",
        description=(
            "the deterministic committed-ledger half of the UXR-31 / "
            "SIG-UI-081 serving-cost read — the committed spend ledger's "
            "latest month against the $300/month ceiling, every figure "
            "labelled measured / operator-reported / estimate / pending "
            "(never an estimate passed off as billing)"
        ),
        command="sig-ops capstone-organizer run --leg cost-ledger",
        precondition="none — reads committed records only",
        artifact=("a sig.capstone-cost-read/1 stdout record; cited in the capstone packet"),
    ),
    Leg(
        leg_id="live-journeys",
        stage="live",
        description=(
            "O1–O4 on the promoted release — the same battery file and "
            "config, SIG_CAPSTONE_BASE_URL pointing at the promoted "
            "origin; recorded agent-verified (never 'user-tested'). "
            "Inside it O1's named-agencies reading follows the release's "
            "placement/publication state (I8, D-K2-1 — a typed absence is "
            "a legitimate pass), O3's per-compartment attribution reading "
            "rides ACT-07, and O4's named channel is settled by D-K11-4"
        ),
        command=(
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone-organizer.config.ts"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1 — the operator's "
            "HG-11 act) AND live_verification=true (OM-19); O3's "
            "attribution reading additionally rides ACT-07 (the "
            "attribution re-export — K13 §7.4); O2's agenda items ride "
            "the WX-02/03 producers; O4's named channel is settled per "
            "D-K11-4"
        ),
        artifact="paced run log + per-leg verdicts appended to the packet",
    ),
    Leg(
        leg_id="cost-read",
        stage="live",
        description=(
            "the SIG-UI-081 / UXR-31 serving-cost read — the UX serving "
            "cost (map sessions, tiles, search queries, downloads egress) "
            "from the billing export against the $300/month ceiling"
        ),
        command="bq query <billing-export> — the promoted-release window",
        precondition=(
            "the billing export holds rows for the promoted-release window "
            "(D-P34.5-2 export link) AND live_verification=true (OM-19)"
        ),
        artifact="cost row appended to the capstone packet + spend ledger",
    ),
    Leg(
        leg_id="walkthrough",
        stage="operator",
        description=(
            "the OP-22 operator walkthrough of O1–O4 at 390 + 1440 px on "
            "the promoted release — 'operator walkthrough (maintainer, not "
            "independent)' (TS-22); REQUESTED, never simulated — the "
            "packet is committed, the walkthrough is the operator's act"
        ),
        command=(
            "operator walks docs/build/reports/p37.68c-capstone/"
            "WALKTHROUGH.md on the promoted release"
        ),
        precondition=(
            "the promoted release exists AND the operator walks it — never "
            "an agent act (OP-22, TS-22)"
        ),
        artifact="the operator's own recorded walkthrough (maintainer, not independent)",
    ),
)

#: The committed machinery each deterministic leg names — `check` verifies
#: the paths exist so a renamed/missing leg file can never silently retire
#: a capstone surface.
DETERMINISTIC_PATHS: tuple[tuple[str, str], ...] = (
    ("web/tests/e2e/capstone-organizer.spec.ts", "the O1–O4 battery"),
    ("web/playwright.capstone-organizer.config.ts", "the capstone runner"),
    (
        "docs/build/reports/p37.68c-capstone/PACKET.md",
        "the capstone packet",
    ),
    (
        "docs/build/reports/p37.68c-capstone/WALKTHROUGH.md",
        "the operator walkthrough packet",
    ),
    (
        "docs/build/reports/spend/spend_ledger.csv",
        "the committed spend ledger the cost-ledger leg reads",
    ),
)


def cost_ledger_read() -> dict[str, object]:
    """The deterministic committed-ledger cost read (``cost-ledger`` leg).

    Shares the advocate split's reader — the ledger and the $300/month
    ceiling are the same contract; only the ``ticket``/``leg`` labels are
    re-stamped so the emitted record names the run that produced it.
    """

    doc = _advocate_cost_ledger_read()
    doc["ticket"] = "P37.68c"
    doc["leg"] = "cost-ledger"
    return doc


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops capstone-organizer plan`` prints."""
    return {
        "schema": "sig.capstone-organizer/1",
        "ticket": "P37.68c",
        "catalog": "R11-K13-CAP-01",
        "split": (
            "c — organizer journeys O1–O4 (a: A1–A4 landed P37.68a, "
            "b: J1–J5 landed P37.68b, d: per-ask checks/budgets/axe/"
            "cost/packet)"
        ),
        "posture": "prepared_not_executed",
        "production_mutations": "none",
        "gate": "publish rides P37.65 Class S — promotion is the operator's act",
        "journeys": ["O1", "O2", "O3", "O4"],
        "cells": ["1440-js", "390-js", "1440-nojs", "390-nojs"],
        "labels": ["agent-verified", "never user-tested"],
        "journey_gates": {
            "O1": (
                "the named-agencies reading follows the release's own "
                "placement/publication state (I8 placement, D-K2-1 "
                "organisation publication — K13 §4.2); the typed absence "
                "is a legitimate pass state"
            ),
            "O2": (
                "approving body and next date ride the WX-02/03 agenda "
                "producers; the feed validates and exists even at 0 items"
            ),
            "O3": (
                "the per-compartment licence/attribution reading rides "
                "ACT-07 — the attribution re-export (K13 §7.4 orders it "
                "before any download link)"
            ),
            "O4": (
                "the where-to-send-results channel is the operator-named "
                "one — D-K11-4 (settled); the page never invents one"
            ),
        },
        "rerun_prompt": RERUN_PROMPT,
        "legs": [asdict(lg) for lg in LEGS],
        "deterministic_paths": [p for p, _ in DETERMINISTIC_PATHS],
    }


def check() -> int:
    """Verify the committed machinery exists; never runs a leg."""
    missing = [(path, why) for path, why in DETERMINISTIC_PATHS if not (REPO_ROOT / path).exists()]
    for path, why in missing:
        print(f"capstone-organizer check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "capstone-organizer check: "
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
        print(f"capstone-organizer run: unknown leg '{leg_id}' (legs: {names})", file=sys.stderr)
        return 2
    if leg.stage != "deterministic":
        print(
            f"capstone-organizer run: leg '{leg_id}' queues — "
            f"precondition: {leg.precondition}. Re-run prompt: {RERUN_PROMPT}",
            file=sys.stderr,
        )
        return 42
    if leg_id == "journeys-fixture":
        build = subprocess.run(
            ["npm", "--prefix", "web", "run", "build"],
            cwd=REPO_ROOT,
            check=False,
        )
        if build.returncode != 0:
            return build.returncode
        return subprocess.run(
            [
                "npx",
                "playwright",
                "test",
                "-c",
                "playwright.capstone-organizer.config.ts",
            ],
            cwd=REPO_ROOT / "web",
            check=False,
        ).returncode
    if leg_id == "cost-ledger":
        print(json.dumps(cost_ledger_read(), indent=2, sort_keys=True))
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops capstone-organizer",
        description=(
            "P37.68c: the K13 §8 capstone organizer-journeys (O1–O4) leg "
            "declaration — prepared_not_executed for every live/operator "
            "leg; the deterministic legs run in this dispatch."
        ),
    )
    sub = parser.add_subparsers(dest="capstone_organizer_command", required=True)
    sub.add_parser("plan", help="print the leg declaration (offline)")
    sub.add_parser("check", help="verify the committed leg machinery exists (never runs a leg)")
    runp = sub.add_parser(
        "run",
        help="execute a deterministic leg; gated legs queue exit 42",
    )
    runp.add_argument("--leg", required=True, help="the leg id (see plan)")
    args = parser.parse_args(argv)
    if args.capstone_organizer_command == "plan":
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.capstone_organizer_command == "check":
        return check()
    if args.capstone_organizer_command == "run":
        return run(args.leg)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
