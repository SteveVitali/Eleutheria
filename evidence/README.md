<!--
SPDX-License-Identifier: Apache-2.0
Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-->
# `evidence/` — the OCFL write-once evidence store

The byte layer under every claim (§17, ADR-006 / ADR-023). Every connector writes
captures through this package; every claim references an `ingest_run` recorded
here. Bytes are **write-once** — changes to the layout after this are migrations,
never in-place edits. Established by ticket **P02.2**.

## What it owns

| Module | Responsibility | Requirements |
|---|---|---|
| `digest` | Content addressing as multihash (base32-lowercase); SHA-2 interop digest + BLAKE3 fixity | SIG-EVID-002/003/004 |
| `ocfl` | OCFL 1.1 writer/reader — one object per source stream, one version per capture; **readable without SIG code** | SIG-EVID-005 |
| `storage` | `BlobStore` backends: `LocalFileStore` + `S3ObjectStore` with versioning + **governance-mode** Object Lock | SIG-EVID-006 |
| `capture` | The capture set (WACZ + screenshot + payload + raw HTML) and a deterministic WARC→WACZ 1.1.1 packager; real Playwright capture behind the `capture` extra | SIG-EVID-007/008 |
| `tiers` | `public`/`restricted`/`sealed` + the sealed **metadata-only** public representation | SIG-EVID-009/010 |
| `redaction` | Redaction as a **new capture** with `parent_capture_id`, method + version | SIG-EVID-011 |
| `access_log` | Audited access to restricted/sealed bytes, with its own retention | SIG-EVID-012 |
| `disappearance` | Disappearance events, research-task generation, link-rot sweep, Wayback | SIG-EVID-013/014/015 |
| `ingest_run` | Reproducibility: the `ingest_run` record, `LC_ALL=C`/`TZ=UTC`, claim-tuple canonicalisation | SIG-EVID-016/017/018 |
| `store` | The `EvidenceStore` facade: capture set → OCFL version → DB rows | (ties the above together) |

The relational side (the deduplicated `evidence_blob` registry, the
`(blob_digest, source_uri)` uniqueness, the redaction-version guard, and the
audited `evidence_access_log`) is the `evidence_store` sqitch change in `db/`.

## CLI (SIG-ENG-013)

```bash
uv run python -m evidence digest FILE      # base32 multihash of a file
uv run python -m evidence object-path ID   # OCFL storage path for a source-stream id
uv run python -m evidence env              # the deterministic ingestion environment
uv run python -m evidence lock-config      # the governance-mode Object Lock config
```

## Live capture (optional)

Real headless-browser capture (Playwright) is the `capture` extra so the store,
OCFL layer, and packaging stay usable and testable without a browser:

```bash
uv sync --extra capture && uv run playwright install chromium
```

## Testing

Pure-Python behaviour (content addressing, OCFL readability + dedup, tiers,
WACZ packaging, redaction, disappearance, reproducibility) is in `tests/evidence/`
and runs with no external services. The byte-level schema is exercised against a
**real** PG18+PostGIS in `tests/db/test_evidence_store.py` (the P02.1
testcontainers harness applies the sqitch plan, now including `evidence_store`).
