# Correction note — source identifiers re-keyed for personal-data protection (2026-10-03)

*P34.18 / ADR-178 · S0 finding RI-01 (F-097/F-131) · operator decisions DR-C6-01
(B-3), OD-17 (A-0.1), OD-20 (A-0.4) — Part VIII personal-data protection.*

## What changed

A cohort of public source identifiers was minted from personal account handles
(and one from a surname): the `camreg_<handle>` source ids, the camera target
ids derived from them, and every identifier composed from those — camera
subject ids, claim ids, evidence/permalink ids and tile properties. Those
identifiers have been re-keyed to neutral ids (`camreg_us_ny_<n>` /
`camreg_und_<n>` / `okc_council_statement`), which are not derived from any
personal token.

The change was made under **Part VIII** of the design spec: identifiers that
embed a person's handle are personal data unrelated to institutional conduct,
and SIG's public surface must not carry them (SIG-PUB-002).

## What did not change

- **No claim was rewritten.** The claim spine is append-only (P1–P3,
  SIG-STORE-011): every claim keeps the identifier it was recorded under.
  Resolution of an old identifier to its neutral form is a read/export-time
  projection, not an edit of the record.
- **No history was rewritten.** The repository's git history retains the old
  strings — that is the operator's accepted posture (OD-20, *"Accept and
  disclose"*). Anyone inspecting past commits will find them; this note is the
  honest disclosure of that fact, and it is the condition under which the
  archive deposits (P37.55) proceed after their history scan.

## Old citations

A URL or citation that carries a retired identifier now resolves to a neutral
notice — *"This identifier has changed."* — rather than to a new page. There is
deliberately **no public redirect and no public old→new list**: a redirect or a
published mapping would repeat the handle (DR-C6-01). The old→new mapping
exists once, in a restricted location, for the operator's audit and rollback
needs only.

## Registry text

The same review removed e-mail-shaped owner strings and handle tokens from the
source registry's non-identifier text (notes, names, agency fields), replacing
them with neutral markers such as `[account withheld]`. One `camera_operator`
value that was itself an account handle is suppressed from public surfaces; the
recorded claim is retained.

## Records

The append-only record of this change: ADR-178 (the decision), the committed
re-key tool (`sig-connectors rekey-personal-ids`, dry-run by default), the
keyed-digest alias table (`policy/src/policy/data/source_aliases.json` —
sha256 digests, no plaintext handles), and the counts-only crawl check
(`docs/build/tools/handle_crawl_check.py`). The re-keyed public pages and the
neutral-notice routes ship with republish #2 (P34.21b).

## Correction — 2026-11-16 (P37.61b, RULING E-1)

Commit `15085e0a` (P34.39a read-back records) pasted four of the listed
personal handles back into six retained-history files — `DEFERRALS.md`,
`runs/P34.39a.md`, `pr/P34.39a-live-1.md`, the
`p34.39a-osm-replay-read-back` README, the generated
`reports/current/current.json`, and `reports/obligations/events.jsonl` — and
the informational crawl check's retained-prefix classification let the
reintroduction pass green.

Under **RULING E-1** (GATE DECISIONS 2026-11-15;
`docs/build/readouts/RULINGS-2026-11-15.md`) the tracked tip is scrubbed at
HEAD by a normal commit — no history rewrite (OD-20's accept-and-disclose
posture stands: the old strings remain in git history):

- The four handle strings are replaced with non-identifying references
  ("the four pre-rekey handles", etc.) — the affected positions name the
  *deployed* ids, which are still the pre-rekey handles pending deferred L2
  `D-P34.18-1`, so writing the neutral ids there would falsify the record.
- All `owner` / `item_owner` fields are removed from the five declared
  ArcGIS catalog-sweep / disposition JSON artifacts
  (`catalog_sweep_2026-09-18*.json`, `catalog_sweep_2026-09-26_retry.json`,
  `p2616_dispositions.json`).
- The pre-edit bytes of every inherited line are archived under
  `docs/build/reports/memory-repair/` (`*_pre-P37.61b-handle-scrub.txt`)
  with listed handles redacted to sha256 digests plus per-line original
  digests for audit — plaintext handles never commit; the true bytes
  remain in git history per OD-20 — and the correction commit is declared
  `seed-commit` in `record_policy/history.policy` per the sanctioned
  memory-repair path.
- The **reappearance guard** (`docs/build/tools/redaction_guard.py`,
  `sig.redaction-guard/1`, wired into `.github/workflows/ci.yml`) is now
  fail-closed on any sha256-listed handle in *any* tracked file — retained
  prefixes included — plus any `item_owner` key anywhere and any
  `owner`/`item_owner` field inside the declared sweep set. Comparison is
  digest-only (`record_policy/redaction_guard.json`); the plaintext list
  stays gitignored and is never printed. `handle_crawl_check.py` keeps its
  informational retained/functional classification for audit.
