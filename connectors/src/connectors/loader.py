# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector-loader gate every connector passes through (§21.5, §22.4, §42.4).

**SIG-INGEST-014 / SIG-INGEST-028 / SIG-CHART-032 (MUST).** The connector loader
MUST check a source's ``ingestion_permitted`` flag, its ``custody_posture``, and
its ``compact_status`` **before any fetch**, and refuse to run when permission is
absent or unresolved. Licensing is enforced by the pipeline, not by good
intentions. This is a runtime gate with a test, not a policy note:
``ingestion_permitted`` defaults to false (:mod:`connectors.registry`), so a
source is inert until a reviewer has resolved its rights and compact posture
*and* flipped the flag.

**SIG-LIC-010 (MUST).** Export licence is **computed** from constituent rights
and the build fails on incompatibility. :func:`assert_export_compatible` is the
connector-loader-level realisation of that gate: it delegates to
:func:`policy.licensing.compute_export_license`, which computes the single licence
a set of sources may be exported under and raises when they span mutually
incompatible compartments (ODbL-1.0 and CC-BY-SA-4.0 cannot be merged, and
neither folds into CC-BY-4.0). Mixing incompatible compartments in one export
fails the build.

The driver (:mod:`connectors.pipeline`) calls :func:`assert_loadable` once, up
front, before any fetch.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from policy.licensing import (
    LicenseIncompatibilityError,
    compute_export_license,
    effective_license,
)

from .registry import CompactStatus, CustodyPosture, SourceRecord, get

T = TypeVar("T")

#: The ``compact_status`` values under which ingestion is permitted (§22.4). Every
#: other state — including ``no_response`` and ``permission_declined`` — denies it.
INGESTION_PERMITTING_COMPACT: frozenset[CompactStatus] = frozenset(
    {
        CompactStatus.PERMISSION_GRANTED,
        CompactStatus.PERMISSION_GRANTED_CONDITIONAL,
        CompactStatus.PUBLIC_TERMS_ONLY,
        CompactStatus.PARTNERSHIP_ACTIVE,
    }
)

#: The ``custody_posture`` values that permit a content-fetching connector (§8.4).
#: ``LINK`` means SIG only links out and never fetches/stores content, so a
#: content-capturing connector MUST NOT run against it.
CUSTODY_PERMITS_FETCH: frozenset[CustodyPosture] = frozenset(
    {CustodyPosture.MIRROR, CustodyPosture.DERIVE, CustodyPosture.REFERENCE}
)


class IngestionNotPermitted(Exception):
    """Raised when a connector is asked to run against a not-yet-permitted source."""


def compact_permits_ingestion(status: CompactStatus) -> bool:
    """Whether a ``compact_status`` permits ingestion (§22.4, SIG-INGEST-027/028)."""
    return status in INGESTION_PERMITTING_COMPACT


def custody_permits_fetch(posture: CustodyPosture) -> bool:
    """Whether a ``custody_posture`` permits a content-fetching connector (§8.4)."""
    return posture in CUSTODY_PERMITS_FETCH


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


def assert_loadable(source: SourceRecord | str) -> SourceRecord:
    """The full connector-loader gate, checked before any fetch (SIG-INGEST-014).

    Refuses to run unless *all three* hold: ``ingestion_permitted`` is true
    (SIG-INGEST-028), the ``compact_status`` permits ingestion (§22.4), and the
    ``custody_posture`` permits a content-fetching connector (§8.4). Any absent or
    unresolved permission fails closed with a reason. Returns the record so the
    driver can chain.
    """
    record = assert_ingestion_permitted(source)
    if not compact_permits_ingestion(record.compact_status):
        raise IngestionNotPermitted(
            f"source {record.id!r} has compact_status={record.compact_status.value!r}, "
            "which does not permit ingestion; the loader refuses to run before any "
            "fetch (SIG-INGEST-014/027)."
        )
    if not custody_permits_fetch(record.custody_posture):
        raise IngestionNotPermitted(
            f"source {record.id!r} has custody_posture={record.custody_posture.value!r} "
            "(link-only); a content-fetching connector MUST NOT run against it "
            "(SIG-INGEST-014, §8.4)."
        )
    return record


def is_loadable(source: SourceRecord | str) -> bool:
    """Whether :func:`assert_loadable` would pass, without raising."""
    try:
        assert_loadable(source)
    except (IngestionNotPermitted, KeyError):
        return False
    return True


def assert_export_compatible(sources: Iterable[SourceRecord | str]) -> str:
    """Compute the export licence for a set of sources; fail on incompatibility.

    The connector-loader realisation of SIG-LIC-010: the export licence is
    *computed* from the constituent rights records, and mixing mutually
    incompatible licence compartments raises
    :class:`policy.licensing.LicenseIncompatibilityError` (the build fails).
    ``UNDETERMINED`` or non-redistributable rights fail the export gate closed.
    Returns the single SPDX licence a compatible set may be exported under.
    """
    records = [(get(s) if isinstance(s, str) else s).rights for s in sources]
    return compute_export_license(records)


def source_export_license(source: SourceRecord | str) -> str:
    """The licence that governs one source's export placement (SIG-LIC-009a)."""
    record = get(source) if isinstance(source, str) else source
    return effective_license(record.rights)


def run_connector(source: SourceRecord | str, fetch: Callable[[SourceRecord], T]) -> T:
    """Run ``fetch`` for ``source`` only if the ingestion gate is open.

    This is the seam Phase-4 connectors are loaded through: the gate is checked
    once, up front, and ``fetch`` never executes for a source that has not been
    permitted (SIG-INGEST-028). Uses the full :func:`assert_loadable` gate.
    """
    record = assert_loadable(source)
    return fetch(record)


__all__ = [
    "CUSTODY_PERMITS_FETCH",
    "INGESTION_PERMITTING_COMPACT",
    "IngestionNotPermitted",
    "LicenseIncompatibilityError",
    "assert_export_compatible",
    "assert_ingestion_permitted",
    "assert_loadable",
    "compact_permits_ingestion",
    "custody_permits_fetch",
    "is_loadable",
    "run_connector",
    "source_export_license",
]
