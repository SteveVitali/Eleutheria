# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Push bulk exports to an S3-compatible object store (§38.5, SIG-EXPORT-008/009).

``sig-exports push --store s3://bucket`` uploads a built release to a zero-or-low-egress
object store. Two invariants are structural, not prose:

* **Content-hash keys (append-only, P1–P3).** Every object key embeds the artifact's
  SHA-256, so an object is **never overwritten** — a re-push of the same bytes is a
  no-op, and different bytes get a different key. A published release URL therefore
  always points at exactly the bytes it named.
* **Long-lived cache (egress economics).** Because keys are immutable, objects are
  uploaded with an immutable ``Cache-Control`` so a CDN can cache them forever — the
  cheapest possible egress profile (SIG-STORE-003, §38.5, ADR-067).

P35.5 (SIG-TRANSP-019, D-J3-4/A-3) adds the distribution-host discipline:

* **Fail-closed bounds.** A push run carries :class:`PushLimits` — a per-file size cap,
  per-run object and byte caps, and a request-rate guard. A cap that can be known up
  front refuses **before the first upload** — a run never truncates or silently drops
  an artifact.
* **A non-listable origin.** The public mirror serves objects by their (forgettable)
  content-hash keys only; :func:`assert_non_listable_origin` probes the configured
  base URL and refuses when an anonymous request can enumerate the bucket.

The S3 client is injected (``boto3`` is already a dependency for the evidence Object-Lock
store — reused here), so the *upload policy* is decided and tested against a fake client
with **no live store** (HG-07). A metered-egress provider fails before any upload
(SIG-EXPORT-008).
"""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .distribution import ObjectStore, assert_low_egress
from .manifest import sha256_hex

#: Immutable objects (content-hash keys) may be cached effectively forever.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"

#: The per-file cap: one raw archive object never exceeds 512 MiB — larger
#: artifacts belong on the peer-distribution path the manifest already emits
#: (torrent/IPFS, SIG-EXPORT-009). Documented ceiling, not a measurement.
DEFAULT_MAX_FILE_BYTES = 536_870_912
#: The per-run request budget: one push run uploads at most this many objects.
#: A run that would exceed it refuses before the first upload — "rate limits in
#: the push path" means a bounded run, never a throttled-forever one.
DEFAULT_MAX_RUN_OBJECTS = 20_000
#: The per-run byte budget (50 GiB): bounds what one push puts on the mirror.
DEFAULT_MAX_RUN_BYTES = 53_687_091_200
#: The request-rate ceiling: a run whose put cadence exceeds this many requests
#: in any 60-second window refuses at the moment it does (the alternative —
#: silently sleeping — hides a misconfigured client behind fake success).
DEFAULT_MAX_REQUESTS_PER_MINUTE = 300


class PushRefusal(RuntimeError):
    """A push bound refused — the run stops, never truncates (SIG-TRANSP-019)."""


@dataclass(frozen=True)
class PushLimits:
    """Fail-closed bounds on one push run (SIG-TRANSP-019).

    ``max_file_bytes`` — one artifact's on-disk size must not exceed this.
    ``max_run_objects`` / ``max_run_bytes`` — a run that would upload more than
    this refuses before the first ``put_object`` (checked against the manifest
    and the on-disk sizes, so the refusal is provable without touching the
    store). ``max_requests_per_minute`` — the put cadence ceiling, measured on
    the injected clock: the run refuses the moment it would exceed it.
    ``min_request_interval_s`` — optional pacing between uploads (0 = none).
    """

    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_run_objects: int = DEFAULT_MAX_RUN_OBJECTS
    max_run_bytes: int = DEFAULT_MAX_RUN_BYTES
    max_requests_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE
    min_request_interval_s: float = 0.0


def check_push_limits(
    export_dir: str | Path, manifest: Mapping[str, Any], limits: PushLimits
) -> None:
    """Refuse a run that would exceed the per-file / per-run caps — before any upload.

    The manifest's declared artifacts are measured on disk (the bytes are read
    for upload anyway), so a cap breach is provable without a live store.
    """
    root = Path(export_dir)
    artifacts = manifest.get("artifacts", [])
    if len(artifacts) > limits.max_run_objects:
        raise PushRefusal(
            f"push run refuses: {len(artifacts)} artifacts exceed the per-run object cap "
            f"({limits.max_run_objects}) — split the release instead of pushing an "
            "unbounded run (SIG-TRANSP-019)"
        )
    total = 0
    for artifact in artifacts:
        path = str(artifact["path"])
        size = (root / path).stat().st_size
        if size > limits.max_file_bytes:
            raise PushRefusal(
                f"push run refuses: {path} is {size} bytes, over the per-file cap "
                f"({limits.max_file_bytes}) — oversize artifacts belong on the "
                "peer-distribution path (SIG-TRANSP-019), never a truncated push"
            )
        total += size
    if total > limits.max_run_bytes:
        raise PushRefusal(
            f"push run refuses: {total} bytes over the per-run byte cap "
            f"({limits.max_run_bytes}) — split the release instead of pushing an "
            "unbounded run (SIG-TRANSP-019)"
        )


def assert_non_listable_origin(fetch: Callable[[str], tuple[int, str]], base_url: str) -> None:
    """Refuse when the mirror origin answers an anonymous object listing.

    SIG-TRANSP-019: the distribution origin must not expose anonymous listing —
    objects are addressable only through their content-hash keys. ``fetch``
    maps a URL to ``(status, body)`` (the live leg wires an anonymous GET;
    tests wire a fake). A 2xx answer carrying a listing document — an S3
    ``ListBucketResult`` or a web autoindex — means enumeration is enabled and
    the publish stops.
    """
    for probe in ("?list-type=2", ""):
        status, body = fetch(f"{base_url.rstrip('/')}/{probe}")
        if not 200 <= status < 300:
            continue
        if "<ListBucketResult" in body or "<Contents>" in body or "Index of /" in body:
            raise PushRefusal(
                f"mirror origin {base_url} answers an anonymous listing "
                f"({probe or 'index'}) — SIG-TRANSP-019 requires a non-listable "
                "origin; disable bucket listing before the push runs"
            )


class S3Client(Protocol):
    """The tiny slice of the boto3 S3 client this module uses (so it is fakeable)."""

    def put_object(self, **kwargs: object) -> object: ...

    def head_object(self, **kwargs: object) -> object: ...


def content_hash_key(release_id: str, path: str, sha256: str) -> str:
    """The immutable object key for an artifact: ``<release>/<path>?<hash8>`` folded in.

    The 12-hex prefix of the SHA-256 is embedded in the key so bytes and key change
    together — an object is never silently overwritten with different content.
    """
    p = Path(path)
    stem = p.stem
    suffix = "".join(p.suffixes)
    parent = str(p.parent).strip(".").strip("/")
    name = f"{stem}.{sha256[:12]}{suffix}"
    prefix = f"{release_id}/"
    return f"{prefix}{parent + '/' if parent else ''}{name}"


@dataclass(frozen=True)
class PushedObject:
    """The record of one uploaded (or already-present) artifact."""

    path: str
    key: str
    sha256: str
    byte_size: int
    skipped: bool  # True when the immutable key already existed (no re-upload)

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "key": self.key,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "skipped": self.skipped,
        }


def _guess_content_type(path: str) -> str:
    mapping = {
        ".json": "application/json",
        ".csv": "text/csv",
        ".jsonl": "application/x-ndjson",
        ".parquet": "application/vnd.apache.parquet",
        ".pmtiles": "application/vnd.pmtiles",
        ".geojson": "application/geo+json",
        ".sqlite": "application/vnd.sqlite3",
        ".torrent": "application/x-bittorrent",
    }
    return mapping.get(Path(path).suffix, "application/octet-stream")


def _object_exists(client: S3Client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:  # noqa: BLE001 - any error (404/NoSuchKey) means "not present"
        return False


def push_export_dir(
    export_dir: str,
    store: ObjectStore,
    client: S3Client,
    *,
    cache_control: str = IMMUTABLE_CACHE_CONTROL,
    limits: PushLimits | None = None,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
) -> list[PushedObject]:
    """Upload every artifact in a built export dir to ``store`` under content-hash keys.

    Fails before any upload if the store is metered-egress (SIG-EXPORT-008) or the
    run would exceed ``limits`` (SIG-TRANSP-019). Skips an object whose immutable
    key already exists (append-only: never overwrite). ``sleep``/``clock`` are
    injected so the rate guard and pacing are fakeable in tests. Returns the
    per-artifact push records.
    """
    assert_low_egress(store)
    limits = limits or PushLimits()
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    with open(Path(export_dir) / "manifest.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
    check_push_limits(export_dir, manifest, limits)
    release_id = str(manifest["release_id"])
    results: list[PushedObject] = []
    put_times: deque[float] = deque()
    uploads = 0
    for artifact in manifest.get("artifacts", []):
        path = str(artifact["path"])
        sha = str(artifact["sha256"])
        data = (Path(export_dir) / path).read_bytes()
        # Integrity: the bytes on disk must match the manifest's declared checksum.
        if sha256_hex(data) != sha:
            raise ValueError(f"checksum mismatch for {path}: disk bytes != manifest sha256")
        key = content_hash_key(release_id, path, sha)
        if _object_exists(client, store.bucket, key):
            results.append(PushedObject(path, key, sha, len(data), skipped=True))
            continue
        # The request-rate guard (SIG-TRANSP-019): a run whose put cadence would
        # exceed the per-minute ceiling refuses — it never silently races ahead.
        now = clock()
        while put_times and put_times[0] <= now - 60.0:
            put_times.popleft()
        if len(put_times) >= limits.max_requests_per_minute:
            raise PushRefusal(
                f"push run refuses: put cadence would exceed "
                f"{limits.max_requests_per_minute} requests/minute — the run "
                "stops rather than racing the store (SIG-TRANSP-019)"
            )
        if uploads and limits.min_request_interval_s > 0:
            sleep(limits.min_request_interval_s)
        put_times.append(now)
        client.put_object(
            Bucket=store.bucket,
            Key=key,
            Body=data,
            ContentType=_guess_content_type(path),
            CacheControl=cache_control,
        )
        uploads += 1
        results.append(PushedObject(path, key, sha, len(data), skipped=False))
    return results


def build_s3_client(store: ObjectStore, endpoint_url: str | None = None) -> S3Client:
    """Build a real boto3 S3 client for ``store`` (reusing the evidence-store dependency).

    ``endpoint_url`` targets an S3-compatible provider (e.g. Cloudflare R2 / Backblaze)
    from ``SIG_OBJECT_STORE_URL``. Credentials are read by boto3 from the environment —
    never written to a file (HG-07 / HG-09).
    """
    import boto3  # lazy: keep the module usable + testable without boto3 configured

    return boto3.client("s3", endpoint_url=endpoint_url)  # type: ignore[no-any-return]


def push_summary(results: list[PushedObject], store: ObjectStore) -> Mapping[str, object]:
    """A JSON-able summary of a push (for the CLI)."""
    uploaded = [r for r in results if not r.skipped]
    return {
        "store": {"provider": store.provider, "bucket": store.bucket},
        "objects": len(results),
        "uploaded": len(uploaded),
        "skipped": len(results) - len(uploaded),
        "bytes_uploaded": sum(r.byte_size for r in uploaded),
        "keys": [r.as_json() for r in results],
    }


__all__ = [
    "IMMUTABLE_CACHE_CONTROL",
    "DEFAULT_MAX_FILE_BYTES",
    "DEFAULT_MAX_RUN_OBJECTS",
    "DEFAULT_MAX_RUN_BYTES",
    "DEFAULT_MAX_REQUESTS_PER_MINUTE",
    "PushLimits",
    "PushRefusal",
    "S3Client",
    "PushedObject",
    "assert_non_listable_origin",
    "check_push_limits",
    "content_hash_key",
    "push_export_dir",
    "build_s3_client",
    "push_summary",
]
