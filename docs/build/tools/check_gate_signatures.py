#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""G4c signed-gate origin check — `gate-signature-check/1` (Round 11 / P34.28; A-16 "Key +
forward rule (Recommended)", GATE-P round 6, 2026-10-01T04:16:29Z; ADR-147 decision 6;
SIG-SEC-010; OP-25 support; B4 G4c).

From this change forward, a gate-affecting record is covered only by an **operator signature
that verifies**. This check walks the commits of a change (`--range BASE..HEAD`) and flags every
**gate-affecting record** it cannot trace to the operator's key:

- (a) a readout `Status:` line added in `docs/build/readouts/*.md` (`*_TEMPLATE.md` names are
  templates, never readouts) whose token is a signed status — SIGNED, PASSED,
  SKIPPED-BY-OPERATOR, NOT-PASSABLE (the G4b signing statuses: an HG-gate signature or a
  Class-S release go);
- (b) a row a commit adds to a `## GATE DECISIONS` table in `docs/build/LEDGER.md` —
  `decision`, `waiver` or `pre-authorization` in the kind-bearing form; every row of a
  kind-less (legacy) table; rows in `RESTORED` tables are exempt (a restoration replays
  history, it makes no new decision);
- (c) an `ingestion_permitted` absent/false → true transition on a `[sources.<id>]` group of
  `connectors/src/connectors/data/sources.toml` — per commit, old text vs new text.

**Coverage.** A trigger is covered when the commit that makes it verifies `G` (`%G?`) against
the allowed-signers file — `--allowed-signers PATH`, else
`docs/build/tools/record_policy/allowed_signers` **as it is at BASE** (read at the base, as in
`check_trailers.py`, so a change can never authorise its own signer). A source flip is
alternatively covered by a committed `GATE DECISIONS` row at HEAD whose text names the source
id and whose **blame commit verifies `G`** — the operator-signed record may sit anywhere in
history (SIG-SEC-010 does not require it in this range).

`Harness: operator`, a signed commit whose signature fails against the file, and a signature
with no committed file are **never** coverage: only the operator's key proves origin (OP-25).
While the file is header-only — the key outstanding — every gate-affecting record fails: the
check fails closed and `D-P34.28-1` tracks the key supply (due before GATE-G4).

An agent never generates, holds or loads the operator's key: this tool only *verifies*.

Usage::

    check_gate_signatures.py --range BASE..HEAD | --range BASE...HEAD [--json PATH]
                             [--repo DIR] [--allowed-signers PATH]

Exit codes: 0 every gate-affecting record is covered · 1 an uncovered record · 2 usage ·
3 vacuous (the range holds no commit) · 5 unknown (shallow clone, unresolvable revision, git
failure) — never treated as green. Python 3.9+, stdlib and `git` only.
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
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_trailers as ct  # noqa: E402
import memory_guard as mg  # noqa: E402

SCHEMA = "gate-signature-check/1"
EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_VACUOUS, EXIT_UNKNOWN = 0, 1, 2, 3, 5
LEDGER_REL = "docs/build/LEDGER.md"
SOURCES_REL = "connectors/src/connectors/data/sources.toml"
READOUT_GLOB = re.compile(r"^docs/build/readouts/[^/]+\.md$")
STATUS_RE = re.compile(r"^\s*Status:\s*(\S+)")
GD_ROW_RE = re.compile(r"^\|")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# the decision-bearing kinds a signature covers (the ticket's "for an HG gate or a Class S go"
# scope reads on the record class — fail-closed); confirmation/correction/date-correction rows
# are annotations, not signature events
SIGNING_KINDS = {"decision", "waiver", "pre-authorization"}
INGEST_RE = re.compile(r"^\s*ingestion_permitted\s*=\s*(true|false)\s*(?:#.*)?$")


def gate_table_indexes(t: "mg.Table") -> tuple[int, int | None] | None:
    """(gate column, kind column) of a GATE DECISIONS table, or None when the table is not
    decision-shaped at all — the TS-08 corrections register shares the `## GATE DECISIONS`
    region but has no `gate` column; its rows are dispositions, never gate decisions."""
    low = [mg.strip_markup(h).strip().lower() for h in t.header]
    gc = next((i for i, h in enumerate(low) if h.startswith("gate")), None)
    if gc is None:
        return None
    kc = low.index("kind") if "kind" in low else None
    return gc, kc


def row_kind(cells: list[str], kc: int | None) -> str:
    if kc is not None and len(cells) > kc:
        return mg.strip_markup(cells[kc]).strip().lower()
    return "decision"  # a kind-less GATE DECISIONS table holds only decisions


def name_status(git: ct.Git, sha: str, parent: str) -> list[tuple[str, str]]:
    out = git.run(
        "diff", "--name-status", "--no-renames", f"{parent}..{sha}", "--"
    )
    pairs: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def added_lines(git: ct.Git, sha: str, parent: str, path: str) -> list[str]:
    diff = git.run(
        "diff", "--unified=0", f"{parent}..{sha}", "--", path, ok=(0, 1)
    )
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def blob_at(git: ct.Git, rev: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(git.repo), "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
    )
    return proc.stdout if proc.returncode == 0 else None


def permitted_groups(text: str) -> set[str]:
    """`[sources.<id>]` groups that declare `ingestion_permitted = true` (the group's key lines —
    `toml_groups` maps a line to the first two components of its table header, so a nested
    `[sources.x.rights]` line still lands on `sources.x`, matching the loader's group)."""
    lines = text.split("\n")
    groups = mg.toml_groups(lines)
    out: set[str] = set()
    for i, line in enumerate(lines, 1):
        m = INGEST_RE.match(line)
        if m and m[1] == "true" and groups.get(i, "").startswith("sources."):
            out.add(groups[i])
    return out


def gd_added_rows(
    git: ct.Git, sha: str, added: list[str]
) -> list[dict[str, str]]:
    """GATE DECISIONS rows this commit adds, judged against the commit's own LEDGER text —
    restricted to rows that literally appear in the diff (not every row in the file)."""
    head = blob_at(git, sha, LEDGER_REL)
    if head is None:
        return []
    add_norm = {mg.norm(l) for l in added if l.strip().startswith("|")}
    out: list[dict[str, str]] = []
    for t in mg.gd_tables(head.split("\n")):
        if t.restored_from:
            continue  # a restoration replays history — it makes no new decision (a
            # smuggled new row fails judge_restored_blocks' verbatim rule, not this check)
        idx = gate_table_indexes(t)
        if idx is None:
            continue
        gc, kc = idx
        for ln, row in t.rows:
            if mg.norm(row) not in add_norm:
                continue
            cells = mg.table_cells(row)
            kind = row_kind(cells, kc)
            if kind not in SIGNING_KINDS:
                continue
            out.append(
                {
                    "line": str(ln),
                    "gate": mg.strip_markup(cells[gc]).strip() if len(cells) > gc else "?",
                    "item": mg.strip_markup(cells[3]).strip() if len(cells) > 3 else "?",
                    "kind": kind,
                }
            )
    return out


def names_source(row_text: str, group: str) -> bool:
    """A GATE DECISIONS row 'names' a source: the `[sources.<id>]` group or the bare `<id>`
    appears on a token boundary (substring matches — `okc` inside `okc_pd_2024`, or `demo`
    inside `sources.demo.rights` — do not count)."""
    src = group.split(".", 1)[-1]
    return any(
        re.search(r"(?<![\w.-])" + re.escape(tok) + r"(?![\w.-])", row_text)
        for tok in (group, src)
    )


def blame_commit(git: ct.Git, rev: str, path: str, line: int) -> str:
    out = git.run("blame", "--line-porcelain", "-L", f"{line},{line}", rev, "--", path)
    m = re.match(r"^([0-9a-f]{40}) ", out)
    if not m:
        raise ct.Unknown(f"git blame produced no sha for {path}:{line}")
    return m[1]


def judge(
    git: ct.Git, base: str, head: str, allowed: Path | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(commit records, violations). A commit record lists its gate-affecting records and how
    each is covered; a violation is one uncovered record."""
    recs: list[dict[str, Any]] = []
    viol: list[dict[str, Any]] = []
    # rows at HEAD for the source-flip record-coverage path (parsed once): only a
    # decision/waiver/pre-authorization row of a non-restored decisions table can carry a
    # standing go — a correction or confirmation naming the source is not an authorization
    head_ledger = blob_at(git, head, LEDGER_REL)
    head_rows: list[tuple[int, str]] = []
    if head_ledger is not None:
        for t in mg.gd_tables(head_ledger.split("\n")):
            if t.restored_from:
                continue  # history; its blame is the restoration commit regardless
            idx = gate_table_indexes(t)
            if idx is None:
                continue
            _, kc = idx
            for ln, row in t.rows:
                if row_kind(mg.table_cells(row), kc) in SIGNING_KINDS:
                    head_rows.append((ln, row))
    verified: dict[str, str] = {}  # sha -> %G?-style status — verify each commit at most once

    def sig_status(sha: str) -> str:
        if sha not in verified:
            c = git.commit(sha)
            # never let git consult ambient config: verification runs only against the
            # pinned allowed-signers file (at BASE or --allowed-signers)
            verified[sha] = (
                git.verify(sha, allowed)
                if c.sig_kind != "none" and allowed is not None
                else ("N" if c.sig_kind == "none" else "E")
            )
        return verified[sha]

    def covered_by_record(source_group: str) -> str | None:
        """A flip is covered by an operator-signed GATE DECISIONS row at HEAD naming the
        source (the row's blame commit verifies `G`). Returns the covering sha or None."""
        for ln, row in head_rows:
            if not names_source(row, source_group):
                continue
            who = blame_commit(git, head, LEDGER_REL, ln)
            if sig_status(who) == "G":
                return who
        return None

    for sha in git.commits(base, head):
        c = git.commit(sha)
        parent = c.parents[0] if c.parents else EMPTY_TREE
        self_signed = sig_status(sha) == "G"
        triggers: list[dict[str, Any]] = []
        for st, path in name_status(git, sha, parent):
            if st == "D":
                continue
            if READOUT_GLOB.match(path) and not path.split("/")[-1].endswith(
                "_TEMPLATE.md"
            ):
                for line in added_lines(git, sha, parent, path):
                    m = STATUS_RE.match(line)
                    if m and m[1].strip("*`").rstrip(".,;").upper() in mg.READOUT_STATUSES:
                        triggers.append(
                            {
                                "kind": "readout-status",
                                "path": path,
                                "detail": f"Status → {m[1].strip('*`').rstrip('.,;')}",
                                "covered": "commit" if self_signed else None,
                            }
                        )
            if path == LEDGER_REL:
                for row in gd_added_rows(git, sha, added_lines(git, sha, parent, path)):
                    triggers.append(
                        {
                            "kind": "gate-record",
                            "path": path,
                            "detail": f"line {row['line']}: {row['gate']} / "
                            f"{row['item']} ({row['kind']})",
                            "covered": "commit" if self_signed else None,
                        }
                    )
            if path == SOURCES_REL:
                old_text = blob_at(git, parent, path) or ""
                new_text = blob_at(git, sha, path) or ""
                for grp in sorted(permitted_groups(new_text) - permitted_groups(old_text)):
                    who = covered_by_record(grp)
                    triggers.append(
                        {
                            "kind": "source-flip",
                            "path": path,
                            "detail": f"ingestion_permitted → true for [{grp}]",
                            "covered": "commit"
                            if self_signed
                            else (f"record@{who[:8]}" if who else None),
                        }
                    )
        rec = {
            "sha": sha,
            "short": sha[:8],
            "subject": c.subject[:120],
            "signature": c.sig_kind,
            "signature_status": verified.get(sha),
            "triggers": triggers,
            "uncovered": [t for t in triggers if not t["covered"]],
        }
        for t in rec["uncovered"]:
            viol.append({"sha": sha, "short": sha[:8], "subject": c.subject[:120], **t})
        recs.append(rec)
    return recs, viol


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_gate_signatures.py", description="G4c signed-gate origin check."
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
            f"check_gate_signatures.py: --range wants BASE..HEAD or BASE...HEAD, got '{args.span}'",
            file=sys.stderr,
        )
        return EXIT_USAGE
    base, head = m.group(1), m.group(2)
    start = Path(args.repo).resolve() if args.repo else Path.cwd()
    top = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if top.returncode:
        print(f"check_gate_signatures.py: {start} is not a git repository", file=sys.stderr)
        return EXIT_USAGE
    repo = Path(top.stdout.strip())
    git = ct.Git(repo)
    allowed: Path | None = None
    if args.allowed:
        allowed = Path(args.allowed).resolve()
        if not allowed.is_file():
            print(
                f"check_gate_signatures.py: no allowed-signers file at {allowed}",
                file=sys.stderr,
            )
            return EXIT_USAGE
    else:
        at_base = subprocess.run(
            ["git", "-C", str(repo), "show", f"{base}:{ct.ALLOWED_SIGNERS_REL}"],
            capture_output=True,
        )
        if at_base.returncode == 0:
            fd, name = tempfile.mkstemp(prefix="allowed_signers.")
            with os.fdopen(fd, "wb") as fh:
                fh.write(at_base.stdout)
            allowed = Path(name)
            atexit.register(allowed.unlink)
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "tool": "docs/build/tools/check_gate_signatures.py",
        "input": {
            "repo": str(repo),
            "range": args.span,
            "allowed_signers": (args.allowed or f"{base}:{ct.ALLOWED_SIGNERS_REL}")
            if allowed
            else None,
        },
    }
    try:
        if git.run("rev-parse", "--is-shallow-repository").strip() == "true":
            raise ct.Unknown("shallow clone — the range may be cut short (fetch-depth: 0)")
        recs, viol = judge(git, base, head, allowed)
    except ct.Unknown as exc:
        doc.update({"summary": {"exit": EXIT_UNKNOWN}, "error": str(exc), "exit": EXIT_UNKNOWN})
        write(args.json, doc)
        print(f"gate-signature-check: unknown — {exc} (never green)")
        return EXIT_UNKNOWN
    code = EXIT_FAIL if viol else (EXIT_VACUOUS if not recs else EXIT_OK)
    n_tr = sum(len(r["triggers"]) for r in recs)
    doc.update(
        {
            "summary": {
                "commits": len(recs),
                "gate_affecting_records": n_tr,
                "uncovered": len(viol),
                "exit": code,
            },
            "commits": recs,
            "violations": viol,
            "exit": code,
        }
    )
    write(args.json, doc)
    print(
        f"gate-signature-check: {args.span} — {len(recs)} commit(s), "
        f"{n_tr} gate-affecting record(s), {len(viol)} uncovered"
    )
    for v in viol:
        print(
            f"  ✗ {v['short']} {v['subject'][:50]!r}: {v['kind']} on {v['path']} — "
            f"{v['detail']} (no operator signature covers it — OP-25, SIG-SEC-010)"
        )
    if code == EXIT_VACUOUS:
        print("  ? vacuous: the range holds no commit — not green")
    elif code == EXIT_OK:
        print(
            "  ✓ every gate-affecting record is covered by an operator signature "
            "(or the range touches none)"
        )
    return code


def write(path: str | None, doc: dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"gate-signature-check: JSON → {p}")


if __name__ == "__main__":
    sys.exit(main())
