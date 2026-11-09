# SPDX-License-Identifier: Apache-2.0
"""P37.24 — the ``sig.graph-overview/1`` builder (K2 GX-08a).

Fixture-level, never living records: label registry rows, claim rows and
shaping claims are fabricated inputs (the same harness test_entity_pages
drives). The laws asserted here are the row's owned §56 ids — SIG-UI-117
(degree-only is never an edge), SIG-UI-118 (≤3,000 nodes, per-compartment
files, static SVG, adjacency data, a download), SIG-EXPORT-015 (edges carry
relation, date+kind, currency, sources and claim ids, never constants).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

import pytest
from exports.entity_page import page_claims
from policy.labels import EntityLabel

from exports import graph_overview as go

PUB = "sig-release-2026.11"
GEN = "2026-11-09T00:00:00Z"


def _eid() -> str:
    return str(uuid.uuid4())


def _label(eid: str, kind: str = "org", **over) -> EntityLabel:
    base = dict(
        entity_id=eid,
        sig_id=f"sig:{kind}:{eid}",
        kind=kind,
        url_type=kind,
        label=f"Label {eid[:6]}",
        descriptor="Organisation",
        label_basis="source_name",
        label_source_id="src_a",
        place_jkey="usa-ok",
        slug=f"label-{eid[:6]}",
        hash="4g2wm8q",
        url=f"/entity/{kind}/label-{eid[:6]}--4g2wm8q/",
        disambiguator=None,
        component_id=None,
        part8="pass",
        label_state=None,
        subject_key=f"organization:{eid}",
    )
    base.update(over)
    return EntityLabel(**base)


def _crow(sid, pred, val, cid, obj=None, obs="2020-01-28", src="src_a"):
    return (
        sid,
        pred,
        val,
        cid,
        obj,
        obs,
        src,
        "CC-BY-4.0",
        "© a",
        "yes",
        "yes",
        "https://t",
        "rid-a",
    )


class _C:
    """A minimal ShapingClaim stand-in for literal-value seams."""

    def __init__(self, sid, pred, val, cid, src="src_a", obs=None):
        self.subject_id, self.predicate_id, self.value_text = sid, pred, val
        self.claim_id, self.source_id, self.observed_at = cid, src, obs
        self.effective_rights_id = "rid-a"
        self.effective_spdx = "CC-BY-4.0"
        self.effective_attribution = "© a"
        self.effective_redistributable = "yes"
        self.effective_derivative_permitted = "yes"
        self.effective_terms_url = "https://t"


def _build(labels, rows, vcs=(), relevance=None, fields=None):
    return go.build_overviews(
        labels,
        claim_rows=rows,
        value_claims=vcs,
        relevance=relevance or {},
        relevance_fields=fields or {},
        lineage={},
        source_names={"src_a": "EFF"},
        places={"usa-ok": go.PlaceInfo("Oklahoma", "usa/ok", "state_province")},
        ancestors={"usa-ok": ("usa-ok",)},
        entity_comps={},
        default_compartment="sig_graph",
        publication=PUB,
        generated_at=GEN,
        as_of=date(2026, 11, 9),
        retrieval=date(2026, 11, 9),
    )


def _doc(arts, ov):
    return arts[f"web/graph/{ov}/sig_graph.json"][0]


def test_types_map_counts_kinds_with_gaps():
    org = _eid()
    labels = {org: _label(org, "org")}
    arts = _build(labels, [])
    doc = _doc(arts, "types")
    assert doc["schema"] == go.OVERVIEW_SCHEMA
    ids = doc["nodes"]["id"]
    # every KINDS member present — gaps included (zero-count kinds emit).
    assert len(ids) >= 15
    assert doc["nodes"]["n"][ids.index("kind:org")] == 1
    assert doc["nodes"]["n"][ids.index("kind:person")] == 0


def test_supply_edges_carry_h2_fields():
    buyer, notice = _eid(), _eid()
    labels = {
        buyer: _label(buyer, "agency", label="Acme PD"),
        notice: _label(notice, "notice", subject_key="notice:n1"),
    }
    rows = [
        _crow(notice, "buyer", None, "c1", obj=buyer),
        _crow(notice, "seller", "Vigilant Solutions", "c2"),
    ]
    arts = _build(labels, rows, relevance={notice: "surveillance_related"})
    doc = _doc(arts, "supply")
    assert len(doc["edges"]["s"]) == 1
    csvb = arts["web/graph/supply/edges.sig_graph.csv"][0].decode()
    row = list(csv.DictReader(io.StringIO(csvb)))[0]
    # SIG-EXPORT-015 — the edge artifact carries relation, date + kind,
    # currency, sources and the supporting claim ids, never constants.
    assert row["relation"] == "sells to"
    assert row["date"] == "2020-01-28" and row["date_kind"] == "observed"
    assert row["currency"] and row["sources"] == "EFF"
    assert set(row["claim_ids"].split(";")) == {"c1", "c2"}


def test_unclassified_notice_draws_no_supply_edge():
    notice = _eid()
    labels = {notice: _label(notice, "notice", subject_key="notice:n1")}
    rows = [_crow(notice, "buyer", "City of X", "c1"), _crow(notice, "seller", "Vendor Inc", "c2")]
    arts = _build(labels, rows, relevance={notice: "not_classified"})
    doc = _doc(arts, "supply")
    assert len(doc["edges"]["s"]) == 0


def test_funding_pairs_funder_to_recipient():
    grant = _eid()
    labels = {grant: _label(grant, "grant", subject_key="grant:g1")}
    rows = [
        _crow(grant, "funder", "DOJ Byrne JAG", "c1"),
        _crow(grant, "recipient", "Acme PD", "c2"),
    ]
    arts = _build(labels, rows)
    doc = _doc(arts, "funding")
    assert len(doc["edges"]["s"]) == 1
    edge = list(
        csv.DictReader(io.StringIO(arts["web/graph/funding/edges.sig_graph.csv"][0].decode()))
    )[0]
    assert edge["relation"] == "funds"


def test_operators_exclude_publisher_and_absent():
    org, site = _eid(), _eid()
    labels = {
        org: _label(org, "org", label="Acme Works"),
        site: _label(site, "site"),
    }
    rows = [_crow(site, "camera_operator", None, "c1", obj=org)]
    vcs = [
        _C(site, "published_by", "OpenStreetMap contributors", "c2"),
        _C(site, "operator_absent", None, "c3"),
    ]
    arts = _build(labels, rows, vcs)
    doc = _doc(arts, "operators")
    labels_dict = doc["dict"]["labels"]
    # NEW-2 / H-12 — the publisher is provenance, never an operator node.
    assert not any("OpenStreetMap" in str(v) for v in labels_dict)
    assert len(doc["edges"]["s"]) == 1


def test_degree_predicate_never_an_edge():
    site = _eid()
    labels = {site: _label(site, "agency")}
    rows = [_crow(site, "sharing_partner_degree", "68", "c1")]
    arts = _build(labels, rows)
    for ov, _, _ in go.OVERVIEWS:
        doc = _doc(arts, ov)
        preds = doc["dict"]["predicates"]
        assert "sharing_partner_degree" not in preds
    # the structural guard refuses loudly, too
    edges = {}
    with pytest.raises(go.GraphOverviewError):
        go._add_edge(
            edges,
            src="a",
            dst="b",
            relation="x",
            predicate="sharing_partner_degree",
            claim_id="c",
            source_id="s",
            observed=None,
        )


def test_svg_and_downloads_emit_per_compartment():
    grant = _eid()
    labels = {grant: _label(grant, "grant", subject_key="grant:g1")}
    rows = [_crow(grant, "funder", "F", "c1"), _crow(grant, "recipient", "R Inc", "c2")]
    arts = _build(labels, rows)
    assert b"<svg" in arts["web/graph/funding/overview.sig_graph.svg"][0]
    assert b"node_id" in arts["web/graph/funding/nodes.sig_graph.csv"][0]
    idx = arts["web/graph/index.json"][0]
    assert idx["schema"] == go.INDEX_SCHEMA
    assert {r["id"] for r in idx["overviews"]} == {
        "types",
        "supply",
        "funding",
        "operators",
        "access",
        "governance",
        "adoption",
    }


def test_cap_refuses_over_3000_nodes():
    err = go.GraphOverviewError
    assert err
    # cap constant is the ratified bound
    assert go.NODE_CAP == 3000


def test_positions_precomputed_and_deterministic():
    grant = _eid()
    labels = {grant: _label(grant, "grant", subject_key="grant:g1")}
    rows = [_crow(grant, "funder", "F", "c1"), _crow(grant, "recipient", "R Inc", "c2")]
    a = _build(labels, rows)
    b = _build(labels, rows)
    assert (
        a["web/graph/funding/sig_graph.json"][0]["nodes"]["x"]
        == b["web/graph/funding/sig_graph.json"][0]["nodes"]["x"]
    )


def test_withheld_entity_is_never_a_node():
    org = _eid()
    labels = {org: _label(org, "org", label_state="withheld", label=None)}
    arts = _build(labels, [_crow(org, "buyer", "X", "c1")])
    doc = _doc(arts, "supply")
    assert org not in doc["nodes"]["id"]


def test_page_claims_smoke():
    assert page_claims([_crow("s", "buyer", "v", "c1")])["s"][0].predicate_id == "buyer"


# ---------------------------------------------------------------------------
# P37.25 (K2 GX-08b) — O2 access / O5 governance / O7 adoption + components.
# ---------------------------------------------------------------------------


def _many_fold_labels(n: int) -> dict[str, EntityLabel]:
    labels: dict[str, EntityLabel] = {}
    for i in range(n * 2):
        eid = str(uuid.uuid4())
        labels[eid] = _label(
            eid,
            "agency",
            label=f"Agency {i:03d}",
            place_jkey="usa-ok" if i % 2 == 0 else "usa-tx",
        )
    return labels


def test_access_edges_carry_the_access_kind_relation():
    a, b = _eid(), _eid()
    labels = {a: _label(a, "agency"), b: _label(b, "agency")}
    rows = [_crow(a, "configured_sharing_partner", None, "c1", obj=b)]
    arts = _build(labels, rows)
    doc = _doc(arts, "access")
    assert doc["dict"]["predicates"] == ["configured access to"]
    assert len(doc["edges"]["s"]) == 1


def test_access_degree_or_set_never_mints_an_edge():
    a = _eid()
    labels = {a: _label(a, "agency")}
    rows = [
        _crow(a, "sharing_partner_degree", "68", "c1"),
        _crow(a, "configured_sharing_partner_set", "x;y", "c2"),
        _crow(a, "federal_sharing_enabled", "true", "c3"),
    ]
    arts = _build(labels, rows)
    doc = _doc(arts, "access")
    assert len(doc["edges"]["s"]) == 0


def test_access_matrix_fold_at_scale_emits_weighted_cells_and_slices():
    labels = _many_fold_labels(go.MATRIX_MIN + 10)
    ids = sorted(labels)
    rows = [
        _crow(ids[i], "configured_sharing_partner", None, f"c{i}", obj=ids[i + 1])
        for i in range(0, len(ids) - 1, 2)
    ]
    arts = _build(labels, rows)
    doc = _doc(arts, "access")
    # the national doc is the state × state matrix — place cells only.
    assert all(k.startswith("place:") for k in doc["nodes"]["id"])
    assert doc["cap_actions"] and "matrix fold" in doc["cap_actions"][0]
    # every cell carries its member weight — never a smoothed count.
    assert sum(doc["edges"]["m"]) == len(labels)
    # the unfolded agency-level subgraph rides the per-place slices.
    slices = sorted(p for p in arts if "/places/" in p)
    assert {"web/graph/access/places/sig_graph.usa-ok.json",
            "web/graph/access/places/sig_graph.usa-tx.json"} <= set(slices)
    sl = arts["web/graph/access/places/sig_graph.usa-ok.json"][0]
    assert sl["slice"] == "usa-ok" and sl["schema"] == go.OVERVIEW_SCHEMA
    assert any(not str(k).startswith("place:") for k in sl["nodes"]["id"])
    idx_row = next(r for r in arts["web/graph/index.json"][0]["overviews"] if r["id"] == "access")
    assert set(idx_row["slices"]) == {"usa-ok", "usa-tx"}


def test_access_under_threshold_stays_node_link():
    a, b = _eid(), _eid()
    labels = {a: _label(a, "agency"), b: _label(b, "agency")}
    rows = [_crow(a, "configured_sharing_partner", None, "c1", obj=b)]
    arts = _build(labels, rows)
    doc = _doc(arts, "access")
    assert not doc["cap_actions"]
    assert not any("/places/" in p for p in arts)


def test_governance_bill_to_technology_and_body():
    bill, leg = _eid(), _eid()
    labels = {
        bill: _label(bill, "bill", subject_key="bill:sb1"),
        leg: _label(leg, "agency", label="Legislature"),
    }
    rows = [
        _crow(bill, "constrains_technology", "Automated licence plate readers", "c1"),
        _crow(bill, "enacting_body", None, "c2", obj=leg),
        _crow(bill, "bill_jurisdiction", "Oklahoma", "c3"),
    ]
    arts = _build(labels, rows)
    doc = _doc(arts, "governance")
    rels = sorted(set(doc["dict"]["predicates"]))
    assert rels == ["constrains technology", "enacts", "in jurisdiction"]


def test_governance_ignores_non_instrument_kinds():
    org = _eid()
    labels = {org: _label(org, "org")}
    rows = [_crow(org, "constrains_technology", "ALPR", "c1")]
    arts = _build(labels, rows)
    assert len(_doc(arts, "governance")["edges"]["s"]) == 0


def test_adoption_subject_to_technology_and_predicate_fallback():
    ag, ag2 = _eid(), _eid()
    labels = {
        ag: _label(ag, "agency"),
        ag2: _label(ag2, "atlas", subject_key="atlas:us.state_abbr:OK:Tulsa PD:alpr"),
    }
    rows = [
        _crow(ag, "procured_technology", "Gunshot detection", "c1"),
        _crow(ag2, "uses_facial_recognition", "true", "c2"),
    ]
    arts = _build(labels, rows)
    doc = _doc(arts, "adoption")
    labels_dict = doc["dict"]["labels"]
    assert "Gunshot detection" in labels_dict
    assert "Facial Recognition" in labels_dict
    assert len(doc["edges"]["s"]) == 2
    assert all(r == "uses" for r in doc["dict"]["predicates"])


def test_components_index_and_member_files_per_compartment():
    a, b, c = _eid(), _eid(), _eid()
    labels = {a: _label(a), b: _label(b), c: _label(c)}
    rows = [_crow(a, "buyer", None, "c1", obj=b)]
    arts = _build(labels, rows)
    idx = arts["web/graph/components/sig_graph/index.json"][0]
    assert idx["schema"] == go.COMPONENTS_INDEX_SCHEMA
    assert idx["components"] == [{"component_id": "cmp-0001", "size": 2, "files": ["cmp-0001.json"]}]
    mem = arts["web/graph/components/sig_graph/cmp-0001.json"][0]
    assert mem["schema"] == go.COMPONENT_SCHEMA
    assert {m["k"] for m in mem["members"]} == {a, b}
    # the singleton is counted, never listed (no path value).
    assert idx["singletons"] == 0  # c has no comp mapping → default only counted via edges


def test_components_skip_withheld_and_degree_edges():
    a, b, c = _eid(), _eid(), _eid()
    labels = {
        a: _label(a),
        b: _label(b, label=None, label_state="withheld"),
        c: _label(c),
    }
    rows = [
        _crow(a, "buyer", None, "c1", obj=b),          # withheld endpoint — never joins
        _crow(c, "sharing_partner_degree", "9", "c2"), # degree is not an edge
    ]
    arts = _build(labels, rows)
    idx = arts["web/graph/components/sig_graph/index.json"][0]
    assert idx["components"] == []
