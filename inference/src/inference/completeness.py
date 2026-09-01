# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Completeness-estimation guardrails — and why capture–recapture is banned (§32.5).

SIG MUST NOT publish a capture–recapture estimate of device population from
volunteer mapping and vendor portal reporting — **not with a caveat, not with a
wide interval** (SIG-METRIC-008), and multi-list log-linear models MUST NOT be used
as a rescue (SIG-METRIC-008a). The Lincoln–Petersen estimator fails here on four
counts, the first dispositive: portals publish a *count, not an inventory*, so the
recapture overlap `m₂` is undefined. This module makes the prohibition executable:
the estimators are functions that always **refuse**, so the ban is a test, not a
code-review convention.

There is exactly one legitimate two-sample application (SIG-METRIC-008b): a
records-derived installation list *with locations* for one jurisdiction against a
**blind** field survey, understood and labelled as measuring **the field survey's
recall in that jurisdiction** — pre-registered, inside a window shorter than the
predicate's half-life, never extrapolated. :class:`RecordsDerivedRecall` is that
object, and it enforces every one of those constraints.

What SIG publishes instead (SIG-METRIC-009): counted quantities with **named
denominators** (see :mod:`inference.denominators`), records-derived **bounds**,
per-agency reconciliation ratios, and measured survey recall — **never a total**,
and never a completeness percentage that implies it knows the denominator of reality
(SIG-METRIC-010). :func:`assert_no_population_total` is the choke point for that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "ProhibitedEstimateError",
    "capture_recapture_population",
    "multi_list_log_linear_population",
    "CompletenessMethod",
    "CompletenessStatement",
    "assert_no_population_total",
    "RecordsDerivedRecall",
]


class ProhibitedEstimateError(RuntimeError):
    """A prohibited completeness/population estimate was attempted (§32.5)."""


def capture_recapture_population(*_args: object, **_kwargs: object) -> float:
    """Refuse a capture–recapture population estimate (SIG-METRIC-008).

    Always raises. Volunteer mapping and vendor portal reporting cannot support
    Lincoln–Petersen here: linkage is impossible (portals publish a count, not an
    inventory, so `m₂` is undefined), closure fails for a FAST predicate,
    independence fails in the direction that *understates* the population, and the
    blind spots are shared. Not with a caveat, not with a wide interval.
    """
    raise ProhibitedEstimateError(
        "capture–recapture population estimation is prohibited (SIG-METRIC-008): "
        "portals publish a count, not an inventory, so the recapture overlap is "
        "undefined; the estimator's known failure mode is understating the very "
        "thing SIG exists to document. Publish counted quantities with named "
        "denominators or records-derived bounds instead (SIG-METRIC-009)."
    )


def multi_list_log_linear_population(*_args: object, **_kwargs: object) -> float:
    """Refuse a multi-list log-linear population estimate (SIG-METRIC-008a).

    Always raises. Multi-list models require three or more lists with
    individual-level linkage and cannot identify the highest-order interaction —
    precisely the one that matters, since every available list shares a single
    latent "public visibility" factor.
    """
    raise ProhibitedEstimateError(
        "multi-list log-linear population estimation is prohibited as a rescue "
        "(SIG-METRIC-008a): the lists share a single latent visibility factor and "
        "the decisive highest-order interaction is unidentifiable."
    )


class CompletenessMethod(StrEnum):
    """The publishable completeness methods (SIG-METRIC-009). None is a total."""

    COUNTED_WITH_DENOMINATOR = "counted_with_denominator"
    RECORDS_DERIVED_BOUNDS = "records_derived_bounds"
    RECONCILIATION_RATIO = "reconciliation_ratio"
    MEASURED_SURVEY_RECALL = "measured_survey_recall"


# Tokens that betray an implied "denominator of reality" — forbidden (SIG-METRIC-010).
_REALITY_DENOMINATORS: frozenset[str] = frozenset(
    {"", "reality", "true population", "all devices", "total", "everything", "the world"}
)


@dataclass(frozen=True)
class CompletenessStatement:
    """A publishable completeness figure that cannot imply it knows reality (§32.5).

    Every statement MUST use one of the four :class:`CompletenessMethod`s, MUST name a
    concrete denominator (never "reality"/"true population", SIG-METRIC-010), and MUST
    publish its `violated_assumptions` — the AC is "publishes its violated
    assumptions, or is omitted", so the field is mandatory (empty means *none known*,
    which is itself a published claim). A population *total* has no valid method and
    cannot be constructed.
    """

    method: CompletenessMethod
    named_denominator: str
    value: float
    violated_assumptions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.method, CompletenessMethod):
            raise ValueError(f"unknown completeness method {self.method!r} (SIG-METRIC-009)")
        if self.named_denominator.strip().lower() in _REALITY_DENOMINATORS:
            raise ProhibitedEstimateError(
                f"named_denominator {self.named_denominator!r} implies a denominator of "
                "reality (SIG-METRIC-010); publish coverage of *known* entities with an "
                "explicit statement that the true population is unknown"
            )

    def as_json(self) -> dict[str, object]:
        return {
            "method": self.method.value,
            "named_denominator": self.named_denominator,
            "value": self.value,
            "violated_assumptions": list(self.violated_assumptions),
        }


def assert_no_population_total(statement: object) -> CompletenessStatement:
    """Refuse to publish anything that is not a denominated completeness statement.

    The choke point for SIG-METRIC-009/010: a bare number, or anything that is not a
    :class:`CompletenessStatement` with a named (non-reality) denominator, fails here
    rather than shipping as an implied population total.
    """
    if not isinstance(statement, CompletenessStatement):
        raise ProhibitedEstimateError(
            "a published completeness figure MUST be a CompletenessStatement with a "
            f"named denominator (SIG-METRIC-009/010), not a bare "
            f"{type(statement).__name__}: {statement!r}"
        )
    return statement


@dataclass(frozen=True)
class RecordsDerivedRecall:
    """The one legitimate two-sample estimate: field-survey recall (SIG-METRIC-008b).

    A records-derived installation list *with locations* for one jurisdiction, against
    a **blind** field survey of that jurisdiction, measuring **the survey's recall** —
    not the device population. §32.5 admits it only under every one of these
    conditions, each enforced in construction:

    * the inventory is **records-derived and carries locations** (`inventory_has_locations`)
      — a bare count is not a device-level inventory and cannot support linkage;
    * the field survey was **blind** to the inventory (`survey_blind`) — otherwise the
      two processes are not independent;
    * the exercise was **pre-registered** (`pre_registered`);
    * it ran inside a **window shorter than the predicate's half-life** (closure).

    It measures recall in *this named jurisdiction only* and MUST NOT be extrapolated:
    there is deliberately no method here that projects the recall onto any other
    jurisdiction or onto a population, and it publishes as method-recall, never a total.
    """

    jurisdiction_id: str
    predicate_id: str
    inventory_size: int
    survey_found_in_inventory: int
    pre_registered: bool
    window_days: float
    predicate_half_life_days: float
    inventory_has_locations: bool = True
    survey_blind: bool = True

    def __post_init__(self) -> None:
        if not self.pre_registered:
            raise ProhibitedEstimateError(
                "records-derived recall MUST be pre-registered (SIG-METRIC-008b); an "
                "unregistered exercise is not the legitimate application"
            )
        if not self.inventory_has_locations:
            raise ProhibitedEstimateError(
                "records-derived recall requires an inventory *with locations* "
                "(SIG-METRIC-008b); a bare count cannot support device-level linkage"
            )
        if not self.survey_blind:
            raise ProhibitedEstimateError(
                "records-derived recall requires a *blind* field survey (SIG-METRIC-008b); "
                "a sighted survey is not independent of the inventory"
            )
        if self.inventory_size <= 0:
            raise ValueError("records-derived recall needs a non-empty inventory (SIG-METRIC-008b)")
        if not (0 <= self.survey_found_in_inventory <= self.inventory_size):
            raise ValueError("survey_found_in_inventory out of range [0, inventory_size]")
        if self.window_days >= self.predicate_half_life_days:
            raise ProhibitedEstimateError(
                f"recall window {self.window_days}d is not shorter than the predicate "
                f"half-life {self.predicate_half_life_days}d (SIG-METRIC-008b): closure "
                "fails and the estimate is no longer defensible"
            )

    @property
    def recall(self) -> float:
        """The measured recall of the field survey in this jurisdiction."""
        return self.survey_found_in_inventory / self.inventory_size

    def statement(self) -> CompletenessStatement:
        """Publish as measured survey recall, denominated by the records inventory.

        Labelled as SIG's method-recall in a named jurisdiction — never extrapolated
        and never a population total (SIG-METRIC-008b/009).
        """
        return CompletenessStatement(
            method=CompletenessMethod.MEASURED_SURVEY_RECALL,
            named_denominator=(
                f"records-derived installation inventory for {self.jurisdiction_id}"
            ),
            value=self.recall,
            violated_assumptions=(),
        )
