# P32.2 — Typed-assertion field map (published before the adapters)

Ticket: `docs/tickets/162_P32.2__typed-claims-and-capture-bindings.md` — SIG-TRUST-001 / SIG-TRUST-002.
Base: `devin/p32-1-baseline-and-memory-audit` @ `ebd34ce`.

This is the contract-ordered mapping the ticket requires **before** the
connector→sink adapter is built: every field the production assertion interface
must preserve, where it lives in the LinkML model and the physical schema today,
and what (if anything) is added. Nothing here guesses predicate semantics;
unregistered predicates fail closed into `assertion_quarantine`.

## 1. Assertion envelope → `claim` (every field preserved)

`sig.assertion/1` is the versioned production envelope (`db.assertion`). Each row
below is: envelope field → LinkML slot (`ontology/schema/entities.yaml` `Claim`)
→ physical column → disposition. `claim` columns already exist for almost
everything; the only new claim columns are the **explicit default provenance**
required by SIG-TRUST-001 ("a named versioned mapping and an explicit basis").

| envelope field | LinkML `Claim` slot | physical column | disposition |
|---|---|---|---|
| `subject_ref` → subject entity | `subject` | `claim.subject_id` | existing; resolved by the sink's identity path |
| `predicate_id` | `predicate` | `claim.predicate_id` | existing; `vocab_predicate` membership is the registered check |
| `object_type` | — *(added)* | `claim.object_type` | existing column; envelope carries it declared, never inferred |
| `object_entity_ref` | — *(added)* | `claim.object_entity` | existing; `record_object_ref`, never `person` |
| `value_kind` | `value_kind` | `claim.value_kind` | existing enum (`value`\|`somevalue`\|`novalue`) |
| `value_text` / `value_num` / `value_bool` / `value_geom` / `value_json` | `value` | same columns | existing; shape enforced by `claim_value_shape` |
| `unit` | — *(added)* | `claim.unit` | existing; `claim_unit_required` for `object_type='quantity'` |
| `raw_value` | `raw_value` | `claim.raw_value` | existing, NOT NULL — the source's literal text |
| `raw_context` | — *(added)* | `claim.raw_context` | existing jsonb citation anchor |
| `normalization_id` / `normalization_version` | — *(added)* | same columns | existing; `vocab_normalization` FK |
| `valid_period` / `valid_edtf` / `valid_from_kind` / `valid_to_kind` | — *(added)* | same columns | existing T1; defaults are *explicit* (see §4) |
| `observed_at` / `observed_edtf` / `observed_at_kind` / `observed_unknown_reason` | — *(added)* | same columns | existing T2; replay preserves the original |
| *(system assertion time)* | — | `claim.sys_period` | DB-controlled T5; replay assertion time lands here automatically |
| `source_reliability` / `reliability_provisional` / `claim_directness` / `artifact_integrity` | — *(added)* | same columns | existing R/D/I axes; never defaulted to stronger |
| `legacy_source_tier` | — *(added)* | same | existing optional Tier A–F passthrough |
| `claim_polarity` / `rank` / `review_status` | — *(added)* | same columns | existing enums/defaults |
| `extraction` (method, extractor, config) | `extraction_method` on `Extraction` | `extraction.*` | existing; one row per (capture, run, method, config) |
| `asserted_by` / `assertion_rationale` | — *(added)* | same columns | existing; `claim_human_needs_rationale` |
| `derived_from_claim_ids` | `supersedes`/`derived_from_claim` edges | `claim.derived_from_claim_ids` | existing uuid[] |
| `revises_claim` / `retraction_of` / `correction_reason` | `supersedes` | same columns | existing self-FK correction links |
| `sensitivity_tier` | — *(added)* | `claim.sensitivity_tier` | existing; absent ⇒ envelope requires the field (see §4) |
| `compartment` (via rights) | — | *(no claim column — see §5)* | compartment is a licence fact on `rights_record`; the claim carries `rights_id` |
| `rights_id` | — | `claim.rights_id` | existing NOT NULL |
| `ingest_run_id` | — | `claim.ingest_run_id` | existing; replay run id, never the original |
| `content_digest` | — | `claim.content_digest` (`claim_content_digest` change) | existing; idempotency key, NULL on old rows |
| `provenance classification` | — | `claim_evidence.binding_status` + `evidence_capture.capture_classification` | legacy-vs-actual lives on the **binding/capture**, where it is true — not a blanket claim flag |
| `map_id` / `map_basis` | — *(added)* | `claim.assertion_map_id` / `claim.assertion_map_basis` | **NEW columns** — the named versioned mapping + basis |

## 2. Evidence binding → `claim_evidence` (the actual capture consumed)

SIG-TRUST-002: every new claim and live re-sighting binds the **actual captured
artifact** the extractor consumed. `claim_evidence` already models the link;
P32.2 populates the columns that existed but were never written and adds the
extractor/config identity the link was missing.

| binding field | physical column | disposition |
|---|---|---|
| capture occurrence id | `claim_evidence.capture_id` | existing PK part; the adapter resolves the **real** `evidence_capture` row (live) or the marked original occurrence (replay) |
| digest / bytes / source | `evidence_capture.content_digest` · `byte_size` · `source_uri` · `blob_digest` | existing; `evidence_blob` dedups bytes — identical bytes ⇒ **one blob, two capture rows** (two immutable occurrence ids) |
| retrieval (source observation) time | `evidence_capture.retrieved_at` | existing; replay binds the *original* occurrence, so this stays the original time |
| OCFL object/version | `evidence_capture.ocfl_object_id` · `ocfl_version` | existing; `OcflCaptureStore` gains **version-pinned** `get`/`metadata` (no mutable head) |
| capture classification | `evidence_capture.capture_classification` | **NEW** — `actual`\|`synthetic`\|`legacy`; existing rows backfilled honestly |
| extraction id | `claim_evidence.extraction_id` | existing column, **previously unwritten** — now populated |
| typed locator | `claim_evidence.locator` | existing jsonb, **previously unwritten** — `parsing.locator` shapes only; `document_only` when no finer anchor exists |
| extractor identity/config | `claim_evidence.extractor_version` · `extraction_config_digest` | **NEW columns** |
| binding status/time | `claim_evidence.binding_status` · `bound_at` | **NEW columns** — `actual_capture`\|`replayed`\|`document_only`\|`legacy_synthetic` (default covers all old rows) |
| role | `claim_evidence.role` | existing `vocab_evidence_role` (`establishes`\|`contradicts`\|…) |

The synthetic per-(source, genre, run) capture (`sig:connector:…` artifact) is
retained only for the legacy path and is classified `synthetic` — it is never
presented as the actual bytes.

## 3. Qualifiers → `claim_qualifier` (the six mapped categories)

`claim_qualifier` exists (`claim_id`, `qualifier_id` → `vocab_predicate`,
`value_text`, `value_num`, `value_entity`, unique on
`(claim_id, qualifier_id, COALESCE(value_text,''))`) — **defined but never
written**. P32.2 writes it and adds the columns the six categories need:

`+ value_bool` `+ unit` `+ jurisdiction` `+ valid_from` `+ valid_to`
`+ extraction_id` `+ rank`; the unique index is widened to cover numeric/entity/
bool so two differently-typed qualifier values cannot collide.

| ticket category | qualifier key family (`vocab_predicate`) | value columns used | coverage |
|---|---|---|---|
| dossier instrument lifecycle | `qual.instrument.*` (e.g. `qual.instrument.stage`, `qual.instrument.effective_date`) | `value_text` / `value_num` + `valid_from`/`valid_to` | full |
| execution evidence / status | `qual.execution.*` (e.g. `qual.execution.status`, `qual.execution.witnessed_by`) | `value_text` / `value_entity` + `extraction_id` | full |
| monetary amount / currency / period | `qual.money.amount`, `qual.money.currency`, `qual.money.period_*` | `value_num` + `unit` + `valid_from`/`valid_to` | full (amount+currency as two qualifiers on the claim; period via the valid columns) |
| actor roles | `qual.actor.role`, `qual.actor.ref` | `value_text` / `value_entity` | full; `value_entity` never `person` |
| capability / modality | `qual.capability.*`, `qual.modality.*` | `value_text` | full |
| clause exceptions; applicability jurisdiction / time | `qual.clause.exception`, `qual.applicability.jurisdiction`, `qual.applicability.*` | `value_text` + `jurisdiction` + `valid_from`/`valid_to` | full |

Unregistered qualifier keys are never guessed: the qualifier fails closed
(quarantine entry naming the claim) while the claim itself still lands —
an unregistered qualifier cannot make a valid claim or entity disappear.

## 4. Defaults — named, versioned, basis-labelled (SIG-TRUST-001)

Every default the adapter applies is recorded on the claim row:

- `assertion_map_id = 'sig.assertion.map.v1'` — the named versioned mapping.
- `assertion_map_basis` — the basis string for how missing fields were derived,
  e.g. `connector_record` (everything came from the record), `capture_retrieved_at`
  (observed time derived from the binding's retrieval time), `legacy_synthetic`
  (the no-capture path), `replay_of:<run_id>`.

Rules the adapter enforces:

- **Sensitivity never lowers.** Absent `sensitivity_tier` ⇒ `0` only when the
  connector declared a tier for the source; a record carrying a nonzero tier is
  preserved verbatim. There is no silent "upgrade" either — the field is required
  in the envelope or the assertion quarantines as `missing_required_field`.
- **No stronger evidence.** `claim_directness`, `source_reliability`,
  `artifact_integrity` default only to the *weakest* honest value the mapping
  declares (record → connector genre default → quarantine), never inferred upward.
- **Valid/observed time stays honest.** Absent ⇒ `unknown` kinds + NULL/`unbounded`
  period (the existing defaults), with the basis string saying so — never
  fabricated dates.
- **Unknown predicate/type ⇒ fail closed.** Unregistered `predicate_id`,
  `object_type`, or `value_kind` does not write a claim; it appends an
  `assertion_quarantine` row (reason, run lineage, full payload) — the entity's
  other claims still land and still serve.

## 5. What is NOT added (deliberate)

- **`claim.compartment`** — no new column. Compartment is a licence fact owned by
  `rights_record` (the claim already carries `rights_id`); a parallel compartment
  column would fork the §42 model. The envelope surfaces the rights record's
  compartment through the existing join. Recorded as a reviewed decision, not an
  oversight.
- **Person entities** — never created (Part VIII); `qual.actor.ref` and
  `object_entity_ref` refuse `person` in the identity guard (unchanged).
- **No mutable "latest" sidecar reads** — `OcflCaptureStore.get/metadata` accept
  a version pin; bindings carry the OCFL version at assertion time.
- **No changes to old rows' meaning** — `binding_status` defaults
  `legacy_synthetic`; `capture_classification` backfills only what is provable
  (`synthetic` for `sig:connector:` artifacts, `actual` for byte-bearing real
  captures, `legacy` for the unverifiable remainder).

## 6. Failure/quarantine vocabulary (`assertion_quarantine.reason`)

`bad_digest` · `unknown_predicate` · `unknown_object_type` · `unknown_value_kind`
· `missing_capture_binding` · `unsupported_locator` · `extractor_failure` ·
`version_mismatch` · `missing_required_field` · `unknown_qualifier`

Each row: `run_id`, `received_at`, `reason`, `connector_name`, `source_id`,
`subject_ref`, `predicate_id`, `payload` (the full rejected assertion, jsonb),
`payload_digest` (idempotency). Quarantine rows are append-only and are **not**
public-read surfaces — unknown content is auditable by internal/restricted roles,
never exposed to `sig_read_public`/`sig_export`.
