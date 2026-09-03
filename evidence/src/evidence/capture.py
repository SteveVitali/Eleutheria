# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The web-capture pipeline (§17.4): WACZ packaging + live browser capture.

Web captures are stored as **WACZ 1.1.1** packages, not screenshots or PDFs alone
(SIG-EVID-007): a WACZ retains the network traffic — including the JSON a SPA
fetched — so a future parser can re-extract fields when SIG's extraction improves
(E2). For any JavaScript-rendered artifact the capture set MUST include (a) the
WACZ, (b) a full-page screenshot, (c) the extracted structured payload if one
exists, and (d) the raw HTML — each a separate ``evidence_capture`` row sharing
one ``evidence_artifact`` (SIG-EVID-008).

:func:`capture_set` turns a :class:`RawCapture` into exactly that set of files.
:func:`build_wacz` is a deterministic WARC→WACZ packager (no browser needed), so
the pipeline is fully testable from fixtures. :func:`capture_live` drives a real
headless browser (Playwright) to produce a :class:`RawCapture`; it is imported
lazily and lives behind the ``capture`` optional dependency, mirroring how the DB
tests gate on Docker — the store is usable and testable without a browser.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime

WACZ_VERSION = "1.1.1"
WARC_VERSION = "WARC/1.1"
_SOFTWARE = "sig-evidence"
# A fixed namespace so a re-run over the same inputs yields identical record ids
# (reproducibility, SIG-EVID-017). Not security-sensitive.
_RECORD_NS = uuid.UUID("6f0b8f4a-2a1e-5c7d-9b3a-000000000017")
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


class CaptureRole(str):
    WACZ = "wacz"
    SCREENSHOT = "screenshot"
    PAYLOAD = "payload"
    RAW_HTML = "raw_html"


@dataclass(frozen=True)
class CapturedResponse:
    """One HTTP response recorded during a capture."""

    url: str
    status: int
    body: bytes
    content_type: str = "application/octet-stream"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RawCapture:
    """The raw material a live capture produces, before packaging."""

    url: str
    responses: tuple[CapturedResponse, ...]
    screenshot_png: bytes
    raw_html: bytes
    captured_at: datetime
    extracted_payload: bytes | None = None
    payload_media_type: str = "application/json"


@dataclass(frozen=True)
class CaptureFile:
    """One member of a capture set — becomes one ``evidence_capture`` row."""

    role: str
    logical_name: str
    media_type: str
    data: bytes


def _http_block(resp: CapturedResponse) -> bytes:
    reason = "OK" if resp.status == 200 else ""
    lines = [f"HTTP/1.1 {resp.status} {reason}".rstrip()]
    headers = {"Content-Type": resp.content_type, "Content-Length": str(len(resp.body))}
    headers.update(resp.headers)
    for name, value in headers.items():
        lines.append(f"{name}: {value}")
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
    return head + resp.body


def _warc_record(
    record_type: str,
    *,
    uri: str | None,
    block: bytes,
    when: datetime,
    content_type: str,
    record_id: str,
) -> bytes:
    headers = [
        WARC_VERSION,
        f"WARC-Type: {record_type}",
        f"WARC-Record-ID: {record_id}",
        f"WARC-Date: {when.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Content-Type: {content_type}",
        f"WARC-Block-Digest: sha256:{hashlib.sha256(block).hexdigest()}",
        f"Content-Length: {len(block)}",
    ]
    if uri is not None:
        headers.insert(4, f"WARC-Target-URI: {uri}")
    return ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8") + block + b"\r\n\r\n"


def build_warc(raw: RawCapture) -> bytes:
    """Assemble a deterministic WARC 1.1 stream from the recorded responses."""
    when = raw.captured_at.astimezone(UTC)
    info_block = (f"software: {_SOFTWARE}\r\nformat: WARC file version 1.1\r\n").encode()
    out = bytearray()
    out += _warc_record(
        "warcinfo",
        uri=None,
        block=info_block,
        when=when,
        content_type="application/warc-fields",
        record_id=f"urn:uuid:{uuid.uuid5(_RECORD_NS, raw.url + ':warcinfo')}",
    )
    for i, resp in enumerate(raw.responses):
        out += _warc_record(
            "response",
            uri=resp.url,
            block=_http_block(resp),
            when=when,
            content_type="application/http; msgtype=response",
            record_id=f"urn:uuid:{uuid.uuid5(_RECORD_NS, resp.url + f':response:{i}')}",
        )
    return bytes(out)


def _cdxj(raw: RawCapture) -> bytes:
    ts = raw.captured_at.astimezone(UTC).strftime("%Y%m%d%H%M%S")
    lines = []
    for resp in raw.responses:
        record = {
            "url": resp.url,
            "status": str(resp.status),
            "mime": resp.content_type.split(";")[0],
            "digest": f"sha256:{hashlib.sha256(resp.body).hexdigest()}",
        }
        lines.append(f"{resp.url} {ts} {json.dumps(record, sort_keys=True)}")
    return ("\n".join(sorted(lines)) + ("\n" if lines else "")).encode("utf-8")


def _pages_jsonl(raw: RawCapture) -> bytes:
    header = {"format": "json-pages-1.0", "id": "pages", "title": "All Pages"}
    page = {
        "id": uuid.uuid5(_RECORD_NS, raw.url + ":page").hex[:10],
        "url": raw.url,
        "ts": raw.captured_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return (json.dumps(header) + "\n" + json.dumps(page, sort_keys=True) + "\n").encode("utf-8")


def build_wacz(raw: RawCapture) -> bytes:
    """Package a capture into a deterministic WACZ 1.1.1 archive (SIG-EVID-007)."""
    created = raw.captured_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    members: dict[str, bytes] = {
        "archive/data.warc": build_warc(raw),
        "indexes/index.cdx": _cdxj(raw),
        "pages/pages.jsonl": _pages_jsonl(raw),
    }
    resources = [
        {
            "name": path.split("/")[-1],
            "path": path,
            "hash": f"sha256:{hashlib.sha256(data).hexdigest()}",
            "bytes": len(data),
        }
        for path, data in sorted(members.items())
    ]
    datapackage = {
        "profile": "data-package",
        "wacz_version": WACZ_VERSION,
        "software": _SOFTWARE,
        "created": created,
        "mainPageUrl": raw.url,
        "mainPageDate": created,
        "resources": resources,
    }
    datapackage_bytes = json.dumps(datapackage, indent=2, sort_keys=True).encode("utf-8")
    members["datapackage.json"] = datapackage_bytes
    members["datapackage-digest.json"] = json.dumps(
        {
            "path": "datapackage.json",
            "hash": f"sha256:{hashlib.sha256(datapackage_bytes).hexdigest()}",
        },
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in sorted(members):
            info = zipfile.ZipInfo(filename=path, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, members[path])
    return buffer.getvalue()


def capture_set(raw: RawCapture) -> list[CaptureFile]:
    """The full capture set for a JS-rendered artifact (SIG-EVID-008).

    WACZ + full-page screenshot + raw HTML, plus the extracted structured payload
    when one exists. Each returned file becomes a separate ``evidence_capture``
    row under one ``evidence_artifact``.
    """
    files = [
        CaptureFile(CaptureRole.WACZ, "capture.wacz", "application/wacz", build_wacz(raw)),
        CaptureFile(CaptureRole.SCREENSHOT, "screenshot.png", "image/png", raw.screenshot_png),
        CaptureFile(CaptureRole.RAW_HTML, "index.html", "text/html", raw.raw_html),
    ]
    if raw.extracted_payload is not None:
        files.append(
            CaptureFile(
                CaptureRole.PAYLOAD,
                "payload.json",
                raw.payload_media_type,
                raw.extracted_payload,
            )
        )
    return files


def capture_live(url: str, *, timeout_ms: int = 30_000) -> RawCapture:
    """Capture a live, JavaScript-rendered page with a real headless browser.

    Drives Playwright (Chromium): records every network response, the fully
    rendered HTML, and a full-page screenshot (SIG-EVID-007/008). Playwright is
    the ``capture`` optional dependency and is imported lazily; if it is not
    installed this raises a clear error rather than importing at module load.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "live capture needs the 'capture' extra: pip install 'sig-evidence[capture]' "
            "and run 'playwright install chromium'"
        ) from exc

    responses: list[CapturedResponse] = []
    with sync_playwright() as pw:  # pragma: no cover - requires a real browser
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        def _on_response(response: object) -> None:
            try:
                body = response.body()  # type: ignore[attr-defined]
            except Exception:
                body = b""
            responses.append(
                CapturedResponse(
                    url=response.url,  # type: ignore[attr-defined]
                    status=response.status,  # type: ignore[attr-defined]
                    body=body,
                    content_type=response.headers.get("content-type", "application/octet-stream"),  # type: ignore[attr-defined]
                )
            )

        page.on("response", _on_response)
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        raw_html = page.content().encode("utf-8")
        screenshot = page.screenshot(full_page=True)
        browser.close()

    return RawCapture(
        url=url,
        responses=tuple(responses),
        screenshot_png=screenshot,
        raw_html=raw_html,
        captured_at=datetime.now(UTC),
    )
