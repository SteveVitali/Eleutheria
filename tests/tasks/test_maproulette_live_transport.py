# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The activation-ready live MapRoulette transport (P29.1, HG-08; ADR-069).

Proves the concrete httpx transport wires a real push/pull the moment the operator
provides a key AND registration — WITHOUT opening a socket (httpx.MockTransport) — and
that the registration gate + dry-run posture keep it dormant otherwise. No live call is
made here (no key is provisioned in this run); this is the activation-ready proof.
"""

from __future__ import annotations

import httpx
import pytest
from policy.sensitivity import SensitivityClass
from tasks.contribution import CHANGESET_HASHTAG, TagChange, TagSuggestion
from tasks.maproulette import (
    ChallengeNotRegisteredError,
    ChallengeTask,
    HttpxMapRouletteTransport,
    MapRouletteClient,
    build_challenge,
)

# A non-secret placeholder for the fake key used in these socket-free tests. Bound to a
# name (not an inline literal) so the no-token-literal guard has nothing to flag (HG-09).
_FAKE_KEY = "unit-test-fake-key"


def _task() -> ChallengeTask:
    return ChallengeTask(
        suggestion=TagSuggestion(
            suggestion_id="sug:1",
            change=TagChange("node", 1, "operator", "OCPD"),
            instruction="Public records attribute this device to OCPD.",
            evidence_ref="evidence:1",
            source_id="okc-records",
            checkin_comment=f"operator=OCPD {CHANGESET_HASHTAG} #sig-okc",
        ),
        lat=35.46,
        lon=-97.51,
        sensitivity_class=SensitivityClass.C1,
    )


def _mock_client(captured: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = request.content.decode() if request.content else ""
        return httpx.Response(200, json={"id": 42, "status": "created"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_httpx_transport_sends_bearer_and_json_without_a_socket() -> None:
    captured: dict[str, object] = {}
    transport = HttpxMapRouletteTransport(client=_mock_client(captured))
    body = transport.post(
        "https://maproulette.org/api/v2/challenge", json={"name": "x"}, api_key=_FAKE_KEY
    )
    assert body == {"id": 42, "status": "created"}
    assert captured["method"] == "POST"
    assert captured["auth"] == f"Bearer {_FAKE_KEY}"  # key rides an Authorization header only
    assert '"name"' in str(captured["body"])


def test_live_push_posts_when_key_and_registered() -> None:
    captured: dict[str, object] = {}
    client = MapRouletteClient(
        api_key=_FAKE_KEY, transport=HttpxMapRouletteTransport(client=_mock_client(captured))
    )
    challenge = build_challenge(
        challenge_id="c1", name="SIG OKC", instruction="review each", jurisdiction="okc"
    )
    result = client.push(challenge=challenge, jurisdiction="okc", tasks=[_task()], registered=True)
    assert result["dry_run"] is False
    assert result["response"] == {"id": 42, "status": "created"}
    assert captured["method"] == "POST"
    assert captured["auth"] == f"Bearer {_FAKE_KEY}"


def test_live_push_still_refuses_while_unregistered() -> None:
    # Activation-ready does NOT bypass the registration gate: exit-3 refusal stands.
    client = MapRouletteClient(
        api_key=_FAKE_KEY, transport=HttpxMapRouletteTransport(client=_mock_client({}))
    )
    challenge = build_challenge(
        challenge_id="c1", name="SIG OKC", instruction="review each", jurisdiction="okc"
    )
    with pytest.raises(ChallengeNotRegisteredError):
        client.push(challenge=challenge, jurisdiction="okc", tasks=[_task()], registered=False)


def test_keyless_client_stays_dry_run_even_with_a_transport() -> None:
    # No key ⇒ dry-run, no network, regardless of a wired transport (HG-08 dormant).
    client = MapRouletteClient(
        api_key=None, transport=HttpxMapRouletteTransport(client=_mock_client({}))
    )
    challenge = build_challenge(
        challenge_id="c1", name="SIG OKC", instruction="review each", jurisdiction="okc"
    )
    result = client.push(challenge=challenge, jurisdiction="okc", tasks=[_task()], registered=True)
    assert result["dry_run"] is True
