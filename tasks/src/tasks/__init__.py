# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `tasks` package: the research-task coordination engine (§33).

The engine that turns a detected gap into coordinated, resolvable work — tasks as
data with a testable closing condition, a lifecycle with auto-invalidation, a
disposition vocabulary that lets the queue shrink, non-exclusive expiring geographic
queues, anti-abuse, and SIG's own local-group registry. The concrete detector
*catalog* (§33.2) is P10.2, registered against this engine's DSL.

* :mod:`tasks.vocabulary` — the controlled enums (assignee, disposition, status) and
  the §33.3 lifecycle transition table.
* :mod:`tasks.spec` — the detector specification language: `TaskType` as data and the
  `TaskTypeRegistry` that refuses an untestable closing condition (SIG-TASK-001/002).
* :mod:`tasks.lifecycle` — the `ResearchTask` state machine, auto-invalidation, and
  the `TaskPool` (duplicate suppression, claim timeout, per-subject rate limiting;
  SIG-TASK-005/006/007/013).
* :mod:`tasks.dispositions` — the disposition→data bridge:
  `resolved_no_evidence_exists` writes a `CoverageRecord` (SIG-TASK-008/009).
* :mod:`tasks.geographic` — expiring, non-exclusive geographic claims (SIG-TASK-010/011).
* :mod:`tasks.recognition` — qualitative recognition; the volume leaderboard is an
  executable refusal (SIG-TASK-012).
* :mod:`tasks.groups` — the SIG-owned local-group registry (SIG-TASK-014).
* :mod:`tasks.catalog` — the concrete §33.2 catalog (P10.2): the 34 task types
  registered against the DSL, and the §31 contradiction-detector→task map
  (SIG-TASK-003/004).
* :mod:`tasks.records_request` — records-request generation (§36, P10.3): the
  51-jurisdiction records-law reference table, emit-with-the-correct-statute,
  operationally-binding residency routing into the geographic queue + a coverage
  fact, versioned templates with measured success rates, and the consent gate
  (SIG-TASK-015/016/016a/016b/017/018).

The contributor system (§34, P16.1) — write tiers, onboarding, safety, and
poisoning resistance:

* :mod:`tasks.contributor` — the five-tier write model (scope + review per tier),
  the L0-entry and no-claim-without-provenance rules, the pseudonymity guarantee,
  and the `Person`-creation gate (SIG-CONTRIB-001/002/006).
* :mod:`tasks.submission` — contributor submissions enter at L0 as evidence,
  device observations route to OSM/DeFlock, and the PII-minimisation posture:
  no contributor real name / device id / precise geolocation, and operational
  logs that purge past a short window (SIG-CONTRIB-002/004/005).
* :mod:`tasks.onboarding` — the two onboarding paths and the moderated
  usability-study harness that gates a ≤10-minute median over an ontology-naïve
  cohort (SIG-CONTRIB-003).
* :mod:`tasks.revert` — revert a contribution as a unit, recorded as a new
  append-only assertion that deletes nothing (SIG-CONTRIB-009; the §16.6 spine).
* :mod:`tasks.poisoning` — vandalism/poisoning resistance: anomaly routing that
  never auto-rejects and guards false absence equally, the vendor
  operating-territory check, the no-SIG-caused-mass-revert refusal, and the
  visual-weight discipline (SIG-CONTRIB-010/011/011a/011b/011c).

Contribution back to the ecosystem (§35, P16.2):

* :mod:`tasks.contribution` — the human-mediated OSM suggestion workflow: a
  MapRoulette cooperative challenge proposes a specific tag change a mapper applies
  in their own account (no direct automated OSM writes), the declared changeset
  hashtag wired to the §7 leverage metric, the contribution-path licence gate
  applied before a suggestion is rendered, per-project correction channels, and the
  Organised Editing activity disclosure (SIG-CONTRIB-014/015/016d/016e/016f/016g/018).
"""

__version__ = "0.0.0"
