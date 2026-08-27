# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Live-Postgres test harness for the claim spine (P02.1).

These are the CI-blocking database tests (§48; SIG-STORE-024). They stand up a
real PostgreSQL 18 + PostGIS instance in a throwaway container (testcontainers),
apply the schema with **sqitch** exactly as production would (§20.4,
SIG-STORE-041), and exercise the append-only, exclusion-constraint, and RLS
behaviour against the running engine — never a mock.

sqitch is run from its official image on a shared Docker network, so the host
needs only Docker (no local Perl/sqitch). If the Docker daemon is unreachable the
tests skip — unless SIG_REQUIRE_DB_TESTS is set (CI sets it), in which case a
missing daemon is a hard failure so the suite can never silently no-op.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"

PG_IMAGE = "postgis/postgis:18-3.6"
SQITCH_IMAGE = "sqitch/sqitch:latest"
PG_USER = "sig"
PG_PASSWORD = "sig"
PG_DB = "sig"


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


def _require_or_skip(reason: str) -> None:
    if os.environ.get("SIG_REQUIRE_DB_TESTS"):
        pytest.fail(f"DB tests are required (SIG_REQUIRE_DB_TESTS set) but {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def sig_database() -> Iterator[dict[str, object]]:
    """Start PG18+PostGIS, deploy the sqitch plan, yield connection params."""
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")

    import docker
    import psycopg
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

        # Wait for a genuine connection (the image restarts once after init).
        deadline = time.time() + 120
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with psycopg.connect(
                    host=host,
                    port=port,
                    user=PG_USER,
                    password=PG_PASSWORD,
                    dbname=PG_DB,
                    connect_timeout=3,
                ):
                    break
            except Exception as exc:  # noqa: BLE001 - retry loop
                last_err = exc
                time.sleep(1)
        else:
            raise RuntimeError(f"Postgres never became ready: {last_err}")

        # Apply the schema with sqitch, on the shared network so it reaches `db`.
        client = docker.from_env()
        client.containers.run(
            SQITCH_IMAGE,
            command=["deploy", f"db:pg://{PG_USER}:{PG_PASSWORD}@db:5432/{PG_DB}"],
            network=network.name,
            working_dir="/repo",
            volumes={str(DB_DIR): {"bind": "/repo", "mode": "ro"}},
            environment={"PGPASSWORD": PG_PASSWORD},
            remove=True,
            stdout=True,
            stderr=True,
        )

        yield {
            "host": host,
            "port": port,
            "user": PG_USER,
            "password": PG_PASSWORD,
            "dbname": PG_DB,
        }
    finally:
        container.stop()
        network.remove()


@pytest.fixture
def conn(sig_database: dict[str, object]) -> Iterator[object]:
    """A per-test superuser connection; every test's writes are rolled back."""
    import psycopg

    connection = psycopg.connect(
        host=sig_database["host"],
        port=sig_database["port"],
        user=sig_database["user"],
        password=sig_database["password"],
        dbname=sig_database["dbname"],
        autocommit=False,
    )
    try:
        yield connection
        connection.rollback()
    finally:
        connection.rollback()
        connection.close()


def seed_claim_prerequisites(conn: object) -> dict[str, object]:
    """Insert the minimum FK targets a claim needs; return the ids used.

    Uses the origin-via-`asserted_by` path (a person entity + rationale) so the
    fixture does not need the full evidence/extraction chain (that is P02.2).
    """
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','integer','quantity','fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        ("contracted_camera_count",),
    )
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) "
        "VALUES('Apache-2.0','yes','yes','2026-01-01') RETURNING rights_id"
    )
    rights_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests) "
        "VALUES('fixture','0','sha','r1','1.0.0','{}','{}','{}') RETURNING run_id"
    )
    run_id = cur.fetchone()[0]
    cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    subject_id = cur.fetchone()[0]
    cur.execute("INSERT INTO entity(entity_type) VALUES('person') RETURNING entity_id")
    author_id = cur.fetchone()[0]
    return {
        "predicate_id": "contracted_camera_count",
        "rights_id": rights_id,
        "run_id": run_id,
        "subject_id": subject_id,
        "author_id": author_id,
    }


def insert_claim(
    conn: object,
    prereqs: dict[str, object],
    *,
    value_text: str = "25",
    value_num: int = 25,
    sensitivity_tier: int = 0,
    observed_at: str = "2026-05-01T00:00:00Z",
    revises_claim: object = None,
    correction_reason: object = None,
) -> object:
    """Insert one claim via the asserted_by origin path; return its claim_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,value_num,unit,raw_value,observed_at,source_reliability,"
        "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
        "ingest_run_id,rights_id,sensitivity_tier,revises_claim,correction_reason) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'cameras',%s,%s,'R1','D1','I1',"
        "%s,'fixture',%s,%s,%s,%s,%s) RETURNING claim_id",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            value_text,
            value_num,
            value_text,
            observed_at,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            sensitivity_tier,
            revises_claim,
            correction_reason,
        ),
    )
    return cur.fetchone()[0]
