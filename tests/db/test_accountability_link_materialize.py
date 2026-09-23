# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize the accountability linkage into the real spine (P28.6, ADR-099).

Exercises the ``accountability_link_materialize`` sqitch change (deploy/verify happen in
the conftest container) and the append-only, idempotent materializer over PG18+PostGIS:

* a real deployment→vendor→contract→funding→policy→oversight chain is derived and WRITTEN
  as labelled L4 ``inference.derived_fact`` rows, EACH citing its establishing claims (§3.1);
* a re-run over an unchanged spine inserts **+0** (idempotent on ``input_digest``);
* the **procured ≠ deployed** guard holds — a bare procurement (``contracted_device_count``)
  claim on the deployment produces NO link (an honest gap, not a deployment edge);
* the read seam round-trips every link with its provenance.
"""

from __future__ import annotations

from conftest import seed_claim_prerequisites
from inference.accountability import (
    materialize_accountability_links,
    read_materialized_accountability_links,
)

# The accountability-layer entity-ref predicates the chain rides on.
_REF_PREDICATES = (
    "operator",
    "buyer",
    "seller",
    "recipient",
    "applies_to",
    "deployments",
)


def _register_predicates(conn: object) -> None:
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('never_resolve','fixture: recorded, not adjudicated') ON CONFLICT DO NOTHING"
    )
    for pred in _REF_PREDICATES:
        conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','entity_ref','entity_ref','fixture','IMMUTABLE',NULL,"
            "'never_resolve') ON CONFLICT DO NOTHING",
            (pred,),
        )
    # A procurement/count predicate, to prove procured ≠ deployed.
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES('contracted_device_count','1.0.0','integer','quantity','fixture',"
        "'IMMUTABLE',NULL,'never_resolve') ON CONFLICT DO NOTHING"
    )


def _entity(conn: object, entity_type: str) -> object:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,)
    ).fetchone()[0]


def _ref_claim(
    conn: object, prereqs: dict, subject_id: object, predicate: str, object_entity: object
) -> object:
    """Insert one tier-0 entity-ref claim ``subject --predicate--> object_entity``."""
    return conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'entity_ref',%s,'value',%s,%s,'2026-05-01T00:00:00Z','R1','D1','I1',"
        "%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject_id,
            predicate,
            object_entity,
            str(object_entity),
            str(object_entity),
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]


def _seed_full_chain(conn: object) -> dict:
    """Seed a deployment with a full governance chain through its operator org."""
    prereqs = seed_claim_prerequisites(conn)
    _register_predicates(conn)
    dep = prereqs["subject_id"]  # a 'deployment' entity
    org = _entity(conn, "organization")
    vendor = _entity(conn, "organization")
    contract = _entity(conn, "contract")
    funding = _entity(conn, "funding_instrument")
    policy = _entity(conn, "policy")
    event = _entity(conn, "accountability_event")
    claims = {
        "op": _ref_claim(conn, prereqs, dep, "operator", org),
        "buy": _ref_claim(conn, prereqs, contract, "buyer", org),
        "sell": _ref_claim(conn, prereqs, contract, "seller", vendor),
        "fund": _ref_claim(conn, prereqs, funding, "recipient", org),
        "pol": _ref_claim(conn, prereqs, policy, "applies_to", dep),
        "evt": _ref_claim(conn, prereqs, event, "deployments", dep),
    }
    return {
        "prereqs": prereqs,
        "dep": dep,
        "org": org,
        "vendor": vendor,
        "contract": contract,
        "funding": funding,
        "policy": policy,
        "event": event,
        "claims": claims,
    }


def test_sqitch_change_deployed_input_digest_column_and_index(conn: object) -> None:
    """The ``accountability_link_materialize`` change deployed the idempotency contract."""
    # The column is selectable on the L4 derived_fact table.
    conn.execute("SELECT input_digest FROM inference.derived_fact WHERE false")
    # The partial unique index exists in the inference schema.
    exists = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='inference' "
        "AND indexname='derived_fact_input_digest_key')"
    ).fetchone()[0]
    assert exists is True


def test_materializes_the_full_governance_chain_with_provenance(conn: object) -> None:
    """A real deployment→vendor→contract→funding→policy→oversight chain, each citing claims."""
    seed = _seed_full_chain(conn)
    summary = materialize_accountability_links(conn)
    # Five chain segments, all inserted.
    assert summary.inserted == 5
    assert summary.links_derived == 5
    assert set(summary.by_link_type) == {
        "has_vendor",
        "procured_under_contract",
        "funded_by",
        "governed_by_policy",
        "overseen_by",
    }

    links = read_materialized_accountability_links(conn)
    by_type = {row["link_type"]: row for row in links}
    assert set(by_type) == set(summary.by_link_type)

    # Every link is an accountability_link:* L4 row citing its establishing claims (§3.1).
    for row in links:
        assert row["predicate_id"].startswith("accountability_link:")
        assert row["establishing_claims"]
        assert row["establishing_claims"] == sorted(row["establishing_claims"])

    # The vendor is reached THROUGH the contract, citing operator+buyer+seller.
    vendor = by_type["has_vendor"]
    assert vendor["object_id"] == str(seed["vendor"])
    assert vendor["via_contract"] == str(seed["contract"])
    assert set(vendor["establishing_claims"]) == {
        str(seed["claims"]["op"]),
        str(seed["claims"]["buy"]),
        str(seed["claims"]["sell"]),
    }
    assert by_type["procured_under_contract"]["object_id"] == str(seed["contract"])
    assert by_type["funded_by"]["object_id"] == str(seed["funding"])
    assert by_type["governed_by_policy"]["object_id"] == str(seed["policy"])
    assert by_type["overseen_by"]["object_id"] == str(seed["event"])


def test_re_run_is_idempotent_plus_zero(conn: object) -> None:
    """A second pass over an unchanged spine inserts +0 (idempotent on input_digest)."""
    _seed_full_chain(conn)
    first = materialize_accountability_links(conn)
    assert first.inserted == 5
    before = conn.execute(
        "SELECT count(*) FROM inference.derived_fact WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    second = materialize_accountability_links(conn)
    assert second.inserted == 0
    assert second.skipped_existing == 5
    after = conn.execute(
        "SELECT count(*) FROM inference.derived_fact WHERE input_digest IS NOT NULL"
    ).fetchone()[0]
    assert after == before  # append-only, no duplicate rows


def test_procured_is_not_deployed(conn: object) -> None:
    """A bare procurement claim on a deployment produces NO link (honest gap, two layers stay
    separate). A deployment with only a ``contracted_device_count`` claim — the classic
    procurement signal — links to nothing: procurement is not deployment (§46 RISK-P21-16)."""
    prereqs = seed_claim_prerequisites(conn)
    _register_predicates(conn)
    dep = prereqs["subject_id"]  # a 'deployment' entity
    # A procurement/count claim (value claim, NOT an accountability entity-ref).
    conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,value_num,"
        "unit,raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
        "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s,'contracted_device_count','quantity','value','25',25,'cameras','25',"
        "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,0)",
        (dep, prereqs["author_id"], prereqs["run_id"], prereqs["rights_id"]),
    )
    summary = materialize_accountability_links(conn)
    assert summary.deployments_considered == 1  # the deployment anchor IS present
    assert summary.links_derived == 0  # …but procurement does not deploy anything
    assert summary.inserted == 0
    assert read_materialized_accountability_links(conn) == []


def test_a_merged_away_deployment_is_not_anchored(conn: object) -> None:
    """A deployment merged into another (resolver dedup) is not a resolved anchor."""
    seed = _seed_full_chain(conn)
    survivor = _entity(conn, "deployment")
    conn.execute("UPDATE entity SET merged_into=%s WHERE entity_id=%s", (survivor, seed["dep"]))
    summary = materialize_accountability_links(conn)
    # The merged-away deployment is skipped; the survivor carries no chain claims → no links.
    assert summary.inserted == 0
