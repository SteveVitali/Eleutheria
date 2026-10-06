#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The non-vacuous npm advisory gate (P34.2 deliverable 6, SIG-ENG-042).

Reads an ``npm audit --json`` report and judges it at ``--level`` (default
``high``): every *leaf* advisory finding at or above the level must be covered
by a live entry of the committed allow-list
(``docs/build/tools/record_policy/npm_audit_allow.toml``) — an entry with an
``expires`` date that has passed no longer covers and is itself a failure, so
an allowance can never silently outlive its grant.

Findings below the level are reported, not judged — a new moderate advisory is
visible in the log without going red. Dependency-chain nodes (``via`` entries
that are strings) carry no advisory of their own; covering the leaf covers the
chain. ``--prod-audit`` (an ``npm audit --omit=dev --json`` report) cross-checks
``scope = "dev-only"`` entries: a package that still appears in the production
audit was never dev-only — the entry is void.

Non-vacuous (SIG-ENG-042): the report must be a real ``npm audit --json`` shape
(``vulnerabilities`` + ``metadata.vulnerabilities`` present); the gate prints
``candidates``/``evaluated``/``allowed``/``blocked`` counts, and an audit that
cannot be read is UNKNOWN — never green.

Exit: 0 covered · 3 a finding at/above the level is uncovered (or an entry
expired / lied about its scope) · 5 unreadable audit or policy · 1 usage.

Usage::

    npm --prefix web audit --omit=dev --json > prod.json || test $? -le 1
    npm_audit_gate.py --audit prod.json --level high          # per-PR gate

    npm --prefix web audit --json > full.json || test $? -le 1
    npm_audit_gate.py --audit full.json --prod-audit prod.json  # nightly
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

EXIT_OK, EXIT_USAGE, EXIT_BLOCK, EXIT_UNKNOWN = 0, 1, 3, 5
SEVERITY = {"info": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}
DEFAULT_POLICY = "docs/build/tools/record_policy/npm_audit_allow.toml"


class UsageParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"npm_audit_gate.py: {message}", file=sys.stderr)
        sys.exit(EXIT_USAGE)


@dataclass
class Finding:
    package: str
    advisory: str  # GHSA-… (the advisory url's last segment), or the source id
    severity: str
    title: str


@dataclass
class Allow:
    id: str
    package: str
    advisories: list[str]
    scope: str  # "dev-only" | "prod"
    reason: str
    tracking: str
    expires: date


def advisory_id(via: dict[str, Any]) -> str:
    url = str(via.get("url") or "")
    if url:
        return url.rstrip("/").rsplit("/", 1)[-1]
    return str(via.get("source") or via.get("name") or "unknown")


def findings(audit: dict[str, Any]) -> list[Finding]:
    """Every leaf advisory (a dict `via` entry) of every vulnerable package."""
    out: list[Finding] = []
    vulns = audit.get("vulnerabilities")
    if not isinstance(vulns, dict):
        raise ValueError("audit report has no `vulnerabilities` object")
    for package, vul in vulns.items():
        if not isinstance(vul, dict):
            continue
        for via in vul.get("via") or []:
            if isinstance(via, dict):
                out.append(
                    Finding(
                        package=package,
                        advisory=advisory_id(via),
                        severity=str(via.get("severity") or "info").lower(),
                        title=str(via.get("title") or ""),
                    )
                )
    return out


def load_audit(path: str) -> dict[str, Any]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read the audit report {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("the audit report is not a JSON object")
    meta = doc.get("metadata")
    if not isinstance(meta, dict) or not isinstance(
        (meta.get("vulnerabilities") or {}).get("total"), int
    ):
        raise ValueError(
            "the audit report lacks `metadata.vulnerabilities.total` — it is not "
            "a real `npm audit --json` document (a vacuous gate is a red gate)"
        )
    return doc


def load_policy(path: Path) -> list[Allow]:
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read the allow-list {path}: {exc}") from exc
    out: list[Allow] = []
    for entry in doc.get("allow", []):
        try:
            out.append(
                Allow(
                    id=str(entry["id"]),
                    package=str(entry["package"]),
                    advisories=[str(a) for a in entry["advisories"]],
                    scope=str(entry.get("scope") or "prod"),
                    reason=str(entry.get("reason") or ""),
                    tracking=str(entry.get("tracking") or ""),
                    expires=date.fromisoformat(str(entry["expires"])),
                )
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"allow-list entry {entry.get('id') or '?'} is malformed: {exc} "
                "(each entry needs id/package/advisories/scope/reason/tracking/expires)"
            ) from exc
    return out


def main(argv: list[str] | None = None) -> int:
    ap = UsageParser(
        prog="npm_audit_gate.py",
        description="Non-vacuous npm advisory gate (P34.2, SIG-ENG-042).",
    )
    ap.add_argument("--audit", required=True, metavar="PATH", help="`npm audit --json` output")
    ap.add_argument(
        "--prod-audit",
        metavar="PATH",
        help="an `npm audit --omit=dev --json` report — cross-checks dev-only entries",
    )
    ap.add_argument("--level", default="high", choices=list(SEVERITY))
    ap.add_argument(
        "--policy", metavar="PATH", help=f"allow-list (default: <repo>/{DEFAULT_POLICY})"
    )
    ap.add_argument(
        "--today", metavar="YYYY-MM-DD", help="override 'today' (tests); default is UTC now"
    )
    ap.add_argument("--json", metavar="PATH", help="optional JSON result record")
    args = ap.parse_args(argv)

    level = SEVERITY[args.level]
    today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
    try:
        audit = load_audit(args.audit)
        all_findings = findings(audit)
        policy_path = Path(args.policy) if args.policy else Path(DEFAULT_POLICY)
        allow = load_policy(policy_path)
        prod_packages: set[str] = set()
        if args.prod_audit:
            prod_audit = load_audit(args.prod_audit)
            prod_packages = set(prod_audit.get("vulnerabilities") or {})
    except ValueError as exc:
        print(f"npm-audit-gate: {exc}", file=sys.stderr)
        return EXIT_UNKNOWN

    candidates = [f for f in all_findings if SEVERITY.get(f.severity, 0) >= level]
    below = len(all_findings) - len(candidates)
    blocked: list[str] = []
    allowed = 0
    for f in candidates:
        entry = next(
            (e for e in allow if e.package == f.package and f.advisory in e.advisories),
            None,
        )
        if entry is None:
            blocked.append(
                f"{f.package} {f.advisory} ({f.severity}) — no allow-list entry: {f.title[:100]}"
            )
            continue
        if entry.expires < today:
            blocked.append(
                f"{f.package} {f.advisory} — allow entry {entry.id} expired "
                f"{entry.expires.isoformat()} (renew it deliberately or fix the advisory)"
            )
            continue
        if entry.scope == "dev-only" and f.package in prod_packages:
            blocked.append(
                f"{f.package} {f.advisory} — entry {entry.id} claims dev-only but the "
                "package is vulnerable in the production audit (`--omit=dev`)"
            )
            continue
        allowed += 1
    # An expired entry fails loudly even when nothing currently needs it —
    # a dead grant is refreshed deliberately or removed, never kept stale.
    for e in allow:
        if e.expires < today:
            blocked.append(f"allow-list entry {e.id} ({e.package}) expired {e.expires.isoformat()}")
        live_hits = [
            f
            for f in candidates
            if f.package == e.package and f.advisory in e.advisories and e.expires >= today
        ]
        if not live_hits and e.expires >= today:
            print(
                f"npm-audit-gate: note — entry {e.id} ({e.package}) covers no current "
                "finding; remove it when the upstream fix lands",
                file=sys.stderr,
            )

    report = {
        "schema": "npm-audit-gate/1",
        "level": args.level,
        "candidates": len(candidates),
        "below_level": below,
        "evaluated": len(candidates),
        "allowed": allowed,
        "blocked": len(blocked),
        "failures": blocked,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for line in blocked:
        print(f"npm-audit-gate: BLOCK {line}", file=sys.stderr)
    print(
        f"npm-audit-gate: level={args.level} candidates={len(candidates)} "
        f"evaluated={len(candidates)} allowed={allowed} blocked={len(blocked)} "
        f"(below-level findings: {below})"
    )
    return EXIT_BLOCK if blocked else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
