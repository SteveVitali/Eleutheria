#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Consistency checker for ``docs/build/COVERAGE_MATRIX.csv``.

P19.2 deliverable; the Round-11 verdict grammar and cross-checks are SEED-15's (Stage B, T4) under
ADR-150 and SIG-ENG-041 ("verdict integrity"). Stdlib only, Python 3.9+, runs in about a second::

    python3 docs/build/tools/check_coverage_matrix.py [docs/build/COVERAGE_MATRIX.csv]

The repo root is derived from the CSV path (``<root>/docs/build/COVERAGE_MATRIX.csv``) or given with
``--root``. Every input lives under that root: the canonical spec, the manifest, ``BUILD_INDEX.md``,
``BACKLOG.csv``, ``DEFERRALS.md``, ``docs/adr/`` and the risk register.

**Structure.** The header is the twelve P19.2 columns plus the four the build-memory 0.5.0 template appends
(``required_domain, achieved_domain, owed_legs, accepted_scope``). There is exactly one row per
requirement id the canonical spec defines — the expected count is **derived from the spec**, never pinned
(SIG-ENG-041) — with no duplicates; ``level`` and ``class`` hold enum values; the domain columns hold
``fixture < implementation < composed-db < hosted < public`` with an optional ``+human`` flag (ADR-150 D2).

**Verdict grammar** (ADR-150 D1)::

    MET · MET-DIFFERENTLY(ADR-nnn|RISK-id;…) · MET-ENGINEERED(D-id;…) · PARTIAL · MISSING ·
    AT-RISK-INTEGRATION · WAIVED(ADR-nnn) · N/A-RATIONALE

A bare ``MET-DIFFERENTLY`` is the legacy boilerplate form (F2b): it is accepted only while the row is
routed to a chain row that has not landed — the row-by-row re-verdict owner (P34.48 in Round 11).

**Routing grammar:** ``—`` · ``accepted`` · a chain row of the manifest (letter suffixes allowed, e.g.
``P34.42a``) · a legacy scoped route (``P19.4:S``) · ``BL-nnn`` (a BACKLOG row) · ``SEED-nn`` (a seed unit).

**Cross-checks** (ADR-150 D3–D7; SIG-ENG-041):

* every verdict except MET and N/A-RATIONALE is routed (non-``—``);
* an *open* verdict (PARTIAL, MISSING, AT-RISK-INTEGRATION, MET-ENGINEERED, bare MET-DIFFERENTLY) never
  routes to a landed chain row, a closed or accepted BACKLOG row, or ``accepted``;
* MET-DIFFERENTLY(ADR-nnn) cites an existing, accepted ADR that names the id; (RISK-id) a risk-register
  row that names the id;
* MET-ENGINEERED(D…) equals the row's ``owed_legs`` and every leg is an OPEN/PARTIAL DEFERRALS row;
* WAIVED(ADR-nnn) cites an existing, accepted ADR that names the id and carries a ``## Revisit trigger``;
  the row has an ``accepted_scope`` naming that ADR and no open owed leg;
* **an amendment that weakens a MUST is a waiver:** every id the spec's waiver table records
  (``### … Waivers adopted …``; G.7.2 in Round 11) is ``WAIVED(<that ADR>)`` here, and every WAIVED row
  is recorded there — no silent waiver, no unrecorded one;
* MET / MET-DIFFERENTLY carry no open owed leg, no ``accepted_scope`` (a scoped acceptance never raises a
  verdict, ADR-150 D6) and never an ``achieved_domain`` below ``required_domain``;
* MET / MET-DIFFERENTLY rows have evidence, and every cited evidence path exists.

Prints the items offered and evaluated (SIG-ENG-042) and fails when the spec defines no ids or the matrix
has no rows (no vacuous pass). Exit 0 on success, 1 on any problem, 2 on a usage or input error.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys

LEGACY_HEADER = [
    "id",
    "level",
    "spec_section",
    "class",
    "verdict",
    "evidence",
    "owning_tickets",
    "tests",
    "adrs",
    "risk_rows",
    "routing",
    "note",
]
# build-memory 0.5.0 template columns (SK-19; ADR-150 D2): appended, never renamed.
DOMAIN_COLUMNS = ["required_domain", "achieved_domain", "owed_legs", "accepted_scope"]
HEADER = LEGACY_HEADER + DOMAIN_COLUMNS

LEVELS = {"MUST", "SHOULD", "MAY", "RATIONALE"}
CLASSES = {
    "covered+tested",
    "covered+untested",
    "deferred(RISK)",
    "deviated(ADR)",
    "rationale-only",
    "process/governance",
    "unreferenced",
}
DOMAINS = ("fixture", "implementation", "composed-db", "hosted", "public")
DOMAIN_RANK = {d: i for i, d in enumerate(DOMAINS)}
HUMAN_FLAG = "+human"

BASE_VERDICTS = (
    "MET",
    "MET-DIFFERENTLY",
    "MET-ENGINEERED",
    "PARTIAL",
    "MISSING",
    "AT-RISK-INTEGRATION",
    "WAIVED",
    "N/A-RATIONALE",
)
_PLAIN = {"MET", "PARTIAL", "MISSING", "AT-RISK-INTEGRATION", "N/A-RATIONALE"}
ADR_ID_RE = re.compile(r"^ADR-\d{3}$")
RISK_ID_RE = re.compile(r"^RISK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+$")
# The DEFERRALS id grammar audit_current_state.py uses (D-<scope>-<n>, dotted scopes allowed).
DEFERRAL_ID_RE = re.compile(r"^D-[A-Z0-9][A-Za-z0-9]*(\.[A-Za-z0-9]+)*(-[A-Za-z0-9]+)+$")
_VERDICT_RE = re.compile(r"^([A-Z][A-Z/-]*[A-Z])(?:\(([^()]*)\))?$")


def parse_verdict(verdict: str) -> tuple[str, tuple[str, ...]] | None:
    """Parse a verdict cell into ``(word, params)``; ``None`` when it is off-grammar.

    ``params`` is empty for the plain words and for the legacy bare ``MET-DIFFERENTLY``.
    """
    m = _VERDICT_RE.match(verdict.strip()) if isinstance(verdict, str) else None
    if not m:
        return None
    word, raw = m.group(1), m.group(2)
    if word not in BASE_VERDICTS:
        return None
    if raw is None:
        if word in ("MET-ENGINEERED", "WAIVED"):
            return None  # these two always carry their parameters
        return word, ()
    params = tuple(p.strip() for p in raw.split(";"))
    if not params or any(not p for p in params) or len(set(params)) != len(params):
        return None
    if word in _PLAIN:
        return None
    if word == "MET-DIFFERENTLY" and all(ADR_ID_RE.match(p) or RISK_ID_RE.match(p) for p in params):
        return word, params
    if word == "MET-ENGINEERED" and all(DEFERRAL_ID_RE.match(p) for p in params):
        return word, params
    if word == "WAIVED" and len(params) == 1 and ADR_ID_RE.match(params[0]):
        return word, params
    return None


def verdict_word(verdict: str) -> str | None:
    """The base verdict word of a well-formed verdict (``WAIVED(ADR-153)`` → ``WAIVED``), else ``None``."""
    parsed = parse_verdict(verdict)
    return parsed[0] if parsed else None


class _VerdictSet(frozenset):
    """A set of base verdict words whose ``in`` test parses the full grammar.

    ``"WAIVED(ADR-153)" in VERDICTS`` is true; ``"WAIVED" in VERDICTS`` is false (WAIVED always names its
    ADR). Iterating yields the base words. Callers that test membership (``audit_current_state.py``, the
    SIG-MEM-004 test) therefore follow the grammar without re-implementing it.
    """

    def __contains__(self, verdict: object) -> bool:
        return isinstance(verdict, str) and verdict_word(verdict) in frozenset(self)


VERDICTS = _VerdictSet(BASE_VERDICTS)
# Verdicts that require a non-"—" routing (every gap, deviation or waiver is routed somewhere).
NON_MET_VERDICTS = _VerdictSet(
    {"MET-DIFFERENTLY", "MET-ENGINEERED", "PARTIAL", "MISSING", "AT-RISK-INTEGRATION", "WAIVED"}
)
# Open verdicts: owed work whose home must still be live (ADR-150 D3; SIG-ENG-041 "the routing of an open
# verdict MUST name a ticket that has not landed"). A bare MET-DIFFERENTLY is open until re-verdicted.
OPEN_WORDS = frozenset({"PARTIAL", "MISSING", "AT-RISK-INTEGRATION", "MET-ENGINEERED"})
MET_WORDS = frozenset({"MET", "MET-DIFFERENTLY"})

ROUTING_SENTINELS = frozenset({"—", "accepted"})
CHAIN_ROUTE_RE = re.compile(r"^P\d{2}\.\d+[a-z]?$")
SCOPED_ROUTE_RE = re.compile(r"^P\d+\.\d+:.+$")
BACKLOG_ROUTE_RE = re.compile(r"^BL-\d{3}$")
SEED_ROUTE_RE = re.compile(r"^SEED-\d{2}[a-z]?$")
ROUTING_TOKEN_RE = re.compile(
    r"^(?:—|accepted|P\d{2}\.\d+[a-z]?|P\d+\.\d+:.+|BL-\d{3}|SEED-\d{2}[a-z]?)$"
)

SCOPE_RE = re.compile(r"^(\S+)@(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?)#(\S.*)$")
ID_DEF_RE = re.compile(r"\*\*(SIG-[A-Z]+-\d+[a-z]?) \((?:MUST|SHOULD|MAY|RATIONALE)")
SIG_ID_RE = re.compile(r"SIG-[A-Z]+-\d{3}[a-z]?")
_FILE_ID_RE = re.compile(r"(?:\d{2,3}[a-z]?_)?([A-Za-z][A-Za-z0-9.-]*)__[^`|\s]*\.md")
_INDEX_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*\**([A-Za-z][A-Za-z0-9.-]*)")
_DEFERRAL_ROW_RE = re.compile(r"^\|\s*(D-[A-Z0-9][A-Za-z0-9._-]*)\s*\|")
_WAIVER_HEADING_RE = re.compile(r"^#{2,4}\s+.*Waivers adopted", re.I)
_PATHLIKE_RE = re.compile(r"^(?:[\w.\[\]-]+/)+[\w.\[\]-]+$|^[\w.-]+\.[A-Za-z0-9]{1,8}$")
OWED_STATUSES = frozenset({"OPEN", "PARTIAL"})


def spec_ids(spec_path: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    for line in spec_path.read_text().splitlines():
        ids.update(ID_DEF_RE.findall(line))
    return ids


def parse_domain(cell: str) -> tuple[int, bool] | None:
    """``(rank, human)`` for a domain cell; ``(-1, False)`` for an empty cell; ``None`` if malformed."""
    cell = cell.strip()
    if cell in ("", "—"):
        return (-1, False)
    human = cell.endswith(HUMAN_FLAG)
    base = cell[: -len(HUMAN_FLAG)] if human else cell
    if base not in DOMAIN_RANK:
        return None
    return (DOMAIN_RANK[base], human)


def split_list(cell: str) -> list[str]:
    return [p.strip() for p in cell.split(";") if p.strip() and p.strip() != "—"]


# ── context (the registers a verdict is cross-checked against) ───────────────


class Context:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.chain = self._chain_ids(root / "docs/tickets/00_MANIFEST.md")
        self.landed = self._landed_ids(root / "docs/build/BUILD_INDEX.md")
        self.backlog = self._backlog(root / "docs/build/BACKLOG.csv")
        self.deferrals = self._deferrals(root / "docs/tickets/DEFERRALS.md")
        self.adrs = self._adrs(root / "docs/adr")
        self.risk_text = self._read(root / "docs/risk_register.md")
        self.adr_text_cache: dict[str, str] = {}

    @staticmethod
    def _read(path: pathlib.Path) -> str:
        return path.read_text() if path.is_file() else ""

    @staticmethod
    def _chain_ids(path: pathlib.Path) -> set[str]:
        ids: set[str] = set()
        if not path.is_file():
            return ids
        for line in path.read_text().splitlines():
            if not re.match(r"^\|\s*\d+[a-z]?\s*\|", line):
                continue
            m = _FILE_ID_RE.search(line)
            if m:
                ids.add(m.group(1))
        return ids

    @staticmethod
    def _landed_ids(path: pathlib.Path) -> set[str]:
        ids: set[str] = set()
        if not path.is_file():
            return ids
        for line in path.read_text().splitlines():
            m = _INDEX_ROW_RE.match(line)
            if m:
                ids.add(m.group(1).rstrip(".*"))
        return ids

    @staticmethod
    def _backlog(path: pathlib.Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        with path.open(newline="") as fh:
            return {r["bl_id"]: r.get("status", "") for r in csv.DictReader(fh)}

    @staticmethod
    def _deferrals(path: pathlib.Path) -> dict[str, str]:
        """D-id → its leading status token (first word of the row's last cell; never last-token-wins)."""
        out: dict[str, str] = {}
        if not path.is_file():
            return out
        for line in path.read_text().splitlines():
            m = _DEFERRAL_ROW_RE.match(line)
            if not m:
                continue
            cells = [c.strip() for c in line.rstrip().rstrip("|").split("|")]
            words = cells[-1].split() if cells else []
            out.setdefault(m.group(1), (words[0].upper().strip("*`") if words else ""))
        return out

    @staticmethod
    def _adrs(adr_dir: pathlib.Path) -> dict[str, pathlib.Path]:
        out: dict[str, pathlib.Path] = {}
        if adr_dir.is_dir():
            for p in sorted(adr_dir.glob("ADR-*.md")):
                m = re.match(r"(ADR-\d{3})\b", p.name)
                if m:
                    out.setdefault(m.group(1), p)
        return out

    def adr_text(self, adr: str) -> str:
        if adr not in self.adr_text_cache:
            p = self.adrs.get(adr)
            self.adr_text_cache[adr] = p.read_text() if p else ""
        return self.adr_text_cache[adr]

    def adr_accepted(self, adr: str) -> bool:
        """The ADR's header status says Accepted (template ``- **Status:**`` or legacy ``- Status:``)."""
        for line in self.adr_text(adr).splitlines()[:40]:
            m = re.match(r"^\s*-\s*\**Status:?\**:?\s*(.*)$", line)
            if m:
                return m.group(1).strip().lower().startswith("accepted")
        return False


def waiver_records(spec_text: str) -> dict[str, set[str]]:
    """Requirement id → the ADRs the spec's waiver tables record for it.

    A waiver table is the first Markdown table under a heading containing "Waivers adopted" (Round 11:
    ``### G.7.2 Waivers adopted by the operator``); its second cell names the waived ids and its last cell
    the ADR. A spec amendment that removes or weakens a MUST is recorded there (plan §6.5; ADR-150 D7).
    """
    out: dict[str, set[str]] = {}
    in_section = False
    for line in spec_text.splitlines():
        if line.startswith("#"):
            in_section = bool(_WAIVER_HEADING_RE.match(line))
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= {"-", " "} or cells[0] in ("#", "Item"):
            continue
        adrs = re.findall(r"ADR-\d{3}", cells[-1])
        for rid in SIG_ID_RE.findall(cells[1]):
            out.setdefault(rid, set()).update(adrs)
    return out


def _evidence_paths(evidence: str) -> list[str]:
    paths: list[str] = []
    for part in evidence.split(";"):
        part = part.strip()
        if not part or part == "—":
            continue
        head = re.split(r"::|[:#\s]", part, maxsplit=1)[0].rstrip(".,)")
        if head.startswith("ADR-"):
            paths.append(head)
        elif _PATHLIKE_RE.match(head) and ("/" in head or "." in head):
            paths.append(head)
    return paths


def _evidence_exists(ctx: Context, ref: str) -> bool:
    if ref.startswith("ADR-"):
        m = re.match(r"ADR-\d{3}", ref)
        return bool(m) and m.group(0) in ctx.adrs
    return (ctx.root / ref).exists()


# ── the check ────────────────────────────────────────────────────────────────


def check(root: pathlib.Path, csv_path: pathlib.Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    spec_path = root / "docs/2_canonical_design_spec.md"
    if not spec_path.is_file():
        return [f"canonical spec not found at {spec_path}"], {}
    spec_text = spec_path.read_text()
    defined = spec_ids(spec_path)
    ctx = Context(root)
    waivers = waiver_records(spec_text)

    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        rows = list(reader)

    stats = {"spec_ids": len(defined), "rows": len(rows), "evaluated": 0, "evidence_refs": 0}
    if not defined:
        errors.append(
            "the canonical spec defines no requirement ids — nothing to check (SIG-ENG-042)"
        )
    if not rows:
        errors.append("the matrix has no data rows — nothing to check (SIG-ENG-042)")
    if header != HEADER:
        errors.append(f"header mismatch:\n  got {header}\n  want {HEADER}")
    if len(rows) != len(defined):
        errors.append(f"{len(rows)} data rows, but the spec defines {len(defined)} ids")

    seen: set[str] = set()
    for n, row in enumerate(rows, start=2):
        if len(row) != len(HEADER):
            errors.append(f"row {n}: has {len(row)} columns, expected {len(HEADER)}")
            continue
        r = dict(zip(HEADER, row))
        rid = r["id"]
        stats["evaluated"] += 1
        where = f"row {n} ({rid})"
        if rid in seen:
            errors.append(f"row {n}: duplicate id {rid}")
        seen.add(rid)
        if rid not in defined:
            errors.append(f"row {n}: id {rid} is not defined in the spec")
        if r["level"] not in LEVELS:
            errors.append(f"{where}: bad level {r['level']!r}")
        if r["class"] not in CLASSES:
            errors.append(f"{where}: bad class {r['class']!r}")
        parsed = parse_verdict(r["verdict"])
        if parsed is None:
            errors.append(f"{where}: verdict {r['verdict']!r} is off the ADR-150 grammar")
            continue
        word, params = parsed
        req = parse_domain(r["required_domain"])
        ach = parse_domain(r["achieved_domain"])
        if req is None:
            errors.append(f"{where}: bad required_domain {r['required_domain']!r}")
        if ach is None:
            errors.append(f"{where}: bad achieved_domain {r['achieved_domain']!r}")
        legs = split_list(r["owed_legs"])
        scopes = split_list(r["accepted_scope"])
        open_legs = []
        for leg in legs:
            if not DEFERRAL_ID_RE.match(leg):
                errors.append(f"{where}: owed leg {leg!r} is not a DEFERRALS id")
            elif leg not in ctx.deferrals:
                errors.append(f"{where}: owed leg {leg} is not a DEFERRALS row")
            elif ctx.deferrals[leg] in OWED_STATUSES:
                open_legs.append(leg)
        for scope in scopes:
            if not SCOPE_RE.match(scope):
                errors.append(f"{where}: accepted_scope {scope!r} is not <readout>@<date>#<clause>")

        # routing grammar and resolution
        routing = r["routing"].strip()
        if not ROUTING_TOKEN_RE.match(routing):
            errors.append(f"{where}: bad routing {routing!r}")
        elif CHAIN_ROUTE_RE.match(routing) and routing not in ctx.chain:
            errors.append(f"{where}: routing {routing} is not a chain row of the manifest")
        elif BACKLOG_ROUTE_RE.match(routing) and routing not in ctx.backlog:
            errors.append(f"{where}: routing {routing} is not a BACKLOG row")
        if r["verdict"] in NON_MET_VERDICTS and routing == "—":
            errors.append(f"{where}: verdict {r['verdict']} requires a non-'—' routing")
        is_open = word in OPEN_WORDS or (word == "MET-DIFFERENTLY" and not params)
        if is_open:
            if routing == "accepted":
                errors.append(
                    f"{where}: open verdict {word} routed to 'accepted' — it needs a live home"
                )
            elif CHAIN_ROUTE_RE.match(routing) and routing in ctx.landed:
                errors.append(
                    f"{where}: open verdict {word} routed to {routing}, which has landed — re-route it to "
                    "an unlanded row or an open BACKLOG row (SIG-ENG-041)"
                )
            elif BACKLOG_ROUTE_RE.match(routing) and ctx.backlog.get(routing) not in (None, "open"):
                errors.append(
                    f"{where}: open verdict {word} routed to {routing}, whose status is "
                    f"{ctx.backlog.get(routing)!r} — an open verdict homes on an open row"
                )
        if word == "MET-DIFFERENTLY" and not params and not CHAIN_ROUTE_RE.match(routing):
            errors.append(
                f"{where}: bare (legacy) MET-DIFFERENTLY must be routed to the chain row that re-verdicts "
                "it, or cite its ADR or RISK row (ADR-150 D1)"
            )

        # verdict-specific entry rules
        if word in MET_WORDS:
            if not r["evidence"].strip() or r["evidence"].strip() == "—":
                errors.append(f"{where}: verdict {word} requires non-blank evidence")
            if open_legs:
                errors.append(
                    f"{where}: {word} with open owed leg(s) {';'.join(open_legs)} (SIG-ENG-041)"
                )
            if scopes:
                errors.append(
                    f"{where}: {word} with an accepted_scope — a scoped acceptance never raises a verdict"
                )
            if req and ach and req[0] >= 0 and ach[0] >= 0:
                if ach[0] < req[0] or (req[1] and not ach[1]):
                    errors.append(
                        f"{where}: {word} with achieved_domain {r['achieved_domain']!r} below "
                        f"required_domain {r['required_domain']!r}"
                    )
            elif req and req[0] >= 0 and ach and ach[0] < 0 and word == "MET":
                errors.append(f"{where}: MET with a required_domain but no achieved_domain")
        if word == "MET-DIFFERENTLY":
            for p in params:
                if p.startswith("ADR-"):
                    if p not in ctx.adrs:
                        errors.append(
                            f"{where}: MET-DIFFERENTLY cites {p}, which has no file in docs/adr/"
                        )
                    elif not ctx.adr_accepted(p):
                        errors.append(f"{where}: MET-DIFFERENTLY cites {p}, which is not Accepted")
                    elif rid not in ctx.adr_text(p):
                        errors.append(
                            f"{where}: MET-DIFFERENTLY cites {p}, which does not name {rid}"
                        )
                else:
                    rows_ = [
                        ln
                        for ln in ctx.risk_text.splitlines()
                        if re.match(rf"^\|\s*{re.escape(p)}\b", ln)
                    ]
                    if not rows_:
                        errors.append(
                            f"{where}: MET-DIFFERENTLY cites {p}, which is not a risk-register row"
                        )
                    elif not any(rid in ln for ln in rows_):
                        errors.append(
                            f"{where}: MET-DIFFERENTLY cites {p}, whose row does not name {rid}"
                        )
        if word == "MET-ENGINEERED":
            if not legs:
                errors.append(f"{where}: MET-ENGINEERED needs owed_legs (ADR-150 D1)")
            elif set(params) != set(legs):
                errors.append(
                    f"{where}: MET-ENGINEERED parameters {';'.join(params)} != owed_legs {';'.join(legs)}"
                )
            closed = [
                leg
                for leg in legs
                if leg in ctx.deferrals and ctx.deferrals[leg] not in OWED_STATUSES
            ]
            if closed:
                errors.append(
                    f"{where}: MET-ENGINEERED leg(s) {';'.join(closed)} are no longer OPEN/PARTIAL — "
                    "re-verdict the row (MET when every leg is DONE)"
                )
        if word == "WAIVED":
            adr = params[0]
            if adr not in ctx.adrs:
                errors.append(f"{where}: WAIVED cites {adr}, which has no file in docs/adr/")
            else:
                text = ctx.adr_text(adr)
                if not ctx.adr_accepted(adr):
                    errors.append(f"{where}: WAIVED cites {adr}, which is not Accepted")
                if rid not in text:
                    errors.append(f"{where}: WAIVED cites {adr}, which does not name {rid}")
                if not re.search(r"^## Revisit trigger\s*$", text, re.M):
                    errors.append(f"{where}: WAIVED cites {adr}, which has no '## Revisit trigger'")
            if not scopes:
                errors.append(f"{where}: WAIVED needs an accepted_scope naming {adr}")
            elif not any((SCOPE_RE.match(s) or [None, ""])[1] == adr for s in scopes):
                errors.append(f"{where}: WAIVED accepted_scope does not name {adr}")
            if open_legs:
                errors.append(f"{where}: WAIVED with open owed leg(s) {';'.join(open_legs)}")
            if adr not in waivers.get(rid, set()):
                errors.append(
                    f"{where}: WAIVED({adr}) is not recorded in the spec's waiver table — every waiver of a "
                    "MUST or clause is recorded there with the operator's words (ADR-150 D7)"
                )
        if word in ("MET", "MET-DIFFERENTLY", "MET-ENGINEERED", "PARTIAL"):
            for ref in _evidence_paths(r["evidence"]):
                stats["evidence_refs"] += 1
                if not _evidence_exists(ctx, ref):
                    errors.append(f"{where}: cited evidence {ref!r} does not exist")

    missing = defined - seen
    if missing:
        errors.append(f"{len(missing)} spec ids missing from the matrix: {sorted(missing)[:10]}...")
    # an amendment that weakens a MUST is a waiver: the spec's waiver records ↔ WAIVED rows
    by_id = {row[0]: row for row in rows if row}
    for rid, adrs in sorted(waivers.items()):
        row = by_id.get(rid)
        if row is None or len(row) < 5:
            errors.append(
                f"{rid}: waived in the spec ({', '.join(sorted(adrs))}) but has no matrix row"
            )
            continue
        parsed = parse_verdict(row[4])
        if not parsed or parsed[0] != "WAIVED" or parsed[1][0] not in adrs:
            errors.append(
                f"{rid}: the spec records a waiver ({', '.join(sorted(adrs))}) but the matrix verdict is "
                f"{row[4]!r} — a weakened MUST is WAIVED(ADR), never a silent amendment"
            )
    stats["waiver_records"] = len(waivers)

    # L1 cross-check: every "nowhere-referenced" seed id must be class != covered+tested, OR carry a test
    # evidence path (SCOPING_ID_LISTS.md §L1; the list is a seed, not a verdict). Skipped if absent.
    lists_path = csv_path.parent / "SCOPING_ID_LISTS.md"
    if lists_path.exists():
        body = lists_path.read_text()
        l1_block = body.split("## L1", 1)[1].split("```", 2)[1]
        l1 = set(re.findall(r"SIG-[A-Z]+-\d+[a-z]?", l1_block))
        for rid in sorted(l1):
            row = by_id.get(rid)
            if row is None or len(row) != len(HEADER):
                errors.append(f"L1 id {rid} not in matrix")
                continue
            if row[3] == "covered+tested" and not row[7].strip("—").strip():
                errors.append(f"L1 id {rid} is covered+tested without a test evidence path")
        print(f"L1 cross-check: {len(l1)} seed ids OK")
    return errors, stats


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog=pathlib.Path(argv[0]).name if argv else "check_coverage_matrix.py"
    )
    ap.add_argument(
        "csv", nargs="?", default=None, help="COVERAGE_MATRIX.csv (default: <root>/docs/build/…)"
    )
    ap.add_argument("--root", default=None, help="repo root (default: derived from the CSV path)")
    args = ap.parse_args(argv[1:])
    if args.csv:
        csv_path = pathlib.Path(args.csv).resolve()
        root = pathlib.Path(args.root).resolve() if args.root else csv_path.parents[2]
    else:
        root = (
            pathlib.Path(args.root).resolve()
            if args.root
            else pathlib.Path(__file__).resolve().parents[3]
        )
        csv_path = root / "docs/build/COVERAGE_MATRIX.csv"
    if not csv_path.is_file():
        print(f"check_coverage_matrix: {csv_path} not found", file=sys.stderr)
        return 2
    errors, stats = check(root, csv_path)
    if stats:
        print(
            f"offered: {stats['spec_ids']} spec ids, {stats['rows']} matrix rows, "
            f"{stats.get('waiver_records', 0)} spec waiver records · evaluated: {stats['evaluated']} rows, "
            f"{stats['evidence_refs']} evidence refs"
        )
    if errors:
        print(f"FAIL: {len(errors)} problem(s):")
        for e in errors:
            print("  -", e)
        return 1
    print(f"{stats['rows']} rows OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
