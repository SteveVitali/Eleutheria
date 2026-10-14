#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_round_close.py`` — the G9 round-close record checks, the capstone
two-sum (G7 item 5) and the tail probe-sweep contract (G10) (P34.33; ADR-199).

Each rule is exercised on a small fixture tree: a valid baseline passes, and one mutation
per test makes exactly that rule fail. Collected by ``make test`` (``testpaths`` includes
``docs/build/tools``)::

    uv run pytest docs/build/tools/test_check_round_close.py
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import pathlib
from datetime import UTC, datetime

_HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[2]
_spec = importlib.util.spec_from_file_location("check_round_close", _HERE / "check_round_close.py")
crc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(crc)

WHEN = "2026-10-02T12:00:00Z"  # inside a 2026-10-01 round
TAIL = "2026-10-01"
AT = datetime(2026, 10, 2, 13, 0, 0, tzinfo=UTC)  # probe records ≤ 24 h old here

POLICY = """schema = "round-close-policy/1"

[banners]
exempt_rounds = [2, 3]
[banners.required_cites]
11 = ["Part XII", "§56"]

[packets]
patterns = ["docs/build/readouts/GATE-*.md", "docs/build/readouts/ACCEPT-*.md"]
[[packets.exempt]]
path = "docs/build/readouts/ACCEPT-R9.md"
date = "2026-09-20"
note = "historical packet predating the two-sum grammar"
"""

SWEEP = """schema = "tail-probe-sweep/1"

[[probe]]
id = "route-allowlist"
title = "public-route allow-list and absence"
requires = ["SIG-OPS-003"]
owner = "P34.10"
command = "uv run sig-ops republish-probe --record-out docs/build/reports/probes/route.json"
record = "docs/build/reports/probes/route-allowlist.json"

[[probe]]
id = "number-truth"
title = "displayed numbers recomputed from bulk"
requires = ["SIG-OPS-011", "DR-C3-15"]
owner = "P35.3"
command = "uv run sig-ops probe-sweep --only number-truth --record-out <record>"
record = "docs/build/reports/probes/number-truth.json"
"""

RISK = """# Risk register

## Phase 1

### Deferred / out of scope here (SIG-ENG-005)

| id | Risk | Compensating control | Revisit trigger |
|---|---|---|---|
| RISK-P1-01 → BL-001 | cited home | c | t |
| RISK-P1-02 | owned via BL-001 sources | c | t |
| RISK-P1-03 | owned by closed BL-002, re-homed below | c | t |

## Round 11 review — seed (recorded 2026-10-02T10:00:00Z)

### Corrections, closures and re-routes of earlier rows (append-only)

| id | correction (recorded 2026-10-02T10:00:00Z) | authority |
|---|---|---|
| RISK-P1-03 | Re-homed BL-002 → **BL-001** (open). | U-1 |
"""

MANIFEST = """# Manifest

## How to build

intro

## The chain

### Round 2 — an old round (rows 1–2)

| # | file |
|---|---|
| 1 | `a.md` |

### Round 11 — P34 11A · rows 201–260, to GATE-G4 · spec: Part XII (§56)

| # | Ticket file |
|---|---|
| 201 | `238_P34.33__x.md` |

## Next section
"""

SPEC = """# Part XII — Round 11

## 56. Round-11 contract extension (2026-10-01)

### 56.1 Scope
"""

BACKLOG = (
    "bl_id,title,type,sources,req_ids,package,blocks,landing,gate,size,status\n"
    "BL-001,a,process,RISK-P1-02,,,,P01+,,S,open\n"
    "BL-002,b,process,RISK-P1-03,,,,P01+,,S,closed\n"
    "BL-003,c,process,ADR-100,,,,P01+,,S,open\n"
)

MATRIX = (
    "id,level,spec_section,class,verdict,evidence,owning_tickets,tests,adrs,risk_rows,"
    "routing,note,required_domain,achieved_domain,owed_legs,accepted_scope\n"
    "SIG-A-001,MUST,1,covered+tested,MET,e,P01.1,t,,—,—,n,implementation,public,—,—\n"
    "SIG-A-002,MUST,1,covered+tested,MET,e,P01.1,t,,—,—,n,implementation,—,—,—\n"
    "SIG-A-003,MUST,1,covered+tested,MET-DIFFERENTLY(ADR-001),e,P01.1,t,ADR-001,—,—,n,implementation,public,—,—\n"
    "SIG-A-004,MUST,1,engineered,MET-ENGINEERED(D-X-1),e,P01.1,t,,—,—,n,implementation,implementation,—,—\n"
    "SIG-A-005,MUST,1,missing,MISSING,e,P01.1,t,,—,—,n,implementation,—,—,—\n"
    "SIG-A-006,MUST,1,waived,WAIVED(ADR-001),e,P01.1,t,ADR-001,—,—,n,implementation,—,—,—\n"
)
# matrix counts: MET 2 · MET-DIFFERENTLY 1 · MET-ENGINEERED 1 · MISSING 1 · WAIVED 1
# → engineering closed = 4, requirement satisfied = 3; layer [public]: ec 2, rs 2

LEDGER = "round:           11\nstatus:          active\n"

PACKET_OK = """# GATE-G4 packet

Recorded 2026-10-05.

Coverage: 2 MET, 1 MET-DIFFERENTLY, 1 MET-ENGINEERED, 1 MISSING, 1 WAIVED(ADR-001).

coverage two-sum: engineering closed = 4 · requirement satisfied = 3
coverage two-sum [public]: engineering closed = 2 · requirement satisfied = 2
"""

PACKET_EXEMPT = """# ACCEPT-R9 (historical)

Recorded 2026-09-20. Coverage: 9 MET, 1 PARTIAL.
"""

TRACE = "# Traceability\n\n**Frozen historical view**: see the coverage matrix.\n"
TVS = "# Ticket vs spec\n\n**Frozen historical view**: see the coverage matrix.\n"

ADR_WITH_TRIGGER = """# ADR-100: A decision

- **Status:** Accepted

## Revisit trigger

The thing changes.
"""

WAIVER_ADR = """# ADR-{n}: Waiver {w}

- **Status:** Accepted

## Revisit trigger

Waiver {w} ends.
"""


def _csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=crc.adr_triggers.COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _register_rows() -> tuple[str, dict[str, pathlib.Path]]:
    """One kind=adr row (ADR-100) plus the waiver rows the register requires."""
    files: dict[str, pathlib.Path] = {"docs/adr/ADR-100-decision.md": ADR_WITH_TRIGGER}
    rows = [
        {
            "adr": "ADR-100",
            "trigger_sha256": crc.adr_triggers.trigger_sha256(ADR_WITH_TRIGGER),
            "state": "quiet",
            "evidence": "e",
            "probe_id": "",
            "home": "BL-003",
            "last_evaluated": WHEN,
            "kind": "adr",
            "waiver": "",
            "trigger_text": "",
        }
    ]
    for i, wv in enumerate(crc.adr_triggers.WAIVER_LINES, start=110):
        text = WAIVER_ADR.format(n=i, w=wv)
        files[f"docs/adr/ADR-{i:03d}-waiver.md"] = text
        rows.append(
            {
                "adr": f"ADR-{i:03d}",
                "trigger_sha256": crc.adr_triggers.trigger_sha256(text),
                "state": "quiet",
                "evidence": "e",
                "probe_id": "",
                "home": "BL-003",
                "last_evaluated": WHEN,
                "kind": "waiver",
                "waiver": wv,
                "trigger_text": "",
            }
        )
    return _csv(rows), files


def _probe_record(at_ts: str = WHEN, verdict: str = "pass") -> str:
    return json.dumps(
        {
            "version": "sig.probe-run/1",
            "generated_at": at_ts,
            "checks": {"leg-1": {"verdict": verdict}},
            "overall": verdict,
        }
    )


def _tree(tmp_path: pathlib.Path, **files) -> pathlib.Path:
    root = tmp_path / "repo"
    register, adr_files = _register_rows()
    base = {
        "docs/risk_register.md": RISK,
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/build/BACKLOG.csv": BACKLOG,
        "docs/2_canonical_design_spec.md": SPEC,
        "docs/build/COVERAGE_MATRIX.csv": MATRIX,
        "docs/build/LEDGER.md": LEDGER,
        "docs/build/tools/record_policy/round_close.toml": POLICY,
        "docs/build/tools/record_policy/tail_probe_sweep.toml": SWEEP,
        "docs/traceability.md": TRACE,
        "docs/build/TICKET_VS_SPEC.md": TVS,
        "docs/build/readouts/GATE-G4.md": PACKET_OK,
        "docs/build/readouts/ACCEPT-R9.md": PACKET_EXEMPT,
        crc.adr_triggers.REGISTER: register,
    }
    for rel, text in {**adr_files, **base, **files}.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text)
    return root


def _errors(root: pathlib.Path, **kw) -> list[str]:
    errors, _stats = crc.check(root, **kw)
    return errors


def test_valid_baseline_passes(tmp_path) -> None:
    errors = _errors(_tree(tmp_path))
    assert errors == [], errors


# ── RISK ids unique / deferred routing (G9) ─────────────────────────────────────


def test_duplicate_risk_id_needs_a_dated_rename(tmp_path) -> None:
    dup = RISK.replace(
        "### Corrections, closures and re-routes",
        "| RISK-P1-01 → BL-001 | second row for the same id | c | t |\n\n"
        "### Corrections, closures and re-routes",
    )
    root = _tree(tmp_path, **{"docs/risk_register.md": dup})
    assert any("RISK-P1-01" in e and "heads 2 definition rows" in e for e in _errors(root))

    renamed = dup.replace(
        "| RISK-P1-03 | Re-homed",
        "| RISK-P1-01 (second occurrence) | **Renamed RISK-P1-01a by this record.** | U-2 |\n"
        "| RISK-P1-03 | Re-homed",
    )
    root = _tree(tmp_path / "ok", **{"docs/risk_register.md": renamed})
    assert _errors(root) == []


def test_rename_outside_a_dated_round_review_fails(tmp_path) -> None:
    undated = RISK.replace(
        "## Round 11 review — seed (recorded 2026-10-02T10:00:00Z)",
        "## Round 11 review — seed",
    ).replace(
        "| RISK-P1-03 | Re-homed",
        "| RISK-P1-03 | **Renamed RISK-P1-01a by this record.** "
        "Re-homed BL-002 → **BL-001**. | U-1 |",
    )
    root = _tree(tmp_path, **{"docs/risk_register.md": undated})
    assert any("outside a dated" in e for e in _errors(root))


def test_unrouted_deferred_row_fails(tmp_path) -> None:
    unrouted = RISK.replace(
        "| RISK-P1-01 → BL-001 | cited home | c | t |",
        "| RISK-P1-04 | no owner, no cite, no record | c | t |",
    )
    root = _tree(tmp_path, **{"docs/risk_register.md": unrouted})
    assert any("RISK-P1-04" in e and "unrouted" in e for e in _errors(root))


def test_rehome_without_corrections_record_fails(tmp_path) -> None:
    # RISK-P1-03's owner is BL-002; give its row a divergent cite with no record.
    bad = RISK.replace(
        "| RISK-P1-03 | owned by closed BL-002",
        "| RISK-P1-03 → BL-001 | owned by closed BL-002",
    ).replace("| RISK-P1-03 | Re-homed BL-002 → **BL-001** (open). | U-1 |\n", "")
    root = _tree(tmp_path, **{"docs/risk_register.md": bad})
    assert any("RISK-P1-03" in e and "re-homed" in e for e in _errors(root))


def test_reroute_target_must_be_open(tmp_path) -> None:
    closed = RISK.replace("Re-homed BL-002 → **BL-001**", "Re-homed BL-002 → **BL-002**")
    root = _tree(tmp_path, **{"docs/risk_register.md": closed})
    assert any("RISK-P1-03" in e and "BL-002" in e and "not open" in e for e in _errors(root))


def test_dead_id_cell_cite_fails(tmp_path) -> None:
    dead = RISK.replace("RISK-P1-01 → BL-001", "RISK-P1-01 → BL-099")
    root = _tree(tmp_path, **{"docs/risk_register.md": dead})
    assert any("RISK-P1-01" in e and "BL-099" in e for e in _errors(root))


# ── Round banners ↔ spec parts (G9) ─────────────────────────────────────────────


def test_round_banner_without_a_spec_cite_fails(tmp_path) -> None:
    bare = MANIFEST.replace(" · spec: Part XII (§56)", "")
    root = _tree(tmp_path, **{"docs/tickets/00_MANIFEST.md": bare})
    assert any("must cite 'Part XII'" in e for e in _errors(root))


def test_unmapped_round_banner_needs_any_resolving_cite(tmp_path) -> None:
    extra = MANIFEST.replace(
        "## Next section",
        "### Round 12 — the next round (rows 600–610)\n\n| # | file |\n|---|---|\n"
        "| 600 | `y.md` |\n\n## Next section",
    )
    root = _tree(tmp_path / "a", **{"docs/tickets/00_MANIFEST.md": extra})
    assert any("Round 12" in e and "cites no spec" in e for e in _errors(root))
    cited = extra.replace(
        "### Round 12 — the next round", "### Round 12 — the next round · spec: Part XII"
    )
    root = _tree(tmp_path / "b", **{"docs/tickets/00_MANIFEST.md": cited})
    assert _errors(root) == []


def test_unresolvable_banner_cite_fails(tmp_path) -> None:
    extra = MANIFEST.replace(
        "## Next section",
        "### Round 12 — the next round · spec: Part LXXXIX (rows 600–610)\n\n"
        "| # | file |\n|---|---|\n| 600 | `y.md` |\n\n## Next section",
    )
    root = _tree(tmp_path, **{"docs/tickets/00_MANIFEST.md": extra})
    assert any("Round 12" in e and "none resolves" in e for e in _errors(root))


def test_exempt_rounds_need_no_cite(tmp_path) -> None:
    # the fixture Round-2 banner carries no cite and is exempt — the baseline already
    # covers this; assert the exempt set is what the fixture policy declares
    errors = _errors(_tree(tmp_path))
    assert not any("Round 2" in e for e in errors)


# ── Frozen views (G9) ───────────────────────────────────────────────────────────


def test_missing_frozen_pointer_fails(tmp_path) -> None:
    root = _tree(tmp_path, **{"docs/traceability.md": "# Traceability\n"})
    assert any("traceability.md" in e and "Frozen historical view" in e for e in _errors(root))


# ── Capstone two-sum (G7 item 5 / SIG-ENG-041) ──────────────────────────────────


def test_claims_without_two_sum_fail(tmp_path) -> None:
    no_sum = PACKET_OK.replace(
        "coverage two-sum: engineering closed = 4 · requirement satisfied = 3\n"
        "coverage two-sum [public]: engineering closed = 2 · requirement satisfied = 2\n",
        "",
    )
    root = _tree(tmp_path, **{"docs/build/readouts/GATE-G4.md": no_sum})
    errors = _errors(root)
    assert any("coverage two-sum" in e for e in errors)
    # a bare claim equal to the matrix count is fine; the missing declaration is the fault
    assert not any("the matrix counts" in e for e in errors)


def test_folded_met_claim_fails(tmp_path) -> None:
    # "4 MET" folds MET-ENGINEERED into MET — the '34 MET' replay
    folded = PACKET_OK.replace("Coverage: 2 MET", "Coverage: 4 MET")
    root = _tree(tmp_path, **{"docs/build/readouts/GATE-G4.md": folded})
    assert any("claims 4 MET" in e and "the matrix counts 2" in e for e in _errors(root))


def test_wrong_two_sum_fails(tmp_path) -> None:
    wrong = PACKET_OK.replace("engineering closed = 4", "engineering closed = 5")
    root = _tree(tmp_path, **{"docs/build/readouts/GATE-G4.md": wrong})
    assert any("declares" in e and "recomputes 4" in e for e in _errors(root))


def test_unknown_layer_two_sum_fails(tmp_path) -> None:
    wrong = PACKET_OK.replace("coverage two-sum [public]", "coverage two-sum [nightly]")
    root = _tree(tmp_path, **{"docs/build/readouts/GATE-G4.md": wrong})
    assert any("unknown status layer" in e for e in _errors(root))


def test_vacuous_exemption_fails(tmp_path) -> None:
    empty = "# ACCEPT-R9\n\nRecorded 2026-09-20. No counts here.\n"
    root = _tree(tmp_path, **{"docs/build/readouts/ACCEPT-R9.md": empty})
    assert any("exempt by date" in e and "vacuous" in e for e in _errors(root))


def test_packet_patterns_and_no_claim_packets(tmp_path) -> None:
    # a packet with no coverage claims owes no two-sum
    quiet = "# GATE-G9\n\nRecorded 2026-10-05. No coverage claims.\n"
    root = _tree(
        tmp_path,
        **{
            "docs/build/readouts/GATE-G4.md": quiet,
            "docs/build/readouts/GATE-G9.md": quiet,
        },
    )
    assert _errors(root) == []


# ── Tail mode (--round-tail) ────────────────────────────────────────────────────


def _tail_tree(tmp_path, **files) -> pathlib.Path:
    base = {
        "docs/build/reports/probes/route-allowlist.json": _probe_record(),
        "docs/build/reports/probes/number-truth.json": _probe_record(),
    }
    return _tree(tmp_path, **{**base, **files})


def test_tail_happy_path(tmp_path) -> None:
    errors = _errors(_tail_tree(tmp_path), round_tail=TAIL, at=AT)
    assert errors == [], errors


def test_tail_requires_the_dated_round_review(tmp_path) -> None:
    no_review = RISK.replace(
        "## Round 11 review — seed (recorded 2026-10-02T10:00:00Z)",
        "## Round 11 review — seed",
    )
    errors = _errors(
        _tail_tree(tmp_path, **{"docs/risk_register.md": no_review}), round_tail=TAIL, at=AT
    )
    assert any("recorded <ts>" in e for e in errors)

    stale_review = no_review.replace(
        "## Round 11 review — seed",
        "## Round 11 review — seed (recorded 2026-09-30T23:00:00Z)",
    )
    errors = _errors(
        _tail_tree(tmp_path / "b", **{"docs/risk_register.md": stale_review}),
        round_tail=TAIL,
        at=AT,
    )
    assert any("predates the round start" in e for e in errors)

    gone = no_review.replace("## Round 11 review — seed", "## Round 10 review — old")
    errors = _errors(
        _tail_tree(tmp_path / "c", **{"docs/risk_register.md": gone}),
        round_tail=TAIL,
        at=AT,
    )
    assert any("no '## Round 11 review'" in e for e in errors)


def test_tail_probe_records_required_fresh_and_evaluating(tmp_path) -> None:
    errors = _errors(
        _tree(tmp_path, **{"docs/build/reports/probes/number-truth.json": _probe_record()}),
        round_tail=TAIL,
        at=AT,
    )
    assert any("route-allowlist" in e and "no docs/build/reports/probes" in e for e in errors)

    stale = _tail_tree(
        tmp_path / "b",
        **{"docs/build/reports/probes/number-truth.json": _probe_record("2026-09-20T00:00:00Z")},
    )
    errors = _errors(stale, round_tail=TAIL, at=AT)
    assert any("number-truth" in e and "older than 24 h" in e for e in errors)

    skipped = _tail_tree(
        tmp_path / "c",
        **{"docs/build/reports/probes/number-truth.json": _probe_record(verdict="skipped")},
    )
    errors = _errors(skipped, round_tail=TAIL, at=AT)
    assert any("number-truth" in e and "every leg skipped" in e for e in errors)

    empty_checks = json.dumps(
        {
            "version": "sig.probe-run/1",
            "generated_at": WHEN,
            "checks": {},
            "overall": "pass",
        }
    )
    root = _tail_tree(
        tmp_path / "d",
        **{"docs/build/reports/probes/number-truth.json": empty_checks},
    )
    errors = _errors(root, round_tail=TAIL, at=AT)
    assert any("number-truth" in e and "'checks' is empty" in e for e in errors)


def test_tail_runs_the_trigger_register_sweep(tmp_path) -> None:
    # an unanswered trigger without an S1 disposition fails via adr_triggers --round-tail
    buf = io.StringIO(_register_rows()[0])
    table = list(csv.DictReader(buf))
    table[0]["state"] = "fired-unanswered"
    table[0]["evidence"] = "FIRED; no answer recorded"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=crc.adr_triggers.COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(table)
    errors = _errors(
        _tail_tree(tmp_path, **{crc.adr_triggers.REGISTER: buf.getvalue()}),
        round_tail=TAIL,
        at=AT,
    )
    assert any("adr_triggers --round-tail" in e and "disposition" in e for e in errors)


def test_bad_sweep_contract_fails(tmp_path) -> None:
    bad = SWEEP.replace(
        'record = "docs/build/reports/probes/number-truth.json"',
        'record = "nowhere.json"',
    )
    errors = _errors(
        _tree(tmp_path, **{"docs/build/tools/record_policy/tail_probe_sweep.toml": bad})
    )
    assert any("number-truth" in e and "record" in e for e in errors)


def test_cli_exit_codes(tmp_path) -> None:
    root = _tree(tmp_path / "ok")
    assert crc.main(["--root", str(root), "check"]) == 0
    bad = _tree(tmp_path / "bad", **{"docs/traceability.md": "no pointer\n"})
    assert crc.main(["--root", str(bad), "check"]) == 1
    assert crc.main(["--root", str(root), "check", "--round-tail", "not-a-date"]) == 2


def test_committed_tree_passes() -> None:
    """The real tree passes the structure checks (the checker's own gate)."""
    errors, stats = crc.check(REPO_ROOT)
    assert errors == [], errors[:20]
    assert stats["deferred_evaluated"] == stats["deferred"] > 0
    assert stats["banners_evaluated"] == stats["banners"] > 0
    assert stats["sweep_probes"] > 0
