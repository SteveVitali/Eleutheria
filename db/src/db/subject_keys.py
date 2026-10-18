# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The declared subject-key pin registry (P35.24 / ADR-212; R11-L3-CP2, F-506/F-518).

``data/subject_key_pins.toml`` is the single committed declaration of which
fields compose a connector subject key, in which order, with which scope
(tenant/state), and which legacy shapes still parse. Emitters mint through
:func:`mint_subject_key`, the claim sink validates incoming subject values
against :func:`parse_subject_key`, and the append-only re-key run re-derives
collisions through the pin's ``distinguish`` selectors and mints constituent
subjects through :func:`split_subject_key` — one derivation on both sides,
never two (CONF-03b / GQ-04).

Grammar (§11 subject values):

- a value is ``<family><segment>(:<segment>)*`` — ``:`` inside a segment is
  forbidden, so parsing stays positional and unambiguous;
- a *scope field* declared ``kind = "scheme_prefixed"`` renders as TWO
  segments — the literal scheme token then the value — so the current shape
  can never be confused with a legacy value (``atlas:us.state_abbr:CA:…``
  vs legacy ``atlas:<agency>:…``);
- ``absent = "unscoped"`` renders the literal ``unscoped`` token when the
  record carries no scope value; ``absent = "omit"`` drops the scope
  segments entirely and falls back to the declared legacy shape
  (``contract:<source>:<id>`` stays valid for single-tenant sources);
- a ``split.shape = "suffix_digest"`` constituent appends ``:s<sha256-12>``
  of the discriminator — deterministic, content-addressed, parse-reversible.
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any, Literal

_PINS_RESOURCE = "subject_key_pins.toml"

#: The ``sig.connector.subject`` identity scheme all these values live under.
SUBJECT_SCHEME = "sig.connector.subject"

#: A constituent-key digest suffix: ``s`` + 12 hex chars of sha256.
_CONSTITUENT_RE = __import__("re").compile(r"^s[0-9a-f]{12}$")


class SubjectKeyError(ValueError):
    """A pinned subject value violates the declared grammar, or a mint
    request misses/violates a declared field."""


class SubjectKeyCollision(SubjectKeyError):
    """Two upstream records in one capture minted the same subject key
    (GQ-04 — the run for that target fails closed)."""


@dataclass(frozen=True)
class SubjectKeyScope:
    field: str
    kind: Literal["scheme_prefixed"]
    scheme: str
    absent: Literal["unscoped", "omit"]


@dataclass(frozen=True)
class SubjectKeyPin:
    """One declared subject-key grammar entry."""

    pin_id: str
    family: str
    key_version: int
    fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    scope: SubjectKeyScope | None
    #: arity -> legacy field order (parse only; never minted)
    legacy_fields: Mapping[int, tuple[str, ...]]
    uniqueness: str | None
    distinguish: tuple[str, ...]
    split_discriminator: str | None
    split_shape: Literal["suffix_digest", "current_fields"] | None
    note: str


@dataclass(frozen=True)
class ParsedSubjectKey:
    """A subject value resolved against its pin."""

    pin: SubjectKeyPin
    key_version: int
    #: declared field -> segment value (legacy parse uses legacy_fields names)
    fields: Mapping[str, str]
    constituent: bool
    discriminator: str | None


@cache
def _doc() -> dict[str, Any]:
    resource = files("db").joinpath("data").joinpath(_PINS_RESOURCE)
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def registry_version() -> str:
    """The version stamp recorded on re-key decisions and reports."""
    return str(_doc()["version"])


@cache
def pins() -> tuple[SubjectKeyPin, ...]:
    out: list[SubjectKeyPin] = []
    for row in _doc().get("pin", []):
        scope = row.get("scope")
        legacy = {
            int(k): tuple(str(v) for v in vals)
            for k, vals in (row.get("legacy_fields") or {}).items()
        }
        split = row.get("split")
        out.append(
            SubjectKeyPin(
                pin_id=str(row["id"]),
                family=str(row["family"]),
                key_version=int(row["key_version"]),
                fields=tuple(str(f) for f in row["fields"]),
                optional_fields=tuple(str(f) for f in row.get("optional_fields", [])),
                scope=(
                    SubjectKeyScope(
                        field=str(scope["field"]),
                        kind="scheme_prefixed",
                        scheme=str(scope["scheme"]),
                        absent=str(scope.get("absent", "unscoped")),  # type: ignore[arg-type]
                    )
                    if scope
                    else None
                ),
                legacy_fields=legacy,
                uniqueness=(str(row["uniqueness"]) if row.get("uniqueness") else None),
                distinguish=tuple(str(s) for s in row.get("distinguish", [])),
                split_discriminator=(
                    str(split["discriminator"]) if split and split.get("discriminator") else None
                ),
                split_shape=(str(split["shape"]) if split and split.get("shape") else None),  # type: ignore[arg-type]
                note=str(row.get("note", "")),
            )
        )
    return tuple(out)


@cache
def _by_family() -> Mapping[str, SubjectKeyPin]:
    return {pin.family: pin for pin in pins()}


def pin_for_subject(value: str) -> SubjectKeyPin | None:
    """The pin whose family prefixes the value (longest match), else None —
    unpinned families pass through (the registry is deliberately partial)."""
    best: SubjectKeyPin | None = None
    for family, pin in _by_family().items():
        if value.startswith(family) and (best is None or len(family) > len(best.family)):
            best = pin
    return best


def _check_segment(field: str, value: Any) -> str:
    if value is None:
        raise SubjectKeyError(f"subject key field {field!r} is required")
    text = str(value).strip()
    if not text:
        raise SubjectKeyError(f"subject key field {field!r} must not be empty")
    if ":" in text:
        raise SubjectKeyError(
            f"subject key field {field!r} must not contain ':' — the value "
            "would break positional parsing"
        )
    return text


def _scope_segments(pin: SubjectKeyPin, field_values: Mapping[str, str]) -> list[str]:
    """The two segments a scheme_prefixed scope renders (or [] when omitted)."""
    assert pin.scope is not None
    raw = field_values.get(pin.scope.field)
    if raw is None or not str(raw).strip():
        if pin.scope.absent == "omit":
            return []
        return [pin.scope.scheme, "unscoped"]
    return [pin.scope.scheme, _check_segment(pin.scope.field, raw)]


def mint_subject_key(pin_id: str, **fields: Any) -> str:
    """Mint a subject value under the pin's CURRENT shape.

    Every declared non-scope field is required; optional fields append when
    given. A scoped pin whose ``absent = "omit"`` rule fires mints the
    declared legacy shape instead (``contract`` without tenant stays
    ``contract:<source>:<id>``).
    """
    pin = next((p for p in pins() if p.pin_id == pin_id), None)
    if pin is None:
        raise SubjectKeyError(f"unknown subject key pin {pin_id!r}")

    # A scope with absent=omit and no value falls back to the legacy shape.
    if pin.scope is not None and pin.scope.absent == "omit":
        raw = fields.get(pin.scope.field)
        if raw is None or not str(raw).strip():
            legacy = pin.legacy_fields.get(len(pin.fields) - 1)
            if legacy is None:
                raise SubjectKeyError(
                    f"pin {pin_id!r} has no no-scope shape; provide {pin.scope.field!r}"
                )
            legacy_segments = [_check_segment(f, fields.get(f)) for f in legacy]
            return pin.family + ":".join(legacy_segments)

    segments: list[str] = []
    for name in pin.fields:
        if pin.scope is not None and name == pin.scope.field:
            segments.extend(_scope_segments(pin, fields))
        else:
            segments.append(_check_segment(name, fields.get(name)))
    for name in pin.optional_fields:
        raw = fields.get(name)
        if raw is not None and str(raw).strip():
            segments.append(_check_segment(name, raw))
    return pin.family + ":".join(segments)


def _parse_current(pin: SubjectKeyPin, segments: list[str]) -> ParsedSubjectKey | None:
    """Parse a current-shape value; None when it does not match."""
    pos = 0
    fields: dict[str, str] = {}
    for name in pin.fields:
        if pin.scope is not None and name == pin.scope.field:
            if pos + 1 >= len(segments) or segments[pos] != pin.scope.scheme:
                return None
            fields[name] = segments[pos + 1]
            pos += 2
        else:
            if pos >= len(segments):
                return None
            fields[name] = segments[pos]
            pos += 1
    for name in pin.optional_fields:
        if pos < len(segments):
            fields[name] = segments[pos]
            pos += 1
    if pos != len(segments):
        return None
    return ParsedSubjectKey(
        pin=pin, key_version=pin.key_version, fields=fields, constituent=False, discriminator=None
    )


def parse_subject_key(value: str) -> ParsedSubjectKey | None:
    """Resolve a subject value against the pin registry.

    Returns the parsed key (current, legacy or constituent shape), or None
    when the family is unpinned or the value matches no declared shape —
    callers decide whether that quarantines (sink) or skips (re-key scan).
    """
    pin = pin_for_subject(value)
    if pin is None:
        return None
    segments = value[len(pin.family) :].split(":")
    if not segments or any(not s for s in segments):
        return None

    # Constituent form: base segments + :s<digest12>.
    if (
        pin.split_shape == "suffix_digest"
        and len(segments) >= 2
        and _CONSTITUENT_RE.match(segments[-1])
    ):
        base = parse_subject_key(pin.family + ":".join(segments[:-1]))
        if base is not None and not base.constituent:
            return ParsedSubjectKey(
                pin=pin,
                key_version=base.key_version,
                fields=base.fields,
                constituent=True,
                discriminator=segments[-1][1:],
            )
        return None

    current = _parse_current(pin, segments)
    if current is not None:
        return current
    # A value starting with the scope literal is a truncated/malformed current
    # key, never a legacy agency named after the scheme token.
    if pin.scope is not None and segments[0] == pin.scope.scheme:
        return None
    legacy = pin.legacy_fields.get(len(segments))
    if legacy is not None:
        return ParsedSubjectKey(
            pin=pin,
            key_version=1,
            fields={name: segments[i] for i, name in enumerate(legacy)},
            constituent=False,
            discriminator=None,
        )
    return None


def split_subject_key(parsed: ParsedSubjectKey, discriminator: str) -> str:
    """The constituent subject value a collided claim-bundle moves to.

    ``suffix_digest``: ``<base>:s<sha256-12>`` of the canonicalised
    discriminator (the coordinate pair for cameras). ``current_fields``:
    re-mint the current shape with the scope field replaced by the
    discriminator (a stored ``atlas:<agency>`` splits per evidenced state
    into ``atlas:us.state_abbr:<state>:<agency>``).
    """
    pin = parsed.pin
    if pin.split_shape == "suffix_digest":
        base = pin.family + ":".join(
            [parsed.fields[name] for name in pin.fields if name in parsed.fields]
            + [parsed.fields[name] for name in pin.optional_fields if name in parsed.fields]
        )
        digest = hashlib.sha256(discriminator.encode("utf-8")).hexdigest()[:12]
        return f"{base}:s{digest}"
    if pin.split_shape == "current_fields":
        if pin.scope is None:
            raise SubjectKeyError(f"pin {pin.pin_id!r} has no scope field to split on")
        fields = dict(parsed.fields)
        fields[pin.scope.field] = discriminator
        return mint_subject_key(pin.pin_id, **fields)
    raise SubjectKeyError(f"pin {pin.pin_id!r} declares no split shape")


def assert_unique_within(keys: Iterable[str], *, context: str = "capture") -> None:
    """GQ-04: two upstream records minting one subject key inside the same
    capture fails closed — the collided key is named in the error."""
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            raise SubjectKeyCollision(
                f"subject key {key!r} minted twice within the same {context} — "
                "the declared key fields are not unique upstream"
            )
        seen.add(key)


def validate_subject_value(value: str) -> str | None:
    """Sink-side check: an error string when a value under a PINNED family
    matches no declared shape; None when valid (or the family is unpinned)."""
    pin = pin_for_subject(value)
    if pin is None:
        return None
    if parse_subject_key(value) is None:
        return (
            f"subject value {value!r} violates the declared grammar of pin "
            f"{pin.pin_id!r} ({registry_version()})"
        )
    return None
