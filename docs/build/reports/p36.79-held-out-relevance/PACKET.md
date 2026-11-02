# P36.79 — held-out search relevance set: the seal packet (prepared, not executed)

Ticket `371_P36.79__held-out-search-relevance-set.md` / **R11-K13-SRCH-00** —
the ≥ 40-query held-out search relevance set, written by a **separate agent
context** (D-K3-7 [B-28] = b, answered 2026-10-01T04:41:11Z) and labelled
**`agent-authored held-out set; not independent`** wherever the set or its
metric appears (SIG-CONF-012 — an estimand label, never real-world
precision). Judged against the first model release (P35.63) at SRCH-07
(P36.71).

**Status: `prepared_not_executed`** — the restricted-bucket object write is
QUEUED; nothing was written to any bucket, nothing was promoted, and no
seal is claimed. The re-run prompt below re-dispatches the write leg when
the preconditions hold.

Machine-readable twin: `packet.json` (`sig.held-out-relevance-seal/1`);
the digest contract every other context reads: `descriptor.json`
(`sig.held-out-relevance-descriptor/1`).

## The set (digest only — the bytes never land in the repo)

- **set:** `sig.held-out-relevance-set/1` · `sig.held-out.search-relevance/2026-10`
- **counts:** 55 queries — 48 `top3` (answerable) + 7 `honest` (the release
  cannot answer; 0 misleading top hits expected) across 17 kinds
- **sha256:** `44c746836f709e9dde74e2a4834a1c8d0a3b447c7beb9cc43ffbdf91a7a8a1b0` · 16,422 B
- **label:** `agent-authored held-out set; not independent` (carried in the
  artifact, the descriptor, and required on every emitted metric surface)
- **generation:** `ops.held_out_relevance build_set()` — deterministic over
  `PIN_COMMIT` inputs (`git show` of the committed registries at the P36.79
  dispatch boundary `80d71cf1`), so a resumed `live_verification=true` run
  re-derives byte-identical bytes; slot selectors are opaque registry
  positions + closed transform vocabulary — the authored act (mix, subjects,
  surfaces, judgements) is committed method, the rendered queries are not.

## The seal and the access rule

- **Object:** `gs://${SIG_GCP_PROJECT}-sig-restricted/search/held-out/sig.held-out-relevance-set-1.json`
  (the PRIVATE restricted bucket). Restore point: bucket versioning + the
  committed digest.
- **Readers:** the acceptance row R11-K13-SRCH-07 (P36.71) only. Tuning
  contexts (P36.31, P36.32, P36.38…P36.40) read the committed descriptor —
  the digest — and never the set: no fixture, reader, or export in the repo
  carries a set row, and `tests/ops/test_held_out_relevance.py` fails if
  emitted content lands in the tree or a non-seal module imports the emit
  path (B-28 = b's "never visible" made structural).
- **Sealed before SRCH-01/02 start:** the digest + reader rule are committed
  now (SIG-ENG-042 — the ordering is the invariant); only the object write
  is queued.

## Authority — the OM-20 naming, quoted verbatim

LEDGER GATE DECISIONS, **GATE-G5 §4 (2026-10-25T18:40Z)**, kind
`pre-authorization`: *"pre-authorise the 13 named 11C OM-20 rows: P35.2,
P35.23, P36.13, P36.33, P36.43, P36.44, P36.46, P36.68, P36.75, P36.76,
P36.77, P36.78, P36.79"* — **P36.79 is named verbatim**; the write is
pre-authorised in-ticket under AR-2/AR-3; expires GATE-G6 (OM-10/OM-20).
Window (the contract cell verbatim): `any time outside 03:00-10:00Z`.

## Queued run — the re-run writes the object

- **Reason queued:** hosted env absent at this row — no ADC,
  `SIG_GCP_PROJECT` unset; the write stays armed, never fabricated.
- **Planned at:** 2026-10-29T16:54:11Z (`date -u`)
- **Re-run (verbatim):**

```
implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md live_verification=true
```

- **Environment required:** `SIG_GCP_PROJECT`, ADC
  (`gcloud auth application-default login`), `SIG_HELDOUT_AUTHOR` (the
  recorded operator id, OM-20 scope discipline), `gcloud storage` on PATH.
- **The leg:** `ops/gcp/held-out-seal.sh --apply` — emits the bytes
  deterministically, writes the object, reads it back and refuses (exit 4)
  unless the object sha256 equals the committed descriptor digest; the clock
  guard exits 42 inside 03:00-10:00Z.
- **Obligation:** `D-P36.79-1` (OPEN) — closed by the executed write whose
  object digest matches `descriptor.json`.

*This packet records the seal obligation; it never claims it ran. The set's
bytes exist only as the derived object — committed nowhere.*
