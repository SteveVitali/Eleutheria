# Hostile-reader review — Oklahoma City dossier (P21.4)

Adopts `docs/governance/hostile-reader-review-dossier.md` (§41, SIG-UI-042). The
reviewer reads the **real rendered** OKC dossier — the one built **from the export
bytes** (`SIG_DATA_SOURCE=export`, `sig-exports build --jurisdiction okc`) — adopting
the stance of the documented organisation's counsel (OKCPD / Flock), and logs every
sentence that could be challenged as uncited, characterised, or overstated.

| Field | Value |
|---|---|
| Dossier reviewed | `/dossier/oklahoma-city/` — a real render from the export (not a mock, not fixtures) |
| Data source | `SIG_DATA_SOURCE=export`, export dir from `sig-exports build --jurisdiction okc` |
| Template version | `resolver-ruleset-2026.07` |
| Reviewers | Reviewer A (counsel stance); Reviewer B (counsel stance) — two independent |
| Review date | 2026 (P21.4 run) |
| Outcome | **No uncited claim found.** Every material number links claim → evidence; the contradiction is shown with both sources and dates. |

## What was checked (and passed)

- **The 299-vs-190 `claimed_device_count` contradiction is reported, not
  characterised.** The figure renders as a contested standoff ("190–299", persistent
  contested marker) whose reconciliation lists BOTH claims — DeFlock (299, 2026-08-20,
  W2) and Chief Bacy (190, 2026-08-18, W2) — each with its source, tier, date, and a
  document link; the "different quantity" note explains the metro-vs-city-limits scope
  difference. No single number is asserted as the truth (no synthetic certainty, §3.1).
- **Every material figure is cited.** Active count (90 → Chief Bacy, 2026-08-18),
  independently-mapped count (31 → OSM, named a **lower bound** in the same figure,
  ODbL-attributed) — each expands to its reconciliation with a document link
  (`data-testid="recon-claim"`, one per claim).
- **Every asserted row value carries a document link.** Contract value/expiry,
  configured access (109), national network (5,000+), retention (7/30 days), agency
  sharing policy, litigation — each row with a value cites its supporting document; a
  gap row (observed searches) renders explicitly as `NOT_RESEARCHED`, not omitted
  (SIG-UI-015).
- **No allegation is stated as established fact.** The litigation row states the Flock
  *platform* is "under federal constitutional challenge (vendor)" — an accurate,
  attributed statement about the existence of litigation, not an adjudicated finding.
- **No un-permitted public-employee name is published.** Claims are attributed to
  source roles/records (e.g. "OKCPD Chief Bacy, city council 2026-08-18" as an
  attribution, not a person-claim); `applyPublicationPolicy` runs over the dossier at
  build (SIG-PUB-017) and can only withhold.

## Findings and disposition

| id | Finding (counsel stance) | Register rule | Disposition | Resolution |
|---|---|---|---|---|
| okc-hr-1 | The 299 figure could read as SIG's own count | 1 (report, don't characterise) | accepted, verified | Rendered as a competing *claim* attributed to DeFlock with its date; the winner is "no resolution", both retained. |
| okc-hr-2 | The 31-device map figure could read as a total | 5 (name uncertainty with the number) | accepted, verified | Labelled "(lower bound)" in the figure headline and the note. |
| okc-hr-3 | "under federal constitutional challenge" | 2 (never state an allegation as fact) | accepted, verified | Phrased as the existence of a vendor-level challenge, attributed to a document; not an outcome. |

**Release status for this review: no uncited claim; clean.** (Publication remains
gated on HG-01/HG-11 per `PUBLICATION_CHECKLIST.md` — this review is one input to
that gate, not the gate itself.)
