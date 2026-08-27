<!--
SPDX-License-Identifier: Apache-2.0
Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-->
# `db/` — the physical claim spine

This package owns the **physical schema** of the canonical store (PostgreSQL 18 +
PostGIS, ADR-001): the L0–L3 claim/evidence/resolution spine of §16, the domain
entity tables of Appendix C, append-only enforcement, the resolution non-overlap
exclusion constraint, and the sensitivity-tier row-level security. It was
established by ticket **P02.1**.

## Migrations are sqitch (SIG-STORE-041)

Physical migrations are managed with [sqitch](https://sqitch.org). Every change
ships a `deploy/`, `revert/`, and `verify/` script and is listed, in dependency
order, in `sqitch.plan`. The schema is **never hand-edited in place**: changes
after P02.1 are new sqitch changes (SIG-STORE-042 — dropping/retyping a `claim`
column requires an ADR and a migration claim-set instead).

```
db/
  sqitch.conf        engine = pg
  sqitch.plan        the ordered change list
  deploy/            forward migrations (CREATE …)
  revert/            reverse migrations (DROP …)
  verify/            post-deploy assertions (object exists / constraint present)
```

## Applying the schema

Deploy against a running Postgres with the sqitch CLI (or its Docker image):

```bash
# with a local sqitch binary:
cd db && sqitch deploy db:pg://user:pw@host:5432/sig

# or with the official image (no local Perl needed):
docker run --rm -e PGPASSWORD=pw -v "$PWD/db":/repo -w /repo \
  sqitch/sqitch deploy db:pg://user@host:5432/sig
```

## Testing

The claim-spine behaviour (append-only, corrections, the exclusion constraint,
RLS, and the schema-integrity guards) is verified against a **real** PG18+PostGIS
instance — never a mock. The tests (`tests/db/`) use `testcontainers` to launch
the database and apply this sqitch plan to it, so all you need locally is a
running Docker daemon:

```bash
make test-db     # SIG_REQUIRE_DB_TESTS=1; fails loudly if Docker is unreachable
```

Without `SIG_REQUIRE_DB_TESTS`, the DB tests skip when Docker is unavailable so
`make test` still runs the rest of the suite; CI sets the flag so they are
blocking (SIG-STORE-024).
