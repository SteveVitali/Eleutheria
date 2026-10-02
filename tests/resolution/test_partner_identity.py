# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Partner-organisation identity (P31.5 / ADR-112 + P32.3 / ADR-122): one scheme,
the ambiguity rule and the never-a-person rule (Part VIII), the scope-qualified
name key (SIG-TRUST-004), the role gate (SIG-TRUST-003), and the ``link()``
helper that emits the entity-ref twin without touching the text claim."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from db.identity_guard import (
    GUARDED_SCHEMES,
    PARTNER_NAME_SCHEME,
    PARTNER_NAME_SCOPED_SCHEME,
    PARTNER_ORG_SCHEMES,
)
from resolution.partner_identity import (
    CROSSWALK_SCHEMES,
    PARTNER_PREDICATES,
    PartnerIdentity,
    PartnerRefusal,
    partner_identity,
    partner_ref_rows,
    partner_rules_version,
    scoped_name_key,
)

#: The schemes the P31.5 sqitch backfill (``partner_org_identity_key.sql``)
#: keyed — the legacy global-name scheme plus the five crosswalk ids. The
#: P32.3 scoped-name scheme backfills in ``partner_org_scoped_identity_key.sql``.
LEGACY_PARTNER_SCHEMES = PARTNER_ORG_SCHEMES - {PARTNER_NAME_SCOPED_SCHEME}

REPO = Path(__file__).resolve().parents[2]


# --- organisations mint, under the normalized name -----------------------------


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (
            "Washington State Department of Transportation",
            "washington state department of transportation",
        ),
        (
            "WASHINGTON STATE DEPARTMENT OF TRANSPORTATION",
            "washington state department of transportation",
        ),
        ("Kentucky Transportation Cabinet", "kentucky transportation cabinet"),
        ("Axon Enterprise, Inc.", "axon enterprise inc"),
        ("Motorola Solutions", "motorola solutions"),
        ("Flock Group Inc", "flock group inc"),
        ("CITY OF SEATTLE", "city of seattle"),
        ("Los Angeles County Sheriff's Dept", "los angeles county sheriff office"),
        ("LAPD", "los angeles police department"),  # exact acronym table hit
        ("Ville de Paris", "ville de paris"),
        ("Polska Agencja Żeglugi Powietrznej", "polska agencja zeglugi powietrznej"),
        ("Smith Electric LLC", "smith electric llc"),  # a company, not its owner
        # place names that are also given names are not refused by the given-name list
        ("San Jose Police Department", "san jose police department"),
        ("St. Paul Police Department", "st paul police department"),
        ("Will County Sheriff's Office", "will county sheriff office"),
        ("Axis Communications AB", "axis communications ab"),
    ],
)
def test_organisations_mint_under_the_scoped_name(name: str, value: str) -> None:
    # P32.3 / ADR-122: a name-only mint keys under ``sig.org.name_scoped`` as
    # ``src:unknown|<name>`` when no jurisdiction/scope is evidenced, marked a
    # candidate (unmerged). The legacy global ``sig.org.name`` is retired.
    ident = partner_identity(name)
    assert isinstance(ident, PartnerIdentity), ident
    assert (ident.scheme, ident.value, ident.basis) == (
        PARTNER_NAME_SCOPED_SCHEME,
        f"src:unknown|{value}",
        "normalized_name_scoped",
    )
    assert ident.candidate is True and ident.scope == "src:unknown"
    assert ident.label == " ".join(name.split())


def test_the_same_body_written_two_ways_is_one_identifier() -> None:
    a = partner_identity("Washington State Department of Transportation")
    b = partner_identity("  WASHINGTON  STATE DEPARTMENT OF TRANSPORTATION ")
    assert isinstance(a, PartnerIdentity) and isinstance(b, PartnerIdentity)
    assert (a.scheme, a.value) == (b.scheme, b.value)
    assert a.label != b.label  # the label is the verbatim display form


# --- P32.3 / SIG-TRUST-004: conservative organisation identity -----------------


def test_identical_names_across_jurisdictions_never_union() -> None:
    # "Springfield Police Department" exists in many states: the SAME name at
    # different evidenced jurisdictions keys differently — no auto-union.
    ok = partner_identity("Springfield Police Department", jurisdiction="us.state_abbr:OK")
    il = partner_identity("Springfield Police Department", jurisdiction="us.state_abbr:IL")
    assert isinstance(ok, PartnerIdentity) and isinstance(il, PartnerIdentity)
    assert (ok.scheme, ok.value) != (il.scheme, il.value)
    assert ok.value == "jur:us.state_abbr:ok|springfield police department"
    assert il.value == "jur:us.state_abbr:il|springfield police department"
    assert ok.scope == "jur:us.state_abbr:ok" and il.scope == "jur:us.state_abbr:il"
    # jurisdiction is carried as the identity basis on the mint
    assert ok.jurisdiction == "us.state_abbr:OK" and il.jurisdiction == "us.state_abbr:IL"


def test_identical_names_in_one_jurisdiction_union() -> None:
    a = partner_identity("City of Seattle", jurisdiction="us.state_abbr:WA")
    b = partner_identity("  CITY OF SEATTLE ", jurisdiction="us.state_abbr:WA")
    assert isinstance(a, PartnerIdentity) and isinstance(b, PartnerIdentity)
    assert (a.scheme, a.value) == (b.scheme, b.value)


def test_different_source_scopes_never_union() -> None:
    # With no evidenced jurisdiction the asserting source scopes the key —
    # "City of Example Falls" under one source never unions with another's.
    a = partner_identity("City of Example Falls", scope="okc-contract")
    b = partner_identity("City of Example Falls", scope="tulsa-contract")
    assert isinstance(a, PartnerIdentity) and isinstance(b, PartnerIdentity)
    assert (a.scheme, a.value) != (b.scheme, b.value)
    assert a.value == "src:okc-contract|city of example falls"
    same = partner_identity("City of Example Falls", scope="okc-contract")
    assert (same.scheme, same.value) == (a.scheme, a.value)


def test_a_strong_external_id_joins_within_scope() -> None:
    # The same UEI asserted under two different source scopes is ONE
    # organisation — the external id is itself the universal scope.
    a = partner_identity("Flock Group Inc", crosswalk={"uei": "ABC123"}, scope="src:a")
    b = partner_identity("FLOCK GROUP INC", crosswalk={"uei": "ABC123"}, scope="src:b")
    assert isinstance(a, PartnerIdentity) and isinstance(b, PartnerIdentity)
    assert (a.scheme, a.value) == (b.scheme, b.value) == ("us.sam.uei", "ABC123")
    # a crosswalk mint is not a name-only candidate
    assert a.candidate is False and a.scope is None and a.jurisdiction is None


def test_uncertain_identity_stays_a_candidate() -> None:
    ident = partner_identity("City of Example Falls", jurisdiction="us.state_abbr:OK")
    assert isinstance(ident, PartnerIdentity)
    ref = ident.as_object_ref(role="operator")
    assert ref["candidate"] is True
    assert ref["jurisdiction"] == "us.state_abbr:OK"
    assert ref["scope"] == "jur:us.state_abbr:ok"
    assert ref["role"] == "operator"
    # a crosswalk ref carries no candidate/scope markers
    ext = partner_identity("Flock Group Inc", crosswalk={"lei": "L1"})
    assert isinstance(ext, PartnerIdentity)
    ext_ref = ext.as_object_ref()
    assert "candidate" not in ext_ref and "scope" not in ext_ref


def test_generic_fema_name_stays_unresolved() -> None:
    # P31.13 preserved: the generic "Federal Emergency Management Agency" — the
    # words name a body in every federal context — refuses the mint even with a
    # jurisdiction attached, and even with a crosswalk id present (the P31.5
    # decision order runs ambiguity before the crosswalk: a generic name never
    # AUTO-resolves — a human disposition may still join the id claim).
    assert partner_identity("Federal Emergency Management Agency") == PartnerRefusal("generic_name")
    assert partner_identity(
        "Federal Emergency Management Agency", jurisdiction="us.cgac.agency_code:7000"
    ) == PartnerRefusal("generic_name")
    assert partner_identity(
        "Federal Emergency Management Agency", crosswalk={"agency_code": "70"}
    ) == PartnerRefusal("generic_name")


def test_scoped_name_key_format() -> None:
    assert scoped_name_key("city of seattle", jurisdiction="us.state_abbr:WA") == (
        "jur:us.state_abbr:wa|city of seattle",
        "jur:us.state_abbr:wa",
    )
    assert scoped_name_key("city of seattle", scope="x") == (
        "src:x|city of seattle",
        "src:x",
    )
    assert scoped_name_key("city of seattle") == (
        "src:unknown|city of seattle",
        "src:unknown",
    )


def test_a_crosswalk_id_wins_over_the_name() -> None:
    ident = partner_identity("Axon Enterprise, Inc.", crosswalk={"uei": " ABC123DEF456 "})
    assert isinstance(ident, PartnerIdentity)
    assert (ident.scheme, ident.value, ident.basis) == (
        "us.sam.uei",
        "ABC123DEF456",
        "crosswalk:uei",
    )
    lei_first = partner_identity("Axon Enterprise, Inc.", crosswalk={"uei": "U", "lei": "L"})
    assert isinstance(lei_first, PartnerIdentity) and lei_first.scheme == "gleif.lei"


# --- the never-a-person rule (Part VIII) -------------------------------------


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("John A. Smith", "person_shaped"),
        ("SMITH, JOHN", "person_shaped"),
        ("JOHN Q CITIZEN", "person_shaped"),
        ("Jane Doe", "person_shaped"),
        ("Maria de la Cruz Garcia", "person_shaped"),
        ("Dr. Jane Roe", "person_shaped"),
        ("John Smith Jr", "person_shaped"),
        ("Jane Q. Public dba JQP Consulting", "sole_proprietor"),
        ("JOHN SMITH DBA SMITH ELECTRIC LLC", "sole_proprietor"),
        ("John Smith doing business as Smith Security Services", "sole_proprietor"),
        ("Smith Consulting, a sole proprietorship", "sole_proprietor"),
        ("Jean Dupont entrepreneur individuel", "sole_proprietor"),
        ("Smith Family Trust", "sole_proprietor"),
        # two-letter legal forms are also name syllables: never an organisation marker
        ("Kim Se-hoon", "person_shaped"),
        ("Park Se Ri", "person_shaped"),
        ("Jose Sa", "person_shaped"),
        ("Maria de Sa", "person_shaped"),
        ("Lee Ag", "person_shaped"),
        ("Known as John Smith", "person_shaped"),
        # a title beside a name is a person (the officer-naming gate)
        ("Sheriff John Smith", "person_shaped"),
        ("Sheriff Smith", "person_shaped"),
        ("Chief of Police John Smith", "person_shaped"),
        ("Police Chief Jane Doe", "person_shaped"),
        ("John Smith, Police Officer", "person_shaped"),
        ("Detective John Smith, Springfield Police Department", "person_shaped"),
        ("Trooper Jane Doe, State Patrol", "person_shaped"),
        ("County Attorney John Smith", "person_shaped"),
        # a given name makes a trade name sole-proprietor-shaped
        ("John Smith Consulting", "person_shaped"),
        ("Jane Doe Security Services", "person_shaped"),
        ("Bob Jones Enterprises", "person_shaped"),
        ("John Smith Law Group", "person_shaped"),
        ("Law Office of John Smith", "person_shaped"),
        ("Siemens AG", "person_shaped"),  # recall cost of dropping the two-letter forms
    ],
)
def test_person_and_sole_proprietor_shaped_names_never_mint(name: str, reason: str) -> None:
    assert partner_identity(name) == PartnerRefusal(reason)


def test_a_crosswalk_id_never_overrides_the_person_rule() -> None:
    # Sole traders register for UEIs too: the id does not make the name an organisation.
    refusal = partner_identity("Jane Q. Public dba JQP Consulting", crosswalk={"uei": "X"})
    assert refusal == PartnerRefusal("sole_proprietor")
    assert partner_identity("John A. Smith", crosswalk={"duns": "123"}) == PartnerRefusal(
        "person_shaped"
    )


# --- the ambiguity rule -----------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("31483054800140", "not_a_name"),  # a bare SIRET: an id of unknown scheme
        ("12-345", "not_a_name"),
        ("King County / WSDOT", "multiple_parties"),
        ("Acme Corp; Beta LLC", "multiple_parties"),
        ("Police Department", "generic_name"),
        ("Department of Transportation", "generic_name"),
        ("Department of Justice", "generic_name"),
        ("City", "generic_name"),
        ("Unknown", "generic_name"),
        ("Various vendors", "generic_name"),
        ("N/A", "not_a_name"),
        ("TBD", "generic_name"),
        # the same words name a body in every jurisdiction
        ("Fire Department", "generic_name"),
        ("Highway Patrol", "generic_name"),
        ("School District", "generic_name"),
        ("Board of Education", "generic_name"),
        ("City Council", "generic_name"),
        ("Housing Authority", "generic_name"),
        ("Port Authority", "generic_name"),
        ("Transit Authority", "generic_name"),
        ("Department of Motor Vehicles", "generic_name"),
        ("Office of the County Attorney", "generic_name"),
        ("Verkada", "single_word"),  # a bare brand or surname cannot be told apart
        ("Smith", "single_word"),
    ],
)
def test_ambiguous_partners_stay_text_only(name: str, reason: str) -> None:
    assert partner_identity(name) == PartnerRefusal(reason)


# --- the link() helper: a separate record, the text claim untouched -------------


def _row(predicate: str, value: object, **extra: object) -> dict[str, object]:
    return {
        "record_kind": "claim",
        "subject_id": "contract:src:1",
        "predicate_id": predicate,
        "value": value,
        "raw_value": value if isinstance(value, str) else ";".join(map(str, value or ())),  # type: ignore[call-overload]
        "source_id": "src",
        "evidence": {"locator": {"kind": "row", "row": 0}},
        **extra,
    }


def test_partner_ref_rows_appends_a_twin_after_the_untouched_text_claim() -> None:
    text = _row("buyer", "City of Example Falls")
    snapshot = dict(text)
    other = _row("amount", "100")
    marker = {"record_kind": "contract", "subject_id": "contract:src:1", "predicate_id": "buyer"}
    out = partner_ref_rows([text, other, marker])
    assert out[0] is text and text == snapshot  # the text claim is not modified
    assert out[1]["object_ref"]["value"] == "src:unknown|city of example falls"
    assert out[2:] == [other, marker]  # a non-partner claim / a non-claim row: no twin
    twin = out[1]
    assert {k: v for k, v in twin.items() if k != "object_ref"} == snapshot
    assert twin["object_ref"] == {
        "scheme": PARTNER_NAME_SCOPED_SCHEME,
        "value": "src:unknown|city of example falls",
        "entity_type": "organization",
        "label": "City of Example Falls",
        "basis": "normalized_name_scoped",
        "scope": "src:unknown",
        "candidate": True,
        "role": "buyer",
        "rules": partner_rules_version(),
    }


def test_partner_ref_rows_carries_the_evidenced_scope_and_role() -> None:
    # P32.3 / SIG-TRUST-004: a row's ``partner_jurisdiction`` anchors the
    # name-only mint; the predicate's organisation role rides on the ref.
    row = _row(
        "camera_operator",
        "Oklahoma City Police Department",
        partner_jurisdiction="us.state_abbr:OK",
    )
    out = partner_ref_rows([row])
    twin = out[1]
    assert twin["object_ref"]["value"] == ("jur:us.state_abbr:ok|oklahoma city police department")
    assert twin["object_ref"]["role"] == "operator"
    assert twin["object_ref"]["candidate"] is True


def test_partner_ref_rows_a_row_crosswalk_keys_the_strong_id() -> None:
    # P32.3 / SIG-TRUST-004: a connector row that carries the party's external
    # id takes the crosswalk path — two sources asserting the same UEI key ONE
    # guarded entity (the union a name-only mint refuses).
    govspend = _row("buyer", "Example Operations Bureau", partner_crosswalk={"uei": "X1"})
    usaspending = _row("recipient", "EXAMPLE OPERATIONS BUREAU", partner_crosswalk={"uei": "X1"})
    out = partner_ref_rows([govspend, usaspending])
    a, b = out[1]["object_ref"], out[3]["object_ref"]
    assert a["scheme"] == b["scheme"] == "us.sam.uei" and a["value"] == b["value"] == "X1"
    assert a["basis"] == b["basis"] == "crosswalk:uei"
    assert "candidate" not in a and "scope" not in a
    # A malformed crosswalk value is ignored — the row falls back to the
    # scoped name mint, never crashing the link stage.
    bad = _row("buyer", "Example Operations Bureau", partner_crosswalk="X1")
    out = partner_ref_rows([bad])
    assert out[1]["object_ref"]["scheme"] == PARTNER_NAME_SCOPED_SCHEME


def test_partner_ref_rows_never_mints_a_publisher() -> None:
    # P32.3 / SIG-TRUST-003: ``camera_registry_publisher`` is provenance — even
    # a caller that names it as a partner predicate gets NO entity-ref twin.
    row = _row("camera_registry_publisher", "OSM Contributors")
    out = partner_ref_rows([row], predicates={"camera_registry_publisher"})
    assert out == [row]
    # and the unmapped default-path case: not in PARTNER_PREDICATES at all
    assert partner_ref_rows([row]) == [row]


def test_partner_ref_rows_splits_a_list_value_and_drops_refused_parties() -> None:
    row = _row(
        "event_organizations",
        ["Washington State Department of Transportation", "Jane Doe", "Police Department"],
    )
    out = partner_ref_rows([row])
    assert out[0] is row
    twins = out[1:]
    assert [t["value"] for t in twins] == ["Washington State Department of Transportation"]
    assert twins[0]["raw_value"] == "Washington State Department of Transportation"


def test_partner_ref_rows_adds_nothing_for_refused_suppressed_or_empty_parties() -> None:
    rows = [
        _row("seller", "John A. Smith"),
        _row("seller", None),
        _row("buyer", "City of Example Falls", part_viii_suppressed=True),
        _row("recipient", "JOHN Q CITIZEN"),
    ]
    assert partner_ref_rows(rows) == rows


def test_partner_ref_rows_only_touches_the_named_predicates() -> None:
    rows = [
        _row("buyer", "City of Example Falls"),
        _row("camera_operator", "City of Example Falls"),
    ]
    out = partner_ref_rows(rows, predicates={"camera_operator"})
    assert [r.get("object_ref", {}).get("value") for r in out] == [
        None,
        None,
        "src:unknown|city of example falls",
    ]


def test_partner_predicates_are_the_reconfirmed_inventory() -> None:
    # ADR-112 §3: no procurement/accountability path emits `applies_to` or `operator`;
    # the operator edge is the camera registry's `camera_operator`. `proceeding_parties`
    # (litigants) is excluded under Part VIII. P31.6 / ADR-113 added the two access-edge
    # predicates: `vendor` (the release's stated vendor) and `configured_sharing_partner`
    # (the directed subject→partner edge claim) — both resolve partner orgs through this
    # module except `flock_portal` slugs, which resolve through `sig.connector.subject`.
    assert PARTNER_PREDICATES == {
        "buyer",
        "seller",
        "recipient",
        "funder",
        "event_organizations",
        "camera_operator",
        "vendor",
        "configured_sharing_partner",
    }
    assert "proceeding_parties" not in PARTNER_PREDICATES


# --- the guarded schemes and their sqitch backfill stay in lock-step -------------


def test_partner_schemes_are_guarded_and_match_the_sqitch_backfill() -> None:
    assert PARTNER_ORG_SCHEMES <= GUARDED_SCHEMES
    assert (
        set(CROSSWALK_SCHEMES.values()) | {PARTNER_NAME_SCHEME, PARTNER_NAME_SCOPED_SCHEME}
        == PARTNER_ORG_SCHEMES
    )
    assert "us.census.fips" not in GUARDED_SCHEMES  # a shared place attribute, never keyed
    # the P31.5 backfill keys the legacy schemes (the global name + crosswalks)
    for part in ("deploy", "verify"):
        sql = (REPO / "db" / part / "partner_org_identity_key.sql").read_text()
        lists = re.findall(r"scheme IN \(([^)]*)\)", sql)
        assert lists, part
        for listed in lists:
            assert set(re.findall(r"'([^']+)'", listed)) == LEGACY_PARTNER_SCHEMES, part
    # the P32.3 backfill keys exactly the new scoped-name scheme
    scoped_sql = (REPO / "db" / "deploy" / "partner_org_scoped_identity_key.sql").read_text()
    assert "'sig.org.name_scoped'" in scoped_sql
    assert "sig.org.name_scoped" == PARTNER_NAME_SCOPED_SCHEME
