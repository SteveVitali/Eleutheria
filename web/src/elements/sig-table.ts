// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4 / K9's table posture / SIG-UI-091) — `<sig-table>`:
 * progressive enhancement over a complete server-rendered table.
 * P37.61 (ENH-01 / C-19 rollout, ADR-249): the same element also upgrades
 * a server-rendered list (`ol`/`ul`) — the table's column controls become
 * declared `data-sort-<key>` values plus the item's full text.
 *
 * The server HTML is the canonical no-JS view — every row rendered, every
 * fact present. The element adds an opt-in toolbar (all `[data-enhancement]`
 * so the parity sweep never counts it): text filtering, multi-facet chips,
 * a column chooser (table mode), "Download this view" (CSV whose
 * provenance lines restate the licences the visible rows are filed
 * under), and sorting (`aria-sort` on header buttons; a toolbar "Sort by"
 * menu when headers already carry interactive sort links, or for lists —
 * the kit never nests a control inside an existing anchor). Filtering
 * hides rows with `hidden` — it never removes DOM — and the view state
 * round-trips through URL parameters so a view is shareable. When a page
 * mounts more than one `<sig-table>`, a `param-prefix` attribute
 * namespaces the controlled params (`src.q`, `iss.sort`, …) so the views
 * stay independent. A module that never loads leaves the markup
 * untouched.
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

/** `data-facet-*` / `data-licence` / `data-compartment` row attributes —
 *  identical for `tr` and `li` rows. */
function readRowAttrs(el: HTMLElement): Pick<
  TableRowModel,
  "facets" | "facetLabels" | "licences" | "compartment"
> {
  const facets: Record<string, string[]> = {};
  const facetLabels: Record<string, Record<string, string>> = {};
  for (const attr of el.getAttributeNames()) {
    if (attr.startsWith("data-facet-label-")) {
      const dim = attr.slice("data-facet-label-".length);
      const labels = (el.getAttribute(attr) ?? "").split("|");
      (facets[dim] ?? []).forEach((v, i) => {
        const label = labels[i]?.trim();
        if (label) (facetLabels[dim] ??= {})[v] = label;
      });
      continue;
    }
    if (!attr.startsWith("data-facet-")) continue;
    const dim = attr.slice("data-facet-".length);
    facets[dim] = (el.getAttribute(attr) ?? "")
      .split("|")
      .map((v) => v.trim())
      .filter((v) => v !== "");
  }
  const licences = (el.getAttribute("data-licence") ?? "")
    .split("|")
    .map((v) => v.trim())
    .filter((v) => v !== "");
  const compartment = el.getAttribute("data-compartment") ?? undefined;
  return {
    facets,
    licences,
    ...(Object.keys(facetLabels).length > 0 ? { facetLabels } : {}),
    ...(compartment !== undefined ? { compartment } : {}),
  };
}

/** Value → display label for a facet dimension across every row's
 *  `data-facet-label-<dim>` map (the row's own rendered vocabulary). */
function facetLabel(
  rows: TableRowModel[],
  dim: string,
  value: string,
): string {
  for (const row of rows) {
    const label = row.facetLabels?.[dim]?.[value];
    if (label) return label;
  }
  return value;
}

function labelize(key: string): string {
  const words = key.replace(/[-_]+/g, " ");
  return words.slice(0, 1).toUpperCase() + words.slice(1);
}

class SigTable extends HTMLElement {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const table = this.querySelector("table");

    // ------------------------------------------------------------------
    // Build the row model — table mode over `<tbody>`, or list mode over
    // every top-level `ol`/`ul` inside the element.
    // ------------------------------------------------------------------
    const headCells: HTMLTableCellElement[] = [];
    const rowEls: HTMLElement[] = [];
    const rowParents: HTMLElement[] = [];
    let model: TableModel;
    const sortKeys = (this.getAttribute("sort") ?? "")
      .split(/\s+/)
      .filter((k) => k !== "");
    const isList = table === null;

    if (table !== null) {
      if (table.tBodies.length === 0) return;
      headCells.push(
        ...table.querySelectorAll<HTMLTableCellElement>("thead th"),
      );
      const trs = [
        ...table.tBodies[0].querySelectorAll<HTMLTableRowElement>("tr"),
      ];
      model = {
        columns: headCells.map((th, index) => ({
          index,
          id: th.getAttribute("data-col") ?? `c${index}`,
          label: (th.textContent ?? "").trim(),
        })),
        rows: trs.map((tr): TableRowModel => {
          rowEls.push(tr);
          rowParents.push(table.tBodies[0]);
          return {
            cells: [...tr.cells].map((td) => (td.textContent ?? "").trim()),
            ...readRowAttrs(tr),
          };
        }),
      };
    } else {
      // List mode: `ol`/`ul` not nested inside another `ol`/`ul` of this
      // element (a `dl`/`ul` inside an `li` stays part of its item).
      const lists = [...this.querySelectorAll<HTMLElement>("ol,ul")].filter(
        (l) => {
          let p: HTMLElement | null = l.parentElement;
          while (p !== null && p !== this) {
            if (p.tagName === "OL" || p.tagName === "UL") return false;
            p = p.parentElement;
          }
          return true;
        },
      );
      if (lists.length === 0) return;
      const itemLabel = this.getAttribute("item-label") ?? "Item";
      model = {
        columns: [
          ...sortKeys.map((k, i) => ({
            index: i,
            id: k,
            label: labelize(k),
          })),
          { index: sortKeys.length, id: "item", label: itemLabel },
        ],
        rows: lists.flatMap((list): TableRowModel[] => {
          const items = [
            ...list.querySelectorAll<HTMLElement>(":scope > li"),
          ];
          return items.map((li) => {
            rowEls.push(li);
            rowParents.push(list);
            return {
              cells: [
                ...sortKeys.map(
                  (k) => li.getAttribute(`data-sort-${k}`) ?? "",
                ),
                (li.textContent ?? "").replace(/\s+/g, " ").trim(),
              ],
              ...readRowAttrs(li),
            };
          });
        }),
      };
    }
    const noun = isList ? "items" : "rows";

    const facetDims = (this.getAttribute("facets") ?? "")
      .split(/\s+/)
      .filter((d) => d !== "");
    const prefix = this.getAttribute("param-prefix") ?? "";
    const unprefixed = (): string => {
      const out = new URLSearchParams();
      new URLSearchParams(window.location.search).forEach((v, k) => {
        if (prefix === "" ? true : k.startsWith(prefix)) {
          out.set(prefix === "" ? k : k.slice(prefix.length), v);
        }
      });
      return out.toString();
    };
    const state: TableState = paramsToState(unprefixed(), model, facetDims);
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
        url.searchParams.delete(prefix + key);
      }
      stateToParams(state).forEach((v, k) =>
        url.searchParams.set(prefix + k, v),
      );
      window.history.replaceState(null, "", url);
    };

    const apply = () => {
      const order = visibleRowOrder(model, state);
      const visible = new Set(order);
      // Physical order follows the sort; hidden rows move too so relative
      // order stays honest when they re-appear. Each row re-appends to its
      // own parent — list mode can cover several sibling lists.
      for (const i of order) rowParents[i].appendChild(rowEls[i]);
      rowEls.forEach((el, i) => {
        el.hidden = !visible.has(i);
      });
      if (table !== null) {
        const hiddenCols = new Set(
          state.hidden
            .map((id) => model.columns.find((c) => c.id === id)?.index)
            .filter((i): i is number => i !== undefined),
        );
        headCells.forEach((th, i) => {
          th.hidden = hiddenCols.has(i);
        });
        rowEls.forEach((el) => {
          [...(el as HTMLTableRowElement).cells].forEach((td, i) => {
            td.hidden = hiddenCols.has(i);
          });
        });
      }
      status.textContent = `Showing ${order.length} of ${model.rows.length} ${noun}.`;
      syncUrl();
    };

    if (this.hasAttribute("filter")) {
      const label = document.createElement("label");
      label.className = "sig-kit-field";
      label.textContent = `Filter ${noun} `;
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
        chip.append(box, ` ${facetLabel(model.rows, dim, value)} (${count})`);
        list.appendChild(chip);
      }
      menu.appendChild(list);
      bar.append(" ", menu);
    }

    if (
      table !== null &&
      this.hasAttribute("columns") &&
      model.columns.length > 1
    ) {
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
          table?.getAttribute("aria-labelledby") ??
          "view";
        const csv = toCsv(model, order, cols, labelText);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
        a.download = `${download}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
        status.textContent = `Downloaded ${order.length} ${noun}.`;
      });
      bar.append(" ", button);
    }

    // --- sorting ---------------------------------------------------------------
    // Two presentations share one state toggle: `th` header buttons when the
    // header cells are inert, or a toolbar "Sort by" menu when the header
    // cells already carry interactive sort links (a control never nests
    // inside an anchor) or the rows are list items.
    const marks = new Map<string, HTMLSpanElement>();
    const paintSort = () => {
      for (const [id, mark] of marks) {
        const on = state.sort === id;
        mark.textContent = on ? (state.dir === "desc" ? "▼" : "▲") : "";
      }
      if (state.sort !== null) {
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
        });
      }
    };
    const setSort = (id: string) => {
      if (state.sort === id) {
        state.dir = state.dir === "asc" ? "desc" : "asc";
      } else {
        state.sort = id;
        state.dir = "asc";
      }
      paintSort();
      apply();
    };
    const headInteractive = headCells.some(
      (th) =>
        th.querySelector(
          "a,button,input,select,textarea,[role=button],[tabindex]",
        ) !== null,
    );
    if (!isList && !headInteractive) {
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
        marks.set(col.id, mark);
        button.appendChild(mark);
        th.appendChild(button);
        button.addEventListener("click", () => setSort(col.id));
      });
    } else if (model.columns.length > 1) {
      const menu = document.createElement("details");
      menu.className = "sig-kit-menu";
      const summary = document.createElement("summary");
      summary.textContent = "Sort by";
      menu.appendChild(summary);
      const list = document.createElement("div");
      list.className = "sig-kit-chips";
      for (const col of model.columns) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "sig-kit-sort";
        const mark = document.createElement("span");
        mark.className = "sig-kit-sort-mark";
        mark.dataset.enhancement = "";
        mark.setAttribute("aria-hidden", "true");
        marks.set(col.id, mark);
        button.append(col.label, " ", mark);
        button.addEventListener("click", () => setSort(col.id));
        list.appendChild(button);
      }
      menu.appendChild(list);
      bar.append(" ", menu);
    }
    paintSort();

    bar.append(" ", status);
    this.insertBefore(bar, this.firstChild);
    apply();
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-table")) {
  customElements.define("sig-table", SigTable);
}
