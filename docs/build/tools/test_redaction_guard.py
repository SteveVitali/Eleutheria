# SPDX-License-Identifier: Apache-2.0
"""Tests for docs/build/tools/redaction_guard.py (sig.redaction-guard/1).

These tests exercise the guard's *invariants* on synthetic fixtures (BM-TEST-01):
a planted listed handle fails — including under a retained-history prefix; a
planted forbidden key fails globally; an owner key fails inside the declared
sweep set but not outside it; a clean tree passes; and no failure output leaks
the planted string. No test pins a living record's current value.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import redaction_guard  # noqa: E402

HANDLE = "synthetic_personal_handle_x"  # a fixture string, not a listed handle
HANDLE_DIGEST = hashlib.sha256(HANDLE.encode()).hexdigest()

SWEEP = "docs/build/reports/catalog_sweep_test.json"
RETAINED_PATH = "docs/build/runs/test_run.md"
PLAIN_PATH = "docs/build/reports/test_plain.json"

BASE_POLICY = {
    "schema": "sig.redaction-guard-policy/1",
    "handle_digests_sha256": [HANDLE_DIGEST],
    "handle_lengths": [len(HANDLE)],
    "forbidden_keys_anywhere": ["item" + "_owner"],
    "forbidden_keys_in_sweeps": ["owner", "item" + "_owner"],
    "sweep_files": [SWEEP],
    "sweep_globs": [],
    "self_exempt_paths": ["docs/build/tools/redaction_guard.py"],
}


def _tree(tmp_path: Path, files: dict[str, bytes]) -> Path:
    for rel, data in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return tmp_path


def _scan(tmp_path: Path, files: dict[str, bytes], policy: dict | None = None) -> dict:
    root = _tree(tmp_path, files)
    return redaction_guard.scan(root, sorted(files), policy or BASE_POLICY)


def test_clean_tree_passes(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {
            RETAINED_PATH: b"nothing sensitive here\n",
            PLAIN_PATH: json.dumps({"a": 1, "nested": [{"owner": "schema-field"}]}).encode(),
        },
    )
    assert report["verdict"] == "pass"
    assert report["violations"]["handle_reappearance"]["hits"] == 0
    assert report["violations"]["owner_field_in_sweep"]["files"] == 0


def test_listed_handle_fails_in_retained_prefix(tmp_path: Path) -> None:
    report = _scan(tmp_path, {RETAINED_PATH: f"the id is {HANDLE} here\n".encode()})
    assert report["verdict"] == "fail"
    v = report["violations"]["handle_reappearance"]
    assert v["files"] == 1 and v["hits"] == 1
    assert v["paths"] == [RETAINED_PATH]
    # Output reports paths and counts only — never the matched string.
    assert HANDLE not in json.dumps(report)


def test_listed_handle_fails_when_glued_into_longer_word(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {RETAINED_PATH: f"prefix-{HANDLE}-suffix and xx{HANDLE}yy\n".encode()},
    )
    assert report["verdict"] == "fail"
    assert report["violations"]["handle_reappearance"]["hits"] >= 2


def test_listed_handle_in_tracked_path_fails(tmp_path: Path) -> None:
    report = _scan(tmp_path, {f"docs/{HANDLE}/x.txt": b"payload\n"})
    assert report["verdict"] == "fail"
    v = report["violations"]["handle_reappearance"]
    assert v["files"] == 1 and v["hits"] >= 1


def test_forbidden_key_fails_anywhere(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {PLAIN_PATH: json.dumps({"datasets": [{"item_owner": "x", "id": 1}]}).encode()},
    )
    assert report["verdict"] == "fail"
    v = report["violations"]["forbidden_key_anywhere"]
    assert v["files"] == 1 and v["hits"] == 1


def test_forbidden_key_line_start_form_fails(tmp_path: Path) -> None:
    report = _scan(tmp_path, {"cfg/app.toml": b'item_owner = "x"\n'})
    assert report["verdict"] == "fail"
    assert report["violations"]["forbidden_key_anywhere"]["files"] == 1


def test_owner_field_fails_inside_declared_sweep(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {SWEEP: json.dumps({"datasets": [{"id": 1, "owner": "arcgis-user"}]}).encode()},
    )
    assert report["verdict"] == "fail"
    v = report["violations"]["owner_field_in_sweep"]
    assert v["files"] == 1 and v["paths"] == [SWEEP]


def test_owner_field_outside_sweep_is_allowed(tmp_path: Path) -> None:
    # obligation-event/1 rows legitimately carry an "owner" schema field — the
    # guard must NOT fail a global owner grep (RULING E-1: scoped, not global).
    report = _scan(
        tmp_path,
        {
            "docs/build/reports/obligations/events.jsonl": (
                b'{"schema": "obligation-event/1", "owner": "the operator"}\n'
            )
        },
    )
    assert report["verdict"] == "pass"
    assert report["violations"]["owner_field_in_sweep"]["files"] == 0


def test_unreadable_declared_sweep_falls_back_to_bytes(tmp_path: Path) -> None:
    # A sweep file that no longer parses as JSON is scanned as bytes — a bare
    # key pattern there still fails (fail-closed, never waved through).
    report = _scan(tmp_path, {SWEEP: b'not json {{{ "owner": x\n'})
    assert report["verdict"] == "fail"
    assert report["violations"]["owner_field_in_sweep"]["files"] == 1


def test_policy_loads_and_committed_policy_shape(tmp_path: Path) -> None:
    policy = redaction_guard.load_policy(
        Path(__file__).resolve().parent / "record_policy" / "redaction_guard.json"
    )
    # Invariants of the committed policy (not living values): digests are
    # sha256-shaped, lengths are positive ints, the sweep set is non-empty,
    # and the guard's own files are self-exempt so the guard does not flag
    # its own declarations.
    assert policy["handle_digests_sha256"]
    for d in policy["handle_digests_sha256"]:
        assert redaction_guard._HEX_64.match(d)
    assert all(isinstance(n, int) and n > 0 for n in policy["handle_lengths"])
    assert policy["sweep_files"]
    assert "docs/build/tools/redaction_guard.py" in policy["self_exempt_paths"]


def test_main_exit_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {RETAINED_PATH: b"clean\n"}
    _tree(tmp_path, files)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(BASE_POLICY), encoding="utf-8")
    monkeypatch.setattr(redaction_guard, "tracked_files", lambda _root: sorted(files))
    rc = redaction_guard.main(["--root", str(tmp_path), "--policy", str(policy_path)])
    assert rc == 0
    (tmp_path / RETAINED_PATH).write_bytes(f"{HANDLE}\n".encode())
    rc = redaction_guard.main(["--root", str(tmp_path), "--policy", str(policy_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert HANDLE not in out
