# LABEL-BIND-FIX — `D-P37.65a-7` machinery half: `verb_build` binds its label post-build

- **Scope:** the machinery half of `D-P37.65a-7` (`docs/tickets/DEFERRALS.md`):
  `verb_build` allocated `publication_id: null` then passed
  `labels_registry=None`, so `record_label_publication`
  (`exports/src/exports/release_identity.py:283-304`, only called at
  `exports/src/exports/release.py:876-877`) was unreachable — every
  ops-path label stranded. The residue bind
  (`sig-2026-11-25.1` → `p-31371dfb…`) is **not** this leg's write — it is
  the resume leg's, operator-authorised under `99018e1b`
  (GATE DECISIONS `dc7e98ad`, "Bind it now"). This leg fixes the machinery
  and documents the exact invocation.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-label-bind-fix` (worktree
  `/private/tmp/sig-label-bind`), PR base
  `r11/P38.3c-round11-integration-plan-2`.
- **Deferral / triage refs:** `docs/tickets/DEFERRALS.md` row
  `D-P37.65a-7`; triage finding 4,
  `docs/build/reports/p37.65a-modes-triage/FINDINGS.md` (on
  `r11/ops-modes-triage`).

## What was actually broken (two defects, one root cause)

Reproduced on `a81b5935` before touching anything — `verb_build` over a
`LocalDirStore` + the `test_release_verify` export fixture:

1. **The strand (the reported defect):** `_allocate_label` appends
   `{label, publication_id: null, state: "allocated"}` to `labels.json`;
   `build_release` then ran with `labels_registry=None` (a `Store` is not
   a path, so the exports-side bind at `release.py:876-877` could never
   reach the registry) → the label stayed `null`-bound forever.
   `read_label_map` (`release_conf.py:157-172`) skips non-`p-<64hex>`
   pubs → no `labels.conf` 301 alias; V2's uniqueness leg read the entry
   as bound to `['None']`.
2. **The stalegen (attempt-2's actual crash, the `work-refused-stalegen`
   residue):** `_allocate_label`'s `labels.json` write shifts the
   registry-state digest (`labels.json` is in `REGISTRY_STATE_FILES`),
   and `verb_build`'s post-build `lock.refresh()` then read the verb's
   own write as drift → `StaleGeneration` → lock left held, label
   stranded, `built` never journaled. Reproduced verbatim:
   `StaleGeneration registry state moved under the held lock`, LOCK left
   behind, `labels.json` entry `publication_id: null`.
3. **Adjacent derivation defect (same lines):** `verb_build` read
   `manifest.get("as_of_world") or manifest.get("as_of")` — top-level
   keys no manifest emits (the real field is
   `manifest["snapshot"]["as_of_world"]`, `manifest.py:310-331`) → the
   label's date silently derived from the build instant. Same-day builds
   masked it; a next-day build would allocate a next-day label the
   descriptor check then refuses ("does not derive from
   snapshot.as_of_world").

## The fix (`ops/src/ops/release_pipeline.py`)

- **`bind_label(store, label, publication_id) -> bool`** — new public
  helper, the exact mirror of `_allocate_label`'s store contract: a dir
  store calls `record_label_publication` on `store.root / "registry"` in
  place; a bucket mirrors `labels.json` to scratch, binds, writes back
  under a metageneration-matched `replace`. Returns `False` when
  `labels.json` carries no entry for the label (a typed `--label` never
  allocated — journaled honestly, no entry invented); refuses
  `label-rebind` when the entry already binds a *different* pub
  (SIG-REL-001 — a label never moves; re-binding the same pub is a legal
  resume).
- **`verb_build`** — after `build_release` names the pub: `lock.refresh()`
  → `emit_event("built")` → `lock.refresh()` → `bind_label(...)` →
  re-baseline `lock.state_digest` → `emit_event("label-bound")`. Two
  discipline fixes ride with it:
  - after `_allocate_label`, `lock.state_digest` re-baselines (the
    `release_reversal._rebaseline` convention) — `refresh()` still
    refuses NEW drift, never the verb's own write;
  - `as_of` derives from `manifest["snapshot"]["as_of_world"]` →
    top-level `as_of_world`/`as_of` → the date-grain
    `reproducibility_inputs.as_of_snapshot` → `_iso(now)` — the same
    chain `_v2_descriptor` validates against.
  - The bind is gated on `build.descriptor["schema"] ==
    sig.publication-descriptor/2` — the same guard `release.py:876` uses
    (v1 carries no label; a v1 build binds nothing).
- **`verb_label_bind(store, apply_, label, publication_id, reason,
  break_lock, now)`** — new verb-shaped composition for the residue
  case: dry-run plans; `--apply` takes the registry lock, refreshes,
  calls `bind_label`, re-baselines, and journals `label-bound` carrying
  `outcome` (`recorded`/`skipped`), the pair, the pub's prior journal
  `publication_history` (evidence the bind lands *after* `built`), and
  the caller's `reason` (the authorisation ref). Validates
  `sig-YYYY-MM-DD.N` / `p-<64hex>` before any lock.
- **CLI** — `sig-ops release label-bind` subparser in `ops/src/ops/cli.py`
  (`_rel_common` + `--label` + `--publication` + `--reason`); `run_verb`
  dispatches it.

## Journal ordering

`built` → `label-bound` — each event lands after the work it records. A
crash between them leaves the honest stranded residue (allocated,
`publication_id: null`) that `label-bind` re-binds — never a bind the
journal never saw. `label-bound` is not a §3.4 lifecycle kind (alongside
`classified`, `sites`, `incident`, `cadence`, `verified-p`): it lands in
`history`, the fold's `state` stays `built`.

`read_label_map` needed no change: `isinstance(pub, str) and
PUB_RE.match(pub)` already resolves bound labels and skips `null` pubs —
once `publication_id` is written, `render_labels_conf` emits the
`/releases/<label>/` → `/releases/<pub>/` 301 aliases `verb_promote`
writes into `conf/<gen>/labels.conf` (`release_conf.py:763`).

## The residue-bind invocation (the resume leg's exact call)

The machinery now supports binding an already-built pub — verified
end-to-end on a `LocalDirStore` (stranded `null`-pub entry → bound +
`label-bound` journaled after `built`):

```bash
sig-ops release label-bind --apply \
  --registry "$SIG_RELEASE_REGISTRY" \
  --label sig-2026-11-25.1 \
  --publication p-31371dfb4b2b26453f818fefd311ea07be50ef8413aa9185be1ede927a773a8b \
  --reason "D-P37.65a-7 residue bind — operator-authorised under 99018e1b (GATE DECISIONS dc7e98ad: 'Bind it now')"
```

Notes for the leg:

- `labels.json` is in `REGISTRY_STATE_FILES`, so the write shifts the
  state digest — the verb lands it inside its own lock window (takes
  `registry/LOCK`, refreshes, writes, re-baselines, journals, releases),
  matching the deferral's "inside a window before the next verb reads it".
- If a stale lock is held, add `--break-lock "<reason>"` (recorded into
  the fresh lock record).
- Equivalent Python form (the `rebuild-work.py` driver pattern):
  `rp.verb_label_bind(store, apply_=True, label="sig-2026-11-25.1",
  publication_id="p-31371dfb…", reason="…")` over
  `rp.open_store(os.environ["SIG_RELEASE_REGISTRY"])`.
- `outcome: "skipped"` + `label_bound: false` means no allocation entry
  matched (typo or the entry was consumed) — nothing was written.

## Verification

- `uv run pytest tests/ops/test_release_pipeline.py
  tests/ops/test_release_conf.py -x -q` — **73 passed** (14 new).
- `uv run ruff check` + `ruff format --check` on the touched files — clean.
- `uv run mypy -p ops` — clean (104 source files).
- New pins (`tests/ops/test_release_pipeline.py`): build binds its
  allocated label (journal `built` → `label-bound`, labels.json
  `publication_id == pub`, lock released); pre-allocated `--label` binds
  (the residue-resume shape); bound label resolves through
  `read_label_map` → `render_labels_conf` 301 alias lines; typed label
  without an entry journals `skipped` honestly; label date derives from
  `snapshot.as_of_world` on a next-day build. `label-bind` verb: stranded
  residue binds + journals after `built` with `publication_history` +
  `reason`; idempotent same-pub re-bind; `label-rebind` refusal leaves
  the first bind intact; missing entry → `skipped`, nothing written;
  `bad-input` validation; dry-run writes nothing; `run_verb` dispatch.
  `tests/ops/test_release_conf.py` gains the `read_label_map`
  bound/null/malformed sweep.
- Live-shape dry-run: `sig-ops release label-bind --registry
  /tmp/sig-lb-test --label sig-2026-11-25.1 --publication p-31371dfb…
  --reason …` prints the two-step plan, writes nothing without `--apply`.

## Files touched

- `ops/src/ops/release_pipeline.py` — `bind_label` + `verb_label_bind`
  added; `verb_build` post-build bind, post-alloc re-baseline, as_of
  derivation; `run_verb` dispatch; `__all__`.
- `ops/src/ops/cli.py` — `release label-bind` subparser.
- `tests/ops/test_release_pipeline.py` — the build/bind pins.
- `tests/ops/test_release_conf.py` — `read_label_map` bound/null sweep.
- `docs/build/runs/LABEL-BIND-FIX.md` — this ledger.

Harness: devin-desktop/swe-2-high/subagent
