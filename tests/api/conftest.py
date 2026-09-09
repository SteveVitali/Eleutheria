# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared fixtures for the public read API tests (P14.1, §37).

The store is the demo scenario (Appendix D.2 OKCPD device counts) extended with
the cases the acceptance criteria need: a C2 asset (coordinates truncated), a C4
asset (jurisdiction only), a restricted entity, and a second, incompatibly-
licensed source (ODbL) so the licence statement can be exercised both ways.
"""

from __future__ import annotations

from datetime import date

import pytest
from api.demo import build_demo_store
from api.store import EntityRecord, InMemoryStore
from evidence.tiers import CaptureMetadata, StorageTier
from policy.rights import RightsRecord
from policy.sensitivity import SensitivityClass
from starlette.testclient import TestClient

from api import create_app


@pytest.fixture
def store() -> InMemoryStore:
    s = build_demo_store()
    # A C2 asset: coordinates are published truncated to 2 dp (geo tier 1).
    s.add_entity(
        EntityRecord(
            entity_id="asset:c2",
            entity_type="asset",
            label="Hidden sensor (C2)",
            lat=35.4676234,
            lon=-97.5164276,
            sensitivity_class=SensitivityClass.C2,
        )
    )
    # A C4 asset: jurisdiction only, no coordinates ever (geo tier 3).
    s.add_entity(
        EntityRecord(
            entity_id="asset:c4",
            entity_type="asset",
            label="Confidential facility (C4)",
            lat=35.4676234,
            lon=-97.5164276,
            sensitivity_class=SensitivityClass.C4,
        )
    )
    # A restricted entity: not served through any tier (SIG-API-011).
    s.add_entity(
        EntityRecord(
            entity_id="agency:restricted",
            entity_type="agency",
            label="Restricted agency",
            visibility=StorageTier.RESTRICTED,
        )
    )
    # An ODbL source that cannot be merged with the CC-BY graph (SIG-LIC-004a).
    s.add_rights(
        RightsRecord(
            source_id="src:osm",
            spdx="ODbL-1.0",
            attribution="OpenStreetMap contributors",
            redistributable=True,
            derivative_permitted=True,
            terms_url="https://www.openstreetmap.org/copyright",
            retrieval_date=date(2026, 7, 1),
        )
    )
    # A restricted capture: metadata public, excerpt redacted, bytes never (SIG-EVID-010).
    s.add_capture(
        CaptureMetadata(
            capture_id="cap:restricted:1",
            source_id="src:records",
            source_uri="https://example/records/restricted.pdf",
            retrieved_at="2026-07-01",
            content_digest="c" + "0" * 40,
            media_type="application/pdf",
            tier=StorageTier.RESTRICTED,
            claims_supported=("contract",),
            title="Restricted memo",
            excerpt="sensitive body text",
        ),
        artifact_id="art:contract",
    )
    return s


@pytest.fixture
def client(store: InMemoryStore) -> TestClient:
    return TestClient(create_app(store))


# --- P19.4: Docker-gated PG harness for the API-over-Postgres tests (LD-F06) ---
#
# ``PgReadStore`` serves the read API over the real claim spine. Standing it up
# reuses the exact Docker/testcontainers + sqitch harness the claim-spine DB tests
# use (``tests/db/conftest.py``, loaded not re-invented). Gating mirrors it: no
# Docker daemon → the ``pg_dsn`` fixture skips, unless ``SIG_REQUIRE_DB_TESTS`` is
# set (CI), which makes a missing daemon a hard failure so the path never no-ops.

import importlib.util as _importlib_util  # noqa: E402
import time as _time  # noqa: E402
from collections.abc import Iterator as _Iterator  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
from typing import Any as _Any  # noqa: E402

_REPO_ROOT = _Path(__file__).resolve().parents[2]
_DB_DIR = _REPO_ROOT / "db"
_PG_IMAGE = "postgis/postgis:18-3.6"
_SQITCH_IMAGE = "sqitch/sqitch:latest"
_PG_USER = "sig"
_PG_PASSWORD = "sig"
_PG_DB = "sig"


def _load_db_conftest() -> _Any:
    path = _REPO_ROOT / "tests" / "db" / "conftest.py"
    spec = _importlib_util.spec_from_file_location("_sig_db_conftest_api", path)
    assert spec is not None and spec.loader is not None
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def pg_dsn() -> _Iterator[str]:
    """Start PG18+PostGIS, deploy the real sqitch plan, yield a DSN string."""
    db = _load_db_conftest()
    if not db._docker_reachable():
        db._require_or_skip("the Docker daemon is not reachable")

    import docker
    import psycopg
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network

    network = Network()
    network.create()
    container = (
        DockerContainer(_PG_IMAGE)
        .with_env("POSTGRES_USER", _PG_USER)
        .with_env("POSTGRES_PASSWORD", _PG_PASSWORD)
        .with_env("POSTGRES_DB", _PG_DB)
        .with_exposed_ports(5432)
        .with_network(network)
        .with_network_aliases("db")
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        deadline = _time.time() + 120
        last_err: Exception | None = None
        while _time.time() < deadline:
            try:
                with psycopg.connect(
                    host=host,
                    port=port,
                    user=_PG_USER,
                    password=_PG_PASSWORD,
                    dbname=_PG_DB,
                    connect_timeout=3,
                ):
                    break
            except Exception as exc:  # noqa: BLE001 - retry loop
                last_err = exc
                _time.sleep(1)
        else:
            raise RuntimeError(f"Postgres never became ready: {last_err}")
        client = docker.from_env()
        client.containers.run(
            _SQITCH_IMAGE,
            command=["deploy", f"db:pg://{_PG_USER}:{_PG_PASSWORD}@db:5432/{_PG_DB}"],
            network=network.name,
            working_dir="/repo",
            volumes={str(_DB_DIR): {"bind": "/repo", "mode": "ro"}},
            environment={"PGPASSWORD": _PG_PASSWORD},
            remove=True,
            stdout=True,
            stderr=True,
        )
        yield f"postgresql://{_PG_USER}:{_PG_PASSWORD}@{host}:{port}/{_PG_DB}"
    finally:
        container.stop()
        network.remove()
