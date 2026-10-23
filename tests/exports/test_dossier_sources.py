# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.44 — the ``sig.dossier-sources/1`` contribution artifacts (T3–T11, T14).

Fixture-level tests of the shared accumulation
(:func:`exports.dossier_sources.accumulate_dossier_contributions`) and its
two consumers — the dossier JSON + ``.runs.jsonl.gz`` artifacts and the
``contributions[]`` mirror on ``transparency/sources.json`` (TRANSP-040):
one computation, two surfaces, identical numbers.

Every assertion runs over fixture rows — no database, no secrets, no
living values. The ``_Engine`` stand-in replaces ``placement@1``'s
``PlacementResult`` (this row reads its output, never re-derives it).
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime
from typing import Any

import pytest
from exports.dossier_sources import (
    DOSSIER_SOURCES_QUERIES,
    RUNS_ROW_SCHEMA,
    SCHEMA,
    accumulate_dossier_contributions,
)

AT = "2026-10-21"

_JROWS: dict[str, dict[str, Any]] = {
    "iso3166-1:US": {
        "jkey": "iso3166-1:US",
        "name": "United States",
        "level": "country",
        "parent": None,
        "vintage": "pl94-2020",
        # P35.45: the canonical identifier mints the slug-path segment —
        # ``usa`` for the country, ``ca`` under it, NAMELSAD+GEOID at county.
        "identifiers": [
            {"kind": "canonical", "scheme": "iso3166-1", "value": "US"},
            {"kind": "alternate", "scheme": "iso3166-1-a3", "value": "USA"},
        ],
    },
    "iso3166-2:US-CA": {
        "jkey": "iso3166-2:US-CA",
        "name": "California",
        "level": "state_province",
        "parent": "iso3166-1:US",
        "vintage": "pl94-2020",
        "identifiers": [{"kind": "canonical", "scheme": "iso3166-2", "value": "US-CA"}],
    },
    "us.census.geoid.county:06037": {
        "jkey": "us.census.geoid.county:06037",
        "name": "Los Angeles County",
        "level": "county",
        "parent": "iso3166-2:US-CA",
        "vintage": "pl94-2020",
        "identifiers": [
            {"kind": "canonical", "scheme": "us.census.geoid.county", "value": "06037"}
        ],
    },
}

#: P35.45 slug paths for the fixture keys — the artifact paths and the
#: ``dossier_slug`` mirror field carry these (never the flat P35.44 slug).
_SLUGS: dict[str, str] = {
    "iso3166-1:US": "usa",
    "iso3166-2:US-CA": "usa/ca",
    "us.census.geoid.county:06037": "usa/ca/los-angeles-county-06037",
}
_CHAINS: dict[str, tuple[str, ...]] = {
    "us.census.geoid.county:06037": (
        "iso3166-1:US",
        "iso3166-2:US-CA",
        "us.census.geoid.county:06037",
    ),
    "iso3166-2:US-CA": ("iso3166-1:US", "iso3166-2:US-CA"),
    "iso3166-1:US": ("iso3166-1:US",),
}


class _Engine:
    """The ``placement@1`` accessor surface the plan reads — jurisdiction
    metadata + ancestor chains (P35.19's output, never re-derived)."""

    def jurisdiction_row(self, jkey: str) -> dict[str, Any] | None:
        return _JROWS.get(jkey)

    def ancestor_chain(self, jkey: str) -> tuple[str, ...]:
        return _CHAINS.get(jkey, ())


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _sighting(
    claim: str,
    subject: str,
    predicate: str,
    source: str,
    first: str,
    last: str,
    first_run: str,
    last_run: str,
    runs: int,
    links: int,
    run_ids: list[str],
    months: list[str],
    artifacts: list[str] | None = None,
    actual: bool = True,
) -> tuple[Any, ...]:
    """One ``claim_sightings`` row in ``CLAIM_SIGHTINGS_COLUMNS`` order."""
    return (
        claim,
        subject,
        predicate,
        source,
        _ts(first),
        _ts(last),
        first_run,
        last_run,
        runs,
        links,
        actual,
        list(run_ids),
        list(months),
        list(artifacts or []),
    )


def _run(
    run_id: str,
    source: str,
    started: str,
    finished: str,
    status: str = "ok",
) -> tuple[Any, ...]:
    """One ``transparency_runs`` row in TRANSPARENCY_RUN_VIEW_COLUMNS order."""
    from policy.transparency import TRANSPARENCY_RUN_VIEW_COLUMNS

    cols = {
        "report_id": f"rep-{run_id}",
        "run_id": run_id,
        "source_id": source,
        "link_basis": "live",
        "clock_basis": "db",
        "shared_run": False,
        "started_at": _ts(started),
        "finished_at": _ts(finished),
        "duration_seconds": 3600,
        "completion_status": status,
        "claims_considered": 10,
        "claims_inserted": 10,
        "claims_duplicate": 0,
        "fetches": 10,
        "records_emitted": 10,
        "robots_outcomes": None,
        "refusal_classes": None,
        "rate_limit_events": 0,
        "disappearances": 0,
        "document_outcomes": None,
        "quota_reached": False,
        "budget_reached": False,
        "error_class": None,
        "per_fetch": None,
        "connector_name": "sig.test",
        "connector_version": "0.0.0",
        "code_commit": "deadbeef",
        "recorded_at": _ts(finished),
    }
    return tuple(cols.get(c) for c in TRANSPARENCY_RUN_VIEW_COLUMNS)


def _site(
    subject: str,
    source: str,
    *,
    jkey: str | None = "iso3166-2:US-CA",
    entity_type: str = "deployment",
    technology: str | None = None,
    basis: str = "declared",
    check: str = "no_point",
    point_status: str = "unresolved",
) -> tuple[str, str, dict[str, Any]]:
    """One ``(compartment, source_id, site_record)`` input row."""
    data: dict[str, Any] = {
        "entity_id": subject,
        "entity_type": entity_type,
        "technology": technology,
        "jurisdiction": jkey,
        "point_status": point_status,
        "source_id": source,
        "jurisdiction_key": jkey,
        "jurisdiction_chain": list(_CHAINS.get(jkey or "", ())),
        "placement_basis": basis,
        "placement_check": check,
    }
    return ("sig_graph", source, data)


def _plan(**kw: Any):
    return accumulate_dossier_contributions(
        release={
            "label": "sig-2026-10-21.1",
            "publication_id": None,
            "as_of_world": "2026-10-21T00:00:00Z",
        },
        ruleset_version="p27.3/1.0.0",
        as_of=AT,
        **kw,
    )


def _docs(plan) -> dict[str, dict[str, Any]]:
    arts = plan.render({})
    return {
        p[len("web/dossier_sources/") : -len(".json")]: json.loads(arts[p])
        for p in arts
        if p.endswith(".json")
    }


@pytest.fixture
def world() -> dict[str, Any]:
    """A small world: one county-placed record shared by two sources, one
    admin-1-placed record, one declared-only record; three runs per source
    plus a ``partial`` run that must never win ``latest_run``."""
    sightings = [
        # srcA on s1 — two sightings across two runs (a real re-sighting).
        _sighting(
            "c1",
            "s1",
            "camera_latitude",
            "srcA",
            "2026-05-01T00:00:00Z",
            "2026-06-01T00:00:00Z",
            "run-a1",
            "run-a2",
            2,
            2,
            ["run-a1", "run-a2"],
            ["2026-05-01 00:00:00+00", "2026-06-01 00:00:00+00"],
            ["art-a"],
        ),
        _sighting(
            "c2",
            "s1",
            "camera_longitude",
            "srcA",
            "2026-05-01T00:00:00Z",
            "2026-05-01T00:00:00Z",
            "run-a1",
            "run-a1",
            1,
            1,
            ["run-a1"],
            ["2026-05-01 00:00:00+00"],
            ["art-a"],
        ),
        # srcB on the SAME subject s1 — the multi-source record (T9).
        _sighting(
            "c3",
            "s1",
            "camera_latitude",
            "srcB",
            "2026-05-15T00:00:00Z",
            "2026-05-15T00:00:00Z",
            "run-b1",
            "run-b1",
            1,
            1,
            ["run-b1"],
            ["2026-05-01 00:00:00+00"],
            ["art-b"],
        ),
        # srcB on s2 — an admin-1-placed record.
        _sighting(
            "c4",
            "s2",
            "camera_technology",
            "srcB",
            "2026-05-15T00:00:00Z",
            "2026-06-15T00:00:00Z",
            "run-b1",
            "run-b2",
            2,
            2,
            ["run-b1", "run-b2"],
            ["2026-05-01 00:00:00+00", "2026-06-01 00:00:00+00"],
            ["art-b2"],
        ),
        # srcC on s3 — single-link claims across two ok runs (T6).
        _sighting(
            "c5",
            "s3",
            "camera_latitude",
            "srcC",
            "2026-05-10T00:00:00Z",
            "2026-05-10T00:00:00Z",
            "run-c1",
            "run-c1",
            1,
            1,
            ["run-c1"],
            ["2026-05-01 00:00:00+00"],
            ["art-c"],
        ),
    ]
    sites = [
        _site(
            "s1",
            "srcA",
            jkey="us.census.geoid.county:06037",
            technology="alpr",
            basis="point_in_polygon",
            check="consistent",
            point_status="resolved",
        ),
        _site(
            "s1",
            "srcB",
            jkey="us.census.geoid.county:06037",
            technology="alpr",
            basis="point_in_polygon",
            check="consistent",
            point_status="resolved",
        ),
        _site("s2", "srcB", jkey="iso3166-2:US-CA", technology="vls"),
        _site("s3", "srcC", jkey="iso3166-2:US-CA"),
    ]
    runs = [
        _run("run-a1", "srcA", "2026-05-01T00:00:00Z", "2026-05-01T01:00:00Z"),
        _run("run-a2", "srcA", "2026-06-01T00:00:00Z", "2026-06-01T01:00:00Z"),
        _run("run-a3", "srcA", "2026-07-01T00:00:00Z", "2026-07-01T01:00:00Z", "partial"),
        _run("run-b1", "srcB", "2026-05-15T00:00:00Z", "2026-05-15T01:00:00Z"),
        _run("run-b2", "srcB", "2026-06-15T00:00:00Z", "2026-06-15T01:00:00Z"),
        _run("run-c1", "srcC", "2026-05-10T00:00:00Z", "2026-05-10T01:00:00Z"),
        _run("run-c2", "srcC", "2026-06-10T00:00:00Z", "2026-06-10T01:00:00Z"),
    ]
    weights = [
        {
            "claim_id": c,
            "source_id": s,
            "predicate_id": p,
            "source_reliability": "R1",
            "claim_directness": "D1",
            "artifact_integrity": "I1",
            "observed_at": _ts("2026-05-01T00:00:00Z"),
            "spdx": "CC0-1.0",
        }
        for c, s, p in (
            ("c1", "srcA", "camera_latitude"),
            ("c3", "srcB", "camera_latitude"),
            ("c4", "srcB", "camera_technology"),
            ("c5", "srcC", "camera_latitude"),
        )
    ]
    return {
        "sightings_rows": sightings,
        "site_rows": sites,
        "run_rows": runs,
        "contradictions": [],
        "weight_rows": weights,
        "lineage_rows": [("c1", "ns-1"), ("c4", "ns-2")],
        "placement": _Engine(),
    }


# --- T1 (shape of the read, the rest lives in tests/unit's closure test) ----


def test_t1_export_queries_key_shape():
    relation, sql = DOSSIER_SOURCES_QUERIES["claim_sightings"]
    assert relation == "v_claim_sightings"
    for token in (
        "GROUP BY 1,2,3,4",
        "{PUB_CLAIM_GATE}",
        "{PUB_ARTIFACT_GATE}",
        "{CAPTURE_SEAL_GATE}",
        "{SIGHTING_BOUND}",
        "min(c.retrieved_at)",
        "count(DISTINCT c.run_id)",
        "count(*)",
        "bool_or(c.binding_status = 'actual_capture')",
    ):
        assert token in sql


# --- T3: the tested invariants ------------------------------------------------


def test_t3_contribution_math_reconciles(world):
    docs = _docs(_plan(**world))
    for slug, doc in docs.items():
        totals = doc["totals"]
        sources = doc["sources"]
        # Σ sources[].claims = totals.claims (a claim belongs to exactly one
        # source — the sum can never over-count).
        assert sum(s["claims"] for s in sources) == totals["claims"], slug
        # Σ sources[].records == totals.records *while the sum_rule is sum*;
        # under "distinct" the by_source overlap is the disclosed fact.
        fig = {f["figure_id"]: f for f in doc["figures"]}
        rec = fig["records"]
        if rec["sum_rule"] == "sum":
            assert sum(s["records"] for s in sources) == totals["records"], slug
            assert rec["value"] == totals["records"]
        # Every figure's by_source reconciles to its value under its rule.
        for f in doc["figures"]:
            summed = sum(b["value"] for b in f["by_source"])
            if f["sum_rule"] == "sum":
                assert summed == f["value"], (slug, f["figure_id"])
            else:
                assert f["sum_rule"] == "distinct"
                assert f.get("sum_disclosure")


# --- T4: ancestor roll-up ------------------------------------------------------


def test_t4_county_record_rolls_to_admin1_and_country(world):
    docs = _docs(_plan(**world))
    county = docs[_SLUGS["us.census.geoid.county:06037"]]
    admin1 = docs[_SLUGS["iso3166-2:US-CA"]]
    country = docs[_SLUGS["iso3166-1:US"]]
    # s1 placed at the county counts in the county + every ancestor.
    for doc in (county, admin1, country):
        subjects = {s["source_id"]: s for s in doc["sources"]}
        assert "srcA" in subjects  # srcA's record s1
    assert county["totals"]["records"] == 1  # s1 (distinct)
    assert admin1["totals"]["records"] == 3  # s1 + s2 + s3
    assert country["totals"]["records"] == 3
    # The chain is the placement chain, not an invented one.
    assert county["jurisdiction"]["chain"] == ["iso3166-1:US", "iso3166-2:US-CA"]
    assert county["jurisdiction"]["level"] == "county"
    assert admin1["jurisdiction"]["level"] == "state_province"


# --- T5: sighting timing + the latest-complete-run rule ------------------------


def test_t5_first_last_seen_and_latest_ok_run(world):
    docs = _docs(_plan(**world))
    admin1 = docs[_SLUGS["iso3166-2:US-CA"]]
    src_a = next(s for s in admin1["sources"] if s["source_id"] == "srcA")
    src_b = next(s for s in admin1["sources"] if s["source_id"] == "srcB")
    # First/last seen come from the sighting aggregate, never invented.
    assert src_a["first_seen"] == {"at": "2026-05-01T00:00:00Z", "run_id": "run-a1"}
    assert src_a["last_seen"] == {"at": "2026-06-01T00:00:00Z", "run_id": "run-a2"}
    # The latest COMPLETE run — the July `partial` never wins.
    assert src_a["latest_run"]["run_id"] == "run-a2"
    # c2 was last sighted in run-a1, before the latest complete run-a2.
    assert src_a["not_reasserted_in_latest_complete_run"] == 1
    assert src_b["latest_run"]["run_id"] == "run-b2"
    # srcB's c3 was last sighted in run-b1 — before the latest complete run.
    assert src_b["not_reasserted_in_latest_complete_run"] == 1


# --- T6: the run_level_only fallback -------------------------------------------


def test_t6_run_level_only_fallback(world):
    docs = _docs(_plan(**world))
    admin1 = docs[_SLUGS["iso3166-2:US-CA"]]
    src_c = next(s for s in admin1["sources"] if s["source_id"] == "srcC")
    assert src_c["sightings"] == "run_level_only"
    assert "not_recorded" in src_c["last_seen"]
    assert "not_evaluable" in src_c["not_reasserted_in_latest_complete_run"]
    # First-seen still reports — a first sighting is a recorded fact.
    assert src_c["first_seen"]["at"] == "2026-05-10T00:00:00Z"
    # The reason is printed, never silent.
    assert src_c["last_seen"]["not_recorded"]


def test_t6_single_ok_run_is_per_run_not_fallback(world):
    w = dict(world)
    # Drop run-c2 → srcC has one completed run: the fallback condition
    # (>1 completed run) cannot fire — a single-link source with one run is
    # just a young series, not missing re-sightings.
    w["run_rows"] = [r for r in world["run_rows"] if r[1] != "run-c2"]
    docs = _docs(_plan(**w))
    admin1 = docs[_SLUGS["iso3166-2:US-CA"]]
    src_c = next(s for s in admin1["sources"] if s["source_id"] == "srcC")
    assert src_c["sightings"] == "per_run"
    assert src_c["last_seen"]["at"] == "2026-05-10T00:00:00Z"


# --- T7: the dossier↔source mirror ----------------------------------------------


def test_t7_contributions_mirror_the_dossier_rows(world):
    plan = _plan(**world)
    docs = _docs(plan)
    for sid, contribs in plan.contributions_by_source.items():
        for c in contribs:
            doc = docs[c["dossier_slug"]]
            row = next(s for s in doc["sources"] if s["source_id"] == sid)
            assert c["records"] == row["records"]
            assert c["claims"] == row["claims"]
            assert c["first_seen_at"] == row["first_seen"]["at"]
            if row["sightings"] == "run_level_only":
                assert c["last_seen_at"] == row["last_seen"]
            else:
                assert c["last_seen_at"] == row["last_seen"]["at"]
            assert c["dossier_jkey"] == doc["jurisdiction"]["jkey"]


# --- T8: the artifact shape -----------------------------------------------------


def test_t8_artifact_shape_and_honest_states(world):
    docs = _docs(_plan(**world))
    doc = docs[_SLUGS["iso3166-2:US-CA"]]
    assert doc["schema"] == SCHEMA
    for block in (
        "release",
        "jurisdiction",
        "definitions",
        "totals",
        "provenance_summary",
        "figures",
        "sources",
        "cross_source",
        "placement",
        "runs_file",
        "downloads",
    ):
        assert block in doc, block
    ps = doc["provenance_summary"]
    assert ps["human_review_status"] == "unreviewed"
    assert ps["scope"] == "dossier"
    assert "placement@1" in ps["rules_applied"]
    # Honest absence: co-location is not_evaluable until DSRC-04 lands.
    assert "not_evaluable" in doc["cross_source"]["colocated_pairs"]
    assert "run_level_only" in doc["definitions"]["sightings"]


# --- T9: the multi-source sum_rule flip -------------------------------------------


def test_t9_multi_source_record_flips_sum_rule(world):
    docs = _docs(_plan(**world))
    county = docs[_SLUGS["us.census.geoid.county:06037"]]
    fig = {f["figure_id"]: f for f in county["figures"]}
    rec = fig["records"]
    # s1 sits under srcA AND srcB — the by_source values overlap.
    assert rec["sum_rule"] == "distinct"
    assert rec["value"] == 1  # the distinct record
    assert sum(b["value"] for b in rec["by_source"]) == 2  # the overlap
    assert rec.get("sum_disclosure")


# --- T10: the runs files --------------------------------------------------------


def test_t10_runs_file_levels_and_determinism(world):
    plan = _plan(**world)
    arts = plan.render({})
    # Country + admin-1 carry the per-(source, run) detail; county does not.
    us_runs = "web/dossier_sources/usa.runs.jsonl.gz"
    ca_runs = "web/dossier_sources/usa/ca.runs.jsonl.gz"
    assert us_runs in arts and ca_runs in arts
    assert not any(p.endswith("06037.runs.jsonl.gz") for p in arts)
    docs = _docs(plan)
    assert docs["usa"]["runs_file"] == us_runs
    assert docs["usa/ca"]["runs_file"] == ca_runs
    assert docs[_SLUGS["us.census.geoid.county:06037"]]["runs_file"] is None
    # gzip determinism (mtime 0): a re-render is byte-identical.
    assert arts[us_runs] == plan.render({})[us_runs]
    # gzip header mtime field (bytes 4-8) is zeroed.
    assert arts[us_runs][4:8] == b"\x00\x00\x00\x00"
    rows = [
        json.loads(line)
        for line in gzip.decompress(arts[us_runs]).decode().splitlines()
        if line.strip()
    ]
    assert rows and all(r["schema"] == RUNS_ROW_SCHEMA for r in rows)
    a1 = next(r for r in rows if r["run_id"] == "run-a1")
    assert a1["claims_first_seen"] == 2  # c1 + c2 first seen in run-a1
    assert a1["claims_resighted"] == 0
    a2 = next(r for r in rows if r["run_id"] == "run-a2")
    assert a2["claims_resighted"] == 1  # c1 re-sighted
    # The partial run rides the log too — the run record is the fact.
    assert any(r["run_id"] == "run-a3" and r["status"] == "partial" for r in rows)


# --- T11: contributions[] on the transparency source rows ------------------------


def test_t11_source_rows_carry_contributions(world):
    from exports.transparency import TRANSPARENCY_SOURCES_PATH, emit_transparency_artifacts

    plan = _plan(**world)
    registry = {
        "srcA": {
            "name": "Fixture A",
            "source_kind": "government_portal",
            "homepage_url": "https://a.example.org",
            "custody_posture": "MIRROR",
            "compact_status": "no_response",
            "ingestion_permitted": True,
            "rights_reviewed_by": "licensing reviewer",
            "rights_reviewed_on": "2026-09-16",
            "rights": {
                "spdx": "CC0-1.0",
                "attribution": "© A",
                "redistributable": True,
                "derivative_permitted": True,
                "terms_url": "https://a.example.org/terms",
            },
            "redistribution": {
                "lane": "raw-ok",
                "evidence": "fixture",
                "evidence_uri": "fixture",
                "decision_authority": "fixture",
                "review_needed": False,
                "part_viii_class": "none-known",
                "packet_limited": False,
                "sig_labelled_cc0": False,
            },
        },
        # A gated source — never permitted, never ingested: the S-11 row
        # discloses no contribution even when the map names one.
        "srcG": {
            "name": "Fixture C",
            "source_kind": "government_portal",
            "homepage_url": "https://c.example.org",
            "custody_posture": "MIRROR",
            "compact_status": "no_response",
            "ingestion_permitted": False,
            "rights_reviewed_by": "",
            "rights_reviewed_on": None,
            "rights": {
                "spdx": "CC0-1.0",
                "attribution": "© C",
                "redistributable": False,
                "derivative_permitted": False,
                "terms_url": "https://c.example.org/terms",
            },
            "redistribution": {
                "lane": "derived-only",
                "evidence": "fixture",
                "evidence_uri": "fixture",
                "decision_authority": "fixture",
                "review_needed": False,
                "part_viii_class": "none-known",
                "packet_limited": False,
                "sig_labelled_cc0": False,
            },
        },
    }
    raw = {
        "transparency_runs": list(world["run_rows"]),
        "transparency_captures": [],
        "transparency_source_rights": [],
        "transparency_sources": [],
        "transparency_predicates": [],
    }
    contribs = dict(plan.contributions_by_source)
    contribs["srcG"] = [
        {
            "dossier_jkey": "iso3166-1:US",
            "dossier_slug": "usa",
            "records": 1,
            "claims": 1,
            "first_seen_at": "2026-05-10T00:00:00Z",
            "last_seen_at": "2026-05-10T00:00:00Z",
        }
    ]
    arts = emit_transparency_artifacts(
        raw,
        claims=[],
        cadence_sources={},
        source_registry=registry,
        site_source_ids=set(),
        at=_ts("2026-10-21T08:00:00Z"),
        contributions_by_source=contribs,
    )
    rows = {r["source_id"]: r for r in json.loads(arts[TRANSPARENCY_SOURCES_PATH])["sources"]}
    a_contribs = rows["srcA"]["contributions"]
    assert a_contribs == plan.contributions_by_source["srcA"]
    assert {c["dossier_jkey"] for c in a_contribs} == {
        "us.census.geoid.county:06037",
        "iso3166-2:US-CA",
        "iso3166-1:US",
    }
    # Gated rows carry the empty list — S-11 discloses no contribution.
    assert rows["srcG"]["lifecycle_state"] == "gated"
    assert rows["srcG"]["contributions"] == []


# --- T14: the sparse dossier -------------------------------------------------------


def test_t14_sparse_dossier_emits_honest_empty_states():
    # A declared-only record with NO sighting rows and NO placement engine —
    # the artifact still emits, every derived field a named absence.
    plan = _plan(
        sightings_rows=[],
        site_rows=[
            _site("s9", "srcZ", jkey=None, basis=None, check=None, point_status="unresolved")
        ],
        run_rows=[],
        contradictions=[],
        weight_rows=[],
        lineage_rows=None,
        placement=None,
    )
    arts = plan.render({})
    # No placement → the undeclared/absent chain still emits its dossier.
    assert arts, "a sparse world still emits artifacts"
    for _path, data in arts.items():
        doc = json.loads(data)
        assert doc["schema"] == SCHEMA
        assert doc["provenance_summary"]["human_review_status"] == "unreviewed"
        for s in doc["sources"]:
            assert "not_recorded" in s["latest_run"] or s["latest_run"]["run_id"]
