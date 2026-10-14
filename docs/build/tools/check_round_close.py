#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""check_round_close.py — the G9 round-close record checks, the capstone two-sum (G7 item 5)
and the tail probe-sweep contract (G10) of the amended SIG-ENG-031 (P34.33; ADR-199).

A round cannot close on records that were never kept. The checker runs **structure mode** in
`make docs-check` (`docs-check-round-close`, also a named step in the CI `docs` job) and
**tail mode** (`--round-tail <round-start>`) at the round tail — the invocation P38 and the
sub-round acceptance rows (P34.47, P35.64, P36.73) run. Stdlib only::

    python3 docs/build/tools/check_round_close.py check
    python3 docs/build/tools/check_round_close.py check --round-tail 2026-10-01 [--at ISO]

Structure mode (`record_policy/round_close.toml` is the policy):

* **RISK ids unique (G9).** A duplicate resolves only through an appended
  `Renamed RISK-…a by this record` inside a **dated** `## Round N review` — never a renamed row.
* **Every deferred RISK row is routed.** Deferred-class headings are check_backlog.py's; a row
  is routed by a BACKLOG `sources` owner, an id-cell `→ BL-nnn` cite, or a corrections-table
  record; every named BL must exist; a re-home (cite ≠ owner) needs the appended record; a
  `Re-homed … → BL-nnn` target must be **open**. A closed/accepted owner is a discharged
  deferral (F-32 §52), not a missing home — the defect class is the unrouted row
  (RISK-P21-03's shape).
* **Round ↔ spec.** Each `### Round N` heading inside the manifest's `## The chain` that opens
  a chain table cites an existing spec part/section; the policy exempts Rounds 2–9 and
  requires Round 11 → `Part XII` + `§56`.
* **Frozen views.** `docs/traceability.md` and `docs/build/TICKET_VS_SPEC.md` are frozen
  Phase-0…P18 views; each carries the appended `Frozen historical view` pointer.
* **Capstone two-sum (G7 item 5; SIG-ENG-041).** A packet under the declared patterns whose
  headline makes a bare `<count> <verdict>` claim must declare
  `coverage two-sum[<layer>]: engineering closed = N · requirement satisfied = M`, recomputed
  from `COVERAGE_MATRIX.csv` — engineering closed = MET + MET-DIFFERENTLY + MET-ENGINEERED,
  requirement satisfied = MET + MET-DIFFERENTLY; `[<layer>]` scopes to an `achieved_domain`
  value. Every bare claim is verified against the matrix count — `N MET` with MET-ENGINEERED
  folded in fails. A qualified count (`MISSING-with-…`) is not a matrix claim by grammar.
  Historical packets are exempt *by date, listed* — a vacuous exemption fails.

Tail mode adds: the `## Round N review` for the LEDGER's `round:` dated ≥ round start;
`adr_triggers.check(round_tail=…)` — P34.32's mode, called never duplicated; and the
`record_policy/tail_probe_sweep.toml` contract — every listed G10 probe needs a committed
`sig.probe-run/1` record ≤ 24 h old at `--at` (the packet commit; default now) that evaluated
something (an empty `checks` or all-`skipped` record fails, G11).

Every leg reports candidates/evaluated; a non-empty candidate set evaluated-to-zero exits 3.
Exit codes: 0 OK · 1 violations · 2 usage/input error · 3 vacuous.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
import tomllib
from datetime import UTC, datetime, timedelta

_TOOLS = pathlib.Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))  # sibling tools are importable from a --root fixture too

import adr_triggers  # noqa: E402  — tail mode consumes its --round-tail leg (P34.32)
import check_coverage_matrix as ccm  # noqa: E402  — the verdict grammar the two-sum reads

ROOT = pathlib.Path(__file__).resolve().parents[3]

RISK = "docs/risk_register.md"
MANIFEST = "docs/tickets/00_MANIFEST.md"
BACKLOG = "docs/build/BACKLOG.csv"
SPEC = "docs/2_canonical_design_spec.md"
MATRIX = "docs/build/COVERAGE_MATRIX.csv"
LEDGER = "docs/build/LEDGER.md"
POLICY = "docs/build/tools/record_policy/round_close.toml"
SWEEP = "docs/build/tools/record_policy/tail_probe_sweep.toml"
FROZEN_VIEW_FILES = ("docs/traceability.md", "docs/build/TICKET_VS_SPEC.md")
FROZEN_VIEW_MARK = "Frozen historical view"
PROBE_RECORD_DIR = "docs/build/reports/probes/"
PROBE_RECORD_SCHEMES = ("docs/build/reports/probes/", "gs://")
PROBE_FRESHNESS = timedelta(hours=24)

# Deferred-class risk-register headings — the same class list check_backlog.py uses.
DEFERRED_HEADING = re.compile(
    r"Deferred|Out of scope|Scaffolded|Unverifiable|not-fully-closed|Bounded", re.I
)
_CORR_HEADING = re.compile(r"orrection|re-route", re.I)
_RISK_DEF_RE = re.compile(r"^\|\s*(RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)\b")
_DEF_ROW_RE = re.compile(r"^\|\s*(RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)\s*(?:→\s*\**\s*(BL-\d{3}))?")
_RENAME_RE = re.compile(r"Renamed (RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+) by this record")
_ROUND_REVIEW_RE = re.compile(r"^##\s+Round\s+(\d+)\s+review\b")
_RECORDED_RE = re.compile(r"recorded\s+(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?)")
# A re-route record is a "Re-homed … → **BL-nnn**" / "Re-routed → BL-nnn" phrase — the
# BL after the arrow in that phrase is the new home. A bare `→ BL-nnn` elsewhere in a
# row (a quoted residue line, a historical cite) is prose, not a re-route.
_REROUTE_RE = re.compile(r"(?:Re-homed|Re-routed)\b[^|`]{0,80}?→\s*\**\s*(BL-\d{3})")
_CORR_ID_RE = re.compile(r"RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")

_CHAIN_HEAD_RE = re.compile(r"^##\s+The chain\b")
_BANNER_RE = re.compile(r"^###\s+Round\s+(\d+)\b")
_BANNER_ROUNDS_RE = re.compile(r"\bRound\s+(\d+)\b")
_TABLE_HEAD_RE = re.compile(r"^\|\s*#\s*\|")
_SPEC_PART_RE = re.compile(r"\bPart\s+([IVXLC]+)\b")
_SPEC_SECT_RE = re.compile(r"§\s*(\d+(?:\.\d+)?)")
_SPEC_PART_HEAD_RE = re.compile(r"^#\s+Part\s+([IVXLC]+)\b", re.M)
_SPEC_SECT_HEAD_RE = re.compile(r"^#{2,4}\s+(\d+(?:\.\d+)?)\.", re.M)

_VERDICT_WORDS = sorted(ccm.BASE_VERDICTS, key=len, reverse=True)
_WORD_ALT = "|".join(_VERDICT_WORDS)
# A coverage-count claim: "<n> <word>" ("34 MET", "62 MET-DIFFERENTLY") or
# "<word> count <n>" ("MET-DIFFERENTLY count is 77"). The verdict word must be bare —
# a qualified verdict ("MISSING-with-recorded-deferral", "MET-ENGINEERED(D-…)") is not
# a bare matrix count by grammar.
_CLAIM_AFTER_RE = re.compile(rf"(?<![\w'/-])(\d[\d,]*)\s+(?:verdicts?\s+)?({_WORD_ALT})(?![-\w(])")
_CLAIM_BEFORE_RE = re.compile(
    rf"\b({_WORD_ALT})(?![-\w(])[^.\n|]{{0,30}}?\bcount\b[^0-9]{{0,15}}(\d[\d,]*)"
)
_TWO_SUM_RE = re.compile(
    r"coverage\s+two-sum(?:\s*\[([^\]\s]+)\])?\s*:\s*engineering\s+closed\s*=\s*(\d+)"
    r"\s*·\s*requirement\s+satisfied\s*=\s*(\d+)"
)
_MD_MARKS_RE = re.compile(r"[`*]")

_LEDGER_ROUND_RE = re.compile(r"^round:\s*(\d+)", re.M)
_ISO_TS_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?Z?$")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PROBE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_OWNER_RE = re.compile(r"^(P\d+\.\d+[a-z]?|SEED-\d+[a-z]?|PLAN-[A-Z0-9]+)$")

EC_WORDS = frozenset({"MET", "MET-DIFFERENTLY", "MET-ENGINEERED"})
RS_WORDS = frozenset({"MET", "MET-DIFFERENTLY"})


def _parse_ts(text: str) -> datetime | None:
    """`date -u` timestamps: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM[:SS]Z`."""
    text = text.strip()
    m = _ISO_TS_RE.match(text)
    if m:
        return datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            int(m.group(5)),
            int(m.group(6) or 0),
            tzinfo=UTC,
        )
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        y, mo, d = (int(p) for p in text.split("-"))
        return datetime(y, mo, d, tzinfo=UTC)
    return None


def _backlog(root: pathlib.Path) -> tuple[list[dict[str, str]], dict[str, str], dict[str, str]]:
    """(rows, bl_id → status, source-id → owning bl_id)."""
    path = root / BACKLOG
    if not path.is_file():
        return [], {}, {}
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    status = {r["bl_id"]: r["status"] for r in rows}
    owner: dict[str, str] = {}
    for r in rows:
        for s in (r.get("sources") or "").split():
            owner.setdefault(s, r["bl_id"])
    return rows, status, owner


def _risk_scan(text: str) -> dict:
    """One pass over the risk register.

    Returns definition counts, rename records (each flagged by whether it sits inside a
    dated ``## Round N review`` section), deferred-class rows (id + id-cell cite),
    corrections-table ids and their ``→ BL-nnn`` re-route targets, and the dated
    round-review sections.
    """
    defs: dict[str, int] = {}
    renames: list[tuple[str, str, bool]] = []  # (base id, renamed id, inside dated review)
    deferred: list[tuple[str, str | None, int]] = []  # (id, id-cell cite, line no)
    corr_ids: dict[str, list[str]] = {}  # id → re-route targets (may be [])
    reviews: list[tuple[int, str | None, int]] = []  # (round, recorded ts, line no)
    in_deferred = False
    in_corr = False
    review_round: int | None = None  # current `## ` is a dated round review for this round
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = _ROUND_REVIEW_RE.match(line)
            review_round = None
            if m:
                rm = _RECORDED_RE.search(line)
                reviews.append((int(m.group(1)), rm.group(1) if rm else None, n))
                review_round = int(m.group(1)) if rm else None
            in_deferred = False
            in_corr = False
            continue
        if line.startswith("### "):
            in_deferred = DEFERRED_HEADING.search(line) is not None
            in_corr = _CORR_HEADING.search(line) is not None
            continue
        if line.startswith("#"):
            in_deferred = False
            continue
        rm = _RENAME_RE.search(line)
        if rm:
            # a rename record counts wherever it sits (check_backlog parity) — but the
            # G9 rule below requires it inside a dated '## Round N review' section
            base = re.sub(r"[a-z]$", "", rm.group(1))
            renames.append((base, rm.group(1), review_round is not None))
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        if in_corr:
            # a corrections/re-route table: first cell names the corrected id(s); a
            # `→ BL-nnn` in the rest of the row is the appended re-route target.
            cells = [c.strip() for c in line.split("|")]
            first = cells[1] if len(cells) > 1 else ""
            ids = [i for i in _CORR_ID_RE.findall(first) if i != "RISK"]
            targets = _REROUTE_RE.findall("|".join(cells[2:]))
            for i in ids:
                corr_ids.setdefault(i, [])
                corr_ids[i].extend(t for t in targets if t not in corr_ids[i])
            continue
        m = _RISK_DEF_RE.match(line)
        if m and not in_corr:
            defs[m.group(1)] = defs.get(m.group(1), 0) + 1
        if in_deferred:
            dm = _DEF_ROW_RE.match(line)
            if dm:
                deferred.append((dm.group(1), dm.group(2), n))
    return {
        "defs": defs,
        "renames": renames,
        "deferred": deferred,
        "corr_ids": corr_ids,
        "reviews": reviews,
    }


def check_risk_register(root: pathlib.Path) -> tuple[list[str], dict[str, int]]:
    """G9 risk legs: unique ids via dated appended disambiguation; every deferred row routed."""
    errors: list[str] = []
    stats = {"risk_defs": 0, "renames": 0, "deferred": 0, "deferred_evaluated": 0}
    path = root / RISK
    if not path.is_file():
        return [f"{RISK} not found"], stats
    scan = _risk_scan(path.read_text())
    _, bl_status, bl_owner = _backlog(root)
    stats["risk_defs"] = len(scan["defs"])
    stats["renames"] = len(scan["renames"])
    stats["deferred"] = len(scan["deferred"])

    # 1. RISK ids unique — a duplicate resolves only through rename records.
    rename_count: dict[str, int] = {}
    for base, _new, _dated in scan["renames"]:
        rename_count[base] = rename_count.get(base, 0) + 1
    for rid, n in sorted(scan["defs"].items()):
        if n - rename_count.get(rid, 0) > 1:
            errors.append(
                f"{RISK}: {rid} heads {n} definition rows with "
                f"{rename_count.get(rid, 0)} rename record(s) — a duplicate RISK id resolves "
                "only through an appended 'Renamed RISK-…a by this record' (never a renamed row)"
            )
    for base, new, dated in scan["renames"]:
        if not dated:
            errors.append(
                f"{RISK}: 'Renamed {new} by this record' sits outside a dated "
                "'## Round N review' section — the disambiguation is an appended, dated record"
            )
        if base not in scan["defs"]:
            errors.append(
                f"{RISK}: rename record names {base} but no definition row carries that id"
            )

    # 2. Every deferred RISK row is routed: a BL owner (sources), an id-cell `→ BL-nnn` cite
    #    or a corrections-table record; every named BL exists; a re-home is recorded; an
    #    appended re-route lands on an open row.
    for rid, cite, line in scan["deferred"]:
        stats["deferred_evaluated"] += 1
        owner = bl_owner.get(rid)
        corr = rid in scan["corr_ids"]
        where = f"{RISK}:{line} ({rid})"
        if owner is None and cite is None and not corr:
            errors.append(
                f"{where}: deferred RISK row is unrouted — no BACKLOG owner, no `→ BL-nnn` "
                "id-cell cite, no corrections-table record (G9 open-home rule; RISK-P21-03's "
                "defect class)"
            )
            continue
        if cite is not None and cite not in bl_status:
            errors.append(f"{where}: id-cell cite → {cite} is not a BACKLOG row")
        if owner is not None and cite is not None and cite != owner and not corr:
            errors.append(
                f"{where}: re-homed {cite} → {owner} in BACKLOG sources with no "
                "corrections-table record — a re-home is an appended routing note"
            )
    for rid, targets in scan["corr_ids"].items():
        for t in targets:
            if t not in bl_status:
                errors.append(
                    f"{RISK} corrections ({rid}): re-route target {t} is not a BACKLOG row"
                )
            elif bl_status[t] != "open":
                errors.append(
                    f"{RISK} corrections ({rid}): re-route target {t} is {bl_status[t]!r}, "
                    "not open — an appended routing note lands on an owed BL row"
                )
    return errors, stats


def _chain_banners(manifest_text: str) -> tuple[list[tuple[int, int, str]], int]:
    """``### Round N`` headings inside `## The chain` that open a chain table.

    Returns ``(banners, candidates)`` where each banner is ``(line, round, heading)`` and
    candidates counts every ``### Round`` heading seen inside the chain block (a heading
    that opens no table is not a banner — it heads notes, not rows).
    """
    banners: list[tuple[int, int, str]] = []
    candidates = 0
    in_chain = False
    pending: tuple[int, int, str] | None = None
    seen_table = False
    for n, line in enumerate(manifest_text.splitlines(), 1):
        if line.startswith("## "):
            if pending is not None and seen_table:
                banners.append(pending)
            pending = None
            seen_table = False
            in_chain = bool(_CHAIN_HEAD_RE.match(line))
            continue
        if not in_chain:
            continue
        if line.startswith("### "):
            if pending is not None and seen_table:
                banners.append(pending)
            pending = None
            seen_table = False
            m = _BANNER_RE.match(line)
            if m:
                candidates += 1
                pending = (n, int(m.group(1)), line.strip())
            continue
        if pending is not None and _TABLE_HEAD_RE.match(line):
            seen_table = True
    if pending is not None and seen_table:
        banners.append(pending)
    return banners, candidates


def _spec_cites(spec_text: str) -> tuple[set[str], set[str]]:
    """(parts, sections) — the cite targets that exist: `# Part XII`, `## 56.`/`### 56.3`."""
    return set(_SPEC_PART_HEAD_RE.findall(spec_text)), set(_SPEC_SECT_HEAD_RE.findall(spec_text))


def check_banners(root: pathlib.Path, policy: dict) -> tuple[list[str], dict[str, int]]:
    """G9 round ↔ spec part: each chain-table `### Round N` banner cites an existing part."""
    errors: list[str] = []
    stats = {"banners": 0, "banners_evaluated": 0}
    mpath, spath = root / MANIFEST, root / SPEC
    if not mpath.is_file():
        return [f"{MANIFEST} not found"], stats
    if not spath.is_file():
        return [f"{SPEC} not found"], stats
    parts, sections = _spec_cites(spath.read_text())
    exempt = set(policy.get("banners", {}).get("exempt_rounds", []))
    required = {int(k): v for k, v in policy.get("banners", {}).get("required_cites", {}).items()}
    banners, candidates = _chain_banners(mpath.read_text())
    stats["banners"] = candidates
    for line, _round, heading in banners:
        stats["banners_evaluated"] += 1
        where = (
            f"{MANIFEST}:{line} ({heading[:60]}…)"
            if len(heading) > 60
            else (f"{MANIFEST}:{line} ({heading})")
        )
        rounds = [int(r) for r in _BANNER_ROUNDS_RE.findall(heading)]
        for rnd in rounds:
            if rnd in exempt:
                continue
            if rnd in required:
                for cite in required[rnd]:
                    if cite not in heading:
                        errors.append(
                            f"{where}: Round {rnd} banner must cite {cite!r} "
                            "(policy banners.required_cites)"
                        )
                continue
            cites = _SPEC_PART_RE.findall(heading) + _SPEC_SECT_RE.findall(heading)
            resolved = [p for p in _SPEC_PART_RE.findall(heading) if p in parts] + [
                s for s in _SPEC_SECT_RE.findall(heading) if s in sections
            ]
            if not cites:
                errors.append(
                    f"{where}: Round {rnd} banner cites no spec part/section "
                    "(G9 round ↔ spec part; exempt rounds live in the policy)"
                )
            elif not resolved:
                errors.append(
                    f"{where}: Round {rnd} banner cites {cites} — none resolves to a "
                    "spec part/section heading"
                )
        # a required cite that resolves to nothing in the spec is a policy error, seen
        # from the banner side too
        for rnd in rounds:
            if rnd in required:
                for cite in required[rnd]:
                    pm = _SPEC_PART_RE.search(cite)
                    sm = _SPEC_SECT_RE.search(cite)
                    if pm and pm.group(1) not in parts:
                        errors.append(
                            f"policy: required cite {cite!r} for Round {rnd} names "
                            f"Part {pm.group(1)} — no such spec part"
                        )
                    if sm and sm.group(1) not in sections:
                        errors.append(
                            f"policy: required cite {cite!r} for Round {rnd} names "
                            f"§{sm.group(1)} — no such spec section"
                        )
    return errors, stats


def check_frozen_pointers(root: pathlib.Path) -> tuple[list[str], dict[str, int]]:
    """The G9 amendment freezes traceability.md / TICKET_VS_SPEC.md as historical views —
    each carries the appended pointer."""
    errors: list[str] = []
    stats = {"frozen_views": len(FROZEN_VIEW_FILES), "frozen_evaluated": 0}
    for rel in FROZEN_VIEW_FILES:
        path = root / rel
        stats["frozen_evaluated"] += 1
        if not path.is_file():
            errors.append(f"{rel} not found")
            continue
        if FROZEN_VIEW_MARK not in path.read_text():
            errors.append(
                f"{rel}: no appended '{FROZEN_VIEW_MARK}' pointer — the file is a frozen "
                "Phase-0…P18 view and must point at COVERAGE_MATRIX.csv (G9 amendment)"
            )
    return errors, stats


def _matrix_counts(
    root: pathlib.Path,
) -> tuple[dict[str, dict[str, int]], int, str | None]:
    """Per-verdict counts overall and per ``achieved_domain`` status layer.

    Returns ``(counts, rows, error)`` — ``counts[layer][word]``; layer ``""`` is the
    overall sum over all rows.
    """
    path = root / MATRIX
    if not path.is_file():
        return {}, 0, f"{MATRIX} not found"
    counts: dict[str, dict[str, int]] = {}
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    def bump(layer: str, word: str) -> None:
        counts.setdefault(layer, {})
        counts[layer][word] = counts[layer].get(word, 0) + 1

    for r in rows:
        word = ccm.verdict_word(r.get("verdict", ""))
        if word is None:
            continue
        bump("", word)
        dom = (r.get("achieved_domain") or "").strip()
        if dom and dom != "—":
            bump(dom, word)
    return counts, len(rows), None


def _two_sum(counts_for_layer: dict[str, int]) -> tuple[int, int]:
    ec = sum(counts_for_layer.get(w, 0) for w in EC_WORDS)
    rs = sum(counts_for_layer.get(w, 0) for w in RS_WORDS)
    return ec, rs


def check_packets(root: pathlib.Path, policy: dict) -> tuple[list[str], dict[str, int]]:
    """The capstone two-sum (G7 item 5): a packet giving coverage counts states both sums."""
    errors: list[str] = []
    stats = {"packets": 0, "packets_evaluated": 0, "claims": 0}
    counts, nrows, err = _matrix_counts(root)
    if err:
        return [err], stats
    pk = policy.get("packets", {})
    patterns = pk.get("patterns", [])
    exempt = {e["path"]: e for e in pk.get("exempt", [])}
    matched: set[str] = set()
    for pat in patterns:
        # the declared patterns are repo-root-relative globs
        for p in sorted(root.glob(pat)):
            if p.is_file():
                matched.add(str(p.relative_to(root)))
    stats["packets"] = len(matched)
    for rel in sorted(matched):
        text = _MD_MARKS_RE.sub("", (root / rel).read_text())
        claims: list[tuple[str, int]] = []
        for m in _CLAIM_AFTER_RE.finditer(text):
            claims.append((m.group(2), int(m.group(1).replace(",", ""))))
        for m in _CLAIM_BEFORE_RE.finditer(text):
            claims.append((m.group(1), int(m.group(2).replace(",", ""))))
        sums = [
            (m.group(1) or "", int(m.group(2)), int(m.group(3))) for m in _TWO_SUM_RE.finditer(text)
        ]
        if rel in exempt:
            # exempt by date, listed — the exemption must not be vacuous
            e = exempt[rel]
            stats["packets_evaluated"] += 1
            if not claims:
                errors.append(
                    f"{rel}: exempt by date ({e.get('date')}) but carries no coverage-count "
                    "claim — a vacuous exemption is removed"
                )
            if str(e.get("date", "")) not in text:
                errors.append(
                    f"{rel}: exempt date {e.get('date')!r} does not appear in the packet — "
                    "the by-date list names the packet's own recorded date"
                )
            continue
        if not claims:
            continue  # a packet without coverage-count claims owes no two-sum
        stats["packets_evaluated"] += 1
        stats["claims"] += len(claims)
        if not sums:
            errors.append(
                f"{rel}: headline coverage counts ({len(claims)} claim(s)) but no "
                "'coverage two-sum: engineering closed = N · requirement satisfied = M' "
                "declaration — SIG-ENG-041 reports both sums, never 'N MET' alone"
            )
        for layer, ec, rs in sums:
            key = layer
            if key not in counts:
                errors.append(
                    f"{rel}: 'coverage two-sum [{layer}]' names an unknown status layer "
                    f"(achieved_domain values: {sorted(k for k in counts if k)})"
                )
                continue
            exp_ec, exp_rs = _two_sum(counts[key])
            if (ec, rs) != (exp_ec, exp_rs):
                errors.append(
                    f"{rel}: coverage two-sum{f' [{layer}]' if layer else ''} declares "
                    f"engineering closed = {ec} · requirement satisfied = {rs}; the matrix "
                    f"recomputes {exp_ec} · {exp_rs} (MET + MET-DIFFERENTLY "
                    f"[+ MET-ENGINEERED for engineering closed])"
                )
        # every bare word-count claim equals the matrix count — a folded or stale count
        # ('34 MET', MET-ENGINEERED counted into MET) is caught here.
        for word, n in claims:
            actual = counts.get("", {}).get(word, 0)
            if n != actual:
                errors.append(
                    f"{rel}: claims {n} {word} — the matrix counts {actual} "
                    "(coverage counts are recomputed, never hand-set)"
                )
    for rel in exempt:
        if rel not in matched:
            errors.append(
                f"policy: exempt packet {rel} matches no declared packet path "
                "(the by-date list names packets under the declared patterns)"
            )
    return errors, stats


def load_policy(root: pathlib.Path) -> tuple[dict, str | None]:
    path = root / POLICY
    if not path.is_file():
        return {}, f"{POLICY} not found"
    try:
        with path.open("rb") as fh:
            policy = tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        return {}, f"{POLICY}: TOML parse error: {e}"
    if policy.get("schema") != "round-close-policy/1":
        return {}, f"{POLICY}: schema {policy.get('schema')!r} != 'round-close-policy/1'"
    return policy, None


def load_sweep(root: pathlib.Path) -> tuple[list[dict], str | None]:
    """The tail probe-sweep contract (G10 tail column): validated in both modes."""
    path = root / SWEEP
    if not path.is_file():
        return [], f"{SWEEP} not found"
    try:
        with path.open("rb") as fh:
            doc = tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        return [], f"{SWEEP}: TOML parse error: {e}"
    if doc.get("schema") != "tail-probe-sweep/1":
        return [], f"{SWEEP}: schema {doc.get('schema')!r} != 'tail-probe-sweep/1'"
    probes = doc.get("probe", [])
    errors: list[str] = []
    seen: set[str] = set()
    for p in probes:
        pid = p.get("id", "")
        where = f"{SWEEP} probe {pid!r}"
        if not _PROBE_ID_RE.match(pid):
            errors.append(f"{where}: id is not a slug token")
        if pid in seen:
            errors.append(f"{where}: duplicate probe id")
        seen.add(pid)
        if not p.get("requires"):
            errors.append(f"{where}: no requirement ids (the probe traces to a requirement)")
        owner = p.get("owner", "")
        if not _OWNER_RE.match(owner):
            errors.append(f"{where}: owner {owner!r} is not a chain-row/seed id")
        if not str(p.get("command", "")).strip():
            errors.append(f"{where}: no producer command — the contract names what runs it")
        rec = str(p.get("record", ""))
        if not any(rec.startswith(s) for s in PROBE_RECORD_SCHEMES) or not rec.endswith(".json"):
            errors.append(
                f"{where}: record {rec!r} — the expected probe-run/1 record lands under "
                "docs/build/reports/probes/*.json (or a cited gs:// path)"
            )
    if errors:
        return [], "; ".join(errors)
    return probes, None


def check_probe_sweep(
    probes: list[dict], root: pathlib.Path, at: datetime
) -> tuple[list[str], dict[str, int]]:
    """Tail leg: every listed probe has a fresh, non-vacuous `probe-run/1` record."""
    errors: list[str] = []
    stats = {"probes": len(probes), "probes_evaluated": 0}
    for p in probes:
        stats["probes_evaluated"] += 1
        pid, rec = p["id"], str(p["record"])
        where = f"probe {pid}"
        if rec.startswith("gs://"):
            # a GCS-cited record is verified by its publisher's own digest; the tail check
            # only judges committed records — flag it explicitly rather than silently pass
            errors.append(
                f"{where}: record {rec} is a GCS path — the tail check reads committed "
                f"records under {PROBE_RECORD_DIR} (G10)"
            )
            continue
        path = root / rec
        if not path.is_file():
            errors.append(
                f"{where}: no {rec} — the tail sweep requires every listed probe's "
                "probe-run/1 record (SIG-MEM-011)"
            )
            continue
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{where}: {rec} is not JSON ({e})")
            continue
        for key in ("version", "generated_at", "checks", "overall"):
            if key not in doc:
                errors.append(f"{where}: {rec} lacks '{key}' — not a probe-run/1 record")
        gen = _parse_ts(str(doc.get("generated_at", "")))
        if gen is None:
            errors.append(
                f"{where}: generated_at {doc.get('generated_at')!r} is not a date -u timestamp"
            )
        else:
            if gen > at + timedelta(minutes=5):
                errors.append(
                    f"{where}: generated_at {doc['generated_at']} postdates the packet commit "
                    f"({at.isoformat()}) — the record was not there when the packet closed"
                )
            elif at - gen > PROBE_FRESHNESS:
                errors.append(
                    f"{where}: generated_at {doc['generated_at']} is older than 24 h at "
                    f"{at.isoformat()} — the tail re-runs the sweep (G10)"
                )
        checks = doc.get("checks")
        if isinstance(checks, dict):
            verdicts = [c.get("verdict") for c in checks.values() if isinstance(c, dict)]
            if not verdicts:
                errors.append(f"{where}: {rec} evaluated nothing — 'checks' is empty (G11)")
            elif all(v == "skipped" for v in verdicts):
                errors.append(
                    f"{where}: {rec} evaluated nothing — every leg skipped (a scheduled "
                    "job that measured nothing fails, G11)"
                )
    return errors, stats


def check_round_review(
    root: pathlib.Path, round_tail: str, reviews: list[tuple[int, str | None, int]]
) -> list[str]:
    """Tail leg: `## Round N review` (N = LEDGER round) dated within the round."""
    errors: list[str] = []
    ledger = root / LEDGER
    if not ledger.is_file():
        return [f"{LEDGER} not found — tail mode reads the round from `round:`"]
    m = _LEDGER_ROUND_RE.search(ledger.read_text())
    if not m:
        return [f"{LEDGER}: no `round:` key — the tail cannot name the round being closed"]
    rnd = int(m.group(1))
    found = [r for r in reviews if r[0] == rnd]
    if not found:
        return [
            f"{RISK}: no '## Round {rnd} review' section — the amended SIG-ENG-031 "
            "requires a dated round review at each round close"
        ]
    if any(rec and rec[:10] >= round_tail for _r, rec, _ln in found):
        return errors
    for _r, rec, line in found:
        if rec is None:
            errors.append(
                f"{RISK}:{line}: '## Round {rnd} review' carries no `recorded <ts>` — "
                "a round review is a dated record"
            )
        else:
            errors.append(
                f"{RISK}:{line}: '## Round {rnd} review' recorded {rec} predates the "
                f"round start {round_tail} — the review lands inside the round "
                "(SIG-ENG-031)"
            )
    return errors


def check(
    root: pathlib.Path,
    round_tail: str | None = None,
    at: datetime | None = None,
) -> tuple[list[str], dict[str, int]]:
    """All legs; ``(errors, stats)``. Tail mode adds the round-review, trigger-register
    and probe-sweep legs."""
    errors: list[str] = []
    stats: dict[str, int] = {}

    policy, perr = load_policy(root)
    if perr:
        return [perr], stats
    probes, serr = load_sweep(root)
    if serr:
        return [serr], stats

    for e, s in (
        check_risk_register(root),
        check_banners(root, policy),
        check_frozen_pointers(root),
        check_packets(root, policy),
    ):
        errors.extend(e)
        stats.update(s)
    stats["sweep_probes"] = len(probes)

    if round_tail is not None:
        at = at or datetime.now(UTC)
        scan = _risk_scan((root / RISK).read_text()) if (root / RISK).is_file() else {"reviews": []}
        errors.extend(check_round_review(root, round_tail, scan["reviews"]))
        at_errors, at_stats = adr_triggers.check(root, round_tail=round_tail)
        errors.extend(f"adr_triggers --round-tail: {e}" for e in at_errors)
        stats["triggers_evaluated"] = at_stats.get("evaluated", 0)
        e, s = check_probe_sweep(probes, root, at)
        errors.extend(e)
        stats.update(s)

    # G11: a non-empty candidate set that evaluated nothing is vacuous, not green.
    for cand_key, eval_key, label in (
        ("deferred", "deferred_evaluated", "deferred risk rows"),
        ("banners", "banners_evaluated", "round banners"),
        ("packets", "packets_evaluated", "coverage packets"),
        ("frozen_views", "frozen_evaluated", "frozen-view pointers"),
    ):
        if stats.get(cand_key, 0) > 0 and stats.get(eval_key, 0) == 0:
            errors.append(f"VACUOUS: {label} offered {stats[cand_key]} but evaluated none (G11)")
    if (
        round_tail is not None
        and stats.get("probes", 0) > 0
        and stats.get("probes_evaluated", 0) == 0
    ):
        errors.append("VACUOUS: probe sweep offered probes but evaluated none (G11)")
    return errors, stats


def _fmt_stats(stats: dict[str, int]) -> str:
    parts = [
        f"risk-ids {stats.get('risk_defs', 0)} defs / {stats.get('renames', 0)} renames",
        f"deferred {stats.get('deferred_evaluated', 0)}/{stats.get('deferred', 0)}",
        f"banners {stats.get('banners_evaluated', 0)}/{stats.get('banners', 0)}",
        f"frozen-views {stats.get('frozen_evaluated', 0)}/{stats.get('frozen_views', 0)}",
        f"packets {stats.get('packets_evaluated', 0)}/{stats.get('packets', 0)}"
        f" ({stats.get('claims', 0)} claims)",
        f"sweep {stats.get('sweep_probes', 0)} probes",
    ]
    if "probes" in stats:
        parts.append(f"probe-records {stats.get('probes_evaluated', 0)}/{stats.get('probes', 0)}")
    if "triggers_evaluated" in stats:
        parts.append(f"triggers {stats['triggers_evaluated']}")
    return " · ".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--root", default=str(ROOT))
    sub = ap.add_subparsers(dest="cmd")
    cp = sub.add_parser("check", help="structure checks; --round-tail adds the tail legs")
    cp.add_argument(
        "--round-tail",
        metavar="YYYY-MM-DD",
        default=None,
        help="tail mode: round start — the Round-N review must be dated inside the round, "
        "adr_triggers runs its --round-tail leg, and every probe in tail_probe_sweep.toml "
        "needs a fresh, non-vacuous probe-run/1 record",
    )
    cp.add_argument(
        "--at",
        metavar="ISO",
        default=None,
        help="the packet-commit timestamp probe records are judged against (default: now)",
    )
    cp.add_argument("--json", metavar="PATH", default=None, help="write a JSON report")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    if args.cmd != "check":
        ap.print_help()
        return 2
    if args.round_tail is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.round_tail):
        print(
            f"--round-tail {args.round_tail!r} is not a YYYY-MM-DD round-start date",
            file=sys.stderr,
        )
        return 2
    at = None
    if args.at:
        at = _parse_ts(args.at)
        if at is None:
            print(f"--at {args.at!r} is not a date -u timestamp", file=sys.stderr)
            return 2
    errors, stats = check(root, round_tail=args.round_tail, at=at)
    print("offered/evaluated:", _fmt_stats(stats))
    report = {
        "tool": "check_round_close/1",
        "round_tail": args.round_tail,
        "at": (at.isoformat() if at else None),
        "stats": stats,
        "errors": errors,
    }
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")
    if any(e.startswith("VACUOUS:") for e in errors):
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 3
    if errors:
        print(f"check_round_close: FAIL — {len(errors)} problem(s):", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    tail = f" · round-tail from {args.round_tail} OK" if args.round_tail else ""
    print(f"check_round_close: OK{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
