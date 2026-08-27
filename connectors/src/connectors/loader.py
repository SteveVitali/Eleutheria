# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``ingestion_permitted`` runtime gate every connector passes through.

**SIG-INGEST-028 / SIG-CHART-032 (MUST).** The pipeline MUST refuse to run a
connector whose registry row says ingestion is not permitted. This is a runtime
gate with a test, not a policy note: ``ingestion_permitted`` defaults to false
(:mod:`connectors.registry`), so a source is inert until a reviewer has both
resolved its rights/compact posture *and* flipped the flag.

Phase-4 connectors call :func:`run_connector` (or, at minimum,
:func:`assert_ingestion_permitted`) before their first fetch; this ticket seeds
the registry and the gate, and deliberately contains no fetching logic (§21.5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .registry import SourceRecord, get

T = TypeVar("T")


class IngestionNotPermitted(Exception):
    """Raised when a connector is asked to run against a not-yet-permitted source."""


def assert_ingestion_permitted(source: SourceRecord | str) -> SourceRecord:
    """Fail closed unless ``ingestion_permitted`` is true for the source.

    Accepts a :class:`~connectors.registry.SourceRecord` or a source id (looked
    up in the registry). Returns the record so callers can chain. Raises
    :class:`IngestionNotPermitted` when the gate is closed (SIG-INGEST-028) and
    :class:`KeyError` for an unknown source id.
    """
    record = get(source) if isinstance(source, str) else source
    if not record.ingestion_permitted:
        raise IngestionNotPermitted(
            f"source {record.id!r} has ingestion_permitted=false; the pipeline "
            "refuses to run its connector until a reviewer resolves its rights "
            "and compact posture and permits ingestion (SIG-INGEST-028)."
        )
    return record


def run_connector(source: SourceRecord | str, fetch: Callable[[SourceRecord], T]) -> T:
    """Run ``fetch`` for ``source`` only if the ingestion gate is open.

    This is the seam Phase-4 connectors are loaded through: the gate is checked
    once, up front, and ``fetch`` never executes for a source that has not been
    permitted (SIG-INGEST-028).
    """
    record = assert_ingestion_permitted(source)
    return fetch(record)
