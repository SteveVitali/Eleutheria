# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The SIG graph-quality suite — registry, evaluator contract and ratchet engine.

P34.44a (SIG-CONF-006/007, ADR-154 decisions 1/2/4, L3 §3/§4/§6). This module is
the *ruleset* half of the suite: it loads and validates the versioned check
registry (``exports/src/exports/data/quality_checks.toml`` — the "source of
truth catalog that declares each check's population, placement, measurement,
mode, baseline, threshold, fixing row and basis class"), evaluates
evaluator-supplied measurements through the ratchet engine, and emits the two
quality records (``sig.quality-report/1`` and ``sig.probe-run/1``).

The module never touches the spine itself — evaluation of a check is supplied
by a *check runner* (``ops.quality`` ships the spine/file evaluators) and this
module never runs SQL, never opens a file and never writes anything. The
rules it enforces:

* ``SIG-CONF-003`` — only mechanical checks may gate. An ``enforce`` or
  ``ratchet`` check must carry a gating basis class (B0/B1/B2/B5); B3
  (agent-labelled) and B4 (maintainer check) evidence may *never* gate, so a
  registry that tries to flip one to ``enforce`` fails validation.
* ``SIG-ENG-042`` — the vacuous-pass guard. A check that evaluates **zero**
  items **fails**; a check that could not run at all reports
  ``not_evaluable`` with an explicit reason. No green checkmark comes from an
  empty evaluation.
* ``SIG-CONF-007`` — the ratchet. A ratchet-mode check fails when its measured
  value regresses past its baseline; improvements are recorded (and the
  registry diff below lets the baseline move only *toward* the threshold);
  a ``ratchet`` mode check flips to ``enforce`` only in its fixing row; and a
  baseline or threshold loosening requires a new ADR.
* Release V15 (``run_release_gate``) — standalone hook that consumes a
  ``sig.quality-report/1``: zero ratchet regressions and zero ``enforce``
  failures pass; a ``not_evaluable`` enforce check blocks (fail closed).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# The schema and its controlled vocabularies (SIG-CONF-006, L3 §3.2)

SCHEMA: Final = "sig.quality-checks/1"
REPORT_VERSION: Final = "sig.quality-report/1"
PROBE_RUN_VERSION: Final = "sig.probe-run/1"
BASELINE_VERSION: Final = "sig.quality-baseline/1"
REGISTRY_VERSION: Final = "1"

DEFAULT_REGISTRY_PATH: Final = Path(__file__).resolve().parent / "data" / "quality_checks.toml"

#: The bundled registry, resolved as a package resource so an installed wheel
#: finds it too (same pattern as ``resolution.quality_gates``).
_REGISTRY_RESOURCE: Final = "data/quality_checks.toml"

#: placement codes (L3 §3.2):
#:   I ingest/sink · M post-materialize nightly spine probe · R release-candidate
#:   gate · P pull request · S scheduled public probe
PLACEMENTS: Final = frozenset({"I", "M", "R", "P", "S"})

#: check modes (L3 §3.2): enforce blocks; ratchet compares against a baseline
#: that may move only toward the threshold and flips to enforce in its fixing
#: row; report publishes but never gates.
MODES: Final = frozenset({"enforce", "ratchet", "report"})

DIRECTIONS: Final = frozenset({"lower_is_better", "higher_is_better"})
UNITS: Final = frozenset({"count", "share", "ratio"})

#: basis classes (SIG-CONF-001): B0 by construction · B1 mechanical census ·
#: B2 mechanical sample · B3 agent review · B4 maintainer check · B5
#: independent human.
BASIS_CLASSES: Final = frozenset({"B0", "B1", "B2", "B3", "B4", "B5"})

#: The gating basis classes — SIG-CONF-003: B3 (agent review) and B4
#: (maintainer check) evidence may *never* gate. B5 is the strongest basis and
#: may gate, but a B5 evidence *completion marker* is a human record — no
#: spine check produces one; it is here for completeness.
GATING_BASIS_CLASSES: Final = frozenset({"B0", "B1", "B2", "B5"})

CHECK_ID_RE: Final = re.compile(r"^GQ-\d{2}$")
FIXING_ROW_RE: Final = re.compile(r"^P\d+\.\d+[a-z]?$")

#: `baseline_at` is a date-only stamp recorded by the baseline apply —
#: always written from `date -u` (OM-04).
BASELINE_AT_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: threshold grammar: "none" | "<= N" | "< N" | "> N" | ">= N" | "== N"
THRESHOLD_RE: Final = re.compile(r"^(<=|<|>|>=|==)\s*([0-9]+(?:\.[0-9]+)?)$")

OUTCOMES: Final = frozenset({"pass", "fail", "not_evaluable", "unbaselined"})

# ---------------------------------------------------------------------------
# The parsed registry


class RegistryError(ValueError):
    """A registry that fails SIG-CONF-006 validation — raised on load."""


@dataclass(frozen=True)
class Threshold:
    """A parsed check threshold; ``op == "none"`` carries no bound."""

    op: str  # "none" | "<=" | "<" | ">" | ">=" | "=="
    value: float | None

    @classmethod
    def parse(cls, raw: Any) -> Threshold:
        if raw == "none":
            return cls("none", None)
        m = THRESHOLD_RE.match(str(raw).strip()) if isinstance(raw, str) else None
        if not m:
            raise RegistryError(f"unparseable threshold {raw!r}")
        return cls(m.group(1), float(m.group(2)))

    def __str__(self) -> str:
        return "none" if self.op == "none" else f"{self.op} {self.value:g}"

    def allows(self, value: float) -> bool:
        """True when ``value`` satisfies the threshold."""
        if self.op == "none":
            return True
        assert self.value is not None
        return {
            "<=": value <= self.value,
            "<": value < self.value,
            ">": value > self.value,
            ">=": value >= self.value,
            "==": value == self.value,
        }[self.op]

    def strictly_tighter_than(self, other: Threshold) -> bool:
        """True when ``self`` permits no value ``other`` forbids — used by the
        registry diff to decide whether a threshold change tightens (allowed)
        or loosens (needs a new ADR)."""
        if other.op == "none" and self.op != "none":
            return True
        if other.op != "none" and self.op == "none":
            return False
        if other.op == "none" or self.op == "none":
            return other.op == self.op
        assert other.value is not None and self.value is not None
        # Same bound, stricter op (< vs <=) is tightening.
        if self.value < other.value and self.op in ("<=", "<", "=="):
            return other.op in ("<=", "<")
        if self.value > other.value and self.op in (">=", ">", "=="):
            return other.op in (">=", ">")
        if self.value == other.value:
            rank = {"<": 0, "<=": 1, ">": 0, ">=": 1, "==": 0}
            same_side = (self.op in ("<", "<=", "==")) == (other.op in ("<", "<=", "=="))
            return same_side and rank.get(self.op, 9) <= rank.get(other.op, 9)
        return False


@dataclass(frozen=True)
class QualityCheck:
    """One parsed registry row (SIG-CONF-006)."""

    check_id: str
    statement: str
    population: str
    placement: frozenset[str]
    mode: str
    direction: str
    threshold: Threshold
    baseline: float | None  # None ⇒ "pending" (P34.44b's baseline run sets it)
    baseline_pending: bool
    unit: str
    basis_class: str
    fixing: tuple[str, ...]
    source_ids: str  # the `from` field — the L1/L2/L3 ids this check deduplicates
    note: str
    baseline_run: str = ""  # the run id the baseline was measured in (P34.44b)
    baseline_at: str = ""  # the `date -u` day that run recorded it (YYYY-MM-DD)


@dataclass(frozen=True)
class CheckRegistry:
    """The loaded, validated registry plus its content digest."""

    version: str
    checks: tuple[QualityCheck, ...]
    digest: str

    def by_id(self) -> dict[str, QualityCheck]:
        return {c.check_id: c for c in self.checks}


def validate_registry(doc: dict[str, Any], known_rows: set[str] | None = None) -> list[str]:
    """Validate a parsed registry document; return every violation found.

    ``known_rows``, when given, is the set of manifest ticket ids the
    ``fixing`` rows must resolve to (loaded from the manifest by the caller).
    """
    errors: list[str] = []
    if str(doc.get("schema")) != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, got {doc.get('schema')!r}")
    if not str(doc.get("version") or ""):
        errors.append("registry must declare a version")
    raw_checks = doc.get("check")
    if not isinstance(raw_checks, list) or not raw_checks:
        errors.append("registry must declare at least one [[check]]")
        return errors
    seen: set[str] = set()
    for i, raw in enumerate(raw_checks):
        where = f"check[{i}]"
        if not isinstance(raw, dict):
            errors.append(f"{where}: not a table")
            continue
        cid = str(raw.get("id") or "")
        where = f"check[{i}] {cid or '(no id)'}"
        if not CHECK_ID_RE.match(cid):
            errors.append(f"{where}: id must match {CHECK_ID_RE.pattern}, got {cid!r}")
        elif cid in seen:
            errors.append(f"{where}: duplicate id {cid}")
        seen.add(cid)
        for field_name in ("statement", "population", "from"):
            if not str(raw.get(field_name) or "").strip():
                errors.append(f"{where}: {field_name} must be a non-empty string")
        placement = raw.get("placement")
        if not isinstance(placement, list) or not placement or not set(placement) <= PLACEMENTS:
            errors.append(f"{where}: placement must be a non-empty subset of {sorted(PLACEMENTS)}")
        mode = raw.get("mode")
        if mode not in MODES:
            errors.append(f"{where}: mode must be one of {sorted(MODES)}")
        direction = raw.get("direction")
        if direction not in DIRECTIONS:
            errors.append(f"{where}: direction must be one of {sorted(DIRECTIONS)}")
        try:
            Threshold.parse(raw.get("threshold"))
        except RegistryError as e:
            errors.append(f"{where}: {e}")
        baseline = raw.get("baseline")
        if mode == "ratchet" and baseline is None:
            errors.append(f"{where}: ratchet checks must declare a baseline")
        elif baseline is not None and not isinstance(baseline, (int, float)):
            if baseline != "pending":
                errors.append(f"{where}: baseline must be a number or 'pending'")
        unit = raw.get("unit")
        if unit not in UNITS:
            errors.append(f"{where}: unit must be one of {sorted(UNITS)}")
        basis = raw.get("basis_class")
        if basis not in BASIS_CLASSES:
            errors.append(f"{where}: basis_class must be one of {sorted(BASIS_CLASSES)}")
        # SIG-CONF-003 — only mechanical checks may gate.
        if mode in ("enforce", "ratchet") and basis in BASIS_CLASSES - GATING_BASIS_CLASSES:
            errors.append(
                f"{where}: mode {mode!r} gates but basis_class {basis!r} may never "
                "gate (SIG-CONF-003 — only B0/B1/B2/B5 evidence may gate)"
            )
        fixing = raw.get("fixing")
        if not isinstance(fixing, list):
            errors.append(f"{where}: fixing must be a list of ticket ids")
        else:
            for row in fixing:
                if not FIXING_ROW_RE.match(str(row)):
                    errors.append(f"{where}: fixing row {row!r} is not a ticket id")
                elif known_rows is not None and row not in known_rows:
                    errors.append(f"{where}: fixing row {row!r} is not a manifest row")
        note = raw.get("note")
        if note is not None and not isinstance(note, str):
            errors.append(f"{where}: note must be a string")
        # The measured-baseline provenance pair (P34.44b): a check whose
        # baseline a recorded run set names the run and its `date -u` day —
        # always both or neither, and only beside a numeric baseline.
        baseline_run = raw.get("baseline_run")
        baseline_at = raw.get("baseline_at")
        if baseline_run is not None and (
            not isinstance(baseline_run, str) or not baseline_run.strip()
        ):
            errors.append(f"{where}: baseline_run must be a non-empty string")
        if baseline_at is not None and (
            not isinstance(baseline_at, str) or not BASELINE_AT_RE.match(baseline_at)
        ):
            errors.append(f"{where}: baseline_at {baseline_at!r} must be YYYY-MM-DD (date -u)")
        if (baseline_run is None) != (baseline_at is None):
            errors.append(f"{where}: baseline_run and baseline_at land together")
        if baseline_run is not None and not isinstance(baseline, (int, float)):
            errors.append(
                f"{where}: baseline_run names a measuring run but baseline is not a measured value"
            )
    return errors


def _parse_check(raw: dict[str, Any]) -> QualityCheck:
    baseline = raw.get("baseline")
    return QualityCheck(
        check_id=str(raw["id"]),
        statement=str(raw["statement"]),
        population=str(raw["population"]),
        placement=frozenset(str(p) for p in raw["placement"]),
        mode=str(raw["mode"]),
        direction=str(raw["direction"]),
        threshold=Threshold.parse(raw["threshold"]),
        baseline=float(baseline) if isinstance(baseline, (int, float)) else None,
        baseline_pending=baseline == "pending",
        unit=str(raw["unit"]),
        basis_class=str(raw["basis_class"]),
        fixing=tuple(str(t) for t in raw.get("fixing", [])),
        source_ids=str(raw["from"]),
        note=str(raw.get("note", "")),
        baseline_run=str(raw.get("baseline_run") or ""),
        baseline_at=str(raw.get("baseline_at") or ""),
    )


def _registry_from_bytes(raw_bytes: bytes, known_rows: set[str] | None = None) -> CheckRegistry:
    """The load+validate core — shared by path and text entry points."""
    doc = tomllib.loads(raw_bytes.decode("utf-8"))
    errors = validate_registry(doc, known_rows)
    if errors:
        raise RegistryError("invalid quality-check registry:\n" + "\n".join(errors))
    checks = tuple(_parse_check(raw) for raw in doc["check"])
    canonical = json.dumps(
        {"version": doc["version"], "checks": [c.check_id for c in checks]},
        sort_keys=True,
    )
    digest = (
        f"{hashlib.sha256(raw_bytes).hexdigest()[:16]}:"
        f"{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"
    )
    return CheckRegistry(version=str(doc["version"]), checks=checks, digest=digest)


def load_registry(
    path: Path | str | None = None, known_rows: set[str] | None = None
) -> CheckRegistry:
    """Load + validate the registry (fail closed — a malformed registry raises)."""
    if path is not None:
        raw_bytes = Path(path).read_bytes()
    else:
        from importlib.resources import files

        raw_bytes = files("exports").joinpath(_REGISTRY_RESOURCE).read_bytes()
    return _registry_from_bytes(raw_bytes, known_rows)


# ---------------------------------------------------------------------------
# The evaluator contract + the ratchet engine


@dataclass(frozen=True)
class Measurement:
    """What a check runner reports for one check — the harness's only input.

    ``offered`` is the candidate population the check addressed; ``evaluated``
    is how many candidates were actually examined (a sampled census evaluates
    fewer than offered, and says so via ``sampled``/``detail``). ``measured``
    is the metric the check's ``direction``/``unit`` describes. A runner that
    cannot evaluate at all returns ``not_evaluable_reason`` instead — the
    check then records ``not_evaluable`` and can never pass.
    """

    check_id: str
    offered: int
    evaluated: int
    measured: float | None = None
    not_evaluable_reason: str | None = None
    sampled: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckOutcome:
    """The ratchet engine's verdict on one check for one run."""

    check_id: str
    mode: str
    basis_class: str
    outcome: str  # "pass" | "fail" | "not_evaluable" | "unbaselined"
    offered: int
    evaluated: int
    measured: float | None
    baseline: float | None
    baseline_pending: bool
    threshold: str
    direction: str
    regression: bool = False
    improvement: bool = False
    alert_band_breach: bool = False
    reason: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def gates(self) -> bool:
        """True when this check may block a run — enforce/gating-basis only."""
        return self.mode in ("enforce", "ratchet") and self.basis_class in (GATING_BASIS_CLASSES)


def evaluate_check(check: QualityCheck, m: Measurement) -> CheckOutcome:
    """Apply the ratchet engine to one check's measurement (SIG-CONF-007)."""
    if m.check_id != check.check_id:
        raise RegistryError(
            f"measurement for {m.check_id!r} cannot evaluate check {check.check_id!r}"
        )
    base = CheckOutcome(
        check_id=check.check_id,
        mode=check.mode,
        basis_class=check.basis_class,
        outcome="pass",
        offered=m.offered,
        evaluated=m.evaluated,
        measured=m.measured,
        baseline=check.baseline,
        baseline_pending=check.baseline_pending,
        threshold=str(check.threshold),
        direction=check.direction,
        detail=dict(m.detail),
    )
    # The evaluator could not run — honest non-result, never a pass.
    if m.not_evaluable_reason:
        return _with(base, outcome="not_evaluable", reason=m.not_evaluable_reason)
    # SIG-ENG-042 — the vacuous-pass guard: a check that examined nothing fails.
    if m.evaluated <= 0:
        return _with(
            base,
            outcome="fail",
            reason=(f"evaluated 0 of {m.offered} offered — no vacuous pass (SIG-ENG-042)"),
        )
    if m.measured is None:
        return _with(
            base,
            outcome="not_evaluable",
            reason="evaluator returned no measured value",
        )
    value = float(m.measured)

    if check.mode == "enforce":
        ok = check.threshold.allows(value)
        return _with(
            base,
            outcome="pass" if ok else "fail",
            reason="" if ok else f"{value:g} violates threshold {check.threshold}",
        )

    if check.mode == "ratchet":
        if check.baseline_pending or check.baseline is None:
            return _with(
                base,
                outcome="unbaselined",
                reason="baseline pending — recorded, does not gate (set by P34.44b)",
            )
        regressed, improved = _compare(value, check.baseline, check.direction)
        if regressed:
            return _with(
                base,
                outcome="fail",
                regression=True,
                reason=(
                    f"{value:g} regresses past baseline {check.baseline:g} "
                    f"({check.direction}; threshold {check.threshold})"
                ),
            )
        return _with(
            base,
            outcome="pass",
            improvement=improved,
            reason=(f"{value:g} improves on baseline {check.baseline:g}" if improved else ""),
        )

    # report — published, never gates; moving the wrong way beyond the band is a
    # Class-S signal (ADR-154). `baseline` on a report row is the last recorded
    # value the alert band is measured against.
    if check.baseline is not None:
        regressed, _ = _compare(value, check.baseline, check.direction)
        if regressed:
            return _with(
                base,
                outcome="pass",
                alert_band_breach=True,
                reason=(
                    f"report metric {value:g} moved the wrong way past "
                    f"{check.baseline:g} — Class S signal"
                ),
            )
    return _with(base, outcome="pass")


def _compare(value: float, baseline: float, direction: str) -> tuple[bool, bool]:
    """Return ``(regressed, improved)`` of ``value`` vs ``baseline``."""
    if direction == "lower_is_better":
        return value > baseline, value < baseline
    return value < baseline, value > baseline


def _with(o: CheckOutcome, **kw: Any) -> CheckOutcome:
    """CheckOutcome is frozen; this is the terse "copy with" helper."""
    return dataclasses.replace(o, **kw)


# ---------------------------------------------------------------------------
# The records


@dataclass(frozen=True)
class RunSummary:
    """Aggregate verdicts for one quality run."""

    overall: str  # "pass" | "fail" | "partial"
    enforce_failures: tuple[str, ...]
    ratchet_regressions: tuple[str, ...]
    unbaselined: tuple[str, ...]
    not_evaluable: tuple[str, ...]
    class_s_trigger: bool
    evaluated_total: int
    offered_total: int


def summarize(outcomes: list[CheckOutcome]) -> RunSummary:
    """Fold per-check outcomes into the run-level verdict."""
    enforce_failures = tuple(
        o.check_id for o in outcomes if o.mode == "enforce" and o.outcome == "fail"
    )
    ratchet_regressions = tuple(o.check_id for o in outcomes if o.regression)
    unbaselined = tuple(o.check_id for o in outcomes if o.outcome == "unbaselined")
    not_evaluable = tuple(o.check_id for o in outcomes if o.outcome == "not_evaluable")
    other_failures = tuple(
        o.check_id
        for o in outcomes
        if o.outcome == "fail" and not o.regression and o.mode != "enforce"
    )
    class_s = bool(ratchet_regressions) or any(o.alert_band_breach for o in outcomes)
    if enforce_failures or ratchet_regressions or other_failures:
        overall = "fail"
    elif unbaselined or not_evaluable:
        overall = "partial"
    else:
        overall = "pass"
    return RunSummary(
        overall=overall,
        enforce_failures=enforce_failures,
        ratchet_regressions=ratchet_regressions,
        unbaselined=unbaselined,
        not_evaluable=not_evaluable,
        class_s_trigger=class_s,
        evaluated_total=sum(o.evaluated for o in outcomes),
        offered_total=sum(o.offered for o in outcomes),
    )


def build_quality_report(
    registry: CheckRegistry,
    outcomes: list[CheckOutcome],
    *,
    placement: str,
    target: str,
    generated_at: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit the ``sig.quality-report/1`` record for one run.

    ``placement`` is the harness placement letter (I/M/R/P/S); ``target`` names
    what was measured (a spine DSN label, a release dir, a capture run id).
    """
    now = (generated_at or datetime.now(UTC)).isoformat()
    summary = summarize(outcomes)
    checks = [
        {
            "id": o.check_id,
            "mode": o.mode,
            "basis_class": o.basis_class,
            "outcome": o.outcome,
            "offered": o.offered,
            "evaluated": o.evaluated,
            "measured": o.measured,
            "baseline": o.baseline,
            "baseline_pending": o.baseline_pending,
            "threshold": o.threshold,
            "direction": o.direction,
            "regression": o.regression,
            "improvement": o.improvement,
            "alert_band_breach": o.alert_band_breach,
            "reason": o.reason,
            "detail": o.detail,
        }
        for o in outcomes
    ]
    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "generated_at": now,
        "placement": placement,
        "target": target,
        "registry": {
            "schema": SCHEMA,
            "version": registry.version,
            "digest": registry.digest,
            "checks_declared": len(registry.checks),
            "checks_evaluated": len(outcomes),
        },
        "checks": checks,
        "totals": {
            "offered": summary.offered_total,
            "evaluated": summary.evaluated_total,
        },
        "summary": {
            "overall": summary.overall,
            "enforce_failures": list(summary.enforce_failures),
            "ratchet_regressions": list(summary.ratchet_regressions),
            "unbaselined": list(summary.unbaselined),
            "not_evaluable": list(summary.not_evaluable),
            "class_s_trigger": summary.class_s_trigger,
        },
    }
    if extra:
        report["extra"] = extra
    return report


def build_probe_run(report: dict[str, Any]) -> dict[str, Any]:
    """Wrap a ``sig.quality-report/1`` in the ``sig.probe-run/1`` envelope
    (SIG-CONF-013) — the same shape ``ops.republish_probe``/``exec_host`` emit:
    ``version`` / ``generated_at`` / ``checks`` / ``overall``, so existing probe
    consumers read a quality run like any other probe run."""
    summary = report["summary"]
    checks = [
        {
            "name": c["id"],
            "outcome": c["outcome"],
            "evaluated": c["evaluated"],
            "offered": c["offered"],
            "reason": c["reason"],
        }
        for c in report["checks"]
    ]
    return {
        "version": PROBE_RUN_VERSION,
        "generated_at": report["generated_at"],
        "probe": "sig-quality",
        "placement": report["placement"],
        "target": report["target"],
        "job": report.get("job", ""),  # the job name when a job ran this (P34.44b)
        "checks": checks,
        "report": report,
        "overall": summary["overall"],
    }


def run_release_gate(report: dict[str, Any]) -> dict[str, Any]:
    """The release-V15 hook (SIG-CONF-007; joins P35.58's V15 suite).

    Consumes a ``sig.quality-report/1`` and returns the gate verdict:
    ``pass`` requires zero ratchet regressions and zero ``enforce`` failures;
    a ``not_evaluable`` ``enforce`` check **fails closed** — a gate that could
    not examine its check does not wave a release through. ``report``-mode and
    ``unbaselined`` ratchet checks never gate.
    """
    if report.get("version") != REPORT_VERSION:
        raise RegistryError(
            f"run_release_gate expects {REPORT_VERSION}, got {report.get('version')!r}"
        )
    enforce_failures = [
        c["id"] for c in report["checks"] if c["mode"] == "enforce" and c["outcome"] == "fail"
    ]
    not_evaluable_enforce = [
        c["id"]
        for c in report["checks"]
        if c["mode"] == "enforce" and c["outcome"] == "not_evaluable"
    ]
    ratchet_regressions = [c["id"] for c in report["checks"] if c["regression"]]
    blocking = sorted(enforce_failures + not_evaluable_enforce + ratchet_regressions)
    return {
        "version": "sig.quality-gate/1",
        "verdict": "fail" if blocking else "pass",
        "enforce_failures": enforce_failures,
        "not_evaluable_enforce": not_evaluable_enforce,
        "ratchet_regressions": ratchet_regressions,
        "class_s": bool(report["summary"]["class_s_trigger"]),
    }


# ---------------------------------------------------------------------------
# The registry diff — the ratchet's rules enforced on the ruleset itself
# (SIG-CONF-007: baselines move only toward thresholds; loosening needs a new
# ADR; enforce flips only in the fixing row)


@dataclass(frozen=True)
class DiffViolation:
    check_id: str
    field: str
    message: str


def diff_registry(
    old: CheckRegistry, new: CheckRegistry, *, ticket: str, adr_ids: tuple[str, ...] = ()
) -> list[DiffViolation]:
    """The ratchet rules applied to a registry change.

    * ``ticket`` is the manifest row landing the change — a mode flip to
      ``enforce`` is allowed only when ``ticket`` is one of the check's
      ``fixing`` rows.
    * ``adr_ids`` are new-ADR citations carried in the change — a baseline or
      threshold *loosening*, or a mode *weakening*, is legal only with one.

    Returns every violation (empty list ⇒ the change is a legal ratchet move).
    """
    violations: list[DiffViolation] = []
    olds, news = old.by_id(), new.by_id()
    loosen = None if adr_ids else "loosening requires a new ADR"
    for cid in sorted(set(olds) - set(news)):
        if loosen:
            violations.append(
                DiffViolation(cid, "check", f"removed check {cid} — removal {loosen}")
            )
    for cid, new_c in sorted(news.items()):
        old_c = olds.get(cid)
        if old_c is None:
            continue  # new check — a declaration, not a ratchet move
        # baseline movement
        if old_c.baseline is not None or new_c.baseline is not None:
            v = _diff_baseline(old_c, new_c, loosen)
            if v:
                violations.append(v)
        # threshold change
        if old_c.threshold != new_c.threshold:
            if not new_c.threshold.strictly_tighter_than(old_c.threshold) and loosen:
                violations.append(
                    DiffViolation(
                        cid,
                        "threshold",
                        f"threshold loosened {old_c.threshold} → {new_c.threshold} — {loosen}",
                    )
                )
        # mode change
        if old_c.mode != new_c.mode:
            violations.extend(_diff_mode(old_c, new_c, ticket, adr_ids))
    return [v for v in violations if v.message]


def _diff_baseline(
    old_c: QualityCheck, new_c: QualityCheck, loosen: str | None
) -> DiffViolation | None:
    if old_c.baseline is None and new_c.baseline is None:
        return None
    if old_c.baseline is None:
        return None  # establishing a baseline is never a loosening
    if new_c.baseline is None:
        if loosen:
            return DiffViolation(
                old_c.check_id,
                "baseline",
                f"baseline {old_c.baseline:g} erased to pending — {loosen}",
            )
        return None
    if new_c.baseline == old_c.baseline:
        return None
    toward = (
        new_c.baseline <= old_c.baseline
        if new_c.direction == "lower_is_better"
        else new_c.baseline >= old_c.baseline
    )
    if toward:
        return None
    if loosen:
        return DiffViolation(
            old_c.check_id,
            "baseline",
            f"baseline moved away from threshold {old_c.baseline:g} → "
            f"{new_c.baseline:g} ({new_c.direction}) — {loosen}",
        )
    return None


def _diff_mode(
    old_c: QualityCheck, new_c: QualityCheck, ticket: str, adr_ids: tuple[str, ...]
) -> list[DiffViolation]:
    out: list[DiffViolation] = []
    if new_c.mode == "enforce" and old_c.mode != "enforce":
        if ticket not in new_c.fixing and ticket not in old_c.fixing:
            out.append(
                DiffViolation(
                    old_c.check_id,
                    "mode",
                    f"ratchet→enforce flip is the fixing row's move — "
                    f"{ticket} is not in fixing={list(new_c.fixing)}",
                )
            )
        if new_c.basis_class not in GATING_BASIS_CLASSES:
            out.append(
                DiffViolation(
                    old_c.check_id,
                    "basis_class",
                    f"basis {new_c.basis_class} may never gate (SIG-CONF-003)",
                )
            )
    elif _mode_rank(new_c.mode) < _mode_rank(old_c.mode):
        if not adr_ids:
            out.append(
                DiffViolation(
                    old_c.check_id,
                    "mode",
                    f"mode weakened {old_c.mode} → {new_c.mode} — loosening requires a new ADR",
                )
            )
    return out


def _mode_rank(mode: str) -> int:
    return {"report": 0, "ratchet": 1, "enforce": 2}[mode]


# ---------------------------------------------------------------------------
# The L2 baseline run — proposal, record and registry apply (P34.44b,
# SIG-CONF-006/007, ADR-154/205). The baseline is set FROM MEASUREMENT: a
# pending baseline takes the measured value; an existing baseline moves only
# toward the threshold when today's measurement is better — a regression is
# recorded as a finding and the baseline stands, never loosened by hand.
# ---------------------------------------------------------------------------


def _check_outcome_map(reports: dict[str, dict[str, Any]]) -> dict[str, tuple[str, dict[str, Any]]]:
    """check_id → (placement, check row) for every measured check across the
    placement reports — a check's placement picks the report that ran it."""
    by_check: dict[str, tuple[str, dict[str, Any]]] = {}
    for placement, report in reports.items():
        for row in report.get("checks", []):
            if row.get("measured") is not None and row.get("outcome") != "not_evaluable":
                by_check.setdefault(str(row["id"]), (str(placement), row))
    return by_check


def baseline_proposal(
    registry: CheckRegistry, reports: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """For each ratchet check: the measured value from the placement report
    that evaluated it and the proposed new baseline.

    * ``baselined`` — a ``pending`` baseline takes today's measured value;
    * ``tightened`` — today's value beats the recorded baseline toward the
      threshold (the ratchet's only legal direction — no ADR needed);
    * ``kept`` — the value stands at the recorded baseline: either equal or
      a **regression** (recorded as a finding; the baseline NEVER loosens
      silently);
    * ``not_measured`` — the run offered no value (``not_evaluable``); the
      baseline is untouched and the check stays pending if it was.
    """
    by_check = _check_outcome_map(reports)
    rows: list[dict[str, Any]] = []
    for check in registry.checks:
        if check.mode != "ratchet":
            continue
        row: dict[str, Any] = {
            "check": check.check_id,
            "unit": check.unit,
            "direction": check.direction,
            "threshold": str(check.threshold),
            "baseline_old": check.baseline,
            "baseline_pending": check.baseline_pending,
            "l2_ref": check.note,
            "fixing": list(check.fixing),
        }
        hit = by_check.get(check.check_id)
        if hit is None:
            row["proposed"] = None
            row["state"] = "not_measured"
        else:
            placement, outcome = hit
            measured = float(outcome["measured"])
            row.update(
                measured=measured,
                placement=placement,
                outcome=outcome.get("outcome"),
                regression=bool(outcome.get("regression")),
            )
            if check.baseline is None:
                row["proposed"] = measured
                row["state"] = "baselined"
            else:
                toward = (
                    measured < check.baseline
                    if check.direction == "lower_is_better"
                    else measured > check.baseline
                )
                if toward:
                    row["proposed"] = measured
                    row["state"] = "tightened"
                else:
                    row["proposed"] = check.baseline
                    row["state"] = "regression_kept" if outcome.get("regression") else "kept"
        rows.append(row)
    return rows


def build_baseline_record(
    *,
    registry: CheckRegistry,
    reports: dict[str, dict[str, Any]],
    target: str,
    run_id: str,
    fetch: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """The ``sig.quality-baseline/1`` record: every check with its L2
    reference (the registry ``from`` ids + the note carrying L2's measured
    value), today's measured value, its outcome, and the baseline proposal —
    plus the counts summary the committed report under
    ``docs/build/reports/quality/`` is rendered from. A check outcome of
    ``fail`` or a ratchet regression is a named finding with its fixing row
    (L2 found 29 of 45 failing — each is reproduced or explained here)."""
    proposal = baseline_proposal(registry, reports)
    by_check_all: dict[str, dict[str, Any]] = {}
    for report in reports.values():
        for row in report.get("checks", []):
            by_check_all.setdefault(str(row["id"]), row)
    comparison: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for check in registry.checks:
        outcome = by_check_all.get(check.check_id) or {}
        comparison.append(
            {
                "id": check.check_id,
                "from": check.source_ids,
                "l2_ref": check.note,
                "mode": check.mode,
                "unit": check.unit,
                "baseline": check.baseline,
                "baseline_pending": check.baseline_pending,
                "measured": outcome.get("measured"),
                "outcome": outcome.get("outcome", "not_run"),
                "reason": outcome.get("reason", ""),
                "regression": bool(outcome.get("regression")),
                "fixing": list(check.fixing),
            }
        )
        if outcome.get("outcome") == "fail" or outcome.get("regression"):
            findings.append(
                {
                    "check": check.check_id,
                    "outcome": outcome.get("outcome"),
                    "measured": outcome.get("measured"),
                    "baseline": check.baseline,
                    "threshold": str(check.threshold),
                    "fixing": list(check.fixing),
                }
            )
    counts = {
        "checks": len(registry.checks),
        "ratchet_checks": sum(1 for c in registry.checks if c.mode == "ratchet"),
        "measured": sum(1 for r in proposal if r.get("measured") is not None),
        "baselined": sum(1 for r in proposal if r["state"] == "baselined"),
        "tightened": sum(1 for r in proposal if r["state"] == "tightened"),
        "kept": sum(1 for r in proposal if r["state"] == "kept"),
        "regressions": sum(1 for r in proposal if r["state"] == "regression_kept"),
        "findings": len(findings),
    }
    record: dict[str, Any] = {
        "version": BASELINE_VERSION,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "run_id": run_id,
        "target": target,
        "registry": {
            "schema": SCHEMA,
            "version": registry.version,
            "digest": registry.digest,
        },
        "placements": sorted(reports),
        "l2_comparison": comparison,
        "proposal": proposal,
        "counts": counts,
        "findings": findings,
        "reports": reports,
    }
    if fetch is not None:
        record["release_fetch"] = fetch
    return record


def apply_baselines(
    registry_text: str,
    proposal: Iterable[dict[str, Any]],
    *,
    run_id: str,
    at: str,
    ticket: str,
    adr_ids: tuple[str, ...] = (),
    known_rows: set[str] | None = None,
) -> str:
    """Rewrite the registry TOML with the proposal's measured baselines and
    return the new text — the ONLY writer of ``baseline_run``/``baseline_at``.

    Every proposal row carrying a ``proposed`` value sets that check's
    ``baseline`` (a ``pending`` resolves to the measured value) and stamps
    ``baseline_run``/``baseline_at`` beside it. The rewrite is then
    re-validated and re-diffed against the original: an illegal ratchet move
    raises ``RegistryError`` — this writer can never emit a loosening, even
    from a hand-crafted proposal.
    """
    if not run_id or not str(run_id).strip():
        raise RegistryError("apply_baselines: run_id must be a non-empty string")
    if not BASELINE_AT_RE.match(str(at)):
        raise RegistryError(f"apply_baselines: --date {at!r} must be YYYY-MM-DD (date -u, OM-04)")
    new_values = {
        str(r["check"]): float(r["proposed"]) for r in proposal if r.get("proposed") is not None
    }
    old = _registry_from_bytes(registry_text.encode("utf-8"), known_rows)
    unknown = sorted(set(new_values) - {c.check_id for c in old.checks})
    if unknown:
        raise RegistryError(f"apply_baselines: proposal names unknown checks {unknown}")

    blocks = re.split(r"(?=^\[\[check\]\])", registry_text, flags=re.M)
    out_blocks: list[str] = []
    for block in blocks:
        m = re.search(r'^id\s*=\s*"(GQ-\d{2})"', block, flags=re.M)
        cid = m.group(1) if m else None
        if cid is None or cid not in new_values:
            out_blocks.append(block)
            continue
        value = new_values[cid]
        baseline_line = f"baseline = {value:g}"
        triple = [
            baseline_line,
            f'baseline_run = "{run_id}"',
            f'baseline_at = "{at}"',
        ]
        lines = block.splitlines()
        new_lines: list[str] = []
        inserted = False
        for line in lines:
            if re.match(r"^baseline\s*=", line):
                if not inserted:
                    new_lines.extend(triple)
                    inserted = True
                continue  # drop the old baseline line (and any duplicate)
            if re.match(r"^baseline_(run|at)\s*=", line):
                continue  # drop stale provenance — ours is written once
            new_lines.append(line)
        if not inserted:
            # A ratchet check always carries a baseline line; defensively
            # insert the triple before `unit =` when the block lacks one.
            for i, line in enumerate(new_lines):
                if re.match(r"^unit\s*=", line):
                    new_lines[i:i] = triple
                    break
            else:
                new_lines.extend(triple)
        # A processed block is rejoined then given its block terminator
        # back — the blank line before the next [[check]] is preserved by
        # the trailing '' element splitlines carries.
        out_blocks.append("\n".join(new_lines) + "\n")
    new_text = "".join(out_blocks)
    new = _registry_from_bytes(new_text.encode("utf-8"), known_rows)
    violations = diff_registry(old, new, ticket=ticket, adr_ids=adr_ids)
    if violations:
        raise RegistryError(
            "apply_baselines: the proposal produced an illegal ratchet move:\n"
            + "\n".join(f"  {v.check_id}.{v.field}: {v.message}" for v in violations)
        )
    return new_text if new_text.endswith("\n") else new_text + "\n"
