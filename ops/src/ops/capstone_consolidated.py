# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.68d (R11-K13-CAP-01, split d — the consolidated row): the
per-ask-checks + consolidated-packet leg declaration.

This row owns the SIG-UI-077 / SIG-UI-078 verdict home (COVERAGE_MATRIX rows
848/849 route here — P37.68a landed the harness, this row owns the
acceptance sweep). Its job is a *leg set*: the deterministic halves run in
this dispatch (the U-003.1…U-003.11 per-ask battery over the committed
fixtures build at all four viewport/JS cells; the ROUTES.csv advertised-
route check over the emitted build; the page-type budgets + axe WCAG 2.2 AA
sweeps over the emitted build; the committed spend-ledger read against the
$300/month ceiling), and the halves that can only run against the promoted
release or inside an operator act are declared here as
``prepared_not_executed`` legs — the same posture the sibling splits carry
(a fixture green is never a live, hosted or public pass; agent-verified is
never user-tested).

Leg ordering follows K13 §5.1/§8, S4c (COV-04) and OM-19:

* ``per-ask-fixture`` runs now: the U-003.1…11 battery
  (``web/tests/e2e/capstone-per-ask.spec.ts``) at all four
  {1440, 390} × {JS, no-JS} project cells against the built fixtures dist.
* ``routes-csv-dist`` runs now: the ROUTES.csv advertised-route check
  (``acceptance-routes-csv.spec.ts`` — P36.72a/COV-04) over the emitted
  build; every advertised row resolves, retires through the one redirect
  generator, or shows its honest notice.
* ``budgets-axe-fixture`` runs now: the page-type budget wire sweep
  (``budget.spec.ts``, sig.page-budgets/1) and the axe WCAG 2.2 AA sweep
  (``a11y*.spec.ts``) over the emitted build.
* ``cost-ledger`` runs now: the deterministic committed-ledger half of the
  UXR-31 / SIG-UI-081 serving-cost read — the committed spend ledger's
  latest month against the $300/month ceiling, labelled honestly
  (``measured`` / ``operator-reported`` / ``estimate`` / ``pending``).
* ``live-per-ask`` queues on P37.65b promoting: the same per-ask battery
  with ``SIG_CAPSTONE_BASE_URL=<promoted-origin>`` — SIG-UI-077's named
  live acceptance checks, including the corpus-named clauses the fixture
  cannot read (the release's own source-row count, Austin Police
  Department, California's per-source breakdown, Seattle watch pages,
  Canberra/ICE/Vigilant query behaviour, the tile verifier's 0-missing at
  every zoom, the benchmark top-3 rates).
* ``live-journeys`` queues on P37.65b promoting: the consolidated
  13-journey battery (SIG-UI-078) — the three sibling spec files
  (capstone-advocate/-journalist/-organizer) at all four cells against the
  promoted origin; J4's durable ``/s/<pub>/`` half rides ACT-24 (HG-11) and
  J5's real ≥ 2-release diff rides the activated predecessor.
* ``live-routes-csv`` queues on P37.65b promoting: the ROUTES.csv
  re-check on the final release (S4c/COV-04) — the emitted-route check
  bound to the promoted bundle's own page-types manifest + redirects.conf,
  its ``external`` rows probed against the deployment URLs.
* ``live-budgets-axe`` queues on P37.65b promoting: budgets + axe on the
  real release — the discovered-route sweeps bound to the promoted
  bundle's manifest (page-type budgets all types; WCAG 2.2 AA).
* ``cost-read`` queues on the billing export holding rows for the
  promoted-release window — SIG-UI-081's measured read, never an estimate
  passed off as billing.
* ``walkthrough`` is the OP-22 consolidated operator walkthrough —
  *requested, never simulated*; the packet
  (``docs/build/reports/p37.68d-capstone/WALKTHROUGH.md``) covers all 13
  journeys + the per-ask surface and is committed; the walkthrough itself
  is the operator's act, recorded "operator walkthrough (maintainer, not
  independent)" (TS-22).

``sig-ops capstone-consolidated plan`` prints the declaration offline;
``sig-ops capstone-consolidated check`` verifies the *committed* machinery
each deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops capstone-consolidated run --leg <id>`` executes a deterministic
leg and queues exit 42 on every gated leg — the named precondition (a
promoted release, a billing-export window, an operator act) is not met by
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
    "spec=docs/tickets/500_P37.68d__ux-capstone-per-ask-checks-and-walkthrough-packet.md "
    "live_verification=true"
)

#: The K13 §5.1 asks this row's battery names — SIG-UI-077's "named
#: acceptance check per ask".
PER_ASK_CHECKS: tuple[str, ...] = (
    "U-003.1",
    "U-003.2",
    "U-003.3",
    "U-003.4",
    "U-003.5",
    "U-003.6",
    "U-003.7",
    "U-003.8",
    "U-003.9",
    "U-003.10",
    "U-003.11",
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
        leg_id="per-ask-fixture",
        stage="deterministic",
        description=(
            "the U-003.1…U-003.11 per-ask acceptance battery "
            "(SIG-UI-077; K13 §5.1's named live-check column) over the "
            "committed fixtures build at all four {1440, 390 px} × "
            "{JS on, JS off} project cells "
            "(web/tests/e2e/capstone-per-ask.spec.ts under "
            "playwright.capstone-consolidated.config.ts; also runs inside "
            "the ordinary test:e2e pass under committed fixtures)"
        ),
        command=(
            "npm --prefix web run build && cd web && "
            "npx playwright test -c playwright.capstone-consolidated.config.ts"
        ),
        precondition="none — runs in this dispatch and any local check",
        artifact=(
            "web/test-results/capstone-per-ask.json (playwright json "
            "reporter); cited in the capstone packet"
        ),
    ),
    Leg(
        leg_id="routes-csv-dist",
        stage="deterministic",
        description=(
            "the ROUTES.csv advertised-route check over the emitted build "
            "(P36.72a / S4c COV-04): every route advertised on the 09-27 "
            "release resolves, retires through the one redirect generator, "
            "or shows its honest notice — the expectation table is a "
            "bijection with the CSV"
        ),
        command=("cd web && npx playwright test acceptance-routes-csv.spec.ts"),
        precondition="none — runs in this dispatch and any local check",
        artifact=(
            "the spec's per-disposition assertions (web/test-results/); "
            "cited in the capstone packet"
        ),
    ),
    Leg(
        leg_id="budgets-axe-fixture",
        stage="deterministic",
        description=(
            "the page-type budget wire sweep (budget.spec.ts — "
            "sig.page-budgets/1, all page types, gzip + brotli, before and "
            "after one scripted interaction per surface) and the axe "
            "WCAG 2.2 AA sweep (a11y*.spec.ts) over the emitted build"
        ),
        command=(
            "cd web && npx playwright test budget.spec.ts a11y.spec.ts a11y-scripts-off.spec.ts"
        ),
        precondition="none — runs in this dispatch and any local check",
        artifact=("the sweep pass lines + web/test-results/; cited in the capstone packet"),
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
        command="sig-ops capstone-consolidated run --leg cost-ledger",
        precondition="none — reads committed records only",
        artifact=("a sig.capstone-cost-read/1 stdout record; cited in the capstone packet"),
    ),
    Leg(
        leg_id="live-per-ask",
        stage="live",
        description=(
            "U-003.1…U-003.11 on the promoted release (SIG-UI-077) — the "
            "same battery file and config, SIG_CAPSTONE_BASE_URL pointing "
            "at the promoted origin; recorded agent-verified (never "
            "'user-tested'). Inside it the corpus-named clauses read the "
            "release's own corpus: the sources-table row count, Austin "
            "Police Department + Vigilant Solutions (LEARN) named with "
            "pages-or-typed-absences (D-K2-1 state), California's "
            "per-source breakdown summing to the figure, Seattle watch "
            "pages, Canberra/ICE/Vigilant query behaviour, the tile "
            "verifier's 0-missing at every zoom, and the benchmark top-3 "
            "rates — none are claimed from the fixture corpus"
        ),
        command=(
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone-consolidated.config.ts"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1 — the operator's "
            "HG-11 act) AND live_verification=true (OM-19); the "
            "corpus-named clauses ride the release's own published corpus "
            "(I8 placement, D-K2-1 organisation publication, D-K3-7 "
            "held-out set) — a typed absence is a legitimate pass state"
        ),
        artifact="paced run log + per-ask verdicts appended to the packet",
    ),
    Leg(
        leg_id="live-journeys",
        stage="live",
        description=(
            "the consolidated 13-journey battery on the promoted release "
            "(SIG-UI-078): A1–A4, J1–J5, O1–O4 through the three sibling "
            "spec files at all four {1440, 390 px} × {JS, no-JS} cells — "
            "the sibling splits' deferred live legs (D-P37.68a-1, "
            "D-P37.68b-1, D-P37.68c-1) this row records the sweep verdict "
            "for; inside it J4's durable /s/<pub>/ half rides ACT-24 "
            "(HG-11), J5's real ≥ 2-release diff rides the activated "
            "predecessor, O1 rides I8/D-K2-1, O3 ACT-07, O4 D-K11-4"
        ),
        command=(
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone.config.ts && "
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone-journalist.config.ts && "
            "SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test "
            "-c playwright.capstone-organizer.config.ts"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1) AND "
            "live_verification=true (OM-19); J4's durable half rides "
            "ACT-24 (HG-11), J5's diff rides the activated predecessor "
            "release; O3's attribution reading rides ACT-07; O1's "
            "named-agencies reading follows I8/D-K2-1; O4's channel is "
            "settled per D-K11-4"
        ),
        artifact="paced run log + the consolidated journey verdict table appended to the packet",
    ),
    Leg(
        leg_id="live-routes-csv",
        stage="live",
        description=(
            "the ROUTES.csv advertised-route check repeated on the final "
            "release (S4c / COV-04): the promoted web bundle staged as the "
            "build (its own page-types.json + redirects.conf), the same "
            "emitted-route check re-run against it, and the disposition "
            "table's 'external' rows probed against the deployment URLs "
            "the release advertises"
        ),
        command=(
            "stage the promoted bundle at web/dist && cd web && "
            "npx playwright test acceptance-routes-csv.spec.ts (+ the "
            "external-row probes the bundle names)"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1) AND its web "
            "bundle + deployment endpoints are fetchable AND "
            "live_verification=true (OM-19)"
        ),
        artifact="per-row dispositions appended to the packet",
    ),
    Leg(
        leg_id="live-budgets-axe",
        stage="live",
        description=(
            "budgets and axe on the real release: the discovered-route "
            "wire sweep (page-type budgets all types, gzip + brotli, "
            "before/after one scripted interaction per surface) and the "
            "axe WCAG 2.2 AA sweep bound to the promoted bundle's own "
            "page-types manifest — measured over the release's bytes, "
            "never the fixture's"
        ),
        command=(
            "stage the promoted bundle at web/dist && cd web && "
            "npx playwright test budget.spec.ts a11y.spec.ts "
            "a11y-scripts-off.spec.ts"
        ),
        precondition=(
            "the P37.65 release is promoted (D-P37.65b-1) AND its web "
            "bundle is fetchable AND live_verification=true (OM-19)"
        ),
        artifact="the measured budget table + axe verdict appended to the packet",
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
            "the OP-22 consolidated operator walkthrough of all 13 "
            "journeys + the per-ask surface at 390 + 1440 px on the "
            "promoted release — 'operator walkthrough (maintainer, not "
            "independent)' (TS-22); REQUESTED, never simulated — the "
            "packet is committed, the walkthrough is the operator's act"
        ),
        command=(
            "operator walks docs/build/reports/p37.68d-capstone/"
            "WALKTHROUGH.md on the promoted release"
        ),
        precondition=(
            "the promoted release exists AND the operator walks it — never "
            "an agent act (OP-22, TS-22)"
        ),
        artifact="the operator's own recorded walkthrough (maintainer, not independent)",
    ),
)

#: The committed machinery each leg names — `check` verifies the paths
#: exist so a renamed/missing leg file can never silently retire a
#: capstone surface.
DETERMINISTIC_PATHS: tuple[tuple[str, str], ...] = (
    ("web/tests/e2e/capstone-per-ask.spec.ts", "the U-003.1…11 battery"),
    ("web/playwright.capstone-consolidated.config.ts", "the per-ask runner"),
    ("web/tests/e2e/capstone-advocate.spec.ts", "the A1–A4 battery (live-journeys)"),
    ("web/tests/e2e/capstone-journalist.spec.ts", "the J1–J5 battery (live-journeys)"),
    ("web/tests/e2e/capstone-organizer.spec.ts", "the O1–O4 battery (live-journeys)"),
    ("web/playwright.capstone.config.ts", "the A1–A4 runner"),
    ("web/playwright.capstone-journalist.config.ts", "the J1–J5 runner"),
    ("web/playwright.capstone-organizer.config.ts", "the O1–O4 runner"),
    ("web/tests/e2e/acceptance-routes-csv.spec.ts", "the ROUTES.csv check"),
    (
        "docs/build/planning/2026-09-30-next-phase/review/ROUTES.csv",
        "the 09-27 advertised-route manifest",
    ),
    ("web/tests/e2e/budget.spec.ts", "the page-type budget sweep"),
    ("web/tests/e2e/page-budgets.json", "the sig.page-budgets/1 ceilings"),
    ("web/tests/e2e/a11y.spec.ts", "the axe WCAG 2.2 AA sweep"),
    ("web/tests/e2e/a11y-scripts-off.spec.ts", "the scripts-off axe sweep"),
    (
        "docs/build/reports/p37.68d-capstone/PACKET.md",
        "the consolidated capstone packet",
    ),
    (
        "docs/build/reports/p37.68d-capstone/WALKTHROUGH.md",
        "the consolidated operator walkthrough packet",
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
    doc["ticket"] = "P37.68d"
    doc["leg"] = "cost-ledger"
    return doc


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops capstone-consolidated plan`` prints."""
    return {
        "schema": "sig.capstone-consolidated/1",
        "ticket": "P37.68d",
        "catalog": "R11-K13-CAP-01",
        "split": (
            "d — consolidated row: U-003.1…11 per-ask checks (SIG-UI-077), "
            "the consolidated 13-journey sweep (SIG-UI-078), the ROUTES.csv "
            "re-check, budgets + axe on the real release, cost read, and "
            "the consolidated operator walkthrough packet"
        ),
        "posture": "prepared_not_executed",
        "production_mutations": "none",
        "gate": "publish rides P37.65 Class S — promotion is the operator's act",
        "per_ask_checks": list(PER_ASK_CHECKS),
        "journeys": [
            "A1",
            "A2",
            "A3",
            "A4",
            "J1",
            "J2",
            "J3",
            "J4",
            "J5",
            "O1",
            "O2",
            "O3",
            "O4",
        ],
        "cells": ["1440-js", "390-js", "1440-nojs", "390-nojs"],
        "labels": ["agent-verified", "never user-tested"],
        "corpus_clauses": {
            "U-003.1": (
                "every published located record at every zoom (tile "
                "verifier = 0 missing) and the basemap serve are the "
                "release's own — the fixture records the style contract "
                "and an honest host_status, never a claimed serve"
            ),
            "U-003.2": (
                "Vigilant Solutions (LEARN) and Austin Police Department "
                "named with pages-or-typed-absences (D-K2-1 state) — the "
                "fixture proves the naming + not-published machinery on "
                "its own corpus"
            ),
            "U-003.3": (
                "benchmark dev ≥ 90 % / held-out ≥ 80 % top-3 (D-K3-7) and "
                "the named Canberra/Texas/ICE/Vigilant behaviours read the "
                "release corpus"
            ),
            "U-003.5": (
                "California's 'from 11 sources' breakdown — the fixture "
                "proves the sum machinery on its own dossier"
            ),
            "U-003.7": (
                "Seattle/Texas place pages — the fixture proves the watch "
                "page + feed-validation machinery on its own places"
            ),
            "U-003.9": (
                "the release's own source-row count — the fixture proves "
                "the sortable/extract/version machinery on its own table"
            ),
            "U-003.11": (
                "the named /task/<uuid>/ → 301 → T-… Acworth titled page — "
                "the fixture proves the canonical-id→handle 301 contract "
                "on its own ids"
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
        print(f"capstone-consolidated check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "capstone-consolidated check: "
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
        print(f"capstone-consolidated run: unknown leg '{leg_id}' (legs: {names})", file=sys.stderr)
        return 2
    if leg.stage != "deterministic":
        print(
            f"capstone-consolidated run: leg '{leg_id}' queues — "
            f"precondition: {leg.precondition}. Re-run prompt: {RERUN_PROMPT}",
            file=sys.stderr,
        )
        return 42
    if leg_id == "per-ask-fixture":
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
                "playwright.capstone-consolidated.config.ts",
            ],
            cwd=REPO_ROOT / "web",
            check=False,
        ).returncode
    if leg_id == "routes-csv-dist":
        return subprocess.run(
            ["npx", "playwright", "test", "acceptance-routes-csv.spec.ts"],
            cwd=REPO_ROOT / "web",
            check=False,
        ).returncode
    if leg_id == "budgets-axe-fixture":
        return subprocess.run(
            [
                "npx",
                "playwright",
                "test",
                "budget.spec.ts",
                "a11y.spec.ts",
                "a11y-scripts-off.spec.ts",
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
        prog="sig-ops capstone-consolidated",
        description=(
            "P37.68d: the K13 §5.1 per-ask checks (SIG-UI-077), the "
            "consolidated 13-journey sweep (SIG-UI-078), the ROUTES.csv "
            "re-check, budgets + axe, cost read and the consolidated "
            "walkthrough packet — prepared_not_executed for every "
            "live/operator leg; the deterministic legs run in this "
            "dispatch."
        ),
    )
    sub = parser.add_subparsers(dest="capstone_consolidated_command", required=True)
    sub.add_parser("plan", help="print the leg declaration (offline)")
    sub.add_parser("check", help="verify the committed leg machinery exists (never runs a leg)")
    runp = sub.add_parser(
        "run",
        help="execute a deterministic leg; gated legs queue exit 42",
    )
    runp.add_argument("--leg", required=True, help="the leg id (see plan)")
    args = parser.parse_args(argv)
    if args.capstone_consolidated_command == "plan":
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.capstone_consolidated_command == "check":
        return check()
    if args.capstone_consolidated_command == "run":
        return run(args.leg)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
