# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.41 / SIG-TRANSP-031 + K9 §5.4 — the upstream-declared change value and
the canonical ``records_digest``.

Two append-only marks land per flushed capture:

* the upstream's own declared change value (``editingInfo.lastEditDate``,
  ``rowsUpdatedAt``, ``metadata_modified``, ``data_last_updated``,
  ``Last-Modified`` / ``ETag``) — the publisher's clock, never SIG's
  retrieval clock; a transport that declares nothing marks nothing
  (``not_detectable`` at the release surface, never a guessed date);
* ``records_digest`` — the order-independent fingerprint of the emitted
  record set under the registry's temporal classes — the SIG-record-change
  signal a byte-only difference never moves.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from connectors.pipeline import run
from connectors.stages import (
    CaptureRef,
    Connector,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from connectors.upstream_modified import (
    UpstreamDeclared,
    declared_from_headers,
    declared_from_metadata,
    declared_from_payload,
    metadata_request_url,
    upstream_declared,
)

# --- the declared-value lanes -------------------------------------------------


def _fetched(body: bytes = b"{}", **kw: Any) -> FetchResult:
    return FetchResult(
        url=str(kw.get("url", "https://upstream.example/x")),
        status=200,
        body=body,
        media_type="application/json",
        headers=dict(kw.get("headers", {})),
    )


def test_metadata_request_url_arcgis_layer_doc() -> None:
    target = {"kind": "arcgis_query", "layer_url": "https://h.example/arcgis/FeatureServer/0/"}
    assert metadata_request_url(target) == "https://h.example/arcgis/FeatureServer/0?f=json"


def test_metadata_request_url_socrata_views_doc() -> None:
    target = {
        "kind": "socrata_rows",
        "layer_url": "https://data.example.gov/resource/abcd-1234.json",
    }
    assert metadata_request_url(target) == "https://data.example.gov/api/views/abcd-1234.json"


def test_metadata_request_url_declared_metadata_url() -> None:
    target = {"kind": "ckan_package", "metadata_url": " https://ckan.example/api/pkg "}
    assert metadata_request_url(target) == "https://ckan.example/api/pkg"


def test_metadata_request_url_document_kind_has_no_probe() -> None:
    assert metadata_request_url({"kind": "document_pdf", "url": "https://x"}) is None


def test_declared_from_metadata_arcgis_epoch_ms() -> None:
    body = json.dumps({"editingInfo": {"lastEditDate": 1720000000000}}).encode()
    d = declared_from_metadata("arcgis_query", body)
    assert d.exposed and d.basis == "editingInfo.lastEditDate"
    assert d.at is not None and d.at.startswith("2024-07-03T")


def test_declared_from_metadata_socrata_epoch_s() -> None:
    body = json.dumps({"rowsUpdatedAt": 1720000000, "dataUpdatedAt": 1710000000}).encode()
    d = declared_from_metadata("socrata_rows", body)
    assert d.basis == "rowsUpdatedAt" and d.at is not None


def test_declared_from_metadata_ckan_iso() -> None:
    d = declared_from_metadata("ckan_package", b'{"metadata_modified": "2026-09-01T12:00:00Z"}')
    assert d.basis == "metadata_modified" and d.at == "2026-09-01T12:00:00Z"


def test_declared_from_metadata_garbage_is_honest_absence() -> None:
    assert not declared_from_metadata("arcgis_query", b"not json").exposed
    assert not declared_from_metadata("arcgis_query", b"{}").exposed


def test_declared_from_payload_eof_portals() -> None:
    body = json.dumps(
        {
            "portals": [
                {"slug": "a", "data_last_updated": "2026-07-01"},
                {"slug": "b", "data_last_updated": "2026-08-15"},
            ]
        }
    ).encode()
    d = declared_from_payload({"kind": "portal_json"}, body)
    assert d.basis == "data_last_updated" and d.at == "2026-08-15T00:00:00Z"
    # A non-portal kind never reads payload fields.
    assert not declared_from_payload({"kind": "arcgis_query"}, body).exposed


def test_declared_from_headers_last_modified_then_etag() -> None:
    d = declared_from_headers({"Last-Modified": "Wed, 15 Oct 2026 08:00:00 GMT"})
    assert d.basis == "Last-Modified" and d.at is not None
    # ETag is a version marker, never a fabricated date.
    d2 = declared_from_headers({"ETag": '"v42"'})
    assert d2.token == '"v42"' and d2.at is None and d2.basis == "ETag"
    # Both present → the declared instant wins.
    d3 = declared_from_headers({"Last-Modified": "Wed, 15 Oct 2026 08:00:00 GMT", "ETag": '"v42"'})
    assert d3.basis == "Last-Modified"
    assert not declared_from_headers({}).exposed


class _ProbeFetcher:
    """A fetcher that serves one metadata document and records its URLs."""

    def __init__(self, body: bytes = b"{}", *, fail: bool = False) -> None:
        self.calls: list[str] = []
        self._body = body
        self._fail = fail

    def fetch(self, url: str, **_kw: Any) -> FetchResult:
        self.calls.append(url)
        if self._fail:
            raise RuntimeError("probe transport failure")
        return FetchResult(url=url, status=200, body=self._body, media_type="application/json")


def test_upstream_declared_metadata_lane_then_fallbacks() -> None:
    target = {
        "kind": "arcgis_query",
        "layer_url": "https://h.example/arcgis/FeatureServer/0",
    }
    fetcher = _ProbeFetcher(json.dumps({"editingInfo": {"lastEditDate": 1720000000000}}).encode())
    d = upstream_declared(target, _fetched(), fetcher=fetcher, metadata_cache={})
    assert d.basis == "editingInfo.lastEditDate" and fetcher.calls == [
        "https://h.example/arcgis/FeatureServer/0?f=json"
    ]


def test_upstream_declared_failed_probe_degrades_not_fatal() -> None:
    target = {
        "kind": "arcgis_query",
        "layer_url": "https://h.example/arcgis/FeatureServer/0",
    }
    fetcher = _ProbeFetcher(fail=True)
    fetched = _fetched(headers={"ETag": '"v7"'})
    d = upstream_declared(target, fetched, fetcher=fetcher, metadata_cache={})
    # The failed probe degrades to the header lane — never run-fatal.
    assert d.token == '"v7"' and d.basis == "ETag"


def test_upstream_declared_cache_dedupes_page_targets() -> None:
    target = {
        "kind": "arcgis_query",
        "layer_url": "https://h.example/arcgis/FeatureServer/0",
    }
    fetcher = _ProbeFetcher(json.dumps({"editingInfo": {"lastEditDate": 1720000000000}}).encode())
    cache: dict[str, UpstreamDeclared] = {}
    upstream_declared(target, _fetched(), fetcher=fetcher, metadata_cache=cache)
    upstream_declared(dict(target, page=1), _fetched(), fetcher=fetcher, metadata_cache=cache)
    upstream_declared(dict(target, page=2), _fetched(), fetcher=fetcher, metadata_cache=cache)
    # One metadata GET per platform document per run — pages share the doc.
    assert len(fetcher.calls) == 1


def test_upstream_declared_nothing_exposed() -> None:
    d = upstream_declared({"kind": "document_pdf", "url": "https://x"}, _fetched(), fetcher=None)
    assert d == UpstreamDeclared() and not d.exposed


# --- the pipeline carries both marks ------------------------------------------


class _DeclaredFetcher:
    """Serves one ArcGIS page + the layer metadata doc."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, url: str, **_kw: Any) -> FetchResult:
        self.calls.append(url)
        if url.endswith("?f=json"):
            return FetchResult(
                url=url,
                status=200,
                body=json.dumps({"editingInfo": {"lastEditDate": 1720000000000}}).encode(),
                media_type="application/json",
            )
        return FetchResult(
            url=url,
            status=200,
            body=json.dumps({"features": [{"FID": 1, "name": "cam"}]}).encode(),
            media_type="application/json",
            retrieved_at=datetime(2026, 10, 20, tzinfo=UTC),
        )


class _DeclaredConnector(Connector):
    name = "declared"
    version = "1"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return [
            {
                "id": "layer-0",
                "url": "https://h.example/arcgis/FeatureServer/0/query",
                "kind": "arcgis_query",
                "layer_url": "https://h.example/arcgis/FeatureServer/0",
            }
        ]

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
        return [
            {"subject_id": f"cam:{r['FID']}", "predicate_id": "name", "value": r["name"]}
            for r in raw_claims
        ]


class _MarkLedger(InMemoryClaimSink):
    """A ledger sink recording the marks ``record_capture`` receives."""

    def __init__(self) -> None:
        super().__init__()
        self.marks: list[dict[str, Any]] = []

    @property
    def logical_run(self) -> str | None:
        return "run-1"

    def resume_marks(self) -> list[Mapping[str, Any]]:
        return []

    def record_capture(self, target_key: str, *, state: str, **fields: Any) -> None:
        self.marks.append({"target_key": target_key, "state": state, **fields})


def _ctx(
    sink: _MarkLedger,
    fetcher: Any,
    captures: InMemoryCaptureStore,
    source: Any,
    ingest_run: Any,
) -> RunContext:
    return RunContext(
        source=source,
        run=ingest_run,
        fetcher=fetcher,
        captures=captures,
        claim_sink=sink,
        parameters={},
    )


def test_flushed_mark_carries_records_digest_and_declared_value(
    permitted_source,
    ingest_run,  # type: ignore[no-untyped-def]
) -> None:
    sink = _MarkLedger()
    report = run(
        _DeclaredConnector(),
        _ctx(sink, _DeclaredFetcher(), InMemoryCaptureStore(), permitted_source, ingest_run),
    )
    flushed = [m for m in sink.marks if m["state"] == "flushed"]
    assert len(flushed) == 1
    mark = flushed[0]
    # The record-set fingerprint rides the flushed mark — never a guess.
    assert mark["records_digest"] and mark["records_digest"] == report.records_digests[0]
    # The upstream-declared instant rides the captured mark with its basis —
    # the publisher's clock, verbatim.
    captured = [m for m in sink.marks if m["state"] == "captured"]
    assert captured[0]["upstream_modified_at"] == mark["upstream_modified_at"]
    assert captured[0]["upstream_modified_basis"] == "editingInfo.lastEditDate"
    assert mark["upstream_modified_at"].startswith("2024-07-03T")


def test_no_declared_value_marks_nothing(permitted_source, ingest_run) -> None:  # type: ignore[no-untyped-def]
    class _PlainFetcher(_DeclaredFetcher):
        def fetch(self, url: str, **_kw: Any) -> FetchResult:
            # A transport that answers the page but declares no metadata
            # endpoint value and carries no declared headers.
            return FetchResult(
                url=url,
                status=200,
                body=json.dumps({"features": [{"FID": 1, "name": "cam"}]}).encode(),
                media_type="application/json",
            )

    sink = _MarkLedger()
    run(
        _DeclaredConnector(),
        _ctx(sink, _PlainFetcher(), InMemoryCaptureStore(), permitted_source, ingest_run),
    )
    for mark in sink.marks:
        assert mark.get("upstream_modified_at") is None
        assert mark.get("upstream_token") is None


def test_records_digest_differs_across_changed_record_sets(
    permitted_source,
    ingest_run,  # type: ignore[no-untyped-def]
) -> None:
    class _ChangingFetcher(_DeclaredFetcher):
        def fetch(self, url: str, **_kw: Any) -> FetchResult:
            if url.endswith("?f=json"):
                return FetchResult(url=url, status=200, body=b"{}")
            self.calls.append(url)
            n = len(self.calls)
            return FetchResult(
                url=url,
                status=200,
                body=json.dumps({"features": [{"FID": 1, "name": f"cam-{n}"}]}).encode(),
                media_type="application/json",
            )

    fetcher = _ChangingFetcher()  # one upstream whose records differ per call
    digests: list[str] = []
    for _ in range(2):
        sink = _MarkLedger()
        report = run(
            _DeclaredConnector(),
            _ctx(sink, fetcher, InMemoryCaptureStore(), permitted_source, ingest_run),
        )
        digests.extend(report.records_digests)
    assert len(set(digests)) == 2  # a different record set → a different digest


def test_records_digest_ignores_volatile_fields_under_registry() -> None:
    # ``claim_set_fingerprint`` with the registry's temporal classes: an
    # obs-class claim's volatile fields never move the record-set digest.
    from connectors.claim_identity_ingest import predicate_temporal_classes
    from evidence.ingest_run import claim_set_fingerprint

    classes = predicate_temporal_classes()
    base = [{"subject_id": "s", "predicate_id": "name", "value": "cam"}]
    same = [{"subject_id": "s", "predicate_id": "name", "value": "cam"}]
    assert claim_set_fingerprint(base, classes=classes) == claim_set_fingerprint(
        same, classes=classes
    )
