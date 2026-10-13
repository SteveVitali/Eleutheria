# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ADR-124 allow-disposition verb + flagged-organisation census (P34.26,
SIG-TRUST-006 / SIG-ONTO-013 / SIG-PUB-002 / SIG-STORE-011, F-452).

G2-ADR124 + D-K2-1 [A-10] ("auto-allow + absence only", ADR-159): an
organisation review-flagged by ``organization.publication_review_required``
is auto-allowed ONLY when it carries a tier 0–1 match record to one of the
three approved registries — Census of Governments (``us.census.geoid``), a
SAM UEI (``us.sam.uei``) or a Wikidata QID (``wikidata.qid``) — asserted by an
``ingestion_permitted`` source, and only after the Part VIII person-name
screen passes over its label and literal party values. Every other flagged
organisation stays a typed ``not yet reviewed`` — never an implicit allow,
never an operator review queue (A-10 dropped OP-14).

Two tools, one module:

* ``sig-ops disposition record --allow --from <sig.disposition-list/1>``
  records ``allow`` rows through :func:`db.dispositions.record_disposition`
  — INSERT-only; the registry's immutability trigger and privilege set admit
  no UPDATE/DELETE route. **Dry-run by default**: without ``--apply`` the
  verb verifies every entry against the spine and prints what it *would*
  insert, and writes nothing.
* ``sig-ops disposition census --out-dir <dir>`` runs the read-only census of
  every flagged organisation (degree + edge share, external identifiers
  held, person-name screen result, current disposition, ADR-159 outcome,
  the obligation it owes) and emits the committed ``sig.org-census/1``
  report (``CENSUS.md`` + ``CENSUS.csv`` + ``census.json`` + the
  ``sig.disposition-list/1`` allow list for the eligible rows). Screened
  labels and literal party values are read for the screen only — **never**
  written to any artifact, and label-bearing identifier schemes
  (``sig.org.name`` & friends) are counted, never listed (K2 §3.4; the
  record carries ids + external scheme:value pairs only).

Refusals (fail closed, each a typed verdict — never a silent skip):

* ``person_entity`` — the target is a person (entity_type ``person`` or a
  ``person`` row): ADR-163, persons are never allowed.
* ``not_an_organization`` / ``target_missing`` — not a flagged-or-org row.
* ``org_status_denied`` — ``withdrawn``/``suppressed`` status (ADR-124).
* ``current_deny_disposition`` — a recorded withhold/restrict/withdraw
  governs the entity: an auto rule never overrides a recorded decision.
* ``no_registry_match`` — the claimed identifier is not on the spine (no
  tier 0–1 match record for that registry).
* ``identifier_provenance`` — the match record's asserting claim does not
  trace to an ``ingestion_permitted`` source (ADR-159 item 6).
* ``person_name_screen`` — the Part VIII screen flagged the label, a
  literal party value or the list-carried registry name (screened strings
  are never echoed back).

The census runs on the fixture spine in CI and read-only on ``sig-pg``
through ``SET ROLE sig_read_public`` inside a read-only transaction — the
connection is opened with ``default_transaction_read_only=on`` so the leg
carries zero writes by construction.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from policy.eligibility import (
    POLICY_VERSION,
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

#: The input list schema — what ``--from`` reads.
DISPOSITION_LIST_SCHEMA = "sig.disposition-list/1"
#: The committed census report schema (CENSUS.md's record block / census.json).
CENSUS_SCHEMA = "sig.org-census/1"
#: The dry-run/apply plan the verb prints.
DISPOSITION_PLAN_SCHEMA = "sig.disposition-plan/1"
#: The obligation every flagged organisation owes — appended in DEFERRALS.
OBLIGATION_ID = "D-R11-ADR124-1"

#: ADR-159's three approved registries: census id → the ``entity_identifier``
#: scheme that records the match on the spine.
REGISTRIES: dict[str, dict[str, str]] = {
    "census_of_governments": {
        "scheme": "us.census.geoid",
        "label": "Census of Governments id",
    },
    "sam_uei": {"scheme": "us.sam.uei", "label": "SAM UEI"},
    "wikidata_qid": {"scheme": "wikidata.qid", "label": "Wikidata QID"},
}

#: The auto-allow rule's match tiers (ADR-159 (a): tier 0–1 of the CONF-13
#: cascade). A spine-asserted registry identifier IS the tier-0 match record.
ALLOWED_MATCH_TIERS = frozenset({0, 1})

#: Identifier schemes whose VALUES are the withheld label itself. The census
#: lists external identifiers held (ADR-159 item 6); a name in a committed
#: file would be the label leak `publication_review_required` withholds —
#: screened labels are never written (K2 §3.4).
_LABEL_SCHEMES = frozenset(
    {"sig.org.name", "sig.org.name_scoped", "sig.curator.handle", "sig.person.name"}
)


def _is_label_scheme(scheme: str) -> bool:
    """True when an identifier value IS a name — excluded from artifacts."""
    return scheme in _LABEL_SCHEMES or scheme.endswith((".name", ".name_scoped"))


#: ``reason_category`` stamped on an auto-allow row: the recorded context is
#: the pending-publication-review flag the allow resolves. The public-safe
#: field is honest (the flag IS why the org was dispositioned); the ADR-159
#: rule + registry live in ``authority``.
ALLOW_REASON_CATEGORY = ReasonCategory.REVIEW_PENDING

#: Typed plan/apply verdicts — one per refusal class, never a bare bool.
VERDICT_RECORD = "record"
VERDICT_ALREADY_ALLOWED = "already_allowed"
REFUSAL_PERSON = "refuse:person_entity"
REFUSAL_NOT_ORG = "refuse:not_an_organization"
REFUSAL_TARGET_MISSING = "refuse:target_missing"
REFUSAL_STATUS = "refuse:org_status_denied"
REFUSAL_DENY = "refuse:current_deny_disposition"
REFUSAL_NO_MATCH = "refuse:no_registry_match"
REFUSAL_PROVENANCE = "refuse:identifier_provenance"
REFUSAL_SCREEN = "refuse:person_name_screen"

#: Census ``adr159_outcome`` vocabulary. The two contract classes are
#: ``auto_allow_eligible`` and ``not yet reviewed``; ``already allowed`` and
#: ``recorded deny`` are the honest typed states for an org whose CURRENT
#: recorded disposition already answers the question (never relabelled
#: "not yet reviewed" — a recorded decision was a review).
OUTCOME_AUTO_ALLOW = "auto_allow_eligible"
OUTCOME_ALREADY_ALLOWED = "already allowed"
OUTCOME_RECORDED_DENY = "recorded deny"
OUTCOME_NOT_REVIEWED = "not yet reviewed"

#: Screen flag categories (the matched text is NEVER carried — ids only).
SCREEN_PASS = "pass"
SCREEN_FLAG_PART_VIII = "flag_part_viii"
SCREEN_FLAG_PERSON_NAME = "flag_person_name"

#: The partner_identity refusal reasons that mean "person-shaped" — the
#: never-a-person rule (ADR-163 / Part VIII). Other refusals (generic_name,
#: single_word, multiple_parties, …) are not person verdicts.
_PERSON_REFUSALS = frozenset({"person_shaped", "sole_proprietor"})

#: ``--decided-by`` names a role or the ADR-159 rule — a lowercase machine
#: token, never a personal name (G2 Step 1). "Jane Smith" cannot validate.
_DECIDED_BY_RE = re.compile(r"^[a-z][a-z0-9_./:-]{1,127}$")

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class DispositionListError(ValueError):
    """A malformed ``sig.disposition-list/1`` input or argument (typed code)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class _Conn(Protocol):
    """The sliver of ``psycopg.Connection`` the verb + census use (injectable)."""

    def execute(self, query: Any, params: tuple = ()) -> Any: ...

    def transaction(self) -> Any: ...

    def __enter__(self) -> _Conn: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Any: ...


ConnectFactory = Callable[[str], _Conn]


def _connect(dsn: str) -> _Conn:
    """Write-capable connection for ``record --apply`` (INSERT-only via
    :func:`db.dispositions.record_disposition` — no UPDATE/DELETE path
    exists to call)."""
    import psycopg

    return psycopg.connect(dsn, connect_timeout=15, autocommit=False)


def _connect_readonly(dsn: str) -> _Conn:
    """The census leg's connection: ``default_transaction_read_only`` pinned
    server-side + a 60 s statement bound — the read-only role over the proxy
    can never hold a write the session could not even express."""
    import psycopg

    return psycopg.connect(
        dsn,
        connect_timeout=15,
        autocommit=True,
        options="-c default_transaction_read_only=on -c statement_timeout=60000",
    )


# --------------------------------------------------------------------------- #
# sig.disposition-list/1 — the input record
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AllowEntry:
    """One ``sig.disposition-list/1`` entry: a claimed registry auto-allow."""

    entity_id: str
    registry: str  # one of REGISTRIES
    scheme: str  # must equal REGISTRIES[registry]["scheme"]
    value: str
    match_tier: int  # must be in ALLOWED_MATCH_TIERS
    registry_name: str | None = None  # screened when present, never emitted
    note: str | None = None


@dataclass(frozen=True)
class DispositionList:
    """A parsed + validated ``sig.disposition-list/1`` file."""

    list_id: str
    policy_version: str
    entries: tuple[AllowEntry, ...]
    generated_at: str | None = None
    note: str | None = None


def _entry_from(obj: Any, idx: int) -> AllowEntry:
    where = f"entries[{idx}]"
    if not isinstance(obj, Mapping):
        raise DispositionListError("bad_entry", f"{where} is not an object")
    entity_id = str(obj.get("entity_id") or "").strip()
    if not _UUID_RE.match(entity_id):
        raise DispositionListError("bad_entry", f"{where}.entity_id is not a uuid")
    registry = str(obj.get("registry") or "").strip()
    if registry not in REGISTRIES:
        raise DispositionListError(
            "bad_entry",
            f"{where}.registry {registry!r} is not one of {sorted(REGISTRIES)}",
        )
    ident = obj.get("identifier")
    if not isinstance(ident, Mapping):
        raise DispositionListError("bad_entry", f"{where}.identifier is not an object")
    scheme = str(ident.get("scheme") or "").strip()
    value = str(ident.get("value") or "").strip()
    if not value:
        raise DispositionListError("bad_entry", f"{where}.identifier.value is empty")
    expected = REGISTRIES[registry]["scheme"]
    if scheme != expected:
        raise DispositionListError(
            "bad_entry",
            f"{where}.identifier.scheme {scheme!r} does not match registry "
            f"{registry!r} (expected {expected!r})",
        )
    tier_raw = obj.get("match_tier")
    if not isinstance(tier_raw, int) or isinstance(tier_raw, bool):
        raise DispositionListError("bad_entry", f"{where}.match_tier is not an integer")
    if tier_raw not in ALLOWED_MATCH_TIERS:
        raise DispositionListError(
            "bad_entry",
            f"{where}.match_tier {tier_raw} is outside tier 0–1 (ADR-159 (a))",
        )
    registry_name = obj.get("registry_name")
    note = obj.get("note")
    return AllowEntry(
        entity_id=entity_id.lower(),
        registry=registry,
        scheme=scheme,
        value=value,
        match_tier=tier_raw,
        registry_name=None if registry_name is None else str(registry_name),
        note=None if note is None else str(note),
    )


def load_disposition_list(raw: Any) -> DispositionList:
    """Parse + validate one ``sig.disposition-list/1`` document.

    Entries are returned sorted by ``entity_id`` (deterministic apply order —
    a re-run over the same list evaluates the same way).
    """
    if not isinstance(raw, Mapping):
        raise DispositionListError("bad_list", "document is not an object")
    rtype = str(raw.get("record_type") or "")
    if rtype != DISPOSITION_LIST_SCHEMA:
        raise DispositionListError(
            "bad_list", f"record_type {rtype!r} is not {DISPOSITION_LIST_SCHEMA!r}"
        )
    list_id = str(raw.get("list_id") or "").strip()
    if not list_id:
        raise DispositionListError("bad_list", "list_id is required")
    policy_version = str(raw.get("policy_version") or POLICY_VERSION)
    if policy_version != POLICY_VERSION:
        raise DispositionListError(
            "bad_list",
            f"policy_version {policy_version!r} is not {POLICY_VERSION!r}",
        )
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, Sequence) or isinstance(entries_raw, str):
        raise DispositionListError("bad_list", "entries is not an array")
    entries = [_entry_from(e, i) for i, e in enumerate(entries_raw)]
    # Deterministic order: sorted by entity_id. Duplicate (entity, scheme,
    # value) rows are a malformed list — the second would be dead input.
    entries.sort(key=lambda e: (e.entity_id, e.scheme, e.value))
    seen: set[tuple[str, str, str]] = set()
    for e in entries:
        key = (e.entity_id, e.scheme, e.value)
        if key in seen:
            raise DispositionListError(
                "bad_list", f"duplicate entry for {e.entity_id} {e.scheme}:{e.value}"
            )
        seen.add(key)
    generated_at = raw.get("generated_at")
    note = raw.get("note")
    return DispositionList(
        list_id=list_id,
        policy_version=policy_version,
        entries=tuple(entries),
        generated_at=None if generated_at is None else str(generated_at),
        note=None if note is None else str(note),
    )


def load_disposition_list_file(path: str | Path) -> DispositionList:
    with open(path, encoding="utf-8") as fh:
        return load_disposition_list(json.load(fh))


def validate_actor_fields(*, authority: str, decided_by: str) -> None:
    """``--authority`` + ``--decided-by`` are required; decided_by is a role
    or the ADR-159 rule — a lowercase machine token, never a personal name."""
    if not str(authority or "").strip():
        raise DispositionListError(
            "bad_args", "--authority is required (the ADR-159 rule + registry id)"
        )
    if not _DECIDED_BY_RE.match(str(decided_by or "")):
        raise DispositionListError(
            "bad_args",
            "--decided-by must be a role or rule token "
            "(^[a-z][a-z0-9_./:-]{1,127}$) — never a personal name",
        )


# --------------------------------------------------------------------------- #
# The person-name screen (K2 §3.4 / ADR-159 (d) — runs over every candidate)
# --------------------------------------------------------------------------- #


def screen_name(name: str) -> str | None:
    """Return the flag category for a screened name, or ``None`` when clean.

    Two screens, both Part VIII law:

    * :func:`policy.intake.screen_part_viii` — the forbidden-token +
      person-identifier-pattern screen the contract names verbatim;
    * :func:`resolution.partner_identity.partner_identity` — the
      never-a-person rule (``person_shaped``/``sole_proprietor``): an
      authoritative-registry match never overrides a person-shaped name
      (ADR-159 (d) — sole traders register for UEIs too).
    """
    from policy.intake import screen_part_viii
    from resolution.partner_identity import PartnerRefusal, partner_identity

    text = str(name or "").strip()
    if not text:
        return None
    if screen_part_viii(text) is not None:
        return SCREEN_FLAG_PART_VIII
    verdict = partner_identity(text)
    if isinstance(verdict, PartnerRefusal) and verdict.reason in _PERSON_REFUSALS:
        return SCREEN_FLAG_PERSON_NAME
    return None


# --------------------------------------------------------------------------- #
# Spine reads (every statement is a SELECT — a test greps for write verbs)
# --------------------------------------------------------------------------- #

#: Flagged organisations — the census universe. The label column is selected
#: separately for screening only; it is never part of the emitted row.
_FLAGGED_SQL = (
    "SELECT o.entity_id::text, o.organization_type, o.status "
    "FROM organization o WHERE o.publication_review_required "
    "ORDER BY o.entity_id"
)

#: Every identifier a flagged org carries (external ids held). The asserting
#: claim id is the provenance anchor — ``None`` means unasserted.
_IDENTIFIERS_SQL = (
    "SELECT ei.entity_id::text, ei.scheme, ei.value, ei.asserted_by_claim::text "
    "FROM entity_identifier ei "
    "JOIN organization o ON o.entity_id = ei.entity_id "
    "WHERE o.publication_review_required "
    "ORDER BY ei.entity_id, ei.scheme, ei.value"
)

#: (entity_id, scheme, value, asserting claim) whose provenance reaches an
#: ``ingestion_permitted`` source — the ADR-159 item-6 registry-match test.
_PERMITTED_IDS_SQL = (
    "SELECT DISTINCT ei.entity_id::text, ei.scheme, ei.value, "
    "  ei.asserted_by_claim::text "
    "FROM entity_identifier ei "
    "JOIN claim c ON c.claim_id = ei.asserted_by_claim "
    "JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
    "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    "JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    "JOIN source_registry sr ON sr.source_id = ea.source_id "
    "WHERE sr.ingestion_permitted "
    "  AND ei.entity_id IN (SELECT entity_id FROM organization "
    "                     WHERE publication_review_required)"
)

#: The K2 "organisation edge" — a claim referencing the org as its partner
#: object. degree = DISTINCT subjects; edge share divides by the flagged
#: org graph's distinct (subject, org) pairs (NEW-1's 42,488, re-measured).
_DEGREE_SQL = (
    "SELECT c.object_entity::text, count(DISTINCT c.subject_id) "
    "FROM claim c "
    "JOIN organization o ON o.entity_id = c.object_entity "
    "WHERE o.publication_review_required "
    "GROUP BY c.object_entity"
)

_EDGE_DENOMINATOR_SQL = (
    "SELECT count(*) FROM ("
    "  SELECT DISTINCT c.subject_id, c.object_entity FROM claim c "
    "  JOIN organization o ON o.entity_id = c.object_entity "
    "  WHERE o.publication_review_required"
    ") pairs"
)

#: Literal party values on the flagged org's claims — screened for the
#: person-name test, counted, never emitted (K2 §3.4).
_LITERAL_PARTIES_SQL = (
    "SELECT c.object_entity::text, c.value_text FROM claim c "
    "JOIN organization o ON o.entity_id = c.object_entity "
    "WHERE o.publication_review_required AND c.value_text IS NOT NULL "
    "GROUP BY c.object_entity, c.value_text"
)

#: The materialized-graph degree — live edges over the materialized edge
#: tables (relationship + entity_role + organization_relation incident on
#: the org; closed sys_period rows excluded where the table is bitemporal).
_MATERIALIZED_DEGREE_SQL = (
    "SELECT e.entity_id::text, "
    " (SELECT count(*) FROM relationship r "
    "   WHERE (r.from_entity = e.entity_id OR r.to_entity = e.entity_id) "
    "     AND upper_inf(r.sys_period)) + "
    " (SELECT count(*) FROM entity_role er "
    "   WHERE er.entity_id = e.entity_id OR er.actor_id = e.entity_id) + "
    " (SELECT count(*) FROM organization_relation rel "
    "   WHERE (rel.from_entity = e.entity_id OR rel.to_entity = e.entity_id) "
    "     AND upper_inf(rel.sys_period)) "
    "FROM organization e WHERE e.publication_review_required"
)

#: Whether the ADR-124 registry exists on this spine — pre-R10 spines
#: (hosted until P34.46's deploy) get a typed refusal, never a crash.
REGISTRY_PRESENT_SQL = "SELECT to_regclass('publication_disposition') IS NOT NULL"

#: Current effective entity dispositions for every flagged org (the SQL
#: twin — access-time rule, latest decided_at ≤ now wins).
_EFFECTIVE_SQL = (
    "SELECT o.entity_id::text, d.disposition, d.disposition_id::text "
    "FROM organization o "
    "JOIN LATERAL ("
    "  SELECT disposition, disposition_id FROM publication_disposition d "
    "  WHERE d.target_kind = 'entity' AND d.target_id = o.entity_id::text "
    "    AND d.decided_at <= clock_timestamp() "
    "  ORDER BY d.decided_at DESC, d.disposition_seq DESC LIMIT 1"
    ") d ON true "
    "WHERE o.publication_review_required"
)

#: One candidate's spine reads (the verb's verification, all SELECTs).
_ORG_ROW_SQL = (
    "SELECT e.entity_type, o.organization_type, o.status, "
    "  o.publication_review_required, "
    "  EXISTS(SELECT 1 FROM person p WHERE p.entity_id = e.entity_id) "
    "FROM entity e LEFT JOIN organization o ON o.entity_id = e.entity_id "
    "WHERE e.entity_id = %s::uuid"
)

_MATCH_ROW_SQL = (
    "SELECT ei.asserted_by_claim::text FROM entity_identifier ei "
    "WHERE ei.entity_id = %s::uuid AND ei.scheme = %s AND ei.value = %s"
)

_PERMITTED_CLAIM_SQL = (
    "SELECT c.claim_id::text FROM claim c "
    "JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
    "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    "JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    "JOIN source_registry sr ON sr.source_id = ea.source_id "
    "WHERE c.claim_id = %s::uuid AND sr.ingestion_permitted LIMIT 1"
)

_EFFECTIVE_ONE_SQL = (
    "SELECT d.disposition, d.disposition_id::text FROM publication_disposition d "
    "WHERE d.target_kind = 'entity' AND d.target_id = %s "
    "  AND d.decided_at <= clock_timestamp() "
    "ORDER BY d.decided_at DESC, d.disposition_seq DESC LIMIT 1"
)

_LABEL_SQL = "SELECT cached_canonical_name FROM organization WHERE entity_id = %s::uuid"

_LITERAL_PARTIES_ONE_SQL = (
    "SELECT DISTINCT c.value_text FROM claim c "
    "WHERE c.object_entity = %s::uuid AND c.value_text IS NOT NULL"
)


def _rows(cur: Any) -> list[Any]:
    return [] if cur is None else list(cur.fetchall())


def _screen_entity(
    conn: _Conn,
    entity_id: str,
    label: str | None,
    extra_names: Sequence[str] = (),
) -> str | None:
    """Run the person-name screen over the label, every literal party value
    on the org's claims, and any caller-supplied name (the list's registry
    name). Returns the flag category or ``None``; screened text is never
    echoed."""
    names: list[str] = [n for n in (label, *extra_names) if n]
    names.extend(str(r[0]) for r in _rows(conn.execute(_LITERAL_PARTIES_ONE_SQL, (entity_id,))))
    for name in names:
        flag = screen_name(name)
        if flag is not None:
            return flag
    return None


# --------------------------------------------------------------------------- #
# record --allow — the verb
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AllowVerdict:
    """One entry's verified verdict — ``record`` only when every check passes."""

    entry: AllowEntry
    verdict: str
    reason: str
    evidence_claim_id: str | None = None
    disposition_id: str | None = None
    supersedes: str | None = None


def verify_entry(conn: _Conn, entry: AllowEntry) -> AllowVerdict:
    """Verify one list entry against the spine (read-only).

    Order matters: person/refusal classes are checked BEFORE the registry
    match so a person-shaped or denied target can never reach the match
    branch (the never-a-person rule and the no-override rule both fail
    closed).
    """
    eid = entry.entity_id
    row = conn.execute(_ORG_ROW_SQL, (eid,)).fetchone()
    if row is None:
        return AllowVerdict(entry, REFUSAL_TARGET_MISSING, "no such entity")
    entity_type, _otype, status, _flagged, is_person = row
    if entity_type == "person" or is_person:
        return AllowVerdict(entry, REFUSAL_PERSON, "person entities are never allowed (ADR-163)")
    if _otype is None:
        return AllowVerdict(entry, REFUSAL_NOT_ORG, f"entity_type is {entity_type!r}")
    if status in ("withdrawn", "suppressed"):
        return AllowVerdict(entry, REFUSAL_STATUS, f"organization.status is {status!r} (ADR-124)")
    eff = conn.execute(_EFFECTIVE_ONE_SQL, (eid,)).fetchone()
    if eff is not None and eff[0] in ("withhold", "restrict", "withdraw"):
        return AllowVerdict(
            entry,
            REFUSAL_DENY,
            f"current effective disposition is {eff[0]!r} — an auto rule "
            "never overrides a recorded decision",
        )
    if eff is not None and eff[0] == "allow":
        return AllowVerdict(entry, VERDICT_ALREADY_ALLOWED, "current effective allow")
    match = conn.execute(_MATCH_ROW_SQL, (eid, entry.scheme, entry.value)).fetchone()
    if match is None:
        return AllowVerdict(
            entry,
            REFUSAL_NO_MATCH,
            f"no {entry.scheme}:{entry.value} identifier on the spine (no tier 0–1 match record)",
        )
    asserted_by = match[0]
    if asserted_by is None:
        return AllowVerdict(
            entry,
            REFUSAL_PROVENANCE,
            "the match record carries no asserting claim (ADR-159 item 6)",
        )
    permitted = conn.execute(_PERMITTED_CLAIM_SQL, (asserted_by,)).fetchone()
    if permitted is None:
        return AllowVerdict(
            entry,
            REFUSAL_PROVENANCE,
            "the asserting claim reaches no ingestion_permitted source",
        )
    label_row = conn.execute(_LABEL_SQL, (eid,)).fetchone()
    label = None if label_row is None else (label_row[0] or None)
    flag = _screen_entity(
        conn, eid, label, extra_names=([entry.registry_name] if entry.registry_name else [])
    )
    if flag is not None:
        return AllowVerdict(
            entry,
            REFUSAL_SCREEN,
            f"person-name screen flagged a screened string ({flag})",
        )
    return AllowVerdict(
        entry,
        VERDICT_RECORD,
        "registry auto-allow verified",
        evidence_claim_id=str(asserted_by),
        supersedes=None if eff is None else str(eff[1]),
    )


def plan_allows(conn: _Conn, entries: Sequence[AllowEntry]) -> list[AllowVerdict]:
    """Verify every entry (deterministic order — the list is pre-sorted)."""
    return [verify_entry(conn, e) for e in entries]


def build_plan(
    lst: DispositionList,
    verdicts: Sequence[AllowVerdict],
    *,
    mode: str,
    authority: str,
    decided_by: str,
) -> dict[str, Any]:
    """The ``sig.disposition-plan/1`` the verb prints — what it would insert
    (dry-run) or did insert (apply), ids + reasons only, never screened text."""
    rows = []
    counts: dict[str, int] = {}
    for v in verdicts:
        rows.append(
            {
                "entity_id": v.entry.entity_id,
                "registry": v.entry.registry,
                "identifier": {"scheme": v.entry.scheme, "value": v.entry.value},
                "match_tier": v.entry.match_tier,
                "verdict": v.verdict,
                "reason": v.reason,
                "evidence_claim_id": v.evidence_claim_id,
                **({"disposition_id": v.disposition_id} if v.disposition_id else {}),
            }
        )
        counts[v.verdict] = counts.get(v.verdict, 0) + 1
    return {
        "record_type": DISPOSITION_PLAN_SCHEMA,
        "list_id": lst.list_id,
        "policy_version": lst.policy_version,
        "mode": mode,
        "authority": authority,
        "decided_by": decided_by,
        "obligation": OBLIGATION_ID,
        "entries": rows,
        "summary": {**counts, "total": len(rows)},
    }


def apply_allows(
    conn: _Conn,
    verdicts: Sequence[AllowVerdict],
    *,
    authority: str,
    decided_by: str,
) -> list[AllowVerdict]:
    """INSERT the ``record``-verdict allows — one transaction, INSERT-only.

    The list is ONE recorded decision batch: either every verified allow
    lands or none does. A refusal is never written. ``decided_at`` is
    omitted so the database stamps it (P32.10a single clock authority).
    """
    from db.dispositions import record_disposition

    out: list[AllowVerdict] = []
    for v in verdicts:
        if v.verdict != VERDICT_RECORD:
            out.append(v)
            continue
        record = new_disposition(
            target_kind=TargetKind.ENTITY,
            target_id=v.entry.entity_id,
            disposition=Disposition.ALLOW,
            reason_category=ALLOW_REASON_CATEGORY,
            authority=authority,
            decided_by=decided_by,
            rationale=(
                f"ADR-159 registry auto-allow: {v.entry.registry} "
                f"{v.entry.scheme}:{v.entry.value} (match tier {v.entry.match_tier}); "
                f"list {OBLIGATION_ID}"
            ),
            evidence_claim_id=v.evidence_claim_id,
            supersedes=v.supersedes,
        )
        did = record_disposition(conn, record)
        out.append(
            AllowVerdict(
                v.entry,
                VERDICT_RECORD,
                v.reason,
                evidence_claim_id=v.evidence_claim_id,
                disposition_id=did,
                supersedes=v.supersedes,
            )
        )
    return out


# --------------------------------------------------------------------------- #
# The flagged-organisation census (sig.org-census/1)
# --------------------------------------------------------------------------- #

CENSUS_COLUMNS = (
    "entity_id",
    "organization_type",
    "status",
    "degree",
    "materialized_degree",
    "edge_share",
    "identifiers",
    "label_identifier_count",
    "registry_match",
    "person_name_screen",
    "screened_literal_party_count",
    "current_disposition",
    "adr159_outcome",
    "obligation",
)


@dataclass
class CensusRow:
    entity_id: str
    organization_type: str
    status: str
    degree: int  # K2 measure — distinct claim subjects referencing the org
    materialized_degree: int  # live relationship/entity_role/org_relation edges
    edge_share: float  # degree / flagged-org (subject, org) pairs
    #: External identifier scheme:value pairs held — label-bearing schemes
    #: are counted, never listed (the withheld name stays out of artifacts).
    identifiers: list[tuple[str, str]] = field(default_factory=list)
    #: How many label-scheme identifiers the org holds (a count, not values).
    label_identifier_count: int = 0
    registry_match: tuple[str, str, str] | None = None  # (registry, scheme, value)
    match_claim_id: str | None = None
    person_name_screen: str = SCREEN_PASS
    screened_literal_party_count: int = 0
    current_disposition: str = "none"
    adr159_outcome: str = OUTCOME_NOT_REVIEWED


@dataclass
class CensusResult:
    rows: list[CensusRow]
    flagged_total: int
    edge_denominator: int
    counts: dict[str, int]
    registry_match_counts: dict[str, int]
    top50_edge_share: float
    person_screen_flagged: int
    #: Whether publication_disposition exists on this spine (false on the
    #: pre-R10 hosted head — allows land with P34.46's deploy).
    disposition_registry_present: bool = True


def _registry_of(scheme: str) -> str | None:
    for reg, meta in REGISTRIES.items():
        if meta["scheme"] == scheme:
            return reg
    return None


def run_census(conn: _Conn) -> CensusResult:
    """The read-only census over the flagged-organisation set.

    Every query is a SELECT — run under ``default_transaction_read_only``
    on the live leg so the leg carries zero writes by construction. Screened
    labels/party values are consumed by :func:`screen_name` in memory only;
    nothing a screen read is returned in the result.
    """
    flagged = _rows(conn.execute(_FLAGGED_SQL))
    labels = {
        str(r[0]): (r[1] or None)
        for r in _rows(
            conn.execute(
                "SELECT o.entity_id::text, o.cached_canonical_name "
                "FROM organization o WHERE o.publication_review_required"
            )
        )
    }
    # The disposition registry lands on hosted only with P34.46's schema
    # deploy; on a pre-R10 spine (or a clone of one) the honest state is
    # "no dispositions recorded" — probe the table before selecting it.
    registry_row = conn.execute(REGISTRY_PRESENT_SQL).fetchone()
    registry_present = bool(registry_row and registry_row[0])
    identifiers: dict[str, list[tuple[str, str, str | None]]] = {}
    for eid, scheme, value, asserted in _rows(conn.execute(_IDENTIFIERS_SQL)):
        identifiers.setdefault(eid, []).append((scheme, value, asserted))
    permitted: dict[tuple[str, str, str], str] = {}
    for eid, scheme, value, claim_id in _rows(conn.execute(_PERMITTED_IDS_SQL)):
        permitted[(eid, scheme, value)] = str(claim_id)
    degree = {str(r[0]): int(r[1]) for r in _rows(conn.execute(_DEGREE_SQL))}
    denominator_row = conn.execute(_EDGE_DENOMINATOR_SQL).fetchone()
    denominator = int(denominator_row[0]) if denominator_row else 0
    mat_degree = {str(r[0]): int(r[1]) for r in _rows(conn.execute(_MATERIALIZED_DEGREE_SQL))}
    literal: dict[str, list[str]] = {}
    for eid, value_text in _rows(conn.execute(_LITERAL_PARTIES_SQL)):
        literal.setdefault(eid, []).append(str(value_text))
    effective = (
        {str(r[0]): (str(r[1]), str(r[2])) for r in _rows(conn.execute(_EFFECTIVE_SQL))}
        if registry_present
        else {}
    )

    rows: list[CensusRow] = []
    counts: dict[str, int] = {}
    registry_counts: dict[str, int] = {}
    screen_flagged = 0
    for eid, otype, status in flagged:
        row = CensusRow(
            entity_id=eid,
            organization_type=str(otype),
            status=str(status),
            degree=degree.get(eid, 0),
            materialized_degree=mat_degree.get(eid, 0),
            edge_share=(degree.get(eid, 0) / denominator) if denominator else 0.0,
        )
        row.identifiers = [
            (s, v) for s, v, _a in identifiers.get(eid, []) if not _is_label_scheme(s)
        ]
        row.label_identifier_count = sum(
            1 for s, _v, _a in identifiers.get(eid, []) if _is_label_scheme(s)
        )
        # Registry match: the first registry-scheme identifier whose asserting
        # claim reaches an ingestion_permitted source (tier 0 — a spine-
        # asserted exact identifier IS the match record, ADR-159 (a)).
        for reg, meta in REGISTRIES.items():
            for scheme, value, _asserted in identifiers.get(eid, []):
                if scheme != meta["scheme"]:
                    continue
                claim_id = permitted.get((eid, scheme, value))
                if claim_id is not None:
                    row.registry_match = (reg, scheme, value)
                    row.match_claim_id = claim_id
                    break
            if row.registry_match is not None:
                break
        if row.registry_match is not None:
            registry_counts[row.registry_match[0]] = (
                registry_counts.get(row.registry_match[0], 0) + 1
            )
        # The person-name screen — always runs (ADR-159 (d)); the screened
        # strings stay in memory, only the count + result are recorded.
        names = [n for n in (labels.get(eid), *literal.get(eid, [])) if n]
        row.screened_literal_party_count = len(literal.get(eid, []))
        for name in names:
            flag = screen_name(name)
            if flag is not None:
                row.person_name_screen = flag
                break
        if row.person_name_screen != SCREEN_PASS:
            screen_flagged += 1
        eff = effective.get(eid)
        row.current_disposition = "none" if eff is None else eff[0]
        # ADR-159 outcome — typed, never an implicit allow.
        if row.current_disposition == "allow":
            row.adr159_outcome = OUTCOME_ALREADY_ALLOWED
        elif row.current_disposition in ("withhold", "restrict", "withdraw"):
            row.adr159_outcome = OUTCOME_RECORDED_DENY
        elif (
            row.status not in ("withdrawn", "suppressed")
            and row.registry_match is not None
            and row.person_name_screen == SCREEN_PASS
        ):
            row.adr159_outcome = OUTCOME_AUTO_ALLOW
        else:
            row.adr159_outcome = OUTCOME_NOT_REVIEWED
        counts[row.adr159_outcome] = counts.get(row.adr159_outcome, 0) + 1
        rows.append(row)

    top50 = sum(sorted((r.degree for r in rows), reverse=True)[:50])
    return CensusResult(
        rows=rows,
        flagged_total=len(flagged),
        edge_denominator=denominator,
        counts=counts,
        registry_match_counts=registry_counts,
        top50_edge_share=(top50 / denominator) if denominator else 0.0,
        person_screen_flagged=screen_flagged,
        disposition_registry_present=registry_present,
    )


def census_record(
    result: CensusResult,
    *,
    spine_name: str,
    generated_at: str,
) -> dict[str, Any]:
    """The ``sig.org-census/1`` record payload (counts + method — no labels)."""
    return {
        "record_type": CENSUS_SCHEMA,
        "generated_at": generated_at,
        "spine": spine_name,
        "policy_version": POLICY_VERSION,
        "rule": "ADR-159 registry auto-allow (G2-ADR124 + D-K2-1 [A-10])",
        "obligation": OBLIGATION_ID,
        "flagged_total": result.flagged_total,
        "disposition_registry_present": result.disposition_registry_present,
        "edge_denominator": result.edge_denominator,
        "outcome_counts": result.counts,
        "registry_match_counts": result.registry_match_counts,
        "person_screen_flagged": result.person_screen_flagged,
        "top50_edge_share": result.top50_edge_share,
        "definitions": {
            "degree": (
                "distinct claim subjects whose claims reference the org via "
                "object_entity (the K2 organisation-edge measure — NEW-1 "
                "re-measured, never pinned)"
            ),
            "materialized_degree": (
                "live incident edges over relationship + entity_role + "
                "organization_relation (open sys_period where bitemporal)"
            ),
            "edge_share": (
                "degree / the flagged-org graph's distinct (subject, org) "
                "pairs (the denominator this report prints)"
            ),
            "registry_match": (
                "an entity_identifier in an ADR-159 registry scheme whose "
                "asserting claim reaches an ingestion_permitted source "
                "(tier-0 match record)"
            ),
            "person_name_screen": (
                "policy.intake.screen_part_viii + the partner_identity "
                "never-a-person rule over cached_canonical_name + literal "
                "party claim values — result only, screened text never "
                "recorded"
            ),
            "adr159_outcome": (
                f"{OUTCOME_AUTO_ALLOW} | {OUTCOME_ALREADY_ALLOWED} | "
                f"{OUTCOME_RECORDED_DENY} | {OUTCOME_NOT_REVIEWED}"
            ),
            "identifiers": (
                "external entity_identifier scheme:value pairs held; "
                "label-bearing schemes (*.name, sig.curator.handle, …) are "
                "counted in label_identifier_count, never listed"
            ),
        },
    }


def _census_csv(result: CensusResult) -> str:
    import io

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CENSUS_COLUMNS)
    for r in result.rows:
        w.writerow(
            [
                r.entity_id,
                r.organization_type,
                r.status,
                r.degree,
                r.materialized_degree,
                f"{r.edge_share:.6f}",
                ";".join(f"{s}:{v}" for s, v in r.identifiers),
                r.label_identifier_count,
                (
                    f"{r.registry_match[0]}:{r.registry_match[1]}:{r.registry_match[2]}"
                    if r.registry_match
                    else ""
                ),
                r.person_name_screen,
                r.screened_literal_party_count,
                r.current_disposition,
                r.adr159_outcome,
                OBLIGATION_ID,
            ]
        )
    return buf.getvalue()


def write_census(
    result: CensusResult,
    out_dir: str | Path,
    *,
    spine_name: str,
    generated_at: str | None = None,
) -> dict[str, Path]:
    """Emit the committed ``sig.org-census/1`` artifacts: CENSUS.md (record
    block + field dictionary + summary), CENSUS.csv (one row per flagged
    org — ids only), census.json (the machine record) and allow-list.json
    (the ``sig.disposition-list/1`` input covering the eligible rows)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = census_record(result, spine_name=spine_name, generated_at=stamp)

    csv_path = out / "CENSUS.csv"
    csv_path.write_text(_census_csv(result), encoding="utf-8")

    json_path = out / "census.json"
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    allow_entries = [
        {
            "entity_id": r.entity_id,
            "registry": r.registry_match[0],
            "identifier": {"scheme": r.registry_match[1], "value": r.registry_match[2]},
            "match_tier": 0,
        }
        for r in result.rows
        if r.adr159_outcome == OUTCOME_AUTO_ALLOW and r.registry_match is not None
    ]
    allow_list = {
        "record_type": DISPOSITION_LIST_SCHEMA,
        "list_id": f"{OBLIGATION_ID}-census-{stamp}",
        "policy_version": POLICY_VERSION,
        "generated_at": stamp,
        "note": (
            "ADR-159 auto-allow candidates from the committed census "
            f"({spine_name}); P34.46 applies them under its in-ticket go "
            "with the Round-10 schema — never applied by P34.26"
        ),
        "entries": allow_entries,
    }
    allow_path = out / "allow-list.json"
    allow_path.write_text(json.dumps(allow_list, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = [
        "# ADR-124 flagged-organisation census (sig.org-census/1)",
        "",
        'P34.26 / ADR-159 (G2-ADR124 + D-K2-1 [A-10], "auto-allow + absence',
        'only"): every `publication_review_required` organisation on the read',
        f"spine (`{spine_name}`), read-only. Screened labels and literal party",
        "values are **never** in this report — ids + scheme:value pairs only",
        "(K2 §3.4; the screen result is a count, not a name). K2 NEW-1's",
        '"969 flagged" and "50 reviews unlock 96.5 %" are re-measured by',
        "this report, never pinned.",
        "",
        "```json",
        json.dumps(record, indent=2, sort_keys=True),
        "```",
        "",
        "## Summary",
        "",
        f"- flagged organisations: **{result.flagged_total}**",
        f"- flagged-org edge denominator (distinct subject,org pairs): "
        f"**{result.edge_denominator}**",
        f"- top-50 degree share: **{result.top50_edge_share:.1%}**",
    ]
    for outcome in (
        OUTCOME_AUTO_ALLOW,
        OUTCOME_ALREADY_ALLOWED,
        OUTCOME_RECORDED_DENY,
        OUTCOME_NOT_REVIEWED,
    ):
        md.append(f"- `{outcome}`: **{result.counts.get(outcome, 0)}**")
    md.append(
        f"- person-name screen flags: **{result.person_screen_flagged}** "
        "(labels/values screened, never recorded)"
    )
    md.append("")
    md.append("## Registry matches (permitted-source asserted)")
    md.append("")
    for reg in sorted(REGISTRIES):
        md.append(
            f"- {reg} (`{REGISTRIES[reg]['scheme']}`): "
            f"**{result.registry_match_counts.get(reg, 0)}**"
        )
    md += [
        "",
        "## Columns (CENSUS.csv)",
        "",
        "| column | meaning |",
        "|---|---|",
        "| entity_id | the flagged organisation's id |",
        "| organization_type | its §11.2 namespaced type |",
        "| status | active/inactive/withdrawn/suppressed |",
        "| degree | distinct claim subjects referencing the org via "
        "`claim.object_entity` (K2's organisation-edge measure) |",
        "| materialized_degree | live incident edges over `relationship` + "
        "`entity_role` + `organization_relation` |",
        "| edge_share | degree / the report's distinct-pair denominator |",
        "| identifiers | external `entity_identifier` `scheme:value` pairs "
        "held — label-bearing schemes (`*.name`, `sig.curator.handle`, …) "
        "are never written; their count is the next column |",
        "| label_identifier_count | how many label-scheme identifiers the "
        "org holds (the withheld name's count — the name itself is never "
        "in this report) |",
        "| registry_match | `registry:scheme:value` whose asserting claim "
        "reaches an `ingestion_permitted` source, else empty |",
        "| person_name_screen | `pass` | `flag_part_viii` | "
        "`flag_person_name` — never the screened string |",
        "| screened_literal_party_count | how many literal party values "
        "the screen ran over (a count, not the values) |",
        "| current_disposition | the effective entity disposition "
        "(`none`/`allow`/`withhold`/`restrict`/`withdraw`) |",
        "| adr159_outcome | the typed ADR-159 state — `auto_allow_eligible` "
        "(the verb would record an allow), `already allowed`, `recorded "
        "deny`, or `not yet reviewed` — never absent, never an implicit "
        "allow |",
        f"| obligation | `{OBLIGATION_ID}` — the owed ADR-124 allow row |",
        "",
        "## Files",
        "",
        "- `CENSUS.csv` — one row per flagged organisation (the columns above)",
        "- `census.json` — the `sig.org-census/1` machine record",
        "- `allow-list.json` — the `sig.disposition-list/1` over the "
        "`auto_allow_eligible` rows; **P34.46 applies it under its "
        "in-ticket go with the Round-10 schema** — P34.26 applies nothing",
        "",
    ]
    md_path = out / "CENSUS.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    return {
        "CENSUS.md": md_path,
        "CENSUS.csv": csv_path,
        "census.json": json_path,
        "allow-list.json": allow_path,
    }
