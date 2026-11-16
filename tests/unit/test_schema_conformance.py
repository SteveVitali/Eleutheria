# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.58 (SIG-STORE-045, BL-049; ADR-248): generated-vs-deployed schema conformance.

The recorded rule (the GATE-P route, decided by SEED-11 and landed here): the
deployed physical schema is the sqitch chain — ``db/sqitch.plan`` plus
``db/deploy|revert|verify`` — and the LinkML-generated
``ontology/generated/sql/sig.sql`` is **documentation only**, the logical schema
surface, never a deploy artifact. ADR-248 records the decision; these tests pin
it, so ``sig.sql`` cannot be silently wired into a deploy path without an ADR
revisiting ADR-248.
"""

from __future__ import annotations

import re

from support import REPO_ROOT

REPO = REPO_ROOT
GENERATED_SQL = REPO / "ontology" / "generated" / "sql" / "sig.sql"
PLAN = REPO / "db" / "sqitch.plan"
ADR = next(
    iter((REPO / "docs" / "adr").glob("ADR-248-*.md")),
    REPO / "docs" / "adr" / "ADR-248-missing.md",
)

# Deploy-capable surfaces: any path that could plausibly feed DDL to a database —
# the sqitch chain itself, db package code, ops/scheduling scripts, CI, build
# files and container definitions. Documentation surfaces (Markdown, tickets,
# build memory) legitimately *name* the artifact in prose and are out of scope.
DEPLOY_SURFACE_GLOBS = (
    "db/**/*",
    "scripts/**/*",
    "ops/**/*.sh",
    "ops/**/*.toml",
    ".github/workflows/*",
    "Makefile",
    "Dockerfile*",
    "docker-compose*.yml",
)
# File-level references only: the bare `ontology/generated` tree is legitimately
# named by the generation gate (`verify-gen` diffs it) — a deploy consumption
# must name the SQL artifact or its `sql/` directory.
REFERENCE_TOKENS = ("generated/sql", "sig.sql")


def _generated_sql_text() -> str:
    assert GENERATED_SQL.is_file(), f"{GENERATED_SQL} missing — run `make gen`"
    return GENERATED_SQL.read_text(encoding="utf-8")


def _plan_change_names() -> list[str]:
    """The change names a sqitch plan declares: non-directive, non-tag lines."""
    names = []
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("%") or line.startswith("@"):
            continue
        names.append(line.split()[0])
    return names


def test_generated_sql_self_declares_documentation_only() -> None:
    """The artifact carries the generator-written declaration (ADR-248): its
    first block names the file, cites the ADR, and says the sqitch chain is
    the deployed schema — so a reader can never mistake it for a deploy
    script."""
    head = "\n".join(_generated_sql_text().splitlines()[:8])
    assert "GENERATED DOCUMENTATION" in head
    assert "DOCUMENTATION ONLY (ADR-248)" in head
    assert "db/sqitch.plan" in head
    assert "Never deploy this file." in head


def test_no_deploy_surface_references_the_generated_ddl() -> None:
    """No deploy-capable path consumes the generated DDL — the seam that would
    silently make ``sig.sql`` physical is what this test exists to fail on."""
    offenders: list[str] = []
    for pattern in DEPLOY_SURFACE_GLOBS:
        for path in sorted(REPO.glob(pattern)):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            hits = [tok for tok in REFERENCE_TOKENS if tok in text]
            if hits:
                offenders.append(f"{path.relative_to(REPO)} ({', '.join(hits)})")
    assert not offenders, (
        "generated `ontology/generated/sql/sig.sql` is documentation only "
        "(ADR-248) — deploy surfaces must not reference it:\n" + "\n".join(offenders)
    )


def test_every_plan_change_ships_its_three_scripts() -> None:
    """The sqitch plan is the complete physical schema authority: every change
    line resolves to its deploy/revert/verify scripts (a reworked change to a
    ``<change>@<tag>.sql`` copy) — no physical DDL arrives from anywhere else."""
    missing: list[str] = []
    for change in _plan_change_names():
        for kind in ("deploy", "revert", "verify"):
            directory = REPO / "db" / kind
            plain = directory / f"{change}.sql"
            tagged = list(directory.glob(f"{change}@*.sql"))
            if not plain.is_file() and not tagged:
                missing.append(f"{kind}/{change}")
    assert not missing, f"plan changes without their sqitch scripts: {missing}"


def test_generated_sql_is_logical_ddl_not_physical() -> None:
    """The generated surface carries none of the spine's physical enforcement
    machinery — a sanity pin on *why* it can never be the deploy artifact
    (append-only triggers, RLS, and grants live only in the sqitch chain)."""
    text = _generated_sql_text()
    for machinery in ("CREATE TRIGGER", "ROW LEVEL SECURITY", "EXCLUDE ", "GRANT "):
        assert machinery not in text, f"generated DDL gained physical machinery: {machinery}"


def test_adr_248_records_the_decided_rule() -> None:
    """The ADR exists, names sqitch authoritative and the generated DDL
    documentation-only, and carries its revisit trigger — the frozen record the
    conformance guard cites."""
    assert ADR.is_file(), "ADR-248 must exist under docs/adr/"
    text = ADR.read_text(encoding="utf-8")
    assert re.search(r"sqitch\.plan.*sole authority|sqitch.*authoritative", text, re.I)
    assert "documentation only" in text.lower()
    assert "## Revisit trigger" in text
