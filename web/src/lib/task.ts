// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Turning a clicked absence hatch into a research task (SIG-UI-007).
 *
 * A gap is an invitation, not an admission: every absence cell links (a plain GET,
 * no JavaScript — SIG-UI-036/037) to the task-intake page carrying the subject,
 * predicate, and absence kind. This module is the pure logic that page uses to
 * derive a well-formed research-task descriptor from those parameters. The shape
 * mirrors the engine's `research_task` row (tasks/src/tasks/vocabulary.py,
 * lifecycle.py): a new task starts in `GENERATED`, is keyed for de-duplication on
 * `(task_type, subject_id)`, and carries the absence kind as its rationale.
 */

import { ABSENCE_KINDS, ABSENCE_KIND_META } from "./epistemic";
import type { AbsenceKind } from "./epistemic";

/** The lifecycle state a freshly generated task starts in (§33.3, TaskStatus.GENERATED). */
export const INITIAL_TASK_STATUS = "generated";

/** The task type an absence-generated task declares (assignee_class routing happens server-side). */
export const ABSENCE_TASK_TYPE = "research_absence";

export interface ResearchTaskDescriptor {
  task_type: string;
  status: string;
  subject_id: string;
  predicate_id: string;
  absence_kind: AbsenceKind;
  rationale: string;
  /** The `(task_type, subject_id)` duplicate-suppression key (SIG-TASK-007). */
  dedup_key: [string, string];
}

/** The parameters the intake page reads from the hatch link's query string. */
export interface AbsenceTaskParams {
  subject_id: string;
  predicate_id: string;
  absence_kind: AbsenceKind;
  /** The human label of the predicate, for the rationale text (optional). */
  predicate_label?: string;
}

function isAbsenceKind(value: string): value is AbsenceKind {
  return (ABSENCE_KINDS as readonly string[]).includes(value);
}

// The hatch → intake link is a plain GET with NO client JavaScript (SIG-UI-036/037),
// and the shell is a fully static build — so the intake target must be a real,
// pre-generated page, not a query string a client script reads. The task parameters
// are therefore encoded into a single URL path SEGMENT (a slug), and the intake
// route is statically generated for every taskable absence the shell links to
// (see `getStaticPaths` on `pages/task/new/[slug].astro`, driven by the fixture
// registry `TASKABLE_ABSENCES`). `~` is the field separator; it never occurs in a
// subject/predicate id, and the whole segment is percent-encoded regardless.
// The slug is a base64url encoding of the params tuple. base64url is URL-safe AND
// filesystem-safe (only [A-Za-z0-9_-]), so it is safe as an Astro static-route
// segment on any OS and needs no extra percent-encoding in the href — unlike a raw
// `subject~predicate~kind` string, whose `:` is invalid on some filesystems and
// whose separator could be truncated by a value that happens to contain it.

function b64urlEncode(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(slug: string): string {
  const b64 = slug.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(b64);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

/**
 * The slug for absence params — a base64url-encoded tuple. This is the value
 * passed to Astro's `getStaticPaths` as the `[slug]` param and handed back by
 * `Astro.params.slug`; it is URL- and filesystem-safe as-is.
 */
export function taskSlug(params: AbsenceTaskParams): string {
  const tuple = [params.subject_id, params.predicate_id, params.absence_kind];
  if (params.predicate_label) tuple.push(params.predicate_label);
  return b64urlEncode(JSON.stringify(tuple));
}

/**
 * Decode a task slug back into params, or return null when it is malformed or the
 * absence kind is not one of the four (§9.5). A null result is the intake page's
 * cue to render an error rather than fabricate a task.
 */
export function decodeTaskSlug(slug: string): AbsenceTaskParams | null {
  let tuple: unknown;
  try {
    tuple = JSON.parse(b64urlDecode(slug));
  } catch {
    return null;
  }
  if (!Array.isArray(tuple)) return null;
  const [subject, predicate, kind, label] = tuple as unknown[];
  if (
    typeof subject !== "string" ||
    typeof predicate !== "string" ||
    typeof kind !== "string" ||
    !isAbsenceKind(kind)
  ) {
    return null;
  }
  return {
    subject_id: subject,
    predicate_id: predicate,
    absence_kind: kind,
    ...(typeof label === "string" && label ? { predicate_label: label } : {}),
  };
}

/** Build a well-formed, GENERATED research-task descriptor from absence params. */
export function buildResearchTask(params: AbsenceTaskParams): ResearchTaskDescriptor {
  const meta = ABSENCE_KIND_META[params.absence_kind];
  const subjectPredicate = params.predicate_label ?? params.predicate_id;
  return {
    task_type: ABSENCE_TASK_TYPE,
    status: INITIAL_TASK_STATUS,
    subject_id: params.subject_id,
    predicate_id: params.predicate_id,
    absence_kind: params.absence_kind,
    rationale: `Research ${subjectPredicate} for ${params.subject_id}: ${meta.label.toLowerCase()} — ${meta.meaning}`,
    dedup_key: [ABSENCE_TASK_TYPE, params.subject_id],
  };
}

/**
 * The href a clickable absence hatch points at (a no-JS GET to the intake page).
 * The base64url slug is already URL-safe, so no percent-encoding is needed and the
 * link always resolves to the page `getStaticPaths` generated for the same slug.
 */
export function absenceTaskHref(params: AbsenceTaskParams): string {
  return `/task/new/${taskSlug(params)}/`;
}
