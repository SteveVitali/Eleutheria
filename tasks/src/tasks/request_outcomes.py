# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The records-request outcome log — the recording backend for BL-028 (D-META.1-2).

:mod:`tasks.records_request` (P10.3, ADR-041) generates ready-to-file request
*templates*; this module is the outcome-recording half the P24.5 triage deferred
until real records-request activity existed. It is an append-only, per-request
log of filing/response outcomes fed by real activity — the claim spine's
``records_request`` predicate surface (what the records connector wrote from a
real MuckRock api_v2 pull) or a platform API payload directly.

The rules:

* **Append-only (P2).** The log is JSONL — a new observation is a new line,
  never a rewrite. :meth:`RequestOutcomeLog.latest` folds the log to the
  current state per request; the view is derived, the history is not.
* **No fabricated outcomes.** An outcome is recorded only from observed data
  (a payload or claim rows). A request still in flight is recorded as
  in-flight; the log never invents a terminal state.
* **The template feed is explicit.** :func:`feed_template_log` measures a
  template version's success rate (SIG-TASK-017) only when the caller names the
  ``record_type`` and template ``version`` that produced the filing — metadata
  SIG's own filings carry. A third-party request SIG merely cites as provenance
  (e.g. an EFF MuckRock request) is recorded in the log but MUST NOT be counted
  against a template's success rate. ``no_responsive_records`` is never a
  template failure: the agency answered on the record (SIG-TASK-009).
* **Coarse state + precise status.** Every outcome carries both the coarse
  ``state`` (filed / acknowledged / in-flight / completed) the log folds on and
  the precise §11.19 ``response_status`` it was derived from; the status → state
  map is versioned data (``data/request_outcomes.toml``), and an unmapped status
  fails loud rather than silently coercing.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

from ._data import load_table
from .records_request import TemplateOutcomeLog

__all__ = [
    "DEFAULT_LOG_PATH",
    "OUTCOME_STATES",
    "InvalidOutcome",
    "RequestOutcome",
    "RequestOutcomeLog",
    "feed_template_log",
    "is_terminal",
    "outcome_from_api_payload",
    "outcome_from_claims",
    "outcome_state_for",
    "outcomes_version",
]

#: The default append-only log location (env-overridable via the CLI).
DEFAULT_LOG_PATH = Path(".sig") / "tasks" / "records_outcomes.jsonl"


# --- the versioned outcome vocabulary (data, not code — SIG-ENG-001) ----------


class InvalidOutcome(ValueError):
    """Raised when an outcome cannot be honestly derived from the observation."""


@cache
def _outcome_data() -> dict[str, Any]:
    return load_table("request_outcomes")


def outcomes_version() -> str:
    """The outcome vocabulary's version (§20)."""
    return str(_outcome_data()["outcomes_version"])


@cache
def _status_to_state() -> dict[str, str]:
    rows = _outcome_data()["status_to_state"]
    assert isinstance(rows, dict)
    return {str(k): str(v) for k, v in rows.items()}


#: The coarse outcome states the log folds on (the ticket's
#: filed/acknowledged/completed plus in-flight and the not-yet-filed draft).
OUTCOME_STATES: frozenset[str] = frozenset(_status_to_state().values())


def outcome_state_for(response_status: str) -> str:
    """Map a §11.19 ``RecordsResponseStatus`` to its coarse outcome state.

    The map is versioned data (``data/request_outcomes.toml``); an unknown
    status fails loud — a silent coerce would mis-record a real outcome.
    """
    try:
        return _status_to_state()[response_status]
    except KeyError:
        raise InvalidOutcome(
            f"response_status {response_status!r} has no outcome-state mapping in "
            "data/request_outcomes.toml — a new §11.19 status is a versioned data "
            "change, never a silent coerce"
        ) from None


def is_terminal(response_status: str) -> bool:
    """Whether a §11.19 status closes the request (the ``completed`` state)."""
    return outcome_state_for(response_status) == "completed"


@cache
def _success_statuses() -> frozenset[str]:
    rows = _outcome_data()["template_success_statuses"]
    assert isinstance(rows, list)
    return frozenset(str(s) for s in rows)


@cache
def _template_excluded_statuses() -> frozenset[str]:
    rows = _outcome_data()["template_excluded_statuses"]
    assert isinstance(rows, list)
    return frozenset(str(s) for s in rows)


# --- the outcome record ------------------------------------------------------


@dataclass(frozen=True)
class RequestOutcome:
    """One observed outcome for one records request (the log's row shape).

    ``request_id`` is the platform's external id (e.g. MuckRock ``136412``);
    ``agency`` is whatever the observation carries (a platform agency id or a
    name — never resolved here, SIG-INGEST-034). ``state`` is the coarse fold
    state; ``response_status`` the precise §11.19 status it came from (``None``
    when the observation carries none). ``observed_at`` is when SIG recorded
    the observation; ``source`` names where it came from (``claim_spine``,
    ``muckrock_api``, a fixture id, …).
    """

    request_id: str
    platform: str
    state: str
    source: str
    observed_at: str
    agency: str | None = None
    response_status: str | None = None
    filed_date: str | None = None
    response_date: str | None = None

    def __post_init__(self) -> None:
        if not str(self.request_id).strip():
            raise InvalidOutcome("a RequestOutcome requires a request_id")
        if self.state not in OUTCOME_STATES:
            raise InvalidOutcome(
                f"outcome state {self.state!r} is not in {sorted(OUTCOME_STATES)} "
                "(data/request_outcomes.toml)"
            )

    @property
    def key(self) -> str:
        """The log's per-request fold key (platform + external id)."""
        return f"{self.platform}:{self.request_id}"

    @property
    def terminal(self) -> bool:
        """Whether this observation is a completed (closed) request."""
        return self.state == "completed"

    def to_row(self) -> dict[str, Any]:
        """The JSONL row: every field, ``None`` included, so rows are self-describing."""
        return {
            "request_id": self.request_id,
            "platform": self.platform,
            "agency": self.agency,
            "state": self.state,
            "response_status": self.response_status,
            "filed_date": self.filed_date,
            "response_date": self.response_date,
            "observed_at": self.observed_at,
            "source": self.source,
            "outcomes_version": outcomes_version(),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> RequestOutcome:
        """Parse one JSONL row back into a :class:`RequestOutcome`."""
        return cls(
            request_id=str(row["request_id"]),
            platform=str(row["platform"]),
            agency=str(row["agency"]) if row.get("agency") is not None else None,
            state=str(row["state"]),
            response_status=(
                str(row["response_status"]) if row.get("response_status") is not None else None
            ),
            filed_date=str(row["filed_date"]) if row.get("filed_date") is not None else None,
            response_date=(
                str(row["response_date"]) if row.get("response_date") is not None else None
            ),
            observed_at=str(row["observed_at"]),
            source=str(row["source"]),
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _opt(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _claim_value(claim: Mapping[str, Any]) -> str | None:
    """The scalar a claim row carries — typed ``value``/``value_text`` or raw (P2)."""
    for key in ("value", "value_text", "raw_value"):
        if claim.get(key) is not None:
            return _opt(claim[key])
    return None


def outcome_from_claims(
    claims: Iterable[Mapping[str, Any]],
    *,
    platform: str = "muckrock",
    source: str = "claim_spine",
    observed_at: str | None = None,
) -> RequestOutcome:
    """Fold one request's §11.19 predicate-surface claim rows into an outcome.

    ``claims`` are the append-only claim rows for a single request subject —
    spine rows (``predicate_id`` + ``value_text``) or connector rows
    (``predicate_id`` + ``value``); both carry the same predicate names. The
    fold takes the *latest* assertion per predicate by claim order (the spine
    is append-only, so a later claim is a later observation). A request with
    no ``response_status`` claim is recorded as ``filed`` when a filing date is
    asserted, else ``in_flight`` — never a fabricated terminal state.
    """
    surface: dict[str, str] = {}
    for claim in claims:
        predicate = str(claim.get("predicate_id") or "")
        value = _claim_value(claim)
        if predicate and value is not None:
            surface[predicate] = value
    request_id = surface.get("external_id") or surface.get("request_id")
    if not request_id:
        raise InvalidOutcome(
            "no external_id claim among the rows — an outcome requires the request's "
            "platform id (§11.19)"
        )
    status = surface.get("response_status")
    if status is not None:
        state = outcome_state_for(status)
    elif surface.get("filed_date"):
        state = "filed"
    else:
        state = "in_flight"
    return RequestOutcome(
        request_id=request_id,
        platform=_opt(surface.get("platform")) or platform,
        agency=_opt(surface.get("target_agency")),
        state=state,
        response_status=status,
        filed_date=_opt(surface.get("filed_date")),
        response_date=_opt(surface.get("response_date")),
        observed_at=observed_at or _now(),
        source=source,
    )


def outcome_from_api_payload(
    payload: Mapping[str, Any],
    *,
    platform: str = "muckrock",
    status_map: Mapping[str, str] | None = None,
    source: str = "muckrock_api",
    observed_at: str | None = None,
) -> RequestOutcome:
    """Parse one platform API request object (e.g. MuckRock api_v2) into an outcome.

    The raw platform status (``status``/``response_status``) is translated to
    the §11.19 vocabulary through ``status_map`` — the caller supplies the
    versioned map (for MuckRock, the connector's ``records_vocab.toml``
    ``[muckrock_status_map]``); a raw value the map does not cover fails loud
    (recorded drift, never a silent coerce). A payload with no status at all is
    ``in_flight`` unless a filing date is present. Only the outcome fields the
    log needs are read — request text is never retained (Part VIII posture).
    """
    request_id = _opt(payload.get("external_id") or payload.get("id") or payload.get("request_id"))
    if not request_id:
        raise InvalidOutcome("the payload carries no request id (external_id/id)")
    raw_status = _opt(payload.get("response_status") or payload.get("status"))
    status: str | None = None
    if raw_status is not None:
        status = (status_map or {}).get(raw_status, raw_status)
        state = outcome_state_for(status)  # fails loud on an unmapped status
    else:
        state = "filed" if _opt(payload.get("date_submitted")) else "in_flight"
    return RequestOutcome(
        request_id=request_id,
        platform=_opt(payload.get("platform")) or platform,
        agency=_opt(payload.get("target_agency") or payload.get("agency")),
        state=state,
        response_status=status,
        filed_date=_opt(payload.get("filed_date") or payload.get("date_submitted")),
        response_date=_opt(payload.get("response_date") or payload.get("datetime_done")),
        observed_at=observed_at or _now(),
        source=source,
    )


# --- the append-only log ------------------------------------------------------


class RequestOutcomeLog:
    """The append-only per-request outcome log (JSONL; BL-028).

    One line per observation; the file is never rewritten. :meth:`latest` folds
    the log to the current state per ``(platform, request_id)`` — a re-observed
    request's newest row wins in the view while every observation stays in the
    history.
    """

    def __init__(self, path: str | Path = DEFAULT_LOG_PATH) -> None:
        self.path = Path(path)

    def record(self, outcome: RequestOutcome) -> RequestOutcome:
        """Append one observation; returns it. Never rewrites an existing line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(outcome.to_row(), sort_keys=True) + "\n")
        return outcome

    def read_all(self) -> list[RequestOutcome]:
        """Every recorded observation, in log order."""
        if not self.path.exists():
            return []
        out: list[RequestOutcome] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(RequestOutcome.from_row(json.loads(line)))
        return out

    def latest(self) -> dict[str, RequestOutcome]:
        """The current state per request — the append-only fold view."""
        latest: dict[str, RequestOutcome] = {}
        for outcome in self.read_all():
            latest[outcome.key] = outcome
        return latest


# --- the template success-rate feed (SIG-TASK-017) ----------------------------


def feed_template_log(
    log: TemplateOutcomeLog,
    outcome: RequestOutcome,
    *,
    record_type: str,
    version: str,
) -> bool:
    """Feed one terminal outcome into a :class:`TemplateOutcomeLog`.

    Returns True when an outcome was counted. The caller MUST name the
    ``record_type`` and template ``version`` that produced the filing — they are
    metadata SIG's own filings carry, never guessed from the request. Counted
    only when the outcome is terminal and its status is not excluded
    (``no_responsive_records`` is a positive coverage finding, SIG-TASK-009, not
    a language failure); in-flight observations are recorded in the log but do
    not move a template's rate.
    """
    if not outcome.terminal or outcome.response_status is None:
        return False
    if outcome.response_status in _template_excluded_statuses():
        return False
    log.record_outcome(
        record_type,
        version,
        succeeded=outcome.response_status in _success_statuses(),
    )
    return True
