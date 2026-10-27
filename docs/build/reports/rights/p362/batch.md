# P36.2 rights-flip/decline batch — staged packets, captures and operator lines

> Row 350 (`docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md`),
> staged 2026-10-27 (`date -u`; devin-desktop/swe-2-high/subagent).
> **Not legal advice.** Every decision belongs to the operator under HG-03; the
> agent stages, captures and verifies — it never executes a flip or a decline
> (OP-26; ADR-169 §14). Agent-drafted text is labelled; the operator's words are
> quoted verbatim with their GATE-P times.

## 1. The E4 §1 lines — recorded verbatim with GATE-P times

All eight lines answered at B-41 (ADR-169 §12), GATE-P **2026-10-01T04:49:27Z**;
B-41's selected option label was *"As listed, R3 flip"* (against the presented
recommendation). R4a/R4b handled as presented per the round-26 record
clarification (S6R-02).

| line | owed row | source | operator's recorded answer | staged state |
|---|---|---|---|---|
| R3 | D-SOURCES.7-1 | `dot_511_tx` | **a — flip under GL-GATE-07 (US)** | flip patch staged on `r11/sources-flips` (unsigned); packet `../dot_511_tx.md` |
| R4a | D-SOURCES.8-1 | `camreg_edmonton_ab` | **b, then decide on the OGL-Edmonton basis (I7-C11 a)** — capture the City of Edmonton terms, flip if they permit | terms capture QUEUED (`terms-manifest.toml` `p362-camreg-edmonton-terms`); decision line staged §3 |
| R4b | D-SOURCES.8-1 | `camreg_hk_hk` | **a — flip on the non-US basis** (`LicenseRef-OperatorAccepted-DBRight`) | flip patch staged on `r11/sources-flips` (unsigned); packet `../camreg_hk_hk.md` |
| R4c | D-SOURCES.8-1 | `camreg_qldc_au` | **b — use the QLDTraffic API instead** (key registered by the operator, B-18) | route note staged; the API connector lands at **P37.70** (row 434); packet `../camreg_qldc_au.md` |
| R4d | D-SOURCES.8-1 | `camreg_bellevue_wa` | **c — decline** (A-9 — SIG's use is or may be commercial) | DECLINE note staged on `r11/sources-flips`; source stays REFUSED; packet `../camreg_bellevue_wa.md` |
| R5 | D-SOURCES.9-1 | `procportal_chicago_il` | **a — flip under GL-GATE-07 (US)** | flip patch staged on `r11/sources-flips` (unsigned); packet `../procportal_chicago_il.md` |
| R6a | D-SOURCES.9-4 | `bidnet_direct` | **a — capture bidnetdirect.com terms, then decide** | terms capture QUEUED (`terms-manifest.toml` `p362-bidnet-terms` — transferred from P34.38's queued leg); decision line staged §3 |
| R6b | D-SOURCES.9-4 | `periscope_s2g` | **a — close as superseded by `bidnet_direct`** | CLOSED-as-superseded note staged on `r11/sources-flips`; packet `../periscope_s2g.md` |

**Staged flip patch (never applied by the agent).** Branch `r11/sources-flips`
carries a second prepared commit on top of P34.38's unapplied patch: the three
flips (`dot_511_tx`, `camreg_hk_hk`, `procportal_chicago_il` — each
`ingestion_permitted = true` + `compact_status = "public_terms_only"` +
`rights_reviewed_by/on` + `[rights]` block + `FLIPPED … under GL-GATE-07`
note), plus the two bookkeeping notes (R4d `DECLINED`, R6b `CLOSED —
superseded`, R4c route note). The operator applies it in one signed commit or a
GATE DECISIONS row (OP-26 / ADR-169 §14; the P34.28 G4c check fails any
unsigned `ingestion_permitted` false→true on the chain). This branch's own
`sources.toml` is untouched — verified by `tests/connectors/test_p362_rights_batch.py`
and `gate`/`validate` output in §5.

## 2. IU1–IU5 — B-36 = a: terms captures, then one E4-style line each

The operator's recorded answer (B-36 + B-37, 2026-10-01T04:46:04Z):
*"Capture IU; TR facts+cite (Recommended)"* — IU1–IU5 terms are captured here,
then each gets a new HG-03 line (GATE-G6 packet at the latest, S6R-28).

Every capture leg is **QUEUED** (`prepared_not_executed`): the precondition
`live:P35.38a` fails — `https://surveillancegraph.org/data-collection/` →
HTTP 404 at 2026-10-27T01:53Z probe (`date -u`; root → 200). A descriptive UA
(SIG-INGEST-036) may not cite a dead owned page; no fetch was attempted.
Re-run: `implement-spec spec=docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md live_verification=true`.
Manifest: `terms-manifest.toml`; queue record: `queued-captures.json`.

Staged decision lines (**agent-drafted, for the operator — not answers**;
each binds once its capture lands verbatim in the packet):

- **IU1 — Leonardo/ELSAG procurement contracts**
  (`leonardocompany-us.com/lpr/how-to-buy/procurement-contracts`): terms not
  captured (only a Data Privacy Policy link found on the page).
  *Staged line:* `IU1: a — flip on the captured terms' basis · b — facts +
  pointers only · c — decline` — GATE-G6.
- **IU2 — Carahsoft / Cellebrite contract vehicle**
  (`carahsoft.com/cellebrite/contracts`): terms not captured.
  *Staged line:* `IU2: a — flip on the captured terms' basis · b — facts +
  pointers only · c — decline` — GATE-G6.
- **IU3 — Google geofence warrants**: Google ToS text is known but never
  captured verbatim into evidence; the public-page fetch leg sits under
  ADR-184's envelope if terms are found to restrict.
  *Staged line:* `IU3: a — record the captured ToS basis and decide · b —
  facts + citations only · c — decline` — GATE-G6.
- **IU4 — SoundThinking press releases**: press-release landing page found;
  `/terms-of-use` path returned 404 at check time — capture attempt records
  the honest outcome.
  *Staged line:* `IU4: a — flip on the captured terms' basis · b — facts +
  citations only · c — decline` — GATE-G6.
- **IU5 — FlockRadar** (`github.com/rxsklife/flockradar`): code carries
  AGPL-3.0; the *data* licence is unstated — capture README + LICENSE and
  decide on what is evidenced.
  *Staged line:* `IU5: a — flip on the captured licence terms (code AGPL-3.0
  ≠ data grant) · b — facts + citations only · c — decline` — GATE-G6.

## 3. The folded re-decision set (D-R11-RIGHTS-1; T3 fold)

Five already-public rows the Stage-P review flagged as out-of-rule /
counsel-flagged. Each stays published under ADR-169's
withdrawal-on-objection guardrail meanwhile; each terms capture is QUEUED on
`live:P35.38a` like §2. **Agent-drafted staged lines — the operator answers,
the agent does not:**

- **`camreg_und_001`** (ArcGIS community item `509475945f494a37bcbeefee139a6ecc`,
  jurisdiction unresolved → DBRight, 2026-09-18):
  `keep under LicenseRef-OperatorAccepted-DBRight (ADR-169 basis) · decline`
  — capture: item `licenseInfo` verbatim.
- **`camreg_calgary_ab`** (City of Calgary Socrata, ToU link text never
  captured → DBRight, 2026-09-18):
  `keep under LicenseRef-OperatorAccepted-DBRight · decline` — capture: the
  dataset Terms-of-Use link body verbatim.
- **`camreg_lexington_ky`** (LFUCG ToU embedded in item
  `d220ce31999448659626afe990ca1328` licenseInfo — permits use and
  derivatives BUT carries an indemnify-AND-defend clause §VI.B →
  PublicRecord-FactualCompilation, flagged counsel-needed, flipped anyway):
  `keep under LicenseRef-PublicRecord-FactualCompilation · decline` —
  capture: item `licenseInfo` verbatim (the clause is already in the record).
- **`dot_511_md`** (MD iMAP attribution-CONDITIONED terms — "data can be
  freely distributed as long as the metadata entry is not modified or
  deleted; derived data must acknowledge the State of Maryland" →
  PublicRecord-FactualCompilation):
  `keep under LicenseRef-PublicRecord-FactualCompilation · decline` —
  capture: the iMAP terms text verbatim.
- **`camreg_md_opendata`** (opendata.maryland.gov `hua3-qc8n`, 451 rows — the
  statewide mirror of the same CHART registry, NO licence metadata; same
  iMAP-conditioned blocker):
  `keep under LicenseRef-PublicRecord-FactualCompilation · decline` —
  capture: portal terms + iMAP terms verbatim.

## 4. Terms-capture manifest (all QUEUED — `live:P35.38a` fails)

`terms-manifest.toml` carries 12 legs: 7 authorized captures (IU1–IU5, R4a
Edmonton, R6a BidNet) + the 5 folded-set terms captures. Each records its
target URL(s), the verbatim-bytes destination, `status = queued`,
`executed = false`, the probe evidence and the re-run prompt. Capture runner:
`capture_terms.py` — a bounded read-only GET under the project UA
(SIG-INGEST-036/037) honoring `Crawl-delay`; it refuses (exit 42) while the
owned explanation page is not live. Captured bytes land verbatim under
`captures/` with `sha256` + `generated_at` (SIG-TRANSP-004 terms-capture
field family); nothing is paraphrased.

## 5. Verification (this run — staging branch, `live_verification=false`)

Commands run against the chain tree (sources.toml untouched):

```
uv run sig-connectors validate            # registry self-checks — see run ledger
uv run sig-connectors gate --source <id>  # every staged row → REFUSED (exit 1)
uv run sig-connectors export-check        # compartments stay single-licence
uv run sig-connectors run --source <id> --mode live   # NOT RUN — no source was
                                          # operator-flipped; running it would
                                          # only re-record exit 3
```

Recorded in the run ledger (`docs/build/runs/P36.2.md`) with exact output.
After the operator's act (not this row): each flipped source must show
`gate` → LOADABLE, `validate` green, `export-check` pass and
`run --mode live` exit 0; each decline stays REFUSED.

## 6. DEFERRALS bookkeeping

- D-SOURCES.7-1 / 8-1 / 9-1 / 9-4 — annotated (P36.2 staged; stays OPEN —
  each closes only with its operator line + verification evidence);
  obligation-event progress notes appended (`events.jsonl`).
- D-R11-RIGHTS-1 — annotated (five staged lines recorded §3; captures
  queued); event appended.
- **D-P36.2-1** (new): the 12 queued terms-capture legs — owner: the OM-19
  leg-runner / the operator; trigger: the `live_verification=true` re-run
  inside a valid window once `live:P35.38a` holds.
