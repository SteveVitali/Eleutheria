// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4) — `<sig-cite>`: format restatement for the page citation.
 *
 * The server-rendered block already carries the verbatim J3 §8.2 sentence
 * and the reporting-register citation; the element adds a JS-only toolbar —
 * a format picker (plain / APA / Chicago / legal) with the restated text
 * and a copy action. Everything renders from `data-cite-*` fields the block
 * declares plus its own rendered text; a missing module leaves the
 * paragraph-form citation complete. All injected chrome is
 * `[data-enhancement]` — the SIG-UI-091 parity sweep never sees it.
 */
import { CITE_FORMATS, formatCite, type CiteFields, type CiteFormat } from "./cite-formats";

class SigCite extends HTMLElement {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const d = this.dataset;
    const plain =
      this.querySelector(".sig-cite__text")?.textContent?.trim() ??
      this.querySelector(".sig-cite__sentence")?.textContent?.trim() ??
      "";
    if (plain === "") return;
    const fields: CiteFields = {
      title: d.citeTitle ?? "",
      release: d.citeRelease ?? "",
      asOfWorld: d.citeAsofWorld ?? "",
      asOfBelief: d.citeAsofBelief ?? "",
      ruleset: d.citeRuleset ?? "",
      url: d.citeUrl ?? "",
      plain,
    };

    const bar = document.createElement("p");
    bar.className = "sig-kit-bar";
    bar.dataset.enhancement = "";

    const label = document.createElement("label");
    label.className = "sig-kit-field";
    label.textContent = "Format ";
    const select = document.createElement("select");
    for (const f of CITE_FORMATS) {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = f.label;
      select.appendChild(opt);
    }
    label.appendChild(select);

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "sig-kit-copy";
    copy.textContent = "Copy citation";

    const status = document.createElement("span");
    status.className = "sig-kit-status";
    status.setAttribute("role", "status");

    bar.append(label, " ", copy, " ", status);
    this.appendChild(bar);

    const out = document.createElement("p");
    out.className = "sig-cite__formatted";
    out.dataset.enhancement = "";
    out.textContent = formatCite(fields, "plain");
    this.appendChild(out);

    select.addEventListener("change", () => {
      out.textContent = formatCite(fields, select.value as CiteFormat);
    });
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(out.textContent ?? "");
        status.textContent = "Copied.";
      } catch {
        status.textContent = "Copy failed — select the text manually.";
      }
    });
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-cite")) {
  customElements.define("sig-cite", SigCite);
}
