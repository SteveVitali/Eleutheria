# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.5 shadow diff (ADR-112): the partner entity-ref claims are additive.

The real connector stages run over the committed partner fixture set
(``tests/partner_fixtures.py``). The records WITHOUT an ``object_ref`` must be exactly
the records the connectors emitted at the P31.5 base commit — the golden digests in
``fixtures/partners/text_claim_digests.json`` were computed there, before this ticket
existed. So the text claims (and every non-claim record) are byte-for-byte unchanged,
the shadow diff is 0, and every entity-ref claim is a new, separately digested record.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pytest
from db.claim_sink import content_digest
from partner_fixtures import GOLDEN, fixture_records
from resolution.partner_identity import PARTNER_PREDICATES


def _golden() -> dict[str, list[str]]:
    return dict(json.loads(GOLDEN.read_text())["runs"])


def _split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = [r for r in rows if "object_ref" not in r]
    refs = [r for r in rows if "object_ref" in r]
    return text, refs


def test_the_text_records_are_the_base_commit_records_shadow_diff_zero() -> None:
    golden = _golden()
    records = fixture_records()
    assert set(records) == set(golden)
    for key, rows in records.items():
        text, _ = _split(rows)
        assert sorted(content_digest(r) for r in text) == golden[key], key


def test_every_entity_ref_claim_is_a_new_separately_digested_record() -> None:
    golden = {d for digests in _golden().values() for d in digests}
    for key, rows in fixture_records().items():
        text, refs = _split(rows)
        text_digests = {content_digest(r) for r in text}
        for ref in refs:
            digest = content_digest(ref)
            assert digest not in golden and digest not in text_digests, key
            # It derives from a text claim of the same subject + predicate, with the
            # same evidence locators and provenance, naming one of its parties.
            source = next(
                r
                for r in text
                if r.get("subject_id") == ref["subject_id"]
                and r.get("predicate_id") == ref["predicate_id"]
                and (
                    r.get("value") == ref["value"]
                    or (isinstance(r.get("value"), list) and ref["value"] in r["value"])
                )
            )
            skip = {"object_ref", "value", "raw_value", "claim_id", "sys_period"}
            assert {k: v for k, v in ref.items() if k not in skip} == {
                k: v for k, v in source.items() if k not in skip
            }, key
            assert ref["record_kind"] == "claim"
            assert ref["predicate_id"] in PARTNER_PREDICATES
            assert ref["object_ref"]["entity_type"] == "organization"


def test_entity_ref_claims_are_emitted_per_connector_family() -> None:
    refs = {
        key: Counter(r["predicate_id"] for r in rows if "object_ref" in r)
        for key, rows in fixture_records().items()
    }
    assert refs["procurement_contracts"] == Counter({"buyer": 2, "seller": 2})
    assert refs["usaspending_awards"] == Counter({"recipient": 1})
    assert refs["ted_eu"] == Counter({"buyer": 1})
    assert refs["dot_511_wa"] == Counter({"camera_operator": 2})
    assert refs["atlas_issue_records"] == Counter({"event_organizations": 1})
    # A DECP party is a bare SIRET: no name, so no identity decision (Part VIII).
    assert refs["decp_fr"] == Counter()


def test_ambiguous_and_person_shaped_partners_stay_text_only() -> None:
    labels = {
        r["object_ref"]["label"]
        for rows in fixture_records().values()
        for r in rows
        if "object_ref" in r
    }
    for refused in (
        "Jane Q. Public dba JQP Consulting",  # sole proprietor
        "John A. Smith",  # person-shaped
        "JOHN Q CITIZEN",  # person-shaped (USAspending recipient)
        "Jane Doe",  # person-shaped (an event's organisations list)
        "Police Department",  # generic
        "Department of Transportation",  # generic (every jurisdiction has one)
        "King County / WSDOT",  # two parties
        "20009020700016",  # a bare id
    ):
        assert refused not in labels
    assert labels == {
        "Washington State Department of Transportation",
        "WASHINGTON STATE DEPARTMENT OF TRANSPORTATION",
        "Example Traffic Camera Systems LLC",
        "City of Example Falls",
        "Polska Agencja Żeglugi Powietrznej",
    }


def test_the_partner_fixture_replay_is_deterministic() -> None:
    first = {k: [content_digest(r) for r in v] for k, v in fixture_records().items()}
    second = {k: [content_digest(r) for r in v] for k, v in fixture_records().items()}
    assert first == second


def test_the_pg_sink_factory_wires_the_production_object_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # P31.5: `make_claim_sink("pg")` builds the sink with `record_object_ref`, so a live
    # run writes the emitted entity-ref records as entity refs; a caller may override it.
    import db.claim_sink as claim_sink
    from connectors.sinks import make_claim_sink

    seen: list[dict[str, object]] = []
    monkeypatch.setattr(
        claim_sink.PgClaimSink,
        "from_dsn",
        classmethod(lambda cls, dsn, **kw: seen.append(kw) or object()),
    )
    make_claim_sink("pg", dsn="postgresql://x", connector_name="c")
    assert seen[-1]["object_resolver"] is claim_sink.record_object_ref

    def mine(_claim: object) -> None:
        return None

    make_claim_sink("pg", dsn="postgresql://x", object_resolver=mine)
    assert seen[-1]["object_resolver"] is mine


def test_the_pg_sink_factory_wires_the_resighting_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # P31.7 / ADR-R9-RESIGHT: `make_claim_sink("pg")` builds the sink with
    # `record_resightings`, so a live re-assertion links the stored claim to the
    # execution's capture; a caller may still override it.
    import db.claim_sink as claim_sink
    from connectors.sinks import make_claim_sink

    seen: list[dict[str, object]] = []
    monkeypatch.setattr(
        claim_sink.PgClaimSink,
        "from_dsn",
        classmethod(lambda cls, dsn, **kw: seen.append(kw) or object()),
    )
    make_claim_sink("pg", dsn="postgresql://x", connector_name="c")
    assert seen[-1]["on_duplicates"] is claim_sink.record_resightings

    def mine(_batch: object) -> None:
        return None

    make_claim_sink("pg", dsn="postgresql://x", on_duplicates=mine)
    assert seen[-1]["on_duplicates"] is mine
