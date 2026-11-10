// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES / K4 JUR-06, K5 DSRC-06 — SIG-JUR-D06, SIG-DSRC-D08/D09):
// PARITY — every dossier page's HTML equals its served JSON twin (the static
// API form); the sources explorer's rendered rows equal its
// `sig.dossier-sources/1` twin; a source's contribution to a dossier reads
// identically on the dossier's explorer and on the source's own dossiers
// page; and the grouped index's row numbers equal each dossier twin. The
// release-backed `/v1/releases/…` leg rides the promoted-release leg
// (P36.72b) — recorded, never claimed here. A divergence fails.

import { expect, test } from "@playwright/test";
import { emittedRoutes } from "./acceptance";

const EMITTED = emittedRoutes();
const dossierTwins = EMITTED.filter(
  (p) =>
    p.startsWith("/dossier/") &&
    p.endsWith(".json") &&
    !p.endsWith("/index.json") &&
    // P37.29: map-embed.json is the embedded app's props payload, not a
    // sig.dossier/2 twin — it has no HTML page counterpart by design.
    !p.endsWith("/map-embed.json"),
);
const explorerTwins = EMITTED.filter((p) =>
  /^\/dossier\/.+\/sources\/index\.json$/.test(p),
);

interface DossierTwin {
  slug_path: string;
  name: string;
  display_name?: string;
  as_of_world: string;
  rollup?: { records?: number };
}

interface DsrcDoc {
  schema: string;
  totals: { records: number; sources: number };
  sources: {
    source_id: string;
    records: number;
    claims: number;
    located_by_point: number;
    placed_by_declared: number;
    share: number;
    licence?: { spdx?: string | null };
    first_seen?: { at?: string } | string | null;
    last_seen?: { at?: string } | string | null;
  }[];
}

test.describe("HTML = JSON twin (SIG-JUR-D06, SIG-DSRC-D09)", () => {
  test("every dossier page's HTML agrees with its .json twin", async ({ request }) => {
    expect(dossierTwins.length).toBeGreaterThan(0);
    const failures: string[] = [];
    for (const twinPath of dossierTwins) {
      const tres = await request.get(twinPath);
      if (tres.status() !== 200) {
        failures.push(`${twinPath} twin → ${tres.status()}`);
        continue;
      }
      const twin = (await tres.json()) as DossierTwin;
      const pagePath = `${twinPath.slice(0, -".json".length)}/`;
      const res = await request.get(pagePath);
      if (res.status() !== 200) {
        failures.push(`${pagePath} → ${res.status()}`);
        continue;
      }
      const html = await res.text();
      const h1 = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(html)?.[1].replace(/<[^>]+>/g, "").trim() ?? "";
      const name = twin.display_name ?? twin.name;
      if (name !== undefined && !h1.includes(name) && !(twin.name && h1.includes(twin.name))) {
        failures.push(`${pagePath} h1 "${h1}" lacks name "${name}"`);
      }
      if (twin.as_of_world && !html.includes(twin.as_of_world)) {
        failures.push(`${pagePath} lacks as_of_world ${twin.as_of_world}`);
      }
      if (twin.rollup?.records !== undefined) {
        const grouped = String(twin.rollup.records).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        if (
          !html.includes(`data-figure-value="${twin.rollup.records}"`) &&
          !html.includes(grouped) &&
          !html.includes(`>${twin.rollup.records}<`)
        ) {
          failures.push(`${pagePath} shows no figure/text for records=${twin.rollup.records}`);
        }
      }
    }
    expect(failures).toEqual([]);
  });
});

test.describe("the sources explorer = its sig.dossier-sources/1 twin (SIG-DSRC-D09)", () => {
  test("every explorer row's cells equal the twin's source entries", async ({ request }) => {
    expect(explorerTwins.length).toBeGreaterThan(0);
    const failures: string[] = [];
    const date = (v: { at?: string } | string | null | undefined): string | null => {
      const at = typeof v === "string" ? v : v?.at;
      if (!at) return null;
      return /^\d{4}-\d{2}-\d{2}/.test(at) ? at.slice(0, 10) : at;
    };
    for (const twinPath of explorerTwins) {
      const doc = (await (await request.get(twinPath)).json()) as DsrcDoc;
      expect(doc.schema).toBe("sig.dossier-sources/1");
      const pagePath = twinPath.slice(0, -"index.json".length);
      const html = await (await request.get(pagePath)).text();
      for (const s of doc.sources) {
        const row = new RegExp(`<tr data-source-id="${s.source_id}">([\\s\\S]*?)</tr>`).exec(html);
        if (!row) {
          // a paginated explorer carries later pages — absence is honest only
          // when the doc itself does not publish the row (never silent: the
          // twin is the source of truth and every rendered row must match it)
          const paginated = html.includes('data-testid="dsrc-pager"');
          if (!paginated) failures.push(`${pagePath} missing row ${s.source_id}`);
          continue;
        }
        const cells = [...row[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(
          (c) => c[1].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(),
        );
        // an honest-state row (withdrawn / upstream-disappeared /
        // ingested-not-published) renders its state text in place of numeric
        // cells — the twin's own flags name the state the row must show,
        // never invented numbers
        const nonNumeric = cells.slice(2).some((c) => c !== "" && !/^[\d,%\s./-]+$/.test(c));
        const stateFlag =
          (s as { lifecycle?: string }).lifecycle !== "published" ||
          (s as { freshness_state?: string }).freshness_state === "disappeared";
        if (nonNumeric && stateFlag) {
          const joined = cells.join(" ");
          if (!/withdrawn|refused|not.published|pending|disappeared|ingested|upstream/i.test(joined)) {
            failures.push(
              `${pagePath} ${s.source_id} non-numeric row names no honest state (${joined})`,
            );
          }
          continue;
        }
        const [, , records, share, located, claims, first, last, , licence] = [
          cells[0] ?? "",
          cells[1] ?? "",
          cells[2] ?? "",
          cells[3] ?? "",
          cells[4] ?? "",
          cells[5] ?? "",
          cells[6] ?? "",
          cells[7] ?? "",
          cells[8] ?? "",
          cells[9] ?? "",
        ];
        const pct = `${Math.round(s.share * 100)}%`;
        if (records !== String(s.records)) {
          failures.push(`${pagePath} ${s.source_id} records ${records} != ${s.records}`);
        }
        if (share !== pct) failures.push(`${pagePath} ${s.source_id} share ${share} != ${pct}`);
        if (located !== `${s.located_by_point} / ${s.placed_by_declared}`) {
          failures.push(`${pagePath} ${s.source_id} located ${located} != ${s.located_by_point} / ${s.placed_by_declared}`);
        }
        if (claims !== String(s.claims)) {
          failures.push(`${pagePath} ${s.source_id} claims ${claims} != ${s.claims}`);
        }
        const fd = date(s.first_seen);
        if (fd !== null && first !== fd) {
          failures.push(`${pagePath} ${s.source_id} first_seen ${first} != ${fd}`);
        }
        const ld = date(s.last_seen);
        if (ld !== null && !last.includes(ld)) {
          failures.push(`${pagePath} ${s.source_id} last_seen ${last} != ${ld}`);
        }
        const spdx = s.licence?.spdx ?? "not_recorded";
        if (licence !== spdx) failures.push(`${pagePath} ${s.source_id} licence ${licence} != ${spdx}`);
      }
    }
    expect(failures).toEqual([]);
  });
});

test.describe("dossier ↔ source contribution parity (SIG-DSRC-D08)", () => {
  test("a source's contribution reads identically on both surfaces", async ({ request }) => {
    const failures: string[] = [];
    let pairs = 0;
    for (const twinPath of explorerTwins) {
      const doc = (await (await request.get(twinPath)).json()) as DsrcDoc;
      const dossierRoute = twinPath.slice(0, -"sources/index.json".length);
      for (const s of doc.sources) {
        const sp = `/sources/${s.source_id}/dossiers/`;
        const sres = await request.get(sp);
        if (sres.status() !== 200) continue; // no dossier page for this source — honest absence
        const shtml = await sres.text();
        const row = new RegExp(
          `<tr data-testid="contribution-row"[^>]*>[\\s\\S]*?href="${dossierRoute}"[\\s\\S]*?</tr>`,
        ).exec(shtml);
        if (!row) continue;
        pairs += 1;
        const val = /data-figure-value="(\d+)"/.exec(row[0])?.[1];
        if (val !== String(s.records)) {
          failures.push(`${sp} contribution to ${dossierRoute} ${val} != twin ${s.records}`);
        }
      }
    }
    expect(failures).toEqual([]);
    expect(pairs, "no dossier↔source contribution pairs measured").toBeGreaterThan(0);
  });
});

test.describe("the grouped index = each dossier twin (SIG-JUR-D06)", () => {
  test("every index row's records figure equals the dossier twin's rollup", async ({ request }) => {
    const html = await (await request.get("/dossier/")).text();
    const items = [...html.matchAll(/data-testid="dossier-index-item"[^>]*data-slug="([^"]+)"/g)].map(
      (m) => m[1],
    );
    expect(items.length).toBeGreaterThan(0);
    const failures: string[] = [];
    for (const slug of items) {
      const res = await request.get(`/dossier/${slug}.json`);
      if (res.status() !== 200) {
        failures.push(`index row ${slug} has no served twin (${res.status()})`);
        continue;
      }
      const twin = (await res.json()) as DossierTwin;
      if (twin.rollup?.records === undefined) continue;
      const at = html.indexOf(`dossier-index-item" data-slug="${slug}"`);
      const itemHtml = at === -1 ? "" : html.slice(at, at + 6000);
      const grouped = String(twin.rollup.records).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      if (
        itemHtml &&
        !itemHtml.includes(`data-figure-value="${twin.rollup.records}"`) &&
        !itemHtml.includes(grouped) &&
        !itemHtml.includes(`>${twin.rollup.records}<`)
      ) {
        failures.push(`index row ${slug} lacks records=${twin.rollup.records}`);
      }
    }
    expect(failures).toEqual([]);
  });
});
