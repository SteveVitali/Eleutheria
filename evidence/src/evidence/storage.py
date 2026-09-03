# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Byte-addressed object-store backends for the OCFL evidence root (§17.3).

:class:`BlobStore` is the minimal key → bytes contract the :mod:`evidence.ocfl`
layer needs. Two backends implement it:

* :class:`LocalFileStore` — a filesystem root, for tests and for the
  air-gapped-restore path (E5, §46.5): the OCFL tree on disk is readable with no
  network and no SIG code.
* :class:`S3ObjectStore` — an S3-compatible bucket (ADR-015). The bucket MUST
  have **versioning enabled** and **Object Lock in *governance* mode** with a
  documented default retention, and **never compliance mode** (SIG-EVID-006), so
  that a lawful takedown (§45) stays satisfiable through a permissioned, audited
  path. :func:`governance_object_lock_configuration` builds exactly that config
  and :func:`assert_governance_not_compliance` is the guard that fails closed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# A conservative default retention. Long enough to defeat an accidental early
# overwrite; short enough that it is a lock, not a permanent seal — governance
# mode plus this window keeps takedown satisfiable (SIG-EVID-006 / §45).
DEFAULT_RETENTION_DAYS = 365


@runtime_checkable
class BlobStore(Protocol):
    """A flat key → bytes store. Keys are ``/``-separated relative paths."""

    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def list(self, prefix: str = "") -> list[str]: ...


class LocalFileStore:
    """A :class:`BlobStore` over a local directory tree."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        return self._root / key

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list(self, prefix: str = "") -> list[str]:
        base = self._root
        if not base.is_dir():
            return []
        keys = [str(p.relative_to(base).as_posix()) for p in base.rglob("*") if p.is_file()]
        return sorted(k for k in keys if k.startswith(prefix))


def governance_object_lock_configuration(
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict:
    """The S3 Object Lock configuration for the evidence bucket (SIG-EVID-006).

    Governance mode with a documented default retention — never compliance mode.
    """
    if retention_days <= 0:
        raise ValueError("default retention must be a positive number of days")
    return {
        "ObjectLockEnabled": "Enabled",
        "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": retention_days}},
    }


def assert_governance_not_compliance(configuration: dict) -> None:
    """Fail loudly if an Object Lock config would use compliance mode (SIG-EVID-006)."""
    mode = configuration.get("Rule", {}).get("DefaultRetention", {}).get("Mode")
    if mode == "COMPLIANCE":
        raise ValueError(
            "evidence Object Lock MUST be governance mode, never compliance "
            "(SIG-EVID-006): compliance mode makes a lawful takedown impossible"
        )
    if mode != "GOVERNANCE":
        raise ValueError(f"evidence Object Lock must be GOVERNANCE, got {mode!r}")


@dataclass
class S3ObjectStore:
    """A :class:`BlobStore` over an S3-compatible bucket (ADR-015).

    ``boto3`` is imported lazily so the OCFL/packaging layers stay usable without
    it. Use :meth:`ensure_bucket` once to create the bucket with versioning and
    governance-mode Object Lock enabled (SIG-EVID-006).
    """

    bucket: str
    prefix: str = ""
    client: Any = None

    def _client(self) -> Any:
        if self.client is None:
            import boto3  # lazy

            self.client = boto3.client("s3")
        return self.client

    def _key(self, key: str) -> str:
        return f"{self.prefix.strip('/')}/{key}".lstrip("/") if self.prefix else key

    def ensure_bucket(self, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        """Create the bucket with versioning + governance Object Lock (SIG-EVID-006)."""
        client = self._client()
        config = governance_object_lock_configuration(retention_days)
        assert_governance_not_compliance(config)
        # Object Lock requires versioning; a lock-enabled bucket enables it, but we
        # set it explicitly so the invariant is legible.
        client.create_bucket(Bucket=self.bucket, ObjectLockEnabledForBucket=True)
        client.put_bucket_versioning(
            Bucket=self.bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        client.put_object_lock_configuration(Bucket=self.bucket, ObjectLockConfiguration=config)

    def put(self, key: str, data: bytes) -> None:
        self._client().put_object(Bucket=self.bucket, Key=self._key(key), Body=data)

    def get(self, key: str) -> bytes:
        response = self._client().get_object(Bucket=self.bucket, Key=self._key(key))
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError  # lazy

        try:
            self._client().head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError:
            return False

    def list(self, prefix: str = "") -> list[str]:
        client = self._client()
        paginator = client.get_paginator("list_objects_v2")
        base = self._key(prefix)
        strip = f"{self.prefix.strip('/')}/" if self.prefix else ""
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=base):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                keys.append(key[len(strip) :] if strip and key.startswith(strip) else key)
        return sorted(keys)
