# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §22.7 Data Library roster — registry completeness audit (SIG-INGEST-041).

P37.13 (row 435): the EFF Data Library index is the Phase 17 ingestion
backlog and every roster entry MUST be registered — ``LINK`` posture until its
rights are reviewed. ``data/data_library_roster.toml``
(``sig.data-library-roster/1``) is the committed mapping: one ``[[entry]]`` per
spec-roster row, ``covers`` naming the registry source id(s) that carry it.

This module is the coverage audit over that file: :func:`spec_roster_datasets`
re-derives the roster from the spec source (never a hand-copied count),
:func:`roster` loads the committed mapping fail-closed, and :func:`coverage`
joins entries to registry records — an entry with no covering source is a
recorded gap, and a covering id that does not resolve fails the audit. The
``sig-connectors roster`` CLI prints the same report; the roster test
(``tests/connectors/test_data_library_roster.py``) asserts the join is total.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ._data import load_table
from .registry import SourceRecord, registry

SCHEMA = "sig.data-library-roster/1"

#: The spec source file carrying the §22.7 roster table — the authoritative
#: enumeration the committed roster file is checked against (never a
#: hand-maintained count).
SPEC_SRC = "docs/research/_meta/spec_src/51b_partIV_s22_6_seeded_registry.md"

_ROSTER_HEADING = "### 22.7 The Data Library specialist-dataset backlog"
_TABLE_ROW = re.compile(r"^\|(.+)\|$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def spec_roster_datasets(spec_src: Path | None = None) -> tuple[str, ...]:
    """The §22.7 roster's dataset cells, parsed from the spec source.

    Reads the markdown table directly under the ``### 22.7`` heading — the
    roster is the spec's contract, so the test compares this parsed set to
    the committed roster file rather than trusting either copy alone.
    """
    path = spec_src or (_repo_root() / SPEC_SRC)
    in_section = False
    rows: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            in_section = line.strip() == _ROSTER_HEADING
            continue
        if not in_section:
            continue
        match = _TABLE_ROW.match(line.strip())
        if not match:
            if rows:
                break  # the table ended — the next prose is out of scope
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if len(cells) < 3 or cells[0] in {"Dataset", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(cells[0])
    return tuple(rows)


@dataclass(frozen=True)
class RosterEntry:
    """One §22.7 roster entry and its covering registry ids."""

    roster_key: str
    spec_dataset: str
    dataset: str
    technology: str
    priority: str
    mapping: str
    covers: tuple[str, ...]
    registered_by: str
    note: str


@cache
def roster() -> tuple[RosterEntry, ...]:
    """The committed roster, loaded fail-closed (``sig.data-library-roster/1``)."""
    table = load_table("data_library_roster")
    if str(table.get("schema", "")) != SCHEMA:
        raise ValueError(f"data_library_roster.toml schema {table.get('schema')!r} != {SCHEMA!r}")
    entries: list[RosterEntry] = []
    seen: set[str] = set()
    for i, row in enumerate(table.get("entry", [])):
        key = str(row.get("roster_key", "")).strip()
        if not key or key in seen:
            raise ValueError(f"roster entry {i}: missing or duplicate roster_key {key!r}")
        seen.add(key)
        covers = tuple(str(c) for c in row.get("covers", ()))
        if not covers:
            raise ValueError(
                f"roster entry {key!r}: 'covers' is empty — a roster row names "
                "the registry id(s) carrying it (SIG-INGEST-041)"
            )
        entries.append(
            RosterEntry(
                roster_key=key,
                spec_dataset=str(row.get("spec_dataset", "")),
                dataset=str(row.get("dataset", "")),
                technology=str(row.get("technology", "")),
                priority=str(row.get("priority", "")),
                mapping=str(row.get("mapping", "")),
                covers=covers,
                registered_by=str(row.get("registered_by", "")),
                note=str(row.get("note", "")),
            )
        )
    return tuple(entries)


@dataclass(frozen=True)
class CoverageRow:
    """One roster entry joined to its covering registry records."""

    entry: RosterEntry
    records: tuple[SourceRecord, ...]
    unresolved: tuple[str, ...]


def coverage() -> tuple[CoverageRow, ...]:
    """Join every roster entry to the registry — fail-closed on a dangling id."""
    records = registry()
    out: list[CoverageRow] = []
    for entry in roster():
        unresolved = tuple(c for c in entry.covers if c not in records)
        out.append(
            CoverageRow(
                entry=entry,
                records=tuple(records[c] for c in entry.covers if c in records),
                unresolved=unresolved,
            )
        )
    return tuple(out)


def coverage_report() -> str:
    """The `sig-connectors roster` text report — one line per roster entry."""
    lines = [
        "§22.7 Data Library roster coverage (sig.data-library-roster/1, SIG-INGEST-041):",
    ]
    uncovered = 0
    for row in coverage():
        if row.unresolved:
            uncovered += 1
            lines.append(f"  {row.entry.roster_key}: UNCOVERED — {', '.join(row.unresolved)}")
            continue
        postures = ", ".join(
            f"{r.id}[{r.custody_posture.value}{'/PERMITTED' if r.ingestion_permitted else ''}]"
            for r in row.records
        )
        lines.append(f"  {row.entry.roster_key}: {postures}")
    lines.append(
        f"{len(roster())} roster entries; {uncovered} uncovered; "
        f"{len(spec_roster_datasets())} rows in the spec table."
    )
    return "\n".join(lines)


__all__ = [
    "CoverageRow",
    "RosterEntry",
    "SCHEMA",
    "SPEC_SRC",
    "coverage",
    "coverage_report",
    "roster",
    "spec_roster_datasets",
]
