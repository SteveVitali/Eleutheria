# ADR-119 — The GCP project-id leak check is scoped to code + config; the append-only build memory is exempt (the design's ADR-R9-LEAKSCOPE)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.19 (`docs/tickets/P31.19__round9-closeout.md`)
  — Round 9 `CLOSE.1`. Closes **D-P30.4-4**.
- **Date:** 2026-09-27
- **Related:** go-live spec **D3** (non-public identifiers resolve from the
  environment; the project id is written `$SIG_GCP_PROJECT`), **HG-09** (secrets
  are environment variables only), **P1–P3** (append-only history is never
  rewritten), ADR-078 (the CI scanning gates), ADR-098 (the custom-domain
  cut-over — one of the landed ADR bodies that records the id), deferral
  **D-P30.4-4**; backlog home **BL-057**; the operator policy answer **Q7 =
  (a)** (LEDGER § GATE DECISIONS "Round 9 ratification", 2026-09-24) and the
  design's own recommendation (`docs/build/reports/ROUND9_FOLLOWUPS_DESIGN.md`
  §6 Q7: *Recommendation: (a)*).

## Context

`tests/connectors/test_secrets.py::test_gcp_project_id_is_env_resolved_not_committed`
implements D3's guard: when armed by `SIG_GCP_PROJECT`, it `git grep`s the real
GCP project id and fails if the literal appears in a tracked file — the
repository is public, so the id must resolve from the environment.

When the P30.4 capstone armed it, the check failed on **45 committed files**
(71 at the P31.19 base): run ledgers, PR bodies, `LEDGER.md`, `BUILD_INDEX.md`,
`DEFERRALS.md`, `docs/build/BACKLOG.csv`, and ADR-098 — every occurrence inside
the append-only build memory (`docs/build/`, `docs/tickets/`, `docs/adr/`),
where the id was necessarily *recorded* to document real hosted work (job
names, bucket paths, digests). The check skipped unarmed, so `make check` was
green without having run it (D-P30.4-4).

The operator's recorded policy decision (Q7, 2026-09-24) answers the two
options the design framed:

- **(a) narrow the check to code + config** — CHOSEN. A GCP project id is not a
  credential (it grants nothing by itself; it is an identifier, and the
  repository that runs the project is public anyway), and the build memory that
  records it is append-only history (P1–P3: never rewritten).
- **(b) one-time recorded redaction** — NOT chosen and NOT done. Redaction can
  legitimately touch only files that are not append-only records; the landed
  ADR bodies, DEFERRALS rows, LEDGER and run-ledger history cannot be
  rewritten, so (b) could never make the armed check pass on its own.

## Decision

1. **The check's scope is an explicit include list — code + config.**
   `test_gcp_project_id_is_env_resolved_not_committed` now greps only
   `_PROJECT_ID_SCOPE`: every §47 package source tree (`<pkg>/src`,
   SIG-ENG-012), the deployable schema surface (`db/deploy`, `db/revert`,
   `db/verify`, `db/sqitch.plan`, `db/sqitch.conf`), `ontology/vocab` +
   `ontology/generated`, the whole `ops/` runtime composition (gcp scripts,
   Dockerfiles, `cadence.toml`, `config.toml`, `ops/web/`), the whole `web/`
   package (SIG-ENG-010 — source, tests, scripts, config, static assets), the
   `tests/` suite, `scripts/`, `.github/`, and the repo build/deploy/CI config
   (`Makefile`, `pyproject.toml` + `*/pyproject.toml`, `uv.lock`, `pylock.toml`,
   `.python-version`, `.gitignore`, `.devinignore`, `.env`/`.env.*`). A
   structural guard asserts the pathspec resolves to real tracked files, so a
   typo can never silently scope the check to nothing.

2. **The exclusions and the reason.** `docs/` is out of scope — above all the
   append-only build memory under `docs/build/`, `docs/tickets/` and
   `docs/adr/`, which *records* the id as historical fact and must not be
   rewritten (P1–P3); every other `docs/` tree, and the root prose documents
   (`README.md`, `AGENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
   `CITATION.cff`, `LICENSE`), are documentation, not code + config. The rule
   is unchanged where it binds: a literal id in any in-scope file is a leak —
   write `$SIG_GCP_PROJECT`.

3. **The check is armed in CI.** The `security` job in
   `.github/workflows/ci.yml` now runs the scoped test with
   `SIG_GCP_PROJECT: ${{ vars.SIG_GCP_PROJECT }}` — the id travels as a
   repository *variable* (it is not a credential and is already public in the
   recorded history), never a committed literal. When the variable is unset
   the test skips, never a false red. Unarmed runs (`make check` without the
   variable) keep the skip-by-default behaviour. Verified armed:
   `SIG_GCP_PROJECT=<id> uv run pytest tests/connectors/test_secrets.py`
   passes on the P31.19 tip — zero occurrences in scope.

4. **What did NOT change.** No append-only record was redacted or rewritten
   (option (b) is not done and never will be done by this ADR). The other
   secret checks in `test_secrets.py` keep their repo-wide scope: a committed
   *credential* is a leak wherever it lands — including build memory — and the
   `SIG_*` value checks stay repo-wide and env-armed (HG-09). `make
   scan-secrets` (`scripts/ci/secret_scan.py`) is untouched.

## Consequences

- The armed check is green and now runs in CI, so D3's project-id rule has a
  live guard on the surfaces where a literal would actually deploy or leak —
  instead of a check that could only ever be red on history it can never fix.
- The build memory keeps its honest history: 71 tracked files record the id as
  fact; none was altered.
- A new doc-only copy of the id (e.g. a new run ledger) is still fine — and
  still should be written `$SIG_GCP_PROJECT` where the author remembers — but
  it no longer breaks a guard whose scope is deployable surfaces.
- `D-P30.4-4` closes; no new deferral is opened.

## Revisit trigger

Revisit when (a) the project id ever carries sensitivity beyond an identifier
(e.g. a policy that treats infrastructure naming as confidential — then the
recorded history, not the check, becomes the problem, and the answer is a new
policy ADR, not a history rewrite); (b) a new deployable surface is added
outside the include list (a new top-level package, a new CI system) — extend
`_PROJECT_ID_SCOPE` in the same change; (c) `vars.SIG_GCP_PROJECT` rotates —
the CI step picks it up without a code change; or (d) a counsel/egress
decision requires the project id out of the public repo entirely — that is a
new ADR about the repository, not this check.
