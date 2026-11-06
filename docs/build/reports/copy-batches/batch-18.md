# Copy batch 18 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P37.7 (row 427, R11-GOV-02 — the public editorial decision log
     page, /about/editorial-decisions/). Append-only, same convention as
     batch-01: rows are never deleted or edited in place; a status change is
     recorded in the confirmation log with a `date -u` stamp. Id prefix: DL-*
     = the editorial decision log page. -->

## Convention

Same as batch-01 (`docs/build/reports/copy-batches/batch-01.md` § Convention):
`pending` = agent-drafted, awaiting verbatim confirmation · `confirmed` = the
operator confirmed these words verbatim. P37.7-specific notes:

- **`{logStart}`** is a rendered placeholder (the `{reviewStatus}`/`{permalink}`
  precedent — the row pins the sentence shape): it resolves to the log's
  earliest `logged_at` at build (`logStartDate` in
  `web/src/lib/editorial-decisions.ts`).
- **DL-07** renders only when a `deletion`/`purge` entry exists (none today —
  the empty state DL-06 is what ships).
- The decision entries themselves are record content (`sig.editorial-decision/1`
  in `web/src/lib/editorial-decisions.ts`), not drafted prose: the `decision`
  fields carry the recorded GATE DECISIONS dispositions with the operator's
  words quoted verbatim — they are bound by test, not this register.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| DL-01 | /about/editorial-decisions/ | Every naming, sensitivity and contested-claim decision SIG makes is recorded here — dated, with its scope, its rationale and its record links. | 87a3af5ef55a4d19d92506844c12248a6ada897d38373bab2ecf3f63f7d4fbe6 | pending |
| DL-02 | /about/editorial-decisions/ | A deletion or a purge appears as a tombstone: its category and its date, never the deleted content. | cbbf97fc7cb2eeaf7286c44864d8914ffceb5ae256d6fe6ef58f5a76f23876fe | pending |
| DL-03 | /about/editorial-decisions/ | SIG has no independent review board for its editorial calls. Those decisions are made by one maintainer under the recorded interim authority logged below — disclosed, never presented as a board — and officer and person naming is turned off. | 4728098ec9eea57ac9a57952d35d47365ca3dc3d66cad4d0a22823a1bbf83ca1 | pending |
| DL-04 | /about/editorial-decisions/ | This log begins {logStart}; entries marked retroactive record decisions taken before it existed, dated as their records are. | afe157adaf073b709fa395dc326f92b98a6f58509af8a9a98094aa923622740d | pending |
| DL-05 | /about/editorial-decisions/ | The log is append-only: a correction is a new entry, never an edit. | 289a122f7139c0c7ff6d2d5fb5941bfb07d2d9b576fbafc2bf3a043e36de913e | pending |
| DL-06 | /about/editorial-decisions/ | No deletions or purges are recorded. | 8c945516520ee745eed246df55e8771d1726cc044732284a30f432306c30882e | pending |
| DL-07 | /about/editorial-decisions/ | Tombstone entries appear in the log above — a category and a date, never content. | 690ea9b23a9ac3055433366cf969274009da88b5b55597cd0bac29f644b1ff81 | pending |
