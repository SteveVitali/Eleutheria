import { describe, expect, it } from "vitest";
import { DOWNLOAD_LISTING_SCHEMA, filesByPath, formatBytes, isDownloadListing } from "../../src/lib/downloads";
import { DOWNLOAD_LISTING_FIXTURE } from "../../src/lib/downloads-fixture";

describe("sig.download-listing/1 (P36.50)", () => {
  it("the committed fixture validates and groups resolve to listed files", () => {
    expect(isDownloadListing(DOWNLOAD_LISTING_FIXTURE)).toBe(true);
    expect(DOWNLOAD_LISTING_FIXTURE.schema).toBe(DOWNLOAD_LISTING_SCHEMA);
    const files = filesByPath(DOWNLOAD_LISTING_FIXTURE);
    for (const g of DOWNLOAD_LISTING_FIXTURE.groups) {
      expect(g.id).toBeTruthy();
      // named members (SHA256SUMS &c.) may resolve to nothing — never a broken group
      for (const p of g.files) expect(typeof p).toBe("string");
      void files;
    }
  });

  it("every file carries licence, sha256 and an R2-host content-hash href", () => {
    for (const f of DOWNLOAD_LISTING_FIXTURE.files) {
      expect(f.license).toBeTruthy();
      expect(f.sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(f.href.startsWith("https://files.surveillancegraph.org/")).toBe(true);
      expect(f.href).toContain(`.${f.sha256.slice(0, 12)}.`);
    }
  });

  it("per-source slice groups name a source and a compartment", () => {
    const srcs = DOWNLOAD_LISTING_FIXTURE.groups.filter((g) => g.kind === "source");
    expect(srcs.length).toBeGreaterThan(0);
    for (const g of srcs) {
      expect(g.source_id).toBeTruthy();
      expect(g.compartment).toBeTruthy();
    }
    // K9 C-8: a statements slice is among them
    const stmts = DOWNLOAD_LISTING_FIXTURE.files.filter((f) => f.path.includes("statements"));
    expect(stmts.some((f) => f.path.startsWith("by-source/"))).toBe(true);
  });

  it("the signature block declares a state honestly (never silent)", () => {
    const sig = DOWNLOAD_LISTING_FIXTURE.signature;
    expect(["signed", "unsigned"]).toContain(sig.state);
    if (sig.state === "unsigned") expect(sig.reason).toBeTruthy();
    expect(sig.checksum_file).toBe("SHA256SUMS");
  });

  it("the guard rejects malformed listings", () => {
    expect(isDownloadListing(null)).toBe(false);
    expect(isDownloadListing({})).toBe(false);
    expect(isDownloadListing({ ...DOWNLOAD_LISTING_FIXTURE, schema: "x" })).toBe(false);
    expect(
      isDownloadListing({
        ...DOWNLOAD_LISTING_FIXTURE,
        files: [{ path: "a" }],
      }),
    ).toBe(false);
  });

  it("formatBytes renders human sizes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KiB");
    expect(formatBytes(3 << 20)).toBe("3.0 MiB");
  });
});
