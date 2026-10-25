# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.64 — the 11B live-read acceptance sweep → a ``sig.probe-run/1`` record.

The capstone's live half (ticket 342, plan S2 §4.2 — contract
``docs/tickets/342_P35.64__sub-round-11b-acceptance.md``): a **read-only**
sweep of the promoted first model release — the thing P35.63 promotes
under the operator's signed HG-11 readout — plus the release-adjacent
surfaces the 11B rows wrote. Its surfaces are release-specific where the
11A sweep's were deployment-generic:

* the promoted release's routes — ``/releases/``, ``/releases/<pub>/``
  and the archive tree ``/r/<pub>/`` — each serving with its pinned
  citation (the release stamp a served page carries, never an unpinned
  release page);
* the release-search surface (``/v1/releases/…/search`` JSON + the
  ``format=html`` route + the web ``?q=`` state);
* the nginx withdrawal barrier — every published disposition answers
  410 + a tombstone body on every alias (G2 activation §4 step 7,
  SIG-RIGHTS-007);
* dossier levels country→place incl. the unplaced report;
* ``/network/`` labels + evidence links (SIG-CONF-005: 0 UUID-only
  labels; every figure reaching evidence in ≤2 clicks or saying why);
* release-namespaced API/web parity;
* eval-confidence disclosures (SIG-CONF-010/012 — ``provisional`` /
  ``review-only`` / ``no human check performed`` wording where it
  belongs);
* map tiles for release-named sites (z≥10).

**The gate.** The sweep's recorded window is ``after P35.63 promotion``
— verbatim — so the gate is the promoted release's existence, read from
the RETURN PASS map: it runs only while ``P35.63``'s row carries no
queued leg. Both legs queued → the sweep refuses (exit 42) and, when
``--record-out`` is given, writes a *suppressed* ``sig.probe-run/1``
record — suppressed is **not** a pass: the live verdict stays queued and
the acceptance note cites this record as its own suppression, never as
a live check. ``--check`` evaluates the gate only.

Reads are never fabricated: every leg runs on supplied routes (a
``--routes-file`` spec or the individual options), skips with a stated
reason when its input set is empty, and records zero counts honestly —
no 200 is ever inferred.

The verbatim re-run prompt (contract §OM-19, scope: the sweep and the
packet — the packet re-drafts from the committed records of that day)::

    implement-spec spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md live_verification=true

Exit codes: ``0`` = sweep ran (see ``overall``) · ``42`` = gated/queued
· ``1`` = sweep findings · ``2`` = usage. stdlib + ``ops.acceptance``.
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

from .republish_probe import REPO_ROOT

SCHEMA = "sig.probe-run/1"
GATE_KIND = "sig.acceptance-gate/1"
PROBE = "sig-11b-acceptance"
TARGET = "11b-promoted-release"
LEG = "P35.64-sweep-packet"

#: The ticket's re-run prompt, recorded on every refusal/queued state —
#: verbatim per the contract (the scope is the sweep and the packet).
RERUN = (
    "implement-spec "
    "spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md "
    "live_verification=true"
)

DEFAULT_MAP = REPO_ROOT / "docs" / "build" / "tools" / "record_policy" / "return_pass.toml"

#: A pinned-citation marker a served release page carries: the p-<sha>
#: route stamp of the release tree or a data-release attribute. A routes
#: spec entry may override with its own markers; the absence of every
#: marker on a served page is an unpinned page — a finding.
PIN_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"p-[0-9a-f]{8,}"),
    re.compile(r"data-release="),
    re.compile(r"release-sha"),
)

#: A bare UUID used as visible label text (SIG-CONF-005: 0 UUID-only
#: labels on /network/) — counted on text nodes only.
UUID_ONLY = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
_TEXT_NODE = re.compile(r">([^<>{}]+)<")
_FIGURE = re.compile(r"<figure\b.*?</figure>", re.DOTALL)


class Acceptance11BError(ValueError):
    """A malformed sweep input (usage failure, exit 2)."""


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_text(url: str, *, timeout: float = 20.0) -> tuple[int | None, str | None]:
    """GET a page's decoded body. ``(None, None)`` = unreachable."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = None
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except OSError:
            body = None
        return int(exc.code), body
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


# ---------------------------------------------------------------------------
# The gate — the promoted-release precondition (the recorded window is
# "after P35.63 promotion") + a recorded instant, in the roll_gate style.
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
            "leg": LEG,
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "advisories": self.advisories,
            "rerun_prompt": None if self.decision == "run" else RERUN,
            "window": "after P35.63 promotion",
        }


def evaluate_gate(inputs: dict[str, Any]) -> Gate:
    """Judge the recorded inputs. Hard criteria: ``p35_63_promotion`` +
    ``now``. The surface advisories scope legs; they never block."""
    if not isinstance(inputs, dict):
        raise Acceptance11BError("the gate input must be a JSON object")
    criteria: list[Criterion] = []
    advisories: list[str] = []

    promoted = inputs.get("p35_63_promoted")
    criteria.append(
        Criterion(
            "p35_63_promotion",
            promoted is True,
            (
                "the promoted first model release exists — P35.63's promotion "
                "leg has left the RETURN PASS queue"
                if promoted is True
                else (
                    "the promoted first model release does not exist — "
                    "P35.63's promotion leg is still queued in the RETURN "
                    "PASS map (live:P35.63 fails; the promotion awaits the "
                    "operator's signed, candidate-specific HG-11 readout)"
                    if inputs.get("p35_63_row_present", True)
                    else "the RETURN PASS map carries no P35.63 row — the "
                    "promotion state is recorded unread, never assumed"
                )
            ),
            promoted,
        )
    )
    criteria.append(
        Criterion(
            "window",
            inputs.get("now") is not None,
            (
                f"the sweep's recorded instant is {inputs['now']}"
                if inputs.get("now")
                else "no 'now' instant supplied — the gate evaluates a "
                "recorded instant, never the wall clock"
            ),
            inputs.get("now"),
        )
    )

    routes = inputs.get("routes") or {}
    if not routes:
        advisories.append(
            "no routes spec supplied — every surface leg reports skipped "
            "with a reason, never a fabricated count"
        )
    if not routes.get("withdrawal_aliases"):
        advisories.append(
            "no published dispositions supplied — the withdrawal leg reports "
            "skipped (the disposition set is a GATE-G5 publication line, "
            "pending), never inferred"
        )
    if inputs.get("disposition_set_present") is not True:
        advisories.append(
            "no committed disposition set — exit item 'nginx honours "
            "withdrawals' reports queued/skipped, never passed"
        )

    decision = "run" if all(c.ok for c in criteria) else "queued"
    return Gate(decision=decision, criteria=criteria, advisories=advisories)


def map_derived_inputs(map_path: Path, *, now: str | None = None) -> dict[str, Any]:
    """Read the RETURN PASS map: P35.63's queued legs decide the promotion.

    The map holds only *queued* legs — a leg that ran leaves the row — so
    `p35_63_promoted` is True only when the row carries no queued leg.
    """
    try:
        data = tomllib.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise Acceptance11BError(f"cannot read the RETURN PASS map {map_path}: {exc}") from exc
    p63: dict[str, Any] = next((r for r in data.get("row", []) if r.get("key") == "P35.63"), {})
    leg_ids = {leg.get("id") for leg in p63.get("legs", [])}
    return {
        "now": now or _now(),
        # the map holds only queued legs — the promotion exists once its leg
        # has left the queue (the 11A convention: "P34.46-slot" absent)
        "p35_63_promoted": bool(p63) and "P35.63-promote-under-hg11" not in leg_ids,
        "p35_63_row_present": bool(p63),
        "queued_p35_63_legs": sorted(x for x in leg_ids if x),
    }


def suppressed_record(*, reasons: list[str], generated_at: str) -> dict[str, Any]:
    """A refused run's ``sig.probe-run/1`` — the gate fired before any
    fetch; the refusal is the recorded evidence, never a pass."""
    return {
        "version": SCHEMA,
        "generated_at": generated_at,
        "probe": PROBE,
        "target": TARGET,
        "leg": LEG,
        "suppressed": "; ".join(reasons),
        "checks": {},
        "overall": "suppressed",
        "rerun_prompt": RERUN,
        "window": "after P35.63 promotion",
        "suppression_note": (
            "the sweep's recorded window is `after P35.63 promotion`, "
            "verbatim; it re-runs at the ticket's verbatim prompt. "
            "Suppressed is not a pass: the live verdict stays queued; this "
            "record exists so the acceptance note cites its own "
            "suppression."
        ),
    }


# ---------------------------------------------------------------------------
# The surface legs — every leg reports honestly; a skipped leg is
# "skipped" with a reason, never a fabricated pass. The fetchers return
# (status, body); (None, None) means unreachable.
# ---------------------------------------------------------------------------


def release_routes_leg(
    urls: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
    pin_markers: tuple[re.Pattern[str], ...] = PIN_MARKERS,
) -> dict[str, Any]:
    """The promoted release's routes — 200 + a pin marker on every page."""
    fetch = fetcher or _fetch_text
    if not urls:
        return {
            "verdict": "skipped",
            "reason": "no release routes supplied (the promoted release's "
            "route tree is caller-supplied)",
        }
    pages: list[dict[str, Any]] = []
    unpinned = 0
    unreachable = 0
    for url in urls:
        status, body = fetch(url)
        if status is None or status != 200 or body is None:
            pages.append({"url": url, "status": status, "pinned": None})
            if status is None:
                unreachable += 1
            continue
        pinned = any(m.search(body) for m in pin_markers)
        if not pinned:
            unpinned += 1
        pages.append({"url": url, "status": 200, "pinned": pinned})
    verdict = "pass"
    if unpinned or any(p["status"] not in (200, None) for p in pages):
        verdict = "fail"
    elif unreachable:
        verdict = "partial"
    return {
        "verdict": verdict,
        "pages": len(pages),
        "unpinned": unpinned,
        "unreachable": unreachable,
        "page_detail": pages[:40],
    }


def release_search_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Release-search surface — JSON + format=html + web ?q= routes."""
    fetch = fetcher or _fetch_text
    if not routes:
        return {"verdict": "skipped", "reason": "no release-search routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url, expect = rt["url"], int(rt.get("expect", 200))
        status, body = fetch(url)
        entry: dict[str, Any] = {"url": url, "expect": expect, "status": status}
        if status == expect and body is not None:
            if body.lstrip().startswith("{"):
                try:
                    entry["rows"] = len(json.loads(body).get("results", []))
                except (ValueError, AttributeError):
                    entry["rows"] = "unparsed"
        elif status is None:
            unreachable += 1
        else:
            failed += 1
        detail.append(entry)
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "routes": len(routes),
        "unreachable": unreachable,
        "route_detail": detail,
    }


def withdrawal_leg(
    aliases: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Every published disposition: 410 + tombstone body on every alias."""
    fetch = fetcher or _fetch_text
    if not aliases:
        return {
            "verdict": "skipped",
            "reason": "no published dispositions supplied — the barrier "
            "stays unprobed this run (never inferred)",
        }
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for url in aliases:
        status, body = fetch(url)
        tombstone = bool(body) and (
            "withdrawn" in (body or "").lower() or "tombstone" in (body or "").lower()
        )
        ok = status == 410 and tombstone
        entry: dict[str, Any] = {"url": url, "status": status, "tombstone": tombstone}
        if status is None:
            unreachable += 1
        elif not ok:
            failed += 1
        detail.append(entry)
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "aliases": len(aliases),
        "aliases_410": sum(1 for d in detail if d["status"] == 410),
        "unreachable": unreachable,
        "alias_detail": detail,
    }


def dossier_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Dossier levels country→place incl. the unplaced report — serving."""
    fetch = fetcher or _fetch_text
    if not routes:
        return {"verdict": "skipped", "reason": "no dossier routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url, level = rt["url"], rt.get("level", "?")
        status, body = fetch(url)
        detail.append({"level": level, "url": url, "status": status})
        if status is None or body is None:
            unreachable += 1
        elif status != 200:
            failed += 1
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "levels": len(routes),
        "served": sum(1 for d in detail if d["status"] == 200),
        "unreachable": unreachable,
        "level_detail": detail,
    }


def network_leg(
    url: str | None,
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """``/network/`` — 0 UUID-only labels; every figure reaching evidence
    in ≤2 clicks or saying why (SIG-CONF-005). Counts are DOM-heuristic —
    reported verbatim so the operator can re-check the rendered page."""
    fetch = fetcher or _fetch_text
    if not url:
        return {"verdict": "skipped", "reason": "no /network/ route supplied"}
    status, body = fetch(url)
    if status != 200 or body is None:
        return {
            "verdict": "fail" if status not in (None,) else "partial",
            "reason": f"GET {url} answered {status}",
        }
    text_nodes = " ".join(_TEXT_NODE.findall(body))
    uuid_only = len(UUID_ONLY.findall(text_nodes))
    fig_blocks = _FIGURE.findall(body)
    evidence_link = re.compile(r"""href=["']/r/""", re.IGNORECASE)
    fig_no_evidence = sum(
        1
        for fb in fig_blocks
        if not evidence_link.search(fb)
        and "data-evidence" not in fb
        and "no evidence link" not in fb.lower()
    )
    verdict = "pass" if uuid_only == 0 and fig_no_evidence == 0 else "fail"
    return {
        "verdict": verdict,
        "uuid_only_labels": uuid_only,
        "figures": len(fig_blocks),
        "figures_without_evidence_link": fig_no_evidence,
    }


def parity_leg(
    pairs: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Release-namespaced API/web parity — same status on both surfaces."""
    fetch = fetcher or _fetch_text
    if not pairs:
        return {"verdict": "skipped", "reason": "no parity pairs supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for pr in pairs:
        a_status, _a = fetch(pr["api"])
        w_status, _w = fetch(pr["web"])
        entry = {
            "api": pr["api"],
            "web": pr["web"],
            "api_status": a_status,
            "web_status": w_status,
        }
        detail.append(entry)
        if a_status is None or w_status is None:
            unreachable += 1
        elif a_status != w_status:
            failed += 1
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "pairs": len(pairs),
        "parities": sum(1 for d in detail if d["api_status"] == d["web_status"] is not None),
        "unreachable": unreachable,
        "pair_detail": detail,
    }


def disclosure_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Eval-confidence disclosures — the required wording present where
    it belongs (SIG-CONF-010/012: provisional / review-only / no human
    check performed)."""
    fetch = fetcher or _fetch_text
    if not routes:
        return {"verdict": "skipped", "reason": "no disclosure routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url, required = rt["url"], list(rt.get("required", []))
        status, body = fetch(url)
        entry: dict[str, Any] = {"url": url, "status": status}
        if status != 200 or body is None:
            if status is None:
                unreachable += 1
            else:
                failed += 1
        else:
            missing = [p for p in required if p not in body]
            entry["missing"] = missing
            if missing:
                failed += 1
        detail.append(entry)
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "routes": len(routes),
        "unreachable": unreachable,
        "route_detail": detail,
    }


def tiles_leg(
    tile_urls: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Ranged GET per tile object (the release's z≥10 site tiles)."""
    fetch = fetcher or _fetch_bytes_ranged
    if not tile_urls:
        return {"verdict": "skipped", "reason": "no tile URLs supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    for url in tile_urls:
        status, data = fetch(url)
        ok = status in (200, 206) and data is not None
        n = len(data) if ok and isinstance(data, bytes) else 0
        detail.append({"url": url, "status": status, "bytes": n})
        if not ok:
            unreachable += 1
    verdict = "pass" if not unreachable else "fail"
    return {
        "verdict": verdict,
        "tiles": len(tile_urls),
        "served": len(tile_urls) - unreachable,
        "unreachable": unreachable,
        "tile_detail": detail,
    }


def run_sweep(
    *,
    routes: dict[str, Any],
    reads: dict[str, Any] | None = None,
    now: str | None = None,
    fetch_text: Callable[..., Any] | None = None,
    fetch_bytes: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the live sweep and build the ``sig.probe-run/1`` record.

    Only called once the gate says ``run`` — the gate itself is evaluated
    by ``evaluate_gate`` and the CLI refuses (exit 42) before this runs.
    """
    checks: dict[str, Any] = {
        "release_routes": release_routes_leg(
            list(routes.get("release_routes") or []), fetcher=fetch_text
        ),
        "release_search": release_search_leg(
            list(routes.get("release_search") or []), fetcher=fetch_text
        ),
        "withdrawal": withdrawal_leg(
            list(routes.get("withdrawal_aliases") or []), fetcher=fetch_text
        ),
        "dossiers": dossier_leg(list(routes.get("dossier_routes") or []), fetcher=fetch_text),
        "network": network_leg(routes.get("network_url"), fetcher=fetch_text),
        "tiles": tiles_leg(list(routes.get("tile_urls") or []), fetcher=fetch_bytes),
        "parity": parity_leg(list(routes.get("parity_pairs") or []), fetcher=fetch_text),
        "disclosures": disclosure_leg(list(routes.get("disclosures") or []), fetcher=fetch_text),
    }
    if reads:
        checks["reads"] = {
            "verdict": "pass",
            "reads": reads,
            "detail": "caller-captured reads, verbatim — never fabricated",
        }
    else:
        checks["reads"] = {
            "verdict": "skipped",
            "reason": "no --reads-file given — the other reads are captured "
            "by the leg caller and supplied here",
        }

    verdicts = [c.get("verdict") for c in checks.values() if isinstance(c, dict)]
    if "fail" in verdicts:
        overall = "fail"
    elif "skipped" in verdicts or "partial" in verdicts:
        overall = "partial"
    else:
        overall = "pass"
    return {
        "version": SCHEMA,
        "generated_at": now or _now(),
        "probe": PROBE,
        "target": TARGET,
        "leg": LEG,
        "checks": checks,
        "overall": overall,
        "rerun_prompt": RERUN,
        "method": (
            "read-only GETs over caller-supplied routes; a leg with no "
            "inputs reports skipped with a reason; no 200 is ever inferred; "
            "the /network/ counts are DOM-heuristic and reported verbatim"
        ),
    }


# ---------------------------------------------------------------------------
# The routes spec — a committed-style JSON the leg caller builds from the
# promoted release's own route manifest; individual options append.
# ---------------------------------------------------------------------------


def _parse_routes(args: argparse.Namespace) -> dict[str, Any]:
    routes: dict[str, Any] = {
        "release_routes": [],
        "release_search": [],
        "withdrawal_aliases": [],
        "dossier_routes": [],
        "parity_pairs": [],
        "disclosures": [],
        "tile_urls": [],
    }
    if args.routes_file:
        try:
            spec = json.loads(Path(args.routes_file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Acceptance11BError(f"--routes-file unreadable: {exc}") from exc
        if not isinstance(spec, dict):
            raise Acceptance11BError("--routes-file must be a JSON object")
        for k, v in spec.items():
            routes[k] = v
    base = (args.site_base or "").rstrip("/")

    def _abs(u: str) -> str:
        return u if u.startswith(("http://", "https://")) else base + u

    routes["release_routes"] += [_abs(u) for u in args.release_url]
    routes["release_search"] += [{"url": _abs(u), "expect": 200} for u in args.search_url]
    routes["withdrawal_aliases"] += [_abs(u) for u in args.withdrawal_alias]
    for d in args.dossier:
        level, sep, url = d.partition(":")
        if not sep or not level or not url:
            raise Acceptance11BError(f"--dossier needs LEVEL:URL — got {d!r}")
        routes["dossier_routes"].append({"level": level, "url": _abs(url)})
    if args.network_url:
        routes["network_url"] = _abs(args.network_url)
    routes["tile_urls"] += list(args.tile_url)
    for p in args.parity:
        a, sep, w = p.partition("|")
        if not sep:
            raise Acceptance11BError(f"--parity needs API_URL|WEB_URL — got {p!r}")
        routes["parity_pairs"].append({"api": a, "web": w})
    for d in args.disclosure:
        url, sep, phrases = d.partition("=")
        if not sep:
            raise Acceptance11BError(f"--disclosure needs URL=PHRASE[,PHRASE] — got {d!r}")
        routes["disclosures"].append(
            {"url": _abs(url), "required": [x for x in phrases.split(",") if x]}
        )
    return {k: v for k, v in routes.items() if v}


def load_inputs(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise Acceptance11BError(f"cannot read inputs {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise Acceptance11BError(f"bad JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sig-ops acceptance-sweep-11b",
        description=(
            "P35.64 — the 11B live-read acceptance sweep → sig.probe-run/1. "
            "Gated: refuses (exit 42, suppressed record) until the promoted "
            "first model release exists (P35.63's legs out of the queue). "
            "--check evaluates the gate only."
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
    ap.add_argument(
        "--routes-file",
        default=None,
        help="a routes-spec JSON (per-surface URL lists, built from the "
        "promoted release's own route manifest)",
    )
    ap.add_argument("--site-base", default=None, help="site base URL for relative routes")
    ap.add_argument("--record-out", default=None, help="write the probe-run record here")
    ap.add_argument("--release-url", action="append", default=[], help="a release route")
    ap.add_argument("--search-url", action="append", default=[], help="a release-search route")
    ap.add_argument("--withdrawal-alias", action="append", default=[], help="a disposition alias")
    ap.add_argument("--dossier", action="append", default=[], help="LEVEL:URL dossier route")
    ap.add_argument("--network-url", default=None, help="the /network/ route")
    ap.add_argument("--tile-url", action="append", default=[], help="a tile object")
    ap.add_argument("--parity", action="append", default=[], help="API_URL|WEB_URL parity pair")
    ap.add_argument(
        "--disclosure",
        action="append",
        default=[],
        help="URL=PHRASE[,PHRASE] required disclosure wording",
    )
    ap.add_argument(
        "--reads-file",
        default=None,
        help="a caller-captured JSON of the other reads (release registry, "
        "disposition set, tile listing)",
    )
    args = ap.parse_args(argv)

    try:
        if args.inputs:
            inputs = load_inputs(args.inputs)
        else:
            inputs = map_derived_inputs(Path(args.map_path), now=args.at)
        if args.at:
            inputs["now"] = args.at
        inputs["routes"] = _parse_routes(args)
        gate = evaluate_gate(inputs)
        reads = load_inputs(args.reads_file) if args.reads_file else None
    except Acceptance11BError as exc:
        print(f"sig-ops acceptance-sweep-11b: REFUSED — {exc}", file=sys.stderr)
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
                    f"sig-ops acceptance-sweep-11b: suppressed probe-run -> {args.record_out}",
                    file=sys.stderr,
                )
            print(
                "sig-ops acceptance-sweep-11b: QUEUED — the leg refuses; exit 42 "
                "(re-run prompt in the record).",
                file=sys.stderr,
            )
            return 42
        print(
            "sig-ops acceptance-sweep-11b: gate green — the sweep may run.",
            file=sys.stderr,
        )
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
                f"sig-ops acceptance-sweep-11b: suppressed probe-run -> {args.record_out}",
                file=sys.stderr,
            )
        print(
            "sig-ops acceptance-sweep-11b: QUEUED — the leg refuses; exit 42.",
            file=sys.stderr,
        )
        return 42

    record = run_sweep(
        routes=inputs.get("routes") or {},
        reads=reads,
        now=inputs.get("now") or args.at,
    )
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.record_out:
        Path(args.record_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.record_out).write_text(text + "\n", encoding="utf-8")
        print(f"sig-ops acceptance-sweep-11b: record -> {args.record_out}", file=sys.stderr)
    print(f"sig-ops acceptance-sweep-11b: overall={record['overall']}", file=sys.stderr)
    return 0 if record["overall"] == "pass" else (1 if record["overall"] == "fail" else 3)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
