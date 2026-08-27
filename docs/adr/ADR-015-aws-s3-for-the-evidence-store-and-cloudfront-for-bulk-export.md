# ADR-015: AWS S3 for the evidence store and CloudFront for bulk-export delivery

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-EVID-005, SIG-EXPORT-008, SIG-EXPORT-009
- **Spec:** docs/2_canonical_design_spec.md §17.3, §38.5

## Context

The evidence store needs S3 semantics (versioning + Object Lock governance mode, ADR-006). But §38.5 makes egress pricing the existential cost for bulk downloads, and AWS egress is expensive — 'success is the failure mode'.

## Decision

Use AWS S3 for the evidence store (where its Object Lock semantics are load-bearing and volume is modest), and front bulk exports with CloudFront to cap origin egress. Reconcile the §38.5 constraint by (a) CloudFront caching, (b) offering torrent and IPFS for the largest artifacts (SIG-EXPORT-009), and (c) keeping a low/zero-egress object-storage mirror (e.g. R2/B2) for bulk export files so the four-figure-bill scenario is bounded.

## Consequences

Object Lock governance mode is available for evidence; bulk-download egress is bounded rather than open-ended. Multi-provider setup adds operational complexity and an explicit egress-budget alarm.

## Alternatives considered

All-AWS with direct S3 downloads (unbounded egress bill); a single zero-egress provider for everything (weaker Object Lock / preservation guarantees for the evidence store).

## Revisit trigger

Monthly egress cost crosses the budgeted threshold, download volume exceeds the modelled TB/month, or a provider changes egress pricing — at which point bulk delivery shifts further to the low-egress mirror and peer-to-peer distribution.
