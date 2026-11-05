# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_security_baseline.py — P37.4a (SIG-SEC-006, ADR-231).

The offline plan of the named mutation script, the window/author gates, the
``sig-ops security-baseline`` verb plans, the deploy-path signing hook, and
the audited-takedown assertion: a withdraw always journals its authority.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ops import security_baseline as SB

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "security-baseline.sh"
LIB = REPO_ROOT / "ops" / "gcp" / "lib.sh"
WEB = REPO_ROOT / "ops" / "gcp" / "web.sh"
CONFIG = REPO_ROOT / "ops" / "gcp" / "config.sh"
SECURITY_MD = REPO_ROOT / "SECURITY.md"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for k in ("SIG_GCP_PROJECT", "SIG_SECB_AUTHOR", "SIG_SECB_NOW"):
        env.pop(k, None)
    env.update(extra or {})
    return env


def _run(args: list[str], extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(extra),
        cwd=str(REPO_ROOT),
    )


# --- the script's offline plan ---------------------------------------------- #


def test_check_plans_the_whole_mutation_offline() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for token in (
        "containeranalysis",
        "containerscanning",
        "cloudkms",
        "sig-release",
        "sig-image-sign",
        "cosign sign",
        "sig.image-signature/1",
        "sbom.cdx.json",
        "security_sign_image",
    ):
        assert token in plan, token


def test_apply_window_guard_and_author_gate() -> None:
    proc = _run(
        ["--apply"],
        {
            "SIG_SECB_NOW": "2026-11-05T05:30:00Z",
            "SIG_SECB_AUTHOR": "op",
            "SIG_GCP_PROJECT": "p",
        },
    )
    assert proc.returncode == 42 and "QUEUED" in proc.stdout
    proc = _run(
        ["--apply"],
        {
            "SIG_SECB_NOW": "2026-11-05T15:30:00Z",
            "SIG_GCP_PROJECT": "p",
        },
    )
    assert proc.returncode == 2
    assert "SIG_SECB_AUTHOR" in (proc.stdout + proc.stderr)


def test_apply_without_project_or_adc_stays_unarmed(tmp_path: Path) -> None:
    proc = _run(
        ["--apply"],
        {
            "SIG_SECB_NOW": "2026-11-05T15:30:00Z",
            "SIG_SECB_AUTHOR": "op",
        },
    )
    assert proc.returncode == 2
    stub = tmp_path / "gcloud"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n")
    stub.chmod(0o755)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(
            {
                "SIG_SECB_NOW": "2026-11-05T15:30:00Z",
                "SIG_SECB_AUTHOR": "op",
                "SIG_GCP_PROJECT": "p",
                "PATH": f"{tmp_path}:{os.environ['PATH']}",
            }
        ),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 3 and "gate pending" in (proc.stdout + proc.stderr)


def test_no_destructive_writes_in_the_leg() -> None:
    text = SCRIPT.read_text()
    for banned in ("buckets delete", "keys destroy", "storage rm ", "rm -r"):
        assert banned not in text
    for guard in ("assert_window", "SIG_SECB_AUTHOR", "require_adc"):
        assert guard in text


# --- the deploy-path wiring -------------------------------------------------- #


def test_deploy_path_carries_the_signing_hook() -> None:
    lib = LIB.read_text()
    assert "security_sign_image" in lib
    assert "SIG_SECB_SIGNING" in lib and "cosign sign" in lib
    web = WEB.read_text()
    assert 'security_sign_image "${pinned}"' in web
    cfg = CONFIG.read_text()
    assert 'SIG_SECB_SIGNING="${SIG_SECB_SIGNING:-0}"' in cfg
    assert "gcpkms://projects/${SIG_GCP_PROJECT}" in cfg


# --- the python verbs -------------------------------------------------------- #


def test_plan_verbs_emit_ordered_steps() -> None:
    apis = SB.api_enable_steps("p")
    assert [a.argv[3] for a in apis] == list(SB.REQUIRED_APIS)
    kms = SB.kms_steps("p")
    joined = " ".join(" ".join(s.argv) for s in kms)
    assert "asymmetric-signing" in joined and "ec-sign-p256-sha256" in joined
    steps = SB.sign_steps("r/i@sha256:" + "a" * 64, SB.kms_key_uri("p"))
    assert steps[0].argv[:3] == ("cosign", "sign", "--yes")
    assert "gcpkms://projects/p/" in SB.kms_key_uri("p")


def test_run_steps_plans_in_check_and_executes_in_apply() -> None:
    steps = [SB.CommandStep("echo", ("echo", "hi"))]
    out = SB.run_steps(steps, apply_=False)
    assert out == ["PLAN: echo: echo hi"]
    out = SB.run_steps(steps, apply_=True, runner=lambda a: "ran\n")
    assert "+ echo hi" in out[0] and "ran" in out[0]


def test_signature_record_schema() -> None:
    rec = SB.signature_record(
        "r/i@sha256:" + "b" * 64,
        key_uri="gcpkms://x",
        signer="op",
        now="2026-11-05T18:00:00Z",
        verify_output="ok\n",
    )
    assert rec["schema"] == "sig.image-signature/1"
    assert rec["signer"] == "op" and rec["image"].startswith("r/i@sha256:")


def test_cli_plan_and_sbom(tmp_path: Path) -> None:
    assert SB.main(["plan", "--project", "p"]) == 0
    out = tmp_path / "sbom.cdx.json"
    assert SB.main(["sbom", "--lock", str(REPO_ROOT / "pylock.toml"), "--out", str(out)]) == 0
    doc = __import__("json").loads(out.read_bytes())
    assert doc["bomFormat"] == "CycloneDX"
    assert (
        SB.main(["sign", "--image", "r/i@sha256:" + "a" * 64, "--project", "p"]) == 0
    )  # check-mode plan


# --- audited takedown -------------------------------------------------------- #


def test_takedown_is_authority_gated_and_audited(tmp_path: Path) -> None:
    """The audited takedown: `check_authority` refuses a missing/malformed
    `sig.operator-authority/1` record and returns the ref the journal carries —
    no unaudited takedown path exists (SIG-SEC-010; the order/receipt journal
    shape itself is pinned by test_release_reversal)."""
    from ops import release_pipeline as rp
    from ops import release_reversal as rr

    store = rp.LocalDirStore(tmp_path / "reg")
    with pytest.raises(rp.PipelineError):
        rr.check_authority(store, "absent")
    _put(
        store,
        "registry/authorities/go-1.json",
        {
            "schema": "sig.operator-authority/1",
            "ref": "GATE-G6 §4",
            "kind": "takedown",
            "issued_at": "2026-11-05T00:00:00Z",
        },
    )
    rec = rr.check_authority(store, "go-1.json")
    assert rec["ref"] == "GATE-G6 §4" and rec["sha256"]
    # revoked / expired / ref-less records refuse loud — never unaudited
    _put(
        store,
        "registry/authorities/bad.json",
        {
            "schema": "sig.operator-authority/1",
            "ref": "",
            "kind": "takedown",
        },
    )
    with pytest.raises(rp.PipelineError):
        rr.check_authority(store, "bad.json")


def _put(store, name: str, body) -> None:
    import json as _json

    data = _json.dumps(body, sort_keys=True).encode() if isinstance(body, dict) else body
    meta = store.stat(name)
    if meta is None:
        store.insert(name, data, content_type="application/json")
    else:
        store.replace(
            name, data, generation=int(meta["generation"]), content_type="application/json"
        )


# --- SECURITY.md -------------------------------------------------------------- #


def test_security_md_declares_the_baseline() -> None:
    text = SECURITY_MD.read_text()
    for token in (
        "sbom.cdx.json",
        "cosign",
        "Cloud KMS",
        "/dispute/",
        "SIG-SEC-006",
        "no SLA",
        "HG-09",
    ):
        assert token in text, token
    # the operator's personal e-mail must never be committed (OP-10)
    assert "@" not in text.replace("sig-release.minisign.pub", "")
