# ADR-203 — Protective seal: the two-carrier deny set and the counts-only at-rest audit (P34.49)

- Date: 2026-10-08
- Status: accepted
- Ticket: P34.49 (Round 11 / P34, row 254 — TS-07's at-rest half: F-406, the
  I7 S1–S9 screen classes, SIG-PUB-002 categorical listing; the sealing half
  of ADR-185's "existing bytes" rule)
- Base: `r11/P34.43-execution-host-and-least-privilege-db-logins-v2`
- Related: ADR-185 (the lanes + the sealing/listing rule this row engineers),
  ADR-181 + ADR-189 (true deletion is the operator's sole in-ticket action —
  this row deliberately carries no delete path), ADR-124 (the
  append-only-disposition discipline the deny set mirrors), ADR-202 (the
  execution host the scan leg runs on), ADR-006 (the write-once OCFL store
  the seal never mutates), SIG-STORE-011 (insert-only; the seal is a new row,
  never an edit), SIG-EVID-010 (the sealed representation's shape)

## Context

F-406 recorded that captures stored before the Round-11 ingest fixes may hold
Part VIII-prohibited material — OSM `user`/`uid` identity metadata (the
`out meta` query shape; presence inferred, never read from bytes), Eyes on
Flock free-text search reasons, and all-attribute ArcGIS payloads carrying
editor-tracking / operator / contact fields — and the I7 lanes impose S1–S9
screen classes on any captured member. The store's tier model already knows
`sealed`, but four questions had non-obvious answers:

1. **What "seal" means mechanically.** `evidence_capture.storage_tier` is a
   mutable column — a tier flip would be an `UPDATE`, which the spine's
   append-only contract and the write surfaces' privilege sets both forbid.
   The seal must be a *record*, not an edit.
2. **Where the refusal lives.** A deny decision has to reach every
   publishable path — the read API's capture route, the export's
   claim→evidence bindings, the release builder that consumes them — and it
   must survive a spine rebuild.
3. **What the audit may say.** The findings that prompted the row are the
   hazard: a report that quotes a field name or value republishes the
   material it is auditing. Everything emitted must be counts + ids.
4. **Who may delete.** Nobody inside this row. WV-06/WV-11 reserve true
   purge to the operator's in-ticket action through a dedicated function;
   the audit's job ends at suppression + a counts-only checklist.

## Decision

**Seal is suppression, recorded append-only — never a byte operation.** The
seal is two carriers of one rule, mirroring ADR-124's disposition twin:

- **Spine carrier** — `capture_seal` (sqitch `seal_register`, appended after
  the plan tip with L44–52 byte-identical): one insert-only row per
  protective `seal`/`unseal` action, keyed by `capture_id` (FK
  `evidence_capture`) + `content_digest`, carrying the firing class ids in
  `rules[]`, `author`, the `sig.at-rest-audit/1` report ref, and a
  DB-clock `recorded_at`. Immutability is enforced twice — a trigger refuses
  `UPDATE`/`DELETE` and no role holds the privilege — so a changed decision
  is a NEW row (`unseal` supersedes; `capture_currently_sealed` reads latest
  action). Writes go through the NOLOGIN `sig_seal_writer` (INSERT-only —
  the L2 leg's auditable surface); readers get column-limited SELECT
  (`seal_seq, capture_id, action, rules, recorded_at` — never `author` or
  the audit ref) so the public consult names *why* at class granularity.
  The register joins `spine_watermark` as a facet because a recorded seal
  changes what serving may emit.
- **Object carrier** — `sig.seal-deny/1` on the restricted bucket: the
  durable, rebuild-surviving deny set — capture/artifact/digest ids + rule
  ids only, a `supersedes` pointer carrying the full prior entries, a new
  object *version* per update under bucket versioning (never an in-place
  rewrite). Rollback replays the prior version, never a delete.

**The publishable paths consult the record, not the tier.** Every serving
surface honours "currently sealed" the way it honours a withheld artifact:
`PgReadStore.capture` answers the sealed representation (existence + digest
only, SIG-EVID-010 — `tier=sealed`, `bytes_available=false`, no byte path)
whatever `storage_tier` the row carries, and `spine_export`'s
claim→evidence binding drops a currently-sealed capture through the
`capture_currently_sealed` consult plus a fail-closed post-check (the
dropped count is recorded counts-only). A pre-`seal_register` spine reads as
honest absence (`to_regclass` guards), never an error. The artifact-level
`withhold` `publication_disposition` written per sealed capture gives the
public tombstone its safe reason (`policy_restriction` for F-406/I7,
`suppressed` for a PUB-002-only flag).

**The scanner is deterministic and counts-only.** `evidence.screen` is a
pure field-name/shape/scoped-value-pattern engine over the committed
`sig.at-rest-audit-decl/1` table (`ops/at_rest_audit.toml`): the three F-406
classes (source-glob members only), the nine I7 lane classes (lane rules
run only on declared member sources), and the five SIG-PUB-002 categories
(screened on every capture for the operator's purge checklist). It emits
`{class_id: field_hit_count}` — a field name or value is an input, never an
output. The L1 report is `sig.at-rest-audit/1` (per class × source counts);
the restricted-only `sig.at-rest-flagged/1` sidecar names object ids +
digests + class ids so L2 seals exactly the flagged set; the
`sig.pub002-listing/1` is categories × counts + digests — the operator's
WV-11 checklist, never the material. The L1 scan runs as an ephemeral
`sig-exec-atrest-<stamp>` job on the P34.43 host (read-only mount,
`sig_audit` read posture, `ops/probes/at-rest/` its only write scope); the
L2 seal is windowed, AR-2-gated, and exits 42 while `capture_seal` is
undeployed — the hosted deploy rides P34.46's plan advance.

## Consequences

- No code path can delete or overwrite a capture byte through this row:
  the deny set is a new version, `capture_seal` refuses mutation by trigger
  and privilege, `OcflStore` stays write-once, and the leg script's
  `assert_no_byte_delta` fails the leg if the object name+generation
  multiset moved.
- An `unseal` is a new row restoring the prior disposition — a recorded,
  reviewable reversal, never an edit.
- A flag that names material stays restricted: public surfaces show counts
  and safe reason categories only.
- The `capture_seal`-absent spine keeps today's behaviour (honest absence)
  so the change deploys independently of the serving code.
- The PUB-002 listing exists so the later true-purge decision (P37.71's
  purge function, WV-11) works from counts + digests, not a re-scan.

## Alternatives considered

- **Mutate `storage_tier` in place** — a single `UPDATE`; rejected: it is a
  forbidden write shape (SIG-STORE-011, the claim spine's no-update rule),
  un-auditable, and unrevertible without a second mutation.
- **Deny set only, no register** — simplest; rejected: the bucket object is
  off the spine's transactional path, so the API/export consult would need
  bucket reads on every capture request and a spine rebuild could diverge
  from it silently.
- **Register only, no deny set** — rejected: the object record is the
  durable artifact surviving a rebuild and the auditable pre-state for the
  operator's purge decision; the contract names it the serving/export deny
  set.
- **Delete the flagged bytes** — the obvious instinct and exactly what
  WV-06/WV-11 reserve to the operator through the purge function; rejected
  outright.
- **Human-in-the-loop per flag** — the screen is deterministic field/shape
  rules on synthetic fixtures; presenting model judgment as a human check
  is forbidden and per-capture review doesn't scale a full store scan.

## Revisit trigger

- The purge function lands (P37.71 / WV-11) — `capture_seal` rows then
  reference tombstones, and the deny set's role changes from "hold the
  suppression" to "record what was purged under authority".
- A serving path that consults captures without the seal consult appears —
  any new capture read must honour `capture_currently_sealed` or the deny
  set, and the export post-check must keep refusing.
- The OCFL store's write path changes so re-capture no longer rewrites an
  inventory head (D-P34.42b-1's trigger) — the seal's byte-delta assertion
  then has a stronger baseline to name.
- A screen class needs value-level or model judgment the declaration
  cannot express — the counts-only contract is the boundary; widening it is
  a new ADR, not a rule edit.
