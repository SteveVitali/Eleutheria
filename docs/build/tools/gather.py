#!/usr/bin/env python3
"""Gather per-id reference data for the 668 spec requirement ids (P19.2 analysis).

Read-only. Writes .agents/scratch/tools/id_data.json.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "docs" / "2_canonical_design_spec.md"

ID_DEF_RE = re.compile(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \((MUST|SHOULD|MAY|RATIONALE)")
ID_TOKEN_RE = re.compile(r"SIG-[A-Z]+-\d+[a-z]?")
RANGE_RE = re.compile(r"SIG-([A-Z]+)-(\d{3})([a-z]?)(?:\.\.\.?|…|–|—|-)(\d{3})")


def parse_spec():
    """Return dict id -> {level, line, section}."""
    ids = {}
    section = ""
    for i, raw in enumerate(SPEC.read_text().splitlines(), start=1):
        m = re.match(r"^(#{1,4}) (.*)", raw)
        if m:
            # keep top-level numbered section label for ## and ### headers
            title = m.group(2).strip()
            level = len(m.group(1))
            if level <= 3:
                section = title
        for mm in ID_DEF_RE.finditer(raw):
            sid, lvl = mm.group(1), mm.group(2)
            if sid not in ids:
                ids[sid] = {"level": lvl, "line": i, "section": section}
    return ids


def exact_refs(text, universe):
    return {tok for tok in ID_TOKEN_RE.findall(text) if tok in universe}


def expand_refs(text, universe):
    """Return set of ids from universe referenced in text (exact + range)."""
    found = set()
    for tok in ID_TOKEN_RE.findall(text):
        if tok in universe:
            found.add(tok)
    for m in RANGE_RE.finditer(text):
        prefix, start, _suf, end = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        if end < start or (end - start) > 120:
            continue
        for n in range(start, end + 1):
            cand = f"SIG-{prefix}-{n:03d}"
            if cand in universe:
                found.add(cand)
    return found


def gather_files(globs, base=ROOT):
    files = []
    for g in globs:
        files.extend(base.glob(g))
    return [f for f in files if f.is_file()]


def scan_class(files, universe):
    """Return dict id -> list of 'relpath' where referenced (first hits capped)."""
    hits = {}
    for f in files:
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        refs = expand_refs(text, universe)
        if not refs:
            continue
        rel = str(f.relative_to(ROOT)) if str(f).startswith(str(ROOT)) else str(f)
        for sid in refs:
            hits.setdefault(sid, [])
            if len(hits[sid]) < 6:
                hits[sid].append(rel)
    return hits


def scan_class_lineref(files, universe):
    """Return dict id -> 'relpath:line' first occurrence, for evidence citation."""
    hits = {}
    for f in files:
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(f.relative_to(ROOT))
        for ln, line in enumerate(lines, start=1):
            refs = expand_refs(line, universe)
            for sid in refs:
                if sid not in hits:
                    hits[sid] = f"{rel}:{ln}"
    return hits


def main():
    ids = parse_spec()
    universe = set(ids)
    print(f"universe: {len(universe)} ids")

    # evidence classes
    src_files = gather_files([
        "*/src/**/*.py", "*/src/**/*.sql", "web/src/**/*.astro", "web/src/**/*.ts",
        "web/src/**/*.tsx", "web/src/**/*.js", "db/deploy/**/*.sql", "db/**/*.sql",
        "ontology/**/*.py",
    ])
    test_files = gather_files(["tests/**/*.py", "*/tests/**/*.py"])
    web_test_files = gather_files(["web/tests/**/*.ts", "web/tests/**/*.js", "web/tests/**/*.tsx"])
    adr_files = gather_files(["docs/adr/ADR-*.md"])
    pr_files = [ROOT / ".agents/scratch/pr" / f"pr_{n}.md" for n in range(1, 47)]
    pr_files = [f for f in pr_files if f.exists()]
    trace_files = [ROOT / "docs" / "traceability.md"]
    risk_files = [ROOT / "docs" / "risk_register.md"]

    print("counts of files:",
          "src", len(src_files), "tests", len(test_files), "webtests", len(web_test_files),
          "adr", len(adr_files), "pr", len(pr_files))

    # exact-token presence (no range expansion) for conservative verdicts
    def exact_set(files):
        s = set()
        for f in files:
            try:
                s |= exact_refs(f.read_text(errors="ignore"), universe)
            except Exception:
                pass
        return s
    exact_src = exact_set(src_files)
    exact_tests = exact_set(test_files) | exact_set(web_test_files)

    # risk rows: id -> [RISK-xxx] found on same line in risk_register.md
    risk_rows = {}
    RISK_RE = re.compile(r"RISK-[A-Z0-9-]+")
    for f in risk_files:
        for line in f.read_text(errors="ignore").splitlines():
            refs = expand_refs(line, universe)
            rr = RISK_RE.findall(line)
            for sid in refs:
                for r in rr:
                    risk_rows.setdefault(sid, [])
                    if r not in risk_rows[sid]:
                        risk_rows[sid].append(r)

    src = scan_class(src_files, universe)
    src_line = scan_class_lineref(src_files, universe)
    tests = scan_class(test_files, universe)
    tests_line = scan_class_lineref(test_files, universe)
    webtests = scan_class(web_test_files, universe)
    webtests_line = scan_class_lineref(web_test_files, universe)
    adr = scan_class(adr_files, universe)
    pr = scan_class(pr_files, universe)
    trace = scan_class(trace_files, universe)
    risk = scan_class(risk_files, universe)

    # ADR requirement-ids field mapping: id -> [ADR-xxx]
    adr_reqids = {}
    for f in adr_files:
        text = f.read_text(errors="ignore")
        mid = re.match(r"(ADR-\d+)", f.stem)
        adr_id = mid.group(1) if mid else f.stem  # e.g. ADR-030
        m = re.search(r"(?im)^\s*[-*]?\s*\**Requirement ids\**\s*[:：]?\s*(.*)$", text)
        line = m.group(1) if m else ""
        refs = expand_refs(line, universe) if line else set()
        # fallback: sometimes ids span multiple lines after header
        for sid in refs:
            adr_reqids.setdefault(sid, []).append(adr_id)

    # PR ownership: id -> [pr numbers]
    pr_owner = {}
    for f in pr_files:
        n = int(f.stem.split("_")[1])
        refs = expand_refs(f.read_text(errors="ignore"), universe)
        for sid in refs:
            pr_owner.setdefault(sid, []).append(n)

    out = {}
    for sid, meta in ids.items():
        out[sid] = {
            "level": meta["level"],
            "spec_line": meta["line"],
            "section": meta["section"],
            "in_src": sid in src,
            "exact_src": sid in exact_src,
            "exact_tests": sid in exact_tests,
            "risk_rows": risk_rows.get(sid, []),
            "in_tests": sid in tests,
            "in_webtests": sid in webtests,
            "in_adr": sid in adr,
            "in_pr": sid in pr,
            "in_trace": sid in trace,
            "in_risk": sid in risk,
            "src_ev": src_line.get(sid),
            "test_ev": tests_line.get(sid),
            "webtest_ev": webtests_line.get(sid),
            "adr_reqids": sorted(set(adr_reqids.get(sid, []))),
            "adr_any": sorted(set(adr.get(sid, [])))[:4],
            "pr_owner": sorted(set(pr_owner.get(sid, []))),
            "src_paths": src.get(sid, [])[:3],
            "test_paths": tests.get(sid, [])[:3],
        }
    outpath = ROOT / ".agents/scratch/tools/id_data.json"
    outpath.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"wrote {outpath} ({len(out)} ids)")

    # sanity roll-ups
    def cnt(k):
        return sum(1 for v in out.values() if v[k])
    print("in_tests:", cnt("in_tests"), "in_src:", cnt("in_src"),
          "in_adr:", cnt("in_adr"), "in_pr:", cnt("in_pr"),
          "in_trace:", cnt("in_trace"), "in_risk:", cnt("in_risk"),
          "in_webtests:", cnt("in_webtests"))


if __name__ == "__main__":
    main()
