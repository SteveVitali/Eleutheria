# ADR-079 — The second jurisdiction: France (Commune de Gex, vidéoprotection) through the P18.1 adapter framework — generalised seed/export/dossier seams, committed fixtures, and the recorded DECP rights gap (vs a new jurisdiction framework or a relabelled OKC copy)

- **Status:** Accepted
- **Phase / ticket:** P24.6 — second jurisdiction (JURIS.2 / GL-JURIS-01)
- **Date:** 2026-09-13
- **Related:** ADR-045 (the P18.1 jurisdiction-adapter framework this reuses, not
  rewrites), ADR-046 (the P18.2 `france_belgium` connectors + the
  `fr.arrete_prefectoral`/`fr.cada` vocabulary), ADR-049 (licence compartments —
  the ODbL graph split this preserves), ADR-066 (`run_okc.sh`, the template this
  runs alongside), SIG-ONTO-068 (non-US vocabulary — never `us.*`/`foia_request`),
  SIG-ONTO-032 (`cooperative_piggyback` + `parent_cooperative_contract`),
  SIG-LIC-004/SIG-EXPORT-005 (UNDETERMINED fails the export gate closed),
  SIG-PUB-017 (jurisdiction-conditional publication — the FR-GDPR officer-name
  withholding), HG-03/HG-04 (operator gates — nothing flipped, nothing fetched),
  `docs/tickets/DEFERRALS.md` D-JURIS.2-1/-2; the defining standard (D7: "the
  second jurisdiction is the design's proof, not a copy").

## Context

JURIS.2 asks for a second jurisdiction ingesting → resolving → publishing with
its own acceptance queries green — proving the evidence-first, append-only
design generalises beyond the Oklahoma City baseline. The contract names the
constraints: reuse the P18.1 adapter framework (no rewrite); rights packets for
the new jurisdiction's sources with `ingestion_permitted=false` and `provided:
no` (HG-03/HG-04 stay operator gates); a `run_<juris>.sh` templated from
`run_okc.sh`; OKC-specific assumptions surfaced; Part VIII binding on the new
jurisdiction's data.

The build-time survey found the reusable machinery already in place: the
`france_belgium` connectors (records + procurement), the `fr.*`/`be.*`
vocabulary, the FR/BE publication profiles (FR-GDPR/BE-GDPR), and one rights
packet (`raa_prefectures.md`). What did not exist: committed run fixtures, the
source→connector run mappings, a France slice in `sig-ops seed`, a France export
request, a France dossier, France-shaped acceptance queries, and the run script.

**Jurisdiction selection.** The spec defers final selection to the operator
(non-blocking): the recorded build-time candidate is **France — Commune de Gex,
département de l'Ain (vidéoprotection)**. Rationale: §52 Phase 18 names France
"the recommended first non-US adapter"; the committed P18.2 test vectors already
exercise Gex/Préfecture de l'Ain, so the slice is grounded in recorded fixtures
rather than invented data; and France exercises the shapes D7 demands — an
**arrêté préfectoral** (dated, five-year-renewable authorization — a shape OKC
has no equivalent of), the **DECP national open-data procurement** index (not
municipal portals), and the **fr.cada** records regime (not `us.foia`). Belgium
is the weaker candidate: its declarationcamera.be register sits behind an eID
wall (`no_equivalent_available`) — a true known-complete-unknown but less
pipeline to exercise. If the operator selects a different jurisdiction, the
dispatch tables added here make it a data row, not a code path.

**OKC-specific assumptions surfaced (recorded, per the contract):**

1. `sig-ops seed`/`up --seed` refused any jurisdiction but `okc`.
2. `sig-exports build --jurisdiction` refused non-`okc`
   (`_jurisdiction_request`).
3. `exports.web_dossier.build_web_dossiers` refused non-`okc`.
4. `tests/acceptance/live_api.py` is OKC-shaped (the seeded deployment subject,
   the J-1 slice traversal, the 299-vs-190 contradiction).
5. `connectors.runner.CONNECTOR_FOR_SOURCE` had no `france_belgium` source ids.
6. The jurisdiction filters (`reconcile resolve`/`sig-resolution match`) match
   `entity_identifier.value ILIKE '%<j>%'` — generic, but subjects must carry
   the jurisdiction token.
7. `web/src/lib/data.ts` export-dir default (`exports/out/okc`) is env-driven
   (`SIG_EXPORT_DIR`) — already generic; its appended FR/BE demonstration
   dossiers are pre-existing and unchanged.
8. The §11.14 connector-emitted predicates (`instrument_type`, `enacting_body`,
   `acquisition_method`, `sunset_date`, …) are outside the resolver ruleset —
   `reconcile resolve` skips them, `/v1/resolution` 404s them. Recorded; the
   material-fact claims use registered predicates.

## Decision

**1. The France slice is a new seed row, not a new code path.**
`ops.seed` gains `_SEED_SLICES` — a `{"okc": …, "france": …}` dispatch of
(claims, agency rows, extra identifier, connector identity). `sig-ops seed
--jurisdiction france` loads the France slice through the same append-only
`PgClaimSink`; the `okc` default is byte-identical. The France claims:

- subjects carry the `france` token (`sig:deployment:france-gex-videoprotection`,
  `contract:france:decp-2025kazvs0000000`, `legal_instrument:france:raa:arrete-01-2026-0451`,
  `jurisdiction:france`) so the ILIKE filters find them;
- material facts use resolver-registered predicates (`deployment_exists`,
  `authorization_state`, `statutory_citation`, `procurement_state`,
  `contract_value`, `contract_signed_date`, `implements_technology`) with
  admissible (genre × predicate) directness rows;
- the arrêté-derived claims carry `ODbL-1.0` (the RAA's recorded licence — the
  share-alike compartment), the DECP-derived claims carry `UNDETERMINED`
  (Licence Ouverte 2.0 is outside the accepted SPDX set — spine yes, export
  no), and nothing asserts a licence the registry does not record;
- the ER match scores two near-duplicate `fr.police_municipale` projections
  ("Police municipale de Gex" / "Police Municipale de la Ville de Gex") — the
  national-namespaced org type, never a widened `us.*` enum.

**2. The connector run path is data, not code.** `CONNECTOR_FOR_SOURCE` gains
four mappings — `raa_prefectures`/`madada`/`declarationcamera_be` →
`france_belgium_records`, `decp_fr` → `france_belgium_procurement` — and three
committed fixtures land under `tests/connectors/fixtures/france/` (the P18.2
test vectors recorded as fixtures: one arrêté, one CADA register row, two DECP
marchés — the second riding an accord-cadre → `cooperative_piggyback` with
`parent_cooperative_contract` set, SIG-ONTO-032). `madada` is recorded **refused
at the loader gate** (`compact_status=not_contacted`, `custody=LINK` — refuses
even a fixture run): that is the gate working in the second jurisdiction, not a
failure. Live is refused exit 3 on all four — HG-03.

**3. The export keeps the compartment discipline; the DECP gap is a recorded
absence, not a row.** `_jurisdiction_request` dispatches `okc`/`france`;
`_france_request` emits `legal_instruments` under `raa_prefectures` rights
(ODbL → its own compartment) and `claims` under `sig` (CC-BY). The DECP marché
content is deliberately absent — a `UNRESOLVED` dossier gap records it —
because an UNDETERMINED row would fail the export gate closed (SIG-EXPORT-005).
The second jurisdiction exercises the licence gate; it does not bypass it.

**4. The dossier is France-shaped, in French, and carries the FR-GDPR
withholding.** `_france_dossier()` emits `slug=gex-videoprotection`,
`jurisdictionCode="FR"`, `lang="fr"`, the twelve §39.2 sections, and a
signing-officer row flagged `isPublicEmployeeName` + `originJurisdiction:"FR"`
— which `applyPublicationPolicy` (SIG-PUB-017) **withholds** under FR-GDPR,
where the US dossier publishes the equivalent name. The row's value names the
office ("M. le préfet de l'Ain"), never an individual — Part VIII twice over.

**5. France has its own acceptance module, not a parameterised OKC one.**
`tests/acceptance/live_api_france.py` asks France's own questions (FR-1..FR-10:
"La vidéoprotection est-elle autorisée ?", the arrêté's legal regime, the DECP
marché value in the spine, the searchable police-municipale orgs, the
implemented technology, the publication gate on the export bytes) plus the
`arrete→deployment→dossier` traversal, and records the HG-03-pending carriers
(RAA corpus, Ma Dada register, the commune OSM layer) as `blocked` with the
exact commands. `run_france.sh` is the eight-stage template of `run_okc.sh` —
same stages, France's subjects and queries.

## Consequences

- The second jurisdiction runs end-to-end over fixtures: `run_france.sh` —
  `sig-ops up --jurisdiction france --seed` → three shadow connector runs (one
  honestly refused at the compact gate) → `sig-resolution match --jurisdiction
  france` → `reconcile resolve --jurisdiction france` → `sig-exports build
  --jurisdiction france` → web build from the export → FR-1..FR-10.
- The OKC path is byte-identical: `seed_jurisdiction(dsn)` defaults `okc`;
  `_jurisdiction_request("okc")` unchanged; `build_web_dossiers("okc")`
  unchanged; `live_api.py` untouched.
- The dispatch tables (`_SEED_SLICES`, `_jurisdiction_request`,
  `build_web_dossiers`, `CONNECTOR_FOR_SOURCE`) make a third jurisdiction a data
  row — the generalisation the contract asked for, without inventing a
  jurisdiction framework.
- The DECP rights gap is honest and visible: the claim sits in the spine, the
  export omits its content, the dossier records `UNRESOLVED`, and
  `decp_fr`'s packet flags the Licence Ouverte→SPDX mapping as counsel-needed
  (HG-02-adjacent).
- Owed operator work is registered: `D-JURIS.2-1` (HG-03 flips + real fetches of
  the three France sources), `D-JURIS.2-2` (HG-04 outreach to the FR source
  operators + Belgium's packet if Belgium lands); RISK-P24-04 records the
  jurisdiction-token filter coupling.

## Alternatives considered

- **Belgium as the second jurisdiction** — rejected as the build-time candidate
  (not ruled out): the declarationcamera.be register is eID-walled
  (`no_equivalent_available`) — a real known-complete-unknown but it exercises
  less of the ingest→resolve→publish path than the RAA/DECP/CADA trio. Its
  `be.loi_cameras` instrument + BE-GDPR profile remain seeded; the dispatch
  tables make it a future data row.
- **A new generic "jurisdiction" abstraction layer** — rejected: the contract
  forbids rewriting the P18.1 framework, and the adapters are already the data
  layer; the honest change was filling the OKC-shaped gaps, not inventing a
  framework for one more jurisdiction.
- **Parameterising `live_api.py` with a `--jurisdiction` flag** — rejected: the
  OKC questions (the 299-vs-190 contradiction, J-1's hop list) are not France's
  questions; a flag would pretend the queries are interchangeable. France's own
  module is the D7 posture.
- **Exporting the DECP marché under a guessed licence (e.g. CC-BY "close
  enough")** — rejected outright: the defining standard forbids asserting a
  licence the registry does not record; `UNDETERMINED` + a recorded gap is the
  honest shape.
- **Flipping `madada`'s compact_status to run its fixture** — rejected:
  `not_contacted` is the honest compact posture; changing it is a reviewer
  judgement (HG-03/04), not a code change. The refusal is the recorded evidence.
- **A shared `run_<juris>.sh` generator** — rejected: two jurisdictions do not
  justify a templating layer; `run_france.sh` stays a readable, editable script
  (the same call run_okc.sh made when it was one).

## Revisit trigger

Revisit this decision when any of the following holds:

- **The operator selects a different second jurisdiction** — the dispatch
  tables (`_SEED_SLICES`, `_jurisdiction_request`, `build_web_dossiers`,
  `CONNECTOR_FOR_SOURCE`) are the seam; a new jurisdiction is a new row + its
  rights packets + its acceptance module, not a framework change. If France
  loses to Belgium or another candidate, this ADR's candidate choice is what
  changes, not the machinery.
- **HG-03 resolves the DECP licence** (Licence Ouverte 2.0 mapped to an accepted
  SPDX expression or `licenses.toml` amended) — the DECP rows join the export;
  remove the `UNRESOLVED` gap then, never silently.
- **The §11.14 predicates enter the resolver ruleset** — `reconcile resolve`
  stops skipping `instrument_type`/`acquisition_method`/etc.; the acceptance
  module's recorded "out of ruleset" note becomes stale.
- **A third jurisdiction lands** — if the dispatch tables stop being sufficient
  (e.g. a jurisdiction needs non-claim seed rows), generalise then; do not
  pre-build the framework now.
- **The ILIKE jurisdiction filter proves too loose** (a jurisdiction token that
  collides with non-jurisdiction identifier text) — replace the filter with a
  structured scheme; RISK-P24-04 records the coupling.
