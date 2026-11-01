# SPDX-License-Identifier: Apache-2.0
"""P36.75 (R11-ACQ-30) — the Flock share-list §43.2a screen + claim builder.

The catalog AC verbatim: an edge carrying an operator id / search reason /
audit row is dropped by the screen (whole-fieldset, A-22); an
organisation-level claim is emitted; **0 person-level or audit-row fields on
any claim**. Zero network, zero DSN — the write path is tests/db's.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connectors.flock_share_lists import (
    CLAIM_FIELDS,
    PROBE_SOURCE_ID,
    build_share_claims,
    page_record_portal,
    screen_share_fieldset,
    screen_vocab,
    snapshot_portals,
)

FIXTURES = Path(__file__).parent / "fixtures" / "flock_share_lists"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_vocab_is_committed_and_schema_bound():
    table = screen_vocab()
    assert table["schema"] == "sig.flock-share-screen/1"
    assert {c["class_id"] for c in table["classes"]} >= {
        "P8-OPERATOR-IDS",
        "P8-SEARCH-REASONS",
        "P8-AUDIT-ROWS",
        "P8-PERSON-MATERIAL",
        "P8-UNREVIEWED-ROWS",
    }


def test_clean_portal_passes_the_screen():
    portal = _load("snapshot_clean.json")["portals"][0]
    assert not screen_share_fieldset(portal).refused


@pytest.mark.parametrize(
    ("slug", "cls"),
    [
        ("reasons-pd", "P8-SEARCH-REASONS"),
        ("audit-pd", "P8-AUDIT-ROWS"),
        ("operator-pd", "P8-OPERATOR-IDS"),
        ("badentry-pd", "P8-NON-SLUG-ENTRY"),
    ],
)
def test_seeded_material_refuses_whole_fieldset(slug: str, cls: str):
    portals = {p["slug"]: p for p in _load("snapshot_seeded.json")["portals"]}
    verdict = screen_share_fieldset(portals[slug])
    assert verdict.refused
    assert cls in verdict.hits


def test_config_flags_never_hit():
    """`public_search_audit: true` / `total_searches: N` are config, never rows."""
    portal = _load("snapshot_clean.json")["portals"][0]
    assert not screen_share_fieldset(portal).refused


def test_builder_emits_org_level_claims_only():
    build = build_share_claims(snapshot_portals(_load("snapshot_clean.json")))
    assert build.claims
    for claim in build.claims:
        assert claim["record_kind"] == "claim"
        assert claim["predicate_id"] == "configured_sharing_partner"
        assert claim["access_kind"] == "configured_access"
        assert claim["subject_id"].startswith("flock_portal:")
        assert claim["object_ref"]["value"].startswith("flock_portal:")
        assert set(claim) <= CLAIM_FIELDS  # 0 person-level / audit-row fields
        assert claim["license"] == "CC-BY-SA-4.0"
        assert claim["compartment"] == "portal"
        assert claim["ai_training_permitted"] is False


def test_builder_drops_refused_portals_entirely():
    build = build_share_claims(snapshot_portals(_load("snapshot_seeded.json")))
    refused_slugs = {r["slug"] for r in build.refused}
    assert refused_slugs == {"reasons-pd", "audit-pd", "operator-pd", "badentry-pd"}
    assert not any(c["subject_id"] == "flock_portal:reasons-pd" for c in build.claims)


def test_claims_digest_identically_to_connector_emit():
    """The builder's shape == the connector's — the write dedupes to +0."""
    from connectors.flock_portal import _portal_partner_ref, _sharing_edge_rows
    from reconcile.sharing import reconcile_sharing

    portals = snapshot_portals(_load("snapshot_clean.json"))
    built = build_share_claims(portals)
    probe_rows = _sharing_edge_rows(reconcile_sharing([]), attribution="")
    assert isinstance(probe_rows, list)
    for claim in built.claims:
        ref = _portal_partner_ref(str(claim["to_org"]))
        assert claim["object_ref"] == ref


def test_page_record_portal_requires_the_page_schema():
    doc = _load("portal_page_served.json")
    portal = page_record_portal(doc)
    assert portal["slug"] == "sunnydale-pd"
    with pytest.raises(ValueError):
        page_record_portal({"schema": "other"})


def test_probe_extraction_claims_stamp_the_probe_source():
    build = build_share_claims(
        [page_record_portal(_load("portal_page_served.json"))],
        source_id=PROBE_SOURCE_ID,
    )
    assert all(c["source_id"] == PROBE_SOURCE_ID for c in build.claims)


def test_feed_is_deterministic_state_matrix():
    build = build_share_claims(snapshot_portals(_load("snapshot_clean.json")))
    feed = build.feed
    assert feed["schema"] == "sig.flock-share-feed/1"
    assert feed["cells"] == sorted(feed["cells"], key=lambda c: (c["from_state"], c["to_state"]))
    assert feed["digest"]
    again = build_share_claims(snapshot_portals(_load("snapshot_clean.json")))
    assert again.feed["digest"] == feed["digest"]
    assert again.claim_set_digest == build.claim_set_digest


def test_cli_requires_inputs(tmp_path, capsys):
    from connectors.cli import main

    assert main(["flock-share-lists", "--dsn", "postgresql://x/y"]) == 2
    assert "at least one" in capsys.readouterr().out


def test_cli_rejects_a_bad_snapshot(tmp_path, capsys):
    from connectors.cli import main

    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert (
        main(
            [
                "flock-share-lists",
                "--snapshot",
                str(bad),
                "--dsn",
                "postgresql://x/y",
            ]
        )
        == 2
    )
    assert "input refused" in capsys.readouterr().out
