#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_live_claims.py`` — the SIG-MEM-011 live-claim binding lint
(P35.3, B4 G10).

Each case is exercised on a small **real git repo** under ``tmp_path`` (the
binding judges claims by their blamed commit time, so fixtures commit with
fixed ``GIT_COMMITTER_DATE``s): pre-binding claims are grandfathered, a claim
committed at/after activation must cite a ``sig.probe-run/1`` record ≤ 24 h
old at its commit, and the range leg judges every claim a change adds.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_live_claims", _HERE / "check_live_claims.py")
clc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(clc)

T_BIND = "2026-10-15T00:00:00Z"  # the binding lands
T_CLAIM = "2026-10-16T00:00:00Z"  # a claim committed after it
T_RECORD = "2026-10-15T23:00:00Z"  # a probe record 1 h before the claim
T_STALE = "2026-10-14T12:00:00Z"  # a record > 24 h before the claim

POLICY_REL = "docs/build/tools/record_policy/live_claims.toml"
POLICY = """schema = "sig.live-claim-policy/1"

[surfaces]
corpus = ["README.md", "docs/build/**/*.md"]

[claims]
assert = ['\\bdeployed\\b', '\\blive\\b', '\\bpublicly\\b']
negate = ['\\bno\\b', '\\bnot\\b', '\\buntil\\b', '\\bdeferred\\b', '\\bstaging\\b', '\\byet\\b']

[citation]
committed_glob = "docs/build/reports/probes/*.json"
remote_scheme = 'gs://'
remote_sha_re = 'sha256:([0-9a-f]{64})'
remote_stamp_re = 'generated_at:([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)'
freshness_hours = 24
skew_minutes = 10

[context]
window = "paragraph"

[activation]
self = "docs/build/tools/record_policy/live_claims.toml"
"""


def _git(root: pathlib.Path, *args: str, when: str | None = None) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
    )
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)


def _write(root: pathlib.Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _commit(root: pathlib.Path, when: str, msg: str = "c") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg, when=when)


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    return root


def _bind(root: pathlib.Path) -> None:
    """Land the binding: policy committed at T_BIND."""
    _write(root, POLICY_REL, POLICY)
    _commit(root, T_BIND)


def _record(root: pathlib.Path, name: str = "probe.json", gen: str = T_RECORD) -> str:
    rel = f"docs/build/reports/probes/{name}"
    _write(
        root,
        rel,
        json.dumps(
            {
                "version": "sig.probe-run/1",
                "generated_at": gen,
                "probe": "fixture-sentinel",
                "checks": {"sentinels": {"verdict": "pass"}},
                "overall": "pass",
            }
        ),
    )
    return rel


def _corpus(root: pathlib.Path) -> int:
    return clc.run(root, "corpus", spec=None, json_out=None, verbose=False)


def test_grandfathered_claim_passes(tmp_path, capsys) -> None:
    root = _repo(tmp_path)
    _write(root, "README.md", "It is also deployed.\n")
    _commit(root, "2026-09-24T00:00:00Z")  # before the binding exists
    _bind(root)
    assert _corpus(root) == 0
    out = capsys.readouterr().out
    assert "grandfathered 1" in out


def test_uncited_claim_after_activation_fails(tmp_path, capsys) -> None:
    root = _repo(tmp_path)
    _bind(root)
    _write(root, "README.md", "It is also deployed.\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1
    out = capsys.readouterr().out
    assert "VIOLATION README.md:1" in out
    assert "no probe-run/1 citation" in out


def test_cited_claim_passes(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    rec = _record(root)
    _write(root, "README.md", f"It is also deployed ({rec}).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 0


def test_stale_record_fails(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    rec = _record(root, gen=T_STALE)
    _write(root, "README.md", f"It is live ({rec}).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_absent_record_fails(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    _write(root, "README.md", "It is live (docs/build/reports/probes/nope.json).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_digest_mismatch_fails(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    rec = _record(root)
    _write(root, "README.md", f"It is live ({rec} sha256:{'0' * 64}).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_declared_digest_passes(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    rec = _record(root)
    # write the claim citing the record, commit, then compute the digest and
    # re-commit — the digest cites the committed record bytes.
    import hashlib

    digest = hashlib.sha256((root / rec).read_bytes()).hexdigest()
    _write(root, "README.md", f"It is live ({rec} sha256:{digest}).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 0


def test_remote_citation_form(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    sha = "a" * 64
    _write(
        root,
        "README.md",
        f"It is live (gs://sig-probes/run.json sha256:{sha} generated_at:{T_RECORD}).\n",
    )
    _commit(root, T_CLAIM)
    assert _corpus(root) == 0


def test_remote_citation_needs_stamp_and_digest(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    _write(root, "README.md", "It is live (gs://sig-probes/run.json).\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_negated_claim_not_flagged(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    _write(
        root,
        "README.md",
        "Nothing is deployed yet; the live leg is deferred until it runs.\n",
    )
    _commit(root, T_CLAIM)
    assert _corpus(root) == 0


def test_range_mode_judges_added_claims(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    base = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    _write(root, "docs/build/OPERATIONAL_READINESS.md", "It is live.\n")
    _commit(root, T_CLAIM)
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    assert clc.run(root, "range", spec=f"{base}...{head}", json_out=None, verbose=False) == 1


def test_range_mode_cited_claim_passes(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    base = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    rec = _record(root)
    _write(root, "README.md", f"It is live ({rec}).\n")
    _commit(root, T_CLAIM)
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    assert clc.run(root, "range", spec=f"{base}...{head}", json_out=None, verbose=False) == 0


def test_vacuous_corpus_exits_3(tmp_path, capsys) -> None:
    root = _repo(tmp_path)
    _bind(root)
    # policy landed but no corpus surface exists
    assert _corpus(root) == 3
    assert "VACUOUS" in capsys.readouterr().err


def test_committed_tree_passes() -> None:
    # the real repo's corpus is consistent — every claim either predates the
    # binding or cites its record.
    root = pathlib.Path(__file__).resolve().parents[3]
    assert clc.run(root, "corpus", spec=None, json_out=None, verbose=False) == 0
