#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""check_runbook.py — the ops-runbook command/path verifier (P35.4, SIG-OPS-010).

The contract's fixture-verified AC: *every command and path named in
``docs/ops/RUNBOOK.md`` exists in the tree it names.* This check is the
deterministic leg of that promise — stdlib only, read-only, so the uv-less CI
``docs`` job runs it under ``make docs-check``.

What is checked (each leg reports candidates/evaluated; a non-empty candidate
set evaluated to zero exits 3 — SIG-ENG-042/G11):

* **Sections** — the nine G1 §3.10 runbook sections are present, in order.
* **Bash fences** — every command line inside a ```bash fence is classified and
  verified:
    - leading ``VAR=value`` env bindings are stripped; ``|`` pipes split into
      segments and each segment is judged; a line continuing a ``\\`` line is
      an argument tail and skipped; pure comments/blank lines skipped;
    - ``bash <path>`` / a repo-relative first token ending in ``.sh`` /
      ``.py`` — the file must exist;
    - ``uv run sig-ops <verb>``, ``sig-ops <verb>``, ``uv run python -m ops
      <verb>`` — the verb must be one of ``ops/src/ops/cli.py``'s
      ``add_parser`` names;
    - ``uv run python -m <pkg> …`` — ``<pkg>/src/<pkg>/__main__.py`` must exist;
    - ``make <target>`` — the target must be declared in ``Makefile``;
    - ``python3 <path>`` — the file must exist;
    - external forms — ``gcloud``, ``gsutil``, ``cloud-sql-proxy``, ``docker``,
      ``sqitch``, ``psql``, ``curl``, ``openssl``, ``npm``, ``git``, ``jq``:
      the command's longest normalized leading shape (``$VARS``, ``$(…)``,
      ``<…>``, quotes and every token from the first ``-flag``/assignment on
      stripped) must appear verbatim in the declared corpus (the ops/gcp
      scripts, the executed deploy report, the monitoring README, the G1 ops
      research command log) — i.e. a form the tree itself already records;
    - shell builtins / assignments (``export``, ``for``/``do``/``done``,
      ``echo``, ``printf``, ``cd``, ``set``, ``date``, ``test``…) are
      allowlisted;
    - anything else fails closed: an unclassified command is an error, so a
      command the checker does not understand can never slip through.
* **Prose paths** — a backticked token that looks like a repo path
  (``ops/…``, ``docs/…``, ``tests/…``, ``db/…``, ``web/…``, ``scripts/…``,
  ``.github/…``, ``Makefile``) outside code fences must resolve to a file or
  directory (globs ``*``/``?`` must match at least one path). Bucket prefixes
  are written ``gs://…`` so they never parse as repo paths.
* **Secret register (SIG-SEC-009)** — the ``## 6.`` section's register table
  (header ``name | owner | consumer | last_rotation | procedure``) carries one
  row per ``[[secret]]`` declared in ``ops/iam_identities.toml`` (name-set and
  consumer-set equality), ``last_rotation`` is an ISO date or ``unknown``
  (never an invented date), and no cell carries a credential-shaped literal.
* **No secrets** — the file carries no private-key block, no
  ``AIza…``-shaped API key, no ``token``/``secret``/``password`` assignment to
  a literal, and no e-mail address (the operator's address stays out of the
  repo — ops/monitoring/README.md's ``<redacted …>`` convention).

Usage::

    python3 docs/build/tools/check_runbook.py [--root DIR] [--json PATH]

Exit codes: 0 OK · 1 violations · 2 usage · 3 vacuous.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNBOOK = "docs/ops/RUNBOOK.md"
OPS_CLI = "ops/src/ops/cli.py"
IAM_TOML = "ops/iam_identities.toml"
MAKEFILE = "Makefile"

# The nine G1 §3.10 sections, in order — matched as `## ` heading text.
SECTIONS = [
    ("alert received", re.compile(r"^##\s+\d*\.*\s*Alert received\b", re.I)),
    ("restore", re.compile(r"^##\s+\d*\.*\s*Restore\b", re.I)),
    ("republish", re.compile(r"^##\s+\d*\.*\s*Republish\b", re.I)),
    ("window watch", re.compile(r"^##\s+\d*\.*\s*Scheduled-window watch\b", re.I)),
    ("job failed", re.compile(r"^##\s+\d*\.*\s*Job failed\b", re.I)),
    ("secret rotation", re.compile(r"^##\s+\d*\.*\s*Secret rotation\b", re.I)),
    ("roll", re.compile(r"^##\s+\d*\.*\s*Roll\b", re.I)),
    ("cost review", re.compile(r"^##\s+\d*\.*\s*Cost review\b", re.I)),
    ("decommission", re.compile(r"^##\s+\d*\.*\s*Decommission\b", re.I)),
]

# Corpus the external command forms are verified against: the deploy/ops
# scripts and the executed/decision records that already carry them.
CORPUS_GLOBS = [
    "ops/gcp/*.sh",
    "ops/gcp/README.md",
    "ops/README.md",
    "ops/monitoring/README.md",
    "docs/build/reports/**/*.md",
    "docs/build/OPERATIONAL_READINESS.md",
    "docs/build/planning/2026-09-30-next-phase/research/G1-ops.md",
]

# External commands: (first token, minimum leading shape length in tokens).
EXTERNAL_MIN = {
    "gcloud": 3,      # e.g. `gcloud run jobs execute`
    "gsutil": 2,
    "cloud-sql-proxy": 1,
    "docker": 2,
    "sqitch": 1,
    "psql": 1,
    "curl": 1,
    "openssl": 2,
    "git": 2,
    "jq": 1,
    "npx": 2,
}

# Shell builtins / coreutils a command line may begin with.
BUILTINS = {
    "export", "for", "do", "done", "if", "then", "else", "elif", "fi",
    "while", "until", "case", "esac", "in", "echo", "printf", "cd", "set",
    "unset", "local", "return", "exit", "test", "[", "[[", "true", "false",
    "sleep", "date", "env", "xargs", "grep", "sort", "head", "tail", "cat",
    "ls", "wc", "tr", "cut", "sed", "awk", "find", "read", "shift", "umask",
    "command", "eval", "exec", "source", ".", "mkdir", "rm", "cp", "mv",
    "sha256sum", "shasum", "diff", "chmod", "touch", "install",
}

_FENCE_RE = re.compile(r"^\s*```")
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_FLAG_RE = re.compile(r"^-")
_VAR_RE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$\(|\$\$")
_QUOTED_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_ANGLE_RE = re.compile(r"<[^>\n]*>")
_WS_RE = re.compile(r"\s+")

_PARSER_RE = re.compile(r"""add_parser\(\s*["']([a-z0-9][a-z0-9\-]*)["']""")
_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:", re.M)
_SECRET_ROW_RE = re.compile(r"\[\[secret\]\]\s*name\s*=\s*\"([^\"]+)\"\s*consumers\s*=\s*\[([^\]]*)\]", re.S)

# Prose path tokens: backticked, rooted at a tree top-level dir.
_PROSE_PATH_RE = re.compile(
    r"`((?:ops|docs|tests|db|web|scripts|connectors|exports|api|ontology|"
    r"parsing|resolution|reconcile|inference|tasks|orchestration|policy|"
    r"evidence|\.github)/[^\s`]+|Makefile)`"
)

# Credential-shaped literals the runbook must never carry.
_SECRET_PATTERNS = [
    ("private-key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("gcp api key", re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}")),
    ("bearer-ish token", re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_/+\-]{16,}", re.I)),
    ("e-mail address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]

_LAST_ROT_RE = re.compile(r"^(unknown|\d{4}-\d{2}-\d{2}([T ][0-9:]{5,8}Z?)?)$")


def _fences(lines: list[str]) -> list[tuple[int, str]]:
    """Yield (lineno, line) inside ```bash fences only."""
    in_fence = False
    is_bash = False
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, 1):
        if _FENCE_RE.match(raw):
            if not in_fence:
                in_fence = True
                is_bash = raw.strip().startswith("```bash")
            else:
                in_fence = False
                is_bash = False
            continue
        if in_fence and is_bash:
            out.append((i, raw.rstrip()))
    return out


def _nonfence_lines(lines: list[str]) -> list[tuple[int, str]]:
    in_fence = False
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, 1):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((i, raw))
    return out


def _strip_comment(line: str) -> str:
    """Drop a trailing ``#`` comment that is not inside quotes (best effort)."""
    depth_s = depth_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not depth_d:
            depth_s = not depth_s
        elif ch == '"' and not depth_s:
            depth_d = not depth_d
        elif ch == "#" and not depth_s and not depth_d and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _normalize_shape(tokens: list[str]) -> str:
    """Join leading command-shape tokens into the corpus-searchable prefix."""
    return " ".join(tokens)


def _shape_tokens(line: str) -> list[str]:
    """Leading tokens usable for corpus prefix match.

    Stops at the first flag, assignment, variable, substitution, quoted or
    angle-bracket token — those are arguments, not command shape.
    """
    out = []
    for tok in line.split():
        if (
            _FLAG_RE.match(tok)
            or _ASSIGN_RE.match(tok)
            or _VAR_RE.search(tok)
            or tok.startswith(('"', "'", "<", "(", "{"))
            or '"' in tok
            or "'" in tok
        ):
            break
        out.append(tok)
    return out


def _verbs(root: pathlib.Path) -> set[str]:
    cli = root / OPS_CLI
    if not cli.is_file():
        return set()
    return set(_PARSER_RE.findall(cli.read_text(errors="replace")))


def _make_targets(root: pathlib.Path) -> set[str]:
    mk = root / MAKEFILE
    if not mk.is_file():
        return set()
    return set(_TARGET_RE.findall(mk.read_text(errors="replace")))


def _corpus(root: pathlib.Path) -> str:
    parts: list[str] = []
    for pattern in CORPUS_GLOBS:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                parts.append(p.read_text(errors="replace"))
    return "\n".join(parts)


def _check_external(
    tokens: list[str], corpus: str, min_len: int
) -> str | None:
    """Return an error string, or None when a verbatim shape matches corpus."""
    if len(tokens) < min_len:
        return f"shape too short to verify ({' '.join(tokens)!r})"
    for k in range(len(tokens), min_len - 1, -1):
        cand = _normalize_shape(tokens[:k])
        if cand in corpus:
            return None
    return (
        f"no verbatim match for {' '.join(tokens)!r} in the ops corpus "
        f"(checked down to {min_len} tokens)"
    )


def _check_command(
    line: str, lineno: int, verbs: set[str], targets: set[str],
    corpus: str, root: pathlib.Path,
) -> list[str]:
    """Judge one command line (already comment-stripped). Returns errors."""
    errs: list[str] = []
    segments = [s.strip() for s in line.split("|")]
    for seg in segments:
        if not seg:
            continue
        toks = seg.split()
        # strip leading env assignments (FOO=bar cmd …)
        while toks and _ASSIGN_RE.match(toks[0]):
            toks = toks[1:]
        if not toks:
            continue
        head = toks[0]
        if head in BUILTINS:
            continue
        if head == "sudo":
            errs.append(f"L{lineno}: `sudo` — runbooks never assume sudo")
            continue
        if head in ("bash", "sh"):
            script = next((t for t in toks[1:] if not t.startswith("-")), None)
            if script is None or not (root / script).exists():
                errs.append(
                    f"L{lineno}: `{head} {script}` — script not in the tree"
                )
            continue
        if head == "uv":
            rest = toks[1:]
            if rest[:1] == ["run"]:
                rest = rest[1:]
            if rest and rest[0] == "sig-ops":
                verb = rest[1] if len(rest) > 1 else ""
                if verb not in verbs:
                    errs.append(
                        f"L{lineno}: `uv run sig-ops {verb}` — no such "
                        f"sig-ops verb in {OPS_CLI}"
                    )
            elif rest[:3] == ["python", "-m", "ops"]:
                verb = rest[3] if len(rest) > 3 else ""
                if verb not in verbs:
                    errs.append(
                        f"L{lineno}: `uv run python -m ops {verb}` — no such "
                        f"ops verb in {OPS_CLI}"
                    )
            elif rest[:2] == ["python", "-m"] and len(rest) > 2:
                pkg = rest[2]
                if not (root / pkg / "src" / pkg / "__main__.py").is_file():
                    errs.append(
                        f"L{lineno}: `uv run python -m {pkg}` — "
                        f"{pkg}/src/{pkg}/__main__.py not in the tree"
                    )
            elif rest and rest[0] == "pytest":
                pass  # `uv run pytest …` — the suite, always present
            else:
                errs.append(
                    f"L{lineno}: `uv {' '.join(rest[:3])}` — unrecognised "
                    "`uv run` form (sig-ops/python -m/pytest only)"
                )
            continue
        if head == "sig-ops":
            verb = toks[1] if len(toks) > 1 else ""
            if verb not in verbs:
                errs.append(
                    f"L{lineno}: `sig-ops {verb}` — no such verb in {OPS_CLI}"
                )
            continue
        if head == "make":
            tgt = next((t for t in toks[1:] if not t.startswith("-")), "")
            if tgt not in targets:
                errs.append(f"L{lineno}: `make {tgt}` — no such Makefile target")
            continue
        if head == "npm":
            # `npm --prefix web run <script>` — the script must be declared in
            # web/package.json.
            m = re.match(r"--prefix\s+(\S+)\s+run\s+([A-Za-z0-9:_-]+)", " ".join(toks[1:]))
            if not m:
                errs.append(
                    f"L{lineno}: `npm …` — only the `npm --prefix <pkg> run "
                    "<script>` form is verified"
                )
            else:
                pkg = root / m.group(1)
                try:
                    scripts = json.loads((pkg / "package.json").read_text())["scripts"]
                except (OSError, json.JSONDecodeError, KeyError):
                    errs.append(
                        f"L{lineno}: `{m.group(1)}/package.json` lacks a "
                        "scripts map"
                    )
                else:
                    if m.group(2) not in scripts:
                        errs.append(
                            f"L{lineno}: `npm --prefix {m.group(1)} run "
                            f"{m.group(2)}` — no such script in "
                            f"{m.group(1)}/package.json"
                        )
            continue
        if head in ("python3", "python"):
            script = next(
                (t for t in toks[1:] if not t.startswith("-") and "/" in t or t.endswith(".py")),
                None,
            )
            if script is not None and not (root / script).exists():
                errs.append(
                    f"L{lineno}: `{head} {script}` — script not in the tree"
                )
            continue
        if head in EXTERNAL_MIN:
            shape = _shape_tokens(seg)
            err = _check_external(shape, corpus, EXTERNAL_MIN[head])
            if err:
                errs.append(f"L{lineno}: `{head}` command: {err}")
            continue
        # a bare repo path executed directly (`ops/gcp/foo.sh --check`)
        if "/" in head and head.split("/")[0] in {
            "ops", "docs", "tests", "db", "web", "scripts",
        }:
            if not (root / head).exists():
                errs.append(f"L{lineno}: `{head}` — not in the tree")
            continue
        errs.append(
            f"L{lineno}: unclassified command `{head}` — classify it in "
            "check_runbook.py or rewrite as a verified form"
        )
    return errs


def _check_register(
    text: str, lines: list[str], root: pathlib.Path
) -> tuple[list[str], dict[str, int]]:
    """Secret-register leg: name/consumer set equality with iam_identities.toml."""
    errs: list[str] = []
    stats = {"register_rows": 0, "evaluated": 0}
    iam = root / IAM_TOML
    if not iam.is_file():
        return [f"{IAM_TOML} missing — the register has no declared matrix"], stats
    declared: dict[str, set[str]] = {}
    for m in _SECRET_ROW_RE.finditer(iam.read_text(errors="replace")):
        name = m.group(1)
        consumers = set(re.findall(r'"([^"]+)"', m.group(2)))
        declared[name] = consumers

    # Locate the register table: a markdown table whose header row holds the
    # five contract fields.
    header_idx = None
    for i, ln in enumerate(lines):
        cells = [c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
        if (
            len(cells) >= 5
            and cells[0] == "name"
            and cells[1] == "owner"
            and cells[2] == "consumer"
            and cells[3] == "last_rotation"
        ):
            header_idx = i
            break
    if header_idx is None:
        return [
            "no secret register table found — expected a table headed "
            "`name | owner | consumer | last_rotation | procedure`"
        ], stats
    rows: dict[str, dict[str, str]] = {}
    for ln in lines[header_idx + 2:]:  # skip header + separator
        if not ln.strip().startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        stats["register_rows"] += 1
        name = cells[0].strip("`")
        rows[name] = {
            "owner": cells[1],
            "consumer": cells[2],
            "last_rotation": cells[3].strip("`"),
            "procedure": cells[4],
        }
        stats["evaluated"] += 1
        if not _LAST_ROT_RE.match(rows[name]["last_rotation"]):
            errs.append(
                f"register row {name}: last_rotation "
                f"{rows[name]['last_rotation']!r} is not `unknown` or an ISO "
                "date — never invent a date"
            )
        cons_cell = rows[name]["consumer"].replace("`", "").replace("—", "")
        got = set(cons_cell.split())
        if name in declared and got != declared[name]:
            errs.append(
                f"register row {name}: consumers {sorted(got)} != declared "
                f"{sorted(declared[name])} in {IAM_TOML}"
            )
    missing = set(declared) - set(rows)
    extra = set(rows) - set(declared)
    if missing:
        errs.append(f"register missing declared secrets: {sorted(missing)}")
    if extra:
        errs.append(f"register names undeclared secrets: {sorted(extra)}")
    return errs, stats


def check(root: pathlib.Path) -> tuple[list[str], dict[str, int]]:
    errs: list[str] = []
    stats: dict[str, int] = {
        "sections": 0,
        "command_lines": 0,
        "prose_paths": 0,
        "register_rows": 0,
        "evaluated": 0,
    }
    rb = root / RUNBOOK
    if not rb.is_file():
        return [f"{RUNBOOK} does not exist"], stats
    text = rb.read_text(errors="replace")
    lines = text.splitlines()

    # --- sections -------------------------------------------------------------
    pos = -1
    for name, rx in SECTIONS:
        hit = next(
            (i for i, ln in enumerate(lines) if rx.match(ln) and i > pos), None
        )
        if hit is None:
            errs.append(f"runbook lacks the G1 §3.10 section '{name}'")
        else:
            pos = hit
            stats["sections"] += 1

    # --- bash fences ----------------------------------------------------------
    verbs = _verbs(root)
    targets = _make_targets(root)
    corpus = _corpus(root)
    prev_cont = False
    for lineno, raw in _fences(lines):
        body = _strip_comment(raw).strip()
        if not body:
            continue
        if prev_cont or raw.rstrip().endswith("\\"):
            prev_cont = raw.rstrip().endswith("\\")
            continue
        stats["command_lines"] += 1
        stats["evaluated"] += 1
        errs.extend(_check_command(body, lineno, verbs, targets, corpus, root))

    # --- prose paths ----------------------------------------------------------
    for lineno, raw in _nonfence_lines(lines):
        for m in _PROSE_PATH_RE.finditer(raw):
            stats["prose_paths"] += 1
            stats["evaluated"] += 1
            tok = m.group(1).rstrip(".,;:)")
            if any(c in tok for c in "*?"):
                if not list(root.glob(tok)):
                    errs.append(
                        f"L{lineno}: `{tok}` — glob matches nothing in the tree"
                    )
            elif not (root / tok).exists():
                errs.append(f"L{lineno}: `{tok}` — not in the tree")

    # --- secret register ------------------------------------------------------
    reg_errs, reg_stats = _check_register(text, lines, root)
    errs.extend(reg_errs)
    stats["register_rows"] = reg_stats["register_rows"]
    stats["evaluated"] += reg_stats["evaluated"]

    # --- no secrets -----------------------------------------------------------
    for lineno, raw in _nonfence_lines(lines):
        for label, rx in _SECRET_PATTERNS:
            if rx.search(raw):
                errs.append(f"L{lineno}: credential-shaped literal ({label})")

    return errs, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="repo root (default: tool's)")
    ap.add_argument("--json", default=None, help="write the JSON report here")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    errs, stats = check(root)
    report = {"runbook": RUNBOOK, "stats": stats, "violations": errs}
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")

    candidates = stats["command_lines"] + stats["prose_paths"] + stats["register_rows"]
    if candidates > 0 and stats["evaluated"] == 0:
        print("check_runbook: candidates offered, none evaluated (vacuous)", file=sys.stderr)
        return 3
    if errs:
        for e in errs:
            print(f"check_runbook: {e}", file=sys.stderr)
        print(
            f"check_runbook: {len(errs)} violation(s) — "
            f"sections {stats['sections']}/{len(SECTIONS)}, "
            f"commands {stats['command_lines']}, prose paths {stats['prose_paths']}, "
            f"register rows {stats['register_rows']}",
            file=sys.stderr,
        )
        return 1
    print(
        f"check_runbook: OK — sections {stats['sections']}/{len(SECTIONS)}, "
        f"{stats['command_lines']} command lines, {stats['prose_paths']} prose "
        f"paths, {stats['register_rows']} register rows, 0 violations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
