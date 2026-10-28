// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.19 (UXK0-3, K0 §4.8, SIG-UI-096, ADR-223): the static CSP layer. On
// `output: "static"` Astro emits a per-page
// `<meta http-equiv="Content-Security-Policy">` carrying that page's tracked
// sha384 hashes for its inline <script>/<style> elements — the authoritative
// per-document policy. The served response header (ops/web/sig-security.conf)
// carries the meta-inexpressible + hash-independent half (frame-ancestors,
// object-src, base-uri, form-action, the *-attr 'none' pair): the browser
// enforces meta ∩ header, so a static host never needs per-page hash maps.
//
// This module holds the two pure transforms that layer needs:
//   - policyDirectives — the parser both the build patcher and the e2e
//     policy check share;
//   - tightenPolicyForType — K0 §4.8's per-type split: T0 record/print pages
//     get `default-src 'none'` and lose the fetch directives entirely (they
//     emit no scripts by ADR-155's registry contract); T1/T2/T3 keep the
//     emitted 'self'-anchored policy with its tracked hashes.

import type { PageType } from "./page-types";

/** The emitted meta tag — exactly the attribute order Astro writes. */
export const CSP_META_RE =
  /(<meta\s+http-equiv="content-security-policy"\s+content=")([^"]*)(")/i;

/** Parse a CSP value into directive-name → source-token list. */
export function policyDirectives(policy: string): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const part of policy.split(";")) {
    const trimmed = part.trim();
    if (trimmed === "") continue;
    const [name, ...tokens] = trimmed.split(/\s+/);
    out.set(name.toLowerCase(), tokens);
  }
  return out;
}

/**
 * K0 §4.8's T0 row drops the whole fetch surface a record/print page never
 * uses: scripts, connect and worker fall back to `default-src 'none'`
 * (style-src-attr/script-src-attr 'none' stay — explicit denials never
 * loosen a fallback). img-src loses `blob:` (T1/T2 need it for island
 * rendering; a record page does not). The emitted style-src keeps its 'self'
 * + tracked hashes — a T0 page that ever carries an inline <style> still
 * renders it, and an absent one costs nothing.
 */
const T0_DROP_DIRECTIVES = new Set([
  "script-src",
  "script-src-elem",
  "connect-src",
  "worker-src",
]);

/** The meta CSP value a route of `type` ships (T0 tightened per K0 §4.8). */
export function tightenPolicyForType(type: PageType, policy: string): string {
  if (type !== "T0") return policy;
  const out: string[] = [];
  for (const [name, tokens] of policyDirectives(policy)) {
    if (T0_DROP_DIRECTIVES.has(name)) continue;
    if (name === "default-src") {
      out.push("default-src 'none'");
    } else if (name === "img-src") {
      out.push(`img-src ${tokens.filter((t) => t !== "blob:").join(" ")}`);
    } else {
      out.push(`${name} ${tokens.join(" ")}`);
    }
  }
  return `${out.join("; ")}; `;
}

/**
 * Rewrite the emitted meta CSP in a built T0 document. No-ops (returns the
 * input unchanged) on a page without the meta — the e2e sweep asserts the
 * meta exists on every route, so a silent miss is caught there, never here.
 */
export function tightenT0Document(html: string): string {
  return html.replace(
    CSP_META_RE,
    (_m, pre: string, content: string, post: string) =>
      pre + tightenPolicyForType("T0", content) + post,
  );
}
