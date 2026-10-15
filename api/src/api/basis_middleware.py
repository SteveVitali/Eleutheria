# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.25 (A-20=a) + P35.57 (SIG-REL-010, G3 §6.3/§6.4) — the basis label.

Every answer this service gives carries its basis class on the wire:

* **``release``** — the release-backed routes (``/v1/dossier/{scope}``,
  ``/v1/coverage/{scope}``, ``/v1/export``, ``/v1/changes``, ``/v1/sources…``,
  ``/v1/releases/**``) answer from the promoted release's verified files. The
  handler marks the request (``scope["state"]["sig_basis"] = "release"`` and
  ``["sig_release"] = {label, publication_id, as_of_world}``) *before* it serves
  — so a release-basis 404 or 503 is still labelled by the authority that
  answered. Headers: ``X-SIG-Basis: release``, ``X-SIG-Release: <label> <pub>``
  (G3 §6.3), ``X-SIG-Basis-Release: <pub>``; the JSON body gains
  ``basis {kind: "release", release: {...}}``.
* **``live-spine``** — every other route answers from the live claim spine and
  says so: ``basis {kind: "live-spine", as_of, spine_watermark,
  latest_release {label, publication_id}}`` plus the legacy ``type`` /
  ``watermark`` / ``release_id`` keys (additive — older clients ignore the new
  fields). The watermark is the bounded O(#facets) probe, never the annotation
  compute; the current release comes from the mounted registry when one exists
  and from the ``release_id`` pin otherwise — absent means "not pinned", never
  a fabricated id.

The middleware is pure ASGI — like :class:`api.alias_middleware.IdentifierAliasMiddleware`
it buffers the body, fixes ``content-length``, and never reorders or drops
fields (the injected ``basis``/``release`` are additive).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from starlette.concurrency import run_in_threadpool

#: The two basis classes (SIG-REL-010): the answer is either computed from the
#: live claim spine or served from a promoted release's pinned files.
BASIS_LIVE_SPINE = "live-spine"
BASIS_RELEASE = "release"

_HEADER_BASIS = b"x-sig-basis"
_HEADER_WATERMARK = b"x-sig-basis-watermark"
_HEADER_RELEASE_ID = b"x-sig-basis-release"
_HEADER_RELEASE = b"x-sig-release"
_DROP_HEADERS = {
    _HEADER_BASIS,
    _HEADER_WATERMARK,
    _HEADER_RELEASE_ID,
    _HEADER_RELEASE,
    b"content-length",
}
_JSON_TYPES = (b"application/json", b"application/ld+json")

_PUBLICATION_RE = re.compile(r"^p-[0-9a-f]{64}$")


def _release_header(block: dict[str, Any] | None) -> str | None:
    """``X-SIG-Release: <label> <publication_id>`` (G3 §6.3) — whichever fields
    are known, never a fabricated label."""
    if not block:
        return None
    label = block.get("label")
    pub = block.get("publication_id")
    if label and pub:
        return f"{label} {pub}"
    return str(label or pub) if (label or pub) else None


def _pin_block(release_id: str | None) -> dict[str, str] | None:
    """The ``latest_release`` block when only the configured pin string is
    known — a ``p-<hex>`` value is a publication id, anything else is a
    release label. Neither is ever invented."""
    if not release_id:
        return None
    if _PUBLICATION_RE.match(release_id):
        return {"publication_id": release_id}
    return {"label": release_id}


def _live_spine_payload(
    watermark: str | None,
    release_id: str | None,
    latest_release: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": BASIS_LIVE_SPINE,
        # Back-compat key (P34.25) — newer clients read ``kind``.
        "type": BASIS_LIVE_SPINE,
    }
    # Absent means "not known / not pinned" — never a fabricated value.
    if watermark:
        payload["watermark"] = watermark
        payload["spine_watermark"] = watermark
        payload["as_of"] = watermark
    if release_id:
        payload["release_id"] = release_id
    if latest_release:
        payload["latest_release"] = latest_release
    return payload


def _release_payload(release: dict[str, Any] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": BASIS_RELEASE, "type": BASIS_RELEASE}
    if release:
        payload["release"] = release
    return payload


class BasisLabelMiddleware:
    """Pure-ASGI response wrapper stamping the basis label (both classes)."""

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
        serving = getattr(state, "release_serving", None)
        current = None
        if serving is not None:
            try:
                ident = await run_in_threadpool(serving.current_identity)
                current = ident.block() if ident is not None else None
            except Exception:  # noqa: BLE001 — a dead registry degrades the label, never the answer
                current = None
        latest_release = current or _pin_block(release_id if release_id else None)
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
                await self._flush(
                    start,
                    bytes(body),
                    send,
                    scope=scope,
                    watermark=watermark,
                    release_id=release_id if release_id else None,
                    current=current,
                    latest_release=latest_release,
                )
                return
            await send(message)

        await self.app(scope, receive, send_buffer)

    async def _flush(
        self,
        start: dict | None,
        body: bytes,
        send: Callable,
        *,
        scope: dict,
        watermark: str | None,
        release_id: str | None,
        current: dict[str, Any] | None,
        latest_release: dict[str, Any] | None,
    ) -> None:
        # The handler's own classification wins: release-backed routes mark the
        # request state before serving so even their error bodies are labelled
        # by the authority that answered.
        req_state = scope.get("state") or {}
        served_release = req_state.get("sig_release")
        if req_state.get("sig_basis") == BASIS_RELEASE:
            basis = _release_payload(served_release)
            basis_header = BASIS_RELEASE.encode()
            release_header = _release_header(served_release)
            basis_release_header = (
                str(served_release.get("publication_id")) if served_release else None
            )
        else:
            basis = _live_spine_payload(watermark, release_id, latest_release)
            basis_header = BASIS_LIVE_SPINE.encode()
            release_header = _release_header(current) or (release_id or None)
            basis_release_header = release_id

        if start is not None:
            headers = [
                (k, v) for k, v in start.get("headers", []) if k.lower() not in _DROP_HEADERS
            ]
            headers.append((_HEADER_BASIS, basis_header))
            if watermark:
                headers.append((_HEADER_WATERMARK, str(watermark).encode()))
            if basis_release_header:
                headers.append((_HEADER_RELEASE_ID, basis_release_header.encode()))
            if release_header:
                headers.append((_HEADER_RELEASE, release_header.encode()))
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
                if isinstance(payload, dict):
                    changed = False
                    if "basis" not in payload:
                        payload = {**payload, "basis": basis}
                        changed = True
                    # The contract body field on release-basis answers —
                    # backstop injection keeps error bodies named too.
                    if (
                        req_state.get("sig_basis") == BASIS_RELEASE
                        and served_release
                        and "release" not in payload
                    ):
                        payload = {**payload, "release": served_release}
                        changed = True
                    if changed:
                        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            # The buffered (possibly rewritten) body carries a correct length —
            # content-length was stripped above and is re-emitted exactly.
            headers.append((b"content-length", str(len(body)).encode()))
            start = {**start, "headers": headers}
            await send(start)
        await send({"type": "http.response.body", "body": body})
