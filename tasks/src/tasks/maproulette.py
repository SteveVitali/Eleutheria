# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The MapRoulette cooperative-challenge client (§33, §35.2; P21.7, ADR-069).

The live edge of contribution back: it turns a selection of SIG suggestions into a
MapRoulette *cooperative* challenge (``cooperativeType=tags``) a human mapper works
one decision at a time (:mod:`tasks.contribution` owns the suggestion/apply/metric
posture; this module owns only the client and its refusals). Four load-bearing
properties, each pinned by ``tests/tasks/test_tasks_maproulette.py``:

* **Human-mediated, never an automated write (SIG-CONTRIB-014/015).** The client
  creates a *challenge* of proposals; it never applies an edit. The challenge's
  ``checkinComment`` carries :data:`~tasks.contribution.CHANGESET_HASHTAG` (016e) —
  :class:`~tasks.contribution.CooperativeChallenge` refuses one that does not.
* **Sensitive tiers are never pushed (RISK-P21-12, §43.3, Part VIII §0.7).** A task
  whose sensitivity class publishes no geometry (``geo_tier >=``
  :data:`SENSITIVE_GEO_TIER_FLOOR` — C3/C4/C5) is **excluded** from the payload:
  a MapRoulette task pins a mapper to a coordinate, so a confidential-facility or
  mobile-asset location must never leave SIG inside a challenge.
* **Registration-gated push (SIG-CONTRIB-016d, RISK-P16-14).** :meth:`MapRouletteClient.push`
  **refuses** (raises :class:`ChallengeNotRegisteredError`) while the Organised
  Editing activity is not registered (``ops/config.toml`` ``[tasks.contribution]
  registered=false``) — the CLI maps that to exit 3. Registering is an off-repo human
  act (HG-08); the flag records it, it does not perform it.
* **Dry-run without the key (additive/back-compat).** With no
  ``SIG_MAPROULETTE_API_KEY`` the client is in **dry-run**: ``push``/``pull`` return
  the exact JSON payload/endpoint they *would* send and touch no network. A live
  call needs the key AND a configured transport (never exercised without HG-08).
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from policy.sensitivity import SensitivityClass, geo_tier_for

from .contribution import (
    CHANGESET_HASHTAG,
    CooperativeChallenge,
    TagSuggestion,
    cooperative_task_payload,
)

__all__ = [
    "MAPROULETTE_API_KEY_ENV",
    "DEFAULT_BASE_URL",
    "SENSITIVE_GEO_TIER_FLOOR",
    "MapRouletteError",
    "ChallengeNotRegisteredError",
    "ChallengeTask",
    "MapRouletteTransport",
    "MapRouletteClient",
    "jurisdiction_hashtag",
    "build_challenge",
    "build_challenge_payload",
]

#: The env var holding the MapRoulette API key (HG-08). Absent ⇒ dry-run.
MAPROULETTE_API_KEY_ENV = "SIG_MAPROULETTE_API_KEY"

#: The MapRoulette API v2 base URL (the located API, SIG-CONTRIB-015b).
DEFAULT_BASE_URL = "https://maproulette.org/api/v2"

#: A task whose sensitivity class sits at or above this geospatial tier publishes
#: **no** geometry (§19.4 tier 3 = ``jurisdiction_only``; classes C3/C4/C5). Such a
#: task is excluded from every challenge push — its coordinate must never leave SIG
#: (RISK-P21-12, §43.3, Part VIII §0.7).
SENSITIVE_GEO_TIER_FLOOR = 3


class MapRouletteError(RuntimeError):
    """Base class for MapRoulette client errors."""


class ChallengeNotRegisteredError(MapRouletteError):
    """Raised when a challenge push is attempted before the OE activity is registered.

    The CLI maps this to exit 3 with the Organised-Editing-registration reason
    (SIG-CONTRIB-016d, RISK-P16-14): SIG may not direct volunteers at a challenge
    that is not disclosed and registered in the OSM activities list.
    """


def jurisdiction_hashtag(jurisdiction: str) -> str:
    """The per-jurisdiction challenge hashtag ``#sig-<jurisdiction>`` (§35).

    Distinct from the changeset hashtag (:data:`CHANGESET_HASHTAG`, which the
    metric reads): this tags the *challenge* so a jurisdiction's contribution
    effort is legible, while every applied edit still carries the changeset
    hashtag the §7 metric counts.
    """
    slug = jurisdiction.strip().lower().replace(" ", "-")
    if not slug:
        raise ValueError("a challenge MUST name its jurisdiction (§35)")
    return f"#sig-{slug}"


@dataclass(frozen=True)
class ChallengeTask:
    """A geo task selected for a challenge: a suggestion plus its coordinate + tier.

    ``sensitivity_class`` gates publication. A task whose class publishes no geometry
    (``geo_tier >=`` :data:`SENSITIVE_GEO_TIER_FLOOR`) is **not pushable** — the
    challenge pins a mapper to the coordinate, so a sensitive-tier location must
    never appear in a push payload (RISK-P21-12). Only geo tasks reach here (§35).
    """

    suggestion: TagSuggestion
    lat: float
    lon: float
    sensitivity_class: SensitivityClass = SensitivityClass.C1

    @property
    def is_pushable(self) -> bool:
        """Whether this task's coordinate may be published in a challenge (RISK-P21-12)."""
        return geo_tier_for(self.sensitivity_class) < SENSITIVE_GEO_TIER_FLOOR


def build_challenge(
    *,
    challenge_id: str,
    name: str,
    instruction: str,
    jurisdiction: str,
) -> CooperativeChallenge:
    """Build a cooperative challenge whose checkin comment carries both hashtags.

    The ``checkinComment`` carries the changeset hashtag (required — the §7 metric
    reads it) *and* the per-jurisdiction challenge hashtag, so an applied edit is
    both counted and jurisdiction-legible.
    """
    checkin_comment = f"{name} {CHANGESET_HASHTAG} {jurisdiction_hashtag(jurisdiction)}"
    return CooperativeChallenge(
        challenge_id=challenge_id,
        name=name,
        instruction=instruction,
        checkin_comment=checkin_comment,
    )


def build_challenge_payload(
    *,
    challenge: CooperativeChallenge,
    jurisdiction: str,
    tasks: Iterable[ChallengeTask],
) -> dict[str, Any]:
    """Render a MapRoulette API v2 challenge-creation payload (SIG-CONTRIB-015a).

    Sensitive-tier tasks are dropped before rendering (RISK-P21-12): they contribute
    only to ``excluded_sensitive_task_count`` — never a coordinate. Each remaining
    task is a cooperative ``tags`` operation (from
    :func:`~tasks.contribution.cooperative_task_payload`) with a point geometry.
    """
    task_list = list(tasks)
    pushable = [t for t in task_list if t.is_pushable]
    excluded = len(task_list) - len(pushable)
    features: list[dict[str, Any]] = []
    for task in pushable:
        payload = cooperative_task_payload(task.suggestion)
        payload["geometry"] = {"type": "Point", "coordinates": [task.lon, task.lat]}
        features.append(payload)
    return {
        "name": challenge.name,
        "description": challenge.instruction,
        "instruction": challenge.instruction,
        "checkinComment": challenge.checkin_comment,
        "checkinSource": challenge.checkin_source,
        "enabled": challenge.enabled,
        "cooperativeType": challenge.cooperative_type.value,
        "hashtag": jurisdiction_hashtag(jurisdiction),
        "tasks": features,
        "excluded_sensitive_task_count": excluded,
    }


class MapRouletteTransport(Protocol):
    """The minimal HTTP seam a *live* MapRoulette call needs (never used in dry-run).

    Kept behind a Protocol so a live wiring supplies an ``httpx``-backed poster with
    the same no-circumvention / TLS-verify posture as
    :class:`connectors.transports.httpx_transport.HttpxTransport`, and a test injects
    a fake to assert the live request shape without opening a socket.
    """

    def post(self, url: str, *, json: dict[str, Any], api_key: str) -> dict[str, Any]: ...

    def get(self, url: str, *, api_key: str) -> dict[str, Any]: ...


@dataclass
class MapRouletteClient:
    """Create/update a challenge and fetch task-status changes (P21.7, ADR-069).

    In **dry-run** (no ``api_key``) ``push``/``pull`` return the payload/endpoint they
    would send and touch no network — the default posture without HG-08. A live call
    needs both the key and a ``transport``; absent a transport the live branch raises
    rather than silently no-op'ing (never fabricate a call that did not happen).
    """

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    transport: MapRouletteTransport | None = None

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        transport: MapRouletteTransport | None = None,
    ) -> MapRouletteClient:
        """Build a client, reading the API key from the environment (HG-08)."""
        source = os.environ if env is None else env
        key = (source.get(MAPROULETTE_API_KEY_ENV) or "").strip() or None
        return cls(api_key=key, transport=transport)

    @property
    def dry_run(self) -> bool:
        """Whether the client is in dry-run (no API key ⇒ no live call)."""
        return not self.api_key

    def push(
        self,
        *,
        challenge: CooperativeChallenge,
        jurisdiction: str,
        tasks: Sequence[ChallengeTask],
        registered: bool,
    ) -> dict[str, Any]:
        """Create/update the challenge, or REFUSE while unregistered / dry-run.

        Refuses (``ChallengeNotRegisteredError``) unless ``registered`` — the OE
        activity gate (SIG-CONTRIB-016d, RISK-P16-14). When registered but keyless,
        returns the dry-run payload. With key + transport, POSTs it (HG-08 only).
        """
        if not registered:
            raise ChallengeNotRegisteredError(
                "REFUSED: a MapRoulette challenge may not be pushed while the SIG "
                "Organised Editing activity is not registered "
                "(ops/config.toml [tasks.contribution] registered=false; "
                "SIG-CONTRIB-016d, RISK-P16-14). Register the activity (HG-08) first."
            )
        payload = build_challenge_payload(
            challenge=challenge, jurisdiction=jurisdiction, tasks=tasks
        )
        endpoint = f"{self.base_url}/challenge"
        if self.dry_run:
            return {"action": "push", "dry_run": True, "endpoint": endpoint, "payload": payload}
        if self.transport is None:
            raise MapRouletteError(
                "a live push needs a configured MapRouletteTransport (HG-08); "
                "none is wired — refusing to claim a call that did not happen"
            )
        response = self.transport.post(endpoint, json=payload, api_key=self.api_key or "")
        return {"action": "push", "dry_run": False, "endpoint": endpoint, "response": response}

    def pull(self, *, challenge_id: str) -> dict[str, Any]:
        """Fetch task-status changes for a challenge, or return the dry-run request.

        Read-only (task statuses feed the §7 metric via the changeset feed, not this
        call): dry-run returns the endpoint it would GET; live GETs it (HG-08 only).
        """
        if not challenge_id:
            raise ValueError("a pull MUST name a challenge id")
        endpoint = f"{self.base_url}/challenge/{challenge_id}/tasks/statuses"
        if self.dry_run:
            return {
                "action": "pull",
                "dry_run": True,
                "endpoint": endpoint,
                "challenge_id": challenge_id,
            }
        if self.transport is None:
            raise MapRouletteError(
                "a live pull needs a configured MapRouletteTransport (HG-08); "
                "none is wired — refusing to claim a call that did not happen"
            )
        response = self.transport.get(endpoint, api_key=self.api_key or "")
        return {
            "action": "pull",
            "dry_run": False,
            "endpoint": endpoint,
            "challenge_id": challenge_id,
            "response": response,
        }
