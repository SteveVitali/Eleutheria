# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared fixture inputs for the P35.17 boundary-pack / jurisdiction-registry
suite (K4 §3.1/§4.2/§5.4, ADR-160).

The fixture inputs are **declared stand-ins**, never captured upstream bytes:
``build_pack`` is driven with ``fixture_inputs=True`` so the emitted manifest
honestly records ``gate.mode = "fixture-bypass"``. The shapefile-family layers
are expressed as GeoJSON (the spec's own format vocabulary admits ``geojson``)
because the tests exercise the pack/registry machinery, not the GDAL shapefile
reader — the zip/dir resolution detector is covered directly in
``test_boundary_pack.py``.

The data deliberately stages the ticket's collision + posture fixtures:

* ``ID`` — ISO 3166-1 alpha-2 for **Indonesia** *and* the USPS code for
  **Idaho** (K4 §3.1/§5.4 ambiguity fixture).
* ``MN`` — ISO alpha-2 for **Mongolia** *and* USPS for **Minnesota**.
* ``DE`` — ISO alpha-2 for **Germany** *and* USPS for **Delaware**; plus
  Cologne-as-Köln (``de.ags:05315000``) versus the real Cologne, Minnesota
  place GEOID — the name-vs-code collision the lookup must not guess on.
* Disputed territories per D-K4-2 — TW / PS / HK / EH keyed on the ISO
  3166-1 codes as published, plus ``XK`` Kosovo labelled
  ``code_status = "user-assigned"``.
* D-K4-4 territory-under-US — Puerto Rico keyed ``iso3166-2:US-PR`` under
  ``iso3166-1:US`` with its ISO 3166-1 code carried as an *alias* identifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


#: A small box polygon around (x, y) — geometry is a stand-in, never surveyed.
def _poly(x: float, y: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[[x, y], [x + 1.0, y], [x + 1.0, y + 1.0], [x, y + 1.0], [x, y]]],
    }


def _geojson(features: list[dict[str, Any]]) -> str:
    return json.dumps({"type": "FeatureCollection", "features": features}, sort_keys=True)


def _feat(props: dict[str, Any], x: float, y: float) -> dict[str, Any]:
    return {"type": "Feature", "properties": props, "geometry": _poly(x, y)}


# --------------------------------------------------------------------------- #
# TIGER/Line stand-ins (GeoJSON carrying the real TIGER column names)          #
# --------------------------------------------------------------------------- #

TIGER_STATE = _geojson(
    [
        _feat(
            {"STUSPS": "MN", "GEOID": "27", "NAME": "Minnesota", "NAMELSAD": "Minnesota"},
            -94.0,
            46.0,
        ),
        _feat(
            {"STUSPS": "ID", "GEOID": "16", "NAME": "Idaho", "NAMELSAD": "Idaho"},
            -114.0,
            44.0,
        ),
        _feat(
            {"STUSPS": "DE", "GEOID": "10", "NAME": "Delaware", "NAMELSAD": "Delaware"},
            -75.5,
            39.0,
        ),
        # D-K4-4: a territory row — keyed iso3166-2:US-PR under iso3166-1:US,
        # with its published ISO 3166-1 code carried as an alias identifier.
        _feat(
            {"STUSPS": "PR", "GEOID": "72", "NAME": "Puerto Rico", "NAMELSAD": "Puerto Rico"},
            -66.5,
            18.2,
        ),
    ]
)

TIGER_COUNTY = _geojson(
    [
        _feat(
            {"GEOID": "27053", "STATEFP": "27", "NAME": "Hennepin", "NAMELSAD": "Hennepin County"},
            -93.5,
            45.0,
        ),
        _feat(
            {"GEOID": "27123", "STATEFP": "27", "NAME": "Ramsey", "NAMELSAD": "Ramsey County"},
            -93.0,
            45.0,
        ),
    ]
)

TIGER_PLACE = _geojson(
    [
        _feat(
            {
                "GEOID": "2743000",
                "STATEFP": "27",
                "NAME": "Minneapolis",
                "NAMELSAD": "Minneapolis city",
            },
            -93.3,
            44.9,
        ),
        # The US-side of the Cologne collision: a Census place named exactly
        # "Cologne" (the real Cologne, MN GEOID) versus de.ags Köln.
        _feat(
            {"GEOID": "2712670", "STATEFP": "27", "NAME": "Cologne", "NAMELSAD": "Cologne city"},
            -93.8,
            44.7,
        ),
    ]
)

CB_500K = _geojson([_feat({"NAME": "Minnesota"}, -94.0, 46.0)])

# --------------------------------------------------------------------------- #
# Gazetteer stand-ins (tab-delimited, the real Gazetteer column names)          #
# --------------------------------------------------------------------------- #

GAZETTEER_STATE = "\n".join(
    [
        "GEOID\tANSICODE\tNAME\tINTPTLAT\tINTPTLONG",
        "27\t01779779\tMinnesota\t46.0000\t-94.0000",
        "16\t01779780\tIdaho\t44.0000\t-114.0000",
        "10\t01779781\tDelaware\t39.0000\t-75.5000",
        "72\t01779782\tPuerto Rico\t18.2000\t-66.5000",
        "",
    ]
)

GAZETTEER_COUNTY = "\n".join(
    [
        "GEOID\tANSICODE\tNAME\tINTPTLAT\tINTPTLONG",
        "27053\t00659404\tHennepin County\t45.0000\t-93.5000",
        "27123\t00659405\tRamsey County\t45.0000\t-93.0000",
        "",
    ]
)

GAZETTEER_PLACE = "\n".join(
    [
        "GEOID\tANSICODE\tNAME\tINTPTLAT\tINTPTLONG",
        "2743000\t00655402\tMinneapolis\t44.9000\t-93.3000",
        "2712670\t00655403\tCologne\t44.7000\t-93.8000",
        "",
    ]
)

# --------------------------------------------------------------------------- #
# Natural Earth stand-ins                                                      #
# --------------------------------------------------------------------------- #

NE_ADMIN0 = _geojson(
    [
        _feat(
            {
                "ISO_A2_EH": "US",
                "ADM0_A3": "USA",
                "NAME_EN": "United States of America",
                "NAME": "United States",
                "NAME_LONG": "United States of America",
                "NAME_SORT": "United States",
                "NAME_FR": "États-Unis",
                "NAME_DE": "Vereinigte Staaten",
                "FORMAL_EN": "United States of America",
            },
            -98.0,
            39.0,
        ),
        _feat(
            {
                "ISO_A2_EH": "ID",
                "ADM0_A3": "IDN",
                "NAME_EN": "Indonesia",
                "NAME": "Indonesia",
                "NAME_LONG": "Indonesia",
                "NAME_SORT": "Indonesia",
                "NAME_FR": "Indonésie",
                "NAME_DE": "Indonesien",
                "FORMAL_EN": "Republic of Indonesia",
            },
            114.0,
            -2.0,
        ),
        _feat(
            {
                "ISO_A2_EH": "MN",
                "ADM0_A3": "MNG",
                "NAME_EN": "Mongolia",
                "NAME": "Mongolia",
                "NAME_LONG": "Mongolia",
                "NAME_SORT": "Mongolia",
                "NAME_FR": "Mongolie",
                "NAME_DE": "Mongolei",
                "FORMAL_EN": "Mongolia",
            },
            103.0,
            46.0,
        ),
        _feat(
            {
                "ISO_A2_EH": "DE",
                "ADM0_A3": "DEU",
                "NAME_EN": "Germany",
                "NAME": "Germany",
                "NAME_LONG": "Germany",
                "NAME_SORT": "Germany",
                "NAME_FR": "Allemagne",
                "NAME_DE": "Deutschland",
                "FORMAL_EN": "Federal Republic of Germany",
            },
            10.0,
            51.0,
        ),
        _feat(
            {
                "ISO_A2_EH": "GB",
                "ADM0_A3": "GBR",
                "NAME_EN": "United Kingdom",
                "NAME": "United Kingdom",
                "NAME_LONG": "United Kingdom",
                "NAME_SORT": "United Kingdom",
                "NAME_FR": "Royaume-Uni",
                "NAME_DE": "Vereinigtes Königreich",
                "FORMAL_EN": "United Kingdom of Great Britain and Northern Ireland",
            },
            -2.0,
            54.0,
        ),
        # D-K4-2 rows: ISO 3166-1 codes as published + XK user-assigned.
        _feat(
            {
                "ISO_A2_EH": "TW",
                "ADM0_A3": "TWN",
                "NAME_EN": "Taiwan",
                "NAME": "Taiwan",
                "NAME_LONG": "Taiwan",
                "NAME_SORT": "Taiwan",
                "NAME_FR": "Taïwan",
                "NAME_DE": "Taiwan",
                "FORMAL_EN": "",
            },
            121.0,
            23.5,
        ),
        _feat(
            {
                "ISO_A2_EH": "PS",
                "ADM0_A3": "PSE",
                "NAME_EN": "Palestine",
                "NAME": "Palestine",
                "NAME_LONG": "Palestine",
                "NAME_SORT": "Palestine",
                "NAME_FR": "Palestine",
                "NAME_DE": "Palästina",
                "FORMAL_EN": "",
            },
            35.2,
            31.9,
        ),
        _feat(
            {
                "ISO_A2_EH": "HK",
                "ADM0_A3": "HKG",
                "NAME_EN": "Hong Kong",
                "NAME": "Hong Kong",
                "NAME_LONG": "Hong Kong",
                "NAME_SORT": "Hong Kong",
                "NAME_FR": "Hong Kong",
                "NAME_DE": "Hongkong",
                "FORMAL_EN": "",
            },
            114.1,
            22.3,
        ),
        _feat(
            {
                "ISO_A2_EH": "EH",
                "ADM0_A3": "ESH",
                "NAME_EN": "Western Sahara",
                "NAME": "Western Sahara",
                "NAME_LONG": "Western Sahara",
                "NAME_SORT": "Western Sahara",
                "NAME_FR": "Sahara occidental",
                "NAME_DE": "Westsahara",
                "FORMAL_EN": "",
            },
            -13.0,
            24.5,
        ),
        # Kosovo: XK is user-assigned (NE ships -99 in ISO_A2; the fixture
        # declares XK in the code field to exercise the D-K4-2 code_status path).
        _feat(
            {
                "ISO_A2_EH": "XK",
                "ADM0_A3": "XKX",
                "NAME_EN": "Kosovo",
                "NAME": "Kosovo",
                "NAME_LONG": "Kosovo",
                "NAME_SORT": "Kosovo",
                "NAME_FR": "Kosovo",
                "NAME_DE": "Kosovo",
                "FORMAL_EN": "",
            },
            20.9,
            42.6,
        ),
        # A row with no ISO code mints no key — recorded, never invented.
        _feat(
            {
                "ISO_A2_EH": "-99",
                "ADM0_A3": "-99",
                "NAME_EN": "Nowhereland",
                "NAME": "Nowhereland",
                "NAME_LONG": "Nowhereland",
                "NAME_SORT": "Nowhereland",
                "NAME_FR": "",
                "NAME_DE": "",
                "FORMAL_EN": "",
            },
            0.0,
            -80.0,
        ),
    ]
)

NE_ADMIN1 = _geojson(
    [
        # DE-NW mints iso3166-2:DE-NW normally (parent iso3166-1:DE).
        _feat(
            {
                "iso_3166_2": "DE-NW",
                "adm1_code": "DEU-3462",
                "name": "Nordrhein-Westfalen",
                "name_en": "North Rhine-Westphalia",
                "name_alt": "",
                "name_local": "",
                "geonunit": "Germany",
            },
            6.5,
            51.5,
        ),
        # GB local-authority units roll up to the ISO 3166-2 first tier via
        # geonunit (K4 §3.1) — two England units → one iso3166-2:GB-ENG row.
        _feat(
            {
                "iso_3166_2": "GB-LND",
                "adm1_code": "GBR-1",
                "name": "Greater London",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "England",
            },
            -0.1,
            51.5,
        ),
        _feat(
            {
                "iso_3166_2": "GB-MAN",
                "adm1_code": "GBR-2",
                "name": "Greater Manchester",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "England",
            },
            -2.2,
            53.5,
        ),
        _feat(
            {
                "iso_3166_2": "GB-BEL",
                "adm1_code": "GBR-3",
                "name": "Belfast",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "Northern Ireland",
            },
            -5.9,
            54.6,
        ),
        # A US admin-1 row in the NE layer mints no key — Census is the US
        # admin-1 source of truth (K4 §3.1).
        _feat(
            {
                "iso_3166_2": "US-MN",
                "adm1_code": "USA-1",
                "name": "Minnesota (NE duplicate)",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "United States",
            },
            -94.0,
            46.0,
        ),
        # An un-codable admin-1 row mints no key (recorded, never invented).
        _feat(
            {
                "iso_3166_2": "",
                "adm1_code": "ZZZ-1",
                "name": "Unmapped Province",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "Nowhereland",
            },
            0.0,
            -79.0,
        ),
    ]
)

# The non-US municipality family (K4 §3.1): a national-scheme layer keyed
# de.ags:<AGS> — Cologne/Köln is the DE-side of the Cologne collision.
DE_AGS = _geojson(
    [
        _feat(
            {"AGS": "05315000", "NAME": "Köln", "NAME_EN": "Cologne"},
            6.9,
            50.9,
        ),
        _feat(
            {"AGS": "05316000", "NAME": "Düsseldorf", "NAME_EN": "Dusseldorf"},
            6.8,
            51.2,
        ),
    ]
)


# --------------------------------------------------------------------------- #
# The fixture spec — the same sig.boundary-pack/1 vocabulary as the production  #
# file, narrowed to fixture formats + fixture source ids.                       #
# --------------------------------------------------------------------------- #

FIXTURE_SPEC_TOML = """\
[pack]
schema = "sig.boundary-pack/1"
pack_id = "boundaries-fixture-2025"

[pack.vintages]
tiger = "tiger-2025"
gazetteer = "gazetteer-2025"
natural_earth = "ne-5.1"

[registry]
license = "CC-BY-4.0"
attribution = ["fixture stand-in upstreams — never captured evidence"]
standing_note = "fixture: Disputed territories follow D-K4-2 (XK user-assigned)"

[[layers]]
id = "tiger_state"
source = "fx_tiger"
file = "tiger_state.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "state_province"
key_scheme = "us.state_abbr"
[layers.fields]
code = "STUSPS"
geoid = "GEOID"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "tiger_county"
source = "fx_tiger"
file = "tiger_county.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "county"
key_scheme = "us.census.geoid.county"
[layers.fields]
geoid = "GEOID"
statefp = "STATEFP"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "tiger_place"
source = "fx_tiger"
file = "tiger_place.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "municipality"
key_scheme = "us.census.geoid.place"
[layers.fields]
geoid = "GEOID"
statefp = "STATEFP"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "gazetteer_state"
source = "fx_tiger"
file = "gazetteer_state.txt"
format = "gazetteer-txt"
role = "us_names"
vintage = "gazetteer-2025"
level = ""
key_scheme = ""
[layers.fields]
geoid = "GEOID"
ansicode = "ANSICODE"
name = "NAME"
intptlat = "INTPTLAT"
intptlong = "INTPTLONG"

[[layers]]
id = "gazetteer_county"
source = "fx_tiger"
file = "gazetteer_county.txt"
format = "gazetteer-txt"
role = "us_names"
vintage = "gazetteer-2025"
level = ""
key_scheme = ""
[layers.fields]
geoid = "GEOID"
ansicode = "ANSICODE"
name = "NAME"
intptlat = "INTPTLAT"
intptlong = "INTPTLONG"

[[layers]]
id = "gazetteer_place"
source = "fx_tiger"
file = "gazetteer_place.txt"
format = "gazetteer-txt"
role = "us_names"
vintage = "gazetteer-2025"
level = ""
key_scheme = ""
[layers.fields]
geoid = "GEOID"
ansicode = "ANSICODE"
name = "NAME"
intptlat = "INTPTLAT"
intptlong = "INTPTLONG"

[[layers]]
id = "cb_500k"
source = "fx_tiger"
file = "cb_500k.geojson"
format = "geojson"
role = "us_display"
vintage = "tiger-2025"
level = ""
key_scheme = ""
[layers.fields]
name = "NAME"

[[layers]]
id = "ne_admin0"
source = "fx_ne"
file = "ne_admin0.geojson"
format = "geojson"
role = "non_us"
vintage = "ne-5.1"
level = "country"
key_scheme = "iso3166-1"
[layers.fields]
code = "ISO_A2_EH"
iso3 = "ADM0_A3"
name = "NAME_EN"
alternates = ["NAME", "NAME_LONG", "NAME_SORT", "NAME_FR", "NAME_DE", "FORMAL_EN"]

[[layers]]
id = "ne_admin1"
source = "fx_ne"
file = "ne_admin1.geojson"
format = "geojson"
role = "non_us"
vintage = "ne-5.1"
level = "state_province"
key_scheme = "iso3166-2"
[layers.fields]
code = "iso_3166_2"
adm1_code = "adm1_code"
name = "name"
alternates = ["name_en", "name_alt", "name_local"]
[layers.rollup]
field = "geonunit"
prefix = "GB"
map = { "England" = "ENG", "Scotland" = "SCT", "Wales" = "WLS", "Northern Ireland" = "NIR" }

[[layers]]
id = "de_ags"
source = "fx_national"
file = "de_ags.geojson"
format = "geojson"
role = "national"
vintage = "ne-5.1"
level = "municipality"
key_scheme = "national:de.ags"
[layers.fields]
code = "AGS"
name = "NAME"
parent_iso = "DE"
alternates = ["NAME_EN"]
"""

FIXTURE_INPUTS: dict[str, str] = {
    "tiger_state.geojson": TIGER_STATE,
    "tiger_county.geojson": TIGER_COUNTY,
    "tiger_place.geojson": TIGER_PLACE,
    "cb_500k.geojson": CB_500K,
    "gazetteer_state.txt": GAZETTEER_STATE,
    "gazetteer_county.txt": GAZETTEER_COUNTY,
    "gazetteer_place.txt": GAZETTEER_PLACE,
    "ne_admin0.geojson": NE_ADMIN0,
    "ne_admin1.geojson": NE_ADMIN1,
    "de_ags.geojson": DE_AGS,
}

#: The gate-test registry: the fixture spec's sources, in both gate states.
FIXTURE_SOURCES_TOML = """\
[sources.fx_tiger]
name = "fixture TIGER stand-in"
ingestion_permitted = false

[sources.fx_ne]
name = "fixture Natural Earth stand-in"
ingestion_permitted = false

[sources.fx_national]
name = "fixture national stand-in"
ingestion_permitted = false
"""

FIXTURE_SOURCES_TOML_PERMITTED = FIXTURE_SOURCES_TOML.replace(
    "ingestion_permitted = false", "ingestion_permitted = true"
)


def write_fixture_inputs(inputs_dir: Path) -> Path:
    """Materialise the fixture input files + spec + a denied source registry."""
    inputs_dir.mkdir(parents=True, exist_ok=True)
    for name, content in FIXTURE_INPUTS.items():
        (inputs_dir / name).write_text(content, encoding="utf-8")
    return inputs_dir


def write_fixture_spec(path: Path) -> Path:
    path.write_text(FIXTURE_SPEC_TOML, encoding="utf-8")
    return path


def write_fixture_registry(path: Path, *, permitted: bool = False) -> Path:
    path.write_text(
        FIXTURE_SOURCES_TOML_PERMITTED if permitted else FIXTURE_SOURCES_TOML,
        encoding="utf-8",
    )
    return path


def build_fixture_pack(tmp_path: Path, spec: Any) -> tuple[Path, dict[str, Any]]:
    """Build the fixture pack under ``tmp_path`` (fixture_inputs=True — the
    manifest honestly records the bypass; the ingestion gate is not exercised)."""
    from exports import boundary_pack as bp

    inputs = write_fixture_inputs(tmp_path / "inputs")
    out = tmp_path / "pack"
    manifest = bp.build_pack(spec, inputs, out, fixture_inputs=True)
    return out, manifest
