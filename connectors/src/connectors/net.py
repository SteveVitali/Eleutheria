# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared rate-limiter and robots layer (§21.5, SIG-INGEST-011/012/013).

A single politeness layer sits between every connector and the network
(SIG-INGEST-011): per-host request budgets, a documented crawler UA carrying a
contact URL, and crawl-delay honoring. **Connectors hold no HTTP client of their
own** — they are handed a :class:`PoliteFetcher` on the run context and every
egress passes through it.

Three rules are enforced here rather than left to prose:

* **Robots is mandatory (SIG-INGEST-012).** Where ``robots.txt`` cannot be
  retrieved, crawl permission is treated as *not granted* and the fetcher refuses
  to run (:class:`RobotsUnretrievable`), via :func:`policy.crawler.robots_permits`.
* **No challenge-defeating crawler (SIG-INGEST-013 / Rule 4).** The fetcher never
  solves a bot-management challenge or rotates identity: a persistent challenge is
  surfaced as a :class:`ChallengeEncountered` outcome for the disappearance layer
  to record, never worked around. Configuring a circumvention technique is a hard
  error via :func:`policy.crawler.assert_no_circumvention`.
* **Politeness (SIG-INGEST-011 / Rule 3).** A per-host :class:`RateLimiter`
  enforces a minimum interval — the source's crawl-delay, or a conservative
  default — so SIG never burdens a small civic host.

The layer is transport-agnostic: it drives a :class:`Transport` (robots retrieval
plus request execution) injected at construction, so it is fully testable without
real sockets and a later ticket can plug a real HTTP transport in unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from policy.crawler import assert_no_circumvention, robots_permits

from .stages import FetchResult

#: The contact URL the crawler UA carries (Crawler Conduct Rule 1, SIG-INGEST-011).
DEFAULT_CONTACT_URL = "https://sig-project.org/crawler"

#: Conservative default minimum seconds between requests to one host when the
#: source publishes no crawl-delay (SIG-INGEST-011 / Rule 3).
DEFAULT_CRAWL_DELAY_SECONDS = 1.0


class RobotsUnretrievable(Exception):
    """Raised when robots.txt cannot be retrieved — permission is not granted."""


class RobotsDisallowed(Exception):
    """Raised when robots.txt disallows the UA from fetching a URL."""


class ChallengeEncountered(Exception):
    """Raised when a source returns a bot-management challenge.

    The fetcher never defeats it (SIG-INGEST-013); the run records the source as
    facing a persistent challenge (a disappearance datum), it does not retry.
    """


@dataclass(frozen=True)
class RobotsResult:
    """The outcome of retrieving robots.txt for a host."""

    #: ``None`` means unretrievable — treated as *not granted* (SIG-INGEST-012).
    text: str | None


@runtime_checkable
class Transport(Protocol):
    """The low-level network transport the fetcher drives (injected, testable)."""

    def robots(self, robots_url: str) -> RobotsResult: ...

    def request(self, url: str, *, user_agent: str) -> FetchResult: ...


def user_agent(name: str, version: str, contact_url: str = DEFAULT_CONTACT_URL) -> str:
    """The documented crawler UA, carrying a contact URL (Rule 1, SIG-INGEST-011)."""
    return f"{name}/{version} (+{contact_url})"


def _host(url: str) -> str:
    return urlsplit(url).netloc


def _robots_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


class RateLimiter:
    """Per-host minimum-interval limiter (SIG-INGEST-011 / Rule 3).

    Tracks the last request time per host and blocks until the host's minimum
    interval has elapsed. ``now`` / ``sleep`` are injectable so the politeness
    behaviour is deterministically testable without real time.
    """

    def __init__(
        self,
        *,
        default_delay: float = DEFAULT_CRAWL_DELAY_SECONDS,
        now: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        import time

        self._default_delay = default_delay
        self._now = now or time.monotonic
        self._sleep = sleep or time.sleep
        self._last: dict[str, float] = {}
        self._delays: dict[str, float] = {}

    def set_host_delay(self, host: str, delay: float) -> None:
        """Pin a host's crawl-delay (from robots.txt or the registry)."""
        self._delays[host] = max(delay, 0.0)

    def delay_for(self, host: str) -> float:
        return self._delays.get(host, self._default_delay)

    def acquire(self, host: str) -> float:
        """Block until the host's budget allows a request; return the wait taken."""
        delay = self.delay_for(host)
        last = self._last.get(host)
        waited = 0.0
        now = self._now()
        if last is not None:
            elapsed = now - last
            if elapsed < delay:
                waited = delay - elapsed
                self._sleep(waited)
                now = self._now()
        self._last[host] = now
        return waited


class PoliteFetcher:
    """The shared fetch layer every connector egresses through (SIG-INGEST-011).

    Constructed once per run with the connector identity (for the UA) and a
    transport. On first contact with a host it retrieves and caches robots.txt,
    refusing to run if it is unretrievable (SIG-INGEST-012) and disallowing URLs
    robots forbids; it then rate-limits per host before each request and returns
    the fetched bytes as a :class:`connectors.stages.FetchResult`.
    """

    def __init__(
        self,
        *,
        connector_name: str,
        connector_version: str,
        transport: Transport,
        contact_url: str = DEFAULT_CONTACT_URL,
        rate_limiter: RateLimiter | None = None,
        circumvention_techniques: Iterable[str] = (),
    ) -> None:
        # A crawler that defeats challenges MUST NOT exist (SIG-INGEST-013): a
        # circumvention technique configured on the fetcher is a hard error.
        for technique in circumvention_techniques:
            assert_no_circumvention(technique)
        self._ua = user_agent(connector_name, connector_version, contact_url)
        self._transport = transport
        self._limiter = rate_limiter or RateLimiter()
        self._robots: dict[str, RobotFileParser] = {}

    @property
    def user_agent_string(self) -> str:
        return self._ua

    def _ensure_robots(self, host: str, sample_url: str) -> RobotFileParser:
        if host in self._robots:
            return self._robots[host]
        result = self._transport.robots(_robots_url(sample_url))
        # An unretrievable robots.txt is not an implied grant (SIG-INGEST-012).
        if not robots_permits(None if result.text is None else True):
            raise RobotsUnretrievable(
                f"robots.txt for {host!r} is unretrievable; crawl permission is "
                "NOT granted and the connector refuses to run (SIG-INGEST-012)."
            )
        parser = RobotFileParser()
        parser.parse((result.text or "").splitlines())
        self._robots[host] = parser
        crawl_delay = parser.crawl_delay(self._ua) or parser.crawl_delay("*")
        if crawl_delay is not None:
            self._limiter.set_host_delay(host, float(crawl_delay))
        return parser

    def can_fetch(self, url: str) -> bool:
        """Whether robots.txt permits the UA to fetch ``url`` (refuses if absent)."""
        host = _host(url)
        parser = self._ensure_robots(host, url)
        return parser.can_fetch(self._ua, url)

    def fetch(self, url: str) -> FetchResult:
        """Fetch ``url`` politely: robots-checked, rate-limited, UA-identified.

        Raises :class:`RobotsUnretrievable` if robots.txt is unavailable,
        :class:`RobotsDisallowed` if it forbids the URL, and
        :class:`ChallengeEncountered` on a bot-management challenge (never
        defeated — SIG-INGEST-013).
        """
        host = _host(url)
        if not self.can_fetch(url):
            raise RobotsDisallowed(
                f"robots.txt disallows {self._ua!r} from fetching {url!r} (Rule 2)."
            )
        self._limiter.acquire(host)
        result = self._transport.request(url, user_agent=self._ua)
        if _is_challenge(result):
            raise ChallengeEncountered(
                f"{url!r} returned a bot-management challenge (status {result.status}); "
                "SIG does not defeat challenges (SIG-INGEST-013) — recorded, not retried."
            )
        return result


#: HTTP statuses that indicate a bot-management challenge rather than content.
_CHALLENGE_STATUSES: frozenset[int] = frozenset({401, 403, 429})


def _is_challenge(result: FetchResult) -> bool:
    # A 401/403/429 is treated conservatively as a bot-management challenge: SIG
    # surfaces it as a disappearance datum rather than defeating it (SIG-INGEST-013).
    return result.status in _CHALLENGE_STATUSES


def now_utc() -> datetime:
    """The retrieval timestamp a fetch records (UTC, per SIG-EVID-018)."""
    return datetime.now(UTC)


__all__ = [
    "ChallengeEncountered",
    "DEFAULT_CONTACT_URL",
    "DEFAULT_CRAWL_DELAY_SECONDS",
    "PoliteFetcher",
    "RateLimiter",
    "RobotsDisallowed",
    "RobotsResult",
    "RobotsUnretrievable",
    "Transport",
    "now_utc",
    "user_agent",
]
