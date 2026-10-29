# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P36.28 static figure kit — graph/chart/legend half (FIG-01b).

Every acceptance point the ticket names: deterministic bipartite and radial
ego layouts (SIG-UI-125/DV03, K6 §6.2), grouping-not-pruning over the caps,
access-kind line patterns + muted-ink currency + independent no-JS hiding
hooks (K6 §6.3/6.4), the generated lexicon legend listing only present
encodings (K14 §4.7, SIG-UI-061), table twins (H-2 fields verbatim), wide +
narrow variants, bar/stacked-bar/strip/timeline emitters, the licence pin
(no third-party layout dependency), and fail-closed spec loading.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from exports.figures import (
    FigureKitError,
    Lexicon,
    build_chart,
    build_ego_figure,
    build_legend_entries,
    build_network_figure,
    chart_spec_from_dict,
    graph_spec_from_dict,
    load_lexicon,
    standalone_document,
)
from exports.figures.chart import INPUT_SCHEMA_CHART
from exports.figures.graph_model import INPUT_SCHEMA_GRAPH

REPO_ROOT = Path(__file__).resolve().parents[2]

RELEASE = {
    "label": "R11 fixture",
    "publication_id": "pub-fixture",
    "as_of_world": "2026-01-01",
}


def _node(key: str, side: str, **kw: object) -> dict[str, object]:
    d: dict[str, object] = {
        "key": key,
        "label": key.upper().replace("_", " "),
        "kind": "agency" if side == "anchor" else "vendor",
        "side": side,
        "href": f"/entities/{key}/",
    }
    d.update(kw)
    return d


def _edge(source: str, target: str, **kw: object) -> dict[str, object]:
    d: dict[str, object] = {
        "source": source,
        "target": target,
        "relation": "supplies",
        "sources": ["src-a"],
        "claim_ids": [f"clm-{source}-{target}"],
    }
    d.update(kw)
    return d


def _graph_doc(**kw: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema": INPUT_SCHEMA_GRAPH,
        "release": RELEASE,
        "kind": "network",
        "title": "Test network figure",
        "nodes": [
            _node("a1", "anchor"),
            _node("a2", "anchor"),
            _node("v1", "counterparty"),
            _node("v2", "counterparty"),
        ],
        "edges": [
            _edge("a1", "v1", access_kind="configured", date="2024-01-01"),
            _edge(
                "a1",
                "v2",
                access_kind="observed",
                date="2019-05-01",
                currency="historical",
            ),
            _edge("a2", "v1", relation="funds", direction="outbound", contested=True),
        ],
    }
    doc.update(kw)
    return doc


def _ego_doc(**kw: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema": INPUT_SCHEMA_GRAPH,
        "release": RELEASE,
        "kind": "ego",
        "title": "Vendor ego",
        "nodes": [
            _node("c", "centre", kind="vendor"),
            _node("n1", "neighbour", kind="agency"),
            _node("n2", "neighbour", kind="agency"),
            _node("n3", "neighbour", kind="instrument"),
        ],
        "edges": [
            _edge("c", "n1", relation="supplies", access_kind="declared"),
            _edge("c", "n2", relation="supplies", access_kind="observed"),
            _edge("c", "n3", relation="funded-by", currency="historical"),
        ],
    }
    doc.update(kw)
    return doc


def _chart_doc(**kw: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema": INPUT_SCHEMA_CHART,
        "release": RELEASE,
        "kind": "bar",
        "title": "Test chart",
        "unit": "agencies",
        "categories": [
            {"label": "Axon", "values": [10], "href": "/entities/axon/"},
            {"label": "Flock", "values": [8]},
            {"label": "Utility", "values": [14]},
        ],
        "series": ["vendors"],
    }
    doc.update(kw)
    return doc


@pytest.fixture(scope="module")
def lexicon() -> Lexicon:
    return load_lexicon(repo_root=REPO_ROOT)


# --- the bipartite network figure ---------------------------------------------


class TestNetworkFigure:
    def test_emits_wide_and_narrow_svg(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        for svg in (res.svg, res.svg_narrow):
            assert svg.startswith("<svg") and svg.endswith(">\n")
            assert 'role="img"' in svg and "aria-labelledby" in svg
        assert res.viewbox[0] == 720
        assert res.narrow_viewbox[0] == 360
        assert res.viewbox[1] <= 520
        assert res.mode == "bipartite"

    def test_byte_deterministic(self, lexicon: Lexicon) -> None:
        a = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        b = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        assert a.svg == b.svg and a.svg_narrow == b.svg_narrow
        assert a.to_json() == b.to_json()

    def test_every_node_links(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        hrefs = re.findall(r'<a href="([^"]+)"', res.svg)
        assert len(hrefs) == 4
        assert all(h.startswith("/") for h in hrefs)
        # node aria-labels carry the full label (drawn text is truncated)
        assert 'aria-label="A1"' in res.svg

    def test_access_kind_and_currency_classes(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        assert "sig-fig-edge-acc-configured" in res.svg
        assert "sig-fig-edge-acc-observed" in res.svg
        assert "sig-fig-edge-muted" in res.svg  # the historical edge
        # declared must NOT appear — the legend/toggles never claim it
        assert "sig-fig-edge-acc-declared" not in res.svg
        # observed = double line: two offset paths of the same class
        assert res.svg.count("sig-fig-edge-acc-observed") >= 2
        # contested edge gets the ≠ mark (raspberry, one meaning)
        assert "sig-fig-contested" in res.svg

    def test_edges_aria_hidden(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        assert '<g aria-hidden="true">' in res.svg

    def test_no_per_edge_data(self, lexicon: Lexicon) -> None:
        """SIG-UI-134: no data-* attributes, no claim ids inside the SVG."""
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        assert "data-" not in res.svg
        assert "clm-" not in res.svg  # claim ids live in the table twin only

    def test_table_twin_carries_h2_fields(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        assert res.table_columns == (
            "counterparty",
            "relation",
            "direction",
            "access_kind",
            "date",
            "date_kind",
            "currency",
            "support",
            "sources",
            "evidence",
        )
        assert len(res.table_rows) == 3
        by_edge = {(r["counterparty"], r["relation"]): r for r in res.table_rows}
        assert by_edge[("V1", "supplies")]["access_kind"] == "configured"
        assert by_edge[("V1", "funds")]["direction"] == "outbound"
        assert by_edge[("V2", "supplies")]["currency"] == "historical"
        assert by_edge[("V2", "supplies")]["evidence"] == ["clm-a1-v2"]
        # the twin names real counterparties, not drawing details
        assert by_edge[("V1", "supplies")]["href"] == "/entities/v1/"

    def test_legend_lists_only_present(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        ids = {e["id"] for e in res.legend}
        assert "line:configured" in ids
        assert "line:observed" in ids
        assert "line:relation" in ids  # the non-access 'funds' edge
        assert "currency:muted" in ids
        assert "mark:contested" in ids
        assert "line:declared" not in ids  # no declared edge present
        assert "mark:provisional" not in ids
        # kinds present get shape entries
        assert "kind:agency" in ids and "kind:vendor" in ids

    def test_legend_uses_lexicon_words(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        by_id = {e["id"]: e for e in res.legend}
        assert by_id["line:configured"]["label"] == "Set up to share"
        assert by_id["line:observed"]["label"] == "Observed use"
        assert by_id["mark:contested"]["label"] == "Contested"

    def test_grouping_over_cap(self, lexicon: Lexicon) -> None:
        nodes = [_node("v1", "counterparty")]
        edges = []
        for i in range(30):
            key = f"a{i:02d}"
            gkey = "g1" if i < 20 else "g2"
            nodes.append(
                _node(
                    key,
                    "anchor",
                    label=f"Agency {i}",
                    group_key=gkey,
                    group_label=f"County {gkey}",
                    group_href=f"/graphs/n/{gkey}/",
                )
            )
            edges.append(_edge(key, "v1"))
        doc = _graph_doc(nodes=nodes, edges=edges)
        res = build_network_figure(graph_spec_from_dict(doc), lexicon)
        assert res.node_count == 3  # 2 group nodes + v1
        assert "County g1 — 20 agencies" in res.svg
        assert 'href="/graphs/n/g1/"' in res.svg
        assert any("grouped" in a for a in res.cap_actions)
        # the twin still names the real counterparties (per-spec edge rows)
        assert len(res.table_rows) == 30
        assert "County g1" not in {str(r["counterparty"]) for r in res.table_rows}

    def test_over_cap_without_groups_refuses(self, lexicon: Lexicon) -> None:
        nodes = [_node("v1", "counterparty")]
        edges = [_edge(f"a{i:02d}", "v1") for i in range(26)]
        nodes += [_node(f"a{i:02d}", "anchor") for i in range(26)]
        with pytest.raises(FigureKitError, match="group_"):
            build_network_figure(
                graph_spec_from_dict(_graph_doc(nodes=nodes, edges=edges)), lexicon
            )

    def test_still_over_row_cap_after_grouping_refuses(self, lexicon: Lexicon) -> None:
        # 30 anchors grouping into 26 distinct places still exceeds 24 rows —
        # the kit refuses rather than drawing a 26-row column (K6 §6.2).
        nodes = [_node("v1", "counterparty")]
        edges = []
        for i in range(30):
            nodes.append(
                _node(
                    f"a{i:02d}",
                    "anchor",
                    group_key=f"g{i:02d}",
                    group_label=f"Place {i}",
                    group_href=f"/g/{i}/",
                )
            )
            edges.append(_edge(f"a{i:02d}", "v1"))
        with pytest.raises(FigureKitError, match="row caps"):
            build_network_figure(
                graph_spec_from_dict(_graph_doc(nodes=nodes, edges=edges)), lexicon
            )

    def test_grouped_edges_dedupe(self, lexicon: Lexicon) -> None:
        nodes = [_node("v1", "counterparty")]
        edges = []
        for i in range(26):
            nodes.append(
                _node(
                    f"a{i}",
                    "anchor",
                    group_key="g1",
                    group_label="Big County",
                    group_href="/graphs/n/g1/",
                )
            )
            edges.append(_edge(f"a{i}", "v1", access_kind="configured"))
        res = build_network_figure(
            graph_spec_from_dict(_graph_doc(nodes=nodes, edges=edges)), lexicon
        )
        # 26 spec edges collapse to ONE drawn curve (same pair + class)
        assert res.desc["drawn_edges"] == 1
        assert len(res.table_rows) == 26

    def test_narrow_places_anchors_above_counterparties(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        narrow = res.svg_narrow
        # anchors' y positions sit above the counterparty block: check via
        # the label texts' order — first anchor label appears before the
        # first counterparty label in document order AND at smaller y.
        a_y = re.search(r'<a href="/entities/a1/"[^>]*>.*?<text[^>]*y="([\d.]+)"', narrow)
        v_y = re.search(r'<a href="/entities/v1/"[^>]*>.*?<text[^>]*y="([\d.]+)"', narrow)
        assert a_y and v_y and float(a_y.group(1)) < float(v_y.group(1))
        # 20-char label truncation
        long_doc = _graph_doc(
            nodes=[
                _node("a1", "anchor", label="A" * 40),
                _node("v1", "counterparty"),
            ],
            edges=[_edge("a1", "v1")],
        )
        res2 = build_network_figure(graph_spec_from_dict(long_doc), lexicon)
        assert "…" in res2.svg_narrow
        assert "A" * 40 in res2.svg_narrow  # full label lives on aria-label
        drawn = re.findall(r"<text[^>]*>(A+…)<", res2.svg_narrow)
        assert drawn and len(drawn[0]) == 20  # the ≤20-char narrow rule

    def test_fail_closed_specs(self, lexicon: Lexicon) -> None:
        with pytest.raises(FigureKitError, match="schema"):
            graph_spec_from_dict({"schema": "nope"})
        with pytest.raises(FigureKitError, match="href"):
            graph_spec_from_dict(_graph_doc(nodes=[_node("a1", "anchor", href=None)]))
        with pytest.raises(FigureKitError, match="href"):
            graph_spec_from_dict(_graph_doc(nodes=[_node("a1", "anchor", href="https://x/")]))
        with pytest.raises(FigureKitError, match="side"):
            graph_spec_from_dict(_graph_doc(nodes=[_node("a1", "middle")]))
        with pytest.raises(FigureKitError, match="unknown node"):
            graph_spec_from_dict(_graph_doc(edges=[_edge("a1", "ghost")]))
        with pytest.raises(FigureKitError, match="duplicate"):
            graph_spec_from_dict(_graph_doc(nodes=[_node("a1", "anchor"), _node("a1", "anchor")]))
        # same-side edges refuse
        doc = _graph_doc(
            nodes=[_node("a1", "anchor"), _node("a2", "anchor"), _node("v1", "counterparty")],
            edges=[_edge("a1", "a2")],
        )
        with pytest.raises(FigureKitError, match="two anchor"):
            build_network_figure(graph_spec_from_dict(doc), lexicon)
        # undated edge carrying a date refuses
        with pytest.raises(FigureKitError, match="undated"):
            graph_spec_from_dict(
                _graph_doc(edges=[_edge("a1", "v1", date="2024-01-01", date_kind="undated")])
            )
        # bad access kind / currency refuse
        with pytest.raises(FigureKitError, match="access_kind"):
            graph_spec_from_dict(_graph_doc(edges=[_edge("a1", "v1", access_kind="magic")]))
        with pytest.raises(FigureKitError, match="currency"):
            graph_spec_from_dict(_graph_doc(edges=[_edge("a1", "v1", currency="fresh")]))
        # no anchors refuses
        with pytest.raises(FigureKitError, match="anchor"):
            build_network_figure(
                graph_spec_from_dict(_graph_doc(nodes=[_node("v1", "counterparty")], edges=[])),
                lexicon,
            )

    def test_standalone_wraps(self, lexicon: Lexicon) -> None:
        res = build_network_figure(graph_spec_from_dict(_graph_doc()), lexicon)
        doc = standalone_document(res.svg, lexicon)
        assert doc.startswith("<?xml")
        assert "<style>" in doc and "sig-fig-edge" in doc
        assert res.svg_narrow  # narrow wraps too
        standalone_document(res.svg_narrow, lexicon)


# --- the radial ego figure ------------------------------------------------------


class TestEgoFigure:
    def test_emits_sectors_and_links(self, lexicon: Lexicon) -> None:
        res = build_ego_figure(graph_spec_from_dict(_ego_doc()), lexicon)
        assert res.mode == "ego-radial"
        assert res.desc["sectors"] == ["funded-by", "supplies"]
        assert res.viewbox[0] == 720 and res.narrow_viewbox[0] == 360
        for svg in (res.svg, res.svg_narrow):
            assert "sig-fig-ego" in svg
            assert "sig-fig-sector" in svg  # per-relation sector guides
            assert "sig-fig-centre" in svg
            assert len(re.findall(r'<a href="', svg)) == 4
        # sector labels are direct text on the figure
        assert ">funded-by<" in res.svg and ">supplies<" in res.svg

    def test_deterministic(self, lexicon: Lexicon) -> None:
        a = build_ego_figure(graph_spec_from_dict(_ego_doc()), lexicon)
        b = build_ego_figure(graph_spec_from_dict(_ego_doc()), lexicon)
        assert a.svg == b.svg and a.svg_narrow == b.svg_narrow

    def test_cap_and_shape_refusals(self, lexicon: Lexicon) -> None:
        # 51 nodes → refuse
        nodes = [_node("c", "centre")]
        edges = []
        for i in range(51):
            nodes.append(_node(f"n{i}", "neighbour"))
            edges.append(_edge("c", f"n{i}"))
        doc = _ego_doc(nodes=nodes, edges=edges)
        with pytest.raises(FigureKitError, match="50"):
            build_ego_figure(graph_spec_from_dict(doc), lexicon)
        # two centres → refuse
        with pytest.raises(FigureKitError, match="one centre"):
            build_ego_figure(
                graph_spec_from_dict(
                    _ego_doc(
                        nodes=[
                            _node("c", "centre"),
                            _node("c2", "centre"),
                            _node("n1", "neighbour"),
                        ],
                        edges=[_edge("c", "n1")],
                    )
                ),
                lexicon,
            )
        # neighbour without a centre edge → refuse
        with pytest.raises(FigureKitError, match="no centre edge"):
            build_ego_figure(
                graph_spec_from_dict(
                    _ego_doc(
                        nodes=[
                            _node("c", "centre"),
                            _node("n1", "neighbour"),
                            _node("orphan", "neighbour"),
                        ],
                        edges=[_edge("c", "n1")],
                    )
                ),
                lexicon,
            )
        # a neighbour↔neighbour edge is not 1-hop → refuse
        with pytest.raises(FigureKitError, match="1-hop"):
            build_ego_figure(
                graph_spec_from_dict(
                    _ego_doc(edges=[_edge("c", "n1"), _edge("n1", "n2"), _edge("c", "n3")])
                ),
                lexicon,
            )

    def test_muted_and_observed_channels(self, lexicon: Lexicon) -> None:
        res = build_ego_figure(graph_spec_from_dict(_ego_doc()), lexicon)
        assert "sig-fig-edge-muted" in res.svg
        assert "sig-fig-edge-acc-declared" in res.svg
        ids = {e["id"] for e in res.legend}
        assert "line:declared" in ids and "currency:muted" in ids


# --- charts ---------------------------------------------------------------------


class TestCharts:
    def test_bar(self, lexicon: Lexicon) -> None:
        res = build_chart(chart_spec_from_dict(_chart_doc()), lexicon)
        assert res.mode == "bar"
        assert "sig-fig-bar" in res.svg
        assert res.table_columns == ("category", "value", "unit")
        assert res.table_rows[0] == {
            "category": "Axon",
            "value": 10.0,
            "unit": "agencies",
            "href": "/entities/axon/",
        }
        # the value is a direct label at the bar's end
        assert ">14<" in res.svg
        assert res.narrow_viewbox[0] == 360
        assert 'href="/entities/axon/"' in res.svg

    def test_bar_deterministic_and_empty_refuses(self, lexicon: Lexicon) -> None:
        a = build_chart(chart_spec_from_dict(_chart_doc()), lexicon)
        b = build_chart(chart_spec_from_dict(_chart_doc()), lexicon)
        assert a.svg == b.svg
        with pytest.raises(FigureKitError, match="needs categories"):
            chart_spec_from_dict(_chart_doc(categories=[]))
        with pytest.raises(FigureKitError, match="negative"):
            chart_spec_from_dict(_chart_doc(categories=[{"label": "x", "values": [-1]}]))
        with pytest.raises(FigureKitError, match="nothing to draw"):
            build_chart(
                chart_spec_from_dict(_chart_doc(categories=[{"label": "x", "values": [0]}])),
                lexicon,
            )

    def test_stacked_bar(self, lexicon: Lexicon) -> None:
        doc = _chart_doc(
            kind="stacked-bar",
            series=["federal", "state", "other"],
            categories=[
                {"label": "Axon", "values": [10, 5, 2], "href": "/entities/axon/"},
                {"label": "Flock", "values": [8, 3, 0]},
            ],
        )
        res = build_chart(chart_spec_from_dict(doc), lexicon)
        assert res.mode == "stacked-bar"
        assert "sig-fig-series-0" in res.svg and "sig-fig-series-2" in res.svg
        ids = [e["id"] for e in res.legend]
        assert ids == ["series:0", "series:1", "series:2"]
        assert [e["label"] for e in res.legend] == ["federal", "state", "other"]
        assert res.table_columns == ("category", "federal", "state", "other", "total")
        assert res.table_rows[0]["total"] == 17.0
        # the legend draws inside the figure too
        assert ">federal<" in res.svg

    def test_stacked_bar_series_cap(self, lexicon: Lexicon) -> None:
        doc = _chart_doc(
            kind="stacked-bar",
            series=[f"s{i}" for i in range(10)],
            categories=[{"label": "x", "values": [1] * 10}],
        )
        with pytest.raises(FigureKitError, match="series"):
            build_chart(chart_spec_from_dict(doc), lexicon)
        # 9 series = the K5 top-8 + other ceiling → allowed
        doc9 = _chart_doc(
            kind="stacked-bar",
            series=[f"s{i}" for i in range(9)],
            categories=[{"label": "x", "values": [1] * 9}],
        )
        res = build_chart(chart_spec_from_dict(doc9), lexicon)
        assert "sig-fig-series-8" in res.svg

    def test_strip(self, lexicon: Lexicon) -> None:
        doc = _chart_doc(
            kind="strip",
            categories=[],
            series=[],
            events=[
                {"date": "2024-01-05", "label": "run A", "href": "/r/a/"},
                {"date": "2024-03-01", "label": "run B"},
                {"date": "2024-03-01", "label": "run C"},
            ],
        )
        res = build_chart(chart_spec_from_dict(doc), lexicon)
        assert res.mode == "strip"
        assert res.svg.count("sig-fig-mark") == 3
        assert 'href="/r/a/"' in res.svg
        # the two same-day events stack into a second lane above lane 0
        cy = re.findall(r"M([\d.]+) ([\d.]+)a4\.50", res.svg)
        assert len({c[1] for c in cy}) == 2  # two lanes: B + C stack
        assert res.table_rows[1]["event"] == "run B"

    def test_timeline(self, lexicon: Lexicon) -> None:
        doc = _chart_doc(
            kind="timeline",
            categories=[],
            series=[],
            events=[
                {"date": "2024-01-05", "label": "contract signed"},
                {"date": "2024-06-01", "label": "deployment observed"},
            ],
        )
        res = build_chart(chart_spec_from_dict(doc), lexicon)
        assert res.mode == "timeline"
        assert "sig-fig-mark-label" in res.svg
        assert "contract signed" in res.svg
        assert res.table_columns == ("date", "event", "kind", "href")

    def test_chart_refusals(self, lexicon: Lexicon) -> None:
        with pytest.raises(FigureKitError, match="schema"):
            chart_spec_from_dict({"schema": "nope"})
        with pytest.raises(FigureKitError, match="kind"):
            chart_spec_from_dict(_chart_doc(kind="pie"))
        # undated events refuse — a time axis cannot place them
        with pytest.raises(FigureKitError, match="undated"):
            chart_spec_from_dict(_chart_doc(kind="strip", categories=[], events=[{"label": "x"}]))
        # malformed ISO date refuses
        with pytest.raises(FigureKitError, match="ISO"):
            chart_spec_from_dict(
                _chart_doc(
                    kind="strip", categories=[], events=[{"date": "not-a-date", "label": "x"}]
                )
            )
        # bar is single-series
        with pytest.raises(FigureKitError, match="single-series"):
            chart_spec_from_dict(
                _chart_doc(
                    kind="bar",
                    series=["a", "b"],
                    categories=[{"label": "x", "values": [1, 2]}],
                )
            )
        # stacked-bar needs named series + matching value counts
        with pytest.raises(FigureKitError, match="named series"):
            chart_spec_from_dict(
                _chart_doc(
                    kind="stacked-bar", series=[], categories=[{"label": "x", "values": [1]}]
                )
            )
        with pytest.raises(FigureKitError, match="values"):
            chart_spec_from_dict(
                _chart_doc(
                    kind="stacked-bar",
                    series=["a", "b"],
                    categories=[{"label": "x", "values": [1]}],
                )
            )


# --- the generated legend --------------------------------------------------------


class TestLegend:
    def test_unknown_encoding_refuses(self, lexicon: Lexicon) -> None:
        with pytest.raises(FigureKitError, match="not in the kit vocabulary"):
            build_legend_entries(["blink:neon"], lexicon)
        with pytest.raises(FigureKitError):
            build_legend_entries(["kind:submarine"], lexicon)

    def test_series_without_label_refuses(self, lexicon: Lexicon) -> None:
        with pytest.raises(FigureKitError, match="caller label"):
            build_legend_entries(["series:3"], lexicon, series_labels=("a",))

    def test_canonical_order_and_dedupe(self, lexicon: Lexicon) -> None:
        entries = build_legend_entries(
            [
                "kind:vendor",
                "line:observed",
                "currency:muted",
                "line:configured",
                "kind:agency",
                "line:configured",
            ],
            lexicon,
        )
        ids = [e.id for e in entries]
        assert ids == [
            "line:configured",
            "line:observed",
            "currency:muted",
            "kind:agency",
            "kind:vendor",
        ]
        # every entry is lexicon-sourced
        for e in entries:
            assert e.label and e.to_json()["spec"]

    def test_fill_states(self, lexicon: Lexicon) -> None:
        entries = build_legend_entries(["fill:singleSource", "fill:corroborated"], lexicon)
        assert entries[0].id == "fill:singleSource"
        assert entries[1].label == "2+ source records; republications not yet collapsed"


# --- the licence pin -------------------------------------------------------------


def test_no_third_party_layout_dependency() -> None:
    """The layout wrapper is in-house deterministic math — the GPL igraph
    wheel is never imported by the figure kit (the contract's licence pin)."""
    import exports.figures as figures_pkg

    pkg_dir = Path(figures_pkg.__file__).parent
    for py in pkg_dir.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        assert "import igraph" not in src and "from igraph" not in src, py.name


# --- the CLI verbs -----------------------------------------------------------------


def _cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "exports", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )


class TestCli:
    def test_network_verb(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps(_graph_doc()), encoding="utf-8")
        out = tmp_path / "fig.svg"
        narrow = tmp_path / "fig.narrow.svg"
        meta = tmp_path / "fig.json"
        r = _cli(
            "figure",
            "network",
            "--in",
            str(spec),
            "--out",
            str(out),
            "--out-narrow",
            str(narrow),
            "--meta",
            str(meta),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        svg = out.read_text(encoding="utf-8")
        assert "sig-fig-graph" in svg
        m = json.loads(meta.read_text(encoding="utf-8"))
        assert m["schema"] == "sig.figure-graph-meta/1"
        assert m["legend"] and m["table_rows"]
        assert "sig-fig-graph" in narrow.read_text(encoding="utf-8")

    def test_ego_and_chart_verbs(self, tmp_path: Path) -> None:
        for verb, doc in (("ego", _ego_doc()), ("chart", _chart_doc())):
            spec = tmp_path / f"{verb}.json"
            spec.write_text(json.dumps(doc), encoding="utf-8")
            out = tmp_path / f"{verb}.svg"
            r = _cli("figure", verb, "--in", str(spec), "--out", str(out))
            assert r.returncode == 0, (verb, r.stdout, r.stderr)
            assert out.read_text(encoding="utf-8").startswith("<svg")

    def test_malformed_spec_refuses(self, tmp_path: Path) -> None:
        spec = tmp_path / "bad.json"
        spec.write_text(json.dumps({"schema": "nope"}), encoding="utf-8")
        r = _cli("figure", "network", "--in", str(spec), "--out", str(tmp_path / "x.svg"))
        assert r.returncode == 4
        assert "refused" in r.stdout
        spec.write_text("{ not json", encoding="utf-8")
        r = _cli("figure", "chart", "--in", str(spec), "--out", str(tmp_path / "x.svg"))
        assert r.returncode == 4

    def test_out_narrow_on_geo_verb_refuses(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps(_graph_doc()), encoding="utf-8")
        # sprite has no narrow variant
        sprite = tmp_path / "sprite.json"
        sprite.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "jkey": "us.ny",
                            "outline": [[[-79, 42], [-79, 45], [-71, 45], [-71, 42], [-79, 42]]],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        r = _cli(
            "figure",
            "sprite",
            "--in",
            str(sprite),
            "--out",
            str(tmp_path / "s.svg"),
            "--out-narrow",
            str(tmp_path / "s.n.svg"),
        )
        assert r.returncode == 4
        assert "no narrow variant" in r.stdout
