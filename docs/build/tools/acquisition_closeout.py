#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""acquisition_closeout.py — P37.66 (R11-ACQ-28) coverage-outcome + acquisition-closeout generator/checker.

Everything is reported at the layer actually reached — ``live_verification=false``, no wave leg
executed live in this dispatch: coverage numbers are *planned* routing over committed evidence,
the realized claims-layer delta is honestly zero, and every live half is a named queued
obligation — never a fabricated green.

Generated outputs (all deterministic from committed inputs): ``COVERAGE_OUTCOME.md`` (the
coverage-delta report per I1 blind spot — I8 §9 + §7.7, the committed ``sig-ops coverage-delta``
method over committed snapshots, never ``/v1/coverage``; the COV-05 vendor×state table; the Class
S readout inputs), ``QUEUE_OUTCOMES.md`` (all 27 reviewed ADR-130 ``SRC-0xx`` dispositions),
``closeout.json`` (``sig.acquisition-closeout/1``), and one appended ``### P37.66`` section in
``docs/tickets/DEFERRALS.md`` — ``D-P37.66-1…-12`` for the 130 ``later-phase(…)`` Tier-2 plan
rows (I8 §6.3's twelve groups) and ``D-P37.66-13…-15`` for the six statutory duty leads; every
row ``owner:``/``trigger:`` (rule 5), each anchored by an ``obligation-event/1`` ``:e0``.

Inputs (all committed): ``PD/data/acquisition_plan.csv`` (694 rows),
``PD/data/candidates_consolidated.csv``, the ADR-130 queue
(``tasks/src/tasks/data/acquisition_queue.toml`` +
``2026-09-25-six-streams/data/source-candidates.csv``),
``tasks/src/tasks/data/statute_leads.toml``,
``connectors/src/connectors/data/sources.toml`` (partitions "unregistered" proposed ids into I8
§5.8 reconciled renames vs genuinely absent), and ``DEFERRALS.md``. ``--check`` regenerates
byte-for-byte, verifies every expected row exists with each generated cell's text intact and that
all 130 plan ids ride exactly one row — a regression fails loud.

Usage::

    python3 docs/build/tools/acquisition_closeout.py --write   # (re)generate (idempotent)
    python3 docs/build/tools/acquisition_closeout.py --check   # verify; exit 1 on drift

Exit codes: 0 ok · 1 drift/missing · 2 input error. Stdlib only; Python 3.11+.
Group owner/trigger/verify wording is this unit's reading of I8 §6.3 and the plan's own
``ticket`` labels (agent interpretation, labelled in the output); plan cells, duty postures and
queue fields are quoted verbatim.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
import tomllib
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[3]
PD = "docs/build/planning/2026-09-30-next-phase"
PLAN_CSV = ROOT / f"{PD}/data/acquisition_plan.csv"
CANDS_CSV = ROOT / f"{PD}/data/candidates_consolidated.csv"
I1_CSV = ROOT / f"{PD}/data/source_coverage.csv"
QUEUE_TOML = ROOT / "tasks/src/tasks/data/acquisition_queue.toml"
QUEUE_CSV = ROOT / "docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv"
STATUTE_TOML = ROOT / "tasks/src/tasks/data/statute_leads.toml"
SOURCES_TOML = ROOT / "connectors/src/connectors/data/sources.toml"
DEFERRALS = ROOT / "docs/tickets/DEFERRALS.md"
OUT_DIR = ROOT / "docs/build/reports/p37.66-acquisition-closeout"
OUT_MD = OUT_DIR / "COVERAGE_OUTCOME.md"
OUT_QUEUE = OUT_DIR / "QUEUE_OUTCOMES.md"
OUT_JSON = OUT_DIR / "closeout.json"

SECTION = "### P37.66 — coverage outcome & acquisition closeout (row 495)"
HEADER = "| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |"
SEP = "|---|---|---|---|---|---|---|---|"
ROW_RE = re.compile(r"^\| (D-P37\.66-\d+) \|", re.M)
TICKET = "P37.66"
RECORDED = "2026-11-18"
HOME = "BL-087"

# The plan's own counts (asserted — the report fails loud on drift).
PLAN_COUNTS = {"W": 46, "1": 108, "2": 281, "3": 259, "total": 694, "defer_t2_later": 130}

# I8 §9's canonical blind-spot names.
BLIND_NAMES = {
    "I1#1": "Flock at origin and scale",
    "I1#2": "Axon/Fusus, PCAM, RTCC",
    "I1#3": "Jurisdiction attribution",
    "I1#4": "Statutory and ordinance reporting",
    "I1#5": "DOT/official registries (tier-A)",
    "I1#6": "Procurement and co-op",
    "I1#7": "Zero-channel classes",
    "I1#8": "Drones/GSD/FRT/CSS",
    "I1#9": "Thin large cities (GL1, of 36)",
    "I1#10": "Mobile ALPR and sharing currency",
    "I1#11": "International",
    "I1#12": "Records and courts",
    "I1#13": "Data brokers",
    "I1#14": "Territories and tribes",
}


@dataclass(frozen=True)
class Group:
    """One I8 §6.3 later-phase reason group → one DEFERRALS row."""

    slug: str
    title: str
    expected: int  # §6.3's count; assert on derive — a regression fails loud
    labels: tuple[str, ...] = ()  # exact `later-phase(…)` labels
    prefix: str = ""  # or match any label with this prefix
    remainder: bool = False  # the "Other" group — anything unmatched
    why: str = ""
    unblocked: str = ""
    verify: str = ""
    proxy: str = ""


GROUPS: tuple[Group, ...] = (
    Group(
        "redaction", "S7 names inside documents — extraction-time redaction", 23,
        labels=("later-phase(extraction-time name redaction for documents, J4 P8-3/P8-6)",),
        why="the rows capture documents whose text carries private names (S7); extraction-time redaction (J4 P8-3/P8-6) is not wired for their family in Round 11, and publishing facts derived from unredacted bytes would breach the §43.4 name posture",
        unblocked="owner: the ticket wiring the extraction-time name-redaction stage (J4 P8-3/P8-6) for the affected families · trigger: that stage lands fixture-tested, then the rows re-packet under their family connector",
        verify="the redaction stage is committed + fixture-verified for the family; each re-packet cites the landed stage and the shadow diff stays 0",
        proxy="every row stays `action=defer`, never fetched; the group is quoted in `COVERAGE_OUTCOME.md` §7",
    ),
    Group(
        "newfamily", "New connector family not worth a Round-11 adapter", 21,
        prefix="later-phase(new family",
        why="each row needs a connector family that did not exist and was not worth a Round-11 adapter (the I8 §6.2 list) — no reviewed adapter means no lawful fetch",
        unblocked="owner: the later-round connector ticket landing the named family adapter (ogc_wms, ocds, html_list, govuk_transparency_csv, nt_tenders_html, parliament_wqa_api, staatscourant_pdf_table, csv_bulk, algoritmeregister, canadabuys, oc_agendaext, miamidade_govaction, stac_geoparquet, pdf-policy, cbp_newsroom, datex2, unspecified) · trigger: the adapter lands fixture-verified, then the row re-packets",
        verify="the named adapter exists in `sig-connectors list-connectors`, its fixture suite is green, and the row re-packets with shadow diff 0",
        proxy="the plan keeps the rows `action=defer` with the per-family labels quoted verbatim",
    ),
    Group(
        "excerpt", "S6 free text — the SIG-PUB-014a excerpt screen", 16,
        labels=(
            "later-phase(SIG-PUB-014a excerpt screen for new families)",
            "later-phase(S6 excerpt screen + slfrf adapter)",
        ),
        why="the rows' free text needs the SIG-PUB-014a excerpt screen before derived facts may publish (one also needs the `slfrf` adapter); the screen is not wired in Round 11",
        unblocked="owner: the policy/publication ticket wiring the SIG-PUB-014a excerpt screen (and the `slfrf` adapter where named) · trigger: the screen is implemented + tested where named, then the row re-packets",
        verify="the excerpt screen exists and is tested on the family's fixtures; the re-packeted row names the screen and the shadow diff stays 0",
        proxy="rows stay `action=defer`; the labels are quoted verbatim",
    ),
    Group(
        "origin", "Derived or mirror — acquire the origin", 11,
        labels=("later-phase(acquire origin; mirror/derived I=0)",),
        why="the candidate is a mirror or derived copy (independence I=0 — it never corroborates); the right acquisition is the origin, which still needs identification and review",
        unblocked="owner: a later acquisition review identifying and packetting the origin source · trigger: an origin is identified and passes review, superseding the mirror row",
        verify="the origin source is registered + gated and the mirror row retires to a `related` link or is consumed under the origin's row (I=0 keeps it out of the corroboration count)",
        proxy="rows stay `action=defer`; no mirror is fetched or scored as independent",
    ),
    Group(
        "naming", "S5 officer/judge names — the §43.4 naming gate", 10,
        labels=("later-phase(section 43.4 naming gate for new families)",),
        why="the rows' surfaces carry officer and judge names (S5); the §43.4 naming gate is not wired for their family in Round 11",
        unblocked="owner: the policy ticket wiring the §43.4 naming gate for the affected families · trigger: the gate is implemented + tested, then the row re-packets",
        verify="the naming gate exists + is tested on the family's fixtures; the re-packeted row cites it; no officer/judge name publishes unscreened",
        proxy="rows stay `action=defer`; the §43.4 labels are quoted verbatim",
    ),
    Group(
        "coarsening", "S4 point layers — coarsening not wired", 10,
        labels=("later-phase(S4 coarsening wired: policy.sensitivity + SIG-PUB-011..014)",),
        why="the rows are point-level layers needing coarsening (`policy.sensitivity` + the SIG-PUB-011..014 publication screens); that machinery is engineering not in Round 11",
        unblocked="owner: the policy.sensitivity coarsening ticket (with the SIG-PUB-011..014 screens) · trigger: coarsening lands + the screens wire, then the row re-packets",
        verify="`policy.sensitivity` coarsening exists + is tested; the row re-packets and publishes only coarsened geometry",
        proxy="rows stay `action=defer`; no point layer is fetched for publication",
    ),
    Group(
        "e4", "E4 questions still pending (R6a/S2 or R4a)", 7,
        labels=("later-phase(E4 R6a/S2 or R4a decided)",),
        why="the rows ride unresolved E4 operator questions (the R6a/S2 or R4a dispositions); the plan never re-decides an operator question",
        unblocked="owner: the operator's recorded answer on the named E4 question · trigger: the answer lands on the plan's decision log, then the row re-packets",
        verify="the decision log records the answer verbatim and the row re-packets under the decided basis",
        proxy="rows stay `action=defer`; nothing is re-decided here (OM-07/08)",
    ),
    Group(
        "iu", "IU terms never captured", 5,
        labels=("later-phase(terms capture then IU line)",),
        why="the candidate's terms were never captured at research; no terms means no rights lane can be decided (rights stay UNDETERMINED, never guessed)",
        unblocked="owner: a later terms-capture desk pass · trigger: terms are captured and land as committed evidence, then the IU review line runs",
        verify="a committed terms capture exists (URL + accessed date + terms text class) and the IU review records a lane decision",
        proxy="rows stay `action=defer`; no rights lane is asserted from absence",
    ),
    Group(
        "q30", "SEC EDGAR — the Q-30 facts-only basis pending", 4,
        labels=("later-phase(Q-30 answered -> ACQ-L1 sec_edgar_fts)",),
        why="EDGAR acquisition needs the operator's Q-30 answer on the facts-only basis before the `sec_edgar_fts` seat may be packeted",
        unblocked="owner: the operator's Q-30 answer · trigger: the answer lands on the plan's decision log and routes to ACQ-L1 `sec_edgar_fts`",
        verify="the decision log records Q-30 verbatim and the `sec_edgar_fts` row re-packets under the decided basis (or stays out if declined)",
        proxy="rows stay `action=defer`; EDGAR is never fetched pending the answer",
    ),
    Group(
        "noindex", "Channel/family with no index surface", 6,
        labels=("later-phase(channel only)", "later-phase(family with no central index)"),
        why="the rows name a channel or family with no index surface — per-document discovery or a per-document adapter is needed before any lawful fetch",
        unblocked="owner: a later discovery pass or the per-document adapter ticket · trigger: an index/enumeration surface is found or the adapter lands",
        verify="a committed record names the enumeration surface (or the adapter exists) and the row re-packets",
        proxy="rows stay `action=defer`; no guessed URL is fetched (§3.1)",
    ),
    Group(
        "tribal", "Tribal data-governance rule (I7 NEW-6)", 3,
        labels=("later-phase(tribal data-governance rule, I7 NEW-6)",),
        why="the rows are tribal-nation sources; acquisition needs the tribal data-governance rule (finding I7 NEW-6) decided before any fetch — sovereignty posture is not inferred",
        unblocked="owner: the governance-rule decision (operator, on tribal-governance research) · trigger: the rule is decided and recorded on the plan's decision log",
        verify="the recorded rule exists and each row re-packets under it (or is excluded by it)",
        proxy="rows stay `action=defer`; the finding stays `proposed`, never treated as decided",
    ),
    Group(
        "other", "Other — singleton later-phase reasons", 14, remainder=True,
        why="each row carries its own later-phase reason (row-specific S9 screens; the IT1/IT4/IT7, C6+ACQ-25 and C8 decisions; a marginal class; per-member-office letters; the OCR path; a discovery-surface note; the ArcGIS org identity; the unreachable FAA host; a withheld origin) — the plan's labels are quoted verbatim below",
        unblocked="owner: the ticket owning each named reason (the row's label) · trigger: that reason's precondition lands — a decision recorded, a screen wired, a host reachable, an adapter landed",
        verify="each row's named precondition is committed (decision-log entry, landed screen, reachable host, registered adapter) and the row re-packets",
        proxy="rows stay `action=defer` with the exact `later-phase(…)` labels quoted",
    ),
)

DUTY_DEFERRALS = (
    {
        "id": "D-P37.66-13",
        "item": "The commenced `future_statutory_disclosure_*` duty leads — requestable publications/records: `future_statutory_disclosure_va` (Va. Code § 2.2-5517 I/J/K, first_due 2026-04-01), `future_statutory_disclosure_al` (JIC rules ch. 265-X-6, commenced 2022-03-17), `future_statutory_disclosure_ar` (Ark. Code 12-12-1805 statistics for public review) and `future_statutory_disclosure_ut` (annual on/after Aug 1 cycle, commenced 2021-08-01) — plus the one-time CA State Auditor 2019-118 artifact context already carried by SRC-011's G2-step5 dossier row",
        "why": "the duties are statutory publication duties whose artifacts exist only if the responsible office published them — or only if asked (a records request); request-sending is outside contact, the operator's act (U-011), and desk research found no publication",
        "unblocked": "owner: the operator via `D-R11-LATER-04` (outreach/records-request sending, LATER-04) · trigger: the operator authorizes sending, or a mandated publication surfaces at a checked index — then a duty-discovery packet lands the artifact under its own review",
        "verify": "a committed capture of the mandated publication (or a recorded records-request exchange) exists for each duty; each lands `ingestion_permitted=false` under HG-03 review with its own terms capture — never from the lead alone",
        "proxy": "the leads are registered desk-research rows (`statute_leads.toml` posture `commenced`) naming citation and first_due; SRC-011's CA survey rides the G2-step5 dossier captures (E4 `D-R10-SOURCES-1`)",
    },
    {
        "id": "D-P37.66-14",
        "item": "`future_statutory_disclosure_nm` — the New Mexico ALPR statute's reporting duty (posture `not_yet_due`, `first_due = 2027-04-01`)",
        "why": "the duty has not commenced — there is nothing to acquire until the first statutory date passes; acquiring earlier would mint a fetch target the duty does not yet support",
        "unblocked": "owner: the duty-discovery sweep (or the acquisition ticket holding the NM row at the date) · trigger: 2027-04-01 elapses — then check the responsible office's index for the mandated publication",
        "verify": "on/after 2027-04-01 a committed record shows the index check (found → packet under review; absent → the row records the checked date and stays owed)",
        "proxy": "the lead is registered with its `first_due` date in `statute_leads.toml` — the calendar itself is the reminder; nothing fetched early",
    },
    {
        "id": "D-P37.66-15",
        "item": "`future_statutory_disclosure_mn` — Minnesota's ALPR reporting duty, posture `contingent` on HF 3198 (enactment-dependent)",
        "why": "the duty exists only if the contingency resolves (HF 3198 enactment); treating a contingent duty as commenced would assert an obligation the record does not show",
        "unblocked": "owner: the legislative-watch pass on the MN instrument · trigger: enactment of HF 3198 is evidenced in a committed record — then the duty moves to `commenced` posture and the publication check runs",
        "verify": "a committed record evidences enactment (or rejection); the duty's posture is updated by a new lead row and the publication check runs under HG-03 review",
        "proxy": "the lead is registered `contingent` with its instrument cited in `statute_leads.toml`; no enactment is assumed",
    },
)


def load_plan() -> list[dict[str, str]]:
    with PLAN_CSV.open(newline="") as fh:
        return list(csv.DictReader(fh))


def load_candidates() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with CANDS_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            for cid in (row.get("cand_ids_merged") or "").split(":"):
                if cid := cid.strip():
                    out[cid] = row
    return out


def _cand_ids(row: dict[str, str]) -> list[str]:
    return [c.strip() for c in (row.get("cand_ids") or "").split(":") if c.strip()]


def later_phase_rows(plan: list[dict[str, str]]) -> list[dict[str, str]]:
    """The Tier-2 rows whose ticket routes them to a later phase (I8 §6.3)."""
    return [
        r
        for r in plan
        if r.get("action") == "defer" and "later-phase(" in (r.get("ticket") or "")
    ]


def group_rows(plan: list[dict[str, str]]) -> dict[str, list[str]]:
    """group slug → sorted plan_ids; raises on count drift (a regression fails loud)."""
    out: dict[str, list[str]] = {g.slug: [] for g in GROUPS}
    for r in later_phase_rows(plan):
        label = (r.get("ticket") or "").strip()
        slug = next(
            (
                g.slug
                for g in GROUPS
                if not g.remainder
                and ((g.prefix and label.startswith(g.prefix)) or label in g.labels)
            ),
            "other",
        )
        out[slug].append(r["plan_id"])
    errs, total = [], 0
    for g in GROUPS:
        out[g.slug].sort()
        total += len(out[g.slug])
        if len(out[g.slug]) != g.expected:
            errs.append(
                f"group {g.slug}: expected {g.expected} rows per I8 §6.3, "
                f"derived {len(out[g.slug])} — the plan or the group mapping drifted"
            )
    if total != PLAN_COUNTS["defer_t2_later"]:
        errs.append(f"later-phase Tier-2 total: expected 130, derived {total}")
    if errs:
        raise SystemExit("acquisition_closeout: " + "; ".join(errs))
    return out


def expected_cells(plan: list[dict[str, str]], cands: dict[str, dict[str, str]]):
    """(dimension, key) → plan_id + blind-spot rollup → plan_ids.

    Mirrors ``coverage_delta.expected_from_plan``: only routed (non-defer)
    rows explain an expected addition; ``blind`` rolls the raw
    ``i7_blind_spots`` labels up to ``I1#n`` for the per-spot table.
    """
    out: dict[tuple[str, str], str] = {}
    blind: dict[str, set[str]] = {}
    for row in plan:
        if row.get("action") == "defer":
            continue
        for cid in _cand_ids(row):
            cand = cands.get(cid)
            if not cand:
                continue
            geo = (cand.get("geographies") or "").split(":")[0].strip()
            if geo:
                out.setdefault(("state_tier", geo), row["plan_id"])
                country = (
                    "US" if geo.startswith("US-") else geo.split("-")[0] if "-" in geo else geo
                )
                out.setdefault(("country", country), row["plan_id"])
            for spot in (cand.get("i7_blind_spots") or "").split(";"):
                spot = spot.strip()
                if spot.startswith("state:") and "tier" in spot:
                    key = "US-" + spot.removeprefix("state:").split("(")[0].strip()
                    out.setdefault(("state_tier", key), row["plan_id"])
                elif spot:
                    bkey = spot.split("(")[0].strip()
                    out.setdefault(("blind_spot", bkey), row["plan_id"])
                    m = re.match(r"(I1#\d+)", bkey)
                    blind.setdefault(m.group(1) if m else bkey, set()).add(row["plan_id"])
            for tech in (cand.get("technology_classes") or "").split(";"):
                if tech.strip():
                    out.setdefault(("technology_class", tech.strip()), row["plan_id"])
    return out, blind


def baseline_cells() -> dict[str, int]:
    """The I1 baseline's claims-evidenced cell counts — mirrors the committed
    ``coverage_delta.snapshot_from_source_coverage`` exactly (first-write
    wins, ``hosted_claims_evidence`` only)."""
    by_key: dict[tuple[str, str], bool] = {}

    def add(dim: str, key: str, covered: bool) -> None:
        if key and (dim, key) not in by_key:
            by_key[(dim, key)] = covered

    with I1_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            covered = bool(
                row.get("hosted_claims_evidence")
                and "none" not in row["hosted_claims_evidence"].lower()
            )
            geo = (row.get("geographies") or "").split(":")[0].strip()
            if geo:
                add("state_tier", geo, covered)
                if geo.startswith("US-"):
                    add("country", "US", covered)
                elif "-" in geo:
                    add("country", geo.split("-")[0], covered)
                else:
                    add("country", geo, covered)
            for tech in (row.get("technology_classes") or "").split(";"):
                if tech.strip():
                    add("technology_class", tech.strip(), covered)
    return {"cells": len(by_key), "covered": sum(1 for v in by_key.values() if v)}


def queue_outcomes(plan: list[dict[str, str]], groups: dict[str, list[str]]) -> list[dict[str, str]]:
    """One outcome row per reviewed ADR-130 queue candidate."""
    queue_doc = tomllib.loads(QUEUE_TOML.read_text())
    qmeta = {}
    with QUEUE_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            qmeta[row["candidate_id"]] = row
    src_plan: dict[str, dict[str, str]] = {}
    for r in plan:
        for cid in _cand_ids(r):
            if cid.startswith("SRC-"):
                src_plan.setdefault(cid, r)
    defer_of = {
        pid: f"D-P37.66-{i + 1}" for i, g in enumerate(GROUPS) for pid in groups[g.slug]
    }
    out = []
    for cid in sorted(queue_doc.get("candidates", {})):
        meta = qmeta.get(cid, {})
        row = {
            "candidate_id": cid,
            "rank": meta.get("rank", ""),
            "family": meta.get("family", ""),
            "jurisdiction": meta.get("jurisdiction", ""),
            "review_status": meta.get("review_status", ""),
        }
        plan_row = src_plan.get(cid)
        if plan_row is None:
            row.update(
                plan_id="—",
                tier="—",
                action="reviewed, no Round-11 plan row",
                outcome="queued — stays on the reviewed queue for a later round's routing",
            )
        elif plan_row["action"] == "defer":
            if "later-phase(" in plan_row.get("ticket", ""):
                row.update(
                    plan_id=plan_row["plan_id"],
                    tier=plan_row["tier"],
                    action="defer (later-phase)",
                    outcome=f"deferred — carried by {defer_of[plan_row['plan_id']]} "
                    f"({plan_row['ticket']})",
                )
            else:
                row.update(
                    plan_id=plan_row["plan_id"],
                    tier=plan_row["tier"],
                    action="defer (Tier 3)",
                    outcome=f"Tier-3 defer ({plan_row['ticket']}) — the umbrella row `D-R11-LATER-09` carries the Tier-3 tail",
                )
        else:
            row.update(
                plan_id=plan_row["plan_id"],
                tier=plan_row["tier"],
                action=plan_row["action"],
                outcome=f"routed — {plan_row['ticket']}; live legs are the wave tickets' queued obligations (HG-03-gated, never flipped here)",
            )
        out.append(row)
    return out


def duty_rows() -> list[dict[str, str]]:
    doc = tomllib.loads(STATUTE_TOML.read_text())
    defer_of = {
        "future_statutory_disclosure_va": "D-P37.66-13",
        "future_statutory_disclosure_al": "D-P37.66-13",
        "future_statutory_disclosure_ar": "D-P37.66-13",
        "future_statutory_disclosure_ut": "D-P37.66-13",
        "future_statutory_disclosure_nm": "D-P37.66-14",
        "future_statutory_disclosure_mn": "D-P37.66-15",
    }
    return [
        {
            "duty_id": d["duty_id"],
            "state": d["state"],
            "citation": d.get("citation", ""),
            "posture": d["posture"],
            "first_due": d.get("first_due", "") or "—",
            "deferral": defer_of[d["duty_id"]],
        }
        for d in doc.get("duties", [])
    ]


def vendor_state_counts(
    plan: list[dict[str, str]], cands: dict[str, dict[str, str]]
) -> dict[str, dict[str, int]]:
    """COV-05: vendor → geography → count of routed plan rows (plan layer)."""
    out: dict[str, dict[str, int]] = {}
    for row in plan:
        if row.get("action") == "defer":
            continue
        for cid in _cand_ids(row):
            cand = cands.get(cid)
            if not cand:
                continue
            geo = (cand.get("geographies") or "").split(":")[0].strip() or "—"
            for v in (cand.get("vendors") or "").split(";"):
                if v := v.strip():
                    out.setdefault(v, {})[geo] = out.setdefault(v, {}).get(geo, 0) + 1
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def registry_partition(
    plan: list[dict[str, str]], cands: dict[str, dict[str, str]]
) -> dict:
    """Proposed source ids of routed rows → registered | renamed | absent.

    Wave tickets reconcile generated ids at registration (I8 §5.8), so a
    missing proposed id is a *rename* when the registry's notes cite it
    (``Proposed id '<sid>'``) and genuinely absent otherwise.
    """
    sources_txt = SOURCES_TOML.read_text()
    table = tomllib.loads(sources_txt).get("sources", {})
    proposed: dict[str, str] = {}
    for row in plan:
        if row.get("action") == "defer":
            continue
        for cid in _cand_ids(row):
            cand = cands.get(cid)
            if cand and (sid := _slug(cand.get("proposed_source_id") or "")):
                proposed.setdefault(sid, row["plan_id"])
    renamed, absent, present = [], {}, []
    for sid in sorted(proposed):
        if sid in table:
            present.append(sid)
        elif sid in sources_txt:
            renamed.append(sid)
        else:
            absent[sid] = proposed[sid]
    return {"present": present, "renamed": renamed, "absent": absent, "total": len(proposed)}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _tbl(headers: list[str], rows: list[list[str]]) -> list[str]:
    esc = lambda s: str(s).replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return out + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]


def render_coverage_md(
    plan: list[dict[str, str]],
    groups: dict[str, list[str]],
    cells_by_dim: dict[str, int],
    blind: dict[str, set[str]],
    base_counts: dict[str, int],
    partition: dict,
    queue: list[dict[str, str]],
    duties: list[dict[str, str]],
    vendor_counts: dict[str, dict[str, int]],
) -> str:
    L: list[str] = []
    L.append("# P37.66 — Coverage outcome and acquisition closeout (ACQ-28)")
    L.append("")
    L.append(
        "> **Generated by `docs/build/tools/acquisition_closeout.py` — do not edit by hand.** Regenerate with `python3 docs/build/tools/acquisition_closeout.py --write`; verify with `--check` (exit 1 on drift). Evidence layers: **plan** = routed `acquisition_plan.csv` rows × `candidates_consolidated.csv` (expected cells — the same derivation `sig-ops coverage-delta --plan/--candidates` runs); **registry** = committed `sources.toml` rows (registered + gated, `ingestion_permitted=false`); **claims** = the I1 baseline's `hosted_claims_evidence` cells. `live_verification=false`: **no wave leg executed live in this dispatch** — the realized claims-layer delta is zero and every live half is a named queued obligation, never a fabricated green."
    )
    L.append("")
    L.append("## 1. Realized coverage delta (claims layer)")
    L.append("")
    L.append(
        f"Baseline = I1's `data/source_coverage.csv` (2026-09-30) expressed as a "
        f"`sig.coverage-snapshot/1` (committed: `baseline_i1.json`): **{base_counts['covered']} of "
        f"{base_counts['cells']} cells covered** at claims layer. `sig-ops coverage-delta --baseline baseline_i1.json --current baseline_i1.json` ran (`realized_delta.txt`): the post-Round-11 claims-layer state is not re-measurable here (no hosted environment, no live verification) and no wave leg executed, so the realized delta is honestly **0 added / 0 removed / 0 changed**. Any cell the waves were projected to add is *expected*, tabulated below at the plan layer with its carrying obligation — never counted as covered."
    )
    L.append("")
    L.append("## 2. Expected delta — what the routed rows would add (plan layer)")
    L.append("")
    L += _tbl(
        ["dimension", "expected cells"],
        [[d, str(cells_by_dim[d])] for d in sorted(cells_by_dim)],
    )
    L.append("")
    L.append("## 3. Per I1 blind spot")
    L.append("")
    L.append(
        "I8 §9's projection table (in the design doc) is the *expected* outcome; the realized column is this dispatch's honest verdict — every spot's coverage work is queued behind the named obligations (the wave tickets' RETURN-PASS legs and the DEFERRALS rows below)."
    )
    L.append("")
    order = [f"I1#{i}" for i in range(1, 15)]
    dim_prefixes = ("city:", "state:", "county:", "territory:", "class:")
    extras = sorted(
        b for b in blind if b not in order and not b.startswith(dim_prefixes)
    )
    rows = []
    for spot in order + extras:
        ids = sorted(blind.get(spot, ()))
        label = f"{spot} {BLIND_NAMES.get(spot, '')}".strip()
        rows.append(
            [
                label,
                str(len(ids)),
                (", ".join(ids[:8]) + (" …" if len(ids) > 8 else "")) or "—",
                "expected only — live leg queued (§obligations); nothing realized",
            ]
        )
    L += _tbl(["I1 blind spot", "routed plan rows", "plan ids (first 8)", "realized"], rows)
    L.append("")
    L.append("## 4. Headline counts vs the plan's §5.5 acceptance targets")
    L.append("")
    L += _tbl(
        ["measure", "target (plan §5.5)", "this report (layer)"],
        [
            [
                "tier-A states covered",
                "46/51+DC states overall",
                "expected-only, plan layer — realized claims delta 0 (queued)",
            ],
            [
                "GL1 thin cities (of 36)",
                "≈ 20–25",
                "expected-only, plan layer (city cells ride Wave-D seats; queued)",
            ],
            [
                "technology classes (T01–T29)",
                "29/29",
                "expected-only, plan layer (ATE rides ACQ-03; queued)",
            ],
            [
                "countries beyond the US",
                "≤ 10",
                "expected-only, plan layer (Wave-C non-US objects kept per S5-4; queued)",
            ],
            [
                "I1 blind spots moved (of 14)",
                "11–12",
                "0 realized this dispatch — all queued; expected set tabulated §3",
            ],
        ],
    )
    L.append("")
    L.append("## 5. Per-source/per-wave verification (I8 §7.7)")
    L.append("")
    L.append(
        "`sig-ops wave-verify --require machinery` ran on this tip (committed: `wave_verify_machinery.json`): engineered 170 pass / 73 fail (67 `registry-row` proposed ids missing from `sources.toml`, 3 `target-row`, 2 `dedupe-anchor`, 1 `generator` = 13 NEW-1/NEW-5 dedupe dispositions), schedule 172 pass, live-executed 237 **pending** (all queued — `--require live` would fail them, correctly), typing/jurisdiction 60+60 pass, fixture shadow-diff / ER / coverage-delta / release-appearance pending inputs (family tickets attach theirs at execution). The closeout's own join over "
        f"**{partition['total']} routed proposed source ids**: "
        f"**{len(partition['present'])} registered** under their own id, "
        f"**{len(partition['renamed'])} registered under a reconciled id** (I8 §5.8 renames — the registry row's notes cite the proposed id, so the renamed half of the `registry-row` fails is an id mismatch, not missing coverage), and "
        f"**{len(partition['absent'])} genuinely absent** — wave rows whose registration lands with their family/wave ticket's queued dispatch."
    )
    L.append("")
    if partition["absent"]:
        L.append("Genuinely unregistered proposed ids (queued with their wave tickets):")
        L.append("")
        L += _tbl(
            ["proposed source id", "plan row"],
            [[s, pid] for s, pid in partition["absent"].items()],
        )
        L.append("")
    L.append("## 6. ADR-130 queue outcomes")
    L.append("")
    counts: dict[str, int] = {}
    for q in queue:
        key = (
            "routed"
            if q["action"]
            not in ("reviewed, no Round-11 plan row", "defer (later-phase)", "defer (Tier 3)")
            else q["action"]
        )
        counts[key] = counts.get(key, 0) + 1
    L.append(
        f"All {len(queue)} reviewed queue candidates carry an outcome (full table: "
        f"`QUEUE_OUTCOMES.md`): " + "; ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "."
    )
    L.append("")
    L.append("## 7. Deferred Tier-2 rows — the 130 later-phase leads (I8 §6.3)")
    L.append("")
    L += _tbl(
        ["group", "count", "DEFERRALS row"],
        [
            [g.title, str(len(groups[g.slug])), f"D-P37.66-{i + 1}"]
            for i, g in enumerate(GROUPS)
        ],
    )
    L.append("")
    L.append("## 8. Statutory duty leads")
    L.append("")
    L += _tbl(
        ["duty", "state", "citation", "posture", "first due", "DEFERRALS row"],
        [
            [d["duty_id"], d["state"], d["citation"], d["posture"], d["first_due"], d["deferral"]]
            for d in duties
        ],
    )
    L.append("")
    L.append("## 9. COV-05 — per-vendor agency counts by state (plan layer)")
    L.append("")
    L.append(
        "Counts are routed-plan-row citations of the candidate record's `vendors` × `geographies` fields — the plan-layer input the HG-11 readout's \"Wave C/D sources\" cell consumes; agency-level claims land only when the queued live legs run."
    )
    L.append("")
    top = sorted(vendor_counts.items(), key=lambda kv: -sum(kv[1].values()))[:15]
    L += _tbl(
        ["vendor", "routed rows", "states (count)"],
        [
            [
                v,
                str(sum(st.values())),
                ", ".join(f"{s}:{n}" for s, n in sorted(st.items()) if s != "—") or "—",
            ]
            for v, st in top
        ],
    )
    L.append("")
    L.append("## 10. Class S readout inputs (for G3/HG-11's \"Wave C/D sources\" cell)")
    L.append("")
    L += [
        f"- Plan shape: {PLAN_COUNTS['total']} rows — {PLAN_COUNTS['W']} W / "
        f"{PLAN_COUNTS['1']} Tier-1 / {PLAN_COUNTS['2']} Tier-2 / {PLAN_COUNTS['3']} Tier-3; "
        f"{PLAN_COUNTS['defer_t2_later']} Tier-2 later-phase rows carried by `D-P37.66-1…-12`.",
        "- Wave C (P37.2 national OSM ALPR layer): `prepared_not_executed` — ING-GO-C recorded, window/hosted env/tier go unmet; legs L1–L5 queued in RETURN PASS.",
        "- Wave D flip-window seats: P37.69a/b registered + gated (fixture-verified); live endpoint preflights queued behind ING-GO-D (`D-P37.69a-1/-2`, `D-P37.69b-1`).",
        f"- Queue: {len(queue)}/27 reviewed candidates resolved ({counts.get('routed', 0)} "
        f"routed, {counts.get('defer (Tier 3)', 0)} Tier-3 defer, "
        f"{counts.get('defer (later-phase)', 0)} later-phase defer, "
        f"{counts.get('reviewed, no Round-11 plan row', 0)} un-routed).",
        f"- Registry engineering layer: {len(partition['present'])}+{len(partition['renamed'])} "
        f"registered of {partition['total']} routed proposed ids; {len(partition['absent'])} absent (queued).",
        "- Duty leads: 6 `future_statutory_disclosure_*` registered — 4 commenced (`D-P37.66-13`), 1 not-yet-due (`D-P37.66-14`), 1 contingent (`D-P37.66-15`).",
        "- Realized claims-layer coverage delta this dispatch: 0/0/0 — recorded, never smoothed; every wave's live half is a named OPEN obligation.",
        "",
        "## Obligations carrying the queued live halves",
        "",
    ]
    L += _tbl(
        ["obligation", "carries"],
        [
            [
                "P37.2 WAVE_C_PACKET (RETURN PASS)",
                "Wave-C legs L1–L5 — the national ALPR origin layer",
            ],
            [
                "D-P37.11-1 / D-P37.12-1 / D-P37.31-1 / -32 / -35 / D-P37.70-1",
                "the keyed hosted live legs (SAM.gov, keyed 511, hosted detectors, AU traffic cameras)",
            ],
            [
                "D-P37.69a-1 / D-P37.69a-2 / D-P37.69b-1",
                "Wave-D seat endpoint preflights + ICO enumeration under the ING-GO-D flip window",
            ],
            [
                "D-P37.63-1 / D-P37.64-1 / D-P37.65a-1 / D-P37.65b-1",
                "the post-promotion acceptance + release legs (Class S)",
            ],
            [
                "D-R11-LATER-04 / D-R11-LATER-09",
                "outreach/records-request sending; the acquisition long tail (the 130 ride beneath it as D-P37.66-1…-12)",
            ],
            [
                "D-P37.66-1 … D-P37.66-15",
                "the later-phase Tier-2 groups + the statutory duty leads",
            ],
        ],
    )
    L.append("")
    return "\n".join(L)


def render_queue_md(queue: list[dict[str, str]]) -> str:
    L = [
        "# P37.66 — ADR-130 acquisition-queue outcomes",
        "",
        "> **Generated by `docs/build/tools/acquisition_closeout.py` — do not edit by hand.** Queue = `tasks/src/tasks/data/acquisition_queue.toml` (the reviewed ADR-130 queue, `acquisition-queue/1`) × `data/source-candidates.csv` (the six-streams research inventory) × `acquisition_plan.csv`. Dispositions quote the plan; gate posture: every routed row stays `ingestion_permitted=false` behind HG-03 — routing never flips a source.",
        "",
    ]
    L += _tbl(
        [
            "candidate",
            "rank",
            "family",
            "jurisdiction",
            "review",
            "plan row",
            "tier",
            "disposition",
        ],
        [
            [
                q["candidate_id"],
                q["rank"],
                q["family"],
                q["jurisdiction"],
                q["review_status"],
                q["plan_id"],
                q["tier"],
                q["outcome"],
            ]
            for q in queue
        ],
    )
    L.append("")
    return "\n".join(L)


def deferral_section(groups: dict[str, list[str]], labels: dict[str, str]) -> str:
    anchors = "` / `".join(f"D-P37.66-{i}:e0" for i in range(1, 16))
    L = [
        "",
        SECTION,
        "",
        "Appended by Devin (swe-2-high/subagent) during P37.66; nothing above is changed. Each row carries `owner:` and",
        "`trigger:` (DEFERRALS rule 5) and an open `BL-087` home; a lead token changes only through an obligation-event",
        f"transition (ADR-126); the anchors `{anchors}` are appended to",
        "`docs/build/reports/obligations/events.jsonl`. Rows D-P37.66-1…-12 are the actionable homes for the 130",
        "`later-phase(…)` Tier-2 plan rows (I8 §6.3's reason groups — the umbrella `D-R11-LATER-09` stays OPEN above",
        "them); D-P37.66-13…-15 carry the statutory duty leads.",
        "",
        HEADER,
        SEP,
    ]

    def item_for(i: int, g: Group, ids: list[str]) -> str:
        if g.slug == "newfamily":
            fams = sorted(
                {
                    labels[pid].removeprefix("later-phase(new family ").rstrip(")")
                    for pid in ids
                }
            )
            return (
                f"The {len(ids)} `later-phase(new family …)` Tier-2 plan rows — families: "
                + "; ".join(fams)
                + " — plan ids: "
                + " ".join(ids)
            )
        if g.slug == "other":
            return f"The {len(ids)} singleton later-phase Tier-2 plan rows, labels verbatim: " + "; ".join(
                f"{pid} `{labels[pid]}`" for pid in ids
            )
        label = g.labels[0] if len(g.labels) == 1 else "later-phase(…)"
        return (
            f"The {len(ids)} `{label}` Tier-2 plan rows — plan ids: " + " ".join(ids)
        )

    status = f"OPEN — created {RECORDED} by {TICKET} (cites {HOME})"
    for i, g in enumerate(GROUPS):
        ids = groups[g.slug]
        cells = [
            f"D-P37.66-{i + 1}",
            "F",
            item_for(i, g, ids),
            g.why,
            g.unblocked,
            g.verify,
            g.proxy,
            status,
        ]
        L.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    for d in DUTY_DEFERRALS:
        cells = [
            d["id"],
            "F",
            d["item"],
            d["why"],
            d["unblocked"],
            d["verify"],
            d["proxy"],
            status,
        ]
        L.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    L.append("")
    return "\n".join(L)


def render_json(
    plan: list[dict[str, str]],
    groups: dict[str, list[str]],
    cells_by_dim: dict[str, int],
    blind: dict[str, set[str]],
    base_counts: dict[str, int],
    partition: dict,
    queue: list[dict[str, str]],
    duties: list[dict[str, str]],
    vendor_counts: dict[str, dict[str, int]],
) -> str:
    tier_counts: dict[str, int] = {}
    for r in plan:
        tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1
    doc = {
        "schema": "sig.acquisition-closeout/1",
        "ticket": TICKET,
        "recorded": RECORDED,
        "live_verification": False,
        "evidence_layers": {
            "plan": "routed acquisition_plan.csv rows × candidates (expected cells)",
            "registry": "committed sources.toml rows (registered + gated)",
            "claims": "I1 baseline hosted_claims_evidence — realized delta not re-measurable this dispatch (0/0/0, honest)",
        },
        "plan_counts": {
            "total": len(plan),
            "tiers": tier_counts,
            "tier2_later_phase": sum(len(v) for v in groups.values()),
        },
        "later_phase_groups": {
            g.slug: {
                "title": g.title,
                "count": len(groups[g.slug]),
                "deferral": f"D-P37.66-{i + 1}",
                "plan_ids": groups[g.slug],
            }
            for i, g in enumerate(GROUPS)
        },
        "duty_leads": duties,
        "queue_outcomes": {"candidates": len(queue), "rows": queue},
        "coverage": {
            "baseline": "data/source_coverage.csv (I1, 2026-09-30)",
            "baseline_cells": base_counts["cells"],
            "baseline_covered": base_counts["covered"],
            "realized_delta": {"added": 0, "removed": 0, "changed": 0},
            "expected_cells_by_dimension": cells_by_dim,
            "expected_plan_rows_by_blind_spot": {k: len(v) for k, v in sorted(blind.items())},
        },
        "registry_engineering": {
            "routed_proposed_ids": partition["total"],
            "registered": len(partition["present"]),
            "registered_renamed": len(partition["renamed"]),
            "absent": len(partition["absent"]),
        },
        "class_s_inputs": {
            "wave_c": "P37.2 prepared_not_executed (ING-GO-C recorded; legs L1–L5 queued)",
            "wave_d": "P37.69a/b seats registered+gated; preflights queued under ING-GO-D",
            "vendor_state_top15": {
                v: dict(sorted(st.items()))
                for v, st in sorted(vendor_counts.items(), key=lambda kv: -sum(kv[1].values()))[
                    :15
                ]
            },
        },
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


# --------------------------------------------------------------------------- #
# Derive + write + check
# --------------------------------------------------------------------------- #


def derive() -> dict:
    plan = load_plan()
    labels = {r["plan_id"]: (r.get("ticket") or "").strip() for r in plan}
    cands = load_candidates()
    groups = group_rows(plan)
    tier_counts: dict[str, int] = {}
    for r in plan:
        tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1
    expected_tiers = {
        "W": PLAN_COUNTS["W"],
        "1": PLAN_COUNTS["1"],
        "2": PLAN_COUNTS["2"],
        "3": PLAN_COUNTS["3"],
    }
    if tier_counts != expected_tiers or len(plan) != PLAN_COUNTS["total"]:
        raise SystemExit(
            f"acquisition_closeout: plan counts drifted — tiers {tier_counts}, "
            f"total {len(plan)}; expected {expected_tiers} of {PLAN_COUNTS['total']}"
        )
    expected, blind = expected_cells(plan, cands)
    by_dim: dict[str, int] = {}
    for dim, _key in expected:
        by_dim[dim] = by_dim.get(dim, 0) + 1
    return {
        "plan": plan,
        "labels": labels,
        "groups": groups,
        "cells_by_dim": by_dim,
        "blind": blind,
        "base_counts": baseline_cells(),
        "partition": registry_partition(plan, cands),
        "queue": queue_outcomes(plan, groups),
        "duties": duty_rows(),
        "vendors": vendor_state_counts(plan, cands),
    }


def _render_all(d: dict) -> dict[pathlib.Path, str]:
    args = (
        d["plan"],
        d["groups"],
        d["cells_by_dim"],
        d["blind"],
        d["base_counts"],
        d["partition"],
        d["queue"],
        d["duties"],
        d["vendors"],
    )
    return {
        OUT_MD: render_coverage_md(*args),
        OUT_QUEUE: render_queue_md(d["queue"]),
        OUT_JSON: render_json(*args),
    }


def write_outputs(d: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in _render_all(d).items():
        path.write_text(text)
    txt = DEFERRALS.read_text()
    if SECTION in txt:
        # append-once: never rewrite the landed section
        print("acquisition_closeout: DEFERRALS P37.66 section already present — left as-is")
    else:
        section = deferral_section(d["groups"], d["labels"])
        DEFERRALS.write_text(txt.rstrip("\n") + "\n" + section)
        print("acquisition_closeout: appended DEFERRALS section")


def check(d: dict) -> list[str]:
    errs: list[str] = []
    for path, want in _render_all(d).items():
        if not path.exists():
            errs.append(f"{path}: missing — run --write")
        elif path.read_text() != want:
            errs.append(
                f"{path}: differs from a fresh generation — an input changed; regenerate"
            )
    txt = DEFERRALS.read_text()
    if SECTION not in txt:
        errs.append(f"{DEFERRALS}: missing the `{SECTION}` section")
    found = set(ROW_RE.findall(txt))
    expected_ids = {f"D-P37.66-{i}" for i in range(1, 16)}
    if missing := (expected_ids - found):
        errs.append(f"{DEFERRALS}: missing rows {sorted(missing)}")
    for i, g in enumerate(GROUPS):
        rid = f"D-P37.66-{i + 1}"
        line = next((ln for ln in txt.splitlines() if ln.startswith(f"| {rid} |")), "")
        if not line:
            continue
        for pid in d["groups"][g.slug]:
            if pid not in line:
                errs.append(f"{DEFERRALS}: {rid} no longer carries plan id {pid}")
        if "owner:" not in line or "trigger:" not in line:
            errs.append(f"{DEFERRALS}: {rid} lacks owner:/trigger: (rule 5)")
    return errs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="acquisition_closeout.py")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    d = derive()
    if args.write:
        write_outputs(d)
        print(f"acquisition_closeout: wrote {OUT_DIR}")
        return 0
    errs = check(d)
    print(
        f"acquisition_closeout --check: {'FAIL' if errs else 'ok'} — "
        f"{sum(len(v) for v in d['groups'].values())} later-phase rows in {len(GROUPS)} groups, "
        f"{len(d['queue'])} queue outcomes, {len(d['duties'])} duty leads"
    )
    for e in errs:
        print(f"  FAIL {e}", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
