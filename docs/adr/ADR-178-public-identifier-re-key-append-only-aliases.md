# ADR-178: Public identifier re-key with append-only aliases and a restricted old→new map

- **Status:** Accepted
- **Phase:** Round 11 / Stage A, 11A (`docs/tickets/221_P34.18__personal-handle-source-id-rename.md`)
- **Ticket:** P34.18 (run ledger `docs/build/runs/P34.18.md`)
- **Date:** 2026-10-03 — the re-key mechanism, alias semantics and restricted-map rule decided here record
  operator decisions already taken: B-3 (DR-C6-01) at 2026-10-01T04:32:16Z (round 10), A-0.1 (OD-17) and
  A-0.4 (OD-20) at 2026-10-01T03:41:19Z (round 1), all in
  `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`
- **Written:** 2026-10-03 (`date -u`; Devin / swe-2-high, P34.18 sub-agent)
- **Decision owner:** the operator (the re-key posture is theirs — DR-C6-01; this ADR engineers it).
- **Relation to landed ADRs:** qualifies none. It *redacts* a personal surname inside ADR-137's body and a
  handle-bearing identifier inside ADR-169's body — the ticket's acceptance (zero handle-list entries in the
  tip's tracked files) requires it and Part VIII binds; both files carry an appended status note recording the
  redaction. It operates on the alias projection added by this change, the append-only spine (P1–P3,
  SIG-STORE-011), and the ADR-132 withdrawal-barrier conf mechanism it extends with `renamed_*.conf`.
- **Related:** DR-C6-01/B-3, OD-17 (A-0.1), OD-19, OD-20 (A-0.4); S0 findings F-097/F-131, RI-01, C3, J4
  NEW-6, TS-04/TS-06; SIG-PUB-002, SIG-STORE-011, SIG-EXPORT-006; P34.21b (republish #2), P34.46 (hosted
  deploy), P34.47 (live crawl closure), P35.26 (full `camera_operator` fix), P37.55 (archive deposits).

## Context

A cohort of camera-registry source identifiers was minted from personal ArcGIS **account handles** (and one
source id from a surname): `camreg_<handle>`, the corresponding target ids, and every identifier composed from
them — camera **subject ids** (`traffic_camera:<source>:<target>:<ref>`), claim ids, evidence/permalink ids,
tile properties, PROV/source records, and one `camera_operator` claim value that is itself an account handle.
The same cohort leaked into registry non-id text: 41 e-mail-shaped owner strings and handle tokens inside
`notes`, `name` and `agency` fields (A-0.1, C3). Because the claim spine is append-only (SIG-STORE-011), the
recorded claims keep these identifiers forever; the question was what the *public* surface may carry.

The operator decided (RATIFICATION_LOG, verbatim):

- **B-3 / DR-C6-01** (round 10, 2026-10-01T04:32:16Z): *"Re-key public source ids that embed personal handles.
  Old URLs get a neutral 'identifier changed' page. The old→new map stays restricted (a public redirect would
  republish the handles)"* — answered **"Re-key, map restricted (Recommended)"**.
- **A-0.1 / OD-17** (round 1, 2026-10-01T03:41:19Z): asked whether to remove the e-mail-shaped owner strings
  and handle tokens from registry non-id text at the tip immediately — answered **"No, wait for P34.18"**
  (this ticket performs the removal on the branch; public `main` changes only on the operator's merge).
- **A-0.4 / OD-20** (round 1, 2026-10-01T03:41:19Z): git history retains the strings on ~96 remote branches;
  agents never rewrite history — answered **"Accept and disclose (Recommended)"** (disclosed in this ticket's
  correction note; SWH/Zenodo deposits unblock after P37.55's history scan).

## Decision

1. **Neutral public identifiers.** Retired source ids are replaced by deterministic neutral ids —
   `camreg_us_ny_<n>` where the layer's jurisdiction is recorded, `camreg_und_<n>` otherwise, and
   `okc_council_statement` for the surname id — never derived from an account handle. Target and composed ids
   (subject/claim/permalink/tile properties) are re-derived or projected from the neutral ids.
2. **Append-only aliases.** An old identifier never disappears: claims keep their recorded `source_id`
   (SIG-STORE-011). Resolution to the neutral id is an **export/read-time projection**
   (`policy.source_aliases`), applied at the seams — `exports.shaping.parse_shaping_claims`,
   `exports.spine_export` supplementary + materialized reads, `resolution.camera_sites_pg`, the API's
   `IdentifierAliasMiddleware`, and the web build's `sources.ts`/`alias.ts` — never a spine rewrite.
3. **Keyed digests, not a public list.** The committed alias table
   (`policy/src/policy/data/source_aliases.json`) carries `sha256:` digests of retired tokens only; it repeats
   no handle. ADR-178's trade-off: **plain sha256, not HMAC** — an HMAC key held in Secret Manager (the
   ticket's other option) would make the committed table unverifiable by any checkout without the key and
   turns every resolver into a key consumer; the digests' role is lookup, not secrecy (the map is restricted
   anyway), and the token space is already public in git history. If a future threat model needs keyed
   digests, that is a new ADR amending this one.
4. **Restricted old→new map.** The plaintext map is written only to the restricted location — the gitignored
   `docs/build/logs/p34.18/restricted_source_map.json` (mode 0600) locally, and the insert-only
   `sig-restricted` object L2 writes on hosted (HG-09 posture; never committed, never in any export). Its
   sha256 is recorded in the alias table as the audit anchor. Readers: the operator, the re-key tool, and the
   `sig-ops renamed-routes` conf generator.
5. **Neutral old-URL handling (OD-19 honoured).** Old identifier URLs are exact-match `location =` rules in
   the generated `conf/renamed_*.conf` barrier serving the static N-5 page
   (`/sources/identifier-changed/` — "This identifier has changed.") in place. **No redirect**: a 301 to the
   new route would publish the mapping and repeat the handle — that is what B-3 forbade. The page is shipped
   by P34.21b's republish #2, not this branch's publish.
6. **`camera_operator` suppression.** A `camera_operator` value digesting onto the suppressed set is marked
   `publication_permitted = False` in shaping and dropped to `None` in the camera-site materialization — the
   spine keeps the recorded claim; the public surface carries no operator. The full predicate fix is P35.26's.
7. **Registry non-id text (OD-17).** The e-mail-shaped owner strings and handle tokens are removed from
   `sources.toml` and `camera_registry_targets.toml` non-id fields on this branch (`(owner …)` →
   `[account withheld]`, e-mail-shaped `agency` values → `(account withheld)`, handle tokens inside `name`
   parentheses dropped).
8. **Retained history disclosed (OD-20).** Git history, the restricted map, and the recorded spine keep the
   old strings; the repo tip's *tracked files* carry zero handle-list entries (the acceptance criterion —
   records such as findings CSVs, run ledgers, live-run trees and reports are re-keyed in place; paths are
   `git mv`ed). `docs/governance/identifier-rekey-note.md` is the dated correction note disclosing this.
9. **Hosted mutation is L2 only.** The insert-only hosted writes + restricted-map object insert run only on
   the operator's verbatim go inside the window (≥ 2026-10-13T12:00Z, outside the daily 03:00–06:30Z
   blackout, preferring 14:00–20:00Z weekdays), with the AR-2 restore point, pre-state capture and a ≤24 h
   probe — queued in RETURN PASS, never executed by this branch.
10. **No in-DB alias table.** A new sqitch change can deploy on hosted only with P34.46's deploy of the plan
    tip; this row's hosted leg uses existing tables plus the restricted-map object (`live:P34.46` edge
    recorded in the run ledger).

## Consequences

- Every public surface — exports, tiles, API responses, the `/sources/` table, old URL routes — projects or
  suppresses retired identifiers deterministically; a recorded claim under an old id still resolves (old ids
  keep working as lookup keys; responses render the neutral id).
- The restricted map is the single plaintext old→new record; its disclosure is a Part VIII event.
- The re-key is idempotent (`sig-connectors rekey-personal-ids`, dry-run by default): a re-run restores the
  plan from the prior restricted map and changes nothing.
- P34.21b's republish #2 ships the re-keyed pages, the N-5 routes and the correction-note link; P34.47's
  live crawl closes RI-01.

## Revisit trigger

- A **second personal-identifier class** is found in public ids (a new finding like C3/J4): this mechanism
  generalises — revisit to confirm the neutral scheme and digest table still fit before a second cohort.
- The **restricted map's location or readership** changes (Secret-Manager-keyed digests, a hosted map
  object schema, a new reader): amend via a new ADR.
- **P34.46** lands the in-DB alias table path: revisit whether the middleware/export projections should read
  it instead of the committed table.
- A legal/complaint driver demands **history rewriting** (beyond OD-20's accept-and-disclose): that is an
  operator decision this ADR does not authorise — revisit with a new ADR and a new gate.
- `camera_operator`'s full fix (**P35.26**) ships: the suppression set semantics are subsumed — revisit to
  retire or keep the digest class.
