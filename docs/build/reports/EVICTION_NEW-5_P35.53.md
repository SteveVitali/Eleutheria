<!-- SPDX-License-Identifier: Apache-2.0 -->

# NEW-5 eviction record — P35.53 (SIG-REL-004/005, REL-03a)

G3 RM-8: real candidate trees and registries do not live in the public
repository. Under this row the committed `/r/p-…` release trees and
staging-registry files below left `docs/build/reports/` — a deletion of
**files**, not of history: every publication id, descriptor digest and
manifest digest the runs recorded stays pinned in the surviving packet
metadata (`CANDIDATE_MANIFEST.json`, `JOURNEY_PORTFOLIO.json`,
`PUBLISH_PROOF.json`, `ROLLBACK_REHEARSAL.json`) and in git history. The
recommit guard is `scripts/ci/release_tree_guard.py` (exercised by
`tests/ops/test_release_pipeline.py`); the verification suites regenerate
their candidate packet at test time (`tests/ops/candidate_fixture.py`).

What each evicted root contained at `HEAD` before this row (publication ids
+ the sha256 of the sorted committed path list — the *set* evidence):

| evicted root | files | publication ids | listing sha256 |
|---|---|---|---|
| `p32.23a-release-candidate/candidate_release` | 21 | `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` | `70fa151f1a8c0da3de0b8d654974525c71f0a1e19ced321a0e28687ede508482` |
| `p32.24-investigation-journey-verification/corpus_registry` | 262 | `p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd` | `786dc108744ec56e15a2e3640901dfef431b03abfa01f5c53807a5481d59470f` |
| `p32.24-investigation-journey-verification/corpus_release` | 179 | `p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd` | `db60feaf2df5287e92de98b84e8b4d57a77ae0d83621595d03faa775c64a2a85` |
| `p32.24-investigation-journey-verification_2026-10-04/corpus_registry` | 262 | `p-d96f6823cb34aa0fa5c4ea21ce7a741cd3bf4b261319a562b0149a9aeddbf562` | `ab21a096fc8049b6dcdaa30c41803f8ce37a048673838a1c5ef6212f07df3e1d` |
| `p32.24-investigation-journey-verification_2026-10-04/corpus_release` | 179 | `p-d96f6823cb34aa0fa5c4ea21ce7a741cd3bf4b261319a562b0149a9aeddbf562` | `a4d1a71a177aab3cc6fae104a04c0f97a8cbdcc73efa0b5484cfff2406a13c80` |
| `p32.25-accepted-release-verification/staging_registry` | 49 | `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` | `afe7c2112c82fa3e65233d6f72ca5b102bc3cd5b8f167963d59cf0d8ced93b79` |
| `p32.25-accepted-release-verification/rehearsal` | 603 | `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`, `p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd` | `e7627b09c950ae49d8f3318947008a0d4bbe9d6fbbeec5aa5a9210082c671d49` |
| `p33.2-composed-verification/release` | 26 | `p-8414a4165a7866094922585e022be28c755f57da4a1bcb801071b0863e615ffe` | `9208d1057e1cb648867dadfd79bd7689205d6b89cd5a34a4b4e9b7d907a46c40` |
| `p33.2-composed-verification/registry` | 35 | `p-8414a4165a7866094922585e022be28c755f57da4a1bcb801071b0863e615ffe` | `9fda3bfcbbc0508c8ea74a5eb28b33238876ece0cd398cd86fa5c639bc2e9d22` |

Kept (not release trees / registry state — the run *records* and the
export/snapshot inputs the tests regenerate from):

- `p32.23a-release-candidate/` packet metadata (`CANDIDATE_MANIFEST.json`,
  `DISCLOSURE.json`, `ROLLBACK_PACKET.json`, `MATERIALIZATION.json`,
  `LIVE_RETURN_PASS.json`, `CORRECTION.md`, `README.md`), its
  `candidate_export/` compartment export, and `_regen_snapshot/`.
- `p32.24-*` report files + `corpus_export/` (the acceptance corpus the
  publish rehearsal still regenerates its stand-in prior from).
- `p32.25-accepted-release-verification/` report files
  (`PUBLISH_PROOF.json`, `ROLLBACK_REHEARSAL.json`, `PUBLIC_VERIFICATION.md`,
  `CORRECTION.md`, `LIVE_RETURN_PASS.json`, `README.md`).
- `p33.2-composed-verification/` report files.

Consumers updated: `tests/ops/test_release_publish_verify.py` and
`tests/ops/test_journey_verify.py` now point at the synthesized packet;
`journey-verify`'s default `--candidate` still names the historical packet —
its manifest survives, so a bare run reports the absent tree through the
candidate checks (fail with owner+landing) instead of a crash.
