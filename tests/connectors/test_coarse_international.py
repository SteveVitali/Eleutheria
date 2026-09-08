# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coarse international datasets (§22.7, §52, SIG-ENG-036/SIG-INGEST-042, P18.1).

Country- and vendor-level international datasets MUST be ingested at explicit
coarse granularity and MUST NEVER be disaggregated to agency level by inference.
"""

from __future__ import annotations

import pytest
from connectors.registry import get

from connectors import coarse_international as ci


def test_all_three_named_datasets_are_registered_and_gated() -> None:
    # §22.7: the coarse datasets are registered LINK-posture and not yet permitted.
    for sid, dataset in ci.DATASETS.items():
        rec = get(sid)
        assert rec.custody_posture.value == "LINK"
        assert rec.ingestion_permitted is False
        assert dataset.granularity in ci.COARSE_GRANULARITIES


def test_country_and_vendor_granularities_are_declared() -> None:
    assert ci.DATASETS["carnegie_ai_gsi"].granularity == "country"
    assert ci.DATASETS["facial_recognition_world_map"].granularity == "country"
    assert ci.DATASETS["aspi_mapping_chinas_tech_giants"].granularity == "vendor"


def test_coarse_claim_stamps_explicit_granularity_and_preserves_raw_value() -> None:
    dataset = ci.DATASETS["carnegie_ai_gsi"]
    row = ci.coarse_claim(
        dataset,
        subject_kind="jurisdiction",
        subject_id="jurisdiction:iso.3166-1:CN",
        predicate="uses_ai_surveillance",
        value=True,
        raw_value="China — AI surveillance: yes",
        attribution="Carnegie Endowment",
    )
    assert row["granularity"] == "country"  # explicit, never inferred finer
    assert row["disaggregation_prohibited"] is True
    assert row["raw_value"] == "China — AI surveillance: yes"  # P2 preserved
    assert row["subject_kind"] == "jurisdiction"


def test_vendor_dataset_claims_a_vendor_subject() -> None:
    dataset = ci.DATASETS["aspi_mapping_chinas_tech_giants"]
    row = ci.coarse_claim(
        dataset,
        subject_kind="vendor",
        subject_id="sig:org:hikvision",
        predicate="operates_in_country",
        value="RS",
        raw_value="Hikvision — Serbia",
        attribution="ASPI",
    )
    assert row["granularity"] == "vendor"


@pytest.mark.parametrize("dataset_id", ["carnegie_ai_gsi", "aspi_mapping_chinas_tech_giants"])
@pytest.mark.parametrize("subject_kind", sorted(ci.DISAGGREGATED_SUBJECT_KINDS))
def test_agency_level_disaggregation_is_refused(dataset_id: str, subject_kind: str) -> None:
    # SIG-ENG-036 / SIG-INGEST-042: neither a country-level index NOR a vendor-level
    # dataset may be pinned to an agency (or deployment/device) by inference — that
    # manufactures precision (P4).
    dataset = ci.DATASETS[dataset_id]
    with pytest.raises(ci.DisaggregationError):
        ci.coarse_claim(
            dataset,
            subject_kind=subject_kind,
            subject_id="atlas:some-agency",
            predicate="uses_surveillance",
            value=True,
            raw_value="x",
            attribution="upstream",
        )


def test_country_dataset_rejects_a_vendor_subject_and_vice_versa() -> None:
    # The subject kind must match the dataset's own granularity.
    with pytest.raises(ci.DisaggregationError):
        ci.assert_not_disaggregated(ci.DATASETS["carnegie_ai_gsi"], "vendor")
    with pytest.raises(ci.DisaggregationError):
        ci.assert_not_disaggregated(ci.DATASETS["aspi_mapping_chinas_tech_giants"], "jurisdiction")


def test_a_non_coarse_granularity_is_rejected_at_construction() -> None:
    with pytest.raises(ci.CoarseGranularityError):
        ci.CoarseDataset(source_id="x", name="x", granularity="agency")
