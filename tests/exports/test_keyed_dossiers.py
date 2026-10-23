# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P35.45 (K4 §5.2/§5.5, JUR-03) — the keyed dossier emission matrix.

The ``placement@1``-bound export mints a ``sig.dossier/2`` artifact per
D-K4-3 page under ``web/dossiers/<slug-path>.json``, the
``sig.dossier-index/2`` index, the honest ``sig.unplaced-report/1``, the
jurisdiction key map and the append-only slug history, the report-only
DBRight re-review list, the ``jurisdiction:<jkey>`` research-queue re-key,
and the measured-build block. With no engine bound the export degrades to
the pre-keyed flat ``web/dossiers.json`` posture unchanged.

The fixture set (``test_spine_export._fixture_claims`` + additions):

* ``A`` — placed Verdin city → chain US/CA/county-06037/place-0644000.
* ``B`` — CA→FL ``outside_declared`` (the two-sided disagreement).
* ``C`` — declared GB-ENG, ``axis_swap_suspected`` → declared fallback.
* ``D`` — declared GB-ENG, ``(0,0)`` → declared fallback, point withheld.
* ``E`` — declared CA, centroid-stamped → ``no_point`` declared fallback.
* ``F`` — undeclared ``(0,0)`` → chainless → the ``unplaced`` report.
* ``G`` — point inside Indonesia, declared ``ID`` → placed at the country
  root (the conservative-profile dossier).
* ``H`` — DBRight-licensed US record → the re-review list row.
"""

from __future__ import annotations

import importlib.util as _ilu
import json

import pytest
from placement_fixtures import build_placement_env
from test_spine_export import _build, _build24, _claim24, _fixture_claims, _site24

_needs_duckdb = pytest.mark.skipif(
    _ilu.find_spec("duckdb") is None,
    reason="duckdb is required for the placement engine",
)

_DBRIGHT = "LicenseRef-OperatorAccepted-DBRight"


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory):
    return build_placement_env(tmp_path_factory.mktemp("keyed_dossiers"))


@pytest.fixture(scope="module")
def engine(env):
    from exports.placement import PlacementEngine

    return PlacementEngine(env.pack_dir, env.registry_path, spec_path=env.spec_path)


def _extra_claims() -> list:
    """F/G/H — the unplaced row, the unadapted country, the DBRight slice."""
    from dataclasses import replace

    f = [
        # Undeclared + null island → chain-less → the unplaced report.
        _claim24("F-lat", "F", "camera_latitude", value_text="0.0", source_id="src_a"),
        _claim24("F-lon", "F", "camera_longitude", value_text="0.0", source_id="src_a"),
    ]
    g = _site24("G", "-5.0", "100.0", "iso.3166_1_alpha2", "ID", source_id="src_b")
    h = [
        # A US-located record whose slice carries the operator-accepted
        # DBRight licence — the re-review list's one row.
        replace(c, effective_spdx=_DBRIGHT, effective_rights_id="rights-dbright")
        for c in _site24("H", "26.0", "-81.0", "us.state_abbr", "FL", source_id="src_b")
    ]
    return f + g + h


@pytest.fixture(scope="module")
def export(engine):
    return _build24(_fixture_claims() + _extra_claims(), placement=engine)


def _artifact(export, path: str):
    raw = export.web_artifacts.get(path)
    return json.loads(raw.decode("utf-8")) if raw is not None else None


def _dossier_docs(export) -> dict[str, dict]:
    """slug_path → the emitted ``sig.dossier/2`` document."""
    out = {}
    for path, data in export.web_artifacts.items():
        if (
            path.startswith("web/dossiers/")
            and path.endswith(".json")
            and not path.endswith("index.json")
        ):
            doc = json.loads(data.decode("utf-8"))
            out[doc["slug_path"]] = doc
    return out


#: The D-K4-3 page set for the fixture claims — every US county/state/country
#: with ≥1 record; the single-record US place and non-US admin-1 mint none.
EXPECTED_PAGES = {
    "usa",
    "usa/ca",
    "usa/fl",
    "usa/ca/verdin-county-06037",
    "gbr",
    "idn",
}


@_needs_duckdb
def test_keyed_dossier_docs_emit_at_canonical_slug_paths(export) -> None:
    docs = _dossier_docs(export)
    assert set(docs) == EXPECTED_PAGES
    for slug_path, doc in docs.items():
        assert doc["schema"] == "sig.dossier/2"
        assert doc["slug"] == slug_path == doc["slug_path"]
        assert doc["jurisdiction_key"] == doc["jurisdiction"]
        assert doc["links"]["self"] == f"/dossier/{slug_path}/"
        assert doc["links"]["json"] == f"/dossier/{slug_path}.json"
        assert doc["page_threshold_basis"].startswith("D-K4-3")
        assert doc["placement_rules"] == "placement@1"
        assert doc["chain"], "every dossier names its root-first breadcrumb chain"


@_needs_duckdb
def test_below_threshold_keys_mint_no_page_but_stay_visible_as_children(export) -> None:
    """Verdin city (1 record < 10, no non-site evidence) and GB-ENG (1 < 10,
    non-US admin-1) mint no page — but each appears on its REGISTRY parent's
    children list as a named absence, never a dangling link (a US place's
    registry parent is the state, so the county's children list is empty)."""
    docs = _dossier_docs(export)
    ca_children = {c["jkey"]: c for c in docs["usa/ca"]["children"]}
    place = ca_children["us.census.geoid.place:0644000"]
    assert place["page"] is False
    assert place["records"] == 1
    # …and it also appears on the county's leaf partition — the county is on
    # the record's located chain even though it is not the place's registry
    # parent.
    by_leaf = {r["jkey"]: r for r in docs["usa/ca/verdin-county-06037"]["rollup"]["by_leaf"]}
    assert by_leaf["us.census.geoid.place:0644000"]["records"] == 1
    assert by_leaf["us.census.geoid.place:0644000"]["page"] is False
    gbr_children = {c["jkey"]: c for c in docs["gbr"]["children"]}
    eng = gbr_children["iso3166-2:GB-ENG"]
    assert eng["page"] is False and eng["records"] == 2  # C + D


@_needs_duckdb
def test_dossier_index_v2_parity_and_unplaced_sibling(export) -> None:
    index = _artifact(export, "web/dossiers/index.json")
    assert index["schema"] == "sig.dossier-index/2"
    rows = {r["slug_path"]: r for r in index["dossiers"]}
    assert set(rows) == EXPECTED_PAGES
    docs = _dossier_docs(export)
    for slug_path, row in rows.items():
        doc = docs[slug_path]
        # Index↔dossier parity: the same accumulated numbers, never a
        # second computation.
        assert row["jkey"] == doc["jurisdiction_key"]
        assert row["records"] == doc["rollup"]["records"]
        assert row["slug"] == row["slug_path"] == slug_path
        assert row["records_placed_only_here"] == doc["rollup"]["records_placed_only_here"]
        assert row["jurisdictionCode"] == doc["jurisdictionCode"]
    unplaced = index["unplaced"]
    assert unplaced["slug_path"] == "unplaced"
    assert unplaced["report"] == "web/unplaced.json"
    assert unplaced["records"] == 1  # F
    assert unplaced["excluded_from"], "the exclusion disclosure travels"
    # The unplaced sibling is never a dossier row.
    assert "unplaced" not in rows
    # The measured dossier-emit block (wall clock + peak RSS + page count).
    m = index["measurement"]
    assert m["dossier_pages"] == len(EXPECTED_PAGES)
    assert m["unplaced_records"] == 1
    assert m["wall_seconds"] >= 0 and m["peak_rss_bytes"] > 0


@_needs_duckdb
def test_rollup_leaf_partition_is_conserved(export) -> None:
    """Every dossier's placed total equals its own leaf count plus the
    member-leaf partition (``records_placed_below == Σ by_leaf.records``) —
    each placed record's recorded chain ends at exactly one leaf
    (SIG-JUR-D07's conservation, realised over member chains — never a sum
    over children, which would double-count chain-spanning records)."""
    docs = _dossier_docs(export)
    for path, doc in docs.items():
        r = doc["rollup"]
        by_leaf_total = sum(int(x["records"]) for x in r["by_leaf"])
        assert r["records_placed_below"] == by_leaf_total
        assert r["records"] == r["records_placed_only_here"] + by_leaf_total, (
            f"{path}: leaf partition does not reconcile"
        )
        assert r["conserved"] is True, f"{path}: dossier reports conservation broken"
    # The exact partition on the fixture: the county's one record lands at the
    # place leaf (recorded chain passes through the county).
    county = docs["usa/ca/verdin-county-06037"]["rollup"]
    assert county["records"] == 1
    assert county["records_placed_only_here"] == 0
    assert county["records_placed_below"] == 1


@_needs_duckdb
def test_rollup_by_source_overlap_is_disclosed(export) -> None:
    """The by_source roll-up leg carries the honest sum rule: 'sum' only when
    the per-source slices partition the placed total."""
    docs = _dossier_docs(export)
    for doc in docs.values():
        rule = doc["rollup"]["by_source_sum_rule"]
        legs = sum(doc["rollup"]["by_source"].values())
        assert rule == ("sum" if legs == doc["rollup"]["records"] else "distinct")


@_needs_duckdb
def test_unplaced_report_shape_links_and_vocabulary(export) -> None:
    report = _artifact(export, "web/unplaced.json")
    assert report["schema"] == "sig.unplaced-report/1"
    assert report["kind"] == "data_quality_report"
    assert report["records"] == 1  # F — undeclared, null island
    assert sum(report["by_reason"].values()) == report["records"]
    assert set(report["by_reason"]) <= set(report["check_vocabulary"])
    # K4 §5.5's verbatim header is carried, never paraphrased.
    assert report["header"] == (
        "These records are published, but SIG cannot yet say which "
        "jurisdiction they belong to. This is a data-quality list, not a place."
    )
    # One row per reason: records + share + linked sources + the honest fix.
    rows = {r["reason"]: r for r in report["reason_rows"]}
    assert set(rows) == set(report["by_reason"])
    for reason, n in report["by_reason"].items():
        row = rows[reason]
        assert row["records"] == n
        assert row["share_percent"] is not None
        assert row["sources"] and row["fix"]
    # §5.5's links point at LIVE routes — never the non-operational intake
    # receiver or a ``/queue/`` route that does not exist.
    assert report["correction"]["corrections"] == "/corrections/"
    assert report["correction"]["research_queue"] == "/research-queue/"
    assert "intake" not in json.dumps(report["correction"])
    # The download slot is a named absence — honest, not a dead link.
    assert report["downloads"]["status"] == "not_emitted"
    assert report["downloads"]["items"] == []
    assert report["excluded_from"]


@_needs_duckdb
def test_jurisdiction_code_is_country_a2_and_conservative_profile(export) -> None:
    """D-K4-7: ``jurisdictionCode`` is the COUNTRY's alpha-2 at every level;
    a country with no publication adapter lands on the conservative profile."""
    docs = _dossier_docs(export)
    assert docs["usa/ca/verdin-county-06037"]["jurisdictionCode"] == "US"
    assert docs["usa"]["jurisdictionCode"] == "US"
    idn = docs["idn"]
    assert idn["jurisdictionCode"] == "ID"
    pub = idn["publication"]
    assert pub["conservative_default"] is True
    assert pub["adapter_code"] is None
    assert pub["public_employee_names_publishable"] is False
    assert "conservative" in pub["note"]
    # GB maps to the UK's adapter via the named alias — never a guessed key.
    assert docs["gbr"]["jurisdictionCode"] == "GB"
    assert docs["gbr"]["publication"]["conservative_default"] is False
    assert docs["usa"]["publication"]["conservative_default"] is False


@_needs_duckdb
def test_research_queue_subject_ids_rekey_to_canonical_jkeys(engine) -> None:
    """``jurisdiction:<slug>`` card subjects and legacy ``jurisdiction`` fields
    re-key to ``jurisdiction:<jkey>`` with the legacy id retained; an
    unresolvable card stays as recorded."""
    export = _build24(
        _fixture_claims(),
        placement=engine,
        raw_over={
            "research_tasks": [
                (
                    "task-k1",
                    "missing_physical_devices",
                    "jurisdiction:ca",  # legacy flat slug → US-CA
                    "ca",
                    5.0,
                    "generated",
                    None,
                    "The mapped-device count reaches the active-device count.",
                    "det/1",
                ),
                (
                    "task-k2",
                    "missing_physical_devices",
                    "jurisdiction:iso3166-2:US-FL",  # already canonical
                    "iso3166-2:US-FL",
                    5.0,
                    "generated",
                    None,
                    "A closing condition.",
                    "det/2",
                ),
                (
                    "task-k3",
                    "missing_physical_devices",
                    "jurisdiction:atlantis",  # unresolvable — stays
                    "atlantis",
                    5.0,
                    "generated",
                    None,
                    "A closing condition.",
                    "det/3",
                ),
            ],
        },
    )
    queue = _artifact(export, "web/research_queue.json")
    by_id = {c["task_id"]: c for c in queue}
    k1 = by_id["task-k1"]
    assert k1["subject_id"] == "jurisdiction:iso3166-2:US-CA"
    assert k1["legacy_subject_id"] == "jurisdiction:ca"
    assert k1["jurisdiction"] == "iso3166-2:US-CA"
    assert k1["legacy_jurisdiction"] == "ca"
    k2 = by_id["task-k2"]
    assert k2["subject_id"] == "jurisdiction:iso3166-2:US-FL"
    assert "legacy_subject_id" not in k2
    k3 = by_id["task-k3"]
    assert k3["subject_id"] == "jurisdiction:atlantis"
    assert k3["jurisdiction"] == "atlantis"
    # …recorded, never silently resolved nor dropped.
    assert "no canonical jurisdiction key" in k3["rekey_note"]


@_needs_duckdb
def test_key_map_resolves_every_registry_key(export) -> None:
    key_map = _artifact(export, "web/jurisdiction_key_map.json")
    assert key_map["schema"] == "sig.jurisdiction-key-map/1"
    assert key_map["unplaced_slug_path"] == "unplaced"
    rows = {r["jkey"]: r for r in key_map["entries"]}
    # Every registry row resolves; the minted pages' paths are the routes.
    assert rows["iso3166-1:US"]["slug_path"] == "usa"
    assert rows["us.census.geoid.county:06037"]["slug_path"] == "usa/ca/verdin-county-06037"
    assert rows["us.census.geoid.place:0644000"]["slug_path"] == "usa/ca/verdin-city-0644000"
    assert rows["iso3166-1:ID"]["slug_path"] == "idn"
    # The unplaced sentinel is not a registry row.
    assert "unplaced" not in rows


@_needs_duckdb
def test_slug_history_seeded_and_append_only(export) -> None:
    history = _artifact(export, "web/jurisdiction_slug_history.json")
    assert history["schema"] == "sig.jurisdiction-slug-history/1"
    rows = {r["slug"]: r for r in history["rows"]}
    # The K4 §8.1 seed: flat slug → canonical successor, incl. the split and
    # corrected rows and the unresolved → unplaced rename.
    assert rows["ca"]["successor"] == "iso3166-2:US-CA"
    assert rows["id"]["kind"] == "split"
    assert set(rows["id"]["successor"]) == {"iso3166-2:US-ID", "iso3166-1:ID"}
    assert rows["bd"]["kind"] == "corrected"
    assert rows["bd"]["successor"] == "iso3166-1:SG"
    assert rows["unresolved"]["successor"] == "unplaced"
    # Plus one moved row per registry key's P35.18-era flat slug.
    assert rows["iso3166-1-us"]["successor"] == "iso3166-1:US"
    # Slugs are unique — the append-only map never names two histories.
    assert len(history["rows"]) == len({r["slug"] for r in history["rows"]})


@_needs_duckdb
def test_dbright_rereview_is_report_only(export) -> None:
    report = _artifact(export, "web/dbright_rereview.json")
    assert report["schema"] == "sig.dbright-rereview/1"
    assert report["report_only"] is True
    assert report["records"] == len(report["rows"]) == 1
    row = report["rows"][0]
    assert row["entity_id"] == "H"
    assert row["source_id"] == "src_b"
    assert row["chain"][0] == "iso3166-1:US"
    # A DBRight row located outside the US never lists.
    assert all(r["chain"][0] == "iso3166-1:US" for r in report["rows"])


@_needs_duckdb
def test_dbright_list_absent_without_dbright_rows(engine) -> None:
    export = _build24(_fixture_claims(), placement=engine)
    assert "web/dbright_rereview.json" not in export.web_artifacts


@_needs_duckdb
def test_disagreement_reads_from_both_dossier_sides(export) -> None:
    """B (declared CA, located FL): the CA dossier counts
    declared-here-located-elsewhere; the FL dossier counts
    located-here-declared-elsewhere. K4 §5.2's pair, one reading."""
    docs = _dossier_docs(export)
    ca = docs["usa/ca"]
    fl = docs["usa/fl"]
    assert ca["disagreements"]["declared_here_located_elsewhere"] == 1
    assert fl["disagreements"]["located_here_declared_elsewhere"] == 1
    # CA's appearing set includes B (the declared leg) — its placed set does not.
    assert ca["rollup"]["records"] == 2  # A + E placed
    assert ca["rollup"]["records_appearing"] == 3  # + B declared


@_needs_duckdb
def test_pre_placement_fallback_is_unchanged() -> None:
    """No engine bound → the pre-P35.45 posture byte-for-byte: the flat
    ``web/dossiers.json``, no per-dossier directory, no v2 index, no unplaced
    report, no key maps."""
    export = _build(_fixture_claims())
    assert "web/dossiers.json" in export.web_artifacts
    keyed = [p for p in export.web_artifacts if p.startswith("web/dossiers/")]
    assert keyed == []
    for path in (
        "web/unplaced.json",
        "web/jurisdiction_key_map.json",
        "web/jurisdiction_slug_history.json",
        "web/dbright_rereview.json",
    ):
        assert path not in export.web_artifacts


@_needs_duckdb
def test_dossier_sources_emit_at_slug_paths_with_placement_totals(export) -> None:
    """The per-dossier sources artifacts file under the same slug paths and
    carry the placed/leaf split the dossier page consumes."""
    sources_paths = {p for p in export.web_artifacts if p.startswith("web/dossier_sources/")}
    assert "web/dossier_sources/usa.json" in sources_paths
    assert "web/dossier_sources/usa/ca.json" in sources_paths
    # The unplaced report's own source rows.
    unplaced_src = _artifact(export, "web/dossier_sources/unplaced.json")
    assert unplaced_src is not None
    assert unplaced_src["jurisdiction"]["unplaced"] is True
    usa_src = _artifact(export, "web/dossier_sources/usa.json")
    t = usa_src["totals"]
    # Placed under the US root: A (Verdin), B (FL), E (CA declared), H (FL).
    assert t["records_placed"] == 4
    # Nobody's leaf is the country row itself — the whole total is Σ
    # descendant leaf counts (the conservation partition).
    assert t["records_placed_only_here"] == 0
