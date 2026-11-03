import { describe, expect, it } from "vitest";
import {
  AGENDA_PORTALS,
  agendaPortalFor,
  EXCLUDED_RESOURCE_KINDS,
  PUBLIC_RESOURCES,
} from "../../src/lib/public-resources";

// P36.55 (UXR-06 / D3-Q4 [B-27] = yes / D-K7-3): the neutral 'Other public
// resources' block is content-neutral — no avoidance routing and no plate
// lookups, ever — and the official agenda portals are official hosts only.

const AVOIDANCE_TERMS = [
  "avoid",
  "evade",
  "detour",
  "reroute",
  "route around",
  "plate lookup",
  "plate-lookup",
  "lookup a plate",
  "track a plate",
  "search a plate",
  "who owns",
  "ticket",
];

describe("PUBLIC_RESOURCES — the answered decision stays enforced (D3-Q4 [B-27])", () => {
  it("carries the peer set, each with a name + tells + https url", () => {
    expect(PUBLIC_RESOURCES.length).toBeGreaterThanOrEqual(5);
    for (const r of PUBLIC_RESOURCES) {
      expect(r.name.length).toBeGreaterThan(0);
      expect(r.tells.length).toBeGreaterThan(0);
      expect(r.url.startsWith("https://")).toBe(true);
    }
  });

  it("no entry is an avoidance-routing or plate-lookup service", () => {
    for (const r of PUBLIC_RESOURCES) {
      const blob = `${r.name} ${r.tells} ${r.url}`.toLowerCase();
      for (const term of AVOIDANCE_TERMS) {
        expect(blob, `${r.name} contains avoidance/lookup term '${term}'`).not.toContain(term);
      }
    }
  });

  it("the exclusion vocabulary is fixed (avoidance_routing + plate_lookup)", () => {
    expect(EXCLUDED_RESOURCE_KINDS).toEqual(["avoidance_routing", "plate_lookup"]);
    // The rows carry no `kind` field at all — the block cannot grow one.
    for (const r of PUBLIC_RESOURCES) {
      expect("kind" in r).toBe(false);
    }
  });
});

describe("AGENDA_PORTALS — official agenda portals always (D-K7-3)", () => {
  it("every portal is an official government host — never a vendor or peer service", () => {
    for (const [key, portal] of Object.entries(AGENDA_PORTALS)) {
      expect(portal.url.startsWith("https://"), key).toBe(true);
      expect(
        /\.gov|legistar|civicclerk|municodemeetings|swagit\.com/.test(portal.url),
        `${key} portal ${portal.url} is not an official/agenda-platform host`,
      ).toBe(true);
      for (const term of ["vendor", "flock", "alpr.watch"]) {
        expect(portal.url.toLowerCase(), key).not.toContain(term);
      }
    }
  });

  it("agendaPortalFor resolves by jkey, then slug", () => {
    expect(
      agendaPortalFor({ jurisdiction_key: "us.census.geoid.place:4064000", slug: "x" })?.url,
    ).toContain("civicclerk");
    expect(agendaPortalFor({ slug: "oklahoma-city" })?.url).toContain("civicclerk");
    expect(agendaPortalFor({ slug: "nowhere" })).toBeNull();
  });
});
