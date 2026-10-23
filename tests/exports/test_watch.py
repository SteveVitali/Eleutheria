# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.43 (K7 WX-01 / F-481, SIG-WATCH-D01…D04) — the watch producer's own suite.

The fixture spine exercises the §5.2 derivation rules end to end: one
auto-renewing contract with a notice window, one contract with an end date and
unknown renewal terms, one SAM-class procurement notice, one agenda item, one
matched bill and one grant — each with the claims its rule fires on, emitted
as the positional ``watch_claims`` rows the EXPORT_QUERIES read returns. The
assertions pin the honesty invariants: ``upper_bound`` never renders as a
deadline, an item exists only where its publishable claims exist, place is
``unplaced`` rather than guessed, evidence anchors carry the gated upstream
form, and an empty watch still emits its coverage statement.
"""

from __future__ import annotations

import json
from datetime import date

from exports.statements import BINDING_DETAIL_COLUMNS
from exports.watch import (
    SCHEMA_WATCH,
    SCHEMA_WATCH_ITEM,
    WATCH_CLAIMS_COLUMNS,
    WATCH_KINDS,
    _placement_input,
    build_watch_payload,
)
from exports.watch import (
    _claims as _normalized_claims,
)
from policy.transparency import LaneDecision

AS_OF = date(2026, 9, 22)
GENERATED = "2026-09-22T00:00:00Z"


def _claim(
    cid: str,
    subject_key: str,
    predicate: str,
    *,
    value_text: str | None = None,
    value_num: int | None = None,
    value_bool: bool | None = None,
    value_json: object = None,
    subject_id: str | None = None,
    source_id: str = "src_a",
    recorded_at: str = "2026-09-01T00:00:00+00",
    revises_claim: str | None = None,
    retraction_of: str | None = None,
) -> tuple:
    """One ``watch_claims`` row in the SELECT's column order."""
    assert len(WATCH_CLAIMS_COLUMNS) == 17
    return (
        cid,
        subject_id or f"ent-{subject_key}",
        subject_key,
        subject_key.split(":", 1)[0],
        predicate,
        value_text,
        value_num,
        value_bool,
        json.dumps(value_json) if value_json is not None else None,
        value_text if value_text is not None else "",
        None,  # observed_at
        recorded_at,
        revises_claim,
        retraction_of,
        "reviewed",
        source_id,
        "CC-BY-4.0",
    )


def _payload(raw: dict, **kw) -> dict:
    return build_watch_payload(raw, as_of=AS_OF, generated_at=GENERATED, **kw)


def _by_kind(payload: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for item in payload["items"]:
        out.setdefault(item["kind"], []).append(item)
    return out


# --- SIG-WATCH-D01: the fixture acceptance ---------------------------------- #


def _fixture_claims() -> list[tuple]:
    """The D01 fixture spine: one contract per contract rule + one subject per
    other §5.2 family, each carrying exactly the claims its rule fires on."""
    return [
        # contract — auto-renews with a 90-day notice window → renewal_deadline
        # at end − 90d (derived, SIG-UI-014b; date asserted below).
        _claim(
            "c1-end",
            "contract:test:tenant:t1:C-100",
            "end_date",
            value_text="2027-06-30",  # future-ok: synthetic: SIG-UI-014b fixture
        ),
        _claim("c1-auto", "contract:test:tenant:t1:C-100", "auto_renews", value_bool=True),
        _claim("c1-win", "contract:test:tenant:t1:C-100", "notice_window_days", value_num=90),
        _claim("c1-buy", "contract:test:tenant:t1:C-100", "buyer", value_text="City of Test"),
        # contract — end date, renewal terms not on record → contract_expiry,
        # upper_bound (never a deadline).
        _claim(
            "c2-end",
            "contract:test:tenant:t1:C-200",
            "end_date",
            value_text="2027-01-31",  # future-ok: synthetic: SIG-UI-014b fixture
        ),
        _claim("c2-buy", "contract:test:tenant:t1:C-200", "buyer", value_text="City of Test"),
        # procurement notice — response deadline + a reviewed term match.
        _claim(
            "n1-dl",
            "procurement_notice:sam_gov:fed:N-9",
            "response_deadline",
            value_text="2026-10-15",
            source_id="sam_gov",
        ),
        _claim(
            "n1-mk",
            "procurement_notice:sam_gov:fed:N-9",
            "matched_keyword",
            value_text="alpr",
            source_id="sam_gov",
        ),
        _claim(
            "n1-buy",
            "procurement_notice:sam_gov:fed:N-9",
            "buyer",
            value_text="CBP",
            source_id="sam_gov",
        ),
        # agenda item — reviewed content_term + the (WX-02) meeting_date claim.
        _claim(
            "a1-term",
            "agenda_item:legistar:seattle_wa:CB-1",
            "content_term",
            value_text="contract_notice",
        ),
        _claim(
            "a1-meet",
            "agenda_item:legistar:seattle_wa:CB-1",
            "meeting_date",
            value_text="2026-10-06",
        ),
        # bill — surveillance-matched, latest status date.
        _claim(
            "b1-mk",
            "legislative_bill:openstates:tx:HB-1",
            "bill_matched_keyword",
            value_text="alpr",
            source_id="openstates",
        ),
        _claim(
            "b1-sd",
            "legislative_bill:openstates:tx:HB-1",
            "bill_status_date",
            value_text="2026-09-10",
            source_id="openstates",
        ),
        _claim(
            "b1-st",
            "legislative_bill:openstates:tx:HB-1",
            "bill_status",
            value_text="passed_lower",
            source_id="openstates",
        ),
        # grant — period end + a reviewed match.
        _claim(
            "g1-per",
            "funding_instrument:usaspending:G-1",
            "period",
            value_json={
                "start": "2025-10-01",
                "end": "2026-12-31",  # future-ok: synthetic: grant period fixture
            },
            source_id="usaspending",
        ),
        _claim(
            "g1-mk",
            "funding_instrument:usaspending:G-1",
            "matched_keyword",
            value_text="flock_safety",
            source_id="usaspending",
        ),
    ]


def test_fixture_spine_derives_the_six_kind_rules() -> None:
    """SIG-WATCH-D01 — the producer emits an item per rule whose inputs exist,
    with the rule's date and certainty (the WX-02 predicates ride the fixture
    so a landed spine exercises the same code the real one will)."""
    payload = _payload({"watch_claims": _fixture_claims()})
    assert payload["schema"] == SCHEMA_WATCH
    kinds = _by_kind(payload)
    assert set(kinds) == {
        "renewal_deadline",
        "contract_expiry",
        "solicitation_deadline",
        "agenda_item",
        "legislative_action",
        "grant_period_end",
    }
    renewal = kinds["renewal_deadline"][0]
    assert renewal["schema"] == SCHEMA_WATCH_ITEM
    assert renewal["date"] == "2027-04-01"  # end − 90d; future-ok: synthetic: SIG-UI-014b fixture
    assert renewal["date_certainty"] == "derived"
    assert renewal["date_kind"] == "notice_deadline"
    assert renewal["termination"] == {
        "expiry_date": "2027-06-30",
        "auto_renews": True,
        "notice_window_days": 90,
    }
    expiry = kinds["contract_expiry"][0]
    assert expiry["date"] == "2027-01-31"  # future-ok: synthetic: SIG-UI-014b fixture
    assert expiry["date_certainty"] == "upper_bound"
    assert expiry["date_kind"] == "expiry"
    assert "deadline" not in expiry["title"].lower()
    assert "latest possible end" in expiry["title"]
    sol = kinds["solicitation_deadline"][0]
    assert sol["date"] == "2026-10-15"
    assert sol["date_certainty"] == "stated"
    assert sol["date_kind"] == "response_deadline"
    agenda = kinds["agenda_item"][0]
    assert agenda["date"] == "2026-10-06"
    assert agenda["date_kind"] == "meeting"
    bill = kinds["legislative_action"][0]
    assert bill["date"] == "2026-09-10"
    assert bill["date_kind"] == "status_change"
    assert bill["status"] == "recently_decided"  # within the 30-day window
    grant = kinds["grant_period_end"][0]
    assert grant["date"] == "2026-12-31"  # future-ok: synthetic: grant period fixture
    assert grant["date_certainty"] == "stated"


def test_items_carry_the_watch_item_fields() -> None:
    payload = _payload({"watch_claims": _fixture_claims()})
    required = {
        "schema",
        "handle",
        "title",
        "kind",
        "date",
        "date_kind",
        "date_certainty",
        "timeline",
        "place",
        "subjects",
        "technology",
        "vendor",
        "status",
        "what_you_can_do",
        "evidence",
        "contested",
        "tasks",
        "first_seen",
        "last_checked",
        "source_ids",
    }
    for item in payload["items"]:
        assert required <= set(item), item["handle"]
        assert item["schema"] == SCHEMA_WATCH_ITEM
        assert item["what_you_can_do"]  # procedural text, never empty
        assert item["last_checked"] == GENERATED
        assert item["first_seen"] == "2026-09-01"
        assert item["source_ids"]


def test_vendor_and_technology_facets_come_from_the_reviewed_vocab() -> None:
    payload = _payload({"watch_claims": _fixture_claims()})
    grant = _by_kind(payload)["grant_period_end"][0]
    assert grant["vendor"] == [{"id": "flock_safety", "label": "Flock Safety"}]
    sol = _by_kind(payload)["solicitation_deadline"][0]
    assert sol["technology"] == [{"id": "alpr", "label": "automated license plate reader"}]


# --- honesty invariants ------------------------------------------------------ #


def test_no_item_without_its_firing_claims() -> None:
    """A kind whose firing predicates are absent emits nothing — never a
    synthetic. An agenda item with a content_term but no meeting_date claim is
    honest zero (the WX-02 predicate's absence is the real spine state)."""
    payload = _payload(
        {
            "watch_claims": [
                _claim("a1", "agenda_item:legistar:t:X-1", "content_term", value_text="alpr"),
                _claim("n1", "procurement_notice:sam_gov:t:N-1", "buyer", value_text="CBP"),
            ]
        }
    )
    assert payload["items"] == []
    assert payload["coverage"]["items_total"] == 0


def test_contract_expiry_without_end_date_emits_nothing() -> None:
    payload = _payload(
        {"watch_claims": [_claim("c", "contract:test:t:X", "buyer", value_text="City")]}
    )
    assert payload["items"] == []


def test_explicit_non_renewal_is_a_stated_end_not_an_upper_bound() -> None:
    """``auto_renews: false`` IS a recorded renewal term — the end date is the
    stated end; unknown terms (absent claims) keep ``upper_bound``."""
    payload = _payload(
        {
            "watch_claims": [
                _claim(
                    "c1",
                    "contract:test:t:K",
                    "end_date",
                    value_text="2027-05-01",  # future-ok: synthetic: contract window fixture
                ),
                _claim("c2", "contract:test:t:K", "auto_renews", value_bool=False),
            ]
        }
    )
    item = payload["items"][0]
    assert item["kind"] == "contract_expiry"
    assert item["date_certainty"] == "stated"


def test_the_twelve_month_contract_window() -> None:
    """Contract kinds list from 12 months ahead only — an expiry past the
    horizon stays off the default list (K7 §5.2 windows, pending D-K7-4)."""
    far = _payload(
        {
            "watch_claims": [
                _claim(
                    "c1",
                    "contract:test:t:F",
                    "end_date",
                    value_text="2028-10-01",  # future-ok: synthetic: past-horizon fixture
                ),
            ]
        }
    )
    assert far["items"] == []
    near = _payload(
        {
            "watch_claims": [
                _claim(
                    "c1",
                    "contract:test:t:N",
                    "end_date",
                    value_text="2027-08-01",  # future-ok: synthetic: in-window fixture
                ),
            ]
        }
    )
    assert [i["kind"] for i in near["items"]] == ["contract_expiry"]


def test_items_drop_30_days_after_their_date() -> None:
    payload = _payload(
        {
            "watch_claims": [
                _claim(
                    "b1",
                    "legislative_bill:openstates:t:B",
                    "bill_matched_keyword",
                    value_text="alpr",
                ),
                _claim(
                    "b2",
                    "legislative_bill:openstates:t:B",
                    "bill_status_date",
                    value_text="2026-08-01",
                ),
            ]
        }
    )
    assert payload["items"] == []  # 2026-08-01 is >30 days before 2026-09-22


def test_status_words() -> None:
    claims = [
        _claim(
            "t1", "legislative_bill:openstates:t:TODAY", "bill_matched_keyword", value_text="alpr"
        ),
        _claim(
            "t2", "legislative_bill:openstates:t:TODAY", "bill_status_date", value_text="2026-09-22"
        ),
        _claim("u1", "legislative_bill:openstates:t:UP", "bill_matched_keyword", value_text="alpr"),
        _claim(
            "u2", "legislative_bill:openstates:t:UP", "bill_status_date", value_text="2026-10-01"
        ),
    ]
    payload = _payload({"watch_claims": claims})
    by_subj = {i["subjects"][0]: i for i in payload["items"]}
    assert by_subj["legislative_bill:openstates:t:TODAY"]["status"] == "today"
    assert by_subj["legislative_bill:openstates:t:UP"]["status"] == "upcoming"


def test_handles_are_deterministic_and_collision_safe() -> None:
    a = _payload({"watch_claims": _fixture_claims()})
    b = _payload({"watch_claims": _fixture_claims()})
    assert [i["handle"] for i in a["items"]] == [i["handle"] for i in b["items"]]
    handles = [i["handle"] for i in a["items"]]
    assert len(handles) == len(set(handles))
    for h in handles:
        assert h.startswith("W-")
        assert "-unplaced-" not in h or h.split("-")[1] == "unplaced"


def test_items_sort_by_date_then_handle() -> None:
    payload = _payload({"watch_claims": _fixture_claims()})
    keys = [(i["date"], i["handle"]) for i in payload["items"]]
    assert keys == sorted(keys)


# --- placement (K7 §5.3) ----------------------------------------------------- #


def test_unplaced_without_a_placement_engine() -> None:
    """No engine → ``unplaced`` — never a guessed jurisdiction."""
    payload = _payload({"watch_claims": _fixture_claims()})
    for item in payload["items"]:
        assert item["place"]["key"] is None
        assert item["place"]["check"] == "unplaced"


def test_federal_floor_places_federal_sources_under_us() -> None:
    """K7 §5.3 — a federal publisher's notice with no finer declaration sits
    under iso3166-1:US (the federal floor is declared inference, recorded on
    the item's placement fields, not a guessed city)."""
    claims = [
        _claim(
            "n1",
            "procurement_notice:sam_gov:fed:N-1",
            "response_deadline",
            value_text="2026-10-15",
            source_id="sam_gov",
        ),
        _claim(
            "n2",
            "procurement_notice:sam_gov:fed:N-1",
            "matched_keyword",
            value_text="alpr",
            source_id="sam_gov",
        ),
    ]
    payload = _payload({"watch_claims": claims})
    item = payload["items"][0]
    # Without an engine the floor input still can't resolve — placement is the
    # engine's job; the producer only supplies the declared (iso, US) pair.
    assert item["place"]["key"] is None
    pi = _placement_input(
        "procurement_notice:sam_gov:fed:N-1",
        _normalized_claims({"watch_claims": claims}),
        "h",
    )
    assert pi.declared == ("iso.3166_1_alpha2", "US")


# --- evidence anchors + the gated upstream ----------------------------------- #


def _binding(claim_id: str, artifact_id: str, artifact_source_id: str = "src_a") -> tuple:
    """A ``claim_binding_detail`` row in BINDING_DETAIL_COLUMNS order."""
    cols = dict.fromkeys(BINDING_DETAIL_COLUMNS)
    cols.update(
        claim_id=claim_id,
        capture_id="cap-1",
        artifact_id=artifact_id,
        role="supports",
        binding_status="bound",
        artifact_source_id=artifact_source_id,
    )
    return tuple(cols[c] for c in BINDING_DETAIL_COLUMNS)


def test_evidence_links_carry_claim_artifact_and_the_gated_upstream() -> None:
    claims = [
        _claim(
            "c1",
            "contract:test:t:E",
            "end_date",
            value_text="2027-01-31",  # future-ok: synthetic: contract expiry fixture
        ),
    ]
    raw = {
        "watch_claims": claims,
        "claim_binding_detail": [_binding("c1", "art-1", "src_a")],
        # evidence_artifacts positional rows: index 0 artifact_id, 10 upstream_url
        # (the rights-gated link — the binding's raw ea.url is never a fallback).
        "evidence_artifacts": [
            (
                "art-1",
                "src_a",
                "Contract PDF",
                "contract",
                "https://x/1",
                "primary",
                "captured",
                "2026",
                "Source A",
                "document",
                "https://sam.gov/opp/1",
            ),
        ],
    }
    lane = {"src_a": {"decision": LaneDecision("raw-ok"), "p8": None}}
    payload = _payload(raw, lane_by_source=lane)
    ev = payload["items"][0]["evidence"][0]
    assert ev["claim_id"] == "c1"
    assert ev["artifact_ids"] == ["art-1"]
    assert ev["upstream"]["status"] == "full_url"
    assert ev["upstream"]["url"] == "https://sam.gov/opp/1"


def test_an_ungated_artifact_url_never_leaks() -> None:
    """The binding detail carries the raw ``ea.url`` — but only the
    rights-gated ``evidence_artifacts.upstream_url`` may leave the artifact.
    Absent from the gated read → ``no_upstream_url_recorded``."""
    raw = {
        "watch_claims": [
            _claim(
                "c1",
                "contract:test:t:E",
                "end_date",
                value_text="2027-01-31",  # future-ok: synthetic: contract expiry fixture
            )
        ],
        "claim_binding_detail": [_binding("c1", "art-1", "src_a")],
        "evidence_artifacts": [],  # the gated read withheld the link
    }
    payload = _payload(raw, lane_by_source={"src_a": {"decision": LaneDecision("raw-ok")}})
    assert payload["items"][0]["evidence"][0]["upstream"]["status"] == "no_upstream_url_recorded"


# --- coverage + the honest empty state --------------------------------------- #


def test_empty_watch_still_carries_coverage() -> None:
    payload = _payload(
        {},
        dossier_places=[
            {"key": "iso3166-2:US-OK", "slug": "iso3166-2-us-ok"},
            {"key": "unresolved", "slug": "unresolved"},
        ],
    )
    assert payload["schema"] == SCHEMA_WATCH
    assert payload["items"] == []
    cov = payload["coverage"]
    assert cov["items_total"] == 0
    assert {p["key"] for p in cov["places"]} == {"iso3166-2:US-OK", "unresolved"}
    assert all(p["items"] == 0 for p in cov["places"])
    assert cov["by_kind"] == {k: 0 for k in WATCH_KINDS}
    assert cov["last_checked"] == GENERATED


def test_coverage_counts_items_per_dossier_place_and_kind() -> None:
    payload = _payload(
        {"watch_claims": _fixture_claims()},
        dossier_places=[{"key": "iso3166-2:US-OK", "slug": "iso3166-2-us-ok"}],
    )
    cov = payload["coverage"]
    assert cov["items_total"] == len(payload["items"])
    assert cov["by_kind"]["renewal_deadline"] == 1
    assert cov["by_kind"]["grant_period_end"] == 1


def test_the_sizing_count_surfaces_in_coverage() -> None:
    """The read-only ``watch_subject_counts`` rows land in ``coverage.sizing``
    — the emission's footprint under the same gates the producer read."""
    payload = _payload(
        {
            "watch_claims": _fixture_claims(),
            "watch_subject_counts": [
                ("contract", 2, 7),
                ("procurement_notice", 1, 3),
            ],
        }
    )
    assert payload["coverage"]["sizing"] == {
        "contract": {"subjects": 2, "claims": 7},
        "procurement_notice": {"subjects": 1, "claims": 3},
    }


# --- supersession / withdrawal / tasks / contested ---------------------------- #


def test_a_retracted_firing_claim_marks_the_item_withdrawn() -> None:
    claims = [
        _claim("b1", "legislative_bill:openstates:t:B", "bill_matched_keyword", value_text="alpr"),
        _claim(
            "b2", "legislative_bill:openstates:t:B", "bill_status_date", value_text="2026-09-10"
        ),
        # A newer retraction naming the status-date claim → the item reads
        # ``withdrawn`` (the spine row stays; the surface marks it).
        _claim(
            "b3",
            "legislative_bill:openstates:t:B",
            "bill_status_date",
            value_text="2026-09-10",
            retraction_of="b2",
            recorded_at="2026-09-15T00:00:00+00",
        ),
    ]
    payload = _payload({"watch_claims": claims})
    item = payload["items"][0]
    assert item["status"] == "withdrawn"


def test_open_research_tasks_link_to_the_item() -> None:
    claims = [
        _claim(
            "c1",
            "contract:test:t:Q",
            "end_date",
            value_text="2027-01-31",  # future-ok: synthetic: contract expiry fixture
        ),
    ]
    raw = {
        "watch_claims": claims,
        "research_tasks": [
            (
                "task-1",
                "contract_expiring",
                "ent-contract:test:t:Q",
                "jur",
                1.0,
                "open",
                "open",
                "renewal terms recorded",
                "det/1",
                None,
                None,
            ),
        ],
    }
    payload = _payload(raw)
    item = payload["items"][0]
    assert item["tasks"] == [
        {"task_id": "task-1", "task_type": "contract_expiring", "status": "open"}
    ]


def test_contested_when_a_materialized_contradiction_names_a_claim() -> None:
    claims = [
        _claim(
            "c1",
            "contract:test:t:R",
            "end_date",
            value_text="2027-01-31",  # future-ok: synthetic: contract expiry fixture
        ),
    ]
    raw = {
        "watch_claims": claims,
        "materialized_contradictions": [
            {"subject_id": "ent-contract:test:t:R", "claim_ids": ["c1", "cx"]},
        ],
    }
    payload = _payload(raw)
    assert payload["items"][0]["contested"] is True


def test_a_later_revision_drives_the_item_date() -> None:
    """Append-only semantics: a revising claim (the newer row, never an update)
    wins the derivation — the item's date follows the corrected value."""
    claims = [
        _claim("b1", "legislative_bill:openstates:t:B", "bill_matched_keyword", value_text="alpr"),
        _claim(
            "b2", "legislative_bill:openstates:t:B", "bill_status_date", value_text="2026-09-10"
        ),
        _claim(
            "b3",
            "legislative_bill:openstates:t:B",
            "bill_status_date",
            value_text="2026-09-18",
            revises_claim="b2",
            recorded_at="2026-09-19T00:00:00+00",
        ),
    ]
    payload = _payload({"watch_claims": claims})
    item = payload["items"][0]
    assert item["date"] == "2026-09-18"
    assert item["status"] == "recently_decided"


# --- the envelope ------------------------------------------------------------ #


def test_the_envelope_declares_its_windows_basis() -> None:
    payload = _payload({"watch_claims": []})
    assert payload["schema"] == SCHEMA_WATCH
    build = payload["build"]
    assert build["windows"]["contract_horizon_days"] == 365
    assert build["windows"]["recently_decided_days"] == 30
    assert build["windows"]["list_days"] == 90
    assert "D-K7-4" in build["windows"]["basis"]
    assert "agent-drafted" in build["what_you_can_do_basis"]


def test_generated_at_and_as_of() -> None:
    payload = _payload({"watch_claims": []})
    assert payload["as_of"] == "2026-09-22"
    assert payload["generated_at"] == GENERATED
