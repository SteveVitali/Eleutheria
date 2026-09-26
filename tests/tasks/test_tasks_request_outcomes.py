# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The records-request outcome log (BL-028 / D-META.1-2, P25.9).

Covers the ticket AC: the outcome-log parse over a committed MuckRock api_v2
fixture (the real request-136412 shape), the claim-row fold, the append-only
log semantics, and the explicit template-log feed (SIG-TASK-017). The live read
itself is the run's evidence — these tests pin the deterministic parse.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from support import load_schemaview
from tasks.cli import main
from tasks.records_request import TemplateOutcomeLog
from tasks.request_outcomes import (
    OUTCOME_STATES,
    InvalidOutcome,
    RequestOutcomeLog,
    feed_template_log,
    is_terminal,
    outcome_from_api_payload,
    outcome_from_claims,
    outcome_state_for,
)

FIXTURES = Path(__file__).parent / "fixtures"
MUCKROCK_136412 = FIXTURES / "muckrock_request_136412.json"

# The versioned api_v2 raw-status map the connector carries (records_vocab.toml
# [muckrock_status_map]); injected, never duplicated in the outcome module.
STATUS_MAP = {
    "submitted": "filed",
    "ack": "acknowledged",
    "processed": "acknowledged",
    "appealing": "appealed",
    "fix": "acknowledged",
    "payment": "fee_demanded",
    "lawsuit": "appealed",
    "rejected": "denied",
    "no_docs": "no_responsive_records",
    "done": "fulfilled",
    "partial": "partially_fulfilled",
    "abandoned": "abandoned",
}


def _fixture() -> dict:
    return json.loads(MUCKROCK_136412.read_text())


# --- the API-shape parse ------------------------------------------------------


def test_the_real_request_136412_payload_parses_to_a_completed_outcome() -> None:
    # The real api_v2 shape observed live 2026-09-15: `done` → fulfilled, the
    # platform agency id is carried verbatim (never resolved), and the response
    # date is the api_v2 `datetime_done` value.
    outcome = outcome_from_api_payload(
        _fixture(), status_map=STATUS_MAP, observed_at="2026-09-16T00:00:00+00:00"
    )
    assert outcome.request_id == "136412"
    assert outcome.platform == "muckrock"
    assert outcome.agency == "265"
    assert outcome.state == "completed"
    assert outcome.response_status == "fulfilled"
    assert outcome.response_date == "2022-11-30T20:10:37.860902-05:00"
    assert outcome.terminal


def test_an_in_flight_request_is_recorded_as_in_flight_never_completed() -> None:
    # No fabricated terminal state: an `ack` status is acknowledged (still
    # open), and a payload carrying no status at all folds to in_flight.
    acked = outcome_from_api_payload(
        {"id": 7, "status": "ack", "agency": 265}, status_map=STATUS_MAP
    )
    assert acked.state == "acknowledged"
    assert not acked.terminal
    empty = outcome_from_api_payload({"id": 8, "agency": 265}, status_map=STATUS_MAP)
    assert empty.state == "in_flight"
    filed = outcome_from_api_payload(
        {"id": 9, "status": "submitted", "date_submitted": "2026-09-01"},
        status_map=STATUS_MAP,
    )
    assert filed.state == "filed"
    assert filed.filed_date == "2026-09-01"


def test_an_unmapped_platform_status_fails_loud() -> None:
    # A raw status outside the versioned map AND the §11.19 vocabulary is
    # recorded drift, never a silent coerce.
    with pytest.raises(InvalidOutcome):
        outcome_from_api_payload({"id": 1, "status": "brand_new_status"}, status_map=STATUS_MAP)


def test_a_payload_without_a_request_id_is_refused() -> None:
    with pytest.raises(InvalidOutcome):
        outcome_from_api_payload({"status": "done"}, status_map=STATUS_MAP)


# --- the claim-row fold (spine / connector shapes) ----------------------------


def test_spine_claim_rows_fold_to_the_same_outcome() -> None:
    # The spine's 136412 claims (predicate_id + value_text, as PgClaimSink wrote
    # them on 2026-09-15) fold to the identical outcome the API payload gives.
    claims = [
        {"predicate_id": "external_id", "value_text": "136412"},
        {"predicate_id": "target_agency", "value_text": "265"},
        {"predicate_id": "requesting_party", "value_text": "3647"},
        {"predicate_id": "response_status", "value_text": "fulfilled"},
        {"predicate_id": "response_date", "value_text": "2022-11-30T20:10:37.860902-05:00"},
    ]
    outcome = outcome_from_claims(claims, observed_at="2026-09-16T00:00:00+00:00")
    api = outcome_from_api_payload(
        _fixture(), status_map=STATUS_MAP, observed_at="2026-09-16T00:00:00+00:00"
    )
    assert outcome.key == api.key
    assert outcome.state == api.state == "completed"
    assert outcome.response_status == "fulfilled"
    assert outcome.agency == "265"
    assert outcome.source == "claim_spine"


def test_claims_without_a_status_fold_to_filed_or_in_flight() -> None:
    filed = outcome_from_claims(
        [
            {"predicate_id": "external_id", "value": "5"},
            {"predicate_id": "filed_date", "value": "2026-09-01"},
        ]
    )
    assert filed.state == "filed"
    unknown = outcome_from_claims([{"predicate_id": "external_id", "value": "6"}])
    assert unknown.state == "in_flight"


def test_claims_without_an_external_id_are_refused() -> None:
    with pytest.raises(InvalidOutcome):
        outcome_from_claims([{"predicate_id": "response_status", "value": "fulfilled"}])


# --- the append-only log -------------------------------------------------------


def test_the_log_is_append_only_and_latest_folds(tmp_path: Path) -> None:
    log = RequestOutcomeLog(tmp_path / "outcomes.jsonl")
    first = log.record(
        outcome_from_api_payload(
            {"id": 136412, "status": "ack", "agency": 265},
            status_map=STATUS_MAP,
            observed_at="2026-09-10T00:00:00+00:00",
        )
    )
    second = log.record(
        outcome_from_api_payload(
            _fixture(), status_map=STATUS_MAP, observed_at="2026-09-16T00:00:00+00:00"
        )
    )
    # Both observations stay in the history; the folded view shows the newest.
    assert [o.state for o in log.read_all()] == ["acknowledged", "completed"]
    assert log.latest()["muckrock:136412"] == second
    assert log.latest()["muckrock:136412"] != first
    # A third observation appends; nothing is rewritten.
    lines_before = (tmp_path / "outcomes.jsonl").read_text()
    log.record(first)
    after = (tmp_path / "outcomes.jsonl").read_text()
    assert after.startswith(lines_before)
    assert len(log.read_all()) == 3


def test_log_rows_round_trip(tmp_path: Path) -> None:
    log = RequestOutcomeLog(tmp_path / "o.jsonl")
    outcome = outcome_from_api_payload(
        _fixture(), status_map=STATUS_MAP, observed_at="2026-09-16T00:00:00+00:00"
    )
    log.record(outcome)
    assert log.read_all() == [outcome]
    row = json.loads((tmp_path / "o.jsonl").read_text().strip())
    assert row["outcomes_version"]  # the row is self-describing (§20)


# --- the template feed (SIG-TASK-017) ------------------------------------------


def test_feed_template_log_counts_terminal_outcomes_only() -> None:
    tlog = TemplateOutcomeLog()
    fulfilled = outcome_from_api_payload(
        _fixture(), status_map=STATUS_MAP, observed_at="2026-09-16T00:00:00+00:00"
    )
    assert feed_template_log(tlog, fulfilled, record_type="alpr_contract", version="v1")
    assert tlog.success_rate("alpr_contract", "v1") == 1.0
    # A denied outcome is a counted failure of the language.
    denied = outcome_from_api_payload({"id": 2, "status": "rejected"}, status_map=STATUS_MAP)
    assert feed_template_log(tlog, denied, record_type="alpr_contract", version="v1")
    assert tlog.success_rate("alpr_contract", "v1") == 0.5


def test_feed_template_log_never_counts_no_responsive_records_or_in_flight() -> None:
    tlog = TemplateOutcomeLog()
    no_docs = outcome_from_api_payload({"id": 3, "status": "no_docs"}, status_map=STATUS_MAP)
    assert no_docs.terminal  # the request closed — but the language did not fail
    assert not feed_template_log(tlog, no_docs, record_type="alpr_contract", version="v1")
    in_flight = outcome_from_api_payload({"id": 4, "status": "ack"}, status_map=STATUS_MAP)
    assert not feed_template_log(tlog, in_flight, record_type="alpr_contract", version="v1")
    assert tlog.sample_size("alpr_contract", "v1") == 0


# --- the vocabulary contract ----------------------------------------------------


def test_outcome_states_cover_every_records_response_status() -> None:
    # The status → state map is total over the frozen §11.19 enum (a new enum
    # value lands unmapped and fails loud in the parse tests).
    sv = load_schemaview()
    enum = set(sv.get_enum("RecordsResponseStatus").permissible_values)
    for status in enum:
        assert outcome_state_for(status) in OUTCOME_STATES
    assert {"filed", "acknowledged", "in_flight", "completed"} <= OUTCOME_STATES


def test_terminal_matches_the_completed_state() -> None:
    assert is_terminal("fulfilled") and is_terminal("no_responsive_records")
    assert not is_terminal("acknowledged") and not is_terminal("appealed")


# --- the CLI --------------------------------------------------------------------


def test_cli_records_a_payload_and_shows_the_fold(tmp_path: Path, capsys) -> None:
    log_path = tmp_path / "outcomes.jsonl"
    status_map = tmp_path / "map.json"
    status_map.write_text(json.dumps(STATUS_MAP))
    rc = main(
        [
            "records-outcomes",
            "record",
            "--payload",
            str(MUCKROCK_136412),
            "--status-map",
            str(status_map),
            "--log",
            str(log_path),
        ]
    )
    assert rc == 0
    assert "recorded muckrock:136412: state=completed" in capsys.readouterr().out
    rc = main(["records-outcomes", "show", "--log", str(log_path)])
    assert rc == 0
    assert "muckrock:136412: completed (fulfilled)" in capsys.readouterr().out


def test_cli_record_requires_an_input(tmp_path: Path) -> None:
    assert main(["records-outcomes", "record", "--log", str(tmp_path / "o.jsonl")]) == 2
