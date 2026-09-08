// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The procurement / renewal watch as pure data + logic (§39.5).
 *
 * The actionable-timing half of P15.4. For every contract it surfaces the fields
 * SIG-UI-026 mandates — expiry, renewal window, notice deadline, approving body,
 * next scheduled meeting, and the replacement procurement if known — and it emits
 * per-jurisdiction subscriptions in **iCal and RSS** so a local group can drop a
 * renewal deadline into its own calendar (SIG-UI-027).
 *
 * The single most important rule here: the watch **keys its alerts on
 * `next_decision_date`**, not the expiry date (SIG-UI-014b). An expiry date is the
 * wrong figure — a contract that auto-renews with a 90-day notice window has a real
 * deadline of expiry-minus-90-days, after which the decision is made by default. So
 * this module does NOT recompute that date: it reuses the P15.2 dossier derivation
 * (`resolveTermination`/`nextDecisionDate`, the SIG-UI-014b wire contract) verbatim,
 * so the watch and the dossier can never disagree about when the decision falls.
 *
 * Colour-free by construction: presentation lives in `styles/epistemic.css`, and a
 * contested contract value carries the shared `≠` marker at every appearance
 * (SIG-UI-008) — the list, the iCal description, the RSS item, and the export.
 */

import { resolveTermination } from "./dossier";
import type { TerminationInput } from "./dossier";
import { CONTESTED_MARKER } from "./epistemic";

// --- The watch item (SIG-UI-026) --------------------------------------------

/**
 * One contract on the renewal watch. `termination` carries the raw auto-renewal
 * inputs the decision date is DERIVED from (never a stored `next_decision_date`, so
 * it can never drift from the inputs — SIG-UI-014b). `contested` marks a contract
 * whose material value is disputed, so the persistent marker travels to every
 * surface this item appears on (SIG-UI-008).
 */
export interface ContractWatchItem {
  contract_id: string;
  /** The deployment / vendor this contract governs, in plain language. */
  subject_label: string;
  jurisdiction: string;
  /** The raw termination inputs — expiry, auto-renewal flag, notice window (days). */
  termination: TerminationInput;
  /** The renewal window: the span (in days before expiry) in which renewal is decided. */
  renewal_window_days: number | null;
  approving_body: string | null;
  /** The next scheduled meeting of the approving body (ISO date), if known. */
  next_scheduled_meeting: string | null;
  /** A known replacement procurement (e.g. a successor RFP), if any. */
  replacement_procurement: string | null;
  /** Whether the contract's material value is contested (drives SIG-UI-008 marker). */
  contested: boolean;
}

/**
 * A watch item with its DERIVED, alertable fields resolved (SIG-UI-026). The
 * `next_decision_date` and `notice_deadline` are the SAME value — the date by which
 * the decision must be taken or it is made by default — computed once, here, from
 * the P15.2 termination derivation. `expiry_date` is retained but is deliberately
 * NOT the alert key.
 */
export interface ResolvedWatchItem extends ContractWatchItem {
  expiry_date: string | null;
  /** The decision date the alert keys on (SIG-UI-014b). Null when no expiry is known. */
  next_decision_date: string | null;
  /** The notice deadline — identical to `next_decision_date` (SIG-UI-026). */
  notice_deadline: string | null;
}

/**
 * Resolve a watch item's derived timing (SIG-UI-026, SIG-UI-014b). Reuses the
 * dossier's `resolveTermination` so the notice deadline / decision date the watch
 * alerts on is byte-identical to the date the dossier surfaces. A contract with no
 * expiry has no decision date and produces no dated alert.
 */
export function resolveWatchItem(item: ContractWatchItem): ResolvedWatchItem {
  const t = resolveTermination(item.termination);
  return {
    ...item,
    expiry_date: t.expiry_date,
    next_decision_date: t.next_decision_date,
    notice_deadline: t.next_decision_date,
  };
}

/** A URL-safe slug for a jurisdiction name (the subscription is offered per one). */
export function jurisdictionSlug(jurisdiction: string): string {
  return jurisdiction
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** The distinct jurisdictions present in a watch list, in first-seen order. */
export function watchJurisdictions(items: readonly ContractWatchItem[]): string[] {
  const seen: string[] = [];
  for (const i of items) if (!seen.includes(i.jurisdiction)) seen.push(i.jurisdiction);
  return seen;
}

/** The watch items for one jurisdiction (SIG-UI-027: subscriptions are per-jurisdiction). */
export function itemsForJurisdiction(
  items: readonly ContractWatchItem[],
  jurisdiction: string,
): ContractWatchItem[] {
  return items.filter((i) => i.jurisdiction === jurisdiction);
}

/**
 * The dated, alertable items for a jurisdiction — resolved and filtered to those
 * that actually have a decision date, sorted by that date. An item with no decision
 * date is shown on the page but is not a calendar/feed alert (there is nothing to
 * put on a calendar).
 */
export function alertItemsForJurisdiction(
  items: readonly ContractWatchItem[],
  jurisdiction: string,
): (ResolvedWatchItem & { next_decision_date: string })[] {
  return itemsForJurisdiction(items, jurisdiction)
    .map(resolveWatchItem)
    .filter((i): i is ResolvedWatchItem & { next_decision_date: string } => i.next_decision_date !== null)
    .sort((a, b) => a.next_decision_date.localeCompare(b.next_decision_date));
}

// --- Subscriptions: iCal (RFC 5545) -----------------------------------------

/** The `≠` contested-marker phrase appended to feed text for a contested value. */
function contestedSuffix(item: ContractWatchItem): string {
  return item.contested ? ` ${CONTESTED_MARKER.glyph} ${CONTESTED_MARKER.label} — see the dossier.` : "";
}

/** Compact an ISO `YYYY-MM-DD` to the iCal date form `YYYYMMDD`. */
function icalDate(iso: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) throw new Error(`invalid ISO date for iCal: "${iso}"`);
  return iso.replace(/-/g, "");
}

/** Escape a text value per RFC 5545 §3.3.11 (backslash, comma, semicolon, newline). */
function icalEscape(text: string): string {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

/**
 * Fold a content line to ≤75 octets per RFC 5545 §3.1, continuing with CRLF + a
 * single leading space. Folding is octet-aware (UTF-8) so a multibyte character is
 * never split across the fold boundary.
 */
function icalFold(line: string): string {
  const enc = new TextEncoder();
  if (enc.encode(line).length <= 75) return line;
  const out: string[] = [];
  let current = "";
  let currentBytes = 0;
  let first = true;
  for (const ch of line) {
    const chBytes = enc.encode(ch).length;
    // Continuation lines carry a leading space, so their budget is 74 octets.
    const limit = first ? 75 : 74;
    if (currentBytes + chBytes > limit) {
      out.push(current);
      current = ch;
      currentBytes = chBytes;
      first = false;
    } else {
      current += ch;
      currentBytes += chBytes;
    }
  }
  out.push(current);
  return out.join("\r\n ");
}

/**
 * A stable, deterministic UID for a watch event. Built from the contract id and the
 * decision date only — no wall-clock, no random — so re-emitting the feed is
 * byte-stable (a subscription must not churn on every fetch).
 */
export function watchEventUid(item: ResolvedWatchItem & { next_decision_date: string }): string {
  return `sig-watch-${item.contract_id}-${icalDate(item.next_decision_date)}@sig.example`;
}

/**
 * The iCal (RFC 5545) subscription for a jurisdiction, keyed on `next_decision_date`
 * (SIG-UI-027, SIG-UI-014b). Each contract's decision date becomes an all-day VEVENT.
 * `stamp` is the deterministic DTSTAMP (the as-of world date), never wall-clock time,
 * so the feed is reproducible (SIG-EVID-018 spirit). Lines are CRLF-joined per spec.
 */
export function toICal(
  items: readonly ContractWatchItem[],
  jurisdiction: string,
  stamp: string,
): string {
  const dtstamp = `${icalDate(stamp)}T000000Z`;
  const lines: string[] = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//SIG//Renewal Watch//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${icalEscape(`SIG renewal watch — ${jurisdiction}`)}`,
  ];
  for (const item of alertItemsForJurisdiction(items, jurisdiction)) {
    const summary = `Decision deadline: ${item.subject_label}`;
    const description =
      `The renewal/notice decision for ${item.subject_label} must be taken by ` +
      `${item.next_decision_date}` +
      (item.termination.auto_renews
        ? ` — after this date the contract auto-renews by default.`
        : ` — the contract expires and must be renewed to continue.`) +
      (item.approving_body ? ` Approving body: ${item.approving_body}.` : "") +
      (item.next_scheduled_meeting ? ` Next scheduled meeting: ${item.next_scheduled_meeting}.` : "") +
      contestedSuffix(item);
    lines.push(
      "BEGIN:VEVENT",
      `UID:${watchEventUid(item)}`,
      `DTSTAMP:${dtstamp}`,
      `DTSTART;VALUE=DATE:${icalDate(item.next_decision_date)}`,
      `SUMMARY:${icalEscape(summary)}`,
      `DESCRIPTION:${icalEscape(description)}`,
      "END:VEVENT",
    );
  }
  lines.push("END:VCALENDAR");
  return lines.map(icalFold).join("\r\n") + "\r\n";
}

// --- Subscriptions: RSS 2.0 -------------------------------------------------

/** Escape text for inclusion in XML (RSS) element content / attributes. */
function xmlEscape(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** RFC 822 date form for an all-day event, at 00:00:00 GMT (RSS `pubDate`). */
export function rssDate(iso: string): string {
  const ms = Date.parse(`${iso}T00:00:00Z`);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO date for RSS: "${iso}"`);
  return new Date(ms).toUTCString();
}

/**
 * The RSS 2.0 subscription for a jurisdiction, keyed on `next_decision_date`
 * (SIG-UI-027). Each contract's decision date is one `<item>` with a stable `guid`
 * and a `pubDate` on that date. `origin` is the site origin for the item links.
 */
export function toRss(
  items: readonly ContractWatchItem[],
  jurisdiction: string,
  origin: string,
): string {
  const channelTitle = `SIG renewal watch — ${jurisdiction}`;
  const channelLink = `${origin}/watch/`;
  const out: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0">',
    "  <channel>",
    `    <title>${xmlEscape(channelTitle)}</title>`,
    `    <link>${xmlEscape(channelLink)}</link>`,
    `    <description>${xmlEscape(
      `Upcoming procurement/renewal decision deadlines in ${jurisdiction}, keyed on the decision date (not the expiry date).`,
    )}</description>`,
  ];
  for (const item of alertItemsForJurisdiction(items, jurisdiction)) {
    const title = `Decision deadline ${item.next_decision_date}: ${item.subject_label}`;
    const desc =
      `Decision must be taken by ${item.next_decision_date}` +
      (item.termination.auto_renews ? " (auto-renews by default after this date)." : " (expires; renew to continue).") +
      (item.approving_body ? ` Approving body: ${item.approving_body}.` : "") +
      (item.replacement_procurement ? ` Replacement procurement: ${item.replacement_procurement}.` : "") +
      contestedSuffix(item);
    out.push(
      "    <item>",
      `      <title>${xmlEscape(title)}</title>`,
      `      <link>${xmlEscape(channelLink)}</link>`,
      `      <guid isPermaLink="false">${xmlEscape(watchEventUid(item))}</guid>`,
      `      <pubDate>${xmlEscape(rssDate(item.next_decision_date))}</pubDate>`,
      `      <description>${xmlEscape(desc)}</description>`,
      "    </item>",
    );
  }
  out.push("  </channel>", "</rss>", "");
  return out.join("\n");
}

/** The canonical page path for the renewal watch (trailing slash — SIG-UI-035). */
export const WATCH_PATH = "/watch/";

/** The canonical iCal subscription path for a jurisdiction. */
export function watchICalPath(jurisdiction: string): string {
  return `/watch/${jurisdictionSlug(jurisdiction)}.ics`;
}

/** The canonical RSS subscription path for a jurisdiction. */
export function watchRssPath(jurisdiction: string): string {
  return `/watch/${jurisdictionSlug(jurisdiction)}.xml`;
}
