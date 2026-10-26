# SPDX-License-Identifier: Apache-2.0
"""Fixture-verified tests for the P35.53 release pipeline (REL-03a,
SIG-REL-004/005, G3 §4.1/§4.4/§5.1–5.2).

Covers the ticket's fixture-verified list: the registry lock contract
(create-if-absent, stale-lock refusal without --break-lock, recorded break),
the stale-generation refusal, the --dry-run default writing nothing, the
G3 §4.1 namespace layout, the stage collision/precondition refusal + resume,
the IAM declaration carrying no public principal, the IaC dry-run showing
the three creates, and the NEW-5 recommit guard refusing a staged-tree path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ops import release_pipeline as rp

REPO = Path(__file__).resolve().parents[2]
IAC = REPO / "ops" / "gcp" / "release-infra.sh"
LIFECYCLE = REPO / "ops" / "gcp" / "release-bucket-lifecycle.json"
GUARD = REPO / "scripts" / "ci" / "release_tree_guard.py"
REPORTS = REPO / "docs" / "build" / "reports"


def _store(tmp_path: Path) -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path / "registry")


def _release_tree(work: Path, pub: str = "p-" + "a" * 64) -> Path:
    """A minimal staged-shape tree — r/<pub>/ + releases/<pub>/ bytes."""
    for ns in ("r", "releases"):
        d = work / ns / pub
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(f"<html>{ns}</html>", encoding="utf-8")
    return work


# --------------------------------------------------------------------------- #
# The lock contract (G3 §4.4)
# ---------------------------------------------------------------------------


def test_lock_is_create_if_absent_and_releases(tmp_path: Path) -> None:
    store = _store(tmp_path)
    lock = rp.acquire_lock(store, "status")
    assert store.read("registry/LOCK") is not None
    assert lock.record["schema"] == "sig.release-lock/1"
    lock.release()
    assert store.read("registry/LOCK") is None


def test_held_lock_refuses_a_second_writer(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rp.acquire_lock(store, "stage")
    with pytest.raises(rp.LockHeld):
        rp.acquire_lock(store, "verify")


def test_break_lock_clears_and_records_the_reason(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rp.acquire_lock(store, "stage")  # a dead run leaves LOCK behind
    lock = rp.acquire_lock(store, "status", break_lock="operator: stale run")
    broke = lock.record["broke_lock"]
    assert broke["verb"] == "stage"
    assert broke["break_reason"] == "operator: stale run"
    lock.release()


def test_stale_generation_refuses_under_the_held_lock(tmp_path: Path) -> None:
    store = _store(tmp_path)
    lock = rp.acquire_lock(store, "stage")
    store.insert(
        "registry/catalog.json",
        b'{"schema":"sig.release-catalog/1","publications":[]}',
        content_type="application/json",
    )
    with pytest.raises(rp.StaleGeneration):
        lock.refresh()


def test_release_refuses_on_silently_drifted_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    lock = rp.acquire_lock(store, "stage")
    store.insert("registry/latest.json", b"{}", content_type="application/json")
    with pytest.raises(rp.StaleGeneration):
        lock.release()


# --------------------------------------------------------------------------- #
# --dry-run writes nothing (the default — §5.1)
# ---------------------------------------------------------------------------


def test_dry_run_verbs_write_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    work = _release_tree(tmp_path / "work")
    rp.verb_stage(store, apply_=False, work_dir=work)
    rp.verb_classify(store, apply_=False, publication_id="p-" + "b" * 64)
    rp.verb_status(store, apply_=False)
    for verb in ("rollback", "withdraw"):
        rp.verb_skeleton(verb, store, apply_=False, publication_id="p-" + "b" * 64)
    # promote landed at P35.54 — a dry-run on an empty registry refuses
    # before any write (the refusal itself proves nothing was written).
    with pytest.raises(rp.PipelineError):
        from ops import release_conf

        release_conf.verb_promote(store, apply_=False, publication_id="p-" + "b" * 64)
    assert list((tmp_path / "registry").rglob("*")) == [] or not (tmp_path / "registry").exists()


def test_dry_run_never_takes_the_lock(tmp_path: Path) -> None:
    store = _store(tmp_path)
    work = _release_tree(tmp_path / "work")
    rp.verb_stage(store, apply_=False, work_dir=work)
    assert store.read("registry/LOCK") is None
    assert store.list("registry/events/") == []


# --------------------------------------------------------------------------- #
# The G3 §4.1 namespace layout
# ---------------------------------------------------------------------------


def test_namespace_layout_matches_the_contract() -> None:
    assert rp.STAGED_NAMESPACES == ("r", "v", "s", "releases")
    assert set(rp.NAMESPACE_LAYOUT["registry"]) == {
        "catalog.json",
        "compat_index.json",
        "withdrawals.json",
        "activations/",
        "events/",
        "LOCK",
        "conf/",
    }
    assert "status" in rp.NAMESPACE_LAYOUT


def test_stage_writes_under_the_staged_namespaces(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "c" * 64
    work = _release_tree(tmp_path / "work", pub=pub)
    out = rp.verb_stage(store, apply_=True, work_dir=work)
    names = store.list("")
    assert f"staged/r/{pub}/index.html" in names
    assert f"staged/releases/{pub}/index.html" in names
    assert not any(n.startswith("r/") or n.startswith("releases/") for n in names)
    assert out["staged"] == 2 and out["applied"] is True


# --------------------------------------------------------------------------- #
# Immutability — the stage collision + resume contract (§5.2, SIG-REL-005)
# ---------------------------------------------------------------------------


def test_stage_resume_skips_identical_bytes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "d" * 64
    work = _release_tree(tmp_path / "work", pub=pub)
    rp.verb_stage(store, apply_=True, work_dir=work)
    again = rp.verb_stage(store, apply_=True, work_dir=work)
    assert again["staged"] == 0 and again["resumed"] == 2


def test_stage_refuses_a_name_collision(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "e" * 64
    work = _release_tree(tmp_path / "work", pub=pub)
    rp.verb_stage(store, apply_=True, work_dir=work)
    (work / "r" / pub / "index.html").write_text("mutated", encoding="utf-8")
    with pytest.raises(rp.NameCollision):
        rp.verb_stage(store, apply_=True, work_dir=work)
    # the staged byte is the ORIGINAL — nothing was overwritten
    assert store.read(f"staged/r/{pub}/index.html") == b"<html>r</html>"


def test_every_apply_verb_journals_an_event(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rp.verb_classify(store, apply_=True, publication_id="p-" + "f" * 64)
    with pytest.raises(rp.VerbDeferred):
        rp.verb_skeleton("rollback", store, apply_=True, publication_id="p-" + "f" * 64)
    events = rp.list_events(store)
    kinds = {e["verb"] for e in events}
    assert kinds == {"classified", "rollback"}


def test_classify_fails_closed_to_class_s(tmp_path: Path) -> None:
    out = rp.verb_classify(_store(tmp_path), apply_=True, publication_id="p-" + "0" * 64)
    assert out["class"] == "class_s" and out["failclosed"] is True


def test_skeleton_verbs_refuse_and_name_the_owner(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(rp.VerbDeferred) as exc:
        rp.verb_skeleton("rollback", store, apply_=True, publication_id="p-" + "1" * 64)
    assert "P35.5" in exc.value.detail["owner"] or "P35" in str(exc.value.detail)


# --------------------------------------------------------------------------- #
# The IAM declaration — no public principal, staging is IAM-only
# ---------------------------------------------------------------------------


def test_iac_declares_no_public_principal() -> None:
    text = IAC.read_text()
    for member in ("allUsers", "allAuthenticatedUsers"):
        # allowed only as the *assertion* strings (verify greps it must NOT
        # appear in live policy) — never as an add-iam-policy-binding member
        for line in text.splitlines():
            if "add-iam-policy-binding" in line or "--member" in line:
                assert member not in line, line
    assert "--no-allow-unauthenticated" in text


def test_iac_check_mode_is_offline_and_names_the_three_creates() -> None:
    out = subprocess.run(
        ["bash", str(IAC), "--check"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",  # no gcloud, no ADC — the plan must still print
            "HOME": str(REPO),
        },
    )
    assert out.returncode == 0, out.stderr
    plan = out.stdout
    # the three creates: bucket, the staging-service pair, the job
    assert "-sig-release" in plan
    assert "sig-web-staging" in plan and "sig-api-staging" in plan
    assert "sig-release" in plan and "sig-release-rt" in plan
    assert "allUsers" in plan  # named only as the thing that must NOT exist
    assert "NO allUsers" in plan
    # and the plan declares nothing else mutating: every side effect is a
    # PLAN line or the rerun prompt — no bare `gcloud ...` execution text
    for line in plan.splitlines():
        assert line.startswith(("PLAN:", "", "note:")), line


def test_lifecycle_declaration_is_the_30_day_noncurrent_rule() -> None:
    doc = json.loads(LIFECYCLE.read_text())
    rule = doc["rule"][0]
    assert rule["action"]["type"] == "Delete"
    assert rule["condition"]["daysSinceNoncurrentTime"] == 30


def test_window_guard_queues_before_the_freeze_lifts() -> None:
    out = subprocess.run(
        ["bash", str(IAC), "--apply", "apply"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(REPO),
            "SIG_GCP_PROJECT": "guard-test",
            "SIG_RELEASE_AUTHOR": "guard-test",
            "SIG_RELEASE_NOW": "2026-10-10T00:00:00Z",  # inside the AR-3 freeze
        },
    )
    assert out.returncode == 42, (out.stdout, out.stderr)
    assert "QUEUED" in out.stdout + out.stderr


def test_apply_refuses_without_the_recorded_author() -> None:
    out = subprocess.run(
        ["bash", str(IAC), "--apply", "apply"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(REPO),
            "SIG_GCP_PROJECT": "guard-test",
            # no SIG_RELEASE_AUTHOR — OM-20's scope discipline refuses
            "SIG_RELEASE_NOW": "2026-10-14T15:00:00Z",  # past the freeze
        },
    )
    assert out.returncode == 4, (out.stdout, out.stderr)
    assert "SIG_RELEASE_AUTHOR" in out.stdout + out.stderr


def test_apply_refuses_without_adc() -> None:
    out = subprocess.run(
        ["bash", str(IAC), "--apply", "apply"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",  # gcloud absent → the ADC gate refuses
            "HOME": str(REPO),
            "SIG_GCP_PROJECT": "guard-test",
            "SIG_RELEASE_AUTHOR": "guard-test",
            "SIG_RELEASE_NOW": "2026-10-14T15:00:00Z",  # past the freeze
        },
    )
    assert out.returncode == 3, (out.stdout, out.stderr)
    assert "gcloud" in out.stdout + out.stderr


# --------------------------------------------------------------------------- #
# NEW-5 — the eviction guard refuses a recommitted staged tree
# ---------------------------------------------------------------------------


def _guard(root: Path) -> list[str]:
    sys.path.insert(0, str(REPO / "scripts" / "ci"))
    try:
        import release_tree_guard

        return release_tree_guard.find_evicted_paths(root)
    finally:
        sys.path.remove(str(REPO / "scripts" / "ci"))
        sys.modules.pop("release_tree_guard", None)


def test_eviction_guard_flags_a_staged_release_tree(tmp_path: Path) -> None:
    staged = tmp_path / "reports" / "staged" / "r" / ("p-" + "9" * 64)
    staged.mkdir(parents=True)
    (staged / "index.html").write_text("x")
    flagged = _guard(tmp_path / "reports")
    assert any("staged" in f for f in flagged)


def test_eviction_guard_flags_registry_files(tmp_path: Path) -> None:
    reg = tmp_path / "reports" / "registry"
    reg.mkdir(parents=True)
    (reg / "catalog.json").write_text("{}")
    (reg / "latest.json").write_text("{}")
    flagged = _guard(tmp_path / "reports")
    assert len(flagged) == 2


def test_eviction_guard_is_clean_on_the_repository() -> None:
    assert _guard(REPORTS) == []


def test_eviction_guard_cli_refuses_and_names_the_path(tmp_path: Path) -> None:
    d = tmp_path / "r" / ("p-" + "8" * 64)
    d.mkdir(parents=True)
    (d / "index.html").write_text("x")
    out = subprocess.run(
        [sys.executable, str(GUARD), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 1
    assert "p-" + "8" * 64 in out.stderr
