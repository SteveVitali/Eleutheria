# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The notifier seam + the recorded-alert ledger (OBS.1 / GL-OBS-01, ADR-077).

The zero-cost posture (SIG-STORE-003) rules out a paid alerting service, so the
notifier seam is three concrete sinks, none of which needs an account:

* the **alert ledger** — an append-only JSONL file (default ``.sig/ops/alerts.jsonl``,
  env ``SIG_ALERT_LOG``). This is the *recorded* half of every alert and is always
  on: an alert is recorded before any external notification is attempted, so the
  deterministic artifact never depends on network or credentials.
* a **log notifier** — a structured ``SIG-ALERT`` line on a stream (stderr in the
  CLI); the same line a workflow log or a host journal captures.
* an optional **webhook notifier** — ``SIG_ALERT_WEBHOOK_URL`` (e.g. a free
  `ntfy.sh` topic, a self-hosted hook, or the host's own endpoint) with an optional
  ``SIG_ALERT_WEBHOOK_TOKEN`` bearer token. Both are **env-only** (HG-09): no
  credential literal ever touches a file, and the URL — which may itself embed a
  secret path — is never logged.

Secret hygiene is structural: every string that reaches a log line, the ledger, or
the webhook body passes through :func:`scrub_secrets`, which replaces the *values*
of secret-looking env vars (``*_TOKEN``/``*_SECRET``/``*_PASSWORD``/``*_KEY`` plus
``SIG_ALERT_WEBHOOK_URL``) with ``***redacted***``. The test suite asserts no env
secret appears in any emitted surface.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TextIO

#: Env-var *name* suffixes whose values are secrets (HG-09) and must never be logged.
SECRET_ENV_RE = re.compile(r"(_TOKEN|_SECRET|_PASSWORD|_KEY)$")
#: SIG_* vars that may embed a credential without carrying a secret-looking suffix
#: (a webhook URL commonly has its token in the path).
EXTRA_SECRET_ENV = ("SIG_ALERT_WEBHOOK_URL",)
#: The marker written in place of a scrubbed secret value.
REDACTED = "***redacted***"

#: Alert severities, low → high. ``warn`` maps to the egress warn band; ``alarm`` to a
#: real threshold breach; ``critical`` to a keepalive/availability failure.
SEVERITIES = ("warn", "alarm", "critical")


def utcnow() -> str:
    """ISO-8601 UTC seconds — the timestamp shape every alert/probe record uses."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def secret_values(env: dict[str, str] | None = None) -> list[str]:
    """Return the *values* of env vars that look secret (never the names that aren't)."""
    resolved = dict(os.environ) if env is None else env
    values: list[str] = []
    for name, value in resolved.items():
        if not value:
            continue
        if SECRET_ENV_RE.search(name) or name in EXTRA_SECRET_ENV:
            values.append(value)
    return values


def scrub_secrets(text: str, env: dict[str, str] | None = None) -> str:
    """Replace every env-secret *value* appearing in ``text`` with ``***redacted***``.

    Longest-first so a secret that is a prefix of another is fully masked. Names are
    fine to log (``SIG_MUCKROCK_TOKEN`` is not itself a secret); values never are.
    """
    for value in sorted(secret_values(env), key=len, reverse=True):
        text = text.replace(value, REDACTED)
    return text


@dataclass(frozen=True)
class Alert:
    """One recorded alert: kind, severity, message, timestamp, structured detail."""

    kind: str  # e.g. "egress-budget", "keepalive", "probe"
    severity: str  # one of SEVERITIES
    message: str
    ts: str
    detail: dict[str, object] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        kind: str,
        severity: str,
        message: str,
        *,
        detail: dict[str, object] | None = None,
        now: str | None = None,
    ) -> Alert:
        if severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES} (got {severity!r})")
        return cls(
            kind=kind,
            severity=severity,
            message=message,
            ts=now or utcnow(),
            detail=dict(detail or {}),
        )

    def as_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
            "ts": self.ts,
            "detail": self.detail,
        }


class AlertLedger:
    """The append-only recorded-alert ledger (JSONL).

    Append-only like the rest of the system: rows are never rewritten; retention is
    a *truncation* of the oldest rows performed by :func:`ops.observe.prune_jsonl`,
    not an in-place edit of surviving history.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, alert: Alert) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_scrubbed_json(alert), sort_keys=True) + "\n")
        return self.path

    def read(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, object]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows


def _scrubbed_json(alert: Alert) -> dict[str, object]:
    """``alert.as_json()`` with every string value scrubbed of env-secret values."""
    raw = alert.as_json()
    return json.loads(scrub_secrets(json.dumps(raw, default=str)))


class Notifier(Protocol):
    """A notification sink. ``send`` returns True when the alert reached the sink."""

    name: str

    def send(self, alert: Alert) -> bool: ...


class LogNotifier:
    """A structured ``SIG-ALERT`` line on a stream — the free, always-on notifier."""

    name = "log"

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stderr

    def send(self, alert: Alert) -> bool:
        line = scrub_secrets(
            f"SIG-ALERT {alert.severity.upper()} {alert.kind}: {alert.message} (ts={alert.ts})"
        )
        print(line, file=self._stream)
        return True


class WebhookNotifier:
    """POSTs the alert as JSON to ``SIG_ALERT_WEBHOOK_URL`` (env-only, HG-09).

    The URL is read from the environment at send time and is **never** logged or
    written to the ledger — it may embed a credential in its path. An optional
    ``SIG_ALERT_WEBHOOK_TOKEN`` rides as a Bearer header. Delivery is best-effort:
    a failure returns False (the alert is still *recorded* in the ledger — the
    record never depends on the network).

    P35.1b (the sig-alerts disposition): when ``SIG_ALERT_WEBHOOK_IAM=1`` — set
    on the probe job once ``sig-alerts`` runs ``--no-allow-unauthenticated`` —
    the request carries TWO credentials: a Google-signed OIDC id token (the
    metadata-server `identity` endpoint, audience = the service origin) in
    ``Authorization`` for the Cloud Run front door, and the app-level
    ``SIG_ALERT_WEBHOOK_TOKEN`` in ``X-SIG-Alert-Token`` for the receiver's own
    check. Off GCP (no metadata server) an IAM-mode send returns False — an
    honest non-delivery, the ledger record still stands.
    """

    name = "webhook"

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        *,
        iam: bool | None = None,
        id_token: Callable[[str], str | None] | None = None,
    ) -> None:
        self._url = url if url is not None else os.environ.get("SIG_ALERT_WEBHOOK_URL")
        self._token = token if token is not None else os.environ.get("SIG_ALERT_WEBHOOK_TOKEN")
        if iam is None:
            iam = os.environ.get("SIG_ALERT_WEBHOOK_IAM", "").lower() in {"1", "true", "yes"}
        self._iam = iam
        self._id_token = id_token  # test seam — production resolves the metadata server

    @property
    def configured(self) -> bool:
        return bool(self._url)

    def send(self, alert: Alert) -> bool:
        if not self._url:
            return False
        body = json.dumps(
            {
                "text": scrub_secrets(f"SIG-ALERT {alert.severity}: {alert.message}"),
                "alert": _scrubbed_json(alert),
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._iam:
            origin = urllib.parse.urlsplit(self._url)
            audience = f"{origin.scheme}://{origin.netloc}"
            fetch = self._id_token or _metadata_id_token
            tok = fetch(audience)
            if not tok:
                return False  # a private service without an id token is unreachable
            headers["Authorization"] = f"Bearer {tok}"
            if self._token:
                headers["X-SIG-Alert-Token"] = self._token
        elif self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310 - operator-set URL
                return 200 <= resp.status < 300
        except Exception:  # noqa: BLE001 - best-effort delivery; the record stands
            return False


#: The Cloud Run / GCE metadata-server identity endpoint (link-local,
#: GCP-internal) — the OIDC id token a ``--no-allow-unauthenticated`` service's
#: front door requires. Off GCP the name does not resolve: ``None``.
_METADATA_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
)


def _metadata_id_token(audience: str, timeout: float = 2.0) -> str | None:
    """A Google-signed OIDC id token for the runtime service account, scoped to
    ``audience`` (the target service's origin). Returns ``None`` off-GCP."""
    url = f"{_METADATA_IDENTITY_URL}?audience={urllib.parse.quote(audience, safe='')}&format=full"
    req = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - metadata IP
            return resp.read().decode("utf-8").strip()
    except Exception:  # noqa: BLE001 - any failure means "not on GCP"
        return None


def notifiers_from_env(
    env: dict[str, str] | None = None, *, stream: TextIO | None = None
) -> list[Notifier]:
    """The notifier router: always the log sink, plus the webhook when env-configured."""
    resolved = dict(os.environ) if env is None else env
    sinks: list[Notifier] = [LogNotifier(stream)]
    if resolved.get("SIG_ALERT_WEBHOOK_URL"):
        sinks.append(WebhookNotifier())
    return sinks


def fire(alert: Alert, *, ledger: AlertLedger, notifiers: list[Notifier]) -> Alert:
    """Record ``alert`` in the ledger, then fan it out to each notifier.

    The record comes first and unconditionally — a notifier that cannot deliver
    (no webhook configured, network down, a crashing sink) never loses the alert
    and never masks the caller's own exit code. Returns the alert that was
    recorded.
    """
    ledger.record(alert)
    for notifier in notifiers:
        try:
            notifier.send(alert)
        except Exception:  # noqa: BLE001 - best-effort delivery; the record stands
            pass
    return alert


def alert_exit_code(alert: Alert | None) -> int:
    """Process exit code after firing: 0 when nothing fired, 6 when an alert did.

    Distinct from the egress budget's 5 (a *budget breach*) — 6 means "a fault was
    observed and recorded" (keepalive failure, a down service, an operator-fired
    alert).
    """
    return 0 if alert is None else 6


# --- the repo-owned sig-alerts receiver (P35.1b / G1-11) -----------------------
#
# The hosted ``sig-alerts`` Cloud Run service historically ran an inline base64
# ``python -c`` program on the movable ``sig-api:latest`` tag — unreproducible
# from the repo and a silent-roll risk. The P35.1b sweep rebuilds it digest-
# pinned on this receiver: the same request contract as the inline program,
# plus the repo's scrub-secrets discipline (an alert body may carry a leaked
# env-secret value — it is scrubbed before the log line, HG-09).

#: Byte cap on a received alert body before the log line truncates it.
RECEIVER_BODY_LIMIT = 4096


def _receiver_handler(
    token: str, emit: Callable[[str], None]
) -> type[http.server.BaseHTTPRequestHandler]:
    """Build the POST handler class for ``build_receiver_server``.

    ``token`` is the expected app-level secret (``""`` = accept unauthenticated,
    matching the pre-sweep service); it arrives as ``Authorization: Bearer`` on
    a public service or ``X-SIG-Alert-Token`` when the front door already holds
    the OIDC id token (``SIG_ALERT_WEBHOOK_IAM=1`` on the caller). ``emit``
    receives the scrubbed ``SIG-ALERT-RECEIVED`` line (the service's only
    output — Cloud Logging captures stdout).
    """

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if token:
                ok = (
                    self.headers.get("Authorization", "") == f"Bearer {token}"
                    or self.headers.get("X-SIG-Alert-Token", "") == token
                )
                if not ok:
                    self.send_response(401)
                    self.end_headers()
                    return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8", "replace")[:RECEIVER_BODY_LIMIT]
            emit(
                scrub_secrets("SIG-ALERT-RECEIVED " + json.dumps({"path": self.path, "body": body}))
            )
            self.send_response(204)
            self.end_headers()

        def log_message(self, *_args: Any) -> None:  # silence the per-request access log
            pass

    return _Handler


def build_receiver_server(
    port: int, *, token: str | None = None, emit: Callable[[str], None] = print
) -> http.server.HTTPServer:
    """A ``http.server.HTTPServer`` bound to ``0.0.0.0:<port>`` serving the
    sig-alerts POST contract. ``token`` defaults to ``SIG_ALERT_WEBHOOK_TOKEN``
    (env-only, HG-09). The caller runs ``serve_forever()`` — a test binds port
    0 and reads the real port back off ``server.server_port``.
    """
    resolved = token if token is not None else os.environ.get("SIG_ALERT_WEBHOOK_TOKEN", "")
    return http.server.HTTPServer(("0.0.0.0", port), _receiver_handler(resolved, emit))


def serve_alert_receiver(port: int | None = None, *, token: str | None = None) -> int:
    """Run the sig-alerts receiver until killed (the Cloud Run service's loop).

    The port resolves flag → ``PORT`` env → 8080; the token resolves flag →
    ``SIG_ALERT_WEBHOOK_TOKEN`` env. Returns 0 on a clean shutdown
    (KeyboardInterrupt); never returns on its own.
    """
    resolved_port = port or int(os.environ.get("PORT", "8080"))
    server = build_receiver_server(resolved_port, token=token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


__all__ = [
    "EXTRA_SECRET_ENV",
    "REDACTED",
    "SECRET_ENV_RE",
    "SEVERITIES",
    "Alert",
    "AlertLedger",
    "LogNotifier",
    "Notifier",
    "WebhookNotifier",
    "RECEIVER_BODY_LIMIT",
    "alert_exit_code",
    "build_receiver_server",
    "fire",
    "notifiers_from_env",
    "scrub_secrets",
    "secret_values",
    "serve_alert_receiver",
    "utcnow",
]
