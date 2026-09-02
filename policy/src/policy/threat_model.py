# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The threat model as a maintained, versioned artifact (§44, SIG-SEC-001).

The threat model is data (``policy/data/threat_model.toml``), reviewed at every
phase gate. Its binding invariant: every adversary row MUST name at least one
mitigation that maps to a defined requirement id. A row with no mapped
mitigation fails the phase gate. :func:`validate_threat_model` enforces exactly
that, so the model is kept operative rather than rhetorical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ._data import load_table

#: A defined SIG requirement id, e.g. SIG-PUB-007, SIG-LIC-004a, SIG-PUB-014a.
_REQUIREMENT_ID = re.compile(r"^SIG-[A-Z]+-\d+[a-z]?$")


class ThreatModelError(Exception):
    """Raised when the threat model fails its phase-gate invariant (SIG-SEC-001)."""


@dataclass(frozen=True)
class ThreatRow:
    """One adversary row of the threat model (§44.2)."""

    adversary: str
    objective: str
    mitigations: tuple[str, ...]
    notes: str = ""


def is_requirement_id(token: str) -> bool:
    """Whether ``token`` is a well-formed SIG requirement id."""
    return bool(_REQUIREMENT_ID.match(token))


def load_threat_model() -> tuple[ThreatRow, ...]:
    """Load the adversary rows from the versioned threat-model artifact."""
    rows = load_table("threat_model")["adversaries"]
    return tuple(
        ThreatRow(
            adversary=r["adversary"],
            objective=r["objective"],
            mitigations=tuple(r["mitigations"]),
            notes=r.get("notes", ""),
        )
        for r in rows
    )


def threat_model_version() -> str:
    """The version stamp of the threat-model artifact (SIG-SEC-001)."""
    return str(load_table("threat_model")["version"])


def validate_threat_model(rows: tuple[ThreatRow, ...] | None = None) -> None:
    """Enforce the phase-gate invariant (SIG-SEC-001).

    Every adversary row must name at least one mitigation that is a well-formed,
    defined requirement id. Raises :class:`ThreatModelError` on the first
    violation.
    """
    rows = rows if rows is not None else load_threat_model()
    if not rows:
        raise ThreatModelError("threat model is empty (SIG-SEC-001)")
    for row in rows:
        mapped = [m for m in row.mitigations if is_requirement_id(m)]
        if not mapped:
            raise ThreatModelError(
                f"adversary {row.adversary!r} has no mitigation mapping to a defined "
                "requirement id; it fails the phase gate (SIG-SEC-001)."
            )
