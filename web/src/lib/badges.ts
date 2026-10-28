// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.22 (K14 UXK14-3a / §4.6 badge row, SIG-UI-024; J4; P15): the neutral
 * text-badge contract (`sig.badge/1`) — the ONE component-side vocabulary for
 * the directness, access-kind, licence and mirror badges a record or source
 * surface renders.
 *
 * A badge is a NEUTRAL text channel: a kind word and a value word, never a
 * coloured verdict (K14's table: "neutral text badges"). Every label comes
 * from the shared lexicon where a state exists (SIG-UI-143: the raw enum is a
 * machine key, never prose) — `directness` reads `states.directness`
 * (§10.5's D1–D6) and `access_kind` reads `states.access` (§12.2's three
 * kinds). `licence` carries the upstream SPDX id verbatim (a name, not an
 * enum — the badge never paraphrases a licence). `mirror` names where the
 * bytes a download/view would come from (J3 §6's R2 mirror + J4's lanes):
 *   - `mirrored`  — SIG holds a copy the download can be served from;
 *   - `at_source` — the bytes live only at the upstream source;
 *   - `no_bytes`  — no publishable bytes are held (metadata only).
 *
 * Pure data + logic (no markup, no colour — `Badge.astro` + `epistemic.css`
 * supply both), so the closed vocabularies are unit-testable and an unknown
 * value fails the build rather than leaking an unvetted label (SIG-ENG-042).
 */

import { lexiconState } from "./lexicon";

/** The four badge kinds (`data-badge` on the component). */
export const BADGE_KINDS = ["directness", "access_kind", "licence", "mirror"] as const;
export type BadgeKind = (typeof BADGE_KINDS)[number];

/** §10.5's closed directness classes — labels live in the lexicon. */
export const DIRECTNESS_CLASSES = ["D1", "D2", "D3", "D4", "D5", "D6"] as const;
export type DirectnessClass = (typeof DIRECTNESS_CLASSES)[number];

/** §12.2's three access kinds — labels + symbols live in the lexicon. */
export const ACCESS_KINDS = [
  "CONFIGURED_ACCESS",
  "DECLARED_POLICY",
  "OBSERVED_USE",
] as const;
export type AccessKind = (typeof ACCESS_KINDS)[number];

/** Where a download's bytes are served from (J3 §6 mirror / J4 lanes). */
export const MIRROR_STATES = ["mirrored", "at_source", "no_bytes"] as const;
export type MirrorState = (typeof MIRROR_STATES)[number];

/** The kind word rendered before the value — plain, never an enum. */
const KIND_LABELS: Record<BadgeKind, string> = {
  directness: "Directness",
  access_kind: "Access",
  licence: "Licence",
  mirror: "Mirror",
};

/** The neutral value words for the mirror states (never colour-carried). */
const MIRROR_LABELS: Record<MirrorState, { label: string; meaning: string }> = {
  mirrored: {
    label: "copy held",
    meaning: "SIG holds a copy; a download can be served from SIG's archive.",
  },
  at_source: {
    label: "at the source",
    meaning: "SIG links out; the bytes live only at the upstream source.",
  },
  no_bytes: {
    label: "no bytes",
    meaning: "No publishable bytes are held — the record is metadata only.",
  },
};

/** One resolved badge: kind + the machine value + the visible words. */
export interface BadgeSpec {
  kind: BadgeKind;
  /** The kind word rendered first ("Directness", "Access", "Licence", "Mirror"). */
  kindLabel: string;
  /** The stored value token — machine channel only (`data-value`, never prose). */
  value: string;
  /** The visible value word (lexicon label, verbatim SPDX id, or a mirror word). */
  label: string;
  /** The plain-language gloss the badge's disclosure can render. */
  meaning: string;
}

function resolve(kind: BadgeKind, value: string): BadgeSpec {
  const kindLabel = KIND_LABELS[kind];
  const v = value.trim();
  switch (kind) {
    case "directness": {
      if (!(DIRECTNESS_CLASSES as readonly string[]).includes(v)) {
        throw new Error(`sig.badge/1 directness: unknown class "${value}" (§10.5 D1–D6)`);
      }
      const state = lexiconState("directness", v);
      return { kind, kindLabel, value: v, label: state.label, meaning: state.plain };
    }
    case "access_kind": {
      if (!(ACCESS_KINDS as readonly string[]).includes(v)) {
        throw new Error(
          `sig.badge/1 access_kind: unknown kind "${value}" (§12.2 access kinds)`,
        );
      }
      const state = lexiconState("access", v);
      return { kind, kindLabel, value: v, label: state.label, meaning: state.plain };
    }
    case "licence": {
      // The upstream SPDX identifier verbatim — a name, never paraphrased.
      if (v === "" || /\s/.test(v) || v.length > 64) {
        throw new Error(`sig.badge/1 licence: "${value}" is not a licence identifier`);
      }
      return {
        kind,
        kindLabel,
        value: v,
        label: v,
        meaning: "The upstream licence the source's rows are published under.",
      };
    }
    case "mirror": {
      if (!(MIRROR_STATES as readonly string[]).includes(v)) {
        throw new Error(`sig.badge/1 mirror: unknown state "${value}" (J4 lanes)`);
      }
      const m = MIRROR_LABELS[v as MirrorState];
      return { kind, kindLabel, value: v, label: m.label, meaning: m.meaning };
    }
  }
}

/** The directness badge for a §10.5 class. */
export function directnessBadge(cls: string): BadgeSpec {
  return resolve("directness", cls);
}

/** The access-kind badge for a §12.2 kind. */
export function accessKindBadge(kind: string): BadgeSpec {
  return resolve("access_kind", kind);
}

/** The licence badge carrying the upstream SPDX id verbatim. */
export function licenceBadge(spdx: string): BadgeSpec {
  return resolve("licence", spdx);
}

/** The mirror badge for a byte-serving state. */
export function mirrorBadge(state: string): BadgeSpec {
  return resolve("mirror", state);
}
