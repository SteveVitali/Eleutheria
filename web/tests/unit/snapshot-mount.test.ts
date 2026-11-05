// SPDX-License-Identifier: Apache-2.0
// P36.66a (SIG-REL-008): the check-snapshot-mount scan rule — planted escaping
// links fail, declared exceptions pass, vacuous is never a silent green.
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { scanHtml, SNAPSHOT_BASE } from "../../scripts/check-snapshot-mount.mjs";

const run = (html: string) => scanHtml(html);

describe("check-snapshot-mount scan rule (P36.66a, SIG-REL-008)", () => {
  it("in-base links pass", () => {
    expect(run(`<a href="${SNAPSHOT_BASE}dossier/x/">x</a><link href="${SNAPSHOT_BASE}favicon.svg">`)).toEqual([]);
  });
  it("a root-absolute escape fails", () => {
    const vs = run(`<a href="/dossier/x/">x</a>`);
    expect(vs.length).toBe(1);
    expect(vs[0]).toContain("escapes the snapshot base");
  });
  it("declared exceptions pass (/r/, /releases/, /v1/, /intake/)", () => {
    expect(
      run(
        `<a href="/r/p-abc/c/g/">r</a><a href="/releases/p-abc/">rel</a>` +
          `<a href="/v1/claim/x">api</a><a href="/intake/new">intake</a>`,
      ),
    ).toEqual([]);
  });
  it("protocol-relative is a failure on its own", () => {
    expect(run(`<a href="//evil.example/x">x</a>`).length).toBe(1);
  });
  it("absolute same-origin: in-base + selector + exception paths pass, others fail", () => {
    const good =
      `<a href="https://surveillancegraph.org${SNAPSHOT_BASE}dossier/x/">a</a>` +
      `<a href="https://surveillancegraph.org/dossier/x/?as_of_world=2026&as_of_belief=2026">sel</a>` +
      `<a href="https://surveillancegraph.org/r/p-x/">r</a>`;
    expect(run(good)).toEqual([]);
    expect(run(`<link rel="canonical" href="https://surveillancegraph.org/dossier/x/">`).length).toBe(1);
  });
  it("the --src leg exits 1 on a planted escape and 0 on a clean file", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-snap-src-"));
    const bad = join(dir, "bad.html");
    const ok = join(dir, "ok.html");
    writeFileSync(bad, `<a href="/escape/">x</a>`);
    writeFileSync(ok, `<a href="${SNAPSHOT_BASE}x/">x</a>`);
    const script = new URL("../../scripts/check-snapshot-mount.mjs", import.meta.url).pathname;
    expect(() => execFileSync("node", [script, "--src", bad], { stdio: "pipe" })).toThrow();
    expect(() => execFileSync("node", [script, "--src", ok], { stdio: "pipe" })).not.toThrow();
  });
});
