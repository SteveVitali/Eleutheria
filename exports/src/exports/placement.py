# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``placement@1`` engine — export-time jurisdiction placement (JUR-02b,
P35.19, K4 §3.3, ADR-092 compute-on-read).

Every released record is placed by a versioned, recorded rule over the
**verified** boundary pack + jurisdiction registry staged as export inputs
(P35.17). The located point wins (R4); suspected axis swaps/sign flips/null-
island points fall back to the declared jurisdiction and are flagged (R3/R5);
a record with no place is a *quality state* with a closed reason vocabulary,
never a hidden bucket (K4-P4). Nothing is written back to the spine — the
engine reads the pack's GeoParquet into a private in-memory DuckDB, evaluates
R1–R8 deterministically, and returns per-record :class:`PlacementResult`
objects the export stamps as the seven additive columns
(K4 §5.3: ``jurisdiction_key``/``jurisdiction_chain``/``placement_basis``/
``placement_check``/``declared_scheme``/``declared_value``/
``boundary_vintage``) plus the record ``jurisdiction`` block (K4 §3.4).

Fail-closed postures (K4 §4.4): the pack must pass
:func:`boundary_pack.verify_pack`, the registry must bind the same
``boundaries_root`` + vintages, DuckDB ``spatial`` is loaded with a strict
``LOAD`` (never a runtime ``INSTALL`` — the extension is baked into the
export image), and a level whose containment answer is ambiguous on a
multi-candidate boundary reports deterministically via the lowest-code
tie-break (K4 §3.3 "Tie-breaks"), never a guessed winner. Landed
``geometry_defect`` claims (P35.16 / PKG-06b) are consumed as inputs when
present; when absent the engine's own variant checks apply.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .boundary_pack import BoundaryPackError, load_spec, read_manifest, verify_pack
from .jurisdictions import (
    LEVELS,
    REGISTRY_SCHEMA,
    country_jkey,
    jurisdiction_key,
    lookup,
    read_registry,
    valid_jkey,
)

if TYPE_CHECKING:
    from .shaping import ShapedSite, ShapingClaim

#: The versioned placement ruleset (K4 §3.3; D-K4-5 ratifies the precedence).
PLACEMENT_RULESET = "placement@1"

#: The machine-readable quality report this module emits per export.
PLACEMENT_REPORT_SCHEMA = "sig.placement-report/1"

#: NE 10m coast tolerance in degrees (K4 §3.3 R2 — "NE + 0.02° tolerance
#: elsewhere"). Applied ONLY to layers the spec declares ``non_us``-roled;
#: TIGER/Line is full-resolution and needs none.
NE_TOLERANCE_DEG = 0.02

#: R1 point-rejection reasons (K4 §3.3 R1) — a closed pair.
REJECT_REASONS: tuple[str, ...] = ("null_island", "invalid_point")

#: The closed ``placement_check`` vocabulary (ticket 299 §5 + K4 §3.3). Every
#: emitted check is a member, or ``point_rejected:<r>`` for ``r`` in
#: :data:`REJECT_REASONS`. Public validators + the quality report read this
#: tuple — there is no second vocabulary to drift from.
PLACEMENT_CHECKS: tuple[str, ...] = (
    "consistent",  # R2 — located chain consistent with (or free of) declared
    "on_boundary",  # tie-break applied (lowest GEOID/code) on a shared boundary
    "outside_declared",  # R4 — located wins, same country
    "outside_declared_country",  # R4 — located wins, across a country border
    "axis_swap_suspected",  # R3 — swapped variant inside declared; point withheld
    "sign_flip_suspected",  # R3 — sign-flipped variant inside declared; withheld
    "no_point",  # R5 — no usable point; declared level only
    "coordinates_conflicted",  # R5 — envelope conflicted; declared level only
    "point_rejected:null_island",  # R5 after R1 — (0,0); declared level only
    "point_rejected:invalid_point",  # R5 after R1 — out of range
    "outside_all_boundaries",  # R6 — point in no boundary beyond tolerance
    "no_location_evidence",  # R7 — nothing declared, no usable point
    "name_unmatched",  # R8 — I8 lookup miss
    "name_ambiguous",  # R8 — I8 lookup ambiguity (never a guess)
    "not_evaluated",  # partial depth — deeper levels were never evaluated
    "null_island",  # R1 rejection, unplaced (nothing declared to fall back to)
    "invalid_point",  # R1 rejection, unplaced
)

#: ``placement_basis`` values (K4 §3.3). ``name_lookup`` covers the R8 hit
#: path (the R-table pins the miss vocabulary; a successful lookup still
#: names its rule honestly).
PLACEMENT_BASIS: tuple[str, ...] = ("point_in_polygon", "declared", "name_lookup")

#: Landed ``geometry_defect`` classes (P35.16 / PKG-06b) the engine consumes
#: when a detector claim exists on the subject (the S2 sequence edge).
#: ``axis_swap``/``sign_flip`` mark the point suspect without re-testing the
#: variant; ``null_island`` rejects the point; ``wrong_jurisdiction`` leaves
#: the point usable (its verdict is the located-wins R4 posture itself).
_DEFECT_SUSPECT: Mapping[str, str] = {
    "axis_swap": "axis_swap_suspected",
    "sign_flip": "sign_flip_suspected",
}
_DEFECT_REJECT = "null_island"
_DEFECT_KNOWN: frozenset[str] = frozenset({*_DEFECT_SUSPECT, _DEFECT_REJECT, "wrong_jurisdiction"})

#: Level depth order (K4 §3.3 R6 chain: country → admin-1 → county → place)
#: is the registry's ``LEVELS`` tuple — the chain walks it in order.


class PlacementError(Exception):
    """A placement input is missing, unverified, or inconsistent — refuse."""


@dataclass(frozen=True)
class PlacementInput:
    """One record's placement inputs — a shaped site row's evidence view.

    ``lat``/``lon`` are the record's own resolved coordinate pair (None when
    the envelope found no usable pair); ``point_status`` the envelope verdict
    (``resolved``/``conflicted``/``unreported``); ``precision`` the declared
    geometry precision (SIG-IDENT-004 — ``organization_centroid_or_unknown``
    is never point-placed); ``declared`` the scheme-qualified pair the
    record's jurisdiction claim carries (``(scheme, value)``, None when the
    declaration is absent or a legacy bare value — never guessed);
    ``defect_flags`` the landed ``geometry_defect`` classes on the subject;
    ``name`` a non-site record's lookup string (R8).
    """

    record_id: str
    source_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    point_status: str = "unreported"
    has_coordinate_claims: bool = False
    precision: str | None = None
    declared: tuple[str, str] | None = None
    defect_flags: frozenset[str] = frozenset()
    name: str | None = None


@dataclass(frozen=True)
class PlacementResult:
    """The recorded placement of one record — basis + check + vintage."""

    record_id: str
    source_id: str | None
    jurisdiction_key: str | None
    jurisdiction_chain: tuple[str, ...]
    placement_basis: str | None
    placement_check: str
    declared: tuple[str, str] | None
    declared_jkey: str | None
    located_jkey: str | None
    boundary_vintage: str | None
    point_withheld: bool
    on_boundary: bool

    def __post_init__(self) -> None:
        # Closed vocabulary — a check outside PLACEMENT_CHECKS is a ruleset
        # bug or a drifted caller; refuse it, never emit it (K4 §3.3/P4).
        if self.placement_check not in PLACEMENT_CHECKS:
            raise PlacementError(
                f"unknown placement_check {self.placement_check!r} — the "
                "placement@1 vocabulary is closed"
            )
        if self.placement_basis is not None and self.placement_basis not in PLACEMENT_BASIS:
            raise PlacementError(
                f"unknown placement_basis {self.placement_basis!r} — the "
                "placement@1 vocabulary is closed"
            )

    @property
    def placed(self) -> bool:
        return self.jurisdiction_key is not None

    def sites_columns(self) -> dict[str, Any]:
        """The seven additive sites-file columns (K4 §5.3)."""
        return {
            "jurisdiction_key": self.jurisdiction_key,
            "jurisdiction_chain": list(self.jurisdiction_chain),
            "placement_basis": self.placement_basis,
            "placement_check": self.placement_check,
            "declared_scheme": self.declared[0] if self.declared else None,
            "declared_value": self.declared[1] if self.declared else None,
            "boundary_vintage": self.boundary_vintage,
        }


def _placement_specs() -> tuple[Any, ...]:
    """The sites-file columns this module stamps — the registry's spec for them.

    Declared beside the writer (P35.39 / SIG-TRANSP-016): the closed
    ``placement@1`` vocabularies above ARE the enum sources — a value outside
    them can never reach a row (the ``__post_init__`` refuses it).
    """
    from .column_registry import ColumnSpec as _CS

    return (
        _CS(
            "jurisdiction_key",
            "the boundary pack's canonical jurisdiction key the record placed into "
            "(None when unplaced)",
        ),
        _CS(
            "jurisdiction_chain",
            "the ordered jurisdiction keys from country down to the placed level",
            dtype="array",
        ),
        _CS(
            "placement_basis",
            "how the placement was derived — a closed ``placement@1`` basis",
            enum_source="export:placement.PLACEMENT_BASIS",
            declared_values=PLACEMENT_BASIS,
        ),
        _CS(
            "placement_check",
            "the ruleset's verdict — a closed ``placement@1`` check (R1–R8)",
            nullable=False,
            enum_source="export:placement.PLACEMENT_CHECKS",
            declared_values=PLACEMENT_CHECKS,
        ),
        _CS(
            "declared_scheme",
            "the scheme of the record's declared jurisdiction identifier "
            "(None when no usable declaration exists — never a guessed bare code)",
        ),
        _CS(
            "declared_value",
            "the declared jurisdiction identifier value within its scheme",
        ),
        _CS(
            "boundary_vintage",
            "the boundary pack vintage the placement ran against (e.g. ``tiger2024``/``ne10m-…``)",
        ),
    )


#: The registry spec for the seven columns ``sites_columns`` emits (P35.39).
PLACEMENT_COLUMN_SPECS = _placement_specs()


# --------------------------------------------------------------------------- #
# Engine construction — verified pack + bound registry → spatial index        #
# --------------------------------------------------------------------------- #


def _strict_spatial(con: Any) -> None:
    """``LOAD spatial`` — never a runtime ``INSTALL`` (K4 §4.4).

    The extension is bundled into the export image at the pinned DuckDB
    version; an unbundled host fails here, loudly, instead of fetching code.
    """
    try:
        con.execute("LOAD spatial")
    except Exception as exc:  # noqa: BLE001 — surface the load failure verbatim
        raise PlacementError(
            "DuckDB `spatial` is not provisioned on this host — the export "
            "image bundles it at build time (K4 §4.4); a runtime INSTALL is "
            f"never attempted. Underlying error: {exc}"
        ) from exc


def _mint_select(layer: Any, parquet_path: Path) -> str | None:
    """The SQL minting ``(jkey, geom)`` rows for one pack layer — mirrors
    ``jurisdictions.build_registry``'s per-scheme key derivation exactly, so a
    geometry is always keyed the way the registry named it."""
    q = "'" + str(parquet_path).replace("'", "''") + "'"
    fields = layer.fields
    code = str(fields.get("code") or "")
    geoid = str(fields.get("geoid") or "")
    code_c = f'"{code}"'
    scheme = layer.key_scheme
    if scheme == "us.state_abbr":
        if not code:
            return None
        return (
            f"SELECT 'iso3166-2:US-' || upper(trim({code_c})) AS jkey, geom"
            f" FROM read_parquet({q})"
            f" WHERE upper(trim({code_c})) ~ '^[A-Z]{{2}}$'"
            + (f" AND trim(\"{geoid}\") ~ '^\\d{{2}}$'" if geoid else "")
        )
    if scheme == "iso3166-1":
        if not code:
            return None
        return (
            f"SELECT 'iso3166-1:' || upper(trim({code_c})) AS jkey, geom"
            f" FROM read_parquet({q})"
            f" WHERE length(upper(trim({code_c}))) = 2"
        )
    if scheme == "iso3166-2":
        if not code:
            return None
        base = (
            f"SELECT 'iso3166-2:' || upper(trim({code_c})) AS jkey, geom"
            f" FROM read_parquet({q})"
            f" WHERE upper(trim({code_c})) ~ '^[A-Z]{{2}}-[A-Z0-9]{{1,3}}$'"
            f"   AND upper(trim({code_c})) NOT LIKE 'US-%'"
        )
        if not layer.rollup:
            return base
        # Rollup: the consumed units union into the mapped first tier
        # (GB geonunit → GB-ENG/SCT/WLS/NIR) exactly as build_registry does;
        # the unconsumed rows mint normally.
        roll = layer.rollup
        field = str(roll["field"])
        prefix = str(roll["prefix"])
        mapping = {str(k): str(v) for k, v in dict(roll["map"]).items()}
        parts = [f"{base} AND upper(trim({code_c})) NOT LIKE '{prefix}-%'"]
        parts.append(
            f"{base} AND upper(trim({code_c})) LIKE '{prefix}-%'"
            f' AND "{field}" NOT IN ({_sql_list(mapping)})'
        )
        for unit, sub in sorted(mapping.items()):
            esc = unit.replace("'", "''")
            parts.append(
                f"SELECT 'iso3166-2:{prefix}-{sub}' AS jkey, ST_Union_Agg(geom) AS geom"
                f" FROM read_parquet({q})"
                f" WHERE \"{field}\" = '{esc}'"
                f' GROUP BY "{field}"'
            )
        return " UNION ALL ".join(f"({p})" for p in parts)
    if scheme == "us.census.geoid.county":
        if not geoid:
            return None
        return (
            f"SELECT 'us.census.geoid.county:' || trim(\"{geoid}\") AS jkey, geom"
            f" FROM read_parquet({q}) WHERE trim(\"{geoid}\") ~ '^\\d{{5}}$'"
        )
    if scheme == "us.census.geoid.place":
        if not geoid:
            return None
        return (
            f"SELECT 'us.census.geoid.place:' || trim(\"{geoid}\") AS jkey, geom"
            f" FROM read_parquet({q}) WHERE trim(\"{geoid}\") ~ '^\\d{{7}}$'"
        )
    if scheme.startswith("national:"):
        if not code:
            return None
        nat = scheme.split(":", 1)[1]
        return (
            f"SELECT '{nat}:' || trim({code_c}) AS jkey, geom"
            f" FROM read_parquet({q}) WHERE trim({code_c}) <> ''"
        )
    return None


def _sql_list(values: Iterable[str]) -> str:
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)


class PlacementEngine:
    """``placement@1`` over a verified boundary pack + bound registry.

    Construction is the fail-closed gate: the pack must verify, the registry
    must bind the pack's ``boundaries_root`` + vintages, and every keyed
    boundary row must name a registry jurisdiction (a geometry the registry
    never named is dropped loudly into ``dropped_boundaries``; a registry
    jurisdiction with no geometry is simply never a point-placement target —
    it can still be reached by the declared/name paths).
    """

    def __init__(
        self,
        pack_dir: Path | str,
        registry: Mapping[str, Any] | Path | str,
        *,
        spec_path: Path | str | None = None,
    ) -> None:
        pack_dir = Path(pack_dir)
        try:
            failures = verify_pack(pack_dir)
            manifest = read_manifest(pack_dir)
            doc = read_registry(registry) if isinstance(registry, (str, Path)) else dict(registry)
        except BoundaryPackError as exc:
            # The pack/registry layer's own error type is normalised to
            # PlacementError — the placement run has ONE refusal surface
            # (the CLI maps it to rc 4).
            raise PlacementError(f"placement input refused: {exc}") from exc
        if failures:
            raise PlacementError(
                "boundary pack fails verification — placement refuses:\n  " + "\n  ".join(failures)
            )
        self._manifest = manifest
        if doc.get("schema") != REGISTRY_SCHEMA:
            raise PlacementError(
                f"registry schema {doc.get('schema')!r}; expected {REGISTRY_SCHEMA!r}"
            )
        bound = doc.get("boundary_pack") or {}
        if bound.get("boundaries_root") != self._manifest.get("boundaries_root"):
            raise PlacementError(
                "registry's boundary_pack.boundaries_root "
                f"{bound.get('boundaries_root')!r} does not match the staged "
                f"pack's {self._manifest.get('boundaries_root')!r} — the "
                "placement inputs are inconsistent (fail closed)"
            )
        if dict(sorted((doc.get("vintages") or {}).items())) != dict(
            sorted((self._manifest.get("vintages") or {}).items())
        ):
            raise PlacementError(
                "registry vintages disagree with the pack's declared vintages "
                "— the placement inputs are inconsistent (fail closed)"
            )
        self._registry = doc
        self._rows: dict[str, Mapping[str, Any]] = {
            str(r["jkey"]): r for r in doc.get("rows") or []
        }
        self._ancestors: dict[str, tuple[str, ...]] = {
            jkey: self._ancestor_chain(row) for jkey, row in self._rows.items()
        }
        self.dropped_boundaries = 0
        self._spec_path = spec_path
        self._con = self._build_index(pack_dir)

    @property
    def pack_manifest(self) -> Mapping[str, Any]:
        """The verified pack manifest — the report's boundary provenance."""
        return self._manifest

    def jurisdiction_row(self, jkey: str) -> Mapping[str, Any] | None:
        """The registry row for ``jkey`` — ``None`` for a non-registry key
        (declared buckets outside the canonical set). Read-only lookup for
        dossier/jurisdiction surfaces (P35.44)."""
        return self._rows.get(jkey)

    def jurisdiction_rows(self) -> Mapping[str, Mapping[str, Any]]:
        """Every registry row by jkey — the canonical jurisdiction set the
        P35.45 dossier roll-up keys off. Read-only (the callers build views;
        they never mutate the verified registry)."""
        return self._rows

    def ancestor_chains(self) -> Mapping[str, tuple[str, ...]]:
        """Every key's recorded root-first chain — ``ancestor_chain`` for the
        whole registry in one read (P35.45's slug-path derivation)."""
        return self._ancestors

    def ancestor_chain(self, jkey: str) -> tuple[str, ...]:
        """The root-first canonical chain ending at ``jkey`` (empty for
        non-registry keys) — the roll-up ancestor list dossier artifacts emit."""
        return self._ancestors.get(jkey, ())

    # -- internals ---------------------------------------------------------- #

    def _ancestor_chain(self, row: Mapping[str, Any]) -> tuple[str, ...]:
        """Root-first parent chain ending at the row's own key."""
        out: list[str] = []
        cur: str | None = str(row["jkey"])
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            cur = self._rows.get(cur, {}).get("parent")
        return tuple(reversed(out))

    def _build_index(self, pack_dir: Path) -> Any:
        """Load every minting layer's ``(jkey, level, geom)`` into DuckDB."""
        import duckdb

        from .boundary_pack import PACK_SPEC_RESOURCE_PATH

        spec = load_spec(self._spec_path or PACK_SPEC_RESOURCE_PATH)
        manifest_layers = {str(e["id"]): e for e in self._manifest["layers"]}
        con = duckdb.connect()
        _strict_spatial(con)
        con.execute(
            "CREATE TABLE bounds (jkey VARCHAR, level VARCHAR, tol_ok BOOLEAN, "
            "xmin DOUBLE, ymin DOUBLE, xmax DOUBLE, ymax DOUBLE, geom GEOMETRY)"
        )
        seen: set[tuple[str, str]] = set()
        for layer in spec.layers:
            if not layer.mints_rows:
                continue
            if layer.id not in manifest_layers:
                # The spec declares a minting layer the verified pack does not
                # carry — a spec/pack drift the run refuses, loudly, instead of
                # silently placing on a partial boundary set (fail closed).
                raise PlacementError(
                    f"spec minting layer {layer.id!r} is absent from the "
                    "verified pack manifest — the placement inputs are "
                    "inconsistent (fail closed)"
                )
            entry = manifest_layers[layer.id]
            select = _mint_select(layer, pack_dir / str(entry["path"]))
            if select is None:
                continue
            tol = layer.role == "non_us"
            try:
                rows = con.execute(
                    "SELECT jkey, ST_XMin(geom), ST_YMin(geom), ST_XMax(geom),"
                    "       ST_YMax(geom), geom FROM (" + select + ")"
                ).fetchall()
            except Exception as exc:  # noqa: BLE001
                raise PlacementError(f"boundary layer {layer.id!r} failed to load: {exc}") from exc
            for jkey, xmin, ymin, xmax, ymax, geom in rows:
                jkey = str(jkey)
                if (layer.id, jkey) in seen or jkey not in self._rows:
                    # A geometry the registry never named is dropped — never a
                    # placement target (the registry is the naming authority).
                    if (layer.id, jkey) not in seen:
                        self.dropped_boundaries += 1
                    seen.add((layer.id, jkey))
                    continue
                seen.add((layer.id, jkey))
                con.execute(
                    "INSERT INTO bounds VALUES (?,?,?,?,?,?,?, ST_GeomFromWKB(?))",
                    (
                        jkey,
                        str(self._rows[jkey].get("level")),
                        tol,
                        float(xmin),
                        float(ymin),
                        float(xmax),
                        float(ymax),
                        # A fetched GEOMETRY returns to Python as its WKB blob —
                        # re-mint it inside the INSERT.
                        bytes(geom),
                    ),
                )
        # Per-bound ancestor maps + the inverted index ``under[L][a]`` = the
        # bounds at level ``L`` that carry ``a`` as an ancestor — drives both
        # the chain's prefix-consistency filter and the honest "this level was
        # never evaluated" marker (a US Census place is state-keyed, not
        # county-keyed, so evaluability is decided per chain, not per leaf).
        self._bounds_levels: set[str] = set()
        self._bounds_anc: dict[str, dict[str, str]] = {}
        self._under: dict[str, dict[str, set[str]]] = {}
        for jkey, level in con.execute("SELECT jkey, level FROM bounds").fetchall():
            jkey, level = str(jkey), str(level)
            self._bounds_levels.add(level)
            anc_chain = self._ancestors.get(jkey, (jkey,))
            anc_by_level = {
                str(self._rows[a].get("level")): a for a in anc_chain[:-1] if a in self._rows
            }
            self._bounds_anc[jkey] = anc_by_level
            for a in anc_chain[:-1]:
                self._under.setdefault(level, {}).setdefault(a, set()).add(jkey)
        return con

    # -- the spatial pass ----------------------------------------------------- #

    def _join_points(
        self, inputs: Sequence[PlacementInput]
    ) -> dict[int, list[tuple[str, str, str]]]:
        """Batch point-in-polygon: ``id → [(jkey, level, 'exact'|'tolerance')]``.

        Only geometrically valid, unflagged, guard-passing points enter the
        join — the R1/guard/defect gates all run per-record in ``_place`` and
        never depend on a spatial answer.
        """
        con = self._con
        con.execute("DROP TABLE IF EXISTS points")
        con.execute("CREATE TABLE points (id INTEGER, x DOUBLE, y DOUBLE)")
        to_place = [(i, inp.lon, inp.lat) for i, inp in enumerate(inputs) if _point_candidate(inp)]
        if to_place:
            con.executemany("INSERT INTO points VALUES (?,?,?)", to_place)
        rows = con.execute(
            """
            SELECT p.id, b.jkey, b.level,
                   CASE WHEN ST_Covers(b.geom, ST_Point(p.x, p.y))
                        THEN 'exact' ELSE 'tolerance' END AS kind
              FROM points p JOIN bounds b
                ON p.x BETWEEN b.xmin - ? AND b.xmax + ?
               AND p.y BETWEEN b.ymin - ? AND b.ymax + ?
             WHERE ST_Covers(b.geom, ST_Point(p.x, p.y))
                OR (b.tol_ok AND ST_DWithin(b.geom, ST_Point(p.x, p.y), ?))
            """,
            [NE_TOLERANCE_DEG] * 5,
        ).fetchall()
        hits: dict[int, list[tuple[str, str, str]]] = {}
        for pid, jkey, level, kind in rows:
            hits.setdefault(int(pid), []).append((str(jkey), str(level), str(kind)))
        return hits

    def _covers(self, jkey: str, lat: float, lon: float) -> bool:
        """Whether the registry geometry for ``jkey`` covers the point (with
        the same tolerance posture the bulk join uses)."""
        row = self._con.execute(
            "SELECT CASE WHEN ST_Covers(geom, ST_Point(?, ?)) THEN true"
            "       WHEN tol_ok AND ST_DWithin(geom, ST_Point(?, ?), ?) THEN true"
            "       ELSE false END FROM bounds WHERE jkey = ?",
            [lon, lat, lon, lat, NE_TOLERANCE_DEG, jkey],
        ).fetchone()
        return bool(row and row[0])

    # -- rule evaluation ------------------------------------------------------ #

    def place_many(self, inputs: Sequence[PlacementInput]) -> list[PlacementResult]:
        """Evaluate R1–R8 per record, in order, first match wins."""
        hits = self._join_points(inputs)
        return [self._place(i, inp, hits.get(i, ())) for i, inp in enumerate(inputs)]

    def _place(
        self,
        idx: int,
        inp: PlacementInput,
        hits: Sequence[tuple[str, str, str]],
    ) -> PlacementResult:
        declared = _declared_pair(inp.declared)
        declared_jkey = jurisdiction_key(declared[0], declared[1]) if declared else None
        if declared_jkey is not None and not valid_jkey(declared_jkey):
            declared_jkey = None
        declared_known = declared_jkey is not None and declared_jkey in self._rows

        # -- non-site name lookup (R8) ------------------------------------- #
        if inp.name is not None and inp.lat is None and not inp.has_coordinate_claims:
            return self._place_by_name(inp, declared, declared_jkey)

        # -- landed defect claims are inputs (K4 §3.3 note) ----------------- #
        unknown_defects = inp.defect_flags - _DEFECT_KNOWN
        if unknown_defects:
            # A geometry_defect class the ruleset does not know is never
            # silently ignored — the closed vocabulary fails closed.
            raise PlacementError(
                f"record {inp.record_id!r}: unknown geometry_defect class "
                f"{sorted(unknown_defects)[0]!r} — placement refuses"
            )
        flagged = inp.defect_flags & _DEFECT_KNOWN
        if flagged & set(_DEFECT_SUSPECT):
            check = _DEFECT_SUSPECT[sorted(flagged & set(_DEFECT_SUSPECT))[0]]
            if declared_known:
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check=check,
                    withheld=True,
                )
            return self._result(inp, declared, declared_jkey, None, check=check, withheld=True)
        if _DEFECT_REJECT in flagged:
            if declared_known:
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check=f"point_rejected:{_DEFECT_REJECT}",
                    withheld=True,
                )
            return self._result(
                inp,
                declared,
                declared_jkey,
                None,
                check=_DEFECT_REJECT,
                withheld=_point_withheld(inp),
            )

        # -- R1: the point itself ------------------------------------------- #
        reject = _reject_reason(inp)
        if reject is not None:
            if declared_known:
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check=f"point_rejected:{reject}",
                    withheld=True,
                )
            return self._result(
                inp,
                declared,
                declared_jkey,
                None,
                check=reject,
                withheld=_point_withheld(inp),
            )

        # -- no usable point ------------------------------------------------ #
        if inp.lat is None or inp.lon is None or not _point_usable(inp):
            if declared_known:
                check = "coordinates_conflicted" if inp.point_status == "conflicted" else "no_point"
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check=check,
                    withheld=_point_withheld(inp),
                )
            # Unplaced with nothing declared — a guarded agency centroid or a
            # conflicted pair is still withheld from the emitted geometry
            # (SIG-IDENT-004: the point the guard refuses is never re-published
            # as the record's location).
            return self._result(
                inp,
                declared,
                declared_jkey,
                None,
                check="no_location_evidence",
                withheld=_point_withheld(inp),
            )

        # -- the point is usable: the located chain -------------------------- #
        chain, on_boundary, deeper_unevaluated = self._locate(hits)

        if not chain:
            # The point sits in no boundary beyond tolerance.
            if declared_known:
                suspected = self._suspected_variant(inp, declared_jkey)
                if suspected:
                    return self._result(
                        inp,
                        declared,
                        declared_jkey,
                        declared_jkey,
                        basis="declared",
                        check=suspected,
                        withheld=True,
                    )
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check="outside_all_boundaries",
                    withheld=True,
                )
            return self._result(inp, declared, declared_jkey, None, check="outside_all_boundaries")

        leaf = chain[-1]
        located_country = chain[0]
        declared_anc = self._ancestors.get(declared_jkey or "", ())
        declared_consistent = (
            declared_jkey is None
            or declared_jkey in self._ancestors.get(leaf, ())
            # A declared key DEEPER than the located leaf is consistent when
            # it extends the located chain (declared county under the located
            # state) — the deeper level was simply never evaluated.
            or leaf in declared_anc
        )
        if declared_jkey is not None and not declared_consistent:
            suspected = self._suspected_variant(inp, declared_jkey if declared_known else None)
            if suspected and declared_known:
                return self._result(
                    inp,
                    declared,
                    declared_jkey,
                    declared_jkey,
                    basis="declared",
                    check=suspected,
                    withheld=True,
                )
            declared_country = _declared_country(declared_jkey)
            check = (
                "outside_declared_country"
                if declared_country is not None and declared_country != located_country
                else "outside_declared"
            )
            return self._result(
                inp,
                declared,
                declared_jkey,
                leaf,
                basis="point_in_polygon",
                check=check,
                chain=chain,
            )

        if on_boundary:
            check = "on_boundary"
        elif deeper_unevaluated:
            # Partial depth (K4 §3.3): a level deeper than the leaf was never
            # evaluated — placed, never unplaced, and not the same as
            # `consistent` (every deeper level came back with an answer).
            check = "not_evaluated"
        else:
            check = "consistent"
        return self._result(
            inp,
            declared,
            declared_jkey,
            leaf,
            basis="point_in_polygon",
            check=check,
            chain=chain,
            on_boundary=on_boundary,
        )

    def _place_by_name(
        self,
        inp: PlacementInput,
        declared: tuple[str, str] | None,
        declared_jkey: str | None,
    ) -> PlacementResult:
        """R8 — the ``lookup@1`` name path for non-site claims (I8)."""
        hits = lookup(list(self._rows.values()), str(inp.name))
        distinct = {str(h["jkey"]) for h in hits}
        if not distinct:
            return self._result(inp, declared, declared_jkey, None, check="name_unmatched")
        if len(distinct) > 1:
            return self._result(inp, declared, declared_jkey, None, check="name_ambiguous")
        jkey = next(iter(distinct))
        return self._result(
            inp,
            declared,
            declared_jkey,
            jkey,
            basis="name_lookup",
            check="consistent",
            chain=self._ancestors.get(jkey, (jkey,)),
        )

    def _consistent(self, jkey: str, chain_by_level: Mapping[str, str]) -> bool:
        """Whether a candidate's registry lineage agrees with the chain.

        Every ancestor level the candidate HAS must match the chain's key at
        that level; a level the candidate's family does not key through (a US
        Census place is state-keyed, never county-keyed) is unconstrained.
        """
        anc = self._bounds_anc.get(jkey) or self._ancestor_levels(jkey)
        return all(chain_by_level.get(level) == a for level, a in anc.items())

    def _ancestor_levels(self, jkey: str) -> dict[str, str]:
        return {
            str(self._rows[a].get("level")): a
            for a in self._ancestors.get(jkey, ())[:-1]
            if a in self._rows
        }

    def _evaluable(self, level: str, chain_by_level: Mapping[str, str]) -> bool:
        """Whether any bound at ``level`` can be consistent with the chain —
        i.e. whether the level is *evaluated* at all under this placement
        (``False`` → the level and everything deeper is `not_evaluated`)."""
        if not chain_by_level:
            return level in self._bounds_levels
        candidates: set[str] = set()
        for _lvl, key in chain_by_level.items():
            candidates |= self._under.get(level, {}).get(key, set())
        return any(self._consistent(b, chain_by_level) for b in candidates)

    def _locate(self, hits: Sequence[tuple[str, str, str]]) -> tuple[list[str], bool, bool]:
        """The located chain — level-ordered, prefix-consistent.

        Returns ``(chain, on_boundary, deeper_unevaluated)``: the chain of
        placed keys root→leaf; whether a multi-candidate level was resolved by
        the lowest-GEOID/code tie-break; and whether any level deeper than
        the leaf went unevaluated (``True`` → `not_evaluated`, the K4 §3.3
        partial-depth marker — "its sub-levels are `not_evaluated`, which is
        not the same as unplaced"). A miss at a level stops the walk ("the
        chain stops there"), so every deeper level is unevaluated.
        """
        by_level: dict[str, list[str]] = {}
        for jkey, level, _kind in hits:
            if jkey not in by_level.setdefault(level, []):
                by_level[level].append(jkey)
        chain: list[str] = []
        chain_by_level: dict[str, str] = {}
        evaluated: set[int] = set()
        on_boundary = False
        for i, level in enumerate(LEVELS):
            if chain and not self._evaluable(level, chain_by_level):
                break  # nothing at this level can sit under the chain
            evaluated.add(i)
            candidates = [j for j in by_level.get(level, ()) if self._consistent(j, chain_by_level)]
            if not candidates:
                break  # evaluated and missed — the chain stops here
            winner = sorted(candidates)[0]  # lowest GEOID/code — the tie-break
            on_boundary = on_boundary or len(candidates) > 1
            chain.append(winner)
            chain_by_level[level] = winner
        if not chain:
            return ([], False, False)
        # Every non-breaking iteration appends exactly one key, in LEVELS
        # order — the leaf sits at LEVELS index ``len(chain) - 1``.
        leaf_index = len(chain) - 1
        deeper_unevaluated = any(i not in evaluated for i in range(leaf_index + 1, len(LEVELS)))
        return (chain, on_boundary, deeper_unevaluated)

    def _suspected_variant(self, inp: PlacementInput, declared_jkey: str | None) -> str | None:
        """R3 — whether a swapped/sign-flipped variant lands inside declared."""
        if declared_jkey is None or inp.lat is None or inp.lon is None:
            return None
        lat, lon = inp.lat, inp.lon
        if self._covers(declared_jkey, lon, lat):  # the swapped pair
            return "axis_swap_suspected"
        for vlat, vlon in ((-lat, lon), (lat, -lon), (-lat, -lon)):
            if (
                -90 <= vlat <= 90
                and -180 <= vlon <= 180
                and self._covers(declared_jkey, vlat, vlon)
            ):
                return "sign_flip_suspected"
        return None

    def _result(
        self,
        inp: PlacementInput,
        declared: tuple[str, str] | None,
        declared_jkey: str | None,
        jkey: str | None,
        *,
        basis: str | None = None,
        check: str,
        chain: Sequence[str] | None = None,
        withheld: bool = False,
        on_boundary: bool = False,
    ) -> PlacementResult:
        if chain is None:
            chain = self._ancestors.get(jkey, ()) if jkey else ()
        vintage = (
            str(self._rows[jkey].get("vintage"))
            if jkey is not None and jkey in self._rows
            else None
        )
        return PlacementResult(
            record_id=inp.record_id,
            source_id=inp.source_id,
            jurisdiction_key=jkey,
            jurisdiction_chain=tuple(chain),
            placement_basis=basis,
            placement_check=check,
            declared=declared,
            declared_jkey=declared_jkey,
            located_jkey=(jkey if basis == "point_in_polygon" else None),
            boundary_vintage=vintage,
            point_withheld=withheld,
            on_boundary=on_boundary,
        )


# --------------------------------------------------------------------------- #
# Inputs from shaped sites + the report                                        #
# --------------------------------------------------------------------------- #


def _declared_pair(declared: tuple[str, str] | None) -> tuple[str, str] | None:
    if not declared or not declared[0] or not str(declared[1] or "").strip():
        return None
    return (str(declared[0]), str(declared[1]).strip())


def _reject_reason(inp: PlacementInput) -> str | None:
    """R1 — the point's own validity, independent of any boundary."""
    if inp.lat is None or inp.lon is None:
        return None
    lat, lon = float(inp.lat), float(inp.lon)
    if math.isnan(lat) or math.isnan(lon):
        return "invalid_point"
    if lat == 0.0 and lon == 0.0:
        return "null_island"
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return "invalid_point"
    return None


def _point_usable(inp: PlacementInput) -> bool:
    """Whether the resolved pair may drive point-in-polygon (SIG-IDENT-004)."""
    if inp.point_status != "resolved":
        return False
    precision = inp.precision
    if precision is None:
        return True
    from resolution.geometry_precision import GeometryPrecisionError, is_point_in_polygon_usable

    try:
        return is_point_in_polygon_usable(precision)
    except (ValueError, GeometryPrecisionError):
        # An unrecognised precision string is not the organisation-centroid
        # class the guard exists for — the point stays usable (the precision
        # column still carries the verbatim value).
        return True


def _point_candidate(inp: PlacementInput) -> bool:
    """Which inputs enter the spatial join at all (gates run per-record too)."""
    if inp.lat is None or inp.lon is None or not _point_usable(inp):
        return False
    if inp.defect_flags & (_DEFECT_KNOWN - {"wrong_jurisdiction"}):
        # A landed suspect/reject flag means the point never enters the join —
        # the detector's verdict is the input (K4 §3.3 note).
        return False
    if _reject_reason(inp) is not None:
        return False
    return True


def _point_withheld(inp: PlacementInput) -> bool:
    """A point existed on the record but never reaches a map/sub-count."""
    return inp.lat is not None and inp.lon is not None


def _declared_country(declared_jkey: str | None) -> str | None:
    """The country key implied by a declared jkey (None when the scheme does
    not encode one — a national key carries no country)."""
    if not declared_jkey:
        return None
    if declared_jkey.startswith("iso3166-1:"):
        return declared_jkey
    if declared_jkey.startswith("iso3166-2:"):
        return country_jkey(declared_jkey.split(":", 1)[1].split("-", 1)[0])
    if declared_jkey.startswith("us.census.geoid."):
        return "iso3166-1:US"
    return None


def site_input(
    site: ShapedSite,
    *,
    claims_by_id: Mapping[str, ShapingClaim],
    defect_flags: frozenset[str] = frozenset(),
    source_id: str | None = None,
) -> PlacementInput:
    """Build the engine input for one shaped site — declared pair from the
    resolved jurisdiction envelope's supporting claims (P35.18's
    ``value_json`` pair first, then the configured-scheme literal), the
    envelope's own point/precision verdict, and the subject's landed defect
    classes."""
    from .shaping import (
        _declared_jurisdiction_pair,
        _default_jurisdiction_config,
        _display_value,
    )

    declared: tuple[str, str] | None = None
    env = site.jurisdiction_envelope
    if env is not None:
        for cid in sorted(env.supporting_claim_ids):
            claim = claims_by_id.get(cid)
            if claim is None:
                continue
            pair = _declared_jurisdiction_pair(claim)
            if pair is not None:
                # The persisted {scheme, value} the connector asserted.
                declared = (pair[0], pair[1])
                break
            literal = str(_display_value(claim).parsed or "")
            cfg = _default_jurisdiction_config().for_claim(claim.source_id, literal)
            if cfg is not None:
                declared = (cfg.scheme, literal)
                break
    # SIG-IDENT-004: a coordinate claim can carry its own geometry precision
    # in ``value_json`` (the LocatedPoint ``{"geometry","precision"}`` payload
    # agency-registry connectors stamp). The site's ``precision`` column is
    # only the sensitivity-tier transform — it never names the centroid
    # class — so the guard reads the stamp off the claims backing the
    # resolved point. A point whose backing claim stamps a never-point-placed
    # precision is never point-placed, whatever the tier label says.
    precision = site.precision
    for cid in sorted(
        set(site.lat_envelope.supporting_claim_ids) | set(site.lon_envelope.supporting_claim_ids)
    ):
        claim = claims_by_id.get(cid)
        if claim is None or not claim.value_json:
            continue
        try:
            blob = json.loads(claim.value_json)
        except (TypeError, ValueError):
            continue
        stamp = blob.get("precision") if isinstance(blob, Mapping) else None
        if isinstance(stamp, str) and stamp.strip():
            precision = stamp.strip()
            break
    return PlacementInput(
        record_id=site.entity_id,
        source_id=source_id,
        lat=site.latitude,
        lon=site.longitude,
        point_status=site.point_status,
        has_coordinate_claims=site.has_coordinate_claims,
        precision=precision,
        declared=declared,
        defect_flags=frozenset(defect_flags),
    )


def build_report(
    results: Sequence[PlacementResult],
    *,
    manifest: Mapping[str, Any] | None = None,
    pack_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``sig.placement-report/1`` quality report (K4 §3.4, SIG-JUR-D05).

    Count conservation is the contract: every result carries exactly one
    ``placement_check``, so ``records == sum(by_check.values())`` globally and
    per source; unplaced records appear under their reason, never under a
    jurisdiction. ``disclosures`` is the located-vs-declared disagreement set
    (R4) — one row per (declared, located) pair, counted once here and
    rendered on both dossiers downstream ("declared here, located elsewhere"
    / "located here, declared elsewhere" — same rows, two readings).
    """
    manifest = dict(manifest or pack_manifest or {})
    by_check: dict[str, int] = {}
    per_source: dict[str, dict[str, Any]] = {}
    disclosures: dict[tuple[str, str], int] = {}
    # Per-dossier (per-jurisdiction) per-source two-sided counts (K4 §3.4):
    # the declared side reads "declared here, located elsewhere: n" and the
    # located side reads "located here, declared elsewhere: n" — the SAME
    # disagreement row counted on both dossiers, never silently resolved.
    by_jurisdiction: dict[str, dict[str, Any]] = {}
    placed = unplaced = 0

    def _dossier_bucket(jkey: str) -> dict[str, Any]:
        return by_jurisdiction.setdefault(
            jkey,
            {
                "declared_here_located_elsewhere": 0,
                "located_here_declared_elsewhere": 0,
                "by_source": {},
            },
        )

    for r in sorted(results, key=lambda r: (r.source_id or "", r.record_id)):
        by_check[r.placement_check] = by_check.get(r.placement_check, 0) + 1
        src = r.source_id or "(unknown)"
        bucket = per_source.setdefault(
            src, {"records": 0, "placed": 0, "unplaced": 0, "by_check": {}}
        )
        bucket["records"] += 1
        bucket["by_check"][r.placement_check] = bucket["by_check"].get(r.placement_check, 0) + 1
        if r.placed:
            placed += 1
            bucket["placed"] += 1
        else:
            unplaced += 1
            bucket["unplaced"] += 1
        if (
            r.declared_jkey
            and r.located_jkey
            and r.placement_check in {"outside_declared", "outside_declared_country"}
        ):
            key = (r.declared_jkey, r.located_jkey)
            disclosures[key] = disclosures.get(key, 0) + 1
            declared_side = _dossier_bucket(r.declared_jkey)
            declared_side["declared_here_located_elsewhere"] += 1
            located_side = _dossier_bucket(r.located_jkey)
            located_side["located_here_declared_elsewhere"] += 1
            for side, field in (
                (declared_side, "declared_here_located_elsewhere"),
                (located_side, "located_here_declared_elsewhere"),
            ):
                src_bucket = side["by_source"].setdefault(
                    src,
                    {
                        "declared_here_located_elsewhere": 0,
                        "located_here_declared_elsewhere": 0,
                    },
                )
                src_bucket[field] += 1
    return {
        "schema": PLACEMENT_REPORT_SCHEMA,
        "rules": PLACEMENT_RULESET,
        "check_vocabulary": list(PLACEMENT_CHECKS),
        "boundary_pack": {
            "pack_id": manifest.get("pack_id"),
            "boundaries_root": manifest.get("boundaries_root"),
            "vintages": dict(sorted((manifest.get("vintages") or {}).items())),
        },
        "totals": {
            "records": len(results),
            "placed": placed,
            "unplaced": unplaced,
        },
        "by_check": dict(sorted(by_check.items())),
        "per_source": {
            sid: {
                "records": v["records"],
                "placed": v["placed"],
                "unplaced": v["unplaced"],
                "by_check": dict(sorted(v["by_check"].items())),
            }
            for sid, v in sorted(per_source.items())
        },
        "disclosures": [
            {"declared": dkey, "located": lkey, "records": n}
            for (dkey, lkey), n in sorted(disclosures.items())
        ],
        # The both-sides dossier view (K4 §3.4): for every disagreement pair
        # (D→L) the invariant ``by_jurisdiction[D].declared_here_… ==
        # by_jurisdiction[L].located_here_… == pair.records`` holds.
        "disclosures_by_jurisdiction": {
            jkey: {
                "declared_here_located_elsewhere": v["declared_here_located_elsewhere"],
                "located_here_declared_elsewhere": v["located_here_declared_elsewhere"],
                "by_source": {
                    sid: dict(sorted(sb.items())) for sid, sb in sorted(v["by_source"].items())
                },
            }
            for jkey, v in sorted(by_jurisdiction.items())
        },
    }


__all__ = [
    "NE_TOLERANCE_DEG",
    "PLACEMENT_BASIS",
    "PLACEMENT_CHECKS",
    "PLACEMENT_REPORT_SCHEMA",
    "PLACEMENT_RULESET",
    "REJECT_REASONS",
    "PlacementEngine",
    "PlacementError",
    "PlacementInput",
    "PlacementResult",
    "build_report",
    "site_input",
]
