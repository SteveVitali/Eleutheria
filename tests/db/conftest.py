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

P34.24a / ADR-196 lifecycle hygiene:

- The sqitch image is pinned **by digest** — a mutable `sqitch/sqitch:<tag>`
  reference fails `tests/unit/test_sqitch_hygiene.py`.
- The database the plan deploys into is created ``TEMPLATE template0``
  (`create_plan_database`), not the postgis image's initdb database. The image
  pre-installs postgis + postgis_topology + postgis_tiger_geocoder +
  fuzzystrmatch into its own database, where the plan's `CREATE EXTENSION IF
  NOT EXISTS` is a silent no-op and `revert/extensions.sql` drops objects the
  plan never owned (the D-P32.16a-1 defect). A template0 database starts with
  **no** extensions, so the plan owns exactly the extensions it creates — the
  deployment shape the claim spine actually runs under.
- `run_sqitch` deploys with `--verify`, so the whole plan's verify scripts run
  against the running engine on every harness use — the stale-verify defect
  class (D-P32.10a-1) can no longer hide behind a deploy-only harness.

The container/sqitch helpers are module-level so the sibling harnesses
(`tests/e2e`, `tests/api`, `tests/resolution`) reuse them through
`_load_db_conftest()` instead of drifting copies.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"

PG_IMAGE = "postgis/postgis:18-3.6"
# P34.24a / ADR-196: pinned by digest — the mutable `latest` tag's resolution
# at writing (docker pull + docker inspect 2026-10-04; App::Sqitch v1.6.1).
SQITCH_IMAGE = (
    "sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3"
)
PG_USER = "sig"
PG_PASSWORD = "sig"
# The image's own initdb database — postgis (and its dependents) land here and
# are NOT plan-owned; sqitch never deploys into it.
PG_ADMIN_DB = "postgres"
# The database the sqitch plan deploys into — created TEMPLATE template0, so
# the plan owns every extension it creates (ADR-196).
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


def wait_ready(host: str, port: int, *, dbname: str = PG_ADMIN_DB, timeout: float = 120.0) -> None:
    """Block until postgres is stable — the image restarts once after initdb,
    so require two consecutive real connections a second apart (a single probe
    can pass inside the restart window and a later sqitch connect then fails)."""
    import psycopg

    deadline = time.time() + timeout
    last_err: Exception | None = None
    ok = 0
    while time.time() < deadline:
        try:
            with psycopg.connect(
                host=host,
                port=port,
                user=PG_USER,
                password=PG_PASSWORD,
                dbname=dbname,
                connect_timeout=3,
            ):
                ok += 1
                if ok >= 2:
                    return
        except Exception as exc:  # noqa: BLE001 - retry loop
            last_err = exc
            ok = 0
        time.sleep(1)
    raise RuntimeError(f"Postgres never became ready: {last_err}")


def create_plan_database(
    host: str, port: int, dbname: str = PG_DB, *, template: str = "template0"
) -> None:
    """Drop+create `dbname` from `template0` (ADR-196).

    A template0 database carries **no** extensions — unlike the postgis image's
    initdb database or `template_postgis` — so `deploy/extensions.sql` really
    installs postgis + btree_gist and the plan owns exactly what it creates.
    The connect goes to `PG_ADMIN_DB` (the image's own database); `dbname` is an
    internal constant, rendered as a quoted identifier.
    """
    import psycopg
    from psycopg import sql

    with psycopg.connect(
        host=host,
        port=port,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_ADMIN_DB,
        autocommit=True,
    ) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(dbname)))
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                sql.Identifier(dbname), sql.Identifier(template)
            )
        )


def run_sqitch(network: str, *argv: str, dbname: str = PG_DB) -> bytes:
    """Run one sqitch command against `dbname` from the pinned image.

    The plan directory is mounted read-only; the sqitch registry lives in the
    database. Raises `docker.errors.ContainerError` (loud) on a non-zero exit.
    """
    import docker

    client = docker.from_env()
    return client.containers.run(
        SQITCH_IMAGE,
        command=[*argv, f"db:pg://{PG_USER}:{PG_PASSWORD}@db:5432/{dbname}"],
        network=network,
        working_dir="/repo",
        volumes={str(DB_DIR): {"bind": "/repo", "mode": "ro"}},
        environment={"PGPASSWORD": PG_PASSWORD},
        remove=True,
        stdout=True,
        stderr=True,
    )


@contextmanager
def pg_container() -> Iterator[tuple[str, str, int]]:
    """Start PG18+PostGIS on its own throwaway network; yield (network, host, port).

    The image's own database is `PG_ADMIN_DB` — the sqitch plan is never
    deployed there; callers create plan databases via `create_plan_database`.
    """
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network

    network = Network()
    network.create()
    container = (
        DockerContainer(PG_IMAGE)
        .with_env("POSTGRES_USER", PG_USER)
        .with_env("POSTGRES_PASSWORD", PG_PASSWORD)
        .with_env("POSTGRES_DB", PG_ADMIN_DB)
        .with_exposed_ports(5432)
        .with_network(network)
        .with_network_aliases("db")
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        wait_ready(host, port)
        yield network.name, host, port
    finally:
        container.stop()
        network.remove()


@pytest.fixture(scope="session")
def sig_database() -> Iterator[dict[str, object]]:
    """Start PG18+PostGIS, deploy the sqitch plan, yield connection params."""
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")

    with pg_container() as (network, host, port):
        create_plan_database(host, port, PG_DB)
        run_sqitch(network, "deploy", "--verify", dbname=PG_DB)
        yield {
            "host": host,
            "port": port,
            "user": PG_USER,
            "password": PG_PASSWORD,
            "dbname": PG_DB,
        }


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


def _id_of(row: object, name: str) -> object:
    """The generated id off a RETURNING row — works for tuple-row cursors and
    dict-row connections alike (fixtures run on both)."""
    if row is None:
        raise RuntimeError(f"expected a {name} row")
    if hasattr(row, "keys"):  # dict_row / RealDictCursor
        return row[name]  # type: ignore[index]
    return row[0]  # type: ignore[index]


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
    rights_id = _id_of(cur.fetchone(), "rights_id")
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests) "
        "VALUES('fixture','0','sha','r1','1.0.0','{}','{}','{}') RETURNING run_id"
    )
    run_id = _id_of(cur.fetchone(), "run_id")
    cur.execute("INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id")
    subject_id = _id_of(cur.fetchone(), "entity_id")
    cur.execute("INSERT INTO entity(entity_type) VALUES('person') RETURNING entity_id")
    author_id = _id_of(cur.fetchone(), "entity_id")
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
    return _id_of(cur.fetchone(), "claim_id")
