#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_gate_signatures.py`` (G4c; P34.28; SIG-SEC-010; OP-25; ADR-147).

Synthetic fixtures build a throw-away git repo per test in ``tmp_path`` carrying a LEDGER
with a kind-bearing `## GATE DECISIONS` table, a PENDING readout and a sources.toml. Signing
tests mint a **throwaway ed25519 key inside the test** (`ssh-keygen -N ""`) — the key never
leaves tmp_path, is never the operator's key, and is never committed. A real signature proves
only "a key in this test's allowed file signed this commit" — the wiring, never an operator
act. Every failing case asserts the specific uncovered record; every passing case asserts the
commit records were actually inspected (`gate_affecting_records` / `commits`), so a no-op
check cannot produce them.

Run::

    uv run pytest docs/build/tools/test_check_gate_signatures.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOL = HERE / "check_gate_signatures.py"
ALLOWED_REL = "docs/build/tools/record_policy/allowed_signers"

LEDGER = """# demo — build ledger

## GATE DECISIONS

### Round 11

| date | ticket | gate | item | answer (verbatim) | consequence | kind |
|---|---|---|---|---|---|---|
| 2026-10-01T10:00:00Z | T1 | GATE-G1 | scope | "yes" (chat) | narrowed | decision |
"""
READOUT = """# GATE-G9 — pending readout

Status: PENDING. No approval is asserted.

An operator or authorized human record supplies the decision; an agent must not sign or
assume silence is approval.
"""
SOURCES = """[sources.demo]
name = "demo"
ingestion_permitted = false

[sources.demo2]
name = "demo2"
ingestion_permitted = false
"""
GATE_ROW = (
    '| 2026-10-04T00:00:00Z | T9 | GATE-G9 | publish | "go" (chat) | released | {kind} |'
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=t",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def commit(repo: Path, msg: str = "change", sign_key: Path | None = None) -> str:
    git(repo, "add", "-A")
    extra: list[str] = []
    post: list[str] = []
    if sign_key is not None:
        extra = ["-c", "gpg.format=ssh", "-c", f"user.signingkey={sign_key}"]
        post = ["-S"]
    git(repo, *extra, "commit", "-q", "--allow-empty", *post, "-m", msg)
    return git(repo, "rev-parse", "HEAD").strip()


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    write(r, "docs/build/LEDGER.md", LEDGER)
    write(r, "docs/build/readouts/GATE-G9.md", READOUT)
    write(r, "connectors/src/connectors/data/sources.toml", SOURCES)
    commit(r, "base")
    git(r, "tag", "base")
    return r


def check(repo: Path, span: str = "base..HEAD", *extra: str) -> tuple[int, dict, str]:
    out = repo.parent / f"gates-{os.getpid()}.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--range",
            span,
            "--repo",
            str(repo),
            "--json",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text()) if out.exists() else {}
    return proc.returncode, doc, proc.stdout + proc.stderr


def viol_kinds(doc: dict) -> list[str]:
    return [v["kind"] for v in doc.get("violations", [])]


def _ssh_key(tmp: Path, name: str) -> Path:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")
    key = tmp / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)],
        check=True,
    )
    return key


def _allowed(path: Path, key: Path) -> Path:
    kind, blob = key.with_suffix(".pub").read_text().split()[:2]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"t@example.invalid {kind} {blob}\n")
    return path


def flip(repo: Path, src: str = "demo") -> None:
    p = repo / "connectors/src/connectors/data/sources.toml"
    text = p.read_text()
    old = f"[sources.{src}]\nname = \"{src}\"\ningestion_permitted = false"
    assert old in text
    p.write_text(text.replace(old, old.replace("false", "true"), 1))


def sign_readout(repo: Path) -> None:
    p = repo / "docs/build/readouts/GATE-G9.md"
    text = p.read_text()
    p.write_text(
        text.replace("Status: PENDING. No approval is asserted.", "Status: SIGNED")
        + '\n## Signature\n\nOperator decision (verbatim, received 2026-10-04T00:00:00Z via chat): "go"\n'
        "GATE DECISIONS row: 2026-10-04T00:00:00Z | GATE-G9\n"
        "Signed by: the operator. Recorded by t/t/t, which does not sign.\n"
    )


def add_gate_row(repo: Path, kind: str = "decision", item: str = "publish") -> None:
    p = repo / "docs/build/LEDGER.md"
    p.write_text(p.read_text() + GATE_ROW.format(kind=kind).replace("publish", item))


# ── unsigned gate-affecting records fail closed ─────────────────────────────


def test_plain_change_passes(repo: Path) -> None:
    write(repo, "notes.md", "x\n")
    commit(repo)
    rc, doc, _ = check(repo)
    assert rc == 0 and doc["summary"]["commits"] == 1
    assert doc["summary"]["gate_affecting_records"] == 0


def test_unsigned_readout_status_fails(repo: Path) -> None:
    sign_readout(repo)
    commit(repo)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["readout-status"], out


def test_not_passable_is_gate_affecting(repo: Path) -> None:
    p = repo / "docs/build/readouts/GATE-G9.md"
    p.write_text(
        p.read_text().replace(
            "Status: PENDING. No approval is asserted.", "Status: NOT-PASSABLE"
        )
    )
    commit(repo)
    rc, doc, _ = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["readout-status"]


@pytest.mark.parametrize("kind", ["decision", "waiver", "pre-authorization"])
def test_unsigned_gate_record_row_fails(repo: Path, kind: str) -> None:
    add_gate_row(repo, kind)
    commit(repo)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["gate-record"], out


def test_unsigned_source_flip_fails(repo: Path) -> None:
    flip(repo)
    commit(repo)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"], out


def test_non_decision_rows_and_new_pending_readout_pass(repo: Path) -> None:
    add_gate_row(repo, "confirmation", "drafted-block")
    write(
        repo,
        "docs/build/readouts/GATE-G10.md",
        "# GATE-G10\n\nStatus: PENDING\n\nAn operator or authorized human record supplies the "
        "decision; an agent must not sign or assume silence is approval.\n",
    )
    commit(repo)
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["summary"]["gate_affecting_records"] == 0


def test_template_files_are_not_readouts(repo: Path) -> None:
    write(
        repo,
        "docs/build/readouts/_GATE_TEMPLATE.md",
        "# template\n\nStatus: SIGNED\n",
    )
    commit(repo)
    rc, doc, _ = check(repo)
    assert rc == 0 and doc["summary"]["gate_affecting_records"] == 0


def test_corrections_register_rows_are_not_gate_records(repo: Path) -> None:
    """A non-decision table inside `## GATE DECISIONS` — the TS-08 corrections register has
    no `gate` column — never produces gate records (its rows are dispositions)."""
    p = repo / "docs/build/LEDGER.md"
    p.write_text(
        p.read_text()
        + "\n| row | date as restored | class (TS-08) | fact (evidence) | correction / status | refs |\n"
        "|---|---|---|---|---|---|\n"
    )
    commit(repo, "add the corrections register")
    p.write_text(
        p.read_text() + "| R20 | 2026-10-04 | fix | the row text | stands as history | B5 |\n"
    )
    commit(repo, "append a corrections row")
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["summary"]["gate_affecting_records"] == 0


def test_flip_with_a_trailing_comment_is_caught(repo: Path) -> None:
    p = repo / "connectors/src/connectors/data/sources.toml"
    text = p.read_text()
    p.write_text(
        text.replace(
            'ingestion_permitted = false', "ingestion_permitted = true  # reviewed", 1
        )
    )
    commit(repo)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"], out


def test_restored_table_rows_are_not_new_decisions(repo: Path) -> None:
    """Rows under a `RESTORED from `<sha>^`` caption replay history — memory_guard's
    blame mode already enforces their verbatim-ness, so G4c exempts the table."""
    src = git(repo, "rev-parse", "base").strip()
    p = repo / "docs/build/LEDGER.md"
    p.write_text(
        p.read_text()
        + f"\n- history carried forward — RESTORED from `{src}^`\n\n"
        "| date | ticket | gate | item | answer | consequence | kind |\n"
        "|---|---|---|---|---|---|---|\n"
        '| 2026-09-01T00:00:00Z | T0 | GATE-OLD | scope | "yes" | — | decision |\n'
    )
    commit(repo, "restore a historical decisions table")
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["summary"]["gate_affecting_records"] == 0


def test_no_allowed_signers_means_a_signature_cannot_cover(repo: Path, tmp_path: Path) -> None:
    key = _ssh_key(tmp_path, "test-only")
    flip(repo)
    commit(repo, "flip", sign_key=key)
    rc, doc, _ = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"]
    assert doc["commits"][0]["signature_status"] == "E"


# ── signed coverage ─────────────────────────────────────────────────────────


@pytest.fixture
def keyed_repo(repo: Path, tmp_path: Path) -> tuple[Path, Path]:
    """`repo` plus a committed allowed_signers at BASE holding the test key."""
    key = _ssh_key(tmp_path, "test-only")
    _allowed(repo / ALLOWED_REL, key)
    commit(repo, "commit the test allowed_signers")
    git(repo, "tag", "-f", "base")  # move base forward: the file must exist AT BASE
    return repo, key


def test_signed_flip_passes(keyed_repo: tuple[Path, Path]) -> None:
    repo, key = keyed_repo
    flip(repo)
    commit(repo, "operator flip", sign_key=key)
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["commits"][0]["signature_status"] == "G"
    assert doc["summary"]["gate_affecting_records"] == 1


def test_signed_readout_and_decision_row_pass(keyed_repo: tuple[Path, Path]) -> None:
    repo, key = keyed_repo
    sign_readout(repo)
    add_gate_row(repo)
    commit(repo, "operator signs", sign_key=key)
    rc, doc, out = check(repo)
    assert rc == 0, out
    assert doc["summary"]["gate_affecting_records"] == 2


def test_wrong_key_fails(keyed_repo: tuple[Path, Path], tmp_path: Path) -> None:
    repo, _key = keyed_repo
    other = _ssh_key(tmp_path, "other-test-only")
    flip(repo)
    commit(repo, "flip signed by a non-allowed key", sign_key=other)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"], out
    assert doc["commits"][0]["signature_status"] != "G"


def test_unsigned_commit_fails_even_with_file(keyed_repo: tuple[Path, Path]) -> None:
    repo, _key = keyed_repo
    flip(repo)
    commit(repo, "unsigned flip")
    rc, doc, _ = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"]


def test_flip_covered_by_a_signed_record(keyed_repo: tuple[Path, Path]) -> None:
    """The flip commit is unsigned but a GATE DECISIONS row naming the source was added by a
    commit that verifies `G` — record coverage (SIG-SEC-010: the record carries the origin)."""
    repo, key = keyed_repo
    add_gate_row(repo, "decision", "sources.demo")
    commit(repo, "operator records the flip decision", sign_key=key)
    flip(repo)
    commit(repo, "agent applies the recorded flip")
    rc, doc, out = check(repo)
    assert rc == 0, out
    trig = doc["commits"][1]["triggers"][0]
    assert trig["kind"] == "source-flip" and trig["covered"].startswith("record@")


def test_flip_with_only_an_unsigned_record_fails(keyed_repo: tuple[Path, Path]) -> None:
    repo, _key = keyed_repo
    add_gate_row(repo, "decision", "sources.demo")
    commit(repo, "unsigned record")
    flip(repo)
    commit(repo, "unsigned flip")
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["gate-record", "source-flip"], out


def test_a_confirmation_row_never_covers_a_flip(keyed_repo: tuple[Path, Path]) -> None:
    """Coverage records must be decision/waiver/pre-authorization rows — a signed
    `confirmation` row that happens to name the source is not an authorization."""
    repo, key = keyed_repo
    add_gate_row(repo, "confirmation", "sources.demo")
    commit(repo, "operator confirms an earlier record", sign_key=key)
    flip(repo)
    commit(repo, "agent applies flip")
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"], out


def test_self_authorisation_fails(repo: Path, tmp_path: Path) -> None:
    """A change adding its own signer cannot authorise itself: the file is read at BASE."""
    key = _ssh_key(tmp_path, "test-only")
    _allowed(repo / ALLOWED_REL, key)
    flip(repo)
    commit(repo, "add my key and flip", sign_key=key)
    rc, doc, out = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"], out
    assert doc["input"]["allowed_signers"] is None


def test_header_only_file_fails_closed(repo: Path, tmp_path: Path) -> None:
    """The committed header-only `allowed_signers` (OP-25 outstanding): even a signed
    gate-affecting commit fails — nothing to verify against."""
    write(repo, ALLOWED_REL, "# allowed_signers — no key yet (OP-25 outstanding)\n")
    commit(repo, "commit header-only allowed_signers")
    git(repo, "tag", "-f", "base")
    key = _ssh_key(tmp_path, "test-only")
    flip(repo)
    commit(repo, "flip", sign_key=key)
    rc, doc, _ = check(repo)
    assert rc == 1 and viol_kinds(doc) == ["source-flip"]


# ── fail-loud edges ──────────────────────────────────────────────────────────


def test_vacuous_range_is_exit_3(repo: Path) -> None:
    rc, doc, _ = check(repo, "HEAD..HEAD")
    assert rc == 3


def test_unresolvable_revision_is_unknown(repo: Path) -> None:
    rc, doc, out = check(repo, "base..no-such-ref")
    assert rc == 5 and "unknown" in out.lower()


def test_not_a_repo_is_usage(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--range", "a..b", "--repo", str(bare)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
