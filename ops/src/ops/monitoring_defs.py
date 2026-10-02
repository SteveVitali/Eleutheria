# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Committed monitoring definitions and the live diff (P34.4 — QA-3/QA-4/QA-5).

``ops/monitoring/*.json`` declares the whole alert set — the notification
channel, the uptime checks and every alert policy — in Google Cloud Monitoring
REST shape **minus volatile fields**, with ``{project}`` templated. Each file
carries a ``_sig`` envelope::

    {"kind": "channel|uptime|policy",
     "id": "<numeric/config id, or null to match on displayName>",
     "displayName": "<human name>",
     "apply": "diff-only|create|update",
     "source": "<where the definition came from>"}

``verify`` normalises live resources the same way and reports one line per
declared resource — ``OK`` / ``DRIFT`` / ``MISSING`` — plus ``EXTRA`` for a live
resource no file declares. It never prints or persists credentials, and a
definition leaf whose value starts with ``<`` (``<redacted …>``) is a
placeholder that never compares — the operator's e-mail address is never
committed, so its live value can never drift the diff.

The live side is a plain mapping ``{"channels": [...], "uptime_checks": [...],
"policies": [...]}`` of the full-fidelity ``gcloud … list --format=json``
bodies, so the same diff runs against ``--from-state`` capture directories
offline (the shape ``ops/gcp/alerts.sh`` writes, and the shape P35.3's probe
needs as a real eval).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Directory the committed definitions live in, relative to the repo root.
DEFS_DIR = Path("ops/monitoring")

#: Output-only fields that never participate in a diff (server-assigned).
VOLATILE_KEYS = frozenset(
    {
        "name",
        "creationRecord",
        "mutationRecord",
        "mutationRecords",
        "verificationStatus",
    }
)

#: A definition leaf whose whole value looks like a placeholder never compares.
PLACEHOLDER_RE = re.compile(r"^<.*>$", re.S)

_KIND_LIST_KEY = {"channel": "channels", "uptime": "uptime_checks", "policy": "policies"}
_KIND_ORDER = ("channel", "uptime", "policy")


@dataclass(frozen=True)
class Definition:
    """One committed definition: its envelope plus the templated REST body."""

    kind: str  # channel | uptime | policy
    rid: str | None  # server id to match on; None => match by displayName
    display_name: str
    apply: str  # diff-only | create | update
    body: Mapping[str, Any]
    path: Path

    @property
    def slug(self) -> str:
        return self.path.stem


@dataclass(frozen=True)
class Finding:
    """One verify result row."""

    status: str  # OK | DRIFT | MISSING | EXTRA
    kind: str
    slug: str
    detail: str = ""


class DefsError(ValueError):
    """A definition file is malformed or unmatchable."""


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER_RE.match(value))


def _substitute(obj: Any, project: str) -> Any:
    """Replace ``{project}`` inside every string leaf."""
    if isinstance(obj, str):
        return obj.replace("{project}", project)
    if isinstance(obj, dict):
        return {k: _substitute(v, project) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, project) for v in obj]
    return obj


def _strip_volatile(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


def normalize(kind: str, obj: Mapping[str, Any], project: str) -> Any:
    """The comparable form of a definition body or a live resource.

    Drops volatile keys (recursively — a policy condition's ``name`` is
    volatile too), resolves ``{project}``, removes ``_sig``, and replaces any
    ``<placeholder>`` leaf in the *definition* side's favour upstream — here we
    only normalise structure; placeholder matching happens in ``_equal``.
    """
    stripped = _strip_volatile(dict(obj))
    stripped.pop("_sig", None)
    return _substitute(stripped, project)


def _diffs(expected: Any, live: Any, path: str = "") -> list[str]:
    """Structural diff; ``<placeholder>`` leaves in *expected* never compare."""
    if _is_placeholder(expected):
        return []
    if isinstance(expected, dict) and isinstance(live, dict):
        out: list[str] = []
        for key in sorted(set(expected) | set(live)):
            if key not in expected:
                out.append(f"{path}.{key}: live-only")
            elif key not in live:
                out.append(f"{path}.{key}: missing live")
            else:
                out.extend(_diffs(expected[key], live[key], f"{path}.{key}"))
        return out
    if isinstance(expected, list) and isinstance(live, list):
        if len(expected) != len(live):
            return [f"{path}: len {len(live)} != {len(expected)}"]
        out = []
        for i, (e, lv) in enumerate(zip(expected, live, strict=True)):
            out.extend(_diffs(e, lv, f"{path}[{i}]"))
        return out
    if expected != live:
        return [f"{path}: live={live!r} != def={expected!r}"]
    return []


def _equal(expected: Any, live: Any) -> tuple[bool, str]:
    ds = _diffs(expected, live)
    return (not ds, "; ".join(ds[:3]) + (" …" if len(ds) > 3 else ""))


def _resource_id(obj: Mapping[str, Any]) -> str:
    name = str(obj.get("name", ""))
    return name.rsplit("/", 1)[-1] if name else ""


def load_definitions(defs_dir: Path | str) -> list[Definition]:
    """Load every ``*.json`` under ``defs_dir`` (sorted — deterministic)."""
    root = Path(defs_dir)
    if not root.is_dir():
        raise DefsError(f"{root} is not a directory")
    out: list[Definition] = []
    for path in sorted(root.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise DefsError(f"{path.name}: invalid JSON: {exc}") from exc
        sig = doc.get("_sig")
        if not isinstance(sig, dict):
            raise DefsError(f"{path.name}: missing the _sig envelope")
        kind = str(sig.get("kind", ""))
        if kind not in _KIND_LIST_KEY:
            raise DefsError(f"{path.name}: _sig.kind must be one of {_KIND_ORDER}")
        apply = str(sig.get("apply", ""))
        if apply not in {"diff-only", "create", "update"}:
            raise DefsError(f"{path.name}: _sig.apply must be diff-only|create|update")
        rid = sig.get("id")
        display = str(sig.get("displayName") or doc.get("displayName") or "")
        if rid is None and not display:
            raise DefsError(f"{path.name}: needs _sig.id or a displayName to match on")
        body = {k: v for k, v in doc.items() if k != "_sig"}
        out.append(Definition(kind, None if rid is None else str(rid), display, apply, body, path))
    return out


def _find_live(defn: Definition, live: Mapping[str, list]) -> Mapping[str, Any] | None:
    for obj in live.get(_KIND_LIST_KEY[defn.kind], []):
        if defn.rid is not None:
            if _resource_id(obj) == defn.rid:
                return obj
        elif str(obj.get("displayName")) == defn.display_name:
            return obj
    return None


def _render_value(v: Any) -> str:
    return json.dumps(v, sort_keys=True)[:120]


def verify_definitions(
    defs: Iterable[Definition], live: Mapping[str, list], project: str
) -> list[Finding]:
    """Diff every definition against the live state; also flag EXTRA live rows.

    Returns one :class:`Finding` per declared resource, then one ``EXTRA`` per
    live resource no definition claims (matched by id, else displayName).
    """
    findings: list[Finding] = []
    claimed: dict[str, set[str]] = {k: set() for k in _KIND_LIST_KEY}
    for defn in defs:
        live_obj = _find_live(defn, live)
        if live_obj is None:
            findings.append(
                Finding("MISSING", defn.kind, defn.slug, f"no live {defn.display_name!r}")
            )
            continue
        claimed[defn.kind].add(str(live_obj.get("name")))
        expected = normalize(defn.kind, defn.body, project)
        actual = normalize(defn.kind, live_obj, project)
        eq, detail = _equal(expected, actual)
        findings.append(
            Finding("OK" if eq else "DRIFT", defn.kind, defn.slug, "" if eq else detail)
        )
    for kind in _KIND_ORDER:
        for obj in live.get(_KIND_LIST_KEY[kind], []):
            if str(obj.get("name")) not in claimed[kind]:
                findings.append(
                    Finding(
                        "EXTRA",
                        kind,
                        _resource_id(obj) or str(obj.get("displayName", "?")),
                        f"live-only {obj.get('displayName')!r}",
                    )
                )
    return findings


def live_from_lists(channels: list, uptime_checks: list, policies: list) -> dict[str, list]:
    return {"channels": channels, "uptime_checks": uptime_checks, "policies": policies}


def infer_project(live: Mapping[str, list]) -> str:
    """The project id from the first live resource name, else "".

    ``--from-state`` verification needs no env: the captured ``name`` fields
    already carry ``projects/<id>/…``.
    """
    for objs in live.values():
        for obj in objs:
            m = re.match(r"^projects/([^/]+)/", str(obj.get("name", "")))
            if m:
                return m.group(1)
    return ""


def load_live_dir(state_dir: Path | str) -> dict[str, list]:
    """The ``--from-state`` loader: the three list-JSON files a capture writes.

    ``channels.json``, ``uptime-checks.json``, ``alert-policies.json`` — missing
    files read as empty lists (a partial capture diffs as MISSING, never as OK).
    """
    root = Path(state_dir)
    live: dict[str, list] = {"channels": [], "uptime_checks": [], "policies": []}
    names = {
        "channels": "channels.json",
        "uptime_checks": "uptime-checks.json",
        "policies": "alert-policies.json",
    }
    for key, fname in names.items():
        path = root / fname
        if path.is_file():
            doc = json.loads(path.read_text())
            if not isinstance(doc, list):
                raise DefsError(f"{fname}: expected a list")
            live[key] = doc
    return live


def format_findings(findings: Iterable[Finding]) -> str:
    """The P35.3-probe line shape: per-row status + the summary + probe line."""
    findings = list(findings)
    lines = []
    for f in findings:
        lines.append(f"{f.status} {f.kind}/{f.slug}" + (f" — {f.detail}" if f.detail else ""))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    bad = sum(counts.get(s, 0) for s in ("DRIFT", "MISSING", "EXTRA"))
    ok = counts.get("OK", 0)
    lines.append(f"verify: {ok} OK, {bad} not-OK ({counts})")
    lines.append("probe: monitoring-defs-verify result=" + ("ok" if bad == 0 else "drift"))
    return "\n".join(lines)


def verify_exit_code(findings: Iterable[Finding]) -> int:
    return 0 if all(f.status == "OK" for f in findings) else 1


def render_policy_body(defn: Definition, project: str) -> dict[str, Any]:
    """The JSON body ``gcloud monitoring policies create|update`` consumes —
    the def body with ``{project}`` resolved and ``_sig`` already stripped."""
    if defn.kind != "policy":
        raise DefsError(f"{defn.slug}: not a policy def")
    return normalize("policy", defn.body, project)
