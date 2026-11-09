# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""parser_canary — the scheduled fixture-replay parser canary (P37.15).

BL-025's canary part (RISK-P7-06): a scheduled replay of every parser family's
committed sample through the family's own parse + ``canary_findings`` path —
SIG-PARSE-007's fixtures replayed on a cadence so a parser that drifts (a
careless edit, a dependency roll, an image that no longer parses its pinned
shape) raises the typed ``parser_drift`` issue instead of quietly extracting
garbage. The spec — ``tests/parser_canary/spec.toml``
(``sig.parser-canary-spec/1``) — is the committed per-family registry; the
sealed corpus under ``tests/parser_canary/corpus/`` rides the workload image
(its digest pins the corpus version).

Two check kinds:

* ``module`` (default) — a connectors module's ``parse_*`` callable over the
  fixture bytes, then its ``canary_findings`` callable over the parsed doc
  (the SIG-PARSE-008 deterministic core each connector ships for exactly this
  job). Optional ``wrap`` and ``canary_kwargs`` carry the family's call
  conventions (the dot_511 ``{"payload": …}`` envelope; audit_structural's
  ``file_kind``).
* ``structural`` — ``parsing.drift`` expectations declared on the family,
  applied to the parsed JSON sample (the generic §24.3 core).

Every run emits ``sig.parser-canary-report/1`` — one entry per family, the
typed-issue list (``sig.parser-canary-issue/1`` rows: ``issue_class`` ∈
{``parser_drift``, ``canary_error``}) — plus the ``sig.probe-run/1`` envelope
(ops.probe_run), and fires the recorded-alert seam on any issue. The issue
vocabulary is deliberately parallel to J3 §7.3's source-issue classes — a
parser family is not an ingest source, so the classes live in the spec and
never extend ``policy.freshness.AUTO_ISSUE_CLASSES``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, NoReturn

from . import probe_run
from .quality_job import suppression_reason

SCHEMA: Final = "sig.parser-canary-spec/1"
REPORT_SCHEMA: Final = "sig.parser-canary-report/1"
ISSUE_SCHEMA: Final = "sig.parser-canary-issue/1"

#: The drift issue class a replayed family's findings raise — the typed
#: issue this ticket's acceptance shape names ("a mutated fixture raises the
#: drift issue class").
ISSUE_CLASS_DRIFT: Final = "parser_drift"
#: The replay mechanics themselves failed (unreadable fixture, parse raised).
ISSUE_CLASS_ERROR: Final = "canary_error"
ISSUE_CLASSES: Final = frozenset({ISSUE_CLASS_DRIFT, ISSUE_CLASS_ERROR})

#: The bucket-relative prefix the run records land under — inside the
#: conditioned ``ops/probes/`` objectCreator scope (ops/iam_identities.toml).
PARSER_CANARY_PREFIX: Final = "ops/probes/parser-canary/"

#: The alert kind stamped on the recorded alert (ops.alerts seam, ADR-077).
ALERT_KIND: Final = "parser-canary"

#: The modules a ``module``-kind family may resolve against — an allow-list,
#: never an arbitrary import path. Exactly the connectors shipping the
#: SIG-PARSE-008 ``canary_findings`` deterministic cores.
ALLOWED_MODULES: Final = frozenset(
    {
        "connectors.osm",
        "connectors.atlas",
        "connectors.accountability",
        "connectors.audit_structural",
        "connectors.dot_511",
        "connectors.flock_portal",
    }
)

_KINDS: Final = frozenset({"module", "structural"})


class CanarySpecError(ValueError):
    """A ``sig.parser-canary-spec/1`` row or file failed its contract."""


def _fail(msg: str) -> NoReturn:
    raise CanarySpecError(msg)


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# The parsed spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Family:
    """One ``[[family]]`` row — a parser family and its replay contract."""

    family_id: str
    kind: str  # "module" | "structural"
    fixture: str
    module: str = ""
    parse: str = ""
    canary: str = ""
    wrap: str = ""
    canary_kwargs: tuple[tuple[str, str], ...] = ()
    expectations: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class CanarySpec:
    """One parsed ``sig.parser-canary-spec/1`` registry."""

    issue_classes: frozenset[str]
    families: tuple[Family, ...]


def load_spec(path: str | Path) -> CanarySpec:
    """Load + validate the family registry — fail closed on any drift."""
    p = Path(path)
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        _fail(f"parser-canary spec unreadable: {e}")
    if str(doc.get("schema")) != SCHEMA:
        _fail(f"{p}: schema must be {SCHEMA!r}")

    raw_classes = doc.get("issue_classes")
    if (
        not isinstance(raw_classes, list)
        or not raw_classes
        or any(not isinstance(c, str) or not c for c in raw_classes)
    ):
        _fail(f"{p}: issue_classes must be a non-empty list of class names")
    issue_classes = frozenset(str(c) for c in raw_classes)
    if ISSUE_CLASS_DRIFT not in issue_classes:
        _fail(f"{p}: issue_classes must carry {ISSUE_CLASS_DRIFT!r} — the drift class")

    raw_families = doc.get("family")
    if not isinstance(raw_families, list) or not raw_families:
        _fail(f"{p}: at least one [[family]] row is required")
    families: list[Family] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_families):
        where = f"{p}: family {i}"
        if not isinstance(raw, dict):
            _fail(f"{where} must be a table")
        fid = str(raw.get("id") or "")
        if not fid:
            _fail(f"{where}: id required")
        if fid in seen:
            _fail(f"{where}: id {fid!r} declared twice")
        seen.add(fid)
        kind = str(raw.get("kind") or "module")
        if kind not in _KINDS:
            _fail(f"{where}: kind {kind!r} not in {sorted(_KINDS)}")
        fixture = str(raw.get("fixture") or "")
        if not fixture or fixture.startswith("/") or ".." in fixture:
            _fail(f"{where}: fixture {fixture!r} must be a corpus-relative path")

        if kind == "module":
            module = str(raw.get("module") or "")
            if module not in ALLOWED_MODULES:
                _fail(
                    f"{where}: module {module!r} not in the canary allow-list "
                    f"{sorted(ALLOWED_MODULES)} — arbitrary imports are refused"
                )
            parse = str(raw.get("parse") or "")
            canary = str(raw.get("canary") or "")
            if not parse or not canary:
                _fail(f"{where}: parse and canary are required for kind 'module'")
            wrap = str(raw.get("wrap") or "")
            kwargs_raw = raw.get("canary_kwargs") or {}
            if not isinstance(kwargs_raw, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in kwargs_raw.items()
            ):
                _fail(f"{where}: canary_kwargs must be a string→string table")
            if raw.get("expectations"):
                _fail(f"{where}: a module family declares no expectations")
            families.append(
                Family(
                    family_id=fid,
                    kind=kind,
                    fixture=fixture,
                    module=module,
                    parse=parse,
                    canary=canary,
                    wrap=wrap,
                    canary_kwargs=tuple(sorted(kwargs_raw.items())),
                )
            )
        else:
            for absent in ("module", "parse", "canary", "wrap", "canary_kwargs"):
                if raw.get(absent):
                    _fail(f"{where}: a structural family declares no {absent}")
            exps_raw = raw.get("expectations") or []
            if not isinstance(exps_raw, list) or not exps_raw:
                _fail(f"{where}: a structural family needs [[family.expectations]]")
            expectations: list[tuple[str, tuple[str, ...]]] = []
            for j, exp in enumerate(exps_raw):
                if not isinstance(exp, dict):
                    _fail(f"{where}.expectations {j} must be a table")
                desc = str(exp.get("description") or "")
                path_raw = exp.get("path")
                if not desc or not isinstance(path_raw, list) or not path_raw:
                    _fail(f"{where}.expectations {j}: description + non-empty path required")
                exp_path = tuple(str(seg) for seg in path_raw)
                if any(not seg for seg in exp_path):
                    _fail(f"{where}.expectations {j}: empty path segment")
                expectations.append((desc, exp_path))
            families.append(
                Family(
                    family_id=fid,
                    kind=kind,
                    fixture=fixture,
                    expectations=tuple(expectations),
                )
            )
    return CanarySpec(issue_classes=issue_classes, families=tuple(families))


# ---------------------------------------------------------------------------
# The replay — one parser family's committed sample through its own canary
# ---------------------------------------------------------------------------


def _resolve(module_name: str, attr: str) -> Any:
    """Resolve ``module.attr`` — the module is allow-listed at spec load; the
    attribute must exist on the imported module."""
    module = importlib.import_module(module_name)
    fn = getattr(module, attr, None)
    if fn is None or not callable(fn):
        _fail(f"{module_name}.{attr} is not a callable")
    return fn


def replay_family(family: Family, corpus_root: Path) -> dict[str, Any]:
    """Replay one family's committed sample; return the result entry.

    ``findings`` empty → ``ok``; findings → ``drift`` (the typed issue class
    ``parser_drift``); a replay that cannot run (missing fixture, parse
    raised) → ``error`` (``canary_error``) — recorded, never masked.
    """
    entry: dict[str, Any] = {"family": family.family_id, "fixture": family.fixture}
    fixture_path = corpus_root / family.fixture
    try:
        data = fixture_path.read_bytes()
    except OSError as e:
        entry.update(verdict="error", error=f"fixture unreadable: {e}", findings=[])
        return entry
    try:
        if family.kind == "module":
            if family.parse == "json":
                parsed = json.loads(data)
            else:
                parsed = _resolve(family.module, family.parse)(data)
            if family.wrap:
                parsed = {family.wrap: parsed}
            findings = _resolve(family.module, family.canary)(parsed, **dict(family.canary_kwargs))
        else:
            from parsing.drift import EACH, StructuralExpectation, structural_findings

            sample = json.loads(data)
            expectations = [
                StructuralExpectation(desc, tuple(EACH if s == "[]" else s for s in path))
                for desc, path in family.expectations
            ]
            findings = structural_findings(sample, expectations)
    except Exception as e:  # noqa: BLE001 — a raised parser is an error class, recorded
        entry.update(verdict="error", error=f"{type(e).__name__}: {e}", findings=[])
        return entry
    findings = [str(f) for f in findings]
    entry.update(
        verdict="drift" if findings else "ok",
        findings=findings,
        error="",
    )
    return entry


def run_canary(spec: CanarySpec, corpus_root: Path, *, now: str | None = None) -> dict[str, Any]:
    """Replay every declared family and assemble ``sig.parser-canary-report/1``.

    The typed issues: one ``sig.parser-canary-issue/1`` entry per non-clean
    family — ``parser_drift`` on findings, ``canary_error`` on a failed
    replay. ``verdict`` is ``fail`` on any issue, ``pass`` only when every
    family replayed clean (a spec that evaluated nothing is never a pass —
    load_spec refuses an empty family list).
    """
    generated_at = now or _utcnow()
    results = [replay_family(f, corpus_root) for f in spec.families]
    issues: list[dict[str, Any]] = []
    for r in results:
        if r["verdict"] == "ok":
            continue
        issue_class = ISSUE_CLASS_DRIFT if r["verdict"] == "drift" else ISSUE_CLASS_ERROR
        issues.append(
            {
                "schema": ISSUE_SCHEMA,
                "issue_class": issue_class,
                "family": r["family"],
                "fixture": r["fixture"],
                "findings": r["findings"],
                "error": r["error"],
                "basis": (
                    f"{r['family']} replay of {r['fixture']} through the family's "
                    "own parse + canary path"
                ),
            }
        )
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": generated_at,
        "spec": SCHEMA,
        "corpus_root": str(corpus_root),
        "families_evaluated": len(results),
        "families_ok": sum(1 for r in results if r["verdict"] == "ok"),
        "families_drifted": sum(1 for r in results if r["verdict"] == "drift"),
        "families_error": sum(1 for r in results if r["verdict"] == "error"),
        "results": results,
        "issues": issues,
        "verdict": "fail" if issues else "pass",
    }


# ---------------------------------------------------------------------------
# The scheduled leg — window guard, records, upload, alert
# ---------------------------------------------------------------------------


def _stamp(now: str) -> str:
    return now.replace(":", "").replace("-", "")


def _object_name(prefix: str, kind: str, now: str) -> str:
    return f"{prefix}{now[:10]}/{_stamp(now)}-{kind}.json"


def _upload(bucket: Any, name: str, doc: dict[str, Any]) -> None:
    bucket.put_object(
        name,
        (json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8"),
        content_type="application/json",
    )


def _fire_alert(
    message: str,
    *,
    kind: str = ALERT_KIND,
    severity: str = "alarm",
    detail: dict[str, Any] | None = None,
) -> Any:
    """Record the alert, then fan out to every configured sink — the record
    is the deterministic half (ops.alerts, ADR-077)."""
    from .alerts import Alert, AlertLedger, fire, notifiers_from_env

    alert = Alert.create(kind, severity, message, detail=detail or {})
    ledger = AlertLedger(Path(os.environ.get("SIG_ALERT_LOG", ".sig/ops/alerts.jsonl")))
    notifiers = notifiers_from_env()
    fire(alert, ledger=ledger, notifiers=notifiers)
    return alert


def run_scheduled(
    spec_path: Path,
    *,
    corpus_root: Path,
    bucket: Any,
    records_prefix: str,
    out_dir: Path | None,
    job_name: str,
    alert_kind: str = ALERT_KIND,
    no_alert: bool = False,
    now: str | None = None,
) -> int:
    """The ``sig-parser-canary`` job's in-container leg.

    Order: window guard → load the spec → replay every family → write
    ``parser-canary-report.json`` + a ``sig.probe-run/1`` envelope → upload
    both as new timestamped objects under ``records_prefix`` (WORM-shaped,
    never rewritten) → fire the recorded-alert seam on any issue. A
    suppressed or refused run still writes a probe-run record — an empty
    slot is never mistaken for a pass.
    """
    generated_at = now or probe_run.utcnow()

    def _emit(record: dict[str, Any], report: dict[str, Any] | None) -> None:
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            if report is not None:
                (out_dir / "parser-canary-report.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
                )
            probe_run.write_record(record, out_dir / "probe-run.json")
        if bucket is not None:
            _upload(bucket, _object_name(records_prefix, "probe-run", generated_at), record)
            if report is not None:
                _upload(
                    bucket,
                    _object_name(records_prefix, "parser-canary-report", generated_at),
                    report,
                )

    suppressed = suppression_reason(datetime.fromisoformat(generated_at.replace("Z", "+00:00")))
    if suppressed:
        record = probe_run.build_record(
            job_name,
            {"window": probe_run.CheckResult("skipped", {"reason": suppressed})},
            subject={"spec": str(spec_path), "corpus_root": str(corpus_root)},
            now=generated_at,
        )
        _emit(record, None)
        print(f"suppressed: {suppressed} — probe-run record written")
        return 0

    def _fail_leg(name: str, detail: dict[str, Any]) -> int:
        record = probe_run.build_record(
            job_name,
            {name: probe_run.CheckResult("fail", detail)},
            subject={"spec": str(spec_path)},
            now=generated_at,
        )
        _emit(record, None)
        return 1

    try:
        spec = load_spec(spec_path)
    except CanarySpecError as e:
        print(f"FAIL spec refused: {e}", file=sys.stderr)
        if not no_alert:
            fired = _fire_alert(
                f"sig-parser-canary: spec refused — {e}",
                kind=alert_kind,
                severity="alarm",
                detail={"job": job_name, "issue_class": ISSUE_CLASS_ERROR},
            )
            from .alerts import alert_exit_code

            return alert_exit_code(fired)
        return _fail_leg("spec", {"error": str(e)})

    report = run_canary(spec, corpus_root, now=generated_at)
    checks: dict[str, probe_run.CheckResult] = {}
    for r in report["results"]:
        checks[f"family:{r['family']}"] = probe_run.CheckResult(
            "pass" if r["verdict"] == "ok" else "fail",
            {
                "outcome": r["verdict"],
                "fixture": r["fixture"],
                "issue_class": (
                    ISSUE_CLASS_DRIFT
                    if r["verdict"] == "drift"
                    else (ISSUE_CLASS_ERROR if r["verdict"] == "error" else "")
                ),
                "findings": r["findings"],
                "error": r["error"],
            },
        )
    record = probe_run.build_record(
        job_name,
        checks,
        subject={
            "spec": str(spec_path),
            "corpus_root": str(corpus_root),
            "families": [f.family_id for f in spec.families],
        },
        now=generated_at,
    )
    _emit(record, report)
    print(
        f"scheduled parser-canary run complete — verdict {report['verdict']} "
        f"({report['families_ok']} ok, {report['families_drifted']} drifted, "
        f"{report['families_error']} error of {report['families_evaluated']})"
    )
    if report["issues"] and not no_alert:
        classes = sorted({i["issue_class"] for i in report["issues"]})
        fired = _fire_alert(
            f"sig-parser-canary: {len(report['issues'])} typed issue(s) — "
            + ", ".join(f"{i['family']}:{i['issue_class']}" for i in report["issues"]),
            kind=alert_kind,
            severity="alarm",
            detail={
                "job": job_name,
                "issue_classes": classes,
                "issues": report["issues"],
            },
        )
        from .alerts import alert_exit_code

        return alert_exit_code(fired)
    return 0 if report["verdict"] == "pass" else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    # ops/src/ops/parser_canary.py -> ops/src/ops -> ops/src -> ops -> repo root
    return Path(__file__).resolve().parents[3]


def _default_corpus() -> Path:
    return _repo_root() / "tests" / "parser_canary"


def _default_spec(corpus: Path) -> Path:
    return corpus / "spec.toml"


def main(argv: list[str] | None = None) -> int:
    """``sig-ops parser-canary`` — the canary surface (offline/digest-pinned)."""
    parser = argparse.ArgumentParser(
        prog="sig-ops parser-canary",
        description=(
            "P37.15 (BL-025 canary part, SIG-PARSE-007/008): the scheduled "
            "fixture-replay parser canary. `check` validates the spec + corpus "
            "(offline); `run` replays every family and emits "
            "sig.parser-canary-report/1; `scheduled` is the sig-parser-canary "
            "job's in-container command (window guard, records under "
            "ops/probes/parser-canary/, recorded alert on any typed issue); "
            "`job` renders the ops/parser_canary.toml declaration."
        ),
    )
    sub = parser.add_subparsers(dest="canary_command", required=True)

    def _corpus_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--corpus",
            default=None,
            help="canary corpus root holding spec.toml + corpus/ (default tests/parser_canary)",
        )

    p_check = sub.add_parser("check", help="validate the spec + corpus (offline)")
    _corpus_arg(p_check)

    p_run = sub.add_parser("run", help="replay every family (offline)")
    _corpus_arg(p_run)
    p_run.add_argument("--out", default=None, help="write the report under this dir")
    p_run.add_argument("--emit", action="store_true", help="print the report JSON")

    p_sched = sub.add_parser(
        "scheduled",
        help="the sig-parser-canary job command: window guard, replay every "
        "family, emit report + probe-run records under the restricted prefix, "
        "recorded alert on any typed issue",
    )
    _corpus_arg(p_sched)
    p_sched.add_argument(
        "--spec",
        default=None,
        help="the family registry (default <corpus>/spec.toml)",
    )
    p_sched.add_argument(
        "--bucket",
        default=os.environ.get("SIG_OPS_GCS_BUCKET", ""),
        help="restricted bucket (default: SIG_OPS_GCS_BUCKET; empty = local only)",
    )
    p_sched.add_argument(
        "--records-prefix",
        default=os.environ.get("SIG_PARSER_CANARY_PROBE_PREFIX", PARSER_CANARY_PREFIX),
        help="bucket-relative record prefix (inside the ops/probes/ grant)",
    )
    p_sched.add_argument(
        "--job-name",
        default=os.environ.get("SIG_PARSER_CANARY_JOB_NAME", "sig-parser-canary"),
        help="the job name stamped on the probe-run record",
    )
    p_sched.add_argument(
        "--alert-kind",
        default=os.environ.get("SIG_PARSER_CANARY_ALERT_KIND", ALERT_KIND),
        help="the recorded-alert kind",
    )
    p_sched.add_argument(
        "--no-alert",
        action="store_true",
        help="record only — never fire the alert channel",
    )
    p_sched.add_argument("--out", default=None, help="local dir for the two records")
    p_sched.add_argument(
        "--now",
        default=None,
        help="ISO-UTC for the window guard (test hook — a live run reads the clock)",
    )

    p_job = sub.add_parser(
        "job",
        help="the sig-parser-canary declaration surface: plan, render, "
        "verify-describe, verify-trigger — offline verbs "
        "ops/gcp/parser-canary.sh drives",
    )
    job_sub = p_job.add_subparsers(dest="job_command", required=True)
    p_jp = job_sub.add_parser("plan", help="print the validated declaration (offline)")
    p_jp.add_argument("--declaration", default=None)
    p_jr = job_sub.add_parser("render", help="render the whole mutation set as argv JSON")
    p_jr.add_argument("--declaration", default=None)
    p_jr.add_argument("--image", required=True, help="digest-pinned image ref")
    p_jr.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", "<SIG_GCP_PROJECT>"))
    p_jr.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_jr.add_argument(
        "--env",
        dest="env_pairs",
        action="append",
        default=[],
        help="NAME=value for a declared plain env var (repeatable)",
    )
    p_jd = job_sub.add_parser(
        "verify-describe", help="judge a recorded `run jobs describe --format=json`"
    )
    p_jd.add_argument("--declaration", default=None)
    p_jd.add_argument("--describe", required=True)
    p_jd.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt = job_sub.add_parser(
        "verify-trigger", help="judge a recorded `scheduler jobs describe --format=json`"
    )
    p_jt.add_argument("--declaration", default=None)
    p_jt.add_argument("--describe", required=True)
    p_jt.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))

    args = parser.parse_args(argv)
    corpus = Path(args.corpus).resolve() if getattr(args, "corpus", None) else _default_corpus()

    if args.canary_command == "check":
        try:
            spec = load_spec(_default_spec(corpus))
        except CanarySpecError as e:
            print(f"FAIL {e}", file=sys.stderr)
            return 1
        problems: list[str] = []
        for f in spec.families:
            if not (corpus / f.fixture).is_file():
                problems.append(f"{f.family_id}: fixture {f.fixture} missing under {corpus}")
        for p_ in problems:
            print(f"FAIL {p_}", file=sys.stderr)
        if problems:
            return 1
        kinds: dict[str, int] = {}
        for f in spec.families:
            kinds[f.kind] = kinds.get(f.kind, 0) + 1
        print(
            f"check OK — {len(spec.families)} families "
            f"({', '.join(f'{k}={v}' for k, v in sorted(kinds.items()))}), "
            f"issue classes {sorted(spec.issue_classes)}"
        )
        return 0

    if args.canary_command == "run":
        try:
            spec = load_spec(_default_spec(corpus))
        except CanarySpecError as e:
            print(f"FAIL {e}", file=sys.stderr)
            return 1
        report = run_canary(spec, corpus)
        if args.out:
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "parser-canary-report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
            )
        if args.emit or not args.out:
            print(json.dumps(report, indent=2, sort_keys=True, default=str))
        else:
            print(
                f"parser-canary-report.json written under {args.out} — verdict {report['verdict']}"
            )
        return 0 if report["verdict"] == "pass" else 1

    if args.canary_command == "scheduled":
        bucket = None
        if args.bucket:
            from .gcs import GcsBucket

            bucket = GcsBucket(args.bucket)
        spec_path = Path(args.spec).resolve() if args.spec else _default_spec(corpus)
        return run_scheduled(
            spec_path,
            corpus_root=corpus,
            bucket=bucket,
            records_prefix=args.records_prefix,
            out_dir=Path(args.out) if args.out else None,
            job_name=args.job_name,
            alert_kind=args.alert_kind,
            no_alert=args.no_alert,
            now=args.now,
        )

    if args.canary_command == "job":
        from . import parser_canary_job

        try:
            decl = parser_canary_job.load_declaration(args.declaration)
        except ValueError as e:
            print(f"sig-ops parser-canary job: refused — {e}", file=sys.stderr)
            return 4
        if args.job_command == "plan":
            print(
                json.dumps(
                    {
                        "schema": parser_canary_job.SCHEMA,
                        "job": decl.job,
                        "service_account": decl.service_account,
                        "image_repo": decl.image_repo,
                        "command": decl.command,
                        "container_args": list(decl.container_args),
                        "tasks": decl.tasks,
                        "max_retries": decl.max_retries,
                        "task_timeout": decl.task_timeout,
                        "cpu": decl.cpu,
                        "memory": decl.memory,
                        "corpus_root": decl.corpus_root,
                        "probe_prefix": decl.probe_prefix,
                        "alert_kind": decl.alert_kind,
                        "scheduler": vars(decl.scheduler),
                        "secret_env": [vars(s) for s in decl.secret_env],
                        "plain_env": list(decl.plain_env),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.job_command == "render":
            env_values = {}
            for pair in args.env_pairs:
                name, _, value = pair.partition("=")
                env_values[name] = value
            try:
                rendered = parser_canary_job.render(
                    decl,
                    project=args.project,
                    region=args.region,
                    image=args.image,
                    env_values=env_values,
                )
            except ValueError as e:
                print(f"sig-ops parser-canary job render: refused — {e}", file=sys.stderr)
                return 4
            print(json.dumps(rendered, indent=2, sort_keys=True))
            return 0
        if args.job_command == "verify-describe":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = parser_canary_job.verify_describe(decl, describe, project=args.project)
            for d in diffs:
                print(f"DRIFT {d}", file=sys.stderr)
            return 1 if diffs else 0
        if args.job_command == "verify-trigger":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = parser_canary_job.verify_trigger(
                decl, describe, project=args.project, region=args.region
            )
            for d in diffs:
                print(f"DRIFT {d}", file=sys.stderr)
            return 1 if diffs else 0

    return 2  # pragma: no cover


__all__ = [
    "ALERT_KIND",
    "ALLOWED_MODULES",
    "ISSUE_CLASSES",
    "ISSUE_CLASS_DRIFT",
    "ISSUE_CLASS_ERROR",
    "ISSUE_SCHEMA",
    "PARSER_CANARY_PREFIX",
    "REPORT_SCHEMA",
    "SCHEMA",
    "CanarySpec",
    "CanarySpecError",
    "Family",
    "load_spec",
    "main",
    "replay_family",
    "run_canary",
    "run_scheduled",
]
