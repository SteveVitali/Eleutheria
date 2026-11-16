#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""redaction_guard.py — ``sig.redaction-guard/1`` (P37.61b; RULING E-1; ADR-178 /
SIG-PUB-002).

The fail-closed *reappearance guard* for the personal-handle re-key. The
existing ``handle_crawl_check.py`` intentionally counts-but-passes hits inside
the retained-history prefixes (``docs/build/runs/``, ``docs/build/pr/``,
``docs/build/reports/``, ``docs/tickets/``, …) — that classification kept the
retained-historical-record distinction meaningful under ADR-178 while the tip
stayed clean. RULING E-1 (GATE DECISIONS 2026-11-15;
``docs/build/readouts/RULINGS-2026-11-15.md``) rules that the
``15085e0a``-style reintroduction — four personal handles pasted back into six
retained-prefix files — may not recur: the tracked **tip** must carry zero
listed handles, **including** the previously-retained prefixes.

This guard is fail-closed on three legs, over every file ``git ls-files``
tracks at the scanned root:

  1. **handle reappearance** — any sha256-listed handle appearing anywhere in a
     tracked file's bytes (including glued inside a longer word, e.g.
     ``prefix-<handle>-suffix``) or in a tracked *path* fails. Comparison is by
     SHA-256 digest only: the committed policy
     (``record_policy/redaction_guard.json``) carries the 32 digests, and this
     tool never loads, prints, or requires the plaintext list.
  2. **``item_owner`` key, anywhere** — an ``item_owner`` object key in any
     tracked file fails (JSON ``"item_owner": …`` or a line-start
     ``item_owner = …`` / ``item_owner: …`` key in TOML/YAML-style data).
  3. **``owner``/``item_owner`` inside the declared sweep set** — the declared
     ArcGIS catalog-sweep / disposition files (and future files matching the
     declared globs) must carry neither an ``owner`` nor an ``item_owner``
     object key, anywhere in their JSON structure. This is *scoped* — per the
     ruling, the ``owner`` field of ``obligation-event/1`` rows is legitimate
     schema, so a global ``owner`` grep is explicitly not the check.

Output never leaks: violations are reported as counts plus file paths only —
never the matched strings — and exit status is the signal (0 clean, 1
violation, 2 tool/policy error). An optional ``--selfcheck`` cross-audits the
committed digest set against the gitignored plaintext list when it exists
locally (development aid; never required by CI).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "sig.redaction-guard/1"
DEFAULT_POLICY = Path(__file__).with_name("record_policy") / "redaction_guard.json"
DEFAULT_HANDLE_LIST = Path("docs/build/logs/next-phase/C3/personal_like_ids.txt")

# Same unreadable/generated skips as handle_crawl_check.py — nothing under a
# skip is tracked content the guard judges (docs/build/logs is gitignored).
SKIP_PREFIXES = (
    ".git/",
    "node_modules/",
    "web/dist/",
    ".venv/",
    "__pycache__/",
)

_WORD_RE = re.compile(rb"[A-Za-z0-9_]+")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _key_patterns(name: str) -> list[re.Pattern[bytes]]:
    """Byte patterns meaning *name* is used as an object/record key."""
    esc = re.escape(name.encode())
    return [
        re.compile(rb'"' + esc + rb'"\s*:'),  # JSON: "name": …
        re.compile(rb"^\s*" + esc + rb"\s*[:=]", re.M),  # line-start key (TOML/YAML)
    ]


def load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "sig.redaction-guard-policy/1":
        raise ValueError(f"{path}: unexpected schema {policy.get('schema')!r}")
    for digest in policy["handle_digests_sha256"]:
        if not _HEX_64.match(digest):
            raise ValueError(f"{path}: malformed digest {digest!r}")
    return policy


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    rels = [p.decode() for p in out.split(b"\0") if p]
    return sorted(rels)


def _iter_l_substrings(token: bytes, lengths: list[int]):
    for length in lengths:
        if length > len(token):
            continue
        for i in range(len(token) - length + 1):
            yield token[i : i + length]


def _handle_hits_in_bytes(data: bytes, digests: set[str], lengths: list[int]) -> int:
    """Count listed-handle occurrences in *data* via digest comparison only."""
    hits = 0
    token_hits: dict[bytes, int] = {}
    for match in _WORD_RE.finditer(data):
        token = match.group(0)
        cached = token_hits.get(token)
        if cached is None:
            cached = sum(
                1
                for sub in _iter_l_substrings(token, lengths)
                if hashlib.sha256(sub).hexdigest() in digests
            )
            token_hits[token] = cached
        hits += cached
    return hits


def _json_key_counts(obj) -> dict[str, int]:
    """Occurrence counts for every dict key anywhere in a JSON structure."""
    counts: dict[str, int] = {}
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, value in cur.items():
                counts[key] = counts.get(key, 0) + 1
                stack.append(value)
        elif isinstance(cur, list):
            stack.extend(cur)
    return counts


def scan(root: Path, rels: list[str], policy: dict) -> dict:
    """Run all three legs over *rels* under *root*; return the verdict dict."""
    digests = set(policy["handle_digests_sha256"])
    lengths = sorted(set(policy["handle_lengths"]))
    self_exempt = set(policy.get("self_exempt_paths", ()))

    declared_sweeps = set(policy["sweep_files"])
    sweep_globs = policy.get("sweep_globs", ())

    anywhere_patterns = {name: _key_patterns(name) for name in policy["forbidden_keys_anywhere"]}
    sweep_names = set(policy["forbidden_keys_in_sweeps"])
    sweep_patterns = {name: _key_patterns(name) for name in sweep_names}

    handle_hits: dict[str, int] = {}
    anywhere_hits: dict[str, int] = {}
    sweep_hits: dict[str, int] = {}
    unreadable: list[str] = []

    for rel in rels:
        if rel.startswith(SKIP_PREFIXES):
            continue
        is_self = rel in self_exempt
        is_sweep = rel in declared_sweeps or any(fnmatch.fnmatch(rel, glob) for glob in sweep_globs)

        # Leg 1 — handles (tracked paths count too: a path may carry a handle).
        path_hits = _handle_hits_in_bytes(rel.encode(), digests, lengths)
        data: bytes | None = None
        try:
            data = (root / rel).read_bytes()
        except OSError:
            unreadable.append(rel)
        body_hits = 0 if data is None else _handle_hits_in_bytes(data, digests, lengths)
        if path_hits + body_hits:
            handle_hits[rel] = path_hits + body_hits

        if is_self or data is None:
            continue

        # Leg 2 — globally-forbidden keys.
        for patterns in anywhere_patterns.values():
            n = sum(len(p.findall(data)) for p in patterns)
            if n:
                anywhere_hits[rel] = anywhere_hits.get(rel, 0) + n

        # Leg 3 — owner/item_owner keys inside the declared sweep set.
        if is_sweep:
            found = 0
            try:
                key_counts = _json_key_counts(json.loads(data))
                found = sum(key_counts.get(name, 0) for name in sweep_names)
            except ValueError:
                # Fail-closed: an unparseable declared sweep is scanned as
                # bytes for the key patterns instead of waved through.
                for patterns in sweep_patterns.values():
                    found += sum(len(p.findall(data)) for p in patterns)
            if found:
                sweep_hits[rel] = found

    violations = {
        "handle_reappearance": {
            "files": len(handle_hits),
            "hits": sum(handle_hits.values()),
            "paths": sorted(handle_hits),
        },
        "forbidden_key_anywhere": {
            "files": len(anywhere_hits),
            "hits": sum(anywhere_hits.values()),
            "paths": sorted(anywhere_hits),
        },
        "owner_field_in_sweep": {
            "files": len(sweep_hits),
            "hits": sum(sweep_hits.values()),
            "paths": sorted(sweep_hits),
        },
    }
    failed = any(v["files"] for v in violations.values()) or bool(unreadable)
    return {
        "schema": SCHEMA,
        "root": str(root),
        "tracked_files": len(rels),
        "handles_listed": len(digests),
        "verdict": "fail" if failed else "pass",
        "violations": violations,
        "unreadable_files": sorted(unreadable),
    }


def selfcheck(root: Path, policy: dict, list_path: Path) -> dict:
    """Cross-audit: the committed digest set must equal sha256(list lines)."""
    p = root / list_path
    if not p.is_file():
        return {"list": str(list_path), "present": False, "match": None}
    entries = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    digests = {hashlib.sha256(e.encode()).hexdigest() for e in entries}
    want = set(policy["handle_digests_sha256"])
    return {
        "list": str(list_path),
        "present": True,
        "entries": len(entries),
        "match": digests == want,
        "digest_only_in_policy": len(want - digests),
        "digest_only_in_list": len(digests - want),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
        help="committed sig.redaction-guard-policy/1 JSON (digests only)",
    )
    ap.add_argument("--json", type=Path, help="write the verdict JSON here")
    ap.add_argument(
        "--selfcheck",
        action="store_true",
        help="cross-audit the digest set against the gitignored plaintext "
        "list (development aid; never required by CI)",
    )
    args = ap.parse_args(argv)

    root = args.root.resolve()
    try:
        policy = load_policy(args.policy)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"redaction-guard: policy error: {exc}", file=sys.stderr)
        return 2

    if args.selfcheck:
        check = selfcheck(root, policy, DEFAULT_HANDLE_LIST)
        print(f"redaction-guard selfcheck: {json.dumps(check)}")
        if check["present"] and not check["match"]:
            print("redaction-guard: digest set does not match the local list")
            return 2

    try:
        rels = tracked_files(root)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"redaction-guard: cannot list tracked files: {exc}", file=sys.stderr)
        return 2

    report = scan(root, rels, policy)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    v = report["violations"]
    print(
        "redaction-guard: {verdict} — {files} tracked files scanned; "
        "handles {hf} files/{hh} hits; forbidden-key-anywhere {kf} files/{kh} "
        "hits; sweep owner-fields {sf} files/{sh} hits; unreadable {u}".format(
            verdict=report["verdict"],
            files=report["tracked_files"],
            hf=v["handle_reappearance"]["files"],
            hh=v["handle_reappearance"]["hits"],
            kf=v["forbidden_key_anywhere"]["files"],
            kh=v["forbidden_key_anywhere"]["hits"],
            sf=v["owner_field_in_sweep"]["files"],
            sh=v["owner_field_in_sweep"]["hits"],
            u=len(report["unreadable_files"]),
        )
    )
    for leg, body in v.items():
        for path in body["paths"]:
            print(f"  {leg}: {path}")
    return 1 if report["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
