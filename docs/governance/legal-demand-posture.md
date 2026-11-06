<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Legal-demand response posture

**Status:** adopted by the operator 2026-10-01T04:03:25Z (GATE-P round 3,
A-4 — `Q-E2-09 [A-4] = c`; ADR-166). **Written:** 2026-11-06 (`date -u`),
P37.8 (manifest row 428, R11-GOV-03). The public rendering lives at
`/about/legal-demands/`; the same sentences ship there as sha256-pinned
`data-copy` rows in `docs/build/reports/copy-batches/batch-19.md` (B-2 —
agent-drafted, pending the operator's verbatim confirmation). This
posture is not legal advice. No lawyer's written opinion has been
obtained, and no lawyer has reviewed it. The operator adopted it on
2026-10-01. (ADR-167.)

SIG-SEC-003 (§44.3) requires the response posture for demands directed at
SIG to be documented **before** the first demand arrives, and a
transparency report covering legal demands received, complied with and
refused. This document is that posture; the published counts sit on the
page. The warrant canary — a SHOULD — is declined (ADR-166 records the
rationale; no canary is operated and none is claimed anywhere).

## What SIG holds

SIG holds public records about surveillance infrastructure, the evidence
behind each claim, and the append-only record of decisions and
corrections. It holds no contributor accounts, no reader tracking, and no
per-person or plate data — not holding data is the main protection.

A demand directed at SIG can therefore reach only public records,
evidence captures and operations logs; it cannot reach data about
contributors, because none is held. (SIG-SEC-002.)

## Who receives legal process

The operator — an individual, disclosed as SIG's interim legal home —
receives all legal process addressed to SIG. There is no organisation
and no lawyer. The channel is the e-mail address the dispute page
names.

ADR-165 records the interim legal home (SIG-GOV-012/013 waived, WV-01).
Every demand lands on one person; this posture records that rather than
removing it.

## Preservation requests

A preservation request is logged with its date and scope. SIG's claim
record and evidence store are append-only and versioned, so
preservation is the default: a correction never overwrites or
deletes. A lawful preservation request is honoured as a recorded legal
hold on what exists.

## User notice

Where a demand seeks information about an identifiable person and the
law allows notice, SIG tells that person before complying. SIG holds
almost nothing about individuals, so in most cases there is no one to
notify.

## Publication of counts

The counts below are republished when a demand arrives or when a
demand's handling changes. Each update is a new dated snapshot
appended to the count record — counts only: never a requester's
identity or case detail.

(On the page, "the counts below" resolves to the rendered
`sig.legal-demand-counts/1` snapshot. ADR-166 decision 2; the
transparency scrub and Part VIII rules, ADR-162.)

## No warrant canary

SIG does not operate a warrant canary. With one maintainer and no
lawyer, a scheduled canary cannot be maintained reliably, and a
lapsed canary would itself read as a signal — so the canary is
declined, and this page says so.

(ADR-166 decision 3.)

## Records

- Decision: `docs/adr/ADR-166-legal-demand-posture.md` (A-4, Q-E2-09 = c,
  adopted 2026-10-01T04:03:25Z); the no counsel basis: ADR-167.
- Public page + count record: `/about/legal-demands/`,
  `web/src/lib/legal-demands.ts` (`sig.legal-demand-posture/1` +
  `sig.legal-demand-counts/1`).
- Copy confirmation register: `docs/build/reports/copy-batches/batch-19.md`.
- Obligation record: `docs/tickets/DEFERRALS.md` row `D-R11-SEC003-1`.
