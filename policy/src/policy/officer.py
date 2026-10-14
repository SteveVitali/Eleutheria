# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The officer-naming test (§43.4, SIG-PUB-007..010).

A named individual MAY be published **only** if all five prongs hold *and* two
independent reviewers concur in writing (SIG-PUB-007/008). This module is the
deterministic gate; the concurrence itself is an agentic, recorded act. The gate
defaults to no-publish on any disagreement or missing prong, and records the
decision, its reasoning, and its reviewers.

Two categorical carve-outs sit outside the test entirely:

* Home addresses are never publishable under any prong (SIG-PUB-009) — they are
  categorically excluded (SIG-PUB-003).
* Routine audit-log rows naming an officer MUST NOT trigger the test, because
  they MUST NOT be ingested at all (SIG-PUB-010, §18.1).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._data import load_json_table


@dataclass(frozen=True)
class OfficerNamingProngs:
    """The five prongs of SIG-PUB-007. A name may be published only if all hold."""

    #: 1. The claim concerns official conduct, not private life.
    official_conduct: bool
    #: 2. The name appears on the face of an R1/R2 record — never inferred/assembled.
    name_on_face_of_record: bool
    #: 3. The record is public in the jurisdiction that produced it.
    record_public_in_jurisdiction: bool
    #: 4. The accountability claim genuinely fails without the name.
    claim_fails_without_name: bool
    #: 5. Severity, currency, and safety are proportionate.
    proportionate: bool

    def all_hold(self) -> bool:
        return (
            self.official_conduct
            and self.name_on_face_of_record
            and self.record_public_in_jurisdiction
            and self.claim_fails_without_name
            and self.proportionate
        )

    def failed(self) -> tuple[str, ...]:
        """The names of the prongs that do not hold (for the recorded reasoning)."""
        checks = {
            "official_conduct": self.official_conduct,
            "name_on_face_of_record": self.name_on_face_of_record,
            "record_public_in_jurisdiction": self.record_public_in_jurisdiction,
            "claim_fails_without_name": self.claim_fails_without_name,
            "proportionate": self.proportionate,
        }
        return tuple(name for name, ok in checks.items() if not ok)


@dataclass(frozen=True)
class ReviewerConcurrence:
    """One reviewer's written position (SIG-PUB-008)."""

    reviewer_id: str
    agrees: bool
    rationale: str
    #: Reviewers must be independent of each other.
    independent: bool = True


@dataclass(frozen=True)
class OfficerNamingDecision:
    """The recorded outcome of the officer-naming test (SIG-PUB-008)."""

    permitted: bool
    reason: str
    prongs: OfficerNamingProngs | None = None
    reviewers: tuple[ReviewerConcurrence, ...] = field(default_factory=tuple)


def _concurrence_ok(reviewers: tuple[ReviewerConcurrence, ...]) -> tuple[bool, str]:
    written = [r for r in reviewers if r.independent and r.rationale.strip()]
    distinct = {r.reviewer_id for r in written}
    if len(distinct) < 2:
        return False, "fewer than two independent reviewers recorded a written position"
    if not all(r.agrees for r in written):
        # Disagreement defaults to no-publish (SIG-PUB-008).
        return False, "reviewers did not concur; disagreement defaults to no-publish"
    return True, "two independent reviewers concurred in writing"


def evaluate_officer_naming(
    prongs: OfficerNamingProngs,
    reviewers: tuple[ReviewerConcurrence, ...],
    *,
    is_home_address: bool = False,
    is_routine_audit_row: bool = False,
) -> OfficerNamingDecision:
    """Decide whether a person-named claim may be published (§43.4).

    Returns a recorded :class:`OfficerNamingDecision`. Publication requires every
    prong to hold *and* two independent reviewers to concur in writing; any
    failure defaults to no-publish.
    """
    if is_home_address:
        return OfficerNamingDecision(
            permitted=False,
            reason="home addresses are outside the test entirely (SIG-PUB-009/003)",
            prongs=prongs,
            reviewers=reviewers,
        )
    if is_routine_audit_row:
        return OfficerNamingDecision(
            permitted=False,
            reason="routine audit-log rows must not trigger the test and must not "
            "be ingested (SIG-PUB-010, §18.1)",
            prongs=prongs,
            reviewers=reviewers,
        )
    if not prongs.all_hold():
        return OfficerNamingDecision(
            permitted=False,
            reason=f"prong(s) not met: {', '.join(prongs.failed())} (SIG-PUB-007)",
            prongs=prongs,
            reviewers=reviewers,
        )
    ok, why = _concurrence_ok(reviewers)
    return OfficerNamingDecision(
        permitted=ok,
        reason=why + (" (SIG-PUB-008)" if not ok else "; all five prongs hold (SIG-PUB-007/008)"),
        prongs=prongs,
        reviewers=reviewers,
    )


# --- the persisted decision record (P35.28, SIG-PUB-007/008, H-9) --------------
#
# ``evaluate_officer_naming`` stays the single decider; this section is its
# persisted side. A naming decision is stored — append-only — in the committed
# data table ``policy/data/officer_naming_decisions.json``
# (``sig.officer-naming-decisions/1``), keyed on the name row's
# ``(subject_id, predicate_id)``. The publication path (the export dossier
# builder, the web dossier gate) reads the LATEST matching record; a missing
# record, a non-concur, an inconsistent record, or a jurisdiction deny all read
# as WITHHOLD — the gate defaults to deny (P35.28). A changed decision is a NEW
# record carrying ``supersedes``, never an edit (P1–P3).
#
# The record is written only by the operator's recorded two-reviewer act — the
# reviewer positions are written human positions, never agent-drafted stand-ins
# (SIG-MEM-009; WV-03/ADR-163 waived only the HG-11 second-reviewer ROLE, never
# this rule) — and by the ingest-side evaluation
# (``connectors.okc_documents.assert_person_naming_permitted`` emits the same
# serialized record via its ``record_sink``, so ingest-time evaluate and
# publish-time gate can never diverge). Until a real concurrence is recorded the
# registry is EMPTY and every public-employee name row withholds.

#: The committed append-only registry's schema tag (data, not code — SIG-LIC-004a).
NAMING_DECISIONS_SCHEMA = "sig.officer-naming-decisions/1"


@dataclass(frozen=True)
class OfficerNamingRecord:
    """One persisted §43.4 decision — the record the publication gate reads.

    Keyed on the name row's ``(subject_id, predicate_id)``; carries the
    evaluation's full inputs (the five prongs, the reviewers' written positions,
    the carve-out flags) so the gate can REPLAY the §43.4 test rather than trust
    the stored ``permitted`` flag — a record whose stored inputs do not replay
    to its recorded verdict is inconsistent and reads as withhold (fail-closed).
    ``decision_id`` is content-derived (sha256 of the canonical payload).
    """

    decision_id: str
    subject_id: str
    predicate_id: str
    permitted: bool
    reason: str
    prongs: OfficerNamingProngs | None = None
    reviewers: tuple[ReviewerConcurrence, ...] = field(default_factory=tuple)
    is_home_address: bool = False
    is_routine_audit_row: bool = False
    #: When the act was recorded (``date -u`` at recording) and by whom/what —
    #: the human reviewer act's own attestation, or the ingest connector's name.
    recorded_at: str = ""
    recorded_by: str = ""
    #: A changed decision is a new record superseding the earlier one (P1–P3).
    supersedes: str | None = None


def _prongs_to_dict(prongs: OfficerNamingProngs) -> dict[str, bool]:
    return {
        "official_conduct": prongs.official_conduct,
        "name_on_face_of_record": prongs.name_on_face_of_record,
        "record_public_in_jurisdiction": prongs.record_public_in_jurisdiction,
        "claim_fails_without_name": prongs.claim_fails_without_name,
        "proportionate": prongs.proportionate,
    }


def _prongs_from_dict(raw: Any) -> OfficerNamingProngs:
    keys = (
        "official_conduct",
        "name_on_face_of_record",
        "record_public_in_jurisdiction",
        "claim_fails_without_name",
        "proportionate",
    )
    if not isinstance(raw, dict) or any(not isinstance(raw.get(k), bool) for k in keys):
        raise ValueError(
            f"{NAMING_DECISIONS_SCHEMA}: a record's 'prongs' must carry the five "
            f"SIG-PUB-007 prongs as booleans ({', '.join(keys)})"
        )
    return OfficerNamingProngs(*(bool(raw[k]) for k in keys))


def _reviewer_from_dict(raw: Any) -> ReviewerConcurrence:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("reviewer_id"), str)
        or not isinstance(raw.get("agrees"), bool)
        or not isinstance(raw.get("rationale"), str)
    ):
        raise ValueError(
            f"{NAMING_DECISIONS_SCHEMA}: a reviewer needs reviewer_id (str), "
            "agrees (bool) and rationale (str)"
        )
    return ReviewerConcurrence(
        reviewer_id=raw["reviewer_id"],
        agrees=raw["agrees"],
        rationale=raw["rationale"],
        independent=bool(raw.get("independent", True)),
    )


def record_to_dict(record: OfficerNamingRecord) -> dict[str, Any]:
    """The canonical wire form of a naming-decision record."""
    out: dict[str, Any] = {
        "decision_id": record.decision_id,
        "subject_id": record.subject_id,
        "predicate_id": record.predicate_id,
        "permitted": record.permitted,
        "reason": record.reason,
        "prongs": _prongs_to_dict(record.prongs) if record.prongs is not None else None,
        "reviewers": [
            {
                "reviewer_id": r.reviewer_id,
                "agrees": r.agrees,
                "rationale": r.rationale,
                "independent": r.independent,
            }
            for r in record.reviewers
        ],
        "is_home_address": record.is_home_address,
        "is_routine_audit_row": record.is_routine_audit_row,
        "recorded_at": record.recorded_at,
        "recorded_by": record.recorded_by,
        "supersedes": record.supersedes,
    }
    return out


def _record_from_dict(raw: Any) -> OfficerNamingRecord:
    """Parse + validate one registry entry; any malformed field raises (fail-closed)."""
    if not isinstance(raw, dict):
        raise ValueError(f"{NAMING_DECISIONS_SCHEMA}: a decision entry must be an object")
    for key in ("decision_id", "subject_id", "predicate_id", "reason"):
        if not isinstance(raw.get(key), str) or not raw[key]:
            raise ValueError(
                f"{NAMING_DECISIONS_SCHEMA}: a decision entry needs a non-empty "
                f"{key!r} (missing in {raw.get('decision_id', '<no id>')!r})"
            )
    if not isinstance(raw.get("permitted"), bool):
        raise ValueError(
            f"{NAMING_DECISIONS_SCHEMA}: 'permitted' must be a boolean ({raw.get('decision_id')!r})"
        )
    supersedes = raw.get("supersedes")
    if supersedes is not None and not isinstance(supersedes, str):
        raise ValueError(f"{NAMING_DECISIONS_SCHEMA}: 'supersedes' must be a string or null")
    return OfficerNamingRecord(
        decision_id=raw["decision_id"],
        subject_id=raw["subject_id"],
        predicate_id=raw["predicate_id"],
        permitted=raw["permitted"],
        reason=raw["reason"],
        prongs=_prongs_from_dict(raw["prongs"]) if raw.get("prongs") is not None else None,
        reviewers=tuple(_reviewer_from_dict(r) for r in raw.get("reviewers", [])),
        is_home_address=bool(raw.get("is_home_address", False)),
        is_routine_audit_row=bool(raw.get("is_routine_audit_row", False)),
        recorded_at=str(raw.get("recorded_at", "")),
        recorded_by=str(raw.get("recorded_by", "")),
        supersedes=supersedes,
    )


def _record_content_id(record: OfficerNamingRecord) -> str:
    """The content-derived decision id: sha256 over the canonical payload."""
    payload = {k: v for k, v in record_to_dict(record).items() if k != "decision_id"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "ond-" + hashlib.sha256(blob.encode()).hexdigest()[:24]


def decision_to_record(
    subject_id: str,
    predicate_id: str,
    decision: OfficerNamingDecision,
    *,
    recorded_at: str,
    recorded_by: str,
    supersedes: str | None = None,
    is_home_address: bool = False,
    is_routine_audit_row: bool = False,
) -> OfficerNamingRecord:
    """Serialize an :func:`evaluate_officer_naming` outcome as a persisted record.

    This is the single ingest→persist serializer: the ingest-side evaluation and
    the operator's recorded concurrence both land through it, so the publication
    gate reads the same decision object the evaluation produced — never a
    recomputed-at-render evaluation. The carve-out flags travel with the record
    so the gate's replay preserves the SIG-PUB-009/010 refusals verbatim.
    """
    record = OfficerNamingRecord(
        decision_id="",
        subject_id=subject_id,
        predicate_id=predicate_id,
        permitted=decision.permitted,
        reason=decision.reason,
        prongs=decision.prongs,
        reviewers=decision.reviewers,
        is_home_address=is_home_address,
        is_routine_audit_row=is_routine_audit_row,
        recorded_at=recorded_at,
        recorded_by=recorded_by,
        supersedes=supersedes,
    )
    return OfficerNamingRecord(**{**record.__dict__, "decision_id": _record_content_id(record)})


def _decisions_from_table(table: Any) -> tuple[OfficerNamingRecord, ...]:
    """Validate a parsed registry table and return its records in append order."""
    if not isinstance(table, dict) or table.get("schema") != NAMING_DECISIONS_SCHEMA:
        raise ValueError(
            f"not a valid {NAMING_DECISIONS_SCHEMA} table "
            f"(schema: {table.get('schema') if isinstance(table, dict) else type(table)!r})"
        )
    decisions = table.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError(f"{NAMING_DECISIONS_SCHEMA}: 'decisions' must be a list")
    return tuple(_record_from_dict(raw) for raw in decisions)


def load_naming_decisions() -> tuple[OfficerNamingRecord, ...]:
    """The committed officer-naming decision registry, in append order.

    A malformed table raises — the registry is the gate's only evidence, so a
    corrupt one fails LOUD at build time rather than silently withholding (or
    worse, silently permitting).
    """
    return _decisions_from_table(load_json_table("officer_naming_decisions"))


def naming_decisions_path() -> Path:
    """The committed registry file ``append_decision`` writes by default."""
    return Path(__file__).resolve().parent / "data" / "officer_naming_decisions.json"


def latest_decision_for(
    subject_id: str,
    predicate_id: str,
    decisions: Any = None,
) -> OfficerNamingRecord | None:
    """The latest record governing a name row's ``(subject_id, predicate_id)``.

    Append order IS supersede order: the last matching entry governs (a changed
    decision is appended with ``supersedes``, never edited in place — P1–P3).
    ``decisions=None`` reads the committed registry.
    """
    rows = load_naming_decisions() if decisions is None else decisions
    latest: OfficerNamingRecord | None = None
    for record in rows:
        if record.subject_id == subject_id and record.predicate_id == predicate_id:
            latest = record
    return latest


def evaluate_record(record: OfficerNamingRecord) -> OfficerNamingDecision:
    """Replay the §43.4 test over the record's stored inputs.

    The gate never trusts the stored ``permitted`` flag alone: the record must
    carry the inputs the decision rested on, and they are re-evaluated. A record
    without stored prongs replays as all-false (deny).
    """
    return evaluate_officer_naming(
        record.prongs or OfficerNamingProngs(False, False, False, False, False),
        record.reviewers,
        is_home_address=record.is_home_address,
        is_routine_audit_row=record.is_routine_audit_row,
    )


def record_concurs(record: OfficerNamingRecord) -> bool:
    """Whether a persisted record establishes the two-reviewer concurrence.

    Fail-closed in both directions: the record's stored verdict must be a permit
    AND the replay of its stored inputs must agree — a record claiming a permit
    whose stored prongs/reviewers do not concur is inconsistent and withholds.
    """
    return record.permitted and evaluate_record(record).permitted


@dataclass(frozen=True)
class NamingGateVerdict:
    """The publication gate's verdict for one public-employee-name row (§43.4+§43.8)."""

    permitted: bool
    reason: str
    #: The governing record's id when one exists — a permitted row carries it as
    #: provenance; a withheld row carries it as the recorded refusal.
    decision_id: str | None = None


def employee_name_publishable(
    subject_id: str,
    predicate_id: str,
    *,
    subject_jurisdiction: str,
    record_origin_jurisdiction: str,
    decisions: Any = None,
) -> NamingGateVerdict:
    """The publication-path officer-naming gate (SIG-PUB-007/008 + SIG-PUB-017).

    A public-employee name is publishable only where BOTH legs permit: a
    persisted two-reviewer concur record naming this row's
    ``(subject_id, predicate_id)`` AND the jurisdiction rule
    (:func:`policy.publication.publication_permitted`). Absent record, a
    non-concur or inconsistent record, a failed prong, or an unknown/restrictive
    jurisdiction all withhold — the default is deny.
    """
    from .publication import publication_permitted

    record = latest_decision_for(subject_id, predicate_id, decisions)
    record_ok = record is not None and record_concurs(record)
    jurisdiction_ok = publication_permitted(
        subject_jurisdiction,
        record_origin_jurisdiction,
        is_public_employee_name=True,
    )
    if record_ok and jurisdiction_ok:
        assert record is not None
        return NamingGateVerdict(
            True,
            "persisted two-reviewer concurrence (SIG-PUB-008) and both "
            "jurisdictions permit (SIG-PUB-017)",
            record.decision_id,
        )
    reasons: list[str] = []
    if record is None:
        reasons.append(
            "no persisted officer-naming decision names this row (SIG-PUB-007/008 — default deny)"
        )
    elif not record_ok:
        reasons.append(f"persisted decision {record.decision_id} does not concur ({record.reason})")
    if not jurisdiction_ok:
        reasons.append("the jurisdiction rule does not permit (SIG-PUB-017)")
    return NamingGateVerdict(
        False,
        "; ".join(reasons),
        record.decision_id if record is not None else None,
    )


def append_decision(
    record: OfficerNamingRecord, *, table_path: Path | None = None
) -> OfficerNamingRecord:
    """Append a naming decision to the registry — the recording act.

    This is the ONLY write path to the committed table, and it is append-only:
    the table must parse as :data:`NAMING_DECISIONS_SCHEMA`, the record must be
    well-formed (non-empty match keys, ``recorded_at``/``recorded_by``), its
    stored ``permitted`` must agree with a replay of its own inputs (an
    inconsistent record is refused — the stored flag is never trusted), the
    ``decision_id`` must not already be present, and a ``supersedes`` pointer
    must name an existing decision. Nothing is ever edited or deleted (P1–P3).
    """
    path = table_path or naming_decisions_path()
    table = json.loads(path.read_text(encoding="utf-8"))
    existing = _decisions_from_table(table)
    if not record.subject_id or not record.predicate_id:
        raise ValueError(
            "a naming-decision record needs non-empty subject_id + predicate_id "
            "(the match keys the publication gate looks up)"
        )
    if not record.recorded_at or not record.recorded_by:
        raise ValueError(
            "a naming-decision record needs recorded_at + recorded_by — the "
            "recording act's provenance (OM-04)"
        )
    replay = evaluate_record(record)
    if replay.permitted != record.permitted:
        raise ValueError(
            f"inconsistent naming-decision record {record.decision_id!r}: the "
            f"stored 'permitted'={record.permitted} disagrees with a replay of "
            f"its own inputs ({replay.reason}) — the stored flag is never trusted"
        )
    if any(r.decision_id == record.decision_id for r in existing):
        raise ValueError(
            f"decision {record.decision_id!r} is already recorded; a changed "
            "decision is a NEW record carrying 'supersedes', never an edit"
        )
    if record.supersedes is not None and not any(
        r.decision_id == record.supersedes for r in existing
    ):
        raise ValueError(
            f"'supersedes' names {record.supersedes!r}, which is not a recorded decision id"
        )
    table["decisions"].append(record_to_dict(record))
    path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
