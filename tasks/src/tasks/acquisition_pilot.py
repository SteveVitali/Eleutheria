# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The gap-closing acquisition pilot — batch selection, measurement and the
bounded-live gate packets (P32.21 / S5, SIG-ACQ-004).

This module is the *second stage* on top of the P32.11 reviewed queue
(:mod:`tasks.acquisition`): the queue produced fully-joined, gated, scored
candidate passports; the pilot selects a small first batch, measures the
capture → extraction → link → publication funnel and maintenance burden over
the committed dossier artifacts, emits exact gate packets for the bounded
live slices, and renders per-family continue / stop / improve
recommendations.

Contract of this stage (the ticket's bounded live stage):

* **Ceilings** — ≤2 incremental non-portfolio families, ≤10 approved
  documents/aggregate rows per family, ≤2 new protocol families, ≤5 total
  families *including the three pilot cities*. Family = the institutional
  provenance family (the queue's ``lineage_group``): the three dossier-city
  municipal groups are the portfolio slot.
* **No approval fabrication** — every rights lane in the queue is
  ``undetermined``; no approval reference exists anywhere in the batch.
  Every bounded live slice is recorded as a ``sig.acq-pilot-return-pass/1``
  gate packet pinned to an OPEN ``DEFERRALS.md`` row — fixture success can
  never close a live outcome.
* **Honest measurement** — funnel numbers derived from the committed dossier
  packets are *offline replay* measurements (committed stand-in fixtures),
  labelled as such; ``measured_minutes`` stays ``None`` (the ``CostRecord``
  rule) until an approved run supplies real minutes.
* **Descriptive only** — the preregistered S5 matched discovery comparison
  was not run; neither a before/after funnel nor a small exploratory
  comparison proves causal superiority. Every readout carries that label.

Nothing here fetches a URL, flips ``ingestion_permitted``, sends a records
request, spends money, or publishes. The acquired batch keeps rejected
metadata-only **SRC-027** outside it by construction.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .acquisition import (
    PreflightStatus,
    QueueDisposition,
    QueueEntry,
    RegistryRelation,
    rank_entries,
)

# --------------------------------------------------------------------------- #
# Versioned contract ids                                                      #
# --------------------------------------------------------------------------- #

#: The batch-selection artifact schema.
BATCH_SCHEMA = "acq-pilot-batch/1"
#: The funnel + maintenance measurement artifact schema.
FUNNEL_SCHEMA = "acq-pilot-funnel/1"
#: The before/after gap-ledger artifact schema.
GAP_LEDGER_SCHEMA = "acq-pilot-gap-ledger/1"
#: The bounded-live gate packet schema — sibling of
#: ``sig.dossier-live-return-pass/1``, scoped to the acquisition pilot.
RETURN_PASS_SCHEMA = "sig.acq-pilot-return-pass/1"
#: The full readout artifact schema.
READOUT_SCHEMA = "acq-pilot-readout/1"
#: The deterministic selection policy version.
SELECTION_VERSION = "acq-pilot-select/1"
#: The OPEN return-pass row this ticket owns for the two incremental live
#: slices (DEFERRALS.md; approval references do not exist).
PILOT_DEFERRAL = "D-P32.21-1"

#: Funnel stage order (S5 "Funnel that makes failure visible").
FUNNEL_STAGES = (
    "discovery",
    "candidate_qualification",
    "approval_gate",
    "capture",
    "extraction",
    "link_support",
    "publication_eligibility",
)

#: Bounded retries per live target before the target escalates to the records
#: channel — a budget, never a blind retry loop.
RETRY_BUDGET_PER_TARGET = 2

#: Predicate prefixes classifying the "structured acquisition/procurement"
#: shape (S5: "one structured funding/acquisition family").
_ACQUISITION_PREFIXES = ("contract.", "procurement.", "funding.")
#: Predicates classifying the "independent oversight" shape (S5: "one
#: independent oversight family").
_OVERSIGHT_PREFIXES = ("oversight.", "governance.", "agency.response", "usage.")
#: Predicates marking an award-discovery/funding family — admissible only when
#: a named local procurement has a traceable award gap (S5 precondition).
_AWARD_PREFIXES = ("funding.", "identity.recipient", "program.purpose")


class PilotError(ValueError):
    """Raised when the pilot inputs violate the batch contract."""


# --------------------------------------------------------------------------- #
# Ceilings + the fixed portfolio                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PilotCeilings:
    """The ticket's bounded live stage caps."""

    total_families: int = 5
    incremental_families: int = 2
    documents_per_family: int = 10
    new_protocol_families: int = 2


CEILINGS = PilotCeilings()


@dataclass(frozen=True)
class PortfolioDossier:
    """One pilot city — fixed by its landed dossier ticket, never re-selected.

    The portfolio slot measures the dossier family the S2 tickets built; its
    live slice is owned by that ticket's own OPEN return-pass deferral (this
    ticket *consumes* the packets, it does not re-issue them).
    """

    family_id: str
    label: str
    #: The bounded ``dossier_*`` source family the ticket introduced.
    source_family: str
    #: The municipal lineage group covering this city's candidate rows.
    lineage_group: str
    report_dir: str
    packet_name: str
    dossier_name: str
    return_pass_name: str
    return_pass_deferral: str
    #: Candidate ids inside the lineage group kept OUT of the acquired batch
    #: (SRC-027 is metadata-only, ``prohibited_until_review``).
    excluded_candidates: tuple[str, ...] = ()


PORTFOLIO: tuple[PortfolioDossier, ...] = (
    PortfolioDossier(
        family_id="okc",
        label="Oklahoma City",
        source_family="dossier_okc",
        lineage_group="okc-municipal",
        report_dir="docs/build/reports/p32.18-okc-dossier",
        packet_name="okc_dossier_packet.json",
        dossier_name="okc_dossier.json",
        return_pass_name="LIVE_RETURN_PASS.json",
        return_pass_deferral="D-P32.18-1",
    ),
    PortfolioDossier(
        family_id="tulsa",
        label="Tulsa",
        source_family="dossier_tulsa",
        lineage_group="tulsa-municipal",
        report_dir="docs/build/reports/p32.19-tulsa-dossier",
        packet_name="tulsa_dossier_packet.json",
        dossier_name="tulsa_dossier.json",
        return_pass_name="LIVE_RETURN_PASS.json",
        return_pass_deferral="D-P32.19-1",
    ),
    PortfolioDossier(
        family_id="san-diego",
        label="San Diego",
        source_family="dossier_san_diego",
        lineage_group="san-diego-municipal",
        report_dir="docs/build/reports/p32.20-san-diego-dossier",
        packet_name="san_diego_dossier_packet.json",
        dossier_name="san_diego_dossier.json",
        return_pass_name="LIVE_RETURN_PASS.json",
        return_pass_deferral="D-P32.20-1",
        excluded_candidates=("SRC-027",),
    ),
)


# --------------------------------------------------------------------------- #
# Selection                                                                   #
# --------------------------------------------------------------------------- #


class RejectReason(StrEnum):
    """The recorded reason a candidate sits outside the acquired batch."""

    #: Inside a pilot-city lineage group — measured under the dossier
    #: family's own return pass, never a new family.
    PORTFOLIO_MEMBER = "portfolio_member"
    #: Joined to a P31.12/.13-owned source — consumed/improved under prior
    #: decisions only, never re-onboarded.
    P31_OWNED = "p31_owned"
    #: Literal duplicate of a sibling candidate or a registered homepage.
    DUPLICATE = "duplicate"
    #: Rights/sensitive rejection — blocked regardless of usefulness.
    BLOCKED = "blocked"
    #: ``prohibited_until_review`` — metadata-only research path only
    #: (SRC-027's network-audit workbooks).
    PROHIBITED = "prohibited_metadata_only"
    #: ``screening_required`` — a Part VIII screen is owed work; an
    #: unscreened family cannot enter a bounded batch.
    SCREENING_OWED = "preflight_screening_owed"
    #: Award/funding family — the S5 precondition (a named local procurement
    #: with a traceable award gap) is not recorded in the dossier gap ledgers.
    AWARD_PRECONDITION = "no_recorded_award_gap"
    #: Neither pilot shape (acquisition / oversight) — a different gap class
    #: for a later batch; expansion is a new scope decision.
    SHAPE_NOT_TESTED = "outside_pilot_shapes"
    #: Eligible and in a pilot shape, but the two incremental slots are
    #: filled — ranked order decides; expansion is a new scope decision.
    CAPACITY = "capacity"


@dataclass(frozen=True)
class RejectedAlternative:
    """One candidate documented outside the acquired batch."""

    candidate_id: str
    family: str
    lineage_group: str
    score: int | None
    reason: RejectReason
    detail: str


@dataclass(frozen=True)
class FamilySelection:
    """One batch family — a portfolio slot or a selected incremental slot."""

    slot: str  # "portfolio" | "incremental"
    family_id: str
    lineage_group: str
    #: "contract/acquisition chain", "independent oversight", or the dossier
    #: city's municipal family.
    role: str
    #: Candidate ids whose targets are inside the acquired batch slice.
    candidate_ids: tuple[str, ...]
    #: Candidate ids inside the family kept outside the acquired batch.
    excluded_candidate_ids: tuple[str, ...]
    #: The recorded selection rule (P-SEL-*) behind this pick.
    rule: str
    rationale: str


@dataclass(frozen=True)
class PilotBatch:
    """The first batch: five families, every rejection recorded."""

    schema: str
    selection_version: str
    ceilings: PilotCeilings
    families: tuple[FamilySelection, ...]
    rejected: tuple[RejectedAlternative, ...]
    #: Computed ceiling values — checked against ``ceilings``.
    totals: Mapping[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "selection_version": self.selection_version,
            "ceilings": {
                "total_families": self.ceilings.total_families,
                "incremental_families": self.ceilings.incremental_families,
                "documents_per_family": self.ceilings.documents_per_family,
                "new_protocol_families": self.ceilings.new_protocol_families,
            },
            "totals": dict(self.totals),
            "families": [
                {
                    "slot": f.slot,
                    "family_id": f.family_id,
                    "lineage_group": f.lineage_group,
                    "role": f.role,
                    "candidate_ids": list(f.candidate_ids),
                    "excluded_candidate_ids": list(f.excluded_candidate_ids),
                    "rule": f.rule,
                    "rationale": f.rationale,
                }
                for f in self.families
            ],
            "rejected_alternatives": [
                {
                    "candidate_id": r.candidate_id,
                    "family": r.family,
                    "lineage_group": r.lineage_group,
                    "score": r.score,
                    "reason": r.reason.value,
                    "detail": r.detail,
                }
                for r in self.rejected
            ],
        }


def _entry_by_id(entries: Sequence[QueueEntry]) -> dict[str, QueueEntry]:
    return {e.passport.candidate_id: e for e in entries}


def _shape(entry: QueueEntry) -> str:
    """Classify a candidate into the pilot's two tested shapes."""
    preds = set(entry.passport.target_predicates)
    if any(pr.startswith(_OVERSIGHT_PREFIXES) for pr in preds):
        return "oversight"
    if any(pr.startswith(_ACQUISITION_PREFIXES) for pr in preds):
        return "acquisition"
    return "other"


#: Predicates that make a candidate an award-discovery/funding family —
#: admissible only when a named local procurement has a traceable award gap
#: (the S5 precondition). ``funding.channel``/``funding.review`` inside a
#: contract family do NOT mark one.
_AWARD_MARKERS = frozenset({"funding.award", "funding.program"})


def _is_award_family(entry: QueueEntry) -> bool:
    """Whether the candidate is an award-discovery/funding family whose S5
    precondition is a named local procurement with a traceable award gap."""
    return any(pr in _AWARD_MARKERS for pr in entry.passport.target_predicates)


def _rejection_reasons(
    entry: QueueEntry, portfolio_groups: frozenset[str]
) -> list[tuple[RejectReason, str]]:
    """Every reason a candidate sits outside the incremental pool.

    Reasons are ordered hard-gate-first; a candidate may carry several (all
    are recorded).
    """
    p = entry.passport
    out: list[tuple[RejectReason, str]] = []
    if entry.join.relation == RegistryRelation.P31_OWNED or any(
        ls.p31_owned for ls in entry.join.linked
    ):
        out.append(
            (
                RejectReason.P31_OWNED,
                "joins to a P31.12/.13-owned source — consumed/improved under "
                "prior decisions only, never re-onboarded (SIG-ACQ-004)",
            )
        )
    if entry.join.relation == RegistryRelation.DUPLICATE:
        out.append(
            (
                RejectReason.DUPLICATE,
                f"literal duplicate ({entry.join.duplicate_of or 'of a sibling/registered row'})"
                " — never onboarded twice",
            )
        )
    if entry.disposition == QueueDisposition.BLOCKED:
        out.append(
            (
                RejectReason.BLOCKED,
                "blocked disposition — rights/sensitive rejection is score-independent",
            )
        )
    if p.preflight.status == PreflightStatus.PROHIBITED_UNTIL_REVIEW:
        out.append(
            (
                RejectReason.PROHIBITED,
                "prohibited_until_review — metadata-only research path; an "
                "explicit content-admissibility + rights decision is owed "
                "before any acquisition",
            )
        )
    elif p.preflight.status == PreflightStatus.SCREENING_REQUIRED:
        out.append(
            (
                RejectReason.SCREENING_OWED,
                "Part VIII screening is owed work — an unscreened family "
                "cannot enter a bounded batch",
            )
        )
    if p.lineage_group in portfolio_groups:
        out.append(
            (
                RejectReason.PORTFOLIO_MEMBER,
                "inside a pilot-city lineage group — its targets ride the "
                "dossier family's own live return pass, never a new family",
            )
        )
    return out


def select_batch(
    entries: Sequence[QueueEntry],
    *,
    portfolio: Sequence[PortfolioDossier] = PORTFOLIO,
    ceilings: PilotCeilings = CEILINGS,
) -> PilotBatch:
    """Select the first batch deterministically — acq-pilot-select/1.

    Rules (recorded on every FamilySelection):

    * **P-SEL-1** — the three pilot-city dossier families occupy the
      portfolio slot verbatim (fixed by P32.18/.19/.20; never re-selected).
    * **P-SEL-2** — one "structured acquisition/procurement" incremental
      family: the highest-ranked eligible non-portfolio candidate whose
      predicates are contract/procurement (award-discovery families are
      excluded separately — the S5 precondition is unmet).
    * **P-SEL-3** — one "independent oversight" incremental family: the
      highest-ranked eligible non-portfolio candidate whose predicates are
      oversight/governance.
    * **P-SEL-4** — ceilings: ≤2 incremental families, ≤10 documents per
      family slice, ≤2 new protocol families, ≤5 families total. A violation
      raises — selection fails closed, never silently truncates.

    Ties/ordering use the queue's own rank order (score desc, research rank
    asc). Every non-selected candidate gets a recorded RejectedAlternative.
    """
    portfolio_groups = frozenset(pf.lineage_group for pf in portfolio)
    ranked = rank_entries(entries)
    rejected: list[RejectedAlternative] = []
    pool: list[QueueEntry] = []
    portfolio_members: dict[str, list[QueueEntry]] = {pf.lineage_group: [] for pf in portfolio}

    for e in ranked:
        p = e.passport
        reasons = _rejection_reasons(e, portfolio_groups)
        if reasons:
            for reason, detail in reasons:
                rejected.append(
                    RejectedAlternative(
                        candidate_id=p.candidate_id,
                        family=p.family,
                        lineage_group=p.lineage_group,
                        score=e.score_result.value,
                        reason=reason,
                        detail=detail,
                    )
                )
            if p.lineage_group in portfolio_groups:
                portfolio_members[p.lineage_group].append(e)
            continue
        if _is_award_family(e):
            rejected.append(
                RejectedAlternative(
                    candidate_id=p.candidate_id,
                    family=p.family,
                    lineage_group=p.lineage_group,
                    score=e.score_result.value,
                    reason=RejectReason.AWARD_PRECONDITION,
                    detail=(
                        "award/funding family — S5 admits one only when a named "
                        "local procurement has a traceable award gap; no dossier "
                        "gap ledger records one"
                    ),
                )
            )
            continue
        pool.append(e)

    # Portfolio slot — the three dossier-city families (P-SEL-1).
    families: list[FamilySelection] = []
    for pf in portfolio:
        members = portfolio_members[pf.lineage_group]
        in_batch = tuple(
            e.passport.candidate_id
            for e in members
            if e.passport.candidate_id not in pf.excluded_candidates
        )
        families.append(
            FamilySelection(
                slot="portfolio",
                family_id=pf.family_id,
                lineage_group=pf.lineage_group,
                role=f"{pf.label} dossier family ({pf.source_family})",
                candidate_ids=in_batch,
                excluded_candidate_ids=pf.excluded_candidates,
                rule="P-SEL-1",
                rationale=(
                    f"the {pf.label} dossier family is fixed by its landed S2 "
                    f"ticket — measured, never re-selected; live slice owned by "
                    f"{pf.return_pass_deferral}"
                ),
            )
        )

    # Incremental slots — one acquisition-shape + one oversight-shape family.
    # rank_entries order is score desc, research rank asc — first eligible
    # wins; a family already picked cannot fill the second slot too.
    picked_groups: set[str] = set()
    slot_specs = (
        (
            "acquisition",
            "contract/acquisition chain",
            "P-SEL-2",
            "the structured acquisition/procurement shape (S5) — contract/"
            "procurement-chain predicates, the relationship class a "
            "dossier's contract-chain gap needs",
        ),
        (
            "oversight",
            "independent oversight",
            "P-SEL-3",
            "the independent oversight shape (S5) — oversight/governance "
            "predicates yielding provenance distinct from municipal "
            "self-report",
        ),
    )
    for shape, role, rule, rationale in slot_specs:
        winner = next(
            (
                e
                for e in pool
                if _shape(e) == shape and e.passport.lineage_group not in picked_groups
            ),
            None,
        )
        if winner is None:
            continue
        group = winner.passport.lineage_group
        picked_groups.add(group)
        # The slice = the family's eligible members that fit the slot's shape
        # or carry a dossier-gap priority (a P0/P1 dossier gap inside a
        # selected provenance family always rides the slice); in-family
        # award/prohibited/off-shape members stay outside the acquired batch
        # and are named.
        slice_ids = tuple(
            e.passport.candidate_id
            for e in pool
            if e.passport.lineage_group == group
            and (_shape(e) == shape or "dossier" in e.passport.priority)
        )
        in_family_excluded = tuple(
            e.passport.candidate_id
            for e in ranked
            if e.passport.lineage_group == group and e.passport.candidate_id not in slice_ids
        )
        dossier_picks = [
            e.passport.candidate_id
            for e in pool
            if e.passport.lineage_group == group and "dossier" in e.passport.priority
        ]
        kind_note = (
            "an improvement under the registered "
            + next(
                (ls.source_id for ls in winner.join.linked if ls.link.kind.value == "same_source"),
                "existing",
            )
            + " row — a first-class acquisition"
            if winner.kind == "improvement"
            else "a net-new target — a new provenance family"
        )
        rationale_text = (
            f"{rationale}; {kind_note}; wins the {shape} slot under "
            f"acq-score/1 rank order (score {winner.score_result.value})"
            + (
                f"; closes recorded dossier gaps via {', '.join(dossier_picks)}"
                if dossier_picks
                else ""
            )
            + (
                f"; in-family excluded from the acquired batch: {', '.join(in_family_excluded)}"
                if in_family_excluded
                else ""
            )
        )
        families.append(
            FamilySelection(
                slot="incremental",
                family_id=group,
                lineage_group=group,
                role=role,
                candidate_ids=slice_ids,
                excluded_candidate_ids=in_family_excluded,
                rule=rule,
                rationale=rationale_text,
            )
        )

    # Every remaining pool candidate is a recorded rejection — capacity or
    # shape-not-tested, ranked order preserved.
    selected_ids = {cid for f in families for cid in f.candidate_ids}
    for e in pool:
        if e.passport.candidate_id in selected_ids:
            continue
        shape = _shape(e)
        if shape == "other":
            reason, detail = (
                RejectReason.SHAPE_NOT_TESTED,
                "a gap class outside the two tested pilot shapes (the "
                "highest-value rejected family — authority/program chains "
                "and local alternatives wait for a follow-on batch; "
                "expansion is a new scope decision)",
            )
        else:
            reason, detail = (
                RejectReason.CAPACITY,
                f"eligible {shape}-shape candidate outranked by the selected "
                "family under acq-score/1 rank order — the two incremental "
                "slots are full; expansion is a new scope decision",
            )
        rejected.append(
            RejectedAlternative(
                candidate_id=e.passport.candidate_id,
                family=e.passport.family,
                lineage_group=e.passport.lineage_group,
                score=e.score_result.value,
                reason=reason,
                detail=detail,
            )
        )

    incremental = sum(1 for f in families if f.slot == "incremental")
    totals = {
        "families": len(families),
        "incremental_families": incremental,
        "portfolio_families": len(families) - incremental,
    }
    batch = PilotBatch(
        schema=BATCH_SCHEMA,
        selection_version=SELECTION_VERSION,
        ceilings=ceilings,
        families=tuple(families),
        rejected=tuple(rejected),
        totals=totals,
    )
    violations = check_batch(batch, entries)
    if violations:
        raise PilotError("batch selection violates the contract: " + "; ".join(violations))
    return batch


def check_batch(batch: PilotBatch, entries: Sequence[QueueEntry]) -> list[str]:
    """The batch-contract invariants — a violation fails closed."""
    v: list[str] = []
    portfolio = [f for f in batch.families if f.slot == "portfolio"]
    incremental = [f for f in batch.families if f.slot == "incremental"]
    if len(batch.families) > batch.ceilings.total_families:
        v.append(f"{len(batch.families)} families > {batch.ceilings.total_families}")
    if len(incremental) > batch.ceilings.incremental_families:
        v.append(f"{len(incremental)} incremental families > {batch.ceilings.incremental_families}")
    if len(portfolio) != len(PORTFOLIO):
        v.append(f"portfolio must be exactly {len(PORTFOLIO)} families")
    groups = [f.lineage_group for f in batch.families]
    if len(groups) != len(set(groups)):
        v.append("two batch families share one lineage group")
    by_id = _entry_by_id(entries)
    for f in batch.families:
        for cid in f.candidate_ids:
            e = by_id.get(cid)
            if e is None:
                v.append(f"{cid}: selected candidate not in the queue")
                continue
            if e.join.relation == RegistryRelation.P31_OWNED or any(
                ls.p31_owned for ls in e.join.linked
            ):
                v.append(f"{cid}: P31-owned source cannot enter the batch")
            if e.join.relation == RegistryRelation.DUPLICATE:
                v.append(f"{cid}: duplicate cannot enter the batch")
            if e.disposition == QueueDisposition.BLOCKED:
                v.append(f"{cid}: blocked disposition cannot enter the batch")
            if e.passport.preflight.status in (
                PreflightStatus.PROHIBITED_UNTIL_REVIEW,
                PreflightStatus.SCREENING_REQUIRED,
                PreflightStatus.REJECTED,
            ):
                v.append(f"{cid}: preflight {e.passport.preflight.status.value} excludes it")
            if not e.passport.independent_yield:
                v.append(f"{cid}: non-independent lineage class cannot add lineage value")
    # SRC-027 can never be in the acquired batch anywhere.
    for f in batch.families:
        if "SRC-027" in f.candidate_ids:
            v.append("SRC-027 must stay outside the acquired batch")
    return v


# --------------------------------------------------------------------------- #
# Committed-artifact measurement                                              #
# --------------------------------------------------------------------------- #


def _repo_root() -> Path:
    """The repository root (tasks/src/tasks/acquisition_pilot.py → parents[3])."""
    return Path(__file__).resolve().parents[3]


# DEFERRALS row statuses (the build-memory audit's vocabulary) and the
# obligation-event register that records a status change with its evidence.
_OWED_STATUSES = frozenset({"OPEN", "PARTIAL"})
_CLOSED_STATUSES = frozenset({"DONE", "WONTFIX", "ACCEPTED-SKELETON"})
_EVENTS_REL = "docs/build/reports/obligations/events.jsonl"
_REGISTER_PREFIX = "docs/tickets/"


def _evidenced_closures(root: Path) -> dict[str, str]:
    """obligation id -> the status its latest obligation-event transition records,
    for transitions that cite at least one existing evidence ref outside the
    register (the register itself is the claim, not proof). Read-only."""
    path = root / _EVENTS_REL
    if not path.is_file():
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict) or ev.get("kind") != "transition":
            continue
        oid, seq = ev.get("obligation_id"), ev.get("seq")
        if not isinstance(oid, str) or not isinstance(seq, int):
            continue
        if oid not in latest or seq > latest[oid]["seq"]:
            latest[oid] = ev
    closures: dict[str, str] = {}
    for oid, ev in latest.items():
        refs = ev.get("evidence_refs")
        evidenced = isinstance(refs, list) and any(
            isinstance(r, str)
            and not r.startswith(_REGISTER_PREFIX)
            and (root / r.split("#", 1)[0]).is_file()
            for r in refs
        )
        if evidenced and isinstance(ev.get("to_status"), str):
            closures[oid] = ev["to_status"]
    return closures


def _load_json(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists():
        raise PilotError(f"committed artifact missing: {rel}")
    return json.loads(path.read_text())


@dataclass(frozen=True)
class DossierFacts:
    """The per-dossier measurements read from committed artifacts."""

    captures: int
    documents: tuple[str, ...]
    methods: tuple[str, ...]
    claims: int
    claims_by_source: Mapping[str, int]
    answer_states: Mapping[str, str]
    #: question slug -> sorted source ids asserting it.
    answer_sources: Mapping[str, tuple[str, ...]]
    #: question slug -> count of assertions.
    answer_assertions: Mapping[str, int]
    unique_to_family_slugs: tuple[str, ...]
    shared_slugs: tuple[str, ...]
    unique_assertions: int
    missing_questions: tuple[str, ...]
    follow_ups: int
    partial_or_unknown: tuple[str, ...]
    release_valid: bool
    release_violations: int
    mechanical_complete: bool
    pilot_complete: bool
    completeness_total: int
    completeness_max: int
    review_status: str
    return_pass_targets: int
    return_pass_deferral: str
    follow_up_drafts: int


def read_dossier_facts(pf: PortfolioDossier, *, root: Path | None = None) -> DossierFacts:
    """Measure one portfolio dossier from its committed artifacts only.

    Captures are *offline replay* counts — the packet's evidence_artifact and
    index_page records replay committed stand-in fixtures; no live byte was
    fetched. ``method=None`` index records are counted under ``index_page``.
    """
    base = root or _repo_root()
    packet = _load_json(base, f"{pf.report_dir}/{pf.packet_name}")
    dossier = _load_json(base, f"{pf.report_dir}/{pf.dossier_name}")
    return_pass = _load_json(base, f"{pf.report_dir}/{pf.return_pass_name}")

    captures = 0
    documents: set[str] = set()
    methods: set[str] = set()
    claims = 0
    claims_by_source: dict[str, int] = {}
    for rec in packet.get("records", []):
        kind = rec.get("record_kind")
        if kind in ("evidence_artifact", "index_page"):
            if rec.get("source_id") != pf.source_family:
                continue  # only this family's own bounded slice is counted
            captures += 1
            documents.add(str(rec.get("document_id")))
            methods.add(str(rec.get("method") or rec.get("record_kind")))
        elif kind == "claim":
            claims += 1
            src = str(rec.get("source_id"))
            claims_by_source[src] = claims_by_source.get(src, 0) + 1

    answer_states: dict[str, str] = {}
    answer_sources: dict[str, set[str]] = {}
    answer_assertions: dict[str, int] = {}
    # (slug, predicate, raw value) -> set of source families asserting it —
    # the uniqueness check runs at fact granularity, not claim ids (two
    # sources may emit the same fact with different claim digests).
    fact_sources: dict[tuple[str, Any, Any], set[str]] = {}
    for ans in dossier.get("answers", []):
        slug = str(ans.get("slug"))
        answer_states[slug] = str(ans.get("state"))
        srcs: set[str] = set()
        n = 0
        for assertion in ans.get("assertions", []):
            src = str(assertion.get("source_id"))
            srcs.add(src)
            n += 1
            key = (
                slug,
                assertion.get("predicate"),
                assertion.get("raw_value") or assertion.get("value"),
            )
            fact_sources.setdefault(key, set()).add(src)
        answer_sources[slug] = srcs
        answer_assertions[slug] = n

    fam = pf.source_family
    unique_slugs = tuple(sorted(s for s, srcs in answer_sources.items() if srcs == {fam}))
    shared_slugs = tuple(
        sorted(s for s, srcs in answer_sources.items() if fam in srcs and len(srcs) > 1)
    )
    unique_assertions = sum(1 for key, srcs in fact_sources.items() if srcs == {fam})
    missing = tuple(str(x) for x in dossier.get("missing_questions", []))
    partial = tuple(
        sorted(s for s, st in answer_states.items() if st in ("partial", "unknown", "unsupported"))
    )
    completeness = dossier.get("completeness", {})
    release = dossier.get("release", {})
    drafts_path = base / pf.report_dir / "FOLLOW_UP_DRAFTS.json"
    follow_up_drafts = 0
    if drafts_path.exists():
        drafts = json.loads(drafts_path.read_text())
        follow_up_drafts = len(drafts.get("drafts") or drafts.get("requests") or [])
    return DossierFacts(
        captures=captures,
        documents=tuple(sorted(documents)),
        methods=tuple(sorted(methods)),
        claims=claims,
        claims_by_source=claims_by_source,
        answer_states=answer_states,
        answer_sources={s: tuple(sorted(v)) for s, v in answer_sources.items()},
        answer_assertions=answer_assertions,
        unique_to_family_slugs=unique_slugs,
        shared_slugs=shared_slugs,
        unique_assertions=unique_assertions,
        missing_questions=missing,
        follow_ups=len(packet.get("follow_ups", [])),
        partial_or_unknown=partial,
        release_valid=bool(release.get("valid")),
        release_violations=len(release.get("violations") or []),
        mechanical_complete=bool(completeness.get("mechanical_complete")),
        pilot_complete=bool(completeness.get("pilot_complete")),
        completeness_total=int(completeness.get("total") or 0),
        completeness_max=int(completeness.get("max") or 0),
        review_status=str(dossier.get("review", {}).get("status", "not_run")),
        return_pass_targets=len(return_pass.get("targets", [])),
        return_pass_deferral=str(return_pass.get("deferral", pf.return_pass_deferral)),
        follow_up_drafts=follow_up_drafts,
    )


# --------------------------------------------------------------------------- #
# Funnel + maintenance burden                                                 #
# --------------------------------------------------------------------------- #


def _award_gap_evidence(pf: PortfolioDossier, root: Path) -> list[str]:
    """Evidence the dossier gap ledgers record no traceable award gap.

    Scans the recorded follow-ups, search log and follow-up drafts for
    award/grant/funding-gap language — the S5 precondition for a funding
    family. Returns the observed hits (expected: none that name an award
    chain).
    """
    packet = _load_json(root, f"{pf.report_dir}/{pf.packet_name}")
    hits: list[str] = []
    terms = ("award", "grant", "usaspending", "subaward")
    for fu in packet.get("follow_ups", []):
        text = f"{fu.get('action', '')} {fu.get('closing_condition', '')}".lower()
        if any(t in text for t in terms):
            hits.append(
                f"{pf.family_id}: follow-up mentions award terms: {fu.get('action', '')[:80]}"
            )
    drafts_path = root / pf.report_dir / "FOLLOW_UP_DRAFTS.json"
    if drafts_path.exists():
        drafts = json.loads(drafts_path.read_text())
        for d in drafts.get("drafts") or drafts.get("requests") or []:
            blob = json.dumps(d).lower()
            if any(t in blob for t in terms):
                hits.append(f"{pf.family_id}: a follow-up draft names award/funding terms")
    return hits


def family_funnel(
    batch: PilotBatch,
    entries: Sequence[QueueEntry],
    *,
    root: Path | None = None,
    portfolio: Sequence[PortfolioDossier] = PORTFOLIO,
) -> dict[str, Any]:
    """The per-family funnel + maintenance burden measurement.

    Every number carries its basis: ``offline_replay`` (committed stand-in
    fixtures through the real connector machinery) or ``research_estimate``
    (CSV/passport values). ``captured_live`` is 0 for every family — no live
    acquisition ran or is implied.
    """
    base = root or _repo_root()
    by_id = _entry_by_id(entries)
    pf_by_group = {pf.lineage_group: pf for pf in portfolio}

    families: dict[str, Any] = {}
    for fam_sel in batch.families:
        group = fam_sel.lineage_group
        group_entries = [e for e in entries if e.passport.lineage_group == group]
        refused = [
            e.passport.candidate_id
            for e in group_entries
            if e.disposition in (QueueDisposition.BLOCKED, QueueDisposition.REFUSED_DUPLICATE)
            or e.passport.preflight.status
            in (PreflightStatus.PROHIBITED_UNTIL_REVIEW, PreflightStatus.REJECTED)
        ]
        qualified = [
            e.passport.candidate_id for e in group_entries if e.passport.candidate_id not in refused
        ]
        undetermined_lanes = sum(
            len(tuple(e.passport.rights.lanes()))
            for e in group_entries
            if not e.passport.rights.decided()
        )
        if fam_sel.slot == "portfolio":
            pf = pf_by_group[group]
            facts = read_dossier_facts(pf, root=base)
            funnel = {
                "discovery": {
                    "candidates_researched": len(group_entries),
                    "urls_researched": sum(
                        bool(e.passport.discovery.primary_url)
                        + bool(e.passport.discovery.secondary_url)
                        for e in group_entries
                    ),
                    "basis": "offline_replay",
                },
                "candidate_qualification": {
                    "complete_passports": len(group_entries),
                    "qualified_for_review": qualified,
                    "hard_refused": refused,
                    "excluded_from_batch": list(fam_sel.excluded_candidate_ids),
                },
                "approval_gate": {
                    "approval_refs": [],
                    "decisions_recorded": 0,
                    "undetermined_rights_lanes": undetermined_lanes,
                    "live_slice": (
                        f"return pass {pf.return_pass_deferral} (OPEN, prepared_not_executed)"
                    ),
                },
                "capture": {
                    "documents": list(facts.documents),
                    "captures_offline_fixture": facts.captures,
                    "captured_live": 0,
                    "capture_methods": list(facts.methods),
                    "basis": "offline_replay — committed stand-in fixtures; never real bytes",
                },
                "extraction": {
                    "claims_emitted": facts.claims,
                    "claims_by_source": dict(facts.claims_by_source),
                    "basis": "offline_replay",
                },
                "link_support": {
                    "answers_supported": len(facts.answer_states),
                    "unique_supported_slugs": list(facts.unique_to_family_slugs),
                    "shared_slugs": list(facts.shared_slugs),
                    "unique_assertions": facts.unique_assertions,
                },
                "publication_eligibility": {
                    "dossier_release_valid": facts.release_valid,
                    "release_violations": facts.release_violations,
                    "mechanical_complete": facts.mechanical_complete,
                    "completeness": f"{facts.completeness_total}/{facts.completeness_max}",
                    "pilot_complete": facts.pilot_complete,
                    "review_status": facts.review_status,
                    "note": (
                        "a release-valid dossier is not a publication — no public exposure exists"
                    ),
                },
            }
            maintenance = {
                "target_count": facts.return_pass_targets,
                "target_note": f"live slice targets per {pf.return_pass_deferral}",
                "protocols": list(facts.methods),
                "protocol_count": len(facts.methods),
                "new_protocol_families": 0,
                "expected_refresh": _refresh_note(pf),
                "effort_owner": f"{pf.return_pass_deferral} + HG-03 operator review",
                "retry_budget": {
                    "per_target": RETRY_BUDGET_PER_TARGET,
                    "attempted": 0,
                    "recorded_failures": _recorded_failures(pf, base),
                },
                "blocked_or_deferred": {
                    "rights_lanes_undetermined": undetermined_lanes,
                    "preflight_exclusions": list(fam_sel.excluded_candidate_ids),
                    "review_status": facts.review_status,
                    "follow_up_drafts_not_sent": facts.follow_up_drafts,
                },
                "cost": {
                    "measured_minutes": None,
                    "measured_basis": (
                        "no approved run measured — an estimate is "
                        "never relabelled as a measurement"
                    ),
                    "one_time_setup": _family_effort(group_entries),
                    "recurring_maintenance": _refresh_note(pf),
                    "estimated_effort": _family_effort(group_entries),
                },
            }
        else:
            slice_entries = [by_id[cid] for cid in fam_sel.candidate_ids]
            lead = slice_entries[0]
            urls = [
                u
                for e in slice_entries
                for u in (
                    e.passport.discovery.primary_url,
                    e.passport.discovery.secondary_url,
                )
                if u
            ]
            expected_preds = sorted(
                {pr for e in slice_entries for pr in e.passport.target_predicates}
            )
            expected_gaps = [e.passport.gap for e in slice_entries]
            expected_missing = sorted({q for e in slice_entries for q in e.missing_questions})
            gates = sorted({g.value for e in slice_entries for g in e.gates})
            extra_questions = [q for e in slice_entries for q in e.passport.extra_questions]
            recorded_failures = [f for e in slice_entries for f in _entry_failures(e)]
            municipal = any(e.passport.rights.municipal_publication_observed for e in slice_entries)
            funnel = {
                "discovery": {
                    "candidates_researched": len(group_entries),
                    "urls_researched": len(urls),
                    "review_depths": {
                        e.passport.candidate_id: e.passport.discovery.review_status
                        for e in slice_entries
                    },
                    "basis": "research inventory — search/selected excerpts are leads, not review",
                },
                "candidate_qualification": {
                    "complete_passports": len(group_entries),
                    "qualified_for_review": qualified,
                    "hard_refused": refused,
                    "excluded_from_batch": list(fam_sel.excluded_candidate_ids),
                    "registry_join": lead.join.relation.value,
                    "kind": lead.kind,
                },
                "approval_gate": {
                    "approval_refs": [],
                    "decisions_recorded": 0,
                    "undetermined_rights_lanes": undetermined_lanes,
                    "gates": gates,
                    "live_slice": f"return pass {PILOT_DEFERRAL} (OPEN, prepared_not_executed)",
                },
                "capture": {
                    "targets": urls,
                    "document_cap": CEILINGS.documents_per_family,
                    "documents_in_slice": len(urls),
                    "captures_offline_fixture": 0,
                    "captured_live": 0,
                    "basis": "no capture — the live slice is a gate packet",
                },
                "extraction": {
                    "claims_emitted": 0,
                    "expected_predicates": expected_preds,
                    "basis": "none — pending the gated live slice",
                },
                "link_support": {
                    "answers_supported": 0,
                    "expected_gaps": expected_gaps,
                    "expected_missing_questions": expected_missing,
                    "status": "pending_live",
                },
                "publication_eligibility": {
                    "status": "not_assessed — pending acquisition + the §5 release gate",
                },
            }
            maintenance = {
                "target_count": len(urls),
                "protocols": ["html_text", "pdf_text"],
                "protocol_count": 2,
                "new_protocol_families": 0,
                "expected_refresh": _refresh_note(pf=None, passport=lead.passport),
                "effort_owner": f"{PILOT_DEFERRAL} + HG-03 operator review",
                "retry_budget": {
                    "per_target": RETRY_BUDGET_PER_TARGET,
                    "attempted": 0,
                    "recorded_failures": recorded_failures,
                },
                "blocked_or_deferred": {
                    "rights_lanes_undetermined": undetermined_lanes,
                    "gates": gates,
                    "extra_questions": extra_questions,
                    "municipal_rights_review": municipal,
                },
                "cost": {
                    "measured_minutes": None,
                    "measured_basis": (
                        "no approved run measured — an estimate is "
                        "never relabelled as a measurement"
                    ),
                    "one_time_setup": " / ".join(
                        sorted({e.passport.cost.estimated_effort for e in slice_entries})
                    ),
                    "recurring_maintenance": _refresh_note(pf=None, passport=lead.passport),
                    "estimated_effort": " / ".join(
                        sorted({e.passport.cost.estimated_effort for e in slice_entries})
                    ),
                    "estimated_basis": "; ".join(
                        f"{e.passport.candidate_id}: {e.passport.cost.estimated_basis}"
                        for e in slice_entries
                    ),
                },
            }
        families[fam_sel.family_id] = {
            "slot": fam_sel.slot,
            "role": fam_sel.role,
            "lineage_group": group,
            "candidate_ids": list(fam_sel.candidate_ids),
            "funnel": funnel,
            "maintenance": maintenance,
        }

    # Award-gap precondition evidence across the three gap ledgers.
    award_hits = [hit for pf in portfolio for hit in _award_gap_evidence(pf, base)]
    return {
        "schema": FUNNEL_SCHEMA,
        "stages": list(FUNNEL_STAGES),
        "basis": (
            "all capture/extraction counts derive from committed stand-in "
            "fixtures replayed through the real connector machinery — offline "
            "replay measurements; captured_live is 0 for every family; no "
            "fixture success closes a live outcome"
        ),
        "matched_comparison": (
            "not run — the preregistered S5 matched discovery comparison "
            "(two matched pairs, 30 min/arm, blinded error review) was not "
            "executed; all results below are descriptive only"
        ),
        "families": families,
        "rejected_families_still_visible": {
            "award_precondition_evidence": award_hits,
            "note": (
                "the dossier gap ledgers record no traceable award gap — "
                "the S5 funding-family precondition is unmet"
            )
            if not award_hits
            else "award-gap language found — re-examine funding-family exclusion",
        },
        "blocked_targets_visible": _blocked_targets(entries),
        "totals": {
            "families": len(families),
            "captured_live_all_families": 0,
            "measured_minutes": None,
        },
    }


def _family_effort(group_entries: Sequence[QueueEntry]) -> str:
    bands = [e.passport.cost.estimated_effort for e in group_entries]
    return " / ".join(sorted(set(bands))) if bands else "unknown"


def _refresh_note(pf: PortfolioDossier | None, passport: Any = None) -> str:
    if pf is not None:
        return {
            "okc": (
                "usage page volatile (the amendment 403 is recorded) — "
                "refresh on publish; council/contract documents are term-bound"
            ),
            "tulsa": (
                "policy PDFs + the MOU template — refresh on policy "
                "revision or instrument replacement"
            ),
            "san-diego": (
                "index listings volatile — refresh on publish; the ASR "
                "is annual; the PAB index on recommendation publication"
            ),
        }[pf.family_id]
    p = passport
    group = p.lineage_group
    if group == "oklahoma-state":
        return (
            "the statewide-contract index refreshes on posting/solicitation; "
            "the DAC program page on program change; the statute record is "
            "version-bound — a new version is a new document"
        )
    if group == "sourcewell-cooperative":
        return (
            "master contract is term-bound (112-page, current term) — "
            "refresh on re-solicitation; the index on posting"
        )
    if group == "california-state-auditor":
        return (
            "the 2019–2020 audit is a static historical baseline — the "
            "follow-up page refreshes on new agency responses"
        )
    return "refresh on publish (unmeasured — no approved run)"


def _recorded_failures(pf: PortfolioDossier, root: Path) -> list[str]:
    """Recorded target failures visible in the family's return pass."""
    rp = _load_json(root, f"{pf.report_dir}/{pf.return_pass_name}")
    out: list[str] = []
    for t in rp.get("targets", []):
        goal = str(t.get("goal", "")).lower()
        if "403" in goal or "over the byte bound" in goal or "16 mb" in goal:
            out.append(f"{t.get('doc_id')}: {t.get('goal', '')[:140]}")
        if "preflight" in str(t.get("kind", "")).lower():
            out.append(
                f"{t.get('doc_id')}: metadata-only preflight — never a workbook/row-level target"
            )
    return out


def _entry_failures(entry: QueueEntry) -> list[str]:
    """Recorded access failures on a candidate's passport."""
    p = entry.passport
    out: list[str] = []
    note = p.rights_access_unknowns.lower()
    if "403" in note:
        out.append(f"{p.candidate_id}: recorded 403 — {p.rights_access_unknowns[:120]}")
    return out


def _blocked_targets(entries: Sequence[QueueEntry]) -> list[dict[str, Any]]:
    """Every failed/403/rights-blocked/prohibited target kept visible with
    its reason and retry budget — the AC's visibility clause."""
    out: list[dict[str, Any]] = []
    for e in rank_entries(entries):
        p = e.passport
        reasons: list[str] = []
        if p.preflight.status == PreflightStatus.PROHIBITED_UNTIL_REVIEW:
            reasons.append("prohibited_until_review — metadata-only path only")
        if p.preflight.status == PreflightStatus.SCREENING_REQUIRED:
            reasons.append("screening_required — Part VIII screen owed")
        if e.disposition == QueueDisposition.BLOCKED:
            reasons.append("blocked — rights/sensitive rejection")
        if e.disposition == QueueDisposition.REFUSED_DUPLICATE:
            reasons.append("refused duplicate")
        if "403" in p.rights_access_unknowns.lower():
            reasons.append("recorded 403 on a prior retrieval")
        if not e.passport.rights.decided() and not reasons:
            n_lanes = len(tuple(p.rights.lanes()))
            reasons.append(f"rights undetermined ({n_lanes} lanes) — routed to review")
        if reasons:
            out.append(
                {
                    "candidate_id": p.candidate_id,
                    "family": p.family,
                    "lineage_group": p.lineage_group,
                    "reasons": reasons,
                    "retry_budget": RETRY_BUDGET_PER_TARGET,
                    "escalation": (
                        "recorded rights/operator decision or the records "
                        "channel — never a blind retry"
                    ),
                }
            )
    return out


# --------------------------------------------------------------------------- #
# Gate packets (bounded live slices)                                          #
# --------------------------------------------------------------------------- #


def return_pass_packet(batch: PilotBatch, entries: Sequence[QueueEntry]) -> dict[str, Any]:
    """``sig.acq-pilot-return-pass/1`` — the exact gate packet for the two
    incremental families' bounded live slices.

    Every slice carries preconditions, per-target goals, caps and explicit
    non-goals. ``approval_refs`` is EMPTY by construction — no approval
    reference exists; each slice is pinned to ``D-P32.21-1`` (OPEN), and the
    three portfolio slices stay pinned to their own deferrals.
    """
    by_id = _entry_by_id(entries)
    families: list[dict[str, Any]] = []
    for sel in batch.families:
        if sel.slot != "incremental":
            continue
        targets: list[dict[str, Any]] = []
        for cid in sel.candidate_ids:
            entry = by_id[cid]
            p = entry.passport
            urls = [u for u in (p.discovery.primary_url, p.discovery.secondary_url) if u]
            for i, url in enumerate(urls, 1):
                targets.append(
                    {
                        "doc_id": f"{cid.lower()}-target-{i}",
                        "candidate_id": cid,
                        "url": url,
                        "kind": "document_capture",
                        "goal": (
                            "bounded capture under HG-03 — actual bytes, locator + "
                            "capture digest; expected predicates: " + ", ".join(p.target_predicates)
                        ),
                    }
                )
        lead = by_id[sel.candidate_ids[0]]
        families.append(
            {
                "family": sel.lineage_group,
                "slot": "incremental",
                "kind": lead.kind,
                "candidate_ids": list(sel.candidate_ids),
                "excluded_candidate_ids": list(sel.excluded_candidate_ids),
                "registered_source": next(
                    (
                        ls.source_id
                        for ls in lead.join.linked
                        if ls.link.kind.value == "same_source"
                    ),
                    None,
                ),
                "document_cap": CEILINGS.documents_per_family,
                "protocols": ["html_text", "pdf_text"],
                "new_protocol_families": 0,
                "retry_budget_per_target": RETRY_BUDGET_PER_TARGET,
                "approval_refs": [],
                "targets": targets,
            }
        )
    return {
        "schema": RETURN_PASS_SCHEMA,
        "packet_id": "acq-pilot-p32.21-live-pass",
        "status": "prepared_not_executed",
        "deferral": PILOT_DEFERRAL,
        "reason_deferred": (
            "live_verification=false: D-R10-SOURCES-1 stays OPEN — every "
            "rights lane in the reviewed queue is undetermined and no approval "
            "reference exists for any bounded slice; HG-03 and the Part VIII "
            "preflight are operator preconditions"
        ),
        "preconditions": [
            "HG-03 exact-target source/rights review per target URL (the three "
            "rights lanes — raw document, fact extraction, derived publication — "
            "are separately decided; a state/local cooperative is not a federal "
            "public-domain assumption)",
            "Part VIII preflight per family — SRC-010/011 carry no flags but "
            "are status not_assessed; the screening must run before capture",
            "municipal-publication review where observed (both incremental "
            "families carry municipal_publication_observed)",
            "resource bounds identical to the replay path (html_text/pdf_text "
            "only, page/byte caps) — new protocol families: 0 of 2 allowed",
            "≤10 approved documents/aggregate rows per family; ≤2 incremental "
            "families; ≤5 families total — the caps are hard, expansion is a "
            "new scope decision",
        ],
        "non_goals": [
            "no source rights flip or ingestion_permitted change",
            "no operator-gate completion or fabricated approval ref",
            "no records request sent and no outreach",
            "no spending",
            "no publication or public release",
            "no broad blind crawler — targets are the reviewed URLs only",
            "no workbook/XLSX/ZIP/sharedStrings or row-level plate/person/query "
            "transport — SRC-027 stays metadata-only outside the acquired batch",
        ],
        "bounded_questions": [
            "SRC-010 (sourcewell-cooperative): does the master cooperative "
            "contract's master identifier → vendor → participation → ordering "
            "chain land as extractable contract predicates under the "
            "rights-reviewed slice (the contract back-chain the municipal "
            "packets only mirror)?",
            "SRC-011 (california-state-auditor): do the audit findings, agency "
            "survey answers and recommendations land as one-auditor-provenance "
            "independent oversight (respondent survey answers are never "
            "treated as independently verified)?",
        ],
        "families": families,
        "portfolio_return_passes": [pf.return_pass_deferral for pf in PORTFOLIO],
    }


# --------------------------------------------------------------------------- #
# Gap ledger — before/after unique contributions                              #
# --------------------------------------------------------------------------- #


def gap_ledger(
    batch: PilotBatch,
    entries: Sequence[QueueEntry],
    *,
    root: Path | None = None,
    portfolio: Sequence[PortfolioDossier] = PORTFOLIO,
) -> dict[str, Any]:
    """``acq-pilot-gap-ledger/1`` — the before/after reconciliation.

    *before* = the recorded gap state each family started from (the dossier's
    own what_we_dont_know / follow-ups for portfolio families; the passport's
    named gap for incrementals). *after* = what the batch uniquely closes —
    offline replay for the portfolio (assertion-level unique support per
    family), ``pending_live`` expectation for the incrementals. Reconciliation
    is exact: every supporting assertion maps to exactly one source family and
    unique + shared slugs partition the supported set — no gap is closed
    twice and no mirror counts as independent.
    """
    base = root or _repo_root()
    pf_by_group = {pf.lineage_group: pf for pf in portfolio}
    by_id = _entry_by_id(entries)

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    all_slugs: dict[str, set[str]] = {}
    for sel in batch.families:
        if sel.slot == "portfolio":
            pf = pf_by_group[sel.lineage_group]
            facts = read_dossier_facts(pf, root=base)
            before[pf.family_id] = {
                "state_before_batch": (
                    "dossier family bounded live slice unexecuted — "
                    "packet built on committed stand-ins"
                ),
                "missing_questions": list(facts.missing_questions),
                "partial_or_unknown": list(facts.partial_or_unknown),
                "follow_ups": facts.follow_ups,
                "review_status": facts.review_status,
            }
            after[pf.family_id] = {
                "supported_slugs": sorted(
                    s for s, st in facts.answer_states.items() if st in ("supported", "partial")
                ),
                "unique_supported_slugs": list(facts.unique_to_family_slugs),
                "shared_supported_slugs": list(facts.shared_slugs),
                "unique_assertions": facts.unique_assertions,
                "basis": "offline_replay — committed stand-in fixtures",
            }
            for slug, srcs in facts.answer_sources.items():
                all_slugs.setdefault(slug, set()).update(srcs)
        else:
            entry = by_id[sel.candidate_ids[0]]
            p = entry.passport
            before[sel.family_id] = {
                "named_gap": p.gap,
                "expected_missing_questions": list(entry.missing_questions),
                "content_window": p.content_window,
                "priority": p.priority,
            }
            after[sel.family_id] = {
                "supported_slugs": [],
                "unique_supported_slugs": [],
                "expected_unique_contribution": p.claims_supported,
                "expected_predicates": list(p.target_predicates),
                "status": (
                    "pending_live — the gated slice has not run; "
                    "expectations are never counted as closures"
                ),
            }

    supported = sorted(all_slugs)
    unique_total = sum(len(a["unique_supported_slugs"]) for a in after.values())
    return {
        "schema": GAP_LEDGER_SCHEMA,
        "before": before,
        "after": after,
        "reconciliation": {
            "supported_question_slugs": supported,
            "assertion_sources_partitioned_by_family": True,
            "unique_supported_total": unique_total,
            "double_counted": 0,
            "mirror_as_independent": 0,
            "p31_duplicate_onboarding": 0,
            "note": (
                "each supported slug's asserting source ids map to exactly one "
                "family bucket; a slug supported by multiple families is "
                "shared, never double-counted as unique; no batch family is a "
                "P31-owned source and no non-independent lineage class "
                "entered the batch"
            ),
        },
    }


# --------------------------------------------------------------------------- #
# Recommendations                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Recommendation:
    family_id: str
    verdict: str  # "continue" | "stop" | "improve"
    basis: str
    unique_closure: str
    cost_basis: str
    conditions: tuple[str, ...]
    stop_conditions: tuple[str, ...]


def recommend(
    batch: PilotBatch,
    entries: Sequence[QueueEntry],
    *,
    root: Path | None = None,
    portfolio: Sequence[PortfolioDossier] = PORTFOLIO,
) -> list[Recommendation]:
    """Per-family continue/stop/improve on unique supported gap closure + cost.

    Deterministic, descriptive only: portfolio verdicts follow the dossier's
    own completeness outcome; incremental verdicts weigh the unique
    relationship/provenance value against the recorded effort/access
    estimates. No verdict asserts causal superiority.
    """
    base = root or _repo_root()
    pf_by_group = {pf.lineage_group: pf for pf in portfolio}
    by_id = _entry_by_id(entries)
    out: list[Recommendation] = []
    for sel in batch.families:
        if sel.slot == "portfolio":
            pf = pf_by_group[sel.lineage_group]
            facts = read_dossier_facts(pf, root=base)
            verdict = "continue" if facts.mechanical_complete else "improve"
            if pf.family_id == "okc":
                unique = (
                    f"{facts.unique_assertions} unique assertions across "
                    f"{len(facts.answer_states)} questions — the scope partition, "
                    "the amendment's owned-vs-partner distinction, the announced "
                    "retention change and the memo's contract facts are nowhere "
                    "else in the corpus"
                )
            elif pf.family_id == "tulsa":
                unique = (
                    f"{facts.unique_assertions} unique assertions — the enacted "
                    "policies' terms and the template's honest present_but_empty "
                    "fields; the q5 contract-chain gate is unresolved by design"
                )
            else:
                unique = (
                    f"{facts.unique_assertions} unique assertions across "
                    f"{len(facts.answer_states)} questions — the subscription-vs-"
                    "hardware split, prime-vs-component roles and the proposed "
                    "recommendation are uniquely evidenced"
                )
            basis = (
                f"completeness {facts.completeness_total}/{facts.completeness_max}, "
                f"mechanical_complete={str(facts.mechanical_complete).lower()}, "
                f"release_valid={str(facts.release_valid).lower()}, "
                f"review={facts.review_status}; live slice owed by {pf.return_pass_deferral}"
            )
            conditions: tuple[str, ...] = (
                f"{pf.return_pass_deferral}: HG-03 per-target review then the bounded captures",
                "independent semantic review (D-R10-HUMAN-1) before pilot_complete can be claimed",
            )
            stop = (
                "any rights lane decided reject → stop the affected target",
                "a live capture contradicting the fixture replay → stop and re-review the packet",
                (
                    "if the records-channel follow-ups cannot resolve the "
                    "contract-chain gap after the bounded slice, stop expanding "
                    "this family (a scope decision)"
                ),
            )
            out.append(
                Recommendation(
                    family_id=pf.family_id,
                    verdict=verdict,
                    basis=basis,
                    unique_closure=unique,
                    cost_basis=(
                        f"committed: {facts.captures} captures / {facts.claims} claims "
                        f"/ {facts.return_pass_targets} return-pass targets; "
                        "measured_minutes none (no approved run)"
                    ),
                    conditions=conditions,
                    stop_conditions=stop,
                )
            )
        else:
            slice_entries = [by_id[cid] for cid in sel.candidate_ids]
            lead = slice_entries[0]
            p = lead.passport
            n_targets = sum(
                bool(e.passport.discovery.primary_url) + bool(e.passport.discovery.secondary_url)
                for e in slice_entries
            )
            if sel.family_id == "oklahoma-state":
                unique = (
                    "the batch's only family closing recorded OKC dossier "
                    "gaps from a non-municipal provenance — the OMES statewide "
                    "contract channel (q5 documentary leads) plus the DAC UVED "
                    "program/authority chain (q6, the P0-dossier gap); a state "
                    "record is not city self-report"
                )
                conditions = (
                    (
                        "HG-03: OMES portal access terms + state/vendor "
                        "document rights and the OSCN historical-version basis "
                        "reviewed"
                    ),
                    "Part VIII screening (status not_assessed) before capture",
                    (
                        "statute versions stay distinct — the DAC program "
                        "description is never legal adjudication, and no "
                        "universal OKCPD applicability is asserted"
                    ),
                )
            elif sel.family_id == "california-state-auditor":
                unique = (
                    "the batch's only non-municipal independent provenance "
                    "(I=3, a state auditor) — findings + agency survey + "
                    "recommendations give the CA portfolio city a governance "
                    "baseline no self-report can provide"
                )
                conditions = (
                    (
                        "HG-03: the report + survey pages' rights reviewed "
                        "(municipal/state publication is not auto-CC0)"
                    ),
                    (
                        "survey answers carry the Auditor's provenance as one "
                        "account — never independently verified respondent facts"
                    ),
                    "historical scope labelled (2019–2020 baseline, T=1) — never asserted current",
                )
            elif sel.family_id == "sourcewell-cooperative":
                unique = (
                    "the only batch family yielding cooperative contract → "
                    "vendor → participation → ordering relationships (R=3) — "
                    "the contract back-chain municipal packets only mirror; "
                    "an improvement under the registered sourcewell row"
                )
                conditions = (
                    (
                        "HG-03: Sourcewell (a Minnesota local government "
                        "unit) terms reviewed — not a federal public-domain "
                        "assumption; vendor exhibits separately assessed"
                    ),
                    "Part VIII screening (status not_assessed) before capture",
                    (
                        "a mirrored council packet is never corroboration — "
                        "preserve one origin contract + local addenda as "
                        "separate documents"
                    ),
                )
            else:
                unique = f"selected {sel.role} family — {p.gap}"
                conditions = (
                    "HG-03 exact-target review before any capture",
                    "Part VIII screening before capture",
                )
            stop = (
                "any rights lane decided reject → stop",
                "content-admissibility or screening failure → stop",
                (
                    "if the bounded slice costs beyond the recorded effort "
                    "band, stop and re-scope — expansion is a new scope decision"
                ),
            )
            out.append(
                Recommendation(
                    family_id=sel.family_id,
                    verdict="continue",
                    basis=(
                        f"acq-score/1 = {lead.score_result.value} "
                        f"({p.priority}), kind={lead.kind}, "
                        f"join={lead.join.relation.value}; effort "
                        f"{p.cost.estimated_effort} estimated (never measured); "
                        f"{len(sel.candidate_ids)} in-batch candidates "
                        f"({', '.join(sel.candidate_ids)})"
                        + (
                            f"; in-family excluded {', '.join(sel.excluded_candidate_ids)}"
                            if sel.excluded_candidate_ids
                            else ""
                        )
                    ),
                    unique_closure=unique,
                    cost_basis=(
                        f"{n_targets} targets / ≤{CEILINGS.documents_per_family} docs; "
                        f"effort {p.cost.estimated_effort}; measured_minutes none"
                    ),
                    conditions=conditions,
                    stop_conditions=stop,
                )
            )
    return out


# --------------------------------------------------------------------------- #
# Readout                                                                     #
# --------------------------------------------------------------------------- #


def pilot_readout(
    entries: Sequence[QueueEntry],
    *,
    root: Path | None = None,
    portfolio: Sequence[PortfolioDossier] = PORTFOLIO,
    ceilings: PilotCeilings = CEILINGS,
) -> dict[str, Any]:
    """The whole ``acq-pilot-readout/1`` record."""
    base = root or _repo_root()
    batch = select_batch(entries, portfolio=portfolio, ceilings=ceilings)
    funnel = family_funnel(batch, entries, root=base, portfolio=portfolio)
    ledger = gap_ledger(batch, entries, root=base, portfolio=portfolio)
    recs = recommend(batch, entries, root=base, portfolio=portfolio)
    packet = return_pass_packet(batch, entries)
    return {
        "schema": READOUT_SCHEMA,
        "selection_version": SELECTION_VERSION,
        "live_verification": False,
        "descriptive_only": (
            "the preregistered S5 matched discovery comparison was not run — "
            "every result is descriptive; neither a before/after funnel nor a "
            "small exploratory comparison proves causal superiority"
        ),
        "batch": batch.as_dict(),
        "funnel": funnel,
        "gap_ledger": ledger,
        "recommendations": [
            {
                "family_id": r.family_id,
                "verdict": r.verdict,
                "basis": r.basis,
                "unique_closure": r.unique_closure,
                "cost_basis": r.cost_basis,
                "conditions": list(r.conditions),
                "stop_conditions": list(r.stop_conditions),
            }
            for r in recs
        ],
        "return_pass": packet,
        "deferrals": {
            "opened": [PILOT_DEFERRAL],
            "consumed_portfolio": [pf.return_pass_deferral for pf in portfolio],
            "annotated": ["D-R10-SOURCES-1"],
        },
        "expansion": "any family beyond this batch is a new scope decision",
    }


def check_pilot(
    readout: Mapping[str, Any],
    entries: Sequence[QueueEntry],
    *,
    root: Path | None = None,
) -> list[str]:
    """The pilot's CI invariants — a violation means the readout is malformed."""
    v: list[str] = []
    batch = readout["batch"]
    ceilings = batch["ceilings"]
    fams = batch["families"]
    incremental = [f for f in fams if f["slot"] == "incremental"]
    if len(fams) > ceilings["total_families"]:
        v.append(f"{len(fams)} families > {ceilings['total_families']}")
    if len(incremental) > ceilings["incremental_families"]:
        v.append("incremental family cap exceeded")
    funnel_fams = readout["funnel"]["families"]
    for fid, fam in funnel_fams.items():
        m = fam["maintenance"]
        if (
            m["protocol_count"] > 0
            and m.get("new_protocol_families", 0) > ceilings["new_protocol_families"]
        ):
            v.append(f"{fid}: new protocol families over cap")
        funnel = fam["funnel"]
        if funnel["capture"]["captured_live"] != 0:
            v.append(f"{fid}: a live capture is claimed — none exists")
        docs = funnel["capture"].get("documents_in_slice")
        if docs is not None and docs > ceilings["documents_per_family"]:
            v.append(f"{fid}: {docs} documents > cap {ceilings['documents_per_family']}")
        if m["cost"]["measured_minutes"] is not None:
            v.append(f"{fid}: measured_minutes fabricated — no approved run")
    for f in fams:
        if "SRC-027" in f["candidate_ids"]:
            v.append("SRC-027 is inside the acquired batch — prohibited")
    rp = readout["return_pass"]
    if rp["status"] != "prepared_not_executed":
        v.append("return pass must be prepared_not_executed")
    if not readout["deferrals"]["opened"]:
        v.append("no OPEN return-pass row recorded for the live slices")
    # A named deferral is an explicit return-pass row only when the committed
    # register carries it — the check reads the register, never the readout's
    # own claim. The row's own leading status decides: OPEN/PARTIAL is the
    # owed home; a closed row (the return pass ran) passes only when its close
    # is recorded as an obligation-event transition citing evidence outside
    # the register — a closure typed into the cell alone is refused.
    base = root or _repo_root()
    deferrals_path = base / "docs/tickets/DEFERRALS.md"
    if not deferrals_path.exists():
        v.append("docs/tickets/DEFERRALS.md missing — cannot verify the OPEN rows")
    else:
        text = deferrals_path.read_text()
        closures = _evidenced_closures(base)
        for d in readout["deferrals"]["opened"] + readout["deferrals"]["consumed_portfolio"]:
            row = next(
                (ln for ln in text.splitlines() if ln.startswith(f"| {d} ")),
                None,
            )
            if row is None:
                v.append(f"{d}: no DEFERRALS.md row — the gate packet has no OPEN home")
                continue
            words = row.rsplit("|", 2)[-2].replace("*", " ").split()
            lead = words[0].upper() if words else ""
            if lead in _OWED_STATUSES:
                continue
            if lead not in _CLOSED_STATUSES:
                v.append(f"{d}: DEFERRALS.md row does not read OPEN (leads {lead!r})")
            elif closures.get(d) != lead:
                v.append(
                    f"{d}: DEFERRALS.md row leads {lead} without an evidence-backed "
                    f"transition in {_EVENTS_REL} — neither an OPEN home nor a recorded closure"
                )
    for fam in rp["families"]:
        if fam["approval_refs"]:
            v.append(f"{fam['family']}: an approval ref is claimed — none exists")
        if len(fam["targets"]) > fam["document_cap"]:
            v.append(f"{fam['family']}: targets over document cap")
    if not readout["descriptive_only"]:
        v.append("descriptive-only label missing")
    # P31 non-duplication across the whole batch.
    for f in fams:
        for cid in f["candidate_ids"]:
            e = next((x for x in entries if x.passport.candidate_id == cid), None)
            if e is not None and any(ls.p31_owned for ls in e.join.linked):
                v.append(f"{cid}: P31-owned join inside the batch")
    return v


def render_readout(readout: Mapping[str, Any]) -> str:
    """Render the human readout markdown."""
    batch = readout["batch"]
    funnel = readout["funnel"]
    ledger = readout["gap_ledger"]
    lines: list[str] = []
    lines.append("# P32.21 acquisition pilot — measured readout")
    lines.append("")
    lines.append(
        f"**Schemas:** `{BATCH_SCHEMA}` · `{FUNNEL_SCHEMA}` · `{GAP_LEDGER_SCHEMA}` · "
        f"`{RETURN_PASS_SCHEMA}` · `{READOUT_SCHEMA}` (selection `{SELECTION_VERSION}`)."
    )
    lines.append(
        "**`live_verification=false` — descriptive only:** the preregistered S5 "
        "matched discovery comparison was not run; every number derives from "
        "committed artifacts (offline replay) or the research inventory "
        "(estimates). `captured_live` is 0 for every family; `measured_minutes` "
        "is never fabricated; fixture success closes no live outcome. No causal "
        "superiority claim is made or implied."
    )
    lines.append("")
    lines.append("## Batch — five families under the live-stage ceilings")
    lines.append("")
    c = batch["ceilings"]
    t = batch["totals"]
    lines.append(
        f"Ceilings: ≤{c['total_families']} families (incl. the three pilot "
        f"cities) · ≤{c['incremental_families']} incremental non-portfolio "
        f"families · ≤{c['documents_per_family']} approved documents/aggregate "
        f"rows per family · ≤{c['new_protocol_families']} new protocol "
        f"families. **Observed:** {t['families']} families "
        f"({t['portfolio_families']} portfolio + {t['incremental_families']} "
        "incremental); ≤10 docs/family enforced per slice; 0 new protocols."
    )
    lines.append("")
    lines.append("| family | slot | role | candidates | excluded | rule |")
    lines.append("|---|---|---|---|---|---|")
    for f in batch["families"]:
        lines.append(
            f"| `{f['lineage_group']}` | {f['slot']} | {f['role']} | "
            f"{', '.join(f['candidate_ids']) or '—'} | "
            f"{', '.join(f['excluded_candidate_ids']) or '—'} | {f['rule']} |"
        )
    lines.append("")
    lines.append("## Rejected alternatives (all recorded)")
    lines.append("")
    lines.append("| candidate | family | score | reason |")
    lines.append("|---|---|---|---|")
    for r in batch["rejected_alternatives"]:
        lines.append(
            f"| `{r['candidate_id']}` | {r['family'][:52]} | "
            f"{r['score'] if r['score'] is not None else 'unscored'} | "
            f"{r['reason']} — {r['detail'][:110]} |"
        )
    lines.append("")
    lines.append("## Funnel + maintenance burden")
    lines.append("")
    lines.append("Stages: " + " → ".join(f"`{s}`" for s in funnel["stages"]) + ".")
    lines.append("")
    lines.append(
        "| family | captures (offline) | claims | unique assertions | "
        "docs/targets | protocols | verdict |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    rec_by_fam = {r["family_id"]: r for r in readout["recommendations"]}
    for fid, fam in funnel["families"].items():
        cap = fam["funnel"]["capture"]
        ex = fam["funnel"]["extraction"]
        link = fam["funnel"]["link_support"]
        m = fam["maintenance"]
        docs = cap.get("documents") or cap.get("targets") or []
        lines.append(
            f"| `{fid}` | {cap.get('captures_offline_fixture', 0)} (live 0) | "
            f"{ex.get('claims_emitted', 0)} | {link.get('unique_assertions', 'pending')} | "
            f"{len(docs)} / {m['target_count']} | {m['protocol_count']} "
            f"(new {m['new_protocol_families']}) | **{rec_by_fam[fid]['verdict']}** |"
        )
    lines.append("")
    lines.append(
        "Blocked / failed / rights-gated targets stay visible with reasons + retry budget:"
    )
    lines.append("")
    for b in funnel["blocked_targets_visible"]:
        lines.append(
            f"- `{b['candidate_id']}` ({b['lineage_group']}): "
            + "; ".join(b["reasons"])
            + f" — retry budget {b['retry_budget']}/target"
        )
    lines.append("")
    lines.append("## Before/after gap ledger — unique contributions")
    lines.append("")
    rec = ledger["reconciliation"]
    lines.append(
        f"{len(rec['supported_question_slugs'])} supported question slugs; "
        f"{rec['unique_supported_total']} supported solely by the portfolio "
        "dossier family; double-counted=0; mirror-as-independent=0; "
        "P31-duplicate-onboarding=0."
    )
    lines.append("")
    for fid, after in ledger["after"].items():
        if after.get("status"):
            lines.append(f"- `{fid}` — {after['status']}")
        else:
            lines.append(
                f"- `{fid}` — supports {len(after['supported_slugs'])} slugs "
                f"({len(after['unique_supported_slugs'])} unique, "
                f"{len(after['shared_supported_slugs'])} shared), "
                f"{after['unique_assertions']} unique assertions"
            )
    lines.append("")
    lines.append("## Recommendations (descriptive — no causal claim)")
    lines.append("")
    for r in readout["recommendations"]:
        lines.append(f"### `{r['family_id']}` → **{r['verdict']}**")
        lines.append("")
        lines.append(f"- basis: {r['basis']}")
        lines.append(f"- unique closure: {r['unique_closure']}")
        lines.append(f"- cost: {r['cost_basis']}")
        for cond in r["conditions"]:
            lines.append(f"- condition: {cond}")
        for cond in r["stop_conditions"]:
            lines.append(f"- stop if: {cond}")
        lines.append("")
    lines.append("## Gate packets / return pass")
    lines.append("")
    rp = readout["return_pass"]
    lines.append(
        f"`{rp['schema']}` `{rp['packet_id']}` — status `{rp['status']}`, "
        f"deferral **{rp['deferral']}** (OPEN). Approval refs: none exist "
        "(never fabricated). Portfolio slices stay pinned to "
        + ", ".join(rp["portfolio_return_passes"])
        + "."
    )
    lines.append("")
    lines.append("## Expansion")
    lines.append("")
    lines.append(
        "Any family beyond this batch is a **new scope decision** — "
        "the ceilings are hard, not soft targets."
    )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "BATCH_SCHEMA",
    "CEILINGS",
    "FUNNEL_SCHEMA",
    "FUNNEL_STAGES",
    "GAP_LEDGER_SCHEMA",
    "PILOT_DEFERRAL",
    "PORTFOLIO",
    "READOUT_SCHEMA",
    "RETURN_PASS_SCHEMA",
    "RETRY_BUDGET_PER_TARGET",
    "SELECTION_VERSION",
    "DossierFacts",
    "FamilySelection",
    "PilotBatch",
    "PilotCeilings",
    "PilotError",
    "PortfolioDossier",
    "Recommendation",
    "RejectReason",
    "RejectedAlternative",
    "check_batch",
    "check_pilot",
    "family_funnel",
    "gap_ledger",
    "pilot_readout",
    "read_dossier_facts",
    "recommend",
    "render_readout",
    "return_pass_packet",
    "select_batch",
]
