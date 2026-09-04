# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §28 reconciliation resolver — the intellectual core (SIG-RECON-004..025).

``RESOLVE(subject, predicate, as_of_world, as_of_belief, ruleset)`` runs a fixed
phase pipeline (Phase 0 GATHER → 1 ADMISSIBILITY → 2 CANONICALIZE → 3 WEIGHT →
4 INDEPENDENCE → 5 STRATEGY → 6 AMBIGUITY → 7 EMIT) over the claims about one
``(subject, predicate)`` pair (SIG-RECON-006). It is deterministic and
rule-based: every output traces to a named rule, there is **no random tie-break
anywhere** (SIG-RECON-007), and the whole decision is reproducible from
``(claims + ruleset_version + resolver_version + as_of pair)`` via the emitted
``input_digest`` (SIG-RECON-020).

The ruleset is data (:mod:`reconcile.ruleset`, SIG-RECON-005); the composed
weight ``W`` and query-time currency ``C`` are :mod:`reconcile.weight`. The
rationale is generated from a versioned template (:mod:`reconcile.rationale`,
SIG-RECON-022). A human MAY override the result, but the override never hides the
algorithmic answer (:func:`pin`, SIG-RECON-024/025).

This module *emits* contradictions and an ``input_digest``; the materialized
``Contradiction`` entity and the byte-identical L3 rebuild are P08.3 (§31, §28.7).
LLMs MUST NOT resolve contradictions or produce confidence (§25.2): nothing here
calls a model.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import cast

from .model import Contradiction, Evidence
from .rationale import render_rationale
from .ruleset import Ruleset, load_ruleset
from .weight import (
    DirectnessExcluded,
    currency,
    directness_for,
    weight_class,
)

RESOLVER_VERSION = "p08.1/1.0.0"

#: Human currency labels for the four currency classes (§10.7).
_CURRENCY_LABEL: dict[str, str] = {
    "C1": "CURRENT",
    "C2": "AGING",
    "C3": "STALE",
    "C4": "HISTORICAL",
}

_RETRACTED = frozenset({"retracted", "withdrawn"})


# --- inputs ------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """One admissible-or-not assertion about a ``(subject, predicate)`` pair.

    The epistemic axes are declared, never inferred: ``reliability`` is the
    source-registry ``R`` (§10.4), ``integrity`` the mechanical ``I`` (§10.6),
    ``genre`` selects the directness ``D`` from the published matrix (§10.5), and
    currency ``C`` is derived at query time from ``observed_at`` (§28.3).
    Dependence is declared too (``independence_class`` / ``derived_from_source``,
    §10.8): copying is stated, not guessed.
    """

    claim_id: str
    subject_id: str
    predicate_id: str
    value: object
    reliability: str
    integrity: str
    genre: str
    observed_at: date
    raw_value: str = ""
    valid_from: date | None = None
    valid_to: date | None = None
    review_status: str = "active"
    independence_class: str | None = None
    collection_method: str | None = None
    derived_from_source: str | None = None
    derived_from_claim_ids: tuple[str, ...] = ()
    source_id: str = ""
    #: Ascending registry rank for the universal tie-break (SIG-RECON-007). When
    #: unset it defaults to the numeric of the reliability code (R1 -> 1).
    source_registry_rank: int | None = None
    structured_exact: bool = False
    field_verified: bool = False
    #: Set for count predicates so Phase 2.3 can refuse cross-basis comparison.
    count_basis: str | None = None
    #: A windowed predicate value (e.g. "412 searches in July") is *indexed*, not
    #: stale, and is exempt from currency downgrade for its window (SIG-RECON-011).
    windowed: bool = False
    content_hash: str = ""
    evidence: Evidence | None = None

    @property
    def rank(self) -> int:
        if self.source_registry_rank is not None:
            return self.source_registry_rank
        try:
            return int(self.reliability[1:])
        except (ValueError, IndexError):
            return 99

    @property
    def class_id(self) -> str:
        """The independence class key (§10.8): declared class, else declared
        upstream source, else the claim stands alone as its own class."""
        return self.independence_class or self.derived_from_source or self.claim_id

    @property
    def method(self) -> str:
        """The collection method for method-breadth counting (§10.8, SIG-EPIS-028);
        falls back to the source id so an undeclared method is not free breadth."""
        return self.collection_method or self.source_id or self.claim_id

    def digest_token(self) -> str:
        if self.content_hash:
            return f"{self.claim_id}:{self.content_hash}"
        payload = (
            f"{self.predicate_id}|{self.value!r}|{self.raw_value}"
            f"|{self.observed_at.isoformat()}|{self.source_id}"
        )
        return f"{self.claim_id}:{hashlib.sha256(payload.encode()).hexdigest()}"


# --- outputs -----------------------------------------------------------------


@dataclass(frozen=True)
class ExcludedClaim:
    """A claim dropped in Phase 1/2, with the reason it is not resolving."""

    claim_id: str
    reason: str


@dataclass(frozen=True)
class Candidate:
    """One canonical candidate value and its aggregated, per-class support."""

    value: object
    best_weight: int
    supporting_class_ids: tuple[str, ...]
    method_breadth: int
    representative: Claim
    supporting_claim_ids: tuple[str, ...]
    #: best weight achieved *within* each supporting class (SIG-RECON-018).
    class_weights: tuple[int, ...]
    class_methods: tuple[str, ...]


@dataclass(frozen=True)
class Resolution:
    """The stored decision record §16.4 describes (SIG-STORE-014).

    On a human override the algorithmic result is preserved on
    :attr:`algorithmic` and both are shown (SIG-RECON-025); resolutions are never
    edited in place (SIG-RECON-021) — :func:`pin` returns a new record.
    """

    subject_id: str
    predicate_id: str
    resolution_status: str  # RESOLVED | UNRESOLVED
    value: object | None
    support: str
    agreement: str
    currency: str | None
    contradiction_state: str
    strategy_id: str | None
    rationale_code: str
    rationale_text: str
    winning_claim_id: str | None
    considered_claim_ids: tuple[str, ...]
    supporting_claim_ids: tuple[str, ...]
    dissenting_claim_ids: tuple[str, ...]
    excluded: tuple[ExcludedClaim, ...]
    independence_class_ids: tuple[str, ...]
    rules_fired: tuple[str, ...]
    ruleset_version: str
    resolver_version: str
    input_digest: str
    as_of_world: date
    as_of_belief: date
    computed_at: datetime
    unresolved_code: str | None = None
    last_known_value: object | None = None
    last_known_date: date | None = None
    contradictions: tuple[Contradiction, ...] = ()
    decided_by: str = "auto"
    override_rationale: str | None = None
    algorithmic: Resolution | None = None

    def decision_key(self) -> tuple[object, ...]:
        """The reproducible core of the decision (everything but wall-clock time).

        Two runs over identical inputs MUST produce identical decision keys
        (SIG-RECON-007/020); ``computed_at`` is deliberately excluded.
        """
        return (
            self.resolution_status,
            repr(self.value),
            self.support,
            self.agreement,
            self.currency,
            self.contradiction_state,
            self.strategy_id,
            self.rationale_code,
            self.rationale_text,
            self.winning_claim_id,
            self.considered_claim_ids,
            self.supporting_claim_ids,
            self.dissenting_claim_ids,
            self.independence_class_ids,
            self.rules_fired,
            self.unresolved_code,
            self.input_digest,
        )


def pin(
    algorithmic: Resolution,
    *,
    value: object,
    decided_by: str,
    override_rationale: str,
) -> Resolution:
    """Pin a curator's value over the algorithmic result (SIG-RECON-024/025).

    ``decided_by`` and a non-empty ``override_rationale`` are mandatory; the
    algorithmic resolution is retained on :attr:`Resolution.algorithmic` so the
    UI can show both — the override never deletes or hides the rule's answer.
    """
    if not decided_by or decided_by == "auto":
        raise ValueError("an override MUST record a non-'auto' decided_by (SIG-RECON-024)")
    if not override_rationale:
        raise ValueError("an override MUST record an override_rationale (SIG-RECON-024)")
    base = algorithmic.algorithmic or algorithmic  # never nest overrides
    return replace(
        algorithmic,
        value=value,
        decided_by=decided_by,
        override_rationale=override_rationale,
        algorithmic=base,
    )


# --- the pipeline ------------------------------------------------------------


@dataclass
class _State:
    subject_id: str
    predicate_id: str
    as_of_world: date
    ruleset: Ruleset
    considered: list[Claim] = field(default_factory=list)
    excluded: list[ExcludedClaim] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    n_basis_dropped: int = 0

    def fire(self, rule: str) -> None:
        if rule not in self.rules:
            self.rules.append(rule)

    def drop(self, claim: Claim, reason: str) -> None:
        self.excluded.append(ExcludedClaim(claim.claim_id, reason))


def RESOLVE(  # noqa: N802 - the spec names the function RESOLVE (SIG-RECON-006)
    subject_id: str,
    predicate_id: str,
    claims: list[Claim],
    *,
    as_of_world: date,
    as_of_belief: date,
    ruleset: Ruleset | None = None,
    blocking_contradiction: bool = False,
    computed_at: datetime | None = None,
) -> Resolution:
    """Resolve one ``(subject, predicate)`` pair over ``claims`` (SIG-RECON-006)."""
    rs = ruleset or load_ruleset()
    st = _State(subject_id, predicate_id, as_of_world, rs)
    computed_at = computed_at or datetime.now(UTC)

    # Phase 0 GATHER — the claims for THIS pair (as_of_belief is the caller's
    # sys_period cut; recorded on the record for reproducibility).
    pair = [c for c in claims if c.subject_id == subject_id and c.predicate_id == predicate_id]

    # Phase 1 ADMISSIBILITY (prior to weight).
    admissible = _admissibility(st, pair)
    considered_ids = tuple(sorted(c.claim_id for c in pair))

    # Phase 2 CANONICALIZE (2.3 count-basis conflation guard).
    admissible = _canonicalize(st, admissible)
    st.considered = admissible

    def _emit(
        *,
        status: str,
        code: str | None,
        candidates: list[Candidate],
        winner: Candidate | None,
        second: Candidate | None,
        strategy: str | None,
    ) -> Resolution:
        return _finalize(
            st,
            considered_ids,
            computed_at,
            as_of_belief,
            status=status,
            code=code,
            candidates=candidates,
            winner=winner,
            second=second,
            strategy=strategy,
        )

    # Phase 1.5 / U0 — no admissible evidence is distinct from balanced evidence.
    if not admissible:
        st.fire("U0")
        return _emit(
            status="UNRESOLVED",
            code="U0",
            candidates=[],
            winner=None,
            second=None,
            strategy=None,
        )

    # Phase 5 STRATEGY selection happens before ranking so a silent/never ruleset
    # short-circuits (SIG-RECON-013).
    strategy = rs.strategy_for(predicate_id)
    if strategy is None or strategy == "never_resolve":
        st.fire("SIG-RECON-013" if strategy is None else "never_resolve")
        code = "NO_STRATEGY" if strategy is None else "NEVER_RESOLVE"
        return _emit(
            status="UNRESOLVED",
            code=code,
            candidates=[],
            winner=None,
            second=None,
            strategy=strategy,
        )

    # Phase 3 WEIGHT + Phase 4 INDEPENDENCE -> candidates.
    candidates = _candidates(st, admissible, as_of_world)
    if not candidates:  # every admissible claim was W0 (retained, non-resolving).
        st.fire("U0")
        return _emit(
            status="UNRESOLVED",
            code="U0",
            candidates=[],
            winner=None,
            second=None,
            strategy=strategy,
        )

    # Phase 5.2 STRATEGY -> a TOTAL order over candidates (SIG-RECON-007).
    ordered = _total_order(candidates, strategy=strategy, ruleset=rs, predicate_id=predicate_id)
    st.fire(strategy)
    st.fire("SIG-RECON-007")
    winner = ordered[0]
    second = ordered[1] if len(ordered) > 1 else None

    # Phase 6 AMBIGUITY TEST — evaluated in order U0..U8 (SIG-RECON-014).
    amb_code = _ambiguity(
        st,
        ordered=ordered,
        winner=winner,
        second=second,
        ruleset=rs,
        predicate_id=predicate_id,
        as_of_world=as_of_world,
        blocking=blocking_contradiction,
    )
    if amb_code is not None:
        st.fire(amb_code)
        return _emit(
            status="UNRESOLVED",
            code=amb_code,
            candidates=ordered,
            winner=winner,
            second=second,
            strategy=strategy,
        )

    # Phase 7 EMIT.
    return _emit(
        status="RESOLVED",
        code=None,
        candidates=ordered,
        winner=winner,
        second=second,
        strategy=strategy,
    )


def _admissibility(st: _State, pair: list[Claim]) -> list[Claim]:
    """Phase 1: drop retracted, out-of-window, D6, and superseded claims."""
    kept: list[Claim] = []
    for c in pair:
        if c.review_status in _RETRACTED:
            st.drop(c, f"review_status={c.review_status}")
            continue
        if not _intersects_world(c, st.as_of_world):
            st.drop(c, "valid_period does not intersect as_of_world")
            continue
        try:
            d = directness_for(c.predicate_id, c.genre)
        except KeyError:
            st.drop(c, f"no directness row for genre {c.genre!r}")
            continue
        if d == "D6":
            st.fire("D6-exclude")  # SIG-EPIS-018: admissibility filter, not a weight
            st.drop(c, "D6 non-probative for this predicate")
            continue
        kept.append(c)

    # 1.4 supersession: within one source and valid-time, the later observation
    # supersedes; drop the earlier (claim_id breaks an exact-time tie).
    latest: dict[tuple[str, object, object], Claim] = {}
    for c in kept:
        key = (c.source_id, c.valid_from, c.valid_to)
        cur = latest.get(key)
        if cur is None or (c.observed_at, c.claim_id) > (cur.observed_at, cur.claim_id):
            latest[key] = c
    winners = set(id(c) for c in latest.values())
    result: list[Claim] = []
    for c in kept:
        if id(c) in winners:
            result.append(c)
        else:
            st.fire("SIG-RECON-006:1.4")
            st.drop(c, "superseded by a later claim from the same source")
    return result


def _intersects_world(c: Claim, as_of_world: date) -> bool:
    if c.valid_from is not None and as_of_world < c.valid_from:
        return False
    if c.valid_to is not None and as_of_world >= c.valid_to:
        return False
    return True


def _value_domain_ok(value: object, datatype: str) -> bool:
    """Phase 2.2 domain check for the datatypes the resolver can verify cheaply.

    Only the machine-checkable scalar domains are enforced here; richer domains
    (edtf, geometry, controlled enums) are validated upstream at extraction
    against the generated JSON Schema (§20.1), so they are accepted as-is.
    """
    if datatype == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if datatype == "boolean":
        return isinstance(value, bool)
    return True


def _canonicalize(st: _State, claims: list[Claim]) -> list[Claim]:
    """Phase 2: canonicalize, then guard against comparing different things.

    Phase 2.2 drops a claim whose value does not fit the predicate's value domain
    with a ``VALUE_DOMAIN_MISMATCH`` contradiction; Phase 2.3 refuses to compare
    claims with different ``count_basis`` — SIG never silently compares different
    things (SIG-RECON-028). Value *normalization* (units, enum casing, entity
    identity, date granularity) is performed upstream at extraction/normalization
    with ``raw_value`` preserved (P2); this phase only rejects the uncanonicalizable.
    """
    # Phase 2.2 — reject values outside the predicate's checkable domain.
    datatype = st.ruleset.predicate(st.predicate_id).get("value_datatype", "")
    domain_ok: list[Claim] = []
    mismatched: list[object] = []
    for c in claims:
        if _value_domain_ok(c.value, str(datatype)):
            domain_ok.append(c)
        else:
            mismatched.append(c.value)
            st.drop(c, f"value {c.value!r} is not a valid {datatype} (VALUE_DOMAIN_MISMATCH)")
    if mismatched:
        st.fire("VALUE_DOMAIN_MISMATCH")
        st.contradictions.append(
            Contradiction(
                contradiction_type="value_domain_mismatch",
                subject_id=st.subject_id,
                predicate_id=st.predicate_id,
                claim_values=tuple(mismatched),
                note=(
                    f"Dropped claim value(s) that cannot be canonicalized to the "
                    f"{datatype} domain of {st.predicate_id} (§28 Phase 2.2)."
                ),
                severity="notable",
            )
        )
    claims = domain_ok

    # Phase 2.3 — count-basis conflation guard.
    bases = {c.count_basis for c in claims if c.count_basis is not None}
    if len(bases) <= 1:
        return claims
    target = st.predicate_id.removesuffix("_device_count")
    kept: list[Claim] = []
    dropped_values: list[object] = []
    for c in claims:
        if c.count_basis is not None and c.count_basis != target:
            st.n_basis_dropped += 1
            dropped_values.append(c.value)
            st.drop(c, f"count_basis {c.count_basis!r} != {target!r} (PREDICATE_CONFLATION)")
        else:
            kept.append(c)
    if dropped_values:
        st.fire("PREDICATE_CONFLATION")
        st.contradictions.append(
            Contradiction(
                contradiction_type="predicate_conflation",
                subject_id=st.subject_id,
                predicate_id=st.predicate_id,
                claim_values=tuple(dropped_values),
                note=(
                    f"Refused to compare {st.predicate_id} against claims carrying a "
                    "different count basis (§29.1 SIG-RECON-028); the mismatched "
                    "claims are dropped, not adjudicated."
                ),
                severity="notable",
                evidence=tuple(
                    c.evidence for c in claims if c.evidence is not None and c.count_basis != target
                ),
            )
        )
    return kept


def _candidates(st: _State, admissible: list[Claim], as_of_world: date) -> list[Candidate]:
    """Phase 3 WEIGHT + Phase 4 INDEPENDENCE.

    Compose ``W`` per claim, drop the W0 tier from the resolving set (retained
    for display), then group by canonical value and count corroboration **per
    independence class and per method**, never per claim (SIG-RECON-018).
    """
    recency = st.ruleset.recency_breaks_ties(st.predicate_id)
    weighted: list[tuple[Claim, int]] = []
    for c in admissible:
        w = _weight(st, c, as_of_world)
        if w is None:
            continue
        if w == 0:
            st.fire("W0-retained")  # §10.6: retained for display, never resolving
            st.drop(c, "W0 non-probative (retained for display, not resolving)")
            continue
        weighted.append((c, w))

    by_value: dict[object, list[tuple[Claim, int]]] = {}
    for c, w in weighted:
        by_value.setdefault(c.value, []).append((c, w))

    candidates: list[Candidate] = []
    for value, group in by_value.items():
        # best weight within each independence class (SIG-RECON-018).
        cls_weight: dict[str, int] = {}
        cls_method: dict[str, str] = {}
        for c, w in group:
            if w > cls_weight.get(c.class_id, -1):
                cls_weight[c.class_id] = w
                cls_method[c.class_id] = c.method
        best_weight = max(w for _, w in group)
        methods = {cls_method[k] for k in cls_weight}
        representative = _representative(group, recency=recency)
        candidates.append(
            Candidate(
                value=value,
                best_weight=best_weight,
                supporting_class_ids=tuple(sorted(cls_weight)),
                method_breadth=len(methods),
                representative=representative,
                supporting_claim_ids=tuple(sorted(c.claim_id for c, _ in group)),
                class_weights=tuple(cls_weight[k] for k in sorted(cls_weight)),
                class_methods=tuple(cls_method[k] for k in sorted(cls_weight)),
            )
        )
    return candidates


def _weight(st: _State, c: Claim, as_of_world: date) -> int | None:
    meta = st.ruleset.predicate(c.predicate_id)
    if c.windowed:
        cur = "C1"  # windowed predicates are indexed, not stale (SIG-RECON-011)
        st.fire("SIG-RECON-011")
    else:
        cur = currency(
            volatility_class=meta["volatility_class"],
            half_life=meta["half_life"],
            observed_at=c.observed_at,
            as_of=as_of_world,
        )
    d = directness_for(c.predicate_id, c.genre)
    try:
        return weight_class(
            reliability=c.reliability,
            directness=d,
            integrity=c.integrity,
            currency=cur,
            structured_exact=c.structured_exact,
            field_verified=c.field_verified,
        )
    except DirectnessExcluded:  # pragma: no cover - D6 already filtered in Phase 1
        return None


def _representative(group: list[tuple[Claim, int]], *, recency: bool) -> Claim:
    """The claim that carries a candidate value under the universal tie-break —
    deterministic, no random choice (SIG-RECON-007). Recency is neutralized for
    IMMUTABLE/GLACIAL predicates so a newer claim gains no edge (SIG-RECON-010)."""

    def key(cw: tuple[Claim, int]) -> tuple[object, ...]:
        observed = -cw[0].observed_at.toordinal() if recency else 0
        return (-cw[1], observed, cw[0].rank, cw[0].claim_id)

    return min(group, key=key)[0]


def _total_order(
    candidates: list[Candidate],
    *,
    strategy: str,
    ruleset: Ruleset,
    predicate_id: str,
) -> list[Candidate]:
    """Phase 5.2: a TOTAL order over candidates (SIG-RECON-007).

    Each strategy contributes its own primary key; the universal tie-break
    ``(weight desc, method_breadth desc, observed_at desc, source_rank asc,
    claim_id asc)`` is appended after it. ``claim_id`` is unique, so the order is
    total and fixed forever — there is no random tie-break. For IMMUTABLE/GLACIAL
    predicates ``observed_at`` is neutralized so recency cannot break a tie
    (SIG-RECON-010).
    """
    recency = ruleset.recency_breaks_ties(predicate_id)

    def observed_key(cand: Candidate) -> int:
        return -cand.representative.observed_at.toordinal() if recency else 0

    def strategy_primary(cand: Candidate) -> tuple[object, ...]:
        if strategy == "latest_observation_wins":
            return (-cand.representative.observed_at.toordinal(),)
        if strategy == "max_support":
            return (-len(cand.supporting_class_ids),)
        if strategy in {"interval_union", "interval_intersection"}:
            return (0,)  # value already merged; universal key orders the rest
        # authoritative_source_wins (weight already encodes authority via R x D).
        return (-cand.best_weight,)

    def sort_key(cand: Candidate) -> tuple[object, ...]:
        rep = cand.representative
        return (
            *strategy_primary(cand),
            -cand.best_weight,
            -cand.method_breadth,
            observed_key(cand),
            rep.rank,
            rep.claim_id,
        )

    return sorted(candidates, key=sort_key)


def _ambiguity(
    st: _State,
    *,
    ordered: list[Candidate],
    winner: Candidate,
    second: Candidate | None,
    ruleset: Ruleset,
    predicate_id: str,
    as_of_world: date,
    blocking: bool,
) -> str | None:
    """Phase 6: the U0..U8 test, evaluated IN ORDER (SIG-RECON-014).

    Returns the id of the first triggering condition, or ``None`` if the winner
    stands. Order is what makes the reason deterministic.
    """
    # U1 — nothing above weak; a tip alone never resolves.
    if winner.best_weight <= 1:
        return "U1"

    # U2 — a genuine standoff between equal, independent, equally-broad evidence.
    if second is not None and winner.best_weight == second.best_weight:
        disjoint = not (set(winner.supporting_class_ids) & set(second.supporting_class_ids))
        if disjoint and winner.method_breadth == second.method_breadth:
            return "U2"

    # U3 — one source vs one source is never resolvable by fiat.
    if len(winner.supporting_class_ids) == 1:
        winner_methods = set(winner.class_methods)
        for cand in ordered[1:]:
            if cand.best_weight >= 2 and (set(cand.class_methods) - winner_methods):
                return "U3"

    # U4 — numeric predicate, spread beyond tolerance, nothing dispositive.
    if _is_numeric(winner.value) and winner.best_weight < 4:
        nums = [float(cast(float, c.value)) for c in ordered if _is_numeric(c.value)]
        if len(nums) >= 2:
            lo, hi = min(nums), max(nums)
            if hi and abs(hi - lo) / abs(hi) > ruleset.tolerance(predicate_id):
                return "U4"

    # U5 — the winner is too old to assert about a changing quantity. Fires even
    # with no dissent at all (SIG-RECON-015): silence plus age is not a resolution.
    if ruleset.currency_can_stale(predicate_id):
        cur = _currency_of(winner.representative, ruleset, as_of_world)
        if cur in {"C3", "C4"}:
            st.fire("SIG-RECON-015")  # the rule the outline lacks
            return "U5"

    # U6 — claims dropped for count-basis mismatch and fewer than two survive.
    if st.n_basis_dropped > 0 and len(st.considered) < 2:
        return "U6"

    # U7 — a human flagged an open BLOCKING contradiction on this pair.
    if blocking:
        return "U7"

    # U8 — strong unreconciled dissent beats a merely-strong winner.
    support, agreement = _confidence(ordered, winner, blocking=blocking)
    if agreement == "IRRECONCILABLE" and support != "CONFIRMED":
        return "U8"

    return None


def _is_numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _currency_of(claim: Claim, ruleset: Ruleset, as_of_world: date) -> str:
    if claim.windowed:
        return "C1"
    return currency(
        volatility_class=ruleset.volatility_class(claim.predicate_id),
        half_life=ruleset.half_life(claim.predicate_id),
        observed_at=claim.observed_at,
        as_of=as_of_world,
    )


def _confidence(
    ordered: list[Candidate],
    winner: Candidate,
    *,
    blocking: bool,
) -> tuple[str, str]:
    """Compute ``support`` (from the winner's evidence) and ``agreement`` (from
    the dissent structure), the two orthogonal fields of §10.7."""
    # support — from the winning value's evidence only (SIG-EPIS-023).
    w3_methods = {winner.class_methods[i] for i, cw in enumerate(winner.class_weights) if cw >= 3}
    w2_classes = sum(1 for cw in winner.class_weights if cw >= 2)
    w2_methods = {winner.class_methods[i] for i, cw in enumerate(winner.class_weights) if cw >= 2}
    if winner.best_weight == 4 or len(w3_methods) >= 2:
        support = "CONFIRMED"
    elif winner.best_weight == 3 or len(w2_methods) >= 2:
        support = "STRONGLY_SUPPORTED"
    elif w2_classes >= 1:
        support = "PROBABLE"
    elif winner.best_weight >= 1:
        support = "WEAKLY_SUPPORTED"
    else:  # pragma: no cover - W0 never enters the resolving set
        support = "UNSUPPORTED"

    # agreement — from the dissent structure only (SIG-EPIS-023).
    dissent = ordered[1:]
    if not dissent:
        agreement = "UNCONTESTED"
    else:
        dissent_classes_w3 = set()
        dissent_classes_w2 = set()
        for cand in dissent:
            for i, cw in enumerate(cand.class_weights):
                if cw >= 3:
                    dissent_classes_w3.add(cand.supporting_class_ids[i])
                if cw >= 2:
                    dissent_classes_w2.add(cand.supporting_class_ids[i])
        if blocking or len(dissent_classes_w3) >= 2:
            agreement = "IRRECONCILABLE"
        elif len(dissent_classes_w2) >= 1:
            agreement = "CONTESTED"
        else:
            agreement = "MINOR_DISAGREEMENT"
    return support, agreement


def _finalize(
    st: _State,
    considered_ids: tuple[str, ...],
    computed_at: datetime,
    as_of_belief: date,
    *,
    status: str,
    code: str | None,
    candidates: list[Candidate],
    winner: Candidate | None,
    second: Candidate | None,
    strategy: str | None,
) -> Resolution:
    """Phase 7 EMIT — assemble the decision record (§16.4, SIG-STORE-014)."""
    rs = st.ruleset
    blocking = code == "U7"
    if winner is not None:
        support, agreement = _confidence(candidates, winner, blocking=blocking)
    else:
        support, agreement = "UNSUPPORTED", "UNCONTESTED"

    supporting_ids: tuple[str, ...] = winner.supporting_claim_ids if winner else ()
    dissenting_ids = (
        tuple(sorted(cid for cand in candidates[1:] for cid in cand.supporting_claim_ids))
        if winner
        else ()
    )
    class_ids = tuple(sorted({cid for cand in candidates for cid in cand.supporting_class_ids}))

    cur_label: str | None = None
    last_known_value: object | None = None
    last_known_date: date | None = None
    if winner is not None:
        cur_label = _CURRENCY_LABEL[_currency_of(winner.representative, rs, st.as_of_world)]
        if status == "UNRESOLVED":
            # SIG-RECON-016: publish the stale/failed winner as last_known with date.
            last_known_value = winner.value
            last_known_date = winner.representative.observed_at

    contradiction_state = _contradiction_state(status, code, agreement)

    rationale_code, rationale_text = render_rationale(
        ruleset=rs,
        status=status,
        code=code,
        predicate_id=st.predicate_id,
        support=support,
        winner=winner,
        second=second,
        as_of_world=st.as_of_world,
    )

    value = winner.value if (winner is not None and status == "RESOLVED") else None

    digest = _input_digest(st.considered, considered_ids, rs.version)

    return Resolution(
        subject_id=st.subject_id,
        predicate_id=st.predicate_id,
        resolution_status=status,
        value=value,
        support=support,
        agreement=agreement,
        currency=cur_label,
        contradiction_state=contradiction_state,
        strategy_id=strategy,
        rationale_code=rationale_code,
        rationale_text=rationale_text,
        winning_claim_id=(
            winner.representative.claim_id if (winner and status == "RESOLVED") else None
        ),
        considered_claim_ids=considered_ids,
        supporting_claim_ids=supporting_ids,
        dissenting_claim_ids=dissenting_ids,
        excluded=tuple(st.excluded),
        independence_class_ids=class_ids,
        rules_fired=tuple(st.rules),
        ruleset_version=rs.version,
        resolver_version=RESOLVER_VERSION,
        input_digest=digest,
        as_of_world=st.as_of_world,
        as_of_belief=as_of_belief,
        computed_at=computed_at,
        unresolved_code=code,
        last_known_value=last_known_value,
        last_known_date=last_known_date,
        contradictions=tuple(st.contradictions),
    )


def _contradiction_state(status: str, code: str | None, agreement: str) -> str:
    if status == "RESOLVED":
        return "uncontested" if agreement == "UNCONTESTED" else "resolved_conflict"
    if code in {"U0", "U1", "U5", "NO_STRATEGY", "NEVER_RESOLVE"}:
        return "insufficient"
    return "unresolved_conflict"


def _input_digest(
    considered: list[Claim],
    considered_ids: tuple[str, ...],
    ruleset_version: str,
) -> str:
    """``hash(sorted claim ids + content hashes)`` (SIG-RECON-006 7.4 / -020)."""
    tokens = sorted(c.digest_token() for c in considered)
    payload = "|".join([ruleset_version, *considered_ids, *tokens])
    return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
    "RESOLVER_VERSION",
    "Candidate",
    "Claim",
    "ExcludedClaim",
    "Resolution",
    "RESOLVE",
    "pin",
]
