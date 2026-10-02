# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.6 — the restore-drill / restore-point / logical-export shell scripts.

Offline contract (SIG-OPS-001): all three scripts are dry-run-by-default with
no ADC and no network; the window guard refuses inside the 03:00–10:00Z band
(and — for the export that loads sig-pg — inside AR-3); the drill's stop rules
refuse on a failed restore point or an unreviewed red probe; the deleteclone
path is name-checked — it can NEVER name sig-pg and refuses every name outside
the producer's stamp shape; the queued legs (export / lifecycle / relabel /
fullrestore) refuse without a verbatim --go; the lifecycle leg never overwrites
foreign rules; and the relabel leg copies seed dumps without ever deleting the
originals. `gcloud` is a PATH stub that records every invocation, so apply-mode
code paths run fully offline (test_protect_iac.py's pattern).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRILL = REPO_ROOT / "ops" / "gcp" / "restore-drill.sh"
POINT = REPO_ROOT / "ops" / "gcp" / "restore-point.sh"
EXPORT = REPO_ROOT / "ops" / "gcp" / "logical-export.sh"
FIXTURES = Path(__file__).parent / "fixtures"

INSIDE_DAILY_BAND = "2026-10-02T05:00:00Z"
INSIDE_AR3 = "2026-10-03T12:00:00Z"  # Sat 2026-10-03, dom<=7 -> the AR-3 window
OPEN_WINDOW = "2026-10-14T12:00:00Z"  # Wednesday, dom 14: outside both windows
CLONE = "sig-pg-drill-20261014t1210z"
GO = "go (verbatim in-ticket) 2026-10-03: run the queued P34.6 export legs"

_STUB_GCLOUD = r"""#!/usr/bin/env bash
# Offline gcloud stub — logs every invocation, then serves canned replies.
# Stateful on instance names: STUB_INSTANCE_STATE is a file of one name per
# line (default seeded with sig-pg); delete removes, clone/create append.
printf '%s\n' "$*" >> "${GCLOUD_STUB_LOG:-/dev/null}"
_state="${STUB_INSTANCE_STATE:-/dev/null}"
_state_names() { [ -f "$_state" ] && cat "$_state" || echo "sig-pg"; }
case "$*" in
  "auth application-default print-access-token") echo stub-token ;;
  "sql instances clone --help")
    echo 'clone an instance: --point-in-time --async' ;;
  "sql instances clone "*)
    name="$(printf '%s' "$*" | awk '{print $4}')"
    printf '%s\n' "$name" >> "$_state" 2>/dev/null || true
    echo '{"name":"op-clone-1"}' ;;
  "sql instances delete "*)
    name="$(printf '%s' "$*" | awk '{print $4}')"
    if [ -f "$_state" ]; then
      grep -v "^${name}$" "$_state" > "$_state.tmp" && mv "$_state.tmp" "$_state" || true
    fi
    echo '{}' ;;
  "sql instances create "*)
    name="$(printf '%s' "$*" | awk '{print $4}')"
    printf '%s\n' "$name" >> "$_state" 2>/dev/null || true
    echo '{"name":"op-create-1"}' ;;
  "sql instances describe"*)
    case "$*" in
      *"value(state)"*) echo "RUNNABLE" ;;
      *) cat "${STUB_SQL_DESCRIBE:-/dev/null}" 2>/dev/null || \
         echo '{"name":"sig-pg","state":"RUNNABLE"}' ;;
    esac ;;
  "sql instances list"*)
    case "$*" in
      *"value(name)"*) _state_names ;;
      *) cat "${STUB_INSTANCES_JSON:-/dev/null}" 2>/dev/null || \
         _state_names | python3 -c 'import json,sys
print(json.dumps([{"name": n, "state": "RUNNABLE"}
                  for n in sys.stdin.read().split()]))' ;;
    esac ;;
  "sql backups list"*)
    if [ -n "${STUB_BACKUPS_FILE:-}" ]; then cat "$STUB_BACKUPS_FILE";
    else
      echo '[{"id":"42","status":"SUCCESSFUL","type":"AUTOMATED",'
      echo ' "endTime":"2026-10-02T11:50:00Z"}]'
    fi ;;
  "sql backups create"*) echo '{"name":"op-backup-1"}' ;;
  "sql backups restore"*) echo '{"name":"op-restore-1"}' ;;
  "sql operations describe"*)
    printf '{"status":"DONE","operationType":"%s"}\n' "${STUB_OP_TYPE:-CLONE}" ;;
  "sql operations list"*) echo '[]' ;;
  "sql export sql"*) echo '{"name":"op-export-1"}' ;;
  "run jobs executions list --job sig-probe"*)
    if [ -n "${STUB_PROBE_FILE:-}" ]; then cat "$STUB_PROBE_FILE";
    else echo '[{"status":{"conditions":[{"type":"Completed","status":"True"}]}}]'; fi ;;
  "run jobs executions list --job sig-materialize"*)
    echo "${STUB_MATERIALIZE_JSON:-[]}" ;;
  "storage ls "*)
    case "$*" in
      *seed-2026-09-15*)
        # existence check on the relabel target: absent unless seeded
        if [ -n "${STUB_SEED_PRESENT:-}" ]; then cat "$STUB_SEED_PRESENT"; else exit 1; fi ;;
      *) cat "${STUB_LS:-/dev/null}" 2>/dev/null || true ;;
    esac ;;
  "storage buckets describe"*)
    cat "${STUB_BUCKET_DESCRIBE:-/dev/null}" 2>/dev/null || echo '{}' ;;
  "storage buckets update"*) echo '{}' ;;
  "storage cp"*) echo '{}' ;;
  "secrets versions access"*) echo stub-password ;;
  *) echo '{}' ;;
esac
"""

# The stub bucket describe for "no lifecycle configured yet".
_EMPTY_BUCKET = '{"name":"example-proj-sig-backups"}'


def _env(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.update(overrides)
    return env


def _run(
    script: Path, args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env or _env(),
        cwd=str(REPO_ROOT),
    )


def _stubbed_env(
    tmp_path: Path, instances: list[str] | None = None, **overrides: str
) -> tuple[dict[str, str], Path]:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "gcloud"
    stub.write_text(_STUB_GCLOUD)
    stub.chmod(0o755)
    log = tmp_path / "gcloud.log"
    log.touch()
    state = tmp_path / "instances.state"
    state.write_text("\n".join(instances if instances is not None else ["sig-pg"]) + "\n")
    base = _env(
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT="example-proj",
        GCLOUD_STUB_LOG=str(log),
        STUB_INSTANCE_STATE=str(state),
        SIG_DRILL_NOW=OPEN_WINDOW,
        SIG_EXPORT_NOW=OPEN_WINDOW,
        SIG_DRILL_EVIDENCE_DIR=str(tmp_path / "evidence"),
        SIG_EVIDENCE_DIR=str(tmp_path / "evidence"),
    )
    base.update(overrides)
    return base, log


def _mutations(log: Path) -> list[str]:
    """Stub invocations that would mutate: clone/delete/create/restore/export/
    cp/update on storage, backups create. Read verbs and --help never count."""
    out = []
    for line in log.read_text().splitlines():
        if "--help" in line:
            continue
        if any(
            tok in line
            for tok in (
                "instances clone",
                "instances delete",
                "instances create",
                "backups create",
                "backups restore",
                "sql export",
                "storage cp",
                "buckets update",
                "storage rm",
                "storage mv",
            )
        ):
            out.append(line)
    return out


def _deletes(log: Path) -> list[str]:
    return [x for x in log.read_text().splitlines() if "instances delete" in x]


# ============================================================================
# restore-drill.sh — plan path
# ============================================================================


@pytest.mark.parametrize(
    "action",
    ["prestate", "clone", "counts", "smoke", "deleteclone", "fullrestore", "all"],
)
def test_drill_check_mode_is_a_plan_only_green(action: str) -> None:
    proc = _run(DRILL, [action])
    assert proc.returncode == 0, f"{action}: {proc.stderr}"
    assert "check OK" in proc.stdout
    assert "PLAN:" in proc.stdout


def test_drill_plan_names_the_pit_clone_and_name_checked_delete() -> None:
    proc = _run(DRILL, ["--check"], env=_env(SIG_GCP_PROJECT="example-proj"))
    plan = proc.stdout
    for needle in (
        "sql instances clone sig-pg sig-pg-drill-<STAMP>",
        "--point-in-time",
        "deleteclone sig-pg-drill-<STAMP>",
        "refuses sig-pg outright",
        "sig.restore-drill/1",
    ):
        assert needle in plan, needle


def test_drill_plan_marks_fullrestore_queued() -> None:
    proc = _run(DRILL, ["--check", "fullrestore"])
    assert "QUEUED" in proc.stdout
    assert "--go" in proc.stdout


# ============================================================================
# restore-drill.sh — deleteclone name checking (THE safety rule)
# ============================================================================


def test_deleteclone_refuses_sig_pg_and_mutates_nothing(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(DRILL, ["--apply", "deleteclone", "sig-pg"], env=env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "production instance" in proc.stderr
    assert _deletes(log) == []


@pytest.mark.parametrize(
    "name",
    [
        "sig-pg-drill-x",
        "sig-pg-drill-20261014t1210",  # no Z
        "sig-pg-drill-20261014t1210z-extra",
        "sig-pg2-drill-20261014t1210z",
        "sig-pg-drill-2026101",
    ],
)
def test_deleteclone_refuses_every_nonconforming_name(tmp_path: Path, name: str) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(DRILL, ["--apply", "deleteclone", name], env=env)
    assert proc.returncode == 42, f"{name}: {proc.stdout + proc.stderr}"
    assert _deletes(log) == []


def test_deleteclone_removes_only_a_valid_drill_instance(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(DRILL, ["--apply", "deleteclone", CLONE], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    deletes = _deletes(log)
    assert deletes == [f"sql instances delete {CLONE} --project example-proj --quiet"]
    assert "sig-pg " not in deletes[0]


def test_deleteclone_discovers_the_newest_drill_instance(tmp_path: Path) -> None:
    """Without an explicit name the newest sig-pg-drill-* is the target — and
    it is still name-checked before the delete."""
    env, log = _stubbed_env(tmp_path, instances=["sig-pg", CLONE])
    proc = _run(DRILL, ["--apply", "deleteclone"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _deletes(log) == [f"sql instances delete {CLONE} --project example-proj --quiet"]


def test_deleteclone_inside_the_band_is_a_window_refusal(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_DRILL_NOW=INSIDE_DAILY_BAND)
    proc = _run(DRILL, ["--apply", "deleteclone", CLONE], env=env)
    assert proc.returncode == 42
    assert _deletes(log) == []


# ============================================================================
# restore-drill.sh — clone leg stop rules
# ============================================================================


def test_clone_refuses_inside_the_daily_band(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_DRILL_NOW=INSIDE_DAILY_BAND)
    proc = _run(DRILL, ["--apply", "clone"], env=env)
    assert proc.returncode == 42
    assert "03:00-10:00Z" in proc.stderr
    assert not any("instances clone" in m for m in _mutations(log))


def test_clone_voids_on_a_failed_restore_point(tmp_path: Path) -> None:
    env, log = _stubbed_env(
        tmp_path,
        STUB_BACKUPS_FILE=str(tmp_path / "backups.json"),
    )
    (tmp_path / "backups.json").write_text('[{"id":"42","status":"FAILED","type":"AUTOMATED"}]')
    proc = _run(DRILL, ["--apply", "clone"], env=env)
    assert proc.returncode == 5, proc.stdout + proc.stderr
    assert "VOID" in proc.stderr
    assert not any("instances clone" in m for m in _mutations(log))


def test_clone_voids_on_a_red_probe_without_a_recorded_note(tmp_path: Path) -> None:
    env, log = _stubbed_env(
        tmp_path,
        STUB_PROBE_FILE=str(tmp_path / "probe.json"),
    )
    (tmp_path / "probe.json").write_text(
        '[{"status":{"conditions":[{"type":"Completed","status":"False",'
        '"message":"stale targets"}]}}]'
    )
    proc = _run(DRILL, ["--apply", "clone"], env=env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "probe" in proc.stderr
    assert not any("instances clone" in m for m in _mutations(log))


def test_clone_proceeds_inside_ar3_when_guards_pass(tmp_path: Path) -> None:
    """The clone is a separate instance: AR-3 does not bind it. With the newest
    backup SUCCESSFUL, a green probe and no running materialize, the leg is
    allowed inside the AR-3 window (outside the daily band)."""
    env, log = _stubbed_env(
        tmp_path,
        SIG_DRILL_NOW=INSIDE_AR3,  # AR-3 active; NOT inside the daily band
        STUB_PROBE_FILE=str(tmp_path / "probe.json"),
    )
    (tmp_path / "probe.json").write_text(
        '[{"status":{"conditions":[{"type":"Completed","status":"False",'
        '"message":"stale targets"}]}}]'
    )
    proc = _run(
        DRILL,
        ["--apply", "clone", "--probe-note", "red probe = the recorded stale-targets class"],
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    clones = [m for m in _mutations(log) if "instances clone" in m]
    assert len(clones) == 1
    assert clones[0].startswith("sql instances clone sig-pg sig-pg-drill-")
    assert "--point-in-time" in clones[0]
    # meta.env lands in the evidence dir
    metas = list((tmp_path / "evidence").glob("drill-*/meta.env"))
    assert metas, "meta.env not written"


def test_clone_refuses_while_a_materialize_runs(tmp_path: Path) -> None:
    env, log = _stubbed_env(
        tmp_path,
        STUB_MATERIALIZE_JSON='[{"status":{"conditions":[]}}]',
    )
    proc = _run(DRILL, ["--apply", "clone"], env=env)
    assert proc.returncode == 42
    assert "materialize" in proc.stderr
    assert not any("instances clone" in m for m in _mutations(log))


def test_clone_allows_terminal_failed_materialize_executions(tmp_path: Path) -> None:
    """Completed=False is terminal (failed/cancelled), not running — the live
    `sig-materialize` history carries six of them; the guard must not read a
    finished failure as a running execution (found by the 2026-10-02 live leg)."""
    env, log = _stubbed_env(
        tmp_path,
        SIG_DRILL_NOW=INSIDE_AR3,
        STUB_MATERIALIZE_JSON=(
            '[{"status":{"conditions":[{"type":"Completed","status":"False",'
            '"reason":"Cancelled"}],"completionTime":"2026-09-27T00:37:58Z"}},'
            '{"status":{"conditions":[{"type":"Completed","status":"True"}]}}]'
        ),
        STUB_PROBE_FILE=str(tmp_path / "probe.json"),
    )
    (tmp_path / "probe.json").write_text(
        '[{"status":{"conditions":[{"type":"Completed","status":"True"}]}}]'
    )
    proc = _run(DRILL, ["--apply", "clone"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert any("instances clone" in m for m in _mutations(log))


def test_fullrestore_refuses_without_a_go(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(DRILL, ["--apply", "fullrestore"], env=env)
    assert proc.returncode == 42
    assert "S5-3" in proc.stderr
    assert _mutations(log) == []


# ============================================================================
# restore-drill.sh — --verify --from-state
# ============================================================================


def test_drill_verify_from_state_green(tmp_path: Path) -> None:
    proc = _run(DRILL, ["--verify", "--from-state", str(FIXTURES / "restore-drill" / "green")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for needle in (
        "OK drill:reproduced",
        "OK drill:rto",
        "OK drill:rpo",
        "OK drill:per-table-parity",
        "OK drill:watermark-equal",
        "OK drill:sqitch-tip-equal",
        "OK drill:postgis",
        "OK drill:api-smoke",
        "OK drill:no-instance-left",
        "OK drill:sig-pg-untouched",
        "result=ok",
    ):
        assert needle in proc.stdout, needle


def test_drill_verify_from_state_reports_every_drift(tmp_path: Path) -> None:
    proc = _run(DRILL, ["--verify", "--from-state", str(FIXTURES / "restore-drill" / "drift")])
    assert proc.returncode == 1
    for needle in (
        "DRIFT drill:reproduced",
        "DRIFT drill:per-table-parity",
        "DRIFT drill:watermark-equal",
        "DRIFT drill:sqitch-tip-equal",
        "DRIFT drill:postgis",
        "DRIFT drill:api-smoke",
        "DRIFT drill:no-instance-left",
        "result=drift",
    ):
        assert needle in proc.stdout, needle


def test_drill_verify_from_state_refuses_a_missing_dir() -> None:
    proc = _run(DRILL, ["--verify", "--from-state", str(FIXTURES / "restore-drill" / "nope")])
    assert proc.returncode == 66


# ============================================================================
# restore-point.sh — the AR-2 procedure
# ============================================================================


def test_restore_point_check_is_plan_only() -> None:
    proc = _run(POINT, [])
    assert proc.returncode == 0, proc.stderr
    assert "sql backups create --instance sig-pg" in proc.stdout
    assert "check OK" in proc.stdout


def test_sqlpoint_creates_and_proves_the_backup(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, STUB_OP_TYPE="CREATE_BACKUP")
    proc = _run(POINT, ["--apply", "sqlpoint"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    created = [m for m in _mutations(log) if "backups create" in m]
    assert created == [
        "sql backups create --instance sig-pg --project example-proj --async --format=json"
    ]
    assert "restore point proven" in proc.stdout


def test_sqlpoint_stops_when_the_backup_is_not_successful(tmp_path: Path) -> None:
    env, log = _stubbed_env(
        tmp_path,
        STUB_BACKUPS_FILE=str(tmp_path / "backups.json"),
    )
    (tmp_path / "backups.json").write_text('[{"id":"42","status":"FAILED","type":"ON_DEMAND"}]')
    proc = _run(POINT, ["--apply", "sqlpoint"], env=env)
    assert proc.returncode == 5, proc.stdout + proc.stderr
    assert "STOP" in proc.stderr


def test_bucketpoint_refuses_a_source_outside_the_sig_buckets(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(
        POINT,
        ["--apply", "bucketpoint", "gs://someone-else-bucket/pg/"],
        env=env,
    )
    assert proc.returncode == 42
    assert not any("storage cp" in m for m in _mutations(log))


def test_bucketpoint_copies_into_sig_restricted(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(
        POINT,
        ["--apply", "bucketpoint", "gs://example-proj-sig-backups/pg/monthly/"],
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    copies = [m for m in _mutations(log) if "storage cp" in m]
    assert len(copies) == 1
    assert "gs://example-proj-sig-restricted/restore-point/" in copies[0]


# ============================================================================
# logical-export.sh — the queued legs
# ============================================================================


@pytest.mark.parametrize("action", ["export", "lifecycle", "relabel"])
def test_export_legs_refuse_without_a_go(tmp_path: Path, action: str) -> None:
    env, log = _stubbed_env(tmp_path)
    proc = _run(EXPORT, ["--apply", action], env=env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "DEFERRALS" in proc.stderr or "queued" in proc.stderr.lower()
    assert _mutations(log) == []


def test_export_leg_refuses_inside_the_band_even_with_a_go(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_EXPORT_NOW=INSIDE_DAILY_BAND)
    proc = _run(EXPORT, ["--apply", "export", "--go", GO], env=env)
    assert proc.returncode == 42
    assert "03:00-10:00Z" in proc.stderr
    assert not any("sql export" in m for m in _mutations(log))


def test_export_leg_refuses_inside_ar3_even_with_a_go(tmp_path: Path) -> None:
    """The export loads sig-pg's single vCPU — AR-3 binds it (unlike the clone)."""
    env, log = _stubbed_env(tmp_path, SIG_EXPORT_NOW=INSIDE_AR3)
    proc = _run(EXPORT, ["--apply", "export", "--go", GO], env=env)
    assert proc.returncode == 42
    assert "AR-3" in proc.stderr


def test_export_leg_with_a_go_exports_to_the_monthly_prefix(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, STUB_OP_TYPE="EXPORT")
    proc = _run(EXPORT, ["--apply", "export", "--go", GO], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    exports = [m for m in _mutations(log) if "sql export" in m]
    assert len(exports) == 1
    assert "sql export sql sig-pg" in exports[0]
    assert "gs://example-proj-sig-backups/pg/monthly/" in exports[0]
    assert "--database=sig" in exports[0]


def test_lifecycle_refuses_to_overwrite_foreign_rules(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign.json"
    foreign.write_text(
        '{"name":"example-proj-sig-backups","lifecycle":{"rule":['
        '{"action":{"type":"Delete"},"condition":{"age":7}}]}}'
    )
    env, log = _stubbed_env(tmp_path, STUB_BUCKET_DESCRIBE=str(foreign))
    proc = _run(EXPORT, ["--apply", "lifecycle", "--go", GO], env=env)
    assert proc.returncode == 42
    assert "never overwriting foreign rules" in proc.stderr.lower() or "REFUSED" in proc.stderr
    assert not any("buckets update" in m for m in _mutations(log))


def test_lifecycle_applies_the_two_p346_rules_on_an_empty_bucket(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(_EMPTY_BUCKET)
    env, log = _stubbed_env(tmp_path, STUB_BUCKET_DESCRIBE=str(empty))
    proc = _run(EXPORT, ["--apply", "lifecycle", "--go", GO], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    updates = [m for m in _mutations(log) if "buckets update" in m]
    assert len(updates) == 1


def test_lifecycle_skips_when_the_rules_already_match(tmp_path: Path) -> None:
    ours = tmp_path / "ours.json"
    ours.write_text(
        '{"name":"example-proj-sig-backups","lifecycle":{"rule":['
        '{"action":{"type":"Delete"},"condition":{"age":30,"matchesPrefix":["pg/adhoc/"]}},'
        '{"action":{"type":"Delete"},"condition":{"age":100,"matchesPrefix":["pg/monthly/"]}}'
        "]}}"
    )
    env, log = _stubbed_env(tmp_path, STUB_BUCKET_DESCRIBE=str(ours))
    proc = _run(EXPORT, ["--apply", "lifecycle", "--go", GO], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SKIP" in proc.stdout
    assert not any("buckets update" in m for m in _mutations(log))


def test_relabel_copies_seeds_and_never_deletes(tmp_path: Path) -> None:
    listing = tmp_path / "ls.txt"
    listing.write_text(
        "gs://example-proj-sig-backups/pg/sig-20260915T124956Z.sql\n"
        "gs://example-proj-sig-backups/pg/sig-20260915T125252Z.sql\n"
    )
    env, log = _stubbed_env(tmp_path, STUB_LS=str(listing))
    proc = _run(EXPORT, ["--apply", "relabel", "--go", GO], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    copies = [m for m in _mutations(log) if "storage cp" in m]
    assert len(copies) == 3  # two seed objects + the README
    assert all("pg/seed-2026-09-15/" in c for c in copies), copies
    # Never a delete, never an rm, never an mv of the originals.
    assert not any(
        "storage rm" in m or "storage mv" in m or "objects delete" in m
        for m in log.read_text().splitlines()
    )


def test_export_verify_from_state_green_and_drift() -> None:
    green = _run(EXPORT, ["--verify", "--from-state", str(FIXTURES / "logical-export" / "green")])
    assert green.returncode == 0, green.stdout + green.stderr
    assert "result=ok" in green.stdout
    drift = _run(EXPORT, ["--verify", "--from-state", str(FIXTURES / "logical-export" / "drift")])
    assert drift.returncode == 1
    assert "DRIFT export:lifecycle" in drift.stdout
    assert "DRIFT export:seed-prefix" in drift.stdout
    assert "DRIFT export:monthly-export-object" in drift.stdout
    assert "result=drift" in drift.stdout


# ============================================================================
# shared invariants
# ============================================================================


def test_no_script_embeds_a_literal_project_id() -> None:
    """The project id must stay env-only (GL-GATE-04): no literal project-like
    name in any of the three scripts."""
    for script in (DRILL, POINT, EXPORT):
        text = script.read_text()
        assert "zeta-medley" not in text
        # the derived bucket name always comes from $SIG_GCP_PROJECT
        assert "-sig-backups" in text  # parameterized usage, not a literal
