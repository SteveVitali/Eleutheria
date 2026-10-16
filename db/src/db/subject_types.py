# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The versioned subject-scheme → entity-type map (P35.14b; L1 NEW-5 / FM-17).

Every connector claim subject is minted under the ``sig.connector.subject``
identity scheme (ADR-110). ``data/subject_entity_types.toml`` declares which
ontology entity type a subject value mints, keyed on the value's scheme prefix.
The claim sink resolves a subject by **longest-prefix match** and the lookup
**fails closed**: a subject matching no entry raises
:class:`UnmappedSubjectScheme` and the record quarantines
(``unknown_subject_scheme``) — never a silent default to ``deployment``.

The same map types the append-only typed-identity write (the L1 correction for
entities minted under the old all-``deployment`` default) and the ``sig:`` /
portal object refs a connector declares, so a subject and an object ref naming
the same identifier always mint one type.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any

_MAP_RESOURCE = "subject_entity_types.toml"

#: The ``vocab_entity_type`` membership (db/deploy/seed_vocab.sql) the map may
#: declare — kept byte-identical to the seed so the artifact fails closed on a
#: type the database would refuse at mint time anyway. ``tests/db`` pins the
#: set equal to the seeded rows so a vocab change cannot drift silently.
KNOWN_ENTITY_TYPES = frozenset(
    {
        "jurisdiction",
        "organization",
        "person",
        "product",
        "technology",
        "capability",
        "deployment",
        "physical_asset",
        "candidate_asset",
        "data_system",
        "contract",
        "funding_instrument",
        "policy",
        "legal_instrument",
        "configuration_state",
        "usage_aggregate",
        "accountability_event",
        "legal_proceeding",
        "records_request",
    }
)


class UnmappedSubjectScheme(ValueError):
    """A ``sig.connector.subject`` value no map prefix covers (fail closed)."""


@cache
def _doc() -> dict[str, Any]:
    data = files(__package__).joinpath("data", _MAP_RESOURCE).read_bytes()
    return tomllib.loads(data.decode("utf-8"))


@cache
def _table() -> Mapping[str, str]:
    prefixes = _doc().get("prefixes") or {}
    out: dict[str, str] = {}
    for prefix, spec in prefixes.items():
        if not isinstance(spec, Mapping):
            raise ValueError(
                f"{_MAP_RESOURCE}: prefix {prefix!r} must be a table with an entity_type member"
            )
        entity_type = str(spec.get("entity_type") or "").strip()
        if not prefix or not entity_type:
            raise ValueError(
                f"{_MAP_RESOURCE}: every prefix needs a non-empty entity_type "
                f"(offending entry {prefix!r})"
            )
        if entity_type not in KNOWN_ENTITY_TYPES:
            raise ValueError(
                f"{_MAP_RESOURCE}: prefix {prefix!r} declares entity_type "
                f"{entity_type!r}, which is not a vocab_entity_type member "
                "(db/deploy/seed_vocab.sql)"
            )
        out[str(prefix)] = entity_type
    if not out:
        raise ValueError(f"{_MAP_RESOURCE}: the map is empty")
    return MappingProxyType(out)


def map_version() -> str:
    """The declared map version, stamped on typed-identity decision rows."""
    version = str(_doc().get("version") or "").strip()
    if not version:
        raise ValueError(f"{_MAP_RESOURCE}: missing version")
    return version


@cache
def mapped_prefixes() -> tuple[str, ...]:
    """Every declared subject-value prefix, longest first."""
    return tuple(sorted(_table(), key=len, reverse=True))


def entity_type_for_prefix(prefix: str) -> str | None:
    """The declared type for one map prefix, or ``None`` when absent."""
    return _table().get(prefix)


def entity_type_for_subject(value: str) -> str:
    """The entity type one ``sig.connector.subject`` value mints.

    Longest-prefix match, so ``data_driven:agency:`` beats a future
    ``data_driven:`` entry. Raises :class:`UnmappedSubjectScheme` for a value
    the map does not cover — the caller quarantines, never defaults.
    """
    for prefix in mapped_prefixes():
        if value.startswith(prefix):
            return _table()[prefix]
    raise UnmappedSubjectScheme(
        f"subject {value!r} matches no subject_entity_types.toml prefix; "
        "a new subject family mints only after the map declares its type"
    )


__all__ = [
    "KNOWN_ENTITY_TYPES",
    "UnmappedSubjectScheme",
    "entity_type_for_prefix",
    "entity_type_for_subject",
    "map_version",
    "mapped_prefixes",
]
