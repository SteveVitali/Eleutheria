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
"""

__version__ = "0.0.0"
