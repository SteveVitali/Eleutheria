# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed statute-inventory seed load (P25.7 / D-CCOPS.1-1, SIG-INGEST-049f).

`state_alpr_statute_inventory` is the one national ALPR-statute inventory —
NCSL's state-by-state table, frozen since 2022-02-03 — committed as a one-time
seed, never a feed. ``runner.run_seed`` serves the packaged asset through the
SAME eight-stage pipeline + loader gate as every source (the documented
in-memory permit flip, SIG-INGEST-028); the registry row stays
``ingestion_permitted=false`` and no network is ever opened.

The seed's `as_of` label is first-class data: it rides every claim's evidence
and a dedicated `as_of` claim carries the page's verbatim label.
"""

from __future__ import annotations

import pytest
from connectors.registry import get
from connectors.runner import live_gate_reasons, run_seed
from connectors.seeds import SeedNotRegistered, seed_asset_path, seed_spec
from connectors.stages import ContentDrift, registered_connectors
from connectors.statute_seed import (
    StatuteSeed,
    parse_statute_seed,
)

SOURCE = "state_alpr_statute_inventory"


def _seed_bytes() -> bytes:
    return seed_asset_path(SOURCE).read_bytes()


# --- the strict parser --------------------------------------------------------


def test_parse_statute_seed_committed_asset() -> None:
    seed = parse_statute_seed(_seed_bytes(), source_id=SOURCE)
    assert isinstance(seed, StatuteSeed)
    assert seed.as_of == "2022-02-03"
    assert seed.as_of_label == "Updated February 03, 2022"
    assert seed.state_count == 16
    assert seed.ncsl_table_rows == 17  # the NCSL table's own layout (CA twice)
    assert len(seed.statutes) == 16
    assert sum(len(e.years) for e in seed.statutes) == 21
    california = next(e for e in seed.statutes if e.state == "California")
    assert california.years == (2011, 2015)
    assert len(california.citations) == 2


def test_parse_statute_seed_not_toml_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(b"not toml [[[", source_id=SOURCE)


def test_parse_statute_seed_missing_frozen_flags_drifts() -> None:
    bad = (
        b'as_of = "2022-02-03"\ninventory_url = "https://x/"\n'
        b'[[statutes]]\nstate = "Maine"\nyears_enacted = [2009]\n'
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(bad, source_id=SOURCE)


def test_parse_statute_seed_bad_entry_drifts() -> None:
    bad = (
        b'as_of = "2022-02-03"\nfrozen = true\nnever_a_feed = true\n'
        b'inventory_url = "https://x/"\n[[statutes]]\nstate = "Maine"\nyears_enacted = []\n'
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(bad, source_id=SOURCE)


def test_parse_statute_seed_count_mismatch_drifts() -> None:
    bad = (
        b'as_of = "2022-02-03"\nfrozen = true\nnever_a_feed = true\n'
        b'inventory_url = "https://x/"\nstate_count = 99\n'
        b'[[statutes]]\nstate = "Maine"\nyears_enacted = [2009]\n'
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(bad, source_id=SOURCE)


def test_parse_statute_seed_unknown_entry_key_drifts() -> None:
    bad = (
        b'as_of = "2022-02-03"\nfrozen = true\nnever_a_feed = true\n'
        b'inventory_url = "https://x/"\n'
        b'[[statutes]]\nstate = "Maine"\nyears_enacted = [2009]\noperator = "x"\n'
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(bad, source_id=SOURCE)


# --- the seed registry + load path --------------------------------------------


def test_seed_spec_is_registered() -> None:
    spec = seed_spec(SOURCE)
    assert spec is not None
    assert spec["asset"] == "state_alpr_statute_seed.toml"
    assert spec["kind"] == "statute_seed"
    assert spec["media_type"] == "application/toml"


def test_seed_connector_is_registered_and_routable() -> None:
    assert "state_statute_seed" in registered_connectors()
    from connectors.runner import CONNECTOR_FOR_SOURCE

    assert CONNECTOR_FOR_SOURCE[SOURCE] == "state_statute_seed"


def test_seed_load_asserts_claims_through_the_gate() -> None:
    """`run_seed` runs the same pipeline + loader gate as every source (P25.7)."""
    report = run_seed(SOURCE, sink_kind="memory")
    assert report.asserted is True
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    # 21 statute-year instruments × their predicate surface + the as_of label.
    instruments = [c for c in claims if c["predicate_id"] == "instrument_type"]
    assert len(instruments) == 21
    assert all(c["value"] == "statute" for c in instruments)

    # Jurisdiction claims carry a us.state CANDIDATE identifier (SIG-INGEST-034).
    jurisdictions = [c for c in claims if c["predicate_id"] == "jurisdiction"]
    assert len(jurisdictions) == 21
    assert all(c["candidate_identifier"]["scheme"] == "us.state" for c in jurisdictions)
    assert {c["value"] for c in jurisdictions} >= {
        "Arkansas",
        "California",
        "Oklahoma",
        "Vermont",
    }

    # Every statute claim constrains ALPR (the inventory's subject).
    tech = [c for c in claims if c["predicate_id"] == "constrains_technology"]
    assert len(tech) == 21 and all(c["value"] == ["alpr"] for c in tech)

    # California's two citations pair positionally with its two statute years.
    citations = [c for c in claims if c["predicate_id"] == "citation"]
    assert {c["value"] for c in citations} == {
        "Veh. Code § 2413",
        "Civ. Code §§ 1798.29, 1798.90.5 (SB 34)",
    }

    # The frozen label travels: one dedicated `as_of` claim carries the page's
    # verbatim label as its raw value, and every claim's evidence carries as_of.
    as_of = [c for c in claims if c["predicate_id"] == "as_of"]
    assert len(as_of) == 1
    assert as_of[0]["value"] == "2022-02-03"
    assert as_of[0]["raw_value"] == "Updated February 03, 2022"
    assert all(c["evidence"]["as_of"] == "2022-02-03" for c in claims)


def test_seed_load_is_idempotent_through_the_sink() -> None:
    """A second load asserts the same content-digest claims (append-only)."""
    report_a = run_seed(SOURCE, sink_kind="memory")
    report_b = run_seed(SOURCE, sink_kind="memory")
    a = [r for r in report_a.claims if r.get("record_kind") == "claim"]
    b = [r for r in report_b.claims if r.get("record_kind") == "claim"]
    assert len(a) == len(b)
    from db.claim_sink import content_digest

    assert {content_digest(c) for c in a} == {content_digest(c) for c in b}


def test_seed_registry_row_stays_unpermitted_and_live_refused() -> None:
    """The seed load never flips the registry row or the live gate (SIG-INGEST-028)."""
    run_seed(SOURCE, sink_kind="memory")
    rec = get(SOURCE)
    assert rec.ingestion_permitted is False
    assert live_gate_reasons(SOURCE)  # a LIVE run for the seed source still refuses


def test_run_seed_unknown_source_refuses() -> None:
    with pytest.raises((SeedNotRegistered, ValueError)):
        run_seed("no_such_source", sink_kind="memory")


def test_run_seed_non_seed_source_refuses() -> None:
    with pytest.raises(SeedNotRegistered):
        run_seed("muckrock", sink_kind="memory")
