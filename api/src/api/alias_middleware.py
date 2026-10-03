# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.18 / ADR-178 — public identifier alias projection on API responses.

The claim spine is append-only: recorded claims keep their old, handle-bearing
source/subject identifiers forever (SIG-STORE-011). The public surface projects
them through the keyed-digest alias table — every retired token in a response
body resolves or redacts to its neutral form, in JSON, JSON-LD, HTML and Turtle
alike, so nothing publicly renderable repeats a handle (TS-04). This is an
output-side projection only: request inputs are untouched, so a historical id
still queries (the old id is the recorded id) while the response renders the
neutral one (A5's old/new compatibility). The deeper schema-side alias read is
a P34.46-class change; this middleware is the P34.18 seam ADR-178 names.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from policy.source_aliases import load_source_aliases, resolve_public_text

_JSON_TYPES = (b"application/json", b"application/ld+json")
_TEXT_TYPES = (b"text/html", b"text/turtle", b"text/plain")


class IdentifierAliasMiddleware:
    """Pure-ASGI response rewriter applying the alias projection."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        aliases = load_source_aliases()
        if aliases.empty:
            await self.app(scope, receive, send)
            return

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
                await self._flush(start, bytes(body), send, aliases)
                return
            await send(message)

        await self.app(scope, receive, send_buffer)

    async def _flush(self, start: dict | None, body: bytes, send: Callable, aliases: Any) -> None:
        if start is not None:
            headers = [
                (k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"
            ]
            ctype = next(
                (v for k, v in start.get("headers", []) if k.lower() == b"content-type"),
                b"",
            )
            ctype_base = ctype.split(b";")[0].strip().lower()
            if ctype_base in _JSON_TYPES:
                try:
                    payload = json.loads(body)
                    body = json.dumps(
                        resolve_public_text(payload, aliases), ensure_ascii=False
                    ).encode("utf-8")
                except (ValueError, TypeError):
                    pass
            elif ctype_base in _TEXT_TYPES:
                try:
                    body = (aliases.resolve_text(body.decode("utf-8"))).encode("utf-8")
                except UnicodeDecodeError:
                    pass
            start = {**start, "headers": headers}
            await send(start)
        await send({"type": "http.response.body", "body": body})
