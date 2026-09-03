# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The per-class canonical-identifier registry and the crosswalk exports
(SIG-IDENT-001/007/033/034).

Two things live here:

* **The canonical-scheme registry (SIG-IDENT-001).** :func:`canonical_scheme_for`
  answers "what is the designated canonical identifier scheme for this
  organisation class?" from the versioned ``data/canonical_schemes.toml`` table —
  ORI9 for US law enforcement, Census GEOID for municipalities, LEI for corporate
  bodies, and so on, with a SIG surrogate where no external scheme exists. Wikidata
  QIDs are recorded where present but are **never canonical for US law enforcement**
  (SIG-IDENT-007); :func:`wikidata_reliable_for` encodes that asymmetry.

* **The crosswalk exports (SIG-IDENT-033/034).** :func:`build_sig_external_crosswalk`
  emits the SIG↔external-identifier mapping and :func:`build_ori_geoid_crosswalk`
  the public ``ORI9 → Census GEOID`` mapping. Both are published only through the
  licence gate (:func:`export_crosswalk`), which fails closed on any constituent
  source whose rights are undetermined or non-redistributable (SIG-LIC-004).
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

from policy.licensing import assert_export_permitted
from policy.rights import RightsRecord

from .geoid import validate_geoid
from .identity import Identifier
from .ori import validate_ori

__all__ = [
    "SchemeResolution",
    "canonical_scheme_for",
    "wikidata_reliable_for",
    "CrosswalkRow",
    "build_sig_external_crosswalk",
    "build_ori_geoid_crosswalk",
    "export_crosswalk",
]


@cache
def _schemes() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "canonical_schemes.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


@dataclass(frozen=True)
class SchemeResolution:
    """The canonical identifier scheme designated for an organisation class."""

    organization_class: str
    canonical_scheme: str | None
    secondary_schemes: tuple[str, ...] = ()
    label: str = ""
    is_surrogate: bool = False


def _match_rule(org_class: str) -> dict[str, Any] | None:
    """Most-specific-first match: exact class beats prefix; longer prefix wins."""
    rules = _schemes()["rule"]
    for rule in rules:
        if org_class in rule.get("classes", []):
            return rule
    best: dict[str, Any] | None = None
    best_len = -1
    for rule in rules:
        for prefix in rule.get("prefixes", []):
            if org_class.startswith(prefix) and len(prefix) > best_len:
                best, best_len = rule, len(prefix)
    return best


def canonical_scheme_for(organization_class: str) -> SchemeResolution:
    """The canonical identifier scheme for ``organization_class`` (SIG-IDENT-001).

    Returns a :class:`SchemeResolution`; a class with no designated external scheme
    resolves to ``is_surrogate=True`` with ``canonical_scheme=None`` (§14.4). An
    unknown class also falls through to a surrogate rather than raising — an
    unrecognised body still needs a stable minted identity.
    """
    rule = _match_rule(organization_class)
    if rule is None or rule.get("surrogate"):
        return SchemeResolution(
            organization_class=organization_class,
            canonical_scheme=None,
            label=(rule or {}).get("label", "SIG surrogate (no external canonical scheme)"),
            is_surrogate=True,
        )
    return SchemeResolution(
        organization_class=organization_class,
        canonical_scheme=rule["canonical"],
        secondary_schemes=tuple(rule.get("secondary", [])),
        label=rule.get("label", ""),
        is_surrogate=False,
    )


def wikidata_reliable_for(organization_class: str) -> bool:
    """Whether Wikidata QIDs may be depended on for this class (SIG-IDENT-007).

    ``False`` for US law-enforcement classes — QIDs are recorded where present but
    coverage is weak, so they are never a coverage dependency there. ``True`` for
    vendors / data brokers, where ``manufacturer:wikidata`` is strong.
    """
    if organization_class.startswith("us.le."):
        return False
    return organization_class in {"vendor", "data_broker"}


@dataclass(frozen=True)
class CrosswalkRow:
    """One published crosswalk row: a SIG entity mapped to an external identifier."""

    sig_id: str
    scheme: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"sig_id": self.sig_id, "scheme": self.scheme, "value": self.value}


def build_sig_external_crosswalk(
    entities: Iterable[tuple[str, Iterable[Identifier]]],
) -> list[CrosswalkRow]:
    """The SIG↔external identifier crosswalk (SIG-IDENT-033).

    ``entities`` is an iterable of ``(sig_id, identifiers)``. Emits one deterministic
    row per (sig_id, scheme, value), sorted, so the artifact is byte-stable across
    runs. This is the single highest-leverage artifact SIG publishes — it lets other
    projects reuse SIG's entity resolution without rebuilding it.
    """
    rows: list[CrosswalkRow] = []
    for sig_id, idents in entities:
        for ident in idents:
            rows.append(CrosswalkRow(sig_id=sig_id, scheme=ident.scheme, value=ident.value))
    return sorted(rows, key=lambda r: (r.sig_id, r.scheme, r.value))


def build_ori_geoid_crosswalk(
    pairs: Iterable[tuple[str, str]],
    *,
    geoid_level: str = "place",
) -> list[dict[str, str]]:
    """The public ``ORI9 → Census GEOID`` crosswalk (SIG-IDENT-034).

    ``pairs`` is an iterable of ``(ori9, geoid)``. Each ORI is validated by pattern
    (SIG-IDENT-002) and each GEOID against ``geoid_level`` (SIG-IDENT-005) before it
    is emitted, so a malformed row fails the build rather than shipping. Output is
    sorted for byte-stability.
    """
    rows: list[dict[str, str]] = []
    for ori, geoid in pairs:
        validate_ori(ori)
        validate_geoid(geoid, geoid_level)
        rows.append({"ori9": ori, "geoid": geoid, "geoid_level": geoid_level})
    return sorted(rows, key=lambda r: (r["ori9"], r["geoid"]))


def export_crosswalk(rows: Sequence[Any], *, rights: Iterable[RightsRecord]) -> list[Any]:
    """Return ``rows`` only if the licence gate permits publishing them (SIG-IDENT-033/034).

    The crosswalk is published under the most permissive licence its constituent
    rights permit; :func:`policy.licensing.assert_export_permitted` fails the export
    **closed** on any source whose rights are undetermined or not redistributable
    (SIG-LIC-004). A crosswalk that would leak a non-redistributable source never
    leaves the build.
    """
    assert_export_permitted(rights)
    return list(rows)
