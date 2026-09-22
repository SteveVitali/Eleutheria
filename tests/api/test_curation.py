# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The authenticated curation service (P21.6, §34, ADR-068).

These are the deterministic acceptance criteria for the curation surface:

* **Disabled by default (RISK-P21-10).** Without ``SIG_CURATION_ENABLED=1`` the
  ``/v1/curation/*`` routes are *absent* (404), and the public read API never
  carries them (Part VIII §0.7).
* **Authenticated + tier-gated (§36.1, §34.1).** No token → 401; a token whose
  contributor tier lacks the write scope → 403.
* **Append-only, human-attributed (P1-P3, §3.1).** A decide writes exactly one row;
  repeating it appends another (a history), never a mutation. No decision is
  writable without a human actor id — enumerated across every write path.
* **Anti-poisoning + machine-suggestions-never-auto-apply (§34.4, SIG-LLM-001/002).**
"""

from __future__ import annotations

import pytest
from api.app import create_app
from api.curation import (
    CURATION_KEYS,
    CurationLog,
    build_curation_router,
    create_curation_app,
)
from api.demo import build_demo_store
from resolution.review_queue import ConfidenceFactor, ReviewItem, ReviewQueue
from starlette.routing import Route
from starlette.testclient import TestClient

# Bearer headers per contributor tier (the demo token registry).
_ANON = {"Authorization": "Bearer anon-demo-key"}
_REGISTERED = {"Authorization": "Bearer registered-demo-key"}
_REVIEWER = {"Authorization": "Bearer reviewer-demo-key"}
_CURATOR = {"Authorization": "Bearer curator-demo-key"}


def _queue() -> ReviewQueue:
    q = ReviewQueue()
    q.enqueue(
        ReviewItem(
            item_id="er_match:a~b",
            kind="er_match",
            summary="tier 5: a ~ b (weight +9.00)",
            confidence=(ConfidenceFactor(name="name", weight=9.0, detail="exact"),),
            overall_weight=9.0,
            payload={"left": {"label": "A"}, "right": {"label": "B"}},
        )
    )
    q.enqueue(
        ReviewItem(
            item_id="er_match:c~d",
            kind="er_match",
            summary="tier 4: c ~ d (weight +3.00)",
            overall_weight=3.0,
            payload={"left": {"label": "C"}, "right": {"label": "D"}},
        )
    )
    # A model-assisted proposal carrying a labelled machine suggestion (SIG-LLM-001).
    q.enqueue(
        ReviewItem(
            item_id="model_extraction:m:1:2",
            kind="model_extraction",
            summary="x operates_alpr 'Flock' [R6/PROPOSED]",
            model_id="gpt-x",
            prompt_version="p1",
            payload={"suggested_decision": "match", "confidence_class": "low"},
        )
    )
    return q


@pytest.fixture
def enabled_client() -> TestClient:
    app = create_curation_app(review_queue=_queue(), curation_log=CurationLog(), enabled=True)
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def disabled_client() -> TestClient:
    app = create_curation_app(enabled=False)
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Disabled-by-default (RISK-P21-10)                                            #
# --------------------------------------------------------------------------- #
def test_routes_absent_when_disabled(disabled_client: TestClient) -> None:
    for method, path in [
        ("get", "/v1/curation/review-queue"),
        ("post", "/v1/curation/review-queue/er_match:a~b/decide"),
        ("post", "/v1/curation/contradiction/x/disposition"),
        ("post", "/v1/curation/task/t/disposition"),
        ("post", "/v1/curation/submission"),
        ("post", "/v1/curation/revert"),
    ]:
        resp = getattr(disabled_client, method)(path, headers=_CURATOR)
        assert resp.status_code == 404, f"{method} {path} should be absent when disabled"


def test_env_gating_default_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIG_CURATION_ENABLED", raising=False)
    app = create_curation_app()  # no explicit enabled -> reads env (unset)
    client = TestClient(app)
    assert client.get("/v1/curation/review-queue", headers=_CURATOR).status_code == 404
    assert client.get("/").json()["enabled"] is False


def test_public_read_api_never_carries_curation_routes() -> None:
    app = create_app(build_demo_store())
    paths = [r.path for r in app.routes if isinstance(r, Route)]
    assert not any("curation" in p for p in paths), "curation must never be on the public API"


# --------------------------------------------------------------------------- #
# Authentication + tier enforcement (§36.1, §34.1)                             #
# --------------------------------------------------------------------------- #
def test_unauthenticated_is_401(enabled_client: TestClient) -> None:
    assert enabled_client.get("/v1/curation/review-queue").status_code == 401
    assert (
        enabled_client.post(
            "/v1/curation/review-queue/er_match:a~b/decide", data={"decision": "match"}
        ).status_code
        == 401
    )
    # A malformed / unknown token is also 401.
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert enabled_client.get("/v1/curation/review-queue", headers=bad).status_code == 401


def test_tier_insufficient_is_403(enabled_client: TestClient) -> None:
    # Reviewing the ER queue needs trusted_reviewer+; a registered contributor is 403.
    assert enabled_client.get("/v1/curation/review-queue", headers=_REGISTERED).status_code == 403
    assert (
        enabled_client.post(
            "/v1/curation/review-queue/er_match:a~b/decide",
            data={"decision": "match"},
            headers=_REGISTERED,
        ).status_code
        == 403
    )
    # A contradiction disposition needs curator (resolution override); a reviewer is 403.
    assert (
        enabled_client.post(
            "/v1/curation/contradiction/x/disposition",
            data={"disposition": "resolved", "reason": "r"},
            headers=_REVIEWER,
        ).status_code
        == 403
    )
    # Anonymous may submit (queue_submission) but may NOT decide.
    assert (
        enabled_client.post(
            "/v1/curation/review-queue/er_match:a~b/decide",
            data={"decision": "match"},
            headers=_ANON,
        ).status_code
        == 403
    )


def test_reviewer_can_list_queue_ordered_by_impact(enabled_client: TestClient) -> None:
    resp = enabled_client.get("/v1/curation/review-queue", headers=_REVIEWER)
    assert resp.status_code == 200
    rows = resp.json()["pending"]
    # RISK-P21-11: highest |weight| first (a~b weight 9 before c~d weight 3).
    ids = [r["item_id"] for r in rows]
    assert ids.index("er_match:a~b") < ids.index("er_match:c~d")


# --------------------------------------------------------------------------- #
# Append-only, one-row-per-decide, never mutates (P1-P3)                       #
# --------------------------------------------------------------------------- #
def test_decide_writes_exactly_one_row_and_repeats_append(enabled_client: TestClient) -> None:
    app = enabled_client.app
    log: CurationLog = app.state.curation_log  # type: ignore[attr-defined]
    assert len(log.records(action="review_decision")) == 0

    r1 = enabled_client.post(
        "/v1/curation/review-queue/er_match:a~b/decide",
        data={"decision": "match", "reason": "clear match"},
        headers=_REVIEWER,
    )
    assert r1.status_code == 200
    rows = log.records(action="review_decision", target_id="er_match:a~b")
    assert len(rows) == 1
    assert rows[0].actor == "reviewer-1"
    assert rows[0].payload["decision"] == "match"

    # Repeat: a SECOND row is appended (append-only history), the first is unchanged.
    first_at = rows[0].at
    r2 = enabled_client.post(
        "/v1/curation/review-queue/er_match:a~b/decide",
        data={"decision": "no-match", "reason": "changed my mind"},
        headers=_REVIEWER,
    )
    assert r2.status_code == 200
    rows2 = log.records(action="review_decision", target_id="er_match:a~b")
    assert len(rows2) == 2
    assert rows2[0].at == first_at  # the original row is never mutated
    assert rows2[0].payload["decision"] == "match"
    assert rows2[1].payload["decision"] == "no-match"


def test_decided_item_drops_out_of_pending_compute_on_read(enabled_client: TestClient) -> None:
    before = enabled_client.get("/v1/curation/review-queue", headers=_REVIEWER).json()["count"]
    enabled_client.post(
        "/v1/curation/review-queue/er_match:a~b/decide",
        data={"decision": "match", "reason": "ok"},
        headers=_REVIEWER,
    )
    after = enabled_client.get("/v1/curation/review-queue", headers=_REVIEWER).json()
    assert after["count"] == before - 1
    assert "er_match:a~b" not in [r["item_id"] for r in after["pending"]]


def test_bad_decision_value_is_400(enabled_client: TestClient) -> None:
    resp = enabled_client.post(
        "/v1/curation/review-queue/er_match:a~b/decide",
        data={"decision": "delete"},
        headers=_REVIEWER,
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# No decision writable without a human actor id — enumerate every write path   #
# --------------------------------------------------------------------------- #
def test_curation_log_refuses_empty_actor() -> None:
    log = CurationLog()
    with pytest.raises(ValueError, match="human actor id"):
        log.append("review_decision", "er_match:a~b", actor="", payload={"decision": "match"})
    assert len(log.records()) == 0


def test_every_write_route_requires_auth_so_carries_an_actor(enabled_client: TestClient) -> None:
    """Enumerate every POST (write) route: with NO token each is 401, so no write
    path can ever create a row without an authenticated human actor id (§3.1)."""
    write_routes = [
        ("/v1/curation/review-queue/er_match:a~b/decide", {"decision": "match"}),
        ("/v1/curation/contradiction/x/disposition", {"disposition": "resolved", "reason": "r"}),
        (
            "/v1/curation/task/t/disposition",
            {"disposition": "resolved_evidence_found", "reason": "r"},
        ),
        ("/v1/curation/submission", {"kind": "report", "evidence_url": "https://e"}),
        ("/v1/curation/revert", {"contribution_id": "c", "reason": "r"}),
    ]
    log: CurationLog = enabled_client.app.state.curation_log  # type: ignore[attr-defined]
    for path, data in write_routes:
        assert enabled_client.post(path, data=data).status_code == 401  # no token
    assert len(log.records()) == 0  # nothing was written by any unauthenticated call


def test_all_router_post_paths_are_covered_by_the_enumeration() -> None:
    """Guard: if a future write route is added, the enumeration above must grow."""
    router = build_curation_router()
    post_paths = {
        r.path for r in router.routes if isinstance(r, Route) and r.methods and "POST" in r.methods
    }
    assert post_paths == {
        "/v1/curation/review-queue/{item_id}/decide",
        "/v1/curation/contradiction/{contradiction_id}/disposition",
        "/v1/curation/task/{task_id}/disposition",
        "/v1/curation/submission",
        "/v1/curation/revert",
    }


# --------------------------------------------------------------------------- #
# Machine suggestions are labelled and NEVER auto-apply (SIG-LLM-001/002)      #
# --------------------------------------------------------------------------- #
def test_model_suggestion_is_labelled_and_not_applied(enabled_client: TestClient) -> None:
    resp = enabled_client.get("/v1/curation/review-queue/model_extraction:m:1:2", headers=_REVIEWER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggestion"]["suggested_decision"] == "match"
    assert body["suggestion"]["auto_applied"] is False
    assert body["suggestion"]["model_id"] == "gpt-x"
    # No decision exists until a human decides.
    assert body["history"] == []
    log: CurationLog = enabled_client.app.state.curation_log  # type: ignore[attr-defined]
    assert len(log.records(action="review_decision")) == 0


def test_deciding_a_model_item_logs_model_provenance(enabled_client: TestClient) -> None:
    enabled_client.post(
        "/v1/curation/review-queue/model_extraction:m:1:2/decide",
        data={"decision": "match", "reason": "verified"},
        headers=_REVIEWER,
    )
    log: CurationLog = enabled_client.app.state.curation_log  # type: ignore[attr-defined]
    row = log.records(action="review_decision", target_id="model_extraction:m:1:2")[0]
    assert row.payload["model_id"] == "gpt-x"
    assert row.payload["prompt_version"] == "p1"
    assert row.actor == "reviewer-1"


# --------------------------------------------------------------------------- #
# L0 submission + anti-poisoning (§34.1-34.4)                                  #
# --------------------------------------------------------------------------- #
def test_submission_refuses_without_evidence(enabled_client: TestClient) -> None:
    resp = enabled_client.post(
        "/v1/curation/submission", data={"kind": "report", "claim": "x"}, headers=_ANON
    )
    assert resp.status_code == 422


def test_submission_routes_device_observation_to_osm(enabled_client: TestClient) -> None:
    resp = enabled_client.post(
        "/v1/curation/submission",
        data={"kind": "device_observation", "evidence_url": "https://e"},
        headers=_ANON,
    )
    assert resp.status_code == 422
    assert "OSM" in str(resp.json()["detail"])


def test_submission_lands_l0_append_only(enabled_client: TestClient) -> None:
    resp = enabled_client.post(
        "/v1/curation/submission",
        data={
            "kind": "report",
            "evidence_url": "https://e/doc",
            "claim": "c",
            "as_of": "2026-07-01",
        },
        headers=_ANON,
    )
    assert resp.status_code == 200
    rec = resp.json()["recorded"]
    assert rec["payload"]["entry_level"] == "L0"
    assert rec["payload"]["produces_l1_claim"] is False
    assert rec["actor"] == "anon-1"


# --------------------------------------------------------------------------- #
# Dispositions + revert carry a reason (§3.1, SIG-CONTRIB-009)                 #
# --------------------------------------------------------------------------- #
def test_contradiction_disposition_requires_reason(enabled_client: TestClient) -> None:
    assert (
        enabled_client.post(
            "/v1/curation/contradiction/x/disposition",
            data={"disposition": "resolved"},
            headers=_CURATOR,
        ).status_code
        == 400
    )
    ok = enabled_client.post(
        "/v1/curation/contradiction/x/disposition",
        data={"disposition": "resolved", "reason": "portal stale"},
        headers=_CURATOR,
    )
    assert ok.status_code == 200


def test_task_no_evidence_disposition_requires_sources(enabled_client: TestClient) -> None:
    assert (
        enabled_client.post(
            "/v1/curation/task/t/disposition",
            data={"disposition": "resolved_no_evidence_exists", "reason": "searched"},
            headers=_REGISTERED,
        ).status_code
        == 400
    )
    ok = enabled_client.post(
        "/v1/curation/task/t/disposition",
        data={
            "disposition": "resolved_no_evidence_exists",
            "reason": "searched",
            "sources_searched": "portal, records",
        },
        headers=_REGISTERED,
    )
    assert ok.status_code == 200
    assert ok.json()["recorded"]["payload"]["sources_searched"] == ["portal", "records"]


def test_revert_requires_reason_and_is_a_new_assertion(enabled_client: TestClient) -> None:
    assert (
        enabled_client.post(
            "/v1/curation/revert", data={"contribution_id": "c"}, headers=_CURATOR
        ).status_code
        == 400
    )
    ok = enabled_client.post(
        "/v1/curation/revert",
        data={"contribution_id": "c", "reason": "vandalism"},
        headers=_CURATOR,
    )
    assert ok.status_code == 200
    assert ok.json()["recorded"]["payload"]["kind"] == "new_assertion_not_deletion"


def test_no_real_name_field_in_token_registry() -> None:
    """Part VIII §0.7 / SIG-CONTRIB-006: contributors are pseudonymous only."""
    for contributor in CURATION_KEYS.values():
        assert not hasattr(contributor, "real_name")
        assert not hasattr(contributor, "legal_name")
        assert contributor.handle  # a pseudonymous handle, never a legal name
