// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.48 (UX9-3; SIG-TRANSP-033): `sources.schema.json` — the generated
// Table Schema for sources.csv (one field per export column, so a column
// the schema does not name is a build failure, J3 §6.5).
import type { APIRoute } from "astro";
import { getTableRows, tableSchema } from "../../../lib/sources-table";

export const GET: APIRoute = () => {
  const { asOf } = getTableRows();
  return new Response(JSON.stringify(tableSchema(asOf), null, 2) + "\n", {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
};
