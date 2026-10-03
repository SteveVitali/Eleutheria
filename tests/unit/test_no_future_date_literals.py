# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.22a (SIG-MEM-005, SIG-ENG-045; B4 G1 R1/R5, B1 §5.4, ADR-146, C-10).

The whole-tree future-date literal guard. Over every tracked text file in
``ops/``, ``exports/``, ``web/src/``, ``connectors/`` (incl. ``data/``),
``api/``, ``db/`` and ``tests/``, an ISO date or timestamp **later than the
HEAD commit time** fails, unless it:

- **(a)** sits in a B4 R5 real-world field (``valid_from``, ``valid_to``,
  ``expiry_date``, ``end_date``, ``effective_date``, ``due_date``,
  ``next_run``, ``schedule_time``, ``deadline``);
- **(b)** carries an inline ``future-ok: <scheduled|real-world|synthetic|
  illustrative>: <reason>`` marker or a ``SYNTHETIC_`` name; or
- **(c)** matches an **unexpired** ``allow`` entry of
  ``docs/build/tools/record_policy/history.policy`` — the ONE allow-list,
  reused through ``memory_guard``'s own ``r1_exempt``/``expired_allow`` (the
  same grammar the history guard applies to record dates; an expired entry
  fails, R5).

``docs/build/planning/**`` (forecast text, not records) and
``docs/build/logs/**`` (gitignored) are never scanned; build-memory records
stay G1's diff-mode job (SEED-02).

``db/sqitch.plan`` L44–52 are additionally guarded by C-10: they are
allow-listed by change id (name + dependencies + ``planned_at``) through the
expiring ``allow db/sqitch.plan`` entries — expiry
2026-10-19T21:00:00Z (future-ok: real-world: recorded expiry) — asserted
byte-identical to the bytes recorded at this row's base, and every plan line
added after L52 must carry a ``planned_at`` no later than its commit time.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from support import REPO_ROOT

REPO = REPO_ROOT
TOOLS = REPO / "docs" / "build" / "tools"
POLICY_REL = "docs/build/tools/record_policy/history.policy"
PLAN_REL = "db/sqitch.plan"
PLAN_BASE_REL = "tests/unit/fixtures/sqitch_plan_L44-52_at_p34.22a_base.txt"
PLAN_FIRST, PLAN_LAST = 44, 52

#: The sweep's scope (deliverable 3). ``connectors/`` includes ``data/``.
SWEEP_DIRS = ("api", "connectors", "db", "exports", "ops", "tests", "web/src")
#: Never scanned — forecast text and gitignored logs are not records.
NEVER_SCAN = ("docs/build/planning/", "docs/build/logs/")

#: B4 R5's real-world field names — a literal that is one of these fields'
#: VALUE is a real-world date (contract expiry, due date, scheduled run), not
#: a record date pretending to be a clock reading.
REAL_WORLD_FIELDS = (
    "valid_from",
    "valid_to",
    "expiry_date",
    "end_date",
    "effective_date",
    "due_date",
    "next_run",
    "schedule_time",
    "deadline",
)
_FIELD_VALUE_RE = re.compile(
    r"(?:^|[^\w])(?:"
    + "|".join(REAL_WORLD_FIELDS)
    + r")[\"'\)\]\}]{0,2}\s*(?:={1,2}|!=|:)\s*[\"'\(\[]?\s*$"
)

#: An ISO-8601 date or timestamp literal: YYYY-MM-DD, optionally followed by
#: a time (HH:MM[:SS[.fff]]) and a zone (Z or ±HH[:MM]).
ISO_LITERAL_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?)"
)

#: A ``SYNTHETIC_`` name anywhere on the line marks a synthetic literal (R5).
SYNTHETIC_NAME_RE = re.compile(r"\bSYNTHETIC_[A-Za-z0-9_]+")

FIXES = (
    "fix it one of three ways (B4 R5): (a) put the value in a real-world "
    "field (valid_from, valid_to, expiry_date, end_date, effective_date, "
    "due_date, next_run, schedule_time, deadline); (b) mark the line inline "
    "`future-ok: <scheduled|real-world|synthetic|illustrative>: <reason>` or "
    "name the binding SYNTHETIC_*; (c) add an expiring `allow` entry to "
    "docs/build/tools/record_policy/history.policy"
)


def _load_guard():
    """``memory_guard`` is the tool that owns the allow grammar — the test
    reuses its Policy.parse + r1_exempt + expired_allow verbatim so the
    allow-list stays ONE list, not a second one."""
    spec = importlib.util.spec_from_file_location("memory_guard", TOOLS / "memory_guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys

    sys.modules.setdefault(spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


MG = _load_guard()


def _policy(root: Path = REPO):
    return MG.Policy.parse((root / POLICY_REL).read_bytes())


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def head_commit_epoch(root: Path = REPO) -> int:
    """The bound: any ISO literal later than the HEAD commit time fails."""
    return int(_git(root, "log", "-1", "--format=%ct", "HEAD").strip())


def tracked_files(root: Path = REPO) -> list[str]:
    """Tracked files under the sweep dirs — untracked scratch is not judged."""
    out = _git(root, "ls-files", "-z", "--", *SWEEP_DIRS)
    return [p for p in out.split("\x00") if p]


def _is_text(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    literal: str
    why: str

    def message(self) -> str:
        return (
            f"{self.path}:{self.line}: future-dated literal {self.literal!r} — {self.why}; {FIXES}"
        )


def scan_line(
    path: str,
    lineno: int,
    line: str,
    *,
    bound_epoch: int,
    bound_date: str,
    policy: MG.Policy,
    now_epoch: int,
) -> list[Finding]:
    """Every future-dated ISO literal on one line, with its reason."""
    out: list[Finding] = []
    for m in ISO_LITERAL_RE.finditer(line):
        st = MG.parse_stamp(m.group(1))
        if st is None or st.malformed:
            continue
        if st.has_time:
            future = st.epoch > bound_epoch
        else:
            future = st.date > bound_date
        if not future:
            continue
        # (a) a real-world field's value
        if _FIELD_VALUE_RE.search(line[: m.start()]):
            continue
        # (b) future-ok marker / SYNTHETIC_ name; (c) unexpired allow entry —
        # all through memory_guard's own grammar (one allow-list).
        exempt, _ = MG.r1_exempt(policy, path, line, st, now_epoch)
        if not exempt and SYNTHETIC_NAME_RE.search(line):
            exempt = True
        if exempt:
            continue
        expired = MG.expired_allow(policy, path, line, now_epoch)
        why = (
            f"allow entry expired {expired} (R5: it no longer exempts)"
            if expired
            else "no real-world field, no future-ok marker, no unexpired allow entry"
        )
        out.append(Finding(path, lineno, st.text, why))
    return out


def sweep(
    root: Path = REPO,
) -> tuple[int, int, list[Finding]]:
    """Scan every tracked text file in scope. Returns
    (files evaluated, literals evaluated, findings)."""
    policy = _policy(root)
    bound_epoch = head_commit_epoch(root)
    bound_date = MG.utc_date(bound_epoch)
    now_epoch = int(time.time())
    files = literals = 0
    findings: list[Finding] = []
    for rel in tracked_files(root):
        if rel.startswith(NEVER_SCAN):
            continue
        data = (root / rel).read_bytes()
        if not _is_text(data):
            continue
        files += 1
        for i, line in enumerate(data.decode("utf-8").splitlines(), 1):
            literals += len(ISO_LITERAL_RE.findall(line))
            findings += scan_line(
                rel,
                i,
                line,
                bound_epoch=bound_epoch,
                bound_date=bound_date,
                policy=policy,
                now_epoch=now_epoch,
            )
    return files, literals, findings


def test_no_future_date_literals() -> None:
    """The whole-tree guard (deliverable 3): no future-dated literal survives
    outside the real-world fields, the markers, or the expiring allow-list —
    and the run reports how much it evaluated (SIG-ENG-042 shape)."""
    files, literals, findings = sweep()
    assert files > 0, "the sweep evaluated no files — a vacuous pass is not a pass"
    assert literals > 0, "the sweep evaluated no literals — a vacuous pass"
    print(f"\nfuture-date sweep: {files} files, {literals} literals evaluated")
    assert not findings, f"{len(findings)} future-dated literal(s) found:\n" + "\n".join(
        f.message() for f in findings
    )


def test_never_scans_planning_or_logs() -> None:
    """`docs/build/planning/**` (forecast text) and `docs/build/logs/**`
    (gitignored) are out of scope by construction — assert it stays true."""
    for rel in tracked_files():
        assert not rel.startswith(NEVER_SCAN)


# --------------------------------------------------------------------------- #
# db/sqitch.plan L44–52 (C-10): allow-listed by change id, never re-stamped   #
# --------------------------------------------------------------------------- #


def _plan_lines() -> list[str]:
    return (REPO / PLAN_REL).read_text(encoding="utf-8").splitlines(keepends=True)


def _plan_l44_52() -> list[str]:
    return _plan_lines()[PLAN_FIRST - 1 : PLAN_LAST]


def test_sqitch_plan_l44_52_byte_identical_to_base() -> None:
    """C-10 / S6R-07: L44–52 keep their stamped change ids forever — the nine
    lines must equal, byte-for-byte, the text recorded at this row's base
    (the fixture is the base tree's bytes; git history is never consulted so
    the check holds in a shallow checkout too)."""
    base = (REPO / PLAN_BASE_REL).read_bytes().decode("utf-8").splitlines(keepends=True)
    assert len(base) == 9, "the recorded base fixture must hold exactly 9 lines"
    got = _plan_l44_52()
    assert got == base, (
        "db/sqitch.plan L44–52 drifted from the bytes recorded at the "
        "P34.22a base (d27b4fa6) — they are never edited or re-stamped "
        "(C-10; corrections append under ADR-146)"
    )


def test_sqitch_allow_entries_cover_l44_52_by_change_id() -> None:
    """The nine lines pass only through the expiring `history.policy` entries
    — each entry's fixed text is exactly the change-id inputs (name,
    dependencies and planned_at), matching one plan line 1:1."""
    policy = _policy()
    allows = [a for a in policy.allow if a.glob == PLAN_REL]
    now = int(time.time())
    lines = _plan_l44_52()
    assert len(lines) == 9
    matched = 0
    for i, line in enumerate(lines):
        stamp_line = line.rstrip("\n")
        st = MG.parse_stamp(ISO_LITERAL_RE.search(line).group(1))
        assert st is not None and st.has_time, f"plan line {PLAN_FIRST + i} has no planned_at"
        entry = next(
            (a for a in allows if stamp_line.startswith(a.text)),
            None,
        )
        assert entry is not None, (
            f"plan line {PLAN_FIRST + i} is not allow-listed by its change id "
            "(name + dependencies + planned_at)"
        )
        matched += 1
        if st.epoch > head_commit_epoch():
            # a future-dated line is exempt ONLY while its entry is unexpired
            exempt, _ = MG.r1_exempt(policy, PLAN_REL, stamp_line, st, now)
            assert exempt, f"plan line {PLAN_FIRST + i} lost its allow cover"
    assert matched == 9


def _line_commit_epoch(path: str, lineno: int) -> int:
    """The committer time of the commit that last touched `path:lineno`
    (git blame). A failure to attribute is loud — a line whose commit cannot
    be read is never passed silently."""
    out = subprocess.run(
        ["git", "blame", "--porcelain", "-L", f"{lineno},{lineno}", "--", path],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"git blame failed for {path}:{lineno} — a plan line whose commit "
            "time cannot be read cannot be checked"
        )
    for ln in out.stdout.splitlines():
        if ln.startswith("committer-time "):
            return int(ln.split()[1])
    raise RuntimeError(f"no committer-time in blame for {path}:{lineno}")


def _planned_at(line: str):
    m = ISO_LITERAL_RE.search(line)
    return MG.parse_stamp(m.group(1)) if m else None


def test_sqitch_lines_after_52_planned_at_le_commit_time() -> None:
    """Every plan line added after L52 carries a planned_at no later than the
    commit that added it (G1 R1) — the future-dated band stops at L52. The
    plan today ends at L52, so the loop is a standing guard: it engages the
    first time a migration is appended."""
    lines = _plan_lines()
    assert len(lines) >= PLAN_LAST, "db/sqitch.plan must keep at least the 52-line spine"
    for lineno, line in enumerate(lines[PLAN_LAST:], PLAN_LAST + 1):
        st = _planned_at(line)
        if st is None:
            continue
        commit_epoch = _line_commit_epoch(PLAN_REL, lineno)
        assert st.epoch <= commit_epoch, (
            f"db/sqitch.plan line {lineno} is planned_at {st.text}, later "
            "than the commit that added it — planned_at is part of the "
            "change id and is never post-dated"
        )


# --------------------------------------------------------------------------- #
# Fixture pairs (deliverable 5 / B4 G1 fixtures)                              #
# --------------------------------------------------------------------------- #

_BOUND = int(dt.datetime(2026, 10, 3, 21, 25, tzinfo=dt.UTC).timestamp())
_BOUND_DATE = "2026-10-03"
_NOW = _BOUND  # fixture 'now' == the bound: the literals below are future


def _scan(line: str, *, path: str = "ops/src/ops/x.py", policy=None, now: int = _NOW):
    return scan_line(
        path,
        1,
        line,
        bound_epoch=_BOUND,
        bound_date=_BOUND_DATE,
        policy=policy if policy is not None else MG.Policy(),
        now_epoch=now,
    )


#: Fixture strings for the planted-literal tests. Each carries a future
#: literal inside a synthetic line; a `future-ok:` in the string is the
#: FIXTURE's marker, and a trailing marker is this file's own exemption
#: (kept on the literal's line so the sweep judges it).
_OP_CHOICE = 'note = "2026-12-31" operator choice'  # future-ok: synthetic: fixture
_BAD_MARK = 'note = "2026-12-31"  # future-ok: bad'  # future-ok: synthetic: fixture
_MARKED = 'note = "2026-12-31"  # future-ok: synthetic: planted fixture'
_MARKED_SCHED = 'when = "2026-12-31"  # future-ok: scheduled: AR-3 window'


def test_planted_future_literal_fails() -> None:
    hits = _scan(_OP_CHOICE)
    assert len(hits) == 1
    assert "2026-12-31" in hits[0].literal  # future-ok: synthetic: assertion
    assert hits[0].path == "ops/src/ops/x.py" and hits[0].line == 1
    assert "future-ok" in hits[0].message() and "allow" in hits[0].message()


def test_real_world_field_passes() -> None:
    assert _scan('valid_from = "2027-06-30"') == []
    assert _scan('"expiry_date": "2027-04-02",') == []
    assert _scan('period["valid_to"] == "2027-06-30"') == []
    assert _scan('end_date = "2026-12-31"') == []


def test_future_ok_marker_passes() -> None:
    assert _scan(_MARKED) == []
    assert _scan(_MARKED_SCHED) == []
    assert _scan('SYNTHETIC_DATE = "2027-01-01"') == []


def test_malformed_future_ok_marker_fails() -> None:
    hits = _scan(_BAD_MARK)
    assert hits, "a marker without `future-ok: <class>: <reason>` is not an exemption"


def test_allow_entry_within_expiry_passes() -> None:
    pol = MG.Policy.parse(
        b"allow ops/** 2026-12-31T23:59:59Z operator choice\n"  # future-ok: synthetic: fixture
    )
    assert _scan(_OP_CHOICE, policy=pol) == []


def test_expired_allow_entry_fails() -> None:
    pol = MG.Policy.parse(
        b"allow ops/** 2026-10-20T00:00:00Z operator choice\n"  # future-ok: synthetic: fixture
    )
    # an entry expired relative to `now` no longer exempts (R5)
    hits = _scan(_OP_CHOICE, policy=pol, now=_NOW + 20 * 86400)
    assert hits and "expired" in hits[0].why


def test_past_literals_are_not_judged() -> None:
    assert _scan('built = "2026-09-28T01:15:49Z"') == []
    assert _scan('on = "2026-10-03"') == []


# --------------------------------------------------------------------------- #
# Release constants (deliverable 1): the notes name the recorded decision     #
# --------------------------------------------------------------------------- #


def test_deferral_notes_reference_the_recorded_decision_not_a_date() -> None:
    """B1 §5.4 regression test 3: EVAL_DEFERRAL_NOTE / EVAL_DISCLOSURE /
    DEFAULT_NOTE carry no ISO date literal — they name the S3 deferral's
    GATE DECISIONS record (commit a33cd6ec; ADR-146) instead."""
    from ops import release_candidate as rc

    for name in ("EVAL_DEFERRAL_NOTE", "EVAL_DISCLOSURE", "DEFAULT_NOTE"):
        text = getattr(rc, name)
        assert ISO_LITERAL_RE.search(text) is None, (
            f"{name} carries an ISO date literal — the deferral references "
            "the recorded decision by id, never a hand-typed date"
        )
        assert "a33cd6ec" in text, f"{name} must name the recorded decision"
