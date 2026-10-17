# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``jurisdictions`` registry + ``lookup@1`` (K4 §3.1/§3.2/§5.4, P35.17, ADR-160).

A jurisdiction is **never keyed on a bare code** (K4-P1, SIG-JUR-D01): the
canonical key names its scheme — ``iso3166-1:<A2>`` for countries,
``iso3166-2:<A2>-<sub>`` for admin-1, ``us.census.geoid.county:<SSCCC>``
(5-digit) and ``us.census.geoid.place:<SSPPPPP>`` (7-digit) for US county and
place, and ``<national scheme>:<code>`` for non-US municipalities (the
``de.ags:05315000`` family — the schema admits them even though the national
open datasets land later, K4 §4.3). Every other identifier is carried as a
``(scheme, value)`` pair (SIG-IDENT-006); codes are fixed-width with an
explicit level (SIG-IDENT-005).

Two postures are load-bearing and come straight from the operator's answers:

* **D-K4-4** — US territories are keyed ``iso3166-2:US-PR`` … under
  ``iso3166-1:US`` (Census state-equivalents) with the ISO 3166-1 code carried
  as an *alias* identifier.
* **D-K4-2** — disputed territories take ISO 3166-1 codes as published
  (TW, PS, HK, EH); ``XK`` for Kosovo is labelled ``code_status =
  "user-assigned"``; names are neutral; the registry document carries one
  standing note. A posture, never an adjudication (SIG-GEO-008 §3.1).

``lookup@1`` (K4 §5.4): ``lookup(name, *, level=None, within=None)`` returns
candidates ``{jkey, name, level, score, basis}`` — exact official name first,
then alternates, filtered by level and by ancestor context; an ambiguous name
returns every candidate rather than guessing (the consumer records
``name_ambiguous`` per R8).

The registry file is SIG metadata: ``license = "CC-BY-4.0"`` with the upstreams
attributed (TIGER/Line + Gazetteer, US Government work under 17 U.S.C. §105;
Natural Earth public domain, "Made with Natural Earth").
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .boundary_pack import (
    PACK_MANIFEST_NAME,
    BoundaryPackError,
    PackSpec,
)
from .manifest import canonical_json, sha256_hex

REGISTRY_SCHEMA = "sig.jurisdiction-registry/1"
LOOKUP_RULESET = "lookup@1"

#: K4 §3.1's `jurisdiction_type` vocabulary — the level is explicit on every
#: key (SIG-IDENT-005).
LEVELS: tuple[str, ...] = ("country", "state_province", "county", "municipality")

_COUNTRY_RE = re.compile(r"^iso3166-1:[A-Z]{2}$")
_ADMIN1_RE = re.compile(r"^iso3166-2:[A-Z]{2}-[A-Z0-9]{1,3}$")
_COUNTY_RE = re.compile(r"^us\.census\.geoid\.county:\d{5}$")
_PLACE_RE = re.compile(r"^us\.census\.geoid\.place:\d{7}$")
#: A national-scheme key (`de.ags:05315000`): `<scheme>:<code>`, scheme never a
#: reserved family.
_NATIONAL_RE = re.compile(r"^[a-z][a-z0-9_.]*:[A-Za-z0-9._-]+$")
_RESERVED_SCHEMES = frozenset(
    {"iso3166-1", "iso3166-2", "us.census.geoid.county", "us.census.geoid.place"}
)

#: Identifier `kind` values an identifier entry may carry.
_IDENTIFIER_KINDS = frozenset({"canonical", "alias", "code"})

#: The closed `basis` vocabulary of `lookup@1` candidates.
LOOKUP_BASES: tuple[str, ...] = ("official_name", "alternate_name", "identifier")

#: Scores — exact official-name hits outrank alternates; identifiers outrank
#: names when the query *is* a code (the caller asked for the scheme's value).
_SCORE_OFFICIAL = 1.0
_SCORE_ALTERNATE = 0.9
_SCORE_IDENTIFIER = 0.95


def country_jkey(alpha2: str) -> str:
    """``iso3166-1:<A2>`` — the country canonical key (K4 §3.1)."""
    return f"iso3166-1:{alpha2.upper()}"


def admin1_jkey(iso3166_2: str) -> str:
    """``iso3166-2:<A2>-<sub>`` — the admin-1 canonical key."""
    code = iso3166_2.upper()
    if not code.startswith("ISO3166-2:"):
        return f"iso3166-2:{code}"
    return f"iso3166-2:{code.split(':', 1)[1]}"


def county_jkey(geoid: str) -> str:
    """``us.census.geoid.county:<SSCCC>`` — fixed-width 5-digit GEOID (SIG-IDENT-005)."""
    if not re.fullmatch(r"\d{5}", geoid):
        raise ValueError(f"county GEOID must be 5 digits, got {geoid!r}")
    return f"us.census.geoid.county:{geoid}"


def place_jkey(geoid: str) -> str:
    """``us.census.geoid.place:<SSPPPPP>`` — fixed-width 7-digit GEOID."""
    if not re.fullmatch(r"\d{7}", geoid):
        raise ValueError(f"place GEOID must be 7 digits, got {geoid!r}")
    return f"us.census.geoid.place:{geoid}"


def national_jkey(scheme: str, code: str) -> str:
    """``<national scheme>:<code>`` — the non-US municipality family (K4 §3.1)."""
    if scheme in _RESERVED_SCHEMES:
        raise ValueError(f"{scheme!r} is a reserved key family")
    return f"{scheme}:{code}"


def valid_jkey(jkey: str) -> bool:
    """Whether ``jkey`` matches a declared key family (or the national form)."""
    if (
        _COUNTRY_RE.fullmatch(jkey)
        or _ADMIN1_RE.fullmatch(jkey)
        or _COUNTY_RE.fullmatch(jkey)
        or _PLACE_RE.fullmatch(jkey)
    ):
        return True
    m = _NATIONAL_RE.fullmatch(jkey)
    return bool(m) and jkey.split(":", 1)[0] not in _RESERVED_SCHEMES


# --------------------------------------------------------------------------- #
# The declared-scheme map (K4 §3.2) — claim (scheme, value) → canonical key   #
# --------------------------------------------------------------------------- #


def key_for_declared(scheme: str, value: str) -> str | None:
    """Map a declared ``(scheme, value)`` pair to its canonical key (K4 §3.2).

    ``sig.unresolved`` maps to ``None`` — an unresolved jurisdiction has no
    key; an unknown scheme raises (fail closed — a bare code is never guessed).
    """
    v = value.strip()
    if scheme == "sig.unresolved":
        return None
    if scheme == "us.state_abbr":
        return admin1_jkey(f"US-{v.upper()}")
    if scheme == "iso.3166_1_alpha2":
        return country_jkey(v)
    if scheme == "iso.3166_2":
        return admin1_jkey(v)
    raise ValueError(
        f"declared scheme {scheme!r} has no K4 §3.2 mapping — the code is never guessed"
    )


DECLARED_SCHEMES: tuple[str, ...] = (
    "us.state_abbr",
    "iso.3166_1_alpha2",
    "iso.3166_2",
    "sig.unresolved",
)


# --------------------------------------------------------------------------- #
# The registry row                                                            #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Jurisdiction:
    """One ``sig.jurisdiction-registry/1`` row (K4 §3.1)."""

    jkey: str
    level: str
    name: str
    vintage: str
    source: str
    alternates: tuple[str, ...] = ()
    identifiers: tuple[dict[str, str], ...] = ()
    parent: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    internal_point: tuple[float, float] | None = None
    code_status: str | None = None
    note: str | None = None

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "jkey": self.jkey,
            "level": self.level,
            "name": self.name,
            "alternates": sorted(set(self.alternates)),
            "identifiers": sorted(
                (dict(i) for i in self.identifiers),
                key=lambda i: (i.get("scheme", ""), i.get("value", ""), i.get("kind", "")),
            ),
            "vintage": self.vintage,
            "source": self.source,
        }
        if self.parent is not None:
            row["parent"] = self.parent
        if self.bbox is not None:
            row["bbox"] = list(self.bbox)
        if self.internal_point is not None:
            row["internal_point"] = list(self.internal_point)
        if self.code_status is not None:
            row["code_status"] = self.code_status
        if self.note is not None:
            row["note"] = self.note
        return row


# --------------------------------------------------------------------------- #
# Registry validation — the SIG-JUR-D01/SIG-IDENT-005 invariants, fail closed  #
# --------------------------------------------------------------------------- #


def validate_registry(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Structural invariants — violations, empty = valid.

    These assert **contract**, never current contents: every jkey unique and
    well-formed, level in the closed vocabulary, identifiers unique per
    ``(scheme, value, kind="code"|"canonical")`` pair, parents resolvable, and
    the fixed-width/level pairing that SIG-IDENT-005 demands.
    """
    failures: list[str] = []
    keys: set[str] = set()
    identifiers: dict[tuple[str, str], str] = {}
    for i, row in enumerate(rows):
        jkey = str(row.get("jkey") or "")
        if not jkey or not valid_jkey(jkey):
            failures.append(f"rows[{i}]: invalid jkey {jkey!r}")
        elif jkey in keys:
            failures.append(f"rows[{i}]: duplicate jkey {jkey!r}")
        keys.add(jkey)
        if row.get("level") not in LEVELS:
            failures.append(f"rows[{i}] {jkey}: level {row.get('level')!r} not in {LEVELS}")
        if not isinstance(row.get("name"), str) or not row["name"]:
            failures.append(f"rows[{i}] {jkey}: name missing")
        for ident in row.get("identifiers") or []:
            if not isinstance(ident, Mapping) or not ident.get("scheme") or "value" not in ident:
                failures.append(f"rows[{i}] {jkey}: malformed identifier {ident!r}")
                continue
            if ident.get("kind") is not None and ident["kind"] not in _IDENTIFIER_KINDS:
                failures.append(
                    f"rows[{i}] {jkey}: identifier kind {ident['kind']!r} not in "
                    f"{sorted(_IDENTIFIER_KINDS)}"
                )
            pair = (str(ident["scheme"]), str(ident["value"]))
            prior = identifiers.get(pair)
            if prior is not None and prior != jkey and ident.get("kind") != "alias":
                failures.append(
                    f"rows[{i}] {jkey}: identifier {pair} also carried by {prior} — "
                    "(scheme, value) must resolve to at most one key (SIG-IDENT-006)"
                )
            else:
                identifiers[pair] = jkey
        for f in ("vintage", "source"):
            if not row.get(f):
                failures.append(f"rows[{i}] {jkey}: {f} missing")
        bbox = row.get("bbox")
        if bbox is not None and not (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(isinstance(v, (int, float)) for v in bbox)
        ):
            failures.append(f"rows[{i}] {jkey}: bbox must be [w,s,e,n] floats")
        pt = row.get("internal_point")
        if pt is not None and not (
            isinstance(pt, list) and len(pt) == 2 and all(isinstance(v, (int, float)) for v in pt)
        ):
            failures.append(f"rows[{i}] {jkey}: internal_point must be [lon,lat] floats")
    for i, row in enumerate(rows):
        parent = row.get("parent")
        if parent is not None and parent not in keys:
            failures.append(f"rows[{i}] {row.get('jkey')!r}: parent {parent!r} not in registry")
    return failures


# --------------------------------------------------------------------------- #
# Registry build — pack layers → rows                                          #
# --------------------------------------------------------------------------- #


def _norm(s: str) -> str:
    """Name normalisation for `lookup@1` matching: casefold + strip accents +
    whitespace collapse (deterministic; no stemming — a guess is never made)."""
    s = unicodedata.normalize("NFKD", s.strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.casefold().split())


def _layer_query(con: Any, pack_dir: Path, layer_id: str) -> list[dict[str, Any]]:
    """Read a pack layer's rows: all attributes + bbox + a surface point."""
    path = pack_dir / f"{layer_id}.parquet"
    q = "'" + str(path).replace("'", "''") + "'"
    cols = [
        str(r[0])
        for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet({q})").fetchall()
        if r[0] != "geom"
    ]
    col_sql = ", ".join(f'"{c}"' for c in cols)
    rows = con.execute(
        f"""
        SELECT {col_sql},
               ST_XMin(geom) xmin, ST_YMin(geom) ymin,
               ST_XMax(geom) xmax, ST_YMax(geom) ymax,
               ST_X(ST_PointOnSurface(geom)) px, ST_Y(ST_PointOnSurface(geom)) py
        FROM read_parquet({q})
        """
    ).fetchall()
    return [
        dict(zip([*cols, "xmin", "ymin", "xmax", "ymax", "px", "py"], r, strict=True)) for r in rows
    ]


def _f(row: Mapping[str, Any], name: str | None) -> Any:
    """A layer attribute by spec field name (upper/lower-insensitive)."""
    if not name:
        return None
    if name in row:
        return row[name]
    for k, v in row.items():
        if k.lower() == name.lower():
            return v
    return None


def _dedupe_keep_order(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        v = str(v).strip()
        if v and _norm(v) not in seen:
            seen.add(_norm(v))
            out.append(v)
    return out


def _us_state_idents(geoid: str, usps: str) -> list[dict[str, str]]:
    """US state/territory identifier set per K4 §3.1 + the D-K4-4 ISO alias."""
    out = [
        {"scheme": "us.census.geoid.state", "value": geoid},
        {"scheme": "us.usps", "value": usps},
        {"scheme": "us.fips.state", "value": geoid},
    ]
    # D-K4-4: the ISO 3166-1 alpha-2 code is an *alias* where ISO publishes one
    # for the territory (PR, VI, GU, AS, MP all carry ISO codes).
    if usps in _US_TERRITORY_ISO_ALIAS:
        out.append({"scheme": "iso3166-1", "value": _US_TERRITORY_ISO_ALIAS[usps], "kind": "alias"})
    return out


#: US territories/DC: the ISO 3166-1 alpha-2 alias where ISO publishes one
#: (D-K4-4; the district has none). The rows stay keyed iso3166-2:US-* under US.
_US_TERRITORY_ISO_ALIAS: dict[str, str] = {
    "PR": "PR",
    "VI": "VI",
    "GU": "GU",
    "AS": "AS",
    "MP": "MP",
    "UM": "UM",
}
_US_TERRITORIES = frozenset(_US_TERRITORY_ISO_ALIAS)


def _bbox(row: Mapping[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(row["xmin"]),
        float(row["ymin"]),
        float(row["xmax"]),
        float(row["ymax"]),
    )


def build_registry(spec: PackSpec, pack_dir: Path | str) -> dict[str, Any]:
    """Derive the ``sig.jurisdiction-registry/1`` document from a verified pack.

    Layer order is significant: the US state layer is read first so county and
    place rows resolve ``parent`` through the STATEFP → state-jkey map; the
    Gazetteer layers then enrich US rows with names/internal points/ANSI ids.
    """
    import duckdb

    from . import boundary_pack as bp

    pack_dir = Path(pack_dir)
    failures = bp.verify_pack(pack_dir)
    if failures:
        raise BoundaryPackError(
            "registry build refuses an unverified pack:\n  " + "\n  ".join(failures)
        )
    manifest = bp.read_manifest(pack_dir)
    manifest_sha256 = sha256_hex((pack_dir / PACK_MANIFEST_NAME).read_bytes())
    con = duckdb.connect()
    bp._spatial(con)

    layer_by_id = {e["id"]: e for e in manifest["layers"]}
    rows: dict[str, Jurisdiction] = {}
    statefp_to_jkey: dict[str, str] = {}
    gaz: dict[str, dict[str, Any]] = {}  # geoid → {intpt, ansi, name}

    # Pass 0 — Gazetteer names/points (role us_names): keyed by declared geoid
    # field, they enrich the polygon layers' rows; they never mint keys.
    for layer in spec.layers:
        if layer.role != "us_names" or layer.id not in layer_by_id:
            continue
        fields = layer.fields
        for r in _layer_query(con, pack_dir, layer.id):
            geoid = str(_f(r, fields.get("geoid")) or "")
            if not geoid:
                continue
            gaz[geoid] = {
                "name": _f(r, fields.get("name")),
                "intpt": (float(r["xmin"]), float(r["ymin"])),
                "ansi": _f(r, fields.get("ansicode")),
            }

    for layer in spec.layers:
        if layer.id not in layer_by_id or not layer.mints_rows:
            continue
        fields = layer.fields
        src_rows = _layer_query(con, pack_dir, layer.id)
        if layer.rollup:
            # e.g. NE admin-1 GB local-authority units → ISO countries via
            # `geonunit` (K4 §3.1: GB rolls up to the ISO 3166-2 first tier);
            # every other row mints its `iso_3166_2` key normally.
            src_rows = _rollup_rows(con, pack_dir, layer, rows, src_rows)
        for r in src_rows:
            code = _f(r, fields.get("code"))
            name = str(_f(r, fields.get("name")) or "").strip()
            if not name:
                continue
            vintage = layer.vintage
            src = layer.source
            intpt = (float(r["px"]), float(r["py"])) if r.get("px") is not None else None
            bbox = _bbox(r) if r.get("xmin") is not None else None

            if layer.key_scheme == "iso3166-1":
                a2 = str(code or "").strip().upper()
                if len(a2) != 2:
                    continue  # NE `-99` etc.: no ISO code → no key (recorded, never invented)
                jkey = country_jkey(a2)
                code_status = "user-assigned" if a2 == "XK" else None  # D-K4-2
                ident = [{"scheme": "iso3166-1", "value": a2, "kind": "canonical"}]
                iso3 = str(_f(r, fields.get("iso3")) or "").strip()
                if iso3 and len(iso3) == 3:
                    ident.append({"scheme": "iso3166-1-a3", "value": iso3})
                alt = [str(_f(r, f) or "") for f in fields.get("alternates") or []]
                rows[jkey] = Jurisdiction(
                    jkey=jkey,
                    level="country",
                    name=name,
                    vintage=vintage,
                    source=src,
                    alternates=tuple(_dedupe_keep_order(alt)),
                    identifiers=tuple(ident),
                    parent=None,
                    bbox=bbox,
                    internal_point=intpt,
                    code_status=code_status,
                )
            elif layer.key_scheme == "iso3166-2":
                code_s = str(code or "").strip().upper()
                if not re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,3}", code_s):
                    continue  # un-codable admin-1 (K4: 13 NE units carry no ISO code)
                if code_s.startswith("US-"):
                    continue  # US admin-1 is Census-keyed (K4 §3.1 "Census for the US")
                jkey = admin1_jkey(code_s)
                ident = [{"scheme": "iso3166-2", "value": code_s, "kind": "canonical"}]
                adm1 = str(_f(r, fields.get("adm1_code")) or "").strip()
                if adm1:
                    ident.append({"scheme": "ne.adm1_code", "value": adm1})
                rows[jkey] = Jurisdiction(
                    jkey=jkey,
                    level="state_province",
                    name=name,
                    vintage=vintage,
                    source=src,
                    alternates=tuple(
                        _dedupe_keep_order(
                            str(_f(r, f) or "") for f in fields.get("alternates") or []
                        )
                    ),
                    identifiers=tuple(ident),
                    parent=country_jkey(code_s.split("-", 1)[0]),
                    bbox=bbox,
                    internal_point=intpt,
                )
            elif layer.key_scheme == "us.state_abbr":
                usps = str(code or "").strip().upper()
                geoid = str(_f(r, fields.get("geoid")) or "").strip()
                if len(usps) != 2 or not re.fullmatch(r"\d{2}", geoid):
                    continue
                jkey = admin1_jkey(f"US-{usps}")
                statefp_to_jkey[geoid] = jkey
                g = gaz.get(geoid) or {}
                if g.get("intpt"):
                    intpt = g["intpt"]
                ident = _us_state_idents(geoid, usps)
                if g.get("ansi"):
                    ident.append({"scheme": "us.gnis", "value": str(g["ansi"])})
                rows[jkey] = Jurisdiction(
                    jkey=jkey,
                    level="state_province",
                    name=name,
                    vintage=vintage,
                    source=src,
                    alternates=tuple(
                        _dedupe_keep_order(
                            [str(g.get("name") or ""), str(_f(r, fields.get("namelsad")) or "")]
                            + [str(_f(r, f) or "") for f in fields.get("alternates") or []]
                        )
                    ),
                    identifiers=tuple(ident),
                    parent="iso3166-1:US",
                    bbox=bbox,
                    internal_point=intpt,
                    note=(
                        "US territory — Census state-equivalent under iso3166-1:US "
                        "(D-K4-4); ISO 3166-1 alias carried in identifiers"
                        if usps in _US_TERRITORIES
                        else None
                    ),
                )
            elif layer.key_scheme == "us.census.geoid.county":
                geoid = str(_f(r, fields.get("geoid")) or "").strip()
                if not re.fullmatch(r"\d{5}", geoid):
                    continue
                jkey = county_jkey(geoid)
                g = gaz.get(geoid) or {}
                if g.get("intpt"):
                    intpt = g["intpt"]
                statefp = str(_f(r, fields.get("statefp")) or geoid[:2])
                ident = [
                    {"scheme": "us.census.geoid.county", "value": geoid, "kind": "canonical"},
                    {"scheme": "us.fips.county", "value": geoid},
                ]
                if g.get("ansi"):
                    ident.append({"scheme": "us.gnis", "value": str(g["ansi"])})
                rows[jkey] = Jurisdiction(
                    jkey=jkey,
                    level="county",
                    name=str(_f(r, fields.get("namelsad")) or name),
                    vintage=vintage,
                    source=src,
                    alternates=tuple(_dedupe_keep_order([name, str(g.get("name") or "")])),
                    identifiers=tuple(ident),
                    parent=statefp_to_jkey.get(statefp),
                    bbox=bbox,
                    internal_point=intpt,
                )
            elif layer.key_scheme == "us.census.geoid.place":
                geoid = str(_f(r, fields.get("geoid")) or "").strip()
                if not re.fullmatch(r"\d{7}", geoid):
                    continue
                jkey = place_jkey(geoid)
                g = gaz.get(geoid) or {}
                if g.get("intpt"):
                    intpt = g["intpt"]
                statefp = str(_f(r, fields.get("statefp")) or geoid[:2])
                ident = [
                    {"scheme": "us.census.geoid.place", "value": geoid, "kind": "canonical"},
                    {"scheme": "us.fips.place", "value": geoid},
                ]
                if g.get("ansi"):
                    ident.append({"scheme": "us.gnis", "value": str(g["ansi"])})
                rows[jkey] = Jurisdiction(
                    jkey=jkey,
                    level="municipality",
                    name=str(_f(r, fields.get("namelsad")) or name),
                    vintage=vintage,
                    source=src,
                    alternates=tuple(_dedupe_keep_order([name, str(g.get("name") or "")])),
                    identifiers=tuple(ident),
                    parent=statefp_to_jkey.get(statefp),
                    bbox=bbox,
                    internal_point=intpt,
                )
            elif layer.key_scheme.startswith("national:"):
                scheme = layer.key_scheme.split(":", 1)[1]
                code_s = str(code or "").strip()
                if not code_s:
                    continue
                parent_scheme = str(fields.get("parent_iso") or "")
                parent = country_jkey(parent_scheme) if parent_scheme else None
                rows[national_jkey(scheme, code_s)] = Jurisdiction(
                    jkey=national_jkey(scheme, code_s),
                    level=layer.level,
                    name=name,
                    vintage=vintage,
                    source=src,
                    alternates=tuple(
                        _dedupe_keep_order(
                            str(_f(r, f) or "") for f in fields.get("alternates") or []
                        )
                    ),
                    identifiers=({"scheme": scheme, "value": code_s, "kind": "canonical"},),
                    parent=parent,
                    bbox=bbox,
                    internal_point=intpt,
                )
            else:
                raise BoundaryPackError(
                    f"layer {layer.id!r}: unknown key_scheme {layer.key_scheme!r}"
                )

    row_list = [rows[k].to_row() for k in sorted(rows)]
    problems = validate_registry(row_list)
    if problems:
        raise BoundaryPackError(
            "the derived registry fails its invariants:\n  " + "\n  ".join(problems)
        )

    return {
        "schema": REGISTRY_SCHEMA,
        "license": spec.registry["license"],
        "attribution": list(spec.registry["attribution"]),
        "standing_note": spec.registry["standing_note"],
        "vintages": dict(sorted(spec.vintages.items())),
        "lookup_rules": LOOKUP_RULESET,
        "boundary_pack": {
            "pack_id": manifest["pack_id"],
            "boundaries_root": manifest["boundaries_root"],
            "manifest_sha256": manifest_sha256,
            "pack_manifest_path": PACK_MANIFEST_NAME,
        },
        "rows": row_list,
    }


def _rollup_rows(
    con: Any,
    pack_dir: Path,
    layer: Any,
    rows: dict[str, Jurisdiction],
    src_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Union fine-grained admin-1 features up to the ISO first tier.

    The declared case (K4 §3.1): NE admin-1 for GB is 232 local-authority
    units; ``geonunit`` rolls them to GB-ENG/SCT/WLS/NIR — the registry records
    the tier chosen per country (the rollup map is the record). Returns the
    rows NOT consumed by the rollup (every other country's admin-1 mints
    normally on its `iso_3166_2` code).
    """
    roll = layer.rollup
    field_name = str(roll["field"])
    prefix = str(roll["prefix"])
    mapping = {str(k): str(v) for k, v in dict(roll["map"]).items()}
    code_field = str(layer.fields.get("code") or "")
    rest: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in src_rows:
        code = str(_f(r, code_field) or "")
        unit = str(_f(r, field_name) or "")
        if code.startswith(f"{prefix}-") and unit in mapping:
            groups.setdefault(unit, []).append(r)
        else:
            rest.append(r)
    path = pack_dir / f"{layer.id}.parquet"
    q = "'" + str(path).replace("'", "''") + "'"
    for unit, _members in sorted(groups.items()):
        sub = mapping[unit]
        jkey = admin1_jkey(f"{prefix}-{sub}")
        esc = unit.replace("'", "''")
        agg = con.execute(
            f"""
            SELECT ST_XMin(g) xmin, ST_YMin(g) ymin, ST_XMax(g) xmax, ST_YMax(g) ymax,
                   ST_X(ST_PointOnSurface(g)) px, ST_Y(ST_PointOnSurface(g)) py
            FROM (SELECT ST_Union_Agg(geom) g FROM read_parquet({q})
                  WHERE "{field_name}" = '{esc}')
            """
        ).fetchone()
        ident = [{"scheme": "iso3166-2", "value": f"{prefix}-{sub}", "kind": "canonical"}]
        rows[jkey] = Jurisdiction(
            jkey=jkey,
            level="state_province",
            name=unit,
            vintage=layer.vintage,
            source=layer.source,
            identifiers=tuple(ident),
            parent=country_jkey(prefix),
            bbox=(float(agg[0]), float(agg[1]), float(agg[2]), float(agg[3])),
            internal_point=(float(agg[4]), float(agg[5])),
            note=f"rolled up from NE geonunit {unit!r} (K4 §3.1: first ISO 3166-2 tier)",
        )
    return rest


def write_registry(doc: Mapping[str, Any], path: Path | str) -> None:
    """Serialise the registry to canonical JSON (byte-stable; UTF-8 + newline)."""
    Path(path).write_bytes(canonical_json(dict(doc)))


def read_registry(path: Path | str) -> dict[str, Any]:
    """Read a ``sig.jurisdiction-registry/1`` document; fail closed on schema."""
    import json

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != REGISTRY_SCHEMA:
        raise BoundaryPackError(
            f"{path}: schema {doc.get('schema')!r}; expected {REGISTRY_SCHEMA!r}"
        )
    problems = validate_registry(doc.get("rows") or [])
    if problems:
        raise BoundaryPackError(
            f"{path}: registry fails its invariants:\n  " + "\n  ".join(problems)
        )
    return doc


# --------------------------------------------------------------------------- #
# lookup@1 (K4 §5.4)                                                           #
# --------------------------------------------------------------------------- #


def _ancestors(row: Mapping[str, Any], by_jkey: Mapping[str, Mapping[str, Any]]) -> set[str]:
    """The row's parent chain (its own key included — `within` is inclusive)."""
    out = {str(row["jkey"])}
    cur = row.get("parent")
    while cur:
        out.add(str(cur))
        nxt = by_jkey.get(str(cur))
        cur = nxt.get("parent") if nxt else None
    return out


def lookup(
    rows: Sequence[Mapping[str, Any]],
    name: str,
    *,
    level: str | None = None,
    within: str | None = None,
) -> list[dict[str, Any]]:
    """``lookup@1`` — the K4 §5.4 gazetteer contract.

    Exact official name (normalized) first, then alternates; ``level`` filters;
    ``within`` (a jkey) restricts to that subtree (the key itself included).
    Ambiguity returns every candidate — the consumer records ``name_ambiguous``
    (R8); this function never guesses.
    """
    if level is not None and level not in LEVELS:
        raise ValueError(f"level {level!r} not in {LEVELS}")
    by_jkey = {str(r["jkey"]): r for r in rows}
    want = _norm(name)
    hits: list[tuple[float, str, Mapping[str, Any], str]] = []
    for row in rows:
        if level is not None and row.get("level") != level:
            continue
        if within is not None and within not in _ancestors(row, by_jkey):
            continue
        if _norm(str(row.get("name") or "")) == want:
            hits.append((_SCORE_OFFICIAL, str(row["jkey"]), row, "official_name"))
            continue
        if any(_norm(str(a)) == want for a in row.get("alternates") or []):
            hits.append((_SCORE_ALTERNATE, str(row["jkey"]), row, "alternate_name"))
            continue
        for ident in row.get("identifiers") or []:
            if _norm(str(ident.get("value") or "")) == want:
                hits.append((_SCORE_IDENTIFIER, str(row["jkey"]), row, "identifier"))
                break
    hits.sort(key=lambda h: (-h[0], h[1]))
    return [
        {
            "jkey": h[2]["jkey"],
            "name": h[2]["name"],
            "level": h[2]["level"],
            "score": h[0],
            "basis": h[3],
            "rules": LOOKUP_RULESET,
        }
        for h in hits
    ]
