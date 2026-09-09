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

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

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


# --- the REFERENCE-capture path (§47, P18.1, P21.8) ---------------------------
#
# The three datasets stay LINK-posture and ``ingestion_permitted = false`` until a
# rights packet + an operator flip changes a row (§22.7). This connector is the
# capture path that runs the moment such a flip happens: it drives the extractor
# above through the eight-stage framework, so ``run --mode live`` on a flipped
# source ingests it — and ``run --mode live`` on an un-flipped source REFUSES at
# the loader gate (exit 3), exactly as every other gated source does. Over
# committed fixtures it runs in replay/shadow with no network (SIG-INGEST-018/019).

from .stages import CaptureRef, Connector, FetchResult, RunContext, register  # noqa: E402


def parse_coarse(data: bytes) -> dict[str, Any]:
    """Parse a coarse-international dataset capture (pure function of the bytes)."""
    payload = json.loads(data.decode("utf-8"))
    if "rows" not in payload:
        raise ValueError("a coarse-international capture must carry a 'rows' list (§22.7)")
    return payload


@register
class CoarseInternationalConnector(Connector):
    """The `coarse_international` connector — country/vendor-level datasets (§22.7, §47).

    The REFERENCE-capture path for the three coarse international datasets (Carnegie
    AI GSI, Facial Recognition World Map, ASPI Mapping China's Tech Giants). It runs
    on the P04.1 eight-stage framework and routes every row through
    :func:`coarse_claim`, so the **anti-disaggregation guard** (SIG-ENG-036 /
    SIG-INGEST-042) cannot be bypassed: a country/vendor claim can never be pinned
    to an agency. The datasets stay LINK-posture until a packet + flip permits a
    live run, so a live run against an un-flipped source is refused at the loader
    gate (exit 3); replay/shadow run over committed fixtures with no network.
    """

    name = "coarse_international"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        return parse_coarse(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        dataset_id = str(parsed.get("dataset") or ctx.source.id)
        return [{"dataset_id": dataset_id, "row": dict(row)} for row in parsed.get("rows", [])]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            dataset = DATASETS[str(raw["dataset_id"])]
            subject_kind = _SUBJECT_KIND_FOR_GRANULARITY[dataset.granularity]
            row = raw["row"]
            out.append(
                coarse_claim(
                    dataset,
                    subject_kind=subject_kind,
                    subject_id=str(row["subject_id"]),
                    predicate=str(row["predicate"]),
                    value=row.get("value"),
                    raw_value=str(row["raw_value"]),
                    attribution=str(row.get("attribution", dataset.name)),
                )
            )
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for claim in linked:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        return out


__all__ = [
    "COARSE_GRANULARITIES",
    "DATASETS",
    "DISAGGREGATED_SUBJECT_KINDS",
    "CoarseDataset",
    "CoarseGranularityError",
    "CoarseInternationalConnector",
    "DisaggregationError",
    "assert_not_disaggregated",
    "coarse_claim",
    "parse_coarse",
]
