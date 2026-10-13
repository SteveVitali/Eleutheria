# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The attribution-corrections artifact generator (P34.21a / ADR-194; E2-12).

``sig-connectors attribution-correction-list`` emits the committed, reviewer-
prepared list ``sig-db attribution-corrections`` consumes: one row per rights-
reviewed registry source carrying the source's OWN corrected (spdx, attribution,
terms) signature — the values the spine's mis-keyed records should have carried
(F-387). The artifact is generated from ``sources.toml`` (the reviewed rights
blocks are the authoritative input), written to
``docs/build/reports/rights/`` and COMMITTED; the reviewer may edit rows, and
``load_corrections`` fail-closed-validates whatever it reads — the artifact is
the control surface, not the registry.

A source with no recorded rights review (``rights_reviewed_by`` /
``rights_reviewed_on`` absent) CANNOT name a reviewer role or review date, so
it is reported under ``skipped`` — never silently corrected with a fabricated
review. The ``basis`` string names E2-12 + ADR-194 so every decision row cites
both.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .registry import sources as _registry_sources

#: The schema id the committed corrections artifact carries (the writer's
#: ``load_corrections`` requires ``corrections`` as a list; the schema string
#: is documentation/round-trip only).
CORRECTIONS_SCHEMA = "sig.attribution-corrections/1"

#: The canonical output path — committed under the rights-reports tree.
DEFAULT_OUTPUT = Path("docs/build/reports/rights/p34_21a_corrections.json")

#: Recorded licence-identifier normalisations (ADR-194): the malformed ids the
#: spine's stored ``rights_record`` rows may still carry, mapped to the
#: canonical SPDX id the corrected record bears. A prior carrying the LEFT id
#: is corrected to the RIGHT id — the same licence text under its canonical
#: expression, never a licence change.
SPDX_NORMALISATIONS: dict[str, str] = {
    "OGL-3.0": "OGL-UK-3.0",
    "LicenceOuverte-2.0": "etalab-2.0",
}

_CORRECTION_BASIS = (
    "E2-12 / ADR-194 attribution correction (P34.21a): the source's own reviewed "
    "rights signature corrected onto its claims — the F-387 record defect "
    "mis-keyed rights on SPDX alone; nothing here re-licenses a resolved record."
)


@dataclass(frozen=True)
class CorrectionRow:
    """One list row — mirrors ``db.rights_corrections.AttributionCorrection``."""

    source_id: str
    spdx: str
    attribution: str
    redistributable: str
    derivative_permitted: str
    terms_url: str
    reviewed_by: str
    reviewed_on: str
    basis: str
    retrieval_date: str
    review_packet: str | None
    spdx_aliases: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "source_id": self.source_id,
            "spdx": self.spdx,
            "attribution": self.attribution,
            "redistributable": self.redistributable,
            "derivative_permitted": self.derivative_permitted,
            "terms_url": self.terms_url,
            "reviewed_by": self.reviewed_by,
            "reviewed_on": self.reviewed_on,
            "basis": self.basis,
            "retrieval_date": self.retrieval_date,
        }
        if self.review_packet:
            out["review_packet"] = self.review_packet
        if self.spdx_aliases:
            out["spdx_aliases"] = list(self.spdx_aliases)
        return out


def _decided(value: bool, *, reviewed: bool) -> str:
    """The spine vocabulary for a registry boolean.

    A recorded rights review distinguishes 'no' (reviewed, not permitted) from
    UNDETERMINED (never reviewed) — the registry's ``false`` default conflates
    the two, so the review metadata is the discriminator.
    """
    if value:
        return "yes"
    return "no" if reviewed else "UNDETERMINED"


def corrections_list() -> dict[str, Any]:
    """The artifact document: one correction row per rights-reviewed source.

    Determinism: rows are emitted in registry ``source_id`` order; the
    generated_at is the caller's date, not the machine clock alone.
    """
    corrections: list[CorrectionRow] = []
    skipped: list[dict[str, Any]] = []
    for rec in _registry_sources():
        reviewed = bool(rec.rights_reviewed_by and rec.rights_reviewed_on)
        reviewed_on = rec.rights_reviewed_on
        if not reviewed or reviewed_on is None or not rec.rights_reviewed_by:
            skipped.append(
                {
                    "source_id": rec.id,
                    "reason": "no recorded rights review — a correction needs a "
                    "reviewer ROLE and review date (Part VIII §0.7), and none "
                    "exists; it stays un-corrected, never fabricated",
                }
            )
            continue
        rights = rec.rights
        aliases: tuple[str, ...] = ()
        spdx = rights.spdx
        # The corrections row's spdx is the registry's (already canonical after
        # the P34.21a renames); aliases name the *recorded* malformed ids the
        # spine's stored rows may carry — the normalisation map, declared.
        aliases = tuple(old for old, new in sorted(SPDX_NORMALISATIONS.items()) if new == spdx)
        corrections.append(
            CorrectionRow(
                source_id=rec.id,
                spdx=spdx,
                attribution=rights.attribution,
                redistributable=_decided(rights.redistributable, reviewed=reviewed),
                derivative_permitted=_decided(rights.derivative_permitted, reviewed=reviewed),
                terms_url=rights.terms_url,
                reviewed_by=rec.rights_reviewed_by,
                reviewed_on=reviewed_on.isoformat(),
                basis=_CORRECTION_BASIS,
                retrieval_date=rights.retrieval_date.isoformat(),
                review_packet=rec.review_packet or None,
                spdx_aliases=aliases,
            )
        )
    return {
        "schema": CORRECTIONS_SCHEMA,
        "generated_from": "connectors/src/connectors/data/sources.toml",
        "note": (
            "Reviewer-prepared corrections list for `sig-db attribution-corrections` "
            "(P34.21a / ADR-194; E2-12, F-387). Generated from the registry's "
            "reviewed rights blocks; a reviewer may edit rows before commit. "
            "Skipped sources carry no recorded rights review and cannot name a "
            "reviewer role — they are never corrected with a fabricated review."
        ),
        "corrections": [c.as_json() for c in corrections],
        "skipped": skipped,
        "totals": {"corrections": len(corrections), "skipped": len(skipped)},
    }


def write_corrections_list(out_path: Path | None = None, *, today: date | None = None) -> Path:
    """Serialise the artifact to ``out_path`` (canonical JSON, committed)."""
    doc = corrections_list()
    doc["generated_on"] = (today or date.today()).isoformat()
    path = out_path or DEFAULT_OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


__all__ = [
    "CORRECTIONS_SCHEMA",
    "DEFAULT_OUTPUT",
    "SPDX_NORMALISATIONS",
    "CorrectionRow",
    "corrections_list",
    "write_corrections_list",
]
