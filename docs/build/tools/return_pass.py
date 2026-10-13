#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""RETURN PASS generator + check — `return-pass-map/1` (P34.29; B3 §3.13 row M5;
V6 in §6; SIG-MEM-010).

The LEDGER's ``### RETURN PASS — current`` region is a **generated region**
(``exempt`` in ``record_policy/history.policy`` — it is regenerated, never
hand-edited; every other LEDGER region only gains lines). This tool renders the
whole region — heading, membership preamble, the
``| ticket | obligations | gates / blocking domain | what the operator must do |
re-run line |`` table and the sources/provenance tail — from the committed map
``docs/build/tools/record_policy/return_pass.toml``, and renders the CURRENT
STATE ``returnPass:`` value as the sorted ticket column of that table.

Membership (B3 §3.13; the T5 γ keying the map's heading records): every owed
obligation (obligation-event head OPEN/PARTIAL) whose S1b disposition is
``live-return-pass(<unit>)`` has a row keyed by the **landed** ticket that owes
the live leg; the re-run line names the Round-11 chain row that runs it. Rows
whose return path has no ticket are keyed ``—`` (kind ``operator``) and are
excluded from ``returnPass:`` — a key is never re-dispatched. Landed Round-11
rows with queued OM-19 live legs carry ``kind = "leg"`` and a ``[[row.legs]]``
entry per queued leg (id, window earliest time + excluded hours, go id or
``pre-authorised: S5-3``, re-run line, ``live:`` dependants) — the one committed
source the orchestrator's boundary comparison and the leg-runner backstop
(OP-24, ``LEG_RUNNER_PROMPT.md``) read.

    return_pass.py generate [--root DIR]   regenerate the LEDGER region + key
    return_pass.py check    [--root DIR]   verify; exit 0 ok / 1 drift or
                                           inconsistency / 2 input error /
                                           3 vacuous (SIG-ENG-042)

``check`` enforces (B3 §3.13 item 4, V6):

* ``returnPass:`` equals the table's ticket column, sorted;
* the committed region equals the generated output **byte-for-byte**;
* every row's ``obligations`` list equals the ``D-*`` ids its obligations cell
  names, every ``kind = "leg"`` row's leg fields stay inside the row's cells,
  and no obligation appears under two rows (two homes inside the map);
* every obligation named in the map is currently owed (a landed leg must leave
  the table at the next regeneration, not linger stale);
* every owed ``live-return-pass(...)`` obligation is named by exactly one row;
* every other owed obligation sits in exactly one home — a RETURN PASS row, a
  manifest row (named in its landing/owner/unblocked-by), or a later-phase /
  wontfix / other non-ticket disposition — and an owed obligation with a
  ``ticket(<unit>)`` disposition resolves to at least one manifest row;
* the count evaluated is reported and a run over a non-empty register that
  evaluates zero obligations is vacuous (exit 3, SIG-ENG-042 shape).

Regeneration triggers (recorded here per the contract): an ``implement-spec``
close that opens or closes a live-leg deferral, an orchestrator gate skip, an
OM-19 leg queued or run, and the round's REC tail. The closing run updates this
map, runs ``generate``, and ``check`` keeps CI honest on the result.

Stdlib only (tomllib needs Python ≥ 3.11); runs in the uv-less CI ``docs`` job.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = pathlib.Path(__file__).resolve().parent
LEDGER_REL = "docs/build/LEDGER.md"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
PD = "docs/build/planning/2026-09-30-next-phase"
UNIVERSE_REL = f"{PD}/universe/UNIVERSE_DISPOSED.csv"
PLAN_REL = f"{PD}/data/round11_plan.csv"

MAP_FORMAT = "return-pass-map/1"
REGION_HEADING_RE = re.compile(r"^###\s+RETURN PASS\s+—\s+current")
HEADING_BOUNDARY_RE = re.compile(r"^#{2,3}\s")
D_ID_RE = re.compile(r"\bD-[A-Z0-9][A-Za-z0-9.\-]*\b")
CHAIN_ROW_RE = re.compile(r"\bP\d+\.\d+[a-z]?\b")
TICKET_ID_RE = re.compile(r"^P(\d+)\.(\d+)([a-z]*)$")
ISO_TOKEN_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
CLOCK_TOKEN_RE = re.compile(r"\b\d{2}:\d{2}Z?\b")
WATCH_BOUND_RE = re.compile(r"\b(owner|trigger|due):")
DISPOSITION_RE = re.compile(r"^([a-z\-]+)\((.*)\)$")
TABLE_HEADER = "| ticket | obligations | gates / blocking domain | what the operator must do | re-run line |"
TABLE_SEP = "|---|---|---|---|---|"
ROW_KINDS = {"obligation", "leg", "operator"}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _norm(text: str) -> str:
    """Cells escape literal pipes as ``\\|``; comparisons see real pipes."""
    return (text or "").replace("\\|", "|")


def ticket_sort_key(ticket: str) -> tuple:
    """Natural ticket order: P34.6 before P34.17 (phase, number, suffix)."""
    m = TICKET_ID_RE.match(ticket)
    if m:
        return (0, int(m.group(1)), int(m.group(2)), m.group(3))
    return (1, 0, 0, ticket)


# ── map ──────────────────────────────────────────────────────────────────────


def load_map(root: pathlib.Path) -> tuple[dict, list[str]]:
    """Parse the committed map; returns (data, errors)."""
    path = root / MAP_REL
    if not path.is_file():
        return {}, [f"{MAP_REL}: missing — the committed map is required"]
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        return {}, [f"{MAP_REL}: not valid TOML — {e}"]
    meta = data.get("meta") or {}
    errors: list[str] = []
    if meta.get("format") != MAP_FORMAT:
        errors.append(f"{MAP_REL}: meta.format is not {MAP_FORMAT!r}")
    for field in ("heading", "preamble", "postamble"):
        if not isinstance(meta.get(field), str) or not meta[field].strip():
            errors.append(f"{MAP_REL}: meta.{field} is missing or empty")
    return data, errors


def map_obligation_index(data: dict) -> dict[str, str]:
    """obligation id -> row key, from the map (first-wins; duplicates reported
    by validate_map)."""
    out: dict[str, str] = {}
    for row in data.get("row", []):
        for oid in row.get("obligations", []):
            out.setdefault(oid, row.get("key", "?"))
    return out


def validate_map(data: dict, manifest_ids: set[str]) -> list[str]:
    """Structural + map↔cell coherence checks that need no ledger or events."""
    errors: list[str] = []
    rows = data.get("row") or []
    if not isinstance(rows, list) or not rows:
        return errors + [f"{MAP_REL}: no [[row]] entries"]
    keys: set[str] = set()
    leg_ids: set[str] = set()
    seen_obligations: dict[str, str] = {}
    for i, row in enumerate(rows):
        key = row.get("key")
        kind = row.get("kind")
        where = f"row {i + 1} ({key!r})"
        if not isinstance(key, str) or not key:
            errors.append(f"{where}: missing key")
        elif key in keys:
            errors.append(f"{where}: duplicate key {key!r} — a key is never shared")
        keys.add(key)
        if kind not in ROW_KINDS:
            errors.append(f"{where}: kind {kind!r} not one of {sorted(ROW_KINDS)}")
        if kind == "operator" and key != "—":
            errors.append(
                f"{where}: an operator-kind row must be keyed '—' "
                "(excluded from returnPass:)"
            )
        for cell_name in ("obligations_cell", "gates_cell", "operator_cell", "rerun_cell"):
            cell = row.get(cell_name)
            if not isinstance(cell, str) or not cell.strip():
                errors.append(f"{where}: {cell_name} is missing or empty")
        obligations = row.get("obligations")
        if not isinstance(obligations, list):
            errors.append(f"{where}: obligations must be a list")
            obligations = []
        cell_ids = D_ID_RE.findall(_norm(row.get("obligations_cell", "")))
        if sorted(obligations) != sorted(cell_ids):
            errors.append(
                f"{where}: obligations {obligations} do not equal the D-* ids "
                f"the obligations cell names {cell_ids}"
            )
        for oid in obligations:
            if oid in seen_obligations:
                errors.append(
                    f"{where}: obligation {oid} is also listed by row "
                    f"{seen_obligations[oid]!r} — two homes inside the map"
                )
            else:
                seen_obligations[oid] = key
        legs = row.get("legs") or []
        if kind == "leg" and not legs:
            errors.append(f"{where}: kind 'leg' carries no [[row.legs]] entries")
        if kind != "leg" and legs:
            errors.append(f"{where}: [[row.legs]] only on kind 'leg' rows")
        gates = _norm(row.get("gates_cell", ""))
        operator = _norm(row.get("operator_cell", ""))
        rerun_cell = _norm(row.get("rerun_cell", ""))
        for leg in legs:
            lid = leg.get("id")
            lwhere = f"{where} leg {lid!r}"
            if not isinstance(lid, str) or not lid.strip():
                errors.append(f"{where}: a leg with no id")
            elif lid in leg_ids:
                errors.append(f"{lwhere}: duplicate leg id")
            else:
                leg_ids.add(lid)
            for oid in leg.get("obligations", []):
                if oid not in obligations:
                    errors.append(
                        f"{lwhere}: names obligation {oid} the row does not carry"
                    )
            earliest = (leg.get("earliest") or "").strip()
            if not earliest:
                errors.append(f"{lwhere}: window earliest time missing")
            else:
                # a machine-parseable bound must be visible in the rendered
                # row; descriptive bounds are free text.
                for tok in ISO_TOKEN_RE.findall(earliest) + CLOCK_TOKEN_RE.findall(
                    earliest
                ):
                    if tok not in gates:
                        errors.append(
                            f"{lwhere}: earliest bound {tok!r} is not in the "
                            "gates / blocking domain cell"
                        )
            excluded = leg.get("excluded")
            if not isinstance(excluded, list):
                errors.append(f"{lwhere}: excluded must be a list")
                excluded = []
            for x in excluded:
                if x not in gates:
                    errors.append(
                        f"{lwhere}: excluded-hours entry {x!r} is not in the "
                        "gates / blocking domain cell"
                    )
            go = (leg.get("go") or "").strip()
            if not go:
                errors.append(f"{lwhere}: go id missing")
            elif go.startswith("pre-authorised:"):
                ref = go.split(":", 1)[1].strip()
                if ref not in gates:
                    errors.append(
                        f"{lwhere}: go {go!r} — {ref!r} is not in the gates "
                        "cell"
                    )
            elif go.startswith("verbatim-go:"):
                if "verbatim" not in gates and "verbatim" not in operator:
                    errors.append(
                        f"{lwhere}: claims a verbatim go but no cell says "
                        "'verbatim'"
                    )
            elif go.startswith("operator:"):
                desc = go.split(":", 1)[1].strip()
                if desc and desc not in operator:
                    errors.append(
                        f"{lwhere}: operator step {desc!r} is not in the "
                        "operator cell"
                    )
            elif go.startswith("none"):
                pass  # read-only / boundary-triggered — nothing to echo
            elif go not in gates and go not in operator:
                errors.append(
                    f"{lwhere}: unrecognised go {go!r} not found in the row's "
                    "cells (use pre-authorised:, verbatim-go:, operator: or none)"
                )
            rerun = (leg.get("rerun") or "").strip()
            if not rerun:
                errors.append(f"{lwhere}: re-run line missing")
            elif not rerun.startswith("none") and _norm(rerun) not in rerun_cell:
                errors.append(
                    f"{lwhere}: re-run line {rerun!r} is not in the re-run cell"
                )
            for dep in leg.get("live_dependants", []):
                if dep not in manifest_ids:
                    errors.append(
                        f"{lwhere}: live: dependant {dep} is not a manifest "
                        "chain row"
                    )
    return errors


# ── rendering ────────────────────────────────────────────────────────────────


def render_table(data: dict) -> str:
    lines = [TABLE_HEADER, TABLE_SEP]
    for row in data.get("row", []):
        lines.append(
            "| {key} | {o} | {g} | {a} | {r} |".format(
                key=row.get("key", "?"),
                o=row.get("obligations_cell", ""),
                g=row.get("gates_cell", ""),
                a=row.get("operator_cell", ""),
                r=row.get("rerun_cell", ""),
            )
        )
    return "\n".join(lines)


def render_region(data: dict) -> str:
    """The full ``### RETURN PASS — current`` region text (trailing newline
    included; deterministic — no wall-clock)."""
    meta = data.get("meta") or {}
    parts = [
        f"### RETURN PASS — current ({meta.get('heading', '').strip()})",
        "",
        (meta.get("preamble") or "").strip("\n"),
        "",
        render_table(data),
        "",
        (meta.get("postamble") or "").strip("\n"),
        "",
    ]
    return "\n".join(parts)


def table_tickets(data: dict) -> list[str]:
    return [r["key"] for r in data.get("row", []) if r.get("kind") != "operator"]


def return_pass_value(data: dict) -> str:
    return ", ".join(sorted(table_tickets(data), key=ticket_sort_key))


# ── ledger ───────────────────────────────────────────────────────────────────


def region_span(lines: list[str]) -> tuple[int, int] | None:
    """0-based [start, end) line span of the generated region — the
    ``### RETURN PASS — current`` heading through the line before the next
    ``##``/``###`` boundary (the same span memory_guard's ``exempt`` rule
    computes)."""
    start = None
    for i, line in enumerate(lines):
        if REGION_HEADING_RE.match(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEADING_BOUNDARY_RE.match(lines[i]):
            end = i
            break
    return start, end


def committed_region(ledger: str) -> str | None:
    lines = ledger.split("\n")
    span = region_span(lines)
    if span is None:
        return None
    return "\n".join(lines[span[0] : span[1]])


def committed_table_rows(ledger: str) -> list[dict] | None:
    """The committed table as cell dicts (ticket/obligations/gates/operator/
    re-run), in committed order — '—' rows included."""
    region = committed_region(ledger)
    if region is None:
        return None
    rows: list[dict] = []
    for line in region.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) < 5 or cells[0] in ("ticket", "") or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(
            {
                "key": cells[0],
                "obligations_cell": cells[1],
                "gates_cell": cells[2],
                "operator_cell": cells[3],
                "rerun_cell": cells[4],
                "obligations": D_ID_RE.findall(_norm(cells[1])),
            }
        )
    return rows


def committed_table_keys(ledger: str) -> list[str] | None:
    """Ticket cells of the committed table (excluding the '—' row)."""
    rows = committed_table_rows(ledger)
    if rows is None:
        return None
    return [r["key"] for r in rows if r["key"] != "—"]


def committed_return_pass(ledger: str) -> str | None:
    in_state = False
    for line in ledger.split("\n"):
        if re.match(r"^##\s+CURRENT STATE", line):
            in_state = True
            continue
        if in_state and line.startswith("## "):
            break
        if in_state:
            m = re.match(r"^returnPass:\s*(.*?)\s*(#.*)?$", line)
            if m:
                return m.group(1).strip()
    return None


def rewrite_ledger(ledger: str, region: str, key_value: str) -> str | None:
    """Replace the generated region span and the ``returnPass:`` value,
    preserving every other byte (alignment and trailing comments included)."""
    lines = ledger.split("\n")
    span = region_span(lines)
    if span is None:
        return None
    # `region` ends with exactly one newline — its split tail ("") is the
    # blank separator line the committed layout keeps before the next `##`.
    new_lines = lines[: span[0]] + region.split("\n") + lines[span[1] :]
    out: list[str] = []
    found = False
    for line in new_lines:
        if not found:
            m = re.match(r"^(returnPass:)(\s*)(.*?)(\s*#.*)?$", line)
            if m:
                line = (
                    f"{m.group(1)}{m.group(2)}{key_value}{m.group(4) or ''}"
                ).rstrip()
                found = True
        out.append(line)
    if not found:
        return None
    return "\n".join(out)


# ── inputs for the home check ────────────────────────────────────────────────


def owed_obligations(events: list[dict]) -> dict[str, dict]:
    """obligation id -> event head, for heads OPEN/PARTIAL (correction events
    never extend the chain — same rule as current_projection.py)."""
    obligation_events = _load("obligation_events")
    by_obl: dict[str, list[dict]] = {}
    for ev in events:
        by_obl.setdefault(ev.get("obligation_id", "?"), []).append(ev)
    owed: dict[str, dict] = {}
    for oid, evs in by_obl.items():
        chain = sorted(
            (e for e in evs if e.get("kind") != "correction"),
            key=lambda e: e.get("seq", -1),
        )
        if chain and chain[-1]["to_status"] in obligation_events.OWED_STATUSES:
            owed[oid] = chain[-1]
    return owed


def load_dispositions(root: pathlib.Path) -> dict[str, str]:
    """deferral-id -> disposition string from the S1b universe table."""
    path = root / UNIVERSE_REL
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("source_kind") == "deferral" and row.get("source_ref"):
                out[row["source_ref"]] = row.get("disposition") or ""
    return out


def load_manifest_ids(root: pathlib.Path) -> set[str]:
    """Chain-row ticket ids, from the manifest (filename id per
    audit_current_state.parse_manifest conventions, without its diagnostics —
    the manifest's own checkers own malformed-row findings)."""
    path = root / "docs/tickets/00_MANIFEST.md"
    ids: set[str] = set()
    if not path.is_file():
        return ids
    in_chain = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if re.match(r"^##\s+The chain", line):
            in_chain = True
            continue
        if in_chain and re.match(r"^## (?!#)", line):
            in_chain = False
        if not in_chain or not line.startswith("|"):
            continue
        m = re.search(r"\b(\d+)_([A-Za-z0-9.\-]+?)__[0-9A-Za-z_.-]+\.md", line)
        if m:
            ids.add(m.group(2))
    return ids


def load_unit_rows(root: pathlib.Path) -> dict[str, list[str]]:
    """catalog unit id (R11-*) -> plan row ticket ids, via cat_ids."""
    path = root / PLAN_REL
    out: dict[str, list[str]] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rid = (row.get("id") or "").strip()
            for unit in re.split(r"[;,\s]+", row.get("cat_ids") or ""):
                if unit and rid:
                    out.setdefault(unit, []).append(rid)
    return out


def deferral_cells(root: pathlib.Path) -> dict[str, dict]:
    """obligation id -> parsed DEFERRALS row (needs unblocked_by for the
    recorded home markers)."""
    obligation_events = _load("obligation_events")
    return {r["id"]: r for r in obligation_events.parse_obligation_rows(root)}


# ── the home rule (B3 §3.13 item 4 / V6) ─────────────────────────────────────


def classify_home(
    oid: str,
    head: dict,
    row: dict | None,
    disposition: str | None,
    table_membership: dict[str, str],
    manifest_ids: set[str],
    unit_rows: dict[str, list[str]],
) -> tuple[str | None, list[str]]:
    """Return (home, problems). ``home`` is one of ``return-pass`` /
    ``manifest`` / ``disposition`` / ``watch`` — or None when none applies.
    ``problems`` lists integrity findings (two homes, unresolvable ticket(),
    a live-return-pass disposition with no table row)."""
    problems: list[str] = []
    in_table = oid in table_membership
    d_kind = d_ref = None
    if disposition:
        m = DISPOSITION_RE.match(disposition)
        if m:
            d_kind, d_ref = m.group(1), m.group(2)
        else:
            d_kind = disposition
    if in_table:
        home = "return-pass"
        if d_kind and d_kind != "live-return-pass":
            problems.append(
                f"{oid}: in the RETURN PASS table (row "
                f"{table_membership[oid]!r}) AND disposed {disposition} — "
                "two homes"
            )
    elif d_kind == "live-return-pass":
        problems.append(
            f"{oid}: disposed {disposition} but no RETURN PASS row names it — "
            "the map is missing a row"
        )
        home = None
    elif d_kind == "ticket":
        home = "manifest"
        rows = unit_rows.get(d_ref or "", [])
        if not rows:
            problems.append(
                f"{oid}: disposition {disposition} resolves to no manifest "
                "chain row (cat_ids)"
            )
    elif d_kind:
        # later-phase / wontfix / decision / operator-action / adr-waiver /
        # merged-into / spec-amendment — a recorded non-chain home.
        home = "disposition"
    else:
        search = " ".join(
            [
                head.get("landing") or "",
                head.get("owner") or "",
                (row or {}).get("unblocked_by") or "",
            ]
        )
        if any(t in manifest_ids for t in CHAIN_ROW_RE.findall(search)):
            home = "manifest"
        elif WATCH_BOUND_RE.search(search):
            # a recorded bounded watch: the DEFERRALS `unblocked by` cell's
            # owner:/trigger:/due: segments name where it unblocks (DEFERRALS
            # rule 5) — the register entry itself is the home.
            home = "watch"
        else:
            home = None
    return home, problems


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_generate(root: pathlib.Path) -> int:
    data, errors = load_map(root)
    if errors:
        for e in errors:
            print(f"generate: {e}", file=sys.stderr)
        return 2
    manifest_ids = load_manifest_ids(root)
    map_errors = validate_map(data, manifest_ids)
    if map_errors:
        for e in map_errors:
            print(f"generate: {e}", file=sys.stderr)
        return 2
    ledger_path = root / LEDGER_REL
    if not ledger_path.is_file():
        print(f"generate: {LEDGER_REL} missing", file=sys.stderr)
        return 2
    ledger = ledger_path.read_text(encoding="utf-8")
    region = render_region(data)
    new = rewrite_ledger(ledger, region, return_pass_value(data))
    if new is None:
        print(
            "generate: no `### RETURN PASS — current` region or no "
            "`returnPass:` line in the LEDGER",
            file=sys.stderr,
        )
        return 2
    if new == ledger:
        print(
            f"generate: {LEDGER_REL} already in sync "
            f"({len(data.get('row', []))} rows · returnPass "
            f"{len(table_tickets(data))} ids)"
        )
        return 0
    ledger_path.write_text(new, encoding="utf-8")
    print(
        f"generate: rewrote `### RETURN PASS — current` + `returnPass:` in "
        f"{LEDGER_REL} ({len(data.get('row', []))} rows · "
        f"{len(table_tickets(data))} key ids)"
    )
    return 0


def cmd_check(root: pathlib.Path) -> int:
    data, errors = load_map(root)
    problems: list[str] = list(errors)
    ledger_path = root / LEDGER_REL
    if not ledger_path.is_file():
        problems.append(f"{LEDGER_REL}: missing")
        ledger = ""
    else:
        ledger = ledger_path.read_text(encoding="utf-8")

    manifest_ids = load_manifest_ids(root)
    if not errors:
        problems += validate_map(data, manifest_ids)

    # 1. the committed region equals the generated form byte-for-byte
    region = committed_region(ledger)
    if region is None:
        problems.append("LEDGER: no `### RETURN PASS — current` region")
    elif not errors and region != render_region(data):
        problems.append(
            "LEDGER: `### RETURN PASS — current` differs from the generated "
            "output — run `return_pass.py generate` (byte-for-byte, V6)"
        )

    # 2. returnPass: equals the sorted table tickets — both the committed
    #    value vs the committed table and vs the generated value
    table_keys = committed_table_keys(ledger)
    rp_value = committed_return_pass(ledger)
    generated_value = return_pass_value(data)
    if rp_value is None:
        problems.append("LEDGER: no `returnPass:` line in CURRENT STATE")
    else:
        committed_sorted = ", ".join(
            sorted(table_keys or [], key=ticket_sort_key)
        )
        if table_keys is not None and rp_value != committed_sorted:
            problems.append(
                f"returnPass: value disagrees with the committed table's "
                f"ticket column — committed {rp_value!r} vs table "
                f"{committed_sorted!r} (V6)"
            )
        if rp_value != generated_value:
            problems.append(
                f"returnPass: {rp_value!r} ≠ the generated key "
                f"{generated_value!r} — run `return_pass.py generate`"
            )

    # 3. the exactly-one-home rule over every owed obligation
    obligation_events = _load("obligation_events")
    events, load_errors = obligation_events.load_jsonl(
        root / obligation_events.EVENTS_PATH
    )
    for e in load_errors:
        problems.append(f"events.jsonl: {e}")
    rows_by_id = deferral_cells(root)
    owed = owed_obligations(events)
    dispositions = load_dispositions(root)
    unit_rows = load_unit_rows(root)
    membership = map_obligation_index(data)
    evaluated = len(rows_by_id) or len(owed)
    homes: dict[str, str] = {}
    for oid, head in owed.items():
        home, probs = classify_home(
            oid,
            head,
            rows_by_id.get(oid),
            dispositions.get(oid),
            membership,
            manifest_ids,
            unit_rows,
        )
        if home is not None:
            homes[oid] = home
        else:
            probs.append(f"{oid}: owed but has no home — not a RETURN PASS "
                         "row, names no manifest row, carries no disposition "
                         "and no recorded owner:/trigger:/due: bound")
        problems += probs
    # a map row naming an obligation that is not owed is a stale row —
    # regeneration must drop it (the staying-in-sync rule)
    for oid, key in membership.items():
        if oid not in owed:
            problems.append(
                f"map row {key!r} names {oid}, which is not owed "
                "(terminal or unknown) — regenerate the table"
            )
    if evaluated == 0:
        print(
            "check: VACUOUS — the obligation register parsed to zero rows; "
            "nothing was evaluated (SIG-ENG-042)",
            file=sys.stderr,
        )
        return 3
    if problems:
        print(
            f"check: FAIL — evaluated {evaluated} obligations "
            f"({len(owed)} owed; homes resolved: {len(homes)}) · "
            f"{len(problems)} problem(s):",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(
        f"check: OK — evaluated {evaluated} obligations ({len(owed)} owed, "
        f"each in exactly one home) · {len(data.get('row', []))} table rows · "
        f"returnPass {len(table_tickets(data))} ids · region byte-identical"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    for name in ("generate", "check"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=pathlib.Path, default=ROOT)
    args = ap.parse_args(argv)
    if args.cmd == "generate":
        return cmd_generate(args.root)
    if args.cmd == "check":
        return cmd_check(args.root)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
