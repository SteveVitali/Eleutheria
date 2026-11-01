// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.42b (K2 GX-06a 06b): the entity figure endpoint — serves the figure
 * kit's emitted SVG bytes as a standalone document. The page renders the
 * figure via <img> (the axe-clean, budget-safe presentation); opened
 * directly, the standalone SVG's node links navigate — every drawn node an
 * <a href> (K2 §4.2 row 7) inside the served document, never inline inside
 * a page where interactive SVG links nest inside the accessibility tree's
 * interactive-controls rule. Bytes re-verify the safety contract at this
 * seam — no scripts/handlers/external refs are ever served (SIG-UI-096).
 */
import type { APIContext } from "astro";
import { getEntityFigureBytes, type EntityFigureKind } from "../../../../lib/data";
import { entityIndex } from "../../../../lib/entity-page";
import { getEntityLabelRows, getEntityPageTwins } from "../../../../lib/data";
import { assertInlineSvgSafe } from "../../../../lib/entity-figures";

export function getStaticPaths() {
  const index = entityIndex(getEntityLabelRows());
  const paths: { params: { type: string; key: string; fig: string } }[] = [];
  for (const row of index.rows) {
    const key = `${row.slug}--${row.hash}`;
    if (getEntityPageTwins(row.url_type!, key).length === 0) continue;
    for (const fig of ["ego", "timeline", "map"] as const) {
      if (getEntityFigureBytes(row.url_type!, key, fig) !== null) {
        paths.push({ params: { type: row.url_type!, key, fig } });
      }
    }
  }
  return paths;
}

export function GET({ params }: APIContext) {
  const fig = params.fig as EntityFigureKind;
  const svg = getEntityFigureBytes(params.type!, params.key!, fig);
  if (svg === null) return new Response("not found", { status: 404 });
  assertInlineSvgSafe(svg, `entity figure ${params.type}/${params.key}/${fig}.svg`);
  return new Response(svg, {
    headers: { "content-type": "image/svg+xml; charset=utf-8" },
  });
}
