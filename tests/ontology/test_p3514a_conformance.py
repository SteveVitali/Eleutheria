# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.14a ontology-side conformance: the group-13 batch plus the vocabulary
hygiene items the ticket lands.

Covers (commit-stable invariants only — generated artifacts are compared to
their source, never hand-asserted values):

* SIG-ONTO-028 — ``operator_absent`` is registered (absence is countable).
* SIG-ONTO-035 — ``mfa_required`` is a ConfigurationState slot AND a predicate.
* SIG-ONTO-051 — every one of the twelve power properties has a carrier on the
  model surface (schema class, slot, predicate, capability slug, or tech domain).
* SIG-ONTO-055 — every active technology slug is family-prefixed; retired
  entries carry ``superseded_by`` pointing at an active slug; no reflexive
  ``skos:broader`` and no cycle survives generation.
* SIG-ONTO-057 — ``us.le.rtcc`` is an OrganizationType member.
* SIG-STORE-037 — every crosswalk carries an explicit SKOS relation and its
  ``lossy`` flag; broadMatch/relatedMatch rows are never silently lossless.
* SIG-STORE-044 — the Wikidata QID→vendor crosswalk exists and its claim
  predicates are registered.
* SIG-GEO-002 — every ``ST_DWithin`` call site casts to ``geography``.
* Succession retirement — ``SuccessionKind``/``succession``/``succession_kind``
  are gone from the schema AND the generated artifacts.
"""

from __future__ import annotations

import json

import pytest
from support import REPO_ROOT, generated_dir, load_vocab


@pytest.fixture(scope="module")
def registry() -> dict:
    return json.loads((generated_dir() / "registry" / "predicate_registry.json").read_text())


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads((generated_dir() / "jsonschema" / "sig.schema.json").read_text())


@pytest.fixture(scope="module")
def vocab_summary() -> dict:
    return json.loads((generated_dir() / "registry" / "vocab_summary.json").read_text())


def _registered_predicates(registry: dict) -> set[str]:
    return {p["predicate_id"] for p in registry["predicates"]}


def _capability_slugs(summary: dict) -> set[str]:
    return set(summary["capability"]["slugs"])


def _class_attrs(schema: dict, name: str) -> set[str]:
    return set(schema["$defs"][name].get("properties", {}))


# --- SIG-ONTO-028 / 035 / 057 -------------------------------------------------


def test_operator_absent_predicate_is_registered(registry: dict) -> None:
    assert "operator_absent" in _registered_predicates(registry)


def test_mfa_slot_on_configuration_state_and_registry(schema: dict, registry: dict) -> None:
    assert "mfa_required" in _class_attrs(schema, "ConfigurationState")
    assert "mfa_required" in _registered_predicates(registry)


def test_rtcc_is_an_organization_type(schema: dict) -> None:
    assert "us.le.rtcc" in schema["$defs"]["OrganizationType"]["enum"]


# --- SIG-ONTO-051: the twelve power properties each have a carrier ------------


# The §12.9 carrier table, mapped onto falsifiable artifacts. Every carrier is
# asserted against the generated schema, registry, capability vocab, or the
# technology source — a carrier that disappears is a conformance defect.
def test_all_twelve_power_property_carriers_exist(
    schema: dict, registry: dict, vocab_summary: dict
) -> None:
    preds = _registered_predicates(registry)
    caps = _capability_slugs(vocab_summary)
    tech = load_vocab("technology")
    domains = {d["slug"] for d in tech["domains"]}

    carriers: dict[str, bool] = {
        "sensor_density": "PhysicalAsset" in schema["$defs"],
        "historical_retention": "retention_days" in _class_attrs(schema, "ConfigurationState"),
        "cross_jurisdictional_sharing": bool(
            {"configured_access_edge", "configured_sharing_partner"} & preds
        ),
        "centralized_search": "federates_search_to" in preds
        and any(s.startswith("search.") and s.endswith(".state") for s in caps)
        and any(s.startswith("search.") and s.endswith(".national") for s in caps),
        "automated_alerts": any(s.startswith("alert.") for s in caps)
        and "distributes_list_to" in preds,
        "database_integration": bool(
            {
                "ingests_feed_from",
                "resells_data_from",
                "requests_data_from",
                "subscribes_to",
            }
            & preds
        ),
        "private_public_access": "enrolls_asset_into" in preds,
        "analytics": "analytics-inference" in domains,
        "identity_resolution": any(s.startswith("search.face.") for s in caps)
        and "search.person_records.commercial" in caps,
        "institutional_policy": "Policy" in schema["$defs"],
        "legal_permissibility": "LegalInstrument" in schema["$defs"]
        and "authorization_state" in preds,
        "operator_behavior": "UsageAggregate" in schema["$defs"] and "observed_use_edge" in preds,
    }
    missing = sorted(name for name, ok in carriers.items() if not ok)
    assert not missing and len(carriers) == 12, f"power properties without a carrier: {missing}"


# --- SIG-ONTO-055: family-prefix rule, retirement, SKOS hygiene ---------------


def test_every_active_technology_slug_is_family_prefixed() -> None:
    tech = load_vocab("technology")
    offenders: list[str] = []
    for dom in tech["domains"]:
        for fam in dom["families"]:
            for t in fam["technologies"]:
                if t.get("status") == "retired":
                    continue
                if not t["slug"].startswith(fam["slug"] + "-"):
                    offenders.append(f"{fam['slug']}:{t['slug']}")
    assert not offenders, f"non-family-prefixed active slugs: {offenders}"


def test_retired_technologies_are_superseded_never_deleted() -> None:
    tech = load_vocab("technology")
    active: set[str] = set()
    retired: list[dict] = []
    for dom in tech["domains"]:
        for fam in dom["families"]:
            for t in fam["technologies"]:
                if t.get("status") == "retired":
                    retired.append(t)
                else:
                    active.add(t["slug"])
    assert len(retired) == 40, f"expected the 40 recorded retirements, saw {len(retired)}"
    unlinked = [t["slug"] for t in retired if t.get("superseded_by") not in active]
    assert not unlinked, f"retired slugs with no live successor: {unlinked}"


def test_no_reflexive_or_cyclic_broader_in_technology_graph() -> None:
    """The same check the generator performs, at the source level: the
    (child → parent) broader graph has no self-loop and no cycle."""
    tech = load_vocab("technology")
    edges: set[tuple[str, str]] = set()
    for dom in tech["domains"]:
        for fam in dom["families"]:
            edges.add((fam["slug"], dom["slug"]))
            for t in fam["technologies"]:
                # The generator keys a retired entry under its `retired/` IRI —
                # a retired slug may legitimately equal its family's slug (the
                # slug it shadowed) without producing a reflexive edge.
                node = f"retired/{t['slug']}" if t.get("status") == "retired" else t["slug"]
                edges.add((node, fam["slug"]))
    reflexive = sorted(a for a, b in edges if a == b)
    assert not reflexive, f"reflexive broader edge(s): {reflexive}"
    live = set(edges)
    while live:
        parents = {b for _, b in live}
        leaves = {a for a, _ in live} - parents
        assert leaves, "cyclic broader graph — no leaf remains"
        live = {(a, b) for a, b in live if a not in leaves}


def test_succession_vocabulary_is_retired_everywhere(schema: dict) -> None:
    # BL-047 / RISK-P3-04: OrganizationRelation is the surviving temporal model.
    assert "SuccessionKind" not in schema["$defs"]
    org_attrs = _class_attrs(schema, "Organization")
    assert "succession" not in org_attrs
    assert "succession_kind" not in org_attrs
    # The reified model's vocabulary survives: OrganizationRelationType is the
    # seven-value relation enum (SIG-IDENT-016) the relation records carry.
    assert "OrganizationRelationType" in schema["$defs"]
    src = (REPO_ROOT / "ontology" / "src" / "ontology" / "schema" / "common.yaml").read_text()
    assert "SuccessionKind:" not in src


# --- SIG-STORE-037 / 044 -------------------------------------------------------


def test_every_crosswalk_has_explicit_relation_and_lossy_flag() -> None:
    cw = load_vocab("crosswalks")
    relations = {"exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch"}
    for row in cw["crosswalks"]:
        assert row["relation"] in relations, row
        assert "lossy" in row, f"crosswalk missing its lossy flag: {row}"
        # A broader/related external axis is never silently lossless —
        # broadMatch/relatedMatch must carry the flag explicitly (never the
        # fabricated precision of an undeclared default).
        if row["relation"] in {"broadMatch", "relatedMatch"}:
            assert row["lossy"] is True, row


def test_wikidata_qid_vendor_crosswalk_exists(registry: dict) -> None:
    cw = load_vocab("crosswalks")
    links = cw["wikidata_vendor_links"]
    assert links, "no QID→vendor links"
    for row in links:
        assert str(row["qid"]).startswith("Q") and row["vendor"], row
    for pred in ("manufacturer_qid", "brand_qid", "operator_qid"):
        assert pred in _registered_predicates(registry)


# --- SIG-GEO-002: ST_DWithin must cast to geography -----------------------------


def test_st_dwithin_call_sites_cast_to_geography() -> None:
    """Metre-based distance filters compare geography, never geometry — an
    uncast ST_DWithin measures degrees and the proximity test lies."""
    offenders: list[str] = []
    for path in (REPO_ROOT / "ops" / "src").rglob("*.py"):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if "ST_DWithin" in line and "::geography" not in line:
                offenders.append(f"{path.name}:{lineno}")
    for path in (REPO_ROOT / "db" / "src").rglob("*.py"):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if "ST_DWithin" in line and "::geography" not in line:
                offenders.append(f"{path.name}:{lineno}")
    assert not offenders, f"ST_DWithin without a ::geography cast: {offenders}"
