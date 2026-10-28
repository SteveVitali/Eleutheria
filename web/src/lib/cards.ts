// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.22 (K14 UXK14-3a / §4.6 card row; K4, K11): the card-family data contract
 * (`sig.card/1`) — ONE spec shape the six kit cards render from: `place`,
 * `organization`, `source`, `task`, `persona` ("start here") and `example`.
 *
 * A card is a linked summary — a kind line, a titled link, an optional figure
 * (always the `<Figure>` contract, SIG-UI-084), optional meta lines, optional
 * chips — or an honestly EMPTY card, which renders the five-part
 * `EmptyState` for a named surface instead of a fabricated zero. The states
 * "with a figure" and "empty" are both named in K14's card row.
 *
 * Per-kind contract (the kicker line names what kind of thing the card is):
 *   - `place`        — kicker: the jurisdiction code; meta: record counts.
 *   - `organization` — kicker: the org kind; meta: recorded relationships.
 *   - `source`       — kicker: the publisher; badges: licence / access / mirror.
 *   - `task`         — kicker: the task kind + place; meta: the closing state.
 *   - `persona`      — kicker: the persona; steps: 3–4 linked start-here steps.
 *   - `example`      — kicker: "Example question"; meta: the question + where
 *     the answer lives.
 *
 * Pure data + logic (no markup, no colour): `assertCard` validates a spec at
 * build time — a malformed card fails the build, never renders a half-card
 * (SIG-ENG-042). `Card.astro` renders it.
 */

import type { EmptySurface } from "./empty";
import type { FigureSpec } from "./figures";

/** The six card kinds (`data-card-kind` on the component). */
export const CARD_KINDS = [
  "place",
  "organization",
  "source",
  "task",
  "persona",
  "example",
] as const;
export type CardKind = (typeof CARD_KINDS)[number];

/** One meta line — a labelled fact, never free prose. */
export interface CardMeta {
  label: string;
  value: string;
  /** Optional link the value renders to. */
  href?: string;
}

/** One linked step on a persona "start here" card (3–4 steps). */
export interface CardStep {
  label: string;
  href: string;
}

/** One badge/chip slot rendered on the card's chip row. */
export interface CardBadge {
  kind: "directness" | "access_kind" | "licence" | "mirror";
  value: string;
}

/**
 * The status-chip vocabulary (K14 §4.6 status row) — the lifecycle states a
 * status chip may carry. Shared by `StatusChip.astro`, this contract and the
 * harness so the three can never drift apart.
 */
export const STATUS_CHIP_KINDS = [
  "provisional",
  "historical",
  "not_reviewed",
  "superseded",
  "withdrawn",
] as const;
export type StatusChipKind = (typeof STATUS_CHIP_KINDS)[number];

/** One status chip slot rendered on the card's chip row. */
export interface CardStatus {
  kind: StatusChipKind;
  /** For `historical`: the date the state began (e.g. "2024-03"). */
  since?: string;
}

/**
 * A card spec. `empty` names the `EmptySurface` the card's empty state renders
 * — when set, `title`/`titleHref`/content fields are unused (the card IS the
 * typed empty state, never a dead card).
 */
export interface CardSpec {
  kind: CardKind;
  /** The titled link text (a name — "Oklahoma City", "Flock Safety"). */
  title?: string;
  /** The card's destination route (a plain GET link, no JavaScript). */
  titleHref?: string;
  /** The kind line naming what the card is (jurisdiction code, org kind…). */
  kicker?: string;
  /** Labelled meta lines (record counts, relationship counts, question text). */
  meta?: CardMeta[];
  /** An optional figure — always the `<Figure>` contract when present. */
  figure?: FigureSpec;
  /** Neutral text badges (source cards: licence / access / mirror). */
  badges?: CardBadge[];
  /** Status chips (provisional, superseded…). */
  statuses?: CardStatus[];
  /** Persona cards: the linked start-here steps (3–4, K14 §6.1). */
  steps?: CardStep[];
  /** The named empty surface — renders `EmptyState`, nothing else. */
  empty?: EmptySurface;
}

const ID_RE = /^\/|^#|^https?:\/\//;

/** Validate a card spec — every failure is a build error, never a warn. */
export function assertCard(card: CardSpec, where: string): void {
  if (!(CARD_KINDS as readonly string[]).includes(card.kind)) {
    throw new Error(`sig.card/1 ${where}: unknown kind "${card.kind}"`);
  }
  if (card.empty !== undefined) {
    // An empty card carries its surface and nothing else — a dead card with a
    // title would read as a thing that exists.
    if (card.title !== undefined || card.titleHref !== undefined) {
      throw new Error(
        `sig.card/1 ${where}: an empty (${card.empty}) card carries no title/link`,
      );
    }
    return;
  }
  if (card.title === undefined || card.title.trim() === "") {
    throw new Error(`sig.card/1 ${where}: a non-empty card names no title`);
  }
  if (card.titleHref === undefined || !ID_RE.test(card.titleHref)) {
    throw new Error(
      `sig.card/1 ${where}: "${card.title}" carries no resolvable link — a card is a doorway, not a dead end`,
    );
  }
  if (card.kind === "persona") {
    const n = card.steps?.length ?? 0;
    if (n < 3 || n > 4) {
      throw new Error(
        `sig.card/1 ${where}: a persona card carries 3–4 linked steps (K14 §6.1), got ${n}`,
      );
    }
  }
  if (card.kind === "example") {
    const question = card.meta?.find((m) => m.label === "Question");
    if (question === undefined || question.value.trim() === "") {
      throw new Error(
        `sig.card/1 ${where}: an example card names its question in meta (K14 §6.2)`,
      );
    }
  }
  for (const m of card.meta ?? []) {
    if (m.label.trim() === "" || m.value.trim() === "") {
      throw new Error(`sig.card/1 ${where}: a meta line lacks a label or a value`);
    }
  }
  for (const s of card.steps ?? []) {
    if (s.label.trim() === "" || !ID_RE.test(s.href)) {
      throw new Error(`sig.card/1 ${where}: a step lacks a label or a resolvable link`);
    }
  }
  for (const b of card.badges ?? []) {
    if (!["directness", "access_kind", "licence", "mirror"].includes(b.kind)) {
      throw new Error(`sig.card/1 ${where}: unknown badge kind "${b.kind}"`);
    }
    if (b.value.trim() === "") {
      throw new Error(`sig.card/1 ${where}: a ${b.kind} badge carries no value`);
    }
  }
}

/** Build + validate a card spec (the one call pages make). */
export function defineCard(card: CardSpec, where: string): CardSpec {
  assertCard(card, where);
  return card;
}
