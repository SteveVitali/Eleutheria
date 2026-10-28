// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.24 (K13 UXK14-5; SIG-UI-063/144/153 owner, DR-C6-28 + DR-K14-10/11/19,
 * SIG-ENG-042 — never a vacuous green). Each test drives the real script
 * (`web/scripts/check-copy-lints.mjs`) over a planted dist tree — a planted
 * `page-types.json` manifest plus planted pages — and asserts the verdict
 * logic both ways: the planted violation reports, the compliant page passes,
 * and the report→enforce flip turns the same finding into a failure. Nothing
 * asserts a count from the living dist build (OM-15).
 */

import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const SCRIPT = fileURLToPath(
  new URL("../../scripts/check-copy-lints.mjs", import.meta.url),
);
const ENFORCE = fileURLToPath(
  new URL("../../scripts/copy-lint-enforce.json", import.meta.url),
);

interface Run {
  status: number | null;
  stdout: string;
  stderr: string;
}

function run(args: string[]): Run {
  const r = spawnSync(process.execPath, [SCRIPT, ...args], { encoding: "utf-8" });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

const MANIFEST = (routes: { path: string; file: string; pattern?: string }[]) =>
  JSON.stringify({
    schema: "sig.page-types-manifest/1",
    routes: routes.map((r) => ({
      path: r.path,
      file: r.file,
      type: "T1",
      pattern: r.pattern ?? `${r.path}**`,
      owner: "test",
      contract: "fixture",
      chrome: "full",
      internal: false,
    })),
  });

const PAGE = (body: string, footer = "") =>
  `<!doctype html><html><body><main>${body}</main>` +
  `<footer>${footer || "<p>Built from 2 sources · data as of 2026-10-01</p>"}</footer></body></html>`;

const REGISTRY = (routes: Record<string, unknown> = {}, defaultMode = "report") =>
  JSON.stringify({ schema: "sig.copy-lint-enforce/1", defaultMode, routes });

/** A planted dist tree + enforce file; returns the CLI flags to point at it. */
function fixture(
  pages: Record<string, string>,
  registry = REGISTRY(),
): { dist: string; registry: string; args: string[] } {
  const dir = mkdtempSync(join(tmpdir(), "sig-copylint-"));
  const dist = join(dir, "dist");
  mkdirSync(dist, { recursive: true });
  const routes: { path: string; file: string }[] = [];
  for (const [route, html] of Object.entries(pages)) {
    const file = join(dist, route, "index.html");
    mkdirSync(join(dist, route), { recursive: true });
    writeFileSync(file, html);
    routes.push({ path: `/${route}/`, file: `${route}/index.html` });
  }
  writeFileSync(join(dist, "page-types.json"), MANIFEST(routes));
  const regFile = join(dir, "enforce.json");
  writeFileSync(regFile, registry);
  return { dist, registry: regFile, args: ["--dist", dist, "--enforce", regFile] };
}

const COMPLIANT = PAGE(
  "<p>Twelve records sit on this short page.</p><p>Each sentence here differs.</p>",
);

describe("check-copy-lints — verdict logic over planted fixtures", () => {
  it("a compliant page passes in report mode", () => {
    const f = fixture({ ok: COMPLIANT });
    const r = run(f.args);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("PASS");
    expect(r.stdout).toContain("1 routes scanned");
  });

  it("'camera sites' where 'records' belongs reports — and fails once enforced (SIG-UI-063)", () => {
    const page = PAGE("<p>The map shows 58 camera sites.</p>");
    const report = fixture({ place: page });
    const r1 = run(report.args);
    expect(r1.status).toBe(0);
    expect(r1.stdout).toContain("[records-vs-sites]");
    const enforced = fixture({ place: page }, REGISTRY({ "/place/**": "enforce" }));
    const r2 = run(enforced.args);
    expect(r2.status).toBe(1);
    expect(r2.stderr).toContain("FAIL");
  });

  it("'records' inside a dedup interval fails the other way; the site word passes", () => {
    const bad = fixture({
      place: PAGE('<p><span data-sig-count="dedup">about 10 records</span></p>'),
    });
    const r1 = run(bad.args);
    expect(r1.status).toBe(0);
    expect(r1.stdout).toContain("[records-vs-sites]");
    const good = fixture({
      place: PAGE(
        '<p>58 records <span data-sig-count="dedup">about 10 camera sites</span>.</p>',
      ),
    });
    expect(run(good.args).stdout).not.toContain("[records-vs-sites]");
  });

  it("a bare plural 'cameras' reports (SIG-UI-063)", () => {
    const f = fixture({ place: PAGE("<p>We list 58 cameras here.</p>") });
    expect(run(f.args).stdout).toContain("[records-vs-sites]");
  });

  it("a repeated 8+ word sentence reports (SIG-UI-144)", () => {
    const s = "This sentence has more than eight words in it.";
    const f = fixture({ page: PAGE(`<p>${s}</p><p>Other text.</p><p>${s}</p>`) });
    expect(run(f.args).stdout).toContain("[repeated-sentence]");
  });

  it("visible-by-default chrome over 40 words reports (SIG-UI-145)", () => {
    const long = Array.from({ length: 45 }, (_, i) => `word${i}`).join(" ");
    const f = fixture({ page: PAGE("<p>body</p>", `<p>${long}</p>`) });
    expect(run(f.args).stdout).toContain("[chrome-words]");
    const collapsed = fixture({
      page: PAGE("<p>body</p>", `<details><p>${long}</p></details><p>short</p>`),
    });
    expect(run(collapsed.args).stdout).not.toContain("[chrome-words]");
  });

  it("joined words report both shapes (SIG-UI-153)", () => {
    const punct = fixture({ page: PAGE("<p>records.The next line.</p>") });
    expect(run(punct.args).stdout).toContain("[joined-punct]");
    const boundary = fixture({
      page: PAGE('<p>a concern?<a href="/x/">records</a></p>'),
    });
    expect(run(boundary.args).stdout).toContain("[joined-boundary]");
  });

  it("an ungrouped 5+ digit run reports; grouped and <time> pass (SIG-UI-153)", () => {
    const bad = fixture({ page: PAGE("<p>The corpus holds 12345 records.</p>") });
    expect(run(bad.args).stdout).toContain("[ungrouped-digits]");
    const good = fixture({
      page: PAGE(
        "<p>The corpus holds 12,345 records, stamped <time>20261028</time>.</p>",
      ),
    });
    expect(run(good.args).stdout).not.toContain("[ungrouped-digits]");
  });

  it("ids in prose report (DR-C6-28); technical blocks exempt", () => {
    const bad = fixture({
      page: PAGE(
        "<p>See SIG-UI-063 for the record_count of 3fa85f64-5717-4562-b3fc-2c963f66afa6.</p>",
      ),
    });
    const out = run(bad.args).stdout;
    expect(out).toContain("[req-id]");
    expect(out).toContain("[snake-case]");
    expect(out).toContain("[uuid]");
    const exempt = fixture({
      page: PAGE(
        '<div data-technical-details><p>record_count 3fa85f64-5717-4562-b3fc-2c963f66afa6</p></div>' +
          '<details class="sig-spec-refs"><summary>Spec references</summary><code>SIG-UI-063</code></details>',
      ),
    });
    expect(run(exempt.args).stdout).not.toMatch(/\[(req-id|snake-case|uuid)\]/);
  });

  it("a raw enum and a bare 'unknown' report", () => {
    const f = fixture({
      page: PAGE("<p>The value is STRONGLY_SUPPORTED and the operator unknown.</p>"),
    });
    const out = run(f.args).stdout;
    expect(out).toContain("[enum]");
    expect(out).toContain("[bare-unknown]");
  });

  it("provisional records / candidate values report (SIG-UI-062)", () => {
    const f = fixture({
      page: PAGE("<p>These provisional records carry a candidate estimate.</p>"),
    });
    const out = run(f.args).stdout;
    expect(out).toContain("[candidate-vs-provisional]");
  });

  it("a banned vocabulary phrasing reports; the glossary defines freely", () => {
    const f = fixture({
      place: PAGE("<p>Each observation-level record joins the rest.</p>"),
    });
    expect(run(f.args).stdout).toContain("[vocabulary]");
    const gloss = fixture({
      glossary: PAGE("<p>camera site: the de-duplicated physical camera.</p>"),
    });
    expect(run(gloss.args).stdout).not.toContain("[records-vs-sites]");
  });

  it("the readability report prints but never fails (CP-8)", () => {
    const long = Array.from({ length: 30 }, (_, i) => `w${i}`).join(" ");
    const f = fixture({ page: PAGE(`<p>${long}. ${long}. ${long}.</p>`) });
    const r = run(f.args);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("readability");
  });

  it("an except-listed rule on an enforced route passes", () => {
    const page = PAGE("<p>The map shows 58 camera sites.</p>");
    const f = fixture(
      { place: page },
      REGISTRY({ "/place/**": { mode: "enforce", except: ["records-vs-sites"] } }),
    );
    expect(run(f.args).status).toBe(0);
  });

  it("no <main> is skipped, never scanned; all-skipped is vacuous (SIG-ENG-042)", () => {
    const f = fixture({ stub: "<html><body><p>redirect</p></body></html>" });
    const r = run(f.args);
    expect(r.status).toBe(3);
    expect(r.stderr).toContain("VACUOUS");
  });

  it("a missing manifest is an input error, never a silent green", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-copylint-nodist-"));
    const r = run(["--dist", join(dir, "dist"), "--enforce", ENFORCE]);
    expect(r.status).toBe(2);
  });

  it("the committed enforce registry parses and defaults to report", () => {
    // read the real committed file, never a planted copy
    const registry = JSON.parse(readFileSync(ENFORCE, "utf8"));
    expect(registry.schema).toBe("sig.copy-lint-enforce/1");
    expect(registry.defaultMode).toBe("report");
  });
});
