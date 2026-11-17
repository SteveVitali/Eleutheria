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
import re
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


def _head(root: pathlib.Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()


T_REPAIR = "2026-10-17T00:00:00Z"  # a repair commit after activation
CLAIM = "It is also deployed."


def _carried_repo(tmp_path: pathlib.Path, readded: str = CLAIM) -> tuple[pathlib.Path, str, str]:
    """A pre-activation claim (source), dropped by a later commit, then re-added
    by a repair commit after activation — `git blame` attributes the re-added
    line to the repair. Returns (root, source sha, repair sha)."""
    root = _repo(tmp_path)
    _write(root, "README.md", f"Intro.\n{CLAIM}\n")
    _commit(root, "2026-09-24T00:00:00Z")
    _bind(root)
    source = _head(root)
    _write(root, "README.md", "Intro.\n")
    _commit(root, T_CLAIM, "drop (a bad merge resolution)")
    _write(root, "README.md", f"Intro.\n{readded}\n")
    _commit(root, T_REPAIR, "repair: re-add the dropped record")
    return root, source, _head(root)


def _list_carried(root: pathlib.Path, commit: str, source: str) -> None:
    _write(
        root,
        POLICY_REL,
        POLICY + f'\n[[carried]]\ncommit = "{commit}"\nsource = "{source}"\nreason = "fixture"\n',
    )
    _commit(root, "2026-10-17T01:00:00Z", "list the carry")


def test_carried_readd_without_entry_fails(tmp_path) -> None:
    root, _source, _repair = _carried_repo(tmp_path)
    assert _corpus(root) == 1


def test_carried_readd_with_entry_passes(tmp_path, capsys) -> None:
    root, source, repair = _carried_repo(tmp_path)
    _list_carried(root, repair, source)
    assert clc.run(root, "corpus", spec=None, json_out=None, verbose=True) == 0
    out = capsys.readouterr().out
    assert "carried 1" in out
    assert f"carried README.md:2 ({repair[:8]} from {source[:8]})" in out


def test_carried_entry_never_exempts_new_text(tmp_path) -> None:
    root, source, repair = _carried_repo(tmp_path, readded="It is now publicly deployed.")
    _list_carried(root, repair, source)
    assert _corpus(root) == 1


def test_carried_entry_needs_pre_activation_source(tmp_path) -> None:
    root = _repo(tmp_path)
    _bind(root)
    _write(root, "README.md", f"Intro.\n{CLAIM}\n")
    _commit(root, T_CLAIM)  # the source line itself postdates activation
    source = _head(root)
    _write(root, "README.md", "Intro.\n")
    _commit(root, "2026-10-16T12:00:00Z")
    _write(root, "README.md", f"Intro.\n{CLAIM}\n")
    _commit(root, T_REPAIR)
    _list_carried(root, _head(root), source)
    assert _corpus(root) == 1


def test_carried_entry_needs_ancestor_source(tmp_path) -> None:
    root, _source, repair = _carried_repo(tmp_path)
    home = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(root, "checkout", "-q", "--orphan", "elsewhere")
    _write(root, "README.md", f"{CLAIM}\n")
    _commit(root, "2026-09-20T00:00:00Z")
    unrelated = _head(root)
    _git(root, "checkout", "-q", "-f", home)
    _list_carried(root, repair, unrelated)
    assert _corpus(root) == 1


def test_malformed_carried_entry_is_a_usage_error(tmp_path) -> None:
    root = _repo(tmp_path)
    _write(
        root,
        POLICY_REL,
        POLICY + '\n[[carried]]\ncommit = "abc123"\nsource = "def456"\n',
    )
    _commit(root, T_BIND)
    _write(root, "README.md", "Intro.\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 2


def test_committed_tree_passes() -> None:
    # the real repo's corpus is consistent — every claim either predates the
    # binding or cites its record.
    root = pathlib.Path(__file__).resolve().parents[3]
    assert clc.run(root, "corpus", spec=None, json_out=None, verbose=False) == 0


# ── P37.61d / RULING E-3 (ADR-251): the corpus is scoped to public + readiness
# surfaces. The lint's guarantee is unchanged — no unevidenced production-state
# assertion on a public or readiness surface — but the build-memory records
# under `docs/build/**` and the ticket ledger under `docs/tickets/**` leave the
# corpus: their live-leg prose is already governed by the run-ledger and
# live-leg rules. The fixtures below are the 23 false positives recovered
# verbatim from committed history
# (`docs/build/fixtures/live_claims_false_positives.json`); each sits on the
# path that recorded it. The fixture repos below load the SHIPPED policy so the
# same assert/negate vocabulary + corpus globs are exercised.

_REPO = _HERE.parents[2]
_REAL_POLICY = (_REPO / POLICY_REL).read_text()
_FP_FIXTURES = json.loads(
    (_REPO / "docs/build/fixtures/live_claims_false_positives.json").read_text()
)["fixtures"]


def _bind_real(root: pathlib.Path) -> None:
    """Land the shipped policy (real vocabulary + rescoped corpus) at T_BIND."""
    _write(root, POLICY_REL, _REAL_POLICY)
    _commit(root, T_BIND)


def test_corpus_scope_is_public_and_readiness_only() -> None:
    """AC4 — the shipped corpus globs cover public/readiness surfaces and no
    build-memory or ticket-ledger path; the range leg reads the same list."""
    policy, errs = clc.load_policy(_REPO)
    assert not errs
    corpus_re = clc._corpus_regex(policy["surfaces"]["corpus"])
    covered = [
        "README.md",
        "db/README.md",
        "docs/README.md",
        "docs/build/OPERATIONAL_READINESS.md",  # the readiness carve-out
        "docs/ops/RUNBOOK.md",
    ]
    for rel in covered:
        assert corpus_re.match(rel), f"{rel} left the judged surfaces"
        assert (_REPO / rel).is_file(), f"{rel} globbed but absent on disk"
    uncovered = [
        "docs/build/LEDGER.md",
        "docs/build/runs/P37.61d.md",
        "docs/build/reports/obligations/events.jsonl",
        "docs/build/reports/memory-repair/x.md",
        "docs/build/fixtures/live_claims_false_positives.json",
        "docs/adr/README.md",  # generated index — regenerated prose, not authored
        "docs/tickets/DEFERRALS.md",
        "docs/tickets/489d_P37.61d__live-claims-rescope.md",
    ]
    for rel in uncovered:
        assert not corpus_re.match(rel), f"{rel} still judged"
    files = clc._glob_files(_REPO, policy["surfaces"]["corpus"])
    assert files, "the shipped corpus must not be vacuous"


def test_historical_false_positives_all_pass(tmp_path) -> None:
    """All 23 recovered false positives exit clean: each sits on a path the
    rescoped corpus never judges."""
    assert len(_FP_FIXTURES) == 23
    root = _repo(tmp_path)
    _write(root, "README.md", "Nothing is deployed yet.\n")  # non-vacuous corpus
    _bind_real(root)
    for fx in _FP_FIXTURES:
        _write(root, fx["path"], fx["line"] + "\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 0


def test_range_leg_ignores_build_memory(tmp_path) -> None:
    """The range leg shares the corpus path semantics: added claims under
    `docs/build/**` / `docs/tickets/**` are not judged."""
    root = _repo(tmp_path)
    _write(root, "README.md", "Clean.\n")
    _bind_real(root)
    base = _head(root)
    for fx in _FP_FIXTURES:
        _write(root, fx["path"], fx["line"] + "\n")
    _commit(root, T_CLAIM)
    assert clc.run(root, "range", spec=f"{base}...{_head(root)}", json_out=None, verbose=False) == 0


def test_false_positive_lines_remain_claim_shaped() -> None:
    """The fixtures' recorded claim-shape flags still match the shipped
    vocabulary — the lines are genuine claim-shaped text, just off-corpus."""
    policy, errs = clc.load_policy(_REPO)
    assert not errs
    assert_res = [re.compile(p, re.I) for p in policy["claims"]["assert"]]
    negate_res = [re.compile(p, re.I) for p in policy["claims"]["negate"]]
    for fx in _FP_FIXTURES:
        claims = clc._classify(fx["line"].splitlines(), assert_res, negate_res)
        assert bool(claims) == fx["still_claim_shaped"], fx["id"]


def test_claim_shaped_false_positives_fire_on_public_surfaces(tmp_path) -> None:
    """SIG-MEM-011 is intact: the same text that fired on build memory still
    fails when it lands on a public surface — the guarantee moved, not the
    vocabulary."""
    root = _repo(tmp_path)
    _write(root, "README.md", "Clean.\n")
    _bind_real(root)
    shaped = [fx for fx in _FP_FIXTURES if fx["still_claim_shaped"]]
    assert shaped  # the fixture set would be vacuous otherwise
    _write(root, "README.md", "".join(fx["line"] + "\n" for fx in shaped))
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_unevidenced_production_assertions_fail_on_held_surfaces(tmp_path) -> None:
    """Positive fixtures: genuine unevidenced production-state assertions on
    each held surface family still fail."""
    root = _repo(tmp_path)
    _write(root, "README.md", "Clean.\n")
    _bind_real(root)
    _write(root, "README.md", "The hosted deployment is live.\n")
    _write(root, "docs/build/OPERATIONAL_READINESS.md", "It is publicly deployed.\n")
    _write(root, "docs/ops/RUNBOOK.md", "The production serve is operational.\n")
    _commit(root, T_CLAIM)
    assert _corpus(root) == 1


def test_range_leg_still_judges_public_surface_claims(tmp_path) -> None:
    """The range leg keeps enforcing the held surfaces: an added claim on the
    readiness carve-out fails."""
    root = _repo(tmp_path)
    _write(root, "README.md", "Clean.\n")
    _bind_real(root)
    base = _head(root)
    _write(root, "docs/build/OPERATIONAL_READINESS.md", "It is live.\n")
    _commit(root, T_CLAIM)
    assert clc.run(root, "range", spec=f"{base}...{_head(root)}", json_out=None, verbose=False) == 1
