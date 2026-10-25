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


def test_seed_registry_row_flipped_at_g5_stays_a_seed() -> None:
    """The seed load never flips the registry row itself (SIG-INGEST-028); the
    row was flipped by the operator at GATE-G5 (2026-10-25, OP-26)."""
    run_seed(SOURCE, sink_kind="memory")
    rec = get(SOURCE)
    assert rec.ingestion_permitted is True  # FLIPPED 2026-10-25 (GATE-G5)
    assert not live_gate_reasons(
        SOURCE
    )  # gate open post-flip; still a one-time seed asset, never a feed


def test_run_seed_unknown_source_refuses() -> None:
    with pytest.raises((SeedNotRegistered, ValueError)):
        run_seed("no_such_source", sink_kind="memory")


def test_run_seed_non_seed_source_refuses() -> None:
    with pytest.raises(SeedNotRegistered):
        run_seed("muckrock", sink_kind="memory")


# --- the 2026 origin-verified refresh (P35.10 / I8 §4.4 / ACQ-06, statute_seed/2) ---
#
# I7-C9 answer `a`: refresh the stale 2022 seed FROM ORIGINS — every v2 entry is
# verified at its own legislature/governor page in the committed I7 packets and
# carries origin_url/instrument_type/effective_date/verified_on/confidence. A new
# committed asset (`supersedes_asset` names the frozen 2022 seed; both stay
# loadable — append-only, P7). `[[duty_rows]]` is the 50-state coverage/duty
# table (SIG-INGEST-050): origin_verified states == the entry states, recorded
# states keep the superseded asset as their provenance, none_recorded is
# ABSENCE OF EVIDENCE — never a "no statute" claim (§3.1).

SOURCE_2026 = "state_alpr_statute_inventory_2026"
ASSET_2026 = "state_alpr_statute_seed_2026.toml"

# The canonical 50 US states — the coverage table's contract (SIG-INGEST-050).
_US_STATES = frozenset(
    {
        "Alabama",
        "Alaska",
        "Arizona",
        "Arkansas",
        "California",
        "Colorado",
        "Connecticut",
        "Delaware",
        "Florida",
        "Georgia",
        "Hawaii",
        "Idaho",
        "Illinois",
        "Indiana",
        "Iowa",
        "Kansas",
        "Kentucky",
        "Louisiana",
        "Maine",
        "Maryland",
        "Massachusetts",
        "Michigan",
        "Minnesota",
        "Mississippi",
        "Missouri",
        "Montana",
        "Nebraska",
        "Nevada",
        "New Hampshire",
        "New Jersey",
        "New Mexico",
        "New York",
        "North Carolina",
        "North Dakota",
        "Ohio",
        "Oklahoma",
        "Oregon",
        "Pennsylvania",
        "Rhode Island",
        "South Carolina",
        "South Dakota",
        "Tennessee",
        "Texas",
        "Utah",
        "Vermont",
        "Virginia",
        "Washington",
        "West Virginia",
        "Wisconsin",
        "Wyoming",
    }
)

#: Enumeration-aid hosts — enumerating is not citing (I7 NEW-7; C9 `a`).
_ENUMERATION_AID_HOSTS = (
    "ncsl.org",
    "legislativeanalysis.org",
    "ghsa.org",
    "multistate.us",
)

# The states the I7 packets verified at origin (F-374).
_ORIGIN_VERIFIED_STATES = frozenset(
    {
        "Connecticut",
        "Idaho",
        "Kentucky",
        "Missouri",
        "New Mexico",
        "Oregon",
        "Virginia",
        "Washington",
    }
)


def _seed_bytes_2026() -> bytes:
    return seed_asset_path(SOURCE_2026).read_bytes()


def _v2(*pairs: tuple[str, str]) -> bytes:
    """A minimal well-formed v2 asset, mutated per-test via (old, new) pairs."""
    entry = (
        '[[statutes]]\nstate = "Oregon"\ninstrument_type = "statute"\n'
        'years_enacted = [2026]\ncitations = ["SB 1516"]\n'
        'origin_url = "https://olis.oregonlegislature.gov/liz/2026R1/Measures/Overview/SB1516"\n'
        'effective_date = "2026-03-31"\ndate_basis = "effective"\n'
        'verified_on = "2026-09-30"\nconfidence = "high"\n'
        'evidence = ["I7-U143"]\n'
    )
    duty = (
        '[[duty_rows]]\nstate = "Oregon"\nstatute_posture = "origin_verified"\n'
        f'statute_ref = "{ASSET_2026}"\n'
        'origin_url = "https://olis.oregonlegislature.gov/liz/2026R1/Measures/Overview/SB1516"\n'
        'instruments = ["SB 1516"]\nduties = []\nevidence = ["I7-U143"]\n'
        'verified_on = "2026-09-30"\n'
    )
    head = (
        'schema = "statute_seed/2"\nas_of = "2026-09-30"\n'
        'as_of_label = "I7/I9a origin reads, 2026-09-30"\n'
        'retrieved = "2026-10-10"\nfrozen = true\nnever_a_feed = true\n'
        'supersedes_asset = "state_alpr_statute_seed.toml"\n'
        'inventory_url = "urn:sig:seed:state-alpr-statute-2026"\n'
        "state_count = 1\nduty_row_count = 1\n"
    )
    doc = head + entry + duty
    for old, new in pairs:
        doc = doc.replace(old, new, 1)
    return doc.encode()


# --- the committed v2 asset ---------------------------------------------------


def test_parse_seed_2026_committed_asset() -> None:
    seed = parse_statute_seed(_seed_bytes_2026(), source_id=SOURCE_2026)
    assert seed.schema == "statute_seed/2"
    assert seed.as_of == "2026-09-30"
    assert seed.supersedes_asset == "state_alpr_statute_seed.toml"
    assert seed.state_count == 8
    assert len(seed.statutes) == 8
    for entry in seed.statutes:
        # I8 §4.4 / AC 2: every entry is origin-cited, never an inventory aid.
        assert entry.origin_url.startswith("https://")
        assert entry.instrument_type in {"statute", "executive_order"}
        assert entry.effective_date  # ISO, year-precision allowed
        assert entry.verified_on == "2026-09-30"  # the packet verification day
        assert entry.confidence in {"high", "medium", "low"}
        assert entry.evidence_ids  # the committed I7/I9a evidence rows
        assert not any(h in entry.origin_url for h in _ENUMERATION_AID_HOSTS)


def test_seed_2026_missouri_is_an_executive_order() -> None:
    """EO 26-18 is an executive instrument, typed executive_order — not a statute."""
    seed = parse_statute_seed(_seed_bytes_2026(), source_id=SOURCE_2026)
    mo = next(e for e in seed.statutes if e.state == "Missouri")
    assert mo.instrument_type == "executive_order"
    assert mo.effective_date == "2026-09-16"
    assert mo.date_basis == "issued"
    assert sum(1 for e in seed.statutes if e.instrument_type == "executive_order") == 1


def test_seed_2026_duty_rows_cover_all_50_states() -> None:
    """AC 3 / SIG-INGEST-050: one coverage row per US state — all 50 present."""
    seed = parse_statute_seed(_seed_bytes_2026(), source_id=SOURCE_2026)
    assert seed.duty_row_count == 50
    assert {r.state for r in seed.duty_rows} == _US_STATES
    verified = {r.state for r in seed.duty_rows if r.statute_posture == "origin_verified"}
    recorded = {r.state for r in seed.duty_rows if r.statute_posture == "recorded"}
    none = {r.state for r in seed.duty_rows if r.statute_posture == "none_recorded"}
    assert verified == _ORIGIN_VERIFIED_STATES == {e.state for e in seed.statutes}
    # The 16 states the frozen 2022 asset recorded keep it as provenance.
    assert len(recorded) == 16
    assert all(
        r.statute_ref == "state_alpr_statute_seed.toml"
        for r in seed.duty_rows
        if r.statute_posture == "recorded"
    )
    # none_recorded is absence of evidence — no instrument asserted (§3.1).
    assert none == _US_STATES - verified - recorded
    assert all(
        not r.instruments and not r.origin_url and not r.statute_ref
        for r in seed.duty_rows
        if r.statute_posture == "none_recorded"
    )


def test_seed_2026_duty_rows_name_registered_sources() -> None:
    """Every `duties` id is a registered future_statutory_disclosure_* source."""
    seed = parse_statute_seed(_seed_bytes_2026(), source_id=SOURCE_2026)
    named = {d for r in seed.duty_rows for d in r.duties}
    assert named == {
        "future_statutory_disclosure_al",
        "future_statutory_disclosure_ar",
        "future_statutory_disclosure_mn",
        "future_statutory_disclosure_nm",
        "future_statutory_disclosure_ut",
        "future_statutory_disclosure_va",
    }
    for source_id in named:
        rec = get(source_id)
        # AC: the duty rows stay fail-closed — no ingestion-permitted flips.
        assert rec.ingestion_permitted is False
        assert live_gate_reasons(source_id)
    # Virginia's I/J/K duty cycle is present and commencement-stamped.
    va = next(r for r in seed.duty_rows if r.state == "Virginia")
    assert "future_statutory_disclosure_va" in va.duties
    assert "April 1" in va.duty_notes and "July 1" in va.duty_notes
    nm = next(r for r in seed.duty_rows if r.state == "New Mexico")
    assert "2027-04-01" in nm.duty_notes  # future-ok: real-world: statutory first-reports deadline


# --- the strict v2 parser ------------------------------------------------------


def test_parse_v2_minimal_asset() -> None:
    seed = parse_statute_seed(_v2(), source_id=SOURCE_2026)
    assert seed.schema == "statute_seed/2"
    assert seed.state_count == 1 and seed.duty_row_count == 1


def test_parse_v2_unknown_entry_key_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(('instrument_type = "statute"', 'instrument_type = "statute"\noperator = "x"')),
            source_id=SOURCE_2026,
        )


def test_parse_v2_missing_origin_url_drifts() -> None:
    doc = _v2(
        (
            'origin_url = "https://olis.oregonlegislature.gov/liz/2026R1/Measures/Overview/SB1516"',
            'origin_url = ""',
        ),
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE_2026)


def test_parse_v2_enumeration_aid_origin_drifts() -> None:
    """NCSL/LAPPA/GHSA enumerate — they are never cited as origins (I7 NEW-7)."""
    doc = _v2(
        (
            "https://olis.oregonlegislature.gov/liz/2026R1/Measures/Overview/SB1516",
            "https://www.ncsl.org/technology-and-communication/automated-license-plate-readers-state-statutes",
        ),
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE_2026)


def test_parse_v2_wrong_instrument_type_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(('instrument_type = "statute"', 'instrument_type = "ordinance"')),
            source_id=SOURCE_2026,
        )


def test_parse_v2_bad_effective_date_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(('effective_date = "2026-03-31"', 'effective_date = "March 2026"')),
            source_id=SOURCE_2026,
        )


def test_parse_v2_missing_verified_on_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(('verified_on = "2026-09-30"', 'verified_on = ""')),
            source_id=SOURCE_2026,
        )


def test_parse_v2_wrong_supersedes_drifts() -> None:
    """supersedes_asset names the committed 2022 asset — append-only (P7)."""
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(
                ('supersedes_asset = "state_alpr_statute_seed.toml"', 'supersedes_asset = ""'),
            ),
            source_id=SOURCE_2026,
        )


def test_parse_v2_duty_row_count_mismatch_drifts() -> None:
    with pytest.raises(ContentDrift):
        parse_statute_seed(
            _v2(("duty_row_count = 1", "duty_row_count = 99")), source_id=SOURCE_2026
        )


def test_parse_v2_duty_posture_entry_mismatch_drifts() -> None:
    """The coverage table's origin_verified states must equal the entry states."""
    doc = _v2(
        (
            'state = "Oregon"\nstatute_posture = "origin_verified"',
            'state = "Ohio"\nstatute_posture = "recorded"',
        ),
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE_2026)


def test_parse_v2_duplicate_duty_state_drifts() -> None:
    """One coverage row per state — a duplicated row is drift, not data."""
    doc = _v2() + (
        b'\n[[duty_rows]]\nstate = "Oregon"\nstatute_posture = "recorded"\n'
        b'statute_ref = "x"\nverified_on = "2026-09-30"\n'
    )
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE_2026)


def test_parse_v2_none_recorded_with_instruments_drifts() -> None:
    """none_recorded is absence of evidence — it must not assert an instrument."""
    doc = _v2(('statute_posture = "origin_verified"', 'statute_posture = "none_recorded"'))
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE_2026)


def test_parse_v2_missing_schema_is_v1_not_v2() -> None:
    """A schema-less document is the v1 shape — v2 fields on v1 rows drift."""
    doc = _v2().replace(b'schema = "statute_seed/2"\n', b"", 1)
    with pytest.raises(ContentDrift):
        parse_statute_seed(doc, source_id=SOURCE)


# --- the v2 seed registry + load path ------------------------------------------


def test_seed_2026_spec_is_registered() -> None:
    spec = seed_spec(SOURCE_2026)
    assert spec is not None
    assert spec["asset"] == "state_alpr_statute_seed_2026.toml"
    assert spec["kind"] == "statute_seed"
    assert spec["media_type"] == "application/toml"


def test_seed_2026_connector_is_routable() -> None:
    from connectors.runner import CONNECTOR_FOR_SOURCE

    assert CONNECTOR_FOR_SOURCE[SOURCE_2026] == "state_statute_seed"


def test_seed_2026_load_asserts_origin_cited_claims() -> None:
    """`run_seed` on the v2 asset emits typed, origin-cited instrument claims."""
    report = run_seed(SOURCE_2026, sink_kind="memory")
    assert report.asserted is True
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]

    # 8 entries, one enactment year each → 8 instruments; 7 statutes + 1 EO.
    instruments = [c for c in claims if c["predicate_id"] == "instrument_type"]
    assert len(instruments) == 8
    assert sum(1 for c in instruments if c["value"] == "statute") == 7
    assert sum(1 for c in instruments if c["value"] == "executive_order") == 1

    # Missouri's EO is typed executive_order end-to-end (not a statute).
    mo = next(c for c in instruments if "Missouri" in c["subject_id"])
    assert mo["value"] == "executive_order"

    # Jurisdiction claims are us.state CANDIDATES (SIG-INGEST-034), never resolves.
    jurisdictions = [c for c in claims if c["predicate_id"] == "jurisdiction"]
    assert len(jurisdictions) == 8
    assert all(c["candidate_identifier"]["scheme"] == "us.state" for c in jurisdictions)
    assert {c["value"] for c in jurisdictions} == _ORIGIN_VERIFIED_STATES

    # Every instrument constrains ALPR and carries a real ISO effective date.
    tech = [c for c in claims if c["predicate_id"] == "constrains_technology"]
    assert len(tech) == 8 and all(c["value"] == ["alpr"] for c in tech)
    effective = {c["value"] for c in claims if c["predicate_id"] == "effective_from"}
    assert effective == {
        "2025-07-01",
        "2026-03-30",
        "2026-03-31",
        "2026-04-10",
        "2026-05-04",
        "2026-07-01",
        "2026-09-16",
    }

    # Per-entry provenance rides the claims: the legislature/governor origin
    # URL + the packet evidence ids — never an enumeration-aid host (I7 NEW-7).
    for c in claims:
        url = c["evidence"].get("source_url", "")
        assert not any(h in url for h in _ENUMERATION_AID_HOSTS)
    wa = next(c for c in instruments if "Washington" in c["subject_id"])
    assert wa["evidence"]["source_url"].startswith("https://app.leg.wa.gov/")
    assert wa["evidence"]["retrieved_date"] == "2026-09-30"
    assert "I7-U142" in wa["evidence"]["evidence_ids"]

    # The refresh label is first-class: one as_of claim carries the packet day.
    as_of = [c for c in claims if c["predicate_id"] == "as_of"]
    assert len(as_of) == 1
    assert as_of[0]["value"] == "2026-09-30"
    assert all(c["evidence"]["as_of"] == "2026-09-30" for c in claims)


def test_seed_2026_load_is_idempotent_through_the_sink() -> None:
    """A second load asserts the same content-digest claims (append-only)."""
    from db.claim_sink import content_digest

    report_a = run_seed(SOURCE_2026, sink_kind="memory")
    report_b = run_seed(SOURCE_2026, sink_kind="memory")
    a = [r for r in report_a.claims if r.get("record_kind") == "claim"]
    b = [r for r in report_b.claims if r.get("record_kind") == "claim"]
    assert len(a) == len(b)
    assert {content_digest(c) for c in a} == {content_digest(c) for c in b}


def test_seed_2026_registry_row_stays_unpermitted_and_live_refused() -> None:
    """The refresh never flips the registry row or the live gate (SIG-INGEST-028)."""
    run_seed(SOURCE_2026, sink_kind="memory")
    rec = get(SOURCE_2026)
    assert rec.ingestion_permitted is False
    assert live_gate_reasons(SOURCE_2026)


def test_seed_2026_supersedes_but_the_2022_asset_stays_loadable() -> None:
    """Append-only (P7): the frozen 2022 seed still loads as committed data."""
    report = run_seed(SOURCE, sink_kind="memory")
    assert report.asserted is True
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    assert sum(1 for c in claims if c["predicate_id"] == "instrument_type") == 21


def test_duty_row_sources_have_exactly_one_disposition() -> None:
    """New duty sources are registry rows with exactly one live-disposition row."""
    import tomllib
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / (
        "connectors/src/connectors/data/live_dispositions.toml"
    )
    dispositions = tomllib.loads(path.read_text())["sources"]
    for source_id in (
        "future_statutory_disclosure_al",
        "future_statutory_disclosure_ar",
        "future_statutory_disclosure_mn",
        "future_statutory_disclosure_nm",
        "future_statutory_disclosure_ut",
        "future_statutory_disclosure_va",
    ):
        assert dispositions[source_id]["disposition"] == "mirror"
