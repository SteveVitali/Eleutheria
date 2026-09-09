# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ER over PostgreSQL — the review queue round-trips through the spine (P19.5, LD-F04).

Until P19.5 the probabilistic matches and the review queue lived only in memory (the
P19.3 composed run recorded this as ``LD-F04``, deferred from P19.4 by its size guard).
These Docker-gated tests cross that seam:

* ``sig-resolution match --dsn … --jurisdiction okc`` reads the OKCPD near-duplicate
  organisations out of the PG spine, scores them with the probabilistic matcher, and
  enqueues the tier-4/5 PROPOSED proposals as ``review_item`` rows;
* ``sig-resolution review decide --dsn …`` (``PgReviewQueue.decide``) appends **exactly
  one** append-only ``review_decision`` row per call — deciding the same item again
  appends a second row (a decision *history*), never an UPDATE/DELETE;
* the module contains no UPDATE/DELETE against the review tables (append-only, P1–P3).

Gating mirrors ``tests/db/conftest.py``: without a reachable Docker daemon the module
**skips**, but with ``SIG_REQUIRE_DB_TESTS=1`` a missing daemon is a **hard failure** so
the path can never silently no-op (never fabricate green).
"""

from __future__ import annotations

import importlib.util
import os
import re
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


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; ER-over-PG tests skip (P19.5)",
        allow_module_level=True,
    )


def _load_db_conftest() -> Any:
    path = REPO_ROOT / "tests" / "db" / "conftest.py"
    spec = importlib.util.spec_from_file_location("_sig_db_conftest_resolution", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pg_dsn() -> Iterator[str]:
    """Start PG18+PostGIS, deploy the real ``db/sqitch.plan``, yield a DSN string."""
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
        yield f"postgresql://{PG_USER}:{PG_PASSWORD}@{host}:{port}/{PG_DB}"
    finally:
        container.stop()
        network.remove()


# The OKCPD near-duplicate pair (+ a Tulsa sheriff that must NOT match them) seeded
# as `organization` projections with a jurisdiction identifier the match filter uses.
_ORGS = [
    ("okc:okcpd-1", "Oklahoma City Police Department", "us.le.municipal_police", "OK"),
    ("okc:okcpd-2", "Oklahoma City Police Dept", "us.le.municipal_police", "OK"),
    ("okc:tcso-1", "Tulsa County Sheriff Office", "us.le.sheriff", "OK"),
]


@pytest.fixture
def seeded_orgs(pg_dsn: str) -> str:
    """Seed the three OKC organisations and clear the review tables; return the DSN."""
    import psycopg

    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE review_decision, review_item CASCADE")
        conn.execute("DELETE FROM organization")
        conn.execute("DELETE FROM entity_identifier WHERE scheme = 'us.state'")
        for subject, canonical, org_type, state in _ORGS:
            row = conn.execute(
                "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
            ).fetchone()
            assert row is not None
            entity_id = row[0]
            conn.execute(
                "INSERT INTO organization(entity_id, organization_type, cached_canonical_name) "
                "VALUES (%s, %s, %s)",
                (entity_id, org_type, canonical),
            )
            conn.execute(
                "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (entity_id, "sig.connector.subject", subject),
            )
            conn.execute(
                "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (entity_id, "us.state", state),
            )
    return pg_dsn


def test_match_reads_pg_candidates_and_enqueues_proposals(
    seeded_orgs: str, capsys: pytest.CaptureFixture[str]
) -> None:
    # `sig-resolution match --dsn … --jurisdiction okc` reads the OKCPD near-duplicate
    # orgs from PG, scores them, and persists the tier-4/5 PROPOSED proposals.
    from resolution.cli import main

    rc = main(["match", "--dsn", seeded_orgs, "--jurisdiction", "okc"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "enqueued" in out and "PROPOSED" in out

    import psycopg

    with psycopg.connect(seeded_orgs, autocommit=True) as conn:
        n_items = conn.execute("SELECT count(*) FROM review_item").fetchone()[0]
    assert n_items >= 1, "match must persist at least one PROPOSED proposal to review_item"

    # Idempotent replay: scoring the same candidate set again enqueues nothing new.
    rc = main(["match", "--dsn", seeded_orgs, "--jurisdiction", "okc"])
    assert rc == 0
    with psycopg.connect(seeded_orgs, autocommit=True) as conn:
        n_items_after = conn.execute("SELECT count(*) FROM review_item").fetchone()[0]
    assert n_items_after == n_items, "replaying match must not duplicate proposals"


def test_review_decide_writes_exactly_one_row_and_history_on_repeat(seeded_orgs: str) -> None:
    from resolution.cli import main
    from resolution.review_pg import PgReviewQueue

    assert main(["match", "--dsn", seeded_orgs, "--jurisdiction", "okc"]) == 0

    queue = PgReviewQueue.from_dsn(seeded_orgs)
    pending = queue.pending()
    assert pending, "there should be a pending proposal to decide"
    item_id = pending[0].item_id

    # One `decide` call → exactly one append-only review_decision row.
    assert (
        main(
            [
                "review",
                "decide",
                item_id,
                "accept",
                "--reviewer",
                "curator:okc",
                "--dsn",
                seeded_orgs,
            ]
        )
        == 0
    )

    import psycopg

    with psycopg.connect(seeded_orgs, autocommit=True) as conn:
        n1 = conn.execute(
            "SELECT count(*) FROM review_decision WHERE item_id = %s", (item_id,)
        ).fetchone()[0]
    assert n1 == 1, "one decide call writes exactly one row"

    # The item leaves `pending` once decided.
    assert all(p.item_id != item_id for p in PgReviewQueue.from_dsn(seeded_orgs).pending())

    # Deciding the same item again appends a SECOND row (history on repeat), not an edit.
    assert (
        main(
            [
                "review",
                "decide",
                item_id,
                "reject",
                "--reviewer",
                "curator:okc",
                "--dsn",
                seeded_orgs,
            ]
        )
        == 0
    )
    with psycopg.connect(seeded_orgs, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT decision, reviewer FROM review_decision WHERE item_id = %s "
            "ORDER BY decided_at, decision_id",
            (item_id,),
        ).fetchall()
    assert len(rows) == 2, "deciding again appends a second row (append-only history)"
    assert [r[0] for r in rows] == ["accept", "reject"]
    assert all(r[1] == "curator:okc" for r in rows)


def test_decisions_are_appended_by_the_db_clock_and_carry_the_reviewer(seeded_orgs: str) -> None:
    from resolution.cli import main
    from resolution.review_pg import PgReviewQueue

    assert main(["match", "--dsn", seeded_orgs, "--jurisdiction", "okc"]) == 0
    queue = PgReviewQueue.from_dsn(seeded_orgs)
    item_id = queue.pending()[0].item_id
    decision = queue.decide(item_id, "accept", reviewer="curator:okc")
    assert decision.accepted and decision.reviewer == "curator:okc"
    assert decision.decided_at  # set by the DB, non-empty
    # A blank reviewer is refused (SIG-IDENT-026).
    other = queue.pending()
    if other:
        with pytest.raises(ValueError):
            queue.decide(other[0].item_id, "accept", reviewer="")


def test_pg_review_backend_is_append_only() -> None:
    # No UPDATE/DELETE anywhere in the PG review backend (append-only, P1–P3).
    src = (REPO_ROOT / "resolution" / "src" / "resolution" / "review_pg.py").read_text()
    assert not re.search(r"\bUPDATE\b|\bDELETE\b", src), "the PG review backend must be append-only"
