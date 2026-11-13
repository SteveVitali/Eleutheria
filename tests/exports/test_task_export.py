# SPDX-License-Identifier: Apache-2.0
"""P36.58 (R11-K13-RQ-01): task export v2 — handles/titles (SIG-RQ-001),
real card metadata (SIG-RQ-003), the predicate table + named predicates
(SIG-RQ-005), campaign aggregation (SIG-RQ-006), lane/place shards and
queue_meta v2.
"""

from __future__ import annotations

import gzip
import json

from exports.task_export import (
    CAMPAIGN_SCHEMA,
    HANDLE_MAX,
    build_queue,
    handle_slug,
    mint_handle,
    place_segment,
)
from tasks.routing import load_gap_routing, load_task_codes

CODES = load_task_codes()
ROUTES = load_gap_routing()


def _card(**over):
    base = {
        "task_id": "t1",
        "task_type": "missing_contract",
        "subject_id": "subjX",
        "subject_label": "subjX",
        "closing_condition": "closing",
        "evidence_sought": "missing_contract",
        "assignee_class": "records_requester",
        "effort_estimate": "substantial",
        "geographic_scope": "jurisdiction",
        "jurisdiction": "",
        "dispositions": ["resolved_evidence_found"],
        "priority": 0.5,
        "status": "generated",
        "detector_version": "det/1",
    }
    base.update(over)
    return base


def _build(cards, raw=None, **kw):
    return build_queue(
        cards,
        raw if raw is not None else {},
        label_registry=kw.pop("label_registry", {}),
        keyed=kw.pop("keyed", None),
        slug_map=kw.pop("slug_map", {}),
        leaf_by_subject=kw.pop("leaf_by_subject", {}),
        routing=ROUTES,
        codes=CODES,
        generated_at="2026-11-03T00:00:00Z",
        **kw,
    )


def _coverage(cid, **over):
    row = {
        "coverage_id": cid,
        "subject_id": "subjX",
        "subject_class": "deployment",
        "jurisdiction_id": None,
        "predicate_id": "seller",
        "absence_kind": "not_researched",
        "sources_searched": [],
        "searched_at": None,
    }
    row.update(over)
    return row


# --- handle grammar (SIG-RQ-001) --------------------------------------------- #


def test_handle_slug_abbreviates_and_drops_place_tail() -> None:
    assert handle_slug("Acworth Police Department", "usa-ga-acworth") == "pd"
    assert handle_slug("Travis County Sheriff's Office", "usa-tx-travis-county") == "travis-so"
    assert handle_slug("Oklahoma City Police Department", "usa-ok-oklahoma-city") == ("oklahoma-pd")
    assert handle_slug("Acworth Police Department", "usa-ga") == "acworth-pd"


def test_handle_slug_ascii_folds_and_cuts() -> None:
    slug = handle_slug("Département de la Sûreté du Québec Long Name Here", "can-qc")
    assert slug is not None and len(slug) <= 24 and " " not in slug
    assert handle_slug("!!!", "usa") is None


def test_mint_handle_shape_and_length_cap() -> None:
    h = mint_handle("T", "usa-ga-acworth", "share", "pd", "task-uuid-1")
    assert h.startswith("T-usa-ga-acworth-share-pd-")
    assert len(h) <= HANDLE_MAX
    # no slug → the segment is omitted, not doubled-up
    assert mint_handle("T", "usa-ok", "retention", None, "x").startswith("T-usa-ok-retention-")


def test_place_segment_unplaced_without_keyed() -> None:
    assert place_segment("iso3166-2:US-GA", None) == "unplaced"
    assert place_segment(None, None) == "unplaced"


# --- card v2 fields ----------------------------------------------------------- #


def test_card_carries_named_predicate_and_trigger_detail() -> None:
    raw = {"materialized_coverage": [_coverage("cov1")]}
    b = _build([_card(trigger={"kind": "coverage", "ref": "cov1"})], raw)
    card = b.cards[0]
    assert card["predicate_ids"] == ["seller"]
    detail = card["trigger"]["detail"]
    assert detail["predicate_id"] == "seller"
    assert detail["absence_kind"] == "not_researched"


def test_card_without_resolvable_trigger_names_no_predicates() -> None:
    b = _build([_card(trigger={"kind": "coverage", "ref": "missing"})])
    card = b.cards[0]
    assert card["predicate_ids"] == []
    assert card["trigger"]["detail"] == {"resolves": False}


def test_card_carries_handle_title_status_and_state() -> None:
    b = _build([_card()])
    card = b.cards[0]
    assert card["handle"].startswith("T-")
    assert card["handle"].count("-") >= 4
    assert card["title"]
    assert card["status"] == "generated"
    assert card["detector_version"] == "det/1"
    assert card["lane"] == "research"
    assert card["place"]["slug"] == "unplaced"


def test_subject_label_never_a_raw_uuid() -> None:
    uuid_subject = "01a0a720-9b9a-7890-a8ae-99705e6b5368"
    b = _build([_card(subject_id=uuid_subject)])
    card = b.cards[0]
    assert uuid_subject not in card["subject_label"]
    assert card["subject_label"].startswith("Record #")


def test_label_registry_supplies_label_and_url() -> None:
    from policy.labels import EntityLabel

    lbl = EntityLabel(
        entity_id="e1",
        sig_id=None,
        kind="agency",
        url_type="agency",
        label="Acworth Police Department",
        descriptor="Acworth Police Department · Government body",
        label_basis="source_name",
        label_source_id=None,
        place_jkey="us.census.geoid.place:1300500",
        slug="acworth-police-department",
        hash="abc1234",
        url="/entity/agency/acworth-police-department--abc1234/",
        disambiguator=None,
        component_id=None,
        part8="pass",
    )
    b = _build([_card(subject_id="e1")], label_registry={"e1": lbl})
    card = b.cards[0]
    assert card["subject_label"] == "Acworth Police Department"
    assert card["subject_url"].endswith("--abc1234/")
    assert card["place_basis"] == "subject_place"
    assert card["jurisdiction"] == "us.census.geoid.place:1300500"


# --- lanes: campaigns + metric-only (SIG-RQ-006) ------------------------------ #


def test_osm_field_gap_aggregates_to_a_campaign() -> None:
    raw = {
        "materialized_coverage": [
            _coverage("c1", predicate_id="brand", subject_id="cam1"),
            _coverage("c2", predicate_id="brand", subject_id="cam2"),
            _coverage("c3", predicate_id="camera_mount", subject_id="cam3"),
        ]
    }
    cards = [
        _card(
            task_id="t1",
            task_type="coverage_hole",
            subject_id="cam1",
            trigger={"kind": "coverage", "ref": "c1"},
        ),
        _card(
            task_id="t2",
            task_type="coverage_hole",
            subject_id="cam2",
            trigger={"kind": "coverage", "ref": "c2"},
        ),
        _card(
            task_id="t3",
            task_type="coverage_hole",
            subject_id="cam3",
            trigger={"kind": "coverage", "ref": "c3"},
        ),
    ]
    b = _build(cards, raw)
    assert b.cards == [], "per-object field gaps are not individual research tasks"
    assert len(b.campaigns) == 2
    brand = next(c for c in b.campaigns if c["predicate_id"] == "brand")
    assert brand["schema"] == CAMPAIGN_SCHEMA
    assert brand["member_count"] == 2
    assert {m["subject_id"] for m in brand["members"]} == {"cam1", "cam2"}
    assert brand["handle"].startswith("M-unplaced-brand-")


def test_registry_field_gap_stays_out_of_the_queue() -> None:
    raw = {"materialized_coverage": [_coverage("c1", predicate_id="camera_operator")]}
    b = _build([_card(trigger={"kind": "coverage", "ref": "c1"})], raw)
    assert b.cards == [] and b.campaigns == []
    assert b.metric_members == 1


def test_agency_gap_stays_a_research_task() -> None:
    raw = {"materialized_coverage": [_coverage("c1", predicate_id="seller")]}
    b = _build([_card(trigger={"kind": "coverage", "ref": "c1"})], raw)
    assert len(b.cards) == 1
    assert b.campaigns == [] and b.metric_members == 0


def test_contradiction_trigger_stays_research_with_detail() -> None:
    raw = {
        "materialized_contradictions": [
            {
                "contradiction_id": "cd1",
                "subject_id": "subjX",
                "predicate_id": "configured_retention_days",
                "contradiction_type": "value_disagreement",
                "status": "open",
                "severity": "notable",
                "claim_ids": ["a", "b"],
            }
        ]
    }
    b = _build(
        [_card(task_type="conflicting_retention", trigger={"kind": "contradiction", "ref": "cd1"})],
        raw,
    )
    card = b.cards[0]
    assert card["predicate_ids"] == ["configured_retention_days"]
    assert card["trigger"]["detail"]["contradiction_type"] == "value_disagreement"
    assert card["handle"].startswith("T-unplaced-retention-")


# --- shards + handles_history + meta ------------------------------------------ #


def test_shards_are_deterministic_jsonl_gz() -> None:
    b = _build([_card()])
    assert len(b.shards) == 1
    path, blob = next(iter(b.shards.items()))
    assert path == "web/tasks/research/unplaced.jsonl.gz"
    rows = [json.loads(line) for line in gzip.decompress(blob).decode().splitlines() if line]
    assert rows[0]["task_id"] == "t1"
    b2 = _build([_card()])
    assert b2.shards[path] == blob, "shard bytes must be deterministic"


def test_handles_history_carries_id_aliases() -> None:
    b = _build([_card()])
    hh = b.handles_history
    assert hh["family"] == "task"
    assert len(hh["rows"]) == 1
    row = hh["rows"][0]
    assert row["old"] == "/task/t1/"
    assert row["target"] == f"/task/{b.cards[0]['handle']}/"


def test_queue_meta_summary_counts() -> None:
    raw = {"materialized_coverage": [_coverage("c1", predicate_id="brand", subject_id="cam1")]}
    b = _build(
        [
            _card(task_id="t1"),
            _card(
                task_id="t2",
                subject_id="cam1",
                task_type="coverage_hole",
                trigger={"kind": "coverage", "ref": "c1"},
            ),
        ],
        raw,
    )
    s = b.summary
    assert s["lanes"]["research"] == 1
    assert s["lanes"]["campaigns"] == 1
    assert s["lanes"]["campaign_members"] == 1
    assert s["tasks_by_type"]["missing_contract"] == 1
    assert s["card_schema"] == "sig.queue-card/2"
    assert s["handle_grammar"] == "k11-handle/1"
    assert any(sh["lane"] == "research" for sh in s["shards"])
    assert any(sh["lane"] == "campaign" for sh in s["shards"])


def test_hash_collision_extends() -> None:
    """Two handles colliding at hash-4 separate at 5..8 (deterministic)."""
    from exports.task_export import resolve_handle_hashes

    # find two ids that collide at length 4
    from policy.labels import entity_hash

    a, seen = 0, {}
    pair = None
    while pair is None:
        i = f"id-{a}"
        h = entity_hash(i, length=4)
        if h in seen:
            pair = (seen[h], i)
            break
        seen[h] = i
        a += 1
        assert a < 200_000
    entries = [
        {
            "_kind": "T",
            "_place": "unplaced",
            "_code": "gap",
            "_slug": None,
            "_object_id": pair[0],
            "handle": "",
        },
        {
            "_kind": "T",
            "_place": "unplaced",
            "_code": "gap",
            "_slug": None,
            "_object_id": pair[1],
            "handle": "",
        },
    ]
    resolve_handle_hashes(entries)
    assert entries[0]["handle"] != entries[1]["handle"]
    assert len(entries[0]["handle"].rsplit("-", 1)[-1]) >= 5


# --- P37.32 (K7 WX-06): the task ↔ item link + the contract trigger ---------- #


def test_contract_expiring_card_links_the_emitted_watch_item() -> None:
    """K7 §5.8 — the task links to the item: a `contract_expiring` card on a
    subject with an emitted watch item carries the item's own handle (never a
    re-derived one)."""
    card = _card(
        task_type="contract_expiring",
        subject_id="ent-c1",
        trigger={"kind": "contract", "ref": "wc-end"},
    )
    item = {
        "handle": "W-us-ok-expiry-c200-77cd",
        "kind": "contract_expiry",
        "title": "City of Test: contract C-200 ends 2027-01-31",  # future-ok: synthetic: fixture
        "subjects": ["contract:test:tenant:t1:C-200"],
    }
    labels = {
        "ent-c1": type(
            "L",
            (),
            {
                "label": "Contract C-200",
                "url": None,
                "subject_key": "contract:test:tenant:t1:C-200",
                "place_jkey": None,
                "descriptor": None,
            },
        )()
    }
    out = _build(
        [card],
        raw={},
        label_registry=labels,
        watch_items_by_subject={"contract:test:tenant:t1:C-200": [item]},
    )
    [built] = out.cards
    assert built["watch_items"] == [
        {
            "handle": "W-us-ok-expiry-c200-77cd",
            "kind": "contract_expiry",
            "title": item["title"],
        }
    ]


def test_card_without_a_matching_item_carries_no_watch_items() -> None:
    out = _build(
        [_card(task_type="contract_expiring", subject_id="ent-c9")],
        raw={},
        watch_items_by_subject={"contract:other:x": [{"handle": "W-x"}]},
    )
    assert "watch_items" not in out.cards[0]


def test_contract_trigger_resolves_the_firing_end_date_claim() -> None:
    """The `contract` trigger names the recorded end the task asks about —
    the claim id IS the trigger ref (SIG-RQ-005's named gap)."""
    card = _card(
        task_type="contract_expiring",
        trigger={"kind": "contract", "ref": "wc-end"},
    )
    raw = {
        "watch_claims": [
            {
                "claim_id": "wc-end",
                "subject_key": "contract:test:t:C-9",
                "predicate_id": "end_date",
                "value_text": "2027-01-31",  # future-ok: synthetic: fixture contract end
                "observed_at": "2026-05-01",
                "source_id": "src_a",
            }
        ]
    }
    out = _build([card], raw=raw)
    detail = out.cards[0]["trigger"]["detail"]
    assert detail["resolves"] is True
    assert detail["end_date"] == "2027-01-31"  # future-ok: synthetic: fixture contract end
    assert detail["predicate_id"] == "end_date"
    # The K11 title template renders "… contract ending <date>".
    assert "2027-01-31" in out.cards[0]["title"]  # future-ok: synthetic: fixture contract end


def test_unresolvable_contract_trigger_is_the_honest_absence() -> None:
    card = _card(
        task_type="contract_expiring",
        trigger={"kind": "contract", "ref": "wc-missing"},
    )
    out = _build([card], raw={"watch_claims": []})
    assert out.cards[0]["trigger"]["detail"] == {"resolves": False}
