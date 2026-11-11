# SPDX-License-Identifier: Apache-2.0
"""P37.28 (K6 VIZ-01b, SIG-UI-125): the per-dossier network-figure emission —
anchors via K4 placement chains, counterparties, the declared grouping
fields, the H-2 edge fields, typed absences and the K5 fig-* breakdowns."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from exports.graph_overview import PlaceInfo
from policy.labels import EntityLabel

from exports import dossier_networks as dn


def _lbl(
    eid: str,
    *,
    kind: str = "agency",
    place: str | None = None,
    label: str | None = None,
    url: str | None = None,
    state: str | None = None,
) -> EntityLabel:
    return EntityLabel(
        entity_id=eid,
        sig_id=None,
        kind=kind,
        url_type=kind if url else None,
        label=label or eid,
        descriptor=None,
        label_basis="source_name",
        label_source_id=None,
        place_jkey=place,
        slug=None,
        hash=None,
        url=url,
        disambiguator=None,
        component_id=None,
        part8="pass",
        label_state=state,
    )


def _row(sid, pred, value=None, cid="c1", obj=None, obs="2024-01-15", src="src-1"):
    return (sid, pred, value, cid, obj, obs, src, "CC0-1.0", "", "yes", "yes", "", f"r-{cid}")


PLACES = {
    "usa": PlaceInfo("United States", "usa", "country"),
    "usa-ok": PlaceInfo("Oklahoma", "usa/ok", "state_province"),
    "usa-ok-40109": PlaceInfo("Oklahoma County", "usa/ok/oklahoma-county-40109", "county"),
}
ANCESTORS = {
    "usa": ("usa",),
    "usa-ok": ("usa", "usa-ok"),
    "usa-ok-40109": ("usa", "usa-ok", "usa-ok-40109"),
}
PAGES = frozenset(PLACES)


def _info(jkey: str):
    p = PLACES[jkey]
    return SimpleNamespace(jkey=jkey, name=p.name, slug_path=p.slug_path, level=p.level)


def _slug_of(jkey: str) -> str:
    return PLACES[jkey].slug_path


RELEASE = {"label": "fixture", "publication_id": None, "as_of_world": "2026-09-20"}


def _entries(jkey, labels, rows, **kw):
    prepared = dn.prepare(
        labels,
        claim_rows=rows,
        value_claims=kw.pop("value_claims", ()),
        relevance=kw.pop("relevance", {"n-1": "surveillance_related"}),
        relevance_fields=kw.pop("relevance_fields", {}),
        places=PLACES,
    )
    return dn.entries_for(
        jkey,
        _info(jkey),
        prepared,
        labels=labels,
        ancestors=ANCESTORS,
        places=PLACES,
        pages=PAGES,
        slug_of=_slug_of,
        lineage={},
        as_of=date(2026, 9, 20),
        source_names={"src-1": "Fixture Source"},
        release=RELEASE,
    )


def _by_id(entries):
    return {e["figure_id"]: e for e in entries}


def test_supply_edges_anchor_by_place_chain() -> None:
    labels = {
        "n-1": _lbl("n-1", kind="notice", place="usa-ok-40109"),
        "buy-1": _lbl("buy-1", place="usa-ok-40109", url="/entity/agency/buyer--abc1234/"),
        "vend-1": _lbl("vend-1", kind="org", url="/entity/org/vendor--def5678/"),
    }
    rows = [
        _row("n-1", "buyer", cid="c1", obj="buy-1"),
        _row("n-1", "vendor", cid="c2", obj="vend-1"),
    ]
    out = _by_id(_entries("usa-ok-40109", labels, rows))
    fig = out["fig-supply"]
    assert fig["status"] == "drawn"
    assert "bought from" in fig["svg"] or "sig-fig-edge" in fig["svg"]
    assert fig["anchors_drawn"] == 1
    # One edge backed by src-1's claims — the by_source leg counts edges.
    assert fig["by_source"] == [{"source_id": "src-1", "value": 1}]
    row = fig["meta"]["table_rows"][0]
    assert row["relation"] == "bought from"
    assert row["date"] == "2024-01-15"
    assert row["evidence"]
    # The same edge anchors the parent state dossier (chain membership).
    state = _by_id(_entries("usa-ok", labels, rows))["fig-supply"]
    assert state["status"] == "drawn"


def test_relevance_gate_keeps_non_surveillance_notices_out() -> None:
    labels = {
        "n-1": _lbl("n-1", kind="notice", place="usa-ok-40109"),
        "buy-1": _lbl("buy-1", place="usa-ok-40109", url="/entity/agency/b--a1/"),
        "vend-1": _lbl("vend-1", kind="org", url="/entity/org/v--b2/"),
    }
    rows = [
        _row("n-1", "buyer", cid="c1", obj="buy-1"),
        _row("n-1", "vendor", cid="c2", obj="vend-1"),
    ]
    out = _by_id(_entries("usa-ok-40109", labels, rows, relevance={"n-1": "not_surveillance"}))
    # The gate drops the whole party pair — no anchored nodes remain.
    assert out["fig-supply"]["status"] == "no_anchors"


def test_funding_recipient_anchors() -> None:
    labels = {
        "g-1": _lbl("g-1", kind="grant"),
        "funder": _lbl("funder", kind="org", url="/entity/org/f--a1/"),
        "recip": _lbl("recip", place="usa-ok", url="/entity/agency/r--b2/"),
    }
    rows = [
        _row("g-1", "funder", cid="c1", obj="funder"),
        _row("g-1", "recipient", cid="c2", obj="recip"),
    ]
    out = _by_id(_entries("usa-ok", labels, rows))
    fig = out["fig-funding"]
    assert fig["status"] == "drawn"
    row = fig["meta"]["table_rows"][0]
    assert row["relation"] == "funded by"
    assert row["direction"] == "inbound"


def test_access_edges_carry_kinds_and_degree_facts() -> None:
    labels = {
        "ag-1": _lbl("ag-1", place="usa-ok", url="/entity/agency/a--a1/"),
        "part-1": _lbl("part-1", kind="org", url="/entity/org/p--b2/"),
    }
    rows = [
        _row("ag-1", "configured_sharing_partner", cid="c1", obj="part-1"),
        _row("ag-1", "sharing_partner_degree", value="9", cid="c3"),
    ]
    fig = _by_id(_entries("usa-ok", labels, rows))["fig-access"]
    assert fig["status"] == "drawn"
    assert fig["toggle_kinds"] == ["configured"]
    assert fig["meta"]["table_rows"][0]["access_kind"] == "configured"
    assert fig["degree_facts"][0]["count"] == 9


def test_policy_instrument_anchors_via_jurisdiction_edge() -> None:
    labels = {
        "bill-1": _lbl("bill-1", kind="bill", url="/entity/policy/b--a1/"),
        "place-e": _lbl("place-e", kind="jurisdiction", place="usa-ok"),
        "body-1": _lbl("body-1", kind="agency", url="/entity/agency/c--d1/"),
    }
    rows = [
        _row("bill-1", "bill_jurisdiction", cid="c1", obj="place-e"),
        _row("bill-1", "enacting_body", cid="c2", obj="body-1"),
        _row("bill-1", "constrains_technology", value="alpr", cid="c3"),
    ]
    fig = _by_id(_entries("usa-ok", labels, rows))["fig-policy"]
    assert fig["status"] == "drawn"
    rels = {r["relation"] for r in fig["meta"]["table_rows"]}
    assert "enacts" in rels
    # 'in jurisdiction' marks placement only — never a counterparty row.
    assert "in jurisdiction" not in rels


def test_country_draws_no_node_link_figure() -> None:
    out = _by_id(_entries("usa", {}, []))
    assert all(e["status"] == "country_no_figure" for e in out.values())


def test_empty_states_are_typed() -> None:
    labels = {"ag-1": _lbl("ag-1", place="usa-ok", url="/entity/agency/a--a1/")}
    out = _by_id(_entries("usa-ok", labels, []))
    assert out["fig-access"]["status"] == "no_anchors"
    assert "reason" in out["fig-access"]


def test_withheld_and_review_pending_never_draw() -> None:
    labels = {
        "n-1": _lbl("n-1", kind="notice", place="usa-ok-40109"),
        "buy-1": _lbl("buy-1", place="usa-ok-40109", state="withheld"),
        "vend-1": _lbl("vend-1", kind="org", url="/entity/org/v--b2/", state="not_yet_reviewed"),
    }
    rows = [
        _row("n-1", "buyer", cid="c1", obj="buy-1"),
        _row("n-1", "vendor", cid="c2", obj="vend-1"),
    ]
    out = _by_id(_entries("usa-ok-40109", labels, rows))
    # Withheld/review-pending endpoints drop the whole edge; the published
    # notice subject itself is still an anchored node → no evidenced edges.
    assert out["fig-supply"]["status"] == "no_evidenced_edges"


def test_grouping_fields_declared_on_every_node() -> None:
    labels = {
        "n-1": _lbl("n-1", kind="notice", place="usa-ok-40109"),
        "buy-1": _lbl("buy-1", place="usa-ok-40109", url="/entity/agency/b--a1/"),
        "vend-1": _lbl("vend-1", kind="org", url="/entity/org/v--b2/"),
    }
    rows = [
        _row("n-1", "buyer", cid="c1", obj="buy-1"),
        _row("n-1", "vendor", cid="c2", obj="vend-1"),
    ]
    fig = _by_id(_entries("usa-ok-40109", labels, rows))["fig-supply"]
    # Every drawn node links — the fixture's grouped fallback fields are
    # declared in the spec the kit consumed (never silently pruned).
    assert '<a href="/entity/agency/b--a1/"' in fig["svg"]
    assert fig["table_href"].startswith("/graphs/supply/")
    assert fig["explore_href"].startswith("/explore/?v=2&overview=supply&jurisdiction=")


def test_figures_k5_rows_shape() -> None:
    entries = _entries(
        "usa-ok",
        {"ag-1": _lbl("ag-1", place="usa-ok", url="/entity/agency/a--a1/")},
        [],
    )
    rows = dn.figures_k5_rows(entries)
    assert [r["figure_id"] for r in rows] == [
        "fig-supply",
        "fig-funding",
        "fig-access",
        "fig-policy",
    ]
    assert all("by_source" in r and "edges" in r for r in rows)
