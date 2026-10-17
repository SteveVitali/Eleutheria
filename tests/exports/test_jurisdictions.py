# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.17 ``sig.jurisdiction-registry/1`` + ``lookup@1`` tests
(K4 §3.1/§3.2/§5.4, ADR-160).

The invariants under test: canonical scheme-named keys (never a bare code,
SIG-JUR-D01/SIG-IDENT-005/006), the declared-scheme map (K4 §3.2), the
D-K4-2 disputed-territory posture (XK user-assigned, neutral names, one
standing note — a posture, never an adjudication), the D-K4-4
territory-under-US keying, and the lookup contract: collisions return every
candidate (never a guess — R8's ``name_ambiguous`` is the consumer's record).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from boundary_pack_fixtures import build_fixture_pack, write_fixture_spec
from exports.boundary_pack import BoundaryPackError

from exports import boundary_pack as bp
from exports import jurisdictions as jr

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None,
    reason="duckdb is required for the registry build path",
)


@pytest.fixture(scope="module")
def registry_doc(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("reg")
    spec = bp.load_spec(write_fixture_spec(tmp / "spec.toml"))
    pack_dir, _manifest = build_fixture_pack(tmp, spec)
    return jr.build_registry(spec, pack_dir)


@pytest.fixture()
def rows(registry_doc: dict) -> list[dict]:
    return registry_doc["rows"]


def _by_jkey(rows: list[dict]) -> dict[str, dict]:
    return {r["jkey"]: r for r in rows}


def _jkeys(hits: list[dict]) -> set[str]:
    return {h["jkey"] for h in hits}


# --------------------------------------------------------------------------- #
# Canonical key families (K4 §3.1 — a jurisdiction is never keyed on a code)   #
# --------------------------------------------------------------------------- #


def test_key_families() -> None:
    assert jr.country_jkey("de") == "iso3166-1:DE"
    assert jr.admin1_jkey("us-mn") == "iso3166-2:US-MN"
    assert jr.admin1_jkey("ISO3166-2:GB-ENG") == "iso3166-2:GB-ENG"
    assert jr.county_jkey("27053") == "us.census.geoid.county:27053"
    assert jr.place_jkey("2743000") == "us.census.geoid.place:2743000"
    assert jr.national_jkey("de.ags", "05315000") == "de.ags:05315000"


def test_key_validation_rejects_bare_codes() -> None:
    # A bare "MN" or "US-MN" is never a key — the scheme is part of the key.
    assert not jr.valid_jkey("MN")
    assert not jr.valid_jkey("US-MN")
    assert not jr.valid_jkey("27053")
    assert jr.valid_jkey("iso3166-1:MN")
    assert jr.valid_jkey("iso3166-2:US-MN")
    assert jr.valid_jkey("us.census.geoid.county:27053")
    assert jr.valid_jkey("de.ags:05315000")


def test_national_jkey_refuses_reserved_scheme() -> None:
    with pytest.raises(ValueError, match="reserved"):
        jr.national_jkey("iso3166-1", "DE")


def test_fixed_width_enforced() -> None:
    with pytest.raises(ValueError, match="5 digits"):
        jr.county_jkey("2705")
    with pytest.raises(ValueError, match="7 digits"):
        jr.place_jkey("274300")


# --------------------------------------------------------------------------- #
# The declared-scheme map (K4 §3.2)                                            #
# --------------------------------------------------------------------------- #


def test_declared_scheme_map() -> None:
    assert jr.key_for_declared("us.state_abbr", "mn") == "iso3166-2:US-MN"
    assert jr.key_for_declared("iso.3166_1_alpha2", "mn") == "iso3166-1:MN"
    assert jr.key_for_declared("iso.3166_2", "DE-NW") == "iso3166-2:DE-NW"
    # sig.unresolved has no key — an unresolved jurisdiction is not invented.
    assert jr.key_for_declared("sig.unresolved", "somewhere") is None


def test_declared_scheme_unknown_fails_closed() -> None:
    with pytest.raises(ValueError, match="never guessed"):
        jr.key_for_declared("free.text", "MN")


# --------------------------------------------------------------------------- #
# Registry validation invariants (fail closed on structure)                    #
# --------------------------------------------------------------------------- #


def _row(jkey: str, level: str = "country", **kw: object) -> dict:
    return {
        "jkey": jkey,
        "level": level,
        "name": kw.pop("name", "X"),
        "alternates": [],
        "identifiers": [{"scheme": "s", "value": jkey}],
        "vintage": "v1",
        "source": "s",
        **kw,
    }


def test_validate_rejects_duplicate_jkey() -> None:
    rows = [_row("iso3166-1:DE"), _row("iso3166-1:DE")]
    assert any("duplicate" in f for f in jr.validate_registry(rows))


def test_validate_rejects_bad_level() -> None:
    assert jr.validate_registry([_row("iso3166-1:DE", level="planet")])


def test_validate_rejects_unresolvable_parent() -> None:
    rows = [
        _row("iso3166-1:DE"),
        _row("iso3166-2:DE-NW", level="state_province", parent="iso3166-1:FR"),
    ]
    assert any("parent" in f for f in jr.validate_registry(rows))


def test_validate_rejects_identifier_collision() -> None:
    # (scheme, value) resolving to two keys is the SIG-IDENT-006 violation —
    # an "ID" identifier on Indonesia AND on Idaho without scheme separation.
    rows = [
        _row(
            "iso3166-1:ID",
            identifiers=[{"scheme": "dup", "value": "ID", "kind": "code"}],
        ),
        _row(
            "iso3166-2:US-ID",
            level="state_province",
            parent="iso3166-1:ID",
            identifiers=[{"scheme": "dup", "value": "ID", "kind": "code"}],
        ),
    ]
    assert any("SIG-IDENT-006" in f for f in jr.validate_registry(rows))


# --------------------------------------------------------------------------- #
# build_registry — pack → rows                                                 #
# --------------------------------------------------------------------------- #


def test_registry_doc_shape(registry_doc: dict) -> None:
    assert registry_doc["schema"] == "sig.jurisdiction-registry/1"
    assert registry_doc["license"] == "CC-BY-4.0"
    assert registry_doc["lookup_rules"] == "lookup@1"
    assert registry_doc["standing_note"]  # D-K4-2
    assert registry_doc["boundary_pack"]["boundaries_root"]
    assert registry_doc["boundary_pack"]["manifest_sha256"]


def test_registry_mints_all_levels(rows: list[dict]) -> None:
    keys = _by_jkey(rows)
    # countries
    for a2 in ("US", "ID", "MN", "DE", "GB", "TW", "PS", "HK", "EH", "XK"):
        assert f"iso3166-1:{a2}" in keys
    # admin-1
    assert "iso3166-2:US-MN" in keys
    assert "iso3166-2:DE-NW" in keys
    # GB rollup: the two England units collapse to the ISO first tier.
    assert "iso3166-2:GB-ENG" in keys
    assert "iso3166-2:GB-NIR" in keys
    assert "iso3166-2:GB-LND" not in keys  # rolled up, never double-keyed
    assert "iso3166-2:GB-MAN" not in keys
    # US admin-1 in the NE layer mints no key (Census is the US truth).
    assert not any(r["source"] == "fx_ne" and r["jkey"].startswith("iso3166-2:US-") for r in rows)
    # county + place + national municipality
    assert "us.census.geoid.county:27053" in keys
    assert "us.census.geoid.place:2743000" in keys
    assert "de.ags:05315000" in keys
    # The un-codable rows mint no key.
    assert not any(r["name"] == "Nowhereland" for r in rows)
    assert not any(r["name"] == "Unmapped Province" for r in rows)


def test_registry_parentage(rows: list[dict]) -> None:
    keys = _by_jkey(rows)
    assert keys["iso3166-2:US-MN"]["parent"] == "iso3166-1:US"
    assert keys["us.census.geoid.county:27053"]["parent"] == "iso3166-2:US-MN"
    assert keys["us.census.geoid.place:2743000"]["parent"] == "iso3166-2:US-MN"
    assert keys["iso3166-2:DE-NW"]["parent"] == "iso3166-1:DE"
    assert keys["iso3166-2:GB-ENG"]["parent"] == "iso3166-1:GB"
    assert keys["de.ags:05315000"]["parent"] == "iso3166-1:DE"
    assert "parent" not in keys["iso3166-1:US"]


def test_d_k4_4_territory_posture(rows: list[dict]) -> None:
    keys = _by_jkey(rows)
    pr = keys["iso3166-2:US-PR"]
    assert pr["parent"] == "iso3166-1:US"
    assert pr["level"] == "state_province"
    # The ISO 3166-1 code is carried as an *alias* — never the key.
    aliases = [i for i in pr["identifiers"] if i["scheme"] == "iso3166-1"]
    assert aliases == [{"scheme": "iso3166-1", "value": "PR", "kind": "alias"}]
    assert "territory" in (pr.get("note") or "").lower()


def test_d_k4_2_disputed_posture(registry_doc: dict) -> None:
    keys = _by_jkey(registry_doc["rows"])
    # XK is user-assigned; the other disputed codes carry no special status.
    assert keys["iso3166-1:XK"]["code_status"] == "user-assigned"
    for a2 in ("TW", "PS", "HK", "EH"):
        assert "code_status" not in keys[f"iso3166-1:{a2}"]
    assert "user-assigned" in registry_doc["standing_note"] or (
        "Disputed" in registry_doc["standing_note"]
    )


def test_registry_identifiers_scheme_keyed(rows: list[dict]) -> None:
    keys = _by_jkey(rows)
    mn = keys["iso3166-2:US-MN"]
    idents = {(i["scheme"], i["value"]) for i in mn["identifiers"]}
    assert ("us.usps", "MN") in idents
    assert ("us.census.geoid.state", "27") in idents
    # Gazetteer enrichment: GNIS/ANSI id carried, internal point preferred.
    assert any(i[0] == "us.gnis" for i in idents)
    assert mn["internal_point"] == [-94.0, 46.0]
    de = keys["iso3166-1:DE"]
    assert ("iso3166-1-a3", "DEU") in {(i["scheme"], i["value"]) for i in de["identifiers"]}


def test_registry_doc_is_deterministic(tmp_path: Path, registry_doc: dict) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    jr.write_registry(registry_doc, a)
    jr.write_registry(registry_doc, b)
    assert a.read_bytes() == b.read_bytes()
    # Canonical JSON is re-readable and validates.
    assert jr.read_registry(a)["schema"] == "sig.jurisdiction-registry/1"


def test_read_registry_fails_closed_on_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "sig.other/1", "rows": []}))
    with pytest.raises(BoundaryPackError):
        jr.read_registry(bad)


def test_build_refuses_unverified_pack(tmp_path: Path, registry_doc: dict) -> None:
    spec = bp.load_spec(write_fixture_spec(tmp_path / "spec.toml"))
    pack_dir, _m = build_fixture_pack(tmp_path / "x", spec)
    (pack_dir / "cb_500k.parquet").unlink()
    with pytest.raises(BoundaryPackError, match="unverified"):
        jr.build_registry(spec, pack_dir)


# --------------------------------------------------------------------------- #
# lookup@1 (K4 §5.4)                                                           #
# --------------------------------------------------------------------------- #


def test_lookup_id_collision(rows: list[dict]) -> None:
    hits = jr.lookup(rows, "ID")
    keys = _jkeys(hits)
    assert keys == {"iso3166-1:ID", "iso3166-2:US-ID"}
    # Disambiguation is by filter — never a guess.
    assert _jkeys(jr.lookup(rows, "ID", level="country")) == {"iso3166-1:ID"}
    assert _jkeys(jr.lookup(rows, "ID", within="iso3166-1:US")) == {"iso3166-2:US-ID"}


def test_lookup_mn_collision(rows: list[dict]) -> None:
    assert _jkeys(jr.lookup(rows, "MN")) == {
        "iso3166-1:MN",
        "iso3166-2:US-MN",
    }
    assert _jkeys(jr.lookup(rows, "MN", level="state_province")) == {"iso3166-2:US-MN"}


def test_lookup_de_collision(rows: list[dict]) -> None:
    assert _jkeys(jr.lookup(rows, "DE")) == {
        "iso3166-1:DE",
        "iso3166-2:US-DE",
    }


def test_lookup_cologne_two_sides(rows: list[dict]) -> None:
    hits = jr.lookup(rows, "Cologne")
    keys = _jkeys(hits)
    assert keys == {"us.census.geoid.place:2712670", "de.ags:05315000"}
    # Both sides surface through the alternate-name channel (the place's
    # official NAMELSAD name is "Cologne city"; Köln's alternate is "Cologne")
    # — an honest ambiguity: every candidate, never a guess.
    by_key = {h["jkey"]: h for h in hits}
    assert by_key["us.census.geoid.place:2712670"]["basis"] == "alternate_name"
    assert by_key["de.ags:05315000"]["basis"] == "alternate_name"
    # And the official-name channels still resolve each side directly.
    assert _jkeys(jr.lookup(rows, "Cologne city")) == {"us.census.geoid.place:2712670"}
    # `within` resolves the ambiguity deterministically.
    assert _jkeys(jr.lookup(rows, "Cologne", within="iso3166-1:DE")) == {"de.ags:05315000"}


def test_lookup_official_name_and_alternates(rows: list[dict]) -> None:
    assert _jkeys(jr.lookup(rows, "Minnesota")) == {"iso3166-2:US-MN"}
    # Case/accents normalised; Köln matches both spellings.
    assert _jkeys(jr.lookup(rows, "köln")) == {"de.ags:05315000"}
    # Germany by its German-language alternate.
    assert "iso3166-1:DE" in _jkeys(jr.lookup(rows, "Deutschland"))


def test_lookup_identifier_hits(rows: list[dict]) -> None:
    # A full GEOID value resolves through the identifier channel.
    assert _jkeys(jr.lookup(rows, "27053")) == {"us.census.geoid.county:27053"}
    # The alpha-3 identifier resolves too.
    assert _jkeys(jr.lookup(rows, "DEU")) == {"iso3166-1:DE"}


def test_lookup_no_match_returns_empty(rows: list[dict]) -> None:
    assert jr.lookup(rows, "Atlantis") == []


def test_lookup_rejects_unknown_level(rows: list[dict]) -> None:
    with pytest.raises(ValueError, match="level"):
        jr.lookup(rows, "X", level="planet")


def test_lookup_within_includes_self(rows: list[dict]) -> None:
    assert _jkeys(jr.lookup(rows, "Minnesota", within="iso3166-2:US-MN")) == {"iso3166-2:US-MN"}


def test_lookup_candidates_carry_ruleset(rows: list[dict]) -> None:
    hits = jr.lookup(rows, "ID")
    assert all(h["rules"] == "lookup@1" for h in hits)
    assert all(h["basis"] in jr.LOOKUP_BASES for h in hits)


# --------------------------------------------------------------------------- #
# The sig-exports boundaries CLI surface                                       #
# --------------------------------------------------------------------------- #


def test_cli_lookup_and_validate(
    tmp_path: Path, registry_doc: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    from exports.cli import main

    reg = tmp_path / "jurisdictions.json"
    jr.write_registry(registry_doc, reg)
    assert main(["boundaries", "validate", "--registry", str(reg)]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "boundaries",
                "lookup",
                "--registry",
                str(reg),
                "--name",
                "MN",
                "--within",
                "iso3166-1:US",
            ]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out)
    assert [c["jkey"] for c in out["candidates"]] == ["iso3166-2:US-MN"]


def test_cli_build_gate_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from boundary_pack_fixtures import write_fixture_inputs
    from exports.cli import main

    inputs = write_fixture_inputs(tmp_path / "inputs")
    spec = write_fixture_spec(tmp_path / "spec.toml")
    reg = tmp_path / "sources.toml"
    from boundary_pack_fixtures import write_fixture_registry

    write_fixture_registry(reg)
    rc = main(
        [
            "boundaries",
            "build",
            "--spec",
            str(spec),
            "--inputs",
            str(inputs),
            "--out",
            str(tmp_path / "pack"),
            "--sources-toml",
            str(reg),
        ]
    )
    assert rc == 4
    assert "refused" in capsys.readouterr().out
