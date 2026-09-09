# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Small-cell disclosure control for the analytics boundary (§18.4).

The published usage aggregates (§11.16) describe *who searched whom*. A small
published cell can be two very different things, and the distinction is
load-bearing and easy to get backwards (SIG-STORE-032):

* a cell that would isolate one **individual's** vehicle movements — a Part VIII
  breach, MUST be suppressed (`protects_individual`); or
* a cell that describes an **institution's** conduct — "this agency ran 3
  immigration-reason searches" — which is exactly the accountability information
  the project exists to publish and MUST NOT be suppressed merely for being small
  (`institutional_conduct`).

This module is the single place that decision is made. It never returns a zero for
a suppressed cell (a zero is itself disclosive); a suppressed cell is published as
``count = None`` carrying ``suppressed_flag`` and the ``k_threshold`` that applied
(SIG-STORE-030). It applies **complementary (secondary) suppression** so a lone
suppressed cell is not recoverable by subtracting the published cells from a
published margin total (SIG-STORE-030). The k = 5 threshold is SIG's own
documented policy, not a claimed standard (SIG-STORE-033); a partner licence may
impose a stricter (larger) threshold, and the stricter one wins.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

# SIG-STORE-033: k = 5 is SIG's OWN documented policy (authoritative external
# small-cell thresholds could not be verified from a primary US federal source,
# R6-F46). Counts 1..k-1 (i.e. 1–4) are "small". Presented as policy, not a
# claimed standard, on the methodology page.
DEFAULT_K_THRESHOLD = 5

# SIG-STORE-030 / §18.4: the finest published time granularity is one month.
# A published period is a calendar month, ``YYYY-MM`` — never a finer instant.
_MONTH_PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SuppressionRationale(StrEnum):
    """Which §18.4 rationale governs a cell's publication (SIG-STORE-031)."""

    # A small cell could identify a private person or their movements → suppress.
    PROTECTS_INDIVIDUAL = "protects_individual"
    # The cell describes an organization's conduct → publish, even when small.
    INSTITUTIONAL_CONDUCT = "institutional_conduct"
    # The upstream licence forbids cell-level republication → suppress, cite rights.
    CONTRACTUAL = "contractual"
    # The two protected/institutional readings cannot be separated. The §18.4
    # default is to suppress AND raise a review task, never to publish (SIG-STORE-032).
    AMBIGUOUS = "ambiguous"
    # A *secondary* suppression applied only to keep another suppressed cell
    # non-invertible (SIG-STORE-030). Recorded distinctly so a suppressed cell is
    # never stamped with a "publish" rationale (e.g. institutional_conduct).
    COMPLEMENTARY = "complementary"


def effective_k_threshold(base_k: int = DEFAULT_K_THRESHOLD, partner_k: int | None = None) -> int:
    """The k that applies once a partner licence's threshold is considered.

    SIG-STORE-033: where a partner's licence imposes a different threshold, the
    **stricter** (larger — it suppresses more) applies. SIG's own k (default 5) is
    the floor.
    """
    if base_k < 1:
        raise ValueError(f"k threshold must be >= 1, got {base_k}")
    if partner_k is None:
        return base_k
    if partner_k < 1:
        raise ValueError(f"partner k threshold must be >= 1, got {partner_k}")
    return max(base_k, partner_k)


def is_small_cell(count: int, k: int = DEFAULT_K_THRESHOLD) -> bool:
    """Whether ``count`` is a small cell (1..k-1) under threshold ``k`` (SIG-STORE-030).

    Zero is not a "small cell": it is the absence of activity, handled by the
    coverage model, not disclosure control. A negative count is a data error.
    """
    if count < 0:
        raise ValueError(f"an aggregate count cannot be negative, got {count}")
    return 0 < count < k


def is_month_period(period: str) -> bool:
    """Whether ``period`` is a bare calendar month ``YYYY-MM`` (§18.4)."""
    return bool(_MONTH_PERIOD.match(period))


def assert_month_granularity(period: str) -> str:
    """Return ``period`` if it is month-granular, else raise (SIG-STORE-030/§18.4).

    A finer grain (a day, an instant) published for a usage aggregate would defeat
    small-cell suppression — daily counts are far more disclosive than monthly —
    so anything finer than one month is refused here, at the boundary.
    """
    if not is_month_period(period):
        raise ValueError(
            f"published aggregate period must be month-granular YYYY-MM (§18.4, "
            f"SIG-STORE-030); {period!r} is finer or malformed."
        )
    return period


@dataclass(frozen=True)
class Cell:
    """One aggregate cell entering disclosure control.

    ``count`` is the true (pre-suppression) count; ``rationale`` is the §18.4
    reading of *what a small value would reveal* for this cell (SIG-STORE-031).
    ``label`` is an opaque identity used only to report which cell a secondary
    suppression fell on; it never carries a name-joinable value.
    """

    label: str
    count: int
    rationale: SuppressionRationale
    rights_record: str | None = None


@dataclass(frozen=True)
class SuppressionDecision:
    """The disclosure-control verdict for one cell (SIG-STORE-030/031).

    A suppressed cell publishes ``published_count = None`` — **never zero** — plus
    ``suppressed_flag`` and the ``k_threshold`` that applied. ``rationale`` records
    which §18.4 reason drove the verdict. ``complementary`` marks a *secondary*
    suppression applied only to protect another cell from being inverted.
    """

    label: str
    published_count: int | None
    suppressed_flag: bool
    rationale: SuppressionRationale
    k_threshold: int
    review_task_required: bool = False
    complementary: bool = False
    rights_record: str | None = None

    @property
    def published(self) -> bool:
        """Whether this cell's true count is published."""
        return not self.suppressed_flag


@dataclass(frozen=True)
class GroupSuppressionResult:
    """The disclosure-control outcome for a group of cells sharing a margin total.

    ``margin_publishable`` is False when the margin (row/column total) MUST NOT be
    published because doing so would make a suppressed cell recoverable and no
    further complementary suppression could prevent it (e.g. a single-cell group).
    ``review_tasks`` are the human-review reasons the run must enqueue (SIG-STORE-032).
    """

    decisions: tuple[SuppressionDecision, ...]
    margin_publishable: bool
    review_tasks: tuple[str, ...]


def _primary_decision(cell: Cell, k: int) -> SuppressionDecision:
    """The per-cell verdict before complementary suppression (SIG-STORE-031/032)."""
    small = is_small_cell(cell.count, k)

    if cell.rationale is SuppressionRationale.INSTITUTIONAL_CONDUCT:
        # Accountability information about an institution: published even when
        # small. Suppressing it would defeat the project's purpose (SIG-STORE-032).
        return SuppressionDecision(
            label=cell.label,
            published_count=cell.count,
            suppressed_flag=False,
            rationale=cell.rationale,
            k_threshold=k,
        )

    if cell.rationale is SuppressionRationale.CONTRACTUAL:
        # The licence forbids cell-level republication regardless of size; cite
        # the rights record so the suppression is auditable.
        if not cell.rights_record:
            raise ValueError(
                f"a contractual suppression must cite a rights record (§18.4); "
                f"cell {cell.label!r} has none."
            )
        return SuppressionDecision(
            label=cell.label,
            published_count=None,
            suppressed_flag=True,
            rationale=cell.rationale,
            k_threshold=k,
            rights_record=cell.rights_record,
        )

    if cell.rationale is SuppressionRationale.PROTECTS_INDIVIDUAL:
        # Suppress only when small — a large count no longer isolates one person.
        if small:
            return SuppressionDecision(
                label=cell.label,
                published_count=None,
                suppressed_flag=True,
                rationale=cell.rationale,
                k_threshold=k,
            )
        return SuppressionDecision(
            label=cell.label,
            published_count=cell.count,
            suppressed_flag=False,
            rationale=cell.rationale,
            k_threshold=k,
        )

    # AMBIGUOUS: the two readings cannot be separated. The §18.4 default is to
    # suppress AND raise a review task — but only a small cell carries disclosure
    # risk; a large ambiguous cell is not a small-cell hazard and is published.
    if small:
        return SuppressionDecision(
            label=cell.label,
            published_count=None,
            suppressed_flag=True,
            rationale=cell.rationale,
            k_threshold=k,
            review_task_required=True,
        )
    return SuppressionDecision(
        label=cell.label,
        published_count=cell.count,
        suppressed_flag=False,
        rationale=cell.rationale,
        k_threshold=k,
    )


def _complementary_candidate(
    cells: Sequence[Cell],
    decisions: Sequence[SuppressionDecision],
) -> int | None:
    """Index of the cell to suppress secondarily, or None if none is suitable.

    Prefer a non-institutional published cell with the smallest count (least
    information lost, and never sacrifices accountability data if avoidable). Only
    fall back to an institutional cell when nothing else can absorb the secondary
    suppression — that fallback is flagged for review by the caller (SIG-STORE-032).
    """
    published = [i for i, d in enumerate(decisions) if not d.suppressed_flag]
    if not published:
        return None
    non_institutional = [
        i for i in published if cells[i].rationale is not SuppressionRationale.INSTITUTIONAL_CONDUCT
    ]
    pool = non_institutional or published
    return min(pool, key=lambda i: (cells[i].count, cells[i].label))


def suppress_group(
    cells: Sequence[Cell],
    *,
    k: int = DEFAULT_K_THRESHOLD,
    partner_k: int | None = None,
    margin_published: bool = True,
) -> GroupSuppressionResult:
    """Apply §18.4 disclosure control to a group of cells sharing a margin total.

    ``cells`` are the cells of one publishable margin — e.g. every
    ``reason_category`` for a fixed ``(searching_org, source_org, period)`` whose
    total SIG intends to publish. Primary suppression is applied per cell
    (SIG-STORE-031/032); then, if ``margin_published`` and exactly one cell is
    suppressed, **complementary suppression** removes a second cell so the first
    cannot be recovered by subtraction (SIG-STORE-030).

    Returns a :class:`GroupSuppressionResult`. ``margin_publishable`` is False when
    non-invertibility could not be achieved (a single-cell group whose only cell is
    suppressed): the caller must then withhold the margin total too.
    """
    k = effective_k_threshold(k, partner_k)
    decisions = [_primary_decision(c, k) for c in cells]
    review_tasks: list[str] = [
        f"ambiguous small cell {d.label!r}: suppressed by default, human review required "
        f"(SIG-STORE-032)"
        for d in decisions
        if d.review_task_required
    ]

    margin_publishable = True
    if margin_published:
        suppressed = [i for i, d in enumerate(decisions) if d.suppressed_flag]
        if len(suppressed) == 1:
            candidate = _complementary_candidate(cells, decisions)
            if candidate is None:
                # Nothing left to absorb a secondary suppression → the margin
                # itself would reveal the single suppressed cell. Withhold it.
                margin_publishable = False
                review_tasks.append(
                    f"cell {cells[suppressed[0]].label!r} is the only cell in its margin; "
                    f"margin total withheld to keep it non-invertible (SIG-STORE-030)"
                )
            else:
                if cells[candidate].rationale is SuppressionRationale.INSTITUTIONAL_CONDUCT:
                    review_tasks.append(
                        f"complementary suppression fell on institutional-conduct cell "
                        f"{cells[candidate].label!r}; confirm the accountability tradeoff "
                        f"(SIG-STORE-032)"
                    )
                # Stamp COMPLEMENTARY, not the cell's own rationale: a cell
                # suppressed only to protect another must never carry a "publish"
                # rationale (e.g. institutional_conduct) once it is null (SIG-STORE-031).
                decisions[candidate] = replace(
                    decisions[candidate],
                    published_count=None,
                    suppressed_flag=True,
                    complementary=True,
                    rationale=SuppressionRationale.COMPLEMENTARY,
                )

    return GroupSuppressionResult(
        decisions=tuple(decisions),
        margin_publishable=margin_publishable,
        review_tasks=tuple(review_tasks),
    )
