# SPDX-License-Identifier: Apache-2.0
"""P35.29 — the ONE label derivation (K2 §3/L-1…L-7, A-10/ADR-159, K11 §3).

Every assertion here is an *invariant*, never a living record: UUIDs are
fresh, names are fixture strings, and no test reads a built artifact.
"""

from __future__ import annotations

import re
import uuid

import pytest
from policy.labels import (
    HASH_LEN,
    LABEL_BASES,
    LABEL_MAX,
    SLUG_MAX,
    EntityLabel,
    LabelFacts,
    derive_label,
    entity_hash,
    entity_url,
    hash4,
    kind_for,
    name_slug,
    resolve_disambiguators,
    sanitize_label,
)
from resolution.partner_identity import natural_person_signal


def _eid() -> str:
    return str(uuid.uuid4())


def facts(**kw) -> LabelFacts:
    kw.setdefault("entity_id", _eid())
    return LabelFacts(**kw)


def _screen(text: str) -> bool:
    """The production screen: partner_identity's affirmative person signal."""
    return bool(natural_person_signal(text))


def derive(f: LabelFacts) -> EntityLabel:
    """derive_label with the production person screen, as every call site passes."""
    return derive_label(f, person_screen=_screen)


# ---------------------------------------------------------------------------
# §3.2 per-kind derivations — label + basis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw,label_prefix,basis",
    [
        # org (allow): canonical name, source casing preserved
        (
            dict(
                entity_type="organisation",
                disposition="allow",
                canonical_name="Acme Surveillance LLC",
            ),
            "Acme Surveillance LLC",
            "source_name",
        ),
        # site: camera_name → tech-class derived
        (
            dict(
                entity_type="camera",
                disposition="allow",
                fields={"camera_name": "I-44 @ Riverside", "agency_name": "Tulsa PD"},
            ),
            "I-44 @ Riverside",
            "source_name",
        ),
        (
            dict(
                entity_type="camera",
                disposition="allow",
                extra={"technology": "ALPR", "place_jkey": "iso3166-2:US-OK"},
                place="Oklahoma",
            ),
            "alpr camera in Oklahoma",
            "derived",
        ),
        # agency
        (
            dict(
                entity_key="agency:tulsa-pd",
                disposition="allow",
                fields={"agency_name": "Tulsa Police Department"},
            ),
            "Tulsa Police Department",
            "source_name",
        ),
        # jurisdiction: registry name via extra
        (
            dict(
                entity_key="jurisdiction:iso.3166-1:US",
                disposition="allow",
                extra={"registry_name": "United States"},
            ),
            "United States",
            "source_name",
        ),
        # program
        (
            dict(
                entity_key="program:safe-streets",
                disposition="allow",
                fields={"program_name": "Safe Streets Initiative"},
            ),
            "Safe Streets Initiative",
            "source_name",
        ),
        # contract: title → seller/buyer derived
        (
            dict(
                entity_key="contract:c-101",
                disposition="allow",
                fields={"title": "ALPR maintenance FY26"},
            ),
            "ALPR maintenance FY26",
            "source_title",
        ),
        (
            dict(
                entity_key="contract:c-102",
                disposition="allow",
                fields={"seller": "Vigilant Solutions Inc"},
            ),
            "Vigilant Solutions Inc contract",
            "derived",
        ),
        # grant
        (
            dict(
                entity_key="grant:g-1", disposition="allow", fields={"recipient": "City of Tulsa"}
            ),
            "City of Tulsa grant",
            "derived",
        ),
        # notice: derived triple (opaque key → no key_name wins)
        (
            dict(
                kind="notice",
                entity_key=None,
                disposition="allow",
                fields={"notice_type": "Solicitation", "posted_date": "2026-09-01"},
            ),
            "Solicitation · 2026-09-01",
            "derived",
        ),
        # bill: identifier + session
        (
            dict(
                entity_key="bill:ok-hb-1234",
                disposition="allow",
                fields={"bill_identifier": "HB 1234", "bill_session": "2026"},
            ),
            "HB 1234 (2026)",
            "key_name",
        ),
        # policy: place ordinance (display-name place)
        (
            dict(
                entity_key="policy:tulsa-ord-1",
                disposition="allow",
                place="Tulsa",
                extra={"place_jkey": "iso3166-2:US-OK"},
            ),
            "Tulsa ordinance",
            "derived",
        ),
        # event: body + date
        (
            dict(
                entity_key="event:agenda-7",
                disposition="allow",
                fields={"platform": "City Council", "meeting_date": "2026-10-06"},
            ),
            "Agenda item · City Council · 2026-10-06",
            "derived",
        ),
        # request
        (
            dict(
                entity_key="request:pra-9",
                disposition="allow",
                fields={"response_status": "partial", "response_date": "2026-08-15"},
                place="California",
                extra={"place_jkey": "iso3166-2:US-CA"},
            ),
            "Records request · California · partial · 2026-08-15",
            "derived",
        ),
        # atlas
        (
            dict(
                entity_key="atlas:odps-maps",
                disposition="allow",
                fields={"source_name": "ODPS public maps"},
            ),
            "ODPS public maps",
            "source_name",
        ),
        # portal
        (
            dict(
                entity_key="platform:okc-council",
                disposition="allow",
                fields={"platform": "OKC Council portal"},
            ),
            "OKC Council portal",
            "source_name",
        ),
    ],
)
def test_per_kind_derivation(kw, label_prefix, basis):
    r = derive(facts(**kw))
    assert r.label == label_prefix
    assert r.label_basis == basis
    assert r.label_state is None
    assert r.slug and r.hash and r.url
    assert re.fullmatch(r"/entity/[a-z]+/[a-z0-9-]+--[0-9a-z]+/", r.url)


def test_every_labelled_row_has_basis_and_fields():
    """L-3: basis is always populated for labelled rows; row() carries the schema."""
    r = derive(
        facts(entity_type="thing", disposition="allow", fields={"name": "North Gate ALPR array"})
    )
    assert r.label_basis in LABEL_BASES
    row = r.row()
    for key in (
        "entity_id",
        "sig_id",
        "kind",
        "url_type",
        "label",
        "descriptor",
        "label_basis",
        "label_source_id",
        "place_jkey",
        "slug",
        "hash",
        "url",
        "disambiguator",
        "component_id",
        "part8",
    ):
        assert key in row
    assert row["part8"] in ("pass", "fallback")


def test_fallback_label_is_typed_words_plus_hash4():
    """L-2/D-K2-5: a facts-less entity still gets a label — never an identifier."""
    eid = _eid()
    r = derive(facts(entity_id=eid, entity_type="thing", disposition="allow"))
    assert r.label == f"Record #{hash4(eid)}"
    assert r.label_basis == "fallback"
    assert r.part8 == "fallback"
    # the fallback never contains the raw UUID
    assert eid not in (r.label or "")


def test_no_label_is_uuid_key_or_source_id():
    """SIG-UI-D20: labels never take identifier shape."""
    eid = _eid()
    r = derive(
        facts(
            entity_id=eid,
            entity_type="thing",
            disposition="allow",
            identifiers=(("sourceid", "SRC-9981"), ("serialno", "SN-44")),
        )
    )
    for bad in (eid, "SRC-9981", "SN-44"):
        assert bad not in (r.label or "")


# ---------------------------------------------------------------------------
# L-4/L-5 text hygiene
# ---------------------------------------------------------------------------


def test_sanitize_strips_controls_and_collapses_whitespace():
    assert sanitize_label("  Acme\x00  Corp\t\u200b LLC  \x7f") == "Acme Corp LLC"


def test_label_cap_80_word_boundary():
    long_name = " ".join(["Alpha"] * 30)
    r = derive(facts(entity_type="organisation", disposition="allow", canonical_name=long_name))
    assert len(r.label or "") <= LABEL_MAX
    assert (r.label or "").endswith("…")
    assert not (r.label or "")[:-1].rstrip().endswith("Alp")


def test_source_casing_preserved():
    r = derive(
        facts(entity_type="organisation", disposition="allow", canonical_name="eBay iNC weird CASE")
    )
    assert r.label == "eBay iNC weird CASE"


# ---------------------------------------------------------------------------
# L-6 person-name screen — incl. literal procurement parties
# ---------------------------------------------------------------------------


def test_person_shaped_candidate_never_labels():
    """A person-shaped literal trips the injected screen → typed fallback."""
    r = derive(
        facts(entity_type="camera", disposition="allow", fields={"camera_name": "John Q Public"})
    )
    assert r.label != "John Q Public"
    assert r.part8 == "fallback"
    assert "Public" not in (r.label or "")


def test_sole_proprietor_party_literal_screened():
    """Literal `seller`/`recipient` values run the screen before labelling."""
    r = derive(
        facts(
            entity_key="contract:c-9",
            disposition="allow",
            fields={"seller": "Jane Public dba JP Consulting"},
        )
    )
    assert "Jane Public" not in (r.label or "")
    assert r.part8 == "fallback"


def test_person_entities_are_never_labelled():
    r = derive(facts(entity_type="person", disposition="allow", canonical_name="Any Name"))
    assert r.label is None and r.slug is None and r.hash is None and r.url is None
    assert r.label_state == "withheld"
    assert r.part8 == "fallback"


def test_default_screen_failclosed_never_crashes():
    def bad_screen(_t: str) -> bool:
        raise RuntimeError("boom")

    r = derive_label(
        facts(entity_type="thing", disposition="allow", fields={"name": "Some label"}),
        person_screen=bad_screen,
    )
    # a crashing screen fails closed: every candidate refused → typed fallback
    assert r.part8 == "fallback"
    assert r.label_basis == "fallback"


# ---------------------------------------------------------------------------
# A-10 organisation gating
# ---------------------------------------------------------------------------


def test_allowed_org_labels():
    r = derive(
        facts(
            entity_type="organisation", disposition="allow", canonical_name="Motorola Solutions Inc"
        )
    )
    assert r.label == "Motorola Solutions Inc"
    assert r.label_state is None


def test_unmatched_org_is_typed_not_yet_reviewed():
    for disposition in (None, "pending", "review"):
        r = derive(
            facts(
                entity_type="organisation",
                disposition=disposition,
                canonical_name="Unreviewed Corp",
            )
        )
        assert r.label is None and r.slug is None and r.hash is None
        assert r.label_state == "not_yet_reviewed", disposition
        assert "Unreviewed Corp" not in (r.descriptor or "")


def test_denied_org_is_withheld():
    r = derive(facts(entity_type="organisation", disposition="deny", canonical_name="Blocked Corp"))
    assert r.label is None and r.label_state == "withheld"


# ---------------------------------------------------------------------------
# Deterministic disambiguation (§3.4)
# ---------------------------------------------------------------------------


def test_disambiguation_is_deterministic_and_unique():
    ids = [_eid(), _eid(), _eid()]

    def make(i: str) -> EntityLabel:
        return derive(
            facts(
                entity_id=i,
                entity_type="thing",
                disposition="allow",
                fields={"name": "North Gate ALPR array"},
            )
        )

    first = resolve_disambiguators([make(i) for i in ids])
    second = resolve_disambiguators([make(i) for i in ids])
    labels = [r.label for r in first]
    assert len(set(labels)) == 3  # no two entities of a kind share a full label
    assert labels == [r.label for r in second]  # pure function
    assert all(r.disambiguator for r in first)


def test_disambiguation_place_first():
    rows = [
        derive(
            facts(
                entity_id=_eid(),
                entity_type="thing",
                disposition="allow",
                fields={"name": "Municipal camera"},
                place="iso3166-2:US-OK",
                extra={},
            )
        ),
        derive(
            facts(
                entity_id=_eid(),
                entity_type="thing",
                disposition="allow",
                fields={"name": "Municipal camera"},
                place="Lubbock County",
                extra={},
            )
        ),
    ]
    # place_hint needs the human place, not the jkey — set via place field
    out = resolve_disambiguators(rows)
    # both rows carry distinct place_hints → the `· {place}` step fires
    assert all(r.disambiguator for r in out)
    assert len({r.label for r in out}) == 2


def test_noncolliding_rows_untouched():
    a = derive(facts(entity_type="thing", disposition="allow", fields={"name": "Row A"}))
    b = derive(facts(entity_type="thing", disposition="allow", fields={"name": "Row B"}))
    out = resolve_disambiguators([a, b])
    assert [r.disambiguator for r in out] == [None, None]


# ---------------------------------------------------------------------------
# Hash + slug primitives (K11 §3)
# ---------------------------------------------------------------------------


def test_entity_hash_is_7_crockford_chars():
    h = entity_hash(_eid())
    assert len(h) == HASH_LEN
    assert re.fullmatch(r"[0-9a-hjkmnp-tv-z]{7}", h)


def test_hash_extension_stays_prefix_stable():
    eid = _eid()
    assert entity_hash(eid, length=8).startswith(entity_hash(eid))


def test_hash_deterministic_over_uuid_text():
    eid = _eid()
    assert entity_hash(eid) == entity_hash(str(uuid.UUID(eid)))


def test_slug_ascii_folds_and_truncates():
    s = name_slug("État des Côtes Ñoño — très long " * 4)
    assert s is not None
    assert len(s) <= SLUG_MAX
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s)
    assert not s.endswith("-")


def test_slug_state_suffix():
    assert name_slug("Tulsa camera", state_slug="usa-ok") == "tulsa-camera-usa-ok"


def test_slug_none_when_label_folds_empty():
    assert name_slug("\x00\x01\x02") is None


def test_url_shape():
    assert entity_url("org", "acme-llc", "abcdefg") == "/entity/org/acme-llc--abcdefg/"


def test_kind_resolution():
    assert kind_for("organisation", None) == "org"
    assert kind_for(None, "contract:c-1") == "contract"
    assert kind_for(None, "platform:p-1") == "portal"
    assert kind_for(None, "registry:r-1") == "atlas"
    assert kind_for("mystery", "nothing:here") == "other"
    assert kind_for("person", None) == "person"


def test_descriptor_carries_kind_and_unplaced():
    r = derive(facts(entity_type="thing", disposition="allow", fields={"name": "Row"}))
    assert "Record" in (r.descriptor or "")
    assert "unplaced" in (r.descriptor or "")
