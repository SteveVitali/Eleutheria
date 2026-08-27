# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ingestion_permitted runtime gate (SIG-INGEST-028 / SIG-CHART-032)."""

from __future__ import annotations

import dataclasses

import pytest
from connectors.loader import (
    IngestionNotPermitted,
    assert_ingestion_permitted,
    run_connector,
)
from connectors.registry import get


def test_connector_refuses_to_run_when_ingestion_not_permitted() -> None:
    # SIG-INGEST-028: the pipeline MUST refuse to run a connector whose row says
    # ingestion is not permitted. Every seeded row defaults to false.
    ran = False

    def fetch(_source: object) -> None:  # pragma: no cover - must not run
        nonlocal ran
        ran = True

    with pytest.raises(IngestionNotPermitted):
        run_connector("deflock", fetch)
    assert ran is False


def test_gate_can_be_addressed_by_id_or_record() -> None:
    with pytest.raises(IngestionNotPermitted):
        assert_ingestion_permitted("eyes_on_flock")
    with pytest.raises(IngestionNotPermitted):
        assert_ingestion_permitted(get("eyes_on_flock"))


def test_connector_runs_only_once_ingestion_is_permitted() -> None:
    # The positive path: flipping ingestion_permitted opens the gate. Built
    # in-memory because no seeded source is permitted at Phase 0.
    permitted = dataclasses.replace(get("eyes_on_flock"), ingestion_permitted=True)
    result = run_connector(permitted, lambda s: f"fetched {s.id}")
    assert result == "fetched eyes_on_flock"
    assert assert_ingestion_permitted(permitted) is permitted


def test_unknown_source_id_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        assert_ingestion_permitted("no_such_source")
