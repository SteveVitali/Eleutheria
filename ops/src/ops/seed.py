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

P24.6 (JURIS.2 / GL-JURIS-01) adds the **second jurisdiction** — France, commune
de Gex (département de l'Ain), vidéoprotection — seeded through the same
append-only path. Its claims are the committed P18.2 fixture values
(`tests/connectors/fixtures/france/`): authorization by **arrêté préfectoral**
(not a contract), procurement by **DECP national open data** (not municipal
portals), records regime **fr.cada** (never ``us.foia`` — SIG-ONTO-068). The
DECP-derived claims carry ``UNDETERMINED`` rights on purpose: they land in the
spine but the export gate keeps them out of a published bundle until the HG-03
review resolves the licence (§42 fail-closed — the licence gate exercised in the
second jurisdiction, not bypassed).
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


# --- France — the second jurisdiction (P24.6 / JURIS.2 / GL-JURIS-01) ----------

#: The France slice subjects carry the ``france`` token so the jurisdiction
#: filters (`entity_identifier.value ILIKE '%france%'`) find them — the same
#: convention the OKC slice follows (SIG-IDENT filters).
_DEPLOYMENT_FR = "sig:deployment:france-gex-videoprotection"
_CONTRACT_FR = "contract:france:decp-2025kazvs0000000"
_INSTRUMENT_FR = "legal_instrument:france:raa:arrete-01-2026-0451"
_JURIS_FR = "jurisdiction:france"
_AGENCY_FR = "agency:france:gex-police-municipale"

#: The committed France slice claims (P24.6). The material facts the dossier and
#: the acceptance queries resolve use predicates the resolver registry knows
#: (``deployment_exists``/``authorization_state``/``statutory_citation``/
#: ``procurement_state``/``contract_value``/``contract_signed_date``/
#: ``implements_technology``); the connector-emitted §11.14 surface
#: (``instrument_type``/``enacting_body``/``acquisition_method``/…) is carried in
#: the spine for provenance even though the ruleset does not adjudicate it —
#: `reconcile resolve` skips out-of-ruleset predicates rather than failing.
_FRANCE_CLAIMS: list[dict[str, Any]] = [
    # Authorization by arrêté préfectoral — the shape the US slice does not have:
    # a dated, five-year-renewable prefectural order, not a signed contract.
    # observed_at = the RAA index's recorded verification date (the source's
    # `last_verified` in the registry): the index attests the arrêté in force
    # *as of that date* — the honest observation time for a current-state claim
    # (a 12-month-half-life predicate asserting a 7-month-old observation is
    # correctly too stale to resolve; the index date is the evidence's date,
    # not the instrument's own effective_from, which stays in raw_value).
    {
        "subject_id": _DEPLOYMENT_FR,
        "predicate_id": "deployment_exists",
        "value": True,
        "raw_value": "vidéoprotection autorisée — arrêté préfectoral 01-2026-0451",
        "observed_at": "2026-08-20",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _DEPLOYMENT_FR,
        "predicate_id": "authorization_state",
        "value": "authorized",
        "raw_value": "autorisé — arrêté préfectoral 01-2026-0451, cinq ans renouvelable",
        "observed_at": "2026-08-20",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _DEPLOYMENT_FR,
        "predicate_id": "statutory_citation",
        "value": "Code de la sécurité intérieure, art. L251-1 à L255-1",
        "raw_value": "CSI L251-1 à L255-1",
        "observed_at": "2026-08-20",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _DEPLOYMENT_FR,
        "predicate_id": "implements_technology",
        "value": "camera-fixed-cctv",
        "raw_value": "vidéoprotection",
        "observed_at": "2026-08-20",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _DEPLOYMENT_FR,
        "predicate_id": "procurement_state",
        "value": "contracted",
        "raw_value": "marché notifié le 2025-04-01 (DECP 2025kazvs0000000)",
        "observed_at": "2026-09-13",
        "source_id": "decp_fr",
        "spdx": "UNDETERMINED",
        "attribution": "Données essentielles de la commande publique (DECP)",
        "evidence_genre": "executed_contract",
    },
    # The DECP marché — spine yes, export no (rights UNDETERMINED until HG-03).
    # observed_at = the fixture's record-observation date: the DECP national
    # dataset as of 2026-09-13 carries this marché (the notification date stays
    # in the value/raw).
    {
        "subject_id": _CONTRACT_FR,
        "predicate_id": "contract_value",
        "value": 50754,
        "raw_value": "50754 EUR",
        "observed_at": "2026-09-13",
        "source_id": "decp_fr",
        "spdx": "UNDETERMINED",
        "attribution": "Données essentielles de la commande publique (DECP)",
        "evidence_genre": "executed_contract",
    },
    {
        "subject_id": _CONTRACT_FR,
        "predicate_id": "contract_signed_date",
        "value": "2025-04-01",
        "raw_value": "2025-04-01",
        "observed_at": "2026-09-13",
        "source_id": "decp_fr",
        "spdx": "UNDETERMINED",
        "attribution": "Données essentielles de la commande publique (DECP)",
        "evidence_genre": "executed_contract",
    },
    # The §11.14 legal-instrument surface the records connector emits over the
    # RAA fixture — carried in the spine for provenance (out of the resolver
    # ruleset: `reconcile resolve` skips, /v1/resolution 404s — recorded, P24.6).
    {
        "subject_id": _INSTRUMENT_FR,
        "predicate_id": "instrument_type",
        "value": "fr.arrete_prefectoral",
        "raw_value": "fr.arrete_prefectoral",
        "observed_at": "2026-02-01",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _INSTRUMENT_FR,
        "predicate_id": "enacting_body",
        "value": "Préfecture de l'Ain",
        "raw_value": "Préfecture de l'Ain",
        "observed_at": "2026-02-01",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    {
        "subject_id": _INSTRUMENT_FR,
        "predicate_id": "sunset_date",
        "value": "2031-02-01",
        "raw_value": "2031-02-01 (cinq ans, renouvelable — dérivé)",
        "observed_at": "2026-02-01",
        "source_id": "raa_prefectures",
        "spdx": "ODbL-1.0",
        "attribution": "Recueil des actes administratifs de la préfecture de l'Ain",
        "evidence_genre": "agency_policy",
    },
    # The internationalized records regime — fr.cada, never us.foia (SIG-ONTO-068).
    {
        "subject_id": _JURIS_FR,
        "predicate_id": "acquisition_method",
        "value": "fr.cada",
        "raw_value": "fr.cada",
        "observed_at": "2026-09-13",
        "source_id": "madada",
        "spdx": "UNDETERMINED",
        "attribution": "Ma Dada — registre des demandes CADA",
        "evidence_genre": "portal_snapshot",
    },
]


def france_agency_rows() -> list[tuple[str, str, str]]:
    """The near-duplicate French organisations the ER match step scores (P24.6).

    ``fr.police_municipale`` is the national-namespaced organisation type the
    P18.1 adapter seeded — the same "no widened US enum" rule the claims follow.
    """
    return [
        (f"{_AGENCY_FR}-1", "Police municipale de Gex", "fr.police_municipale"),
        (f"{_AGENCY_FR}-2", "Police Municipale de la Ville de Gex", "fr.police_municipale"),
    ]


#: The jurisdiction → (claims, agency rows, extra identifier) seed table. The
#: dispatch is data so a third jurisdiction is a new row, not a new code path.
_SEED_SLICES: dict[str, dict[str, Any]] = {
    "okc": {
        "claims": _OKC_CLAIMS,
        "agency_rows": okc_agency_rows,
        "extra_identifier": ("us.state", "OK"),
        "connector_name": "okc-seed",
        "code_commit": "p21.4-seed",
    },
    "france": {
        "claims": _FRANCE_CLAIMS,
        "agency_rows": france_agency_rows,
        "extra_identifier": ("fr.insee", "01"),
        "connector_name": "france-seed",
        "code_commit": "p24.6-seed",
    },
}


def seedable_jurisdictions() -> tuple[str, ...]:
    """The jurisdictions a slice exists for (the `sig-ops seed` allowlist)."""
    return tuple(sorted(_SEED_SLICES))


def seed_jurisdiction(dsn: str, jurisdiction: str = "okc") -> dict[str, int]:
    """Load a jurisdiction's slice claims into the spine at ``dsn``; small report.

    Append-only + idempotent (PgClaimSink content-digest ON CONFLICT). Also seeds
    the near-duplicate ``organization`` projections so ``sig-resolution match
    --jurisdiction <j>`` has candidates to score. ``jurisdiction`` defaults to
    ``okc`` so the P21.4 callers are unchanged; ``france`` is the P24.6 second
    jurisdiction.
    """
    import psycopg
    from db.claim_sink import SUBJECT_SCHEME, PgClaimSink

    slice_def = _SEED_SLICES[jurisdiction]  # KeyError on an unknown jurisdiction
    sink = PgClaimSink.from_dsn(
        dsn,
        connector_name=str(slice_def["connector_name"]),
        connector_version="1.0.0",
        code_commit=str(slice_def["code_commit"]),
    )
    sink.assert_claims(slice_def["claims"])

    # Organisation projections for the ER candidate read (idempotent).
    extra_scheme, extra_value = slice_def["extra_identifier"]
    with psycopg.connect(dsn, autocommit=True) as conn:
        for subject, canonical, org_type in slice_def["agency_rows"]():
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
                    (entity_id, extra_scheme, extra_value),
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
