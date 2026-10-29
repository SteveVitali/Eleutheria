// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4) — `<sig-details>`: progressive enhancement around a
 * server-rendered `<details>` disclosure.
 *
 * The native element already works without JS — this adds the two upgrades
 * the chrome needs: (a) a fragment that names the disclosure (or any id
 * inside it) opens it, so a shared `#cite-details` link lands expanded;
 * (b) a closed disclosure opens for print and restores afterwards, so the
 * cited-fact affordance never prints as a stub.
 *
 * Failure rule (K0): if this module never runs the markup is unchanged —
 * the `<details>` is already complete.
 */

class SigDetails extends HTMLElement {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const details = this.querySelector("details");
    if (details === null) return;

    const openForHash = () => {
      const hash = window.location.hash;
      if (hash.length < 2) return;
      let id = "";
      try {
        id = decodeURIComponent(hash.slice(1));
      } catch {
        return;
      }
      if (id === "") return;
      if (details.id === id || details.querySelector(`[id="${CSS.escape(id)}"]`) !== null) {
        details.open = true;
      }
    };
    openForHash();
    window.addEventListener("hashchange", openForHash);

    let openedForPrint = false;
    window.addEventListener("beforeprint", () => {
      openedForPrint = !details.open;
      if (openedForPrint) details.open = true;
    });
    window.addEventListener("afterprint", () => {
      if (openedForPrint) {
        details.open = false;
        openedForPrint = false;
      }
    });
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-details")) {
  customElements.define("sig-details", SigDetails);
}
