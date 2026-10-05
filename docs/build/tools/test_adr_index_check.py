#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``adr_index_check.py`` — G8-1/G8-2 (P34.32): the generated index tells the truth
(every row a title, an owning ticket/phase and a status; the latest `## Status updates` line wins)
and every ADR named in a later ADR's declaration field or a Related-family annotation carries its
appended `- **Status:** <Kind> by ADR-NNN (<date>)` line.

Fixture trees exercise each rule; the last test runs the check over the committed tree (an
invariant — the tree must satisfy the checker — never a pinned living value)::

    uv run pytest docs/build/tools/test_adr_index_check.py
"""

from __future__ import annotations

import importlib.util
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[2]
_spec = importlib.util.spec_from_file_location("adr_index_check", _HERE / "adr_index_check.py")
ai = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ai)

# ── fixture ADR texts covering every landed header form ───────────────────────────────────

COLON_ADR = """# ADR-001: Colon title

- **Ticket:** P01.1 (Round 0)
- **Status:** Accepted

## Decision

Do it.

## Revisit trigger

When the load doubles.
"""

DASH_ADR = """# ADR-002 — Em-dash title

- Date: 2026-01-01
- Status: accepted (legacy)
- Phase: P02

## Revisit trigger

When the licence changes.

## Status updates

- **Status:** Qualified by ADR-001 (2026-10-01)
"""

HYPHEN_ADR = """# ADR-003 - Hyphen title

**Phase / ticket:** P03 (plain non-bullet)

Status: proposed

## Revisit trigger

When the format shifts.
"""

NO_OWNER_ADR = """# ADR-004 — No owner field

- Date: 2026-01-01
- Status: accepted

## Revisit trigger

When something.
"""

NEW_ADR_NO_FIELDS = """# ADR-146: New ADR missing the template fields

- Date: 2026-01-01

## Revisit trigger

When anything.
"""

DECLARING_SUPERSEDES = """# ADR-010: Declares a supersession

- **Ticket:** P10
- **Status:** Accepted
- **Supersedes:** ADR-001

## Revisit trigger

When it lands.
"""

DECLARING_RELATED = """# ADR-011: Declares in a Related annotation

- **Ticket:** P11
- **Status:** Accepted
- **Related:** ADR-002 (the envelope this extends), ADR-003

## Revisit trigger

When it lands.
"""

DECLARING_NONE = """# ADR-012: Declares nothing

- **Ticket:** P12
- **Status:** Accepted
- **Related:** ADR-001
- **Amends / qualifies / extends:** extends ADR-002 (it does not); no status line for ADR-002; the
  shorthand "extends ADR-003" is not the decision
- **Supersedes:** none

## Revisit trigger

When it lands.
"""

DECLARING_BODY = """# ADR-013: Declares in body text

- **Ticket:** P13
- **Status:** Accepted

## Decision

1. ADR-003 is superseded, ADR-002 is not touched.

## Revisit trigger

When it lands.
"""

DECLARING_MISSING_TARGET = """# ADR-014: Names a missing ADR

- **Ticket:** P14
- **Status:** Accepted
- **Supersedes:** ADR-404

## Revisit trigger

When it lands.
"""


def _tree(tmp_path: pathlib.Path, adrs: dict[str, str], readme: str | None = None) -> pathlib.Path:
    adr_dir = tmp_path / "repo" / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    for name, text in adrs.items():
        (adr_dir / name).write_text(text)
    if readme is not None:
        (adr_dir / "README.md").write_text(readme)
    return tmp_path / "repo"


def _gen_readme(root: pathlib.Path) -> str:
    return ai.generate_index(root / "docs" / "adr")


def _check(root: pathlib.Path):
    return ai.check(root)


# ── index generation (G8-1) ───────────────────────────────────────────────────────────────


def test_all_h1_and_header_forms_parse_into_index_rows(tmp_path) -> None:
    root = _tree(
        tmp_path,
        {"ADR-001-colon.md": COLON_ADR, "ADR-002-dash.md": DASH_ADR, "ADR-003-hyphen.md": HYPHEN_ADR},
    )
    r1 = next(r for r in ai.index_rows(root / "docs" / "adr") if r[1] == "ADR-001")
    r2 = next(r for r in ai.index_rows(root / "docs" / "adr") if r[1] == "ADR-002")
    r3 = next(r for r in ai.index_rows(root / "docs" / "adr") if r[1] == "ADR-003")
    assert r1[2] == "Colon title" and r1[3] == "P01.1 (Round 0)" and r1[4] == "Accepted"
    assert r2[2] == "Em-dash title" and r2[3] == "P02"
    # the appended `## Status updates` line overrides the header status
    assert r2[4] == "Qualified by ADR-001 (2026-10-01)"
    assert r3[2] == "Hyphen title" and r3[3] == "P03 (plain non-bullet)" and r3[4] == "proposed"


def test_matching_readme_passes_and_hand_edit_fails(tmp_path) -> None:
    adrs = {"ADR-001-colon.md": COLON_ADR, "ADR-002-dash.md": DASH_ADR}
    root = _tree(tmp_path / "a", adrs)
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, warnings, stats = _check(root)
    assert errors == []
    assert stats["offered"] == 2 and stats["index_rows"] == 2
    edited = _tree(tmp_path / "b", adrs)
    (edited / "docs" / "adr" / "README.md").write_text(_gen_readme(edited) + "hand\n")
    errors, _, _ = _check(edited)
    assert any("does not match a fresh adr-index regeneration" in e for e in errors)


def test_dash_cells_fail_on_new_adrs_and_unexplained_but_warn_on_absent_legacy(tmp_path) -> None:
    # a pre-146 ADR with no owner field at all: the generator's `—` is honest → warning
    root = _tree(tmp_path / "a", {"ADR-004-none.md": NO_OWNER_ADR})
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, warnings, _ = _check(root)
    assert errors == []
    assert any("ADR-004" in w and "—" in w for w in warnings)
    # ADR-146+ must carry the template header fields → hard failure
    new = _tree(tmp_path / "b", {"ADR-146-new.md": NEW_ADR_NO_FIELDS})
    (new / "docs" / "adr" / "README.md").write_text(_gen_readme(new))
    errors, _, _ = _check(new)
    assert any("ADR-146" in e and "≥ ADR-146" in e for e in errors)


# ── supersession / qualification status lines (G8-2, COV-14) ───────────────────────────────


def test_supersedes_field_without_the_appended_line_fails_then_passes(tmp_path) -> None:
    adrs = {"ADR-001-target.md": COLON_ADR, "ADR-010-src.md": DECLARING_SUPERSEDES}
    missing = _tree(tmp_path / "a", adrs)
    (missing / "docs" / "adr" / "README.md").write_text(_gen_readme(missing))
    errors, _, _ = _check(missing)
    assert any(
        "declares ADR-001 Superseded" in e and "no `- **Status:** Superseded by ADR-010" in e
        for e in errors
    )
    fixed = _tree(
        tmp_path / "b",
        {
            "ADR-001-target.md": COLON_ADR
            + """
## Status updates

- **Status:** Superseded by ADR-010 (2026-10-05)
""",
            "ADR-010-src.md": DECLARING_SUPERSEDES,
        },
    )
    (fixed / "docs" / "adr" / "README.md").write_text(_gen_readme(fixed))
    errors, _, _ = _check(fixed)
    assert errors == []


def test_a_status_line_without_the_date_is_malformed(tmp_path) -> None:
    adrs = {
        "ADR-001-target.md": COLON_ADR
        + """
## Status updates

- **Status:** Superseded by ADR-010
""",
        "ADR-010-src.md": DECLARING_SUPERSEDES,
    }
    root = _tree(tmp_path, adrs)
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, _, _ = _check(root)
    assert any("lacks the `(<date -u>)` date" in e for e in errors)


def test_related_annotation_declares_but_a_bare_reference_does_not(tmp_path) -> None:
    adrs = {"ADR-002-dash.md": DASH_ADR, "ADR-011-src.md": DECLARING_RELATED}
    root = _tree(tmp_path, adrs)
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, _, _ = _check(root)
    # "ADR-002 (the envelope this extends)" obliges an Extended line; bare "ADR-003" does not
    assert any("declares ADR-002 Extended" in e for e in errors)
    assert not any("ADR-003" in e for e in errors)


def test_none_quoted_and_no_status_line_forms_declare_nothing(tmp_path) -> None:
    adrs = {
        "ADR-001-colon.md": COLON_ADR,
        "ADR-002-dash.md": DASH_ADR,
        "ADR-003-hyphen.md": HYPHEN_ADR,
        "ADR-012-none.md": DECLARING_NONE,
    }
    root = _tree(tmp_path, adrs)
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, _, _ = _check(root)
    assert errors == []


def test_body_declaration_obliges_a_line(tmp_path) -> None:
    adrs = {
        "ADR-002-dash.md": DASH_ADR,
        "ADR-003-hyphen.md": HYPHEN_ADR,
        "ADR-013-body.md": DECLARING_BODY,
    }
    root = _tree(tmp_path, adrs)
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, _, _ = _check(root)
    # "ADR-003 is superseded" → Superseded; "ADR-002 is not touched" declares nothing
    assert any("declares ADR-003 Superseded" in e for e in errors)
    assert not any("ADR-002" in e for e in errors)


def test_a_named_target_with_no_file_fails_closed(tmp_path) -> None:
    root = _tree(tmp_path, {"ADR-014-src.md": DECLARING_MISSING_TARGET})
    (root / "docs" / "adr" / "README.md").write_text(_gen_readme(root))
    errors, _, _ = _check(root)
    assert any("names ADR-404" in e and "no ADR-404-*.md file exists" in e for e in errors)


def test_vacuous_tree_reports_vacuous(tmp_path) -> None:
    root = tmp_path / "repo"
    (root / "docs" / "adr").mkdir(parents=True)
    errors, _, _ = _check(root)
    assert errors and errors[0].startswith("vacuous")


def test_committed_tree_satisfies_the_checker() -> None:
    """Every declaration has its appended line; the only `—` cell is ADR-120's genuinely-absent
    owner field (a warning, never silent)."""
    errors, warnings, stats = ai.check(REPO_ROOT)
    assert errors == [], errors[:20]
    assert stats["offered"] == stats["index_rows"] > 0
