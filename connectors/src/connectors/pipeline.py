# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector driver: run stages, gate, isolate, record (§21.1-21.6).

This is the framework's engine. It runs a :class:`~connectors.stages.Connector`
through the eight stages, enforcing the contract the stages only *declare*:

* the connector-loader gate is checked **before any fetch** (SIG-INGEST-014/028),
  via :func:`connectors.loader.assert_loadable`;
* ``fetch()`` is the only stage that egresses, and every post-capture stage runs
  under :func:`connectors.isolation.network_isolated` so an accidental egress
  fails the run (SIG-INGEST-002);
* each stage output is content-addressed and persisted, so stages are separately
  addressable and retryable (SIG-INGEST-001);
* a 404 / removal / persistent challenge is recorded as a disappearance — a
  first-class event **and** a research task — instead of raising
  (SIG-INGEST-009/010);
* claims are asserted **only** on a live run, never in replay or shadow mode
  (SIG-INGEST-018/019).

The name ``pipeline`` matches the orchestration boundary: this module is a plain
library the ``orchestration/`` package (and the CLI) drive; it imports no
workflow orchestrator (SIG-ENG-013).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from evidence.ingest_run import claim_set_fingerprint

from .disappearance import (
    Disappearance,
    failing_status_for_error,
    failing_status_for_http,
    note_disappearance,
)
from .isolation import network_isolated
from .loader import assert_loadable
from .net import ChallengeEncountered, RobotsDisallowed, RobotsUnretrievable
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    Stage,
    StageArtifact,
)


@dataclass
class RunReport:
    """The result of one connector run."""

    claims: list[dict[str, Any]] = field(default_factory=list)
    captures: list[CaptureRef] = field(default_factory=list)
    disappearances: list[Disappearance] = field(default_factory=list)
    #: Politeness refusals on discovery-continuation targets (P25.5): a resolved
    #: child document whose host refuses the fetch (a robots refusal from a
    #: non-standard fetcher — the shared ``PoliteFetcher`` never refuses post
    #: GL-GATE-08 / ADR-088) is recorded here — a first-class per-document
    #: disposition — while the run continues to the next resolved target. A
    #: refusal on a *seed* target still propagates (a refused seed is a
    #: refused run).
    refusals: list[dict[str, Any]] = field(default_factory=list)
    #: Per-document content drift on discovery-continuation targets (P26.6): a
    #: resolved child document whose captured bytes no longer parse as the
    #: platform's expected genre is a recorded disposition — fail-closed, never
    #: a fabricated extraction — and the run continues to the next resolved
    #: target. Drift on a *seed* capture still propagates (a drifted seed is a
    #: drifted run).
    drifted: list[dict[str, Any]] = field(default_factory=list)
    asserted: bool = False
    #: Quota-bounded sweep bookkeeping (P26.19). A target flagged
    #: ``quota_governed`` participates in a per-run request budget: the driver
    #: counts every such request it ISSUES (a refused request still counts —
    #: the recorded rate-limit lesson) and stops the sweep cleanly BEFORE the
    #: hard quota wall. Absent the flag / a ``request_budget`` parameter these
    #: stay at their defaults and behaviour is byte-for-byte unchanged.
    sweep_requests: int = 0
    #: The per-run request budget in force (``ctx.parameters["request_budget"]``)
    #: or ``None`` when unbounded.
    sweep_budget: int | None = None
    #: Set once a governed slice hit the configured budget: the run stopped with
    #: headroom and the remaining slices are deferred to the next fresh window.
    budget_reached: bool = False
    #: Set once a governed slice observed a 429 rate-limit wall: the run stops
    #: immediately and NEVER re-probes the exhausted window (SIG-INGEST-012/013).
    quota_reached: bool = False
    #: Governed slices the driver deliberately did NOT issue (budget spent or
    #: quota reached), each ``{"id", "reason"}`` — the honest record that the
    #: coverage tail is deferred, not lost.
    sweep_skipped: list[dict[str, Any]] = field(default_factory=list)
    #: Transient: the HTTP status of the most recent challenge the driver saw
    #: (set by ``_fetch_or_disappear``), read once per iteration to classify a
    #: 429 wall. Not part of the durable record.
    last_challenge_status: int | None = None

    @property
    def fingerprint(self) -> str:
        """Order-independent fingerprint of the claim set (SIG-INGEST-003/017)."""
        return claim_set_fingerprint([dict(c) for c in self.claims])


def _addressed(ctx: RunContext, stage: Stage, payload: Any) -> StageArtifact:
    """Content-address a stage output and persist it (SIG-INGEST-001)."""
    return ctx.artifacts.put(StageArtifact.of(stage, payload))


def run_post_capture(
    connector: Connector, ctx: RunContext, capture: CaptureRef
) -> list[dict[str, Any]]:
    """Run parse→extract→normalize→link→load for one capture, network-isolated.

    Every stage here is a pure function of the stored capture (SIG-INGEST-002);
    the isolation makes that testable — an egress raises and fails the run. The
    returned claims are *not* asserted here; the caller decides (live vs replay).
    """
    with network_isolated():
        parsed = connector.parse(ctx, capture)
        _addressed(ctx, Stage.PARSE, parsed)
        raw_claims = connector.extract(ctx, parsed)
        _addressed(ctx, Stage.EXTRACT, raw_claims)
        normalized = connector.normalize(ctx, raw_claims)
        _addressed(ctx, Stage.NORMALIZE, normalized)
        linked = connector.link(ctx, normalized)
        _addressed(ctx, Stage.LINK, linked)
        claims = connector.load(ctx, linked)
        _addressed(ctx, Stage.LOAD, claims)
    return claims


def _target_id(target: Mapping[str, Any]) -> str:
    return str(target.get("id") or target.get("locator") or target.get("url") or "target")


def run(connector: Connector, ctx: RunContext) -> RunReport:
    """Run one connector end-to-end through the eight stages.

    Gates before the first fetch, isolates every post-capture stage, records
    disappearances as data, and asserts the claim set only on a live run.
    """
    # SIG-INGEST-014/028: the gate is checked once, up front, before any fetch.
    assert_loadable(ctx.source)

    report = RunReport()
    targets = connector.discover(ctx)
    _addressed(ctx, Stage.DISCOVER, targets)

    # P26.19 — quota-bounded sweep guard (opt-in per target via ``quota_governed``
    # + the ``request_budget`` parameter). It bounds a keyword-sweep source (SAM.gov
    # over the api.data.gov daily quota) to one fresh window WITH HEADROOM and
    # stops cleanly rather than burning the window into a 429 crash. Targets that
    # do not opt in see none of this (``budget`` None / flag absent).
    budget = ctx.parameters.get("request_budget")
    if isinstance(budget, int) and not isinstance(budget, bool):
        report.sweep_budget = int(budget)

    for target in targets:
        governed = bool(target.get("quota_governed"))
        if governed and report.quota_reached:
            # RATE-LIMIT HONESTY: a 429 wall was already observed this run — the
            # window is exhausted, so we NEVER re-probe it. The remaining budgeted
            # slices are recorded as deferred, not issued (SIG-INGEST-012/013).
            report.sweep_skipped.append({"id": _target_id(target), "reason": "quota_reached"})
            continue
        if (
            governed
            and report.sweep_budget is not None
            and report.sweep_requests >= report.sweep_budget
        ):
            # Stop BEFORE the hard wall: the per-run request budget (headroom under
            # the daily tier) is spent. Remaining slices wait for the next window.
            report.budget_reached = True
            report.sweep_skipped.append({"id": _target_id(target), "reason": "budget_reached"})
            continue
        report.last_challenge_status = None
        if governed:
            # A request we are about to ISSUE counts against the window even if it
            # is refused — that is the whole lesson (a refused request still burns
            # the quota). Count before the fetch so a 429 is honestly accounted.
            report.sweep_requests += 1
        fetched = _fetch_or_disappear(connector, ctx, target, report)
        if governed and fetched is None and report.last_challenge_status == 429:
            report.quota_reached = True
        if fetched is None:
            continue
        _addressed(ctx, Stage.FETCH, fetched)
        capture = connector.capture(ctx, fetched)
        _addressed(ctx, Stage.CAPTURE, capture)
        report.captures.append(capture)
        report.claims.extend(run_post_capture(connector, ctx, capture))

    # Bounded discovery continuation (P25.5): a captured resource index is the
    # discovery surface for its per-document children (RAA index rows, CCOPS
    # linked filings). ``discover_more`` is a pure function of the stored
    # captures (network-isolated); only ``fetch()`` egresses for the resolved
    # targets, and exactly one bounded pass runs — never a recursive crawl.
    with network_isolated():
        extra = connector.discover_more(ctx, report.captures)
    # A connector may record a disappearance while resolving follow-on targets
    # (P25.7): a captured upstream index/lookup can report that a reviewed
    # resource is *gone* — there is no URL left to fetch, so the disposition is
    # recorded here as first-class data rather than becoming a silent empty run.
    if ctx.resolved_disappearances:
        report.disappearances.extend(ctx.resolved_disappearances)
        ctx.resolved_disappearances.clear()
    if extra:
        _addressed(ctx, Stage.DISCOVER, extra)
        seen = {c.source_uri for c in report.captures}
        for target in extra:
            url = str(target.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            fetched = _fetch_or_disappear(connector, ctx, target, report, record_refusals=True)
            if fetched is None:
                continue
            _addressed(ctx, Stage.FETCH, fetched)
            capture = connector.capture(ctx, fetched)
            _addressed(ctx, Stage.CAPTURE, capture)
            report.captures.append(capture)
            try:
                report.claims.extend(run_post_capture(connector, ctx, capture))
            except ContentDrift as drift:
                # P26.6: a resolved child document that doesn't parse as the
                # platform's genre is a per-document fail-closed disposition —
                # recorded with its locator, the run continues. Drift on a seed
                # capture (the loop above) still propagates and fails the run.
                report.drifted.append(
                    {
                        "id": _target_id(target),
                        "url": url,
                        "platform": target.get("platform"),
                        "tenant_id": target.get("tenant_id"),
                        "document_kind": target.get("document_kind"),
                        "refusal": "ContentDrift",
                        "detail": str(drift),
                        "observed_at": _now().isoformat(),
                    }
                )

    # SIG-INGEST-018/019: replay and shadow runs produce claims but never assert.
    if ctx.asserts_claims and ctx.claim_sink is not None:
        ctx.claim_sink.assert_claims(report.claims)
        report.asserted = True
    return report


def _fetch_or_disappear(
    connector: Connector,
    ctx: RunContext,
    target: Mapping[str, Any],
    report: RunReport,
    *,
    record_refusals: bool = False,
) -> FetchResult | None:
    """Fetch one target, or record a disappearance and return ``None``.

    A gone status (404/410), a restricted status (401/451), a persistent
    challenge, or a transport-level failure (``unreachable``, P26.17) becomes a
    first-class disappearance event + research task, never a swallowed
    exception (SIG-INGEST-009/010). A robots-disallowed URL was a politeness
    refusal, not a disappearance — but under GL-GATE-08 / ADR-088 the shared
    ``PoliteFetcher`` never refuses on robots: the verdict is recorded
    (``robots_disregarded``) and the fetch proceeds. The refusal path below is
    retained for non-standard fetcher implementations that still raise: on a
    *seed* target a refusal propagates (a refused seed is a refused run); on a
    discovery-continuation target (``record_refusals=True``) — or a target
    that declares ``record_refusals`` itself, as every multi-tenant
    agenda-platform target does (P26.3: each host's own robots verdict is a
    recorded per-host outcome) — it lands on ``report.refusals``, and the run
    continues.
    """
    subject_id = target.get("subject_id")
    try:
        fetched = connector.fetch(ctx, target)
    except (RobotsUnretrievable, RobotsDisallowed) as exc:
        # GL-GATE-08 / ADR-088: PoliteFetcher never raises these — a robots
        # verdict is recorded (robots_disregarded) and the fetch proceeds.
        # The catch is retained for non-standard fetcher implementations that
        # still refuse on robots; their refusal is recorded exactly as before.
        if not (record_refusals or target.get("record_refusals")):
            raise  # a politeness refusal on a seed target refuses the run
        report.refusals.append(
            {
                "id": _target_id(target),
                "url": str(target.get("url", "")),
                "refusal": type(exc).__name__,
                "detail": str(exc),
                "observed_at": _now().isoformat(),
            }
        )
        return None
    except ChallengeEncountered as exc:
        # Surface the raw HTTP status so the driver can tell a 429 quota wall from
        # a 401/403 auth challenge (P26.19); the disappearance record itself keeps
        # its coarse ``access_restricted`` classification unchanged.
        report.last_challenge_status = getattr(exc, "status", None)
        status = failing_status_for_error(exc)
        assert status is not None
        report.disappearances.append(
            note_disappearance(
                artifact_id=_target_id(target),
                observed_at=_now(),
                failing_status=status,
                subject_id=subject_id,
            )
        )
        return None
    except Exception as exc:
        # A transport-level failure (httpx.ConnectError/ReadTimeout/TLS, …) is
        # an `unreachable` disappearance — recorded as data, never a crash that
        # abandons the remaining targets (P26.17 / ADR-088: with robots
        # non-gating, unretrievable-policy hosts are attempted and their
        # honest reachability lands here). Non-transport errors still raise.
        status = failing_status_for_error(exc)
        if status is None:
            raise
        report.disappearances.append(
            note_disappearance(
                artifact_id=_target_id(target),
                observed_at=_now(),
                failing_status=status,
                subject_id=subject_id,
            )
        )
        return None

    failing = failing_status_for_http(fetched.status)
    if failing is not None:
        report.disappearances.append(
            note_disappearance(
                artifact_id=_target_id(target),
                observed_at=_now(),
                failing_status=failing,
                subject_id=subject_id,
            )
        )
        return None
    return fetched


def _now() -> Any:
    from .net import now_utc

    return now_utc()


def run_stage(connector: Connector, ctx: RunContext, stage: Stage, payload: Any = None) -> Any:
    """Run a single stage in isolation, addressing its output (SIG-INGEST-001).

    Stages are separately addressable and retryable: given the upstream payload,
    this runs exactly one stage and persists its content-addressed artifact.
    ``fetch()`` egresses; every other stage runs network-isolated.
    """
    out: Any
    if stage is Stage.DISCOVER:
        # Pre-capture: not isolated (it may read a prior capture from the store),
        # but it is handed no fetcher, so it lists identifiers, it does not egress.
        out = connector.discover(ctx)
    elif stage is Stage.FETCH:
        assert_loadable(ctx.source)
        out = connector.fetch(ctx, payload)
    elif stage is Stage.CAPTURE:
        out = connector.capture(ctx, payload)
    else:
        # Post-capture stages are pure functions of stored artifacts; any egress
        # here fails the run (SIG-INGEST-002).
        method = getattr(connector, stage.value)
        with network_isolated():
            out = method(ctx, payload)
    _addressed(ctx, stage, out)
    return out


__all__ = ["RunReport", "run", "run_post_capture", "run_stage"]
