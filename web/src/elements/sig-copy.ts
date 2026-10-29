// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4) — `<sig-copy>`: a one-action "copy this" affordance over
 * server-rendered content.
 *
 * The element wraps the thing worth copying — an anchor, a code line, a
 * sentence — and adds a JS-only button plus a live status. What it copies:
 * the `value` attribute when set, else the first descendant `a[href]`'s
 * resolved URL, else the element's own trimmed text. The source content is
 * never altered; the button and status are `[data-enhancement]` so the
 * no-JS parity sweep (SIG-UI-091) excludes them.
 */

class SigCopy extends HTMLElement {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;

    const explicit = this.getAttribute("value");
    const anchor = this.querySelector<HTMLAnchorElement>("a[href]");
    const value =
      explicit !== null
        ? explicit
        : anchor !== null
          ? anchor.href
          : (this.textContent ?? "").trim();
    if (value === "") return;

    const label = this.getAttribute("label") ?? "Copy";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sig-kit-copy";
    button.dataset.enhancement = "";
    button.textContent = label;
    const status = document.createElement("span");
    status.className = "sig-kit-status";
    status.setAttribute("role", "status");
    status.dataset.enhancement = "";

    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(value);
        status.textContent = "Copied.";
      } catch {
        // An unavailable clipboard API degrades honestly: the source text is
        // still on the page to select, and the status says so.
        status.textContent = "Copy failed — select the text manually.";
      }
    });

    // No stray text nodes beside the chrome — a bare " " here would sit
    // OUTSIDE the [data-enhancement] elements and change the page's text,
    // breaking SIG-UI-091 parity. Spacing is the stylesheet's job.
    this.append(button, status);
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-copy")) {
  customElements.define("sig-copy", SigCopy);
}
