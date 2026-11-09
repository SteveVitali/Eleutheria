// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.24 (GX-08a) — the per-compartment overview download endpoint
// (`/graph/<ov>/<file>`): the emitted bytes verbatim in export mode, the
// fixture-derived shapes otherwise — no named download is a dead link.
import type { APIRoute, GetStaticPaths } from "astro";
import { getGraphIndex, getGraphOverviewFile } from "../../../lib/data";

const FILES = (comp: string) => [
  `${comp}.json`,
  `nodes.${comp}.csv`,
  `edges.${comp}.csv`,
  `overview.${comp}.svg`,
];

export const getStaticPaths: GetStaticPaths = () =>
  getGraphIndex().flatMap((r) =>
    r.compartments.flatMap((c) =>
      FILES(c).map((file) => ({ params: { ov: r.id, file } })),
    ),
  );

const MIME: Record<string, string> = {
  ".json": "application/json",
  ".csv": "text/csv",
  ".svg": "image/svg+xml",
};

export const GET: APIRoute = ({ params }) => {
  const bytes = getGraphOverviewFile(String(params.ov), String(params.file));
  if (bytes === null) return new Response("not found", { status: 404 });
  const ext = String(params.file).match(/\.[^.]+$/)?.[0] ?? "";
  return new Response(bytes, {
    headers: { "content-type": `${MIME[ext] ?? "application/octet-stream"}; charset=utf-8` },
  });
};
