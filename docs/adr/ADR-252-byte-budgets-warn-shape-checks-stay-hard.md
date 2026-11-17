# ADR-252 — Ledger byte budgets become warnings; shape checks stay hard (RULING E-4)

- Date: 2026-11-17
- Status: accepted (engineering; check severity — no control-state writes)
- Ticket: P37.61e (Round 11 / P37, sub-round 11D, manifest row 489e — on
  `r11/P37.61e-byte-budgets-to-warnings`)
- Base: `r11/P37.61d-live-claims-rescope` (`c8df314a`)
- Authority: operator **RULING E-4**, recorded verbatim in
  `docs/build/LEDGER.md` GATE DECISIONS (2026-11-15, channel interactive)
  and `docs/build/readouts/RULINGS-2026-11-15.md`
- Amends: B3 §6 (the ledger-contract bounds in
  `docs/build/planning/2026-09-30-next-phase/design/B3-ledger-redesign.md`
  and their validator embodiment — V1, V2's byte caps, V4's entry cap, V11's
  recipe bound); **SIG-MEM-010 qualified** — its byte-budget clauses now
  name *advisory* declared targets, while its shape clauses and the new
  combined ceiling stay MUSTs
- Relates: SIG-MEM-010, BM-LEDGER-06/08, BM-ORIENT-01, ADR-073 (the
  build-memory root), ADR-120/126/127 (the Round-10 memory extension)

## Context

B3 §6 gave the control ledger two families of bounds: **byte budgets** (the
orient region ≤ 12 KiB, CURRENT STATE ≤ 3 KiB, the `returnPass` line ≤
1024 B after L8, PHASE LOG entries ≤ 2 KiB, the orient recipe ≤ 48 KiB) and
**shape rules** (key order and vocabulary, no `| PRIOR`, the returnPass
id-list grammar, ≤ 256 B per CURRENT STATE line, one PHASE-LOG append
target, no key-named line outside CURRENT STATE). Both families enforced
the same way — `guarded`/`rep.v`, a hard failure.

The budgets kept paying a repair tax the shapes never did.
`docs/build/tools/record_policy/history.policy` records repair arc after
repair arc in which a PHASE LOG entry ran 2,224 B or 2,917 B, the orient
recipe read 49,183–53,622 B, or a `nextTicket` advance pushed the head a
few hundred bytes over a cap — each one forcing a "slide line", compaction
or trim commit whose only purpose was to satisfy the byte bound again. The
invariants that actually protect interpretation — the reader takes the
first key match, the keys come in a fixed order, `| PRIOR` would smuggle
history into a values-only block, returnPass must be an id list — are
structural, not dimensional. A 2,224 B PHASE LOG entry is ugly; it is never
unreadable the way a `| PRIOR` chain or a key-shadow line is wrong.

RULING E-4 (2026-11-15) settles it: byte budgets become warnings, the
named shape checks stay hard, and one generous hard ceiling — the CURRENT
STATE block plus the ledger head ≤ 18 KiB — keeps the normal agent
orientation read bounded.

## Decision

1. **Every byte budget is advisory.** In `ledger_contract.py` the rules
   `orient-budget` (> 12,288 B — the > 8,192 B level was already a warning),
   `cs-budget` (> 3,072 B), `returnPass-line-budget` (> 1,024 B, new split
   rule — decision 4), `entry-budget` (> 2,048 B, now warned in the current
   PHASE LOG region too, not only legacy ones) and `probe-budget`
   (> 49,152 B) emit `warning`, never `error`. In the vendored
   `scripts/docs/check-build-memory.sh`, each `guarded ledger-budget` byte
   cap is `warn ledger-budget` under new tagged SIG-LOCAL hunks (L9, L14 —
   and L8's byte half); **L5 retires**: the orient-probe line returns to
   upstream's own `warn` byte-for-byte, so the hunk is gone, not weakened.
   Under the guards marker nothing in this class can fail the docs leg.

2. **Every shape check stays hard.** CURRENT STATE key order and declared
   vocabulary, keys outside the block, `| PRIOR` history, the returnPass
   comma-id-list grammar, the ≤ 256 B per-line CURRENT STATE rule, the
   PHASE-LOG append target and the `## OPEN FINDINGS` boundary all remain
   failures. The ruling names the ≤ 256 B line rule hard: it is a shape
   check (a line is a *slot*, not a size budget), so it does not demote
   with the budgets it happens to be measured in bytes next to.

3. **One hard ceiling.** New additive check `head-ceiling`
   (`ledger_contract.py`) / `ledger-ceiling` (the vendored script, SIG-LOCAL
   L15): the CURRENT STATE block plus the ledger head (orient region) read
   ≤ **18,432 B** (18 KiB) combined — replacing the separate 12 KiB +
   3 KiB hard fails with one bound sized to a single ~20 KB agent read.
   `guarded` in the script, `rep.v` in the validator: it fails.

4. **Bundled ids were split before demoting.** Upstream's
   `guarded ledger-budget` judged byte caps and shape rules under one id —
   demoting the id would have demoted the shapes. The script now carries
   two ids: `ledger-budget` holds only byte budgets (warn), and new
   `ledger-shape` holds the still-guarded shape rules — the ≤ 256 B
   CS-line rule and `| PRIOR` (L10, split out of the shared `$cap` line,
   the L8 site), the returnPass grammar (L11), the key-shadow rule (L12)
   and the append target (L13). `ledger_contract.py` mirrors the split on
   the one bundled rule: `line-budget` keeps the ≤ 256 B hard bound for
   every key, while new rule `returnPass-line-budget` warns above the
   L8-raised 1,024 B. The vendored body's diff vs the pinned upstream
   (release 0.5.0, sha256 `f48a365d…`) still shows only tagged `SIG-LOCAL`
   hunks — the banner now enumerates fifteen (L5 recorded as retired) —
   and no consumer of either verdict format parses these check ids (the
   JSON keeps `{check, severity, …}` unchanged), so no downstream reader
   needed updating.

5. **The notes-file budget is named unmatched.** The ruling's "notes-file
   budget that has needed 'slide line' and compaction commits" has no
   identifiable dedicated check id: Phase-4 enumeration found the
   2 KiB PHASE-LOG entry budget to be the bound those repairs actually
   served (the history records them as entry/probe overages). The nearest
   generic flags — the `size` check's > 1 MB-fixture / > 5 MB-file
   warnings — already warn and stay as they are; nothing is silently
   dropped, and no new notes-file check is invented.

6. **A fold still archives every clause.** Budget pressure is no longer a
   failure, but "never fold or rotate text unless the fold archives every
   clause it drops" stands unchanged: the only sanctioned escape remains
   the verbatim-archive convention under `docs/build/reports/memory-repair/`
   (hash-linked, same-commit). Advisory budgets shrink how often the escape
   is needed; they do not widen it.

7. **`memory_guard.py` is verified consistent — unchanged.** It carries no
   byte budgets (its machinery is sha256/prefix byte-identity on
   append-only history); nothing there contradicts the new severities.

8. **Per-check severity table.** Every check id that judges the bounds,
   with its verdict under this ADR:

   | surface | check / rule | bound judged | verdict |
   |---|---|---|---|
   | `ledger_contract.py` | `orient-budget`/`orient-budget` | orient region > 12,288 B (> 8,192 B) | warning (was error; warn level unchanged) |
   | `ledger_contract.py` | `orient-budget`/`orient-shape` | missing `## OPEN FINDINGS` | **error** (shape) |
   | `ledger_contract.py` | `current-state`/`cs-budget` | CURRENT STATE section > 3,072 B | warning (was error) |
   | `ledger_contract.py` | `current-state`/`line-budget` | key line > 256 B (non-`returnPass`) | **error** (shape, named hard) |
   | `ledger_contract.py` | `current-state`/`returnPass-line-budget` (new split) | `returnPass` line > 1,024 B | warning (was error inside `line-budget`) |
   | `ledger_contract.py` | `current-state`/`key-order`, `key-vocabulary`, `prior-history`, `returnPass-grammar`, `key-shadow`, `updatedAt-future`, `next-unknown`, `next-not-lowest`, `lastCompleted-uncovered` | key order/vocab, `| PRIOR`, id-list grammar, key-shadow, the V2 value rules | **error** (shape/state — unchanged) |
   | `ledger_contract.py` | `phase-log`/`entry-budget` | entry > 2,048 B, any region | warning (was error in current region) |
   | `ledger_contract.py` | `phase-log`/`markup-id`, `future-date`, `kind-vocabulary`, `append-target`, `append-order` | entry shape, dates, vocabulary, append target | **error** in the current region (warnings in older regions — unchanged) |
   | `ledger_contract.py` | `orient-probe`/`probe-budget` | orient recipe > 49,152 B | warning (was error) |
   | `ledger_contract.py` | `orient-probe`/`next-unresolved` | `nextTicket` resolves | **error** (unchanged) |
   | `ledger_contract.py` | `head-ceiling`/`head-ceiling` (new) | CS block + ledger head > 18,432 B | **error** (new hard ceiling) |
   | `ledger_contract.py` | `named-paths`, `stale-tokens`, `ticket-counts`, `phase-log-done`, `build-index`, `return-pass`, `gate-decisions`, `run-harness`, `manifest-rounds` | unchanged | unchanged |
   | `check-build-memory.sh` | `ledger-budget` — orient > 12 KiB / > 8 KiB | orient byte budget | warn (was `guarded` / already warn) |
   | `check-build-memory.sh` | `ledger-budget` — CURRENT STATE section > 3 KiB | byte budget | warn (was `guarded`) |
   | `check-build-memory.sh` | `ledger-budget` — `returnPass` line > 1,024 B | byte budget | warn (was `guarded` inside shared `$cap`) |
   | `check-build-memory.sh` | `ledger-budget` — PHASE LOG entries > 2 KiB, any region | byte budget | warn (was `guarded` current / warn older) |
   | `check-build-memory.sh` | `ledger-budget` — orient recipe > 48 KiB | byte budget | warn (was `guarded` via L5 — L5 retired, upstream `warn` restored) |
   | `check-build-memory.sh` | `ledger-shape` (new id) — CS line > 256 B, `| PRIOR`, returnPass grammar, key-shadow, append target | shape rules | **guarded** — fail under the marker (split out of `ledger-budget`) |
   | `check-build-memory.sh` | `ledger-ceiling` (new id) | CS block + ledger head > 18 KiB | **guarded** — fail under the marker (new hard ceiling) |
   | `check-build-memory.sh` | `size` — fixture > 1 MB / file > 5 MB under `docs/build` | nearest generic flag to the unmatched "notes-file budget" | warn (unchanged) |
   | `memory_guard.py` | — | no byte budgets to demote | verified consistent; unchanged |

## Consequences

- A byte overage — a fat PHASE LOG entry, a long `returnPass` queue, an
  orient region past 12 KiB — stops forcing repair/compaction commits;
  it is a visible warning in the same JSON report, never a silent pass.
- The ledger stays protected where protection means something: key order,
  vocabulary, `| PRIOR`, grammar, the append target and the 18 KiB combined
  ceiling still fail under the guards marker and in `make docs-check`.
- G10 applies to the PR that lands this: the unchanged base checks pass on
  the final tree apart from the documented retired violations listed in the
  PR body (none of the records this PR touches breaches a shape rule).
- The vendored provenance claim survives audit: fifteen `SIG-LOCAL` hunks
  are declared, the diff vs pinned upstream shows only tagged hunks, and
  L5's retirement is the cleanest possible form — upstream text restored.
- `docs/build/reports/memory-repair/` archives stay the single escape for
  dropped bytes; the ADR changes severity, never archive discipline.

## Alternatives considered

- **Raise the budgets instead of demoting them.** Rejected — it keeps the
  repair tax at a new line and does nothing about the real defect: the
  checks conflated "big" with "wrong". The ruling's split (bytes advise,
  shape fails) is the honest model of what each bound was for.
- **Drop the byte budgets entirely.** Rejected — the warnings still carry
  the information (a 53 KiB recipe *was* a readability problem the last-3
  window deserved to know about), and the combined 18 KiB ceiling alone
  cannot distinguish a bloated head from a bloated entry.
- **Keep `guarded ledger-budget` and mark its findings advisory in the
  report.** Rejected — severity inside a shared id is exactly the bundling
  hazard the ruling calls out; the split ids make "what failed" legible in
  the JSON without reading message text.
- **A hard ceiling on the orient recipe rather than head+CS.** Rejected —
  the ruling names the bound it wants (CURRENT STATE + head ≤ 18 KiB, the
  ~20 KB orientation read); the recipe includes history windows (last-3
  entries, the next row's contract head) whose size the ledger does not
  control.

## Revisit trigger

- **A byte-budget warning becomes chronic:** if a budget warning is the
  standing state for two or more consecutive dispatches, revisit the bound
  or the recipe — an always-on warning is the old failure in disguise, and
  either the budget is wrong or the record is bloated.
- **A shape rule wants demoting too:** severity changes are new ADRs
  (SIG-ENG-003) under an operator ruling — never an edit of this one.
- **The 18 KiB combined ceiling binds in practice:** if legitimate growth
  (e.g. a `returnPass` queue the table genuinely needs) pushes head+CS over
  it, the ceiling size is the knob — raise it by ADR, never by folding
  unarchived text.
- **The vendored checker is re-vendored:** upstream bumps must reapply the
  SIG-LOCAL hunks L8–L16 (or retire them if upstream adopts the same
  severity split); the banner's hunk list is the audit surface.
