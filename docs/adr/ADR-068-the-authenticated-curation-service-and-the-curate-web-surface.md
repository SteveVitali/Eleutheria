# ADR-068 — The authenticated curation service and the `/curate/**` web surface

- **Status:** Accepted
- **Phase / ticket:** P21.6 — Curation web UI (the review queue and L0 contributor entry as a web surface)
- **Date:** 2026
- **Related / amends:** ADR-030 (LLM-to-review boundary — **amended**, see below),
  ADR-054 (the contributor system: five tiers, L0 entry, revert-as-new-assertion,
  poisoning resistance), ADR-061 (`PgReviewQueue` / `review_decision`), ADR-066
  (`sig-ops` runtime composition, the export-backed web data layer), ADR-049 (the
  no-JS archivable public web shell); LD-F05, LD-H04, LD-D04; RISK-P21-10, RISK-P21-11;
  SIG-CONTRIB-*, SIG-LLM-001..007, SIG-UI-036..041, SIG-IDENT-025/026.

## Gate status (copied from the run contract)

The capstone decision-gate on this ticket resolved **RUN AS WRITTEN**: A6 was ticked
(CLI + JSONL accepted as the Phase-5 conforming form) **and** the operator wants the
web surface as the Phase-21 enhancement — so this ticket is not skipped. Separately,
**P21.2 shipped the shrunk case** (compute-on-read accepted under A5/HG-14; **no** new
annotation-persistence repos were built). Therefore, per this ticket's out-of-scope
rule, this ADR builds **no new persistence**: curation writes use the existing paths —
the JSONL append-only curation log and P19.5's `PgReviewQueue` / `review_decision`
table for ER review decisions, and **compute-on-read** for contradiction/task
dispositions. Every write is still append-only and carries a human actor id.

## Context

Through P21.5 SIG had a public **read** API (`api.app`, §37) and a static, zero-JS
public web shell (`web/`, Phase 15), but the curation surface the Phase-5 ticket
deferred to "P15" — reviewers working the ER review queue and contradiction/task
dispositions in a browser, and L0 contributors submitting through the web — was never
built (LD-F05, LD-H04). The engine pieces existed and were tested: the review queue
(`resolution/review_queue.py`, `review_pg.py`), the contributor tiers and submission /
revert / anti-poisoning logic (`tasks/`), and the policy gates (`policy/`). What was
missing was the **authenticated write surface** and its **web pages**.

Two constraints shape the design. First, **Part VIII §0.7 is binding**: the curation
API is authenticated and must never run on the public API process, and it serves no
per-person data beyond the P16.1 pseudonymous contributor id. Second, the **defining
standard §3.1**: machine suggestions are labelled suggestions, never auto-applied; a
decision carries a reason; a contradiction is dispositioned (shown with both claims,
their evidence and dates), never deleted.

## Decision

**1. A separate, authenticated FastAPI app — mounted only when `SIG_CURATION_ENABLED=1`.**
`api/src/api/curation.py` builds `create_curation_app()`, distinct from the public
`create_app()`. When the flag is not set (the default), the app carries **no**
`/v1/curation/*` routes at all — the write surface is *structurally absent* (404), not
merely guarded (RISK-P21-10). The public read-API process never sets the flag, so it
can never expose the write surface. `sig-api serve-curation` refuses to bind (exit 3)
unless the flag is set. In the runtime composition (`sig-ops up`) it runs as a second
host process bound to loopback (`127.0.0.1:8001`); `sig-ops status` reports it on its
own line, marked *authenticated, non-public*; `ops/docker-compose.yml` gains an
`api-curation` service (in the `curation` profile) whose published port is bound to
`127.0.0.1` only.

*Rejected:* mounting curation routes conditionally on the existing public app. Even
env-gated, that puts the write surface one config flip away from the public process —
Part VIII §0.7 wants the separation to be structural (a different app, a different
process, a different port), not a runtime toggle on the public app.

**2. Bearer-token auth bound to the P16.1 contributor tiers; per-route tier checks.**
Every route requires a bearer token that maps to a pseudonymous
`tasks.contributor.Contributor` (no/unknown token → 401). Each route asserts the
contributor's tier holds the write scope it needs (`tasks.contributor.may_write`;
insufficient → 403): listing/deciding the ER queue needs `verify_submissions`
(trusted-reviewer+); a contradiction disposition needs `resolution_override`
(curator+); a task disposition needs `task_disposition` (registered+); an L0
submission needs `queue_submission` (any authenticated tier); a revert needs
`human_assertion` (curator+). The token registry carries only a pseudonymous handle
and a tier — no real-name field exists (SIG-CONTRIB-006).

**3. Append-only, human-attributed writes via the existing paths (P21.2 shrunk).**
Every write appends exactly one row to an append-only `CurationLog` (the JSONL queue
path) carrying the action, target id, the **human actor id** (the contributor handle),
a timestamp, and an action-specific payload. Nothing is ever mutated: deciding the
same item again appends a second row (a decision *history*), never an edit — the same
append-only semantics as `PgReviewQueue`'s `review_decision` table (ADR-061), which is
the durable backend when a DSN is configured. The review queue's *pending* set and the
contradiction/task dispositions are **computed on read** (proposals minus those with a
decision row; the latest disposition per id) — no new persistence repo, consistent
with P21.2's shrunk compute-on-read posture. `CurationLog.append` refuses an empty
actor, so no write path — not a default, not a machine suggestion — can create a row
without a human being attributable for it.

**4. Machine suggestions are labelled and never auto-apply (amends ADR-030).**
ADR-030 drew the LLM-to-review boundary in the engine (LLM output reaches only the
review queue; `ReviewQueue` has no graph-write path). This ADR extends that boundary
to the **API and the web surface**: a model-assisted proposal carries its suggested
decision, confidence class and model/prompt provenance as a *labelled suggestion*
(`auto_applied: false`); the `/decide` route requires an explicit human `decision`
field, and there is no code path that reads a suggestion and writes a decision. A test
enumerates every write route and asserts each is unreachable without an authenticated
actor (401), so no decision is ever writable without a human actor id.

**5. The `/curate/**` web pages: server-shaped, progressively enhanced, WCAG 2.2 AA.**
`web/src/pages/curate/**` are Astro pages behind auth. They are **not** under the
public zero-JS/performance budget (a JS island for keyboard shortcuts/diff views is
permitted), but they are under **WCAG 2.2 AA** and ship no client JS in the built site,
so every form is a native `<form method="post">` that works with **no JavaScript**
(progressive enhancement), posting to the authenticated curation API. The queue is
ordered by impact (RISK-P21-11), the compare view shows the per-comparison match
rationale (SIG-IDENT-025) with no decision pre-selected, the contradiction view shows
both claims with evidence and dates (§3.1), and the L0 form refuses without evidence
and routes device observations to OSM/DeFlock (SIG-CONTRIB-004). `lighthouserc.json`
gets a separate `/curate/**` assertion block (accessibility 100; performance advisory;
script-size not asserted). The public pages keep the zero-JS budget unchanged.

## Consequences

- The curation write surface exists and is exercised end to end, closing LD-F05 /
  LD-H04 for the review-queue + L0-entry scope.
- **RISK-P21-10** (a curation endpoint exposed publicly): mitigated by the separate
  process + env flag + loopback binding + the disabled-by-default structural guard and
  its test.
- **RISK-P21-11** (reviewer fatigue): the queue is ordered by tier/impact in both the
  API and the web view.
- No new persistence was added: contradiction/task dispositions are compute-on-read and
  the audit trail is the append-only JSONL curation log (or `review_decision` for ER
  decisions), consistent with P21.2 (shrunk). When a real annotation-persistence layer
  lands, the `CurationLog` seam is the swap point.
- Asset-promotion (SIG-PUB-012) is **not** wired to the curation service here (still
  PARTIAL); MapRoulette / OSM contribution-back and the usability study are P21.7.

## Revisit trigger

Revisit when any of the following fires (SIG-STORE-007):

- **A real annotation-persistence layer is built** (P21.2 un-shrunk) — the
  compute-on-read dispositions and the JSONL `CurationLog` are replaced by that layer's
  repos; the `CurationLog` seam is the intended swap point.
- **Go-public is approved (HG-01 + HG-11)** — the local-only, loopback-bound staging
  posture for the curation process is replaced by a real authenticated host/DNS
  cut-over with production credentials (beyond the P16.1 demo tier tokens).
- **The tier-token model outgrows demo keys** — account provisioning beyond the P16.1
  tier tokens (deliberately out of scope here) is designed.
