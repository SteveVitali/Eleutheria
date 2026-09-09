<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# `docs/` — map of the SIG documentation tree

Everything a reader needs about the Surveillance Infrastructure Graph lives here: the
specification and the research base behind it, the decisions taken during the build, the
governance and safety policies, and the committed record of how the repository was built.

Each subtree has a **mode** that fixes how it may change. This matters because much of
`docs/` is *evidence* — generated artifacts, frozen research, append-only registers and
historical records — and editing those by hand would falsify the record. Only the *living*
docs are edited in place.

| Mode | What it means | How it changes |
|---|---|---|
| **generated** | a build artifact assembled from source | edit the source + regenerate; never hand-edit the output |
| **frozen** | a captured evidence cache, not maintained further | not edited; corrections are recorded elsewhere (Appendix G / spot-checks) |
| **append-only** | a spec-mandated register or immutable-decision record | add new rows/records; never rewrite a landed entry |
| **historical record** | a committed record of what happened during the build | not rewritten; only broken references are repaired |
| **living** | a document kept in sync with the code | edited in place, minimal diffs, every claim verified |

## Top-level entries

| Entry | Mode | What it is / how to change it |
|---|---|---|
| [`1_deep_research_overview.md`](./1_deep_research_overview.md) | **frozen** | The source outline (landscape synthesis + project definition) the spec supersedes. Historical input; not edited. |
| [`2_canonical_design_spec.md`](./2_canonical_design_spec.md) | **generated** | The canonical design & implementation specification. Assembled by `sh docs/research/_meta/spec_src/BUILD.sh` from the section sources — **never hand-edited** (SIG-ENG-003). Change a requirement in `docs/research/_meta/spec_src/*.md` + an ADR. |
| [`adr/`](./adr/) | **append-only** | Architecture Decision Records (Appendix F). A decision is immutable; a change is a **new** ADR (SIG-ENG-003). Only the index [`adr/README.md`](./adr/README.md) is living, and every new ADR adds an index row + an Appendix F row in the same PR (SIG-ENG-039). |
| [`build/`](./build/) | **historical record** | Durable build memory — planning ledger, build index, decision memo, coverage matrix, capstone/backlog/reconciliation reports, integration plan and release notes. Records of what happened; not rewritten. The index [`build/README.md`](./build/README.md) is living. See [`build/DOCS_REFRESH_REPORT.md`](./build/DOCS_REFRESH_REPORT.md) for the docs audits. |
| [`governance/`](./governance/) | **living** | The adopted governance & safety policies (takedown/corrections/suppression, Code of Conduct, anti-misuse, contributor safety, …). They adopt the spec's Part VIII policy; to change a requirement, amend the spec via an ADR. See [`governance/README.md`](./governance/README.md). |
| [`research/`](./research/) | **frozen** | The evidence base for the spec — thirteen research workstreams plus `_meta/` (traceability, gap analysis, spot-checks, and the spec section sources under `_meta/spec_src/`). A frozen cache; corrections are recorded in Appendix G and `_meta/LEAD_SPOTCHECKS.md`, not by editing findings. The index [`research/README.md`](./research/README.md) is living. |
| [`risk_register.md`](./risk_register.md) | **append-only** | The spec-mandated risk register (§53, SIG-ENG-031). Each ticket appends its phase's risks + compensating controls; landed entries are not rewritten. |
| [`slice/`](./slice/) | **historical record** | The P06.1 vertical-slice hardness precondition and retrospective. A record of that slice; only broken references are repaired, never its findings. |
| [`studies/`](./studies/) | **living** | Standalone studies referenced by tickets (e.g. the sous-surveillance.net → OSM import study, P18.2). Kept in sync with the code that reads their machine-readable form. |
| [`tickets/`](./tickets/) | **historical record** | The ordered ticket backlog — the build's committed contract record ([`tickets/00_MANIFEST.md`](./tickets/00_MANIFEST.md) is the order; each `PXX.Y` file is one ticket's contract). Executed contracts; not rewritten. |
| [`traceability.md`](./traceability.md) | **append-only** | The spec-mandated traceability record: requirement → where it is implemented → the test that proves it. Each ticket appends its section; landed entries are not rewritten. |

## Where to start

- **Run it / find your way around** → the repository [`README.md`](../README.md) (`make check`, the packages, the run modes, releases).
- **Contribute** → [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`governance/`](./governance/).
- **Understand the design** → [`2_canonical_design_spec.md`](./2_canonical_design_spec.md); the decisions behind it → [`adr/`](./adr/).
- **See how it was built** → [`build/`](./build/) and [`tickets/00_MANIFEST.md`](./tickets/00_MANIFEST.md).
