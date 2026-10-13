# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.25 (A-20=a, SIG-REL-010) — the ``live-spine`` basis label on every response.

Every answer this service gives is computed from the **live claim spine**, not
from a release-pinned export — so every response says so: an ``X-SIG-Basis``
header on every response, and a ``"basis"`` body field on every JSON object
body (including error bodies — a 404 is a live-spine answer too). The label
carries the spine watermark the answer describes (the bounded O(#facets)
probe, never the annotation compute) and the promoted release id only where
the service was configured with one — absent means "not pinned", never a
fabricated id. This is basis *disclosure* only; release parity is P35.57's.

The middleware is pure ASGI — like :class:`api.alias_middleware.IdentifierAliasMiddleware`
it buffers the body, fixes ``content-length``, and never reorders or drops
fields (the injected ``basis`` is additive; older clients ignore it).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from starlette.concurrency import run_in_threadpool

#: The basis label value — the answer is computed from the live claim spine.
BASIS_LIVE_SPINE = "live-spine"

_HEADER_BASIS = b"x-sig-basis"
_HEADER_WATERMARK = b"x-sig-basis-watermark"
_HEADER_RELEASE = b"x-sig-basis-release"
_DROP_HEADERS = {_HEADER_BASIS, _HEADER_WATERMARK, _HEADER_RELEASE, b"content-length"}
_JSON_TYPES = (b"application/json", b"application/ld+json")


def _basis_payload(watermark: str | None, release_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": BASIS_LIVE_SPINE}
    # Absent means "not known / not pinned" — never a fabricated value.
    if watermark:
        payload["watermark"] = watermark
    if release_id:
        payload["release_id"] = release_id
    return payload


class BasisLabelMiddleware:
    """Pure-ASGI response wrapper stamping the live-spine basis label."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        app = scope.get("app")
        state = getattr(app, "state", None)
        store = getattr(state, "store", None)
        release_id = getattr(state, "basis_release_id", None)
        watermark: str | None = None
        probe = getattr(store, "spine_watermark", None)
        if probe is not None:
            try:
                # The probe runs on the store's pooled connection — a bounded
                # O(#facets) read — off the event loop (route handlers are
                # sync too, but this call must never block the loop).
                watermark = await run_in_threadpool(probe)
            except Exception:  # noqa: BLE001 — a dead store degrades the label, never the answer
                watermark = None
        basis = _basis_payload(watermark, release_id if release_id else None)

        start: dict | None = None
        body = bytearray()

        async def send_buffer(message: dict) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                return
            if message["type"] == "http.response.body":
                body.extend(message.get("body", b""))
                if message.get("more_body"):
                    return
                await self._flush(start, bytes(body), send, basis)
                return
            await send(message)

        await self.app(scope, receive, send_buffer)

    async def _flush(self, start: dict | None, body: bytes, send: Callable, basis: dict) -> None:
        if start is not None:
            headers = [
                (k, v) for k, v in start.get("headers", []) if k.lower() not in _DROP_HEADERS
            ]
            headers.append((_HEADER_BASIS, BASIS_LIVE_SPINE.encode()))
            if "watermark" in basis:
                headers.append((_HEADER_WATERMARK, str(basis["watermark"]).encode()))
            if "release_id" in basis:
                headers.append((_HEADER_RELEASE, str(basis["release_id"]).encode()))
            ctype = next(
                (v for k, v in start.get("headers", []) if k.lower() == b"content-type"),
                b"",
            )
            ctype_base = ctype.split(b";")[0].strip().lower()
            if ctype_base in _JSON_TYPES:
                try:
                    payload = json.loads(body)
                except (ValueError, TypeError):
                    payload = None
                if isinstance(payload, dict) and "basis" not in payload:
                    payload = {**payload, "basis": basis}
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            # The buffered (possibly rewritten) body carries a correct length —
            # content-length was stripped above and is re-emitted exactly.
            headers.append((b"content-length", str(len(body)).encode()))
            start = {**start, "headers": headers}
            await send(start)
        await send({"type": "http.response.body", "body": body})
