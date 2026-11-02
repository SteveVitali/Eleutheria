// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.48 (UX9-3; SIG-TRANSP-033): `sources.csv` — the flattened RFC 4180
// export of the same sig.source-row/1 rows the table renders (K9 §8; the
// Table Schema is its generated twin at sources.schema.json).
import type { APIRoute } from "astro";
import { getTableRows, tableCsv } from "../../../lib/sources-table";

export const GET: APIRoute = () => {
  const { rows, asOf } = getTableRows();
  return new Response(tableCsv(rows, asOf), {
    headers: { "content-type": "text/csv; charset=utf-8" },
  });
};
