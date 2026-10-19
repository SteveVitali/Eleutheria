// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.65 containment-check mechanism tests (SIG-REL-008 `Also:`; SIG-ENG-042
 * — never a vacuous green). Each test drives the real script
 * (`web/scripts/check-root-absolute-paths.mjs`) over a planted fixture tree —
 * never asserts a count from the living baseline (OM-15): the baseline record
 * is the check's input, and what is asserted is the *verdict logic* — growth
 * fails, allow-listed constructions pass, shrinkage passes with an advisory.
 */

import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const SCRIPT = fileURLToPath(
  new URL("../../scripts/check-root-absolute-paths.mjs", import.meta.url),
);
const WEB_ROOT = fileURLToPath(new URL("../..", import.meta.url));

interface Run {
  status: number | null;
  stdout: string;
  stderr: string;
}

function run(args: string[]): Run {
  const r = spawnSync(process.execPath, [SCRIPT, ...args], { encoding: "utf-8" });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

/** A planted src tree under a fresh tmp dir; returns {src, name(file)} where
 *  `name` gives the repo-relative form the checker records for a file. */
function fixture(files: Record<string, string>): {
  src: string;
  dir: string;
  name: (f: string) => string;
} {
  const dir = mkdtempSync(join(tmpdir(), "sig-paths-"));
  const src = join(dir, "src", "pages");
  mkdirSync(src, { recursive: true });
  for (const [n, text] of Object.entries(files)) {
    writeFileSync(join(src, n), text);
  }
  return {
    src: join(dir, "src"),
    dir,
    name: (f: string) => relative(WEB_ROOT, join(src, f)),
  };
}

const BASELINE_SHAPE = (
  sites: number,
  files: Record<string, number>,
  allowlist: unknown[] = [],
) =>
  JSON.stringify({
    schema: "sig.path-containment-baseline/1",
    measured_at: "2026-10-19T00:00:00Z",
    rule: "fixture",
    scope: "fixture",
    sites,
    files,
    allowlist,
  });

function baselineAt(dir: string, json: string): string {
  const p = join(dir, "baseline.json");
  writeFileSync(p, json);
  return p;
}

describe("check-root-absolute-paths — verdict logic over planted fixtures", () => {
  it("a planted NEW root-absolute site fails the check", () => {
    const f = fixture({ "new-page.astro": '<a href="/escape/">x</a>' });
    const baseline = baselineAt(f.dir, BASELINE_SHAPE(0, {}));
    const r = run(["--src", f.src, "--baseline", baseline]);
    expect(r.status).toBe(1);
    expect(r.stderr + r.stdout).toContain("containment failure");
  });

  it("growth inside a baseline file fails (recorded → measured)", () => {
    const f = fixture({ "a.astro": '<a href="/x/">1</a><a href="/y/">2</a>' });
    const baseline = baselineAt(f.dir, BASELINE_SHAPE(1, { [f.name("a.astro")]: 1 }));
    const r = run(["--src", f.src, "--baseline", baseline]);
    expect(r.status).toBe(1);
    expect(r.stderr).toContain("growth");
  });

  it("an equal count passes", () => {
    const f = fixture({ "a.astro": '<a href="/x/">1</a>' });
    const baseline = baselineAt(f.dir, BASELINE_SHAPE(1, { [f.name("a.astro")]: 1 }));
    const r = run(["--src", f.src, "--baseline", baseline]);
    expect(r.status).toBe(0);
  });

  it("shrinkage passes with an advisory (the sweep lowers the baseline)", () => {
    const f = fixture({ "a.astro": "<p>no links</p>" });
    const baseline = baselineAt(f.dir, BASELINE_SHAPE(3, { [f.name("a.astro")]: 3 }));
    const r = run(["--src", f.src, "--baseline", baseline]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("shrink");
  });

  it("an allow-listed construction passes; beyond the cap it fails", () => {
    const guards = 'const a = p.endsWith("/"); const b = q.endsWith("/");';
    const f = fixture({ "a.astro": `---\n${guards}\n---\n<p>x</p>` });
    const ok = baselineAt(
      f.dir,
      BASELINE_SHAPE(0, {}, [
        { file: f.name("a.astro"), token: "/", count: 2, reason: "boundary checks" },
      ]),
    );
    expect(run(["--src", f.src, "--baseline", ok]).status).toBe(0);

    const f2 = fixture({ "a.astro": `---\n${guards} const c = r.endsWith("/");\n---\n<p>x</p>` });
    const over = baselineAt(
      f2.dir,
      BASELINE_SHAPE(0, {}, [
        { file: f2.name("a.astro"), token: "/", count: 2, reason: "cap" },
      ]),
    );
    expect(run(["--src", f2.src, "--baseline", over]).status).toBe(1);
  });

  it("the real tree holds against the committed baseline (the gate itself)", () => {
    const r = run([]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("containment holds");
  });

  it("an empty measurement is vacuous, never a silent green (SIG-ENG-042)", () => {
    const f = fixture({ "a.md": "# no site-bearing extension" });
    const baseline = baselineAt(f.dir, BASELINE_SHAPE(0, {}));
    const r = run(["--src", f.src, "--baseline", baseline]);
    expect(r.status).toBe(3);
  });
});
