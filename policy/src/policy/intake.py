# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The anonymous correction receiver contract (P32.16 / ADR-135, §55.5 SIG-FIND-006).

The **pure** half of the durable anonymous correction intake: every rule the
public receiver and the private moderation loop share lives here as data-driven
functions over `data/intake_receiver.toml` — the POST field allowlist, per-field
bounds and shapes, the Part VIII pre-persistence screen, the append-only event
vocabulary and fail-closed transition table, and the coarse public-status map.

Two hard rules this module exists to hold (S4 research §8, §55.5):

* **Refused payloads are never persisted.** The Part VIII screen (plate /
  per-trip / per-person / per-search tokens and person-shaped identifier
  patterns) runs in :func:`validate_report` BEFORE any storage layer sees a
  row; a rejection carries per-field errors and no row, so forbidden content
  can never reach a public log or the claim spine by construction.
* **A received report is not a correction.** The event vocabulary keeps
  `applied`/`published` reserved for the P32.16a authorized bridge; nothing in
  this contract lets a submission or a reviewer turn into a claim write. The
  public status projection (:func:`public_state`) emits only coarse states —
  never raw narrative, contact or network identifiers.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from ._data import load_table
from .governance import intake_categories, permitted_outcomes

__all__ = [
    "IntakeContractError",
    "IntakeFieldError",
    "NormalizedReport",
    "allowed_fields",
    "category_ids",
    "category_response_window_hours",
    "contract",
    "contract_version",
    "event_vocabulary",
    "housekeeping_events",
    "is_lifecycle_event",
    "legal_transition",
    "limits",
    "moderation_events",
    "normalize_report",
    "public_state",
    "redactable_fields",
    "screen_part_viii",
    "validate_evidence_url",
    "validate_moderation_detail",
]


class IntakeContractError(Exception):
    """The receiver contract table is missing or malformed (fail closed)."""


class IntakeFieldError(Exception):
    """One or more intake fields failed validation — never persisted.

    ``fields`` maps each rejected field name to a safe, bounded reason; the
    receiver returns it verbatim (it names the *rule*, never echoes content).
    """

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(f"intake fields rejected: {sorted(fields)}")
        self.fields = fields


def contract() -> dict[str, Any]:
    """The `intake-receiver/1` contract table (data, not code)."""
    table = load_table("intake_receiver")
    if "contract" not in table or "limits" not in table or "events" not in table:
        raise IntakeContractError("intake_receiver.toml is missing required sections")
    return table


def contract_version() -> str:
    return str(contract()["contract"]["version"])


def limits() -> dict[str, Any]:
    return dict(contract()["limits"])


def allowed_fields() -> frozenset[str]:
    """The exact POST body allowlist — anything else is an unknown-field error."""
    return frozenset(str(f) for f in contract()["contract"]["fields"])


def category_ids() -> frozenset[str]:
    """The §45.1 categories, consumed from the one takedown.toml source of truth."""
    return frozenset(str(c["id"]) for c in intake_categories())


def category_response_window_hours(category: str) -> int:
    """The category's published response/triage SLA in hours (SIG-GOV-003).

    This is the existing **triage** SLA — never a promise of final resolution.
    """
    for c in intake_categories():
        if str(c["id"]) == category:
            return int(c["sla_hours"])
    raise IntakeContractError(f"unknown intake category {category!r}")


def _patterns() -> dict[str, str]:
    return dict(contract()["patterns"])


# --------------------------------------------------------------------------- #
# The Part VIII pre-persistence screen (§0.7 / §43.2 — never stored)
# --------------------------------------------------------------------------- #
def _forbidden_tokens() -> tuple[str, ...]:
    return tuple(str(t).lower() for t in contract()["part_viii"]["forbidden_tokens"])


def _person_shaped() -> tuple[re.Pattern[str], ...]:
    return tuple(
        re.compile(str(p), re.IGNORECASE) for p in contract()["part_viii"]["person_shaped_patterns"]
    )


def screen_part_viii(text: str, *, include_person_shaped: bool = True) -> str | None:
    """Return the matched forbidden token/pattern, or ``None`` if clean.

    The same Part VIII law the connector vocabularies carry: plate, per-trip,
    per-person and per-search content is refused *before persistence* — the
    caller must let the raise propagate so no row is ever written. Person-shaped
    identifier patterns (email/phone/SSN/plate-shaped) are a best-effort screen,
    not a DLP promise; the quarantined payload stays reviewer-facing regardless.
    """
    lowered = text.lower()
    # Separator-normalized scan too: a URL/field writer can trivially dodge the
    # plain substring check with `license-plate`/`license.plate` — the refusal
    # must hold under the cheapest evasion (same tokens, separators→space).
    squashed = re.sub(r"[-_./]+", " ", lowered)
    for token in _forbidden_tokens():
        if token in lowered or token in squashed:
            return token
    if include_person_shaped:
        for pattern in _person_shaped():
            match = pattern.search(text)
            if match is not None:
                return match.group(0)
    return None


# --------------------------------------------------------------------------- #
# Field validators (each returns the normalized value or raises for its field)
# --------------------------------------------------------------------------- #
def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _check_pattern(value: str, name: str) -> bool:
    return re.fullmatch(_patterns()[name], value) is not None


def validate_evidence_url(url: str) -> str:
    """Validate one public evidence reference — never fetched (SSRF bar).

    Rules: https only; no userinfo/credentials; host must resolve lexically as
    a public name (no IP literals, loopback/private/link-local hosts, no
    ``localhost``); bounded length. The URL is stored verbatim as an untrusted
    reference — nothing in this codebase ever dereferences it.
    """
    max_chars = int(limits()["evidence_url_max_chars"])
    if len(url) > max_chars:
        raise IntakeFieldError({"evidence_urls": f"a URL exceeds {max_chars} chars"})
    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        raise IntakeFieldError({"evidence_urls": "a URL is not parseable"}) from exc
    if parts.scheme.lower() != "https":
        raise IntakeFieldError({"evidence_urls": "evidence references must be https://"})
    if not parts.hostname:
        raise IntakeFieldError({"evidence_urls": "a URL has no host"})
    if parts.username or parts.password:
        raise IntakeFieldError({"evidence_urls": "a URL must not carry credentials"})
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise IntakeFieldError({"evidence_urls": "a URL host is not public"})
    try:
        ip = ip_address(host.strip("[]"))
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise IntakeFieldError({"evidence_urls": "a URL host is not a public address"})
    return url.strip()


# --------------------------------------------------------------------------- #
# The normalized report
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NormalizedReport:
    """One validated, persistence-ready report payload (allowlisted fields only).

    ``form_token`` is deliberately absent — it is transport authentication,
    verified by the receiver and never stored.
    """

    category: str
    description: str
    idempotency_key: str
    publication_id: str | None = None
    record_key: str | None = None
    claim_ids: tuple[str, ...] = ()
    evidence_urls: tuple[str, ...] = ()
    contact_for_legal_demand: str | None = None


def _list_field(raw: Any) -> list[str]:
    """Coerce a JSON list / urlencoded repeated-or-comma field into a string list."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(v).strip() for v in raw if str(v).strip()]
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def normalize_report(
    fields: dict[str, Any],
    *,
    default_idempotency_key: str | None = None,
) -> NormalizedReport:
    """Validate + normalize a POST body against `intake-receiver/1`.

    Collects **every** field error and raises one :class:`IntakeFieldError`
    carrying all of them — a rejection enumerates which rules fired without
    echoing content. Nothing returned here has been persisted; callers treat a
    raise as "no row exists".
    """
    errors: dict[str, str] = {}
    lim = limits()

    for name in fields:
        if name not in allowed_fields():
            errors[name] = "unknown field"

    def text_field(name: str) -> str | None:
        raw = fields.get(name)
        if raw is None:
            return None
        if isinstance(raw, (list, tuple)):
            if len(raw) > 1:
                errors[name] = "must be a single value"
                return None
            raw = raw[0] if raw else ""
        if not isinstance(raw, str):
            errors[name] = "must be text"
            return None
        return _nfc(raw.strip())

    category = text_field("category")
    if category is None:
        errors["category"] = "a category is required"
    elif category not in category_ids():
        errors["category"] = "unknown category"

    publication_id = text_field("publication_id") or None
    if publication_id is not None and not _check_pattern(publication_id, "publication_id"):
        errors["publication_id"] = "not a release namespace (p-<64 hex>)"

    record_key = text_field("record_key") or None
    if record_key is not None and (
        len(record_key) > int(lim["record_key_max_chars"])
        or not _check_pattern(record_key, "record_key")
    ):
        errors["record_key"] = "not a <compartment>:<type>:<id> record key"

    claim_ids = _list_field(fields.get("claim_ids"))
    if len(claim_ids) > int(lim["claim_ids_max"]):
        errors["claim_ids"] = f"at most {lim['claim_ids_max']} claim ids"
    elif any(
        len(c) > int(lim["claim_id_max_chars"]) or not re.fullmatch(r"[0-9a-fA-F-]{8,128}", c)
        for c in claim_ids
    ):
        errors["claim_ids"] = "claim ids must be bounded public hex/uuid references"

    evidence_urls = _list_field(fields.get("evidence_urls"))
    if len(evidence_urls) > int(lim["evidence_urls_max"]):
        errors["evidence_urls"] = f"at most {lim['evidence_urls_max']} evidence references"
    else:
        for url in evidence_urls:
            try:
                validate_evidence_url(url)
            except IntakeFieldError as exc:
                errors["evidence_urls"] = next(iter(exc.fields.values()))
                break

    description = text_field("description") or ""
    d_min, d_max = int(lim["description_min_chars"]), int(lim["description_max_chars"])
    if not (d_min <= len(description) <= d_max):
        errors["description"] = f"must be {d_min}–{d_max} Unicode code points"

    contact = text_field("contact_for_legal_demand") or None
    if contact is not None:
        if len(contact) > int(lim["contact_max_chars"]):
            errors["contact_for_legal_demand"] = f"at most {lim['contact_max_chars']} code points"
        elif category != "legal_demand":
            errors["contact_for_legal_demand"] = (
                "only a legal_demand report may carry a contact (SIG-GOV-002)"
            )

    idem = text_field("idempotency_key") or (default_idempotency_key or "")
    if not re.fullmatch(_patterns()["idempotency_key"], idem):
        errors["idempotency_key"] = "must be a 16–128 char token nonce"

    # The Part VIII screen — LAST, so structural errors report first; a screen
    # hit refuses the field and the whole report (never persisted). The reason
    # names the rule and the remedy, never the matched content.
    _screen_reason = (
        "carries plate/person-shaped content — describe institutional facts "
        "only, no plates, names, contact or identifying details (Part VIII)"
    )
    if not errors.get("description"):
        hit = screen_part_viii(description)
        if hit is not None:
            errors["description"] = _screen_reason
    for url in evidence_urls:
        hit = screen_part_viii(url)
        if hit is not None:
            errors["evidence_urls"] = _screen_reason
            break
    if record_key is not None and screen_part_viii(record_key) is not None:
        errors["record_key"] = _screen_reason
    if contact is not None and screen_part_viii(contact, include_person_shaped=False) is not None:
        # A legal contact IS a person channel — the person-shaped screen does not
        # apply to it (it would reject every legitimate contact); forbidden Part
        # VIII tokens still do.
        errors["contact_for_legal_demand"] = _screen_reason

    if errors:
        raise IntakeFieldError(errors)

    assert category is not None and description and idem  # noqa: S101 - checked above
    return NormalizedReport(
        category=category,
        description=description,
        idempotency_key=idem,
        publication_id=publication_id,
        record_key=record_key,
        claim_ids=tuple(claim_ids),
        evidence_urls=tuple(evidence_urls),
        contact_for_legal_demand=contact,
    )


# --------------------------------------------------------------------------- #
# The append-only event vocabulary, transitions and public projection
# --------------------------------------------------------------------------- #
def event_vocabulary() -> dict[str, tuple[str, ...]]:
    ev = contract()["events"]
    return {
        "lifecycle": tuple(str(e) for e in ev["lifecycle"]),
        "housekeeping": tuple(str(e) for e in ev["housekeeping"]),
    }


def is_lifecycle_event(event: str) -> bool:
    return event in event_vocabulary()["lifecycle"]


def housekeeping_events() -> frozenset[str]:
    return frozenset(event_vocabulary()["housekeeping"])


def moderation_events() -> frozenset[str]:
    """The events a private reviewer may append through the curation surface.

    `received` belongs to the receiver only; `applied`/`published` are reserved
    for the P32.16a bridge role (nobody may write them here); `expunged` is
    written only by the retention function, never the API.
    """
    return frozenset(event_vocabulary()["lifecycle"]) - {
        "received",
        "applied",
        "published",
    } | {"redacted"}


def legal_transition(current_lifecycle: str | None, event: str) -> bool:
    """Whether ``event`` may follow the current lifecycle event (fail closed).

    ``current_lifecycle=None`` means the report only exists (a fresh row is in
    state ``received`` by construction — its ``received`` event is written in
    the same transaction). Housekeeping events (`redacted`, `expunged`) are
    always legal — they do not move the lifecycle.
    """
    if event in housekeeping_events():
        return True
    current = current_lifecycle or "received"
    for row in contract()["events"]["transitions"]:
        if str(row["from"]) == current:
            return event in {str(t) for t in row["to"]}
    return False


def public_state(lifecycle_event: str | None) -> str:
    """The coarse public status for a lifecycle event — the ONLY public label.

    Maps to received / under_review / decided / resolved / closed. Raw text,
    contact, URLs, network identifiers and reviewer rationale are never part
    of this projection.
    """
    lifecycle = lifecycle_event or "received"
    for row in contract()["public_status"]["map"]:
        if str(row["lifecycle"]) == lifecycle:
            return str(row["state"])
    raise IntakeContractError(f"no public-state mapping for {lifecycle!r}")


def redactable_fields() -> frozenset[str]:
    """The payload fields moderator redaction may clear (irreversible)."""
    return frozenset(
        {
            "description",
            "evidence_urls",
            "contact",
            "claim_ids",
            "publication_id",
            "record_key",
        }
    )


_EVENT_DETAIL_KEYS: dict[str, frozenset[str]] = {
    "triaged": frozenset({"note"}),
    "assigned": frozenset({"assignee", "note"}),
    "review_requested": frozenset({"note"}),
    "disposition_proposed": frozenset(
        {"outcome", "reason", "note", "public_response", "public_response_publish", "legal_hold"}
    ),
    "disposition_approved": frozenset(
        {
            "outcome",
            "reason",
            "note",
            "public_response",
            "public_response_publish",
            "approves_seq",
            "legal_hold",
        }
    ),
    "closed": frozenset({"note"}),
    "redacted": frozenset({"fields", "note"}),
}


def validate_moderation_detail(event: str, detail: dict[str, Any] | None) -> dict[str, Any]:
    """Validate + sanitize a moderation event's detail payload (fail closed).

    The detail is the restricted audit record: allowlisted keys only, bounded
    text, and — for dispositions — the mandatory outcome + reason every outcome
    (refusal included) must carry (SIG-GOV-004). ``public_response`` is the
    reviewer-authored text a reporter may see; it is returned publicly ONLY when
    the approver also sets ``public_response_publish`` true.
    """
    detail = dict(detail or {})
    allowed = _EVENT_DETAIL_KEYS.get(event)
    if allowed is None:
        raise IntakeFieldError({"event": f"{event!r} is not a moderation event"})
    unknown = set(detail) - allowed
    if unknown:
        raise IntakeFieldError({k: "unknown detail key" for k in sorted(unknown)})
    lim = limits()
    out: dict[str, Any] = {}

    def bounded(key: str, cap: int) -> str | None:
        v = detail.get(key)
        if v is None:
            return None
        s = _nfc(str(v).strip())
        if len(s) > cap:
            raise IntakeFieldError({key: f"at most {cap} code points"})
        return s or None

    note = bounded("note", int(lim["event_note_max_chars"]))
    if note:
        out["note"] = note

    if event == "assigned":
        assignee = bounded("assignee", 64)
        if assignee is None or re.fullmatch(r"[a-z0-9_.-]{2,64}", assignee) is None:
            raise IntakeFieldError({"assignee": "a reviewer handle (slug) is required"})
        out["assignee"] = assignee

    if event in {"disposition_proposed", "disposition_approved"}:
        outcome = bounded("outcome", 64)
        outcomes = frozenset(str(o["id"]) for o in permitted_outcomes())
        if outcome is None or outcome not in outcomes:
            raise IntakeFieldError({"outcome": f"must be one of {sorted(outcomes)}"})
        reason = bounded("reason", int(lim["event_note_max_chars"]))
        if reason is None:
            raise IntakeFieldError(
                {"reason": "every disposition MUST carry a reason — refusal included"}
            )
        response = bounded("public_response", int(lim["public_response_max_chars"]))
        publish = bool(detail.get("public_response_publish"))
        if publish and response is None:
            raise IntakeFieldError(
                {"public_response": "required when public_response_publish is true"}
            )
        out["outcome"] = outcome
        out["reason"] = reason
        if response is not None:
            out["public_response"] = response
        if publish:
            out["public_response_publish"] = True
        if detail.get("legal_hold"):
            out["legal_hold"] = True
        if event == "disposition_approved":
            seq = detail.get("approves_seq")
            if not isinstance(seq, int) or seq < 1:
                raise IntakeFieldError(
                    {"approves_seq": "the event_seq of the proposal being approved"}
                )
            out["approves_seq"] = seq
        # A response published to the reporter must survive the same Part VIII
        # screen — it is bounded reviewer-authored text headed for a receipt.
        if response is not None and screen_part_viii(response) is not None:
            raise IntakeFieldError({"public_response": "matches the Part VIII refusal screen"})

    if event == "redacted":
        raw = _list_field(detail.get("fields"))
        bad = set(raw) - redactable_fields()
        if not raw or bad:
            raise IntakeFieldError({"fields": f"subset of {sorted(redactable_fields())} required"})
        out["fields"] = sorted(set(raw))

    return out
