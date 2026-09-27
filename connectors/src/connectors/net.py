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

* **Robots is probed and recorded, never enforced (SIG-INGEST-012, as amended
  by ADR-087 and superseded in its enforcement by ADR-088 / GL-GATE-08).**
  Every host's ``robots.txt`` is still retrieved once per run and the
  RFC 9309 §2.3.1.4 access-result split is still recorded per host —
  ``retrieved`` (a policy governs), ``no_policy_4xx`` (a 4xx answer means no
  policy exists), ``unretrievable`` (connection failure / 5xx / 429) — via
  :func:`policy.crawler.robots_access_permits`. Under GL-GATE-08 the operator
  accepted disregarding robots entirely: a ``Disallow`` verdict — and the
  RFC-assumed disallow of an *unretrievable* policy — **no longer refuses**
  the fetch. Instead the fetch proceeds and the record marks it
  ``robots_disregarded`` (:attr:`PoliteFetcher.robots_disregarded`, the fetch
  record's field of the same name), so a claim's provenance says the fetch
  ignored a refusal. The classes :class:`RobotsUnretrievable` /
  :class:`RobotsDisallowed` are retained for record-vocabulary compatibility —
  pre-P26.17 fetch records name them — but ``PoliteFetcher`` never raises
  them.
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

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from policy.crawler import assert_no_circumvention, robots_access_permits

from .api_allowlist import api_allow_reason
from .stages import FetchResult

#: The contact URL the UA carries (Crawler Conduct Rule 1, SIG-INGEST-011). The
#: path avoids the token "crawler": some API WAFs (e.g. the Overpass front-end)
#: reject any User-Agent containing it with HTTP 406 (ADR-083 / P25 live finding).
DEFAULT_CONTACT_URL = "https://sig-project.org/data-collection"

#: Conservative default minimum seconds between requests to one host when the
#: source publishes no crawl-delay (SIG-INGEST-011 / Rule 3).
DEFAULT_CRAWL_DELAY_SECONDS = 1.0


class RobotsUnretrievable(Exception):
    """Raised when robots.txt is *unavailable* — permission is not granted.

    "Unavailable" means the retrieval failed at the transport level (connection
    error, timeout, redirect exhaustion) or the server answered 5xx/429
    (SIG-INGEST-012, RFC 9309 §2.3.1.4). A 4xx answer never raises this: it
    means no policy exists, so access is unrestricted (ADR-087).

    Retained for record-vocabulary compatibility (pre-P26.17 fetch records and
    the ``politeness_refusal`` run-row outcome name it) and for non-standard
    fetcher implementations: under GL-GATE-08 / ADR-088 ``PoliteFetcher``
    itself never raises it — an unretrievable policy is recorded as the
    ``unretrievable`` per-host outcome and the fetch is attempted anyway
    (marked ``robots_disregarded``).
    """


class RobotsDisallowed(Exception):
    """Raised when robots.txt disallows the UA from fetching a URL.

    Retained for record-vocabulary compatibility (pre-P26.17 fetch records name
    it) and for non-standard fetcher implementations: under GL-GATE-08 /
    ADR-088 ``PoliteFetcher`` itself never raises it — a ``Disallow`` verdict
    is recorded and the fetch proceeds marked ``robots_disregarded``.
    """


class ChallengeEncountered(Exception):
    """Raised when a source returns a bot-management challenge.

    The fetcher never defeats it (SIG-INGEST-013); the run records the source as
    facing a persistent challenge (a disappearance datum), it does not retry.

    ``status`` carries the HTTP status that triggered it (401/403/429) so a
    quota-metered sweep can tell a rate-limit wall (429) apart from an auth
    challenge (401/403) and stop cleanly on the former without re-probing the
    exhausted window (the recorded rate-limit lesson, P26.19).
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        #: The HTTP status that produced the challenge (``None`` if unknown).
        self.status = status


@dataclass(frozen=True)
class RobotsResult:
    """The outcome of retrieving robots.txt for a host.

    Two signals are kept distinct (RFC 9309 §2.3.1.4 / ADR-087): ``text`` is the
    policy body when one was retrieved (2xx), and ``status`` is the HTTP status
    of the robots response when the transport reached a server — ``None`` for a
    connection-level failure (timeout, DNS, redirect exhaustion). ``text=None``
    *with* a 4xx ``status`` means "no policy exists" (unrestricted); with a
    5xx/429 or no ``status`` it means "unavailable" (not granted).
    """

    #: ``None`` means no policy body was retrieved — the ``status`` decides
    #: whether that is "no policy exists" (4xx) or "unavailable" (else).
    text: str | None
    #: The HTTP status of the robots response; ``None`` on connection failure.
    status: int | None = None


@runtime_checkable
class Transport(Protocol):
    """The low-level network transport the fetcher drives (injected, testable).

    ``request`` accepts optional per-request ``headers`` (default none) so an
    authenticated source (e.g. MuckRock's Bearer-JWT data endpoints, §23.5) can
    ride the single shared egress seam rather than opening its own HTTP client
    (SIG-INGEST-011). Sources that need no auth ignore it.
    """

    def robots(self, robots_url: str) -> RobotsResult: ...

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult: ...


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
        """Pin a host's crawl-delay (from robots.txt or the registry).

        Ratchets UP only: the strictest reviewed floor wins — a pinned API
        budget (``rate_limit_per_min`` on the target row, P26.11) is never
        lowered by a shorter robots crawl-delay, and robots can only demand
        slower. Politeness always honours the maximum declared delay.
        """
        self._delays[host] = max(float(delay), self._delays.get(host, 0.0), 0.0)

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
    transport. On first contact with a host it retrieves and caches robots.txt
    and records the RFC 9309 §2.3.1.4 outcome per host (ADR-087). Under
    GL-GATE-08 / ADR-088 the verdict is **probed and recorded, never
    enforced**: a ``Disallow`` verdict or an unretrievable policy no longer
    refuses the fetch — the URL is fetched anyway and the fetch is marked
    ``robots_disregarded`` so provenance says the refusal was ignored. It then
    rate-limits per host before each request and returns the fetched bytes as
    a :class:`connectors.stages.FetchResult`.
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
        #: Auditable conduct decisions (ADR-083): one entry per fetch recording
        #: whether robots (CRAWL) or the API allow-list (API) governed it.
        self.conduct_decisions: list[dict[str, str]] = []
        #: Per-host robots.txt retrieval outcomes for the audit trail (ADR-087):
        #: ``host -> {"robots_url", "status", "outcome"}`` where ``outcome`` is
        #: ``"retrieved"`` (a policy governs), ``"no_policy_4xx"`` (RFC 9309
        #: §2.3.1.4 — the host answered 4xx, no policy exists, unrestricted), or
        #: ``"unretrievable"`` (connection failure / 5xx / 429 — not granted).
        self.robots_outcomes: dict[str, dict[str, Any]] = {}
        #: Per-URL audit rows for fetches that proceeded despite a non-grant
        #: (GL-GATE-08 / ADR-088): ``{"url", "host", "verdict"}`` where verdict
        #: is ``"disallowed"`` (a retrieved policy forbids the URL) or
        #: ``"unretrievable"`` (no policy could be obtained — the RFC-assumed
        #: disallow). The live runner writes these into the fetch record's
        #: ``robots_disregarded`` field so a claim's provenance says the fetch
        #: ignored a refusal.
        self.robots_disregarded: list[dict[str, str]] = []

    @property
    def user_agent_string(self) -> str:
        return self._ua

    def set_host_delay(self, host: str, delay: float) -> None:
        """Pin a host's minimum request interval (seconds).

        A reviewed API budget riding the target row (``rate_limit_per_min`` —
        e.g. OpenStates' declared 5/min for the 50-state sweep, P26.11) is
        applied here so a long bounded sweep never out-runs the source's ToS
        rate; robots' crawl-delay still overrides when it demands slower.
        """
        self._limiter.set_host_delay(host, float(delay))

    def _ensure_robots(self, host: str, sample_url: str) -> RobotFileParser:
        if host in self._robots:
            return self._robots[host]
        robots_url = _robots_url(sample_url)
        result = self._transport.robots(robots_url)
        retrieved = result.text is not None
        # RFC 9309 §2.3.1.4 access-result split (ADR-087 — the classification
        # layer is unchanged): a 4xx answer means no policy exists
        # (unrestricted); an *unavailable* robots.txt — connection failure,
        # 5xx, 429 — is the RFC-assumed disallow (SIG-INGEST-012). Under
        # GL-GATE-08 / ADR-088 neither outcome refuses the fetch: the verdict
        # is recorded here and a proceeded-despite-non-grant fetch is marked
        # ``robots_disregarded`` in ``fetch``.
        if not robots_access_permits(retrieved=retrieved, status=result.status):
            outcome = "unretrievable"
        else:
            outcome = "retrieved" if retrieved else "no_policy_4xx"
        self.robots_outcomes[host] = {
            "robots_url": robots_url,
            "status": result.status,
            "outcome": outcome,
        }
        parser = RobotFileParser()
        parser.parse((result.text or "").splitlines())
        self._robots[host] = parser
        crawl_delay = parser.crawl_delay(self._ua) or parser.crawl_delay("*")
        if crawl_delay is not None:
            self._limiter.set_host_delay(host, float(crawl_delay))
        return parser

    def _robots_verdict(self, url: str) -> str:
        """The recorded robots verdict for ``url`` — never enforced (ADR-088).

        Probes and caches the host's policy, then classifies the verdict:
        ``"allowed"`` (a retrieved policy permits the URL), ``"disallowed"`` (a
        retrieved policy forbids it), ``"no_policy_4xx"`` (the host answered
        4xx — no policy exists, RFC 9309 §2.3.1.4), or ``"unretrievable"``
        (the policy could not be obtained — the RFC-assumed disallow).
        """
        host = _host(url)
        parser = self._ensure_robots(host, url)
        outcome = self.robots_outcomes[host]["outcome"]
        if outcome == "unretrievable":
            return "unretrievable"
        if outcome == "no_policy_4xx":
            return "no_policy_4xx"
        return "allowed" if parser.can_fetch(self._ua, url) else "disallowed"

    def can_fetch(self, url: str) -> bool:
        """Whether robots.txt permits the UA to fetch ``url``.

        Under GL-GATE-08 / ADR-088 this returns the *recorded verdict* only —
        it never raises and its answer does not gate :meth:`fetch`. ``False``
        means a retrieved policy disallows the URL or the policy is
        unretrievable (the RFC-assumed disallow); ``True`` means a retrieved
        policy allows it or no policy exists (4xx).
        """
        return self._robots_verdict(url) in ("allowed", "no_policy_4xx")

    def fetch(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        """Fetch ``url`` politely: robots-checked, rate-limited, UA-identified.

        Optional ``headers`` are per-request request headers passed to the
        transport — the seam an authenticated source uses to carry a credential
        (e.g. an ``Authorization: Bearer <jwt>`` on MuckRock's api_v2 data
        endpoints, §23.5) through the shared politeness layer rather than an HTTP
        client of its own (SIG-INGEST-011). Supplying a credential this way is
        *authentication*, not access-control circumvention (Rule 4 / SIG-INGEST-013).

        A non-``None`` ``body`` makes the request a **POST** (a documented
        API-mode pattern — e.g. USAspending's ``spending_by_award`` sub-award
        search, §23.6). POST is still robots-checked / allow-listed and
        rate-limited exactly as a GET; it is a different verb on a documented
        endpoint, never a circumvention.

        Under GL-GATE-08 / ADR-088 robots verdicts are **probed and recorded,
        never enforced**: this raises :class:`ChallengeEncountered` on a
        bot-management challenge (never defeated — SIG-INGEST-013) but never
        raises for a robots outcome. A CRAWL-mode fetch whose verdict is
        ``disallowed`` or ``unretrievable`` proceeds and is recorded in
        :attr:`robots_disregarded` — the audit trail says the refusal was
        ignored rather than pretending it never existed.
        """
        host = _host(url)
        # ADR-083 carve-out: an allow-listed API endpoint is API mode (documented,
        # ToS-governed, rate-limited) — robots governs crawling, not this. A host
        # off the allow-list stays CRAWL and its robots verdict is recorded
        # (post-ADR-088: recorded, never enforced).
        api_reason = api_allow_reason(url)
        if api_reason is not None:
            self.conduct_decisions.append({"url": url, "mode": "api", "basis": api_reason})
        else:
            verdict = self._robots_verdict(url)
            decision: dict[str, str] = {
                "url": url,
                "mode": "crawl",
                "robots_verdict": verdict,
            }
            if verdict in ("disallowed", "unretrievable"):
                # GL-GATE-08: the operator accepted disregarding robots — the
                # fetch proceeds and the record marks it, so provenance says
                # the refusal was ignored (never silently bypassed).
                decision["outcome"] = "robots_disregarded"
                self.robots_disregarded.append({"url": url, "host": host, "verdict": verdict})
            self.conduct_decisions.append(decision)
        self._limiter.acquire(host)
        # Pass headers/body only when present so a transport that predates the
        # seams (and takes only user_agent) keeps working unchanged (back-compat).
        kwargs: dict[str, Any] = {}
        if headers is not None:
            kwargs["headers"] = headers
        if body is not None:
            kwargs["body"] = body
        result = self._transport.request(url, user_agent=self._ua, **kwargs)
        if _is_challenge(result):
            raise ChallengeEncountered(
                f"{url!r} returned a bot-management challenge (status {result.status}); "
                "SIG does not defeat challenges (SIG-INGEST-013) — recorded, not retried.",
                status=result.status,
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
