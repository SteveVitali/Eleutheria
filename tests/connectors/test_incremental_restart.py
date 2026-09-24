# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.4 / ADR-111: per-capture streaming + restart = resume (D-P30.1-2).

The driver contract, pinned with an in-memory ledger sink (the real-PG proof,
through ``ingest_run_capture`` and ``PgClaimSink``, is
``tests/db/test_resume_pg.py``):

* each capture's claims are flushed as soon as the capture is processed (one
  ``assert_claims`` call per capture), and a live run can keep none of them in
  memory while its count stays exact;
* an execution killed at page *k* and restarted under the same logical run issues
  **no fetch for pages <= k**, asserts only the tail, and ends with the same claim
  set, capture digests, emitted count and shadow-replay diff (0) as an
  uninterrupted run;
* a page captured but not flushed is re-processed from the stored capture (no
  fetch); if the stored bytes are gone the page is re-fetched (degraded resume);
* a page that disappears after the interruption is still recorded as a
  disappearance; a completed logical run, or no logical run, never skips.
"""

from __future__ import annotations

import json
import tracemalloc
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from connectors.pipeline import RunReport, completion_status, run
from connectors.replay import shadow_replay
from connectors.stages import (
    ArtifactStore,
    CaptureLedger,
    CaptureRef,
    Connector,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    Stage,
)

PAGES = 8
ROWS_PER_PAGE = 5


class Killed(BaseException):  # noqa: N818 - models a SIGKILL: not an Exception
    """Raised by the fetcher to model the process dying mid-run.

    A ``BaseException`` escapes the pipeline's ``except Exception`` exactly like a
    SIGKILL escapes everything: no completion is recorded.
    """


class PagedFetcher:
    """Serves ``PAGES`` deterministic ArcGIS-like pages and counts every fetch."""

    def __init__(self, *, kill_at: int | None = None, gone: frozenset[int] = frozenset()) -> None:
        self.calls: list[str] = []
        self._kill_at = kill_at
        self._gone = gone

    def fetch(
        self, url: str, *, headers: Mapping[str, str] | None = None, body: bytes | None = None
    ) -> FetchResult:
        page = int(url.rsplit("=", 1)[1])
        if self._kill_at is not None and page == self._kill_at:
            raise Killed(url)
        self.calls.append(url)
        if page in self._gone:
            return FetchResult(url=url, status=404, body=b"", media_type="application/json")
        rows = [
            {"FID": page * ROWS_PER_PAGE + i, "name": f"cam {page}-{i}"}
            for i in range(ROWS_PER_PAGE)
        ]
        return FetchResult(
            url=url,
            status=200,
            body=json.dumps({"features": rows}, sort_keys=True).encode(),
            media_type="application/json",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


class PagedConnector(Connector):
    """A paged registry: every page yields two claims per row plus one entity record."""

    name = "paged"
    version = "1"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        return json.loads(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        return list(parsed["features"])

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in raw_claims:
            subject = f"traffic_camera:paged:{row['FID']}"
            out.append({"subject_id": subject, "predicate_id": "name", "value": row["name"]})
            out.append({"subject_id": subject, "predicate_id": "fid", "value": row["FID"]})
            out.append({"record_kind": "traffic_camera", "subject_id": subject})
        return out


class DiscoveringConnector(PagedConnector):
    """A connector that resolves follow-on targets from its seed captures' bytes."""

    name = "paged-discovering"

    def discover_more(self, ctx: RunContext, captures: list[CaptureRef]) -> list[Mapping[str, Any]]:
        for c in captures:
            ctx.captures.get(c.digest)  # needs the stored bytes of every seed
        return []


class LedgerState:
    """The durable state two executions share (the spine's ``ingest_run_capture``)."""

    def __init__(self) -> None:
        self.marks: list[dict[str, Any]] = []  # (execution, mark) in append order
        self.completed: set[int] = set()
        self.claims: dict[str, Mapping[str, Any]] = {}  # content key -> claim (dedup)
        self.asserted_batches: list[int] = []


def _key(claim: Mapping[str, Any]) -> str:
    return json.dumps(claim, sort_keys=True, default=str)


class LedgerSink:
    """An in-memory claim sink implementing the CaptureLedger protocol."""

    def __init__(self, state: LedgerState, execution: int, logical_run: str | None) -> None:
        self._state = state
        self._execution = execution
        self._logical_run = logical_run
        self.inserted = 0

    @property
    def logical_run(self) -> str | None:
        return self._logical_run

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
        self._state.asserted_batches.append(len(claims))
        for claim in claims:
            if claim.get("record_kind", "claim") != "claim":
                continue
            if _key(claim) not in self._state.claims:
                self._state.claims[_key(claim)] = claim
                self.inserted += 1

    def record_completion(self, status: str, **_: Any) -> None:
        self._state.completed.add(self._execution)

    def resume_marks(self) -> list[Mapping[str, Any]]:
        if self._state.completed:
            return []
        best: dict[str, dict[str, Any]] = {}
        for mark in self._state.marks:
            prior = best.get(mark["target_key"])
            if prior is None or prior["state"] != "flushed":
                best[mark["target_key"]] = mark
        return list(best.values())

    def record_capture(self, target_key: str, *, state: str, **fields: Any) -> None:
        self._state.marks.append({"target_key": target_key, "state": state, **fields})


def _targets(pages: int = PAGES) -> list[dict[str, Any]]:
    return [
        {"id": "layer-0", "url": f"https://arcgis.example/0/query?resultOffset={p}", "page": p}
        for p in range(pages)
    ]


def _ctx(
    source: Any,
    ingest_run: Any,
    fetcher: PagedFetcher,
    sink: Any,
    captures: InMemoryCaptureStore,
    **kwargs: Any,
) -> RunContext:
    return RunContext(
        source=source,
        run=ingest_run,
        fetcher=fetcher,
        captures=captures,
        claim_sink=sink,
        parameters={"targets": _targets(), **kwargs.pop("parameters", {})},
        **kwargs,
    )


def _uninterrupted(source: Any, ingest_run: Any) -> tuple[RunReport, LedgerState]:
    state = LedgerState()
    ctx = _ctx(
        source, ingest_run, PagedFetcher(), LedgerSink(state, 0, "src@w1"), InMemoryCaptureStore()
    )
    return run(PagedConnector(), ctx), state


def test_the_pg_sink_protocol_split() -> None:
    assert isinstance(LedgerSink(LedgerState(), 0, None), CaptureLedger)
    assert not isinstance(InMemoryClaimSink(), CaptureLedger)


def test_each_capture_is_flushed_as_it_is_processed(permitted_source, ingest_run) -> None:  # type: ignore[no-untyped-def]
    report, state = _uninterrupted(permitted_source, ingest_run)
    # One assert_claims call per capture, each holding exactly that capture's records.
    assert state.asserted_batches == [ROWS_PER_PAGE * 3] * PAGES
    assert report.claim_count == PAGES * ROWS_PER_PAGE * 3
    assert len(state.claims) == PAGES * ROWS_PER_PAGE * 2
    assert report.asserted and report.fetches == PAGES
    flushed = [m for m in state.marks if m["state"] == "flushed"]
    assert [m["records"] for m in flushed] == [ROWS_PER_PAGE * 3] * PAGES


def test_an_interrupted_run_resumes_without_refetching_flushed_pages(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    baseline, baseline_state = _uninterrupted(permitted_source, ingest_run)
    k = 3  # pages 0..2 flushed, the process dies fetching page 3
    state = LedgerState()
    captures = InMemoryCaptureStore()
    first = PagedFetcher(kill_at=k)
    with pytest.raises(Killed):
        run(
            PagedConnector(),
            _ctx(permitted_source, ingest_run, first, LedgerSink(state, 1, "src@w1"), captures),
        )
    assert len(first.calls) == k and not state.completed  # killed: no completion
    landed_before = len(state.claims)
    assert landed_before == k * ROWS_PER_PAGE * 2  # the flushed prefix committed

    second = PagedFetcher()
    sink2 = LedgerSink(state, 2, "src@w1")
    # A fresh capture store: a restart need not read the stored bytes of flushed pages.
    report = run(
        PagedConnector(),
        _ctx(permitted_source, ingest_run, second, sink2, InMemoryCaptureStore()),
    )
    fetched_pages = sorted(int(u.rsplit("=", 1)[1]) for u in second.calls)
    assert fetched_pages == list(range(k, PAGES))  # no fetch for pages < k
    assert report.fetches == PAGES - k
    assert [r["action"] for r in report.resumed] == ["skipped"] * k
    # Only the tail was inserted; the final state equals an uninterrupted run.
    assert sink2.inserted == (PAGES - k) * ROWS_PER_PAGE * 2
    assert set(state.claims) == set(baseline_state.claims)
    assert report.claim_count == baseline.claim_count
    assert [c.digest for c in report.captures] == [c.digest for c in baseline.captures]
    assert completion_status(report) == "ok" and state.completed == {2}


def test_a_captured_but_unflushed_page_is_reprocessed_from_the_stored_capture(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    baseline, baseline_state = _uninterrupted(permitted_source, ingest_run)

    class DiesInFlush(LedgerSink):
        def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
            if len(self._state.asserted_batches) == 4:  # page 4: captured, then killed
                raise Killed("mid-flush")
            super().assert_claims(claims)

    state = LedgerState()
    captures = InMemoryCaptureStore()  # a persistent store (e.g. the GCS mount)
    with pytest.raises(Killed):
        run(
            PagedConnector(),
            _ctx(
                permitted_source,
                ingest_run,
                PagedFetcher(),
                DiesInFlush(state, 1, "w"),
                captures,
            ),
        )
    assert state.marks[-1]["state"] == "captured"  # page 4: stored, never flushed

    second = PagedFetcher()
    report = run(
        PagedConnector(),
        _ctx(permitted_source, ingest_run, second, LedgerSink(state, 2, "w"), captures),
    )
    assert sorted(int(u.rsplit("=", 1)[1]) for u in second.calls) == [5, 6, 7]
    assert [r["action"] for r in report.resumed] == ["skipped"] * 4 + ["reprocessed"]
    assert set(state.claims) == set(baseline_state.claims)
    assert report.claim_count == baseline.claim_count


def test_without_the_stored_bytes_an_unflushed_page_is_refetched(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    state = LedgerState()
    state.marks.append(
        {
            "target_key": _key_of(_targets()[0]),
            "state": "captured",
            "capture_digest": "sha256-gone",
            "source_uri": _targets()[0]["url"],
            "media_type": "application/json",
            "byte_size": 10,
            "retrieved_at": None,
        }
    )
    fetcher = PagedFetcher()
    report = run(
        PagedConnector(),
        _ctx(
            permitted_source, ingest_run, fetcher, LedgerSink(state, 2, "w"), InMemoryCaptureStore()
        ),
    )
    assert report.fetches == PAGES and report.resumed == []  # degraded: re-fetched


def test_a_page_that_disappears_after_the_interruption_is_still_detected(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    state = LedgerState()
    with pytest.raises(Killed):
        run(
            PagedConnector(),
            _ctx(
                permitted_source,
                ingest_run,
                PagedFetcher(kill_at=2),
                LedgerSink(state, 1, "w"),
                InMemoryCaptureStore(),
            ),
        )
    second = PagedFetcher(gone=frozenset({6}))
    report = run(
        PagedConnector(),
        _ctx(
            permitted_source, ingest_run, second, LedgerSink(state, 2, "w"), InMemoryCaptureStore()
        ),
    )
    assert [d.event.artifact_id for d in report.disappearances] == ["layer-0"]
    assert report.disappearances[0].event.failing_status == "link_rotted"  # the 404
    assert completion_status(report) == "partial"
    assert len(report.captures) == PAGES - 1


def test_a_completed_logical_run_or_no_logical_run_never_skips(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    _, state = _uninterrupted(permitted_source, ingest_run)  # completed
    again = PagedFetcher()
    sink = LedgerSink(state, 2, "src@w1")
    report = run(
        PagedConnector(), _ctx(permitted_source, ingest_run, again, sink, InMemoryCaptureStore())
    )
    assert report.fetches == PAGES and report.resumed == [] and sink.inserted == 0  # +0

    fresh = LedgerState()
    fresh.marks.extend(state.marks)  # marks exist, but this sink has no logical run
    none = PagedFetcher()
    run(
        PagedConnector(),
        _ctx(
            permitted_source, ingest_run, none, LedgerSink(fresh, 3, None), InMemoryCaptureStore()
        ),
    )
    assert len(none.calls) == PAGES and not [m for m in fresh.marks if m not in state.marks]


def test_a_discovering_connector_refetches_a_flushed_seed_whose_bytes_are_gone(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    state = LedgerState()
    with pytest.raises(Killed):
        run(
            DiscoveringConnector(),
            _ctx(
                permitted_source,
                ingest_run,
                PagedFetcher(kill_at=3),
                LedgerSink(state, 1, "w"),
                InMemoryCaptureStore(),
            ),
        )
    kept = InMemoryCaptureStore()
    second = PagedFetcher()
    report = run(
        DiscoveringConnector(),
        _ctx(permitted_source, ingest_run, second, LedgerSink(state, 2, "w"), kept),
    )
    assert report.fetches == PAGES and report.resumed == []


def test_shadow_replay_of_the_resumed_captures_diffs_zero(permitted_source, ingest_run) -> None:  # type: ignore[no-untyped-def]
    baseline, _ = _uninterrupted(permitted_source, ingest_run)
    state = LedgerState()
    captures = InMemoryCaptureStore()
    with pytest.raises(Killed):
        run(
            PagedConnector(),
            _ctx(
                permitted_source,
                ingest_run,
                PagedFetcher(kill_at=5),
                LedgerSink(state, 1, "w"),
                captures,
            ),
        )
    report = run(
        PagedConnector(),
        _ctx(permitted_source, ingest_run, PagedFetcher(), LedgerSink(state, 2, "w"), captures),
    )
    # Replaying the resumed run's captures (the skipped pages included) reproduces the
    # uninterrupted run's claim set exactly.
    ctx = _ctx(permitted_source, ingest_run, PagedFetcher(), None, captures)
    diff = shadow_replay(PagedConnector(), ctx, report.captures, baseline.claims)
    assert not diff.added and not diff.removed and len(diff.unchanged) == baseline.claim_count


def test_a_target_limit_bounds_the_slice_and_completes_partial(
    permitted_source, ingest_run
) -> None:  # type: ignore[no-untyped-def]
    state = LedgerState()
    fetcher = PagedFetcher()
    ctx = _ctx(
        permitted_source,
        ingest_run,
        fetcher,
        LedgerSink(state, 1, "w"),
        InMemoryCaptureStore(),
        parameters={"target_limit": 3},
    )
    report = run(PagedConnector(), ctx)
    assert report.fetches == 3 and report.target_limited
    assert [s["reason"] for s in report.sweep_skipped] == ["target_limit"] * (PAGES - 3)
    assert completion_status(report) == "partial"


def test_memory_is_bounded_by_one_capture(permitted_source, ingest_run) -> None:  # type: ignore[no-untyped-def]
    """A bounded live run keeps no claim and one artifact per stage (measured)."""

    def peak(bounded: bool, pages: int) -> tuple[int, RunReport, ArtifactStore]:
        store = ArtifactStore(keep_history=not bounded)
        ctx = RunContext(
            source=permitted_source,
            run=ingest_run,
            fetcher=PagedFetcher(),
            captures=_LatestOnlyCaptureStore(),
            claim_sink=_CountingSink(),
            parameters={"targets": _targets(pages)},
            artifacts=store,
            retain_record=(lambda _r: False) if bounded else None,
        )
        tracemalloc.start()
        report = run(PagedConnector(), ctx)
        _, top = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return top, report, store

    small_peak, _, _ = peak(True, 40)
    big_peak, bounded, store = peak(True, 400)
    unbounded_peak, full, _ = peak(False, 400)
    assert bounded.claims == [] and bounded.claim_count == full.claim_count == 400 * 15
    assert len(store._by_key) == len(Stage)  # one artifact per stage, not one per capture
    # 10x the pages: with the capture store external (as the OCFL store on disk/GCS
    # is), the bounded run grows only by its per-page bookkeeping (a CaptureRef and
    # a report entry per page), while the unbounded one also retains every claim and
    # every stage artifact of every page.
    unbounded_small, _, _ = peak(False, 40)
    bounded_growth = (big_peak - small_peak) / 360
    unbounded_growth = (unbounded_peak - unbounded_small) / 360
    print(
        f"per-page peak growth: bounded {bounded_growth:.0f} B, unbounded {unbounded_growth:.0f} B"
    )
    assert bounded_growth < unbounded_growth / 5


class _LatestOnlyCaptureStore(InMemoryCaptureStore):
    """Holds only the latest capture in memory, like a store backed by disk/GCS."""

    def put(self, data: bytes, **kwargs: Any) -> CaptureRef:
        self._blobs.clear()
        return super().put(data, **kwargs)


class _CountingSink:
    def __init__(self) -> None:
        self.count = 0

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
        self.count += len(claims)


def _key_of(target: Mapping[str, Any]) -> str:
    from connectors.pipeline import _target_key

    return _target_key(target)
