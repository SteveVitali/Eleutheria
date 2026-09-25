# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Declared §32.1 peer classes — the negative-space policy is data, not code.

A **peer class** is ``(entity_type, connector class)`` (ADR-115): a claim
subject belongs to a class when at least one of its tier-0, currently-valid
claims was written by an ``ingest_run`` whose ``connector_name`` the class
declares. Each class declares its **tracked predicates** in
``data/peer_classes.toml``; a predicate absent from the declaration is never
negative space for that class, and a subject whose claims come only from
undeclared connectors has no declared coverage surface (no rows, never a
guess). This is what makes the §32.1 negative space *proportionate*: a traffic
camera in the ``dot_511`` class is "not researched" for ``camera_operator``
but never for ``bill_title`` — that predicate is not in the class's declared
surface.

The declaration is a TOML artifact reviewed like the connector vocabularies
(SIG-ENG-001): loaded through this module (mirroring ``tasks._data.load_table``),
validated at load, and versioned on change (§20).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

__all__ = ["PeerClass", "load_peer_classes"]


@dataclass(frozen=True)
class PeerClass:
    """One declared §32.1 peer class: ``(entity_type, connectors) → tracked``.

    ``connectors`` are ``ingest_run.connector_name`` values — the acquisition
    channels whose lineage makes a subject a member. ``tracked`` is the
    declared predicate set: the attributes this class is expected to have
    researched; a member lacking one is ``not_researched`` for it.
    """

    entity_type: str
    connectors: tuple[str, ...]
    tracked: tuple[str, ...]


def _parse(raw: dict) -> tuple[PeerClass, ...]:
    """Validate the TOML payload into immutable classes (fail loud on a bad file)."""
    if not raw.get("version"):
        raise ValueError("peer_classes.toml must declare a 'version'")
    classes: list[PeerClass] = []
    claimed_connectors: set[tuple[str, str]] = set()
    for i, entry in enumerate(raw.get("class") or ()):
        entity_type = str(entry.get("entity_type") or "")
        connectors = tuple(str(c) for c in entry.get("connectors") or ())
        tracked = tuple(str(p) for p in entry.get("tracked") or ())
        if not entity_type:
            raise ValueError(f"peer class #{i} has no entity_type")
        if not connectors:
            raise ValueError(f"peer class #{i} ({entity_type}) declares no connectors")
        if not tracked:
            raise ValueError(f"peer class #{i} ({entity_type}) declares no tracked predicates")
        if len(set(tracked)) != len(tracked):
            raise ValueError(f"peer class #{i} ({entity_type}) lists a predicate twice")
        for connector in connectors:
            key = (entity_type, connector)
            if key in claimed_connectors:
                raise ValueError(
                    f"connector {connector!r} is declared by two {entity_type!r} "
                    "peer classes — membership must be unambiguous"
                )
            claimed_connectors.add(key)
        classes.append(PeerClass(entity_type=entity_type, connectors=connectors, tracked=tracked))
    return tuple(classes)


@cache
def load_peer_classes() -> tuple[PeerClass, ...]:
    """Return the declared peer classes shipped in ``data/peer_classes.toml``."""
    resource = files("inference").joinpath("data", "peer_classes.toml")
    with resource.open("rb") as fh:
        return _parse(tomllib.load(fh))
