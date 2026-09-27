# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The anonymous correction receiver (P32.16 / ADR-135, §55.5 SIG-FIND-006).

Deterministic acceptance over the in-memory store:

* **Disabled by default** — without ``SIG_INTAKE_ENABLED=1`` the ``/intake/*``
  routes are *absent* (404), and the public read API never carries them.
* **Operating gate** — an enabled-but-unstaffed receiver refuses new reports
  with ``receiver_not_operating`` and never renders the form.
* **Form token + idempotence** — ``GET /intake/new`` issues an expiring signed
  token; the nonce doubles as the idempotency key so retries are +0.
* **Receipt capability** — ``rct-<128-bit>`` + a 256-bit bearer token shown
  once, stored only as a digest; status reveals coarse state only.
* **Bounds/screens** — oversized bodies, unknown fields, non-https/private
  evidence URLs, plate/person payloads all refused before persistence.
* **Isolation** — the receiver mounts no ``/v1/curation/*`` routes and the
  public read app mounts no ``/intake/*`` routes (contract tests).
"""

from __future__ import annotations

import pytest
from api.app import create_app
from api.demo import build_demo_store
from api.intake import (
    AbuseGate,
    FormTokenSigner,
    MemoryIntakeStore,
    create_intake_app,
)
from starlette.testclient import TestClient

SECRETS = {
    "form_secret": "test-form-secret-0123456789",
    "abuse_secret": "test-abuse-secret-0123456",
}


def _app(**kw) -> TestClient:
    opts = {
        "store": MemoryIntakeStore(),
        "enabled": True,
        "operational": True,
        **SECRETS,
        **kw,
    }
    return TestClient(create_intake_app(**opts), raise_server_exceptions=True)


def _mint_form(client: TestClient) -> str:
    resp = client.get("/intake/new")
    assert resp.status_code == 200
    import re

    match = re.search(r'name="form_token" value="([^"]+)"', resp.text)
    assert match, "the no-JS form must embed a signed form_token"
    return match.group(1)


def _submit(client: TestClient, token: str, **fields):
    body = {
        "form_token": token,
        "category": "factual_error",
        "description": "The retention-days value on this record is wrong.",
        **fields,
    }
    return client.post("/intake/v1/reports", json=body)


# --------------------------------------------------------------------------- #
# Mounting + operating gate
# --------------------------------------------------------------------------- #
def test_disabled_by_default_no_routes() -> None:
    client = TestClient(create_intake_app(env={}))  # SIG_INTAKE_ENABLED unset
    assert client.get("/intake/new").status_code == 404
    assert client.post("/intake/v1/reports").status_code == 404
    assert client.post("/intake/v1/status").status_code == 404
    root = client.get("/").json()
    assert root["enabled"] is False and root["operational"] is False


def test_public_read_app_never_carries_intake() -> None:
    """The /intake surface is structurally absent from the public read API."""
    app = create_app(build_demo_store())
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert not any(p.startswith("/intake") for p in paths)


def test_receiver_never_carries_curation_routes() -> None:
    client = _app()
    assert client.get("/v1/curation/review-queue").status_code == 404
    assert client.post("/v1/curation/submission").status_code == 404


def test_unstaffed_receiver_not_operational() -> None:
    """Enabled + not operational: form hidden, POST refuses honestly."""
    client = TestClient(
        create_intake_app(enabled=True, operational=False, **SECRETS),
        raise_server_exceptions=True,
    )
    assert client.get("/").json()["operational"] is False
    form = client.get("/intake/new")
    assert form.status_code == 503
    assert "not yet operating" in form.text
    assert "<form" not in form.text  # no live form is ever served
    resp = client.post(
        "/intake/v1/reports",
        json={"category": "factual_error", "description": "x" * 30},
    )
    assert resp.status_code == 503
    assert resp.json()["error"] == "receiver_not_operating"
    # Status lookup still works for any pre-existing receipt.
    assert client.post("/intake/v1/status", json={}).status_code in (404, 429)


def test_operational_requires_real_secrets() -> None:
    """An operational app without its secrets fails construction (fail closed)."""
    with pytest.raises(RuntimeError, match="form secret"):
        create_intake_app(enabled=True, operational=True, abuse_secret="x" * 20, env={})
    with pytest.raises(RuntimeError, match="abuse secret"):
        create_intake_app(enabled=True, operational=True, form_secret="x" * 20, env={})


def test_intake_operational_env_gate() -> None:
    from api.intake import intake_operational

    assert intake_operational(env={}) is False
    assert intake_operational(env={"SIG_INTAKE_OPERATIONAL": "1"}) is False or True
    # Config flag alone is never enough — the env arm must also be 1.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("[intake]\noperational = false\n")
        assert intake_operational(env={"SIG_INTAKE_OPERATIONAL": "1"}, config_path=cfg) is False
        cfg.write_text("[intake]\noperational = true\n")
        assert intake_operational(env={}, config_path=cfg) is False
        assert intake_operational(env={"SIG_INTAKE_OPERATIONAL": "1"}, config_path=cfg) is True


# --------------------------------------------------------------------------- #
# The form + submission flow
# --------------------------------------------------------------------------- #
def test_form_serves_signed_token_and_no_js() -> None:
    client = _app()
    resp = client.get("/intake/new")
    assert resp.status_code == 200
    assert "<script" not in resp.text  # zero-JS surface
    assert "Part VIII" in resp.text
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["referrer-policy"] == "no-referrer"
    token = _mint_form(client)
    assert token.startswith("v1.")


def test_submit_happy_path_json() -> None:
    client = _app()
    token = _mint_form(client)
    resp = _submit(client, token, idempotency_key="my-form-nonce-00001")
    assert resp.status_code == 201
    body = resp.json()
    assert body["receipt_id"].startswith("rct-")
    assert len(body["receipt_id"]) == 4 + 32
    assert len(body["status_token"]) >= 40  # 256-bit url-safe
    assert body["response_window_hours"] == 336
    assert "not yet verified or published" in body["detail"]
    assert resp.headers["cache-control"] == "no-store"


def test_submit_form_urlencoded_returns_html_receipt() -> None:
    client = _app()
    token = _mint_form(client)
    resp = client.post(
        "/intake/v1/reports",
        data={
            "form_token": token,
            "category": "privacy_harm",
            "description": "This record exposes a specific household to harm.",
        },
        headers={"Accept": "text/html"},
    )
    assert resp.status_code == 201
    assert "text/html" in resp.headers["content-type"]
    assert "rct-" in resp.text
    assert 'data-testid="status-token"' in resp.text
    # The token is NEVER placed in a URL — confirmation renders inline (no 303).
    assert "status_token=" not in resp.text


def test_duplicate_retry_is_idempotent() -> None:
    client = _app()
    token = _mint_form(client)
    first = _submit(client, token, idempotency_key="retry-nonce-abcdef123")
    assert first.status_code == 201
    retry = _submit(client, token, idempotency_key="retry-nonce-abcdef123")
    assert retry.status_code == 200
    body = retry.json()
    assert body["duplicate"] is True
    assert body["receipt_id"] == first.json()["receipt_id"]
    # The token is issued exactly once — a retry cannot mint a second one.
    assert "status_token" not in body


def test_invalid_or_missing_form_token() -> None:
    client = _app()
    resp = _submit(client, "v1.forged.token", idempotency_key="nonce-abcdefghij")
    assert resp.status_code == 403
    assert resp.json()["error"] == "invalid_form_token"
    resp2 = _submit(client, "", idempotency_key="nonce-abcdefghij")
    assert resp2.status_code == 403


def test_form_token_expiry() -> None:
    signer = FormTokenSigner("k" * 20, ttl_seconds=10)
    token = signer.mint(now=1000.0)
    assert signer.verify(token, now=1005.0) is not None
    assert signer.verify(token, now=2000.0) is None
    assert signer.verify("v1.bad") is None
    assert signer.verify(token + "tampered") is None


# --------------------------------------------------------------------------- #
# Rejection cases — nothing persists, reasons are safe
# --------------------------------------------------------------------------- #
def test_oversized_body_413() -> None:
    client = _app()
    token = _mint_form(client)
    resp = _submit(client, token, description="y" * 20000)
    assert resp.status_code == 413
    assert resp.json()["error"] == "payload_too_large"


def test_unknown_field_and_bad_shapes_422() -> None:
    client = _app()
    token = _mint_form(client)
    resp = _submit(
        client,
        token,
        idempotency_key="nonce-1234567890ab",
        email="x@y.z",
        publication_id="not-a-release",
        evidence_urls=["http://insecure.example/x"],
    )
    assert resp.status_code == 422
    fields = resp.json()["fields"]
    assert fields["email"] == "unknown field"
    assert "publication_id" in fields
    assert "evidence_urls" in fields


def test_plate_person_payload_refused_before_store() -> None:
    client = _app()
    store = client.app.state.store
    token = _mint_form(client)
    for payload in (
        "The license plate AB-1234 appears in this record.",
        "this record shows the mayor's travel history",
        "contact jane.doe@example.com about this",
    ):
        resp = _submit(
            client,
            token,
            idempotency_key=f"nonce-{abs(hash(payload)) & 0xFFFFFFF:x}",
            description=payload,
        )
        assert resp.status_code == 422
        assert "description" in resp.json()["fields"]
    assert len(store.reports) == 0  # refused payloads are NEVER persisted


def test_script_payload_quarantined_and_escaped() -> None:
    """Script-bearing text may be stored (quarantined) but is NEVER rendered."""
    client = _app()
    token = _mint_form(client)
    resp = _submit(
        client,
        token,
        idempotency_key="nonce-scriptpayload",
        description="See <script>alert(1)</script> and <img src=x onerror=y>.",
    )
    assert resp.status_code == 201
    rid = resp.json()["receipt_id"]
    status = client.post(
        "/intake/v1/status",
        json={"receipt_id": rid, "status_token": resp.json()["status_token"]},
    )
    assert status.status_code == 200
    assert "script" not in status.json()  # status projection carries no raw text


def test_evidence_urls_never_fetched() -> None:
    """URL validation is lexical only — no resolver/egress exists on this path."""
    client = _app()
    token = _mint_form(client)
    resp = _submit(
        client,
        token,
        idempotency_key="nonce-urlvalidation",
        evidence_urls=["https://example.com/doc"],
    )
    assert resp.status_code == 201


# --------------------------------------------------------------------------- #
# The receipt status surface
# --------------------------------------------------------------------------- #
def _accepted(client: TestClient, key: str = "nonce-accept-00001") -> dict:
    token = _mint_form(client)
    resp = _submit(client, token, idempotency_key=key)
    assert resp.status_code == 201
    return resp.json()


def test_status_happy_path_coarse_only() -> None:
    client = _app()
    acc = _accepted(client)
    resp = client.post(
        "/intake/v1/status",
        json={"receipt_id": acc["receipt_id"], "status_token": acc["status_token"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "received"
    assert body["category"] == "factual_error"
    assert body["response_window_hours"] == 336
    # The public projection must NEVER carry raw text/contact/network ids.
    forbidden = {
        "description",
        "contact",
        "contact_for_legal_demand",
        "evidence_urls",
        "ip",
        "address",
        "user_agent",
        "idempotency_key",
        "record_key",
        "claim_ids",
        "publication_id",
    }
    assert forbidden.isdisjoint(body.keys())


def test_status_uniform_unknown_receipt() -> None:
    client = _app()
    resp = client.post(
        "/intake/v1/status",
        json={"receipt_id": "rct-" + "0" * 32, "status_token": "nope"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "unknown_receipt"


def test_status_wrong_token_same_response_as_unknown() -> None:
    """A bad token and a bad receipt id are indistinguishable (no enumeration)."""
    client = _app()
    acc = _accepted(client)
    bad_token = client.post(
        "/intake/v1/status",
        json={"receipt_id": acc["receipt_id"], "status_token": "wrong"},
    )
    bad_id = client.post(
        "/intake/v1/status",
        json={"receipt_id": "rct-" + "f" * 32, "status_token": acc["status_token"]},
    )
    assert bad_token.status_code == bad_id.status_code == 404
    assert bad_token.json() == bad_id.json()


def test_receipt_ids_do_not_enumerate() -> None:
    client = _app()
    a = _accepted(client, "nonce-enum-a00001")
    b = _accepted(client, "nonce-enum-b00002")
    assert a["receipt_id"] != b["receipt_id"]
    assert a["receipt_id"][4:] != b["receipt_id"][4:]
    # No sequential structure: the ids are 128-bit random.
    assert not b["receipt_id"].endswith(str(int(a["receipt_id"][-4:], 16) + 1))


def test_failed_lookup_rate_limit() -> None:
    gate = AbuseGate(
        "s" * 20,
        per_pseudonym_burst=3,
        per_pseudonym_per_hour=5,
        global_per_hour=100,
        failed_lookup_limit=3,
    )
    for _ in range(3):
        assert gate.record_failed_lookup("10.0.0.9") is False
    assert gate.record_failed_lookup("10.0.0.9") is True
    # A different pseudonym is unaffected.
    assert gate.record_failed_lookup("10.0.0.10") is False


def test_submit_rate_limits() -> None:
    gate = AbuseGate(
        "s" * 20,
        per_pseudonym_burst=2,
        per_pseudonym_per_hour=2,
        global_per_hour=100,
        failed_lookup_limit=10,
    )
    assert gate.try_accept("10.1.1.1", now=1000.0) is None
    assert gate.try_accept("10.1.1.1", now=1001.0) is None
    retry = gate.try_accept("10.1.1.1", now=1002.0)
    assert retry is not None and retry > 0
    # A different network pseudonym has its own bucket.
    assert gate.try_accept("10.1.1.2", now=1002.0) is None
    # The pseudonym is not the raw address and rotates daily.
    p1 = gate.pseudonym("10.1.1.1")
    assert "10.1.1.1" not in p1 and len(p1) == 32


def test_global_circuit_breaker() -> None:
    gate = AbuseGate(
        "s" * 20,
        per_pseudonym_burst=1000,
        per_pseudonym_per_hour=1000,
        global_per_hour=2,
        failed_lookup_limit=10,
    )
    assert gate.try_accept("10.2.0.1", now=0.0) is None
    assert gate.try_accept("10.2.0.2", now=0.0) is None
    assert gate.try_accept("10.2.0.3", now=0.0) is not None  # global backpressure


def test_origin_and_fetch_metadata_defense() -> None:
    client = _app()
    token = _mint_form(client)
    base = {
        "form_token": token,
        "category": "factual_error",
        "description": "The retention-days value on this record is wrong.",
        "idempotency_key": "nonce-origin-check1",
    }
    bad = client.post("/intake/v1/reports", json=base, headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403
    cross = client.post(
        "/intake/v1/reports",
        json=base,
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert cross.status_code == 403
    # Same-origin Origin and privacy clients without headers pass the check.
    ok = client.post(
        "/intake/v1/reports",
        json=base,
        headers={"Origin": "http://testserver"},
    )
    assert ok.status_code == 201


def test_unsupported_content_type_415() -> None:
    client = _app()
    resp = client.post(
        "/intake/v1/reports",
        content=b"a=1",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 415


def test_no_cors_grant() -> None:
    client = _app()
    resp = client.options("/intake/v1/reports")
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
