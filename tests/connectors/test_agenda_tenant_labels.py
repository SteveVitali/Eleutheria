# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.7 — registry and tenant label corrections M1–M7 (I7-X4 B-40 `approve`).

Pins the six ``jurisdiction`` label corrections in
``data/agenda_tenants.toml`` verbatim per I8 §4.1, the key-stability check
(the TOML row key *does* enter the claim identity
``agenda_item:<src>:<tenant_id>:<id>``, so keys are never renamed), the M6
declared-lineage marking on ``ncdot_runneals_mirror`` (SIG-CONF-014 shape:
mirror-of + derived-from + documentary evidence, never a delete), and the
M7 ``faa_drone_waivers.homepage_url`` fix pointing at the FAA waiver
tables.
"""

from __future__ import annotations

from connectors.dot_511 import enumerated_outcomes
from connectors.procurement import agenda_tenants, tenant_targets
from connectors.registry import get

# M1–M5 (I8 §4.1 verbatim): registry row key -> corrected jurisdiction.
CORRECTED_JURISDICTIONS = {
    "charlotte_ia": "Charlotte, NC",
    "concord_ca": "Concord, NH",
    "san_bernardino_ca": "San Bernardino County, CA",
    "newark": "Newark, NJ",
    "clark": "Clark County, NV",
    "carrollton_ga": "Carrollton, TX",
}

PART_91_113_TABLE = "https://www.faa.gov/uas/advanced_operations/part_91_waivers/waivers_issued"
PART_107_TABLE = "https://www.faa.gov/uas/commercial_operators/part_107_waivers/waivers_issued"


def test_six_tenant_rows_resolve_to_the_corrected_jurisdictions() -> None:
    # M1–M5: the registry rows carry the corrected jurisdiction strings.
    tenants = agenda_tenants()
    for key, expected in CORRECTED_JURISDICTIONS.items():
        assert key in tenants, f"tenant row missing: {key}"
        assert tenants[key]["jurisdiction"] == expected, (
            f"{key}: {tenants[key]['jurisdiction']!r} != {expected!r}"
        )


def test_corrected_labels_reach_the_connector_target_resolution() -> None:
    # The label the connector emits rides through tenant_targets()
    # (SIG-INGEST-034 candidate identifier) — resolve it the same way.
    # P35.8: a tenant emits more than one index target (recency + keyword
    # slices); the recency row is the one whose id IS the tenant key.
    targets = {t["tenant_id"]: t for t in tenant_targets("legistar") if t["id"] == t["tenant_id"]}
    for key, expected in CORRECTED_JURISDICTIONS.items():
        assert targets[key]["jurisdiction"] == expected


def test_corrected_rows_keep_none_of_their_stale_labels() -> None:
    # Scoped to the six corrected keys: the same strings are legitimate
    # labels on OTHER tenants (e.g. the real San Bernardino city tenant).
    stale_by_key = {
        "charlotte_ia": "City of Charlotte, IA",
        "concord_ca": "City of Concord, CA",
        "san_bernardino_ca": "City of San Bernardino, CA",
        "newark": "newark (legistar tenant — unresolved)",
        "clark": "clark (legistar tenant — unresolved)",
        "carrollton_ga": "City of Carrollton, GA",
    }
    tenants = agenda_tenants()
    for key, stale in stale_by_key.items():
        assert tenants[key]["jurisdiction"] != stale


def test_tenant_key_is_the_claim_identity_component() -> None:
    # Key-stability check (P35.7 deliverable 2): agenda subjects are minted
    # `agenda_item:<src>:<tenant_id>:<external_id>` and `tenant_id` is the
    # TOML row key — NOT the platform `tenant` slug. The key therefore
    # enters the claim identity, so keys stay unchanged across the M1–M5
    # label corrections (a rename would mint new subjects for the same
    # upstream matters).
    # P35.8: select the recency slice — the keyword slices carry :kwN ids.
    targets = {t["tenant_id"]: t for t in tenant_targets("legistar") if t["id"] == t["tenant_id"]}
    for key in CORRECTED_JURISDICTIONS:
        target = targets[key]
        assert target["id"] == key
        assert target["tenant_id"] == key
    # The platform slug differs from the key on the mislabelled rows — the
    # slug (not the key) is what the API host keys on.
    charlotte = targets["charlotte_ia"]
    assert charlotte["tenant"] == "charlottenc"  # API slug, unchanged
    # The subject shape the normalizer mints: the row key, not the slug,
    # fills the <tenant> slot of the claim identity.
    subject = f"agenda_item:legistar:{charlotte['tenant_id']}:12345"
    assert ":charlotte_ia:" in subject
    assert ":charlottenc:" not in subject


def test_ncdot_runneals_mirror_declared_lineage() -> None:
    # M6: the mirror row declares its lineage on the registry (SIG-CONF-014
    # shape — mirror-of/derived-from plus documentary evidence), keyed on
    # the NCDOT (state) origin, and nothing about the row was deleted.
    rows = {r["id"]: r for r in enumerated_outcomes()}
    mirror = rows["ncdot_runneals_mirror"]
    assert mirror["mirror_of"] == "dot_511_nc"
    assert mirror["derived_from"] == "dot_511_nc"
    evidence = str(mirror["lineage_evidence"])
    assert "NuWFvHYDMVmmxMeM" in evidence
    assert "I5 NEW-5" in evidence
    # The declared origin is a registered source row.
    assert "NuWFvHYDMVmmxMeM" in get("dot_511_nc").homepage_url
    # The row still records its enumerated (non-target) outcome.
    assert mirror["status"] == "unresolved_rights"


def test_faa_drone_waivers_homepage_points_at_the_waiver_tables() -> None:
    # M7: the homepage names the Part 91.113 waivers table (DFR
    # authorizations); the notes name the Part 107 table verbatim — never
    # the generic faa.gov UAS landing page.
    src = get("faa_drone_waivers")
    assert src.homepage_url == PART_91_113_TABLE
    assert PART_107_TABLE in src.notes
    assert "part_91_waivers" in src.notes
