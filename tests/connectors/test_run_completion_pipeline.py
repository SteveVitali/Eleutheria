# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.2 / ADR-109: every live execution ends by recording its completion.

The pipeline appends the completion through the sink's ``record_completion``
(the PG sink writes an ``ingest_run_completion`` row; the real-PG proof is
``tests/db/test_run_completion.py``). These tests pin the driver contract with a
recording sink: success → ``ok``/``partial``/``quota_reached``, an exception →
``failed`` carrying only the exception CLASS, replay/shadow and gate refusals →
nothing, and a completion that cannot be written never masks the run.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from connectors.isolation import NetworkEgressBlocked
from connectors.loader import IngestionNotPermitted
from connectors.pipeline import RunReport, completion_status, run
from connectors.stages import CompletionRecorder, InMemoryClaimSink


class RecordingSink:
    """A claim sink that also records completions (the CompletionRecorder protocol)."""

    def __init__(self, *, fail: bool = False) -> None:
        self.claims: list[Mapping[str, Any]] = []
        self.completions: list[dict[str, Any]] = []
        self._fail = fail

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
        self.claims.extend(claims)

    def record_completion(
        self, status: str, *, source_id: str | None = None, detail: str | None = None
    ) -> str:
        if self._fail:
            raise ConnectionError("server closed the connection unexpectedly")
        self.completions.append({"status": status, "source_id": source_id, "detail": detail})
        return "completion-1"


def _targets(url: str = "https://portal.example/p1") -> list[dict[str, str]]:
    return [{"id": "p1", "url": url, "subject_id": "entity-1"}]


def _ctx(make_context, make_fetcher, transport, sink, **kwargs):  # type: ignore[no-untyped-def]
    ctx = make_context(
        fetcher=make_fetcher(transport), parameters={"targets": _targets()}, **kwargs
    )
    ctx.claim_sink = sink
    return ctx


def test_protocol_distinguishes_recording_sinks() -> None:
    assert isinstance(RecordingSink(), CompletionRecorder)
    assert not isinstance(InMemoryClaimSink(), CompletionRecorder)


def test_a_clean_run_records_ok_once(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 3})})
    sink = RecordingSink()
    report = run(toy_connector, _ctx(make_context, make_fetcher, transport, sink))
    assert report.asserted is True
    assert sink.completions == [{"status": "ok", "source_id": "eyes_on_flock", "detail": None}]


def test_a_run_with_a_disappearance_records_partial(
    make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {}, status=404)})
    sink = RecordingSink()
    run(toy_connector, _ctx(make_context, make_fetcher, transport, sink))
    assert [c["status"] for c in sink.completions] == ["partial"]


def test_an_exception_records_failed_with_the_class_only_and_propagates(
    make_fetcher, make_context, transport_factory, json_response, leaky_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 1})})
    sink = RecordingSink()
    with pytest.raises(NetworkEgressBlocked):
        run(leaky_connector, _ctx(make_context, make_fetcher, transport, sink))
    assert sink.completions == [
        {"status": "failed", "source_id": "eyes_on_flock", "detail": "NetworkEgressBlocked"}
    ]


def test_a_gate_refusal_is_not_an_execution_and_records_nothing(
    make_fetcher, make_context, transport_factory, json_response, toy_connector, permitted_source
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 1})})
    sink = RecordingSink()
    ctx = _ctx(make_context, make_fetcher, transport, sink)
    ctx.source = dataclasses.replace(permitted_source, ingestion_permitted=False)
    with pytest.raises(IngestionNotPermitted):
        run(toy_connector, ctx)
    assert sink.completions == []


@pytest.mark.parametrize("mode", ["replay", "shadow"])
def test_replay_and_shadow_record_nothing(
    mode, make_fetcher, make_context, transport_factory, json_response, toy_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    transport = transport_factory({url: json_response(url, {"id": "p1", "cameras": 1})})
    sink = RecordingSink()
    run(toy_connector, _ctx(make_context, make_fetcher, transport, sink, **{mode: True}))
    assert sink.completions == [] and sink.claims == []


def test_an_unwritable_completion_never_masks_the_run(
    make_fetcher, make_context, transport_factory, json_response, toy_connector, leaky_connector
) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/p1"
    ok = transport_factory({url: json_response(url, {"id": "p1", "cameras": 2})})
    report = run(toy_connector, _ctx(make_context, make_fetcher, ok, RecordingSink(fail=True)))
    assert report.asserted is True  # the success path still returns its report
    leak = transport_factory({url: json_response(url, {"id": "p1", "cameras": 2})})
    with pytest.raises(NetworkEgressBlocked):  # the ORIGINAL exception, not ConnectionError
        run(leaky_connector, _ctx(make_context, make_fetcher, leak, RecordingSink(fail=True)))


def test_completion_status_precedence() -> None:
    assert completion_status(RunReport()) == "ok"
    assert completion_status(RunReport(refusals=[{"id": "x"}])) == "partial"
    assert completion_status(RunReport(drifted=[{"id": "x"}])) == "partial"
    assert completion_status(RunReport(budget_reached=True)) == "partial"
    # A 429 wall wins over every other disposition.
    assert completion_status(RunReport(quota_reached=True, refusals=[{"id": "x"}])) == (
        "quota_reached"
    )
