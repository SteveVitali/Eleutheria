# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.22 / F-504 — the shared claim-identity function (evidence.claim_identity).

The digest covers only what the claim IS: volatile acquisition fields (row
position, page/capture URL, capture digest, fetch time, upstream version
counters) never enter identity; the temporal qualifier is in identity for the
registry's ``obs`` class only; ``value_json`` is canonicalised; and
``payload_version`` seals the scheme. These tests pin invariants, never a
specific digest value.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from evidence.claim_identity import (
    NEVER_IDENTITY_KEYS,
    OBSERVATION_STRATEGIES,
    PAYLOAD_VERSION,
    canonical_json,
    claim_digest,
    digest_base,
    temporal_class,
)


def _claim(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subject_id": "cam:okc-42",
        "predicate_id": "camera_operator",
        "value": "ACME Surveillance",
        "source_id": "okc_registry",
        "license": "CC0-1.0",
        "record_kind": "claim",
    }
    base.update(over)
    return base


# --- the volatile field classes (F-504's named set) ---------------------------


def test_row_and_page_position_never_in_identity() -> None:
    a = _claim(row_index=0, feature_index=1, page=1, page_url="https://reg/p1")
    b = _claim(row_index=17, feature_index=99, page=3, page_url="https://reg/p9")
    assert claim_digest(a) == claim_digest(b)


def test_capture_identity_and_fetch_time_never_in_identity() -> None:
    a = _claim(capture_digest="a" * 64, retrieved_at="2026-01-01T00:00:00Z")
    b = _claim(capture_digest="b" * 64, retrieved_at="2026-06-30T12:00:00Z")
    c = _claim(fetched_at="2026-06-30", capture_id="cap-9", ocfl_version="v7")
    assert claim_digest(a) == claim_digest(b) == claim_digest(c)


def test_upstream_version_counters_never_in_identity() -> None:
    a = _claim(osm_version=1, source_version="v1")
    b = _claim(osm_version=42, source_version="v9", release_digest="deadbeef")
    assert claim_digest(a) == claim_digest(b)


def test_nested_acquisition_metadata_drops_completely() -> None:
    a = _claim(evidence={"capture_digest": "x" * 64, "retrieved_at": "t0"})
    b = _claim()  # no `evidence` mapping at all — same claim
    assert claim_digest(a) == claim_digest(b)


def test_generated_and_envelope_fields_never_in_identity() -> None:
    a = _claim()
    b = _claim(
        claim_id="3f4f5d18-0000-4000-8000-000000000001",
        sys_period="[2026-01-01,)",
        recorded_at="2026-01-01T00:00:00Z",
    )
    assert claim_digest(a) == claim_digest(b)
    # record_kind is a routing envelope, not identity: bare vs explicit "claim"
    # records are the same claim.
    bare = _claim()
    del bare["record_kind"]
    assert claim_digest(bare) == claim_digest(a)


def test_volatile_key_list_covers_the_named_classes() -> None:
    for key in (
        "row_index",
        "feature_index",
        "page",
        "page_url",
        "capture_digest",
        "retrieved_at",
        "retrieved_date",
        "osm_version",
        "claim_id",
        "sys_period",
        "recorded_at",
    ):
        assert key in NEVER_IDENTITY_KEYS, key


# --- the obs/ref temporal-qualifier split --------------------------------------


def test_ref_drops_the_temporal_qualifier() -> None:
    a = _claim(valid_from="2024-01-01", observed_at="2024-01-02")
    b = _claim(valid_from="2025-06-01", observed_at="2025-06-02")
    c = _claim()  # no qualifier at all — a ref claim is what it asserts
    assert claim_digest(a, temporal_class="ref") == claim_digest(b, temporal_class="ref")
    assert claim_digest(a, temporal_class="ref") == claim_digest(c, temporal_class="ref")


def test_obs_keeps_the_temporal_qualifier() -> None:
    a = _claim(valid_from="2024-01-01", valid_to="2024-02-01")
    b = _claim(valid_from="2024-02-01", valid_to="2024-03-01")
    c = _claim(valid_from="2024-01-01", valid_to="2024-02-01")
    assert claim_digest(a, temporal_class="obs") != claim_digest(b, temporal_class="obs")
    assert claim_digest(a, temporal_class="obs") == claim_digest(c, temporal_class="obs")


def test_obs_still_drops_volatile_fields() -> None:
    a = _claim(valid_from="2024-01-01", row_index=3, capture_digest="x" * 64)
    b = _claim(valid_from="2024-01-01", row_index=9, capture_digest="y" * 64)
    assert claim_digest(a, temporal_class="obs") == claim_digest(b, temporal_class="obs")


def test_temporal_class_is_registry_read_never_guessed() -> None:
    # The interval family (SIG-RECON-011) is observational; everything else —
    # including the camera-registry strategies whose sighting history lives in
    # claim_evidence (ADR-R9-RESIGHT) — is reference.
    for strategy in OBSERVATION_STRATEGIES:
        assert temporal_class(resolution_strategy=strategy) == "obs"
    assert temporal_class(is_windowed=True) == "obs"
    for strategy in (
        "latest_observation_wins",
        "max_support",
        "authoritative_source_wins",
        "never_resolve",
        None,
    ):
        assert temporal_class(resolution_strategy=strategy) == "ref"


# --- value_json canonicalisation ------------------------------------------------


def test_value_json_key_order_and_whitespace_never_digest() -> None:
    a = _claim(value_json={"b": 2, "a": 1})
    b = _claim(value_json={"a": 1, "b": 2})
    assert claim_digest(a) == claim_digest(b)
    # canonical storage renders one byte string regardless of input order
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert canonical_json({"a": 1}) == '{"a":1}'


def test_value_json_scalar_normalisation() -> None:
    a = _claim(value_json={"count": 30.0})
    b = _claim(value_json={"count": 30})
    assert claim_digest(a) == claim_digest(b)
    d = _claim(value_json={"price": Decimal("30.50")})
    e = _claim(value_json={"price": "30.5"})
    assert claim_digest(d) == claim_digest(e)


def test_value_json_nested_and_datetime_canonicalisation() -> None:
    a = _claim(value_json={"meta": {"z": 1, "a": 2}, "when": datetime(2026, 1, 1, tzinfo=UTC)})
    b = _claim(
        value_json={
            "when": "2026-01-01T00:00:00+00:00",
            "meta": {"a": 2, "z": 1},
        }
    )
    assert claim_digest(a) == claim_digest(b)


def test_value_json_serialised_string_is_the_same_claim() -> None:
    """A stored row's jsonb read back as text digests like the dict form."""
    a = _claim(value_json={"a": 1, "b": [1, 2]})
    b = _claim(value_json='{"b":[1,2],"a":1}')
    assert claim_digest(a) == claim_digest(b)


def test_absent_and_null_members_unify() -> None:
    a = _claim(value_json={"a": 1, "b": None}, unit=None)
    b = _claim(value_json={"a": 1})
    assert claim_digest(a) == claim_digest(b)


def test_payload_version_seals_the_scheme() -> None:
    base = digest_base(_claim(), temporal_class="ref")
    assert base["payload_version"] == PAYLOAD_VERSION
    # A record that carries a stale/forged version can never override the seal.
    forged = _claim(payload_version="sig.claim-payload/0")
    assert digest_base(forged, temporal_class="ref")["payload_version"] == PAYLOAD_VERSION
    assert claim_digest(forged) == claim_digest(_claim())


# --- emitted-vs-stored parity shape ---------------------------------------------


def test_digest_base_is_pure_projection() -> None:
    """The digest base contains no volatile key at any depth."""
    record = _claim(
        row_index=5,
        evidence={"capture_digest": "x" * 64, "note": "kept"},
        qualifiers=[{"qualifier_id": "q1", "capture_digest": "y" * 64}],
    )
    base = digest_base(record, temporal_class="ref")
    assert "row_index" not in base
    assert base["evidence"] == {"note": "kept"}  # non-volatile content survives
    assert base["qualifiers"] == [{"qualifier_id": "q1"}]
    assert "observed_at" not in base
    assert base["payload_version"] == PAYLOAD_VERSION


# --- SIG-INGEST-004 (P35.34): the binding versions are identity ----------------
#
# §21.2 verbatim: "The claim's logical identity MUST include extractor_version
# and normalizer_version." The withheld amendment would have dropped the MUST;
# it stands — these tests pin its behavioural form (same input, different
# binding version → a genuinely new claim id, never a silent re-bind).


def test_extractor_version_is_identity() -> None:
    """Same record minted under extractor v1 vs v2 → different digests."""
    record = _claim()
    v1 = claim_digest(record, extractor_version="extractor-1.0.0", normalizer_version="norm-1.0.0")
    v2 = claim_digest(record, extractor_version="extractor-2.0.0", normalizer_version="norm-1.0.0")
    assert v1 != v2


def test_normalizer_version_is_identity() -> None:
    """Same record minted under normalizer v1 vs v2 → different digests."""
    record = _claim()
    v1 = claim_digest(record, extractor_version="extractor-1.0.0", normalizer_version="norm-1.0.0")
    v2 = claim_digest(record, extractor_version="extractor-1.0.0", normalizer_version="norm-2.0.0")
    assert v1 != v2


def test_same_versions_rebind() -> None:
    """Unchanged versions over identical input preserve parity — the seal
    never churns identity on its own."""
    record = _claim(row_index=0, retrieved_at="2026-10-01T00:00:00Z")
    again = _claim(row_index=9, retrieved_at="2026-10-19T00:00:00Z")
    assert claim_digest(record, extractor_version="e-1", normalizer_version="n-1") == claim_digest(
        again, extractor_version="e-1", normalizer_version="n-1"
    )


def test_sealed_versions_land_in_the_digest_base() -> None:
    base = digest_base(
        _claim(),
        temporal_class="ref",
        extractor_version="extractor-1.0.0",
        normalizer_version="norm-1.0.0",
    )
    assert base["extractor_version"] == "extractor-1.0.0"
    assert base["normalizer_version"] == "norm-1.0.0"


def test_record_carried_versions_enter_identity() -> None:
    """A record that itself declares the versions (top-level or under
    ``evidence``) digests on them — they are content, not volatile
    acquisition metadata."""
    a = _claim(extractor_version="e-1")
    b = _claim(extractor_version="e-2")
    assert claim_digest(a) != claim_digest(b)
    c = _claim(evidence={"extractor_version": "e-1"})
    d = _claim(evidence={"extractor_version": "e-2"})
    assert claim_digest(c) != claim_digest(d)


def test_the_seal_overrides_a_record_carried_value() -> None:
    """The bound version (what the evidence binding writes) wins over
    whatever the record happened to carry — the identity names the version
    actually bound."""
    record = _claim(extractor_version="carried-e")
    sealed = claim_digest(record, extractor_version="bound-e")
    carried = claim_digest(_claim(extractor_version="bound-e"))
    assert sealed == carried
    assert sealed != claim_digest(record)


def test_unsealed_mint_keeps_the_keys_absent() -> None:
    """An asserted-origin mint (no extraction binding) seals nothing — the
    keys stay honestly absent, never a fabricated default."""
    base = digest_base(_claim(), temporal_class="ref")
    assert "extractor_version" not in base
    assert "normalizer_version" not in base
