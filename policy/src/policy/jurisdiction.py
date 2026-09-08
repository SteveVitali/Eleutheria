# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The jurisdiction adapter framework (§5.3, §13.7–13.8, §43.8).

The data model is international from the beginning (SIG-CHART-029) and MUST NOT
carry a US-shaped assumption (SIG-CHART-030, §5.3). This module is the reusable
**jurisdiction adapter** a new country plugs into: it declares, as data, the five
things onboarding a jurisdiction requires —

1. its **jurisdiction code system(s)** and level hierarchy,
2. its **organization types** (a national namespace, not a widened US enum),
3. its **legal-instrument types** (likewise namespaced),
4. its **records-request vocabulary** (the internationalised acquisition method,
   including ``no_equivalent_available`` for a jurisdiction with no access regime),
5. its **publication rules** (the jurisdiction-conditional profile of §43.8).

— and a **machine-checked checklist** (:func:`adapter_checklist`) plus the hard
no-US-shaped-assumption gate (:func:`assert_no_us_shaped_assumption`) that together
prove a non-US jurisdiction onboards with **no ``us.*``-only code path**. P18.2
(France/Belgium) is the first consumer of this framework.

The adapter set is **data, not code** (``policy/data/jurisdiction_adapters.toml``):
adding a country is a data row and a test fixture, never a schema change. The full
18-item checklist of the research base (R9 Part I) is recorded in
:data:`CHECKLIST_ITEMS`; the items expressible as ontology-vocabulary + publication
data are gated here, and the per-source ingestion items (boundary sources,
procurement portals, gazette routes, DPA corpora) are owned by each country's
connector work (Phase 18.2+).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from ._data import load_table
from .publication import publication_permitted

#: The US vocabulary namespace. A non-US adapter that reaches for a ``us.*`` term
#: is exactly the US-shaped assumption §5.3 prohibits.
US_NAMESPACE = "us"

#: Country-neutral vocabulary terms that are not owned by any single namespace:
#: the shared abstract parents (dotless, so they carry no prefix) plus the
#: explicit ``no_equivalent_available`` coverage fact (§13.8). Any adapter may
#: reference these without it counting as a foreign-namespace borrow.
SHARED_NEUTRAL_TERMS = frozenset({"no_equivalent_available"})

#: The 18-item jurisdiction-adapter checklist (R9 Part I). Each entry maps its
#: item to the adapter field that satisfies it, or ``None`` when the item is a
#: per-source ingestion concern a country's connector work owns (Phase 18.2+),
#: not something the framework can gate from vocabulary + publication data alone.
CHECKLIST_ITEMS: dict[str, str | None] = {
    "jurisdiction_levels": "jurisdiction_levels",  # 1
    "overlapping_parent_kinds": None,  # 2 — declared with levels; sources per-country
    "national_code_schemes": "national_code_schemes",  # 3
    "boundary_source": None,  # 4 — per-source ingestion (P18.2+)
    "wikidata_coverage_check": None,  # 5 — per-source ingestion (P18.2+)
    "organization_types": "organization_types",  # 6
    "organization_identifier_schemes": "national_code_schemes",  # 7
    "law_enforcement_registry": None,  # 8 — per-source ingestion (P18.2+)
    "legal_instrument_types": "legal_instrument_types",  # 9
    "authorization_regime": "legal_instrument_types",  # 10
    "data_protection_regime": "legal_instrument_types",  # 11
    "records_request_methods": "records_request_methods",  # 12
    "procurement_sources": None,  # 13 — per-source ingestion (P18.2+)
    "official_gazette": None,  # 14 — per-source ingestion (P18.2+)
    "default_languages": "default_languages",  # 15
    "date_number_locale": None,  # 16 — per-source ingestion (P18.2+)
    "publication_profile": "publication_profile",  # 17
    "local_partner": "local_partner",  # 18
}

#: The subset the framework gates now (item -> adapter field). The others are
#: deferred to per-country ingestion and are reported, not asserted.
GATED_ITEMS: dict[str, str] = {
    item: fld for item, fld in CHECKLIST_ITEMS.items() if fld is not None
}


class USShapedAssumptionError(Exception):
    """Raised when a non-US adapter reaches for a ``us.*``-only code path (§5.3).

    The mechanical form of SIG-CHART-030: onboarding a jurisdiction MUST NOT
    require a US-shaped vocabulary term. Raised naming the offending value so the
    defect is found here rather than in production.
    """


class AdapterIncomplete(Exception):
    """Raised when an adapter fails a gated checklist item (SIG-CHART-029)."""


@dataclass(frozen=True)
class JurisdictionAdapter:
    """One country's plug-in to the international data model (§5.3, §13.7).

    ``code`` is the jurisdiction identifier the publication engine keys on
    (``policy/data/jurisdictions.toml``, e.g. ``US``/``FR``/``UK``/``DE``);
    ``namespace`` is the vocabulary prefix its namespaced terms carry (``us``,
    ``fr``, ``uk``, ``de``) — the two differ deliberately (the UK's ISO code is
    ``GB`` but its vocabulary namespace is ``uk``).
    """

    code: str
    namespace: str
    #: Ordered coarse→fine `JurisdictionType` levels for the country (§11.1).
    jurisdiction_levels: tuple[str, ...] = ()
    #: Code-system / organization-identifier scheme ids (§11.1, §14.2).
    national_code_schemes: tuple[str, ...] = ()
    #: `OrganizationType` terms the country introduces (§11.2, §13.7).
    organization_types: tuple[str, ...] = ()
    #: `LegalInstrumentType` terms — authorization + data-protection regime (§11.14).
    legal_instrument_types: tuple[str, ...] = ()
    #: `AcquisitionMethod` records-request terms, incl. ``no_equivalent_available`` (§13.8).
    records_request_methods: tuple[str, ...] = ()
    #: BCP-47 default language tags for labels/presentation (§9.7, SIG-ONTO-069).
    default_languages: tuple[str, ...] = ()
    #: Transliteration scheme(s) for non-Latin scripts, if any (SIG-ONTO-069).
    transliteration_schemes: tuple[str, ...] = ()
    #: The §43.8 publication profile that applies (e.g. ``US-DEFAULT``, ``FR-GDPR``).
    publication_profile: str = ""
    #: The named local partner/reviewer (§7.1 Goal 7); absent ⇒ read-only mode (item 18).
    local_partner: str = ""

    @property
    def is_us(self) -> bool:
        return self.namespace == US_NAMESPACE

    def country_scoped_vocab(self) -> tuple[str, ...]:
        """The country-scoped vocabulary terms — the ones that MUST use this
        adapter's own namespace (jurisdiction levels, org / legal-instrument types,
        records-request methods). Code systems are excluded: they legitimately use
        global scheme namespaces (``iso.*``, ``wikidata.*``) as well as national
        ones, so they are gated only against the ``us.*`` ban, not the own-namespace
        rule."""
        return (
            *self.jurisdiction_levels,
            *self.organization_types,
            *self.legal_instrument_types,
            *self.records_request_methods,
        )

    def all_vocab(self) -> tuple[str, ...]:
        """Every vocabulary term this adapter references, across all five slots —
        including ``national_code_schemes``, so the ``us.*`` ban covers code
        systems too (a non-US adapter reaching for ``us.census.geoid`` is exactly
        the US-shaped assumption §5.3 prohibits)."""
        return (*self.country_scoped_vocab(), *self.national_code_schemes)


def _prefix(term: str) -> str | None:
    """The namespace segment of a ``<cc>.*`` term, or ``None`` for a dotless one."""
    return term.split(".", 1)[0] if "." in term else None


def assert_no_us_shaped_assumption(adapter: JurisdictionAdapter) -> None:
    """Gate a non-US adapter against any ``us.*``-only vocabulary term (§5.3).

    Two rules, both skipped for a US adapter (it *is* the ``us`` namespace):

    1. **No ``us.*`` term, anywhere** (SIG-CHART-030). Across *all five* onboarding
       slots — including ``national_code_schemes`` — a term in the ``us`` namespace
       means the country cannot be onboarded without a US-shaped code path.
    2. **Country-scoped terms use the adapter's own namespace.** For jurisdiction
       levels, org / legal-instrument types, and records-request methods, a
       namespaced term must carry the adapter's own namespace; a dotless term is a
       country-neutral shared abstract parent and is always admissible, as is an
       explicitly neutral term (:data:`SHARED_NEUTRAL_TERMS`). (Code systems are
       exempt from rule 2 — they legitimately use global scheme namespaces such as
       ``iso.*`` / ``wikidata.*`` — but not from rule 1.)

    Either violation raises :class:`USShapedAssumptionError` naming the term.
    """
    if adapter.is_us:
        return
    # Rule 1: the hard us.* ban, across every slot (SIG-CHART-030).
    for term in adapter.all_vocab():
        if _prefix(term) == US_NAMESPACE:
            raise USShapedAssumptionError(
                f"adapter {adapter.code!r} (namespace {adapter.namespace!r}) references "
                f"{term!r}, a {US_NAMESPACE}.* term; onboarding it would require a "
                f"US-shaped code path (§5.3, SIG-CHART-030)."
            )
    # Rule 2: country-scoped vocab must use the adapter's own namespace.
    for term in adapter.country_scoped_vocab():
        if term in SHARED_NEUTRAL_TERMS:
            continue
        prefix = _prefix(term)
        if prefix is None:
            continue  # a shared abstract parent — country-neutral
        if prefix != adapter.namespace:
            raise USShapedAssumptionError(
                f"adapter {adapter.code!r} (namespace {adapter.namespace!r}) references "
                f"{term!r}, which is in the {prefix!r} namespace, not its own; a country "
                f"onboards under its own namespace (§5.3, SIG-ONTO-068)."
            )


def adapter_checklist(adapter: JurisdictionAdapter) -> dict[str, bool]:
    """Evaluate the gated checklist items for ``adapter`` (SIG-CHART-029).

    Returns ``{item: satisfied}`` over :data:`GATED_ITEMS`. An item is satisfied
    when its backing adapter field is non-empty — a country onboards by supplying
    its code system, org types, legal instruments, records-request vocabulary,
    languages, a publication profile, and a named local partner.
    """
    result: dict[str, bool] = {}
    for item, fld in GATED_ITEMS.items():
        result[item] = bool(getattr(adapter, fld))
    return result


def validate_adapter(adapter: JurisdictionAdapter) -> dict[str, bool]:
    """Run the full framework gate over ``adapter`` and return its checklist.

    Enforces the no-US-shaped-assumption rule (:func:`assert_no_us_shaped_assumption`)
    then requires every gated checklist item to pass (:class:`AdapterIncomplete`).
    This is what a Stage-6 onboarding proves against.
    """
    assert_no_us_shaped_assumption(adapter)
    checklist = adapter_checklist(adapter)
    missing = sorted(item for item, ok in checklist.items() if not ok)
    if missing:
        raise AdapterIncomplete(
            f"adapter {adapter.code!r} is missing checklist items {missing} "
            "(§5.3 jurisdiction-adapter checklist, SIG-CHART-029)."
        )
    return checklist


def _adapter_from_row(code: str, row: Mapping[str, Any]) -> JurisdictionAdapter:
    def seq(key: str) -> tuple[str, ...]:
        return tuple(row.get(key, []))

    return JurisdictionAdapter(
        code=code,
        namespace=str(row["namespace"]),
        jurisdiction_levels=seq("jurisdiction_levels"),
        national_code_schemes=seq("national_code_schemes"),
        organization_types=seq("organization_types"),
        legal_instrument_types=seq("legal_instrument_types"),
        records_request_methods=seq("records_request_methods"),
        default_languages=seq("default_languages"),
        transliteration_schemes=seq("transliteration_schemes"),
        publication_profile=str(row.get("publication_profile", "")),
        local_partner=str(row.get("local_partner", "")),
    )


@cache
def adapters() -> dict[str, JurisdictionAdapter]:
    """The seeded jurisdiction adapters, keyed by jurisdiction code (data table)."""
    table = load_table("jurisdiction_adapters")
    return {code: _adapter_from_row(code, row) for code, row in table.get("adapters", {}).items()}


def get(code: str) -> JurisdictionAdapter:
    """Return one adapter by jurisdiction code, or raise :class:`KeyError`."""
    return adapters()[code]


def adapter_publication_permitted(
    adapter: JurisdictionAdapter,
    record_origin_jurisdiction: str,
    *,
    is_public_employee_name: bool,
) -> bool:
    """Jurisdiction-conditional publication for a subject in ``adapter`` (§43.8).

    A thin, adapter-aware wrapper over :func:`policy.publication.publication_permitted`:
    the data subject's jurisdiction is the adapter's own ``code``, and both it and the
    record's origin jurisdiction must permit publication (SIG-PUB-017). The evaluation
    keys on the jurisdiction ``code`` (``policy/data/jurisdictions.toml``); the
    adapter's ``publication_profile`` is the *name* of the §43.8 regime that applies
    (e.g. ``FR-GDPR`` vs ``US-DEFAULT``, checklist item 17), not itself the lookup
    key. Keeping the subject jurisdiction bound to the adapter is what makes the
    France/US contrast — redact-by-default under FR-GDPR vs presumptively-public
    under US-DEFAULT — fall out of the adapter set rather than a hard-coded global
    rule.
    """
    return publication_permitted(
        adapter.code,
        record_origin_jurisdiction,
        is_public_employee_name=is_public_employee_name,
    )
