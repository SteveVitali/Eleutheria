# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""probe_run — the shared ``sig.probe-run/1`` record seam (P35.3, G10/SIG-OPS-011).

Every production-truth probe writes one record format — this module — never a
parallel schema. Factored additively out of ``republish_probe.py``: a record
carries

* ``version``      — ``sig.probe-run/1``,
* ``generated_at`` — a ``date -u`` timestamp,
* ``probe``        — the registry id of the probe that ran,
* ``subject``      — what was probed (paths/urls/inputs — redaction-safe),
* ``release``      — the release/export identifiers the run binds, when known,
* ``checks``       — one leg per check: ``pass`` | ``fail`` | ``skipped`` with
                     structured detail and offered/evaluated counts,
* ``overall``      — ``fail`` on any failed leg, ``partial`` on any skipped leg,
                     ``pass`` only when every leg that ran was green.

Honesty rules inherited from the republish-probe writer: an empty/no-input leg
is ``skipped`` with a reason, never a fabricated pass; a leg that offered a
non-empty candidate set but evaluated none fails (SIG-ENG-042 — the
observability.yml 0-measurement replay). ``write_record`` prints the record's
sha256 — the output digest a live-claim citation (SIG-MEM-011) and the tail
sweep (ADR-199) bind.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROBE_RUN_VERSION = "sig.probe-run/1"


def utcnow() -> str:
    """A ``date -u``-form timestamp — the only clock a record may cite (OM-04)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class CheckResult:
    """One probe-run leg: a verdict plus structured, redaction-safe detail."""

    verdict: str  # "pass" | "fail" | "skipped"
    detail: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {"verdict": self.verdict, **self.detail}


def overall_for(verdicts: list[str]) -> str:
    """The honest roll-up: fail > partial (skipped) > pass; empty → partial."""
    if "fail" in verdicts:
        return "fail"
    if not verdicts or "skipped" in verdicts:
        return "partial"
    return "pass"


def build_record(
    probe: str,
    checks: dict[str, CheckResult],
    *,
    subject: dict[str, Any] | None = None,
    release: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Assemble the ``sig.probe-run/1`` record for one probe run."""
    return {
        "version": PROBE_RUN_VERSION,
        "generated_at": now or utcnow(),
        "probe": probe,
        "subject": subject or {},
        "release": release or {},
        "checks": {name: c.as_json() for name, c in checks.items()},
        "overall": overall_for([c.verdict for c in checks.values()]),
    }


def write_record(record: dict[str, Any], out: Path) -> str:
    """Write the record bytes and return their sha256 — the cited digest."""
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    out.write_text(payload, encoding="utf-8")
    return digest


def record_sha256(path: Path) -> str:
    """The digest a citation binds: sha256 of the committed record's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
