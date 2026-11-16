// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
//
// P37.60 (SIG-UI-152, DR-K14-18): baseline adoption — the sanctioned way a
// screenshot becomes a committed baseline.
//
//   node scripts/visual-adopt-baselines.mjs --ticket P37.60 [--results web/test-results]
//
// Playwright's CI runner renders the linux/canonical actuals; when the grid
// reports "A snapshot doesn't exist …, writing actual", the run's artifact
// carries web/test-results/<slug>/<group>--<cell>-actual.png. This script
// copies each actual into tests/visual/visual.spec.ts-snapshots/ AND writes
// its provenance row into tests/visual/baselines.json — a baseline change
// MUST cite its ticket, so the ticket is a required flag, never defaulted.
//
// Only -actual.png from a NATIONAL-build run may be adopted (invented names
// only — the spec's data-source guard makes a fixtures actual impossible to
// merge green, but the ledger makes the provenance explicit either way).

import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SNAP = join(WEB, "tests/visual/visual.spec.ts-snapshots");
const LEDGER_PATH = join(WEB, "tests/visual/baselines.json");

const args = process.argv.slice(2);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const TICKET = opt("--ticket");
const RESULTS = resolve(opt("--results") ?? join(WEB, "test-results"));
const NOTE = opt("--note") ?? "baseline adopted from the linux CI run (visual-leg artifact)";

if (!TICKET || !/^P\d+\.\d+[a-z]?$/.test(TICKET)) {
  console.error("usage: node scripts/visual-adopt-baselines.mjs --ticket P37.60 [--results <dir>] [--note <text>]");
  console.error("a baseline change MUST cite its ticket (SIG-UI-152) — the flag is required.");
  process.exit(2);
}
if (!existsSync(RESULTS)) {
  console.error(`no test-results at ${RESULTS} — nothing to adopt`);
  process.exit(0);
}

const actuals = [];
for (const dir of readdirSync(RESULTS)) {
  const d = join(RESULTS, dir);
  try {
    for (const f of readdirSync(d)) {
      const m = f.match(/^([a-z0-9-]+)--(light|dark)-(1440|390|320)-actual\.png$/);
      if (m) actuals.push({ src: join(d, f), name: `${m[1]}--${m[2]}-${m[3]}.png` });
    }
  } catch {
    /* not a directory */
  }
}

if (actuals.length === 0) {
  console.log("no -actual.png captures found — nothing to adopt");
  process.exit(0);
}

mkdirSync(SNAP, { recursive: true });
const ledger = JSON.parse(readFileSync(LEDGER_PATH, "utf8"));
if (ledger.schema !== "sig.visual-baselines/1") {
  console.error(`${LEDGER_PATH} is not sig.visual-baselines/1`);
  process.exit(2);
}

let adopted = 0;
for (const a of actuals.sort((x, y) => x.name.localeCompare(y.name))) {
  copyFileSync(a.src, join(SNAP, a.name));
  const existing = ledger.baselines[a.name];
  ledger.baselines[a.name] = {
    ticket: TICKET,
    note: existing?.ticket === TICKET ? (existing.note ?? NOTE) : NOTE,
  };
  adopted++;
}
writeFileSync(LEDGER_PATH, JSON.stringify(ledger, null, 2) + "\n");
console.log(`adopted ${adopted} baseline(s) under ${TICKET} into tests/visual/visual.spec.ts-snapshots/`);
