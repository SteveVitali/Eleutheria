# ADR-212 — Truthful subject keys: pinned field sets and append-only re-keying (P35.24)

- Date: 2026-10-18
- Status: accepted
- Ticket: P35.24 (Round 11 / P35 sub-round 11B, manifest row `R11-L3-CP2` —
  owned findings **F-506** (S1, the subject-key collision defect) and
  **F-518** (S1, the dedup/parity obligation it violates); metric L2-M07,
  GQ-04/GQ-05, CONF-03b)
- Base: `r11/P35.22-truthful-claim-identity` (9959c491)
- Related: SIG-INGEST-003 (truthful ingest — a subject key names one real
  subject), SIG-INGEST-004 (dedup parity — emitter and sink derive the same
  key), SIG-IDENT-005/006 (scheme-qualified canonical keys), ADR-110 (the
  `entity_identity_key` uniqueness guard + race-safe mint), ADR-211 (the
  claim-identity classes whose digest the correction rows mint under),
  ADR-136/ADR-141 (the correction/recovery apply paths this run mirrors),
  GQ-04 (the I-placement check this lands — `fixing = ["P35.24"]`)

## Context

A `sig.connector.subject` value is supposed to name exactly one real
subject. Upstream, it did not: the key derivation concatenated whatever the
emitter happened to hold, and the composed fields were **not unique** for
several families:

- **Cameras (F-518 / L2-M07).** `traffic_camera:<source>:<target>:<ref>` —
  the declared `camera_ref` upstream is not unique per (source, target):
  5,278 stored keys folded ≥ 2 real cameras into one subject (the plan
  row's count — the true count is re-derived at run time, never assumed).
- **Atlas of Surveillance agencies (F-506).** `atlas:<agency>(:<family>)` —
  two states' coincidentally-equal agency strings merged into one subject.
- **Data Driven agency aggregates.** `data_driven:agency:<agency_id>` —
  collided across releases for the same reason.
- **Procurement contracts (F-506).** `contract:<source>:<external_id>` —
  legistar/civicclerk/primegov share the external-id space; two tenants'
  equal ids merged.

The spine's correction model makes a rewrite impossible anyway: stored
subject keys are identity-bearing values (`entity_identity_key`, ADR-110)
and claims are append-only. The truthful fix has two halves: (a) make key
composition a **declared, versioned grammar** — pinned field sets per
family, a scope rule, a `key_version` — so a future field-set change is a
declared new version, not silent drift; and (b) **re-key the already-
collided keys append-only** — correction claims split each collided key
into evidence-derived constituent subjects, the old binding stays in
history, and the current view reads truthful subjects.

## Decision

1. **The pin registry is committed TOML, mirrored into the spine.**
   `db/src/db/data/subject_key_pins.toml` (`sig.subject-key-pins/1`) is the
   single runtime source: per family it declares the ordered `fields` a
   current key composes from, the `scope` rendering
   (`kind = "scheme_prefixed"` — the scope field renders as TWO segments,
   literal scheme token + value, so current and legacy values are disjoint
   by construction; `absent` ∈ `unscoped|omit`), the `legacy_fields`
   arities that still parse (never minted), the `distinguish` selectors the
   collision scan re-derives (`predicate:<id>` / `context:<key>`), and the
   `split` shape (discriminator + constituent rendering). A `subject_key_pin`
   table seeds the same six pins so a recorded decision names the registry
   version it was minted under; UPDATE/DELETE on it is forbidden by trigger
   (append-only, P1–P3). No segment may contain `:` — mint fails closed, so
   positional parsing stays unambiguous.

2. **One derivation, both sides.** Emitters mint through
   `db.subject_keys.mint_subject_key` — `dot_511.py` (camera), `atlas.py`
   (state-scoped agency), `data_driven.py` (state-scoped agency),
   `procurement.py` (tenant-scoped `contract:` + the pre-existing
   `agenda_item:`/`agenda_document:` convention, now grammar-declared). The
   sink's mint path validates every stored value against the declared
   grammar (`validate_subject_value` in `claim_sink`): a malformed or
   drifted pinned-family key quarantines with
   `unknown_subject_scheme`-class rejection, never a silent write. Unpinned
   families pass through — the registry is deliberately partial and an
   unmapped prefix is not an error.

3. **Camera keys keep their shape; uniqueness is enforced per capture
   (GQ-04).** `traffic_camera:` stays the camera identity anchor — ≈232,000
   existing subjects live under it and a scheme change would fork them into
   permanent append-only twins (the existing `CameraRegistryEntry`
   comment's warning). The truthful fix for cameras is not a new shape: it
   is (a) `assert_unique_within` at emit — two upstream rows minting one
   pinned key inside a capture aborts the target run closed
   (`SubjectKeyCollision`, the I-placement GQ-04 hook, never a silent
   merge); and (b) the append-only split of already-collided stored keys.
   A target may still pin its ref field explicitly (`camera_ref_field`,
   P36.6) — an absent declared column fails closed as before.

4. **Scoped families mint `key_version = 2`.** `atlas:` gains
   `us.state_abbr:<state>` (absent → `unscoped`);
   `data_driven:agency:` the same; `contract:` gains `tenant:<tenant_id>`
   (absent → omit — single-tenant sources keep the legacy 2-segment shape).
   Stored legacy-shape values keep parsing (`legacy_fields`) — the slug-
   shaped seed convention (`contract:okc-flock-c241032`, arity-1) included —
   but are never minted again.

5. **The re-key run is a new write surface, not a rewrite.**
   `db/src/db/subject_rekey.py` + `sig-db subject-rekey` (default: plan
   only; `--apply` writes):
   - `collision_scan` re-derives collided keys from the LIVE spine via each
     pin's `distinguish` selectors — a key is collided when a selector
     shows > 1 distinct current value (camera: `camera_latitude`; scoped
     families: the scope value in `raw_context`). The 5,278 figure is a
     planning number; the run measures the real count and any drift is a
     finding.
   - `plan_subject` groups the key's current claims into per-upstream-
     record evidence bundles (`capture_id` + locator; evidence-less
     assertion claims form singleton bundles) and clusters bundles by the
     pin's discriminator: camera bundles cluster on their coordinate pair
     (`split.shape = "suffix_digest"` → `:s<n>` constituent suffix —
     deliberately NOT a guessed upstream ref); scoped families cluster on
     the evidenced scope value (`shape = "current_fields"` → the current
     grammar with the evidenced scope). Claims whose bundle carries no
     usable discriminator stay on the legacy key — `unplaced`, never
     guessed.
   - `apply_subject` runs one transaction per subject key (an interrupted
     run resumes): each moved claim closes (`sys_period` end — the only
     UPDATE the run issues, the spine's current-view mechanism) and the
     corrected row appends under the constituent entity (minted through
     `resolve_identities` under the identity guard) with `revises_claim` +
     `correction_reason = 'subject_rekey_constituent'` + an identity-class
     `content_digest` (ADR-211's P35.22 digest, `payload_version =
     'sig.claim-payload/1'` — volatile correction linkage never enters it).
     Every `claim_evidence` row re-binds to the new claim id verbatim. One
     `subject_rekey_decision` row per (old value, constituent) records the
     discriminator, claims_moved, run id and registry version —
     `UNIQUE (scheme, old_value, new_value, registry_version)` is the +0
     rerun barrier (`INSERT … ON CONFLICT DO NOTHING`). Decision rows are
     immutable by trigger.
   - The run mints its own `ingest_run` (`subject-rekey/1.0.0`) and reports
     `sig.subject-rekey/1` — pre/post collision counts, per-key plans and
     tallies; dry-run touches nothing (verified: no run row, no decisions,
     every claim still current).

6. **The hosted run and the disclosures are queued live legs.** The
   `live_verification=false` invocation lands machinery only: the hosted
   apply, the `/status/` API-basis notice (S6 A-20 — the dedup-behaviour
   change posts when the behaviour actually lands on the hosted spine,
   matching ADR-211's posture) and the post-run zero-collision verification
   leg are queued under OM-19/OM-20 with the verbatim
   `live_verification=true` re-run prompt. The OM-20 pre-authorisation
   scope: one hosted re-key run appending correction claims + subsequent
   ingest under pinned keys + the `/status/` notice — recorded in the run
   ledger, never implied executed.

## Deviations and contract-artifact gaps (recorded, not silent)

- **Camera constituent keys carry `:s<n>` suffixes, not upstream refs.**
  The collided key's own camera_ref field was non-unique by definition —
  reusing it (or guessing a better field) would falsify the fix. The
  suffix is stable (sorted discriminator order) and the decision row
  records the coordinate discriminator each constituent evidences; a
  truthful upstream ref is re-pinned later only if the registry declares
  one — never assumed here.
- **`correction_reason` value.** `subject_rekey_constituent` is a new
  reason string; the closed `vocab`-style column is free text, so no
  vocabulary row is needed — recorded.
- **`entity_identifier` vs `entity_identity_key` in scans.** The collision
  scan reads `entity_identity_key` (the guarded identity index) while
  tests read `entity_identifier` (the read surface) — the guard keeps them
  consistent (ADR-110); the scan keys on the guard table because that is
  the uniqueness contract being measured.
- **`subject_key_pin` is a mirror, not the source.** The TOML is the
  runtime grammar; the table exists so decisions name a version and the
  verify script can assert the mirror (6 pins, one registry version). A
  grammar change is a new TOML version + a new sqitch change appending
  seeds — never an edit of landed rows.
- **No GQ-04 spine evaluator is added.** GQ-04's placement is `I`
  (ingest-time) — the evaluator is `assert_unique_within` at emit +
  `validate_subject_value` at sink; the stored-collision count lives in
  the re-key run's own `sig.subject-rekey/1` report, not the probe runner.

## Consequences

- Two tenants' equal strings produce distinct scoped keys at emit; scoped
  keys never collide across tenants/states (tested).
- A drifted/malformed pinned-family value quarantines at the sink — the
  parity defect class (emitter/sink divergent derivations) is now a
  single shared function.
- A per-capture duplicate mint fails the target run closed — the 5,278
  defect class can never re-enter through this connector.
- Collided stored keys split append-only: history keeps the old binding
  (closed claims + decisions), the current view reads truthful
  constituents, and a rerun of an applied run is +0.
- Unplaced claims are a reported residual, not a silent loss — the
  decision log + report count them per key.
- Downstream: P35.25's `derived_from_claim_ids` lineage binds claims whose
  subjects are now truthful (CP-4 sequencing on CP-2); the merge/alias
  consequences of split subjects are P35.57's lane.

## Revisit trigger

Revisit when (a) the registry bumps to `sig.subject-key-pins/2` — a new
grammar version is a new ADR or an explicit amendment with its own
registry version, never silent drift; (b) a family declares a truthful
upstream ref the suffix constituents could be re-pinned to (a second
re-key generation under a new decision basis); (c) a new pinned family
needs a discriminator neither `coordinate_pair` nor `context:` expresses;
or (d) P35.57's merge/alias surface makes `sig.connector.subject` values
non-canonical for split constituents.
