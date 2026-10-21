// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The dossier's API (JSON) form (SIG-UI-011). The shell is static-first
// (SIG-UI-036), so this is emitted as committed static files at build time —
// one per canonical slug path (`dossier/usa/ca.json` — P35.45) — rather than
// served from a live API; the shape is the `/v1` dossier contract.
//
// P35.45 (K4 §8.1): the twin also resolves the OLD flat slugs. A static host
// cannot serve a real 301/300, so each history row emits a redirect DOCUMENT
// at the old `.json` address carrying the equivalent semantics:
//   - `moved`/`corrected` → `{ "status": 301, "location": "<canonical>.json" }`
//   - `split`             → `{ "status": 300, "choices": [ … ] }`
// and `/dossier/unplaced.json` serves the `sig.unplaced-report/1` twin.
import type { APIRoute, GetStaticPaths } from "astro";
import { dossierJsonPath, renderDossierJson } from "../../lib/dossier";
import type { Dossier } from "../../lib/dossier";
import { getDossiers, getJurisdictionKeyMap, getSlugHistory, getUnplacedReport } from "../../lib/data";
import { getReleaseStamp } from "../../lib/release-stamp";

type JsonProps =
  | { kind: "dossier"; dossier: Dossier }
  | { kind: "unplaced"; report: Record<string, unknown> }
  | { kind: "redirect"; body: Record<string, unknown> };

const jsonPath = (slugPath: string): string => dossierJsonPath(slugPath);

export const getStaticPaths: GetStaticPaths = () => {
  const out: { params: { path: string }; props: JsonProps }[] = getDossiers().map(
    (d) => ({
      params: { path: d.slug },
      props: { kind: "dossier", dossier: d } satisfies JsonProps,
    }),
  );
  const taken = new Set(out.map((p) => p.params.path));

  const report = getUnplacedReport();
  if (report !== null && !taken.has("unplaced")) {
    out.push({ params: { path: "unplaced" }, props: { kind: "unplaced", report } });
    taken.add("unplaced");
  }

  // Back-compat JSON stubs — the machine form of the moved/split stubs the
  // HTML route renders (K4 §8.1: jkey, slug path or legacy slug all resolve).
  const keyMap = getJurisdictionKeyMap();
  const targetFor = (jkey: string) => {
    if (jkey === "unplaced") {
      return { jkey, slug_path: "unplaced", json: jsonPath("unplaced") };
    }
    const row = keyMap?.get(jkey);
    return row?.slug_path
      ? { jkey, slug_path: row.slug_path, json: jsonPath(row.slug_path) }
      : null;
  };
  for (const row of getSlugHistory()) {
    if (taken.has(row.slug)) continue;
    const successors = Array.isArray(row.successor)
      ? row.successor
      : row.successor !== undefined
        ? [row.successor]
        : [];
    const targets = successors
      .map((j) => targetFor(String(j)))
      .filter((t): t is NonNullable<typeof t> => t !== null);
    const body =
      row.kind === "split"
        ? {
            status: 300,
            kind: "split",
            note: row.note ?? "this slug covered more than one jurisdiction",
            choices: targets,
          }
        : {
            status: 301,
            kind: row.kind,
            note: row.note ?? "this dossier moved to a canonical jurisdiction path",
            location: targets[0]?.json ?? null,
            target: targets[0] ?? null,
          };
    out.push({
      params: { path: row.slug },
      props: { kind: "redirect", body },
    });
    taken.add(row.slug);
  }
  return out;
};

export const GET: APIRoute = ({ props }) => {
  const p = props as JsonProps;
  const origin = new URL(import.meta.env.SITE ?? "https://surveillancegraph.org").origin;
  // P35.13 (SIG-REL-009, G3 §6.1): the JSON twin carries the release + licence
  // blocks when a sig.site-release/1 is bound — `null` bound-free.
  const stamp = getReleaseStamp();
  const body =
    p.kind === "dossier"
      ? renderDossierJson(p.dossier, origin, stamp?.releaseBlock)
      : p.kind === "unplaced"
        ? p.report
        : p.body;
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
