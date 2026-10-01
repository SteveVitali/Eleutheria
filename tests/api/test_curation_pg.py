# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The PG-backed curation review queue (P31.10) — route contract without Docker.

The route-level behaviour that only exists when the queue is a
:class:`resolution.review_pg.PgReviewQueue`: only ``accept``/``reject`` reach the
append-only write path (``defer``/``unsure`` write NOTHING and the item stays
pending), the reviewer is the pseudonymous contributor handle from the tier
token, and the camera-site evidence view rides along on item GET. The real-SQL
halves (prefix/tier/bucket filtering, the sampler, campaign tables) are pinned
in ``tests/db/test_camera_site_review.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from api.curation import create_curation_app
from resolution.review_pg import PgReviewQueue
from resolution.review_queue import ReviewItem
from starlette.testclient import TestClient

_REVIEWER = {"Authorization": "Bearer reviewer-demo-key"}
_CURATOR = {"Authorization": "Bearer curator-demo-key"}


class _FakeConn:
    """A psycopg-shaped stub: every read returns empty."""

    def execute(self, *args: Any, **kwargs: Any) -> _FakeConn:
        return self

    def fetchall(self) -> list[Any]:
        return []

    def fetchone(self) -> None:
        return None


class _FakePgQueue(PgReviewQueue):
    """A PgReviewQueue with the SQL stubbed out — enough for route tests."""

    def __init__(self, items: list[ReviewItem]) -> None:
        super().__init__(conn=_FakeConn())
        self._items = {i.item_id: i for i in items}
        self.decide_calls: list[tuple[str, str, str, str | None]] = []

    def get(self, item_id: str) -> ReviewItem | None:
        return self._items.get(item_id)

    def decisions(self, item_id: str | None = None):  # type: ignore[override]
        return ()

    def decide(self, item_id, decision, *, reviewer, rationale=None):  # type: ignore[override]
        if decision not in {"accept", "reject"}:
            raise ValueError(f"decision must be one of ['accept', 'reject'], got {decision!r}")
        if not reviewer:
            raise ValueError("a review decision MUST record the human reviewer")
        if item_id not in self._items:
            raise ValueError(f"no such review item {item_id!r}")
        self.decide_calls.append((item_id, decision, reviewer, rationale))
        from resolution.review_queue import ReviewDecision

        return ReviewDecision(item_id=item_id, decision=decision, reviewer=reviewer, decided_at="t")


def _pg_client() -> tuple[TestClient, _FakePgQueue]:
    queue = _FakePgQueue(
        [
            ReviewItem(
                item_id="er_match:camera_site:a:b",
                kind="er_match",
                summary="Same camera? x vs y, 21.5 m apart (4g:proximate_unique)",
                payload={
                    "left": "a",
                    "right": "b",
                    "tier": 4,
                    "tier_label": "4g:proximate_unique",
                    "reason": "tier_not_auto_write",
                    "evidence": {"distance_m": 21.5, "soft_conflicts": []},
                },
            ),
            ReviewItem(
                item_id="er_match:identity_duplicate:g:h",
                kind="er_match",
                summary="identity duplicate",
            ),
        ]
    )
    return TestClient(create_curation_app(review_queue=queue, enabled=True)), queue


def test_pg_decide_writes_accept_with_the_pseudonymous_curator() -> None:
    client, queue = _pg_client()
    resp = client.post(
        "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
        data={"decision": "match", "reason": "same pole"},
        headers=_CURATOR,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["review_decision"] == "accept"
    # The reviewer on the record is the tier-token handle, never a person.
    assert queue.decide_calls == [("er_match:camera_site:a:b", "accept", "curator-1", "same pole")]


def test_pg_decide_no_match_maps_to_reject() -> None:
    client, queue = _pg_client()
    resp = client.post(
        "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
        json={"decision": "no-match"},
        headers=_CURATOR,
    )
    assert resp.status_code == 200
    assert queue.decide_calls[0][1] == "reject"


def test_pg_defer_writes_nothing_and_stays_pending() -> None:
    client, queue = _pg_client()
    resp = client.post(
        "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
        data={"decision": "defer", "reason": "not sure"},
        headers=_CURATOR,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deferred"] is True and body["review_decision"] is None
    assert queue.decide_calls == []  # no review_decision — the item stays pending


def test_pg_decide_rejects_unknown_decisions() -> None:
    client, queue = _pg_client()
    resp = client.post(
        "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
        data={"decision": "approve"},
        headers=_CURATOR,
    )
    assert resp.status_code == 400
    assert queue.decide_calls == []


def test_pg_item_view_carries_the_camera_site_evidence() -> None:
    client, _queue = _pg_client()
    resp = client.get("/v1/curation/review-queue/er_match:camera_site:a:b", headers=_CURATOR)
    assert resp.status_code == 200
    body = resp.json()
    ev = body["evidence"]
    assert ev["distance_m"] == 21.5 and ev["tier_label"] == "4g:proximate_unique"
    assert ev["stratum"] == "4g"
    # Observations resolve through the (stubbed) spine read — None here, but the
    # keys exist; real claim reads are pinned in tests/db.
    assert "left_observation" in ev and "right_observation" in ev


def test_pg_list_filters_family_and_reports_stratum() -> None:
    client, _queue = _pg_client()
    import resolution.camera_site_review as csr

    captured: dict[str, Any] = {}

    def _pending(conn, *, prefixes=None, tier=None, bucket=None, campaign=None, limit=None):
        captured.update(prefixes=prefixes, tier=tier, bucket=bucket, campaign=campaign, limit=limit)
        return ()

    orig = csr.pending_items
    csr.pending_items = _pending  # the route imports it lazily per call
    try:
        resp = client.get(
            "/v1/curation/review-queue?family=camera-site&tier=4&bucket=soft-conflict",
            headers=_CURATOR,
        )
        assert resp.status_code == 200
        assert captured["prefixes"] == (
            "er_match:camera_site:",
            "er_match:camera_site_disputed:",
        )
        assert captured["tier"] == 4 and captured["bucket"] == "soft-conflict"

        resp = client.get("/v1/curation/review-queue?family=bogus", headers=_CURATOR)
        assert resp.status_code == 400

        resp = client.get("/v1/curation/review-queue?family=all", headers=_CURATOR)
        assert resp.status_code == 200
        assert captured["prefixes"] is None  # family=all lifts the camera-site filter
    finally:
        csr.pending_items = orig


def test_pg_decide_requires_authentication_and_scope() -> None:
    client, _queue = _pg_client()
    assert (
        client.post(
            "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
            data={"decision": "match"},
        ).status_code
        == 401
    )
    # A registered contributor lacks verify_submissions → 403.
    assert (
        client.post(
            "/v1/curation/review-queue/er_match:camera_site:a:b/decide",
            data={"decision": "match"},
            headers={"Authorization": "Bearer registered-demo-key"},
        ).status_code
        == 403
    )


def test_coordinates_reduce_to_the_curator_tier() -> None:
    """§19.4 reduction keyed on the contributor tier: reviewer→2dp, curator→full."""
    client, _queue = _pg_client()
    import resolution.camera_site_review as csr

    obs = {
        "subject_id": "a",
        "source_id": "dot_511_zz",
        "latitude": 35.4676234,
        "longitude": -97.5164276,
        "external_ref": "101",
        "operator": "Zed DOT",
        "name": "I-35 @ Main",
        "roadway": None,
        "direction": None,
        "jurisdiction": "US-OK",
        "camera_type": "traffic",
        "claim_ids": [],
    }

    def _pair(conn, item):
        return {
            "left_subject": "a",
            "right_subject": "b",
            "stratum": "4g",
            "tier": 4,
            "distance_m": 21.5,
            "left_observation": dict(obs),
            "right_observation": dict(obs, subject_id="b"),
        }

    orig = csr.pair_evidence
    csr.pair_evidence = _pair  # imported lazily inside _camera_evidence
    try:
        curator = client.get(
            "/v1/curation/review-queue/er_match:camera_site:a:b", headers=_CURATOR
        ).json()["evidence"]
        reviewer = client.get(
            "/v1/curation/review-queue/er_match:camera_site:a:b", headers=_REVIEWER
        ).json()["evidence"]
    finally:
        csr.pair_evidence = orig
    # curator tier → geo tier 0 (full precision; the claims are public tier-0).
    assert curator["coordinate_tier"] == 0
    assert curator["left_observation"]["latitude"] == pytest.approx(35.4676234)
    # trusted_reviewer → geo tier 1 (the published 2-dp truncation, ~1 km).
    assert reviewer["coordinate_tier"] == 1
    assert reviewer["left_observation"]["latitude"] == pytest.approx(35.46)
    assert reviewer["left_observation"]["longitude"] == pytest.approx(-97.51)


def test_demo_queue_path_is_unchanged() -> None:
    """No DSN → the in-memory queue + CurationLog semantics stay exactly as P21.6."""
    from api.curation import CurationLog
    from resolution.review_queue import ReviewQueue

    log = CurationLog()
    queue = ReviewQueue()
    queue.enqueue(ReviewItem(item_id="er_match:a~b", kind="er_match", summary="tier 5: a ~ b"))
    client = TestClient(create_curation_app(review_queue=queue, curation_log=log, enabled=True))
    resp = client.post(
        "/v1/curation/review-queue/er_match:a~b/decide",
        data={"decision": "defer"},
        headers=_CURATOR,
    )
    assert resp.status_code == 200
    # The demo path still records a deferred CurationLog row (unchanged).
    assert log.records(action="review_decision", target_id="er_match:a~b")


def test_html_queue_and_item_pages_render_without_js() -> None:
    """The loopback surface is plain HTML + POST forms — zero client script."""
    client, _queue = _pg_client()
    import resolution.camera_site_review as csr

    orig = csr.pending_items
    csr.pending_items = lambda conn, **kw: ()  # type: ignore[attr-defined]
    try:
        list_resp = client.get(
            "/v1/curation/review-queue",
            headers={**_CURATOR, "Accept": "text/html"},
        )
    finally:
        csr.pending_items = orig
    assert list_resp.status_code == 200 and "<script" not in list_resp.text
    item_resp = client.get(
        "/v1/curation/review-queue/er_match:camera_site:a:b",
        headers={**_CURATOR, "Accept": "text/html"},
    )
    assert item_resp.status_code == 200
    assert "<script" not in item_resp.text
    assert "decision" in item_resp.text and "defer" in item_resp.text
