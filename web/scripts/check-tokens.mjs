// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.16 (R11-K13-UXK14-1, SIG-UI-146 / SIG-UI-156): the design-token gate,
 * wired into `npm run check` as `check:tokens` AFTER `build`.
 *
 * THE STYLELINT-EQUIVALENT ALLOW-LIST (SIG-UI-146, K14 §4 "single source"):
 * every declaration in `src/styles/*.css` (except the defining file
 * `tokens.css`) must take its colour, font size, space, radius and motion
 * values from `var(--sig-*)` tokens. Component styles carry no literals for
 * those channels — a `hsl()` that bypasses the palette, a `0.85rem` font that
 * bypasses the 8-step scale, a `0.35rem` gap that bypasses the space ramp or
 * a `3px` radius that bypasses the shape set is a build failure, not a style
 * opinion. The allowed literals per channel are enumerated below and are the
 * WHOLE list:
 *
 *   - colour properties: only `var(--sig-*)`, `color-mix(in srgb, var(--sig-*)
 *     …|transparent)`, `transparent`, `currentColor`, `inherit`, `none`. No
 *     hex/rgb/hsl/named colours anywhere outside tokens.css.
 *   - font-size: only `var(--sig-step-*)`, `inherit`, em or % relatives.
 *   - font-family / font shorthand: only `var(--sig-font-*)` / `inherit`.
 *   - line-height: only `var(--sig-leading-*)`, `inherit`, `normal`, unitless.
 *   - space (margin, padding, gap, inset, top/right/bottom/left, scroll-*):
 *     only `0`, `auto`, `var(--sig-*)`, `±1px` (the visually-hidden trick) and
 *     physical print units inside @page (cm/mm/in/pt/pc/q).
 *   - radius: only `var(--sig-radius-*)`, `0`, a % (the 50% range-point dot).
 *   - border widths / border shorthands: `0`/`none` or `var(--sig-border-*)` —
 *     K14's 1 px / 2 px emphasis pair. `outline`/`outline-offset` are exempt:
 *     the 3 px focus ring is a spec'd constant, not a rhythm value.
 *   - motion (transition*, animation*): durations come only from
 *     `var(--sig-motion-*)` (or a literal `0ms`/`0s`); no hard-coded timings.
 *   - box/text-shadow: `none` or a token.
 *   - Sizing (width, height, min- and max- variants, flex, grid tracks) is NOT
 *     token-bound —
 *     K14 tokens govern colour/size/space/radius, containers govern width.
 *
 * THE BUDGET LEG (SIG-UI-156, K0 §4.3): the font file ships ≤ 30 KiB and the
 * built design-system CSS — every dist css file that carries `--sig-`
 * custom properties — ships ≤ 12 KiB gzip each. Measured on build output,
 * never source, so the number is the wire number.
 *
 * Usage: node scripts/check-tokens.mjs [--dist DIR]
 * Exit: 0 pass · 1 failure · 2 usage · 3 vacuous (nothing measured —
 * SIG-ENG-042, never a silent green).
 */

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const STYLES_DIR = join(WEB, "src", "styles");
const FONTS_DIR = join(WEB, "src", "assets", "fonts");
const DEFINING_FILE = "tokens.css";

const CSS_BUDGET_BYTES = 12 * 1024; // SIG-UI-156: ≤ 12 KiB gzip
const FONT_BUDGET_BYTES = 30 * 1024; // SIG-UI-156: ≤ 30 KiB on the wire

/* --- The allow-lists -------------------------------------------------------- */

const COLOR_KEYWORDS = new Set([
  "transparent",
  "currentcolor",
  "inherit",
  "none",
  "initial",
  "unset",
  "revert",
]);
/** Named colours that must never appear in a colour-accepting property. */
const NAMED_COLOR_RE =
  /\b(red|blue|green|black|white|gr[ae]y|orange|yellow|purple|pink|brown|cyan|magenta|violet|teal|navy|silver|gold|maroon|olive|lime|aqua|fuchsia|crimson|indigo|salmon|khaki|plum|orchid|tomato|turquoise|slateblue|steelblue|royalblue|skyblue|seagreen|forestgreen|darkgreen|lightgreen|deeppink|hotpink|coral|beige|ivory|lavender|peachpuff|peru|tan|wheat|thistle|snow|linen|azure|mintcream|honeydew|gainsboro|whitesmoke|dimgray|dimgrey|darkslategray|darkslategrey|lightslategray|lightslategrey|slategray|slategrey|rebeccapurple)\b/i;
const COLOR_LITERAL_RE =
  /#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color)\s*\(/i;

const COLOR_PROPS = new Set([
  "color",
  "background",
  "background-color",
  "border",
  "border-top",
  "border-right",
  "border-bottom",
  "border-left",
  "border-color",
  "border-top-color",
  "border-right-color",
  "border-bottom-color",
  "border-left-color",
  "fill",
  "stroke",
  "caret-color",
  "text-decoration",
  "text-decoration-color",
  "column-rule",
  "column-rule-color",
  "accent-color",
]);
const SPACE_PROPS = new Set([
  "margin",
  "margin-top",
  "margin-right",
  "margin-bottom",
  "margin-left",
  "margin-block",
  "margin-block-start",
  "margin-block-end",
  "margin-inline",
  "margin-inline-start",
  "margin-inline-end",
  "padding",
  "padding-top",
  "padding-right",
  "padding-bottom",
  "padding-left",
  "padding-block",
  "padding-block-start",
  "padding-block-end",
  "padding-inline",
  "padding-inline-start",
  "padding-inline-end",
  "gap",
  "row-gap",
  "column-gap",
  "inset",
  "inset-block",
  "inset-block-start",
  "inset-block-end",
  "inset-inline",
  "inset-inline-start",
  "inset-inline-end",
  "top",
  "right",
  "bottom",
  "left",
  "scroll-margin",
  "scroll-margin-top",
  "scroll-margin-bottom",
  "scroll-padding",
]);
const RADIUS_PROPS = new Set([
  "border-radius",
  "border-top-left-radius",
  "border-top-right-radius",
  "border-bottom-left-radius",
  "border-bottom-right-radius",
  "border-start-start-radius",
  "border-start-end-radius",
  "border-end-start-radius",
  "border-end-end-radius",
]);
const BORDER_PROPS = new Set([
  "border",
  "border-top",
  "border-right",
  "border-bottom",
  "border-left",
  "border-width",
  "border-top-width",
  "border-right-width",
  "border-bottom-width",
  "border-left-width",
  "border-block",
  "border-inline",
  "border-block-start",
  "border-block-end",
  "border-inline-start",
  "border-inline-end",
]);
const MOTION_PROPS = new Set([
  "transition",
  "transition-duration",
  "transition-delay",
  "animation",
  "animation-duration",
  "animation-delay",
]);
const SHADOW_PROPS = new Set(["box-shadow", "text-shadow"]);

/* --- Value validators ------------------------------------------------------- */

const VAR_TOKEN_RE = /var\(--sig-[\w-]+(?:\s*,[^)]*)?\)/;
const VAR_ONLY_RE = /^var\(--sig-[\w-]+(?:\s*,[^)]*)?\)$/;
const COLOR_MIX_RE =
  /^color-mix\(\s*in\s+(?:srgb|oklch|hsl)\s*,\s*(?:var\(--sig-[\w-]+\)|transparent|currentColor)(?:\s+[\d.]+%)?\s*,\s*(?:var\(--sig-[\w-]+\)|transparent|currentColor)(?:\s+[\d.]+%)?\s*\)$/i;

function isSpacePart(part) {
  if (part === "0" || part === "auto") return true;
  if (VAR_ONLY_RE.test(part)) return true;
  if (/^-?\d*\.?\d+%$/.test(part)) return true; // layout-relative position (top: 50%), not rhythm
  if (part === "-9999px") return true; // the off-screen skip-link position
  if (/^-?\d*\.?\d+px$/.test(part) && Math.abs(parseFloat(part)) <= 1) return true; // the 1px hidden-clip trick
  if (/^\d+(\.\d+)?(cm|mm|in|pt|pc|q)$/i.test(part)) return true; // physical print units (@page)
  if (/^calc\(/.test(part)) {
    const inner = part.replace(/var\(--sig-[\w-]+\)/g, "");
    if (!/\d(px|rem|em|vh|vw|%)/.test(inner.replace(/[\d.]+/g, ""))) {
      // calc may only combine tokens with unitless arithmetic
      return !/[-+]?\d*\.?\d+(px|rem|em|vh|vw|%|cm|mm|in|pt|pc|q|deg|ms|s|ch|ex)/.test(inner);
    }
    return false;
  }
  return false;
}

/** Splits a declaration value into top-level parts (spaces not inside parens). */
function topLevelParts(value) {
  const parts = [];
  let depth = 0;
  let cur = "";
  for (const ch of value) {
    if (ch === "(") depth++;
    if (ch === ")") depth--;
    if (/\s/.test(ch) && depth === 0) {
      if (cur) parts.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  if (cur) parts.push(cur);
  return parts;
}

/** Strip comments and @charset/@import lines; return the body text. */
function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, " ");
}

/**
 * Naive declaration scan — sufficient for our hand-maintained, well-formed
 * styles (no strings containing braces/semicolons are used in these files).
 * Yields { prop, value, line } for every `prop: value;` inside rules.
 */
function* declarations(css, file) {
  const body = stripComments(css);
  let line = 1;
  let i = 0;
  const n = body.length;
  let depth = 0;
  let declStart = -1;
  while (i < n) {
    const ch = body[i];
    if (ch === "\n") line++;
    if (ch === "{") {
      depth++;
      i++;
      declStart = i;
      continue;
    }
    if (ch === "}") {
      depth--;
      i++;
      declStart = i;
      continue;
    }
    if (depth > 0) {
      if (ch === ";" || ch === "{") {
        const seg = body.slice(declStart, i).trim();
        const m = /^(--[\w-]+|[a-zA-Z-]+)\s*:\s*(.+)$/s.exec(seg);
        if (m) {
          // line of the declaration start
          const startOffset = declStart + (body.slice(declStart, i).length - body.slice(declStart, i).trimStart().length);
          const declLine = line - (body.slice(startOffset, i).match(/\n/g) || []).length;
          yield { prop: m[1].toLowerCase(), value: m[2].trim(), line: declLine, file };
        }
        declStart = i + 1;
      }
    } else {
      declStart = i;
    }
    i++;
  }
}

/* --- The checks ------------------------------------------------------------- */

const failures = [];
const notes = [];

function fail(file, line, msg) {
  failures.push(`${relative(WEB, file)}:${line}: ${msg}`);
}

function checkDeclaration({ file, line, prop, value }) {
  if (prop.startsWith("--")) return; // custom property aliases are values-typed by tokens.css
  if (COLOR_LITERAL_RE.test(value)) {
    fail(file, line, `colour literal in '${prop}: ${value}' — colours live in tokens.css only`);
    return;
  }
  if (COLOR_PROPS.has(prop)) {
    let rest = value;
    rest = rest.replace(/var\(--sig-[\w-]+\)/g, " ");
    rest = rest.replace(
      /color-mix\([^)]*\)/gi,
      " ",
    );
    for (const w of rest.split(/[\s,]+/).filter(Boolean)) {
      const wl = w.toLowerCase();
      if (COLOR_KEYWORDS.has(wl)) continue;
      if (
        prop.startsWith("border") &&
        /^(none|solid|dashed|dotted|double|groove|ridge|inset|outset|hidden)$/i.test(wl)
      )
        continue;
      if (prop === "text-decoration" && /^(underline|none|dotted|dashed|solid|wavy|double|line-through|overline|skip-ink)$/i.test(wl))
        continue;
      if (prop === "background" && /^(repeat|no-repeat|repeat-x|repeat-y|fixed|scroll|local|cover|contain|center|top|bottom|left|right|padding-box|border-box|content-box)$/i.test(wl))
        continue;
      if (NAMED_COLOR_RE.test(wl)) {
        fail(file, line, `named colour '${w}' in '${prop}: ${value}' — use a token`);
      }
      // any length literal in a colour prop's border shorthand part is caught by BORDER_PROPS below
    }
  }
  if (prop === "font-size") {
    if (!/^(var\(--sig-step-[\w-]+\)|inherit|larger|smaller|medium|\d*\.?\d+(em|rem|%))$/.test(value)) {
      fail(file, line, `font-size '${value}' — use a var(--sig-step-*) (em/% relatives allowed)`);
    } else if (/rem$/.test(value)) {
      fail(file, line, `font-size rem literal '${value}' — use a var(--sig-step-*)`);
    }
  }
  if (prop === "font-family" || prop === "font") {
    if (!/^(var\(--sig-[\w-]+\)|inherit)$/.test(value)) {
      fail(file, line, `'${prop}: ${value}' — use var(--sig-font-*) or inherit`);
    }
  }
  if (prop === "line-height") {
    if (!/^(var\(--sig-leading-\d\)|inherit|normal|\d*\.?\d+)$/.test(value)) {
      fail(file, line, `line-height '${value}' — use var(--sig-leading-*) or a unitless ratio`);
    }
  }
  if (SPACE_PROPS.has(prop)) {
    for (const part of topLevelParts(value)) {
      if (!isSpacePart(part)) {
        fail(file, line, `space literal '${part}' in '${prop}: ${value}' — use var(--sig-space-*)`);
      }
    }
  }
  if (RADIUS_PROPS.has(prop)) {
    for (const part of topLevelParts(value)) {
      if (!/^(var\(--sig-[\w-]+\)|0|50%|\d*\.?\d+%)$/.test(part)) {
        fail(file, line, `radius literal '${part}' in '${prop}: ${value}' — use var(--sig-radius-*)`);
      }
    }
  }
  if (BORDER_PROPS.has(prop)) {
    if (/\d*\.?\d+(px|rem|em|vh|vw|ch)/.test(value.replace(/var\(--sig-[\w-]+\)/g, ""))) {
      fail(file, line, `border width literal in '${prop}: ${value}' — use var(--sig-border-*)`);
    }
    const colorPart = value.replace(/var\(--sig-[\w-]+\)/g, "").replace(/\b(none|solid|dashed|dotted|double|groove|ridge|inset|outset|hidden|0)\b/gi, "");
    if (NAMED_COLOR_RE.test(colorPart)) {
      fail(file, line, `named colour in '${prop}: ${value}' — use a token`);
    }
  }
  if (MOTION_PROPS.has(prop)) {
    const withoutVars = value.replace(/var\(--sig-[\w-]+\)/g, "");
    if (/-?\d*\.?\d+(ms|s)\b/.test(withoutVars.replace(/\b0(ms|s)\b/g, ""))) {
      fail(file, line, `motion literal in '${prop}: ${value}' — use var(--sig-motion-*)`);
    }
  }
  if (SHADOW_PROPS.has(prop)) {
    const rest = value.replace(/var\(--sig-[\w-]+\)/g, "").trim();
    if (!/^(none|inherit)$/i.test(rest)) {
      fail(file, line, `shadow literal in '${prop}: ${value}' — shadows are 'none' or a token`);
    }
  }
}

/* --- Driver ----------------------------------------------------------------- */

function main() {
  const args = process.argv.slice(2);
  let dist = join(WEB, "dist");
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--dist") {
      dist = args[++i];
    } else {
      console.error(`check-tokens: unknown arg ${args[i]}`);
      process.exit(2);
    }
  }

  // Leg 1 — the source allow-list over src/styles/*.css except tokens.css.
  if (!existsSync(STYLES_DIR)) {
    console.error("check-tokens: src/styles/ missing — vacuous");
    process.exit(3);
  }
  const cssFiles = readdirSync(STYLES_DIR)
    .filter((f) => f.endsWith(".css") && f !== DEFINING_FILE)
    .map((f) => join(STYLES_DIR, f));
  if (cssFiles.length === 0) {
    console.error("check-tokens: no component styles found — vacuous");
    process.exit(3);
  }
  let declCount = 0;
  for (const file of cssFiles) {
    const css = readFileSync(file, "utf8");
    for (const decl of declarations(css, file)) {
      declCount++;
      checkDeclaration(decl);
    }
  }
  notes.push(`allow-list: ${declCount} declarations scanned in ${cssFiles.length} files`);

  // tokens.css itself: the font must be self-hosted + optional-display.
  const tokensCss = readFileSync(join(STYLES_DIR, DEFINING_FILE), "utf8");
  if (!/@font-face[\s\S]*?font-display:\s*optional/.test(tokensCss)) {
    fail(join(STYLES_DIR, DEFINING_FILE), 1, "@font-face must declare font-display: optional (K14)");
  }
  if (!/src:\s*url\("\.\.\/assets\/fonts\//.test(tokensCss)) {
    fail(join(STYLES_DIR, DEFINING_FILE), 1, "the Public Sans @font-face must be self-hosted (../assets/fonts/)");
  }

  // Leg 2 — the font budget (SIG-UI-156).
  const fontFiles = existsSync(FONTS_DIR)
    ? readdirSync(FONTS_DIR).filter((f) => f.endsWith(".woff2"))
    : [];
  if (fontFiles.length === 0) {
    console.error("check-tokens: no self-hosted woff2 under src/assets/fonts/ — vacuous");
    process.exit(3);
  }
  for (const f of fontFiles) {
    const size = statSync(join(FONTS_DIR, f)).size;
    notes.push(`font ${f}: ${size} B (${(size / 1024).toFixed(1)} KiB)`);
    if (size > FONT_BUDGET_BYTES) {
      fail(join(FONTS_DIR, f), 0, `font ${f} is ${size} B > ${FONT_BUDGET_BYTES} B (30 KiB)`);
    }
  }
  // The OFL-1.1 licence must ship beside the vendored font.
  if (!existsSync(join(FONTS_DIR, "OFL.txt"))) {
    fail(join(FONTS_DIR, "OFL.txt"), 0, "OFL.txt missing — the licence ships beside the font");
  }

  // Leg 3 — the built design-system CSS budget (gzip, wire-measured).
  if (!existsSync(dist)) {
    console.error(`check-tokens: ${relative(WEB, dist)} missing — run after \`npm run build\``);
    process.exit(3);
  }
  const builtCss = [];
  (function walk(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, entry.name);
      if (entry.isDirectory()) walk(p);
      else if (entry.name.endsWith(".css")) builtCss.push(p);
    }
  })(dist);
  const designCss = builtCss.filter((p) => readFileSync(p, "utf8").includes("--sig-"));
  if (designCss.length === 0) {
    console.error("check-tokens: no built css carries --sig-* tokens — vacuous");
    process.exit(3);
  }
  for (const p of designCss) {
    const gz = gzipSync(readFileSync(p)).length;
    notes.push(`css ${relative(WEB, p)}: ${gz} B gzip (${(gz / 1024).toFixed(2)} KiB)`);
    if (gz > CSS_BUDGET_BYTES) {
      fail(p, 0, `built css ${relative(dist, p)} is ${gz} B gzip > ${CSS_BUDGET_BYTES} B (12 KiB)`);
    }
  }

  for (const n of notes) console.log(`check-tokens: ${n}`);
  if (failures.length) {
    for (const f of failures) console.error(`FAIL ${f}`);
    console.error(`check-tokens: ${failures.length} failure(s)`);
    process.exit(1);
  }
  console.log("check-tokens: OK");
}

main();
