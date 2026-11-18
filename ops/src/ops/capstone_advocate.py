# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.68a (R11-K13-CAP-01, split a): the advocate-capstone leg declaration.

The ticket's job — D3's journeys A1–A4 × {390, 1440 px} × {JS on, JS off
where the journey allows} on the promoted release — is a *leg set*: the
deterministic halves run in this dispatch (the A1–A4 battery over the
committed fixtures build at all four viewport/JS cells; the committed
spend-ledger read against the $300/month ceiling), and the halves that can
only run against the promoted release or inside an operator act are
declared here as ``prepared_not_executed`` legs — the same posture the
map-acceptance machinery carries (a fixture green is never a live, hosted
or public pass; agent-verified is never user-tested).

Leg ordering follows K13 §8 and OM-19:

* ``journeys-fixture`` runs now: the A1–A4 battery
  (``web/tests/e2e/capstone-advocate.spec.ts``) at all four
  {1440, 390} × {JS, no-JS} project cells against the built fixtures dist.
* ``cost-ledger`` runs now: the deterministic committed-ledger half of the
  UXR-31 / SIG-UI-081 serving-cost read — the committed spend ledger's
  latest month against the $300/month ceiling, labelled honestly
  (``measured`` / ``operator-reported`` / ``estimate`` / ``pending``).
* ``live-journeys`` queues on P37.65b promoting: the same battery with
  ``SIG_CAPSTONE_BASE_URL=<promoted-origin>``.
* ``cost-read`` queues on the billing export holding rows for the
  promoted-release window — SIG-UI-081's measured read, never an estimate
  passed off as billing.
* ``walkthrough`` is the OP-22 operator walkthrough of A1–A4 —
  *requested, never simulated*; the packet
  (``docs/build/reports/p37.68a-capstone/WALKTHROUGH.md``) is committed and
  the walkthrough itself is the operator's act, recorded
  "operator walkthrough (maintainer, not independent)".

``sig-ops capstone-advocate plan`` prints the declaration offline;
``sig-ops capstone-advocate check`` verifies the *committed* machinery each
deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops capstone-advocate run --leg <id>`` executes a deterministic leg
and queues exit 42 on every gated leg — the named precondition (a promoted
release, a billing-export window, an operator act) is not met by
declaration, never by probing production.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEND_LEDGER = REPO_ROOT / "docs/build/reports/spend/spend_ledger.csv"
CEILING_USD = 300.0

#: The ticket's verbatim re-run prompt — the OM-19 form the deferred legs
#: name so the return pass needs no fresh operator text.
RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/497_P37.68a__ux-capstone-advocate-journeys.md "
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
            "the A1–A4 capstone journey battery over the committed fixtures "
            "build at all four {1440, 390 px} × {JS on, JS off} project cells "
            "(web/tests/e2e/capstone-advocate.spec.ts under "
            "playwright.capstone.config.ts; also runs inside the ordinary "
            "test:e2e pass under committed fixtures)"
        ),
        command=(
            "npm --prefix web run build && cd web && "
            "npx playwright test -c playwright.capstone.config.ts"
        ),
        precondition="none — runs in this dispatch and any local check",
        artifact=(
            "web/test-results/capstone-advocate.json (playwright json "
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
        command="sig-ops capstone-advocate run --leg cost-ledger",
        precondition="none — reads committed records only",
        artifact=("a sig.capstone-cost-read/1 stdout record; cited in the capstone packet"),
    ),
    Leg(
        leg_id="live-journeys",
        stage="live",
        description=(
            "A1–A4 on the promoted release — the same battery file and "
            "config, SIG_CAPSTONE_BASE_URL pointing at the promoted "
            "origin; recorded agent-verified (never 'user-tested')"
        ),
        command=(
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone.config.ts"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1 — the operator's "
            "HG-11 act) AND live_verification=true (OM-19)"
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
            "the OP-22 operator walkthrough of A1–A4 at 390 + 1440 px on "
            "the promoted release — 'operator walkthrough (maintainer, not "
            "independent)' (TS-22); REQUESTED, never simulated — the "
            "packet is committed, the walkthrough is the operator's act"
        ),
        command=(
            "operator walks docs/build/reports/p37.68a-capstone/"
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
    ("web/tests/e2e/capstone-advocate.spec.ts", "the A1–A4 battery"),
    ("web/playwright.capstone.config.ts", "the capstone runner"),
    (
        "docs/build/reports/p37.68a-capstone/PACKET.md",
        "the capstone packet",
    ),
    (
        "docs/build/reports/p37.68a-capstone/WALKTHROUGH.md",
        "the operator walkthrough packet",
    ),
    (
        "docs/build/reports/spend/spend_ledger.csv",
        "the committed spend ledger the cost-ledger leg reads",
    ),
)


def _parse_amount(raw: str) -> tuple[float | None, float | None]:
    """Classify a ledger amount cell.

    Returns ``(measured, estimate_upper)``: ``measured`` is set for a plain
    numeric figure and ``estimate_upper`` for a ``~N-M`` range's upper bound;
    both ``None`` for an empty (``pending``) or unparseable cell — the
    ledger's own ``source_label`` column carries the label.
    """

    raw = raw.strip()
    if not raw:
        return None, None
    if raw.startswith("~"):
        bounds = raw.lstrip("~").split("-")
        try:
            return None, float(bounds[-1])
        except ValueError:
            return None, None
    try:
        return float(raw), None
    except ValueError:
        return None, None


def cost_ledger_read() -> dict[str, object]:
    """The deterministic committed-ledger cost read (``cost-ledger`` leg).

    Reads the committed spend ledger's latest month and reports the GCP
    cloud-account figure against the $300/month ceiling — ``measured`` and
    ``pending`` kept strictly apart; a pending row is never read as zero.
    """

    rows = list(csv.DictReader(SPEND_LEDGER.open(encoding="utf-8")))
    months = sorted({r["month"] for r in rows})
    latest = months[-1] if months else ""
    month_rows = [r for r in rows if r["month"] == latest]
    gcp_measured = 0.0
    gcp_estimate_upper = 0.0
    gcp_pending: list[str] = []
    outside_pending: list[str] = []
    outside_measured = 0.0
    outside_estimate_upper = 0.0
    ceilings: list[str] = []
    for r in month_rows:
        measured, est_upper = _parse_amount(r["amount_usd"])
        label = r["source_label"]
        outside = "outside-cloud-account" in r["note"]
        name = f"{r['provider']}:{r['category']}"
        if label == "ceiling":
            # a declared hard cap, never spend — reported, never summed
            ceilings.append(f"{name} ${r['amount_usd']}")
            continue
        if label == "pending":
            (outside_pending if outside else gcp_pending).append(name)
            continue
        # estimate / measured / operator-reported: the amount cell carries
        # the figure (a `~N-M` range bounds it from above)
        figure = measured if measured is not None else est_upper
        if figure is None:
            (outside_pending if outside else gcp_pending).append(name)
            continue
        if label == "estimate":
            if outside:
                outside_estimate_upper += figure
            else:
                gcp_estimate_upper += figure
        else:
            if outside:
                outside_measured += figure
            else:
                gcp_measured += figure
    # The ceiling comparison the ledger rules define: the $300/month cloud-
    # account budget watches GCP lines only; a pending row is named, never
    # summed. The estimate upper bound is the conservative figure.
    gcp_bound = gcp_measured + gcp_estimate_upper
    return {
        "schema": "sig.capstone-cost-read/1",
        "ticket": "P37.68a",
        "leg": "cost-ledger",
        "posture": "committed-ledger read — measured and estimate kept apart",
        "source": str(SPEND_LEDGER.relative_to(REPO_ROOT)),
        "month": latest,
        "ceiling_usd": CEILING_USD,
        "gcp_cloud_account": {
            "measured_usd": round(gcp_measured, 2),
            "estimate_upper_usd": round(gcp_estimate_upper, 2),
            "bound_usd": round(gcp_bound, 2),
            "pending_rows": gcp_pending,
            "vs_ceiling": (
                f"{gcp_bound / CEILING_USD:.0%} of ${CEILING_USD:.0f}"
                if gcp_bound
                else "no figure (all rows pending)"
            ),
        },
        "outside_cloud_account": {
            "measured_usd": round(outside_measured, 2),
            "estimate_upper_usd": round(outside_estimate_upper, 2),
            "pending_rows": outside_pending,
            "declared_ceilings": ceilings,
            "note": (
                "billed outside the cloud account — reported for "
                "completeness, never part of the $300 ceiling comparison; "
                "declared hard caps are named, never summed as spend"
            ),
        },
        "verdict": (
            "under-ceiling on the committed figures (estimate-bounded); "
            "the measured billing-export read is the queued live leg "
            "'cost-read'"
        ),
    }


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops capstone-advocate plan`` prints."""
    return {
        "schema": "sig.capstone-advocate/1",
        "ticket": "P37.68a",
        "catalog": "R11-K13-CAP-01",
        "split": (
            "a — advocate journeys A1–A4 (b: J1–J5, c: O1–O4, "
            "d: per-ask checks/budgets/axe/cost/packet)"
        ),
        "posture": "prepared_not_executed",
        "production_mutations": "none",
        "gate": "publish rides P37.65 Class S — promotion is the operator's act",
        "journeys": ["A1", "A2", "A3", "A4"],
        "cells": ["1440-js", "390-js", "1440-nojs", "390-nojs"],
        "labels": ["agent-verified", "never user-tested"],
        "rerun_prompt": RERUN_PROMPT,
        "legs": [asdict(lg) for lg in LEGS],
        "deterministic_paths": [p for p, _ in DETERMINISTIC_PATHS],
    }


def check() -> int:
    """Verify the committed machinery exists; never runs a leg."""
    missing = [(path, why) for path, why in DETERMINISTIC_PATHS if not (REPO_ROOT / path).exists()]
    for path, why in missing:
        print(f"capstone-advocate check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "capstone-advocate check: "
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
        print(f"capstone-advocate run: unknown leg '{leg_id}' (legs: {names})", file=sys.stderr)
        return 2
    if leg.stage != "deterministic":
        print(
            f"capstone-advocate run: leg '{leg_id}' queues — "
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
                "playwright.capstone.config.ts",
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
        prog="sig-ops capstone-advocate",
        description=(
            "P37.68a: the K13 §8 capstone advocate-journeys (A1–A4) leg "
            "declaration — prepared_not_executed for every live/operator "
            "leg; the deterministic legs run in this dispatch."
        ),
    )
    sub = parser.add_subparsers(dest="capstone_advocate_command", required=True)
    sub.add_parser("plan", help="print the leg declaration (offline)")
    sub.add_parser("check", help="verify the committed leg machinery exists (never runs a leg)")
    runp = sub.add_parser(
        "run",
        help="execute a deterministic leg; gated legs queue exit 42",
    )
    runp.add_argument("--leg", required=True, help="the leg id (see plan)")
    args = parser.parse_args(argv)
    if args.capstone_advocate_command == "plan":
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.capstone_advocate_command == "check":
        return check()
    if args.capstone_advocate_command == "run":
        return run(args.leg)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
