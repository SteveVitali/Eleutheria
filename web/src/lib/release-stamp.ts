// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.13 / SIG-REL-009 (G3 §6.1/§6.2) — the release-stamp reader.
 *
 * Every public page names the release it was built from: label, data as-of,
 * build instant, linked code commit, publication id, and the pointer to the
 * release's own `release.json` (`<link rel="describedby">`). The stamp's only
 * data source is the release's `sig.site-release/1` object — itself a
 * rendering of the `sig.publication-descriptor/2` (SIG-MEM-011), so no value
 * is ever recomputed or hand-supplied here.
 *
 * Provenance seam (build-time, never client JS):
 *
 *   - `fixtures` mode — `null` (a development build carries no release; the
 *     honest dev-build sentence keeps rendering).
 *   - `export` mode — read, in order: `$SIG_RELEASE_JSON` (a path to the
 *     release's `release.json`), `$SIG_RELEASE_DIR/release.json`, then
 *     `<exportDir>/release.json` (the file staged beside the export bytes the
 *     site builds from). Unset/absent in all three → `null`: the interim
 *     release-id sentence renders until a republish supplies the object.
 *     A *present but malformed* document is a hard build error — a stamp that
 *     cannot verify is never silently degraded.
 */

import { existsSync, readFileSync } from "node:fs";
import { dataSource, exportDir } from "./data";

/** The wire schema id the stamp reads (emitted by `exports.site_release`). */
export const SITE_RELEASE_SCHEMA = "sig.site-release/1";

export interface ReleaseStamp {
  /** `sig-YYYY-MM-DD.N` — the human release label. */
  label: string;
  /** `p-<64hex>` — the content-addressed publication id. */
  publicationId: string;
  /** `p-3f9ac21e…` — the abbreviated form the stamp prints. */
  publicationShort: string;
  /** The raw ISO instant the data is pinned at. */
  asOfWorldInstant: string;
  /** `2026-10-15 06:02 UTC` — the §6.1 display form (seconds when non-zero). */
  asOfWorld: string;
  /** The raw ISO build instant. */
  builtAtInstant: string;
  /** The build instant in §6.1 display form. */
  builtAt: string;
  /** The first eight hex of the release's code commit. */
  commit8: string;
  /** The commit's repository URL (the stamp's link target). */
  commitHref: string;
  /** The release's own release.json href — always `/release.json` on the
   * latest-view site (the site-root object names the active release). */
  describedby: string;
  /** `<meta name="sig-release">` content — `<label> <pub>` (G3 §6.1). */
  metaContent: string;
  /** The JSON twin's `release` block — `{label, publication_id, as_of_world}`
   * in wire shape (§6.1: the same identity on the machine-readable twins). */
  releaseBlock: { label: string; publication_id: string; as_of_world: string };
}

const LABEL_RE = /^sig-\d{4}-\d{2}-\d{2}\.\d+$/;
const PUB_RE = /^p-[0-9a-f]{64}$/;
const HEX40_RE = /^[0-9a-f]{40}$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
// An ISO-8601 instant with a UTC designator — the descriptor's instants are
// always Z-normalised (release_identity.parse_instant enforces it upstream;
// the reader re-checks rather than re-derives).
const INSTANT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$/;

function fail(path: string, what: string): never {
  throw new Error(
    `${path}: not a valid ${SITE_RELEASE_SCHEMA} — ${what}. ` +
      "The release stamp never renders an unverified identity.",
  );
}

function isInstant(v: unknown): v is string {
  return typeof v === "string" && INSTANT_RE.test(v) && !Number.isNaN(Date.parse(v));
}

/** `2026-10-15 06:02 UTC` — the §6.1 stamp's instant form. */
function stampInstant(instant: string): string {
  const [d, t] = instant.replace("+00:00", "Z").split("T");
  const hms = t.replace(/Z$/, "");
  const hm = hms.endsWith(":00") ? hms.slice(0, 5) : hms;
  return `${d} ${hm} UTC`;
}

/** Fail-closed validation of a parsed `sig.site-release/1` document. */
export function validateSiteReleaseDoc(doc: unknown, path: string): ReleaseStamp {
  if (typeof doc !== "object" || doc === null || Array.isArray(doc)) {
    fail(path, `expected a JSON object, got ${Array.isArray(doc) ? "array" : typeof doc}`);
  }
  const o = doc as Record<string, unknown>;
  if (o.schema !== SITE_RELEASE_SCHEMA) {
    fail(path, `schema ${JSON.stringify(o.schema)} != ${SITE_RELEASE_SCHEMA}`);
  }
  if (typeof o.label !== "string" || !LABEL_RE.test(o.label)) {
    fail(path, `label ${JSON.stringify(o.label)} is not sig-YYYY-MM-DD.N`);
  }
  if (typeof o.publication_id !== "string" || !PUB_RE.test(o.publication_id)) {
    fail(path, `publication_id ${JSON.stringify(o.publication_id)} is not p-<64hex>`);
  }
  if (typeof o.descriptor_sha256 !== "string" || !HEX64_RE.test(o.descriptor_sha256)) {
    fail(path, "descriptor_sha256 is not 64-hex");
  }
  if (!isInstant(o.as_of_world)) fail(path, "as_of_world is not an ISO instant");
  if (!isInstant(o.as_of_belief)) fail(path, "as_of_belief is not an ISO instant");
  if (typeof o.belief_pinned !== "boolean") fail(path, "belief_pinned is not a bool");
  if (!isInstant(o.built_at)) fail(path, "built_at is not an ISO instant");
  const code = o.code as Record<string, unknown> | undefined;
  if (
    !code ||
    typeof code.commit !== "string" ||
    !HEX40_RE.test(code.commit) ||
    typeof code.url !== "string" ||
    !code.url ||
    typeof code.repository !== "string" ||
    !code.repository
  ) {
    fail(path, "code block needs commit (40-hex), url and repository");
  }
  const integrity = o.integrity_manifest as Record<string, unknown> | undefined;
  if (
    !integrity ||
    typeof integrity.path !== "string" ||
    !integrity.path ||
    typeof integrity.sha256 !== "string" ||
    !HEX64_RE.test(integrity.sha256)
  ) {
    fail(path, "integrity_manifest needs path + 64-hex sha256");
  }
  const pub = o.publication_id;
  return {
    label: o.label,
    publicationId: pub,
    publicationShort: `${pub.slice(0, 10)}…`,
    asOfWorldInstant: o.as_of_world as string,
    asOfWorld: stampInstant(o.as_of_world as string),
    builtAtInstant: o.built_at as string,
    builtAt: stampInstant(o.built_at as string),
    commit8: code.commit.slice(0, 8),
    commitHref: code.url,
    describedby: "/release.json",
    metaContent: `${o.label} ${pub}`,
    releaseBlock: {
      label: o.label,
      publication_id: pub,
      as_of_world: o.as_of_world as string,
    },
  };
}

function releaseJsonPath(): string | null {
  const direct = process.env.SIG_RELEASE_JSON;
  if (direct) return direct;
  const dir = process.env.SIG_RELEASE_DIR;
  if (dir) return `${dir.replace(/\/$/, "")}/release.json`;
  const beside = `${exportDir()}/release.json`;
  return existsSync(beside) ? beside : null;
}

/**
 * The site's release stamp, or `null` when no release identity is bound —
 * the honest development/interim state, never a fabricated one. In `export`
 * mode a bound-but-malformed `release.json` throws (fail-closed): a stamp
 * that cannot verify is a build error, not a quiet degradation.
 */
export function getReleaseStamp(): ReleaseStamp | null {
  if (dataSource() === "fixtures") return null;
  const path = releaseJsonPath();
  if (path === null || !existsSync(path)) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(path, "utf-8"));
  } catch (cause) {
    throw new Error(`${path}: unreadable release.json`, { cause });
  }
  return validateSiteReleaseDoc(parsed, path);
}
