# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.10 — the §43.5 asset-promotion gate over the real spine (SIG-PUB-012).

The composed-db twin of ``tests/unit/test_policy_promotion.py``, over the
real sqitch-deployed PG18+PostGIS spine:

* a permitted promotion's claims mint a ``physical_asset`` entity (the
  ``promoted:`` subject family the committed map declares), land
  ``fixed_asset_location`` geometry and append the candidate's recorded
  ``candidate_promotion_status = 'promoted'`` on its ``candidate:`` subject
  (which mints ``candidate_asset``);
* the refusal path mints nothing — :func:`promotion_claims` raises
  :class:`PromotionRefused` before a claim exists, and a bare corroborated
  candidate leaves only its own row;
* the promotion is append-only: a second identical write inserts +0.

DB-gated: these run under ``SIG_REQUIRE_DB_TESTS`` (``make test-db``) and
skip without Docker — the conftest's autouse typer stub is deliberately
bypassed by constructing the sink with the REAL map explicitly.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from policy.promotion import (
    CandidateForPromotion,
    Confirmation,
    ConfirmationKind,
    PromotionRefused,
    promotion_claims,
)

_TRUNCATE = (
    "TRUNCATE claim_evidence, assertion_quarantine, claim, extraction, "
    "evidence_capture, evidence_blob, evidence_artifact, entity_identifier, "
    "entity_type_decision, entity_identity_key, ingest_run, source_registry, "
    "entity CASCADE"
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """A DSN whose spine is truncated before AND after the test."""
    dsn = _dsn(sig_database)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)


def _real_map_sink(dsn: str, **kwargs: Any) -> Any:
    """A sink whose subject typer is the committed map — explicit, so the
    conftest stub cannot soften the fail-closed contract these tests pin.
    """
    from db.claim_sink import PgClaimSink
    from db.subject_types import entity_type_for_subject

    return PgClaimSink.from_dsn(
        dsn,
        connector_name="asset_promotion_test",
        connector_version="1.0.0",
        code_commit="p37.10-test",
        subject_typer=entity_type_for_subject,
        **kwargs,
    )


def _entity_type_for_subject_value(conn: Any, value: str) -> str | None:
    row = conn.execute(
        "SELECT e.entity_type FROM entity_identifier i "
        "JOIN entity e ON e.entity_id = i.entity_id "
        "WHERE i.scheme = 'sig.connector.subject' AND i.value = %s",
        (value,),
    ).fetchone()
    return None if row is None else str(row[0])


def _claims_for_subject_value(conn: Any, value: str) -> list[tuple[str, str]]:
    return [
        (str(r[0]), str(r[1] or ""))
        for r in conn.execute(
            "SELECT c.predicate_id, c.value_text FROM claim c "
            "JOIN entity_identifier i ON i.entity_id = c.subject_id "
            "WHERE i.scheme = 'sig.connector.subject' AND i.value = %s "
            "ORDER BY c.predicate_id",
            (value,),
        )
    ]


def _candidate(**kw: Any) -> CandidateForPromotion:
    base = {
        "subject": "candidate:rf:okc-1",
        "detection_method": "rf_oui_match",
        "observation_count": 4,
        "promotion_status": "corroborated",
        "confirmations": (
            Confirmation(
                ConfirmationKind.FIELD,
                "mapper.alice",
                ("018f4e8a-0000-7000-8000-0000000000f1",),
            ),
        ),
        "location_estimate_wkt": "POINT(-97.52 35.46)",
    }
    base.update(kw)
    return CandidateForPromotion(**base)


def test_a_permitted_promotion_mints_a_physical_asset(clean_dsn: str) -> None:
    sink = _real_map_sink(clean_dsn)
    candidate = _candidate()
    write = promotion_claims(candidate, source_id="promotion_test", license="CC0-1.0")
    sink.assert_claims(list(write.claims))
    assert sink.report.quarantined == 0

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # The promoted: subject minted a physical_asset (SIG-PUB-012) …
        assert _entity_type_for_subject_value(conn, write.asset_subject) == "physical_asset"
        # … and the candidate's own subject mints candidate_asset (SIG-ONTO-029).
        assert _entity_type_for_subject_value(conn, candidate.subject) == "candidate_asset"
        asset_claims = dict(_claims_for_subject_value(conn, write.asset_subject))
        assert asset_claims["asset_exists_at_location"] == "true"
        assert "fixed_asset_location" in asset_claims
        # The recorded status flip lands on the candidate, value 'promoted'.
        candidate_claims = dict(_claims_for_subject_value(conn, candidate.subject))
        assert candidate_claims["candidate_promotion_status"] == "promoted"
        # The promoted asset's location lands as the verbatim geometry_wkt
        # value — never a bare claim (raw_value preserved verbatim too).
        assert asset_claims["fixed_asset_location"] == "POINT(-97.52 35.46)"
        row = conn.execute(
            "SELECT c.raw_value FROM claim c "
            "JOIN entity_identifier i ON i.entity_id = c.subject_id "
            "WHERE i.value = %s AND c.predicate_id = 'fixed_asset_location'",
            (write.asset_subject,),
        ).fetchone()
        assert row is not None and row[0] == "POINT(-97.52 35.46)"


def test_the_promotion_write_is_append_only(clean_dsn: str) -> None:
    sink = _real_map_sink(clean_dsn)
    write = promotion_claims(_candidate(), source_id="promotion_test", license="CC0-1.0")
    sink.assert_claims(list(write.claims))
    first = sink.report.inserted
    assert first == len(write.claims) == 3
    # A replay of the identical write inserts +0 (content-digest identity).
    sink.assert_claims(list(write.claims))
    assert sink.report.inserted == first


def test_a_corroboration_only_candidate_writes_nothing(clean_dsn: str) -> None:
    sink = _real_map_sink(clean_dsn)
    candidate = _candidate(confirmations=(), observation_count=10_000)
    with pytest.raises(PromotionRefused):
        promotion_claims(candidate, source_id="promotion_test", license="CC0-1.0")
    # Only the candidate's own record lands — no physical_asset is ever minted.
    sink.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": candidate.subject,
                "predicate_id": "candidate_promotion_status",
                "value": "corroborated",
                "raw_value": "corroborated",
                "source_id": "promotion_test",
                "license": "CC0-1.0",
            }
        ]
    )
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _entity_type_for_subject_value(conn, candidate.subject) == "candidate_asset"
        count = conn.execute(
            "SELECT count(*) FROM entity WHERE entity_type = 'physical_asset'"
        ).fetchone()
        assert count is not None and count[0] == 0


def test_the_promoted_prefix_mints_only_physical_assets(clean_dsn: str) -> None:
    # The map row the writer relies on: a promoted: subject is a
    # physical_asset by construction — asserted through the real sink so a
    # map drift fails loud here.
    from db.subject_types import entity_type_for_subject

    assert entity_type_for_subject("promoted:candidate:rf:x") == "physical_asset"
    assert entity_type_for_subject("candidate:rf:x") == "candidate_asset"
