# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The web-shaped dossier bundle a jurisdiction export emits (P21.4, ADR-066).

`sig-exports build --jurisdiction <j>` writes ``web/dossiers.json`` into the export
directory: a JSON array of dossiers in the exact ``web/src/lib/dossier.ts``
``Dossier`` contract, so the static site can be built **from the export** rather
than from the committed TS fixtures (LD-V08, §38.1). Building the site from these
bytes is the whole point: an export and the site agree by construction.

The Oklahoma City dossier is the worked-case dossier the shell already renders
(same at-a-glance / cost / sharing / retention / accountability content, so the site
is byte-comparable in both modes) **plus** the defining-standard contradiction
(§3.1): the 299-vs-190 ``claimed_device_count`` disagreement — DeFlock's community
map (~299 metro) vs Chief Bacy's council statement (~190 city limits) — as a
first-class, contested material figure whose reconciliation lists BOTH claims with
their sources and dates. Nothing collapses it to one number (no synthetic
certainty). Its presence (absent from the committed fixtures) is what proves the
page was rendered from the export bytes rather than the fixtures.

This is fixture-backed, not live: there are no green sources on this build (HG-03
skipped), so the values are the committed P06.1 slice. The builder is a pure
function of that slice — deterministic, byte-reproducible.
"""

from __future__ import annotations

from typing import Any

_AS_OF: dict[str, Any] = {
    "as_of_world": "2026-08-20",
    "as_of_belief": "2026-08-20",
    "world_defaulted": False,
    "belief_defaulted": False,
    "question": "as-of world 2026-08-20, belief 2026-08-20",
    "belief_pinned": True,
}
_RULESET_VERSION = "resolver-ruleset-2026.07"

# --- the defining-standard contradiction: 299 vs ~190 claimed_device_count ----

_CLAIMED_CLAIMS: list[dict[str, Any]] = [
    {
        "claimId": "deflock",
        "value": 299,
        "source": "DeFlock community map",
        "tier": "W2",
        "date": "2026-08-20",
        "documentUrl": "/v1/claim/deflock",
        "differentQuantityNote": (
            "DeFlock maps ~299 devices across the metro; Chief Bacy's ~190 counts devices "
            "within city limits. These may measure different quantities — both are retained."
        ),
    },
    {
        "claimId": "bacy",
        "value": 190,
        "source": "OKCPD Chief Bacy, city council 2026-08-18",
        "tier": "W2",
        "date": "2026-08-18",
        "documentUrl": "/v1/claim/bacy",
    },
]

_CLAIMED_FIGURE: dict[str, Any] = {
    "key": "claimed_device_count",
    "label": "Claimed device count",
    # A range, never a single collapsed number — the contradiction is the fact.
    "value": "190–299",
    "unit": "devices",
    "support": "STRONGLY_SUPPORTED",
    "evidenceCount": 2,
    "contested": True,
    "reconciliation": {
        "rule": "UNRESOLVED_STANDOFF",
        # No winner: the standoff is unresolved (empty id => winning_present false).
        "winningClaimId": "",
        "claims": _CLAIMED_CLAIMS,
        "note": (
            "Unresolved. 299 rests on the DeFlock community map (2026-08-20); ~190 rests on "
            "Chief Bacy's council statement (2026-08-18). No source establishes the claimed "
            "device count directly; both values are shown with their evidence (§3.1)."
        ),
    },
}

# --- the worked-case figures (mirroring web/src/lib/dossier-fixture.ts) --------

_DEVICE_COUNT_CLAIMS: list[dict[str, Any]] = [
    {
        "claimId": "contract",
        "value": 42,
        "source": "Public records request (city procurement)",
        "tier": "W3",
        "date": "2026-07-01",
        "documentUrl": "/v1/claim/contract",
    },
    {
        "claimId": "portal",
        "value": 38,
        "source": "Eyes on Flock portal aggregator",
        "tier": "W2",
        "date": "2026-07-01",
        "documentUrl": "/v1/claim/portal",
        "differentQuantityNote": (
            "The portal counts devices reporting on 2026-07-01; the contract counts devices "
            "procured. These may measure different quantities."
        ),
    },
]

_ACTIVE_FIGURE: dict[str, Any] = {
    "key": "active_device_count",
    "label": "Active device count",
    "value": 42,
    "unit": "devices",
    "support": "STRONGLY_SUPPORTED",
    "evidenceCount": 1,
    "contested": True,
    "reconciliation": {
        "rule": "HIGHEST_TIER_WINS",
        "winningClaimId": "contract",
        "claims": _DEVICE_COUNT_CLAIMS,
        "note": (
            "The W3 records-request contract (42) outranks the W2 portal snapshot (38); the "
            "dissent is preserved and the value is marked contested."
        ),
    },
}

_MAPPED_FIGURE: dict[str, Any] = {
    "key": "mapped_device_count",
    "label": "Independently mapped devices",
    "value": 31,
    "unit": "devices",
    "lowerBound": True,
    "support": "PROBABLE",
    "evidenceCount": 1,
    "contested": False,
    "reconciliation": {
        "rule": "INDEPENDENT_MAP_LOWER_BOUND",
        "winningClaimId": "osm",
        "claims": [
            {
                "claimId": "osm",
                "value": 31,
                # The OSM-derived layer: its OWN separate ODbL compartment (§42, HG-02).
                "source": "OpenStreetMap contributors (ODbL 1.0, share-alike)",
                "tier": "W2",
                "date": "2026-08-20",
                "documentUrl": "/v1/claim/osm",
            }
        ],
        "note": (
            "Independently mapped devices are a lower bound on the physical population, not a "
            "competing count. OSM-derived; published under ODbL 1.0 with attribution + share-alike."
        ),
    },
}


def _okc_dossier() -> dict[str, Any]:
    """The Oklahoma City dossier in the web ``Dossier`` contract.

    Mirrors the worked fixture (``web/src/lib/dossier-fixture.ts``) so the site is
    equivalent in fixtures/export mode, then adds the 299-vs-190 claimed-count
    contradiction as the leading figure of "what is deployed" (§3.1).
    """
    return {
        "slug": "oklahoma-city",
        "subject_label": "Oklahoma City Police Department — ALPR deployment",
        "jurisdiction": "Oklahoma City, Oklahoma",
        "asOf": _AS_OF,
        "rulesetVersion": _RULESET_VERSION,
        "source_families": [
            "Executed procurement contract (public records request)",
            "Eyes on Flock portal aggregator",
            "DeFlock community map",
            "OpenStreetMap community map (ODbL)",
            "Oklahoma City Council minutes",
        ],
        "authorization": {
            "approving_body": "Oklahoma City Council",
            "vote": "Consent agenda (no roll-call vote)",
            "consent_agenda": True,
            "public_comment": False,
            "date": "2025-03-25",
        },
        "termination": {
            "auto_renews": True,
            "notice_window_days": 90,
            "expiry_date": "2027-04-02",
        },
        "legal_regime": {
            "state_statute": "Okla. Stat. tit. 47 — ALPR data retention limits",
            "local_ordinance": "Oklahoma City Municipal Code ch. 30 (surveillance procurement)",
            "disclosure_duties": [
                "Oklahoma Open Records Act — response to public records requests",
                "Council approval required for surveillance-technology procurement",
            ],
        },
        "gaps": [
            {
                "label": "Claimed device count is contested (299 vs ~190)",
                "kind": "UNRESOLVED",
                "subject_id": "sig:deployment:okc-okcpd-flock",
                "predicate_id": "claimed_device_count",
                "note": "DeFlock maps ~299 metro; Chief Bacy states ~190 within city limits. "
                "Different scopes; the disagreement is retained, not adjudicated.",
            },
            {
                "label": "Data-sharing partners",
                "kind": "NOT_RESEARCHED",
                "subject_id": "agency:okcpd",
                "predicate_id": "sharing_partners",
                "note": "SIG has not yet researched which agencies OKCPD shares ALPR data with.",
            },
            {
                "label": "Retention window (days)",
                "kind": "NO_EVIDENCE_FOUND",
                "subject_id": "agency:okcpd",
                "predicate_id": "retention_days",
                "sources_searched": ["portal", "records request", "council minutes 2023–2026"],
            },
            {
                "label": "Unexplained delta: 42 contracted vs 38 active",
                "kind": "UNRESOLVED",
                "subject_id": "agency:okcpd",
                "predicate_id": "contracted_active_delta",
                "note": "Four contracted devices are not reported active. Were they never "
                "installed, or removed?",
            },
        ],
        "sections": [
            {
                "section_id": "at_a_glance",
                "rows": [
                    {"label": "Operator", "value": "Oklahoma City Police Department"},
                    {
                        "label": "Technology",
                        "value": "Automated licence-plate readers (ALPR) + RTCC integration",
                    },
                    {"label": "Lifecycle status", "value": "Operational"},
                ],
            },
            {
                "section_id": "what_is_deployed",
                # The 299-vs-190 contradiction leads (§3.1), then the worked counts.
                "figures": [_CLAIMED_FIGURE, _ACTIVE_FIGURE, _MAPPED_FIGURE],
                "rows": [
                    {
                        "label": "Device type",
                        "value": "Fixed ALPR cameras; one RTCC integration hub",
                    },
                ],
            },
            {
                "section_id": "cost_and_expiry",
                "rows": [
                    {
                        "label": "Contract value (annual)",
                        "value": None,
                        "note": "Not disclosed in the released contract.",
                    },
                    {
                        "label": "Contract expiry",
                        "value": "2027-04-02",
                        "documentUrl": "/v1/claim/contract",
                    },
                ],
            },
            {
                "section_id": "who_else_can_see",
                "rows": [
                    {
                        "label": "Data-sharing partners",
                        "value": None,
                        "absence": "NOT_RESEARCHED",
                        "subject_id": "agency:okcpd",
                        "predicate_id": "sharing_partners",
                    },
                    {
                        "label": "Configured-access edges (observed 2026-07-14)",
                        "value": 147,
                        "note": "Configured access — not 'currently shares with 147' "
                        "(§12.2, SIG-TIME-005).",
                    },
                ],
            },
            {
                "section_id": "configuration_and_retention",
                "rows": [
                    {
                        "label": "Policy written retention (days)",
                        "value": None,
                        "note": "Policy document not located.",
                    },
                    {
                        "label": "Configured retention (days)",
                        "value": None,
                        "absence": "NO_EVIDENCE_FOUND",
                        "subject_id": "agency:okcpd",
                        "predicate_id": "retention_days",
                    },
                    {
                        "label": "Vendor default retention (days)",
                        "value": 30,
                        "documentUrl": "/v1/claim/vendor-default",
                    },
                ],
            },
            {
                "section_id": "usage",
                "rows": [
                    {
                        "label": "Searches (30-day window ending 2026-07-15)",
                        "value": 412,
                        "note": "A windowed count with explicit bounds — never rendered as a "
                        "current rate (SIG-RECON-011).",
                    },
                ],
            },
            {
                "section_id": "where_the_hardware_is",
                "rows": [
                    {
                        "label": "Independently mapped devices",
                        "value": 31,
                        "note": "A lower bound (OSM/ODbL). See the reference map for locations "
                        "at published precision.",
                    },
                    {
                        "label": "Reference map",
                        "value": "/reference-map/",
                        "documentUrl": "/reference-map/",
                    },
                ],
            },
            {
                "section_id": "policy",
                "rows": [
                    {
                        "label": "Immigration-enforcement configuration evidence",
                        "value": None,
                        "absence": "NOT_RESEARCHED",
                        "subject_id": "agency:okcpd",
                        "predicate_id": "immigration_enforcement_config",
                        "note": "Rendered as unknown, not omitted (SIG-UI-015).",
                    },
                ],
            },
            {
                "section_id": "accountability_events",
                "rows": [
                    {
                        "label": "Procurement approval",
                        "value": "Approved 2025-03-25 (see authorization block)",
                    },
                    # A public-employee name, publishable under US-DEFAULT (SIG-PUB-017);
                    # applyPublicationPolicy leaves it shown (contrast: FR/BE withhold).
                    {
                        "label": "Approving official",
                        "value": "Chief Wade Gourley",
                        "isPublicEmployeeName": True,
                        "originJurisdiction": "US",
                    },
                ],
            },
            {
                "section_id": "timeline",
                "rows": [
                    {
                        "label": "2025-04-03",
                        "value": "Executed contract signed",
                        "documentUrl": "/v1/claim/contract",
                    },
                    {
                        "label": "2026-07-15",
                        "value": "Transparency-portal snapshot captured",
                        "documentUrl": "/v1/claim/portal",
                    },
                    {"label": "2026-08-20", "value": "OpenStreetMap community map reconciled"},
                ],
            },
            {"section_id": "what_we_dont_know"},
            {
                "section_id": "how_we_know_this",
                "rows": [
                    {
                        "label": "Sources",
                        "value": "Contract, transparency portal, DeFlock, OSM, council minutes",
                    },
                    {
                        "label": "Methodology",
                        "value": "/methodology/",
                        "documentUrl": "/methodology/",
                        "note": "See the methodology page for tiers, currency, and recon rules.",
                    },
                ],
            },
        ],
    }


def _france_dossier() -> dict[str, Any]:
    """The France dossier — Commune de Gex (Ain) vidéoprotection (P24.6, JURIS.2).

    The second-jurisdiction dossier in the same web ``Dossier`` contract, in its
    own BCP-47 language (``fr``), and carrying the Part VIII surface the FR
    adapter dictates: the signing-officer row is marked ``isPublicEmployeeName``
    + ``originJurisdiction: "FR"`` so the build-time publication gate
    (``applyPublicationPolicy`` / SIG-PUB-017) **withholds** it under FR-GDPR —
    where the US dossier publishes the equivalent name. The DECP marché is a
    recorded gap, not a figure: its rights are UNDETERMINED (Licence Ouverte 2.0
    outside the accepted SPDX set pending HG-03), so its content stays
    link-posture and is never re-published here.
    """
    return {
        "slug": "gex-videoprotection",
        "subject_label": "Commune de Gex — vidéoprotection (arrêté préfectoral)",
        "jurisdiction": "Gex, Ain, France",
        "jurisdictionCode": "FR",
        "lang": "fr",
        "asOf": _AS_OF,
        "rulesetVersion": _RULESET_VERSION,
        "source_families": [
            "Arrêté préfectoral (Recueil des actes administratifs de l'Ain, ODbL)",
            "Avis de marché public (DECP — lien seulement, droits en revue HG-03)",
            "Registre CADA (Ma Dada — lien seulement)",
        ],
        "authorization": {
            "approving_body": "Préfecture de l'Ain",
            "vote": None,
            "consent_agenda": None,
            "public_comment": None,
            "date": "2026-02-01",
        },
        "termination": {
            "auto_renews": True,
            "notice_window_days": None,
            "expiry_date": "2031-02-01",
        },
        "legal_regime": {
            "state_statute": "Code de la sécurité intérieure, art. L251-1 à L255-1",
            "local_ordinance": None,
            "disclosure_duties": [
                "RGPD — droit d'accès",
                "CADA — communication des documents administratifs",
            ],
        },
        "gaps": [
            {
                "label": "Marché DECP — droits non résolus (HG-03)",
                "kind": "UNRESOLVED",
                "subject_id": "contract:france:decp-2025kazvs0000000",
                "predicate_id": "contract_value",
                "note": "Le marché DECP 2025kazvs0000000 existe (posture lien); ses "
                "droits sont UNDETERMINED — contenu exclu de l'export publié "
                "jusqu'à la revue HG-03 (§42 fail-closed).",
            },
            {
                "label": "Partenaires de partage de données",
                "kind": "NOT_RESEARCHED",
                "subject_id": "agency:france:gex-police-municipale",
                "predicate_id": "sharing_partners",
                "note": "SIG n'a pas recherché les partenaires de partage.",
            },
        ],
        "sections": [
            {
                "section_id": "at_a_glance",
                "rows": [
                    {"label": "Exploitant", "value": "Commune de Gex"},
                    {"label": "Technologie", "value": "Vidéoprotection (caméras fixes)"},
                    {"label": "Statut", "value": "Autorisée par arrêté préfectoral"},
                ],
            },
            {
                "section_id": "what_is_deployed",
                "rows": [
                    {
                        "label": "Type de dispositif",
                        "value": "Caméras fixes de vidéoprotection",
                    },
                    {
                        "label": "Base légale",
                        "value": "Arrêté préfectoral 01-2026-0451 (CSI L251-1 à L255-1)",
                    },
                ],
            },
            {
                "section_id": "cost_and_expiry",
                "rows": [
                    {
                        "label": "Valeur du marché",
                        "value": None,
                        "absence": "UNRESOLVED",
                        "subject_id": "contract:france:decp-2025kazvs0000000",
                        "predicate_id": "contract_value",
                        "note": "Marché DECP en lien — droits UNDETERMINED, revue HG-03.",
                    },
                    {
                        "label": "Expiration de l'autorisation",
                        "value": "2031-02-01",
                        "note": "Cinq ans, renouvelable (dérivé de la date d'effet).",
                    },
                ],
            },
            {
                "section_id": "who_else_can_see",
                "rows": [
                    {
                        "label": "Partenaires de partage",
                        "value": None,
                        "absence": "NOT_RESEARCHED",
                        "subject_id": "agency:france:gex-police-municipale",
                        "predicate_id": "sharing_partners",
                    },
                ],
            },
            {
                "section_id": "configuration_and_retention",
                "rows": [
                    {
                        "label": "Durée de conservation (jours)",
                        "value": None,
                        "absence": "NO_EVIDENCE_FOUND",
                        "subject_id": "sig:deployment:france-gex-videoprotection",
                        "predicate_id": "configured_retention_days",
                    },
                ],
            },
            {
                "section_id": "usage",
                "rows": [
                    {
                        "label": "Consultations (fenêtre)",
                        "value": None,
                        "absence": "NOT_RESEARCHED",
                    },
                ],
            },
            {
                "section_id": "where_the_hardware_is",
                "rows": [
                    {
                        "label": "Dispositifs cartographiés",
                        "value": None,
                        "absence": "NO_EVIDENCE_FOUND",
                        "note": "Aucune couche OSM n'a été importée pour cette commune.",
                    },
                ],
            },
            {
                "section_id": "policy",
                "rows": [
                    {
                        "label": "Base légale",
                        "value": "Code de la sécurité intérieure L251-1 à L255-1",
                    },
                    {
                        "label": "Régime d'accès aux documents",
                        "value": "fr.cada — jamais us.foia (SIG-ONTO-068)",
                    },
                ],
            },
            {
                "section_id": "accountability_events",
                "rows": [
                    {
                        "label": "Autorisation préfectorale",
                        "value": "Arrêté en vigueur depuis le 2026-02-01",
                    },
                    # The public-employee-name row the FR-GDPR publication gate
                    # withholds (SIG-PUB-017; contrast: the US dossier publishes it).
                    {
                        "label": "Signataire de l'arrêté",
                        "value": "M. le préfet de l'Ain",
                        "isPublicEmployeeName": True,
                        "originJurisdiction": "FR",
                    },
                ],
            },
            {
                "section_id": "timeline",
                "rows": [
                    {"label": "2025-04-01", "value": "Marché DECP notifié (lien)"},
                    {"label": "2026-02-01", "value": "Arrêté préfectoral en vigueur"},
                    {"label": "2031-02-01", "value": "Expiration (renouvelable)"},
                ],
            },
            {"section_id": "what_we_dont_know"},
            {
                "section_id": "how_we_know_this",
                "rows": [
                    {
                        "label": "Sources",
                        "value": "RAA de l'Ain (ODbL), DECP (lien), Ma Dada (lien)",
                    },
                    {
                        "label": "Méthodologie",
                        "value": "/methodology/",
                        "documentUrl": "/methodology/",
                    },
                ],
            },
        ],
    }


def build_web_dossiers(jurisdiction: str) -> list[dict[str, Any]]:
    """Return the web dossier bundle for ``jurisdiction`` (``okc``, ``france``)."""
    if jurisdiction == "france":
        return [_france_dossier()]
    if jurisdiction != "okc":
        raise ValueError(
            f"no jurisdiction dossier bundle for {jurisdiction!r} (buildable: 'okc', 'france')"
        )
    return [_okc_dossier()]
