# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The private intake-moderation surface (P32.16 / ADR-135, §55.5 SIG-FIND-006).

Mounted on the loopback curation app ONLY — authenticated + tier-gated like
every curation write (§34.1, §36.1). Deterministic acceptance:

* Queue + detail require a bearer token and the verify scope; deciding a
  disposition takes the curator scope (proposal/approval two-key separation).
* The queue shows pending reports in policy-priority order and survives
  "restarts" (it's a query over durable state, not a process buffer).
* Events are append-only with fail-closed transitions; an approval must name
  the live proposal; a reviewed report is never a claim/review_decision write.
* Redaction is irreversible on the payload and audited on the event log.
"""

from __future__ import annotations

from api.curation import create_curation_app
from api.intake import MemoryIntakeStore
from starlette.testclient import TestClient

_ANON = {"Authorization": "Bearer anon-demo-key"}
_REGISTERED = {"Authorization": "Bearer registered-demo-key"}
_REVIEWER = {"Authorization": "Bearer reviewer-demo-key"}
_CURATOR = {"Authorization": "Bearer curator-demo-key"}


def _client() -> tuple[TestClient, MemoryIntakeStore]:
    store = MemoryIntakeStore()
    app = create_curation_app(enabled=True, intake_store=store)
    return TestClient(app, raise_server_exceptions=True), store


def _seed_report(
    store: MemoryIntakeStore,
    *,
    key: str,
    category: str = "factual_error",
    description: str = "The retention-days value on this record is wrong.",
) -> str:
    receipt = f"rct-{key:<028}"[:36]
    store.insert_report(
        report_id=f"00000000-0000-4000-8000-{key[:12]:>012}",
        receipt_id=receipt,
        idempotency_key=f"nonce-{key}",
        category=category,
        description=description,
        publication_id=None,
        record_key=None,
        claim_ids=[],
        evidence_urls=[],
        contact=None,
        token_digest=b"\x00" * 32,
    )
    return receipt


# --------------------------------------------------------------------------- #
# Auth + mounting
# --------------------------------------------------------------------------- #
def test_routes_absent_without_store() -> None:
    client = TestClient(create_curation_app(enabled=True))
    assert client.get("/v1/curation/intake").status_code == 404
    assert client.get("/v1/curation/intake", headers=_REVIEWER).status_code == 404


def test_no_token_401() -> None:
    client, _ = _client()
    assert client.get("/v1/curation/intake").status_code == 401
    assert (
        client.post("/v1/curation/intake/rct-x/events", json={"event": "triaged"}).status_code
        == 401
    )


def test_low_tier_403() -> None:
    client, store = _client()
    _seed_report(store, key="aaa1")
    assert client.get("/v1/curation/intake", headers=_ANON).status_code == 403
    assert client.get("/v1/curation/intake", headers=_REGISTERED).status_code == 403


def test_queue_and_detail() -> None:
    client, store = _client()
    r1 = _seed_report(store, key="bbb1", category="factual_error")
    r2 = _seed_report(store, key="bbb2", category="privacy_harm")
    resp = client.get("/v1/curation/intake", headers=_REVIEWER)
    assert resp.status_code == 200
    rows = resp.json()["pending"]
    assert len(rows) == 2
    # Priority order: privacy_harm (priority 1) before factual_error (3).
    assert rows[0]["receipt_id"] == r2
    assert rows[0]["priority"] == 1
    assert rows[0]["sla_hours"] == 72
    assert rows[0]["state"] == "received"

    detail = client.get(f"/v1/curation/intake/{r1}", headers=_REVIEWER)
    assert detail.status_code == 200
    body = detail.json()
    assert body["description"].startswith("The retention-days")
    assert [e["event"] for e in body["events"]] == ["received"]
    assert body["lifecycle_event"] == "received"


def test_detail_unknown_404() -> None:
    client, _ = _client()
    assert client.get("/v1/curation/intake/rct-nope", headers=_REVIEWER).status_code == 404


# --------------------------------------------------------------------------- #
# Event appends — transitions, two-key approval, detail contract
# --------------------------------------------------------------------------- #
def test_happy_path_received_to_closed() -> None:
    client, store = _client()
    receipt = _seed_report(store, key="ccc1")

    def post(event: str, detail=None, headers=_REVIEWER):
        return client.post(
            f"/v1/curation/intake/{receipt}/events",
            json={"event": event, "detail": detail or {}},
            headers=headers,
        )

    # Approval with no live proposal fails on the transition (curator scope).
    assert (
        post(
            "disposition_approved",
            {"outcome": "refuse", "reason": "x", "approves_seq": 1},
            headers=_CURATOR,
        ).status_code
        == 409
    )
    assert post("triaged").status_code == 201
    assert post("assigned", {"assignee": "rev-7"}).status_code == 201
    assert post("review_requested", {"note": "needs the cited PDF"}).status_code == 201
    assert post("closed").status_code == 409  # undecided cannot close
    resp = post("disposition_proposed", {"outcome": "refuse", "reason": "not evidenced"})
    assert resp.status_code == 201
    seq = resp.json()["event_seq"]
    # The approval requires the curator scope, not just verify.
    assert (
        post(
            "disposition_approved",
            {"outcome": "refuse", "reason": "not evidenced", "approves_seq": seq},
            headers=_REVIEWER,
        ).status_code
        == 403
    )
    assert (
        post(
            "disposition_approved",
            {"outcome": "refuse", "reason": "not evidenced", "approves_seq": seq},
            headers=_CURATOR,
        ).status_code
        == 201
    )
    assert post("closed", headers=_REVIEWER).status_code == 201
    # Terminal: nothing follows closed.
    assert post("triaged").status_code == 409

    events = client.get(f"/v1/curation/intake/{receipt}", headers=_REVIEWER).json()["events"]
    assert [e["event"] for e in events] == [
        "received",
        "triaged",
        "assigned",
        "review_requested",
        "disposition_proposed",
        "disposition_approved",
        "closed",
    ]


def test_event_write_cannot_target_bridge_or_receiver_events() -> None:
    client, store = _client()
    receipt = _seed_report(store, key="ddd1")
    for event in ("received", "applied", "published", "expunged"):
        resp = client.post(
            f"/v1/curation/intake/{receipt}/events",
            json={"event": event, "detail": {}},
            headers=_CURATOR,
        )
        assert resp.status_code == 422


def test_event_detail_validation() -> None:
    client, store = _client()
    receipt = _seed_report(store, key="eee1")
    # A disposition without outcome+reason fails (SIG-GOV-004).
    resp = client.post(
        f"/v1/curation/intake/{receipt}/events",
        json={"event": "disposition_proposed", "detail": {"outcome": "refuse"}},
        headers=_REVIEWER,
    )
    assert resp.status_code == 422
    # Unknown detail keys refused.
    resp2 = client.post(
        f"/v1/curation/intake/{receipt}/events",
        json={"event": "triaged", "detail": {"raw_ip": "1.2.3.4"}},
        headers=_REVIEWER,
    )
    assert resp2.status_code == 422


def test_redaction_is_irreversible_and_audited() -> None:
    client, store = _client()
    receipt = _seed_report(store, key="fff1", description="sensitive narrative text")
    resp = client.post(
        f"/v1/curation/intake/{receipt}/events",
        json={"event": "redacted", "detail": {"fields": ["description"]}},
        headers=_REVIEWER,
    )
    assert resp.status_code == 201
    detail = client.get(f"/v1/curation/intake/{receipt}", headers=_REVIEWER).json()
    assert detail["description"] == "[redacted]"
    assert detail["events"][-1]["event"] == "redacted"
    # The lifecycle did not move — redaction is housekeeping, not a decision.
    assert detail["lifecycle_event"] == "received"


def test_queue_drops_decided_reports() -> None:
    client, store = _client()
    receipt = _seed_report(store, key="ggg1")
    client.post(
        f"/v1/curation/intake/{receipt}/events",
        json={"event": "disposition_proposed", "detail": {"outcome": "refuse", "reason": "dup"}},
        headers=_REVIEWER,
    )
    client.post(
        f"/v1/curation/intake/{receipt}/events",
        json={
            "event": "disposition_approved",
            "detail": {"outcome": "refuse", "reason": "dup", "approves_seq": 2},
        },
        headers=_CURATOR,
    )
    pending = client.get("/v1/curation/intake", headers=_REVIEWER).json()["pending"]
    assert pending == []
    history = client.get("/v1/curation/intake?all=true", headers=_REVIEWER).json()["pending"]
    assert len(history) == 1


def test_moderation_never_touches_canonical_state() -> None:
    """The moderation store interface carries no claim/review write methods —
    a reviewed report is not an applied correction (P32.16a owns that bridge)."""
    _, store = _client()
    assert not hasattr(store, "record_decision")
    assert not hasattr(store, "insert_claim")


def test_receiver_role_isolation_is_schema_level() -> None:
    """The PG-side proof lives in tests/db/test_intake_pg.py; here we pin the
    boundary object: the receiver protocol exposes no event-writing methods."""
    from db.intake import IntakeReceiverStore

    for forbidden in ("record_event", "redact", "queue", "detail"):
        assert not hasattr(IntakeReceiverStore, forbidden)
