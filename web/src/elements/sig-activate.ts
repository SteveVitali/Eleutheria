// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.29 (K6 VIZ-04, SIG-UI-127) — `<sig-activate>`: the in-place map
 * activation on dossiers. The element upgrades a plain
 * `<a class="sig-activate" href="/map/?v=2&jurisdiction=<jkey>">` (the no-JS
 * and touch path — the link simply navigates) into a
 * `<button aria-expanded>` ONLY where the pointer+width media query matches
 * (K6 §5.4's desktop-only rule — never touch/mobile activation), and on
 * click lazily `import()`s the deferred K1 map-app bundle the emitted shim
 * names (`app` attribute → `/_kit/sig-map-embed.js`) plus the per-dossier
 * props document (`props` → `dossier/<slug>/map-embed.json`). Nothing T2 is
 * fetched before the click: the element itself is the ≈1.5 KiB T1
 * enhancement the dossier page is classified for.
 *
 * The mount reuses the static figure's reserved box (`target` names the
 * overlay host inside it). The static SVG stays in the DOM — never removed —
 * so `/print/` and every print rendition keep the figure; it is
 * `aria-hidden` once the first drawn render lands. The embedded app writes
 * no browser history and no `sig.workspace-state` URL (V-10); "Open full
 * map" / "Cite this view" are the hand-offs, "Close interactive map"
 * restores the figure and returns focus to the button. A failed import,
 * props fetch, WebGL init or tile load keeps the static figure and shows the
 * failure notice (role=status). Every injected node is `[data-enhancement]`
 * for the no-JS parity sweep (SIG-UI-091).
 */

const DESKTOP_POINTER = "(min-width: 64rem) and (pointer: fine)";
const FAILURE_TEXT =
  "The interactive map could not load; the figure and the places table show the same records.";

interface EmbedModule {
  mountEmbeddedMap: (host: HTMLElement, props: Record<string, unknown>) => () => void;
}

class SigActivate extends HTMLElement {
  private enhanced = false;
  private button: HTMLButtonElement | null = null;
  private unmount: (() => void) | null = null;
  private busy = false;
  private observer: MutationObserver | null = null;

  connectedCallback() {
    if (this.enhanced) return;
    this.enhanced = true;
    const anchor = this.querySelector<HTMLAnchorElement>("a[href].sig-activate");
    if (anchor === null) return;
    // K6 §5.4: the upgrade exists only where the desktop pointer media query
    // matches — on phones/tablets (and without a fine pointer) the anchor is
    // the complete affordance and navigates to /map/.
    if (typeof window === "undefined" || !window.matchMedia) return;
    if (!window.matchMedia(DESKTOP_POINTER).matches) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "sig-activate__button";
    // NOT [data-enhancement]: the button REPLACES the anchor (identical
    // text) — the parity sweep compares main text, so the control's own
    // label must count on both sides of the upgrade (SIG-UI-091). Only
    // the injected chrome around it (the status note) is enhancement.
    button.setAttribute("aria-expanded", "false");
    const controls = this.getAttribute("target");
    if (controls) button.setAttribute("aria-controls", controls);
    button.textContent = anchor.textContent;
    button.addEventListener("click", () => void this.activate());
    anchor.replaceWith(button);
    this.button = button;
  }

  disconnectedCallback() {
    this.observer?.disconnect();
  }

  private host(): HTMLElement | null {
    const id = this.getAttribute("target");
    if (!id) return null;
    const root = this.getRootNode() as Document | ShadowRoot;
    return root.getElementById?.(id) ?? document.getElementById(id);
  }

  private staticFigure(): Element | null {
    const sel = this.getAttribute("static-figure");
    return sel ? this.closest("figure")?.querySelector(sel) ?? null : null;
  }

  private note(text: string) {
    const p = document.createElement("p");
    p.className = "sig-activate__note";
    p.setAttribute("role", "status");
    p.dataset.enhancement = "";
    p.dataset.copy = "SA-02";
    p.textContent = text;
    this.append(p);
  }

  private async activate() {
    if (this.busy || this.unmount !== null || this.button === null) return;
    const host = this.host();
    const appHref = this.getAttribute("app");
    const propsHref = this.getAttribute("props");
    const cssHref = this.getAttribute("css");
    if (host === null || !appHref || !propsHref) return;
    this.busy = true;
    this.button.setAttribute("aria-busy", "true");
    try {
      // Both fetches are post-action: the deferred module (the K1 map app's
      // emitted chunk — the same hashed module graph /map/ shares) and this
      // dossier's serialised props document.
      const [mod, res] = await Promise.all([
        import(/* @vite-ignore */ appHref) as Promise<EmbedModule>,
        fetch(propsHref),
      ]);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const props = (await res.json()) as Record<string, unknown>;
      if (typeof mod.mountEmbeddedMap !== "function") {
        throw new Error("map-embed: no mountEmbeddedMap export");
      }
      if (cssHref && !document.querySelector(`link[href="${cssHref}"]`)) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = cssHref;
        link.dataset.enhancement = "";
        document.head.appendChild(link);
      }
      host.hidden = false;
      this.unmount = mod.mountEmbeddedMap(host, {
        ...props,
        embedded: {
          ...((props.embedded as Record<string, unknown> | undefined) ?? {}),
          onClose: () => this.deactivate(true),
          onFailed: () => this.fail(),
        },
      });
      this.button.setAttribute("aria-expanded", "true");
      host.setAttribute("data-activated", "true");
      // The static SVG stays in the DOM — it is only hidden from AT once the
      // app's first drawn render lands (data-drawn latches on idle).
      this.observer = new MutationObserver(() => {
        const drawn = host.querySelector("[data-drawn='true']");
        const failed = host.querySelector("[data-failed='true']");
        if (drawn) this.staticFigure()?.setAttribute("aria-hidden", "true");
        if (failed) this.fail();
      });
      this.observer.observe(host, {
        attributes: true,
        attributeFilter: ["data-drawn", "data-failed"],
        subtree: true,
      });
    } catch {
      this.fail();
    } finally {
      this.busy = false;
      this.button?.removeAttribute("aria-busy");
    }
  }

  private fail() {
    if (this.unmount !== null) {
      try {
        this.unmount();
      } catch {
        /* teardown best-effort */
      }
      this.unmount = null;
    }
    this.observer?.disconnect();
    this.observer = null;
    const host = this.host();
    if (host) {
      host.hidden = true;
      host.removeAttribute("data-activated");
    }
    this.staticFigure()?.removeAttribute("aria-hidden");
    this.button?.setAttribute("aria-expanded", "false");
    if (!this.querySelector(".sig-activate__note")) this.note(FAILURE_TEXT);
    this.button?.focus();
  }

  /** "Close interactive map" — unmounts, restores the figure, returns focus. */
  private deactivate(refocus: boolean) {
    this.observer?.disconnect();
    this.observer = null;
    if (this.unmount !== null) {
      try {
        this.unmount();
      } catch {
        /* teardown best-effort */
      }
      this.unmount = null;
    }
    const host = this.host();
    if (host) {
      host.hidden = true;
      host.removeAttribute("data-activated");
    }
    this.staticFigure()?.removeAttribute("aria-hidden");
    this.button?.setAttribute("aria-expanded", "false");
    if (refocus) this.button?.focus();
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sig-activate")) {
  customElements.define("sig-activate", SigActivate);
}
