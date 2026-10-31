// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.36 (K13 capstone O3): "Download this view" — the per-dossier sites list
// as CSV at `/dossier/<path>/sites/index.csv`. The download carries the FULL
// list (never a page slice) with `#`-comment licence provenance lines leading,
// per ADR-224's CSV convention.
import type { APIRoute } from "astro";
import {
  getDossiers,
  getDossierIndex,
  getJurisdictionKeyMap,
  getMapSites,
  getSiteMetadata,
} from "../../../../lib/data";
import {
  buildJurisdictionLookup,
  buildSitesModel,
  emittedSiteLists,
  sitesCsv,
} from "../../../../lib/sites";
import type { SiteList } from "../../../../lib/sites";
import { dossierDisplayTitle } from "../../../../lib/jurisdictions";
import type { Dossier } from "../../../../lib/dossier";

export function getStaticPaths() {
  const dossiers = getDossiers();
  const lookup = buildJurisdictionLookup(
    dossiers,
    getDossierIndex(),
    getJurisdictionKeyMap(),
  );
  const model = buildSitesModel(getMapSites(), lookup);
  const bySlug = new Map<string, Dossier>(dossiers.map((d) => [d.slug, d]));
  return emittedSiteLists(model).map((list) => ({
    params: { path: list.slug },
    props: { list, dossier: bySlug.get(list.slug) ?? null },
  }));
}

interface Props {
  list: SiteList;
  dossier: Dossier | null;
}

export const GET: APIRoute<Props> = ({ props }) => {
  const { list, dossier } = props;
  const meta = getSiteMetadata();
  const name = dossier
    ? dossierDisplayTitle(dossier.subject_label, dossier.jurisdiction)
    : list.slug;
  const licences = [...new Set(list.rows.map((r) => r.licence).filter((l): l is string => l !== null))];
  const body = sitesCsv(list, {
    dossierName: name,
    asOf: meta.asOf.as_of_world,
    licence: licences.length === 1 ? licences[0] : licences.join("; ") || null,
  });
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="sig-sites-${list.slug.replace(/\//g, "-")}.csv"`,
    },
  });
};
