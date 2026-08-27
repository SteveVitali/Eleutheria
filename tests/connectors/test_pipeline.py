# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector driver end-to-end: gate, isolate, record (§21.1-21.6)."""

from __future__ import annotations

import pytest
from connectors.isolation import NetworkEgressBlocked
from connectors.loader import IngestionNotPermitted
from connectors.pipeline import run, run_stage
from connectors.stages import Stage


def _targets() -> list[dict[str, str]]:
    return [{"id": "p1", "url": "https://portal.example/p1", "subject_id": "entity-1"}]


def test_full_run_produces_and_asserts_claims(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 12})})
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})

    report = run(toy_connector, ctx)

    assert len(report.claims) == 1
    assert report.claims[0]["value_num"] == 12
    assert report.asserted is True
    # SIG-INGEST-001: every stage persisted a content-addressed artifact.
    for stage in Stage:
        assert ctx.artifacts.latest(stage) is not None
    # The claim reached the sink on a live run.
    assert list(ctx.claim_sink.claims)[0]["value_num"] == 12
    # One capture was archived, content-addressed.
    assert len(report.captures) == 1
    assert ctx.captures.has(report.captures[0].digest)


def test_gate_refuses_before_any_fetch(
    make_fetcher, make_context, transport_factory, json_response, toy_connector, permitted_source
) -> None:  # type: ignore[no-untyped-def]
    import dataclasses

    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 1})})
    # Revoke the permission the fixture granted: the gate must refuse up front.
    denied = dataclasses.replace(permitted_source, ingestion_permitted=False)
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})
    ctx.source = denied

    with pytest.raises(IngestionNotPermitted):
        run(toy_connector, ctx)
    assert transport.request_log == []  # no fetch happened


def test_404_records_a_disappearance_not_an_exception(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-009/010: a 404 is a first-class event + research task, not an error.
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {}, status=404)})
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})

    report = run(toy_connector, ctx)

    assert report.claims == []
    assert len(report.disappearances) == 1
    rows = report.disappearances[0].rows()
    assert rows["event"]["capture_status"] == "link_rotted"
    assert rows["research_task"]["task_type"] == "source_disappeared"
    assert rows["research_task"]["subject_id"] == "entity-1"


def test_persistent_challenge_records_a_disappearance(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-013 + 009/010: a persistent challenge is recorded, never defeated.
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {}, status=403)})
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})

    report = run(toy_connector, ctx)

    assert report.claims == []
    assert report.disappearances[0].rows()["event"]["capture_status"] == "access_restricted"


def test_egress_after_capture_fails_the_run(
    make_fetcher, make_context, transport_factory, json_response, leaky_connector
) -> None:  # type: ignore[no-untyped-def]
    # AC: a network call after capture() fails the run.
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 1})})
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})

    with pytest.raises(NetworkEgressBlocked):
        run(leaky_connector, ctx)


def test_stages_are_separately_runnable_and_idempotent(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-001/003: a single stage runs on its own and is idempotent.
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 7})})
    ctx = make_context(fetcher=make_fetcher(transport), parameters={"targets": _targets()})

    targets = run_stage(toy_connector, ctx, Stage.DISCOVER)
    fetched = run_stage(toy_connector, ctx, Stage.FETCH, targets[0])
    capture = run_stage(toy_connector, ctx, Stage.CAPTURE, fetched)
    parsed_a = run_stage(toy_connector, ctx, Stage.PARSE, capture)
    parsed_b = run_stage(toy_connector, ctx, Stage.PARSE, capture)
    assert parsed_a == parsed_b  # idempotent
    assert parsed_a == {"id": "p1", "cameras": 7}
