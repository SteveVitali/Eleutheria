# Intake receiver operating packet (P32.16 / ADR-135, SIG-FIND-006)

**Status:** prepared, **not ratified**. The durable anonymous correction
receiver is *built*; it is **not operating** and must not be advertised as
operational until every gate below is satisfied. This packet is the evidence
an operator reviews to flip it on — it describes the deployment the code
supports, the obligations that are the operator's (not the code's), and the
honest-statement rules for every public surface.

## 1. Gate statement

| Gate | State | Owner |
|---|---|---|
| `D-R10-PUBLISH-1` (GATE-G3 → P32.25 public-exposure approval) | **OPEN** | human decision |
| Staffed moderation owner (`ops/config.toml [intake].owner`) | unnamed | operator |
| Reviewer rotation covers published response SLAs (`[intake].staffed`) | `false` | operator |
| Retention schedule ratified (`[intake].retention_*` mirrors `intake_receiver.toml`) | values recorded, ratification pending | operator |
| Secrets provisioned (`SIG_INTAKE_FORM_SECRET`, `SIG_INTAKE_ABUSE_SECRET`) | env-only, never files (HG-09) | operator |
| Receiver DB login granted `sig_intake_receiver` membership | pending | operator |
| Reviewer DB login granted `sig_intake_reviewer` membership | pending | operator |
| Infra identifier-retention exclusions proven (§7) | pending | operator |

`[intake].operational = false` stays committed until every row above is green.
The app *enforces* this: accepting a report requires
`SIG_INTAKE_OPERATIONAL=1` **and** the committed flag **and** a non-empty
owner; anything less answers `receiver_not_operating` and the public page
states the receiver is not yet operating.

## 2. Process and privilege matrix

| Process | Command | Bind | DB role | Can reach |
|---|---|---|---|---|
| Public read API | `sig-api serve` | as deployed | `sig_read_public` | released views only — **no intake grants at all** |
| **Receiver (new)** | `sig-api serve-intake` | public port (operator-chosen) | `sig_intake_receiver` | INSERT report/receipt/contact/`received`-event; SELECT `intake.report_public` + receipt digest columns. **No claim/review/disposition grants — proven in `tests/db/test_intake_pg.py::test_receiver_role_isolation_matrix` + `::test_receiver_cannot_actually_write_canonical`.** |
| Curation (moderation) | `sig-api serve-curation` | **loopback only**, `SIG_CURATION_ENABLED=1`, bearer auth | `sig_intake_reviewer` (intake paths) | SELECT intake payloads/events, INSERT reviewer events, EXECUTE `redact_report`/`expunge_report`. No canonical writes. |

The event writer-guard trigger reads `current_setting('role')`, so the
boundary is the session role, not just grants: `received` exists only under
`sig_intake_receiver`, every reviewer event only under `sig_intake_reviewer`,
and `applied`/`published` are refused for **every** current role (reserved
for the P32.16a authorized bridge).

## 3. Network profile and egress

- The receiver makes **zero outbound calls**. Submitted `evidence_urls` are
  stored as untrusted text references; the receiver never fetches them
  (tested: private/loopback/link-local/credential-bearing and non-https URLs
  are refused at intake).
- Recommended perimeter posture: the receiver behind the same TLS/reverse
  proxy as the read API, egress-deny for its address, rate-limit at the edge
  *in addition to* the in-app token buckets.
- No CORS headers are emitted — there is no cross-origin write by default;
  Origin + Fetch Metadata are validated when a browser supplies them.

## 4. What the receiver stores (and never stores)

- Stores: the allowlisted fields only — category, optional release/record/
  claim references, a ≤4000-code-point narrative, ≤3 https references, an
  optional legal-demand contact (separate restricted table), the idempotency
  key, and the SHA-256 digest of the one-purpose status token.
- Never stores: the status token itself, IP addresses, user agents or any
  durable network identifier, upload bodies, or any field outside the
  allowlist. Refused payloads are never persisted anywhere (asserted by
  tests) and never echoed back unescaped.
- App logs must carry receipt ids only — request bodies, contact and
  network identifiers are redacted by construction (the app never reads IP
  or UA headers for storage or logging). The operator's own logging
  pipeline must honor the same exclusions (§7).

## 5. Receipt semantics

- `rct-<32-hex>` receipt id + a ≥128-bit status token, shown **once** to the
  reporter. Only the keyed digest is stored.
- Status checks are `POST /intake/v1/status` with receipt+token in the body
  — **never** a URL token (no referer/history/analytics leak). Comparison is
  constant-time; failed lookups are rate-limited; receipts are
  non-enumerating.
- Public status shows only the coarse state (`received / under_review /
  decided / resolved / closed`) plus a reviewer-approved `public_response`.

## 6. Moderation workflow (loopback only)

- `GET /v1/curation/intake` — bounded pending queue (oldest-first).
- `GET /v1/curation/intake/<receipt>` — full restricted view: payload,
  contact, append-only event log.
- `POST /v1/curation/intake/<receipt>/events` — append a lifecycle event.
  Tier-enforced: triage/assign/review-request/propose need a reviewer actor;
  `disposition_approved` and `closed` need a curator actor; every event must
  follow the transition table (invalid → 409), and an approval must name the
  proposal it approves (`approves_seq`).
- `POST /v1/curation/intake/<receipt>/redact` — irreversible field redaction
  via `intake.redact_report` (audited).
- A disposition is only a decision record. **No application exists here** —
  `BeliefLog.correct` is never invoked by the receiver or this surface; the
  authorized correction-application bridge is P32.16a (SIG-FIND-008).

## 7. Operator obligations outside this repo

Proven in code vs. owed by the operator — the privacy claims in §4 are true
of the application; the deployment proves the rest:

- **DB logins**: create the receiver login, `GRANT sig_intake_receiver TO
  <login>`; reviewer login → `GRANT sig_intake_reviewer`. (The roles are
  NOLOGIN groups by design.)
- **Infra log retention**: load balancer / proxy / monitoring / platform
  logs may hold IP+UA outside app control. Enumerate them, pin retention,
  and record the exclusions before claiming "no durable network
  identifiers" publicly.
- **Backup posture**: intake tables are inside PG backups; the retention
  schedule in §8 applies to live rows — backup expiry/rotation is an
  operator policy to ratify and record.
- **Secret management**: `SIG_INTAKE_FORM_SECRET`, `SIG_INTAKE_ABUSE_SECRET`,
  the DB credentials and the curation bearer are environment/injector
  secrets (HG-09) — never in files, never in the repo.
- **No-anonymity claim**: the site must never promise anonymity it cannot
  prove. The honest line: "we do not ask who you are and we do not store
  network identifiers in the report system" — which the schema enforces —
  not "you are anonymous".

## 8. Retention and purge (operator-ratified schedule)

- Payloads: expunge **30 days after final disposition**
  (`disposition_approved`/`closed`) — blanked fields + `expunged_at`, the
  audit row retained (expunge is content-clearing, not row deletion).
- Undecided reports: flagged **past the 90-day review/reminder ceiling** —
  never silently expunged; the sweep reports them for a reviewer decision.
- `legal_hold`: only an authorized reviewer event carries it; held rows are
  skipped by the sweep and reported (`legal_hold_skipped`).
- Run: `sig-api intake-purge --dry-run` (default) then `--apply`, on the
  operator's schedule; the run's output is the audit trail. Values live in
  `policy/data/intake_receiver.toml [retention]`; `ops/config.toml
  [intake].retention_*` records the ratified mirror.

## 9. Failure and restart behavior

- A submission is durable only after the DB commit — a crash mid-submit
  cannot produce a half-report (single transaction).
- The receiver is stateless across restarts: receipts, idempotency dedupe
  and statuses survive process restart and redeploy (proven by
  `test_durable_submit_restart_receipt_moderation`: a fresh connection sees
  the committed report).
- Form tokens expire (policy-table TTL) and single-use idempotency keys make
  retries safe: a re-POSTed form returns the *same* receipt (201 duplicate),
  never a second report.
- If PG is unreachable the receiver answers 503 `persistence_failed` and
  never fabricates a receipt.

## 10. Abuse monitoring

In-app limits (policy table, code of record): 5 accepted reports/hour per
rotating abuse pseudonym (burst 3), 100/hour global, ≤24 h pseudonym TTL.
The pseudonym is an HMAC over (secret, day-bucket, peer hint) — it expires,
it is not logged durably, and there is no account or identity behind it.
The operator watches 429/403 rates and the `receiver_not_operating` floor at
the edge; sustained flooding is an edge-layer problem the packet does not
claim to solve in-app.

## 11. Publication and advertising

- Public surfaces state the receiver is **built, not yet operating** — the
  `/dispute/` page already does. Do not publish "report it anonymously and
  we'll act" copy until the §1 gate rows are all green.
- A report is never an automatic correction, suppression or takedown vote;
  every public mention keeps that sentence.
- `D-R10-PUBLISH-1` remains **OPEN**; engineering readiness (tests green,
  schema deployed) is *not* public-exposure authorization.
