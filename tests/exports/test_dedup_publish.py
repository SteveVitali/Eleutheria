# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.47 (SIG-CONF-005 / GQ-10): the dedup publication view + its export wiring.

Pure tests over fabricated shaping rows + a synthetic camera-site ER run — no
database. The matrix: the shared ``DedupView`` projects one record row per
post-collapse record (copies nested, never an excess row); the C0/C1/C2 basis
and L3 §5.2 display strings emit verbatim; possible-duplicate links list with
distance + reason and "not merged" wording; same-layer co-located records are
classed ``multi_view``, never duplicates; the count interval publishes per
dossier / map / the national figure through the dep's bound computation; and
the honest-absence states (``not_recorded`` / ``not_evaluable``) emit rather
than fabricate.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import build_spine_export

from exports import dedup

# --- fixtures --------------------------------------------------------------- #


def _claim(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    spdx: str = "CC-BY-4.0",
    redistributable: str = "yes",
    derivative_permitted: str = "yes",
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=0,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id=f"rights-{spdx}-{redistributable}-{derivative_permitted}",
        effective_spdx=spdx,
        effective_redistributable=redistributable,
        effective_derivative_permitted=derivative_permitted,
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://example/terms",
    )


def _site(
    subject: str, source_id: str, lat: str = "35.46", lon: str = "-97.51"
) -> list[ShapingClaim]:
    return [
        _claim(
            f"{subject}-{source_id}-lat",
            subject,
            "camera_latitude",
            value_text=lat,
            source_id=source_id,
        ),
        _claim(
            f"{subject}-{source_id}-lon",
            subject,
            "camera_longitude",
            value_text=lon,
            source_id=source_id,
        ),
        _claim(
            f"{subject}-{source_id}-jur",
            subject,
            "camera_jurisdiction",
            value_text="Oklahoma",
            source_id=source_id,
        ),
    ]


def _rows(claims: list[ShapingClaim]) -> list[tuple]:
    return [
        (
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
        for c in claims
    ]


def _build(claims: list[ShapingClaim], raw_over: dict | None = None):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    return build_spine_export(
        dataset,
        raw_over or {},
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )


def _run(*links: dict, declared_distance_m: float = 25.0) -> dict:
    """The synthetic latest-completed run as ``read_resolved_site_runs`` emits it."""
    applied = [
        (str(lk["left"]), str(lk["right"]))
        for lk in links
        if lk["disposition"] in ("auto_write", "human_accept")
    ]
    return {
        "run_key": "run-1",
        "observation_count": 0,
        "cluster_count": 0,
        "auto_write_tiers": [0, 1, 2],
        "summary": {"count_intervals": {"declared_distance_m": declared_distance_m}},
        "auto_write_edges": applied,
        "human_accept_edges": [],
        "resolved_edges": applied,
        "proposed_count": sum(1 for lk in links if lk["disposition"] == "proposed"),
        "cannot_link_count": sum(1 for lk in links if lk["disposition"] == "human_reject"),
        "refused_count": sum(1 for lk in links if lk["disposition"] == "refused"),
        "links": list(links),
    }


def _derived(
    left: str, right: str, tier: int, *, ref: str | None = "U-7", site_id: str | None = None
) -> dict:
    basis = (
        "same upstream layer ingested twice"
        if tier == 0
        else (
            f"copy of lin_a record {ref}, checked automatically"
            if tier == 1
            else "position-matched copy of lin_a (layer is a republish; matched by location)"
        )
    )
    return {
        "left": left,
        "right": right,
        "disposition": "auto_write",
        "relation_type": "derived_from",
        "tier": tier,
        "site_id": site_id or left,
        "evidence": {
            "site_id": site_id or left,
            "basis": basis,
            "sources": [f"src_{left[-1]}", f"src_{right[-1]}"],
            "shared_upstream_ref": ref,
            "distance_m": 0.5,
        },
    }


def _possible(
    left: str,
    right: str,
    *,
    dist: float = 20.0,
    sources: list[str] | None = None,
    reason: str = "possible_duplicate:inferential",
    disposition: str = "proposed",
) -> dict:
    srcs = sources or [f"src_{left[-1]}", f"src_{right[-1]}"]
    return {
        "left": left,
        "right": right,
        "disposition": disposition,
        "relation_type": "possible_duplicate",
        "tier": 3,
        "site_id": None,
        "evidence": {
            "site_ids": [left, right],
            "basis": (
                f"possible duplicate of {right}, {dist} m away; "
                "not merged: SIG cannot prove it is the same camera"
            ),
            "possible_duplicate_reason": reason,
            "distance_m": dist,
            "sources": srcs,
        },
    }


def _lineages(*pairs: tuple[str, str]) -> dict[str, tuple[str, ...]]:
    return {m: tuple(sorted(v for mm, v in pairs if mm == m)) for m, _ in pairs}


_MEMBERS = {"rec_a": "src_a", "rec_b": "src_b", "rec_c": "src_c"}
_SOURCES = {"src_a": "Alpha DOT", "src_b": "Beta Mirror", "src_c": "Gamma Feed"}


# --- the shared DedupView ---------------------------------------------------- #


def test_copies_carry_c0_c1_c2_bases_verbatim() -> None:
    run = _run(
        _derived("rec_a", "rec_b", 0),
        _derived("rec_a", "rec_c", 1, ref="U-7"),
        _derived("rec_a", "rec_d", 2, ref=None),
    )
    members = {**_MEMBERS, "rec_d": "src_d"}
    view = dedup.build_dedup_view(
        [run], member_records=members, member_lineages=None, source_names=_SOURCES
    )
    assert view is not None
    copies = {e["record"]: e for e in view.record_fields("rec_a")["copies"]}
    assert copies["rec_b"]["basis"] == "C0"
    assert copies["rec_c"]["basis"] == "C1"
    assert copies["rec_d"]["basis"] == "C2"
    assert "checked automatically" in copies["rec_c"]["basis_text"]
    assert copies["rec_c"]["upstream_id"] == "U-7"
    # The L3 §5.2 copy display — verbatim.
    assert copies["rec_c"]["display"] == (
        "Also published by Gamma Feed (a copy of the same upstream record, "
        "id U-7, checked automatically)."
    )


def test_possible_duplicate_lists_not_merged_with_distance_and_reason() -> None:
    run = _run(
        _possible("rec_a", "rec_c", dist=20.0, reason="possible_duplicate:soft_conflict:name")
    )
    view = dedup.build_dedup_view(
        [run], member_records=_MEMBERS, member_lineages=None, source_names=_SOURCES
    )
    assert view is not None
    fields = view.record_fields("rec_a")
    (pd,) = fields["possible_duplicates"]
    assert pd["record"] == "rec_c"
    assert pd["distance_m"] == 20.0
    assert pd["reason"] == "possible_duplicate:soft_conflict:name"
    assert "not merged" in pd["display"]
    assert "verified" not in pd["display"] and "certified" not in pd["display"]
    # The linked record names the pair back — the listing is symmetric.
    (back,) = view.record_fields("rec_c")["possible_duplicates"]
    assert back["record"] == "rec_a"


def test_same_layer_colocated_is_multi_view_never_duplicate() -> None:
    run = _run(
        _possible("rec_a", "rec_b", dist=3.0, sources=["src_a", "src_a"]),
    )
    view = dedup.build_dedup_view(
        [run], member_records=_MEMBERS, member_lineages=None, source_names=_SOURCES
    )
    assert view is not None
    fields = view.record_fields("rec_a")
    assert fields["possible_duplicates"] == []
    (mv,) = fields["multi_view"]
    assert mv["record"] == "rec_b"
    assert "multi-view" in mv["display"].lower() or "Multi-view" in mv["display"]
    assert "duplicate" not in mv["display"].replace("not duplicates", "")


def test_independent_lineages_count_distinct_classes() -> None:
    run = _run(_derived("rec_a", "rec_b", 1))
    lineages = {
        "rec_a": ("lin_a",),
        "rec_b": ("lin_b",),
        "rec_c": ("lin_c",),
    }
    view = dedup.build_dedup_view(
        [run], member_records=_MEMBERS, member_lineages=lineages, source_names=_SOURCES
    )
    assert view is not None
    fields = view.record_fields("rec_a")
    assert fields["n_independent_lineages"] == 2
    assert (
        fields["n_independent_lineages_display"] == "Seen independently by 2 sources: lin_a, lin_b."
    )
    assert view.record_fields("rec_c")["n_independent_lineages"] == 1


def test_missing_lineage_read_is_not_evaluable_never_zero() -> None:
    run = _run(_derived("rec_a", "rec_b", 1))
    view = dedup.build_dedup_view(
        [run], member_records=_MEMBERS, member_lineages=None, source_names=_SOURCES
    )
    assert view is not None
    n = view.record_fields("rec_a")["n_independent_lineages"]
    assert isinstance(n, dict) and "not_evaluable" in n


def test_no_run_is_not_recorded_never_fabricated() -> None:
    assert (
        dedup.build_dedup_view(
            [], member_records=_MEMBERS, member_lineages={}, source_names=_SOURCES
        )
        is None
    )
    fields = dedup.not_recorded_fields()
    for key in ("site_id", "copies", "possible_duplicates", "multi_view", "n_independent_lineages"):
        assert isinstance(fields[key], dict) and "not_recorded" in fields[key]
    interval = dedup.interval_block(None, _MEMBERS)
    assert "not_evaluable" in interval and "upper" not in interval


def test_interval_uses_the_deps_bound_computation() -> None:
    # upper: applied edges only; lower: + every possible link within the
    # declared distance. The 40 m link stays OUTSIDE the lower bound.
    run = _run(
        _derived("rec_a", "rec_b", 1),
        _possible("rec_a", "rec_c", dist=20.0),
        _possible("rec_a", "rec_d", dist=40.0),
    )
    members = {**_MEMBERS, "rec_d": "src_d"}
    view = dedup.build_dedup_view(
        [run], member_records=members, member_lineages=None, source_names=_SOURCES
    )
    assert view is not None
    iv = dedup.interval_block(view, members)
    # {a,b} + {c} + {d} = 3 upper; the 20 m link additionally merges a-c → 2 lower.
    assert (iv["lower"], iv["upper"], iv["records"]) == (2, 3, 4)
    assert "between 2 and 3 listed cameras" in iv["display"]


def test_inflation_measured_published_as_measured() -> None:
    run = _run(_derived("rec_a", "rec_b", 1))
    view = dedup.build_dedup_view(
        [run], member_records=_MEMBERS, member_lineages=None, source_names=_SOURCES
    )
    inf = dedup.dossier_inflation(view, _MEMBERS, published_rows=2)
    assert inf["published_rows"] == 2
    assert inf["lineage_roots"] == 2
    assert inf["measured"] == pytest.approx(1.0)


def test_withheld_member_never_leaks_through_a_link() -> None:
    # rec_b unpublished → the a-b derived edge is invisible: a and c keep
    # their own singleton site ids and no copy names rec_b.
    run = _run(
        _derived("rec_a", "rec_b", 1),
        _possible("rec_a", "rec_c", dist=10.0),
    )
    view = dedup.build_dedup_view(
        [run],
        member_records={"rec_a": "src_a", "rec_c": "src_c"},
        member_lineages=None,
        source_names=_SOURCES,
    )
    assert view is not None
    fields = view.record_fields("rec_a")
    assert fields["copies"] == []
    assert fields["site_id"] == "rec_a"
    # And a withheld site root never leaks as a site_id either.
    run2 = _run(_derived("rec_b", "rec_a", 1))
    view2 = dedup.build_dedup_view(
        [run2],
        member_records={"rec_a": "src_a", "rec_c": "src_c"},
        member_lineages=None,
        source_names=_SOURCES,
    )
    assert view2 is not None
    assert view2.record_fields("rec_a")["site_id"] == "rec_a"


# --- the export wiring ------------------------------------------------------- #


def _raw_with_run() -> dict:
    run = _run(
        _derived("rec_a", "rec_b", 1, ref="U-7"),
        _possible("rec_a", "rec_c", dist=20.0),
    )
    lineage = [
        ("rec_a-src_a-lat", "lin_a"),
        ("rec_a-src_a-lon", "lin_a"),
        ("rec_a-src_a-jur", "lin_a"),
        ("rec_b-src_b-lat", "lin_b"),
        ("rec_b-src_b-lon", "lin_b"),
        ("rec_b-src_b-jur", "lin_b"),
        ("rec_c-src_c-lat", "lin_c"),
        ("rec_c-src_c-lon", "lin_c"),
        ("rec_c-src_c-jur", "lin_c"),
    ]
    return {"materialized_site_runs": [run], "claim_lineage": lineage}


def _claims() -> list[ShapingClaim]:
    return _site("rec_a", "src_a") + _site("rec_b", "src_b") + _site("rec_c", "src_c")


def _site_rows(export) -> list[dict]:
    rows = []
    for path, data in export.bundle.artifact_bytes.items():
        if path.endswith("sites.jsonl"):
            rows.extend(json.loads(line) for line in data.decode().splitlines() if line.strip())
    return rows


def test_export_emits_one_row_per_record_with_copies_nested() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    rows = _site_rows(export)
    assert sorted(r["entity_id"] for r in rows) == ["rec_a", "rec_c"]
    (a,) = [r for r in rows if r["entity_id"] == "rec_a"]
    assert a["site_id"] == "rec_a"
    (copy,) = a["copies"]
    assert copy["record"] == "rec_b" and copy["basis"] == "C1"
    (pd,) = a["possible_duplicates"]
    assert pd["record"] == "rec_c" and "not merged" in pd["display"]
    assert a["n_independent_lineages"] == 2
    (c,) = [r for r in rows if r["entity_id"] == "rec_c"]
    assert c["copies"] == []
    assert c["site_id"] == "rec_c"
    # ``merged_into`` is never written anywhere.
    assert "merged_into" not in a and "merged_into" not in c


def test_export_rows_without_run_carry_not_recorded() -> None:
    export = _build(_claims())
    rows = _site_rows(export)
    assert len(rows) == 3  # no collapse → every record still emits
    for r in rows:
        assert isinstance(r["site_id"], dict) and "not_recorded" in r["site_id"]
        assert isinstance(r["copies"], dict) and "not_recorded" in r["copies"]


def test_map_draws_canonical_members_and_the_interval() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    m = json.loads(export.web_artifacts["web/map.json"].decode())
    assert sorted(a["id"] for a in m["assets"]) == ["rec_a", "rec_c"]
    iv = m["count_interval"]
    assert (iv["records"], iv["lower"], iv["upper"]) == (3, 1, 2)
    assert "between 1 and 2 listed cameras" in iv["display"]
    (a,) = [a for a in m["assets"] if a["id"] == "rec_a"]
    assert a["site_id"] == "rec_a"
    assert a["n_independent_lineages"] == 2


def test_national_coverage_metric_publishes_the_interval() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    cov = json.loads(export.web_artifacts["web/coverage.json"].decode())
    (metric,) = [m for m in cov if m["id"] == "resolved_sites"]
    assert "between 1 and 2 listed cameras" in metric["value"]
    assert metric["count_interval"]["lower"] == 1
    assert metric["count_interval"]["upper"] == 2


def test_dossier_sources_publish_interval_and_measured_inflation() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    docs = [
        json.loads(export.web_artifacts[p].decode())
        for p in export.web_artifacts
        if "dossier_sources" in p and p.endswith(".json")
    ]
    assert docs
    for doc in docs:
        iv = doc["totals"]["count_interval"]
        assert iv["records"] == 3 and iv["upper"] == 2 and iv["lower"] == 1
        inf = doc["totals"]["dossier_inflation_vs_lineage_roots"]
        # Two emitted rows (rec_a + rec_c) against two lineage roots → 1.0×.
        assert inf["published_rows"] == 2 and inf["lineage_roots"] == 2
        assert inf["measured"] == pytest.approx(1.0)
        (fig,) = [f for f in doc["figures"] if f["figure_id"] == "listed_cameras"]
        assert "between" in fig["display"]


def test_nested_copy_claim_anchors_stay_emittable() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    rc_paths = [p for p in export.web_artifacts if p.endswith("record_claims.jsonl")]
    claim_ids = {
        r["claim_id"]
        for p in rc_paths
        for r in (
            json.loads(line)
            for line in export.web_artifacts[p].decode().splitlines()
            if line.strip()
        )
    }
    # rec_b nests under rec_a — its claims still anchor (never erased).
    assert "rec_b-src_b-lat" in claim_ids


def test_published_record_projects_the_dedup_block() -> None:
    export = _build(_claims(), raw_over=_raw_with_run())
    rows = _site_rows(export)
    from exports.published_record import record_from_site_row

    rec = record_from_site_row(
        {k: v for k, v in rows[0].items()}, compartment="apache", license_id="CC-BY-4.0"
    )
    assert rec.dedup is not None
    assert rec.dedup["site_id"] == "rec_a"
    assert rec.dedup["copies"][0]["record"] == "rec_b"
    # A pre-P35.47 row (no dedup fields) keeps the sparse block.
    bare = record_from_site_row(
        {k: v for k, v in rows[0].items() if k not in rec.dedup},
        compartment="apache",
        license_id="CC-BY-4.0",
    )
    assert bare.dedup is None
    assert "dedup" not in bare.id_free_doc()
