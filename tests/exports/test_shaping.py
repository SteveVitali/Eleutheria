# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the compute-on-read export data-shaping layer (P27.3, LAUNCH.3).

Pure tests over fabricated ``ShapingClaim`` rows — no database. The DB-backed
end-to-end (seeded spine → ``run_shaping`` → ``PgReadStore`` enumeration reads)
lives in ``tests/db/test_shaping_spine.py``.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import pytest
from exports.shaping import (
    CONFLICTED_JURISDICTION,
    ENVELOPE_CONFLICTED,
    ENVELOPE_RESOLVED,
    ENVELOPE_UNREPORTED,
    SHAPING_SCHEMA_VERSION,
    UNASSERTED_JURISDICTION,
    UNRESOLVED_JURISDICTION,
    ShapingClaim,
    build_shaped_dataset,
    observation_envelope,
    parse_coordinate,
    shape_sharing_edges,
    shape_sites,
)
from inference.denominators import PublishedAggregate


def _claim(
    claim_id: str,
    subject_id: str,
    predicate_id: str,
    *,
    value_text: str | None = None,
    value_num: float | None = None,
    raw_value: str | None = None,
    value_kind: str = "value",
    source_id: str | None = "src_a",
    sensitivity_tier: int = 0,
    spdx: str = "CC0-1.0",
    redistributable: str = "yes",
    observed_at: date | None = date(2026, 5, 1),
) -> ShapingClaim:
    raw = raw_value
    if raw is None:
        raw = (
            value_text if value_text is not None else ("" if value_num is None else str(value_num))
        )
    return ShapingClaim(
        claim_id=claim_id,
        subject_id=subject_id,
        predicate_id=predicate_id,
        value_kind=value_kind,
        value_text=value_text,
        value_num=value_num,
        raw_value=raw,
        observed_at=observed_at,
        sensitivity_tier=sensitivity_tier,
        source_id=source_id,
        connector_name="camreg",
        # A rights id is per-licence in a real spine; derive it so a fabricated
        # licence mix is distinct the way the real one would be.
        effective_rights_id=f"rights-{spdx}",
        effective_spdx=spdx,
        effective_redistributable=redistributable,
        effective_derivative_permitted=redistributable,
        effective_attribution="",
        effective_terms_url="",
    )


def _row(c: ShapingClaim) -> tuple:
    return (
        c.claim_id,
        c.subject_id,
        c.predicate_id,
        c.value_kind,
        c.value_text,
        c.value_num,
        c.raw_value,
        c.observed_at,
        c.sensitivity_tier,
        c.source_id,
        c.connector_name,
        c.effective_rights_id,
        c.effective_spdx,
        c.effective_redistributable,
        c.effective_derivative_permitted,
        c.effective_attribution,
        c.effective_terms_url,
    )


def _raw(claims: list[ShapingClaim], **over: object) -> dict:
    base: dict[str, object] = {
        "shaping_claims": [_row(c) for c in claims],
        "subject_entities": [(s, "deployment") for s in sorted({c.subject_id for c in claims})],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1 closed=0",
    }
    base.update(over)
    return base


def _dataset(claims: list[ShapingClaim], **over: object):
    return build_shaped_dataset(
        _raw(claims, **over),
        as_of="2026-09-23",
        generated_at="2026-09-23T00:00:00Z",
        spine_label="unit",
    )


def _geo(
    subject: str,
    lat: str,
    lon: str,
    juris: str,
    *,
    source: str = "src_a",
    spdx: str = "CC0-1.0",
) -> list[ShapingClaim]:
    return [
        _claim(
            f"{subject}-lat",
            subject,
            "camera_latitude",
            value_text=lat,
            source_id=source,
            spdx=spdx,
        ),
        _claim(
            f"{subject}-lon",
            subject,
            "camera_longitude",
            value_text=lon,
            source_id=source,
            spdx=spdx,
        ),
        _claim(
            f"{subject}-jur",
            subject,
            "camera_jurisdiction",
            value_text=juris,
            source_id=source,
            spdx=spdx,
        ),
    ]


# --- parse_coordinate: the normalization path ------------------------------- #


def test_parse_coordinate_prefers_typed_value_num() -> None:
    p = parse_coordinate(
        predicate_id="camera_latitude",
        value_num="35.46756000",
        value_text="35.46756000",
        raw_value="35.46756000",
    )
    assert p.parse_ok and p.parsed == 35.46756
    assert p.raw_value == "35.46756000"  # raw literal preserved (SIG-PARSE-004)


def test_parse_coordinate_parses_text_when_no_typed_shadow() -> None:
    p = parse_coordinate(
        predicate_id="camera_longitude",
        value_num=None,
        value_text="-97.5164000",
        raw_value="-97.5164000",
    )
    assert p.parse_ok and p.parsed == pytest.approx(-97.5164)


def test_parse_coordinate_unparseable_keeps_raw() -> None:
    p = parse_coordinate(
        predicate_id="camera_latitude",
        value_num=None,
        value_text="not-a-number",
        raw_value="not-a-number",
    )
    assert not p.parse_ok and p.parsed is None and p.raw_value == "not-a-number"


def test_parse_coordinate_out_of_range_is_a_gap_not_a_guess() -> None:
    p = parse_coordinate(
        predicate_id="camera_latitude",
        value_num=None,
        value_text="123.45",
        raw_value="123.45",
    )
    assert not p.parse_ok and "out of range" in (p.note or "")


# --- observation envelopes: the §29 observation-level framing --------------- #


def test_envelope_unanimous_multi_source_resolves() -> None:
    env = observation_envelope(
        "camera_latitude",
        [
            _claim("a1", "s", "camera_latitude", value_text="35.46", source_id="dot_511"),
            _claim("a2", "s", "camera_latitude", value_text="35.46", source_id="osm"),
        ],
    )
    assert env.status == ENVELOPE_RESOLVED
    assert env.value == "35.46"
    assert env.n_observations == 2 and env.n_sources == 2
    assert env.dissenting_claim_ids == ()


def test_envelope_conflict_keeps_every_candidate() -> None:
    env = observation_envelope(
        "camera_latitude",
        [
            _claim("a1", "s", "camera_latitude", value_text="40.1", source_id="dot_511"),
            _claim("a2", "s", "camera_latitude", value_text="41.2", source_id="atlas"),
            _claim("a3", "s", "camera_latitude", value_text="40.1", source_id="osm"),
        ],
    )
    assert env.status == ENVELOPE_CONFLICTED
    assert env.value is None
    assert env.distinct_values == ("40.1", "41.2")
    assert set(env.considered_claim_ids) == {"a1", "a2", "a3"}
    # The modal value's backers support; the rest dissent — all stay visible.
    assert set(env.supporting_claim_ids) == {"a1", "a3"}
    assert env.dissenting_claim_ids == ("a2",)


def test_envelope_empty_is_unreported() -> None:
    env = observation_envelope("camera_latitude", [])
    assert env.status == ENVELOPE_UNREPORTED and env.value is None


def test_envelope_deterministic_regardless_of_input_order() -> None:
    claims = [
        _claim("a2", "s", "camera_jurisdiction", value_text="OK"),
        _claim("a1", "s", "camera_jurisdiction", value_text="TX"),
        _claim("a3", "s", "camera_jurisdiction", value_text="OK"),
    ]
    a = observation_envelope("camera_jurisdiction", claims)
    b = observation_envelope("camera_jurisdiction", list(reversed(claims)))
    assert a == b


# --- sites: geometry + tier reduction + dedup framing ----------------------- #


def test_site_point_with_lineage() -> None:
    sites = shape_sites(_geo("s1", "35.467560", "-97.516400", "OK"), entity_types={})
    assert len(sites) == 1
    site = sites[0]
    assert site.point_status == "resolved"
    assert site.latitude == pytest.approx(35.46756)
    assert site.longitude == pytest.approx(-97.5164)
    assert site.jurisdiction == "OK"
    assert site.observation_level == "observation"
    # Lineage: every claim that shaped the site is named (§21.6).
    assert set(site.claim_ids) == {"s1-lat", "s1-lon", "s1-jur"}
    assert "s1-lat" in site.lat_envelope.supporting_claim_ids


def test_site_conflicted_coordinates_never_pick_a_winner() -> None:
    claims = _geo("s1", "40.1", "-80.0", "NY")
    claims.append(_claim("s1-lat-b", "s1", "camera_latitude", value_text="41.2", source_id="atlas"))
    (site,) = shape_sites(claims, entity_types={})
    assert site.point_status == "conflicted"
    assert site.latitude is None and site.longitude is None
    assert "camera_latitude" in site.conflicted_predicates
    # Both candidates stay visible in the envelope.
    assert site.lat_envelope.distinct_values == ("40.1", "41.2")


def test_site_missing_coordinate_is_unreported_gap() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims = [c for c in claims if c.predicate_id != "camera_longitude"]
    (site,) = shape_sites(claims, entity_types={})
    assert site.point_status == "unreported"
    assert site.latitude is None and site.longitude is None


def test_site_unparseable_coordinate_is_a_gap_not_a_point() -> None:
    claims = [
        _claim("a", "s1", "camera_latitude", value_text="not-a-number"),
        _claim("b", "s1", "camera_longitude", value_text="-10.0"),
        _claim("c", "s1", "camera_jurisdiction", value_text="WA"),
    ]
    (site,) = shape_sites(claims, entity_types={})
    assert site.point_status == "unreported"
    assert site.latitude is None


def test_site_tier_reduction_goes_through_apply_tier() -> None:
    # The §19.4 mechanism is the only path a published coordinate takes: tier-1
    # claims (not publishable publicly) are excluded by the publishable filter,
    # but the reduction itself is exercised here via apply_tier semantics —
    # a claim-set fabricated at a publishable seam still reduces deterministically.
    from policy.sensitivity import apply_tier

    assert apply_tier(35.46756, -97.5164, 0) == (35.46756, -97.5164)
    t1 = apply_tier(35.46756, -97.5164, 1)
    assert t1 is not None and t1 != (35.46756, -97.5164)
    assert apply_tier(35.46756, -97.5164, 3) is None  # jurisdiction only


def test_non_publishable_claims_are_excluded_and_counted() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims += [
        _claim("x-lat", "s2", "camera_latitude", value_text="40.0", redistributable="UNDETERMINED"),
        _claim(
            "x-lon", "s2", "camera_longitude", value_text="-70.0", redistributable="UNDETERMINED"
        ),
        _claim(
            "x-jur", "s2", "camera_jurisdiction", value_text="TX", redistributable="UNDETERMINED"
        ),
    ]
    ds = _dataset(claims)
    assert [s.entity_id for s in ds.sites] == ["s1"]
    assert ds.claims_excluded_not_publishable == 3
    assert ds.claims_read == 6 and ds.claims_shaped == 3


def test_non_public_tier_claims_never_shape_a_site() -> None:
    claims = [
        _claim("a", "s1", "camera_latitude", value_text="35.46", sensitivity_tier=1),
        _claim("b", "s1", "camera_longitude", value_text="-97.51", sensitivity_tier=1),
        _claim("c", "s1", "camera_jurisdiction", value_text="OK", sensitivity_tier=1),
    ]
    ds = _dataset(claims)
    assert ds.sites == ()
    assert ds.claims_excluded_not_publishable == 3


def test_duplicate_coordinate_group_is_labelled_not_merged() -> None:
    claims = _geo("s1", "35.467560", "-97.516400", "OK", source="dot_511")
    claims += _geo("s2", "35.467560", "-97.516400", "OK", source="osm")
    ds = _dataset(claims)
    assert len(ds.sites) == 2  # observation-level: two subjects, both kept
    groups = {s.observation_group for s in ds.sites}
    assert groups == {"35.467560,-97.516400"}
    assert ds.observation_groups_multi_source == 1
    # The coverage aggregate measures the same group-level signal: both sites sit
    # in a coordinate cell observed by two sources (a per-site n_sources count
    # would read 0 — duplication lives at the group, not the subject).
    multi = next(a for a in ds.aggregates if "two or more sources" in a.label)
    assert multi.count == 2 and multi.denominator == 2


def test_licence_conflict_is_flagged_not_merged() -> None:
    # CC-BY-4.0 and ODbL-1.0 are mutually incompatible under compute_export_license
    # ({CC-BY-4.0} ∩ {ODbL-1.0} = ∅) — the site cannot ship as one row.
    claims = _geo("s1", "35.46", "-97.51", "OK", spdx="CC-BY-4.0")
    claims.append(_claim("extra", "s1", "camera_name", value_text="pole cam", spdx="ODbL-1.0"))
    (site,) = shape_sites(claims, entity_types={})
    assert site.licence_conflict is True
    assert set(site.licenses) == {"CC-BY-4.0", "ODbL-1.0"}
    # The rights provenance P27.4 needs is carried on the site.
    assert {r["spdx"] for r in site.rights} == {"CC-BY-4.0", "ODbL-1.0"}


def test_share_alike_propagates_without_conflict() -> None:
    # CC0 + ODbL resolves to ODbL (CC0 is relicensable to it) — no conflict, and
    # the share-alike licence rides along in the licence set.
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims.append(_claim("n", "s1", "camera_name", value_text="cam", spdx="ODbL-1.0"))
    (site,) = shape_sites(claims, entity_types={})
    assert site.licence_conflict is False
    assert set(site.licenses) == {"CC0-1.0", "ODbL-1.0"}


def test_site_label_from_camera_name_when_unanimous() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims.append(_claim("n1", "s1", "camera_name", value_text="I-35 @ 12th"))
    (site,) = shape_sites(claims, entity_types={})
    assert site.label == "I-35 @ 12th"


# --- jurisdiction grouping + coverage --------------------------------------- #


def test_jurisdiction_groups_include_unresolved_and_unasserted() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims += _geo("s2", "45.36", "-122.84", UNRESOLVED_JURISDICTION)
    claims.append(_claim("j1", "s3", "camera_operator", value_text="x"))  # not a shaping pred? no
    claims = [c for c in claims if c.predicate_id != "camera_operator"]
    claims.append(_claim("j2", "s3", "camera_name", value_text="cam"))  # no jurisdiction claim
    ds = _dataset(claims)
    buckets = {j.jurisdiction: j for j in ds.jurisdictions}
    assert "OK" in buckets and UNRESOLVED_JURISDICTION in buckets
    assert buckets[UNRESOLVED_JURISDICTION].is_unresolved
    assert UNASSERTED_JURISDICTION in buckets
    for j in ds.jurisdictions:
        assert isinstance(j.sites, PublishedAggregate)
        assert j.sites.count <= j.sites.denominator


def test_conflicted_jurisdiction_is_its_own_honest_bucket() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims.append(_claim("j2", "s1", "camera_jurisdiction", value_text="TX", source_id="atlas"))
    ds = _dataset(claims)
    buckets = {j.jurisdiction: j for j in ds.jurisdictions}
    assert CONFLICTED_JURISDICTION in buckets
    site = ds.sites[0]
    assert site.jurisdiction_status == ENVELOPE_CONFLICTED
    assert site.jurisdiction_envelope.distinct_values == ("OK", "TX")


def test_coverage_aggregates_are_denominated_never_totals() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims += _geo("s2", "45.36", "-122.84", "OR")
    claims.append(_claim("j", "s3", "camera_jurisdiction", value_text="WA"))  # no geo
    ds = _dataset(claims)
    for agg in ds.aggregates:
        assert isinstance(agg, PublishedAggregate)
        assert agg.count <= agg.denominator
        assert agg.phrase()  # denominator-bearing phrasing
    geo = ds.aggregates[0]
    assert geo.count == 2 and geo.denominator == 3 and geo.not_evaluable == 1


def test_coverage_metrics_match_the_web_contract() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    ds = _dataset(claims)
    forbidden = {"reality", "the population", "all jurisdictions", "all devices"}
    for m in ds.coverage_metrics:
        assert m["is_population_total"] is False
        assert m["denominator"].strip()
        assert m["denominator"].strip().lower() not in forbidden
        assert m["population_note"].strip()
        assert m["kind"] in {
            "counted_quantity",
            "records_derived_bound",
            "reconciliation_ratio",
            "survey_recall",
        }


# --- freshness + sharing edges ----------------------------------------------- #


def test_source_freshness_rows_and_not_evaluable() -> None:
    # The camera-registry predicates are registered (P30.2a, ADR-104), so their
    # staleness is evaluable against the registry volatility; a predicate the
    # ontology registry does not know is still honestly not-evaluable, never faked.
    claims = [
        *_geo("s1", "35.46", "-97.51", "OK"),
        _claim("s1-x", "s1", "unregistered_predicate_x", value_text="v"),
    ]
    ds = _dataset(
        claims,
        source_stats=[("src_a", 4, datetime(2026, 5, 2), 4)],
        source_runs=[("src_a", datetime(2026, 5, 2), "succeeded")],
    )
    (src,) = ds.sources
    assert src.freshness.source_id == "src_a"
    assert src.freshness.status == "ok"
    assert src.staleness_not_evaluable == 1  # only the unregistered predicate
    assert src.volatility_class == "SLOW"  # camera_latitude/longitude (2y) dominate
    row = src.freshness_row()
    assert set(row) == {
        "source",
        "last_successful_run",
        "last_content_change",
        "status",
        "stale_entity_count",
        "volatility_class",
    }


def test_sharing_edges_classified_into_access_kinds() -> None:
    edges = shape_sharing_edges(
        [
            ("c1", "s1", "configured_sharing_partner", "org:x", "dot_511", None),
            ("c2", "s1", "observed_data_use", "org:y", "osm", None),
            ("c3", "s1", "declared_data_policy", "org:z", "atlas", None),
            ("c4", "s1", "external_link", "org:w", "atlas", None),
        ]
    )
    kinds = {e.predicate_id: e.access_kind for e in edges}
    assert kinds["configured_sharing_partner"] == "configured_access"
    assert kinds["observed_data_use"] == "observed_use"
    assert kinds["declared_data_policy"] == "declared_policy"
    assert kinds["external_link"] == "unclassified"  # flagged, never coerced


# --- serialization + determinism -------------------------------------------- #


def test_geojson_ready_shape() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    ds = _dataset(claims)
    gj = ds.to_geojson()
    assert gj["type"] == "FeatureCollection"
    (feature,) = gj["features"]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    assert feature["geometry"]["coordinates"] == [
        pytest.approx(-97.51),
        pytest.approx(35.46),
    ]
    props = feature["properties"]
    assert props["observation_level"] == "observation"
    assert props["claim_ids"]
    # No per-person / per-plate / raw-precision leaking fields.
    for key in props:
        assert "plate" not in key and "person" not in key


def test_geojson_null_geometry_for_conflicted_site() -> None:
    claims = _geo("s1", "40.1", "-80.0", "NY")
    claims.append(_claim("b", "s1", "camera_latitude", value_text="41.2", source_id="atlas"))
    ds = _dataset(claims)
    (feature,) = ds.to_geojson()["features"]
    assert feature["geometry"] is None
    assert feature["properties"]["point_status"] == "conflicted"


def test_deterministic_output_bytes() -> None:
    claims = _geo("s1", "35.46", "-97.51", "OK")
    claims += _geo("s2", "45.36", "-122.84", UNRESOLVED_JURISDICTION)
    a = _dataset(claims)
    b = _dataset(list(reversed(claims)))
    assert a.to_json_str() == b.to_json_str()
    json.dumps(a.to_json())  # serialisable


def test_schema_version_and_metadata_carried() -> None:
    ds = _dataset(_geo("s1", "35.46", "-97.51", "OK"))
    out = ds.to_json()
    assert out["schema_version"] == SHAPING_SCHEMA_VERSION
    assert out["as_of"] == "2026-09-23"
    assert out["spine_watermark"] == "claims=1 closed=0"
    assert out["provenance"]["is_complete"] is True
