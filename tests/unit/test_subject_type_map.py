# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed subject-scheme → entity-type map (P35.14b; L1 NEW-5 / FM-17).

``db/src/db/data/subject_entity_types.toml`` is the versioned, fail-closed
artifact the sink's mint path consults (SIG-IDENT-025). These tests pin the
artifact's contract: every declared type is a ``vocab_entity_type`` member,
longest-prefix matching is deterministic, and an unmapped value refuses —
never a silent ``deployment``. No Docker needed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from db.subject_types import (
    KNOWN_ENTITY_TYPES,
    UnmappedSubjectScheme,
    entity_type_for_prefix,
    entity_type_for_subject,
    map_version,
    mapped_prefixes,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_map_is_versioned() -> None:
    # The version is what the typed-identity decision rows stamp — a missing
    # version would make a correction unversioned, so load fails closed.
    assert re.fullmatch(r"\d+\.\d+\.\d+", map_version())


def test_every_declared_type_is_a_vocab_member() -> None:
    for prefix in mapped_prefixes():
        assert entity_type_for_prefix(prefix) in KNOWN_ENTITY_TYPES, prefix


def test_known_entity_types_mirror_the_seed() -> None:
    # KNOWN_ENTITY_TYPES is the frozen copy of vocab_entity_type's INSERT —
    # a seed_vocab change must update both deliberately.
    sql = (REPO_ROOT / "db" / "deploy" / "seed_vocab.sql").read_text()
    block = sql.split("INSERT INTO vocab_entity_type", 1)[1].split(";")[0]
    seeded = set(re.findall(r"\('([a-z_]+)',", block))
    assert KNOWN_ENTITY_TYPES == seeded


def test_declared_subjects_mint_their_map_types() -> None:
    cases = {
        "traffic_camera:dot511:nyc:cam-1": "physical_asset",
        "osm:node/12345": "physical_asset",
        "data_driven:agency:okcpd": "organization",
        "agency:okc:okcpd-1": "organization",
        "agency_registry_entry:fbi_cde:OK0090100": "organization",
        "contract:okc-flock-c241032": "contract",
        "procurement_notice:sam:abc-1": "contract",
        "funding_instrument:usaspending:fain-1": "funding_instrument",
        "flock_portal:okc-pd": "data_system",
        "seed:statute_seed": "data_system",
        "sig:dataset:bia-tribal-leaders-directory": "data_system",
        "jurisdiction:france": "jurisdiction",
        "jurisdiction:iso.3166-1:FR": "jurisdiction",
        "legal_instrument:france:raa:arrete-01": "legal_instrument",
        "agenda_item:granicus:tenant:item-9": "legal_instrument",
        "legislative_bill:openstates:hb-1": "legal_instrument",
        "sig:document:tolc-lgds-ast-2025-11-19": "legal_instrument",
        "legal_proceeding:accountability:case-1": "legal_proceeding",
        "records:muckrock:req-1": "records_request",
        "madada:request_event/42": "records_request",
        "accountability:src:incident-1": "accountability_event",
        "usage_aggregate:a:b:c": "usage_aggregate",
        "audit_deployment:okcpd": "deployment",
        "audit_org:okcpd": "organization",
        "atlas:okcpd:alpr": "deployment",
        "ccops:okc:okcpd": "policy",
        "pathways:rtcc:federation": "deployment",
        "sig:deployment:okc-okcpd-flock": "deployment",
    }
    for subject, expected in cases.items():
        assert entity_type_for_subject(subject) == expected, subject


def test_longest_prefix_wins() -> None:
    # ``data_driven:agency:`` (organization) beats any shorter ``data_driven:``
    # family entry — and there is deliberately no bare ``data_driven:`` entry.
    assert entity_type_for_subject("data_driven:agency:x") == "organization"
    with pytest.raises(UnmappedSubjectScheme):
        entity_type_for_subject("data_driven:something-else")


def test_an_unmapped_scheme_refuses_never_defaults() -> None:
    # The pre-P35.14b defect: every unknown subject minted 'deployment'. An
    # unmapped value must raise — the sink quarantines it.
    for subject in ("totally:new:scheme", "subj:1", "deployment:okc"):
        with pytest.raises(UnmappedSubjectScheme):
            entity_type_for_subject(subject)


def test_no_map_entry_can_quietly_produce_deployment_by_default() -> None:
    # There is no catch-all prefix: every entry is a colon-terminated family
    # prefix (so `agency:` can never match `agency_registry_entry:` or
    # `agencyx:`), and "" is never declared.
    assert all(p.endswith(":") for p in mapped_prefixes())
    assert "" not in mapped_prefixes()


def test_prefixes_are_unique_and_sorted_longest_first() -> None:
    prefixes = mapped_prefixes()
    assert len(prefixes) == len(set(prefixes))
    assert list(prefixes) == sorted(prefixes, key=len, reverse=True)
