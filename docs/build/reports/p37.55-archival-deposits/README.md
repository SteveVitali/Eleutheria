# P37.55 — Archival deposits: the committed evidence set

Round 11 / P37 / sub-round 11D · manifest row 482 · `R11-TRANS-01` ·
`implement-spec spec=docs/tickets/482_P37.55__archival-deposits.md live_verification=false`
(OM-20: the external archival request is never pre-authorised — the SWH
save-now and the Zenodo production publish remain the operator's explicit
verbatim go; everything here is `prepared_not_executed`).

## What lives here

| File | What it is |
|---|---|
| `history_scan.json` | The `sig.history-scan/1` report — every blob advertised under the public ref surface (`refs/remotes/{origin,pull}`, `refs/tags`) scanned for the `secret_scan.py` rule set, credential-shaped paths, e-mail-shaped literals, and the P34.18 restricted handle list. Findings name rule + path + **sha256 of the matched literal** — never the matched bytes. |
| `history_scan_dispositions.toml` | `sig.history-scan-dispositions/1` — the reviewed per-class disposition of what the scan found: `exempt` (reviewed false positives — e.g. AWS's own documented example key seeded in tests) and `disclosed` (accepted-and-disclosed retained history — the A-0.4 / P34.18 pattern). An entry matching no finding is stale and fails the report. |
| `deposit_package.json` | The `sig.deposit-package/1` accounting report written by `sig-exports deposit-package` when the package was assembled. |

## The scan, honestly (Q-E2-23 [B-6] = a — scan first, then submit)

The scan was **not** clean-by-absence — retained history carries material,
exactly as E2-21 predicted and P34.18 disclosed (A-0.4 = a). The report
records the whole public ref surface. Classes of finding and their recorded
dispositions:

- **Disclosed retained handles** — the restricted handle list matches are
  the class P34.18's correction note
  (`docs/governance/identifier-rekey-note.md`, OD-20) already disclosed:
  old personal-handle-derived identifiers remain in history because history
  was never rewritten. Recorded as the disclosed class — counted, never
  blocking, never re-printed.
- **Exempted false positives** — reviewed non-credentials: AWS's published
  documentation example key in test fixtures; Secret Manager *name* values
  (`sig-*` — a name is never a credential) and shell `$(…)`/`${…}`
  templates; service-account *listings* without a `private_key` field; the
  build-log `.gitignore` mechanism file.
- **Disclosed retained history** — a Google Maps *browser* key in a scraped
  fixture (public-in-page by Google's design; the tip already carries the
  `REDACTED-` placeholder); the operator's own address in the operator's own
  OP-25 signing records; public agency/org/community contact addresses
  captured verbatim in source data and the catalog sweep; GCP
  service-account *identifiers* (names, not keys).
- **Unclassified e-mail tokens** — every e-mail-shaped literal is classified
  by a deterministic shape rule or covered by a disposition entry; an
  unclassified-and-undispositioned token blocks. The reviewer-only token
  list is written to `docs/build/logs/history-scan-emails.txt` (gitignored —
  never committed).

The report's `disposition` must read `clean` (zero undisposed findings, no
stale entries) before the SWH submission — `sig-ops swh-save --now
--scan-report <this report>` refuses otherwise (exit 4, writes nothing).

## The Zenodo package (D-J3-9 [B-21] = yes — open compartments only, after the attribution fix)

`sig-exports deposit-package --in <export> --out <pkg>` assembles the
package **allow-list, fail-closed**: only compartments declared under a real
open licence in `policy/src/policy/data/licenses.toml` (+ `metadata`, the
export's own descriptor docs) ship. Excluded by construction: the two
GL-GATE-07 risk-accepted lanes `operator_accepted` / `public_record` (by
compartment name *and* licence token, so a combined-licence surface cannot
slip through), `derived_facts` (a counsel-approved publication basis, not an
open licence), `web` (derived view indexes, not a deposit surface), and all
`evidence*` bytes (§38.2 — their digests ride `digests.json`). Every
included byte must hash to the manifest's recorded digest or the build
refuses.

The publish is **OP-19** — the operator's manual act
(`sig-exports deposit --in <pkg> --production` with `SIG_ZENODO_TOKEN`,
or a web upload). Nothing here deposits anything; `10.5072/…` sandbox
DOIs never stand in for the production concept DOI (RISK-P21-08).

## Operator handoff (RETURN PASS `P37.55` `kind = "leg"`)

1. Re-run the scan against the submitted head → a clean
   `sig.history-scan/1` report; confirm the dispositions file's judgments
   (each `decided_by` reads "agent-analysis P37.55 — confirm in the verbatim
   go").
2. `sig-ops swh-save --now --scan-report <report>` — the verbatim go.
3. Rebuild the public export after P34.21b's republish, run
   `sig-exports deposit-package`, then the OP-19 publish; record both DOIs
   in `docs/build/reports/DEPOSITS.md`.
