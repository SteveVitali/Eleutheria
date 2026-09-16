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
Nothing here deletes or overwrites: :meth:`GcsBucket.put_object` writes a NEW
object name per run and this module exposes no delete path, matching the
append-only ethos (P1–P3).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

#: The Cloud Run / GCE metadata server token endpoint (link-local, GCP-internal).
_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)
_GCS_API = "https://storage.googleapis.com"

#: A POST that succeeds (object written) or raises — never silently skipped.
_HTTPOpener = Callable[[urllib.request.Request, float], tuple[int, bytes]]


def _default_opener(req: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed hosts
        return resp.status, resp.read()


def _metadata_server_token(timeout: float = 2.0) -> str | None:
    """The job service account's access token from the GCP metadata server.

    Returns ``None`` off-GCP: the link-local name simply does not resolve (or
    times out) on a laptop, which is the signal to try the gcloud fallback.
    """
    req = urllib.request.Request(_METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - metadata IP
            return str(json.loads(resp.read())["access_token"])
    except Exception:  # noqa: BLE001 - any failure means "not on GCP"
        return None


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


class GcsError(RuntimeError):
    """A GCS call failed — surfaced, never swallowed (honest ops records)."""


@dataclass
class GcsBucket:
    """Read/write objects in one GCS bucket over the JSON API.

    ``token_provider``/``opener`` are injectable: tests pass fakes and no
    network is touched. With the defaults, each call resolves a fresh token
    (metadata server on Cloud Run, gcloud ADC in an operator shell).
    """

    bucket: str
    token_provider: Callable[[], str | None] = default_token_provider
    opener: _HTTPOpener = _default_opener

    def _request(
        self, method: str, url: str, *, body: bytes | None = None, content_type: str | None = None
    ) -> tuple[int, bytes]:
        token = self.token_provider()
        if not token:
            raise GcsError(
                "no GCS access token available (metadata server + gcloud ADC both "
                "absent) — the record stays local; nothing was uploaded"
            )
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            status, payload = self.opener(req, 60.0)
        except urllib.error.HTTPError as exc:
            raise GcsError(f"GCS {method} {url} -> HTTP {exc.code}") from exc
        except Exception as exc:  # noqa: BLE001 - surfaced, not hidden
            raise GcsError(f"GCS {method} {url} failed: {exc}") from exc
        if not (200 <= status < 300):
            raise GcsError(f"GCS {method} {url} -> HTTP {status}")
        return status, payload

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

    def get_object(self, name: str) -> bytes:
        """Download one object's bytes."""
        url = (
            f"{_GCS_API}/storage/v1/b/{urllib.parse.quote(self.bucket)}/o/"
            f"{urllib.parse.quote(name, safe='')}?alt=media"
        )
        _, payload = self._request("GET", url)
        return payload


__all__ = [
    "GcsBucket",
    "GcsError",
    "default_token_provider",
]
