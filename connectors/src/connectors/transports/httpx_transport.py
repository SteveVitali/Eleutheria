# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The real HTTP transport behind the politeness layer (§21.5, §26, P21.3, LD-F03).

:class:`HttpxTransport` implements :class:`connectors.net.Transport` over
``httpx``. It is the concrete network path a live run injects into
:class:`~connectors.net.PoliteFetcher`; the fetcher still owns robots-permission,
per-host rate-limiting and challenge-surfacing, so this class only has to do the
transport-level work the politeness layer cannot:

* **Retry-with-backoff on 429 / 503 / 504** honouring ``Retry-After`` (§26 Rule 3,
  SIG-INGEST-037). A transient rate-limit or gateway-timeout is *backed off and
  retried*, not treated as a bot-management challenge — this is exactly the
  Overpass etiquette (429 = slot exhaustion → back off; 504 = query too large,
  but we still back off before giving up, LD-F03 / SIG-INGEST-045h). A challenge
  status (401/403) is **never** retried and is surfaced by the fetcher.
* **Conditional GET / ETag** (SIG-INGEST-017): the last ``ETag`` (and
  ``Last-Modified``) seen per URL is remembered and replayed as ``If-None-Match``
  / ``If-Modified-Since`` so an unchanged resource returns 304 and no bytes are
  re-downloaded — the transport serves the previously-captured body back on 304.
* **No circumvention (§26 Rule 4, SIG-INGEST-037).** The transport never rotates
  identity, never solves a challenge, and refuses to be configured with any
  enumerated circumvention technique (:func:`policy.crawler.assert_no_circumvention`).
  It follows redirects only within the same registrable behaviour ``httpx``
  provides and never disables TLS verification.

The transport is **transport-only**: it opens sockets, so it is never used inside
the network-isolated post-capture context (:mod:`connectors.isolation`) — only
``fetch()`` egresses (SIG-INGEST-002).
"""

from __future__ import annotations

import email.utils
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

import httpx
from policy.crawler import assert_no_circumvention

from ..net import RobotsResult, now_utc
from ..stages import FetchResult

#: Default connect/read timeout for a single request (seconds). Overpass queries
#: carry their own ``[timeout:…]`` server-side; this bounds the client wait.
DEFAULT_TIMEOUT_SECONDS = 180.0

#: A conservative default cap on backoff retries for a single request.
DEFAULT_MAX_RETRIES = 3

#: The statuses that mean "back off and retry", not "content" and not "challenge"
#: (§26 Rule 3; Overpass 429/504, SIG-INGEST-045h; 503 Service Unavailable).
RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 503, 504})

#: A conservative fallback backoff (seconds) when a retryable status carries no
#: ``Retry-After`` header — grows with the attempt number.
DEFAULT_BACKOFF_SECONDS = 1.0

#: The absolute cap on any single backoff wait (seconds), so a hostile or broken
#: ``Retry-After`` can never wedge a run for hours.
MAX_BACKOFF_SECONDS = 300.0


def default_user_agent(homepage: str = "https://sig-project.org") -> str:
    """The fallback crawler UA when policy supplies none (``SIG/<version> (+url)``).

    :class:`~connectors.net.PoliteFetcher` normally builds the UA from the
    connector identity; this is the standalone fallback the spec names
    (``SIG/<version> (+https://<homepage>)``) for a transport used without a
    fetcher (e.g. robots pre-flight).
    """
    from .. import __version__

    return f"SIG/{__version__} (+{homepage})"


@dataclass
class _CachedResponse:
    """The validators + body remembered per URL for conditional GET (ETag)."""

    etag: str | None
    last_modified: str | None
    body: bytes
    media_type: str
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)


class HttpxTransport:
    """A :class:`connectors.net.Transport` over ``httpx`` (the live network path).

    Construct once per run and inject into :class:`~connectors.net.PoliteFetcher`.
    ``sleep`` is injectable so the backoff behaviour is deterministically testable
    without real waits, and ``client`` accepts a pre-built :class:`httpx.Client`
    (a test passes one wired to :class:`httpx.MockTransport`, so no socket opens).
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        sleep: Callable[[float], None] | None = None,
        circumvention_techniques: Iterable[str] = (),
        conditional_get: bool = True,
    ) -> None:
        # Rule 4 (SIG-INGEST-037): a circumvention technique configured on the
        # transport is a hard error — the live path never defeats a challenge.
        for technique in circumvention_techniques:
            assert_no_circumvention(technique)
        # follow_redirects is enabled (a 301/302 is normal), but identity is never
        # rotated and TLS verification is never disabled (Rule 4).
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._owns_client = client is None
        self._max_retries = max(0, int(max_retries))
        self._sleep = sleep or time.sleep
        self._conditional_get = conditional_get
        self._cache: dict[str, _CachedResponse] = {}
        #: Backoff waits taken, in order — surfaced as crawler-conduct evidence in
        #: the fetch record (RISK-P21-04).
        self.rate_limit_events: list[dict[str, object]] = []

    # -- Transport protocol ---------------------------------------------------
    def robots(self, robots_url: str) -> RobotsResult:
        """Retrieve robots.txt; ``None`` text means unretrievable (SIG-INGEST-012)."""
        try:
            resp = self._client.get(robots_url, headers={"User-Agent": default_user_agent()})
        except httpx.HTTPError:
            # Unretrievable robots.txt is NOT an implied grant — the fetcher fails
            # closed on a None text (SIG-INGEST-012).
            return RobotsResult(text=None)
        if resp.status_code != 200:
            return RobotsResult(text=None)
        return RobotsResult(text=resp.text)

    def request(
        self, url: str, *, user_agent: str, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        """Execute one GET with backoff-retry + conditional GET (never circumvents).

        The ``user_agent`` and any per-request ``headers`` (e.g. an
        ``Authorization: Bearer`` credential riding the shared seam, §23.5) come
        from the fetcher. A challenge status (401/403) is returned unretried for
        the fetcher to surface (SIG-INGEST-013); a 429/503/504 is backed off and
        retried up to ``max_retries`` (§26 Rule 3).
        """
        request_headers: dict[str, str] = {"User-Agent": user_agent}
        if headers:
            request_headers.update(headers)
        cached = self._cache.get(url)
        if self._conditional_get and cached is not None:
            if cached.etag is not None:
                request_headers["If-None-Match"] = cached.etag
            if cached.last_modified is not None:
                request_headers["If-Modified-Since"] = cached.last_modified

        attempt = 0
        while True:
            resp = self._client.get(url, headers=request_headers)
            status = resp.status_code
            if status in RETRYABLE_STATUSES and attempt < self._max_retries:
                wait = self._retry_after_seconds(resp) or _bounded(
                    DEFAULT_BACKOFF_SECONDS * (2**attempt)
                )
                self.rate_limit_events.append(
                    {
                        "url": url,
                        "status": status,
                        "action": "back_off",
                        "wait_seconds": wait,
                        "attempt": attempt + 1,
                    }
                )
                self._sleep(wait)
                attempt += 1
                continue
            return self._to_fetch_result(url, resp)

    # -- helpers --------------------------------------------------------------
    def _to_fetch_result(self, url: str, resp: httpx.Response) -> FetchResult:
        response_headers = {k: v for k, v in resp.headers.items()}
        # A 304 means the previously-captured body is still current: serve it back
        # so the post-capture stages address the same bytes (SIG-INGEST-017/003).
        if resp.status_code == 304 and (cached := self._cache.get(url)) is not None:
            return FetchResult(
                url=url,
                status=304,
                body=cached.body,
                media_type=cached.media_type,
                retrieved_at=now_utc(),
                headers=response_headers,
            )
        media_type = _media_type(resp)
        body = resp.content
        if self._conditional_get and resp.status_code == 200:
            self._cache[url] = _CachedResponse(
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
                body=body,
                media_type=media_type,
                status=200,
                headers=response_headers,
            )
        return FetchResult(
            url=url,
            status=resp.status_code,
            body=body,
            media_type=media_type,
            retrieved_at=now_utc(),
            headers=response_headers,
        )

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response) -> float | None:
        """Parse ``Retry-After`` (delta-seconds or HTTP-date) into a bounded wait."""
        value = resp.headers.get("Retry-After")
        if not value:
            return None
        value = value.strip()
        if value.isdigit():
            return _bounded(float(value))
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed is None:
            return None
        delta = (parsed - now_utc()).total_seconds()
        return _bounded(delta) if delta > 0 else 0.0

    def close(self) -> None:
        """Close the underlying client if this transport created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpxTransport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _media_type(resp: httpx.Response) -> str:
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return content_type.split(";", 1)[0].strip() or "application/octet-stream"


def _bounded(seconds: float) -> float:
    return max(0.0, min(float(seconds), MAX_BACKOFF_SECONDS))


__all__ = [
    "DEFAULT_BACKOFF_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpxTransport",
    "MAX_BACKOFF_SECONDS",
    "RETRYABLE_STATUSES",
    "default_user_agent",
]
