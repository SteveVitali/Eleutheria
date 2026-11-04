// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.62 (K11 RQ-03b / SIG-RQ-002, SIG-RQ-008, SIG-RQ-009) — the task detail
 * page model: `/task/<handle>/` (+ the `sig.task-page/1` JSON twin), the
 * `/task/<task_id>/` id-alias redirects, and the dossier gap→task resolver
 * every 'What we don't know' absence and typed-absence row resolves through.
 *
 * The §5.3 block contract (SIG-RQ-002): every block is a VALUE or a NAMED
 * ABSENCE — a task page never leaves a block blank and never invents a fact.
 * The copy templates here are agent-drafted (K11 §16 records them as such);
 * the data fields all read the `sig.queue-card/2` card verbatim.
 */

import type { ResearchTaskCard } from "./research-queue";
import type { QueueCampaign } from "./queue-hub";
import { typeLabel, roleLabel } from "./queue-hub";

export const TASK_PAGE_SCHEMA = "sig.task-page/1";

/** The route path a task handle serves at (base-relative, withBase()'d by callers). */
export function taskHref(handle: string): string {
  return `task/${handle}/`;
}

/** The JSON twin path (`/task/<handle>.json`). */
export function taskJsonHref(handle: string): string {
  return `task/${handle}.json`;
}

/** The route path a campaign handle serves at. */
export function campaignHref(handle: string): string {
  return `research-queue/campaign/${handle}/`;
}

// --- The K11 §5.3 block copy (agent-drafted, K11 §16) ------------------------ //

/** "Why it matters" — per-type plain language, keyed on task_type. */
export const WHY_IT_MATTERS: Record<string, string> = {
  missing_physical_devices:
    "Devices that exist in the record but not on the map are invisible to every count SIG publishes. Mapping them makes the inventory honest.",
  missing_contract:
    "The contract says what was bought, what it costs and when it renews. Without it the cost and accountability record stays incomplete.",
  conflicting_retention:
    "Two sources disagree about how long data is kept. Until the conflict resolves, every reader has to guess which number to believe.",
  stale_evidence:
    "The evidence behind this record has aged past its declared volatility class — the fact may have changed since SIG last looked.",
  orphaned_device:
    "A device with no recorded operator cannot be held to account — somebody runs it and the record does not say who.",
  new_sharing_node:
    "A new participant in a data-sharing network may extend who can see the data. Confirming it keeps the access record current.",
  vendor_replacement:
    "A vendor replacement changes who operates the system and who holds the data — the accountability chain needs the new name.",
  portal_disappeared:
    "A transparency portal that went offline removes a public evidence channel — finding out why tells you whether the record moved or vanished.",
  portal_appeared_no_deployment:
    "A new vendor portal with no recorded deployment may announce a system SIG has not yet counted.",
  contract_expiring:
    "A renewal decision is a moment when the contract — and the surveillance it pays for — can be questioned, changed or ended.",
  coverage_hole:
    "SIG's record has a hole here. Closing it is the difference between an inventory and a guess.",
  link_rot:
    "A source URL that stopped resolving takes the evidence trail with it — the claim needs a live or archived copy.",
};

export function whyItMatters(card: ResearchTaskCard): string {
  return (
    WHY_IT_MATTERS[card.task_type] ??
    `A task of type "${typeLabel(card.task_type)}" names a fact the record does not yet establish — closing it makes the public record more complete.`
  );
}

/** The "What's unknown" sentence — the absence kind in plain words. */
export function unknownNote(card: ResearchTaskCard): string | null {
  const detail = (card.trigger?.detail ?? {}) as Record<string, unknown>;
  const kind = detail["absence_kind"];
  const searched = Array.isArray(detail["sources_searched"])
    ? (detail["sources_searched"] as unknown[]).map(String)
    : [];
  if (kind === "not_researched") {
    return "SIG has not looked for this fact yet — nothing is recorded either way.";
  }
  if (kind === "searched_not_found" || kind === "no_evidence_found") {
    return `SIG looked and found nothing${
      searched.length > 0 ? ` — sources searched: ${searched.join(", ")}` : ""
    }.`;
  }
  if (kind === "unresolved") {
    return "The recorded evidence disagrees — the gap is open until the conflict resolves.";
  }
  const preds = card.predicate_ids ?? [];
  if (preds.length > 0) {
    return `The record does not establish ${preds.join(", ")} for this subject.`;
  }
  return null; // no absence kind recorded → the named-absence fallback
}

/** "Triggered by" — the materialized trigger in words (never a bare ref). */
export function triggerSentence(card: ResearchTaskCard): string {
  const t = card.trigger;
  if (!t) return "No trigger is recorded for this task — it may predate trigger recording.";
  const detail = (t.detail ?? {}) as Record<string, unknown>;
  const date =
    (detail["searched_at"] as string | undefined) ??
    (detail["observed_at"] as string | undefined) ??
    (detail["valid_from"] as string | undefined);
  const datePart = date ? ` (recorded ${String(date).slice(0, 10)})` : "";
  if (t.kind === "coverage") {
    const pred = detail["predicate_id"] ? `the predicate ${String(detail["predicate_id"])}` : "a predicate";
    return `A coverage detector recorded that ${pred} is absent for this subject${datePart}.`;
  }
  if (t.kind === "contradiction") {
    const ty = detail["contradiction_type"] ? ` (${String(detail["contradiction_type"])})` : "";
    return `A recorded contradiction${ty} names this subject — both evidence sides are kept visible${datePart}.`;
  }
  if (t.kind === "relationship") {
    const ak = detail["access_kind"] ? `${String(detail["access_kind"])} access` : "an access relationship";
    return `A sharing-network edge records ${ak} touching this subject${datePart}.`;
  }
  return `The detector recorded a ${t.kind} trigger${datePart}.`;
}

/** "How to act" — the per-role steps (agent-drafted, K11 §5.3). */
export function howToAct(card: ResearchTaskCard): string[] {
  const role = card.assignee_class;
  const closing = card.closing_condition;
  switch (role) {
    case "records_requester":
      return [
        "Read the closing condition and the evidence sought below.",
        "File the request with the agency named on this page — SIG sends nothing; you file it yourself.",
        closing,
      ];
    case "document_reviewer":
      return [
        "Read the closing condition and the evidence sought below.",
        "Review the documents the task names and report what they actually say.",
        closing,
      ];
    case "field_mapper":
      return [
        "Read the closing condition and check the place this task names.",
        "Record what you observe — a mapped observation is evidence.",
        closing,
      ];
    case "analyst":
      return ["Read the closing condition and work the analysis it asks for.", closing];
    case "local_group":
      return [
        "Read the closing condition — this task suits people close to the place it names.",
        closing,
      ];
    case "curator":
    case "developer":
      return ["This task is tooling or curation work — the closing condition names the fix.", closing];
    default:
      return ["Read the closing condition — it states what would close this task.", closing];
  }
}

// --- Status line ------------------------------------------------------------- //

/** "Open · unclaimed · anyone may work this task" — the K11 §5.3 status block. */
export function statusLine(card: ResearchTaskCard, claimedBy: string | null): string {
  const status = card.status ?? "generated";
  if (card.disposition) return `Closed · ${card.disposition}`;
  if (claimedBy) {
    return `Open · ${status} · ${claimedBy} claims priority — anyone may still work this task`;
  }
  return `Open · ${status} · unclaimed — anyone may work this task`;
}

// --- Related tasks ----------------------------------------------------------- //

/** Other tasks on the same subject, place or type (K11 §5.3's Related block). */
export function relatedTasks(
  card: ResearchTaskCard,
  cards: readonly ResearchTaskCard[],
): ResearchTaskCard[] {
  return cards.filter(
    (c) =>
      c !== card &&
      (c.subject_id === card.subject_id ||
        c.task_type === card.task_type ||
        (card.place?.slug !== undefined && c.place?.slug === card.place.slug)),
  );
}

// --- The sig.task-page/1 JSON twin ------------------------------------------- //

/** The machine-readable twin — the same fields the HTML page renders. */
export function taskPageTwin(
  card: ResearchTaskCard,
  opts: { claimedBy: string | null; related: readonly ResearchTaskCard[] },
): Record<string, unknown> {
  return {
    schema: TASK_PAGE_SCHEMA,
    handle: card.handle ?? null,
    task_id: card.task_id ?? null,
    title: card.title ?? card.subject_label,
    task_type: card.task_type,
    status: statusLine(card, opts.claimedBy),
    subject: {
      id: card.subject_id,
      label: card.subject_label,
      url: card.subject_url ?? null,
    },
    place: card.place ?? null,
    place_basis: card.place_basis ?? null,
    lane: card.lane ?? "research",
    assignee_class: card.assignee_class,
    effort_estimate: card.effort_estimate,
    geographic_scope: card.geographic_scope,
    jurisdiction: card.jurisdiction,
    closing_condition: card.closing_condition,
    evidence_sought: card.evidence_sought,
    predicate_ids: card.predicate_ids ?? [],
    dispositions: card.dispositions,
    trigger: card.trigger ?? null,
    priority: card.priority,
    generated_at: card.generated_at ?? null,
    detector_version: card.detector_version ?? null,
    disposition: card.disposition ?? null,
    related_handles: opts.related.map((c) => c.handle).filter((h): h is string => Boolean(h)),
  };
}

// --- The id-alias rows (/task/<task_id>/ → /task/<handle>/) ------------------ //

export interface TaskAlias {
  /** The task's canonical id (task_id — a UUID in a real export). */
  taskId: string;
  /** The handle the alias resolves to. */
  handle: string;
}

/**
 * The id-alias pairs — `/task/<task_id>/` redirects (301 where the include
 * runs) to the handle page (SIG-RQ-009). Derived from the cards in every
 * mode so the fixture corpus exercises the same seam the export's
 * `task_handles_history` artifact feeds. A card without a handle emits no
 * alias (it has no page to redirect to); a task_id equal to the handle is
 * skipped (the page IS the answer).
 */
/** The leading path separator — built, never a `"/"` literal site (SIG-REL-008). */
const LEAD = String.fromCharCode(47);

export function taskIdAliases(cards: readonly ResearchTaskCard[]): TaskAlias[] {
  const out: TaskAlias[] = [];
  const seen = new Set<string>();
  for (const c of cards) {
    if (!c.task_id || !c.handle || c.task_id === c.handle) continue;
    if (seen.has(c.task_id)) continue;
    seen.add(c.task_id);
    out.push({ taskId: c.task_id, handle: c.handle });
  }
  return out;
}

/**
 * `*_handles_history`-family rows for the task id-aliases — merged with the
 * export's artifact rows (rename history rides the artifact; the alias
 * derivation covers every mode). Dedup on `old`, artifact rows first so a
 * recorded rename is never overridden by a derivation.
 */
export function taskHandleRows(
  cards: readonly ResearchTaskCard[],
  artifactRows: readonly { old: string; target: string; note?: string }[],
): { old: string; target: string; note?: string }[] {
  const out: { old: string; target: string; note?: string }[] = [];
  const seen = new Set<string>();
  for (const r of artifactRows) {
    if (seen.has(r.old)) continue;
    seen.add(r.old);
    out.push(r);
  }
  for (const a of taskIdAliases(cards)) {
    const old = `${LEAD}task${LEAD}${a.taskId}${LEAD}`;
    if (seen.has(old)) continue;
    seen.add(old);
    out.push({
      old,
      target: `${LEAD}task${LEAD}${a.handle}${LEAD}`,
      note: "canonical task id → public handle",
    });
  }
  return out;
}

// --- The dossier gap → task resolver (SIG-RQ-008) ---------------------------- //

export interface GapRef {
  subject_id: string;
  predicate_id: string;
}

export type GapLink =
  | { kind: "task"; handle: string; href: string; title: string }
  | { kind: "campaign"; handle: string; href: string; title: string }
  | { kind: "none"; reason: string };

/**
 * Resolve a dossier gap to its task or campaign page — or the honest named
 * absence (SIG-RQ-008: the link resolves to the real page FOR THAT GAP or
 * states that none is queued; a guessed link is worse than a named absence).
 *
 * A research task matches when its subject and a named missing predicate
 * align with the gap's — the same (subject_id, predicate_id) pair the
 * coverage detector recorded (the gap and the card both derive from it).
 * A field-gap campaign matches on the missing predicate + member subject.
 * A gap with no queued task names that fact — the queue does not carry a
 * task for it in this release.
 */
export function resolveGapLink(
  gap: GapRef,
  cards: readonly ResearchTaskCard[],
  campaigns: readonly QueueCampaign[],
): GapLink {
  for (const c of cards) {
    if (
      c.subject_id === gap.subject_id &&
      (c.predicate_ids ?? []).includes(gap.predicate_id) &&
      c.handle
    ) {
      return {
        kind: "task",
        handle: c.handle,
        href: taskHref(c.handle),
        title: c.title ?? c.subject_label,
      };
    }
  }
  for (const camp of campaigns) {
    if (
      camp.predicate_id === gap.predicate_id &&
      camp.handle &&
      (camp.members ?? []).some((m) => m.subject_id === gap.subject_id)
    ) {
      return {
        kind: "campaign",
        handle: camp.handle,
        href: campaignHref(camp.handle),
        title: `${camp.predicate_id} campaign in ${camp.place?.name ?? "this place"}`,
      };
    }
  }
  return {
    kind: "none",
    reason: "The queue carries no task for this gap in this release — the absence stays named, never a guessed link.",
  };
}

// --- Campaign page helpers (K11 §5.4) ---------------------------------------- //

/** The campaign's "why it matters" line — per contribution kind. */
export function campaignWhy(campaign: QueueCampaign): string {
  if (campaign.contribution?.kind === "osm-field-gap") {
    return `The ${campaign.predicate_id} tag feeds "who runs this camera" — an unlabelled record cannot be attributed to an operator.`;
  }
  return `This field is missing on ${campaign.member_count} records — filling it makes the record attributable.`;
}

/** The member page slice (K11 §5.4's paginated subject list, ≤50 rows). */
export const CAMPAIGN_MEMBERS_PAGE = 50;
