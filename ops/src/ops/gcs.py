# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A minimal Google Cloud Storage client over the JSON API (P26.1 / OPS.2).

The scheduled-ops jobs (``sig-probe``, the ``sig-ingest-*`` family) must leave
their outcome rows as per-run timestamped objects in the PRIVATE
``…-sig-restricted`` bucket — WORM-shaped, never read-modify-write. The zero-cost
posture (SIG-STORE-003) means **no SDK dependency**: the JSON API is three stdlib
``urllib`` calls (upload / list / download) authenticated by an OAuth2 access
token resolved in this order:

1. the Cloud Run metadata server (the job's service account — the normal case
   inside a Cloud Run job),
2. ``gcloud auth application-default print-access-token`` (an operator shell
   with ADC, e.g. running ``sig-ops probe-history`` locally),
3. ``SIG_GCS_ACCESS_TOKEN`` (explicit override, e.g. a test or a token broker).

The token provider and the URL opener are injectable so the whole client is
deterministic in tests — no socket is opened unless the caller asks for one.
The default provider is :class:`CachingTokenProvider` (D-P37.65a-3): the
token resolves once, is reused until near expiry, and a transient failure is
a bounded retry — never the per-request ``gcloud`` subprocess (~5–6 s wall,
measured) nor the hard mid-plan exit that made ``release stage --apply``
infeasible at national scale.
Append-only by default: audit/record writers use per-run timestamped names and
never rewrite objects (P1–P3). The single exception is
:meth:`GcsBucket.delete_object`, added for P34.10 — the repository-owned
publish path's removal of retired public-site objects, guarded by the
protected release-namespace check in ``ops.publish`` (SIG-OPS-003/004).
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

#: The Cloud Run / GCE metadata server token endpoint (link-local, GCP-internal).
_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)
_GCS_API = "https://storage.googleapis.com"

#: A POST that succeeds (object written) or raises — never silently skipped.
_HTTPOpener = Callable[[urllib.request.Request, float], tuple[int, bytes]]

#: D-P37.65a-3 — the per-request costs the release-stage leg measured.
#: Every request below bounded-retries transient failures instead of dying on
#: the first blip, and a resolved token is cached until near expiry instead of
#: paying a ``gcloud`` subprocess (~5–6 s wall) per call.
_REQUEST_ATTEMPTS = 3
_RETRY_BACKOFF_S = 0.25
#: A gcloud-issued ADC access token lives ~1 h; refresh well inside that.
_GCLOUD_TOKEN_TTL_S = 45.0 * 60.0
#: Re-resolve this far before a declared (metadata-server) expiry.
_TOKEN_EXPIRY_MARGIN_S = 60.0
#: HTTP statuses worth a bounded retry — throttling + transient 5xx. A 4xx
#: other than 429 means the request itself is wrong; it is never retried. A
#: 412 precondition refusal is handled by the caller's own lane (it is the
#: create-if-absent signal, not a failure).
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


def _default_opener(req: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed hosts
        return resp.status, resp.read()


def _metadata_server_token_doc(timeout: float = 2.0) -> dict | None:
    """The metadata-server token *document* (``access_token`` + ``expires_in``).

    Returns ``None`` off-GCP: the link-local name simply does not resolve (or
    times out) on a laptop, which is the signal to try the gcloud fallback.
    """
    req = urllib.request.Request(_METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - metadata IP
            doc = json.loads(resp.read())
            if doc.get("access_token"):
                return dict(doc)
    except Exception:  # noqa: BLE001 - any failure means "not on GCP"
        return None
    return None


def _metadata_server_token(timeout: float = 2.0) -> str | None:
    """The job service account's access token from the GCP metadata server."""
    doc = _metadata_server_token_doc(timeout)
    return str(doc["access_token"]) if doc else None


def _gcloud_adc_token(timeout: float = 15.0) -> str | None:
    """The operator's ADC token via ``gcloud`` (local shell path)."""
    try:
        proc = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    token = proc.stdout.strip()
    return token or None


def default_token_provider() -> str | None:
    """Resolve an access token: env override → metadata server → gcloud ADC."""
    override = os.environ.get("SIG_GCS_ACCESS_TOKEN", "").strip()
    if override:
        return override
    return _metadata_server_token() or _gcloud_adc_token()


class CachingTokenProvider:
    """Resolve an access token ONCE and reuse it until near expiry
    (D-P37.65a-3).

    The uncached ``default_token_provider`` pays a metadata-server probe plus
    a ``gcloud`` subprocess for *every* request — measured 5–6 s wall each in
    an operator shell (gcloud 583.0.0), which made ``release stage --apply``
    cost ~40–60 s per object at national scale. This provider caches by
    source:

    * ``SIG_GCS_ACCESS_TOKEN`` — explicit override, trusted for the process;
    * the metadata server — the response carries ``expires_in``, so the cache
      refreshes ``_TOKEN_EXPIRY_MARGIN_S`` ahead of the declared expiry;
    * ``gcloud … print-access-token`` — an opaque token with a ~1 h lifetime,
      cached for ``_GCLOUD_TOKEN_TTL_S``.

    Resolution itself bounded-retries (``attempts``) so one slow/hung gcloud
    call is a retry, never a mid-plan hard exit. Thread-safe: the stage
    verb's insert pool shares the provider.
    """

    def __init__(
        self,
        *,
        metadata_token: Callable[[float], dict | None] = _metadata_server_token_doc,
        gcloud_token: Callable[[float], str | None] = _gcloud_adc_token,
        env: Callable[[str], str | None] = os.environ.get,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        attempts: int = _REQUEST_ATTEMPTS,
        gcloud_ttl: float = _GCLOUD_TOKEN_TTL_S,
        expiry_margin: float = _TOKEN_EXPIRY_MARGIN_S,
    ) -> None:
        self._metadata_token = metadata_token
        self._gcloud_token = gcloud_token
        self._env = env
        self._clock = clock
        self._sleep = sleep
        self._attempts = max(1, attempts)
        self._gcloud_ttl = gcloud_ttl
        self._expiry_margin = expiry_margin
        self._mutex = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def __call__(self) -> str | None:
        with self._mutex:
            if self._token is not None and self._clock() < self._expires_at:
                return self._token
            for attempt in range(self._attempts):
                token = self._resolve_once()
                if token:
                    return token
                if attempt + 1 < self._attempts:
                    self._sleep(_RETRY_BACKOFF_S * (attempt + 1))
            return None

    def invalidate(self) -> None:
        """Drop the cached token — called on an HTTP 401 so the next request
        re-resolves (a revoked or early-expired token is never trusted past a
        refusal)."""
        with self._mutex:
            self._token = None
            self._expires_at = 0.0

    def _resolve_once(self) -> str | None:
        override = (self._env("SIG_GCS_ACCESS_TOKEN") or "").strip()
        if override:
            self._token = override
            self._expires_at = float("inf")  # an explicit token is trusted
            return override
        doc = self._metadata_token(2.0)
        if doc and doc.get("access_token"):
            expires_in = float(doc.get("expires_in") or 3600.0)
            self._token = str(doc["access_token"])
            self._expires_at = self._clock() + max(expires_in - self._expiry_margin, 5.0)
            return self._token
        token = self._gcloud_token(15.0)
        if token:
            self._token = token
            self._expires_at = self._clock() + self._gcloud_ttl
            return token
        return None


class GcsError(RuntimeError):
    """A GCS call failed — surfaced, never swallowed (honest ops records)."""


class GcsPreconditionFailed(GcsError):
    """An ``if-generation-match`` precondition failed — HTTP 412.

    P35.53 (SIG-REL-005, G3 §5.1): ``stage`` inserts staged objects with
    ``ifGenerationMatch=0`` and takes the registry lock as a
    create-if-absent object; a 412 is the name-collision / held-lock /
    stale-generation signal the release pipeline refuses on — it is never
    retried past.
    """


@dataclass
class GcsBucket:
    """Read/write objects in one GCS bucket over the JSON API.

    ``token_provider``/``opener`` are injectable: tests pass fakes and no
    network is touched. The default provider is a :class:`CachingTokenProvider`
    — the token resolves once and is reused until near expiry (D-P37.65a-3);
    an injected plain callable keeps its per-call semantics.
    """

    bucket: str
    token_provider: Callable[[], str | None] = field(default_factory=CachingTokenProvider)
    opener: _HTTPOpener = _default_opener

    def _call(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        not_found_none: bool = False,
        precondition: bool = False,
    ) -> tuple[int, bytes] | None:
        """One HTTP call with bounded transient retry (D-P37.65a-3).

        Retries only what is safe to retry: connection/timeout failures,
        throttling and 5xx; a 401 drops the cached token (when the provider
        is a :class:`CachingTokenProvider`) and re-resolves once. A 412 with
        ``precondition=True`` raises :class:`GcsPreconditionFailed` — the
        create-if-absent signal the release pipeline refuses on, never a
        retried failure. A 404 with ``not_found_none=True`` returns ``None``.
        Everything else non-2xx raises :class:`GcsError`.
        """
        token_invalidated = False
        last_exc: Exception | None = None
        for attempt in range(_REQUEST_ATTEMPTS):
            token = self.token_provider()
            if not token:
                # The provider already bounded-retried its resolution; a None
                # here means credentials are genuinely absent — fail closed.
                raise GcsError(
                    "no GCS access token available (metadata server + gcloud ADC "
                    "both absent, retried) — the record stays local; nothing was "
                    "uploaded"
                )
            headers = {"Authorization": f"Bearer {token}"}
            if content_type:
                headers["Content-Type"] = content_type
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                status, payload = self.opener(req, 60.0)
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, b""
            except Exception as exc:  # noqa: BLE001 - transient transport failure
                last_exc = exc
                if attempt + 1 < _REQUEST_ATTEMPTS:
                    time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                raise GcsError(f"GCS {method} {url} failed: {exc}") from exc
            if status == 404 and not_found_none:
                return None
            if status == 412 and precondition:
                raise GcsPreconditionFailed(f"GCS {method} {url} -> HTTP 412")
            if status == 401 and not token_invalidated:
                invalidate = getattr(self.token_provider, "invalidate", None)
                if callable(invalidate):
                    token_invalidated = True
                    invalidate()
                    continue
            if status in _TRANSIENT_STATUSES and attempt + 1 < _REQUEST_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                continue
            if not (200 <= status < 300):
                raise GcsError(f"GCS {method} {url} -> HTTP {status}")
            return status, payload
        raise GcsError(f"GCS {method} {url} failed: {last_exc}") from last_exc

    def _request(
        self, method: str, url: str, *, body: bytes | None = None, content_type: str | None = None
    ) -> tuple[int, bytes]:
        out = self._call(method, url, body=body, content_type=content_type)
        assert out is not None  # not_found_none is unset — a status always returns
        return out

    def put_object(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload ``body`` as a NEW object ``name``; returns the object name.

        Callers pass a per-run timestamped name (``ops/probes/<date>/<ts>.jsonl``)
        so the log stays WORM-shaped — objects are never rewritten in place.
        """
        url = (
            f"{_GCS_API}/upload/storage/v1/b/{urllib.parse.quote(self.bucket)}/o"
            f"?uploadType=media&name={urllib.parse.quote(name)}"
        )
        self._request("POST", url, body=body, content_type=content_type)
        return name

    def list_objects(self, prefix: str) -> list[str]:
        """Object names under ``prefix`` (paginated)."""
        names: list[str] = []
        page_token: str | None = None
        while True:
            query = f"prefix={urllib.parse.quote(prefix)}&fields=items(name),nextPageToken"
            if page_token:
                query += f"&pageToken={urllib.parse.quote(page_token)}"
            url = f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o?{query}"
            _, payload = self._request("GET", url)
            doc = json.loads(payload)
            names.extend(str(item["name"]) for item in doc.get("items", []))
            page_token = doc.get("nextPageToken")
            if not page_token:
                return names

    def list_object_details(self, prefix: str) -> list[dict]:
        """Object ``name`` + ``md5Hash`` + ``size`` under ``prefix`` (paginated).

        P37.3: the replica/copy verify legs need the content fingerprint, not
        just the name — one paged read carries the whole parity basis.
        """
        items: list[dict] = []
        page_token: str | None = None
        while True:
            query = (
                f"prefix={urllib.parse.quote(prefix)}&fields=items(name,md5Hash,size),nextPageToken"
            )
            if page_token:
                query += f"&pageToken={urllib.parse.quote(page_token)}"
            url = f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o?{query}"
            _, payload = self._request("GET", url)
            doc = json.loads(payload)
            items.extend(doc.get("items", []))
            page_token = doc.get("nextPageToken")
            if not page_token:
                return items

    def get_object(self, name: str) -> bytes:
        """Download one object's bytes."""
        url = (
            f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o/"
            f"{urllib.parse.quote(name, safe='')}?alt=media"
        )
        _, payload = self._request("GET", url)
        return payload

    def delete_object(self, name: str, *, generation: int | None = None) -> str:
        """Delete one object; returns its name.

        Added for P34.10 (SIG-OPS-003/004): the ONE sanctioned deleter — the
        repository-owned publish path (``sig-ops publish-web``) calls it for
        remote extras the allow-listed site tree no longer carries. Callers
        MUST already exclude the protected release namespaces
        (``ops.publish.PROTECTED_PREFIXES``); ``ops.publish.sync_tree``
        re-checks every name at the write so a caller bug cannot delete a
        release tree either. P35.53 additionally uses it to *release* the
        release registry's ``registry/LOCK`` object — the only object the
        pipeline is ever allowed to delete. P35.55's ``--purge-versions``
        passes ``generation=`` to delete exactly one NONCURRENT version of
        an object a disposition-authorised withdrawal removed (the live
        version is never named by the purge — see
        ``release_reversal.purge_noncurrent_versions``).
        """
        url = (
            f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o/"
            f"{urllib.parse.quote(name, safe='')}"
        )
        if generation is not None:
            url += f"?generation={int(generation)}"
        self._request("DELETE", url)
        return name

    def list_object_versions(self, prefix: str) -> list[dict]:
        """Every version of every object under ``prefix`` (``versions=true`` —
        noncurrent versions carry ``generation`` and are deleted only under
        the P35.55 ``--purge-versions`` legal-takedown lane)."""
        items: list[dict] = []
        page_token: str | None = None
        while True:
            query = (
                f"versions=true&prefix={urllib.parse.quote(prefix)}"
                "&fields=items(name,generation,timeDeleted),nextPageToken"
            )
            if page_token:
                query += f"&pageToken={urllib.parse.quote(page_token)}"
            url = f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o?{query}"
            _, payload = self._request("GET", url)
            doc = json.loads(payload)
            items.extend(doc.get("items", []))
            page_token = doc.get("nextPageToken")
            if not page_token:
                return items

    def _request_preconditioned(
        self,
        url: str,
        *,
        body: bytes,
        content_type: str,
    ) -> tuple[int, bytes]:
        """A POST that may legitimately answer 412 (precondition failed).

        Same auth/opener discipline as :meth:`_request`, but HTTP 412 maps
        to :class:`GcsPreconditionFailed` instead of a generic error so the
        release pipeline can refuse name collisions / held locks /
        stale generations distinctly.
        """
        out = self._call("POST", url, body=body, content_type=content_type, precondition=True)
        assert out is not None
        return out

    def insert_object(
        self,
        name: str,
        body: bytes,
        *,
        if_generation_match: int = 0,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """Upload ``body`` under a generation precondition; returns the
        object's metadata (parsed JSON).

        ``if_generation_match=0`` is create-if-absent (P35.53 / SIG-REL-005):
        a live object under ``name`` answers 412 →
        :class:`GcsPreconditionFailed`. A nonzero value is the conditional
        replace the registry lock uses for ``labels.json``.
        """
        url = (
            f"{_GCS_API}/upload/storage/v1/b/{urllib.parse.quote(self.bucket)}/o"
            f"?uploadType=media&name={urllib.parse.quote(name)}"
            f"&ifGenerationMatch={if_generation_match}"
        )
        _, payload = self._request_preconditioned(url, body=body, content_type=content_type)
        try:
            return json.loads(payload)
        except ValueError:
            return {"name": name}

    def copy_object_to(self, name: str, *, dest: GcsBucket, dest_name: str | None = None) -> dict:
        """Server-side copy of ``name`` into ``dest`` (JSON API ``copyTo``).

        P37.3 (SIG-STORE-048): the off-instance replica and the monthly-export
        cross-project copy never download bytes through the job — ``copyTo``
        is the storage-side clone, so the caller needs only read on the source
        and create on the destination (no delete anywhere). ``dest`` shares
        this client's token provider (the job's one service account holds both
        grants — the dest bucket may live in another project). Returns the
        destination object's metadata.
        """
        target = dest_name or name
        url = (
            f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o/"
            f"{urllib.parse.quote(name, safe='')}/copyTo/b/"
            f"{urllib.parse.quote(dest.bucket)}/o/{urllib.parse.quote(target, safe='')}"
        )
        _, payload = self._request("POST", url)
        try:
            return json.loads(payload)
        except ValueError:
            return {"name": target, "bucket": dest.bucket}

    def get_object_meta(self, name: str) -> dict | None:
        """One object's JSON metadata (``generation``, ``md5Hash``,
        ``size``, ``updated``), or ``None`` when the name is absent (404)."""
        url = (
            f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o/"
            f"{urllib.parse.quote(name, safe='')}?alt=json"
        )
        out = self._call("GET", url, not_found_none=True)
        if out is None:
            return None
        return json.loads(out[1])


__all__ = [
    "CachingTokenProvider",
    "GcsBucket",
    "GcsError",
    "GcsPreconditionFailed",
    "default_token_provider",
]
