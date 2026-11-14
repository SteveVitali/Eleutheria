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
* for an HTML page an optional **WACZ** logical file is written under
  ``--wacz`` (``capture_wacz=True``) — by default a deterministic
  single-response WACZ 1.1.1 packaged from the fetched bytes via
  :func:`evidence.capture.build_wacz` (P37.56 / BL-026), with the P02.2
  Playwright capture path still wiring in through the ``wacz_builder`` seam
  when a rendered capture is required; the byte-addressed content still
  content-addresses stably (LD-F02/LD-H02: live-connector WACZ per run).

The returned :class:`~connectors.stages.CaptureRef` carries the **connectors'**
multihash (identical to :class:`~connectors.stages.InMemoryCaptureStore`), so the
post-capture stages and fixture replay are byte-identical whichever store backs
the run (additive/back-compat; ``shadow_replay`` diff = 0).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from evidence.digest import multihash
from evidence.ocfl import OcflStore

from .stages import CaptureRef

#: The logical path the raw fetched bytes are stored under in each OCFL object.
CAPTURE_LOGICAL_PATH = "capture"
#: The logical path the retrieval metadata sidecar is stored under.
METADATA_LOGICAL_PATH = "metadata.json"
#: The logical path an optional WACZ web-archive is stored under (HTML pages).
WACZ_LOGICAL_PATH = "page.wacz"
#: The logical path the applied-redaction record is stored under inside a
#: derivative object — the ``sig.redaction-review/1`` sidecar naming the
#: parent, the reviewed scope digests, the method/version and the reviewer
#: role (P36.15; SIG-PUB-015/016). The record carries digests of the removed
#: spans — never the removed text itself.
REDACTION_LOGICAL_PATH = "redaction.json"

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
        status: int | None = None,
    ) -> CaptureRef:
        """Archive ``data`` as an OCFL version and return its content-addressed ref.

        The connectors' multihash is the address (so replay is byte-identical to
        the in-memory store); the OCFL object records the bytes plus a metadata
        sidecar (retrieval time, source URI, media type, response headers, the
        response status). Under ``capture_wacz`` an HTML capture additionally
        carries a deterministic single-response WACZ (P37.56) whose digest is
        recorded on the sidecar and returned on the ref.
        """
        digest = multihash(data)
        object_id = capture_object_id(digest)
        wacz: bytes | None = None
        if self._should_capture_wacz(media_type):
            wacz = (
                self._wacz_builder(source_uri, data)
                if self._wacz_builder is not None
                else self._package_wacz(
                    data,
                    media_type=media_type,
                    source_uri=source_uri,
                    retrieved_at=retrieved_at,
                    headers=headers,
                    status=status,
                )
            )
        metadata: dict[str, Any] = {
            "digest": digest,
            "source_uri": source_uri,
            "media_type": media_type,
            "retrieved_at": retrieved_at.isoformat() if retrieved_at is not None else None,
            "byte_size": len(data),
            # Response headers are retrieval provenance (§17), NOT content — the
            # fetch record excludes them; the capture keeps them for audit.
            "headers": dict(headers) if headers else {},
            "status": status,
        }
        if wacz is not None:
            # The WACZ member's own content address + size — the availability
            # record a run row audits against, never implied by presence alone.
            metadata["wacz"] = {"digest": multihash(wacz), "byte_size": len(wacz)}
        files: dict[str, bytes] = {
            CAPTURE_LOGICAL_PATH: data,
            METADATA_LOGICAL_PATH: json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode(
                "utf-8"
            ),
        }
        if wacz is not None:
            files[WACZ_LOGICAL_PATH] = wacz
        self._store.add_version(
            object_id,
            files,
            message=f"live capture of {source_uri}",
        )
        # The version THIS put committed is the capture's pinned occurrence —
        # carried on the ref so a claim's evidence binding names the version
        # the extraction consumed, and a replay reads that same version rather
        # than whatever head later versions moved to (SIG-TRUST-002).
        version = self._head_version(digest)
        return CaptureRef(
            digest=digest,
            media_type=media_type,
            source_uri=source_uri,
            byte_size=len(data),
            retrieved_at=retrieved_at,
            ocfl_object_id=object_id,
            ocfl_version=version,
            wacz_digest=multihash(wacz) if wacz is not None else None,
        )

    def put_derivative(
        self,
        data: bytes,
        *,
        media_type: str,
        parent_capture_id: str,
        parent_digest: str,
        redaction: Mapping[str, object],
        source_uri: str = "",
        retrieved_at: datetime | None = None,
    ) -> CaptureRef:
        """Archive a redaction derivative as a NEW OCFL object (SIG-EVID-011, P36.15).

        The derivative is content-addressed like every capture (its own object,
        its own digest — identical redacted bytes dedup to one object); the
        **parent is never modified** (SIG-EPIS-006). ``redaction`` is the
        ``sig.redaction-review/1`` applied-redaction record
        (:func:`evidence.redaction.apply_redaction`'s outcome) — written as the
        object's ``redaction.json`` sidecar and summarized on the metadata
        sidecar so the capture's provenance names its parent, the method and
        version, and the reviewing *role*.
        """
        digest = multihash(data)
        object_id = capture_object_id(digest)
        record = dict(redaction)
        review = record.get("review")
        review_map = dict(review) if isinstance(review, Mapping) else {}
        spans = record.get("spans")
        metadata = {
            "digest": digest,
            "source_uri": source_uri,
            "media_type": media_type,
            "retrieved_at": retrieved_at.isoformat() if retrieved_at is not None else None,
            "byte_size": len(data),
            "headers": {},
            "parent_capture_id": parent_capture_id,
            "parent_digest": parent_digest,
            "redaction": {
                "method": record.get("redaction_method"),
                "version": record.get("redaction_version"),
                "reviewer_role": review_map.get("reviewer_role"),
                "span_count": len(spans) if isinstance(spans, list | tuple) else 0,
            },
        }
        files: dict[str, bytes] = {
            CAPTURE_LOGICAL_PATH: data,
            METADATA_LOGICAL_PATH: json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode(
                "utf-8"
            ),
            REDACTION_LOGICAL_PATH: json.dumps(record, sort_keys=True, ensure_ascii=False).encode(
                "utf-8"
            ),
        }
        self._store.add_version(
            object_id,
            files,
            message=(
                f"redaction derivative of {parent_digest} "
                f"({redaction.get('redaction_method')} {redaction.get('redaction_version')})"
            ),
        )
        version = self._head_version(digest)
        return CaptureRef(
            digest=digest,
            media_type=media_type,
            source_uri=source_uri,
            byte_size=len(data),
            retrieved_at=retrieved_at,
            ocfl_object_id=object_id,
            ocfl_version=version,
        )

    def get(self, digest: str, *, version: str | None = None) -> bytes:
        """Read the captured bytes back by content multihash (OCFL resolve).

        ``version`` (P32.2) pins the immutable occurrence version — a replay
        reads the version the original extraction consumed, never whatever a
        later re-fetch moved ``head`` to. ``None`` keeps the back-compat
        current-head resolve.
        """
        return self._store.resolve(
            capture_object_id(digest), version or self._head_version(digest), CAPTURE_LOGICAL_PATH
        )

    def has(self, digest: str) -> bool:
        """Whether a capture with this content multihash is archived."""
        return self._store.object_exists(capture_object_id(digest))

    def metadata(self, digest: str, *, version: str | None = None) -> dict:
        """The retrieval metadata sidecar for an archived capture (audit path)."""
        raw = self._store.resolve(
            capture_object_id(digest),
            version or self._head_version(digest),
            METADATA_LOGICAL_PATH,
        )
        return json.loads(raw)

    # -- helpers --------------------------------------------------------------
    def _head_version(self, digest: str) -> str:
        return self._store.read_inventory(capture_object_id(digest))["head"]

    def _should_capture_wacz(self, media_type: str) -> bool:
        # The flag alone enables the WACZ path (P37.56): no builder needed —
        # the deterministic packager covers the fetched-response shape, and a
        # supplied ``wacz_builder`` (P02.2 Playwright) still takes precedence.
        return self._capture_wacz and media_type.split(";", 1)[0].strip() in {
            "text/html",
            "application/xhtml+xml",
        }

    def _package_wacz(
        self,
        data: bytes,
        *,
        media_type: str,
        source_uri: str,
        retrieved_at: datetime | None,
        headers: Mapping[str, str] | None,
        status: int | None,
    ) -> bytes:
        """A deterministic single-response WACZ 1.1.1 over the fetched bytes.

        Records the response exactly as the fetch stage observed it — the real
        status and headers, never a synthesized render (the Playwright
        ``wacz_builder`` seam remains the path for a JS-rendered capture). A
        caller that bypassed the fetch stage and supplied no status archives a
        conventional 200 only as a packaging default — the sidecar records the
        truthful ``status: null``.
        """
        from evidence.capture import CapturedResponse, RawCapture, build_wacz

        return build_wacz(
            RawCapture(
                url=source_uri,
                responses=(
                    CapturedResponse(
                        url=source_uri,
                        status=status if status is not None else 200,
                        body=data,
                        content_type=media_type,
                        headers=dict(headers or {}),
                    ),
                ),
                # The fetch path holds no render — no screenshot to record.
                screenshot_png=b"",
                raw_html=data,
                captured_at=retrieved_at if retrieved_at is not None else datetime.now(UTC),
            )
        )


__all__ = [
    "CAPTURE_LOGICAL_PATH",
    "METADATA_LOGICAL_PATH",
    "OcflCaptureStore",
    "REDACTION_LOGICAL_PATH",
    "WACZ_LOGICAL_PATH",
    "WaczBuilder",
    "capture_object_id",
]
