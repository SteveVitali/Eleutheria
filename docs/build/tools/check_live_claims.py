#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""check_live_claims.py — the SIG-MEM-011 live-claim binding lint (P35.3, B4 G10).

A committed build-memory / readiness / README statement that **asserts
production state** must cite a ``sig.probe-run/1`` record (id, time, result,
output digest) no older than 24 h at its commit — the record resolvable under
``docs/build/reports/probes/`` or at a cited digested ``gs://`` path. The lint
verifies the **citation form** — never the truth of the underlying probe (B4
§2.3 item 8 carried explicitly; SIG-OPS-011 owns the probe). Stdlib only::

    python3 docs/build/tools/check_live_claims.py corpus [--root ROOT] [--json PATH]
    python3 docs/build/tools/check_live_claims.py range --range BASE...HEAD [--json PATH]

Two legs:

* **corpus** — every declared corpus surface (`live_claims.toml`
  `[surfaces].corpus`) is segmented into statements; each statement is
  classified against the `[claims]` assert/negate vocabularies. A statement
  with an assert hit and no negate hit is a CLAIM. Claims on lines whose
  blamed commit predates the policy's own introduction commit are
  ``grandfathered`` — *exempt by date, listed* (the ADR-199 precedent; the
  binding did not exist to cite). Claims at/after activation — including any
  uncommitted/dirty line — must carry a resolvable citation in their
  paragraph window.
* **range** — `git diff` of the change restricted to corpus surfaces; every
  claim the change *adds* must cite (commit time = the range head's
  committer time).

Citation grammar (declared in `[citation]`): a committed path under
`committed_glob` that exists, parses as ``sig.probe-run/1`` (version,
generated_at, checks, overall — `probe` names the id; the record's sha256 is
the output digest), optionally followed by `(sha256:<64hex>)` which must
equal the record bytes' digest; or a remote ``gs://`` path carrying
`sha256:<64hex>` and `generated_at:<ISO>` inline (the digest binds the bytes;
the stamp is what the freshness check reads — remote bytes are never fetched).
Freshness: `generated_at` within `freshness_hours` before the claim's commit
time (never materially after — `skew_minutes`).

Every leg reports candidates/evaluated; a non-empty candidate set
evaluated-to-zero exits 3 (SIG-ENG-042 — never a vacuous green).
Exit codes: 0 OK · 1 violations · 2 usage/input error · 3 vacuous.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
POLICY = "docs/build/tools/record_policy/live_claims.toml"
PROBE_RECORD_VERSION = "sig.probe-run/1"

_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_COMMENT_RE = re.compile(r"<!--.*?-->")
_FENCE_RE = re.compile(r"^\s*```")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s")
_BLANK_RE = re.compile(r"^\s*$")
# A statement boundary inside a line: a table cell, a semicolon clause, or a
# sentence end. The claim context is the segment between boundaries.
_SEGMENT_SPLIT_RE = re.compile(r"[;|]|\.(?:\s|$)")
# Committed-record citation token inside the citation window.
_COMMITED_CITE_RE = re.compile(
    r"(docs/build/reports/probes/[A-Za-z0-9._/-]+\.json)"
    r"(?:[^\n]{0,80}?\(?\s*sha256:([0-9a-f]{64})\s*\)?)?"
)
_ZERO_SHA = "0" * 40


def _git(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git_ts(root: pathlib.Path, rev: str) -> int | None:
    out = _git(root, "show", "-s", "--format=%ct", rev)
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip())
    except ValueError:
        return None


def _activation_ts(root: pathlib.Path, policy_rel: str) -> int | None:
    """The committer time of the commit that introduced the policy file —
    the binding's activation; claims committed before it are grandfathered.
    An uncommitted policy file (a pre-commit local run) activates *now*: every
    committed line predates the binding, while dirty/uncommitted lines —
    which blame as not-yet-committed, i.e. 'now' — are still judged."""
    out = _git(
        root,
        "log",
        "--diff-filter=A",
        "-1",
        "--format=%ct",
        "--",
        policy_rel,
    )
    if out.returncode == 0 and out.stdout.strip():
        try:
            return int(out.stdout.strip())
        except ValueError:
            pass
    return int(datetime.now(UTC).timestamp())


def _file_latest_ts(root: pathlib.Path, rel: str) -> int | None:
    out = _git(root, "log", "-1", "--format=%ct", "--", rel)
    if out.returncode == 0 and out.stdout.strip():
        try:
            return int(out.stdout.strip())
        except ValueError:
            pass
    return None


def _blame_line_ts(root: pathlib.Path, rel: str) -> dict[int, int]:
    """line-no → committer-time; dirty lines blame as _ZERO_SHA → 'now'."""
    out = _git(root, "blame", "--line-porcelain", "--", rel)
    ts: dict[int, int] = {}
    if out.returncode != 0:
        return ts
    line_no = 0
    pending_zero = False
    now = int(datetime.now(UTC).timestamp())
    for raw in out.stdout.splitlines():
        m = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", raw)
        if m:
            line_no = int(m.group(2))
            pending_zero = m.group(1) == _ZERO_SHA
            continue
        if raw.startswith("committer-time "):
            try:
                ts[line_no] = now if pending_zero else int(raw.split()[1])
            except ValueError:
                pass
    return ts


def _head_of_range(spec: str) -> str:
    for sep in ("...", ".."):
        if sep in spec:
            return spec.split(sep, 1)[1]
    return spec


def _added_lines(root: pathlib.Path, spec: str) -> dict[str, list[tuple[int, str]]]:
    """file → [(new-line-no, text)] for `+` lines of `git diff spec`."""
    out = _git(root, "diff", "--unified=0", "--no-color", spec)
    if out.returncode != 0:
        return {}
    added: dict[str, list[tuple[int, str]]] = {}
    cur: str | None = None
    new_no = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw in out.stdout.splitlines():
        if raw.startswith("+++ b/"):
            cur = raw[len("+++ b/") :]
            added.setdefault(cur, [])
            continue
        if raw.startswith("+++ ") or raw.startswith("--- "):
            continue
        m = hunk_re.match(raw)
        if m:
            new_no = int(m.group(1))
            continue
        if cur is None:
            continue
        if raw.startswith("+"):
            added[cur].append((new_no, raw[1:]))
            new_no += 1
        elif raw.startswith("-"):
            continue
        else:
            new_no += 1
    return added


def _glob_files(root: pathlib.Path, patterns: list[str]) -> list[pathlib.Path]:
    seen: set[pathlib.Path] = set()
    for pat in patterns:
        for p in sorted(root.glob(pat)):
            if p.is_file() and p not in seen:
                seen.add(p)
    return sorted(seen)


def _segments(line: str) -> list[str]:
    """The statement segments of one line, code spans and comments stripped."""
    line = _COMMENT_RE.sub(" ", line)
    line = _CODE_SPAN_RE.sub(" ", line)
    return [s.strip() for s in _SEGMENT_SPLIT_RE.split(line) if s.strip()]


def _classify(
    lines: list[str],
    assert_res: list[re.Pattern[str]],
    negate_res: list[re.Pattern[str]],
) -> list[tuple[int, str]]:
    """[(line_no, segment)] of candidate claims — an assert hit whose segment
    carries no negation. Fenced code blocks are skipped whole."""
    claims: list[tuple[int, str]] = []
    fenced = False
    for n, raw in enumerate(lines, 1):
        if _FENCE_RE.match(raw):
            fenced = not fenced
            continue
        if fenced:
            continue
        for seg in _segments(raw):
            if not any(rx.search(seg) for rx in assert_res):
                continue
            if any(rx.search(seg) for rx in negate_res):
                continue
            claims.append((n, seg))
    return claims


def _window(lines: list[str], line_no: int) -> str:
    """The citation window: the containing markdown paragraph (the maximal
    contiguous run of non-blank, non-heading lines holding the claim)."""
    lo = line_no - 1
    hi = line_no - 1
    while lo > 0 and not (_BLANK_RE.match(lines[lo - 1]) or _HEADING_RE.match(lines[lo - 1])):
        lo -= 1
    while hi < len(lines) - 1 and not (
        _BLANK_RE.match(lines[hi + 1]) or _HEADING_RE.match(lines[hi + 1])
    ):
        hi += 1
    return "\n".join(lines[lo : hi + 1])


def _parse_iso(stamp: str) -> int | None:
    try:
        return int(datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())
    except ValueError:
        return None


def _check_citation(
    root: pathlib.Path,
    window: str,
    commit_ts: int,
    policy: dict,
) -> tuple[bool, str]:
    """Does the window carry a resolvable, fresh probe-run citation?"""
    cit = policy["citation"]
    fresh = timedelta(hours=int(cit.get("freshness_hours", 24)))
    skew = timedelta(minutes=int(cit.get("skew_minutes", 10)))
    # committed-path form — resolvable bytes, the strongest citation.
    for m in _COMMITED_CITE_RE.finditer(window):
        rel, declared_sha = m.group(1), m.group(2)
        path = root / rel
        if not path.is_file():
            return False, f"citation {rel} names no committed record"
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, f"citation {rel} does not parse as JSON"
        if rec.get("version") != PROBE_RECORD_VERSION:
            return False, f"citation {rel} is not {PROBE_RECORD_VERSION}"
        for key in ("probe", "generated_at", "checks", "overall"):
            if key not in rec:
                return False, f"citation {rel} lacks {key}"
        gen = _parse_iso(str(rec["generated_at"]))
        if gen is None:
            return False, f"citation {rel} generated_at is not date -u ISO"
        if gen > commit_ts + skew.total_seconds():
            return False, f"citation {rel} postdates the claim's commit"
        if gen < commit_ts - fresh.total_seconds():
            return False, f"citation {rel} is older than {fresh} at the claim's commit"
        if declared_sha is not None:
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            if got != declared_sha:
                return False, f"citation {rel} digest {declared_sha[:12]}… != record bytes"
        return True, f"cites {rel}"
    # remote digested form — gs:// + sha256 + generated_at inline; the bytes
    # are never fetched (read-only form check; the digest binds them).
    remote_scheme = cit.get("remote_scheme", "gs://")
    if remote_scheme in window:
        sha_m = re.search(cit["remote_sha_re"], window)
        stamp_m = re.search(cit["remote_stamp_re"], window)
        if sha_m is None or stamp_m is None:
            return (
                False,
                f"remote citation lacks {'sha256' if sha_m is None else 'generated_at'} inline",
            )
        gen = _parse_iso(stamp_m.group(1))
        if gen is None:
            return False, "remote citation generated_at is not date -u ISO"
        if gen > commit_ts + skew.total_seconds():
            return False, "remote citation postdates the claim's commit"
        if gen < commit_ts - fresh.total_seconds():
            return False, "remote citation is stale at the claim's commit"
        return True, "cites digested remote record (form-checked)"
    return False, "no probe-run/1 citation in the claim's paragraph"


def load_policy(root: pathlib.Path) -> tuple[dict, list[str]]:
    path = root / POLICY
    errs: list[str] = []
    if not path.is_file():
        return {}, [f"policy absent: {POLICY}"]
    try:
        pol = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        return {}, [f"policy unreadable: {e}"]
    if pol.get("schema") != "sig.live-claim-policy/1":
        errs.append(f"policy schema {pol.get('schema')!r} != 'sig.live-claim-policy/1'")
    surfaces = pol.get("surfaces", {}).get("corpus")
    if not isinstance(surfaces, list) or not surfaces:
        errs.append("policy [surfaces].corpus must be a non-empty list")
    claims = pol.get("claims", {})
    for key in ("assert", "negate"):
        if not isinstance(claims.get(key), list) or not claims[key]:
            errs.append(f"policy [claims].{key} must be a non-empty list")
    cit = pol.get("citation", {})
    for key in ("committed_glob", "remote_sha_re", "remote_stamp_re"):
        if not cit.get(key):
            errs.append(f"policy [citation].{key} is required")
    return pol, errs


def _report(result: dict, verbose: bool) -> None:
    print(
        f"check_live_claims {result['mode']}: "
        f"files {result['files']} · segments {result['segments']} · "
        f"claims {result['claims']} · grandfathered {result['grandfathered']} · "
        f"cited {result['cited']} · violations {len(result['violations'])}"
    )
    for v in result["violations"]:
        print(f"  VIOLATION {v['file']}:{v['line']}: {v['reason']} — {v['segment'][:100]}")
    if result["grandfathered_list"] and verbose:
        for g in result["grandfathered_list"]:
            print(f"  grandfathered {g['file']}:{g['line']}: {g['segment'][:100]}")
    for w in result.get("warnings", []):
        print(f"  warning: {w}", file=sys.stderr)


def run(
    root: pathlib.Path,
    mode: str,
    *,
    spec: str | None,
    json_out: pathlib.Path | None,
    verbose: bool,
) -> int:
    policy, errs = load_policy(root)
    if errs:
        for e in errs:
            print(f"check_live_claims: {e}", file=sys.stderr)
        return 2
    assert_res = [re.compile(p, re.I) for p in policy["claims"]["assert"]]
    negate_res = [re.compile(p, re.I) for p in policy["claims"]["negate"]]
    activation = _activation_ts(root, policy["activation"]["self"])
    if activation is None:
        print("check_live_claims: cannot resolve activation commit time", file=sys.stderr)
        return 2

    result: dict = {
        "mode": mode,
        "files": 0,
        "segments": 0,
        "claims": 0,
        "grandfathered": 0,
        "cited": 0,
        "violations": [],
        "grandfathered_list": [],
        "warnings": [],
    }

    if mode == "corpus":
        files = _glob_files(root, policy["surfaces"]["corpus"])
        if not files:
            print("check_live_claims: VACUOUS — no corpus files matched", file=sys.stderr)
            return 3
        result["files"] = len(files)
        for path in files:
            rel = str(path.relative_to(root))
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            claims = _classify(lines, assert_res, negate_res)
            result["segments"] += sum(len(_segments(ln)) for ln in lines if not _FENCE_RE.match(ln))
            if not claims:
                continue
            latest = _file_latest_ts(root, rel)
            if latest is not None and latest < activation:
                # the file was last touched before the binding — every claim
                # in it predates the rule; no per-line blame needed.
                result["claims"] += len(claims)
                result["grandfathered"] += len(claims)
                result["grandfathered_list"] += [
                    {"file": rel, "line": n, "segment": s} for n, s in claims
                ]
                continue
            line_ts = _blame_line_ts(root, rel)
            for n, seg in claims:
                result["claims"] += 1
                ts = line_ts.get(n)
                if ts is None:
                    result["warnings"].append(f"{rel}:{n}: unblamable line — judged at HEAD time")
                    ts = _git_ts(root, "HEAD") or activation
                if ts < activation:
                    result["grandfathered"] += 1
                    result["grandfathered_list"].append({"file": rel, "line": n, "segment": seg})
                    continue
                ok, why = _check_citation(root, _window(lines, n), ts, policy)
                if ok:
                    result["cited"] += 1
                else:
                    result["violations"].append(
                        {"file": rel, "line": n, "segment": seg, "reason": why}
                    )
    else:  # range mode
        if not spec:
            print("check_live_claims: range mode needs --range BASE...HEAD", file=sys.stderr)
            return 2
        head = _head_of_range(spec)
        head_ts = _git_ts(root, head)
        if head_ts is None:
            print(f"check_live_claims: cannot resolve head {head!r}", file=sys.stderr)
            return 2
        added = _added_lines(root, spec)
        corpus_re = _corpus_regex(policy["surfaces"]["corpus"])
        offered = 0
        for rel, items in sorted(added.items()):
            if not corpus_re.search(rel):
                continue
            path = root / rel
            try:
                lines = (
                    path.read_text(encoding="utf-8", errors="replace").splitlines()
                    if path.is_file()
                    else [ln for _n, ln in items]
                )
            except OSError:
                lines = [ln for _n, ln in items]
            text_lines = lines if lines else [ln for _n, ln in items]
            for n, text in items:
                offered += 1
                for seg in _segments(text):
                    if not any(rx.search(seg) for rx in assert_res):
                        continue
                    if any(rx.search(seg) for rx in negate_res):
                        continue
                    result["claims"] += 1
                    win = _window(text_lines, min(n, len(text_lines))) if text_lines else seg
                    ok, why = _check_citation(root, win, head_ts, policy)
                    if ok:
                        result["cited"] += 1
                    else:
                        result["violations"].append(
                            {"file": rel, "line": n, "segment": seg, "reason": why}
                        )
        result["files"] = len(added)
        result["segments"] = offered
        if offered == 0:
            result["warnings"].append("no corpus-surface lines added in range — nothing to judge")

    result["grandfathered_list"] = result["grandfathered_list"][:60]
    _report(result, verbose)
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result["violations"]:
        return 1
    return 0


def _corpus_regex(patterns: list[str]) -> re.Pattern[str]:
    parts = []
    for pat in patterns:
        rx = re.escape(pat)
        # `**/` matches zero or more directories (pathlib semantics), a bare
        # `**` matches across separators, and `*` matches within one segment.
        rx = rx.replace(r"\*\*/", "(?:.*/)?")
        rx = rx.replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        parts.append(f"(?:{rx})")
    return re.compile(r"^(?:" + "|".join(parts) + r")$")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("corpus", "range"))
    ap.add_argument("--root", default=str(ROOT), help="repo root (fixture roots in tests)")
    ap.add_argument("--range", dest="spec", default=None, help="BASE...HEAD for range mode")
    ap.add_argument("--json", dest="json_out", default=None, help="write the detail JSON here")
    ap.add_argument("-v", "--verbose", action="store_true", help="list grandfathered claims")
    args = ap.parse_args(argv)
    return run(
        pathlib.Path(args.root).resolve(),
        args.mode,
        spec=args.spec,
        json_out=pathlib.Path(args.json_out) if args.json_out else None,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
