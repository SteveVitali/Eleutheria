"""Tests for check_dispositions.py (row S1b): tiny fixtures, one test per rule and failure mode.

Run: uv run python -m pytest \
         docs/build/planning/2026-09-30-next-phase/tools/test_check_dispositions.py
"""

from __future__ import annotations

import csv
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_dispositions as cd  # noqa: E402

ASKS = [f"U-003.{i}" for i in range(1, 12)]


def _write(path: pathlib.Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def make_pd(tmp: pathlib.Path) -> pathlib.Path:
    pd = tmp / "pd"
    _write(
        pd / "data" / "ticket_catalog.csv",
        ["cat_id", "class", "where_it_must_land", "depends_on"],
        [
            {
                "cat_id": "SEED-11",
                "class": "seed",
                "where_it_must_land": "stage-B seed",
                "depends_on": "",
            },
            {
                "cat_id": "SEED-12",
                "class": "seed",
                "where_it_must_land": "stage-B seed",
                "depends_on": "",
            },
            {
                "cat_id": "R11-ACT-06",
                "class": "r11",
                "where_it_must_land": "early R11 (wave 0)",
                "depends_on": "R11-PRE-01",
            },
            {"cat_id": "R11-PRE-01", "class": "r11", "where_it_must_land": "R11", "depends_on": ""},
            {
                "cat_id": "R11-K13-W1-1",
                "class": "r11",
                "where_it_must_land": "R11",
                "depends_on": "",
            },
            {
                "cat_id": "R11-LATE-01",
                "class": "r11",
                "where_it_must_land": "R11",
                "depends_on": "R11-ACT-06",
            },
            {"cat_id": "OP-01", "class": "operator", "where_it_must_land": "R11", "depends_on": ""},
            {
                "cat_id": "LATER-01",
                "class": "later",
                "where_it_must_land": "later",
                "depends_on": "",
            },
        ],
    )
    _write(
        pd / "data" / "k13_tickets.csv",
        ["ticket_id", "wave"],
        [{"ticket_id": "W1-1", "wave": "W1"}],
    )
    _write(pd / "data" / "decision_catalog.csv", ["dec_id"], [{"dec_id": "Q-1"}])
    _write(
        pd / "universe" / "UNIVERSE.csv",
        ["u_id", "source_kind", "source_ref", "effective_status"],
        [
            {
                "u_id": "U-0001",
                "source_kind": "deferral",
                "source_ref": "D-A-1",
                "effective_status": "OPEN",
            },
            {
                "u_id": "U-0002",
                "source_kind": "requirement",
                "source_ref": "SIG-X-001",
                "effective_status": "PARTIAL",
            },
        ],
    )
    _write(
        pd / "findings" / "FINDINGS.csv",
        ["f_id", "origin_ref", "severity"],
        [
            {"f_id": "F-01", "origin_ref": "A2", "severity": "S1"},
            {"f_id": "F-045", "origin_ref": "X1:NEW-1", "severity": "S2"},
        ],
    )
    fb = pd / "feedback" / "OPERATOR_FEEDBACK.md"
    fb.parent.mkdir(parents=True, exist_ok=True)
    fb.write_text(
        "# fb\n\n### U-001 — what\n\n| id | ask |\n|---|---|\n"
        + "".join(f"| {a} | ask |\n" for a in ASKS)
    )
    _write(
        pd / "data" / "acquisition_plan.csv",
        ["plan_id", "cand_ids", "ticket"],
        [
            {"plan_id": "AP-1", "cand_ids": "C-1", "ticket": "ACQ-01 -> live ACQ-02"},
            {"plan_id": "AP-2", "cand_ids": "C-2;C-3", "ticket": "later-phase(new family foo)"},
        ],
    )
    _write(
        pd / "data" / "candidates_consolidated.csv",
        ["cand_ids_merged"],
        [{"cand_ids_merged": "C-1"}, {"cand_ids_merged": "C-2;C-3"}],
    )
    return pd


def row(item, kind, ref, disp, dref, status="", links="", why="because"):
    return {
        "item_id": item,
        "source_kind": kind,
        "source_ref": ref,
        "title": "t",
        "severity_or_status": status,
        "disposition": disp,
        "disposition_ref": dref,
        "rationale": why,
        "stream": "S1b",
        "links": links,
    }


def baseline() -> list[dict]:
    rows = [
        row("U-0001", "deferral", "D-A-1", "ticket(R11-ACT-06)", "R11-ACT-06", "OPEN"),
        row(
            "U-0002", "requirement", "SIG-X-001", "spec-amendment(SIG-X-001)", "SEED-12", "PARTIAL"
        ),
        row("F-01", "finding", "A2", "ticket(R11-K13-W1-1)", "R11-K13-W1-1", "S1"),
        row("F-045", "finding", "X1:NEW-1", "merged-into(F-01)", "F-01", "S2"),
        row(
            "U-001",
            "feedback",
            "feedback/OPERATOR_FEEDBACK.md U-001",
            "already-done(recorded)",
            "OPERATOR_FEEDBACK.md U-001",
        ),
        row(
            "CG-ACQ-01",
            "candidate_group",
            "plan",
            "ticket(R11-LATE-01)",
            "R11-LATE-01",
            "n=1 candidates",
        ),
        row(
            "CG-LATER-new-family-foo",
            "candidate_group",
            "plan",
            "later-phase(new family foo)",
            "LATER-01",
            "n=1 candidates",
        ),
    ]
    for a in ASKS:
        rows.append(
            row(
                a,
                "feedback",
                f"feedback/OPERATOR_FEEDBACK.md {a}",
                "ticket(R11-K13-W1-1)",
                "R11-K13-W1-1;R11-LATE-01",
            )
        )
    return rows


def errs(rows, pd):
    return cd.check(rows, pd).errors


@pytest.fixture()
def pd(tmp_path):
    return make_pd(tmp_path)


def test_baseline_passes(pd):
    assert errs(baseline(), pd) == []


def test_main_exit_codes(pd, tmp_path):
    out = pd / "universe" / "UNIVERSE_DISPOSED.csv"
    _write(out, cd.COLS, baseline())
    assert cd.main(["--pd", str(pd)]) == 0
    bad = [r for r in baseline() if r["item_id"] != "F-01"]
    _write(out, cd.COLS, bad)
    assert cd.main(["--pd", str(pd)]) == 1


# ---- (a) exactly once
def test_a_missing_item(pd):
    rows = [r for r in baseline() if r["item_id"] != "U-0002"]
    assert any(e.startswith("(a) source item U-0002") for e in errs(rows, pd))


def test_a_duplicate_item(pd):
    rows = baseline() + [baseline()[0]]
    assert any("U-0001 appears 2 times" in e for e in errs(rows, pd))


def test_a_extra_item(pd):
    rows = baseline() + [row("F-999", "finding", "Z", "ticket(R11-ACT-06)", "R11-ACT-06")]
    assert any("F-999 is not a source item" in e for e in errs(rows, pd))


def test_a_wrong_source_ref_and_kind(pd):
    rows = baseline()
    rows[0] = dict(rows[0], source_ref="D-WRONG", source_kind="risk")
    e = errs(rows, pd)
    assert any("U-0001 source_kind" in x for x in e) and any("U-0001 source_ref" in x for x in e)


def test_a_group_size_mismatch(pd):
    rows = baseline()
    rows[5] = dict(rows[5], severity_or_status="n=7 candidates")
    assert any("CG-ACQ-01 size" in e for e in errs(rows, pd))


def test_a_candidate_in_two_plan_rows(pd):
    _write(
        pd / "data" / "acquisition_plan.csv",
        ["plan_id", "cand_ids", "ticket"],
        [
            {"plan_id": "AP-1", "cand_ids": "C-1", "ticket": "ACQ-01 -> live ACQ-02"},
            {"plan_id": "AP-2", "cand_ids": "C-1;C-2;C-3", "ticket": "later-phase(new family foo)"},
        ],
    )
    rows = baseline()
    rows[6] = dict(rows[6], severity_or_status="n=1 candidates")
    assert any("candidate C-1 appears in 2" in e for e in errs(rows, pd))


# ---- (b) enum and references
def test_b_kind_not_in_enum(pd):
    rows = baseline()
    rows[1] = dict(rows[1], disposition="postpone(SIG-X-001)")
    assert any("not in the enum" in e for e in errs(rows, pd))


def test_b_unparseable_disposition(pd):
    rows = baseline()
    rows[1] = dict(rows[1], disposition="ticket R11-ACT-06")
    assert any("is not kind(arg)" in e for e in errs(rows, pd))


def test_b_unknown_cat(pd):
    rows = baseline()
    rows[0] = dict(rows[0], disposition="ticket(R11-NOPE-01)", disposition_ref="R11-NOPE-01")
    assert any("R11-NOPE-01 is not a catalog unit" in e for e in errs(rows, pd))


def test_b_ticket_class_must_fit(pd):
    rows = baseline()
    rows[0] = dict(rows[0], disposition="ticket(LATER-01)", disposition_ref="LATER-01")
    assert any("class 'later', not seed/r11" in e for e in errs(rows, pd))


def test_b_operator_action_needs_operator_unit(pd):
    rows = baseline()
    rows[0] = dict(rows[0], disposition="operator-action(do it)", disposition_ref="R11-ACT-06")
    assert any("operator-action ref R11-ACT-06" in e for e in errs(rows, pd))
    rows[0] = dict(rows[0], disposition="operator-action(do it)", disposition_ref="OP-01")
    assert not any("U-0001" in e and "(b)" in e for e in errs(rows, pd))


def test_b_unknown_decision(pd):
    rows = baseline()
    rows[0] = dict(rows[0], disposition="decision(Q-404)", disposition_ref="Q-404")
    assert any("decision Q-404 is not in the decision catalog" in e for e in errs(rows, pd))


def test_b_spec_and_waiver_landing(pd):
    rows = baseline()
    rows[1] = dict(rows[1], disposition="spec-amendment(SIG-X-001)", disposition_ref="SEED-11")
    assert any("spec-amendment must land in SEED-12" in e for e in errs(rows, pd))
    rows[1] = dict(rows[1], disposition="adr-waiver(draft ADR)", disposition_ref="SEED-12")
    assert any("adr-waiver must land in SEED-11" in e for e in errs(rows, pd))


def test_b_merged_into_chain_and_missing(pd):
    rows = baseline()
    rows[2] = dict(rows[2], disposition="merged-into(U-0001)", disposition_ref="U-0001")
    rows[0] = dict(rows[0], disposition="merged-into(U-0002)", disposition_ref="U-0002")
    assert any("is itself merged" in e for e in errs(rows, pd))
    rows = baseline()
    rows[3] = dict(rows[3], disposition="merged-into(F-777)", disposition_ref="F-777")
    assert any("target F-777 is not an item" in e for e in errs(rows, pd))


def test_b_later_phase_needs_explicit_trigger(pd):
    rows = baseline()
    rows[1] = dict(rows[1], disposition="later-phase(trigger)", disposition_ref="LATER-01")
    assert any("no explicit trigger" in e for e in errs(rows, pd))
    rows[1] = dict(
        rows[1],
        disposition="later-phase(operator authorises contact)",
        disposition_ref="R11-ACT-06",
    )
    assert any("later-phase ref R11-ACT-06" in e for e in errs(rows, pd))


def test_b_already_done_needs_evidence(pd):
    rows = baseline()
    rows[1] = dict(rows[1], disposition="already-done(x)", disposition_ref="SEED-12")
    assert any("needs evidence text" in e for e in errs(rows, pd))


def test_b_link_tokens_resolve(pd):
    rows = baseline()
    rows[0] = dict(rows[0], links="gate:Q-404 interim:R11-NOPE-01 U-0999 F-888 CG-NONE")
    e = " | ".join(errs(rows, pd))
    for tok in ("gate:Q-404", "interim:R11-NOPE-01", "U-0999", "F-888", "CG-NONE"):
        assert tok in e


# ---- (c) S0/S1 placement
def test_c_first_wave_closure(pd):
    fw = cd.first_waves(cd.load_catalog(pd), pd)
    assert {"SEED-11", "R11-ACT-06", "R11-PRE-01", "R11-K13-W1-1"} <= fw
    assert "R11-LATE-01" not in fw and "LATER-01" not in fw


def test_c_severe_outside_first_waves_fails(pd):
    rows = baseline()
    rows[2] = dict(rows[2], disposition="ticket(R11-LATE-01)", disposition_ref="R11-LATE-01")
    assert any(e.startswith("(c) F-01") for e in errs(rows, pd))


def test_c_interim_decision_and_done_pass(pd):
    rows = baseline()
    rows[2] = dict(
        rows[2],
        disposition="ticket(R11-LATE-01)",
        disposition_ref="R11-LATE-01",
        links="interim:R11-ACT-06",
    )
    assert errs(rows, pd) == []
    rows[2] = dict(rows[2], disposition="decision(Q-1)", disposition_ref="Q-1", links="")
    assert errs(rows, pd) == []
    rows[2] = dict(rows[2], disposition="already-done(fixed live)", disposition_ref="evidence.txt")
    assert errs(rows, pd) == []


def test_c_interim_must_itself_be_first_wave(pd):
    rows = baseline()
    rows[2] = dict(
        rows[2],
        disposition="ticket(R11-LATE-01)",
        disposition_ref="R11-LATE-01",
        links="interim:LATER-01",
    )
    assert any(e.startswith("(c) F-01") for e in errs(rows, pd))


def test_c_severe_wontfix_fails(pd):
    rows = baseline()
    rows[2] = dict(rows[2], disposition="wontfix(not worth it)", disposition_ref="note.md")
    assert any("(c) F-01 (S1) is wontfix" in e for e in errs(rows, pd))


def test_c_follows_merged_into(pd):
    rows = baseline()
    sev = pd / "findings" / "FINDINGS.csv"
    _write(
        sev,
        ["f_id", "origin_ref", "severity"],
        [
            {"f_id": "F-01", "origin_ref": "A2", "severity": "S1"},
            {"f_id": "F-045", "origin_ref": "X1:NEW-1", "severity": "S0"},
        ],
    )
    rows[2] = dict(rows[2], disposition="ticket(R11-LATE-01)", disposition_ref="R11-LATE-01")
    e = errs(rows, pd)
    assert any(x.startswith("(c) F-045") for x in e) and any(x.startswith("(c) F-01") for x in e)


# ---- (d) operator asks
def test_d_ask_needs_a_ticket(pd):
    rows = baseline()
    i = next(n for n, r in enumerate(rows) if r["item_id"] == "U-003.4")
    rows[i] = dict(rows[i], disposition="already-done(it works)", disposition_ref="note.md")
    assert any("(d) operator ask U-003.4" in e for e in errs(rows, pd))


def test_d_ask_missing(pd):
    rows = [r for r in baseline() if r["item_id"] != "U-003.11"]
    assert any("(d) operator ask U-003.11 has no disposition" in e for e in errs(rows, pd))


# ---- (e) owed deferrals
def test_e_owed_deferral_missing(pd):
    rows = [r for r in baseline() if r["item_id"] != "U-0001"]
    assert any(e.startswith("(e) owed deferral D-A-1") for e in errs(rows, pd))


def test_e_owed_deferral_counts(pd):
    res = cd.check(baseline(), pd)
    assert res.stats["owed_n"] == 1 and res.stats["owed"] == {"ticket": 1}


# ---- helpers
@pytest.mark.parametrize(
    "ticket,group",
    [
        ("ACQ-23 -> live ACQ-27 (conditional: N-line / RB-06 a)", "CG-ACQ-23"),
        ("none (I7 Tier 3)", "CG-TIER3"),
        ("G2-step5(E4 D-R10-SOURCES-1 dossier captures)", "CG-G2-STEP5"),
        ("later-phase(new family ogc_wms)", "CG-LATER-new-family-ogc-wms"),
    ],
)
def test_plan_group(ticket, group):
    assert cd.plan_group(ticket) == group


def test_plan_group_unknown():
    with pytest.raises(ValueError):
        cd.plan_group("something else")


def test_parse_disposition():
    assert cd.parse_disposition("ticket(R11-ACT-06)") == ("ticket", "R11-ACT-06")
    assert cd.parse_disposition("later-phase(a (nested) trigger)") == (
        "later-phase",
        "a (nested) trigger",
    )
    assert cd.parse_disposition("ticket") is None


def test_feedback_ids(pd):
    ids = cd.load_feedback_ids(pd)
    assert ids[0] == "U-001" and ids[1:] == ASKS
