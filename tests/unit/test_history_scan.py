# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The public-history scan (P37.55, Q-E2-23 [B-6] = a).

A seeded git repo proves the invariant: a secret committed and "removed" in a
later commit is still found in history — the whole point of scanning blobs,
not the tip. Handle-list and e-mail findings are the *disclosed* class
(A-0.4): counted, never blocking; an unclassified e-mail or a credential path
blocks. Findings never echo matched bytes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))
import history_scan as hs  # noqa: E402

# A fake AWS-shaped key assembled so THIS test file carries no credential
# literal (the tracked-file scanner scans tests too).
SEEDED_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
SEEDED_HANDLE = "camreg_jdoe_example"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _seed_repo(tmp_path: Path, files: dict[str, bytes], branch: str = "origin/main") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    for rel, data in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        _git(repo, "add", rel)
        _git(repo, "commit", "-qm", f"add {rel}")
    # Mirror the public surface: the scanner reads refs/remotes/origin/*.
    _git(repo, "update-ref", f"refs/remotes/{branch}", "HEAD")
    return repo


def test_secret_removed_from_the_tip_is_still_found_in_history(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        {
            "leak.py": f'KEY = "{SEEDED_AWS_KEY}"\n'.encode(),
            "ok.py": b"x = 1\n",
        },
    )
    # "Remove" the secret — the tip is clean, history is not.
    (repo / "leak.py").write_text("x = 2\n")
    _git(repo, "add", "leak.py")
    _git(repo, "commit", "-qm", "remove the key")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert report["disposition"] == "findings"
    assert "secret:aws-access-key" in report["findings"]
    # The finding names paths/rule ids — never the secret itself.
    blob = str(report["findings"])
    assert SEEDED_AWS_KEY not in blob


def test_clean_history_reports_clean(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, {"a.py": b"x = 1\n"})
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert report["disposition"] == "clean"
    assert report["findings"] == {}
    assert report["scope"]["commits"] == 1


def test_credential_path_in_history_is_a_finding(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, {".env": b"A=1\n"})
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert report["disposition"] == "findings"
    assert "path:env-file" in report["findings"]


def test_handle_list_hits_are_disclosed_not_blocking(tmp_path: Path) -> None:
    handle_file = tmp_path / "handles.txt"
    handle_file.write_text(f"{SEEDED_HANDLE}\n")
    repo = _seed_repo(tmp_path, {"sources.toml": f'id = "{SEEDED_HANDLE}"\n'.encode()})
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",), handle_path=handle_file)
    assert report["disposition"] == "clean"
    assert report["disclosed"]["handle_tokens_matched"] == 1
    assert SEEDED_HANDLE not in str(report)


def test_absent_handle_list_is_recorded_skipped(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, {"a.py": b"x = 1\n"})
    report = hs.scan_history(
        repo, namespaces=("refs/remotes/origin",), handle_path=tmp_path / "absent.txt"
    )
    assert "absent" in report["disclosed"]["handle_list"]
    assert report["disposition"] == "clean"


def test_unclassified_email_blocks_classified_email_does_not(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        {
            "a.md": b"contact noreply@github.com\n",
            "b.md": b"owner ceo@realemail.example-corp.com\n",
        },
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert report["disposition"] == "findings"
    assert "restricted:unclassified-email" in report["findings"]
    assert report["email_shape"]["classes"]["github-noreply"] == 1
    # The unclassified token's bytes never enter the report.
    assert "ceo@realemail.example-corp.com" not in str(report)


def test_no_refs_is_a_usage_error_not_a_green(tmp_path: Path) -> None:
    repo = tmp_path / "bare"
    repo.mkdir()
    _git(repo, "init", "-q")
    with pytest.raises(RuntimeError):
        hs.scan_history(repo, namespaces=("refs/remotes/origin",))


def test_token_sink_collects_tokens_for_the_reviewer_only(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, {"a.md": b"mailto noreply@github.com\n"})
    sink: dict[str, str] = {}
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",), token_sink=sink)
    assert sink == {"noreply@github.com": "github-noreply"}
    assert "noreply@github.com" not in str(report)  # never in the report


def _dispositions(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "dispositions.toml"
    p.write_text(f'schema = "{hs.DISPOSITIONS_SCHEMA}"\n{body}')
    return p


def test_disposition_exempt_clears_a_reviewed_false_positive(tmp_path: Path) -> None:
    import hashlib

    repo = _seed_repo(tmp_path, {"leak.py": f'KEY = "{SEEDED_AWS_KEY}"\n'.encode()})
    lit = hashlib.sha256(SEEDED_AWS_KEY.encode()).hexdigest()
    disp = _dispositions(
        tmp_path,
        f'[[disposition]]\nid="aws-example"\ndisposition="exempt"\n'
        f'justification="documented example key"\n'
        f'[disposition.match]\nliteral_sha256="{lit}"\n',
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",), dispositions_path=disp)
    assert report["disposition"] == "clean"
    assert report["dispositions"]["exempt"] == {"aws-example": 1}
    assert SEEDED_AWS_KEY not in str(report)


def test_disposition_disclosed_records_not_erases(tmp_path: Path) -> None:
    import hashlib

    repo = _seed_repo(tmp_path, {"x.md": b"contact someone@realemail-corp.com\n"})
    tok = hashlib.sha256(b"someone@realemail-corp.com").hexdigest()
    disp = _dispositions(
        tmp_path,
        f'[[disposition]]\nid="contact"\ndisposition="disclosed"\n'
        f'justification="a public contact"\n'
        f'[disposition.match]\ntoken_sha256="{tok}"\n',
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",), dispositions_path=disp)
    assert report["disposition"] == "clean"
    assert report["dispositions"]["disclosed"] == {"contact": 1}
    assert report["email_shape"]["unclassified_remaining"] == 0


def test_stale_disposition_fails_loud(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, {"a.py": b"x = 1\n"})
    disp = _dispositions(
        tmp_path,
        '[[disposition]]\nid="ghost"\ndisposition="exempt"\n'
        'justification="never fires"\n'
        '[disposition.match]\ntoken_sha256="deadbeef"\n',
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",), dispositions_path=disp)
    assert report["disposition"] == "findings"
    assert report["dispositions"]["stale"] == ["ghost"]


def test_secret_manager_name_and_command_values_are_not_credentials(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        {
            # Assembled so THIS file carries no SIG_* credential-shaped literal
            # (tests/connectors/test_secrets.py scans test files too).
            "a.md": b'`SIG_SAM_GOV_KEY = "' + b'sig-sam-gov-key"` - a name\n',
            "b.md": b'SIG_PG_PASSWORD="' + b'$(gcloud secrets versions access latest)"\n',
        },
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert report["disposition"] == "clean"
    assert "secret:sig-credential-literal" not in report["findings"]


def test_service_account_listing_without_private_key_is_not_a_finding(
    tmp_path: Path,
) -> None:
    repo = _seed_repo(
        tmp_path,
        {"service-accounts.json": b'[{"email": "svc@p.iam.gserviceaccount.com"}]\n'},
    )
    report = hs.scan_history(repo, namespaces=("refs/remotes/origin",))
    assert "path:service-account-key" not in report["findings"]
    # A listing carrying a private_key field IS a key file.
    repo2 = _seed_repo(
        tmp_path / "r2",
        {"service-accounts.json": b'{"type": "service_account", "private_key": "x"}\n'},
    )
    report2 = hs.scan_history(repo2, namespaces=("refs/remotes/origin",))
    assert "path:service-account-key" in report2["findings"]


def test_cli_clean_and_findings_exit_codes(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        {"leak.py": f'KEY = "{SEEDED_AWS_KEY}"\n'.encode()},
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "ci" / "history_scan.py"),
            "--root",
            str(repo),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "FINDINGS" in proc.stderr
    assert SEEDED_AWS_KEY not in proc.stderr and SEEDED_AWS_KEY not in proc.stdout
    proc2 = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "ci" / "history_scan.py"),
            "--root",
            str(repo),
            "--namespaces",
            "refs/remotes/missing",
        ],
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 2
