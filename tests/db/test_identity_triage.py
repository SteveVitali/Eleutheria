# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of the P31.3 duplicate-identifier triage (ADR-110, D-P30.4-3).

Every ``(scheme, value)`` shared by more than one entity gets a recorded same_as or
distinct decision through the existing review-queue writer. The recording is
append-only: both identifier rows stay, and so do the entities and claims. A re-run
is +0. The read-only report exits non-zero while any pair is undecided.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest

_TABLES = (
    "review_decision",
    "review_item",
    "entity_identity_key",
    "entity_identifier",
    "organization",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _entity_with(conn: psycopg.Connection[Any], *identifiers: tuple[str, str]) -> str:
    eid = str(
        conn.execute(
            "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
        ).fetchone()[0]
    )
    for scheme, value in identifiers:
        conn.execute(
            "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s)",
            (eid, scheme, value),
        )
    return eid


def test_every_duplicate_pair_gets_an_append_only_decision(clean_dsn: str, tmp_path: Path) -> None:
    from resolution.cli import main

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        a = _entity_with(conn, ("sig.connector.subject", "agency:x-1"), ("us.state", "XX"))
        b = _entity_with(conn, ("sig.connector.subject", "agency:x-2"), ("us.state", "XX"))
        r1 = _entity_with(conn, ("sig.connector.subject", "cam:1"))
        r2 = _entity_with(conn, ("sig.connector.subject", "cam:1"))
        identifiers_before = conn.execute("SELECT count(*) FROM entity_identifier").fetchone()[0]

    decisions = {
        "decisions": [
            {
                "scheme": "us.state",
                "value": "XX",
                "entities": [b, a],
                "decision": "distinct",
                "rationale": "two agencies that share a state",
                "evidence": {"why": "test"},
            },
            {
                "scheme": "sig.connector.subject",
                "value": "cam:1",
                "entities": [r1, r2],
                "decision": "same_as",
                "rationale": "race duplicate",
            },
        ]
    }
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps(decisions), encoding="utf-8")
    args = ["identity-triage", "--dsn", clean_dsn, "--decisions", str(path)]

    # Read-only: two pairs, both undecided, exit 1; nothing written.
    assert main(args) == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM review_item").fetchone()[0] == 0

    assert main([*args, "--apply"]) == 0
    assert main([*args, "--apply"]) == 0  # +0 re-run
    assert main(args) == 0  # every pair now decided

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT ri.kind, ri.payload->>'scheme', rd.decision, rd.reviewer, rd.rationale"
            "  FROM review_decision rd JOIN review_item ri USING (item_id) ORDER BY 2"
        ).fetchall()
        # Append-only: every identifier row is still there, so the duplicate query
        # still returns both pairs.
        assert conn.execute("SELECT count(*) FROM entity_identifier").fetchone()[0] == (
            identifiers_before
        )
        dup = conn.execute(
            "SELECT count(*) FROM (SELECT 1 FROM entity_identifier GROUP BY scheme, value "
            "HAVING count(DISTINCT entity_id) > 1) d"
        ).fetchone()[0]
    assert dup == 2
    assert [(r[0], r[1], r[2]) for r in rows] == [
        ("er_match", "sig.connector.subject", "accept"),
        ("er_match", "us.state", "reject"),
    ]
    assert all(r[3].startswith("engineering:P31.3") and r[4] for r in rows)


def test_a_pair_without_a_committed_decision_stays_undecided(
    clean_dsn: str, tmp_path: Path
) -> None:
    from resolution.cli import main

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _entity_with(conn, ("sig.connector.subject", "orphan:1"))
        _entity_with(conn, ("sig.connector.subject", "orphan:1"))
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps({"decisions": []}), encoding="utf-8")
    assert main(["identity-triage", "--dsn", clean_dsn, "--decisions", str(path), "--apply"]) == 1


def test_the_packaged_decisions_cover_the_three_hosted_pairs() -> None:
    from resolution.identity_triage import load_decisions

    decisions = load_decisions()
    assert {(d["scheme"], d["value"]) for d in decisions} == {
        ("sig.connector.subject", "traffic_camera:camreg_camilo_schools:camilo_schools_cctv:1"),
        ("us.state", "OK"),
        ("fr.insee", "01"),
    }
    assert all(len(set(d["entities"])) == 2 and d["evidence"] for d in decisions)
