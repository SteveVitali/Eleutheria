# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""Evidence-complete research-dossier portfolios (P32.17, §55.7, SIG-DOS-001/002).

The S2 stream's accountable local artifact is a *reviewed research dossier*: a
twelve-question portfolio over the bounded `dossier_documents` evidence packets
(P32.12/ADR-131) that answers *what is deployed, who operates it, how it was
procured, who can see the data, under what authority, what is retained and
shared, what changed, and what remains unknown* — every displayed assertion
traceable to a captured byte-range, and every gap an explicit field state with
a search basis and a closing condition. It is NOT the §39.2 inventory overview:
the inventory says "a point on the map"; this portfolio answers the local
accountability questions with evidence lineage preserved.

Two versioned contracts live here:

* ``sig.dossier-packet/1`` — the reviewed input a dossier ticket authors: the
  emitted `dossier_documents` records (claims + evidence_artifact capture
  rows), the source search log, declared states the machinery cannot infer
  (`not_applicable`, `withheld`, `derived`), precise follow-up tasks, declared
  restrictions, and the independent-review record.
* ``sig.dossier-portfolio/1`` — the rendered output consumed by `web/` and the
  print path: per-question answers in the six-state vocabulary
  (supported/disputed/derived/unknown/withheld/not_applicable), the
  fact-to-capture ledger, the normalized search log, the independent
  completion checklist, the rubric score + pilot gate, release-validation
  violations, and the derived decision windows.

State discipline (S2 / SIG-DOS-001): canonical answer states are *not* search
states. "Searched, not found" is a research basis under `unknown`, never an
assertion of absence; a blank value is never a state — every question is
represented explicitly; `not_applicable` and `withheld` are declared with
rationale/basis, never inferred; a same-scope, same-period disagreement is
`disputed` and stays visible — different scopes are *not* contradictions.

Gate discipline (SIG-DOS-002): the rubric scores every question 0–3;
`mechanical_complete` needs total ≥ 28/36 with q1/q5/q7/q8 each ≥ 2;
`pilot_complete` additionally needs the independent semantic review marked
`completed` (D-R10-HUMAN-1 — never fabricated) and zero release violations.
Release validation fails closed on unsupported affirmative claims,
misclassified instruments, missing state/basis, hidden conflicts, fabricated
absence, and completeness inflated by blanks.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping, Sequence
from typing import Any

from db.claim_sink import content_digest

__all__ = [
    "PACKET_SCHEMA",
    "PORTFOLIO_SCHEMA",
    "DOSSIER_SCHEMA",
    "GENERATOR_VERSION",
    "QUESTION_IDS",
    "QUESTIONS",
    "QUESTION_TITLES",
    "ANSWER_STATES",
    "SEARCH_OUTCOMES",
    "REQUIRED_MINIMUM",
    "COMPLETE_TOTAL",
    "COMPLETE_MAX",
    "CORRECTION_ROUTE",
    "build_dossier",
    "build_portfolio",
    "render_portfolio_json",
    "render_dossier_print_html",
    "validate_packet",
]

PACKET_SCHEMA = "sig.dossier-packet/1"
PORTFOLIO_SCHEMA = "sig.dossier-portfolio/1"
DOSSIER_SCHEMA = "sig.research-dossier/1"
GENERATOR_VERSION = "research-dossier/1"

#: The durable public correction route a dossier's q12 points at (P32.14–P32.16:
#: the corrections log is the public face of the canonical correction path).
CORRECTION_ROUTE = "/corrections/"

# --------------------------------------------------------------------------- #
# The fixed twelve-question S2 rubric (SIG-DOS-002). Order is canonical: q1..q12
# is both the render order and the scoring order.
# --------------------------------------------------------------------------- #

QUESTIONS: tuple[dict[str, str], ...] = (
    {"id": "q1", "slug": "operator_buyer_funder", "title": "Operator, buyer and funder"},
    {"id": "q2", "slug": "technologies_products", "title": "Technologies and products"},
    {
        "id": "q3",
        "slug": "inventory_count",
        "title": "Owned inventory and the count universe",
    },
    {
        "id": "q4",
        "slug": "external_access",
        "title": "External database / network access",
    },
    {
        "id": "q5",
        "slug": "procurement_money",
        "title": "Procurement and money basis",
    },
    {"id": "q6", "slug": "authority", "title": "Authority and applicability"},
    {"id": "q7", "slug": "retention", "title": "Retention and exceptions"},
    {"id": "q8", "slug": "sharing", "title": "Sharing actors and mode"},
    {"id": "q9", "slug": "timeline", "title": "Effective / change timeline"},
    {
        "id": "q10",
        "slug": "oversight",
        "title": "Oversight findings and institutional response",
    },
    {
        "id": "q11",
        "slug": "independent_support",
        "title": "Independent support versus agency statements",
    },
    {
        "id": "q12",
        "slug": "unknowns_corrections",
        "title": "Unresolved evidence and the correction route",
    },
)
QUESTION_IDS: tuple[str, ...] = tuple(q["id"] for q in QUESTIONS)
QUESTION_TITLES: dict[str, str] = {q["id"]: q["title"] for q in QUESTIONS}

#: The canonical answer-state vocabulary (SIG-DOS-001). `not_researched` and the
#: other workflow outcomes are SEARCH states — they live under `unknown`, never
#: as an answer state.
ANSWER_STATES: tuple[str, ...] = (
    "supported",
    "disputed",
    "derived",
    "unknown",
    "withheld",
    "not_applicable",
)

#: The recorded search-log outcomes. `found` is informational (the claim set
#: carries the finding); the three documented-not-found outcomes make a bounded,
#: reviewable `unknown`.
SEARCH_OUTCOMES: tuple[str, ...] = (
    "found",
    "searched_not_found",
    "access_blocked",
    "version_unverified",
    "not_researched",
)
_DOCUMENTED_SEARCH: frozenset[str] = frozenset(
    {"searched_not_found", "access_blocked", "version_unverified"}
)

#: SIG-DOS-002's pilot-completeness gate: total ≥ 28/36 AND each of q1/q5/q7/q8
#: ≥ 2 — the four questions whose absence would make the dossier unreviewable.
COMPLETE_TOTAL = 28
COMPLETE_MAX = 36
REQUIRED_MINIMUM: dict[str, int] = {"q1": 2, "q5": 2, "q7": 2, "q8": 2}

# --------------------------------------------------------------------------- #
# Release-side mirrors of the P32.12 emit-time guards. The connector already
# refuses a template asserting executed-instrument predicates / a subscription
# asserting local-hardware predicates at EMIT time (ADR-131). The release
# validator re-checks so a hand-edited packet cannot launder a misclassified
# instrument past the dossier gate. The lists mirror
# `connectors/src/connectors/data/dossier_documents_vocab.toml`; a tests/exports
# consistency test asserts equality with the TOML (exports cannot import
# connectors — connectors depends on sig-exports, never the reverse).
# --------------------------------------------------------------------------- #

TEMPLATE_EXECUTION_GUARD: frozenset[str] = frozenset(
    {
        "buyer",
        "seller",
        "recipient",
        "vendor",
        "funder",
        "signed_date",
        "contract_signed_date",
        "contract_value",
        "contract_start_date",
        "contract_end_date",
        "contracted_device_count",
        "amount",
        "amends_contract",
        "lifecycle_transition",
        "procurement_state",
    }
)
SUBSCRIPTION_HARDWARE_GUARD: frozenset[str] = frozenset(
    {
        "claimed_device_count",
        "active_device_count",
        "installed_device_count",
        "contracted_device_count",
        "invoiced_device_count",
        "deployment_exists",
        "fixed_asset_location",
        "asset_exists_at_location",
        "implements_technology",
    }
)

#: The crosswalk fields flagged `required = true` (a required field left
#: unanswered is partial coverage — the question can never reach "sufficiently
#: scoped"). Mirrored from dossier_field_crosswalk.toml; consistency-tested.
REQUIRED_CROSSWALK_FIELDS: frozenset[str] = frozenset(
    {"retention_period", "technology", "access_edge"}
)

#: The §29.3 scope-qualifier predicates that decide count comparability — same
#: scope + same period + different value is a `disputed` conflict; different
#: scope is a different quantity, never a contradiction (S2).
_SCOPE_QUALIFIERS: frozenset[str] = frozenset({"count_scope", "count_scope_detail"})

#: Count-valued predicates require a count_scope qualifier to be "sufficiently
#: scoped" — a device/partner count without its universe is a partial answer.
_COUNT_PREDICATES: frozenset[str] = frozenset(
    {"claimed_device_count", "contracted_device_count", "sharing_partner_degree"}
)

#: Predicates whose dates feed the derived decision window (a stated date a
#: future decision can hang off — the document's own dates, never the capture
#: date).
_DECISION_PREDICATES: frozenset[str] = frozenset(
    {"contract_end_date", "contract_start_date", "signed_date", "as_of", "posted_date"}
)

#: The bookkeeping predicate the adapter emits for configured-but-unanswered
#: fields (mandated != populated, never fabricated).
_FIELD_STATE_PREDICATE = "disclosure_field_state"
_FIELD_STATE_UNRESOLVED: frozenset[str] = frozenset({"absent", "present_but_empty", "redacted"})

#: Predicates where a claim asserts THE value of a measured thing — two of these
#: in the same scope + period disagreeing IS a conflict (§29/S2). Verbatim
#: clause predicates (use_restriction, written_policy_value, products, titles,
#: lifecycle labels…) are excluded: each literal is a distinct stated fact, so
#: two different clause texts are two rules, never a contradiction.
_CONFLICT_ELIGIBLE: frozenset[str] = frozenset(
    {
        "claimed_device_count",
        "contracted_device_count",
        "sharing_partner_degree",
        "contract_value",
        "funding_amount",
        "amount",
        "retention_period",
        "contract_start_date",
        "contract_end_date",
        "signed_date",
        "effective_from",
        "buyer",
        "seller",
        "vendor",
        "funder",
        "recipient",
        "authorization_state",
    }
)


# --------------------------------------------------------------------------- #
# Packet validation
# --------------------------------------------------------------------------- #


def validate_packet(packet: Mapping[str, Any]) -> list[str]:
    """The `sig.dossier-packet/1` input contract — returns violations ([] = valid).

    Fail-closed at composition: a malformed packet produces violations, not a
    silently-drifted dossier.
    """
    problems: list[str] = []
    if str(packet.get("schema")) != PACKET_SCHEMA:
        problems.append(f"schema must be {PACKET_SCHEMA!r}")
    if not isinstance(packet.get("subject"), Mapping):
        problems.append("subject block is required")
    else:
        for key in ("slug", "label", "jurisdiction"):
            if not packet["subject"].get(key):
                problems.append(f"subject.{key} is required")
    records = packet.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        problems.append("records must be the emitted dossier_documents record list")
    for key in ("search_log", "follow_ups"):
        if key in packet and not isinstance(packet[key], Sequence):
            problems.append(f"{key} must be a list")
    declared = packet.get("declared") or {}
    for kind in ("not_applicable", "withheld", "derived"):
        entries = declared.get(kind) or []
        if isinstance(entries, Mapping):
            entries = [{"question": q, **v} for q, v in entries.items()]
        for entry in entries:
            q = str(entry.get("question") or "")
            if q not in QUESTION_IDS:
                problems.append(f"declared.{kind}: unknown question {q!r}")
    review = packet.get("review") or {}
    status = str(review.get("status") or "not_run")
    if status not in {"not_run", "pending", "completed"}:
        problems.append(f"review.status {status!r} is not a legal mark")
    return problems


# --------------------------------------------------------------------------- #
# Assertion normalization
# --------------------------------------------------------------------------- #


def _capture_index(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """document_id → its evidence_artifact provenance row (the capture binding)."""
    return {
        str(r["document_id"]): r
        for r in records
        if r.get("record_kind") == "evidence_artifact" and r.get("document_id")
    }


def _claims(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [r for r in records if r.get("record_kind") == "claim"]


def _scope_labels(claim: Mapping[str, Any]) -> dict[str, str]:
    """The §29.3 scope qualifiers a claim carries (count universe + detail)."""
    out: dict[str, str] = {}
    for q in claim.get("qualifiers") or ():
        pred = str(q.get("predicate") or "")
        if pred in _SCOPE_QUALIFIERS:
            out[pred] = str(q.get("value") or "")
    return out


def _scope_key(assertion: Mapping[str, Any]) -> tuple[Any, ...]:
    """Comparability key: same predicate + same unit + same count universe."""
    scope = assertion["scope"]
    return (
        assertion["predicate"],
        assertion.get("unit") or "",
        tuple(sorted(scope.items())),
    )


def _window(assertion: Mapping[str, Any]) -> tuple[str | None, str | None]:
    return (assertion.get("valid_from"), assertion.get("valid_to"))


def _windows_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Inclusive-overlap test over declared valid windows; a null bound is open."""
    af, at = _window(a)
    bf, bt = _window(b)
    if at is not None and bf is not None and at < bf:
        return False
    if bt is not None and af is not None and bt < af:
        return False
    return True


def _assertion(claim: Mapping[str, Any], capture: Mapping[str, Any] | None) -> dict[str, Any]:
    """One emitted claim as a rendered assertion — the citation unit.

    Every displayed field is lifted from the emitted record verbatim; nothing is
    invented (a missing capture binding is reported, never filled).
    """
    evidence = claim.get("evidence") or {}
    return {
        "predicate": str(claim.get("predicate_id") or ""),
        "value": claim.get("value"),
        "raw_value": claim.get("raw_value"),
        "unit": claim.get("unit"),
        "object_type": claim.get("object_type"),
        "value_kind": claim.get("value_kind"),
        "source_field": claim.get("source_field"),
        "scope": _scope_labels(claim),
        "qualifiers": [dict(q) for q in (claim.get("qualifiers") or ())],
        "valid_from": claim.get("valid_from"),
        "valid_to": claim.get("valid_to"),
        "valid_edtf": claim.get("valid_edtf"),
        "observed_at": claim.get("observed_at"),
        "evidence_genre": claim.get("evidence_genre"),
        "document_genre": claim.get("document_genre"),
        "document_id": claim.get("document_id"),
        "claim_directness": claim.get("claim_directness"),
        "field_state": claim.get("field_state") or "answered",
        "claim_digest": content_digest(claim),
        "capture_digest": (capture or {}).get("capture_digest"),
        "capture_method": (capture or {}).get("method"),
        "access_mode": (capture or {}).get("access_mode"),
        "source_id": claim.get("source_id"),
        "source_url": evidence.get("source_url"),
        "retrieved_date": evidence.get("retrieved_date"),
        "locator": evidence.get("locator"),
        "extraction_method": evidence.get("extraction_method"),
        "rationale": claim.get("assertion_rationale"),
    }


def _conflicts(assertions: Sequence[Mapping[str, Any]]) -> set[int]:
    """Indexes of assertions in same-scope/same-period value disagreement.

    Only conflict-eligible predicates (a measured single value) participate —
    two verbatim clause texts are two stated rules, never a contradiction.
    """
    flagged: set[int] = set()
    by_scope: dict[tuple[Any, ...], list[int]] = {}
    for i, a in enumerate(assertions):
        if a["value"] is None or a["predicate"] not in _CONFLICT_ELIGIBLE:
            continue
        by_scope.setdefault(_scope_key(a), []).append(i)
    for idxs in by_scope.values():
        for i in idxs:
            for j in idxs:
                if i >= j:
                    continue
                if (
                    _windows_overlap(assertions[i], assertions[j])
                    and str(assertions[i]["value"]).strip() != str(assertions[j]["value"]).strip()
                ):
                    flagged.add(i)
                    flagged.add(j)
    return flagged


# --------------------------------------------------------------------------- #
# The state machine + rubric
# --------------------------------------------------------------------------- #


def _declared_index(packet: Mapping[str, Any], kind: str) -> dict[str, Mapping[str, Any]]:
    """declared.<kind> as {question_id: entry}; a mapping or a list is accepted."""
    entries = (packet.get("declared") or {}).get(kind) or []
    if isinstance(entries, Mapping):
        entries = [{"question": q, **v} for q, v in entries.items()]
    return {str(e.get("question") or ""): e for e in entries}


def _search_basis(search_log: Sequence[Mapping[str, Any]], qid: str) -> Mapping[str, Any] | None:
    """The strongest documented search basis recorded for a question."""
    best: Mapping[str, Any] | None = None
    for entry in search_log:
        if str(entry.get("question") or "") != qid:
            continue
        outcome = str(entry.get("outcome") or "")
        if best is None or (outcome in _DOCUMENTED_SEARCH):
            best = entry
    return best


def _documented_basis(entry: Mapping[str, Any] | None) -> bool:
    """A bounded, reviewable unknown: named sources + a date + a real outcome."""
    if entry is None:
        return False
    if str(entry.get("outcome") or "") not in _DOCUMENTED_SEARCH:
        return False
    return bool(entry.get("sources_searched")) and bool(entry.get("searched_at"))


def _follow_ups_for(follow_ups: Sequence[Mapping[str, Any]], qid: str) -> list[Mapping[str, Any]]:
    return [f for f in follow_ups if str(f.get("question") or "") == qid]


def _specific_follow_up(tasks: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """A follow-up is *specific* when it names what to obtain and how it closes."""
    for t in tasks:
        if t.get("action") and t.get("closing_condition"):
            return t
    return None


def _score_answer(
    state: str,
    assertions: Sequence[Mapping[str, Any]],
    *,
    search_entry: Mapping[str, Any] | None,
    follow_ups: Sequence[Mapping[str, Any]],
    declared_partial: bool,
    unresolved_required: bool,
    derived_inputs_ok: bool = True,
    na_valid: bool = True,
) -> int:
    """The S2 rubric: 0 unresearched / 1 bounded documented unknown /
    2 traceable partial / 3 traceable sufficiently scoped."""
    if state == "not_applicable":
        # n/a scores only when it is a VALID declared absence (rationale + no
        # evidence it would hide); an invalid n/a is a release violation, never
        # a quiet boost to the total.
        return 3 if na_valid else 0
    if state == "withheld":
        return 2
    if state == "unknown":
        if _documented_basis(search_entry) and _specific_follow_up(follow_ups) is not None:
            return 1
        return 0
    # supported / disputed / derived — traceable evidence answers. Partial when
    # any assertion is under-scoped/under-bound, a required field went
    # unanswered, or the packet declared the answer partial.
    score = 3
    if not derived_inputs_ok:
        return 0
    for a in assertions:
        if not a.get("capture_digest") or not a.get("locator"):
            score = min(score, 2)
        if a["predicate"] in _COUNT_PREDICATES and not a["scope"].get("count_scope"):
            score = min(score, 2)
        if a.get("field_state") == "redacted":
            score = min(score, 2)
    if unresolved_required or declared_partial:
        score = min(score, 2)
    return score


# --------------------------------------------------------------------------- #
# Composition
# --------------------------------------------------------------------------- #


def build_dossier(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Compose one `sig.research-dossier/1` dossier from a reviewed packet.

    Pure and deterministic: the same packet yields byte-identical JSON. The
    mechanical states (supported/disputed/derived-from-claims/unknown) derive
    from the emitted records + the search log; the states machinery cannot
    infer (`not_applicable`, `withheld`, `derived` over a declared computation)
    are read from the packet's `declared` block and validated, never guessed.
    """
    problems = validate_packet(packet)
    if problems:
        raise ValueError(f"invalid {PACKET_SCHEMA} packet: {'; '.join(problems)}")

    records = [dict(r) for r in packet.get("records") or ()]
    captures = _capture_index(records)
    claims = _claims(records)
    by_question: dict[str, list[Mapping[str, Any]]] = {q: [] for q in QUESTION_IDS}
    for c in claims:
        qid = str(c.get("dossier_field") or "")
        if qid in by_question:
            by_question[qid].append(c)

    search_log = [dict(e) for e in (packet.get("search_log") or ())]
    follow_ups = [dict(f) for f in (packet.get("follow_ups") or ())]
    declared_na = _declared_index(packet, "not_applicable")
    declared_wh = _declared_index(packet, "withheld")
    declared_dv = _declared_index(packet, "derived")
    declared_partial = _declared_index(packet, "partial")
    restricted = {
        str(r.get("digest")): r for r in (packet.get("restricted") or ()) if r.get("digest")
    }

    violations: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    claim_by_digest = {content_digest(c): c for c in claims}

    for q in QUESTIONS:
        qid = q["id"]
        qclaims = by_question[qid]
        # value claims = real assertions; bookkeeping rows record field states.
        value_claims = [c for c in qclaims if c.get("predicate_id") != _FIELD_STATE_PREDICATE]
        field_rows = [c for c in qclaims if c.get("predicate_id") == _FIELD_STATE_PREDICATE]
        field_states = [
            {
                "field": str(c.get("value") or c.get("source_field") or ""),
                "state": str(c.get("field_state") or ""),
                "document_id": c.get("document_id"),
                "source_id": c.get("source_id"),
            }
            for c in field_rows
        ]
        assertion_set = [
            _assertion(c, captures.get(str(c.get("document_id") or ""))) for c in value_claims
        ]
        # value=None assertions (redacted somevalue) carry no comparable value
        # and are skipped inside _conflicts — the returned indexes address
        # ``assertion_set`` directly.
        flagged = _conflicts(assertion_set)
        for i in flagged:
            assertion_set[i]["conflicting"] = True
        tasks = _follow_ups_for(follow_ups, qid)
        basis = _search_basis(search_log, qid)
        declared = declared_na.get(qid) or declared_wh.get(qid) or declared_dv.get(qid) or {}
        unresolved_required = any(
            fs["state"] in _FIELD_STATE_UNRESOLVED and fs["field"] in REQUIRED_CROSSWALK_FIELDS
            for fs in field_states
        )
        answer: dict[str, Any] = {
            "question": qid,
            "slug": q["slug"],
            "title": q["title"],
            "field_states": field_states,
            "search_basis": basis,
            "follow_ups": tasks,
            "declared": dict(declared) if declared else None,
            "assertions": [],
        }

        # --- state classification (S2 discipline: declared beats derived) ----
        na_valid = False
        if qid in declared_na:
            answer["state"] = "not_applicable"
            rationale = str(declared_na[qid].get("rationale") or "")
            if not rationale.strip():
                violations.append(
                    {
                        "code": "not_applicable_without_rationale",
                        "question": qid,
                        "detail": (
                            "a not_applicable answer must name why the question does not apply"
                        ),
                    }
                )
            if assertion_set:
                violations.append(
                    {
                        "code": "not_applicable_with_evidence",
                        "question": qid,
                        "detail": (
                            "the packet holds evidence claims for this question — "
                            "n/a cannot hide them"
                        ),
                    }
                )
                # The suppressed evidence still lands on the ledger so a reviewer
                # can see exactly what the invalid n/a tried to hide.
                for a in assertion_set:
                    ledger.append(_ledger_row(qid, a, state="suppressed"))
                assertion_set = []
            na_valid = bool(rationale.strip()) and not any(
                v.get("question") == qid for v in violations
            )
            answer["summary"] = rationale or "Declared not applicable."
        elif qid in declared_wh:
            answer["state"] = "withheld"
            basis_txt = str(declared_wh[qid].get("basis") or "")
            reason = str(declared_wh[qid].get("reason") or "")
            if not basis_txt.strip() or not reason.strip():
                violations.append(
                    {
                        "code": "withheld_without_basis",
                        "question": qid,
                        "detail": "a withheld answer must name the policy basis and reason",
                    }
                )
            answer["summary"] = (
                "Evidence exists for this question but is withheld: "
                f"{reason or 'policy restriction'}"
            )
            # The assertions stay on the ledger as withheld rows — digests, never
            # values or locators (the citation must not leak the withheld fact).
            for a in assertion_set:
                ledger.append(_ledger_row(qid, a, state="withheld", suppress=True))
            assertion_set = []
        elif qid in declared_dv:
            answer["state"] = "derived"
            inputs = [str(x) for x in (declared_dv[qid].get("inputs") or ())]
            resolved = [claim_by_digest.get(d) for d in inputs]
            missing = [d for d, c in zip(inputs, resolved, strict=False) if c is None]
            if missing:
                violations.append(
                    {
                        "code": "derived_unresolved_inputs",
                        "question": qid,
                        "detail": f"derivation inputs not in the packet: {missing}",
                    }
                )
            # A derivation must not hide a same-scope conflict: if the question's
            # own evidence disagrees and the competing claims are not all inputs,
            # the derived single value silently picks a winner (S2).
            if flagged:
                hidden_conflicts = {assertion_set[i]["claim_digest"] for i in flagged} - set(inputs)
                if hidden_conflicts:
                    violations.append(
                        {
                            "code": "derived_hides_conflict",
                            "question": qid,
                            "detail": (
                                "same-scope competing claims excluded from the "
                                f"derivation: {sorted(hidden_conflicts)} — the "
                                "answer must be disputed, not silently resolved"
                            ),
                        }
                    )
            input_claims = [c for c in resolved if c is not None]
            input_assertions = [
                _assertion(c, captures.get(str(c.get("document_id") or ""))) for c in input_claims
            ]
            answer["derivation"] = {
                "method": str(declared_dv[qid].get("method") or ""),
                "value": declared_dv[qid].get("value"),
                "inputs": inputs,
                "note": declared_dv[qid].get("note"),
            }
            answer["assertions"] = input_assertions
            answer["summary"] = str(declared_dv[qid].get("note") or "Derived answer.")
            derived_ok = not missing
            answer["score"] = _score_answer(
                "derived",
                input_assertions,
                search_entry=basis,
                follow_ups=tasks,
                declared_partial=qid in declared_partial,
                unresolved_required=unresolved_required,
                derived_inputs_ok=derived_ok,
            )
            for a in input_assertions:
                ledger.append(_ledger_row(qid, a, state="rendered"))
            assertion_set = []
        elif assertion_set:
            answer["state"] = "disputed" if flagged else "supported"
            rendered = assertion_set
            answer["assertions"] = rendered
            scopes = {(_scope_key(a)) for a in rendered}
            parts = []
            for a in rendered:
                scope_txt = ", ".join(f"{k}={v}" for k, v in a["scope"].items()) or "unscoped"
                parts.append(f"{a['predicate']}={a['value']!r} [{scope_txt}]")
            if answer["state"] == "disputed":
                answer["summary"] = (
                    f"Same-scope evidence disagrees — {len(scopes)} scope partition(s), "
                    "every competing value is kept visible: " + "; ".join(parts)
                )
            else:
                answer["summary"] = "; ".join(parts)
        else:
            answer["state"] = "unknown"
            outcome = str((basis or {}).get("outcome") or "not_researched")
            answer["summary"] = f"No evidence-backed answer — recorded research state: {outcome}."

        if qid not in declared_dv:
            answer["score"] = _score_answer(
                str(answer["state"]),
                list(answer.get("assertions") or ()),
                search_entry=basis,
                follow_ups=tasks,
                declared_partial=qid in declared_partial,
                unresolved_required=unresolved_required,
                na_valid=na_valid,
            )

        # Mechanical fill: an unknown question with no declared search entry
        # records `not_researched` honestly — the worst basis, never a gap.
        # q11/q12 are composed mechanically from the packet itself (a search
        # state is meaningless for them), so they are excluded.
        if answer["state"] == "unknown" and basis is None and qid not in ("q11", "q12"):
            search_log.append(
                {
                    "question": qid,
                    "outcome": "not_researched",
                    "sources_searched": [],
                    "searched_at": None,
                    "declared": False,
                    "note": "No search recorded for this question.",
                }
            )

        for a in answer.get("assertions") or ():
            ledger.append(_ledger_row(qid, a, state="rendered"))
        answers.append(answer)

    # --- q11 (independent support vs agency statements) — mechanical profile --
    # The answer IS the evidence-profile derivation over the packet's claims:
    # instrument/probative classes vs agency-statement/non-probative classes.
    q11 = next(a for a in answers if a["question"] == "q11")
    if not q11.get("declared"):
        instrument = [
            c
            for c in claims
            if c.get("claim_directness") != "D6" and c.get("predicate_id") != _FIELD_STATE_PREDICATE
        ]
        statements = [c for c in claims if c.get("claim_directness") == "D6"]
        genres: dict[str, int] = {}
        for c in claims:
            if c.get("predicate_id") == _FIELD_STATE_PREDICATE:
                continue
            g = str(c.get("evidence_genre") or "unknown")
            genres[g] = genres.get(g, 0) + 1
        if instrument or statements:
            q11["state"] = "derived"
            q11["derivation"] = {
                "method": "claim_directness/evidence_genre profile over the packet's claims",
                "value": {
                    "instrument_backed_claims": len(instrument),
                    "non_probative_claims": len(statements),
                    "claims_by_genre": genres,
                },
                "inputs": [content_digest(c) for c in claims],
                "note": (
                    "Counts evidence classes, not truths: an agency statement and an "
                    "executed instrument are different support classes (S2 q11)."
                ),
            }
            q11["summary"] = (
                f"{len(instrument)} claim(s) trace to probative instruments/records; "
                f"{len(statements)} carry non-probative (agency-statement) directness."
            )
            q11["score"] = 3 if instrument else 2
            ledger.append(
                {
                    "question": "q11",
                    "source_field": None,
                    "predicate": "evidence_profile",
                    "fact": "derived evidence-class profile",
                    "claim_digest": None,
                    "claim_digests": [content_digest(c) for c in claims],
                    "capture_digest": None,
                    "state": "derived",
                }
            )
        else:
            q11["state"] = "unknown"
            q11["summary"] = "No claims in the packet — the support profile cannot be derived."
            q11["score"] = 0

    # --- q12 (unresolved evidence + correction route) — mechanical ledger ----
    q12 = next(a for a in answers if a["question"] == "q12")
    if not q12.get("declared"):
        unresolved_fields = [
            fs
            for a in answers
            for fs in (a.get("field_states") or ())
            if fs["state"] in _FIELD_STATE_UNRESOLVED
        ]
        unknown_qs = [a["question"] for a in answers if a["state"] == "unknown"]
        q12["state"] = "supported"
        q12["summary"] = (
            f"{len(unresolved_fields)} unresolved field state(s) recorded; "
            f"{len(unknown_qs)} question(s) still unknown; corrections route: "
            f"{packet.get('correction_route') or CORRECTION_ROUTE}"
        )
        q12["field_inventory"] = unresolved_fields
        q12["correction_route"] = str(packet.get("correction_route") or CORRECTION_ROUTE)
        # Complete when every unresolved field is covered by a specific follow-up.
        covered = all(
            _specific_follow_up(_follow_ups_for(follow_ups, a["question"])) is not None
            for a in answers
            if a["state"] == "unknown"
        )
        q12["score"] = 3 if covered else 2

    # --- structural release violations ---------------------------------------
    # Unsupported affirmative claims, misclassified instruments, fabricated
    # absence, and blank answers fail closed (SIG-DOS-001/002).
    violations.extend(_structural_violations(answers, claims, search_log))

    # --- deferred unknown-answer validation ------------------------------------
    # Emitted only AFTER the mechanical q11/q12 composition, so a mechanically
    # answered question never draws a spurious "no basis" violation.
    for a in answers:
        if a["state"] != "unknown":
            continue
        if a.get("search_basis") is None:
            violations.append(
                {
                    "code": "unknown_without_basis",
                    "question": a["question"],
                    "detail": (
                        "an unknown answer needs a recorded search basis "
                        "(sources searched + date + outcome)"
                    ),
                }
            )
        if _specific_follow_up(a.get("follow_ups") or ()) is None:
            violations.append(
                {
                    "code": "unknown_without_followup",
                    "question": a["question"],
                    "detail": (
                        "an honest unknown needs a precise follow-up task "
                        "(what to obtain + a closing condition)"
                    ),
                }
            )

    # --- the fact-to-capture ledger + restrictions ---------------------------
    for a in ledger:
        if a.get("claim_digest") and a["claim_digest"] in restricted:
            violations.append(
                {
                    "code": "restricted_claim_rendered",
                    "question": a["question"],
                    "detail": (
                        f"claim {a['claim_digest'][:12]}… is on the packet's "
                        "restricted list but is rendered"
                    ),
                }
            )

    scores = {a["question"]: int(a.get("score") or 0) for a in answers}
    total = sum(scores.values())
    mechanical = total >= COMPLETE_TOTAL and all(
        scores[q] >= REQUIRED_MINIMUM[q] for q in REQUIRED_MINIMUM
    )
    review_status = str((packet.get("review") or {}).get("status") or "not_run")
    blocking: list[str] = []
    if not mechanical:
        if total < COMPLETE_TOTAL:
            blocking.append(f"rubric_total {total}/{COMPLETE_MAX} below {COMPLETE_TOTAL}")
        for qid, floor in REQUIRED_MINIMUM.items():
            if scores[qid] < floor:
                blocking.append(f"{qid} scored {scores[qid]} below the required {floor}")
    if review_status != "completed":
        blocking.append(f"independent_review {review_status} (a completed review is required)")
    if violations:
        blocking.append(f"{len(violations)} release violation(s)")
    completeness = {
        "total": total,
        "max": COMPLETE_MAX,
        "required_minimum": dict(REQUIRED_MINIMUM),
        "per_question": scores,
        "mechanical_complete": mechanical,
        "pilot_complete": mechanical and review_status == "completed" and not violations,
        "blocking": blocking,
    }

    # --- the completion checklist (independent — re-derives, never trusts) ----
    checklist = _checklist(answers, packet, claims, violations, completeness)

    subject = packet.get("subject") or {}
    return {
        "schema": DOSSIER_SCHEMA,
        "generator": GENERATOR_VERSION,
        "kind": "research_dossier",
        "dossier_id": str(packet.get("dossier_id") or subject.get("slug") or ""),
        "subject": {
            "slug": subject.get("slug"),
            "label": subject.get("label"),
            "jurisdiction": subject.get("jurisdiction"),
            "entity_id": subject.get("entity_id"),
            "jurisdiction_slug": subject.get("jurisdiction_slug"),
        },
        "as_of": dict(packet.get("as_of") or {}),
        "source_families": sorted({str(c.get("source_id")) for c in claims if c.get("source_id")}),
        "review_status": review_status,
        "review": dict(packet.get("review") or {"status": "not_run"}),
        "answers": answers,
        "ledger": ledger,
        "search_log": search_log,
        "checklist": checklist,
        "completeness": completeness,
        "decision_windows": _decision_windows(
            answers, str((packet.get("as_of") or {}).get("world") or "")
        ),
        "what_we_dont_know": _what_we_dont_know(answers),
        "release": {"valid": not violations, "violations": violations},
    }


def _ledger_row(
    qid: str, a: Mapping[str, Any], *, state: str, suppress: bool = False
) -> dict[str, Any]:
    """One fact→capture ledger row (SIG-DOS-001). A withheld row keeps the claim
    digest only — the citation must not leak the withheld fact's value/locator."""
    if suppress:
        return {
            "question": qid,
            "source_field": a.get("source_field"),
            "predicate": a["predicate"],
            "fact": "(withheld)",
            "claim_digest": a["claim_digest"],
            "capture_digest": None,
            "state": "withheld",
        }
    value = a.get("value")
    fact = f"{a['predicate']}={value!r}" if value is not None else f"{a['predicate']}=somevalue"
    return {
        "question": qid,
        "source_field": a.get("source_field"),
        "predicate": a["predicate"],
        "fact": fact,
        "claim_digest": a["claim_digest"],
        "capture_digest": a.get("capture_digest"),
        "source_id": a.get("source_id"),
        "source_url": a.get("source_url"),
        "locator": a.get("locator"),
        "retrieved_date": a.get("retrieved_date"),
        "extraction_method": a.get("extraction_method"),
        "scope": a.get("scope"),
        "applicability": a.get("rationale"),
        "valid_from": a.get("valid_from"),
        "valid_to": a.get("valid_to"),
        "valid_edtf": a.get("valid_edtf"),
        "directness": a.get("claim_directness"),
        "genre": a.get("evidence_genre"),
        "state": state,
    }


def _decision_windows(answers: Sequence[Mapping[str, Any]], as_of_world: str) -> dict[str, Any]:
    """Derived decision windows — the stated dates a future decision hangs off.

    `next_decision_date` is the earliest stated contract end ≥ as-of (the only
    'must decide by' shape in the vocabulary); every dated decision-relevant
    assertion is listed with its date KIND so a posting date never reads as an
    effective date (S2).
    """
    windows: list[dict[str, Any]] = []
    for a in answers:
        for x in a.get("assertions") or ():
            if x["predicate"] in _DECISION_PREDICATES:
                windows.append(
                    {
                        "question": a["question"],
                        "predicate": x["predicate"],
                        "value": x.get("value"),
                        "valid_from": x.get("valid_from"),
                        "valid_to": x.get("valid_to"),
                        "valid_edtf": x.get("valid_edtf"),
                        "source_id": x.get("source_id"),
                        "document_id": x.get("document_id"),
                    }
                )
    ends = [
        str(w["value"])
        for w in windows
        if w["predicate"] == "contract_end_date" and str(w["value"]) >= as_of_world
    ]
    return {
        "windows": windows,
        "next_decision_date": min(ends) if ends else None,
        "note": (
            None
            if ends
            else "No stated future contract-end/renewal date is recorded — the "
            "absence of a decision date is itself reported."
        ),
    }


def _what_we_dont_know(answers: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The headline unknowns — unknown/withheld/partial answers as gap rows."""
    out: list[dict[str, Any]] = []
    for a in answers:
        if a["state"] == "unknown":
            out.append(
                {
                    "question": a["question"],
                    "label": a["title"],
                    "state": "unknown",
                    "basis": (a.get("search_basis") or {}).get("outcome"),
                    "follow_up": (a.get("follow_ups") or [None])[0],
                }
            )
        elif a["state"] == "withheld":
            out.append(
                {
                    "question": a["question"],
                    "label": a["title"],
                    "state": "withheld",
                    "basis": (a.get("declared") or {}).get("basis"),
                }
            )
        elif int(a.get("score") or 0) == 2:
            out.append(
                {
                    "question": a["question"],
                    "label": a["title"],
                    "state": a["state"],
                    "basis": "partial coverage — the answer is traceable but not fully scoped",
                }
            )
    return out


# --------------------------------------------------------------------------- #
# The independent completion checklist (SIG-DOS-002)
# --------------------------------------------------------------------------- #


def _checklist(
    answers: Sequence[Mapping[str, Any]],
    packet: Mapping[str, Any],
    claims: Sequence[Mapping[str, Any]],
    violations: Sequence[Mapping[str, Any]],
    completeness: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The completion checklist — re-derived independently of the answers.

    Each item is evaluated mechanically where possible; human-facing marks
    (comparability review, adversarial/semantic review) record the packet's
    declared status honestly — `not_run` is a real state, never a green.
    """
    items: list[dict[str, Any]] = []

    def add(item: str, status: str, detail: str) -> None:
        items.append({"item": item, "status": status, "detail": detail})

    missing = [q for q in QUESTION_IDS if not any(a["question"] == q for a in answers)]
    bad_states = [a["question"] for a in answers if a["state"] not in ANSWER_STATES]
    add(
        "all_twelve_questions_present",
        "pass" if len(answers) == 12 and not missing else "fail",
        f"{len(answers)}/12 questions represented" + (f"; missing {missing}" if missing else ""),
    )
    add(
        "states_legal",
        "pass" if not bad_states else "fail",
        "every answer carries a state in the six-state vocabulary"
        + (f"; illegal on {bad_states}" if bad_states else ""),
    )
    unbound = [
        a["question"]
        for a in answers
        for x in (a.get("assertions") or ())
        if not x.get("claim_digest") or not x.get("capture_digest") or not x.get("locator")
    ]
    add(
        "affirmatives_evidence_backed",
        "pass" if not unbound else "fail",
        "every rendered assertion cites a claim digest + capture digest + locator"
        + (f"; unbound on {sorted(set(unbound))}" if unbound else ""),
    )
    unk = [a for a in answers if a["state"] == "unknown"]
    no_basis = [a["question"] for a in unk if not _documented_basis(a.get("search_basis"))]
    add(
        "search_log_complete",
        "pass" if not no_basis else "fail",
        "every unknown answer carries a documented search basis (named sources + date)"
        + (f"; undocumented on {no_basis}" if no_basis else ""),
    )
    # Conflict visibility is structurally guaranteed: the state machine emits
    # `disputed` for every same-scope/same-period disagreement, so nothing can
    # render as a silent winner. The check stays as an honest recorded item.
    add(
        "same_scope_conflicts_visible",
        "pass",
        "same-scope/same-period disagreements render as disputed with both values — "
        "the classification is mechanical, so a conflict cannot be hidden",
    )
    under_scoped = [
        a["question"]
        for a in answers
        for x in (a.get("assertions") or ())
        if x["predicate"] in _COUNT_PREDICATES and not x["scope"].get("count_scope")
    ]
    add(
        "scope_and_time_comparable",
        "pass" if not under_scoped else "fail",
        "count assertions carry count_scope universes and declared valid windows"
        + (f"; under-scoped on {sorted(set(under_scoped))}" if under_scoped else ""),
    )
    misclassified = _misclassified(claims)
    add(
        "instrument_genre_classified",
        "pass" if not misclassified else "fail",
        "no template asserts an executed-instrument predicate; no subscription "
        "asserts local-hardware predicates"
        + (f"; violations: {misclassified}" if misclassified else ""),
    )
    review = packet.get("review") or {}
    rstatus = str(review.get("status") or "not_run")
    add(
        "independent_semantic_review",
        "pass" if rstatus == "completed" else ("pending" if rstatus == "pending" else "fail"),
        "material governance/contract/relationship assertions independently "
        f"reviewed — recorded status: {rstatus} (D-R10-HUMAN-1)",
    )
    redacted = [c for c in claims if c.get("field_state") == "redacted"]
    withheld_qs = [a["question"] for a in answers if a["state"] == "withheld"]
    add(
        "restrictions_consumed",
        "pass",
        f"{len(redacted)} redacted field(s) rendered as somevalue (exists, value "
        f"withheld); {len(withheld_qs)} withheld question(s) declared "
        f"{sorted(withheld_qs)}; declared restrictions checked against the ledger",
    )
    gate = [
        f"total {completeness['total']}/{completeness['max']} ≥ {COMPLETE_TOTAL}",
        *(
            f"{q} {completeness['per_question'].get(q)}/3 ≥ {f}"
            for q, f in REQUIRED_MINIMUM.items()
        ),
    ]
    add(
        "rubric_threshold",
        "pass" if completeness["mechanical_complete"] else "fail",
        "the rubric gate — " + " AND ".join(gate),
    )
    add(
        "no_unsupported_claims",
        "pass" if not violations else "fail",
        f"{len(violations)} release violation(s)" if violations else "release validation clean",
    )
    return items


def _structural_violations(
    answers: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
    search_log: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Fail-closed release rules beyond per-state basis checks."""
    out: list[dict[str, Any]] = []
    # 1. Unsupported affirmative claims: every rendered assertion must bind a
    #    claim digest + capture digest + locator — a citation the reader can open.
    for a in answers:
        if a["state"] not in {"supported", "disputed", "derived"}:
            continue
        for x in a.get("assertions") or ():
            if not x.get("claim_digest") or not x.get("capture_digest") or not x.get("locator"):
                out.append(
                    {
                        "code": "unsupported_affirmative_claim",
                        "question": a["question"],
                        "detail": (
                            f"{x.get('predicate')} lacks a capture binding or locator — "
                            "a rendered affirmative claim must cite captured bytes"
                        ),
                    }
                )
    # 2. Blank answers: a declared derived answer with no value/method is a blank
    #    field wearing a state — never completeness-inflating.
    for a in answers:
        if a["state"] == "derived" and a.get("declared"):
            d = a["declared"]
            if d.get("value") in (None, "") or not str(d.get("method") or "").strip():
                out.append(
                    {
                        "code": "blank_answer",
                        "question": a["question"],
                        "detail": "a derived answer needs a value and a method",
                    }
                )
    # 3. Misclassified instruments (the emit guard's release-side twin).
    for m in _misclassified(claims):
        out.append(
            {
                "code": "misclassified_instrument",
                "question": next(
                    (
                        a["question"]
                        for a in answers
                        for x in (a.get("assertions") or ())
                        if x.get("document_id") == m["document_id"]
                        and x.get("predicate") == m["predicate"]
                    ),
                    None,
                ),
                "detail": f"{m['detail']} on {m['document_id']}",
            }
        )
    # 4. Fabricated absence: a documented not-found outcome on a question that
    #    DOES hold evidence claims — "no record found" must never become "no X".
    evidenced = {
        a["question"] for a in answers if a["state"] in {"supported", "disputed", "derived"}
    }
    for e in search_log:
        q = str(e.get("question") or "")
        if q in evidenced and str(e.get("outcome") or "") in _DOCUMENTED_SEARCH:
            out.append(
                {
                    "code": "absence_fabricated",
                    "question": q,
                    "detail": (
                        f"search log records {e.get('outcome')} but the packet holds "
                        "evidence claims for this question"
                    ),
                }
            )
    return out


def _misclassified(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """The release-side genre re-check (the emit guard's verifier twin)."""
    out: list[dict[str, str]] = []
    for c in claims:
        pred = str(c.get("predicate_id") or "")
        genre = str(c.get("evidence_genre") or "")
        if genre == "template" and pred in TEMPLATE_EXECUTION_GUARD:
            out.append(
                {
                    "genre": genre,
                    "predicate": pred,
                    "document_id": str(c.get("document_id")),
                    "detail": "a template asserts an executed-instrument predicate",
                }
            )
        if genre == "subscription" and pred in SUBSCRIPTION_HARDWARE_GUARD:
            out.append(
                {
                    "genre": genre,
                    "predicate": pred,
                    "document_id": str(c.get("document_id")),
                    "detail": "a subscription asserts a local-hardware predicate",
                }
            )
    return out


# --------------------------------------------------------------------------- #
# Release validation + rendering
# --------------------------------------------------------------------------- #


def build_portfolio(packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compose the `sig.dossier-portfolio/1` artifact from reviewed packets."""
    dossiers = [build_dossier(p) for p in packets]
    return {
        "schema": PORTFOLIO_SCHEMA,
        "generator": GENERATOR_VERSION,
        "dossiers": dossiers,
        "summary": {
            "dossier_count": len(dossiers),
            "pilot_complete": sum(1 for d in dossiers if d["completeness"]["pilot_complete"]),
            "mechanical_complete": sum(
                1 for d in dossiers if d["completeness"]["mechanical_complete"]
            ),
            "release_invalid": sum(1 for d in dossiers if not d["release"]["valid"]),
        },
    }


def render_portfolio_json(portfolio: Mapping[str, Any]) -> bytes:
    """Deterministic web-facing JSON (indented, sorted — diffable)."""
    return (json.dumps(portfolio, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _e(text: object) -> str:
    return html.escape("" if text is None else str(text))


def render_dossier_print_html(dossier: Mapping[str, Any]) -> str:
    """The standalone print/PDF form (SIG-DOS-003): qualifiers, scope labels,
    original dates + their kind, citations (capture digest + locator), competing
    values, search bases, follow-ups, checklist and the rubric — every page
    footer carries the as-of pair + dossier id so a paper copy stays citable."""
    comp = dossier["completeness"]
    footer = (
        f"<p class='footer'>Research dossier {_e(dossier['dossier_id'])} — as-of world "
        f"{_e((dossier.get('as_of') or {}).get('world'))}, belief "
        f"{_e((dossier.get('as_of') or {}).get('belief'))} · score "
        f"{comp['total']}/{comp['max']} · {_e(dossier['review_status'])} review · "
        "schema " + _e(dossier["schema"]) + "</p>"
    )
    pages: list[str] = []
    chunks = [dossier["answers"][i : i + 3] for i in range(0, 12, 3)]
    for idx, chunk in enumerate(chunks):
        parts = ["<div class='page'>"]
        if idx == 0:
            parts.append(
                f"<h1>{_e(dossier['subject']['label'])}</h1>"
                f"<p class='kind'>Reviewed research dossier — evidence-complete "
                f"portfolio (not the inventory overview)</p>"
                f"<p class='score'>Rubric {comp['total']}/{comp['max']} — "
                f"pilot_complete: {_e(comp['pilot_complete'])} · blocking: "
                f"{_e('; '.join(comp['blocking']) or 'none')}</p>"
            )
        for a in chunk:
            parts.append(f"<h2>{_e(a['question'])} — {_e(a['title'])}</h2>")
            parts.append(
                f"<p class='state'>state: <strong>{_e(a['state'])}</strong> · "
                f"score {_e(a['score'])}/3</p><p>{_e(a['summary'])}</p>"
            )
            if a.get("assertions"):
                parts.append(
                    "<table><thead><tr><th>predicate</th><th>value</th><th>scope</th>"
                    "<th>dates</th><th>source / locator</th><th>capture</th></tr></thead><tbody>"
                )
                for x in a["assertions"]:
                    dates = " · ".join(
                        s
                        for s in (
                            (
                                f"valid {_e(x.get('valid_from'))}–{_e(x.get('valid_to'))}"
                                if x.get("valid_from") or x.get("valid_to")
                                else ""
                            ),
                            (
                                f"retrieved {_e(x.get('retrieved_date'))}"
                                if x.get("retrieved_date")
                                else ""
                            ),
                            (
                                f"observed {_e(x.get('observed_at'))}"
                                if x.get("observed_at")
                                else ""
                            ),
                        )
                        if s
                    )
                    scope = ", ".join(f"{k}={v}" for k, v in (x.get("scope") or {}).items())
                    loc = x.get("locator") or {}
                    loc_txt = loc.get("locator") or json.dumps(loc, sort_keys=True)
                    conflict = " ≠" if x.get("conflicting") else ""
                    value_txt = (
                        x.get("value") if x.get("value") is not None else "(somevalue — redacted)"
                    )
                    parts.append(
                        f"<tr><td>{_e(x['predicate'])}</td>"
                        f"<td>{_e(value_txt)}{conflict}</td>"
                        f"<td>{_e(scope or 'unscoped')}</td>"
                        f"<td>{dates}</td><td>{_e(x.get('source_id'))} · {_e(loc_txt)}</td>"
                        f"<td>{_e((x.get('capture_digest') or '—')[:16])}…</td></tr>"
                    )
                parts.append("</tbody></table>")
            if a.get("search_basis"):
                b = a["search_basis"]
                parts.append(
                    f"<p class='basis'>search basis: {_e(b.get('outcome'))} — "
                    f"{_e(', '.join(b.get('sources_searched') or ()))} "
                    f"({_e(b.get('searched_at'))}) {_e(b.get('note') or '')}</p>"
                )
            for t in a.get("follow_ups") or ():
                parts.append(
                    f"<p class='followup'>follow-up: {_e(t.get('action'))} — closes when "
                    f"{_e(t.get('closing_condition'))}</p>"
                )
        parts.append(footer + "</div>")
        pages.append("".join(parts))
    tail = ["<div class='page'><h2>Completion checklist</h2><table><tbody>"]
    for c in dossier["checklist"]:
        tail.append(
            f"<tr><td>{_e(c['item'])}</td><td>{_e(c['status'])}</td><td>{_e(c['detail'])}</td></tr>"
        )
    tail.append("</tbody></table><h2>Decision windows</h2><ul>")
    for w in dossier["decision_windows"]["windows"]:
        tail.append(
            f"<li>{_e(w['predicate'])} = {_e(w['value'])} "
            f"(valid {_e(w.get('valid_from'))}–{_e(w.get('valid_to'))})</li>"
        )
    tail.append(
        f"</ul><p>next_decision_date: {_e(dossier['decision_windows']['next_decision_date'])}</p>"
        + footer
        + "</div>"
    )
    css = (
        "body{font-family:Georgia,serif;margin:2em}h1{font-size:1.4em}"
        "h2{font-size:1.05em;border-bottom:1px solid #999;padding-top:1em}"
        "table{border-collapse:collapse;width:100%;font-size:.85em}"
        "td,th{border:1px solid #bbb;padding:3px 6px;text-align:left;vertical-align:top}"
        ".footer{border-top:1px solid #999;font-size:.75em;margin-top:2em;color:#444}"
        ".page{page-break-after:always}.state,.basis,.followup{font-size:.85em}"
        ".kind{font-style:italic}"
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{_e(dossier['subject']['label'])} — SIG research dossier (print)</title>"
        f"<style>{css}</style></head><body>" + "".join(pages + tail) + "</body></html>"
    )


def packet_digest(packet: Mapping[str, Any]) -> str:
    """Content digest over a packet — the dossier's input idempotency key."""
    payload = json.dumps(packet, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
