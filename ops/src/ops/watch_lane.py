# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.33 (K7 WX-03, D-K7-2 [B-22] = the lane) — the watch lane.

The ``sig-watch-publish`` job's deterministic core, mirroring the status
lane (P36.43 / ``status_lane.py``): read the watch producer's ``sig/watch/2``
payload — the publishable-claims derivation ``exports.watch.build_watch_payload``
emits off the read-only export snapshot (K7 §7: "reads only publishable
watch rows through a read-only view") — and emit the lane file set under
``watch/**`` at the **watch clock** (the second clock, W-P6: pages say
"watch checked <time>" apart from "data release <pub>"):

* ``watch/state.json`` — ``sig.watch-heartbeat/1`` (the lane's timestamp +
  item counters; the probe-watched heartbeat),
* ``watch/lane.json`` — ``sig.watch-lane/1``, the lane document the pages
  and probes derive from,
* ``watch/watch.json`` — the input ``sig/watch/2`` payload verbatim (the
  machine-readable twin),
* ``watch/index.html`` — the lane-rendered ``/watch/`` index (upcoming
  decisions + the coverage statement + both clocks),
* ``watch/place/<path>/index.html`` — per-place pages (every coverage row,
  every resolvable item key, the ``unplaced`` bucket — SIG-WATCH-004),
* ``watch/item/<handle>/index.html`` — per-item pages (one alert date with
  kind + certainty — an ``upper_bound`` is never labelled a deadline,
  SIG-WATCH-002 — timeline, evidence, tasks),
* ``watch/archive/<YYYY-MM-DD>.json`` — the append-only daily archive of
  the lane document (never deleted, never overwritten — P1–P3).

The lane emits only the files it OWNS: kind/vendor/technology facet pages,
history pages, pagination, citations and feeds stay the release web build's
(and WX-04b's feed set's) — the publish leg's delete plan is scoped to the
lane-owned path shapes so a daily refresh can never remove a page the lane
does not render. Every emitted file passes the S-1 secret scan and the
zero-JS gate before it is written (SIG-TRANSP-022 — the lane renders
zero-JS only).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from exports.release_pages import DISPUTE_HREF, SITE_NAV
from policy.transparency import find_secrets

# ---------------------------------------------------------------------------
# Schemas + constants
# ---------------------------------------------------------------------------

WATCH_LANE_SCHEMA = "sig.watch-lane/1"
WATCH_HEARTBEAT_SCHEMA = "sig.watch-heartbeat/1"
WATCH_SCHEMA = "sig/watch/2"
WATCH_ITEM_SCHEMA = "sig.watch-item/1"

WATCH_DIR = "watch"
HEARTBEAT_PATH = f"{WATCH_DIR}/state.json"
LANE_DOC_PATH = f"{WATCH_DIR}/lane.json"
PAYLOAD_PATH = f"{WATCH_DIR}/watch.json"
INDEX_PATH = f"{WATCH_DIR}/index.html"
PLACE_PREFIX = f"{WATCH_DIR}/place/"
ITEM_PREFIX = f"{WATCH_DIR}/item/"
ARCHIVE_PREFIX = f"{WATCH_DIR}/archive/"
UNPLACED_PATH = "unplaced"

#: The six §5.2 kinds the v1 producer derives — closed list; a kind outside
#: it is producer/schema drift the lane refuses, never silently renders.
WATCH_KINDS: tuple[str, ...] = (
    "renewal_deadline",
    "contract_expiry",
    "solicitation_deadline",
    "agenda_item",
    "legislative_action",
    "grant_period_end",
)

_KIND_LABELS: dict[str, str] = {
    "renewal_deadline": "Renewal decision",
    "contract_expiry": "Contract expiry",
    "solicitation_deadline": "Solicitation deadline",
    "agenda_item": "Agenda item",
    "legislative_action": "Legislative action",
    "grant_period_end": "Grant period end",
}

_DATE_KIND_LABELS: dict[str, str] = {
    "notice_deadline": "notice deadline",
    "expiry": "contract expiry date",
    "response_deadline": "response deadline",
    "meeting": "meeting",
    "scheduled_action": "scheduled action",
    "status_change": "status change",
    "period_end": "period end",
}

#: SIG-WATCH-002 — an ``upper_bound`` reads "latest possible date"; the word
#: "deadline" never labels it (the kind word is dropped for an upper_bound
#: row whatever its kind — the same rule ``watch-v2.ts#itemDateLabel``).
_CERTAINTY_LABELS: dict[str, str] = {
    "stated": "stated",
    "derived": "derived",
    "upper_bound": "latest possible date",
}

_STATUSES: tuple[str, ...] = (
    "upcoming",
    "today",
    "recently_decided",
    "superseded",
    "withdrawn",
)
_STATUS_LABELS: dict[str, str] = {
    "upcoming": "upcoming",
    "today": "today",
    "recently_decided": "recently decided",
    "superseded": "date moved",
    "withdrawn": "withdrawn",
}

_NO_UPSTREAM_URL = "no upstream URL on record"
_NOT_PUBLISHABLE = "not publishable under the source's terms"
_NOT_RECORDED = "not recorded"


class WatchLaneError(ValueError):
    """A lane input or the publish set failed its closed contract."""


# ---------------------------------------------------------------------------
# Input parsing (fail-closed — never coerce)
# ---------------------------------------------------------------------------


def _dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_lane_time(value: str | datetime) -> datetime:
    d = _dt(value)
    if d is None:
        raise WatchLaneError(f"unparseable lane time {value!r} — ISO-8601 UTC required")
    return d.astimezone(UTC)


def _check_item(item: Any, where: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise WatchLaneError(f"{where}: item is not an object")
    if item.get("schema") not in (None, WATCH_ITEM_SCHEMA):
        raise WatchLaneError(f"{where}: not a {WATCH_ITEM_SCHEMA} item")
    for field in ("handle", "title", "kind", "date"):
        if not isinstance(item.get(field), str) or not item.get(field):
            raise WatchLaneError(f"{where}: item is missing {field}")
    if item["kind"] not in WATCH_KINDS:
        raise WatchLaneError(f"{where}: unknown watch kind {item['kind']!r}")
    certainty = item.get("date_certainty") or "stated"
    if certainty not in _CERTAINTY_LABELS:
        raise WatchLaneError(f"{where}: unknown date_certainty {certainty!r}")
    status = item.get("status")
    if status is not None and status not in _STATUSES:
        raise WatchLaneError(f"{where}: unknown status {status!r}")
    if _dt(item["date"]) is None:
        raise WatchLaneError(f"{where}: unparseable item date {item['date']!r}")
    return dict(item)


def load_watch_payload(path: str | Path) -> dict[str, Any]:
    """Parse a ``sig/watch/2`` payload file — fail-closed on schema drift."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return check_watch_payload(doc)


def check_watch_payload(doc: Any) -> dict[str, Any]:
    """Validate the ``sig/watch/2`` envelope + its ``sig.watch-item/1`` rows."""
    if not isinstance(doc, Mapping) or doc.get("schema") != WATCH_SCHEMA:
        raise WatchLaneError(f"not a {WATCH_SCHEMA} document")
    items = doc.get("items")
    if not isinstance(items, list):
        raise WatchLaneError("watch payload items is not a list")
    seen: set[str] = set()
    checked = []
    for i, raw in enumerate(items):
        item = _check_item(raw, f"items[{i}]")
        if item["handle"] in seen:
            raise WatchLaneError(f"items[{i}]: duplicate handle {item['handle']!r}")
        seen.add(item["handle"])
        checked.append(item)
    out = dict(doc)
    out["items"] = checked
    return out


# ---------------------------------------------------------------------------
# The lane document
# ---------------------------------------------------------------------------


def _by_key(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for i in items:
        k = str(i.get(field) or "not_recorded")
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items()))


def _item_index(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i in items:
        place = i.get("place") or {}
        out.append(
            {
                "handle": i["handle"],
                "date": i["date"],
                "kind": i["kind"],
                "status": i.get("status") or "upcoming",
                "date_certainty": i.get("date_certainty") or "stated",
                "place_key": place.get("key"),
                "contested": bool(i.get("contested")),
            }
        )
    out.sort(key=lambda r: (r["date"], r["handle"]))
    return out


def _place_pages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The emitted place-page set (SIG-WATCH-004 — the same rule
    ``watch-v2.ts#placePages`` applies): every coverage row, every item key
    the coverage slugs resolve, and the ``unplaced`` bucket."""
    coverage = payload.get("coverage") or {}
    pages: dict[str, dict[str, Any]] = {}
    key_to_slug: dict[str, str] = {}
    for row in coverage.get("places") or []:
        key, slug = str(row.get("key") or ""), str(row.get("slug") or "")
        if not key or not slug:
            continue
        key_to_slug[key] = slug
        pages[slug] = {"key": key, "path": slug, "coverage": dict(row), "unplaced": False}
    item_keys: set[str] = set()
    items = payload.get("items") or []
    for item in items:
        place = item.get("place") or {}
        for k in [place.get("key"), *(place.get("chain") or [])]:
            if k:
                item_keys.add(str(k))
    for key in sorted(item_keys):
        item_slug = key_to_slug.get(key)
        if item_slug and item_slug not in pages:
            pages[item_slug] = {
                "key": key,
                "path": item_slug,
                "coverage": None,
                "unplaced": False,
            }
    out = sorted(pages.values(), key=lambda p: str(p["path"]))
    if any(not (i.get("place") or {}).get("key") for i in items) or not out:
        out.append({"key": None, "path": UNPLACED_PATH, "coverage": None, "unplaced": True})
    return out


def _items_for_place(items: list[dict[str, Any]], key: str | None) -> list[dict[str, Any]]:
    """Place + registry children (K7 §5.4 — chain membership); ``None`` is the
    unplaced bucket."""
    if key is None:
        rows = [i for i in items if not (i.get("place") or {}).get("key")]
    else:
        rows = [
            i
            for i in items
            if (i.get("place") or {}).get("key") == key
            or key in ((i.get("place") or {}).get("chain") or [])
        ]
    return sorted(rows, key=lambda i: (i["date"], i["handle"]))


def build_watch_lane(
    *,
    payload: Mapping[str, Any],
    release: Mapping[str, Any] | None = None,
    lane_time: datetime,
) -> dict[str, Any]:
    """Build the ``sig.watch-lane/1`` document at the lane's own clock.

    Deterministic: same inputs → the same document. ``lane_time`` is the
    watch clock — labelled "watch checked" everywhere the release's
    ``as_of``/``generated_at`` rides beside it (W-P6, never silently).
    """
    lane_time = lane_time.astimezone(UTC)
    items = list(payload.get("items") or [])
    coverage = payload.get("coverage") or {}
    monitored = coverage.get("monitored") or {}
    places = _place_pages(payload)
    return {
        "schema": WATCH_LANE_SCHEMA,
        "lane_time": _iso(lane_time),
        "release": (
            {
                "id": str(release.get("id") or release.get("publication_id") or ""),
                "as_of_world": str(release.get("as_of_world") or ""),
            }
            if release
            else None
        ),
        "payload": {
            "as_of": str(payload.get("as_of") or ""),
            "generated_at": str(payload.get("generated_at") or ""),
            "ruleset": str((payload.get("build") or {}).get("ruleset") or ""),
        },
        "counts": {
            "items_total": len(items),
            "by_kind": _by_key(items, "kind"),
            "by_status": _by_key(items, "status"),
            "places_with_items": sum(
                1 for r in coverage.get("places") or [] if int(r.get("items") or 0) > 0
            ),
            "places_pages": len(places),
        },
        "monitored": {
            "tenants_registered": int(monitored.get("tenants_registered") or 0),
            "tenant_jurisdictions": sorted(
                {str(t) for t in monitored.get("tenant_jurisdictions") or []}
            ),
        },
        "last_checked": str(coverage.get("last_checked") or ""),
        "items_index": _item_index(items),
    }


def watch_heartbeat_doc(lane: Mapping[str, Any]) -> dict[str, Any]:
    """``sig.watch-heartbeat/1`` — ``watch/state.json`` (the OSM state.txt
    pattern: the lane's timestamp + the counters a probe can watch)."""
    return {
        "schema": WATCH_HEARTBEAT_SCHEMA,
        "lane_time": lane["lane_time"],
        "payload_generated_at": lane["payload"]["generated_at"],
        "items_total": lane["counts"]["items_total"],
        "places_pages": lane["counts"]["places_pages"],
        "tenants_registered": lane["monitored"]["tenants_registered"],
        "release": lane.get("release"),
    }


# ---------------------------------------------------------------------------
# Zero-JS HTML emitters (the status lane's chrome contract — no <script>)
# ---------------------------------------------------------------------------


def _e(v: Any) -> str:
    return escape("" if v is None else str(v), quote=True)


def _layout(title: str, body: str) -> str:
    nav = "".join(f'<a href="{_e(href)}">{_e(label)}</a>' for label, href in SITE_NAV)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{_e(title)} — SIG watch</title>\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "</head>\n<body>\n"
        f'<nav aria-label="Site">{nav}</nav>\n<main>\n{body}\n</main>\n'
        f'<footer><a href="{_e(DISPUTE_HREF)}">Corrections and disputes</a></footer>\n'
        "</body>\n</html>\n"
    )


def _date_label(item: Mapping[str, Any]) -> str:
    """The one alert date's rendered label — an ``upper_bound`` NEVER sits
    beside the word "deadline" (SIG-WATCH-002)."""
    certainty = str(item.get("date_certainty") or "stated")
    kind_label = (
        "expiry"
        if certainty == "upper_bound"
        else _DATE_KIND_LABELS.get(
            str(item.get("date_kind") or ""), str(item.get("date_kind") or "date")
        )
    )
    return f"{_e(item['date'])} ({_e(kind_label)} · {_e(_CERTAINTY_LABELS[certainty])})"


def _status_label(item: Mapping[str, Any]) -> str:
    return _STATUS_LABELS.get(str(item.get("status") or "upcoming"), "upcoming")


def _contested(item: Mapping[str, Any]) -> str:
    return (
        ' <span title="contested — a published disagreement names this item">≠</span>'
        if item.get("contested")
        else ""
    )


def _item_row(item: Mapping[str, Any], place_href: str | None) -> str:
    tech = ", ".join(str(t.get("label") or t.get("id")) for t in item.get("technology") or [])
    vendors = ", ".join(str(v.get("label") or v.get("id")) for v in item.get("vendor") or [])
    place_cell = _NOT_RECORDED
    if place_href:
        place_text = place_href.removeprefix("watch/place/").removesuffix("/")
        place_cell = f'<a href="/{_e(place_href)}">{_e(place_text)}</a>'
    return (
        "<tr>"
        f"<td>{_date_label(item)}<br>{_e(_status_label(item))}{_contested(item)}</td>"
        f"<td>{place_cell}</td>"
        f"<td>{_e(item.get('body') or _NOT_RECORDED)}</td>"
        f'<td><a href="/watch/item/{_e(item["handle"])}/">{_e(item["title"])}</a><br>'
        f"{_e(_KIND_LABELS.get(str(item['kind']), item['kind']))}</td>"
        f"<td>{_e(tech or _NOT_RECORDED)}</td>"
        f"<td>{_e(vendors or _NOT_RECORDED)}</td>"
        f"<td>{_e(len(item.get('evidence') or []))}</td>"
        "</tr>"
    )


def _place_href_for(item: Mapping[str, Any], pages: list[dict[str, Any]]) -> str | None:
    key = (item.get("place") or {}).get("key")
    for p in pages:
        if key is None and p["unplaced"]:
            return f"watch/place/{p['path']}/"
        if key is not None and p["key"] == key:
            return f"watch/place/{p['path']}/"
    for k in reversed((item.get("place") or {}).get("chain") or []):
        for p in pages:
            if p["key"] == k:
                return f"watch/place/{p['path']}/"
    return None


def _coverage_statement(lane: Mapping[str, Any], coverage: Mapping[str, Any] | None) -> str:
    """SIG-WATCH-004 — the monitored-portal statement an empty result MUST
    arrive with (a pipeline gap never reads as a research gap)."""
    monitored = lane["monitored"]
    n = monitored["tenants_registered"]
    checked = lane["lane_time"]
    if coverage is None:
        return (
            f"SIG checks {n} registered agenda/procurement tenants "
            f"(last checked {_e(checked)} — the watch clock). This row is the "
            f"unplaced data-quality bucket: items whose place did not resolve."
        )
    juris = len(monitored["tenant_jurisdictions"])
    return (
        f"SIG checks {n} registered agenda/procurement tenants across "
        f"{juris} jurisdiction(s) (last checked {_e(checked)} — the watch clock). "
        "Decisions in bodies SIG does not check will not appear here."
    )


def watch_index_html(lane: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    """``watch/index.html`` — upcoming decisions at the watch clock."""
    items = list(payload.get("items") or [])
    pages = _place_pages(payload)
    list_days = (payload.get("build") or {}).get("windows", {}).get("list_days") or 90
    rel = lane.get("release") or {}
    by_kind = " · ".join(f"{_e(k)} {_e(v)}" for k, v in lane["counts"]["by_kind"].items()) or "none"
    rows = "".join(_item_row(i, _place_href_for(i, pages)) for i in items)
    table = (
        "<table><thead><tr><th>Date</th><th>Place</th><th>Body</th><th>Decision</th>"
        "<th>Technology</th><th>Vendor</th><th>Evidence</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        if rows
        else "<p>No upcoming decisions found as of the last check.</p>"
    )
    body = f"""
<h1>Upcoming decisions</h1>
<p>Watch checked {_e(lane["lane_time"])} UTC — the watch clock, refreshed between releases;
the published data is release {_e(rel.get("id") or "not_recorded")}
(data as of {_e(rel.get("as_of_world") or lane["payload"]["as_of"] or "not_recorded")}).
The payload's own build stamp is {_e(lane["payload"]["generated_at"] or "not_recorded")}.</p>
<p>{_e(lane["counts"]["items_total"])} tracked item(s) — {by_kind}.
The default list shows the next {_e(list_days)} days; a place page keeps every item it covers.</p>
<h2>Items</h2>
{table}
<h2>Coverage</h2>
<p>{_e(_coverage_statement(lane, None))}</p>
<p>Machine-readable: <a href="/watch/lane.json">lane.json</a>,
<a href="/watch/watch.json">watch.json</a>,
<a href="/watch/state.json">state.json</a> (the heartbeat).</p>
"""
    return _layout("Upcoming decisions", body)


def watch_place_html(
    lane: Mapping[str, Any],
    payload: Mapping[str, Any],
    page: Mapping[str, Any],
) -> str:
    """``watch/place/<path>/index.html`` — the place's items WITH its coverage
    statement (SIG-WATCH-004/D04); an empty result names its cause class
    (SIG-WATCH-010), never a research gap."""
    items = _items_for_place(list(payload.get("items") or []), page["key"])
    pages = _place_pages(payload)
    title = (
        "Not yet placed"
        if page["unplaced"]
        else str((page.get("coverage") or {}).get("key") or page["path"])
    )
    rows = "".join(_item_row(i, _place_href_for(i, pages)) for i in items)
    if rows:
        content = (
            "<table><thead><tr><th>Date</th><th>Place</th><th>Body</th><th>Decision</th>"
            "<th>Technology</th><th>Vendor</th><th>Evidence</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    elif page["unplaced"]:
        content = "<p>No unplaced items as of the last check.</p>"
    elif page["coverage"] is not None and int(page["coverage"].get("items") or 0) == 0:
        content = (
            "<p>No upcoming decisions found for this place as of "
            f"{_e(lane['lane_time'])} — <em>none found</em>: SIG checks the "
            "bodies and portals named below.</p>"
        )
    else:
        content = (
            "<p>SIG does not yet check an agenda or procurement source for this "
            "place — <em>not monitored</em>.</p>"
        )
    body = f"""
<h1>Watch — {_e(title)}</h1>
<p>Watch checked {_e(lane["lane_time"])} UTC — the watch clock, refreshed between
releases; items may cite claims newer than the release.</p>
{content}
<h2>Coverage</h2>
<p>{_e(_coverage_statement(lane, page.get("coverage")))}</p>
<p><a href="/watch/">All upcoming decisions</a></p>
"""
    return _layout(f"Watch — {title}", body)


def _upstream_cell(up: Mapping[str, Any] | None) -> str:
    """The J3 §5.3 publication form — full URL, host + path-hash, withheld,
    or the named absence (never a link under withheld_by_policy)."""
    up = up or {}
    status = str(up.get("status") or "")
    if status == "full_url" and up.get("url"):
        return f'<a href="{_e(up["url"])}">{_e(up["url"])}</a>'
    if status == "host_only" and up.get("host"):
        return f"{_e(up['host'])}#path_sha256:{_e(up.get('path_sha256') or _NOT_RECORDED)}"
    if status == "withheld_by_policy":
        return _e(_NOT_PUBLISHABLE)
    return _e(_NO_UPSTREAM_URL)


def watch_item_html(lane: Mapping[str, Any], item: Mapping[str, Any]) -> str:
    """``watch/item/<handle>/index.html`` — one alert date (kind + certainty),
    timeline, evidence links, tasks and the procedural what-you-can-do."""
    rel = lane.get("release") or {}
    timeline = "".join(
        f"<tr><td>{_e(t.get('date'))}</td><td>{_e(t.get('kind'))}</td>"
        f"<td><code>{_e(t.get('claim_id') or _NOT_RECORDED)}</code></td></tr>"
        for t in item.get("timeline") or []
    )
    evidence = "".join(
        f"<tr><td><code>{_e(e.get('claim_id'))}</code></td>"
        f"<td>{_e(e.get('predicate') or _NOT_RECORDED)}</td>"
        f"<td>{_e(e.get('source_id') or _NOT_RECORDED)}</td>"
        f"<td>{_upstream_cell(e.get('upstream'))}</td></tr>"
        for e in sorted(
            item.get("evidence") or [],
            key=lambda e: (str(e.get("predicate") or ""), str(e.get("claim_id") or "")),
        )
    )
    tasks = "".join(
        f'<li><a href="/task/{_e(t["task_id"])}/"><code>{_e(t["task_id"])}</code></a>'
        f" — {_e(t.get('task_type') or _NOT_RECORDED)} ({_e(t.get('status') or 'open')})</li>"
        for t in item.get("tasks") or []
    )
    tech = ", ".join(str(t.get("label") or t.get("id")) for t in item.get("technology") or [])
    vendors = ", ".join(str(v.get("label") or v.get("id")) for v in item.get("vendor") or [])
    place = item.get("place") or {}
    timeline_table = (
        "<table><thead><tr><th>Date</th><th>Fact</th><th>Claim</th></tr></thead>"
        f"<tbody>{timeline}</tbody></table>"
        if timeline
        else "<p>No other dated facts on record.</p>"
    )
    evidence_table = (
        "<table><thead><tr><th>Claim</th><th>Predicate</th><th>Source</th>"
        f"<th>Upstream</th></tr></thead><tbody>{evidence}</tbody></table>"
        if evidence
        else "<p>No evidence links on record.</p>"
    )
    upper_note = (
        "<p><strong>Latest possible date — the real deadline may be earlier.</strong> "
        "The stated end is on record; the renewal terms are not, so the actual "
        "decision may come sooner.</p>"
        if item.get("date_certainty") == "upper_bound"
        else ""
    )
    body = f"""
<h1>{_e(item["title"])}</h1>
<p><code>{_e(item["handle"])}</code>{_contested(item)}</p>
<p>Watch checked {_e(lane["lane_time"])} UTC — the watch clock; the published
data is release {_e(rel.get("id") or "not_recorded")}.</p>
<h2>The decision</h2>
<table>
<tr><th>Alert date</th><td>{_date_label(item)}</td></tr>
<tr><th>Kind</th><td>{_e(_KIND_LABELS.get(str(item["kind"]), item["kind"]))}</td></tr>
<tr><th>Status</th><td>{_e(_status_label(item))}</td></tr>
<tr><th>Body</th><td>{_e(item.get("body") or _NOT_RECORDED)}</td></tr>
<tr><th>Place</th><td>{_e(place.get("key") or "not yet placed")}</td></tr>
<tr><th>Technology</th><td>{_e(tech or _NOT_RECORDED)}</td></tr>
<tr><th>Vendor</th><td>{_e(vendors or _NOT_RECORDED)}</td></tr>
<tr><th>First seen</th><td>{_e(item.get("first_seen") or _NOT_RECORDED)}</td></tr>
<tr><th>Last checked</th><td>{_e(item.get("last_checked") or _NOT_RECORDED)}</td></tr>
</table>
{upper_note}
<h2>What you can do</h2>
<p>{_e(item.get("what_you_can_do") or _NOT_RECORDED)}</p>
<h2>Timeline</h2>
{timeline_table}
<h2>Evidence</h2>
{evidence_table}
{f"<h2>Open research tasks</h2><ul>{tasks}</ul>" if tasks else ""}
<p><a href="/watch/">All upcoming decisions</a></p>
"""
    return _layout(str(item["title"]), body)


# ---------------------------------------------------------------------------
# The emit — file set + scrub gate
# ---------------------------------------------------------------------------


def _check_publish_set(files: Mapping[str, str]) -> None:
    """The S-1 secret gate + zero-JS guard over the lane's file set — a
    secret-shaped value or a ``<script>`` anywhere aborts the emit."""
    for rel, text in files.items():
        findings = find_secrets(text)
        if findings:
            kinds = ", ".join(sorted({f.pattern_class for f in findings}))
            raise WatchLaneError(
                f"lane emit refused — secret-shaped value in {rel} ({kinds}); "
                "the publish set aborts (S-1)"
            )
        if rel.endswith(".html") and "<script" in text.lower():
            raise WatchLaneError(f"lane emit refused — <script> in {rel}; the lane is zero-JS")


def emit_watch_files(
    payload: Mapping[str, Any],
    lane: Mapping[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    """Write the ``watch/**`` lane file set under ``out_dir``.

    Returns the repo-relative → absolute path map. The archive object is
    append-only: a same-day re-emit must be byte-identical and a drifted
    one refuses (P1–P3), exactly like the status lane's archive rule.
    """
    out = Path(out_dir)
    lane_text = json.dumps(lane, indent=2, sort_keys=True) + "\n"
    payload_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    files: dict[str, str] = {
        LANE_DOC_PATH: lane_text,
        HEARTBEAT_PATH: json.dumps(watch_heartbeat_doc(lane), indent=2, sort_keys=True) + "\n",
        PAYLOAD_PATH: payload_text,
        INDEX_PATH: watch_index_html(lane, payload),
    }
    day = str(lane["lane_time"])[:10]
    files[f"{ARCHIVE_PREFIX}{day}.json"] = lane_text
    for page in _place_pages(payload):
        files[f"{PLACE_PREFIX}{page['path']}/index.html"] = watch_place_html(lane, payload, page)
    for item in payload.get("items") or []:
        files[f"{ITEM_PREFIX}{item['handle']}/index.html"] = watch_item_html(lane, item)

    _check_publish_set(files)
    written: dict[str, Path] = {}
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith(ARCHIVE_PREFIX) and path.exists():
            if path.read_text(encoding="utf-8") != text:
                raise WatchLaneError(
                    f"archive object {rel} exists with different bytes — the "
                    "archive is append-only; refusing to overwrite"
                )
            continue
        path.write_text(text, encoding="utf-8")
        written[rel] = path
    return written


#: Remote-path shapes the lane OWNS — a ``plan_watch_sync`` delete candidate
#: must match one of these (``watch/archive/**`` is excluded separately).
#: Everything else under ``watch/**`` — kind/vendor/technology facets,
#: history, pagination, per-item ``citations.txt`` and the feed files — is
#: the release web build's (WX-04a) and WX-04b's, never the lane's to remove.
def lane_owns_object(name: str) -> bool:
    if name.startswith(ARCHIVE_PREFIX):
        return False
    if name in {HEARTBEAT_PATH, LANE_DOC_PATH, PAYLOAD_PATH, INDEX_PATH}:
        return True
    if name.startswith(PLACE_PREFIX):
        return True
    if name.startswith(ITEM_PREFIX) and name.endswith("/index.html"):
        return True
    return False
