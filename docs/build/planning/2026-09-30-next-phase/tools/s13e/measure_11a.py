#!/usr/bin/env python3
"""SEED-13e (Round-11 Stage B, T3 close-out): re-measure the Load lists of the 60 11A contracts
(rows 201-260) on the current working tree and estimate each row's working set in a 256k window.

stdlib only; read-only (prints a TSV/markdown report to stdout; writes nothing). Planning, not execution evidence.

Method (counter `utf8-bytes/3 | /4`, plan §8.5 / S6R-27):
  * every `- ` line of a contract's `## Load` section is one entry; its byte figures are the `N B` numbers on it;
  * an entry whose figures equal the sizes of its paths at the contract's commit is a WHOLE-FILE entry and is
    re-measured as the current file size;
  * any other entry (a § section, a line range, a grep selection, a fixed allowance) is CARRIED at its recorded
    figure when none of its files changed since the contract's commit, else flagged `changed-partial`;
  * `docs/tickets/DEFERRALS.md` is re-measured separately: the table rows that name the row id today, plus the
    register rows whose ids those rows name (the DEFERRALS-first share), shown beside the recorded allowance;
  * the contract's own entry is re-measured as its current size.
The working-set model is an agent inference (labelled in the review): fixed skill text the run loads
(implement-spec + self-review SKILL.md, measured), a harness/dispatch allowance, written output by size
class, diff re-reads by the self-review/gap passes, and tool output by live-leg count.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
TICKETS = ROOT / "docs" / "tickets"
PD = "docs/build/planning/2026-09-30-next-phase/"
HOME = pathlib.Path.home()
# the commits that wrote the full contracts (SEED-13b / 13c / 13d)
COMMIT = [(201, 220, "08026350"), (221, 240, "4cd43ce0"), (241, 260, "c1382e83")]
SKILLS = [HOME / ".claude/skills/implement-spec/SKILL.md", HOME / ".claude/skills/self-review/SKILL.md"]
HARNESS_ALLOWANCE = 15_000  # tokens: Devin Desktop system prompt + dispatch prompt (unknown; inference)
OUTPUT_TOKENS = {"S": 15_000, "M": 30_000, "L": 30_000, "plan": 37_500, "gate": 5_000}  # written output (inference;
# plan = an 8-row PLAN-11B batch at ≈ 14 KB per contract ÷ 3; a 12-row batch would be ≈ 56,000)
TOOL_BASE, TOOL_PER_LEG = 25_000, 12_000  # test/lint/CI/grep output; per live leg in the same context (inference)
NUM = re.compile(r"(\d[\d,]*) B(?![A-Za-z])")
TICK = re.compile(r"`([^`\s]+)`")


def commit_for(row: int) -> str:
    for a, b, c in COMMIT:
        if a <= row <= b:
            return c
    raise SystemExit(f"no commit for row {row}")


def resolve(tok: str) -> str | None:
    """Repo-relative path, `~/…` absolute path, or None when the token is not a file path."""
    t = tok.rstrip(".,;:")
    if t.startswith("PD/"):
        t = PD + t[3:]
    if t.startswith("~/"):
        p = HOME / t[2:]
        return str(p) if p.exists() else None
    if (ROOT / t).is_file():
        return t
    return None


def blob_size_at(commit: str, path: str) -> int | None:
    if path.startswith("/"):
        return None
    r = subprocess.run(["git", "cat-file", "-s", f"{commit}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return int(r.stdout.strip()) if r.returncode == 0 else None


def blob_id_at(commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "rev-parse", f"{commit}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def worktree_blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def size_now(path: str) -> int:
    return (pathlib.Path(path) if path.startswith("/") else ROOT / path).stat().st_size


def deferrals_share(rid: str) -> tuple[int, int, list[str]]:
    """Bytes of the DEFERRALS table rows naming `rid` today + the register rows whose ids they name."""
    lines = (ROOT / "docs/tickets/DEFERRALS.md").read_text(encoding="utf-8").splitlines()
    pat = re.compile(r"(?<![\w.])" + re.escape(rid) + r"(?![\w])")
    direct = [i for i, ln in enumerate(lines) if ln.startswith("|") and pat.search(ln)]
    ids: set[str] = set()
    for i in direct:
        m = re.match(r"^\|\s*`?(D-[A-Za-z0-9.\-]+)`?\s*\|", lines[i])
        if m:
            ids.add(m.group(1))
    extra = []
    for i, ln in enumerate(lines):
        m = re.match(r"^\|\s*`?(D-[A-Za-z0-9.\-]+)`?\s*\|", ln)
        if m and m.group(1) in ids and i not in direct:
            extra.append(i)
    sel = sorted(set(direct) | set(extra))
    total = sum(len(lines[i].encode("utf-8")) + 1 for i in sel)
    return total, len(direct), sorted(ids)


def contract_files() -> list[pathlib.Path]:
    out = []
    for p in sorted(TICKETS.glob("2[0-6][0-9]_*.md")):
        n = int(p.name[:3])
        if 201 <= n <= 260:
            out.append(p)
    return out


def size_class(text: str) -> str:
    m = re.search(r"\*\*Size budget:\*\*\s*([^\n]*)", text)
    s = m.group(1) if m else ""
    if s.startswith("S "):
        return "S"
    if s.startswith("M ") or s.startswith("L-split"):
        return "M"
    if "two contexts" in s:
        return "M"  # P34.48: two ≤ 1-run contexts of ~30 re-verdicts each; sized per context
    if "contexts" in s:
        return "plan"
    if "gate marker" in s:
        return "gate"
    return "M"


def legs(text: str) -> int:
    m = re.search(r"\*\*Live stage:\*\*\s*([^\n]*)", text)
    s = (m.group(1) if m else "").lower()
    if s.startswith("none") or "offline" in s:
        return 0
    if "three legs" in s:
        return 1  # P34.46: each leg runs in its own context from the re-run line (contract)
    return 1


EDIT_RE = re.compile(r"\b(to (change|repair|patch|rewrite|edit|extend|complete|fix|modify|retire|correct|"
                     r"harden|replace|update|split|move|add)|code to|the tool to|the guard to|the script to)\b", re.I)


def main() -> int:
    skills_b = sum(p.stat().st_size for p in SKILLS if p.exists())
    rows = []
    for p in contract_files():
        row = int(p.name[:3])
        rid = p.name.split("_", 1)[1].split("__")[0]
        commit = commit_for(row)
        text = p.read_text(encoding="utf-8")
        hm = re.search(r"\*\*Load \(token-counted[^*]*\*\*\s*([\d,]+) B", text)
        header_total = int(hm.group(1).replace(",", "")) if hm else 0
        sec = re.search(r"^## Load[^\n]*\n(.*?)(?=^## )", text, re.S | re.M)
        body = sec.group(1) if sec else ""
        entries = [ln for ln in body.splitlines() if ln.startswith("- ")]
        rec_sum = now_sum = 0
        edited = 0
        flags: list[str] = []
        defer_rec = 0
        for e in entries:
            tail = e.rsplit(" — ", 1)[-1]  # the figure(s) after the last dash: one total, or "a B + b B" per file
            nums = [int(x.replace(",", "")) for x in NUM.findall(tail)]
            rec = sum(nums)
            rec_sum += rec
            headpart = e.split(" — ")[0] if " — " in e else e
            toks = TICK.findall(headpart)
            paths = [q for q in (resolve(t) for t in toks) if q]
            if len(toks) != len(paths):  # a token that is not a resolvable file: treat as a partial entry
                nums_paths_ok = False
            else:
                nums_paths_ok = True
            if not nums:
                continue
            if any(q == f"docs/tickets/{p.name}" for q in paths):
                now = size_now(f"docs/tickets/{p.name}")
                now_sum += now
                if now != rec:
                    flags.append(f"self {rec}->{now}")
                continue
            if paths == ["docs/tickets/DEFERRALS.md"]:
                defer_rec = rec
                now_sum += rec  # replaced below by max(recorded allowance, measured share)
                continue
            at = [blob_size_at(commit, q) if not q.startswith("/") else None for q in paths]
            if nums_paths_ok and paths and len(paths) == len(nums) and all(a is not None and a == n for a, n in zip(at, nums)):
                now = sum(size_now(q) for q in paths)
                now_sum += now
                if now != rec:
                    flags.append(f"whole {paths[0].split('/')[-1]} {rec}->{now}")
            elif nums_paths_ok and paths and all(q.startswith("/") for q in paths) and len(paths) == len(nums):
                now = sum(size_now(q) for q in paths)
                now_sum += now
                if now != rec:
                    flags.append(f"home {paths[0].split('/')[-1]} {rec}->{now}")
            else:
                changed = [q for q in paths if not q.startswith("/") and blob_id_at(commit, q) not in (None, worktree_blob(q))]
                now_sum += rec
                if changed:
                    flags.append("changed-partial " + ",".join(c.split("/")[-1] for c in changed))
            if EDIT_RE.search(e):
                edited += rec
        dshare, ddirect, dids = deferrals_share(rid) if defer_rec else (0, 0, [])
        if defer_rec:
            now_sum += max(0, dshare - defer_rec)
        cls = size_class(text)
        nlegs = legs(text)
        load_t3 = now_sum / 3
        ws = (load_t3 + skills_b / 3 + HARNESS_ALLOWANCE + OUTPUT_TOKENS[cls] * 1.75
              + (TOOL_BASE + TOOL_PER_LEG * nlegs if cls != "gate" else 5_000) + edited / 3 * 0.5)
        rows.append(dict(row=row, id=rid, header=header_total, rec=rec_sum, now=now_sum, d=now_sum - header_total,
                         t3=now_sum // 3, t4=now_sum // 4, dshare=dshare, drec=defer_rec,
                         ddirect=ddirect, edited=edited, cls=cls, legs=nlegs, ws=round(ws), flags=flags,
                         consistent=(rec_sum == header_total)))
    print(f"# skills loaded by every run (implement-spec + self-review SKILL.md): {skills_b} B "
          f"≈ {skills_b // 3} (÷3) · {skills_b // 4} (÷4)")
    hdr = ["row", "id", "header_B", "entries_sum_B", "now_B", "delta_B", "now_t3", "now_t4", "deferrals_share_B",
           "deferrals_recorded_B", "deferrals_rows_naming", "edited_B", "class", "legs", "working_set_t3", "flags"]
    print("\t".join(hdr))
    for r in rows:
        print("\t".join(str(x) for x in [r["row"], r["id"], r["header"], r["rec"], r["now"], r["d"], r["t3"], r["t4"],
                                          r["dshare"], r["drec"], r["ddirect"], r["edited"], r["cls"], r["legs"], r["ws"],
                                          "; ".join(r["flags"]) + ("" if r["consistent"] else " ; HEADER≠SUM")]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
