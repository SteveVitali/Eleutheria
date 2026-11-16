# SPDX-License-Identifier: Apache-2.0
"""P37.46b — the organisation cascade planner (R11-CONF-13 13b; SIG-CONF-004).

Pure-pass tests: tier 0 exact shared authoritative identifiers, tier 1 the
established org_crosswalk_entry crosswalk, tier 2 surfaced 'possibly the
same' (never linked), the collision exclusion, the civil-ORI refusal, and the
run-key / digest determinism the +0 re-run contract rests on.
"""

from __future__ import annotations

import pytest
from resolution.cascade import CascadeContext
from resolution.org_cascade_pg import (
    ORG_CASCADE_RESOLVER_VERSION,
    ORG_CASCADE_RULESET_VERSION,
    OrgCascadeResult,
    OrgIdentifier,
    OrgRecord,
    org_decision_digest,
    plan_org_cascade,
)


def _rec(
    eid: str,
    *,
    name: str | None = None,
    state: str | None = None,
    org_class: str = "us.le.municipal_police",
    ids: tuple[tuple[str, str], ...] = (),
    xwalk: bool = False,
    attr: tuple[str, ...] = (),
) -> OrgRecord:
    return OrgRecord(
        entity_id=eid,
        organization_class=org_class,
        name=name,
        state=state,
        identifiers=tuple(OrgIdentifier(s, v, f"claim-{eid}-{s}-{v}") for s, v in ids),
        is_crosswalk_entry=xwalk,
        attribute_claims=attr,
    )


def _by_pair(result: OrgCascadeResult):
    return {(d.left, d.right): d for d in result.decisions}


def test_tier0_shared_authoritative_identifier() -> None:
    a = _rec("e-a", ids=(("us.fbi.ori", "OK0261100"),))
    b = _rec("e-b", ids=(("us.fbi.ori", "OK0261100"),))
    result = plan_org_cascade([a, b])
    d = _by_pair(result)[("e-a", "e-b")]
    assert d.tier == 0 and d.relation == "same_as" and d.disposition == "auto_link"
    assert d.evidence["rule"] == "exact_shared_canonical_identifier"
    assert d.evidence["shared_identifiers"] == [{"scheme": "us.fbi.ori", "value": "OK0261100"}]
    # Every match records its establishing claims (SIG-IDENT-025).
    assert set(d.evidence_claims) == {
        "claim-e-a-us.fbi.ori-OK0261100",
        "claim-e-b-us.fbi.ori-OK0261100",
    }
    assert result.clusters["e-a"] == result.clusters["e-b"]


def test_tier0_covers_every_lane_scheme() -> None:
    for scheme, value in (
        ("us.sam.uei", "ZK12AB34CD56"),
        ("us.census.geoid", "4046250000"),
        ("wikidata.qid", "Q4915"),
        ("gleif.lei", "529900T8BM49AURSDO55"),
    ):
        a = _rec("e-a", ids=((scheme, value),))
        b = _rec("e-b", ids=((scheme, value),))
        d = _by_pair(plan_org_cascade([a, b])).get(("e-a", "e-b"))
        assert d is not None and d.tier == 0, (scheme, d)


def test_civil_ori_never_auto_links() -> None:
    # 9th char alphabetic = civil/applicant ORI (SIG-IDENT-003): no tier-0.
    a = _rec("e-a", ids=(("us.fbi.ori", "OK026110A"),))
    b = _rec("e-b", ids=(("us.fbi.ori", "OK026110A"),))
    result = plan_org_cascade([a, b])
    assert _by_pair(result) == {}


def test_invalid_ori_never_auto_links() -> None:
    a = _rec("e-a", ids=(("us.fbi.ori", "not-an-ori"),))
    b = _rec("e-b", ids=(("us.fbi.ori", "not-an-ori"),))
    assert _by_pair(plan_org_cascade([a, b])) == {}


def test_non_tier0_scheme_does_not_link() -> None:
    a = _rec("e-a", ids=(("us.state_abbr", "OK"),))
    b = _rec("e-b", ids=(("us.state_abbr", "OK"),))
    assert _by_pair(plan_org_cascade([a, b])) == {}


def test_tier1_established_crosswalk() -> None:
    # The LEAIC-style upstream row asserts ORI + GEOID on ONE crosswalk entity.
    c = _rec(
        "e-c",
        ids=(("us.fbi.ori", "OK0261100"), ("us.census.geoid", "4046250000")),
        xwalk=True,
    )
    a = _rec("e-a", ids=(("us.fbi.ori", "OK0261100"),))
    b = _rec("e-b", ids=(("us.census.geoid", "4046250000"),))
    result = plan_org_cascade([a, b, c])
    pairs = _by_pair(result)
    # The entry links at tier 0 to both sides (literal shared identifiers)…
    assert pairs[("e-a", "e-c")].tier == 0
    assert pairs[("e-b", "e-c")].tier == 0
    # …and the bridged pair records tier 1 with the entry as its evidence.
    d = pairs[("e-a", "e-b")]
    assert d.tier == 1 and d.relation == "same_as" and d.disposition == "auto_link"
    assert d.evidence["rule"] == "established_upstream_crosswalk"
    assert d.evidence["crosswalk_entity"] == "e-c"
    assert all(
        e in result.clusters and result.clusters[e] == result.clusters["e-a"]
        for e in ("e-b", "e-c")
    )


def test_tier1_needs_a_crosswalk_entry() -> None:
    # Two orgs sharing nothing do not link — even when their identifiers are
    # complementary lanes.
    a = _rec("e-a", ids=(("us.fbi.ori", "OK0261100"),))
    b = _rec("e-b", ids=(("us.census.geoid", "4046250000"),))
    assert _by_pair(plan_org_cascade([a, b])) == {}


def test_tier2_possibly_same_surfaced_never_linked() -> None:
    a = _rec("e-a", name="Tulsa Police Department", state="OK", attr=("claim-a",))
    b = _rec("e-b", name="Tulsa Police Department", state="OK", attr=("claim-b",))
    result = plan_org_cascade([a, b])
    d = _by_pair(result)[("e-a", "e-b")]
    assert d.tier == 2 and d.relation == "possibly_same" and d.disposition == "surfaced"
    assert d.evidence["rule"] == "normalized_name_state_class"
    # Surfaced, never linked: the pair stays in distinct clusters.
    assert result.clusters["e-a"] != result.clusters["e-b"]
    assert set(d.evidence_claims) == {"claim-a", "claim-b"}


def test_tier2_requires_state_match() -> None:
    a = _rec("e-a", name="Tulsa Police Department", state="OK")
    b = _rec("e-b", name="Tulsa Police Department", state="TX")
    assert _by_pair(plan_org_cascade([a, b])) == {}


def test_tier2_requires_class_match() -> None:
    a = _rec("e-a", name="Tulsa Police Department", state="OK")
    b = _rec("e-b", name="Tulsa Police Department", state="OK", org_class="us.le.sheriff")
    assert _by_pair(plan_org_cascade([a, b])) == {}


def test_tier2_collision_list_excludes() -> None:
    a = _rec("e-a", name="Springfield Police Department", state="IL")
    b = _rec("e-b", name="Springfield Police Department", state="IL")
    result = plan_org_cascade([a, b])
    assert _by_pair(result) == {}
    assert result.collision_excluded_pairs == 1


def test_linked_pair_gets_no_possibly_same_row() -> None:
    a = _rec(
        "e-a",
        name="Tulsa Police Department",
        state="OK",
        ids=(("wikidata.qid", "Q1"),),
    )
    b = _rec(
        "e-b",
        name="Tulsa Police Department",
        state="OK",
        ids=(("wikidata.qid", "Q1"),),
    )
    pairs = _by_pair(plan_org_cascade([a, b]))
    assert len(pairs) == 1 and pairs[("e-a", "e-b")].relation == "same_as"


def test_run_key_deterministic_and_input_sensitive() -> None:
    a = _rec("e-a", ids=(("wikidata.qid", "Q1"),))
    b = _rec("e-b", ids=(("wikidata.qid", "Q1"),))
    k1 = plan_org_cascade([a, b]).run_key
    k2 = plan_org_cascade([b, a]).run_key  # input order never matters
    assert k1 == k2 and k1.startswith("orgcascade:")
    changed = plan_org_cascade([a, _rec("e-b", ids=(("wikidata.qid", "Q2"),))]).run_key
    assert changed != k1


def test_decision_digest_stable() -> None:
    a = _rec("e-a", ids=(("wikidata.qid", "Q1"),))
    b = _rec("e-b", ids=(("wikidata.qid", "Q1"),))
    result = plan_org_cascade([a, b])
    d = result.decisions[0]
    assert org_decision_digest(result.run_key, d) == org_decision_digest(result.run_key, d)
    assert org_decision_digest("other-run", d) != org_decision_digest(result.run_key, d)


def test_summary_counts() -> None:
    a = _rec("e-a", ids=(("wikidata.qid", "Q1"),), name="A PD", state="OK")
    b = _rec("e-b", ids=(("wikidata.qid", "Q1"),), name="B PD", state="TX")
    c = _rec("e-c", name="C PD", state="OK")
    d = _rec("e-d", name="C PD", state="OK")
    result = plan_org_cascade([a, b, c, d])
    s = result.summary()
    assert s["record_type"] == "sig.org-cascade-run/1"
    assert s["same_as_pairs"] == 1 and s["possibly_same_pairs"] == 1
    assert s["auto_link_tiers"] == [0, 1]
    assert s["resolved_organizations"] == 3  # {a,b} merged; c,d stay distinct


def test_pair_order_is_canonical() -> None:
    a = _rec("e-z", ids=(("wikidata.qid", "Q1"),))
    b = _rec("e-a", ids=(("wikidata.qid", "Q1"),))
    d = plan_org_cascade([a, b]).decisions[0]
    assert (d.left, d.right) == ("e-a", "e-z")


def test_ruleset_versions_stamped() -> None:
    result = plan_org_cascade([])
    assert result.ruleset_version == ORG_CASCADE_RULESET_VERSION
    assert result.resolver_version == ORG_CASCADE_RESOLVER_VERSION


def test_context_collision_extension() -> None:
    # An injected context can extend the collision set without code changes.
    ctx = CascadeContext(
        name_collisions=frozenset({"tulsa police department"}),
        shared_hosting_domains=frozenset(),
        tier0_schemes=frozenset(
            {"us.fbi.ori", "us.census.geoid", "gleif.lei", "us.sam.uei", "wikidata.qid"}
        ),
    )
    a = _rec("e-a", name="Tulsa Police Department", state="OK")
    b = _rec("e-b", name="Tulsa Police Department", state="OK")
    result = plan_org_cascade([a, b], context=ctx)
    assert _by_pair(result) == {}
    assert result.collision_excluded_pairs == 1


@pytest.mark.parametrize("count", [1, 40])
def test_empty_and_singleton_inputs(count: int) -> None:
    recs = [_rec(f"e-{i}") for i in range(count)]
    result = plan_org_cascade(recs)
    assert result.decisions == ()
    assert len(result.clusters) == count
