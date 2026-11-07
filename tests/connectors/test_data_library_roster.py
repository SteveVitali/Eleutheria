# SPDX-License-Identifier: Apache-2.0
"""The §22.7 Data Library roster test (SIG-INGEST-041, P37.13).

The roster is the spec's contract: every one of its rows MUST be registered,
``LINK`` posture until rights are reviewed. The committed mapping
(``connectors/src/connectors/data/data_library_roster.toml``,
``sig.data-library-roster/1``) is checked against the spec source's own table —
never a hand-copied count — and every covering id must resolve in the
registry. A new roster row lands without a covering source, or a covering row
is removed from ``sources.toml``: this test fails loud.
"""

from __future__ import annotations

import pytest
from connectors.data_library_roster import (
    coverage,
    roster,
    spec_roster_datasets,
)
from connectors.registry import CustodyPosture, registry

#: The eight LINK rows P37.13 registered for entries no earlier row covered.
P37_13_NEW = {
    "datalib_aaron_swartz_day",
    "datalib_atlas_border_communities",
    "datalib_clearview_ai_table",
    "datalib_federally_funded_bwc",
    "datalib_mediajustice_em_map",
    "datalib_public_safety_drones",
    "datalib_ring_neighbors_partnerships",
    "datalib_who_has_your_face",
}


def test_spec_table_yields_sixteen_rows() -> None:
    """The §22.7 spec table still parses to its documented 16 rows."""
    datasets = spec_roster_datasets()
    assert len(datasets) == 16, datasets
    assert datasets[0] == "Vigilant / Data Driven ALPR data"
    assert datasets[-1] == "Mapping China's Tech Giants (ASPI)"


def test_roster_matches_the_spec_table_row_for_row() -> None:
    """Every spec-table dataset cell names exactly one roster entry."""
    spec = list(spec_roster_datasets())
    committed = [e.spec_dataset for e in roster()]
    assert committed == spec, (
        f"roster/spec drift — spec rows missing from the roster file: "
        f"{set(spec) - set(committed)}; roster rows with no spec row: "
        f"{set(committed) - set(spec)}"
    )


def test_every_roster_entry_is_registered() -> None:
    """Each roster entry's `covers` resolves to registry source ids (SIG-INGEST-041)."""
    records = registry()
    uncovered = [(row.entry.roster_key, row.unresolved) for row in coverage() if row.unresolved]
    assert uncovered == [], uncovered
    for row in coverage():
        for record in row.records:
            assert record.id in records


def test_no_covering_id_is_shared_across_roster_entries_except_ca_survey() -> None:
    """A covering row may serve one roster entry; the CA auditor serves one."""
    seen: dict[str, str] = {}
    for row in coverage():
        for record in row.records:
            assert record.id not in seen or record.id in {
                "ca_state_auditor",
                "statrep_ca_california_auditor_alpr",
            }, f"{record.id} covers both {seen[record.id]} and {row.entry.roster_key}"
            seen.setdefault(record.id, row.entry.roster_key)


def test_p37_13_rows_are_link_posture_and_gated() -> None:
    """The new rows are LINK custody and `ingestion_permitted=false` — the
    operator's HG-03 line flips them, never the registry write (SIG-INGEST-041)."""
    records = registry()
    for sid in sorted(P37_13_NEW):
        record = records[sid]
        assert record.custody_posture == CustodyPosture.LINK, sid
        assert record.ingestion_permitted is False, sid
        assert record.rights.spdx == "UNDETERMINED", sid
        assert record.rights.redistributable is False, sid
        assert record.rights_reviewed_by == "", sid


def test_roster_covers_exactly_the_sixteen_entries() -> None:
    """Completeness the other way: the roster file adds no phantom entries."""
    assert len(roster()) == 16
    assert {e.roster_key for e in roster()} == {
        "aaron-swartz-day-psp",
        "aspi-mapping-chinas-tech-giants",
        "atlas-border-communities",
        "california-alpr-survey",
        "carnegie-ai-gsi",
        "cell-site-simulator-datasets",
        "clearview-ai-usage-table",
        "federally-funded-body-cameras",
        "facial-recognition-world-map",
        "mediajustice-electronic-monitoring",
        "public-safety-drones",
        "ring-neighbors-partnerships",
        "upturn-mass-extraction",
        "vigilant-data-driven-alpr",
        "who-has-your-face",
        "wiretap-reports",
    }


def test_every_p37_13_id_is_a_roster_cover() -> None:
    """The eight new rows are each claimed by exactly one roster entry — no
    orphaned registration and no forgotten roster entry."""
    covers = {sid for row in coverage() for sid in row.entry.covers}
    assert P37_13_NEW <= covers
    unclaimed = [sid for sid in P37_13_NEW if sid not in covers]
    assert unclaimed == []


def test_roster_cli_report_shape() -> None:
    """`sig-connectors roster` reports every entry; nothing is UNCOVERED."""
    from connectors.data_library_roster import coverage_report

    report = coverage_report()
    assert "UNCOVERED" not in report
    assert "16 roster entries; 0 uncovered" in report


@pytest.mark.parametrize("key", [e.roster_key for e in roster()])
def test_entry_metadata_is_recorded(key: str) -> None:
    """Every entry carries its dataset title, priority and registration basis —
    the mapping is a recorded claim, never an unexplained row."""
    entry = next(e for e in roster() if e.roster_key == key)
    assert entry.dataset.strip(), key
    assert entry.priority.strip(), key
    assert entry.registered_by.strip(), key
    assert entry.mapping in {"exact", "equivalent"}, key
