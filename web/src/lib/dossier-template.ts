// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.55 (K6 VIZ-02, SIG-UI-069): the ONE dossier template's composition
 * contract. Every dossier level renders through this plan — special dossier
 * kinds are typed variants inside it, never a second template (SIG-UI-069).
 *
 * The plan keeps the twelve §39.2 sections in their exact SIG-UI-010 order
 * (`validateDossier` already fails the build on any drift) and anchors the
 * v2 blocks where SIG-UI-069 names them:
 *
 *   header strip (K4 row fields)
 *   §1 At a glance — stat rows, locator, Figure 1, Explore bar
 *   §2–§7 deployed / cost / access / retention / usage / hardware
 *   'Where this comes from' (K5)
 *   §8–§10 policy / accountability events / timeline
 *   'Next decisions' (K7)
 *   §11 What we don't know (K11 gap links)
 *   'Other public resources' (D3-Q4 [B-27] = yes — neutral, UXR-06)
 *   §12 How we know this (dossier scope)
 *   the child-jurisdiction roll-up
 *
 * The network-figure slots ride INSIDE their sections (Figs 2–5 on §2, §3,
 * §4, §8 — K6 §4.1) as typed empty states until VIZ-01b lands the content.
 */

import type { Dossier, Section } from "./dossier";

/** One unit the page renders, in template order. */
export type TemplateUnit =
  | { kind: "header-strip" }
  | { kind: "section"; section: Section }
  | { kind: "where-this-comes-from" }
  | { kind: "next-decisions" }
  | { kind: "other-public-resources" }
  | { kind: "rollup" };

/**
 * The §39.2 sections that carry a network-figure slot (K6 §4.1: Fig 2 "Who
 * runs and supplies it" on deployed, Fig 3 "Who funds it" on cost, Fig 4
 * "Who can search this data" on access, Fig 5 "Which rules apply" on
 * policy) — typed empty states until VIZ-01b emits a slot.
 */
export const NETWORK_SLOT_SECTIONS: Readonly<Record<string, { figure: string; title: string }>> = {
  what_is_deployed: { figure: "fig-2", title: "Who runs and supplies it" },
  cost_and_expiry: { figure: "fig-3", title: "Who funds it" },
  who_else_can_see: { figure: "fig-4", title: "Who can search this data" },
  policy: { figure: "fig-5", title: "Which rules apply" },
};

/** The section id 'Where this comes from' renders after (K6/SIG-UI-069). */
export const WTCF_AFTER = "where_the_hardware_is";
/** 'Next decisions' renders after this section (before what_we_dont_know). */
export const DECISIONS_AFTER = "timeline";
/** 'Other public resources' renders after this section (before how_we_know_this). */
export const RESOURCES_AFTER = "what_we_dont_know";

/**
 * Compose the one template's render plan. Fail-closed: a section id not in
 * the plan position `validateDossier` guarantees is a build error, never a
 * silently dropped section (SIG-ENG-042).
 */
export function templatePlan(dossier: Dossier): TemplateUnit[] {
  const plan: TemplateUnit[] = [{ kind: "header-strip" }];
  for (const section of dossier.sections) {
    plan.push({ kind: "section", section });
    if (section.section_id === WTCF_AFTER) plan.push({ kind: "where-this-comes-from" });
    if (section.section_id === DECISIONS_AFTER) plan.push({ kind: "next-decisions" });
    if (section.section_id === RESOURCES_AFTER) plan.push({ kind: "other-public-resources" });
  }
  plan.push({ kind: "rollup" });
  return plan;
}

// ---------------------------------------------------------------------------
// 'Next decisions' (K7 / SIG-WATCH-009).
// ---------------------------------------------------------------------------

/**
 * The watch items for a dossier's place — matched on the place's name (the
 * `sig.watch-item/1` jurisdiction label carries the display name, not the
 * key). Sorted by derived decision date; items with none sort last.
 */
export function decisionsForDossier<T extends { jurisdiction: string }>(
  items: readonly T[],
  dossier: Dossier,
): T[] {
  const names = new Set(
    [dossier.name, dossier.display_name, dossier.jurisdiction]
      .filter((n): n is string => Boolean(n))
      .map((n) => n.split(",")[0]!.trim()),
  );
  return items.filter((i) => names.has(i.jurisdiction));
}
