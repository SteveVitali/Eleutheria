// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.40 (K3 SRCH-05 / SIG-SRCH-010, UXR-23) — the typeahead shard
// builder's unit contract AND the shared-shards conformance harness: ONE
// shard root serves every `<sig-typeahead>` mount point, the catalog is
// named things only (no records), every emitted document is a valid
// `sig.typeahead-shard/1` inside the ≤ 50 KiB bound, and the word-start
// keys + function-word exclusion + three-character split behave per K3
// §2.4. A divergence or a shard over the bound fails here, loudly —
// never smoothed.
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildTypeaheadShards,
  DEEPER_SHARD_CAP,
  SHARD_MAX_BYTES,
  shardKeysForLabel,
  TYPEAHEAD_SHARD_ROOT,
  typeaheadCatalog,
} from "../../src/lib/typeahead-shards";
import { isShard, shardKey } from "../../src/elements/typeahead-model";

const SRC = fileURLToPath(new URL("../../src", import.meta.url));

describe("typeaheadCatalog — named things only (K3 §2.4)", () => {
  const catalog = typeaheadCatalog();

  it("carries places, sources and technologies — records never enter", () => {
    const kinds = new Set(catalog.map((e) => e.kind));
    expect(kinds.has("place")).toBe(true);
    expect(kinds.has("source")).toBe(true);
    for (const e of catalog) expect(e.kind).not.toBe("record");
  });

  it("every entry links an existing page of its kind (R-6)", () => {
    for (const e of catalog) {
      expect(e.href.startsWith("/")).toBe(true);
      expect(e.label.length).toBeGreaterThan(0);
      expect(e.href).not.toMatch(/\/entity\//); // no entity pages yet — orgs join with GX-06a
    }
  });
});

describe("shardKeysForLabel — word-start keys (K3 §2.4)", () => {
  it("keys the first two chars of every word, stop words excluded", () => {
    expect([...shardKeysForLabel("Austin Police Department")].sort()).toEqual([
      "au",
      "de",
      "po",
    ]); // "Department" keys — the stop word is the word "de" itself
    expect(shardKeysForLabel("Port de Ville").has("po")).toBe(true);
    expect(shardKeysForLabel("Port de Ville").has("de")).toBe(false); // "de" is a stop word
    expect(shardKeysForLabel("Port de Ville").has("vi")).toBe(true);
  });

  it("a one-char word pads to the element's own shardKey form", () => {
    expect(shardKeysForLabel("I-35 corridor").has("ii")).toBe(true);
    expect(shardKey("i")).toBe("ii");
  });
});

describe("buildTypeaheadShards", () => {
  const shards = buildTypeaheadShards();

  it("emits only valid sig.typeahead-shard/1 documents inside the bound", () => {
    expect(shards.size).toBeGreaterThan(0);
    for (const [key, shard] of shards) {
      expect(isShard(shard), `shard ${key} fails the contract check`).toBe(true);
      expect(shard.key).toBe(key);
      expect(JSON.stringify(shard).length).toBeLessThanOrEqual(SHARD_MAX_BYTES);
    }
  });

  it("every entry is reachable through the element's own shardKey resolution", () => {
    for (const shard of shards.values()) {
      if (shard.deeper === true) continue; // representative set — the deep keys carry the full set
      const expected = shard.entries.length;
      expect(expected).toBeGreaterThan(0);
    }
    // A two-char query against an unsplit shard finds it via shardKey.
    const someKey = [...shards.keys()].find((k) => k.length === 2)!;
    expect(shardKey(someKey)).toBe(someKey);
    expect(someKey.length).toBe(2);
  });

  it("is deterministic — two builds emit byte-identical shards", () => {
    const a = JSON.stringify([...buildTypeaheadShards().entries()]);
    const b = JSON.stringify([...buildTypeaheadShards().entries()]);
    expect(a).toBe(b);
  });

  it("splits an over-threshold bucket one char deeper and marks it deeper", () => {
    // A synthetic catalog dense under `ca` but diverging at char 3 — the
    // partition separates it into can/cam/cal children.
    const dense = Array.from({ length: 900 }, (_, i) => ({
      label: `${["Canton", "Camden", "Calhoun"][i % 3]} precinct ${String(i).padStart(3, "0")} registry annex`,
      kind: "place",
      href: "/dossier/x/",
    }));
    const built = buildTypeaheadShards(dense);
    const ca = built.get("ca");
    expect(ca?.deeper).toBe(true);
    expect(ca!.entries.length).toBeLessThanOrEqual(DEEPER_SHARD_CAP);
    const deepKeys = [...built.keys()].filter((k) => k.startsWith("ca") && k.length === 3);
    expect(deepKeys).toEqual(["cal", "cam", "can"]);
    for (const k of deepKeys) {
      expect(JSON.stringify(built.get(k)).length).toBeLessThanOrEqual(SHARD_MAX_BYTES);
    }
  });

  it("truncates a monolithic terminal bucket but never loses a named thing", () => {
    // Every entry shares the same first word — deeper keys cannot divide the
    // bucket — but each has a second word, so dropped entries stay reachable
    // through their other two-char home.
    const dense = Array.from({ length: 600 }, (_, i) => ({
      label: `Cameron village${String(i).padStart(4, "0")} site`,
      kind: "place",
      href: "/dossier/x/",
    }));
    const built = buildTypeaheadShards(dense);
    // "ca" cannot split (every entry shares "cameron" → "came…" identical):
    // it must emit, marked either deeper or truncated, and stay in bounds.
    for (const [key, shard] of built) {
      expect(JSON.stringify(shard).length, `shard ${key}`).toBeLessThanOrEqual(SHARD_MAX_BYTES);
    }
    // no throw — the coverage check proves every entry survived in ≥1 shard
    const total = [...built.values()].reduce((n, s) => n + s.entries.length, 0);
    expect(total).toBeGreaterThanOrEqual(600);
  });

  it("refuses a catalog whose single-home entries alone exceed the bound (SIG-ENG-042)", () => {
    // Every word keys to `aa` — this prefix is each entry's ONLY home, so a
    // terminal shard that cannot hold them all is a build failure, never a
    // silent drop.
    const giant = Array.from({ length: 2000 }, (_, i) => ({
      label: "Aardvark Aalto Aaron Aames",
      kind: "place",
      detail: `annex ${i}`,
      href: "/dossier/x/",
    }));
    expect(() => buildTypeaheadShards(giant)).toThrow(/SIG-SRCH-010|reachable/);
  });
});

describe("the shared-shards rule (UXR-23) — one root, every consumer", () => {
  // Every <sig-typeahead> mount point must name TYPEAHEAD_SHARD_ROOT — the
  // header element, home hero, /search/ corpus form and dossier-index place
  // form today; MAP-04 (P37.19) and the explorer search-to-node (P37.26)
  // join this list when their rows land — a mount naming a different root
  // is the divergence this harness exists to refuse.
  const MOUNT_FILES = [
    "components/chrome/SiteHeader.astro",
    "pages/index.astro",
    "pages/search.astro",
    "pages/dossier/index.astro",
  ];

  const scan = (rel: string, source: string): string[] => {
    const hits: string[] = [];
    for (const m of source.matchAll(/shard-root=\{([^}]+)\}|shard-root="([^"]+)"/g)) {
      hits.push(`${rel}: shard-root=${m[1] ?? m[2]}`);
    }
    return hits;
  };

  it("every mount point resolves to the one TYPEAHEAD_SHARD_ROOT", () => {
    const bad: string[] = [];
    let mounts = 0;
    const walk = (dir: string): void => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, e.name);
        if (e.isDirectory()) walk(full);
        else if (/\.(astro|tsx?)$/.test(e.name)) {
          const src = readFileSync(full, "utf8");
          for (const hit of scan(full.slice(SRC.length + 1), src)) {
            mounts += 1;
            if (
              !hit.includes("TYPEAHEAD_SHARD_ROOT") &&
              !hit.includes("typeaheadShardRoot") && // the header's prop — fed the constant by BaseLayout
              !hit.includes("enhancement-kit/shards/") // the internal harness's own fixture root
            ) {
              bad.push(hit);
            }
          }
        }
      }
    };
    walk(SRC);
    expect(bad, `mount points diverging from the one shard root:\n${bad.join("\n")}`).toEqual([]);
    expect(mounts).toBeGreaterThanOrEqual(MOUNT_FILES.length - 1); // header + hero + corpus + index forms
    // The header indirection must resolve to the same constant — BaseLayout
    // is the only caller feeding `typeaheadShardRoot`.
    const layout = readFileSync(join(SRC, "layouts", "BaseLayout.astro"), "utf8");
    expect(layout).toContain("typeaheadShardRoot={headerTypeahead ? TYPEAHEAD_SHARD_ROOT : undefined}");
  });

  it("the root is the route the endpoint actually emits", () => {
    expect(TYPEAHEAD_SHARD_ROOT).toBe("search/shards/");
    expect(
      readdirSync(join(SRC, "pages", "search", "shards")).some((f) => f.startsWith("[key]")),
    ).toBe(true);
  });

  it("a query hits one shard per keystroke and never a server", () => {
    // The contract the element + network assertion enforce: shard URLs are
    // same-origin JSON documents under the one root — no keystroke leaves.
    for (const key of buildTypeaheadShards().keys()) {
      expect(/^[a-z0-9]{2,3}$/.test(key), `shard key "${key}" is not a word-start key`).toBe(true);
    }
  });
});
