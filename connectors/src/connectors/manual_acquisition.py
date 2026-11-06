# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Manual-acquisition dependencies modelled as data (§21.3, SIG-INGEST-008; P37.5b).

Some dependencies are **manual-acquisition** — a human obtains them through an
account/login, a mailed disc, a records release — and MUST be modelled as such,
with a documented human procedure recording DOI (or the publisher's identifier),
version, and checksum. The build MUST NOT assume they are automatically
fetchable: pretending a manual dependency is automatable produces a pipeline
that silently runs on stale data.

The registry is ``data/manual_acquisitions.toml`` (``sig.manual-acquisitions/1``),
data not code: each ``[[dependency]]`` row names the ``sources.toml`` source it
models, the human access path, and the acquisition provenance — ``identifier``/
``doi``, ``version``, ``sha256``, ``acquired_at`` — which MUST be populated when
the row is marked ``status = "acquired"`` and MUST be empty while ``pending`` (a
pending row claiming acquisition fields is a fabricated record). The documented
procedure lives in ``docs/ops/manual-acquisition.md``.

``sig-connectors validate`` fails closed on a registry defect: a source whose
``access_method`` declares manual acquisition with no record, a record naming a
source that does not declare manual acquisition, an unknown ``source_id``, or a
``status``/provenance contradiction. ``sig-connectors run`` refuses a registered
manual dependency in every mode — there is no automatic fetch path for it; the
runbook is the path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ._data import load_table

TABLE = "manual_acquisitions"
SCHEMA = "sig.manual-acquisitions/1"
RUNBOOK = "docs/ops/manual-acquisition.md"

#: The closed ``status`` vocabulary: the dependency awaits its human leg, or the
#: leg ran and the provenance fields carry the record.
STATUSES: frozenset[str] = frozenset({"pending", "acquired"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
#: ``access_method`` free text that declares manual acquisition (the
#: ``leaic_crosswalk`` row's "manual acquisition (login)" shape).
_MANUAL_MARK = re.compile(r"\bmanual\b", re.IGNORECASE)


class ManualAcquisitionError(Exception):
    """The committed registry is malformed — fail closed, never guess."""


class ManualAcquisitionRequired(Exception):
    """``sig-connectors run`` was asked to drive a manual-acquisition dependency.

    A registered manual dependency has no automatic fetch path at any mode —
    the documented human procedure (the runbook the message names) is the only
    acquisition path (SIG-INGEST-008).
    """


@dataclass(frozen=True)
class ManualAcquisition:
    """One ``[[dependency]]`` row — a manual-acquisition record."""

    id: str
    source_id: str
    identifier: str
    doi: str
    version: str
    sha256: str
    acquired_at: str
    status: str
    access: str
    runbook: str
    notes: str


def _as_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _dependency(row: dict[str, Any]) -> ManualAcquisition:
    return ManualAcquisition(
        id=_as_str(row.get("id")),
        source_id=_as_str(row.get("source_id")),
        identifier=_as_str(row.get("identifier")),
        doi=_as_str(row.get("doi")),
        version=_as_str(row.get("version")),
        sha256=_as_str(row.get("sha256")),
        acquired_at=_as_str(row.get("acquired_at")),
        status=_as_str(row.get("status")),
        access=_as_str(row.get("access")),
        runbook=_as_str(row.get("runbook")),
        notes=_as_str(row.get("notes")),
    )


def manual_acquisitions() -> tuple[ManualAcquisition, ...]:
    """The committed manual-acquisition records (``sig.manual-acquisitions/1``).

    Raises :class:`ManualAcquisitionError` on a malformed table — a bad registry
    is a registration defect surfaced loud, never a silent empty set.
    """
    raw = load_table(TABLE)
    schema = _as_str(raw.get("schema"))
    if schema != SCHEMA:
        raise ManualAcquisitionError(f"manual_acquisitions.toml schema {schema!r} != {SCHEMA!r}")
    deps = raw.get("dependency")
    if not isinstance(deps, list):
        raise ManualAcquisitionError("manual_acquisitions.toml: [[dependency]] must be a list")
    out: list[ManualAcquisition] = []
    seen: set[str] = set()
    for row in deps:
        if not isinstance(row, dict):
            raise ManualAcquisitionError(
                "manual_acquisitions.toml: a dependency row is not a table"
            )
        dep = _dependency(row)
        if not dep.id or not dep.source_id:
            raise ManualAcquisitionError(
                "manual_acquisitions.toml: every dependency needs id + source_id"
            )
        if dep.id in seen:
            raise ManualAcquisitionError(
                f"manual_acquisitions.toml: duplicate dependency id {dep.id!r}"
            )
        seen.add(dep.id)
        out.append(dep)
    return tuple(out)


def manual_acquisition_ids() -> frozenset[str]:
    """The ``source_id`` set the registry models as manual-acquisition."""
    return frozenset(dep.source_id for dep in manual_acquisitions())


def is_manual_acquisition(source_id: str) -> bool:
    """Whether ``source_id`` is registered as a manual-acquisition dependency."""
    return source_id in manual_acquisition_ids()


def is_manual_access_method(access_method: str) -> bool:
    """Whether an ``access_method`` string declares manual acquisition."""
    return bool(_MANUAL_MARK.search(access_method))


def assert_automatic_acquirable(source_id: str) -> None:
    """Refuse to drive a registered manual-acquisition dependency (SIG-INGEST-008).

    Called by ``runner.run_source`` before any mode resolves — a manual
    dependency has no fetch stage for ``sig-connectors run`` to drive; the
    runbook is the acquisition path.
    """
    if is_manual_acquisition(source_id):
        record = next(dep for dep in manual_acquisitions() if dep.source_id == source_id)
        raise ManualAcquisitionRequired(
            f"source {source_id!r} is a manual-acquisition dependency "
            f"({record.identifier!r}) — no automatic fetch path exists; the "
            f"documented human procedure in {record.runbook or RUNBOOK} is the "
            "acquisition path (SIG-INGEST-008)"
        )


def _record_violations(dep: ManualAcquisition, source_ids: set[str]) -> list[str]:
    """Per-record integrity rules (provenance completeness/honesty)."""
    out: list[str] = []
    where = f"dependency {dep.id!r} (source {dep.source_id!r})"
    if dep.source_id not in source_ids:
        out.append(f"{where}: source_id not in the committed source registry")
    if dep.status not in STATUSES:
        out.append(f"{where}: status {dep.status!r} not in {sorted(STATUSES)}")
    if not dep.access:
        out.append(f"{where}: no human access path recorded")
    if not dep.identifier:
        out.append(f"{where}: no identifier recorded (the publisher's id the record cites)")
    if dep.status == "acquired":
        # The MUST: the human procedure records DOI (or identifier), version,
        # and checksum. An acquired row missing any one is a record defect.
        for field in ("version", "sha256", "acquired_at"):
            if not getattr(dep, field):
                out.append(f"{where}: acquired but {field} empty")
        if dep.sha256 and not _SHA256.match(dep.sha256):
            out.append(f"{where}: sha256 {dep.sha256!r} is not a 64-hex digest")
    elif dep.status == "pending":
        # A pending row claiming acquisition provenance is a fabricated record.
        for field in ("doi", "version", "sha256", "acquired_at"):
            if getattr(dep, field):
                out.append(
                    f"{where}: pending but {field} populated — a pending row "
                    "carries no acquisition provenance"
                )
    return out


def manual_acquisition_violations() -> list[str]:
    """One violation per registry/source mismatch (SIG-INGEST-008).

    Both directions bind: every source whose ``access_method`` declares manual
    acquisition MUST have a record (the dependency is modelled), and every
    record MUST name a source that actually declares manual acquisition (the
    registry cannot mark a fetchable source manual and quietly shelter it).
    """
    from .registry import sources

    srcs = {s.id: s for s in sources()}
    manual_declared = {sid for sid, s in srcs.items() if is_manual_access_method(s.access_method)}
    deps = manual_acquisitions()
    registered = {dep.source_id for dep in deps}

    violations: list[str] = []
    for sid in sorted(manual_declared - registered):
        violations.append(
            f"source {sid!r} declares manual acquisition in access_method but "
            "carries no [[dependency]] record — every manual dependency MUST be "
            "modelled (SIG-INGEST-008)"
        )
    for sid in sorted(registered - manual_declared):
        violations.append(
            f"dependency for source {sid!r}: the source does not declare manual "
            "acquisition in access_method — the registry cannot mark a "
            "fetchable source manual"
        )
    for dep in deps:
        violations.extend(_record_violations(dep, set(srcs)))
    return violations


__all__ = [
    "RUNBOOK",
    "SCHEMA",
    "STATUSES",
    "ManualAcquisition",
    "ManualAcquisitionError",
    "ManualAcquisitionRequired",
    "assert_automatic_acquirable",
    "is_manual_access_method",
    "is_manual_acquisition",
    "manual_acquisition_ids",
    "manual_acquisition_violations",
    "manual_acquisitions",
]
