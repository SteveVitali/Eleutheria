# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``wave-verify`` — I8 §7.7's per-source and per-wave checks as one command (P35.6).

The §7.7 verification table names eight evidence layers for an acquisition
wave; this CLI joins the registry, the cadence declaration, the plan rows and
whatever run evidence exists, and reports each check at the layer it actually
reached — engineered, fixture, schedule, live-executed — never higher
(no synthetic certainty, §3.1).

Checks (§7.7):

* **engineered** — every scoped source parses in the registry and its
  ``ingestion_permitted`` state matches the expected posture (generated rows:
  ``false``; a wave that claims a flip names its expected set via
  ``--expect-permitted``). ``sig-connectors validate`` is the authoritative
  registry check; this CLI verifies the scoped set specifically.
* **schedule** — no unscheduled live source and no cron lint findings, reusing
  ``scheduled.unscheduled_live_sources`` + ``lint_cadence_crons``; scoped
  sources that carry no cadence coverage at all are reported (a pending
  schedule is reported, never silently absent).
* **fixture (shadow)** — ``--shadow`` names a JSON of per-source replay/shadow
  diffs; every diff must be ``0``.
* **live-executed** — ``--live-runs`` names a JSON of per-source run records
  (``outcome``, ``captures_landed_bytes``, ``claims_added``,
  ``rerun_claims_added``): run row ``ok`` + captures landed (bytes, not
  digest-only) + claims > 0 + the +0 re-run (``rerun_claims_added == 0``).
  Without run evidence the check is ``pending`` — machinery-only waves report
  pending, never a false green.
* **typing** — every scoped camera-class registry target carries a SKOS
  ``technology`` slug and none is typed ``traffic_camera`` for an ALPR/ATE row
  (R3; the spine-wide "0 new traffic_camera-only typings" half needs live
  evidence and stays pending without a live-runs input).
* **jurisdiction** — every scoped target carries ``jurisdiction_scheme =
  iso.3166_2`` and a full ISO code (``US-DE``, never ``DE``; R4); a sub-state
  geography must name ``jurisdiction_place`` (GEOID lands with PKG-06a/K4).
* **ER / coverage / public** — reported as ``pending`` unless
  ``--er-summary``, ``--coverage`` or ``--release`` inputs are supplied.

Exit status: ``1`` on any failed check; ``pending`` checks do not fail the run
unless ``--require live`` promotes every pending live-layer check to a failure
(the wave-activation rows' mode — this row's machinery mode leaves them
pending).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acq_gen import (
    DEFAULT_CANDIDATES,
    DEFAULT_PLAN,
    SOURCES_TOML,
    TARGET_FILES,
    _cand_ids,
    _candidate_rows,
    _plan_ticket,
)
from .live_diff import lint_cadence_crons, pin_lint
from .scheduled import load_cadence, unscheduled_live_sources

_CADENCE = Path(__file__).resolve().parents[2] / "cadence.toml"

#: Registry `kind`s that are camera-class transports — the R3/R4/typing checks
#: bind these, not document/index targets.
CAMERA_KINDS: frozenset[str] = frozenset(
    {"arcgis_query", "socrata_rows", "arcgis_outstatistics", "socrata_aggregate"}
)


@dataclass(frozen=True)
class Finding:
    layer: str
    check: str
    status: str  # "pass" | "fail" | "pending"
    subject: str = ""
    detail: str = ""


@dataclass
class Report:
    findings: list[Finding]

    def by_status(self, status: str) -> list[Finding]:
        return [f for f in self.findings if f.status == status]

    def ok(self) -> bool:
        return not self.by_status("fail")


def _scoped_plan_sources(plan_csv: Path, candidates_csv: Path) -> dict[str, dict[str, str]]:
    """plan_id → {source_seed fields} for routed (non-defer) plan rows.

    Used to scope the wave when ``--source`` isn't given: every routed row's
    proposed id (normalized) is the expected scope, so a wave-verify over the
    plan checks exactly what ACQ-01 would emit.
    """
    from .acq_gen import _slug

    cands = _candidate_rows(candidates_csv)
    out: dict[str, dict[str, str]] = {}
    with plan_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("action") == "defer":
                continue
            cand = next((cands[c] for c in _cand_ids(row) if c in cands), {})
            sid = _slug(cand.get("proposed_source_id") or "")
            out[row["plan_id"]] = {
                "source_id": sid,
                "family": row["family"],
                "action": row["action"],
                "acq": _plan_ticket(row, row["family"]),
                "geographies": cand.get("geographies", ""),
            }
    return out


def _registry_state(source_ids: Iterable[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Per-source registry posture for the scoped ids; unregistered ids error."""
    from .acq_gen import SOURCES_TOML

    table = tomllib.loads(SOURCES_TOML.read_text()).get("sources", {})
    state: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for sid in source_ids:
        row = table.get(sid)
        if row is None:
            missing.append(sid)
        else:
            state[sid] = row
    return state, missing


def _target_rows(source_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in TARGET_FILES:
        if not path.exists():
            continue
        doc = tomllib.loads(path.read_text())
        rows.extend(r for r in doc.get("targets", []) if r.get("source_id") in source_ids)
    return rows


def _load_json(path: Path | None) -> Any:
    return json.loads(path.read_text()) if path else None


def verify_wave(
    *,
    sources: frozenset[str] = frozenset(),
    plan_csv: Path = DEFAULT_PLAN,
    candidates_csv: Path = DEFAULT_CANDIDATES,
    cadence_path: Path = _CADENCE,
    shadow_path: Path | None = None,
    live_runs_path: Path | None = None,
    er_summary_path: Path | None = None,
    coverage_path: Path | None = None,
    release_path: Path | None = None,
    expect_permitted: frozenset[str] = frozenset(),
    require_live: bool = False,
) -> Report:
    findings: list[Finding] = []

    # --- scope ---------------------------------------------------------------
    plan_scope = _scoped_plan_sources(plan_csv, candidates_csv)
    scoped = set(sources)
    expected_targets: list[dict[str, Any]] = []
    deduped_rows: list[dict[str, Any]] = []
    emitted_families: dict[str, str] = {}
    if not scoped:
        # Default scope: exactly the source ids ACQ-01 would emit for this
        # plan — a deduped proposal (a target under an existing source) or a
        # widen row is NOT an expected `[sources.<id>]` row, and asking for it
        # would be synthetic certainty, not a gap (R1/NEW-1).
        from .acq_gen import generate

        gen = generate(plan_csv=plan_csv, candidates_csv=candidates_csv)
        # manifest["emitted_ids"] covers fresh emits AND converged re-runs
        # (an idempotent replay emits no row but the id is still in scope).
        scoped = set(gen.manifest.get("emitted_ids") or {i["id"] for i in gen.sources})
        expected_targets = list(gen.targets)
        deduped_rows = list(gen.manifest.get("deduped", []))
        emitted_families = {
            str(r["source_id"]): str(r.get("family", ""))
            for r in gen.manifest.get("rows", [])
            if r.get("source_id")
        }
        if gen.errors:
            findings.append(
                Finding(
                    "engineered",
                    "generator",
                    "fail",
                    detail=f"{len(gen.errors)} generator error(s): {gen.errors[0]}",
                )
            )
    generated_only = scoped - set(expect_permitted)

    # --- engineered: registry rows exist + gate posture -----------------------
    registry_state, missing = _registry_state(sorted(scoped))
    if not scoped:
        findings.append(Finding("engineered", "scope", "pending", detail="no scoped sources"))
    for sid in sorted(missing):
        findings.append(
            Finding(
                "engineered",
                "registry-row",
                "fail",
                sid,
                "no [sources.<id>] row — the wave cannot claim a source the registry does not hold",
            )
        )
    # Every deduped proposal lands under a registered source (R1); every
    # expected generated target row is registered (NEW-1/NEW-5).
    registered = set(tomllib.loads(SOURCES_TOML.read_text()).get("sources", {}))
    for d in deduped_rows:
        under = str(d.get("under", ""))
        if under not in registered:
            findings.append(
                Finding(
                    "engineered",
                    "dedupe-anchor",
                    "fail",
                    str(d.get("plan_id", "")),
                    f"deduped proposal {d.get('proposed_source_id')!r} names "
                    f"{under!r}, which is not a registered source",
                )
            )
    registered_target_ids: set[str] = set()
    for path in TARGET_FILES:
        if path.exists():
            registered_target_ids.update(
                str(r.get("id")) for r in tomllib.loads(path.read_text()).get("targets", [])
            )
    for t in expected_targets:
        if str(t.get("id")) not in registered_target_ids:
            findings.append(
                Finding(
                    "engineered",
                    "target-row",
                    "fail",
                    str(t.get("id", "")),
                    f"expected registry target for source {t.get('source_id')!r} is not registered",
                )
            )
    for sid, row in sorted(registry_state.items()):
        permitted = bool(row.get("ingestion_permitted", False))
        if sid in generated_only and permitted:
            findings.append(
                Finding(
                    "engineered",
                    "gate-posture",
                    "fail",
                    sid,
                    "generated row is ingestion_permitted=true — only an "
                    "operator HG-03 line may land that (P35.6 emits false)",
                )
            )
        elif sid in expect_permitted and not permitted:
            findings.append(
                Finding(
                    "engineered",
                    "gate-posture",
                    "fail",
                    sid,
                    "expected a flipped (permitted) row but the registry is still gated",
                )
            )
        else:
            state = "permitted" if permitted else "gated"
            findings.append(
                Finding(
                    "engineered",
                    "gate-posture",
                    "pass",
                    sid,
                    f"ingestion_permitted={permitted} ({state})",
                )
            )
        # compact_status is part of the gate posture (SIG-INGEST-027).
        if (
            row.get("compact_status")
            in {"permission_granted", "permission_granted_conditional", "partnership_active"}
            and not permitted
        ):
            findings.append(
                Finding(
                    "engineered",
                    "gate-posture",
                    "fail",
                    sid,
                    f"compact_status={row['compact_status']!r} on a gated row — "
                    "a granted compact with no flip is a contradictory record",
                )
            )

    # --- schedule -------------------------------------------------------------
    cadence = load_cadence(cadence_path)
    unscheduled = unscheduled_live_sources(cadence)
    lint = lint_cadence_crons(cadence) + pin_lint(cadence)
    scoped_unscheduled = [s for s in unscheduled if s in scoped]
    for sid in scoped_unscheduled:
        findings.append(
            Finding(
                "schedule",
                "cadence-coverage",
                "fail",
                sid,
                "loadable live-target source with no cadence coverage (unscheduled_live_sources)",
            )
        )
    if not scoped_unscheduled:
        findings.append(
            Finding("schedule", "cadence-coverage", "pass", detail="no unscheduled live source")
        )
    scoped_sources = {s.source for s in cadence.sources}
    scoped_members = {m for b in cadence.batches for m in b.members}
    for sid in sorted(scoped & set(registry_state)):
        if registry_state[sid].get("ingestion_permitted"):
            continue  # covered by the loadable-source check above
        if sid in scoped_sources or sid in scoped_members:
            findings.append(
                Finding(
                    "schedule",
                    "cadence-coverage",
                    "pass",
                    sid,
                    "cadence coverage recorded ahead of the flip",
                )
            )
        else:
            findings.append(
                Finding(
                    "schedule",
                    "cadence-coverage",
                    "pending",
                    sid,
                    "gated source carries no cadence coverage yet (family ticket assigns)",
                )
            )
    for finding in lint:
        findings.append(Finding("schedule", "cron-lint", "fail", detail=finding))
    if not lint:
        findings.append(Finding("schedule", "cron-lint", "pass", detail="cron + pin lint clean"))

    # --- fixture (shadow diff) -------------------------------------------------
    shadow = _load_json(shadow_path)
    if shadow is None:
        findings.append(
            Finding(
                "fixture",
                "shadow-diff",
                "pending",
                detail="no --shadow input (family tickets attach theirs)",
            )
        )
    else:
        rows = shadow.get("shadow", shadow if isinstance(shadow, list) else [])
        bad = [r for r in rows if r.get("source_id") in scoped or not scoped]
        nonzero = [r for r in bad if int(r.get("diff", 0)) != 0]
        for r in nonzero:
            findings.append(
                Finding(
                    "fixture",
                    "shadow-diff",
                    "fail",
                    str(r.get("source_id", "")),
                    f"shadow diff {r.get('diff')} != 0",
                )
            )
        if not nonzero:
            findings.append(
                Finding(
                    "fixture",
                    "shadow-diff",
                    "pass",
                    detail=f"{len(bad)} scoped shadow row(s) diff=0",
                )
            )

    # --- live-executed + idempotence -------------------------------------------
    live = _load_json(live_runs_path)
    live_rows = live.get("runs", live if isinstance(live, list) else []) if live else []
    by_source = {str(r.get("source_id")): r for r in live_rows}
    for sid in sorted(scoped):
        run = by_source.get(sid)
        if run is None:
            findings.append(
                Finding(
                    "live-executed",
                    "manual-first-run",
                    "pending",
                    sid,
                    "no run evidence supplied (no live stage yet)",
                )
            )
            continue
        if str(run.get("outcome")) != "ok":
            findings.append(
                Finding(
                    "live-executed",
                    "manual-first-run",
                    "fail",
                    sid,
                    f"run outcome {run.get('outcome')!r}",
                )
            )
        elif int(run.get("captures_landed_bytes") or 0) <= 0:
            findings.append(
                Finding(
                    "live-executed",
                    "captures-landed",
                    "fail",
                    sid,
                    "no capture bytes landed (J4 NEW-5: bytes, not digests)",
                )
            )
        elif int(run.get("claims_added") or 0) <= 0:
            findings.append(
                Finding("live-executed", "claims-added", "fail", sid, "first run added 0 claims")
            )
        else:
            findings.append(
                Finding(
                    "live-executed",
                    "manual-first-run",
                    "pass",
                    sid,
                    f"ok; {run.get('captures_landed_bytes')} capture bytes; "
                    f"{run.get('claims_added')} claims",
                )
            )
        rerun = run.get("rerun_claims_added")
        if rerun is None:
            findings.append(
                Finding("idempotence", "plus-zero-rerun", "pending", sid, "no re-run recorded")
            )
        elif int(rerun) == 0:
            findings.append(
                Finding(
                    "idempotence", "plus-zero-rerun", "pass", sid, "+0 re-run (claims_added == 0)"
                )
            )
        else:
            findings.append(
                Finding(
                    "idempotence",
                    "plus-zero-rerun",
                    "fail",
                    sid,
                    f"re-run added {rerun} claims, expected +0",
                )
            )

    # --- typing + jurisdiction (per scoped registry target) ---------------------
    targets = _target_rows(scoped)
    saw_camera = False
    for row in targets:
        kind = str(row.get("kind") or "")
        if kind not in CAMERA_KINDS:
            continue
        saw_camera = True
        tid = str(row.get("id"))
        tech = str(row.get("technology") or "")
        family = emitted_families.get(str(row.get("source_id"))) or next(
            (v["family"] for v in plan_scope.values() if v["source_id"] == row.get("source_id")),
            "",
        )
        if not tech:
            findings.append(
                Finding(
                    "typing",
                    "technology",
                    "pending",
                    tid,
                    "no SKOS technology slug yet (family ticket fills; PKG-07)",
                )
            )
        elif tech == "traffic_camera" and re.search(
            r"alpr|ate\b|traffic.?enforcement", family, re.I
        ):
            findings.append(
                Finding(
                    "typing",
                    "technology",
                    "fail",
                    tid,
                    "ALPR/ATE-class target typed traffic_camera (I1 NEW-9 / R3)",
                )
            )
        else:
            findings.append(Finding("typing", "technology", "pass", tid, f"technology={tech}"))
        scheme = str(row.get("jurisdiction_scheme") or "")
        state = str(row.get("state") or "")
        if scheme != "iso.3166_2" and scheme != "us.state_abbr" or not state:
            findings.append(
                Finding(
                    "jurisdiction",
                    "jurisdiction-key",
                    "fail",
                    tid,
                    f"jurisdiction_scheme={scheme!r} state={state!r} — R4 requires "
                    "iso.3166_2 (full ISO code, never a bare code)",
                )
            )
        elif re.fullmatch(r"[A-Z]{2}(-[A-Z0-9]+)?", state) is None:
            findings.append(
                Finding(
                    "jurisdiction",
                    "jurisdiction-key",
                    "fail",
                    tid,
                    f"state {state!r} is not an ISO 3166-2 code (R4)",
                )
            )
        else:
            sub = str(row.get("jurisdiction_place") or row.get("geoid") or "")
            findings.append(
                Finding(
                    "jurisdiction",
                    "jurisdiction-key",
                    "pass",
                    tid,
                    f"{scheme}:{state}" + (f" ({sub})" if sub else ""),
                )
            )
    if not saw_camera and scoped:
        findings.append(
            Finding(
                "typing",
                "technology",
                "pending",
                detail="no camera-class registry targets in scope",
            )
        )

    # --- ER / coverage / public -------------------------------------------------
    evidence_inputs: tuple[tuple[str, str, Path | None, str], ...] = (
        ("er", "expected-merges", er_summary_path, "camera_site_run/match counts"),
        (
            "coverage",
            "coverage-delta",
            coverage_path,
            "per-dimension delta (ACQ-01 coverage-delta)",
        ),
        ("public", "release-appearance", release_path, "G3 V1–V14 on the Class S candidate"),
    )
    for layer, check, input_path, hint in evidence_inputs:
        doc = _load_json(input_path)
        if doc is None:
            findings.append(Finding(layer, check, "pending", detail=f"no input ({hint})"))
        elif doc.get("unexplained") or doc.get("failures"):
            findings.append(
                Finding(
                    layer,
                    check,
                    "fail",
                    detail=f"{hint}: {doc.get('unexplained') or doc.get('failures')}",
                )
            )
        else:
            findings.append(Finding(layer, check, "pass", detail=hint))

    report = Report(findings)
    if require_live:
        report = Report(
            [
                Finding(
                    f.layer,
                    f.check,
                    "fail",
                    f.subject,
                    f.detail + " (--require live promotes pending live evidence to a failure)",
                )
                if f.status == "pending"
                and f.layer in {"live-executed", "idempotence", "er", "coverage", "public"}
                else f
                for f in findings
            ]
        )
    return report


def _print(report: Report) -> None:
    order = {
        "engineered": 0,
        "schedule": 1,
        "fixture": 2,
        "live-executed": 3,
        "idempotence": 4,
        "typing": 5,
        "jurisdiction": 6,
        "er": 7,
        "coverage": 8,
        "public": 9,
    }
    for f in sorted(report.findings, key=lambda f: (order.get(f.layer, 99), f.check, f.subject)):
        mark = {"pass": "PASS", "fail": "FAIL", "pending": "PENDING"}[f.status]
        subject = f" {f.subject}" if f.subject else ""
        detail = f" — {f.detail}" if f.detail else ""
        print(f"  {mark:<7} [{f.layer}] {f.check}{subject}{detail}")
    p, f_, pend = (
        len(report.by_status("pass")),
        len(report.by_status("fail")),
        len(report.by_status("pending")),
    )
    print(f"wave-verify: {p} pass, {f_} fail, {pend} pending")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops wave-verify",
        description=(
            "I8 §7.7's per-source/per-wave verification as one command "
            "(P35.6): joins registry, cadence, plan and supplied run evidence; "
            "reports each check at the layer it reached, never higher."
        ),
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="scope to source ids (repeatable)",
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--cadence", type=Path, default=_CADENCE)
    parser.add_argument("--shadow", type=Path, help="JSON of per-source shadow diffs")
    parser.add_argument("--live-runs", type=Path, help="JSON of per-source run records")
    parser.add_argument("--er-summary", type=Path)
    parser.add_argument("--coverage", type=Path, help="coverage-delta JSON output")
    parser.add_argument("--release", type=Path)
    parser.add_argument(
        "--expect-permitted",
        action="append",
        default=[],
        help="source ids expected flipped (the wave's HG-03 list)",
    )
    parser.add_argument(
        "--require",
        choices=("machinery", "live"),
        default="machinery",
        help="'live' promotes pending live-layer evidence to failures",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify_wave(
        sources=frozenset(args.source),
        plan_csv=args.plan,
        candidates_csv=args.candidates,
        cadence_path=args.cadence,
        shadow_path=args.shadow,
        live_runs_path=args.live_runs,
        er_summary_path=args.er_summary,
        coverage_path=args.coverage,
        release_path=args.release,
        expect_permitted=frozenset(args.expect_permitted),
        require_live=args.require == "live",
    )
    if args.json:
        print(
            json.dumps(
                {
                    "schema": "sig.wave-verify/1",
                    "findings": [f.__dict__ for f in report.findings],
                    "ok": report.ok(),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print(report)
    return 0 if report.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Finding", "Report", "verify_wave"]
