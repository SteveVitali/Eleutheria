# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.43 (K7 WX-01 / F-481 / SIG-WATCH-D01…D04) — the watch producer v1.

The §39.5 watch surface previously read the ``contract_watch`` raw key — a key
no query ever filled, so dated procurement, agenda, legislative and grant
records already on the spine never reached the watch (F-481). This module is the
producer: two ``EXPORT_QUERIES`` reads (the publishable claims on the five
watch subject families + a read-only sizing count) feed one pure-Python
derivation implementing the six K7 §5.2 rules verbatim — ``renewal_deadline``,
``contract_expiry``, ``solicitation_deadline``, ``agenda_item``,
``legislative_action`` and ``grant_period_end`` — emitting the ``sig/watch/2``
envelope with ``sig.watch-item/1`` items (the §5.1 field set) and a coverage
block. An empty result always arrives *with* its coverage statement (the
honest-empty rule).

Honesty rules this module encodes (K7 §5.2/§5.3/§6 + the ticket's invariants):

* an item exists only where its publishable claims exist — the query is gated
  by ``{PUB_CLAIM_GATE}`` + effective rights, exactly like every other claim
  read; a kind whose firing predicates do not yet exist on the spine yields no
  items, never a synthetic (WX-02 predicates — ``meeting_date``,
  ``auto_renews``, ``notice_window_days``, ``renewal_term_months`` — are in the
  read list so they are picked up the day they land; today they contribute
  zero rows);
* an ``upper_bound`` date is never labelled a deadline — ``contract_expiry``
  carries ``date_certainty: "upper_bound"`` and its own title wording ("latest
  possible end"), and links the ``contract_expiring`` research task where the
  detector has opened one (K11; WX-06 owns the detector run);
* ``technology``/``vendor`` come only from the reviewed vocabulary matches the
  claims declare (``content_term``/``matched_keyword``/``bill_matched_keyword``
  values resolved through ``agenda_content_vocab.toml``) — never inferred;
* place follows the K7 §5.3 order — resolved jurisdiction claims → the
  agenda/portal tenant's registered jurisdiction → buyer office /
  ``place_of_performance`` → ``unplaced`` — via the P35.19 placement engine;
  a NUTS code is never an ISO-3166-2 identifier and no place is guessed;
* every free-text field that draws on claim literals passes the P35.31 S-2 +
  S-5 + S-7 scrub (``policy.transparency.scrub_text``); every upstream link
  passes the J3 §5.3 lane rule (``statements.upstream_block`` — the same S-6
  publication form the statements stream emits);
* ``what_you_can_do`` is procedural template text (agent-drafted, pending
  operator sign-off — D-K7-4/D-K7-5 ride the window/feed decisions); it tells
  a *reader* what they could do and is never outreach by SIG (W-P5: SIG sends
  no e-mail);
* the list windows are the design's *declared inference*, recorded in the
  emitted ``windows`` block pending D-K7-4: items list from ``first_seen``
  until 30 days after their date (then the per-place history owns them), the
  default list is the next 90 days, and ``renewal_deadline``/
  ``contract_expiry`` surface from 12 months ahead.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from typing import Any

from policy.labels import entity_hash, name_slug
from policy.transparency import scrub_text

from policy import withdrawals as policy_withdrawals

from . import placement as _placement
from . import statements as _stmt
from .analytics import _next_decision_date
from .jurisdictions import CONNECTOR_DATA_DIR, jurisdiction_slug

#: The emitted artifact + item schema ids.
SCHEMA_WATCH = "sig/watch/2"
SCHEMA_WATCH_ITEM = "sig.watch-item/1"

#: The derivation ruleset id — bump on a rule change (K7 §5.2 + D-K7-4 windows).
WATCH_RULESET = "watch-derivation/1"

#: The six §5.2 kinds v1 derives.
WATCH_KINDS: tuple[str, ...] = (
    "renewal_deadline",
    "contract_expiry",
    "solicitation_deadline",
    "agenda_item",
    "legislative_action",
    "grant_period_end",
)

#: Subject-key families the watch reads (the ``sig.connector.subject`` prefix —
#: ``procurement_notice`` subjects type as ``contract`` in the entity map, so the
#: FAMILY prefix, never the entity type, is the discriminator).
_WATCH_FAMILIES: tuple[str, ...] = (
    "contract",
    "procurement_notice",
    "agenda_item",
    "legislative_bill",
    "funding_instrument",
)

#: The bounded predicate set the producer reads — the §5.2 firing predicates,
#: the context fields the §5.1 surface needs (title/body/subjects/timeline), and
#: the WX-02 dated-decision predicates (``auto_renews``, ``notice_window_days``,
#: ``renewal_term_months``, ``meeting_date``, ``bill_hearing_date``) whose absence
#: on a pre-WX-02 spine is honest zero, not a gap to fill.
_WATCH_PREDICATES: tuple[str, ...] = (
    # subject-family record markers
    "contract",
    "procurement_notice",
    "agenda_item",
    "legislative_bill",
    "funding_instrument",
    # contract fields (§11.11)
    "title",
    "buyer",
    "seller",
    "amount",
    "currency",
    "signed_date",
    "start_date",
    "end_date",
    "renewal_options",
    "document",
    "acquisition_channel",
    "lifecycle_transition",
    "place_of_performance",
    # WX-02 dated-decision predicates (not yet on the spine — zero rows today)
    "auto_renews",
    "notice_window_days",
    "renewal_term_months",
    "meeting_date",
    "bill_hearing_date",
    "bill_action_date",
    # procurement notice fields
    "notice_type",
    "posted_date",
    "response_deadline",
    # bill fields (P26.11)
    "bill_external_id",
    "bill_identifier",
    "bill_title",
    "bill_session",
    "bill_jurisdiction",
    "bill_status",
    "bill_status_date",
    # funding instrument fields (§11.12)
    "period",
    "funder",
    "recipient",
    "program_name",
    "federal_award_id",
    "description",
    # the reviewed surveillance matches (agenda_content_vocab term ids)
    "content_term",
    "matched_keyword",
    "bill_matched_keyword",
    # jurisdiction declarations (claim-side placement inputs)
    "jurisdiction",
)

#: Positional columns of the ``watch_claims`` rows (mirrors the SELECT).
WATCH_CLAIMS_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "subject_id",
    "subject_key",
    "entity_type",
    "predicate_id",
    "value_text",
    "value_num",
    "value_bool",
    "value_json",
    "raw_value",
    "observed_at",
    "recorded_at",
    "revises_claim",
    "retraction_of",
    "review_status",
    "source_id",
    "spdx_expression",
)

#: Positional columns of the ``watch_subject_counts`` sizing read.
WATCH_COUNT_COLUMNS: tuple[str, ...] = ("family", "subjects", "claims")

_WATCH_PREDICATE_SQL = (
    " AND c.predicate_id IN (" + ",".join(f"'{p}'" for p in _WATCH_PREDICATES) + ")"
)

#: The EXPORT_QUERIES entries the producer reads. Both run inside the export's
#: same ``REPEATABLE READ READ ONLY`` snapshot, guarded by ``entity_identifier``
#: (the subject-key surface the claims group on — a pre-P35.24 spine degrades to
#: honest absence). ``{PUB_CLAIM_GATE}`` + effective-rights apply exactly like
#: ``claim_weights``; ``upper_inf(c.sys_period)`` is the literal the caller's
#: belief-pinning rewrite targets.
WATCH_QUERIES: dict[str, tuple[str, str]] = {
    # The publishable claims on the five watch subject families (F-481 — the
    # producer the surface never had). One row per claim with the subject key,
    # the typed value columns, the supersession pair (status derivation) and
    # the establishing source (``claim_source`` CTE rides ``{EFFECTIVE}``).
    "watch_claims": (
        "entity_identifier",
        "{EFFECTIVE}SELECT c.claim_id::text, c.subject_id::text, skey.subject_key,"
        "       e.entity_type, c.predicate_id,"
        "       COALESCE(c.value_text, c.raw_value), c.value_num, c.value_bool,"
        "       c.value_json::text, c.raw_value,"
        "       c.observed_at::text, lower(c.sys_period)::text,"
        "       c.revises_claim::text, c.retraction_of::text,"
        "       c.review_status::text, cs.source_id, rr.spdx_expression"
        "  FROM claim c"
        "  JOIN entity e ON e.entity_id = c.subject_id"
        # One canonical subject key per entity — the LATERAL … LIMIT 1 the
        # label_entities read uses (a plain join would multiply claims across
        # an entity's identifier rows).
        "  JOIN LATERAL (SELECT ei.value AS subject_key"
        "                FROM entity_identifier ei"
        "               WHERE ei.entity_id = c.subject_id"
        "                 AND ei.scheme = 'sig.connector.subject'"
        "               ORDER BY ei.value LIMIT 1) skey ON true"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "       ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE skey.subject_key ~ '^(contract|procurement_notice|agenda_item"
        "                          |legislative_bill|funding_instrument):'"
        "   AND c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND rr.redistributable = 'yes'" + _WATCH_PREDICATE_SQL + "   AND {PUB_CLAIM_GATE}"
        " ORDER BY c.subject_id, c.predicate_id, c.observed_at NULLS LAST, c.claim_id",
    ),
    # The read-only sizing count the ticket's catalog row names — the emission's
    # footprint BEFORE it lands: subjects + claim rows per watch family under the
    # IDENTICAL gates the watch_claims read applies (the same publication gate +
    # effective-rights join — so the count the operator reviews is the count the
    # producer actually read, never a population total — SIG-METRIC-010).
    "watch_subject_counts": (
        "entity_identifier",
        "{EFFECTIVE}SELECT split_part(skey.subject_key, ':', 1) AS family,"
        "       count(DISTINCT c.subject_id)::int, count(*)::int"
        "  FROM claim c"
        "  JOIN LATERAL (SELECT ei.value AS subject_key"
        "                FROM entity_identifier ei"
        "               WHERE ei.entity_id = c.subject_id"
        "                 AND ei.scheme = 'sig.connector.subject'"
        "               ORDER BY ei.value LIMIT 1) skey ON true"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "       ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE skey.subject_key ~ '^(contract|procurement_notice|agenda_item"
        "                             |legislative_bill|funding_instrument):'"
        "   AND c.sensitivity_tier = 0"
        "   AND upper_inf(c.sys_period)"
        "   AND rr.redistributable = 'yes'" + _WATCH_PREDICATE_SQL + "   AND {PUB_CLAIM_GATE}"
        " GROUP BY 1 ORDER BY 1",
    ),
}


# --------------------------------------------------------------------------- #
# The declared-inference windows (K7 §5.2 — pending operator decision D-K7-4)
# --------------------------------------------------------------------------- #

#: Items list from ``first_seen`` until this many days AFTER their date (then
#: the per-place history archive — a later surface row — owns them).
_RECENTLY_DECIDED_DAYS = 30
#: ``renewal_deadline``/``contract_expiry`` surface this many days ahead —
#: many councils need two or three meeting cycles (K7 §5.2 windows).
_CONTRACT_HORIZON_DAYS = 365
#: The default rendered list window (the page applies it; recorded here).
_LIST_WINDOW_DAYS = 90

#: The federal publishers whose watch subjects sit under ``iso3166-1:US`` when
#: no finer place resolves (K7 §5.3 — federal items under ``usa`` with the buyer
#: office as the body). A source id outside this set never mints a federal
#: placement by default.
_FEDERAL_SOURCES: frozenset[str] = frozenset({"usaspending", "sam_gov", "gsa", "congress_gov"})

#: Kind → the short word the ``W-<place>-<kind>-<slug>-<hash4>`` handle embeds.
_HANDLE_KIND_WORDS: dict[str, str] = {
    "renewal_deadline": "renewal",
    "contract_expiry": "expiry",
    "solicitation_deadline": "solicitation",
    "agenda_item": "agenda",
    "legislative_action": "bill",
    "grant_period_end": "grant",
}

#: ``date_kind`` — the WHAT-the-date-is label (never a certainty claim).
_DATE_KIND_BY_KIND: dict[str, str] = {
    "renewal_deadline": "notice_deadline",
    "contract_expiry": "expiry",
    "solicitation_deadline": "response_deadline",
    "agenda_item": "meeting",
    "legislative_action": "status_change",
    "grant_period_end": "period_end",
}

#: The bill predicates that (when they land) express a *scheduled* action — the
#: preferred date source; absent, the recent ``bill_status_date`` is the item's
#: date with ``date_kind: status_change`` (the label says what moved, never
#: "deadline").
_BILL_SCHEDULED_PREDICATES: tuple[str, ...] = ("bill_hearing_date", "bill_action_date")

#: Dated predicates rendered on the item's ``timeline`` — other dated facts
#: around the alert date (posted, signed, start, end, prior status).
_TIMELINE_PREDICATES: dict[str, str] = {
    "signed_date": "signed",
    "start_date": "period_start",
    "end_date": "period_end",
    "posted_date": "posted",
    "response_deadline": "response_deadline",
    "meeting_date": "meeting",
    "bill_status_date": "status_change",
    "bill_hearing_date": "scheduled_action",
    "bill_action_date": "scheduled_action",
    "period": "period",
}

#: Agent-drafted procedural templates (§5.1 ``what_you_can_do``) — recorded in
#: the envelope's ``build.what_you_can_do_basis`` as pending operator sign-off.
#: Procedural only: how a reader could see/comment/request the record — never a
#: position, never outreach (W-P4/W-P5, Part VIII).
_WHAT_YOU_CAN_DO: dict[str, str] = {
    "renewal_deadline": (
        "The auto-renewal is decided by {body}: if no action is taken by the "
        "listed date, the contract renews by default. The body's meeting agendas "
        "and minutes are public, and most bodies accept written comment before "
        "the meeting at which the item is heard."
    ),
    "contract_expiry": (
        "The listed date is the contract's stated end — the real renewal terms "
        "are not on record, so the actual decision may come earlier. The "
        "contract's renewal clause can be requested from {body} under the "
        "jurisdiction's public-records law."
    ),
    "solicitation_deadline": (
        "The buyer accepts responses until the listed deadline. The notice "
        "itself carries the submission instructions and any pre-bid or "
        "comment dates."
    ),
    "agenda_item": (
        "The listed body may act on this item at the listed meeting. The "
        "agenda documents and the body's public-comment rules are published by "
        "the body before the meeting."
    ),
    "legislative_action": (
        "The bill's recorded status changed on the listed date. The "
        "legislature's own record links the current text, committee "
        "assignments and any scheduled hearing."
    ),
    "grant_period_end": (
        "The recorded funding period ends on the listed date. The awarding "
        "agency's record carries the reporting and renewal terms."
    ),
}


# --------------------------------------------------------------------------- #
# Normalized claim rows
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Claim:
    """One publishable watch-surface claim, normalized off the SQL tuple."""

    claim_id: str
    subject_id: str
    subject_key: str
    entity_type: str
    predicate: str
    value: str | None
    value_num: float | None
    value_bool: bool | None
    value_json: Any
    raw_value: str | None
    observed_at: str | None
    recorded_at: str | None
    revises_claim: str | None
    retraction_of: str | None
    review_status: str | None
    source_id: str | None


def _dicts(rows: Any, columns: Sequence[str]) -> list[dict[str, Any]]:
    """Positional rows → dicts; Mapping rows re-keyed (the test fixture shape)."""
    out: list[dict[str, Any]] = []
    for r in rows or ():
        if isinstance(r, Mapping):
            out.append({c: r.get(c) for c in columns})
        else:
            out.append(dict(zip(columns, r, strict=False)))
    return out


def _claims(raw: Mapping[str, Any]) -> list[_Claim]:
    out: list[_Claim] = []
    for r in _dicts(raw.get("watch_claims") or [], WATCH_CLAIMS_COLUMNS):
        value_json = r.get("value_json")
        if isinstance(value_json, str) and value_json.strip():
            try:
                value_json = json.loads(value_json)
            except ValueError:
                value_json = None
        out.append(
            _Claim(
                claim_id=str(r.get("claim_id") or ""),
                subject_id=str(r.get("subject_id") or ""),
                subject_key=str(r.get("subject_key") or ""),
                entity_type=str(r.get("entity_type") or ""),
                predicate=str(r.get("predicate_id") or ""),
                value=str(r["value_text"]) if r.get("value_text") is not None else None,
                value_num=float(r["value_num"]) if r.get("value_num") is not None else None,
                value_bool=bool(r["value_bool"]) if r.get("value_bool") is not None else None,
                value_json=value_json,
                raw_value=str(r["raw_value"]) if r.get("raw_value") is not None else None,
                observed_at=_iso(r.get("observed_at")),
                recorded_at=_iso(r.get("recorded_at")),
                revises_claim=str(r["revises_claim"]) if r.get("revises_claim") else None,
                retraction_of=str(r["retraction_of"]) if r.get("retraction_of") else None,
                review_status=str(r["review_status"]) if r.get("review_status") else None,
                source_id=str(r["source_id"]) if r.get("source_id") else None,
            )
        )
    # P34.19/F-337 (SIG-GOV-007): the committed publication withdrawals bind the
    # watch read exactly as they bind the sites slice — a listed claim id or a
    # listed subject entity is suppressed in every public artifact (fail closed
    # both directions; the spine record itself is untouched).
    return [
        c
        for c in out
        if c.subject_key
        and c.predicate
        and policy_withdrawals.withdrawal_for_claim(c.claim_id) is None
        and policy_withdrawals.withdrawal_for_entity(c.subject_id) is None
    ]


def _iso(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _date_of(claim: _Claim | None) -> date | None:
    """The claim's ISO date value — a date only, never a datetime guess."""
    if claim is None or claim.value is None:
        return None
    try:
        return date.fromisoformat(str(claim.value).strip()[:10])
    except ValueError:
        return None


def _period_bounds(claim: _Claim | None) -> tuple[str | None, str | None]:
    """A ``period`` claim's ``{start, end}`` — the §11.12 value_json shape."""
    if claim is None or not isinstance(claim.value_json, Mapping):
        return None, None
    start = str(claim.value_json.get("start") or "").strip() or None
    end = str(claim.value_json.get("end") or "").strip() or None
    return start, end


def _latest(claims: Sequence[_Claim], predicate: str) -> _Claim | None:
    """The newest non-retracted claim for ``predicate`` (recorded order, then id)."""
    cands = [c for c in claims if c.predicate == predicate and not c.retraction_of]
    if not cands:
        return None
    return max(cands, key=lambda c: (c.recorded_at or "", c.claim_id))


def _all(claims: Sequence[_Claim], predicate: str) -> list[_Claim]:
    return [c for c in claims if c.predicate == predicate]


def _text(claim: _Claim | None) -> str | None:
    if claim is None or claim.value is None:
        return None
    text = str(claim.value).strip()
    return text or None


# --------------------------------------------------------------------------- #
# Reviewed-term classification (agenda_content_vocab — the term ids the
# content_term / matched_keyword / bill_matched_keyword claim values name)
# --------------------------------------------------------------------------- #


@cache
def _vocab_terms() -> dict[str, dict[str, str]]:
    """term_id → {kind, label} from the reviewed agenda-content vocabulary."""
    try:
        data = tomllib.loads(
            (CONNECTOR_DATA_DIR / "agenda_content_vocab.toml").read_text(encoding="utf-8")
        )
    except OSError:
        return {}
    out: dict[str, dict[str, str]] = {}
    for term in data.get("terms") or ():
        tid = str(term.get("id") or "").strip()
        if tid:
            out[tid] = {
                "kind": str(term.get("kind") or ""),
                "label": str(term.get("label") or tid),
            }
    return out


@cache
def _tenant_jurisdictions() -> dict[str, str]:
    """tenant_id → registered jurisdiction name (K7 §5.3 step 2), from the two
    tenant registries — agenda_tenants.toml (agenda_item/contract keys) and
    procurement_portal_tenants.toml (procurement_notice keys). Both are
    committed, versioned registry data (§20); a missing row is honest absence.
    """
    out: dict[str, str] = {}
    for fname in ("agenda_tenants.toml", "procurement_portal_tenants.toml"):
        try:
            data = tomllib.loads((CONNECTOR_DATA_DIR / fname).read_text(encoding="utf-8"))
        except OSError:
            continue
        for tenant_id, row in (data.get("tenants") or {}).items():
            juris = str(row.get("jurisdiction") or "").strip()
            if juris:
                out[str(tenant_id)] = juris
    return out


# --------------------------------------------------------------------------- #
# Placement inputs (K7 §5.3 — resolved jurisdiction → tenant → buyer/PoP →
# federal floor → unplaced; nothing is guessed)
# --------------------------------------------------------------------------- #


def _family(subject_key: str) -> str:
    return subject_key.split(":", 1)[0]


def _subject_segments(subject_key: str) -> list[str]:
    return subject_key.split(":")


def _tenant_for(subject_key: str) -> str | None:
    """The registered tenant id the subject key scopes to, if any.

    ``agenda_item:<platform>:<tenant>:<ext>`` and the tenant-scoped procurement
    notice carry the tenant positionally; ``contract:<source>:tenant:<t>:<id>``
    carries it under the declared ``tenant`` scheme segment (sig.subject-key-pins).
    """
    segs = _subject_segments(subject_key)
    if len(segs) >= 4 and segs[0] == "agenda_item":
        return segs[2]
    if len(segs) >= 4 and segs[0] == "procurement_notice":
        return segs[2]
    if len(segs) >= 5 and segs[0] == "contract" and segs[2] == "tenant":
        return segs[3]
    return None


def _candidate_pair(claim: _Claim) -> tuple[str, str] | None:
    """The connector's declared ``{scheme, value}`` — persisted in value_json
    (SIG-INGEST-034 / P35.18). No pair, never a guess."""
    blob = claim.value_json
    if not isinstance(blob, Mapping):
        return None
    scheme, value = blob.get("scheme"), blob.get("value")
    if isinstance(scheme, str) and scheme.strip() and isinstance(value, str) and value.strip():
        return scheme.strip(), value.strip()
    return None


def _placement_input(
    subject_key: str, claims: Sequence[_Claim], handle: str
) -> _placement.PlacementInput:
    """The K7 §5.3 order for one draft item: resolved jurisdiction → tenant →
    buyer office / place_of_performance → unplaced (federal floor first)."""
    declared: tuple[str, str] | None = None
    name: str | None = None

    # 1. the claim's resolved jurisdiction — jurisdiction/place/bill predicates
    for pred in ("jurisdiction", "place_of_performance", "bill_jurisdiction"):
        for c in _all(claims, pred):
            pair = _candidate_pair(c)
            if pair is not None:
                declared = pair
                break
            if name is None:
                name = _text(c)
        if declared is not None:
            break

    # 2. the agenda/portal tenant's registered jurisdiction (registry data —
    #    a tenant absent from the registry keeps searching honestly).
    if name is None and declared is None:
        tenant = _tenant_for(subject_key)
        if tenant:
            name = _tenant_jurisdictions().get(tenant)

    # 3. the buyer office's name (K4 key via the engine's name lookup — never a
    #    bare-code guess; ambiguous → the engine records name_ambiguous).
    if name is None and declared is None:
        name = _text(_latest(claims, "buyer")) or _text(_latest(claims, "funder"))

    # 4. the federal floor — a federal publisher's subject sits under
    #    iso3166-1:US unless a finer declaration already resolved (K7 §5.3).
    sources = {c.source_id for c in claims if c.source_id}
    if declared is None and name is None and sources & _FEDERAL_SOURCES:
        declared = ("iso.3166_1_alpha2", "US")

    return _placement.PlacementInput(
        record_id=handle,
        source_id=sorted(sources)[0] if sources else None,
        declared=declared,
        name=name,
    )


# --------------------------------------------------------------------------- #
# The derivation
# --------------------------------------------------------------------------- #


def _bool_of(claim: _Claim | None) -> bool | None:
    """A typed boolean — ``value_bool`` first, then a literal text value (a
    pre-WX-02 spine may carry the flag either way; anything else is absent)."""
    if claim is None:
        return None
    if claim.value_bool is not None:
        return claim.value_bool
    if claim.value is not None:
        lowered = claim.value.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
    return None


def _status(
    date_value: date,
    as_of: date,
    firing_claim: _Claim,
    *,
    superseded: frozenset[str],
    retracted: frozenset[str],
) -> str:
    """The §5.1 status word. A claim is superseded/retracted when ANOTHER claim's
    ``revises_claim``/``retraction_of`` names it — never by its own outbound
    correction edge (that marks the *correcting* row, which is current)."""
    if firing_claim.claim_id in retracted:
        return "withdrawn"
    if firing_claim.claim_id in superseded:
        return "superseded"
    if date_value == as_of:
        return "today"
    if date_value < as_of:
        return "recently_decided"
    return "upcoming"


def _listed(kind: str, date_value: date, as_of: date) -> bool:
    """The §5.2 windows: listed until 30 days past; contract kinds surface only
    within the 12-month horizon."""
    if date_value < as_of - timedelta(days=_RECENTLY_DECIDED_DAYS):
        return False
    if kind in ("renewal_deadline", "contract_expiry"):
        return date_value <= as_of + timedelta(days=_CONTRACT_HORIZON_DAYS)
    return True


def _first_seen(claims: Sequence[_Claim]) -> str | None:
    stamps = [
        str(c.recorded_at or c.observed_at or "")[:10]
        for c in claims
        if (c.recorded_at or c.observed_at)
    ]
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else None


def _source_ids(claims: Sequence[_Claim]) -> list[str]:
    return sorted({str(c.source_id) for c in claims if c.source_id})


def _matched_terms(claims: Sequence[_Claim]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(technology, vendor) from the reviewed-vocab match claims — declared ids
    only, classified by the committed vocabulary; an unknown id is still named,
    honestly labelled by the vocab's own missing kind."""
    tech: dict[str, str] = {}
    vendor: dict[str, str] = {}
    for c in claims:
        if c.predicate not in ("content_term", "matched_keyword", "bill_matched_keyword"):
            continue
        tid = str(c.value or "").strip()
        if not tid:
            continue
        entry = _vocab_terms().get(tid)
        if entry is not None and entry["kind"] == "vendor":
            vendor[tid] = entry["label"]
        else:
            # technology / instrument / program — and unknown ids keep their
            # own label text so a vocabulary gap is visible, never dropped.
            tech[tid] = (entry or {}).get("label") or tid
    return (
        [{"id": k, "label": v} for k, v in sorted(tech.items())],
        [{"id": k, "label": v} for k, v in sorted(vendor.items())],
    )


def _external_id(subject_key: str) -> str:
    segs = _subject_segments(subject_key)
    return segs[-1] if len(segs) > 1 else subject_key


def _handle(place_key: str | None, kind: str, subject_key: str) -> str:
    place = jurisdiction_slug(place_key) if place_key else "unplaced"
    slug = name_slug(_external_id(subject_key)) or "item"
    digest = entity_hash(subject_key + "|" + kind, length=4)
    return f"W-{place}-{_HANDLE_KIND_WORDS[kind]}-{slug}-{digest}"


def _timeline(claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Other dated facts on the subject — posted, signed, period bounds, prior
    status — each dated and attributed to its claim, sorted deterministically."""
    out: list[dict[str, Any]] = []
    for c in claims:
        label = _TIMELINE_PREDICATES.get(c.predicate)
        if label is None:
            continue
        if c.predicate == "period":
            start, end = _period_bounds(c)
            for tag, d in (("period_start", start), ("period_end", end)):
                if d:
                    out.append({"kind": tag, "date": d, "claim_id": c.claim_id})
            continue
        if c.predicate == "lifecycle_transition" and isinstance(c.value_json, Mapping):
            trans_date = str(c.value_json.get("date") or "").strip()[:10]
            state = str(c.value_json.get("state") or "").strip()
            if trans_date and state:
                out.append(
                    {"kind": f"lifecycle:{state}", "date": trans_date, "claim_id": c.claim_id}
                )
            continue
        fact_date = _date_of(c)
        if fact_date is not None:
            out.append({"kind": label, "date": fact_date.isoformat(), "claim_id": c.claim_id})
    out.sort(key=lambda t: (t["date"], t["kind"], t["claim_id"]))
    return out


def _evidence_links(
    claims: Sequence[_Claim],
    binding_by_claim: Mapping[str, Sequence[Mapping[str, Any]]],
    artifact_url_by_id: Mapping[str, str],
    lane_by_source: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Per item: its claims + the claim→capture→artifact binding each rides
    (P32.2/P34.21b) and the S-6-gated upstream document link (J3 §5.3 lane
    rule — the same ``statements.upstream_block`` the statements stream emits).
    """
    out: list[dict[str, Any]] = []
    for c in sorted(claims, key=lambda c: (c.predicate, c.claim_id)):
        bindings = binding_by_claim.get(c.claim_id) or []
        entry: dict[str, Any] = {
            "claim_id": c.claim_id,
            "predicate": c.predicate,
            "source_id": c.source_id,
            "artifact_ids": sorted(
                {str(b["artifact_id"]) for b in bindings if b.get("artifact_id")}
            ),
            "upstream": _stmt.upstream_block(None, lane="unknown", gate_passed=False),
        }
        # One upstream link per item claim: the first binding's artifact URL,
        # scrubbed under THAT artifact's source lane (a binding without a URL
        # leaves the honest none-status block).
        for b in bindings:
            # ONLY the evidence_artifacts read's ``upstream_url`` — already
            # effective-rights gated (redistributable='yes' only) — may leave
            # this file. The binding detail's raw ``ea.url`` is deliberately
            # not a fallback: an artifact whose rights withhold the link stays
            # withheld here (fail-closed, never a second URL path).
            url = artifact_url_by_id.get(str(b.get("artifact_id") or ""))
            if not url:
                continue
            lane_entry = lane_by_source.get(str(b.get("artifact_source_id") or c.source_id)) or {}
            decision = lane_entry.get("decision")
            entry["upstream"] = _stmt.upstream_block(
                url,
                lane=str(getattr(decision, "lane", "unknown") or "unknown"),
                gate_passed=True,
                part_viii_class=lane_entry.get("p8"),
            )
            break
        out.append(entry)
    return out


# --- the six §5.2 rules ------------------------------------------------------ #


def _derive_contracts(subject_key: str, claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Rules 1+2 — ``renewal_deadline`` (auto-renewing contract with a notice
    window; the date is ``_next_decision_date`` — analytics' one derivation,
    never a second formula) and ``contract_expiry`` (end_date with renewal
    terms unknown → ``upper_bound``; an explicit non-renewal → ``stated``)."""
    end = _latest(claims, "end_date")
    end_date = _date_of(end)
    if end is None or end_date is None:
        return []
    auto = _latest(claims, "auto_renews")
    window = _latest(claims, "notice_window_days")
    termination = {
        "expiry_date": end_date.isoformat(),
        "auto_renews": _bool_of(auto),
        "notice_window_days": (
            _int(window.value_num if window.value_num is not None else window.value)
            if window is not None
            else None
        ),
    }
    if termination["auto_renews"] and termination["notice_window_days"] is not None:
        decision = _next_decision_date(termination)
        if decision is None:
            return []
        kind, certainty, item_date = "renewal_deadline", "derived", decision
    else:
        kind = "contract_expiry"
        # auto_renews explicitly false is a recorded renewal term → the end is
        # stated; absent/partial terms leave the upper bound honest.
        certainty = "stated" if termination["auto_renews"] is False else "upper_bound"
        item_date = end_date.isoformat()
    return [
        {
            "kind": kind,
            "date": item_date,
            "date_certainty": certainty,
            "firing_claims": {end.claim_id} | {c.claim_id for c in (auto, window) if c is not None},
            "termination": termination,
        }
    ]


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _derive_notice(subject_key: str, claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Rule 3 — ``solicitation_deadline``: response_deadline + a reviewed match."""
    deadline = _latest(claims, "response_deadline")
    d = _date_of(deadline)
    matched = _all(claims, "matched_keyword") + _all(claims, "content_term")
    if deadline is None or d is None or not matched:
        return []
    return [
        {
            "kind": "solicitation_deadline",
            "date": d.isoformat(),
            "date_certainty": "stated",
            "firing_claims": {deadline.claim_id} | {c.claim_id for c in matched},
        }
    ]


def _derive_agenda(subject_key: str, claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Rule 4 — ``agenda_item``: reviewed agenda-vocab ``content_term`` +
    ``meeting_date`` (a WX-02 predicate — absent on today's spine → no item)."""
    meeting = _latest(claims, "meeting_date")
    d = _date_of(meeting)
    terms = _all(claims, "content_term")
    if meeting is None or d is None or not terms:
        return []
    return [
        {
            "kind": "agenda_item",
            "date": d.isoformat(),
            "date_certainty": "stated",
            "firing_claims": {meeting.claim_id} | {c.claim_id for c in terms},
        }
    ]


def _derive_bill(subject_key: str, claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Rule 5 — ``legislative_action``: a surveillance-matched bill with a
    scheduled action/hearing date preferred, else its recent status date (the
    ``status_change`` date kind — the label names what moved)."""
    matched = _all(claims, "bill_matched_keyword")
    if not matched:
        return []
    firing = None
    date_kind = _DATE_KIND_BY_KIND["legislative_action"]
    for pred in _BILL_SCHEDULED_PREDICATES:
        firing = _latest(claims, pred)
        if firing is not None:
            date_kind = "scheduled_action"
            break
    if firing is None:
        firing = _latest(claims, "bill_status_date")
    d = _date_of(firing)
    if firing is None or d is None:
        return []
    return [
        {
            "kind": "legislative_action",
            "date": d.isoformat(),
            "date_kind": date_kind,
            "date_certainty": "stated",
            "firing_claims": {firing.claim_id} | {c.claim_id for c in matched},
        }
    ]


def _derive_grant(subject_key: str, claims: Sequence[_Claim]) -> list[dict[str, Any]]:
    """Rule 6 — ``grant_period_end``: funding period end + a surveillance match."""
    period = _latest(claims, "period")
    _start, end = _period_bounds(period)
    matched = _all(claims, "matched_keyword") + _all(claims, "content_term")
    end_d: date | None = None
    if end:
        try:
            end_d = date.fromisoformat(end[:10])
        except ValueError:
            end_d = None
    if period is None or end_d is None or not matched:
        return []
    return [
        {
            "kind": "grant_period_end",
            "date": end_d.isoformat(),
            "date_certainty": "stated",
            "firing_claims": {period.claim_id} | {c.claim_id for c in matched},
        }
    ]


_DERIVERS = {
    "contract": _derive_contracts,
    "procurement_notice": _derive_notice,
    "agenda_item": _derive_agenda,
    "legislative_bill": _derive_bill,
    "funding_instrument": _derive_grant,
}


# --------------------------------------------------------------------------- #
# Titles — per-kind templates; a verbatim title that names a person is never
# the agenda/bill label (K7 §6: the matter number + matched term carry it)
# --------------------------------------------------------------------------- #


def _title(
    kind: str,
    subject_key: str,
    claims: Sequence[_Claim],
    *,
    body: str | None,
    date_value: str,
) -> str:
    """The per-kind title — the S-2/S-5/S-7 scrub applies to each claim-derived
    PART (body, external id, term labels, bill id/status, program), never to
    the composed string: the templates and ISO dates are safe literals, and a
    whole-string scrub would strip an ISO date as personal data. A
    person-named verbatim title never surfaces (K7 §6 — the matter number +
    matched term carry the label)."""
    tech, vendors = _matched_terms(claims)
    tag = ""
    if vendors:
        tag = f" — {scrub_text(vendors[0]['label'])}"
    elif tech:
        tag = f" ({scrub_text(tech[0]['label'])})"
    who = scrub_text(body) if body else "the buyer"
    ext = scrub_text(_external_id(subject_key))
    if kind == "renewal_deadline":
        return (
            f"{who}: contract {ext} renewal decision — "
            f"auto-renews without action by {date_value}{tag}"
        )
    if kind == "contract_expiry":
        return (
            f"{who}: contract {ext} — latest possible end {date_value}"
            " (renewal terms not on record)"
        )
    if kind == "solicitation_deadline":
        return f"{who}: solicitation {ext} — responses due {date_value}{tag}"
    if kind == "agenda_item":
        return f"{who}: agenda item {ext} on {date_value}{tag}"
    if kind == "legislative_action":
        bill = _text(_latest(claims, "bill_identifier")) or ext
        status = _text(_latest(claims, "bill_status"))
        return (
            f"{who}: bill {scrub_text(bill)} — "
            f"{scrub_text(status) if status else 'status update'} ({date_value}){tag}"
        )
    program = _text(_latest(claims, "program_name"))
    return (
        f"{who}: funding period for "
        f"{scrub_text(program) if program else ext} ends {date_value}{tag}"
    )


# --------------------------------------------------------------------------- #
# The build
# --------------------------------------------------------------------------- #


def build_watch_payload(
    raw: Mapping[str, Any],
    *,
    as_of: date,
    generated_at: str,
    dossier_places: Sequence[Mapping[str, Any]] = (),
    placement: _placement.PlacementEngine | None = None,
    lane_by_source: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """The ``sig/watch/2`` envelope — items + coverage, honest when empty.

    ``raw`` supplies the producer's own reads (``watch_claims``,
    ``watch_subject_counts``) plus the shared evidence/task/contradiction rows
    (``claim_binding_detail``, ``evidence_artifacts``, ``research_tasks``,
    ``materialized_contradictions``). ``dossier_places`` is the dossier index's
    place list (``{key, slug}``) — every dossier place gets a coverage row even
    with zero items (SIG-WATCH-D04).
    """
    claims = _claims(raw)
    by_subject: dict[str, list[_Claim]] = {}
    for c in claims:
        by_subject.setdefault(c.subject_key, []).append(c)

    # Shared row sets — evidence bindings (P32.2 detail), artifact upstream
    # URLs (the evidence_artifacts read is already effective-rights gated),
    # open research tasks, and the materialized contradiction index.
    binding_by_claim: dict[str, list[dict[str, Any]]] = {}
    for d in _dicts(raw.get("claim_binding_detail") or [], _stmt.BINDING_DETAIL_COLUMNS):
        binding_by_claim.setdefault(str(d.get("claim_id") or ""), []).append(d)
    artifact_url_by_id: dict[str, str] = {}
    for r in raw.get("evidence_artifacts") or ():
        try:
            aid, url = str(r[0]), r[10]
        except (TypeError, IndexError):
            continue
        if url:
            artifact_url_by_id[aid] = str(url)
    tasks_by_subject: dict[str, list[dict[str, Any]]] = {}
    for r in _dicts(raw.get("research_tasks") or [], _RESEARCH_TASK_COLUMNS):
        if str(r.get("status") or "") in _CLOSED_TASK_STATUSES:
            continue
        tasks_by_subject.setdefault(str(r.get("subject_id") or ""), []).append(r)
    contested_claims: set[str] = set()
    contested_subjects: set[str] = set()
    for c in raw.get("materialized_contradictions") or ():
        if not isinstance(c, Mapping):
            continue
        for cid in c.get("claim_ids") or ():
            contested_claims.add(str(cid))
        if c.get("subject_id"):
            contested_subjects.add(str(c["subject_id"]))

    lane_by_source = lane_by_source or {}

    # Supersession/withdrawal index — a claim is superseded when another
    # publishable claim's ``revises_claim`` names it; retracted when a
    # ``retraction_of`` does (the edge lives on the NEWER row).
    superseded: frozenset[str] = frozenset(str(c.revises_claim) for c in claims if c.revises_claim)
    retracted: frozenset[str] = frozenset(str(c.retraction_of) for c in claims if c.retraction_of)

    # -- derive drafts (kind/date/certainty per subject) -------------------- #
    drafts: list[dict[str, Any]] = []
    for subject_key in sorted(by_subject):
        family = _family(subject_key)
        deriver = _DERIVERS.get(family)
        if deriver is None:
            continue
        subj_claims = by_subject[subject_key]
        for draft in deriver(subject_key, subj_claims):
            try:
                item_date = date.fromisoformat(str(draft["date"]))
            except ValueError:
                continue
            if not _listed(draft["kind"], item_date, as_of):
                continue
            drafts.append(
                {
                    **draft,
                    "subject_key": subject_key,
                    "claims": subj_claims,
                    "_d": item_date,
                }
            )

    # -- handles + placement ------------------------------------------------ #
    for draft in drafts:
        draft["handle"] = _handle(None, draft["kind"], draft["subject_key"])
    if placement is not None:
        inputs = [_placement_input(d["subject_key"], d["claims"], d["handle"]) for d in drafts]
        results = placement.place_many(inputs)
        result_by_handle = {r.record_id: r for r in results}
    else:
        result_by_handle = {}

    # -- emit items ---------------------------------------------------------- #
    items: list[dict[str, Any]] = []
    for draft in drafts:
        claims_for = draft["claims"]
        res = result_by_handle.get(draft["handle"])
        if res is not None:
            place = {
                "key": res.jurisdiction_key,
                "chain": list(res.jurisdiction_chain),
                "basis": res.placement_basis,
                "check": res.placement_check,
                "declared_scheme": res.declared[0] if res.declared else None,
                "declared_value": res.declared[1] if res.declared else None,
                "boundary_vintage": res.boundary_vintage,
            }
            place_part = jurisdiction_slug(res.jurisdiction_key) if res.jurisdiction_key else None
        else:
            place = {"key": None, "chain": [], "basis": None, "check": "unplaced"}
            place_part = None
        # Re-mint the handle with the resolved place (W-<place>-… — the place
        # segment exists only once placement ran; pre-placement draft handles
        # are never emitted).
        if place_part:
            draft["handle"] = _handle(place_part, draft["kind"], draft["subject_key"])
        kind = draft["kind"]
        subject_entity_ids = {c.subject_id for c in claims_for}
        body = (
            _text(_latest(claims_for, "buyer"))
            or _text(_latest(claims_for, "funder"))
            or _tenant_jurisdictions().get(_tenant_for(draft["subject_key"]) or "")
            or _text(_latest(claims_for, "bill_jurisdiction"))
        )
        tech, vendors = _matched_terms(claims_for)
        firing_ids = draft["firing_claims"]
        firing = claims_for[0]
        for c in claims_for:
            fd = _date_of(c)
            if c.claim_id in firing_ids and fd is not None and fd.isoformat() == draft["date"]:
                firing = c
                break
        status = _status(draft["_d"], as_of, firing, superseded=superseded, retracted=retracted)
        item: dict[str, Any] = {
            "schema": SCHEMA_WATCH_ITEM,
            "handle": draft["handle"],
            "title": _title(
                kind,
                draft["subject_key"],
                claims_for,
                body=body,
                date_value=str(draft["date"]),
            ),
            "kind": kind,
            "date": draft["date"],
            "date_kind": draft.get("date_kind") or _DATE_KIND_BY_KIND[kind],
            "date_certainty": draft["date_certainty"],
            "timeline": _timeline(claims_for),
            "place": place,
            "body": scrub_text(body) if body else None,
            "subjects": [draft["subject_key"]],
            "technology": tech,
            "vendor": vendors,
            "status": status,
            "what_you_can_do": _WHAT_YOU_CAN_DO[kind].format(body=body or "the issuing body"),
            "evidence": _evidence_links(
                [c for c in claims_for if c.claim_id in firing_ids] or [claims_for[0]],
                binding_by_claim,
                artifact_url_by_id,
                lane_by_source,
            ),
            "contested": bool(
                (set(firing_ids) | {c.claim_id for c in claims_for}) & contested_claims
            )
            or bool(subject_entity_ids & contested_subjects),
            "tasks": [
                {
                    "task_id": str(t["task_id"]),
                    "task_type": str(t["task_type"]),
                    "status": str(t["status"]),
                }
                for t in sorted(
                    (t for sid in subject_entity_ids for t in (tasks_by_subject.get(sid) or ())),
                    key=lambda t: str(t["task_id"]),
                )
            ],
            "first_seen": _first_seen(claims_for),
            "last_checked": generated_at,
            "source_ids": _source_ids(claims_for),
        }
        if draft.get("termination"):
            item["termination"] = draft["termination"]
        items.append(item)

    items.sort(key=lambda i: (i["date"], i["handle"]))

    # -- coverage ------------------------------------------------------------ #
    count_rows = _dicts(raw.get("watch_subject_counts") or [], WATCH_COUNT_COLUMNS)
    sizing = {
        str(r.get("family") or ""): {
            "subjects": int(r.get("subjects") or 0),
            "claims": int(r.get("claims") or 0),
        }
        for r in count_rows
        if r.get("family")
    }
    coverage = _coverage(items, dossier_places, generated_at, sizing)

    return {
        "schema": SCHEMA_WATCH,
        "as_of": as_of.isoformat(),
        "generated_at": generated_at,
        "build": {
            "ruleset": WATCH_RULESET,
            "windows": {
                "list_days": _LIST_WINDOW_DAYS,
                "recently_decided_days": _RECENTLY_DECIDED_DAYS,
                "contract_horizon_days": _CONTRACT_HORIZON_DAYS,
                "solicitation_from": "posted_date",
                "basis": (
                    "K7 §5.2 windows — the design's declared inference pending "
                    "operator decision D-K7-4 (never silently ratified)"
                ),
            },
            "what_you_can_do_basis": (
                "agent-drafted procedural templates pending operator sign-off "
                "(K7 §5.1; no position is ever recommended — W-P4/W-P5)"
            ),
        },
        "coverage": coverage,
        "items": items,
    }


#: Research-task statuses that no longer need listing under an item.
_CLOSED_TASK_STATUSES: frozenset[str] = frozenset(
    {"resolved", "closed", "done", "completed", "withdrawn"}
)

#: Positional columns of the ``research_tasks`` raw rows (the EXPORT_QUERIES
#: SELECT order in spine_export).
_RESEARCH_TASK_COLUMNS: tuple[str, ...] = (
    "task_id",
    "task_type",
    "subject_id",
    "jurisdiction_id",
    "priority",
    "status",
    "disposition",
    "closing_condition",
    "detector_version",
    "trigger_kind",
    "trigger_ref",
)


def _coverage(
    items: Sequence[Mapping[str, Any]],
    dossier_places: Sequence[Mapping[str, Any]],
    generated_at: str,
    sizing: Mapping[str, Any],
) -> dict[str, Any]:
    """SIG-WATCH-D04 — every dossier-index place gets a coverage row, empty or
    not; the monitored-portal statement rides the committed tenant registries
    (bodies/portals SIG actually checks, never a claimed coverage it lacks)."""
    tenants = _tenant_jurisdictions()
    by_place: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        place = item.get("place") or {}
        keys = [k for k in (place.get("chain") or ()) if k] or (
            [place["key"]] if place.get("key") else []
        )
        for k in keys or ():
            by_place.setdefault(str(k), []).append(item)
    places: list[dict[str, Any]] = []
    for p in dossier_places:
        key = str(p.get("key") or "")
        slug = str(p.get("slug") or jurisdiction_slug(key))
        rows = by_place.get(key) or []
        places.append(
            {
                "key": key,
                "slug": slug,
                "items": len(rows),
                "kinds": sorted({str(i["kind"]) for i in rows}),
                "last_checked": generated_at,
            }
        )
    return {
        "monitored": {
            "tenant_jurisdictions": sorted(set(tenants.values())),
            "tenants_registered": len(tenants),
        },
        "places": places,
        "by_kind": {k: sum(1 for i in items if i["kind"] == k) for k in WATCH_KINDS},
        "items_total": len(items),
        "sizing": dict(sizing),
        "last_checked": generated_at,
    }
