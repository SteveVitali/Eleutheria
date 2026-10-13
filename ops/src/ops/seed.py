# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Seed a jurisdiction's slice claims into the PG claim spine (P21.4, ADR-066).

`sig-ops seed --jurisdiction okc` loads the Oklahoma City / OKCPD Flock ALPR slice
into a running spine so the composed stack has real, resolvable data to serve —
the scope-qualified counts (P32.3 / SIG-TRUST-004) the dossier must keep
distinct: DeFlock's **299 metro**, the agency's **90 active city-limits**, and
the OKCPD chief's **~100 privately-owned city-limits** — a scope partition, NOT a
contradiction; the "~190" city figure is an explicitly derived approximate sum,
never a claim.

There are **no green sources** on this build (HG-03 was skipped in P21.3), so this
is *not* a live fetch: the values below are the committed P06.1 slice
(`tests/acceptance/fixtures/okc_sources.json` / `okc_slice.py`), loaded through the
same append-only write path a connector uses (`db.claim_sink.PgClaimSink`). Every
row is an INSERT; nothing overwrites an existing claim (P1–P3). Re-running is
idempotent (content-digest ON CONFLICT DO NOTHING). Every seeded claim carries the
``evidence_origin``=``seed_fixture`` qualifier (P32.3 / SIG-TRUST-004) so no read
surface presents fixture material as primary live evidence.

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

#: The committed OKC slice claims (P06.1, scope-repaired P32.3 /
#: SIG-TRUST-004). Each is a connector-shaped dict for PgClaimSink: the resolver
#: derives count_basis from the `_device_count` suffix. Every row carries the
#: ``evidence_origin``=``seed_fixture`` qualifier — seeded material is labelled
#: so no read surface presents it as primary live evidence — and every count
#: carries ``count_scope`` (+``count_scope_detail`` where it refines the scope):
#: DeFlock's 299 is a METRO count, the OKCPD chief's ~100 is PRIVATELY-OWNED cameras inside
#: CITY LIMITS, and the agency's 90 is CITY-LIMITS agency-operated — different
#: scopes, so they are NOT a contradiction. The "~190" city figure a reader
#: derives from 90 + ~100 is an explicitly derived approximate sum
#: (``reconcile.count_scope.derive_approximate_sum``, L4-labelled, never a
#: claim) — the seed asserts only the two sourced inputs, honestly.
_OKC_JURISDICTION = "us.state_abbr:OK"


def _okc_qualifiers(scope: str, detail: str | None = None) -> list[dict[str, Any]]:
    qualifiers: list[dict[str, Any]] = [
        {
            "qualifier_id": "count_scope",
            "value": scope,
            "jurisdiction": _OKC_JURISDICTION,
        },
    ]
    if detail:
        qualifiers.append({"qualifier_id": "count_scope_detail", "value": detail})
    return qualifiers


_OKC_CLAIMS: list[dict[str, Any]] = [
    # DeFlock's community map — ~299 devices across the METRO (not the city).
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 299,
        "raw_value": "299",
        "observed_at": "2026-08-20",
        "source_id": "deflock",
        "spdx": "CC-BY-4.0",
        "attribution": "DeFlock community map",
        "evidence_genre": "community_map",
        "qualifiers": _okc_qualifiers("metro"),
    },
    # the OKCPD chief's statement — ~100 PRIVATELY-OWNED cameras inside CITY LIMITS
    # (the sourced input the "~190" derived city sum adds to the agency's 90 —
    # the sum itself is derived, not claimed).
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 100,
        "raw_value": "businesses own around 100 within city limits",
        "observed_at": "2026-08-18",
        "source_id": "okc_council_statement",
        "spdx": "CC-BY-4.0",
        "attribution": "the OKCPD chief, city council 2026-08-18",
        "evidence_genre": "news_article",
        "qualifiers": _okc_qualifiers("city_limits", "privately_owned"),
    },
    # The agency's own fleet — 90 active, city limits, agency-operated.
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "active_device_count",
        "value": 90,
        "raw_value": "OKCPD has 90 cameras",
        "observed_at": "2026-08-18",
        "source_id": "okc_council_statement",
        "spdx": "CC-BY-4.0",
        "attribution": "the OKCPD chief, city council 2026-08-18",
        "evidence_genre": "official_statement",
        "qualifiers": _okc_qualifiers("city_limits", "agency_operated"),
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
        "qualifiers": _okc_qualifiers("city_limits", "agency_operated"),
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
        "qualifiers": _okc_qualifiers("metro"),
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
        "value": "2031-02-01",  # future-ok: real-world: recorded arrêté sunset
        "raw_value": (
            "2031-02-01 (cinq ans, "  # future-ok: real-world: recorded sunset
            "renouvelable — dérivé)"
        ),
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


#: The qualifier-only predicate ids the seed claims name (P32.3 / ADR-122) —
#: pre-registered through the sink's connector-declared vocabulary path so the
#: ``claim_qualifier`` FK never quarantines them.
_SEED_QUALIFIER_VOCAB: tuple[tuple[str, str], ...] = (
    ("count_scope", "string"),
    ("count_scope_detail", "string"),
    ("evidence_origin", "string"),
)


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
    from db.identity_guard import resolve_identities

    slice_def = _SEED_SLICES[jurisdiction]  # KeyError on an unknown jurisdiction
    sink = PgClaimSink.from_dsn(
        dsn,
        connector_name=str(slice_def["connector_name"]),
        connector_version="1.0.0",
        code_commit=str(slice_def["code_commit"]),
    )
    sink.register_vocabulary(_SEED_QUALIFIER_VOCAB)

    # P32.3 / SIG-TRUST-004: stamp ``evidence_origin=seed_fixture`` on EVERY
    # seeded claim — fixture material is labelled, never presented as primary
    # live evidence.
    claims: list[dict[str, Any]] = []
    for raw in slice_def["claims"]:
        claim = dict(raw)
        qualifiers = [dict(q) for q in claim.get("qualifiers") or ()]
        if not any(q.get("qualifier_id") == "evidence_origin" for q in qualifiers):
            qualifiers.append({"qualifier_id": "evidence_origin", "value": "seed_fixture"})
        claim["qualifiers"] = qualifiers
        claims.append(claim)
    sink.assert_claims(claims)

    # Organisation projections for the ER candidate read (idempotent). The subject
    # identifiers go through the identity guard (P31.3 / ADR-110), so a concurrent
    # seed or sink never mints a second entity for one subject. The jurisdiction
    # identifier (`us.state` / `fr.insee`) is an attribute many organisations share
    # on purpose, so it is NOT keyed. It is attached only to an entity this call minted.
    extra_scheme, extra_value = slice_def["extra_identifier"]
    rows = slice_def["agency_rows"]()
    with psycopg.connect(dsn, autocommit=True) as conn, conn.transaction():
        resolved = resolve_identities(
            conn, SUBJECT_SCHEME, [subject for subject, _, _ in rows], entity_type="organization"
        )
        for subject, canonical, org_type in rows:
            entity_id = resolved.entity_by_value[subject]
            if subject in resolved.minted:
                conn.execute(
                    "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (entity_id, extra_scheme, extra_value),
                )
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
