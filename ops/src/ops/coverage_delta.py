# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``coverage-delta`` — the I1 blind-spot method as a committed tool (P35.6, I8 §7.7).

I8 §7.7 requires a per-wave coverage delta "per I1 blind spot, tier-A/B state,
GL1 city, technology class and country" — and forbids `/v1/coverage` as volume
evidence (I1:559-560). This module implements the method over **committed
snapshots**, never a live API: a snapshot is a `sig.coverage-snapshot/1` JSON
document (or the equivalent `dimension,key,covered,evidence` CSV) carrying the
coverage cells the evidence actually showed — one row per
`(dimension, key)` cell, with the *evidence layer* named (`spine`, `fixture`,
`registry`, `release`) so a fixture green is never reported as live coverage
(no synthetic certainty, §3.1).

A **delta** compares two snapshots and classifies each cell:

* ``added`` — uncovered/absent → covered;
* ``removed`` — covered → uncovered/absent;
* ``changed`` — still covered but the evidence changed;
* ``unchanged``.

Every change is then **explained or unexplained**: an ``--expected`` file (or
the `--plan` + `--candidates` pair, which derives expected-addition cells from
the Round-11-routed rows' geography/technology seeds) names the change's
recorded reason. Anything left unexplained is printed as `UNEXPLAINED` — the
defining standard's "no unexplained dots" applied to coverage itself — and
``--fail-on-unexplained`` makes the command exit non-zero on any of them.

The tool is strictly read-only: it never touches the spine, the network or a
registry row.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acq_gen import DEFAULT_CANDIDATES, _cand_ids

SNAPSHOT_SCHEMA = "sig.coverage-snapshot/1"

#: The committed dimension registry (I8 §7.7) — `ops/coverage_dimensions.toml`.
DIMENSIONS_FILE = Path(__file__).resolve().parents[2] / "coverage_dimensions.toml"


def declared_dimensions(path: Path = DIMENSIONS_FILE) -> tuple[str, ...]:
    """The dimension names a snapshot may carry — the committed registry."""
    import tomllib

    doc = tomllib.loads(path.read_text())
    return tuple(sorted(doc.get("dimensions", {})))


#: The dimensions a wave delta reports (I8 §7.7, I1's method), loaded from
#: the committed registry — never a code-side guess.
DIMENSIONS: tuple[str, ...] = declared_dimensions()


@dataclass(frozen=True)
class Cell:
    """One coverage cell — `(dimension, key)` — with its evidence."""

    dimension: str
    key: str
    covered: bool
    evidence: str = ""  # names the evidence layer + pointer, e.g. "spine:claims>0"
    tier: str = ""  # tier-A/B marker where the cell is a state_tier row


@dataclass(frozen=True)
class Change:
    """One snapshot→snapshot cell transition."""

    dimension: str
    key: str
    kind: str  # "added" | "removed" | "changed"
    before_evidence: str
    after_evidence: str
    explanation: str = ""  # "" = UNEXPLAINED


def _assert_dimension(dimension: str, path: Path, declared: tuple[str, ...]) -> None:
    if dimension not in declared:
        raise ValueError(
            f"{path}: cell declares undeclared dimension {dimension!r} — "
            f"the committed registry (ops/coverage_dimensions.toml) holds "
            f"{list(declared)}; an undeclared dimension is drift, not coverage"
        )


def load_snapshot(
    path: Path, *, dimensions: tuple[str, ...] = DIMENSIONS
) -> tuple[str, dict[tuple[str, str], Cell], str]:
    """Load a `sig.coverage-snapshot/1` JSON doc or a dimension/key CSV.

    Returns ``(label, cells, layer)`` — `layer` is the snapshot's declared
    evidence layer (``spine`` | ``fixture`` | ``registry`` | ``release`` |
    ``unknown``), carried through so a fixture snapshot is never reported as
    live coverage.

    A cell whose `dimension` is not declared in
    `ops/coverage_dimensions.toml` fails to load — an undeclared dimension is
    drift, not coverage.
    """
    text = path.read_text()
    if path.suffix == ".json" or text.lstrip().startswith("{"):
        doc = json.loads(text)
        if doc.get("schema") not in (SNAPSHOT_SCHEMA, None):
            raise ValueError(f"{path}: unknown snapshot schema {doc.get('schema')!r}")
        layer = str(doc.get("layer") or "unknown")
        label = str(doc.get("label") or path.name)
        cells: dict[tuple[str, str], Cell] = {}
        for row in doc.get("cells", []):
            _assert_dimension(str(row["dimension"]), path, dimensions)
            cell = Cell(
                dimension=str(row["dimension"]),
                key=str(row["key"]),
                covered=bool(row.get("covered")),
                evidence=str(row.get("evidence", "")),
                tier=str(row.get("tier", "")),
            )
            cells[(cell.dimension, cell.key)] = cell
        return label, cells, layer
    cells = {}
    for row in csv.DictReader(text.splitlines()):
        _assert_dimension(str(row["dimension"]), path, dimensions)
        cell = Cell(
            dimension=str(row["dimension"]),
            key=str(row["key"]),
            covered=str(row.get("covered", "")).strip().lower() in {"1", "true", "yes"},
            evidence=str(row.get("evidence", "")),
            tier=str(row.get("tier", "")),
        )
        cells[(cell.dimension, cell.key)] = cell
    return path.name, cells, "unknown"


def snapshot_from_source_coverage(path: Path, *, layer: str = "registry") -> dict[str, Any]:
    """Build a `sig.coverage-snapshot/1` doc from an I1 `source_coverage.csv`.

    The CSV's `technology_classes` and `geographies` columns become
    `technology_class`/`state_tier`/`country` cells; a source counts as
    coverage evidence for a cell only when its row records actual hosted
    claims (`hosted_claims_evidence` naming captures/claims, not
    "none found") — a permitted-but-never-ingested row is a *registration*,
    honestly labelled `covered=false`.
    """
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(dimension: str, key: str, covered: bool, evidence: str, tier: str = "") -> None:
        if not key or (dimension, key) in seen:
            return
        seen.add((dimension, key))
        cells.append(
            {
                "dimension": dimension,
                "key": key,
                "covered": covered,
                "evidence": evidence,
                "tier": tier,
            }
        )

    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            covered = bool(
                row.get("hosted_claims_evidence")
                and "none" not in row["hosted_claims_evidence"].lower()
            )
            evidence = (
                f"{layer}:{row.get('source_id', '')} claims={row.get('hosted_claims_evidence', '')}"
            )
            geo = (row.get("geographies") or "").split(":")[0].strip()
            if geo:
                add("state_tier", geo, covered, evidence)
                if geo.startswith("US-"):
                    add("country", "US", covered, evidence)
                elif "-" in geo:
                    add("country", geo.split("-")[0], covered, evidence)
                else:
                    add("country", geo, covered, evidence)
            for tech in (row.get("technology_classes") or "").split(";"):
                if tech.strip():
                    add("technology_class", tech.strip(), covered, evidence)
    cells.sort(key=lambda c: (c["dimension"], c["key"]))
    return {"schema": SNAPSHOT_SCHEMA, "label": path.name, "layer": layer, "cells": cells}


def expected_from_plan(plan_csv: Path, candidates_csv: Path) -> dict[tuple[str, str], str]:
    """`(dimension, key)` → the plan_id that explains an expected addition.

    Only Round-11-**routed** rows (non-defer) explain a change — a deferred
    candidate appearing as new coverage is unexplained, exactly the drift the
    delta exists to catch.
    """
    from .acq_gen import _candidate_rows

    cands = _candidate_rows(candidates_csv)
    out: dict[tuple[str, str], str] = {}
    with plan_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("action") == "defer":
                continue
            for cid in _cand_ids(row):
                cand = cands.get(cid)
                if not cand:
                    continue
                geo = (cand.get("geographies") or "").split(":")[0].strip()
                if geo:
                    out.setdefault(("state_tier", geo), row["plan_id"])
                    country = geo.split("-")[0] if "-" in geo else geo
                    country_key = "US" if geo.startswith("US-") else country
                    out.setdefault(("country", country_key), row["plan_id"])
                for spot in (cand.get("i7_blind_spots") or "").split(";"):
                    spot = spot.strip()
                    if spot.startswith("state:") and "tier" in spot:
                        key = "US-" + spot.removeprefix("state:").split("(")[0].strip()
                        out.setdefault(("state_tier", key), row["plan_id"])
                    elif spot:
                        out.setdefault(("blind_spot", spot.split("(")[0].strip()), row["plan_id"])
                for tech in (cand.get("technology_classes") or "").split(";"):
                    if tech.strip():
                        out.setdefault(("technology_class", tech.strip()), row["plan_id"])
    return out


def load_expected(path: Path | None) -> dict[tuple[str, str], str]:
    """An `--expected` JSON/CSV of `(dimension,key) → explanation` rows."""
    if path is None:
        return {}
    text = path.read_text()
    out: dict[tuple[str, str], str] = {}
    if path.suffix == ".json" or text.lstrip().startswith("{"):
        for row in json.loads(text).get("expected", []):
            out[(str(row["dimension"]), str(row["key"]))] = str(row.get("reason", ""))
        return out
    for row in csv.DictReader(text.splitlines()):
        out[(str(row["dimension"]), str(row["key"]))] = str(row.get("reason", ""))
    return out


def delta(
    before: Mapping[tuple[str, str], Cell],
    after: Mapping[tuple[str, str], Cell],
    *,
    expected: Mapping[tuple[str, str], str] | None = None,
) -> list[Change]:
    """Every added/removed/changed cell between two snapshots, sorted."""
    expected = expected or {}
    changes: list[Change] = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if a is not None and a.covered and (b is None or not b.covered):
            kind = "added"
        elif b is not None and b.covered and (a is None or not a.covered):
            kind = "removed"
        elif b is not None and a is not None and b.evidence != a.evidence:
            kind = "changed"
        else:
            continue
        changes.append(
            Change(
                dimension=key[0],
                key=key[1],
                kind=kind,
                before_evidence=b.evidence if b else "",
                after_evidence=a.evidence if a else "",
                explanation=expected.get(key, ""),
            )
        )
    return changes


def report_text(
    changes: Iterable[Change], *, before_label: str, after_label: str, layer: str
) -> str:
    lines = [
        f"coverage-delta: {before_label} -> {after_label} (snapshot layer: {layer})",
        "  dimension          kind      cell                                        explanation",
    ]
    counts = {"added": 0, "removed": 0, "changed": 0}
    unexplained = 0
    for c in changes:
        counts[c.kind] += 1
        why = c.explanation or "UNEXPLAINED"
        if not c.explanation:
            unexplained += 1
        lines.append(f"  {c.dimension:<18} {c.kind:<9} {c.key:<43} {why}")
    lines.append(
        f"  -- {counts['added']} added, {counts['removed']} removed, "
        f"{counts['changed']} changed; {unexplained} unexplained"
    )
    return "\n".join(lines)


def report_json(
    changes: Iterable[Change], *, before_label: str, after_label: str, layer: str
) -> str:
    doc = {
        "schema": "sig.coverage-delta/1",
        "before": before_label,
        "after": after_label,
        "layer": layer,
        "changes": [
            {
                "dimension": c.dimension,
                "key": c.key,
                "kind": c.kind,
                "before_evidence": c.before_evidence,
                "after_evidence": c.after_evidence,
                "explanation": c.explanation or None,
                "unexplained": not c.explanation,
            }
            for c in changes
        ],
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops coverage-delta",
        description=(
            "I1's blind-spot coverage-delta method as a committed, read-only "
            "tool (P35.6, I8 §7.7): compares two committed coverage snapshots "
            "and reports added/removed/changed cells, explained or "
            "UNEXPLAINED. Never queries /v1/coverage or the network."
        ),
    )
    parser.add_argument("--baseline", type=Path, help="pre-wave snapshot (JSON or CSV)")
    parser.add_argument("--current", type=Path, help="post-wave/generated snapshot")
    parser.add_argument("--expected", type=Path, help="JSON/CSV of expected (dimension,key)→reason")
    parser.add_argument("--plan", type=Path, help="derive expected cells from the acquisition plan")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument(
        "--from-source-coverage",
        type=Path,
        help="convert an I1 source_coverage.csv to a snapshot JSON and exit",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on-unexplained", action="store_true")
    args = parser.parse_args(argv)

    if args.from_source_coverage is not None:
        doc = snapshot_from_source_coverage(args.from_source_coverage)
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    if args.baseline is None or args.current is None:
        parser.error("--baseline and --current are required (unless --from-source-coverage)")

    expected = load_expected(args.expected)
    if args.plan is not None:
        expected = {**expected_from_plan(args.plan, args.candidates), **expected}

    before_label, before, _ = load_snapshot(args.baseline)
    after_label, after, layer = load_snapshot(args.current)
    changes = delta(before, after, expected=expected)

    if args.format == "json":
        print(report_json(changes, before_label=before_label, after_label=after_label, layer=layer))
    else:
        print(report_text(changes, before_label=before_label, after_label=after_label, layer=layer))
    if args.fail_on_unexplained and any(not c.explanation for c in changes):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "Cell",
    "Change",
    "DIMENSIONS",
    "declared_dimensions",
    "delta",
    "expected_from_plan",
    "load_expected",
    "load_snapshot",
    "snapshot_from_source_coverage",
]
