# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-dossier map + locator figure emission (K6 VIZ-01a, P36.54).

For every D-K4-3 page key this module composes the ``sig.figure-kit-geo/1``
spec from the export's own verified inputs — the boundary-pack geometries
the placement run minted (``PlacementEngine.jurisdiction_outlines``), the
keyed registry, and the contribution plan's placed leg — renders the figure
through the one kit (``exports.figures.build_map_figure`` — P36.27, the
single render-core owner), and emits:

* ``inputs/dossier-visuals/<slug-path>.json`` — the **restricted build
  input** ``sig.dossier-visuals/1`` (K6 §9.1: consumed by the Astro build,
  NEVER published — per-area record geometry across compartments would be a
  licence-mixed derived dataset, SIG-UI-134/DV12). It rides
  ``SpineExport.restricted_artifacts``: written to disk, never manifest-listed.
* ``inputs/dossier-visuals/index.json`` — the ``sig.dossier-visuals-index/1``
  size/time report (per-dossier bytes/gzip/mode/cap actions + wall clock);
  it is the VIZ-01a "size and time report" and measures the same way on the
  real release (US/GA/TX/CA/DC-scale dossiers ride the next export).
* ``inputs/dossier-visuals/locator-symbols.json`` + the public produced-work
  sheet ``web/figures/locator-symbols.svg`` — the ``sig.locator-symbols/1``
  parent-context glyphs every dossier locator + the JUR-04 index cite.
* ``web/map/coverage_by_jurisdiction.json`` — MAP-01b's coverage table.
  P37.17 (D-K1-4 = yes, ADR-241): the real ``declared-scope@1`` rule emits
  from ``exports.map_dict.coverage_doc`` when bound — children draw
  ``covered``/``not_covered``; an unbound build keeps the honest soft
  fallback (``rule_version: "rule-pending@1"``, the K6 §5.1 verbatim
  legend, ``rule_pending`` children).
* ``web/figures/dossier/<slug-path>.svg`` — the standalone download for
  country + admin-1 dossiers only (D-K6-5), the P36.19 standalone document.

Honesty postures (agent-drafted copy is labelled, never proxied — OM-08/09):
the per-dossier ``figures[]`` twin carries ``caption_drafted`` naming the
K6 §5.1 template as agent-drafted; ``provisional`` records stay False —
the export has no candidate-record signal yet, recorded not fabricated.
"""

from __future__ import annotations

import gzip
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import dossier_networks as _dn
from . import figures as _fig
from . import static_map as _sm
from .figures.model import FigureKitError, spec_from_dict
from .manifest import canonical_json, sha256_hex

#: The emitted document ids (K6 §9.1 + the index/report).
VISUALS_SCHEMA = "sig.dossier-visuals/1"
VISUALS_INDEX_SCHEMA = "sig.dossier-visuals-index/1"

#: Restricted staging root — the same ``inputs/`` seam the boundary pack uses
#: (K4 §4.2's "restricted export inputs"; outside the published ``web/`` tree).
VISUALS_DIR = "inputs/dossier-visuals"

#: Public produced-work paths.
LOCATOR_SVG_PATH = "web/figures/locator-symbols.svg"
LOCATOR_INDEX_PATH = "web/figures/locator-symbols.json"
COVERAGE_PATH = "web/map/coverage_by_jurisdiction.json"
STANDALONE_DIR = "web/figures/dossier"

#: Levels whose dossiers earn the standalone SVG download (D-K6-5 verbatim:
#: "country and admin-1 dossiers in Round 11").
_STANDALONE_LEVELS = frozenset({"country", "state_province"})


def _compartment_of(licences: Sequence[str], compartment_of_lic: Mapping[str, str]) -> str:
    """One record's compartment label for the figure spec — deterministic:
    the sorted-first compartment across its published licences (a record
    spanning compartments draws under its first; the figure's drawn set is
    reported in ``compartments_drawn`` regardless)."""
    comps = sorted({compartment_of_lic.get(str(lic), "unknown") for lic in licences})
    return comps[0] if comps else "unknown"


def _record_inputs(
    acc: Any,
    *,
    sites_by_id: Mapping[str, Any],
    results_by_id: Mapping[str, Any],
    licences_by_subject: Mapping[str, Any],
    compartment_of_lic: Mapping[str, str],
    geo_predicates: frozenset[str],
) -> list[dict[str, Any]]:
    """The figure's ``records[]`` — published positions only (SIG-UI-134).

    Draw rule mirrors ``_map_layer`` verbatim: under a bound placement run a
    point draws only when the ruleset placed it ``point_in_polygon`` — a
    declared-level fallback, a withheld/suspect point and a conflicted pair
    never paint (K4 §3.3 / SIG-JUR-004). ``conflicting`` counts withheld
    coordinates; ``located_elsewhere_jkey`` marks a declared-here record
    whose published point sits outside this dossier (K6 V-3's second
    honesty counter).
    """
    out: list[dict[str, Any]] = []
    placed = dict(acc.placed_subjects or {})
    appearing = dict(acc.subjects or {})
    subjects = sorted(set(placed) | set(appearing))
    for subj in subjects:
        site = sites_by_id.get(subj)
        res = results_by_id.get(subj)
        in_placed = subj in placed
        sources = sorted(placed.get(subj) or appearing.get(subj) or ())
        licences = sorted(licences_by_subject.get(subj) or ())
        lat = lon = None
        conflicting = False
        if site is not None:
            draw = (
                site.latitude is not None
                and site.longitude is not None
                and res is not None
                and res.placement_basis == "point_in_polygon"
            )
            if draw:
                lat, lon = float(site.latitude), float(site.longitude)
            conflicting = bool(
                site.point_status == "conflicted" or (res is not None and res.point_withheld)
            )
        tier = int(site.sensitivity_tier) if site is not None else 3
        declared_jkey = str(res.declared_jkey) if res is not None and res.declared_jkey else None
        elsewhere = None
        if not in_placed:
            # Appearing (declared leg) but not placed here — K6's "declared
            # here, located elsewhere" counter keys on the leaf it sat in.
            leaf = str(res.jurisdiction_key) if res is not None and res.jurisdiction_key else None
            elsewhere = leaf or "unplaced"
        contested = False
        if site is not None:
            contested = bool(set(site.conflicted_predicates) - set(geo_predicates))
        out.append(
            {
                "record_id": str(subj),
                "lat": lat,
                "lon": lon,
                "tier": tier,
                "sources": sources,
                "compartment": _compartment_of(licences, compartment_of_lic),
                "declared_jkey": declared_jkey,
                "located_elsewhere_jkey": elsewhere,
                "conflicting": conflicting,
                "contested": contested,
                "provisional": False,
            }
        )
    return out


def _figure_spec_doc(
    *,
    release: Mapping[str, Any],
    info: Any,
    outline: Any,
    children: list[dict[str, Any]],
    records: list[dict[str, Any]],
    boundary_vintage: str,
) -> dict[str, Any]:
    """The ``sig.figure-kit-geo/1`` document for one dossier."""
    return {
        "schema": "sig.figure-kit-geo/1",
        "release": dict(release),
        "jurisdiction": {
            "jkey": info.jkey,
            "slug_path": info.slug_path,
            "level": info.level,
            "chain": list(info.chain),
            "name": info.name,
            "provisional": False,
        },
        "outline": [[[float(x), float(y)] for x, y in ring] for ring in (outline or ())],
        "children": children,
        "records": records,
        "boundary_vintage": boundary_vintage,
    }


def _vintage_for(jkey: str, vintages: Mapping[str, str]) -> str:
    """The pack vintage that minted this key's outline — TIGER for US rows,
    Natural Earth for non-US, the pack id when neither names it."""
    if jkey.startswith("iso3166-2:US-") or jkey.startswith("us.census."):
        return str(vintages.get("tiger") or "unknown")
    return str(vintages.get("natural_earth") or next(iter(vintages.values()), "unknown"))


def build_dossier_visuals(
    *,
    dataset: Any,
    contribution_plan: Any,
    keyed: Any,
    pages: Mapping[str, str],
    outlines_geojson: Mapping[str, Any],
    registry_rows: Mapping[str, Mapping[str, Any]],
    licences_by_subject: Mapping[str, Any],
    compartment_of_lic: Mapping[str, str],
    geo_predicates: frozenset[str],
    release: Mapping[str, Any],
    vintages: Mapping[str, str],
    placement_results: Sequence[Any] = (),
    sites_href_prefix: str = "/dossier/",
    coverage_verdicts: Mapping[str, str] | None = None,
    # P37.28 (K6 VIZ-01b): the network-figure inputs — absent, every
    # dossier's ``networks[]`` stays empty (the slot's typed not-emitted
    # state; the doc contract is unchanged).
    labels: Any = None,
    claim_rows: Sequence[Sequence[Any]] = (),
    value_claims: Sequence[Any] = (),
    relevance: Mapping[str, str] | None = None,
    relevance_fields: Mapping[str, Mapping[str, Any]] | None = None,
    ancestors: Mapping[str, tuple[str, ...]] | None = None,
    source_names: Mapping[str, str] | None = None,
    lineage: Mapping[str, str] | None = None,
    as_of: Any = None,
) -> dict[str, Any]:
    """Emit every dossier's visuals bundle — the one entry point.

    Returns ``{"docs": {jkey: doc}, "figures_twin": {jkey: [fig,…]},
    "standalone": {jkey: svg}, "locator_svg": str, "locator_index": doc,
    "coverage": doc, "report": doc}`` — the caller assigns artifact paths.
    """
    t0 = time.monotonic()
    outlines = _sm.outlines_from_geojson({str(k): v for k, v in outlines_geojson.items()})
    sites_by_id = {str(s.entity_id): s for s in dataset.sites}
    results_by_id = {str(r.record_id): r for r in placement_results}
    lexicon = _fig.load_lexicon()

    docs: dict[str, dict[str, Any]] = {}
    figures_twin: dict[str, list[dict[str, Any]]] = {}
    figures_k5: dict[str, list[dict[str, Any]]] = {}
    standalone: dict[str, str] = {}
    coverage_entries: dict[str, dict[str, Any]] = {}
    locator_parents: dict[str, Any] = {}

    # P37.28 (K6 VIZ-01b): the once-per-export family graphs the per-dossier
    # figures slice — the SAME claim sets and the same collectors'
    # semantics as the national overviews, scoped to each dossier's chain.
    net_prepared = None
    net_places: dict[str, Any] = {}
    if labels is not None and ancestors is not None:
        net_places = {
            str(jk): _dn._go.PlaceInfo(
                name=str(ki.name or jk),
                slug_path=str(ki.slug_path or ""),
                level=str(ki.level or ""),
            )
            for jk, ki in keyed.keys.items()
        }
        net_prepared = _dn.prepare(
            labels,
            claim_rows=claim_rows,
            value_claims=value_claims,
            relevance=relevance or {},
            relevance_fields=relevance_fields or {},
            places=net_places,
        )

    for jkey in sorted(pages):
        info = keyed.keys[jkey]
        acc = contribution_plan.dossiers.get(jkey)
        kids = _sm.figure_children(
            jkey, keyed=keyed, registry_rows=registry_rows, outlines=outlines
        )
        child_rows: list[dict[str, Any]] = []
        for c in kids:
            cinfo = keyed.keys.get(c)
            href = f"/dossier/{cinfo.slug_path}/" if cinfo is not None and c in pages else None
            crings = outlines.get(c) or ()
            child_rows.append(
                {
                    "jkey": c,
                    "rings": [[[float(x), float(y)] for x, y in r] for r in crings],
                    # P37.17 (D-K1-4 = yes): the real declared-scope verdict
                    # when bound; rule_pending remains the unbound posture.
                    "coverage": (coverage_verdicts or {}).get(c, "rule_pending"),
                    "href": href,
                }
            )
        records = (
            _record_inputs(
                acc,
                sites_by_id=sites_by_id,
                results_by_id=results_by_id,
                licences_by_subject=licences_by_subject,
                compartment_of_lic=compartment_of_lic,
                geo_predicates=geo_predicates,
            )
            if acc is not None
            else []
        )
        spec_doc = _figure_spec_doc(
            release=release,
            info=info,
            outline=outlines.get(jkey) or (),
            children=child_rows,
            records=records,
            boundary_vintage=_vintage_for(jkey, vintages),
        )

        locator: dict[str, Any] | None = None
        parent_key = info.parent
        parent_outline = outlines.get(parent_key) if parent_key else None
        own_outline = outlines.get(jkey) or ()
        if parent_key and parent_outline and own_outline:
            geo = _sm.locator_geometry(parent_outline, own_outline)
            locator = {
                "parent_symbol": _sm.locator_symbol_id(parent_key),
                "parent_jkey": parent_key,
                "child_d": geo["child_d"],
                "viewbox": geo["viewbox"],
            }
            locator_parents[parent_key] = parent_outline
        else:
            locator = {
                "status": "no_parent_context" if parent_key is None else "no_boundary_geometry",
                "parent_jkey": parent_key,
            }

        map_block: dict[str, Any]
        try:
            spec = spec_from_dict(spec_doc)
            result = _fig.build_map_figure(spec, lexicon)
        except FigureKitError as exc:
            # A registry key with no mintable outline emits the typed absence
            # — the honest state (SIG-ENG-042 records it; the export refuses
            # only on malformed *inputs*, which spec_from_dict already did).
            map_block = {
                "status": "no_boundary",
                "reason": str(exc),
                "records_total": len(records),
            }
            figure_meta: dict[str, Any] | None = None
            svg_text: str | None = None
        else:
            meta = result.to_json()
            map_block = dict(meta)
            map_block["svg"] = result.svg
            figure_meta = meta
            svg_text = result.svg

        coverage_entries[jkey] = {
            "sources": sorted({s for r in records for s in r["sources"]}),
            "technologies": sorted(
                {
                    str(sites_by_id[r["record_id"]].technology)
                    for r in records
                    if r["record_id"] in sites_by_id and sites_by_id[r["record_id"]].technology
                }
            ),
        }

        doc: dict[str, Any] = {
            "schema": VISUALS_SCHEMA,
            "release": dict(release),
            "jurisdiction": {
                "jkey": info.jkey,
                "slug_path": info.slug_path,
                "level": info.level,
                "chain": list(info.chain),
                "name": info.name,
            },
            "map": map_block,
            "locator": locator,
            # P37.28 (K6 VIZ-01b): the four network figures — drawn
            # bipartite SVGs (wide + narrow) or the typed absence, one
            # entry per family, never a missing slot.
            "networks": (
                _dn.entries_for(
                    jkey,
                    info,
                    net_prepared,
                    labels=labels,
                    ancestors=ancestors,
                    places=net_places,
                    pages=frozenset(pages),
                    slug_of=lambda k: keyed.keys[k].slug_path,
                    lineage=lineage or {},
                    as_of=as_of,
                    source_names=source_names or {},
                    release=release,
                    lexicon=lexicon,
                )
                if net_prepared is not None
                else []
            ),
            "timeline_items": 0,
        }
        docs[jkey] = doc

        # The published twin — metadata + caption, never geometry (K6 §9.2).
        cap = None
        if figure_meta is not None:
            drawn = figure_meta["desc"]["records_drawn"]
            total = figure_meta["desc"]["records_total"]
            no_point = figure_meta["not_drawn"]["declared_no_point"]
            nd = figure_meta["not_drawn"]
            n_elsewhere = sum(int(x["records"]) for x in nd["located_elsewhere"])
            cap = (
                f"Where SIG's published records are in {info.name}. "
                f"{drawn} of {total} published records drawn under the "
                f"{figure_meta['rule']} rule ({figure_meta['mode']}); "
                f"{no_point} have no published point, "
                f"{n_elsewhere} declared here are located elsewhere, "
                f"{nd['conflicting']} withheld as conflicting coordinates, "
                f"{nd['tier3']} at precision tier 3. Not a census — counts "
                "show what the named sources publish. "
                f"{_sm.RULE_PENDING_LEGEND}."
            )
        twin_row = {
            "figure_id": "fig-map",
            "kind": "map",
            "caption": cap,
            "caption_drafted": "agent-drafted (K6 §5.1 template, labelled — VIZ-02 binds the copy)",
            "meta": figure_meta,
            "links": {
                "sites": f"{sites_href_prefix}{info.slug_path}/sites/",
                "download": (
                    f"/figures/dossier/{info.slug_path}.svg"
                    if info.level in _STANDALONE_LEVELS
                    else None
                ),
            },
        }
        figures_twin[jkey] = [twin_row]
        # The network-figure twin rows — metadata + agent-drafted caption +
        # links, never geometry (K6 §9.2's figures[] contract).
        for _net in doc["networks"]:
            if _net.get("status") != "drawn":
                continue
            figures_twin[jkey].append(
                {
                    "figure_id": _net["figure_id"],
                    "kind": "network",
                    "caption": (
                        f"{_net['title']} in {info.name}. "
                        f"{_net['edges_drawn']} recorded relationships between "
                        f"{_net['anchors_drawn']} placed and "
                        f"{_net['counterparties_drawn']} counterparties, drawn "
                        f"as a static figure — every node links, every edge "
                        f"carries its date or 'undated'."
                    ),
                    "caption_drafted": (
                        "agent-drafted (K6 §6.1 composition, labelled — VIZ-02 binds the copy)"
                    ),
                    "meta": _net["meta"],
                    "links": {
                        "overview": f"/graphs/{_net['overview']}/",
                        "explorer": _net["explore_href"],
                        "table": _net["table_href"],
                    },
                }
            )
        figures_k5[jkey] = _dn.figures_k5_rows(doc["networks"])
        if svg_text is not None and info.level in _STANDALONE_LEVELS:
            standalone[jkey] = _fig.standalone_document(svg_text, lexicon)

    # Locator symbol sheet + index.
    if locator_parents:
        loc_svg, loc_index = _sm.build_locator_symbols(
            sorted(locator_parents.items(), key=lambda p: p[0])
        )
    else:
        loc_svg, loc_index = None, {"schema": _sm.LOCATOR_SYMBOLS_SCHEMA, "symbols": {}}

    coverage = _sm.coverage_doc(coverage_entries, release=release)

    report_rows = []
    for jkey in sorted(docs):
        payload = canonical_json(docs[jkey])
        gz = len(gzip.compress(payload, compresslevel=9, mtime=0))
        m = docs[jkey]["map"]
        report_rows.append(
            {
                "jkey": jkey,
                "slug_path": keyed.keys[jkey].slug_path,
                "path": f"{VISUALS_DIR}/{keyed.keys[jkey].slug_path}.json",
                "bytes": len(payload),
                "gzip_bytes": gz,
                "mode": m.get("mode") or m.get("status"),
                "cap_actions": m.get("cap_actions", []),
            }
        )
    report = {
        "schema": VISUALS_INDEX_SCHEMA,
        "release": dict(release),
        "wall_seconds": round(time.monotonic() - t0, 3),
        "dossier_figures": len(report_rows),
        "standalone_svgs": len(standalone),
        "locator_parent_symbols": len(locator_parents),
        "rows": report_rows,
        "note": (
            "VIZ-01a size/time report — measured per emission; the same "
            "measurement rides the real release (US/GA/TX/CA/DC-scale rows)."
        ),
    }
    return {
        "docs": docs,
        "figures_twin": figures_twin,
        "figures_k5": figures_k5,
        "standalone": standalone,
        "locator_svg": loc_svg,
        "locator_index": loc_index,
        "coverage": coverage,
        "report": report,
    }


def visuals_bytes(doc: Mapping[str, Any]) -> bytes:
    """Deterministic restricted-artifact bytes for one visuals doc."""
    return canonical_json(doc)


def digest_of(data: bytes) -> str:
    return sha256_hex(data)


__all__ = [
    "COVERAGE_PATH",
    "LOCATOR_INDEX_PATH",
    "LOCATOR_SVG_PATH",
    "STANDALONE_DIR",
    "VISUALS_DIR",
    "VISUALS_INDEX_SCHEMA",
    "VISUALS_SCHEMA",
    "build_dossier_visuals",
    "digest_of",
    "visuals_bytes",
]
