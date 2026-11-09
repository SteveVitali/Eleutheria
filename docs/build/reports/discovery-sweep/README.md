# Discovery sweep — the recurring registry-completeness pass (P37.13)

`sig.discovery-sweep/1` — the recurring form of Stream I's source-discovery
method (research/I3…I9b, `docs/build/planning/2026-09-30-next-phase/`). Its
contract: the documented feed universe is re-enumerated on a cadence, every
entry is mapped to the source registry, and the result is committed with its
query log — a census, never a one-time answer (SIG-INGEST-048: the ecosystem's
membership turns over fast enough that the registry needs a **recurring**
sweep).

## Method (one sweep)

1. **Enumerate the documented surfaces.** Fetch the EFF Data Library index
   (`atlas_data_library`), byte-recorded (size + sha256); parse the spec
   §22.7 roster table from its spec source (never a hand-copied count);
   walk the spec §22.6 H2 projects list; read the registry id set.
2. **Map.** Every enumerated entry gets a disposition: `registered:<id>`,
   `new-linked:<id>` (registered LINK by this sweep), `related:<id>`
   (a different artifact covering the same fact class — recorded, never
   silently counted as the roster row) or `candidate-unregistered`.
3. **Record.** `SWEEP.md` (the dated report), `query_log.csv` (every fetch /
   parse / diff, Stream-I style), `candidates.csv` (one row per enumerated
   entry with its disposition + evidence).
4. **Gate nothing.** Registration is `ingestion_permitted=false` +
   rights UNDETERMINED — a sweep never flips a source (HG-03 is the
   operator's line) and never contacts anyone (U-011).

## Cadence

The sweep recurs once per round, or sooner when a roster-bearing artifact
changes (the Data Library index, spec §22, a registration batch). The next
sweep re-runs this method into a new dated directory and diffs against the
last committed `candidates.csv`: entries that moved `candidate-unregistered`
→ `registered:*` are the sweep's coverage gain; new index entries are the
discovery yield.

## Runs

| date | directory | enumerated | registered at sweep | candidates opened |
|---|---|---|---|---|
| 2026-11-07 | `2026-11-07/` | 42 index entries + 16 spec-roster rows + 7 §22.6 H2 rows | 19 (11 pre-registered + 8 new LINK) | 23 (→ `D-P37.13-1`) |
