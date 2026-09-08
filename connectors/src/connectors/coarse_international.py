# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coarse international datasets, ingested at explicit coarse granularity (§22.7, §52).

Some international sources are inherently coarse: country-level surveillance
indices (Carnegie's AI Global Surveillance Index), global facial-recognition maps
(the Facial Recognition World Map), and vendor-level international datasets (ASPI's
Mapping China's Tech Giants). SIG-ENG-036 / SIG-INGEST-042 bind their ingestion:
each MUST enter the graph as a claim carrying its **explicit coarse granularity**
and MUST NEVER be disaggregated to agency level by inference — a country-level
index attached to a specific agency would manufacture precision the source never
had (P4, SIG-ONTO-021).

This module is the claim-shaping layer that enforces that. It does not fetch —
these sources are registered LINK-posture and ``ingestion_permitted = false`` until
their rights are reviewed (§22.7) — it owns the **claim shape and the
anti-disaggregation guard** every coarse-international connector must route through:

* :func:`coarse_claim` stamps each row with the dataset's declared granularity and
  a subject at that granularity (a country/region Jurisdiction, or a vendor
  Organization), never an agency.
* :func:`assert_not_disaggregated` is the hard gate: offering an agency-level
  subject for a coarse dataset raises :class:`DisaggregationError`, so the P4
  violation is caught at the seam rather than silently persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: The coarse granularities a country/vendor-level international dataset may claim.
#: `agency`/`device` are deliberately absent — that is the level SIG-INGEST-042
#: forbids inferring.
COARSE_GRANULARITIES = frozenset({"country", "region", "vendor"})

#: Subject kinds that represent an agency-level (or finer) disaggregation. Attaching
#: a coarse dataset's claim to one of these is the inference SIG-ENG-036 prohibits.
DISAGGREGATED_SUBJECT_KINDS = frozenset(
    {"agency", "organization", "deployment", "device", "physical_asset"}
)

#: Subject kinds a coarse claim MAY carry, by granularity. ``vendor`` denotes an
#: Organization bearing the **vendor role** (§12.4) — "vendor" is a role, never an
#: entity subtype (SIG-ONTO-012) — kept distinct from the bare ``organization``
#: subject kind, which is banned precisely because it is the ambiguous agency-level
#: pin SIG-INGEST-042 forbids.
_SUBJECT_KIND_FOR_GRANULARITY = {
    "country": "jurisdiction",
    "region": "jurisdiction",
    "vendor": "vendor",
}


class DisaggregationError(Exception):
    """Raised when a coarse dataset is disaggregated toward agency level (SIG-INGEST-042).

    The mechanical form of SIG-ENG-036: a country-/vendor-level claim MUST NOT be
    pinned to a specific agency, deployment, or device by inference. Raised naming
    the dataset and subject so the P4 defect is auditable.
    """


class CoarseGranularityError(Exception):
    """Raised when a dataset declares a granularity that is not coarse."""


@dataclass(frozen=True)
class CoarseDataset:
    """A registered coarse international dataset (§22.7, SIG-INGEST-042)."""

    #: The source-registry id this dataset is seeded under.
    source_id: str
    #: Human-readable dataset name.
    name: str
    #: The dataset's explicit coarse granularity — one of :data:`COARSE_GRANULARITIES`.
    granularity: str

    def __post_init__(self) -> None:
        if self.granularity not in COARSE_GRANULARITIES:
            raise CoarseGranularityError(
                f"dataset {self.source_id!r} declares granularity {self.granularity!r}; "
                f"coarse international datasets are one of {sorted(COARSE_GRANULARITIES)} "
                "(SIG-INGEST-042)."
            )


#: The three coarse international datasets named for Stage 6 (§22.7, OL-5.3-01).
#: Country-level indices and a global FR map are `country`; the ASPI vendor study
#: is `vendor`. Each is registered in the source registry (data/sources.toml).
DATASETS: dict[str, CoarseDataset] = {
    "carnegie_ai_gsi": CoarseDataset(
        source_id="carnegie_ai_gsi",
        name="AI Global Surveillance Index (Carnegie)",
        granularity="country",
    ),
    "facial_recognition_world_map": CoarseDataset(
        source_id="facial_recognition_world_map",
        name="Facial Recognition World Map",
        granularity="country",
    ),
    "aspi_mapping_chinas_tech_giants": CoarseDataset(
        source_id="aspi_mapping_chinas_tech_giants",
        name="Mapping China's Tech Giants (ASPI)",
        granularity="vendor",
    ),
}


def assert_not_disaggregated(dataset: CoarseDataset, subject_kind: str) -> None:
    """Reject an agency-level subject for a coarse dataset (SIG-ENG-036/INGEST-042).

    A coarse dataset's claim subject must sit at its own granularity — a
    country/region :class:`Jurisdiction` or a vendor :class:`Organization` — never
    an agency, deployment, or device. Anything in :data:`DISAGGREGATED_SUBJECT_KINDS`
    raises :class:`DisaggregationError`.
    """
    if subject_kind in DISAGGREGATED_SUBJECT_KINDS:
        raise DisaggregationError(
            f"dataset {dataset.source_id!r} is {dataset.granularity}-level; attaching its "
            f"claim to a {subject_kind!r} subject would disaggregate it to agency level by "
            "inference (SIG-ENG-036 / SIG-INGEST-042, P4)."
        )
    expected = _SUBJECT_KIND_FOR_GRANULARITY[dataset.granularity]
    if subject_kind != expected:
        raise DisaggregationError(
            f"dataset {dataset.source_id!r} is {dataset.granularity}-level; its claim "
            f"subject must be a {expected!r}, not {subject_kind!r} (SIG-INGEST-042)."
        )


def coarse_claim(
    dataset: CoarseDataset,
    *,
    subject_kind: str,
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    attribution: str,
) -> dict[str, Any]:
    """Build one coarse-granularity claim row (SIG-INGEST-042).

    Routes through :func:`assert_not_disaggregated` so the granularity guard cannot
    be bypassed, then stamps the row with the dataset's ``granularity``, the raw
    upstream value (P2), and a ``disaggregation_prohibited`` marker that travels with
    the claim so no downstream step re-pins it to an agency.
    """
    assert_not_disaggregated(dataset, subject_kind)
    return {
        "record_kind": "claim",
        "source_id": dataset.source_id,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2: the coarse source value is preserved verbatim
        "granularity": dataset.granularity,  # SIG-INGEST-042: explicit, never inferred finer
        "disaggregation_prohibited": True,
        "source_attribution": attribution,
    }


__all__ = [
    "COARSE_GRANULARITIES",
    "DATASETS",
    "DISAGGREGATED_SUBJECT_KINDS",
    "CoarseDataset",
    "CoarseGranularityError",
    "DisaggregationError",
    "assert_not_disaggregated",
    "coarse_claim",
]
