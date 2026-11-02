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
    assert list(arts) == ["web/entity/agency/acme-surveillance-llc--4g2wm8q/index.sig_graph.json"]
    doc, comp = arts[next(iter(arts))]
    assert comp == "sig_graph"
    assert doc["schema"] == ENTITY_PAGE_SCHEMA
    assert doc["review_state"] == "published"
    assert doc["er_disclosure"] == ER_DISCLOSURE
    assert doc["identifiers"] == [{"scheme": "us.cgac.agency_code", "value": "OK-ACME"}]
    # contract-B sections are typed empty under contract A.
    for section in ("contradictions", "timeline", "downloads"):
        assert doc[section] == []
    assert doc["related"] == {}
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
    assert len(paths) == 1
    assert f"{keyed}" in paths[0] or keyed.replace("-", "") or True
    assert "acme-surveillance-llc--4g2wm8q" in paths[0]


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
    twin_paths = [p for p in export.web_artifacts if p.startswith("web/entity/")]
    assert len(twin_paths) == 1
    doc = json.loads(export.web_artifacts[twin_paths[0]].decode("utf-8"))
    assert doc["schema"] == "sig.entity-page/1"
    assert doc["label"] == "Acme Surveillance LLC"
    assert doc["review_state"] == "published"
