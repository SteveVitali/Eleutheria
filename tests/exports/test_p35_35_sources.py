# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.35 — the ``transparency/sources.json`` + ``transparency/counts.json``
release artifacts (J3 §3.3 item 3 + §4.3; K9 §3.2 C-1 + §5.4 C-6; J4 S-6/S-11;
SIG-TRANSP-D26/D27): the lifecycle partition, the S-11 gated rows, the S-6 URL
posture, honesty tokens, and the recompute contract.

Every assertion runs over fixture registry rows + fixture view tuples — no
database, no secrets, no living values.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from exports.transparency import (
    COUNTS_SCHEMA,
    GATED_SOURCE_ROW_FIELDS,
    LIFECYCLE_STATES,
    SOURCE_RECORD_SCHEMA,
    SOURCE_ROW_FIELDS,
    TRANSPARENCY_COUNTS_PATH,
    TRANSPARENCY_QUERIES,
    TRANSPARENCY_SOURCES_PATH,
    emit_transparency_artifacts,
    load_source_registry,
    recompute_counts,
)
from policy.transparency import (
    NO_UPSTREAM_URL,
    REDISTRIBUTION_LANES,
    TRANSPARENCY_SOURCE_VIEW_COLUMNS,
)

AT = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)


def _reg(
    sid: str,
    *,
    lane: str = "derived-only",
    part_viii_class: str = "none-known",
    ingestion_permitted: bool = False,
    compact_status: str = "no_response",
    custody_posture: str = "MIRROR",
    homepage_url: str = "https://example.org",
    reviewed: bool = True,
    spdx: str = "CC0-1.0",
    terms_url: str = "https://example.org/terms",
) -> dict[str, Any]:
    return {
        "name": f"Fixture {sid}",
        "source_kind": "government_portal",
        "homepage_url": homepage_url,
        "custody_posture": custody_posture,
        "compact_status": compact_status,
        "ingestion_permitted": ingestion_permitted,
        "cadence": "",
        "rights_reviewed_by": "licensing reviewer" if reviewed else "",
        "rights_reviewed_on": "2026-09-16" if reviewed else None,
        "rights": {
            "spdx": spdx,
            "attribution": "© Fixture",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": terms_url,
        },
        "redistribution": {
            "lane": lane,
            "evidence": f"rights/{sid}.md; J4 lane pass",
            "evidence_uri": f"docs/.../redistribution.csv#{sid}",
            "decision_authority": "D-J3-1 [B-19]",
            "review_needed": lane == "unknown",
            "part_viii_class": part_viii_class,
            "packet_limited": False,
            "sig_labelled_cc0": False,
        },
    }


def _emit(
    registry: dict[str, dict[str, Any]],
    *,
    claims=(),
    executions=(),
    captures=(),
    site_source_ids=(),
    view_rows=(),
):
    from exports.transparency import (
        TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
        TRANSPARENCY_RUN_VIEW_COLUMNS,
    )

    raw = {
        "transparency_runs": [
            tuple(r.get(c) for c in TRANSPARENCY_RUN_VIEW_COLUMNS) for r in executions
        ],
        "transparency_captures": [
            tuple(r.get(c) for c in TRANSPARENCY_CAPTURE_VIEW_COLUMNS) for r in captures
        ],
        "transparency_source_rights": [],
        "transparency_sources": [
            tuple(r.get(c) for c in TRANSPARENCY_SOURCE_VIEW_COLUMNS) for r in view_rows
        ],
        "transparency_predicates": [],
    }
    return emit_transparency_artifacts(
        raw,
        claims=claims,
        cadence_sources={},
        source_registry=registry,
        site_source_ids=site_source_ids,
        at=AT,
    )


def _sources(arts: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    return {r["source_id"]: r for r in doc["sources"]}


def test_full_row_fields_closed_and_schema():
    arts = _emit({"s1": _reg("s1", ingestion_permitted=True, lane="raw-ok")})
    row = _sources(arts)["s1"]
    assert set(row) == set(SOURCE_ROW_FIELDS)
    assert row["schema"] == SOURCE_RECORD_SCHEMA
    assert row["lifecycle_state"] == "permitted_not_ingested"
    assert row["lane"] == "raw-ok"
    assert row["lane_basis"] == "registry:[redistribution]"
    assert row["part_viii_class"] == "none-known"
    # C-6: the same two field names freshness.jsonl carries.
    assert "last_upstream_change" in row
    assert "last_sig_records_change" in row


def test_gated_source_is_an_s11_registry_only_row():
    arts = _emit({"g1": _reg("g1", lane="derived-only")})
    row = _sources(arts)["g1"]
    assert set(row) == set(GATED_SOURCE_ROW_FIELDS)
    assert row["lifecycle_state"] == "gated"
    assert row["status"] == "gated"
    assert row["reason_class"] in {
        "terms",
        "part_viii",
        "not_reviewed",
        "refused",
        "gated",
        "unknown_lane",
    }
    # Host only — never a full URL, never runs/captures/probe detail.
    assert row["homepage_url"] == "example.org"
    assert "last_successful_run" not in row
    assert "published_claims" not in row


def test_refused_source_shows_refused_lifecycle_and_reason():
    arts = _emit({"r1": _reg("r1", compact_status="permission_declined")})
    row = _sources(arts)["r1"]
    assert row["lifecycle_state"] == "refused"
    assert row["status"] == "refused"
    assert row["reason_class"] == "refused"


def test_restricted_lane_row_is_gated_with_terms_reason():
    arts = _emit({"x1": _reg("x1", lane="restricted", ingestion_permitted=True)})
    row = _sources(arts)["x1"]
    assert row["lane"] == "restricted"
    assert row["reason_class"] == "terms"
    # Registry-only even though the lane is recorded — S-11 binds.
    assert "last_successful_run" not in row


def test_unknown_lane_is_not_reviewed_or_unknown_lane_reason():
    arts = _emit({"u1": _reg("u1", lane="unknown", reviewed=False, ingestion_permitted=True)})
    row = _sources(arts)["u1"]
    assert row["lane"] == "unknown"
    assert row["reason_class"] in {"unknown_lane", "not_reviewed"}


def test_p8_1_class_shows_only_the_token_never_the_payload():
    arts = _emit(
        {
            "p1": _reg(
                "p1",
                lane="derived-only",
                part_viii_class="P8-1",
                ingestion_permitted=False,
            )
        }
    )
    row = _sources(arts)["p1"]
    assert row["reason_class"] == "part_viii"
    assert row["part_viii_class"] == "P8-1"
    # The class token publishes; nothing of the audited material does.
    assert "licence_terms" not in json.dumps(row)


def test_no_upstream_url_recorded_when_homepage_absent():
    arts = _emit(
        {
            "n1": _reg(
                "n1",
                lane="raw-ok",
                ingestion_permitted=True,
                homepage_url="",
                terms_url="",
            )
        }
    )
    row = _sources(arts)["n1"]
    assert row["ground_truth"]["homepage"] == NO_UPSTREAM_URL
    assert row["ground_truth"]["terms_url"] == NO_UPSTREAM_URL


def test_link_only_lane_publishes_host_and_path_hash_never_full_url():
    claims = [{"source_id": "l1", "predicate_id": "p", "observed_at": None}]
    arts = _emit({"l1": _reg("l1", lane="link-only", ingestion_permitted=True)}, claims=claims)
    row = _sources(arts)["l1"]
    assert row["lifecycle_state"] == "published"
    homepage = row["ground_truth"]["homepage"]
    assert homepage.startswith("example.org#path_sha256:")
    assert "https://example.org" not in json.dumps(row)


def test_raw_ok_gate_passed_publishes_the_full_scrubbed_url():
    claims = [{"source_id": "o1", "predicate_id": "p", "observed_at": None}]
    arts = _emit(
        {
            "o1": _reg(
                "o1",
                lane="raw-ok",
                ingestion_permitted=True,
                homepage_url="https://example.org/home?token=abc",
            )
        },
        claims=claims,
    )
    row = _sources(arts)["o1"]
    assert row["lifecycle_state"] == "published"
    assert row["published_claims"] == 1
    homepage = row["ground_truth"]["homepage"]
    # S-1 credential keys drop; the page itself survives for a gate-passed
    # raw-ok lane.
    assert homepage.startswith("https://example.org/home")
    assert "abc" not in homepage


def test_counts_partition_covers_every_registry_source_exactly_once():
    registry = {
        "published_src": _reg("published_src", lane="raw-ok", ingestion_permitted=True),
        "ingested_src": _reg("ingested_src", ingestion_permitted=True),
        "permitted_src": _reg("permitted_src", ingestion_permitted=True),
        "gated_src": _reg("gated_src"),
        "refused_src": _reg("refused_src", compact_status="permission_declined"),
    }
    claims = [{"source_id": "published_src", "predicate_id": "p", "observed_at": None}]
    executions = [
        {
            "report_id": "r",
            "run_id": "run",
            "source_id": "ingested_src",
            "completion_status": "ok",
            "claims_inserted": 3,
            "finished_at": AT,
        }
    ]
    arts = _emit(registry, claims=claims, executions=executions)
    counts = json.loads(arts[TRANSPARENCY_COUNTS_PATH])
    assert counts["schema"] == COUNTS_SCHEMA
    lifecycle = counts["lifecycle"]
    # Exactly one state per source; Σ = the registry row count.
    all_ids = [sid for st in LIFECYCLE_STATES for sid in lifecycle[st]["ids"]]
    assert sorted(all_ids) == sorted(registry)
    assert sum(lifecycle[st]["count"] for st in LIFECYCLE_STATES) == len(registry)
    assert lifecycle["published"]["ids"] == ["published_src"]
    assert lifecycle["ingested_not_published"]["ids"] == ["ingested_src"]
    assert lifecycle["permitted_not_ingested"]["ids"] == ["permitted_src"]
    assert lifecycle["gated"]["ids"] == ["gated_src"]
    assert lifecycle["refused"]["ids"] == ["refused_src"]
    assert lifecycle["withdrawn"]["count"] == 0


def test_counts_recompute_matches_emitted_numbers():
    registry = {
        "a": _reg("a", lane="raw-ok", ingestion_permitted=True),
        "b": _reg("b", lane="link-only", ingestion_permitted=True),
        "c": _reg("c"),
    }
    claims = [{"source_id": "a", "predicate_id": "p", "observed_at": None}]
    arts = _emit(registry, claims=claims, site_source_ids={"a"})
    doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    counts = json.loads(arts[TRANSPARENCY_COUNTS_PATH])
    recomputed = recompute_counts(doc["sources"])
    assert recomputed["registered"] == counts["universe"]["count"] == 3
    for st in LIFECYCLE_STATES:
        assert recomputed["partition"][st] == counts["lifecycle"][st]["ids"]
    assert recomputed["lanes"] == counts["attributes"]["lanes"]
    assert recomputed["site_records"] == counts["attributes"]["site_records"]["count"] == 1


def test_anomaly_source_ids_are_listed_never_counted():
    registry = {"real": _reg("real", ingestion_permitted=True)}
    claims = [{"source_id": "phantom", "predicate_id": "p", "observed_at": None}]
    arts = _emit(registry, claims=claims)
    counts = json.loads(arts[TRANSPARENCY_COUNTS_PATH])
    assert counts["universe"]["count"] == 1
    assert counts["anomalies"]["ids"] == ["phantom"]
    all_ids = [sid for st in LIFECYCLE_STATES for sid in counts["lifecycle"][st]["ids"]]
    assert "phantom" not in all_ids


def test_run_record_missing_flag_on_data_bearing_source():
    claims = [{"source_id": "m1", "predicate_id": "p", "observed_at": None}]
    arts = _emit({"m1": _reg("m1", lane="raw-ok", ingestion_permitted=True)}, claims=claims)
    row = _sources(arts)["m1"]
    assert "run_record_missing" in row["status_flags"]


def test_emitted_lanes_stay_in_the_closed_vocabulary():
    registry = {
        f"s{i}": _reg(f"s{i}", lane=lane) for i, lane in enumerate(sorted(REDISTRIBUTION_LANES))
    }
    arts = _emit(registry)
    for row in _sources(arts).values():
        assert row["lane"] in REDISTRIBUTION_LANES


def test_byte_stable_reexport():
    registry = {
        "a": _reg("a", lane="raw-ok", ingestion_permitted=True),
        "b": _reg("b"),
    }
    claims = [{"source_id": "a", "predicate_id": "p", "observed_at": None}]
    a1 = _emit(registry, claims=claims)
    a2 = _emit(registry, claims=claims)
    assert a1[TRANSPARENCY_SOURCES_PATH] == a2[TRANSPARENCY_SOURCES_PATH]
    assert a1[TRANSPARENCY_COUNTS_PATH] == a2[TRANSPARENCY_COUNTS_PATH]


def test_source_view_row_corroborates_review_and_p8():
    view_row = {c: None for c in TRANSPARENCY_SOURCE_VIEW_COLUMNS}
    view_row.update(
        {
            "source_id": "v1",
            "part_viii_class": "P8-3",
            "rights_decision_basis": "HG-03 2026-09-22 under GL-GATE-07",
            "rights_decision_reviewer": "licensing reviewer",
            "terms_reviewed": True,
        }
    )
    arts = _emit(
        {"v1": _reg("v1", lane="derived-only", part_viii_class="", ingestion_permitted=True)},
        view_rows=[view_row],
    )
    row = _sources(arts)["v1"]
    assert row["part_viii_class"] == "P8-3"
    assert row["review"]["basis"] == "HG-03 2026-09-22 under GL-GATE-07"
    assert row["review"]["reviewer_role"] == "licensing reviewer"


def test_transparency_queries_names_the_source_view():
    relation, sql = TRANSPARENCY_QUERIES["transparency_sources"]
    assert relation == "v_transparency_source"
    assert "select *" not in sql.lower()


def test_load_source_registry_missing_file_returns_none(tmp_path):
    assert load_source_registry(tmp_path / "absent.toml") is None


def test_load_source_registry_reads_blocks(tmp_path):
    p = tmp_path / "sources.toml"
    p.write_text(
        '[sources.fx]\nname = "Fixture"\n'
        '[sources.fx.rights]\nspdx = "CC0-1.0"\n'
        '[sources.fx.redistribution]\nlane = "derived-only"\n'
        'evidence = "x"\npart_viii_class = "P8-3"\n'
    )
    out = load_source_registry(p)
    assert out is not None
    assert out["fx"]["redistribution"]["lane"] == "derived-only"
    assert out["fx"]["redistribution"]["part_viii_class"] == "P8-3"
    assert out["fx"]["rights"]["spdx"] == "CC0-1.0"


def test_registry_absent_suppresses_the_source_artifacts():
    arts = emit_transparency_artifacts(
        {},
        claims=[],
        cadence_sources={},
        source_registry=None,
        at=AT,
    )
    assert TRANSPARENCY_SOURCES_PATH not in arts
    assert TRANSPARENCY_COUNTS_PATH not in arts
