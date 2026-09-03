# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Object-store backends + governance-mode Object Lock (SIG-EVID-006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from evidence import storage


def test_local_file_store_roundtrip(tmp_path: Path) -> None:
    store = storage.LocalFileStore(tmp_path)
    store.put("a/b/c.txt", b"data")
    assert store.exists("a/b/c.txt")
    assert store.get("a/b/c.txt") == b"data"
    assert not store.exists("missing")
    assert store.list("a/") == ["a/b/c.txt"]


def test_object_lock_config_is_governance_not_compliance() -> None:
    config = storage.governance_object_lock_configuration()
    assert config["ObjectLockEnabled"] == "Enabled"
    assert config["Rule"]["DefaultRetention"]["Mode"] == "GOVERNANCE"
    assert config["Rule"]["DefaultRetention"]["Days"] == storage.DEFAULT_RETENTION_DAYS
    storage.assert_governance_not_compliance(config)  # must not raise


def test_compliance_mode_is_rejected() -> None:
    bad = {"Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 30}}}
    with pytest.raises(ValueError, match="governance mode"):
        storage.assert_governance_not_compliance(bad)


def test_retention_must_be_positive() -> None:
    with pytest.raises(ValueError):
        storage.governance_object_lock_configuration(0)


class _FakeS3:
    """A minimal in-memory stand-in for boto3's s3 client."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[tuple[str, dict]] = []

    def create_bucket(self, **kw: object) -> None:
        self.calls.append(("create_bucket", kw))

    def put_bucket_versioning(self, **kw: object) -> None:
        self.calls.append(("put_bucket_versioning", kw))

    def put_object_lock_configuration(self, **kw: object) -> None:
        self.calls.append(("put_object_lock_configuration", kw))

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[Key] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        import io

        return {"Body": io.BytesIO(self.objects[Key])}


def test_ensure_bucket_enables_versioning_and_governance_lock() -> None:
    """SIG-EVID-006: bucket setup turns on versioning + governance Object Lock."""
    fake = _FakeS3()
    store = storage.S3ObjectStore(bucket="evidence", client=fake)
    store.ensure_bucket()

    by_name = {name: kw for name, kw in fake.calls}
    assert by_name["create_bucket"]["ObjectLockEnabledForBucket"] is True
    assert by_name["put_bucket_versioning"]["VersioningConfiguration"]["Status"] == "Enabled"
    lock = by_name["put_object_lock_configuration"]["ObjectLockConfiguration"]
    assert lock["Rule"]["DefaultRetention"]["Mode"] == "GOVERNANCE"


def test_s3_store_put_get_via_injected_client() -> None:
    fake = _FakeS3()
    store = storage.S3ObjectStore(bucket="evidence", prefix="root", client=fake)
    store.put("x/y.bin", b"bytes")
    assert store.get("x/y.bin") == b"bytes"
    assert "root/x/y.bin" in fake.objects  # prefix applied
