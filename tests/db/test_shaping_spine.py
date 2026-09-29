# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Docker-gated seeded-spine end-to-end for export data-shaping (P27.3, LAUNCH.3).

Seeds a small, fully-controlled spine on a real PG18+PostGIS testcontainer —
entities, the L0 evidence chain (source_registry → artifact → capture →
claim_evidence 'establishes'), camera_* claims, an effective-rights decision,
and a sharing edge — then runs :func:`exports.shaping.run_shaping` and the
``PgReadStore`` enumeration reads against it. Read-only throughout; the per-test
connection is rolled back by the ``conn`` fixture.
"""

from __future__ import annotations

import pytest
from api.store_pg import PgReadStore
from exports.shaping import (
    CONFLICTED_JURISDICTION,
    UNASSERTED_JURISDICTION,
    UNRESOLVED_JURISDICTION,
    run_shaping,
)


def _seed_predicate(cur, predicate_id: str, object_type: str = "literal") -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','string',%s,'fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id, object_type),
    )


def _rights(cur, spdx: str, redistributable: str) -> str:
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) VALUES(%s,%s,%s,'2026-01-01') RETURNING rights_id",
        (spdx, redistributable, redistributable),
    )
    return cur.fetchone()[0]


def _run(cur, connector: str, status: str = "succeeded") -> str:
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests,status,"
        "finished_at) VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}',%s,"
        "'2026-05-02T00:00:00Z') RETURNING run_id",
        (connector, status),
    )
    return cur.fetchone()[0]


def _source(cur, source_id: str, rights_id: str) -> None:
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted','obey',true)",
        (source_id, source_id, rights_id),
    )


def _artifact_capture(cur, source_id: str, rights_id: str, run_id: str, key: str) -> str:
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (source_id, f"urn:sig:test:{key}", rights_id),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (artifact_id, f"digest-{key}", run_id, f"urn:sig:test:{key}", f"urn:sig:test:{key}"),
    )
    return cur.fetchone()[0]


def _entity(cur, entity_type: str = "deployment") -> str:
    cur.execute("INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,))
    return cur.fetchone()[0]


def _claim(
    cur,
    *,
    subject,
    predicate,
    value=None,
    value_num=None,
    object_type="literal",
    run_id,
    rights_id,
    author_id,
    capture_id=None,
    tier=0,
) -> str:
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,%s,'value',%s,%s,%s,'2026-05-01T00:00:00Z','R1','D1','I1',"
        "%s,'fixture',%s,%s,%s) RETURNING claim_id",
        (
            subject,
            predicate,
            object_type,
            value,
            value_num,
            "" if value is None else str(value),
            author_id,
            run_id,
            rights_id,
            tier,
        ),
    )
    claim_id = cur.fetchone()[0]
    if capture_id is not None:
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (claim_id, capture_id),
        )
    return claim_id


@pytest.fixture
def seeded(conn) -> dict:
    """A controlled spine: 2 geolocated subjects + unresolved + conflicted +
    unpublishable + a sharing edge + a rights decision."""
    cur = conn.cursor()
    for pred in (
        "camera_latitude",
        "camera_longitude",
        "camera_jurisdiction",
        "camera_name",
        "configured_sharing_partner",
    ):
        _seed_predicate(
            cur, pred, "literal" if pred != "configured_sharing_partner" else "entity_ref"
        )

    cc0 = _rights(cur, "CC0-1.0", "yes")
    odbl = _rights(cur, "ODbL-1.0", "yes")
    undet = _rights(cur, "LicenseRef-Unknown", "UNDETERMINED")

    run_a = _run(cur, "camreg_a")
    run_b = _run(cur, "camreg_osm")
    run_c = _run(cur, "muckrock", status="failed")

    _source(cur, "camreg_a", cc0)
    _source(cur, "camreg_osm", odbl)
    _source(cur, "muckrock", undet)

    cap_a = _artifact_capture(cur, "camreg_a", cc0, run_a, "a")
    cap_b = _artifact_capture(cur, "camreg_osm", odbl, run_b, "b")
    cap_c = _artifact_capture(cur, "muckrock", undet, run_c, "c")

    author = _entity(cur, "person")

    def claims_for(subject, *, cap, run, rights):
        _claim(
            cur,
            subject=subject,
            predicate="camera_latitude",
            value="35.46",
            value_num=35.46,
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )
        _claim(
            cur,
            subject=subject,
            predicate="camera_longitude",
            value="-97.51",
            value_num=-97.51,
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )
        _claim(
            cur,
            subject=subject,
            predicate="camera_jurisdiction",
            value="OK",
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )

    s1 = _entity(cur)
    claims_for(s1, cap=cap_a, run=run_a, rights=cc0)
    # Same subject, second source corroborating (N observations, M sources).
    _claim(
        cur,
        subject=s1,
        predicate="camera_latitude",
        value="35.46",
        value_num=35.46,
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )

    # A second subject at the SAME coordinate from the OSM source — a labelled
    # cross-source duplicate observation group, never merged.
    s2 = _entity(cur)
    _claim(
        cur,
        subject=s2,
        predicate="camera_latitude",
        value="35.46",
        value_num=35.46,
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )
    _claim(
        cur,
        subject=s2,
        predicate="camera_longitude",
        value="-97.51",
        value_num=-97.51,
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )
    _claim(
        cur,
        subject=s2,
        predicate="camera_jurisdiction",
        value="OK",
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )

    # unresolved jurisdiction subject, no coordinates.
    s3 = _entity(cur)
    _claim(
        cur,
        subject=s3,
        predicate="camera_jurisdiction",
        value=UNRESOLVED_JURISDICTION,
        run_id=run_a,
        rights_id=cc0,
        author_id=author,
        capture_id=cap_a,
    )

    # Conflicting latitude claims — the contradiction must stay visible.
    s4 = _entity(cur)
    _claim(
        cur,
        subject=s4,
        predicate="camera_latitude",
        value="40.1",
        value_num=40.1,
        run_id=run_a,
        rights_id=cc0,
        author_id=author,
        capture_id=cap_a,
    )
    _claim(
        cur,
        subject=s4,
        predicate="camera_latitude",
        value="41.2",
        value_num=41.2,
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )
    _claim(
        cur,
        subject=s4,
        predicate="camera_longitude",
        value="-80.0",
        value_num=-80.0,
        run_id=run_a,
        rights_id=cc0,
        author_id=author,
        capture_id=cap_a,
    )
    _claim(
        cur,
        subject=s4,
        predicate="camera_jurisdiction",
        value="NY",
        run_id=run_a,
        rights_id=cc0,
        author_id=author,
        capture_id=cap_a,
    )
    _claim(
        cur,
        subject=s4,
        predicate="camera_jurisdiction",
        value="NJ",
        run_id=run_b,
        rights_id=odbl,
        author_id=author,
        capture_id=cap_b,
    )

    # An UNDETERMINED-rights subject — excluded from the public shape, counted.
    s5 = _entity(cur)
    claims_for(s5, cap=cap_c, run=run_c, rights=undet)

    # A sharing edge on s1 (configured access kind).
    partner = _entity(cur, "organization")
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
        "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s,'configured_sharing_partner','entity_ref',%s,'value','partner',"
        "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (s1, partner, author, run_a, cc0),
    )
    edge_claim = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (edge_claim, cap_a),
    )

    return {
        "s1": str(s1),
        "s2": str(s2),
        "s3": str(s3),
        "s4": str(s4),
        "s5": str(s5),
        "cc0": cc0,
        "odbl": odbl,
        "undet": undet,
    }


def test_run_shaping_over_seeded_spine(conn, seeded) -> None:
    ds = run_shaping(conn, as_of="2026-09-23", note="seeded", spine_label="seeded")
    sites = {s.entity_id: s for s in ds.sites}

    # Publishable scope only: the UNDETERMINED subject is excluded and counted.
    assert seeded["s5"] not in sites
    assert ds.claims_excluded_not_publishable == 3

    # Geometry assembled with lineage + reduction path applied (tier-0 identity).
    s1 = sites[seeded["s1"]]
    assert s1.point_status == "resolved"
    assert s1.latitude == pytest.approx(35.46) and s1.longitude == pytest.approx(-97.51)
    assert s1.jurisdiction == "OK" and s1.jurisdiction_status == "resolved"
    assert set(s1.source_ids) == {"camreg_a", "camreg_osm"}  # N obs, M sources
    assert s1.n_observation_claims == 4 and s1.n_sources == 2
    assert s1.claim_ids  # lineage
    assert s1.observation_level == "observation"  # never a resolved census
    assert s1.observation_group == "35.460000,-97.510000"

    # The cross-source duplicate at the same coordinate is labelled, not merged.
    s2 = sites[seeded["s2"]]
    assert s2.observation_group == s1.observation_group
    assert ds.observation_groups_multi_source == 1

    # The unresolved jurisdiction bucket is a first-class group.
    s3 = sites[seeded["s3"]]
    assert s3.jurisdiction == UNRESOLVED_JURISDICTION
    assert s3.point_status == "unreported"

    # Contradictions stay visible: s4 keeps both lat values + both jurisdictions.
    s4 = sites[seeded["s4"]]
    assert s4.point_status == "conflicted"
    assert s4.latitude is None and s4.longitude is None
    assert s4.lat_envelope.status == "conflicted"
    assert s4.lat_envelope.distinct_values == ("40.1", "41.2")
    assert s4.jurisdiction == CONFLICTED_JURISDICTION
    assert s4.jurisdiction_envelope.distinct_values == ("NJ", "NY")

    # Per-jurisdiction grouping with named denominators.
    buckets = {j.jurisdiction: j for j in ds.jurisdictions}
    assert UNRESOLVED_JURISDICTION in buckets
    assert buckets["OK"].subjects == 2 and buckets["OK"].sites.count == 2
    assert buckets[UNRESOLVED_JURISDICTION].sites.not_evaluable == 1
    assert buckets[CONFLICTED_JURISDICTION].subjects == 1

    # Coverage aggregates: every count denominated, none a bare total.
    for agg in ds.aggregates:
        assert agg.count <= agg.denominator
    for m in ds.coverage_metrics:
        assert m["is_population_total"] is False and m["denominator"].strip()

    # Sharing edge classified; licence posture carried on the site.
    assert any(
        e.subject_id == seeded["s1"] and e.access_kind == "configured_access"
        for e in ds.sharing_edges
    )
    assert set(s1.licenses) == {"CC0-1.0", "ODbL-1.0"}  # ODbL propagates, visible
    assert s1.rights  # per-rights provenance for P27.4's compartment gate

    # Freshness rows exist per source and honestly mark registry gaps.
    sources = {s.freshness.source_id: s for s in ds.sources}
    assert set(sources) == {"camreg_a", "camreg_osm"}
    assert sources["camreg_a"].staleness_not_evaluable > 0

    # Provenance completeness over shaped claims: every claim has a source.
    assert ds.provenance["is_complete"] is True


def test_run_shaping_is_read_only(conn, seeded) -> None:
    before = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
    run_shaping(conn, as_of="2026-09-23")
    after = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
    assert before == after


class _SharedConn:
    """Wraps the test's open transaction so the store's recompute seam reads the
    seeded rows without a commit (a committed seed would pollute the shared
    container for the rest of the suite). ``close`` is a no-op — teardown owns it.
    """

    def __init__(self, conn) -> None:
        self._conn = conn

    @property
    def info(self):
        # run_shaping opens its own snapshot transaction only when the conn is
        # IDLE; the test transaction is INTRANS, so it must fetch in place.
        return self._conn.info

    def cursor(self):
        return self._conn.cursor()

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def close(self) -> None:
        pass


def _store_over(conn) -> PgReadStore:
    """A PgReadStore whose reads all run over the test's open transaction."""
    import threading

    store = PgReadStore.__new__(PgReadStore)
    store._dsn = "(shared test connection)"
    store._conn = conn
    store._role = None
    store._ruleset = None
    store._as_of = None
    store._annotation_lock = threading.Lock()
    store._annotation_cache = None
    store._last_annotation_view = None
    store._shaping_cache = None
    store._connect = lambda: _SharedConn(conn)  # type: ignore[method-assign]
    return store


def test_pgreadstore_enumeration_reads(seeded, conn) -> None:
    """The P27.4 reads are typed and serve the same shaped dataset (P27.3)."""
    store = _store_over(conn)
    sites = store.geolocated_sites()
    # Geolocated = coordinate evidence carried: s1, s2 (resolved) + s4 (conflicted);
    # s3 (jurisdiction-only) and s5 (unpublishable) are not geolocated sites.
    assert {s.entity_id for s in sites} == {seeded["s1"], seeded["s2"], seeded["s4"]}
    assert all(s.observation_level == "observation" for s in sites)

    jurisdictions = store.publishable_jurisdictions()
    assert {j.jurisdiction for j in jurisdictions} >= {"OK", UNRESOLVED_JURISDICTION}
    for j in jurisdictions:
        assert j.sites.count <= j.sites.denominator

    sources = store.sources_with_freshness()
    assert {s.freshness.source_id for s in sources} >= {"camreg_a", "camreg_osm"}

    edges = store.sharing_edges()
    assert any(e.access_kind == "configured_access" for e in edges)

    # Publishable scopes are a superset of geolocated sites: s3 (jurisdiction-only,
    # publishable) is a scope but not a point; s5 (unpublishable) is neither.
    scopes = store.publishable_scopes()
    assert scopes == sorted(scopes)
    assert {seeded["s1"], seeded["s2"], seeded["s3"], seeded["s4"]} <= set(scopes)
    assert seeded["s5"] not in scopes

    dataset = store.shaped_dataset()
    assert dataset.schema_version and dataset.sites
    # Memoized per watermark: a second call returns the same view object.
    assert store.shaped_dataset() is dataset


def test_unasserted_jurisdiction_bucket(conn, seeded) -> None:
    """A subject with no jurisdiction claim lands in the honest (unasserted) bucket."""
    cur = conn.cursor()
    cc0 = seeded["cc0"]
    run = _run(cur, "camreg_extra")
    author = _entity(cur, "person")
    s6 = _entity(cur)
    _claim(
        cur,
        subject=s6,
        predicate="camera_latitude",
        value="30.0",
        value_num=30.0,
        run_id=run,
        rights_id=cc0,
        author_id=author,
    )
    _claim(
        cur,
        subject=s6,
        predicate="camera_longitude",
        value="-90.0",
        value_num=-90.0,
        run_id=run,
        rights_id=cc0,
        author_id=author,
    )
    ds = run_shaping(conn, as_of="2026-09-23")
    buckets = {j.jurisdiction for j in ds.jurisdictions}
    assert UNASSERTED_JURISDICTION in buckets
    site = next(s for s in ds.sites if s.entity_id == str(s6))
    assert site.jurisdiction == UNASSERTED_JURISDICTION


def test_pre_decision_spine_falls_back_to_recorded_rights(sig_database) -> None:
    """On a spine without rights_decision the recorded rights_id is effective."""
    # The testcontainer schema includes rights_decision (P27.2 landed), so the
    # effective path is exercised everywhere above; this test pins the fallback
    # assembler path directly instead.
    from exports.shaping import _queries_for

    fallback = _queries_for(has_decisions=False)
    assert "latest_decision" not in fallback["shaping_claims"]
    assert "c.rights_id" in fallback["shaping_claims"]
    effective = _queries_for(has_decisions=True)
    assert "latest_decision" in effective["shaping_claims"]


def test_effective_rights_decision_resolves_undetermined(conn, seeded) -> None:
    """A rights_decision lifts UNDETERMINED claims into the publishable shape."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_decision(source_id,rights_id,prior_rights_id,basis,reviewer) "
        "VALUES('muckrock',%s,%s,'HG-03 test','maintainer (delegated)')",
        (seeded["cc0"], seeded["undet"]),
    )
    ds = run_shaping(conn, as_of="2026-09-23")
    assert seeded["s5"] in {s.entity_id for s in ds.sites}
    assert ds.claims_excluded_not_publishable == 0
