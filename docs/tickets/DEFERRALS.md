<!--
  docs/tickets/DEFERRALS.md (BM-DEFER-01). Seeded by P22.3 (build-memory v2 migration) from the
  docs/build/LEDGER.md RETURN PASS table + returnPass: list. Append-only companion — NOT a chain
  ticket, never overwritten or deleted. The four rules below are stated verbatim.
-->
# Deferred obligations ledger

> **Maintained companion — NOT a generated ticket.** Committed and hand-maintained; preserved
> across any ticket regeneration; never overwritten or deleted. It has no `NN_` sequence prefix
> so it is not mistaken for a chain ticket.

The rules:
1. **Every run, first:** read this file. If the ticket you are about to implement — or a
   prerequisite it depends on — unblocks any `OPEN` row, **closing that row is part of your
   run**: verify it for real, then flip it to `DONE` with the date and evidence.
2. **Never delete a row.** Flip `OPEN` → `DONE` (verified) or `WONTFIX` (with a reason).
   History stays.
3. **When you defer something new,** append a row here in the same run that defers it. A
   deferral that is not in this file did not happen.
4. **Gates refuse to pass** while any `OPEN` row scoped to that phase remains. Treat an open
   row as gate-blocking.

Status values: `OPEN` (owed) · `PARTIAL` · `DONE` (verified — add date + evidence) ·
`WONTFIX` (add reason) · `ACCEPTED-SKELETON`. `kind`: V (verification) | F (functionality) |
D (deviation) | H (handoff seam) | P (human prerequisite) | X (other).

Pre-existing normalized debt is tracked in `docs/build/BACKLOG.csv`; each row below cites its
`BL-` id where one exists (no duplication). These rows are the **RETURN PASS** obligations from
`docs/build/LEDGER.md` — Phase-21 tickets the operator ran with a human gate skipped. They are
**not** blocks (the chain completed and the round-1 capstone is DONE); they are owed operator
work re-run per each ticket's `Run:` line after the operator acts.

| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |
|---|---|---|---|---|---|---|---|
| D-P21.1-1 | P | HG-03 — flip the reviewed OKC/critical-path sources to `ingestion_permitted=true` | P21.1 shipped the 27 rights packets, review-metadata rule + `review-status` CLI, but flipping a source is a human/rights decision (gate HG-03), not a code change | operator reads the packets in `docs/build/reports/rights/`, picks source ids to flip (each needs reviewer role + date) | `sig-connectors review-status` shows flip-ready sources; `loadable now: 0` until flipped | OPEN (cites BL-032) |
| D-P21.1-2 | P | HG-04 — record actual Stage-0 outreach outcomes to the 19 federation-compact projects | P21.1 shipped the outreach record template + letter; no outreach was performed (no outcomes to record) | operator performs/records outreach; rows move off `not_contacted`/`public_terms_only` | `docs/build/reports/STAGE0_OUTREACH_RECORD.md` all rows `not_contacted` | OPEN (cites BL-033) |
| D-P21.3-1 | V | HG-03 — first real LIVE fetch of ≥1 green source (document-connector modules okc_procurement/okcpd_policy/ok_statute) | P21.3 landed `HttpxTransport`/`OcflCaptureStore`/`sig-connectors run --mode live` (refuses exit 3 for non-green sources); no source is green yet | after D-P21.1-1 flips ≥1 source, re-run `implement-spec spec=docs/tickets/P21.3__live-connector-wiring.md live_verification=true` | stub + fixture-replay tested; `run --mode live` refuses exit 3, no socket opened | OPEN (cites BL-023) |
| D-P21.3-2 | P | HG-09 — API tokens (`SIG_MUCKROCK_TOKEN`/`SIG_DATA_GOV_KEY`/`SIG_OVERPASS_ENDPOINT`/`SIG_CIVICCLERK_BASE`) exported in the worker shell | live fetch needs credentials; `provided: no` at the P21.3 gate (secrets never in a file) | operator exports the env vars in the re-run shell; ledger records only `provided: yes/no` | no live fetch; no-token-literal test passes | OPEN (cites BL-024) |
| D-P21.4-1 | P | HG-01 — name the legal home | P21.4 ended at local staging; public publish is gated on a named legal home | operator names the legal home; `PUBLICATION_CHECKLIST.md` HG-01 ticks | staging-only run; `docs/build/reports/PUBLICATION_CHECKLIST.md` HG-01 open | OPEN (cites BL-034) |
| D-P21.4-2 | P | HG-11 — establish two reviewer roles + written concurrence + live takedown contact | governance prerequisites for public publish were not established | operator establishes the roles/concurrence/contact; `concurrence.md` filled | `docs/build/reports/okc/concurrence.md` template only | OPEN (cites BL-036) |
| D-P21.4-3 | P | Go-public — DNS/host cut-over to publish the first jurisdiction | impossible while HG-01 + HG-11 are open; P21.4 ends at staging | after D-P21.4-1/2, operator decides go-public and re-runs `implement-spec spec=docs/tickets/P21.4__first-jurisdiction-ingest-and-publish.md live_verification=true` | staging only (`SIG_STAGING_*` local); OSM-in-exports (HG-02) already ticked | OPEN (no dedicated BL; depends on BL-034/BL-036) |
| D-P21.5-1 | V | HG-07 — real Zenodo (sandbox) deposit + object-store push + egress report + SWH save | P21.5 ran dry-run/FakeZenodo/MockTransport; no credentials (`provided: no`), zero-cost posture | operator provides `SIG_ZENODO_SANDBOX_TOKEN`/`SIG_OBJECT_STORE_*` and re-runs `implement-spec spec=docs/tickets/P21.5__infra-deposit-and-tiles.md live_verification=true` | free paths (tiles/.torrent/degraded/SWH-save) real; credentialed steps dry-run/stub tested | OPEN (cites BL-029) |
| D-P21.7-1 | V | HG-08 — MapRoulette API key + registered OSM Organised-Editing page → real challenge push/pull | P21.7 ran dry-run/stub; the registration gate refuses push (exit 3) while `registered=false`; no creds | operator creates the account, registers the OE page, sets `SIG_MAPROULETTE_API_KEY`/`SIG_OSM_OE_PAGE`/`registered=true`, re-runs P21.7 live | dry-run payloads + OSM feed over fixtures tested; push refused exit 3 | OPEN (cites BL-039) |
| D-P21.7-2 | P | HG-10 — run the moderated usability study with ≥5 ontology-naïve participants | P21.7 shipped the runnable protocol + opt-in aggregate-only instrumentation; the study was not run | operator schedules ≥5 participants and runs the protocol; results replace "not yet run" | protocol + aggregate-only timing landed; results = gate-pending | OPEN (cites BL-040) |
| D-P21.8-1 | V | HG-03/HG-04 — live fetch of the data-driven / coarse-international sources (eff_data_driven, aspi, carnegie, facial_recognition_world_map) | P21.8 shipped the `data_driven` connector + coarse path over fixtures + 4 rights packets; no source green | operator flips the sources (per-source HG-03/04) and re-runs P21.8 with green sources | `run --mode live` refuses exit 3 for the new sources; fixtures tested | OPEN (cites BL-042) |
| D-P21.9-1 | V | HG-03/HG-04 — live fetch of the Stage-5 pathway sources (rtcc_federation / fr_css_forensics / acoustic_drone_location) | P21.9 shipped the `pathways` connector + 3 extractors + parser layers over fixtures + 3 rights packets; sources LINK-posture, UNDETERMINED | operator flips the sources and re-runs P21.9 with green sources | `run --mode live` refuses exit 3 for all 3 sources; shadow diff 0 | OPEN (cites BL-043) |
