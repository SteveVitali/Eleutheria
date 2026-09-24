# ADR-078 — CI composed hardening: a real composed-e2e job, offline vendored scanners, the PR-vs-nightly split, and the starlette security bump (vs a SaaS scanning stack)

- **Status:** Accepted
- **Phase / ticket:** P24.4 — CI hardening (CI.1, GL-CI-01)
- **Date:** 2026-09-13
- **Related:** ADR-072 (the documentation freshness gates this ticket wires onto
  PRs), ADR-073 (committed build memory — `check-build-memory.sh` enforcement),
  ADR-076 (the free GitHub Actions cron precedent), ADR-077 (observability),
  ADR-049 (the licence categories SIG-UI-039 excludes — mirrored here for Python
  deps); SIG-ENG-015/016 (CI mirrors `make check`), SIG-STORE-003 (binding
  zero-cost posture), HG-09 (secrets env-only), RISK-P21-05 (no credential
  literals), RISK-P24-03; the LEDGER open findings CI-RED-01 and DOCKER-DOWN.

## Context

CI.1 (GL-CI-01) asks for four things inside the zero-cost posture: (a) a CI job
that runs the composed `tests/e2e` **for real** — Node + Docker present so the
S8 web-build seams run, closing the P20.4/CI-RED-01 gap honestly; (b) a nightly
composed run; (c) dependency / licence / secret scanning; (d) `make docs-check`
+ `check-build-memory.sh` enforced on PRs.

The landed seams to build on (re-confirmed at build time):

- `ci.yml` already had three jobs: `docs` (PR-only, `make docs-check`), `python`
  (`make check` mirror, `SIG_REQUIRE_DB_TESTS=1` — Docker is present on
  `ubuntu-latest`, so `tests/db` and `tests/e2e` already ran there, but the S8
  web-build fixtures *skipped* because no Node/`web/node_modules` is installed),
  and `web` (`npm run check` — the JS-side licence gate `check:licenses`).
- The secret/license checks that already exist are narrower than the contract:
  `tests/connectors/test_secrets.py` covers `SIG_*` literals in `.py`/`.toml`
  only; `check-build-memory.sh` greps secret shapes under `docs/` only; the
  licence gate covers `web/` JS deps only — the Python dep tree had neither a
  licence gate nor a vulnerability audit.

Two constraints shape the design: **SIG-STORE-003** (zero-cost — no paid
scanning service, no credential literals) and the repo's own "humans and CI run
the same commands" rule (`Makefile` header) — whatever CI runs must be runnable
locally, byte for byte.

## Decision

**1. A dedicated `composed` job runs `tests/e2e` for real — with the web build
present.** `ci.yml` gains a `composed` job: checkout → uv + `make sync` → Node 22
+ `npm --prefix web ci` → `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e`
(`TESTCONTAINERS_RYUK_DISABLED=true`, matching the `python` job). Docker is on
the runner, so seams S1–S7 run; Node + `web/node_modules` make the S8 fixtures
run instead of skip — including the LD-V08 export-mode dossier build. The
`python` job is unchanged (it still runs the full suite; S8 skips there without
node_modules — a documented, deliberate duplication: the `composed` job is the
one that proves the *whole* suite with the web build present).

**2. Scanning is three gates, split by where each can be deterministic.**

- **Secret scan** (`scripts/ci/secret_scan.py`, stdlib-only): every *tracked*
  file (`git ls-files`) scanned for high-confidence credential shapes — a
  superset of the build-memory grep set (AKIA…, `gh[pousr]_`/`github_pat_`,
  `xox[baprs]-`, `sk-`, `AIza`, PEM private-key blocks) plus a repo-specific
  `SIG_*_{TOKEN,KEY,SECRET,PASSWORD} = "literal"` rule (`SIG_SECRET_*` is carved
  out — those vars hold Secret Manager *names*, never values, per the P24.1
  convention). Findings print `file:line: rule-id` and **never echo the matched
  text**. Runs on every PR — a committed secret is a permanent leak; nightly is
  too late.
- **Dependency licence scan** (`scripts/ci/license_scan.py`, stdlib-only):
  classifies every installed distribution via `importlib.metadata`
  (`License-Expression` → `License` → `License ::` classifiers). It mirrors the
  web gate's *excluded categories* exactly (non-commercial, source-available,
  BUSL, SSPL, Elastic, Commons-Clause, proprietary — substring match); an
  **unresolvable** licence is a review-required failure; and a **strong-copyleft
  (GPL/AGPL)** dependency must equal the frozen `EXPECTED_STRONG_COPYLEFT` set
  (`docutils`, `igraph`, `rfc3987` — all dev/transitive, reviewed) so a *new*
  copyleft dep breaks the gate and a departed one forces the set to shrink. A
  copyleft flag only counts when the signal *line* is a licence identifier
  (begins with the token) — licence *texts* that merely mention GPL (pandas'
  bundled licence-history table) do not flag. Runs on every PR.
- **Dependency vulnerability audit** (`scripts/ci/dep_audit.sh`): `uv export
  --frozen --all-packages` → `uvx --from pip-audit pip-audit` against OSV — free,
  no account, no committed tool dependency. It needs **network** and advisories
  drift without a commit, so it rides the **nightly** (not the PR gate — a
  PyPI/OSV outage must not block PRs).

All three are reachable by humans via `make scan-secrets` / `scan-licenses` /
`audit-deps` (`security-scan` = all three).

**3. `nightly.yml` runs the composed suite + all three scans and *reports*.**
Cron `0 3 * * *` (03:00 UTC — ahead of reingest 05:00 and observability 06:00 so
a broken composed run reports before they spend calls) + `workflow_dispatch`.
Every stage runs `continue-on-error`, so the report is complete even on red —
a report that exists only on green is the wrong shape. `nightly_report.py`
composes `nightly-report.md` (stage table + log tails + run link), uploads it
`if: always()` with the JUnit XML + scan logs, and **exits non-zero when any
stage failed** — the report step is itself the gate; a red nightly is loud.

**4. The doc gates are enforced on PRs as named steps.** The `docs` job already
ran `make docs-check` (which includes `check-build-memory.sh`); the contract
names both, so the job now also runs `bash scripts/docs/check-build-memory.sh .`
as its own visible step — the enforcement survives a future docs-check
recomposition.

**5. The gate caught a real vulnerability — fixed, not papered over.** The first
`pip-audit` run reported starlette 0.48.0 vulnerable (PYSEC-2026-248/249/1942/
2280/2281; the 0.x line never received the fixes — minimum fixed is 1.3.1).
`api/pyproject.toml` bumps `fastapi>=0.141,<0.142` (0.135+ is the first line
whose starlette bound admits 1.x) and pins `starlette>=1.3.1` explicitly (the
package imports starlette directly; the floor documents the security
constraint). `uv.lock` + `pylock.toml` regenerated; the whole suite re-verified
green (2878 tests incl. all `tests/api` + `tests/e2e`). A nightly that went red
on day one and stayed red would have been honest reporting but a worse outcome
— the fix is in this ticket.

## Consequences

- The composed suite runs for real in CI on every PR + push-to-main, and again
  nightly — the honest closure of CI-RED-01 (S8 runs, not skips) and the
  DOCKER-DOWN carry (the full DB + composed suite is CI-enforced with
  `SIG_REQUIRE_DB_TESTS=1`, and was re-run green locally for this ticket).
- A seeded violation is provably fatal to the gate — asserted by
  `tests/unit/test_security_scanners.py` (seeded AWS key / PEM / `SIG_*` literal
  → exit 1; BUSL / unresolvable / new-GPL records → exit 1) and by the workflow
  tests that fail if a scan step is removed.
- The report artifact exists even when the run is red (`if: always()`), so the
  nightly *reports* rather than silently failing.
- Secrets stay env-only (HG-09): the workflows reference `${{ secrets.* }}`/
  `${{ vars.* }}` only; the scanners carry no credentials.

## Alternatives considered

- **gitleaks (action or binary)** for the secret scan — rejected as the default:
  `gitleaks-action` wants a licence key for org repos and a downloaded binary
  adds supply-chain surface for a job a 40-line stdlib scanner does
  deterministically offline; the shape set here is a deliberate superset of what
  `check-build-memory.sh` already greps. Equivalent-class, swappable later.
- **Dependabot/Renovate/GitHub Advanced Security** — rejected: GHAS secret
  scanning is a paid/org feature; Dependabot version bumps are orthogonal (this
  gate audits the *current* tree nightly, which is what CI.1 asks).
- **pip-licenses as a committed dep** — rejected: an extra toolchain dep to scan
  metadata the stdlib already reads; `importlib.metadata` + the explicit
  allowlist/deny-lists keeps the gate zero-cost and vendored-style.
- **Run the dep audit on PRs too** — rejected: it needs network (OSV) and a
  PyPI outage would block unrelated PRs; new-dep review is still covered at PR
  time by the licence gate, and the nightly cadence is the spec's shape.
- **Extend the `python` job with Node instead of a separate `composed` job** —
  rejected: keeps the fast unit/integration job fast and names the composed
  gate as its own check (a `composed` failure reads as *the composed suite*,
  not "something in make test").
- **Ignore-list the starlette CVEs** — rejected outright: the fix was cheap
  (fastapi bump) and an allowlisted vuln is a hidden vuln.

## Revisit trigger

Revisit this decision when any of the following holds:

- **The runner image changes** (ubuntu-latest drops a Docker daemon or Node):
  the `composed` job would fail loudly via `SIG_REQUIRE_DB_TESTS=1` — revisit if
  the fix is a heavier runner rather than a restore.
- **The secret-scan shape set needs to grow** (new credential classes — e.g.
  `SIG_*` gains a new suffix): extend `RULES` and add a seeded test; if the
  shape set becomes unwieldy, swapping in gitleaks behind the same step is a
  drop-in change.
- **The licence gate's expected-copyleft set needs a fourth entry** — that is a
  deliberate review point, not a bug: edit `EXPECTED_STRONG_COPYLEFT` with a
  comment naming the review, or remove the dep.
- **pip-audit flakes on advisory-DB availability** — if nightly redness from
  network flakiness (not real vulns) becomes noise, add a retry; do NOT make it
  non-blocking (a silent audit is worse than a flaky one, RISK-P24-03).
- **Nightly cadence proves wrong** (too slow to catch a same-day advisory, or
  wasteful): the cron is one line; the report/gate machinery does not change.
- **fastapi 1.x lands / starlette floor needs raising** — the `starlette>=1.3.1`
  floor in `api/pyproject.toml` is the security line; keep it ≥ the then-current
  fixed version.
