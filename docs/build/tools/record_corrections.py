#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.
"""Validate evidenced, append-only interpretations; never rewrite original records.

Only readout-pointer/gate-row recording-time upper bounds and a PHASE LOG
header's markup-only spelling are supported. Every other date, shape and history rule
continues to judge the original bytes. See record_policy/record_corrections.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REGISTER = "docs/build/reports/memory-repair/record_corrections.jsonl"
LEDGER = "docs/build/LEDGER.md"
SCHEMA = "record-correction/1"
FIELDS = {
    "schema",
    "kind",
    "recorded_at",
    "path",
    "source_commit",
    "source_line",
    "line_sha256",
    "interpretation",
}
KINDS = {"readout-pointer-date", "gate-row-recording-date", "phase-log-heading-markup"}


@dataclass
class Corrections:
    candidates: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)
    dates: dict[tuple[str, str], str] = field(default_factory=dict)
    headings: set[tuple[str, str]] = field(default_factory=set)


def stamp(value: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise ValueError("timestamps require an exact UTC clock reading including seconds")
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def load(root: Path, read: Callable[[str], str | None], revision: str, now: int) -> Corrections:
    """Validate the complete register at this snapshot, failing closed on any error.

    `revision` is the judged commit, or HEAD for an uncommitted tree/index. A
    committed correction's own introducing timestamp is checked even when the
    target was added outside the current diff. No register means no changed policy.
    """
    result = Corrections()
    raw = read(REGISTER)
    if raw is None:
        return result

    def git(*args: str) -> str:
        p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        if p.returncode:
            raise ValueError("unavailable or invalid provenance: " + " ".join(args[:2]))
        return p.stdout

    try:
        rev = git("rev-parse", "--verify", revision + "^{commit}").strip()
    except ValueError as e:
        result.errors.append((0, str(e)))
        return result
    historical = subprocess.run(
        ["git", "-C", str(root), "show", f"{rev}:{REGISTER}"], capture_output=True, text=True
    )
    previous = historical.stdout.splitlines() if historical.returncode == 0 else []
    seen: set[tuple[str, str]] = set()
    for number, line in enumerate(raw.splitlines(), 1):
        result.candidates += 1
        try:

            def unique_fields(pairs: list[tuple[str, object]]) -> dict:
                obj: dict = {}
                for key, value in pairs:
                    if key in obj:
                        raise ValueError("duplicate JSON field")
                    obj[key] = value
                return obj

            rec = json.loads(line, object_pairs_hook=unique_fields)
            if not isinstance(rec, dict) or set(rec) != FIELDS:
                raise ValueError("exact record-correction/1 fields required")
            if rec["schema"] != SCHEMA or rec["kind"] not in KINDS:
                raise ValueError("unsupported correction schema or kind")
            path, source, lineno = rec["path"], rec["source_commit"], rec["source_line"]
            if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
                raise ValueError("source_commit must be a full commit id")
            if type(lineno) is not int or lineno < 1:
                raise ValueError("source_line must be a positive integer")
            if not isinstance(path, str) or not (
                path == LEDGER
                if rec["kind"] in {"phase-log-heading-markup", "gate-row-recording-date"}
                else re.fullmatch(r"docs/build/readouts/[A-Za-z0-9_-]+\.md", path)
            ):
                raise ValueError("unsupported target path")
            git("merge-base", "--is-ancestor", source, rev)
            lines = git("show", f"{source}:{path}").splitlines()
            if lineno > len(lines):
                raise ValueError("source line does not exist")
            original = lines[lineno - 1]
            if lines.count(original) != 1:
                raise ValueError("source target is ambiguous within its original file")
            digest = hashlib.sha256(original.encode()).hexdigest()
            if rec["line_sha256"] != digest:
                raise ValueError("source line digest mismatch")
            blame = git("blame", "--porcelain", "-L", f"{lineno},{lineno}", source, "--", path)
            if blame.split()[0] != source:
                raise ValueError("source_commit did not introduce the targeted line")
            current = (read(path) or "").splitlines()
            if current.count(original) != 1:
                raise ValueError("original target must survive unchanged exactly once")
            key = (path, original)
            if key in seen:
                raise ValueError("duplicate or conflicting correction for one target")
            seen.add(key)
            source_time = int(git("show", "-s", "--format=%ct", source).strip())
            recorded = stamp(rec["recorded_at"])
            bound = now
            if line in previous:
                if previous.count(line) != 1:
                    raise ValueError("ambiguous correction provenance")
                n = previous.index(line) + 1
                origin = git("blame", "--porcelain", "-L", f"{n},{n}", rev, "--", REGISTER).split()[
                    0
                ]
                bound = min(bound, int(git("show", "-s", "--format=%ct", origin).strip()))
            if recorded < source_time or recorded > bound + 300:
                raise ValueError("correction recording time is outside its evidenced clock bounds")
            if rec["kind"] in {"readout-pointer-date", "gate-row-recording-date"}:
                pointer = rec["kind"] == "readout-pointer-date"
                match = re.fullmatch(
                    r"GATE DECISIONS row: (\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z)"
                    r" \| (GATE-[A-Za-z0-9-]+)",
                    original,
                )
                if pointer and not match:
                    raise ValueError("target is not an exact readout GATE DECISIONS pointer")
                if pointer:
                    assert match is not None
                    wrong_stamp, gate = match[1], match[2]
                else:
                    cells = [x.strip() for x in original.strip("|").split("|")]
                    headings = [
                        x for x in current[: current.index(original)] if x.startswith("## ")
                    ]
                    if (
                        not original.startswith("|")
                        or len(cells) != 7
                        or cells[-1] not in {"decision", "confirmation"}
                        or not re.fullmatch(r"GATE-[A-Za-z0-9-]+", cells[1])
                        or not headings
                        or not headings[-1].startswith("## GATE DECISIONS")
                    ):
                        raise ValueError("target is not a GATE DECISIONS decision/confirmation row")
                    wrong_stamp, gate = cells[0], cells[1]
                    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z", wrong_stamp):
                        raise ValueError("gate-row timestamp must be an exact UTC date/time")
                wrong = int(
                    dt.datetime.fromisoformat(wrong_stamp.replace("Z", "+00:00")).timestamp()
                )
                if wrong <= source_time + 300:
                    raise ValueError("record date does not exceed its recording commit tolerance")
                interpretation = rec["interpretation"]
                if not isinstance(interpretation, dict) or set(interpretation) != {
                    "recorded_at_or_before"
                }:
                    raise ValueError("date correction requires only recorded_at_or_before")
                if stamp(interpretation["recorded_at_or_before"]) != source_time:
                    raise ValueError(
                        "corrected bound must equal the verified recording commit time"
                    )
                # The pointer still names the same existing decision, never a new decision.
                ledger = read(LEDGER) or ""
                section = re.search(r"(?ms)^## GATE DECISIONS\b.*?(?=^## |\Z)", ledger)
                rows = []
                for row in section[0].splitlines() if section else []:
                    cells = [x.strip() for x in row.strip().strip("|").split("|")]
                    if (
                        row.startswith("|")
                        and len(cells) == 7
                        and cells[0] == wrong_stamp
                        and cells[1] == gate
                        and cells[-1] == "decision"
                    ):
                        rows.append(row)
                if len(rows) != 1:
                    raise ValueError("pointer does not identify exactly one decision row")
                result.dates[key] = interpretation["recorded_at_or_before"]
            else:
                current_line = current.index(original)
                headings = [x for x in current[:current_line] if x.startswith("## ")]
                if not headings or not re.match(r"^## PHASE LOG(?! INDEX)", headings[-1]):
                    raise ValueError("target is not in a PHASE LOG section")
                match = re.fullmatch(r"- \d{4}-\d\d-\d\d — (.+?) — (.+)", original)
                if not match or not re.search(r"[*_`]", match[1]):
                    raise ValueError("target does not have a marked-up PHASE LOG heading")
                expected = re.sub(r"[*_`]", "", match[1])
                if rec["interpretation"] != {"heading": expected}:
                    raise ValueError("heading correction must remove only markup from the heading")
                result.headings.add(key)
        except (ValueError, TypeError, KeyError, IndexError) as e:
            result.errors.append((number, str(e)))
    if result.errors:
        result.dates.clear()
        result.headings.clear()
    return result
