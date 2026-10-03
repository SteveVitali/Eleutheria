// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P34.18 / ADR-178 (S0 RI-01): the web-side alias resolution seam.
 *
 * Python's `policy.source_aliases` owns the canonical resolver; this module is
 * the same keyed-digest mechanism in TypeScript so the site's build-time
 * tables (`/sources/`, downloads metadata) resolve or redact any retired
 * identifier that survives in already-published export bytes — the page can
 * never drift from the re-key even before P34.21b's re-export lands.
 *
 * The committed table stores sha256 token digests only; old ids never appear
 * in the repository or in built pages.
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Must stay identical to `policy.source_aliases._TOKEN_RUN` — ``@`` is
// included so an e-mail-shaped owner token resolves as ONE run.
const TOKEN = /[A-Za-z0-9][A-Za-z0-9._@-]*/g;

interface AliasFile {
  source_aliases?: Record<string, string>;
  target_aliases?: Record<string, string>;
  token_aliases?: Record<string, string>;
  redaction_aliases?: Record<string, string>;
}

let table: Map<string, string> | null = null;

function aliasTable(): Map<string, string> {
  if (table !== null) return table;
  table = new Map();
  try {
    const path = fileURLToPath(
      new URL("../../../policy/src/policy/data/source_aliases.json", import.meta.url),
    );
    const data = JSON.parse(readFileSync(path, "utf-8")) as AliasFile;
    for (const section of [
      data.source_aliases,
      data.target_aliases,
      data.token_aliases,
      data.redaction_aliases,
    ]) {
      for (const [digest, neutral] of Object.entries(section ?? {})) {
        table.set(digest, neutral);
      }
    }
  } catch {
    // Absent or unreadable table = no aliases (fail-safe pass-through, same as
    // the Python loader's `empty` posture).
  }
  return table;
}

/** Resolve a retired token digest to its neutral identifier, else null. */
export function resolveToken(token: string): string | null {
  const table = aliasTable();
  const sha = (s: string) => createHash("sha256").update(s).digest("hex");
  // Suppressed/redaction entries are keyed by the lowercased form.
  return table.get(sha(token)) ?? table.get(sha(token.toLowerCase())) ?? null;
}

/** Resolve a full source id; pass-through when nothing matches. */
export function resolveSourceId(id: string): string {
  return resolveToken(id) ?? id;
}

/** Resolve every retired token embedded in a text value (urls, credits). */
export function resolveTextIds(text: string): string {
  return text.replace(TOKEN, (tok) => resolveToken(tok) ?? tok);
}
