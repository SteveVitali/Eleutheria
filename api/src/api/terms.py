# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Acceptable-use terms with a stated remedy (§37.4, SIG-API-013).

Terms that prohibit re-identification but state no remedy are decorative
(SIG-API-013). These terms therefore pair each prohibition with an explicit
consequence: access revocation and referral, consistent with the Part VIII
categorical exclusions (§43.2) and the no-per-person-query posture (SIG-API-012).
"""

from __future__ import annotations

from .models import TermsResponse

TERMS_VERSION = "2026-01-v1"

_PROHIBITIONS: tuple[str, ...] = (
    "Attempting to re-identify any individual from published data, including "
    "correlating device or location records to a person (SIG-API-012, §43.2).",
    "Joining SIG data against any external dataset for the purpose of "
    "de-pseudonymisation or per-person tracking (SIG-PUB-003a).",
    "Using the API to derive a real-time device-liveness or presence signal.",
    "Requesting coordinates at finer precision than an asset's sensitivity tier publishes (§19.4).",
    "Automated access exceeding the tier's published rate limit.",
)

_REMEDY = (
    "Violation is a material breach of these terms. The remedy is immediate "
    "revocation of API access (all tiers and issued keys), invalidation of "
    "affected credentials, and — where the violation is an attempted "
    "re-identification of an individual — referral to the SIG editorial board "
    "and, where applicable, to counsel. Continued or automated abuse may be "
    "blocked at the network layer without notice."
)

_TIER_DESCRIPTIONS: dict[str, str] = {
    "anonymous": "Rate-limited access to public data; no credential required.",
    "registered": "Higher rate limits for a registered account.",
    "partner": "Bulk access under an agreed partner data-use agreement.",
}

#: Per-compartment licence statement (SIG-LIC-004/010, §42). Each export
#: compartment is offered under its own licence and kept in a separate file; the
#: OSM-derived physical layer is a Produced Work under ODbL with attribution +
#: share-alike (HG-02 disposition), never mixed into the CC-BY graph compartment.
_LICENSES: dict[str, str] = {
    "sig_graph": "CC-BY-4.0 — the SIG-produced reconciliation graph (attribution).",
    "osm_physical": (
        "ODbL-1.0 — the OpenStreetMap-derived physical device layer, a Produced Work "
        "offered under ODbL with attribution to © OpenStreetMap contributors and the "
        "share-alike notice; kept in its own separate compartment (§42, SIG-LIC-004a)."
    ),
    "crosswalk": "The most permissive licence its constituents allow (SIG-EXPORT-007).",
}


def acceptable_use_terms() -> TermsResponse:
    """The acceptable-use terms served at ``/terms`` (SIG-API-013)."""
    return TermsResponse(
        version=TERMS_VERSION,
        tiers=dict(_TIER_DESCRIPTIONS),
        prohibitions=list(_PROHIBITIONS),
        remedy=_REMEDY,
        reidentification_prohibited=True,
        licenses=dict(_LICENSES),
    )
