// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.63 (K11 RQ-04 / SIG-RQ-007, SIG-RQ-010): the records-request drafts
// model — matching, the never-send pin, the .txt builders and the ≤25 MB
// place-bundle sharding.
import { describe, expect, it } from "vitest";
import {
  DRAFT_BUNDLE_MAX_BYTES,
  NEVER_SENT_LINE,
  assertDraftsNeverSent,
  draftBundleFiles,
  draftBundleHref,
  draftForTask,
  draftTxt,
  isDraftRole,
  parseDraftsEnvelope,
  placeDraftBundles,
  residencyLine,
  type RecordsRequestDraft,
} from "../../src/lib/records-drafts";
import { placeFacets } from "../../src/lib/queue-hub";
import {
  QUEUE_CAMPAIGNS,
  RECORDS_REQUEST_DRAFTS,
  RESEARCH_QUEUE,
} from "../../src/lib/corrections-methodology-fixture";
import { dispositionsFor } from "../../src/lib/research-queue";

const OKC_CARD = RESEARCH_QUEUE.find((c) => c.task_type === "conflicting_retention")!;
const VA_CARD = RESEARCH_QUEUE.find((c) => c.task_type === "cooperative_contract_unexplored")!;
const FIELD_CARD = RESEARCH_QUEUE.find((c) => c.assignee_class === "field_mapper")!;

describe("draft eligibility and matching (SIG-RQ-007)", () => {
  it("drafts serve exactly the records-requester and document-reviewer classes", () => {
    expect(isDraftRole("records_requester")).toBe(true);
    expect(isDraftRole("document_reviewer")).toBe(true);
    for (const other of ["field_mapper", "local_group", "analyst", "curator", "developer"]) {
      expect(isDraftRole(other)).toBe(false);
    }
  });

  it("matches on the (task_type, subject_id) dedup key", () => {
    const d = draftForTask(OKC_CARD, RECORDS_REQUEST_DRAFTS);
    expect(d?.statutory_citation).toBe("Okla. Stat. tit. 51 § 24A.1");
    expect(draftForTask(VA_CARD, RECORDS_REQUEST_DRAFTS)?.residency_restricted).toBe(true);
    // A non-draft-role task has no draft — and never invents one.
    expect(draftForTask(FIELD_CARD, RECORDS_REQUEST_DRAFTS)).toBeNull();
    // A draft for a different subject does not bleed across tasks.
    const wrong = draftForTask({ ...OKC_CARD, subject_id: "agency:other" }, RECORDS_REQUEST_DRAFTS);
    expect(wrong).toBeNull();
  });
});

describe("the never-send pin", () => {
  it("rejects any row whose status is not 'drafted'", () => {
    const sent: RecordsRequestDraft = { ...RECORDS_REQUEST_DRAFTS[0]!, status: "sent" };
    expect(() => assertDraftsNeverSent([sent])).toThrow(/NEVER SEND/);
    expect(() => assertDraftsNeverSent(RECORDS_REQUEST_DRAFTS)).not.toThrow();
  });

  it("rejects an envelope with a nonzero sent count or a malformed shape", () => {
    expect(() =>
      parseDraftsEnvelope({ requests: RECORDS_REQUEST_DRAFTS, sent: 1 }, "test"),
    ).toThrow(/sent/);
    expect(() => parseDraftsEnvelope({ nope: true }, "test")).toThrow(/requests/);
    const rows = parseDraftsEnvelope({ requests: RECORDS_REQUEST_DRAFTS, sent: 0 }, "test");
    expect(rows).toHaveLength(RECORDS_REQUEST_DRAFTS.length);
  });
});

describe("the .txt draft document", () => {
  it("carries the DRAFT banner, statute, citation, versions, residency and never-send line", () => {
    const draft = draftForTask(OKC_CARD, RECORDS_REQUEST_DRAFTS)!;
    const text = draftTxt(OKC_CARD, draft);
    expect(text).toContain("DRAFT PUBLIC-RECORDS REQUEST");
    expect(text).toContain("Oklahoma Open Records Act");
    expect(text).toContain("Okla. Stat. tit. 51 § 24A.1");
    expect(text).toContain("surveillance_policy v1");
    expect(text).toContain(NEVER_SENT_LINE);
    expect(text).toContain("[the contributor who files this request");
    expect(text).toContain(draft.draft_body);
    // No requester identity and no transmit path in the text itself.
    expect(text).not.toMatch(/mailto:|https?:\/\//);
  });

  it("renders the residency routing note verbatim for a restricted state", () => {
    const draft = draftForTask(VA_CARD, RECORDS_REQUEST_DRAFTS)!;
    expect(residencyLine(draft)).toContain("restricts public-records requests to residents");
    const open = draftForTask(OKC_CARD, RECORDS_REQUEST_DRAFTS)!;
    expect(residencyLine(open)).toContain("No residency restriction");
  });
});

describe("per-place bundles (SIG-RQ-010)", () => {
  const bundles = placeDraftBundles(RESEARCH_QUEUE, RECORDS_REQUEST_DRAFTS, placeFacets(RESEARCH_QUEUE));

  it("bundles mint only for places that have drafts", () => {
    const slugs = bundles.map((b) => b.slug);
    expect(slugs).toContain("usa/ok/oklahoma-city-4064000");
    expect(slugs).toContain("usa/va/fairfax-county-51059");
    // The unplaced bucket has no draft-bearing task — no file is minted.
    expect(slugs).not.toContain("unplaced");
    expect(bundles.find((b) => b.slug === "usa/ok/oklahoma-city-4064000")!.entries).toHaveLength(1);
  });

  it("each emitted file is ≤ 25 MB and carries the DRAFT + never-send lines", () => {
    const files = draftBundleFiles(bundles);
    expect(files.length).toBeGreaterThan(0);
    for (const f of files) {
      expect(new TextEncoder().encode(f.text).length).toBeLessThanOrEqual(DRAFT_BUNDLE_MAX_BYTES);
      expect(f.text).toContain("DRAFT");
      expect(f.text).toContain("0 sent");
      expect(f.path).toMatch(/^research-queue\/drafts\/.+\.txt$/);
    }
    const okc = files.find((f) => f.routeSlug === "usa/ok/oklahoma-city-4064000")!;
    expect(okc.text).toContain("Oklahoma Open Records Act");
    const va = files.find((f) => f.routeSlug === "usa/va/fairfax-county-51059")!;
    expect(va.text).toContain("Virginia Freedom of Information Act");
    expect(va.text).toContain("restricts public-records requests to residents");
  });

  it("splits over-cap bundles at draft boundaries, each part ≤ the cap and labelled", () => {
    // Synthetic oversized drafts force the split — the cap is never smoothed.
    const big = "x".repeat(4_000);
    const drafts: RecordsRequestDraft[] = Array.from({ length: 5 }, (_, i) => ({
      ...RECORDS_REQUEST_DRAFTS[0]!,
      subject_id: `agency:s${i}`,
      draft_body: big,
    }));
    const cards = drafts.map((d, i) => ({
      ...OKC_CARD,
      task_id: `fx-big-${i}`,
      subject_id: d.subject_id!,
      handle: `T-big-${i}`,
    }));
    const [bundle] = placeDraftBundles(cards, drafts, [{ slug: "usa/ok/oklahoma-city-4064000", name: "Oklahoma City" }]);
    const files = draftBundleFiles([bundle!], 8_000);
    expect(files.length).toBeGreaterThan(1);
    for (const f of files) {
      expect(new TextEncoder().encode(f.text).length).toBeLessThanOrEqual(8_000);
      expect(f.routeSlug).toContain("--part-");
      expect(f.text).toMatch(/part \d+ of \d+/);
    }
    expect(files.reduce((n, f) => n + f.drafts, 0)).toBe(5);
  });

  it("a single draft over the cap fails loud — never a truncated file", () => {
    const drafts: RecordsRequestDraft[] = [
      { ...RECORDS_REQUEST_DRAFTS[0]!, draft_body: "x".repeat(10_000) },
    ];
    const bundles_ = [{ slug: "usa/ok", placeName: "Oklahoma", entries: [{ card: OKC_CARD, draft: drafts[0]! }] }];
    expect(() => draftBundleFiles(bundles_, 5_000)).toThrow(/cap/);
  });

  it("bundle hrefs name the file — part files only for multi-part bundles", () => {
    expect(draftBundleHref("usa/ok")).toBe("research-queue/drafts/usa/ok.txt");
    expect(draftBundleHref("usa/ok", { n: 2, of: 3 })).toBe(
      "research-queue/drafts/usa/ok--part-2-of-3.txt",
    );
    expect(draftBundleHref("usa/ok", { n: 1, of: 1 })).toBe("research-queue/drafts/usa/ok.txt");
  });
});

describe("the campaign lane stays untouched", () => {
  it("campaigns never carry a draft (field gaps aggregate, they are not filed)", () => {
    expect(QUEUE_CAMPAIGNS.length).toBeGreaterThan(0);
    for (const c of QUEUE_CAMPAIGNS) {
      for (const m of c.members ?? []) {
        expect(
          RECORDS_REQUEST_DRAFTS.some((d) => d.subject_id === m.subject_id),
        ).toBe(false);
      }
    }
  });

  it("fixture cards keep unique handles incl. the new document-reviewer row", () => {
    const handles = RESEARCH_QUEUE.map((c) => c.handle).filter(Boolean);
    expect(new Set(handles).size).toBe(handles.length);
    const va = RESEARCH_QUEUE.find((c) => c.handle === "T-usa-va-fairfax-county-contract-pd-d8r2")!;
    expect(va.assignee_class).toBe("document_reviewer");
    expect(va.dispositions).toEqual(dispositionsFor("document_reviewer"));
  });
});
