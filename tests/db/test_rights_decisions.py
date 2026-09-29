# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only rights-resolution log (P27.2 / ADR-095; SIG-LIC-004).

AC coverage:
- a licence review is recorded as NEW ``rights_decision`` + ``rights_record``
  rows — never an UPDATE on the spine;
- decisions resolve a source's UNDETERMINED-recorded claims to the reviewed
  record (the effective-rights rule), idempotently;
- a decision can NEVER relicense an already-resolved claim;
- decision rows are immutable (UPDATE/DELETE refuse);
- fail-closed validation: UNDETERMINED is not a resolution; reviewer/terms/basis
  are required.
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest
from conftest import insert_claim, seed_claim_prerequisites
from db.rights_decisions import (
    RightsResolution,
    RightsResolutionError,
    apply_resolution,
    apply_resolutions,
    capture_terms,
    plan_resolutions,
    validate_resolution,
)


def _res(**over: object) -> RightsResolution:
    defaults: dict[str, object] = {
        "source_id": "fixture_src",
        "spdx": "LicenseRef-PublicRecord-FactualCompilation",
        "attribution": "Fixture public body",
        "redistributable": "yes",
        "derivative_permitted": "yes",
        "terms_url": "https://example.gov/terms",
        "retrieval_date": date(2026, 9, 22),
        "reviewed_by": "maintainer (delegated)",
        "reviewed_on": date(2026, 9, 22),
        "basis": "HG-03 2026-09-22 under GL-GATE-07: public record / factual compilation",
        "review_packet": "docs/build/reports/rights/fixture_src.md",
    }
    defaults.update(over)
    return RightsResolution(**defaults)  # type: ignore[arg-type]


def _seed_source_with_claims(conn: object, source_id: str = "fixture_src", n: int = 2) -> dict:
    """A source whose claims carry a shared UNDETERMINED rights record."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) "
        "VALUES('UNDETERMINED','UNDETERMINED','UNDETERMINED','2026-01-01') RETURNING rights_id"
    )
    und_id = str(cur.fetchone()[0])
    prereqs = seed_claim_prerequisites(conn)
    prereqs["rights_id"] = und_id  # claims recorded under the UNDETERMINED record
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
        "VALUES(%s,'Fixture','portal','R2','fixture',%s,'MIRROR','no_response','obey')",
        (source_id, und_id),
    )
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'webpage','crawl','primary',%s,'captured') RETURNING artifact_id",
        (source_id, f"urn:sig:{source_id}:page", und_id),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,capture_method,"
        "capture_tool_version) VALUES(%s,%s,10,'text/html',now(),%s,'o','v1','x','v') "
        "RETURNING capture_id",
        (artifact_id, f"d-{source_id}", prereqs["run_id"]),
    )
    capture_id = cur.fetchone()[0]
    claim_ids = []
    for _ in range(n):
        cid = insert_claim(conn, prereqs)
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (cid, capture_id),
        )
        claim_ids.append(str(cid))
    return {
        "und_id": und_id,
        "artifact_id": artifact_id,
        "capture_id": capture_id,
        "claim_ids": claim_ids,
        "prereqs": prereqs,
    }


def _effective_spdx(conn: object, claim_id: str) -> str:
    """Resolve a claim's effective licence through the decision rule (the reader's SQL)."""
    row = conn.execute(
        "SELECT rr.spdx_expression FROM claim c"
        " LEFT JOIN (SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id"
        "   FROM claim_evidence ce"
        "   JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "   JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "   WHERE ce.role = 'establishes' ORDER BY ce.claim_id, ea.source_id) cs"
        "   ON cs.claim_id = c.claim_id"
        " LEFT JOIN rights_decision rd ON rd.source_id = cs.source_id"
        "   AND rd.prior_rights_id = c.rights_id"
        " JOIN rights_record rr ON rr.rights_id = COALESCE(rd.rights_id, c.rights_id)"
        " WHERE c.claim_id = %s",
        (claim_id,),
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_schema_exists_and_is_append_only(conn: object) -> None:
    seed = _seed_source_with_claims(conn)
    report = apply_resolution(conn, _res())
    decision_id = report["decisions"][0]["decision_id"]
    with pytest.raises(psycopg.Error) as exc:
        with conn.transaction():
            conn.execute("UPDATE rights_decision SET basis = 'x'")
    assert "immutable" in str(exc.value)
    with pytest.raises(psycopg.Error) as exc:
        with conn.transaction():
            conn.execute("DELETE FROM rights_decision WHERE decision_id = %s", (decision_id,))
    assert "immutable" in str(exc.value)
    assert seed["und_id"]  # silence lint


def test_decision_resolves_undetermined_claims(conn: object) -> None:
    seed = _seed_source_with_claims(conn, n=2)
    report = apply_resolution(conn, _res())
    assert report["claims_lifted"] == 2
    assert len(report["decisions"]) == 1  # one prior (the shared UNDETERMINED record)
    for cid in seed["claim_ids"]:
        assert _effective_spdx(conn, cid) == "LicenseRef-PublicRecord-FactualCompilation"
    # The recorded rights_id is untouched — assertion-time provenance survives.
    rows = conn.execute(
        "SELECT rights_id FROM claim WHERE claim_id = ANY(%s)", (seed["claim_ids"],)
    ).fetchall()
    assert {str(r[0]) for r in rows} == {seed["und_id"]}


def test_apply_is_idempotent(conn: object) -> None:
    _seed_source_with_claims(conn, n=2)
    first = apply_resolution(conn, _res())
    second = apply_resolution(conn, _res())
    assert first["decisions"][0]["inserted"] is True
    assert second["decisions"][0]["inserted"] is False
    assert first["decisions"][0]["decision_id"] == second["decisions"][0]["decision_id"]
    n = conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0]
    assert n == 1


def test_decision_never_relicenses_a_resolved_claim(conn: object) -> None:
    """A claim recorded under a REAL licence is untouched by a source decision."""
    seed = _seed_source_with_claims(conn, n=1)
    prereqs = dict(seed["prereqs"])
    # A second claim under a resolved (ODbL) record — the decision must NOT touch it.
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,derivative_permitted,"
        "retrieval_date) VALUES('ODbL-1.0','yes','yes','2026-01-01') RETURNING rights_id"
    )
    prereqs["rights_id"] = str(cur.fetchone()[0])
    odbl_claim = str(insert_claim(conn, prereqs))
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (odbl_claim, seed["capture_id"]),
    )
    report = apply_resolution(conn, _res())
    assert report["claims_lifted"] == 1  # only the UNDETERMINED-recorded claim
    assert _effective_spdx(conn, odbl_claim) == "ODbL-1.0"


def test_no_publish_decision_is_recorded_honestly(conn: object) -> None:
    """`redistributable='no'` is a legitimate resolution — a decided exclusion."""
    seed = _seed_source_with_claims(conn, n=1)
    res = _res(
        spdx="LicenseRef-MuckRock-API-ToS",
        redistributable="no",
        derivative_permitted="no",
        basis="Reviewed 2026-09-15: API ToS not redistributable (decided exclusion)",
    )
    report = apply_resolution(conn, res)
    assert report["claims_lifted"] == 1
    row = conn.execute(
        "SELECT rr.redistributable FROM rights_decision rd"
        " JOIN rights_record rr ON rd.rights_id = rr.rights_id"
        " WHERE rd.source_id = %s",
        (seed["und_id"] and "fixture_src",),
    ).fetchone()
    assert str(row[0]) == "no"


def test_plan_is_read_only(conn: object) -> None:
    seed = _seed_source_with_claims(conn, n=2)
    plan = plan_resolutions(conn, [_res()])
    assert plan[0]["claims_lifted"] == 2
    assert plan[0]["undetermined_priors"] == [seed["und_id"]]
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_undetermined_is_not_a_resolution(conn: object) -> None:
    res = _res(redistributable="UNDETERMINED", derivative_permitted="UNDETERMINED")
    problems = validate_resolution(res)
    assert problems  # refused before any write
    _seed_source_with_claims(conn)
    with pytest.raises(RightsResolutionError):
        apply_resolution(conn, res)
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_reviewer_terms_and_basis_are_required(conn: object) -> None:
    for field, bad in (("reviewed_by", ""), ("terms_url", ""), ("basis", "  ")):
        res = _res(**{field: bad})
        assert validate_resolution(res), f"{field} must be required"
    _seed_source_with_claims(conn)  # noqa: F841 - fixture


def test_terms_capture_links_the_archived_terms(conn: object) -> None:
    """SIG-LIC-002: the reviewed terms page is archived as evidence and linked."""
    _seed_source_with_claims(conn)
    res = _res()
    from db.rights_decisions import _ensure_rights_record

    rights_id = _ensure_rights_record(conn, res)
    fetched = {"body": b"<html>terms of use</html>", "media_type": "text/html", "http_status": 200}
    capture_id = capture_terms(conn, res, rights_id, fetched, code_commit="deadbeef")
    report = apply_resolution(conn, res, terms_capture_id=capture_id)
    assert report["claims_lifted"] == 2
    row = conn.execute(
        "SELECT terms_capture_id FROM rights_decision WHERE source_id = 'fixture_src'"
    ).fetchone()
    assert str(row[0]) == capture_id
    # The capture's artifact is the real terms URL — the archived terms evidence.
    art = conn.execute(
        "SELECT ea.url, ec.byte_size, ec.capture_method FROM evidence_capture ec"
        " JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        " WHERE ec.capture_id = %s",
        (capture_id,),
    ).fetchone()
    assert art[0] == "https://example.gov/terms"
    assert int(art[1]) == len(b"<html>terms of use</html>")
    assert art[2] == "http_get"


def test_apply_resolutions_batch(conn: object) -> None:
    _seed_source_with_claims(conn, source_id="src_a", n=1)
    _seed_source_with_claims(conn, source_id="src_b", n=3)
    reports = apply_resolutions(
        conn,
        [_res(source_id="src_a"), _res(source_id="src_b", spdx="CC0-1.0")],
    )
    assert [r["claims_lifted"] for r in reports] == [1, 3]
