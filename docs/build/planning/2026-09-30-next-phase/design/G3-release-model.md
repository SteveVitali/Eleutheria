# G3 — Release, deploy provenance and versioning model

Row **G3** of `META_PLAN.md` §6 Stream G (owner D, depends C2, G2, J3). Written 2026-09-30 by Claude Code (Opus 5.5) in
the planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `4181a0ac`,
code byte-identical to chain tip `b051732c` for every path cited). Work window (`date -u`): **2026-09-30T18:32:55Z → see
footer**. `PD` = `docs/build/planning/2026-09-30-next-phase`.

> **Design only (P3/P10).** Nothing here was executed against production. GCP access was `describe`/`list` only (§16).
> Nothing below is `engineered`, `staging-verified` or `live-executed` (P5). Commands are for Round-11 tickets and carry
> **[unverified]** unless copied from a committed script. Costs and durations marked **[est]** are planning guesses; list
> prices are **inference**. Every public sentence quoted here is **agent-drafted** and must be confirmed verbatim by the
> operator before it ships (META_PLAN §2). The operator's address is **‹operator address›** (value in META_PLAN §7.1).

**Inputs read.** META_PLAN §3, the G3 row, §7/§7.1, §8.2, §9; `design/G2-activation.md` (whole); `design/J3-transparency-design.md`
§0–§3, §7.1, §8, §9, §11–§16; `review/JOURNEYS.md` §1–§3 (P2, P3, P7), §5 H10/H17, §11; `review/DATA_TRUTH.md` §1, §3, §4.1,
§4.14–§4.16, §5, §6; `research/G1-ops.md` §0–§3.6, §3.10, §4–§8; `research/F5-eng-debt.md` §4 PKG-03/PKG-04 + `data/eng_debt.csv`
ED-14…ED-24; `design/H2-branch-ci.md` §0, §1.4, §2.4, §5; `research/B1-date-drift.md` §5.4, §5.8, §6, §7; `research/E1-contradictions.md`
E1-01; `findings/FINDINGS.csv` (F-02, F-07, F-08, F-11, F-14, F-15) and the titles of every `findings/incoming/*.csv` row (to avoid
re-raising). Code: `exports/src/exports/{release.py, release_pages.py (names), manifest.py, spine_export.py, cli.py}`,
`ops/src/ops/{publish.py, deploy.py, release_serving.py, release_publish_verify.py (header), composed_verify.py:256}`, `ops/gcp/{web.sh,
export.sh}`, `ops/web/{nginx.conf, Dockerfile}`, `web/astro.config.mjs`, `web/src/{components/Citation.astro, layouts/BaseLayout.astro,
pages/releases/index.astro}`, `api/src/api/{app.py, routes.py (route list), release_search.py, cli.py, models.py HealthResponse}`,
`CHANGELOG.md` head, every package `__init__.py`/`pyproject.toml` version line; ADR-132 (via the P32.13 module docstring); spec
SIG-EXPORT-003, SIG-UI-035, SIG-UI-049, SIG-FIND-001/002; go-live spec HG-11 row; `docs/build/readouts/GATE-G3.md` head;
`docs/build/reports/REPUBLISH_LIVE_2026-09-27.md` §0–§2.

**Outputs.** This file and `findings/incoming/G3.csv` (NEW-1…NEW-6).

---

## 0. Summary

**The model in one paragraph.** A production release is one content-addressed publication `p-<sha256(descriptor v2)>`
with an immutable human label **`sig-YYYY-MM-DD.N`** (UTC date of the data as-of; `.N` = ordinal among releases with that
as-of date). The descriptor binds the spine snapshot (as-of instants from the clock, watermark, environment), the code
commit (clean, pushed), every ruleset/policy/ontology/renderer version (one version source, no `0.0.0`), and the
evaluation status and disclosures. One command family, **`sig-ops release cut → build → stage → verify → promote`**, run by
one owner holding one registry lock, builds everything a release serves (records `r/<pub>/`, a latest view `v/<pub>/`, a
citable page snapshot `s/<pub>/`, the landing and data under `releases/<pub>/`) into a **private release bucket**, verifies
it on a **private staging origin**, and promotes by **metadata only**: a new immutable config generation (promoted set,
latest pointer, withdrawals, selectors) plus a digest-pinned revision roll of `sig-web` and `sig-api`. Bytes are never
copied or overwritten at promotion, so there is no mixed-release window and no hand `rsync`. Every page shows the release
label, as-of, commit and build time, and links a machine-readable `release.json`. Every API response names the release it
serves or labels itself `live-spine`. Rollback is a new generation pointing at an earlier release, with the **current**
withdrawals re-applied. Withdrawal is tombstone bytes plus a new generation plus a roll. Code versions are semver tags that
the operator puts on `main` after each merge sitting. The **CHANGELOG** and the per-release data changelog link to each
other through release labels.

```
 cut ── on-demand backup → sig-materialize → export (REPEATABLE READ; as-of = date -u; belief = snapshot instant)
  │
 build ─ descriptor v2 → r/<pub>/ (P32.13) + v/<pub>/ (Astro base=/) + s/<pub>/ (Astro base=/s/<pub>/, J3) + releases/<pub>/
  │       + release.json + integrity manifest            [all dates from the clock; built_at fixed once]
 stage ─ upload to gs://…-sig-release/staged/ (private) · candidate state = staged · nothing public
  │
 verify ─ V1–V14 on private staging origins (sig-web-staging + sig-api-staging: same digests, IAM-only) ── fail → failed
  │
 classify ─ Class R (routine, standing go) | Class S (candidate-specific signed readout, HG-11 domain)
  │
 promote ─ conf/<gen+1>/ {promoted.map, latest.json, withdrawn.conf, selectors.conf, labels.conf, releases/index}
          → roll sig-api then sig-web by digest with SIG_LATEST_PUB / SIG_CONF_GEN → post-promote checks
          → fail ⇒ automatic rollback to the previous generation (pre-authorised) + alert
```

**Promotion gate (§5.5).** V1 integrity · V2 identity and clock · V3 route allow-list and absence · V4 stamp and manifest ·
V5 link crawl and snapshot containment · V6 number truth (site = release files) · V7 API parity · V8 attribution · V9
jurisdiction–coordinate sanity · V10 withdrawal barrier on every alias · V11 zero-JS/budgets/a11y · V12 scrub and secret
scan · V13 disclosures · V14 diff sanity. After promotion the same checks run against the public origins, plus
`probe-hosted`.

**Cadence and sign-off rule (proposal, §7).**
- **Cadence.** Cut monthly on the 15th at 14:00Z, after the day 6–13 batch window. Cut early when net-new publishable claims
  reach ≥ 10 % of the release **and** ≥ 14 days have passed, or when a fix or source change is ready. Alert when the
  release is > 35 days old.
- **Class R, no new signature.** Same code commit as an operator-signed release, same versions, allow-list, compartments,
  licences and source set, a bounded diff, and every check green with no waivers. It promotes under one standing operator
  go, recorded verbatim and revocable, and the operator is emailed the diff.
- **Class S, candidate-specific readout signed verbatim.** Anything else: code or template change, new route, source,
  compartment, licence or disclosure, version or schema change, an anomalous diff, or any waiver.
- **No readout needed.** Withdrawals and rollbacks to an earlier promoted release.

**Tickets (§11): 11 keys, 13 runs.** REL-10 Versioning discipline + one version source (S) · REL-01 Release identity v2 +
clock guards (M) · REL-02 Provenance stamp, `release.json`, headers (M) · REL-03a Release pipeline, layout, private bucket and
staging origin (M) · REL-03b Templated nginx, config generations, metadata-only promotion (M) · REL-08 Rollback, withdrawal,
purge, runbook, legacy floor (M) · REL-04a Verification suite A (M) · REL-05 API release parity (M) · REL-04b Verification suite B
+ post-promote auto-rollback (M) · REL-09 Dark cutover to the release layout (S, live) · REL-06 Classifier, standing go, readout
generator (M) · *first model release = G2 ACT-24 (HG-11)* · REL-07 Cadence automation (M, live) · REL-11 Second-release
acceptance (S, live).

**New findings (§15).**
- **NEW-1 (S2).** The public release id is not content-addressed. `sig-2026-09-27-ce480ab1` is a pure function of the date,
  the ruleset and resolver `0.0.0`, so two different exports from the same day share one id.
- **NEW-2 (S2).** The live release was **not** belief-pinned: `belief_pinned: false` in its own files. Its recorded belief
  "2026-09-27" is a truncated date, so the cut cannot be reproduced.
- **NEW-3 (S2).** Release code identity cannot be verified: `resolver_version`/`renderer.version` = `0.0.0` in every
  release, and `renderer.revision` is unchecked free text.
- **NEW-4 (S2, latent).** The withdrawal include is read only at nginx start. No reload path exists, so autoscaled
  instances can disagree.
- **NEW-5 (S3).** Release trees and staging registries are committed to the **public** repo. A real candidate staged that
  way would be public before sign-off.
- **NEW-6 (S3).** The web code has no base-path support (0 `BASE_URL` uses, 85 root-absolute path sites in 36 files), so J3's
  `/s/<pub>/` snapshot build needs an unsized refactor.

**Decisions this row makes for other rows** (J3 §8.6, G2 ACT-17, F5 PKG-04):
- Registry location: a private release bucket, mounted read-only by `sig-web` and `sig-api`.
- Topology: LB path rules for `/v1/*` and `/intake/*`, with nginx for static files and the deny barrier (G2 option 3a).
- Latest flip policy: metadata-only promotion, monotonic in as-of. Rollback is a new generation.
- Same-day selector rule: multiple activations per day are allowed, and the label carries `.N`. New citations are path-pinned,
  never selector-based. A legacy selector that is ambiguous answers 409.
- Status lane: a separate publish class that may write only `status/**`.
- Descriptor v2: one ADR, merging J3's `transparency_root`/`snapshot_renderer`.
- Tags: operator-only, on `main`, after sittings.

---

## 1. Ground truth that constrains the design

| # | fact | evidence | consequence |
|---|---|---|---|
| GT-1 | The live site is `sig-web` nginx over a gcsfuse mount of the `…-sig-web` bucket; "the bucket sync IS the deploy". 289 objects, all written 2026-09-27T01:33:56–59Z. `…-sig-public` holds 134 objects written 01:30:28–01:31:17Z, at the bucket root | `ops/web/nginx.conf:1-10`, `ops/gcp/web.sh:6-10` (code); `gcloud storage ls -l -r` 18:42:27Z (live-read) | the latest view is overwritten in place. At P32.13 scale (≈475k objects, G2 step 7 upload ≈1–2 h [est]) an in-place sync would serve mixed releases for hours |
| GT-2 | The deploy "plan" is printed strings (`deploy.py:88-94`: `rsync … --delete-unmatched-destination-objects web/dist gs://…-sig-web`). P31.16 hand-typed three syncs. The public data sync used `--delete`, which removed the previous public bundle | `ops/src/ops/deploy.py:65-104`; `REPUBLISH_LIVE_2026-09-27.md:32-47` (code, recorded-execution) | one executor must own every public byte (F-02, C4 NEW-10, ED-22/23); public data needs its own immutable namespace |
| GT-3 | P32.13 already implements `publication_id = p-sha256(ID-free descriptor)`, a separate `manifest_sha256`, refusal of different bytes under one id, `activate`/`rollback`/`clear_latest_pointer`/`record_withdrawal` with **current** withdrawals re-applied on rollback, activation receipts, and a date-grained `compat_index` | `exports/src/exports/release.py:1-35, 166-213, 1025-1257` (code) | keep and extend it. G3 changes what the descriptor binds and where the registry lives, not the hash graph |
| GT-4 | Descriptor v1 binds `data_release_id`, **date-only** `as_of_world`/`as_of_belief`, ruleset, `resolver_version`, `policy_version`, `projection_version`, renderer `{package, version, revision}`, `input_manifest_sha256`, and projection/evidence/dossier roots. It binds no code commit (only a caller-typed `--renderer-revision`), no ontology version, no environment, no spine watermark and no evaluation or disclosure fields | `release.py:166-204`; `exports/cli.py:272-276` (code) | SIG-FIND-001 ("pinning input snapshot, code, ontology, policy …") is only partly met, so descriptor v2 is needed (J3 §3.4 reached the same trigger) |
| GT-5 | `data_release_id` = `sig-<as_of date>-<sha256(as_of date, belief date, ruleset, resolver)[:8]>`. The three recorded ids recompute **exactly** from dates, `p27.3/1.0.0` and `0.0.0` alone | `exports/src/exports/manifest.py:78-108`; recompute 18:47:56Z (recorded-execution) | **NEW-1**. The id names a date, not a dataset |
| GT-6 | `export.sh` passes `--as-of <instant>` and never `--belief`. The export reads current belief (`upper_inf(sys_period)`) and records `as_of_belief = as_of[:10]`, with `belief_pinned: false` in all 55 dossier-index entries of the live release | `ops/gcp/export.sh:45,61`; `exports/src/exports/spine_export.py:750-755, 2107-2108`; `shaping.py:1643-1646` (code); C3 capture `web/dossier_index.json` sha256 `a4938e68…` (recorded-execution) | **NEW-2**. v2 records the snapshot instant and watermark |
| GT-7 | 11 of 14 Python packages hard-code `__version__ = "0.0.0"`; all 14 `pyproject.toml` say `0.1.0`; `run_spine_export` uses the exports `__version__` as `resolver_version`. The GATE-G3-signed candidate records `resolver_version 0.0.0`, `renderer.version 0.0.0`. `composed_verify` defaults `renderer_revision="p33.2"` | `*/src/*/__init__.py`; `spine_export.py:2113`; `p32.23a…/descriptor.json`; `ops/src/ops/composed_verify.py:256` (code) | **NEW-3**. One version source; commit taken from the tree, never typed |
| GT-8 | nginx includes `/mnt/sig-web/conf/withdrawn_*.conf` once, at start; nothing in the repo reloads it (0 `nginx -s reload` references). The live `sig-web` image (`5c064881`) predates the include altogether | `ops/web/nginx.conf:137-143`; grep 18:49:18Z (code); G2 §1, G2 NEW-2 (live-read, cited) | **NEW-4**. Withdrawals must take effect through a new revision reading an immutable config generation |
| GT-9 | The base image is `nginx:1.27.5-alpine` with a repo-owned `nginx.conf`. The official image's entrypoint can render `/etc/nginx/templates/*.template` with envsubst at start | `ops/web/Dockerfile` (code); entrypoint behaviour is **inference** (verify in REL-03b) | per-revision config values (`SIG_LATEST_PUB`, `SIG_CONF_GEN`) are cheap |
| GT-10 | `sig-web` and `sig-public`: versioning unset, 7-day soft delete (18:36:12Z); `sig-web` is `allUsers:objectViewer` (G1); no CDN on the LB (G1) | `gcloud storage buckets describe` (live-read); G1 §1 | a new private bucket avoids a third public origin; rollback relies on generations, not object versions |
| GT-11 | The Astro build has **no** `base`; 85 root-absolute path sites in 36 files; 0 `BASE_URL` uses. `web/src/pages/releases/index.astro` renders `/releases/` from the catalog seen at build time | `web/astro.config.mjs:60-90`; grep 18:47:42Z (code) | **NEW-6**. The release tool, not Astro, owns `/releases/index.html` (C4 NEW-10) |
| GT-12 | The API root reports `api_version`/`package_version` only; `/health` reports store readiness. The API's `/v1/*` routes read the **live spine** (C3 watermark 2,514,683 at 17:07Z vs 2,423,200 in the release); only `/v1/releases/{pub}/…/search` is release-namespaced and reads a registry path | `api/src/api/app.py:71-186`; `release_search.py:75-82`; DATA_TRUTH §1, §5 cause 6 (code, live-read cited) | API/site parity needs a release pointer in the API and a basis label on every route |
| GT-13 | The repository is **PUBLIC**; 0 tags; no GitHub release. `CHANGELOG.md` `[0.1.0] — unreleased (REL.1 marker skipped-by-operator …)` | `gh repo view` 18:35:42Z (live-read); `git tag -l` → 0; `CHANGELOG.md:9` | commit links on pages are verifiable by anyone. The premise of J3 D-J3-3 ("repo is private") no longer holds (E1 NEW-14) |
| GT-14 | Drift since the release: G1 counted ≤ 156,273 **emitted** claims from 32 runs since 09-27T01:30Z (≤ 6.4 %, upper bound). C3 read the API watermark at 2,514,683 at 17:07Z = **+91,483 net (+3.8 %)** in ≈ 3.65 days (≈ 25k/day, **inference**). The first-fire wave (10-01…10-21) adds ≈ 1.4 M emitted, mostly duplicate OSM | G1 §3.6; DATA_TRUTH §1 | a drift trigger must count net publishable claims, not emitted ones. A 10 % trigger could otherwise fire every ~10 days |
| GT-15 | HG-11 in the go-live spec is "operating governance: two reviewer roles + written concurrence + live takedown/corrections contact". The chain has used "HG-11" as the per-publication sign-off (P31.16 republish; GATE-G3 "Decision domain: HG-11 publication"). Its governance half is an operator waiver (E1-01) | `docs/3_sig_golive_spec.md:92`; `docs/build/readouts/GATE-G3.md:6`; E1-01 | §7.3 names the per-release sign-off explicitly and does not claim the governance prerequisites |

---

## 2. Principles (binding on every REL ticket)

- **RM-1 One writer, one path.** Public bytes change only through `sig-ops release …` (release, rollback, withdrawal) or
  `sig-ops status publish` (`status/**` only, J3 TX-07). No hand `rsync`, no second sync of one prefix, and no agent-typed
  bucket command in a runbook.
- **RM-2 Immutable after staging.** Bytes under `staged/{r,v,s,releases}/<pub>/` never change except when a recorded
  disposition replaces them with a tombstone or removes them. Nothing deletes a staged namespace.
- **RM-3 Promotion is metadata.** Promotion and rollback write a new immutable config generation and roll services by digest.
  They never copy or overwrite release bytes.
- **RM-4 The clock is the only date source** (B1, P2). Every instant comes from `datetime.now(UTC)` or the database's
  snapshot time at the moment it describes. It is never a CLI argument, except in an explicit, labelled replay.
- **RM-5 Identity is what was read, not what was asked for.** The descriptor records the snapshot instant, the watermark
  and the commit actually used.
- **RM-6 Fail closed.** A check that cannot run fails. A classifier that cannot decide says Class S. A promotion whose
  post-checks fail rolls back.
- **RM-7 Two clocks, both labelled** (J3 T-7). Release pages state the release's as-of. The status lane and live-spine API
  responses state their own time and never pose as a citation.
- **RM-8 Nothing real in the public repo.** Candidate trees and registries live in the private bucket. The repo records
  digests, labels, ids and readouts only (NEW-5).

---

## 3. Release identity

### 3.1 Identifiers

| id | form | derivation | where it appears | mutable? |
|---|---|---|---|---|
| **publication id** (canonical) | `p-<64 hex>` | sha256 of canonical descriptor v2 (P32.13 hash graph unchanged) | URLs `/r/<pub>/`, `/s/<pub>/`, `/releases/<pub>/`; `release.json`; API headers | never |
| **label** (human) | `sig-YYYY-MM-DD.N` | `YYYY-MM-DD` = UTC date of `as_of_world`. `N` = 1 + count of catalog entries in **any** state with that as-of date, allocated by `build` under the registry lock and written into the descriptor | page stamp, citations, release notes, changelogs | never. Unpromoted labels show as `never-promoted` on `/releases/`, so gaps are explained |
| **short form** | `p-3f9ac21e` | first 8 hex of the publication id | stamp (display only, never a URL) | never |
| **export id** | `sig-export-<YYYYMMDDTHHMMSSZ>-<key8>` | `key` = sha256 of the reproducibility inputs **including** the snapshot instants, the watermark and the commit (fixes NEW-1). Internal. It replaces `sig-<date>-<key8>` as the manifest `release_id` for new exports | export manifest, descriptor `export.id` | never |
| **label alias** | `/releases/sig-2026-10-15.1/` → 301 → `/releases/p-…/` | `conf/<gen>/labels.conf`, from the catalog | edge | append-only |

The date in the label is the **data** date, because that is what a reader cites ("SIG, data as of 2026-10-15"). Publication
and build instants appear next to it in the stamp. Same-day releases are expected (withdrawal-driven or fix-driven re-cuts),
and `.N` makes them unambiguous (J3 NEW-4).

### 3.2 Descriptor v2 (`sig.publication-descriptor/2`) — contents

All fields are rendering inputs and none holds the publication id (the ID-free rule). Fields marked ★ are new in v2.

| block | fields | source |
|---|---|---|
| identity | `schema`, ★`label`, ★`environment` (`production` \| `staging` \| `fixture` \| `replay`) | builder; environment comes from the DSN target recorded by `cut` |
| spine snapshot ★ | `as_of_world` (ISO instant = export start from the clock), `as_of_belief` (ISO instant = `now()` inside the REPEATABLE READ snapshot), `belief_pinned` (true: the read is now pinned to that instant), `spine_watermark` (claims, max claim seq/time; P32.4 `spine_watermark` row), `materialize_run` (job execution + image digest), `sqitch_head` (change name), `restore_point` (on-demand backup id) | `cut` (RM-5) |
| export | ★`export.id`, `input_manifest_sha256`, `content_key` | export manifest |
| code ★ | `code.commit` (40 hex, from `git rev-parse HEAD` of a **clean** tree that is **pushed** to `origin`), `code.repository` (`https://github.com/SteveVitali/Eleutheria`), `images.export` (digest used by `sig-export`), `renderer {package, version, revision=code.commit}`, `site_renderer {web version, astro version, package-lock sha256}` (J3 `snapshot_renderer`) | builder; `--renderer-revision` is removed as a free input (NEW-3) |
| versions | `ruleset_version`, `resolver_version` (★ = `resolution` package version + `+g<commit8>`, never the exports placeholder), `policy_version`, `projection_version`, `search_index_version`, ★`ontology_version` + `ontology_generated_sha256`, ★`descriptor_schema` | one version source (REL-10) |
| publication gates ★ | `disposition_root` (sha256 over the ADR-124 dispositions effective at the snapshot), `rights_registry_sha256` (`sources.toml` + redistribution lanes, J3 TX-02), `attribution_gate` (version + pass count) | export |
| evaluation ★ | `evaluation.status` (`deferred` \| `provisional` \| `certified`), `eval_confidence {mode, applied}`, `deferral_refs` (e.g. `D-R6.1-EVAL`), `review_status_summary` (dossiers) | release candidate (P32.23a vocabulary) |
| disclosures ★ | list of `{id, text_sha256}` from a committed `ops/disclosures.toml` whose texts the operator confirmed verbatim | builder; V13 checks they render |
| roots | per-compartment projection roots, `evidence_root`, `dossier_root`, ★`transparency_root` (J3 §3.4) | P32.13 + J3 |
| build ★ | `built_at` (ISO instant from the clock at the **first** `build` of this candidate, fixed once like `SOURCE_DATE_EPOCH`; a re-render passes the recorded value, so bytes reproduce) | builder |

**Not in the descriptor**, so it lives outside the hashed bytes: `activated_at`, the promoting approval, serving image
digests and the config generation. These go in `latest.json` and the activation receipts (GT-3).

**Only v2 is promotable.** `promote` refuses a v1 descriptor. This alone keeps the fixture candidate `p-17b713…` (as-of
2026-10-19, 0 records, F-15) out of production, consistent with Q-12/B1 option C (supersede, no re-sign; ACT-12 records the
supersession).

### 3.3 Clock rules (B1) enforced by the builder (V2)

1. `cut` reads `date -u` (T0) and refuses to start inside AR-3 windows (day 6 00:00Z → day 13 12:00Z; daily 03:00–06:30Z)
   unless `--emergency <reason>`.
2. **Host clock check:** `|T0 − Date header of an HTTPS GET to a Google endpoint| ≤ 120 s`, or refuse (a wrong machine clock is
   the B1 failure class; **[unverified]** endpoint choice).
3. `as_of_world ≤ as_of_belief ≤ built_at ≤ now + 5 min`. For any activation, `activated_at ≥ built_at`.
4. No date in the descriptor, stamp, landing, disclosures or release notes is later than `built_at`. The scan covers every
   ISO-looking value in the tree, with an allow-list for real-world future fields (`expiry_date`, `valid_until`, …; B1 §5.4 test 1).
5. `--as-of` overrides exist only as `--replay <reason>`, which sets `environment=replay` and makes the release Class S.
6. The label date is derived, never typed. `.N` comes from the catalog under the lock.

### 3.4 Lifecycle and catalog

States are append-only events (`registry/events/<ts>-<kind>-<pub8>.json`, created with `if-generation-match=0`):
`cut → built → staged → verified | failed → promoted → (superseded | rolled-back-from | withdrawn-whole)`, plus `never-promoted`
(abandoned after 30 days, or on operator request). The public catalog (`/releases/catalog.json`, `/releases/index.html`) is a
projection over those events and is regenerated in every config generation. Promotion is **monotonic in `as_of_world`**: a
candidate older than the current latest can only become latest through `rollback` (operator go).

---

## 4. Storage and serving topology (decides G2 ACT-17 "registry location", F5 PKG-04, J3 §8.6)

### 4.1 Buckets and prefixes

| location | contents | writer | readers | public? |
|---|---|---|---|---|
| **`gs://…-sig-release`** (new; versioned, 30-day noncurrent lifecycle, uniform access, **no `allUsers`**) | `registry/{catalog.json, compat_index.json, withdrawals.json, activations/, events/, LOCK}`; `registry/conf/<gen>/…`; `staged/r/<pub>/`, `staged/v/<pub>/`, `staged/s/<pub>/`, `staged/releases/<pub>/{landing, data/, changes/}`; `status/**` (J3 status lane) | `sig-release-rt` (release tool), `sig-status-rt` (only `status/**`, IAM condition on the object prefix **[unverified]**) | `sig-web-rt`, `sig-api-rt` (objectViewer, read-only gcsfuse mounts) | only through nginx/LB |
| `gs://…-sig-web` (today's root site) | the legacy tree (GT-1) | ACT-05 publish path until REL-09 | `sig-web` until REL-09 | yes today (QA-7 removes `allUsers`); kept 90 days after REL-09 as the rollback floor source, then deleted on operator go |
| `gs://…-sig-public` (today's root downloads) | the 09-27 public bundle | frozen after REL-09 | probe, direct users | **D-G3-7**: freeze plus `README.txt` pointing to `/releases/latest/` until J3 TX-11's mirror is live, then retire |
| `gs://…-sig-restricted` | exports, OCFL, run rows | unchanged | unchanged | no |

Immutability is enforced by the single writer, versioning and a monthly digest audit (V1 run over all promoted namespaces).
It is **not** enforced by a retention lock, because withdrawal must overwrite bytes with tombstones (§8.3).

### 4.2 nginx (templated; REL-03b, extends ACT-17's P32.13 roll)

- A per-revision environment (`SIG_LATEST_PUB`, `SIG_CONF_GEN`, `SIG_STAGING`) is rendered into the config at start (GT-9).
- `location /` (and `/_astro/`, `/tiles/`, `/404.html`, `/release.json`) → `root /mnt/rel/staged/v/${SIG_LATEST_PUB}`. The
  latest view is one immutable tree per release, so the flip is atomic per revision.
- `/r/`, `/s/`, `/releases/<pub>/` → `root /mnt/rel/staged`, gated by `map $uri_pub $promoted { default 0; include
  /mnt/rel/registry/conf/${SIG_CONF_GEN}/promoted.map; }` → **404 for any unpromoted namespace**. The staging service sets
  `SIG_STAGING=1` to bypass this gate and adds `X-Robots-Tag: noindex`.
- `/releases/`, `/releases/index.html`, `/releases/catalog.json`, `/releases/latest.json` → `alias
  …/conf/${SIG_CONF_GEN}/releases/`. The release tool is the **only** generator of the index (C4 NEW-10), and the Astro
  `releases/` page leaves the public allow-list.
- `include …/conf/${SIG_CONF_GEN}/withdrawn.conf`, `selectors.conf` (J3 §8.3), `labels.conf`. Every file in a generation is
  immutable, so every instance of a revision agrees (NEW-4).
- `add_header X-SIG-Release "${SIG_LATEST_LABEL} ${SIG_LATEST_PUB}"` and `X-SIG-Conf-Gen` on every response.

### 4.3 LB and API routing (G2 option 3a, adopted)

LB path rules `/v1/*` → serverless NEG `sig-api`, and `/intake/*` → `sig-intake` once G2 step 6 lands. Everything else goes
to `sig-web`. The site and the API then share one origin. `/terms` and `/openapi.json` routing is left to C2 NEW-8's owner.
`sig-api` mounts `gs://…-sig-release` read-only with `--release-registry /mnt/rel/registry` and reads the same `SIG_CONF_GEN`
(REL-05). Nginx does not proxy to Cloud Run, which avoids auth tokens and a second hop.

### 4.4 Publish classes (exactly four; J3 §8.6 (d))

| class | tool | may write | takes effect by |
|---|---|---|---|
| release | `sig-ops release promote` | `registry/events`, `registry/conf/<gen+1>` | revision roll (sig-api → sig-web) |
| rollback / clear | `sig-ops release rollback \| clear-latest` | the same | revision roll |
| withdrawal | `sig-ops release withdraw` | tombstones under `staged/**`, `registry/withdrawals.json`, `conf/<gen+1>`; R2/CDN purge | bytes immediately; aliases on roll |
| status | `sig-ops status publish` (J3 TX-07) | `status/**` only | next request (`max-age=0`) |

Legacy class (bucket root, ACT-05) is retired at REL-09.

---

## 5. Build → stage → verify → promote

### 5.1 The one command family (REL-03a)

`sig-ops release {cut, build, stage, verify, classify, promote, rollback, clear-latest, withdraw, status}`:

- Each verb takes the registry lock (`registry/LOCK`, create-if-absent generation precondition; a stale lock clears only with
  `--break-lock <reason>`), is resumable, and writes an event.
- Routine runs execute as the Cloud Run job **`sig-release`** under `sig-release-rt` (ACT-13 pattern: least privilege, never
  the Editor default SA).
- A Class S `promote` is run by the operator (§7.3).
- `--dry-run` is the default. `--apply` is required for any write.
- `status` prints the state machine for a candidate.

### 5.2 Stages

| stage | what happens | writes | duration / cost [est] |
|---|---|---|---|
| **cut** | T0 from the clock (§3.3). On-demand Cloud SQL backup (G2 AR-2). `sig-materialize` (derived tables; the same job the scheduler runs). `export.sh run` with `SIG_EXPORT_AS_OF=T0`, now passing the belief instant and returning `spine_watermark`/`sqitch_head`. Fetch the export to the build host (the job's disk) | backup, derived tables, `sig-restricted/exports/national/<T0>/` | 15–45 min; ≈ $0.10–0.30 (09-27 export: 12 min, ≈ $0.10) |
| **build** | allocate label; descriptor v2; `sig-exports release build` (records, landing, evidence, search indexes); Astro export-mode build **twice**: latest view (base `/`) → `v/<pub>/` and snapshot (base `/s/<pub>/`, J3 TX-13b) → `s/<pub>/`; `release.json` into both; J3 transparency and data bundles into `releases/<pub>/`; integrity manifest | local (job disk) | ≈ 20–40 min (P32.13: ≈98 s for 237k records; Astro ×2 ≈ 10–20 min) |
| **stage** | upload `staged/{r,v,s,releases}/<pub>/` with `if-generation-match=0` (a name collision refuses; nothing is overwritten) | release bucket | ≈ 1–2 h for ≈ 480k objects [est]; ≈ $2.4–2.6 in writes (G2 inference) |
| **verify** | V1–V14 against two private staging services: **`sig-web-staging`** (same `sig-web` image digest; `--no-allow-unauthenticated`; `SIG_STAGING=1`, `SIG_LATEST_PUB=<candidate>`) and **`sig-api-staging`** (same `sig-api` digest, IAM-only, current release = the candidate). The probe uses an identity token. A tagged revision of the public `sig-api` is **not** used, because tag URLs of an `allUsers` service are public and would expose the candidate before promotion | report in `registry/events` | ≈ 30–60 min |
| **classify** | Class R \| S (§7.3); for S, generate the agent-drafted readout (REL-06) | readout draft (committed in the ticket's PR, digests only) | minutes |
| **promote** | check the approval (standing go for R; signed readout naming this pub for S) → write `conf/<gen+1>` (promoted.map += pub, `latest.json`, `withdrawn.conf` from the **current** registry, `selectors.conf`, `labels.conf`, `releases/`) → roll `sig-api` (new env) → roll `sig-web` (new env; `min-instances=1` during the flip) → post-promote checks → event `promoted` | conf gen; two revisions | ≈ 5–10 min [est; revision roll time unmeasured] |

Timings are recorded for each run. The first two runs replace the estimates.

### 5.3 Page-level pinning (J3 NEW-1)

Every release ships **two** renderings of the same site build inputs:

- **latest view** `v/<pub>/`: served at `/…` while the release is latest. Its stamp says "latest view of `sig-…`" and links
  the pinned copy.
- **snapshot** `s/<pub>/`: served at `/s/<pub>/…` forever. It carries a `rel="latest-version"` link (RFC 5829) to the
  latest-view URL, and its own URL is its canonical.

The cite block (J3 TX-13a) links the snapshot URL. Records stay at `/r/<pub>/…` (P32.13). A reader's permalink is therefore
a path, not a query string, and the question "does nginx honour `?as_of=`?" goes away. Legacy selectors resolve at the edge
(J3 §8.3, `selectors.conf`): one match → 302, several → 409, none → 404 naming the current release.

**Containment rule (V5):** no same-origin link in `s/<pub>/` leaves `/s/<pub>/`, except to `/r/<pub>/`, `/releases/`,
declared latest-version links and external URLs. **This needs a `withBase()` refactor of 85 path sites (NEW-6).** Until it
lands, J3 §8.1's fallback applies: the stamp cites the data (`/releases/<pub>/` + figure pointer), and the page says
"latest view; an immutable copy of this page is not yet published" (agent-drafted, J3 §8.2).

### 5.4 Route allow-list

`ops/public_routes.toml` (ACT-05/G1 §3.2) applies to the top level of `v/<pub>/` and `s/<pub>/`. Added prefixes: `r/`,
`s/`, `releases/`, `status/`, `release.json`. Removed: `releases/` from the Astro tree. Any change to the allow-list makes
the release Class S. The file's sha256 is recorded in `release.json` (`routes_sha256`).

### 5.5 Verification suite (REL-04a/04b; gates promotion)

"S" = on the staging origin before promote. "P" = on every public origin (canonical LB host, `sig-web` run.app URL, and
the bucket URL while it exists) after promote. Every check writes a JSON result. **Any failure or skip blocks promotion**;
a waiver is possible only with Class S and is recorded in the readout.

| id | check | pass criterion | S | P |
|---|---|---|---|---|
| V1 | Integrity | `validate_release` complete; descriptor recomputes to the pub id; every integrity-manifest artifact under 1 MB, and a stratified 2 % sample of larger or record files, is fetched over HTTP and matches sha256 (the full tree is checked monthly by the audit) | ✓ | sample 200 |
| V2 | Identity and clock | v2 schema; `environment=production`; commit is 40-hex, pushed (`git ls-remote`/`gh api …/commits/<sha>` 200) and was clean; no version = `0.0.0`; §3.3 rules 1–6; label unique; `as_of_world` > current latest's | ✓ | — |
| V3 | Allow-list and absence | route set equals `public_routes.toml`; content assertions (curate banner, loopback form actions, `demo_*` slugs, `presentation/`); denied routes (`/curate/`, unpromoted `/r/<other>/`, `/intake/` and `/research-dossier/` unless in scope) → 404 | ✓ | ✓ all origins |
| V4 | Stamp and manifest | crawl: every HTML page has exactly one stamp whose label/pub/commit/as-of equal `release.json`; `<link rel="describedby" href="/release.json">`; `X-SIG-Release` on every response (P: equals `latest.json`) | ✓ | ✓ |
| V5 | Link crawl and containment | every same-origin href → 200 or a declared 410 (ACT-16/DR-C4-01); the §5.3 containment rule | ✓ | sample |
| V6 | Number truth: site = release files | DR-C3-15 recompute of headline, dossier and map figures from the bulk files; every `data-artifact` figure pointer resolves (PKG-10/J3 TX-09) | ✓ | — |
| V7 | API parity | §6.4: release-backed routes are byte-equal (canonical JSON) to the release files for every dossier scope and 20 coverage scopes; live-spine routes carry basis labels; `/`, `/health` name the release | ✓ (`sig-api-staging`) | ✓ |
| V8 | Attribution sanity | 0 rows with `attribution_required` and empty attribution (ACT-07/PKG-08 gate); `LICENCES.json` one licence plus attribution per compartment; map/tile attribution names the upstream holders (DR-C3-09); no source rendered as a bare id or a personal-handle id (DR-C3-13 list) | ✓ | — |
| V9 | Jurisdiction–coordinate sanity | 0 points at (0,0); 0 points where the swapped `(lon,lat)` falls inside the claimed jurisdiction and the unswapped pair does not (regression cases: the Nottingham/mark43 axis swap, I-stream NEW-2); points outside the claimed boundary are withheld or shown as a disclosed conflict (DR-C3-05); per-dossier geolocated counts equal the bulk recompute | ✓ | — |
| V10 | Withdrawal barrier | every disposition in the **current** registry → 410 with the `sig.tombstone/1` body on every alias (canonical, `index.html`, `.json`, no-slash, entity stub, `s/` and `v/` pages via J3 `page_index.json`); served `X-SIG-Conf-Gen` = recorded gen | ✓ | all new since last release + sample 20 |
| V11 | Zero-JS, budgets, a11y | 0 `<script>` on content pages; ≤ 150 KiB; island ceilings (ADR-134); axe 0 serious/critical on the Lighthouse URL set + landing + one snapshot page | ✓ | — |
| V12 | Scrub and secrets | J3 TX-01 scan over every file in the publish set; one hit aborts | ✓ | — |
| V13 | Disclosures | every descriptor disclosure renders on its target pages with the confirmed text digest; the "API is live" line; eval-status wording matches `evaluation.status` | ✓ | ✓ |
| V14 | Diff sanity | vs the current latest: per-compartment record Δ, source-set Δ, licence-set Δ, route-set Δ, template fingerprint Δ (the digest of a fixed-fixture build of the same commit), version/schema Δ. Results feed §7.3 | ✓ | — |
| P1 | Hosted probes | `uv run sig-ops probe-hosted` green; new `sig-probe` targets: `/release.json` pub = `latest.json` pub; release age < 35 days; served conf gen = latest recorded gen (a regression alarm); absence targets | — | ✓ |

**On failure.** A staging failure marks the candidate `failed`: fix forward with a new candidate, never patch staged bytes.
A post-promote failure triggers an **automatic rollback** to the previous generation (pre-authorised, D-G3-8), an alert to
‹operator address› (ACT-02), and an incident note.

---

## 6. Deploy provenance

### 6.1 The stamp (every HTML page; REL-02; agent-drafted wording)

> **Release sig-2026-10-15.1** · data as of 2026-10-15 06:02 UTC · built 2026-10-15 07:40 UTC from code
> [`‹commit8›`](https://github.com/SteveVitali/Eleutheria/commit/‹commit›) · `p-3f9ac21e…` *(illustrative values)*
> This is the latest view. Cite the fixed copy: `/s/p-…/dossier/tx/`. The public API also serves newer, unreleased
> records, labelled "live".

- The stamp is static HTML in `BaseLayout`, with no script (SIG-UI-036). The print stylesheet repeats it as a running footer
  (C2 NEW-6/NEW-23).
- On `s/` pages the second sentence becomes "This is the fixed copy of this page in release sig-…; the latest view is
  here."
- `<meta name="sig-release" content="<label> <pub>">` and `<link rel="describedby" type="application/json"
  href="/release.json">`.
- JSON twins (`/dossier/<x>.json`, C2 NEW-31) gain a top-level `release {label, publication_id, as_of_world}` block and a
  `licence` block.

**Interim (before REL-02; G2 ACT-06, text only):** "This site shows release sig-2026-09-27-ce480ab1, data as of
2026-09-27. The public API is updated continuously and may show newer records." (G2 §6, agent-drafted). The interim text
must not call the permalink "belief-pinned", because the release was not belief-pinned (NEW-2).

### 6.2 Machine-readable manifests

| file | schema | immutable? | fields |
|---|---|---|---|
| `/release.json` (inside `v/<pub>/` and `s/<pub>/`) | `sig.site-release/1` | yes | `label`, `publication_id`, `descriptor_sha256`, `as_of_world`, `as_of_belief`, `belief_pinned`, `spine_watermark`, `built_at`, `code {commit, url, repository}`, `versions {…}`, `evaluation {status, deferral_refs}`, `disclosures [ids]`, `routes_sha256`, `integrity_manifest` (path + sha256 of the release's `sig.release-integrity/1`) |
| `/releases/latest.json` (conf gen) | `sig.latest-pointer/2` | per generation | `label`, `publication_id`, `manifest_sha256`, `activated_at`, `conf_gen`, `class` (R\|S), `approval_ref` (standing-go id or signed readout path + sha256), `previous`, `serving {sig_web_image, sig_api_image}` (digests), `rolled_back` |
| `/releases/catalog.json` (conf gen) | `sig.publication-catalog/2` | per generation | each entry's state, label, pub, as-of, activation times, code commit, ★`code_tag` (filled in by a later generation once the operator has tagged, §9.5) |
| `/releases/<pub>/` landing | HTML + `release-notes.json` | yes | identity, dates, code, versions, disclosures, verification summary digest, sign-off class and reference, data changelog (J3 TX-14), downloads (J3 TX-10b) |

### 6.3 Headers

`sig-web`: `X-SIG-Release: <label> <pub>`, `X-SIG-Conf-Gen: <n>`. `sig-api`: `X-SIG-Release` (the current release),
`X-SIG-Basis: release | live-spine`, `X-SIG-Code: <commit12>`. The API image carries `org.opencontainers.image.revision`
and `SIG_CODE_COMMIT`, baked in at build.

### 6.4 API/site parity rule (REL-05; SIG-REL-D10)

| class | routes (today's `routes.py`) | must |
|---|---|---|
| **release-backed** (the site shows the same answer) | `/v1/dossier/{scope}`, `/v1/coverage/{scope}`, `/v1/export`, `/v1/changes`, `/v1/releases/**`, J3 `/v1/sources…` (TX-15) | answer from the **current promoted release's files** (or `?release=<pub>` for any promoted release); body `release {label, publication_id, as_of_world}`; `X-SIG-Basis: release`. Unknown scope → 404, never a placeholder (DR-C3-12; ACT-08 removes the placeholder) |
| **live-spine** | `/v1/claim`, `/v1/entity`, `/v1/resolution`, `/v1/evidence`, `/v1/contradiction`, `/v1/task`, `/v1/crosswalk`, `/v1/search` | body `basis {kind: "live-spine", as_of: <now>, spine_watermark, latest_release {label, publication_id}}`; `X-SIG-Basis: live-spine`. The OpenAPI description says "newer than the site; not a citation" |
| service | `/`, `/health` | add `release`, `code_commit`, `image` (digest from `SIG_IMAGE_DIGEST`, set at deploy) |

V7 enforces the rule. A promotion that moves the site to a release the API cannot serve is refused.

---

## 7. Cadence and sign-off

### 7.1 What the drift numbers say

- Net drift was measured at **+91,483 claims (+3.8 %)** in ≈ 3.65 days (GT-14). That is ≈ 25k/day, an inference from a
  single reading.
- Emitted drift was **≤ 156,273** (G1).
- The first-fire wave will emit ≈ 1.4 M more, mostly duplicates.
- A monthly cadence therefore leaves the site 5–25 % behind the spine by month-end, if the rate holds (**inference**).
- The status lane (J3 TX-07) and the stamp's "API is newer" line disclose that gap between releases. A cadence faster than
  twice a month buys little: each release costs ≈ $2.5 in object writes and ≈ 3 GB of storage [est], and when a Class S
  sign-off is needed it costs the operator 1–2 hours.

### 7.2 Schedule and triggers (REL-07; proposal for D-G3-4)

| trigger | rule | class default |
|---|---|---|
| scheduled | Cloud Scheduler `sig-sched-release-cut`, cron `0 14 15 * *` (day-of-month only; G1 cron lint). The 15th falls after the day 6–13 batch window, so monthly registries are complete | R if eligible |
| data delta | daily evaluator in `sig-probe`/status lane: `net_new = eligible(spine_watermark) − release.watermark`. Cut when `net_new ≥ 10 %` of the release's published claims **and** ≥ 14 days since the last promotion | R if eligible |
| max age | alert at 35 days; cut at 35 days if no cut is running | R if eligible |
| fix ready | a public-facing fix merged on the stack with a green G3a head | **S** (code changed) |
| source change | Stream I sources after HG-03, or a lane change | **S** |
| withdrawal-driven | within 7 days of a withdrawal that tombstones latest-view pages, so the latest view has no 410 holes | R (same code) |
| freeze | no `cut` starts in AR-3 windows; `withdraw` and `rollback` are always allowed | — |

The weekly `sig-materialize` (G1 §3.6) is kept, so the API's materialized views lag live claims by at most 7 days.

### 7.3 Sign-off scope: which changes need a fresh signature (proposal for D-G3-3; the operator ratifies)

The chain calls the per-release operator signature "HG-11". Its governance half (two independent reviewers) is an operator
waiver (E1-01, GT-15), so the signature is the operator's own publication decision. This rule names it the **release go**,
in the HG-11 decision domain, and claims nothing about reviewer independence.

| Class **S** — candidate-specific readout, signed verbatim (agent-drafted readout, REL-06) | Class **R** — routine refresh under a standing go |
|---|---|
| the first release under this model (G2 ACT-24) and the first release after any descriptor schema change | same `code.commit` as a release the operator signed under Class S |
| any code change (so data refreshes normally reuse the last signed commit) | same versions: ruleset, resolver, policy, projection, ontology, descriptor schema |
| a route allow-list change; a new public surface | same allow-list, compartments, licences, attribution texts and disclosures, and the same evaluation status |
| a new compartment, licence, attribution text or redistribution lane | same source set, or fewer **only** through recorded withdrawals |
| a source's first public appearance (Stream I batches, after HG-03) | V14 bounds: total published records −2 % … +15 %; no compartment < −5 % or > +50 %; no source loses > 20 % of its records |
| a change of disclosure text or evaluation status (e.g. provisional → certified) | all V1–V14 green, **zero waivers** |
| a Part VIII-relevant change (a new sensitive category, officer-naming, SIG-PUB-017 jurisdictions) | `environment=production`, cut by the scheduled or drift trigger, outside freezes |
| a `--replay` or `--emergency` cut; any waiver; any V14 anomaly; a classifier error | — |

- **Needs no readout:** `withdraw`, `rollback` to an earlier promoted release, `clear-latest`, and the automatic post-promote
  rollback. Each still records an operator go or the pre-authorisation id.
- **Fail-closed:** anything the classifier cannot compute is Class S.
- **Agents:** an agent may *run* a Class R promotion under the standing go. An agent may never promote Class S, never sign,
  and never treat silence as approval.

**Standing-go text** (agent-drafted; the operator confirms it verbatim or edits it; recorded in GATE DECISIONS with
`date -u`):

> "I authorise routine data refreshes of SIG to be published without a new sign-off when `sig-ops release classify` reports
> Class R, every verification check passes with no waivers, and the code is exactly the code of a release I signed. Each
> such release is emailed to me with its diff and check results. This covers Class R only, and I can revoke it at any time."

**Notification.** Every promotion, whether R or S, rollback or withdrawal emails ‹operator address›. The email carries the
label, pub, class, approval reference, the V14 diff table and the verification summary (ACT-02 channel). A monthly digest
lists the Class R promotions, as the operator's review point.

---

## 8. Rollback and withdrawal

### 8.1 Pointer rollback (REL-08)

`sig-ops release rollback --to <pub|label> --reason <text>` runs as follows:

- `exports.release.rollback` (GT-3) re-applies the **current** withdrawals.
- It writes `conf/<gen+1>` with `latest = <pub>` and rolls `sig-api` and `sig-web` with the new env, then runs the P checks.
- **Cloud Run traffic reversion to an older revision is forbidden.** An old revision carries an old `SIG_CONF_GEN` and would
  serve routes withdrawn since then (ADR-132's "a withhold under R2 still denies under a rollback to R1").
- The P1 conf-gen regression probe alarms if an older generation is ever served.
- Target: ≤ 10 min from command to verified [est; measured in REL-11].

### 8.2 No prior release: the legacy floor

The first model release has no predecessor (G2 R15). REL-09 fixes this as follows:

- It imports the then-live root site (post-ACT-06/07) as `staged/v/legacy-<YYYYMMDD>/`. The import is not a publication:
  it has no pub id and is labelled `legacy-…`.
- It serves that tree through the new nginx, byte-compared route by route against the old root: a **zero-diff dark cutover**.
- The legacy tree becomes the rollback floor for the first promotion.
- `clear-latest` stays available for the archive-only case (`/releases/` shows no current release).
- A live prior-pointer rehearsal happens on the **second** release (REL-11), which closes G2 R15.

### 8.3 Withdrawal (the barrier live nginx cannot honour today: G2 NEW-2, NEW-4 here)

`sig-ops release withdraw --disposition <file> --authority <ref>` runs these steps in order:

1. INSERT the ADR-124 disposition, append-only.
2. `record_withdrawal` → `apply_withdrawals` over **every** staged namespace (`r/`, `s/`, `v/`, `releases/*/data`). The
   canonical bytes are replaced by the `sig.tombstone/1` body, or removed whole for artifacts, immediately.
3. Emit `conf/<gen+1>/withdrawn.conf` with alias coverage (PKG-03b/ED-16: `index.html`, `.json`, trailing slash, entity stubs,
   `page_index` pages).
4. Roll `sig-api`, then `sig-web`.
5. Purge caches (§8.5).
6. Probe every alias on every origin → 410.
7. Record a receipt.

**Technical SLA:** live on every alias within **15 minutes** of the command [target]. Policy SLAs stay in `takedown.toml`.
When latest-view pages carry tombstones, a withdrawal-driven re-cut follows within 7 days (§7.2).

### 8.4 Tombstones

A tombstone is `sig.tombstone/1` served with **410** on every alias. It carries `target_kind`, `target_id`,
`withdrawn_at` (from the clock), a public-safe `reason_class`, `disposition_ref`, `superseded_by` (if any), the release
label, and the dispute contact (Q-29). A tombstone is itself immutable per disposition. A later reinstatement is a new
disposition and a new release, never an edit.

### 8.5 Caches, CDN and mirrors

- **Today:** there is no CDN (G1). `Cache-Control` on `/r/`, `/s/` and `v/` pages stays `max-age=300, must-revalidate`, so
  a browser or shared cache holds a withdrawn page for ≤ 5 minutes. `_astro/` under `v/<pub>/` can stay `immutable`, because
  it is scoped to the release.
- **If Cloud CDN is enabled:** `gcloud compute url-maps invalidate-cdn-cache sig-web-urlmap --path "<route>*"` joins
  `withdraw` **[unverified flags]**.
- **With J3's R2 mirror (TX-11):** keys are content-hash with `immutable`, so expiry never helps. `withdraw` deletes the
  object on R2, purges the Cloudflare cache by URL (token in Secret Manager, HG-09) and verifies 404 on the mirror
  (SIG-TRANSP-D20).
- Torrents, Zenodo deposits and downloaded copies cannot be recalled (J3 §9.3). `/releases/<pub>/` says so plainly.

### 8.6 Object versioning and takedowns

The release bucket is versioned, so a mistaken overwrite can be recovered for 30 days. For Part VIII or legal takedowns,
`withdraw --purge-versions` also deletes the noncurrent versions of the withdrawn objects. These are bucket objects, not the
claim spine, so the append-only rule is untouched. The event records it.

---

## 9. Codebase versioning

### 9.1 Today

There are no tags locally or on origin, and no GitHub release (GT-13; A3 NEW-3: the HG-05 "integrate & release v0.1.0" row
is missing). `CHANGELOG.md` holds `[0.1.0] — unreleased`. Versions disagree: 14 pyprojects say `0.1.0`, 11 `__version__`
strings say `0.0.0`, and `web/package.json` says `0.1.0` (NEW-3). Production runs unmerged stack commits (`sig-api`
`ba3dca61`, `sig-web` `5c064881`; G2 §1). This is the operator's chosen workflow (§7.1 Q-11).

### 9.2 Tags on `main` (operator actions; agents never tag or push `main`)

| tag | when | points at |
|---|---|---|
| `v0.1.0` | after the operator's #141–#190 sitting (H1/H2 §2.4) | the `main` merge commit whose tree equals `b051732c^{tree}` (H1 tree invariant) |
| `v0.2.0` | the sitting that includes the release model (REL-01…REL-09) and the first model release (ACT-24) | that sitting's final merge commit |
| `v0.N.0` / `v0.N.P` | each later sitting: **minor** for any public route, API, schema, descriptor or ontology change; **patch** for fix-only sittings | the final merge commit |
| `v1.0.0` | an operator criterion, proposed as: the human-evaluation spine complete (HUMAN-H4/H5) **and** the HG-11 governance prerequisites met without waiver (E1-01) | — |

- Tags are annotated: `git tag -a v0.N.0 <sha> -m "<CHANGELOG section>"`, then `git push origin v0.N.0`. The tag object
  carries the true date, so no hand-typed date appears anywhere (B1).
- Agents prepare `docs/build/reports/releases/TAG_v0.N.0.md` in the last stack PR of the range. It holds the tree hash, the
  green CI run ids, the included PRs, and the production release labels built from commits in the range.

### 9.3 One version source (REL-10)

- Every package's `__version__ = importlib.metadata.version("<pkg>")`.
- A `make check` test asserts that `pyproject` = `__version__` = `web/package.json`.
- `scripts/bump_version.py <x.y.z>` bumps all 14 packages and the web package together, in the stack PR that precedes a tag.
- `resolver_version` = `resolution` version + `+g<commit8>`.

### 9.4 CHANGELOG discipline

- `## [Unreleased]` is split into Keep-a-Changelog sections (Added/Changed/Fixed/Removed/Security). Each entry names its
  ticket and requirement ids.
- **CI check** (docs job): a PR that touches `web/src/pages/**`, `web/src/layouts/**`, `api/src/api/{routes,app,models}.py`,
  `exports/src/exports/{release*,spine_export,manifest}.py`, `ops/public_routes.toml`, `ops/disclosures.toml`, `policy/**` or
  `ontology/src/**` must change `CHANGELOG.md`. The alternative is a `Changelog: none (<reason>)` commit trailer.
- At a tag, the section heading becomes `## [0.N.0] — tagged by the operator (see git show v0.N.0)`, avoiding a typed date.
  The section ends with "Production releases built from this range: …".
- **Data changes are not code changes.** They go in each release's data changelog (J3 TX-14, `/releases/<pub>/`).

### 9.5 Linking releases and code

- Each release landing names its commit (a GitHub URL; the repo is public).
- A release built before its commit is tagged shows "untagged". The next config generation's catalog adds `code_tag` once
  `git describe --contains` finds a tag, as a mutable overlay. The immutable landing is not edited.
- Each CHANGELOG version section lists the release labels it produced.
- A GitHub Release per tag is optional and operator-run, with the CHANGELOG section as its body.

---

## 10. Draft requirements (provisional `SIG-REL` family; T1 numbers them or folds them)

| id | requirement (draft) | acceptance |
|---|---|---|
| SIG-REL-D01 | Every production release MUST have a content-addressed publication id and an immutable human label `sig-YYYY-MM-DD.N`: the UTC date of the data as-of plus an ordinal per date, never reused. | the label→id map never changes across generations (test over catalog history); a duplicate label refuses |
| SIG-REL-D02 | The release descriptor MUST bind: the spine snapshot (world and belief instants, watermark, environment); the clean, pushed code commit; ruleset, resolver, policy, projection and ontology versions from one version source; the publication-gate digests; the evaluation status; the disclosure digests; and `built_at`. | descriptor recompute; `promote` refuses a dirty tree, an unpushed commit, a `0.0.0` version, a non-sha revision or a v1 descriptor |
| SIG-REL-D03 | Every date in a release MUST come from the clock at the moment it describes; none may be later than the build instant. Replays MUST be labelled. | §3.3 guard tests (planted future date, skewed host clock, typed `--as-of` without `--replay`) |
| SIG-REL-D04 | Public release bytes MUST change only through the release tool (promote, rollback, withdraw) or the status publisher (`status/**`). Release storage MUST NOT be publicly readable except through the serving layer. *(Refines SIG-OPS-004.)* | the IAM live-diff shows no `allUsers` and no writer besides `sig-release-rt`/`sig-status-rt`; hand-sync grep over runbooks = 0 |
| SIG-REL-D05 | After staging, a release's bytes MUST NOT change except by a tombstone or removal under a recorded disposition. | the monthly digest audit over all promoted namespaces is 0-diff (tombstones match receipts); a dry-run of any tool shows 0 deletions |
| SIG-REL-D06 | Promotion MUST switch the latest view, `/releases/latest.json` and the API's current release together, by metadata only. A candidate MUST NOT be publicly reachable before promotion. | an unpromoted pub → 404 on all public origins; post-promote V4/V7 agree; conf gen served = recorded |
| SIG-REL-D07 | A candidate MUST pass V1–V14 on a private staging origin, and V1/V3/V4/V5/V7/V10/V13/P1 on every public origin after promotion. A post-promotion failure MUST roll back automatically. | a planted failure in each check blocks promotion (test); a planted post-promote failure restores the previous pub within 10 min (rehearsal) |
| SIG-REL-D08 | A page snapshot MUST contain no same-origin link outside its own `/s/<pub>/` prefix, except to `/r/<pub>/`, `/releases/` and declared latest-version links. *(Complements SIG-TRANSP-D23.)* | containment crawl = 0 escapes |
| SIG-REL-D09 | Every HTML page MUST show the release label, data as-of, code commit (linked) and build time, and link `release.json`. Every response MUST carry `X-SIG-Release`. *(Refines SIG-OPS-004's release-id clause; closes F-11, DR-C3-14.)* | V4 crawl = 100 %; header probe |
| SIG-REL-D10 | Every API route whose answer the site shows MUST serve the current promoted release's files and name that release. Every other route MUST label itself live-spine, with its watermark and the current release id. | V7 parity test; OpenAPI lint for the basis field |
| SIG-REL-D11 | A release MUST be cut at least monthly outside the batch window, and early when net-new publishable claims reach 10 % and 14 days have passed. Release age MUST be alerted at 35 days. *(Specifies SIG-OPS-008's triggers; S1 merges the two.)* | scheduler job present (live-diff); the drift evaluator is unit-tested; a release-age probe exists |
| SIG-REL-D12 | Promotion MUST be Class S (a candidate-specific signed readout) unless the classifier proves every Class R condition. Class R requires a recorded, revocable standing operator go. The classifier MUST fail closed. | classifier matrix test (one planted change per S condition → S) |
| SIG-REL-D13 | Rollback MUST re-apply the current withdrawal set and MUST NOT revert serving configuration. A withdrawal MUST be live on every alias of every release, snapshot, latest view, download and mirror within 15 minutes, with a dated tombstone. | rehearsal: withdraw → 410 on all aliases ≤ 15 min; rollback after a withdrawal still 410s |
| SIG-REL-D14 | Code versions MUST come from one source. Semver tags MUST be placed on `main` by the operator after merge sittings. Public-behaviour changes MUST carry a CHANGELOG entry, and release notes MUST link commits or tags to release labels. | version-equality test; CHANGELOG CI check; the landing names the commit |

---

## 11. Round-11 ticket outline

Sizes follow J3 §12: **S** ≈ half a fresh-context run, **M** one run, **L** split a/b. "Live" means the ticket has a
production stage that needs an operator go. The order below is dependency order.

| key | title | size | scope (one line) | depends (G2 ACT / J3 TX / F5 PKG) | live / gate |
|---|---|---|---|---|---|
| REL-10 | Versioning discipline + one version source | S | `importlib.metadata` versions, equality test, bump script, CHANGELOG CI check, tag procedure + `TAG_v0.N.0` template, `v0.1.0` instructions | none; lands day 1 (coordinate H2 TC-PIN) | tags = operator |
| REL-01 | Release identity v2 + clock guards | M | descriptor v2 (§3.2), label allocation, export id + `BuildSpec` with instants/watermark/commit (NEW-1/2), belief instant passed by `export.sh`, §3.3 guards; **one ADR** extending ADR-132, merging J3 TX-13b's descriptor fields | ACT-12 (B1 constants, `p-17b713` supersession) first; REL-10 | — |
| REL-02 | Provenance stamp, `release.json`, headers | M | `BaseLayout` stamp + print footer, `release.json`, meta/link, JSON-twin `release` block, API `/`/`/health` fields, `X-SIG-*` headers | REL-01; ACT-06 (interim stamp text); J3 TX-13a owns the cite block (adjacent) | via republish |
| REL-03a | Release pipeline, layout, private bucket, staging origin | M | `sig-ops release` state machine + lock + events, `…-sig-release` bucket (IaC), `staged/{r,v,s,releases}` layout, `stage` with generation preconditions, `sig-web-staging` + `sig-api-staging` (IAM-only), `sig-release` job + SA | ACT-05/PKG-04 publish half (allow-list, assertions); ACT-01 (versioning, QA-7); ACT-13 (least-privilege job pattern) | infra create — op go |
| REL-03b | Templated nginx, config generations, metadata-only promotion | M | envsubst template (§4.2), promoted-set map, `conf/<gen>/`, `promote`, release tool owns `/releases/` index, per-release entity stubs, revision rolls by digest | REL-03a; ACT-17 (P32.13 nginx roll, LB rules, registry mount); PKG-03b (alias coverage, tombstone body) | via REL-09 |
| REL-08 | Rollback, withdrawal, purge, runbook, legacy floor | M | `rollback`, `clear-latest`, `withdraw` (+ `--purge-versions`), R2/CDN purge hooks, legacy-floor import, conf-gen regression probe, RUNBOOK sections republish/rollback/withdrawal (G1-15 owns the file) | REL-03b; J3 TX-11 (mirror hook, when it exists) | rehearsal in REL-09/REL-11 |
| REL-04a | Verification suite A | M | V1–V5, V11–V13 as `sig-ops release verify`, staging + public modes, JSON results | REL-02, REL-03a; ACT-16 (crawl gate); J3 TX-01 (scrub) | — |
| REL-05 | API release parity | M | the API reads `SIG_CONF_GEN`/latest; release-backed routes from release files; basis labels; `?release=`; headers | ACT-08/PKG-09a (placeholder purge), ACT-11 (API roll), ACT-17 (mount); J3 TX-15 coordinates | API roll — op go |
| REL-04b | Verification suite B + post-promote auto-rollback | M | V6–V10, V14, P1 probes into `cadence.toml`, auto-rollback | REL-04a, REL-05, REL-08; PKG-08/ACT-07 (attribution gate), PKG-06a/b (geometry), PKG-10 (DR-C3-15, figure pointers), ACT-02 (alert delivery) | — |
| REL-09 | Dark cutover to the release layout | S | import the legacy floor, roll `sig-web` onto the templated image with `SIG_LATEST_PUB=legacy-…`, byte-compare every allow-listed route, retire the bucket-root serving path | REL-03b, REL-04a, REL-08; ACT-06/07 republishes done | **op go**; no visible change |
| REL-06 | Classifier, standing go, readout generator | M | `classify` (§7.3 matrix, fail-closed), template fingerprint, agent-drafted readout generator, notification email, the sign-off-scope ADR | REL-04b; J3 TX-14 (diff files; the first release is the baseline) | operator ratifies D-G3-3 |
| *ACT-24* | *first model release (G2 step 7, D-R10-PUBLISH-1)* | — | *executed with `sig-ops release cut…promote`; Class S; the J3 TX-13b `/s/` exposure rides here* | REL-01…REL-09, REL-06; G2 steps 3–4 | ***HG-11*** |
| REL-07 | Cadence automation | M | `sig-sched-release-cut` monthly job, drift evaluator (shared with TX-07), max-age alert, AR-3 freezes in tooling, weekly `sig-materialize` | REL-03a, REL-06; ACT-13; J3 TX-07 | new scheduler job — op go |
| REL-11 | Second-release acceptance | S | the first Class R promotion under the standing go (if eligible), live prior-pointer rollback rehearsal + restore, withdrawal rehearsal on a low-stakes record, measured timings replace §5.2 estimates | REL-07, REL-08; ACT-24; the second cut | **live**; standing go (D-G3-3) |

**Minimum set for ACT-24:** REL-10, 01, 02, 03a, 03b, 08, 04a, 09, 06, plus REL-05 in "label-only" mode. In that mode the
API adds basis labels and release headers, but release-backed serving can follow before REL-11.

**Exactly-one ownership (P9):**
- ACT-05 keeps the allow-list, content assertions and absence probes.
- ACT-17 keeps LB rules, the registry mount and the first P32.13 nginx roll.
- PKG-03b keeps alias coverage and the tombstone body.
- J3 TX-13b keeps `/s/` build + `page_index` + `selectors.conf` and **the `withBase` refactor (NEW-6)**.
- REL-01 absorbs the descriptor-v2 ADR.
- REL-02 absorbs F-11 and DR-C3-14.
- REL-07 absorbs G1-07/F-08's cadence half. The status half goes to TX-07.
- REL-08 absorbs G2 R15 and C4 NEW-10's deletion half, which is already fixed by construction: no tool deletes staged
  prefixes.

---

## 12. Operator decisions needed

| id | question | recommendation |
|---|---|---|
| **D-G3-1** | Adopt this model (identity v2, a private release bucket mounted by `sig-web`/`sig-api`, LB path rules, metadata-only promotion, conf generations) via a new ADR extending ADR-132? | Yes |
| **D-G3-2** | Label format `sig-YYYY-MM-DD.N` (data date + ordinal)? | Yes |
| **D-G3-3** | The §7.3 sign-off scope and the standing-go text for Class R, including the V14 bounds | Yes, as drafted; revisit after 3 Class R promotions |
| **D-G3-4** | Cadence: monthly on the 15th at 14:00Z; early at ≥ 10 % net and ≥ 14 days; 35-day age alert | Yes |
| D-G3-5 | May production releases use unmerged stack commits (pushed, G3a-green head, clean tree), as today? | Yes (matches Q-11); the tag follows the merge sitting |
| D-G3-6 | Tags: `v0.1.0` after the #190 sitting, `v0.2.0` at the first model-release sitting, and the §9.2 semver policy and 1.0 criterion | Yes |
| D-G3-7 | Legacy buckets: keep the `sig-web` root 90 days after REL-09, then delete; freeze the `sig-public` root with a README and retarget the probes, until J3 TX-11 | Yes |
| D-G3-8 | Pre-authorise automatic rollback when post-promote checks fail | Yes |
| D-G3-9 | A 15-minute technical SLA for a withdrawal to reach every alias | Yes |
| D-G3-10 | Private `sig-web-staging` and `sig-api-staging` services (≈ $0/mo at min 0) and the release bucket's cost (≈ 3 GB/month growth, ≈ $0.06/month added per month [inference]) inside the Q-10 ceiling | Yes |

---

## 13. Risks

| id | risk | mitigation |
|---|---|---|
| RR-1 | Scope: 13 runs on top of G2's 25, J3's 16 and F5's 13 | the ACT-24 minimum set (§11); REL-07/11 after the first release |
| RR-2 | Revision-roll latency and cold starts with a gcsfuse mount make the flip slow or flaky (unmeasured) | `min-instances=1` during promote; measure in REL-09; the flip is atomic per revision regardless |
| RR-3 | gcsfuse and nginx over millions of accumulated objects (≈ 480k per release) slow `try_files` (unmeasured, **inference**) | measure with the P32.24 corpus ×N in REL-03a; gcsfuse metadata cache; fall back to an LB backend bucket for `/r/` if needed (a new decision) |
| RR-4 | The `withBase` refactor (NEW-6) delays snapshots | J3 §8.1 fallback for the first release; containment crawl keeps the refactor honest |
| RR-5 | Class R becomes a rubber stamp | strict bounds; fail-closed classifier; an email per promotion; a monthly digest; revocable go |
| RR-6 | A wrong host clock or a typed date re-creates B1 | §3.3 guards incl. the external clock check |
| RR-7 | A traffic reversion by hand resurrects withdrawn routes | forbidden in the runbook; P1 conf-gen regression alarm |
| RR-8 | Many withdrawals mean many revisions (the Cloud Run revision retention limit is unverified) | prune non-serving revisions older than 30 days in `withdraw`; **[unverified]** limit |
| RR-9 | The API cannot serve some site-shown answer from release files in time for ACT-24 | label-only mode (basis + headers) is acceptable for ACT-24; full parity before REL-11 |
| RR-10 | Citation churn: v1-era URLs (`?as_of_world=…`, 09-24/09-27) were never pinned | `selectors.conf` 404 page names the current release (J3 §8.3); the landing explains that pre-model releases were unpinned (NEW-2) |

---

## 14. Interfaces

- **G2.** Step 0 (ACT-05/06/07) stays on the legacy path. ACT-12 precedes REL-01. ACT-17 is the base image for REL-03b.
  Step 3's candidate (ACT-15) is built by `sig-ops release build` once REL-01 lands; otherwise with P32.23a and then rebuilt.
  Step 7 (ACT-24) is the first `promote` and supersedes G2's "publish-web --apply" line for the staged tree. G2 R12 (API
  numbers move while the site stays) is answered by §6.4 and §7.2.
- **J3.** §8.6 items (a)–(e) are decided in §0 and §4.4. TX-13a sits next to REL-02. TX-13b ships in ACT-24. TX-07 is
  publish class 4. TX-11's purge hooks go into REL-08. TX-14's diffs feed V14 and REL-06. D-J3-3's premise (a private repo)
  is superseded by GT-13.
- **F5.** PKG-04's "G3 decides topology" is answered by §4.3. PKG-03b precedes REL-03b. PKG-06, PKG-08, PKG-09a and PKG-10
  are check providers for REL-04b and REL-05.
- **G1.** SIG-OPS-003 (allow-list) is consumed. SIG-OPS-004 is refined by D04/D09. SIG-OPS-008 is specified by D11. The
  runbook ticket (G1-15) hosts REL-08's sections. The `live-diff` tool checks D04's IAM.
- **H2.** Tags follow §2.4 sittings. The CHANGELOG check joins the docs job. G3a-green heads are a promote precondition.
- **B1/B4.** §3.3 applies the B1 clock rules to releases. B4's date guard should scan `release.json` and landings too.
- **C6/S1.** Findings routing below. C2 NEW-4/F-07's user-facing half is closed by §5.3 plus TX-13; NEW-2 here is the
  data-layer cause.

---

## 15. New findings (`findings/incoming/G3.csv`)

| id | title | sev |
|---|---|---|
| NEW-1 | The public release id is not content-addressed. `data_release_id` = `sig-<as-of date>-<sha256(date, belief date, ruleset, resolver)[:8]>`, with no spine content, watermark or commit, so different exports on the same day share one id. The two 2026-09-24 exports (different manifests, md5 `vkygLoO8…` vs `fvhR4VyZ…`) necessarily carry `sig-2026-09-24-bd01cb94`. A fixture export and a production export on one day would collide. The id is also the Zenodo version identity | S2 |
| NEW-2 | The live release was not belief-pinned. `export.sh` never passes `--belief`; the export read current belief and recorded `as_of_belief` as the date. All 55 dossier-index entries say `belief_pinned: false`, while every page calls its permalink "Belief-pinned (reproducible after SIG corrects itself)". The recorded cut cannot be reproduced even by a working resolver | S2 |
| NEW-3 | Release code identity cannot be verified. `resolver_version` and `renderer.version` are the placeholder `0.0.0` in every release (09-24, 09-27 and the signed `p-17b713`), because 11 of 14 packages hard-code `__version__ = "0.0.0"` while every pyproject says `0.1.0`. `renderer.revision` is unchecked free text (`composed_verify` default `"p33.2"`). SIG-FIND-001 and SIG-EXPORT-003 are unmet | S2 |
| NEW-4 | The withdrawal deny include is read only when nginx starts; no reload or roll path exists. A withdrawal written to the gcsfuse-mounted bucket leaves aliases served 200 by running instances while new instances deny them (latent: the live image has no include, G2 NEW-2) | S2 |
| NEW-5 | Release trees and staging registries are committed to the public repository (898 `/r/p-…` files and 84 registry files under `docs/build/reports/`). The P32.25 "staging" registry is therefore public, and a real candidate staged the same way would be published before sign-off | S3 |
| NEW-6 | J3's `/s/<pub>/` snapshot build assumes base-path support the web code lacks: no `base` in `astro.config.mjs`, 0 `BASE_URL` uses, and 85 root-absolute path sites in 36 files. Without a refactor, snapshot pages link out of the pinned copy | S3 |

Related earlier findings, not re-raised: F-02, F-07, F-08, F-11, F-14, F-15; C2 NEW-4/6/23/31; C4 NEW-9/10/11/14; G1 NEW-4/5/6/13;
G2 NEW-2; J3 NEW-1/NEW-4; B1 NEW-2; A3 NEW-3; E1 NEW-14; E1-01; ED-16, ED-21…ED-24.

---

## 16. Command log and limits

All reads were read-only. The project is `zeta-medley-508121-u7`. Times are from `date -u`.

| time | command (abridged) | used for |
|---|---|---|
| 18:32:55 | `date -u`; `git status`; `ls` of PD | header |
| 18:33–18:35 | `sed`/`grep` over META_PLAN, G2, J3, JOURNEYS, DATA_TRUTH, G1, F5 (+ `eng_debt.csv`), H2, B1, E1; FINDINGS + incoming titles | §1, §14, §15 |
| 18:33–18:45 | code reads: `exports/src/exports/{release,manifest,spine_export,shaping,cli}.py`, `ops/src/ops/{publish,deploy,release_serving,release_publish_verify,composed_verify}.py`, `ops/gcp/{web,export}.sh`, `ops/web/{nginx.conf,Dockerfile}`, `web/astro.config.mjs`, `web/src/{components/Citation.astro,layouts/BaseLayout.astro,pages/releases/index.astro}`, `api/src/api/{app,routes,release_search,cli,models}.py` | §1–§6 |
| 18:35:42 | `gh repo view SteveVitali/Eleutheria --json visibility,defaultBranchRef,latestRelease` → PUBLIC, `latestRelease: null`; `git tag -l` → 0 | GT-13 |
| 18:36:03–18:36:12 | `gcloud storage ls gs://…-sig-{public,web}/`; `gcloud storage buckets describe` (versioning, soft delete); `ls -l` of `index.html`, `manifest.json` | GT-1, GT-10 |
| 18:42:27 | `gcloud storage ls -l -r gs://…-sig-{web,public}/` → 289 objects 01:33:56–59Z; 134 objects 01:30:28–01:31:17Z | GT-1 |
| 18:46:24–18:46:36 | `gcloud storage ls -l` and `objects describe` of `…-sig-restricted/exports/national/2026-09-24T{150000,154017}Z/manifest.json` (size 34,631 each; md5 differ; bundle totals 924,457,431 vs 924,496,399 B) | NEW-1 |
| 18:47:42 | web link-site grep (85 sites, 36 files, 0 `BASE_URL`) | NEW-6 |
| 18:47:56 | `uv run python -c` recompute of `BuildSpec.release_id()` for 09-24/09-27/09-28 → `bd01cb94`/`ce480ab1`/`30e3add6`; `export.sh` belief grep → 0; `__version__ "0.0.0"` count → 11; `composed_verify.py:256` | NEW-1, NEW-3 |
| 18:49:18 | `belief_pinned` count over the C3 capture of `web/dossier_index.json` (sha256 `a4938e68…`) → 55 false, 0 true; nginx include / reload grep; committed release-tree counts (898, 84) | NEW-2, NEW-4, NEW-5 |

**Limits.**
- No hosted database query and no object-content read were made. The same-day id collision for the 09-24 pair is
  **inferred** from code and the manifests' identical sizes and differing hashes; the manifests were not opened.
- Revision-roll time, gcsfuse behaviour at millions of objects, the official nginx image's envsubst entrypoint and the
  Cloud Run revision-retention limit are unverified.
- All costs are list-price inference.
- No secret value was read (P14).
- Nothing was committed, and no file outside the two declared outputs was written.

---

Work window closed 2026-09-30T18:55:43Z (`date -u`). Findings file: `findings/incoming/G3.csv` (6 rows, NEW-1…NEW-6).
