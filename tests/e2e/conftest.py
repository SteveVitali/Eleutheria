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
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


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

    The claim-spine harness (``tests/db/conftest.py``, shared helpers — P34.24a):
    the plan database is created ``TEMPLATE template0`` so the plan owns its
    extensions (ADR-196), and sqitch deploys with ``--verify`` from the
    digest-pinned image.  (S1 asserts this deployment landed.)
    """
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")

    with _DB.pg_container() as (network, host, port):
        _DB.create_plan_database(host, port, _DB.PG_DB)
        _DB.run_sqitch(network, "deploy", "--verify", dbname=_DB.PG_DB)
        yield {
            "host": host,
            "port": port,
            "user": _DB.PG_USER,
            "password": _DB.PG_PASSWORD,
            "dbname": _DB.PG_DB,
        }


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
