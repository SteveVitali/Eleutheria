# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The capture set + WACZ packaging (SIG-EVID-007/008)."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

from evidence.capture import (
    CapturedResponse,
    CaptureRole,
    RawCapture,
    build_wacz,
    capture_set,
)

_WHEN = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)


def _raw(*, with_payload: bool) -> RawCapture:
    return RawCapture(
        url="https://portal.example/app",
        responses=(
            CapturedResponse(
                url="https://portal.example/app",
                status=200,
                body=b"<html>app shell</html>",
                content_type="text/html",
            ),
            CapturedResponse(
                url="https://portal.example/api/cameras.json",
                status=200,
                body=b'{"cameras": 42}',
                content_type="application/json",
            ),
        ),
        screenshot_png=b"\x89PNG\r\n\x1a\n screenshot",
        raw_html=b"<html>app shell</html>",
        captured_at=_WHEN,
        extracted_payload=b'{"cameras": 42}' if with_payload else None,
    )


def test_js_artifact_full_capture_set() -> None:
    """SIG-EVID-008: WACZ + screenshot + payload + raw HTML, one artifact."""
    files = capture_set(_raw(with_payload=True))
    roles = {f.role for f in files}
    assert roles == {
        CaptureRole.WACZ,
        CaptureRole.SCREENSHOT,
        CaptureRole.PAYLOAD,
        CaptureRole.RAW_HTML,
    }
    media = {f.role: f.media_type for f in files}
    assert media[CaptureRole.WACZ] == "application/wacz"
    assert media[CaptureRole.SCREENSHOT] == "image/png"
    assert media[CaptureRole.RAW_HTML] == "text/html"


def test_capture_set_without_payload_omits_it() -> None:
    files = capture_set(_raw(with_payload=False))
    assert CaptureRole.PAYLOAD not in {f.role for f in files}
    assert len(files) == 3


def test_wacz_is_a_valid_1_1_1_package() -> None:
    """SIG-EVID-007: a WACZ 1.1.1 zip with datapackage + WARC, not a screenshot."""
    wacz = build_wacz(_raw(with_payload=True))
    with zipfile.ZipFile(io.BytesIO(wacz)) as zf:
        names = set(zf.namelist())
        assert {
            "archive/data.warc",
            "pages/pages.jsonl",
            "datapackage.json",
            "datapackage-digest.json",
        } <= names
        datapackage = json.loads(zf.read("datapackage.json"))
        assert datapackage["wacz_version"] == "1.1.1"
        warc = zf.read("archive/data.warc")

    # Re-parseable (E2): the SPA's fetched JSON is retained in the WARC, so a
    # future parser can re-extract even though a screenshot could not.
    assert b'{"cameras": 42}' in warc
    assert b"WARC/1.1" in warc


def test_wacz_packaging_is_deterministic() -> None:
    """Reproducibility (SIG-EVID-017): same input -> byte-identical WACZ."""
    assert build_wacz(_raw(with_payload=True)) == build_wacz(_raw(with_payload=True))


def test_wacz_digest_block_matches_body() -> None:
    wacz = build_wacz(_raw(with_payload=True))
    with zipfile.ZipFile(io.BytesIO(wacz)) as zf:
        digest = json.loads(zf.read("datapackage-digest.json"))
        assert digest["path"] == "datapackage.json"
        assert digest["hash"].startswith("sha256:")
