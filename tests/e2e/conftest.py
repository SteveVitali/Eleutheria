# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Docker-gated harness for the composed end-to-end stack (P19.3, CAPSTONE step 3).

The composed suite drives the whole build as one unit for the first time — the
PG18+PostGIS claim spine (deployed with the real ``db/sqitch.plan``) through the
OCFL evidence store, connector replay, entity resolution, the reconciliation
resolver, the API, exports, and the ``web/`` build.  It reuses the **exact**
Docker/testcontainers + sqitch harness the claim-spine DB tests use
(``tests/db/conftest.py``), so the composed run stands the schema up the way
production does (§20.4, §48; SIG-STORE-024/041).

Gating mirrors ``tests/db/conftest.py:_require_or_skip`` (imported below, not
re-invented): without a reachable Docker daemon the module **skips**, but with
``SIG_REQUIRE_DB_TESTS=1`` (CI sets it) a missing daemon is a **hard failure** so
the composed path can never silently no-op (never fabricate green).
"""

from __future__ import annotations

import importlib.util
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"

PG_IMAGE = "postgis/postgis:18-3.6"
SQITCH_IMAGE = "sqitch/sqitch:latest"
PG_USER = "sig"
PG_PASSWORD = "sig"
PG_DB = "sig"


def _load_db_conftest() -> Any:
    """Load ``tests/db/conftest.py`` as a module to reuse its helpers verbatim.

    ``tests/db`` is not an importable package, so the append-only re-proof and the
    gate helper are loaded from the file directly rather than duplicated here
    (single home for ``_require_or_skip`` / ``seed_claim_prerequisites`` /
    ``insert_claim``).
    """
    path = REPO_ROOT / "tests" / "db" / "conftest.py"
    spec = importlib.util.spec_from_file_location("_sig_db_conftest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DB = _load_db_conftest()
_require_or_skip = _DB._require_or_skip
_docker_reachable = _DB._docker_reachable
seed_claim_prerequisites = _DB.seed_claim_prerequisites
insert_claim = _DB.insert_claim


@pytest.fixture(scope="session")
def composed_db() -> Iterator[dict[str, object]]:
    """Start PG18+PostGIS, deploy the real ``db/sqitch.plan``, yield conn params.

    A byte-for-byte reuse of the claim-spine harness (``tests/db/conftest.py``):
    the container runs on a shared Docker network and sqitch deploys the plan
    from its official image, so the host needs only Docker.  (S1 asserts this
    deployment landed.)
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
def composed_conn(composed_db: dict[str, object]) -> Iterator[Any]:
    """A per-test superuser connection whose writes are rolled back."""
    import psycopg

    connection = psycopg.connect(
        host=composed_db["host"],
        port=composed_db["port"],
        user=composed_db["user"],
        password=composed_db["password"],
        dbname=composed_db["dbname"],
        autocommit=False,
    )
    try:
        yield connection
        connection.rollback()
    finally:
        connection.rollback()
        connection.close()
