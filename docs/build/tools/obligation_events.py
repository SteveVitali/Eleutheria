#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Obligation events + coverage assessments — the append-only memory-transition layer (P32.7).

ADR-126 / SIG-MEM-002: the deferral register (`docs/tickets/DEFERRALS.md`) holds
compatibility cells whose leading token is the current status; every status change is
recorded as an explicit evidence-backed **obligation-event/1** in
`docs/build/reports/obligations/events.jsonl`, and every scoped requirement verdict is a
**coverage-assessment/1** in `coverage_assessments.jsonl`. No "last token wins": an
obligation's current status is the head of a linked event chain, each link carrying its
predecessor and evidence refs. Ambiguity stays open.

Subcommands (each a plain stdlib CLI — consume, don't fork
`audit_current_state.py`, which stays the read-only inconsistency detector):

    migrate [--recorded-at YYYY-MM-DD] [--source-commit SHA]
        Create the migration anchors for every DEFERRALS obligation row plus the
        reconciled status-conflict rows (RECONCILIATIONS below) on a *fresh* log.
        The log is append-only (P34.8 / B2 §5.1, F-26): ``migrate`` REFUSES to run
        over an existing events.jsonl — it never regenerates or rewrites history.
        ``--recorded-at`` defaults to `date -u`; a future date or a date later
        than the source commit is rejected.

    append --event-json PATH [--recorded-at YYYY-MM-DD]
        Validate one obligation-event/1 record against the chain head and append
        it to events.jsonl (the shadow writer; the single-authoritative-writer
        protocol arrives at cutover — D-R10-MEMORY-1, owner P32.8). The record's
        ``recorded_at``/``observed_at`` may not be later than `date -u` nor later
        than the ``source_commit``'s committer date, and a transition's
        ``recorded_at`` may not be earlier than its predecessor's (the effective
        date, after any appended ``date-correction`` records — correction events
        themselves are excepted). ``--recorded-at`` stamps the event's
        ``recorded_at`` before validating.

    check
        Validate events.jsonl + coverage_assessments.jsonl + DEFERRALS cell
        consistency. Emits {check, severity, file, obligation, evidence, message}
        diagnostics (same shape as audit_current_state.py); exit 1 on any.

Corrections (P34.8): a ``kind: "correction"`` event is an appended annotation —
it never extends the status chain. Its ``correction`` payload names the
corrected record (``file``, ``line``, ``event_id``), the prior line's sha256 and
the source commit that authored it; a ``reason`` beginning ``date-correction``
carries ``field``, ``recorded_value`` and ``true_value`` (ADR-146: a wrong date
is corrected only by an appended, dated correction — never by rewriting the
record). Corrections of ``events.jsonl`` lines chain on the corrected event via
``expected_previous_event``; corrections of another file's lines (e.g. the
coverage ledger) carry ``expected_previous_event: null`` and ``obligation_id
"—"``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = pathlib.Path(__file__).resolve().parent
EVENTS_PATH = "docs/build/reports/obligations/events.jsonl"
ASSESSMENTS_PATH = "docs/build/reports/obligations/coverage_assessments.jsonl"
DEFERRALS_PATH = "docs/tickets/DEFERRALS.md"
SPEC_PATH = "docs/2_canonical_design_spec.md"

EVENT_SCHEMA = "obligation-event/1"
ASSESSMENT_SCHEMA = "coverage-assessment/1"
MIGRATION_TICKET = "P32.7"


def _load_audit():
    spec = importlib.util.spec_from_file_location(
        "audit_current_state", TOOLS / "audit_current_state.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


audit_current_state = _load_audit()

VALID_STATUSES = set(audit_current_state.VALID_STATUSES)
OWED_STATUSES = set(audit_current_state.OWED_STATUSES)
TERMINAL_STATUSES = set(audit_current_state.TERMINAL_STATUSES)
DEFERRAL_CELL_RE = audit_current_state.DEFERRAL_CELL_RE
DEFERRAL_XREF_RE = audit_current_state.DEFERRAL_XREF_RE
DEFERRAL_ID_RE = audit_current_state.DEFERRAL_ID_RE
BL_HOME_RE = audit_current_state.BL_HOME_RE
DATED_TERMINAL_RE = audit_current_state.DATED_TERMINAL_RE
diag = audit_current_state.diag

EVENT_KINDS = {"migration", "transition", "correction"}
DOMAINS = ("fixture", "implementation", "composed-db", "hosted", "public")
DOMAIN_RANK = {d: i for i, d in enumerate(DOMAINS)}
# The verdict grammar is check_coverage_matrix.py's (ADR-150 D1; SIG-ENG-041; SEED-15): MET ·
# MET-DIFFERENTLY(ADR-nnn|RISK-id;…) · MET-ENGINEERED(D-id;…) · PARTIAL · MISSING · AT-RISK-INTEGRATION ·
# WAIVED(ADR-nnn) · N/A-RATIONALE, with its parameters; "NA" / "N/A" are the legacy P32.7 spellings.
_ccm = audit_current_state.check_coverage_matrix
LEGACY_VERDICTS = {"NA", "N/A"}
VERDICTS = (
    set(_ccm.BASE_VERDICTS) | LEGACY_VERDICTS
)  # base words; parameters parsed per verdict_word()
MET_VERDICTS = {"MET", "MET-DIFFERENTLY"}


def verdict_word(verdict: object) -> str | None:
    """The base word of a well-formed verdict (``WAIVED(ADR-153)`` → ``WAIVED``); ``None`` if off-grammar."""
    if not isinstance(verdict, str):
        return None
    if verdict in LEGACY_VERDICTS:
        return verdict
    return _ccm.verdict_word(verdict)


# Refs that are registers/plans rather than evidence of an executed action. A
# *transition* event (status actually changed after the anchor) needs at least one
# evidence ref outside docs/tickets/ — the register itself is the claim, not proof.
REGISTER_PREFIXES = ("docs/tickets/",)
# Refs that can never establish an implementation-domain MET verdict — a planning
# document saying "will be built" or "is designed" is not built code.
PLANNING_PREFIXES = ("docs/build/planning/", "docs/tickets/")

EVENT_FIELDS = (
    "schema",
    "event_id",
    "kind",
    "obligation_id",
    "seq",
    "expected_previous_event",
    "from_status",
    "to_status",
    "ticket_id",
    "owner",
    "landing",
    "backlog_home",
    "evidence_refs",
    "observed_at",
    "recorded_at",
    "source_commit",
    "reason",
)
MIGRATION_EXTRA_FIELDS = ("anchor",)
CORRECTION_EXTRA_FIELDS = ("correction",)
# Payload of a kind="correction" event: the corrected record's location and
# provenance. `prior_line_sha256`/`source_commit` name the line the correction
# cites — for a date-correction the wrong-value-bearing line as it stands (the
# commit that wrote the wrong value); for a rewrite correction the pre-rewrite
# line and the commit that authored it (the rewrite itself is named by
# `rewrite_commit`). A `date-correction` reason requires field/recorded_value/
# true_value; a whole-record correction leaves them unset and may carry
# `fields` (the rewritten field names) and `rewrite_commit`.
CORRECTION_FIELDS = {
    "file",
    "line",
    "event_id",
    "field",
    "recorded_value",
    "true_value",
    "fields",
    "prior_line_sha256",
    "source_commit",
    "rewrite_commit",
    "register_rec",
    "note",
}
CORRECTION_REQUIRED = {"file", "line", "event_id", "prior_line_sha256", "source_commit"}
DATE_CORRECTION_PREFIX = "date-correction"
ASSESSMENT_FIELDS = (
    "schema",
    "assessment_id",
    "requirement_id",
    "verdict",
    "domain",
    "code_revision",
    "evidence_refs",
    "limitations",
    "assessor",
    "assessed_at",
    "supersedes",
    "seq",
)

# Recorded interpretations of the four P32.1 status-conflict rows (the raw parser
# status disagreed with a dated terminal token later in the same cell). Each entry
# was decided by reading the cited evidence — the raw digest stays on the anchor so
# the disagreement remains visible forever; the *choice* is recorded here, never by
# "last token wins". Rows absent from this map keep parser_status and surface as
# `events/unreconciled-conflict` (ambiguous → stays owed until a ticket records an
# interpretation).
RECONCILIATIONS: dict[str, dict] = {
    "D-P21.4-3": {
        "to_status": "DONE",
        "observed_at": "2026-09-16",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell itself records DONE 2026-09-16 — the operator decided GO at the go-public "
            "checkpoint, the GCP cut-over ran and was verified anonymously, and the "
            "custom-domain leg was skipped-by-operator (recorded, not silently dropped). "
            "Recorded interpretation: terminal DONE; the leading OPEN was stale."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/reports/PUBLICATION_CHECKLIST.md",
            "docs/build/LEDGER.md",
        ],
    },
    "D-P21.5-1": {
        "to_status": "PARTIAL",
        "observed_at": "2026-09-16",
        "owner": "operator",
        "landing": "operator action (repo-visibility decision for the SWH save-now leg; HG-07 for any future credentialed leg)",
        "reason": (
            "the dated DONE tokens are per-leg discharges — Zenodo deposit (2026-09-15), the GCS "
            "object-store push, and the live egress report — while the Software Heritage save-now "
            "leg was DECLINED-BY-OPERATOR because the repository is private and that leg reopens "
            "if visibility flips, and a non-GCS object-store push remains 'if desired'. Recorded "
            "interpretation: PARTIAL — the owed residue is an operator decision, not engineering."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/reports/DEPOSITS.md",
            "docs/build/LEDGER.md",
        ],
    },
    "D-SOURCES.2-4": {
        "to_status": "DONE",
        "observed_at": "2026-09-19",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-19 (P26.17) — RESOLVED-BY-GL-GATE-08: the operator's "
            "recorded PrimeGov/robots disposition removed the gate, so the owed ADR-083-style "
            "API-mode justification is moot. Recorded interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P26.17.md",
            "docs/build/LEDGER.md",
        ],
    },
    "D-R7.3-BREADTH": {
        "to_status": "DONE",
        "observed_at": "2026-09-26",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-26 — all eight accountability-breadth sources landed: "
            "P31.12 wired+landed the first four and P31.13 the remaining four under digest-pinned "
            "hosted jobs (+0 re-runs, rights_decision rows recorded, materialize +0). Recorded "
            "interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.12.md",
            "docs/build/runs/P31.13.md",
            "docs/build/reports/p31.13-hosted/VERIFICATION.md",
        ],
    },
    # The same defect class created after the P32.1 baseline: P32.2/P32.4/P32.5
    # appended verified DONE records to these cells without flipping the leading
    # token. Each is unambiguous (named ticket + ADR + tests in the cell itself)
    # so each gets the same recorded-interpretation treatment.
    "D-P31.1-1": {
        "to_status": "DONE",
        "observed_at": "2026-10-11",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-10-11 (P32.4 / ADR-123) — _spine_watermark now reads the "
            "trigger-maintained spine_watermark table (bounded by construction); invalidation "
            "verified for all three classes on real PG18; the p31-scale-local fixture met the "
            "named budget. Composed/hosted latency evidence is reserved to the P32.24/P33.2 e2e "
            "rows, which this closure explicitly does not claim. Recorded interpretation: DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P32.4.md",
            "docs/build/reports/p32.4-watermark/RESULTS.md",
            "docs/adr/ADR-123-shared-bitemporal-occurrence-selection.md",
        ],
    },
    "D-P31.1-3": {
        "to_status": "DONE",
        "observed_at": "2026-09-28",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-28 (P32.2, route half; ADR-121 §6) — the entity route "
            "resolves each predicate independently; unknown predicates land on an explicit "
            "unregistered_predicates field while registered facts flow through the eligibility "
            "policy. Recorded interpretation: DONE; composed/hosted verification stays P33.2's."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P32.2.md",
            "docs/adr/ADR-121-typed-assertions-and-actual-capture-bindings.md",
            "tests/api/test_api_unregistered_predicates.py",
        ],
    },
    "D-P31.5-2": {
        "to_status": "DONE",
        "observed_at": "2026-10-12",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-10-12 (P32.5 / ADR-124) — publication-eligibility/1 + the "
            "publication_disposition registry withhold publication_review_required organisations "
            "from every public surface until a recorded allow; the flag was NOT declared moot and "
            "the owed operator action is recorded in ADR-124. Recorded interpretation: DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P32.5.md",
            "docs/adr/ADR-124-one-publication-eligibility-policy.md",
            "tests/unit/test_publication_eligibility.py",
        ],
    },
    # P33.1 defect-sweep findings: eight Round-9 rows recorded verified dated
    # DONEs inside an owed-leading status cell in the `P31.x (YYYY-MM-DD): DONE`
    # word order, which the shared DATED_TERMINAL_RE could not see — so the
    # audit reported them clean and the e0 anchors preserved them as owed.
    # Each cell's DONE cites named tickets, hosted evidence and tests; each
    # interpretation is recorded here and each cell was rewritten with the old
    # value preserved verbatim (P33.1 reconciliation, 2026-10-21).
    "D-P30.1-2": {
        "to_status": "DONE",
        "observed_at": "2026-09-25",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-25 (P31.4 / HARDEN.4 / ADR-111) — memory-bounded "
            "resumable ingest with persisted per-target captures (ingest_run_capture + hosted "
            "GCS capture store); hosted kill/resume produced the identical output set (+0, same "
            "capture digests). Recorded interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.4.md",
            "tests/connectors/test_incremental_restart.py",
            "tests/db/test_resume_pg.py",
        ],
    },
    "D-P30.2a-1": {
        "to_status": "DONE",
        "observed_at": "2026-09-25",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-25 (P31.8 completing P31.5's family half; ADR-112) — "
            "all 62 unregistered measured predicates registered, 180x17 genre/directness "
            "assessed, hosted materialize +13,131 envelopes then +0, after-inventory "
            "2,623,647/2,623,647 links admissible. Recorded interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.8.md",
            "docs/build/reports/p31.8-hosted/predicate_inventory_after.json",
        ],
    },
    "D-P30.2a-2": {
        "to_status": "DONE",
        "observed_at": "2026-09-25",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-25 (P31.7; ADR-114 revisit trigger recorded) — "
            "uncapped re-sighting recording and supersession landed; hosted +232,096 links at "
            "43% of the 15 GB disk projection, under the 50% trigger. Recorded interpretation: "
            "terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.7.md",
            "docs/build/reports/p31.7-hosted/VERIFICATION.md",
            "tests/db/test_resightings.py",
        ],
    },
    "D-P30.3-1": {
        "to_status": "DONE",
        "observed_at": "2026-09-27",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-27 (P31.16 publish completing P31.2's engine half; "
            "ADR-109) — /data-freshness/ serves real last_successful_run ISO dates for all 178 "
            "sources from the appended ingest_run_completion spine. Recorded interpretation: "
            "terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.2.md",
            "docs/build/reports/REPUBLISH_LIVE_2026-09-27.md",
        ],
    },
    "D-P30.3-2": {
        "to_status": "DONE",
        "observed_at": "2026-09-27",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-27 (P31.16 publish completing P31.15's engineering "
            "half; ADR-118) — the live map draws from per-compartment pmtiles sources, "
            "/map/points.json is 404 on both origins, R8-1 recorded CLOSED. Recorded "
            "interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.15.md",
            "docs/build/reports/REPUBLISH_LIVE_2026-09-27.md",
            "docs/build/readouts/ACCEPT-R8.md",
        ],
    },
    "D-P30.3-3": {
        "to_status": "DONE",
        "observed_at": "2026-09-27",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-27 (P31.16 publish completing P31.14's engineering "
            "half; ADR-117) — the web/analytics family is live licence-separated and the public "
            "surfaces render real values with no not-recorded placeholders. Recorded "
            "interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.14.md",
            "docs/build/reports/REPUBLISH_LIVE_2026-09-27.md",
        ],
    },
    "D-P31.1-2": {
        "to_status": "DONE",
        "observed_at": "2026-09-25",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-25 (P31.4) — every sig-api job rolled by pinned "
            "digest (never :latest, before/after recorded); sig-probe swept 8/8 ok including "
            "sig-api-health. Recorded interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.4.md",
        ],
    },
    "D-P31.3-1": {
        "to_status": "DONE",
        "observed_at": "2026-09-25",
        "owner": "—",
        "landing": "—",
        "reason": (
            "the cell records DONE 2026-09-25 (P31.4; ADR-111) — sig-sink-bench on the rolled "
            "image through the live gate: 179,882 claims/min, re-run +0, 0 duplicate digests; "
            "the later OSM-replay observation point is tracked separately under OPEN "
            "D-P31.4-1. Recorded interpretation: terminal DONE."
        ),
        "evidence_refs": [
            "docs/tickets/DEFERRALS.md",
            "docs/build/runs/P31.4.md",
        ],
    },
}

KIND_DEFAULT_OWNERS = {
    "P": "operator",
    "V": "engineering",
    "F": "engineering",
    "D": "engineering",
    "H": "engineering (chain seam)",
    "X": "maintainer",
    "E": "engineering",
}

OWNER_RE = re.compile(
    r"owners?\s+((?:P\d+\.\d+[a-z]?|P\d+|HUMAN-H\d+|GATE-[\w-]+)"
    r"(?:\s*(?:→|/|–|,|\+)\s*"
    r"(?:P\d+\.\d+[a-z]?|HUMAN-H\d+|GATE-[\w-]+|\d+[a-z]?))*)",
    re.I,
)
CHAIN_ID_RE = re.compile(r"\b(P\d+\.\d+[a-z]?|HUMAN-H\d+|GATE-[A-Za-z0-9]+)\b")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_head(root: pathlib.Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "—"


def parse_obligation_rows(root: pathlib.Path) -> list[dict]:
    """Parse DEFERRALS obligation rows (same conventions as audit_current_state)."""
    path = root / DEFERRALS_PATH
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if DEFERRAL_XREF_RE.match(line):
            continue  # cross-reference/sweep rows are not obligation rows
        m = DEFERRAL_CELL_RE.match(line)
        if not m:
            continue
        oid = m.group(1).rstrip("`*.,;:)")
        if not DEFERRAL_ID_RE.match(oid):
            continue
        cells = [c.strip() for c in line.split("|")]
        # layout: | id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        n = len(cells)
        # Cells can carry literal '|' (unescaped, inside code spans), so n > 8 is
        # possible. The status cell is always the LAST content cell (the audit's
        # own convention); positional overflow is absorbed into `item`, the
        # free-text column most likely to hold the stray pipes.
        if n >= 8:
            kind = cells[1]
            item = "|".join(cells[2 : n - 5]).strip()
            why, unblocked, verify, proxy, status_cell = (
                cells[n - 5],
                cells[n - 4],
                cells[n - 3],
                cells[n - 2],
                cells[n - 1],
            )
        else:
            status_cell = cells[n - 1] if n else ""
            cells += [""] * (8 - n)
            kind, item, why = cells[1], cells[2], cells[3]
            unblocked, verify, proxy = cells[4], cells[5], cells[6]
        words = status_cell.split()
        rows.append(
            {
                "id": oid,
                "line": lineno,
                "raw_line": line,
                "kind": kind,
                "item": item,
                "why": why,
                "unblocked_by": unblocked,
                "verify": verify,
                "proxy": proxy,
                "status_cell": status_cell,
                "status": words[0].upper() if words else "",
                "prose_terminal": (
                    DATED_TERMINAL_RE.search(status_cell).group(0)
                    if DATED_TERMINAL_RE.search(status_cell)
                    else None
                ),
            }
        )
    return rows


def parse_sweep_tables(lines: list[str]) -> dict[str, dict]:
    """Owner/landing per obligation from the '| id|row | status | owner | … | landing |'
    sweep tables. Later tables win (they are dated sweeps)."""
    out: dict[str, dict] = {}
    in_sweep = False
    for line in lines:
        if re.match(r"^\|\s*(row|id)\s*\|\s*status\s*\|\s*owner", line, re.I):
            in_sweep = True
            continue
        if not in_sweep:
            continue
        if re.match(r"^\|[\s:-]+\|", line):
            continue
        m = DEFERRAL_XREF_RE.match(line)
        if m:
            cells = [c.strip() for c in line.split("|")]
            cells = cells[1:-1] if cells and cells[0] == "" else cells
            if len(cells) >= 5:
                out[m.group(1)] = {"owner": cells[2], "landing": cells[4]}
            continue
        if not line.startswith("|"):
            in_sweep = False
    return out


def _scheduled_chain(text: str) -> str:
    ids: list[str] = []
    for tok in CHAIN_ID_RE.findall(text):
        if tok not in ids:
            ids.append(tok)
    return " → ".join(ids) if ids else ""


def _derive_owner_landing(
    row: dict, rec: dict | None, sweeps: dict[str, dict]
) -> tuple[str, str, str]:
    """Return (owner, landing, backlog_home) for the migration anchor."""
    status = (rec["to_status"] if rec else row["status"]) or ""
    bl = BL_HOME_RE.search(row["raw_line"])
    backlog_home = bl.group(0) if bl else "—"
    if status in TERMINAL_STATUSES:
        owner, landing = "—", "—"
        if rec:
            owner = rec.get("owner", owner)
            landing = rec.get("landing", landing)
        return owner, landing, backlog_home
    sweep = sweeps.get(row["id"], {})
    owner = (rec or {}).get("owner") or sweep.get("owner") or ""
    if not owner:
        om = OWNER_RE.search(row["item"])
        owner = om.group(1).strip().rstrip(".,;") if om else ""
    if not owner:
        owner = KIND_DEFAULT_OWNERS.get(row["kind"], "engineering")
    landing = (rec or {}).get("landing") or sweep.get("landing") or ""
    if not landing:
        # The row's declared "owner X → …" chain is the landing when present;
        # it outranks incidental ticket ids in the "unblocked by" cell.
        om = OWNER_RE.search(row["item"])
        if om:
            landing = _scheduled_chain(om.group(1)) or om.group(1).strip().rstrip(".,;")
    if not landing:
        # scheduled chains live in the "owner X → …" item text and the
        # "unblocked by" cell — not the status cell (whose dated history is
        # retrospective and would mislabel landings).
        landing = _scheduled_chain(row["unblocked_by"])
    if not landing:
        landing = _scheduled_chain(row["item"])
    if not landing:
        landing = backlog_home
    if landing == "—" and row["kind"] == "P":
        landing = "operator action"
    return owner, landing, backlog_home


def build_anchors(
    root: pathlib.Path, recorded_at: str, source_commit: str
) -> tuple[list[dict], list[dict]]:
    """Build the migration anchor for every DEFERRALS obligation row. Returns
    (events, diags). Deterministic: depends only on inputs + the fixed args."""
    path = root / DEFERRALS_PATH
    lines = path.read_text().splitlines() if path.is_file() else []
    sweeps = parse_sweep_tables(lines)
    events: list[dict] = []
    diags: list[dict] = []
    for row in parse_obligation_rows(root):
        oid = row["id"]
        rec = RECONCILIATIONS.get(oid)
        conflicted = bool(row["prose_terminal"]) and row["status"] in OWED_STATUSES
        if rec:
            interpretation = "reconciled"
            to_status = rec["to_status"]
            reason = rec["reason"]
            evidence_refs = list(rec["evidence_refs"])
            observed_at = rec["observed_at"]
        elif conflicted:
            interpretation = "unreconciled-conflict"
            to_status = row["status"]
            reason = (
                "raw parser status leads "
                f"{row['status']} but the cell records {row['prose_terminal']} — ambiguous, "
                "stays owed until a ticket records an interpretation (no last-token-wins)"
            )
            evidence_refs = [DEFERRALS_PATH]
            observed_at = recorded_at
        else:
            interpretation = "preserved"
            to_status = row["status"]
            reason = "migration anchor: raw cell status preserved verbatim"
            evidence_refs = [DEFERRALS_PATH]
            observed_at = recorded_at
        owner, landing, backlog_home = _derive_owner_landing(row, rec, sweeps)
        events.append(
            {
                "schema": EVENT_SCHEMA,
                "event_id": f"{oid}:e0",
                "kind": "migration",
                "obligation_id": oid,
                "seq": 0,
                "expected_previous_event": None,
                "from_status": row["status"],
                "to_status": to_status,
                "ticket_id": MIGRATION_TICKET,
                "owner": owner,
                "landing": landing,
                "backlog_home": backlog_home,
                "evidence_refs": evidence_refs,
                "observed_at": observed_at,
                "recorded_at": recorded_at,
                "source_commit": source_commit,
                "reason": reason,
                "anchor": {
                    "row_line": row["line"],
                    "row_sha256": _sha256_text(row["raw_line"]),
                    "parser_status": row["status"],
                    "prose_terminal": row["prose_terminal"],
                    "interpretation": interpretation,
                },
            }
        )
        if interpretation == "unreconciled-conflict":
            diags.append(
                diag(
                    "events/unreconciled-conflict",
                    "conflict",
                    DEFERRALS_PATH,
                    oid,
                    f"line {row['line']}",
                    f"{oid}: leading {row['status']} vs {row['prose_terminal']} — no recorded "
                    "reconciliation; status stays owed with an owner",
                )
            )
    return events, diags


def load_jsonl(path: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Parse a jsonl file; returns (objects, parse-error messages)."""
    objs: list[dict] = []
    errs: list[str] = []
    if not path.is_file():
        return objs, errs
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            objs.append(json.loads(line))
        except json.JSONDecodeError as e:
            errs.append(f"line {i}: {e}")
    return objs, errs


def _ref_exists(root: pathlib.Path, ref: str) -> bool:
    return (root / ref.split("#", 1)[0]).exists()


# `docs/build/logs/` is the one gitignored subtree (ADR-073): a ref into it
# existed on the writer's machine when the record appended but is absent on a
# fresh checkout. A missing volatile ref is a warning, never an error — the
# append-only record is the fact, not a claim the file is present now.
VOLATILE_REF_PREFIX = "docs/build/logs/"


def _ref_missing(root: pathlib.Path, ref: str) -> str | None:
    """None = resolvable; "volatile" = missing under the gitignored logs tree;
    "missing" = a committed-path ref that does not exist."""
    path = ref.split("#", 1)[0]
    if (root / path).exists():
        return None
    return "volatile" if path.startswith(VOLATILE_REF_PREFIX) else "missing"


def _validate_correction(root: pathlib.Path, ev: dict) -> list[str]:
    """Correction-payload validation (kind="correction"); shape only — target
    resolution happens in check_event_chain."""
    errs: list[str] = []
    corr = ev.get("correction")
    if not isinstance(corr, dict):
        return ["correction event missing correction{…} payload"]
    for k in corr:
        if k not in CORRECTION_FIELDS:
            errs.append(f"unknown correction field {k!r}")
    for k in CORRECTION_REQUIRED:
        if k not in corr:
            errs.append(f"correction missing field {k!r}")
    if errs:
        return errs
    if not isinstance(corr["file"], str) or not _ref_exists(root, corr["file"]):
        errs.append(f"correction file does not exist: {corr.get('file')!r}")
    if not isinstance(corr["line"], int) or corr["line"] < 1:
        errs.append("correction line must be a positive integer")
    if not isinstance(corr["event_id"], str) or not corr["event_id"]:
        errs.append("correction event_id must name the corrected record")
    if not re.fullmatch(r"[0-9a-f]{64}", str(corr["prior_line_sha256"])):
        errs.append("correction prior_line_sha256 must be a sha256 hex digest")
    if str(ev.get("reason", "")).startswith(DATE_CORRECTION_PREFIX):
        for k in ("recorded_value", "true_value"):
            if corr.get(k) in (None, ""):
                errs.append(f"date-correction requires correction.{k}")
        if corr.get("field") is not None and not isinstance(corr["field"], str):
            errs.append("date-correction correction.field must be a string")
    for k in ("fields",):
        if k in corr and not (
            isinstance(corr[k], list) and all(isinstance(f, str) for f in corr[k])
        ):
            errs.append(f"correction {k} must be a list of field names")
    epe = ev.get("expected_previous_event")
    if corr["file"] == EVENTS_PATH:
        if epe != corr["event_id"]:
            errs.append(
                "a correction of an events.jsonl record chains on the corrected "
                "event: expected_previous_event must equal correction.event_id"
            )
    elif epe is not None:
        errs.append(
            "a correction of another file's record carries expected_previous_event=null"
        )
    return errs


def _validate_event(root: pathlib.Path, ev: dict) -> tuple[list[str], list[str]]:
    """Schema-level validation; returns (errors, warnings)."""
    errs: list[str] = []
    warns: list[str] = []
    if ev.get("schema") != EVENT_SCHEMA:
        errs.append(f"schema must be {EVENT_SCHEMA!r}")
    kind = ev.get("kind")
    allowed = set(EVENT_FIELDS) | (
        set(MIGRATION_EXTRA_FIELDS)
        if kind == "migration"
        else set(CORRECTION_EXTRA_FIELDS)
        if kind == "correction"
        else set()
    )
    for k in ev:
        if k not in allowed:
            errs.append(f"unknown field {k!r}")
    for k in EVENT_FIELDS:
        if k not in ev:
            errs.append(f"missing field {k!r}")
    if errs:
        return errs, warns
    if ev["kind"] not in EVENT_KINDS:
        errs.append(f"kind {ev['kind']!r} not in {sorted(EVENT_KINDS)}")
    if not isinstance(ev["seq"], int) or ev["seq"] < 0:
        errs.append("seq must be a non-negative integer")
    for s in ("from_status", "to_status"):
        if ev[s] not in VALID_STATUSES and not (
            ev["kind"] == "correction" and ev[s] == "—"
        ):
            errs.append(f"{s} {ev[s]!r} not a valid status")
    if not isinstance(ev["evidence_refs"], list) or not ev["evidence_refs"]:
        errs.append("evidence_refs must be a non-empty list")
    else:
        for r in ev["evidence_refs"]:
            missing = "missing" if not isinstance(r, str) else _ref_missing(root, r)
            if missing == "volatile":
                warns.append(
                    f"evidence ref under the gitignored logs tree — absent on "
                    f"a fresh checkout: {r!r}"
                )
            elif missing:
                errs.append(f"evidence ref does not exist: {r!r}")
        if ev["kind"] == "transition" and all(
            r.split("#", 1)[0].startswith(REGISTER_PREFIXES) for r in ev["evidence_refs"]
        ):
            errs.append(
                "transition evidence is register-only (docs/tickets/) — a status change "
                "needs at least one ref outside the register"
            )
    for d in ("observed_at", "recorded_at"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(ev[d])):
            errs.append(f"{d} {ev[d]!r} is not a YYYY-MM-DD fixed input")
    if ev["kind"] == "migration":
        if ev["expected_previous_event"] is not None:
            errs.append("migration anchor must have expected_previous_event=null")
        anchor = ev.get("anchor")
        if not isinstance(anchor, dict) or "row_sha256" not in anchor:
            errs.append("migration event missing anchor{row_sha256}")
    elif ev["kind"] == "correction":
        errs += _validate_correction(root, ev)
    else:
        if ev["expected_previous_event"] is None:
            errs.append("transition must name expected_previous_event (chain on the anchor)")
    return errs, warns


def _corrected_dates(events: list[dict]) -> dict[tuple[str, str], str]:
    """`{(event_id, field): true_value}` from appended `date-correction` records
    targeting this ledger — a correction supersedes the recorded value for
    chain checks (ADR-146). Later corrections win."""
    out: dict[tuple[str, str], str] = {}
    for ev in events:
        if ev.get("kind") != "correction":
            continue
        corr = ev.get("correction") or {}
        if (
            corr.get("file") == EVENTS_PATH
            and str(ev.get("reason", "")).startswith(DATE_CORRECTION_PREFIX)
            and isinstance(corr.get("field"), str)
            and corr.get("true_value") is not None
            and isinstance(corr.get("event_id"), str)
        ):
            # `true_value` may carry a full ISO instant; the wire field is a date
            out[(corr["event_id"], corr["field"])] = str(corr["true_value"])[:10]
    return out


def _effective_date(ev: dict, field: str, corrected: dict[tuple[str, str], str]) -> str:
    """The recorded date of `field`, as corrected by appended date-corrections."""
    return corrected.get((str(ev.get("event_id")), field), str(ev.get(field)))


def check_event_chain(
    root: pathlib.Path,
    events: list[dict],
    assessments: list[dict] | None = None,
    raw_lines: list[str] | None = None,
) -> list[dict]:
    """Chain-level validation; returns diagnostics. `raw_lines` (the file's
    literal lines) lets a same-file correction be bound to the exact bytes it
    names."""
    diags: list[dict] = []
    rows = {r["id"]: r for r in parse_obligation_rows(root)}
    assessment_ids = (
        {a.get("assessment_id") for a in assessments} if assessments is not None else None
    )
    by_id: dict[str, dict] = {}
    by_obl: dict[str, list[dict]] = {}
    for ev in events:
        eid = ev.get("event_id", "?")
        errs, warns = _validate_event(root, ev)
        for e in errs:
            diags.append(
                diag("events/malformed", "error", EVENTS_PATH, ev.get("obligation_id", "?"), eid, e)
            )
        for w in warns:
            diags.append(
                diag(
                    "events/volatile-ref",
                    "warning",
                    EVENTS_PATH,
                    ev.get("obligation_id", "?"),
                    eid,
                    w,
                )
            )
        if eid in by_id:
            diags.append(
                diag(
                    "events/duplicate-id",
                    "error",
                    EVENTS_PATH,
                    ev.get("obligation_id", "?"),
                    eid,
                    f"event id {eid} appears twice",
                )
            )
        else:
            by_id[eid] = ev
        by_obl.setdefault(ev.get("obligation_id", "?"), []).append(ev)
        oid = ev.get("obligation_id", "?")
        if oid != "?" and oid not in rows and ev.get("kind") != "correction":
            diags.append(
                diag(
                    "events/unknown-obligation",
                    "error",
                    EVENTS_PATH,
                    oid,
                    eid,
                    f"event names obligation {oid} which has no DEFERRALS row",
                )
            )
    # corrections resolve their targets after every event is known
    for ev in events:
        if ev.get("kind") != "correction":
            continue
        corr = ev.get("correction") or {}
        eid = ev.get("event_id", "?")
        oid = ev.get("obligation_id", "?")
        target: dict | None = None
        if corr.get("file") == EVENTS_PATH:
            target = by_id.get(corr.get("event_id"))
            if raw_lines is not None:
                ln = corr.get("line")
                target_line = (
                    raw_lines[ln - 1] if isinstance(ln, int) and 1 <= ln <= len(raw_lines) else None
                )
                # a target beyond the on-disk prefix is a same-append candidate;
                # the by_id check above still binds it
                if target_line is not None:
                    try:
                        line_obj = json.loads(target_line)
                    except json.JSONDecodeError:
                        line_obj = {}
                    if line_obj.get("event_id") != corr.get("event_id"):
                        diags.append(
                            diag(
                                "events/unknown-correction-target",
                                "error",
                                EVENTS_PATH,
                                oid,
                                eid,
                                f"correction names line {ln} as {corr.get('event_id')!r} but "
                                f"that line carries {line_obj.get('event_id')!r}",
                            )
                        )
                    elif str(ev.get("reason", "")).startswith(
                        DATE_CORRECTION_PREFIX
                    ) and _sha256_text(target_line) != corr.get("prior_line_sha256"):
                        # a date-correction's prior_line_sha256 names the
                        # wrong-value-bearing line exactly as it stands
                        diags.append(
                            diag(
                                "events/stale-correction",
                                "error",
                                EVENTS_PATH,
                                oid,
                                eid,
                                f"date-correction cites prior_line_sha256 "
                                f"{str(corr.get('prior_line_sha256'))[:16]}… but line {ln} "
                                "hashes differently",
                            )
                        )
            if target is None:
                diags.append(
                    diag(
                        "events/unknown-correction-target",
                        "error",
                        EVENTS_PATH,
                        oid,
                        eid,
                        f"correction names event {corr.get('event_id')!r} which is not in "
                        "this ledger",
                    )
                )
            elif target.get("obligation_id") != oid:
                diags.append(
                    diag(
                        "events/unknown-correction-target",
                        "error",
                        EVENTS_PATH,
                        oid,
                        eid,
                        f"correction obligation_id {oid!r} does not match the corrected "
                        f"event's {target.get('obligation_id')!r}",
                    )
                )
        elif (
            corr.get("file") == ASSESSMENTS_PATH
            and assessment_ids is not None
            and corr.get("event_id") not in assessment_ids
        ):
            diags.append(
                diag(
                    "events/unknown-correction-target",
                    "error",
                    EVENTS_PATH,
                    oid,
                    eid,
                    f"correction names assessment {corr.get('event_id')!r} which is not in "
                    f"{ASSESSMENTS_PATH}",
                )
            )
        if (
            target is not None
            and isinstance(corr.get("field"), str)
            and corr.get("recorded_value") is not None
            and str(target.get(corr["field"])) != str(corr["recorded_value"])
        ):
            diags.append(
                diag(
                    "events/stale-correction",
                    "error",
                    EVENTS_PATH,
                    oid,
                    eid,
                    f"correction records {corr['field']}={corr['recorded_value']!r} but the "
                    f"corrected record carries {target.get(corr['field'])!r}",
                )
            )
    corrected = _corrected_dates(events)
    heads: dict[str, dict] = {}
    for oid, evs in by_obl.items():
        anchors = [e for e in evs if e.get("kind") == "migration"]
        transitions = [e for e in evs if e.get("kind") == "transition"]
        if not anchors and not transitions:
            continue  # a corrections-only group is annotation, not a chain
        if len(anchors) == 0:
            diags.append(
                diag(
                    "events/missing-anchor",
                    "error",
                    EVENTS_PATH,
                    oid,
                    "—",
                    f"{oid} has events but no migration anchor (seq 0)",
                )
            )
        if len(anchors) > 1:
            diags.append(
                diag(
                    "events/duplicate-anchor",
                    "error",
                    EVENTS_PATH,
                    oid,
                    "—",
                    f"{oid} has {len(anchors)} migration anchors — one raw digest per obligation",
                )
            )
        if any(e.get("seq") != 0 for e in anchors):
            diags.append(
                diag(
                    "events/missing-anchor",
                    "error",
                    EVENTS_PATH,
                    oid,
                    "—",
                    f"{oid} migration anchor must be seq 0",
                )
            )
        prev_claims: dict[str, list[str]] = {}
        for e in transitions:
            prev_claims.setdefault(str(e.get("expected_previous_event")), []).append(
                e.get("event_id", "?")
            )
        for prev, claimants in prev_claims.items():
            if len(claimants) > 1:
                diags.append(
                    diag(
                        "events/competing-transition",
                        "error",
                        EVENTS_PATH,
                        oid,
                        " & ".join(claimants),
                        f"{oid}: {len(claimants)} transitions both extend {prev} — "
                        "competing heads are a recorded conflict, never silently picked",
                    )
                )
        # replay the chain in seq order; each transition's expected_previous_event
        # must equal the head event id before it applies. Correction events are
        # annotations — never chain links — and are excepted from the
        # backwards-recorded_at rule (P34.8).
        ordered = sorted(evs, key=lambda e: e.get("seq") if isinstance(e.get("seq"), int) else -1)
        head: dict | None = None
        for e in ordered:
            if e.get("kind") == "migration":
                head = e
                continue
            if e.get("kind") == "correction":
                continue
            if head is None:
                diags.append(
                    diag(
                        "events/missing-predecessor",
                        "error",
                        EVENTS_PATH,
                        oid,
                        e.get("event_id", "?"),
                        f"{oid}: transition {e.get('event_id')} applies before any anchor",
                    )
                )
                continue
            if e.get("expected_previous_event") != head["event_id"]:
                diags.append(
                    diag(
                        "events/missing-predecessor",
                        "error",
                        EVENTS_PATH,
                        oid,
                        e.get("event_id", "?"),
                        f"{oid}: {e.get('event_id')} expects {e.get('expected_previous_event')} "
                        f"but the chain head is {head['event_id']}",
                    )
                )
            if e.get("seq") != head.get("seq", -1) + 1:
                diags.append(
                    diag(
                        "events/missing-predecessor",
                        "error",
                        EVENTS_PATH,
                        oid,
                        e.get("event_id", "?"),
                        f"{oid}: {e.get('event_id')} seq {e.get('seq')} does not follow "
                        f"head seq {head.get('seq')}",
                    )
                )
            else:
                prev_rec = _effective_date(head, "recorded_at", corrected)
                if str(e.get("recorded_at")) < prev_rec:
                    diags.append(
                        diag(
                            "events/backwards-recorded-at",
                            "error",
                            EVENTS_PATH,
                            oid,
                            e.get("event_id", "?"),
                            f"{oid}: {e.get('event_id')} recorded_at {e.get('recorded_at')} is "
                            f"earlier than its previous event's {prev_rec} — dates come from "
                            "`date -u` at recording, corrected only by appended "
                            "date-correction events (ADR-146)",
                        )
                    )
                head = e
        if head is not None:
            heads[oid] = head
    # every DEFERRALS obligation must have exactly one anchor; its chain head is the
    # current status and must equal the compatibility cell's leading token.
    for oid, row in rows.items():
        if oid not in by_obl:
            diags.append(
                diag(
                    "events/missing-anchor",
                    "error",
                    EVENTS_PATH,
                    oid,
                    f"DEFERRALS line {row['line']}",
                    f"{oid} has no migration anchor — every obligation carries one",
                )
            )
            continue
        head = heads.get(oid)
        if head is None:
            continue
        if head["to_status"] != row["status"]:
            diags.append(
                diag(
                    "events/cell-divergence",
                    "error",
                    EVENTS_PATH,
                    oid,
                    f"DEFERRALS line {row['line']}",
                    f"{oid}: event head says {head['to_status']} but the compatibility cell "
                    f"leads {row['status']} — update the cell only with matching transition "
                    "evidence, never silently",
                )
            )
        if head["to_status"] in OWED_STATUSES:
            if not head.get("owner") or head["owner"] == "—":
                diags.append(
                    diag(
                        "events/owed-without-owner",
                        "error",
                        EVENTS_PATH,
                        oid,
                        head["event_id"],
                        f"{oid} is owed ({head['to_status']}) but records no owner",
                    )
                )
            if not head.get("landing") or head["landing"] == "—":
                diags.append(
                    diag(
                        "events/owed-without-landing",
                        "error",
                        EVENTS_PATH,
                        oid,
                        head["event_id"],
                        f"{oid} is owed ({head['to_status']}) but records no landing",
                    )
                )
        anchor = next((e for e in by_obl[oid] if e.get("kind") == "migration"), None)
        if anchor and anchor.get("anchor", {}).get("interpretation") == "unreconciled-conflict":
            diags.append(
                diag(
                    "events/unreconciled-conflict",
                    "conflict",
                    DEFERRALS_PATH,
                    oid,
                    f"line {row['line']}",
                    f"{oid}: raw status conflict has no recorded reconciliation — stays owed "
                    "with an owner until a ticket records the interpretation",
                )
            )
    return diags


def _spec_ids(root: pathlib.Path) -> set[str]:
    spec = root / SPEC_PATH
    if not spec.is_file():
        return set()
    # letter-suffixed ids (SIG-INGEST-046b, SIG-PUB-014b) are requirement ids too (SEED-15)
    return set(re.findall(r"\bSIG-[A-Z][A-Z0-9]*-\d{3}[a-z]?\b", spec.read_text()))


def check_assessments(root: pathlib.Path, assessments: list[dict]) -> list[dict]:
    diags: list[dict] = []
    spec_ids = _spec_ids(root)
    by_id: dict[str, dict] = {}
    by_scope: dict[tuple[str, str], list[dict]] = {}
    for a in assessments:
        aid = a.get("assessment_id", "?")
        errs: list[str] = []
        if a.get("schema") != ASSESSMENT_SCHEMA:
            errs.append(f"schema must be {ASSESSMENT_SCHEMA!r}")
        for k in a:
            if k not in ASSESSMENT_FIELDS:
                errs.append(f"unknown field {k!r}")
        for k in ASSESSMENT_FIELDS:
            if k not in a:
                errs.append(f"missing field {k!r}")
        if not errs:
            if a["domain"] not in DOMAINS:
                errs.append(f"domain {a['domain']!r} not in {DOMAINS}")
            if verdict_word(a["verdict"]) is None:
                errs.append(
                    f"verdict {a['verdict']!r} is off the ADR-150 grammar ({' · '.join(sorted(VERDICTS))}, "
                    "with each word's parameters)"
                )
            if spec_ids and a["requirement_id"] not in spec_ids:
                errs.append(
                    f"requirement {a['requirement_id']!r} is not a spec id — coverage "
                    "assessments assess spec requirements"
                )
            if not isinstance(a["evidence_refs"], list) or not a["evidence_refs"]:
                errs.append("evidence_refs must be a non-empty list")
            else:
                for r in a["evidence_refs"]:
                    missing = (
                        "missing" if not isinstance(r, str) else _ref_missing(root, r)
                    )
                    if missing == "volatile":
                        diags.append(
                            diag(
                                "coverage/volatile-ref",
                                "warning",
                                ASSESSMENTS_PATH,
                                a.get("requirement_id", "?"),
                                aid,
                                f"evidence ref under the gitignored logs "
                                f"tree — absent on a fresh checkout: {r!r}",
                            )
                        )
                    elif missing:
                        errs.append(f"evidence ref does not exist: {r!r}")
                if verdict_word(a["verdict"]) in MET_VERDICTS and all(
                    r.split("#", 1)[0].startswith(PLANNING_PREFIXES) for r in a["evidence_refs"]
                ):
                    errs.append(
                        "MET/MET-DIFFERENTLY backed only by planning documents "
                        f"({PLANNING_PREFIXES}) — a new implementation requirement is "
                        "never marked MET because a plan says so"
                    )
            if not isinstance(a["seq"], int) or a["seq"] < 0:
                errs.append("seq must be a non-negative integer")
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(a["assessed_at"])):
                errs.append("assessed_at must be a YYYY-MM-DD fixed input")
        for e in errs:
            diags.append(
                diag(
                    "coverage/malformed",
                    "error",
                    ASSESSMENTS_PATH,
                    a.get("requirement_id", "?"),
                    aid,
                    e,
                )
            )
        if aid in by_id:
            diags.append(
                diag(
                    "coverage/duplicate-id",
                    "error",
                    ASSESSMENTS_PATH,
                    a.get("requirement_id", "?"),
                    aid,
                    f"assessment id {aid} appears twice",
                )
            )
        else:
            by_id[aid] = a
        by_scope.setdefault((a.get("requirement_id", "?"), a.get("domain", "?")), []).append(a)
    # supersedes links + exactly one current head per (requirement, domain)
    for (req, dom), group in by_scope.items():
        for a in group:
            s = a.get("supersedes")
            if s is not None:
                target = by_id.get(s)
                if target is None:
                    diags.append(
                        diag(
                            "coverage/missing-superseded",
                            "error",
                            ASSESSMENTS_PATH,
                            req,
                            a.get("assessment_id", "?"),
                            f"{a.get('assessment_id')} supersedes {s} which does not exist",
                        )
                    )
                else:
                    if (target["requirement_id"], target["domain"]) != (req, dom):
                        diags.append(
                            diag(
                                "coverage/missing-superseded",
                                "error",
                                ASSESSMENTS_PATH,
                                req,
                                a.get("assessment_id", "?"),
                                "supersedes must stay within the same requirement+domain scope",
                            )
                        )
                    target["superseded_by"] = a.get("assessment_id")
        current = [a for a in group if not a.get("superseded_by")]
        if len(current) > 1:
            diags.append(
                diag(
                    "coverage/competing-assessment",
                    "error",
                    ASSESSMENTS_PATH,
                    req,
                    "/".join(a.get("assessment_id", "?") for a in current),
                    f"{req}@{dom}: {len(current)} current assessments — a superseded chain "
                    "keeps one head; competing heads are a conflict",
                )
            )
    heads = {
        (a["requirement_id"], a["domain"]): a for a in by_id.values() if not a.get("superseded_by")
    }
    # domain-override: a MET head in domain D while a higher domain carries a
    # non-MET current verdict — fixture pass must never paper over a hosted failure.
    for (req, dom), a in heads.items():
        if verdict_word(a["verdict"]) not in MET_VERDICTS:
            continue
        for (req2, dom2), b in heads.items():
            if req2 != req:
                continue
            if (
                DOMAIN_RANK.get(dom2, -1) > DOMAIN_RANK.get(dom, -1)
                and verdict_word(b["verdict"]) not in MET_VERDICTS
            ):
                diags.append(
                    diag(
                        "coverage/domain-override",
                        "error",
                        ASSESSMENTS_PATH,
                        req,
                        a.get("assessment_id", "?"),
                        f"{req}: {dom} claims {a['verdict']} while {dom2} holds "
                        f"{b['verdict']} — a narrower-domain pass cannot override a "
                        "wider-domain non-MET",
                    )
                )
    for a in by_id.values():
        a.pop("superseded_by", None)
    return diags


def _utc_today() -> str:
    """`date -u +%F` — the only clock the tool reads (SIG-MEM-005 / OM-04)."""
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _commit_utc_date(root: pathlib.Path, sha: str) -> str | None:
    """UTC committer date (YYYY-MM-DD) of a commit, or None if it doesn't resolve."""
    try:
        out = subprocess.run(
            ["git", "show", "-s", "--format=%cI", sha],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return None
    return out[:10] or None


def _check_event_dates(root: pathlib.Path, ev: dict, today: str) -> list[str]:
    """Write-path date rules (B1 §5.6): no recorded/observed date later than
    `date -u` nor later than the source commit's committer date. Stored history
    is not re-judged — a wrong recorded value is corrected by an appended
    date-correction, never rewritten."""
    errs: list[str] = []
    for d in ("observed_at", "recorded_at"):
        v = str(ev.get(d, ""))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            continue  # the malformed check reports it
        if v > today:
            errs.append(
                f"{d} {v} is later than `date -u` ({today}) — a recorded date comes "
                "from the clock, never from a guessed schedule"
            )
        src = str(ev.get("source_commit", ""))
        cdate = _commit_utc_date(root, src) if src not in ("", "—") else None
        if cdate is not None and v > cdate:
            errs.append(
                f"{d} {v} is later than its source_commit's committer date {cdate} "
                f"({src[:12]}) — a record cannot observe before its evidence exists"
            )
    return errs


def migrate(
    root: pathlib.Path, recorded_at: str | None = None, source_commit: str | None = None
) -> int:
    events_path = root / EVENTS_PATH
    if events_path.exists():
        print(
            f"migrate: refused — {EVENTS_PATH} exists. The log is append-only: it is "
            "never regenerated or rewritten; history is repaired by appended "
            "correction/transition events (P34.8, B2 §5.1, F-26; ADR-146).",
            file=sys.stderr,
        )
        return 1
    recorded_at = recorded_at or _utc_today()
    source_commit = source_commit or _git_head(root)
    today = _utc_today()
    for err in _check_event_dates(
        root,
        {"recorded_at": recorded_at, "observed_at": recorded_at, "source_commit": source_commit},
        today,
    ):
        print(f"migrate: {err}", file=sys.stderr)
        return 1
    anchors, diags = build_anchors(root, recorded_at, source_commit)
    bad = [
        (ev["event_id"], e) for ev in anchors for e in _check_event_dates(root, ev, today)
    ]
    if bad:
        for eid, e in bad:
            print(f"migrate: {eid}: {e}", file=sys.stderr)
        return 1
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("w") as fh:
        for ev in anchors:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(
        f"migrate: wrote {len(anchors)} migration anchors → {EVENTS_PATH} "
        "(fresh log — the file is append-only from here; never run migrate on it again)"
    )
    for d in diags:
        print(f"  {d['severity']} {d['check']} {d['obligation']}: {d['message']}")
    return 0


def append_event(
    root: pathlib.Path, event_json: pathlib.Path, recorded_at: str | None = None
) -> int:
    events_path = root / EVENTS_PATH
    events, errs = load_jsonl(events_path)
    for e in errs:
        print(f"append: existing events.jsonl is malformed ({e})", file=sys.stderr)
        return 2
    try:
        ev = json.loads(event_json.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"append: cannot read event json: {e}", file=sys.stderr)
        return 2
    if recorded_at is not None:
        ev["recorded_at"] = recorded_at
    today = _utc_today()
    date_errs = _check_event_dates(root, ev, today)
    if date_errs:
        for e in date_errs:
            print(f"append: {e}", file=sys.stderr)
        return 1
    # corrections can name a record in the coverage ledger — resolve them
    assessments = None
    corr = ev.get("correction") or {}
    if ev.get("kind") == "correction" and corr.get("file") == ASSESSMENTS_PATH:
        assessments, _aerrs = load_jsonl(root / ASSESSMENTS_PATH)
    raw = (
        [ln for ln in events_path.read_text().splitlines() if ln.strip()]
        if events_path.is_file()
        else None
    )
    candidate = events + [ev]
    diags = check_event_chain(root, candidate, assessments, raw)
    # Block on errors — except a cell-divergence on the appended obligation
    # itself: the event is appended first and is the very evidence that backs
    # the subsequent compatibility-cell update (cells move only with matching
    # transition evidence, so they can never be updated before the event).
    blocking = [
        d
        for d in diags
        if d["severity"] == "error"
        and not (
            d["check"] == "events/cell-divergence" and d["obligation"] == ev.get("obligation_id")
        )
    ]
    if blocking:
        for d in blocking:
            print(
                f"  {d['severity']} {d['check']} {d['obligation']}: {d['message']}", file=sys.stderr
            )
        print("append: rejected — the chain must validate cleanly before append", file=sys.stderr)
        return 1
    with events_path.open("a") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"append: appended {ev['event_id']} ({ev['obligation_id']} → {ev['to_status']})")
    return 0


def check(root: pathlib.Path) -> int:
    diags: list[dict] = []
    events, errs = load_jsonl(root / EVENTS_PATH)
    _epath = root / EVENTS_PATH
    raw_event_lines = (
        [ln for ln in _epath.read_text().splitlines() if ln.strip()]
        if _epath.is_file()
        else []
    )
    _apath = root / ASSESSMENTS_PATH
    raw_assessment_lines = (
        [ln for ln in _apath.read_text().splitlines() if ln.strip()]
        if _apath.is_file()
        else []
    )
    for e in errs:
        diags.append(diag("events/malformed", "error", EVENTS_PATH, "—", "jsonl", e))
    assessments, aerrs = load_jsonl(root / ASSESSMENTS_PATH)
    for e in aerrs:
        diags.append(diag("coverage/malformed", "error", ASSESSMENTS_PATH, "—", "jsonl", e))
    diags += check_event_chain(root, events, assessments, raw_event_lines)
    diags += check_assessments(root, assessments)
    # G11 (P34.9): the jsonl lines are the candidates; parsed records are what
    # was evaluated. Lines offered and nothing parsed → vacuous, exit 3.
    candidates = len(raw_event_lines) + len(raw_assessment_lines)
    evaluated = len(events) + len(assessments)
    if candidates > 0 and evaluated == 0:
        print(
            f"check: VACUOUS — {candidates} record line(s) offered, 0 parsed "
            "(G11, exit 3)",
            file=sys.stderr,
        )
        return 3
    if not diags:
        print(
            f"check: green — {len(events)} events ({sum(1 for e in events if e.get('kind') == 'transition')} transitions), "
            f"{len(assessments)} coverage assessments, chains and cells consistent "
            f"(candidates {candidates}, evaluated {evaluated})"
        )
        return 0
    for d in diags:
        print(f"{d['severity']:8} {d['check']:34} {d['obligation']:20} {d['message']}")
    errors = [d for d in diags if d["severity"] == "error"]
    if not errors:
        print(
            f"check: green — {len(diags)} warning(s), "
            f"{len(events)} events, {len(assessments)} assessments "
            f"(candidates {candidates}, evaluated {evaluated})"
        )
        return 0
    print(
        f"check: {len(errors)} error(s), {len(diags) - len(errors)} warning(s) "
        f"(candidates {candidates}, evaluated {evaluated})",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    mig = sub.add_parser(
        "migrate",
        help="create the initial migration anchors (refuses an existing log — append-only)",
    )
    mig.add_argument(
        "--recorded-at",
        default=None,
        help="YYYY-MM-DD; defaults to `date -u`",
    )
    mig.add_argument("--source-commit", default=None)
    app = sub.add_parser(
        "append", help="validate + append an event (transition or correction)"
    )
    app.add_argument("--event-json", required=True, type=pathlib.Path)
    app.add_argument(
        "--recorded-at",
        default=None,
        help="stamp the event's recorded_at (YYYY-MM-DD; default: the event's own)",
    )
    sub.add_parser("check", help="validate events + assessments + cells")
    args = ap.parse_args(argv)
    if args.cmd == "migrate":
        return migrate(ROOT, args.recorded_at, args.source_commit)
    if args.cmd == "append":
        return append_event(ROOT, args.event_json, args.recorded_at)
    if args.cmd == "check":
        return check(ROOT)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
