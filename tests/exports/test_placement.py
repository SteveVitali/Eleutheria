# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.19 ``placement@1`` — export-time jurisdiction placement (K4 §3.3/§3.4,
JUR-02b, ADR-092 compute-on-read).

The matrix under test is the contract's §7 fixture set staged by
``placement_fixtures.py`` (all boxes nest: country ⊃ state ⊃ county ⊃ place;
declared stand-ins, ``fixture_inputs=True`` — never captured evidence):

* R1 rejects — ``(0,0)`` null-island and out-of-range/NaN points, declared
  fallback vs unplaced;
* R2 — the full located chain ``country → admin-1 → county → place`` reads
  ``consistent``; deeper levels never evaluated read ``not_evaluated``;
* R3 — the Nottingham axis swap and the GA/NZ sign flips: declared level,
  ``*_suspected``, point withheld;
* R4 — located wins: CA→FL and MO/KS (same country) read
  ``outside_declared``; GB-declared→Indonesia and Idaho-declared→Indonesia
  read ``outside_declared_country``; the disclosure pair is counted on both
  dossier sides;
* R5 — no usable point + known declared → declared level (``no_point`` /
  ``coordinates_conflicted`` / ``point_rejected:*``);
* R6/R7 — ``outside_all_boundaries`` / ``no_location_evidence`` unplaced;
* R8 — ``name_lookup``/``name_unmatched``/``name_ambiguous`` (fixture-only);
* the shared-boundary tie-break (lowest GEOID, ``on_boundary``);
* the SIG-IDENT-004 agency-centroid guard — ``organization_centroid_or_unknown``
  never drives point-in-polygon and the point is withheld;
* landed ``geometry_defect`` flags (P35.16) consumed as inputs — an unknown
  class refuses placement;
* fail-closed construction: unverified/tampered pack, divergent
  ``boundaries_root``/vintages, spec/pack layer drift;
* the closed ``placement_check`` vocabulary is exactly ticket-299 §5's list.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from exports.placement import (
    PLACEMENT_BASIS,
    PLACEMENT_CHECKS,
    PLACEMENT_RULESET,
    PlacementEngine,
    PlacementError,
    PlacementInput,
    PlacementResult,
    build_report,
)
from placement_fixtures import build_placement_env

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None,
    reason="duckdb is required for the placement engine",
)


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory):
    return build_placement_env(tmp_path_factory.mktemp("placement"))


@pytest.fixture(scope="module")
def engine(env) -> PlacementEngine:
    return PlacementEngine(env.pack_dir, env.registry_path, spec_path=env.spec_path)


def _place(engine: PlacementEngine, *inputs: PlacementInput) -> list[PlacementResult]:
    return engine.place_many(list(inputs))


def _p(
    rid: str,
    lat: float | None = None,
    lon: float | None = None,
    *,
    declared: tuple[str, str] | None = None,
    name: str | None = None,
    precision: str | None = None,
    flags: frozenset[str] = frozenset(),
    status: str = "resolved",
    coord: bool = True,
) -> PlacementInput:
    return PlacementInput(
        record_id=rid,
        source_id="src_a",
        lat=lat,
        lon=lon,
        point_status=status,
        has_coordinate_claims=coord,
        precision=precision,
        declared=declared,
        defect_flags=flags,
        name=name,
    )


# --------------------------------------------------------------------------- #
# The closed vocabulary (ticket 299 §5 — this exact list, no more no less)     #
# --------------------------------------------------------------------------- #


def test_placement_check_vocabulary_is_the_contract_list() -> None:
    assert set(PLACEMENT_CHECKS) == {
        "consistent",
        "on_boundary",
        "outside_declared",
        "outside_declared_country",
        "axis_swap_suspected",
        "sign_flip_suspected",
        "no_point",
        "coordinates_conflicted",
        "point_rejected:null_island",
        "point_rejected:invalid_point",
        "outside_all_boundaries",
        "no_location_evidence",
        "name_unmatched",
        "name_ambiguous",
        "not_evaluated",
        "null_island",
        "invalid_point",
    }


def test_result_refuses_a_check_outside_the_vocabulary() -> None:
    """The closed vocabulary is enforced at the dataclass — an unknown
    placement_check value is a build error, never an emitted row."""
    with pytest.raises(PlacementError, match="closed"):
        PlacementResult(
            record_id="x",
            source_id=None,
            jurisdiction_key=None,
            jurisdiction_chain=(),
            placement_basis=None,
            placement_check="somewhere_else",
            declared=None,
            declared_jkey=None,
            located_jkey=None,
            boundary_vintage=None,
            point_withheld=False,
            on_boundary=False,
        )
    with pytest.raises(PlacementError, match="closed"):
        PlacementResult(
            record_id="x",
            source_id=None,
            jurisdiction_key=None,
            jurisdiction_chain=(),
            placement_basis="guessed",
            placement_check="consistent",
            declared=None,
            declared_jkey=None,
            located_jkey=None,
            boundary_vintage=None,
            point_withheld=False,
            on_boundary=False,
        )


# --------------------------------------------------------------------------- #
# R2 — the located chain                                                     #
# --------------------------------------------------------------------------- #


def test_inside_declared_full_chain(engine: PlacementEngine) -> None:
    """A point inside the declared state's full chain places at the leaf:
    country → admin-1 → county → place."""
    (r,) = _place(engine, _p("a", 34.0, -115.0, declared=("us.state_abbr", "CA")))
    assert r.placement_check == "consistent"
    assert r.placement_basis == "point_in_polygon"
    assert r.jurisdiction_key == "us.census.geoid.place:0644000"
    assert r.jurisdiction_chain == (
        "iso3166-1:US",
        "iso3166-2:US-CA",
        "us.census.geoid.county:06037",
        "us.census.geoid.place:0644000",
    )
    assert r.declared == ("us.state_abbr", "CA")
    assert r.declared_jkey == "iso3166-2:US-CA"
    assert r.boundary_vintage == "tiger-2025"
    assert not r.point_withheld and not r.on_boundary


def test_undeclared_point_places_identically(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 34.0, -115.0))
    assert r.placement_check == "consistent"
    assert r.jurisdiction_key == "us.census.geoid.place:0644000"


def test_country_only_chain_reads_not_evaluated(engine: PlacementEngine) -> None:
    """Partial depth (K4 §3.3): Indonesia loads no admin-1 layer — a hit at
    country level places there and the deeper levels read ``not_evaluated``,
    never unplaced and never ``consistent``."""
    (r,) = _place(engine, _p("a", -2.0, 110.0, declared=("iso.3166_1_alpha2", "ID")))
    assert r.placement_check == "not_evaluated"
    assert r.placed
    assert r.jurisdiction_key == "iso3166-1:ID"
    assert r.jurisdiction_chain == ("iso3166-1:ID",)


def test_state_leaf_with_no_county_boundaries_is_not_evaluated(
    engine: PlacementEngine,
) -> None:
    (r,) = _place(engine, _p("a", 44.0, -112.5, declared=("us.state_abbr", "ID")))
    assert r.placement_check == "not_evaluated"
    assert r.jurisdiction_key == "iso3166-2:US-ID"


def test_declared_key_deeper_than_the_leaf_extends_consistently(
    engine: PlacementEngine,
) -> None:
    """A declared county under the located state is consistent with the
    located chain (the declared level is deeper than the located answer);
    the placement stays at the located leaf and deeper levels are
    not_evaluated."""
    (r,) = _place(engine, _p("a", 35.0, -114.9, declared=("us.census.geoid.county", "06037")))
    assert r.jurisdiction_key == "iso3166-2:US-CA"
    assert r.placement_check in {"consistent", "not_evaluated"}
    assert r.declared_jkey == "us.census.geoid.county:06037"


# --------------------------------------------------------------------------- #
# The shared-boundary tie-break                                              #
# --------------------------------------------------------------------------- #


def test_shared_boundary_lowest_geoid_wins(engine: PlacementEngine) -> None:
    """The two Kansas counties overlap on x ∈ [-96.6,-96.5] — a point in the
    band double-hits and the lowest GEOID wins deterministically."""
    (r,) = _place(engine, _p("a", 39.0, -96.55))
    assert r.jurisdiction_key == "us.census.geoid.county:20100"
    assert r.placement_check == "on_boundary"
    assert r.on_boundary
    assert r.jurisdiction_chain[:2] == ("iso3166-1:US", "iso3166-2:US-KS")


def test_shared_boundary_is_deterministic(engine: PlacementEngine) -> None:
    inputs = [_p(f"b{i}", 39.0, -96.55) for i in range(4)]
    keys = {r.jurisdiction_key for r in engine.place_many(inputs)}
    assert keys == {"us.census.geoid.county:20100"}


# --------------------------------------------------------------------------- #
# The NE +0.02° coast tolerance — non_us layers only                         #
# --------------------------------------------------------------------------- #


def test_coast_tolerance_places_the_ne_country(engine: PlacementEngine) -> None:
    """0.01° north of Indonesia's box (which tops out at lat 6.0) is inside
    the 0.02° tolerance → placed at country level (deeper: not_evaluated)."""
    (r,) = _place(engine, _p("a", 6.01, 110.0))
    assert r.jurisdiction_key == "iso3166-1:ID"
    assert r.placement_check == "not_evaluated"


def test_coast_tolerance_is_bounded(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 6.05, 110.0))
    assert not r.placed
    assert r.placement_check == "outside_all_boundaries"


def test_no_tolerance_on_tiger_layers(engine: PlacementEngine) -> None:
    """A point 0.01° outside the California box does NOT tolerance-hit the
    state — TIGER is full-resolution. It still lands inside the US country
    box (NE admin-0, tolerance-eligible) at country level."""
    (r,) = _place(engine, _p("a", 36.01, -115.0))
    assert r.jurisdiction_key == "iso3166-1:US"
    assert "US-CA" not in r.jurisdiction_chain


# --------------------------------------------------------------------------- #
# R3 — suspected swapped / sign-flipped points (declared fallback, withheld) #
# --------------------------------------------------------------------------- #


def test_nottingham_axis_swap(engine: PlacementEngine) -> None:
    """The recorded pair (lat=-1.15, lon=52.95) sits in no boundary, but its
    swap (52.95, -1.15) lands inside the declared GB-ENG rollup → declared
    level, ``axis_swap_suspected``, the point withheld (never drawn, never
    sub-counted)."""
    (r,) = _place(engine, _p("a", -1.15, 52.95, declared=("iso.3166_2", "GB-ENG")))
    assert r.placement_check == "axis_swap_suspected"
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-2:GB-ENG"
    assert r.located_jkey is None
    assert r.point_withheld


def test_georgia_sign_flip(engine: PlacementEngine) -> None:
    """A south-of-equator 'Georgia' point flips its sign back inside the
    declared US-GA → ``sign_flip_suspected``, declared level, withheld."""
    (r,) = _place(engine, _p("a", -32.5, -82.5, declared=("us.state_abbr", "GA")))
    assert r.placement_check == "sign_flip_suspected"
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-2:US-GA"
    assert r.point_withheld


def test_new_zealand_sign_flip(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 41.0, 172.0, declared=("iso.3166_1_alpha2", "NZ")))
    assert r.placement_check == "sign_flip_suspected"
    assert r.jurisdiction_key == "iso3166-1:NZ"
    assert r.point_withheld


def test_landed_axis_swap_flag_consumes_the_detector_verdict(
    engine: PlacementEngine,
) -> None:
    """A landed geometry_defect claim (P35.16) is an input: the flag marks
    the point suspect without re-testing the variant — even when the
    recorded pair would have located cleanly."""
    (r,) = _place(
        engine,
        _p(
            "a",
            34.0,
            -115.0,
            declared=("us.state_abbr", "CA"),
            flags=frozenset({"axis_swap"}),
        ),
    )
    assert r.placement_check == "axis_swap_suspected"
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-2:US-CA"
    assert r.point_withheld


def test_wrong_jurisdiction_flag_leaves_the_point_usable(
    engine: PlacementEngine,
) -> None:
    """``wrong_jurisdiction`` flags the *label*, not the point — the point
    still enters the join and located wins (R4 IS the detector's verdict)."""
    (r,) = _place(
        engine,
        _p(
            "a",
            26.5,
            -81.5,
            declared=("us.state_abbr", "CA"),
            flags=frozenset({"wrong_jurisdiction"}),
        ),
    )
    assert r.placement_check == "outside_declared"
    assert r.jurisdiction_key == "iso3166-2:US-FL"


def test_unknown_defect_class_refuses(engine: PlacementEngine) -> None:
    with pytest.raises(PlacementError, match="unknown geometry_defect"):
        _place(engine, _p("a", 34.0, -115.0, flags=frozenset({"mystery"})))


def test_defect_flag_with_no_declaration_is_unplaced(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 34.0, -115.0, flags=frozenset({"axis_swap"})))
    assert not r.placed
    assert r.placement_check == "axis_swap_suspected"
    assert r.point_withheld


# --------------------------------------------------------------------------- #
# R4 — located wins; the disagreement is disclosed                           #
# --------------------------------------------------------------------------- #


def test_california_declared_florida_located(engine: PlacementEngine) -> None:
    """The K4 CA→FL fixture: the point wins; declared CA stays on the record
    and the (declared → located) pair is counted for both dossiers."""
    (r,) = _place(engine, _p("a", 26.5, -81.5, declared=("us.state_abbr", "CA")))
    assert r.placement_check == "outside_declared"
    assert r.placement_basis == "point_in_polygon"
    assert r.jurisdiction_key == "iso3166-2:US-FL"
    assert r.declared_jkey == "iso3166-2:US-CA"
    assert r.located_jkey == "iso3166-2:US-FL"


def test_mo_ks_border_located_kansas_wins(engine: PlacementEngine) -> None:
    """MoDOT-on-the-Kansas-side: a Missouri-declared point inside Kansas is
    a same-country R4 — located wins, disclosed, never silently resolved."""
    (r,) = _place(engine, _p("a", 39.5, -95.5, declared=("us.state_abbr", "MO")))
    assert r.placement_check == "outside_declared"
    assert r.jurisdiction_key == "iso3166-2:US-KS"


def test_cross_country_disagreement(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", -2.0, 110.0, declared=("iso.3166_1_alpha2", "GB")))
    assert r.placement_check == "outside_declared_country"
    assert r.jurisdiction_key == "iso3166-1:ID"


def test_id_idaho_vs_id_indonesia_are_two_keys(engine: PlacementEngine) -> None:
    """The I1 'ID' ambiguity resolved: a USPS Idaho record lands on
    ``iso3166-2:US-ID``; an ISO Indonesia record on ``iso3166-1:ID`` — two
    distinct canonical keys, never one bucket."""
    (idaho, indonesia, crossed) = _place(
        engine,
        _p("a", 44.0, -112.5, declared=("us.state_abbr", "ID")),
        _p("b", -2.0, 110.0, declared=("iso.3166_1_alpha2", "ID")),
        _p("c", -2.0, 110.0, declared=("us.state_abbr", "ID")),
    )
    assert idaho.jurisdiction_key == "iso3166-2:US-ID"
    assert indonesia.jurisdiction_key == "iso3166-1:ID"
    assert idaho.jurisdiction_key != indonesia.jurisdiction_key
    # A USPS-declared Idaho record sitting in Indonesia crosses a country.
    assert crossed.placement_check == "outside_declared_country"
    assert crossed.jurisdiction_key == "iso3166-1:ID"


def test_mn_minnesota_vs_mn_mongolia(engine: PlacementEngine) -> None:
    """The 'MN' ambiguity the other way: a USPS Minnesota point lands on the
    state key; the Mongolian record (no geometry in the K4 fixture story —
    here declared-only) places at country level ``iso3166-1:MN``."""
    (us_mn, mn_mongolia) = _place(
        engine,
        _p("a", 46.0, -92.5, declared=("us.state_abbr", "MN")),
        _p("b", 47.0, 104.0, declared=("iso.3166_1_alpha2", "MN")),
    )
    assert us_mn.jurisdiction_key == "iso3166-2:US-MN"
    assert mn_mongolia.jurisdiction_key == "iso3166-1:MN"


# --------------------------------------------------------------------------- #
# R1 — the point's own validity                                              #
# --------------------------------------------------------------------------- #


def test_null_island_declared_falls_back_withheld(engine: PlacementEngine) -> None:
    """(0,0) is never placed by point: declared fallback, the rejected reason
    carried as ``point_rejected:null_island``, the pair withheld."""
    (r,) = _place(engine, _p("a", 0.0, 0.0, declared=("iso.3166_2", "GB-ENG")))
    assert r.placement_check == "point_rejected:null_island"
    assert r.jurisdiction_key == "iso3166-2:GB-ENG"
    assert r.point_withheld


def test_null_island_undeclared_is_unplaced(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 0.0, 0.0))
    assert not r.placed
    assert r.placement_check == "null_island"
    # The defective pair is withheld even with nothing declared — a (0,0)
    # never re-emits as the record's geometry.
    assert r.point_withheld


def test_out_of_range_and_nan_are_invalid(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 95.0, 0.0))
    assert not r.placed and r.placement_check == "invalid_point"
    (r,) = _place(engine, _p("a", float("nan"), 0.0))
    assert r.placement_check == "invalid_point"
    (r,) = _place(engine, _p("a", 200.0, 0.0, declared=("us.state_abbr", "CA")))
    assert r.placement_check == "point_rejected:invalid_point"
    assert r.jurisdiction_key == "iso3166-2:US-CA"


def test_landed_null_island_flag_is_point_rejected(engine: PlacementEngine) -> None:
    (r,) = _place(
        engine,
        _p("a", 0.0, 0.0, declared=("us.state_abbr", "CA"), flags=frozenset({"null_island"})),
    )
    assert r.placement_check == "point_rejected:null_island"
    assert r.jurisdiction_key == "iso3166-2:US-CA"


# --------------------------------------------------------------------------- #
# R5 — no usable point + declared                                            #
# --------------------------------------------------------------------------- #


def test_no_point_declared_falls_back(engine: PlacementEngine) -> None:
    """K4 §3.6: 'the 1 Mongolian record, which has no geometry, is placed at
    country level iso3166-1:MN' — a declaration with no usable point is a
    declared-level placement, not an unplaced record."""
    (r,) = _place(
        engine,
        _p("a", declared=("iso.3166_1_alpha2", "MN"), status="unreported", coord=False),
    )
    assert r.placement_check == "no_point"
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-1:MN"


def test_conflicted_envelope_declared_falls_back(engine: PlacementEngine) -> None:
    (r,) = _place(
        engine, _p("a", declared=("us.state_abbr", "CA"), status="conflicted", coord=False)
    )
    assert r.placement_check == "coordinates_conflicted"
    assert r.jurisdiction_key == "iso3166-2:US-CA"


def test_usable_point_in_no_boundary_with_declared_falls_back(
    engine: PlacementEngine,
) -> None:
    """A real point that lands in no boundary ('ocean') with a declared key:
    the declaration is the only usable evidence — declared level, honestly
    named ``outside_all_boundaries``, the point withheld from maps/sub-counts."""
    (r,) = _place(engine, _p("a", 0.1, 0.1, declared=("us.state_abbr", "CA")))
    assert r.placement_check == "outside_all_boundaries"
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-2:US-CA"
    assert r.point_withheld


# --------------------------------------------------------------------------- #
# R6 / R7 — unplaced quality states                                          #
# --------------------------------------------------------------------------- #


def test_point_in_no_boundary_no_declared_is_unplaced(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", 0.1, 0.1))
    assert not r.placed
    assert r.placement_basis is None
    assert r.placement_check == "outside_all_boundaries"
    assert r.jurisdiction_chain == ()


def test_no_point_no_declared_is_unplaced(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", status="unreported", coord=False))
    assert not r.placed
    assert r.placement_check == "no_location_evidence"


def test_sig_unresolved_is_no_declaration(engine: PlacementEngine) -> None:
    """A ``sig.unresolved`` bucket is 'nothing declared' (R7), never a key —
    with a point the record still locates; without one it is unplaced."""
    (located, unlocated) = _place(
        engine,
        _p("a", 47.0, 104.0, declared=("sig.unresolved", "unknown")),
        _p("b", declared=("sig.unresolved", "unknown"), status="unreported", coord=False),
    )
    assert located.jurisdiction_key == "iso3166-1:MN"
    assert not unlocated.placed
    assert unlocated.placement_check == "no_location_evidence"


def test_unknown_declared_key_is_treated_as_undeclared(engine: PlacementEngine) -> None:
    """A declared key the registry never minted cannot be placed at — it is
    recorded (the declared columns carry it verbatim) but the located answer
    still wins, and the disagreement is disclosed."""
    (r,) = _place(engine, _p("a", 26.5, -81.5, declared=("iso.3166_2", "US-XX")))
    assert r.placement_check == "outside_declared"
    assert r.jurisdiction_key == "iso3166-2:US-FL"
    assert r.declared_jkey == "iso3166-2:US-XX"


# --------------------------------------------------------------------------- #
# SIG-IDENT-004 — the agency-centroid guard                                   #
# --------------------------------------------------------------------------- #


def test_organization_centroid_is_never_point_placed(engine: PlacementEngine) -> None:
    """A centroid-stamped point inside a real boundary is NOT used — the
    declared fallback carries the record and the pair is withheld."""
    (r,) = _place(
        engine,
        _p(
            "a",
            34.0,
            -115.0,
            declared=("us.state_abbr", "CA"),
            precision="organization_centroid_or_unknown",
        ),
    )
    assert r.placement_basis == "declared"
    assert r.jurisdiction_key == "iso3166-2:US-CA"
    assert r.placement_check == "no_point"
    assert r.point_withheld


def test_organization_centroid_undeclared_never_locates(
    engine: PlacementEngine,
) -> None:
    (r,) = _place(
        engine,
        _p("a", 34.0, -115.0, precision="organization_centroid_or_unknown"),
    )
    assert not r.placed
    assert r.placement_check == "no_location_evidence"
    assert r.point_withheld


# --------------------------------------------------------------------------- #
# R8 — the non-site name lookup (fixture-only until I8)                       #
# --------------------------------------------------------------------------- #


def test_name_lookup_single_hit_places(engine: PlacementEngine) -> None:
    """'Verdin city' (the place NAMELSAD) resolves one registry row — the
    record lands on it with basis ``name_lookup``."""
    (r,) = _place(engine, _p("a", name="Verdin city", coord=False))
    assert r.placement_check == "consistent"
    assert r.placement_basis == "name_lookup"
    assert r.jurisdiction_key == "us.census.geoid.place:0644000"
    assert r.jurisdiction_chain[0] == "iso3166-1:US"


def test_name_lookup_ambiguous_never_guesses(engine: PlacementEngine) -> None:
    """Two places named Centerville → name_ambiguous: every candidate stays
    visible, no winner is picked."""
    (r,) = _place(engine, _p("a", name="Centerville", coord=False))
    assert not r.placed
    assert r.placement_check == "name_ambiguous"


def test_name_lookup_miss_is_unmatched(engine: PlacementEngine) -> None:
    (r,) = _place(engine, _p("a", name="Atlantis", coord=False))
    assert not r.placed
    assert r.placement_check == "name_unmatched"


# --------------------------------------------------------------------------- #
# Construction — the fail-closed gate                                        #
# --------------------------------------------------------------------------- #


def test_engine_refuses_a_missing_pack(env) -> None:
    with pytest.raises(PlacementError, match="refused"):
        PlacementEngine(env.pack_dir.parent / "nope", env.registry_path, spec_path=env.spec_path)


def test_engine_refuses_a_tampered_layer(env, tmp_path: Path) -> None:
    import shutil

    bad_pack = tmp_path / "pack_tampered"
    shutil.copytree(env.pack_dir, bad_pack)
    (bad_pack / "us_states.parquet").write_bytes(b"tampered")
    with pytest.raises(PlacementError, match="verif"):
        PlacementEngine(bad_pack, env.registry_path, spec_path=env.spec_path)


def test_engine_refuses_root_divergence(env) -> None:
    doc = json.loads(json.dumps(env.registry_doc))
    doc["boundary_pack"]["boundaries_root"] = "0" * 64
    with pytest.raises(PlacementError, match="boundaries_root"):
        PlacementEngine(env.pack_dir, doc, spec_path=env.spec_path)


def test_engine_refuses_vintage_divergence(env) -> None:
    doc = json.loads(json.dumps(env.registry_doc))
    doc["vintages"] = {"tiger": "tiger-1999", "natural_earth": "ne-5.1"}
    with pytest.raises(PlacementError, match="vintage"):
        PlacementEngine(env.pack_dir, doc, spec_path=env.spec_path)


def test_engine_refuses_a_non_registry_document(env, tmp_path: Path) -> None:
    bad = tmp_path / "not_a_registry.json"
    bad.write_text(json.dumps({"schema": "sig.other/1", "rows": []}))
    with pytest.raises(PlacementError, match="schema"):
        PlacementEngine(env.pack_dir, bad, spec_path=env.spec_path)


def test_engine_refuses_spec_pack_drift(env, tmp_path: Path) -> None:
    """A spec declaring a minting layer the pack does not carry refuses —
    never a silently-partial boundary set."""
    drifted = tmp_path / "spec_drifted.toml"
    drifted.write_text(
        env.spec_path.read_text(encoding="utf-8")
        + """
[[layers]]
id = "extra_layer"
source = "fx_ne"
file = "missing.geojson"
format = "geojson"
role = "non_us"
vintage = "ne-5.1"
level = "state_province"
key_scheme = "iso3166-2"
[layers.fields]
code = "iso_3166_2"
name = "name"
"""
    )
    with pytest.raises(PlacementError, match="absent"):
        PlacementEngine(env.pack_dir, env.registry_path, spec_path=drifted)


def test_engine_marks_a_geometry_the_registry_never_named(env, tmp_path: Path) -> None:
    """A bound minted under a jkey absent from the registry is dropped,
    counted — never a placement target (the registry is the naming
    authority)."""
    doc = json.loads(json.dumps(env.registry_doc))
    doc["rows"] = [r for r in doc["rows"] if r["jkey"] != "iso3166-2:US-MO"]
    eng = PlacementEngine(env.pack_dir, doc, spec_path=env.spec_path)
    assert eng.dropped_boundaries == 1
    # A point inside the dropped box still lands at its parent levels.
    (r,) = eng.place_many([_p("a", 39.0, -92.0)])
    assert "iso3166-2:US-MO" not in r.jurisdiction_chain
    assert r.jurisdiction_key == "iso3166-1:US"


# --------------------------------------------------------------------------- #
# The quality report (sig.placement-report/1)                                #
# --------------------------------------------------------------------------- #


def test_report_conservation_and_check_vocabulary(engine: PlacementEngine, env) -> None:
    inputs = [
        _p("c1", 34.0, -115.0, declared=("us.state_abbr", "CA")),
        _p("c2", 26.5, -81.5, declared=("us.state_abbr", "CA")),
        _p("c3", 0.1, 0.1),
        _p("c4", declared=("iso.3166_1_alpha2", "MN"), status="unreported", coord=False),
    ]
    report = build_report(_place(engine, *inputs), manifest=engine.pack_manifest)
    assert report["schema"] == "sig.placement-report/1"
    assert report["rules"] == PLACEMENT_RULESET
    assert report["check_vocabulary"] == list(PLACEMENT_CHECKS)
    assert report["totals"]["records"] == 4
    assert report["totals"]["placed"] + report["totals"]["unplaced"] == 4
    assert sum(report["by_check"].values()) == 4
    # Per-source conservation too.
    assert report["per_source"]["src_a"]["records"] == 4
    assert sum(report["per_source"]["src_a"]["by_check"].values()) == 4
    # Boundary provenance rides the report.
    assert report["boundary_pack"]["boundaries_root"] == env.manifest["boundaries_root"]
    assert report["boundary_pack"]["vintages"]["tiger"] == "tiger-2025"


def test_disclosures_count_both_dossier_sides(engine: PlacementEngine) -> None:
    """K4 §3.4: one CA-declared/FL-located record increments 'declared here,
    located elsewhere' on California AND 'located here, declared elsewhere'
    on Florida — the same disagreement counted on both dossiers."""
    results = _place(
        engine,
        _p("a", 26.5, -81.5, declared=("us.state_abbr", "CA")),
        _p("b", 26.6, -81.6, declared=("us.state_abbr", "CA")),
    )
    report = build_report(results, manifest=engine.pack_manifest)
    assert report["disclosures"] == [
        {
            "declared": "iso3166-2:US-CA",
            "located": "iso3166-2:US-FL",
            "records": 2,
        }
    ]
    both = report["disclosures_by_jurisdiction"]
    assert both["iso3166-2:US-CA"]["declared_here_located_elsewhere"] == 2
    assert both["iso3166-2:US-FL"]["located_here_declared_elsewhere"] == 2
    # Per-source breakdown present on both sides.
    assert both["iso3166-2:US-CA"]["by_source"]["src_a"]["declared_here_located_elsewhere"] == 2


def test_unplaced_never_counted_as_a_jurisdiction(engine: PlacementEngine) -> None:
    """K4-P4: unplaced is a quality state — 'unplaced' is a total, never a
    jkey bucket."""
    (r,) = _place(engine, _p("a", 0.1, 0.1))
    report = build_report([r], manifest=engine.pack_manifest)
    assert report["totals"]["unplaced"] == 1
    assert "unplaced" not in {
        k.split(":", 1)[0] for k in report.get("disclosures_by_jurisdiction", {})
    }


# --------------------------------------------------------------------------- #
# PlacementInput construction from a shaped site (site_input)                #
# --------------------------------------------------------------------------- #


def test_site_input_reads_declared_pair_from_value_json() -> None:
    """The declared (scheme, value) comes from the claim's persisted
    ``value_json`` pair (P35.18) — a legacy claim without it falls to the
    committed source-scheme config (or stays undeclared, never guessed)."""
    from datetime import date as _date

    from exports.shaping import ShapingClaim, shape_sites

    def _claim(cid: str, sid: str, pred: str, value: str, vj: dict | None = None):
        return ShapingClaim(
            claim_id=cid,
            subject_id=sid,
            predicate_id=pred,
            value_kind="value",
            value_text=value,
            value_num=None,
            raw_value=value,
            observed_at=_date(2026, 5, 1),
            sensitivity_tier=0,
            source_id="src_a",
            connector_name="camreg",
            effective_rights_id="r",
            effective_spdx="CC-BY-4.0",
            effective_redistributable="yes",
            effective_derivative_permitted="yes",
            effective_attribution="a",
            effective_terms_url="",
            value_json=json.dumps(vj) if vj is not None else None,
        )

    claims = [
        _claim("c1", "ent-1", "camera_latitude", "34.0"),
        _claim("c2", "ent-1", "camera_longitude", "-115.0"),
        _claim(
            "c3",
            "ent-1",
            "camera_jurisdiction",
            "CA",
            vj={"scheme": "us.state_abbr", "value": "CA"},
        ),
    ]
    sites = shape_sites(claims, entity_types={"ent-1": "deployment"})
    (site,) = sites
    by_id = {c.claim_id: c for c in claims}
    from exports.placement import site_input

    inp = site_input(site, claims_by_id=by_id)
    assert inp.declared == ("us.state_abbr", "CA")
    assert inp.lat == 34.0 and inp.lon == -115.0
    assert inp.point_status == "resolved"


def test_site_input_reads_claim_precision_stamp() -> None:
    """SIG-IDENT-004: a coordinate claim carrying LocatedPoint's
    ``value_json.precision`` guards the point even though the site's
    tier-derived precision label says ``full_precision``."""
    from datetime import date as _date

    from exports.placement import site_input
    from exports.shaping import ShapingClaim, shape_sites

    def _claim(cid, sid, pred, value, vj=None):
        return ShapingClaim(
            claim_id=cid,
            subject_id=sid,
            predicate_id=pred,
            value_kind="value",
            value_text=value,
            value_num=None,
            raw_value=value,
            observed_at=_date(2026, 5, 1),
            sensitivity_tier=0,
            source_id="src_a",
            connector_name="camreg",
            effective_rights_id="r",
            effective_spdx="CC-BY-4.0",
            effective_redistributable="yes",
            effective_derivative_permitted="yes",
            effective_attribution="a",
            effective_terms_url="",
            value_json=json.dumps(vj) if vj is not None else None,
        )

    claims = [
        _claim(
            "c1",
            "ent-1",
            "camera_latitude",
            "34.0",
            vj={"geometry": "34.0", "precision": "organization_centroid_or_unknown"},
        ),
        _claim("c2", "ent-1", "camera_longitude", "-115.0"),
    ]
    (site,) = shape_sites(claims, entity_types={"ent-1": "deployment"})
    inp = site_input(site, claims_by_id={c.claim_id: c for c in claims})
    assert inp.precision == "organization_centroid_or_unknown"


# --------------------------------------------------------------------------- #
# Engine determinism + basis vocabulary                                       #
# --------------------------------------------------------------------------- #


def test_place_many_is_deterministic_and_batched(engine: PlacementEngine) -> None:
    inputs = [
        _p("a", 34.0, -115.0, declared=("us.state_abbr", "CA")),
        _p("b", 39.0, -96.55),
        _p("c", -2.0, 110.0),
    ]
    first = engine.place_many(inputs)
    second = engine.place_many(inputs)
    assert [r.placement_check for r in first] == [r.placement_check for r in second]
    assert [r.jurisdiction_key for r in first] == [r.jurisdiction_key for r in second]
    assert all(r.placement_basis in PLACEMENT_BASIS or r.placement_basis is None for r in first)


def test_vintage_carried_on_every_placed_record(engine: PlacementEngine) -> None:
    """boundary_vintage names the boundary vintage behind the placement —
    the registry row's own vintage (SIG-ONTO-011, one vintage per release)."""
    (us_row, ne_row) = _place(engine, _p("a", 34.0, -115.0), _p("b", -2.0, 110.0))
    assert us_row.boundary_vintage == "tiger-2025"
    assert ne_row.boundary_vintage == "ne-5.1"


def test_build_spec_from_pack_manifest(engine: PlacementEngine) -> None:
    manifest = engine.pack_manifest
    assert manifest["pack_id"] == "boundaries-placement-fixture"
    assert manifest["gate"]["mode"] == "fixture-bypass"
