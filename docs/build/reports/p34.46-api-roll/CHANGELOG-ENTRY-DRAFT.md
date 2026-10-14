<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- P34.46 L1 draft — the API changelog entry. Ships ONLY once confirmed
     verbatim (contract § In scope 6); it lands in CHANGELOG.md under
     [Unreleased] at L2 after the roll verifies, not before. The image
     digest fills from the deployed revision at the slot. -->

# API changelog entry — DRAFT (ships verbatim-confirmed at L2)

Proposed entry for `CHANGELOG.md` `## [Unreleased]` `### Changed`:

> - **API: Round-10 schema + read roll deployed** (P34.46; cites
>   SIG-TRUST-001/002/005/006, SIG-FIND-006/008, SIG-EVAL-001/002,
>   SIG-STORE-008, SIG-SEC-011) — `sig-api` rolled by digest
>   (`sig-api@sha256:<digest>`) over the deployed plan tip: typed
>   assertions and capture bindings, the shared temporal read contract,
>   the append-only publication-disposition registry with the
>   disposition-aware read surface (`pending_publication_review`
>   tombstones for the still-flagged), the durable anonymous correction
>   intake and its reviewed-application bridge, bounded recovery apply,
>   the least-privilege public read allowlist and login roles, the
>   Part VIII seal register, and the honest evaluation posture. Every
>   response carries the A-20 basis label; `/v1/dossier/fl` no longer
>   serves the placeholder and `/terms` names no board or counsel
>   (RI-02, F-130, F-189 — verified live at the slot).

Verification note (not part of the entry): the wording is confirmed
verbatim against what the rolled revision actually serves before it
ships — the dossier/terms claims hold only if the L2 verification
items pass.
