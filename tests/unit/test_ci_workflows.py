# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""CI workflow structure gates (CI.1 / GL-CI-01, ADR-078).

These tests pin the `.github/workflows/ci.yml` + `nightly.yml` job structure:
if the composed job, the security scans, the PR doc gates, or the nightly
reporting steps are removed or gutted, a test here fails — the CI hardening
cannot silently rot. (The scanners themselves are exercised in
`test_security_scanners.py`.)
"""

from __future__ import annotations

from pathlib import Path

import yaml
from support import REPO_ROOT

CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
NIGHTLY_YML = REPO_ROOT / ".github" / "workflows" / "nightly.yml"


def _doc(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _runs(job: dict) -> list[str]:
    """Every `run:` body in a job's steps."""
    return [s.get("run", "") or "" for s in job.get("steps", [])]


def _uses(job: dict) -> list[str]:
    return [s.get("uses", "") or "" for s in job.get("steps", [])]


def _step_env(job: dict, needle: str) -> dict:
    """The env block of the step whose `run:` contains `needle`."""
    for s in job.get("steps", []):
        if needle in (s.get("run") or ""):
            return s.get("env") or {}
    return {}


# --- the composed job: tests/e2e FOR REAL, with Node + web deps --------------


def test_ci_composed_job_exists_and_runs_e2e() -> None:
    doc = _doc(CI_YML)
    job = doc["jobs"].get("composed")
    assert job is not None, "ci.yml must carry the `composed` job (GL-CI-01)"
    runs = _runs(job)
    assert any("pytest tests/e2e" in r for r in runs), "the composed job must run tests/e2e"


def test_ci_composed_job_fails_loudly_without_docker() -> None:
    """SIG_REQUIRE_DB_TESTS=1 on the pytest step → a missing daemon fails, never skips."""
    job = _doc(CI_YML)["jobs"]["composed"]
    env = _step_env(job, "pytest tests/e2e")
    assert env.get("SIG_REQUIRE_DB_TESTS") == "1", (
        "the composed e2e step must set SIG_REQUIRE_DB_TESTS=1"
    )


def test_ci_composed_job_installs_node_and_web_deps() -> None:
    """S8's web-build fixtures only run when npm + web/node_modules exist."""
    job = _doc(CI_YML)["jobs"]["composed"]
    assert any("setup-node" in u for u in _uses(job)), "composed job needs setup-node"
    runs = _runs(job)
    assert any("npm" in r and "ci" in r and "web" in r for r in runs), (
        "composed job must install web/node_modules (npm --prefix web ci)"
    )


def test_ci_composed_job_installs_the_workspace() -> None:
    job = _doc(CI_YML)["jobs"]["composed"]
    assert any("make sync" in r for r in _runs(job))


# --- the doc gates on PRs AND pushes to main (P34.1 / CF-01, ADR-151) ---------


def test_ci_docs_job_runs_on_pull_requests_and_pushes_to_main() -> None:
    """The docs gate judges PRs and landed commits alike — a change cannot dodge
    the guards by merging (P34.1 rewrote the seed's PR-only pin, ADR-151)."""
    doc = _doc(CI_YML)
    triggers = doc.get("on") or doc.get(True)
    assert "pull_request" in triggers, "ci.yml must still trigger on pull requests"
    assert triggers.get("push", {}).get("branches") == ["main"]
    job = doc["jobs"].get("docs")
    assert job is not None
    assert not job.get("if"), (
        "the docs job must not carry a pull_request-only `if` — it runs on both "
        "pull_request and push-to-main events"
    )


def test_ci_docs_job_judges_the_push_head_on_main() -> None:
    """The push-side twin (CF-01): on `push`, the history guard takes the landed
    head's first-parent diff; on `pull_request`, the PR base...head range."""
    job = _doc(CI_YML)["jobs"]["docs"]
    steps = job["steps"]
    push_step = [s for s in steps if "--first-parent" in (s.get("run") or "")]
    assert len(push_step) == 1, "the docs job needs one --first-parent push step"
    assert "github.event_name == 'push'" in push_step[0]["if"]
    assert "check-build-memory.sh" in push_step[0]["run"]
    pr_step = _docs_step("check-build-memory.sh . --range")
    assert "github.event_name == 'pull_request'" in pr_step["if"]
    trailer = _docs_step("check_trailers.py")
    assert "--range" in trailer["run"]
    assert "github.event.before" in trailer["run"], (
        "on a push the trailer check judges the push's commits (event.before...sha)"
    )


def test_ci_docs_job_enforces_docs_check_and_build_memory() -> None:
    """Both `make docs-check` AND the explicit check-build-memory.sh step."""
    job = _doc(CI_YML)["jobs"]["docs"]
    runs = _runs(job)
    assert any("make docs-check" in r for r in runs), "docs job must run make docs-check"
    assert any("check-build-memory.sh" in r for r in runs), (
        "docs job must run check-build-memory.sh explicitly (GL-CI-01)"
    )


# --- the security job: secret + licence scans on every PR --------------------


def test_ci_security_job_runs_secret_and_license_scans() -> None:
    doc = _doc(CI_YML)
    job = doc["jobs"].get("security")
    assert job is not None, "ci.yml must carry the `security` job (GL-CI-01)"
    runs = _runs(job)
    assert any("scan-secrets" in r or "secret_scan" in r for r in runs)
    assert any("scan-licenses" in r or "license_scan" in r for r in runs)


# --- nightly: scheduled composed run + all three scans + a report -------------


def test_nightly_is_scheduled_and_manually_dispatchable() -> None:
    doc = _doc(NIGHTLY_YML)
    # PyYAML parses the bare `on:` key as boolean True (YAML 1.1).
    triggers = doc.get("on") or doc.get(True)
    assert triggers.get("schedule"), "nightly.yml must carry a cron schedule"
    assert any(s.get("cron") for s in triggers["schedule"])
    assert "workflow_dispatch" in triggers


def test_nightly_runs_composed_e2e_and_all_three_scans() -> None:
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    runs = _runs(job)
    assert any("pytest tests/e2e" in r for r in runs), "nightly must run tests/e2e"
    assert any("secret_scan" in r or "scan-secrets" in r for r in runs)
    assert any("license_scan" in r or "scan-licenses" in r for r in runs)
    assert any("dep_audit" in r or "audit-deps" in r for r in runs)


def test_nightly_e2e_fails_loudly_without_docker() -> None:
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    env = _step_env(job, "pytest tests/e2e")
    assert env.get("SIG_REQUIRE_DB_TESTS") == "1"


def test_nightly_reports_an_artifact_and_gates_on_failures() -> None:
    """The report step is the gate (exits non-zero on a failed stage); the
    artifact upload runs `if: always()` so a red nightly still carries evidence."""
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    steps = job.get("steps", [])
    report = [s for s in steps if "nightly_report" in (s.get("run") or "")]
    assert report, "nightly must compose nightly-report.md via scripts/ci/nightly_report.py"
    uploads = [s for s in steps if "upload-artifact" in (s.get("uses") or "")]
    assert uploads, "nightly must upload the report artifact"
    assert any("always()" in (s.get("if") or "") for s in uploads), (
        "the report artifact must upload even when a stage failed"
    )
    paths = uploads[0].get("with", {}).get("path", "")
    assert "nightly-report.md" in paths


# --- workflows themselves carry no credential literals ------------------------


def test_workflow_files_have_no_credential_literals() -> None:
    """Workflows reference secrets only via ${{ secrets.* }} — the scanner itself
    asserts it (also covered by the tree-wide secret scan)."""
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/ci/secret_scan.py"),
            str(REPO_ROOT / ".github" / "workflows"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


# --- Round 11 seed (SEED-02b): runner pin, history guards, trailer check -----

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
MAKEFILE = REPO_ROOT / "Makefile"


def test_every_job_of_every_workflow_pins_ubuntu_24_04() -> None:
    """S6R-27 / FEA-16: `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19, so the
    runner never floats — the pin does not hinge on P34.1's date."""
    jobs = [(p.name, n, j) for p in WORKFLOWS for n, j in _doc(p)["jobs"].items()]
    assert len(jobs) >= 9
    floating = [(wf, n, j.get("runs-on")) for wf, n, j in jobs]
    assert [f for f in floating if f[2] != "ubuntu-24.04"] == []


def _docs_step(needle: str) -> dict:
    steps = [s for s in _doc(CI_YML)["jobs"]["docs"]["steps"] if needle in (s.get("run") or "")]
    assert len(steps) == 1, f"the docs job must run `{needle}` in exactly one step"
    return steps[0]


def test_ci_docs_job_runs_the_history_guard_over_the_pr_range() -> None:
    """BM-HIST-01: the validator's history mode (→ memory_guard.py) judges base...head of
    the PR, with full history; its non-zero exits are never masked."""
    job = _doc(CI_YML)["jobs"]["docs"]
    assert job["steps"][0]["with"]["fetch-depth"] == 0
    step = _docs_step("check-build-memory.sh . --range")
    assert '"$BASE_SHA...$HEAD_SHA"' in step["run"]
    assert step["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    assert all("|| true" not in (s.get("run") or "") for s in job["steps"])
    assert all(not s.get("continue-on-error") for s in job["steps"])
    # reported even when an earlier docs step is red; the job still fails on any red step
    assert step["if"] == "${{ github.event_name == 'pull_request' && !cancelled() }}"


def test_ci_docs_job_runs_the_om01_trailer_check_on_every_event() -> None:
    """OM-01 judges every authored commit: the PR range on pull_request, the push's
    commits (event.before...sha, landed-head fallback) on push to main."""
    step = _docs_step("check_trailers.py")
    assert "check_trailers.py --range" in step["run"]
    assert step["if"] == "${{ !cancelled() }}" and not step.get("continue-on-error")
    assert "github.event.pull_request.base.sha" in step["run"]
    assert "github.event.before" in step["run"]
    assert "git rev-parse HEAD^" in step["run"], (
        "a push with an absent/zero `before` falls back to the landed head"
    )
    assert (REPO_ROOT / "docs/build/tools/check_trailers.py").is_file()


def test_make_docs_check_runs_the_round11_checkers() -> None:
    """B4 G7 item 1: the memory guard, spec-source and coverage-matrix checkers are part of
    `make docs-check` (which the docs job runs)."""
    text = MAKEFILE.read_text()
    line = next(ln for ln in text.splitlines() if ln.startswith("docs-check:"))
    for target in ("docs-check-memory", "docs-check-spec", "docs-check-matrix"):
        assert target in line.split(":", 1)[1].split(), target
        assert f"\n{target}:" in text, target
    assert "memory_guard.py all --worktree" in text
    assert "check_spec_src.py" in text and "check_coverage_matrix.py" in text


def test_pytest_collects_the_build_memory_tool_suites() -> None:
    import tomllib

    cfg = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert "docs/build/tools" in cfg["testpaths"]
    assert (REPO_ROOT / "docs/build/tools/test_memory_guard.py").is_file()


# --- P34.1 / SIG-ENG-046 / ADR-151: the toolchain pin and CI hygiene ----------

WEB = REPO_ROOT / "web"


def _npm_range_ok(version: tuple[int, int, int], expr: str) -> bool:
    """Does `version` satisfy an npm-style engine range? Covers the comparator
    forms engine fields use: `*`, `x`, exact, `>=`, `>`, `<=`, `<`, `^`, `~`,
    partial versions (`18`, `18.1`), and `||` alternatives. An unrecognised
    comparator fails loudly (a human re-reads the range) rather than passing."""

    import re

    def parts(v: str) -> tuple[int, int, int] | None:
        m = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+][0-9A-Za-z.-]*)?", v)
        return None if not m else (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0))

    def cmp_one(v: tuple[int, int, int], tok: str) -> bool:
        tok = tok.strip()
        if tok in ("", "*", "x", "X"):
            return True
        m = re.match(r"^(>=|<=|>|<|=)?\s*v?([0-9xX.*]+)$", tok)
        assert m, f"unparsed comparator {tok!r}"
        op, num = m.group(1) or "=", m.group(2)
        if "x" in num.lower() or "*" in num or num.count(".") < 2:
            base = num.replace("x", "0").replace("X", "0").replace("*", "0")
            t = parts(base)
            assert t, f"unparsed comparator {tok!r}"
            if op == "=":
                dots = len(re.findall(r"\.", num))
                return v[: dots + 1] == t[: dots + 1]
            v3, t3 = v, t
            return {">=": v3 >= t3, "<=": v3 <= t3, ">": v3 > t3, "<": v3 < t3}[op]
        t = parts(num)
        assert t, f"unparsed comparator {tok!r}"
        if op == "=":
            return v == t
        if op in (">=", "<=", ">", "<"):
            return {">=": v >= t, "<=": v <= t, ">": v > t, "<": v < t}[op]
        raise AssertionError(f"unparsed comparator {tok!r}")

    def expanded(v: tuple[int, int, int], tok: str) -> bool:
        tok = tok.strip()
        if tok.startswith(("^", "~")):
            t = parts(tok[1:])
            assert t, f"unparsed comparator {tok!r}"
            if tok[0] == "^":
                upper = (0, t[1] + 1, 0) if t[0] == 0 else (t[0] + 1, 0, 0)
            else:
                upper = (t[0], t[1] + 1, 0)
            return v >= t and v < upper
        return cmp_one(v, tok)

    for alt in expr.split("||"):
        toks = [t for t in re.split(r"\s+", alt.strip()) if t and t != "-"]
        if toks and all(expanded(version, t) for t in toks):
            return True
    return False


def test_node_toolchain_pin_files_agree() -> None:
    """The one Node/npm pin: `.nvmrc` exact, `engines` ranges, `packageManager`
    exact, `engine-strict` — all mutually consistent (SIG-ENG-046)."""
    import json
    import re

    nvmrc = (WEB / ".nvmrc").read_text().strip()
    assert re.fullmatch(r"v?\d+\.\d+\.\d+", nvmrc), ".nvmrc must pin an exact version"
    pkg = json.loads((WEB / "package.json").read_text())
    assert pkg["engines"]["node"] == ">=24 <25"
    assert pkg["engines"]["npm"] == ">=11 <12"
    pm = pkg["packageManager"]
    m = re.fullmatch(r"npm@(\d+)\.(\d+)\.(\d+)", pm)
    assert m, "packageManager must pin an exact npm"
    node_v = tuple(int(x) for x in nvmrc.lstrip("v").split("."))
    assert _npm_range_ok(node_v, pkg["engines"]["node"])
    assert _npm_range_ok(tuple(int(x) for x in m.groups()), pkg["engines"]["npm"])
    assert int(nvmrc.lstrip("v").split(".")[0]) == 24, "the pin is a Node 24 LTS"
    assert "engine-strict" in (WEB / ".npmrc").read_text(), (
        ".npmrc must set engine-strict=true so a drifting local toolchain fails"
    )


def test_every_setup_node_uses_nvmrc_and_node_jobs_print_the_pin() -> None:
    """Every `setup-node` step resolves the lockfile-adjacent pin file, and every
    node-using job installs the `packageManager` npm and logs both versions."""
    for wf in WORKFLOWS:
        doc = _doc(wf)
        for job_name, job in doc["jobs"].items():
            steps = job.get("steps", [])
            setup_node = [s for s in steps if "actions/setup-node" in (s.get("uses") or "")]
            for s in setup_node:
                w = s.get("with") or {}
                assert w.get("node-version-file") == "web/.nvmrc", (
                    f"{wf.name}:{job_name} must resolve node from web/.nvmrc"
                )
                assert "node-version" not in w, f"{wf.name}:{job_name} must not float a major"
            if setup_node or any("npm " in (s.get("run") or "") for s in steps):
                runs = [s.get("run") or "" for s in steps]
                assert any("npm install -g" in r and "packageManager" in r for r in runs), (
                    f"{wf.name}:{job_name} must install the packageManager-pinned npm"
                )
                assert any("node -v" in r for r in runs) and any("npm -v" in r for r in runs), (
                    f"{wf.name}:{job_name} must print node -v and npm -v"
                )


def test_lockfile_drift_gate_and_npm_ci_only() -> None:
    """A lockfile the pinned npm would write differently fails at PR time, and
    dependencies install via `npm ci` only — never a bare `npm install`."""
    doc = _doc(CI_YML)
    for name in ("composed", "web"):
        runs = [s.get("run") or "" for s in doc["jobs"][name]["steps"]]
        assert any("--package-lock-only" in r and "--ignore-scripts" in r for r in runs), (
            f"{name} must run npm install --package-lock-only --ignore-scripts"
        )
        assert any("git diff --exit-code" in r and "package-lock.json" in r for r in runs), (
            f"{name} must fail when the regeneration diffs the lockfile"
        )
    import re

    for wf in WORKFLOWS:
        doc = _doc(wf)
        for job_name, job in doc["jobs"].items():
            for r in [s.get("run") or "" for s in job.get("steps", [])]:
                for hit in re.finditer(r"npm[ \t]+([a-z-]+)", r):
                    cmd = hit.group(1)
                    assert cmd != "install" or "--package-lock-only" in r or "-g" in r, (
                        f"{wf.name}:{job_name}: dependency installs are `npm ci`, "
                        f"never bare `npm install` (found in {r!r})"
                    )


def test_lockfile_gate_detects_drift(tmp_path) -> None:
    """The gate is real: a byte-drifted lockfile is a diff `git diff
    --exit-code` fails on. (The pinned-toolchain regen itself is byte-stable —
    verified in the P34.1 run ledger.)"""
    import json
    import subprocess

    lock = json.loads((WEB / "package-lock.json").read_text())
    drifted = tmp_path / "package-lock.json"
    lock["packages"]["node_modules/left-pad"] = {"version": "1.3.0", "dev": True}
    drifted.write_text(json.dumps(lock, indent=2) + "\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "package-lock.json").write_text(json.dumps(lock, indent=2))
    subprocess.run(["git", "add", "package-lock.json"], cwd=repo, check=True)
    (repo / "package-lock.json").write_text(drifted.read_text())
    proc = subprocess.run(
        ["git", "diff", "--exit-code", "--", "package-lock.json"], cwd=repo, capture_output=True
    )
    assert proc.returncode != 0, "a drifted lockfile must fail the drift gate"


def test_uv_version_pinned_and_matches_setup_uv() -> None:
    """`[tool.uv] required-version` is the same version every setup-uv installs."""
    import re
    import tomllib

    py = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    req = py["tool"]["uv"]["required-version"]
    m = re.fullmatch(r"==(\d+\.\d+\.\d+)", req)
    assert m, "required-version must be an exact `==` pin"
    for wf in WORKFLOWS:
        for job_name, job in _doc(wf)["jobs"].items():
            for s in job.get("steps", []):
                if "astral-sh/setup-uv" in (s.get("uses") or ""):
                    assert (s.get("with") or {}).get("version") == m.group(1), (
                        f"{wf.name}:{job_name}: setup-uv must install {m.group(1)}"
                    )


def test_action_majors_target_node24() -> None:
    """Every action is a major whose runtime is Node 24 (manifests checked at
    P34.1): checkout ≥7, setup-node ≥7, upload-artifact ≥7, setup-uv ≥10."""
    floor = {
        "actions/checkout": 7,
        "actions/setup-node": 7,
        "actions/upload-artifact": 7,
        "astral-sh/setup-uv": 10,
    }
    for wf in WORKFLOWS:
        for job_name, job in _doc(wf)["jobs"].items():
            for s in job.get("steps", []):
                uses = s.get("uses") or ""
                if "@" not in uses or uses.startswith("./"):
                    continue
                repo, _, ref = uses.partition("@")
                if repo in floor:
                    assert int(ref.lstrip("v").split(".")[0]) >= floor[repo], (
                        f"{wf.name}:{job_name}: {uses} is below the Node-24 major floor"
                    )


def test_every_workflow_defaults_to_bash_with_pipefail() -> None:
    """Workflow-level `defaults: run: shell: bash` = `bash --noprofile --norc
    -eo pipefail` on the runner — a failure on the left of a pipe is a failure."""
    assert len(WORKFLOWS) == 5
    for wf in WORKFLOWS:
        shell = (_doc(wf).get("defaults") or {}).get("run", {}).get("shell")
        assert shell == "bash", f"{wf.name} must default `run` to `shell: bash`"


def test_pipefail_mutation_false_pipe_tee_fails(tmp_path) -> None:
    """The `shell: bash` semantics: `false | tee x` fails the step under
    `-eo pipefail` and would have passed under the old `bash -e` default."""
    import subprocess

    step = tmp_path / "step.sh"
    step.write_text("false | tee out.txt\n")
    pinned = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(step)],
        capture_output=True,
        cwd=tmp_path,
    )
    assert pinned.returncode != 0, "pipefail must turn `false | tee` into a step failure"
    old = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", str(step)], capture_output=True, cwd=tmp_path
    )
    assert old.returncode == 0, "documents the pre-pin behaviour the policy removed"


def test_ci_cancel_in_progress_is_pr_only() -> None:
    """SIG-ENG-046: superseded PR runs may cancel; a run for a push to `main`
    never does."""
    doc = _doc(CI_YML)
    expr = doc["concurrency"]["cancel-in-progress"]
    assert "pull_request" in str(expr) and "github.event_name" in str(expr), (
        "cancel-in-progress must be true only for pull_request events"
    )
    assert str(expr).strip() != "true", "push-to-main runs must never be cancelled"


def test_scheduled_workflows_complete_a_started_run() -> None:
    """A scheduled/dispatch sweep that has started is never cancelled — a
    cancelled sweep leaves an unmeasured gap (ADR-151)."""
    for name in ("nightly.yml", "keepalive.yml", "observability.yml", "reingest.yml"):
        doc = _doc(REPO_ROOT / ".github" / "workflows" / name)
        assert doc["concurrency"]["cancel-in-progress"] is False, (
            f"{name} must set cancel-in-progress: false"
        )


def test_every_dev_dependency_engine_admits_the_pin() -> None:
    """G3e: the lockfile's recorded `engines` for every devDependency admit the
    pinned node/npm — an engine that excludes the pin fails here, not at npm."""
    import json

    pkg = json.loads((WEB / "package.json").read_text())
    lock = json.loads((WEB / "package-lock.json").read_text())
    node_v = tuple(int(x) for x in (WEB / ".nvmrc").read_text().strip().lstrip("v").split("."))
    npm_v = tuple(int(x) for x in pkg["packageManager"].split("@")[1].split("."))
    for dep in pkg.get("devDependencies", {}):
        entry = lock["packages"].get(f"node_modules/{dep}")
        assert entry, f"devDependency {dep} missing from the lockfile"
        eng = entry.get("engines") or {}
        if "node" in eng:
            assert _npm_range_ok(node_v, eng["node"]), (
                f"{dep} engines.node {eng['node']!r} excludes the pinned Node {node_v}"
            )
        if "npm" in eng:
            assert _npm_range_ok(npm_v, eng["npm"]), (
                f"{dep} engines.npm {eng['npm']!r} excludes the pinned npm {npm_v}"
            )
        lc = lock["packages"]["node_modules/license-checker-rseidelsohn"]
        assert lc["engines"]["node"] and _npm_range_ok(node_v, lc["engines"]["node"]), (
            "license-checker-rseidelsohn must admit the pinned Node (H2 §3.5 item 1)"
        )


def test_make_ci_local_covers_every_ci_run_command() -> None:
    """Parity (P34.1): every `run:` command in ci.yml's five jobs is reachable
    from `make ci-local` — either verbatim as a recipe line (env prefixes and
    the web job's working-directory normalized) or as a named target it reaches.
    A closed set of runner-provisioning/log lines is exempt, each justified."""
    import re

    text = MAKEFILE.read_text()
    recipes: dict[str, list[str]] = {}
    deps: dict[str, list[str]] = {}
    cur = None
    for raw in text.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if raw.startswith("\t"):
            if cur:
                recipes.setdefault(cur, []).append(raw[1:])
        elif m and not raw.startswith(("ifeq", "else", "endif", " ")):
            cur = m.group(1)
            deps[cur] = [d for d in m.group(2).split() if re.fullmatch(r"[A-Za-z0-9_-]+", d)]
            recipes.setdefault(cur, [])
        elif raw.strip():
            cur = None

    closure: list[str] = []
    seen: set[str] = set()

    def reach(target: str) -> None:
        if target in seen or target not in recipes:
            return
        seen.add(target)
        closure.extend(recipes[target])
        for d in deps.get(target, []):
            reach(d)
        for line in recipes[target]:
            for mm in re.finditer(r"\$\(MAKE\)\s+([^;|&]+)|\bmake\s+([A-Za-z0-9_-]+)", line):
                args = mm.group(1) or mm.group(2) or ""
                for t in args.split():
                    if re.fullmatch(r"[A-Za-z0-9_-]+", t):
                        reach(t)

    reach("ci-local")

    def norm(line: str, web_cwd: bool) -> str:
        line = line.strip().lstrip("@")
        line = re.sub(r"^((?:[A-Z_]+=\S+\s+)+)", "", line)  # env assignments
        line = re.sub(r"\s+", " ", line).strip()
        if web_cwd:
            line = re.sub(r"\bnpm\b(?! --prefix)", "npm --prefix web", line)
            line = line.replace("-- package-lock.json", "-- web/package-lock.json")
        return line

    def strip_envs(line: str) -> str:
        return re.sub(r"^((?:[A-Z_]+=\S+\s+)+)", "", line.strip().lstrip("@"))

    env_steps = (
        "uv python install",  # `make sync` resolves the pinned interpreter
        "npm install -g",  # the runner provisions the pinned npm; locally
        # engine-strict + `engines.npm` assert it
        "node -v",
        "npm -v",
        "python3 --version",  # version log lines, not gate commands
        "npx playwright install",  # browser/OS provisioning; locally the developer's
        "git rev-parse HEAD^",  # push-range fallback inside a shell block
        # In a clean CI checkout `git diff --exit-code` IS the drift predicate
        # (worktree==index); locally the tree is dirty by construction, so
        # ci-local asserts the same predicate as file-hash stability across the
        # regen — green even over an intentional uncommitted regeneration.
        "git diff --exit-code",
    )
    shell_noise = re.compile(r"^(if\b|then\b|else\b|elif\b|fi$|done$|do$|echo\b|[A-Za-z_]+=|\[|\})")
    normalized_closure = {strip_envs(re.sub(r"\s+", " ", ln)) for ln in closure}

    doc = _doc(CI_YML)
    missing: list[str] = []
    for job_name, job in doc["jobs"].items():
        web_cwd = (job.get("defaults") or {}).get("run", {}).get("working-directory") == "web"
        for step in job.get("steps", []):
            run = step.get("run")
            if not run:
                continue
            for raw_line in run.splitlines():
                # the env/diagnostic whitelist matches the un-rewritten line —
                # web-cwd prefixing must not turn `npm install -g` into a miss
                plain = norm(raw_line, False)
                if not plain or shell_noise.match(plain):
                    continue
                if any(p in plain for p in env_steps):
                    continue
                line = norm(raw_line, web_cwd)
                if any(
                    t in line
                    for t in (
                        "check_trailers.py",
                        "check-build-memory.sh",
                        "verify_recorded_ci.py",
                        "npm_audit_gate.sh",
                    )
                ):
                    # Checked by name, not verbatim: range/out args legitimately
                    # differ locally — the verifier's diff base (branch base vs
                    # the PR's recorded base sha) and the gate driver's --out
                    # dir (gitignored docs/build/logs vs the workspace root).
                    tool = next(
                        t
                        for t in (
                            "check_trailers.py",
                            "check-build-memory.sh",
                            "verify_recorded_ci.py",
                            "npm_audit_gate.sh",
                        )
                        if t in line
                    )
                    if any(tool in c for c in normalized_closure):
                        continue
                    missing.append(f"{job_name}: {line!r} — no {tool} reachable from ci-local")
                    continue
                make_targets = re.findall(r"\bmake\s+([A-Za-z0-9_-]+)", line)
                if make_targets:
                    for t in make_targets:
                        if t not in seen:
                            missing.append(
                                f"{job_name}: `{line}` — `make {t}` unreachable from ci-local"
                            )
                    continue
                if not any(line in c or c == line for c in normalized_closure):
                    missing.append(f"{job_name}: `{line}` — no counterpart reachable from ci-local")
    assert missing == [], "ci.yml commands with no ci-local counterpart:\n" + "\n".join(missing)


# --- P34.2 (SIG-MEM-007, SIG-ENG-042): recorded-CI verifier, advisory gate, ---
# --- fail-closed leak check ------------------------------------------------


def test_docs_job_verifies_added_ci_lines_against_github() -> None:
    """G3b: the docs job re-verifies every `ci:` line the change adds against
    GitHub — a closeout commit that records a green which never was fails."""
    job = _doc(CI_YML)["jobs"]["docs"]
    step = _docs_step("verify_recorded_ci.py")
    assert "--diff-base" in step["run"], "the verifier judges the change's added lines"
    assert "github.event.pull_request.base.sha" in step["run"]
    assert "github.event.before" in step["run"], "pushes to main are verified too"
    assert step["env"].get("GH_TOKEN") == "${{ secrets.GITHUB_TOKEN }}", (
        "the verifier's `gh api` reads need the token — never secrets, read-only"
    )
    assert not step.get("continue-on-error") and "|| true" not in step["run"]
    perms = job.get("permissions") or {}
    assert perms.get("actions") == "read" and perms.get("checks") == "read", (
        "the docs job needs actions:read + checks:read for the run/check-runs reads"
    )


def test_security_job_runs_the_npm_advisory_gate() -> None:
    """P34.2 deliverable 6: the per-PR gate is `npm audit --omit=dev` judged by
    npm_audit_gate.py at high — driven by one script ci-local runs verbatim, so
    the preserved-status handling can never drift between the two."""
    job = _doc(CI_YML)["jobs"]["security"]
    runs = _runs(job)
    gate = [r for r in runs if "npm_audit_gate.sh" in r]
    assert len(gate) == 1, "the security job must run npm_audit_gate.sh exactly once"
    assert "--full" not in gate[0], "the per-PR gate is production-only (not --full)"
    # the driver really runs the prod audit + the gate — and preserves npm's status
    script = (REPO_ROOT / "scripts/ci/npm_audit_gate.sh").read_text()
    assert "npm --prefix web audit --omit=dev --json" in script
    assert "--level high" in script and '"$rc" -gt 1' in script
    assert "|| rc=$?" in script, "npm audit's findings exit (1) must be preserved for the gate"
    # the gate needs the pinned toolchain — setup-node in this job
    assert any("setup-node" in u for u in _uses(job))


def test_fail_closed_leak_check_is_armed_everywhere_it_runs() -> None:
    """P34.2 deliverable 7: `SIG_GCP_PROJECT` arms the leak check in EVERY job
    whose suite can run it — the dedicated security step and the python job's
    `make test` (the suite fails closed when it is unset)."""
    doc = _doc(CI_YML)
    sec = _step_env(doc["jobs"]["security"], "test_gcp_project_id_is_env_resolved")
    assert sec.get("SIG_GCP_PROJECT") == "${{ vars.SIG_GCP_PROJECT }}"
    py = _step_env(doc["jobs"]["python"], "make test")
    assert py.get("SIG_GCP_PROJECT") == "${{ vars.SIG_GCP_PROJECT }}", (
        "the full pytest suite includes the fail-closed leak check — the python "
        "job must arm it or `make test` goes red"
    )


def test_nightly_carries_the_full_audit_and_recorded_ci_stages() -> None:
    """Nightly scope (P34.2): the full-tree npm audit against the dated
    allow-list, and `verify_recorded_ci.py --all` over every Round-11 record."""
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    steps = {s.get("id"): s for s in job.get("steps", []) if s.get("id")}
    npm = steps.get("npm")
    assert npm and "npm_audit_gate.sh" in npm["run"] and "--full" in npm["run"], (
        "nightly must run the full npm audit through the allow-list gate"
    )
    script = (REPO_ROOT / "scripts/ci/npm_audit_gate.sh").read_text()
    assert "npm --prefix web audit --json" in script and "--prod-audit" in script, (
        "`--full` must run both audits and cross-check `dev-only` allow entries "
        "against the production tree"
    )
    rci = steps.get("recordedci")
    assert rci and "verify_recorded_ci.py --all" in rci["run"], (
        "nightly must verify every recorded ci: line (the --all scope)"
    )
    assert (rci.get("env") or {}).get("GH_TOKEN") == "${{ secrets.GITHUB_TOKEN }}"
    perms = doc.get("permissions") or {}
    assert perms.get("actions") == "read" and perms.get("checks") == "read", (
        "nightly's verifier needs actions:read + checks:read"
    )
    # the report is the gate — the new stages must be in it and the artifact
    report = next(s for s in job["steps"] if "nightly_report" in (s.get("run") or ""))
    assert "npm=" in report["run"] and "recordedci=" in report["run"], (
        "a stage the report cannot see passes silently — wire both outcomes in"
    )
    upload = next(s for s in job["steps"] if "upload-artifact" in (s.get("uses") or ""))
    paths = upload.get("with", {}).get("path", "")
    assert "npm-audit.txt" in paths and "recorded-ci.txt" in paths


def test_ci_local_mirrors_the_new_gates() -> None:
    """`make ci-local` is the five-job mirror (P34.1): the verifier and the
    advisory gate run locally on the same inputs."""
    text = MAKEFILE.read_text()
    ci_local = text.split("ci-local:", 1)[1].split("\n\n", 1)[0]
    assert "verify_recorded_ci.py --diff-base" in ci_local
    assert "npm_audit_gate.sh --out" in ci_local, (
        "the advisory gate runs through the same driver script as ci.yml"
    )
