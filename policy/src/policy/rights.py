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
* ``reservation`` is a first-class **refusal** state, distinct from
  ``UNDETERMINED`` (SIG-INGEST-046c, §23.7). An affirmative machine-readable
  rights reservation — a ``Content-Signal`` directive, a TDM reservation, an
  EU DSM Article 4 reservation — is honoured as a refusal and recorded on the
  rights record, never collapsed into ``UNDETERMINED``: an unresolved record
  invites the Stage-0 conversation, a refused one closes it. The state is
  additive — a recorded reservation sits beside the SPDX expression and never
  edits a landed fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: Sentinel SPDX value for a source whose rights are not yet resolved
#: (SIG-LIC-004). Distinct from any real SPDX expression.
UNDETERMINED = "UNDETERMINED"

#: The vocabulary of affirmative machine-readable rights reservations a
#: recorded ``RightsReservation.kind`` names (SIG-INGEST-046c). Detection is in
#: :mod:`policy.crawler`; these are the *recorded* kinds.
RESERVATION_KINDS: frozenset[str] = frozenset(
    {
        "content_signal",  # Content-Signal directive, e.g. ``ai-train=no``
        "tdm_reservation",  # TDM-Reservation: 1 header / tdmrep signal
        "x_robots_tag",  # X-Robots-Tag: noai / noimageai
        "article_4",  # an EU DSM Article 4 reservation in another form
        "express_terms",  # captured express terms carrying a reservation (A-8/S6 R-19)
        "opt_out",  # a direct host-level opt-out (§26 rule 7)
        "other",  # a reservation form not yet enumerated — detail carried verbatim
    }
)


@dataclass(frozen=True)
class RightsReservation:
    """A recorded affirmative machine-readable rights reservation (SIG-INGEST-046c).

    The record of a refusal, not a licence fact: ``kind`` names the reservation
    form from :data:`RESERVATION_KINDS`, ``verbatim`` carries the
    machine-readable signal as observed, ``observed_on`` the date it was
    recorded, and ``evidence`` the pointer a reviewer can audit (a fetch/live
    record, a capture). All four are required — a reservation is asserted only
    on evidence (§3.1), never inferred.
    """

    kind: str
    verbatim: str
    observed_on: date
    evidence: str

    def __post_init__(self) -> None:
        if self.kind not in RESERVATION_KINDS:
            raise ValueError(
                f"rights reservation kind {self.kind!r} not in "
                f"{sorted(RESERVATION_KINDS)} — a new kind is an additive "
                "vocabulary entry (SIG-INGEST-046c)"
            )
        if not self.verbatim:
            raise ValueError("a rights reservation requires the verbatim signal")
        if not self.evidence:
            raise ValueError("a rights reservation requires an evidence pointer (§3.1)")


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
    #: P34.19 (F-403, ADR-183): the source's captured terms, verbatim, for
    #: express-terms sources the operator chose to keep public. Empty when the
    #: source carries no captured express terms.
    captured_terms_verbatim: str = ""
    #: Pointer to the capture evidence (artifact + item id) the verbatim text
    #: was read from.
    captured_terms_evidence: str = ""
    #: The recorded basis on which the source's rows are published (e.g.
    #: ``operator-accepted express terms (ADR-183)``). Empty when no express
    #: acceptance applies.
    publication_basis: str = ""
    #: A recorded affirmative machine-readable rights reservation
    #: (SIG-INGEST-046c, P36.1a). Optional and additive — ``None`` means no
    #: refusal is recorded (the common case); a set value is the *refused*
    #: state, stored distinctly from ``UNDETERMINED``: the source's SPDX
    #: expression keeps its own meaning and the reservation sits beside it.
    reservation: RightsReservation | None = None

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("rights record requires a source_id")
        if not self.spdx:
            raise ValueError("rights record requires an SPDX expression (or UNDETERMINED)")


def is_undetermined(record: RightsRecord) -> bool:
    """Whether a source's rights are unresolved (SIG-LIC-004)."""
    return record.spdx.strip().upper() == UNDETERMINED


def is_refused(record: RightsRecord) -> bool:
    """Whether the record carries an affirmative rights reservation (SIG-INGEST-046c).

    *Refused* is a distinct state from *unresolved*: ``is_refused`` and
    :func:`is_undetermined` are independent — a reservation is honoured as a
    refusal, never collapsed into ``UNDETERMINED``.
    """
    return record.reservation is not None
