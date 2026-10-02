# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Count comparability scope (P32.3 / SIG-TRUST-004, ADR-122).

A count claim answers a question at a *scope*: "90 active cameras operated by
OKCPD inside city limits" is a different question from "299 devices mapped
across the metro". Comparing the two as one count is the same class of error as
conflating bases (§29.1 SIG-RECON-026/028) — the claims are retained and each
scope keeps its own answer, but they are **not** a contradiction and MUST NOT be
adjudicated against each other.

The model is deliberately small:

* :class:`CountScope` — the declared scope of one count claim: a ``label``
  (``metro`` / ``city_limits`` / ``statewide`` / …), an optional evidenced
  ``jurisdiction`` token, and an optional ``detail`` refinement
  (``privately_owned`` / ``partner_agency``). Scope is declared on the claim —
  carried as ``claim_qualifier`` rows on the spine — never inferred from the
  source (SIG-TRUST-004: comparability is scope-qualified, not guessed).
* :func:`compare_scope` — the three-way relation: ``SAME`` (comparable),
  ``DIFFERENT`` (declared scopes provably distinct → non-comparable, not a
  contradiction), ``UNKNOWN`` (a scope is undeclared → comparability cannot be
  established; non-comparable by default).
* :func:`partition_by_scope` — bucket a claim set by scope so contradiction
  detection runs *within* a scope only.
* :class:`DerivedApproximateSum` — an approximate roll-up like "~190" that a
  downstream consumer may build from scoped claims: it names its inputs and
  assumptions, is always L4, and can never be an observation (the
  :class:`reconcile.model.Inference` invariants — SIG-RECON-031 — applied to a
  count roll-up; SIG-DOS-003 requires labelling, not hiding, the ~190 sum).
"""

from __future__ import annotations

import enum
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "SCOPE_MIXED_CODE",
    "CountScope",
    "DerivedApproximateSum",
    "ScopeRelation",
    "compare_scope",
    "partition_by_scope",
    "scope_from_qualifiers",
    "scope_key",
]

#: The ``unresolved_code`` the §28 resolver emits for a scope-mixed count group
#: (the pair cannot be resolved to one value because its admissible claims
#: answer different questions). NOT a contradiction — the claims stay visible.
SCOPE_MIXED_CODE = "SCOPE_MIXED"

#: The claim_qualifier ids carrying count scope on the spine (P32.3); the same
#: ids are named in materialize.read_claim_groups and api.store_pg.
QUALIFIER_COUNT_SCOPE = "count_scope"
QUALIFIER_COUNT_SCOPE_DETAIL = "count_scope_detail"
QUALIFIER_EVIDENCE_ORIGIN = "evidence_origin"

#: The ``evidence_origin`` value marking seeded/fixture material — never
#: presented as primary live evidence (SIG-TRUST-004).
ORIGIN_SEED_FIXTURE = "seed_fixture"


@dataclass(frozen=True)
class CountScope:
    """The declared scope a count claim is asserted at.

    ``label`` is the scope class (``metro``/``city_limits``/``statewide``/…);
    ``jurisdiction`` is the evidenced jurisdiction token when the record carries
    one (``us.state_abbr:OK``, ``fr.insee:01``); ``detail`` refines the scope
    (``privately_owned``, ``partner_agency``). ``key()`` is the canonical
    comparability token — byte-equal keys are the *only* scopes that compare.
    """

    label: str
    jurisdiction: str | None = None
    detail: str | None = None

    def key(self) -> str:
        parts = [self.label.strip().lower()]
        if self.jurisdiction:
            parts.append(f"jur={self.jurisdiction.strip().lower()}")
        if self.detail:
            parts.append(f"detail={self.detail.strip().lower()}")
        return "|".join(parts)

    def label_text(self) -> str:
        """The human-readable scope for a dossier/API label."""
        out = self.label
        if self.detail:
            out = f"{self.detail} {out}"
        if self.jurisdiction:
            out = f"{out} ({self.jurisdiction})"
        return out


def scope_key(scope: CountScope | None) -> str:
    """The partition token for a scope; ``"unscoped"`` when none was declared."""
    return scope.key() if scope is not None else "unscoped"


class ScopeRelation(enum.StrEnum):
    """How two count claims' scopes relate (§29.1 extended, P32.3)."""

    #: Declared scopes equal — comparable; a value disagreement IS a contradiction.
    SAME = "same"
    #: Declared scopes provably distinct — non-comparable; NOT a contradiction
    #: (299 metro vs ~190 city is a scope mismatch, kept visible as such).
    DIFFERENT = "different"
    #: A scope is undeclared — comparability cannot be established, so the
    #: conservative read is non-comparable (never silently union scopes).
    UNKNOWN = "unknown"


def compare_scope(a: CountScope | None, b: CountScope | None) -> ScopeRelation:
    """The comparability relation between two claims' declared scopes."""
    if a is None or b is None:
        return ScopeRelation.UNKNOWN
    return ScopeRelation.SAME if a.key() == b.key() else ScopeRelation.DIFFERENT


def partition_by_scope(claims: Iterable[Any]) -> dict[str, list[Any]]:
    """Bucket claims by their ``.scope`` key (insertion order preserved).

    Every element must expose ``.scope`` (``CountScope | None``) — the partition
    runs contradiction/resolution logic per bucket so only same-scope claims
    ever compare.
    """
    out: dict[str, list[Any]] = {}
    for c in claims:
        out.setdefault(scope_key(getattr(c, "scope", None)), []).append(c)
    return out


def scope_from_qualifiers(
    qualifiers: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> CountScope | None:
    """Build a :class:`CountScope` from a claim's qualifier map/rows.

    Accepts either a mapping ``{qualifier_id: value}`` (the readers' shape) or
    the spine's row list (``{"qualifier_id": …, "value_text": …,
    "jurisdiction": …}``). Returns ``None`` when no ``count_scope`` qualifier is
    present — the claim's scope is undeclared (``UNKNOWN`` comparability).
    """
    label: str | None = None
    detail: str | None = None
    jurisdiction: str | None = None
    if isinstance(qualifiers, Mapping):
        label = _text(qualifiers.get(QUALIFIER_COUNT_SCOPE))
        detail = _text(qualifiers.get(QUALIFIER_COUNT_SCOPE_DETAIL))
        jurisdiction = _text(qualifiers.get("jurisdiction"))
    else:
        for row in qualifiers:
            qid = str(row.get("qualifier_id") or "")
            if qid == QUALIFIER_COUNT_SCOPE:
                label = _text(row.get("value_text") or row.get("value"))
                jurisdiction = _text(row.get("jurisdiction")) or jurisdiction
            elif qid == QUALIFIER_COUNT_SCOPE_DETAIL:
                detail = _text(row.get("value_text") or row.get("value"))
    if not label:
        return None
    return CountScope(label=label, jurisdiction=jurisdiction, detail=detail)


def _text(value: Any) -> str | None:
    s = str(value).strip() if value is not None else ""
    return s or None


@dataclass(frozen=True)
class DerivedApproximateSum:
    """An explicitly derived approximate roll-up of scoped count claims.

    The "~190" case (SIG-DOS-003): a figure a reader may *derive* by adding
    scoped values (``90 agency-active + ~100 privately-owned, both city
    limits``). It is NOT an observation:

    * :attr:`layer` is pinned ``"L4"`` and :attr:`is_observation` is always
      False — it MUST NOT be written into a resolved value, a claim, or an
      asset's ``operator`` (SIG-RECON-031);
    * :attr:`pushable_to_osm` is always False;
    * it names its inputs (the claim values it sums), its ``assumptions``
      (e.g. scopes are disjoint — double-counting is possible), and its
      ``approximate`` marker; the ``label`` is the display string ("~190")
      a surface MUST show instead of a bare integer.
    """

    subject_id: str
    basis: str  # the metric the roll-up reports (e.g. "derived_total")
    scope: CountScope | None  # the scope the inputs share (None = mixed/unknown)
    inputs: tuple[int, ...]
    input_bases: tuple[str, ...]
    label: str
    note: str = ""
    assumptions: tuple[str, ...] = ()
    approximate: bool = True

    layer: str = field(default="L4", init=False)
    pushable_to_osm: bool = field(default=False, init=False)

    @property
    def is_observation(self) -> bool:
        """A derived sum is never an observation (SIG-RECON-031)."""
        return False

    @property
    def value(self) -> int:
        return sum(self.inputs)

    def as_view(self) -> dict[str, object]:
        """The labelled view a dossier/API renders — never a bare number."""
        return {
            "label": self.label,
            "approximate": True,
            "derived": True,
            "layer": self.layer,
            "basis": self.basis,
            "scope": self.scope.label_text() if self.scope else None,
            "inputs": list(self.inputs),
            "input_bases": list(self.input_bases),
            "assumptions": list(self.assumptions),
            "note": self.note,
        }


def _base_key(scope: CountScope) -> str:
    """The scope key WITHOUT the sub-population detail (the roll-up scope)."""
    parts = [scope.label.strip().lower()]
    if scope.jurisdiction:
        parts.append(f"jur={scope.jurisdiction.strip().lower()}")
    return "|".join(parts)


def derive_approximate_sum(
    subject_id: str,
    claims: Sequence[Any],
    *,
    basis: str = "derived_total",
    label_prefix: str = "~",
    assumptions: Sequence[str] = (),
    note: str = "",
) -> DerivedApproximateSum:
    """Roll up same-scope count claims into a labelled derived sum.

    Only claims that share ONE declared scope — one ``label``+``jurisdiction``
    — may roll up (a mixed/undeclared scope raises ``ValueError`` — summing
    across scopes is the exact conflation this module exists to prevent). The
    inputs SHOULD name distinct sub-populations via ``detail`` (the "~190"
    city total adds the agency's ``active`` 90 and the privately-owned
    ``claimed`` ~100 — disjoint populations, one place): two inputs sharing a
    ``detail`` would be the same sub-population counted twice, and an
    undeclared ``detail`` cannot be proven disjoint — both refuse. The
    output scope is the shared scope with ``detail=None`` (the whole place).
    """
    if not claims:
        raise ValueError("a derived sum needs at least one input claim")
    scopes = [getattr(c, "scope", None) for c in claims]
    if any(s is None for s in scopes):
        raise ValueError("cannot sum counts whose scope is undeclared (comparability UNKNOWN)")
    typed: list[CountScope] = [s for s in scopes if s is not None]
    if len({_base_key(s) for s in typed}) != 1:
        raise ValueError(
            "cannot sum counts across scopes — partition_by_scope first "
            "(a cross-scope sum is a conflation, SIG-TRUST-004)"
        )
    details = [s.detail for s in typed]
    if len(claims) > 1:
        if any(d is None for d in details):
            raise ValueError(
                "cannot sum counts with an undeclared sub-population "
                "(detail=None cannot be proven disjoint, SIG-TRUST-004)"
            )
        if len(set(details)) != len(details):
            raise ValueError(
                "cannot sum the same sub-population twice "
                "(identical count_scope_detail — that is a contradiction set, not parts)"
            )
    first = typed[0]
    out_scope = CountScope(label=first.label, jurisdiction=first.jurisdiction)
    inputs = tuple(int(c.value) for c in claims)
    input_bases = tuple(str(getattr(c, "count_basis", "unknown")) for c in claims)
    return DerivedApproximateSum(
        subject_id=subject_id,
        basis=basis,
        scope=out_scope,
        inputs=inputs,
        input_bases=input_bases,
        label=f"{label_prefix}{sum(inputs)}",
        note=note
        or (
            f"derived sum of {len(inputs)} same-scope claims at scope "
            f"{out_scope.key()!r} (bases: {', '.join(sorted(set(input_bases)))})"
        ),
        assumptions=tuple(assumptions)
        or ("input scopes are disjoint populations (no device counted twice)",),
    )


__all__ = [
    "SCOPE_MIXED_CODE",
    "CountScope",
    "DerivedApproximateSum",
    "ScopeRelation",
    "compare_scope",
    "derive_approximate_sum",
    "partition_by_scope",
    "scope_from_qualifiers",
    "scope_key",
    "QUALIFIER_COUNT_SCOPE",
    "QUALIFIER_COUNT_SCOPE_DETAIL",
    "QUALIFIER_EVIDENCE_ORIGIN",
    "ORIGIN_SEED_FIXTURE",
]
