# P32.24 — public investigation acceptance portfolio

- schema `sig.journey-portfolio/1` · requirement `SIG-FIND-007`
- candidate `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` · identity `sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f`
- evaluation **deferred** (mode `shadow`, decision null) — the S3 human-evaluation spine is operator-deferred; nothing here is a final evaluation
- published=False · provisional=True · review_only=True · ruleset `provisional-ruleset/1`
- acceptance release `p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd` · manifest `239814908a8cd8d5641a7425901bdf59c7020ed1c2700a70b58ba592c6ed480c` · records=75 · dossiers=okc, tulsa, san-diego

## Verdict — **PASS**

The P32.23a candidate publishes **zero records** — the record journeys are honestly `not_applicable` on it and execute over the declared acceptance corpus instead. Independent human usability evidence is `deferred` (D-R10-USERS-1): no session results exist or are claimed.

| check | journey | evidence class | status | detail |
|---|---|---|---|---|
| `candidate.export_digests` | candidate | automated_conformance | **pass** | 24 artifacts verified under candidate_export/ |
| `candidate.release_validation` | candidate | automated_conformance | **pass** | state=complete, artifacts_checked=18 |
| `candidate.identity` | candidate | automated_conformance | **pass** | publication=p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587; ruleset=provisional-ruleset/1; identity=sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f |
| `candidate.evaluation_deferred` | candidate | automated_conformance | **pass** | status=deferred; decision=None; mode=shadow; applied=[]; published=False; provisional=True; review_only=True |
| `candidate.record_surface` | candidate | automated_conformance | **not_applicable** | input_records=0; output_records=0; dossier_pages=0; evidence_pages=16 — the candidate publishes no records (its fixture-seeded repaired spine has no public population on this build), so record-journey semantics are exercised on the acceptance corpus instead |
| `candidate.zero_js` | candidate | automated_conformance | **pass** | 0 script-carrying pages |
| `candidate.deferral_dispositions` | candidate | automated_conformance | **pass** | dispositions=['D-R10-HUMAN-1', 'D-R10-LIVE-1', 'D-R10-PUBLISH-1', 'D-R6.1-EVAL'] |
| `candidate.dossier_portfolio` | candidate | automated_conformance | **pass** | dossiers=3; dossier_ids=['okc-flock-alpr', 'san-diego-sdpd-alpr', 'tulsa-tpd-alpr']; review=['not_run'] |
| `A.build_validates` | A | automated_conformance | **pass** | state=complete; artifacts_checked=176; publication=p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd |
| `A.records_reachable` | A | automated_conformance | **pass** | 75 records, 0 missing/mismatched |
| `A.citation` | A | automated_conformance | **pass** | manifest_sha256=239814908a8cd8d5…; sampled 25 record docs; bad=[] |
| `A.browse_exhaustive` | A | automated_conformance | **pass** | browse-covered 75/75; dup=0; deepest page=2 |
| `A.jurisdiction_unreported` | A | automated_conformance | **pass** | 5 unreported-jurisdiction records listed |
| `A.search` | A | automated_conformance | **pass** | tail=sig_graph:deployment:ent-acc-dep-54 found=True; exact=True; no-public-point hits=13 (expected>=13); no-match hits=0 |
| `A.location_states` | A | automated_conformance | **pass** | point=59; unresolved_point=['ent-acc-dep-45', 'ent-acc-dep-46', 'ent-acc-dep-47']; unreported=['ent-acc-dep-40', 'ent-acc-dep-41', 'ent-acc-dep-42', 'ent-acc-dep-43', 'ent-acc-dep-44', 'ent-acc-partner-00', 'ent-acc-partner-01', 'ent-acc-partner-02', 'ent-acc-partner-03', 'ent-acc-partner-04', 'ent-acc-partner-05', 'ent-acc-partner-06', 'ent-acc-partner-07'] |
| `A.evidence_anchors` | A | automated_conformance | **pass** | art-acc-1 anchor page=present; ghost anchor locator=unlocated; dep-03 unlocated leg=present |
| `A.dossiers` | A | automated_conformance | **pass** | scopes=['okc', 'tulsa', 'san-diego']; bad=[] |
| `A.static_vs_json` | A | automated_conformance | **pass** | sampled 20 records; disagreements=[] |
| `B.edges_typed` | B | automated_conformance | **pass** | 3 edges; untyped/unevidenced=0 |
| `B.edge_claims_resolve` | B | automated_conformance | **pass** | 3 edges; unresolved claim refs=[] |
| `B.bounded` | B | automated_conformance | **pass** | nodes=5; edges=3; kinds=['configured_access', 'declared_policy', 'observed_use'] |
| `B.candidate_network` | B | automated_conformance | **not_applicable** | candidate network: nodes=0; edges=0 — the typed-edge legs run on the acceptance corpus; re-run on the production candidate |
| `B.eval_deferred` | B | automated_conformance | **deferred** | any claim that a configured edge equals observed access, or a certified resolved-site interpretation, requires the final human evaluation — operator-deferred 2026-10-19 |
| `C.receipt_to_moderation` | C | automated_conformance | **pass** | sig.journey-intake-proof/1 executed on a real PG: 10/10 steps ok — submit→fresh-connection status→queue visibility |
| `C.receiver_cannot_write` | C | automated_conformance | **pass** | sig.journey-intake-proof/1 executed on a real PG: 10/10 steps ok — receiver-role canonical writes refused by the role grant shape |
| `C.apply_canonical_once` | C | automated_conformance | **pass** | sig.journey-intake-proof/1 executed on a real PG: 10/10 steps ok — §16.6 close+revises pair, one intake.application receipt, `applied` event; retry reconciles |
| `C.publish_linkage` | C | automated_conformance | **pass** | sig.journey-intake-proof/1 executed on a real PG: 10/10 steps ok — mark_published names publication_id + correction_ref; received/decided/applied/unpublished/published stay visible-distinct |
| `C.citation_persists` | C | automated_conformance | **pass** | manifest_sha256=239814908a8cd8d5641a7425901bdf59c7020ed1c2700a70b58ba592c6ed480c; the applied correction lands in the claim spine for the NEXT release — the released record bytes are unchanged (the manifest still validates) |
| `W.entity_withhold` | W | automated_conformance | **pass** | entity route permitted=False; json permitted=False; unaffected route permitted=True |
| `W.claim_withhold` | W | automated_conformance | **pass** | denied routes=4; claim-asserting route permitted=False |
| `W.tombstone_shape` | W | automated_conformance | **pass** | html tombstone=present; json schema=sig.tombstone/1 |
| `WT.no_js` | walkthrough | agent_walkthrough | **pass** | 0 script-carrying pages under p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd |
| `WT.keyboard` | walkthrough | agent_walkthrough | **verified_by_test** | the emitted archive is pure <a>-link/table markup (verified below); the interactive keyboard/axe proof is owned by the web e2e suite — agent walkthrough recorded in WALKTHROUGH_LOG.md |
| `WT.print` | walkthrough | agent_walkthrough | **pass** | emitted record/browse/dossier pages are single self-contained HTML documents with inline CSS and no external assets — print renders the same bytes |
| `WT.back_forward` | walkthrough | agent_walkthrough | **verified_by_test** | the sig.workspace-state/1 contract (islands/workspace.ts) is the only history adapter; its unit suite pins parse/emit + restored state — agent walkthrough recorded in WALKTHROUGH_LOG.md |
| `WT.release_citation` | walkthrough | agent_walkthrough | **pass** | the record citation /r/p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd/… resolves inside the staged release (verified byte-for-byte against the integrity manifest in A.records_reachable); the convenience /entity/ stub labels itself 'never cite' |
| `WT.receipt_to_moderation` | walkthrough | agent_walkthrough | **verified_by_test** | the deterministic traversal is owned by tests/db/test_journey_portfolio_pg.py (receipt→restart→queue→disposition→canonical apply→publish); the agent walkthrough narrative is in WALKTHROUGH_LOG.md |
| `UX.independent_sessions` | UX | independent_human | **deferred** | no volunteers were available in this run — the moderated-session task protocol is landed as the compensating control; nothing about user comprehension/satisfaction is claimed or fabricated |

## Honest gaps (owner → landing)

- `candidate.record_surface` — **not_applicable** · owner `D-P32.23a-1` → the production candidate (hosted repaired spine) — record-journey legs re-run against it at the return pass
- `B.candidate_network` — **not_applicable** · owner `D-P32.23a-1` → the production candidate (hosted repaired spine)
- `B.eval_deferred` — **deferred** · owner `D-R10-HUMAN-1` → the S3 human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23)
- `UX.independent_sessions` — **deferred** · owner `D-R10-USERS-1` → the moderated usability study (volunteer recruitment — operator-gated; GATE-G3 blocks public launch meanwhile)

## Boundaries

- `independent_human_evidence`: none — D-R10-USERS-1 OPEN; no usability/satisfaction/completion result is claimed
- `intake_operational`: False
- `live_verification`: False
- `publication`: not performed — D-R10-PUBLISH-1 OPEN
- `production_candidate`: not built — D-P32.23a-1 + D-R10-LIVE-1 OPEN
- `eval_final`: none — eval=deferred (D-R10-HUMAN-1)
