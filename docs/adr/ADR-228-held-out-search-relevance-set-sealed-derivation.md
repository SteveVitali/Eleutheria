# ADR-228 — held-out search relevance set: sealed derivation, digest-only reader contract (P36.79)

- Date: 2026-10-29
- Status: accepted
- Ticket: P36.79 (R11-K13-SRCH-00, manifest row 371 — on
  `r11/P36.79-held-out-search-relevance-set`)
- Base: `r11/P36.30-procurement-relevance-rule`
- Requirement stamps: **SIG-SRCH-013** (measured relevance — held-out half;
  owner P36.71, this row also named), **SIG-CONF-012** (the metric is
  estimand-labelled wherever it appears), **SIG-ENG-042** (the set seals
  before SRCH-01/02 start — the ordering is the invariant), **D-K3-7 [B-28]
  = b** (separate agent, labelled — carried verbatim)
- Supersedes: nothing.

## Context

SIG-SRCH-013 requires relevance measured each release on a development set
and a **held-out set** (top-3 ≥ 80% held-out; 0 misleading top hits). The
K3 design (§9, D-K3-7) requires the held-out set written **before** the
tuning work and **never visible to** the contexts that tune it (P36.31,
P36.32, P36.38–P36.40); the answered plan decision B-28 = b makes a
separate agent context the author, labelled `agent-authored held-out set;
not independent`. The contract requires: only the set's sha256 commits; the
bytes live as one restricted-bucket object; only SRCH-07 (P36.71) reads it;
a resumed `live_verification=true` run re-derives the bytes
deterministically.

The tension: deterministic re-derivation demands committed generation
machinery, while "never visible" forbids the set content in the repo. Any
committed generator is, in principle, runnable — the seal cannot be
cryptographic under a deterministic re-derivation requirement.

## Decision

1. **Sealed derivation, not committed content.** `ops.held_out_relevance`
   emits `sig.held-out-relevance-set/1` deterministically from the
   committed registries **at a pinned commit** (`git show PIN:path`; PIN =
   the P36.79 dispatch boundary, immutable in history). The recipe is the
   committed method — slots select opaque registry positions and render
   query text through a closed surface vocabulary — so no query string is
   committed and every expectation is resolved (auditable) at emit time.
   Wall clock, environment and ordering never enter the bytes.
2. **Digest-only reader contract.** The single committed reference point is
   `docs/build/reports/p36.79-held-out-relevance/descriptor.json`
   (`sig.held-out-relevance-descriptor/1`): label, locator, reader rule,
   sha256 — never a set row. Readers consume the digest; SRCH-07 fetches
   the object and verifies it against the digest.
3. **No read path in the repo.** The emit machinery lives in the ops seal
   lane (the production-mutation surface), never in `exports`/`web`/`api`/
   `tasks` where benchmark readers live; no fixture, data file or reader
   carries a set row. A test fails on any emitted binding landing in the
   tree or any non-seal module importing the emit path. A tuning context
   that ran the generator would be breaking this recorded rule — a
   discipline breach, exactly like reading the bucket.
4. **The label travels with the metric.** Every surface that reports the
   held-out metric labels it `agent-authored held-out set; not independent`
   (SIG-CONF-012) — the estimand is declared wherever the number appears.
5. **The write is one bounded mutation.** `ops/gcp/held-out-seal.sh` —
   OM-14 named at GATE-G5 (expires GATE-G6), window `any time outside
   03:00-10:00Z`, `SIG_HELDOUT_AUTHOR` recorded, emit → write → read-back
   digest verify (refuses on mismatch). Restore point: bucket versioning +
   the committed digest. Queued `prepared_not_executed` while hosted
   credentials are absent (OM-19); `D-P36.79-1` records the obligation.

## Consequences

- The set exists before P36.31/P36.32 start; its digest is the only thing
  those rows may bind.
- A resumed run re-derives byte-identical bytes only while the recipe and
  the pinned inputs stand — changing `_SLOTS`, a transform, or `PIN_COMMIT`
  mints a different digest, which is a **new seal**, never a silent edit.
- SRCH-07 trusts the digest, not a copy: `verify_object` is the only
  acceptance check.

## Revisit trigger

- P36.71 (SRCH-07) reports the held-out metric against the first model
  release — evaluate whether the agent-authored label stays sufficient or
  an operator-authored set is commissioned (D-K3-7 = a).
- Any tuning-context read path is proposed, or the recipe's opacity is
  judged insufficient — re-decide the seal mechanism (e.g. an
  operator-held seed) as a new ADR.
- The object write is executed — record the sealed digest + time in the
  run ledger and flip `D-P36.79-1`.
