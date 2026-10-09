# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.47 — the 11A live-read acceptance sweep → a ``sig.probe-run/1`` record.

The capstone's live half (ticket 259, plan §5.1 + §13.1, S2 §4.1): a
**read-only** crawl of the five public surfaces — the site, the API, the
tiles, the ``sig-public`` object listing and the repo tip — counting

* every entry of the personal-handle list (the gitignored C3 input —
  **counts only**; a handle value is never printed, logged or recorded,
  and an absent list means RI-01 is *not checked*, never passed), and
* the L3 §4.5 / C6 not-claimable and status words outside disclosed
  contexts (TS-10; SIG-CONF-012).

The sweep is **gated**: it must not run before the recorded window —
P34.46's L2 deploy landed live (its ``P34.46-slot`` leg no longer queued
in the RETURN PASS map) and ``now`` ≥ ``WINDOW_EARLIEST`` (the earliest
possible L2 slot instant, so the window is never bypassed by an early
clock alone). An unmet gate refuses with exit 42 — the leg queues, never
proceeds — and writes a *suppressed* ``sig.probe-run/1`` record when
``--record-out`` is given, so the refusal is itself recorded evidence,
not a fabricated pass.

Exit-item coverage: exit item 5 (G2 step 1 live) additionally needs
P34.46's L3 soak read — while the ``P34.46-soak`` leg remains queued that
item's leg reports ``skipped`` (queued), not failed and not passed.

Exit codes: ``0`` = sweep ran (see ``overall`` in the record) · ``42`` =
gated/queued · ``2`` = usage.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .republish_probe import REPO_ROOT, absence_check, handle_crawl_check

SCHEMA = "sig.probe-run/1"
GATE_KIND = "sig.acceptance-gate/1"
PROBE = "sig-11a-acceptance"
TARGET = "11a-live-surfaces"

#: Contract live window: the sweep runs after P34.46's L2 lands live and
#: never before the earliest possible L2 slot instant (ticket §Live
#: window: "≥ 2026-10-14"; P34.46's earliest slot is 14:00Z).
WINDOW_EARLIEST = "2026-10-14T14:00:00Z"  # future-ok: scheduled window floor (OM-19)

#: The ticket's re-run prompt, recorded on every refusal/queued state.
RERUN = (
    "implement-spec "
    "spec=docs/tickets/259_P34.47__sub-round-11a-acceptance.md "
    "live_verification=true (scope: the sweep and the packet)"
)

DEFAULT_HANDLE_LIST = (
    REPO_ROOT / "docs" / "build" / "logs" / "next-phase" / "C3" / "personal_like_ids.txt"
)
DEFAULT_MAP = REPO_ROOT / "docs" / "build" / "tools" / "record_policy" / "return_pass.toml"

#: The not-claimable / status-word list the ticket scans for, verbatim
#: (L3 §4.5 + C6, plan §5.1 — exact case as written).
CLAIM_WORDS: tuple[str, ...] = (
    "human-verified",
    "independently reviewed",
    "certified",
    "counsel",
    "editorial board",
    "one-click",
    "anonymous",
    "reproducible",
    "Reviewed",
    "Releasable",
    "complete",
)

#: Disclosed contexts (TS-10): a word occurrence on a line matching one of
#: these is the word bound to recorded state — the sanctioned negative /
#: conditional framings (L3 §4.5's "what SIG says instead" plus the
#: conditional forms). A conservative agent judgement, labelled; every
#: raw count is recorded alongside so the operator can re-check.
DISCLOSED_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"no human check performed",
        r"checked automatically",
        r"reviewed by an ai agent",
        r"agent[- ]checked|agent (review|reviewed)",
        r"maintainer check \(?not independent\)?",
        r"not (yet )?(performed|run|verified|reviewed|certified|independent"
        r"|complete|anonymous|released|available)",
        r"\bun(verified|reviewed|certified|released)\b",
        r"\bincomplete\b",
        r"\bnot\b[^.]{0,60}\b(verified|reviewed|certified|independent|anonymous|reproducible|complete)\b",
        r"\bno\b[^.]{0,40}\b(counsel|review|certification|verification)\b",
        r"\bprovisional\b",
        r"\bwithdrawn\b",
        r"\bpending\b",
        r"\bcannot\b",
        r"\bnever\b",
        r"possible duplicate; not merged",
        r"not merged",
    )
)


class AcceptanceError(ValueError):
    """A malformed sweep input (usage failure, exit 2)."""


def _iso(text: Any) -> _dt.datetime:
    """Parse an ISO-8601 instant (Z or offset) — raises AcceptanceError."""
    if not isinstance(text, str) or not text.strip():
        raise AcceptanceError(f"expected an ISO-8601 instant, got {text!r}")
    t = text.strip()
    try:
        dt = _dt.datetime.fromisoformat(t[:-1] + "+00:00" if t.endswith("Z") else t)
    except ValueError as exc:
        raise AcceptanceError(f"bad ISO-8601 instant {text!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise AcceptanceError(f"instant {text!r} carries no timezone (UTC required)")
    return dt.astimezone(_dt.UTC)


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_handles(path: Path) -> list[str]:
    """The personal-handle list — read only; values are never recorded."""
    try:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError as exc:
        raise AcceptanceError(f"cannot read handle list {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# The count-only scanners — handles and claim words. Handle VALUES are never
# in the output; word hits carry (url, line) locations since the word list is
# public, bounded by _MAX_LOCATIONS.
# ---------------------------------------------------------------------------

_MAX_LOCATIONS = 20


def _line_hit_counts(
    text: str, handles: Sequence[str]
) -> tuple[int, dict[str, dict[str, int]], list[dict[str, Any]]]:
    """Scan one decoded page/record. Returns (handle_hits, per-word, locs).

    ``per-word`` maps each claim word to ``{"hits": n, "undisclosed": n}``;
    a hit on a line carrying a disclosed-context marker is disclosed.
    Locations record ``{"line": <1-based>, "words": [...]}`` per undisclosed
    hit line — never the line's text, never a handle value.
    """
    handle_hits = 0
    per_word: dict[str, dict[str, int]] = {w: {"hits": 0, "undisclosed": 0} for w in CLAIM_WORDS}
    word_res = {w: re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)") for w in CLAIM_WORDS}
    locations: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for h in handles:
            handle_hits += line.count(h)
        undisclosed_here: list[str] = []
        for w, rx in word_res.items():
            hits = len(rx.findall(line))
            if not hits:
                continue
            per_word[w]["hits"] += hits
            if any(d.search(line) for d in DISCLOSED_RES):
                continue
            per_word[w]["undisclosed"] += hits
            undisclosed_here.append(w)
        if undisclosed_here and len(locations) < _MAX_LOCATIONS:
            locations.append({"line": lineno, "words": sorted(set(undisclosed_here))})
    return handle_hits, per_word, locations


def scan_text(text: str, handles: Sequence[str]) -> dict[str, Any]:
    """The per-document scan result — counts only for handles."""
    handle_hits, per_word, locations = _line_hit_counts(text, handles)
    return {
        "handle_hits": handle_hits,
        "claim_words": {w: c for w, c in per_word.items() if c["hits"]},
        "undisclosed_word_hits": sum(c["undisclosed"] for c in per_word.values()),
        "undisclosed_locations": locations,
    }


def scan_bytes(data: bytes, handles: Sequence[str]) -> dict[str, Any]:
    """The byte-surface scan (tiles, listing payloads) — substring counts.

    Claim words are scanned on the latin-1 decoded bytes (a 1:1 byte map,
    so every raw occurrence is seen) with the same disclosed-context rule.
    """
    handle_hits = sum(data.count(h.encode("utf-8")) for h in handles)
    decoded = data.decode("latin-1")
    per_word: dict[str, dict[str, int]] = {}
    undisclosed = 0
    for w in CLAIM_WORDS:
        hits = decoded.count(w)
        if not hits:
            continue
        und = 0
        start = 0
        for _ in range(hits):
            idx = decoded.index(w, start)
            ctx = decoded[max(0, idx - 160) : idx + len(w) + 160]
            if not any(d.search(ctx) for d in DISCLOSED_RES):
                und += 1
            start = idx + len(w)
        per_word[w] = {"hits": hits, "undisclosed": und}
        undisclosed += und
    return {
        "handle_hits": handle_hits,
        "claim_words": per_word,
        "undisclosed_word_hits": undisclosed,
    }


# ---------------------------------------------------------------------------
# The gate — a recorded-inputs judgement in the roll_gate style, plus the
# map-derived facts the live caller supplies.
# ---------------------------------------------------------------------------


@dataclass
class Criterion:
    id: str
    ok: bool
    detail: str
    value: Any = None


@dataclass
class Gate:
    decision: str  # "run" | "queued"
    criteria: list[Criterion] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)

    @property
    def refusals(self) -> list[str]:
        return [f"{c.id}: {c.detail}" for c in self.criteria if not c.ok]

    def to_record(self) -> dict[str, Any]:
        return {
            "kind": GATE_KIND,
            "decision": self.decision,
            "leg": "P34.47-sweep-packet",
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "advisories": self.advisories,
            "rerun_prompt": None if self.decision == "run" else RERUN,
            "window_earliest": WINDOW_EARLIEST,
        }


def evaluate_gate(inputs: dict[str, Any]) -> Gate:
    """Judge the recorded inputs. Hard criteria: ``p34_46_l2`` + ``window``.

    ``p34_46_l3_soak`` and ``handle_list`` are advisories: they scope legs
    (exit item 5 / RI-01), they never block the sweep itself.
    """
    if not isinstance(inputs, dict):
        raise AcceptanceError("the gate input must be a JSON object")
    criteria: list[Criterion] = []
    advisories: list[str] = []

    l2 = inputs.get("p34_46_l2_landed")
    criteria.append(
        Criterion(
            "p34_46_l2",
            l2 is True,
            (
                "P34.46's L2 deploy landed live (its slot leg left the queue)"
                if l2 is True
                else "P34.46's L2 deploy has not landed — its slot leg is still "
                "queued in the RETURN PASS map (live:P34.46 fails)"
            ),
            l2,
        )
    )

    earliest = _iso(inputs.get("window_earliest") or WINDOW_EARLIEST)
    now_raw = inputs.get("now")
    if now_raw is None:
        criteria.append(
            Criterion(
                "window",
                False,
                "no 'now' instant supplied — the gate evaluates a recorded "
                "instant, never the wall clock",
            )
        )
    else:
        now = _iso(now_raw)
        ok = now >= earliest
        criteria.append(
            Criterion(
                "window",
                ok,
                f"now {now.isoformat()} {'>=' if ok else '<'} window floor {earliest.isoformat()}",
                now.isoformat(),
            )
        )

    if inputs.get("p34_46_l3_soak_read") is not True:
        advisories.append(
            "exit-item-5: P34.46's L3 soak read is not recorded — that item "
            "reports queued/skipped, never passed"
        )
    if inputs.get("handle_list_present") is not True:
        advisories.append(
            "RI-01: the handle list is absent — RI-01 is reported not "
            "checked (blockedOn), never passed"
        )

    decision = "run" if all(c.ok for c in criteria) else "queued"
    return Gate(decision=decision, criteria=criteria, advisories=advisories)


def map_derived_inputs(
    map_path: Path, *, now: str | None = None, handle_list: Path = DEFAULT_HANDLE_LIST
) -> dict[str, Any]:
    """Read the RETURN PASS map: P34.46's queued legs decide l2/l3 state."""
    try:
        data = tomllib.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AcceptanceError(f"cannot read the RETURN PASS map {map_path}: {exc}") from exc
    p46: dict[str, Any] = next((r for r in data.get("row", []) if r.get("key") == "P34.46"), {})
    leg_ids = {leg.get("id") for leg in p46.get("legs", [])}
    return {
        "now": now or _now(),
        "p34_46_l2_landed": "P34.46-slot" not in leg_ids,
        "p34_46_l3_soak_read": "P34.46-soak" not in leg_ids,
        "handle_list_present": handle_list.is_file(),
        "queued_p34_46_legs": sorted(x for x in leg_ids if x),
    }


# ---------------------------------------------------------------------------
# The sweep legs — every leg reports honestly; a skipped leg is "skipped"
# with a reason, never a fabricated pass.
# ---------------------------------------------------------------------------


def _fetch_text(url: str, *, timeout: float = 20.0) -> tuple[int | None, str | None]:
    """GET a page's decoded body. ``(None, None)`` = unreachable."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None


def _fetch_bytes_ranged(
    url: str, *, limit: int = 2**20, timeout: float = 20.0
) -> tuple[int | None, bytes | None]:
    """A ranged GET (the PMTiles read pattern) returning raw bytes."""
    req = urllib.request.Request(url, headers={"Range": f"bytes=0-{limit - 1}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None


def fetch_sitemap_urls(
    sitemap_url: str, *, max_pages: int, fetcher: Callable[..., Any] | None = None
) -> tuple[list[str], str | None]:
    """``<loc>`` entries of a sitemap, bounded. ``(urls, error)``."""
    fetch = fetcher or _fetch_text
    status, text = fetch(sitemap_url)
    if status != 200 or text is None:
        return [], f"sitemap {sitemap_url} answered {status}"
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    return locs[:max_pages], None


def surface_leg(
    urls: Sequence[str],
    handles: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
    scan: Callable[..., dict[str, Any]] = scan_text,
) -> dict[str, Any]:
    """Crawl a list of URLs on one surface — counts aggregated per surface."""
    fetch = fetcher or _fetch_text
    if not urls:
        return {"verdict": "skipped", "reason": "no URLs supplied for this surface"}
    pages: list[dict[str, Any]] = []
    total_handles = 0
    total_undisclosed = 0
    word_totals: dict[str, dict[str, int]] = {}
    unreachable = 0
    for url in urls:
        status, body = fetch(url)
        if status is None or body is None:
            unreachable += 1
            pages.append({"url": url, "status": status, "scanned": False})
            continue
        res = scan(body, handles)
        total_handles += res["handle_hits"]
        total_undisclosed += res["undisclosed_word_hits"]
        for w, c in res["claim_words"].items():
            agg = word_totals.setdefault(w, {"hits": 0, "undisclosed": 0})
            agg["hits"] += c["hits"]
            agg["undisclosed"] += c["undisclosed"]
        page: dict[str, Any] = {
            "url": url,
            "status": status,
            "scanned": True,
            "handle_hits": res["handle_hits"],
            "undisclosed_word_hits": res["undisclosed_word_hits"],
        }
        if res.get("undisclosed_locations"):
            page["undisclosed_locations"] = res["undisclosed_locations"]
        pages.append(page)
    verdict = "pass"
    if total_handles or total_undisclosed:
        verdict = "fail"
    elif unreachable:
        verdict = "partial"
    return {
        "verdict": verdict,
        "pages": len(pages),
        "scanned": len(pages) - unreachable,
        "unreachable": unreachable,
        "handle_hits": total_handles,
        "claim_words": word_totals,
        "undisclosed_word_hits": total_undisclosed,
        "page_detail": pages,
    }


def tiles_leg(
    tile_urls: Sequence[str],
    handles: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Ranged GET per tile object; byte-scan the returned range."""
    fetch = fetcher or _fetch_bytes_ranged
    if not tile_urls:
        return {"verdict": "skipped", "reason": "no --tile-url given"}
    tiles: list[dict[str, Any]] = []
    total_handles = 0
    total_undisclosed = 0
    unreachable = 0
    for url in tile_urls:
        status, data = fetch(url)
        if status not in (200, 206) or data is None:
            unreachable += 1
            tiles.append({"url": url, "status": status, "scanned": False})
            continue
        res = scan_bytes(data, handles)
        total_handles += res["handle_hits"]
        total_undisclosed += res["undisclosed_word_hits"]
        tiles.append(
            {
                "url": url,
                "status": status,
                "scanned": True,
                "bytes": len(data),
                "handle_hits": res["handle_hits"],
                "claim_words": res["claim_words"],
                "undisclosed_word_hits": res["undisclosed_word_hits"],
            }
        )
    verdict = "pass"
    if total_handles or total_undisclosed:
        verdict = "fail"
    elif unreachable:
        verdict = "partial"
    return {
        "verdict": verdict,
        "tiles": len(tiles),
        "scanned": len(tiles) - unreachable,
        "unreachable": unreachable,
        "handle_hits": total_handles,
        "undisclosed_word_hits": total_undisclosed,
        "tile_detail": tiles,
    }


def listing_leg(listing_file: Path | None, handles: Sequence[str]) -> dict[str, Any]:
    """The downloaded ``sig-public`` object listing — names scanned."""
    if listing_file is None:
        return {"verdict": "skipped", "reason": "no --listing-file given"}
    try:
        text = listing_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"verdict": "fail", "reason": f"cannot read {listing_file}: {exc}"}
    objects = [line for line in text.splitlines() if line.strip()]
    res = scan_text("\n".join(objects), handles)
    verdict = "pass" if res["handle_hits"] == 0 and res["undisclosed_word_hits"] == 0 else "fail"
    return {
        "verdict": verdict,
        "objects": len(objects),
        "handle_hits": res["handle_hits"],
        "claim_words": res["claim_words"],
        "undisclosed_word_hits": res["undisclosed_word_hits"],
    }


def repo_tip_leg(
    *,
    repo_root: Path,
    handle_list: Path,
    export_dirs: Sequence[Path] = (),
    tiles_dirs: Sequence[Path] = (),
    build_dirs: Sequence[Path] = (),
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """The repo tip + served trees — the P34.18 count-only crawl."""
    res = handle_crawl_check(
        repo_root=repo_root,
        handle_list=handle_list,
        export_dirs=export_dirs,
        tiles_dirs=tiles_dirs,
        build_dirs=build_dirs,
        runner=runner,
    )
    return res.as_json()


def suppressed_record(*, reasons: list[str], generated_at: str) -> dict[str, Any]:
    """A refused run's ``sig.probe-run/1`` — the gate fired before any
    fetch; the refusal is the recorded evidence, never a pass."""
    return {
        "version": SCHEMA,
        "generated_at": generated_at,
        "probe": PROBE,
        "target": TARGET,
        "leg": "P34.47-sweep-packet",
        "suppressed": "; ".join(reasons),
        "checks": {},
        "overall": "suppressed",
        "rerun_prompt": RERUN,
    }


def run_sweep(
    *,
    site_urls: Sequence[str],
    api_urls: Sequence[str],
    tile_urls: Sequence[str],
    listing_file: Path | None,
    handle_list: Path,
    repo_root: Path = REPO_ROOT,
    export_dirs: Sequence[Path] = (),
    tiles_dirs: Sequence[Path] = (),
    build_dirs: Sequence[Path] = (),
    l3_soak_read: bool = False,
    reads: dict[str, Any] | None = None,
    now: str | None = None,
    cadence_path: str | Path | None = None,
    env: dict[str, str] | None = None,
    fetch_text: Callable[..., Any] | None = None,
    fetch_bytes: Callable[..., Any] | None = None,
    check_absent: Callable[..., Any] | None = None,
    crawl_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the live sweep and build the ``sig.probe-run/1`` record.

    Only called once the gate says ``run`` — the gate itself is evaluated
    by ``evaluate_gate`` and the CLI refuses (exit 42) before this runs.
    """
    handles: list[str] = []
    ri01_not_checked = not handle_list.is_file()
    if not ri01_not_checked:
        handles = load_handles(handle_list)

    checks: dict[str, Any] = {}
    # F-02: the publish path must refuse /curate/ — the cadence http-absent
    # targets prove the denied routes stay absent (one definition, no drift).
    checks["absence_probe"] = absence_check(
        cadence_path, env=env, check_absent=check_absent
    ).as_json()

    checks["repo_tip"] = (
        repo_tip_leg(
            repo_root=repo_root,
            handle_list=handle_list,
            export_dirs=export_dirs,
            tiles_dirs=tiles_dirs,
            build_dirs=build_dirs,
            runner=crawl_runner,
        )
        if not ri01_not_checked
        else {
            "verdict": "skipped",
            "reason": "handle list absent — RI-01 not checked (blockedOn)",
        }
    )
    checks["site"] = surface_leg(site_urls, handles, fetcher=fetch_text)
    checks["api"] = surface_leg(api_urls, handles, fetcher=fetch_text)
    checks["tiles"] = tiles_leg(tile_urls, handles, fetcher=fetch_bytes)
    checks["sig_public_listing"] = listing_leg(listing_file, handles)

    surfaces = ("repo_tip", "site", "api", "tiles", "sig_public_listing")
    if ri01_not_checked:
        checks["ri01"] = {
            "verdict": "skipped",
            "state": "not-checked",
            "detail": "handle list absent — RI-01 reported not checked",
        }
    else:
        surface_fails = [s for s in surfaces if checks[s].get("verdict") == "fail"]
        surface_hits = sum(
            int(checks[s].get("handle_hits") or 0)
            + int(checks[s].get("repo_and_trees", {}).get("hits") or 0)
            for s in surfaces
        )
        surface_skipped = [
            s for s in surfaces if checks[s].get("verdict") in ("skipped", "partial")
        ]
        if surface_fails or surface_hits:
            checks["ri01"] = {
                "verdict": "fail",
                "state": "open",
                "detail": (
                    f"handle hits/failed surfaces "
                    f"({', '.join(surface_fails) or 'hits'}) — RI-01 stays open"
                ),
            }
        elif surface_skipped:
            checks["ri01"] = {
                "verdict": "skipped",
                "state": "open",
                "detail": (
                    f"surfaces unproven: {', '.join(surface_skipped)} — "
                    "RI-01 not closed, never passed"
                ),
            }
        else:
            checks["ri01"] = {
                "verdict": "pass",
                "state": "closed",
                "detail": "0 handle-list entries on every surface — RI-01 closes",
            }
    checks["exit_item_5_soak"] = (
        {"verdict": "skipped", "reason": "P34.46's L3 soak read not yet recorded"}
        if not l3_soak_read
        else {"verdict": "pass", "detail": "L3 soak read recorded — evaluated live"}
    )
    if reads:
        # the leg-captured reads (scheduler triggers, billing export, managed
        # cert) — verbatim caller-captured summaries, never fabricated
        checks["reads"] = {"verdict": "pass", "reads": reads}
    else:
        checks["reads"] = {
            "verdict": "skipped",
            "reason": "no --reads-file given — scheduler/billing/cert reads "
            "are captured by the leg caller and supplied here",
        }

    verdicts = [c.get("verdict") for c in checks.values() if isinstance(c, dict)]
    if "fail" in verdicts:
        overall = "fail"
    elif "skipped" in verdicts or "partial" in verdicts:
        overall = "partial"
    elif "open" in verdicts:
        overall = "fail"
    else:
        overall = "pass"
    return {
        "version": SCHEMA,
        "generated_at": now or _now(),
        "probe": PROBE,
        "target": TARGET,
        "leg": "P34.47-sweep-packet",
        "handles_checked": len(handles) if not ri01_not_checked else 0,
        "checks": checks,
        "overall": overall,
        "rerun_prompt": RERUN,
        "method": (
            "counts only: handle values are never printed or recorded; "
            "claim-word hits are counted undisclosed unless their line "
            "matches the disclosed-context list (TS-10)"
        ),
    }


def load_inputs(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise AcceptanceError(f"cannot read inputs {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"bad JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sig-ops acceptance-sweep",
        description=(
            "P34.47 — the 11A live-read acceptance sweep → sig.probe-run/1. "
            "Gated: refuses (exit 42, suppressed record) until P34.46's L2 "
            "has landed and the window floor has passed. --check evaluates "
            "the gate only."
        ),
    )
    ap.add_argument("--check", action="store_true", help="evaluate the gate only")
    ap.add_argument(
        "--inputs",
        default=None,
        help="a recorded inputs JSON instead of the live RETURN PASS map read",
    )
    ap.add_argument("--map", dest="map_path", default=str(DEFAULT_MAP))
    ap.add_argument("--at", dest="at", default=None, help="the 'now' instant (default: the clock)")
    ap.add_argument("--handle-list", default=str(DEFAULT_HANDLE_LIST))
    ap.add_argument("--record-out", default=None, help="write the probe-run record here")
    ap.add_argument("--site-url", action="append", default=[], help="a site page to crawl")
    ap.add_argument("--sitemap-url", default=None, help="fetch <loc> entries as site URLs")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--api-url", action="append", default=[], help="an API route to crawl")
    ap.add_argument("--tile-url", action="append", default=[], help="a tile object to ranged-GET")
    ap.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml for the F-02 absence probe (denied routes)",
    )
    ap.add_argument("--listing-file", default=None, help="a downloaded sig-public object listing")
    ap.add_argument(
        "--reads-file",
        default=None,
        help="a caller-captured JSON of the other reads (scheduler/billing/cert)",
    )
    ap.add_argument("--export-dir", action="append", default=[])
    ap.add_argument("--tiles-dir", action="append", default=[])
    ap.add_argument("--build-dir", action="append", default=[])
    args = ap.parse_args(argv)

    try:
        if args.inputs:
            inputs = load_inputs(args.inputs)
            inputs.setdefault("handle_list_present", Path(args.handle_list).is_file())
        else:
            inputs = map_derived_inputs(
                Path(args.map_path), now=args.at, handle_list=Path(args.handle_list)
            )
        gate = evaluate_gate(inputs)
        reads = load_inputs(args.reads_file) if args.reads_file else None
    except AcceptanceError as exc:
        print(f"sig-ops acceptance-sweep: REFUSED — {exc}", file=sys.stderr)
        return 2

    gate_record = gate.to_record()
    if args.check:
        print(json.dumps(gate_record, indent=2, sort_keys=True))
        if gate.decision != "run":
            if args.record_out:
                rec = suppressed_record(
                    reasons=gate.refusals, generated_at=inputs.get("now") or _now()
                )
                Path(args.record_out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.record_out).write_text(
                    json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                print(
                    f"sig-ops acceptance-sweep: suppressed probe-run -> {args.record_out}",
                    file=sys.stderr,
                )
            print(
                "sig-ops acceptance-sweep: QUEUED — the leg refuses; exit 42 "
                "(re-run prompt in the record).",
                file=sys.stderr,
            )
            return 42
        print("sig-ops acceptance-sweep: gate green — the sweep may run.", file=sys.stderr)
        return 0

    if gate.decision != "run":
        print(json.dumps(gate_record, indent=2, sort_keys=True))
        if args.record_out:
            rec = suppressed_record(reasons=gate.refusals, generated_at=inputs.get("now") or _now())
            Path(args.record_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.record_out).write_text(
                json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"sig-ops acceptance-sweep: suppressed probe-run -> {args.record_out}",
                file=sys.stderr,
            )
        print(
            "sig-ops acceptance-sweep: QUEUED — the leg refuses; exit 42.",
            file=sys.stderr,
        )
        return 42

    site_urls = list(args.site_url)
    if args.sitemap_url:
        locs, err = fetch_sitemap_urls(args.sitemap_url, max_pages=args.max_pages)
        if err:
            print(f"sig-ops acceptance-sweep: sitemap: {err}", file=sys.stderr)
        site_urls += locs
    record = run_sweep(
        site_urls=site_urls,
        api_urls=list(args.api_url),
        tile_urls=list(args.tile_url),
        listing_file=Path(args.listing_file) if args.listing_file else None,
        handle_list=Path(args.handle_list),
        export_dirs=[Path(d) for d in args.export_dir],
        tiles_dirs=[Path(d) for d in args.tiles_dir],
        build_dirs=[Path(d) for d in args.build_dir],
        l3_soak_read=inputs.get("p34_46_l3_soak_read") is True,
        reads=reads,
        cadence_path=args.cadence,
        now=inputs.get("now") or args.at,
    )
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.record_out:
        Path(args.record_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.record_out).write_text(text + "\n", encoding="utf-8")
        print(f"sig-ops acceptance-sweep: record -> {args.record_out}", file=sys.stderr)
    print(f"sig-ops acceptance-sweep: overall={record['overall']}", file=sys.stderr)
    return 0 if record["overall"] == "pass" else (1 if record["overall"] == "fail" else 3)
