#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OM-01 commit-trailer check — `trailer-check/1` (Round 11 Stage B, SEED-02b; plan §3.3 OM-01, A-21).

Commits keep the operator's name as author (A-21), so the harness that wrote a commit is recorded only
in its trailers. This check fails a change (a PR range) that contains an **untrailered agent commit**:
every commit must either carry a recognised harness trailer or be an operator commit.

**Trailer grammar** (plan §3.3, S6R-10). Trailers are read from the message's **final paragraph** —
leniently, line by line, because Devin writes `Generated with [Devin](https://devin.ai)` directly above
its `Co-Authored-By:` line with no blank line, which git's own trailer parser rejects. A trailer quoted
in the body does not count. Keys are case-insensitive. Any one recognised harness trailer passes:

- `Co-Authored-By: Claude <model> <noreply@anthropic.com>` — Claude Code, e.g. the planning and seed
  commits' `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; model id = the slug of the name
  (`claude-opus-5-5`; a parenthesised note such as `(1M context)` is dropped);
- `Co-Authored-By: Devin [<model>] <…devin-ai-integration[bot]@users.noreply.github.com>` (or
  `<devin@cognition.ai>`) — Devin, as Devin records it (seen in this repo's history on 2026-08-26…09-28);
  a Devin trailer that names no model passes with a warning unless a `Harness:` line names it;
- `Harness: <harness>/<model-id>/<tier>` — each part `[a-z0-9][a-z0-9._-]*`
  (e.g. `devin-desktop/swe-2-high/subagent`, `claude-code/claude-opus-5-5/subagent`; BM-HARNESS-01).

**Operator commits** need no harness trailer:

- a `Harness: operator` trailer;
- a merge commit made on GitHub (two or more parents, committer `GitHub <noreply@github.com>`, signed —
  GitHub signs its web merges; the signature's presence is checked, not GitHub's key) — the operator
  merges through GitHub (H1);
- a **valid OP-25 signature**: a signed commit (`gpgsig` header) whose signature verifies against the
  allowed-signers file (`%G?` = `G`). The file is `--allowed-signers PATH`, else
  `docs/build/tools/record_policy/allowed_signers` **as it is at BASE** — read at the base so a change
  can never authorise its own signer. Until OP-25's public key is committed there is nothing to verify
  against, so a signature alone identifies no one (a signing default in an agent session's git config
  must not turn an untrailered agent commit green): such a commit fails, and the message says to add
  `Harness: operator` (agent interpretation of "a valid OP-25 signature", plan §3.3; the file path is
  P34.28's to fix — it may commit it here or pass `--allowed-signers`).

A commit with both a harness trailer and `Harness: operator` passes as an agent commit, with a warning.
Author and committer e-mail addresses are never written to the report.

Usage::

    check_trailers.py --range BASE..HEAD | --range BASE...HEAD [--json PATH] [--repo DIR]
                      [--allowed-signers PATH]

`BASE...HEAD` (a PR: from the merge base) and `BASE..HEAD` both judge the commits reachable from HEAD
and not from BASE (merges included).

Exit codes: 0 every commit passes · 1 an untrailered agent commit or a failed signature · 2 usage ·
3 vacuous (the range holds no commit) · 5 unknown (shallow clone, unresolvable revision, git failure) —
never treated as green. Python 3.9+, stdlib and `git` only.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "trailer-check/1"
EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_VACUOUS, EXIT_UNKNOWN = 0, 1, 2, 3, 5
ALLOWED_SIGNERS_REL = "docs/build/tools/record_policy/allowed_signers"

TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)[ \t]*:[ \t]*(.*?)\s*$")
PART = r"[a-z0-9][a-z0-9._-]*"
HARNESS_RE = re.compile(rf"^({PART})/({PART})/({PART})$", re.I)
COAUTHOR_RE = re.compile(r"^(?P<name>[^<>]+?)\s*<(?P<email>[^<>\s]+)>$")
CLAUDE_EMAIL = "noreply@anthropic.com"
DEVIN_EMAIL_RE = re.compile(
    r"^(?:\d+\+)?devin-ai-integration\[bot\]@users\.noreply\.github\.com$|^devin@cognition\.ai$",
    re.I,
)
GITHUB_COMMITTER = ("GitHub", "noreply@github.com")


class Unknown(Exception):
    pass


def slug(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).replace(".", "-").strip("-")


def final_paragraph(message: str) -> list[str]:
    paras = [p for p in re.split(r"\n[ \t]*\n", message.strip()) if p.strip()]
    if len(paras) < 2:  # a subject line alone has no trailer block
        return []
    lines: list[str] = []
    for raw in paras[-1].splitlines():
        if raw[:1] in (" ", "\t") and lines:  # a folded continuation line
            lines[-1] += " " + raw.strip()
        else:
            lines.append(raw.rstrip())
    return lines


@dataclass
class Trailers:
    harness: list[dict[str, str | None]] = field(default_factory=list)
    operator: bool = False
    malformed: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def parse_trailers(message: str) -> Trailers:
    t = Trailers()
    for line in final_paragraph(message):
        m = TRAILER_RE.match(line)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2)
        if key == "harness":
            if value.strip().lower() == "operator":
                t.operator = True
                continue
            h = HARNESS_RE.match(value.strip())
            if h:
                t.harness.append(
                    {
                        "kind": "harness",
                        "harness": h.group(1).lower(),
                        "model": h.group(2).lower(),
                        "tier": h.group(3).lower(),
                    }
                )
            else:
                t.malformed.append(f"Harness: {value}")
        elif key == "co-authored-by":
            c = COAUTHOR_RE.match(value.strip())
            if not c:
                continue
            name, email = c.group("name").strip(), c.group("email")
            if name.lower().startswith("claude") and email.lower() == CLAUDE_EMAIL:
                model = slug(name)
                if model == "claude":  # `Claude` alone names no model
                    t.rejected.append(f"Co-Authored-By: {name} <{email}> (names no model)")
                    continue
                t.harness.append(
                    {"kind": "co-author", "harness": "claude-code", "model": model, "tier": None}
                )
            elif name.lower().startswith("devin") and DEVIN_EMAIL_RE.match(email):
                rest = slug(re.sub(r"^devin", "", name, flags=re.I).strip(" ()"))
                t.harness.append(
                    {"kind": "co-author", "harness": "devin", "model": rest or None, "tier": None}
                )
            elif name.lower().startswith(("claude", "devin")):
                t.rejected.append(f"Co-Authored-By: {name} <…> (not the harness's address)")
    return t


@dataclass
class Commit:
    sha: str
    parents: list[str]
    committer: tuple[str, str]
    subject: str
    message: str
    sig_kind: str  # none | ssh | pgp | x509 | other


class Git:
    def __init__(self, repo: Path) -> None:
        self.repo = repo

    def run(self, *args: str, ok: tuple[int, ...] = (0,)) -> str:
        proc = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True)
        if proc.returncode not in ok:
            raise Unknown(f"git {' '.join(args[:3])} failed: {(proc.stderr or '').strip()[:200]}")
        return proc.stdout

    def commits(self, base: str, head: str) -> list[str]:
        for rev in (base, head):
            if subprocess.run(
                ["git", "-C", str(self.repo), "rev-parse", "--verify", "-q", f"{rev}^{{commit}}"],
                capture_output=True,
            ).returncode:
                raise Unknown(f"unresolvable revision '{rev}'")
        return self.run("rev-list", "--reverse", f"{base}..{head}").split()

    def commit(self, sha: str) -> Commit:
        raw = self.run("cat-file", "commit", sha)
        header, _, message = raw.partition("\n\n")
        parents: list[str] = []
        committer = ("", "")
        sig = ""
        for line in header.splitlines():
            if line.startswith("parent "):
                parents.append(line.split()[1])
            elif line.startswith("committer "):
                m = re.match(r"committer (.*?) <([^>]*)>", line)
                if m:
                    committer = (m.group(1), m.group(2))
            elif line.startswith(("gpgsig ", "gpgsig-sha256 ")):
                sig = line.split(" ", 1)[1]
        if not sig:
            kind = "none"
        elif "SSH SIGNATURE" in sig:
            kind = "ssh"
        elif "PGP SIGNATURE" in sig:
            kind = "pgp"
        elif "SIGNED MESSAGE" in sig:
            kind = "x509"
        else:
            kind = "other"
        subject = message.strip().splitlines()[0] if message.strip() else ""
        return Commit(sha, parents, committer, subject, message, kind)

    def verify(self, sha: str, allowed: Path) -> str:
        """`%G?` with the allowed-signers file configured (G = a good signature from an allowed key)."""
        out = self.run(
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed}",
            "log",
            "-1",
            "--format=%G?",
            sha,
        )
        return out.strip()[:1] or "N"


def classify(c: Commit, git: Git, allowed: Path | None) -> dict[str, Any]:
    t = parse_trailers(c.message)
    rec: dict[str, Any] = {
        "sha": c.sha,
        "short": c.sha[:8],
        "subject": c.subject[:120],
        "parents": len(c.parents),
        "signature": c.sig_kind,
        "trailers": t.harness,
        "class": "",
        "violations": [],
        "warnings": [],
    }
    for bad in t.malformed:
        rec["warnings"].append(
            f"malformed harness trailer '{bad}' (want <harness>/<model-id>/<tier>)"
        )
    for bad in t.rejected:
        rec["warnings"].append(f"not a recognised harness trailer: {bad}")
    if t.harness:
        rec["class"] = "agent"
        if t.operator:
            rec["warnings"].append("carries both a harness trailer and `Harness: operator`")
        named = any(h["model"] for h in t.harness)
        if not named:
            rec["warnings"].append(
                "the harness trailer names no model — add `Harness: <harness>/<model-id>/<tier>` (OM-01)"
            )
        return rec
    if t.operator:
        rec["class"] = "operator"
        return rec
    if len(c.parents) >= 2 and c.committer == GITHUB_COMMITTER and c.sig_kind != "none":
        rec["class"] = "operator-github-merge"
        return rec
    if c.sig_kind != "none":
        if allowed is None:
            rec["class"] = "untrailered"
            rec["violations"].append(
                f"{c.sig_kind} signature present but nothing to verify it against (no allowed-signers file at the "
                "base; OP-25 pending) and no harness trailer — an operator commit says `Harness: operator` (OM-01)"
            )
            return rec
        status = git.verify(c.sha, allowed)
        rec["signature_status"] = status
        if status == "G":
            rec["class"] = "operator-signed"
            return rec
        rec["class"] = "untrailered"
        rec["violations"].append(
            f"signature does not verify against {allowed.name} (%G? = {status}) and no harness trailer"
        )
        return rec
    rec["class"] = "untrailered"
    rec["violations"].append(
        "no recognised harness trailer (Co-Authored-By: Claude …/Devin …, Harness: <harness>/<model>/<tier>), "
        "no `Harness: operator`, no OP-25 signature (OM-01)"
    )
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_trailers.py", description="OM-01 commit-trailer check."
    )
    ap.add_argument("--range", required=True, metavar="BASE..HEAD", dest="span")
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--repo", metavar="DIR")
    ap.add_argument("--allowed-signers", metavar="PATH", dest="allowed")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code not in (0, None) else EXIT_OK
    m = re.fullmatch(r"(.+?)\.\.\.?(.+)", args.span)
    if not m:
        print(
            f"check_trailers.py: --range wants BASE..HEAD or BASE...HEAD, got '{args.span}'",
            file=sys.stderr,
        )
        return EXIT_USAGE
    base, head = m.group(1), m.group(2)
    start = Path(args.repo).resolve() if args.repo else Path.cwd()
    top = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if top.returncode:
        print(f"check_trailers.py: {start} is not a git repository", file=sys.stderr)
        return EXIT_USAGE
    repo = Path(top.stdout.strip())
    git = Git(repo)
    allowed: Path | None = None
    if args.allowed:
        allowed = Path(args.allowed).resolve()
        if not allowed.is_file():
            print(f"check_trailers.py: no allowed-signers file at {allowed}", file=sys.stderr)
            return EXIT_USAGE
    else:
        at_base = subprocess.run(
            ["git", "-C", str(repo), "show", f"{base}:{ALLOWED_SIGNERS_REL}"], capture_output=True
        )
        if at_base.returncode == 0:
            fd, name = tempfile.mkstemp(prefix="allowed_signers.")
            with os.fdopen(fd, "wb") as fh:
                fh.write(at_base.stdout)
            allowed = Path(name)
            atexit.register(allowed.unlink)
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "tool": "docs/build/tools/check_trailers.py",
        "input": {
            "repo": str(repo),
            "range": args.span,
            "allowed_signers": (args.allowed or f"{base}:{ALLOWED_SIGNERS_REL}")
            if allowed
            else None,
        },
    }
    try:
        if git.run("rev-parse", "--is-shallow-repository").strip() == "true":
            raise Unknown("shallow clone — the range may be cut short (fetch-depth: 0)")
        shas = git.commits(base, head)
        recs = [classify(git.commit(s), git, allowed) for s in shas]
    except Unknown as exc:
        doc.update({"summary": {"exit": EXIT_UNKNOWN}, "error": str(exc), "exit": EXIT_UNKNOWN})
        write(args.json, doc)
        print(f"trailer-check: unknown — {exc} (never green)")
        return EXIT_UNKNOWN
    viol = [(r, v) for r in recs for v in r["violations"]]
    warn = [(r, w) for r in recs for w in r["warnings"]]
    classes: dict[str, int] = {}
    for r in recs:
        classes[r["class"]] = classes.get(r["class"], 0) + 1
    code = EXIT_FAIL if viol else (EXIT_VACUOUS if not recs else EXIT_OK)
    doc.update(
        {
            "summary": {
                "commits": len(recs),
                "classes": classes,
                "violations": len(viol),
                "warnings": len(warn),
                "exit": code,
            },
            "commits": recs,
            "exit": code,
        }
    )
    write(args.json, doc)
    print(
        f"trailer-check: {args.span} — {len(recs)} commit(s): "
        + ", ".join(f"{k} {v}" for k, v in sorted(classes.items()))
    )
    for r, v in viol:
        print(f"  ✗ {r['short']} {r['subject'][:60]!r}: {v}")
    for r, w in warn[:20]:
        print(f"  ~ {r['short']} {r['subject'][:60]!r}: {w}")
    if len(warn) > 20:
        print(f"  ~ … {len(warn) - 20} more warning(s) in the JSON report")
    if code == EXIT_VACUOUS:
        print("  ? vacuous: the range holds no commit — not green")
    elif code == EXIT_OK:
        print(
            "  ✓ every commit carries a recognised harness trailer or is an operator commit (OM-01)"
        )
    return code


def write(path: str | None, doc: dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"trailer-check: JSON → {p}")


if __name__ == "__main__":
    sys.exit(main())
