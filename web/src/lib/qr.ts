// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.26 (K14 UXK14-9 / K14 §4.11, SIG-UI-098/130/155) — the print document's
 * QR code: a byte-mode QR (error-correction level M) rendered as SVG path data
 * at build time. Dependency-free and deterministic: the same URL always yields
 * the same module matrix, so a printed brief's code can never drift from the
 * permalink it encodes.
 *
 * Scope: byte mode only (the pinned permalinks this row encodes are ASCII
 * URLs), EC level M (15 % recovery — the print-document class), symbol
 * versions 1–10 (≈ 213-byte capacity — far above any dossier permalink).
 * Anything that does not fit fails closed (`rangeError`), never a truncated
 * code (SIG-ENG-042). The matrix is verified against a reference encoder in
 * `tests/unit/qr.test.ts`.
 */

/** Error-correction level M — the print-document class. */
export const QR_EC_LEVEL = "M" as const;

interface EcVersion {
  version: number;
  /** Data codewords per block (one entry per block; later blocks may carry one more). */
  blocks: readonly number[];
  /** EC codewords generated per block. */
  ecPerBlock: number;
}

/**
 * ISO 18004 table 9, EC level M, versions 1–10. `blocks` lists each RS block's
 * data-codeword count; the symbol's total codewords = sum(blocks) +
 * blocks.length × ecPerBlock.
 */
const EC_M: readonly EcVersion[] = [
  { version: 1, blocks: [16], ecPerBlock: 10 },
  { version: 2, blocks: [28], ecPerBlock: 16 },
  { version: 3, blocks: [44], ecPerBlock: 26 },
  { version: 4, blocks: [32, 32], ecPerBlock: 18 },
  { version: 5, blocks: [43, 43], ecPerBlock: 24 },
  { version: 6, blocks: [27, 27, 27, 27], ecPerBlock: 16 },
  { version: 7, blocks: [31, 31, 31, 31], ecPerBlock: 18 },
  { version: 8, blocks: [38, 38, 39, 39], ecPerBlock: 22 },
  { version: 9, blocks: [36, 36, 36, 37, 37], ecPerBlock: 22 },
  { version: 10, blocks: [43, 43, 43, 43, 44], ecPerBlock: 26 },
];

/** Alignment-pattern centre coordinates per version (index = version). */
const ALIGN_CENTERS: readonly (readonly number[])[] = [
  [],
  [], // v1 has none
  [6, 18],
  [6, 22],
  [6, 26],
  [6, 30],
  [6, 34],
  [6, 22, 38],
  [6, 24, 42],
  [6, 26, 46],
  [6, 28, 50],
];

/** Byte-mode character-count field width: 8 bits through version 9, 16 from 10. */
function countBits(version: number): number {
  return version <= 9 ? 8 : 16;
}

/** The data-codeword capacity of a version (sum of its block sizes). */
function dataCapacity(v: EcVersion): number {
  return v.blocks.reduce((a, b) => a + b, 0);
}

/** The maximum byte-mode payload of a version. */
export function qrCapacityBytes(version: number): number {
  const v = EC_M[version - 1];
  if (!v) throw new Error(`qrCapacityBytes: version ${version} outside the 1–10 table`);
  return Math.floor((dataCapacity(v) * 8 - 4 - countBits(version)) / 8);
}

// --- GF(2^8) over the QR polynomial 0x11D -----------------------------------

const GF_EXP = new Uint8Array(512);
const GF_LOG = new Uint8Array(256);
{
  let x = 1;
  for (let i = 0; i < 255; i++) {
    GF_EXP[i] = x;
    GF_LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255]!;
}

function gfMul(a: number, b: number): number {
  return a === 0 || b === 0 ? 0 : GF_EXP[GF_LOG[a]! + GF_LOG[b]!]!;
}

/** The Reed–Solomon generator polynomial of degree `degree` (coefficients
 *  highest-degree first, leading 1 included → length degree+1). */
function rsGenerator(degree: number): number[] {
  let gen = [1];
  for (let i = 0; i < degree; i++) {
    const next = new Array<number>(gen.length + 1).fill(0);
    for (let j = 0; j < gen.length; j++) {
      // (x + αⁱ)·P in descending-coefficient order:
      // next[j] += P[j] (the x term), next[j+1] += αⁱ·P[j].
      next[j] ^= gen[j]!;
      next[j + 1] ^= gfMul(gen[j]!, GF_EXP[i]!);
    }
    gen = next;
  }
  return gen;
}

/** The `degree`-byte RS remainder of `data` under `gen` (length degree+1). */
function rsRemainder(data: readonly number[], gen: readonly number[]): number[] {
  const degree = gen.length - 1;
  const res = new Array<number>(degree).fill(0);
  for (const d of data) {
    const factor = d ^ res.shift()!;
    res.push(0);
    for (let j = 0; j < degree; j++) res[j] ^= gfMul(gen[j + 1]!, factor);
  }
  return res;
}

// --- Bit stream --------------------------------------------------------------

class BitWriter {
  readonly bits: number[] = [];
  push(value: number, width: number): void {
    for (let i = width - 1; i >= 0; i--) this.bits.push((value >>> i) & 1);
  }
}

/** The interleaved (data ++ ec) codeword stream for one version. */
function encodePayload(text: string, v: EcVersion): number[] {
  const data = [...new TextEncoder().encode(text)];
  const cap = dataCapacity(v);
  const headerBits = 4 + countBits(v.version);
  if (data.length * 8 + headerBits > cap * 8) {
    throw new RangeError(
      `qr: payload of ${data.length} bytes does not fit version ${v.version}-M ` +
        `(capacity ${qrCapacityBytes(v.version)}) — refuse a truncated code`,
    );
  }
  const w = new BitWriter();
  w.push(0b0100, 4); // byte mode
  w.push(data.length, countBits(v.version));
  for (const b of data) w.push(b, 8);
  // Terminator: up to 4 zero bits, then pad to the byte boundary, then EC/11.
  w.push(0, Math.min(4, cap * 8 - w.bits.length));
  while (w.bits.length % 8 !== 0) w.push(0, 1);
  const pad = [0xec, 0x11];
  const bytes: number[] = [];
  for (let i = 0; i < w.bits.length; i += 8) {
    bytes.push(w.bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
  }
  for (let i = 0; bytes.length < cap; i++) bytes.push(pad[i % 2]!);

  // Split into RS blocks, append each block's remainder, then interleave.
  const gen = rsGenerator(v.ecPerBlock);
  const dataBlocks: number[][] = [];
  const ecBlocks: number[][] = [];
  let off = 0;
  for (const len of v.blocks) {
    const block = bytes.slice(off, off + len);
    dataBlocks.push(block);
    ecBlocks.push(rsRemainder(block, gen));
    off += len;
  }
  const out: number[] = [];
  for (let i = 0; i < Math.max(...v.blocks); i++) {
    for (const b of dataBlocks) if (i < b.length) out.push(b[i]!);
  }
  for (let i = 0; i < v.ecPerBlock; i++) {
    for (const b of ecBlocks) out.push(b[i]!);
  }
  return out;
}

// --- The symbol matrix ---------------------------------------------------------

export interface QrMatrix {
  version: number;
  /** Modules per side (17 + 4·version). */
  size: number;
  /** Row-major module bitmap: true = dark. */
  modules: boolean[];
}

type Grid = {
  size: number;
  dark: boolean[];
  isFunction: boolean[];
};

function set(g: Grid, r: number, c: number, on: boolean, fn = true): void {
  g.dark[r * g.size + c] = on;
  if (fn) g.isFunction[r * g.size + c] = true;
}

function finder(g: Grid, r: number, c: number): void {
  // The 9×9 block centred on the 7×7 finder at (r,c) carries the separators.
  for (let dr = -4; dr <= 4; dr++) {
    for (let dc = -4; dc <= 4; dc++) {
      const rr = r + dr;
      const cc = c + dc;
      if (rr < 0 || cc < 0 || rr >= g.size || cc >= g.size) continue;
      const edge = Math.max(Math.abs(dr), Math.abs(dc));
      // edge 0–1 = the dark centre, 2 = light ring, 3 = dark ring, 4 = separator.
      set(g, rr, cc, edge === 0 || edge === 1 || edge === 3);
    }
  }
}

function alignment(g: Grid, r: number, c: number): void {
  for (let dr = -2; dr <= 2; dr++) {
    for (let dc = -2; dc <= 2; dc++) {
      const edge = Math.max(Math.abs(dr), Math.abs(dc));
      set(g, r + dr, c + dc, edge !== 1);
    }
  }
}

/** 15-bit format info for (ecLevel M=0, mask) — BCH(15,5) ⊕ 0x5412. */
function formatBits(mask: number): number {
  const data = mask; // EC level M encodes as 00 → the 5-bit payload is the mask
  let rem = data << 10;
  for (let i = 14; i >= 10; i--) {
    if ((rem >>> i) & 1) rem ^= 0x537 << (i - 10);
  }
  return ((data << 10) | rem) ^ 0x5412;
}

/** 18-bit version info — BCH(18,6) over generator 0x1F25. */
function versionBits(version: number): number {
  let rem = version << 12;
  for (let i = 17; i >= 12; i--) {
    if ((rem >>> i) & 1) rem ^= 0x1f25 << (i - 12);
  }
  return (version << 12) | rem;
}

const MASK_FNS: readonly ((r: number, c: number) => boolean)[] = [
  (r, c) => (r + c) % 2 === 0,
  (r) => r % 2 === 0,
  (_r, c) => c % 3 === 0,
  (r, c) => (r + c) % 3 === 0,
  (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
  (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
  (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
  (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
];

function drawFunctionPatterns(g: Grid, version: number): void {
  finder(g, 3, 3);
  finder(g, 3, g.size - 4);
  finder(g, g.size - 4, 3);
  // Timing.
  for (let i = 8; i < g.size - 8; i++) {
    set(g, 6, i, i % 2 === 0);
    set(g, i, 6, i % 2 === 0);
  }
  // Alignment centres — skip ONLY the three pairs that coincide with a finder
  // pattern; centres on the timing lines (e.g. (6, 26)) still draw — the
  // alignment pattern overwrites the timing modules there (ISO fig. E.1).
  const centers = ALIGN_CENTERS[version] ?? [];
  centers.forEach((r, i) => {
    centers.forEach((c, j) => {
      const corner =
        (i === 0 && j === 0) || (i === 0 && j === centers.length - 1) || (i === centers.length - 1 && j === 0);
      if (!corner) alignment(g, r, c);
    });
  });
  // Reserve the format-info strips (they are written after masking).
  for (let i = 0; i <= 5; i++) g.isFunction[8 * g.size + i] = true;
  g.isFunction[8 * g.size + 7] = true;
  g.isFunction[8 * g.size + 8] = true;
  g.isFunction[7 * g.size + 8] = true;
  for (let i = 0; i <= 5; i++) g.isFunction[i * g.size + 8] = true;
  // Format copy 2 — row 8 at columns (size-1)…(size-8), and column 8 at
  // rows (size-7)…(size-1) (the (size-8, 8) cell is the dark module).
  for (let i = 0; i < 8; i++) g.isFunction[8 * g.size + (g.size - 1 - i)] = true;
  for (let i = 8; i < 15; i++) g.isFunction[(g.size - 15 + i) * g.size + 8] = true;
  // The dark module.
  set(g, 4 * version + 9, 8, true);
  // Version info for v ≥ 7.
  if (version >= 7) {
    const bits = versionBits(version);
    for (let i = 0; i < 18; i++) {
      const bit = ((bits >>> i) & 1) === 1;
      const r = Math.floor(i / 3);
      const c = (i % 3) + g.size - 11;
      set(g, r, c, bit);
      set(g, c, r, bit);
    }
  }
}

/** Zigzag payload placement (ISO 18004 §7.7.3): MSB first, column pairs
 *  right→left, skipping the timing column. */
function drawData(g: Grid, codewords: number[]): void {
  const bits: number[] = [];
  for (const b of codewords) for (let i = 7; i >= 0; i--) bits.push((b >>> i) & 1);
  let bit = 0;
  let up = true;
  for (let c = g.size - 1; c >= 1; c -= 2) {
    if (c === 6) c = 5; // the timing column
    for (let i = 0; i < g.size; i++) {
      const r = up ? g.size - 1 - i : i;
      for (const cc of [c, c - 1]) {
        const idx = r * g.size + cc;
        if (g.isFunction[idx]) continue;
        if (bit < bits.length) g.dark[idx] = bits[bit++] === 1;
      }
    }
    up = !up;
  }
}

/** Write the two copies of the 15-bit format word for `mask`. */
function drawFormat(g: Grid, mask: number): void {
  const bits = formatBits(mask);
  const get = (i: number) => ((bits >>> i) & 1) === 1;
  // Copy 1: around the top-left finder — written MSB-first (bit 14 at the
  // first cell), matching the ISO winding order (verified against a
  // reference encoder's matrix).
  for (let i = 0; i <= 5; i++) set(g, 8, i, get(14 - i));
  set(g, 8, 7, get(8));
  set(g, 8, 8, get(7));
  set(g, 7, 8, get(6));
  for (let i = 9; i <= 14; i++) set(g, 14 - i, 8, get(14 - i));
  // Copy 2: row 8 at columns (size-1)…(size-8), and column 8 at
  // rows (size-7)…(size-1).
  for (let i = 0; i < 8; i++) set(g, 8, g.size - 1 - i, get(i));
  for (let i = 8; i < 15; i++) set(g, g.size - 15 + i, 8, get(i));
}

/** ISO penalty score (the four rules) — the mask with the lowest score wins. */
function penalty(g: Grid): number {
  const { size, dark } = g;
  const at = (r: number, c: number) => dark[r * size + c];
  let score = 0;
  // Rule 1 — runs of ≥ 5 same-colour modules in rows and columns.
  for (const horizontal of [true, false]) {
    for (let i = 0; i < size; i++) {
      let run = 1;
      for (let j = 1; j < size; j++) {
        const same = horizontal ? at(i, j) === at(i, j - 1) : at(j, i) === at(j - 1, i);
        if (same) run++;
        else {
          if (run >= 5) score += 3 + (run - 5);
          run = 1;
        }
      }
      if (run >= 5) score += 3 + (run - 5);
    }
  }
  // Rule 2 — 2×2 same-colour blocks.
  for (let r = 0; r < size - 1; r++) {
    for (let c = 0; c < size - 1; c++) {
      const v = at(r, c);
      if (v === at(r, c + 1) && v === at(r + 1, c) && v === at(r + 1, c + 1)) score += 3;
    }
  }
  // Rule 3 — finder-like 1011101 flanked by a four-light run.
  const like = (cells: boolean[]): boolean => {
    const pat = [true, false, true, true, true, false, true];
    const eq = (off: number) => pat.every((b, k) => cells[off + k] === b);
    for (let i = 0; i + 11 <= cells.length; i++) {
      if (
        (eq(i + 4) && !cells[i] && !cells[i + 1] && !cells[i + 2] && !cells[i + 3]) ||
        (eq(i) && !cells[i + 7] && !cells[i + 8] && !cells[i + 9] && !cells[i + 10])
      ) {
        score += 40;
        i += 10;
      }
    }
    return false;
  };
  for (const horizontal of [true, false]) {
    for (let i = 0; i < size; i++) {
      const cells: boolean[] = [];
      for (let j = 0; j < size; j++) cells.push(horizontal ? at(i, j) : at(j, i));
      like(cells);
    }
  }
  // Rule 4 — dark-module proportion (10 per 5 % step from 50 %).
  const darkCount = dark.filter(Boolean).length;
  const total = size * size;
  score += Math.floor(Math.abs(darkCount * 20 - total * 10) / total) * 10;
  return score;
}

/**
 * Encode `text` as a byte-mode QR symbol at EC level M. Picks the smallest
 * version in 1–10 that fits, then the lowest-penalty mask (first on ties).
 * `opts.mask` forces a mask (0–7) — the conformance tests pin one so the
 * matrix can be compared module-for-module with a reference encoder.
 */
export function qrEncode(text: string, opts: { mask?: number } = {}): QrMatrix {
  const bytes = new TextEncoder().encode(text).length;
  const v = EC_M.find((cand) => bytes <= qrCapacityBytes(cand.version));
  if (!v) {
    throw new RangeError(
      `qr: payload of ${bytes} bytes exceeds version 10-M ` +
        `(capacity ${qrCapacityBytes(10)}) — refuse a truncated code`,
    );
  }
  const codewords = encodePayload(text, v);
  const size = 17 + 4 * v.version;

  const base: Grid = { size, dark: new Array(size * size).fill(false), isFunction: new Array(size * size).fill(false) };
  drawFunctionPatterns(base, v.version);
  drawData(base, codewords);

  const masks = opts.mask !== undefined ? [opts.mask] : [0, 1, 2, 3, 4, 5, 6, 7];
  let best: { mask: number; dark: boolean[]; score: number } | null = null;
  for (const mask of masks) {
    if (mask < 0 || mask > 7) throw new RangeError(`qr: mask ${mask} outside 0–7`);
    const dark = [...base.dark];
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const idx = r * size + c;
        if (!base.isFunction[idx] && MASK_FNS[mask]!(r, c)) dark[idx] = !dark[idx];
      }
    }
    const g: Grid = { size, dark, isFunction: base.isFunction };
    drawFormat(g, mask);
    const score = penalty(g);
    if (best === null || score < best.score) best = { mask, dark, score };
  }
  return { version: v.version, size, modules: best!.dark };
}

/** The number of mask patterns the auto-selection evaluated (always 8). */
export const QR_MASK_COUNT = 8;

/**
 * SVG path `d` for a matrix — every dark module a unit square, run-merged per
 * row for compact output. `border` is the quiet-zone width in modules (4 per
 * ISO); the returned path is drawn inside a viewBox of `(size + 2·border)²`.
 */
export function qrPathData(m: QrMatrix, border = 4): { viewBox: number; d: string } {
  const parts: string[] = [];
  for (let r = 0; r < m.size; r++) {
    let c = 0;
    while (c < m.size) {
      if (m.modules[r * m.size + c]) {
        let w = 1;
        while (c + w < m.size && m.modules[r * m.size + c + w]) w++;
        parts.push(`M${c + border} ${r + border}h${w}v1h${-w}z`);
        c += w;
      } else {
        c++;
      }
    }
  }
  return { viewBox: m.size + 2 * border, d: parts.join("") };
}
