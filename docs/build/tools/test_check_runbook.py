#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_runbook.py`` — the P35.4 ops-runbook verifier
(SIG-OPS-010 / SIG-SEC-009).

Each case builds a small fixture tree under ``tmp_path`` — a runbook, a
stub ``ops/src/ops/cli.py`` parser table, a stub ``ops/iam_identities.toml``
secret matrix, a Makefile, and a corpus file — so the assertions are about
invariants (nine sections, verified commands, register equality, no
credential-shaped literals), never about a living record's current value.
"""

from __future__ import annotations

import importlib.util
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "check_runbook", _HERE / "check_runbook.py"
)
crb = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(crb)

SECTIONS = """## 1. Alert received
## 2. Restore
## 3. Republish
## 4. Scheduled-window watch
## 5. Job failed
## 6. Secret rotation
## 7. Roll
## 8. Cost review
## 9. Decommission
"""

REGISTER = """
| name | owner | consumer | last_rotation | procedure |
|---|---|---|---|---|
| `sig-a` | operator | `sig-rt` | `unknown` | stdin add |
| `sig-b` | operator | — | `unknown` | rotate before use |
"""

IAM = """[[secret]]
name = "sig-a"
consumers = ["sig-rt"]

[[secret]]
name = "sig-b"
consumers = []
"""

CLI = """import argparse
p = argparse.ArgumentParser()
sub = p.add_subparsers()
sub.add_parser("roll-jobs")
sub.add_parser("live-diff")
"""

MAKEFILE = "docs-check:\n\ttrue\nlint:\n\ttrue\n"

CORPUS_CMD = "gcloud run jobs execute"


def _tree(tmp_path: pathlib.Path, runbook: str) -> pathlib.Path:
    (tmp_path / "docs/ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/ops/RUNBOOK.md").write_text(runbook)
    (tmp_path / "ops/src/ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ops/src/ops/cli.py").write_text(CLI)
    (tmp_path / "ops/iam_identities.toml").write_text(IAM)
    (tmp_path / "Makefile").write_text(MAKEFILE)
    # the corpus an external command form is verified against
    (tmp_path / "ops/gcp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ops/gcp/x.sh").write_text(f"#!/bin/sh\n{CORPUS_CMD} sig-x\n")
    (tmp_path / "ops/gcp/real.sh").write_text("#!/bin/sh\ntrue\n")
    return tmp_path


def _rb(body: str = "", register: str = REGISTER) -> str:
    return SECTIONS + register + body


def test_missing_runbook(tmp_path):
    errs, _ = crb.check(_tree(tmp_path, "") / "empty")
    assert any("RUNBOOK.md" in e for e in errs)


def test_minimal_runbook_passes(tmp_path):
    body = """
```bash
uv run sig-ops roll-jobs --image img@sha256:deadbeef
bash ops/gcp/real.sh --check
make docs-check
gcloud run jobs execute <job>
```
See `ops/iam_identities.toml` and `docs/build/tools/check_runbook.py`-style
paths like `ops/gcp/real.sh`.
"""
    (tmp_path / "docs/ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/ops/RUNBOOK.md").write_text(_rb(body))
    (tmp_path / "ops/src/ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ops/src/ops/cli.py").write_text(CLI)
    (tmp_path / "ops/iam_identities.toml").write_text(IAM)
    (tmp_path / "Makefile").write_text(MAKEFILE)
    (tmp_path / "ops/gcp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ops/gcp/x.sh").write_text(f"#!/bin/sh\n{CORPUS_CMD} sig-x\n")
    (tmp_path / "ops/gcp/real.sh").write_text("#!/bin/sh\ntrue\n")
    (tmp_path / "docs/build/tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/build/tools/check_runbook.py").write_text("# stub\n")
    errs, stats = crb.check(tmp_path)
    assert errs == []
    assert stats["sections"] == 9
    assert stats["command_lines"] >= 4
    assert stats["register_rows"] == 2


def test_missing_section_fails(tmp_path):
    rb = _rb("").replace("## 7. Roll\n", "")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("'roll'" in e for e in errs)


def test_unknown_sig_ops_verb_fails(tmp_path):
    rb = _rb("```bash\nuv run sig-ops frobnicate --now\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("frobnicate" in e for e in errs)


def test_missing_script_fails(tmp_path):
    rb = _rb("```bash\nbash ops/gcp/ghost.sh --check\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("ghost.sh" in e for e in errs)


def test_unverifiable_gcloud_form_fails(tmp_path):
    rb = _rb("```bash\ngcloud frobnicate everything --now\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("gcloud" in e and "no verbatim match" in e for e in errs)


def test_prose_path_must_resolve(tmp_path):
    rb = _rb("The file `docs/nope/missing.md` does not exist.\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("missing.md" in e for e in errs)


def test_register_missing_secret_fails(tmp_path):
    rb = _rb("", register=REGISTER.replace("| `sig-b` | operator | — | `unknown` | rotate before use |\n", ""))
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("sig-b" in e for e in errs)


def test_register_consumer_drift_fails(tmp_path):
    bad = REGISTER.replace("`sig-rt`", "`sig-other-rt`")
    errs, _ = crb.check(_tree(tmp_path, _rb("", register=bad)))
    assert any("consumers" in e for e in errs)


def test_register_invented_date_fails(tmp_path):
    bad = REGISTER.replace("`unknown`", "`yesterday`", 1)
    errs, _ = crb.check(_tree(tmp_path, _rb("", register=bad)))
    assert any("last_rotation" in e for e in errs)


def test_credential_literal_fails(tmp_path):
    rb = _rb("The key is AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMY123456 in prose.\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("credential" in e for e in errs)


def test_unclassified_command_fails_closed(tmp_path):
    rb = _rb("```bash\ntotally-unknown-cmd --flag\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert any("unclassified" in e for e in errs)


def test_env_assignment_prefix_stripped(tmp_path):
    rb = _rb("```bash\nSIG_GCP_PROJECT=p uv run sig-ops live-diff\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert errs == []


def test_continuation_tail_skipped(tmp_path):
    rb = _rb("```bash\ngcloud run jobs execute <job> \\\n    --project p\n```\n")
    errs, _ = crb.check(_tree(tmp_path, rb))
    assert errs == []
