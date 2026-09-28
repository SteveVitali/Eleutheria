# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P33.2 — the composed Round-10 verification, exercised on a real PG18 spine.

Docker-backed (postgis:18-3.6 + the full sqitch plan, same harness as the rest
of ``tests/db``; ``SIG_REQUIRE_DB_TESTS=1`` turns a missing daemon into a hard
failure — never a silent skip). Runs
``ops.composed_verify.run_composed_verification`` over a throwaway catalog
inside the session container and asserts the ``sig.composed-verification/1``
verdict plus the spine side-effects each leg is supposed to land:

* the fixture claims carry ``actual_capture`` evidence bindings pinned to the
  committed fixture document's multihash (SIG-TRUST-002);
* a re-sighting appends a second establishing occurrence — append-only,
  never an UPDATE;
* the activated release carries the eligible fixture deployment while the
  withheld / UNDETERMINED-rights subjects are excluded loudly;
* the correction the intake journey applies revises a claim the release
  itself published (§16.6 close+revises, exactly once).

The runner COMMITS every leg (autocommit sinks, materializations, a recorded
disposition, a rights_decision, the canonical correction) — so it runs in a
dedicated ``sig_p332_composed`` database deployed by the real sqitch plan and
dropped on teardown. None of it leaks into the shared session ``sig``
catalog the rest of ``tests/db`` counts rows in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from ops import composed_verify as cv

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"
SQITCH_IMAGE = "sqitch/sqitch:latest"
SCRATCH_DB = "sig_p332_composed"


def _dsn(db: dict[str, object], dbname: str | None = None) -> str:
    name = dbname or str(db["dbname"])
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{name}"


def _pg_container_network(sig_database: dict[str, object]) -> str:
    """The Docker network of the session's PG container — found by its
    published port, so sqitch deploys reach it through the same ``db`` alias
    ``tests/db/conftest.py`` registers."""
    import docker

    host_port = int(sig_database["port"])  # type: ignore[arg-type]
    client = docker.from_env()
    # one API call — inspecting each container separately races short-lived
    # helpers (the testcontainers reaper) and dies on a NotFound.
    for container in client.api.containers():
        for binding in container.get("Ports") or []:
            if int(binding.get("PublicPort") or 0) == host_port:
                networks = list((container.get("NetworkSettings") or {}).get("Networks", {}))
                assert networks, "PG container has no attached networks"
                return str(networks[0])
    raise RuntimeError("could not locate the session PG container by its port")


@pytest.fixture(scope="module")
def proof_out(sig_database: dict[str, object], tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Deploy the real plan into a scratch catalog and run the verifier."""
    import docker

    admin = psycopg.connect(_dsn(sig_database), autocommit=True)
    admin.execute(f"DROP DATABASE IF EXISTS {SCRATCH_DB}")
    admin.execute(f"CREATE DATABASE {SCRATCH_DB}")
    docker.from_env().containers.run(
        SQITCH_IMAGE,
        command=[
            "deploy",
            f"db:pg://{sig_database['user']}:{sig_database['password']}@db:5432/{SCRATCH_DB}",
        ],
        network=_pg_container_network(sig_database),
        working_dir="/repo",
        volumes={str(DB_DIR): {"bind": "/repo", "mode": "ro"}},
        environment={"PGPASSWORD": str(sig_database["password"])},
        remove=True,
        stdout=True,
        stderr=True,
    )
    dsn = _dsn(sig_database, SCRATCH_DB)
    out = tmp_path_factory.mktemp("p33.2-composed")
    try:
        proof = cv.run_composed_verification(dsn, out_dir=out)
        yield {"proof": proof, "out": out, "dsn": dsn}
    finally:
        # The runner leaves its connections closed, but the intake stores /
        # sinks may hold pools — terminate before dropping the catalog.
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (SCRATCH_DB,),
        )
        admin.execute(f"DROP DATABASE IF EXISTS {SCRATCH_DB}")
        admin.close()


@pytest.fixture(scope="module")
def proof(proof_out: dict[str, Any]) -> dict[str, Any]:
    return proof_out["proof"]


def test_verdict_pass_and_schema(proof: dict[str, Any]) -> None:
    assert proof["schema"] == cv.PROOF_SCHEMA
    assert proof["verdict"] == "pass"
    failed = [
        f"{leg['leg']}::{c['check']}" for leg in proof["legs"] for c in leg["checks"] if not c["ok"]
    ]
    assert failed == [], f"composed checks failed: {failed}"


def test_all_five_legs_ran(proof: dict[str, Any]) -> None:
    legs = {leg["leg"] for leg in proof["legs"]}
    assert {
        "A.capture_to_claim",
        "B.temporal_role_resolution",
        "C.eligible_release",
        "D.search_record",
        "E.correction",
    } <= legs


def test_intake_receiver_stays_non_operational(proof: dict[str, Any]) -> None:
    """operational=false is the honest production state — the fixture proves
    the machinery; the receiver must never be reported as live."""
    assert proof["environment"]["intake_operational"] is False
    assert proof["environment"]["live_verification"] is False


def test_proof_files_written(proof_out: dict[str, Any]) -> None:
    proof, out = proof_out["proof"], proof_out["out"]
    emitted = json.loads((out / cv.PROOF_JSON).read_text())
    assert emitted["schema"] == cv.PROOF_SCHEMA
    assert emitted["verdict"] == "pass"
    assert (out / cv.PROOF_MD).exists()
    # the trees the runner built are on disk: the export compartments, the
    # activated release namespace, and the registry latest pointer.
    pub = proof["release"]["publication_id"]
    assert (out / "export" / "manifest.json").exists()
    assert (out / "release" / "releases" / pub / "catalog_entry.json").exists()
    assert (out / "registry" / "staged" / "r" / pub).is_dir()
    assert proof["correction"]["schema"] == "sig.journey-intake-proof/1"


def test_correction_target_was_a_released_claim(proof_out: dict[str, Any]) -> None:
    """The corrected claim revises a claim that was already in the spine
    BEFORE the journey ran (the release carries it) — not a claim the journey
    itself seeded."""
    conn = psycopg.connect(proof_out["dsn"], autocommit=True, row_factory=dict_row)
    try:
        target = proof_out["proof"]["correction"]["target_claim_id"]
        row = conn.execute(
            "SELECT predicate_id, ingest_run_id::text AS run FROM claim WHERE claim_id = %s::uuid",
            (target,),
        ).fetchone()
        assert row is not None
        assert row["predicate_id"] == cv.COUNT_PREDICATE
        corr = conn.execute(
            "SELECT value_text, revises_claim::text AS revises, correction_reason "
            "FROM claim WHERE revises_claim = %s::uuid",
            (target,),
        ).fetchone()
        assert corr is not None and corr["revises"] == target
        # the target's object_type is 'literal' — the bridge admits
        # value_text (+unit) only, so the corrected count rides value_text.
        assert corr["value_text"] == "225"
        assert corr["correction_reason"] == "acceptance_journey"
    finally:
        conn.close()


def test_append_only_re_sighting_left_two_occurrences(proof_out: dict[str, Any]) -> None:
    """Every fixture claim carries exactly two establishing bindings (the
    original capture + the later re-sighting capture) — appended, never
    rewritten."""
    conn = psycopg.connect(proof_out["dsn"], autocommit=True, row_factory=dict_row)
    try:
        rows = conn.execute(
            "SELECT ce.claim_id::text AS cid, count(*) AS n FROM claim_evidence ce "
            "JOIN claim c ON c.claim_id = ce.claim_id "
            "JOIN ingest_run r ON c.ingest_run_id = r.run_id "
            "WHERE r.connector_name = 'composed-fixture' "
            "GROUP BY ce.claim_id HAVING count(*) <> 2",
        ).fetchall()
        assert rows == [], f"fixture claims without exactly 2 occurrences: {rows}"
    finally:
        conn.close()
