# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The eight-stage interface: ordering, egress, content addressing (SIG-INGEST-001/002/003)."""

from __future__ import annotations

import pytest
from connectors.stages import (
    EGRESS_STAGE,
    POST_CAPTURE_STAGES,
    STAGE_ORDER,
    ArtifactStore,
    InMemoryCaptureStore,
    Stage,
    StageArtifact,
    content_digest,
    get_connector,
    is_post_capture,
    may_egress,
    register,
    registered_connectors,
    stage_names,
)


def test_the_eight_stages_are_named_and_ordered() -> None:
    # SIG-INGEST-001: the canonical eight stages, in order.
    assert [s.value for s in STAGE_ORDER] == [
        "discover",
        "fetch",
        "capture",
        "parse",
        "extract",
        "normalize",
        "link",
        "load",
    ]
    assert stage_names() == [s.value for s in STAGE_ORDER]


def test_fetch_is_the_only_egress_stage() -> None:
    # SIG-INGEST-002: fetch() is the ONLY stage permitted network egress.
    assert EGRESS_STAGE is Stage.FETCH
    assert may_egress(Stage.FETCH)
    for stage in STAGE_ORDER:
        if stage is not Stage.FETCH:
            assert not may_egress(stage)


def test_post_capture_stages_are_the_pure_ones() -> None:
    # SIG-INGEST-002: every stage after capture() is a pure function of artifacts.
    assert POST_CAPTURE_STAGES == (
        Stage.PARSE,
        Stage.EXTRACT,
        Stage.NORMALIZE,
        Stage.LINK,
        Stage.LOAD,
    )
    assert not is_post_capture(Stage.FETCH)
    assert not is_post_capture(Stage.CAPTURE)
    assert is_post_capture(Stage.PARSE)
    assert is_post_capture(Stage.LOAD)


def test_content_addressing_is_deterministic_and_order_independent() -> None:
    # SIG-INGEST-003: identical inputs => identical digest (idempotency handle).
    a = {"b": 1, "a": [3, 2, 1]}
    b = {"a": [3, 2, 1], "b": 1}
    assert content_digest(a) == content_digest(b)
    assert content_digest(a) != content_digest({"a": [1, 2, 3], "b": 1})


def test_fetch_result_addresses_by_body_not_volatile_headers() -> None:
    # SIG-INGEST-003: response headers (Date/Server) vary between identical
    # fetches; the fetch address must not depend on them.
    from connectors.stages import FetchResult

    a = FetchResult(url="https://x/a", status=200, body=b"same", headers={"Date": "Mon"})
    b = FetchResult(url="https://x/a", status=200, body=b"same", headers={"Date": "Tue"})
    c = FetchResult(url="https://x/a", status=200, body=b"different")
    assert content_digest(a) == content_digest(b)
    assert content_digest(a) != content_digest(c)


def test_capture_ref_addresses_by_content_not_retrieval_time() -> None:
    # SIG-INGEST-003: re-capturing identical bytes later addresses identically.
    from datetime import UTC, datetime

    from connectors.stages import CaptureRef

    early = CaptureRef("d", "text/plain", "https://x/a", 4, datetime(2026, 1, 1, tzinfo=UTC))
    late = CaptureRef("d", "text/plain", "https://x/a", 4, datetime(2026, 9, 9, tzinfo=UTC))
    assert content_digest(early) == content_digest(late)


def test_stage_artifact_carries_its_digest() -> None:
    artifact = StageArtifact.of(Stage.EXTRACT, [{"x": 1}])
    assert artifact.stage is Stage.EXTRACT
    assert artifact.digest == content_digest([{"x": 1}])


def test_artifact_store_addresses_and_retries_stages() -> None:
    # SIG-INGEST-001: stages are separately addressable and retryable.
    store = ArtifactStore()
    art = store.put(StageArtifact.of(Stage.PARSE, {"k": "v"}))
    assert store.get(Stage.PARSE, art.digest) is art
    assert store.latest(Stage.PARSE) is art
    assert store.latest(Stage.LOAD) is None


def test_in_memory_capture_store_is_content_addressed() -> None:
    store = InMemoryCaptureStore()
    ref = store.put(b"hello", media_type="text/plain", source_uri="https://x/a")
    again = store.put(b"hello", media_type="text/plain", source_uri="https://x/b")
    assert ref.digest == again.digest  # same bytes => same address
    assert store.get(ref.digest) == b"hello"
    assert store.has(ref.digest)
    assert ref.byte_size == 5


def test_connector_registry_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    import connectors.stages as stages_mod

    monkeypatch.setattr(stages_mod, "_REGISTRY", {})
    from connectors.stages import Connector

    class _Dummy(Connector):
        name = "dummy"
        version = "1"

        def discover(self, ctx):  # type: ignore[no-untyped-def]
            return []

        def fetch(self, ctx, target):  # type: ignore[no-untyped-def]
            raise NotImplementedError

        def parse(self, ctx, capture):  # type: ignore[no-untyped-def]
            return None

        def extract(self, ctx, parsed):  # type: ignore[no-untyped-def]
            return []

        def normalize(self, ctx, raw_claims):  # type: ignore[no-untyped-def]
            return []

    register(_Dummy)
    assert get_connector("dummy") is _Dummy
    assert "dummy" in registered_connectors()
    with pytest.raises(ValueError):

        class _Other(_Dummy):
            pass

        _Other.name = "dummy"
        register(_Other)
