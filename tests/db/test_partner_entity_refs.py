# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of P31.5 (ADR-112): partner entity-ref claims on the claim spine.

The committed partner fixture set is replayed through the REAL connector stages
(``tests/partner_fixtures.py``) and written by the production-wired ``PgClaimSink``
(``object_resolver = record_object_ref``). No ``object_entity`` row is hand-inserted.

* The sink writes ``object_type='entity_ref'`` claims whose ``object_entity`` is an
  ``organization`` entity, minted once per partner identifier through the identity
  guard, labelled by an ``organization`` row; the text claims stay literal and exactly
  the base-commit text claims; a replay inserts +0.
* Person-shaped and ambiguous partners mint nothing (Part VIII).
* The P28.6 accountability materializer produces > 0 links from those claims (re-run
  +0), anchored only on real deployments (procured ≠ deployed). The P28.2 edge
  materializer reads them and honestly produces 0 edges: a buyer is not an access edge
  (the access-edge claims are P31.6). The export's sharing-edge read excludes them.
* The ``partner_org_identity_key`` backfill adopts a legacy partner identifier.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from partner_fixtures import GOLDEN, fixture_records

_SPINE_TABLES = (
    "inference.derived_fact",
    "relationship",
    "organization",
    "ingest_run_completion",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identity_key",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)

_DEPLOY = Path(__file__).resolve().parents[2] / "db" / "deploy" / "partner_org_identity_key.sql"
_WSDOT = "washington state department of transportation"


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _land(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    """Write every fixture run through a production-wired PG sink (one run each)."""
    from db.claim_sink import PgClaimSink, record_object_ref

    reports = {}
    for key, records in fixture_records().items():
        sink = PgClaimSink(conn, connector_name=key, object_resolver=record_object_ref)
        sink.assert_claims(records)
        reports[key] = sink.report
    return reports


def _count(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def test_the_sink_writes_entity_ref_claims_beside_unchanged_text_claims(clean_dsn: str) -> None:
    from db.claim_sink import content_digest
    from partner_fixtures import golden_digest

    records = fixture_records()
    text = {
        content_digest(r)
        for rows in records.values()
        for r in rows
        if r.get("record_kind", "claim") == "claim" and "object_ref" not in r
    }
    refs = {content_digest(r) for rows in records.values() for r in rows if "object_ref" in r}
    golden = {d for v in json.loads(GOLDEN.read_text())["runs"].values() for d in v}
    # The text claims are the base-commit records — compared with the stamped
    # `vocab_version` normalized back (a §20 vocabulary migration restamps record
    # provenance without changing claim content; `golden_digest` does exactly
    # that). The stored comparison below keeps the raw digest.
    text_base = {
        golden_digest(key, r)
        for key, rows in records.items()
        for r in rows
        if r.get("record_kind", "claim") == "claim" and "object_ref" not in r
    }
    assert refs and text_base <= golden

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn)
        stored = conn.execute(
            "SELECT c.content_digest, c.object_type, c.object_entity::text, oe.entity_type,"
            "       c.value_text"
            "  FROM claim c LEFT JOIN entity oe ON oe.entity_id = c.object_entity"
        ).fetchall()
        literal = {r[0] for r in stored if r[1] == "literal"}
        entity_ref = {r[0] for r in stored if r[1] == "entity_ref"}
        # The spine holds exactly the text claims as literals and the new records as refs.
        assert literal == text
        assert entity_ref == refs
        for _digest, object_type, object_entity, object_entity_type, value_text in stored:
            if object_type == "entity_ref":
                assert object_entity is not None and object_entity_type == "organization"
                assert value_text  # the claim still states the party's name (value shape)
            else:
                assert object_entity is None

        # One organisation per partner identifier, however many sources name it: the
        # WSDOT contract buyer, USAspending recipient, both camera operators and the
        # Atlas event all point at ONE entity.
        wsdot = conn.execute(
            "SELECT DISTINCT c.object_entity FROM claim c"
            "  JOIN entity_identity_key k ON k.entity_id = c.object_entity"
            " WHERE k.scheme = 'sig.org.name' AND k.value = %s",
            (_WSDOT,),
        ).fetchall()
        assert len(wsdot) == 1
        assert (
            _count(
                conn,
                "SELECT count(DISTINCT c.predicate_id) FROM claim c WHERE c.object_entity = %s",
                (wsdot[0][0],),
            )
            == 4  # buyer, recipient, camera_operator, event_organizations
        )

        orgs = conn.execute(
            "SELECT o.cached_canonical_name, o.organization_type,"
            "       o.publication_review_required, o.identity_basis ->> 'scheme'"
            "  FROM organization o ORDER BY 1"
        ).fetchall()
        assert {r[0] for r in orgs} == {
            "City of Example Falls",
            "Example Traffic Camera Systems LLC",
            "Polska Agencja Żeglugi Powietrznej",
            "Washington State Department of Transportation",
        }
        assert {r[1:] for r in orgs} == {("unclassified", True, "sig.org.name")}
        from resolution.partner_identity import partner_rules_version

        rules = conn.execute(
            "SELECT DISTINCT identity_basis ->> 'rules' FROM organization"
        ).fetchall()
        assert rules == [(partner_rules_version(),)]  # the deciding ruleset is recorded
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'organization'") == 4
        assert (
            _count(conn, "SELECT count(*) FROM entity_identity_key WHERE scheme = 'sig.org.name'")
            == 4
        )


def test_person_shaped_and_ambiguous_partners_mint_nothing(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn)
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'person'") == 0
        for refused in (
            "jane q public dba jqp consulting",
            "john a smith",
            "john q citizen",
            "jane doe",
            "police department",
            "department of transportation",
            "king county wsdot",
            "20009020700016",
            "31483054800140",
        ):
            assert (
                _count(
                    conn,
                    "SELECT count(*) FROM entity_identifier WHERE scheme = 'sig.org.name'"
                    " AND value = %s",
                    (refused,),
                )
                == 0
            ), refused
        # ...and each still stands as its text claim (the literal is never dropped).
        for name in ("John A. Smith", "JOHN Q CITIZEN", "Police Department"):
            assert _count(conn, "SELECT count(*) FROM claim WHERE value_text = %s", (name,)) == 1, (
                name
            )


def test_a_replay_inserts_nothing(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        first = _land(conn)
        before = [
            _count(conn, f"SELECT count(*) FROM {t}")
            for t in ("claim", "entity", "organization", "entity_identity_key")
        ]
        again = _land(conn)
        after = [
            _count(conn, f"SELECT count(*) FROM {t}")
            for t in ("claim", "entity", "organization", "entity_identity_key")
        ]
    assert sum(r.inserted for r in first.values()) > 0
    assert sum(r.inserted for r in again.values()) == 0
    assert sum(r.entities for r in again.values()) == 0
    assert before == after


def test_the_materializers_run_over_the_emitted_claims(clean_dsn: str) -> None:
    from exports.shaping import _queries_for
    from inference.accountability import (
        materialize_accountability_links,
        read_materialized_accountability_links,
    )
    from reconcile.materialize import materialize_sharing_edges
    from resolution.partner_identity import PARTNER_PREDICATES

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn)
        cameras = {
            str(r[0])
            for r in conn.execute(
                "SELECT entity_id FROM entity_identifier WHERE scheme = 'sig.connector.subject'"
                " AND value LIKE 'traffic_camera:%%'"
            ).fetchall()
        }
        assert len(cameras) == 2

        links = materialize_accountability_links(conn)
        assert links.inserted > 0
        assert links.by_link_type == {
            # camera --operator--> WSDOT <--buyer-- contract C-001
            "procured_under_contract": 2,
            # ...and that contract's seller
            "has_vendor": 2,
            # camera --operator--> WSDOT <--recipient-- the USAspending award
            "funded_by": 2,
            # camera --operator--> WSDOT <--organizations-- the Atlas event
            "overseen_by": 2,
        }
        rows = read_materialized_accountability_links(conn)
        entity_ref_claims = {
            str(r[0])
            for r in conn.execute(
                "SELECT claim_id FROM claim WHERE object_type = 'entity_ref'"
            ).fetchall()
        }
        for row in rows:
            # Anchored only on the real camera deployments, never on a procurement
            # record or an event (procured ≠ deployed).
            assert row["deployment_id"] in cameras
            # Every link cites spine claims, and those are the emitted entity-refs.
            assert set(row["establishing_claims"]) <= entity_ref_claims
        rerun = materialize_accountability_links(conn)
        assert (rerun.inserted, rerun.skipped_existing) == (0, links.inserted)

        edges = materialize_sharing_edges(conn)
        # The edge reader considers every entity-ref claim, but a buyer / seller /
        # operator is not a §12.2 access edge: none is coerced into one (SIG-ONTO-042).
        # Access-edge claims are P31.6.
        assert edges.considered_claims == len(entity_ref_claims) > 0
        assert (edges.observations, edges.inserted) == (0, 0)
        assert materialize_sharing_edges(conn).inserted == 0

        # The export's sharing-edge read leaves the partner entity-refs out.
        shared = conn.execute(_queries_for(True)["sharing_edges"]).fetchall()
        assert not {r[2] for r in shared} & PARTNER_PREDICATES


def test_a_person_object_is_refused_and_nothing_is_written(clean_dsn: str) -> None:
    from db.claim_sink import EntityRef, PgClaimSink, record_object_ref

    claim = {
        "subject_id": "contract:src:1",
        "predicate_id": "seller",
        "value": "John A. Smith",
        "source_id": "src",
        "object_ref": {"scheme": "sig.org.name", "value": "john a smith", "entity_type": "person"},
    }
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="p", object_resolver=record_object_ref)
        with pytest.raises(ValueError, match="Part VIII"):
            sink.assert_claims([claim])

        def person(_claim: Any) -> EntityRef:
            return EntityRef("sig.org.name", "john a smith", "person")

        other = PgClaimSink(conn, connector_name="p2", object_resolver=person)
        with pytest.raises(ValueError, match="Part VIII"):
            other.assert_claims([{k: v for k, v in claim.items() if k != "object_ref"}])
        assert _count(conn, "SELECT count(*) FROM claim") == 0
        assert _count(conn, "SELECT count(*) FROM entity") == 0


def test_the_backfill_adopts_a_legacy_partner_identifier(clean_dsn: str) -> None:
    from db.claim_sink import PgClaimSink, record_object_ref

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # An unguarded writer's identifiers: two entities for one partner name.
        first = conn.execute(
            "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
        ).fetchone()[0]
        second = conn.execute(
            "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
        ).fetchone()[0]
        for entity_id in (first, second):
            conn.execute(
                "INSERT INTO entity_identifier(entity_id, scheme, value)"
                " VALUES (%s, 'sig.org.name', 'acme surveillance inc')",
                (entity_id,),
            )
        # The deploy script's backfill (+ its fail-closed check) keys the earliest one.
        conn.execute(_DEPLOY.read_text())
        keyed = conn.execute(
            "SELECT entity_id, backfilled FROM entity_identity_key"
            " WHERE scheme = 'sig.org.name' AND value = 'acme surveillance inc'"
        ).fetchall()
        assert keyed == [(first, True)]
        conn.execute(_DEPLOY.read_text())  # re-runnable: +0

        # A new entity-ref claim for the same partner reuses that entity.
        PgClaimSink(conn, connector_name="adopt", object_resolver=record_object_ref).assert_claims(
            [
                {
                    "subject_id": "contract:src:9",
                    "predicate_id": "seller",
                    "value": "Acme Surveillance, Inc.",
                    "source_id": "src",
                    "object_ref": {
                        "scheme": "sig.org.name",
                        "value": "acme surveillance inc",
                        "entity_type": "organization",
                        "label": "Acme Surveillance, Inc.",
                    },
                }
            ]
        )
        assert (
            conn.execute(
                "SELECT object_entity FROM claim WHERE predicate_id = 'seller'"
            ).fetchone()[0]
            == first
        )
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'organization'") == 2
