# ADR-074 — OKC document connectors (`okc_procurement`/`okcpd_policy`/`ok_statute`) over the sig-parsing layers, with the Part VIII guard

- **Status:** Accepted
- **Phase / ticket:** P23.5 — LIVE.1a / GL-LIVE-01 (the one genuinely-new build item in Round 3; the new-code half of LIVE.1)
- **Date:** 2026-09-10
- **Related / amends:** ADR-071 (reuses the ADR-033-deferred `parsing.tables`/`parsing.clauses`/`parsing.genre` layers, LD-F17), ADR-026 (the eight-stage connector contract), ADR-063/ADR-065 (registry review metadata + the gated `run --mode live|replay|shadow`, the content-free fetch record); RISK-P0-08, RISK-P21-16; SIG-INGEST-018/019/021/028/033/034, SIG-PARSE-001..008, SIG-PUB-002/003/004/006/007/008. Closes BL-023, BL-024, BL-026.

## Gate status (copied from the run contract)

- **HG-03 (≥1 OKC doc source green): SATISFIED.** RIGHTS.1 (P21.1 re-run, GL-GATE-03) flipped `okc_procurement`, `okcpd_policy`, and `ok_statute` to `ingestion_permitted=true` (CC0-1.0; government records / statutory text are public domain). `sig-connectors review-status --source <id>` reports all five gate fields True and `loadable now: True` for each.
- **HG-09 (`SIG_*` API tokens for the live smoke): NOT provided** (`provided: no`, per P23.4 / ACCT.1). The real live fetch of the cited documents cannot run in this isolated context, so this ticket implements the full fetch→OCFL→parse→emit code and proves it via **shadow replay** (diff = 0) against committed fixtures, and opens `D-LIVE.1a-1` (kind V, HG-09) for the real live smoke. No live green is fabricated.

## Context

The P06.1 vertical slice (`tests/acceptance/fixtures/okc_sources.json`) encoded three OKC document sources the dossier asserts claims for but **no live connector exercised**: `okc_procurement` (the Flock Master Agreement C241032 family), `okcpd_policy` (the OKCPD Operations Manual §5-118 ALPR clause), and `ok_statute` (47 O.S. §7-606.1). LIVE.1 in the go-live spec is the P21.3 transport re-run **plus** these three document-connector modules P21.3 could not exercise; GL-META-00 split the new code (this ticket) from the transport re-run (P21.3, manifest row 73). Once RIGHTS.1 flipped the sources green (HG-03), the composed pipeline can fetch → capture → parse → emit the same claims the fixtures encode.

Two design questions had to be settled, both echoing ADR-071:

**One connector or three?** The three OKC sources reuse the same eight-stage machinery, the same sig-parsing layers, the same claim shape, and the same Part VIII guard. But each is a **distinct registry row** with its own predicate surface (a contract table vs a policy clause vs a statute), and the fixture→registry mapping test (`test_okc_slice_mapping.py`) already names three ids (`okc_procurement`, `okcpd_policy`, `ok_statute`). So the split differs from ADR-071's single connector.

**Where does Part VIII bind?** These are document connectors reading public records; the risk is not a coordinate leak but a *predicate/value* leak — a per-plate, per-trip, per-person, or per-search fact, or an un-gated person name — smuggled into a claim. The guard must run for every claim at the ingest boundary, mechanically, not per-source.

## Decision

1. **One shared base + three registered subclasses.** `connectors/src/connectors/okc_documents.py` owns all the shared machinery (the per-connector config from `data/okc_documents_vocab.toml`, the predicate allowlist, the Part VIII guard, the `okc_claim` shape, the genre re-derivation, and the two sig-parsing extractors) as `OkcDocumentConnector`. Three thin modules — `okc_procurement.py`, `okcpd_policy.py`, `ok_statute.py` — each `@register` a subclass whose `name` keys its config. Each is wired to its green registry source in `runner.CONNECTOR_FOR_SOURCE`. This keeps the eight-stage boilerplate un-triplicated while honoring the three distinct registry rows.

2. **The claims are read through the ADR-033-deferred parser layers (reused, not re-built).** A procurement document reaches the connector as an extracted text grid read by the layer-4 `pdf_table` engine (`parsing.tables`, `CELL` locators); a policy/statute document is prose organised into numbered clauses read by the layer-3 `pdf_text` clause locator (`parsing.clauses`, `BYTE_RANGE` locators). The document **genre is re-derived from the text** (`parsing.genre.classify_genre`) and a disagreeing fixture label is rejected — a document cannot be relabelled to unlock a predicate surface it does not belong to.

3. **The Part VIII guard runs for every claim, in `okc_claim`.** Three prongs, each enforced by the single builder every extractor routes through, so no per-source path can bypass them:
   - **No plate/trip/per-person data** (`assert_part_viii_safe`, §0.7 / §43.2, RISK-P0-08): the predicate id **and** the verbatim raw value are scanned for a forbidden token (plate / per-trip / per-person / per-search / travel-history / home-address), and a predicate that names a categorically excluded kind (`policy.publication.is_categorically_excluded`) is refused. The connectors emit institutional facts ONLY.
   - **The officer-naming gate** (`assert_person_naming_permitted`, §43.4): a person-naming predicate must pass the five-prong `policy.officer.evaluate_officer_naming` test with two independent written concurrences, or it is refused (default no-publish).
   - **The sensitivity tier travels with the claim** (§43.3): every claim carries its sensitivity class (C1 — institutional/public-record facts, no per-asset coordinate) and its geospatial publication tier (`policy.sensitivity.geo_tier_for`).
   A test fails if any prong is removed.

4. **Shadow replay is the proof, the live smoke is deferred.** The three connectors ship over committed fixtures under `tests/connectors/fixtures/okc/` (each a faithful transcription of the cited public document, with a `SOURCES.md` citing url + retrieval date). A shadow replay over each fixture is byte-identical (0 diffs, SIG-INGEST-019) and a replay is reproducible (SIG-INGEST-017). The real live fetch is operator-gated on HG-09 tokens (`D-LIVE.1a-1`); `run --mode live` for these now-green sources fetches through the shared politeness layer into the OCFL store (P21.3 owns the transport) — exercised by P21.3's re-run when tokens are present.

## Consequences

- The three sources the OKC dossier depends on now have real connectors: the slice's claims are reproducible from captured documents, not only hand-transcribed fixtures. BL-023/BL-024/BL-026 are closed (connector-code half).
- The Part VIII guard is a reusable, tested pattern for future document connectors: predicate/value token scan + categorical-exclusion + officer gate + sensitivity stamp, all in one claim builder.
- The live smoke remains owed (`D-LIVE.1a-1`, HG-09); the shadow-replay diff-0 proof is the compensating control until tokens are provided. The transport wiring re-run stays with P21.3 (`D-P21.3-1`/`D-P21.3-2`), which now has the connector code to exercise.
- No source was flipped (RIGHTS.1 owns that), no publish happened (LIVE.2/GATE-G2), and no non-OKC source was touched (SOURCES.1) — the out-of-scope list held.

## Alternatives considered

- **Extend the existing `pathways` connector with three more families.** Rejected: the pathways families are LINK-posture and epistemically-loaded (procured≠deployed); the OKC document sources are green public records with a different predicate surface and a different guard (Part VIII content, not deployment inference). Folding them in would blur two different epistemic contracts.
- **Reuse the `procurement` connector for `okc_procurement`.** Rejected: that connector writes the §11.11 Contract/FundingInstrument entity surface via API payloads (cooperative vehicles, USAspending sub-awards), a different shape than reading a captured contract *document* as a table through the parser layers; and it does not carry the Part VIII document guard.
- **One connector, three extractors (the ADR-071 shape).** Rejected here only for the module split (three registry rows, three names in the mapping test); the *implementation* still shares one base, so the boilerplate is not triplicated.

## Revisit trigger

Revisit if: (a) the real live smoke lands (HG-09 tokens provided) and the OCFL-captured document parses to a different claim shape than the fixture encodes (the fixture would then be corrected, append-only, and the shadow diff re-baselined); (b) an OKC document genuinely needs a person-named claim (the officer gate would then be exercised with real reviewer concurrences, not just refused by default); (c) a fourth OKC document source or a non-table/non-clause document kind (e.g. a scanned PDF needing OCR) is added, which would extend the extractor dispatch and possibly a new parser layer; or (d) the Part VIII forbidden-token set or the categorical-exclusion list changes, which is a versioned vocabulary migration (§20).
