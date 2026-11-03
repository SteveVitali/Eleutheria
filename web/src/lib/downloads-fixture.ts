// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The committed `sig.download-listing/1` fixture the `/data/` page renders in
 * `fixtures`/`national` mode (P36.50). Models the honest interim posture: the
 * R2 mirror row is committed-disabled (enabled by the publish leg) and the
 * OP-20 pipeline key is not yet provisioned — `unsigned` is declared, never
 * silently signed.
 */
import type { DownloadListing } from "./downloads";

export const DOWNLOAD_LISTING_FIXTURE: DownloadListing = {
  schema: "sig.download-listing/1",
  release_id: "sig-export-20261102T000000Z-deadbeef",
  publication_id: null,
  generated_at: "2026-11-02T00:00:00Z",
  mirror: {
    provider: "cloudflare-r2",
    base_url: "https://files.surveillancegraph.org",
    bucket: "sig-bulk",
    enabled: false,
    status: "committed-disabled — enabled by the P35.5 live leg after OP-09 + the OM-20 list",
    note: "Download links name the R2 host's content-hash keys; the mirror row's committed enabled posture is reported verbatim — objects resolve once the publish leg has pushed them.",
  },
  signature: {
    algorithm: "minisign",
    key: "OP-20 — the SIG release pipeline's minisign key (Secret Manager; SIG-REL-015)",
    state: "unsigned",
    checksum_file: "SHA256SUMS",
    signature_file: "SHA256SUMS.minisig",
    public_key_file: "sig-release.minisign.pub",
    reason: "the pipeline key is not yet provisioned (OP-20 — operator action)",
    note: "the signature proves integrity, never approval (SIG-REL-015)",
  },
  files: [
    { path: "sig_graph/sites.csv", name: "sites.csv", kind: "compartment", format: "csv", media_type: "text/csv", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 123456, sha256: "a".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/sig_graph/sites.aaaaaaaaaaaa.csv", row_count: 812 },
    { path: "sig_graph/statements.jsonl", name: "statements.jsonl", kind: "compartment", format: "jsonl", media_type: "application/x-ndjson", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 234567, sha256: "b".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/sig_graph/statements.bbbbbbbbbbbb.jsonl", row_count: 2048, schema: "sig.statement/1" },
    { path: "sig_graph/ATTRIBUTION.txt", name: "ATTRIBUTION.txt", kind: "attribution", format: "txt", media_type: "text/plain", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 2048, sha256: "c".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/sig_graph/ATTRIBUTION.cccccccccccc.txt" },
    { path: "sig_graph/LICENCE.txt", name: "LICENCE.txt", kind: "attribution", format: "txt", media_type: "text/plain", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 512, sha256: "d".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/sig_graph/LICENCE.dddddddddddd.txt" },
    { path: "osm_physical/sites.csv", name: "sites.csv", kind: "compartment", format: "csv", media_type: "text/csv", compartment: "osm_physical", license: "ODbL-1.0", byte_size: 98765, sha256: "e".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/osm_physical/sites.eeeeeeeeeeee.csv", row_count: 640 },
    { path: "by-source/camreg_trpa_us/statements.jsonl.gz", name: "statements.jsonl.gz", kind: "source-slice", format: "jsonl.gz", media_type: "application/gzip", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 4096, sha256: "f".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-source/camreg_trpa_us/statements.ffffffffffff.jsonl.gz", row_count: 96, schema: "sig.statement/1", source_id: "camreg_trpa_us" },
    { path: "by-source/camreg_trpa_us/sites.csv.gz", name: "sites.csv.gz", kind: "source-slice", format: "csv.gz", media_type: "application/gzip", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 2048, sha256: "1".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-source/camreg_trpa_us/sites.111111111111.csv.gz", row_count: 34, source_id: "camreg_trpa_us" },
    { path: "by-source/camreg_trpa_us/ATTRIBUTION.txt", name: "ATTRIBUTION.txt", kind: "source-slice", format: "txt", media_type: "text/plain", compartment: "sig_graph", license: "CC-BY-4.0", byte_size: 1024, sha256: "2".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-source/camreg_trpa_us/ATTRIBUTION.222222222222.txt", source_id: "camreg_trpa_us" },
    { path: "by-source/osm_overpass/statements.jsonl.gz", name: "statements.jsonl.gz", kind: "source-slice", format: "jsonl.gz", media_type: "application/gzip", compartment: "osm_physical", license: "ODbL-1.0", byte_size: 3072, sha256: "3".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-source/osm_overpass/statements.333333333333.jsonl.gz", row_count: 128, schema: "sig.statement/1", source_id: "osm_overpass" },
    { path: "by-dossier/usa/ok/public_record/statements.jsonl.gz", name: "statements.jsonl.gz", kind: "dossier-slice", format: "jsonl.gz", media_type: "application/gzip", compartment: "public_record", license: "CC0-1.0", byte_size: 5120, sha256: "6".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-dossier/usa/ok/public_record/statements.666666666666.jsonl.gz", row_count: 189, schema: "sig.statement/1", dossier_slug: "usa/ok", dossier_compartment: "public_record" },
    { path: "by-dossier/usa/ok/public_record/ATTRIBUTION.txt", name: "ATTRIBUTION.txt", kind: "dossier-slice", format: "txt", media_type: "text/plain", compartment: "public_record", license: "CC0-1.0", byte_size: 1024, sha256: "7".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/by-dossier/usa/ok/public_record/ATTRIBUTION.777777777777.txt", dossier_slug: "usa/ok", dossier_compartment: "public_record" },
    { path: "datapackage.json", name: "datapackage.json", kind: "transparency", format: "json", media_type: "application/json", compartment: "metadata", license: "CC-BY-4.0", byte_size: 8192, sha256: "4".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/datapackage.444444444444.json" },
    { path: "web/sources.json", name: "sources.json", kind: "transparency", format: "json", media_type: "application/json", compartment: "web", license: "CC-BY-4.0", byte_size: 4096, sha256: "5".repeat(64), href: "https://files.surveillancegraph.org/sig-export-20261102T000000Z-deadbeef/web/sources.555555555555.json", row_count: 2, schema: "sig.source-licence-table/1" },
  ],
  groups: [
    { id: "compartment:sig_graph", kind: "compartment", title: "sig_graph compartment", license: "CC-BY-4.0", files: ["sig_graph/sites.csv", "sig_graph/statements.jsonl", "sig_graph/ATTRIBUTION.txt", "sig_graph/LICENCE.txt"] },
    { id: "compartment:osm_physical", kind: "compartment", title: "osm_physical compartment", license: "ODbL-1.0", files: ["osm_physical/sites.csv"] },
    { id: "source:camreg_trpa_us", kind: "source", title: "TRPA camera registry", source_id: "camreg_trpa_us", compartment: "sig_graph", license: "CC-BY-4.0", files: ["by-source/camreg_trpa_us/statements.jsonl.gz", "by-source/camreg_trpa_us/sites.csv.gz", "by-source/camreg_trpa_us/ATTRIBUTION.txt"] },
    { id: "source:osm_overpass", kind: "source", title: "osm_overpass", source_id: "osm_overpass", compartment: "osm_physical", license: "ODbL-1.0", files: ["by-source/osm_overpass/statements.jsonl.gz"] },
    { id: "dossier:usa/ok", kind: "dossier", title: "Oklahoma", dossier_slug: "usa/ok", compartment: "public_record", license: "CC0-1.0", files: ["by-dossier/usa/ok/public_record/statements.jsonl.gz", "by-dossier/usa/ok/public_record/ATTRIBUTION.txt"] },
    { id: "release", kind: "release", title: "Release descriptor + integrity files", license: "CC-BY-4.0", files: ["datapackage.json", "SHA256SUMS", "SHA256SUMS.minisig", "sig-release.minisign.pub"] },
    { id: "transparency", kind: "transparency", title: "Transparency + web-consumption metadata", license: "CC-BY-4.0", files: ["web/sources.json"] },
  ],
  counts: { files: 11, bytes: 481772, compartments: 3, sources: 2 },
  metadata: { datapackage: "datapackage.json", catalog: "catalog.jsonld", dictionary: "dictionary.json", provenance: "provenance.jsonld", manifest: "manifest.json" },
  note: "Every file is listed with the licence and attribution its bundle's ATTRIBUTION.txt/LICENCE.txt states verbatim — captured terms and the operator-accepted basis (ADR-183, no withdrawal): a bad bundle is corrected by a new release, never retracted silently. The listing names but cannot list itself or the integrity files' self-referential members.",
};
