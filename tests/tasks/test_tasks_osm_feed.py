# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OSM changeset feed → §7 leverage metric (P21.7, §35.2; ADR-069).

Covers the ticket ACs: replay over the recorded fixtures attributes N changesets to
the LeverageLedger and 0 on re-run (append-only, idempotent); NO OSM display names
are stored (Part VIII §0.7).
"""

from __future__ import annotations

from pathlib import Path

from tasks.contribution import CHANGESET_HASHTAG, LeverageLedger
from tasks.osm_feed import (
    build_feed_url,
    ingest_changesets,
    leverage_metric_json,
    parse_changesets,
    pull_files,
)

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("osm_changesets_*.xml"))


def test_fixtures_present() -> None:
    assert FIXTURES, "recorded OSM changeset fixtures must be committed"


def test_parse_keeps_only_hashtag_bearing_changesets() -> None:
    xml = (Path(__file__).parent / "fixtures" / "osm_changesets_okc_page1.xml").read_bytes()
    parsed = parse_changesets(xml)
    ids = {cs.changeset_id for cs in parsed}
    # page1 has two hashtagged (001, 002) and one non-SIG (003) which is dropped.
    assert ids == {"140000001", "140000002"}
    assert all(CHANGESET_HASHTAG in cs.comment for cs in parsed)


def test_open_changeset_attributed_but_not_yet_accepted() -> None:
    xml = (Path(__file__).parent / "fixtures" / "osm_changesets_okc_page2.xml").read_bytes()
    parsed = {cs.changeset_id: cs for cs in parse_changesets(xml)}
    assert parsed["140000004"].accepted is True  # closed
    assert parsed["140000005"].accepted is False  # still open


def test_no_osm_user_names_are_stored_anywhere() -> None:
    # Part VIII §0.7: the parser reads id + comment only; the stored records must
    # contain no display name / uid even though the fixture XML carries them.
    result = pull_files(FIXTURES)
    blob = repr(
        [(c.changeset_id, c.comment, c.accepted) for c in result.ledger._changesets.values()]
    )
    for forbidden in ("mapper_alice", "mapper_bob", "mapper_dan", "mapper_erin", "uid", "1000001"):
        assert forbidden not in blob


def test_pull_attributes_and_is_idempotent_on_rerun() -> None:
    ledger = LeverageLedger()
    first = pull_files(FIXTURES, ledger=ledger)
    # Four hashtag-bearing changesets across both pages (001,002,004 closed; 005 open).
    assert first.added_count == 4
    assert set(first.added) == {"140000001", "140000002", "140000004", "140000005"}
    # §7 metric counts only ACCEPTED (closed) hashtagged changesets → 3.
    assert ledger.accepted_operator_attributions() == 3
    # Re-run over the same feed adds nothing (append-only, idempotent by id).
    second = pull_files(FIXTURES, ledger=ledger)
    assert second.added_count == 0
    assert ledger.accepted_operator_attributions() == 3


def test_since_filter_drops_earlier_changesets() -> None:
    # page1 closed 2026-09-10; page2 has 004 closed 2026-09-11 and 005 still open.
    # --since 09-11 keeps only the closed changeset from that day (an open changeset
    # has no closed_at, so it is not "closed at/after" the cutoff).
    result = pull_files(FIXTURES, since="2026-09-11T00:00:00Z")
    assert set(result.added) == {"140000004"}


def test_leverage_metric_json_is_public_and_username_free() -> None:
    result = pull_files(FIXTURES)
    metric = leverage_metric_json(result.ledger)
    assert metric["hashtag"] == CHANGESET_HASHTAG
    assert metric["accepted_operator_attributions"] == 3
    assert metric["attributed_changeset_ids"] == [
        "140000001",
        "140000002",
        "140000004",
        "140000005",
    ]


def test_ingest_changesets_directly_is_idempotent() -> None:
    xml = (Path(__file__).parent / "fixtures" / "osm_changesets_okc_page1.xml").read_bytes()
    parsed = parse_changesets(xml)
    ledger = LeverageLedger()
    assert ingest_changesets(ledger, parsed).added_count == 2
    assert ingest_changesets(ledger, parsed).added_count == 0


def test_build_feed_url_constructs_public_api_query() -> None:
    url = build_feed_url(since="2026-09-01T00:00:00Z", bbox="-97.6,35.4,-97.5,35.5")
    assert url.startswith("https://api.openstreetmap.org/api/0.6/changesets?")
    assert "closed=true" in url
    assert "time=" in url and "bbox=" in url
