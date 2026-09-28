#!/usr/bin/env python3
"""Render this dated plan's contracts, ownership CSV and §55 from PLAN.json.

No runtime or ledger writes. Use --check to verify generated planning artifacts.
The manifest/ADR/coverage integration is deliberately a separate reviewed action.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
REL = HERE.relative_to(ROOT).as_posix()
RESEARCH = {
    "S1": "S1-evidence-integrity.md", "S2": "S2-local-dossiers.md",
    "S3": "S3-human-evaluation.md", "S4": "S4-public-product.md",
    "S5": "S5-source-strategy.md", "S6": "S6-build-memory.md",
}


def outputs(plan: dict) -> dict[Path, str]:
    result = {}
    owners = {rid: t for t in plan["tickets"] for rid in t["requirements"]}
    for t in plan["tickets"]:
        marker = t["kind"] in {"human", "gate"}
        lines = [
            "<!-- Authored from the reviewed six-stream PLAN.json; planning is not execution evidence. -->",
            f'# {t["id"]} — {t["title"]}', "",
            f'- **Sequence:** {t["sequence"]} of {plan["last_sequence"]}',
            f'- **Phase:** Round 10 / {t["stream"]}',
            f'- **Kind:** {t["kind"]}',
            '- **Tag:** six-stream-round10',
            '- **base_branch:** current checkout — the branch the previous ticket left checked out',
            '- **Depends on:** ' + ', '.join(t["depends"]),
            f'- **Gate status:** {t["gate"]}',
            f'- **Live stage:** {t["live"]}',
        ]
        if not marker:
            lines.append(f'- **Run:** `implement-spec spec=docs/tickets/{t["filename"]} live_verification=false`')
        lines += ["", "## Goal", "", t["title"] + ". Deliver the bounded delta below against the actual landed predecessor, preserving prior decisions and explicit verification domains.",
                  "", "## Load (read these — do not re-read others)", "",
                  '- Root `AGENTS.md`, then the nearest package `AGENTS.md` for every touched package; `docs/tickets/DEFERRALS.md` before work.',
                  '- `docs/2_canonical_design_spec.md` Part 0, §3, Part VIII, and §55' + ("; requirements below give exact subsection ownership." if t["requirements"] else "; the tail audits rather than re-owns implementation requirements."),
                  f'- `{REL}/DESIGN.md` shared contract and sequencing sections; `{REL}/HANDOFF.md` activation rules.',
                  f'- `{REL}/PLAN.json` for exact dependency/ownership map; `docs/tickets/00_MANIFEST.md` remains chain order.']
        if t["stream"] in RESEARCH:
            lines.append(f'- `{REL}/research/{RESEARCH[t["stream"]]}` for evidence, field contracts, limits and negative cases relevant to this unit.')
        for path in t["paths"]:
            suffix = "" if (ROOT / path).exists() else " (planned output/target; confirm or create within this contract)"
            lines.append(f'- `{path}`{suffix}.')
        lines += ["", "## In scope — deliverables", ""]
        for i, item in enumerate(t["deliverables"], 1):
            lines.append(f"{i}. {item}")
        lines += ["", "## Out of scope", "",
                  '- Other contracts retain their implementation ownership. Consume shared schemas/functions; do not fork them to finish this unit.',
                  '- No source rights flip, human label, gate signature, outreach, publication, main integration or unapproved spend is inferred from this ticket.',
                  '- Do not rewrite landed ADR bodies, claim history, prior run evidence or the active plan without an appended scoped amendment.',
                  "", "## Acceptance criteria", ""]
        for item in t["acceptance"]:
            lines.append(f'- [ ] {item} *({"human" if marker else "deterministic or independently reviewed, as identified in the readout"})*')
        if marker:
            readout = "ACCEPT-R10.md" if t["id"] == "GATE-ACCEPT" else t["id"] + ".md"
            lines += [f'- [ ] Actual authority and date recorded in `docs/build/readouts/{readout}` and the ledger gate record; checkboxes stay unticked until then. *(human)*',
                      "", "## Exit criterion and blocked consumers", "",
                      'The signed/verified readout satisfies the exact criteria above. This marker has no implement-spec run. Never guess past it; a deferral or reduced-scope decision requires the operator’s explicit recorded choice. Engineering before this marker can complete with precise OPEN RETURN PASS obligations; that does not satisfy this exit criterion.',
                      'Direct consumers: ' + ', '.join(x["id"] for x in plan["tickets"] if t["id"] in x["depends"]) + '.']
        else:
            lines += ['- [ ] Verification green; every new behavior has a meaningful test that fails if removed; requirement ids stamped in the PR; anything not automatically verifiable has an owned `DEFERRALS.md` row and compensating control; new deviations/decisions have ADRs; run ledger/BUILD_INDEX and control advancement follow the authorized closeout protocol. *(deterministic)*',
                      "", "## Verification and live return path", "",
                      'Run the package gates relevant to the change and `make check` before committing. DB/temporal/RLS changes require Docker-backed tests with `SIG_REQUIRE_DB_TESTS=1`; web changes require `npm --prefix web run check`. Run spec/coverage/backlog/build-memory checks for memory/spec changes. Record exact commands, revision, domain and unavailable checks; a skip is not a live pass.',
                      'The Run line starts the engineering stage with live verification disabled. An operator-gated live stage is executed only after its concrete scope/approval is recorded; re-dispatch the same contract with `live_verification=true` at the explicit RETURN PASS. Do not close the live obligation from fixture success. If this ticket requires a signed predecessor marker, it must land first; no automatic bypass.',
                      'Use resource bounds from the research and live packet; changed requirements or overflowing independent concerns require an appended split/amendment before continuing. Preserve prior wire names and defaults unless the canonical contract explicitly defines a versioned migration.']
        lines += ["", "## Requirement IDs to satisfy and stamp in the PR", "",
                  ', '.join(t["requirements"]) if t["requirements"] else 'No new requirement ownership. Verify the referenced prerequisites and the round-wide obligations; do not double-own another ticket’s ids.',
                  "", "## Cross-cutting invariants", "",
                  'The manifest and canonical §3/Part VIII bind this ticket: evidence-first; qualified uncertainty; append-only corrections; no plate/trip/person ingestion; sensitivity and licence compartments; fail-closed source gates; no invented human work; no merge/tag/push-main. Public access withdrawals apply even to historical releases and rollback.',
                  "", "## Notes", "",
                  f'Planning baseline: `{plan["baseline"]}`; engineering is not yet implemented by this packet. Reconfirm anchors at P32.1. This contract is one coherent change; independent human, source and publication prerequisites remain visible in the readouts and deferrals.']
        result[ROOT / "docs/tickets" / t["filename"]] = "\n".join(lines) + "\n"

    sections = {
        "55.2": "Evidence, semantics and temporal integrity",
        "55.3": "A three-dossier acceptance portfolio",
        "55.4": "Independent human evaluation",
        "55.5": "Released discovery, citations and correction",
        "55.6": "Gap-driven source acquisition",
        "55.7": "Current build memory and closeout reliability",
        "55.8": "Activation, verification and publication",
    }
    s = ["# Part XI — Evidence integrity and investigation completion", "", "## 55. Round-10 contract extension (2026-09-25)", "",
         "### 55.1 Scope, precedence and execution authority", "",
         f'This additive extension is recorded by {plan["planning_adr"]}, under the operator’s request for six fully researched follow-up streams. It defines future implementation obligations; it is not evidence that they are implemented, that human labels exist, or that a source/publication gate is signed. Existing Part VIII protections, frozen package layout, P31 ownership and operator decisions remain binding. Where this extension tightens a current implementation (notably provenance, identity and evaluation), migrate additively with the explicitly gated rollout described here; preserve historical decisions and disclosures.', "",
         f'The design rationale and typed shared interfaces are `{REL}/DESIGN.md`; primary-source and code research is in its `research/` directory. `{REL}/PLAN.json` and `REQUIREMENTS.csv` map every new requirement to exactly one contract in `docs/tickets/00_MANIFEST.md`. Research notes propose examples; these normative paragraphs and the final design control the implementation when earlier draft suggestions differ.', "",
         'Execution sequence: reconcile landed P31 → integrity/tooling and independent engineering → freeze repaired snapshot → human development labels and dossier semantic review → freeze candidate then draw its confirmatory sample → independent blinded final campaign → one evaluation without holdout leakage → rematerialize every final artifact → verify one candidate → human publication gate → publish → full independent capstone/reconciliation/documentation tail. The evaluator and memory events remain shadow-only until their recorded activation/cutover decisions. No planning operation advances another active ledger.', "",
         # Landed-state paragraph appended by P33.5's spec_src amendment (ADR-145, 2026-09-28):
         # the canonical §55.1 source carries it verbatim; the renderer must emit it or --check
         # reports a false stale flag and a blind regen would revert the amendment.
         'The paragraph above is the *design* order. The landed Round-10 build deviated from it at exactly one point, by recorded operator decision: the human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) was deferred wholesale on 2026-10-19 and the chain resumed at P32.23a under amended scope — the release candidate was materialized on the **active provisional** policy basis with the deferral disclosed in every artifact (ADR-142). §55.9 records the dated landed state; the deferred rows remain OPEN obligations, not completed work (P33.5 reconciliation, ADR-145).', "",
         'Architecture decision: retain Astro plus the three named map/search/network React islands. Add release-specific read-only SQLite FTS5 search through the existing API package with no-JS HTML and complete static browse/records; use separate, gated anonymous intake storage and a restricted correction application bridge. No general SPA, new basemap, account system or search cluster is selected. Bounded cost/latency/storage benchmarks precede deployment; failure requires a measured alternative ADR, not silently reduced corpus coverage.', ""]
    # Landed-state paragraphs appended by P33.5's spec_src amendment (ADR-145, 2026-09-28),
    # keyed by the requirement they follow in the rendered section.
    landed_notes = {
        "SIG-TRUST-009": ["The landed GATE-G3 signature (2026-10-19) was an **explicitly recorded reduced-scope acceptance** for the bounded staging publication (ADR-144): the deferred evaluation spine (`evaluation.status=deferred`, `eval-confidence/1` `mode=shadow`, `applied=[]`), dossiers published `mechanical_complete`/`pilot_complete=False`, and the non-operational intake receiver were each *scoped and disclosed*, not satisfied. The release half of `D-R10-PUBLISH-1` was discharged by that signature; production exposure, the production candidate (`D-P32.23a-1`) and intake operating prerequisites (`D-P32.16-1`) remain OPEN. Nothing in a scoped signature waives this requirement's full criterion set for production exposure — the scope is recorded, never silently dropped."],
        "SIG-TRUST-010": ["Where the final evaluation is **deferred by recorded operator decision** rather than decided, the inconclusive case of this contract applies (ADR-142): the candidate materializes the *active provisional* rules (`provisional-ruleset/1`), pins `evaluation.status=deferred` / `decision=null` / `mode=shadow` / `applied=[]` in its identity, builds unpublished-by-construction (the `latest` pointer is byte-checked unchanged), and the build refuses if the shadow gate ever reports activated. A deferred-evaluation candidate cannot satisfy release acceptance; a later accepted evaluation re-issues the candidate under this requirement's full terms."],
    }
    for section, title in sections.items():
        s += [f"### {section} {title}", ""]
        for rid, r in plan["requirements"].items():
            if r["section"] == section:
                s += [f'**{rid} ({r["level"]}).** {r["text"]} Owner: {owners[rid]["id"]}.', ""]
                for note in landed_notes.get(rid, []):
                    s += [note, ""]
    s += ["### 55.9 Traceability and explicit human obligations", "",
          "New requirement rows enter COVERAGE_MATRIX as MISSING with ticket routing; planning does not turn them MET. Existing assessments remain dated historical evidence. D-R6.1-EVAL and the human portions of D-P30.2b-1/-2 move to the explicit HUMAN-H4/P32.22a/HUMAN-H5/P32.23 path without being closed. P31 source/publication and calendar obligations retain their original authorities and evidence. The research candidate inventory records review depth and uncertain availability; a listed URL is not ingestion clearance.", "",
          "HUMAN-H4 records human development/calibration labels and separate documentary semantic review; P32.22a freezes the candidate and its sampling frame; HUMAN-H5 records final blinded confirmatory adjudication. GATE-G3 exercises HG-11 for the concrete release and receiver operating packet. GATE-ACCEPT records Round-10 capstone acceptance. Source rights, resource changes, workflow-writer cutover and independent usability work remain separately scoped decisions/return paths. Neither an agent-generated label nor an incomplete dossier may satisfy the human/pilot gate by relabeling it complete.", "",
          # Landed-state paragraph appended by P33.5's spec_src amendment (ADR-145, 2026-09-28).
          "**Landed state as of the P33.5 reconciliation (2026-09-28, ADR-145).** The recorded obligations above are obligations, not completions: the S3 spine rows (HUMAN-H4, P32.22a, HUMAN-H5, P32.23) are OPEN under `D-R10-HUMAN-1`/`D-R6.1-EVAL` per the operator's 2026-10-19 wholesale-deferral dispatch amendment; the evaluation machinery is landed but runs `mode=shadow` (`eval-confidence/1`, `applied=[]`, `awaiting_humans`) and never promotes without the recorded activation decision; no human label exists and none may be fabricated. The release candidate `p-17b713…` (identity `sha256:bc20d4bf…` over frozen snapshot `sha256:138714a6…`) carries `evaluation.status=deferred` on the provisional basis and was published only inside the bounded staging registry — no production exposure exists. GATE-G3 exercised HG-11 under the explicitly reduced scope recorded above (signed 2026-10-19); the bounded staging publication was verified and rollback-rehearsed (`sig.release-publish-verification/1` pass 25/25, ADR-144). The intake receiver is built and deliberately non-operational — `[intake].operational=false`; `/intake/new` and `POST /intake/v1/reports` return `503 receiver_not_operating` (`D-P32.16-1`). GATE-ACCEPT's signature exists (`ACCEPT-R10`, signed 2026-09-28) — it accepts the capstone register *as presented* and closes no deferred row. Production publication (`D-R10-PUBLISH-1`), the hosted recovery/production candidate (`D-R10-LIVE-1`, `D-P32.23a-1`), source rights (`D-R10-SOURCES-1`), human labels and review, and `SIG-MEM-004` (scheduled to P33.8) all remain owed.", ""]
    result[ROOT / "docs/research/_meta/spec_src/96b_partXI_s55_six_streams.md"] = "\n".join(s)
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "section", "level", "owner", "contract", "status", "verification"])
    for rid, r in plan["requirements"].items():
        t = owners[rid]
        writer.writerow([rid, r["section"], r["level"], t["id"], "docs/tickets/" + t["filename"], "MISSING", " | ".join(t["acceptance"])])
    result[HERE / "REQUIREMENTS.csv"] = out.getvalue()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = json.loads((HERE / "PLAN.json").read_text())
    errors = []
    for path, body in outputs(plan).items():
        if args.check:
            if not path.exists() or path.read_text() != body:
                errors.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
    if errors:
        print("Stale generated planning artifacts: " + ", ".join(errors))
        return 1
    print(f'Planning artifacts {"verified" if args.check else "rendered"}: {len(plan["tickets"])} contracts, {len(plan["requirements"])} requirements')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
