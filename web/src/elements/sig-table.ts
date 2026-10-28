// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4 / K9's table posture / SIG-UI-091) — `<sig-table>`:
 * progressive enhancement over a complete server-rendered table.
 *
 * The server HTML is the canonical no-JS view — every row rendered, every
 * fact present. The element adds an opt-in toolbar (all `[data-enhancement]`
 * so the parity sweep never counts it): text filtering, multi-facet chips,
 * a column chooser, "Download this view" (CSV whose provenance lines restate
 * the licences the visible rows are filed under), and column sorting with
 * `aria-sort`. Filtering hides rows with `hidden` — it never removes DOM —
 * and the view state round-trips through URL parameters so a view is
 * shareable. A module that never loads leaves the markup untouched.
 */
import {
  facetValues,
  paramsToState,
  stateToParams,
  toCsv,
  visibleRowOrder,
  type TableModel,
  type TableRowModel,
  type TableState,
} from "./table-model";

const CONTROLLED_PARAMS = ["q", "sort", "dir", "cols"];

class SigTable extends HTMLElement {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const table = this.querySelector("table");
    if (table === null || table.tBodies.length === 0) return;

    const headCells = [...table.querySelectorAll<HTMLTableCellElement>("thead th")];
    const rowEls = [...table.tBodies[0].querySelectorAll<HTMLTableRowElement>("tr")];
    const model: TableModel = {
      columns: headCells.map((th, index) => ({
        index,
        id: th.getAttribute("data-col") ?? `c${index}`,
        label: (th.textContent ?? "").trim(),
      })),
      rows: rowEls.map((tr): TableRowModel => {
        const facets: Record<string, string[]> = {};
        for (const attr of tr.getAttributeNames()) {
          if (!attr.startsWith("data-facet-")) continue;
          const dim = attr.slice("data-facet-".length);
          facets[dim] = (tr.getAttribute(attr) ?? "")
            .split("|")
            .map((v) => v.trim())
            .filter((v) => v !== "");
        }
        const licences = (tr.getAttribute("data-licence") ?? "")
          .split("|")
          .map((v) => v.trim())
          .filter((v) => v !== "");
        const compartment = tr.getAttribute("data-compartment") ?? undefined;
        return {
          cells: [...tr.cells].map((td) => (td.textContent ?? "").trim()),
          facets,
          licences,
          ...(compartment !== undefined ? { compartment } : {}),
        };
      }),
    };

    const facetDims = (this.getAttribute("facets") ?? "")
      .split(/\s+/)
      .filter((d) => d !== "");
    const state: TableState = paramsToState(
      window.location.search,
      model,
      facetDims,
    );
    for (const dim of facetDims) state.facets[dim] ??= [];

    // --- toolbar -------------------------------------------------------------
    const bar = document.createElement("div");
    bar.className = "sig-kit-bar";
    bar.dataset.enhancement = "";

    const status = document.createElement("span");
    status.className = "sig-kit-status";
    status.setAttribute("role", "status");

    const syncUrl = () => {
      const url = new URL(window.location.href);
      for (const key of [...CONTROLLED_PARAMS, ...facetDims]) {
        url.searchParams.delete(key);
      }
      const p = stateToParams(state);
      p.forEach((v, k) => url.searchParams.set(k, v));
      window.history.replaceState(null, "", url);
    };

    const apply = () => {
      const order = visibleRowOrder(model, state);
      const visible = new Set(order);
      const tbody = table.tBodies[0];
      // Physical order follows the sort; hidden rows move too so relative
      // order stays honest when they re-appear.
      for (const i of order) tbody.appendChild(rowEls[i]);
      rowEls.forEach((tr, i) => {
        tr.hidden = !visible.has(i);
      });
      const hiddenCols = new Set(
        state.hidden
          .map((id) => model.columns.find((c) => c.id === id)?.index)
          .filter((i): i is number => i !== undefined),
      );
      headCells.forEach((th, i) => {
        th.hidden = hiddenCols.has(i);
      });
      rowEls.forEach((tr) => {
        [...tr.cells].forEach((td, i) => {
          td.hidden = hiddenCols.has(i);
        });
      });
      status.textContent = `Showing ${order.length} of ${model.rows.length} rows.`;
      syncUrl();
    };

    if (this.hasAttribute("filter")) {
      const label = document.createElement("label");
      label.className = "sig-kit-field";
      label.textContent = "Filter rows ";
      const input = document.createElement("input");
      input.type = "search";
      input.className = "sig-kit-filter";
      input.value = state.q;
      input.addEventListener("input", () => {
        state.q = input.value;
        apply();
      });
      label.appendChild(input);
      bar.append(label);
    }

    for (const dim of facetDims) {
      const values = facetValues(model.rows, dim);
      if (values.size === 0) continue;
      const menu = document.createElement("details");
      menu.className = "sig-kit-menu";
      const summary = document.createElement("summary");
      summary.textContent = `Filter by ${dim}`;
      menu.appendChild(summary);
      const list = document.createElement("div");
      list.className = "sig-kit-chips";
      for (const [value, count] of values) {
        const chip = document.createElement("label");
        chip.className = "sig-kit-chip";
        const box = document.createElement("input");
        box.type = "checkbox";
        box.checked = (state.facets[dim] ?? []).includes(value);
        box.addEventListener("change", () => {
          const set = new Set(state.facets[dim] ?? []);
          if (box.checked) set.add(value);
          else set.delete(value);
          state.facets[dim] = [...set];
          apply();
        });
        chip.append(box, ` ${value} (${count})`);
        list.appendChild(chip);
      }
      menu.appendChild(list);
      bar.append(" ", menu);
    }

    if (this.hasAttribute("columns") && model.columns.length > 1) {
      const menu = document.createElement("details");
      menu.className = "sig-kit-menu";
      const summary = document.createElement("summary");
      summary.textContent = "Columns";
      menu.appendChild(summary);
      const list = document.createElement("div");
      list.className = "sig-kit-chips";
      for (const col of model.columns) {
        const chip = document.createElement("label");
        chip.className = "sig-kit-chip";
        const box = document.createElement("input");
        box.type = "checkbox";
        box.checked = !state.hidden.includes(col.id);
        box.addEventListener("change", () => {
          if (!box.checked) {
            if (model.columns.length - state.hidden.length <= 1) {
              // Never hide the last visible column — a view with no facts is
              // not a view.
              box.checked = true;
              status.textContent = "At least one column must stay visible.";
              return;
            }
            state.hidden = [...state.hidden, col.id];
          } else {
            state.hidden = state.hidden.filter((id) => id !== col.id);
          }
          apply();
        });
        chip.append(box, ` ${col.label}`);
        list.appendChild(chip);
      }
      menu.appendChild(list);
      bar.append(" ", menu);
    }

    const download = this.getAttribute("download");
    if (download !== null) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sig-kit-download";
      button.textContent = "Download this view (CSV)";
      button.addEventListener("click", () => {
        const order = visibleRowOrder(model, state);
        const cols = model.columns
          .map((c) => c.id)
          .filter((id) => !state.hidden.includes(id));
        const labelText =
          this.getAttribute("label") ??
          table.getAttribute("aria-labelledby") ??
          "table view";
        const csv = toCsv(model, order, cols, labelText);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
        a.download = `${download}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
        status.textContent = `Downloaded ${order.length} rows.`;
      });
      bar.append(" ", button);
    }

    // --- sortable headers ------------------------------------------------------
    const marks: HTMLSpanElement[] = [];
    const paintSort = () => {
      headCells.forEach((th, i) => {
        const on = state.sort === model.columns[i].id;
        if (on) {
          th.setAttribute(
            "aria-sort",
            state.dir === "desc" ? "descending" : "ascending",
          );
        } else {
          th.removeAttribute("aria-sort");
        }
        marks[i].textContent = on ? (state.dir === "desc" ? "▼" : "▲") : "";
      });
    };
    headCells.forEach((th, i) => {
      const col = model.columns[i];
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sig-kit-sort";
      while (th.firstChild !== null) button.appendChild(th.firstChild);
      const mark = document.createElement("span");
      mark.className = "sig-kit-sort-mark";
      mark.dataset.enhancement = "";
      mark.setAttribute("aria-hidden", "true");
      marks[i] = mark;
      button.appendChild(mark);
      th.appendChild(button);
      button.addEventListener("click", () => {
        if (state.sort === col.id) {
          state.dir = state.dir === "asc" ? "desc" : "asc";
        } else {
          state.sort = col.id;
          state.dir = "asc";
        }
        paintSort();
        apply();
      });
    });
    paintSort();

    bar.append(" ", status);
    this.insertBefore(bar, table);
    apply();
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-table")) {
  customElements.define("sig-table", SigTable);
}
