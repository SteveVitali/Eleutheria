# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The zero-egress mirror leg (P35.5, SIG-TRANSP-019): mirrors.toml rows, the
preflight refusals, the non-listable probe and the egress-accounting join — all
against fake clients, no live store (HG-07)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from ops.egress import EgressConfig

from ops import mirror_push as M

_REPO = Path(__file__).resolve().parents[2]
_COMMITTED_MIRRORS = _REPO / "ops" / "mirrors.toml"


class FakeS3:
    """A deterministic in-memory stand-in for the boto3 S3 client."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:  # noqa: N803
        if Key in self.objects:
            return {"Bucket": Bucket, "Key": Key}
        raise KeyError(Key)

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.objects[str(kwargs["Key"])] = kwargs
        return {"ETag": "fake"}


def _export_dir(tmp_path: Path, files: dict[str, bytes] | None = None) -> Path:
    """A minimal built export dir: manifest.json + matching on-disk bytes."""
    out = tmp_path / "export"
    out.mkdir()
    files = files or {"a.json": b'{"x": 1}\n', "b.csv": b"a,b\n1,2\n"}
    artifacts = []
    for path, data in files.items():
        (out / path).write_bytes(data)
        artifacts.append(
            {
                "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_size": len(data),
            }
        )
    (out / "manifest.json").write_text(
        json.dumps({"release_id": "sig-test-1", "artifacts": artifacts}),
        encoding="utf-8",
    )
    return out


def _mirrors(tmp_path: Path, *rows: str) -> Path:
    """A small mirrors.toml fixture."""
    p = tmp_path / "mirrors.toml"
    p.write_text("\n".join(rows), encoding="utf-8")
    return p


_R2_ENABLED = """[[mirror]]
name = "r2"
kind = "object-store"
enabled = true
provider = "cloudflare-r2"
bucket = "sig-bulk"
url = "https://files.example"
"""

_R2_DISABLED = _R2_ENABLED.replace("enabled = true", "enabled = false")

_METERED_ENABLED = """[[mirror]]
name = "metered"
kind = "object-store"
enabled = true
provider = "aws-s3"
bucket = "sig"
url = "https://cdn.example"
"""

_NON_OBJECT_STORE = """[[mirror]]
name = "zen"
kind = "deposit"
enabled = true
url = "https://zenodo.org/"
"""


def test_the_committed_r2_row_parses_disabled() -> None:
    # The contract: the mirror row lands committed-disabled — the live leg
    # enables it (an explicit file change), never a default-true row.
    entry = M.mirror_entry(_COMMITTED_MIRRORS, "r2-public")
    assert entry.enabled is False
    assert entry.kind == "object-store"
    assert entry.provider  # a resolvable push target, just not enabled


def test_a_disabled_row_refuses_the_leg(tmp_path: Path) -> None:
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_DISABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
    )
    with pytest.raises(M.MirrorRefusal, match="enabled=false"):
        leg.preflight()


def test_an_unknown_mirror_name_refuses(tmp_path: Path) -> None:
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="nope",
        export_dir=_export_dir(tmp_path),
    )
    with pytest.raises(M.MirrorRefusal, match="not in"):
        leg.preflight()


def test_a_non_object_store_row_refuses(tmp_path: Path) -> None:
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _NON_OBJECT_STORE),
        name="zen",
        export_dir=_export_dir(tmp_path),
    )
    with pytest.raises(M.MirrorRefusal, match="object-store"):
        leg.preflight()


def test_a_metered_provider_refuses_before_any_upload(tmp_path: Path) -> None:
    # SIG-EXPORT-008 in the publish path: aws-s3 is egress class "metered" —
    # assert_low_egress refuses and no object moves.
    client = FakeS3()
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _METERED_ENABLED),
        name="metered",
        export_dir=_export_dir(tmp_path),
        client=client,
    )
    with pytest.raises(M.MirrorRefusal, match="egress"):
        leg.push()
    assert client.objects == {}


def test_a_missing_manifest_refuses(tmp_path: Path) -> None:
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=tmp_path / "nothing-here",
    )
    with pytest.raises(M.MirrorRefusal, match="manifest"):
        leg.preflight()


def test_the_leg_pushes_content_hash_keys_with_immutable_cache(tmp_path: Path) -> None:
    client = FakeS3()
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
        client=client,
        fetch=lambda url: (403, ""),  # listing denied — the origin stays private
    )
    outcome = leg.push()
    assert outcome.uploaded == 2 and outcome.skipped == 0
    assert outcome.non_listable is True
    for key, kwargs in client.objects.items():
        assert key.startswith("sig-test-1/")  # <release_id>/<path>.<sha12>
        assert kwargs["CacheControl"] == "public, max-age=31536000, immutable"
        assert kwargs["Bucket"] == "sig-bulk"


def test_a_listing_origin_refuses_before_any_upload(tmp_path: Path) -> None:
    client = FakeS3()
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
        client=client,
        fetch=lambda url: (200, "<ListBucketResult><Contents/></ListBucketResult>"),
    )
    with pytest.raises(M.MirrorRefusal, match="non-listable"):
        leg.push()
    assert client.objects == {}


def test_an_egress_alarm_join_refuses_the_leg(tmp_path: Path) -> None:
    # $60 reported against the $50 hard ceiling — the leg refuses (kill switch
    # first, never a push that blows the ceiling further).
    cfg = EgressConfig(
        monthly_budget_gb=100.0,
        alarm_ratio=0.8,
        provider="cloudflare-r2",
        bucket="sig-bulk",
        hard_ceiling_usd=50.0,
    )
    client = FakeS3()
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
        client=client,
        egress_config=cfg,
        usage_usd=60.0,
    )
    with pytest.raises(M.MirrorRefusal, match="ALARM"):
        leg.push()
    assert client.objects == {}


def test_spend_below_the_ceiling_allows_the_leg(tmp_path: Path) -> None:
    cfg = EgressConfig(
        monthly_budget_gb=100.0,
        alarm_ratio=0.8,
        provider="cloudflare-r2",
        bucket="sig-bulk",
        hard_ceiling_usd=50.0,
    )
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
        client=FakeS3(),
        fetch=lambda url: (404, ""),
        egress_config=cfg,
        usage_usd=0.0,  # $0 — the R2 free-tier expectation
    )
    outcome = leg.push()
    assert outcome.egress_level == "ok"


def test_preflight_reports_the_plan_without_touching_the_store(
    tmp_path: Path,
) -> None:
    leg = M.MirrorPushLeg(
        mirrors_path=_mirrors(tmp_path, _R2_ENABLED),
        name="r2",
        export_dir=_export_dir(tmp_path),
        client=FakeS3(),  # preflight never constructs or calls the client
    )
    lines = leg.preflight()
    assert any("preflight OK" in line for line in lines)
    assert any("content-hash keys" in line for line in lines)
