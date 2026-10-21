# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.41a (D1): the partitioned pytest runner's contract (contract AC 1–2).

`scripts/ci/pytest_partitions.py` splits the suite into the committed
partition table and runs one pytest process per partition. These tests drive
the runner at a temporary tree through ``--root`` and substitute the pytest
command through ``PYTEST_PARTITIONS_CMD`` (the only place that seam is
legal — it appears in neither ``ci.yml`` nor the ``Makefile``). Every
subprocess these tests start gets an env with ``RUNNER_TEMP``,
``GITHUB_ACTIONS``, ``GITHUB_STEP_SUMMARY``, ``GITHUB_OUTPUT``,
``GITHUB_RUN_ID``, ``GITHUB_RUN_ATTEMPT`` and every ``CI_*``/``PYTEST_*``
variable removed or pointed at ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from support import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "pytest_partitions.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pytest_partitions", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PP = _load_module()

_SCRUB_EXACT = {
    "GITHUB_ACTIONS",
    "GITHUB_STEP_SUMMARY",
    "GITHUB_OUTPUT",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "PYTEST_PARTITIONS_CMD",
}


def _scrubbed_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    """The env every spawned subprocess sees: CI/pytest ambient state removed,
    RUNNER_TEMP pointed at tmp_path."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in _SCRUB_EXACT and not k.startswith(("CI_", "PYTEST_", "RUNNER_TEMP"))
    }
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir(parents=True, exist_ok=True)
    env["RUNNER_TEMP"] = str(runner_temp)
    env.update(extra)
    return env


FAKE_PYTEST = """\
import sys

args = sys.argv[1:]
pos = []
skip = False
for a in args:
    if skip:
        skip = False
        continue
    if a in ("-p", "--basetemp"):
        skip = True
        continue
    if a.startswith("-"):
        continue
    pos.append(a)
joined = " ".join(pos)
if "d-failpass" in joined:
    print("===== 1 passed in 0.01s =====")
    sys.exit(1)
if "d-fail" in joined:
    sys.exit(1)
if "d-empty" in joined:
    sys.exit(5)
if "d-nosummary" not in joined:
    print("collected 1 item")
    print("===== 1 passed in 0.01s =====")
sys.exit(0)
"""


def _make_tree(tmp_path: Path, partitions: str, dirs=("tests/a", "tests/b")) -> Path:
    root = tmp_path / "repo"
    (root / "scripts" / "ci").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "ci" / "pytest_partitions.txt").write_text(partitions, encoding="utf-8")
    return root


def _fake_pytest(tmp_path: Path) -> str:
    fake = tmp_path / "fake_pytest.py"
    fake.write_text(FAKE_PYTEST, encoding="utf-8")
    return f"{sys.executable} {fake}"


def _run(root: Path, tmp_path: Path, cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--root", str(root)],
        capture_output=True,
        text=True,
        env=_scrubbed_env(tmp_path, PYTEST_PARTITIONS_CMD=cmd),
    )


def _check(root: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check", "--root", str(root)],
        capture_output=True,
        text=True,
        env=_scrubbed_env(tmp_path),
    )


# --- AC 1: the committed partition file is valid; the union covers all ---


def test_committed_partition_file_passes_check(tmp_path) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        capture_output=True,
        text=True,
        env=_scrubbed_env(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr


def test_collect_union_over_partitions_equals_whole_collection(tmp_path) -> None:
    """AC 1's union check: on a temporary tree the node ids collected across
    the partitions equal the whole collection, with no duplicates — including
    the `*` partition's `--ignore` behaviour and a named `testpaths` entry."""
    root = tmp_path / "repo"
    (root / "scripts" / "ci").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests", "docs/tools"]\n',
        encoding="utf-8",
    )
    for d in ("tests/a", "tests/b", "tests/c", "docs/tools"):
        (root / d).mkdir(parents=True)
    (root / "tests" / "a" / "test_a.py").write_text("def test_a():\n    pass\n")
    (root / "tests" / "b" / "test_b.py").write_text("def test_b():\n    pass\n")
    (root / "tests" / "c" / "test_c.py").write_text("def test_c():\n    pass\n")
    (root / "docs" / "tools" / "test_d.py").write_text("def test_d():\n    pass\n")
    (root / "scripts" / "ci" / "pytest_partitions.txt").write_text(
        "tests/a\ndocs/tools\n*\n", encoding="utf-8"
    )

    def collect(*args: str) -> list[str]:
        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"]
        proc = subprocess.run(
            [*cmd, "--collect-only", "-q", *args],
            capture_output=True,
            text=True,
            cwd=root,
            env=_scrubbed_env(tmp_path),
        )
        assert proc.returncode in (0, 5), proc.stdout + proc.stderr
        return sorted(line for line in proc.stdout.splitlines() if "::test_" in line)

    whole = collect("tests", "docs/tools")
    part_a = collect("tests/a")
    part_tools = collect("docs/tools")
    part_star = collect("--ignore=tests/a", "--ignore=docs/tools", "tests")
    assert whole, "the fixture tree must collect something (vacuous union is red)"
    union = part_a + part_tools + part_star
    assert sorted(union) == whole, (
        "the partitions must cover the whole collection exactly once "
        f"(union={union}, whole={whole})"
    )
    assert len(union) == len(set(union)), "a node id collected twice is an overlap"


# --- AC 2: run verdicts ------------------------------------------------------


def test_run_all_partitions_pass_exits_zero(tmp_path) -> None:
    root = _make_tree(tmp_path, "tests/a\ntests/b\n*\n")
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "nproc=" in proc.stdout
    for k in (1, 2, 3):
        assert f"partition {k} " in proc.stdout


def test_run_one_failing_partition_exits_one_and_names_it(tmp_path) -> None:
    root = _make_tree(tmp_path, "tests/d-fail\ntests/b\n*\n", dirs=("tests/d-fail", "tests/b"))
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 1
    assert "partition 1 " in proc.stdout and "rc=1" in proc.stdout


def test_run_nonzero_rc_with_a_passed_line_exits_one(tmp_path) -> None:
    """A partition that exits non-zero DESPITE a `passed` summary (a real
    pytest failing shape — failures reported after the summary line is
    composed, or a teardown/internal error) is red: the verdict is rc AND
    summary, never either alone."""
    root = _make_tree(
        tmp_path,
        "tests/a\ntests/d-failpass\n*\n",
        dirs=("tests/a", "tests/d-failpass"),
    )
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 1
    assert "partition 2 " in proc.stdout and "rc=1" in proc.stdout


def test_run_partition_collecting_nothing_exits_one(tmp_path) -> None:
    """pytest rc 5 (no tests collected) is red — a vacuous pass is never green."""
    root = _make_tree(tmp_path, "tests/d-empty\ntests/b\n*\n", dirs=("tests/d-empty", "tests/b"))
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 1
    assert "rc=5" in proc.stdout


def test_run_zero_rc_without_a_passed_line_exits_one(tmp_path) -> None:
    """A substituted command that exits 0 but runs nothing is still red."""
    root = _make_tree(
        tmp_path,
        "tests/d-nosummary\ntests/b\n*\n",
        dirs=("tests/d-nosummary", "tests/b"),
    )
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 1
    assert "no `passed` summary line" in proc.stdout


def test_missing_rc_file_fails(tmp_path) -> None:
    """A partition whose rc file vanished between write and judge is red."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "p1.log").write_text("===== 1 passed in 0.01s =====\n", encoding="utf-8")
    metas = [{"k": 1, "label": "tests/a", "log_name": "p1.log", "rc_name": "p1.rc"}]
    ok, results = PP._evaluate(run_dir, metas)
    assert not ok
    assert "missing or unparsable rc" in results[0]["problems"][0]


def test_run_refuses_an_invalid_table_and_starts_nothing(tmp_path) -> None:
    root = _make_tree(tmp_path, "tests/a\n")  # no `*` line
    proc = _run(root, tmp_path, _fake_pytest(tmp_path))
    assert proc.returncode == 2
    assert (tmp_path / "runner-temp").iterdir() is not None
    leftovers = list((tmp_path / "runner-temp").glob("pytest-par-*"))
    assert leftovers == [], "check failure must exit before anything launches"


# --- AC 2: check's exit-2 matrix --------------------------------------------


@pytest.mark.parametrize(
    ("partitions", "dirs", "needle"),
    [
        ("tests/a tests/a\n*\n", ("tests/a",), "same directory"),
        ("tests tests/a\n*\n", ("tests/a",), "must not overlap"),
        ("tests/missing\n*\n", (), "not an existing directory"),
        ("scripts\n*\n", ("scripts",), "outside every testpaths"),
        ("tests/a\n", ("tests/a",), "exactly one `*`"),
        ("tests/a\n*\n*\n", ("tests/a",), "exactly one `*`"),
        ("tests/a *\n", ("tests/a",), "its line's only token"),
    ],
)
def test_check_rejects_bad_tables(tmp_path, partitions, dirs, needle) -> None:
    root = _make_tree(tmp_path, partitions, dirs=dirs)
    proc = _check(root, tmp_path)
    assert proc.returncode == 2
    assert needle in proc.stderr, proc.stderr


def test_makefile_reaches_test_par_and_ci_yml_uses_it() -> None:
    """The wiring half of D1: `make test-par` exists, `ci-local` runs it, and
    the `python` job's Test step is `make test-par` with its env block."""
    text = (REPO_ROOT / "Makefile").read_text()
    assert "\ntest-par:" in text
    assert "scripts/ci/pytest_partitions.py run" in text
    ci_local = text.split("ci-local:", 1)[1].split("\n\n", 1)[0]
    assert "$(MAKE) test-par" in ci_local
    assert "$(MAKE) test\n" not in ci_local.replace("$(MAKE) test-par", "")
    import yaml

    job = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())["jobs"][
        "python"
    ]
    step = next(s for s in job["steps"] if s.get("run") == "make test-par")
    env = step.get("env") or {}
    assert env.get("SIG_REQUIRE_DB_TESTS") == "1"
    assert env.get("TESTCONTAINERS_RYUK_DISABLED") == "true"
    assert "SIG_GCP_PROJECT" in env
    assert (
        "PYTEST_PARTITIONS_CMD" not in text
        and "PYTEST_PARTITIONS_CMD"
        not in (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    )


def test_committed_table_keeps_bare_conftest_importers_isolated() -> None:
    """tests/db and tests/e2e re-import helpers via ``sys.modules['conftest']``,
    so a second conftest dir on their partition line shadows it (the measured
    D1 constraint — the api conftest produced 27 db collection errors)."""
    table = REPO_ROOT / "scripts" / "ci" / "pytest_partitions.txt"
    lines = [
        line.split()
        for line in table.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    conftest_dirs = {p.parent.as_posix() for p in REPO_ROOT.glob("tests/*/conftest.py")}
    bare_importers = {"tests/db", "tests/e2e"}
    for tokens in lines:
        for token in tokens:
            if token in bare_importers:
                shared = set(tokens) - {token}
                assert not shared & conftest_dirs, (
                    f"{token} shares a partition line with conftest dirs {shared & conftest_dirs}"
                )
