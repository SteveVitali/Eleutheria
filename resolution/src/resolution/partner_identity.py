# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Partner-organisation identity for entity-ref claims (P31.5 / ADR-112).

A connector that names a partner — a contract's ``buyer`` or ``seller``, a funding
instrument's ``funder`` or ``recipient``, an accountability event's organisations, a
camera's operator — writes the name as a text claim. This module decides, purely and
deterministically, whether that name can also stand as an ``organization`` entity,
and under which identifier:

* **One identifier scheme per partner** (:func:`partner_identity`). An external
  crosswalk id when the record carries one (LEI, UEI, DUNS, CAGE, a federal agency
  code — schemes in :data:`db.identity_guard.PARTNER_ORG_SCHEMES`), otherwise the
  normalized name under ``sig.org.name`` (:func:`resolution.normalize.normalize_org_name`,
  SIG-IDENT-022). Two records that normalize to the same name name the same entity;
  merging anything beyond that is entity resolution (P28.1), not this module.
* **The ambiguity rule.** A value that is not a name, names several parties, is only
  generic words, or is one bare word stays a text claim.
* **The never-a-person rule (Part VIII).** A natural-person-shaped or
  sole-proprietor-shaped name never becomes an entity. An organisation needs a
  positive organisation marker. When in doubt the partner stays text.

The rules are versioned data (``data/partner_identity.toml``). :func:`partner_ref_rows`
is the connector ``link()`` helper: after each eligible text claim it appends a
**separate** entity-ref claim record (the text claim plus an ``object_ref``), so the
text claim is byte-for-byte unchanged and the entity-ref claim has its own content
digest. The claim sink resolves ``object_ref`` through the identity guard
(:func:`db.claim_sink.record_object_ref`).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

from db.identity_guard import PARTNER_NAME_SCHEME, PARTNER_ORG_SCHEMES

from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name

__all__ = [
    "CROSSWALK_SCHEMES",
    "PARTNER_ENTITY_TYPE",
    "PARTNER_NAME_SCHEME",
    "PARTNER_PREDICATES",
    "PartnerIdentity",
    "PartnerRefusal",
    "partner_identity",
    "partner_ref_rows",
    "partner_rules_version",
]

#: The entity type every partner object is minted as (never ``deployment``, never
#: ``person``).
PARTNER_ENTITY_TYPE = "organization"

#: The crosswalk-id keys a record may carry for a party, and the guarded scheme each
#: maps to. Checked in this order; the first present wins.
CROSSWALK_SCHEMES: Mapping[str, str] = {
    "lei": "gleif.lei",
    "uei": "us.sam.uei",
    "duns": "dnb.duns",
    "cage": "us.dla.cage",
    "agency_code": "us.cgac.agency_code",
}
assert set(CROSSWALK_SCHEMES.values()) | {PARTNER_NAME_SCHEME} == PARTNER_ORG_SCHEMES

#: The partner predicates the connectors emit entity-ref claims for (ADR-112 §3, the
#: re-confirmed connector inventory; ADR-113 adds the P31.6 pair). Procurement
#: §11.11/§11.12 parties, the accountability event's organisations (§11.17), the
#: camera registry's operator, the Data Driven release's `vendor`, and the §12.2
#: configured-access edge predicate (named partners — data_driven twins it through
#: ``partner_ref_rows``; the flock/audit connectors attach the ref on the edge claim
#: itself, not through this helper). Each connector twins only its own subset.
PARTNER_PREDICATES: frozenset[str] = frozenset(
    {
        "buyer",
        "seller",
        "recipient",
        "funder",
        "event_organizations",
        "camera_operator",
        "vendor",
        "configured_sharing_partner",
    }
)

_NON_WORD = re.compile(r"[^a-z]")


@cache
def _rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "partner_identity.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def partner_rules_version() -> str:
    """The version stamp carried on every entity-ref record (both rulesets)."""
    return f"partner_identity/{_rules()['version']}+normalize/{NORMALIZE_RULESET_VERSION}"


@cache
def _token_set(key: str) -> frozenset[str]:
    return frozenset(str(t) for t in _rules()[key])


@cache
def _phrases(key: str) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(str(p).split()) for p in _rules()[key])


@dataclass(frozen=True)
class PartnerIdentity:
    """A partner that stands as an organisation: its guarded identifier and label."""

    scheme: str
    value: str
    label: str
    basis: str  # "crosswalk:<key>" or "normalized_name"

    def as_object_ref(self) -> dict[str, str]:
        """The ``object_ref`` a record carries to the claim sink."""
        return {
            "scheme": self.scheme,
            "value": self.value,
            "entity_type": PARTNER_ENTITY_TYPE,
            "label": self.label,
            "basis": self.basis,
            "rules": partner_rules_version(),
        }


@dataclass(frozen=True)
class PartnerRefusal:
    """Why a partner stays text only (the ambiguity or the never-a-person rule)."""

    reason: str


def _has_run(tokens: Sequence[str], phrase: Sequence[str]) -> bool:
    n = len(phrase)
    return any(tuple(tokens[i : i + n]) == tuple(phrase) for i in range(len(tokens) - n + 1))


def _display(name: str) -> str:
    return " ".join(name.split())


def partner_identity(
    name: str, *, crosswalk: Mapping[str, str] | None = None
) -> PartnerIdentity | PartnerRefusal:
    """Decide whether ``name`` names an organisation, and under which identifier.

    Returns a :class:`PartnerIdentity` or a :class:`PartnerRefusal` (the partner
    stays a text claim). The person and ambiguity checks run on the name even when a
    crosswalk id is present: sole traders register for UEIs and SIRETs too, so an id
    never overrides the never-a-person rule. See ``data/partner_identity.toml`` for
    the decision order.
    """
    raw = str(name or "")
    label = _display(raw)
    if not label:
        return PartnerRefusal("empty")
    normalized = normalize_org_name(label)
    tokens = normalized.split()
    words = [t for t in tokens if len(_NON_WORD.sub("", t)) >= 2]
    if not words:
        return PartnerRefusal("not_a_name")
    if any(sep in label for sep in _rules()["multi_party_separators"]):
        return PartnerRefusal("multiple_parties")
    token_set = set(tokens)
    if any(_has_run(tokens, p) for p in _phrases("individual_phrases")):
        return PartnerRefusal("sole_proprietor")
    if token_set & (_token_set("person_tokens") | _token_set("given_names")):
        return PartnerRefusal("person_shaped")
    if token_set & _token_set("role_tokens") and not token_set & _token_set("head_nouns"):
        return PartnerRefusal("person_shaped")  # a title beside a name ("Sheriff Smith")
    common = _token_set("generic_tokens") | _token_set("org_tokens")
    if not token_set - common:
        return PartnerRefusal("generic_name")
    if not token_set & _token_set("org_tokens"):
        return PartnerRefusal("single_word" if len(tokens) == 1 else "person_shaped")
    for key, scheme in CROSSWALK_SCHEMES.items():
        value = str((crosswalk or {}).get(key) or "").strip()
        if value:
            return PartnerIdentity(scheme, value, label, f"crosswalk:{key}")
    return PartnerIdentity(PARTNER_NAME_SCHEME, normalized, label, "normalized_name")


def _names(value: Any) -> list[str]:
    """The party names a claim value carries: one string, or each string of a list."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if isinstance(v, str) and v.strip()]
    return []


def partner_ref_rows(
    rows: Iterable[Mapping[str, Any]], *, predicates: Iterable[str] = PARTNER_PREDICATES
) -> list[dict[str, Any]]:
    """Append an entity-ref claim record after each eligible partner text claim.

    The connector ``link()`` stage calls this. Every input row is returned
    unchanged and in order. After a ``record_kind == "claim"`` row whose predicate
    is a partner predicate, one entity-ref record is added per party name that
    :func:`partner_identity` accepts. It is a copy of the text row (same subject,
    predicate, evidence locators, provenance), with that one party as its value and
    an ``object_ref``. A list-valued row (an event's organisations) yields one
    record per accepted party. A Part-VIII-suppressed row, an empty value, or a
    refused name adds nothing. The text claim is never touched.
    """
    wanted = frozenset(predicates)
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(dict(row) if not isinstance(row, dict) else row)
        if row.get("record_kind", "claim") != "claim" or row.get("predicate_id") not in wanted:
            continue
        if row.get("part_viii_suppressed") or row.get("object_ref"):
            continue
        names = _names(row.get("value"))
        seen: set[tuple[str, str]] = set()
        for party in names:
            ident = partner_identity(party)
            if not isinstance(ident, PartnerIdentity) or (ident.scheme, ident.value) in seen:
                continue
            seen.add((ident.scheme, ident.value))
            twin = dict(row)
            if len(names) > 1 or not isinstance(row.get("value"), str):
                twin["value"] = party
                twin["raw_value"] = party
            twin["object_ref"] = ident.as_object_ref()
            out.append(twin)
    return out
