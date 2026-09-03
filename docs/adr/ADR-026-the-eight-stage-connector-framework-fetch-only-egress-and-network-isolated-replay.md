# ADR-026: The eight-stage connector framework — fetch-only egress, socket-level network-isolated replay

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P04.1
- **Requirement ids:** SIG-INGEST-001, SIG-INGEST-002, SIG-INGEST-003, SIG-INGEST-011, SIG-INGEST-012, SIG-INGEST-013, SIG-INGEST-014, SIG-INGEST-015, SIG-INGEST-016, SIG-INGEST-017, SIG-INGEST-018, SIG-INGEST-019, SIG-INGEST-028, SIG-LIC-010
- **Spec:** docs/2_canonical_design_spec.md §21 (connector architecture), §22.4 (compact enforcement), §42.4 (export-time computation)

## Context

§21 requires every source adapter to implement the same eight-stage interface
(`discover→fetch→capture→parse→extract→normalize→link→load`), with `fetch()` the
only stage permitted network egress, every post-`capture()` stage a pure function
of stored artifacts, network-isolated replay, and shadow-mode diffing. P04.1 owns
the **reusable substrate** every later connector (P04.2/P04.3, P07.x) plugs into;
it writes no source-specific connector. Much of the machinery already exists in
adjacent packages — the OCFL evidence store and its content addressing, ingest-run
reproducibility (`evidence.ingest_run`, including `canonical_claim_tuple` /
`claim_set_fingerprint`), disappearance events (`evidence.disappearance`), the
licence-compartment gate (`policy.licensing`), crawler conduct (`policy.crawler`),
the deterministic resolver (`resolution.cascade`), and the PROV-O projection
(`exports.provo`). The framework's job is to define the stage contract and wire
these together, not to reimplement them.

## Decision

Add the connector framework to the existing `connectors` package (§47 already
homes ingestion there), across focused modules: `stages` (the `Stage` vocabulary,
content-addressed `StageArtifact`, the stores, `RunContext`, and the `Connector`
base class), `net` (the shared politeness layer), `isolation`, `pipeline` (the
driver), `replay`, `disappearance`, and `lineage`; and extend `loader` with the
full gate and the export-compatibility check. `connectors` gains workspace
dependencies on `sig-evidence`, `sig-resolution`, and `sig-exports` (none depend
back on it — no cycle).

Three decisions are load-bearing:

1. **`fetch()` is the only egress stage, and isolation is enforced at the socket
   layer (SIG-INGEST-002/018).** `connectors.isolation.network_isolated` patches
   `socket.socket`/`create_connection` to raise, and the driver runs *every*
   post-capture stage inside it — on a live run *and* during replay — so an
   accidental egress in `parse()` or later fails the run rather than silently
   succeeding. Enforcing below any HTTP client makes the guarantee independent of
   what a connector reaches for. `discover()` lists identifiers only; all content
   egress flows through `fetch()` and the single shared `PoliteFetcher`.

2. **A narrow `CaptureStore` seam, in-memory now, OCFL adapter later.** The
   post-capture stages read archived bytes back by digest through a small
   `CaptureStore` protocol (`put`/`get`/`has`). P04.1 ships the in-memory
   implementation the tests and replay harness use; adapting the real
   `evidence.store.EvidenceStore` (OCFL/S3) to it is a P04.2 concern. This keeps
   replay reproducibility testable without standing up object storage, and keeps
   the framework decoupled from the storage backend.

3. **The connector-loader gate and export check delegate to existing policy.**
   `loader.assert_loadable` checks `ingestion_permitted` **and** a
   permitting `compact_status` **and** a content-permitting `custody_posture`
   before any fetch (SIG-INGEST-014/028); `loader.assert_export_compatible`
   delegates to `policy.licensing.compute_export_license`, so the SIG-LIC-010
   build-fails-on-incompatibility gate has one implementation, reused, not two.

The `load()` stage *produces* claim rows; the **driver** asserts them, and only
on a live run — replay and shadow runs never assert (SIG-INGEST-018/019). This is
what lets shadow mode report a diff before anything lands.

## Consequences

Later connectors implement the source-specific stages
(`discover/fetch/parse/extract/normalize`) and inherit gate, isolation, lineage,
disappearance handling, replay, and shadow mode for free. Every stage stays a
plain-CLI-runnable, separately addressable unit, so the Dagster-OSS orchestration
choice remains reversible (SIG-INGEST-021, ADR-016) — the orchestrator import
stays confined to `orchestration/`. The cost: a real `CaptureStore` adapter over
the OCFL store is still owed (tracked for P04.2), and socket-level isolation is a
coarse instrument — it forbids *all* sockets in post-capture stages, which is
correct for replay but means a stage may never legitimately open one (by design).

## Alternatives considered

- **A new top-level `ingest`/`pipeline` package** — rejected: not in the fixed
  §47 layout, and it would split the framework from the registry and loader gate
  it builds on.
- **Enforcing purity by code review / a lint rule instead of runtime isolation**
  — rejected: SIG-INGEST-018 wants the *interface* to make source contact
  impossible during replay, and AC1 is a runtime test; a lint rule proves nothing
  at run time.
- **Taking a hard dependency on `evidence.store.EvidenceStore` now** — rejected:
  it drags OCFL/S3 (and boto3/playwright) into every connector test and couples
  the stage contract to one backend; the `CaptureStore` protocol is the seam.
- **Re-implementing licence compatibility in `connectors`** — rejected:
  `policy.licensing.compute_export_license` already realises SIG-LIC-010; the
  loader delegates.

## Revisit trigger

The OCFL `CaptureStore` adapter lands (P04.2) and reveals the protocol is too
narrow; or a source legitimately needs egress in a stage other than `fetch()`
(would require re-reading SIG-INGEST-002); or socket-level isolation proves too
coarse for a connector that must talk to SIG-internal infrastructure mid-pipeline.
