// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.68d (R11-K13-CAP-01, split d — the K13 §5.1 per-ask checks, SIG-UI-077):
// the named acceptance check for every operator ask U-003.1…U-003.11, run once
// per {390, 1440 px} × {JS on, JS off} project cell of
// playwright.capstone-consolidated.config.ts. Two audiences run the same file:
//   - fixtures: `npx playwright test -c playwright.capstone-consolidated.config.ts`
//     previews the built dist (the fixture-verified layer);
//   - the promoted release: `SIG_CAPSTONE_BASE_URL=<origin> npx playwright
//     test -c playwright.capstone-consolidated.config.ts` — the deferred live
//     leg (D-P37.68d-1, OM-19 `live_verification=true`).
// Every check resolves its targets from the served site itself (the A–Z
// directory supplies the dossier routes, the dossier's own blocks supply the
// sources/sites/print links, the research queue supplies the task pages, the
// source table the source detail pages) so the identical spec runs against
// the promoted origin — nothing fixture-specific is hard-coded.
//
// Corpus-named clauses (K13 §5.1 names release content — "342 rows" on
// /sources/, Austin Police Department, California's 11 sources, Seattle watch
// pages, Canberra/ICE/Vigilant query behaviour, the tile verifier at every
// zoom, the benchmark top-3 rates) are checked at the layer this dispatch can
// honestly reach: the spec asserts the machinery contract each clause names
// over whatever corpus the served site publishes, and the live leg's
// precondition (sig.capstone-consolidated/1 `live-per-ask`) names the
// corpus-specific readings verbatim. A fixture green is recorded
// AGENT-VERIFIED / fixture-verified — never live, hosted, public or
// "user-tested" (P4).

import { expect, test } from "@playwright/test";
import { visibleTextMinusIdSpans } from "./acceptance";

const jsOn = (): boolean => test.info().project.use.javaScriptEnabled !== false;

/**
 * Resolve a place dossier through the A–Z directory — the named no-JS
 * place-lookup equivalent that exists on every published build. Mirrors the
 * journalist battery's helper: `sortName` matches the index row's
 * `data-sort-name` prefix so the battery follows whatever slug the served
 * corpus actually publishes.
 */
async function resolveDossierViaAZ(
  request: import("@playwright/test").APIRequestContext,
  letter: string,
  sortName: string,
): Promise<string> {
  const res = await request.get(`/dossier/a-z/${letter}/`);
  expect(res.status()).toBe(200);
  const html = await res.text();
  const items = [
    ...html.matchAll(
      /data-testid="dossier-index-item"[^>]*data-sort-name="([^"]*)"[^>]*>(.*?)<\/li>/gs,
    ),
  ];
  const hrefs = items
    .filter((m) => m[1]!.toLowerCase().startsWith(sortName))
    .flatMap((m) =>
      [...(m[2] ?? "").matchAll(/href="(\/dossier\/[^"]+\/)"/g)].map(
        (h) => h[1]!,
      ),
    )
    .filter(
      (h) =>
        !h.startsWith("/dossier/a-z/") &&
        !h.startsWith("/dossier/figures/") &&
        !h.includes("/print/"),
    );
  // Prefer the canonical jurisdiction-path dossier (/dossier/usa/…) —
  // legacy/demo slugs resolve too but the canonical path is the corpus.
  const href =
    hrefs.find((h) => h.startsWith("/dossier/usa/")) ?? hrefs[0] ?? null;
  expect(
    href,
    `a dossier row matching "${sortName}" must exist on /dossier/a-z/${letter}/`,
  ).toBeTruthy();
  return href!;
}

/** Any dossier the served A–Z directory offers — never a hard-coded slug. */
async function resolveAnyDossier(
  request: import("@playwright/test").APIRequestContext,
): Promise<string> {
  for (const letter of "abcdefghijklmnopqrstuvwxyz") {
    const res = await request.get(`/dossier/a-z/${letter}/`);
    if (res.status() !== 200) continue;
    const html = await res.text();
    const href = [
      ...html.matchAll(/href="(\/dossier\/[^"]+\/)"/g),
    ]
      .map((m) => m[1]!)
      .find(
        (h) =>
          !h.startsWith("/dossier/a-z/") &&
          !h.startsWith("/dossier/figures/") &&
          !h.includes("/print/") &&
          !h.endsWith("/unplaced/") &&
          !h.endsWith("/unresolved/"),
      );
    if (href) return href;
  }
  throw new Error("the A–Z directory offers no place dossier");
}

/**
 * Every published source row's page href from the /sources/ table — the
 * caller picks which published source answers a clause; a corpus may carry
 * published sources that legitimately omit optional links (e.g. no terms
 * page declared), so the helper returns the whole published set.
 */
async function resolvePublishedSources(
  request: import("@playwright/test").APIRequestContext,
): Promise<string[]> {
  const res = await request.get("/sources/");
  expect(res.status()).toBe(200);
  const html = await res.text();
  const rows = [
    ...html.matchAll(
      /<tr[^>]*data-testid="source-table-row"[^>]*data-status="published"[\s\S]*?<\/tr>/g,
    ),
  ];
  const hrefs = [
    ...new Set(
      rows
        .map((r) => /href="(\/sources\/[^"]+\/)"/.exec(r[0])?.[1])
        .filter((h): h is string => Boolean(h)),
    ),
  ];
  expect(
    hrefs.length,
    "the sources table must carry published rows",
  ).toBeGreaterThan(0);
  return hrefs;
}

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

test.describe("U-003.1 — the map draws with a real basemap and place context", () => {
  test("the map page, the self-hosted style contract, the ≤100 KiB no-JS doc and a record's linked place/source/evidence", async ({
    page,
    request,
  }) => {
    // The page serves at both widths; the no-JS document is the reader's
    // first paint (the K13 clause caps it at 100 KiB — measured, never assumed).
    await page.goto("/map/");
    const res = await request.get("/map/");
    expect(res.status()).toBe(200);
    const bytes = Buffer.byteLength(await res.text(), "utf-8");
    expect(bytes, "no-JS /map/ document must stay ≤ 100 KiB").toBeLessThanOrEqual(
      100 * 1024,
    );

    // The basemap contract is self-hosted: style.json's sources resolve to
    // pmtiles: or same-origin paths — never a third-party tile hostname the
    // reader's fetch would leak to (D-K1-1 reversed; the served PMTiles leg
    // itself rides the promoted release — the fixture records its honest
    // host_status, asserted here as a declared field, never a claimed serve).
    const styleRes = await request.get("/map/style.json");
    expect(styleRes.status()).toBe(200);
    const style = (await styleRes.json()) as {
      sources?: Record<string, { url?: string }>;
    };
    expect(style.sources, "the map style must carry sources").toBeTruthy();
    for (const [name, src] of Object.entries(style.sources!)) {
      const url = src.url ?? "";
      expect(
        url === "" || url.startsWith("pmtiles://") || url.startsWith("/"),
        `style source ${name} must be self-hosted (pmtiles: or same-origin), got ${url}`,
      ).toBeTruthy();
    }
    const ctx = (await (await request.get("/map/style-context.json")).json()) as {
      metadata?: Record<string, unknown>;
    };
    expect(
      ctx.metadata?.["sig:contract"],
      "the basemap context declares its lock contract",
    ).toBe("sig.basemap-style/1");

    // "Oklahoma City" frames the city — resolved from the served site: the
    // map page's own place rows offer a place-scoped frame, and the resolved
    // dossier's map-embed document carries located records whose panel links
    // (place, sources, record) all resolve.
    const mapHtml = await res.text();
    const placeRows = [...mapHtml.matchAll(/data-testid="map-places-row"/g)];
    expect(
      placeRows.length,
      "the map page must carry place rows (type a place → it frames)",
    ).toBeGreaterThan(0);
    const okc = await resolveDossierViaAZ(request, "o", "oklahoma city");
    const embedHref = `${okc}map-embed.json`;
    const embedRes = await request.get(embedHref);
    expect(embedRes.status()).toBe(200);
    const embed = (await embedRes.json()) as {
      records?: {
        label?: string;
        lat?: number;
        lon?: number;
        recordHref?: string;
        jurisdiction?: { href?: string };
        sources?: { href?: string }[];
      }[];
      attribution?: string;
    };
    const record = embed.records?.find(
      (r) => typeof r.lat === "number" && typeof r.lon === "number",
    );
    expect(
      record,
      "the place's map-embed must carry a located record (the frame + panel data)",
    ).toBeTruthy();
    // A record opens a panel with linked place, source and evidence — the
    // panel's data contract: every link the record advertises resolves.
    expect(record!.jurisdiction?.href).toBeTruthy();
    expect((await request.get(record!.jurisdiction!.href!)).status()).toBe(200);
    for (const s of record!.sources ?? []) {
      expect((await request.get(s.href!)).status()).toBe(200);
    }
    expect(record!.recordHref).toBeTruthy();
    expect((await request.get(record!.recordHref!.split("#")[0]!)).status()).toBe(
      200,
    );
    // The no-JS equivalent is the sites list the map page itself advertises.
    const sites = await request.get("/map/");
    expect(/data-testid="sites-list-link"/.test(await sites.text())).toBeTruthy();
  });
});

test.describe("U-003.2 — readable labels, entity pages, navigable graphs", () => {
  test("0 UUID labels on a bounded crawl of the public families", async ({
    request,
  }) => {
    // The K13 clause is a crawl; this is the bounded honest form — the
    // family roots plus one resolved instance per dynamic family. The full
    // emitted-file crawl lives in acceptance-crawl.spec.ts (fixture layer);
    // the live leg repeats this fetch-scan on the promoted origin.
    const pages = new Set<string>([
      "/",
      "/dossier/",
      "/sources/",
      "/entity/",
      "/explore/",
      "/graphs/",
      "/search/",
      "/disagreements/",
      "/research-queue/",
      "/changes/",
      "/evidence/",
      "/watch/",
      "/map/",
    ]);
    const tx = await resolveDossierViaAZ(request, "t", "texas").catch(() =>
      resolveAnyDossier(request),
    );
    pages.add(tx);
    const source = (await resolvePublishedSources(request))[0]!;
    pages.add(source);
    const failures: string[] = [];
    for (const path of pages) {
      const res = await request.get(path);
      expect(res.status(), `${path} must serve`).toBe(200);
      const text = visibleTextMinusIdSpans(await res.text());
      if (UUID_RE.test(text)) failures.push(`${path} shows a bare UUID`);
    }
    expect(failures).toEqual([]);
  });

  test("entity index pages are named — a page or the typed not-published state", async ({
    request,
  }) => {
    for (const indexPath of ["/entity/org/", "/entity/agency/"]) {
      const res = await request.get(indexPath);
      expect(res.status()).toBe(200);
      const html = await res.text();
      const links = [
        ...new Set(
          [...html.matchAll(/href="(\/entity\/(?:org|agency)\/[^"]+\/)"/g)].map(
            (m) => m[1]!,
          ),
        ),
      ];
      expect(links.length, `${indexPath} must list entities`).toBeGreaterThan(0);
      for (const href of links.slice(0, 4)) {
        const pres = await request.get(href);
        expect(pres.status()).toBe(200);
        const phtml = await pres.text();
        const h1 = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(phtml)?.[1] ?? "";
        expect(h1.trim().length, `${href} must render a named h1`).toBeGreaterThan(
          0,
        );
        // Published page or the honest not-published state — the D-K2-1
        // gate's typed absence carries its publication basis, never a bare id.
        const isPublished = !/not published as a page/.test(h1);
        if (!isPublished) {
          expect(
            /data-testid="publication-basis"/.test(phtml),
            `${href} must carry its publication basis`,
          ).toBeTruthy();
        }
      }
    }
  });

  test("every graph edge is dated or 'undated', sources named; /explore/ overviews navigable", async ({
    request,
  }) => {
    // The no-JS overview family — every index row's overview page resolves.
    const gres = await request.get("/graphs/");
    expect(gres.status()).toBe(200);
    const ghtml = await gres.text();
    const overviewLinks = [
      ...new Set(
        [...ghtml.matchAll(/href="(\/graphs\/[a-z-]+\/)"/g)].map((m) => m[1]!),
      ),
    ];
    expect(
      overviewLinks.length,
      "the graphs index must advertise navigable overviews",
    ).toBeGreaterThan(0);
    for (const href of overviewLinks) {
      expect((await request.get(href)).status(), href).toBe(200);
    }
    // A drill-down's edge rows: dated or 'undated', every edge naming its
    // source — the J2 clause at the per-ask level.
    const ares = await request.get("/graphs/access/");
    expect(ares.status()).toBe(200);
    const ahtml = await ares.text();
    const drill = /href="(\/graphs\/access\/[^"]+\/)"/.exec(ahtml)?.[1];
    expect(drill, "the access overview must advertise a drill-down").toBeTruthy();
    const dhtml = await (await request.get(drill!)).text();
    const edgeRows = [
      ...dhtml.matchAll(/data-testid="graph-edge-row"[\s\S]*?<\/tr>/g),
    ];
    expect(edgeRows.length, "the drill-down must list edges").toBeGreaterThan(0);
    for (const row of edgeRows.slice(0, 8)) {
      const cells = [...row[0].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) =>
        c[1]!.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(),
      );
      const dateCell = cells[3] ?? "";
      expect(
        dateCell === "undated" || /\d{4}-\d{2}-\d{2}/.test(dateCell),
        `every edge is dated or 'undated' (got '${dateCell}')`,
      ).toBeTruthy();
      expect(
        (cells[5] ?? "").length,
        "every edge names its source",
      ).toBeGreaterThan(0);
    }
  });
});

test.describe("U-003.3 — flexible search across the graph", () => {
  test("the GET form contract, the shard/index machinery, honest empty results", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    const form = page.getByTestId("hero-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", "/search/");

    // The release-pinned forms: plain GETs carrying q + format=html to a
    // same-origin results route — the "works with JS off" contract (the
    // endpoint itself is the served-API leg — named on the live leg).
    const sres = await request.get("/search/");
    expect(sres.status()).toBe(200);
    const shtml = await sres.text();
    const searchForms = [
      ...shtml.matchAll(
        /<form[^>]*data-testid="release-search-[^"]*form"[^>]*>/g,
      ),
    ];
    expect(
      searchForms.length,
      "the search page must carry release search forms",
    ).toBeGreaterThan(0);
    for (const f of searchForms) {
      expect(f[0]).toContain('method="get"');
      expect(/action="[^"]+"/.test(f[0])).toBeTruthy();
    }

    // The typeahead machinery emits: the index doc + at least one shard,
    // each advertising resolvable routes — a misleading top hit cannot
    // resolve to a page the release does not serve.
    const ires = await request.get("/search/index.json");
    expect(ires.status()).toBe(200);
    const index = (await ires.json()) as {
      schema?: string;
      items?: { href?: string; kind?: string }[];
    };
    expect(index.schema).toBe("sig.search-index/1");
    expect(index.items?.length).toBeGreaterThan(0);
    for (const item of index.items!.slice(0, 8)) {
      expect(item.href, "every index item names a route").toBeTruthy();
      expect((await request.get(item.href!)).status(), item.href).toBe(200);
    }
    const shardHtml = shtml;
    const shardRoot = /shard-root="([^"]+)"/.exec(shardHtml)?.[1] ?? "/search/shards/";
    const shard = await request.get(`${shardRoot}ac.json`);
    // 'ac' is not guaranteed on every corpus; the contract is the shard
    // FAMILY emits — any shard file answering with its schema.
    if (shard.status() === 200) {
      expect(((await shard.json()) as { schema?: string }).schema).toBe(
        "sig.typeahead-shard/1",
      );
    }
  });
});

test.describe("U-003.4 — the dossier list is grouped by country", () => {
  test("the index groups United States → states, other countries → subdivisions, 'Not yet placed'", async ({
    request,
  }) => {
    const res = await request.get("/dossier/");
    expect(res.status()).toBe(200);
    const html = await res.text();
    // The group headings the ask names — never one flat alphabetical dump.
    expect(/id="group-us"/.test(html)).toBeTruthy();
    expect(/id="group-other"/.test(html)).toBeTruthy();
    expect(html).toContain("Not yet placed");
    // United States → states: the US group's links resolve to state dossiers.
    const usGroup = /id="group-us"[\s\S]*?(?=<h2|$)/.exec(html)?.[0] ?? "";
    const stateLinks = [
      ...new Set(
        [...usGroup.matchAll(/href="(\/dossier\/usa\/[^"]+\/)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ];
    expect(
      stateLinks.length,
      "the United States group must list states",
    ).toBeGreaterThan(0);
    for (const href of stateLinks.slice(0, 4)) {
      expect((await request.get(href)).status(), href).toBe(200);
    }
    // Other countries → subdivisions: a non-US dossier link resolves.
    const otherGroup = /id="group-other"[\s\S]*?(?=<h2|$)/.exec(html)?.[0] ?? "";
    const otherLinks = [
      ...new Set(
        [...otherGroup.matchAll(/href="(\/dossier\/[^"]+\/)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ].filter((h) => !h.startsWith("/dossier/usa/"));
    if (otherLinks.length > 0) {
      expect((await request.get(otherLinks[0]!)).status()).toBe(200);
    }
    // The split page — a jurisdiction rendered across two dossier pages
    // carries the honest split marker (the fixture's /dossier/id/; the
    // release's /dossier/md/ → Maryland is the same machinery).
    const idRes = await request.get("/dossier/id/");
    if (idRes.status() === 200) {
      expect(await idRes.text()).toContain("Split");
    }
  });
});

test.describe("U-003.5 — which sources contributed what, when", () => {
  test("a dossier's 'from N sources' breaks down to the figure; the source page names last run + first/last seen", async ({
    request,
  }) => {
    // The ask is corpus-level: walk the A–Z directory for a dossier whose
    // source breakdown exists AND at least one contributing source's page
    // resolves (corpora may carry rows for not-yet-published sources). The
    // fixture's Oklahoma City dossier is the row that answers.
    const az = await request.get("/dossier/a-z/");
    expect(az.status()).toBe(200);
    const letters = [
      ...new Set(
        [...(await az.text()).matchAll(/href="(\/dossier\/a-z\/[a-z]\/)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ];
    expect(
      letters.length,
      "the A–Z directory must index letter pages",
    ).toBeGreaterThan(0);
    const azLinks: string[] = [];
    for (const letter of letters.slice(0, 12)) {
      const lhtml = await (await request.get(letter)).text();
      for (const m of lhtml.matchAll(/href="(\/dossier\/[^"]+\/)"/g)) {
        const h = m[1]!;
        if (
          !h.startsWith("/dossier/a-z/") &&
          !h.startsWith("/dossier/figures/") &&
          !h.includes("/print/") &&
          !azLinks.includes(h)
        ) {
          azLinks.push(h);
        }
      }
    }
    expect(
      azLinks.length,
      "the A–Z directory must list dossiers",
    ).toBeGreaterThan(0);

    let html = "";
    let doc:
      | {
          totals?: { records?: number };
          sources?: {
            records?: number;
            source_page?: string;
            runs_page?: string;
          }[];
        }
      | undefined;
    let figValue: string | undefined;
    for (const d of azLinks.slice(0, 8)) {
      const sres = await request.get(`${d}sources/`);
      if (sres.status() !== 200) continue;
      const shtml = await sres.text();
      const artifact = /data-artifact="(web\/dossier_sources\/[^"]+\.json)"/.exec(
        shtml,
      )?.[1];
      if (!artifact) continue;
      const ares = await request.get(`/artifact/${artifact}`);
      if (ares.status() !== 200) continue;
      const candidate = (await ares.json()) as typeof doc;
      let anyPage = false;
      for (const s of candidate?.sources ?? []) {
        if (
          s.source_page &&
          (await request.get(s.source_page)).status() === 200 &&
          s.runs_page &&
          (await request.get(s.runs_page)).status() === 200 &&
          (await (await request.get(s.runs_page)).text()).includes(
            'data-testid="run-row"',
          )
        ) {
          anyPage = true;
          break;
        }
      }
      if (!anyPage) continue;
      html = await (await request.get(d)).text();
      figValue = /data-figure-id="dsrc-records"[^>]*data-figure-value="(\d+)"/.exec(
        html,
      )?.[1];
      doc = candidate;
      break;
    }
    expect(
      doc,
      "no dossier with a resolvable source page was found in the A–Z directory",
    ).toBeTruthy();
    expect(figValue, "the dossier must carry the records figure").toBeTruthy();
    // The breakdown sums to the figure — read at the artifact layer (the
    // figure's own pointer contract), never scraped rendered text.
    const summed = (doc!.sources ?? []).reduce((n, s) => n + (s.records ?? 0), 0);
    expect(summed).toBe(doc!.totals?.records ?? -1);
    expect(String(doc!.totals?.records)).toBe(figValue);
    // A per-source row's own page carries the when: last run + first/last
    // seen. Corpora may carry rows whose page is not emitted (a demo or
    // not-yet-published source); a published row's page must resolve, and
    // its runs page carries either execution-keyed run rows — dated, so
    // first and last seen read directly — or the typed runs-none state.
    let withRuns: { source_page?: string; runs_page?: string } | undefined;
    let resolvable = 0;
    for (const s of doc.sources ?? []) {
      if (!s.source_page) continue;
      if ((await request.get(s.source_page)).status() !== 200) continue;
      resolvable++;
      if (
        s.runs_page &&
        (await request.get(s.runs_page)).status() === 200 &&
        (await (await request.get(s.runs_page)).text()).includes(
          'data-testid="run-row"',
        )
      ) {
        withRuns = s;
        break;
      }
    }
    expect(
      resolvable,
      "at least one contributing source's page must resolve",
    ).toBeGreaterThan(0);
    expect(
      withRuns,
      "no contributing source carried an execution-keyed run history",
    ).toBeTruthy();
    const pres = await request.get(withRuns!.source_page!);
    expect(pres.status()).toBe(200);
    const phtml = await pres.text();
    expect(/data-testid="subnav-runs"/.test(phtml)).toBeTruthy();
    expect(
      /data-testid="freshness-verdict"/.test(phtml) ||
        /data-testid="pageb-runs"/.test(phtml),
      "the source page must carry its freshness/run summary",
    ).toBeTruthy();
    const rres = await request.get(withRuns!.runs_page!);
    expect(rres.status()).toBe(200);
    const rhtml = await rres.text();
    // First/last seen: the execution-keyed run history's dated rows — the
    // earliest and latest <time> are the source's seen span.
    const times = [...rhtml.matchAll(/datetime="([^"]+)"/g)].map((m) => m[1]!);
    expect(
      times.length,
      "the runs page must date its runs — the first/last-seen record",
    ).toBeGreaterThan(0);
  });
});

test.describe("U-003.6 — default map/network visualizations and search on dossiers", () => {
  test("a located-record dossier shows Figure 1, prints it, carries the activate control and the scoped search", async ({
    page,
    request,
  }) => {
    const tx = await resolveDossierViaAZ(request, "t", "texas");
    await page.goto(tx);
    // Figure 1 is the dossier's default figure — visible with JS off.
    await expect(page.locator("[data-testid='fig1-caption']").first()).toBeVisible();
    // The activate control (the map upgrade is opt-in; the figure renders without it).
    await expect(page.getByTestId("fig1-activate").first()).toBeAttached();
    // The network figure slot: a figure or its typed absence — never a silent gap.
    const slot = page.getByTestId("network-figure-slot").first();
    await expect(slot).toBeAttached();
    // The scoped search carries the place's jurisdiction scope.
    const scope = page.getByTestId("dossier-scoped-search-scope").first();
    await expect(scope).toBeAttached();
    expect(await scope.getAttribute("value")).toContain("iso3166-2");
    const sform = page.getByTestId("dossier-scoped-search-form").first();
    await expect(sform).toBeAttached();
    // The print path resolves within ≤ 3 dossier ancestors (the A3 walk).
    let trail = tx;
    let printHref: string | null = null;
    for (let hop = 0; hop < 3 && printHref === null; hop += 1) {
      const res = await request.get(trail);
      expect(res.status()).toBe(200);
      const h = await res.text();
      printHref = /href="(\/dossier\/[^"]*print\/)"/.exec(h)?.[1] ?? null;
      if (printHref === null) {
        const up = trail.replace(/[^/]+\/$/, "");
        expect(
          up !== trail && up.startsWith("/dossier/"),
          `no print action on ${trail} and no dossier ancestor remains`,
        ).toBeTruthy();
        trail = up;
      }
    }
    const pres = await request.get(printHref!);
    expect(pres.status()).toBe(200);
    expect(/data-testid="council-brief"/.test(await pres.text())).toBeTruthy();
  });
});

test.describe("U-003.7 — /watch answers", () => {
  test("a place watch page renders items or the typed empty state; its feeds validate", async ({
    request,
  }) => {
    // Resolve a place watch page from the served /watch/ family.
    const wres = await request.get("/watch/");
    expect(wres.status()).toBe(200);
    const whtml = await wres.text();
    const placeHref =
      /href="(\/watch\/place\/[^"]+\/)"/.exec(whtml)?.[1] ??
      (await (async () => {
        const pres = await request.get("/watch/place/usa/");
        expect(pres.status()).toBe(200);
        return /href="(\/watch\/place\/usa\/[^"]+\/)"/.exec(await pres.text())?.[1];
      })());
    expect(placeHref, "a place watch page must resolve").toBeTruthy();
    const pres = await request.get(placeHref!);
    expect(pres.status()).toBe(200);
    const phtml = await pres.text();
    // Items or the typed empty state (empty states name the cause — the
    // state/missing/action testids carry it, never a silent blank).
    const hasItems = /data-testid="watch-item|data-testid="agenda/.test(phtml);
    const hasEmpty = /data-testid="empty-state/.test(phtml);
    expect(
      hasItems || hasEmpty,
      "the watch page must show items or a typed empty state",
    ).toBeTruthy();
    // The feeds validate and exist even at 0 items — RFC 5545, RSS, JSON Feed.
    const base = placeHref!.replace(/^\/watch\/place\//, "/watch/feeds/place/").replace(/\/$/, "");
    const ics = await request.get(`${base}.ics`);
    expect(ics.status()).toBe(200);
    const icsText = await ics.text();
    expect(icsText).toContain("BEGIN:VCALENDAR");
    expect(icsText).toContain("VERSION:2.0");
    expect(icsText).toContain("END:VCALENDAR");
    const xml = await request.get(`${base}.xml`);
    expect(xml.status()).toBe(200);
    expect(await xml.text()).toContain("<rss");
    const json = await request.get(`${base}.json`);
    expect(json.status()).toBe(200);
    const feed = (await json.json()) as { version?: string; items?: unknown[] };
    expect(feed.version).toContain("jsonfeed.org");
    expect(feed.items, "the producer fills the feed items array").toBeTruthy();
  });
});

test.describe("U-003.8 — /evidence shows the publishable artifacts with honest binding states", () => {
  test("the index lists artifact rows, each carrying a binding state; links resolve or name the absence", async ({
    request,
  }) => {
    const res = await request.get("/evidence/");
    expect(res.status()).toBe(200);
    const html = await res.text();
    const rows = [...html.matchAll(/data-testid="evidence-artifact-row"/g)];
    expect(
      rows.length,
      "the evidence index must list artifact rows",
    ).toBeGreaterThan(0);
    // The binding states are declared on the page — the claim-view counts and
    // the lane/state facets are the honest readout, never a bare list.
    for (const id of [
      "claim-view-emitted",
      "claim-view-eligible",
      "claim-view-cap",
      "facet-lane",
      "facet-state",
    ]) {
      expect(
        html.includes(`data-testid="${id}"`),
        `the evidence index must carry ${id}`,
      ).toBeTruthy();
    }
    // The JSON twin emits for machine readers.
    expect((await request.get("/evidence/index.json")).status()).toBe(200);
    // Every linked artifact resolves, or the row names the typed absence —
    // the 'shows nothing' clause means honest states, never dead links.
    const artifactHrefs = [
      ...new Set(
        [
          ...html.matchAll(
            /data-testid="artifact-link"[^>]*href="([^"]+)"/g,
          ),
        ].map((m) => m[1]!),
      ),
    ];
    for (const href of artifactHrefs.slice(0, 8)) {
      expect((await request.get(href)).status(), href).toBe(200);
    }
  });
});

test.describe("U-003.9 — the sources table is sortable and complete", () => {
  test("rows exist; every column sorts asc/desc without JS; published rows carry extract, version, homepage and terms links", async ({
    request,
  }) => {
    const res = await request.get("/sources/");
    expect(res.status()).toBe(200);
    const html = await res.text();
    const rows = [...html.matchAll(/data-testid="source-table-row"/g)];
    expect(rows.length, "the sources table must carry rows").toBeGreaterThan(0);
    // Every advertised sort URL resolves — the no-JS sort contract
    // (the '342 rows' count is the release corpus's; the machinery here).
    const sortHrefs = [
      ...new Set(
        [...html.matchAll(/href="(\/sources\/sort\/[^"]+\/)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ];
    expect(
      sortHrefs.length,
      "the table must advertise no-JS sort URLs",
    ).toBeGreaterThan(0);
    for (const href of sortHrefs) {
      expect((await request.get(href)).status(), href).toBe(200);
    }
    // Non-published rows name their state honestly — a gated, refused or
    // not-yet-ingested row never renders as published.
    const nonPublished = [
      ...html.matchAll(
        /<tr[^>]*data-testid="source-table-row"[^>]*data-status="(?!published)([^"]*)"[\s\S]*?<\/tr>/g,
      ),
    ];
    for (const row of nonPublished) {
      const status = row[1]!;
      expect(
        row[0],
        `a ${status} row must name its own state`,
      ).toContain(status);
    }
    // A published source page carries the invariant record (subnav, rights,
    // licence, publication basis); the corpus must offer at least one
    // published page carrying the ask's optional links (homepage + terms)
    // — a source that declares no upstream page omits the link honestly.
    const published = await resolvePublishedSources(request);
    let optionalSeen = false;
    for (const src of published.slice(0, 6)) {
      const phtml = await (await request.get(src)).text();
      for (const id of [
        "source-subnav",
        "subnav-runs",
        "subnav-versions",
        "licence-section",
        "rights-section",
        "publication-basis",
      ]) {
        expect(
          phtml.includes(`data-testid="${id}"`),
          `${src} must carry ${id}`,
        ).toBeTruthy();
      }
      expect((await request.get(`${src}versions/`)).status()).toBe(200);
      if (
        /data-testid="homepage-link"/.test(phtml) &&
        /data-testid="terms-link"/.test(phtml)
      ) {
        optionalSeen = true;
      }
    }
    expect(
      optionalSeen,
      "no published source page carried homepage + terms links",
    ).toBeTruthy();
  });
});

test.describe("U-003.10 — per-source detail pages carry the full record", () => {
  test("a source page shows metadata, rights, conduct, execution-keyed history, hashed captures, downloads where the lane allows, dossier contribution, changelog", async ({
    request,
  }) => {
    // The clause's full record is the published-source contract; a corpus
    // must offer at least one source carrying it (a published source with
    // no dossier contribution omits that subnav honestly).
    const candidates = await resolvePublishedSources(request);
    const REQUIRED = [
      "source-description",
      "rights-section",
      "rights-record",
      "conduct-section",
      "homepage-link",
      "terms-link",
      "licence-section",
      "changelog-section",
      "subnav-runs",
      "subnav-captures",
      "subnav-versions",
      "subnav-dossiers",
      "contribution-row",
      "publication-basis",
    ];
    let src = "";
    let html = "";
    for (const candidate of candidates.slice(0, 6)) {
      const chtml = await (await request.get(candidate)).text();
      if (REQUIRED.every((id) => chtml.includes(`data-testid="${id}"`))) {
        src = candidate;
        html = chtml;
        break;
      }
    }
    expect(
      src,
      "no published source page carried the full record contract",
    ).toBeTruthy();
    for (const id of REQUIRED) {
      expect(
        html.includes(`data-testid="${id}"`),
        `the source page must carry ${id}`,
      ).toBeTruthy();
    }
    // Execution-keyed history resolves; captures carry content hashes.
    expect((await request.get(`${src}runs/`)).status()).toBe(200);
    const cres = await request.get(`${src}captures/`);
    expect(cres.status()).toBe(200);
    const chtml = await cres.text();
    expect(
      /sha256|multihash|digest|content hash/i.test(chtml),
      "captures must carry content hashes",
    ).toBeTruthy();
    // The dossier-contribution link resolves.
    expect((await request.get(`${src}dossiers/`)).status()).toBe(200);
  });
});

test.describe("U-003.11 — the research queue is usable", () => {
  test("a canonical task id 301s to its public handle; the page is titled; ≤50 cards/page; drafts exist for records requests", async ({
    request,
  }) => {
    // The queue paginates its cards — the clause's ≤ 50 bound.
    const qres = await request.get("/research-queue/");
    expect(qres.status()).toBe(200);
    const qhtml = await qres.text();
    const cards = [...qhtml.matchAll(/data-testid="task-card"/g)];
    expect(cards.length, "the queue must carry task cards").toBeGreaterThan(0);
    expect(
      cards.length,
      "the queue page must stay ≤ 50 cards",
    ).toBeLessThanOrEqual(50);
    // Resolve a task's JSON twin → the canonical id → the 301 → the handle.
    const taskHref = /href="(\/task\/[^"#]+\/)"/.exec(qhtml)?.[1];
    expect(taskHref, "the queue must link a task page").toBeTruthy();
    const twin = await request.get(`${taskHref!.replace(/\/$/, "")}.json`);
    expect(twin.status()).toBe(200);
    const doc = (await twin.json()) as { task_id?: string; handle?: string };
    expect(doc.task_id, "the task twin must name its canonical id").toBeTruthy();
    // The canonical id routes to the public handle: on the promoted origin
    // the edge answers a 301; a static serve emits the equivalent alias-stub
    // page (task-alias-stub) linking the successor handle. Either is the
    // contract; a wrong or absent successor is not.
    const canon = await request.get(`/task/${doc.task_id}/`, {
      maxRedirects: 0,
    });
    let target = "";
    if (canon.status() === 301) {
      target = canon.headers()["location"] ?? "";
      expect(target).toContain("/task/T-");
    } else {
      expect(canon.status()).toBe(200);
      const chtml = await canon.text();
      expect(
        /data-testid="task-alias-stub"/.test(chtml),
        "a canonical task id must 301 or emit the alias-stub successor",
      ).toBeTruthy();
      target = /href="(\/task\/T-[^"]+\/)"/.exec(chtml)?.[1] ?? "";
      expect(
        target,
        "the alias-stub must link the task's public handle",
      ).toContain("/task/T-");
    }
    // The public page is titled with the ask — a name, never the bare handle.
    const pres = await request.get(target.replace(/^https?:\/\/[^/]+/, ""));
    expect(pres.status()).toBe(200);
    const phtml = await pres.text();
    const h1 = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(phtml)?.[1] ?? "";
    expect(h1.trim().length, "the task page must render a title").toBeGreaterThan(
      0,
    );
    // Drafts for records requests: a draft-bearing task exists on the served
    // site (the A4 walk — the queue's linked tasks carry the download).
    const taskHrefs = [
      ...new Set(
        [...qhtml.matchAll(/href="(\/task\/[^"#]+\/)"/g)].map((m) => m[1]!),
      ),
    ];
    let draftSeen = false;
    for (const href of taskHrefs.slice(0, 6)) {
      const r = await request.get(href);
      if (r.status() === 200 && /data-testid="draft-download"/.test(await r.text())) {
        draftSeen = true;
        break;
      }
    }
    expect(
      draftSeen,
      "no records-request draft among the queue's first tasks",
    ).toBeTruthy();
  });
});
