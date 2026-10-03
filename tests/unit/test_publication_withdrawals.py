# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.19 (F-337, SIG-GOV-007) — the committed publication-withdrawal list.

Nine live Atlas face-recognition rows cite the BuzzFeed News Clearview
article whose agency data came from "internal documents, which were
uncovered by a source who declined to be named" (I4-F103) — leak
provenance, the same class `wired_shotspotter_leak` is refused under
(SIG-PUB-005). The committed `sig.publication-withdrawals/1` table is the
single list every public layer matches — export writer, API reads, web
export-mode readers.
"""

from __future__ import annotations

from policy import withdrawals

#: The nine F-337 upstream Atlas rows (I4-L048, verified against
#: docs/build/logs/P34.19/atlas_download.csv).
F337_AOS_IDS = {
    "AOS000953",
    "AOS000960",
    "AOS000961",
    "AOS000962",
    "AOS000963",
    "AOS000964",
    "AOS000965",
    "AOS000966",
    "AOS004507",
}

#: The ten live claim ids the list suppresses — the nine F-337 claims plus
#: Miami's second candidate, suppressed fail-closed until a host-side join
#: narrows it to AOS000960 vs AOS005165 (D-P34.19-1).
F337_CLAIM_IDS = {
    "01a0a6cb-b1e9-7552-b25c-aba32b812402",
    "01a0a6d0-e0e1-7fd4-9bc9-2b8c9bc5d30f",
    "01a0a6cb-be21-70cb-9dfe-ea2cca7891d9",
    "01a0a6cb-bfb0-71f8-9da3-fc0b3296c889",
    "01a0a6cb-c14b-7dc8-a13b-b13937727dd5",
    "01a0a6cb-c2d5-717b-bbf6-f4d6f1b1da9c",
    "01a0a6cb-c479-74c3-9660-c52ef5f73a3f",
    "01a0a6cb-c603-7c0f-98a6-1567cfe2b513",
    "01a0a6cf-9316-79ab-9b3f-305fcab85bfe",
    "01a0a6cb-bca2-7111-b994-11c9b0fc129f",
}

F337_ENTITY_IDS = {
    "01a0a6cb-b180-7a78-921d-dddeae9bfa96",
    "01a0a6cb-bc2c-7d8f-9d8b-18e491cfce74",
    "01a0a6cb-bdad-7143-8359-1818da838b08",
    "01a0a6cb-bf42-7c76-98c8-2cf3aba70844",
    "01a0a6cb-c0d7-7568-95da-cc0d216450eb",
    "01a0a6cb-c255-755d-a9a7-0796a34d1fa9c",
    "01a0a6cb-c407-7eff-9e32-022f19efc1dd",
    "01a0a6cb-c588-7f93-b07e-7e6f0e7ef70b",
    "01a0a6cf-929c-7b12-b18c-53caed58eb8a",
}

BUZZFEED = (
    "https://www.buzzfeednews.com/article/ryanmac/clearview-ai-fbi-ice-global-law-enforcement"
)


def test_the_list_covers_exactly_the_nine_f337_rows() -> None:
    entries = withdrawals.withdrawal_entries()
    assert len(entries) == 9
    assert {e["upstream_id"] for e in entries} == F337_AOS_IDS
    assert withdrawals.withdrawn_upstream_ids() == F337_AOS_IDS


def test_every_entry_is_an_atlas_leak_provenance_withdrawal() -> None:
    for entry in withdrawals.withdrawal_entries():
        assert entry["source_id"] == "eff_atlas_of_surveillance"
        assert entry["predicate"] == "deployment_exists"
        assert entry["raw_value"] == "Face Recognition"
        assert entry["reason"] == "leak-provenance"
        assert entry["disposition"] == "withdraw"
        assert entry["kind"] == "rights_withdrawal"
        assert entry["tainted_locator"] == BUZZFEED
        assert "F-337" in entry["authority"]
        assert entry["entity_id"] in F337_ENTITY_IDS
        assert set(entry["claim_ids"]) <= F337_CLAIM_IDS
        assert entry["agency"]


def test_the_suppressed_id_sets_cover_claims_entities_and_upstream() -> None:
    assert withdrawals.withdrawn_claim_ids() == F337_CLAIM_IDS
    assert withdrawals.withdrawn_entity_ids() == F337_ENTITY_IDS
    for target in F337_CLAIM_IDS | F337_ENTITY_IDS | F337_AOS_IDS:
        assert withdrawals.is_withdrawn(target), target


def test_the_miami_candidate_is_fail_closed_with_a_note() -> None:
    miami = next(e for e in withdrawals.withdrawal_entries() if e["upstream_id"] == "AOS000960")
    assert miami["candidate_claim_ids"] == ["01a0a6cb-bca2-7111-b994-11c9b0fc129f"]
    assert "AOS005165" in miami["note"]
    assert "D-P34.19-1" in miami["note"]
    assert withdrawals.is_withdrawn("01a0a6cb-bca2-7111-b994-11c9b0fc129f")


def test_lookup_helpers_match_by_kind() -> None:
    assert (
        withdrawals.withdrawal_for_claim("01a0a6cb-b1e9-7552-b25c-aba32b812402")["upstream_id"]
        == "AOS000953"
    )
    assert (
        withdrawals.withdrawal_for_entity("01a0a6cf-929c-7b12-b18c-53caed58eb8a")["upstream_id"]
        == "AOS004507"
    )
    assert withdrawals.withdrawal_for_claim("not-a-claim") is None
    assert withdrawals.withdrawal_for_entity("not-an-entity") is None
    # claim ids never match as entities and vice versa — the suppression is
    # the claim, not the whole agency record.
    assert withdrawals.withdrawal_for_entity("01a0a6cb-b1e9-7552-b25c-aba32b812402") is None


def test_non_target_ids_pass_through() -> None:
    assert not withdrawals.is_withdrawn("AOS005165")
    assert withdrawals.withdrawal_for("01a0a6cb-0000-0000-0000-000000000000") is None


def test_schema_gate_is_pinned() -> None:
    assert withdrawals.publication_withdrawals()["schema"] == "sig.publication-withdrawals/1"


def test_entries_are_unique_per_upstream_row() -> None:
    seen: set[str] = set()
    for entry in withdrawals.withdrawal_entries():
        assert entry["upstream_id"] not in seen
        seen.add(entry["upstream_id"])
