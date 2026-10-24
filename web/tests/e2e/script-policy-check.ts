// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.50 (K0 §4.12 item 2): the pure script-policy check — shared by
// script-policy.spec.ts (which drives it over every discovered route) and the
// unit suite (which proves an injected `<script>` on a T0 fixture is caught —
// the check itself is tested, never assumed).

import { createHash } from "node:crypto";
import type { PageType } from "../../src/lib/page-types";

export interface ScriptElement {
  attrs: string;
  body: string;
  src: string | null;
  type: string | null;
  inline: boolean;
}

const sha256 = (body: string): string =>
  createHash("sha256").update(body, "utf8").digest("hex");

/** Every `<script>` element in a served HTML document. */
export function scriptsOf(html: string): ScriptElement[] {
  const out: ScriptElement[] = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>|<script\b([^>]*)\/>/gi;
  for (const m of html.matchAll(re)) {
    const attrs = m[1] ?? m[3] ?? "";
    const body = m[2] ?? "";
    const src = attrs.match(/\bsrc\s*=\s*["']([^"']+)["']/i)?.[1] ?? null;
    const type = attrs.match(/\btype\s*=\s*["']([^"']+)["']/i)?.[1] ?? null;
    out.push({ attrs, body, src, type: type?.toLowerCase() ?? null, inline: src === null });
  }
  return out;
}

/** A module script src'd from the build's own content-hashed asset dir. */
export const ASTRO_ASSET_SRC = /^\/_astro\/[\w.~-]+\.js$/;

/**
 * Every reason a `<script>` element is a violation on a route of `type`
 * (empty = conforming). `bootstrapHashes` is the recorded Astro bootstrap set
 * (`astro-runtime-script-hashes.json`); `t1Entries` the T1 module-entry
 * allow-list (`t1-module-entries.json` — empty until UXK0-4 lands one).
 * T3 carries no script-shape rule here (ADR-068 owns `/curate/**`) — only the
 * universal `on*=`/`javascript:` bans apply, which are HTML-level scans.
 */
export function scriptViolations(
  type: PageType,
  s: ScriptElement,
  bootstrapHashes: ReadonlySet<string>,
  t1Entries: ReadonlySet<string>,
): string[] {
  const problems: string[] = [];
  if (s.type === "application/ld+json") {
    problems.push(
      'inline application/ld+json block — D-J3-7 is linked files only (a <link rel="alternate"> is data, not a script)',
    );
    return problems;
  }
  if (type === "T0") {
    problems.push("T0 ships no <script> element of any kind");
    return problems;
  }
  if (type === "T3") return problems;
  const isModule = s.type === "module";
  if (s.inline) {
    const digest = sha256(s.body);
    if (!bootstrapHashes.has(digest)) {
      problems.push(
        `inline ${s.type ?? "classic"} script is not a recorded Astro bootstrap hash (sha256 ${digest} — record it in astro-runtime-script-hashes.json only after review)`,
      );
    }
    return problems;
  }
  // src'd script
  if (!isModule) {
    problems.push(`non-module src'd script (${s.type ?? "classic"}) — only type="module" is permitted`);
  }
  if (type === "T1" && !t1Entries.has(s.src!)) {
    problems.push(`T1 module src ${s.src} is not an allow-listed entry in t1-module-entries.json`);
  }
  if (type === "T2" && !ASTRO_ASSET_SRC.test(s.src!)) {
    problems.push(`T2 module src ${s.src} is not a content-hashed /_astro/ asset`);
  }
  return problems;
}

/** The universal bans — inline event handlers and javascript: URLs on every type. */
export function universalViolations(html: string): { onHandlers: string[]; jsUrls: string[] } {
  return {
    onHandlers: html.match(/<[a-zA-Z][^>]*\son[a-zA-Z]+\s*=/g) ?? [],
    jsUrls: html.match(/\b(?:href|src|action)\s*=\s*["']?\s*javascript:/gi) ?? [],
  };
}
