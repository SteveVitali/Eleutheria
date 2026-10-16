# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""truth_scan — the fixture-sentinel scan + claim-marker binding (P35.3; G10,
SIG-OPS-012 + DRAFT-OPS-2 sentinels, DR-C3-03 human-completion markers).

Two scanners over the same committed table (``ops/sentinels.toml``):

* **sentinel-scan** — sweeps the declared scan roots (the release-candidate
  build output ``--rc``, the public web build ``web/dist`` / ``--scan``, a
  sampled live API response set ``--api-sample``) for the declared sentinels:
  ``example.test``, ``sig.example``, ``_FIXTURE``, ``demo_``, ``Reviewer A/B``,
  loopback URLs, ``capture_kind: stand-in`` without a sibling disclosure, and
  — over the source registry — unregistered contact domains. A hit inside a
  declared fixture compartment passes only when that compartment's ``allow``
  list names the sentinel; a hit anywhere else fails. An undeclared
  compartment never exempts.

* **claim-marker-scan** — "human-verified" / "Reviewed" / "independent
  review" assertions count only where a recorded human-completion marker
  exists: a ``marker:<path>`` citation in the same file resolving to a
  committed record carrying ``reviewer:`` (a human, never an agent label),
  ``recorded`` and ``subject:`` tokens.

Findings carry ``path:line + sentinel id`` — never the matched text — so a
result is redaction-safe. Both emit ``sig.probe-run/1`` via ``ops.probe_run``
(the one record format); offered/evaluated counts ride every leg and a run
that offered candidates but evaluated none fails (SIG-ENG-042).
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .probe_run import CheckResult, build_record
from .republish_probe import attribution_sample_check

REPO_ROOT = Path(__file__).resolve().parents[3]
SENTINELS_PATH = REPO_ROOT / "ops" / "sentinels.toml"
DEFERRALS_PATH = REPO_ROOT / "docs" / "tickets" / "DEFERRALS.md"

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".astro", ".pytest_cache"}
_MAX_FILE_BYTES = 8 * 1024 * 1024
_RULES = {"capture-kind-standin-disclosure"}
_SENTINEL_KINDS = {"literal", "regex", "rule"}
_STANDIN_RE = re.compile(r"stand[-_ ]?in", re.I)
_CAPTURE_KIND_RE = re.compile(r"capture_?kind", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_URL_HOST_RE = re.compile(r"https?://([^/\s'\"<>]+)")
_DOMAIN_RE = re.compile(r"\b([a-z0-9-]+(\.[a-z0-9-]+)+)\b", re.I)
_MARKER_CITE_RE = re.compile(r"\bmarker\s*:\s*([A-Za-z0-9_./~-]+)")
_REVIEWER_RE = re.compile(r"\breviewer\s*:\s*(.+)")


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """`**` = any depth (incl. zero), `*` = within a segment — glob → regex."""
    parts = pattern.split("/")
    out = ["^"]
    for i, seg in enumerate(parts):
        last = i == len(parts) - 1
        if seg == "**":
            out.append(".*" if last else r"(?:[^/]+(?:/|$))*")
        else:
            seg_r = re.escape(seg).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
            out.append(seg_r + ("" if last else "/"))
    out.append("$")
    return re.compile("".join(out))


@dataclass(frozen=True)
class Sentinel:
    id: str
    kind: str  # literal | regex | rule
    pattern: str
    note: str
    rx: re.Pattern[str] | None = None


@dataclass(frozen=True)
class Compartment:
    id: str
    paths: tuple[str, ...]
    allow: frozenset[str]  # sentinel/claim-marker ids, or {"all"}
    reason: str
    debt: str
    globs: tuple[re.Pattern[str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ClaimMarker:
    id: str
    assert_res: tuple[re.Pattern[str], ...]
    safe_res: tuple[re.Pattern[str], ...]


@dataclass
class SentinelsConfig:
    sentinels: list[Sentinel] = field(default_factory=list)
    compartments: list[Compartment] = field(default_factory=list)
    claim_markers: list[ClaimMarker] = field(default_factory=list)
    marker_globs: list[re.Pattern[str]] = field(default_factory=list)
    marker_required: list[str] = field(default_factory=list)
    marker_agent_label: re.Pattern[str] | None = None
    contact_sources: list[str] = field(default_factory=list)
    contact_fields: list[str] = field(default_factory=list)
    registered_domains: set[str] = field(default_factory=set)
    standin_disclosure_keys: list[str] = field(default_factory=list)
    standin_posture_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    """One violation — path:line + id, never the matched bytes (redaction-safe)."""

    check: str  # leg id, e.g. "sentinels", "contact-domains", "assertions"
    sentinel: str  # sentinel / claim-marker id
    path: str
    line: int
    note: str = ""

    def as_json(self) -> dict[str, Any]:
        d = {"sentinel": self.sentinel, "path": self.path, "line": self.line}
        if self.note:
            d["note"] = self.note
        return d


def load_sentinels(path: Path) -> tuple[SentinelsConfig, list[str]]:
    """Validate the committed table; ``(config, errors)`` — errors ⇒ unusable."""
    cfg = SentinelsConfig()
    errors: list[str] = []
    if not path.is_file():
        return cfg, [f"{path}: sentinels table not found"]
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        return cfg, [f"{path}: TOML parse error: {e}"]
    if doc.get("schema") != "sig.sentinels/1":
        errors.append(f"{path}: schema {doc.get('schema')!r} != 'sig.sentinels/1'")

    cfg.standin_disclosure_keys = list(doc.get("standin_disclosure_keys") or [])
    cfg.standin_posture_keys = list(doc.get("standin_posture_keys") or [])
    if not cfg.standin_disclosure_keys and not cfg.standin_posture_keys:
        errors.append(
            "no standin_disclosure_keys/posture_keys — the stand-in leg needs its disclosure keys"
        )

    seen: set[str] = set()
    for i, s in enumerate(doc.get("sentinel", [])):
        sid = str(s.get("id", f"#{i}"))
        where = f"sentinel {sid!r}"
        if sid in seen:
            errors.append(f"{where}: duplicate sentinel id")
        seen.add(sid)
        kind = s.get("kind")
        pattern = str(s.get("pattern", ""))
        if kind not in _SENTINEL_KINDS:
            errors.append(f"{where}: kind {kind!r} not in {sorted(_SENTINEL_KINDS)}")
            continue
        if kind == "rule":
            if pattern not in _RULES:
                errors.append(f"{where}: rule {pattern!r} not a named rule ({sorted(_RULES)})")
            rx = None
        elif kind == "literal":
            rx = re.compile(re.escape(pattern))
        else:
            try:
                rx = re.compile(pattern)
            except re.error as e:
                errors.append(f"{where}: regex does not compile: {e}")
                continue
        cfg.sentinels.append(Sentinel(sid, kind, pattern, str(s.get("note", "")), rx))
    sentinel_ids = set(seen)

    marker_ids: set[str] = set()
    for i, m in enumerate(doc.get("claim_marker", [])):
        mid = str(m.get("id", f"#{i}"))
        where = f"claim_marker {mid!r}"
        marker_ids.add(mid)
        try:
            assert_res = tuple(re.compile(p) for p in m.get("assert", []))
            safe_res = tuple(re.compile(p) for p in m.get("safe", []))
        except re.error as e:
            errors.append(f"{where}: pattern does not compile: {e}")
            continue
        if not assert_res:
            errors.append(
                f"{where}: no assert patterns — a marker asserting nothing checks nothing"
            )
        cfg.claim_markers.append(ClaimMarker(mid, assert_res, safe_res))
    exemptible = sentinel_ids | marker_ids | {"all"}

    for i, c in enumerate(doc.get("compartment", [])):
        cid = str(c.get("id", f"#{i}"))
        where = f"compartment {cid!r}"
        paths = tuple(str(p) for p in (c.get("paths") or []))
        allow = frozenset(str(a) for a in (c.get("allow") or []))
        if not paths:
            errors.append(f"{where}: no paths — a compartment declares where it binds")
        bad = sorted(allow - exemptible)
        if bad:
            errors.append(
                f"{where}: allow names undeclared ids {bad} — an undeclared "
                "compartment/sentinel never exempts"
            )
        if not str(c.get("reason", "")).strip():
            errors.append(f"{where}: no reason — a fixture compartment declares why it exists")
        globs: list[re.Pattern[str]] = []
        for p in paths:
            try:
                globs.append(_glob_regex(p))
            except re.error as e:
                errors.append(f"{where}: path {p!r}: {e}")
        cfg.compartments.append(
            Compartment(
                cid,
                paths,
                allow,
                str(c.get("reason", "")),
                str(c.get("debt", "")),
                tuple(globs),
            )
        )

    markers = doc.get("markers") or {}
    cfg.marker_globs = [_glob_regex(g) for g in markers.get("record_glob", [])]
    cfg.marker_required = [str(t) for t in markers.get("required", [])]
    agent = str(markers.get("agent_label", ""))
    cfg.marker_agent_label = re.compile(agent) if agent else None
    if not cfg.marker_globs or not cfg.marker_required:
        errors.append(
            "[markers]: record_glob + required — the marker-record shape must be declared"
        )

    contact = doc.get("contact_registry") or {}
    cfg.contact_sources = [str(s) for s in contact.get("sources", [])]
    cfg.contact_fields = [str(f) for f in contact.get("fields", [])]
    cfg.registered_domains = {
        str(d).lower()
        for d in (contact.get("registered_domains") or doc.get("registered_domains") or [])
    }
    if not cfg.registered_domains:
        errors.append(
            "no registered_domains — an unregistered-domain check with no registry is vacuous"
        )
    return cfg, errors


# --- scanning primitives -------------------------------------------------------


def _iter_files(roots: list[Path], repo_root: Path) -> list[tuple[Path, str, list[str]]]:
    """``(abs, display, match_variants)`` — repo-rel when under root, else
    scan-root-rel; compartments may match either."""
    out: list[tuple[Path, str, list[str]]] = []
    for root in roots:
        if not root.is_dir():
            continue
        base = root.resolve()
        for p in sorted(base.rglob("*")):
            if not p.is_file() or any(part in _SKIP_DIRS for part in p.parts):
                continue
            try:
                if p.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            variants: list[str] = []
            try:
                variants.append(str(p.resolve().relative_to(repo_root.resolve())))
            except ValueError:
                pass
            try:
                variants.append(str(p.relative_to(base)))
            except ValueError:
                pass
            disp = variants[0] if variants else str(p)
            out.append((p, disp, variants))
    return out


def _is_probably_text(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(8192)
    except OSError:
        return False
    return b"\x00" not in head


def _compartment_for(
    cfg: SentinelsConfig, variants: list[str], sentinel_id: str
) -> Compartment | None:
    for comp in cfg.compartments:
        if "all" not in comp.allow and sentinel_id not in comp.allow:
            continue
        if any(g.match(v) for g in comp.globs for v in variants):
            return comp
    return None


# --- the stand-in-disclosure rule leg -------------------------------------------

_STANDIN_KIND_RE = re.compile(r"""["']?capture_?kind["']?\s*[:=]\s*["']?stand[-_]?in""", re.I)


def _walk_tables(obj: Any) -> list[dict]:
    tables: list[dict] = []
    if isinstance(obj, dict):
        tables.append(obj)
        for v in obj.values():
            tables.extend(_walk_tables(v))
    elif isinstance(obj, list):
        for v in obj:
            tables.extend(_walk_tables(v))
    return tables


def _standin_disclosed(table: dict, cfg: SentinelsConfig) -> bool:
    """A stand-in capture is disclosed by an explicit disclosure key, or by a
    posture key carrying a stand-in-shaped value (``acquisition: "stand_in"`` —
    the P34.22b vocabulary's public disclosure)."""
    for k in cfg.standin_disclosure_keys:
        if str(table.get(k, "")).strip():
            return True
    for k in cfg.standin_posture_keys:
        if _STANDIN_RE.search(str(table.get(k, ""))):
            return True
    return False


def _standin_findings_toml(path: Path, disp: str, cfg: SentinelsConfig) -> list[Finding]:
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except tomllib.TOMLDecodeError:
        return []
    out: list[Finding] = []
    for table in _walk_tables(doc):
        kind = str(table.get("capture_kind", table.get("captureKind", "")))
        if not _STANDIN_RE.search(kind):
            continue
        if not _standin_disclosed(table, cfg):
            out.append(
                Finding(
                    "standin-disclosure",
                    "standin-undisclosed",
                    disp,
                    1,
                    "capture_kind: stand-in without a sibling disclosure",
                )
            )
    return out


def _standin_findings_json(path: Path, disp: str, cfg: SentinelsConfig) -> list[Finding]:
    out: list[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    docs: list[tuple[int, Any]] = []
    if path.suffix == ".jsonl":
        for n, line in enumerate(lines, 1):
            if line.strip():
                try:
                    docs.append((n, json.loads(line)))
                except json.JSONDecodeError:
                    continue
    else:
        try:
            docs.append((1, json.loads("\n".join(lines))))
        except json.JSONDecodeError:
            return out
    for n, doc in docs:
        for table in _walk_tables(doc):
            kind = str(table.get("capture_kind", table.get("captureKind", "")))
            if not _STANDIN_RE.search(kind):
                continue
            if not _standin_disclosed(table, cfg):
                out.append(
                    Finding(
                        "standin-disclosure",
                        "standin-undisclosed",
                        disp,
                        n,
                        "capture_kind: stand-in without a sibling disclosure",
                    )
                )
    return out


def _standin_findings_text(path: Path, disp: str, cfg: SentinelsConfig) -> list[Finding]:
    """Generic text: a capture_kind:stand-in mention needs a disclosure key's
    token anywhere in the same document."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if not _STANDIN_KIND_RE.search(text):
        return []
    for key in cfg.standin_disclosure_keys:
        if re.search(rf"\"'?{re.escape(key)}\"'?\s*[:=]", text, re.I):
            return []
    for key in cfg.standin_posture_keys:
        if re.search(rf"\"'?{re.escape(key)}\"'?\s*[:=]\s*[\"']?stand[-_]?in", text, re.I):
            return []
    first = next(
        (i for i, line in enumerate(text.splitlines(), 1) if _STANDIN_KIND_RE.search(line)),
        1,
    )
    return [
        Finding(
            "standin-disclosure",
            "standin-undisclosed",
            disp,
            first,
            "capture_kind: stand-in without a sibling disclosure",
        )
    ]


def _standin_scan(
    files: list[tuple[Path, str, list[str]]], cfg: SentinelsConfig
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    candidates = 0
    for path, disp, _variants in files:
        text_hint = path.suffix in {".md", ".txt", ".html", ".yaml", ".yml", ".csv", ""}
        if path.suffix == ".toml":
            candidates += 1
            findings.extend(_standin_findings_toml(path, disp, cfg))
        elif path.suffix in {".json", ".jsonl"}:
            candidates += 1
            findings.extend(_standin_findings_json(path, disp, cfg))
        elif text_hint:
            candidates += 1
            findings.extend(_standin_findings_text(path, disp, cfg))
    return findings, candidates


# --- contact domains ------------------------------------------------------------


def _domains_of(value: str) -> list[str]:
    out = [m.group(1).lower() for m in _EMAIL_RE.finditer(value)]
    out += [m.group(1).lower() for m in _URL_HOST_RE.finditer(value)]
    if not out:
        out += [m.group(1).lower() for m in _DOMAIN_RE.finditer(value)]
    # strip the subdomains — the registered unit is the eTLD+1-ish suffix pair
    return [d.split("@")[-1] for d in out]


def _registered(domain: str, registered: set[str]) -> bool:
    """`d` registered when it is, or sits under, a registered domain."""
    parts = domain.split(".")
    for i in range(len(parts)):
        if ".".join(parts[i:]) in registered:
            return True
    return False


def contact_domain_check(cfg: SentinelsConfig, root: Path) -> tuple[CheckResult, int]:
    """Every contact field's domain is registered — or it is a placeholder hit."""
    findings: list[Finding] = []
    domains_checked = 0
    for rel in cfg.contact_sources:
        path = root / rel
        if not path.is_file():
            return (
                CheckResult("fail", {"reason": f"declared contact registry absent: {rel}"}),
                domains_checked,
            )
        try:
            doc = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
        except tomllib.TOMLDecodeError as e:
            return CheckResult("fail", {"reason": f"{rel}: TOML parse error: {e}"}), domains_checked
        for table in _walk_tables(doc):
            for field_name in cfg.contact_fields:
                value = table.get(field_name)
                if not isinstance(value, str) or not value.strip():
                    continue
                for domain in _domains_of(value):
                    domains_checked += 1
                    if not _registered(domain, cfg.registered_domains):
                        findings.append(
                            Finding(
                                "contact-domains",
                                "unregistered-contact-domain",
                                rel,
                                1,
                                f"{field_name} names an unregistered contact domain",
                            )
                        )
    detail = {
        "domains_checked": domains_checked,
        "violations": [f.as_json() for f in findings[:50]],
        "violation_count": len(findings),
    }
    if domains_checked == 0:
        return CheckResult("skipped", {**detail, "reason": "no contact fields in the registry"}), 0
    return CheckResult("fail" if findings else "pass", detail), domains_checked


# --- sentinel scan --------------------------------------------------------------


def sentinel_scan(
    cfg: SentinelsConfig, files: list[tuple[Path, str, list[str]]]
) -> tuple[list[Finding], dict[str, int], dict[str, int]]:
    """Text sentinels over the file set; ``(violations, hits, exempted)``."""
    violations: list[Finding] = []
    hits: dict[str, int] = {s.id: 0 for s in cfg.sentinels if s.kind != "rule"}
    exempted: dict[str, int] = {}
    for path, disp, variants in files:
        if not _is_probably_text(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for s in cfg.sentinels:
                if s.kind == "rule" or s.rx is None or not s.rx.search(line):
                    continue
                hits[s.id] = hits.get(s.id, 0) + 1
                comp = _compartment_for(cfg, variants, s.id)
                if comp is None:
                    violations.append(Finding("sentinels", s.id, disp, n))
                else:
                    exempted[comp.id] = exempted.get(comp.id, 0) + 1
    return violations, hits, exempted


def compartments_check(cfg: SentinelsConfig, root: Path) -> CheckResult:
    """Every compartment's `debt` id exists in DEFERRALS — an exemption is
    never an untracked hole."""
    problems: list[dict[str, Any]] = []
    checked = 0
    deferrals = ""
    if (root / "docs/tickets/DEFERRALS.md").is_file():
        deferrals = (root / "docs/tickets/DEFERRALS.md").read_text(
            encoding="utf-8", errors="replace"
        )
    for comp in cfg.compartments:
        if not comp.debt:
            continue
        checked += 1
        if comp.debt not in deferrals:
            problems.append(
                {
                    "compartment": comp.id,
                    "debt": comp.debt,
                    "note": "debt id absent from docs/tickets/DEFERRALS.md",
                }
            )
    if checked == 0:
        return CheckResult("skipped", {"reason": "no compartment carries a debt id", "checked": 0})
    return CheckResult("fail" if problems else "pass", {"checked": checked, "violations": problems})


def sentinel_record(
    cfg: SentinelsConfig,
    config_errors: list[str],
    files: list[tuple[Path, str, list[str]]],
    root: Path,
    *,
    subject: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """The `fixture-sentinel` probe-run/1 record."""
    checks: dict[str, CheckResult] = {}
    checks["config"] = CheckResult(
        "fail" if config_errors else "pass",
        {"errors": config_errors, "sentinels": len(cfg.sentinels)},
    )
    violations: list[Finding] = []
    hits: dict[str, int] = {}
    exempted: dict[str, int] = {}
    standin_findings: list[Finding] = []
    standin_candidates = 0
    if not config_errors:
        violations, hits, exempted = sentinel_scan(cfg, files)
        standin_findings, standin_candidates = _standin_scan(files, cfg)
    checks["sentinels"] = CheckResult(
        "skipped" if config_errors else ("fail" if violations else "pass"),
        {
            **({"reason": "config invalid"} if config_errors else {}),
            "files_scanned": len(files),
            "hits": {k: v for k, v in hits.items() if v},
            "exempted": exempted,
            "violations": [f.as_json() for f in violations[:50]],
            "violation_count": len(violations),
        },
    )
    checks["standin-disclosure"] = CheckResult(
        "skipped" if config_errors else ("fail" if standin_findings else "pass"),
        {
            **({"reason": "config invalid"} if config_errors else {}),
            "candidates": standin_candidates,
            "evaluated": standin_candidates,
            "violations": [f.as_json() for f in standin_findings[:50]],
            "violation_count": len(standin_findings),
        },
    )
    if config_errors:
        checks["contact-domains"] = CheckResult("skipped", {"reason": "config invalid"})
    else:
        cd, domains = contact_domain_check(cfg, root)
        cd = CheckResult(cd.verdict, {**cd.detail, "domains_checked": domains})
        checks["contact-domains"] = cd
    checks["compartments"] = (
        CheckResult("skipped", {"reason": "config invalid"})
        if config_errors
        else compartments_check(cfg, root)
    )
    return build_record("fixture-sentinel", checks, subject=subject, now=now)


# --- claim-marker scan ----------------------------------------------------------


def _marker_is_valid(cfg: SentinelsConfig, cite: str, root: Path) -> tuple[bool, str]:
    """The cited path is a recorded human-completion marker, never an agent."""
    path = (root / cite).resolve()
    try:
        rel = path.relative_to(root.resolve())
    except ValueError:
        return False, "marker cites a path outside the repo"
    if not path.is_file():
        return False, "marker record absent"
    if cfg.marker_globs and not any(g.match(str(rel)) for g in cfg.marker_globs):
        return False, "cited file is outside the declared marker-record globs"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, "marker record unreadable"
    for token in cfg.marker_required:
        if token not in text:
            return False, f"marker record lacks {token!r}"
    if cfg.marker_agent_label is not None:
        m = _REVIEWER_RE.search(text)
        if m and cfg.marker_agent_label.search(m.group(1)):
            return False, "the recorded reviewer is an agent label — not a human label"
    return True, ""


def claim_marker_scan(
    cfg: SentinelsConfig,
    files: list[tuple[Path, str, list[str]]],
    root: Path,
) -> tuple[list[Finding], dict[str, int], dict[str, int], int]:
    """``(violations, assertions, exempted, markers_checked)``."""
    violations: list[Finding] = []
    assertions: dict[str, int] = {m.id: 0 for m in cfg.claim_markers}
    exempted: dict[str, int] = {}
    markers_checked = 0
    marker_cache: dict[str, tuple[bool, str]] = {}
    for path, disp, variants in files:
        if not _is_probably_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cites = [m.group(1) for m in _MARKER_CITE_RE.finditer(text)]
        validated: list[tuple[str, bool, str]] = []
        for cite in cites:
            if cite not in marker_cache:
                marker_cache[cite] = _marker_is_valid(cfg, cite, root)
                markers_checked += 1
            ok, why = marker_cache[cite]
            validated.append((cite, ok, why))
        file_ok = any(ok for _c, ok, _w in validated)
        for n, line in enumerate(text.splitlines(), 1):
            for marker in cfg.claim_markers:
                if not any(rx.search(line) for rx in marker.assert_res):
                    continue
                if any(rx.search(line) for rx in marker.safe_res):
                    continue
                assertions[marker.id] += 1
                comp = _compartment_for(cfg, variants, marker.id)
                if comp is not None:
                    exempted[comp.id] = exempted.get(comp.id, 0) + 1
                    continue
                if file_ok:
                    continue
                note = ""
                if validated:
                    note = "; ".join(
                        f"marker:{c} — {w or 'invalid'}" for c, ok, w in validated if not ok
                    )
                violations.append(
                    Finding(
                        "assertions",
                        marker.id,
                        disp,
                        n,
                        note or "no recorded human-completion marker cited",
                    )
                )
    return violations, assertions, exempted, markers_checked


def claim_marker_record(
    cfg: SentinelsConfig,
    config_errors: list[str],
    files: list[tuple[Path, str, list[str]]],
    root: Path,
    *,
    subject: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """The `claim-markers` probe-run/1 record."""
    checks: dict[str, CheckResult] = {}
    checks["config"] = CheckResult(
        "fail" if config_errors else "pass",
        {"errors": config_errors, "claim_markers": len(cfg.claim_markers)},
    )
    violations: list[Finding] = []
    assertions: dict[str, int] = {}
    exempted: dict[str, int] = {}
    markers_checked = 0
    if not config_errors:
        violations, assertions, exempted, markers_checked = claim_marker_scan(cfg, files, root)
    checks["assertions"] = CheckResult(
        "skipped" if config_errors else ("fail" if violations else "pass"),
        {
            **({"reason": "config invalid"} if config_errors else {}),
            "files_scanned": len(files),
            "assertions": {k: v for k, v in assertions.items() if v},
            "exempted": exempted,
            "violations": [f.as_json() for f in violations[:50]],
            "violation_count": len(violations),
        },
    )
    checks["marker-records"] = CheckResult(
        "skipped" if config_errors else "pass",
        {
            **({"reason": "config invalid"} if config_errors else {}),
            "markers_checked": markers_checked,
            "note": "every cited marker:<path> resolved and validated during the scan",
        },
    )
    return build_record("claim-markers", checks, subject=subject, now=now)


# --- the probe-sweep legs (evidence-form bindings for the DR-C3 owners) --------


def jurisdiction_coordinate_check(public_dir: Path | None) -> CheckResult:
    """Mechanical coordinate invariants over exported rows — the DR-C3-05/11
    boundary leg itself is its owner's; this leg binds the evidence form
    honestly: ranges, no (0,0), no swapped axes."""
    if public_dir is None or not public_dir.is_dir():
        return CheckResult("skipped", {"reason": "no --public-dir given"})
    candidates = evaluated = 0
    bad: list[dict[str, Any]] = []
    for path in sorted(public_dir.rglob("*")):
        if path.suffix not in {".jsonl", ".json"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        docs: list[Any] = []
        if path.suffix == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    try:
                        docs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        else:
            try:
                docs.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        for doc in docs:
            candidates += 1
            for table in _walk_tables(doc):
                lat = table.get("lat", table.get("latitude"))
                lon = table.get("lon", table.get("lng", table.get("longitude")))
                coords = table.get("coordinates")
                if not isinstance(coords, list) and isinstance(table.get("geometry"), dict):
                    coords = table["geometry"].get("coordinates")
                pair = None
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    pair = (float(lat), float(lon))
                elif (
                    isinstance(coords, list)
                    and len(coords) >= 2
                    and all(isinstance(c, (int, float)) for c in coords[:2])
                ):
                    pair = (float(coords[1]), float(coords[0]))  # GeoJSON lon,lat
                if pair is None:
                    continue
                evaluated += 1
                la, lo = pair
                why = None
                if la == 0.0 and lo == 0.0:
                    why = "null-island (0,0)"
                elif not -90.0 <= la <= 90.0:
                    why = "latitude out of range (swapped axes?)"
                elif not -180.0 <= lo <= 180.0:
                    why = "longitude out of range"
                if why:
                    bad.append({"path": str(path.name), "reason": why})
    if candidates == 0:
        return CheckResult(
            "skipped",
            {"reason": f"no JSON/JSONL rows under {public_dir}", "candidates": 0, "evaluated": 0},
        )
    if evaluated == 0:
        return CheckResult(
            "fail",
            {
                "reason": "rows offered but none carried coordinates — vacuous (SIG-ENG-042)",
                "candidates": candidates,
                "evaluated": 0,
            },
        )
    return CheckResult(
        "fail" if bad else "pass",
        {"candidates": candidates, "evaluated": evaluated, "violations": bad[:50]},
    )


def api_release_parity_check(api_sample: Path | None, release_dir: Path | None) -> CheckResult:
    """Each sampled ``/v1/dossier/{scope}`` response equals the release JSON
    byte-for-byte, or is a 404 where no release file exists (DR-C3-12)."""
    if api_sample is None or release_dir is None:
        return CheckResult("skipped", {"reason": "needs --api-sample and --release-dir together"})
    if not api_sample.is_dir():
        return CheckResult("fail", {"reason": f"absent: {api_sample}"})
    candidates = 0
    mismatches: list[dict[str, Any]] = []
    for sample in sorted(api_sample.rglob("*.json")):
        candidates += 1
        rel = sample.relative_to(api_sample)
        expected = release_dir / rel
        try:
            body = json.loads(sample.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            mismatches.append({"sample": str(rel), "reason": "sample is not JSON"})
            continue
        api_404 = body.get("detail") == "Not Found" or body.get("status") == 404
        if expected.is_file():
            try:
                rel_body = json.loads(expected.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                mismatches.append({"sample": str(rel), "reason": "release file is not JSON"})
                continue
            if api_404 or body != rel_body:
                mismatches.append({"sample": str(rel), "reason": "API response != release JSON"})
        elif not api_404:
            mismatches.append({"sample": str(rel), "reason": "no release file and API did not 404"})
    if candidates == 0:
        return CheckResult(
            "skipped", {"reason": f"no .json samples under {api_sample}", "candidates": 0}
        )
    return CheckResult(
        "fail" if mismatches else "pass",
        {"candidates": candidates, "evaluated": candidates, "violations": mismatches[:50]},
    )


def number_truth_check(public_dir: Path | None) -> CheckResult:
    """Recompute row counts against the export manifest's declared counts —
    the DR-C3-15 owner's deeper 'displayed number' check binds this form."""
    if public_dir is None or not public_dir.is_dir():
        return CheckResult("skipped", {"reason": "no --public-dir given"})
    manifest = public_dir / "manifest.json"
    if not manifest.is_file():
        return CheckResult(
            "skipped",
            {"reason": "no manifest.json declaring counts to recompute against"},
        )
    try:
        decl = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return CheckResult("fail", {"reason": "manifest.json is not JSON"})
    declared = (
        decl.get("files")
        or decl.get("counts")
        or (decl.get("counts_by_file") if isinstance(decl, dict) else None)
        or {}
    )
    if not isinstance(declared, dict) or not declared:
        return CheckResult(
            "skipped",
            {"reason": "manifest.json declares no per-file counts to recompute"},
        )
    evaluated = 0
    mismatches: list[dict[str, Any]] = []
    for name, want in sorted(declared.items()):
        target = public_dir / str(name)
        if not target.is_file():
            mismatches.append({"file": name, "reason": "declared file absent"})
            evaluated += 1
            continue
        if not isinstance(want, (int, float)):
            mismatches.append({"file": name, "reason": "declared count is not numeric"})
            evaluated += 1
            continue
        if target.suffix == ".jsonl":
            try:
                got = sum(
                    1
                    for line in target.read_text(encoding="utf-8", errors="replace").splitlines()
                    if line.strip()
                )
            except OSError:
                got = -1
        else:
            try:
                got = len(json.loads(target.read_text(encoding="utf-8", errors="replace")))
            except (json.JSONDecodeError, TypeError):
                got = -1
        evaluated += 1
        if got != int(want):
            mismatches.append({"file": name, "declared": int(want), "recomputed": got})
    return CheckResult(
        "fail" if mismatches else "pass",
        {"candidates": len(declared), "evaluated": evaluated, "violations": mismatches[:50]},
    )


SWEEP_CHECKS = {
    "attribution-sanity": lambda public_dir, _a, _r: attribution_sample_check(public_dir),
    "jurisdiction-coordinate": lambda public_dir, _a, _r: jurisdiction_coordinate_check(public_dir),
    "api-release-parity": lambda _p, api_sample, release_dir: api_release_parity_check(
        api_sample, release_dir
    ),
    "number-truth": lambda public_dir, _a, _r: number_truth_check(public_dir),
}


def sweep_record(
    probe_id: str,
    *,
    public_dir: Path | None,
    api_sample: Path | None,
    release_dir: Path | None,
    now: str | None = None,
) -> dict[str, Any]:
    """One registered probe's probe-run/1 — honest legs, no fabricated pass."""
    check_fn = SWEEP_CHECKS[probe_id]
    checks = {"check": check_fn(public_dir, api_sample, release_dir)}
    subject = {
        "public_dir": str(public_dir) if public_dir else None,
        "api_sample": str(api_sample) if api_sample else None,
        "release_dir": str(release_dir) if release_dir else None,
    }
    return build_record(probe_id, checks, subject=subject, now=now)
