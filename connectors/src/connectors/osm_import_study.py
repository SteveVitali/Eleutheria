# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The sous-surveillance.net → OSM import study and its contribution gate (§35.2, P18.2).

The ~12,000-camera import the outline files under "France and Belgium: Technopolice"
is the concrete, already-executed path from an *activist database* to the *common
geographic substrate* SIG's whole federation thesis depends on — and the strongest
available evidence that the thesis works. **SIG-CONTRIB-016 makes studying it a
precondition of contribution**: Phase 18 MUST study the import — its conventions, its
community consultation, and its outcome — *before* proposing any SIG-originated
contribution at scale. SIG proposes nothing at scale before understanding how the
existing import was consulted and received (the P16.2 human-mediated posture).

This module owns two things:

* **The study as data** (:func:`import_study`, from ``data/osm_import_study.toml``):
  the machine-readable form of the prose study in
  ``docs/studies/osm-sous-surveillance-import.md`` — its field crosswalk and
  distance-banded conflation conventions (F9.12), its consultation timeline and the
  one-line-email licensing anti-pattern it must not repeat (F9.6/F9.8), its measured
  outcome (F9.6/F9.7/F9.10), and the corrections to the outline's number and actor
  attribution it establishes (F9.7).
* **The contribution gate** (:func:`assert_import_studied_before_scaled_contribution`):
  a hard precondition that refuses a *SIG-originated contribution at scale* proposal
  until the study is complete. Per-device human-mediated suggestions (P16.2,
  :mod:`tasks.contribution`) are unaffected — the gate is specifically the
  SIG-CONTRIB-016c bulk case, which the import study is the documented precondition of.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from ._data import load_table

#: The study sections SIG-CONTRIB-016 requires be documented before a scaled
#: contribution may be proposed: the import's conventions, its community
#: consultation, and its outcome.
REQUIRED_SECTIONS: tuple[str, ...] = ("conventions", "consultation", "outcome")


class ImportNotStudied(Exception):
    """Raised when a scaled OSM contribution is proposed before the import is studied.

    The mechanical form of SIG-CONTRIB-016: the ~12,000-camera import MUST be studied
    — conventions, consultation, and outcome documented — before any SIG-originated
    contribution at scale. Raised naming the missing section(s).
    """


@dataclass(frozen=True)
class ImportStudy:
    """The sous-surveillance.net → OSM import study (§35.2, SIG-CONTRIB-016).

    ``join_key`` is the upstream identifier that survives in OSM
    (``ref:sous-surveillance_net``), the key SIG reconciles on rather than
    re-importing the activist database. The three required sections are each present
    iff their table carries ``documented = true`` and at least one substantive fact.
    """

    join_key: str
    import_source_id: str
    corrections: Mapping[str, Any]
    conventions: Mapping[str, Any]
    consultation: Mapping[str, Any]
    outcome: Mapping[str, Any]

    def _section(self, name: str) -> Mapping[str, Any]:
        return getattr(self, name)

    def documented_sections(self) -> dict[str, bool]:
        """Whether each required section is documented (SIG-CONTRIB-016)."""
        result: dict[str, bool] = {}
        for name in REQUIRED_SECTIONS:
            section = self._section(name)
            result[name] = bool(section.get("documented")) and len(section) > 1
        return result

    def missing_sections(self) -> list[str]:
        """The required study sections not yet documented."""
        return [name for name, ok in self.documented_sections().items() if not ok]

    def is_complete(self) -> bool:
        """Whether conventions, consultation, and outcome are all documented."""
        return not self.missing_sections()


def _study_from_table(table: Mapping[str, Any]) -> ImportStudy:
    return ImportStudy(
        join_key=str(table.get("join_key", "")),
        import_source_id=str(table.get("import_source_id", "")),
        corrections=dict(table.get("corrections", {})),
        conventions=dict(table.get("conventions", {})),
        consultation=dict(table.get("consultation", {})),
        outcome=dict(table.get("outcome", {})),
    )


@cache
def import_study() -> ImportStudy:
    """The sous-surveillance.net → OSM import study (``data/osm_import_study.toml``)."""
    return _study_from_table(load_table("osm_import_study"))


def assert_import_studied_before_scaled_contribution(
    proposal: Mapping[str, Any] | None = None,
) -> ImportStudy:
    """Refuse a SIG-originated contribution at scale until the import is studied (SIG-CONTRIB-016).

    Returns the completed :class:`ImportStudy` when the study documents its
    conventions, consultation, and outcome; otherwise raises :class:`ImportNotStudied`
    naming the missing sections. ``proposal`` is the (optional) scaled-contribution
    description being gated — it is echoed in the error so the refusal is auditable.
    This gate is the SIG-CONTRIB-016c bulk case only; the P16.2 per-device
    human-mediated suggestion workflow is not gated by it.
    """
    study = import_study()
    if not study.is_complete():
        what = (
            f" ({proposal.get('description')})" if proposal and proposal.get("description") else ""
        )
        raise ImportNotStudied(
            f"a SIG-originated OSM contribution at scale{what} may not be proposed until the "
            f"~12,000-camera sous-surveillance.net import is studied (SIG-CONTRIB-016); "
            f"undocumented section(s): {study.missing_sections()}"
        )
    return study


__all__ = [
    "REQUIRED_SECTIONS",
    "ImportNotStudied",
    "ImportStudy",
    "assert_import_studied_before_scaled_contribution",
    "import_study",
]
