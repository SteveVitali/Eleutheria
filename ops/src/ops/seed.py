# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Seed a jurisdiction's slice claims into the PG claim spine (P21.4, ADR-066).

`sig-ops seed --jurisdiction okc` loads the Oklahoma City / OKCPD Flock ALPR slice
into a running spine so the composed stack has real, resolvable data to serve —
above all the **299-vs-190 `claimed_device_count` contradiction** (§3.1) the
dossier must surface with both sources and dates.

There are **no green sources** on this build (HG-03 was skipped in P21.3), so this
is *not* a live fetch: the values below are the committed P06.1 slice
(`tests/acceptance/fixtures/okc_sources.json` / `okc_slice.py`), loaded through the
same append-only write path a connector uses (`db.claim_sink.PgClaimSink`). Every
row is an INSERT; nothing overwrites an existing claim (P1–P3). Re-running is
idempotent (content-digest ON CONFLICT DO NOTHING).

The OSM-derived physical layer is kept in its **separate ODbL compartment** (§42):
its one seed claim carries ``ODbL-1.0`` with the OSM attribution + share-alike
notice; the graph claims carry ``CC-BY-4.0``.
"""

from __future__ import annotations

from typing import Any

#: The deployment subject the slice hangs off (contains "okc" so the jurisdiction
#: filter `entity_identifier.value ILIKE '%okc%'` finds it — SIG-IDENT filters).
_DEPLOYMENT = "sig:deployment:okc-okcpd-flock"
_AGENCY = "agency:okc:okcpd"

#: The committed OKC slice claims (P06.1). Each is a connector-shaped dict for
#: PgClaimSink: the resolver derives count_basis from the `_device_count` suffix.
_OKC_CLAIMS: list[dict[str, Any]] = [
    # The within-predicate disagreement the dossier must keep visible: DeFlock's
    # community map (~299 metro) vs Chief Bacy's statement (~190 city limits).
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 299,
        "raw_value": "299",
        "observed_at": "2026-08-20",
        "source_id": "deflock",
        "spdx": "CC-BY-4.0",
        "attribution": "DeFlock community map",
        "evidence_genre": "news_article",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 190,
        "raw_value": "businesses own around 100 within city limits",
        "observed_at": "2026-08-18",
        "source_id": "bacy",
        "spdx": "CC-BY-4.0",
        "attribution": "OKCPD Chief Bacy, city council 2026-08-18",
        "evidence_genre": "news_article",
    },
    # A resolved (uncontested) neighbour so the spine is not contradiction-only.
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "active_device_count",
        "value": 90,
        "raw_value": "OKCPD has 90 cameras",
        "observed_at": "2026-08-18",
        "source_id": "bacy",
        "spdx": "CC-BY-4.0",
        "attribution": "OKCPD Chief Bacy, city council 2026-08-18",
        "evidence_genre": "official_statement",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "contracted_device_count",
        "value": 90,
        "raw_value": "90 cameras",
        "observed_at": "2023-01-01",
        "source_id": "okc-contract-c241032",
        "spdx": "CC-BY-4.0",
        "attribution": "OKC Master Agreement C241032",
        "evidence_genre": "contract",
    },
    # The OSM-derived physical layer — SEPARATE ODbL compartment (§42, HG-02):
    # published with ODbL attribution + share-alike, kept apart from the graph.
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "mapped_device_count",
        "value": 31,
        "raw_value": "31",
        "observed_at": "2026-08-20",
        "source_id": "osm",
        "spdx": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 (share-alike)",
        "evidence_genre": "community_map",
    },
]


def okc_agency_rows() -> list[tuple[str, str, str]]:
    """The near-duplicate OKCPD organisations the ER match step scores (P19.5)."""
    return [
        (f"{_AGENCY}-1", "Oklahoma City Police Department", "us.le.municipal_police"),
        (f"{_AGENCY}-2", "Oklahoma City Police Dept", "us.le.municipal_police"),
    ]


def seed_jurisdiction(dsn: str) -> dict[str, int]:
    """Load the OKC slice claims into the spine at ``dsn``; return a small report.

    Append-only + idempotent (PgClaimSink content-digest ON CONFLICT). Also seeds
    the near-duplicate OKCPD ``organization`` projections so ``sig-resolution match
    --jurisdiction okc`` has candidates to score.
    """
    import psycopg
    from db.claim_sink import SUBJECT_SCHEME, PgClaimSink

    sink = PgClaimSink.from_dsn(
        dsn,
        connector_name="okc-seed",
        connector_version="1.0.0",
        code_commit="p21.4-seed",
    )
    sink.assert_claims(_OKC_CLAIMS)

    # Organisation projections for the ER candidate read (idempotent).
    with psycopg.connect(dsn, autocommit=True) as conn:
        for subject, canonical, org_type in okc_agency_rows():
            row = conn.execute(
                "SELECT entity_id FROM entity_identifier WHERE scheme = %s AND value = %s",
                (SUBJECT_SCHEME, subject),
            ).fetchone()
            if row is None:
                created = conn.execute(
                    "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
                ).fetchone()
                assert created is not None
                entity_id = created[0]
                conn.execute(
                    "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s)",
                    (entity_id, SUBJECT_SCHEME, subject),
                )
                conn.execute(
                    "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (entity_id, "us.state", "OK"),
                )
            else:
                entity_id = row[0]
            conn.execute(
                "INSERT INTO organization(entity_id, organization_type, cached_canonical_name) "
                "VALUES (%s, %s, %s) ON CONFLICT (entity_id) "
                "DO UPDATE SET cached_canonical_name = EXCLUDED.cached_canonical_name",
                (entity_id, org_type, canonical),
            )

    return {
        "inserted": sink.report.inserted,
        "duplicates": sink.report.duplicates,
        "entities": sink.report.entities,
    }
