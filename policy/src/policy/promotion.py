# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §43.5 candidate → ``PhysicalAsset`` promotion gate (P37.10; SIG-PUB-012).

Layer G leads (RF/OUI matches, unverified reports, model output) enter the
graph as ``CandidateAsset`` claims at ``evidence_tier = F`` (SIG-ONTO-006) and
MUST NOT appear in any public device layer until promoted under §43.5
(SIG-PUB-011). Promotion to a published ``PhysicalAsset`` requires **either**
human field or imagery confirmation, **or** a documentary record — **never
corroboration count alone** (SIG-PUB-012). A candidate whose location
intersects a residential parcel is barred at every precision regardless of
confirmation (SIG-PUB-013, enforced through :func:`candidate_publishable`).

This module is the **only** candidate→``PhysicalAsset`` writer:

* :func:`promotion_permitted` is the single decision function on the write
  path — a pure gate returning every named refusal, never a warning.
* :func:`promotion_claims` is the single claim producer: it mints the
  promoted asset's claim set only behind a permitted decision and raises
  :class:`PromotionRefused` otherwise. The :class:`PromotionWrite` it returns
  carries a private gate token — a ``PromotionWrite`` cannot be fabricated
  without the gate having run.
* The emitted asset subject rides the ``promoted:`` prefix the committed
  subject map (:mod:`db.subject_types`) declares as ``physical_asset``; the
  candidate's own ``candidate:`` subject mints ``candidate_asset``. A new
  promotion path is not a code shortcut — it is a deliberate map edit plus a
  gate change, the failure mode this module exists to prevent.

What counts as confirmation is deliberately narrow. A ``Confirmation`` names
one of three admissible kinds (``field`` — a human field verification;
``imagery`` — an imagery confirmation; ``documentary`` — a documentary
record, the D1/D2 class of SIG-RECON-033) plus the **actor or document
reference** evidencing it — a field/imagery confirmation names the confirming
actor, a documentary confirmation names the record. Corroboration
(``observation_count``, the ``corroborated`` status) is never an admissible
kind, and a candidate's ``detection_method`` is how the lead was *found* —
``imagery_detection`` is an automated detection, not a recorded imagery
confirmation — so it never satisfies SIG-PUB-012 on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .sensitivity import candidate_publishable

#: The versioned rule stamped on every decision and every emitted claim
#: (``assertion_rationale``). Bump when the §43.5 rule's enforcement changes.
PROMOTION_RULE_VERSION = "asset-promotion/1"

#: The subject prefix the promoted asset mints under — declared
#: ``physical_asset`` in ``db/src/db/data/subject_entity_types.toml``.
PROMOTED_SUBJECT_PREFIX = "promoted:"


class ConfirmationKind(StrEnum):
    """The admissible §43.5 confirmation classes (SIG-PUB-012).

    Corroboration is **not** a member by construction: there is no
    ``CORROBORATION`` value a caller can pass, so a corroboration count can
    never masquerade as confirmation.
    """

    #: A human field verification — the reference names the confirming actor.
    FIELD = "field"
    #: An imagery confirmation — the reference names the confirming actor.
    IMAGERY = "imagery"
    #: A documentary record — the reference names the record (D1/D2 class).
    DOCUMENTARY = "documentary"


#: The promoted asset's §11.8 ``confirmation_status`` per confirmation kind —
#: deterministic precedence when several kinds are recorded (field first).
_CONFIRMATION_STATUS = (
    (ConfirmationKind.FIELD, "field_confirmed"),
    (ConfirmationKind.IMAGERY, "imagery_confirmed"),
    (ConfirmationKind.DOCUMENTARY, "record_confirmed"),
)


@dataclass(frozen=True)
class Confirmation:
    """One recorded confirmation behind a promotion request.

    ``reference`` is the actor or document reference the record carries —
    the confirming actor for ``field``/``imagery``, the documentary record
    for ``documentary``. ``claim_ids`` are the spine claims recording the
    confirmation, carried onto the emitted claims'
    ``derived_from_claim_ids`` so the promotion keeps its evidence chain.
    """

    kind: ConfirmationKind
    reference: str
    claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateForPromotion:
    """The candidate facts a promotion request is decided over.

    Mirrors the §11.9 ``CandidateAsset`` shape: ``subject`` is the candidate's
    ``sig.connector.subject`` value (the ``candidate:`` family), and
    ``observation_count``/``promotion_status`` are the recorded corroboration
    facts — inputs to the decision, never confirmation themselves.
    """

    subject: str
    detection_method: str
    observation_count: int = 0
    promotion_status: str = "unreviewed"
    residential_parcel_flag: bool = False
    confirmations: tuple[Confirmation, ...] = ()
    location_estimate_wkt: str | None = None
    asset_technology: str | None = None


class PromotionRefusal(StrEnum):
    """The closed refusal vocabulary — one machine-checkable reason each."""

    #: No candidate subject named — a promotion always names its candidate.
    MISSING_SUBJECT = "missing_subject"
    #: A ``promotion_status`` outside the §11.9 vocabulary — fail closed.
    UNKNOWN_STATUS = "unknown_status"
    #: Residential-parcel intersection — barred at every precision (SIG-PUB-013).
    RESIDENTIAL_PARCEL = "residential_parcel"
    #: A recorded ``rejected``/``suppressed_by_policy`` decision stands.
    DECIDED = "decided"
    #: Already promoted — the append-only record is written once, never twice.
    ALREADY_PROMOTED = "already_promoted"
    #: No admissible confirmation recorded — corroboration count alone never
    #: promotes (SIG-PUB-012).
    CORROBORATION_ONLY = "corroboration_only"
    #: A confirmation kind declared without its actor/document reference —
    #: the §3.1 defining standard: a claim carries the evidence behind it.
    UNPROVENANCED_CONFIRMATION = "unprovenanced_confirmation"


#: The §11.9 ``promotion_status`` vocabulary (seed_vocab/ontology enum).
_KNOWN_STATUSES = frozenset(
    {"unreviewed", "corroborated", "promoted", "rejected", "suppressed_by_policy"}
)
_DECIDED_STATUSES = frozenset({"rejected", "suppressed_by_policy"})


@dataclass(frozen=True)
class PromotionDecision:
    """The recorded promotion verdict — permitted only with zero refusals."""

    permitted: bool
    refusals: tuple[PromotionRefusal, ...]
    #: The promoted asset's ``confirmation_status`` (§11.8) — ``None`` on refusal.
    confirmation_status: str | None
    #: The candidate's ``promotion_status`` the write records — ``promoted`` on
    #: success, ``suppressed_by_policy`` on a parcel refusal, else unchanged.
    resulting_status: str
    rule: str = PROMOTION_RULE_VERSION


def promotion_permitted(candidate: CandidateForPromotion) -> PromotionDecision:
    """The §43.5 promotion decision — every refusal named, fail closed.

    This is the single gate on the candidate→``PhysicalAsset`` write path:
    :func:`promotion_claims` refuses without its permit and no other code
    mints a promoted asset. Corroboration facts (``observation_count``, the
    ``corroborated`` status) are inputs to the record, never promotion
    evidence — a candidate with a thousand corroborating observations and no
    recorded field, imagery or documentary confirmation is refused
    ``corroboration_only``.
    """
    refusals: list[PromotionRefusal] = []
    status = str(candidate.promotion_status or "")

    if not str(candidate.subject or "").strip():
        refusals.append(PromotionRefusal.MISSING_SUBJECT)
    if status not in _KNOWN_STATUSES:
        refusals.append(PromotionRefusal.UNKNOWN_STATUS)
    if not candidate_publishable(bool(candidate.residential_parcel_flag)):
        refusals.append(PromotionRefusal.RESIDENTIAL_PARCEL)
    if status == "promoted":
        refusals.append(PromotionRefusal.ALREADY_PROMOTED)
    elif status in _DECIDED_STATUSES:
        refusals.append(PromotionRefusal.DECIDED)

    confirmations = tuple(candidate.confirmations or ())
    if not confirmations:
        refusals.append(PromotionRefusal.CORROBORATION_ONLY)
    elif any(not str(c.reference or "").strip() for c in confirmations):
        refusals.append(PromotionRefusal.UNPROVENANCED_CONFIRMATION)

    confirmation_status: str | None = None
    if not refusals:
        kinds = {c.kind for c in confirmations}
        for kind, confirmed_as in _CONFIRMATION_STATUS:
            if kind in kinds:
                confirmation_status = confirmed_as
                break

    if not refusals:
        resulting = "promoted"
    elif PromotionRefusal.RESIDENTIAL_PARCEL in refusals:
        resulting = "suppressed_by_policy"
    else:
        # A refusal records no status change: corroboration-only stays what it
        # was, a decided/already-promoted candidate keeps its recorded status.
        resulting = status if status in _KNOWN_STATUSES else "unreviewed"

    return PromotionDecision(
        permitted=not refusals,
        refusals=tuple(refusals),
        confirmation_status=confirmation_status,
        resulting_status=resulting,
    )


class PromotionRefused(Exception):
    """A candidate→``PhysicalAsset`` write attempted without a permit.

    Carries the gate's decision so the caller can record *why* — a refusal is
    a named fact, never a silent drop.
    """

    def __init__(self, candidate: CandidateForPromotion, decision: PromotionDecision):
        self.candidate = candidate
        self.decision = decision
        named = ", ".join(r.value for r in decision.refusals) or "no refusals"
        super().__init__(
            f"promotion of {candidate.subject!r} refused ({named}; "
            f"{PROMOTION_RULE_VERSION}, SIG-PUB-012)"
        )


#: The private token only :func:`promotion_claims` knows — a
#: ``PromotionWrite`` cannot be fabricated without the gate having run.
_GATE_TOKEN = object()


@dataclass(frozen=True)
class PromotionWrite:
    """The gated write: the promoted asset's claim set, minted once.

    Constructible **only** by :func:`promotion_claims` behind a permitted
    :func:`promotion_permitted` decision — any other construction raises at
    ``__post_init__``, so there is exactly one candidate→``PhysicalAsset``
    writer.
    """

    _gate_token: object = field(repr=False, compare=False)
    decision: PromotionDecision = field(compare=False)
    #: The promoted asset's ``sig.connector.subject`` value — the
    #: ``promoted:`` family the subject map declares ``physical_asset``.
    asset_subject: str = ""
    #: The promoted asset's ``confirmation_status`` (§11.8).
    confirmation_status: str = ""
    #: The claim records to hand the sink — the asset's existence (+
    #: location when the candidate carries an estimate) and the candidate's
    #: recorded ``candidate_promotion_status = promoted`` flip, each carrying
    #: ``derived_from_claim_ids`` naming the confirmation evidence.
    claims: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self._gate_token is not _GATE_TOKEN:
            raise TypeError(
                "PromotionWrite is minted only by promotion_claims() behind "
                "promotion_permitted() — the only candidate->PhysicalAsset "
                "writer (SIG-PUB-012)"
            )


def promotion_claims(
    candidate: CandidateForPromotion,
    *,
    source_id: str,
    license: str,
    attribution: str | None = None,
) -> PromotionWrite:
    """The only candidate→``PhysicalAsset`` writer (SIG-PUB-012).

    Emits the promoted asset's claim set — ``asset_exists_at_location`` on
    the new ``promoted:`` subject (a ``physical_asset`` by the committed
    subject map), ``fixed_asset_location`` when the candidate carries a
    location estimate, and the candidate's recorded
    ``candidate_promotion_status = promoted`` — every claim carrying the
    confirmation's claim ids as ``derived_from_claim_ids`` and the rule stamp
    in ``assertion_rationale``.

    Raises :class:`PromotionRefused` whenever :func:`promotion_permitted`
    refuses — a corroboration-only candidate mints nothing.
    """
    decision = promotion_permitted(candidate)
    if not decision.permitted:
        raise PromotionRefused(candidate, decision)

    subject = str(candidate.subject).strip()
    asset_subject = f"{PROMOTED_SUBJECT_PREFIX}{subject}"
    derived = sorted({c for conf in candidate.confirmations for c in conf.claim_ids})
    references = sorted({conf.reference.strip() for conf in candidate.confirmations})
    rationale = (
        f"{PROMOTION_RULE_VERSION}: §43.5 promotion of {subject!r} — "
        f"{decision.confirmation_status} via "
        + ",".join(sorted({conf.kind.value for conf in candidate.confirmations}))
        + f" confirmation ({'; '.join(references)})"
    )

    claims: list[dict[str, Any]] = [
        {
            "record_kind": "claim",
            "subject_id": asset_subject,
            "predicate_id": "asset_exists_at_location",
            "value": "true",
            "raw_value": "true",
            "derived_from_claim_ids": derived,
            "assertion_rationale": rationale,
            "source_id": source_id,
            "license": license,
        }
    ]
    if attribution:
        claims[0]["source_attribution"] = attribution
    if candidate.location_estimate_wkt:
        claims.append(
            {
                "record_kind": "claim",
                "subject_id": asset_subject,
                "predicate_id": "fixed_asset_location",
                "value": candidate.location_estimate_wkt,
                "raw_value": candidate.location_estimate_wkt,
                "derived_from_claim_ids": derived,
                "assertion_rationale": rationale,
                "source_id": source_id,
                "license": license,
            }
        )
    claims.append(
        {
            "record_kind": "claim",
            "subject_id": subject,
            "predicate_id": "candidate_promotion_status",
            "value": decision.resulting_status,
            "raw_value": decision.resulting_status,
            "derived_from_claim_ids": derived,
            "assertion_rationale": rationale,
            "source_id": source_id,
            "license": license,
        }
    )

    return PromotionWrite(
        _gate_token=_GATE_TOKEN,
        decision=decision,
        asset_subject=asset_subject,
        confirmation_status=decision.confirmation_status or "",
        claims=tuple(claims),
    )


__all__ = [
    "PROMOTED_SUBJECT_PREFIX",
    "PROMOTION_RULE_VERSION",
    "CandidateForPromotion",
    "Confirmation",
    "ConfirmationKind",
    "PromotionDecision",
    "PromotionRefusal",
    "PromotionRefused",
    "PromotionWrite",
    "promotion_claims",
    "promotion_permitted",
]
