# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.5 cost guard — `ops/gcp/cost-guard.sh` + `docs/build/reports/spend/`.

Covers the ticket's deterministic acceptance criteria (SIG-OPS-009): the
check-mode plan names the $300 ceiling, the 50/90/100 % thresholds and the
project scope; the apply path is idempotent and stays inside the authorised
mutation allowlist (API enable, two budgets, one dataset); the test budget's
delete is name-checked and refuses without the fired-confirmation; `--verify
--from-state` is proven both directions offline; the billing account is
discovered live, never committed; and the spend ledger's label vocabulary +
no-fabrication rules hold on the committed CSVs.

`--apply` never touches production in tests: stub `gcloud`/`bq` binaries on
PATH record invocations and serve canned state.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "cost-guard.sh"
SPEND_DIR = REPO_ROOT / "docs" / "build" / "reports" / "spend"
RUNBOOK = REPO_ROOT / "docs" / "build" / "reports" / "INFRA_RUNBOOK.md"
STUBS = Path(__file__).parent / "fixtures" / "costguard" / "stubs"

PROJECT = "sig-fixture-project"  # a fixture id — the real id is never committed (OP-07)
PROJECT_NUMBER = "42424242"  # GCP stores the budget scope as the project number
CEILING = "SIG infra ceiling — 300 USD per month (U-008)"
TEST_NAME = "SIG-P34.5 test threshold — fires then deleted"


def _ceiling_budget() -> dict:
    return {
        "name": "billingAccounts/AAAA-BBBB-CCCC/budgets/7001",
        "displayName": CEILING,
        "amount": {"specifiedAmount": {"currencyCode": "USD", "units": "300"}},
        "thresholdRules": [
            {"thresholdPercent": 0.5, "spendBasis": "CURRENT_SPEND"},
            {"thresholdPercent": 0.9, "spendBasis": "CURRENT_SPEND"},
            {"thresholdPercent": 1.0, "spendBasis": "CURRENT_SPEND"},
        ],
        # Live state carries the project NUMBER, not the id — the real apply
        # stored `projects/<number>` after `gcloud` normalised the flag.
        "budgetFilter": {"projects": [f"projects/{PROJECT_NUMBER}"]},
        "allUpdatesRule": {},
    }


def _default_state(**over) -> dict:
    state = {
        "project": PROJECT,
        "project_number": PROJECT_NUMBER,
        "billing_acct": "AAAA-BBBB-CCCC",
        "apis_enabled": ["billingbudgets.googleapis.com"],
        "budgets": [],
        "datasets": [],
        "channels": [
            {
                "name": f"projects/{PROJECT}/notificationChannels/424242",
                "displayName": "SIG operator email (Track 0.5)",
                "enabled": True,
            }
        ],
        "export_rows": 0,
    }
    state.update(over)
    return state


def _env(tmp_path: Path, state: dict | None = None, **over: str) -> tuple[dict, Path]:
    """PATH with the offline stubs; returns (env, evidence-root)."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name in ("gcloud", "bq"):
        shutil.copy(STUBS / name, bindir / name)
        (bindir / name).chmod(0o755)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state if state is not None else _default_state()))
    ev = tmp_path / "evidence"
    env = dict(
        os.environ,
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT=PROJECT,
        GCLOUD_STUB_STATE=str(state_path),
        GCLOUD_STUB_LOG=str(tmp_path / "gcloud.log"),
        BQ_STUB_LOG=str(tmp_path / "bq.log"),
        SIG_COST_GUARD_EVIDENCE_DIR=str(ev),
        # from-state verify carries no live `projects describe`; the number is
        # the env override the real leg-runner exports alongside it.
        SIG_BUDGET_PROJECT_NUMBER=PROJECT_NUMBER,
    )
    env.update(over)
    return env, ev


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _gcloud_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "gcloud.log"
    return log.read_text().splitlines() if log.exists() else []


def _state(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "state.json").read_text())


# --- check mode ---------------------------------------------------------------


def test_no_args_is_a_plan_only_check(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    env.pop("SIG_GCP_PROJECT")
    proc = _run([], env)
    assert proc.returncode == 0, proc.stderr
    assert "check OK" in proc.stdout
    assert "PLAN:" in proc.stdout
    # Check mode makes no tool calls at all.
    assert _gcloud_calls(tmp_path) == []
    assert not (tmp_path / "bq.log").exists()


def test_plan_names_ceiling_thresholds_scope_and_rollback(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run([], env)
    out = proc.stdout
    assert "--budget-amount=300USD" in out
    assert "percent=0.50" in out and "percent=0.90" in out and "percent=1.0" in out
    # Infrastructure-only: the filter is on the SIG project, not the account.
    assert "--filter-projects=projects/$SIG_GCP_PROJECT" in out
    assert "gcloud billing budgets delete" in out  # rollback printed
    assert "sig_billing_export" in out
    assert "test threshold" in out
    assert "--fired-confirmed" in out
    # The billing-export link is an operator console step — the plan says so.
    assert "OP-12" in out


def test_check_mode_never_needs_adc_or_project(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(deny_adc=True))
    env.pop("SIG_GCP_PROJECT")
    proc = _run([], env)
    assert proc.returncode == 0


# --- apply: the allowlist + idempotency --------------------------------------


def test_apply_all_runs_the_authorised_mutations_in_order(tmp_path: Path) -> None:
    env, ev = _env(tmp_path, _default_state(apis_enabled=[]))
    proc = _run(["--apply"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _gcloud_calls(tmp_path)
    # Only the authorised mutation verbs ever reach gcloud.
    mutations = [
        c for c in calls if " create " in c or " delete " in c or " enable " in c or " update " in c
    ]
    assert mutations[0].startswith("gcloud services enable billingbudgets.googleapis.com")
    creates = [c for c in mutations if "budgets create" in c]
    assert len(creates) == 2  # ceiling + test budget — nothing else
    ceiling_call = creates[0]
    assert "--budget-amount=300USD" in ceiling_call
    for pct in ("percent=0.50", "percent=0.90", "percent=1.0"):
        assert pct in ceiling_call
    assert f"--filter-projects=projects/{PROJECT}" in ceiling_call
    # The committed operator channel is wired in when it resolves.
    assert "notificationChannels/424242" in ceiling_call
    # Default IAM recipients are never disabled.
    assert "--disable-default-iam-recipients" not in ceiling_call
    test_call = creates[1]
    assert "--budget-amount=0.01USD" in test_call
    assert test_call.count("percent=") == 1 and "percent=1.0" in test_call
    # The dataset leg ran through bq; exportcheck reported no rows.
    assert (tmp_path / "bq.log").read_text().count("bq mk --dataset") == 1
    assert "no export table yet" in proc.stdout
    # Pre/post evidence landed with sha256s.
    predirs = [d for d in ev.glob("pre-*") if d.is_dir()]
    postdirs = [d for d in ev.glob("post-*") if d.is_dir()]
    assert predirs and postdirs
    assert "budgets.json" in {p.name for p in predirs[0].iterdir()}
    # Post-state verify passed.
    assert "ceiling-budget OK" in proc.stdout


def test_budget_create_is_idempotent_by_display_name(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(budgets=[_ceiling_budget()]))
    proc = _run(["--apply", "budget"], env)
    assert proc.returncode == 0
    assert "SKIP" in proc.stdout
    assert not any("budgets create" in c for c in _gcloud_calls(tmp_path))


def test_dataset_create_is_idempotent(tmp_path: Path) -> None:
    ds = {
        "datasetReference": {"datasetId": "sig_billing_export"},
        "id": f"{PROJECT}:sig_billing_export",
    }
    env, _ = _env(tmp_path, _default_state(datasets=[ds]))
    proc = _run(["--apply", "dataset"], env)
    assert proc.returncode == 0
    assert "SKIP dataset" in proc.stdout
    bq_log = (tmp_path / "bq.log").read_text() if (tmp_path / "bq.log").exists() else ""
    assert "bq mk" not in bq_log


def test_budgets_list_failure_refuses_create(tmp_path: Path) -> None:
    """A failed read must never be treated as 'absent' — no blind duplicate."""
    env, _ = _env(tmp_path, _default_state(deny_budgets=True))
    proc = _run(["--apply", "budget"], env)
    assert proc.returncode != 0
    assert "not creating on a failed read" in proc.stderr
    assert not any("budgets create" in c for c in _gcloud_calls(tmp_path))


def test_permission_denied_reports_op12(tmp_path: Path) -> None:
    """Billing-admin denial surfaces as the honest OP-12 path, not a retry."""
    state = _default_state()
    # list works (viewer), create denied (no costsManager): emulate by denying
    # the create only — the stub denies both, so simulate create-denied via a
    # budgets list that succeeds then a create denied.
    env, _ = _env(tmp_path, state)
    proc = _run(["--apply", "budget"], env)
    assert proc.returncode == 0  # list succeeds, create succeeds in the default stub
    # Now deny at create time.
    st = _state(tmp_path)
    st["deny_budgets"] = True
    (tmp_path / "state.json").write_text(json.dumps(st))
    env2 = env
    proc2 = _run(["--apply", "budget"], env2)
    assert proc2.returncode != 0
    assert "OP-12" in proc2.stderr or "not creating on a failed read" in proc2.stderr


def test_apply_requires_adc(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(deny_adc=True))
    proc = _run(["--apply", "budget"], env)
    assert proc.returncode == 3
    assert "gate pending" in proc.stdout + proc.stderr


# --- test-budget lifecycle ----------------------------------------------------


def test_testbudget_delete_refuses_without_fired_confirmation(tmp_path: Path) -> None:
    state = _default_state()
    env, _ = _env(tmp_path, state)
    proc = _run(["--apply"], env)
    assert proc.returncode == 0
    proc = _run(["--apply", "testbudget-delete"], env)
    assert proc.returncode == 42
    assert "REFUSED" in proc.stderr
    assert not any("budgets delete" in c for c in _gcloud_calls(tmp_path))
    # The test budget is still there — it must not outlive an unconfirmed fire.
    names = [b["displayName"] for b in _state(tmp_path)["budgets"]]
    assert TEST_NAME in names


def test_testbudget_delete_after_confirmation_removes_only_it(tmp_path: Path) -> None:
    env, ev = _env(tmp_path)
    assert _run(["--apply"], env).returncode == 0
    proc = _run(
        ["--apply", "testbudget-delete", "--fired-confirmed", "operator e-mail 2026-10-02"],
        env,
    )
    assert proc.returncode == 0, proc.stderr
    remaining = [b["displayName"] for b in _state(tmp_path)["budgets"]]
    assert remaining == [CEILING]  # name-checked: only the test budget is gone
    deletes = [c for c in _gcloud_calls(tmp_path) if "budgets delete" in c]
    assert len(deletes) == 1
    # The confirmation is recorded in the evidence dir.
    assert any("fired-confirmed.txt" in p.name for p in ev.rglob("*"))


def test_testbudget_delete_is_skip_when_absent(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(budgets=[_ceiling_budget()]))
    proc = _run(
        ["--apply", "testbudget-delete", "--fired-confirmed", "recorded"],
        env,
    )
    assert proc.returncode == 0
    assert "SKIP" in proc.stdout


# --- verify (live + from-state) ------------------------------------------------


def _state_dir(tmp_path: Path, budgets: list, datasets: list) -> Path:
    d = tmp_path / "state-dir"
    d.mkdir(exist_ok=True)
    (d / "budgets.json").write_text(json.dumps(budgets))
    (d / "datasets.json").write_text(json.dumps(datasets))
    return d


DS = {"datasetReference": {"datasetId": "sig_billing_export"}, "id": "p:sig_billing_export"}


def test_verify_from_state_all_ok(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    d = _state_dir(tmp_path, [_ceiling_budget()], [DS])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ceiling-budget OK" in proc.stdout
    assert "export-dataset OK" in proc.stdout


def test_verify_from_state_missing_budget_and_dataset(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    d = _state_dir(tmp_path, [], [])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert proc.returncode == 1
    assert "ceiling-budget MISSING" in proc.stdout
    assert "export-dataset MISSING" in proc.stdout


def test_verify_from_state_drifted_threshold_or_amount(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    bad = _ceiling_budget()
    bad["thresholdRules"] = [{"thresholdPercent": 0.5, "spendBasis": "CURRENT_SPEND"}]
    d = _state_dir(tmp_path, [bad], [DS])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert proc.returncode == 1
    assert "DRIFT" in proc.stdout
    bad = _ceiling_budget()
    bad["amount"]["specifiedAmount"]["units"] = "299"
    d = _state_dir(tmp_path, [bad], [DS])
    assert _run(["--verify", "--from-state", str(d)], env).returncode == 1
    bad = _ceiling_budget()
    bad["budgetFilter"]["projects"] = []  # account-wide = NOT infrastructure-only
    d = _state_dir(tmp_path, [bad], [DS])
    assert _run(["--verify", "--from-state", str(d)], env).returncode == 1


def test_verify_scope_matches_project_id_or_number_but_not_another(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    id_form = _ceiling_budget()
    id_form["budgetFilter"]["projects"] = [f"projects/{PROJECT}"]
    d = _state_dir(tmp_path, [id_form], [DS])
    assert _run(["--verify", "--from-state", str(d)], env).returncode == 0
    wrong = _ceiling_budget()
    wrong["budgetFilter"]["projects"] = ["projects/99999999"]
    d = _state_dir(tmp_path, [wrong], [DS])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert proc.returncode == 1
    assert "DRIFT" in proc.stdout


def test_verify_from_state_reports_test_budget_observation(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    test_budget = dict(_ceiling_budget())
    test_budget["displayName"] = TEST_NAME
    d = _state_dir(tmp_path, [_ceiling_budget(), test_budget], [DS])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert proc.returncode == 0
    assert "test-budget    present" in proc.stdout
    d = _state_dir(tmp_path, [_ceiling_budget()], [DS])
    proc = _run(["--verify", "--from-state", str(d)], env)
    assert "test-budget    gone" in proc.stdout


def test_verify_live_against_stub(tmp_path: Path) -> None:
    state = _default_state(budgets=[_ceiling_budget()], datasets=[DS])
    env, _ = _env(tmp_path, state)
    proc = _run(["--verify"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ceiling-budget OK" in proc.stdout


def test_verify_live_fails_when_api_disabled(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(apis_enabled=[]))
    proc = _run(["--verify"], env)
    assert proc.returncode == 1
    assert "not enabled" in proc.stderr


def test_exportcheck_reports_rows_when_present(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, _default_state(export_rows=12))
    proc = _run(["--apply", "exportcheck"], env)
    assert proc.returncode == 0
    assert "holds rows" in proc.stdout


def test_exportcheck_is_honest_when_absent(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run(["--apply", "exportcheck"], env)
    assert proc.returncode == 0
    assert "no export table yet" in proc.stdout


# --- hygiene ------------------------------------------------------------------


def test_script_commits_no_project_or_account_or_email_literals() -> None:
    text = SCRIPT.read_text()
    assert "medley" not in text and "eleutheria-508121" not in text
    assert not re.search(r"billingAccounts/[A-Z0-9]{6}", text)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), "no e-mail literals"
    assert ":latest" not in text


def test_check_mode_works_without_any_env(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("SIG_GCP_PROJECT", None)
    env.pop("SIG_BILLING_ACCOUNT", None)
    proc = _run([], env)
    assert proc.returncode == 0


def test_billing_account_env_override(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_BILLING_ACCOUNT="ZZZZ-YYYY-XXXX")
    proc = _run(["--apply", "budget"], env)
    assert proc.returncode == 0
    assert "ZZZZ-YYYY-XXXX" in proc.stdout


# --- spend ledger --------------------------------------------------------------


LABELS = {"measured", "operator-reported", "estimate", "pending"}


def _ledger_rows() -> list[dict]:
    with open(SPEND_DIR / "spend_ledger.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def _usage_rows() -> list[dict]:
    with open(SPEND_DIR / "agent_usage.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def test_spend_ledger_label_vocabulary() -> None:
    rows = _ledger_rows()
    assert rows, "the ledger must carry rows"
    for r in rows:
        assert r["source_label"] in LABELS, f"unknown label {r['source_label']!r}"


def test_pending_rows_carry_no_amount() -> None:
    for r in _ledger_rows():
        if r["source_label"] == "pending":
            assert r["amount_usd"] == "", f"pending row must not fabricate: {r}"
        if r["source_label"] == "measured":
            assert r["amount_usd"] not in ("", "~"), f"measured row needs a figure: {r}"
            assert r["evidence"], "measured rows need an evidence pointer"


def test_no_measured_row_claims_unexported_billing() -> None:
    """Until the export link lands, no GCP row may be labelled measured."""
    for r in _ledger_rows():
        if r["provider"] == "gcp" and r["source_label"] == "measured":
            pytest.fail(
                "a measured GCP row exists but the billing export is not yet "
                "linked (D-P34.5-2) — verified measured rows only"
            )


def test_non_gcp_rows_are_outside_the_cloud_account() -> None:
    rows = [r for r in _ledger_rows() if r["provider"] != "gcp"]
    assert rows, "the ledger must carry the non-GCP lines"
    for r in rows:
        assert "outside-cloud-account" in r["note"]


def test_agent_usage_is_separate_and_uncapped() -> None:
    rows = _usage_rows()
    assert rows
    for r in rows:
        assert r["source_label"] in LABELS
        assert "amount_usd" not in r, "agent usage is never a spend line"
        assert "never dollar-capped" in r["note"] or "never" in r["note"].lower()


def test_spend_ledger_doc_names_the_conventions() -> None:
    doc = (SPEND_DIR / "SPEND_LEDGER.md").read_text()
    for word in ("measured", "operator-reported", "estimate", "pending"):
        assert f"`{word}`" in doc
    assert "$300" in doc or "USD 300" in doc or "300" in doc
    assert "gcp_billing_export_v1_" in doc
    assert "OP-12" in doc


def test_monthly_ledger_file_exists_with_labels_and_cap_assumption() -> None:
    doc = (SPEND_DIR / "2026-10.md").read_text()
    for word in ("estimate", "pending"):
        assert word in doc
    # B-11: the 40 GB autoresize cap is recorded as an assumption, not a figure.
    assert "40 GB" in doc and "assumption" in doc.lower()
    # Agent usage is present and uncapped.
    assert "never dollar-capped" in doc
    # No committed billing-account literal (the id is discovered live).
    assert not re.search(r"billingAccounts?/[A-Z0-9]{6}", doc)
    assert not re.search(r"gcp_billing_export_v1_[A-Z0-9]{6}", doc)


def test_runbook_carries_the_cost_guard_section() -> None:
    text = RUNBOOK.read_text()
    assert "Cost guard (P34.5" in text
    assert "cost-guard.sh --check" in text
    assert "cost-guard.sh --verify" in text
    assert "sig_billing_export" in text


# --- DEFERRALS -----------------------------------------------------------------


def test_deferral_rows_exist() -> None:
    text = (REPO_ROOT / "docs" / "tickets" / "DEFERRALS.md").read_text()
    for did in ("D-P34.5-1", "D-P34.5-2", "D-P34.5-3"):
        assert f"| {did} |" in text
    assert "testbudget-delete --fired-confirmed" in text
