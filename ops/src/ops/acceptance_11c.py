# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.73 — the 11C live-read acceptance sweep → a ``sig.probe-run/1`` record.

The capstone's live half (ticket 419, plan S2 §4.3 — contract
``docs/tickets/419_P36.73__sub-round-11c-acceptance.md``): a **read-only**
sweep of the promoted core-surfaces release — the thing P36.72b promotes
under the operator's signed HG-11 Class S readout at the GATE-G6 sitting —
checking that the advertised state matches the recorded state. Its legs:

* the promoted release's routes — ``/r/<pub>/`` and the route tree — each
  serving with its pinned citation (11B's check, carried);
* **advertised routes resolve** — every route the surface advertises (the
  route manifest / sitemap set, caller-supplied) answers its declared
  status, never a fabricated 200;
* **budgets hold** — the wire-measured bytes of each supplied route stay
  under the caller's per-route ceiling (ADR-155's page-type budgets read
  on the wire, never asserted);
* **labels read what they claim** — 0 bare-UUID labels on the supplied
  pages (SIG-CONF-005) plus the pinned-release markers the release pages
  carry;
* **the changelog and mirrors serve** — the changelog route and each
  supplied mirror endpoint (``versions.json``, content-addressed objects)
  answer, with a sha256 binding when the caller supplies one;
* the release-search surface + **search resolves** — JSON query routes
  returning at least their declared minimum rows (the §4.3 exit-4 shape:
  jurisdictions, cities, vendor and agency names — the caller's query set);
* **rate limits enforced** — the supplied API routes answer with a
  recognised rate-limit header present (the enforcement signal a read can
  honestly record; a 429 is only ever measured, never provoked on purpose
  beyond the caller's declared probe);
* the nginx withdrawal barrier, dossier levels, ``/network/`` labels +
  evidence links, release-namespaced API/web parity, eval-confidence
  disclosures and map tiles — the 11B legs, carried.

**The gate.** The sweep's recorded window is ``after P36.72 promotion``
— verbatim — so the gate is the promoted release's existence, read from
the RETURN PASS map: it runs only while ``P36.72b``'s row carries no
queued ``P36.72b-promote`` leg. The leg queued → the sweep refuses (exit
42) and, when ``--record-out`` is given, writes a *suppressed*
``sig.probe-run/1`` record — suppressed is **not** a pass: the live
verdict stays queued and the acceptance note cites this record as its own
suppression, never as a live check. ``--check`` evaluates the gate only.

Reads are never fabricated: every leg runs on supplied routes (a
``--routes-file`` spec or the individual options), skips with a stated
reason when its input set is empty, and records zero counts honestly —
no 200 is ever inferred.

The verbatim re-run prompt (contract §OM-19, scope: the sweep and the
packet — the packet re-drafts from the committed records of that day)::

    implement-spec spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md live_verification=true

Exit codes: ``0`` = sweep ran (see ``overall``) · ``42`` = gated/queued
· ``1`` = sweep findings · ``2`` = usage. stdlib + ``ops.acceptance_11b``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import acceptance_11b as a11b
from .republish_probe import REPO_ROOT

SCHEMA = "sig.probe-run/1"
GATE_KIND = "sig.acceptance-gate/1"
PROBE = "sig-11c-acceptance"
TARGET = "11c-promoted-release"
LEG = "P36.73-sweep-packet"

#: The ticket's re-run prompt, recorded on every refusal/queued state —
#: verbatim per the contract (the scope is the sweep and the packet).
RERUN = (
    "implement-spec "
    "spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md "
    "live_verification=true"
)

DEFAULT_MAP = REPO_ROOT / "docs" / "build" / "tools" / "record_policy" / "return_pass.toml"

#: Recognised rate-limit header names (RFC 9333 + the common X- forms) —
#: enforcement a read can honestly observe on an ordinary response.
RATE_HEADERS = (
    "ratelimit",
    "ratelimit-limit",
    "ratelimit-remaining",
    "ratelimit-reset",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "retry-after",
)


class Acceptance11CError(ValueError):
    """A malformed sweep input (usage failure, exit 2)."""


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_headers(url: str, *, timeout: float = 20.0) -> tuple[int | None, dict[str, str]]:
    """GET a route's status + response headers (lowercased names)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        return int(exc.code), {k.lower(): v for k, v in exc.headers.items()}
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, {}


# ---------------------------------------------------------------------------
# The gate — the promoted-release precondition (the recorded window is
# "after P36.72 promotion") + a recorded instant, in the 11B style.
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
            "window": "after P36.72 promotion",
        }


def evaluate_gate(inputs: dict[str, Any]) -> Gate:
    """Judge the recorded inputs. Hard criteria: ``p36_72b_promotion`` +
    ``now``. The surface advisories scope legs; they never block."""
    if not isinstance(inputs, dict):
        raise Acceptance11CError("the gate input must be a JSON object")
    criteria: list[Criterion] = []
    advisories: list[str] = []

    promoted = inputs.get("p36_72b_promoted")
    criteria.append(
        Criterion(
            "p36_72b_promotion",
            promoted is True,
            (
                "the promoted core-surfaces release exists — P36.72b's "
                "promotion leg has left the RETURN PASS queue"
                if promoted is True
                else (
                    "the promoted core-surfaces release does not exist — "
                    "P36.72b's promote leg is still queued in the RETURN "
                    "PASS map (live:P36.72b fails; the promotion awaits the "
                    "operator's signed, candidate-specific HG-11 readout "
                    "at the GATE-G6 sitting)"
                    if inputs.get("p36_72b_row_present", True)
                    else "the RETURN PASS map carries no P36.72b row — the "
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
            "skipped (the disposition set is a GATE-G6 publication line, "
            "pending), never inferred"
        )
    if not routes.get("mirror_urls"):
        advisories.append(
            "no mirror endpoints supplied — the mirrors leg reports "
            "skipped (the mirror leg D-P36.68-1 stays queued), never "
            "inferred"
        )
    if inputs.get("disposition_set_present") is not True:
        advisories.append(
            "no committed disposition set — the withdrawal-barrier read "
            "reports queued/skipped, never passed"
        )

    decision = "run" if all(c.ok for c in criteria) else "queued"
    return Gate(decision=decision, criteria=criteria, advisories=advisories)


def map_derived_inputs(map_path: Path, *, now: str | None = None) -> dict[str, Any]:
    """Read the RETURN PASS map: P36.72b's queued legs decide the promotion.

    The map holds only *queued* legs — a leg that ran leaves the row — so
    `p36_72b_promoted` is True only when the row carries no queued
    `P36.72b-promote` leg.
    """
    try:
        data = tomllib.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise Acceptance11CError(f"cannot read the RETURN PASS map {map_path}: {exc}") from exc
    row: dict[str, Any] = next((r for r in data.get("row", []) if r.get("key") == "P36.72b"), {})
    leg_ids = {leg.get("id") for leg in row.get("legs", [])}
    return {
        "now": now or _now(),
        # the map holds only queued legs — the promotion exists once its leg
        # has left the queue (the 11A/11B convention)
        "p36_72b_promoted": bool(row) and "P36.72b-promote" not in leg_ids,
        "p36_72b_row_present": bool(row),
        "queued_p36_72b_legs": sorted(x for x in leg_ids if x),
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
        "window": "after P36.72 promotion",
        "suppression_note": (
            "the sweep's recorded window is `after P36.72 promotion`, "
            "verbatim; it re-runs at the ticket's verbatim prompt. "
            "Suppressed is not a pass: the live verdict stays queued; this "
            "record exists so the acceptance note cites its own "
            "suppression."
        ),
    }


# ---------------------------------------------------------------------------
# The 11C legs — every leg reports honestly; a skipped leg is "skipped"
# with a reason, never a fabricated pass.
# ---------------------------------------------------------------------------


def advertised_routes_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Every advertised route answers its declared status — the surface's
    own route set (the emitted route manifest / sitemap, caller-supplied)."""
    fetch = fetcher or a11b._fetch_text
    if not routes:
        return {
            "verdict": "skipped",
            "reason": "no advertised-route set supplied (the promoted "
            "surface's route manifest is caller-supplied)",
        }
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url, expect = rt["url"], int(rt.get("expect", 200))
        status, _body = fetch(url)
        detail.append({"url": url, "expect": expect, "status": status})
        if status is None:
            unreachable += 1
        elif status != expect:
            failed += 1
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "routes": len(routes),
        "resolved": sum(1 for d in detail if d["status"] == d["expect"]),
        "unreachable": unreachable,
        "route_detail": detail[:80],
    }


def budget_leg(
    entries: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Wire-measured bytes per route vs the caller's per-route ceiling —
    the ADR-155 page-type budgets read on the wire, never asserted. A
    measured overage is a finding (bounded + loud), never a smoothed pass."""
    fetch = fetcher or a11b._fetch_bytes_ranged
    if not entries:
        return {
            "verdict": "skipped",
            "reason": "no budget routes supplied — the per-route ceilings "
            "come from the emitted page-budgets manifest",
        }
    detail: list[dict[str, Any]] = []
    unreachable = 0
    over = 0
    for e in entries:
        url = e["url"]
        ceiling = int(e["ceiling_bytes"])
        status, data = fetch(url)
        measured = len(data) if isinstance(data, bytes) else None
        ok = status in (200, 206) and measured is not None and measured <= ceiling
        detail.append(
            {
                "url": url,
                "status": status,
                "measured_bytes": measured,
                "ceiling_bytes": ceiling,
                "within": ok if measured is not None else None,
            }
        )
        if status is None:
            unreachable += 1
        elif not ok:
            over += 1
    verdict = "fail" if over else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "routes": len(entries),
        "over_ceiling": over,
        "unreachable": unreachable,
        "route_detail": detail[:80],
    }


def labels_leg(
    urls: Sequence[str],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """0 bare-UUID labels on the supplied pages + the pinned-release marker
    the release pages carry — 'labels read what they claim' (SIG-CONF-005;
    counts are DOM-heuristic, reported verbatim)."""
    fetch = fetcher or a11b._fetch_text
    if not urls:
        return {"verdict": "skipped", "reason": "no label-check pages supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    bad = 0
    for url in urls:
        status, body = fetch(url)
        entry: dict[str, Any] = {"url": url, "status": status}
        if status != 200 or body is None:
            unreachable += 1
            detail.append(entry)
            continue
        text_nodes = " ".join(a11b._TEXT_NODE.findall(body))
        entry["uuid_only_labels"] = len(a11b.UUID_ONLY.findall(text_nodes))
        entry["release_pinned"] = any(m.search(body) for m in a11b.PIN_MARKERS)
        if entry["uuid_only_labels"] or not entry["release_pinned"]:
            bad += 1
        detail.append(entry)
    verdict = "fail" if bad else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "pages": len(urls),
        "uuid_only_labels": sum(d.get("uuid_only_labels", 0) for d in detail),
        "unpinned": sum(1 for d in detail if d.get("release_pinned") is False),
        "unreachable": unreachable,
        "page_detail": detail[:40],
    }


def changelog_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """The changelog serves — the supplied changelog routes answer 200 and
    carry their declared markers (e.g. a release id / version token)."""
    fetch = fetcher or a11b._fetch_text
    if not routes:
        return {"verdict": "skipped", "reason": "no changelog routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url, required = rt["url"], list(rt.get("required", []))
        status, body = fetch(url)
        entry: dict[str, Any] = {"url": url, "status": status}
        if status != 200 or body is None:
            unreachable += 1
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


def mirrors_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Each supplied mirror endpoint serves — ``versions.json`` and the
    content-addressed objects — with a sha256 binding when the caller
    supplies one (digest-verified, never asserted)."""
    fetch = fetcher or a11b._fetch_bytes_ranged
    if not routes:
        return {
            "verdict": "skipped",
            "reason": "no mirror endpoints supplied — the mirror leg "
            "D-P36.68-1 stays queued, so this set is empty by default",
        }
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url = rt["url"]
        want = str(rt.get("sha256", "")).lower()
        status, data = fetch(url)
        entry: dict[str, Any] = {"url": url, "status": status}
        if status not in (200, 206) or data is None:
            unreachable += 1
        elif want:
            got = hashlib.sha256(data).hexdigest()
            entry["sha256"] = got
            entry["digest_match"] = got == want
            if not entry["digest_match"]:
                failed += 1
        detail.append(entry)
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "endpoints": len(routes),
        "digest_checked": sum(1 for d in detail if "digest_match" in d),
        "unreachable": unreachable,
        "endpoint_detail": detail[:40],
    }


def search_resolve_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Search resolves — each supplied query route's JSON answers with at
    least its declared minimum rows (the §4.3 exit-4 shape; the caller's
    jurisdiction/city/vendor/agency query set — measured, never asserted)."""
    fetch = fetcher or a11b._fetch_text
    if not routes:
        return {"verdict": "skipped", "reason": "no search-resolve routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    failed = 0
    for rt in routes:
        url = rt["url"]
        minimum = int(rt.get("min_results", 1))
        status, body = fetch(url)
        entry: dict[str, Any] = {"url": url, "status": status, "min_results": minimum}
        if status != 200 or body is None:
            unreachable += 1
        else:
            try:
                rows = len(json.loads(body).get("results", []))
            except (ValueError, AttributeError):
                rows = 0
            entry["rows"] = rows
            if rows < minimum:
                failed += 1
        detail.append(entry)
    verdict = "fail" if failed else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "queries": len(routes),
        "resolved": sum(1 for d in detail if d.get("rows", 0) >= d["min_results"]),
        "unreachable": unreachable,
        "query_detail": detail[:80],
    }


def ratelimit_leg(
    routes: Sequence[dict[str, Any]],
    *,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Rate limits enforced — a recognised rate-limit header present on
    each supplied API route's ordinary response (the enforcement signal a
    read-only sweep can honestly record; a 429 is measured if the route
    answers one, never provoked)."""
    fetch = fetcher or _fetch_headers
    if not routes:
        return {"verdict": "skipped", "reason": "no rate-limit routes supplied"}
    detail: list[dict[str, Any]] = []
    unreachable = 0
    missing = 0
    for rt in routes:
        url = rt["url"] if isinstance(rt, dict) else str(rt)
        wanted = (
            list(rt.get("headers", RATE_HEADERS)) if isinstance(rt, dict) else list(RATE_HEADERS)
        )
        status, headers = fetch(url)
        present = sorted(h for h in wanted if h in headers)
        entry: dict[str, Any] = {
            "url": url,
            "status": status,
            "rate_headers_present": present,
        }
        if status is None:
            unreachable += 1
        elif not present:
            missing += 1
        detail.append(entry)
    verdict = "fail" if missing else ("partial" if unreachable else "pass")
    return {
        "verdict": verdict,
        "routes": len(routes),
        "with_headers": sum(1 for d in detail if d["rate_headers_present"]),
        "unreachable": unreachable,
        "route_detail": detail[:40],
    }


def run_sweep(
    *,
    routes: dict[str, Any],
    reads: dict[str, Any] | None = None,
    now: str | None = None,
    fetch_text: Callable[..., Any] | None = None,
    fetch_bytes: Callable[..., Any] | None = None,
    fetch_headers: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the live sweep and build the ``sig.probe-run/1`` record.

    Only called once the gate says ``run`` — the gate itself is evaluated
    by ``evaluate_gate`` and the CLI refuses (exit 42) before this runs.
    """
    checks: dict[str, Any] = {
        "release_routes": a11b.release_routes_leg(
            list(routes.get("release_routes") or []), fetcher=fetch_text
        ),
        "advertised_routes": advertised_routes_leg(
            list(routes.get("advertised_routes") or []), fetcher=fetch_text
        ),
        "budgets": budget_leg(list(routes.get("budget_routes") or []), fetcher=fetch_bytes),
        "labels": labels_leg(list(routes.get("label_pages") or []), fetcher=fetch_text),
        "changelog": changelog_leg(list(routes.get("changelog_routes") or []), fetcher=fetch_text),
        "mirrors": mirrors_leg(list(routes.get("mirror_urls") or []), fetcher=fetch_bytes),
        "release_search": a11b.release_search_leg(
            list(routes.get("release_search") or []), fetcher=fetch_text
        ),
        "search_resolve": search_resolve_leg(
            list(routes.get("search_resolve") or []), fetcher=fetch_text
        ),
        "rate_limit": ratelimit_leg(
            list(routes.get("ratelimit_routes") or []), fetcher=fetch_headers
        ),
        "withdrawal": a11b.withdrawal_leg(
            list(routes.get("withdrawal_aliases") or []), fetcher=fetch_text
        ),
        "dossiers": a11b.dossier_leg(list(routes.get("dossier_routes") or []), fetcher=fetch_text),
        "network": a11b.network_leg(routes.get("network_url"), fetcher=fetch_text),
        "tiles": a11b.tiles_leg(list(routes.get("tile_urls") or []), fetcher=fetch_bytes),
        "parity": a11b.parity_leg(list(routes.get("parity_pairs") or []), fetcher=fetch_text),
        "disclosures": a11b.disclosure_leg(
            list(routes.get("disclosures") or []), fetcher=fetch_text
        ),
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
            "budgets are wire-measured bytes against caller ceilings; the "
            "label counts are DOM-heuristic and reported verbatim"
        ),
    }


# ---------------------------------------------------------------------------
# The routes spec — a committed-style JSON the leg caller builds from the
# promoted release's own route manifest; individual options append.
# ---------------------------------------------------------------------------


def _parse_routes(args: argparse.Namespace) -> dict[str, Any]:
    routes: dict[str, Any] = {
        "release_routes": [],
        "advertised_routes": [],
        "budget_routes": [],
        "label_pages": [],
        "changelog_routes": [],
        "mirror_urls": [],
        "release_search": [],
        "search_resolve": [],
        "ratelimit_routes": [],
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
            raise Acceptance11CError(f"--routes-file unreadable: {exc}") from exc
        if not isinstance(spec, dict):
            raise Acceptance11CError("--routes-file must be a JSON object")
        for k, v in spec.items():
            routes[k] = v
    base = (args.site_base or "").rstrip("/")

    def _abs(u: str) -> str:
        return u if u.startswith(("http://", "https://")) else base + u

    routes["release_routes"] += [_abs(u) for u in args.release_url]
    routes["advertised_routes"] += [{"url": _abs(u), "expect": 200} for u in args.route]
    for b in args.budget:
        url, sep, ceiling = b.partition(":")
        if not sep or not url or not ceiling.isdigit():
            raise Acceptance11CError(f"--budget needs URL:CEILING_BYTES — got {b!r}")
        routes["budget_routes"].append({"url": _abs(url), "ceiling_bytes": int(ceiling)})
    routes["label_pages"] += [_abs(u) for u in args.label_page]
    routes["changelog_routes"] += [{"url": _abs(u), "required": []} for u in args.changelog_url]
    for m in args.mirror_url:
        url, sep, sha = m.partition("=")
        entry: dict[str, Any] = {"url": url}
        if sep and sha:
            entry["sha256"] = sha
        routes["mirror_urls"].append(entry)
    routes["release_search"] += [{"url": _abs(u), "expect": 200} for u in args.search_url]
    for q in args.search_resolve:
        url, sep, minimum = q.partition(":")
        if not sep or not minimum.isdigit():
            raise Acceptance11CError(f"--search-resolve needs URL:MIN_RESULTS — got {q!r}")
        routes["search_resolve"].append({"url": _abs(url), "min_results": int(minimum)})
    routes["ratelimit_routes"] += [_abs(u) for u in args.ratelimit_url]
    routes["withdrawal_aliases"] += [_abs(u) for u in args.withdrawal_alias]
    for d in args.dossier:
        level, sep, url = d.partition(":")
        if not sep or not level or not url:
            raise Acceptance11CError(f"--dossier needs LEVEL:URL — got {d!r}")
        routes["dossier_routes"].append({"level": level, "url": _abs(url)})
    if args.network_url:
        routes["network_url"] = _abs(args.network_url)
    routes["tile_urls"] += list(args.tile_url)
    for p in args.parity:
        a, sep, w = p.partition("|")
        if not sep:
            raise Acceptance11CError(f"--parity needs API_URL|WEB_URL — got {p!r}")
        routes["parity_pairs"].append({"api": a, "web": w})
    for d in args.disclosure:
        url, sep, phrases = d.partition("=")
        if not sep:
            raise Acceptance11CError(f"--disclosure needs URL=PHRASE[,PHRASE] — got {d!r}")
        routes["disclosures"].append(
            {"url": _abs(url), "required": [x for x in phrases.split(",") if x]}
        )
    return {k: v for k, v in routes.items() if v}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sig-ops acceptance-sweep-11c",
        description=(
            "P36.73 — the 11C live-read acceptance sweep → sig.probe-run/1. "
            "Gated: refuses (exit 42, suppressed record) until the promoted "
            "core-surfaces release exists (P36.72b's promote leg out of the "
            "RETURN PASS queue). --check evaluates the gate only."
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
    ap.add_argument("--route", action="append", default=[], help="an advertised route (expect 200)")
    ap.add_argument(
        "--budget",
        action="append",
        default=[],
        help="URL:CEILING_BYTES — a wire-measured budget route",
    )
    ap.add_argument("--label-page", action="append", default=[], help="a label-check page")
    ap.add_argument("--changelog-url", action="append", default=[], help="a changelog route")
    ap.add_argument(
        "--mirror-url",
        action="append",
        default=[],
        help="a mirror endpoint (URL or URL=SHA256 for a digest binding)",
    )
    ap.add_argument("--search-url", action="append", default=[], help="a release-search route")
    ap.add_argument(
        "--search-resolve",
        action="append",
        default=[],
        help="URL:MIN_RESULTS — a search query that must resolve ≥ N rows",
    )
    ap.add_argument(
        "--ratelimit-url",
        action="append",
        default=[],
        help="an API route checked for rate-limit headers",
    )
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
            inputs = a11b.load_inputs(args.inputs)
        else:
            inputs = map_derived_inputs(Path(args.map_path), now=args.at)
        if args.at:
            inputs["now"] = args.at
        inputs["routes"] = _parse_routes(args)
        gate = evaluate_gate(inputs)
        reads = a11b.load_inputs(args.reads_file) if args.reads_file else None
    except (Acceptance11CError, a11b.Acceptance11BError) as exc:
        print(f"sig-ops acceptance-sweep-11c: REFUSED — {exc}", file=sys.stderr)
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
                    f"sig-ops acceptance-sweep-11c: suppressed probe-run -> {args.record_out}",
                    file=sys.stderr,
                )
            print(
                "sig-ops acceptance-sweep-11c: QUEUED — the leg refuses; exit 42 "
                "(re-run prompt in the record).",
                file=sys.stderr,
            )
            return 42
        print(
            "sig-ops acceptance-sweep-11c: gate green — the sweep may run.",
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
                f"sig-ops acceptance-sweep-11c: suppressed probe-run -> {args.record_out}",
                file=sys.stderr,
            )
        print(
            "sig-ops acceptance-sweep-11c: QUEUED — the leg refuses; exit 42.",
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
        print(f"sig-ops acceptance-sweep-11c: record -> {args.record_out}", file=sys.stderr)
    print(f"sig-ops acceptance-sweep-11c: overall={record['overall']}", file=sys.stderr)
    return 0 if record["overall"] == "pass" else (1 if record["overall"] == "fail" else 3)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
