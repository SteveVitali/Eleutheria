# ADR-246 — Claim viewer v2: document-genre scope, the download pane, the excerpt gate, and `quotation_permitted` (P37.37)

- Date: 2026-11-12
- Status: accepted
- Ticket: P37.37 (K8 EV-03, manifest row 461 — on `r11/P37.37-claim-viewer-v2`)
- Base: `r11/P37.36-raw-archive`
- Requirement stamps: SIG-EVUI-009 (owned), SIG-EVUI-004 (cited; amends SIG-UI-028), SIG-UI-028, SIG-UI-029 (spec amended)
- Decisions implemented verbatim: `D-K8-1 [B-44] / D-K8-2 [B-22] = as recommended` (the plan cell — "a locator always; an excerpt ≤ 300 characters only where recorded terms permit quotation")
- Supersedes: nothing

## Context

K8's EV-03 lands the claim viewer's second form: generation for
document-genre `actual_capture` claims with a published cap (D-K8-2), the
lane-aware pane union P36.51's `ClaimView` model specified, the §4.4 diff
over real captures only, and spec amendments to SIG-UI-028/029. Four
decisions were the ticket's to make and are recorded here.

## Decision

1. **"Document genres" is the recorded document class set.** Of the closed
   `vocab_artifact_genre` vocabulary, claim views mint for:
   `agenda_document`, `agency_policy`, `audit_log`, `bill_index`,
   `contract`, `council_minutes`, `executed_contract`, `invoice`,
   `news_article`, `official_statement`, `portal_document`,
   `portal_snapshot`, `template`, `vendor_default_page`. The dataset and
   run-record classes (`camera_registry`, `osm_node_set`, `community_map`,
   `subscription`, `recommendation`, `connector_run`) are not document
   genres — their claims keep record anchors and statements, never a
   standalone view (K8 E-P4).
2. **A fifth pane kind, `download`, joins the union.** A raw-ok capture
   whose bytes the raw archive serves (P37.36's `served_href_map`, read as
   `raw['raw_hrefs']`) renders the locator + hash/time with the
   view-original link — never inline text the release does not carry.
   `assertClaimView` requires the raw-ok lane AND the served href; a raw-ok
   claim with no served object renders `locator_only` (a label never
   implies a route the release does not carry). `text_span` fires only
   where the declared `capture_texts` seam supplies stored text AND the
   recorded `byte_range` locator resolves — the `document_text` a sealed or
   restricted lane forbids can never enter a view.
3. **The excerpt gate is fail-closed (D-K8-1).** A locator always renders
   (`Locator.span` is optional — a page/row/selector locator carries none
   rather than a fabricated range). The recorded `claim_evidence.excerpt`
   publishes only on a non-metadata pane, at most 300 characters, and only
   where the source's recorded terms permit quotation — the new
   `[redistribution].quotation_permitted` registry marker — or on the
   raw-ok lane, where the bytes themselves publish (an excerpt is trivially
   permitted). No source sets the marker today; the gate stays closed until
   a recorded terms verdict opens it.
4. **Diff fields are recorded values only.** The per-capture `fields` map
   is predicate → verbatim `raw_value` over every publishable bound claim
   (all genres — the §4.4 diff is not scoped to view-eligible claims); a
   multi-valued predicate joins its values sorted with `"; "` so a set
   change diffs honestly. A second capture that was never recorded is a
   typed absence on the artifact page, never a fabricated pair
   (SIG-EVUI-005).

## Consequences

- `evidence.json` carries `claim_views` (generated, capped at 20,000 per
  D-K8-2) and `build.claim_views` (`cap`/`eligible`/`emitted`/`overflow`),
  which `/evidence/` states verbatim.
- `[redistribution]` gains the additive `quotation_permitted` field
  (closed-shape parse extended; default `false`).
- SIG-UI-028/029 are amended at `spec_src` (lane-aware pane model; real
  captures only).

## Revisit trigger

Revisit when the capture-text seam produces stored text for real claims
(the `text_span` pane starts firing in export mode), when a source's
recorded terms verdict first sets `quotation_permitted`, or when a diff
needs a field vocabulary beyond predicate→raw_value.
