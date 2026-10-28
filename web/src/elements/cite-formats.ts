// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4) — the pure formatter half of `<sig-cite>`.
 *
 * The server-rendered citation block always carries the verbatim J3 §8.2
 * sentence; the element offers the same citation restated in named register
 * formats — plain (the verbatim line), APA 7, Chicago 17 author-date-ish
 * web form, and a Bluebook-flavoured legal form. Every format is built only
 * from the fields the page itself renders (title, as-of pair, ruleset,
 * release, URL) — a format never invents a fact the block does not carry.
 */

export interface CiteFields {
  /** Page title as rendered in the H1. */
  title: string;
  /** Short release label (e.g. `2026.10-a1b2c3d`); empty in the unreleased build. */
  release: string;
  /** `as_of_world` — the data's observed-state date (ISO `YYYY-MM-DD`). */
  asOfWorld: string;
  /** `as_of_belief` — the build's belief pin (ISO `YYYY-MM-DD`). */
  asOfBelief: string;
  /** Ruleset version the page was rendered under. */
  ruleset: string;
  /** The cite URL (immutable snapshot when published, else the permalink). */
  url: string;
  /** The verbatim cite line the block already renders (the plain format). */
  plain: string;
}

export type CiteFormat = "plain" | "apa" | "chicago" | "legal";

export const CITE_FORMATS: { id: CiteFormat; label: string }[] = [
  { id: "plain", label: "Plain" },
  { id: "apa", label: "APA" },
  { id: "chicago", label: "Chicago" },
  { id: "legal", label: "Legal" },
];

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** `YYYY-MM-DD` → `October 28, 2026`; falls back to the raw string. */
export function formatDateUS(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!m) return iso;
  const month = MONTHS[Number(m[2]) - 1];
  return month ? `${month} ${Number(m[3])}, ${m[1]}` : iso;
}

function yearOf(iso: string): string {
  const m = /^(\d{4})/.exec(iso.trim());
  return m ? m[1] : "n.d.";
}

/**
 * Render one format. The register word "SIG" stands for the publishing
 * body; the site name is omitted where a style drops a site identical to
 * the author (APA 7 §9.2/§10.16).
 */
export function formatCite(fields: CiteFields, format: CiteFormat): string {
  switch (format) {
    case "plain":
      return fields.plain;
    case "apa": {
      const year = yearOf(fields.asOfWorld);
      const retrieved =
        fields.release === ""
          ? ` Retrieved ${formatDateUS(fields.asOfBelief)},`
          : "";
      return `Surveillance Infrastructure Graph. (${year}). ${fields.title}.${retrieved} ${fields.url}`;
    }
    case "chicago":
      return (
        `Surveillance Infrastructure Graph. "${fields.title}." ` +
        `Data as of ${formatDateUS(fields.asOfWorld)}. ` +
        `Accessed ${formatDateUS(fields.asOfBelief)}. ${fields.url}.`
      );
    case "legal":
      return (
        `Surveillance Infrastructure Graph, ${fields.title}, ` +
        `${fields.url} (data as of ${formatDateUS(fields.asOfWorld)})`
      );
  }
}
