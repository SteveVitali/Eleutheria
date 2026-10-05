# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""living_record_backtest — the nightly advance backtest over a fixture git
repo (P34.31, SIG-ENG-040). Commit C plants a test pinning a living value;
commit C′ legitimately changes the value; the replay must name the test and
the transition. The real tree's report shape is asserted read-only."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "docs/build/tools/record_policy/living_records.toml"

_spec = importlib.util.spec_from_file_location(
    "living_record_backtest", REPO_ROOT / "docs/build/tools/living_record_backtest.py"
)
assert _spec and _spec.loader
bt = importlib.util.module_from_spec(_spec)
sys.modules["living_record_backtest"] = bt
_spec.loader.exec_module(bt)

PIN_TEST = """
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_living_pin():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket: P9.1" in text


def test_invariant():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket:" in text
"""

FIXED_TEST = """
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_living_pin():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket:" in text


def test_invariant():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket:" in text
"""

CONV_TEST = """
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_converted_pin():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket: P9.1" in text
"""

FIXED_CONV_TEST = """
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_converted_pin():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    assert "nextTicket:" in text
"""

# A lint-clean invariant over a living read: the assert carries no key, named
# id, status, or date literal, so the lint never flags it — a failure means
# the transition head's own tree is broken (the fix-forward shape), not a pin.
TREE_TEST = """
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tree_invariant():
    text = (ROOT / "docs" / "build" / "LEDGER.md").read_text()
    errors = [ln for ln in text.splitlines() if "BROKEN" in ln]
    assert errors == []
"""


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=backtest@example.invalid",
            "-c",
            "user.name=backtest",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def _commit(repo: Path, files: dict[str, str], msg: str) -> str:
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD").strip()


def _fixture_repo(root: Path) -> dict:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    c1 = _commit(
        repo,
        {
            "docs/build/LEDGER.md": "# ledger\nnextTicket: P9.1\n",
            "tests/test_pin.py": PIN_TEST,
            "tests/test_conv.py": CONV_TEST,
            "tests/test_tree.py": TREE_TEST,
        },
        "C: pins planted",
    )
    c2 = _commit(
        repo,
        {
            # legit living change that also breaks the committed tree —
            # the closeout-head shape: lint-clean tests trip on the tree
            # itself, pins trip on their stale literal.
            "docs/build/LEDGER.md": "# ledger\nBROKEN row\nnextTicket: P9.2\n",
        },
        "C': living change landing a transiently broken tree",
    )
    c3 = _commit(
        repo,
        {
            "docs/build/LEDGER.md": "# ledger\nnextTicket: P9.9\n",
            "tests/test_conv.py": FIXED_CONV_TEST,
        },
        "C'': living change + one pin converted (one stays live at HEAD)",
    )
    return {"repo": repo, "c1": c1, "c2": c2, "c3": c3}


def test_transitions_and_pin_caught(tmp_path: Path) -> None:
    fx = _fixture_repo(tmp_path)
    policy = bt.load_policy(POLICY_PATH)
    trans = bt.transitions(fx["repo"], policy, window=50)
    assert len(trans) == 2
    assert trans[0]["changed_living"] == ["docs/build/LEDGER.md"]
    evaluated = bt.evaluated_tests_at(fx["repo"], fx["c1"], policy)
    assert ("tests/test_pin.py", "test_living_pin") in evaluated
    assert ("tests/test_pin.py", "test_invariant") in evaluated

    report = bt.run(fx["repo"], window=50, max_transitions=5, timeout=120, policy_path=POLICY_PATH)
    assert report["schema"] == "living-backtest/1"
    assert report["totals"]["transitions_replayed"] == 2
    assert report["totals"]["tests_replayed"] > 0
    # test_living_pin is byte-identical at HEAD (C3 never fixed it): its
    # failure on each replayed tree is a live pin — one pin-broken per
    # transition.
    assert report["totals"]["pin_broken"] == 2
    pin = [f for tr in report["transitions"] for f in tr["failures"] if f["class"] == "pin-broken"]
    assert len(pin) == 2
    assert all("test_living_pin" in f["test"] for f in pin)
    # the converted shape: the pin still fails on each replayed tree but its
    # test is edited at HEAD — resolved history, reported as the conversion,
    # not a pin finding
    converted = [
        f
        for tr in report["transitions"]
        for f in tr["failures"]
        if f["class"] == "converted-in-head"
    ]
    assert len(converted) == 2
    assert all("test_converted_pin" in f["test"] for f in converted)
    # the lint-clean invariant fails only on the broken C′ tree — its class is
    # the tree's, never a pin's, whatever the test's later fate.
    broken = [
        f for tr in report["transitions"] for f in tr["failures"] if f["class"] == "broken-tree"
    ]
    assert len(broken) == 1
    assert "test_tree_invariant" in broken[0]["test"]
    assert report["totals"]["broken_tree"] == 1


def test_vacuous_run_is_never_green(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {"docs/build/LEDGER.md": "nextTicket: P9.1\n"}, "only")
    code = bt.main(
        [
            "--root",
            str(repo),
            "--window",
            "10",
            "--max-transitions",
            "5",
            "--policy",
            str(POLICY_PATH),
        ]
    )
    assert code == 3


def test_pin_broken_exit_code(tmp_path: Path) -> None:
    fx = _fixture_repo(tmp_path)
    out_json = tmp_path / "report.json"
    code = bt.main(
        [
            "--root",
            str(fx["repo"]),
            "--window",
            "50",
            "--max-transitions",
            "5",
            "--policy",
            str(POLICY_PATH),
            "--json",
            str(out_json),
        ]
    )
    assert code == 1
    report = json.loads(out_json.read_text())
    assert report["totals"]["pin_broken"] == 2


def test_real_tree_report_is_well_formed() -> None:
    """The committed repo replays cleanly — the nightly gate's floor."""
    report = bt.run(REPO_ROOT, window=60, max_transitions=2, timeout=300)
    assert report["schema"] == "living-backtest/1"
    assert report["totals"]["transitions_with_living_change"] > 0
    assert report["totals"]["tests_replayed"] > 0
    assert report["totals"]["infra"] == 0, json.dumps(report["transitions"], indent=1)
    assert report["totals"]["pin_broken"] == 0, json.dumps(report["transitions"], indent=1)
