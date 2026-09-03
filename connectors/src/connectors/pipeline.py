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
from .net import ChallengeEncountered
from .stages import (
    CaptureRef,
    Connector,
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
    asserted: bool = False

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

    for target in targets:
        fetched = _fetch_or_disappear(connector, ctx, target, report)
        if fetched is None:
            continue
        _addressed(ctx, Stage.FETCH, fetched)
        capture = connector.capture(ctx, fetched)
        _addressed(ctx, Stage.CAPTURE, capture)
        report.captures.append(capture)
        report.claims.extend(run_post_capture(connector, ctx, capture))

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
) -> FetchResult | None:
    """Fetch one target, or record a disappearance and return ``None``.

    A gone status (404/410), a restricted status (401/451), or a persistent
    challenge becomes a first-class disappearance event + research task, never a
    swallowed exception (SIG-INGEST-009/010). A robots-disallowed URL is a
    politeness refusal, not a disappearance, and propagates.
    """
    subject_id = target.get("subject_id")
    # A robots-disallowed or robots-unretrievable fetch raises out of the fetcher
    # and propagates: that is a politeness refusal to run, not a disappearance.
    try:
        fetched = connector.fetch(ctx, target)
    except ChallengeEncountered as exc:
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
