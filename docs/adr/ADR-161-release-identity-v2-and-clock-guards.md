# ADR-161 — Release identity v2 (`sig.publication-descriptor/2`, calendar labels, keyed export ids) and the §3.3 clock guards (P35.12 — R11-REL-01; SIG-REL-001/002/003 owner; extends ADR-132, never edits it)

- **Date:** 2026-10-16
- **Status:** accepted
- **Ticket:** P35.12 (Round 11 / P35, sub-round 11B, manifest row 294; requirement R11-REL-01)
- **Base:** `r11/P35.4-ops-runbook-v2`
- **Extends:** ADR-132 (immutable release namespaces + the acyclic
  integrity-manifest hash graph). Nothing in ADR-132's landed body is
  rewritten — this ADR adds identity fields and gates by reference; the
  `p-<64 hex>` namespace, the external integrity manifest and the
  mutable-overlay split stand unchanged.
- **Related:** ADR-124 (the `publication_disposition` spine mirror the
  `gates.disposition_root` digests), ADR-133 (the per-compartment search
  index whose version the descriptor records), J3's TX-13b descriptor
  fields (merged here per G3 §3.2), K4 (the jurisdiction boundary pack —
  `boundaries_root` is its published input), NEW-1/NEW-2/NEW-3 (the
  recorded defects this ADR retires), ADR-146/C-10 (sqitch.plan lines
  44–52 are never re-stamped).

## Context

The G3 release model
(`docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md`
§3) audited the live
release path and found three identity defects the v1 descriptor could not
express:

- **NEW-1** — `data_release_id` was
  `sig-<as-of date>-<sha256(dates, ruleset, resolver)[:8]>`: a date, not a
  dataset. The two same-day `2026-09-24` national exports carried the same
  id `sig-2026-09-24-bd01cb94` for different bytes, and a fixture export
  was indistinguishable from a production one.
- **NEW-2** — the export never pinned the belief instant
  (`export.sh` passed `--as-of` and never `--belief`); the descriptor
  recorded `as_of_belief = as_of[:10]` with `belief_pinned: false`, so the
  snapshot the release names was not the snapshot the read took.
- **NEW-3** — code identity was a caller-typed `--renderer-revision`
  string, while 11 of 14 packages reported `__version__ = "0.0.0"`: the
  GATE-G3-signed candidate recorded `resolver_version 0.0.0`, and no
  commit at all.

B1/§3.3 adds the clock failures this row engineers against: a wrong host
clock or a typed date re-creates stale/future stamps, so the build reads
T0 once, checks it against a remote `Date` header, refuses the AR-3
windows, enforces `as_of_world ≤ as_of_belief ≤ built_at`, and forces
`--replay` for any historical cut (Class S).

## The recorded operator answers (B-9), verbatim

From `docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md`
§ "Decisions the operator took", the
GATE-P record — quoted, not paraphrased:

> **D-G3-1** — "Adopt this model (identity v2, a private release bucket
> mounted by `sig-web`/`sig-api`, LB path rules, metadata-only promotion,
> conf generations) via a new ADR extending ADR-132?" — **Yes**
>
> **D-G3-2** — "Label format `sig-YYYY-MM-DD.N` (data date + ordinal)?" —
> **Yes**

The plan cell carries the same answers as **Option 1 for both**: the
calendar-date label `sig-YYYY-MM-DD.N` and the short hash-suffixed export
id `sig-export-<ts>-<key8>` (`sig-export-<YYYYMMDDTHHMMSSZ>-<key8>` — the
export's snapshot instant compacted + the leading 8 hex of the keyed
input digest). This ADR is the "new ADR extending ADR-132" D-G3-1 names.

## Decision

1. **`sig.publication-descriptor/2` is the release identity contract.**
   Its field names follow G3 §3.2 exactly (the schema is the seam row
   295's stamp and the site consume): `label`, `environment`
   (`production|staging|fixture|replay`), the `snapshot` block
   (`as_of_world`, `as_of_belief`, `belief_pinned`, `spine_watermark`,
   `materialize_run`, `sqitch_head`, `restore_point`), `export`
   (`id`, `input_manifest_sha256`, `content_key`), `code` (`commit`,
   `repository`, `tree`, `images.export`), `renderer` and the J3 TX-13b
   `site_renderer` block (`version`, `astro_version`,
   `package_lock_sha256`), `versions` (ruleset, resolver, policy,
   projection, search-index, `ontology_version`,
   `ontology_generated_sha256`, `descriptor_schema`), `gates`
   (`disposition_root`, `rights_registry_sha256`, `attribution_gate`),
   `evaluation` (`status`, `eval_confidence`, `deferral_refs`,
   `review_status_summary`), `disclosures` (`{id, text_sha256}`),
   `graph_quality`, `compartment_projections`, `evidence_root`,
   `dossier_root`, `transparency_root`, `boundaries_root`, and `build`
   (`built_at`, `publish_class`, `replay_reason`). Every field is
   populated or explicitly declared-empty (`null`/`[]`); every field
   traces to a build artifact (§3.1); no field holds the publication id —
   the ADR-132 ID-free rule is preserved, so `p-<sha256>` stays a pure
   function of canonical inputs.
2. **The human label is `sig-YYYY-MM-DD.N`** — `YYYY-MM-DD` = the UTC
   date of `snapshot.as_of_world` (the *data* date a reader cites), `N` =
   1 + the count of catalog/registry entries already carrying that as-of
   date, allocated under the registry lock (`labels.lock` flock +
   `labels.json`, `sig.release-labels/1`). The date is derived, never
   typed; a same-day second release takes `.2`; a label is never re-issued.
3. **The export id is `sig-export-<ts>-<key8>`** — `ts` the snapshot
   instant (`YYYYMMDDTHHMMSSZ`), `key8` the leading sha256 hex of the
   `BuildSpec.export_id_inputs()` — the §38.1 reproducibility tuple *plus*
   the snapshot/belief instants, `spine_watermark`, `code_commit`,
   `environment`, `replay`, `materialize_run`, `sqitch_head` and
   `restore_point`. This retires NEW-1: two same-day exports with
   different inputs can never collide; identical inputs still name the
   same export (SIG-EXPORT-003's pure-function rule stands).
4. **`boundaries_root` is declared as the K4 (JUR-01) input.** Row 297's
   jurisdiction boundary pack hashes to this field; until it lands the
   field is recorded `null` — populated or explicitly declared-empty,
   never absent. `transparency_root` (J3 TX-13b) is likewise declared and
   is populated over the export's disclosure/exclusion artifacts
   (`exclusions.json`, `web/terms_disclosure.json`, transparency/
   methodology/provenance artifacts) as a `{path: sha256}` content root.
5. **The §3.3 clock guards bind on the operator path.** T0 is read
   exactly once per build/execution and shared by every stamp; the AR-3
   windows (monthly day 6 00:00Z → day 13 12:00Z; daily 03:00–06:30Z)
   refuse unless `--emergency <reason>`; the host clock is checked
   against a remote HTTPS `Date` header (|skew| ≤ 120 s); a typed
   `--as-of`/`--belief` later than T0 (+5 min skew) refuses before any
   DB read; an earlier-UTC-day `--as-of` requires `--replay <reason>`,
   which forces `environment=replay` and `build.publish_class = "S"`; the
   descriptor enforces `as_of_world ≤ as_of_belief ≤ built_at ≤
   now + 5 min`, activation enforces `activated_at ≥ built_at`, and the
   emitted-metadata scan refuses any stamped instant later than
   `built_at` (real-world future fields — `expiry_date`, `valid_until`,
   `sunset`, `renewal_date`, `retention_until`, `review_by`, `deadline` —
   are the allow-list, B1 §5.4). A same-UTC-day typed `--as-of` is the
   normal `export.sh` cut path (the script stamps `date -u`; a Cloud Run
   start hours later is the same data day, never a replay claim).
6. **Promotion is v2-only and fail-closed (SIG-REL-002).** `promote`
   refuses, naming every reason: a non-v2 descriptor (this alone keeps
   the `p-17b713…` fixture candidate out — superseded, consistent with
   Q-12/B1 option C), `code.commit` not a 40-hex sha, a dirty tree
   (recorded at build or live now), a commit pushed to no remote ref, a
   `0.0.0`/missing version field or malformed label, and an
   `as_of_world` earlier than the current latest release's (monotonic;
   rollback is the older path). Promotion mutates no hosted state — it
   runs the same `activate()` path over the caller's registry.
7. **v1 stays a first-class read format.** `descriptor_document` and the
   v1 build path are unchanged (byte-identical reproduction); the catalog
   accessors read v1 and v2 transparently. Only promotion gates on v2.
   `--renderer-revision` remains required for v1 and is refused on v2 —
   v2 carries one code identity (`renderer.revision = code.commit`,
   NEW-3's fix; the commit is read from the tree, never typed, GT-7).
8. **`export.sh` propagates the belief instant.** `SIG_EXPORT_BELIEF`
   maps to `--belief`, `SIG_EXPORT_ENVIRONMENT` (default `production`) to
   `--environment`, `SIG_EXPORT_REPLAY`/`SIG_EXPORT_EMERGENCY` to the
   clock-guard flags — the snapshot block's `as_of_belief`/`belief_pinned`
   and `spine_watermark`/`sqitch_head` (read inside the same REPEATABLE
   READ snapshot) now ride the manifest into the descriptor (NEW-2's fix).

## Consequences

- Every new release built through `sig-exports release build
  --schema-version 2` (the default) carries a complete, validatable v2
  descriptor; the fixture path and the export.sh path share one identity
  model.
- The fixture candidate `p-17b713…` is structurally excluded from
  promotion — no re-sign, no special-case, the v2-only rule does it.
- Row 295 (REL-02, the site stamp/release.json) consumes `label`,
  `code.commit`, `built_at`; row 297 (JUR-01) fills `boundaries_root`;
  the publish rows own the hosted descriptor write — this row performs
  none.
- `manifest.json`'s `release_id` changes form for every build (the
  NEW-1 fix is intentionally breaking: the old id was the defect). Legacy
  manifests and descriptors remain readable; nothing renames landed ids.
- Host-clock checks need one outbound HTTPS request on the operator path;
  `--skip-host-clock-check` records a declared skip (never silent).
- Deferred honestly: `materialize_run`/`restore_point`/`images.export`/
  `site_renderer.*`/`graph_quality`/`disclosures` stay declared-empty
  until the cut/publish/disclosure rows (294's successors) populate them
  — the fields exist now, the values are those rows' legs.

## Revisit trigger

- The release tool (`sig-ops release …`, REL-03/…) lands and wants the
  promotion probe set re-bound (e.g. `code.repository` or the remote-ref
  check moves), or
- a third descriptor version is proposed — v2's promotion-only rule then
  needs re-litigating, or
- the AR-3 windows or the host-clock endpoint/tolerance change
  (§3.3 marks the endpoint `[unverified]`), or
- row 297's K4 boundary pack lands and `boundaries_root` semantics need
  pinning beyond "sha256-or-null".
