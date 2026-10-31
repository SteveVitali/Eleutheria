// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4, K3's SRCH-05 posture) — `<sig-typeahead>`: an APG
 * combobox over static suggestion shards.
 *
 * The element wraps a plain GET form whose input already submits a working
 * no-JS search. With JS it becomes a listbox-combobox: each keystroke maps
 * to a shard key (`<shard-root><key>.json`, `sig.typeahead-shard/1`), the
 * shard is fetched once and cached, and the top matches render as options.
 * There is no live-spine read anywhere — a failed fetch or malformed shard
 * closes the listbox and the form still submits. Every injected node is
 * `[data-enhancement]` for the SIG-UI-091 parity sweep.
 */
import {
  isShard,
  matchEntries,
  shardKey,
  type TypeaheadEntry,
  type TypeaheadShard,
} from "./typeahead-model";

const uid = (() => {
  let n = 0;
  return () => `sig-typeahead-${++n}`;
})();

// P36.40: SSR-safe — a T2 island bundle imports this module to register the
// element under its own `/_astro/` graph, and Astro evaluates the island's
// module graph during server-side rendering where `HTMLElement` does not
// exist. The class is never instantiated there (there is no DOM to mount),
// so the browser-only base is a stand-in under SSR only.
const HTMLElementBase: typeof HTMLElement =
  typeof HTMLElement === "undefined"
    ? (class {} as unknown as typeof HTMLElement)
    : HTMLElement;

class SigTypeahead extends HTMLElementBase {
  private enhanced = false;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const root = this.getAttribute("shard-root");
    const input = this.querySelector<HTMLInputElement>(
      'input[type="search"], input[name="q"], input[type="text"]',
    );
    if (root === null || input === null) return;

    const minChars = Number(this.getAttribute("min-chars") ?? "2");
    const keyLen = Number(this.getAttribute("key-len") ?? "2");
    const maxItems = Number(this.getAttribute("max-items") ?? "8");

    const id = uid();
    const popup = document.createElement("div");
    popup.className = "sig-typeahead-popup";
    popup.dataset.enhancement = "";
    const list = document.createElement("ul");
    list.className = "sig-typeahead-list";
    list.id = `${id}-listbox`;
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-label", "Suggestions");
    list.hidden = true;
    const status = document.createElement("span");
    status.className = "sig-kit-status";
    status.setAttribute("role", "status");
    popup.append(list, status);
    input.insertAdjacentElement("afterend", popup);

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", list.id);
    input.setAttribute("autocomplete", "off");

    const shards = new Map<string, Promise<TypeaheadShard>>();
    let options: TypeaheadEntry[] = [];
    let active = -1;
    let open = false;

    const loadShard = (key: string): Promise<TypeaheadShard> => {
      let p = shards.get(key);
      if (p === undefined) {
        p = fetch(`${root}${key}.json`)
          .then((r) => (r.ok ? r.json() : null))
          .then(
            (doc): TypeaheadShard =>
              isShard(doc) && doc.key === key
                ? doc
                : { schema: "sig.typeahead-shard/1", key, entries: [] },
          )
          .catch((): TypeaheadShard => ({ schema: "sig.typeahead-shard/1", key, entries: [] }));
        shards.set(key, p);
      }
      return p;
    };

    const setOpen = (value: boolean) => {
      open = value;
      list.hidden = !value;
      input.setAttribute("aria-expanded", String(value));
      if (!value) {
        active = -1;
        input.removeAttribute("aria-activedescendant");
      }
    };

    const render = () => {
      while (list.firstChild !== null) list.removeChild(list.firstChild);
      options.forEach((entry, i) => {
        const li = document.createElement("li");
        li.className = "sig-typeahead-option";
        li.id = `${id}-opt-${i}`;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", String(i === active));
        const text = document.createElement("span");
        text.textContent = entry.label;
        li.appendChild(text);
        if (entry.kind !== undefined && entry.kind !== "") {
          const kind = document.createElement("span");
          kind.className = "sig-typeahead-kind";
          kind.textContent = entry.kind;
          li.append(" ", kind);
        }
        if (entry.detail !== undefined && entry.detail !== "") {
          const detail = document.createElement("span");
          detail.className = "sig-typeahead-detail";
          detail.textContent = entry.detail;
          li.append(" ", detail);
        }
        li.addEventListener("pointerdown", (e) => {
          // pointerdown (not click) so the choice lands before blur closes.
          e.preventDefault();
          window.location.assign(entry.href);
        });
        list.appendChild(li);
      });
    };

    const refresh = async () => {
      const q = input.value.trim();
      if (q.length < minChars) {
        options = [];
        setOpen(false);
        status.textContent = "";
        return;
      }
      const key = shardKey(q, keyLen);
      if (key === null) {
        options = [];
        setOpen(false);
        status.textContent = "";
        return;
      }
      let shard = await loadShard(key);
      // P36.40's split shards: a `deeper` bucket split to three-char keys —
      // once the query's first run reaches three characters, refetch the
      // deeper shard for the full set (the two-char shard is a bounded
      // representative set by construction).
      const run = /^[a-z0-9]+/i.exec(q)?.[0].toLowerCase() ?? "";
      if (shard.deeper === true && run.length > key.length) {
        const deepKey = (run + run.slice(-1).repeat(3)).slice(0, 3);
        if (deepKey !== key) shard = await loadShard(deepKey);
      }
      // A slower shard reply must never overwrite a newer query.
      if (input.value.trim() !== q) return;
      options = matchEntries(shard.entries, q).slice(0, maxItems);
      // Nothing pre-selected: Enter still submits the plain GET form unless
      // the user actively arrows onto an option (the no-JS path, preserved).
      active = -1;
      render();
      setOpen(options.length > 0);
      status.textContent =
        options.length === 0
          ? "No suggestions."
          : `${options.length} suggestion${options.length === 1 ? "" : "s"}.`;
    };

    const move = (delta: number) => {
      if (!open || options.length === 0) return;
      active = (active + delta + options.length) % options.length;
      input.setAttribute("aria-activedescendant", `${id}-opt-${active}`);
      [...list.children].forEach((li, i) =>
        li.setAttribute("aria-selected", String(i === active)),
      );
    };

    input.addEventListener("input", () => void refresh());
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        move(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        move(-1);
      } else if (e.key === "Enter") {
        if (open && active >= 0 && options[active] !== undefined) {
          e.preventDefault();
          window.location.assign(options[active].href);
        }
        // No active option: the event propagates and the GET form submits —
        // the no-JS path, preserved.
      } else if (e.key === "Escape") {
        setOpen(false);
        status.textContent = "";
      }
    });
    input.addEventListener("blur", () => {
      // Defer so a pointerdown on an option lands first.
      setTimeout(() => {
        if (!this.contains(document.activeElement)) setOpen(false);
      }, 0);
    });
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-typeahead")) {
  customElements.define("sig-typeahead", SigTypeahead);
}
