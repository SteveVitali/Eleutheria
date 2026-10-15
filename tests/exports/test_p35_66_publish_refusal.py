# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.66 — the publication refusal (SIG-PUB-011/013).

A ``candidate_asset`` subject — or any subject carrying the emit-stamped
``residential_parcel_flag`` — never reaches a public device layer at any
precision: shaping excludes it (counted honestly in
``candidate_subjects_excluded``), and each publish surface (sites geojson →
tiles, published records, the release search index, dossier packets) refuses
it as a **build error**, never a warning.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from exports.published_record import record_from_site_row
from exports.research_dossier import PACKET_SCHEMA, validate_packet
from exports.search_index import build_search_index
from exports.shaping import ShapingClaim, build_shaped_dataset, shape_sites
from exports.tiles import slim_geojson_for_tiles
from policy.sensitivity import CandidateAssetPublishRefused

from exports import shaping


def _claim(
    claim_id: str,
    subject_id: str,
    predicate_id: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=claim_id,
        subject_id=subject_id,
        predicate_id=predicate_id,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=0,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id="rights-CC0",
        effective_spdx="CC0-1.0",
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
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
        c.occurrence_capture_id,
        c.occurrence_retrieved_at,
        c.occurrence_bound_at,
        c.effective_rights_id,
        c.effective_spdx,
        c.effective_redistributable,
        c.effective_derivative_permitted,
        c.effective_attribution,
        c.effective_terms_url,
    )


def _geo(subject: str, *, source: str = "src_a") -> list[ShapingClaim]:
    return [
        _claim(f"{subject}-lat", subject, "camera_latitude", value_text="35.46", source_id=source),
        _claim(
            f"{subject}-lon", subject, "camera_longitude", value_text="-97.52", source_id=source
        ),
        _claim(
            f"{subject}-jur",
            subject,
            "camera_jurisdiction",
            value_text="OK",
            source_id=source,
        ),
    ]


def _raw(claims: list[ShapingClaim], subject_entities: list[tuple]) -> dict[str, Any]:
    return {
        "shaping_claims": [_row(c) for c in claims],
        "subject_entities": subject_entities,
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1 closed=0",
    }


def _dataset(raw: dict[str, Any]):
    return build_shaped_dataset(
        raw, as_of="2026-10-15", generated_at="2026-10-15T00:00:00Z", spine_label="unit"
    )


# --- shaping: refused subjects never become sites ------------------------------


def test_candidate_and_flagged_subjects_never_shape_sites() -> None:
    claims = _geo("plain") + _geo("cand") + _geo("flagged")
    ds = _dataset(
        _raw(
            claims,
            [
                ("plain", "deployment", False),
                ("cand", "candidate_asset", False),
                ("flagged", "physical_asset", True),
            ],
        )
    )
    assert {s.entity_id for s in ds.sites} == {"plain"}
    # The exclusion is counted honestly — both refused subjects carried
    # publishable shaping claims.
    assert ds.candidate_subjects_excluded == 2
    assert ds.to_json()["totals"]["candidate_subjects_excluded"] == 2
    assert ds.subjects_total == 1


def test_flagged_subject_with_no_publishable_claims_is_not_counted() -> None:
    claims = _geo("plain") + [
        _claim("x", "cand", "camera_latitude", value_text="1.0"),
    ]
    # A subject's claims must be publishable to count as an exclusion — a
    # sensitivity_tier > 0 claim never shapes, so refusing the subject is a
    # no-op on the totals.
    claims[3] = ShapingClaim(**{**claims[3].__dict__, "sensitivity_tier": 2})
    raw = _raw(claims, [("plain", "deployment", False), ("cand", "candidate_asset", False)])
    ds = _dataset(raw)
    assert {s.entity_id for s in ds.sites} == {"plain"}
    assert ds.candidate_subjects_excluded == 0  # refused, but nothing publishable


def test_shape_sites_refuses_subjects_by_param() -> None:
    claims = _geo("a") + _geo("b")
    sites = shape_sites(claims, entity_types={}, refused_subjects={"b"})
    assert {s.entity_id for s in sites} == {"a"}


def test_post_shape_guard_raises_on_a_smuggled_candidate_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense-in-depth: even if the refuse-list were bypassed upstream, the
    post-shape assertion fails the build rather than emit a candidate site."""
    real = shaping.shape_sites
    monkeypatch.setattr(
        shaping,
        "shape_sites",
        lambda claims, *, entity_types, refused_subjects=frozenset(): real(
            claims, entity_types=entity_types
        ),
    )
    raw = _raw(_geo("cand"), [("cand", "candidate_asset", False)])
    with pytest.raises(CandidateAssetPublishRefused):
        _dataset(raw)


def test_two_column_subject_rows_stay_back_compat() -> None:
    """A pre-P35.66 two-column subject_entities row set still shapes — the
    flag column is optional; the candidate-asset type check still binds."""
    ds = _dataset(_raw(_geo("cand"), [("cand", "candidate_asset")]))
    assert ds.sites == ()
    assert ds.candidate_subjects_excluded == 1


# --- published_record: the record projection refuses ----------------------------


def _site_row(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "entity_id": "ent-1",
        "entity_type": "deployment",
        "geometry": {"coordinates": [-97.5, 35.46], "type": "Point"},
        "point_status": "resolved",
        "claim_ids": [],
        "source_id": "src_a",
        "spdx": "CC0-1.0",
    }
    base.update(over)
    return base


def test_record_from_site_row_refuses_candidate_and_flagged() -> None:
    with pytest.raises(CandidateAssetPublishRefused, match="SIG-PUB-011"):
        record_from_site_row(
            _site_row(entity_type="candidate_asset"),
            compartment="c",
            license_id="L",
        )
    with pytest.raises(CandidateAssetPublishRefused, match="SIG-PUB-013"):
        record_from_site_row(
            _site_row(residential_parcel_flag=True),
            compartment="c",
            license_id="L",
        )


# --- search_index: the corpus refuses -------------------------------------------


def _index_row(entity_type: str = "deployment", flag: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {
        "record_key": f"comp:{entity_type}:ent-1",
        "entity_id": "ent-1",
        "entity_type": entity_type,
        "label": "A",
        "jurisdiction": "OK",
        "location_kind": "point",
        "source_id": "src_a",
        "claim_ids": [],
    }
    if flag:
        row["residential_parcel_flag"] = True
    return row


def test_build_search_index_refuses_flagged_and_candidate(tmp_path) -> None:
    out = tmp_path / "idx" / "search_index.sqlite"
    with pytest.raises(CandidateAssetPublishRefused):
        build_search_index(
            [_index_row(), _index_row(flag=True)],
            publication_id="p",
            compartment="comp",
            license_id="CC0-1.0",
            out=out,
        )
    assert not out.exists()  # refused BEFORE any bytes are written
    with pytest.raises(CandidateAssetPublishRefused):
        build_search_index(
            [_index_row(entity_type="candidate_asset")],
            publication_id="p",
            compartment="comp",
            license_id="CC0-1.0",
            out=out,
        )


# --- tiles: the slim path refuses before rendering ------------------------------


def _feature(**props: Any) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-97.5, 35.46]},
        "properties": {"entity_id": "e1", "entity_type": "deployment", **props},
    }


def test_slim_geojson_refuses_flagged_and_candidate_features() -> None:
    flagged = json.dumps(
        {"type": "FeatureCollection", "features": [_feature(residential_parcel_flag=True)]}
    ).encode()
    with pytest.raises(CandidateAssetPublishRefused):
        slim_geojson_for_tiles(flagged)
    candidate = json.dumps(
        {"type": "FeatureCollection", "features": [_feature(entity_type="candidate_asset")]}
    ).encode()
    with pytest.raises(CandidateAssetPublishRefused):
        slim_geojson_for_tiles(candidate)
    # A clean feature still slims to the render properties.
    ok = json.dumps({"type": "FeatureCollection", "features": [_feature()]}).encode()
    slimmed = json.loads(slim_geojson_for_tiles(ok))
    assert slimmed["features"][0]["properties"]["entity_type"] == "deployment"


# --- research_dossier: the packet contract refuses --------------------------------


def _packet(subject: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": PACKET_SCHEMA,
        "subject": subject,
        "records": records,
    }


def test_validate_packet_refuses_a_flagged_or_candidate_subject() -> None:
    clean = _packet(
        {"slug": "s", "label": "L", "jurisdiction": "J"},
        [{"record_kind": "claim", "residential_parcel_flag": False}],
    )
    assert validate_packet(clean) == []
    flagged_subject = _packet(
        {
            "slug": "s",
            "label": "L",
            "jurisdiction": "J",
            "entity_type": "candidate_asset",
        },
        [],
    )
    assert any("SIG-PUB-011" in p for p in validate_packet(flagged_subject))
    flagged_flag = _packet(
        {
            "slug": "s",
            "label": "L",
            "jurisdiction": "J",
            "residential_parcel_flag": True,
        },
        [],
    )
    assert any("SIG-PUB" in p for p in validate_packet(flagged_flag))
    flagged_claim = _packet(
        {"slug": "s", "label": "L", "jurisdiction": "J"},
        [{"record_kind": "claim", "residential_parcel_flag": True}],
    )
    assert any("SIG-PUB-013" in p for p in validate_packet(flagged_claim))
