// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.63 (K11 RQ-04 / SIG-RQ-007, SIG-RQ-010) — the records-request drafts
 * surface: `sig.records-request-drafts/1` rows persisted into the export
 * (DRAFT state), rendered and downloadable on the task pages, and bundled
 * per place under `/research-queue/drafts/`.
 *
 * **DRAFT, NEVER SEND.** A draft is a document the operator (or a
 * contributor) may file by hand — SIG has no transmit path and never fires
 * one (SIG-RQ-007; ADR-171; `D-R7.2-SEND` stays operator-gated). The row
 * shape mirrors the detector's own `records_requests.json` artifact
 * (`tasks.detect.RecordsRequestDraft.as_dict`): the statute, citation,
 * template version, residency posture and request text are verbatim —
 * SIG-TRANSP: the draft text is verbatim-recorded, never paraphrased.
 */

import type { ResearchTaskCard } from "./research-queue";
import { placeSlugOf, placeNameOf, tasksForPlace } from "./queue-hub";

/** The drafts artifact schema id (the `web/records_request_drafts.json` export artifact). */
export const DRAFTS_SCHEMA = "sig.records-request-drafts/1";

/** The page anchor the draft block renders under (`/task/<handle>/#records-request-draft`). */
export const DRAFT_ANCHOR = "records-request-draft";

/**
 * SIG-RQ-010 — no single queue download file larger than 25 MB (the same cap
 * `task_export.SHARD_MAX_BYTES` enforces export-side). Place bundles split
 * into `…--part-<n>-of-<m>` parts at draft boundaries when they would exceed
 * it; a single draft over the cap is a data defect and fails loud.
 */
export const DRAFT_BUNDLE_MAX_BYTES = 25 * 1024 * 1024;

/**
 * The `records_requests.json` row shape (`tasks.detect.RecordsRequestDraft.as_dict`,
 * verbatim) — the export's DRAFT persistence shape. `status` is always
 * `"drafted"`: there is no other legal value and no transmit path exists.
 */
export interface RecordsRequestDraft {
  status: string;
  task_type: string;
  subject_id: string | null;
  jurisdiction_id: string | null;
  trigger_kind: string | null;
  trigger_ref: string | null;
  records_law_key: string;
  jurisdiction_name: string;
  target_agency: string;
  records_contact: string;
  record_type: string;
  statute_name: string;
  statutory_citation: string;
  records_sought: string;
  draft_body: string;
  response_deadline: string;
  appeal_path: string;
  residency_restricted: boolean;
  routing_note: string;
  template_version: string;
  template_set_version: string;
  table_version: string;
}

/** The `web/records_request_drafts.json` envelope — the detector's payload shape. */
export interface RecordsRequestDraftsEnvelope {
  schema?: string;
  status?: string;
  drafted?: number;
  /** Always 0 — sending is operator-gated; any other value fails the build. */
  sent?: number;
  requests: RecordsRequestDraft[];
}

// --- The never-send pin ----------------------------------------------------- //

/**
 * Fail LOUD if a draft row is anything but `status: "drafted"` — a row
 * claiming `sent`/`filed` is a contract violation (SIG-RQ-007, never send),
 * never a render state.
 */
export function assertDraftsNeverSent(
  drafts: readonly RecordsRequestDraft[],
  where = "records_request_drafts",
): void {
  for (const [i, d] of drafts.entries()) {
    if (d.status !== "drafted") {
      throw new Error(
        `${where}#${i + 1}: a records-request draft carries status "${d.status}" — ` +
          "DRAFT, NEVER SEND is violated (SIG-RQ-007)",
      );
    }
  }
}

/**
 * Validate the export-mode envelope (`web/records_request_drafts.json`).
 * `sent` must be absent-or-0 — a nonzero value means the envelope claims a
 * transmission, which the surface refuses to render (SIG-RQ-007).
 */
export function parseDraftsEnvelope(parsed: unknown, path: string): RecordsRequestDraft[] {
  const o = parsed as RecordsRequestDraftsEnvelope | null;
  if (o === null || typeof o !== "object") {
    throw new Error(`${path}: expected a ${DRAFTS_SCHEMA} envelope object`);
  }
  if (!Array.isArray(o.requests)) {
    throw new Error(`${path}: expected a "requests" array (${DRAFTS_SCHEMA})`);
  }
  if (o.sent !== undefined && o.sent !== 0) {
    throw new Error(
      `${path}: the drafts envelope carries sent=${String(o.sent)} — ` +
        "SIG sends nothing; a nonzero sent count can never publish (SIG-RQ-007)",
    );
  }
  const rows = o.requests;
  assertDraftsNeverSent(rows, path);
  return rows;
}

// --- Draft ↔ task matching -------------------------------------------------- //

/** The two assignee classes a records-request draft can serve (§36; SIG-RQ-007). */
export const DRAFT_ROLES: ReadonlySet<string> = new Set([
  "records_requester",
  "document_reviewer",
]);

export function isDraftRole(assignee: string): boolean {
  return DRAFT_ROLES.has(assignee);
}

/**
 * The draft for a task — matched on the SIG-TASK-007 dedup key
 * `(task_type, subject_id)`, the same pair the detector drafts per task.
 * `null` when the export publishes no draft for the task (honest absence —
 * the page names it rather than guessing).
 */
export function draftForTask(
  card: ResearchTaskCard,
  drafts: readonly RecordsRequestDraft[],
): RecordsRequestDraft | null {
  for (const d of drafts) {
    if (d.task_type === card.task_type && d.subject_id === card.subject_id) return d;
  }
  return null;
}

// --- The rendered + downloadable text --------------------------------------- //

/**
 * The never-send line (K11 §5.3 verbatim): rendered once per page (SIG-UI-144
 * — the full sentence appears exactly once in `main`).
 */
export const NEVER_SENT_LINE = "SIG sends nothing; you file it; the filer is left blank.";

/** The residency line a draft carries — the routing note verbatim, or the honest open posture. */
export function residencyLine(draft: RecordsRequestDraft): string {
  if (draft.residency_restricted) return draft.routing_note;
  return "No residency restriction is recorded for this statute — any member of the public may file it.";
}

/** The route path a task's `.txt` draft download serves at (base-relative). */
export function draftTxtHref(handle: string): string {
  return `task/${handle}.draft.txt`;
}

/**
 * The downloadable `.txt` for one task's draft — the DRAFT banner, the
 * statute + citation, the template versions, the residency posture, the
 * never-send line, then the request body VERBATIM (SIG-TRANSP — the draft
 * text is verbatim-recorded).
 */
export function draftTxt(card: ResearchTaskCard, draft: RecordsRequestDraft): string {
  const lines = [
    "DRAFT PUBLIC-RECORDS REQUEST — never sent by SIG (SIG-TASK-018)",
    "=".repeat(72),
    "",
    `Task:           ${card.title ?? card.subject_label}`,
    `Handle:         ${card.handle ?? card.task_id ?? "(unhandled)"}`,
    `Statute:        ${draft.statute_name} (${draft.statutory_citation})`,
    `Agency:         ${draft.target_agency}`,
    `Records contact:${" "}${draft.records_contact}`,
    `Template:       ${draft.record_type} ${draft.template_version} (set ${draft.template_set_version}, law table ${draft.table_version})`,
    `Response due:   ${draft.response_deadline}`,
    `Appeal path:    ${draft.appeal_path}`,
    `Residency:      ${residencyLine(draft)}`,
    "",
    "Records sought:",
    `  ${draft.records_sought}`,
    "",
    `${NEVER_SENT_LINE} Filing is a public act attributable to the filer`,
    "(SIG-TASK-018). This is a template, not legal advice.",
    "",
    "-".repeat(72),
    "",
    draft.draft_body,
    "",
  ];
  return lines.join("\n");
}

// --- Per-place bundles (SIG-RQ-010: ≤ 25 MB per file) ------------------------ //

export interface DraftBundleEntry {
  card: ResearchTaskCard;
  draft: RecordsRequestDraft;
}

/** One place's draft bundle — the facet's name and the (card, draft) pairs it covers. */
export interface DraftBundle {
  slug: string;
  placeName: string;
  entries: DraftBundleEntry[];
}

/**
 * The per-place draft bundles — one per place facet that has ≥ 1 task with a
 * draft, covering the place AND its slug-path children (the same coverage the
 * place queue page has, `tasksForPlace`).
 */
export function placeDraftBundles(
  cards: readonly ResearchTaskCard[],
  drafts: readonly RecordsRequestDraft[],
  facets: readonly { slug: string; name: string }[],
): DraftBundle[] {
  const out: DraftBundle[] = [];
  for (const facet of facets) {
    const entries = tasksForPlace(cards, facet.slug)
      .map((card) => ({ card, draft: draftForTask(card, drafts) }))
      .filter((e): e is DraftBundleEntry => e.draft !== null);
    if (entries.length > 0) {
      out.push({ slug: facet.slug, placeName: placeNameFor(facet, cards), entries });
    }
  }
  return out;
}

function placeNameFor(
  facet: { slug: string; name: string },
  cards: readonly ResearchTaskCard[],
): string {
  const card = cards.find((c) => placeSlugOf(c) === facet.slug);
  return card ? placeNameOf(card) : facet.name;
}

/** The route path a place's draft bundle (or one part of it) serves at. */
export function draftBundleHref(slug: string, part?: { n: number; of: number }): string {
  const suffix = part && part.of > 1 ? `--part-${part.n}-of-${part.of}` : "";
  return `research-queue/drafts/${slug}${suffix}.txt`;
}

export interface DraftBundleFile {
  /** The rest-param route slug (`usa/ok` or `usa/ok--part-1-of-3`). */
  routeSlug: string;
  /** The site-relative file path (`research-queue/drafts/<routeSlug>.txt`). */
  path: string;
  /** The bundle's place label. */
  placeName: string;
  /** How many drafts this part carries. */
  drafts: number;
  /** The `.txt` body. */
  text: string;
}

const BUNDLE_RULE = "-".repeat(72);

function bundleHeader(bundle: DraftBundle, part?: { n: number; of: number }): string {
  const partNote =
    part && part.of > 1 ? ` — part ${part.n} of ${part.of} (sharded, ≤ 25 MB per file)` : "";
  return [
    `DRAFT PUBLIC-RECORDS REQUESTS — ${bundle.placeName}${partNote}`,
    "=".repeat(72),
    "",
    `${bundle.entries.length} drafted records request${bundle.entries.length === 1 ? "" : "s"} for tasks scoped to ${bundle.placeName} and the places under it.`,
    `${NEVER_SENT_LINE} Every request below is a DRAFT (status: drafted); 0 sent.`,
    "A template, not legal advice — the statute each draft cites is the law of record.",
    "",
  ].join("\n");
}

function bundleSection(entry: DraftBundleEntry, index: number): string {
  const { card, draft } = entry;
  return [
    `${BUNDLE_RULE}`,
    `[${index}] ${card.title ?? card.subject_label}`,
    `    Task: ${card.handle ?? card.task_id ?? "(unhandled)"} · ${card.task_type}`,
    `    Statute: ${draft.statute_name} (${draft.statutory_citation})`,
    `    Agency: ${draft.target_agency}`,
    `    Residency: ${residencyLine(draft)}`,
    `    Template: ${draft.record_type} ${draft.template_version} (set ${draft.template_set_version}, law table ${draft.table_version})`,
    "",
    draft.draft_body,
    "",
  ].join("\n");
}

function byteLen(text: string): number {
  return new TextEncoder().encode(text).length;
}

/**
 * Materialise every place bundle's `.txt` files. A bundle under the cap is
 * one file (`<slug>.txt`); over the cap it splits at draft boundaries into
 * `…--part-<n>-of-<m>` parts each ≤ `maxBytes` (SIG-RQ-010). A single draft
 * section over the cap throws — a 25 MB draft is a data defect, never a
 * truncated file.
 */
export function draftBundleFiles(
  bundles: readonly DraftBundle[],
  maxBytes: number = DRAFT_BUNDLE_MAX_BYTES,
): DraftBundleFile[] {
  const out: DraftBundleFile[] = [];
  for (const bundle of bundles) {
    const sections = bundle.entries.map((e, i) => bundleSection(e, i + 1));
    // Greedy boundary split — each section lands whole in one part.
    const parts: string[][] = [[]];
    for (const section of sections) {
      if (byteLen(section) > maxBytes) {
        throw new Error(
          `draft bundle ${bundle.slug}: a single draft section is ${byteLen(section)} B, ` +
            `over the ${maxBytes} B cap (SIG-RQ-010) — a defect, never a truncated file`,
        );
      }
      const current = parts[parts.length - 1]!;
      const candidate = [...current, section].join(BUNDLE_RULE + "\n");
      const header = bundleHeader(bundle, { n: parts.length, of: parts.length });
      if (current.length > 0 && byteLen(header + candidate) > maxBytes) {
        parts.push([section]);
      } else {
        current.push(section);
      }
    }
    const of = parts.length;
    parts.forEach((sections_, i) => {
      const part = { n: i + 1, of };
      const text = bundleHeader(bundle, part) + sections_.join(BUNDLE_RULE + "\n");
      const routeSlug = of > 1 ? `${bundle.slug}--part-${i + 1}-of-${of}` : bundle.slug;
      out.push({
        routeSlug,
        path: draftBundleHref(bundle.slug, part),
        placeName: bundle.placeName,
        drafts: sections_.length,
        text,
      });
    });
  }
  return out;
}

/** The bundle list the hub's Downloads section renders (place label + files). */
export function draftBundleLinks(files: readonly DraftBundleFile[]): {
  placeName: string;
  files: { href: string; label: string; drafts: number }[];
}[] {
  const byPlace = new Map<string, { placeName: string; files: { href: string; label: string; drafts: number }[] }>();
  for (const f of files) {
    const row = byPlace.get(f.placeName) ?? { placeName: f.placeName, files: [] };
    const m = /--part-(\d+)-of-(\d+)\.txt$/.exec(f.path);
    row.files.push({
      href: f.path,
      label: m ? `part ${m[1]} of ${m[2]}` : ".txt",
      drafts: f.drafts,
    });
    byPlace.set(f.placeName, row);
  }
  return [...byPlace.values()];
}
