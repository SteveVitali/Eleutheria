# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.map-dict/1`` map dictionary + the real coverage rule (P37.17,
K1-map §3.3/§3.6/§7, MAP-01b, ADR-241).

``web/map/dict.json`` is the public map's field dictionary: the indices the
short tile keys resolve through (``sr`` → ``sources[]``, ``tc`` →
``technologies[]``, ``vd`` → ``vendor_slots[]``), the jurisdiction chains +
bboxes for every ``j``/``jp`` key in use, the per-jurisdiction unplotted
counts (tier 3 + no published point) and the national facet totals. SIG
metadata — CC-BY-4.0 — never upstream data strings pooled across licences.

``web/map/coverage_by_jurisdiction.json`` carries the **real** rule
(``declared-scope@1``) now that D-K1-4 [B-22] is answered *yes*: a source
covers the jurisdictions in its declared ``sources.toml`` scope
(``jurisdiction_scheme`` + ``jurisdiction``); a global crowdsourced source
(OSM/DeFlock — ``publisher_type = "crowdsourced"`` with no declared scope) is
listed in ``observed_sources`` but never counts as "SIG has looked". Counts
in single-source cells are shown with their "1 source" label, never
suppressed (D-K1-4 (a)) — the cells' ``s1`` facet carries them.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .jurisdictions import CONNECTOR_DATA_DIR

#: The emitted document ids.
MAP_DICT_SCHEMA = "sig.map-dict/1"
COVERAGE_RULE_VERSION = "declared-scope@1"
#: The UXR-14 interim legend line — corroboration counts registry sources
#: until L3 CONF-07b ships ``n_independent_lineages`` (verbatim).
CORROBORATION_LEGEND = "2+ source records; republications not yet collapsed"
COVERAGE_LEGEND = (
    "Where SIG has looked: a source counts where it declares coverage; "
    "global crowdsourced sources (OSM, DeFlock) are listed but do not count"
)
MAP_DICT_PATH = "web/map/dict.json"

_ONTOLOGY_VOCAB = (
    Path(__file__).resolve().parents[4] / "ontology" / "vocab" / "technology.yaml"
)

#: ``jurisdiction_scheme`` → the canonical K4 jkey prefix.
_SCHEME_PREFIX = {
    "iso.3166_1": "iso3166-1:",
    "iso.3166_2": "iso3166-2:",
    "us.census.geoid.county": "us.census.geoid.county:",
    "us.census.geoid.place": "us.census.geoid.place:",
}


def technology_codes(vocab_path: Path | None = None) -> dict[str, int]:
    """The deterministic technology code map: slug → ``tc`` int.

    Codes assign in the committed ``ontology/vocab/technology.yaml`` order
    over ACTIVE slugs (a ``status: retired`` entry is skipped — a retired
    slug resolves through ``superseded_by`` upstream), code 0 = unclassified.
    The YAML is parsed with a minimal line scan (no PyYAML dependency): each
    ``- slug:`` line opens an entry; ``status: retired`` before the next slug
    marks it retired.
    """
    path = vocab_path or _ONTOLOGY_VOCAB
    codes: dict[str, int] = {}
    tech_indent: int | None = None
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if re.match(r"technologies:\s*$", stripped):
            tech_indent = indent
            continue
        if (
            tech_indent is not None
            and stripped
            and indent <= tech_indent
            and not stripped.startswith("-")
        ):
            tech_indent = None  # left the technologies: block
            current = None
        m = re.match(r"-\s*slug:\s*([a-z0-9-]+)\s*$", stripped)
        if m:
            if tech_indent is None:
                current = None
                continue  # domain/family slugs never carry a tc code
            current = m.group(1)
            if current not in codes:
                codes[current] = len(codes) + 1  # tentative — retired revokes
            continue
        # ``status: retired`` trails its slug inside the same entry — revoke
        # the tentative code so the gap never ships (superseded_by stands).
        if tech_indent is not None and re.match(r"status:\s*retired\s*$", stripped) and current:
            codes.pop(current, None)
            current = None
    return codes


def _source_scope(row: Mapping[str, Any]) -> str | None:
    """A source row's declared jurisdiction scope as a K4 jkey (or None)."""
    scheme = str(row.get("jurisdiction_scheme") or "")
    value = str(row.get("jurisdiction") or "")
    prefix = _SCHEME_PREFIX.get(scheme)
    if not prefix or not value:
        return None
    return f"{prefix}{value}"


def load_source_registry_sources(data_dir: Path | None = None) -> dict[str, Mapping[str, Any]]:
    """The committed ``sources.toml`` rows keyed by source id (read-only)."""
    root = Path(data_dir) if data_dir is not None else CONNECTOR_DATA_DIR
    doc = tomllib.loads((root / "sources.toml").read_text(encoding="utf-8"))
    return {str(k): v for k, v in (doc.get("sources") or {}).items()}


def declared_scopes(
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """``source_id → declared jkey`` for sources with a declared scope."""
    out: dict[str, str] = {}
    for sid, row in sources.items():
        jk = _source_scope(row)
        if jk:
            out[sid] = jk
    return out


def crowdsourced_globals(sources: Mapping[str, Mapping[str, Any]]) -> set[str]:
    """Sources that never count as "looked" (D-K1-4 (b)): declared
    ``publisher_type = "crowdsourced"`` OR no declared scope at all."""
    out: set[str] = set()
    for sid, row in sources.items():
        if str(row.get("publisher_type") or "") == "crowdsourced" or not _source_scope(row):
            out.add(sid)
    return out


def coverage_doc(
    observed: Mapping[str, Mapping[str, Any]],
    *,
    release: Mapping[str, Any],
    scopes: Mapping[str, str],
    global_sources: set[str],
    ancestors: Mapping[str, Sequence[str]],
    all_jkeys: Sequence[str],
) -> dict[str, Any]:
    """``web/map/coverage_by_jurisdiction.json`` — the real declared-scope rule.

    ``observed`` is ``jkey → {sources, technologies}`` (the records the
    release actually publishes there). ``scopes`` maps a source id to its
    declared jkey; ``ancestors`` maps a jkey to its root-first chain.
    A jkey is ``covered`` when at least one scoped source's declared key is
    the jkey itself or one of its ancestors — the declared scope covers the
    place and everything inside it.
    """
    covering: dict[str, list[str]] = {str(k): [] for k in all_jkeys}
    all_set = set(str(k) for k in all_jkeys)
    for sid, declared in sorted(scopes.items()):
        for jkey in all_set:
            chain = {jkey, *ancestors.get(jkey, ())}
            if declared in chain:
                covering[jkey].append(sid)
    rows: dict[str, Any] = {}
    for jkey in sorted(all_set):
        obs = observed.get(jkey) or {}
        obs_sources = sorted(str(s) for s in obs.get("sources") or ())
        rows[jkey] = {
            "sources": covering[jkey],
            "observed_sources": obs_sources,
            "global_sources_not_counted": [s for s in obs_sources if s in global_sources],
            "technologies": sorted(str(t) for t in obs.get("technologies") or ()),
            "basis": "declared_scope",
            "coverage": "covered" if covering[jkey] else "not_covered",
        }
    return {
        "schema": "sig.jurisdiction-coverage/1",
        "release": dict(release),
        "rule_version": COVERAGE_RULE_VERSION,
        "rule_decision": "D-K1-4",
        "pending": False,
        "legend": COVERAGE_LEGEND,
        "corroboration_legend": CORROBORATION_LEGEND,
        "jurisdictions": rows,
    }


def build_map_dict(
    slice_rows: Sequence[Mapping[str, Any]],
    *,
    release: Mapping[str, Any],
    source_names: Mapping[str, str],
    registry_sources: Mapping[str, Mapping[str, Any]],
    tech_codes: Mapping[str, int],
    vendor_slots: Mapping[str, int],
    vendor_labels: Mapping[str, str],
    jurisdictions: Mapping[str, Mapping[str, Any]],
    ancestor_chains: Mapping[str, Sequence[str]],
) -> tuple[dict[str, Any], dict[tuple[str, str], int]]:
    """The ``sig.map-dict/1`` document over the release's emitted site rows.

    ``slice_rows`` are the per-compartment sites rows (``_site_row_data``
    dicts plus a ``_compartment`` marker) — the same rows the tiles reduce.
    ``jurisdictions`` is the registry's ``jkey → row`` for every key in use;
    ``ancestor_chains`` the registry's root-first chains. Returns
    ``(document, source_index)`` — ``source_index`` maps
    ``(source_id, compartment) → sr`` for the tile emit.
    """
    # Sources: one entry per (source_id, compartment) pair seen in the rows.
    pairs: set[tuple[str, str, str]] = set()  # (source_id, compartment, spdx)
    for row in slice_rows:
        sid = str(row.get("source_id") or "")
        if not sid:
            continue
        pairs.add((sid, str(row.get("_compartment") or ""), str(row.get("spdx") or "")))
    sources: list[dict[str, Any]] = []
    source_index: dict[tuple[str, str], int] = {}
    for i, (sid, comp, spdx) in enumerate(sorted(pairs)):
        reg = registry_sources.get(sid) or {}
        sources.append(
            {
                "index": i,
                "id": sid,
                "name": source_names.get(sid) or reg.get("name") or sid,
                "publisher": reg.get("name") or None,
                "publisher_type": reg.get("publisher_type") or None,
                "licence": spdx or None,
                "compartment": comp or None,
                "url": f"/sources/{sid}/",
            }
        )
        source_index[(sid, comp)] = i

    technologies = [
        {"code": code, "slug": slug, "label": slug.replace("-", " ")}
        for slug, code in sorted(tech_codes.items(), key=lambda kv: kv[1])
    ]
    vendors = [
        {
            "slot": slot,
            "key": key,
            "label": vendor_labels.get(key) or key,
        }
        for key, slot in sorted(vendor_slots.items(), key=lambda kv: kv[1])
        if slot > 0
    ]

    used: set[str] = set()
    for row in slice_rows:
        for fld in ("jurisdiction_key", "jurisdiction"):
            v = row.get(fld)
            if isinstance(v, str) and v:
                used.add(v)
    jdocs: dict[str, Any] = {}
    for jkey in sorted(used):
        row = jurisdictions.get(jkey)
        if row is None:
            continue
        jdocs[jkey] = {
            "name": row.get("name"),
            "level": row.get("level"),
            "chain": list(ancestor_chains.get(jkey, ())) + [jkey],
            "bbox": row.get("bbox"),
        }

    unplotted: dict[str, int] = {}
    by_tech: dict[str, int] = {}
    by_vend: dict[str, int] = {}
    for row in slice_rows:
        jk = row.get("jurisdiction_key") or row.get("jurisdiction") or "unplaced"
        jkey = str(jk)
        tier = row.get("tier", row.get("sensitivity_tier", 0))
        if row.get("geometry") is None or int(tier or 0) == 3:
            unplotted[jkey] = unplotted.get(jkey, 0) + 1
        tech = row.get("technology")
        if tech:
            by_tech[str(tech)] = by_tech.get(str(tech), 0) + 1
        vkey = row.get("vendor_key")
        if vkey:
            by_vend[str(vendor_slots.get(str(vkey), 9))] = (
                by_vend.get(str(vendor_slots.get(str(vkey), 9)), 0) + 1
            )
    totals: dict[str, Any] = {
        # row-level measured counts (a record sliced by N sources counts N
        # times — the facet totals the filters sum against, never a census)
        "slice_rows": len(slice_rows),
        "by_technology": dict(sorted(by_tech.items())),
        "by_vendor_slot": dict(sorted(by_vend.items())),
        "unplotted_rows": sum(unplotted.values()),
    }
    return (
        {
            "schema": MAP_DICT_SCHEMA,
            "release": dict(release),
            "contract": "sig.map-tiles/2",
            "corroboration_legend": CORROBORATION_LEGEND,
            "sources": sources,
            "technologies": technologies,
            "vendor_slots": vendors,
            "jurisdictions": jdocs,
            "unplotted": dict(sorted(unplotted.items())),
            "totals": totals,
        },
        source_index,
    )


def vendor_slot_map(
    vendor_counts: Mapping[str, int],
    *,
    top_max: int = 8,
) -> dict[str, int]:
    """``vendor_key → vd slot``: the top ``top_max`` vendors by record count
    (ties → lexical) take slots 1..``top_max``; every other named vendor is 9
    ("other"); the unknown/absent vendor is 0 — never emitted in the map."""
    ranked = sorted(vendor_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out: dict[str, int] = {}
    for i, (key, _count) in enumerate(ranked[:top_max]):
        out[key] = i + 1
    for key, _count in ranked[top_max:]:
        out.setdefault(key, 9)
    return out


__all__ = [
    "CONNECTOR_DATA_DIR",
    "CORROBORATION_LEGEND",
    "COVERAGE_LEGEND",
    "COVERAGE_RULE_VERSION",
    "MAP_DICT_PATH",
    "MAP_DICT_SCHEMA",
    "build_map_dict",
    "coverage_doc",
    "crowdsourced_globals",
    "declared_scopes",
    "load_source_registry_sources",
    "technology_codes",
    "vendor_slot_map",
]
