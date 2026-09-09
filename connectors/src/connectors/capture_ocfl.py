# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The OCFL-backed capture store the live pipeline archives through (§17, P21.3).

:class:`OcflCaptureStore` adapts the evidence layer's OCFL 1.1 root
(:class:`evidence.ocfl.OcflStore`) to the connectors' narrow
:class:`~connectors.stages.CaptureStore` Protocol, so a live connector run
archives its fetched bytes into durable, content-addressed, third-party-readable
evidence rather than the in-memory store the tests use (LD-F03).

The mapping (SIG-EVID-004/005, §17.3):

* one OCFL **object per capture digest** — the id is derived from the connectors'
  content multihash, so identical bytes always address the same object and a
  re-fetch of unchanged content deduplicates to one stored blob (append-only,
  P1–P3: a re-run adds a version, never overwrites);
* the raw bytes are the ``capture`` logical file, and a sibling ``metadata.json``
  records the **retrieval time, source URI, media type and the response headers**
  (§17: what was fetched, from where, and when) — the fetch *record* carries no
  content, but the capture carries the headers so a reviewer can audit the
  retrieval (Content-Type, ETag, robots-relevant signals);
* for an HTML page an optional **WACZ** logical file is written through the P02.2
  Playwright capture path when a ``wacz_builder`` is supplied (``--wacz``);
  the byte-addressed content still content-addresses stably (LD-F02/LD-H02:
  live-connector WACZ per run).

The returned :class:`~connectors.stages.CaptureRef` carries the **connectors'**
multihash (identical to :class:`~connectors.stages.InMemoryCaptureStore`), so the
post-capture stages and fixture replay are byte-identical whichever store backs
the run (additive/back-compat; ``shadow_replay`` diff = 0).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime

from evidence.digest import multihash
from evidence.ocfl import OcflStore

from .stages import CaptureRef

#: The logical path the raw fetched bytes are stored under in each OCFL object.
CAPTURE_LOGICAL_PATH = "capture"
#: The logical path the retrieval metadata sidecar is stored under.
METADATA_LOGICAL_PATH = "metadata.json"
#: The logical path an optional WACZ web-archive is stored under (HTML pages).
WACZ_LOGICAL_PATH = "page.wacz"

#: A WACZ builder turns (url, bytes) into a WACZ archive's bytes (P02.2 Playwright).
WaczBuilder = Callable[[str, bytes], bytes]


def capture_object_id(digest: str) -> str:
    """The OCFL object id for a capture of content-multihash ``digest``.

    Content-addressed, so identical bytes always map to the same object and
    dedup to one blob across runs (SIG-EVID-004).
    """
    return f"sig:capture:{digest}"


class OcflCaptureStore:
    """A :class:`connectors.stages.CaptureStore` over an OCFL evidence root.

    ``store`` is an initialised :class:`evidence.ocfl.OcflStore`; ``wacz_builder``
    (optional) enables the ``--wacz`` HTML-page path. The store is content-
    addressed: :meth:`get` / :meth:`has` resolve by the connectors' multihash.
    """

    def __init__(
        self,
        store: OcflStore,
        *,
        wacz_builder: WaczBuilder | None = None,
        capture_wacz: bool = False,
    ) -> None:
        self._store = store
        self._wacz_builder = wacz_builder
        self._capture_wacz = capture_wacz

    def put(
        self,
        data: bytes,
        *,
        media_type: str,
        source_uri: str,
        retrieved_at: datetime | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> CaptureRef:
        """Archive ``data`` as an OCFL version and return its content-addressed ref.

        The connectors' multihash is the address (so replay is byte-identical to
        the in-memory store); the OCFL object records the bytes plus a metadata
        sidecar (retrieval time, source URI, media type, response headers).
        """
        digest = multihash(data)
        object_id = capture_object_id(digest)
        metadata = {
            "digest": digest,
            "source_uri": source_uri,
            "media_type": media_type,
            "retrieved_at": retrieved_at.isoformat() if retrieved_at is not None else None,
            "byte_size": len(data),
            # Response headers are retrieval provenance (§17), NOT content — the
            # fetch record excludes them; the capture keeps them for audit.
            "headers": dict(headers) if headers else {},
        }
        files: dict[str, bytes] = {
            CAPTURE_LOGICAL_PATH: data,
            METADATA_LOGICAL_PATH: json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode(
                "utf-8"
            ),
        }
        if self._should_capture_wacz(media_type):
            assert self._wacz_builder is not None  # guarded by _should_capture_wacz
            files[WACZ_LOGICAL_PATH] = self._wacz_builder(source_uri, data)
        self._store.add_version(
            object_id,
            files,
            message=f"live capture of {source_uri}",
        )
        return CaptureRef(
            digest=digest,
            media_type=media_type,
            source_uri=source_uri,
            byte_size=len(data),
            retrieved_at=retrieved_at,
        )

    def get(self, digest: str) -> bytes:
        """Read the captured bytes back by content multihash (OCFL resolve)."""
        return self._store.resolve(
            capture_object_id(digest), self._head_version(digest), CAPTURE_LOGICAL_PATH
        )

    def has(self, digest: str) -> bool:
        """Whether a capture with this content multihash is archived."""
        return self._store.object_exists(capture_object_id(digest))

    def metadata(self, digest: str) -> dict:
        """The retrieval metadata sidecar for an archived capture (audit path)."""
        raw = self._store.resolve(
            capture_object_id(digest), self._head_version(digest), METADATA_LOGICAL_PATH
        )
        return json.loads(raw)

    # -- helpers --------------------------------------------------------------
    def _head_version(self, digest: str) -> str:
        return self._store.read_inventory(capture_object_id(digest))["head"]

    def _should_capture_wacz(self, media_type: str) -> bool:
        return (
            self._capture_wacz
            and self._wacz_builder is not None
            and media_type.split(";", 1)[0].strip() in {"text/html", "application/xhtml+xml"}
        )


__all__ = [
    "CAPTURE_LOGICAL_PATH",
    "METADATA_LOGICAL_PATH",
    "OcflCaptureStore",
    "WACZ_LOGICAL_PATH",
    "WaczBuilder",
    "capture_object_id",
]
