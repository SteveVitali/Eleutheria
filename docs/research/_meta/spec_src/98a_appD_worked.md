# Appendix D — Worked example: the Example City dossier, fully traced

This appendix demonstrates that the specification can produce the outline's Appendix B object
(OL-B-01…OL-B-12), and — more importantly — shows how the machinery changes what that object says.

## D.1 The outline's object

The outline presents a dossier in which `contracted_quantity: 42`, `portal_reported_quantity: 38`,
and `osm_mapped_quantity: 31`, with a research gap "reconcile 42 contract units vs 38 portal units."
It presents this as a contradiction awaiting resolution.

## D.2 What SIG actually produces

**These are not three answers to one question. They are three answers to three questions, plus one
genuine finding.**

| Predicate | Value | Source | R · D · I · C | W | Resolution |
|---|---|---|---|---|---|
| `contracted_device_count` | **42** | Executed contract, signed 2025-04-03 | R1 · D1 · I1 · C1 (IMMUTABLE) | **W4** | RESOLVED · CONFIRMED · UNCONTESTED · CURRENT |
| `active_device_count` | **38** | Portal capture 2026-07-15 | R2 · D1 · I1 · C1 | **W3** | RESOLVED · STRONGLY_SUPPORTED · MINOR_DISAGREEMENT · CURRENT |
| ↳ *same contract, for this predicate* | *42* | Executed contract | R1 · **D5** · I1 · C3 | **W1** | Dissenting, retained, not resolving |
| `mapped_device_count` | **31** | OSM, 2026-08-20 | R5 · D3 · I1 · C1 | W2 | RESOLVED — **lower bound only** |

The contract does not "lose" to the portal. It **wins its own predicate at W4** and is merely weak
evidence (D5, capped at W1) for a different predicate — current activity — that it was never
evidence for.

**The rationale SIG emits, quotable verbatim:**

> "38 active devices, as reported by the agency's transparency portal captured 2026-07-15. The
> portal is the most direct available source for currently active devices. The executed contract's
> figure of 42 is recorded separately as the contracted quantity; it is not evidence of the active
> count. 31 devices are independently mapped, which is a lower bound on the physical population."

**The genuine findings**, which become research tasks:

- `unresolved_delta(contracted=42, active=38) = 4` → task #1: were four never installed, or removed?
- `gap(active=38, mapped=31) ≥ 7` → task #2: locate and map at least seven devices.

## D.3 Where the outline's dossier understates the situation

| Outline field | SIG's rendering | Why |
|---|---|---|
| `status: active` | Four tracks: `procurement=contracted`, `physical=installed`, `operational=active`, `authorization=unknown` | §13.4 — one enum cannot carry this |
| `retention: 30 days` | `policy_written_retention_days` vs `configured_retention_days` vs `vendor_default_retention_days`, each with its own evidence | §29.5, P10 |
| `sharing.outgoing_configured: 147` | 147 **configured-access** edges as observed 2026-07-14 — never "currently shares with 147" | SIG-TIME-005, §12.2 |
| `national_search_observed: true` | Split: `configured_access` (national lookup enabled) vs `observed_use` (a national search occurred) | §12.2 |
| `usage.searches_last_30d: 412` | A **windowed** predicate with explicit bounds, exempt from currency decay for its window, and never rendered as a current rate | SIG-RECON-011 |
| `policies.immigration_enforcement.configuration_evidence: unknown` | Rendered as `not_researched` vs `searched_not_found` — with sources searched | §9.5, SIG-UI-012 |
| `physical_assets.unknown_operator_near_jurisdiction: 4` | Candidate attributions at L4, labelled `probable`, never written to the asset | §29.2, §30.4 |

## D.3a The second worked object: a local research-gap report

The outline's other worked example (OL-3-06) is a *research-gap* object for a jurisdiction, and it
is what a local group receives. It is produced by the detectors of §33.2, not hand-assembled:

| Outline gap statement | Producing detector | Disposition available |
|---|---|---|
| "Contract indicates 78 cameras" | — (a resolved `contracted_device_count`, W4) | — |
| "OSM currently has 61 probable ALPR devices" | — (a resolved `mapped_device_count`, lower bound) | — |
| "Portal reports 75" | — (a resolved `active_device_count`) | — |
| **"14 OSM devices have unknown operator"** | #5 orphaned device | `resolved_evidence_found` / `resolved_no_evidence_exists` |
| **"Latest contract amendment is missing"** | **#33 contract amendment chain incomplete** | `resolved_evidence_found` / `blocked_fee` / `blocked_access_denied` |
| **"Sharing snapshot is 94 days old"** | **#34 sharing snapshot stale** — 94 days exceeds the FAST 4-month half-life boundary at `C2`→`C3` | `resolved_evidence_found` |
| (implied) 75 reported vs 61 mapped | #1 missing physical devices | `resolved_evidence_found` |
| (implied) 78 contracted vs 75 active | Camera-count reconciliation delta (§29.1) | — |

Two things this demonstrates that the outline's version does not:

- **Every gap is a typed task with a defined closing condition and a disposition vocabulary**, so a
  local group can record "we searched and the record does not exist" and have that become a
  `CoverageRecord` rather than leaving the task open forever (§33.4, SIG-TASK-009).
- **The three counts are not in conflict.** 78 contracted, 75 active, 61 mapped are three
  predicates. The findings are the *deltas* — 3 unexplained between contracted and active, and at
  least 14 between active and mapped — not a disagreement to be adjudicated.

## D.4 The provenance chain for one fact

For "38 active devices", every link is traversable in both directions:

```
Source            transparency portal for this agency  [rights: UNDETERMINED → not redistributable]
 └─ Artifact      portal page, stable_locator = <slug>, capture_status = captured
     └─ Capture   sha2-256 multihash …, retrieved 2026-07-15T14:03Z, WACZ + screenshot + HTML
         └─ Extraction   html_selector v2.3.1, run_id …, review_status = sampled_ok
             └─ Claim    active_device_count = 38
                         raw_value = "38", locator = {selector: "...", text_span: [412,414]}
                         observed_at = 2026-07-15, valid_*_kind = unknown/ongoing
                         R2 · D1 · I1 · C1 → W3
                 └─ Resolution   value 38, STRONGLY_SUPPORTED / MINOR_DISAGREEMENT / CURRENT
                                 ruleset v2026.3, resolver v1.4.0, decided_by auto
                     └─ Dossier  §1 row, with the ⊕⊕⊕◯ glyph and a ≠ marker
```

A journalist clicking the 38 reaches the capture, the highlighted span, the extraction method, the
competing claims, and the rule that fired. That is OL-24-18 discharged.

## D.5 Appendix C pathways

All three of the outline's illustrative pathways (OL-C-01…OL-C-03) are expressible, with edge types
sharper than the outline's prose:

**Pathway 1 — private camera to fusion center.**
`Business —owner→ Camera` · `Camera —enrolls_asset_into→ Integration Platform` ·
`Platform —federates_search_to→ RTCC` · `RTCC —operated_by→ Police Department` ·
`Department —participates_in→ Fusion Center`.
Note `enrolls_asset_into` rather than "streams_via": the object is a *device*, and whether a live
feed follows is a separate, evidenced fact with its own consent gate.

**Pathway 2 — roadside ALPR to federal access.**
`ALPR —operated_by→ Department` · `Department —hosts_data_for→ Vendor network` ·
`Vendor network —is_queryable_by→ {Neighboring PD, State Police, Federal organization}`, each edge
directional, scoped, dated, and separately evidenced — and each distinguishing configured access
from observed use.

**Pathway 3 — commercial data.**
`Department —subscribes_to→ Investigative platform` · `Platform —resells_data_from→ Aggregating
broker` · `Broker —resells_data_from→ Ad-tech source`. The chain has **six layers, not five**: the
aggregating broker and the productizing platform are routinely different companies, which the
outline's five-step diagram collapses.

**And the question the pathways exist to answer** (OL-C-04) — *what chain of institutions turns an
observation into searchable power?* — is the access-path closure of §30.2, with its hop limits,
non-composition rules, minimum-over-path confidence, and speculative labelling.

---
