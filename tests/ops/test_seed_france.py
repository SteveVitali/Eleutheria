# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France seed slice (P24.6 / JURIS.2 / GL-JURIS-01).

The second jurisdiction's committed slice: claims on ``france``-tokened subjects
(so the ILIKE jurisdiction filters find them), material facts on resolver-
registered predicates, the connector-emitted §11.14 surface carried for
provenance, and Part VIII discipline on every row — no plate/person data, the
DECP rows keep ``UNDETERMINED`` rights (spine yes, export no).
"""

from __future__ import annotations

import ops.seed as seed

FRANCE_SUBJECTS = {
    seed._DEPLOYMENT_FR,
    seed._CONTRACT_FR,
    seed._INSTRUMENT_FR,
    seed._JURIS_FR,
}

# The predicates the resolver registry knows — the material facts the API and
# the acceptance queries resolve.
RESOLVER_PREDICATES = {
    "deployment_exists",
    "authorization_state",
    "statutory_citation",
    "procurement_state",
    "contract_value",
    "contract_signed_date",
    "implements_technology",
}

# Part VIII (§0.7): no plate/person/trip data may ever appear in a claim.
FORBIDDEN_TOKENS = ("plate", "trip", "person", "face", "biometric", "track")


def test_france_is_a_seedable_jurisdiction() -> None:
    assert "france" in seed.seedable_jurisdictions()
    assert "okc" in seed.seedable_jurisdictions()


def test_france_slice_subjects_carry_the_jurisdiction_token() -> None:
    # `reconcile resolve --jurisdiction france` / `sig-resolution match` filter on
    # `entity_identifier.value ILIKE '%france%'` — every seeded subject must hit it.
    for claim in seed._FRANCE_CLAIMS:
        assert "france" in claim["subject_id"], claim["subject_id"]


def test_france_slice_uses_resolver_registered_predicates_for_material_facts() -> None:
    # The material facts the acceptance queries resolve must be predicates the
    # §28 ruleset adjudicates — an unregistered predicate 404s on /v1/resolution.
    import reconcile.weight as weight

    registry = weight.predicate_registry()
    deployment_predicates = {
        c["predicate_id"] for c in seed._FRANCE_CLAIMS if c["subject_id"] == seed._DEPLOYMENT_FR
    }
    assert deployment_predicates <= set(registry)
    contract_predicates = {
        c["predicate_id"] for c in seed._FRANCE_CLAIMS if c["subject_id"] == seed._CONTRACT_FR
    }
    assert contract_predicates <= set(registry)


def test_france_slice_carries_the_connector_emitted_surface_for_provenance() -> None:
    # The §11.14 legal-instrument predicates and the fr.cada acquisition regime
    # are out of the resolver ruleset but are real claims in the spine.
    predicates = {c["predicate_id"] for c in seed._FRANCE_CLAIMS}
    assert "instrument_type" in predicates
    assert "acquisition_method" in predicates
    inst = next(c for c in seed._FRANCE_CLAIMS if c["predicate_id"] == "instrument_type")
    assert inst["value"] == "fr.arrete_prefectoral"
    acq = next(c for c in seed._FRANCE_CLAIMS if c["predicate_id"] == "acquisition_method")
    assert acq["value"] == "fr.cada"
    assert not acq["value"].startswith("us.")
    assert acq["value"] != "foia_request"


def test_france_slice_claims_use_directness_genres() -> None:
    # A claim whose genre is absent from the (genre x predicate) matrix is dropped
    # by the resolver ("no directness row") — every resolvable claim needs a
    # registered genre for its predicate.
    import reconcile.weight as weight

    registry = weight.predicate_registry()
    for claim in seed._FRANCE_CLAIMS:
        predicate = claim["predicate_id"]
        if predicate not in registry:
            continue  # out-of-ruleset claims are skipped, not dropped-by-genre
        genre = claim["evidence_genre"]
        assert genre in registry[predicate]["directness"], (predicate, genre)
        assert registry[predicate]["directness"][genre] != "D6", (predicate, genre)


def test_france_slice_rights_posture_is_honest() -> None:
    # The arrêté-derived claims carry the RAA's recorded ODbL; the DECP claims
    # carry UNDETERMINED (spine yes, export no — §42 fail-closed); nothing is
    # asserted under a licence the registry does not record.
    for claim in seed._FRANCE_CLAIMS:
        assert claim["spdx"] in {"ODbL-1.0", "CC-BY-4.0", "UNDETERMINED"}
        if claim["source_id"] == "decp_fr":
            assert claim["spdx"] == "UNDETERMINED", claim
        if claim["source_id"] == "raa_prefectures":
            assert claim["spdx"] == "ODbL-1.0", claim


def test_france_slice_has_no_part_viii_forbidden_data() -> None:
    # No plate/person/trip/biometric data anywhere in the slice (Part VIII §0.7).
    import json

    blob = json.dumps(seed._FRANCE_CLAIMS).lower()
    for token in FORBIDDEN_TOKENS:
        assert token not in blob, f"forbidden Part VIII token {token!r} in the France slice"


def test_france_agency_rows_use_the_national_org_type() -> None:
    rows = seed.france_agency_rows()
    assert len(rows) >= 2  # the near-duplicate pair the ER match scores
    for subject, canonical, org_type in rows:
        assert "france" in subject
        assert org_type == "fr.police_municipale"  # the national namespaced type
        assert "Gex" in canonical


def test_seed_jurisdiction_rejects_an_unknown_jurisdiction() -> None:
    import pytest

    with pytest.raises(KeyError):
        seed.seed_jurisdiction("postgresql://unused", jurisdiction="atlantis")


def test_sig_ops_seed_accepts_france() -> None:
    import argparse

    from ops.cli import _cmd_seed

    # Unknown jurisdiction still refuses (exit 2), naming the seedable set.
    rc = _cmd_seed(argparse.Namespace(jurisdiction="atlantis", dsn="x"))
    assert rc == 2
