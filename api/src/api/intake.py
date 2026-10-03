# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The durable anonymous correction receiver (P32.16 / ADR-135, §55.5 SIG-FIND-006).

A **separate public-facing process** — never mounted on the read API, never the
loopback curation app (S4-D4: "a narrowly scoped public receiver, not public
curation"). It accepts bounded, allowlisted anonymous reports only:

* **Allowlist + bounds are data** — every field is validated by
  :mod:`policy.intake` against `intake_receiver.toml`; unknown fields, bad
  shapes, oversized bodies and Part VIII plate/person-shaped payloads are
  refused **before persistence** (no row is ever written for a rejection).
* **No uploads, no URL fetches** — evidence references are parsed, never
  dereferenced (SSRF bar); reporter HTML is never rendered (all output escaped).
* **Receipt capability** — an unguessable `rct-<128-bit>` receipt id plus a
  256-bit one-purpose bearer status token; only the token's SHA-256 digest is
  stored and lookups compare in constant time + are failure-rate-limited. The
  token is shown exactly once, in the inline (non-redirect) confirmation — it
  never appears in a URL, `Location`, analytics or persistent browser storage.
* **Idempotent retries** — the signed form token's nonce doubles as the
  idempotency key, so a no-JS reload re-POST returns the same receipt without
  double-counting.
* **Abuse control without durable identity** — per-pseudonym + global token
  buckets keyed on an HMAC pseudonym of the normalized ingress address (daily
  rotated secret, ≤24h TTL, never persisted; the pseudonym is still potentially
  personal data — never called anonymous).
* **Operating gate** — `SIG_INTAKE_ENABLED=1` mounts the surface (staging);
  accepting reports additionally requires the committed `ops/config.toml`
  `[intake].operational` flag AND `SIG_INTAKE_OPERATIONAL=1` — the unstaffed
  receiver answers `503 receiver_not_operating`, never an advertised form.

State isolation: this module talks to an :class:`IntakeReceiverStore` — the PG
implementation runs ``SET ROLE sig_intake_receiver`` and physically cannot
write claims, review decisions or publication dispositions (the schema has no
such grant). Nothing here calls the curation service or the claim sink.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import tomllib
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.intake import IntakeReceiverStore, PgIntakeReceiverStore
from db.intake_apply import APPLYABLE_OUTCOMES, IntakeApplyError, derive_operation_id
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from policy import intake as pint

from . import __version__
from .prohibitions import assert_no_prohibited_routes, route_paths

__all__ = [
    "INTAKE_ENABLED_ENV",
    "INTAKE_OPERATIONAL_ENV",
    "INTAKE_FORM_SECRET_ENV",
    "INTAKE_ABUSE_SECRET_ENV",
    "AbuseGate",
    "FormTokenSigner",
    "MemoryIntakeStore",
    "create_intake_app",
    "intake_enabled",
    "intake_operational",
    "ops_config_path",
    "receiver_store_from_dsn",
]

INTAKE_ENABLED_ENV = "SIG_INTAKE_ENABLED"
INTAKE_OPERATIONAL_ENV = "SIG_INTAKE_OPERATIONAL"
INTAKE_FORM_SECRET_ENV = "SIG_INTAKE_FORM_SECRET"
INTAKE_ABUSE_SECRET_ENV = "SIG_INTAKE_ABUSE_SECRET"


def intake_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Whether the receiver surface is mounted (``SIG_INTAKE_ENABLED=1``).

    Disabled ⇒ no ``/intake/*`` routes exist at all (404), mirroring the
    curation surface's disabled-by-default contract (RISK-P21-10 shape).
    """
    source = os.environ if env is None else env
    return source.get(INTAKE_ENABLED_ENV) == "1"


def ops_config_path() -> Path:
    """The repo's ``ops/config.toml`` — the committed operator-gate input."""
    return Path(__file__).resolve().parents[3] / "ops" / "config.toml"


def intake_operational(
    env: Mapping[str, str] | None = None, config_path: str | Path | None = None
) -> bool:
    """Whether the receiver may ACCEPT reports — two keys, both fail-closed.

    Requires the committed operator decision ``[intake].operational = true``
    (ops/config.toml — a gate record like the contribution `registered` flag)
    AND ``SIG_INTAKE_OPERATIONAL=1`` in the process environment (the armed
    kill-switch). Without both, the receiver refuses new reports with
    ``receiver_not_operating`` — an unstaffed receiver is never advertised as
    operational (D-R10-PUBLISH-1 / GATE-G3).
    """
    source = os.environ if env is None else env
    if source.get(INTAKE_OPERATIONAL_ENV) != "1":
        return False
    path = Path(config_path) if config_path is not None else ops_config_path()
    try:
        with path.open("rb") as fh:
            cfg = tomllib.load(fh)
    except OSError:
        return False
    return cfg.get("intake", {}).get("operational") is True


# --------------------------------------------------------------------------- #
# The form token — expiring anti-replay HMAC token; its nonce doubles as the
# no-JS idempotency key (a reload re-POST is the same submission).
# --------------------------------------------------------------------------- #
class FormTokenSigner:
    """Mint + verify the expiring signed form token (`v1.<b64 payload>.<b64 sig>`)."""

    def __init__(self, secret: str | bytes, ttl_seconds: int) -> None:
        key = secret.encode() if isinstance(secret, str) else secret
        if len(key) < 16:
            raise ValueError("the intake form secret must be at least 16 bytes")
        self._key = key
        self._ttl = ttl_seconds

    def mint(self, *, now: float | None = None) -> str:
        import time

        issued = int(now if now is not None else time.time())
        payload = json.dumps(
            {"n": secrets.token_hex(16), "iat": issued}, separators=(",", ":")
        ).encode()
        body = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
        sig = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
        return f"v1.{body}.{sig}"

    def verify(self, token: str, *, now: float | None = None) -> str | None:
        """Return the token's nonce iff signature + expiry hold, else ``None``."""
        import time

        try:
            version, body, sig = token.split(".", 2)
        except ValueError:
            return None
        if version != "v1":
            return None
        expected = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        try:
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        except (ValueError, json.JSONDecodeError):
            return None
        nonce, issued = payload.get("n"), payload.get("iat")
        if not isinstance(nonce, str) or not isinstance(issued, int):
            return None
        if (now if now is not None else time.time()) - issued > self._ttl:
            return None
        return nonce


# --------------------------------------------------------------------------- #
# The abuse gate — ephemeral pseudonyms + token buckets, nothing persisted.
# --------------------------------------------------------------------------- #
class AbuseGate:
    """Rate limits keyed on a rotating HMAC pseudonym of the ingress address.

    The pseudonym is ``HMAC(secret, "<UTC day>|<normalized host>")`` — the
    daily-rotated secret bounds its lifetime to ≤24h by construction, and the
    raw address is never stored (in-memory buckets only). Per the research it
    is still potentially personal data — never called anonymous.
    """

    def __init__(
        self,
        secret: str | bytes,
        *,
        per_pseudonym_burst: int,
        per_pseudonym_per_hour: int,
        global_per_hour: int,
        failed_lookup_limit: int,
    ) -> None:
        key = secret.encode() if isinstance(secret, str) else secret
        if len(key) < 16:
            raise ValueError("the intake abuse secret must be at least 16 bytes")
        self._key = key
        self._burst = per_pseudonym_burst
        self._rate = per_pseudonym_per_hour / 3600.0
        self._global_rate = global_per_hour / 3600.0
        self._global_cap = global_per_hour
        self._failed_limit = failed_lookup_limit
        self._buckets: dict[str, tuple[float, float]] = {}  # pseudonym -> (tokens, ts)
        self._global = (float(global_per_hour), 0.0)
        self._failed: dict[str, list[float]] = {}

    def pseudonym(self, client_host: str) -> str:
        """The rotating abuse pseudonym for an ingress address (≤24h TTL)."""
        import time

        day = int(time.time()) // 86400
        msg = f"{day}|{client_host.strip().lower()}".encode()
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()[:32]

    @staticmethod
    def _take(
        bucket: tuple[float, float], cap: int, rate: float, now: float
    ) -> tuple[float, float]:
        tokens, ts = bucket
        tokens = min(float(cap), tokens + (now - ts) * rate)
        return tokens, now

    def try_accept(self, client_host: str, *, now: float | None = None) -> float | None:
        """Consume one submission slot; returns retry-after seconds if limited."""
        import time

        moment = now if now is not None else time.time()
        pseudo = self.pseudonym(client_host)
        tokens, ts = self._buckets.get(pseudo, (float(self._burst), moment))
        tokens, ts = self._take((tokens, ts), self._burst, self._rate, moment)
        gtokens, gts = self._take(self._global, self._global_cap, self._global_rate, moment)
        self._global = (gtokens, gts)
        if tokens < 1.0:
            self._buckets[pseudo] = (tokens, ts)
            return max(1.0, (1.0 - tokens) / self._rate)
        if gtokens < 1.0:
            return max(1.0, (1.0 - gtokens) / self._global_rate)
        self._buckets[pseudo] = (tokens - 1.0, ts)
        self._global = (gtokens - 1.0, gts)
        return None

    def record_failed_lookup(self, client_host: str, *, now: float | None = None) -> bool:
        """Record a failed status lookup; True once the hourly cap is exceeded."""
        import time

        moment = now if now is not None else time.time()
        pseudo = self.pseudonym(client_host)
        window = [t for t in self._failed.get(pseudo, []) if moment - t < 3600.0]
        window.append(moment)
        self._failed[pseudo] = window
        return len(window) > self._failed_limit


# --------------------------------------------------------------------------- #
# The in-memory receiver store — the deterministic test/dev double mirroring
# PgIntakeReceiverStore's contract (durable semantics are PG-only; serving
# requires a real DSN).
# --------------------------------------------------------------------------- #
class MemoryIntakeStore:
    """A lossless-enough in-memory double for tests (restart = data loss by design)."""

    def __init__(self) -> None:
        self.reports: dict[str, dict[str, Any]] = {}
        self._idem: dict[str, str] = {}
        self._digests: dict[str, bytes] = {}
        self.events: list[dict[str, Any]] = []
        # P32.16a: simulated applied receipts (PG truth is intake.application).
        self.applications: list[dict[str, Any]] = []

    def insert_report(
        self,
        *,
        report_id: str,
        receipt_id: str,
        idempotency_key: str,
        category: str,
        description: str,
        publication_id: str | None,
        record_key: str | None,
        claim_ids: list[str],
        evidence_urls: list[str],
        contact: str | None,
        token_digest: bytes,
    ) -> None:
        from datetime import UTC, datetime

        self.reports[report_id] = {
            "report_id": report_id,
            "receipt_id": receipt_id,
            "idempotency_key": idempotency_key,
            "category": category,
            "description": description,
            "publication_id": publication_id,
            "record_key": record_key,
            "claim_ids": list(claim_ids),
            "evidence_urls": list(evidence_urls),
            "contact": contact,
            "received_at": datetime.now(UTC).isoformat(),
            "lifecycle_event": "received",
        }
        self._idem[idempotency_key] = receipt_id
        self._digests[report_id] = token_digest
        self.events.append(
            {
                "report_id": report_id,
                "event": "received",
                "actor": "sig-intake-receiver",
                "detail": {},
            }
        )

    def find_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        receipt = self._idem.get(idempotency_key)
        if receipt is None:
            return None
        for r in self.reports.values():
            if r["receipt_id"] == receipt:
                return {
                    "receipt_id": receipt,
                    "category": r["category"],
                    "received_at": r["received_at"],
                    "state": pint.public_state(r["lifecycle_event"]),
                    "public_response": None,
                }
        return None

    def public_status(self, receipt_id: str) -> dict[str, Any] | None:
        for r in self.reports.values():
            if r["receipt_id"] == receipt_id:
                return {
                    "report_id": r["report_id"],
                    "receipt_id": receipt_id,
                    "category": r["category"],
                    "received_at": r["received_at"],
                    "lifecycle_event": r["lifecycle_event"],
                    "state": pint.public_state(r["lifecycle_event"]),
                    "public_response": r.get("public_response"),
                }
        return None

    def receipt_token_digest(self, report_id: str) -> bytes | None:
        return self._digests.get(report_id)

    # -- the reviewer interface (same store, the private side) ---------------- #
    # Mirrors PgIntakeReviewerStore so the moderation routes are testable
    # without a database. `expunge_due` is a no-op report: retention semantics
    # are PG-fixture tested (tests/db).
    def queue(self, *, limit: int = 200, include_closed: bool = False) -> list[dict[str, Any]]:
        rows = sorted(self.reports.values(), key=lambda r: r["received_at"])
        if not include_closed:
            terminal = {"disposition_approved", "applied", "published", "closed"}
            rows = [r for r in rows if r["lifecycle_event"] not in terminal]
        return [
            {
                "receipt_id": r["receipt_id"],
                "category": r["category"],
                "received_at": r["received_at"],
                "lifecycle_event": r["lifecycle_event"],
            }
            for r in rows[:limit]
        ]

    def detail(self, receipt_id: str) -> dict[str, Any] | None:
        for r in self.reports.values():
            if r["receipt_id"] == receipt_id:
                events = [e for e in self.events if e["report_id"] == r["report_id"]]
                lifecycle = next(
                    (e["event"] for e in reversed(events) if pint.is_lifecycle_event(e["event"])),
                    "received",
                )
                return {
                    **{k: v for k, v in r.items() if k != "lifecycle_event"},
                    "events": [{"event_seq": i + 1, **e} for i, e in enumerate(events)],
                    "lifecycle_event": lifecycle,
                }
        return None

    def record_event(self, receipt_id: str, event: str, actor: str, detail: dict[str, Any]) -> int:
        row = self.detail(receipt_id)
        if row is None:
            raise KeyError(f"unknown receipt {receipt_id!r}")
        seq = len(self.events) + 1
        self.events.append(
            {"report_id": row["report_id"], "event": event, "actor": actor, "detail": detail}
        )
        if pint.is_lifecycle_event(event):
            self.reports[row["report_id"]]["lifecycle_event"] = event
        return seq

    def redact(self, receipt_id: str, fields: list[str], actor: str) -> None:
        row = self.detail(receipt_id)
        if row is None:
            raise KeyError(f"unknown receipt {receipt_id!r}")
        report = self.reports[row["report_id"]]
        for f in fields:
            if f == "description":
                report["description"] = "[redacted]"
            elif f == "contact":
                report["contact"] = None
            elif f in {"evidence_urls", "claim_ids"}:
                report[f] = []
            else:
                report[f] = None
        self.events.append(
            {
                "report_id": row["report_id"],
                "event": "redacted",
                "actor": actor,
                "detail": {"fields": sorted(fields)},
            }
        )

    def close(self) -> None:
        return None

    # -- the application bridge interface (P32.16a / SIG-FIND-008) ------------ #
    # Simulates PgIntakeApplicationStore's contract: the approval event is the
    # authority record, operation_id is the idempotency key. No canonical
    # writes happen here — the memory double only tracks lifecycle + receipts.
    def apply(
        self, receipt_id: str, *, actor: str, operation_id: str | None = None
    ) -> dict[str, Any]:
        row = self.detail(receipt_id)
        if row is None:
            raise IntakeApplyError("unknown_receipt", "unknown receipt")
        events = row["events"]
        latest = next((e for e in reversed(events) if pint.is_lifecycle_event(e["event"])), None)
        # Retry-after-commit: an `applied`-latest report's committed
        # application row IS the operation — reconcile to it. A superseded
        # approval comes back through re-proposal → re-approval and derives a
        # new operation_id, so it falls through to the approval gate.
        if latest is not None and latest["event"] == "applied":
            prior_app = next(
                (a for a in reversed(self.applications) if a["report_id"] == row["report_id"]),
                None,
            )
            if prior_app is not None:
                if operation_id is not None and operation_id != prior_app["operation_id"]:
                    raise IntakeApplyError(
                        "operation_id_conflict",
                        "operation_id names a different application — reconcile, never overwrite",
                    )
                return {
                    **prior_app,
                    "receipt_id": receipt_id,
                    "applied": True,
                    "reconciled": True,
                }
        if latest is None or latest["event"] != "disposition_approved":
            raise IntakeApplyError(
                "no_current_approval",
                "the latest lifecycle event is not an approval",
            )
        outcome = str((latest["detail"] or {}).get("outcome") or "")
        if outcome not in APPLYABLE_OUTCOMES:
            raise IntakeApplyError("outcome_not_appliable", f"outcome {outcome!r} does not apply")
        op_id = operation_id or derive_operation_id(
            row["report_id"], int(latest["event_seq"]), outcome
        )
        prior = next((a for a in self.applications if a["operation_id"] == op_id), None)
        if prior is not None:
            if (
                prior["report_id"] != row["report_id"]
                or int(prior["approval_seq"]) != int(latest["event_seq"])
                or prior["outcome"] != outcome
            ):
                raise IntakeApplyError(
                    "operation_id_conflict",
                    "operation_id already names a different application — "
                    "reconcile, never overwrite",
                )
            return {**prior, "receipt_id": receipt_id, "applied": True, "reconciled": True}
        seq = (latest["detail"] or {}).get("approves_seq")
        proposal_event = next(
            (
                e
                for e in events
                if seq is not None
                and int(e["event_seq"]) == int(seq)
                and e["event"] == "disposition_proposed"
            ),
            None,
        )
        if proposal_event is None:
            raise IntakeApplyError(
                "approval_without_proposal",
                "the approval does not name a live disposition_proposed",
            )
        try:
            proposal = pint.validate_proposal(
                outcome, (proposal_event["detail"] or {}).get("proposal") or {}
            )
        except pint.IntakeFieldError as exc:
            raise IntakeApplyError("invalid_proposal", str(exc)) from exc
        app = {
            "application_id": str(uuid.uuid4()),
            "report_id": row["report_id"],
            "operation_id": op_id,
            "approval_seq": int(latest["event_seq"]),
            "proposal_seq": int(proposal_event["event_seq"]),
            "outcome": outcome,
            "approved_by": latest["actor"],
            "applied_by": actor,
            "target_kind": proposal["target_kind"],
            "target_claim_id": (
                proposal["target_id"] if proposal["target_kind"] == "claim" else None
            ),
            "target_id": proposal["target_id"],
            "result_claim_id": (str(uuid.uuid4()) if outcome in ("correct", "annotate") else None),
            "disposition_id": (str(uuid.uuid4()) if outcome in ("suppress", "delete") else None),
            "ingest_run_id": None,
            "detail": {},
            "applied_at": datetime.now(UTC).isoformat(),
        }
        self.applications.append(app)
        self.record_event(
            receipt_id,
            "applied",
            actor,
            {
                "application_id": app["application_id"],
                "operation_id": op_id,
                "outcome": outcome,
                "approval_seq": app["approval_seq"],
                "target_kind": proposal["target_kind"],
                "target_id": proposal["target_id"],
            },
        )
        return {
            **app,
            "receipt_id": receipt_id,
            "applied": True,
            "reconciled": False,
        }

    def mark_published(
        self,
        receipt_id: str,
        *,
        actor: str,
        publication_id: str | None = None,
        correction_ref: str | None = None,
        tombstone: str | None = None,
    ) -> dict[str, Any]:
        row = self.detail(receipt_id)
        if row is None:
            raise IntakeApplyError("unknown_receipt", "unknown receipt")
        events = row["events"]
        latest = next((e for e in reversed(events) if pint.is_lifecycle_event(e["event"])), None)
        if latest is not None and latest["event"] == "published":
            return {
                "receipt_id": receipt_id,
                "event": "published",
                "event_seq": int(latest["event_seq"]),
                "detail": latest["detail"],
                "reconciled": True,
            }
        if latest is None or latest["event"] != "applied":
            raise IntakeApplyError("not_applied", "publication linkage requires an applied report")
        linkage: dict[str, str] = {}
        if publication_id is not None or correction_ref is not None or tombstone is not None:
            try:
                linkage = pint.validate_publish_linkage(
                    publication_id=publication_id,
                    correction_ref=correction_ref,
                    tombstone=tombstone,
                )
            except pint.IntakeFieldError as exc:
                raise IntakeApplyError("invalid_linkage", str(exc)) from exc
        app = next((a for a in self.applications if a["report_id"] == row["report_id"]), None)
        if app is None:
            raise IntakeApplyError("no_application", "no applied receipt exists")
        detail = {
            "application_id": app["application_id"],
            "operation_id": app["operation_id"],
            **linkage,
        }
        if "correction_ref" not in detail:
            detail["correction_ref"] = str(app["result_claim_id"] or app["disposition_id"])
        if "publication_id" not in detail and "tombstone" not in detail:
            detail["tombstone"] = "release identity not yet linked"
        seq = self.record_event(receipt_id, "published", actor, detail)
        return {
            "receipt_id": receipt_id,
            "event": "published",
            "event_seq": seq,
            "detail": detail,
            "reconciled": False,
        }

    def application(self, receipt_id: str) -> dict[str, Any] | None:
        for r in self.reports.values():
            if r["receipt_id"] == receipt_id:
                for a in self.applications:
                    if a["report_id"] == r["report_id"]:
                        return dict(a)
                return None
        return None


def receiver_store_from_dsn(dsn: str) -> IntakeReceiverStore:
    """The durable receiver store — `SET ROLE sig_intake_receiver` on connect."""
    return PgIntakeReceiverStore.from_dsn(dsn)


# --------------------------------------------------------------------------- #
# The receiver app
# --------------------------------------------------------------------------- #
def _client_host(request: Request) -> str:
    """The normalized ingress address for abuse pseudonymization.

    Uses the direct peer only — `X-Forwarded-For` is *trusted* input and must be
    normalized by the deployment edge before it reaches here (the operating
    packet records that requirement); the app never guesses at header truth.
    """
    return (request.client.host if request.client else "unknown").lower()


def _security_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; base-uri 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Cross-Origin-Opener-Policy": "same-origin",
    }


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title></head><body>{body}</body></html>"
    )


def _html_response(markup: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(markup, status_code=status, headers=_security_headers())


def _json(
    payload: dict[str, Any], status: int = 200, extra_headers: dict[str, str] | None = None
) -> JSONResponse:
    headers = dict(_security_headers())
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(payload, status_code=status, headers=headers)


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def _check_origin(request: Request) -> None:
    """Defensive Origin / Fetch-Metadata validation (S4 §8).

    An Origin header, when supplied, must be same-origin (scheme-agnostic host
    match — the edge terminates TLS). `Sec-Fetch-Site: cross-site` is refused.
    Clients without either header pass — the signed form token is the actual
    anti-CSRF control, so privacy clients are never blocked for missing
    optional headers. There is no CORS grant on this surface at all.
    """
    origin = request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit

        try:
            host = urlsplit(origin).hostname or ""
        except ValueError:
            host = ""
        if host.lower() != (request.url.hostname or "").lower():
            raise HTTPException(status_code=403, detail="origin_mismatch")
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site and fetch_site.lower() == "cross-site":
        raise HTTPException(status_code=403, detail="cross_site_refused")


def _intake_form_html(form_token: str) -> str:
    cats = "".join(
        f'<option value="{html.escape(str(c["id"]))}">{html.escape(str(c["label"]))}</option>'
        for c in pint.intake_categories()
    )
    return _page(
        "Report a problem",
        f"""<h1>Report a problem</h1>
<p>This is SIG's anonymous correction channel. No account, no email, no
identity is required — the single exception is a legal demand that needs
standing (you may optionally leave a contact for that category only).</p>
<p><strong>Describe institutional facts only.</strong> Do not include licence
plates, people's names, home addresses, per-person movements or other
identifying details — such reports are refused automatically before storage
(Part VIII). Free text can disclose personal information; keep it to the
record facts. References are stored, never fetched.</p>
<form method="post" action="/intake/v1/reports" accept-charset="utf-8">
<input type="hidden" name="form_token" value="{html.escape(form_token)}">
<p><label>What are you reporting?
<select name="category" required>{cats}</select></label></p>
<p><label>Release id (optional — the p-… namespace this concerns)
<input type="text" name="publication_id" maxlength="66" size="50"></label></p>
<p><label>Record reference (optional — &lt;compartment&gt;:&lt;type&gt;:&lt;id&gt;)
<input type="text" name="record_key" maxlength="200" size="50"></label></p>
<p><label>Public claim ids (optional — up to 10, comma-separated)
<input type="text" name="claim_ids" maxlength="600" size="50"></label></p>
<p><label>Description (required — what is wrong or harmful; 20–4000 chars)<br>
<textarea name="description" required minlength="20" maxlength="4000"
 rows="8" cols="72"></textarea></label></p>
<p><label>Public evidence links (optional — up to 3 https URLs, comma-separated)
<input type="text" name="evidence_urls" maxlength="2048" size="60"></label></p>
<p><label>Contact for a legal demand (optional, legal demand only)
<input type="text" name="contact_for_legal_demand" maxlength="512" size="50"></label></p>
<p><button type="submit">Send report</button></p>
</form>
<p><a href="/intake/status">Check a receipt</a></p>""",
    )


def _status_form_html() -> str:
    return _page(
        "Check a receipt",
        """<h1>Check a receipt</h1>
<p>Enter the receipt id and the status token shown when your report was
accepted. The token is never put in a URL and this page stores nothing.</p>
<form method="post" action="/intake/v1/status" accept-charset="utf-8">
<p><label>Receipt id (rct-…) <input type="text" name="receipt_id"
 required maxlength="40" size="40"></label></p>
<p><label>Status token <input type="text" name="status_token" required
 maxlength="128" size="64"></label></p>
<p><button type="submit">Check status</button></p>
</form>
<p><a href="/intake/new">Start a report</a></p>""",
    )


_NOT_OPERATING_BODY = _page(
    "Correction channel — not yet operating",
    """<h1>Correction channel</h1>
<p><strong>The anonymous correction receiver is not yet operating.</strong>
It opens only after a staffed moderation owner, the retention schedule and the
public-exposure decision are approved (GATE-G3 / HG-11). This page will never
advertise an unstaffed receiver. The public
<a href="/dispute/">dispute page</a> describes the process and every completed
correction is listed on the <a href="/corrections/">corrections log</a>.</p>""",
)


def create_intake_app(
    *,
    store: IntakeReceiverStore | None = None,
    enabled: bool | None = None,
    operational: bool | None = None,
    form_secret: str | bytes | None = None,
    abuse_secret: str | bytes | None = None,
    env: Mapping[str, str] | None = None,
    abuse_gate: AbuseGate | None = None,
    signer: FormTokenSigner | None = None,
) -> FastAPI:
    """The anonymous correction receiver app — its own process, always.

    ``enabled`` mounts the surface (staging + status); ``operational`` opens
    the form/POST path. Both default to the env/config gates so a bare service
    is never operational by accident.
    """
    if enabled is None:
        enabled = intake_enabled(env)
    if operational is None:
        operational = intake_operational(env)

    app = FastAPI(title="SIG Correction Receiver", version=__version__)
    app.state.enabled = enabled
    app.state.operational = operational
    app.state.store = store if store is not None else MemoryIntakeStore()

    lim = pint.limits()
    if signer is None:
        secret = form_secret or (env or os.environ).get(INTAKE_FORM_SECRET_ENV)
        if secret is None:
            if operational:
                raise RuntimeError(
                    "an operational receiver requires a form secret "
                    f"({INTAKE_FORM_SECRET_ENV}) — fail closed"
                )
            secret = "intake-form-dev-only-secret"
        signer = FormTokenSigner(secret, int(pint.contract()["form_token"]["ttl_seconds"]))
    app.state.signer = signer

    if abuse_gate is None:
        secret = abuse_secret or (env or os.environ).get(INTAKE_ABUSE_SECRET_ENV)
        if secret is None:
            if operational:
                raise RuntimeError(
                    "an operational receiver requires an abuse secret "
                    f"({INTAKE_ABUSE_SECRET_ENV}) — fail closed"
                )
            secret = "intake-abuse-dev-only-secret"
        abuse_cfg = pint.contract()["abuse"]
        abuse_gate = AbuseGate(
            secret,
            per_pseudonym_burst=int(abuse_cfg["per_pseudonym_burst"]),
            per_pseudonym_per_hour=int(abuse_cfg["per_pseudonym_per_hour"]),
            global_per_hour=int(abuse_cfg["global_per_hour"]),
            failed_lookup_limit=int(pint.contract()["receipt"]["failed_lookup_limit"]),
        )
    app.state.abuse = abuse_gate
    if not enabled:
        # Disabled ⇒ the surface is absent entirely (404), like curation.

        @app.get("/")
        def disabled_root() -> dict[str, Any]:
            return {
                "service": "sig-intake-receiver",
                "version": __version__,
                "enabled": False,
                "operational": False,
            }

        return app

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "sig-intake-receiver",
            "version": __version__,
            "enabled": True,
            "operational": operational,
            "contract": pint.contract_version(),
            "submission": "POST /intake/v1/reports (operational only)",
            "status": "POST /intake/v1/status",
        }

    @app.get("/intake/new", response_class=HTMLResponse)
    def new_form(request: Request) -> Response:
        if not app.state.operational:
            return _html_response(_NOT_OPERATING_BODY, status=503)
        token = app.state.signer.mint()
        return _html_response(_intake_form_html(token))

    @app.get("/intake/status", response_class=HTMLResponse)
    def status_form() -> Response:
        return _html_response(_status_form_html())

    @app.post("/intake/v1/reports")
    async def submit_report(request: Request) -> Response:
        if not app.state.operational:
            if _wants_html(request):
                return _html_response(_NOT_OPERATING_BODY, status=503)
            return _json(
                {
                    "error": "receiver_not_operating",
                    "detail": "the correction receiver is not yet operating "
                    "(staffing/operating approval pending)",
                },
                status=503,
            )
        _check_origin(request)

        content_type = (request.headers.get("content-type") or "").split(";")[0].strip()
        if content_type not in {"application/json", "application/x-www-form-urlencoded"}:
            return _json(
                {
                    "error": "unsupported_media_type",
                    "detail": "submit JSON or application/x-www-form-urlencoded",
                },
                status=415,
            )
        body = await request.body()
        if len(body) > int(lim["body_bytes"]):
            return _json(
                {
                    "error": "payload_too_large",
                    "detail": f"bodies are capped at {lim['body_bytes']} bytes",
                },
                status=413,
            )
        try:
            if content_type == "application/json":
                raw = json.loads(body or b"{}")
                if not isinstance(raw, dict):
                    raise ValueError
                fields: dict[str, Any] = dict(raw)
            else:
                from urllib.parse import parse_qsl

                fields = {}
                for key, value in parse_qsl(body.decode("utf-8", errors="replace")):
                    if key in fields:
                        existing = fields[key]
                        fields[key] = (
                            [*existing, value] if isinstance(existing, list) else [existing, value]
                        )
                    else:
                        fields[key] = value
        except (ValueError, UnicodeDecodeError):
            return _json({"error": "malformed_body"}, status=422)

        # The form token is transport auth + the no-JS idempotency nonce.
        token = str(fields.get("form_token") or "")
        nonce = app.state.signer.verify(token)
        if nonce is None:
            return _json(
                {
                    "error": "invalid_form_token",
                    "detail": "the form token is missing, malformed or expired — "
                    "load /intake/new for a fresh one",
                },
                status=403,
            )
        fields.setdefault("idempotency_key", nonce)

        retry_after = app.state.abuse.try_accept(_client_host(request))
        if retry_after is not None:
            return _json(
                {
                    "error": "rate_limited",
                    "retry_after_seconds": int(retry_after) + 1,
                    "detail": "submission rate exceeded — wait and retry; your "
                    "prepared report is not lost if you keep this page",
                },
                status=429,
                extra_headers={"Retry-After": str(int(retry_after) + 1)},
            )

        try:
            report = pint.normalize_report(fields)
        except pint.IntakeFieldError as exc:
            # Rejected BEFORE persistence: no row, no log entry, only the safe
            # per-field reasons. 422 preserves escaped safe fields in the form
            # (the reporter's page is still open) — nothing is stored here.
            return _json({"error": "invalid_report", "fields": exc.fields}, status=422)

        store: IntakeReceiverStore = app.state.store
        prior = store.find_by_idempotency(report.idempotency_key)
        if prior is not None:
            # Idempotent retry: same nonce ⇒ same receipt, +0 stored, no
            # double-count. The status token is shown once at first acceptance;
            # a retry names the original receipt without re-issuing a token.
            return _json(
                {
                    "receipt_id": prior["receipt_id"],
                    "duplicate": True,
                    "received_at": prior["received_at"],
                    "state": prior["state"],
                    "detail": "already received — use the status token issued "
                    "with the first acceptance",
                },
                status=200,
            )

        receipt_id = f"rct-{secrets.token_hex(16)}"
        status_token = secrets.token_urlsafe(int(pint.contract()["receipt"]["token_bytes"]))
        digest = hashlib.sha256(status_token.encode()).digest()
        try:
            store.insert_report(
                report_id=str(uuid.uuid4()),
                receipt_id=receipt_id,
                idempotency_key=report.idempotency_key,
                category=report.category,
                description=report.description,
                publication_id=report.publication_id,
                record_key=report.record_key,
                claim_ids=list(report.claim_ids),
                evidence_urls=list(report.evidence_urls),
                contact=report.contact_for_legal_demand,
                token_digest=digest,
            )
        except Exception:
            # Failed persistence ⇒ honest "not received" — never optimistic.
            return _json(
                {
                    "error": "persistence_failed",
                    "detail": "the report was NOT received — retry; nothing was stored",
                },
                status=503,
            )

        window = pint.category_response_window_hours(report.category)
        if _wants_html(request):
            return _html_response(
                _page(
                    "Report received",
                    f"""<h1>Report received</h1>
<p><strong>Received; not yet verified or published.</strong> Your report is in
the private review queue. A reviewer response is aimed for within
{window} hours (the published triage window — not a resolution promise).</p>
<p>Receipt id: <code data-testid="receipt-id">{html.escape(receipt_id)}</code></p>
<p>Status token: <code data-testid="status-token">{html.escape(status_token)}</code></p>
<p><strong>Save both now — the token is shown once and cannot be recovered.</strong>
Use them on the <a href="/intake/status">receipt page</a> to check progress.
This page stores nothing and the token is never part of a link.</p>""",
                ),
                status=201,
            )
        return _json(
            {
                "receipt_id": receipt_id,
                "status_token": status_token,
                "received": "received",
                "response_window_hours": window,
                "detail": "Received; not yet verified or published.",
            },
            status=201,
        )

    @app.post("/intake/v1/status")
    async def check_status(request: Request) -> Response:
        content_type = (request.headers.get("content-type") or "").split(";")[0].strip()
        fields: dict[str, Any] = {}
        if content_type == "application/json":
            try:
                raw = json.loads(await request.body() or b"{}")
                if isinstance(raw, dict):
                    fields = dict(raw)
            except json.JSONDecodeError:
                pass
        elif content_type == "application/x-www-form-urlencoded":
            from urllib.parse import parse_qsl

            fields = dict(parse_qsl((await request.body()).decode("utf-8", errors="replace")))
        receipt_id = str(fields.get("receipt_id") or "")
        status_token = str(fields.get("status_token") or "")

        store = app.state.store
        row = store.public_status(receipt_id) if receipt_id else None
        ok = False
        if row is not None and status_token:
            digest = store.receipt_token_digest(str(row["report_id"]))
            ok = bool(
                digest is not None
                and hmac.compare_digest(digest, hashlib.sha256(status_token.encode()).digest())
            )
        if not ok:
            over = app.state.abuse.record_failed_lookup(_client_host(request))
            status = 429 if over else 404
            return _json(
                {"error": "unknown_receipt", "detail": "no receipt matches that id/token pair"},
                status=status,
            )
        assert row is not None  # noqa: S101
        payload = {
            "receipt_id": row["receipt_id"],
            "state": row["state"],
            "received_at": row["received_at"],
            "category": row["category"],
            "response_window_hours": pint.category_response_window_hours(row["category"]),
        }
        if row.get("public_response"):
            payload["response"] = row["public_response"]
        if _wants_html(request):
            body = (
                f"<h1>Receipt status</h1><p>State: <strong>"
                f"{html.escape(payload['state'])}</strong></p>"
                f"<p>Received: {html.escape(payload['received_at'])} · Category: "
                f"{html.escape(payload['category'])}</p>"
            )
            if payload.get("response"):
                body += f"<p>Reviewer response: {html.escape(payload['response'])}</p>"
            body += '<p><a href="/intake/status">Check another</a></p>'
            return _html_response(_page("Receipt status", body))
        return _json(payload)

    # The structural bar also guards this surface — a prohibited route shape
    # must fail construction, not a later request.
    assert_no_prohibited_routes(route_paths([r for r in app.routes if isinstance(r, Route)]))
    return app
