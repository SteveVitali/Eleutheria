## Summary

Implements **P02.2 — the OCFL write-once evidence store** (canonical §17): the byte layer under every claim. Stacked on `devin/p02-1-claim-spine`.

- A new **`evidence/`** package (`sig-evidence`) owning the §17 store contract (ADR-006/ADR-023): content addressing, OCFL 1.1 layout, the S3/Object-Lock backend, storage tiers, the WACZ capture pipeline, redaction, disappearance/link-rot, and ingest-run reproducibility.
- A new **`db/` sqitch change** `evidence_store`: the deduplicated blob registry, the `(blob_digest, source_uri)` uniqueness §17.2 mandates, the redaction-version guard, and the audited access log — exercised against a real PG18.

Spec: `docs/tickets/P02.2__evidence-store.md` (cites §17). Requirement IDs stamped: **SIG-EVID-001 … SIG-EVID-017**.

## What changed

- `evidence/src/evidence/`: `digest`, `ocfl`, `storage`, `capture`, `tiers`, `redaction`, `access_log`, `disappearance`, `ingest_run`, `store`, `cli`.
- `db/deploy|revert|verify/evidence_store.sql` + `db/sqitch.plan`.
- Wiring: `pyproject.toml` (workspace member + mypy overrides), `Makefile`, `tests/support.py` (ADR-sanctioned package).
- Tests: `tests/evidence/` (49 unit) + `tests/db/test_evidence_store.py` (7 live-PG).
- Docs: `ADR-023`, `docs/adr/README.md`, `docs/traceability.md` (P02.2 section), `docs/risk_register.md` (P02.2 section), `evidence/README.md`.
- `uv.lock` / `pylock.toml`: add `blake3`, `boto3`; `playwright` as the optional `capture` extra.

## Design decisions

- **New `evidence/` package (ADR-023).** §47's package list is frozen and none of its members is a natural home for a cross-cutting, connector-facing evidence-store library. Registered as an ADR-sanctioned addition (`ADR_EXTENSION_PACKAGES`) so the layout tests treat it as sanctioned, not a violation.
- **Blob-level dedup (ADR-023).** §17.2 requires both "dedup by digest → one blob, **N capture rows**" and "`(content_digest, source_uri)` unique". P02.1 shipped `evidence_capture UNIQUE (content_digest, artifact_id)`, which blocks the N rows. The uniqueness is moved to a new `evidence_blob (blob_digest, source_uri)` registry; the capture uniqueness is dropped (new sqitch change, never an in-place edit).
- **Governance-mode Object Lock, never compliance** (SIG-EVID-006), so a lawful takedown stays satisfiable — enforced by `assert_governance_not_compliance`.
- **Real browser capture kept optional.** Live Playwright capture ships behind the `capture` extra; the store, OCFL layer, and deterministic WACZ packager are usable/testable without a browser (mirroring how the DB tests gate on Docker).

## Verification

- `make check` green: ruff + ruff format + mypy (70 source files) + **497 pytest passed** (incl. the 7 new live-PG tests and 49 evidence unit tests) + `verify-gen`.
- **Live (Phase 5.3):** drove real headless-Chromium `capture_live` against a local SPA (JS `fetch` of JSON): recorded 2 responses (HTML + JSON), rendered HTML, a 10 KB PNG screenshot, and packaged a valid WACZ 1.1.1 whose WARC **retained the fetched JSON** (E2 re-parseability). Cleaned up after.

### Acceptance criteria → evidence

| AC (spec) | Status | Evidence |
|---|---|---|
| OCFL object readable without SIG's code (SIG-EVID-005) | met | `test_ocfl.py::test_object_readable_without_sig_code` (stdlib-only walk of inventory.json) |
| Sealed → metadata-only public rep; bytes access-controlled + audited (SIG-EVID-010/012) | met | `test_tiers.py::test_sealed_exposes_metadata_only`; `test_access_log.py`; DB `test_access_log_only_records_restricted_and_sealed` |
| Digests round-trip as multihash; dedup by digest (1 blob, N rows) (SIG-EVID-002/004) | met | `test_digest.py`; DB `test_unchanged_page_yields_one_blob_but_many_capture_rows`; `test_store.py::test_refetch_of_unchanged_bytes_dedups_blobs` |
| JS artifact → full capture set under one artifact (SIG-EVID-008) | met | `test_capture.py::test_js_artifact_full_capture_set`; `test_store.py::test_capture_set_becomes_n_rows_under_one_object`; live smoke |
| Redaction → new capture w/ parent_capture_id; original never edited (SIG-EVID-011) | met | `test_redaction.py`; DB `test_redaction_is_a_new_capture_with_parent_and_version` / `test_redaction_without_version_is_rejected` |
| Vanished artifact → disappearance event + research task; nothing deleted (SIG-EVID-013/014) | met | DB `test_disappearance_is_an_update_not_a_delete`, `test_ingest_run_grant_forbids_delete_on_evidence`; `test_disappearance.py` |
| Phase-gate (§51.3): CI green, new reqs tested, ADRs for deviations, traceability + risk-register updated | met | `make check`; ADR-023; `docs/traceability.md`; `docs/risk_register.md` |

Full requirement→where→test map: `docs/traceability.md` (P02.2 section).

## Deferred / scaffolded (documented in the risk register)

- **SIG-EVID-007/008 live WACZ per-PR** and **SIG-EVID-017 connector-level reproducibility** — the machinery is built and tested here; the live-connector wiring lands in P04+/P08 (RISK-P2-09/10). The real capture path is verified once here (live smoke above).
- Out of scope per ticket: EDTF/as-of/PROV-O export (P02.3), Zenodo/SWH deposit (Phase 14).

Generated with [Devin](https://devin.ai)

