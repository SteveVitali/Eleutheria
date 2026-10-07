#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deterministic current-state projection — `current-projection/1` + `input-manifest/1` (P32.7).

ADR-126 / SIG-MEM-002: renders the current view of every obligation, scoped coverage
assessment, evidence-domain record, funnel value, governing ADR and known
inconsistency from an explicitly hashed input set. The output is **advisory**:
`docs/build/LEDGER.md` CURRENT STATE and the DEFERRALS compatibility cells remain
the control authority — this tool never writes them. Conflicts are preserved, never
synthesized into an answer; if inconsistencies remain the tool still emits a bounded
report and exits nonzero.

Semantic payload timestamps are fixed inputs (recorded dates inside events /
assessments / source docs). Wall-clock generation time lives only in
`receipt.json`, which is a receipt — never an input, never part of the payload.

    generate [--out DIR]      write manifest.json + current.json + CURRENT.md
                              (+ obligations-N.md spill pages) + receipt.json
    verify [--out DIR]        recompute input digests + regenerate the payload;
                              nonzero when any input hash changed (stale) or the
                              committed output drifted
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = pathlib.Path(__file__).resolve().parent
OUT_DIR_REL = "docs/build/reports/current"
OBLIGATIONS_REL = "docs/build/reports/obligations"
MAX_LINES = 250
MAX_BYTES = 20 * 1024

CORE_INPUTS = [
    "docs/tickets/DEFERRALS.md",
    "docs/tickets/00_MANIFEST.md",
    "docs/build/LEDGER.md",
    "docs/build/BUILD_INDEX.md",
    "docs/build/COVERAGE_MATRIX.csv",
    "docs/build/BACKLOG.csv",
    f"{OBLIGATIONS_REL}/events.jsonl",
    f"{OBLIGATIONS_REL}/coverage_assessments.jsonl",
    f"{OBLIGATIONS_REL}/reconciliations.json",
    f"{OBLIGATIONS_REL}/governing_adrs.json",
    f"{OBLIGATIONS_REL}/MIGRATION.md",
    "docs/build/reports/p32.1-baseline/EVIDENCE_DOMAINS_AND_SOURCE_FUNNEL.md",
    "docs/build/reports/p32.1-baseline/RECONCILIATION.md",
    "docs/2_canonical_design_spec.md",
]
# the projection also depends on everything the audit reads — it is enumerated by
# glob so no silent source is missed:
GLOB_INPUTS = [
    "docs/tickets/*.md",
    "docs/adr/*.md",
    "docs/build/readouts/*.md",
    "docs/build/runs/*.md",
]
MANIFEST_SCHEMA = "input-manifest/1"
PROJECTION_SCHEMA = "current-projection/1"
RECEIPT_SCHEMA = "projection-receipt/1"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


audit_current_state = _load("audit_current_state")
obligation_events = _load("obligation_events")

diag = audit_current_state.diag
OWED = obligation_events.OWED_STATUSES
TERMINAL = obligation_events.TERMINAL_STATUSES
DOMAINS = obligation_events.DOMAINS
MET_VERDICTS = obligation_events.MET_VERDICTS


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enumerate_inputs(root: pathlib.Path, out_dir: pathlib.Path) -> list[str]:
    """The explicit input set: core files + glob enumeration, repo-relative,
    sorted, with generated outputs excluded by construction."""
    inputs: set[str] = set(CORE_INPUTS)
    for pat in GLOB_INPUTS:
        for p in sorted(root.glob(pat)):
            if p.is_file():
                inputs.add(p.relative_to(root).as_posix())
    out_prefix = out_dir.relative_to(root).as_posix() if out_dir.is_relative_to(root) else ""
    clean: list[str] = []
    for rel in sorted(inputs):
        if out_prefix and rel.startswith(out_prefix + "/"):
            continue  # generated output is never its own input (acyclic manifest)
        if not (root / rel).is_file():
            continue  # absent optional inputs are omitted, not fabricated
        clean.append(rel)
    return clean


def build_manifest(root: pathlib.Path, out_dir: pathlib.Path) -> dict:
    inputs = [
        {"path": rel, "sha256": _sha256_file(root / rel)} for rel in enumerate_inputs(root, out_dir)
    ]
    return {
        "schema": MANIFEST_SCHEMA,
        "acyclic": True,
        "rule": (
            "inputs are enumerated source files only; generated projections, run "
            "receipts and validation output under docs/build/reports/current/ are "
            "structurally excluded — the manifest cannot contain a forward or "
            "cyclic dependency because outputs are never inputs"
        ),
        "excluded_prefixes": [
            "docs/build/reports/current/",
            "docs/build/logs/",
        ],
        "input_commit": _git_head(root),
        "inputs": inputs,
    }


def _status_cells(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        m = re.match(r"^\s*([A-Za-z][A-Za-z0-9]*):\s*(.*?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def parse_ledger_state(root: pathlib.Path) -> dict:
    path = root / "docs/build/LEDGER.md"
    if not path.is_file():
        return {}
    text = path.read_text()
    state: dict[str, str] = {}
    in_state = False
    for line in text.splitlines():
        if re.match(r"^##?\s*CURRENT STATE", line):
            in_state = True
            continue
        if in_state and line.startswith("## "):
            break
        if in_state:
            m = re.match(r"^([a-zA-Z]+):\s*(.*?)\s*$", line)
            if m:
                # same convention as audit_current_state._lval: a trailing
                # `# comment` is annotation, not the value
                state[m.group(1)] = re.sub(r"\s*#.*$", "", m.group(2)).strip()
    return state


def parse_coverage_csv(root: pathlib.Path) -> dict[str, dict]:
    path = root / "docs/build/COVERAGE_MATRIX.csv"
    out: dict[str, dict] = {}
    if not path.is_file():
        return out
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            req = (
                row.get("id") or row.get("requirement_id") or row.get("requirement") or ""
            ).strip()
            if not req:
                continue
            out[req] = {
                "verdict": (row.get("verdict") or row.get("status") or "").strip(),
                "evidence": (row.get("evidence") or "").strip(),
                "assessed": (row.get("assessed") or row.get("assessed_at") or "").strip(),
                "label": "historical/csv",
            }
    return out


def parse_funnel(root: pathlib.Path) -> tuple[list[dict], list[dict], dict]:
    """Parse EVIDENCE_DOMAINS_AND_SOURCE_FUNNEL.md → (domains, baseline rows, releases)."""
    path = root / "docs/build/reports/p32.1-baseline/EVIDENCE_DOMAINS_AND_SOURCE_FUNNEL.md"
    domains: list[dict] = []
    baseline: list[dict] = []
    releases: dict = {"public_release": "—", "database_run_ids": "—", "note": ""}
    if not path.is_file():
        return domains, baseline, releases
    section = None
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            section = line
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if len(cells) > 2 and cells[0] == "" else cells
        if section and section.startswith("## 1") and len(cells) >= 4:
            dom = cells[0].strip("`")
            if dom in DOMAINS:
                domains.append(
                    {
                        "domain": dom,
                        "definition": cells[1],
                        "instruments": cells[2],
                        "never_establishes": cells[3],
                    }
                )
        if section and section.startswith("## 3") and len(cells) >= 3:
            unit = cells[0].strip()
            if unit and unit != "unit" and not unit.startswith("--"):
                baseline.append({"unit": unit, "value": cells[1], "domain_date_evidence": cells[2]})
                if unit == "published":
                    releases["public_release"] = cells[1]
    releases["database_run_ids"] = (
        "not recorded in projection inputs — hosted-domain facts are recorded "
        "evidence only (never measured by this offline tool)"
    )
    releases["note"] = (
        "public release row comes from the recorded p32.1 baseline input; no live "
        "fetch is performed"
    )
    return domains, baseline, releases


def classify_conflicts(
    diags: list[dict],
    events: list[dict],
    documented: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split all diagnostics (audit + event-chain + coverage checkers) into
    reconciled-by-event / reconciled-by-documentation / known-inconsistency sets.

    Reconciled conflicts are enumerated from the event store itself: an
    interpretation recorded on a migration anchor is the reconciliation — once
    the compatibility cell agrees with the head, the raw audit diag is gone for
    good, which is exactly what reconciled means."""
    doc_keys = {(d["check"], d["obligation"]) for d in documented}
    by_event: list[dict] = []
    for ev in events:
        if ev.get("kind") == "migration" and ev.get("anchor", {}).get("interpretation") in {
            "reconciled",
            "ambiguous-open",
        }:
            by_event.append(
                {
                    "obligation": ev["obligation_id"],
                    "event_id": ev["event_id"],
                    "interpretation": ev["anchor"]["interpretation"],
                    "from": ev["from_status"],
                    "to": ev["to_status"],
                    "observed_at": ev["observed_at"],
                    "evidence_refs": ev["evidence_refs"],
                    "reason": ev["reason"],
                }
            )
    covered_conflict_obligations = {
        ev["obligation_id"]
        for ev in events
        if ev.get("kind") == "migration"
        and ev.get("anchor", {}).get("interpretation") in {"reconciled", "ambiguous-open"}
    }
    by_doc: list[dict] = []
    inconsistencies: list[dict] = []
    for d in diags:
        if d["severity"] == "conflict" and (
            d["check"] == "deferrals/status-conflict"
            and d["obligation"] in covered_conflict_obligations
        ):
            continue  # already enumerated from the event store
        if (d["check"], d["obligation"]) in doc_keys:
            by_doc.append(
                {
                    "check": d["check"],
                    "obligation": d["obligation"],
                    "file": d["file"],
                    "pointer": next(
                        x["pointer"]
                        for x in documented
                        if (x["check"], x["obligation"]) == (d["check"], d["obligation"])
                    ),
                }
            )
            continue
        inconsistencies.append(d)
    return by_event, by_doc, inconsistencies


def build_projection(root: pathlib.Path, out_dir: pathlib.Path, manifest: dict) -> dict:
    diags, _meta = audit_current_state.audit(root)
    rows = obligation_events.parse_obligation_rows(root)
    events, _errs = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    assessments, _ = obligation_events.load_jsonl(root / obligation_events.ASSESSMENTS_PATH)
    # an inconsistent event chain or assessment set IS a known inconsistency —
    # the projection preserves it rather than rendering over bad inputs
    diags += obligation_events.check_event_chain(root, events)
    diags += obligation_events.check_assessments(root, assessments)
    by_obl: dict[str, list[dict]] = {}
    for ev in events:
        by_obl.setdefault(ev.get("obligation_id", "?"), []).append(ev)
    rec_path = root / f"{OBLIGATIONS_REL}/reconciliations.json"
    documented = (
        json.loads(rec_path.read_text()).get("documented", []) if rec_path.is_file() else []
    )
    by_event, by_doc, inconsistencies = classify_conflicts(diags, events, documented)

    obligations: list[dict] = []
    for row in rows:
        oid = row["id"]
        # correction events annotate the log — they never become the status
        # head and are not part of the projected chain (P34.8)
        chain = sorted(
            (e for e in by_obl.get(oid, []) if e.get("kind") != "correction"),
            key=lambda e: e.get("seq", -1),
        )
        head = chain[-1] if chain else None
        obligations.append(
            {
                "id": oid,
                "status": head["to_status"] if head else row["status"],
                "status_source": f"event-head {head['event_id']}" if head else "cell (no events)",
                "kind": row["kind"],
                "owner": head["owner"] if head else "—",
                "landing": head["landing"] if head else "—",
                "backlog_home": head["backlog_home"] if head else "—",
                "item": row["item"],
                "unblocked_by": row["unblocked_by"],
                "verify": row["verify"],
                "proxy": row["proxy"],
                "line": row["line"],
                "events": chain,
            }
        )
    owed = [o for o in obligations if o["status"] in OWED]

    for a in assessments:
        a.pop("superseded_by", None)
    coverage_historical = parse_coverage_csv(root)
    coverage_heads = [
        {
            "requirement_id": a["requirement_id"],
            "domain": a["domain"],
            "verdict": a["verdict"],
            "assessed_at": a["assessed_at"],
            "code_revision": a["code_revision"],
            "limitations": a["limitations"],
            "supersedes": a["supersedes"],
            "assessment_id": a["assessment_id"],
        }
        for a in sorted(assessments, key=lambda a: (a["requirement_id"], a["domain"], a["seq"]))
    ]

    domains, baseline, releases = parse_funnel(root)
    assess_by_domain: dict[str, list[dict]] = {}
    for a in coverage_heads:
        assess_by_domain.setdefault(a["domain"], []).append(
            {
                "requirement": a["requirement_id"],
                "verdict": a["verdict"],
                "assessed_at": a["assessed_at"],
            }
        )
    evidence_domains = []
    for d in domains:
        dom = d["domain"]
        recorded = [
            {"unit": b["unit"], "value": b["value"], "recorded": b["domain_date_evidence"]}
            for b in baseline
            if b["domain_date_evidence"].startswith(dom)
        ]
        evidence_domains.append(
            {
                "domain": dom,
                "instruments": d["instruments"],
                "never_establishes": d["never_establishes"],
                "recorded_baseline": recorded,
                "assessment_verdicts": assess_by_domain.get(dom, []),
            }
        )

    gov_path = root / f"{OBLIGATIONS_REL}/governing_adrs.json"
    governing = json.loads(gov_path.read_text()).get("adrs", []) if gov_path.is_file() else []

    control = parse_ledger_state(root)
    projection = {
        "schema": PROJECTION_SCHEMA,
        "authority": (
            "advisory — docs/build/LEDGER.md CURRENT STATE and the DEFERRALS.md "
            "compatibility cells remain the control authority; this projection is "
            "derived from hashed inputs and never writes them (shadow mode; the "
            "single-writer protocol is D-R10-MEMORY-1 → P32.8)"
        ),
        "input_commit": manifest["input_commit"],
        "manifest_inputs": len(manifest["inputs"]),
        "control": control,
        "counts": {
            "obligations": len(obligations),
            "owed": len(owed),
            "open": sum(1 for o in owed if o["status"] == "OPEN"),
            "partial": sum(1 for o in owed if o["status"] == "PARTIAL"),
            "terminal": len(obligations) - len(owed),
            "events": len(events),
            "transitions": sum(1 for e in events if e.get("kind") == "transition"),
            "coverage_assessments": len(assessments),
            "coverage_historical_rows": len(coverage_historical),
            "reconciled_by_event": len(by_event),
            "reconciled_by_documentation": len(by_doc),
            "known_inconsistencies": len(inconsistencies),
            "conflicted": len(inconsistencies),
        },
        "obligations": obligations,
        "coverage": {
            "historical_csv": {
                "path": "docs/build/COVERAGE_MATRIX.csv",
                "label": "historical/csv — dated cell assessments, preserved (not rewritten)",
                "by_requirement": coverage_historical,
            },
            "assessments": coverage_heads,
        },
        "evidence_domains": evidence_domains,
        "source_funnel": baseline,
        "releases": releases,
        "governing_adrs": governing,
        "reconciled": {"by_event": by_event, "by_documentation": by_doc},
        "known_inconsistencies": inconsistencies,
        "incomplete": bool(inconsistencies),
        "stale_sources": [],
    }
    return projection


def _verify_cell(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:160] + ("…" if len(text) > 160 else "")


def _short_ctrl(text: str) -> str:
    """LEDGER CURRENT-STATE values carry long prior-note chains; the
    orientation view shows only the current head."""
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.split(" | PRIOR:", 1)[0].strip()
    return text[:160] + ("…" if len(text) > 160 else "")


def render_markdown(projection: dict) -> tuple[str, dict[str, str]]:
    """Render CURRENT.md plus link-out pages; the main view is bounded and never
    drops obligations — overflow moves to pages, still complete."""
    c = projection["counts"]
    ctrl = projection["control"]
    sections: list[tuple[str, list[str]]] = []
    head = [
        "# SIG current build state — deterministic projection (advisory)",
        "",
        "> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md",
        "> compatibility cells remain the control authority. This view is derived from",
        "> the hashed `input-manifest/1` (`manifest.json`); it never writes control",
        "> state. Shadow mode — the single-writer protocol is `D-R10-MEMORY-1` → P32.8.",
        f"> input_commit: `{projection['input_commit']}` · inputs hashed: "
        f"{projection['manifest_inputs']} · wall-clock receipt: `receipt.json`",
        "",
        "## Control (advisory read of LEDGER.md)",
        "",
        f"- projectStatus `{ctrl.get('projectStatus', '?')}` · round `{ctrl.get('round', '?')}` · "
        f"nextTicket `{ctrl.get('nextTicket', '?')}` · lastCompleted `{ctrl.get('lastCompleted', '?')}`",
        f"- chainTip `{_short_ctrl(ctrl.get('chainTip', '—'))}` · "
        f"returnPass `{_short_ctrl(ctrl.get('returnPass', '—'))}` · "
        f"updatedAt `{_short_ctrl(ctrl.get('updatedAt', '—'))}`",
        "",
    ]
    counts = [
        "## Obligations",
        "",
        f"- {c['obligations']} obligations · **{c['owed']} owed** "
        f"({c['open']} OPEN, {c['partial']} PARTIAL) · {c['terminal']} terminal",
        f"- {c['events']} events ({c['transitions']} transitions beyond anchors) · "
        f"{c['reconciled_by_event']} status conflicts reconciled by recorded events · "
        f"{c['reconciled_by_documentation']} documented in `reconciliations.json`",
        "",
    ]
    obl_lines = [
        "| obligation | status | owner | landing | how to verify |",
        "|---|---|---|---|---|",
    ]
    owed = [o for o in projection["obligations"] if o["status"] in OWED]
    for o in owed:
        obl_lines.append(
            f"| {o['id']} | {o['status']} | {_verify_cell(o['owner'])} | "
            f"{_verify_cell(o['landing'])} | {_verify_cell(o['verify'])} |"
        )
    sections.append(("obligations", obl_lines))

    inc_lines: list[str] = []
    if projection["known_inconsistencies"]:
        inc_lines.append("| check | obligation | message |")
        inc_lines.append("|---|---|---|")
        for d in projection["known_inconsistencies"]:
            inc_lines.append(f"| {d['check']} | {d['obligation']} | {_verify_cell(d['message'])} |")
    else:
        inc_lines.append(
            "- none — every P32.1 baseline conflict is either reconciled by a recorded "
            "event interpretation (old values preserved on the anchor) or documented in "
            "`reconciliations.json`; anything new would appear here and fail `verify`"
        )
    sections.append(("inconsistencies", inc_lines))

    dom_lines = ["| domain | latest recorded evidence | assessments |", "|---|---|---|"]
    for d in projection["evidence_domains"]:
        rec = (
            "; ".join(
                f"{r['unit']}: {_verify_cell(r['value'])[:60]} ({r['recorded'][:60]})"
                for r in d["recorded_baseline"]
            )
            or "—"
        )
        av = (
            "; ".join(
                f"{a['requirement']}={a['verdict']} ({a['assessed_at']})"
                for a in d["assessment_verdicts"]
            )
            or "—"
        )
        dom_lines.append(f"| {d['domain']} | {rec} | {av} |")
    sections.append(("domains", dom_lines))

    fun_lines = ["| unit | recorded value | domain · date · evidence |", "|---|---|---|"]
    for b in projection["source_funnel"]:
        fun_lines.append(
            f"| {b['unit']} | {_verify_cell(b['value'])[:80]} | {b['domain_date_evidence'][:80]} |"
        )
    sections.append(("funnel", fun_lines))

    rel_lines = [
        f"- public release: {_verify_cell(projection['releases'].get('public_release', '—'))[:140]}",
        f"- database run ids: {projection['releases'].get('database_run_ids', '—')}",
    ]
    sections.append(("releases", rel_lines))

    cov_lines = [
        "| requirement | domain | verdict | assessed_at | supersedes |",
        "|---|---|---|---|---|",
    ]
    for a in projection["coverage"]["assessments"]:
        cov_lines.append(
            f"| {a['requirement_id']} | {a['domain']} | {a['verdict']} | "
            f"{a['assessed_at']} | {a['supersedes'] or '—'} |"
        )
    cov_lines.append(
        f"- historical CSV: {c['coverage_historical_rows']} dated rows in "
        "`docs/build/COVERAGE_MATRIX.csv` (labelled `historical/csv`, preserved verbatim)"
    )
    sections.append(("coverage", cov_lines))

    gov_lines = ["| ADR | scope | file |", "|---|---|---|"]
    for g in projection["governing_adrs"]:
        gov_lines.append(
            f"| {g.get('id', '?')} | {_verify_cell(g.get('scope', ''))[:80]} | {g.get('file', '—')} |"
        )
    sections.append(("adrs", gov_lines))

    tail = [
        "## Reading this view",
        "",
        "- owed obligations are never dropped: if the table exceeds the view budget it",
        "  moves to `obligations-N.md` link-out pages (still complete, same columns).",
        "- `verify` recomputes every input digest; a changed input is reported stale.",
        "- deferred work context: `docs/tickets/DEFERRALS.md` remains the register; this",
        "  projection reproduces its leading cells via the event chains it validates.",
        "",
    ]

    def assemble(inline_obligations: bool, extra_sections: list[tuple[str, list[str]]]) -> str:
        lines = list(head) + list(counts)
        if inline_obligations:
            lines += obl_lines
        for name, body in extra_sections:
            if name == "obligations":
                if not inline_obligations:
                    lines += body + [""]
                continue
            title = {
                "inconsistencies": "## Known inconsistencies (preserved, never synthesized)",
                "domains": "## Evidence domains — recorded evidence only",
                "funnel": "## Source funnel (recorded baseline, domain-labelled)",
                "releases": "## Releases (recorded)",
                "coverage": "## Coverage — scoped assessments + historical CSV",
                "adrs": "## Governing ADRs",
            }.get(name, f"## {name}")
            lines += [title, ""] + body + [""]
        lines += tail
        return "\n".join(lines) + "\n"

    # Pass 1: fully inlined. Pass 2+: spill the obligation table into pages, then
    # coverage, then funnel, until bounded. Nothing is ever dropped.
    doc = assemble(True, sections)
    if len(doc.splitlines()) <= MAX_LINES and len(doc.encode()) <= MAX_BYTES:
        return doc, {}

    pages: dict[str, str] = {}
    spill_order = ["obligations", "coverage", "funnel", "adrs"]
    spilled: set[str] = set()

    def _replace_section(name: str, body: list[str]) -> None:
        for i, (n, _b) in enumerate(sections):
            if n == name:
                sections[i] = (name, body)
                return

    def spill(name: str, chunk: int = 120) -> None:
        body = dict(sections)[name]
        if body[0].startswith("|"):
            header, rows = body[:2], body[2:]
        else:
            header, rows = [], body
        if len(rows) <= chunk:
            fname = f"{name}.md"
            pages[fname] = (
                f"# link-out: {name} (page 1/1)\n\n"
                + "\n".join(header + rows)
                + "\n\n← back: CURRENT.md\n"
            )
            _replace_section(
                name,
                [f"- `{name}` → see [{fname}]({fname}) (complete — {len(rows)} rows)"],
            )
            return
        n_pages = (len(rows) + chunk - 1) // chunk
        links = []
        for i in range(n_pages):
            fname = f"{name}-{i + 1}.md"
            part = rows[i * chunk : (i + 1) * chunk]
            page = f"# link-out: {name} (page {i + 1}/{n_pages})\n\n"
            page += "\n".join(header + part)
            page += "\n\n← back: CURRENT.md"
            if i + 1 < n_pages:
                page += f" · next page: {name}-{i + 2}.md"
            page += "\n"
            pages[fname] = page
            links.append(f"[{fname}]({fname})")
        _replace_section(
            name,
            [f"- `{name}` spilled across {n_pages} pages (complete): " + " ".join(links)],
        )

    for name in spill_order:
        if len(doc.splitlines()) <= MAX_LINES and len(doc.encode()) <= MAX_BYTES:
            break
        spill(name)
        spilled.add(name)
        doc = assemble("obligations" not in spilled, sections)
    return doc, pages


def generate(root: pathlib.Path, out_dir: pathlib.Path) -> int:
    manifest = build_manifest(root, out_dir)
    projection = build_projection(root, out_dir, manifest)
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    projection["manifest_sha256"] = _sha256_text(manifest_text)
    md, pages = render_markdown(projection)
    projection["current_md"] = {
        "lines": len(md.splitlines()),
        "bytes": len(md.encode()),
        "budget": f"{MAX_LINES} lines / {MAX_BYTES} bytes",
        "spill_pages": sorted(pages),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(manifest_text)
    (out_dir / "current.json").write_text(
        json.dumps(projection, indent=2, ensure_ascii=False) + "\n"
    )
    (out_dir / "CURRENT.md").write_text(md)
    for name, text in pages.items():
        (out_dir / name).write_text(text)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "generated_at": _utcnow(),
        "git_head": _git_head(root),
        "tool": "docs/build/tools/current_projection.py",
        "note": (
            "wall-clock receipt — kept out of the deterministic payload; "
            "input digests live in manifest.json"
        ),
        "files": sorted(p.name for p in out_dir.iterdir() if p.name != "receipt.json"),
    }
    (out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    c = projection["counts"]
    print(
        f"generate: {c['obligations']} obligations ({c['owed']} owed) · "
        f"{c['events']} events · {c['coverage_assessments']} assessments · "
        f"{c['known_inconsistencies']} known inconsistencies · "
        f"CURRENT.md {projection['current_md']['lines']} lines/"
        f"{projection['current_md']['bytes']}B "
        f"(+{len(pages)} spill pages) → {out_dir.relative_to(root) if out_dir.is_relative_to(root) else out_dir}"
    )
    if projection["known_inconsistencies"]:
        for d in projection["known_inconsistencies"]:
            print(
                f"  INCOMPLETE {d['check']} {d['obligation']}: {d['message'][:100]}",
                file=sys.stderr,
            )
        return 1
    return 0


def verify(root: pathlib.Path, out_dir: pathlib.Path) -> int:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        print(f"verify: {manifest_path} missing — run generate", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    stale: list[str] = []
    for entry in manifest["inputs"]:
        rel = entry["path"]
        p = root / rel
        if not p.is_file():
            stale.append(f"{rel}: MISSING (recorded {entry['sha256'][:12]}…)")
        else:
            now = _sha256_file(p)
            if now != entry["sha256"]:
                stale.append(
                    f"{rel}: stale digest — recorded {entry['sha256'][:12]}… vs current {now[:12]}…"
                )
    current = set(enumerate_inputs(root, out_dir))
    recorded = {e["path"] for e in manifest["inputs"]}
    for rel in sorted(current - recorded):
        stale.append(f"{rel}: new input not covered by the recorded manifest")
    # output drift: regenerate the payload in-memory and compare
    projection = build_projection(root, out_dir, manifest)
    projection["manifest_sha256"] = (
        manifest["manifest_sha256"] if "manifest_sha256" in manifest else ""
    )
    committed = out_dir / "current.json"
    if committed.is_file():
        regen = json.dumps(projection, indent=2, ensure_ascii=False) + "\n"
        have = committed.read_text()
        # compare payload minus self-referential fields
        pj = json.loads(regen)
        cj = json.loads(have)
        for k in ("manifest_sha256", "current_md", "input_commit"):
            pj.pop(k, None)
            cj.pop(k, None)
        if pj != cj:
            stale.append("current.json: projection content drifted from recorded inputs")
    md_path = out_dir / "CURRENT.md"
    if md_path.is_file():
        nlines = len(md_path.read_text().splitlines())
        nbytes = len(md_path.read_bytes())
        if nlines > MAX_LINES or nbytes > MAX_BYTES:
            stale.append(
                f"CURRENT.md exceeds budget: {nlines} lines/{nbytes}B "
                f"(limit {MAX_LINES}/{MAX_BYTES})"
            )
    if stale:
        print("verify: STALE / drifted — regenerate the projection:", file=sys.stderr)
        for s in stale:
            print(f"  {s}", file=sys.stderr)
        return 1
    print(f"verify: fresh — {len(recorded)} input digests match; projection in sync")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    for name in ("generate", "verify"):
        p = sub.add_parser(name)
        p.add_argument(
            "--out",
            type=pathlib.Path,
            default=ROOT / OUT_DIR_REL,
        )
    args = ap.parse_args(argv)
    if args.cmd == "generate":
        return generate(ROOT, args.out)
    if args.cmd == "verify":
        return verify(ROOT, args.out)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
