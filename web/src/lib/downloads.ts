// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The `sig.download-listing/1` contract (P36.50, R11-K13-TX-10b / J3 §6,
 * SIG-TRANSP-014/018) — every downloadable file of a release with licence,
 * format, size, row count and sha256, plus the R2-host download links (A-3=a)
 * and the pipeline-signature block (D-J3-8 = a; `unsigned` is declared, never
 * silent). `/data/` renders it as the mutable latest view; the immutable
 * `/releases/<pub>/data/` page renders the bound copy in the release tree.
 */

export const DOWNLOAD_LISTING_SCHEMA = "sig.download-listing/1";

export interface DownloadFile {
  path: string;
  name: string;
  kind: "compartment" | "source-slice" | "dossier-slice" | "attribution" | "transparency" | string;
  format: string;
  media_type: string;
  compartment: string | null;
  license: string;
  byte_size: number;
  sha256: string;
  href: string;
  row_count?: number;
  schema?: string;
  source_id?: string;
  dossier_slug?: string;
  dossier_compartment?: string;
}

export interface DownloadGroup {
  id: string;
  kind: "compartment" | "source" | "dossier" | "release" | "transparency" | string;
  title: string;
  license?: string;
  source_id?: string;
  dossier_slug?: string;
  compartment?: string;
  files: string[];
}

export interface DownloadListing {
  schema: string;
  release_id: string;
  publication_id: string | null;
  generated_at: string;
  mirror: {
    provider: string;
    base_url: string;
    bucket: string;
    enabled: boolean;
    status: string;
    note: string;
  };
  signature: {
    algorithm: string;
    key: string;
    state: "signed" | "unsigned";
    checksum_file: string;
    signature_file: string;
    public_key_file: string;
    reason?: string;
    note: string;
  };
  files: DownloadFile[];
  groups: DownloadGroup[];
  counts: { files: number; bytes: number; compartments: number; sources: number };
  metadata: Record<string, string>;
  note: string;
  release?: { label: string; publication_id: string; as_of_world: string };
}

export function isDownloadListing(v: unknown): v is DownloadListing {
  const o = v as Partial<DownloadListing> | null;
  return (
    !!o &&
    o.schema === DOWNLOAD_LISTING_SCHEMA &&
    typeof o.release_id === "string" &&
    !!o.mirror &&
    typeof o.mirror.base_url === "string" &&
    !!o.signature &&
    (o.signature.state === "signed" || o.signature.state === "unsigned") &&
    Array.isArray(o.files) &&
    Array.isArray(o.groups) &&
    o.files.every(
      (f) =>
        typeof f.path === "string" &&
        typeof f.license === "string" &&
        typeof f.sha256 === "string" &&
        typeof f.href === "string" &&
        typeof f.byte_size === "number",
    )
  );
}

export function filesByPath(l: DownloadListing): Map<string, DownloadFile> {
  return new Map(l.files.map((f) => [f.path, f]));
}

export function formatBytes(n: number): string {
  if (n >= 1 << 20) return `${(n / (1 << 20)).toFixed(1)} MiB`;
  if (n >= 1 << 10) return `${(n / (1 << 10)).toFixed(1)} KiB`;
  return `${n} B`;
}
