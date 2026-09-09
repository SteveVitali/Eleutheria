# CURATION_UI.md — running and using the curation surface (P21.6, ADR-068)

The **curation surface** is the authenticated write side of SIG: reviewers work the
entity-resolution review queue and contradiction/task dispositions, and L0 contributors
submit evidence and request reverts. It is a **separate, authenticated service** from
the public read API and is **never public** (Part VIII §0.7). This document is how to
run it locally, who can do what, and a recorded end-to-end walkthrough.

> **Persistence note (P21.2 was shrunk).** P21.2 shipped the compute-on-read case and
> built **no new annotation-persistence repos**. So curation uses the **existing**
> paths: ER review decisions land in an **append-only JSONL curation log** (and, when a
> DSN is configured, P19.5's `PgReviewQueue` / `review_decision` table); contradiction
> and task dispositions are **compute-on-read** (the latest disposition per id, read
> from the same append-only log). Every write is one new row carrying a **human actor
> id** — nothing is mutated, nothing is deleted.

## Disabled by default, and never on the public process (RISK-P21-10)

The curation routes are **absent** unless `SIG_CURATION_ENABLED=1`:

- `create_curation_app()` (`api/src/api/curation.py`) mounts `/v1/curation/*` **only**
  when the flag is set; with it unset the app has no such routes at all (404), not
  merely guarded.
- `sig-api serve-curation` **refuses to start** (exit 3) unless the flag is set.
- The public read API (`sig-api serve` / `create_app`) **never** carries curation
  routes — a test asserts it (`tests/api/test_curation.py::test_public_read_api_never_carries_curation_routes`).

## Running it locally

### Via `sig-ops` (the recommended local path)

```sh
# From web/: build the static site once so the static server has something to serve.
npm --prefix web run build

# Bring the whole stack up. `sig-ops up` starts, alongside PG + the read API + the
# static server, the AUTHENTICATED curation service as a SEPARATE host process,
# bound to loopback (127.0.0.1:8001) with SIG_CURATION_ENABLED=1.
uv run sig-ops up --jurisdiction okc

# `status` reports the curation process on its OWN line, marked non-public:
uv run sig-ops status
#   PG        (…): healthy
#   API       (http://127.0.0.1:8000): healthy
#   curation  (http://127.0.0.1:8001): healthy  [authenticated, non-public]
#   static    (http://127.0.0.1:4321): healthy

uv run sig-ops down   # stops every host process (incl. curation) + tears down PG
```

Override the bind with `SIG_CURATION_HOST` / `SIG_CURATION_PORT`. It defaults to
loopback deliberately — the curation surface must not be world-reachable.

### Directly (a single process)

```sh
SIG_CURATION_ENABLED=1 uv run sig-api serve-curation --host 127.0.0.1 --port 8001
```

### The web pages

The `/curate/**` pages are built by the normal web build (`npm --prefix web run build`
→ `web/dist/curate/…`). They are the reviewer/contributor UI; each form posts to the
curation API at `SIG_CURATION_API_URL` (default `http://127.0.0.1:8001`, baked at build
time). These pages are **behind auth and under WCAG 2.2 AA but are NOT under the public
zero-JS/performance budget** — a JS island for keyboard shortcuts/diff views is
permitted (the shipped build uses none, so every form works with **no JavaScript**).
Do **not** deploy `/curate/**` to the public archive/CDN; serve them only from the
authenticated curation surface.

## Roles (P16.1 contributor tiers → what each route needs)

Auth is a bearer token that maps to a **pseudonymous** contributor tier (no real-name
field exists — SIG-CONTRIB-006). A missing/unknown token is `401`; a token whose tier
lacks the route's write scope is `403`.

| Route | Method | Required scope | Minimum tier |
|---|---|---|---|
| `/v1/curation/review-queue` (list, filter by tier) | GET | `verify_submissions` | trusted_reviewer |
| `/v1/curation/review-queue/{id}` (compare view) | GET | `verify_submissions` | trusted_reviewer |
| `/v1/curation/review-queue/{id}/decide` (match/no-match/defer) | POST | `verify_submissions` | trusted_reviewer |
| `/v1/curation/contradiction/{id}/disposition` | POST | `resolution_override` | curator |
| `/v1/curation/task/{id}/disposition` | POST | `task_disposition` | registered |
| `/v1/curation/submission` (L0 entry) | POST | `queue_submission` | anonymous (authenticated) |
| `/v1/curation/revert` | POST | `human_assertion` | curator |

The demo token registry (`CURATION_KEYS`) maps `anon-demo-key`, `registered-demo-key`,
`reviewer-demo-key`, `curator-demo-key`, `maintainer-demo-key` to those tiers.
Production wires this to the real tier-token store; account provisioning beyond the
P16.1 tier tokens is out of scope (P21.6).

## The four invariants (and where they are proven)

- **Disabled by default / never public** — RISK-P21-10; `tests/api/test_curation.py`
  (`test_routes_absent_when_disabled`, `test_public_read_api_never_carries_curation_routes`),
  `tests/ops/test_curation_service.py`.
- **Authenticated + tier-gated** — 401/403; `test_unauthenticated_is_401`,
  `test_tier_insufficient_is_403`.
- **Append-only, human actor id** — one row per decide, repeats append, empty actor
  refused; `test_decide_writes_exactly_one_row_and_repeats_append`,
  `test_curation_log_refuses_empty_actor`,
  `test_every_write_route_requires_auth_so_carries_an_actor`.
- **Machine suggestions labelled, never auto-applied** — SIG-LLM-001/002;
  `test_model_suggestion_is_labelled_and_not_applied`; e2e `curate.spec.ts`.

## Recorded walkthrough — a reviewer processes an ER item without JS (AC)

The screens are described in text (the surface is colour-free and semantic).

1. **Queue** (`GET /curate/`, or `GET /v1/curation/review-queue`). The reviewer signs
   in as `reviewer-demo-key` (trusted_reviewer). Two items are pending, **ordered by
   impact** (RISK-P21-11): the tier-5 match `agency:okcpd ~ agency:okc-pd` (weight
   +12.40) first, then the tier-4 vendor match. Each item links to a compare page. A
   model-assisted extraction shows a **labelled machine suggestion** ("Machine
   suggestion (not applied): match — confidence medium, from model gpt-x / prompt
   p-2026-07. A human must decide.").
2. **Compare** (`GET /curate/{id}/`). Two side-by-side panels show the left/right
   entity fields; the **match rationale** lists the per-comparison decomposition
   (`name +8.2 — exact token overlap`, `jurisdiction +4.2 — same city`). The decide
   form is a native `<form method="post">` with radios **match / no-match / defer** —
   **none pre-selected** — and a reason field. No JavaScript is required.
3. **Decide** (`POST /v1/curation/review-queue/{id}/decide`, `decision=match`). The
   server appends **exactly one** append-only row attributed to the human actor
   (`actor=reviewer-1`) and (for a model-assisted item) copies the model/prompt
   provenance onto the row. Without JS the browser follows a 303 redirect back to the
   queue; API clients get JSON.
4. **History / reversal**. Deciding the same item again (`decision=no-match`) appends a
   **second** row — the decision *history* now reads `['match', 'no-match']`; the first
   row is never mutated. The item drops out of *pending* (compute-on-read).

Verbatim run against the app (TestClient over `create_curation_app()` with
`SIG_CURATION_ENABLED=1`):

```
== root ==
{'service': 'SIG curation service', 'enabled': True, 'public': False, …}
== list (reviewer) ==
pending count: 2 | first: er_match:agency:okcpd~agency:okc-pd
== compare (item detail) ==
summary: tier 5: agency:okcpd ~ agency:okc-pd (weight +12.40, p=0.998)
== decide match ==
status: 200 | recorded actor: reviewer-1 | decision: match
== decide again (append-only history) ==
second row status: 200
history rows: 2 -> decisions: ['match', 'no-match']
== unauth 401 == 401
== wrong tier 403 == 403
== model suggestion labelled ==
suggestion: match auto_applied: False
```

The same flow works without JavaScript in the browser: `web/tests/e2e/curate.nojs.spec.ts`
drives the built pages with JS disabled and asserts every form is a native POST form
with its required fields and no `<script>`, and `curate.spec.ts` + `a11y.spec.ts` assert
WCAG 2.2 AA (axe) on every `/curate/` page.
