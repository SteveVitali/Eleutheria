# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.13 / SIG-API-009 — enforced per-client rate limits on the public read API.

The §37.4 anonymous tier is rate-limited (SIG-API-011); this module is the
enforcement half of the API exposure posture: a **per-client token bucket**
of 30 requests per 60 seconds with burst 10 (the K3 §5.6 / D-K3-6 [B-30]
decision — ``30/min, burst 10; no Cloud Armor now``). The limiter is
**in-process**: D-K3-6 stays open and no managed edge layer (Cloud Armor) is
introduced — a paid edge would break the zero-cost posture (SIG-STORE-003).

Contract on the wire:

* **Headers on every response** — ``RateLimit-Limit``, ``RateLimit-Remaining``
  and ``RateLimit-Reset`` (seconds until the bucket is full again) are stamped
  on every response the middleware sees, including the rejected one and every
  error path beneath it.
* **A rejected burst returns the documented rejection** — HTTP ``429`` with
  ``Retry-After``, the app's typed ``{detail, code, **extra}`` body shape
  (``code: "rate_limited"``), and an HTML page when the client asked for the
  no-JS representation (``format=html`` or ``Accept: text/html`` — the K3
  §5.6 / DR-C4-10 rule).
* **Client key** — the client address the trusted edge appends to
  ``Forwarded``/``X-Forwarded-For``, never the raw peer and never a raw
  client-supplied chain entry (the C4 NEW-16 intake lesson, K3 §5.6).
  ``SIG_API_TRUSTED_PROXY_HOPS`` declares how many forwarding hops stand
  between the public edge and this process: the Nth-from-right chain entry is
  what the outermost trusted proxy observed; a shorter chain falls back to
  the direct peer. The hosted posture behind the external Google load
  balancer is ``2`` (the LB appends ``<client-ip>, <lb-ip>``).

The middleware mounts only when a posture is set — the code ships **dark**
ahead of the hosted-enforcement flip (OM-20 / OM-19): ``off`` (default) mounts
nothing at all, ``advise`` stamps headers and keeps the accounting without
rejecting (the "defined" half), ``enforce`` additionally rejects over-limit
bursts (the "enforced" half — the named mutation).
"""

from __future__ import annotations

import ipaddress
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from starlette.responses import HTMLResponse, JSONResponse, Response

#: The documented posture (SIG-API-009): 30 requests per 60-second window per
#: client, burst capacity 10 (K3 §5.6, D-K3-6 [B-30]).
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_BURST = 10

#: Posture env names — a deploy sets them (the OM-20 flip), never per-request
#: derived state. ``SIG_API_RATE_LIMIT``: ``off`` (default, nothing mounted) ·
#: ``advise`` (headers + accounting, never rejects — the "defined" half) ·
#: ``enforce`` (headers + the 429 rejection — the "enforced" half).
#: ``SIG_API_TRUSTED_PROXY_HOPS``: how many trusted edge hops append the
#: client chain (0 = the direct peer only; 2 behind the Google external LB).
ENV_RATE_LIMIT_POSTURE = "SIG_API_RATE_LIMIT"
ENV_TRUSTED_PROXY_HOPS = "SIG_API_TRUSTED_PROXY_HOPS"

#: The stamped header names (IETF draft-ietf-httpapi-ratelimit-headers shape:
#: limit, remaining, reset).
HEADER_LIMIT = b"ratelimit-limit"
HEADER_REMAINING = b"ratelimit-remaining"
HEADER_RESET = b"ratelimit-reset"
HEADER_RETRY_AFTER = b"retry-after"
_RATE_HEADERS = {HEADER_LIMIT, HEADER_REMAINING, HEADER_RESET}

POSTURES = ("off", "advise", "enforce")

#: Bounded memory: bucket state is per-process and pruned — an idle client
#: forgets after this TTL (its bucket would have refilled anyway), and the
#: table refuses unbounded growth (the oldest entries go first).
_BUCKET_TTL_SECONDS = 3600.0
_MAX_BUCKETS = 50_000


@dataclass(frozen=True)
class RateLimitConfig:
    """The limiter's configured posture for one process."""

    posture: str = "off"
    trusted_proxy_hops: int = 0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RateLimitConfig:
        env = os.environ if env is None else env
        posture = (env.get(ENV_RATE_LIMIT_POSTURE) or "off").strip().lower()
        if posture not in POSTURES:
            # Fail closed and loud: a posture typo must never silently un-limit
            # the public surface.
            raise ValueError(
                f"{ENV_RATE_LIMIT_POSTURE}={posture!r} is not one of {POSTURES} — "
                "the public read API refuses to boot under an unknown rate-limit posture"
            )
        raw_hops = (env.get(ENV_TRUSTED_PROXY_HOPS) or "0").strip()
        try:
            hops = int(raw_hops)
        except ValueError:
            raise ValueError(
                f"{ENV_TRUSTED_PROXY_HOPS}={raw_hops!r} is not an integer — "
                "the public read API refuses to boot under an unknown proxy-hop count"
            ) from None
        # Bounded so a typo can never unbounded-walk a header chain (same bound
        # as the intake receiver's gate).
        return cls(posture=posture, trusted_proxy_hops=max(0, min(hops, 8)))


@dataclass(frozen=True)
class LimitDecision:
    """One bucket read: whether a slot was consumed and the header values."""

    allowed: bool
    remaining: int
    #: Seconds until the bucket is full again (the ``RateLimit-Reset`` value).
    reset_seconds: int
    #: Seconds until at least one more request is allowed (``Retry-After`` on
    #: a rejection).
    retry_after_seconds: int


class TokenBucketLimiter:
    """Per-client token buckets: ``rate`` refills/sec up to ``burst`` capacity.

    In-memory only — per Cloud Run instance, never persisted (SIG-STORE-003's
    zero-cost posture: no shared store, no managed edge).
    """

    def __init__(
        self,
        *,
        limit: int = RATE_LIMIT_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
        burst: int = RATE_LIMIT_BURST,
    ) -> None:
        self._limit = limit
        self._burst = burst
        self._rate = limit / float(window_seconds)
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, ts)

    def _evict(self, now: float) -> None:
        """Bound the table: drop idle-over-TTL keys, then the oldest slice."""
        if len(self._buckets) <= _MAX_BUCKETS:
            return
        stale = [k for k, (_, ts) in self._buckets.items() if now - ts > _BUCKET_TTL_SECONDS]
        for k in stale:
            del self._buckets[k]
        if len(self._buckets) > _MAX_BUCKETS:
            oldest = sorted(self._buckets, key=lambda k: self._buckets[k][1])
            for k in oldest[: len(self._buckets) - _MAX_BUCKETS]:
                del self._buckets[k]

    def check(self, key: str, *, now: float | None = None) -> LimitDecision:
        """Consume one slot for ``key``; the decision is honest either way."""
        moment = time.monotonic() if now is None else now
        self._evict(moment)
        tokens, ts = self._buckets.get(key, (float(self._burst), moment))
        tokens = min(float(self._burst), tokens + (moment - ts) * self._rate)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._buckets[key] = (tokens, moment)
        return LimitDecision(
            allowed=allowed,
            remaining=max(0, int(tokens)),
            reset_seconds=int((float(self._burst) - tokens) / self._rate) + 1,
            retry_after_seconds=(0 if allowed else max(1, int((1.0 - tokens) / self._rate) + 1)),
        )


def _normalize_ip(host: str) -> str:
    """Canonicalise one IP literal for the bucket key — compressed IPv6,
    normalised IPv4; bracketed ``[v6]:port`` / ``v4:port`` forms strip the
    port. Unparseable text lowercases (still a consistent, bounded key)."""
    h = host.strip()
    if h.startswith("[") and "]" in h:
        h = h[1 : h.index("]")]
    elif h.count(":") == 1 and h.rsplit(":", 1)[1].isdigit():
        h = h.rsplit(":", 1)[0]
    try:
        return str(ipaddress.ip_address(h))
    except ValueError:
        return h.lower()[:64]


def _scope_header(scope: dict, name: bytes) -> str:
    for k, v in scope.get("headers", []):
        if k.lower() == name:
            return v.decode("latin-1")
    return ""


def _forwarded_chain(scope: dict) -> list[str]:
    """The left-to-right client→proxy address chain from forwarding headers —
    RFC 7239 ``Forwarded: for=`` first, else ``X-Forwarded-For``. Each entry
    is what a hop *claimed*; only the trusted-hop-sliced tail is ever used."""
    fwd = _scope_header(scope, b"forwarded")
    if fwd:
        chain: list[str] = []
        for element in fwd.split(","):
            for piece in element.split(";"):
                key, _, val = piece.partition("=")
                if key.strip().lower() == "for" and val.strip():
                    chain.append(val.strip().strip('"'))
        return chain
    xff = _scope_header(scope, b"x-forwarded-for")
    if xff:
        return [p.strip() for p in xff.split(",") if p.strip()]
    return []


def client_key(scope: dict, trusted_proxy_hops: int = 0) -> str:
    """The edge-normalised client address the bucket keys on (K3 §5.6).

    ``trusted_proxy_hops = N`` declares how many forwarding hops the operator
    has placed between the public edge and this process. Each trusted hop
    appends the *peer it observed*, so the Nth-from-right entry of the
    ``Forwarded``/``X-Forwarded-For`` chain is what the outermost trusted
    proxy saw — the real client (behind the Google external LB the LB appends
    ``<client-ip>, <lb-ip>``, so ``N=2``). Entries further left are
    client-claimed and ignored; a chain shorter than N (or absent) falls back
    to the direct peer — a raw client-supplied header is **never** trusted on
    its own (C4 NEW-16).
    """
    if trusted_proxy_hops > 0:
        chain = _forwarded_chain(scope)
        if len(chain) >= trusted_proxy_hops:
            return _normalize_ip(chain[len(chain) - trusted_proxy_hops])
    peer = scope.get("client")
    host = peer[0] if peer else ""
    return _normalize_ip(host) if host else "unknown"


def _wants_html(scope: dict) -> bool:
    """The no-JS rule mirrored at middleware level (K3 §5.6 / DR-C4-10):
    explicit ``format=html`` wins, else a browser ``Accept: text/html``."""
    query = scope.get("query_string", b"")
    params = {
        p.split(b"=", 1)[0]: p.split(b"=", 1)[1] if b"=" in p else b""
        for p in query.split(b"&")
        if p
    }
    fmt = params.get(b"format", b"").decode("latin-1")
    accept = _scope_header(scope, b"accept")
    return fmt == "html" or (not fmt and "text/html" in accept)


_REJECTION_HTML = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Too many requests</title></head><body>"
    "<h1>Too many requests</h1>"
    "<p>The public read API allows {limit} requests per {window} seconds per "
    "client (burst {burst}). Your client exceeded the limit — wait for the "
    "reset window shown in the <code>RateLimit-Reset</code> header and retry.</p>"
    "</body></html>"
)


def _rate_headers(decision: LimitDecision) -> list[tuple[bytes, bytes]]:
    return [
        (HEADER_LIMIT, str(RATE_LIMIT_REQUESTS).encode()),
        (HEADER_REMAINING, str(decision.remaining).encode()),
        (HEADER_RESET, str(decision.reset_seconds).encode()),
    ]


class RateLimitMiddleware:
    """Pure-ASGI per-client limiter + the limit/remaining/reset headers.

    Stamps the three ``RateLimit-*`` headers on every response it sees —
    success, error, and its own 429 rejection alike. In ``advise`` posture the
    accounting runs and headers are honest but nothing is ever rejected; in
    ``enforce`` posture an over-limit burst is refused with the documented
    429 + ``Retry-After`` body (and an HTML page when the client asked for
    HTML). Mounts inside :class:`BasisLabelMiddleware` so a rejection still
    carries the basis/provenance stamps.
    """

    def __init__(
        self,
        app: Any,
        *,
        limiter: TokenBucketLimiter | None = None,
        enforce: bool = True,
        trusted_proxy_hops: int = 0,
    ) -> None:
        self.app = app
        self.limiter = limiter or TokenBucketLimiter()
        self.enforce = enforce
        self.trusted_proxy_hops = trusted_proxy_hops

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        decision = self.limiter.check(client_key(scope, self.trusted_proxy_hops))
        if self.enforce and not decision.allowed:
            await self._reject(scope, receive, send, decision)
            return

        started = False

        async def send_stamped(message: dict) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() not in _RATE_HEADERS
                ]
                headers.extend(_rate_headers(decision))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_stamped)
        except Exception:
            # An unhandled failure is still an answer this service gives —
            # when nothing was started yet, emit the 500 ourselves so the
            # rate headers ride it too. ServerErrorMiddleware's own send
            # wrapper sees response_started and only re-raises; the exception
            # still propagates for logging/monitoring.
            if not started:
                response = JSONResponse(
                    {"detail": "internal server error", "code": "internal_error"},
                    status_code=500,
                    headers={
                        "ratelimit-limit": str(RATE_LIMIT_REQUESTS),
                        "ratelimit-remaining": str(decision.remaining),
                        "ratelimit-reset": str(decision.reset_seconds),
                    },
                )
                await response(scope, receive, send)
            raise

    async def _reject(
        self, scope: dict, receive: Callable, send: Callable, decision: LimitDecision
    ) -> None:
        """The documented rejection: 429 + Retry-After + the rate headers,
        JSON or HTML per the no-JS negotiation rule."""
        retry = max(1, decision.retry_after_seconds)
        headers = {
            "ratelimit-limit": str(RATE_LIMIT_REQUESTS),
            "ratelimit-remaining": "0",
            "ratelimit-reset": str(decision.reset_seconds),
            "retry-after": str(retry),
        }
        response: Response
        if _wants_html(scope):
            response = HTMLResponse(
                _REJECTION_HTML.format(
                    limit=RATE_LIMIT_REQUESTS,
                    window=RATE_LIMIT_WINDOW_SECONDS,
                    burst=RATE_LIMIT_BURST,
                ),
                status_code=429,
                headers=headers,
            )
        else:
            response = JSONResponse(
                {
                    "detail": "rate limit exceeded — the public read API allows "
                    f"{RATE_LIMIT_REQUESTS} requests per "
                    f"{RATE_LIMIT_WINDOW_SECONDS} seconds per client "
                    f"(burst {RATE_LIMIT_BURST}); retry after the reset window",
                    "code": "rate_limited",
                    "limit": RATE_LIMIT_REQUESTS,
                    "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                    "burst": RATE_LIMIT_BURST,
                    "retry_after_seconds": retry,
                },
                status_code=429,
                headers=headers,
            )
        await response(scope, receive, send)
