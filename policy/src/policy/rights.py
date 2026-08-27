# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rights as first-class data (§42.1, SIG-LIC-001..004b).

Every source and evidence artifact carries a :class:`RightsRecord`. Three
non-obvious invariants live here rather than in prose:

* ``redistributable`` is a **separately reviewed boolean** and MUST NOT be
  derived from the licence string (SIG-LIC-003). A site-wide permissive licence
  may not cover incorporated third-party data. The dataclass therefore *requires*
  the field explicitly and never infers it.
* A source with unresolved rights is ``UNDETERMINED`` (SIG-LIC-004): the
  connector may still run for internal research, but the export gate fails closed.
* ``ai_training_permitted`` is a first-class grant distinct from the licence
  (SIG-LIC-004b), and defaults to ``False`` — access permission is not training
  permission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: Sentinel SPDX value for a source whose rights are not yet resolved
#: (SIG-LIC-004). Distinct from any real SPDX expression.
UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class RightsRecord:
    """The rights record every source and evidence artifact MUST carry (SIG-LIC-001)."""

    source_id: str
    spdx: str
    attribution: str
    #: Separately reviewed — NOT derived from ``spdx`` (SIG-LIC-003).
    redistributable: bool
    derivative_permitted: bool
    terms_url: str
    retrieval_date: date
    #: First-class grant, separate from the licence (SIG-LIC-004b). Default deny.
    ai_training_permitted: bool = False
    #: Provenance signal for silently-travelling share-alike (SIG-LIC-009a): the
    #: licence of a share-alike upstream this content is plausibly derived from,
    #: even where ``spdx`` itself declares something more permissive.
    upstream_license: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("rights record requires a source_id")
        if not self.spdx:
            raise ValueError("rights record requires an SPDX expression (or UNDETERMINED)")


def is_undetermined(record: RightsRecord) -> bool:
    """Whether a source's rights are unresolved (SIG-LIC-004)."""
    return record.spdx.strip().upper() == UNDETERMINED
