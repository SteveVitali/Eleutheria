# SPDX-License-Identifier: Apache-2.0
"""P36.41 — the ``sig.entity-page/1`` contract A through the export.

Fixture-level, never living records: entity rows, dispositions, label facts,
claims and materialized edges are fabricated ``raw`` rows (the same tuple
shape ``fetch_export_raw`` produces inside the read snapshot) — the same
harness ``test_entity_slug_history.py`` drives. The A-10 legs asserted here
are the operator's answered decision verbatim (D-K2-1 = b + c): an
auto-allowed organisation gets a keyed twin; every other organisation is
typed ``not_yet_reviewed``; a withheld/person entity emits nothing.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from exports.entity_page import (
    DEGREE_PREDICATES,
    ENTITY_PAGE_SCHEMA,
    ER_DISCLOSURE,
    PAGE_KINDS,
    PAGE_STATE_NOT_YET_REVIEWED,
    PAGE_STATE_PUBLISHED,
    PAGE_STATE_UNPAGED,
    PAGE_STATE_WITHHELD,
    WITHHELD_RELATIONSHIPS_NOTICE,
    build_twin,
    claim_groups,
    degree_only_facts,
    entity_page_artifacts,
    page_claims,
    page_state,
    relation_groups,
    review_record,
)
from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import build_spine_export
from policy.labels import EntityLabel

PUB = "sig-release-2026.09"
GEN = "2026-09-22T00:00:00Z"


def _eid() -> str:
    return str(uuid.uuid4())


def _label(eid: str, kind: str = "org", **over) -> EntityLabel:
    base = dict(
        entity_id=eid,
        sig_id=f"sig:{kind}:{eid}",
        kind=kind,
        url_type=kind,
        label="Acme Surveillance LLC",
        descriptor="Organisation",
        label_basis="source_name",
        label_source_id="src_a",
        place_jkey="usa-ok",
        slug="acme-surveillance-llc",
        hash="4g2wm8q",
        url=f"/entity/{kind}/acme-surveillance-llc--4g2wm8q/",
        disambiguator=None,
        component_id=None,
        part8="pass",
        label_state=None,
        subject_key=f"organization:{eid}",
    )
    base.update(over)
    return EntityLabel(**base)


def _claim_row(
    sid: str,
    pred: str,
    val: str | None,
    cid: str,
    *,
    obj: str | None = None,
    obs: str = "2020-01-28",
    src: str = "src_a",
    spdx: str = "CC-BY-4.0",
    rid: str = "rights-a",
) -> tuple:
    return (
        sid,
        pred,
        val,
        cid,
        obj,
        obs,
        src,
        spdx,
        f"© {src}",
        "yes",
        "yes",
        "https://example/terms",
        rid,
    )


# ---------------------------------------------------------------------------
# page_state — the A-10 decision surface
# ---------------------------------------------------------------------------


def test_page_state_published_for_keyed_page_kind():
    assert page_state(_label(_eid(), "agency")) == PAGE_STATE_PUBLISHED


def test_page_state_not_yet_reviewed_is_typed():
    lbl = _label(_eid(), label=None, slug=None, hash=None, url=None, label_state="not_yet_reviewed")
    assert page_state(lbl) == PAGE_STATE_NOT_YET_REVIEWED
    rec = review_record(lbl)
    assert rec["schema"] == ENTITY_PAGE_SCHEMA
    assert rec["review_state"] == "not_yet_reviewed"
    assert rec["kind"] == "org"
    # the typed state carries no label, key, url or identifier — never an
    # improvised name, never a raw id (SIG-UI-053/108).
    for field in ("label", "slug", "hash", "url", "entity_id", "key"):
        assert field not in rec


def test_page_state_withheld_and_person_emit_nothing():
    assert page_state(_label(_eid(), label_state="withheld")) == PAGE_STATE_WITHHELD
    assert page_state(_label(_eid(), kind="person")) == PAGE_STATE_WITHHELD


def test_page_state_unpaged_for_non_contract_a_kinds():
    # contract A covers organisations, agencies and portals only — a keyed
    # site/notice label is the typed ``unpaged`` absence, never a page.
    for kind in set(("site", "notice", "contract", "atlas", "jurisdiction")) - set(PAGE_KINDS):
        assert page_state(_label(_eid(), kind=kind)) == PAGE_STATE_UNPAGED


# ---------------------------------------------------------------------------
# The twin sections — claims, relations (H-2 fields), degree-only
# ---------------------------------------------------------------------------


def _ctx() -> dict:
    return {
        "resolutions": {},
        "lineage": {},
        "source_names": {"src_a": "EFF Data Driven"},
        "claim_sources": {"c1": {"src_a"}, "c2": {"src_a"}},
        "as_of": date(2026, 9, 22),
    }


def test_claim_groups_carry_the_four_envelope_fields():
    eid = _eid()
    rows = [
        _claim_row(eid, "agency_name", "Acme PD", "c1"),
        _claim_row(eid, "agency_name", "Acme PD", "c2"),
    ]
    by_subj = page_claims(rows)
    groups = claim_groups(
        eid,
        by_subj[eid],
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF Data Driven"},
        claim_sources={"c1": {"src_a"}, "c2": {"src_a"}},
        as_of=date(2026, 9, 22),
    )
    assert len(groups) == 1
    env = groups[0]["envelope"]
    # SIG-UI-004 — the four fields separately, never folded into one word.
    assert set(env) >= {"status", "support", "agreement", "currency"}
    assert groups[0]["claim_ids"] == ["c1", "c2"]
    assert groups[0]["sources"] == [{"id": "src_a", "name": "EFF Data Driven"}]


def test_relation_groups_emit_h2_fields_and_mark_historical():
    eid, partner = _eid(), _eid()
    labels = {partner: _label(partner, "org", label="Vigilant Solutions")}
    rows = [
        _claim_row(eid, "configured_sharing_partner", None, "c1", obj=partner, obs="2020-01-28"),
    ]
    by_subj = page_claims(rows)
    ctx = _ctx()
    groups, withheld = relation_groups(
        eid,
        by_subj[eid],
        edge_rows=[],
        labels=labels,
        resolutions={},
        lineage={},
        source_names=ctx["source_names"],
        claim_sources=ctx["claim_sources"],
        as_of=ctx["as_of"],
    )
    assert not withheld
    assert len(groups) == 1
    grp = groups[0]
    assert grp["direction"] == "outbound"
    item = grp["items"][0]
    # H-2 — relation in words, direction, date + kind, the four epistemic
    # fields, source names, claim ids; historical marked (SIG-UI-116).
    assert item["relation"] == "configured sharing partner"
    assert item["date_kind"] in ("observed", "undated")
    assert set(item) >= {"status", "support", "agreement", "currency"}
    assert item["counterparty"]["label"] == "Vigilant Solutions"
    assert item["counterparty"]["url"]


def test_inbound_relation_counterparty_is_the_subject():
    eid, site = _eid(), _eid()
    labels = {site: _label(site, "site", label="surveillance camera in usa-ok", url=None)}
    labels[site] = _label(site, "site", label="surveillance camera in usa-ok")
    rows = [_claim_row(site, "camera_operator", None, "c1", obj=eid)]
    by_subj = page_claims(rows)
    groups, _ = relation_groups(
        eid,
        by_subj[site],
        edge_rows=[],
        labels=labels,
        **_ctx(),
    )
    assert groups[0]["direction"] == "inbound"
    assert groups[0]["items"][0]["counterparty"]["entity_id"] == site
    # an unpaged-kind counterparty carries no entity-page URL (SIG-UI-068).
    assert groups[0]["items"][0]["counterparty"]["url"] is None


def test_withheld_counterparty_drops_the_row_and_sets_the_notice():
    eid, partner = _eid(), _eid()
    labels = {partner: _label(partner, "org", label_state="withheld")}
    rows = [_claim_row(eid, "seller", None, "c1", obj=partner)]
    by_subj = page_claims(rows)
    groups, withheld = relation_groups(eid, by_subj[eid], edge_rows=[], labels=labels, **_ctx())
    assert groups == []
    assert withheld is True
    doc = build_twin(
        _label(eid),
        publication=PUB,
        generated_at=GEN,
        compartment="sig_graph",
        entity_type="organisation",
        withheld_relationships=withheld,
    )
    # SIG-UI-080 — the mandated sentence, verbatim; no name, no count.
    assert doc["withheld_notice"] == WITHHELD_RELATIONSHIPS_NOTICE


def test_degree_only_is_never_an_edge():
    eid = _eid()
    rows = [
        _claim_row(eid, "sharing_partner_degree", "851", "c1"),
        _claim_row(eid, "configured_sharing_partner", None, "c2", obj=_eid()),
    ]
    by_subj = page_claims(rows)
    degree = degree_only_facts(
        eid, by_subj[eid], source_names={"src_a": "EFF"}, claim_sources={}, as_of=None
    )
    assert len(degree) == 1
    assert degree[0]["counts"] == [851]
    assert degree[0]["claim_ids"] == ["c1"]
    # SIG-UI-117 — the degree predicate never lands in the relations table.
    groups, _ = relation_groups(
        eid,
        by_subj[eid],
        edge_rows=[],
        labels={},
        **_ctx(),
    )
    for grp in groups:
        assert "degree" not in grp["relation"]
    for c in by_subj[eid]:
        assert c.predicate_id in DEGREE_PREDICATES or c.object_entity is not None


def test_materialized_access_edge_joins_the_relations():
    eid, partner = _eid(), _eid()
    labels = {partner: _label(partner, "org", label="Vigilant Solutions")}
    edge = {
        "from_entity": eid,
        "to_entity": partner,
        "edge_type": "configured_access",
        "access_kind": "configured_access",
        "direction": "outbound",
        "evidence_claim": "c1",
        "observed_at": "2020-01-28",
        "valid_to": None,
        "valid_to_kind": "unknown",
    }
    rows = [_claim_row(eid, "configured_sharing_partner", None, "c1", obj=partner)]
    by_subj = page_claims(rows)
    groups, _ = relation_groups(eid, by_subj[eid], edge_rows=[edge], labels=labels, **_ctx())
    access = [g for g in groups if g["access_kind"] == "configured_access"]
    assert access and access[0]["items"][0]["counterparty"]["label"] == "Vigilant Solutions"


# ---------------------------------------------------------------------------
# The per-compartment artifact map
# ---------------------------------------------------------------------------


def test_artifacts_emit_per_compartment_for_published_entities():
    eid = _eid()
    labels = {eid: _label(eid, "agency")}
    rows = [_claim_row(eid, "agency_name", "Acme PD", "c1")]
    arts = entity_page_artifacts(
        labels,
        claim_rows=rows,
        edge_rows=[],
        identifiers={eid: [("us.cgac.agency_code", "OK-ACME")]},
        entity_types={eid: "organisation"},
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF"},
        entity_comps={eid: {"sig_graph"}},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=date(2026, 9, 22),
        retrieval=date(2026, 9, 22),
    )
    twin_path = "web/entity/agency/acme-surveillance-llc--4g2wm8q/index.sig_graph.json"
    assert twin_path in arts
    # contract B emits the download siblings beside the twin.
    assert {p.rsplit(".", 1)[-1] for p in arts} == {"json", "csv"}
    doc, comp = arts[twin_path]
    assert comp == "sig_graph"
    assert doc["schema"] == ENTITY_PAGE_SCHEMA
    assert doc["review_state"] == "published"
    assert doc["er_disclosure"] == ER_DISCLOSURE
    assert doc["identifiers"] == [{"scheme": "us.cgac.agency_code", "value": "OK-ACME"}]
    # contract B (P37.22) — populated where evidence exists, typed empty
    # where it does not.
    assert doc["contradictions"] == []
    assert doc["timeline"] and doc["timeline"][0]["date"] == "2020-01-28"
    assert doc["downloads"] and doc["related"]["sources"] == [
        {"id": "src_a", "name": "EFF", "url": "/sources/src_a/"}
    ]
    assert doc["access"]["closures"] == []


def test_artifacts_skip_review_state_withheld_and_unpaged():
    keyed = _eid()
    review = _eid()
    withheld = _eid()
    person = _eid()
    site = _eid()
    labels = {
        keyed: _label(keyed, "agency"),
        review: _label(
            review, label=None, slug=None, hash=None, url=None, label_state="not_yet_reviewed"
        ),
        withheld: _label(withheld, label_state="withheld"),
        person: _label(person, kind="person"),
        site: _label(site, kind="site"),
    }
    arts = entity_page_artifacts(
        labels,
        claim_rows=[],
        edge_rows=[],
        identifiers={},
        entity_types={},
        resolutions={},
        lineage={},
        source_names={},
        entity_comps={},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=None,
        retrieval=date(2026, 9, 22),
    )
    paths = list(arts)
    # only the keyed agency emits (twin + the contract-B download siblings);
    # review/withheld/person/unpaged states emit nothing.
    assert len(paths) == 3
    assert all("acme-surveillance-llc--4g2wm8q" in p for p in paths)


# ---------------------------------------------------------------------------
# End-to-end through build_spine_export (the test_entity_slug_history harness)
# ---------------------------------------------------------------------------


def _shaping_claim(cid: str, sid: str, pred: str, *, value_text: str | None = None) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=0,
        source_id="src_a",
        connector_name="camreg",
        effective_rights_id="rights-CC-BY-4.0",
        effective_spdx="CC-BY-4.0",
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution="© src_a",
        effective_terms_url="https://example/terms",
    )


def _rows(claims: list[ShapingClaim]) -> list[tuple]:
    return [
        (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]


def test_export_emits_entity_page_twins():
    org = _eid()
    claims = [_shaping_claim(f"{org}-lat", _eid(), "camera_latitude", value_text="35.46")]
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
        "label_entities": [
            (
                org,
                "organisation",
                f"organization:{org}",
                None,
                "Acme Surveillance LLC",
                False,
                None,
            ),
        ],
        "label_entity_dispositions": [],
        "label_facts": [],
        "entity_labels": [],
        "entity_page_claims": [
            _claim_row(org, "agency_name", "Acme Surveillance LLC", "c1"),
        ],
    }
    dataset = build_shaped_dataset(
        raw,
        as_of="2026-09-22",
        generated_at="2026-09-22T00:00:00Z",
        spine_label="unit",
    )
    export = build_spine_export(
        dataset,
        raw,
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 9, 22),
            as_of_belief=date(2026, 9, 22),
            ruleset_version="ruleset/1",
            resolver_version="resolver/1",
        ),
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )
    twin_paths = [p for p in export.web_artifacts if p.startswith("web/entity/") and "/index." in p]
    assert len(twin_paths) == 1
    doc = json.loads(export.web_artifacts[twin_paths[0]].decode("utf-8"))
    assert doc["schema"] == "sig.entity-page/1"
    assert doc["label"] == "Acme Surveillance LLC"
    assert doc["review_state"] == "published"


# ---------------------------------------------------------------------------
# Access closures (GX-07 / P37.21) — D-K2-2 = a, descriptive only
# ---------------------------------------------------------------------------

from exports.entity_page import (  # noqa: E402
    CLOSURE_MAX_PATHS_PER_DIRECTION,
    _closure_for_compartment,
    access_closures,
    closure_edge_pools,
)


def _edge_row(frm: str, to: str, cid: str, kind: str = "configured_access", **over) -> dict:
    """A materialized ``relationship`` row (the ``read_materialized_edges`` shape)."""
    row = {
        "from_entity": frm,
        "to_entity": to,
        "edge_type": kind,
        "access_kind": kind,
        "direction": "a_to_b",
        "valid_from_kind": "unknown",
        "valid_to_kind": "ongoing",
        "asserted_by": frm,
        "observed_at": "2020-01-28",
        "valid_from": None,
        "valid_to": None,
        "evidence_claim": cid,
        "evidence_claims": [cid],
        "relationship_id": f"rel-{cid}",
    }
    row.update(over)
    return row


def _closure_labels(*ids: str) -> dict:
    return {eid: _label(eid, "org", label=f"Org {eid[-2:]}") for eid in ids}


def test_closure_pools_reverse_for_the_inbound_question():
    a, b = _eid(), _eid()
    out_pool, in_pool = closure_edge_pools([_edge_row(a, b, "c1")])
    assert out_pool[0].from_org == a and out_pool[0].to_org == b
    # the inbound pool runs the same evidence in the holder's direction.
    assert in_pool[0].from_org == b and in_pool[0].to_org == a
    assert in_pool[0].evidence == ("c1",)


def test_access_closures_emit_both_directions_with_hops_and_evidence():
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, b, c)
    edges = [_edge_row(a, b, "c1"), _edge_row(b, c, "c2")]
    pools = closure_edge_pools(edges)
    ctx = _ctx()
    kw = dict(
        labels=labels,
        source_names=ctx["source_names"],
        claim_sources=ctx["claim_sources"],
        as_of=ctx["as_of"],
    )

    groups, withheld = access_closures(a, pools, **kw)
    assert not withheld
    assert [g["direction"] for g in groups] == ["outbound"]
    grp = groups[0]
    assert grp["question"] == "whose data this entity can reach"
    assert grp["counts"] == {"publishable": 1, "historical": 0, "speculative": 0}
    (path,) = grp["paths"]
    assert path["source"] == a and path["target"] == c
    assert path["hop_count"] == 2 and path["temporal_status"] == "live"
    assert path["speculative"] is False
    # per-hop evidence + labelled endpoints (SIG-UI-025 / §3.1).
    assert [h["evidence"] for h in path["hops"]] == [["c1"], ["c2"]]
    assert path["hops"][0]["from"]["label"] is not None
    assert path["hops"][1]["to"]["entity_id"] == c
    assert path["claim_ids"] == ["c1", "c2"]

    groups_c, _ = access_closures(c, pools, **kw)
    assert [g["direction"] for g in groups_c] == ["inbound"]
    ipath = groups_c[0]["paths"][0]
    # the chain reads in the real accessor → … → entity direction.
    assert ipath["source"] == a and ipath["target"] == c
    assert [h["from_org"] for h in ipath["hops"]] == [a, b]
    assert ipath["hops"][0]["to_org"] == b

    # B has only direct (one-hop) edges — a 1-hop path is the observation,
    # already a relationship row, never a closure inference.
    groups_b, _ = access_closures(b, pools, **kw)
    assert groups_b == []


def test_access_closures_mark_historical_and_speculative():
    a, b, c, d, e = (_eid() for _ in range(5))
    labels = _closure_labels(a, b, c, d, e)
    ctx = _ctx()
    kw = dict(
        labels=labels,
        source_names=ctx["source_names"],
        claim_sources=ctx["claim_sources"],
        as_of=ctx["as_of"],
    )

    # a path through a recorded end bound is labelled historical (live vs
    # historical — never present-tense, never dropped).
    ended = _edge_row(b, c, "c2", valid_to_kind="exact", valid_to="2019-01-01")
    groups, _ = access_closures(a, closure_edge_pools([_edge_row(a, b, "c1"), ended]), **kw)
    assert groups[0]["counts"]["historical"] == 1
    assert groups[0]["paths"][0]["temporal_status"] == "historical"

    # ≤ 3 hops publishable; beyond is labelled speculative (SIG-RECON-050).
    chain = [
        _edge_row(a, b, "c1"),
        _edge_row(b, c, "c2"),
        _edge_row(c, d, "c3"),
        _edge_row(d, e, "c4"),
    ]
    groups, _ = access_closures(a, closure_edge_pools(chain), **kw)
    flat = [p for g in groups for p in g["paths"]]
    spec = [p for p in flat if p["speculative"]]
    assert spec and all(p["hop_count"] > 3 for p in spec)
    assert groups[0]["counts"]["speculative"] == len(spec)


def test_access_closures_never_compose_observed_use():
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, b, c)
    edges = [_edge_row(a, b, "c1", "observed_use"), _edge_row(b, c, "c2", "observed_use")]
    groups, _ = access_closures(
        a,
        closure_edge_pools(edges),
        labels=labels,
        source_names={},
        claim_sources={},
        as_of=date(2026, 9, 22),
    )
    # SIG-RECON-049 #2 — use is not access; the chain never forms.
    assert groups == []


def test_access_closures_drop_a_path_through_a_withheld_org():
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, c)
    labels[b] = _label(b, "org", label_state="withheld")
    edges = [_edge_row(a, b, "c1"), _edge_row(b, c, "c2")]
    groups, withheld = access_closures(
        a,
        closure_edge_pools(edges),
        labels=labels,
        source_names={},
        claim_sources={},
        as_of=date(2026, 9, 22),
    )
    # SIG-UI-080 — the withheld hop is never named or counted; the whole
    # path drops and the twin's notice sentence covers the absence.
    assert groups == []
    assert withheld is True


def test_access_closures_need_an_as_of_snapshot():
    # no snapshot pin → no live/historical marking is ever guessed.
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, b, c)
    arts = entity_page_artifacts(
        labels,
        claim_rows=[],
        edge_rows=[_edge_row(a, b, "c1"), _edge_row(b, c, "c2")],
        identifiers={},
        entity_types={},
        resolutions={},
        lineage={},
        source_names={},
        entity_comps={},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=None,
        retrieval=date(2026, 9, 22),
    )
    for _p, (doc, _comp) in arts.items():
        if "/index." not in _p:
            continue  # the download siblings are not twin docs
        assert doc["access"]["closures"] == []


def test_degree_only_facts_carry_the_d_k2_3_sentences():
    eid = _eid()
    rows = [
        _claim_row(eid, "sharing_partner_degree", "851", "c1"),
        _claim_row(eid, "sharing_partner_degree", "1", "c2"),
    ]
    degree = degree_only_facts(
        eid,
        page_claims(rows)[eid],
        source_names={"src_a": "EFF"},
        claim_sources={},
        as_of=None,
    )
    assert degree[0]["sentences"] == [
        "Shared with 1 agency — partners not named",
        "Shared with 851 agencies — partners not named",
    ]


def test_closure_compartment_filing_requires_every_hops_evidence():
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, b, c)
    edges = [_edge_row(a, b, "c1"), _edge_row(b, c, "c2")]
    groups, _ = access_closures(
        a,
        closure_edge_pools(edges),
        labels=labels,
        source_names={},
        claim_sources={},
        as_of=date(2026, 9, 22),
    )
    # c2 licenses elsewhere → the whole path stays out of sig_graph (ADR-106);
    # a mixed-compartment path files under NEITHER — the derived fact can't
    # be split across incompatible licences.
    filed = _closure_for_compartment(
        groups,
        {"c1": "sig_graph", "c2": "osm_odbl"},
        compartment="sig_graph",
        default_compartment="sig_graph",
    )
    assert filed == []
    assert (
        _closure_for_compartment(
            groups,
            {"c1": "sig_graph", "c2": "osm_odbl"},
            compartment="osm_odbl",
            default_compartment="sig_graph",
        )
        == []
    )
    # both hops' evidence in the compartment → the path files whole.
    other = _closure_for_compartment(
        groups,
        {"c1": "osm_odbl", "c2": "osm_odbl"},
        compartment="osm_odbl",
        default_compartment="sig_graph",
    )
    assert [p["claim_ids"] for g in other for p in g["paths"]] == [["c1", "c2"]]


def test_closure_group_caps_paths_and_reports_more():
    a = _eid()
    partners = [_eid() for _ in range(3)]
    third = [_eid() for _ in range(2)]
    labels = _closure_labels(a, *partners, *third)
    edges = [_edge_row(a, p, f"c{i}") for i, p in enumerate(partners)]
    edges += [
        _edge_row(p, t, f"d{i}")
        for i, (p, t) in enumerate([(partners[0], third[0]), (partners[1], third[1])])
    ]
    groups, _ = access_closures(
        a,
        closure_edge_pools(edges),
        labels=labels,
        source_names={},
        claim_sources={},
        as_of=date(2026, 9, 22),
    )
    filed = _closure_for_compartment(
        groups,
        {},
        compartment="sig_graph",
        default_compartment="sig_graph",
    )
    assert filed[0]["path_count"] == 2
    assert filed[0]["more"] == 0
    assert len(filed[0]["paths"]) == 2
    assert CLOSURE_MAX_PATHS_PER_DIRECTION >= 2  # the cap constant exists


def test_artifacts_emit_closures_only_in_their_compartment():
    a, b, c = _eid(), _eid(), _eid()
    labels = _closure_labels(a, b, c)
    labels[a] = _label(a, "agency", label="Acme PD")
    # distinct keys — the shared fixture slug/hash would collide on path.
    labels[b] = _label(
        b, "org", label="Org b", slug="org-b", hash="7xk3mrb", url="/entity/org/org-b--7xk3mrb/"
    )
    labels[c] = _label(
        c, "org", label="Org c", slug="org-c", hash="2rn6vqc", url="/entity/org/org-c--2rn6vqc/"
    )
    edges = [_edge_row(a, b, "c1"), _edge_row(b, c, "c2")]
    rows = [
        _claim_row(a, "configured_sharing_partner", None, "c1", obj=b),
        _claim_row(b, "configured_sharing_partner", None, "c2", obj=c),
    ]
    arts = entity_page_artifacts(
        labels,
        claim_rows=rows,
        edge_rows=edges,
        identifiers={},
        entity_types={},
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF"},
        # A files under two compartments; the closure evidence licenses to
        # sig_graph, so only the sig_graph twin carries the path (ADR-106).
        entity_comps={a: {"sig_graph", "osm_odbl"}},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=date(2026, 9, 22),
        retrieval=date(2026, 9, 22),
    )
    a_docs = {p: d for p, (d, _) in arts.items() if "/agency/" in p}
    sig_doc = a_docs["web/entity/agency/acme-surveillance-llc--4g2wm8q/index.sig_graph.json"]
    osm_doc = a_docs["web/entity/agency/acme-surveillance-llc--4g2wm8q/index.osm_odbl.json"]
    assert sig_doc["access"]["closures"]
    (grp,) = sig_doc["access"]["closures"]
    assert grp["direction"] == "outbound"
    assert grp["paths"][0]["target"] == c
    assert osm_doc["access"]["closures"] == []
    # the inbound closure rides the far entity's twin the same way.
    c_docs = [
        d
        for _p, (d, _c) in arts.items()
        if "/index." in _p and isinstance(d, dict) and d.get("entity_id") == c
    ]
    assert c_docs and all(d["access"]["closures"][0]["direction"] == "inbound" for d in c_docs)


# ---------------------------------------------------------------------------
# Contract B (GX-05b / P37.22): kinds, timeline, contradictions, related,
# downloads — the §4.2 rows 8/9/11/12 the twin carries first-class.
# ---------------------------------------------------------------------------

from exports.entity_page import (  # noqa: E402
    contradiction_records,
    download_entries,
    related_pages,
    relationships_csv,
    timeline_entries,
)


def test_page_state_published_for_contract_b_kinds():
    for kind in ("notice", "contract", "grant", "bill", "policy", "event"):
        lbl = _label(_eid(), kind=kind, url_type=kind)
        assert page_state(lbl) == PAGE_STATE_PUBLISHED
    # request/atlas/site stay outside the 05b row — typed unpaged.
    for kind in ("request", "atlas", "site"):
        assert page_state(_label(_eid(), kind=kind)) == PAGE_STATE_UNPAGED


def test_timeline_entries_stated_observed_sightings_and_undated():
    eid = _eid()
    rows = [
        _claim_row(eid, "posted_date", "2020-01-28", "c9"),
        _claim_row(eid, "agency_name", "Acme PD", "c1", obs=None),
    ]
    by_subj = page_claims(rows)
    groups = claim_groups(
        eid,
        by_subj[eid],
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF"},
        claim_sources={"c9": {"src_a"}},
        as_of=None,
    )
    entries = timeline_entries(
        eid,
        by_subj[eid],
        claim_groups=groups,
        relation_groups=[],
        degree_facts=[],
        sightings=[
            {
                "claim_id": "c9",
                "subject_id": eid,
                "source_id": "src_a",
                "first_seen": "2020-01-29",
                "last_seen": "2021-02-03",
            }
        ],
        claim_sources={"c9": {"src_a"}},
        source_names={"src_a": "EFF Data Driven"},
    )
    kinds = {e["kind"] for e in entries}
    assert {"stated", "observed", "first_seen", "last_seen"} <= kinds
    stated = [e for e in entries if e["kind"] == "stated"]
    assert stated[0]["date"] == "2020-01-28" and stated[0]["label"] == "posted date"
    first = [e for e in entries if e["kind"] == "first_seen"][0]
    assert first["label"] == "first seen — EFF Data Driven"
    # the undated claim group is listed apart, never placed on the axis.
    undated = [e for e in entries if e["date_kind"] == "undated"]
    assert undated and all(e["date"] is None for e in undated)
    dated = [e for e in entries if e["date"]]
    assert [e["date"] for e in dated] == sorted(e["date"] for e in dated)


def test_contradiction_records_subject_overlap_and_envelope():
    eid, other = _eid(), _eid()
    rows = [_claim_row(eid, "agency_name", "Acme PD", "c1")]
    by_subj = page_claims(rows)
    groups = [
        {
            "predicate": "agency_name",
            "relation": "agency name",
            "envelope": {
                "status": "unresolved_conflict",
                "support": "STRONGLY_SUPPORTED",
                "agreement": "unresolved_conflict",
                "currency": "CURRENT",
                "rationale": None,
            },
            "claim_ids": ["c1", "c2"],
            "sources": [{"id": "src_a", "name": "EFF"}],
        }
    ]
    contra = [
        {
            "contradiction_id": "contra-1",
            "subject_id": other,
            "predicate_id": "camera_latitude",
            "contradiction_type": "coordinate",
            "status": "open",
            "severity": "low",
            "claim_ids": ["c1", "c9"],
        },
        {
            "contradiction_id": "contra-2",
            "subject_id": _eid(),
            "predicate_id": "other_pred",
            "contradiction_type": "value",
            "status": "open",
            "severity": "low",
            "claim_ids": ["cz"],
        },
    ]
    recs = contradiction_records(
        eid,
        [*by_subj[eid]],
        contradiction_rows=contra,
        claim_groups=groups,
        claim_sources={"c1": {"src_a"}, "c9": {"src_b"}, "cz": {"src_z"}},
        source_names={"src_a": "EFF", "src_b": "Other", "src_z": "Zed"},
    )
    # the claim-overlap row lands; the unrelated subject's row never does.
    ids = {r["contradiction_id"] for r in recs}
    assert "contra-1" in ids and "contra-2" not in ids
    env = [r for r in recs if r["kind"] == "envelope_conflict"]
    assert (
        env and env[0]["predicate"] == "agency_name" and env[0]["status"] == "unresolved_conflict"
    )


def test_related_pages_dossier_source_task_document():
    eid = _eid()
    lbl = _label(eid, "contract", url_type="contract", place_jkey="usa-ok")
    rows = [_claim_row(eid, "posted_date", "2020-01-28", "c1")]
    by_subj = page_claims(rows)
    rel = related_pages(
        lbl,
        by_subj[eid],
        dossier_index={"usa-ok": {"slug_path": "usa/ok", "name": "Oklahoma", "level": "admin1"}},
        task_index={
            eid: [
                {
                    "task_id": "t1",
                    "handle": "T-usa-ok-verify-q1c4",
                    "title": "Verify the award",
                    "task_type": "verify",
                    "status": "generated",
                }
            ]
        },
        claim_documents={"c1": {"art-1"}},
        doc_index={
            "art-1": {
                "title": "The notice PDF",
                "artifact_type": "document",
                "source_id": "src_a",
                "source_name": "EFF",
            }
        },
        claim_sources={"c1": {"src_a"}},
        source_names={"src_a": "EFF"},
    )
    assert rel["dossiers"][0]["url"] == "/dossier/usa/ok/"
    assert rel["sources"] == [{"id": "src_a", "name": "EFF", "url": "/sources/src_a/"}]
    assert rel["tasks"][0]["url"] == "/task/T-usa-ok-verify-q1c4/"
    assert rel["documents"][0]["artifact_id"] == "art-1"
    assert rel["watch"] == []


def test_download_artifacts_emit_twin_relationships_csv_and_statements():
    eid, partner = _eid(), _eid()
    labels = {
        eid: _label(eid, "contract", url_type="contract"),
        partner: _label(partner, "org", label="Acme LLC"),
    }
    rows = [
        _claim_row(eid, "posted_date", "2020-01-28", "c1"),
        _claim_row(eid, "seller", None, "c2", obj=partner),
    ]
    arts = entity_page_artifacts(
        labels,
        claim_rows=rows,
        edge_rows=[],
        identifiers={},
        entity_types={eid: "contract"},
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF"},
        entity_comps={eid: {"sig_graph"}},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=None,
        retrieval=date(2026, 9, 22),
        statement_rows={
            "sig_graph": [{"schema": "sig.statement/1", "entity_id": eid, "claim_id": "c1"}]
        },
    )
    base = "web/entity/contract/acme-surveillance-llc--4g2wm8q"
    assert f"{base}/index.sig_graph.json" in arts
    rel_json, _ = arts[f"{base}/relationships.sig_graph.json"]
    assert rel_json["schema"] == "sig.entity-relationships/1"
    csv_bytes, _ = arts[f"{base}/relationships.sig_graph.csv"]
    text = csv_bytes.decode("utf-8")
    assert text.splitlines()[0].startswith("relation,direction")
    assert "Acme LLC" in text
    stmt_bytes, _ = arts[f"{base}/statements.sig_graph.jsonl"]
    assert b'"entity_id"' in stmt_bytes and eid.encode() in stmt_bytes
    doc, _ = arts[f"{base}/index.sig_graph.json"]
    paths = {d["path"] for d in doc["downloads"]}
    assert "entity/contract/acme-surveillance-llc--4g2wm8q/statements.sig_graph.jsonl" in paths
    # populated contract-B slots — the record is never typed-empty here.
    assert doc["timeline"] and doc["related"]["sources"]


def test_contract_b_sections_file_per_compartment():
    eid = _eid()
    labels = {eid: _label(eid, "contract", url_type="contract")}
    rows = [
        _claim_row(eid, "posted_date", "2020-01-28", "c1"),
        _claim_row(eid, "award_date", "2020-02-01", "c2", rid="rights-odbl", spdx="ODbL-1.0"),
    ]
    arts = entity_page_artifacts(
        labels,
        claim_rows=rows,
        edge_rows=[],
        identifiers={},
        entity_types={eid: "contract"},
        resolutions={},
        lineage={},
        source_names={"src_a": "EFF"},
        entity_comps={eid: {"sig_graph"}},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=None,
        retrieval=date(2026, 9, 22),
    )
    sig_doc, _ = arts["web/entity/contract/acme-surveillance-llc--4g2wm8q/index.sig_graph.json"]
    odbl_doc, _ = arts["web/entity/contract/acme-surveillance-llc--4g2wm8q/index.osm_physical.json"]
    sig_dates = {(e["kind"], e["date"]) for e in sig_doc["timeline"] if e["kind"] == "stated"}
    odbl_dates = {(e["kind"], e["date"]) for e in odbl_doc["timeline"] if e["kind"] == "stated"}
    assert sig_dates == {("stated", "2020-01-28")}
    assert odbl_dates == {("stated", "2020-02-01")}


def test_relationships_csv_deterministic_shape():
    eid, partner = _eid(), _eid()
    labels = {partner: _label(partner, "org", label="Acme LLC")}
    rows = [_claim_row(eid, "seller", None, "c1", obj=partner)]
    by_subj = page_claims(rows)
    groups, _ = relation_groups(eid, by_subj[eid], edge_rows=[], labels=labels, **_ctx())
    a = relationships_csv(groups)
    assert a == relationships_csv(groups)
    lines = a.decode().splitlines()
    assert lines[0].split(",")[:3] == ["relation", "direction", "access_kind"]
    assert lines[1].startswith("seller,outbound,")


def test_download_entries_lists_only_emitted_files():
    entries = download_entries("contract", "k--h", "sig_graph", has_statements=False)
    kinds = {(e["kind"], e["format"]) for e in entries}
    assert ("statements", "jsonl") not in kinds
    assert ("twin", "json") in kinds and ("relationships", "csv") in kinds
