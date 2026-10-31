// SPDX-License-Identifier: Apache-2.0
// P36.35 (JUR-05 / SIG-UI-058 owner; SIG-JUR-009/012 owner) — the ONE
// redirect generator's fixtures. Every leg asserts an invariant, never a
// living record (OM-15): the fixture histories are committed documents.
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  redirectRules,
  renderRedirectsConf,
  resolveRequest,
  type RedirectInputs,
} from "../../src/lib/redirects";
import {
  JURISDICTION_SLUG_HISTORY_FIXTURE,
} from "../../src/lib/data";
import { ENTITY_SLUG_HISTORY_FIXTURE } from "../../src/lib/entity-history";

const EMITTED = new Set([
  "/",
  "/dossier/",
  "/dossier/unplaced/",
  "/dossier/usa/",
  "/dossier/usa/ok/",
  "/dossier/id/",
  "/dossier/bd/",
  "/dossier/unresolved/",
  "/sources/",
  "/network/",
  "/data-freshness/",
  "/explore/",
]);

function inputs(over: Partial<RedirectInputs> = {}): RedirectInputs {
  return {
    slugHistory: JURISDICTION_SLUG_HISTORY_FIXTURE.rows,
    jurisdictionTargets: new Map([
      ["unplaced", "/dossier/unplaced/"],
      ["iso3166-2:US-OK", "/dossier/usa/ok/"],
    ]),
    jurisdictionLevels: new Map([["iso3166-2:US-OK", "admin-1"]]),
    entityHistory: ENTITY_SLUG_HISTORY_FIXTURE.rows,
    handleRows: [],
    emittedRoutes: EMITTED,
    ...over,
  };
}

const byFrom = (rules: ReturnType<typeof redirectRules>) =>
  new Map(rules.map((r) => [r.from, r]));

describe("jurisdiction rules (SIG-JUR-009)", () => {
  it("moved row with a resolved successor → 301 (+ aliases gated on print)", () => {
    const rules = byFrom(
      redirectRules(
        inputs({
          slugHistory: [
            {
              slug: "ok",
              kind: "moved",
              successor: "iso3166-2:US-OK",
              first_release: null,
              last_release: null,
            },
          ],
        }),
      ),
    );
    expect(rules.get("/dossier/ok/")).toMatchObject({
      status: 301,
      target: "/dossier/usa/ok/",
      family: "jurisdiction",
    });
    // print alias: the successor is an admin-1 dossier → minted print.
    expect(rules.get("/dossier/ok/print/")?.target).toBe("/dossier/usa/ok/print/");
    expect(rules.get("/dossier/ok.json")?.target).toBe("/dossier/usa/ok.json");
  });

  it("the fixture split row serves its split page in place (300 semantics)", () => {
    const rules = byFrom(redirectRules(inputs()));
    expect(rules.get("/dossier/id/")).toMatchObject({ status: 200, serve: "/dossier/id/index.html" });
  });

  it("the fixture corrected row serves its correction page (200, never a rename)", () => {
    const rules = byFrom(redirectRules(inputs()));
    expect(rules.get("/dossier/bd/")).toMatchObject({ status: 200, serve: "/dossier/bd/index.html" });
  });

  it("moved row whose successor is not emitted → serves the honest stub", () => {
    const rules = byFrom(
      redirectRules(
        inputs({
          slugHistory: [
            { slug: "xx", kind: "moved", successor: "iso3166-1:XX", first_release: null, last_release: null },
          ],
        }),
      ),
    );
    expect(rules.get("/dossier/xx/")?.status).toBe(200);
  });

  it("a 301 carries args — the as-of permalink keeps its selector (SIG-JUR-012)", () => {
    const rules = redirectRules(
      inputs({
        slugHistory: [
          { slug: "ok", kind: "moved", successor: "iso3166-2:US-OK", first_release: null, last_release: null },
        ],
      }),
    );
    const conf = renderRedirectsConf(rules, {
      jurisdictions: 1,
      entities: 0,
      handles: 0,
      routes: EMITTED.size,
    });
    expect(conf).toContain("return 301 /dossier/usa/ok/$is_args$args;");
    const hit = resolveRequest(rules, "/dossier/ok/?as_of_world=2026-09-27&as_of_belief=2026-09-27");
    expect(hit?.status).toBe(301);
    expect(hit?.target).toBe("/dossier/usa/ok/");
  });
});

describe("entity rules (`sig.slug-history/1`)", () => {
  const rules = byFrom(redirectRules(inputs()));

  it("a fixture rename produces its 301 on the retired key URL", () => {
    expect(rules.get("/entity/agency/okc-office-of-emergency-management--b9sdfah/")).toMatchObject({
      status: 301,
      target: "/entity/agency/oklahoma-city-emergency-management--b9sdfah/",
    });
  });

  it("merged → 301 to the survivor; split → 300; withdrawn → 410", () => {
    expect(rules.get("/entity/agency/oklahoma-city-fusion-center--yarw4yk/")?.status).toBe(301);
    expect(rules.get("/entity/agency/okcpd-field-operations--257dn0h/")?.status).toBe(300);
    expect([...rules.values()].some((r) => r.status === 410 && r.family === "entity")).toBe(true);
  });

  it("/id/<type>/<uuid> — 302 while current, terminal statuses otherwise", () => {
    expect(rules.get("/id/agency/agency:okcpd/")).toMatchObject({ status: 302 });
    expect(rules.get("/id/agency/agency:okcpd")).toMatchObject({ status: 302 });
    expect(rules.get("/id/agency/agency:okc-fusion-center/")?.status).toBe(301);
    expect(rules.get("/id/agency/agency:okcpd-field-operations/")?.status).toBe(300);
  });
});

describe("fixed legacy list + handles", () => {
  it("/task/new/** is retired → 410 prefix rule, always", () => {
    const rules = byFrom(redirectRules(inputs()));
    expect(rules.get("/task/new/")).toMatchObject({ status: 410, family: "legacy" });
    expect(resolveRequest(redirectRules(inputs()), "/task/new/cam-1/")?.status).toBe(410);
  });

  it("a re-emitted /task/new/ route fails loud (the namespace is retired)", () => {
    expect(() =>
      redirectRules(inputs({ emittedRoutes: new Set(["/task/new/x/"]) })),
    ).toThrow(/task\/new/);
  });

  it("live pages outrank the fixed list — /data-freshness/ and /network/ carry no rule while emitted", () => {
    const rules = byFrom(redirectRules(inputs()));
    expect(rules.has("/data-freshness/")).toBe(false);
    expect(rules.has("/network/")).toBe(false);
  });

  it("retired source + existing successor → the fixed rule fires", () => {
    const rules = byFrom(
      redirectRules(inputs({ emittedRoutes: new Set(["/sources/"]) })),
    );
    expect(rules.get("/data-freshness/")).toMatchObject({ status: 301, target: "/sources/" });
    expect(rules.has("/network/")).toBe(false); // /explore/ not emitted → no rule
  });

  it("handle-history rows feed the same table (301)", () => {
    const rules = byFrom(
      redirectRules(
        inputs({
          handleRows: [{ old: "/task/old-handle/", target: "/task/new-handle/", family: "handle" }],
        }),
      ),
    );
    expect(rules.get("/task/old-handle/")).toMatchObject({ status: 301, target: "/task/new-handle/" });
  });
});

describe("the one-generator contract (SIG-UI-058)", () => {
  it("every fixture history URL resolves — rule or stub, never nothing", () => {
    const rules = redirectRules(inputs());
    for (const row of JURISDICTION_SLUG_HISTORY_FIXTURE.rows) {
      const hit = resolveRequest(rules, `/dossier/${row.slug}/`);
      const stub = EMITTED.has(`/dossier/${row.slug}/`);
      expect(hit !== null || stub).toBe(true);
    }
  });

  it("two rules for one URL refuse (a duplicate location = is a broken include)", () => {
    expect(() =>
      redirectRules(
        inputs({
          slugHistory: [
            { slug: "ok", kind: "moved", successor: "iso3166-2:US-OK", first_release: null, last_release: null },
          ],
          handleRows: [{ old: "/dossier/ok/", target: "/x/", family: "handle" }],
        }),
      ),
    ).toThrow(/two rules/);
  });

  it("the rendered conf is deterministic and carries the renamed-source boundary", () => {
    const rules = redirectRules(inputs());
    const a = renderRedirectsConf(rules, { jurisdictions: 3, entities: 12, handles: 0, routes: EMITTED.size });
    const b = renderRedirectsConf(rules, { jurisdictions: 3, entities: 12, handles: 0, routes: EMITTED.size });
    expect(a).toBe(b);
    expect(a).toContain("sig.redirects-conf/1");
    expect(a).toContain("renamed_*.conf");
  });

  it("lint: no second redirect-writing path inside web/src", () => {
    const SRC = join(__dirname, "../../src");
    const ALLOWED = new Set([
      "pages/dossier/[...path].astro",
      "pages/id/[type]/[uuid].astro",
      "lib/redirects.ts",
    ]);
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const p = join(dir, e.name);
        if (e.isDirectory()) walk(p);
        else if (/\.(astro|ts|mjs)$/.test(e.name)) {
          const rel = p.slice(SRC.length + 1);
          const text = readFileSync(p, "utf-8");
          if (
            /http-equiv="refresh"/.test(text) ||
            /Astro\.redirect|context\.redirect|Response\.redirect|return\s*30[0-9]\s*\S/.test(text)
          ) {
            if (!ALLOWED.has(rel)) offenders.push(rel);
          }
        }
      }
    };
    walk(SRC);
    expect(offenders).toEqual([]);
  });
});
