// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.19 (UXK0-3, K0 §4.8, SIG-ENG-042): the check-unsafe-dom.mjs mechanism
 * tests — the ban is proven on planted fixtures, never assumed. Each test
 * drives the real script over a planted tree (the same convention as
 * root-absolute-paths-check.test.ts): a violating file fails, comments that
 * NAME the sinks pass, an empty tree is vacuous — never a silent green.
 */

import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const SCRIPT = fileURLToPath(
  new URL("../../scripts/check-unsafe-dom.mjs", import.meta.url),
);

function fixture(files: Record<string, string>): string {
  const dir = mkdtempSync(join(tmpdir(), "sig-dom-"));
  const src = join(dir, "src");
  mkdirSync(src, { recursive: true });
  for (const [n, text] of Object.entries(files)) writeFileSync(join(src, n), text);
  return src;
}

function run(src: string) {
  return spawnSync(process.execPath, [SCRIPT, "--src", src, "--list"], {
    encoding: "utf-8",
  });
}

describe("check-unsafe-dom.mjs", () => {
  it("fails on innerHTML, dangerouslySetInnerHTML and MapLibre setHTML", () => {
    const src = fixture({
      "a.ts": 'const el = document.createElement("div");\nel.innerHTML = "<b>x</b>";\n',
      "b.tsx": "export const C = () => <div dangerouslySetInnerHTML={{ __html: x }} />;\n",
      "c.ts": 'import { Popup } from "maplibre-gl";\nnew Popup().setHTML("<b>x</b>");\n',
      "d.ts": 'x.insertAdjacentHTML("beforeend", s);\ny.outerHTML = s;\ndocument.write(s);\n',
    });
    const r = run(src);
    expect(r.status).toBe(1);
    for (const token of [
      "innerHTML",
      "dangerouslySetInnerHTML",
      "setHTML",
      "insertAdjacentHTML",
      "outerHTML",
      "document.write",
    ]) {
      expect(r.stderr + r.stdout).toContain(token);
    }
  });

  it("passes on sink names inside comments (the ban is on use)", () => {
    const src = fixture({
      "a.ts":
        '// client code renders text only: no innerHTML, no dangerouslySetInnerHTML,\n' +
        "// no MapLibre setHTML — the grep bans USE, never the name in prose.\n" +
        "/* outerHTML, insertAdjacentHTML and document.write are named here too. */\n" +
        'const el = document.createElement("div");\nel.textContent = "safe";\n',
    });
    const r = run(src);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("0 hit(s)");
  });

  it("is vacuous-failing on an empty tree (SIG-ENG-042)", () => {
    const r = run(fixture({}));
    expect(r.status).toBe(3);
    expect(r.stderr + r.stdout).toContain("VACUOUS");
  });

  it("the committed web/src tree scans clean", () => {
    const webRoot = fileURLToPath(new URL("../../src", import.meta.url));
    const r = run(webRoot);
    expect(r.status).toBe(0);
  });
});
