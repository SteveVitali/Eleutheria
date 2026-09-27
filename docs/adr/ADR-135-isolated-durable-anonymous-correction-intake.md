# ADR-135 — Durable anonymous correction intake as a separate receiver process over an isolated `intake` schema: receipts via POST-secret, private loopback-only moderation, `applied`/`published` reserved for the P32.16a bridge (P32.16)

- Date: 2026-10-18
- Status: accepted (engineering; **the receiver is built but NOT operating** — public exposure stays with GATE-G3 / D-R10-PUBLISH-1, which remains OPEN, and a staffed owner is still unnamed)
- Ticket: P32.16 (Round 10 / S4, row 176; requirement SIG-FIND-006)
- Base: the P32.15 chain tip `devin/p32-15-coordinated-investigation-workspace` (PR #171, stacked on P32.14 / PR #170)

## Context

The public `/dispute/` page described a submission path that did not exist:
`policy.CorrectionsIntake` is an in-memory model only, nothing durable
accepted a report, and no public process could safely take anonymous input.
S4's research (`S4-public-product.md` §8) specifies a **durable anonymous
correction receiver** with hard properties: bounded account-free reports,
durable storage *outside* the claim spine (unreviewed input must be
expungeable), a receiver role with **no** claim-spine or curator writes,
receipt secrets that never appear in a URL, private moderation on the
existing loopback curation surface, and a lifecycle that keeps
submission, decision, application and publication separate — a report is
never an automatic correction, suppression or takedown vote.

Three boundary traps had to be avoided by construction, not by convention:

- The public read API is read-only; mounting a POST there would breach it.
- The authenticated curation app is loopback-only with tiered write scopes;
  exposing it to the public or minting a receiver credential in its scope
  system would breach Part VIII §0.7.
- Anonymous input is hostile by default: plates, per-person/per-trip detail,
  script payloads, oversized bodies and unsafe URLs must be refused before
  anything is stored, and rejected content must never reach a public log or
  the claim store.

## Decision

**A separate public-facing receiver process (`sig-api serve-intake`) over an
isolated `intake` schema, with a session-role-enforced event boundary and a
private moderation surface on the existing loopback curation app.**

### 1. Storage (`db/sqitch.plan` → `intake_storage`)

A dedicated `intake` schema — deliberately outside the append-only claim
spine and the WORM evidence store because unreviewed input must be
expungeable — holds:

- `intake.report` — the quarantined payload. Identity columns
  (`report_id`, `receipt_id`, `idempotency_key`, `category`,
  `received_at`) are immutable by trigger; rows are never deleted; payload
  columns change only through SECURITY DEFINER maintenance functions.
- `intake.reporter_contact` — the legal-demand-only contact, a separate
  restricted table cleared wholesale by redaction/expunge.
- `intake.receipt` — the keyed digest (`bytea`, 32 bytes) of the
  one-purpose status token. The token itself is never stored; comparison is
  constant-time app-side and failed lookups are rate-limited.
- `intake.event` — the append-only restricted audit log
  (`received/triaged/assigned/review_requested/disposition_proposed/
  disposition_approved/closed` + housekeeping `redacted`/`expunged`).
  **`applied`/`published` are reserved for the P32.16a authorized bridge
  and refused by the writer guard for every current role** — the state
  machine cannot reach an applied state in this ticket, by schema, not by
  policy.
- `intake.report_public` — the definer-owned coarse projection (receipt id,
  category, received_at, lifecycle event → coarse state, and the
  reviewer-flagged `public_response` only). Raw narrative, contact, URLs
  and network identifiers are unreachable from it.

Two NOLOGIN roles: `sig_intake_receiver` (INSERT payloads/receipt/event +
SELECT the projection + the receipt digest columns only) and
`sig_intake_reviewer` (SELECT payloads + INSERT events + EXECUTE the two
maintenance functions). The **event writer guard reads
`current_setting('role')`**: a `received` event exists only under
`SET ROLE sig_intake_receiver` with the fixed actor, every reviewer event
only under `SET ROLE sig_intake_reviewer` — a stolen credential cannot
cross the boundary even where a grant exists. No existing role
(`sig_read_public`, `sig_read_restricted`, `sig_read_sealed`, `sig_export`,
`sig_ingest`, `sig_materialize`) holds any intake grant.

### 2. The receiver process (`api/src/api/intake.py`, `sig-api serve-intake`)

- `POST /intake/v1/reports` accepts `application/x-www-form-urlencoded` and
  JSON with the identical allowlisted contract from
  `policy/data/intake_receiver.toml`: expiring signed `form_token`,
  `idempotency_key`, `category`, optional `publication_id`/`record_key`,
  ≤10 public `claim_ids`, a 20–4000-code-point `description`, ≤3 public
  https `evidence_urls`, optional legal-demand `contact`. Unknown fields,
  uploads and oversized bodies are rejected; accepted reports return a 201
  with an opaque `rct-<hex32>` receipt + a single-use-purpose status token.
- `POST /intake/v1/status` — the receipt+token check **in the body** (never
  a URL, so receipts cannot leak via referer/analytics); token comparison
  is `hmac.compare_digest` over the keyed digest; the response is only the
  coarse state + an approved public response.
- `GET /intake/new` + `GET|POST /intake/status` — the no-JS HTML surfaces
  (no scripts, no third-party assets, `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer`), re-rendering safe fields escaped.
- The process needs `SIG_INTAKE_ENABLED=1` to exist at all, and
  `SIG_INTAKE_OPERATIONAL=1` + the committed `ops/config.toml
  [intake].operational` flag + a staffed owner to accept reports — the
  operating gate is enforced in code, not in prose. Until then every write
  returns `receiver_not_operating` and the form states the receiver is not
  yet operating.
- The receiver is **never mounted** on `create_app` and never reuses the
  curation app — separate process, separate port, separate role.
- Abuse: a rotating HMAC abuse pseudonym (per-deployment secret, ≤24 h
  TTL, no durable IP/UA storage), per-pseudonym and global token-bucket
  limits from the policy table, Origin/Fetch-Metadata validation when
  supplied, and no CORS headers (no cross-origin write by default).

### 3. Screening (`policy/src/policy/intake.py` + `intake_receiver.toml`)

Pure contract: field allowlist + bounds, URL validation (https only, no
credentials, no private/loopback/link-local hosts, no server-side fetch —
references stay untrusted data), the Part VIII screen (plates,
per-person/per-trip, identifying details, secrets, script/HTML payloads —
with separator-normalized matching so hyphen/underscore/space variants
cannot dodge it), the event vocabulary + lifecycle transition table
(`received → triaged → assigned/review_requested → disposition_proposed →
disposition_approved → closed`), the coarse public-state map
(`received|under_review|decided|resolved|closed`), and moderator detail
validation (`approves_seq` binds an approval to a live proposal).

### 4. Private moderation (`api/src/api/intake_moderation.py` on the curation app)

`/v1/curation/intake[...]` routes on the existing **loopback-only**
authenticated curation app: a bounded pending queue, full detail (payload +
contact + event log), event append with per-event actor-tier enforcement
(`disposition_approved`/`closed` need curator tier), invalid-transition
refusal as 409, and a redaction endpoint. The public status surface
updates only through these recorded events — no route ever mutates a
report row directly.

### 5. Retention + gates

`sig-api intake-purge` (dry-run default) applies the policy-table
retention: expunge payloads 30 days after final disposition, flag
undecided reports past the 90-day review ceiling, skip + report
`legal_hold` rows — every action lands on the audit log. The operating
packet (`docs/governance/intake-receiver-operating-packet.md`) records the
process/role/network matrix, the staffing + retention + disclosure
obligations, and the gate statement: **this receiver is not advertised as
operational while unstaffed or unapproved**; `D-R10-PUBLISH-1` stays OPEN.

## Alternatives considered

- **A POST route on the public read API.** Rejected — the read API is
  read-only by contract; a write path on it violates the Part VIII
  boundary and blurs the receiver's separate-blast-radius posture.
- **Reusing the curation app (or its credential system) as the public
  surface.** Rejected — curation is authenticated loopback-only with
  canonical write scopes; the public receiver must never hold them, so it
  gets its own process and its own DB role instead of a "narrow" share of
  the curator's authority.
- **Storing reports in the claim spine as pending claims.** Rejected —
  unreviewed input is not a claim and must be expungeable; the claim spine
  is append-only. The intake schema's separate lifecycle + retention is
  the honest model; application to the spine is the P32.16a bridge.
- **Receipt token in the URL.** Rejected — URLs leak through referer,
  history and analytics; the token travels in the POST body, its keyed
  digest only is stored, and failed lookups are rate-limited.
- **Enforcing event authority in grants alone.** Rejected — the receiver
  legitimately holds `INSERT` on `intake.event` (for `received`), so the
  writer guard enforces the session-role boundary for *which* event each
  role may append; grants alone could not distinguish the two.

## Consequences

- Reports are durable (real transactions, restart-proof — proven across
  fresh connections in `tests/db/test_intake_pg.py`), idempotent on
  `idempotency_key`, and opaque (unguessable receipt ids; no enumeration).
- A compromised receiver credential yields: inserting more reports and
  reading the coarse projection — nothing else. Canonical writes, review
  tables and restricted evidence are unreachable by construction.
- Public status leaks only coarse state + approved responses; the
  projection is the only readable surface for the receiver role.
- The lifecycle cannot reach `applied`/`published` until P32.16a mints its
  bridge role — the writer guard refuses those events for every role that
  exists today.
- Ops owes: the receiver login's role provisioning, log-redaction and
  infra-identifier exclusions (load balancer/proxy retention is outside
  this repo), the named owner, retention ratification and GATE-G3 — all
  recorded in the operating packet and `ops/config.toml [intake]`
  (`operational=false`, `owner=""`, `staffed=false` committed).

## Revisit trigger

Revisit when (a) P32.16a lands the authorized correction-application
bridge — its role must be added to the writer guard's `applied`/`published`
allow-list deliberately, never by loosening the guard for existing roles;
(b) the receiver's field contract needs a new field — the allowlist +
policy table + schema CHECK move together or not at all; (c) an operator
asks to advertise the receiver before GATE-G3 — the
`ops/config.toml[intake]` gate + this ADR's status make that a governance
decision, not a config flip; or (d) a jurisdiction requires different
retention — the policy table changes with a recorded reviewer-facing
extension path (`legal_hold`), never a silent extension.
