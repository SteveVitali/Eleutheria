# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Egress-friendly distribution + peer distribution (§38.5, SIG-EXPORT-008/009)."""

from __future__ import annotations

from datetime import date

import pytest
from exports.manifest import Artifact, BuildSpec, Manifest

from exports import distribution as D

_SPEC = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1")


def _manifest(*sizes: int) -> Manifest:
    arts = tuple(
        Artifact.of(
            name=f"a{i}.parquet",
            path=f"c/a{i}.parquet",
            media_type="x",
            compartment="c",
            license="CC-BY-4.0",
            data=b"x" * n,
        )
        for i, n in enumerate(sizes)
    )
    return Manifest(_SPEC, arts)


def test_metered_egress_provider_fails_the_build() -> None:
    # SIG-EXPORT-008: success is the failure mode; a metered provider is rejected.
    with pytest.raises(D.EgressError):
        D.assert_low_egress(D.ObjectStore("aws-s3", "sig"))


def test_zero_and_low_egress_providers_are_accepted() -> None:
    D.assert_low_egress(D.ObjectStore("cloudflare-r2", "sig"))  # zero
    D.assert_low_egress(D.ObjectStore("backblaze-b2", "sig"))  # low


def test_largest_artifacts_get_torrent_and_ipfs() -> None:
    # SIG-EXPORT-009: torrent + IPFS for the largest artifacts, small ones plain.
    plan = D.plan_distribution(
        _manifest(10, 1_000_000),
        store=D.ObjectStore("cloudflare-r2", "sig"),
        base_url="https://s3/sig",
        cdn_url="https://cdn/sig",
        large_threshold_bytes=1000,
    )
    small, large = plan.artifacts
    assert small.ipfs_cid is None and small.torrent_magnet is None
    assert large.ipfs_cid is not None and large.torrent_magnet is not None
    assert len(plan.peer_distributed()) == 1


def test_cdn_and_mirror_urls_are_built() -> None:
    plan = D.plan_distribution(
        _manifest(10),
        store=D.ObjectStore("wasabi", "sig"),
        base_url="https://s3/sig",
        cdn_url="https://cdn/sig",
        mirror_base_urls=["https://mirror/sig"],
    )
    art = plan.artifacts[0]
    rel = f"{_SPEC.release_id()}/c/a0.parquet"
    assert art.cdn_url == f"https://cdn/sig/{rel}"
    assert art.mirror_urls == (f"https://mirror/sig/{rel}",)


def test_ipfs_cid_and_magnet_are_deterministic_content_addresses() -> None:
    sha = "a" * 64
    assert D.ipfs_cidv1_raw(sha).startswith("b")
    assert D.ipfs_cidv1_raw(sha) == D.ipfs_cidv1_raw(sha)
    assert (
        D.torrent_magnet_v2(sha, "x.parquet") == "magnet:?xt=urn:btmh:1220" + sha + "&dn=x.parquet"
    )


def test_largest_artifact_selects_by_size() -> None:
    m = _manifest(5, 99, 20)
    assert D.largest_artifact(m.artifacts).byte_size == 99
    assert D.largest_artifact(()) is None
