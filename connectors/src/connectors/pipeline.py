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

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
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
    CaptureLedger,
    CaptureRef,
    CompletionRecorder,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    Stage,
    StageArtifact,
)
from .stages import content_digest as stage_content_digest

_log = logging.getLogger(__name__)


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
    #: Every record the post-capture stages emitted (P31.4). A live run may retain
    #: only some records in :attr:`claims` (``RunContext.retain_record``) so its
    #: memory stays bounded by one capture; this count is always exact, and a
    #: target a restarted execution skipped contributes the count its mark recorded.
    claim_count: int = 0
    #: The number of ``fetch()`` calls this execution issued (P31.4): a resumed
    #: execution issues none for the targets it did not re-fetch.
    fetches: int = 0
    #: Targets a restarted execution did not fetch (P31.4 / ADR-111), each
    #: ``{"target", "action", "capture_digest"}``. ``skipped``: an interrupted
    #: execution of the same logical run had already flushed it, so it is counted
    #: as seen and not re-walked. ``reprocessed``: it had been captured but not
    #: flushed, so its claims were re-derived from the stored capture.
    resumed: list[dict[str, Any]] = field(default_factory=list)
    #: Set when ``ctx.parameters["target_limit"]`` bounded the run to its first N
    #: seed targets (a bounded slice). The rest are listed in ``sweep_skipped``
    #: with reason ``target_limit``, and the run completes ``partial``.
    target_limited: bool = False

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


def completion_status(report: RunReport) -> str:
    """The ``ingest_run_completion`` status for an execution that ran to its end.

    ``quota_reached`` if it stopped at a 429 wall. ``partial`` if any target was
    recorded as a disappearance, refusal or drift, the request budget deferred a
    tail of slices, or a ``target_limit`` bounded the run. Otherwise ``ok``.
    (``failed`` is the exception path in :func:`run`.)
    """
    if report.quota_reached:
        return "quota_reached"
    if (
        report.disappearances
        or report.refusals
        or report.drifted
        or report.budget_reached
        or report.target_limited
    ):
        return "partial"
    return "ok"


def _record_completion(ctx: RunContext, status: str, *, detail: str | None = None) -> None:
    """Append the execution's completion, if the sink records completions (ADR-109).

    Only a live execution records one: replay and shadow runs assert nothing and
    have no run to complete. A completion that cannot be written (for example the
    database connection is already gone) is logged and dropped. It never masks
    the run's own outcome or exception. The run then honestly has no completion.
    """
    sink = ctx.claim_sink
    if not ctx.asserts_claims or not isinstance(sink, CompletionRecorder):
        return
    try:
        sink.record_completion(status, source_id=ctx.source.id, detail=detail)
    except Exception as exc:  # noqa: BLE001 - recording must never mask the run outcome
        _log.warning(
            "ingest-run completion (%s) for %s not recorded: %s",
            status,
            ctx.source.id,
            type(exc).__name__,
        )


def run(connector: Connector, ctx: RunContext) -> RunReport:
    """Run one connector end-to-end through the eight stages.

    Gates before the first fetch, isolates every post-capture stage, records
    disappearances as data, and asserts the claim set only on a live run.

    Every live execution that passed the gate ends by appending its completion to a
    sink that records completions (P31.2 / ADR-109): the success path records
    :func:`completion_status`, and an exception records ``failed`` (with the
    exception's class, never its message) before it propagates. A gate refusal is
    not an execution, so it records nothing.
    """
    # SIG-INGEST-014/028: the gate is checked once, up front, before any fetch.
    assert_loadable(ctx.source)
    try:
        report = _run_stages(connector, ctx)
    except Exception as exc:
        _record_completion(ctx, "failed", detail=type(exc).__name__)
        raise
    _record_completion(ctx, completion_status(report))
    return report


def _target_key(target: Mapping[str, Any]) -> str:
    """The resume key of one fetch target (P31.4 / ADR-111).

    The target's URL (else its id) plus a digest of the whole target mapping, so two
    targets that share a URL but differ in any parameter (a page offset, a request
    body) never share a key. A target whose mapping changes between executions
    simply does not resume, which is the safe direction.
    """
    locator = str(target.get("url") or target.get("id") or target.get("locator") or "target")
    return f"{locator}#{stage_content_digest(dict(target))[:16]}"


def _ledger(ctx: RunContext) -> CaptureLedger | None:
    """The run's capture ledger, when it resumes (a live run with a logical run key)."""
    sink = ctx.claim_sink
    if not ctx.asserts_claims or not isinstance(sink, CaptureLedger):
        return None
    return sink if sink.logical_run else None


def _mark_capture(ledger: CaptureLedger | None, key: str, capture: CaptureRef, **kw: Any) -> None:
    if ledger is None:
        return
    ledger.record_capture(
        key,
        capture_digest=capture.digest,
        source_uri=capture.source_uri,
        media_type=capture.media_type,
        byte_size=capture.byte_size,
        retrieved_at=capture.retrieved_at,
        **kw,
    )


def _capture_of(mark: Mapping[str, Any]) -> CaptureRef:
    retrieved = mark.get("retrieved_at")
    return CaptureRef(
        digest=str(mark["capture_digest"]),
        media_type=str(mark["media_type"]),
        source_uri=str(mark["source_uri"]),
        byte_size=int(mark["byte_size"]),
        retrieved_at=retrieved if isinstance(retrieved, datetime) else None,
    )


def _emit(
    ctx: RunContext,
    report: RunReport,
    ledger: CaptureLedger | None,
    key: str,
    capture: CaptureRef,
    claims: list[dict[str, Any]],
) -> None:
    """Flush one capture's claims (P31.4 / ADR-111) and account for them.

    On a live run the claims are asserted now, one ``assert_claims`` call per
    capture (a commit boundary, ADR-110), and the target's ``flushed`` mark is
    appended once they have committed. Replay and shadow runs assert nothing
    (SIG-INGEST-018/019). The report keeps every record unless the context
    retains only some (bounded memory); the count is always exact.
    """
    if ctx.asserts_claims and ctx.claim_sink is not None:
        ctx.claim_sink.assert_claims(claims)
        _mark_capture(ledger, key, capture, state="flushed", records=len(claims))
    report.claim_count += len(claims)
    retain = ctx.retain_record
    report.claims.extend(claims if retain is None else [c for c in claims if retain(c)])


def _resume_target(
    connector: Connector,
    ctx: RunContext,
    report: RunReport,
    key: str,
    mark: Mapping[str, Any] | None,
) -> tuple[str, CaptureRef | None]:
    """Apply the resume rule (ADR-111) to one target.

    Returns ``("fetch", None)`` when the target needs a normal fetch: it has no
    mark, or its stored bytes are gone (an ephemeral capture store, the degraded
    resume). Returns ``("skipped", None)`` for a target an interrupted execution
    had flushed: it is recorded as seen (its capture digest and record count go
    into the report) and not re-walked. Returns ``("reprocess", capture)`` for a
    target that had been captured but not flushed and whose bytes the store still
    holds: its claims are re-derived from the stored capture, with no request.
    """
    if mark is None:
        return "fetch", None
    capture = _capture_of(mark)
    stored = ctx.captures.has(capture.digest)
    # A connector that resolves follow-on targets reads every seed capture's bytes
    # in ``discover_more``, so it can skip a flushed seed only if the bytes remain.
    needs_bytes = type(connector).discover_more is not Connector.discover_more
    if mark.get("state") == "flushed" and (stored or not needs_bytes):
        report.captures.append(capture)
        report.claim_count += int(mark.get("records") or 0)
        report.resumed.append(
            {"target": key, "action": "skipped", "capture_digest": capture.digest}
        )
        return "skipped", None
    if stored:
        report.resumed.append(
            {"target": key, "action": "reprocessed", "capture_digest": capture.digest}
        )
        return "reprocess", capture
    return "fetch", None


def _reprocess(
    connector: Connector, ctx: RunContext, report: RunReport, capture: CaptureRef
) -> list[dict[str, Any]] | None:
    """Re-derive a stored capture's claims, or ``None`` if the stored bytes no longer yield.

    An interrupted execution may have captured a transient error page (a WAF page, an
    ArcGIS error envelope) or left a partly written object. Re-reading those bytes on
    every restart would pin the run to the failure for the whole cadence window, so
    any failure here marks the target ``refetched`` and the caller fetches it again,
    exactly as a run without resume would.
    """
    try:
        return run_post_capture(connector, ctx, capture)
    except Exception as exc:  # noqa: BLE001 - any failure means "fetch it again"
        _log.warning(
            "stored capture %s no longer yields (%s); fetching the target again",
            capture.digest,
            type(exc).__name__,
        )
        for entry in reversed(report.resumed):
            if entry["capture_digest"] == capture.digest and entry["action"] == "reprocessed":
                entry["action"] = "refetched"
                break
        return None


def _run_stages(connector: Connector, ctx: RunContext) -> RunReport:
    """The body of :func:`run`, after the gate: discover → … → load (+ assert).

    Since P31.4 (ADR-111) each capture's claims are flushed to the sink as soon as
    the capture is processed, so a live run's memory is bounded by one capture and
    an interruption loses at most the capture in flight. A live run whose sink
    carries a logical run key also resumes: targets an interrupted execution of the
    same logical run had flushed are skipped (and still counted as seen), and
    targets it had only captured are re-processed from the stored capture.
    """
    report = RunReport()
    ledger = _ledger(ctx)
    marks = {str(m["target_key"]): m for m in ledger.resume_marks()} if ledger else {}
    targets = connector.discover(ctx)
    _addressed(ctx, Stage.DISCOVER, targets)

    # P31.4: a bounded slice — the first N seed targets only (recorded, partial).
    limit = ctx.parameters.get("target_limit")
    if isinstance(limit, int) and not isinstance(limit, bool) and 0 <= limit < len(targets):
        report.target_limited = True
        report.sweep_skipped.extend(
            {"id": _target_id(t), "reason": "target_limit"} for t in targets[limit:]
        )
        targets = list(targets[:limit])

    # P26.19 — quota-bounded sweep guard (opt-in per target via ``quota_governed``
    # + the ``request_budget`` parameter). It bounds a keyword-sweep source (SAM.gov
    # over the api.data.gov daily quota) to one fresh window WITH HEADROOM and
    # stops cleanly rather than burning the window into a 429 crash. Targets that
    # do not opt in see none of this (``budget`` None / flag absent).
    budget = ctx.parameters.get("request_budget")
    if isinstance(budget, int) and not isinstance(budget, bool):
        report.sweep_budget = int(budget)

    for target in targets:
        key = _target_key(target)
        action, stored = _resume_target(connector, ctx, report, key, marks.get(key))
        if action == "skipped":
            continue  # flushed by an interrupted execution: seen, not re-walked
        if stored is not None:
            # Captured by an interrupted execution but never flushed: re-derive its
            # claims from the stored capture. No request is issued. If the stored
            # bytes no longer yield, fall through to a normal fetch (below).
            reprocessed = _reprocess(connector, ctx, report, stored)
            if reprocessed is not None:
                _addressed(ctx, Stage.CAPTURE, stored)
                report.captures.append(stored)
                _emit(ctx, report, ledger, key, stored, reprocessed)
                continue
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
        _mark_capture(ledger, key, capture, state="captured")
        _emit(ctx, report, ledger, key, capture, run_post_capture(connector, ctx, capture))

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
            key = _target_key(target)
            action, child = _resume_target(connector, ctx, report, key, marks.get(key))
            if action == "skipped":
                continue  # flushed by an interrupted execution: seen, not re-walked
            reprocessed = None if child is None else _reprocess(connector, ctx, report, child)
            if reprocessed is None:
                child = None  # no stored capture, or its bytes no longer yield: fetch
            if child is None:
                fetched = _fetch_or_disappear(connector, ctx, target, report, record_refusals=True)
                if fetched is None:
                    continue
                _addressed(ctx, Stage.FETCH, fetched)
                child = connector.capture(ctx, fetched)
                _mark_capture(ledger, key, child, state="captured")
            _addressed(ctx, Stage.CAPTURE, child)
            report.captures.append(child)
            try:
                claims = (
                    reprocessed
                    if reprocessed is not None
                    else run_post_capture(connector, ctx, child)
                )
            except ContentDrift as drift:
                # P26.6: a resolved child document that doesn't parse as the
                # platform's genre is a per-document fail-closed disposition —
                # recorded with its locator, the run continues. Drift on a seed
                # capture (the loop above) still propagates and fails the run.
                # A drifted capture is never marked flushed, so a restarted run
                # re-derives (and re-records) the drift.
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
                continue
            _emit(ctx, report, ledger, key, child, claims)

    # SIG-INGEST-018/019: replay and shadow runs produce claims but never assert.
    # A live run has asserted each capture's claims as it went (P31.4).
    if ctx.asserts_claims and ctx.claim_sink is not None:
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
    report.fetches += 1
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


__all__ = ["RunReport", "completion_status", "run", "run_post_capture", "run_stage"]
