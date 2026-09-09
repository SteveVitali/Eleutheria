# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Object-store push (§38.5, SIG-EXPORT-008/009): content-hash keys, no live store."""

from __future__ import annotations

import json
from datetime import date

import pytest
from exports.bundle import build_bundle
from exports.compartments import ExportRow, ExportTable
from exports.distribution import EgressError, ObjectStore
from exports.manifest import BuildSpec

from exports import push as P


class FakeS3:
    """A deterministic in-memory stand-in for the boto3 S3 client (HG-07: no live store)."""

    def __init__(self, existing: set[str] | None = None) -> None:
        self.objects: dict[str, dict[str, object]] = {}
        self._existing = existing or set()

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:  # noqa: N803
        if Key in self.objects or Key in self._existing:
            return {"Bucket": Bucket, "Key": Key}
        raise KeyError(Key)  # boto3 raises ClientError(404); any exception = not present

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.objects[str(kwargs["Key"])] = kwargs
        return {"ETag": "fake"}


def _build_export(tmp_path):
    spec = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1")
    tables = [
        ExportTable(
            name="claims",
            rows=(ExportRow(source_id="sig", data={"subject_id": "s", "value": 1}),),
            kind="tabular",
        )
    ]
    rights = _rights()
    bundle = build_bundle(spec, tables, rights)
    out = tmp_path / "release"
    bundle.write_to(out)
    return out


def _rights():
    from policy.rights import RightsRecord

    return [
        RightsRecord(
            source_id="sig",
            spdx="CC-BY-4.0",
            attribution="© SIG",
            redistributable=True,
            derivative_permitted=True,
            terms_url="https://creativecommons.org/licenses/by/4.0/",
            retrieval_date="2026-06-30",
        )
    ]


def test_content_hash_key_embeds_the_digest() -> None:
    key = P.content_hash_key("sig-2026-06-30-abcd1234", "sig_graph/claims.parquet", "a" * 64)
    assert key == "sig-2026-06-30-abcd1234/sig_graph/claims.aaaaaaaaaaaa.parquet"


def test_metered_egress_provider_fails_before_any_upload(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    with pytest.raises(EgressError):
        P.push_export_dir(str(out), ObjectStore("aws-s3", "sig"), client)
    assert client.objects == {}  # nothing uploaded


def test_push_uploads_with_immutable_cache_control(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    results = P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client)
    assert results and all(not r.skipped for r in results)
    for kwargs in client.objects.values():
        assert kwargs["CacheControl"] == P.IMMUTABLE_CACHE_CONTROL
        assert kwargs["Bucket"] == "sig-bulk"


def test_push_is_idempotent_never_overwrites(tmp_path) -> None:
    # Append-only (P1-P3): a re-push of the same bytes uploads nothing (immutable keys).
    out = _build_export(tmp_path)
    client = FakeS3()
    P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client)
    uploaded_first = dict(client.objects)
    again = P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client)
    assert all(r.skipped for r in again)
    assert client.objects == uploaded_first  # unchanged


def test_push_detects_disk_corruption(tmp_path) -> None:
    out = _build_export(tmp_path)
    # Corrupt one artifact after the manifest recorded its checksum.
    parquet = next(out.rglob("*.parquet"))
    parquet.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), FakeS3())


def test_push_summary_counts(tmp_path) -> None:
    out = _build_export(tmp_path)
    store = ObjectStore("wasabi", "sig-bulk")
    results = P.push_export_dir(str(out), store, FakeS3())
    summary = P.push_summary(results, store)
    assert summary["uploaded"] == len(results)
    assert summary["skipped"] == 0
    assert json.dumps(summary)  # JSON-able for the CLI
