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
  **scope-qualified** normalized name under ``sig.org.name_scoped`` (P32.3 /
  ADR-122; :func:`resolution.normalize.normalize_org_name`, SIG-IDENT-022).

  P32.3 replaced the global ``sig.org.name`` key: a bare normalized name is NOT an
  identity — "City of Springfield Police Department" names a different body in
  every jurisdiction (SIG-TRUST-004). A name-only partner now keys as
  ``jur:<jurisdiction>|<name>`` when the record's jurisdiction is evidenced, else
  ``src:<source>|<name>`` inside the source scope that asserted it, and is marked
  ``candidate`` (unmerged) in its object ref. Two records union only when their
  scoped keys match byte-for-byte or a recorded identity disposition joins them —
  identical names across jurisdictions NEVER auto-union. The legacy
  ``sig.org.name`` scheme stays guarded for already-written rows but nothing new
  mints it; ``python -m resolution partner-name-audit`` produces the dry-run
  impact report for those legacy keys.
* **The ambiguity rule.** A value that is not a name, names several parties, is only
  generic words, or is one bare word stays a text claim.
* **The never-a-person rule (Part VIII).** A natural-person-shaped or
  sole-proprietor-shaped name never becomes an entity. An organisation needs a
  positive organisation marker. When in doubt the partner stays text.
* **The role gate (SIG-TRUST-003).** Only a predicate whose object plays an
  operational organisation role (:mod:`db.organization_roles`) may twin a
  partner ref. A provenance label — the registry's ``camera_registry_publisher``
  — is recorded as text and mints nothing: a publisher is not an operator.

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

from db.identity_guard import (
    PARTNER_NAME_SCHEME,
    PARTNER_NAME_SCOPED_SCHEME,
    PARTNER_ORG_SCHEMES,
)
from db.organization_roles import mints_entity_ref, role_for_predicate

from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name

__all__ = [
    "CROSSWALK_SCHEMES",
    "PARTNER_ENTITY_TYPE",
    "PARTNER_NAME_SCHEME",
    "PARTNER_NAME_SCOPED_SCHEME",
    "PARTNER_PREDICATES",
    "PartnerIdentity",
    "PartnerRefusal",
    "natural_person_signal",
    "partner_identity",
    "partner_ref_rows",
    "partner_rules_version",
    "scoped_name_key",
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
assert (
    set(CROSSWALK_SCHEMES.values())
    | {
        PARTNER_NAME_SCHEME,
        PARTNER_NAME_SCOPED_SCHEME,
    }
    == PARTNER_ORG_SCHEMES
)

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
assert all(mints_entity_ref(p) for p in PARTNER_PREDICATES)

_SCOPE_CLEAN = re.compile(r"[^a-z0-9._:-]+")


def _scope_token(token: str) -> str:
    """Normalise a jurisdiction/source token for the scoped-name key."""
    return _SCOPE_CLEAN.sub("_", str(token).strip().lower()) or "unknown"


def scoped_name_key(
    normalized: str, *, jurisdiction: str | None = None, scope: str | None = None
) -> tuple[str, str]:
    """The ``sig.org.name_scoped`` identifier value for a normalized name.

    Returns ``(key, scope_token)`` where ``key`` is ``jur:<jurisdiction>|<name>``
    when ``jurisdiction`` is evidenced, else ``src:<source>|<name>`` inside the
    asserting source's scope, else ``src:unknown|<name>``. Identical names in
    different scopes never collide, so nothing auto-unions across jurisdictions
    (SIG-TRUST-004).
    """
    if jurisdiction:
        scope_token = f"jur:{_scope_token(jurisdiction)}"
    elif scope:
        scope_token = f"src:{_scope_token(scope)}"
    else:
        scope_token = "src:unknown"
    return f"{scope_token}|{normalized}", scope_token


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
    """A partner that stands as an organisation: its guarded identifier and label.

    ``jurisdiction``/``scope``/``candidate`` (P32.3) carry the identity basis a
    name-only mint is anchored to; a crosswalk-id mint leaves them unset (the
    external id is itself the universal scope).
    """

    scheme: str
    value: str
    label: str
    basis: str  # "crosswalk:<key>" or "normalized_name_scoped"
    jurisdiction: str | None = None
    scope: str | None = None  # "jur:<jurisdiction>" / "src:<source>" / "src:unknown"
    candidate: bool = False  # name-only mints are unmerged review candidates

    def as_object_ref(self, *, role: str | None = None) -> dict[str, Any]:
        """The ``object_ref`` a record carries to the claim sink."""
        return {
            "scheme": self.scheme,
            "value": self.value,
            "entity_type": PARTNER_ENTITY_TYPE,
            "label": self.label,
            "basis": self.basis,
            "rules": partner_rules_version(),
            **({"jurisdiction": self.jurisdiction} if self.jurisdiction else {}),
            **({"scope": self.scope} if self.scope else {}),
            **({"candidate": True} if self.candidate else {}),
            **({"role": role} if role else {}),
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
    name: str,
    *,
    crosswalk: Mapping[str, str] | None = None,
    jurisdiction: str | None = None,
    scope: str | None = None,
) -> PartnerIdentity | PartnerRefusal:
    """Decide whether ``name`` names an organisation, and under which identifier.

    Returns a :class:`PartnerIdentity` or a :class:`PartnerRefusal` (the partner
    stays a text claim). The person and ambiguity checks run on the name even when a
    crosswalk id is present: sole traders register for UEIs and SIRETs too, so an id
    never overrides the never-a-person rule. See ``data/partner_identity.toml`` for
    the decision order.

    P32.3: ``jurisdiction`` (evidenced, e.g. ``"us.state_abbr:OK"``) scopes a
    name-only mint to that jurisdiction; ``scope`` (the asserting source id) is
    the fallback scope. A name-only result is always ``candidate=True`` — it has
    NOT been merged with any other entity and stays unmerged until a recorded
    disposition (SIG-TRUST-004).
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
    key, scope_token = scoped_name_key(normalized, jurisdiction=jurisdiction, scope=scope)
    return PartnerIdentity(
        PARTNER_NAME_SCOPED_SCHEME,
        key,
        label,
        "normalized_name_scoped",
        jurisdiction=jurisdiction,
        scope=scope_token,
        candidate=True,
    )


def natural_person_signal(name: str) -> str | None:
    """The affirmative natural-person signal a recipient name carries (P35.9 / P8-6).

    Returns the person-signal reason — ``"sole_proprietor"`` or
    ``"person_shaped"`` — when the name carries affirmative person evidence,
    else ``None``. Runs only the identity layer's *affirmative* person checks:
    a sole-trader phrase ("Jane Q. Public dba JQP Consulting"), a person /
    honorific / given-name token, or a bare role title beside a name
    ("Sheriff Smith"). The ambiguity refusals are NOT person evidence: a
    two-word name with no organisation marker is merely ambiguous
    ("Magnet Forensics" lands there — a company without a reviewed marker
    keeps its recipient claim, the ambiguity merely withholds the entity
    mint). Empty values, multi-party strings, and generic agency names
    return ``None`` — not persons, just refused entity mints.
    """
    raw = str(name or "")
    label = _display(raw)
    if not label:
        return None
    normalized = normalize_org_name(label)
    tokens = normalized.split()
    if not tokens:
        return None
    if any(_has_run(tokens, p) for p in _phrases("individual_phrases")):
        return "sole_proprietor"
    token_set = set(tokens)
    if token_set & (_token_set("person_tokens") | _token_set("given_names")):
        return "person_shaped"
    if token_set & _token_set("role_tokens") and not token_set & _token_set("head_nouns"):
        return "person_shaped"
    return None


def _names(value: Any) -> list[str]:
    """The party names a claim value carries: one string, or each string of a list."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if isinstance(v, str) and v.strip()]
    return []


def partner_ref_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    predicates: Iterable[str] = PARTNER_PREDICATES,
    scope: str | None = None,
    jurisdiction: str | None = None,
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

    P32.3 (SIG-TRUST-003/004):

    * the role gate runs on every row — a predicate whose object is a provenance
      role (``camera_registry_publisher``) or unmapped never mints a ref, even if
      a caller widens ``predicates`` (``db.organization_roles.mints_entity_ref``);
    * ``jurisdiction``/``scope`` (or per-row ``partner_jurisdiction``/
      ``partner_scope``) anchor name-only mints to their evidenced scope, and the
      minted ref carries the predicate's organisation role;
    * a per-row ``partner_crosswalk`` mapping (e.g. ``{"uei": "ABC…"}``) takes
      the crosswalk-id path — two sources asserting the same external id key
      the same guarded entity and join (SIG-TRUST-004), while name-only mints
      never do.
    """
    wanted = frozenset(predicates)
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(dict(row) if not isinstance(row, dict) else row)
        predicate = row.get("predicate_id")
        if row.get("record_kind", "claim") != "claim" or predicate not in wanted:
            continue
        if not mints_entity_ref(str(predicate)):
            continue  # provenance roles (publisher/host) mint nothing — SIG-TRUST-003
        if row.get("part_viii_suppressed") or row.get("object_ref"):
            continue
        role = role_for_predicate(str(predicate))
        row_jurisdiction = row.get("partner_jurisdiction", jurisdiction)
        row_scope = row.get("partner_scope", scope)
        row_crosswalk = row.get("partner_crosswalk")
        names = _names(row.get("value"))
        seen: set[tuple[str, str]] = set()
        for party in names:
            ident = partner_identity(
                party,
                crosswalk=row_crosswalk if isinstance(row_crosswalk, Mapping) else None,
                jurisdiction=row_jurisdiction,
                scope=row_scope,
            )
            if not isinstance(ident, PartnerIdentity) or (ident.scheme, ident.value) in seen:
                continue
            seen.add((ident.scheme, ident.value))
            twin = dict(row)
            if len(names) > 1 or not isinstance(row.get("value"), str):
                twin["value"] = party
                twin["raw_value"] = party
            twin["object_ref"] = ident.as_object_ref(role=str(role) if role else None)
            out.append(twin)
    return out
