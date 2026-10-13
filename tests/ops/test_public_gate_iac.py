# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21b leg L1 — `ops/gcp/public-gate.sh` offline contract.

The ticket's engineering acceptance criteria, pinned on fixtures (never the
live bucket): the script is dry-run by default with no ADC and no network; the
exclusion set derives from the committed `ops/cadence.toml` sig-public probe
targets plus the tombstone prefix; `plan` prints the exact unconditional→
conditioned IAM diff and the rollback line; `--apply` refuses without the
verbatim `SIG_PUBLIC_GATE_GO`, without a saved+sha256-verified pre-state, and
inside the daily band; the no-delete invariant holds (no object deletion code
path — SIG-OPS-004); `--verify --from-state` reads a recorded policy and names
any surviving unconditional anonymous binding. `--apply` itself never runs
against production here: a stub `gcloud` on PATH records invocations.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "public-gate.sh"

INSIDE_DAILY_BAND = "2026-10-05T05:00:00Z"  # future-ok: synthetic: gate window fixture
OPEN_WINDOW = "2026-10-05T12:00:00Z"  # future-ok: synthetic: gate window fixture
GO = "yes — the A-0.2 go, recorded verbatim in GATE DECISIONS"

_POLICY = {
    "bindings": [
        {
            "role": "roles/storage.legacyObjectReader",
            "members": ["allUsers", "allAuthenticatedUsers"],
        },
        {"role": "roles/storage.admin", "members": ["serviceAccount:ci@example.iam"]},
    ],
    "etag": "Bw==",
    "version": 1,
}
_DESCRIBE = {
    "versioning": {"enabled": True},
    "iamConfiguration": {
        "uniformBucketLevelAccess": {"enabled": True},
        "publicAccessPrevention": "inherited",
    },
}
_LISTING = """gs://example-proj-sig-public/manifest.json
gs://example-proj-sig-public/LICENCES.json
gs://example-proj-sig-public/peel_odl1/sites.csv
gs://example-proj-sig-public/peel_odl1/claims.jsonl
gs://example-proj-sig-public/peel_odl1/sites.parquet
gs://example-proj-sig-public/r/2026-09-27/manifest.json
"""

_STUB_GCLOUD = """#!/usr/bin/env bash
# Offline gcloud stub: logs every invocation to $GCLOUD_STUB_LOG, then serves
# canned replies. set-iam-policy STASHES the applied file so the next
# get-iam-policy serves it (the post-apply verify path).
printf '%s\\n' "$*" >> "${GCLOUD_STUB_LOG:-/dev/null}"
case "$*" in
  "auth application-default print-access-token") echo stub-token ;;
  "storage buckets describe"*) cat "$STUB_DESCRIBE" ;;
  "storage buckets get-iam-policy"*)
    if [ -f "${STUB_IAM_AFTER_PATH:-/nonexistent}" ]; then
      cat "$STUB_IAM_AFTER_PATH"; else cat "$STUB_IAM"; fi ;;
  "storage ls"*)
    if [ -n "$STUB_LISTING" ]; then
      cat "$STUB_LISTING"; else echo gs://example-proj-sig-public/manifest.json; fi ;;
  "storage buckets set-iam-policy"*)
    cp "${!#}" "$STUB_IAM_AFTER_PATH"; echo "Updated IAM policy" ;;
  "storage cp"*) echo "Copying file" ;;
  *) echo '{}' ;;
esac
"""

_CURL_STUB = """#!/usr/bin/env bash
# Offline curl stub: excluded objects + the tombstone answer 200; everything
# else on storage.googleapis.com answers 403 (the anonymous-read-off state).
url="${!#}"
printf '%s\\n' "$url" >> "${CURL_STUB_LOG:-/dev/null}"
case "$url" in
  *storage.googleapis.com*/manifest.json|*storage.googleapis.com*/LICENCES.json|\
  *storage.googleapis.com*/peel_odl1/sites.csv|*storage.googleapis.com*/tombstones/*)
    echo 200 ;;
  *storage.googleapis.com*) echo 403 ;;
  *) echo 200 ;;
esac
"""


def _env(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.pop("SIG_PUBLIC_GATE_GO", None)
    env.pop("SIG_PUBLIC_GATE_NOW", None)
    env.pop("SIG_PUBLIC_GATE_EXCLUDE", None)
    env.update(overrides)
    return env


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env or _env(),
        cwd=str(REPO_ROOT),
    )


def _write_prestate(
    root: Path,
    *,
    policy: dict | None = None,
    describe: dict | None = None,
    bucket: str = "example-proj-sig-public",
    tamper: bool = False,
) -> Path:
    """A saved pre-state dir (describe/iam/listing + sha256 sidecars)."""
    pre = root / "prestate"
    pre.mkdir(exist_ok=True)
    files = {
        f"describe.{bucket}.json": json.dumps(describe if describe is not None else _DESCRIBE),
        f"iam.{bucket}.json": json.dumps(policy if policy is not None else _POLICY),
        f"listing.{bucket}.txt": _LISTING,
    }
    for name, body in files.items():
        f = pre / name
        f.write_text(body)
        digest = hashlib.sha256(body.encode()).hexdigest()
        if tamper and name.startswith("iam."):
            digest = "0" * 64
        (pre / f"{name}.sha256").write_text(digest)
    return pre


def _stubbed_env(tmp_path: Path, **overrides: str) -> tuple[dict[str, str], Path]:
    """A PATH whose `gcloud`/`curl` are offline stubs; returns (env, gcloud log)."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name, body in (("gcloud", _STUB_GCLOUD), ("curl", _CURL_STUB)):
        stub = bindir / name
        stub.write_text(body)
        stub.chmod(0o755)
    log = tmp_path / "gcloud.log"
    log.touch()
    base = _env(
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT="example-proj",
        GCLOUD_STUB_LOG=str(log),
        CURL_STUB_LOG=str(tmp_path / "curl.log"),
        STUB_DESCRIBE=str(tmp_path / "describe.json"),
        STUB_IAM=str(tmp_path / "iam.json"),
        STUB_IAM_AFTER_PATH=str(tmp_path / "iam-after.json"),
        SIG_PUBLIC_GATE_EVIDENCE_DIR=str(tmp_path / "evidence"),
    )
    (tmp_path / "describe.json").write_text(json.dumps(_DESCRIBE))
    (tmp_path / "iam.json").write_text(json.dumps(_POLICY))
    base.update(overrides)
    return base, log


# --- dry-run by default ---------------------------------------------------------


def test_plan_without_prestate_refuses_and_never_calls_gcloud() -> None:
    # no stub at all: the offline path must not even try gcloud
    result = _run(["plan"], env=_env(SIG_GCP_PROJECT="example-proj"))
    assert result.returncode == 46
    assert "--prestate" in result.stderr


def test_check_apply_without_prestate_names_every_gate(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    result = _run(["apply"], env=env)
    assert result.returncode == 0, result.stderr
    assert "SIG_PUBLIC_GATE_GO" in result.stdout
    assert "--prestate" in result.stdout
    assert log.read_text() == ""  # no gcloud call in check mode


def test_prefixes_derives_cadence_targets_and_tombstone(tmp_path: Path) -> None:
    env, _ = _stubbed_env(tmp_path)
    result = _run(["prefixes"], env=env)
    assert result.returncode == 0, result.stderr
    # the committed sig-public probe targets (ops/cadence.toml)
    assert "LICENCES.json" in result.stdout
    assert "manifest.json" in result.stdout
    assert "peel_odl1/sites.csv" in result.stdout
    assert "tombstones/" in result.stdout
    assert "reason=" in result.stdout


def test_list_summarises_a_saved_listing(tmp_path: Path) -> None:
    pre = _write_prestate(tmp_path)
    result = _run(
        ["list", "--listing", str(pre / "listing.example-proj-sig-public.txt")],
        env=_env(SIG_GCP_PROJECT="example-proj"),
    )
    assert result.returncode == 0, result.stderr
    assert "peel_odl1/" in result.stdout
    assert "(root)" in result.stdout
    assert "6 objects total" in result.stdout


def test_plan_prints_unconditional_to_conditioned_diff_and_rollback(tmp_path: Path) -> None:
    env, _ = _stubbed_env(tmp_path)
    pre = _write_prestate(tmp_path)
    result = _run(["plan", "--prestate", str(pre)], env=env)
    assert result.returncode == 0, result.stderr
    assert "BEFORE roles/storage.legacyObjectReader" in result.stdout
    assert "unconditional" in result.stdout
    assert "AFTER  roles/storage.legacyObjectReader" in result.stdout
    assert "rollback: gcloud storage buckets set-iam-policy" in result.stdout
    new = json.loads((pre / "policy.new.json").read_text())
    anon = [
        b
        for b in new["bindings"]
        if {"allUsers", "allAuthenticatedUsers"} & set(b.get("members", []))
    ]
    assert len(anon) == 1, anon
    binding = anon[0]
    assert binding["role"] == "roles/storage.legacyObjectReader"
    expr = binding["condition"]["expression"]
    assert "manifest.json" in expr and "LICENCES.json" in expr
    assert "peel_odl1/sites.csv" in expr
    assert "resource.name ==" in expr  # exact-object keeps, not whole-tree
    # the named account binding is preserved verbatim
    assert any(
        b["role"] == "roles/storage.admin" and "serviceAccount:ci@example.iam" in b["members"]
        for b in new["bindings"]
    )


def test_extra_excludes_join_the_condition(tmp_path: Path) -> None:
    env, _ = _stubbed_env(tmp_path)
    pre = _write_prestate(tmp_path)
    result = _run(
        ["plan", "--prestate", str(pre), "--exclude", "tiles/canary/"],
        env=env,
    )
    assert result.returncode == 0, result.stderr
    new = json.loads((pre / "policy.new.json").read_text())
    expr = json.dumps(new)
    assert "tiles/canary/" in expr
    assert "resource.name.startsWith" in expr  # prefix form


# --- the gates -------------------------------------------------------------------


def test_apply_refuses_without_verbatim_go(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    pre = _write_prestate(tmp_path)
    result = _run(["--apply", "apply", "--prestate", str(pre)], env=env)
    assert result.returncode == 43
    assert "SIG_PUBLIC_GATE_GO" in result.stderr
    assert "set-iam-policy" not in log.read_text()


def test_apply_refuses_without_saved_prestate(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    result = _run(
        ["--apply", "apply"],
        env={**env, "SIG_PUBLIC_GATE_NOW": OPEN_WINDOW},
    )
    assert result.returncode == 44
    assert "--prestate" in result.stderr
    assert "set-iam-policy" not in log.read_text()


def test_apply_refuses_inside_daily_band(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    pre = _write_prestate(tmp_path)
    result = _run(
        ["--apply", "apply", "--prestate", str(pre)],
        env={**env, "SIG_PUBLIC_GATE_NOW": INSIDE_DAILY_BAND},
    )
    assert result.returncode == 42
    assert "03:00-10:00Z" in result.stderr
    assert "set-iam-policy" not in log.read_text()


def test_apply_refuses_tampered_prestate(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    pre = _write_prestate(tmp_path, tamper=True)
    result = _run(
        ["--apply", "apply", "--prestate", str(pre)],
        env={**env, "SIG_PUBLIC_GATE_NOW": OPEN_WINDOW},
    )
    assert result.returncode == 44
    assert "sha256" in result.stderr
    assert "set-iam-policy" not in log.read_text()


def test_apply_refuses_without_live_p343_versioning(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    pre = _write_prestate(
        tmp_path,
        describe={
            "versioning": {"enabled": False},
            "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": True}},
        },
    )
    result = _run(
        ["--apply", "apply", "--prestate", str(pre)],
        env={**env, "SIG_PUBLIC_GATE_NOW": OPEN_WINDOW},
    )
    assert result.returncode == 44
    assert "set-iam-policy" not in log.read_text()


def test_apply_runs_set_iam_policy_and_tombstone_then_post_checks(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    pre = _write_prestate(tmp_path)
    result = _run(
        ["--apply", "apply", "--prestate", str(pre)],
        env={**env, "SIG_PUBLIC_GATE_NOW": OPEN_WINDOW},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    calls = log.read_text()
    assert "storage buckets set-iam-policy" in calls
    assert "storage cp" in calls  # the tombstone note object (additive)
    # the tombstone lands under tombstones/ on the public bucket
    assert "tombstones/2026-09-27-tree.txt" in calls
    # post-checks ran: a re-read of the policy + anonymous probes (verify OK)
    assert calls.count("get-iam-policy") >= 1
    assert "post-checks" in result.stdout
    # the recorded rollback command is printed beside the plan
    assert "rollback: gcloud storage buckets set-iam-policy" in result.stdout


def test_apply_post_checks_fail_when_policy_unchanged(tmp_path: Path) -> None:
    """If set-iam-policy is dropped by the provider, the post-check catches it
    and prints the rollback command (exit 6)."""
    env, log = _stubbed_env(tmp_path, SIG_PUBLIC_GATE_GO=GO)
    # The stub never stashes a new policy: get-iam-policy keeps serving the
    # unconditional fixture → verify DRIFT → the apply must refuse loudly.
    env.pop("STUB_IAM_AFTER_PATH", None)
    stub = tmp_path / "bin" / "gcloud"
    stub.write_text(
        _STUB_GCLOUD.replace(
            'cp "${!#}" "$STUB_IAM_AFTER_PATH"; echo "Updated IAM policy"',
            'echo "Updated IAM policy"',
        )
    )
    stub.chmod(0o755)
    pre = _write_prestate(tmp_path)
    result = _run(
        ["--apply", "apply", "--prestate", str(pre)],
        env={**env, "SIG_PUBLIC_GATE_NOW": OPEN_WINDOW},
    )
    assert result.returncode == 6
    assert "rollback" in result.stderr or "DRIFT" in result.stderr + result.stdout


# --- verify ---------------------------------------------------------------------


def test_verify_from_state_flags_surviving_unconditional_binding(tmp_path: Path) -> None:
    env, _ = _stubbed_env(tmp_path)
    pre = _write_prestate(tmp_path)  # carries the OLD unconditional policy
    result = _run(["--verify", "--from-state", str(pre)], env=env)
    assert result.returncode == 1
    assert "DRIFT" in result.stderr + result.stdout


def test_verify_from_state_passes_on_the_computed_policy(tmp_path: Path) -> None:
    env, _ = _stubbed_env(tmp_path)
    pre = _write_prestate(tmp_path)
    plan = _run(["plan", "--prestate", str(pre)], env=env)
    assert plan.returncode == 0, plan.stderr
    # swap the recorded iam for the computed one — the post-leg state
    new = (pre / "policy.new.json").read_text()
    iam = next(pre.glob("iam.*.json"))
    iam.write_text(new)
    result = _run(["--verify", "--from-state", str(pre)], env=env)
    assert result.returncode == 0, result.stderr + result.stdout


# --- the never-delete invariant ---------------------------------------------------


def test_no_object_deletion_path_exists() -> None:
    # code only — comments are prose about the invariant, not commands
    code = "\n".join(
        line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#")
    )
    for forbidden in (
        "storage rm",
        "objects delete",
        "buckets delete",
        "rsync --delete",
        "storage mv",
        "remove-iam-policy-binding",
    ):
        assert forbidden not in code, f"forbidden mutation path: {forbidden}"


def test_prestate_needs_adc_and_captures_state(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    result = _run(["--apply", "prestate"], env=env)
    assert result.returncode == 0, result.stderr
    calls = log.read_text()
    assert "storage buckets describe" in calls
    assert "get-iam-policy" in calls
    assert "storage ls" in calls
    assert "state-dir:" in result.stdout
