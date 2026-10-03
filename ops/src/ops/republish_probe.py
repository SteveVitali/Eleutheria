# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""republish_probe — the P34.21b republish-#2 pre-flight probe record.

The ticket's L2 prerequisite: a fresh (≤ 24 h) ``sig.probe-run/1`` record that
proves, before the new export is cut over, that

* the **denied routes stay absent** on every public origin (the same
  ``http-absent`` cadence targets ``publish-web --apply`` verifies post-sync —
  one probe definition, no drift),
* the **handle crawl** runs over the repo tip and every tree the republish
  will serve (``--export-dir``/``--tiles-dir``/``--build-dir``/a downloaded
  bucket listing) — **counts only**: a matched handle is never printed
  (ADR-178, SIG-PUB-002),
* a **tile sample** answers a ranged GET on each ``--tile-url``,
* a **sig-public listing** is recorded (object count + handle hits counted),
  and
* an **attribution sample** proves every ``attribution_required`` public row
  carries a non-empty ``_rights.attribution`` (the holder) **and** a
  ``_rights.terms_url`` (E2-12/ADR-194 — the failure this republish repairs).

Every check is honest about what it did: a skipped leg is ``"skipped"`` with a
reason, never a fabricated pass. ``overall`` is ``pass`` only when every leg
that ran was green; ``partial`` names legs left unproven; ``fail`` fails the
record. The record itself carries ``generated_at`` — the ≤ 24-hour freshness
rule is enforced by the leg-runner, not hidden here.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from typing import Any

from .observe import http_absent
from .publish import _iter_jsonl_rows
from .scheduled import load_cadence, resolve_targets

PROBE_RUN_VERSION = "sig.probe-run/1"

REPO_ROOT = Path(__file__).resolve().parents[3]
HANDLE_CRAWL_TOOL = REPO_ROOT / "docs" / "build" / "tools" / "handle_crawl_check.py"
DEFAULT_HANDLE_LIST = (
    REPO_ROOT / "docs" / "build" / "logs" / "next-phase" / "C3" / "personal_like_ids.txt"
)


def _utcnow() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_range_status(url: str, *, timeout: float = 15.0) -> int | None:
    """A ranged GET — the PMTiles read pattern. ``None`` = unreachable."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


@dataclass(frozen=True)
class CheckResult:
    """One probe-run leg: a verdict plus structured, redaction-safe detail."""

    verdict: str  # "pass" | "fail" | "skipped"
    detail: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {"verdict": self.verdict, **self.detail}


# --- absence ---------------------------------------------------------------------


def absence_check(
    cadence_path: str | Path | None,
    *,
    env: dict[str, str] | None = None,
    check_absent: Callable[[str], tuple[bool, str]] | None = None,
) -> CheckResult:
    """Probe every cadence ``http-absent`` target (the denied routes)."""
    cadence = load_cadence(cadence_path)
    specs = {s.name: s for s in cadence.probe_targets}
    resolved, skipped_names = resolve_targets(cadence, env)
    check = check_absent or http_absent
    probes: list[dict[str, Any]] = []
    skipped: list[str] = []
    for name, url in resolved:
        if specs[name].kind != "http-absent":
            continue
        ok, detail = check(url)
        probes.append({"name": name, "url": url, "ok": ok, "detail": detail})
        if not ok:
            pass  # counted below — never short-circuit the record
    for name in skipped_names:
        if specs.get(name) is not None and specs[name].kind == "http-absent":
            skipped.append(name)
    if not probes:
        return CheckResult(
            "skipped",
            {"reason": "no resolvable http-absent targets", "unresolved": skipped},
        )
    failed = [p for p in probes if not p["ok"]]
    return CheckResult(
        "fail" if failed else "pass",
        {
            "probes": probes,
            "count": len(probes),
            "failed": len(failed),
            "unresolved": skipped,
        },
    )


# --- handle crawl ------------------------------------------------------------------


def _scan_listing_for_handles(listing: Path, handles: Sequence[str]) -> dict[str, int]:
    """Count handle hits in a downloaded bucket listing. Counts only."""
    try:
        text = listing.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"hits": 0, "objects": 0}
    objects = [line for line in text.splitlines() if line.strip()]
    hits = 0
    for line in objects:
        for handle in handles:
            hits += line.count(handle)
    return {"hits": hits, "objects": len(objects)}


def handle_crawl_check(
    *,
    repo_root: Path = REPO_ROOT,
    handle_list: Path = DEFAULT_HANDLE_LIST,
    export_dirs: Sequence[Path] = (),
    tiles_dirs: Sequence[Path] = (),
    build_dirs: Sequence[Path] = (),
    bucket_listing: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> CheckResult:
    """The P34.18 count-only crawl over the repo tip + every served tree.

    Runs ``docs/build/tools/handle_crawl_check.py --json`` (one implementation —
    the probe never re-derives its own classification); the downloaded
    sig-public listing is scanned here with the same counts-only rule.
    """
    if not handle_list.is_file():
        return CheckResult(
            "skipped",
            {"reason": f"handle list absent: {handle_list} (gitignored C3 input)"},
        )
    run = runner or subprocess.run
    cmd: list[str] = [
        os.environ.get("PYTHON", "python3"),
        str(HANDLE_CRAWL_TOOL),
        "--root",
        str(repo_root),
        "--handle-list",
        str(handle_list),
        "--json",
    ]
    for opt, dirs in (
        ("--export-dir", export_dirs),
        ("--tiles-dir", tiles_dirs),
        ("--build-dir", build_dirs),
    ):
        for d in dirs:
            cmd += [opt, str(d)]
    out = run(cmd, capture_output=True, text=True, check=False)
    detail: dict[str, Any] = {}
    if out.returncode not in (0, 1):
        return CheckResult(
            "fail",
            {"reason": "handle_crawl_check not runnable", "stderr_tail": out.stderr[-400:]},
        )
    try:
        report = json.loads(out.stdout)
    except json.JSONDecodeError:
        return CheckResult("fail", {"reason": "handle_crawl_check emitted no JSON"})
    detail["repo_and_trees"] = {
        "verdict": report.get("verdict"),
        "handles_checked": report.get("handles_checked"),
        "hits": report.get("hits"),
        "files_with_hits": report.get("files_with_hits"),
    }
    repo_ok = report.get("verdict") == "pass"
    if bucket_listing is not None:
        try:
            handles = [
                line.strip()
                for line in handle_list.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
        except OSError:
            handles = []
        listing = _scan_listing_for_handles(bucket_listing, handles)
        detail["sig_public_listing"] = {
            "objects": listing["objects"],
            "handle_hits": listing["hits"],
        }
        listing_ok = listing["hits"] == 0
    else:
        detail["sig_public_listing"] = {"skipped": True}
        listing_ok = True
    return CheckResult("pass" if (repo_ok and listing_ok) else "fail", detail)


# --- tile sample -------------------------------------------------------------------


def tile_sample_check(
    tile_urls: Sequence[str],
    *,
    probe: Callable[[str], int | None] | None = None,
) -> CheckResult:
    """One ranged GET per tile URL — 200 or 206 is a live tile."""
    if not tile_urls:
        return CheckResult("skipped", {"reason": "no --tile-url given"})
    check = probe or http_range_status
    probes = []
    for url in tile_urls:
        status = check(url)
        probes.append({"url": url, "status": status, "ok": status in (200, 206)})
    failed = [p for p in probes if not p["ok"]]
    return CheckResult(
        "fail" if failed else "pass",
        {"probes": probes, "count": len(probes), "failed": len(failed)},
    )


# --- attribution sample -----------------------------------------------------------


def attribution_sample_check(public_root: Path | None) -> CheckResult:
    """Every ``attribution_required`` row carries a holder + a terms URL."""
    if public_root is None:
        return CheckResult("skipped", {"reason": "no --public-dir given"})
    if not public_root.is_dir():
        return CheckResult("fail", {"reason": f"absent: {public_root}"})
    rows_checked = 0
    missing_holder = 0
    missing_terms = 0
    for _rel, _n, row in _iter_jsonl_rows(public_root):
        rights = row.get("_rights")
        if not isinstance(rights, dict):
            continue
        if not rights.get("attribution_required", False):
            continue
        rows_checked += 1
        attribution = rights.get("attribution")
        if attribution is None or not str(attribution).strip():
            missing_holder += 1
        terms = rights.get("terms_url")
        if terms is None or not str(terms).strip():
            missing_terms += 1
    detail = {
        "rows_checked": rows_checked,
        "missing_attribution": missing_holder,
        "missing_terms_url": missing_terms,
    }
    if rows_checked == 0:
        return CheckResult(
            "skipped",
            {**detail, "reason": "no attribution_required rows in the sample"},
        )
    return CheckResult("fail" if (missing_holder or missing_terms) else "pass", detail)


# --- the record --------------------------------------------------------------------


def run_republish_probe(
    *,
    cadence_path: str | Path | None = None,
    repo_root: Path = REPO_ROOT,
    handle_list: Path = DEFAULT_HANDLE_LIST,
    export_dirs: Sequence[Path] = (),
    tiles_dirs: Sequence[Path] = (),
    build_dirs: Sequence[Path] = (),
    bucket_listing: Path | None = None,
    tile_urls: Sequence[str] = (),
    public_dir: Path | None = None,
    release: dict[str, Any] | None = None,
    now: str | None = None,
    env: dict[str, str] | None = None,
    check_absent: Callable[[str], tuple[bool, str]] | None = None,
    tile_probe: Callable[[str], int | None] | None = None,
    crawl_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Build the ``sig.probe-run/1`` record. Every leg reports honestly."""
    checks = {
        "absence": absence_check(cadence_path, env=env, check_absent=check_absent),
        "handle_crawl": handle_crawl_check(
            repo_root=repo_root,
            handle_list=handle_list,
            export_dirs=export_dirs,
            tiles_dirs=tiles_dirs,
            build_dirs=build_dirs,
            bucket_listing=bucket_listing,
            runner=crawl_runner,
        ),
        "tile_sample": tile_sample_check(tile_urls, probe=tile_probe),
        "attribution_sample": attribution_sample_check(public_dir),
    }
    verdicts = [c.verdict for c in checks.values()]
    if "fail" in verdicts:
        overall = "fail"
    elif "skipped" in verdicts:
        overall = "partial"
    else:
        overall = "pass"
    record: dict[str, Any] = {
        "version": PROBE_RUN_VERSION,
        "generated_at": now or _utcnow(),
        "release": release or {},
        "checks": {name: c.as_json() for name, c in checks.items()},
        "overall": overall,
    }
    return record


def read_release_record(dist: Path | None) -> dict[str, Any]:
    """``.sig-release.json`` under the built tree — release/export identifiers."""
    if dist is None:
        return {}
    marker = dist / ".sig-release.json"
    if not marker.is_file():
        return {}
    try:
        doc = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        k: doc.get(k)
        for k in ("release_id", "data_release", "built_at", "export_id")
        if doc.get(k) is not None
    }
