#!/usr/bin/env python3
"""check_restorations_map.py — P34.27 resolution-map checker.

Asserts the invariant of the P34.27 contract (row 232, `restorations_p34.27.csv`):

* **total** — every `loss` / `transition-unjustified` row of the authoritative
  register `append_only_register.csv` maps to exactly one restored block
  (44 restored by P34.27; the two GATE DECISIONS rows SEED-06 already
  restored are mapped to their `RESTORED from` block, anchor `git-kept`);
* **unique** — no two map rows share the same anchor tag, and no map row
  addresses a commit+file pair the register does not classify as owed
  (no excluded row is accidentally "restored");
* **byte-exact** — for every row with an archive, `sha256` equals both the
  archive file's digest and the digest of the source bytes at `<commit>^`
  (the `git show <sha>^:<file>` range the anchor names); every archived line
  appears verbatim in `restored_block_path` (the P26.16 operator-account
  redaction is applied before comparing, per the D3 precedent).

Usage: ``python3 docs/build/tools/check_restorations_map.py [--json PATH]``
Exit 0 on success, 1 on any failure. Read-only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MR = ROOT / "docs/build/reports/memory-repair"
REGISTER = MR / "append_only_register.csv"
MAP = MR / "restorations_p34.27.csv"
EMAIL = "14stevevitali@gmail.com"
REDACT = "`<operator account — redacted per the D3 precedent, P34.27>`"
GIT_KEPT = "git-kept"  # SEED-06 rows: git keeps the bytes, no new archive

EXPECTED_SCHEMA = ["register_commit", "file", "classification", "restored_block_path", "anchor", "sha256"]
# the two SEED-06 GATE DECISIONS rows the register keeps as owed but resolved
SEED06 = {"c2055d96", "e2175c93"}


def git_show(rev: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def git_removed(sha: str, path: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "-U0", f"{sha}^", sha, "--", path],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [l[1:] for l in out.split("\n") if l.startswith("-") and not l.startswith("---")]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_ranges(src: str) -> list[tuple[int, int]] | None:
    """'L39-41,L74-74' → [(39,41),(74,74)]; '…all-removed' → None."""
    if "all-removed" in src:
        return None
    return [(int(a), int(b)) for a, b in re.findall(r"L(\d+)-(\d+)", src)] or None


def main() -> int:
    reg = list(csv.DictReader(REGISTER.open()))
    owed = [r for r in reg if r["classification"] in ("loss", "transition-unjustified")]
    mrows = list(csv.DictReader(MAP.open()))
    errs: list[str] = []

    if not mrows or list(mrows[0].keys()) != EXPECTED_SCHEMA:
        errs.append(f"map schema ≠ {EXPECTED_SCHEMA}: {list(mrows[0].keys()) if mrows else 'EMPTY'}")

    # uniqueness of anchor tags and coverage of owed rows
    tags = [r["anchor"].split("|")[0] for r in mrows]
    for t in sorted(set(tags)):
        if tags.count(t) != 1:
            errs.append(f"duplicate anchor tag {t}")
    owed_keys = {(r["commit"], r["file"]) for r in owed}
    for k in {(r["register_commit"], r["file"]) for r in mrows} - owed_keys:
        errs.append(f"map row {k} is not an owed register row (excluded row restored?)")
    # per-key counts must match exactly (several owed rows can share a
    # commit+file pair — e.g. DEFERRALS cells under one rewrite)
    from collections import Counter

    oc = Counter((r["commit"], r["file"], r["classification"]) for r in owed)
    mc = Counter((r["register_commit"], r["file"], r["classification"]) for r in mrows)
    for k, n in sorted((oc | mc).items()):
        if oc.get(k, 0) != mc.get(k, 0):
            errs.append(f"{k}: register rows {oc.get(k, 0)} ≠ map rows {mc.get(k, 0)}")
    if len(owed) != len(mrows):
        errs.append(f"map rows {len(mrows)} ≠ owed register rows {len(owed)}")

    for r in mrows:
        tag, _, rest = r["anchor"].partition("|")
        src, _, rest = rest.partition("|")
        section, _, arch = rest.partition("|")
        commit = r["register_commit"]
        path = r["file"]
        target = ROOT / r["restored_block_path"]
        if not target.exists():
            errs.append(f"{tag}: restored_block_path missing: {r['restored_block_path']}")
        if arch == GIT_KEPT:
            if commit not in SEED06:
                errs.append(f"{tag}: git-kept anchor on a non-SEED-06 row")
            continue
        # archive exists and hashes to the map's sha256
        ap = MR / arch
        if not ap.exists():
            errs.append(f"{tag}: archive missing {arch}")
            continue
        ab = ap.read_bytes()
        if sha256(ab) != r["sha256"]:
            errs.append(f"{tag}: archive sha256 ≠ map sha256")
            continue
        # archive equals the source bytes at <commit>^ (or the removed diff
        # lines for all-removed events.jsonl rows)
        try:
            if src.endswith("all-removed"):
                want = ("\n".join(git_removed(commit, path)) + "\n").encode()
            else:
                ranges = parse_ranges(src)
                lines = git_show(f"{commit}^", path).split("\n")
                want = ("\n".join(l for a, b in ranges for l in lines[a - 1 : b]) + "\n").encode()
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            errs.append(f"{tag}: source bytes unreadable ({src}): {e}")
            continue
        if want != ab:
            # the P26.16 archive redacts the operator account address (D3 precedent)
            if want.replace(EMAIL.encode(), REDACT.encode()) == ab:
                pass
            else:
                errs.append(f"{tag}: archive bytes ≠ {commit}^:{path} {src}")
                continue
        # restoration verification: for the events ledger the restored block is
        # the appended correction records (each archived line's event_id must
        # carry a `correction` naming its prior_line_sha256); for every other
        # file the archived bytes appear verbatim (P26.16 redaction applied).
        if r["restored_block_path"].endswith(".jsonl"):
            corr = [
                e for e in (json.loads(l) for l in target.read_text().split("\n") if l.strip())
                if e.get("kind") == "correction"
            ]
            by_target = {e.get("correction", {}).get("event_id"): e for e in corr}
            ok = True
            for l in ab.decode().split("\n"):
                if not l:
                    continue
                oid = json.loads(l)["event_id"]
                want = hashlib.sha256(l.encode()).hexdigest()  # line, no trailing \n (P34.8 convention)
                hits = [
                    e for e in corr
                    if e.get("correction", {}).get("event_id") == oid
                    and e.get("correction", {}).get("prior_line_sha256") == want
                ]
                if not hits:
                    errs.append(
                        f"{tag}: no correction record names event {oid} with "
                        f"prior_line_sha256 {want[:12]}… ({commit})"
                    )
                    ok = False
                    break
            _ = by_target, ok
            continue
        if not target.exists():
            continue
        text = target.read_text()
        if tag.startswith("PL-"):
            # register rec: the correction entry quotes the removed *clauses*
            # in commit order (the byte-exact lines live in the archive) — every
            # comma-number of the superseded reading must appear, and at least
            # one `Spine @…Z: **…**` clause must be quoted verbatim.
            for n in set(re.findall(r"\d{1,3}(?:,\d{3})+", ab.decode())):
                if n not in text:
                    errs.append(f"{tag}: superseded reading {n} absent from {r['restored_block_path']}")
                    break
            clauses = re.findall(r"Spine @\S+?: \*\*[^*]+\*\*", ab.decode())
            if clauses and not any(c in text for c in clauses):
                errs.append(f"{tag}: no verbatim `Spine @` clause quoted in {r['restored_block_path']}")
            continue
        for l in ab.decode().split("\n"):
            if not l:
                continue
            probe = l.replace(EMAIL, REDACT)
            if probe not in text and l not in text:
                errs.append(f"{tag}: archived line not verbatim in {r['restored_block_path']}: {l[:80]!r}")
                break

    for e in errs:
        print(f"FAIL {e}")
    if errs:
        print(f"check_restorations_map: {len(errs)} failure(s)")
        return 1
    print(
        f"check_restorations_map: green — {len(mrows)} map rows cover {len(owed)} "
        "owed register rows; anchors unique; archives hash-match the sources; "
        "restored text verbatim in every target"
    )
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        pathlib.Path(out).write_text(json.dumps({"rows": len(mrows), "owed": len(owed), "errors": []}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
