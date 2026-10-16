# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1b — the Artifact Registry cleanup-policy evaluator (fixture-verified).

Everything is deterministic: fixture image-version lists, a pinned ``now``,
and the committed ``ops/gcp/ar-cleanup-policy.json``. The contract under test:
a version is a delete candidate iff a Delete policy's condition matches AND no
Keep policy retains it — the ``keep-younger-than-30d``, ``keep-newest-10`` and
generated ``keep-live-referenced`` rules each hold, and a live-referenced
digest is never a candidate (the fail-closed rule the sweep asserts before
apply).
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ops.ar_cleanup import (
    CleanupPolicyError,
    ImageVersion,
    evaluate,
    load_policy,
    merge_live_referenced,
    normalize_docker_images,
    referenced_digests,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_FILE = REPO_ROOT / "ops" / "gcp" / "ar-cleanup-policy.json"

NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)


def _v(package: str, digest: str, days_old: float, tags=()) -> ImageVersion:
    return ImageVersion(
        package=package,
        version=digest,
        tags=tuple(tags),
        uploaded=(NOW - timedelta(days=days_old)).isoformat(timespec="seconds"),
    )


def _policies(digests=()) -> list[dict]:
    return merge_live_referenced(load_policy(POLICY_FILE), digests)


# --- the committed policy file ------------------------------------------------


def test_committed_policy_loads_and_is_the_documented_shape() -> None:
    policies = load_policy(POLICY_FILE)
    assert len(policies) == 3
    names = {p["name"] for p in policies}
    assert names == {
        "delete-older-than-30d",
        "keep-younger-than-30d",
        "keep-newest-10-per-package",
    }
    delete = next(p for p in policies if p["action"]["type"] == "Delete")
    assert delete["condition"]["olderThan"] == "30d"
    keep_mrv = next(p for p in policies if "mostRecentVersions" in p)
    assert keep_mrv["mostRecentVersions"]["keepCount"] == 10


@pytest.mark.parametrize(
    "doc",
    [
        "not-a-list",
        [{"action": {"type": "Delete"}, "condition": {}}],  # no name
        [{"name": "x", "action": {"type": "Maybe"}, "condition": {}}],
        [{"name": "x", "action": {"type": "Keep"}}],  # neither condition nor mrv
        # a Keep mixing condition + mostRecentVersions — the documented format forbids it
        [
            {
                "name": "x",
                "action": {"type": "Keep"},
                "condition": {"tagState": "any"},
                "mostRecentVersions": {"keepCount": 2},
            }
        ],
        [{"name": "x", "action": {"type": "Delete"}, "condition": {"olderThan": "soon"}}],
    ],
)
def test_load_policy_fails_closed_on_malformed(tmp_path: Path, doc) -> None:
    f = tmp_path / "p.json"
    f.write_text(json.dumps(doc))
    with pytest.raises(CleanupPolicyError):
        load_policy(f)


def test_load_policy_duplicate_names_refused(tmp_path: Path) -> None:
    f = tmp_path / "p.json"
    f.write_text(
        json.dumps(
            [
                {"name": "a", "action": {"type": "Delete"}, "condition": {}},
                {"name": "a", "action": {"type": "Keep"}, "condition": {}},
            ]
        )
    )
    with pytest.raises(CleanupPolicyError):
        load_policy(f)


# --- the merge: the generated live-referenced keep -----------------------------


def test_merge_live_referenced_adds_keep_only_with_digests() -> None:
    base = load_policy(POLICY_FILE)
    assert [p["name"] for p in merge_live_referenced(base, [])] == [p["name"] for p in base]
    merged = merge_live_referenced(base, ["sha256:" + "a" * 64, "sha256:" + "b" * 64])
    gen = merged[-1]
    assert gen["name"] == "keep-live-referenced"
    assert gen["action"]["type"] == "Keep"
    assert gen["condition"]["versionNamePrefixes"] == [
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
    ]


# --- evaluation ----------------------------------------------------------------


def test_old_unreferenced_version_is_a_candidate() -> None:
    # A package's only version is inside its keep-newest-10 window — use a
    # delete+age-bound pair without the keepCount rule to isolate the
    # delete-side semantics.
    policies = [
        {
            "name": "delete-old",
            "action": {"type": "Delete"},
            "condition": {"tagState": "any", "olderThan": "30d"},
        }
    ]
    v = _v("sig-api", "sha256:" + "c" * 64, days_old=60, tags=("build-x",))
    plan = evaluate(policies, [v], now=NOW)
    assert [c["version"] for c in plan["candidates"]] == [v.version]
    assert plan["candidates"][0]["matchedBy"] == ["delete-old"]


def test_newest_10_window_keeps_a_sole_old_version() -> None:
    # The committed keepCount-10 window retains a package's ten most recent
    # versions at any age — a lone old version is never a candidate (the
    # conservative side of the keep rules).
    v = _v("sig-api", "sha256:" + "c" * 64, days_old=60, tags=("build-x",))
    plan = evaluate(_policies(), [v], now=NOW)
    assert plan["candidates"] == []
    assert plan["kept"][0]["by"] == "keep-newest-10-per-package"


def test_live_referenced_version_is_never_a_candidate() -> None:
    # The referenced digest is the OLDEST of eleven >30d versions — outside
    # both the <30d keep and the newest-10 window; only the generated
    # live-referenced keep retains it.
    digest = "sha256:" + "1" * 64
    versions = [_v("sig-api", f"sha256:{i:064d}", days_old=200 - i) for i in range(10)]
    versions.append(_v("sig-api", digest, days_old=201))
    plan = evaluate(_policies([digest]), versions, now=NOW)
    assert plan["candidates"] == []
    by_ref = [k for k in plan["kept"] if k["by"] == "keep-live-referenced"]
    assert [k["version"] for k in by_ref] == [digest]


def test_younger_than_30d_is_kept() -> None:
    v = _v("sig-api", "sha256:" + "2" * 64, days_old=10)
    plan = evaluate(_policies(), [v], now=NOW)
    assert plan["candidates"] == []
    # Either "no delete policy matches" (the <30d version never meets the
    # delete condition) — the <30d keep is belt-and-suspenders, not required.
    assert plan["kept"][0]["version"] == v.version


def test_newest_10_per_package_survive() -> None:
    # Thirteen versions of one package, all older than 30d: the newest ten are
    # kept, the oldest three are candidates.
    versions = [_v("sig-api", f"sha256:{i:064d}", days_old=100 - i) for i in range(13)]
    plan = evaluate(_policies(), versions, now=NOW)
    kept_newest = {c["version"] for c in plan["kept"] if c["by"] == "keep-newest-10-per-package"}
    assert len(kept_newest) == 10
    candidates = {c["version"] for c in plan["candidates"]}
    assert candidates == {f"sha256:{i:064d}" for i in (0, 1, 2)}


def test_keep_window_is_per_package() -> None:
    a = [_v("sig-api", f"sha256:a{i:063d}", days_old=60 + i) for i in range(12)]
    b = [_v("sig-batch", f"sha256:b{i:063d}", days_old=60 + i) for i in range(12)]
    plan = evaluate(_policies(), a + b, now=NOW)
    candidates = [c for c in plan["candidates"]]
    assert len(candidates) == 4
    assert {c["package"] for c in candidates} == {"sig-api", "sig-batch"}


def test_tag_state_and_prefix_conditions() -> None:
    policies = [
        {
            "name": "delete-old-untagged",
            "action": {"type": "Delete"},
            "condition": {"tagState": "untagged", "olderThan": "1d"},
        },
        {
            "name": "keep-release-tags",
            "action": {"type": "Keep"},
            "condition": {"tagState": "tagged", "tagPrefixes": ["release"]},
        },
    ]
    tagged_release = _v("p", "sha256:" + "d" * 64, 90, tags=("release-9",))
    tagged_other = _v("p", "sha256:" + "e" * 64, 90, tags=("nightly",))
    untagged = _v("p", "sha256:" + "f" * 64, 90)
    plan = evaluate(policies, [tagged_release, tagged_other, untagged], now=NOW)
    candidates = {c["version"] for c in plan["candidates"]}
    # tagged versions never match the untagged delete; the release tag is kept
    # anyway. Only the old untagged version is a candidate.
    assert candidates == {untagged.version}


def test_undated_version_fails_closed_under_age_bounds() -> None:
    v = ImageVersion(package="p", version="sha256:" + "0" * 64, tags=(), uploaded="")
    plan = evaluate(_policies(), [v], now=NOW)
    # olderThan cannot match an undated version → no delete policy → kept.
    assert plan["candidates"] == []


def test_evaluation_is_deterministic_sorted() -> None:
    policies = [
        {
            "name": "delete-old",
            "action": {"type": "Delete"},
            "condition": {"tagState": "any", "olderThan": "30d"},
        }
    ]
    versions = [
        _v("z-pkg", "sha256:" + "3" * 64, 60),
        _v("a-pkg", "sha256:" + "4" * 64, 60),
        _v("m-pkg", "sha256:" + "5" * 64, 60),
    ]
    plan = evaluate(policies, versions, now=NOW)
    assert [c["package"] for c in plan["candidates"]] == ["a-pkg", "m-pkg", "z-pkg"]
    assert plan["kind"] == "sig.ar-cleanup-candidates/1"
    assert plan["totalVersions"] == 3


# --- input adapters -------------------------------------------------------------


def test_normalize_docker_images_from_gcloud_rows() -> None:
    raw = [
        {
            "image": "us-central1-docker.pkg.dev/p/sig/sig-api",
            "digest": "sha256:" + "6" * 64,
            "tags": ["latest", "ingest-abc"],
            "uploadTime": "2026-09-20T01:02:03Z",
        },
        {
            "image": "us-central1-docker.pkg.dev/p/sig/sig-batch",
            "digest": "sha256:" + "7" * 64,
            "createTime": "2026-09-21T01:02:03Z",
        },
    ]
    versions = normalize_docker_images(raw)
    assert versions[0].package == "sig-api" and versions[0].tags == ("latest", "ingest-abc")
    assert versions[1].package == "sig-batch" and versions[1].uploaded == "2026-09-21T01:02:03Z"


def test_referenced_digests_extracts_only_at_digests() -> None:
    jobs = [
        {"template": {"template": {"containers": [{"image": "repo/x@sha256:" + "8" * 64}]}}},
        {"template": {"template": {"containers": [{"image": "repo/y:latest"}]}}},
    ]
    revs = [{"spec": {"containers": [{"image": "repo/z@sha256:" + "9" * 64}]}}]
    assert referenced_digests(jobs, revs) == [
        "sha256:" + "8" * 64,
        "sha256:" + "9" * 64,
    ]


# --- the CLI seam ----------------------------------------------------------------


def test_cli_merged_policy_and_candidates(tmp_path: Path) -> None:
    digests = tmp_path / "digests.txt"
    digest = "sha256:" + "a" * 64
    digests.write_text(f"# live-referenced\n{digest}\n")
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "ar-cleanup",
            "merged-policy",
            "--policy",
            str(POLICY_FILE),
            "--digests",
            str(digests),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    merged = json.loads(proc.stdout)
    assert merged[-1]["name"] == "keep-live-referenced"

    images = tmp_path / "images.json"
    # Twelve >30d versions of one package: the newest ten survive on keepCount,
    # the referenced oldest survives on keep-live-referenced, and the one
    # remaining old version is the candidate.
    rows = [
        {
            "image": "p/sig-api",
            "digest": f"sha256:{i:064d}",
            "uploadTime": (NOW - timedelta(days=200 - i)).isoformat(),
        }
        for i in range(10)
    ]
    rows.append(
        {
            "image": "p/sig-api",
            "digest": digest,
            "uploadTime": (NOW - timedelta(days=201)).isoformat(),
        }
    )
    rows.append(
        {
            "image": "p/sig-api",
            "digest": "sha256:" + "f" * 64,
            "uploadTime": (NOW - timedelta(days=202)).isoformat(),
        }
    )
    images.write_text(json.dumps(rows))
    merged_path = tmp_path / "merged.json"
    merged_path.write_text(proc.stdout)
    proc2 = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "ar-cleanup",
            "candidates",
            "--policy",
            str(merged_path),
            "--images",
            str(images),
            "--now",
            NOW.isoformat(),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc2.returncode == 0, proc2.stderr
    plan = json.loads(proc2.stdout)
    assert [c["version"] for c in plan["candidates"]] == ["sha256:" + "f" * 64]


def test_cli_candidates_unreadable_input_exits_64(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "ar-cleanup",
            "candidates",
            "--policy",
            str(tmp_path / "absent.json"),
            "--images",
            str(tmp_path / "absent2.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 64
    assert "ar-cleanup:" in proc.stderr
