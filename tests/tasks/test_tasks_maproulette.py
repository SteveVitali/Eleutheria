# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""MapRoulette cooperative-challenge client (P21.7, §35.2; ADR-069).

Covers the ticket ACs: payloads match MapRoulette API v2 shapes; a sensitive-tier
coordinate is EXCLUDED from the push payload (RISK-P21-12); ``push`` REFUSES while
the OE activity is not registered (SIG-CONTRIB-016d); dry-run without the key.
"""

from __future__ import annotations

import pytest
from policy.sensitivity import SensitivityClass
from tasks.contribution import CHANGESET_HASHTAG, TagChange, TagSuggestion
from tasks.maproulette import (
    ChallengeNotRegisteredError,
    ChallengeTask,
    MapRouletteClient,
    build_challenge,
    build_challenge_payload,
    jurisdiction_hashtag,
)


def _suggestion(sid: str, node_id: int) -> TagSuggestion:
    return TagSuggestion(
        suggestion_id=sid,
        change=TagChange("node", node_id, "operator", "Oklahoma City Police Department"),
        instruction="Public records attribute this device to OCPD; suggest operator=OCPD.",
        evidence_ref=f"evidence:{sid}",
        source_id="okc-records",
        checkin_comment=f"operator=OCPD {CHANGESET_HASHTAG} #sig-okc",
    )


def _task(sid: str, node_id: int, cls: SensitivityClass) -> ChallengeTask:
    return ChallengeTask(
        suggestion=_suggestion(sid, node_id), lat=35.46, lon=-97.51, sensitivity_class=cls
    )


def _challenge():
    return build_challenge(
        challenge_id="sig-okc",
        name="SIG operator attribution — OKC",
        instruction="Review each operator=* suggestion and apply in your own account.",
        jurisdiction="okc",
    )


def test_jurisdiction_hashtag_is_sig_prefixed() -> None:
    assert jurisdiction_hashtag("OKC") == "#sig-okc"
    assert jurisdiction_hashtag("New York") == "#sig-new-york"
    with pytest.raises(ValueError):
        jurisdiction_hashtag("   ")


def test_challenge_checkin_comment_carries_both_hashtags() -> None:
    # The changeset hashtag (the §7 metric reads it) AND the jurisdiction hashtag.
    ch = _challenge()
    assert CHANGESET_HASHTAG in ch.checkin_comment
    assert "#sig-okc" in ch.checkin_comment


def test_payload_matches_maproulette_v2_cooperative_shape() -> None:
    payload = build_challenge_payload(
        challenge=_challenge(),
        jurisdiction="okc",
        tasks=[_task("s1", 111, SensitivityClass.C1)],
    )
    assert payload["cooperativeType"] == "tags"
    assert payload["checkinSource"] == "SIG"
    assert CHANGESET_HASHTAG in payload["checkinComment"]
    assert payload["hashtag"] == "#sig-okc"
    (feature,) = payload["tasks"]
    assert feature["cooperativeType"] == "tags"
    assert feature["operations"][0]["operationType"] == "modifyElement"
    assert feature["operations"][0]["set"] == {"operator": "Oklahoma City Police Department"}
    assert feature["geometry"] == {"type": "Point", "coordinates": [-97.51, 35.46]}


def test_sensitive_tier_task_is_excluded_from_push_payload() -> None:
    # RISK-P21-12 / §43.3 / Part VIII §0.7: a C4 (confidential facility) coordinate
    # never leaves SIG in a challenge — it is dropped, contributing only a count.
    tasks = [
        _task("public", 111, SensitivityClass.C1),
        _task("reduced", 222, SensitivityClass.C2),
        _task("candidate", 333, SensitivityClass.C3),
        _task("confidential", 444, SensitivityClass.C4),
        _task("mobile", 555, SensitivityClass.C5),
    ]
    payload = build_challenge_payload(challenge=_challenge(), jurisdiction="okc", tasks=tasks)
    # C1 + C2 publish geometry; C3/C4/C5 (geo_tier 3) do not.
    assert len(payload["tasks"]) == 2
    assert payload["excluded_sensitive_task_count"] == 3
    ids = {f["evidence_ref"] for f in payload["tasks"]}
    assert ids == {"evidence:public", "evidence:reduced"}


def test_is_pushable_flag() -> None:
    assert _task("a", 1, SensitivityClass.C1).is_pushable is True
    assert _task("b", 2, SensitivityClass.C2).is_pushable is True
    assert _task("c", 3, SensitivityClass.C3).is_pushable is False
    assert _task("d", 4, SensitivityClass.C4).is_pushable is False
    assert _task("e", 5, SensitivityClass.C5).is_pushable is False


def test_push_refused_while_unregistered() -> None:
    # SIG-CONTRIB-016d / RISK-P16-14: no push before the OE activity is registered.
    client = MapRouletteClient(api_key=None)
    with pytest.raises(ChallengeNotRegisteredError):
        client.push(
            challenge=_challenge(),
            jurisdiction="okc",
            tasks=[_task("s1", 111, SensitivityClass.C1)],
            registered=False,
        )


def test_push_dry_run_when_registered_but_keyless() -> None:
    client = MapRouletteClient(api_key=None)
    assert client.dry_run is True
    result = client.push(
        challenge=_challenge(),
        jurisdiction="okc",
        tasks=[_task("s1", 111, SensitivityClass.C1)],
        registered=True,
    )
    assert result["dry_run"] is True
    assert result["endpoint"].endswith("/challenge")
    assert result["payload"]["cooperativeType"] == "tags"


def test_pull_dry_run_without_key() -> None:
    client = MapRouletteClient(api_key=None)
    result = client.pull(challenge_id="999")
    assert result["dry_run"] is True
    assert result["challenge_id"] == "999"
    assert "/challenge/999/" in result["endpoint"]


class _FakeTransport:
    """Records the live request without opening a socket (HG-08 branch coverage)."""

    def __init__(self) -> None:
        self.posted: dict[str, object] = {}
        self.got: dict[str, object] = {}

    def post(self, url: str, *, json: dict, api_key: str) -> dict:  # noqa: A002
        self.posted = {"url": url, "json": json, "api_key": api_key}
        return {"id": 4242, "status": "created"}

    def get(self, url: str, *, api_key: str) -> dict:
        self.got = {"url": url, "api_key": api_key}
        return {"tasks": []}


_FAKE_KEY = "fake-test-value"  # not a real credential (test double)


def test_live_push_uses_transport_and_key() -> None:
    transport = _FakeTransport()
    client = MapRouletteClient(api_key=_FAKE_KEY, transport=transport)
    assert client.dry_run is False
    result = client.push(
        challenge=_challenge(),
        jurisdiction="okc",
        tasks=[_task("s1", 111, SensitivityClass.C1)],
        registered=True,
    )
    assert result["dry_run"] is False
    assert result["response"] == {"id": 4242, "status": "created"}
    assert transport.posted["api_key"] == _FAKE_KEY
    assert transport.posted["url"].endswith("/challenge")


def test_live_push_without_transport_refuses_rather_than_faking() -> None:
    from tasks.maproulette import MapRouletteError

    client = MapRouletteClient(api_key=_FAKE_KEY, transport=None)
    with pytest.raises(MapRouletteError):
        client.push(
            challenge=_challenge(),
            jurisdiction="okc",
            tasks=[_task("s1", 111, SensitivityClass.C1)],
            registered=True,
        )


def test_from_env_reads_key() -> None:
    assert MapRouletteClient.from_env({}).dry_run is True
    assert MapRouletteClient.from_env({"SIG_MAPROULETTE_API_KEY": "k"}).dry_run is False
