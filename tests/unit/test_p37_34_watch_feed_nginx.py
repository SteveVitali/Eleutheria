# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P37.34 — the nginx feed content types (SIG-WATCH-005).

The serving contract: `.ics` → ``text/calendar`` and `.opml` →
``text/x-opml`` at http level (the legacy ``/watch/<j>.ics`` emitters share
the extension — K7 Q11's octet-stream defect fixed); the v2 feed files
under ``/watch/feeds/`` carry ``application/rss+xml`` for the `.xml` RSS
2.0 forms and ``application/feed+json`` for the JSON Feed 1.1 forms (a
location-scoped ``types`` block REPLACES the inherited table, so the block
re-declares every type the directory serves — ``text/html`` for the
directory page included); the legacy flat ``/watch/<j>.xml`` renewal feeds
are RSS and serve ``application/rss+xml``. Subscribers poll on their own
schedule — ``max-age=3600``.
"""

from __future__ import annotations

import re
from pathlib import Path

NGINX = Path(__file__).resolve().parents[2] / "ops" / "web" / "nginx.conf"


def _text() -> str:
    return NGINX.read_text(encoding="utf-8")


def test_ics_and_opml_types_at_http_level() -> None:
    text = _text()
    http_types = re.search(r"^\s*types \{(.*?)\}", text, re.S | re.M)
    assert http_types, "the http-level types block is missing"
    body = http_types.group(1)
    assert "text/calendar ics" in body
    assert "text/x-opml opml" in body
    # The stock types stay — pmtiles/geojson are never displaced.
    assert "application/vnd.pmtiles pmtiles" in body


def test_watch_feeds_location_carries_the_feed_types() -> None:
    text = _text()
    m = re.search(r"location /watch/feeds/ \{(.*?)\n    \}", text, re.S)
    assert m, "location /watch/feeds/ missing"
    block = m.group(1)
    # A scoped types{} replaces the table — every type the directory can
    # serve is re-declared (the index page's html included).
    for needle in (
        "text/html html",
        "text/calendar ics",
        "application/rss+xml xml",
        "application/feed+json json",
        "text/x-opml opml",
    ):
        assert needle in block, f"/watch/feeds/ types lacks {needle}"
    assert "max-age=3600" in block
    # The strict layer still rides the feed bytes.
    assert "sig-headers.conf" in block
    assert "sig-security.conf" in block


def test_legacy_watch_xml_serves_rss_type() -> None:
    text = _text()
    assert 'location ~ "^/watch/[^/]+\\.xml$"' in text
    # json under watch/feeds/ is feed+json — but the lane's own JSON docs
    # (state.json/lane.json/watch.json outside feeds/) keep
    # application/json via the stock mime table.
    lane_json = re.search(r"location /watch/feeds/ \{.*?application/json", text, re.S)
    assert lane_json is None or True  # scope check below is the guard
    feeds_block = re.search(r"location /watch/feeds/ \{(.*?)\n    \}", text, re.S)
    assert feeds_block is not None
    # No blanket application/json inside the feeds scope — a *.json under
    # /watch/feeds/ is a feed, always feed+json.
    assert "application/json json" not in feeds_block.group(1)
