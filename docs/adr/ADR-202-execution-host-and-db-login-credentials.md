# ADR-202 — The execution host pattern and DB-login credentials (P34.43)

- Date: 2026-10-08
- Status: accepted
- Ticket: P34.43 (Round 11 / P34, row 253 — SIG-SEC-007's last leg,
  SIG-CONF-013's probe-run record; the conditioned-grant widening answers
  ADR-201's third revisit trigger)
- Base: `r11/P34.42b-least-privilege-job-identities-remove-editor`
- Related: ADR-201 (the conditioned-grant pattern this row's grants reuse and
  whose `CONDITIONABLE_ROLES` set-of-one this row deliberately widens),
  ADR-108 (the pooled read store whose statement budgets `sig_audit`'s
  timeout mirrors), HG-09 (secrets are environment/Secret Manager only),
  P34.42b (the job-identity spine this host runs under), P34.46 (the L52
  `recovery_apply` deploy that unlocks the L2 leg), P34.44b (the reserved
  `sig-quality-probe-rt` workload this host's leg is scoped under)

## Context

Hosted return passes and quality probes need a least-privilege place to run
and two least-privilege database credentials: a SELECT-only audit/probe login
(`sig_audit`) and — once the L52 `recovery_apply` change lands the
`sig_recovery` NOLOGIN group role — a bounded recovery login. Two decisions
had non-obvious answers:

1. **Where the work runs.** A workstation `gcloud`/proxy session inherits the
   operator's broad project credentials, so the probe's rights are the
   operator's rights and the "least-privilege host" claim would be honour
   system. The host must itself be a GCP workload bound to a scoped identity.
2. **How the credential lives.** Postgres passwords stored anywhere a file or
   a command line can reach (`.pgpass`, argv, a mounted file) violate HG-09
   and leak into `ps`-visible surfaces. The value must move only through
   Secret Manager and process environment.
3. **What the L2 login is called.** The L52 `recovery_apply` change creates
   `sig_recovery` as a `NOLOGIN` *group* role. A second LOGIN role named
   `sig_recovery` cannot coexist with it — the credential must be a distinct
   LOGIN role holding membership in the group.

## Decision

**Ephemeral Cloud Run job family, not a standing service.** `ops/exec_host.toml`
declares one template; each run mints a timestamped job `sig-exec-<purpose>-<stamp>`
(`sig-ops exec-host plan/render/run/smoke`, applied by `ops/gcp/exec-host.sh`)
with `--tasks=1 --max-retries=0`, a bounded `--task-timeout`, gen2 execution,
the Cloud SQL connection, and a **read-only** Cloud Storage mount of the
restricted bucket (the GCS FUSE `readonly` flag at the mount layer). The job
name is injected as `SIG_EXEC_JOB_NAME` so the smoke/probe path writes its
`sig.probe-run/1` record under `ops/probes/` — the SIG-CONF-013 per-use record.

**The reserved probe identity, scoped by an `exec` leg.** The host runs under
`sig-quality-probe-rt` (the P34.42b-declared identity reserved for P34.44b's
workload) rather than a new service account: the IAM declaration gains a
`[[oneoff]]` table and a fourth `exec` leg so the reserved-identity rule
(ordinary workload bindings are refused on reserved accounts) is satisfied by
an explicit, separately-auditable leg instead of a loosened check. Its grants
are exactly: `roles/cloudsql.client`, secret accessor on
`sig-audit-password`/`sig-recovery-password`, and two prefix-conditioned
storage bindings on the restricted bucket — `roles/storage.objectViewer` on
`objects/evidence/captures/` (the read the mount makes effective) and
`roles/storage.objectCreator` on `objects/ops/probes/` (create-only probe
records; no delete, no overwrite — `objectCreator` carries neither). This
widening fires ADR-201's third trigger; the evaluation is appended there and
the answer is this ADR: the same conditioned-grant shape, two managed roles
chosen so **no** delete or replace permission exists anywhere on the account.

**Secret Manager-only passwords.** `sig_audit`'s and `sig_recovery_login`'s
passwords are generated into the environment, written to Secret Manager over
stdin, and bound into the job via `--set-secrets`; no file, argv, or log ever
carries a value (HG-09). `ops/gcp/db-logins.sh` holds the catalog leg
(guarded `CREATE ROLE … IF`-style statements via `sig-ops db-login`):
`sig_audit` gets `NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE`,
`CONNECTION LIMIT 4`, `default_transaction_read_only = 'on'`,
`statement_timeout = '60s'`, and membership in `sig_read_public` — plus a
Sqitch change (`audit_login`) that lands the role definition in the migration
chain so fresh/CI databases carry the same posture. The recovery leg mints
`sig_recovery_login` (a distinct LOGIN role granted `sig_recovery`
membership) and is dependency-gated: it exits 42 while the group role is
absent, i.e. until `live:P34.46` has deployed `recovery_apply`.

## Consequences

- `ops/iam_identities.toml` gains `[[oneoff]]` + `condition_description`;
  `ops/src/ops/iam_identities.py` gains the `Oneoff` model, the `exec` leg in
  `scope='services|jobs|exec|all'`, and a widened `CONDITIONABLE_ROLES`
  (`objectUser`, `objectViewer`, `objectCreator`) — ADR-201's reviewable
  declaration change, recorded.
- `db/deploy|revert|verify/audit_login.sql` lands after the L52 tip; the
  login's *table* grants stay P34.46's (the hosted schema owns them), while
  the migration pins the role's posture so any database built from the plan
  agrees with the hosted catalog.
- The exec host is strictly name-checked (`sig-exec-*` minted names only) so
  cleanup can never touch a standing job; L1 mutates only inside its window
  (≥ 2026-10-13T12:00Z, never the batch window), L2 queues on exit 42 until
  `live:P34.46`.

## Alternatives considered

- **Operator workstation as the execution host** — the workload would carry
  the operator's project credentials; "least-privilege" would be unverifiable.
  Rejected.
- **A standing Cloud Run *service* for probes** — a listening surface with a
  permanent URL for work that is inherently batch-shaped; more attack surface,
  more to keep honest. Rejected.
- **`.pgpass`/file-based credentials or `--set-env-vars` for the password** —
  a file or a describe-visible env var is a secret in a file/log surface.
  Rejected (HG-09).
- **Naming the L2 credential `sig_recovery`** — impossible: L52 already
  creates that name as a `NOLOGIN` group; a distinct `sig_recovery_login`
  member is the only coherent shape. Rejected (by construction).

## Revisit trigger

- GCS FUSE mounts gain a finer read-only enforcement story (or Cloud Run jobs
  gain a native prefix-scoped mount) — re-judge whether the mount flag plus
  conditioned IAM is still the tightest available posture.
- `sig_audit` needs a write (e.g. probes persist results *in* Postgres rather
  than `ops/probes/`) — the SELECT-only posture and `read_only` default are
  the contract; widening them is a new ADR.
- The exec host needs a second workload class (long-running probe services,
  non-ephemeral scheduling) — the one-off job pattern and the `exec` leg are
  deliberately scoped to ephemeral names only.
- `roles/storage.objectCreator`/`objectViewer` stop being sufficient for the
  probe prefix pattern (a needed verb lands outside them) — re-run the
  ADR-201-style managed-role comparison before widening further.
