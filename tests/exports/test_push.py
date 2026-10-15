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


# ── P35.5 / SIG-TRANSP-019: fail-closed push bounds + the non-listable origin ──


def test_an_oversized_artifact_refuses_before_any_upload(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    limits = P.PushLimits(max_file_bytes=1)  # every artifact is over the cap
    with pytest.raises(P.PushRefusal, match="per-file cap"):
        P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client, limits=limits)
    assert client.objects == {}  # refused, never truncated


def test_an_over_run_object_cap_run_refuses_before_any_upload(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    limits = P.PushLimits(max_run_objects=0)  # no run fits
    with pytest.raises(P.PushRefusal, match="per-run object cap"):
        P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client, limits=limits)
    assert client.objects == {}


def test_an_over_run_byte_cap_run_refuses_before_any_upload(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    limits = P.PushLimits(max_run_bytes=1)
    with pytest.raises(P.PushRefusal, match="per-run byte cap"):
        P.push_export_dir(str(out), ObjectStore("cloudflare-r2", "sig-bulk"), client, limits=limits)
    assert client.objects == {}


def test_an_over_rate_run_refuses_instead_of_racing(tmp_path) -> None:
    # The request-rate guard: a frozen clock means the second put already
    # exceeds a 1-request/minute cap — the run refuses, it does not slow-play.
    out = _build_export(tmp_path)
    client = FakeS3()
    limits = P.PushLimits(max_requests_per_minute=1)
    with pytest.raises(P.PushRefusal, match="requests/minute"):
        P.push_export_dir(
            str(out),
            ObjectStore("cloudflare-r2", "sig-bulk"),
            client,
            limits=limits,
            clock=lambda: 0.0,
        )
    assert len(client.objects) == 1  # the cap fired on the second put


def test_pacing_interval_sleeps_between_uploads(tmp_path) -> None:
    out = _build_export(tmp_path)
    client = FakeS3()
    slept: list[float] = []
    limits = P.PushLimits(min_request_interval_s=0.05)
    P.push_export_dir(
        str(out),
        ObjectStore("cloudflare-r2", "sig-bulk"),
        client,
        limits=limits,
        sleep=slept.append,
    )
    uploads = sum(1 for _ in client.objects)
    assert slept == [0.05] * (uploads - 1)


def test_a_listing_origin_refuses() -> None:
    def listing_fetch(url: str) -> tuple[int, str]:
        return 200, "<ListBucketResult><Contents><Key>r/…</Key></Contents></ListBucketResult>"

    with pytest.raises(P.PushRefusal, match="non-listable"):
        P.assert_non_listable_origin(listing_fetch, "https://files.example")


def test_an_autoindex_origin_refuses() -> None:
    def index_fetch(url: str) -> tuple[int, str]:
        return 200, "<html><title>Index of /</title>...</html>"

    with pytest.raises(P.PushRefusal, match="non-listable"):
        P.assert_non_listable_origin(index_fetch, "https://files.example")


def test_a_non_listable_origin_passes() -> None:
    def deny_fetch(url: str) -> tuple[int, str]:
        return 403, "<Error><Code>AccessDenied</Code></Error>"

    P.assert_non_listable_origin(deny_fetch, "https://files.example")  # no refusal
