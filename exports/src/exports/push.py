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

The S3 client is injected (``boto3`` is already a dependency for the evidence Object-Lock
store — reused here), so the *upload policy* is decided and tested against a fake client
with **no live store** (HG-07). A metered-egress provider fails before any upload
(SIG-EXPORT-008).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .distribution import ObjectStore, assert_low_egress
from .manifest import sha256_hex

#: Immutable objects (content-hash keys) may be cached effectively forever.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"


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
) -> list[PushedObject]:
    """Upload every artifact in a built export dir to ``store`` under content-hash keys.

    Fails before any upload if the store is metered-egress (SIG-EXPORT-008). Skips an
    object whose immutable key already exists (append-only: never overwrite). Returns the
    per-artifact push records.
    """
    assert_low_egress(store)
    with open(Path(export_dir) / "manifest.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
    release_id = str(manifest["release_id"])
    results: list[PushedObject] = []
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
        client.put_object(
            Bucket=store.bucket,
            Key=key,
            Body=data,
            ContentType=_guess_content_type(path),
            CacheControl=cache_control,
        )
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
    "S3Client",
    "PushedObject",
    "content_hash_key",
    "push_export_dir",
    "build_s3_client",
    "push_summary",
]
