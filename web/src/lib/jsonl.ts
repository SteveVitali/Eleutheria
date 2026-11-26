// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Chunked synchronous readers for the export layout's `*.jsonl` row streams
 * (D-P37.65a-2).
 *
 * `readFileSync(path, "utf-8")` materialises the whole file as ONE V8 string —
 * and V8 caps a string at 0x1fffffe8 characters (~512 MiB), so any compartment
 * `sites.jsonl` / `statements.jsonl` / `labels/*.jsonl` past the cap throws
 * `ERR_STRING_TOO_LONG` (`osm_physical/statements.jsonl` in the 2026-11-25
 * national export is 1,013,125,905 B — it killed every export-mode
 * `astro build`). `readLinesSync` reads fixed-size chunks through
 * `StringDecoder` — a multi-byte codepoint split across a chunk boundary
 * still decodes correctly — and yields one line at a time, so peak memory
 * is bounded by the longest LINE, never by the file.
 *
 * These are build-time readers (the shell is static-first, SIG-UI-036): they
 * run in the prerender pass, never ship to the client.
 */

import { closeSync, openSync, readSync, statSync } from "node:fs";
import { StringDecoder } from "node:string_decoder";

/**
 * Read chunk size — large enough to keep the syscall count low, small enough
 * that the line carry-over stays far from the string cap.
 */
const CHUNK_BYTES = 8 * 1024 * 1024;

/**
 * Yield each line of `path` with its `\n` terminator stripped (a trailing
 * unterminated line still yields). Semantically identical to iterating
 * `readFileSync(path, "utf-8").split("\n")` minus the split's final empty
 * element — every existing caller skips blank lines, so the contract holds.
 * The file is never materialised as one string.
 */
export function* readLinesSync(path: string): Generator<string, void, undefined> {
  const fd = openSync(path, "r");
  try {
    const decoder = new StringDecoder("utf-8");
    const buf = Buffer.allocUnsafe(CHUNK_BYTES);
    let carry = "";
    for (;;) {
      const n = readSync(fd, buf, 0, buf.length, null);
      if (n <= 0) break;
      const text = carry + decoder.write(buf.subarray(0, n));
      let start = 0;
      for (;;) {
        const nl = text.indexOf("\n", start);
        if (nl === -1) break;
        yield text.slice(start, nl);
        start = nl + 1;
      }
      carry = text.slice(start);
    }
    carry += decoder.end();
    if (carry !== "") yield carry;
  } finally {
    closeSync(fd);
  }
}

/**
 * `true` when `path` carries at least one non-blank line — the streaming
 * replacement for `readFileSync(path, "utf-8").trim() !== ""` over a file
 * that may exceed the string cap (stops at the first non-blank line).
 */
export function hasNonBlankLine(path: string): boolean {
  for (const line of readLinesSync(path)) {
    if (line.trim() !== "") return true;
  }
  return false;
}

/**
 * The parsed rows of a jsonl artifact, blank lines skipped — the streaming
 * drop-in for `readFileSync(path, "utf-8").split("\n") … JSON.parse`.
 */
export function readJsonlRows<T = unknown>(path: string): T[] {
  const rows: T[] = [];
  for (const line of readLinesSync(path)) {
    const t = line.trim();
    if (!t) continue;
    rows.push(JSON.parse(t) as T);
  }
  return rows;
}

/**
 * The parsed rows of a jsonl artifact, parsed ONCE per file revision
 * (D-P37.65a-2 (b)) — for the artifacts every per-source page re-reads
 * (`transparency/captures.jsonl`, `transparency/freshness.jsonl`): without
 * the memo each of the ~hundreds of source pages re-parsed the shared feed.
 * The cache validates on `mtimeMs` + `size`, so a rewritten file re-reads
 * honestly while an unchanged file parses exactly once per build.
 */
const _jsonlRowsCache = new Map<string, { mtimeMs: number; size: number; rows: unknown[] }>();

export function readJsonlRowsCached<T = unknown>(path: string): T[] {
  const st = statSync(path);
  const hit = _jsonlRowsCache.get(path);
  if (hit && hit.mtimeMs === st.mtimeMs && hit.size === st.size) {
    return hit.rows as T[];
  }
  const rows = readJsonlRows(path);
  _jsonlRowsCache.set(path, { mtimeMs: st.mtimeMs, size: st.size, rows });
  return rows as T[];
}
