# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The REAL local restore drill (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075).

This is the deterministic proxy for the gate-pending cloud restore (D-DEPLOY.1-1):
over a real PG18+PostGIS container it seeds the claim spine, `pg_dump`s it, restores
the dump into a *fresh* database, and asserts the graph (claim / evidence / entity
counts) reproduces. The SQL tools run INSIDE the container via `docker exec`, so the
host needs only Docker (no local `pg_dump`). Skips without Docker unless
`SIG_REQUIRE_DB_TESTS` is set (then a missing daemon fails loudly).
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from conftest import (  # reuse the exact production-shaped harness
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

from ops import backup as B

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"


@pytest.fixture(scope="module")
def drill_db() -> Iterator[dict[str, object]]:
    """A dedicated PG18+PostGIS container + sqitch schema, with COMMITTED seed data.

    Separate from the session `sig_database` fixture because the drill needs data
    that survives (committed, not rolled back) so `pg_dump` can capture it, plus the
    wrapped container object to run the SQL tools via `docker exec`.
    """
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

        # Seed COMMITTED graph data (autocommit) so pg_dump captures it.
        host_dsn = f"postgresql://{PG_USER}:{PG_PASSWORD}@{host}:{port}/{PG_DB}"
        with psycopg.connect(host_dsn, autocommit=True) as conn:
            prereqs = seed_claim_prerequisites(conn)
            insert_claim(conn, prereqs, value_text="299", value_num=299)
            insert_claim(conn, prereqs, value_text="190", value_num=190)

        yield {
            "host": host,
            "port": port,
            "host_dsn": host_dsn,
            "container": container.get_wrapped_container(),
        }
    finally:
        container.stop()
        network.remove()


def _exec_runner(container: object) -> B.Runner:
    """A backup.Runner that executes SQL tools INSIDE the PG container."""

    def run(argv: Sequence[str]) -> B.RunResult:
        code, output = container.exec_run(list(argv))  # type: ignore[attr-defined]
        text = output.decode("utf-8", "replace") if isinstance(output, bytes) else str(output)
        return B.RunResult(returncode=int(code), stdout=text, stderr=text)

    return run


def test_restore_drill_reproduces_the_graph(drill_db: dict[str, object]) -> None:
    host_dsn = str(drill_db["host_dsn"])
    # DSNs as seen from INSIDE the container (localhost) for the SQL tools.
    tool_dsn = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:5432/{PG_DB}"

    report = B.restore_drill(
        source_dsn=tool_dsn,
        admin_dsn=tool_dsn,
        host_source_dsn=host_dsn,
        host_target_dsn=B.swap_dbname(host_dsn, "sig_restore"),
        target_dbname="sig_restore",
        dump_path="/tmp/sig-restore-drill.dump",
        run=_exec_runner(drill_db["container"]),
    )

    # The graph reproduces: every spine table's cardinality matches after restore.
    assert report.reproduced, report.as_json()
    # …and it is a MEANINGFUL graph (the two seeded claims + their entities survive).
    assert report.source_counts["claim"] == 2
    assert report.restored_counts["claim"] == 2
    assert report.restored_counts["entity"] == report.source_counts["entity"] > 0
    assert report.restored_counts["evidence_artifact"] == report.source_counts["evidence_artifact"]
