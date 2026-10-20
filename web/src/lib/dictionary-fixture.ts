// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The fixtures-mode data dictionary (P35.39, SIG-TRANSP-016).
 *
 * A small demonstration `sig.data-dictionary/1` document exercising the page's
 * render paths — a resource with an enum-sourced column, a unit column, the
 * shared rights block, and a document entry. The real dictionary a public
 * build renders is `<exportDir>/dictionary.json` — generated beside the bytes
 * it documents, never a copy.
 */

import type { DataDictionary } from "./dictionary";

export const DICTIONARY_FIXTURE: DataDictionary = {
  schema: "sig.data-dictionary/1",
  name: "SIG data dictionary",
  version: "demo-2026-09-30",
  created: "2026-09-30",
  ontology: {
    schema_file: "ontology/generated/jsonschema/sig.schema.json",
    schema_id: "https://surveillancegraph.org/schema/sig",
    version: "0.0.0-demo",
    metamodel_version: "1.7.0",
    sha256: "0".repeat(64),
    vocabulary_registry: "ontology/generated/registry/vocab_summary.json",
  },
  resources: [
    {
      name: "sites",
      title: "Published site observations",
      description:
        "One row per (site, source, rights-record) slice: the tier-reduced point plus " +
        "the disclosure columns — observation-level records, never a resolved census.",
      kind: "table",
      table_schema: "schemas/sites.tableschema.json",
      paths: ["sig_graph/sites.csv", "sig_graph/sites.geojson"],
      sources: ["demo_registry"],
      columns: [
        {
          name: "subject_id",
          type: "string",
          description: "the site's subject identifier",
          nullable: false,
        },
        {
          name: "technology",
          type: "string",
          description:
            "the subject's declared SKOS technology slug (null when unreported or conflicted)",
          nullable: true,
          enum_source: "linkml:skos:technology",
          enum_values: ["alpr-fixed", "camera-fixed-cctv", "gunshot-detection"],
        },
        {
          name: "n_sources",
          type: "integer",
          description:
            "the number of sources the slice's claims draw on — corroboration-visibility, " +
            "not a merged record",
          nullable: false,
          unit: "count",
        },
        {
          name: "geometry",
          type: "object",
          description:
            "the tier-reduced Point geometry — null when the point was withheld or the " +
            "envelope conflicted",
          nullable: true,
        },
        {
          name: "rights_license",
          type: "string",
          description: "the row's effective SPDX licence id (the shared rights block)",
          nullable: false,
        },
      ],
    },
  ],
  documents: [
    {
      path: "manifest.json",
      media_type: "application/json",
      description: "the export manifest — every emitted artifact, digest and compartment",
    },
    {
      path: "provenance.ttl",
      media_type: "text/turtle",
      schema: "sig.prov-lineage/1",
      description: "the PROV-O lineage graph in Turtle",
    },
  ],
};
