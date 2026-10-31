// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import * as esbuild from "esbuild";
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, relative, resolve, sep } from "node:path";
import sharp from "sharp";
import { resolveTileCopyList } from "./scripts/export-tiles.mjs";
import { buildManifest, classifyDist, classifyRoute, writeManifest } from "./src/lib/page-types.ts";
import { tightenT0Document } from "./src/lib/csp.ts";
import { BASEMAP_TILE_ORIGIN } from "./src/lib/basemap.ts";
import { redirectRules, renderRedirectsConf } from "./src/lib/redirects.ts";
import {
  getSlugHistory,
  getEntitySlugHistory,
  getHandleHistories,
  getJurisdictionKeyMap,
  getUnplacedReport,
} from "./src/lib/data.ts";
import {
  renderCardSvg,
  renderLogoSvg,
  SOCIAL_CARDS,
  SOCIAL_CARD_SIZE,
} from "./src/lib/brand.ts";
import { getSiteMetadata } from "./src/lib/data.ts";

// P21.5 (deliverable 3, LD-F07/H08) + P30.3 (ADR-106) + P31.15 (ADR-R9-TILES) +
// P35.52 (sig.map-tiles/2, ADR-156): in `export` mode the static build CONSUMES
// the rendered vector tiles the export produced — ONE archive PER LICENCE
// COMPARTMENT (`<compartment>-sites.<sha8>.pmtiles`, e.g. the ODbL osm_physical
// layer apart from the CC-BY graph) — never a merged, mixed-licence archive.
// Each is served as its own source with its own attribution
// (/map/style.json), over a plain background with NO basemap (Q8). The copy list is
// the SAME list `/map/style.json` is built from (data.ts getCompartmentTileSources):
// the manifest's `web/tiles/<compartment>-sites.<sha8>.pmtiles` artifacts plus the
// `web/tiles/index.json` contract index — so the style can never name an archive
// that was not copied, and no unlisted file is served.
// Fixtures mode (the CI default) is untouched.
function sigExportTiles() {
  return {
    name: "sig-export-tiles",
    hooks: {
      "astro:build:done": ({ dir }) => {
        // P35.51: the same manifest-listed copy runs under the `national`
        // overlay — the synthetic national fixture's per-compartment archives
        // (SIG_NATIONAL_DIR / the gitignored default `web/national/`).
        const mode = process.env.SIG_DATA_SOURCE;
        if (mode !== "export" && mode !== "national") return;
        const repoRoot = fileURLToPath(new URL("../", import.meta.url));
        const override =
          mode === "national" ? process.env.SIG_NATIONAL_DIR : process.env.SIG_EXPORT_DIR;
        // `npm --prefix web` runs scripts with cwd=web/, so a repo-relative
        // dir override must be anchored at the repo root, not the cwd.
        const exportDir =
          override !== undefined && override !== ""
            ? resolve(repoRoot, override)
            : join(repoRoot, mode === "national" ? "web/national" : "exports/out/okc");
        const destDir = join(fileURLToPath(dir), "tiles");
        // P34.34a: the copy list comes from resolveTileCopyList — a manifest
        // that lists zero archives is an HONEST empty-tile export (the map
        // page states it), not a build error; only a missing manifest or a
        // listed-but-absent archive fails loud.
        const { tilesDir, files } = resolveTileCopyList(exportDir, mode);
        if (files.length === 0) return;
        mkdirSync(destDir, { recursive: true });
        for (const f of files) cpSync(join(tilesDir, f), join(destDir, f));
      },
    },
  };
}

// P34.10 (SIG-OPS-003, G1 §3.2 item 1): the DEFAULT build emits only the
// allow-listed public surface (`ops/public_routes.toml`). Every route that must
// never ship to a public origin lives outside `src/pages/` under
// `src/internal/` — the authenticated curation shell `/curate/**` (ADR-068, a
// loopback-only app surface, never public), the withdrawn surfaces
// (`/contribution-back/` per C-12, `/visual-language/` per A-0.3 = b), and the
// not-yet-approved namespaces (`/releases/`, `/research-dossier/` — the former
// is also owned by the release pipeline, exactly one generator per G2 0b).
// They are injected ONLY when `SIG_BUILD_INTERNAL=1` — the web e2e suite sets it
// (its tests exercise the internal surface); a publishable build never carries
// them, and `sig-ops publish-web` independently refuses a tree that does.
const INTERNAL_ROUTES = [
  ["/curate", "curate/index.astro"],
  ["/curate/submit", "curate/submit.astro"],
  ["/curate/tasks", "curate/tasks.astro"],
  ["/curate/contradictions", "curate/contradictions.astro"],
  ["/curate/revert", "curate/revert.astro"],
  ["/curate/[id]", "curate/[id].astro"],
  ["/releases", "releases/index.astro"],
  ["/research-dossier", "research-dossier/index.astro"],
  ["/research-dossier/[slug]", "research-dossier/[slug].astro"],
  ["/research-dossier/[slug].json", "research-dossier/[slug].json.ts"],
  ["/contribution-back", "contribution-back.astro"],
  ["/visual-language", "visual-language.astro"],
  // P36.20 (UXK0-4): the internal enhancement-kit harness — exercises every
  // element over fixture markup plus the fixture shard endpoint
  // `<sig-typeahead>` reads (P36.40's real shards land in export mode later).
  ["/enhancement-kit", "enhancement-kit/index.astro"],
  ["/enhancement-kit/shards/[key].json", "enhancement-kit/shards/[key].json.ts"],
  // P36.22 (UXK14-3a): the internal component-kit-A harness — mounts every
  // kit-A component over fixture data so the e2e suite exercises the visual
  // layer end-to-end; never published.
  ["/component-kit", "component-kit/index.astro"],
];

function sigInternalRoutes() {
  const enabled = !["", "0", "false"].includes(
    (process.env.SIG_BUILD_INTERNAL ?? "").trim().toLowerCase(),
  );
  return {
    name: "sig-internal-routes",
    hooks: {
      "astro:config:setup": ({ injectRoute }) => {
        if (!enabled) return;
        for (const [pattern, file] of INTERNAL_ROUTES) {
          injectRoute({
            pattern,
            entrypoint: fileURLToPath(new URL(`./src/internal/${file}`, import.meta.url)),
          });
        }
      },
    },
  };
}

// P34.13 (QW-11): the chrome quick-fixes that belong to the BUILD, not a page —
// (a) the canonical-only sitemap (RI-51): walk the emitted pages and list a URL
// only when it is its OWN canonical — print pages canonicalise to their dossier
// and so never appear, and every URL resolves on the canonical origin — plus
// noindex pages never appear at all; (b) the flat /403.html + /410.html copies
// matching the /404.html error-page convention (the nginx `error_page` wiring
// that serves them is P34.40's dark roll — this row only builds the pages).
// P36.22: /500.html needs no copy — Astro emits 500.astro flat natively,
// exactly like 404.astro (the loop keeps it listed for the audit trail).
// P36.21 (K13 §2.5, ADR-155): the sitemap is generated FROM THE ROUTE REGISTRY —
// a URL is listed only when its page type is T0 or T1, so the stateful T2
// surfaces (`/map/`, `/network/`, `/search/` — `noindex,follow` documents whose
// canonical lives on the base surface) can never leak into the indexable set
// even if a page's own meta drifts.
function sigChrome() {
  return {
    name: "sig-chrome",
    hooks: {
      "astro:build:done": ({ dir }) => {
        const distDir = fileURLToPath(dir);
        for (const code of ["403", "410", "500"]) {
          const page = join(distDir, code, "index.html");
          if (existsSync(page)) cpSync(page, join(distDir, `${code}.html`));
        }
        const INTERNAL_SEGMENTS = new Set(
          INTERNAL_ROUTES.map(([pattern]) => pattern.split("/")[1]).concat(["task"]),
        );
        const origin = "https://surveillancegraph.org";
        const urls = [];
        const walk = (d) => {
          for (const entry of readdirSync(d, { withFileTypes: true })) {
            const full = join(d, entry.name);
            if (entry.isDirectory()) {
              walk(full);
            } else if (entry.name === "index.html") {
              const html = readFileSync(full, "utf-8");
              if (html.includes('name="robots" content="noindex"')) continue;
              const m = html.match(/<link rel="canonical" href="([^"]+)"/);
              if (!m) continue;
              const rel = `${relative(distDir, full).split(sep).join("/").replace(/index\.html$/, "")}`;
              const own = `${origin}/${rel}`;
              if (m[1] !== own) continue;
              // K13 §2.5 (P36.21): the sitemap is the canonical T0/T1 set only
              // — the page-type registry decides, so a stateful T2 surface or
              // a T3/internal route can never be listed even when its document
              // meta is canonical-shaped.
              const classified = classifyRoute(`/${rel}`);
              if (!classified.ok) continue;
              if (classified.entry.type !== "T0" && classified.entry.type !== "T1") continue;
              urls.push(m[1]);
            }
          }
        };
        walk(distDir);
        const publicUrls = urls
          .filter((u) => !INTERNAL_SEGMENTS.has(new URL(u).pathname.split("/")[1]))
          .sort();
        // P35.39 (SIG-TRANSP-017 / J3 §6.6): the linked machine metadata is
        // sitemap-listed. The DCAT-3 catalog the export emits (`catalog.jsonld`
        // at the bundle root) is copied to a web-owned route — `/releases/` is a
        // protected prefix the release pipeline owns, so the build can never
        // serve it there. Export mode only: a fixtures build carries no real
        // catalog, and the sitemap never names a URL the built site will not
        // resolve (QW-11: every loc must answer on the emitted tree).
        if (process.env.SIG_DATA_SOURCE === "export") {
          const repoRoot = fileURLToPath(new URL("../", import.meta.url));
          const override = process.env.SIG_EXPORT_DIR;
          const exportDir =
            override !== undefined && override !== ""
              ? resolve(repoRoot, override)
              : join(repoRoot, "exports/out/okc");
          const catalogSrc = join(exportDir, "catalog.jsonld");
          if (existsSync(catalogSrc)) {
            mkdirSync(join(distDir, "data"), { recursive: true });
            cpSync(catalogSrc, join(distDir, "data", "catalog.jsonld"));
            publicUrls.push(`${origin}/data/catalog.jsonld`);
          }
        }
        const sitemap =
          `<?xml version="1.0" encoding="UTF-8"?>\n` +
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
          publicUrls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n") +
          `\n</urlset>\n`;
        writeFileSync(join(distDir, "sitemap.xml"), sitemap);
      },
    },
  };
}

// P36.20 (UXK0-4, ADR-224): the T1 enhancement kit emission. The
// framework-free custom elements under `src/elements/` are bundled by
// esbuild (a build-time dep of Vite — no new runtime dependency) into
// `dist/_kit/sig-*.js`, ONE emitted entry per element file, under STABLE
// unprefixed names: the T1 module allow-list
// (`tests/e2e/t1-module-entries.json`, P35.50/ADR-155) can then name each
// admitted entry verbatim instead of a moving content hash, and the strict
// CSP's `script-src 'self'` (P36.19/ADR-223) admits them without a hash
// allowance. A page pulls in an element module with an explicit
// `<script type="module" src="/_kit/…">` — never render-blocking (module
// scripts are deferred), never silently loaded (the allow-list records
// every admitted entry), and absent on every T0 page.
function sigEnhancementKit() {
  return {
    name: "sig-enhancement-kit",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        const distDir = fileURLToPath(dir);
        const elementsDir = fileURLToPath(new URL("./src/elements", import.meta.url));
        const files = readdirSync(elementsDir)
          .filter((f) => /^sig-[\w-]+\.ts$/.test(f))
          .sort();
        const outDir = join(distDir, "_kit");
        mkdirSync(outDir, { recursive: true });
        for (const f of files) {
          await esbuild.build({
            entryPoints: [join(elementsDir, f)],
            outfile: join(outDir, f.replace(/\.ts$/, ".js")),
            bundle: true,
            minify: true,
            format: "esm",
            platform: "browser",
            target: "es2022",
            banner: { js: "// SPDX-License-Identifier: Apache-2.0" },
            logLevel: "warning",
          });
        }
        console.log(
          `sig-enhancement-kit: ${files.length} element module(s) emitted to /_kit/`,
        );
      },
    },
  };
}

// P36.25 (UXK14-7, K14 §4.12 + DR-K14-20, SIG-UI-154): the brand assets that
// must be GENERATED at build time — the raster favicon set (32 px PNG + the
// 180 px apple-touch-icon), the standalone logo file, and one social card
// per page type (`sig.social-card/1` — T0/T1/T2; T3 is loopback-only and
// shares none). `sharp` is a build-time dependency of Astro itself (the
// image pipeline — imported statically above: no new dependency is added,
// and a static import survives past the Vite module-runner teardown where a
// dynamic import() would fail). The cards' "data as of" comes from the same
// data layer the pages read — a card can never name a different as-of than
// the site it advertises. Emitted under dist root (favicon-32.png,
// apple-touch-icon.png, brand/logo.svg, social/card-*.png); under a
// `/s/<pub>/` snapshot build the same files land inside the snapshot, so the
// head tags' withBase() URLs stay self-contained.
function sigBrandAssets() {
  return {
    name: "sig-brand-assets",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        const distDir = fileURLToPath(dir);
        const publicDir = fileURLToPath(new URL("./public", import.meta.url));
        // The 32 px icon and the 180 px touch icon are the committed
        // favicon.svg rasterised — one glyph source, never a redrawn second
        // mark that could drift.
        const favicon = readFileSync(join(publicDir, "favicon.svg"));
        await sharp(favicon, { density: 384 })
          .resize(32, 32)
          .png()
          .toFile(join(distDir, "favicon-32.png"));
        await sharp(favicon, { density: 384 })
          .resize(180, 180)
          .png()
          .toFile(join(distDir, "apple-touch-icon.png"));
        // The standalone logo — the mark in ink on a transparent ground.
        mkdirSync(join(distDir, "brand"), { recursive: true });
        writeFileSync(join(distDir, "brand", "logo.svg"), renderLogoSvg());
        // One card per page type — the release's as-of, never a recomputed
        // date (SIG-REL-009's rule: the stamp's data is the release's own).
        mkdirSync(join(distDir, "social"), { recursive: true });
        const asOfWorld = getSiteMetadata().asOf.as_of_world;
        for (const card of SOCIAL_CARDS) {
          const svg = Buffer.from(renderCardSvg(card, asOfWorld));
          await sharp(svg, { density: 96 })
            .resize(SOCIAL_CARD_SIZE.width, SOCIAL_CARD_SIZE.height)
            .png()
            .toFile(join(distDir, ...card.file.split("/")));
        }
        console.log(
          `sig-brand-assets: favicon-32.png + apple-touch-icon.png + brand/logo.svg + ${SOCIAL_CARDS.length} social card(s) emitted`,
        );
      },
    },
  };
}

// P36.35 (JUR-05 / SIG-UI-058, SIG-JUR-009/012): the ONE redirect generator.
// Every URL-history artifact the build reads — the jurisdiction slug history,
// the entity `sig.slug-history/1`, every `*_handles_history`, the fixed
// legacy list — derives ONE rule table via `src/lib/redirects.ts`; the
// emitted `dist/redirects.conf` is the generated include (the static stub
// pages are the fallback where the include cannot run). The emitted-route
// set gates every 3xx: a redirect is never written to a target this build
// does not emit, and a fixed-legacy rule fires only once its source route
// retired (SIG-ENG-042 — an unverifiable surface fails, never ships).
function sigRedirects() {
  return {
    name: "sig-redirects",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        const distDir = fileURLToPath(dir);
        // The emitted-route set — every `<route>/index.html` under dist.
        const emittedRoutes = new Set();
        const walk = (sub) => {
          for (const e of readdirSync(join(distDir, sub), { withFileTypes: true })) {
            if (e.isDirectory()) walk(`${sub}${e.name}/`);
            else if (e.name === "index.html") emittedRoutes.add(`/${sub}`);
          }
        };
        walk("");
        const keyMap = getJurisdictionKeyMap();
        const jurisdictionTargets = new Map();
        const jurisdictionLevels = new Map();
        if (getUnplacedReport() !== null) {
          jurisdictionTargets.set("unplaced", "/dossier/unplaced/");
        }
        for (const [jkey, row] of keyMap ?? []) {
          if (row.slug_path) jurisdictionTargets.set(jkey, `/dossier/${row.slug_path}/`);
          if (row.level) jurisdictionLevels.set(jkey, row.level);
        }
        const slugHistory = getSlugHistory();
        const entityHistory = getEntitySlugHistory();
        const handleRows = getHandleHistories().map((r) => ({ ...r, family: "handle" }));
        const rules = redirectRules({
          slugHistory,
          jurisdictionTargets,
          jurisdictionLevels,
          entityHistory,
          handleRows,
          emittedRoutes,
        });
        // SIG-JUR-009: every historical slug resolves — a stub page OR a rule.
        for (const row of slugHistory) {
          const from = `/dossier/${row.slug}/`;
          if (!emittedRoutes.has(from) && !rules.some((r) => r.from === from)) {
            throw new Error(
              `redirects: historical slug /dossier/${row.slug}/ resolves to ` +
                "nothing — every published URL must answer (SIG-JUR-009)",
            );
          }
        }
        writeFileSync(
          join(distDir, "redirects.conf"),
          renderRedirectsConf(rules, {
            jurisdictions: slugHistory.length,
            entities: entityHistory.length,
            handles: handleRows.length,
            routes: emittedRoutes.size,
          }),
        );
        console.log(`sig-redirects: ${rules.length} redirect rule(s) emitted to /redirects.conf`);
      },
    },
  };
}

// P35.50 (UXK0-1, K0 §4.12 item 1, ADR-155, SIG-UI-041/NEW-4): route discovery —
// the `astro:build:done` hook walks `dist/**/*.html` and classifies every built
// route against web/src/lib/page-types.ts. An unclassified route or a route two
// registry entries claim at equal strength FAILS THE BUILD — a new page is
// classified before it ships, never silently. The hook also writes
// `dist/page-types.json` (`sig.page-types-manifest/1`), the discovered-route
// manifest every e2e/axe sweep iterates instead of a hand-maintained list. It
// runs LAST so it sees the complete emitted tree (the injected internal routes,
// the flat 403/410 copies and every generated page alike).
function sigPageTypes() {
  return {
    name: "sig-page-types",
    hooks: {
      "astro:build:done": ({ dir }) => {
        const distDir = fileURLToPath(dir);
        const { routes, errors } = classifyDist(distDir);
        if (errors.length > 0) {
          throw new Error(
            `page-type registry: ${errors.length} unclassifiable route(s)\n  ${errors.join("\n  ")}`,
          );
        }
        // P36.19 (UXK0-3, K0 §4.8): Astro emits one global meta policy — the
        // T0 record/print pages get K0's stricter `default-src 'none'` row
        // (no script-src/connect-src/worker-src, no img blob:) by rewriting
        // the emitted meta here, where the classification is already known.
        // csp.spec.ts asserts the tightened shape on every discovered T0
        // route, so a page that missed the patch fails the gate.
        let t0Tightened = 0;
        for (const r of routes) {
          if (r.type !== "T0") continue;
          const file = join(distDir, r.file);
          const html = readFileSync(file, "utf-8");
          const tightened = tightenT0Document(html);
          if (tightened !== html) {
            writeFileSync(file, tightened);
            t0Tightened += 1;
          }
        }
        writeManifest(distDir, buildManifest(routes));
        console.log(
          `sig-page-types: ${routes.length} route(s) classified, ${t0Tightened} T0 meta CSP(s) tightened`,
        );
      },
    },
  };
}

// The public SIG web shell (Phase 15). Astro is a zero-JS-by-default static-first
// framework: with no explicit `client:*` directive on a component, the built page
// ships no client JavaScript at all (SIG-UI-036). Archivability is therefore
// STRUCTURAL — re-enabling client JS requires an explicit, greppable `client:`
// directive in a `.astro` file, not silent erosion. `output: "static"` makes the
// whole build a set of plain HTML files that read from web archives years later
// (SIG-UI-037).
export default defineConfig({
  output: "static",
  // P27.9 (DECISION-SPA = B, ADR-097 extending ADR-068): React arrives via
  // @astrojs/react. It renders to STATIC HTML at build time by default (no client
  // JS) — client JavaScript ships ONLY for components carrying an explicit
  // `client:*` directive, which in the public surface is exactly the three named
  // islands (map / network / search). Every other page still ships zero `<script>`
  // (SIG-UI-036/037); each island preserves its no-JS fallback (SIG-UI-050).
  integrations: [react(), sigExportTiles(), sigInternalRoutes(), sigChrome(), sigEnhancementKit(), sigBrandAssets(), sigRedirects(), sigPageTypes()],
  // The canonical public origin (P27.6 deliverable 4, ADR-093). This is the real
  // custom domain the launch surface is cited at; the belief-pinned permalinks
  // (SIG-UI-035) resolve against it. DNS/TLS cut-over completes in P27.10 — the
  // origin string is fixed here now so no permalink churns when the domain goes live.
  site: "https://surveillancegraph.org",
  // Trailing slashes normalised so belief-pinned permalinks are stable across
  // hosts and archives (SIG-UI-035).
  trailingSlash: "always",
  build: {
    // Inline nothing implicitly: keep assets as separate, cacheable, budgetable
    // files so the Lighthouse resource-size budgets (SIG-UI-041) are meaningful.
    inlineStylesheets: "never",
  },
  // P36.19 (UXK0-3, K0 §4.8, SIG-UI-096, ADR-223): the strict page CSP. On a
  // static build Astro emits a <meta http-equiv="Content-Security-Policy">
  // per page with the per-page hashes for its inline <script>/<style>
  // elements (the island bootstrap + scoped styles) — script-src/style-src
  // default to 'self' plus those hashes, never 'unsafe-inline'/'unsafe-eval'.
  // script-src-attr/style-src-attr 'none' bans inline handlers and style=""
  // attributes at the platform layer (every style= site moved to classes;
  // MapLibre/React set CSSOM properties, never the style attribute, so no
  // exception is needed — K0's recorded fallback clause stays unused).
  // The directives a <meta> cannot express (frame-ancestors, the T0
  // tightening, the standalone-SVG policy, HSTS, Permissions-Policy) ride the
  // nginx response layer (ops/web/sig-security.conf + the $sig_csp /
  // $sig_permissions_policy maps).
  security: {
    csp: {
      algorithm: "SHA-384",
      directives: [
        "default-src 'self'",
        "img-src 'self' data: blob:",
        // P36.33 (MAP-02, SIG-UI-100): K0 §4.8's `connect-src 'self' <SIG tile
        // origin>` — the basemap archive lives on the SIG tile host.
        `connect-src 'self' ${BASEMAP_TILE_ORIGIN}`,
        "worker-src 'self' blob:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
      ],
      scriptDirective: {
        resources: [{ resource: "'none'", kind: "attribute" }],
      },
      styleDirective: {
        resources: [{ resource: "'none'", kind: "attribute" }],
      },
    },
  },
  devToolbar: { enabled: false },
});
