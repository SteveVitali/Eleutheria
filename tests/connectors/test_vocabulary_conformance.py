# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.14a connector-output vocabulary conformance (SIG-TRUST-001 / L1 NEW-2).

The claim sink's vocabulary is closed: a predicate id, artifact genre, or enum
value that is not in the generated ontology registry never lands — it quarantines.
This suite mechanically enumerates the vocabulary surface connectors can emit
and asserts every member is registered in ``ontology/generated``:

* every ``*_predicate_allowlist`` entry in every ``*_vocab.toml``;
* every ``predicate_id`` literal a connector module stamps on a claim;
* every ``artifact_genre`` mapping + ``evidence_genre`` literal a connector
  can stamp;
* the OSM ``[mobility]`` map's targets against the ontology ``Mobility`` enum.

A planted-violation test proves the gate is a gate: an invented id fails the
same check the real surface passes.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_CONNECTORS = REPO_ROOT / "connectors" / "src" / "connectors"
_DATA = _CONNECTORS / "data"
_GENERATED = REPO_ROOT / "ontology" / "generated"
_REGISTRY = _GENERATED / "registry" / "predicate_registry.json"
_SCHEMA = _GENERATED / "jsonschema" / "sig.schema.json"

_VOCAB_TOMLS = sorted(_DATA.glob("*_vocab.toml"))
_CONNECTOR_SOURCES = sorted(
    p for p in _CONNECTORS.glob("*.py") if p.name not in {"__init__.py", "cli.py"}
)

_PREDICATE_LITERAL = re.compile(r"""["']predicate_id["']\s*[:=]\s*["']([a-zA-Z0-9_.]+)["']""")
_PREDICATE_CONST = re.compile(
    r"""^[A-Z0-9_]*PREDICATE[A-Z0-9_]*\s*=\s*["']([a-zA-Z0-9_.]+)["']""", re.M
)
_GENRE_LITERAL = re.compile(r"""["']evidence_genre["']\s*[:=]\s*["']([a-z_]+)["']""")


def _registry() -> dict:
    return json.loads(_REGISTRY.read_text())


def registered_predicates() -> set[str]:
    return {p["predicate_id"] for p in _registry()["predicates"]}


def registered_genres() -> set[str]:
    return set(_registry()["artifact_genres"])


def toml_predicate_ids() -> set[str]:
    """Every id named by a connector vocabulary's predicate allowlist."""
    ids: set[str] = set()
    for path in _VOCAB_TOMLS:
        doc = tomllib.loads(path.read_text())
        stack: list[object] = [doc]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for key, value in node.items():
                    if key.endswith("predicate_allowlist") and isinstance(value, list):
                        ids.update(str(v) for v in value)
                    else:
                        stack.append(value)
            elif isinstance(node, list):
                stack.extend(node)
    return ids


def source_predicate_ids() -> set[str]:
    """Every ``predicate_id`` a connector module stamps in code."""
    ids: set[str] = set()
    for path in _CONNECTOR_SOURCES:
        src = path.read_text()
        ids.update(_PREDICATE_LITERAL.findall(src))
        ids.update(_PREDICATE_CONST.findall(src))
    ids.discard("")  # a param-name hit like {"predicate_id": pred} is not an id
    return ids


def emitted_genres() -> set[str]:
    """Every genre a connector can stamp: ``artifact_genre`` maps + literals."""
    genres: set[str] = set()
    for path in _DATA.glob("*.toml"):
        doc = tomllib.loads(path.read_text())
        stack: list[object] = [doc]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"artifact_genre", "evidence_genre"} and isinstance(value, str):
                        genres.add(value)
                    else:
                        stack.append(value)
            elif isinstance(node, list):
                stack.extend(node)
    for path in _CONNECTOR_SOURCES:
        genres.update(_GENRE_LITERAL.findall(path.read_text()))
    return genres


def mobility_map_targets() -> dict[str, str]:
    """The OSM ``[mobility]`` map's upstream value → ontology member targets."""
    doc = tomllib.loads((_DATA / "osm_tag_vocab.toml").read_text())
    return {str(k): str(v) for k, v in doc["mobility"].items()}


def ontology_mobility_members() -> set[str]:
    schema = json.loads(_SCHEMA.read_text())
    return set(schema["$defs"]["Mobility"]["enum"])


def test_every_allowlisted_predicate_is_registered() -> None:
    reg = registered_predicates()
    missing = sorted(toml_predicate_ids() - reg)
    assert not missing, f"connector predicate allowlists name unregistered ids: {missing}"


def test_every_source_stamped_predicate_is_registered() -> None:
    reg = registered_predicates()
    ids = source_predicate_ids()
    assert ids, "scan found no stamped predicate ids — the surface shrank silently"
    missing = sorted(ids - reg)
    assert not missing, f"connector modules stamp unregistered predicates: {missing}"


def test_every_emitted_genre_is_registered() -> None:
    reg = registered_genres()
    genres = emitted_genres()
    assert genres, "scan found no emitted genres — the surface shrank silently"
    missing = sorted(genres - reg)
    assert not missing, f"connectors stamp unregistered artifact genres: {missing}"


def test_atlas_method_map_covers_every_method_with_a_registered_genre() -> None:
    """Every Atlas evidence-genre method carries an artifact_genre mapping —
    an unmapped method is a vocabulary defect (granularity loss), never a guess."""
    doc = tomllib.loads((_DATA / "atlas_vocab.toml").read_text())
    reg = registered_genres()
    unmapped = [m for m, spec in doc["evidence_genres"].items() if "artifact_genre" not in spec]
    assert not unmapped, f"Atlas methods with no artifact_genre mapping: {unmapped}"
    unregistered = sorted(
        {spec["artifact_genre"] for spec in doc["evidence_genres"].values()} - reg
    )
    assert not unregistered, f"Atlas artifact_genre targets not in registry: {unregistered}"


def test_mobility_map_targets_are_ontology_enum_members() -> None:
    members = ontology_mobility_members()
    targets = mobility_map_targets()
    bad = {k: v for k, v in targets.items() if v not in members}
    assert not bad, f"mobility map targets outside the Mobility enum: {bad}"
    # SIG-GEO-005: the historical defect — `mobile` is not an enum member and
    # must never be emitted again.
    assert "mobile" not in targets.values()


def test_planted_violation_fails_closed() -> None:
    """A predicate the registry does not know must fail the same membership
    check the real surface passes — the gate is not a rubber stamp."""
    planted = "sig.test.never_registered_p35_14a"
    assert planted not in registered_predicates()
    with _assert_missing(planted):
        _require_registered({planted}, registered_predicates())


def test_planted_genre_violation_fails_closed() -> None:
    planted = "sig_test_genre_never_registered"
    assert planted not in registered_genres()
    with _assert_missing(planted):
        _require_registered({planted}, registered_genres())


def _require_registered(ids: set[str], registry: set[str]) -> None:
    missing = sorted(ids - registry)
    assert not missing, f"unregistered: {missing}"


def _assert_missing(member: str):
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        try:
            yield
        except AssertionError as exc:
            assert member in str(exc)
            return
        raise AssertionError(f"planted violation {member!r} was not rejected")

    return _ctx()
