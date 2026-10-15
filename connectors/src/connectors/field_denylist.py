# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Part VIII layer-field denylist (F-330, owned by P35.6 / R11-ACQ-01).

F-330 showed that the keyword/owner discovery SIG uses for camera registries
surfaces public ArcGIS/Socrata layers carrying **per-person data** — Flock
"search results" (PLATE + capture time + location), a Mark43 "CGPD LPR Hits"
layer (PLATE, HOTLIST_REASON, TIMESTAMP, ADDRESS), a Flower Mound registrant
layer (FIRST_NAME, LAST_NAME, ADDRESS1, PHONE, EMAIL), a Socrata ``red_vrm``
field, and the Horizon City Axon layer's ``owner_firstname`` /
``owner_lastname`` / ``badge_id`` that GL-GATE-07 excluded by hand. The gate
until now was reviewer disposition; this module makes it a **schema denylist**
read from the committed ``data/field_denylist.toml`` table (SIG-ENG-001 — data,
not code).

The denylist is a **registration refusal**, never a capture-time filter: an
ArcGIS/Socrata ``[[targets]]`` row whose declared ``observed_fields`` (the
layer's published schema) or ``out_fields`` (the reviewed capture allowlist)
contains a denied field is refused by ``sig-connectors validate``, by the
ACQ-01 registry/target generator, and (belt-and-braces) by
:func:`connectors.dot_511.registry_targets`. A layer that publishes plate or
registrant fields is not a camera registry and never registers — Part VIII
§0.7 is absolute (SIG-PUB-002/003/004, SIG-STORE-025).

Matching is token-based so case and separators are irrelevant but unrelated
names never collide: ``FIRST_NAME``, ``firstName``, ``owner_first_name`` and
``ownerFirstName`` all reduce to the tokens ``[first, name]`` /
``[owner, first, name]`` and match the ``["first","name"]`` sequence, while
``RoadwayName`` (``[roadway, name]``), ``template`` (``[template]``) and a
camera layer's organisation ``Owner`` field stay permitted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from functools import cache
from typing import Any

from ._data import load_table

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_ALPHA_DIGIT_BOUNDARY = re.compile(r"(?<=[a-zA-Z])(?=[0-9])|(?<=[0-9])(?=[a-zA-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _tokens(field_name: str) -> tuple[str, ...]:
    """Normalise a published field name to lowercase snake tokens.

    ``CAMERA_ID`` → ``("camera","id")``; ``ownerFirstName`` →
    ``("owner","first","name")``; ``ADDRESS1`` → ``("address","1")``. camelCase
    boundaries, letter↔digit boundaries and non-alphanumeric runs all split
    tokens, so case and separators can never hide a denied name.
    """
    split_camel = _CAMEL_BOUNDARY.sub("_", str(field_name))
    split_digits = _ALPHA_DIGIT_BOUNDARY.sub("_", split_camel)
    return tuple(t for t in _NON_ALNUM.split(split_digits.lower()) if t)


@cache
def _deny_tokens() -> frozenset[str]:
    return frozenset(str(t) for t in load_table("field_denylist").get("deny_tokens", ()))


@cache
def _deny_sequences() -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(str(t) for t in seq) for seq in load_table("field_denylist").get("deny_sequences", ())
    )


def denied_match(field_name: str) -> str | None:
    """The denylist term ``field_name`` matches, or ``None``.

    Returns the matched token (``"plate"``) or joined sequence
    (``"first name"``) for error messages.
    """
    toks = _tokens(field_name)
    if not toks:
        return None
    for tok in toks:
        if tok in _deny_tokens():
            return tok
    for seq in _deny_sequences():
        n = len(seq)
        if n and any(toks[i : i + n] == seq for i in range(len(toks) - n + 1)):
            return " ".join(seq)
    return None


def is_denied(field_name: str) -> bool:
    """Whether a published layer field name is Part VIII denied (F-330)."""
    return denied_match(field_name) is not None


def field_violations(fields: Iterable[str]) -> list[str]:
    """Sorted ``"<field>" (denied "<term>")`` entries for the denied fields."""
    out: list[str] = []
    for field in fields:
        term = denied_match(str(field))
        if term is not None:
            out.append(f"{field!r} (denied {term!r})")
    return sorted(out)


#: The platforms the F-330 denylist gates — ArcGIS REST feature-layer queries
#: and Socrata ``/resource`` rows, the two transports F-330's archetypes ride.
DENYLIST_KINDS: frozenset[str] = frozenset({"arcgis_query", "socrata_rows"})
DENYLIST_PLATFORMS: frozenset[str] = frozenset({"arcgis", "socrata"})


def _row_fields(row: Mapping[str, Any]) -> list[str]:
    """Every field name a target row declares (published schema + allowlist)."""
    fields: list[str] = []
    for key in ("observed_fields", "out_fields"):
        value = row.get(key)
        if isinstance(value, str):
            fields.extend(f.strip() for f in value.split(","))
        elif isinstance(value, (list, tuple)):
            fields.extend(str(f) for f in value)
    return [f for f in fields if f]


def target_field_violations(row: Mapping[str, Any]) -> list[str]:
    """Denylist hits on one registry ``[[targets]]`` row (F-330).

    Applies to ArcGIS/Socrata platform targets (``kind`` in
    :data:`DENYLIST_KINDS` or ``platform`` in :data:`DENYLIST_PLATFORMS`); other
    kinds return ``[]`` — the denylist gates the transports F-330 named, not
    unrelated document/index targets.
    """
    kind = str(row.get("kind") or "")
    platform = str(row.get("platform") or "")
    if kind not in DENYLIST_KINDS and platform not in DENYLIST_PLATFORMS:
        return []
    return field_violations(_row_fields(row))


class FieldDenylistViolation(ValueError):
    """A registry target carries a Part VIII denied layer field (F-330)."""


def assert_target_fields_clean(row: Mapping[str, Any]) -> None:
    """Refuse a target row whose declared fields hit the denylist."""
    violations = target_field_violations(row)
    if violations:
        raise FieldDenylistViolation(
            f"registry target {row.get('id')!r} declares denied Part VIII field(s) "
            f"{', '.join(violations)} — a layer publishing plate/registrant fields "
            "is not a camera registry and is refused registration (F-330; "
            "SIG-PUB-002/003/004, SIG-STORE-025)"
        )


__all__ = [
    "DENYLIST_KINDS",
    "DENYLIST_PLATFORMS",
    "FieldDenylistViolation",
    "assert_target_fields_clean",
    "denied_match",
    "field_violations",
    "is_denied",
    "target_field_violations",
]
