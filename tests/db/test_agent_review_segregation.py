# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.48 storage segregation over real PG18+PostGIS (SIG-CONF-002, ADR-128).

The agent-review lane appends ``sig.agent-review/1`` JSONL records under
``docs/build/reports/agent-review/`` — never a ``human_eval_*`` table. These
tests prove the human-evaluation schema refuses agent-shaped rows even when
a writer bypasses the lane entirely:

* the label column's CHECK admits only the reference vocabulary — every
  lane verdict (``faithful``/``relevant``/``off_topic``/``unsure``) violates
  it at the database layer;
* a label row must cite a ``human_eval_attestation`` row — an agent verdict
  has none, and the FK refuses the insert;
* the table has no agent-provenance columns — ``labeller_kind``,
  ``model_id``, ``prompt_digest``, ``context_id`` have nowhere to land;
* the pipeline roles (materialize/ingest/read/export) hold no INSERT — only
  the attested reviewer role writes the table.
"""

from __future__ import annotations

import psycopg
import pytest
from resolution.human_eval import build_blinded_packet
from resolution.human_eval_pg import write_manifest, write_packets, write_samples

CAMPAIGN = "camp-ar-seg"


def _sample_row(sample_id: str, partition: str, draw_order: int) -> dict:
    return {
        "campaign_id": CAMPAIGN,
        "sample_id": sample_id,
        "pair_id": f"{sample_id}-pair",
        "left_ref": f"{sample_id}-L",
        "right_ref": f"{sample_id}-R",
        "packet_digest": None,
        "partition": partition,
        "estimand": "auto_positive_precision",
        "stratum_id": "s1",
        "dependency_group_id": f"dg-{sample_id}",
        "source_lineage_ids": [f"src-{sample_id}"],
        "selection_probability": 0.5,
        "weight": 2.0,
        "draw_order": draw_order,
        "reference_basis": "physical_identity",
    }


@pytest.fixture
def seg_campaign(conn: object) -> None:
    conn.execute(
        "INSERT INTO human_eval_campaign"
        "(campaign_id, purpose, protocol_digest, frame_snapshot, ruleset_digest,"
        " seed, design, created_by) "
        "VALUES (%s,'seg test','pd','snap','rs','s1',%s::jsonb,'fixture')",
        (CAMPAIGN, '{"a":1}'),
    )
    rows = [_sample_row("seg-dev", "development", 0)]
    write_samples(conn, rows, role=None)
    write_manifest(
        conn,
        campaign_id=CAMPAIGN,
        sample_rows=rows,
        denominators={"development": {"s1": {"universe": 2, "drawn": 1}}},
        created_by="fixture",
        role=None,
    )
    write_packets(
        conn,
        [
            {
                "campaign_id": CAMPAIGN,
                "sample_id": "seg-dev",
                "payload": build_blinded_packet(
                    sample_id="seg-dev",
                    seed="s1",
                    left_evidence={"name": "L"},
                    right_evidence={"name": "R"},
                ),
            }
        ],
        role=None,
    )


def _denied(conn: object, exc: type, sql: str, params: tuple = ()) -> None:
    """Assert a statement is refused inside a savepoint (fixture survives)."""
    with pytest.raises(exc):
        with conn.transaction():
            conn.execute(sql, params)


@pytest.mark.parametrize(
    "verdict", ["faithful", "relevant", "off_topic", "unsure", "agent_consensus"]
)
def test_lane_verdicts_violate_the_label_check_constraint(
    conn: object, seg_campaign: None, verdict: str
) -> None:
    """An agent verdict is not a reference label — the CHECK refuses it."""
    _denied(
        conn,
        psycopg.errors.CheckViolation,
        "INSERT INTO human_eval_label"
        "(campaign_id, sample_id, reviewer_id, label_round, label,"
        " rubric_version, packet_digest, attestation_id, label_digest)"
        " VALUES (%s,'seg-dev','rev-1','independent_1',%s,"
        " 'rub/1', 'pd', gen_random_uuid(), 'dg')",
        (CAMPAIGN, verdict),
    )


def test_an_agent_row_cannot_cite_a_human_attestation(conn: object, seg_campaign: None) -> None:
    """Even a valid-vocabulary row needs a real attestation_id — an agent
    verdict has no human-identity attestation, so the FK refuses it."""
    _denied(
        conn,
        psycopg.errors.ForeignKeyViolation,
        "INSERT INTO human_eval_label"
        "(campaign_id, sample_id, reviewer_id, label_round, label,"
        " rubric_version, packet_digest, attestation_id, label_digest)"
        " VALUES (%s,'seg-dev','agent:claude-opus-5-5','independent_1','same',"
        " 'rub/1', 'pd', '00000000-0000-0000-0000-000000000000', 'dg')",
        (CAMPAIGN,),
    )


def test_the_label_table_has_no_agent_provenance_columns(conn: object) -> None:
    cols = {
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'human_eval_label'"
        )
    }
    for agent_field in (
        "labeller_kind",
        "model_id",
        "prompt_digest",
        "context_id",
        "corpus_digest",
    ):
        assert agent_field not in cols, f"{agent_field} has nowhere to land"
    # And the lane's record family never lands as a table either.
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    }
    assert not any(t.startswith("agent_review") for t in tables)


def test_pipeline_roles_cannot_write_the_label_table(conn: object) -> None:
    """Only the attested reviewer role writes labels — every pipeline role an
    agent lane would ever run as holds no INSERT."""
    for role in (
        "sig_materialize",
        "sig_ingest",
        "sig_export",
        "sig_read_public",
        "sig_read_restricted",
        "sig_eval_admin",
        "sig_eval_custodian",
    ):
        allowed = conn.execute(
            "SELECT has_table_privilege(%s, 'human_eval_label', 'INSERT')", (role,)
        ).fetchone()[0]
        assert not allowed, f"{role} must not insert into human_eval_label"


def test_the_lane_appends_files_never_tables(tmp_path) -> None:
    """End-to-end storage segregation: a lane run appends JSONL under the
    lane dir and writes zero rows — the records never touch the spine."""
    from resolution.agent_review import append_records, build_packet, make_record

    packet = build_packet(
        {
            "version": "sig.agent-review-corpus/1",
            "capture_kind": "fixture",
            "items": [
                {
                    "item_id": "seg-item",
                    "kind": "edge",
                    "strata": ["procurement_edges"],
                    "evidence": {"snippet": "CCTV maintenance contract"},
                }
            ],
        },
        seed="s",
        week="2026-W43",
    )
    item = packet["items"][0]
    records = [
        make_record(
            packet,
            item,
            context_id=ctx,
            verdict="relevant",
            model_id="claude-opus-5-5@test",
            labelled_at="2026-10-22T08:00:00Z",  # future-ok: synthetic: stand-in fixture stamp
        )
        for ctx in ("a", "b")
    ]
    path = tmp_path / "labels.jsonl"
    assert append_records(path, records) == 2
    # Every appended line is sig.agent-review/1 JSONL — a file record family,
    # never a human_eval_* row.
    for line in path.read_text().splitlines():
        row = __import__("json").loads(line)
        assert row["version"] == "sig.agent-review/1"
        assert row["labeller_kind"] == "agent"
