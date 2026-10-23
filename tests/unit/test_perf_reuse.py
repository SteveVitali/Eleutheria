# SPDX-License-Identifier: Apache-2.0
"""P35.41a (D2): unit tests for `scripts/ci/perf_reuse.py`.

Every test is hermetic: `fingerprint`/`record`/`_lint_hits` run against a
throwaway `git init` repo in `tmp_path`; `decide` runs with a fully seeded
environment (a real record file at `$CI_RECORD`) and every helper seam
monkeypatched, so each fail-closed branch is proven to answer `run`. The
real-repo `cmd_lint` test doubles as a wiring check that the committed
allow-list covers today's audited hits.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "perf_reuse", REPO_ROOT / "scripts" / "ci" / "perf_reuse.py"
)
perf_reuse = importlib.util.module_from_spec(SPEC)
sys.modules["perf_reuse"] = perf_reuse
SPEC.loader.exec_module(perf_reuse)

FP = "a" * 64
RECORD = {
    "schema": "sig.perf-pass/1",
    "lane": "web-perf-fixtures",
    "nonrecords": FP,
    "pr": "17",
    "head": "c" * 40,
    "base": "b" * 40,
    "run": "9911",
    "attempt": "1",
    "image": "ubuntu24-20251012.1",
}


def _record_text(record: dict) -> str:
    keys = [k for k in perf_reuse.RECORD_KEYS if k in record]
    keys += [k for k in record if k not in perf_reuse.RECORD_KEYS]
    return "".join(f"{k}={record[k]}\n" for k in keys)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A two-branch repo: `docs/` records tree + `web/` site, merged head."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "docs/tickets").mkdir(parents=True)
    (repo / "docs/build/tools").mkdir(parents=True)
    (repo / "docs/adr").mkdir(parents=True)
    (repo / "web").mkdir()
    (repo / "docs/tickets/x.md").write_text("ticket\n")
    (repo / "docs/build/tools/t.sh").write_text("tool\n")
    (repo / "docs/adr/ADR-1.md").write_text("adr\n")
    (repo / "web/a.ts").write_text("export {};\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "feature")
    (repo / "web/b.ts").write_text("export {};\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo


def _merge_head(repo: Path) -> None:
    for cand in ("main", "master"):
        try:
            _git(repo, "checkout", "-q", cand)
            break
        except subprocess.CalledProcessError:
            continue
    _git(repo, "merge", "--no-ff", "-qm", "merge", "feature")


def _seed_env(monkeypatch: pytest.MonkeyPatch, record_path: Path, **over: str) -> None:
    env = {
        "CI_EVENT_NAME": "pull_request",
        "CI_REPOSITORY": "org/repo",
        "CI_HEAD_REPO": "org/repo",
        "CI_PR_NUMBER": "17",
        "CI_FINGERPRINT": FP,
        "CI_IMAGE": "ubuntu24-20251012.1",
        "CI_RECORD": str(record_path),
    }
    env.update(over)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def _seed_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, record: dict | None = None
) -> Path:
    """Patch every helper seam to the all-green reuse shape and write a real
    record file at `$CI_RECORD`."""
    path = tmp_path / "record"
    path.write_text(_record_text(RECORD if record is None else record))
    monkeypatch.setattr(perf_reuse, "fingerprint", lambda rev: FP)
    monkeypatch.setattr(perf_reuse, "_has_link_or_gitlink", lambda: False)
    monkeypatch.setattr(perf_reuse, "_lint_hits", lambda: [])
    monkeypatch.setattr(perf_reuse, "_allow_problems", lambda: [])
    _seed_env(monkeypatch, path)
    return path


def _decide(capsys) -> tuple[int, str]:
    rc = perf_reuse.cmd_decide()
    out = capsys.readouterr().out.strip().splitlines()
    return rc, out[-1]


# ---------------- fingerprint ----------------


def test_fingerprint_is_64_hex_and_stable(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    fp1 = perf_reuse.fingerprint("HEAD")
    assert len(fp1) == 64 and all(c in "0123456789abcdef" for c in fp1)
    assert perf_reuse.fingerprint("HEAD") == fp1


def test_fingerprint_ignores_records_only_changes(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    for p in ("docs/tickets/y.md", "docs/adr/ADR-2.md"):
        (tmp_repo / p).write_text("more records\n")
        _git(tmp_repo, "add", "-A")
        _git(tmp_repo, "commit", "-qm", "records")
    assert perf_reuse.fingerprint("HEAD") == before


def test_fingerprint_counts_docs_build_tools(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    (tmp_repo / "docs/build/tools/new.sh").write_text("tool2\n")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "tools")
    # docs/build/tools is CI code, not records => the fingerprint MUST change
    assert perf_reuse.fingerprint("HEAD") != before


def test_fingerprint_changes_on_non_records_change(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    (tmp_repo / "web/a.ts").write_text("export const x = 1;\n")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "code")
    assert perf_reuse.fingerprint("HEAD") != before


def test_fingerprint_changes_on_mode_only_change(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    target = tmp_repo / "web/a.ts"
    target.chmod(0o755)
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "mode")
    assert perf_reuse.fingerprint("HEAD") != before


def test_fingerprint_changes_on_add_and_remove(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    (tmp_repo / "web/new.ts").write_text("export {};\n")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "add")
    assert perf_reuse.fingerprint("HEAD") != before
    _git(tmp_repo, "rm", "-q", "web/new.ts")
    _git(tmp_repo, "commit", "-qm", "remove")
    assert perf_reuse.fingerprint("HEAD") == before


def test_fingerprint_changes_on_symlink(tmp_repo, monkeypatch):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    before = perf_reuse.fingerprint("HEAD")
    (tmp_repo / "web/link.ts").symlink_to("a.ts")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "link")
    assert perf_reuse.fingerprint("HEAD") != before
    assert perf_reuse._has_link_or_gitlink()


# ---------------- lint ----------------


def test_lint_drops_docs_build_tools_hits(tmp_repo, monkeypatch):
    (tmp_repo / "web/x.ts").write_text(
        'const a = "docs/build/tools/run_x.sh";\nconst b = "docs/tickets/FOO.md";\n'
    )
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "hits")
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    hits = perf_reuse._lint_hits()
    assert hits == [
        ("web/x.ts", 'const b = "docs/tickets/FOO.md";'),
    ]


def test_cmd_lint_fails_on_unaudited_hit(tmp_repo, monkeypatch, capsys):
    (tmp_repo / "web/x.ts").write_text('const b = "docs/build/reports/r.md";\n')
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-qm", "hit")
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    assert perf_reuse.cmd_lint() == 2
    assert "unaudited" in capsys.readouterr().err


def test_cmd_lint_real_repo_allow_list_covers_hits():
    assert perf_reuse.cmd_lint() == 0


def test_allow_check_real_repo_clean():
    assert perf_reuse.main(["allow-check"]) == 0


def test_allow_check_rejects_bad_rows(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "scripts/ci"
    bad.mkdir(parents=True)
    (bad / "perf_reuse_allow.txt").write_text(
        "web/a.ts\tfine row\nnot-a-tabbed-row\nsrc/outside.ts\toutside web\nweb/b.ts\t\n"
    )
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_path)
    assert perf_reuse.main(["allow-check"]) == 2
    err = capsys.readouterr().err
    assert "expected exactly one tab" in err
    assert "web/-rooted" in err


# ---------------- record ----------------


def _record_env(monkeypatch: pytest.MonkeyPatch, dest: Path, **over: str) -> None:
    env = {
        "CI_RECORD_OUT": str(dest),
        "CI_PR_NUMBER": "17",
        "CI_IMAGE": "ubuntu24-20251012.1",
        "GITHUB_RUN_ID": "9911",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    env.update(over)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_record_writes_nine_keys_on_merge_head(tmp_repo, monkeypatch, tmp_path):
    _merge_head(tmp_repo)
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    dest = tmp_path / "out" / "record"
    _record_env(monkeypatch, dest)
    assert perf_reuse.cmd_record() == 0
    record, why = perf_reuse._read_record(str(dest))
    assert record is not None, why
    parents = _git(tmp_repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert record["base"] == parents[1] and record["head"] == parents[2]
    assert record["nonrecords"] == perf_reuse.fingerprint("HEAD")
    assert record["pr"] == "17" and record["run"] == "9911"
    assert record["schema"] == "sig.perf-pass/1"


def test_record_refuses_single_parent_head(tmp_repo, monkeypatch, tmp_path):
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)  # HEAD not a merge
    dest = tmp_path / "record"
    _record_env(monkeypatch, dest)
    assert perf_reuse.cmd_record() == 1
    assert not dest.exists()


@pytest.mark.parametrize("bad_image", ["", "not a label", "-", "-1.0", "ubuntu24-"])
def test_record_refuses_invalid_image(tmp_repo, monkeypatch, tmp_path, bad_image):
    _merge_head(tmp_repo)
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    dest = tmp_path / "record"
    _record_env(monkeypatch, dest, CI_IMAGE=bad_image)
    assert perf_reuse.cmd_record() == 1
    assert not dest.exists()


def test_record_refuses_missing_env(tmp_repo, monkeypatch, tmp_path):
    _merge_head(tmp_repo)
    monkeypatch.setattr(perf_reuse, "_root", lambda: tmp_repo)
    dest = tmp_path / "record"
    _record_env(monkeypatch, dest, CI_PR_NUMBER="")
    assert perf_reuse.cmd_record() == 1
    assert not dest.exists()


# ---------------- decide: every fail-closed branch ----------------


def test_decide_reuse_when_everything_matches(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "reuse"


def test_decide_reuse_notice_names_run_and_head(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    perf_reuse.cmd_decide()
    out = capsys.readouterr().out
    assert "::notice title=ci-perf-reuse::run 9911 head " in out
    assert RECORD["head"][:7] in out


@pytest.mark.parametrize(
    "env_over",
    [
        {"CI_EVENT_NAME": "push"},
        {"CI_EVENT_NAME": "workflow_dispatch"},
        {"CI_EVENT_NAME": ""},
        {"CI_HEAD_REPO": "fork/repo"},
        {"CI_HEAD_REPO": ""},
        {"CI_REPOSITORY": ""},
        {"CI_FINGERPRINT": "xyz"},
        {"CI_FINGERPRINT": ""},
        {"CI_PR_NUMBER": "18"},  # record.pr != env pr
        {"CI_PR_NUMBER": ""},
        {"CI_IMAGE": "ubuntu22-1.0"},  # image changed
        {"CI_IMAGE": ""},
        {"CI_IMAGE": "ubuntu-24"},  # differs from the recorded image
    ],
)
def test_decide_env_guards_fail_closed(monkeypatch, capsys, tmp_path, env_over):
    record_path = _seed_clean(monkeypatch, tmp_path)
    for k, v in env_over.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("CI_RECORD", str(record_path))
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_fingerprint_mismatch_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setattr(perf_reuse, "fingerprint", lambda rev: "f" * 64)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_no_record_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setenv("CI_RECORD", str(tmp_path / "absent"))
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_unset_record_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.delenv("CI_RECORD", raising=False)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("schema"),  # missing key
        lambda r: r.update(extra="x"),  # extra key
        lambda r: r.update(schema="other/9"),
        lambda r: r.update(lane="other-lane"),
        lambda r: r.update(base="not-hex"),
        lambda r: r.update(attempt="abc"),
        lambda r: r.update(image=""),
        lambda r: r.update(nonrecords="z" * 64),
        lambda r: r.update(nonrecords="e" * 64),  # valid but different fp
    ],
)
def test_decide_bad_records_run(monkeypatch, capsys, tmp_path, mutate):
    record = dict(RECORD)
    mutate(record)
    _seed_clean(monkeypatch, tmp_path, record)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


@pytest.mark.parametrize("corrupt", ["no-final-newline", "has-cr", "short-lines"])
def test_decide_malformed_record_runs(monkeypatch, capsys, tmp_path, corrupt):
    path = _seed_clean(monkeypatch, tmp_path)
    text = _record_text(RECORD)
    if corrupt == "no-final-newline":
        path.write_text(text.rstrip("\n"))
    elif corrupt == "has-cr":
        path.write_text(text.replace("\n", "\r\n"))
    else:
        path.write_text("schema=sig.perf-pass/1\n")
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_symlink_or_gitlink_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setattr(perf_reuse, "_has_link_or_gitlink", lambda: True)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_unknown_lint_hit_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setattr(
        perf_reuse, "_lint_hits", lambda: [("web/x.ts", 'import "docs/build/r.md";')]
    )
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_lint_error_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)

    def boom():
        raise RuntimeError("grep exploded")

    monkeypatch.setattr(perf_reuse, "_lint_hits", boom)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_allow_list_malformed_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setattr(perf_reuse, "_allow_problems", lambda: ["bad row"])
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_crash_runs(monkeypatch, capsys, tmp_path):
    _seed_clean(monkeypatch, tmp_path)

    def boom(rev):
        raise RuntimeError("ls-tree exploded")

    monkeypatch.setattr(perf_reuse, "fingerprint", boom)
    rc, word = _decide(capsys)
    assert rc == 0 and word == "run"


def test_decide_appends_step_summary(monkeypatch, capsys, tmp_path):
    summary = tmp_path / "summary.md"
    _seed_clean(monkeypatch, tmp_path)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    perf_reuse.cmd_decide()
    assert "reuse" in summary.read_text()
