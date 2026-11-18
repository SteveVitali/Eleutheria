# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.65a (J3 TX-16, R11-K13-TX-16): the transparency-acceptance leg
declaration — final release cut + live crawl + scrub audit.

The ticket's job is the TX-16 acceptance battery around the final release
cut: the scrub audit (the J3 TX-01/P35.31 secret scan over every published
transparency file), the page-type budgets at real scale, the K13 §8
capstone journey re-runs (J1, J4 — agent walkthrough, never user research),
the release cut itself and the live crawl over the staged candidate.

What runs in this dispatch (``live_verification=false``) is the
deterministic half: the scrub audit over the emitted dist's published
transparency families, the J1/J4 fixture-walkable legs and the budgets
cite. The two legs that cannot run in an engineering dispatch are declared
``prepared_not_executed``:

* ``release-cut`` — the row's named production mutation (a release build
  under the plan's window text: `final release cut never inside AR-3
  windows (12-06 -> 12-13T12:00Z)` — the plan cell, verbatim). It needs the
  hosted release registry (``$SIG_RELEASE_REGISTRY``) — whose infra apply
  leg is still owed by ``D-P35.53-1`` — plus project ADC; both are absent
  in this dispatch (the ``eleutheria-sig-release`` bucket does not exist).
* ``live-crawl`` — the ``release verify --mode S`` suite over the staged
  candidate's staging origin (the V3/V5 crawl + V12 publish-set scrub at
  release scale). It needs the cut leg's staged candidate and the IAM-only
  staging origin — same absence.

The promote is P37.65b's in-ticket pause — never this row's leg.

``sig-ops transparency-acceptance plan`` prints the declaration offline;
``sig-ops transparency-acceptance check`` verifies the committed machinery
each deterministic leg names exists (exit 0 — it never runs a leg);
``sig-ops transparency-acceptance run --leg <id>`` executes a deterministic
leg and queues exit 42 on the gated legs — the named precondition is not
met by declaration, never by probing production.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The ticket's verbatim re-run prompt — the OM-19 form the deferred legs
#: name so the return pass needs no fresh operator text.
RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md "
    "live_verification=true"
)

#: The plan cell's window text, verbatim — the release cut may never run
#: inside the AR-3 windows it names.
WINDOW_TEXT = "final release cut never inside AR-3 windows (12-06 -> 12-13T12:00Z)"

#: Where this dispatch's scrub-audit record lands (the committed report
#: artifact beside PACKET.md — the same packet.json convention
#: p36.44-release-cadence and p37.33-watch-lane use).
DEFAULT_AUDIT_OUT = "docs/build/reports/p37.65a-transparency-acceptance/scrub-audit.json"


@dataclass(frozen=True)
class Leg:
    """One acceptance leg — its command, the precondition that must hold
    before it may run, and the artifact it writes."""

    leg_id: str
    stage: str  # "deterministic" | "production-mutation" | "live"
    description: str
    command: str
    precondition: str
    artifact: str


#: The committed leg list — order is the OM-19 execution order.
LEGS: tuple[Leg, ...] = (
    Leg(
        leg_id="scrub-audit",
        stage="deterministic",
        description=(
            "the TX-16 scrub audit — the J3 TX-01/P35.31 secret scan "
            "(policy.transparency.find_secrets, the one shared detector) "
            "over every published transparency file in the emitted tree: "
            "the transparency/ artifact family, the status lane, the "
            "source explorer, the downloads center, the raw archive, the "
            "evidence/changes surfaces and the release namespaces where "
            "present. One secret-shaped hit fails; the record names "
            "file/line/pattern-class, never the matched value"
        ),
        command="sig-ops transparency-acceptance run --leg scrub-audit",
        precondition="none — runs in this dispatch over the emitted dist",
        artifact="docs/build/reports/p37.65a-transparency-acceptance/scrub-audit.json",
    ),
    Leg(
        leg_id="journeys",
        stage="deterministic",
        description=(
            "the K13 §8 capstone re-runs' fixture-walkable half — J1 "
            "(defend a headline figure: figure → source artifact → "
            "breakdown, ≤ 2 actions to evidence, as-of + Provisional/honest "
            "labels) and J4's cite-block contract (every sampled route "
            "carries exactly one cite block in exactly one mode — immutable "
            "/ interim / unreleased — with the pinned-selector permalink "
            "resolving). J4's durable-pin half (the /s/<pub>/ byte-"
            "identical read) rides the staged candidate under live-crawl "
            "(web/tests/e2e/transparency-acceptance.spec.ts)"
        ),
        command=(
            "npx playwright test tests/e2e/transparency-acceptance.spec.ts --project=chromium"
        ),
        precondition="none — runs in the ordinary test:e2e pass and this dispatch",
        artifact="playwright run output; cited in the acceptance packet",
    ),
    Leg(
        leg_id="budgets",
        stage="deterministic",
        description=(
            "page-type budget all types (the catalog's acceptance shape) — "
            "the generalised budget.spec.ts wire measurement over the "
            "real-sized national build, every discovered route, gzip + "
            "brotli, before and after one scripted interaction per surface"
        ),
        command="bash scripts/ci/national_budget_leg.sh budgets",
        precondition="none — runs in CI (perf job); this dispatch cites it",
        artifact="budget.spec results over the national build; the packet cites the measure",
    ),
    Leg(
        leg_id="release-cut",
        stage="production-mutation",
        description=(
            "the row's named production mutation — the final release cut "
            "under the plan's window text: `sig-ops release cut --apply` "
            "fixes T0 under the §3.3 clock guards and journals the cut; "
            "`release build` + `release sites` + `release stage` assemble "
            "and stage the immutable candidate into $SIG_RELEASE_REGISTRY "
            "(the private gs://<project>-sig-release registry — insert-"
            "only, collision-refuses, resume-safe)"
        ),
        command=(
            "sig-ops release cut --apply --registry $SIG_RELEASE_REGISTRY && "
            "sig-ops release build --registry $SIG_RELEASE_REGISTRY "
            "--export-dir <spine export> --work-dir <build> --apply && "
            "sig-ops release sites --registry $SIG_RELEASE_REGISTRY "
            "--work-dir <build> --apply && "
            "sig-ops release stage --registry $SIG_RELEASE_REGISTRY "
            "--work-dir <build> --apply"
        ),
        precondition=(
            f"the hosted release registry exists and is reachable "
            f"(D-P35.53-1 landed — absent today: the bucket 404s) + project "
            f"ADC + SIG_GCP_PROJECT present + the window holds "
            f"({WINDOW_TEXT}) + live_verification=true (OM-19)"
        ),
        artifact=(
            "registry journal sig.release-event/1 rows (cut → built → "
            "staged) + the built release tree; the run ledger's evidence"
        ),
    ),
    Leg(
        leg_id="live-crawl",
        stage="live",
        description=(
            "the live crawl — `sig-ops release verify --mode S` over the "
            "staged candidate on the IAM-only staging origin: the G3 §5.5 "
            "suite (V1 integrity, V2 identity/clock, V3 allow-list + "
            "content assertions, V4 site-release stamp, V5 the crawl — "
            "every published route answers, V11 labels, V12 the publish-"
            "set secret scan at release scale, V13 disclosures, V14/V15 "
            "where the suite names them) — any failure or skip blocks "
            "promotion, which is P37.65b's pause anyway"
        ),
        command=(
            "sig-ops release verify --registry $SIG_RELEASE_REGISTRY "
            "--work-dir <build> --mode S --origin <IAM-only staging origin> "
            "--origin-header 'Authorization: Bearer <identity token>' --apply"
        ),
        precondition=(
            "release-cut staged the candidate + the IAM-only staging "
            "origin exists (D-P35.53-1) + the identity token; "
            "live_verification=true (OM-19)"
        ),
        artifact="sig.release-verify/1 result rows per check, appended to the packet",
    ),
)

#: The committed machinery each deterministic leg names — `check` verifies
#: the paths exist so a renamed/missing leg file can never silently retire
#: an acceptance surface.
DETERMINISTIC_PATHS: tuple[tuple[str, str], ...] = (
    ("web/tests/e2e/transparency-acceptance.spec.ts", "the J1/J4 deterministic journey legs"),
    ("scripts/ci/national_budget_leg.sh", "the budgets leg carrier"),
    ("web/tests/e2e/page-budgets.json", "the sig.page-budgets/1 contract"),
    ("policy/src/policy/transparency.py", "the one shared secret detector (find_secrets, S-1)"),
    ("ops/src/ops/release_pipeline.py", "the release cut/build/sites/stage verbs"),
    ("ops/src/ops/release_verify.py", "the G3 §5.5 verify suite (the live-crawl checks)"),
    ("docs/build/reports/p37.65a-transparency-acceptance/PACKET.md", "the Class S readout packet"),
)

#: The published-transparency file families the scrub audit covers —
#: declared by in-tree path prefix so the same audit binds the web dist
#: form (``artifact/transparency/``…), the export form (``transparency/``…)
#: and the release tree form (``r/<pub>/transparency/``…, ``s/<pub>/``…).
#: ``transparency-artifacts`` is the one required family — a tree with no
#: transparency artifact at all fails the audit rather than passing
#: vacuous (SIG-ENG-042).
TRANSPARENCY_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("transparency-artifacts", ("transparency/", "artifact/transparency/")),
    ("status-lane", ("status/",)),
    ("source-explorer", ("sources/",)),
    ("downloads", ("data/",)),
    ("raw-archive", ("raw/", "artifact/raw/")),
    ("evidence", ("evidence/", "artifact/evidence/")),
    ("changes", ("changes/",)),
    ("release-namespaces", ("r/", "v/", "s/", "releases/")),
    ("statements", ("statements/",)),
)

REQUIRED_FAMILY = "transparency-artifacts"
AUDIT_SCHEMA = "sig.scrub-audit/1"


def _family_of(rel: str) -> str | None:
    """The transparency family a tree-relative path belongs to, by prefix."""
    for family, prefixes in TRANSPARENCY_FAMILIES:
        if any(rel.startswith(prefix) for prefix in prefixes):
            return family
    return None


def scrub_audit(root: Path, *, at: str | None = None) -> dict[str, object]:
    """The TX-16 scrub audit over ``root`` — one ``sig.scrub-audit/1`` row.

    Every file under the declared transparency families is scanned with
    ``policy.transparency.find_secrets`` — the same detector the publish
    gate (``ops.publish.assert_publish_set_secret_free``) and V12 run.
    The record carries per-family file counts and hits as
    file/line/pattern-class — never the matched value (J4 S-1's evidence
    rule). Verdict ``fail`` on any hit OR on a vacuous audit (zero files
    scanned, or the required transparency-artifacts family absent).
    """
    from policy.transparency import find_secrets

    files = sorted(p for p in root.rglob("*") if p.is_file())
    family_files = {family: 0 for family, _ in TRANSPARENCY_FAMILIES}
    family_hits = {family: 0 for family, _ in TRANSPARENCY_FAMILIES}
    hits: list[dict[str, object]] = []
    scanned = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        family = _family_of(rel)
        if family is None:
            continue
        scanned += 1
        family_files[family] += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        found = find_secrets(text)
        family_hits[family] += len(found)
        hits.extend({"file": rel, "line": f.line, "pattern_class": f.pattern_class} for f in found)
    families: dict[str, dict[str, object]] = {
        family: {
            "prefixes": list(prefixes),
            "files": family_files[family],
            "hits": family_hits[family],
            "state": "scanned" if family_files[family] else "absent",
        }
        for family, prefixes in TRANSPARENCY_FAMILIES
    }
    vacuous = scanned == 0 or family_files[REQUIRED_FAMILY] == 0
    verdict = "fail" if (hits or vacuous) else "pass"
    detail = (
        f"{scanned} published-transparency files scanned under {root.as_posix()} "
        f"— {len(hits)} secret-shaped hit(s)"
    )
    if vacuous:
        detail += "; VACUOUS — the required transparency-artifacts family is absent"
    return {
        "schema": AUDIT_SCHEMA,
        "ticket": "P37.65a",
        "tree": root.as_posix(),
        "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
        "families": [{"family": k, **v} for k, v in families.items()],
        "files_scanned": scanned,
        "hits": hits,
        "verdict": verdict,
        "detail": detail,
        "evidence_rule": (
            "file/line/pattern-class only — matched values are never recorded (J4 S-1)"
        ),
    }


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops transparency-acceptance plan`` prints."""
    return {
        "schema": "sig.transparency-acceptance/1",
        "ticket": "P37.65a",
        "catalog": "R11-K13-TX-16",
        "posture": "prepared_not_executed",
        "production_mutations": (
            "the final release cut itself (a release build under the plan's "
            "window text) — declared, gated on the hosted registry + ADC "
            "this dispatch lacks (D-P35.53-1 OPEN); never executed here"
        ),
        "window": WINDOW_TEXT,
        "gate": (
            "none (cut + checks; the HG-11 pause is P37.65b) — the promote "
            "leg and the final Class S readout are P37.65b's in-ticket "
            "pause, never this row's"
        ),
        "rerun_prompt": RERUN_PROMPT,
        "legs": [asdict(lg) for lg in LEGS],
        "deterministic_paths": [p for p, _ in DETERMINISTIC_PATHS],
        "transparency_families": {
            family: list(prefixes) for family, prefixes in TRANSPARENCY_FAMILIES
        },
    }


def check() -> int:
    """Verify the committed machinery exists; never runs a leg."""
    missing = [(path, why) for path, why in DETERMINISTIC_PATHS if not (REPO_ROOT / path).exists()]
    for path, why in missing:
        print(f"transparency-acceptance check: MISSING {path} — {why}", file=sys.stderr)
    if missing:
        return 1
    print(
        "transparency-acceptance check: "
        f"{len(DETERMINISTIC_PATHS)} committed legs present; "
        f"{sum(1 for lg in LEGS if lg.stage != 'deterministic')} gated legs "
        "declared prepared_not_executed"
    )
    return 0


def run(leg_id: str, *, tree: Path | None = None, out: Path | None = None) -> int:
    """Execute a deterministic leg; queue (exit 42) every gated leg."""
    leg = next((lg for lg in LEGS if lg.leg_id == leg_id), None)
    if leg is None:
        names = ", ".join(lg.leg_id for lg in LEGS)
        print(
            f"transparency-acceptance run: unknown leg '{leg_id}' (legs: {names})",
            file=sys.stderr,
        )
        return 2
    if leg.stage != "deterministic":
        print(
            f"transparency-acceptance run: leg '{leg_id}' queues — "
            f"precondition: {leg.precondition}. Re-run prompt: {RERUN_PROMPT}",
            file=sys.stderr,
        )
        return 42
    if leg_id == "scrub-audit":
        root = tree if tree is not None else REPO_ROOT / "web" / "dist"
        if not root.is_dir():
            print(
                f"transparency-acceptance run: scrub-audit needs an emitted tree — "
                f"{root} absent (run `npm --prefix web run build` first)",
                file=sys.stderr,
            )
            return 2
        record = scrub_audit(root)
        target = out if out is not None else REPO_ROOT / DEFAULT_AUDIT_OUT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"scrub-audit: {record['detail']} → {target}")
        return 0 if record["verdict"] == "pass" else 1
    if leg_id == "journeys":
        return subprocess.run(
            [
                "npx",
                "playwright",
                "test",
                "tests/e2e/transparency-acceptance.spec.ts",
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
        prog="sig-ops transparency-acceptance",
        description=(
            "P37.65a / J3 TX-16: the transparency-acceptance leg declaration "
            "(scrub audit + budgets + J1/J4 legs deterministic; the release "
            "cut and the live crawl declared prepared_not_executed)."
        ),
    )
    sub = parser.add_subparsers(dest="transparency_acceptance_command", required=True)
    sub.add_parser("plan", help="print the leg declaration as JSON")
    sub.add_parser("check", help="verify the committed machinery exists")
    r = sub.add_parser("run", help="execute a deterministic leg")
    r.add_argument("--leg", required=True, choices=[lg.leg_id for lg in LEGS])
    r.add_argument(
        "--tree",
        default=None,
        help="(scrub-audit) the emitted tree to scan (default: web/dist)",
    )
    r.add_argument(
        "--out",
        default=None,
        help=f"(scrub-audit) sig.scrub-audit/1 record path (default: {DEFAULT_AUDIT_OUT})",
    )
    args = parser.parse_args(argv)
    if args.transparency_acceptance_command == "plan":
        print(json.dumps(plan(), indent=2))
        return 0
    if args.transparency_acceptance_command == "check":
        return check()
    if args.transparency_acceptance_command == "run":
        return run(
            args.leg,
            tree=Path(args.tree) if args.tree else None,
            out=Path(args.out) if args.out else None,
        )
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
