# ADR-034: The `records` connector — targeted-lookup posture, MuckRock api_v2 + short-lived JWT, and the `no_responsive_records` → coverage bridge

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P07.2
- **Requirement ids:** SIG-ONTO-040, SIG-INGEST-033, SIG-INGEST-034, SIG-INGEST-036, SIG-INGEST-037, SIG-TIME-011 (via `db.absence`), and the §23.5 `records` connector + §11.19 `RecordsRequest` entity/predicate requirements
- **Spec:** docs/2_canonical_design_spec.md §23.5 (`records` — MuckRock/NextRequest/DocumentCloud); §11.19 (`RecordsRequest` **[NEW]**, SIG-ONTO-040); §23.1 (universal connector rules); §26 (crawler conduct, SIG-INGEST-036/037); §9.5 (the four absence states / coverage model); §21.1 (the eight-stage `parse→extract→normalize` seam, ADR-026); research R4 F4.1/F4.2/F4.3 (the MuckRock api_v2 + JWT facts)

## Context

P07.2 adds the third source connector on the P04.1 framework — the **public-records
channel** (`records`: MuckRock, NextRequest, DocumentCloud) — and the runtime shape of the
§11.19 `RecordsRequest` entity. The channel is unlike `osm`/`atlas` in three load-bearing
ways, and each forced a decision:

1. **The APIs are rate-limited and auth-gated, and using them wrong is a *legal* posture,
   not an engineering choice (SIG-INGEST-036/037).** MuckRock is ~15 req/min with a 401 on
   every data endpoint; NextRequest/DocumentCloud are small civic hosts. §26 rule 5 (prefer
   the offered channel) plus the rate-limit rule mean these are **targeted lookups** for
   *known* requests/agencies/documents — never crawled or enumerated.
2. **MuckRock is `api_v2` with a five-minute JWT, and the outline's `api_v1` reference is
   wrong (R4 F4.1).** There is no unauthenticated read path (F4.2); tokens expire after five
   minutes and a "fetch a token at job start" design fails (F4.3). But connectors hold no
   HTTP client of their own — every egress goes through the shared politeness layer
   (SIG-INGEST-011). So *where does the credential attach?*
3. **`no_responsive_records` is a positive finding, not a null (SIG-ONTO-040).** An agency
   stating on the record that it holds no responsive documents (e.g. no ALPR contracts) is
   evidence and MUST feed the `NO_EVIDENCE_FOUND` coverage model (§9.5), not be discarded.

The §11.19 `RecordsRequest` schema, the `RecordsResponseStatus`/`RecordsPlatform` enums, and
the `CoverageRecord`/`EvidenceArtifact` classes already exist in the ontology (P01.1); the
four-state absence model already exists as tested code (`db.absence`, P02.3). So this ticket
owns the connector's **runtime** shape and the coverage bridge, not new schema.

## Decision

1. **The `records` connector is a targeted-lookup client, enforced in code.** `discover()`
   returns only explicitly-supplied targets, and `assert_targeted_lookup` refuses a target
   that would enumerate: a `mode` of crawl/enumerate/list/scrape, a pagination cursor
   (`page`/`cursor`/`offset`), or a bare listing endpoint (`/api_v2/requests/` with no
   specific id) — a target must name a request by `external_id`, an agency by `agency_id`, or
   a document by url. A `CrawlAttempted` is raised otherwise. The refusal is the SIG-INGEST-037
   legal posture in code: a deviation is an ADR with counsel, not a code change.

2. **MuckRock uses `api_v2` only, with a short-lived JWT that rides the shared egress seam.**
   `muckrock_endpoint` builds `https://www.muckrock.com/api_v2/<collection>/<id>/`;
   `assert_muckrock_api_v2` refuses any `api_v1` URL. `MuckRockTokenCache` wraps an injected
   `TokenSource`, mints a `MuckRockToken` with a 300-second lifetime, and **refreshes once the
   token is within a 30-second margin of expiry** (so the effective reuse window is < 5 min)
   and **on a 401** (`fetch` catches the framework's `ChallengeEncountered`, invalidates, and
   retries exactly once; a second failure propagates to the disappearance layer unchanged —
   this is not challenge-solving). The concrete token mint (a POST of username/password to
   `accounts.muckrock.com/api/token/`) is left to the ops/live-run layer, exactly as
   `connectors.net.Transport` injects the concrete HTTP client — here it is the seam the cache
   refreshes through, so the TTL / refresh-on-401 logic is deterministically testable.

3. **DEVIATION: `connectors.net` gains an optional per-request `headers` argument** on
   `PoliteFetcher.fetch`, the `Fetcher`/`Transport` protocols, so the JWT rides the **single
   shared politeness layer** rather than a records-specific HTTP client (SIG-INGEST-011). It is
   additive and back-compatible: `headers` defaults to `None`, and the fetcher passes it to the
   transport **only when present**, so a transport predating the seam (taking only
   `user_agent`) keeps working unchanged. Supplying a credential this way is *authentication*,
   never access-control circumvention (Rule 4 / SIG-INGEST-013): the connector never solves a
   challenge, rotates identity, or bypasses a paywall.

4. **`no_responsive_records` writes a `CoverageRecord` by reusing `db.absence`.**
   `coverage_record_row` maps the positive finding onto `AbsenceState.NO_EVIDENCE_FOUND`
   (`coverage_record.absence_kind = 'searched_not_found'`) via the canonical §9.5 model, and
   `render_absence` enforces SIG-TIME-011 — the record MUST name the sources searched, and an
   empty set is rejected. This is the bridge P09.1 (the full coverage model) and P10.3 (records
   as research tasks) both build on.

5. **The `RecordsRequest` runtime shape validates against the frozen enums; the connector
   emits candidates, never resolutions.** `RecordsRequest` carries the §11.19 predicate surface
   and rejects an out-of-vocabulary `response_status`/`platform` (lock-stepped to the ontology
   enums by a test). Its claim rows pass the **predicate allowlist** (SIG-INGEST-033): the
   connector may write only the `RecordsRequest` surface plus the released-document link;
   a procurement value, a deployment, or a parsed-document claim is refused at ingest. Party
   predicates carry a **candidate identifier** (`muckrock.agency` for a numeric id, the
   `records.agency_name` surrogate otherwise), never a resolved entity id (SIG-INGEST-034).

6. **Released documents are captured as `EvidenceArtifact` rows and linked; the P07.1 parser
   is *called*, not run.** Each released document is captured (framework `capture()`), given a
   stable `EvidenceArtifact` id keyed on its source URI (so the request's `released_documents`
   links to it before the bytes arrive), and **classified** via
   `parsing.classification.classify` / `classify_archive` (a mixed-format ZIP is classified per
   member). The layered *extraction* of the document — the concrete PDF-text/table/OCR engines
   ADR-033 Decision 4 assigns to this ticket — is **deliberately not wired here**: §23.5 scopes
   P07.2 to capturing the *request* and its released *captures* and explicitly hands "the
   layered parsing of the released documents themselves" to P07.1's interface, so the connector
   records the routing verdict and defers running the engine to the point a claim must be
   extracted from a document (a follow-on within Phase 7/8). Each capture also emits a
   `CaptureQualityReport` alongside the ingest run record.

7. **`connectors` gains `sig-db` and `sig-parsing` as direct workspace dependencies.** Both are
   leaf packages that never import `connectors` (no cycle) and were already in the transitive
   closure via `sig-resolution`; declaring them directly makes the `db.absence` and
   `parsing.classification` imports honest. `pylock.toml` is unchanged.

## Consequences

The records channel now ingests through the same eight stages as every other source, but as a
lookup client that cannot be turned into a crawler by configuration, that authenticates to
MuckRock's api_v2 correctly and survives its five-minute token, and that turns an agency's
on-record "no responsive documents" into queryable evidence instead of a dropped null. The
`RecordsRequest` runtime shape and the `no_responsive_records` → coverage bridge are a stable
interface P09.1 and P10.3 depend on. Costs and deferrals, stated rather than hidden:

- **No live token mint and no real HTTP transport ship here.** `MuckRockTokenCache` refreshes
  through an injected `TokenSource`; the concrete POST to `accounts.muckrock.com` lands with
  the live transport wiring in `orchestration/`/`ops` (the same deferral `connectors.net` already
  makes for its HTTP transport). The TTL and refresh-on-401 logic is complete and tested.
- **No document-extraction engine ships here (per §23.5 scope + ADR-033 Decision 4).** The
  connector captures and *classifies* released documents (routing them to a layer) and links
  them to the request; running layer 3/4/5 to extract claims from a document is triggered when
  a document-derived claim is needed, behind the P07.1 interface. A mis-route of the scanned-PDF
  heuristic is corrected downstream, never a silent drop.
- **The `headers` seam on `connectors.net` is a framework change to a P04.1 module.** It is
  additive and back-compatible (default `None`, passed only when present), and it is the correct
  home for auth: the single shared egress seam. The alternative — a records-owned HTTP client —
  was rejected because it would break SIG-INGEST-011.
- **The records channel spans several REFERENCE-posture sources whose per-document rights
  vary.** Unlike `osm` (ODbL) and `atlas` (CC-BY), the connector does **not** stamp a single
  export compartment on its rows; the compartment is decided per source by the licence gate
  (SIG-LIC-009a). Each row records its `source_id` and the vocabulary version instead.

## Alternatives considered

- **A records-specific authenticated HTTP client.** Rejected: connectors hold no HTTP client of
  their own (SIG-INGEST-011); auth must ride the shared politeness layer, which is why the
  `headers` seam was added there instead.
- **Fetching a MuckRock token once per job.** Rejected: the token dies after five minutes and
  every subsequent data endpoint 401s (R4 F4.3); the cache refreshes early and on a 401.
- **Treating `no_responsive_records` as a null / not modelling it.** Rejected outright by
  SIG-ONTO-040 — it is the single most important record the channel produces for the
  negative-space surfaces (§32).
- **A bespoke coverage-record encoding in the connector.** Rejected: the four-state absence
  model already exists as tested code (`db.absence`); reusing it keeps the connector's coverage
  record identical to every other NO_EVIDENCE_FOUND finding and enforces SIG-TIME-011 for free.
- **Letting `discover()` page through a records listing.** Rejected: enumeration is prohibited
  and doomed at these rate limits, and the refusal is a legal posture (SIG-INGEST-037).

## Revisit trigger

Revisit if any of: MuckRock changes its auth model or api_v2 object model (the token host, the
five-minute TTL, or the endpoint set — re-verify against `accounts.muckrock.com` and the
`/api_v2/` router root); a records source's rights review resolves a per-source export
compartment that the connector should stamp (today it defers to the licence gate); the P07.1
document-extraction engines land and the connector must run a layer over a captured document
(Decision 6 / ADR-033 Decision 4); a records source publishes an offered **bulk** channel that
changes the targeted-lookup calculus (§26 rule 5); or SIG-INGEST-036/037's crawler-conduct
posture is amended (which is an ADR with counsel, per §26).

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger fired:** the live HTTP transport and the OCFL capture store landed (ADR-065), and
§26's crawler-conduct posture was amended (ADR-083, ADR-087, ADR-088; written into the spec by ADR-145)
without the counsel this trigger names (F3 §5.1). **Answer:** F3 classified this trigger as needing only a
recorded evaluation. The counsel condition cannot be met: SIG has no counsel (U-013), and Round 11 waives
SIG-INGEST-037's counsel clause (WV-07, ADR-182), so crawler-posture changes are recorded as the operator's
own determinations by ADR — GL-GATE-08 on every host (ADR-168), the terms-conflicted fetch envelope (ADR-184),
rule 6 for DocumentCloud/MuckRock (ADR-187) and the Flock portal probe (ADR-188); the crawler-policy text and
the rule-7 opt-out register are rows P36.1a/b. DocumentCloud/MuckRock documents get their own connector (row
P36.77) under ADR-184 and ADR-187; this connector's MuckRock targeted-lookup decisions are unchanged, and a
further §26 change re-arms this trigger. The decision above stays in force until that answer lands; this ADR's
body is unchanged (SIG-ENG-003).

## Status updates

- **Status:** Qualified by ADR-182 (2026-10-01)
- **Status note (2026-10-01T13:59:14Z, Round-11 T1, unit SEED-12c):** ADR-182 (WV-07; the operator's adopted sentence,
  agent-drafted and adopted at 2026-10-01T04:28:49Z, sha256 `c5a71e9d7fd9…`: *"I waive the counsel-review clauses of
  SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such."*) leaves
  this ADR's counsel-conditioned revisit clause unable to fire as written — SIG has no counsel (U-013; F3 §5.4,
  NEW-8). The clause: "SIG-INGEST-036/037's crawler-conduct posture is amended (which is an ADR with counsel, per
  §26)". Restated (agent reading, labelled): it fires when that posture is amended by an ADR resting on the operator's
  recorded determination — SIG-INGEST-037's ADR-level-decision rule stands, its counsel clause is waived — as the
  trigger evaluation above records for ADR-168, ADR-184, ADR-187 and ADR-188; or when counsel is obtained (LATER-05)
  or a first legal demand arrives (ADR-182's and ADR-166's triggers). The decision and the body above are unchanged
  (SIG-ENG-003).
