# SPDX-License-Identifier: Apache-2.0
"""P37.12 (D-SOURCES.7-2 / OP-13): the keyed US 511 JSON API lanes.

The acceptance shape — *keyed targets run live without a key in the repo* —
in five fail-closed parts:

1. The ten graduated ``[[targets]]`` rows expand into declared single-page
   fetch targets carrying only the ``SIG_*`` env-var NAME (``api_key_env``),
   never a credential value.
2. A fetch whose env var is unset raises :class:`KeyNotProvisioned` BEFORE
   any egress — the pipeline records it as a per-target refusal and the run
   continues (never a crash that abandons the remaining targets).
3. With the env var provisioned, the Iteris ``key`` rides the wire URL only:
   every recorded surface (per_fetch, conduct_decisions, FetchResult.url →
   the capture's source_uri) carries the credential-free URL; OHGO's key
   rides the documented ``Authorization: APIKEY`` header.
4. The declared contracts parse STRICTLY: the Iteris top-level row array and
   OHGO's ApiResult envelope (truncation = ContentDrift, never a partial
   registry), and the emitted records carry media-field NAMES on
   ``excluded_fields`` — never their values (Part VIII).
5. No key literal exists anywhere in the committed tree.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from connectors.dot_511 import (
    Dot511Connector,
    KeyedSpecNotDeclared,
    assert_target_keyed_spec,
    expand_registry_rows,
    registry_targets,
    target_keyed_violations,
    target_table,
)
from connectors.net import PoliteFetcher
from connectors.stages import FetchResult, KeyNotProvisioned

KEYED_KINDS = {"iteris_511_rows", "ohgo_511_cameras"}

#: The ten graduated keyed rows and their (source_id, kind, env-name).
EXPECTED_KEYED = {
    "fl511_api": ("dot_511_fl", "iteris_511_rows", "SIG_US511_FL_KEY"),
    "511ny_api": ("dot_511_ny", "iteris_511_rows", "SIG_US511_NY_KEY"),
    "az511_api": ("dot_511_az", "iteris_511_rows", "SIG_US511_AZ_KEY"),
    "nvroads_api": ("dot_511_nvroads", "iteris_511_rows", "SIG_US511_NV_KEY"),
    "ohgo_api": ("dot_511_oh", "ohgo_511_cameras", "SIG_US511_OH_KEY"),
    "511pa": ("dot_511_pa", "iteris_511_rows", "SIG_US511_PA_KEY"),
    "511wi": ("dot_511_wi", "iteris_511_rows", "SIG_US511_WI_KEY"),
    "511alaska": ("dot_511_ak", "iteris_511_rows", "SIG_US511_AK_KEY"),
    "ctroads": ("dot_511_ct", "iteris_511_rows", "SIG_US511_CT_KEY"),
    "newengland511": ("dot_511_newengland", "iteris_511_rows", "SIG_US511_NE_KEY"),
}


# --- fakes -----------------------------------------------------------------


@dataclass
class _RobotsResult:
    text: str | None
    status: int


class _FakeTransport:
    """A Transport that records every wire URL + headers it is asked for."""

    def __init__(self, body: bytes = b"[]") -> None:
        self.requests: list[dict[str, Any]] = []
        self._body = body

    def robots(self, robots_url: str) -> _RobotsResult:
        return _RobotsResult(text="User-agent: *\nAllow: /\n", status=200)

    def request(self, url: str, *, user_agent: str, **kwargs: Any) -> FetchResult:
        # A real transport reports the WIRE url it fetched — the fetcher's
        # auth_param seam must sanitize it back out of the recorded result.
        self.requests.append({"url": url, "headers": dict(kwargs.get("headers") or {})})
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime.now(UTC),
        )


class _Ctx:
    """The minimal RunContext stand-in a keyed fetch needs."""

    def __init__(self, fetcher: PoliteFetcher) -> None:
        self.fetcher = fetcher
        self.source = type("S", (), {"id": "dot_511_fl"})()


# --- 1. registry graduation --------------------------------------------------


def test_ten_keyed_targets_graduated() -> None:
    """Every EXPECTED_KEYED row is a [[targets]] row — never again enumerated."""
    targets = {str(r.get("id")): r for r in target_table().get("targets", [])}
    enumerated = {str(r.get("id")) for r in target_table().get("enumerated", [])}
    for row_id, (source_id, kind, env) in EXPECTED_KEYED.items():
        row = targets.get(row_id)
        assert row is not None, f"{row_id} missing from [[targets]]"
        assert row_id not in enumerated, f"{row_id} still [[enumerated]]"
        assert str(row["source_id"]) == source_id
        assert str(row["kind"]) == kind
        assert str(row["api_key_env"]) == env
        assert str(row.get("technology") or "").strip()


def test_keyed_violations_clean() -> None:
    """The committed registry passes the keyed-declaration validator."""
    assert target_keyed_violations() == []


def test_keyed_rows_expand_to_single_declared_page() -> None:
    """Each keyed source expands to exactly one declared fetch target."""
    for row_id, (source_id, kind, env) in EXPECTED_KEYED.items():
        targets = registry_targets(source_id)
        assert len(targets) == 1, f"{source_id} expanded to {len(targets)} targets"
        target = targets[0]
        assert target["id"] == row_id
        assert target["kind"] == kind
        assert target["api_key_env"] == env
        assert target["page"] == 0 and target["page_count"] == 1
        # No credential or credential-shaped value ever lands in the target.
        for value in target.values():
            assert not re.search(r"(?i)(key|token|secret)\s*=\s*[A-Za-z0-9]{8,}", str(value))


def test_keyed_spec_rejects_non_env_name() -> None:
    """A key literal or non-SIG_* name in api_key_env is a registry defect."""
    with pytest.raises(KeyedSpecNotDeclared):
        assert_target_keyed_spec(
            {"id": "x", "kind": "iteris_511_rows", "api_key_env": "abc123secret"}
        )
    with pytest.raises(KeyedSpecNotDeclared):
        assert_target_keyed_spec(
            {"id": "x", "kind": "iteris_511_rows"}  # missing declaration
        )
    # api_key_env on a non-keyed kind is a defect too — keyed-only data.
    with pytest.raises(KeyedSpecNotDeclared):
        assert_target_keyed_spec(
            {"id": "x", "kind": "arcgis_query", "api_key_env": "SIG_US511_FL_KEY"}
        )


def test_unknown_kind_still_refused() -> None:
    """An unregistered kind stays a hard expansion error (no new platform sneaks in)."""
    with pytest.raises(ValueError, match="unknown kind"):
        expand_registry_rows(
            [
                {
                    "id": "x",
                    "kind": "bogus_kind",
                    "source_id": "s",
                    "layer_url": "u",
                    "state": "FL",
                    "agency": "a",
                    "technology": "fixed-camera-ptz",
                    "axis_order": "lon-lat",
                }
            ],
            source_id="s",
        )


# --- 2. unprovisioned fetch: recorded refusal, zero egress --------------------


def test_unprovisioned_iteris_fetch_refuses_zero_egress() -> None:
    """Absent the env binding the fetch refuses before any request is issued."""
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher)
    target = registry_targets("dot_511_fl")[0]
    env = {k: v for k, v in os.environ.items() if k != "SIG_US511_FL_KEY"}
    with patch.dict(os.environ, env, clear=True), pytest.raises(KeyNotProvisioned) as exc:
        connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert exc.value.env_name == "SIG_US511_FL_KEY"
    assert transport.requests == []  # zero egress — before even the robots probe


def test_unprovisioned_ohgo_fetch_refuses_zero_egress() -> None:
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher)
    target = registry_targets("dot_511_oh")[0]
    env = {k: v for k, v in os.environ.items() if k != "SIG_US511_OH_KEY"}
    with patch.dict(os.environ, env, clear=True), pytest.raises(KeyNotProvisioned):
        connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert transport.requests == []


# --- 3. provisioned fetch: credential on the wire, never recorded -------------


def test_iteris_key_rides_wire_url_never_recorded() -> None:
    """The ?key= lands in the transport request; every record keeps it out."""
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher)
    target = registry_targets("dot_511_fl")[0]
    secret = "TESTKEY-not-a-real-key-123"
    with patch.dict(os.environ, {"SIG_US511_FL_KEY": secret}):
        result = connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert len(transport.requests) == 1
    wire = transport.requests[0]["url"]
    assert f"key={secret}" in wire  # the credential reached the wire
    # Every recorded surface is credential-free.
    assert secret not in result.url
    assert result.url == target["url"]
    for row in fetcher.per_fetch:
        assert secret not in json.dumps(row)
    for row in fetcher.conduct_decisions:
        assert secret not in json.dumps(row)
    for row in fetcher.reservations + fetcher.robots_disregarded:
        assert secret not in json.dumps(row)


def test_ohgo_key_rides_authorization_header() -> None:
    """OHGO's documented APIKEY header — the URL stays untouched."""
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher)
    target = registry_targets("dot_511_oh")[0]
    secret = "TESTKEY-not-a-real-key-456"
    with patch.dict(os.environ, {"SIG_US511_OH_KEY": secret}):
        result = connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req["headers"].get("Authorization") == f"APIKEY {secret}"
    assert secret not in req["url"]
    assert result.url == target["url"]
    for row in fetcher.per_fetch + fetcher.conduct_decisions:
        assert secret not in json.dumps(row)


# --- 4. the declared contracts parse strictly ---------------------------------


def _capture(data: bytes, source_uri: str) -> tuple[Any, Any]:
    """A CaptureRef-ish pair parse() needs: (capture, ctx carrying captures+source)."""
    from connectors.stages import CaptureRef

    ref = CaptureRef(
        digest="d" * 8,
        media_type="application/json",
        source_uri=source_uri,
        byte_size=len(data),
    )
    captures = {ref.digest: data}
    ctx = type(
        "C",
        (),
        {
            "captures": type("CS", (), {"get": staticmethod(lambda d: captures[d])})(),
            "source": type("S", (), {"id": "dot_511_fl"})(),
            "parameters": {"targets": registry_targets("dot_511_fl")},
        },
    )()
    return ref, ctx


ITERIS_ROWS = [
    {
        "Id": 101,
        "Source": "District",
        "SourceId": "d101",
        "Roadway": "I-95",
        "Direction": "Northbound",
        "Latitude": 27.96,
        "Longitude": -82.45,
        "Location": "I-95 at Sample Rd",
        "SortOrder": 0,
        "Views": [{"Id": 101, "Url": "https://fl511.com/map/Cctv/101", "Status": "Enabled"}],
    },
    {
        "Id": "cam-002",
        "RoadwayName": "I-4",
        "DirectionOfTravel": "Westbound",
        "Latitude": 28.54,
        "Longitude": -81.38,
        "Name": "I-4 @ MM 72",
        "Url": "https://fl511.com/map/Cctv/002",
        "Status": "Enabled",
        "Organization": "FDOT D5",
    },
]


def test_iteris_array_parses_and_emits_registry_rows() -> None:
    """The declared row-array shape emits camera records; Views stays excluded."""
    payload = json.dumps(ITERIS_ROWS).encode()
    ref, ctx = _capture(payload, registry_targets("dot_511_fl")[0]["url"])
    connector = Dot511Connector()
    parsed = connector.parse(ctx, ref)
    raw = connector.extract(ctx, parsed)
    assert len(raw) == 2
    for record in raw:
        # The Views/Url values never reach the record — names only.
        assert "Views" in record["excluded_fields"] or "Url" in record["excluded_fields"]
        assert not any("fl511.com/map" in str(v) for v in record["fields"].values()), (
            "a feed-content URL reached the emitted record"
        )
    normalized = connector.normalize(ctx, raw)
    claims = [r for r in normalized if r.get("record_kind") == "claim"]
    assert any(r["predicate_id"] == "camera_latitude" for r in claims)
    assert any(
        r["predicate_id"] == "camera_jurisdiction" and r.get("value") == "FL" for r in claims
    )
    blob = json.dumps(normalized)
    assert "TESTKEY" not in blob and "map/Cctv" not in blob


def test_iteris_error_envelope_is_drift() -> None:
    """A keyed-out or object payload is ContentDrift — never a silent empty."""
    from connectors.stages import ContentDrift

    for body in (
        b'{"Message": "Invalid Key"}',
        b'{"Error": "Invalid Key"}',
        b'{"cameras": []}',
        b"<html>app shell</html>",
    ):
        ref, ctx = _capture(body, registry_targets("dot_511_fl")[0]["url"])
        with pytest.raises(ContentDrift):
            Dot511Connector().parse(ctx, ref)


def test_iteris_non_object_row_is_drift() -> None:
    from connectors.stages import ContentDrift

    ref, ctx = _capture(b'[["not","an","object"]]', registry_targets("dot_511_fl")[0]["url"])
    with pytest.raises(ContentDrift):
        Dot511Connector().parse(ctx, ref)


OHGO_RESULT = {
    "Links": [],
    "LastUpdated": "2026-11-07T00:00:00Z",
    "TotalPageCount": 1,
    "TotalResultCount": 2,
    "CurrentResultCount": 2,
    "Results": [
        {
            "Links": [{"Href": "https://publicapi.ohgo.com/api/v1/cameras/1", "Rel": "self"}],
            "Id": "cam-oh-1",
            "Latitude": 41.97,
            "Longitude": -83.61,
            "Location": "I-75 at SR-582",
            "Description": "Camera site",
            "CameraViews": [
                {"Direction": "NB", "SmallUrl": "https://publicapi.ohgo.com/img/1.jpg"}
            ],
        },
        {
            "Links": [],
            "Id": "cam-oh-2",
            "Latitude": 39.96,
            "Longitude": -82.99,
            "Location": "I-70 at I-270",
            "Description": "Camera site",
            "CameraViews": [],
        },
    ],
}


def _ohgo_ctx(data: bytes):
    return _capture(data, registry_targets("dot_511_oh")[0]["url"])


def test_ohgo_result_parses_and_emits() -> None:
    ref, ctx = _ohgo_ctx(json.dumps(OHGO_RESULT).encode())
    # The OHGO source id flows through the ctx.source used in _capture; rebuild
    # a ctx whose source.id is dot_511_oh for the emit path's source stamp.
    ctx.source.id = "dot_511_oh"
    connector = Dot511Connector()
    parsed = connector.parse(ctx, ref)
    raw = connector.extract(ctx, parsed)
    assert len(raw) == 2
    for record in raw:
        assert "CameraViews" in record["excluded_fields"] or "Links" in record["excluded_fields"]
        assert "ohgo.com/img" not in json.dumps(record["fields"])
    normalized = connector.normalize(ctx, raw)
    assert any(r.get("predicate_id") == "camera_latitude" for r in normalized)


def test_ohgo_truncated_page_is_drift() -> None:
    """CurrentResultCount < TotalResultCount — a partial inventory is refused."""
    from connectors.stages import ContentDrift

    drifted = {**OHGO_RESULT, "CurrentResultCount": 1}
    ref, ctx = _ohgo_ctx(json.dumps(drifted).encode())
    with pytest.raises(ContentDrift):
        Dot511Connector().parse(ctx, ref)


def test_ohgo_malformed_envelope_is_drift() -> None:
    from connectors.stages import ContentDrift

    for body in (b"[1,2]", b'{"Error": "key required"}', b"not json"):
        ref, ctx = _ohgo_ctx(body)
        with pytest.raises(ContentDrift):
            Dot511Connector().parse(ctx, ref)


# --- 5. no credential literal in the committed tree -----------------------------


def test_no_key_literal_in_registered_data() -> None:
    """The registry rows and cadence bindings carry env/secret NAMES only."""
    for row in target_table().get("targets", []):
        env = str(row.get("api_key_env") or "")
        if env:
            assert re.fullmatch(r"SIG_[A-Z0-9_]+", env), env
    import tomllib
    from pathlib import Path

    cadence = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "ops" / "cadence.toml").read_text()
    )
    keyed_sources = {s for s, _, _ in EXPECTED_KEYED.values()}
    for row in cadence.get("sources", []):
        if row.get("id") in keyed_sources:
            assert row.get("state") == "paused", row["id"]
            for env_name, secret_name in (row.get("secrets") or {}).items():
                assert re.fullmatch(r"SIG_US511_[A-Z0-9_]+", env_name), env_name
                assert re.fullmatch(r"sig-us511-[a-z0-9-]+", secret_name), secret_name
