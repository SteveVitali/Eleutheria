# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P36.27 static figure kit — geography half (FIG-01a, ADR-157).

Every acceptance point the ticket names gets a test that fails if the
behaviour is removed: projection/fit, simplification determinism, the
``static-12px@1`` binning threshold, points-vs-areas, the tier guards and
precision ceilings, the 'not drawn' counters, outlines + child links, the
locator and index sprite, the CSP-safe serializer, byte-determinism, and the
lexicon/token vocabulary (SIG-UI-066/094/123/124/131/134).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from exports.figures import (
    RULE_NAME,
    FigureKitError,
    FigureSizeError,
    Lexicon,
    SpriteEntry,
    SvgError,
    assert_svg_safe,
    build_index_sprite,
    build_locator,
    build_map_figure,
    load_lexicon,
    sig_token_value,
    spec_from_dict,
    standalone_document,
)
from exports.figures.binning import (
    BIN_HEX_MIN_DIAMETER_PX,
    BIN_POINT_MAX_RECORDS,
    BIN_POINT_ZOOM_MIN,
    finest_drawable_res,
    meters_per_view_unit,
    plan_binning,
)
from exports.figures.model import INPUT_SCHEMA, RecordInput, load_spec
from exports.figures.paths import outline_to_path
from exports.figures.projection import (
    fit_bounds,
    outline_bounds,
    project,
    project_outline,
)
from exports.figures.serialize import El, document
from exports.figures.simplify import ring_perimeter, simplify_ring
from exports.figures.tokens import SIG_TOKEN_VALUES_DARK, SIG_TOKEN_VALUES_LIGHT

REPO_ROOT = Path(__file__).resolve().parents[2]
TOKENS_CSS = REPO_ROOT / "web/src/styles/tokens.css"

NY_OUTLINE = [[[-79.8, 42.0], [-79.8, 45.0], [-71.8, 45.0], [-71.8, 42.0], [-79.8, 42.0]]]
CHILD_OUTLINE = [[[-74.0, 42.5], [-74.0, 43.0], [-73.5, 43.0], [-73.5, 42.5], [-74.0, 42.5]]]


def _ol(rings: list[list[list[float]]]) -> tuple[tuple[tuple[float, float], ...], ...]:
    """JSON rings → the kit's ``Outline``."""
    return tuple(tuple((float(pt[0]), float(pt[1])) for pt in ring) for ring in rings)


def _rec(
    rid: str,
    lat: float | None = 42.65,
    lon: float | None = -73.75,
    tier: int = 0,
    sources: list[str] | None = None,
    **kw: object,
) -> dict[str, object]:
    d: dict[str, object] = {
        "record_id": rid,
        "lat": lat,
        "lon": lon,
        "tier": tier,
        "sources": sources or ["src-a"],
        "compartment": "records",
    }
    d.update(kw)
    return d


def _spec_doc(**kw: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema": INPUT_SCHEMA,
        "release": {
            "label": "R11 fixture",
            "publication_id": "pub-fixture",
            "as_of_world": "2026-01-01",
        },
        "jurisdiction": {
            "jkey": "us.ny",
            "slug_path": "/us/ny/",
            "level": "state",
            "chain": ["us", "us.ny"],
            "name": "New York",
        },
        "outline": NY_OUTLINE,
        "children": [],
        "records": [_rec("r1")],
        "boundary_vintage": "census.cb.2025.500k",
        "size_cap_gzip": None,
    }
    doc.update(kw)
    return doc


@pytest.fixture(scope="module")
def lexicon() -> Lexicon:
    return load_lexicon(repo_root=REPO_ROOT)


# --- projection and fit -------------------------------------------------------


def test_projection_known_point() -> None:
    # Null island projects to the origin.
    x, y = project(0.0, 0.0)
    assert abs(x) < 1e-6 and abs(y) < 1e-6
    # The Mercator world spans ±world/2 at the poles' latitude bound.
    x, _ = project(180.0, 0.0)
    assert x == pytest.approx(20037508.342789244)


def test_fit_frame_respects_aspect_and_cap() -> None:
    bounds = outline_bounds([project_outline(_ol(NY_OUTLINE))])
    frame = fit_bounds(bounds, 720, 520, 8)
    assert frame.width == 720
    assert frame.height <= 520
    # The fitted scale keeps every bound inside the padded box.
    for ring in project_outline(_ol(NY_OUTLINE)):
        for x, y in ring:
            vx, vy = frame.point(x, y)
            assert 8 - 1e-6 <= vx <= 712 + 1e-6
            assert 8 - 1e-6 <= vy <= frame.height - 8 + 1e-6


def test_fit_frame_degenerate_input_fails() -> None:
    with pytest.raises(FigureKitError):
        outline_bounds([])
    with pytest.raises(FigureKitError):
        fit_bounds((0, 0, 1, 1), width=16, max_height=16, padding=8)


def test_framing_zoom_band() -> None:
    # A US-state-sized frame reads in the recorded ~z5–6 band (D-K6-4) —
    # the zoom vocabulary the binning rule shares with MAP-07.
    bounds = outline_bounds([project_outline(_ol(NY_OUTLINE))])
    frame = fit_bounds(bounds, 720, 520, 8)
    assert 4.0 < frame.zoom < 8.0


# --- simplification and determinism -------------------------------------------


def test_simplify_deterministic_and_min_perimeter() -> None:
    ring = (
        (0.0, 0.0),
        (0.0001, 5.0),
        (0.0, 10.0),
        (10.0, 10.0),
        (9.9999, 5.0),
        (10.0, 0.0),
    )
    s1 = simplify_ring(ring, tolerance=0.5)
    s2 = simplify_ring(ring, tolerance=0.5)
    assert s1 == s2  # byte-stable subsequence
    assert len(s1) <= len(ring)
    assert all(p in ring for p in s1)
    # A degenerate sub-pixel ring is dropped by the 1.0px perimeter rule.
    tiny = (((0.0, 0.0), (0.2, 0.0), (0.1, 0.2)),)
    assert outline_to_path(tiny) is None
    assert ring_perimeter(tiny[0]) < 1.0


# --- the static-12px@1 binning rule --------------------------------------------


def _mk_records(n: int, tier: int = 0) -> list[RecordInput]:
    return [
        spec_from_dict(_spec_doc(records=[_rec(f"r{i}", tier=tier)])).records[0] for i in range(n)
    ]


def test_binning_points_mode_below_threshold() -> None:
    plan = plan_binning(_mk_records(3), zoom=10.5, frame_scale=0.001, mean_lat=42.0, width=720)
    assert plan.mode == "points"
    assert plan.h3_res is None


def test_binning_areas_above_record_cap() -> None:
    plan = plan_binning(
        _mk_records(BIN_POINT_MAX_RECORDS + 1, tier=0),
        zoom=12.0,
        frame_scale=0.001,
        mean_lat=42.0,
        width=720,
    )
    assert plan.mode == "h3-areas"
    assert plan.h3_res is not None


def test_binning_areas_below_zoom() -> None:
    plan = plan_binning(
        _mk_records(2), zoom=BIN_POINT_ZOOM_MIN - 0.1, frame_scale=0.0008, mean_lat=42.0, width=720
    )
    assert plan.mode == "h3-areas"
    assert plan.h3_res is not None
    # The chosen resolution satisfies the 12-px rule at this frame.
    import h3

    m_per_unit = meters_per_view_unit(0.0008, 42.0)
    diameter_m = 2.0 * h3.average_hexagon_edge_length(plan.h3_res, unit="m")
    assert diameter_m / m_per_unit >= BIN_HEX_MIN_DIAMETER_PX


def test_binning_precision_ceiling_tiers() -> None:
    # A tier-2 cohort caps the res well below what the 12-px rule alone would
    # pick — never finer than the published precision (K6 V-4).
    t0 = plan_binning(
        _mk_records(2, tier=0), zoom=6.0, frame_scale=0.0008, mean_lat=42.0, width=720
    )
    t2 = plan_binning(
        _mk_records(2, tier=2), zoom=6.0, frame_scale=0.0008, mean_lat=42.0, width=720
    )
    assert t0.h3_res is not None and t2.h3_res is not None
    assert t2.h3_res <= t0.h3_res
    cap = finest_drawable_res(_mk_records(1, tier=2))
    assert cap is not None and t2.h3_res <= cap


def test_binning_deterministic_cell_order() -> None:
    recs = _mk_records(40)
    p1 = plan_binning(recs, zoom=6.0, frame_scale=0.0008, mean_lat=42.0, width=720)
    p2 = plan_binning(list(reversed(recs)), zoom=6.0, frame_scale=0.0008, mean_lat=42.0, width=720)
    assert p1 == p2


# --- the figure itself ---------------------------------------------------------


def test_map_figure_areas_mode_not_drawn(lexicon: Lexicon) -> None:
    doc = _spec_doc(
        records=[
            _rec("a", contested=True),
            _rec("b", lat=42.7, lon=-73.8, sources=["s1", "s2"]),
            _rec("c", lat=None, lon=None, declared_jkey="us.ny"),
            _rec("d", lat=41.0, lon=-74.0, tier=3),
            _rec("e", lat=43.0, lon=-75.0, tier=1, conflicting=True),
            _rec("f", lat=42.9, lon=-74.5, tier=2),
            _rec("g", lat=42.2, lon=-75.5, located_elsewhere_jkey="us.pa"),
        ]
    )
    res = build_map_figure(spec_from_dict(doc), lexicon)
    assert res.mode == "h3-areas"
    nd = res.not_drawn
    assert nd.declared_no_point == 1
    assert nd.located_elsewhere == (("us.pa", 1),)
    assert nd.conflicting == 1
    assert nd.tier3 == 1
    assert res.rule == RULE_NAME
    meta = res.to_json()
    assert meta["schema"] == "sig.figure-geo-meta/1"
    assert meta["not_drawn"]["tier3"] == 1


def test_map_figure_points_mode(lexicon: Lexicon) -> None:
    # A tight county-level outline frames above z10 → tier-0 published points.
    doc = _spec_doc(
        outline=[[[-74.1, 42.4], [-74.1, 42.6], [-73.9, 42.6], [-73.9, 42.4], [-74.1, 42.4]]],
        records=[_rec("a", lat=42.5, lon=-74.0), _rec("b", lat=42.55, lon=-73.95)],
        jurisdiction={
            "jkey": "us.ny.albany",
            "slug_path": "/us/ny/albany/",
            "level": "county",
            "chain": ["us", "us.ny", "us.ny.albany"],
            "name": "Albany County",
        },
    )
    res = build_map_figure(spec_from_dict(doc), lexicon)
    assert res.mode == "points"
    assert res.zoom >= BIN_POINT_ZOOM_MIN
    assert "sig-fig-point" in res.svg


def test_child_links_and_hatch(lexicon: Lexicon) -> None:
    doc = _spec_doc(
        children=[
            {
                "jkey": "us.ny.albany",
                "rings": CHILD_OUTLINE,
                "coverage": "covered",
                "href": "/us/ny/albany/",
            },
            {
                "jkey": "us.ny.tomp",
                "rings": [
                    [[-76.7, 42.3], [-76.7, 42.7], [-76.2, 42.7], [-76.2, 42.3], [-76.7, 42.3]]
                ],
                "coverage": "not_covered",
            },
            {
                "jkey": "us.ny.ulster",
                "rings": [
                    [[-74.4, 41.8], [-74.4, 42.1], [-73.9, 42.1], [-73.9, 41.8], [-74.4, 41.8]]
                ],
                "coverage": "rule_pending",
            },
        ]
    )
    res = build_map_figure(spec_from_dict(doc), lexicon)
    # The drill-down link is the pointer affordance; the places-table rows in
    # the metadata are the accessible twin (SIG-UI-131).
    assert 'href="/us/ny/albany/"' in res.svg
    assert 'aria-hidden="true"' in res.svg
    assert "fig-hatch" in res.svg
    assert "sig-fig-child-uncovered" in res.svg
    assert "sig-fig-child-pending" in res.svg
    rows = {c["jkey"]: c for c in res.children}
    assert rows["us.ny.albany"]["href"] == "/us/ny/albany/"
    assert rows["us.ny.tomp"]["coverage"] == "not_covered"


def test_map_figure_byte_deterministic(lexicon: Lexicon) -> None:
    doc = _spec_doc(
        children=[
            {
                "jkey": "us.ny.albany",
                "rings": CHILD_OUTLINE,
                "coverage": "covered",
                "href": "/us/ny/albany/",
            }
        ],
        records=[_rec(f"r{i}", lat=42.0 + i * 0.1) for i in range(30)],
    )
    a = build_map_figure(spec_from_dict(doc), lexicon)
    b = build_map_figure(spec_from_dict(json.loads(json.dumps(doc))), lexicon)
    assert a.svg == b.svg  # byte-identical across builds
    assert standalone_document(a.svg, lexicon) == standalone_document(b.svg, lexicon)


def test_map_figure_no_data_leakage(lexicon: Lexicon) -> None:
    doc = _spec_doc(records=[_rec(f"r{i}", lat=42.0 + i * 0.05) for i in range(20)])
    res = build_map_figure(spec_from_dict(doc), lexicon)
    svg = res.svg
    # SIG-UI-134: no per-area numerals, ids or data-* in emitted bytes.
    assert not re.search(r"\bdata-[a-z0-9-]+\s*=", svg)
    for rid in (f"r{i}" for i in range(20)):
        assert rid not in svg


def test_size_cap_fallback_ladder(lexicon: Lexicon) -> None:
    doc = _spec_doc(
        children=[
            {"jkey": f"us.ny.c{i}", "rings": CHILD_OUTLINE, "coverage": "covered"}
            for i in range(60)
        ],
        records=[_rec(f"r{i}", lat=42.0 + i * 0.01) for i in range(500)],
    )
    res = build_map_figure(spec_from_dict(doc), lexicon)
    assert res.gzip_bytes <= 30 * 1024
    if res.cap_actions:
        assert res.cap_actions[0] == "child-outline-tol-1.0px"


def test_size_cap_fail_closed(lexicon: Lexicon) -> None:
    doc = _spec_doc(
        records=[_rec(f"r{i}", lat=42.0 + i * 0.01) for i in range(400)],
        size_cap_gzip=10,  # an unsatisfiable cap must refuse, never emit silently
    )
    with pytest.raises(FigureSizeError):
        build_map_figure(spec_from_dict(doc), lexicon)


def test_empty_spec_fails_closed(lexicon: Lexicon) -> None:
    with pytest.raises(FigureKitError):
        spec_from_dict({"schema": "wrong"})
    with pytest.raises(FigureKitError):
        spec_from_dict(_spec_doc(records=[_rec("x", tier=9)]))
    with pytest.raises(FigureKitError):
        build_map_figure(spec_from_dict(_spec_doc(outline=[])), lexicon)


def test_load_spec_from_disk(tmp_path: Path, lexicon: Lexicon) -> None:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(_spec_doc()), encoding="utf-8")
    spec = load_spec(p)
    res = build_map_figure(spec, lexicon)
    assert res.mode in ("points", "h3-areas")


# --- the CSP-safe serializer ----------------------------------------------------


def test_svg_safety_rejects_banned_output(lexicon: Lexicon) -> None:
    res = build_map_figure(spec_from_dict(_spec_doc()), lexicon)
    svg = res.svg
    assert assert_svg_safe(svg, allow_style_block=False) == svg
    for bad in (
        "<script>x</script>",
        '<a onclick="x()"/>',
        '<a href="https://evil.example/"/>',
        '<a href="//evil.example/"/>',
        '<a href="javascript:void(0)"/>',
        '<rect style="fill:red"/>',
        '<path data-count="5"/>',
        "<style>@import url(https://evil.example/x.css)</style>",
        "<foreignObject/>",
    ):
        with pytest.raises(SvgError):
            assert_svg_safe(bad if "<svg" not in bad else bad, allow_style_block=True)


def test_serializer_refuses_banned_attr_and_href() -> None:
    with pytest.raises(SvgError):
        El("path").attr("onclick", "x()")
    with pytest.raises(SvgError):
        El("a").attr("href", "https://evil.example/")
    with pytest.raises(SvgError):
        El("a").attr("href", "javascript:void(0)")
    # Fragment + root-relative links are the whole permitted vocabulary.
    assert document(El("a").attr("href", "#fig-hatch")) == '<a href="#fig-hatch"/>\n'
    assert document(El("a").attr("href", "/us/ny/")) == '<a href="/us/ny/"/>\n'


def test_inline_figure_never_carries_style(lexicon: Lexicon) -> None:
    res = build_map_figure(spec_from_dict(_spec_doc()), lexicon)
    assert "<style" not in res.svg
    with pytest.raises(SvgError):
        assert_svg_safe(
            res.svg.replace("<defs>", "<style>x{}</style><defs>"), allow_style_block=False
        )


# --- the standalone renderer ----------------------------------------------------


def test_standalone_document(lexicon: Lexicon) -> None:
    res = build_map_figure(spec_from_dict(_spec_doc()), lexicon)
    doc = standalone_document(res.svg, lexicon)
    assert doc.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<style>" in doc
    # The style block carries the same --sig-* literals, light and dark —
    # the lexicon's declared data hue included.
    assert sig_token_value(lexicon.data_hue_token) in doc
    assert "prefers-color-scheme:dark" in doc
    assert SIG_TOKEN_VALUES_DARK["sig-data-1"] in doc
    # The full safety contract still holds — the style block is the only
    # relaxation the P36.19 policy grants.
    assert assert_svg_safe(doc, allow_style_block=True) == doc
    assert "onload" not in doc
    # The only http literal is the SVG namespace identifier (a name, never a
    # fetch) — no external reference may appear anywhere else.
    assert doc.count("http://") == 1
    assert 'xmlns="http://www.w3.org/2000/svg"' in doc
    assert "https://" not in doc
    assert not re.search(r"\bdata-[a-z0-9-]+\s*=", doc)  # no data-* attributes


# --- locator and index sprite ---------------------------------------------------


def test_locator_and_sprite(lexicon: Lexicon) -> None:
    ctx = _ol(NY_OUTLINE)
    fcs = _ol(CHILD_OUTLINE)
    svg = build_locator(tuple(ctx), tuple(fcs), "New York", "Albany County")
    assert "sig-fig-locator" in svg
    assert assert_svg_safe(svg, allow_style_block=False) == svg
    # Focus outside context → fail closed.
    with pytest.raises(FigureKitError):
        build_locator(
            _ol(NY_OUTLINE),
            (((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),),
            "New York",
            "Nowhere",
        )

    spr, index = build_index_sprite(
        [
            SpriteEntry("us.ny", _ol(NY_OUTLINE)),
            SpriteEntry("us.ny.albany", _ol(CHILD_OUTLINE)),
        ]
    )
    assert "sig-fig-sprite" in spr
    assert index["schema"] == "sig.figure-index-sprite/1"
    assert [g["jkey"] for g in index["glyphs"]] == ["us.ny", "us.ny.albany"]
    assert index["glyphs"][1]["x"] == index["cell_px"]
    with pytest.raises(FigureKitError):
        build_index_sprite([])
    with pytest.raises(FigureKitError):
        build_index_sprite(
            [
                SpriteEntry("dup", _ol(NY_OUTLINE)),
                SpriteEntry("dup", _ol(CHILD_OUTLINE)),
            ]
        )


# --- the lexicon / token vocabulary ---------------------------------------------


def test_lexicon_bindings(lexicon: Lexicon) -> None:
    # The kit reads P36.17's shared lexicon — the declared bindings drive the
    # emitted vocabulary (no figure-private meanings).
    assert lexicon.data_hue_token == "sig-data-1"
    assert lexicon.contested_token.startswith("sig-epi-")
    assert lexicon.corroboration_class(1) == "sig-fig-src-single"
    assert lexicon.corroboration_class(2) == "sig-fig-src-corroborated"
    with pytest.raises(FigureKitError):
        lexicon.check_class("sig-fig-invented")


def test_token_mirror_matches_tokens_css() -> None:
    """The Python mirror must equal tokens.css byte-for-byte — the same drift
    rule ``web/tests/unit/design-tokens.test.ts`` enforces on the TS side."""
    text = TOKENS_CSS.read_text(encoding="utf-8")
    # Split light :root, the dark @media block and the print @media block.
    dark_m = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*?)\n\}", text, re.S)
    assert dark_m, "tokens.css lost its dark block"
    head = text[: dark_m.start()]
    root_m = re.search(r":root\s*\{(.*?)\}", head, re.S)
    assert root_m
    light_css = dict(re.findall(r"--(sig-[a-z0-9-]+)\s*:\s*([^;]+);", root_m.group(1)))
    dark_css = dict(re.findall(r"--(sig-[a-z0-9-]+)\s*:\s*([^;]+);", dark_m.group(1)))
    for name, value in SIG_TOKEN_VALUES_LIGHT.items():
        assert light_css.get(name, "").rstrip() == value, f"light {name} drifted"
    for name, value in SIG_TOKEN_VALUES_DARK.items():
        assert dark_css.get(name, "").rstrip() == value, f"dark {name} drifted"


def test_lexicon_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(FigureKitError):
        load_lexicon(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema":"sig.lexicon/1","legend":{}}', encoding="utf-8")
    with pytest.raises(FigureKitError):
        load_lexicon(bad)


def test_unknown_token_fails_closed() -> None:
    with pytest.raises(FigureKitError):
        sig_token_value("sig-made-up")


# --- the CLI seam ----------------------------------------------------------------


def test_cli_figure_map(tmp_path: Path) -> None:
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(_spec_doc()), encoding="utf-8")
    out = tmp_path / "fig.svg"
    meta = tmp_path / "meta.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "exports",
            "figure",
            "map",
            "--in",
            str(spec),
            "--out",
            str(out),
            "--meta",
            str(meta),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    svg = out.read_text(encoding="utf-8")
    assert_svg_safe(svg, allow_style_block=False)
    m = json.loads(meta.read_text(encoding="utf-8"))
    assert m["schema"] == "sig.figure-geo-meta/1"
    assert m["rule"] == RULE_NAME


def test_cli_figure_refuses_bad_spec(tmp_path: Path) -> None:
    spec = tmp_path / "bad.json"
    spec.write_text('{"schema":"nope"}', encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "exports",
            "figure",
            "map",
            "--in",
            str(spec),
            "--out",
            str(tmp_path / "x.svg"),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 4
    assert "refused" in proc.stdout


def test_cli_figure_sprite(tmp_path: Path) -> None:
    spec = tmp_path / "sprite.json"
    spec.write_text(
        json.dumps({"entries": [{"jkey": "us.ny", "outline": NY_OUTLINE}]}),
        encoding="utf-8",
    )
    out = tmp_path / "spr.svg"
    idx = tmp_path / "idx.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "exports",
            "figure",
            "sprite",
            "--in",
            str(spec),
            "--out",
            str(out),
            "--meta",
            str(idx),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    index = json.loads(idx.read_text(encoding="utf-8"))
    assert index["schema"] == "sig.figure-index-sprite/1"
