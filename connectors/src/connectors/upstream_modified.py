# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The upstream-declared change value per fetch target (P35.41 / K9 §5.4,
SIG-TRANSP-031; generalises SIG-INGEST-030c).

Every capture mark may carry the upstream's own declared "last modified" —
the value the *publisher* asserts, never SIG's fetch clock. The read order
is:

1. **platform metadata** — one bounded metadata GET per platform document
   per run, through the run's shared fetcher (the politeness layer — the
   read is robots-checked, rate-limited and recorded in ``per_fetch`` like
   every egress): ArcGIS layer ``editingInfo.lastEditDate`` (the
   ``<layer>?f=json`` doc), Socrata dataset
   ``rowsUpdatedAt``/``dataUpdatedAt`` (``/api/views/<id>.json``), CKAN
   ``metadata_modified`` (a target-declared ``metadata_url``).
2. **payload-declared** — fields the captured document itself declares,
   read from the bytes already fetched (zero extra egress): Eyes on Flock
   ``data_last_updated`` — the already-read precedent (SIG-INGEST-030c).
3. **response headers** — HTTP ``Last-Modified`` (a declared instant) or
   ``ETag`` (an opaque version marker) — the only header fields read, both
   on the S-14 allowlist.

A transport exposing none of these yields ``basis=None`` — the mark stays
empty and the release surface reads ``not_detectable``, never a guessed
date. A metadata GET that errors (challenge, opt-out, transport failure,
unparseable body) degrades the same way — the probe is never run-fatal,
and the failure is already recorded in the fetcher's per-fetch telemetry.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

#: The closed vocabulary of upstream-declared basis labels — the field the
#: value came from (never an invented source). ``None`` on the record
#: renders as ``not_detectable`` at the release surface.
DECLARED_BASIS_ARCGIS = "editingInfo.lastEditDate"
DECLARED_BASIS_SOCRATA_ROWS = "rowsUpdatedAt"
DECLARED_BASIS_SOCRATA_DATA = "dataUpdatedAt"
DECLARED_BASIS_CKAN = "metadata_modified"
DECLARED_BASIS_HTTP_LAST_MODIFIED = "Last-Modified"
DECLARED_BASIS_HTTP_ETAG = "ETag"
DECLARED_BASIS_EOF = "data_last_updated"

#: The target ``kind`` values whose platform serves a metadata document.
_ARCGIS_KINDS = frozenset({"arcgis_query", "arcgis_outstatistics"})
_SOCRATA_KINDS = frozenset({"socrata_rows", "socrata_aggregate"})
#: Eyes on Flock's portal payload declares per-portal ``data_last_updated``
#: on the bytes the target already returns — payload-declared, no extra GET.
_EOF_KINDS = frozenset({"portal_json"})


@dataclass(frozen=True)
class UpstreamDeclared:
    """The upstream's declared change value for one capture.

    ``at`` is the publisher-declared instant (ISO-8601) where the transport
    exposes one; ``token`` is an opaque upstream version marker (HTTP
    ``ETag``) where the publisher declares only a version, not a date;
    ``basis`` names the declared field the value came from. All three
    ``None`` = the transport exposed nothing — honest ``not_detectable``,
    never a fabricated value.
    """

    at: str | None = None
    token: str | None = None
    basis: str | None = None

    @property
    def exposed(self) -> bool:
        return self.at is not None or self.token is not None


_NOT_DETECTED = UpstreamDeclared()


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def metadata_request_url(target: Mapping[str, Any]) -> str | None:
    """The platform metadata document URL for ``target``, or ``None``.

    ArcGIS layer targets read the layer service doc (``<layer>?f=json`` —
    ``editingInfo.lastEditDate``); Socrata dataset targets read the dataset
    metadata view (``/api/views/<id>.json`` — ``rowsUpdatedAt`` /
    ``dataUpdatedAt``); a CKAN-style target declares its own
    ``metadata_url`` (``metadata_modified``). Everything else — document,
    image, portal, probe — has no metadata GET here: the payload-declared
    and header lanes still apply. One URL per target; page targets of one
    layer share the document (the run-level cache dedupes the GET).
    """
    kind = str(target.get("kind") or "")
    layer_url = str(target.get("layer_url") or "").rstrip("/")
    if kind in _ARCGIS_KINDS and layer_url:
        return f"{layer_url}?f=json"
    if kind in _SOCRATA_KINDS and layer_url:
        parts = urlsplit(layer_url)
        # <host>/resource/<dataset-id>.json → <host>/api/views/<dataset-id>.json
        path = parts.path or ""
        if "/resource/" in path:
            rid = path.rsplit("/resource/", 1)[1].removesuffix(".json")
            if rid:
                return f"{parts.scheme}://{parts.netloc}/api/views/{rid}.json"
        return None
    declared = str(target.get("metadata_url") or "").strip()
    if declared:
        return declared
    return None


def _epoch_ms_iso(raw: Any) -> str | None:
    try:
        return _iso(datetime.fromtimestamp(int(raw) / 1000, tz=UTC))
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _epoch_s_iso(raw: Any) -> str | None:
    try:
        return _iso(datetime.fromtimestamp(int(raw), tz=UTC))
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def declared_from_metadata(kind: str, body: bytes) -> UpstreamDeclared:
    """Parse the declared field out of a platform metadata document.

    ``kind`` selects the platform shape: ArcGIS ``editingInfo.lastEditDate``
    (epoch ms), Socrata ``rowsUpdatedAt`` then ``dataUpdatedAt`` (epoch s),
    CKAN ``metadata_modified`` (ISO-8601). An absent or unparseable field
    yields the empty record — never a guessed date.
    """
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _NOT_DETECTED
    if not isinstance(doc, dict):
        return _NOT_DETECTED
    if kind in _ARCGIS_KINDS:
        info = doc.get("editingInfo")
        if isinstance(info, Mapping):
            at = _epoch_ms_iso(info.get("lastEditDate"))
            if at is not None:
                return UpstreamDeclared(at=at, basis=DECLARED_BASIS_ARCGIS)
        return _NOT_DETECTED
    if kind in _SOCRATA_KINDS:
        for key, basis in (
            ("rowsUpdatedAt", DECLARED_BASIS_SOCRATA_ROWS),
            ("dataUpdatedAt", DECLARED_BASIS_SOCRATA_DATA),
        ):
            at = _epoch_s_iso(doc.get(key))
            if at is not None:
                return UpstreamDeclared(at=at, basis=basis)
        return _NOT_DETECTED
    # CKAN package metadata: an ISO timestamp, no epoch form.
    raw = str(doc.get("metadata_modified") or "").strip()
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return _NOT_DETECTED
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return UpstreamDeclared(at=_iso(dt), basis=DECLARED_BASIS_CKAN)
    return _NOT_DETECTED


def _parse_date_value(raw: Any) -> datetime | None:
    """One upstream date field → a datetime; ``None`` on anything odd."""
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def declared_from_payload(target: Mapping[str, Any], body: bytes) -> UpstreamDeclared:
    """The declared field carried on the captured bytes themselves.

    Eyes on Flock's portal document declares per-portal
    ``data_last_updated`` — the source-level declared value is the latest
    portal date the document carries (SIG-INGEST-030c's already-read
    precedent: the field the upstream publishes as its own freshness, never
    SIG's fetch time). Other payload kinds declare nothing at this lane.
    """
    kind = str(target.get("kind") or "")
    if kind not in _EOF_KINDS:
        return _NOT_DETECTED
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _NOT_DETECTED
    portals = doc.get("portals") if isinstance(doc, dict) else None
    latest: datetime | None = None
    for portal in portals or ():
        if not isinstance(portal, Mapping):
            continue
        parsed = _parse_date_value(portal.get("data_last_updated"))
        if parsed is not None and (latest is None or parsed > latest):
            latest = parsed
    if latest is None:
        return _NOT_DETECTED
    return UpstreamDeclared(at=_iso(latest), basis=DECLARED_BASIS_EOF)


def declared_from_headers(headers: Mapping[str, str] | None) -> UpstreamDeclared:
    """The S-14-allowlisted header lane: ``Last-Modified`` then ``ETag``.

    ``Last-Modified`` is a publisher-declared instant (HTTP-date → ISO);
    ``ETag`` is an opaque upstream version marker — a changed tag evidences
    a change but declares no date, so it lands as the token, never as an
    invented timestamp. Only these two header names are read; nothing else
    on the response reaches this record.
    """
    headers = headers or {}
    lowered = {str(k).lower(): str(v) for k, v in headers.items()}
    last_modified = lowered.get("last-modified")
    if last_modified:
        try:
            dt = parsedate_to_datetime(last_modified)
        except (TypeError, ValueError):
            dt = None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return UpstreamDeclared(at=_iso(dt), basis=DECLARED_BASIS_HTTP_LAST_MODIFIED)
    etag = lowered.get("etag")
    if etag:
        return UpstreamDeclared(token=etag, basis=DECLARED_BASIS_HTTP_ETAG)
    return _NOT_DETECTED


def upstream_declared(
    target: Mapping[str, Any],
    fetched: Any,
    *,
    fetcher: Any = None,
    metadata_cache: dict[str, UpstreamDeclared] | None = None,
) -> UpstreamDeclared:
    """The declared change value for one captured target (K9 §5.4 item 1).

    Read order: platform metadata GET (one bounded read per metadata URL
    per run through the shared fetcher — ``metadata_cache`` dedupes the
    page targets of one layer) → payload-declared fields on the bytes
    already fetched → the S-14 header lane. Any probe failure degrades to
    the next lane or to honest absence; the probe is never run-fatal.
    """
    url = metadata_request_url(target)
    if url is not None and fetcher is not None:
        if metadata_cache is None:
            metadata_cache = {}
        if url not in metadata_cache:
            try:
                result = fetcher.fetch(url)
                metadata_cache[url] = declared_from_metadata(
                    str(target.get("kind") or ""), result.body
                )
            except Exception:  # noqa: BLE001 — a failed probe is honest absence
                metadata_cache[url] = _NOT_DETECTED
        declared = metadata_cache[url]
        if declared.exposed:
            return declared
    # The payload lane reads the bytes already fetched — no extra egress.
    body = getattr(fetched, "body", b"")
    declared = declared_from_payload(target, body)
    if declared.exposed:
        return declared
    return declared_from_headers(getattr(fetched, "headers", None))


__all__ = [
    "DECLARED_BASIS_ARCGIS",
    "DECLARED_BASIS_CKAN",
    "DECLARED_BASIS_EOF",
    "DECLARED_BASIS_HTTP_ETAG",
    "DECLARED_BASIS_HTTP_LAST_MODIFIED",
    "DECLARED_BASIS_SOCRATA_DATA",
    "DECLARED_BASIS_SOCRATA_ROWS",
    "UpstreamDeclared",
    "declared_from_headers",
    "declared_from_metadata",
    "declared_from_payload",
    "metadata_request_url",
    "upstream_declared",
]
