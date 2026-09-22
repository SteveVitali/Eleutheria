# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.4 — credential transport hygiene for the keyed live sources (HG-09).

The SAM.gov / OpenStates / data.gov keys authenticate the request on the
**header** seam — never in the request URL. A key riding the query string would
be copied verbatim into ``FetchResult.url`` and from there into the capture's
recorded ``source_uri``, the fetch record's ``rate_limit_events``, refusal and
challenge messages, the run rows under ``gs://…-sig-restricted/ops/runs/``, and
the committed ``docs/build/reports/live_runs/`` records — a credential leak into
the append-only spine and build memory.

These tests pin the contract: with the key env var set, the connector's
``fetch()`` carries the credential in the reviewed header (``api_key_header`` in
the vocab) and the recorded URL surface stays credential-free; keyless, no
credential header is sent and the shared layer's recorded refusal/challenge
stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import pytest
from connectors.accountability import (
    AccountabilityConnector,
    congress_gov_config,
    openstates_config,
)
from connectors.agency_registry import AgencyRegistryConnector, cde_config
from connectors.live_targets import live_targets
from connectors.procurement import ProcurementConnector, sam_gov_config
from connectors.registry import get
from connectors.stages import FetchResult, InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

_SENTINEL = "test-sentinel-key-value-7f3a9c"  # a stand-in, never a real key


@dataclass
class _RecordingFetcher:
    """A fetcher stub that records every (url, headers, body) handed to it."""

    calls: list[dict[str, Any]] = field(default_factory=list)

    def fetch(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.calls.append({"url": url, "headers": dict(headers or {}), "body": body})
        return FetchResult(url=url, status=200, body=b"{}", media_type="application/json")


def _ctx(source_id: str, fetcher: _RecordingFetcher) -> RunContext:
    return RunContext(
        source=get(source_id),
        run=IngestRun("credential-test", "0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )


def _keyed_cases() -> list[tuple[str, Any, str, str]]:
    """(source id, connector, env var, expected header) for each keyed source."""
    return [
        (
            "sam_gov",
            ProcurementConnector(),
            "SIG_SAM_GOV_KEY",
            str(sam_gov_config()["api_key_header"]),
        ),
        (
            "openstates",
            AccountabilityConnector(),
            "SIG_OPENSTATES_KEY",
            str(openstates_config()["api_key_header"]),
        ),
        (
            "fbi_cde_agency_registry",
            AgencyRegistryConnector(),
            "SIG_DATA_GOV_KEY",
            str(cde_config()["api_key_header"]),
        ),
        (
            # P26.12 — the federal legislation sweep shares the api.data.gov
            # key with the FBI CDE source; it rides the documented X-Api-Key
            # header, never the URL.
            "congress_gov",
            AccountabilityConnector(),
            "SIG_DATA_GOV_KEY",
            str(congress_gov_config()["api_key_header"]),
        ),
    ]


@pytest.mark.parametrize(
    ("source_id", "connector", "env_var", "header"),
    _keyed_cases(),
    ids=[c[0] for c in _keyed_cases()],
)
def test_api_key_rides_the_header_never_the_url(
    monkeypatch: pytest.MonkeyPatch,
    source_id: str,
    connector: Any,
    env_var: str,
    header: str,
) -> None:
    """With the key exported, fetch() sends it as a header; every recorded URL
    surface (FetchResult.url → CaptureRef.source_uri) stays credential-free."""
    monkeypatch.setenv(env_var, _SENTINEL)
    fetcher = _RecordingFetcher()
    ctx = _ctx(source_id, fetcher)
    for target in live_targets(source_id):
        connector.fetch(ctx, target)
    assert fetcher.calls, f"{source_id}: no fetch issued"
    for call in fetcher.calls:
        assert _SENTINEL not in call["url"], (
            f"{source_id}: the credential leaked into the request URL — "
            "it would be recorded as source_uri / in run rows (HG-09)"
        )
        assert call["headers"].get(header) == _SENTINEL, (
            f"{source_id}: expected the {header} header to carry the key"
        )


def test_keyed_fetch_records_no_credential_in_source_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end at the capture seam: the capture's recorded source_uri (what
    lands in the OCFL inventory + claim locators) carries no key material."""
    monkeypatch.setenv("SIG_OPENSTATES_KEY", _SENTINEL)
    fetcher = _RecordingFetcher()
    connector = AccountabilityConnector()
    ctx = _ctx("openstates", fetcher)
    fetched = connector.fetch(ctx, live_targets("openstates")[0])
    capture = connector.capture(ctx, fetched)
    assert _SENTINEL not in capture.source_uri
    assert _SENTINEL not in fetched.url
    query = urlsplit(capture.source_uri).query.lower()
    assert "apikey" not in query and "api_key" not in query


@pytest.mark.parametrize(
    ("source_id", "connector", "env_var", "header"),
    _keyed_cases(),
    ids=[c[0] for c in _keyed_cases()],
)
def test_keyless_fetch_sends_no_credential_header(
    monkeypatch: pytest.MonkeyPatch,
    source_id: str,
    connector: Any,
    env_var: str,
    header: str,
) -> None:
    """Keyless, no credential header is sent — the upstream's recorded refusal /
    disappearance (SAM.gov 404, OpenStates 403) stands, never defeated. The CDE
    connector falls back to api.data.gov's documented public DEMO_KEY, which
    still travels the header, not the URL."""
    monkeypatch.delenv(env_var, raising=False)
    fetcher = _RecordingFetcher()
    ctx = _ctx(source_id, fetcher)
    for target in live_targets(source_id):
        connector.fetch(ctx, target)
    for call in fetcher.calls:
        sent = call["headers"].get(header)
        if source_id == "fbi_cde_agency_registry":
            assert sent == "DEMO_KEY"  # the documented public fallback
        else:
            assert sent is None, f"{source_id}: a credential header was sent keyless"
