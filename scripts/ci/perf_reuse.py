#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.41a (D2): fixture-mode Lighthouse reuse (ADR-219).

A records-only push (docs/build minus docs/build/tools, docs/tickets,
docs/adr) cannot change the fixture-mode `Performance budgets` measurement.
`decide` answers `reuse` for a same-PR head only when a restored record
proves a prior same-PR pass carried the byte-identical non-records tree on
the same runner image — every other shape answers `run`, including any
exception. Reuse is a `ci-perf-reuse` notice, never a fresh measurement.
Commands: `fingerprint <rev>` (sha256 of non-records `ls-tree` entries) ·
`decide` (reads CI_* env; last stdout line `run`/`reuse`; exit 0) ·
`record` (writes nine `key=value` lines to `$CI_RECORD_OUT`; refuses with
exit 1 unless HEAD is a two-parent merge with a valid image) · `lint` /
`allow-check` (the web→records coupling lint over `perf_reuse_allow.txt`).
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "sig.perf-pass/1"
LANE = "web-perf-fixtures"
RECORD_KEYS = ("schema", "lane", "nonrecords", "pr", "head", "base", "run", "attempt", "image")
CACHE_PREFIX = "perf-pass-v1-"
ALLOW_FILE = Path("scripts/ci") / "perf_reuse_allow.txt"
_RES = {
    "schema": re.compile(r"sig\.perf-pass/1"),
    "lane": re.compile(r"web-perf-fixtures"),
    "nonrecords": re.compile(r"[0-9a-f]{64}"),
    "pr": re.compile(r"\d+"),
    "head": re.compile(r"[0-9a-f]{40}"),
    "base": re.compile(r"[0-9a-f]{40}"),
    "run": re.compile(r"\d+"),
    "attempt": re.compile(r"\d+"),
    "image": re.compile(r"[A-Za-z0-9]+-[0-9][0-9A-Za-z._]*"),
}
_GREP = re.compile(r'docs/(?:build|tickets|adr)/|["\']docs["\']')


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=_root(), check=True, capture_output=True)


def _is_records(path: str) -> bool:
    return (
        path.startswith("docs/tickets/")
        or path.startswith("docs/adr/")
        or (path.startswith("docs/build/") and not path.startswith("docs/build/tools/"))
    )


def fingerprint(rev: str) -> str:
    """SHA-256 of NUL-joined ``ls-tree -r -z`` entries outside records paths."""
    digest = hashlib.sha256()
    for entry in _git("ls-tree", "-r", "-z", "--full-tree", rev).stdout.split(b"\0"):
        if entry and not _is_records(
            entry.partition(b"\t")[2].decode("utf-8", "surrogateescape")
        ):
            digest.update(entry + b"\0")
    return digest.hexdigest()


def _has_link_or_gitlink() -> bool:
    """True when HEAD's tree holds any mode-120000 symlink or 160000 gitlink."""
    out = _git("ls-tree", "-r", "HEAD").stdout.decode("utf-8", "replace")
    return any(
        line.split("\t", 1)[0].split()[0] in ("120000", "160000")
        for line in out.splitlines()
    )


def _lint_hits() -> list[tuple[str, str]]:
    """Coupling-lint ``(path, stripped line)`` hits; lines whose every match
    is a ``docs/build/tools/…`` path are dropped (records-adjacent, not
    records)."""
    proc = _git(
        "grep", "-n", "-E", r'docs/(build|tickets|adr)/|["\']docs["\']',
        "HEAD", "--", "web", ":!web/package-lock.json",
    )
    hits: list[tuple[str, str]] = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        path, _, rest = line.partition(":")[2].partition(":")
        text = rest.partition(":")[2].strip()
        matches = list(_GREP.finditer(text))
        if matches and all(text[m.start() :].startswith("docs/build/tools/") for m in matches):
            continue
        hits.append((path, text))
    return hits


def _allow_rows() -> list[tuple[str, str]]:
    path = _root() / ALLOW_FILE
    if not path.is_file():
        return []
    return [
        (parts[0], parts[1])
        for raw in path.read_text(encoding="utf-8").splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
        for parts in [raw.strip().split("\t")]
        if len(parts) == 2
    ]


def _allow_problems() -> list[str]:
    """Strict shape check: each non-comment row is one tab, a ``web/``-rooted
    path, and non-empty line text."""
    path = _root() / ALLOW_FILE
    if not path.is_file():
        return [f"{ALLOW_FILE} is missing"]
    problems = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            problems.append(f"{ALLOW_FILE}:{lineno}: expected exactly one tab")
        elif not parts[0].startswith("web/") or not parts[1]:
            problems.append(f"{ALLOW_FILE}:{lineno}: not a web/-rooted path + text row")
    return problems


def _read_record(path: str) -> tuple[dict[str, str] | None, str]:
    """Strict nine-key ``key=value`` parse; ``(None, reason)`` on any deviation."""
    if not path or not Path(path).is_file():
        return None, "no restored record at CI_RECORD (cache miss)"
    text = Path(path).read_bytes().decode("utf-8")
    if "\r" in text or not text.endswith("\n"):
        return None, "record malformed (CR or missing final newline)"
    rows = [line.split("=", 1) for line in text.splitlines()]
    if len(rows) != len(RECORD_KEYS) or any(len(r) != 2 for r in rows):
        return None, "record malformed (wrong line count or non key=value line)"
    record = dict(rows)
    if set(record) != set(RECORD_KEYS):
        return None, "record keys are not exactly the required nine"
    bad = [k for k in RECORD_KEYS if not _RES[k].fullmatch(record[k])]
    if bad:
        return None, f"record field(s) fail their regex: {', '.join(bad)}"
    return record, ""


def _notice(kind: str, reason: str) -> None:
    print(f"::notice title=ci-perf-{kind}::{reason}")
    dest = os.environ.get("GITHUB_STEP_SUMMARY")
    if dest:
        try:
            with open(dest, "a", encoding="utf-8") as handle:
                handle.write(f"- perf reuse: `{kind}` — {reason}\n")
        except OSError:
            pass


def _run(reason: str) -> int:
    _notice("run", reason)
    print("run")
    return 0


def cmd_decide() -> int:
    """Answer `reuse` only when every contract condition holds; else `run`."""
    try:
        env = os.environ
        if env.get("CI_EVENT_NAME") != "pull_request":
            return _run(f"event `{env.get('CI_EVENT_NAME') or 'unset'}` is not pull_request")
        repo, head_repo = env.get("CI_REPOSITORY", ""), env.get("CI_HEAD_REPO", "")
        if not repo or not head_repo or repo != head_repo:
            return _run("forked or missing head repository — no secrets, no cache")
        fp = env.get("CI_FINGERPRINT", "")
        if not _RES["nonrecords"].fullmatch(fp):
            return _run("CI_FINGERPRINT is missing or not 64-hex")
        if fp != fingerprint("HEAD"):
            return _run("CI_FINGERPRINT does not match the fresh HEAD tree scan")
        record, why = _read_record(env.get("CI_RECORD", ""))
        if record is None:
            return _run(why)
        if record["nonrecords"] != fp:
            return _run("record nonrecords differs — the non-records tree changed")
        if record["pr"] != env.get("CI_PR_NUMBER", ""):
            return _run("record pr does not equal CI_PR_NUMBER")
        if _has_link_or_gitlink():
            return _run("HEAD holds a symlink or gitlink — tree scan unsafe")
        problems = _allow_problems()
        try:
            unknown = [h for h in _lint_hits() if h not in _allow_rows()]
        except Exception as exc:
            return _run(f"coupling lint errored: {exc!r}")
        if problems or unknown:
            path, text = unknown[0] if unknown else ("", "")
            return _run(f"coupling lint failed: {'; '.join(problems) or f'unaudited hit {path}: {text[:80]}'}")
        image = env.get("CI_IMAGE", "")
        if not _RES["image"].fullmatch(image):
            return _run("CI_IMAGE is missing or not ImageOS-ImageVersion")
        if record["image"] != image:
            return _run("runner image changed since the recorded pass")
        _notice("reuse", f"run {record['run']} head {record['head'][:7]}")
        print("reuse")
        return 0
    except Exception as exc:  # every other path fails closed
        return _run(f"unexpected error: {exc!r}")


def cmd_record() -> int:
    """Write the nine-line record to ``$CI_RECORD_OUT``; refuse with exit 1
    (and write nothing) when HEAD is not a two-parent merge or a field fails
    its regex."""
    try:
        parents = [
            line.split()[1]
            for line in _git("cat-file", "-p", "HEAD").stdout.decode().splitlines()
            if line.startswith("parent ")
        ]
        if len(parents) != 2:
            print("perf_reuse record: HEAD does not have exactly two parents — refuse", file=sys.stderr)
            return 1
        dest = os.environ.get("CI_RECORD_OUT", "")
        record = {
            "schema": SCHEMA, "lane": LANE,
            "nonrecords": fingerprint("HEAD"),
            "pr": os.environ.get("CI_PR_NUMBER", ""),
            "head": parents[1], "base": parents[0],
            "run": os.environ.get("GITHUB_RUN_ID", ""),
            "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "image": os.environ.get("CI_IMAGE", ""),
        }
        bad = [k for k in RECORD_KEYS if not _RES[k].fullmatch(record[k])]
        if not dest or bad:
            print(f"perf_reuse record: {'CI_RECORD_OUT unset' if not dest else f'invalid field(s) {bad}'} — refuse", file=sys.stderr)
            return 1
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text("".join(f"{k}={record[k]}\n" for k in RECORD_KEYS))
        print(f"perf_reuse record: wrote {dest} for head {record['head'][:12]}")
        return 0
    except Exception as exc:
        print(f"perf_reuse record: failed ({exc!r}) — no record written", file=sys.stderr)
        return 1


def cmd_lint() -> int:
    problems = _allow_problems()
    for problem in problems:
        print(f"perf_reuse lint: {problem}", file=sys.stderr)
    try:
        hits, allow = _lint_hits(), set(_allow_rows())
    except Exception as exc:
        print(f"perf_reuse lint: coupling scan failed: {exc}", file=sys.stderr)
        return 2
    unknown = 0
    for path, text in hits:
        if (path, text) not in allow:
            unknown += 1
            print(f"perf_reuse lint: unaudited coupling hit {path}: {text[:80]}", file=sys.stderr)
    for path, text in allow - set(hits):
        print(f"::notice title=ci-perf-lint::stale allow-list row {path}: {text[:60]}")
    return 2 if (unknown or problems) else 0


def main(argv: list[str] | None = None) -> int:
    commands = {"fingerprint", "decide", "record", "lint", "allow-check"}
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in commands or len(args) > 2 or (len(args) == 2 and args[0] != "fingerprint"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if args[0] == "fingerprint":
            print(fingerprint(args[1]))
            return 0
        if args[0] == "decide":
            return cmd_decide()
        if args[0] == "record":
            return cmd_record()
        if args[0] == "lint":
            return cmd_lint()
        problems = _allow_problems()
        for problem in problems:
            print(f"perf_reuse allow-check: {problem}", file=sys.stderr)
        return 2 if problems else 0
    except Exception as exc:  # fails closed (nonzero) on every command
        print(f"perf_reuse: {exc!r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
