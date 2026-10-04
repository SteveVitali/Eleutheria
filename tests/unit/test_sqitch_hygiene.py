# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.24a (SIG-ENG-045, SIG-STORE-041, SIG-MEM-005; ADR-196).

Sqitch lifecycle hygiene guards:

1. **Rework shape (D-P32.10a-1).** The append-only repair of the stale
   `shared_temporal_contract` verify: the `@r11-sqitch-hygiene` tag and the
   reworked change sit at the plan tail; the tag-suffixed script copies are
   byte-identical to the landed scripts (committed fixtures — never git
   history, so the check holds in a shallow checkout); the reworked
   deploy/revert are deliberate no-ops; the reworked verify asserts the 27
   *named* facets this change installs, never a global count.
2. **Verify lint.** No live verify script asserts an unscoped
   `count(*) FROM spine_watermark` — a living registry grows whenever a later
   change legitimately adds a facet, so a global exact count is a stale
   assertion by construction. Tag-suffixed preserved copies are exempt (they
   are historical artifacts, run only for their own tagged instance).
3. **Planner identity (D5).** Every plan line after the frozen L52 spine names
   the plan's recorded planner identity `Devin <devin@sig-project.org>` —
   set through `SQITCH_FULLNAME`/`SQITCH_EMAIL`, never the git user.
4. **Pinned image.** No operational path references a mutable
   `sqitch/sqitch:<tag>`; every digest-pinned reference equals the recorded
   digest. Historical records (run ledgers, planning docs) are out of scope —
   they record what ran.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from support import REPO_ROOT

REPO = REPO_ROOT
PLAN = REPO / "db" / "sqitch.plan"
REWORK_TAG = "r11-sqitch-hygiene"
BASE_DIR = REPO / "tests" / "unit" / "fixtures" / "sqitch_rework_at_p34.24a_base"
PLAN_LAST_FROZEN = 52  # the C-10 frozen spine; every line after it is appended

#: The plan's recorded planner identity — on all 52 frozen lines and required
#: on every appended line (SQITCH_FULLNAME/SQITCH_EMAIL, never the git user).
PLANNER = "Devin <devin@sig-project.org>"

#: The digest the mutable `latest` tag resolved to at writing (docker pull +
#: docker inspect 2026-10-04; App::Sqitch v1.6.1).
SQITCH_IMAGE_PINNED = (
    "sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3"
)
_SQITCH_DIGEST = SQITCH_IMAGE_PINNED.split("@", 1)[1]

#: A mutable image reference: `sqitch/sqitch:<tag>` (incl. docker.io/ prefix).
SQITCH_MUTABLE_RE = re.compile(r"(?:docker\.io/)?sqitch/sqitch:[A-Za-z0-9][A-Za-z0-9._-]*")
#: Any digest-pinned reference (to assert it equals the recorded digest).
SQITCH_DIGEST_RE = re.compile(r"(?:docker\.io/)?sqitch/sqitch@sha256:[0-9a-f]{64}")
#: The stale-assertion defect class: an unscoped count over the living
#: watermark registry.
WATERMARK_GLOBAL_COUNT_RE = re.compile(
    r"count\s*\(\s*\*\s*\)\s+FROM\s+(?:public\.)?spine_watermark", re.IGNORECASE
)

#: Operational/config paths the pin guard scans. docs/build/runs/, planning/,
#: and tickets/ are append-only records of what ran — never scanned.
PIN_SCAN_DIRS = ("ops", "db", "tests", "scripts", "docs/build/tools", ".github")

#: The 27 facets `shared_temporal_contract` installs — the reworked verify's
#: contract (publication_dispositions' `publication_disposition`, the 28th
#: row, belongs to its own change's verify).
EXPECTED_FACETS = (
    "claim",
    "claim_evidence",
    "claim_qualifier",
    "evidence_capture",
    "evidence_artifact",
    "evidence_blob",
    "extraction",
    "ingest_run",
    "ingest_run_capture",
    "ingest_run_completion",
    "rights_record",
    "rights_decision",
    "source_registry",
    "entity",
    "entity_identifier",
    "organization",
    "organization_relation",
    "relationship",
    "resolution",
    "contradiction",
    "coverage_record",
    "research_task",
    "review_item",
    "review_decision",
    "camera_site_run",
    "camera_site_match",
    "camera_site_execution",
)


def _plan_lines() -> list[str]:
    return PLAN.read_text(encoding="utf-8").splitlines()


def _appended_lines() -> list[tuple[int, str]]:
    lines = _plan_lines()
    return list(enumerate(lines[PLAN_LAST_FROZEN:], PLAN_LAST_FROZEN + 1))


def planner_of(line: str) -> str | None:
    """The planner token of a change/tag plan line: `<ts> <planner> [# note]`.

    Returns None for header/blank lines (``%`` directives)."""
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\S+)\s+(.*?)\s*(?:#|$)", line)
    return m.group(2) if m else None


def _strip_sql_comments(text: str) -> list[str]:
    """Statements of a sqitch script with `--` comment lines removed."""
    return [
        ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("--")
    ]


# --------------------------------------------------------------------------- #
# 1. The rework's shape                                                        #
# --------------------------------------------------------------------------- #


def test_rework_plan_tail() -> None:
    """The appended tail is exactly the tag line then the reworked change —
    both appended at EOF by sqitch, both naming the reworked dependency."""
    appended = _appended_lines()
    assert len(appended) >= 2, "the tag + reworked change must be appended after L52"
    (tag_lineno, tag_line), (chg_lineno, chg_line) = appended[0], appended[1]
    assert tag_line.startswith(f"@{REWORK_TAG} "), (
        f"plan line {tag_lineno} must be the @{REWORK_TAG} tag"
    )
    assert chg_line.startswith(
        f"shared_temporal_contract [shared_temporal_contract@{REWORK_TAG}] "
    ), f"plan line {chg_lineno} must be the reworked shared_temporal_contract"
    # sqitch never interleaves: the frozen spine is untouched above them.
    assert not _plan_lines()[PLAN_LAST_FROZEN - 1].startswith("@")


def test_tagged_copies_byte_identical_to_landed() -> None:
    """The `*@r11-sqitch-hygiene.sql` copies equal the landed scripts
    byte-for-byte — the fixtures are the pre-rework bytes, committed, so a
    shallow checkout never needs git history to prove it."""
    for kind in ("deploy", "revert", "verify"):
        tagged = REPO / "db" / kind / f"shared_temporal_contract@{REWORK_TAG}.sql"
        base = BASE_DIR / kind / "shared_temporal_contract.sql"
        assert tagged.is_file(), f"missing {tagged}"
        assert tagged.read_bytes() == base.read_bytes(), (
            f"{tagged.name} drifted from the landed script — a reworked copy is "
            "a preserved artifact, never edited"
        )


def test_reworked_deploy_and_revert_are_noops() -> None:
    """The reworked deploy/revert carry no DDL — the schema is unchanged, the
    repair is the verify script. `BEGIN; SELECT 1; COMMIT;` exactly."""
    for kind in ("deploy", "revert"):
        stmts = _strip_sql_comments(
            (REPO / "db" / kind / "shared_temporal_contract.sql").read_text()
        )
        assert stmts == ["BEGIN;", "SELECT 1;", "COMMIT;"], (
            f"reworked {kind}/shared_temporal_contract.sql must be a no-op "
            "(the real DDL lives in the @tag copy)"
        )


def test_reworked_verify_asserts_named_facets() -> None:
    """The reworked verify names all 27 facets this change installs and no
    longer asserts a global count."""
    text = (REPO / "db" / "verify" / "shared_temporal_contract.sql").read_text()
    for facet in EXPECTED_FACETS:
        assert f"('{facet}')" in text, f"reworked verify does not name facet {facet}"
    assert not WATERMARK_GLOBAL_COUNT_RE.search(text), (
        "reworked verify still asserts a global spine_watermark count — the "
        "defect it exists to repair (D-P32.10a-1)"
    )


# --------------------------------------------------------------------------- #
# 2. Verify lint                                                               #
# --------------------------------------------------------------------------- #


def _live_verify_scripts() -> list[Path]:
    """Current-instance verify scripts; `@tag` preserved copies are exempt."""
    return [p for p in (REPO / "db" / "verify").glob("*.sql") if "@" not in p.name]


def test_no_unscoped_watermark_count_in_verify() -> None:
    """D-P32.10a-1's class can never recur silently: no live verify script may
    assert an unscoped `count(*) FROM spine_watermark` — a verify names the
    facets its own change installs (ADR-196)."""
    offenders = [
        p.relative_to(REPO)
        for p in _live_verify_scripts()
        if WATERMARK_GLOBAL_COUNT_RE.search(p.read_text())
    ]
    assert not offenders, "verify scripts with an unscoped spine_watermark count: " + ", ".join(
        str(o) for o in offenders
    )


def test_unscoped_count_fixture_fails() -> None:
    """The lint actually bites: the planted stale shape is caught."""
    stale = "SELECT 1/(CASE WHEN (SELECT count(*) FROM spine_watermark)=27 THEN 1 ELSE 0 END);"
    assert WATERMARK_GLOBAL_COUNT_RE.search(stale)
    scoped = (
        "SELECT 1 FROM spine_watermark w WHERE w.facet = 'claim' "
        "AND w.row_count = (SELECT count(*) FROM claim)"
    )
    assert not WATERMARK_GLOBAL_COUNT_RE.search(scoped)


# --------------------------------------------------------------------------- #
# 3. Planner identity                                                          #
# --------------------------------------------------------------------------- #


def test_appended_plan_lines_carry_the_planner_identity() -> None:
    """Every plan line appended after the frozen L52 spine — change or tag —
    names `Devin <devin@sig-project.org>` exactly."""
    appended = _appended_lines()
    assert appended, "no appended plan lines — the guard is vacuous"
    for lineno, line in appended:
        planner = planner_of(line)
        assert planner == PLANNER, (
            f"db/sqitch.plan line {lineno} names planner {planner!r}, "
            f"expected {PLANNER!r} (SQITCH_FULLNAME/SQITCH_EMAIL, never git)"
        )


def test_planner_identity_rejects_malformed_lines() -> None:
    """The guard's shape: a wrong name, a wrong address, or a missing
    `<email>` all fail the identity check."""
    good = "new_change [x] 2026-10-04T00:00:00Z Devin <devin@sig-project.org> # n"
    assert planner_of(good) == PLANNER
    for bad in (
        "new_change [x] 2026-10-04T00:00:00Z Someone <devin@sig-project.org> # n",
        "new_change [x] 2026-10-04T00:00:00Z Devin <other@sig-project.org> # n",
        "new_change [x] 2026-10-04T00:00:00Z Devin # n",
        "@tag 2026-10-04T00:00:00Z Root <root@localhost> # n",
    ):
        assert planner_of(bad) != PLANNER


# --------------------------------------------------------------------------- #
# 4. The pinned image                                                          #
# --------------------------------------------------------------------------- #


def _scanned_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z", "--", *PIN_SCAN_DIRS], cwd=REPO, text=True
    )
    return [p for p in out.split("\x00") if p]


def test_no_mutable_sqitch_image_reference() -> None:
    """No operational/config path references `sqitch/sqitch:<tag>` — the image
    is pinned by digest everywhere it is invoked (ADR-196)."""
    offenders: list[str] = []
    for rel in _scanned_files():
        for i, line in enumerate((REPO / rel).read_text(errors="replace").splitlines(), 1):
            if SQITCH_MUTABLE_RE.search(line):
                offenders.append(f"{rel}:{i}")
    assert not offenders, "mutable sqitch/sqitch:<tag> references: " + ", ".join(offenders)


def test_every_sqitch_digest_is_the_recorded_pin() -> None:
    """Every `sqitch/sqitch@sha256:` reference in operational paths is exactly
    the recorded digest — a different pin is a silent image change."""
    offenders: list[str] = []
    for rel in _scanned_files():
        for i, line in enumerate((REPO / rel).read_text(errors="replace").splitlines(), 1):
            for m in SQITCH_DIGEST_RE.finditer(line):
                if m.group(0).split("@", 1)[1] != _SQITCH_DIGEST:
                    offenders.append(f"{rel}:{i}")
    assert not offenders, "non-pinned sqitch digests: " + ", ".join(offenders)


def test_the_harnesses_actually_use_the_pin() -> None:
    """A pin nobody uses is a vacuous guard — the DB harness, the round-trip
    script and the compose service must all name the pinned reference."""
    for rel in (
        "tests/db/conftest.py",
        "scripts/ci/sqitch_roundtrip.sh",
        "ops/docker-compose.yml",
    ):
        assert SQITCH_IMAGE_PINNED in (REPO / rel).read_text(), (
            f"{rel} does not reference the pinned sqitch image"
        )
