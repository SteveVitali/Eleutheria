# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rationale generation from versioned templates (SIG-RECON-022/023).

Every resolution carries a human-readable rationale filled *only* from the
resolution's own structured fields, from a template in the versioned ruleset
(:mod:`reconcile.ruleset`). The target is that a journalist can quote it verbatim
without adding interpretation; :func:`check_template` is the mechanical form of
that guarantee and is what the committed template test asserts over every
template (SIG-RECON-023): (a) no unresolved placeholder; (b) names a source or a
named rule; (c) every value is attributed to a source or a named rule; (d) no
support term and agreement term in the same sentence (SIG-EPIS-025); (e) no
evaluative adjective from the style guide's prohibited list (§41).
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from .ruleset import Ruleset

if TYPE_CHECKING:  # pragma: no cover
    from .resolve import Candidate

_DAYS_PER_MONTH = 30.4375

#: Phrases that count as naming a rule for clauses (b)/(c) — the resolution's own
#: named rule is a legitimate attribution when there is no source to cite.
_RULE_PHRASES = (
    "ruleset",
    "lower bound",
    "does not adjudicate",
    "cannot be compared",
    "not-safe-to-publish",
    "no admissible source",
    "as of",
    "reported by",
    "mapped by",
    "rests on",
    "record",
)

#: Placeholders whose fills are values that clause (c) requires be attributed.
_VALUE_PLACEHOLDERS = ("{value}", "{dissent_value}")
#: Placeholders / phrases that constitute an attribution in the same sentence.
_ATTRIBUTION_TOKENS = (
    "{source}",
    "{dissent_source}",
    "{methods}",
    "as of",
    "reported by",
    "mapped by",
    "rests on",
    "record",
)


def _label(predicate_id: str) -> str:
    return predicate_id.replace("_", " ")


def _fmt(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _source_of(cand: Candidate | None) -> str:
    if cand is None:
        return "an unnamed source"
    ev = cand.representative.evidence
    if ev is not None and ev.source_family:
        return ev.source_family
    return cand.representative.source_id or "an unnamed source"


def _months_between(earlier: date, later: date) -> int:
    return max(0, round((later - earlier).days / _DAYS_PER_MONTH))


def _human_duration_months(months: int) -> str:
    if months >= 24 and months % 12 == 0:
        return f"{months // 12} years"
    return f"{months} months"


def _human_half_life(half_life: str) -> str:
    hl = half_life.strip().lower()
    if hl in {"infinite", "inf"}:
        return "indefinitely"
    if hl.endswith("mo"):
        return f"{hl[:-2]} months"
    if hl.endswith("y"):
        return f"{hl[:-1]} years"
    return hl


def _select_code(
    status: str, code: str | None, predicate_id: str, support: str, has_dissent: bool
) -> str:
    if status == "RESOLVED":
        if support == "CONFIRMED" and has_dissent is False:
            # multiple independent classes on ONE value -> the "confirmed" template.
            return "RESOLVED_CONFIRMED_MULTI"
        if predicate_id == "mapped_device_count":
            return "RESOLVED_LOWER_BOUND"
        if support == "CONFIRMED":
            return "RESOLVED_CONFIRMED_MULTI"
        return "RESOLVED_OVER_DISSENT" if has_dissent else "RESOLVED_DIRECT"
    return {
        "U0": "UNRESOLVED_NO_EVIDENCE",
        "U1": "UNRESOLVED_WEAK",
        "U2": "UNRESOLVED_STANDOFF",
        "U3": "UNRESOLVED_STANDOFF",
        "U4": "UNRESOLVED_SPREAD",
        "U5": "UNRESOLVED_STALE",
        "U6": "UNRESOLVED_CONFLATION",
        "U7": "UNRESOLVED_BLOCKING",
        "U8": "UNRESOLVED_IRRECONCILABLE",
        "NO_STRATEGY": "UNRESOLVED_NO_STRATEGY",
        "NEVER_RESOLVE": "UNRESOLVED_NO_STRATEGY",
    }[code or "U0"]


def render_rationale(
    *,
    ruleset: Ruleset,
    status: str,
    code: str | None,
    predicate_id: str,
    support: str,
    winner: Candidate | None,
    second: Candidate | None,
    as_of_world: date,
) -> tuple[str, str]:
    """Return ``(rationale_code, rationale_text)`` for a resolution (SIG-RECON-022)."""
    has_dissent = second is not None
    rationale_code = _select_code(status, code, predicate_id, support, has_dissent)
    template = ruleset.template(rationale_code)

    label = _label(predicate_id)
    fill: dict[str, object] = {"predicate_label": label}
    if winner is not None:
        rep = winner.representative
        fill.update(
            value=_fmt(winner.value),
            source=_source_of(winner),
            observed_at=rep.observed_at.isoformat(),
            n_classes=len(winner.supporting_class_ids),
            methods=", ".join(dict.fromkeys(winner.class_methods)),
            last_known_date=rep.observed_at.isoformat(),
        )
        months = _months_between(rep.observed_at, as_of_world)
        fill["age_human"] = _human_duration_months(months)
        fill["half_life_human"] = _human_half_life(ruleset.half_life(predicate_id))
    if second is not None:
        fill.update(
            dissent_value=_fmt(second.value),
            dissent_source=_source_of(second),
            dissent_observed_at=second.representative.observed_at.isoformat(),
        )
    text = template.format_map(_SafeFill(fill))
    return rationale_code, text


class _SafeFill(dict):  # type: ignore[type-arg]
    """A format mapping that leaves a marker for a genuinely-missing key so a
    template/field mismatch surfaces as a visible placeholder the test catches
    rather than a crash mid-render."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


# --- the committed template checks (SIG-RECON-023) ---------------------------


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.])\s+", text) if s.strip()]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z-]*", text.lower()))


def check_template(ruleset: Ruleset, rationale_code: str, rendered: str, raw: str) -> list[str]:
    """Return the list of clause violations for one rendered template (empty = ok).

    ``rendered`` is the template filled with a representative complete example;
    ``raw`` is the unfilled template (clause (c) is checked structurally on it).
    """
    problems: list[str] = []

    # (a) no unresolved placeholder.
    if "{" in rendered or "}" in rendered:
        problems.append(f"{rationale_code}: (a) unresolved placeholder in rendered text")

    # (b) names at least one source, or a named rule. A template that references
    # a source placeholder names a source even if the word "source" is absent.
    low = rendered.lower()
    names_source = (
        "source" in low
        or any(p in low for p in _RULE_PHRASES)
        or any(tok in raw for tok in ("{source}", "{dissent_source}", "{methods}"))
    )
    if not names_source:
        problems.append(f"{rationale_code}: (b) names no source and no rule")

    # (c) every value is attributed within its sentence.
    for sentence in _sentences(raw):
        if any(v in sentence for v in _VALUE_PLACEHOLDERS):
            if not any(tok in sentence for tok in _ATTRIBUTION_TOKENS):
                problems.append(f"{rationale_code}: (c) unattributed value in: {sentence!r}")

    # (d) no support term and agreement term in the same sentence.
    support = set(ruleset.support_terms)
    agreement = set(ruleset.agreement_terms)
    for sentence in _sentences(rendered):
        words = _words(sentence)
        if (words & support) and (words & agreement):
            problems.append(
                f"{rationale_code}: (d) support+agreement in one sentence: {sentence!r}"
            )

    # (e) no prohibited evaluative adjective (§41).
    banned = _words(rendered) & set(ruleset.prohibited_adjectives)
    if banned:
        problems.append(f"{rationale_code}: (e) prohibited adjective(s) {sorted(banned)}")

    return problems


#: A representative complete fill covering every placeholder any template uses —
#: the committed template test renders each template with this and runs the
#: clause checks (SIG-RECON-023).
REPRESENTATIVE_FILL: dict[str, object] = {
    "value": 38,
    "source": "the agency transparency portal",
    "observed_at": "2026-07-15",
    "predicate_label": "active device count",
    "dissent_value": 42,
    "dissent_source": "the executed contract",
    "dissent_observed_at": "2025-04-03",
    "n_classes": 3,
    "methods": "an executed contract, council minutes, and a vendor press release",
    "age_human": "31 months",
    "half_life_human": "6 months",
    "last_known_date": "2024-01-12",
}


def render_representative(ruleset: Ruleset, rationale_code: str) -> str:
    """Render one template with :data:`REPRESENTATIVE_FILL` (for the template test)."""
    return ruleset.template(rationale_code).format_map(_SafeFill(REPRESENTATIVE_FILL))


__all__ = [
    "REPRESENTATIVE_FILL",
    "check_template",
    "render_rationale",
    "render_representative",
]
