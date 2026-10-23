# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.45 — canonical dossier keys, slug paths, and the D-K4-3 page set.

This module is the single derivation of everything a dossier *is* under the
post-P35.19 placement model (K4 §5.2):

* **group_by_key** — a record belongs to the dossier of every key on its
  recorded ``placement@1`` ``jurisdiction_chain`` (the placed leg), plus the
  declared bucket's dossier when the declaration disagrees (the disclosed
  leg). Ancestry is *never* re-derived here — the chain the engine emitted
  is the only input.
* **slug paths** — a dossier's URL segment chain mirrors the canonical
  chain: ``usa``, ``usa/ca``, ``usa/ca/verdin-county-06037``,
  ``gbr/eng``. Multi-segment slugs are scoped by their ancestors, so two
  counties sharing a NAMELSAD under different states never collide.
* **page thresholds (D-K4-3, applied verbatim)** — every county with ≥1
  record; US places with ≥10 records *or* any non-site evidence; every
  US admin-1 (incl. PR/VI state-equivalents under ``iso3166-1:US``, D-K4-4);
  non-US admin-1 with ≥10 records; every country with ≥1 record.
* **the ``unplaced`` sentinel** — records with no chain get the honest
  ``unplaced`` report key. "Not yet placed" is a *data-quality state*,
  never a place: it is excluded from jurisdiction counts and place
  facets, and it is not a registry row.

The module is pure — no I/O, no DuckDB — so fixtures and unit tests drive
it directly. ``PlacementEngine.jurisdiction_rows()`` supplies the registry
rows; a test stand-in only needs that accessor and ``ancestor_chain``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .jurisdictions import jurisdiction_slug

# --------------------------------------------------------------------------- #
# Vocabulary                                                                  #
# --------------------------------------------------------------------------- #

#: The unplaced report's sentinel key. Chosen so it can never collide with a
#: registry slug path (every registry segment derives from a code or a
#: NAMELSAD+GEOID, and no top segment is a bare dictionary word other than a
#: lowercase ISO-3 country code). It names a *state of the data*, not a
#: place — see K4 §5.2 "unplaced/ is a data-quality report, not a place".
UNPLACED = "unplaced"

#: The legacy sentinel the pre-P35.45 flat buckets emitted. Old release trees
#: keep their ``unresolved/`` pages readable; the new world writes
#: ``unplaced/`` only (the history artifact carries the rename).
LEGACY_UNRESOLVED = "unresolved"

#: D-K4-3's applied thresholds, carried verbatim — the dossier artifact
#: records WHICH rule minted the page, never a re-decided threshold.
THRESHOLD_COUNTY = "D-K4-3: every US county with at least one record"
THRESHOLD_US_PLACE_RECORDS = "D-K4-3: US places with at least 10 records"
THRESHOLD_US_PLACE_NONSITE = "D-K4-3: any US place with non-site evidence"
THRESHOLD_US_ADMIN1 = (
    "D-K4-3 level table: every US state or state-equivalent with at least "
    "one record (territories sit under iso3166-1:US — D-K4-4)"
)
THRESHOLD_NON_US_ADMIN1 = "D-K4-3: non-US admin-1 jurisdictions with at least 10 records"
THRESHOLD_COUNTRY = "D-K4-3 level table: every country with at least one record"

_US_PLACE_MIN_RECORDS = 10
_NON_US_ADMIN1_MIN_RECORDS = 10


# --------------------------------------------------------------------------- #
# The keyed dossier descriptor                                                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class KeyedJurisdiction:
    """One canonical registry row dressed for dossier duty.

    Everything a dossier page, index row, or key-map entry needs — derived
    once from the registry row plus the engine's recorded ancestor chain.
    ``records``/``page`` are NOT here: membership is the contribution plan's
    job (``dossier_sources``); eligibility is :func:`page_basis`.
    """

    jkey: str
    level: str
    name: str
    parent: str | None
    #: Root-first canonical chain ending at ``jkey`` — the engine's record,
    #: never re-derived.
    chain: tuple[str, ...]
    #: The dossier URL path, e.g. ``usa/ca/verdin-county-06037``.
    slug_path: str
    #: The chain's root key (the country dossier this sits under).
    country_jkey: str | None
    #: ISO 3166-1 alpha-2 of the chain root — the ``jurisdictionCode`` wire
    #: value (D-K4-7: always the COUNTRY's alpha-2, never the leaf code).
    country_a2: str | None
    #: The row's canonical identifier code (``US-CA``, ``06037``, ``GB-ENG``…)
    #: — shown secondary beside the name, never in place of it.
    code: str | None
    #: The canonical identifier's scheme (``iso3166-2``,
    #: ``us.census.geoid.county``…).
    scheme: str | None
    vintage: str | None
    note: str | None = None
    #: Registry alternates — the lookup@1 surface (name display only).
    alternates: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class KeyedRegistry:
    """The registry dressed for dossier duty: per-key descriptors, the
    ``jkey → slug_path`` map, children-by-parent, and the unplaced sentinel."""

    keys: dict[str, KeyedJurisdiction]
    #: ``parent jkey -> sorted child jkeys`` (registry parentage — never
    #: inferred from slug strings).
    children: dict[str | None, tuple[str, ...]]
    #: ``slug_path -> jkey`` — the exact inverse of ``KeyedJurisdiction.slug_path``;
    #: a collision (two keys minting one path) would be a naming bug, so this
    #: map is asserted complete at build time.
    by_slug_path: dict[str, str]

    def info(self, jkey: str) -> KeyedJurisdiction | None:
        return self.keys.get(jkey)

    def slug_path(self, jkey: str) -> str | None:
        info = self.keys.get(jkey)
        return info.slug_path if info is not None else None

    def display_name(self, jkey: str) -> str:
        """``"California, United States"``-style — name with the ancestor
        names appended (skipping repeats), so a county page title carries
        its state and country without re-querying."""
        info = self.keys.get(jkey)
        if info is None:
            return jkey
        parts = [info.name]
        seen = {info.name}
        # Nearest-first: the chain is root-first, so a county page reads
        # "Los Angeles County, California, United States".
        for anc in reversed(info.chain[:-1]):
            row = self.keys.get(anc)
            if row is not None and row.name not in seen:
                seen.add(row.name)
                parts.append(row.name)
        return ", ".join(parts)


# --------------------------------------------------------------------------- #
# Registry → keyed descriptors                                                #
# --------------------------------------------------------------------------- #


def _canonical_identifier(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """``(code, scheme)`` of the row's canonical identifier — the pair the
    page shows as "Code · Scheme" beneath the name."""
    for ident in row.get("identifiers") or []:
        if ident.get("kind") == "canonical":
            return (
                str(ident.get("value") or "") or None,
                str(ident.get("scheme") or "") or None,
            )
    return None, None


def _identifier_value(row: Mapping[str, Any], scheme: str) -> str | None:
    for ident in row.get("identifiers") or []:
        if str(ident.get("scheme") or "") == scheme:
            return str(ident.get("value") or "") or None
    return None


def _country_a2_of(jkey: str) -> str | None:
    """The ISO alpha-2 a ``iso3166-1:<A2>`` key encodes (D-K4-7)."""
    m = re.fullmatch(r"iso3166-1:([A-Z0-9]{2})", jkey)
    return m.group(1) if m else None


def _country_segment(row: Mapping[str, Any]) -> str:
    """The country path segment: lowercase ISO-3 (``usa``), falling back to
    alpha-2 (``xk``), then the slugged key — never an invented name."""
    a3 = _identifier_value(row, "iso3166-1-a3")
    if a3:
        return a3.lower()
    a2 = _country_a2_of(str(row.get("jkey") or ""))
    if a2:
        return a2.lower()
    return jurisdiction_slug(str(row.get("jkey") or ""))


def _code_of(jkey: str, row_code: str | None) -> str:
    """The canonical code a path segment derives from — the registry row's
    ``canonical`` identifier value when it exists, else the jkey's own
    scheme suffix (``iso3166-2:US-CA`` → ``US-CA``). Registry rows minted
    under a national scheme (``us.usps``…) carry no iso3166-2 canonical
    identifier even though the KEY encodes one — the jkey is the record."""
    if row_code:
        return row_code
    return jkey.split(":", 1)[1] if ":" in jkey else jkey


def _admin1_segment(jkey: str, code: str | None) -> str:
    """``US-CA``/``GB-ENG`` → ``ca``/``eng`` — the code part, lower-cased."""
    c = _code_of(jkey, code)
    if "-" in c:
        return c.split("-", 1)[1].lower()
    return jurisdiction_slug(c)


def _slug_path(
    jkey: str,
    rows: Mapping[str, Mapping[str, Any]],
    chains: Mapping[str, tuple[str, ...]],
) -> str:
    """The K4 §5.2 URL path for one registry key — derived from the chain,
    never from the raw key string alone (chain segments carry the scope)."""
    chain = chains.get(jkey)
    if not chain or chain[-1] != jkey:
        # No recorded chain → fall back to the parent-walk the registry
        # already verifies (jurisdictions._ancestors): same root-first order.
        path: list[str] = []
        cur: str | None = jkey
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            path.append(cur)
            cur = str(rows.get(cur, {}).get("parent") or "") or None
        chain = tuple(reversed(path)) or (jkey,)
    segments: list[str] = []
    for i, anc in enumerate(chain):
        row = rows.get(anc)
        if row is None:
            segments.append(jurisdiction_slug(anc))
            continue
        level = str(row.get("level") or "")
        code, _scheme = _canonical_identifier(row)
        if i == 0:
            segments.append(_country_segment(row))
        elif level == "state_province":
            segments.append(_admin1_segment(anc, code))
        elif level in ("county", "municipality"):
            name_seg = jurisdiction_slug(str(row.get("name") or anc))
            geoid = jurisdiction_slug(_code_of(anc, code))
            segments.append(f"{name_seg}-{geoid}")
        else:
            # National-scheme or future level: the canonical code's slug.
            segments.append(jurisdiction_slug(code or anc))
    return "/".join(segments)


def keyed_registry(
    rows: Sequence[Mapping[str, Any]],
    chains: Mapping[str, tuple[str, ...]] | None = None,
) -> KeyedRegistry:
    """Dress every registry row for dossier duty.

    ``chains`` is the engine's recorded ancestor map (``ancestor_chain`` per
    key); absent, the registry's own verified parentage supplies the chain —
    same root-first shape. Either way ancestry is *read*, never invented.
    """
    by_jkey: dict[str, Mapping[str, Any]] = {str(r["jkey"]): r for r in rows}
    chain_map: dict[str, tuple[str, ...]] = {}
    if chains is not None:
        chain_map = {str(k): tuple(v) for k, v in chains.items()}
    else:
        for jkey in by_jkey:
            path: list[str] = []
            cur: str | None = jkey
            seen: set[str] = set()
            while cur and cur not in seen:
                seen.add(cur)
                path.append(cur)
                cur = str(by_jkey.get(cur, {}).get("parent") or "") or None
            chain_map[jkey] = tuple(reversed(path))
    children: dict[str | None, list[str]] = {}
    keys: dict[str, KeyedJurisdiction] = {}
    for jkey, row in sorted(by_jkey.items()):
        code, scheme = _canonical_identifier(row)
        chain = chain_map.get(jkey, (jkey,))
        parent = str(row.get("parent") or "") or None
        country_jkey = chain[0] if chain else None
        keys[jkey] = KeyedJurisdiction(
            jkey=jkey,
            level=str(row.get("level") or ""),
            name=str(row.get("name") or jkey),
            parent=parent,
            chain=chain,
            slug_path=_slug_path(jkey, by_jkey, chain_map),
            country_jkey=country_jkey,
            country_a2=_country_a2_of(country_jkey or ""),
            code=code,
            scheme=scheme,
            vintage=str(row.get("vintage") or "") or None,
            note=str(row.get("note") or "") or None,
            alternates=tuple(str(a) for a in row.get("alternates") or ()),
        )
        children.setdefault(parent, []).append(jkey)
    by_slug: dict[str, str] = {}
    for jkey, info in keys.items():
        prior = by_slug.get(info.slug_path)
        if prior is not None:
            raise ValueError(
                f"slug-path collision: {jkey!r} and {prior!r} both mint "
                f"{info.slug_path!r} — the registry named two places one path"
            )
        by_slug[info.slug_path] = jkey
    return KeyedRegistry(
        keys=keys,
        children={p: tuple(sorted(c)) for p, c in children.items()},
        by_slug_path=by_slug,
    )


# --------------------------------------------------------------------------- #
# D-K4-3 page thresholds — applied, never re-decided                          #
# --------------------------------------------------------------------------- #


def page_basis(
    info: KeyedJurisdiction,
    *,
    placed_records: int,
    has_non_site_evidence: bool = False,
) -> str | None:
    """The verbatim D-K4-3 basis minting this key's dossier page — or
    ``None`` when no page is emitted (below threshold). Every returned
    string is the decision text carried into the artifact.

    * ``country`` — every country with ≥1 placed record.
    * ``state_province`` — every US admin-1 (incl. PR/VI under
      ``iso3166-1:US``, D-K4-4) with ≥1; non-US admin-1 needs ≥10.
    * ``county`` — every US county with ≥1 (non-US counties fall under
      their national scheme's row and share the admin-1 sub-country rule:
      no page below the records threshold for their parent scheme — today
      only US Census counties mint county rows).
    * ``municipality`` — US places with ≥10 records, OR any US place with
      non-site evidence (research-dossier/agenda/CCOPS/city-scoped claims).
    """
    if placed_records < 1 and not (info.level == "municipality" and has_non_site_evidence):
        return None
    if info.level == "country":
        return THRESHOLD_COUNTRY
    if info.level == "state_province":
        if info.country_jkey == "iso3166-1:US":
            return THRESHOLD_US_ADMIN1
        return THRESHOLD_NON_US_ADMIN1 if placed_records >= _NON_US_ADMIN1_MIN_RECORDS else None
    if info.level == "county":
        return THRESHOLD_COUNTY
    if info.level == "municipality":
        if has_non_site_evidence:
            return THRESHOLD_US_PLACE_NONSITE
        return THRESHOLD_US_PLACE_RECORDS if placed_records >= _US_PLACE_MIN_RECORDS else None
    # National-scheme sub-country rows share the non-US admin-1 threshold —
    # a minted page needs the same evidence depth an admin-1 does.
    return THRESHOLD_NON_US_ADMIN1 if placed_records >= _NON_US_ADMIN1_MIN_RECORDS else None


def page_keys(
    reg: KeyedRegistry,
    placed_counts: Mapping[str, int],
    non_site_keys: frozenset[str] | set[str] = frozenset(),
) -> dict[str, str]:
    """``{jkey: verbatim basis}`` for every key whose page mints under
    D-K4-3 — the applied decision table, deterministic (key-sorted)."""
    out: dict[str, str] = {}
    for jkey, info in reg.keys.items():
        basis = page_basis(
            info,
            placed_records=placed_counts.get(jkey, 0),
            has_non_site_evidence=jkey in non_site_keys,
        )
        if basis is not None:
            out[jkey] = basis
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------- #
# group_by_key — the membership derivation                                    #
# --------------------------------------------------------------------------- #


def group_by_key(row: Mapping[str, Any]) -> tuple[frozenset[str], frozenset[str], str | None]:
    """One site row's dossier membership under the placement model.

    Returns ``(placed_keys, declared_keys, leaf_key)``:

    * ``placed_keys`` — every key on the row's recorded
      ``jurisdiction_chain`` (root-first; the leaf included). A chain-less
      row carries ``{UNPLACED}`` — the honest report, never a guessed home.
    * ``declared_keys`` — the row's declared bucket ``{declared}`` when it
      names a real key AND differs from the chain leaf: the disagreement
      keeps both sides visible (K4 §5.2's "declared elsewhere" view).
      ``unresolved``/empty declarations mint nothing.
    * ``leaf_key`` — ``jurisdiction_key`` when set (the deepest placed
      level), else ``None``.
    """
    chain = [str(k) for k in row.get("jurisdiction_chain") or () if k]
    leaf = str(row.get("jurisdiction_key") or "") or None
    placed = frozenset(chain) if chain else frozenset({UNPLACED})
    declared_raw = str(row.get("jurisdiction") or "").strip()
    declared: set[str] = set()
    if declared_raw and declared_raw not in {
        UNPLACED,
        LEGACY_UNRESOLVED,
        "(unasserted)",
        "(conflicted)",
    }:
        declared.add(declared_raw)
    return placed, frozenset(declared), leaf


__all__ = [
    "UNPLACED",
    "LEGACY_UNRESOLVED",
    "KeyedJurisdiction",
    "KeyedRegistry",
    "THRESHOLD_COUNTRY",
    "THRESHOLD_COUNTY",
    "THRESHOLD_NON_US_ADMIN1",
    "THRESHOLD_US_ADMIN1",
    "THRESHOLD_US_PLACE_NONSITE",
    "THRESHOLD_US_PLACE_RECORDS",
    "group_by_key",
    "keyed_registry",
    "page_basis",
    "page_keys",
]
