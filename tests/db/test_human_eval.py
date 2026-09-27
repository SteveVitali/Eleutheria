# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P32.9 human-evaluation schema over real PG18+PostGIS (SIG-EVAL-001/002).

Proves the four guarantees the ticket demands, on the sqitch-deployed schema
the conftest container builds exactly as production would:

* role isolation — ``sig_eval_admin`` prepares and reads only *released*
  labels; ``sig_eval_reviewer`` sees its own assignments/packets/labels under
  the ``sig.eval_reviewer`` GUC and nothing else; ``sig_eval_custodian`` is the
  sealing authority; ``sig_materialize`` + the read/export/ingest roles hold
  NO eval-table grants, so sealed reference labels are unreachable from
  clustering and model-development views;
* append-only supersession — labels/adjudications supersede by new row, every
  table's immutability trigger refuses UPDATE/DELETE even for the owner;
* sealing — ``sealed_final`` labels stay invisible in the released views until
  a custodian ``human_eval_release`` row exists, and only an ``operational``
  release exposes anything to ``sig_materialize``;
* manifest + denominators — the recorded digests recompute, the persisted
  denominators survive, and a tampered row is detected;
* P31 compatibility — the operational review queue still speaks accept/reject
  and zero human labels leaves the campaign ``prepared``/``provisional``.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from conftest import (
    DB_DIR,
    PG_DB,
    PG_IMAGE,
    PG_PASSWORD,
    PG_USER,
    SQITCH_IMAGE,
    _docker_reachable,
    _require_or_skip,
    insert_claim,
    seed_claim_prerequisites,
)
from resolution.human_eval import build_blinded_packet, label_digest, label_watermark
from resolution.human_eval_pg import (
    assign_reviewers,
    campaign_status,
    campaign_watermark,
    export_workbook,
    record_adjudication,
    record_attestation,
    record_label,
    record_release,
    verify_manifest,
    write_manifest,
    write_packets,
    write_samples,
)

CAMPAIGN = "camp-pg-1"
DESIGN = {"purpose": "test", "seed": "s1", "strata": ["s1"], "protocol": "rubric/1"}


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
def eval_campaign(conn: object) -> dict[str, object]:
    """A prepared campaign: 1 development + 1 sealed_final sample + packets."""
    conn.execute(
        "INSERT INTO human_eval_campaign"
        "(campaign_id, purpose, protocol_digest, frame_snapshot, ruleset_digest,"
        " seed, design, created_by) "
        "VALUES (%s,'pg test','pd','snap','rs','s1',%s::jsonb,'fixture')",
        (CAMPAIGN, '{"a":1}'),
    )
    rows = [_sample_row("hev-dev", "development", 0), _sample_row("hev-sealed", "sealed_final", 1)]
    write_samples(conn, rows, role=None)
    write_manifest(
        conn,
        campaign_id=CAMPAIGN,
        sample_rows=rows,
        denominators={"development": {"s1": {"universe": 2, "drawn": 1}},
                      "sealed_final": {"s1": {"universe": 4, "drawn": 1}}},
        created_by="fixture",
        role=None,
    )
    packets = [
        {
            "campaign_id": CAMPAIGN,
            "sample_id": s["sample_id"],
            "payload": build_blinded_packet(
                sample_id=s["sample_id"],
                seed="s1",
                left_evidence={"name": f"{s['sample_id']} left", "latitude": 1.0},
                right_evidence={"name": f"{s['sample_id']} right", "latitude": 2.0},
            ),
        }
        for s in rows
    ]
    write_packets(conn, packets, role=None)
    return {"campaign_id": CAMPAIGN, "samples": rows, "packets": packets}


def _attest(conn: object, reviewer: str) -> str:
    return record_attestation(
        conn,
        campaign_id=CAMPAIGN,
        reviewer_id=reviewer,
        kind="human_identity",
        detail={"method": "fixture"},
        recorded_by="fixture",
        role=None,
    )


def _packet_digest(conn: object, sample_id: str) -> str:
    return conn.execute(
        "SELECT packet_digest FROM human_eval_packet WHERE campaign_id=%s AND sample_id=%s",
        (CAMPAIGN, sample_id),
    ).fetchone()[0]


def _label(conn: object, sample_id: str, reviewer: str, *, label: str = "same",
           round_: str = "independent_1", supersedes: str | None = None,
           role: str | None = None) -> str:
    pkt = _packet_digest(conn, sample_id)
    out = record_label(
        conn,
        campaign_id=CAMPAIGN,
        sample_id=sample_id,
        reviewer_id=reviewer,
        round=round_,
        label=label,
        reason_codes=["fixture_reason"],
        evidence_refs=[{"claim": sample_id}],
        rubric_version="eval-rubric/1",
        packet_digest=pkt,
        attestation_id=_attest(conn, reviewer),
        label_digest=label_digest(
            campaign_id=CAMPAIGN,
            sample_id=sample_id,
            reviewer_id=reviewer,
            round=round_,
            label=label,
            reason_codes=["fixture_reason"],
            evidence_refs=[{"claim": sample_id}],
            rubric_version="eval-rubric/1",
            packet_digest=pkt,
        ),
        supersedes_label_id=supersedes,
        role=role,
    )
    # record_label leaves the session at the given role; reset for the caller.
    _reset(conn)
    return out


def _as_role(conn: object, role: str, guc_reviewer: str | None = None) -> None:
    conn.execute(f"SET ROLE {role}")
    if guc_reviewer is not None:
        conn.execute("SELECT set_config('sig.eval_reviewer', %s, true)", (guc_reviewer,))


def _reset(conn: object) -> None:
    conn.execute("RESET ROLE")
    conn.execute("SELECT set_config('sig.eval_reviewer', '', false)")


def _denied(conn: object, sql: str, params: tuple = ()) -> None:
    """Assert a statement is denied WITHOUT rolling back the test transaction.

    The conftest ``conn`` is one long transaction per test — a full rollback
    would discard the fixture rows. A nested ``conn.transaction()`` savepoint
    confines the aborted statement so the denial can be asserted mid-test and
    the seeded data survives.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with conn.transaction():
            conn.execute(sql, params)


# --------------------------------------------------------------------------- #
# Grants matrix — who may touch what                                          #
# --------------------------------------------------------------------------- #
def test_admin_prepares_but_never_sees_base_labels(conn: object) -> None:
    priv = lambda t, p: conn.execute(  # noqa: E731
        "SELECT has_table_privilege('sig_eval_admin', %s, %s)", (t, p)
    ).fetchone()[0]
    for t in ("human_eval_campaign", "human_eval_manifest", "human_eval_sample",
              "human_eval_packet", "human_eval_assignment", "human_eval_attestation"):
        assert priv(t, "SELECT") and priv(t, "INSERT"), t
        assert not priv(t, "UPDATE") and not priv(t, "DELETE"), t
    assert priv("human_eval_label_released", "SELECT")
    assert priv("human_eval_adjudication_released", "SELECT")
    # The sealing boundary: admin has NO base label/adjudication/release access.
    for t in ("human_eval_label", "human_eval_adjudication", "human_eval_release"):
        for p in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert not priv(t, p), f"admin must not hold {p} on {t}"


def test_reviewer_scoped_writes_no_internals(conn: object) -> None:
    priv = lambda t, p: conn.execute(  # noqa: E731
        "SELECT has_table_privilege('sig_eval_reviewer', %s, %s)", (t, p)
    ).fetchone()[0]
    assert priv("human_eval_label", "INSERT") and priv("human_eval_label", "SELECT")
    assert priv("human_eval_attestation", "INSERT")
    for t in ("human_eval_packet", "human_eval_assignment"):
        assert priv(t, "SELECT")
    # Strata, probabilities, partitions, adjudications, releases, designs: denied.
    for t in ("human_eval_sample", "human_eval_adjudication", "human_eval_release",
              "human_eval_campaign", "human_eval_manifest"):
        assert not priv(t, "SELECT"), t
    assert not priv("human_eval_label", "UPDATE")
    assert not priv("human_eval_label", "DELETE")


def test_custodian_reads_all_writes_decisions_only(conn: object) -> None:
    priv = lambda t, p: conn.execute(  # noqa: E731
        "SELECT has_table_privilege('sig_eval_custodian', %s, %s)", (t, p)
    ).fetchone()[0]
    for t in ("human_eval_label", "human_eval_adjudication", "human_eval_release",
              "human_eval_sample", "human_eval_packet", "human_eval_campaign"):
        assert priv(t, "SELECT"), t
    assert priv("human_eval_release", "INSERT")
    assert priv("human_eval_adjudication", "INSERT")
    # The custodian cannot mint a human label — labels are reviewer-written only.
    assert not priv("human_eval_label", "INSERT")


def test_materialize_and_read_roles_have_no_eval_access(conn: object) -> None:
    def priv(role: str, table: str, p: str) -> bool:
        return conn.execute(
            "SELECT has_table_privilege(%s, %s, %s)", (role, table, p)
        ).fetchone()[0]

    base = ("human_eval_campaign", "human_eval_manifest", "human_eval_sample",
            "human_eval_packet", "human_eval_assignment", "human_eval_attestation",
            "human_eval_label", "human_eval_adjudication", "human_eval_release")
    for role in ("sig_materialize", "sig_read_public", "sig_read_restricted",
                 "sig_read_sealed", "sig_export"):
        for t in base:
            for p in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                assert not priv(role, t, p), f"{role} must not hold {p} on {t}"
    for p in ("SELECT", "INSERT"):
        assert not priv("sig_ingest", "human_eval_label", p)
    # The materializer's only eval surface is the operational released views.
    assert priv("sig_materialize", "human_eval_label_operational", "SELECT")
    assert priv("sig_materialize", "human_eval_adjudication_operational", "SELECT")


# --------------------------------------------------------------------------- #
# Reviewer isolation — two reviewers cannot see each other's first pass        #
# --------------------------------------------------------------------------- #
def test_reviewer_rls_isolates_labels_packets_assignments(conn: object, eval_campaign: dict) -> None:
    assign_reviewers(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-a", sample_ids=["hev-dev"],
        pass_no=1, assigned_by="fixture", role=None,
    )
    assign_reviewers(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-b", sample_ids=["hev-sealed"],
        pass_no=1, assigned_by="fixture", role=None,
    )
    _label(conn, "hev-dev", "rev-a", role=None)
    _label(conn, "hev-sealed", "rev-b", role=None)

    _as_role(conn, "sig_eval_reviewer", "rev-a")
    try:
        # Own label only — rev-b's sealed label does not exist for rev-a.
        rows = conn.execute(
            "SELECT reviewer_id, sample_id FROM human_eval_label"
        ).fetchall()
        assert rows == [("rev-a", "hev-dev")]
        # Only own assignment.
        a = conn.execute("SELECT sample_id FROM human_eval_assignment").fetchall()
        assert a == [("hev-dev",)]
        # Packet for the assigned sample only — the unassigned one is invisible.
        p = conn.execute(
            "SELECT sample_id FROM human_eval_packet ORDER BY sample_id"
        ).fetchall()
        assert p == [("hev-dev",)]
        # Sample internals (strata/probability) are not even grantable.
        _denied(conn, "SELECT * FROM human_eval_sample")
    finally:
        _reset(conn)


def test_reviewer_cannot_write_another_reviewers_label(conn: object, eval_campaign: dict) -> None:
    # The attestation + packet exist for rev-b, minted as the superuser fixture.
    att_b = _attest(conn, "rev-b")
    pkt = _packet_digest(conn, "hev-dev")
    _as_role(conn, "sig_eval_reviewer", "rev-a")
    try:
        # Even with a valid attestation/packet, writing AS rev-b is refused by
        # the WITH CHECK — one reviewer can never impersonate or overwrite another.
        _denied(
            conn,
            "INSERT INTO human_eval_label"
            "(campaign_id, sample_id, reviewer_id, label_round, label,"
            " reason_codes, evidence_refs, rubric_version, packet_digest,"
            " attestation_id, label_digest) "
            "VALUES (%s,'hev-dev','rev-b','independent_1','same','{}','[]',"
            "'eval-rubric/1',%s,%s,'x')",
            (CAMPAIGN, pkt, att_b),
        )
    finally:
        _reset(conn)


def test_unset_guc_fails_closed(conn: object, eval_campaign: dict) -> None:
    _label(conn, "hev-dev", "rev-a", role=None)
    conn.execute("SET ROLE sig_eval_reviewer")
    try:
        # No sig.eval_reviewer GUC → the session is nobody → sees nothing.
        assert conn.execute("SELECT count(*) FROM human_eval_label").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM human_eval_assignment").fetchone()[0] == 0
    finally:
        _reset(conn)


def test_workbook_export_carries_only_blinded_fields(conn: object, eval_campaign: dict) -> None:
    assign_reviewers(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-a", sample_ids=["hev-dev"],
        pass_no=1, assigned_by="fixture", role=None,
    )
    rows = export_workbook(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-a", pass_no=1, role=None
    )
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {"sample_id", "packet_digest", "packet", "label",
                        "reason_codes", "evidence_refs", "rubric_version"}
    # The payload carries sides only — no stratum/tier/score/pair ids.
    assert set(row["packet"]) == {"packet_version", "side_a", "side_b"}


# --------------------------------------------------------------------------- #
# Append-only supersession + insufficient persistence                          #
# --------------------------------------------------------------------------- #
def test_insufficient_label_persists_and_never_auto_accepts(conn: object, eval_campaign: dict) -> None:
    # Written through the production path: assign the packet, then the label
    # lands under sig_eval_reviewer + the sig.eval_reviewer GUC — own row only.
    assign_reviewers(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-a", sample_ids=["hev-dev"],
        pass_no=1, assigned_by="fixture", role=None,
    )
    _label(conn, "hev-dev", "rev-a", label="insufficient_evidence",
           role="sig_eval_reviewer")
    row = conn.execute(
        "SELECT label FROM human_eval_label WHERE campaign_id=%s AND sample_id='hev-dev'",
        (CAMPAIGN,),
    ).fetchone()
    assert row[0] == "insufficient_evidence"
    # It can never surface as an operational accept: the vocabulary is a CHECK
    # boundary, and no write path maps it onto review_decision.
    assert conn.execute(
        "SELECT count(*) FROM review_decision rd JOIN review_item ri "
        "ON ri.item_id = rd.item_id WHERE ri.item_id LIKE 'hev-%'"
    ).fetchone()[0] == 0


def test_append_only_supersession(conn: object, eval_campaign: dict) -> None:
    first = _label(conn, "hev-dev", "rev-a", label="insufficient_evidence", role=None)
    # A correction is a NEW row pointing at the old one; both persist.
    second = _label(conn, "hev-dev", "rev-a", label="same", supersedes=first, role=None)
    rows = conn.execute(
        "SELECT label_id, label, supersedes_label_id FROM human_eval_label "
        "WHERE campaign_id=%s ORDER BY label_seq",
        (CAMPAIGN,),
    ).fetchall()
    assert len(rows) == 2
    assert str(rows[0][0]) == first and str(rows[1][0]) == second
    assert str(rows[1][2]) == first, "the correction must point at the row it supersedes"
    # A second *unlinked* first-pass label is refused (one current label per
    # reviewer+sample+round) — history changes by supersession, never by twin.
    with pytest.raises(psycopg.errors.UniqueViolation):
        _label(conn, "hev-dev", "rev-a", label="different", role=None)
    conn.rollback()


@pytest.mark.parametrize("table", [
    "human_eval_campaign", "human_eval_manifest", "human_eval_sample",
    "human_eval_packet", "human_eval_assignment", "human_eval_attestation",
    "human_eval_label", "human_eval_adjudication", "human_eval_release",
])
def test_every_eval_table_is_immutable(conn: object, eval_campaign: dict, table: str) -> None:
    # Seed one row in each auxiliary table so the UPDATE actually reaches a row
    # (a trigger on an empty table never fires).
    _label(conn, "hev-dev", "rev-a", role=None)
    assign_reviewers(
        conn, campaign_id=CAMPAIGN, reviewer_id="rev-a", sample_ids=["hev-dev"],
        pass_no=1, assigned_by="fixture", role=None,
    )
    record_adjudication(
        conn, campaign_id=CAMPAIGN, sample_id="hev-dev", adjudicator_id="adj-1",
        phase="resolution", label="same", reason="r", evidence_refs=[], role=None,
    )
    record_release(
        conn, campaign_id=CAMPAIGN, scope="development_only",
        authorized_by="fixture", detail={}, role=None,
    )
    # The immutability trigger refuses UPDATE/DELETE even for the table owner.
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        conn.execute(f"UPDATE {table} SET campaign_id = campaign_id")
    conn.rollback()
    # …and a non-owner role is refused at the privilege layer too.
    conn.execute("SET ROLE sig_eval_admin")
    try:
        _denied(conn, f"DELETE FROM {table}")
    finally:
        conn.execute("RESET ROLE")


# --------------------------------------------------------------------------- #
# Sealing — sealed_final unreachable until an authorized release               #
# --------------------------------------------------------------------------- #
def test_sealed_labels_stay_invisible_until_release(conn: object, eval_campaign: dict) -> None:
    _label(conn, "hev-dev", "rev-a", role=None)
    _label(conn, "hev-sealed", "rev-b", role=None)
    # The adjudication lands through the custodian path it will use in production.
    record_adjudication(
        conn, campaign_id=CAMPAIGN, sample_id="hev-sealed", adjudicator_id="adj-1",
        phase="resolution", label="same", reason="settled", evidence_refs=[],
        role="sig_eval_custodian",
    )
    conn.execute("RESET ROLE")

    # The model-development surface (admin → released view): dev only.
    _as_role(conn, "sig_eval_admin")
    try:
        rows = conn.execute(
            "SELECT sample_id FROM human_eval_label_released ORDER BY sample_id"
        ).fetchall()
        assert rows == [("hev-dev",)]
        assert conn.execute(
            "SELECT count(*) FROM human_eval_adjudication_released"
        ).fetchone()[0] == 0
        # No base-table path at all.
        _denied(conn, "SELECT * FROM human_eval_label")
    finally:
        _reset(conn)

    # The clustering surface: the operational view exists but is empty, and
    # every base table is a privilege denial.
    conn.execute("SET ROLE sig_materialize")
    try:
        _denied(conn, "SELECT * FROM human_eval_label")
        _denied(conn, "SELECT * FROM human_eval_sample")
        _denied(conn, "SELECT * FROM human_eval_adjudication")
        _denied(conn, "SELECT * FROM human_eval_release")
        assert conn.execute(
            "SELECT count(*) FROM human_eval_label_operational"
        ).fetchone()[0] == 0
    finally:
        _reset(conn)

    # A non-operational release opens the model-development view, never the
    # operational one — recorded through the custodian path.
    record_release(
        conn, campaign_id=CAMPAIGN, scope="final",
        authorized_by="P32.23-gate", detail={}, role="sig_eval_custodian",
    )
    conn.execute("RESET ROLE")
    _as_role(conn, "sig_eval_admin")
    try:
        assert {
            r[0] for r in conn.execute(
                "SELECT sample_id FROM human_eval_label_released"
            ).fetchall()
        } == {"hev-dev", "hev-sealed"}
    finally:
        _reset(conn)
    conn.execute("SET ROLE sig_materialize")
    try:
        assert conn.execute(
            "SELECT count(*) FROM human_eval_label_operational"
        ).fetchone()[0] == 0
    finally:
        _reset(conn)

    # Only an operational release exposes anything to clustering.
    record_release(
        conn, campaign_id=CAMPAIGN, scope="operational",
        authorized_by="P32.23-gate", detail={}, role="sig_eval_custodian",
    )
    conn.execute("RESET ROLE")
    conn.execute("SET ROLE sig_materialize")
    try:
        rows = conn.execute(
            "SELECT sample_id, label FROM human_eval_label_operational"
        ).fetchall()
        assert set(rows) == {("hev-sealed", "same"), ("hev-dev", "same")}
    finally:
        _reset(conn)


def test_release_requires_the_custodian(conn: object, eval_campaign: dict) -> None:
    _as_role(conn, "sig_eval_admin")
    try:
        _denied(
            conn,
            "INSERT INTO human_eval_release(campaign_id, scope, authorized_by) "
            "VALUES (%s, 'operational', 'x')",
            (CAMPAIGN,),
        )
    finally:
        _reset(conn)


def test_custodian_cannot_mint_a_label(conn: object, eval_campaign: dict) -> None:
    att = _attest(conn, "custodian")
    _as_role(conn, "sig_eval_custodian")
    try:
        _denied(
            conn,
            "INSERT INTO human_eval_label"
            "(campaign_id, sample_id, reviewer_id, label_round, label,"
            " rubric_version, packet_digest, attestation_id, label_digest) "
            "VALUES (%s,'hev-dev','custodian','independent_1','same','r','p',%s,'d')",
            (CAMPAIGN, att),
        )
    finally:
        _reset(conn)


# --------------------------------------------------------------------------- #
# Manifest + denominators + watermark                                          #
# --------------------------------------------------------------------------- #
def test_manifest_verifies_and_detects_tamper(conn: object, eval_campaign: dict) -> None:
    result = verify_manifest(conn, CAMPAIGN, role=None)
    assert result["verified"], result
    assert result["denominators"]["sealed_final"]["s1"] == {"universe": 4, "drawn": 1}
    # A tampered row breaks the digest — simulate the owner-level edit the
    # trigger normally forbids by suspending triggers like a privileged hostile.
    conn.execute("SET session_replication_role = replica")
    try:
        conn.execute(
            "UPDATE human_eval_sample SET weight = 9.9 "
            "WHERE campaign_id = %s AND sample_id = 'hev-sealed'",
            (CAMPAIGN,),
        )
    finally:
        conn.execute("SET session_replication_role = DEFAULT")
    result = verify_manifest(conn, CAMPAIGN, role=None)
    assert not result["verified"]
    assert result["computed_manifest_digest"] != result["stored_manifest_digest"]


def test_denominators_are_persisted_on_the_manifest(conn: object, eval_campaign: dict) -> None:
    row = conn.execute(
        "SELECT denominators, sample_count FROM human_eval_manifest WHERE campaign_id=%s",
        (CAMPAIGN,),
    ).fetchone()
    assert row[0]["development"]["s1"]["universe"] == 2
    assert row[0]["sealed_final"]["s1"]["drawn"] == 1
    assert row[1] == 2


def test_watermark_tracks_the_label_chain(conn: object, eval_campaign: dict) -> None:
    _label(conn, "hev-dev", "rev-a", role=None)
    _label(conn, "hev-dev", "rev-b", round_="independent_2", role=None)
    wm = campaign_watermark(conn, CAMPAIGN, role=None)
    digests = [
        r[0]
        for r in conn.execute(
            "SELECT label_digest FROM human_eval_label WHERE campaign_id=%s ORDER BY label_seq",
            (CAMPAIGN,),
        ).fetchall()
    ]
    assert wm == label_watermark([{"label_digest": d} for d in digests])
    # The admin surface cannot compute the sealed half — only the custodian sees all.
    _as_role(conn, "sig_eval_admin")
    try:
        released = [
            r[0]
            for r in conn.execute(
                "SELECT label_digest FROM human_eval_label_released ORDER BY label_seq"
            ).fetchall()
        ]
        assert len(released) == 2  # dev labels visible
    finally:
        conn.rollback()
        _reset(conn)


# --------------------------------------------------------------------------- #
# Zero-label posture + P31 compatibility                                       #
# --------------------------------------------------------------------------- #
def test_zero_labels_leave_campaign_prepared(conn: object, eval_campaign: dict) -> None:
    status = campaign_status(conn, CAMPAIGN, role=None)
    assert status["state"] == "prepared"
    status = campaign_status(conn, CAMPAIGN, role="sig_eval_admin")
    assert status["state"] == "prepared"
    conn.execute("RESET ROLE")
    _label(conn, "hev-dev", "rev-a", role=None)
    status = campaign_status(conn, CAMPAIGN, role=None)
    assert status["state"] == "provisional"
    conn.rollback()


def test_p31_operational_review_is_untouched(conn: object, eval_campaign: dict) -> None:
    conn.execute(
        "INSERT INTO review_item(item_id, kind, summary, payload) "
        "VALUES('er_match:camera_site:x:y','er_match','s','{}')"
    )
    conn.execute(
        "INSERT INTO review_decision(item_id, decision, reviewer) "
        "VALUES('er_match:camera_site:x:y','accept','curator')"
    )
    # The operational vocabulary still has no 'insufficient' — eval abstentions
    # live only in the reference-label channel.
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO review_decision(item_id, decision, reviewer) "
            "VALUES('er_match:camera_site:x:y','insufficient_evidence','curator')"
        )
    conn.rollback()
    # Eval labels never appear in the operational queue.
    assert conn.execute(
        "SELECT count(*) FROM review_item WHERE item_id LIKE 'hev-%'"
    ).fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# Reversibility — the change deploys and reverts without touching history      #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def revert_db() -> Iterator[dict[str, object]]:
    """A dedicated container for the sqitch revert drill (module-scoped)."""
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")

    import docker
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network

    network = Network()
    network.create()
    container = (
        DockerContainer(PG_IMAGE)
        .with_env("POSTGRES_USER", PG_USER)
        .with_env("POSTGRES_PASSWORD", PG_PASSWORD)
        .with_env("POSTGRES_DB", PG_DB)
        .with_exposed_ports(5432)
        .with_network(network)
        .with_network_aliases("db")
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        deadline = time.time() + 120
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with psycopg.connect(
                    host=host, port=port, user=PG_USER, password=PG_PASSWORD,
                    dbname=PG_DB, connect_timeout=3,
                ):
                    break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1)
        else:
            raise RuntimeError(f"Postgres never became ready: {last_err}")

        client = docker.from_env()

        def sqitch(*argv: str) -> None:
            out = client.containers.run(
                SQITCH_IMAGE,
                command=[*argv, f"db:pg://{PG_USER}:{PG_PASSWORD}@db:5432/{PG_DB}"],
                network=network.name,
                working_dir="/repo",
                volumes={str(DB_DIR): {"bind": "/repo", "mode": "ro"}},
                environment={"PGPASSWORD": PG_PASSWORD},
                remove=True,
                stdout=True,
                stderr=True,
            )
            return out

        sqitch("deploy")

        dsn = f"postgresql://{PG_USER}:{PG_PASSWORD}@{host}:{port}/{PG_DB}"
        yield {"dsn": dsn, "sqitch": sqitch}
    finally:
        container.stop()
        network.remove()


def test_revert_drops_only_the_eval_surface_and_keeps_history(revert_db: dict) -> None:
    """Deploy → seed claim + review + eval rows → revert to the parent change →
    eval tables gone, every earlier table and row intact → re-deploy → clean."""
    sqitch = revert_db["sqitch"]
    with psycopg.connect(str(revert_db["dsn"]), autocommit=True) as conn:
        prereqs = seed_claim_prerequisites(conn)
        claim_id = insert_claim(conn, prereqs, value_text="55", value_num=55)
        conn.execute(
            "INSERT INTO review_item(item_id, kind, summary, payload) "
            "VALUES('er_match:camera_site:a:b','er_match','s','{}')"
        )
        conn.execute(
            "INSERT INTO review_decision(item_id, decision, reviewer) "
            "VALUES('er_match:camera_site:a:b','reject','curator')"
        )
        conn.execute(
            "INSERT INTO human_eval_campaign"
            "(campaign_id, purpose, protocol_digest, frame_snapshot, ruleset_digest,"
            " seed, design, created_by) "
            "VALUES('revert-camp','t','pd','snap','rs','s','{}','fixture')"
        )

    # Seed a sample + label under the campaign (committed so the revert really
    # drops live rows, proving the revert script works on a populated surface).
    with psycopg.connect(str(revert_db["dsn"]), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO human_eval_sample"
            "(campaign_id, sample_id, pair_id, left_ref, right_ref, partition,"
            " estimand, stratum_id, dependency_group_id, selection_probability,"
            " draw_order, reference_basis) "
            "VALUES('revert-camp','hev-r1','p1','l','r','development','e','s1',"
            "'dg','1.0',0,'physical_identity')"
        )
        claim_before = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
        review_before = conn.execute("SELECT count(*) FROM review_decision").fetchone()[0]

    sqitch("revert", "-y", "--to", "publication_dispositions")

    with psycopg.connect(str(revert_db["dsn"]), autocommit=True) as conn:
        for t in ("human_eval_campaign", "human_eval_sample", "human_eval_label",
                  "human_eval_release", "human_eval_label_released"):
            assert conn.execute(
                "SELECT to_regclass(%s)", (f"public.{t}",)
            ).fetchone()[0] is None, f"{t} must be dropped by the revert"
        # Nothing earlier is touched: the claim + operational review history
        # survive byte-for-byte.
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == claim_before
        assert conn.execute(
            "SELECT count(*) FROM review_decision"
        ).fetchone()[0] == review_before
        assert conn.execute(
            "SELECT count(*) FROM claim WHERE claim_id = %s", (claim_id,)
        ).fetchone()[0] == 1

    # And the change re-deploys cleanly (forward path stays migratable).
    sqitch("deploy")
    with psycopg.connect(str(revert_db["dsn"]), autocommit=True) as conn:
        assert conn.execute(
            "SELECT to_regclass('public.human_eval_label')"
        ).fetchone()[0] is not None
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == claim_before
