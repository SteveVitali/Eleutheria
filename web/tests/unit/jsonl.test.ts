// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * D-P37.65a-2 (a): the chunked jsonl readers behind `web/src/lib/jsonl.ts` —
 * the contract is byte-for-byte `.split("\n")` semantics without ever
 * materialising the file as one V8 string (the 0x1fffffe8-char cap that
 * killed every export-mode build on a >512 MiB `statements.jsonl`).
 */
import { afterAll, describe, expect, it } from "vitest";
import { mkdtempSync, rmSync, statSync, writeFileSync, appendFileSync, openSync, writeSync, closeSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  hasNonBlankLine,
  readJsonlRows,
  readJsonlRowsCached,
  readLinesSync,
} from "../../src/lib/jsonl";

const dir = mkdtempSync(join(tmpdir(), "sig-jsonl-"));
afterAll(() => rmSync(dir, { recursive: true, force: true }));

const collect = (path: string): string[] => [...readLinesSync(path)];

describe("readLinesSync — .split(\"\\n\") semantics without the whole string", () => {
  it("yields every line, strips the terminator, keeps interior blanks", () => {
    const p = join(dir, "plain.jsonl");
    writeFileSync(p, '{"a":1}\n\n{"a":2}\n   \n{"a":3}\n');
    expect(collect(p)).toEqual(['{"a":1}', "", '{"a":2}', "   ", '{"a":3}']);
  });

  it("yields a trailing unterminated line", () => {
    const p = join(dir, "unterminated.jsonl");
    writeFileSync(p, '{"a":1}\n{"a":2}');
    expect(collect(p)).toEqual(['{"a":1}', '{"a":2}']);
  });

  it("an empty file yields nothing; a blank-only file yields its blank lines", () => {
    const empty = join(dir, "empty.jsonl");
    writeFileSync(empty, "");
    expect(collect(empty)).toEqual([]);
    const blanks = join(dir, "blanks.jsonl");
    writeFileSync(blanks, "\n\n");
    expect(collect(blanks)).toEqual(["", ""]);
  });

  it("decodes a multi-byte codepoint split across the 8 MiB chunk boundary", () => {
    // Pad so a 4-byte UTF-8 character (emoji) straddles the read chunk:
    // bytes [8MiB-2, 8MiB+2) carry the emoji — a naive per-chunk toString
    // would corrupt it; StringDecoder carries the partial sequence.
    const p = join(dir, "boundary.jsonl");
    const CHUNK = 8 * 1024 * 1024;
    const pad = "x".repeat(CHUNK - 2 - "head:".length);
    const fd = openSync(p, "w");
    try {
      writeSync(fd, `head:${pad}💥:tail\n`);
      writeSync(fd, "second\n");
      writeSync(fd, "third");
    } finally {
      closeSync(fd);
    }
    expect(statSync(p).size).toBeGreaterThan(CHUNK);
    const lines = collect(p);
    expect(lines[1]).toBe("second");
    expect(lines[2]).toBe("third");
    expect(lines[0]!.endsWith("💥:tail")).toBe(true);
    expect(lines[0]!.startsWith("head:")).toBe(true);
    expect(lines[0]!.length).toBe(CHUNK - 2 - "head:".length + "head:".length + "💥:tail".length);
  });
});

describe("hasNonBlankLine", () => {
  it("is false on a missing-content file, true past whitespace", () => {
    const p = join(dir, "ws.jsonl");
    writeFileSync(p, "\n   \n");
    expect(hasNonBlankLine(p)).toBe(false);
    appendFileSync(p, '{"a":1}\n');
    expect(hasNonBlankLine(p)).toBe(true);
  });
});

describe("readJsonlRows / readJsonlRowsCached", () => {
  it("parses non-blank lines only", () => {
    const p = join(dir, "rows.jsonl");
    writeFileSync(p, '{"a":1}\n\n{"a":2}\n');
    expect(readJsonlRows(p)).toEqual([{ a: 1 }, { a: 2 }]);
  });

  it("the cached reader returns ONE parsed array per file revision", () => {
    const p = join(dir, "cached.jsonl");
    writeFileSync(p, '{"a":1}\n');
    const first = readJsonlRowsCached(p);
    expect(readJsonlRowsCached(p)).toBe(first); // the memo, not a re-parse
    // A rewritten file (different size) re-reads honestly.
    writeFileSync(p, '{"a":1}\n{"a":2}\n{"a":3}\n');
    const second = readJsonlRowsCached(p);
    expect(second).not.toBe(first);
    expect(second).toEqual([{ a: 1 }, { a: 2 }, { a: 3 }]);
  });
});
