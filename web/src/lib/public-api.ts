// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The public read-API base URL, baked at BUILD time (P34.13 / QW-11). The
 * deployed base is environment-specific (HG-12 — no staging/local host is
 * baked in); the committed default is the public read API recorded at launch
 * (docs/build/reports/LAUNCH_RECORD_2026-09-24.md §1), and a publish can
 * override it with SIG_API_BASE_URL. Mirrors the curation.ts env pattern.
 */
export function publicApiBaseUrl(): string {
  return (
    process.env.SIG_API_BASE_URL ?? "https://sig-api-e5ctyx36jq-uc.a.run.app"
  ).replace(/\/+$/, "");
}

/** The API's acceptable-use terms endpoint (SIG-API-013). */
export function apiTermsUrl(): string {
  return `${publicApiBaseUrl()}/terms`;
}
