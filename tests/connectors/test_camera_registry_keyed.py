# SPDX-License-Identifier: Apache-2.0
"""P37.70 (D-SOURCES.8-2 / OP-13): the keyed AU traffic-camera GeoJSON lanes.

The acceptance shape — *keyed targets run live without a key in the repo* —
in five fail-closed parts, mirroring the P37.12 acceptance shape:

1. The two graduated ``[[targets]]`` rows (``nsw_live_traffic_cameras``,
   ``qld_qldtraffic_api``) expand into declared single-page fetch targets
   carrying only the ``SIG_*`` env-var NAME (``api_key_env``), never a
   credential value; ``qldc_au_cctv_cameras`` records the E4-R4c = b
   supersession while staying a gated target.
2. A fetch whose env var is unset raises :class:`KeyNotProvisioned` BEFORE
   any egress — recorded per-target, never a crash.
3. With the env var provisioned, QLDTraffic's ``apikey`` rides the wire URL
   only (every recorded surface stays credential-free) and TfNSW's key rides
   the documented ``Authorization: apikey`` header.
4. The declared contracts parse STRICTLY: a GeoJSON ``FeatureCollection`` of
   Features (and NSW's documented ``rights`` member — its absence is drift,
   never a silently re-licensed read); emitted records carry media-field
   NAMES on ``excluded_fields`` — never their values (Part VIII).
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
    registry_targets,
    target_keyed_violations,
    target_table,
)
from connectors.net import PoliteFetcher
from connectors.stages import FetchResult, KeyNotProvisioned

#: The two graduated keyed rows and their (source_id, kind, env-name).
EXPECTED_KEYED = {
    "qld_qldtraffic_api": ("camreg_qldtraffic_au", "qldtraffic_geojson", "SIG_QLDTRAFFIC_KEY"),
    "nsw_live_traffic_cameras": ("camreg_nsw_live_au", "nsw_live_geojson", "SIG_NSW_LIVE_KEY"),
}


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
        self.requests.append({"url": url, "headers": dict(kwargs.get("headers") or {})})
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime.now(UTC),
        )


class _Ctx:
    def __init__(self, fetcher: PoliteFetcher, source_id: str = "camreg_qldtraffic_au") -> None:
        self.fetcher = fetcher
        self.source = type("S", (), {"id": source_id})()


# --- 1. registry graduation + the supersession record -------------------------


def test_two_keyed_targets_graduated() -> None:
    """Both keyed AU rows are [[targets]] rows — never again enumerated."""
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
        assert str(row.get("jurisdiction_scheme")) == "iso.3166_2"


def test_keyed_violations_clean() -> None:
    assert target_keyed_violations() == []


def test_qldc_arcgis_row_records_the_supersession() -> None:
    """E4-R4c = b: camreg_qldc_au stays a gated target, notes record the swap."""
    targets = {str(r.get("id")): r for r in target_table().get("targets", [])}
    row = targets.get("qldc_au_cctv_cameras")
    assert row is not None
    assert str(row["source_id"]) == "camreg_qldc_au"
    assert "E4-R4c" in str(row.get("notes"))
    assert "camreg_qldtraffic_au" in str(row.get("notes"))


def test_keyed_rows_expand_to_single_declared_page() -> None:
    for row_id, (source_id, kind, env) in EXPECTED_KEYED.items():
        targets = registry_targets(source_id)
        assert len(targets) == 1, f"{source_id} expanded to {len(targets)} targets"
        target = targets[0]
        assert target["id"] == row_id
        assert target["kind"] == kind
        assert target["api_key_env"] == env
        assert target["page"] == 0 and target["page_count"] == 1
        for value in target.values():
            assert not re.search(r"(?i)(key|token|secret)\s*=\s*[A-Za-z0-9]{8,}", str(value))


def test_keyed_spec_rejects_non_env_name() -> None:
    for kind in ("qldtraffic_geojson", "nsw_live_geojson"):
        with pytest.raises(KeyedSpecNotDeclared):
            assert_target_keyed_spec({"id": "x", "kind": kind, "api_key_env": "abc123secret"})
        with pytest.raises(KeyedSpecNotDeclared):
            assert_target_keyed_spec({"id": "x", "kind": kind})


# --- 2. unprovisioned fetch: recorded refusal, zero egress --------------------


@pytest.mark.parametrize(
    ("source_id", "env_name"),
    [
        ("camreg_qldtraffic_au", "SIG_QLDTRAFFIC_KEY"),
        ("camreg_nsw_live_au", "SIG_NSW_LIVE_KEY"),
    ],
)
def test_unprovisioned_fetch_refuses_zero_egress(source_id: str, env_name: str) -> None:
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher, source_id)
    target = registry_targets(source_id)[0]
    env = {k: v for k, v in os.environ.items() if k != env_name}
    with patch.dict(os.environ, env, clear=True), pytest.raises(KeyNotProvisioned) as exc:
        connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert exc.value.env_name == env_name
    assert transport.requests == []  # zero egress — before even the robots probe


# --- 3. provisioned fetch: credential on the wire, never recorded -------------


def test_qldtraffic_key_rides_wire_url_never_recorded() -> None:
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher)
    target = registry_targets("camreg_qldtraffic_au")[0]
    secret = "TESTKEY-not-a-real-key-qld"
    with patch.dict(os.environ, {"SIG_QLDTRAFFIC_KEY": secret}):
        result = connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert len(transport.requests) == 1
    wire = transport.requests[0]["url"]
    assert f"apikey={secret}" in wire
    assert secret not in result.url
    assert result.url == target["url"]
    for row in fetcher.per_fetch + fetcher.conduct_decisions:
        assert secret not in json.dumps(row)


def test_nsw_key_rides_authorization_header() -> None:
    transport = _FakeTransport()
    fetcher = PoliteFetcher(
        connector_name="dot_511",
        connector_version="test",
        transport=transport,  # type: ignore[arg-type]
    )
    connector = Dot511Connector()
    ctx = _Ctx(fetcher, "camreg_nsw_live_au")
    target = registry_targets("camreg_nsw_live_au")[0]
    secret = "TESTKEY-not-a-real-key-nsw"
    with patch.dict(os.environ, {"SIG_NSW_LIVE_KEY": secret}):
        result = connector.fetch(ctx, target)  # type: ignore[arg-type]
    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req["headers"].get("Authorization") == f"apikey {secret}"
    assert secret not in req["url"]
    assert result.url == target["url"]
    for row in fetcher.per_fetch + fetcher.conduct_decisions:
        assert secret not in json.dumps(row)


# --- 4. the declared contracts parse strictly ---------------------------------


def _capture(data: bytes, source_id: str) -> tuple[Any, Any]:
    from connectors.stages import CaptureRef

    ref = CaptureRef(
        digest="d" * 8,
        media_type="application/json",
        source_uri=registry_targets(source_id)[0]["url"],
        byte_size=len(data),
    )
    captures = {ref.digest: data}
    ctx = type(
        "C",
        (),
        {
            "captures": type("CS", (), {"get": staticmethod(lambda d: captures[d])})(),
            "source": type("S", (), {"id": source_id})(),
            "parameters": {"targets": registry_targets(source_id)},
        },
    )()
    return ref, ctx


QLD_FC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "qld-cam-1",
            "geometry": {"type": "Point", "coordinates": [153.02, -27.47]},
            "properties": {
                "description": "Gateway Mwy at Lytton",
                "image_url": "https://api.qldtraffic.qld.gov.au/img/1.jpg",
                "region": "Metro",
            },
        },
        {
            "type": "Feature",
            "id": "qld-cam-2",
            "geometry": {"type": "Point", "coordinates": [151.95, -27.56]},
            "properties": {"description": "Warrego Hwy at Toowoomba"},
        },
    ],
}

NSW_FC = {
    "type": "FeatureCollection",
    "rights": {"copyright": "Transport for NSW", "licence": "CC BY 4.0"},
    "features": [
        {
            "type": "Feature",
            "id": "d2e386",
            "geometry": {"type": "Point", "coordinates": [151.206, -33.868]},
            "properties": {
                "title": "Anzac Parade at Alison Road",
                "direction": "south",
                "href": "https://api.transport.nsw.gov.au/img/d2e386.jpg",
                "view": "Looking south",
                "region": "Sydney",
            },
        }
    ],
}


def test_qld_feature_collection_parses_and_emits() -> None:
    payload = json.dumps(QLD_FC).encode()
    ref, ctx = _capture(payload, "camreg_qldtraffic_au")
    connector = Dot511Connector()
    parsed = connector.parse(ctx, ref)
    raw = connector.extract(ctx, parsed)
    assert len(raw) == 2
    assert "image_url" in raw[0]["excluded_fields"]
    for record in raw:
        assert "api.qldtraffic.qld.gov.au/img" not in json.dumps(record["fields"])
    normalized = connector.normalize(ctx, raw)
    claims = [r for r in normalized if r.get("record_kind") == "claim"]
    assert any(r["predicate_id"] == "camera_latitude" for r in claims)
    assert any(
        r["predicate_id"] == "camera_jurisdiction" and r.get("value") == "AU-QLD" for r in claims
    )


def test_nsw_feature_collection_parses_and_emits() -> None:
    payload = json.dumps(NSW_FC).encode()
    ref, ctx = _capture(payload, "camreg_nsw_live_au")
    connector = Dot511Connector()
    parsed = connector.parse(ctx, ref)
    assert parsed["payload"].get("rights") == NSW_FC["rights"]
    raw = connector.extract(ctx, parsed)
    assert len(raw) == 1
    assert "href" in raw[0]["excluded_fields"]
    assert "d2e386" in json.dumps(raw[0]["fields"])
    normalized = connector.normalize(ctx, raw)
    assert any(r.get("predicate_id") == "camera_latitude" for r in normalized)
    assert any(
        r.get("predicate_id") == "camera_jurisdiction" and r.get("value") == "AU-NSW"
        for r in normalized
    )


@pytest.mark.parametrize(
    "body",
    [
        b'{"Message": "Missing Authentication Token"}',
        b'{"type": "Feature", "features": []}',
        b'{"type": "FeatureCollection"}',
        b"<html>app shell</html>",
        b'{"type": "FeatureCollection", "features": [{"type": "X", "properties": {}}]}',
        b'{"type": "FeatureCollection", "features": [{"type": "Feature"}]}',
    ],
)
def test_geojson_drift_shapes_refused(body: bytes) -> None:
    from connectors.stages import ContentDrift

    for source_id in ("camreg_qldtraffic_au", "camreg_nsw_live_au"):
        ref, ctx = _capture(body, source_id)
        with pytest.raises(ContentDrift):
            Dot511Connector().parse(ctx, ref)


def test_nsw_missing_rights_member_is_drift() -> None:
    """NSW's documented `rights` member absent — the contract is broken, never re-licensed."""
    from connectors.stages import ContentDrift

    stripped = {k: v for k, v in NSW_FC.items() if k != "rights"}
    ref, ctx = _capture(json.dumps(stripped).encode(), "camreg_nsw_live_au")
    with pytest.raises(ContentDrift):
        Dot511Connector().parse(ctx, ref)


def test_nsw_unpaginated_single_page_only() -> None:
    """The declared contract is one whole-inventory file — the page_count pin."""
    target = registry_targets("camreg_nsw_live_au")[0]
    assert target["page_count"] == 1 and target["page"] == 0


# --- 5. no credential literal in the committed tree -----------------------------


def test_no_key_literal_in_registered_data() -> None:
    import tomllib
    from pathlib import Path

    for row in target_table().get("targets", []):
        env = str(row.get("api_key_env") or "")
        if env:
            assert re.fullmatch(r"SIG_[A-Z0-9_]+", env), env
    cadence = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "ops" / "cadence.toml").read_text()
    )
    keyed_sources = {s for s, _, _ in EXPECTED_KEYED.values()}
    seen = set()
    for row in cadence.get("sources", []):
        if row.get("id") in keyed_sources:
            seen.add(row["id"])
            assert row.get("state") == "paused", row["id"]
            for env_name, secret_name in (row.get("secrets") or {}).items():
                assert re.fullmatch(r"SIG_[A-Z0-9_]+", env_name), env_name
                assert re.fullmatch(r"sig-[a-z0-9-]+", secret_name), secret_name
    assert seen == keyed_sources
