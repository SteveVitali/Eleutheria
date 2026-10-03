# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.20 (SIG-EVUI-D05, AC3) — the shared ``{PUB_ARTIFACT_GATE}`` on the
``evidence_artifacts`` export query: a withheld artifact never reaches the
/evidence/ interim artifact list, while a publishable one carries the registry
``source_name``, the honest ``capture_classification``, and the S-6-scrubbed
``upstream_url``. Seeded on a real PG18+PostGIS testcontainer (Docker-gated)."""

from __future__ import annotations

import json

import pytest
from exports.spine_export import run_spine_export


def _rights(cur, spdx: str, redistributable: str) -> str:
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) VALUES(%s,%s,%s,'2026-01-01') RETURNING rights_id",
        (spdx, redistributable, redistributable),
    )
    return cur.fetchone()[0]


def _run(cur, connector: str) -> str:
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests,status,"
        "finished_at) VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}','succeeded',"
        "'2026-05-02T00:00:00Z') RETURNING run_id",
        (connector,),
    )
    return cur.fetchone()[0]


def _source(cur, source_id: str, name: str, rights_id: str) -> None:
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted','obey',true)",
        (source_id, name, rights_id),
    )


def _artifact_capture(
    cur, source_id: str, rights_id: str, run_id: str, key: str, *, url: str | None = None
) -> str:
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,url,stable_locator,title,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (
            source_id,
            url,
            f"urn:sig:p3420:{key}",
            f"Document {key}",
            rights_id,
        ),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,capture_classification) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0','actual')",
        (artifact_id, f"digest-{key}", run_id, f"urn:sig:p3420:{key}"),
    )
    return str(artifact_id)


def _withhold(cur_conn, target_id: str) -> None:
    from db.dispositions import TargetKind, record_disposition
    from policy.eligibility import Disposition, ReasonCategory, new_disposition

    rec = new_disposition(
        target_kind=TargetKind.ARTIFACT,
        target_id=target_id,
        disposition=Disposition.WITHHOLD,
        reason_category=ReasonCategory.REVIEW_DENIED,
        authority="reviewer:test",
        decided_at=None,
    )
    record_disposition(cur_conn, rec)


@pytest.fixture
def seeded(conn) -> dict:
    cur = conn.cursor()
    rights = _rights(cur, "CC0-1.0", "yes")
    run = _run(cur, "camreg_fixture")
    _source(cur, "camreg_cc0", "Camera Registry (CC0)", rights)
    allowed = _artifact_capture(
        cur, "camreg_cc0", rights, run, "allowed", url="https://example.org/reg.json"
    )
    withheld = _artifact_capture(cur, "camreg_cc0", rights, run, "withheld")
    _withhold(conn, withheld)
    return {"allowed": allowed, "withheld": withheld}


def test_withheld_artifact_never_lists(conn, seeded: dict) -> None:
    """A withhold disposition removes the artifact from the published list —
    the shared gate, never a second eligibility rule."""
    export = run_spine_export(conn, as_of="2026-10-03", note="seeded", spine_label="seeded")
    evidence = json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))
    ids = {a["artifact_id"] for a in evidence["artifacts"]}
    assert seeded["allowed"] in ids
    assert seeded["withheld"] not in ids


def test_listed_artifact_carries_name_classification_and_scrubbed_url(conn, seeded: dict) -> None:
    """K8 NEW-6/NEW-9 — a published artifact lists with the registry name, the
    capture class, and the upstream URL only where effective rights allow."""
    export = run_spine_export(conn, as_of="2026-10-03", note="seeded", spine_label="seeded")
    evidence = json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))
    row = next(a for a in evidence["artifacts"] if a["artifact_id"] == seeded["allowed"])
    assert row["source_name"] == "Camera Registry (CC0)"
    assert row["capture_classification"] == "actual"
    assert row["upstream_url"] == "https://example.org/reg.json"
